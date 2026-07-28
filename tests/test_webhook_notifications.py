from unittest.mock import Mock

import pytest

import lastfm_monitor as monitor


class FakeResponse:
    # Stores a minimal requests-compatible webhook response
    def __init__(self, status_code=204, headers=None, json_data=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._json_data = json_data

    # Returns the configured response payload
    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON payload")
        return self._json_data


# Configures a valid deterministic Discord webhook
def configure_discord(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/123/private-token")
    monkeypatch.setattr(monitor, "WEBHOOK_USERNAME", "Last.fm Monitor")
    monkeypatch.setattr(monitor, "WEBHOOK_AVATAR_URL", "")
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {})
    monkeypatch.setattr(monitor, "WEBHOOK_TRANSFORMS", [])
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "")
    monkeypatch.setattr(monitor, "NTFY_SHORT", False)


# Verifies the generated config exposes webhook settings while retaining private placeholders
def test_config_block_contains_complete_webhook_settings():
    compile(monitor.CONFIG_BLOCK, "<generated-config>", "exec")
    for setting in ("WEBHOOK_ENABLED", "WEBHOOK_PROVIDER", "WEBHOOK_URL", "WEBHOOK_USERNAME", "WEBHOOK_AVATAR_URL", "WEBHOOK_ACTIVE_NOTIFICATION", "WEBHOOK_INACTIVE_NOTIFICATION", "WEBHOOK_TRACK_NOTIFICATION", "WEBHOOK_SONG_NOTIFICATION", "WEBHOOK_SONG_ON_LOOP_NOTIFICATION", "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION", "WEBHOOK_FOLLOWERS_NOTIFICATION", "WEBHOOK_FOLLOWINGS_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION", "WEBHOOK_HEADERS", "WEBHOOK_TEMPLATE", "WEBHOOK_TRANSFORMS", "NTFY_ACCESS_TOKEN", "NTFY_SHORT"):
        assert f"{setting} =" in monitor.CONFIG_BLOCK
    assert "WEBHOOK_URL" in monitor.SECRET_KEYS
    assert "NTFY_ACCESS_TOKEN" in monitor.SECRET_KEYS


# Verifies startup email and webhook summaries use compact single-line category rollups
def test_startup_notification_summaries_use_compact_rollups(monkeypatch):
    email_settings = {"ACTIVE_NOTIFICATION": False, "INACTIVE_NOTIFICATION": False, "TRACK_NOTIFICATION": False, "SONG_NOTIFICATION": False, "SONG_ON_LOOP_NOTIFICATION": False, "OFFLINE_ENTRIES_NOTIFICATION": False, "ERROR_NOTIFICATION": True, "FOLLOWERS_NOTIFICATION": True, "FOLLOWINGS_NOTIFICATION": True}
    webhook_settings = {"WEBHOOK_ENABLED": True, "WEBHOOK_PROVIDER": "ntfy", "WEBHOOK_ACTIVE_NOTIFICATION": True, "WEBHOOK_INACTIVE_NOTIFICATION": True, "WEBHOOK_TRACK_NOTIFICATION": False, "WEBHOOK_SONG_NOTIFICATION": True, "WEBHOOK_SONG_ON_LOOP_NOTIFICATION": True, "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION": True, "WEBHOOK_ERROR_NOTIFICATION": True, "WEBHOOK_FOLLOWERS_NOTIFICATION": True, "WEBHOOK_FOLLOWINGS_NOTIFICATION": False}
    for setting, value in {**email_settings, **webhook_settings}.items():
        monkeypatch.setattr(monitor, setting, value)
    expected_email = "* Notifications (email):        On (errors, followers, followings)"
    expected_webhook = "* Notifications (webhook):      On (active, inactive, every song, songs on loop, offline entries, errors, followers)"
    assert monitor._startup_notification_summary_lines() == [expected_email, expected_webhook]


