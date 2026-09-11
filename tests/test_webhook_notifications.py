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
    for setting in ("WEBHOOK_ENABLED", "WEBHOOK_PROVIDER", "WEBHOOK_URL", "WEBHOOK_USERNAME", "WEBHOOK_AVATAR_URL", "WEBHOOK_ACTIVE_NOTIFICATION", "WEBHOOK_INACTIVE_NOTIFICATION", "WEBHOOK_TRACK_NOTIFICATION", "WEBHOOK_SONG_NOTIFICATION", "WEBHOOK_SONG_ON_LOOP_NOTIFICATION", "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION", "WEBHOOK_FOLLOWERS_NOTIFICATION", "WEBHOOK_FOLLOWINGS_NOTIFICATION", "WEBHOOK_PROFILE_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION", "WEBHOOK_HEADERS", "WEBHOOK_TEMPLATE", "WEBHOOK_TRANSFORMS", "NTFY_ACCESS_TOKEN", "NTFY_SHORT"):
        assert f"{setting} =" in monitor.CONFIG_BLOCK
    assert "WEBHOOK_URL" in monitor.SECRET_KEYS
    assert "NTFY_ACCESS_TOKEN" in monitor.SECRET_KEYS


# Verifies startup summaries use short labels and unstarred bounded continuation lines
def test_startup_notification_summaries_use_compact_rollups(monkeypatch):
    email_settings = {"ACTIVE_NOTIFICATION": True, "INACTIVE_NOTIFICATION": True, "TRACK_NOTIFICATION": True, "SONG_NOTIFICATION": True, "SONG_ON_LOOP_NOTIFICATION": True, "OFFLINE_ENTRIES_NOTIFICATION": True, "ERROR_NOTIFICATION": True, "FOLLOWERS_NOTIFICATION": True, "FOLLOWINGS_NOTIFICATION": True, "PROFILE_NOTIFICATION": True}
    webhook_settings = {"WEBHOOK_ENABLED": True, "WEBHOOK_ACTIVE_NOTIFICATION": True, "WEBHOOK_INACTIVE_NOTIFICATION": True, "WEBHOOK_TRACK_NOTIFICATION": True, "WEBHOOK_SONG_NOTIFICATION": True, "WEBHOOK_SONG_ON_LOOP_NOTIFICATION": True, "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION": True, "WEBHOOK_ERROR_NOTIFICATION": True, "WEBHOOK_FOLLOWERS_NOTIFICATION": True, "WEBHOOK_FOLLOWINGS_NOTIFICATION": True, "WEBHOOK_PROFILE_NOTIFICATION": True}
    for setting, value in {**email_settings, **webhook_settings}.items():
        monkeypatch.setattr(monitor, setting, value)
    expected_email = "* Notifications (email):        On (active, inactive, tracked, songs, loops, offline, errors,\n                                followers, followings, profile)\n"
    expected_webhook = "* Notifications (webhook):      On (active, inactive, tracked, songs, loops, offline, errors,\n                                followers, followings, profile)\n"
    rows = {row.label: row for row in monitor.build_startup_summary("someuser")}
    assert monitor.format_startup_summary_row(rows["Notifications (email)"]) == expected_email
    assert monitor.format_startup_summary_row(rows["Notifications (webhook)"]) == expected_webhook
    assert all(len(line) <= 100 for summary in (expected_email, expected_webhook) for line in summary.splitlines())
    assert all(not line.startswith("*") for summary in (expected_email, expected_webhook) for line in summary.splitlines()[1:])


