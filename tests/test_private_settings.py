import ast
import os
import subprocess
import sys

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
    with pytest.raises(monitor.RecoveryError):
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

    # Several providers quote the credentials back in the rejection reply. The sign-in has already restored
    # the previous password by then, so the value that was tried has to reach the redaction from the caller
    def test_a_reply_quoting_the_password_is_redacted(self, tmp_path, configured_mail, capsys):
        destination = tmp_path / ".env"
        destination.write_text('SMTP_PASSWORD="old-value"\n', encoding="utf-8")

        def echo(password, timeout=15):
            raise monitor.smtplib.SMTPAuthenticationError(535, f"5.7.8 Not accepted. Sent: pass={password}".encode())

        with pytest.raises(monitor.PrivateSettingsError) as raised:
            monitor.run_set_smtp_password(env_file=destination, interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: "mail-secret-value", sign_in=echo)

        assert "mail-secret-value" not in str(raised.value)
        assert "<redacted>" in str(raised.value)
        assert "did not accept the password" in str(raised.value)
        assert "mail-secret-value" not in capsys.readouterr().out

    def test_a_declined_replacement_keeps_the_saved_password(self, tmp_path, configured_mail):
        destination = tmp_path / ".env"
        original = 'SMTP_PASSWORD="old-value"\n'
        destination.write_text(original, encoding="utf-8")
        with pytest.raises(monitor.RecoveryError) as raised:
            monitor.run_set_smtp_password(env_file=destination, interactive=True, input_func=lambda prompt: "n", sign_in=lambda password, timeout=15: "monitor@example.test")
        assert destination.read_bytes() == original.encode("utf-8")
        assert raised.value.advice.summary == "The saved SMTP password was left as it is and the dotenv file was not changed"

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


# Every command that asks before replacing, with the subject each one names and whether that subject is plural
REPLACEABLE_COMMANDS = (
    ("run_set_webhook_url", "--set-webhook-url", "WEBHOOK_URL", "webhook URL", False),
    ("run_set_smtp_password", "--set-smtp-password", "SMTP_PASSWORD", "SMTP password", False),
    ("run_set_lastfm_credentials", "--set-lastfm-credentials", "LASTFM_API_KEY", "Last.fm API credentials", True),
    ("run_set_spotify_credentials", "--set-spotify-credentials", "SP_CLIENT_ID", "Spotify OAuth app credentials", True),
)


# Raises at the prompt, standing in for Ctrl+C at a question the command has its own answer for
def interrupted(prompt):
    raise KeyboardInterrupt


