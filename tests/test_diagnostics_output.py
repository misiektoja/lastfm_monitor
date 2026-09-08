"""The verbose and debug printers: the grammar every debug line follows and the coverage each mode owes a user."""

import ast
import re
import sys
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


# The only place a user who never opens --help learns the two modes exist
class TestTheDefaultOutputNamesBothModes:
    def test_a_plain_run_says_where_more_detail_lives(self, restored_globals, tmp_path, capsys):
        run_main_to_the_loop(tmp_path)
        printed = capsys.readouterr().out
        assert "* More details:\t\t\tuse --verbose or --debug" in printed
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
    def test_an_unusable_email_channel_names_the_setting_that_fixes_it(self):
        assert 'verbose_print("Email notifications are off because SMTP_HOST is still the shipped placeholder")' in SOURCE


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
    def __init__(self, clock, scrobble, fail_after=None):
        self.clock = clock
        self.scrobble = scrobble
        self.fail_after = fail_after
        self.calls = 0

    def get_now_playing(self):
        return None

    def get_recent_tracks(self, limit=1):
        self.calls += 1
        if self.fail_after is not None and self.calls > self.fail_after:
            raise RuntimeError("HTTP code 500 from Last.fm")
        return [FakePlayed(*self.scrobble)]


class FakeNetwork:
    def __init__(self, user):
        self.user = user

    def get_user(self, username):
        return self.user


# Runs the real monitoring loop on a fake clock advanced by each patched sleep and returns what it printed
def drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles, check_interval=30, liveness=0, fail_after=None):
    clock = FakeClock()
    user = FakeUser(clock, (clock.now - 600, FakeTrack()), fail_after=fail_after)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "time", clock)
    monkeypatch.setattr(monitor, "LASTFM_CHECK_INTERVAL", check_interval)
    monkeypatch.setattr(monitor, "LASTFM_ACTIVE_CHECK_INTERVAL", 10)
    monkeypatch.setattr(monitor, "LASTFM_INACTIVITY_CHECK", 180)
    monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", liveness)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", liveness)
    monkeypatch.setattr(monitor, "TRACK_FOLLOWINGS", False)
    monkeypatch.setattr(monitor, "TRACK_FOLLOWERS", False)
    monkeypatch.setattr(monitor, "TRACK_BIO", False)
    monkeypatch.setattr(monitor, "TRACK_DISPLAY_NAME", False)
    monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", False)
    monkeypatch.setattr(monitor, "PROGRESS_INDICATOR", False)
    monkeypatch.setattr(monitor, "TRACK_SONGS", False)
    monkeypatch.setattr(monitor, "get_track_info", lambda *a, **k: (0, None, ""))
    monkeypatch.setattr(monitor, "get_spotify_apple_genius_search_urls", lambda *a, **k: tuple([""] * 13))
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *a, **k: (False, False))

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

    def test_the_wait_between_checks_names_its_interval(self, debug_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=2, check_interval=45)
        assert "Waiting for the next check" in transcript
        assert "interval=45s" in transcript

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
    # A streak below its alert threshold printed nothing at all, which reads as a run that stopped working
    def test_the_first_transient_failure_says_retries_are_active(self, verbose_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=4, fail_after=2)
        notices = [line for line in transcript.splitlines() if "automatic retries are active" in line.casefold()]
        assert len(notices) == 1
        assert notices[0].startswith("* ")

    # A bare notice between two timestamped blocks cannot be correlated with the events beside it
    def test_the_notice_carries_the_timestamp_trailer(self, verbose_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=4, fail_after=2).splitlines()
        index = next(number for number, line in enumerate(transcript) if "automatic retries are active" in line.casefold())
        assert transcript[index + 1].startswith("Timestamp:")

    def test_the_same_failure_names_the_cycle_and_the_cause_in_debug(self, debug_on, monkeypatch, tmp_path, capsys):
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=4, fail_after=2)
        failures = [line for line in transcript.splitlines() if "Monitoring cycle" in line]
        assert failures
        assert "outcome=failed" in failures[0]
        assert "RuntimeError" in failures[0]
