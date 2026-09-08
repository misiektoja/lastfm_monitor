"""Recovery classification: the closed code set, the advice each failure produces and the block it renders."""

import ast
import inspect
from pathlib import Path

import pylast
import pytest
import requests

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Contexts the classifier routes on, so a typo in a call site cannot fall through to the runtime branch unnoticed
KNOWN_CONTEXTS = frozenset({"runtime", "config", "set_lastfm_credentials", "set_spotify_credentials", "set_webhook_url", "target.missing", "secret.missing", "connectivity", "email", "webhook", "file"})


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
    def test_every_declared_code_is_reachable_from_the_classifier(self):
        unreachable = monitor.RECOVERY_CODES - classifier_codes()
        assert unreachable == set(), f"codes nothing can return: {sorted(unreachable)}"

    def test_the_classifier_returns_no_code_outside_the_set(self):
        undeclared = classifier_codes() - monitor.RECOVERY_CODES
        assert undeclared == set(), f"codes returned but not declared: {sorted(undeclared)}"

    def test_an_unsupported_code_is_refused(self):
        with pytest.raises(ValueError):
            monitor.make_recovery_advice("lastfm.exploded", "summary", "fix", True)

    def test_every_call_site_names_a_context_the_classifier_routes_on(self):
        contexts = call_site_contexts()
        assert contexts, "print_recovery_error is never called"
        unknown = sorted(set(contexts) - KNOWN_CONTEXTS)
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


class TestRedaction:
    def test_a_configured_secret_is_replaced_in_every_field(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "s3cret-key-value")
        advice = monitor.make_recovery_advice("unknown", "Failed with s3cret-key-value", "Retry with s3cret-key-value", True, "Sent s3cret-key-value")
        assert "s3cret-key-value" not in advice.summary + advice.fix + advice.detail
        assert advice.summary.count("<redacted>") == 1

    def test_a_classified_failure_does_not_echo_the_key_back(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "s3cret-key-value")
        advice = monitor.classify_recovery_error(RuntimeError("rejected key s3cret-key-value"))
        assert "s3cret-key-value" not in advice.detail


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
