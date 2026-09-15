"""The verbose and debug printers: the grammar every debug line follows and the coverage each mode owes a user."""

import ast
import re
import sys
from html import escape
from itertools import count
from pathlib import Path

import pytest
import requests as req

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

DEBUG_PREFIX = re.compile(r"^\[DEBUG \d{2}:\d{2}:\d{2}\] ")
ALLOWED_OUTCOMES = {"OK", "failed", "degraded", "skipped"}
# A leading verb built from a variable is part of the label, unlike a value interpolated into it
LABEL_INTERPOLATION = re.compile(r"^HTTP \{\.\.\.\}$")
# Field values that read as one token even though they interpolate more than once
COMPOSITE_FIELD = re.compile(r"^(\{\.\.\.\}: \{\.\.\.\}|\{\.\.\.\}/\{\.\.\.\}|\{\.\.\.\}s|#\{\.\.\.\}|#\{\.\.\.\}/\{\.\.\.\}|\{\.\.\.\})$")
DANGLING_WORD = re.compile(r"\b(for|from|to|of|in|on|with|because|failed|error)$", re.IGNORECASE)

API_KEY = "lastfmapikey00000000000000000000"


@pytest.fixture
def restored_globals():
    saved = {name: value for name, value in vars(monitor).items() if name.isupper()}
    yield
    for name, value in saved.items():
        setattr(monitor, name, value)


@pytest.fixture
def debug_on(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)


@pytest.fixture
def verbose_on(monkeypatch):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)


