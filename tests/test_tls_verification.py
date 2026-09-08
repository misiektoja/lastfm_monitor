"""The VERIFY_SSL switch: its shipped default, the call sites that read it and the library sessions it has to reach."""

import ast
import re
import ssl
from pathlib import Path

import pylast
import pytest
import urllib3

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")

# Everything this tool sends a request through, so a new one added without the switch is a setting that lies
OUTBOUND_CALLERS = ("req", "SPOTIFY_SESSION", "WEBHOOK_SESSION")


# Returns every outbound request call in the module with the verify keyword it passes, if any
def outbound_calls():
    calls = []
    for node in ast.walk(ast.parse(SOURCE)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        caller = node.func.value
        if not isinstance(caller, ast.Name) or caller.id not in OUTBOUND_CALLERS or node.func.attr not in ("get", "post", "request"):
            continue
        verify = next((keyword.value for keyword in node.keywords if keyword.arg == "verify"), None)
        name = verify.id if isinstance(verify, ast.Name) else None
        calls.append((f"{caller.id}.{node.func.attr} at line {node.lineno}", name))
    return calls


@pytest.fixture
def restored_tls():
    saved = (monitor.VERIFY_SSL, pylast.SSL_CONTEXT, monitor.SPOTIFY_SESSION.verify, monitor.WEBHOOK_SESSION.verify)
    yield
    monitor.VERIFY_SSL, pylast.SSL_CONTEXT, monitor.SPOTIFY_SESSION.verify, monitor.WEBHOOK_SESSION.verify = saved


class TestTheShippedDefault:
    def test_verification_is_on_out_of_the_box(self):
        assert monitor.VERIFY_SSL is True

    # exec(CONFIG_BLOCK, globals()) overwrites the fallback block, so a wrong value there cannot fail a behavioural test
    @pytest.mark.parametrize("block", ["template", "fallback"])
    def test_both_declarations_of_the_default_say_true(self, block):
        before_exec = SOURCE.partition("exec(CONFIG_BLOCK, globals())")[0]
        searched = monitor.CONFIG_BLOCK if block == "template" else before_exec.replace(monitor.CONFIG_BLOCK, "")
        assert re.search(r"(?m)^VERIFY_SSL = True$", searched), f"the {block} default is not True"


class TestTheContextBuilder:
    def test_verification_on_gives_a_verifying_context(self, restored_tls):
        monitor.VERIFY_SSL = True
        context = monitor.tls_context()
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True

    # Setting CERT_NONE while check_hostname is still on raises, so the order inside the builder is load-bearing
    def test_verification_off_gives_a_context_that_checks_nothing(self, restored_tls):
        monitor.VERIFY_SSL = False
        context = monitor.tls_context()
        assert context.verify_mode == ssl.CERT_NONE
        assert context.check_hostname is False

    # One builder, so the sweep catches the next call site somebody adds without reading any of this
    def test_nothing_else_builds_a_context_of_its_own(self):
        assert SOURCE.count("ssl.create_default_context()") == 1


class TestEveryCallSiteReadsTheSwitch:
    def test_the_module_still_makes_outbound_calls(self):
        assert outbound_calls(), "no outbound request calls were found, so this guard checks nothing"

    def test_every_outbound_call_passes_the_switch(self):
        missing = [where for where, name in outbound_calls() if name != "VERIFY_SSL"]
        assert missing == [], f"outbound calls that skip VERIFY_SSL: {missing}"

    # Anything that speaks TLS without going through requests needs the same switch, and mail was the one that kept verifying
    def test_the_mail_handshake_uses_the_shared_context(self):
        assert "smtp_object.starttls(context=tls_context())" in SOURCE

    # One handshake, so the preflight check fails exactly where a real send would
    def test_one_helper_opens_every_authenticated_mail_session(self):
        assert SOURCE.count("smtplib.SMTP(") == 1
        assert SOURCE.count("smtp_connect_and_login(") == 5

    # Spotipy owns its session, so it has to be handed the one already carrying the setting
    def test_spotipy_is_handed_the_configured_session(self):
        assert "requests_session=SPOTIFY_SESSION" in SOURCE


class TestApplyingTheSetting:
    def test_both_sessions_and_the_lastfm_client_follow_the_switch(self, restored_tls, capsys):
        monitor.VERIFY_SSL = False
        monitor.apply_tls_verification_setting()
        capsys.readouterr()
        assert monitor.SPOTIFY_SESSION.verify is False
        assert monitor.WEBHOOK_SESSION.verify is False
        assert pylast.SSL_CONTEXT.verify_mode == ssl.CERT_NONE
        assert pylast.SSL_CONTEXT.check_hostname is False

    def test_leaving_it_on_keeps_every_connection_verifying(self, restored_tls, capsys):
        monitor.VERIFY_SSL = True
        monitor.apply_tls_verification_setting()
        assert capsys.readouterr().out == ""
        assert monitor.SPOTIFY_SESSION.verify is True
        assert monitor.WEBHOOK_SESSION.verify is True
        assert pylast.SSL_CONTEXT.verify_mode == ssl.CERT_REQUIRED

    # Turning verification off is a deliberate choice and nothing else in the tool explains why interception is invisible
    def test_switching_it_off_says_so_once(self, restored_tls, capsys):
        monitor.VERIFY_SSL = False
        monitor.apply_tls_verification_setting()
        output = capsys.readouterr().out
        assert "TLS certificate verification is off" in output
        assert output.count("Warning") == 1

    # A pylast release that renames the context would otherwise leave a new attribute nothing reads
    def test_a_missing_pylast_seam_degrades_towards_verifying(self, restored_tls, monkeypatch, capsys):
        monkeypatch.delattr(pylast, "SSL_CONTEXT")
        monitor.VERIFY_SSL = False
        monitor.apply_tls_verification_setting()
        capsys.readouterr()
        assert not hasattr(pylast, "SSL_CONTEXT")

    def test_the_certificate_warning_is_silenced_only_while_the_switch_is_off(self, restored_tls, monkeypatch, capsys):
        silenced = []
        monkeypatch.setattr(urllib3, "disable_warnings", lambda category: silenced.append(category))
        monitor.VERIFY_SSL = True
        monitor.apply_tls_verification_setting()
        assert silenced == []
        monitor.VERIFY_SSL = False
        monitor.apply_tls_verification_setting()
        capsys.readouterr()
        assert silenced == [urllib3.exceptions.InsecureRequestWarning]


class TestConnectivitySettings:
    # Argument defaults bind when the function is defined, which is before any config file has been read
    def test_the_connectivity_check_reads_the_current_settings(self, monkeypatch):
        seen = {}

        def fake_get(url, timeout=None, headers=None, verify=None):
            seen.update(url=url, timeout=timeout, verify=verify)
            raise monitor.req.RequestException("stopped before the network")

        monkeypatch.setattr(monitor.req, "get", fake_get)
        monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://example.invalid/probe")
        monkeypatch.setattr(monitor, "CHECK_INTERNET_TIMEOUT", 11)
        monkeypatch.setattr(monitor, "VERIFY_SSL", False)
        assert monitor.check_internet() is False
        assert seen == {"url": "https://example.invalid/probe", "timeout": 11, "verify": False}

    def test_an_explicit_argument_still_wins(self, monkeypatch):
        seen = {}

        def fake_get(url, timeout=None, headers=None, verify=None):
            seen.update(url=url, timeout=timeout)
            raise monitor.req.RequestException("stopped before the network")

        monkeypatch.setattr(monitor.req, "get", fake_get)
        monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://example.invalid/probe")
        assert monitor.check_internet(url="https://other.invalid/", timeout=3) is False
        assert seen == {"url": "https://other.invalid/", "timeout": 3}
