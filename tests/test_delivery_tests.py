"""What the test commands send: one wording per message, and what each command does with nothing to send."""

import subprocess
import sys
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")

# The table every sibling monitor sends, with this tool's name substituted
SHARED_MESSAGES = (
    ("TEST_EMAIL_SUBJECT", "lastfm_monitor: test email"),
    ("TEST_EMAIL_BODY", "This test email was sent by --send-test-email. Your SMTP settings work."),
    ("TEST_WEBHOOK_TITLE", "lastfm_monitor: test webhook"),
    ("TEST_WEBHOOK_BODY", "This test notification was sent by --send-test-webhook. Your webhook settings work."),
    ("DOCTOR_TEST_EMAIL_SUBJECT", "lastfm_monitor: doctor test email"),
    ("DOCTOR_TEST_EMAIL_BODY", "This test email was sent after approval in --doctor. Your SMTP delivery settings work."),
    ("DOCTOR_TEST_WEBHOOK_TITLE", "lastfm_monitor: doctor test webhook"),
    ("DOCTOR_TEST_WEBHOOK_BODY", "This test notification was sent after approval in --doctor. Your webhook delivery settings work."),
)


# Runs the real script with nothing configured, so a command with no destination answers for itself
def run_with_defaults(tmp_path, *arguments):
    return subprocess.run([sys.executable, str(PROJECT_ROOT / "lastfm_monitor.py"), *arguments, "--config-file", "none", "--env-file", "none"], capture_output=True, text=True, cwd=tmp_path)


class TestSharedWording:

    @pytest.mark.parametrize("name, expected", SHARED_MESSAGES)
    def test_each_message_is_the_shared_one(self, name, expected):
        assert getattr(monitor, name) == expected

    def test_the_subject_names_the_tool(self):
        assert all(getattr(monitor, name).startswith(f"{monitor.TOOL_NAME}: ") for name, _ in SHARED_MESSAGES if name.endswith(("SUBJECT", "TITLE")))

    # The body names the command because the message can arrive minutes later, beside another monitor's
    @pytest.mark.parametrize("name, expected", [(name, expected) for name, expected in SHARED_MESSAGES if name.endswith("BODY")])
    def test_each_body_names_what_sent_it(self, name, expected):
        assert "--send-test-" in expected or "--doctor" in expected

    def test_the_messages_are_constants_rather_than_literals(self):
        for name, expected in SHARED_MESSAGES:
            # Defined once and read where it is sent, so the doctor and the command cannot drift apart
            assert SOURCE.count(name) >= 2, name
            written = expected if name.endswith("BODY") else expected.replace(monitor.TOOL_NAME, "{TOOL_NAME}")
            assert SOURCE.count(chr(34) + written + chr(34)) == 1, name

    # Every tool shipped this one, copied around long enough that all seven had it
    def test_the_old_wording_is_gone(self):
        assert "seems to be correct" not in SOURCE
        assert "Your webhook alerts are set up correctly" not in SOURCE


class TestNothingToSend:

    def test_the_email_destination_is_checked_before_the_send_is_announced(self, tmp_path):
        result = run_with_defaults(tmp_path, "--send-test-email")
        assert result.returncode == 1
        assert "Sending test email" not in result.stdout
        assert "The mail server settings are incomplete" in result.stdout
        assert "To fix:" in result.stdout and "Guide:" in result.stdout

    def test_the_webhook_destination_is_checked_before_the_send_is_announced(self, tmp_path):
        result = run_with_defaults(tmp_path, "--send-test-webhook")
        assert result.returncode == 1
        assert "Sending test webhook" not in result.stdout
        assert "WEBHOOK_URL must contain a complete HTTPS link" in result.stdout
        assert "To fix:" in result.stdout and "Guide:" in result.stdout

    # The monitoring run's notice says the same thing, so a one-shot test must not print both
    def test_one_command_reports_one_problem_once(self, tmp_path):
        result = run_with_defaults(tmp_path, "--send-test-webhook")
        assert "Webhook notifications are off because" not in result.stdout
        assert result.stdout.count("WEBHOOK_URL") == 2

    def test_the_senders_run_before_the_monitoring_notice(self):
        assert SOURCE.index("if args.send_test_webhook:") < SOURCE.index("verbose_print(\"Webhook notifications are off because")

    @pytest.mark.parametrize("missing, names, expected", [
        ("SMTP_HOST", "MAIL_DESTINATION_SETTINGS", True),
        ("SMTP_USER", "MAIL_DESTINATION_SETTINGS", False),
        ("SMTP_USER", "MAIL_SIGN_IN_SETTINGS", True),
        ("SMTP_PASSWORD", "MAIL_SIGN_IN_SETTINGS", False),
        ("SMTP_PASSWORD", "MAIL_DELIVERY_SETTINGS", True),
    ])
    def test_each_question_asks_about_its_own_settings(self, monkeypatch, missing, names, expected):
        for name in monitor.MAIL_DELIVERY_SETTINGS:
            monkeypatch.setattr(monitor, name, "configured@example.test")
        monkeypatch.setattr(monitor, missing, "")
        assert (missing in monitor.mail_settings_missing(getattr(monitor, names))) is expected


class TestDeliveredMessages:

    @pytest.fixture
    def configured_mail(self, monkeypatch):
        for name in monitor.MAIL_DELIVERY_SETTINGS:
            monkeypatch.setattr(monitor, name, "configured@example.test")

    def test_the_doctor_email_test_sends_the_doctor_message(self, monkeypatch, configured_mail):
        sent = []
        monkeypatch.setattr(monitor, "send_email", lambda subject, body, body_html, use_ssl, smtp_timeout=15: sent.append((subject, body)) or 0)
        monkeypatch.setattr(monitor, "_doctor_terminal_stream", lambda: type("S", (), {"isatty": lambda self: True})())
        monkeypatch.setattr(monitor.sys, "stdin", type("S", (), {"isatty": lambda self: True})())
        report = monitor.DoctorReport()
        report.email_ready = True
        monitor._doctor_offer_notification_tests(report, input_func=lambda prompt: "y")
        assert sent == [(monitor.DOCTOR_TEST_EMAIL_SUBJECT, monitor.DOCTOR_TEST_EMAIL_BODY)]

    def test_the_doctor_webhook_test_sends_the_doctor_message(self, monkeypatch):
        sent = []
        monkeypatch.setattr(monitor, "send_webhook", lambda title, body, category, force=False: sent.append((title, body)) or 0)
        monkeypatch.setattr(monitor, "_doctor_terminal_stream", lambda: type("S", (), {"isatty": lambda self: True})())
        monkeypatch.setattr(monitor.sys, "stdin", type("S", (), {"isatty": lambda self: True})())
        report = monitor.DoctorReport()
        report.webhook_ready = True
        monitor._doctor_offer_notification_tests(report, input_func=lambda prompt: "y")
        assert sent == [(monitor.DOCTOR_TEST_WEBHOOK_TITLE, monitor.DOCTOR_TEST_WEBHOOK_BODY)]

    @pytest.mark.parametrize("label", ["* Email sent successfully !", "* Webhook sent successfully !"])
    def test_each_command_reports_its_result_the_shared_way(self, label):
        assert f'print("{label}")' in SOURCE