# Renders one call argument as source-like text, marking each interpolation as {...}
def rendered_text(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, False
    if isinstance(node, ast.JoinedStr):
        return "".join(str(part.value) if isinstance(part, ast.Constant) else "{...}" for part in node.values), True
    return None, False


# Returns every debug_print call in the module as (line, operation, interpolated, fields)
def debug_print_calls():
    for node in ast.walk(TREE):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "debug_print":
            operation, interpolated = rendered_text(node.args[0]) if node.args else (None, False)
            yield node.lineno, operation, interpolated, [(keyword.arg, keyword.value) for keyword in node.keywords if keyword.arg]


# Returns the source lines of one function definition
def function_source(name):
    for node in ast.walk(TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(SOURCE, node) or ""
    raise AssertionError(f"{name} is not defined")


class FakeResponse:
    def __init__(self, status_code=200, headers=None, content=b"", payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no JSON payload")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise req.HTTPError(f"HTTP {self.status_code}", response=self)


class TestTheTwoModesAreIndependent:
    def test_both_printers_are_silent_while_both_modes_are_off(self, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monitor.debug_print("Some operation", outcome="OK")
        monitor.verbose_print("Something a user could act on")
        monitor.verbose_notice("Something else")
        assert capsys.readouterr().out == ""

    def test_debug_alone_does_not_bring_the_verbose_lines(self, debug_on, capsys):
        monitor.debug_print("Some operation", outcome="OK")
        monitor.verbose_print("Something a user could act on")
        printed = capsys.readouterr().out
        assert "Some operation" in printed
        assert "Something a user could act on" not in printed

    def test_verbose_alone_does_not_bring_the_debug_lines(self, verbose_on, capsys):
        monitor.debug_print("Some operation", outcome="OK")
        monitor.verbose_print("Something a user could act on")
        printed = capsys.readouterr().out
        assert "Some operation" not in printed
        assert "* Something a user could act on" in printed

    # A flag typed on the command line has to survive a configuration file that saved the mode as off
    @pytest.mark.parametrize("flag, setting", [("--verbose", "VERBOSE_MODE"), ("--debug", "DEBUG_MODE")])
    def test_the_flag_wins_over_a_saved_false(self, restored_globals, tmp_path, capsys, flag, setting):
        config_path = tmp_path / "lastfm.conf"
        config_path.write_text(f'LASTFM_API_KEY = "{API_KEY}"\nLASTFM_API_SECRET = "lastfmapisecret00000000000000000"\nDISABLE_LOGGING = True\n{setting} = False\n', encoding="utf-8")
        settled = {}

        def stop_at_the_loop(*args, **kwargs):
            settled[setting] = getattr(monitor, setting)
            raise SystemExit(0)

        with pytest.MonkeyPatch.context() as patch:
            patch.chdir(tmp_path)
            patch.setattr(monitor, "lastfm_monitor_user", stop_at_the_loop)
            patch.setattr(monitor, "check_internet", lambda *a, **k: True)
            patch.setattr(monitor.sys, "argv", ["lastfm_monitor", "someuser", "--config-file", str(config_path), "--env-file", "none", flag])
            with pytest.raises(SystemExit):
                monitor.main()
        capsys.readouterr()
        assert settled[setting] is True

    # The flags are applied once before the configuration file so its own failures are traced too
    def test_the_flags_are_applied_before_the_configuration_file_is_read(self):
        body = function_source("main")
        first_apply = body.index("apply_diagnostic_cli_flags(args)")
        config_load = body.index("load_config_file(cfg_path)")
        assert first_apply < config_load
        assert body.count("apply_diagnostic_cli_flags(args)") >= 2
        assert body.index("apply_diagnostic_cli_flags(args)", config_load) > config_load


# Runs main through the real config load and startup summary, stopping where the monitoring loop would start
def run_main_to_the_loop(tmp_path, arguments=()):
    config_path = tmp_path / "lastfm.conf"
    config_path.write_text(f'LASTFM_API_KEY = "{API_KEY}"\nLASTFM_API_SECRET = "lastfmapisecret00000000000000000"\nDISABLE_LOGGING = True\n', encoding="utf-8")
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(tmp_path)
        patch.setattr(monitor, "lastfm_monitor_user", lambda *args, **kwargs: sys.exit(0))
        patch.setattr(monitor, "check_internet", lambda *a, **k: True)
        patch.setattr(monitor.sys, "argv", ["lastfm_monitor", "someuser", "--config-file", str(config_path), "--env-file", "none", *arguments])
        with pytest.raises(SystemExit):
            monitor.main()


# Verifies an empty export is treated as absent, so a shell-profile leftover does not blank the dotenv value
def test_an_empty_export_does_not_shadow_the_dotenv_file(restored_globals, tmp_path):
    config_path = tmp_path / "lastfm.conf"
    config_path.write_text('LASTFM_API_SECRET = "lastfmapisecret00000000000000000"\nDISABLE_LOGGING = True\n', encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text(f"LASTFM_API_KEY={API_KEY}\n", encoding="utf-8")
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(tmp_path)
        patch.setenv("LASTFM_API_KEY", "")
        patch.setattr(monitor, "lastfm_monitor_user", lambda *args, **kwargs: sys.exit(0))
        patch.setattr(monitor, "check_internet", lambda *a, **k: True)
        patch.setattr(monitor.sys, "argv", ["lastfm_monitor", "someuser", "--config-file", str(config_path), "--env-file", str(env_file)])
        with pytest.raises(SystemExit):
            monitor.main()
        assert monitor.LASTFM_API_KEY == API_KEY


# The only place a user who never opens --help learns the two modes exist
class TestTheDefaultOutputNamesBothModes:
    def test_a_plain_run_says_where_more_detail_lives(self, restored_globals, tmp_path, capsys):
        run_main_to_the_loop(tmp_path)
        printed = capsys.readouterr().out
        assert "* More details:                 use --verbose or --debug" in printed
        assert "* Debug mode:" not in printed

    @pytest.mark.parametrize("flag", ["--verbose", "--debug"])
    def test_either_mode_replaces_that_row_with_the_state_of_both(self, restored_globals, tmp_path, capsys, flag):
        run_main_to_the_loop(tmp_path, [flag])
        printed = capsys.readouterr().out
        assert "More details:" not in printed
        assert "* Verbose mode:" in printed
        assert "* Debug mode:" in printed


class TestTheLineFormat:
    def test_a_debug_line_is_timestamped_and_prefixed(self, debug_on, capsys):
        monitor.debug_print("Some operation", outcome="OK")
        assert DEBUG_PREFIX.match(capsys.readouterr().out.strip())

    def test_the_fields_render_as_one_comma_separated_list(self, debug_on, capsys):
        monitor.debug_print("Some operation", user="someuser", outcome="OK")
        assert capsys.readouterr().out.strip().endswith("Some operation: user=someuser, outcome=OK")

    # A call site can pass an optional field unconditionally rather than branching around it
    def test_an_unset_field_is_dropped(self, debug_on, capsys):
        monitor.debug_print("Some operation", user="someuser", status=None)
        assert capsys.readouterr().out.strip().endswith("Some operation: user=someuser")

    def test_an_operation_with_no_fields_stays_a_bare_label(self, debug_on, capsys):
        monitor.debug_print("Some operation")
        assert capsys.readouterr().out.strip().endswith("] Some operation")

    def test_a_verbose_line_reads_as_part_of_the_run(self, verbose_on, capsys):
        monitor.verbose_print("Email alerts are off")
        assert capsys.readouterr().out == "* Email alerts are off\n"

    # A bare verbose line between two timestamped blocks cannot be correlated with anything
    def test_a_notice_raised_while_monitoring_closes_its_own_block(self, verbose_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "MONITORING_ACTIVE", True)
        monitor.verbose_notice("Automatic retries are active")
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "* Automatic retries are active"
        assert lines[1].startswith("Timestamp:")

    # Before monitoring starts the notice belongs to the startup screen, which the monitoring header closes
    def test_a_notice_raised_at_startup_carries_no_trailer(self, verbose_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "MONITORING_ACTIVE", False)
        monitor.verbose_notice("Email alerts are off")
        assert capsys.readouterr().out == "* Email alerts are off\n"

    # The startup screen is one block, so the real notice a run prints there must not split it in half
    def test_the_startup_notice_a_real_run_prints_stays_bare(self, restored_globals, tmp_path, capsys):
        run_main_to_the_loop(tmp_path, arguments=["--verbose"])
        transcript = capsys.readouterr().out.splitlines()
        index = next(number for number, line in enumerate(transcript) if line.startswith("* Email notifications are off because"))
        assert not transcript[index + 1].startswith("Timestamp:")


class TestSecretsAreRedactedInsideThePrinter:
    # One caller interpolating a secret is enough to leak it, so the sanitizer sits in the printer
    def test_a_secret_a_caller_passes_never_reaches_a_debug_line(self, debug_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", API_KEY)
        monitor.debug_print("Some operation", key=API_KEY)
        assert API_KEY not in capsys.readouterr().out

    def test_the_same_protection_covers_the_verbose_printer(self, verbose_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", API_KEY)
        monitor.verbose_print(f"Authenticated with {API_KEY}")
        assert API_KEY not in capsys.readouterr().out

    # Inlining the rendering into the sanitizer's argument breaks the check that every printed problem is classified
    def test_the_printer_sanitizes_one_local_rather_than_the_expression(self):
        body = function_source("debug_print")
        assert "message = format_diagnostic_line(_operation, fields)" in body
        assert "sanitize_error_text(message)" in body


class TestEveryDebugLineFollowsOneGrammar:
    def test_the_printers_keep_the_family_signatures(self):
        assert "def debug_print(_operation, **fields):" in SOURCE
        assert "def verbose_print(message):" in SOURCE
        assert "def format_diagnostic_line(operation, fields):" in SOURCE

    def test_no_operation_carries_an_interpolated_value(self):
        offenders = [(line, operation) for line, operation, interpolated, _ in debug_print_calls() if interpolated and not LABEL_INTERPOLATION.match(operation or "")]
        assert offenders == []

    def test_no_operation_ends_in_punctuation_or_mid_sentence(self):
        offenders = []
        for line, operation, _, fields in debug_print_calls():
            if operation is None:
                continue
            if operation.rstrip().endswith((":", ",", "...")):
                offenders.append((line, operation))
            elif fields and DANGLING_WORD.search(operation.rstrip(" :")):
                offenders.append((line, operation))
        assert offenders == []

    def test_no_line_uses_an_arrow_instead_of_an_outcome(self):
        offenders = [(line, operation) for line, operation, _, _ in debug_print_calls() if operation and "->" in operation]
        assert offenders == []

    def test_every_detail_is_a_named_field(self):
        offenders = []
        for line, _operation, _, fields in debug_print_calls():
            for name, value in fields:
                text, interpolated = rendered_text(value)
                if text is None:
                    continue
                if "->" in text:
                    offenders.append((line, name, text))
                elif interpolated and text.count("{...}") > 1 and not COMPOSITE_FIELD.fullmatch(text) and name != "error" and " " in text:
                    offenders.append((line, name, text))
        assert offenders == []

    # Reserving the token is what keeps grep 'outcome=failed' meaningful across the sibling tools
    def test_the_outcome_vocabulary_stays_closed(self):
        offenders = []
        for line, _, _, fields in debug_print_calls():
            for name, value in fields:
                if name != "outcome":
                    continue
                text, interpolated = rendered_text(value)
                if text is None:
                    continue
                if interpolated or text not in ALLOWED_OUTCOMES:
                    offenders.append((line, text))
        assert offenders == []

    # A shared wrapper takes its operation from the caller, and only that shape may pass a name here
    def test_only_a_shared_wrapper_takes_its_operation_from_a_variable(self):
        wrappers = {"debug_swallowed_exception", "verbose_degraded_feature"}
        functions = [(node.lineno, node.end_lineno or node.lineno, node.name) for node in ast.walk(TREE) if isinstance(node, ast.FunctionDef)]
        offenders = []
        for line, operation, _, _ in debug_print_calls():
            if operation is not None:
                continue
            owners = [name for start, end, name in functions if start <= line <= end]
            if not owners or owners[-1] not in wrappers:
                offenders.append(line)
        assert offenders == []
        assert "debug_print(context," in function_source("debug_swallowed_exception")
        assert "debug_print(feature," in function_source("verbose_degraded_feature")


class TestEveryOutboundCallIsNamed:
    def test_a_scraped_page_names_the_address_the_timeout_and_the_result(self, debug_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor.req, "get", lambda url, **kwargs: FakeResponse(200, content=b"<html></html>"))
        monitor._lastfm_http_get_with_retry("https://www.last.fm/user/someuser/following")
        printed = capsys.readouterr().out
        assert "HTTP GET" in printed
        assert "url=https://www.last.fm/user/someuser/following" in printed
        assert "status=200" in printed
        assert "outcome=OK" in printed
        assert "timeout=" in printed

    def test_a_failed_page_names_the_transport_failure(self, debug_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor.req, "get", lambda url, **kwargs: (_ for _ in ()).throw(req.ConnectionError("no route to host")))
        monkeypatch.setattr(monitor.time, "sleep", lambda seconds: None)
        with pytest.raises(RuntimeError):
            monitor._lastfm_http_get_with_retry("https://www.last.fm/user/someuser/following", attempts=2)
        printed = capsys.readouterr().out
        assert "outcome=failed" in printed
        assert "ConnectionError" in printed

    def test_the_scrobble_fetch_names_the_user_and_what_came_back(self, debug_on, capsys):
        class Network:
            def get_user(self, username):
                return self

            def get_recent_tracks(self, limit=1):
                return ["one", "two"]

        monitor.lastfm_get_recent_tracks("someuser", Network(), 2)
        printed = capsys.readouterr().out
        assert "user=someuser" in printed
        assert "tracks=2" in printed
        assert "outcome=OK" in printed

    def test_a_rejected_scrobble_fetch_names_the_error(self, debug_on, capsys):
        class Network:
            def get_user(self, username):
                raise RuntimeError("Invalid API key")

        with pytest.raises(RuntimeError):
            monitor.lastfm_get_recent_tracks("someuser", Network(), 1)
        printed = capsys.readouterr().out
        assert "outcome=failed" in printed
        assert "RuntimeError" in printed


class TestNoFailureIsSwallowedSilently:
    # A handler that runs before the flags are resolved cannot print through them, and only those are exempt
    def test_no_broad_handler_stays_silent(self):
        exempt = {"apply_early_output_config", "_config_template_defaults", "clear_screen"}
        reporters = ("debug_print", "debug_swallowed_exception", "verbose_print", "verbose_notice", "verbose_degraded_feature", "print", "print_recovery_error")
        # A handler that classifies its failure hands the report to the caller, which prints it as a check or a block
        classifiers = ("classify_recovery_error", "make_recovery_advice", "make_doctor_check")
        functions = [(node.lineno, node.end_lineno or node.lineno, node.name) for node in ast.walk(TREE) if isinstance(node, ast.FunctionDef)]
        offenders = []
        for node in ast.walk(TREE):
            if not (isinstance(node, ast.ExceptHandler) and node.type and ast.unparse(node.type) == "Exception"):
                continue
            owners = [name for start, end, name in functions if start <= node.lineno <= end]
            if owners and owners[-1] in exempt:
                continue
            called = {getattr(inner.func, "id", "") for inner in ast.walk(node) if isinstance(inner, ast.Call)}
            reported = bool(called & set(reporters + classifiers)) or any(isinstance(inner, ast.Raise) for inner in ast.walk(node))
            # A handler that only records the failure falls through to the block that reports it
            funnels_into_a_shared_report = all(isinstance(statement, ast.Assign) for statement in node.body)
            if not reported and not funnels_into_a_shared_report:
                offenders.append(node.lineno)
        assert offenders == []

    def test_a_webhook_rate_limit_header_that_cannot_be_read_is_named(self, debug_on, capsys):
        assert monitor.webhook_retry_after_seconds(FakeResponse(429, headers={"Retry-After": "not a number"})) == monitor.WEBHOOK_FALLBACK_RETRY_SECONDS
        assert "outcome=failed" in capsys.readouterr().out

    def test_a_track_link_that_cannot_be_read_is_named(self, debug_on, capsys):
        class Track:
            def get_url(self):
                raise RuntimeError("Last.fm rejected the request")

        urls = monitor.get_spotify_apple_genius_search_urls("Artist", "Track", track_obj=Track())
        printed = capsys.readouterr().out
        assert urls[11].endswith("/Artist/_/Track")
        assert "outcome=failed" in printed
        assert "RuntimeError" in printed


class TestADegradedFeatureSaysSoInVerbose:
    # Silence here is indistinguishable from nothing to report, which is the whole bug
    def test_a_tracked_list_that_could_not_be_read_says_which_alert_cannot_fire(self, verbose_on, monkeypatch, tmp_path, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(monitor, "lastfm_get_friends", lambda username: (_ for _ in ()).throw(RuntimeError("Last.fm returned HTTP 503")))
        monitor.check_friends_changes("someuser", track_followings=True, track_followers=False, save_state=False)
        printed = capsys.readouterr().out
        assert "followings" in printed.casefold()
        assert "*" in printed

    def test_the_same_failure_names_its_cause_in_debug(self, debug_on, monkeypatch, tmp_path, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(monitor, "lastfm_get_friends", lambda username: (_ for _ in ()).throw(RuntimeError("Last.fm returned HTTP 503")))
        monitor.check_friends_changes("someuser", track_followings=True, track_followers=False, save_state=False)
        printed = capsys.readouterr().out
        assert "outcome=degraded" in printed or "outcome=failed" in printed
        assert "RuntimeError" in printed

    # A channel switched off at startup is a decision the user can act on, so it is said once in verbose
    def test_an_unusable_email_channel_names_the_setting_that_fixes_it(self, restored_globals, tmp_path, capsys):
        run_main_to_the_loop(tmp_path, arguments=["--verbose"])
        printed = capsys.readouterr().out
        assert "* Email notifications are off because SMTP_HOST is still the shipped placeholder" in printed

    def test_an_unusable_email_channel_stays_quiet_without_the_flag(self, restored_globals, tmp_path, capsys):
        run_main_to_the_loop(tmp_path)
        assert "Email notifications are off because" not in capsys.readouterr().out


class TestEveryDeliveryIsTraced:
    def test_a_delivered_email_is_confirmed_rather_than_only_announced(self, debug_on, monkeypatch, capsys):
        sent = []

        class Session:
            def sendmail(self, sender, receiver, message):
                sent.append(receiver)

            def quit(self):
                pass

        monkeypatch.setattr(monitor, "SMTP_HOST", "mail.example.com")
        monkeypatch.setattr(monitor, "SMTP_PORT", 587)
        monkeypatch.setattr(monitor, "SMTP_USER", "someuser")
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "not-a-real-password")
        monkeypatch.setattr(monitor, "SENDER_EMAIL", "from@example.com")
        monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "to@example.com")
        monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda use_ssl, smtp_timeout=15: Session())
        assert monitor.send_email("Subject", "Body", "", False) == 0
        printed = capsys.readouterr().out
        assert sent == ["to@example.com"]
        assert "host=mail.example.com" in printed
        assert "outcome=OK" in printed

    def test_a_refused_email_names_the_server_and_the_cause(self, debug_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "SMTP_HOST", "mail.example.com")
        monkeypatch.setattr(monitor, "SMTP_PORT", 587)
        monkeypatch.setattr(monitor, "SMTP_USER", "someuser")
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "not-a-real-password")
        monkeypatch.setattr(monitor, "SENDER_EMAIL", "from@example.com")
        monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "to@example.com")
        monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda use_ssl, smtp_timeout=15: (_ for _ in ()).throw(OSError("connection refused")))
        assert monitor.send_email("Subject", "Body", "", False) == 1
        printed = capsys.readouterr().out
        assert "host=mail.example.com" in printed
        assert "outcome=failed" in printed
        assert "OSError" in printed

    def test_a_delivered_email_names_where_it_went_in_verbose(self, verbose_on, monkeypatch, capsys):
        class Session:
            def sendmail(self, sender, receiver, message):
                pass

            def quit(self):
                pass

        monkeypatch.setattr(monitor, "SMTP_HOST", "mail.example.com")
        monkeypatch.setattr(monitor, "SMTP_PORT", 587)
        monkeypatch.setattr(monitor, "SMTP_USER", "someuser")
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "not-a-real-password")
        monkeypatch.setattr(monitor, "SENDER_EMAIL", "from@example.com")
        monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "to@example.com")
        monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda use_ssl, smtp_timeout=15: Session())
        assert monitor.send_email("Now playing", "Body", "", False) == 0
        assert "* Email delivered to to@example.com: Now playing" in capsys.readouterr().out

    def test_a_delivered_webhook_names_the_provider_and_the_alert_in_verbose(self, verbose_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://example.com/hooks/abc")
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
        monkeypatch.setattr(monitor, "post_webhook_request", lambda **kwargs: FakeResponse(204))
        assert monitor.send_webhook("Now playing", "Description", "song", force=True) == 0
        assert "* Webhook delivered through discord: Now playing" in capsys.readouterr().out

    def test_every_webhook_attempt_names_its_status_and_the_retry_delay(self, debug_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://example.com/hooks/abc")
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
        monkeypatch.setattr(monitor, "post_webhook_request", lambda **kwargs: FakeResponse(500))
        waits = []
        assert monitor.send_webhook("Title", "Description", "song", force=True, sleeper=waits.append) == 1
        printed = capsys.readouterr().out
        assert "host=example.com" in printed
        assert "status=500" in printed
        assert "outcome=failed" in printed
        assert waits and f"delay={waits[0]:g}s" in printed

    def test_a_delivered_webhook_is_confirmed(self, debug_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://example.com/hooks/abc")
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
        monkeypatch.setattr(monitor, "post_webhook_request", lambda **kwargs: FakeResponse(204))
        assert monitor.send_webhook("Title", "Description", "song", force=True) == 0
        printed = capsys.readouterr().out
        assert "status=204" in printed
        assert "outcome=OK" in printed

    # The destination is traced by host alone, never by the private URL a webhook carries
    def test_the_webhook_trace_never_carries_the_private_url(self, debug_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://example.com/hooks/private-token-value")
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
        monkeypatch.setattr(monitor, "post_webhook_request", lambda **kwargs: FakeResponse(204))
        monitor.send_webhook("Title", "Description", "song", force=True)
        assert "private-token-value" not in capsys.readouterr().out

    def test_each_channel_reports_its_own_outcome(self, debug_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: 1)
        monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: 0)
        monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "to@example.com")
        monitor.send_notification_channels("song", "Subject", "Body", email_enabled=True, webhook_enabled=True)
        printed = capsys.readouterr().out
        assert "channel=email" in printed
        assert "channel=webhook" in printed
        assert "outcome=failed" in printed
        assert "outcome=OK" in printed


class TestEveryFileIsTraced:
    def test_a_written_csv_names_the_file_on_the_way_in(self, debug_on, tmp_path, capsys):
        csv_path = tmp_path / "played.csv"
        monitor.init_csv_file(str(csv_path))
        monitor.write_csv_entry(str(csv_path), "2026-09-08 10:00:00", "Artist", "Track", "Album")
        printed = capsys.readouterr().out
        assert str(csv_path) in printed
        assert printed.count("outcome=OK") >= 2

    def test_a_csv_that_cannot_be_written_names_the_failure(self, debug_on, tmp_path, capsys):
        missing = tmp_path / "no-such-directory" / "played.csv"
        with pytest.raises(RuntimeError):
            monitor.write_csv_entry(str(missing), "2026-09-08 10:00:00", "Artist", "Track", "Album")
        printed = capsys.readouterr().out
        assert "outcome=failed" in printed
        assert str(missing) in printed

    def test_a_state_file_is_named_on_both_branches(self, debug_on, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monitor.save_friends_state("someuser", "followings", {"one", "two"})
        assert monitor.load_friends_state("someuser", "followings") == {"one", "two"}
        printed = capsys.readouterr().out
        assert "lastfm_someuser_followings.json" in printed
        assert printed.count("outcome=OK") >= 2


class TestEveryWaitIsTraced:
    # An idle-looking tool has to be tellable apart from a hung one
    def test_a_retry_names_its_delay_and_its_reason(self, debug_on, monkeypatch, capsys):
        waits = []
        monkeypatch.setattr(monitor.time, "sleep", waits.append)
        monkeypatch.setattr(monitor.req, "get", lambda url, **kwargs: FakeResponse(503, headers={"Content-Type": "application/json"}))
        with pytest.raises(RuntimeError):
            monitor._lastfm_http_get_with_retry("https://www.last.fm/user/someuser", attempts=2, base_delay=1.0)
        printed = capsys.readouterr().out
        assert waits == [1.0]
        assert "delay=1s" in printed
        assert "status=503" in printed


class TestConfigAndSecretsAreTraced:
    def test_the_configuration_load_names_the_file_and_how_much_it_applied(self, debug_on, tmp_path, capsys):
        config_path = tmp_path / "lastfm.conf"
        config_path.write_text('LASTFM_CHECK_INTERVAL = 30\nTRACK_SONGS = True\n', encoding="utf-8")
        namespace = {}
        assert monitor.load_config_file(str(config_path), namespace=namespace) is True
        printed = capsys.readouterr().out
        assert str(config_path) in printed
        assert "settings=2" in printed
        assert "outcome=OK" in printed

    def test_a_configuration_file_that_failed_says_so_in_the_same_grammar(self, debug_on, tmp_path, capsys):
        config_path = tmp_path / "lastfm.conf"
        config_path.write_text("LASTFM_CHECK_INTERVAL = (\n", encoding="utf-8")
        assert monitor.load_config_file(str(config_path), namespace={}, report_errors=False) is False
        assert "outcome=failed" in capsys.readouterr().out

    # The redaction pass strips everything after a secret name followed by =, which ate the rest of this line
    def test_the_grouped_trace_survives_the_redaction_pass(self, restored_globals, tmp_path, capsys):
        run_main_to_the_loop(tmp_path, ["--debug"])
        grouped = [line for line in capsys.readouterr().out.splitlines() if "Secret sources" in line]
        assert grouped
        assert grouped[0].endswith("Secret sources: source=config file, names=LASTFM_API_KEY LASTFM_API_SECRET")

    def test_each_secret_names_where_it_resolved_from(self, debug_on, restored_globals, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", API_KEY)
        monitor.record_secret_source("LASTFM_API_KEY", "config file")
        printed = capsys.readouterr().out
        assert "name=LASTFM_API_KEY" in printed
        assert "source=config file" in printed
        assert API_KEY not in printed


class FakeClock:
    def __init__(self, start=1757000000):
        self.now = start

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += int(seconds)


class FakeTrack:
    def __init__(self, artist="Artist", title="Track"):
        self.artist = artist
        self.title = title
        self.info = {"album": ""}

    def __eq__(self, other):
        return isinstance(other, FakeTrack) and (self.artist, self.title) == (other.artist, other.title)

    def __hash__(self):
        return hash((self.artist, self.title))

    def __str__(self):
        return f"{self.artist} - {self.title}"


class FakePlayed:
    def __init__(self, timestamp, track):
        self.timestamp = timestamp
        self.track = track
        self.album = ""


class FakeUser:
    def __init__(self, clock, scrobble, fail_after=None, recover_after=None, error_factory=None):
        self.clock = clock
        self.scrobble = scrobble
        self.fail_after = fail_after
        self.recover_after = recover_after
        self.error_factory = error_factory or (lambda call: RuntimeError("HTTP code 500 from Last.fm"))
        self.calls = 0

    def get_now_playing(self):
        return None

    def get_recent_tracks(self, limit=1):
        self.calls += 1
        failing = self.fail_after is not None and self.calls > self.fail_after and (self.recover_after is None or self.calls <= self.recover_after)
        if failing:
            raise self.error_factory(self.calls)
        return [FakePlayed(*self.scrobble)]


class FakeNetwork:
    def __init__(self, user):
        self.user = user

    def get_user(self, username):
        return self.user


# Runs the real monitoring loop on a fake clock advanced by each patched sleep and returns what it printed
def drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles, check_interval=30, liveness=0, fail_after=None, fail_recover_after=None, error_factory=None, friends_fail_after=None, friends_recover_after=None, friends_failing_calls=None, stub_notifications=True):
    if friends_failing_calls is not None:
        friends_fail_after = 0

    clock = FakeClock()
    user = FakeUser(clock, (clock.now - 600, FakeTrack()), fail_after=fail_after, recover_after=fail_recover_after, error_factory=error_factory)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "time", clock)
    monkeypatch.setattr(monitor, "LASTFM_CHECK_INTERVAL", check_interval)
    monkeypatch.setattr(monitor, "LASTFM_ACTIVE_CHECK_INTERVAL", 10)
    monkeypatch.setattr(monitor, "LASTFM_INACTIVITY_CHECK", 180)
    monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", liveness)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", liveness)
    monkeypatch.setattr(monitor, "TRACK_FOLLOWINGS", friends_fail_after is not None)
    monkeypatch.setattr(monitor, "FRIENDS_CHECK_INTERVAL", check_interval if friends_fail_after is not None else 0)
    monkeypatch.setattr(monitor, "FRIENDS_RETRY_INTERVAL", check_interval)
    monkeypatch.setattr(monitor, "FRIENDS_CHANGE_COUNTER", 3)
    monkeypatch.setattr(monitor, "TRACK_FOLLOWERS", False)
    monkeypatch.setattr(monitor, "TRACK_BIO", False)
    monkeypatch.setattr(monitor, "TRACK_DISPLAY_NAME", False)
    monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", False)
    monkeypatch.setattr(monitor, "PROGRESS_INDICATOR", False)
    monkeypatch.setattr(monitor, "TRACK_SONGS", False)
    monkeypatch.setattr(monitor, "get_track_info", lambda *a, **k: (0, None, ""))
    monkeypatch.setattr(monitor, "get_spotify_apple_genius_search_urls", lambda *a, **k: tuple([""] * 13))
    if stub_notifications:
        monkeypatch.setattr(monitor, "send_notification_channels", lambda *a, **k: (False, False))

    if friends_fail_after is not None:
        friends_calls = count(1)

        def failing_friends(_username):
            call = next(friends_calls)
            if friends_failing_calls is not None:
                failing = call in friends_failing_calls
            else:
                failing = call > friends_fail_after and (friends_recover_after is None or call <= friends_recover_after)
            if failing:
                raise RuntimeError("Cannot read the friends list")
            return {"someone"}

        monkeypatch.setattr(monitor, "lastfm_get_friends", failing_friends)

    deadline = clock.now + (cycles - 1) * check_interval
    plain_sleep = clock.sleep

    def stopping_sleep(seconds):
        plain_sleep(seconds)
        if clock.now > deadline:
            raise KeyboardInterrupt

    clock.sleep = stopping_sleep
    capsys.readouterr()
    with pytest.raises((KeyboardInterrupt, SystemExit)):
        monitor.lastfm_monitor_user(user, FakeNetwork(user), "someuser", [], "")
    return capsys.readouterr().out


class TestEveryCompletedCheckIsTraced:
    # Coverage of failures alone makes a healthy run indistinguishable from a hung one
    def test_each_finished_cycle_names_the_target_and_what_it_found(self, debug_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=4)
        completed = [line for line in transcript.splitlines() if "Completed check" in line]
        assert len(completed) == 4
        assert "check=#1" in completed[0]
        assert "check=#4" in completed[3]
        assert "user=someuser" in completed[0]
        assert "state=offline" in completed[0]
        assert "outcome=OK" in completed[0]

    def test_the_wait_between_checks_names_its_interval(self, debug_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=2, check_interval=45)
        assert "Waiting for the next check" in transcript
        assert "interval=45s" in transcript
        assert "reason=the user is offline" in transcript

    # The failure handler and the healthy path share one completed-check line, so without a result the trace
    # reads the same either way and the wait after a failure looks like an ordinary polling pause
    def test_a_failed_cycle_reports_its_result_and_names_what_the_wait_is_for(self, debug_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=4, liveness=3600, fail_after=2)
        completed = [line for line in transcript.splitlines() if "Completed check" in line]

        assert "outcome=OK" in completed[0]
        assert "outcome=failed" in completed[-1]
        assert "reason=the last check failed" in transcript

    # On a 30-second interval a per-check verbose line is 120 identical lines an hour, so it belongs in debug
    def test_a_quiet_run_prints_nothing_periodic_in_verbose(self, verbose_on, monkeypatch, tmp_path, capsys):
        short_run = tmp_path / "short"
        long_run = tmp_path / "long"
        short_run.mkdir()
        long_run.mkdir()
        after_three = drive_quiet_cycles(monkeypatch, capsys, short_run, cycles=3)
        after_twelve = drive_quiet_cycles(monkeypatch, capsys, long_run, cycles=12)
        assert "Completed check" not in after_twelve
        assert after_twelve == after_three

    # The liveness banner is what answers "is it alive", on its own cadence rather than once per check
    def test_the_liveness_banner_still_reports_on_its_own_cadence(self, verbose_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=10, check_interval=30, liveness=120)
        assert transcript.count("Monitoring healthy for someuser") == 2


class TestARunThatIsRetryingSaysSo:
    # A first failure that waits for a threshold makes the first half hour of an outage look like an idle run
    def test_the_first_failure_is_reported_at_once_with_its_schedule(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=4, liveness=3600, fail_after=2)
        reports = [line for line in transcript.splitlines() if line.startswith("* Error:")]
        assert len(reports) == 1
        assert reports[0] == "* Error: The Last.fm API is temporarily unavailable (retrying in 30 seconds)"

    # A report with no timestamp under it cannot be placed in the run it came from
    def test_the_report_carries_the_fix_and_the_timestamp_trailer(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=4, liveness=3600, fail_after=2).splitlines()
        index = next(number for number, line in enumerate(transcript) if line.startswith("* Error:"))
        assert transcript[index + 1].startswith("To fix: ")
        assert transcript[index + 2].startswith("Guide: ")
        assert transcript[index + 3].startswith("Timestamp:")

    def test_the_same_failure_names_the_cycle_and_the_cause_in_debug(self, debug_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=4, fail_after=2)
        failures = [line for line in transcript.splitlines() if "Monitoring cycle" in line]
        assert failures
        assert "outcome=failed" in failures[0]
        assert "RuntimeError" in failures[0]


class TestAVerboseNoticeNeverFloats:
    # A line with no timestamp under it cannot be placed in time, and a degraded feature is exactly when that matters
    def test_a_degraded_feature_notice_is_closed_before_the_next_check(self, verbose_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=4, friends_fail_after=1).splitlines()
        notices = [number for number, line in enumerate(transcript) if "cannot fire" in line]
        assert len(notices) == 1
        assert transcript[notices[0] + 1].startswith("Timestamp:")

    # Closing on the notice line would print a trailer of its own right before the block that follows it
    def test_a_real_block_in_the_same_check_absorbs_the_notice(self, verbose_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=3, liveness=30, friends_fail_after=1).splitlines()
        index = next(number for number, line in enumerate(transcript) if "cannot fire" in line)
        assert transcript[index + 1].startswith("* Monitoring healthy")
        assert transcript[index + 2].startswith("Liveness check, timestamp:")
        assert not any(line.startswith("Timestamp:") for line in transcript[index + 1:index + 3])

    def test_the_helper_leaves_the_close_to_the_check(self, verbose_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "MONITORING_ACTIVE", True)
        monkeypatch.setattr(monitor, "PENDING_NOTICE_BLOCK", False)
        monitor.verbose_degraded_feature("Followings check", "following change alerts")
        assert "Timestamp:" not in capsys.readouterr().out
        assert monitor.PENDING_NOTICE_BLOCK is True
        monitor.close_pending_notice_block()
        assert capsys.readouterr().out.startswith("Timestamp:")

    # One trailer belongs to the check, not to each feature that failed during it
    def test_two_degraded_features_share_one_trailer(self, verbose_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "MONITORING_ACTIVE", True)
        monkeypatch.setattr(monitor, "PENDING_NOTICE_BLOCK", False)
        monitor.verbose_degraded_feature("Followings check", "following change alerts")
        monitor.verbose_degraded_feature("Followers check", "follower change alerts")
        monitor.close_pending_notice_block()
        assert capsys.readouterr().out.count("Timestamp:") == 1

    def test_a_block_that_closes_itself_leaves_nothing_pending(self, verbose_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "MONITORING_ACTIVE", True)
        monkeypatch.setattr(monitor, "PENDING_NOTICE_BLOCK", False)
        monitor.verbose_degraded_feature("Followings check", "following change alerts")
        monitor.print_cur_ts("Timestamp:\t\t\t")
        monitor.close_pending_notice_block()
        assert capsys.readouterr().out.count("Timestamp:") == 1

    # The startup screen is one block that the monitoring header closes, so a trailer there would split it in half
    def test_a_notice_before_monitoring_starts_stays_bare(self, verbose_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "MONITORING_ACTIVE", False)
        monkeypatch.setattr(monitor, "PENDING_NOTICE_BLOCK", False)
        monitor.verbose_degraded_feature("Followings check", "following change alerts")
        monitor.close_pending_notice_block()
        printed = capsys.readouterr().out
        assert "cannot fire" in printed
        assert "Timestamp:" not in printed

    def test_a_check_with_no_notice_prints_no_trailer_of_its_own(self, verbose_on, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "PENDING_NOTICE_BLOCK", False)
        monitor.close_pending_notice_block()
        assert capsys.readouterr().out == ""

    # A silent retry window reads as a run that stopped checking, so the first failure has to name what cannot fire
    def test_the_silent_retry_window_names_the_alerts_it_cannot_fire(self, verbose_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=4, friends_fail_after=1)
        notices = [line for line in transcript.splitlines() if "cannot fire" in line]
        assert len(notices) == 1
        assert notices[0].startswith("* Friends/profile check is unavailable")
        assert "friend and profile change alerts" in notices[0]

    def test_the_same_outage_repeats_only_in_debug(self, debug_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=6, friends_fail_after=1)
        lines = transcript.splitlines()
        degraded = [line for line in lines if "outcome=degraded" in line]
        assert len(degraded) == 1
        assert "alert=friend and profile change alerts" in degraded[0]
        repeats = [line for line in lines if "Friends/profile check" in line and "outcome=failed" in line]
        assert len(repeats) > 1
        assert "attempt=#2" in repeats[0]
        assert "RuntimeError" in repeats[0]


class TestARecoveryIsNewsOnlyIfTheFailureWas:
    # A recovery for a failure the reader never saw explains nothing and reads as an event of its own
    def test_the_recovery_follows_a_notice_the_reader_saw(self, verbose_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=5, friends_fail_after=1, friends_recover_after=3).splitlines()
        assert len([line for line in transcript if "cannot fire" in line]) == 1
        recovered = [number for number, line in enumerate(transcript) if "available again" in line]
        assert len(recovered) == 1
        assert transcript[recovered[0]].startswith("* Friends/profile check is available again")
        assert transcript[recovered[0] + 1].startswith("Timestamp:")

    def test_a_failure_nobody_saw_recovers_quietly(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=5, friends_fail_after=1, friends_recover_after=3)
        assert "cannot fire" not in transcript
        assert "available again" not in transcript

    # The threshold error line is printed whatever the mode, so its recovery has to be too
    def test_an_error_the_run_printed_gets_its_recovery_without_verbose(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=6, friends_fail_after=1, friends_recover_after=4)
        assert "Cannot confirm the friend and profile state (attempt 3)" in transcript
        assert transcript.count("* Friends/profile check is available again") == 1

    # Whatever verbose stops printing, debug still has to carry, or a support transcript loses the recovery
    def test_the_recovery_is_traced_even_when_it_is_not_printed(self, debug_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=5, friends_fail_after=1, friends_recover_after=3)
        recovered = [line for line in transcript.splitlines() if "Friends/profile check" in line and "outcome=OK" in line]
        assert len(recovered) == 1
        assert "failures=2" in recovered[0]

    # A second outage nobody saw must not inherit the first one's announcement
    def test_the_announcement_does_not_carry_into_the_next_outage(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=9, friends_failing_calls={2, 3, 4, 6, 7})
        assert transcript.count("Cannot confirm the friend and profile state (attempt 3)") == 1
        assert transcript.count("* Friends/profile check is available again") == 1

    def test_a_run_that_never_failed_says_nothing_about_recovering(self, verbose_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=5, friends_fail_after=99)
        assert "available again" not in transcript


# Raises one failure category for the first run of failing checks and another one after it
def two_category_failure(call):
    return RuntimeError("HTTP code 500 from Last.fm") if call <= 8 else RuntimeError("The read operation timed out")


# Records every alert the loop hands to the delivery helper and answers with the outcome each call is given
def recording_channels(monkeypatch, outcomes):
    calls = []

    def record(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None, **kwargs):
        calls.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html, "email": bool(email_enabled), "webhook": bool(webhook_enabled)})
        return outcomes[min(len(calls), len(outcomes)) - 1]

    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "send_notification_channels", record)
    return calls


