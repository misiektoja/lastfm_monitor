import os

import pytest

import lastfm_monitor as monitor


# Verifies private setup requires a terminal and a writable destination
def test_private_setup_requires_safe_persistence(tmp_path):
    with pytest.raises(monitor.PrivateSettingsError):
        monitor.run_set_webhook_url(env_file=tmp_path / ".env", interactive=False)
    with pytest.raises(monitor.PrivateSettingsError):
        monitor.run_set_lastfm_credentials(env_file="none", interactive=True)


# Verifies the hidden webhook flow updates only its intended dotenv assignment
def test_set_webhook_url_updates_only_the_webhook(tmp_path):
    destination = tmp_path / ".env"
    destination.write_text('SMTP_PASSWORD="keep-me"\nWEBHOOK_URL="old"\n', encoding="utf-8")
    secret = "https://discord.com/api/webhooks/123/new-private-token"
    result = monitor.run_set_webhook_url(env_file=destination, interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: secret)
    content = destination.read_text(encoding="utf-8")
    assert result == str(destination)
    assert 'SMTP_PASSWORD="keep-me"' in content
    assert f'WEBHOOK_URL="{secret}"' in content
    if os.name == "posix":
        assert destination.stat().st_mode & 0o777 == 0o600


# Verifies invalid webhook input never changes the file or exposes the entered value
def test_set_webhook_url_rejects_invalid_input_without_leak(tmp_path, capsys):
    destination = tmp_path / ".env"
    destination.write_text('SMTP_PASSWORD="keep-me"\n', encoding="utf-8")
    secret = "http://example.test/private-token"
    with pytest.raises(monitor.PrivateSettingsError) as raised:
        monitor.run_set_webhook_url(env_file=destination, interactive=True, getpass_func=lambda prompt: secret)
    output = capsys.readouterr().out
    assert secret not in output
    assert secret not in str(raised.value)
    assert destination.read_text(encoding="utf-8") == 'SMTP_PASSWORD="keep-me"\n'


# Verifies Last.fm credentials are collected privately and committed atomically as a pair
def test_set_lastfm_credentials_saves_both_values(tmp_path, capsys):
    destination = tmp_path / ".env"
    values = iter(["lastfm-key", "lastfm-secret"])
    monitor.run_set_lastfm_credentials(env_file=destination, interactive=True, getpass_func=lambda prompt: next(values))
    content = destination.read_text(encoding="utf-8")
    output = capsys.readouterr().out
    assert 'LASTFM_API_KEY="lastfm-key"' in content
    assert 'LASTFM_API_SECRET="lastfm-secret"' in content
    assert "lastfm-key" not in output
    assert "lastfm-secret" not in output


# Verifies Spotify credentials are collected privately and committed atomically as a pair
def test_set_spotify_credentials_saves_both_values(tmp_path, capsys):
    destination = tmp_path / ".env"
    values = iter(["spotify-client", "spotify-secret"])
    monitor.run_set_spotify_credentials(env_file=destination, interactive=True, getpass_func=lambda prompt: next(values))
    content = destination.read_text(encoding="utf-8")
    output = capsys.readouterr().out
    assert 'SP_CLIENT_ID="spotify-client"' in content
    assert 'SP_CLIENT_SECRET="spotify-secret"' in content
    assert "spotify-client" not in output
    assert "spotify-secret" not in output


# Verifies declined replacement leaves every saved credential unchanged
def test_private_credential_replacement_requires_confirmation(tmp_path):
    destination = tmp_path / ".env"
    original = 'LASTFM_API_KEY="old-key"\nLASTFM_API_SECRET="old-secret"\n'
    destination.write_text(original, encoding="utf-8")
    with pytest.raises(monitor.PrivateSettingsError):
        monitor.run_set_lastfm_credentials(env_file=destination, interactive=True, input_func=lambda prompt: "n", getpass_func=lambda prompt: pytest.fail("secret prompt should not run"))
    assert destination.read_text(encoding="utf-8") == original


# Verifies unsupported keys cannot be written through the private persistence helper
def test_dotenv_writer_rejects_unknown_keys(tmp_path):
    with pytest.raises(ValueError):
        monitor.update_dotenv_file(tmp_path / ".env", {"UNEXPECTED_SECRET": "value"})
