"""Delivery across the two channels: what the sender reports and which channel a later attempt sends again."""

import pytest

import lastfm_monitor as monitor
from test_diagnostics_output import drive_quiet_cycles


# Counts the calls each channel receives and answers with the queued result codes
class FakeDeliveries:
    def __init__(self, email_results=(), webhook_results=()):
        self.email_results = list(email_results)
        self.webhook_results = list(webhook_results)
        self.emails = 0
        self.webhooks = 0

    def send_email(self, *args, **kwargs):
        self.emails += 1
        return self.email_results.pop(0) if self.email_results else 0

    def send_webhook(self, *args, **kwargs):
        self.webhooks += 1
        return self.webhook_results.pop(0) if self.webhook_results else 0


@pytest.fixture
def channels(monkeypatch):
    deliveries = FakeDeliveries()
    monkeypatch.setattr(monitor, "send_email", deliveries.send_email)
    monkeypatch.setattr(monitor, "send_webhook", deliveries.send_webhook)
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "someone@example.invalid")
    return deliveries


# Raises the one failure that enables both error channels, so a retry can be watched on each of them
def rejected_key(_call):
    return RuntimeError("Invalid API key - You must be granted a valid key by last.fm")


class TestWhatTheSenderReports:
    def test_a_delivered_channel_is_reported_as_delivered(self, channels, capsys):
        delivered = monitor.send_notification_channels("error", "subject", "body", email_enabled=True, webhook_enabled=True)
        capsys.readouterr()
        assert delivered == (True, True)

    def test_a_failed_email_is_not_reported_as_sent(self, monkeypatch, capsys):
        deliveries = FakeDeliveries(email_results=[1])
        monkeypatch.setattr(monitor, "send_email", deliveries.send_email)
        monkeypatch.setattr(monitor, "send_webhook", deliveries.send_webhook)
        delivered = monitor.send_notification_channels("error", "subject", "body", email_enabled=True, webhook_enabled=True)
        capsys.readouterr()
        assert delivered == (False, True)

    def test_a_failed_webhook_is_not_reported_as_sent(self, monkeypatch, capsys):
        deliveries = FakeDeliveries(webhook_results=[1])
        monkeypatch.setattr(monitor, "send_email", deliveries.send_email)
        monkeypatch.setattr(monitor, "send_webhook", deliveries.send_webhook)
        delivered = monitor.send_notification_channels("error", "subject", "body", email_enabled=True, webhook_enabled=True)
        capsys.readouterr()
        assert delivered == (True, False)

    def test_a_disabled_channel_is_never_attempted(self, channels, capsys):
        delivered = monitor.send_notification_channels("error", "subject", "body", email_enabled=False, webhook_enabled=False)
        capsys.readouterr()
        assert delivered == (False, False)
        assert (channels.emails, channels.webhooks) == (0, 0)


class TestAFailedChannelIsSentAgain:
    # Treating an attempt as a delivery loses the alert entirely, since the flag stops the next attempt
    def test_the_failed_channel_is_tried_again_once_its_hold_has_passed(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        deliveries = FakeDeliveries(email_results=[1, 0])
        monkeypatch.setattr(monitor, "send_email", deliveries.send_email)
        monkeypatch.setattr(monitor, "send_webhook", deliveries.send_webhook)
        monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
        monkeypatch.setattr(monitor, "webhook_event_enabled", lambda event: True)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=8, liveness=3600, fail_after=2, error_factory=rejected_key, stub_notifications=False)
        assert deliveries.emails == 1
        assert "* The email alert is on hold for 5 minutes after 1 attempt, then tried again" in transcript
        drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=16, liveness=3600, fail_after=2, error_factory=rejected_key, stub_notifications=False)
        assert deliveries.emails == 2

    # The channel that arrived must not be sent again while the other one is still being retried
    def test_the_delivered_channel_is_not_sent_twice(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        deliveries = FakeDeliveries(email_results=[1, 0])
        monkeypatch.setattr(monitor, "send_email", deliveries.send_email)
        monkeypatch.setattr(monitor, "send_webhook", deliveries.send_webhook)
        monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
        monkeypatch.setattr(monitor, "webhook_event_enabled", lambda event: True)
        drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=8, liveness=3600, fail_after=2, error_factory=rejected_key, stub_notifications=False)
        assert deliveries.webhooks == 1

    def test_nothing_is_sent_again_once_both_arrived(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        deliveries = FakeDeliveries()
        monkeypatch.setattr(monitor, "send_email", deliveries.send_email)
        monkeypatch.setattr(monitor, "send_webhook", deliveries.send_webhook)
        monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
        monkeypatch.setattr(monitor, "webhook_event_enabled", lambda event: True)
        drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=10, liveness=3600, fail_after=2, error_factory=rejected_key, stub_notifications=False)
        assert (deliveries.emails, deliveries.webhooks) == (1, 1)

    # A retry on a check that reports nothing else still leaves its own lines behind
    def test_a_retry_on_a_quiet_check_closes_its_block(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        deliveries = FakeDeliveries(email_results=[1, 0])
        monkeypatch.setattr(monitor, "send_email", deliveries.send_email)
        monkeypatch.setattr(monitor, "send_webhook", deliveries.send_webhook)
        monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
        monkeypatch.setattr(monitor, "webhook_event_enabled", lambda event: True)
        transcript = drive_quiet_cycles(monkeypatch, capsys, tmp_path, cycles=16, liveness=3600, fail_after=2, error_factory=rejected_key, stub_notifications=False).splitlines()
        retries = [number for number, line in enumerate(transcript) if line.startswith("Sending email notification")]
        assert len(retries) == 2
        assert transcript[retries[-1] + 1].startswith("Timestamp:")