class TestAMonitoringFailureAlertsBothChannels:
    # A failure the tool can retry away is alerted only once the outage has lasted the alert delay, so a blip of a
    # few checks reaches nobody while a real outage still does
    @pytest.mark.parametrize("cycles,expected", [(5, []), (6, [(True, True)])])
    def test_a_retryable_failure_is_alerted_once_the_outage_has_lasted(self, monkeypatch, tmp_path, capsys, cycles, expected):
        calls = recording_channels(monkeypatch, [(True, True)])
        # The startup snapshot takes two calls, so the loop fails from its first check and thirty seconds apart
        # the fifth failing check is the first to reach two minutes
        drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=cycles, liveness=3600, fail_after=2, stub_notifications=False)
        errors = [call for call in calls if call["type"] == "error"]
        assert [(call["email"], call["webhook"]) for call in errors] == expected

    # A failure nothing here can retry away is alerted on the first check, since waiting would change nothing
    def test_a_failure_that_cannot_clear_itself_is_alerted_at_once(self, monkeypatch, tmp_path, capsys):
        calls = recording_channels(monkeypatch, [(True, True)])
        drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=3, liveness=3600, fail_after=2, error_factory=lambda call: RuntimeError("Invalid API key - You must be granted a valid key by last.fm"), stub_notifications=False)
        errors = [call for call in calls if call["type"] == "error"]
        assert [call["subject"] for call in errors] == ["lastfm_monitor: API key error! (user: someuser)"]

    # An outage used to reach the webhook but not email, which only heard about a rejected API key
    def test_any_failure_alerts_both_channels_once(self, monkeypatch, tmp_path, capsys):
        calls = recording_channels(monkeypatch, [(True, True)])
        drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=8, liveness=3600, fail_after=2, stub_notifications=False)
        errors = [call for call in calls if call["type"] == "error"]
        assert [(call["email"], call["webhook"]) for call in errors] == [(True, True)]
        assert errors[0]["subject"] == "lastfm_monitor: monitoring error (user: someuser)"
        assert "The Last.fm API is temporarily unavailable" in errors[0]["body"]
        assert "To fix:" in errors[0]["body"]

    # The guide link sits under the fix in both bodies, since HTML renders the newline the fix carries as a space
    def test_the_guide_link_keeps_its_own_line_in_the_html_body(self, monkeypatch, tmp_path, capsys):
        calls = recording_channels(monkeypatch, [(True, True)])
        drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=8, liveness=3600, fail_after=2, stub_notifications=False)
        error = next(call for call in calls if call["type"] == "error")
        text_lines = error["body"].splitlines()
        html_lines = error["body_html"].removeprefix("<html><head></head><body>").removesuffix("</body></html>").split("<br>")
        fix_index = next(index for index, line in enumerate(text_lines) if line.startswith("To fix: "))
        assert text_lines[fix_index + 1].startswith("Guide: https://")
        assert html_lines[fix_index] == escape(text_lines[fix_index])
        assert html_lines[fix_index + 1] == text_lines[fix_index + 1]

    # A failure that changes category is a different failure, so it earns each channel a new alert
    def test_a_changed_failure_category_earns_a_new_alert(self, monkeypatch, tmp_path, capsys):
        calls = recording_channels(monkeypatch, [(True, True)])
        drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=14, liveness=3600, fail_after=1, error_factory=two_category_failure, stub_notifications=False)
        errors = [call for call in calls if call["type"] == "error"]
        assert len(errors) == 2
        assert "temporarily unavailable" in errors[0]["body"]
        assert "timed out" in errors[1]["body"]

    # Each channel is tracked on its own, so the one that failed is retried while the one that landed is left alone
    def test_a_failed_channel_is_retried_and_a_delivered_one_is_not(self, monkeypatch, tmp_path, capsys):
        calls = recording_channels(monkeypatch, [(True, False), (False, True)])
        drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=8, liveness=3600, fail_after=2, stub_notifications=False)
        errors = [call for call in calls if call["type"] == "error"]
        assert [(call["email"], call["webhook"]) for call in errors] == [(True, True), (False, True)]

    # A run that recovered and fails again is in a new outage, which deserves its own alert
    def test_a_new_outage_after_a_recovery_alerts_again(self, monkeypatch, tmp_path, capsys):
        calls = recording_channels(monkeypatch, [(True, True)])
        fetches = count(1)
        real_fetch = monitor.lastfm_get_recent_tracks

        def twice_failing_fetch(*args, **kwargs):
            if next(fetches) in (3, 4, 5, 6, 7, 10, 11, 12, 13, 14):
                raise RuntimeError("HTTP code 500 from Last.fm")
            return real_fetch(*args, **kwargs)

        monkeypatch.setattr(monitor, "lastfm_get_recent_tracks", twice_failing_fetch)
        drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=13, liveness=3600, stub_notifications=False)
        errors = [call for call in calls if call["type"] == "error"]
        assert [(call["email"], call["webhook"]) for call in errors] == [(True, True), (True, True)]