class TestTwoAnswers:

    @pytest.mark.parametrize("runner, flag, key, subject, plural", REPLACEABLE_COMMANDS)
    def test_a_declined_replacement_says_the_saved_value_stands(self, tmp_path, configured_mail, runner, flag, key, subject, plural):
        destination = tmp_path / ".env"
        destination.write_text(f'{key}="already-saved-value"\n', encoding="utf-8")
        with pytest.raises(monitor.RecoveryError) as raised:
            getattr(monitor, runner)(env_file=destination, interactive=True, input_func=lambda prompt: "n", getpass_func=lambda prompt: pytest.fail("asked for the value"))
        advice = raised.value.advice
        kept = "were left as they are" if plural else "was left as it is"
        assert advice.summary == f"The saved {subject} {kept} and the dotenv file was not changed"
        assert f"answer y to replace the saved {'values' if plural else 'value'}" in advice.fix
        assert advice.code == "secret.entry"

    # All seven tools read the interrupt here as an n, which answers a keypress with advice to answer it again
    @pytest.mark.parametrize("runner, flag, key, subject, plural", REPLACEABLE_COMMANDS)
    def test_an_interrupt_at_the_replace_prompt_is_a_cancel(self, tmp_path, configured_mail, runner, flag, key, subject, plural):
        destination = tmp_path / ".env"
        destination.write_text(f'{key}="already-saved-value"\n', encoding="utf-8")
        with pytest.raises(monitor.RecoveryError) as raised:
            getattr(monitor, runner)(env_file=destination, interactive=True, input_func=interrupted, getpass_func=lambda prompt: pytest.fail("asked for the value"))
        advice = raised.value.advice
        assert advice.summary == f"{subject[:1].upper()}{subject[1:]} setup was cancelled and the dotenv file was not changed"
        assert f"when you have the {'values' if plural else 'value'} ready" in advice.fix

    @pytest.mark.parametrize("runner, flag, key, subject, plural", REPLACEABLE_COMMANDS)
    def test_an_interrupt_at_the_hidden_prompt_is_a_cancel(self, tmp_path, configured_mail, runner, flag, key, subject, plural):
        with pytest.raises(monitor.RecoveryError) as raised:
            getattr(monitor, runner)(env_file=tmp_path / ".env", interactive=True, getpass_func=interrupted)
        assert raised.value.advice.summary.endswith("setup was cancelled and the dotenv file was not changed")

    # Ctrl+C echoes nothing, so without the newline the error block continues the prompt line
    @pytest.mark.parametrize("runner, flag, key, subject, plural", REPLACEABLE_COMMANDS)
    def test_the_error_starts_on_its_own_line(self, tmp_path, configured_mail, capsys, runner, flag, key, subject, plural):
        destination = tmp_path / ".env"
        destination.write_text(f'{key}="already-saved-value"\n', encoding="utf-8")
        with pytest.raises(monitor.RecoveryError):
            getattr(monitor, runner)(env_file=destination, interactive=True, input_func=interrupted)
        assert capsys.readouterr().out == "\n"

    @pytest.mark.parametrize("runner, flag, key, subject, plural", REPLACEABLE_COMMANDS)
    def test_the_error_after_a_hidden_prompt_starts_on_its_own_line(self, tmp_path, configured_mail, capsys, runner, flag, key, subject, plural):
        with pytest.raises(monitor.RecoveryError):
            getattr(monitor, runner)(env_file=tmp_path / ".env", interactive=True, getpass_func=interrupted)
        assert capsys.readouterr().out.endswith("\n\n")

    @pytest.mark.parametrize("runner, flag, key, subject, plural", REPLACEABLE_COMMANDS)
    def test_neither_answer_touches_the_file(self, tmp_path, configured_mail, runner, flag, key, subject, plural):
        destination = tmp_path / ".env"
        original = f'{key}="already-saved-value"\n'
        for answer in (lambda prompt: "n", interrupted):
            destination.write_text(original, encoding="utf-8")
            with pytest.raises(monitor.RecoveryError):
                getattr(monitor, runner)(env_file=destination, interactive=True, input_func=answer)
            assert destination.read_bytes() == original.encode("utf-8")

    # A RecoveryError reaching a clause that only names PrivateSettingsError is a traceback
    def test_the_dispatch_clause_carries_the_raised_type(self):
        source = (monitor.Path(__file__).resolve().parents[1] / "lastfm_monitor.py").read_text(encoding="utf-8")
        assert "except (PrivateSettingsError, RecoveryError) as exc:" in source


class TestInterruptHandling:

    def test_a_prompt_reads_with_the_default_interrupt_behavior(self):
        seen = []
        monitor.read_interactively(lambda prompt: seen.append(monitor.signal.getsignal(monitor.signal.SIGINT)), "answer? ")
        monitor.read_secret_interactively(lambda prompt: seen.append(monitor.signal.getsignal(monitor.signal.SIGINT)), "secret? ")
        assert seen == [monitor.signal.default_int_handler, monitor.signal.default_int_handler]

    def test_the_tool_handler_is_back_afterwards(self):
        def sentinel(sig, frame):
            pass

        previous = monitor.signal.getsignal(monitor.signal.SIGINT)
        monitor.signal.signal(monitor.signal.SIGINT, sentinel)
        try:
            monitor.read_interactively(lambda prompt: "y", "answer? ")
            assert monitor.signal.getsignal(monitor.signal.SIGINT) is sentinel
            with pytest.raises(KeyboardInterrupt):
                monitor.read_secret_interactively(interrupted, "secret? ")
            assert monitor.signal.getsignal(monitor.signal.SIGINT) is sentinel
        finally:
            monitor.signal.signal(monitor.signal.SIGINT, previous)

    # A prompt that keeps the shared handler answers Ctrl+C by terminating the tool with a success code
    def test_every_secret_prompt_goes_through_a_reader(self):
        source = (monitor.Path(__file__).resolve().parents[1] / "lastfm_monitor.py").read_text(encoding="utf-8")
        assert 'prompt(f"Replace' not in source
        assert source.count("read_interactively(prompt") == 4
        assert source.count("read_secret_interactively(hidden_prompt") == 4


class TestNoTargetIsNeeded:

    @pytest.mark.parametrize("flag", sorted(monitor.SECRET_ACTION_FLAGS))
    def test_a_secret_command_runs_without_a_username(self, flag, tmp_path):
        result = subprocess.run([sys.executable, str(monitor.Path(__file__).resolve().parents[1] / "lastfm_monitor.py"), flag], capture_output=True, text=True, cwd=tmp_path, stdin=subprocess.DEVNULL)
        assert "No Last.fm username was provided" not in result.stdout
        assert "requires an interactive terminal" in result.stdout


