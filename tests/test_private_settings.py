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


# The command that saves each secret, so a new SECRET_KEYS entry without a hidden entry path fails here.
# NTFY_ACCESS_TOKEN has none in any of the sibling monitors: the setup wizard collects it.
SECRET_ENTRY_COMMANDS = {
    "LASTFM_API_KEY": "--set-lastfm-credentials",
    "LASTFM_API_SECRET": "--set-lastfm-credentials",
    "SP_CLIENT_ID": "--set-spotify-credentials",
    "SP_CLIENT_SECRET": "--set-spotify-credentials",
    "SMTP_PASSWORD": "--set-smtp-password",
    "WEBHOOK_URL": "--set-webhook-url",
    "NTFY_ACCESS_TOKEN": None,
}


# Settings a sign-in needs, complete enough that only the password is under test
MAIL_SETTINGS = {"SMTP_HOST": "smtp.example.test", "SMTP_USER": "monitor@example.test", "SENDER_EMAIL": "monitor@example.test", "RECEIVER_EMAIL": "owner@example.test"}


@pytest.fixture
def configured_mail(monkeypatch):
    for name, value in MAIL_SETTINGS.items():
        monkeypatch.setattr(monitor, name, value)


# Records the prompts a run reaches, so a question asked too early is visible
class Prompts:
    def __init__(self, answers=()):
        self.seen = []
        self._answers = iter(answers)

    def __call__(self, prompt):
        self.seen.append(prompt)
        return next(self._answers)


class TestOneCommandPerSecret:

    def test_every_secret_is_accounted_for(self):
        assert set(SECRET_ENTRY_COMMANDS) == set(monitor.SECRET_KEYS)

    @pytest.mark.parametrize("flag", sorted(flag for flag in SECRET_ENTRY_COMMANDS.values() if flag))
    def test_each_command_is_a_secret_action(self, flag):
        assert flag in monitor.SECRET_ACTION_FLAGS

    def test_the_secret_actions_are_exactly_the_commands(self):
        assert set(monitor.SECRET_ACTION_FLAGS) == {flag for flag in SECRET_ENTRY_COMMANDS.values() if flag}

    def test_each_command_has_a_runner(self):
        for flag in {flag for flag in SECRET_ENTRY_COMMANDS.values() if flag}:
            assert hasattr(monitor, f"run_{flag.removeprefix('--').replace('-', '_')}"), flag


class TestMailSignIn:

    def test_the_shared_handshake_is_used(self, configured_mail, monkeypatch):
        opened = []
        monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda use_ssl, smtp_timeout=15: opened.append((use_ssl, smtp_timeout)) or type("S", (), {"quit": lambda self: None})())
        assert monitor.smtp_sign_in("mail-secret-value", timeout=5) == MAIL_SETTINGS["SMTP_USER"]
        assert opened == [(monitor.SMTP_SSL, 5)]

    # The wizard and this command must not be left running on a password the server never accepted
    def test_a_refused_sign_in_restores_the_configured_password(self, configured_mail, monkeypatch):
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "previous-value")

        def refuse(use_ssl, smtp_timeout=15):
            assert monitor.SMTP_PASSWORD == "mail-secret-value"
            raise RuntimeError("535 refused")

        monkeypatch.setattr(monitor, "smtp_connect_and_login", refuse)
        with pytest.raises(RuntimeError):
            monitor.smtp_sign_in("mail-secret-value")
        assert monitor.SMTP_PASSWORD == "previous-value"

    @pytest.mark.parametrize("password", ["", "   ", "your_smtp_password"])
    def test_nothing_is_checked_without_a_password(self, configured_mail, password):
        with pytest.raises(monitor.PrivateSettingsError):
            monitor.smtp_sign_in(password)

    def test_only_the_unset_settings_are_named(self, configured_mail, monkeypatch):
        monkeypatch.setattr(monitor, "SMTP_HOST", "")
        monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "your_receiver_email")
        with pytest.raises(monitor.PrivateSettingsError) as raised:
            monitor.smtp_sign_in("mail-secret-value")
        assert "SMTP_HOST and RECEIVER_EMAIL are not set" in str(raised.value)
        assert "SMTP_USER" not in str(raised.value)