# Verifies webhook categories remain off while the master switch is disabled
def test_startup_webhook_summary_respects_master_switch(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    assert monitor._startup_notification_state(monitor._startup_webhook_notification_categories()) == "Off"


# Verifies URL validation and provider detection reject unsafe destinations
def test_webhook_url_validation_and_detection():
    assert monitor.validate_webhook_url("https://example.test/private-topic")
    assert not monitor.validate_webhook_url("http://example.test/private-topic")
    assert not monitor.validate_webhook_url("https://user:password@example.test/private-topic")
    assert monitor.detect_webhook_provider("https://discord.com/api/webhooks/123/private-token") == "discord"
    assert monitor.detect_webhook_provider("https://ntfy.sh/private-topic") == "ntfy"


# Verifies every Last.fm-specific event has an independent webhook switch
@pytest.mark.parametrize("notification_type,setting", [("active", "WEBHOOK_ACTIVE_NOTIFICATION"), ("inactive", "WEBHOOK_INACTIVE_NOTIFICATION"), ("track", "WEBHOOK_TRACK_NOTIFICATION"), ("song", "WEBHOOK_SONG_NOTIFICATION"), ("loop", "WEBHOOK_SONG_ON_LOOP_NOTIFICATION"), ("offline_entries", "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION"), ("followers", "WEBHOOK_FOLLOWERS_NOTIFICATION"), ("followings", "WEBHOOK_FOLLOWINGS_NOTIFICATION"), ("profile", "WEBHOOK_PROFILE_NOTIFICATION"), ("error", "WEBHOOK_ERROR_NOTIFICATION")])
def test_webhook_event_switches_are_independent(monkeypatch, notification_type, setting):
    for variable in ("WEBHOOK_ACTIVE_NOTIFICATION", "WEBHOOK_INACTIVE_NOTIFICATION", "WEBHOOK_TRACK_NOTIFICATION", "WEBHOOK_SONG_NOTIFICATION", "WEBHOOK_SONG_ON_LOOP_NOTIFICATION", "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION", "WEBHOOK_FOLLOWERS_NOTIFICATION", "WEBHOOK_FOLLOWINGS_NOTIFICATION", "WEBHOOK_PROFILE_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION"):
        monkeypatch.setattr(monitor, variable, False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, setting, True)
    assert monitor.webhook_event_enabled(notification_type)
    assert sum(monitor.webhook_event_enabled(event) for event in ("active", "inactive", "track", "song", "loop", "offline_entries", "followers", "followings", "profile", "error")) == 1


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
    args = monitor.argparse.Namespace(webhook_provider=None, webhook_url="https://ntfy.sh/private-topic", webhook_enabled=None, webhook_active=True, webhook_inactive=None, webhook_track=None, webhook_song_changes=None, webhook_loop=None, webhook_offline_entries=None, webhook_followers=None, webhook_followings=None, webhook_profile=None, webhook_errors=False)
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


# Verifies every delivery carries the deadline and refuses a redirect, which could retarget the payload
def test_webhook_delivery_is_bounded_and_does_not_follow_redirects(monkeypatch):
    configure_discord(monkeypatch)
    post = Mock(return_value=FakeResponse())
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)

    assert monitor.send_webhook("Track changed", "Artist - Song", "song", force=True) == 0
    request = post.call_args
    assert request.args == (monitor.WEBHOOK_URL,)
    assert request.kwargs["timeout"] == monitor.WEBHOOK_TIMEOUT_SECONDS
    assert request.kwargs["allow_redirects"] is False


# Verifies a destination replaced mid-delivery is refused rather than posted to blindly
def test_webhook_delivery_refuses_a_destination_that_stopped_validating(monkeypatch):
    configure_discord(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "http://example.test/hook")
    post = Mock(return_value=FakeResponse())
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)

    with pytest.raises(monitor.req.exceptions.InvalidURL):
        monitor.post_webhook_request(json={"content": "body"})
    post.assert_not_called()


DISCORD_DESTINATION = "https://discord.com/api/webhooks/123/private-token"
NTFY_DESTINATION = "https://ntfy.sh/a-private-topic"
UNRECOGNISED_DESTINATION = "https://hooks.example.test/services/an-unrecognised-destination"


