"""Where each secret came from: the placeholder predicate, the recorded source and the buckets they are reported in."""

import ast
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")

REAL_KEY = "lastfmapikey00000000000000000000"


# Returns the secret names one assignment writes to, including the tuple unpack that splits a combined argument
def assigned_secret_names(assignment):
    return {node.id for target in assignment.targets for node in ast.walk(target) if isinstance(node, ast.Name) and node.id in monitor.SECRET_KEYS}


# Returns the functions that assign a secret from a parsed argument, with the secrets each one records as command line
def command_line_secret_assignments():
    assigned, recorded = {}, {}
    for node in ast.walk(ast.parse(SOURCE)):
        if not isinstance(node, ast.FunctionDef):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Assign) and assigned_secret_names(inner):
                reads_argument = any(isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id == "args" for value in ast.walk(inner.value))
                if reads_argument:
                    assigned.setdefault(node.name, set()).update(assigned_secret_names(inner))
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "record_secret_source" and len(inner.args) == 2:
                first, second = inner.args
                if isinstance(first, ast.Constant) and isinstance(second, ast.Constant) and second.value == "command line":
                    recorded.setdefault(node.name, set()).add(first.value)
    return assigned, recorded


@pytest.fixture(autouse=True)
def clean_sources():
    saved = dict(monitor.SECRET_SOURCES)
    monitor.SECRET_SOURCES.clear()
    yield
    monitor.SECRET_SOURCES.clear()
    monitor.SECRET_SOURCES.update(saved)


class TestThePlaceholderPredicate:
    @pytest.mark.parametrize("value", [REAL_KEY, "  padded-but-real  ", "your"])
    def test_a_real_value_counts_as_set(self, value):
        assert monitor.doctor_value_is_set(value) is True

    @pytest.mark.parametrize("value", ["", "   ", "your_lastfm_api_key", "  your_webhook_url", None, 0, True, ["a"]])
    def test_nothing_and_the_shipped_placeholder_do_not(self, value):
        assert monitor.doctor_value_is_set(value) is False

    # The template ships every secret as a placeholder, so treating one as configured is a false positive on the one question asked
    @pytest.mark.parametrize("key", monitor.SECRET_KEYS)
    def test_no_shipped_secret_counts_as_configured(self, key):
        assert monitor.doctor_value_is_set(getattr(monitor, key)) is False


class TestSecretFingerprint:
    def test_an_unset_secret_reports_only_that(self):
        assert monitor.secret_fields("your_lastfm_api_key", "LASTFM_API_KEY") == {"value": "not set", "chars": None}

    # The provider issues these lengths, so reporting one discloses nothing the user chose
    @pytest.mark.parametrize("key", monitor.FIXED_LENGTH_SECRET_KEYS)
    def test_a_provider_issued_secret_reports_its_length(self, key):
        assert monitor.secret_fields(REAL_KEY, key) == {"value": "set", "chars": 32}

    # A user-chosen password's length is a real disclosure in output that gets pasted into public bug reports
    @pytest.mark.parametrize("key", [key for key in monitor.SECRET_KEYS if key not in monitor.FIXED_LENGTH_SECRET_KEYS])
    def test_a_user_chosen_secret_reports_presence_only(self, key):
        assert monitor.secret_fields("hunter2-and-then-some", key) == {"value": "set", "chars": None}

    # The diagnostic line is documented as comma-separated key=value fields, so no field value may carry a comma
    @pytest.mark.parametrize("key", monitor.SECRET_KEYS)
    def test_no_secret_field_value_carries_a_comma(self, key):
        assert all("," not in str(value) for value in monitor.secret_fields(REAL_KEY, key).values())

    # The length belongs to the trace as its own field, so a reader can split the line on ", " and get pairs
    def test_the_trace_splits_into_key_value_pairs(self, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "DEBUG_MODE", True)
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)

        monitor.record_secret_source("LASTFM_API_KEY", "environment")

        rendered = capsys.readouterr().out.strip().split("Secret resolution: ", 1)[1]
        assert dict(field.split("=", 1) for field in rendered.split(", ")) == {"name": "LASTFM_API_KEY", "source": "environment", "value": "set", "chars": "32"}