class TestSetSmtpPassword:

    def test_a_terminal_is_required(self, tmp_path, configured_mail):
        with pytest.raises(monitor.PrivateSettingsError):
            monitor.run_set_smtp_password(env_file=tmp_path / ".env", interactive=False)

    # Answering two questions to be told the mail server was never configured is the drift this catches
    def test_incomplete_settings_stop_the_run_before_any_prompt(self, tmp_path, configured_mail, monkeypatch):
        monkeypatch.setattr(monitor, "SMTP_HOST", "")
        destination = tmp_path / ".env"
        destination.write_text('SMTP_PASSWORD="keep-me"\n', encoding="utf-8")
        prompts = Prompts()
        with pytest.raises(monitor.PrivateSettingsError) as raised:
            monitor.run_set_smtp_password(env_file=destination, interactive=True, input_func=prompts, getpass_func=prompts)
        assert prompts.seen == []
        assert "incomplete" in str(raised.value)

    def test_an_accepted_password_replaces_only_its_own_assignment(self, tmp_path, configured_mail):
        destination = tmp_path / ".env"
        destination.write_text('WEBHOOK_URL="https://ntfy.sh/keep-me"\nSMTP_PASSWORD="old-value"\n', encoding="utf-8")
        result = monitor.run_set_smtp_password(env_file=destination, interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: "mail-secret-value", sign_in=lambda password, timeout=15: "monitor@example.test")
        content = destination.read_text(encoding="utf-8")
        assert result == str(destination)
        assert 'SMTP_PASSWORD="mail-secret-value"' in content
        assert 'WEBHOOK_URL="https://ntfy.sh/keep-me"' in content

    def test_a_refused_sign_in_leaves_the_file_byte_for_byte(self, tmp_path, configured_mail, capsys):
        destination = tmp_path / ".env"
        original = 'SMTP_PASSWORD="old-value"\n'
        destination.write_text(original, encoding="utf-8")

        def refuse(password, timeout=15):
            raise RuntimeError("535 Username and Password not accepted")

        with pytest.raises(monitor.PrivateSettingsError) as raised:
            monitor.run_set_smtp_password(env_file=destination, interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: "mail-secret-value", sign_in=refuse)
        assert destination.read_bytes() == original.encode("utf-8")
        assert "mail-secret-value" not in str(raised.value)
        assert "mail-secret-value" not in capsys.readouterr().out

    def test_a_declined_replacement_keeps_the_saved_password(self, tmp_path, configured_mail):
        destination = tmp_path / ".env"
        original = 'SMTP_PASSWORD="old-value"\n'
        destination.write_text(original, encoding="utf-8")
        with pytest.raises(monitor.PrivateSettingsError) as raised:
            monitor.run_set_smtp_password(env_file=destination, interactive=True, input_func=lambda prompt: "n", sign_in=lambda password, timeout=15: "monitor@example.test")
        assert destination.read_bytes() == original.encode("utf-8")
        assert "cancelled" in str(raised.value)

    def test_a_first_run_asks_nothing_but_the_password(self, tmp_path, configured_mail):
        destination = tmp_path / ".env"
        prompts = Prompts(["mail-secret-value"])
        monitor.run_set_smtp_password(env_file=destination, interactive=True, input_func=lambda prompt: pytest.fail(f"asked {prompt}"), getpass_func=prompts, sign_in=lambda password, timeout=15: "monitor@example.test")
        assert len(prompts.seen) == 1
        assert 'SMTP_PASSWORD="mail-secret-value"' in destination.read_text(encoding="utf-8")

    # The sign-in needs the configured mail server, which only exists after the config file is read
    def test_the_command_is_dispatched_after_the_config_file_is_loaded(self):
        source = (monitor.Path(__file__).resolve().parents[1] / "lastfm_monitor.py").read_text(encoding="utf-8")
        assert source.index("if not load_config_file(cfg_path):") < source.index('"set_smtp_password": args.set_smtp_password')
        assert source.index('"set_smtp_password": run_set_smtp_password') > source.index("if not load_config_file(cfg_path):")