# Verifies webhook categories remain off while the master switch is disabled
def test_startup_webhook_summary_respects_master_switch(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    assert monitor._startup_notification_summary_lines()[1] == "* Notifications (webhook):      Off"


# Verifies URL validation and provider detection reject unsafe destinations
def test_webhook_url_validation_and_detection():
    assert monitor.validate_webhook_url("https://example.test/private-topic")
    assert not monitor.validate_webhook_url("http://example.test/private-topic")
    assert not monitor.validate_webhook_url("https://user:password@example.test/private-topic")
    assert monitor.detect_webhook_provider("https://discord.com/api/webhooks/123/private-token") == "discord"
    assert monitor.detect_webhook_provider("https://ntfy.sh/private-topic") == "ntfy"


# Verifies every Last.fm-specific event has an independent webhook switch
@pytest.mark.parametrize("notification_type,setting", [("active", "WEBHOOK_ACTIVE_NOTIFICATION"), ("inactive", "WEBHOOK_INACTIVE_NOTIFICATION"), ("track", "WEBHOOK_TRACK_NOTIFICATION"), ("song", "WEBHOOK_SONG_NOTIFICATION"), ("loop", "WEBHOOK_SONG_ON_LOOP_NOTIFICATION"), ("offline_entries", "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION"), ("followers", "WEBHOOK_FOLLOWERS_NOTIFICATION"), ("followings", "WEBHOOK_FOLLOWINGS_NOTIFICATION"), ("error", "WEBHOOK_ERROR_NOTIFICATION")])
def test_webhook_event_switches_are_independent(monkeypatch, notification_type, setting):
    for variable in ("WEBHOOK_ACTIVE_NOTIFICATION", "WEBHOOK_INACTIVE_NOTIFICATION", "WEBHOOK_TRACK_NOTIFICATION", "WEBHOOK_SONG_NOTIFICATION", "WEBHOOK_SONG_ON_LOOP_NOTIFICATION", "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION", "WEBHOOK_FOLLOWERS_NOTIFICATION", "WEBHOOK_FOLLOWINGS_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION"):
        monkeypatch.setattr(monitor, variable, False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, setting, True)
    assert monitor.webhook_event_enabled(notification_type)
    assert sum(monitor.webhook_event_enabled(event) for event in ("active", "inactive", "track", "song", "loop", "offline_entries", "followers", "followings", "error")) == 1


# Verifies Discord payloads preserve customization while disabling mentions
def test_discord_payload_and_headers_are_customizable(monkeypatch):
    configure_discord(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_TRANSFORMS", [("title", "upper")])
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"X-Monitor": "{version}", "X-Title": "{title}"})
    post = Mock(return_value=FakeResponse())
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
    assert monitor.send_webhook("Track changed", "Artist - Song", "song", force=True) == 0
    payload = post.call_args.kwargs["json"]
    assert payload["allowed_mentions"] == {"parse": []}
    assert payload["embeds"][0]["title"] == "TRACK CHANGED"
    assert post.call_args.kwargs["headers"]["X-Title"] == "TRACK CHANGED"
    assert post.call_args.kwargs["headers"]["X-Monitor"] == monitor.VERSION


# Verifies ntfy requests use native text payloads and private Bearer authentication
def test_ntfy_payload_and_access_token(monkeypatch):
    configure_discord(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.sh/private-topic")
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "tk_private")
    post = Mock(return_value=FakeResponse(status_code=200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
    assert monitor.send_webhook("Title", "Body", "song", force=True) == 0
    assert post.call_args.kwargs["data"] == b"Body"
    assert post.call_args.kwargs["params"] == {"title": "Title"}
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer tk_private"
    assert post.call_args.kwargs["headers"]["Content-Type"] == "text/plain; charset=utf-8"


# Verifies webhook rate-limit waits are capped and retries remain bounded
def test_webhook_rate_limit_is_capped(monkeypatch):
    configure_discord(monkeypatch)
    post = Mock(side_effect=[FakeResponse(status_code=429, headers={"Retry-After": "999"}), FakeResponse()])
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
    sleeps = []
    assert monitor.send_webhook("Title", "Body", "song", force=True, sleeper=sleeps.append) == 0
    assert post.call_count == monitor.WEBHOOK_MAX_ATTEMPTS == 2
    assert sleeps == [monitor.WEBHOOK_MAX_RETRY_AFTER_SECONDS]


# Verifies email and webhook attempts remain independent and compact text stays ntfy-only
def test_notification_channels_are_independent_and_ntfy_short_is_scoped(monkeypatch):
    configure_discord(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "NTFY_SHORT", True)
    email = Mock(return_value=0)
    webhook = Mock(return_value=0)
    monkeypatch.setattr(monitor, "send_email", email)
    monkeypatch.setattr(monitor, "send_webhook", webhook)
    assert monitor.send_notification_channels("song", "Normal title", "Normal body", email_enabled=True, webhook_enabled=True, subject_short="Short title", body_short="Short body") == (True, True)
    email.assert_called_once_with("Normal title", "Normal body", "", monitor.SMTP_SSL)
    webhook.assert_called_once_with("Short title", "Short body", "song", force=True)


# Verifies runtime webhook flags enable selected events and correct known provider mismatches
def test_webhook_cli_overrides(monkeypatch):
    configure_discord(monkeypatch)
    args = monitor.argparse.Namespace(webhook_provider=None, webhook_url="https://ntfy.sh/private-topic", webhook_enabled=None, webhook_active=True, webhook_inactive=None, webhook_track=None, webhook_song_changes=None, webhook_loop=None, webhook_offline_entries=None, webhook_followers=None, webhook_followings=None, webhook_errors=False)
    parser = Mock()
    monitor.apply_webhook_cli_overrides(args, parser)
    assert monitor.WEBHOOK_PROVIDER == "ntfy"
    assert monitor.WEBHOOK_ENABLED is True
    assert monitor.WEBHOOK_ACTIVE_NOTIFICATION is True
    assert monitor.WEBHOOK_ERROR_NOTIFICATION is False
    parser.error.assert_not_called()


# Verifies long ntfy messages stay under the service boundary with a visible marker
def test_ntfy_message_is_bounded():
    _, message = monitor.build_ntfy_webhook_message("Title", ("a" * monitor.NTFY_MESSAGE_LIMIT_BYTES) + "x")
    assert len(message.encode("utf-8")) <= monitor.NTFY_MESSAGE_LIMIT_BYTES
    assert message.endswith(monitor.NTFY_TRUNCATION_SUFFIX)