class TestRecordingTheSource:
    def test_a_recorded_source_is_kept(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        monitor.record_secret_source("LASTFM_API_KEY", "dotenv file")
        assert monitor.SECRET_SOURCES == {"LASTFM_API_KEY": "dotenv file"}

    # The same key may exist in several sources while only the last applied one supplied the effective value
    def test_a_later_layer_replaces_the_earlier_answer(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        monitor.record_secret_source("LASTFM_API_KEY", "dotenv file")
        monitor.record_secret_source("LASTFM_API_KEY", "command line")
        assert monitor.SECRET_SOURCES == {"LASTFM_API_KEY": "command line"}

    def test_a_placeholder_earns_no_source(self, monkeypatch):
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "your_webhook_url")
        monitor.record_secret_source("WEBHOOK_URL", "config file")
        assert monitor.SECRET_SOURCES == {}

    def test_a_value_replaced_by_a_placeholder_loses_its_source(self, monkeypatch):
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.sh/private-topic")
        monitor.record_secret_source("WEBHOOK_URL", "dotenv file")
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "")
        monitor.record_secret_source("WEBHOOK_URL", "config file")
        assert monitor.SECRET_SOURCES == {}

    def test_a_source_outside_the_documented_order_is_refused(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        with pytest.raises(ValueError):
            monitor.record_secret_source("LASTFM_API_KEY", "guesswork")

    def test_the_trace_names_the_source_without_the_value(self, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "DEBUG_MODE", True)
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        monitor.record_secret_source("LASTFM_API_KEY", "command line")
        output = capsys.readouterr().out
        assert "name=LASTFM_API_KEY, source=command line, value=set, chars=32" in output
        assert REAL_KEY not in output


class TestReportingBuckets:
    def test_sources_are_reported_in_precedence_order(self, monkeypatch):
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "a-real-password")
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.sh/private-topic")
        monitor.record_secret_source("WEBHOOK_URL", "command line")
        monitor.record_secret_source("LASTFM_API_KEY", "environment")
        monitor.record_secret_source("SMTP_PASSWORD", "config file")
        assert monitor.secrets_by_source() == [("config file", ["SMTP_PASSWORD"]), ("environment", ["LASTFM_API_KEY"]), ("command line", ["WEBHOOK_URL"])]

    # The guard belongs in both places, since a value can be cleared after its source was recorded
    def test_a_name_whose_value_became_a_placeholder_earns_no_row(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        monitor.record_secret_source("LASTFM_API_KEY", "environment")
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "your_lastfm_api_key")
        assert monitor.secrets_by_source() == []

    def test_nothing_configured_reports_nothing(self):
        assert monitor.secrets_by_source() == []


class TestTheOrderTheLayersRunIn:
    # A secret on the command line is visible in ps output and shell history, which a config file is not
    def test_every_secret_taken_from_an_argument_is_filed_under_the_command_line(self):
        assigned, recorded = command_line_secret_assignments()
        missing = sorted({f"{function}:{name}" for function, names in assigned.items() for name in names - recorded.get(function, set())})
        assert missing == [], f"secrets assigned from an argument without recording the command line: {missing}"

    def test_the_guard_sees_the_arguments_that_carry_secrets(self):
        assigned, _ = command_line_secret_assignments()
        assert {name for names in assigned.values() for name in names} == {"LASTFM_API_KEY", "LASTFM_API_SECRET", "SP_CLIENT_ID", "SP_CLIENT_SECRET", "WEBHOOK_URL"}

    # After load_dotenv both layers look identical in os.environ, so the snapshot has to be taken first
    def test_exported_keys_are_captured_before_the_dotenv_is_loaded(self):
        assert SOURCE.index("exported_secrets = frozenset(") < SOURCE.index("load_dotenv(env_path, override=False")

    # A trace taken before the arguments are applied reports every command-line secret as coming from somewhere else
    def test_the_grouped_trace_runs_after_the_arguments_are_applied(self):
        assert SOURCE.index('record_secret_source("SP_CLIENT_SECRET", "command line")') < SOURCE.index("grouped_secrets = secrets_by_source()")

    # An unusable setting switches its feature off once, rather than failing at every alert for the rest of the run
    def test_the_webhook_channel_is_gated_where_the_configuration_is_settled(self):
        assert SOURCE.index("apply_webhook_cli_overrides(args, parser)") < SOURCE.index("if WEBHOOK_ENABLED and not validate_webhook_url():\n        verbose_print(\"Webhook notifications are off") < SOURCE.index("if not check_internet():")

    # Applying the flags only before the config load lets the config erase them, only after hides its own failures
    def test_the_explicit_diagnostic_flags_are_applied_on_both_sides_of_the_config_load(self):
        applications = [index for index in range(len(SOURCE)) if SOURCE.startswith("apply_diagnostic_cli_flags(args)", index)]
        config_load = SOURCE.index("if not load_config_file(cfg_path):")
        assert any(index < config_load for index in applications), "no flag application before the config load"
        assert any(index > config_load for index in applications), "no flag application after the config load"