# Records the debug mode in force each time a hidden prompt is answered
class DebugRecordingPrompt:
    def __init__(self, answers):
        self.debug_modes = []
        self._answers = iter(answers)

    def __call__(self, prompt):
        self.debug_modes.append(monitor.DEBUG_MODE)
        answer = next(self._answers)
        if isinstance(answer, BaseException):
            raise answer
        return answer


# A trace fired while someone is typing a secret is the one thing the tool must not print
class TestDebugIsSilentWhileASecretIsTyped:

    @pytest.mark.parametrize("command, answers", [
        ("run_set_webhook_url", ["https://discord.com/api/webhooks/123/private-token"]),
        ("run_set_lastfm_credentials", ["api-key-value", "api-secret-value"]),
        ("run_set_spotify_credentials", ["client-id-value", "client-secret-value"]),
    ])
    def test_the_hidden_reader_runs_with_debug_off(self, tmp_path, monkeypatch, command, answers):
        monkeypatch.setattr(monitor, "DEBUG_MODE", True)
        prompt = DebugRecordingPrompt(answers)

        getattr(monitor, command)(env_file=tmp_path / ".env", interactive=True, getpass_func=prompt)

        assert prompt.debug_modes == [False] * len(answers)
        assert monitor.DEBUG_MODE is True

    def test_the_password_reader_runs_with_debug_off(self, tmp_path, monkeypatch, configured_mail):
        monkeypatch.setattr(monitor, "DEBUG_MODE", True)
        prompt = DebugRecordingPrompt(["mail-secret-value"])

        monitor.run_set_smtp_password(env_file=tmp_path / ".env", interactive=True, getpass_func=prompt, sign_in=lambda password, timeout=15: "monitor@example.test")

        assert prompt.debug_modes == [False]
        assert monitor.DEBUG_MODE is True

    def test_an_interrupt_at_the_prompt_restores_the_debug_mode(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "DEBUG_MODE", True)

        with pytest.raises(monitor.RecoveryError):
            monitor.run_set_webhook_url(env_file=tmp_path / ".env", interactive=True, getpass_func=DebugRecordingPrompt([KeyboardInterrupt()]))

        assert monitor.DEBUG_MODE is True

    # A new hidden reader that skips the suppression would be invisible in a transcript, so the sweep is structural
    def test_every_hidden_reader_sits_inside_a_suppressed_scope(self):
        source = (monitor.Path(__file__).resolve().parents[1] / "lastfm_monitor.py").read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.FunctionDef):
                continue
            reads = [call for call in ast.walk(node) if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "read_secret_interactively"]
            if not reads:
                continue
            decorated = any(isinstance(decorator, ast.Name) and decorator.id == "suppresses_debug_output" for decorator in node.decorator_list)
            suppressed = any(isinstance(item.context_expr, ast.Call) and isinstance(item.context_expr.func, ast.Name) and item.context_expr.func.id == "debug_output_suppressed" for block in ast.walk(node) if isinstance(block, ast.With) for item in block.items)
            assert decorated or suppressed, f"{node.name} reads a secret with debug output still on"


# Verifies an assignment the owner exported keeps its export, since dropping it changes what a shell sourcing the file exports
def test_an_exported_assignment_keeps_its_export(tmp_path):
    destination = tmp_path / ".env"
    destination.write_text('export SMTP_PASSWORD="old"\nOTHER=keep\n', encoding="utf-8")

    monitor.update_dotenv_file(destination, {"SMTP_PASSWORD": "new"})

    assert destination.read_text(encoding="utf-8") == 'export SMTP_PASSWORD="new"\nOTHER=keep\n'


# Verifies a line break inside a value is escaped rather than written through, since a raw one would split the assignment
def test_a_line_break_in_a_value_cannot_split_the_assignment(tmp_path):
    destination = tmp_path / ".env"

    monitor.update_dotenv_file(destination, {"SMTP_PASSWORD": "one\ntwo"})

    assert destination.read_text(encoding="utf-8") == 'SMTP_PASSWORD="one\\ntwo"\n'


# Verifies the writer refuses a key this tool does not ship, so a typo cannot put an unknown name in the private file
def test_the_writer_refuses_a_key_this_tool_does_not_ship(tmp_path):
    with pytest.raises(ValueError):
        monitor.update_dotenv_file(tmp_path / ".env", {"NOT_A_SECRET": "value"})


# Verifies the writer refuses a value that is not text, so a mistyped caller fails before the file is touched
def test_the_writer_refuses_a_value_that_is_not_text(tmp_path):
    with pytest.raises(TypeError):
        monitor.update_dotenv_file(tmp_path / ".env", {"SMTP_PASSWORD": 1234})