class TestALastingFailureIsReportedOnce:
    # At a 30 second interval a two day outage used to be 5760 identical blocks
    def test_the_same_failure_does_not_repeat_while_it_lasts(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=12, liveness=3600, fail_after=2)
        assert len([line for line in transcript.splitlines() if line.startswith("* Error:")]) == 1

    # The banner is what says a broken run is still alive, and it carries more than the line it replaced
    def test_a_lasting_failure_is_carried_by_the_liveness_banner(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=20, liveness=120, fail_after=2).splitlines()
        degraded = [number for number, line in enumerate(transcript) if line.startswith("* Monitoring degraded for someuser.")]
        assert len(degraded) == 4
        assert "The Last.fm API is temporarily unavailable since " in transcript[degraded[0]]
        assert transcript[degraded[0] + 1].startswith("Liveness check, timestamp:")

    # A healthy banner during an outage would say the opposite of what the run is doing
    def test_the_healthy_banner_stays_away_while_the_run_is_degraded(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=20, liveness=120, fail_after=2)
        assert "Monitoring healthy for someuser" not in transcript

    # A throttled failure stops printing, so nothing marks the moment it cleared unless the recovery says so
    def test_the_recovery_is_reported_without_any_flag(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=10, liveness=3600, fail_after=2, fail_recover_after=6).splitlines()
        recovered = [number for number, line in enumerate(transcript) if line.startswith("* Monitoring recovered for someuser after ")]
        assert len(recovered) == 1
        assert transcript[recovered[0] + 1].startswith("Timestamp:")

    # Without a reset the recovery line is followed at once by a banner, since the timer ran through the whole outage
    def test_the_recovery_starts_the_quiet_period_again(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=10, liveness=120, fail_after=2, fail_recover_after=6).splitlines()
        recovered = next(number for number, line in enumerate(transcript) if line.startswith("* Monitoring recovered"))
        healthy = next(number for number, line in enumerate(transcript) if line.startswith("* Monitoring healthy"))
        # Without the reset the banner arrives in the same check as the recovery, sharing its timestamp
        assert transcript[healthy + 1].split("\t")[-1] != transcript[recovered + 1].split("\t")[-1]

    def test_a_second_failure_category_is_reported_in_full(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=10, liveness=3600, fail_after=2, error_factory=two_category_failure)
        reports = [line for line in transcript.splitlines() if line.startswith("* Error:")]
        assert len(reports) == 2
        assert "temporarily unavailable" in reports[0]
        assert "timed out" in reports[1]
        assert transcript.count("To fix: ") == 2

    # With the banner switched off nothing is left to carry the reminder, so the old summaries keep their cadence
    def test_the_aggregated_summary_survives_where_the_banner_is_off(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        monkeypatch.setattr(monitor, "ERROR_500_NUMBER_LIMIT", 3)
        monkeypatch.setattr(monitor, "ERROR_500_TIME_LIMIT", 60)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=12, liveness=0, fail_after=2)
        aggregated = [line for line in transcript.splitlines() if line.startswith("* Error 50x (")]
        assert aggregated
        assert "The Last.fm API is temporarily unavailable (retrying in 30 seconds)" in aggregated[0]
        assert "Monitoring degraded for someuser" not in transcript

    # The probe that found the cadence bugs: a long outage read end to end rather than a two-check test
    def test_a_long_outage_prints_one_report_and_one_reminder(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=130, liveness=3600, fail_after=2)
        lines = transcript.splitlines()
        assert len([line for line in lines if line.startswith("* Error:")]) == 1
        assert len([line for line in lines if line.startswith("* Monitoring degraded")]) == 1

    def test_the_failure_and_its_category_stay_in_debug(self, debug_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=8, liveness=3600, fail_after=2)
        failures = [line for line in transcript.splitlines() if "Monitoring cycle" in line and "outcome=failed" in line]
        assert len(failures) > 1
