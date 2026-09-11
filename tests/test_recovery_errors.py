"""Recovery classification: the closed code set, the advice each failure produces and the block it renders."""

import ast
import inspect
import re
import sys
from pathlib import Path

import pylast
import pytest
import requests

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Returns the contexts the classifier branches on, so a typo in a call site cannot fall through to the runtime branch unnoticed
def routed_contexts():
    tree = ast.parse(inspect.getsource(monitor.classify_recovery_error))
    contexts = {"runtime"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or not isinstance(node.left, ast.Name) or node.left.id != "context":
            continue
        for comparator in node.comparators:
            values = comparator.elts if isinstance(comparator, (ast.Tuple, ast.List, ast.Set)) else [comparator]
            contexts.update(value.value for value in values if isinstance(value, ast.Constant) and isinstance(value.value, str))
    return contexts


# Returns the recovery codes the classifier can actually return, read from the branches themselves
def classifier_codes():
    tree = ast.parse(inspect.getsource(monitor.classify_recovery_error))
    codes = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else ""
        if name in ("advice", "make_recovery_advice") and isinstance(node.args[0], ast.Constant):
            codes.add(node.args[0].value)
    return codes


# Returns the codes the doctor rows build directly, which never pass through the classifier
def doctor_codes():
    source = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    codes = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith(("doctor_", "_doctor_")):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "make_recovery_advice" and inner.args and isinstance(inner.args[0], ast.Constant):
                codes.add(inner.args[0].value)
    return codes


# Returns the context every print_recovery_error call site passes, with the default filled in
def call_site_contexts():
    tree = ast.parse((PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8"))
    contexts = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "print_recovery_error":
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        context = keywords.get("context")
        if context is None:
            contexts.append("runtime")
        elif isinstance(context, ast.Constant):
            contexts.append(context.value)
        else:
            # A computed context is checked at runtime instead, by the closed set in make_recovery_advice
            contexts.append("runtime")
    return contexts


class TestTheClosedCodeSet:
    # A preflight row states a condition the classifier has no error to route on, so it builds its advice directly
    def test_every_declared_code_is_reachable(self):
        unreachable = monitor.RECOVERY_CODES - classifier_codes() - doctor_codes()
        assert unreachable == set(), f"codes nothing can return: {sorted(unreachable)}"

    def test_no_code_outside_the_set_is_produced(self):
        undeclared = (classifier_codes() | doctor_codes()) - monitor.RECOVERY_CODES
        assert undeclared == set(), f"codes returned but not declared: {sorted(undeclared)}"

    def test_the_preflight_codes_are_the_ones_the_classifier_cannot_reach(self):
        assert doctor_codes() - classifier_codes() == {"config.insecure", "dependency.missing"}

    # A call site that adds context used to replace the error text the rules read, so every such failure was unknown
    @pytest.mark.parametrize("message, expected", [
        ("User not found", "target.not_found"),
        ("Invalid API key - You must be granted a valid key by last.fm", "auth.api_key_invalid"),
        ("Login: User required to be logged in", "target.not_visible"),
        ("Connection timed out", "network.timeout"),
    ])
    def test_a_caller_supplied_detail_does_not_hide_the_error(self, message, expected):
        advice = monitor.classify_recovery_error(Exception(message), detail="Cannot read the recent tracks of 'someuser'")
        assert advice.code == expected
        assert "Cannot read the recent tracks" in advice.detail

    def test_an_unsupported_code_is_refused(self):
        with pytest.raises(ValueError):
            monitor.make_recovery_advice("lastfm.exploded", "summary", "fix", True)

    def test_every_call_site_names_a_context_the_classifier_routes_on(self):
        contexts = call_site_contexts()
        assert contexts, "print_recovery_error is never called"
        unknown = sorted(set(contexts) - routed_contexts())
        assert unknown == [], f"call sites pass contexts nothing routes on: {unknown}"


class TestLastfmStatusMapping:
    # Last.fm answers HTTP 200 and puts the real failure in a numeric code, so the code is what has to be read
    @pytest.mark.parametrize("status, expected", [
        ("17", "target.not_visible"),
        ("10", "auth.api_key_invalid"),
        ("13", "auth.api_key_invalid"),
        ("26", "auth.api_key_invalid"),
        ("29", "lastfm.rate_limited"),
        ("6", "target.not_found"),
        ("7", "target.not_found"),
        ("8", "lastfm.unavailable"),
        ("11", "lastfm.unavailable"),
        ("16", "lastfm.unavailable"),
    ])
    def test_a_web_service_error_is_classified_from_its_status(self, status, expected):
        error = pylast.WSError(None, status, "Something the API said")
        assert monitor.classify_recovery_error(error).code == expected

    # pylast raises the same class with an integer HTTP status when Last.fm returns 5xx
    def test_an_http_status_on_the_same_error_is_treated_as_an_outage(self):
        error = pylast.WSError(None, 503, "Connection to the API failed with HTTP code 503")
        assert monitor.classify_recovery_error(error).code == "lastfm.unavailable"

    def test_the_hidden_listening_history_names_the_privacy_setting(self):
        advice = monitor.classify_recovery_error(pylast.WSError(None, "17", "Login: User required to be logged in"))
        assert "recent listening" in advice.summary
        assert monitor.PRIVACY_GUIDE_URL in advice.fix

    def test_a_status_that_is_not_a_number_falls_through_to_the_message(self):
        assert monitor.recovery_lastfm_status(pylast.WSError(None, "not a code", "x")) is None
        assert monitor.classify_recovery_error(pylast.WSError(None, "not a code", "Invalid API key")).code == "auth.api_key_invalid"


class TestRetryability:
    @pytest.mark.parametrize("error, retryable", [
        (pylast.WSError(None, "29", "Rate limit exceeded"), True),
        (pylast.WSError(None, "16", "Temporarily unavailable"), True),
        (RuntimeError("the request timed out"), True),
        (RuntimeError("connection refused"), True),
        (pylast.WSError(None, "10", "Invalid API key"), False),
        (pylast.WSError(None, "17", "Login: User required to be logged in"), False),
        (pylast.WSError(None, "6", "User not found"), False),
    ])
    def test_retryable_marks_only_failures_that_waiting_can_clear(self, error, retryable):
        assert monitor.classify_recovery_error(error).retryable is retryable


class TestContextRouting:
    @pytest.mark.parametrize("context, detail, expected", [
        ("config", "Config file 'x.conf' does not exist", "config.missing"),
        ("config", "Config file 'x.conf' contains unsupported content: Line 1", "config.invalid"),
        ("target.missing", "No Last.fm username was given", "target.missing"),
        ("secret.missing", "LASTFM_API_KEY is empty", "secret.missing"),
        ("set_lastfm_credentials", "--set-lastfm-credentials requires an interactive terminal", "secret.entry"),
        ("set_webhook_url", "Webhook setup was cancelled. The dotenv file was not changed", "secret.entry"),
        ("set_webhook_url", "That does not look like a complete HTTPS webhook URL", "webhook.invalid"),
        ("set_spotify_credentials", "Could not save private values in '/x/.env'", "file.unwritable"),
        ("email", "The SMTP settings are incorrect (invalid port number in SMTP_PORT)", "smtp.invalid"),
        ("email", "authentication failed", "smtp.authentication"),
        ("email", "the host went away", "smtp.connection"),
        ("webhook", "WEBHOOK_URL must contain a complete HTTPS link", "webhook.invalid"),
        ("webhook", "the service is applying a rate limit", "webhook.rate_limited"),
        ("webhook", "The webhook service could not be reached (ConnectTimeout)", "webhook.connection"),
        ("webhook", "The webhook service returned HTTP 404", "webhook.rejected"),
        ("file", "Cannot load the last status from 'x.json'", "file.unreadable"),
        ("file", "the directory is read-only", "file.unwritable"),
    ])
    def test_a_context_and_its_detail_pick_the_expected_code(self, context, detail, expected):
        assert monitor.classify_recovery_error(context=context, detail=detail).code == expected

    # Refusing the dotenv destination is a choice the user made, not a permission the machine withheld
    def test_the_env_file_sentinel_is_not_reported_as_a_permissions_problem(self):
        advice = monitor.classify_recovery_error(context="set_webhook_url", detail="Private setup requires a dotenv destination and cannot use --env-file none")
        assert advice.code == "secret.entry"
        assert "--env-file none" in advice.fix
        assert "permissions" not in advice.fix

    @pytest.mark.parametrize("cause, expected", [(requests.Timeout("timed out"), "network.timeout"), (requests.ConnectionError("no route"), "network.unavailable")])
    def test_the_connectivity_check_is_classified_from_the_error_not_the_detail(self, cause, expected):
        assert monitor.classify_recovery_error(cause, context="connectivity").code == expected

    def test_an_unrecognized_failure_still_produces_advice(self):
        advice = monitor.classify_recovery_error(RuntimeError("something new"))
        assert advice.code == "unknown"
        assert advice.fix


    # A write failure often names a missing file, which must not be mistaken for a file the tool could not read
    @pytest.mark.parametrize("detail", ["Could not initialize CSV file '/x/y.csv': [Errno 2] No such file or directory", "The CSV file '/x/y.csv' cannot be opened for writing"])
    def test_a_write_failure_is_never_reported_as_unreadable(self, detail):
        advice = monitor.classify_recovery_error(context="file.unwritable", detail=detail)
        assert advice.code == "file.unwritable"
        assert advice.fix.startswith("Check that the directory exists and is writable, or choose another path")

    # Verifies a failed CSV write reports through the recovery block, since the monitoring loop carries on past it
    def test_no_csv_write_failure_prints_its_own_line(self):
        csv_writers = {"init_csv_file", "write_csv_entry"}
        offenders = []
        guarded = 0
        for node in ast.walk(ast.parse((PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Try) or (node.body[-1].end_lineno or node.body[0].lineno) - node.body[0].lineno > 6:
                continue
            if not any(isinstance(inner, ast.Call) and getattr(inner.func, "id", "") in csv_writers for statement in node.body for inner in ast.walk(statement)):
                continue
            guarded += 1
            offenders.extend(f"line {statement.lineno}" for handler in node.handlers for statement in handler.body if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and getattr(statement.value.func, "id", "") == "print")

        assert guarded >= 6, f"only {guarded} CSV writes are guarded, so this no longer covers them"
        assert not offenders, "CSV write failures reported outside the recovery block:\n" + "\n".join(offenders)

class TestRendering:
    def test_every_failure_renders_an_error_line_and_a_fix_line(self):
        rendered = monitor.render_recovery_error(pylast.WSError(None, "17", "Login: User required to be logged in"), debug=False)
        lines = rendered.splitlines()
        assert lines[0].startswith("* Error: ")
        assert lines[1].startswith("To fix: ")
        assert "Technical detail" not in rendered

    def test_the_technical_cause_appears_only_in_debug(self):
        error = pylast.WSError(None, "6", "User not found")
        assert "Technical detail: User not found" in monitor.render_recovery_error(error, debug=True)
        assert "Technical detail" not in monitor.render_recovery_error(error, debug=False)

    def test_a_guide_link_sits_on_its_own_line(self):
        advice = monitor.classify_recovery_error(pylast.WSError(None, "10", "Invalid API key"))
        assert advice.fix.splitlines()[-1] == f"Guide: {monitor.LASTFM_API_GUIDE_URL}"

    def test_print_recovery_error_writes_the_block_and_returns_the_advice(self, capsys):
        advice = monitor.print_recovery_error(context="target.missing", detail="No Last.fm username was given", debug=False)
        output = capsys.readouterr().out
        assert advice.code == "target.missing"
        assert output.splitlines()[0] == "* Error: No Last.fm username was given"
        assert output.splitlines()[1].startswith("To fix: ")

    # The advice has to survive the exception boundary unchanged, or a re-raise would be classified twice
    def test_a_recovery_error_carries_its_advice_through_unchanged(self):
        advice = monitor.classify_recovery_error(pylast.WSError(None, "29", "Rate limit exceeded"))
        assert monitor.classify_recovery_error(monitor.RecoveryError(advice)) == advice

    def test_the_original_cause_stays_attached_for_debug_output(self):
        cause = pylast.WSError(None, "29", "Rate limit exceeded")
        assert monitor.RecoveryError(monitor.classify_recovery_error(cause), cause).__cause__ is cause


# A real Last.fm key is 32 hex characters, so anything at that length has to be replaced wherever it appears
FULL_LENGTH_KEY = "lastfmapikey00000000000000000000"


class TestRedaction:
    def test_a_configured_secret_is_replaced_in_every_field(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", FULL_LENGTH_KEY)
        advice = monitor.make_recovery_advice("unknown", f"Failed with {FULL_LENGTH_KEY}", f"Retry with {FULL_LENGTH_KEY}", True, f"Sent {FULL_LENGTH_KEY}")
        assert FULL_LENGTH_KEY not in advice.summary + advice.fix + advice.detail
        assert advice.summary.count("<redacted>") == 1

    def test_a_classified_failure_does_not_echo_the_key_back(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", FULL_LENGTH_KEY)
        advice = monitor.classify_recovery_error(RuntimeError(f"rejected key {FULL_LENGTH_KEY}"))
        assert FULL_LENGTH_KEY not in advice.detail

    def test_a_full_length_secret_is_replaced_anywhere_it_appears(self, monkeypatch):
        monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "tk_ntfyaccesstoken00000000000000")
        assert "tk_ntfyaccesstoken00000000000000" not in monitor.sanitize_error_text("Delivery failed with tk_ntfyaccesstoken00000000000000")

    # A short configured password is also an ordinary word, so replacing it would corrupt the text it happens to appear in
    def test_a_short_secret_leaves_ordinary_text_untouched(self, monkeypatch):
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "lastfm")
        assert monitor.sanitize_error_text("Cannot read the recent tracks of 'lastfm_listener'") == "Cannot read the recent tracks of 'lastfm_listener'"

    # The shape patterns anchor on the setting name rather than the value, so a short password stays covered where it is actually exposed
    def test_a_short_secret_is_still_redacted_in_the_assignment_form(self, monkeypatch):
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "lastfm")
        assert monitor.sanitize_error_text("SMTP_PASSWORD = lastfm") == "SMTP_PASSWORD = <redacted>"

    def test_a_placeholder_is_never_treated_as_a_secret(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "your_lastfm_api_key")
        assert monitor.sanitize_error_text("still set to your_lastfm_api_key") == "still set to your_lastfm_api_key"

    # Replacing the shorter value first would leave the longer one half redacted and still readable
    def test_a_secret_containing_another_secret_is_replaced_whole(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", FULL_LENGTH_KEY)
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", f"{FULL_LENGTH_KEY}-and-more")
        assert monitor.sanitize_error_text(f"sent {FULL_LENGTH_KEY}-and-more") == "sent <redacted>"

    @pytest.mark.parametrize("key", monitor.SECRET_KEYS)
    def test_every_secret_setting_is_redacted_in_a_quoted_source_line(self, key):
        assert monitor.sanitize_error_text(f'{key} = "whatever-was-written-here"') == f"{key} = <redacted>"

    # This is the real path: a config file that fails to parse quotes its own offending line back to the terminal and the log
    def test_a_quoted_config_source_line_cannot_leak_a_password(self):
        detail = 'Config file \'x.conf\' has invalid Python syntax at line 1 | Source: SMTP_PASSWORD = "hunter2-not-a-real-password | Parser: unterminated string literal'
        assert "hunter2" not in monitor.classify_recovery_error(context="config", detail=detail).summary

    # spotipy authenticates the Spotify app with Basic while Spotify and ntfy carry Bearer, so both schemes have to be covered
    @pytest.mark.parametrize("scheme", ["Bearer", "bearer", "Basic", "basic"])
    def test_both_authorization_schemes_this_tool_sends_are_redacted(self, scheme):
        assert monitor.sanitize_error_text(f"Authorization: {scheme} c2VjcmV0LXZhbHVlLWhlcmU=") == f"Authorization: {scheme} <redacted>"

    def test_an_authorization_header_inside_a_dict_repr_is_redacted(self):
        assert "c2VjcmV0" not in monitor.sanitize_error_text("Sending POST request with Headers: {'Authorization': 'Basic c2VjcmV0LXZhbHVlLWhlcmU='}")

    # pylast signs every request, so the signature and the key travel as parameters
    @pytest.mark.parametrize("parameter", ["api_key", "api_sig", "sk", "token", "secret", "password"])
    def test_a_signed_request_parameter_is_redacted(self, parameter):
        assert monitor.sanitize_error_text(f"GET https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&{parameter}=8b1e5d2846af0b7c") == f"GET https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&{parameter}=<redacted>"

    def test_a_discord_webhook_url_is_redacted_even_when_it_is_not_the_configured_one(self):
        assert monitor.sanitize_error_text("posted to https://discord.com/api/webhooks/123456789/aBcDeFgHiJkLmNoPqRsTuVwXyZ") == "posted to <redacted>"

    def test_an_authorization_value_configured_in_webhook_headers_is_redacted(self, monkeypatch):
        monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"Authorization": "Bearer tk_ntfyaccesstoken00000000000000"})
        assert "tk_ntfyaccesstoken00000000000000" not in monitor.sanitize_error_text("header was Bearer tk_ntfyaccesstoken00000000000000")

    def test_known_secret_values_skips_anything_below_the_floor(self, monkeypatch):
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "short")
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", FULL_LENGTH_KEY)
        assert "short" not in monitor.known_secret_values()
        assert FULL_LENGTH_KEY in monitor.known_secret_values()


class TestRecoveryHintTracker:
    def test_the_first_failure_of_a_category_renders_and_the_repeat_does_not(self):
        tracker = monitor.RecoveryHintTracker()
        outage = monitor.classify_recovery_error(pylast.WSError(None, "16", "Temporarily unavailable"))
        assert tracker.should_render(outage) is True
        assert tracker.should_render(outage) is False

    def test_a_changed_category_renders_again(self):
        tracker = monitor.RecoveryHintTracker()
        outage = monitor.classify_recovery_error(pylast.WSError(None, "16", "Temporarily unavailable"))
        rejected = monitor.classify_recovery_error(pylast.WSError(None, "10", "Invalid API key"))
        tracker.should_render(outage)
        assert tracker.should_render(rejected) is True
        assert tracker.should_render(outage) is True

    def test_a_recurrence_after_a_good_cycle_renders_again(self):
        tracker = monitor.RecoveryHintTracker()
        outage = monitor.classify_recovery_error(pylast.WSError(None, "16", "Temporarily unavailable"))
        tracker.should_render(outage)
        tracker.reset()
        assert tracker.should_render(outage) is True


class TestTheOneShotRefusals:
    @pytest.fixture(autouse=True)
    # Startup assigns module globals, so the settings every later test reads are restored afterwards
    def restored_settings(self):
        snapshot = {name: value for name, value in vars(monitor).items() if isinstance(value, (str, int, float, bool, type(None)))}
        yield
        for name, value in snapshot.items():
            setattr(monitor, name, value)

    # Verifies a malformed credential pair says what shape the value has to take instead of naming the settings
    def test_a_malformed_spotify_credential_pair_names_the_expected_shape(self, monkeypatch, tmp_path, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor", "someuser", "-z", "onlyid", "--config-file", "none", "--env-file", "none"])

        with pytest.raises(SystemExit):
            monitor.main()

        printed = capsys.readouterr().out
        assert "* Error: -z / --spotify-creds is not in the expected format" in printed
        assert "To fix: Pass the client id and the client secret as one value separated by a colon" in printed
        assert f"Guide: {monitor.SPOTIFY_APP_GUIDE_URL}" in printed

    # Verifies an optional dependency the enabled feature needs is reported with the command that installs it
    def test_a_missing_optional_dependency_names_the_install_command(self, monkeypatch, tmp_path, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setitem(sys.modules, "bs4", None)
        monkeypatch.setattr(monitor, "friends_check_enabled", lambda: True)
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor", "someuser", "--config-file", "none", "--env-file", "none", "-u", "key", "-w", "secret"])

        with pytest.raises(SystemExit):
            monitor.main()

        printed = capsys.readouterr().out
        assert "* Error: Friend and profile tracking needs beautifulsoup4, which is not installed" in printed
        assert "To fix: Install it with: " in printed
        assert f"Guide: {monitor.INSTALL_GUIDE_URL}" in printed

    # Verifies an unusable separator mode names the three values it accepts rather than repeating the raised text alone
    def test_an_unusable_separator_mode_names_the_accepted_values(self, monkeypatch, tmp_path, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(monitor, "ASCII_LOG_SEPARATORS", "Maybe")
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor", "someuser", "--config-file", "none", "--env-file", "none", "-u", "key", "-w", "secret"])

        with pytest.raises(SystemExit):
            monitor.main()

        printed = capsys.readouterr().out
        assert "* Error: ASCII_LOG_SEPARATORS must be" in printed
        assert 'To fix: Set ASCII_LOG_SEPARATORS to "Auto", "On" or "Off"' in printed
        assert f"Guide: {monitor.TERMINAL_GUIDE_URL}" in printed


# Every place that reports a problem without the classifier and the reason it cannot use one
CLASSIFIER_EXEMPTIONS = {
    "or higher required": "runs at import on an interpreter too old to load the rest of the file",
    "Couldn't find the pyLast library": "raised at import, while a dependency the classifier itself needs is missing",
    "Cannot clear the screen contents": "a cosmetic notice with nothing for the operator to recover from",
    "is available again after": "a recovery notice that reports a failure ending rather than a failure",
}

# Words that mark a printed line as a report of something going wrong
TROUBLE_WORDS = re.compile(r"error|cannot|can't|failed|failure|invalid|not valid|missing|not installed|no such|refused|unsupported|needs to be|could not|couldn't|unable to", re.IGNORECASE)


# Returns the literal text one print argument shows, leaving out the parts an f-string fills at runtime
def printed_text(node):
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else ""
    if isinstance(node, ast.JoinedStr):
        return "".join(printed_text(part) for part in node.values)
    if isinstance(node, ast.BinOp):
        return printed_text(node.left) + printed_text(node.right)
    return ""


# Returns every printed line that reads as a problem, paired with the line it sits on
def reported_problems(source):
    found = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}):
            continue
        text = " ".join(printed_text(argument) for argument in node.args)
        if TROUBLE_WORDS.search(text):
            found.append((node.lineno, " ".join(text.split())))
    return found


# A problem reported without a category leaves the reader with a message and no next step
def test_every_reported_problem_goes_through_the_classifier():
    unexplained = [f"line {line}: {text[:120]}" for line, text in reported_problems(inspect.getsource(monitor)) if not any(marker in text for marker in CLASSIFIER_EXEMPTIONS)]

    assert unexplained == []


# An exemption list that stopped matching anything would quietly cover the whole file
def test_the_classifier_guard_still_inspects_the_source():
    source = inspect.getsource(monitor)
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}]
    problems = reported_problems(source)

    assert len(inspected) > 200
    assert all(any(marker in text for _, text in problems) for marker in CLASSIFIER_EXEMPTIONS), "an exemption stopped matching a printed line"


# The only advice that names no page, and the reason no page covers it
GUIDELESS_ADVICE = {
    "The connectivity endpoint did not answer in time": "no page covers this check and the doctor report already ends with the troubleshooting link",
    "The connectivity endpoint could not be reached": "no page covers this check and the doctor report already ends with the troubleshooting link",
}

# The guide sits in this positional slot for each builder, or inside the fix when the signature carries no slot
GUIDE_SLOT = {"advice": 4, "make_recovery_advice": 5}


# True when this builder attaches a documentation link in any of the three shapes the tool uses
def attaches_a_guide(node, source):
    slot = GUIDE_SLOT.get(getattr(node.func, "id", ""))
    if slot is not None and len(node.args) > slot:
        return True
    if any(keyword.arg in ("guide_url", "guide") for keyword in node.keywords):
        return True
    return "recovery_fix_with_guide" in (ast.get_source_segment(source, node.args[2]) or "")


# Returns every expression assigned to each plain name in the module, so a fix held in a variable can be read
def assigned_expressions(tree):
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
    return assignments


# Returns the text of the summary or fix, resolving one level of plain-name assignment
def resolved_text(node, source, assignments):
    if isinstance(node, ast.Name):
        return " ".join(ast.get_source_segment(source, value) or "" for value in assignments.get(node.id, []))
    return ast.get_source_segment(source, node) or ""


# Returns every advice builder that names no page, paired with the summary it reports
def guideless_advice(source):
    tree = ast.parse(source)
    assignments = assigned_expressions(tree)
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT) or len(node.args) < 3:
            continue
        # A builder that re-wraps an already-classified advice carries whatever guide that advice was given
        if isinstance(node.args[2], ast.Attribute) and node.args[2].attr == "fix":
            continue
        if attaches_a_guide(node, source) or "recovery_fix_with_guide" in resolved_text(node.args[2], source, assignments):
            continue
        found.append((node.lineno, resolved_text(node.args[1], source, assignments)))
    return found


# A failure with no page to read leaves the operator with a one-line fix and nowhere to go next
def test_every_failure_names_a_page():
    source = inspect.getsource(monitor)
    unexplained = [f"line {line}: {summary[:100]}" for line, summary in guideless_advice(source) if not any(marker in summary for marker in GUIDELESS_ADVICE)]

    assert unexplained == []


# An allowlist that stopped matching anything would quietly cover every failure in the file
def test_the_guide_guard_still_inspects_the_source():
    source = inspect.getsource(monitor)
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT]
    bare = guideless_advice(source)

    assert len(inspected) > 40
    assert all(any(marker in summary for _, summary in bare) for marker in GUIDELESS_ADVICE), "an allowlisted summary stopped matching a builder"