# Points the reload at one dotenv file and restores every global it can change
@pytest.fixture
def reloadable(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    monkeypatch.setattr(monitor, "DOTENV_FILE", str(env))
    monkeypatch.setattr(monitor, "WEBHOOK_URL", DISCORD_DESTINATION)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    for secret in monitor.SECRET_KEYS:
        monkeypatch.delenv(secret, raising=False)
    return env


class TestSecretReload:

    # A destination edited into the dotenv file can belong to the other service
    def test_a_reloaded_url_moves_the_provider_with_it(self, reloadable, capsys):
        reloadable.write_text(f'WEBHOOK_URL="{NTFY_DESTINATION}"\n', encoding="utf-8")
        monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)
        assert monitor.WEBHOOK_URL == NTFY_DESTINATION
        assert monitor.WEBHOOK_PROVIDER == "ntfy"
        assert "* Updated webhook provider to ntfy" in capsys.readouterr().out

    # A reload trace says which secret arrived and whether the new value is set, never any part of the value
    def test_the_reload_traces_the_secret_without_showing_it(self, reloadable, capsys, monkeypatch):
        monkeypatch.setattr(monitor, "DEBUG_MODE", True)
        reloadable.write_text(f'WEBHOOK_URL="{NTFY_DESTINATION}"\n', encoding="utf-8")

        monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)

        output = capsys.readouterr().out
        assert f"Secret reload: name=WEBHOOK_URL, path={reloadable}, value=set" in output
        assert "a-private-topic" not in output.split("Secret reload:", 1)[1].splitlines()[0]

    # The stored value is casefolded for comparisons, which is not how the service spells itself
    def test_the_message_uses_the_service_spelling(self, reloadable, capsys, monkeypatch):
        monkeypatch.setattr(monitor, "WEBHOOK_URL", NTFY_DESTINATION)
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
        reloadable.write_text(f'WEBHOOK_URL="{DISCORD_DESTINATION}"\n', encoding="utf-8")
        monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)
        assert monitor.WEBHOOK_PROVIDER == "discord"
        assert "* Updated webhook provider to Discord" in capsys.readouterr().out

    def test_an_unrecognised_url_leaves_the_configured_provider_alone(self, reloadable, capsys):
        reloadable.write_text(f'WEBHOOK_URL="{UNRECOGNISED_DESTINATION}"\n', encoding="utf-8")
        monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)
        assert monitor.WEBHOOK_URL == UNRECOGNISED_DESTINATION
        assert monitor.WEBHOOK_PROVIDER == "discord"
        assert "Updated webhook provider" not in capsys.readouterr().out

    def test_a_url_for_the_configured_provider_says_nothing(self, reloadable, capsys):
        reloadable.write_text(f'WEBHOOK_URL="{DISCORD_DESTINATION}"\n', encoding="utf-8")
        monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)
        assert "Updated webhook provider" not in capsys.readouterr().out

    # The cached handler holds tokens issued to the previous application
    def test_new_spotify_app_credentials_drop_the_cached_handler(self, reloadable, monkeypatch):
        monkeypatch.setattr(monitor, "SP_OAUTH_MEMORY_CACHE_HANDLER", object())
        monkeypatch.setattr(monitor, "SP_CLIENT_ID", "old-client-id")
        reloadable.write_text('SP_CLIENT_ID="new-client-id"\n', encoding="utf-8")
        monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)
        assert monitor.SP_CLIENT_ID == "new-client-id"
        assert monitor.SP_OAUTH_MEMORY_CACHE_HANDLER is None

    def test_a_reloaded_secret_is_reported_as_coming_from_the_dotenv_file(self, reloadable):
        reloadable.write_text(f'WEBHOOK_URL="{NTFY_DESTINATION}"\n', encoding="utf-8")
        monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)
        assert monitor.SECRET_SOURCES["WEBHOOK_URL"] == "dotenv file"

    def test_the_sentinel_switches_the_reload_off(self, reloadable, monkeypatch, capsys):
        reloadable.write_text(f'WEBHOOK_URL="{NTFY_DESTINATION}"\n', encoding="utf-8")
        # A file actually named 'none', so the sentinel cannot be satisfied by the path simply not existing
        (reloadable.parent / "none").write_text(f'WEBHOOK_URL="{NTFY_DESTINATION}"\n', encoding="utf-8")
        monkeypatch.chdir(reloadable.parent)
        monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
        monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)
        assert monitor.WEBHOOK_URL == DISCORD_DESTINATION
        assert "Reloaded" not in capsys.readouterr().out
