"""The guided setup: answers held until Save, the mail server sign-in, the escape from every rejected answer, the frame around its questions, the review summary, per-section editing and the files it writes."""

import argparse
import ast
import os
import smtplib
import subprocess
import sys
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")
REAL_VERIFY_SMTP = monitor._wizard_verify_smtp


# Puts back everything a saved run applies, module settings and the environment the dotenv is loaded into,
# so one test's answers cannot reach the next
@pytest.fixture(autouse=True)
def module_settings_restored():
    saved = {name: getattr(monitor, name) for name in monitor._config_allowed_names() if hasattr(monitor, name)}
    saved_environment = dict(os.environ)
    yield
    for name, value in saved.items():
        setattr(monitor, name, value)
    os.environ.clear()
    os.environ.update(saved_environment)


# Keeps the wizard's mail server sign-in offline, so no scripted setup run opens a connection
@pytest.fixture(autouse=True)
def accepted_smtp_sign_in(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: None)


# Hands the real sign-in check back to the one test that drives it against a stub connection
@pytest.fixture
def real_smtp_sign_in(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", REAL_VERIFY_SMTP)


# Answers one scripted question per call and fails the test when the wizard asks more than the script covers
class Script:
    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def __call__(self, prompt=""):
        self.prompts.append(str(prompt))
        assert self.answers, f"the wizard asked more than the script answers: {prompt!r}"
        return self.answers.pop(0)


# The answers a full first run gives: target, intervals, credentials, then every optional section declined
def full_run_answers(**overrides):
    answers = {
        "target": ["someuser", ""],
        "polling": ["", "", ""],
        "auth": [],
        "spotify": ["n"],
        "tracking": ["n", "n", "n", "n"],
        "output": ["", "", ""],
        "email": ["n"],
        "webhook": ["n"],
        "review": ["1"],
        "doctor": ["n"],
    }
    answers.update(overrides)
    return [answer for group in ("target", "polling", "auth", "spotify", "tracking", "output", "email", "webhook", "review", "doctor") for answer in answers[group]]


# Runs the real wizard with every network call replaced, so a test exercises the questions and the writes only
@pytest.fixture
def wizard(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_verify_lastfm_credentials", lambda api_key, api_secret: None)
    monkeypatch.setattr(monitor, "run_doctor", lambda **kwargs: 0)
    monkeypatch.chdir(tmp_path)

    def run(answers, secrets=("api-key", "api-secret"), config_file=None, env_file=None):
        script = Script(answers)
        secret_script = Script(secrets)
        code = monitor.run_setup_wizard(
            config_file=str(config_file or tmp_path / "lastfm_monitor.conf"),
            env_file=str(env_file or tmp_path / ".env"),
            input_func=script,
            getpass_func=secret_script,
            interactive=True,
        )
        return code, script

    return run


# Stands in for a run that typed no flags at all, so every override the wizard runs behind reads as unset
class NoFlags(argparse.Namespace):
    def __getattr__(self, name): return None


# Returns the settings a written config assigns
def config_values(path):
    values = {}
    for statement in ast.parse(Path(path).read_text(encoding="utf-8")).body:
        if isinstance(statement, ast.Assign) and isinstance(statement.targets[0], ast.Name):
            try:
                values[statement.targets[0].id] = ast.literal_eval(statement.value)
            except (ValueError, TypeError):
                continue
    return values


class TestNothingIsWrittenBeforeSave:

    def test_a_discarded_run_writes_no_files(self, wizard, tmp_path):
        code, _script = wizard(full_run_answers(review=["3"], doctor=["y"]))

        assert code == 1
        assert list(tmp_path.iterdir()) == []

    def test_a_declined_discard_returns_to_the_summary(self, wizard, tmp_path):
        code, script = wizard(full_run_answers(review=["3", "n", "1"], doctor=["n"]))

        assert code == 0
        assert "Setup answers retained." not in script.prompts
        assert (tmp_path / "lastfm_monitor.conf").is_file()

    def test_an_interrupt_leaves_the_destinations_alone(self, wizard, tmp_path, capsys):
        def interrupt(prompt=""):
            raise KeyboardInterrupt

        code = monitor.run_setup_wizard(config_file=str(tmp_path / "lastfm_monitor.conf"), env_file=str(tmp_path / ".env"), input_func=interrupt, interactive=True)

        assert code == 1
        assert "Destination files were not changed" in capsys.readouterr().out
        assert list(tmp_path.iterdir()) == []


class TestWhatSaveWrites:

    def test_the_answers_reach_the_configuration(self, wizard, tmp_path):
        code, _script = wizard(full_run_answers(polling=["30", "5m", ""], output=["", "scrobbles", ""]))

        assert code == 0
        written = config_values(tmp_path / "lastfm_monitor.conf")
        assert written["LASTFM_USERNAME"] == "someuser"
        assert (written["LASTFM_CHECK_INTERVAL"], written["LASTFM_ACTIVE_CHECK_INTERVAL"]) == (30, 300)
        assert written["CSV_FILE"] == "scrobbles.csv"
        assert written["DOTENV_FILE"] == str(tmp_path / ".env")

    def test_the_written_configuration_loads_back(self, wizard, tmp_path):
        wizard(full_run_answers())

        namespace = {}
        assert monitor.load_config_file(str(tmp_path / "lastfm_monitor.conf"), namespace=namespace) is True
        assert namespace["LASTFM_USERNAME"] == "someuser"

    # A wizard that changed nothing about the webhook used to collapse the shipped template into one 270-character line
    def test_the_written_configuration_keeps_the_templates_own_lines(self, wizard, tmp_path):
        wizard(full_run_answers())

        written = (tmp_path / "lastfm_monitor.conf").read_text(encoding="utf-8")
        assert written.count("\nWEBHOOK_TEMPLATE = {\n") == 1
        assert "WEBHOOK_TEMPLATE = {'" not in written

    # Verifies a setting still holding the shipped default keeps the template's own lines rather than a collapsed repr
    def test_an_unchanged_setting_keeps_the_template_formatting(self):
        rendered = monitor.generate_config_with_current_values(dict(monitor._config_template_defaults()))

        assert rendered.count("\nWEBHOOK_TEMPLATE = {\n") == 1
        assert "WEBHOOK_TEMPLATE = {'" not in rendered

    # Verifies a changed setting is rewritten in place, replacing every line of the value it stood for
    def test_a_changed_setting_replaces_the_whole_template_value(self):
        values = dict(monitor._config_template_defaults())
        values["WEBHOOK_TEMPLATE"] = {"content": "one line"}
        rendered = monitor.generate_config_with_current_values(values)

        assert "WEBHOOK_TEMPLATE = {'content': 'one line'}\n" in rendered
        assert monitor.parse_config_content(rendered)["WEBHOOK_TEMPLATE"] == {"content": "one line"}

    # A secret in the configuration would be world readable and would sit in its backup as well
    def test_the_secrets_go_to_the_dotenv_file_only(self, wizard, tmp_path):
        wizard(full_run_answers(), secrets=("live-api-key", "live-api-secret"))

        assert "live-api-key" not in (tmp_path / "lastfm_monitor.conf").read_text(encoding="utf-8")
        dotenv = (tmp_path / ".env").read_text(encoding="utf-8")
        assert "LASTFM_API_KEY=" in dotenv and "live-api-key" in dotenv

    def test_a_run_that_queues_no_secret_writes_no_dotenv_file(self, wizard, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "already-configured")
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", "already-configured")

        wizard(full_run_answers(auth=["n"]), secrets=())

        assert (tmp_path / "lastfm_monitor.conf").is_file()
        assert not (tmp_path / ".env").exists()

    # A rerun loads the saved secrets into the values the writer starts from, which is how they reached the config file
    def test_a_secret_already_in_effect_is_never_copied_into_the_configuration(self, wizard, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "loaded-key-value")
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", "loaded-secret-value")
        config = tmp_path / "lastfm_monitor.conf"
        config.write_text("LASTFM_CHECK_INTERVAL = 42\n", encoding="utf-8")

        code, _script = wizard(["y"] + full_run_answers(auth=["n"]), secrets=())

        assert code == 0
        backup = next(path for path in tmp_path.iterdir() if path.name.endswith(".bak"))
        for path in (config, backup):
            text = path.read_text(encoding="utf-8")
            assert "loaded-key-value" not in text and "loaded-secret-value" not in text

    def test_an_unpersisted_target_is_left_out_of_the_file(self, wizard, tmp_path):
        wizard(full_run_answers(target=["someuser", "n"]))

        assert config_values(tmp_path / "lastfm_monitor.conf")["LASTFM_USERNAME"] == ""

    def test_replacing_a_config_keeps_a_timestamped_backup(self, wizard, tmp_path):
        config = tmp_path / "lastfm_monitor.conf"
        config.write_text("LASTFM_CHECK_INTERVAL = 42\n", encoding="utf-8")

        code, _script = wizard(["y"] + full_run_answers())

        assert code == 0
        backup = next(path for path in tmp_path.iterdir() if path.name.endswith(".bak"))
        assert backup.read_text(encoding="utf-8") == "LASTFM_CHECK_INTERVAL = 42\n"

    def test_declining_the_replacement_and_the_alternative_cancels(self, wizard, tmp_path):
        config = tmp_path / "lastfm_monitor.conf"
        config.write_text("LASTFM_CHECK_INTERVAL = 42\n", encoding="utf-8")

        code, _script = wizard(["n", ""])

        assert code == 1
        assert config.read_text(encoding="utf-8") == "LASTFM_CHECK_INTERVAL = 42\n"


# The doctor run the wizard offers reads the same source map monitoring does, so a secret it just saved
# must not be reported as one nothing supplied
class TestTheSecretsTheWizardPutsInEffect:

    def test_doctor_names_the_dotenv_file_the_wizard_just_wrote(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
        env_path = tmp_path / ".env"
        env_path.write_text("LASTFM_API_KEY=written-key\nSMTP_PASSWORD=written-password\n", encoding="utf-8")
        state = monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(env_path), dict(monitor._config_template_defaults()))
        state.secret_updates = {"LASTFM_API_KEY": "written-key", "SMTP_PASSWORD": "written-password"}

        monitor._wizard_apply_saved_values(state, env_path=env_path)

        assert monitor.secrets_by_source() == [("dotenv file", ["LASTFM_API_KEY", "SMTP_PASSWORD"])]
        assert [row.label for row in monitor.doctor_secret_checks()] == ["Secrets loaded from the dotenv file"]

    def test_a_secret_exported_before_the_run_is_not_credited_to_the_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
        monkeypatch.setenv("LASTFM_API_SECRET", "exported-secret")
        env_path = tmp_path / ".env"
        env_path.write_text("LASTFM_API_KEY=written-key\n", encoding="utf-8")
        state = monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(env_path), dict(monitor._config_template_defaults()))

        monitor._wizard_apply_saved_values(state, env_path=env_path)

        assert monitor.secrets_by_source() == [("dotenv file", ["LASTFM_API_KEY"]), ("environment", ["LASTFM_API_SECRET"])]

    # Without python-dotenv the entered values are applied straight from the wizard, and they still have a home
    def test_the_entered_values_are_credited_when_the_file_cannot_be_read_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
        state = monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(tmp_path / ".env"), dict(monitor._config_template_defaults()))
        state.secret_updates = {"WEBHOOK_URL": "https://example.test/hooks/written"}

        monitor._wizard_apply_saved_values(state, env_path=None)

        assert monitor.secrets_by_source() == [("dotenv file", ["WEBHOOK_URL"])]


class TestPerSectionEditing:

    def test_one_section_is_changed_without_losing_the_others(self, wizard, tmp_path):
        # Review, choose Output files, switch the log off, keep the rest, then save
        code, _script = wizard(full_run_answers(target=["someuser", ""], review=["2", "6", "n", "notes", "", "1"]))

        assert code == 0
        written = config_values(tmp_path / "lastfm_monitor.conf")
        assert written["DISABLE_LOGGING"] is True
        assert written["CSV_FILE"] == "notes.csv"
        assert written["LASTFM_USERNAME"] == "someuser"

    # Re-entering a section starts it over from the values setup began with, which is what its defaults then show
    def test_editing_a_section_restarts_it_from_the_starting_values(self, wizard, tmp_path):
        code, script = wizard(full_run_answers(output=["", "scrobbles", ""], review=["2", "6", "", "", "", "1"]))

        assert code == 0
        assert config_values(tmp_path / "lastfm_monitor.conf")["CSV_FILE"] == ""
        assert "Optional CSV output path (blank disables it): " in script.prompts

    def test_returning_to_the_summary_changes_nothing(self, wizard, tmp_path):
        code, _script = wizard(full_run_answers(review=["2", "10", "1"]))

        assert code == 0
        assert config_values(tmp_path / "lastfm_monitor.conf")["LASTFM_USERNAME"] == "someuser"

    def test_every_section_has_a_collector_and_every_collector_a_section(self):
        names = [name for name, _label, _description, _config_keys, _secret_keys in monitor.WIZARD_SECTIONS]
        collectors = SOURCE.split("    collectors = {")[1].split("    }")[0]
        assert len(names) == len(set(names)) == collectors.count(": lambda")
        for name in names:
            assert f'"{name}": lambda' in collectors

    def test_a_section_reset_returns_its_keys_to_the_starting_values(self):
        state = monitor.WizardSetupState("config", "env", {"LASTFM_CHECK_INTERVAL": 10})
        state.config_values["LASTFM_CHECK_INTERVAL"] = 99
        state.secret_updates["LASTFM_API_KEY"] = "typed"

        monitor._wizard_reset_section(state, ("LASTFM_CHECK_INTERVAL",), ("LASTFM_API_KEY",))

        assert state.config_values["LASTFM_CHECK_INTERVAL"] == 10
        assert state.secret_updates == {}

    # A declined section is written as the template ships it, not as the loaded config happened to hold it
    def test_a_cleared_section_returns_to_the_template_values(self):
        state = monitor.WizardSetupState("config", "env", {"LASTFM_CHECK_INTERVAL": 99})

        monitor._wizard_clear_section(state, ("LASTFM_CHECK_INTERVAL",))

        assert state.config_values["LASTFM_CHECK_INTERVAL"] == monitor._config_template_defaults()["LASTFM_CHECK_INTERVAL"]


class TestAlertsThisSetupCanProduce:

    def test_an_alert_whose_feature_is_off_is_never_offered(self, wizard, tmp_path):
        # Custom email alerts are asked one by one, and only three of the ten can fire without profile tracking
        code, script = wizard(full_run_answers(email=["y", "smtp.invalid", "", "", "user", "from@invalid", "to@invalid", "3", "y", "y", "n", "n", "y", "y"]), secrets=("api-key", "api-secret", ""))

        assert code == 0
        asked = [prompt for prompt in script.prompts if prompt.startswith("Email on ")]
        assert "Email on follower changes? [y/N]: " not in asked
        assert "Email on starts listening? [y/N]: " in asked
        assert config_values(tmp_path / "lastfm_monitor.conf")["FOLLOWERS_NOTIFICATION"] is False

    def test_the_recommended_preset_switches_on_only_what_it_names(self, wizard, tmp_path):
        code, _script = wizard(full_run_answers(email=["y", "smtp.invalid", "", "", "user", "from@invalid", "to@invalid", "1"]), secrets=("api-key", "api-secret", ""))

        assert code == 0
        written = config_values(tmp_path / "lastfm_monitor.conf")
        assert written["SONG_NOTIFICATION"] is False
        assert written["ACTIVE_NOTIFICATION"] is True
        assert written["ERROR_NOTIFICATION"] is True

    def test_the_recommended_preset_leaves_out_the_every_song_alert(self):
        assert "SONG_NOTIFICATION" not in monitor.WIZARD_RECOMMENDED_EMAIL_KEYS
        assert "WEBHOOK_SONG_NOTIFICATION" not in monitor.WIZARD_RECOMMENDED_WEBHOOK_KEYS

    def test_every_offered_alert_is_a_real_setting(self):
        allowed = monitor._config_allowed_names()
        assert set(monitor.WIZARD_EMAIL_NOTIFICATION_KEYS) | set(monitor.WIZARD_WEBHOOK_NOTIFICATION_KEYS) <= allowed
        assert set(monitor.WIZARD_RECOMMENDED_EMAIL_KEYS) <= set(monitor.WIZARD_EMAIL_NOTIFICATION_KEYS)
        assert set(monitor.WIZARD_RECOMMENDED_WEBHOOK_KEYS) <= set(monitor.WIZARD_WEBHOOK_NOTIFICATION_KEYS)


class TestTheSavedTarget:

    def test_the_setting_ships_in_the_template(self):
        assert "LASTFM_USERNAME" in monitor._config_allowed_names()

    def test_the_positional_wins_over_the_saved_value(self):
        assert "if not args.username and LASTFM_USERNAME:\n        args.username = LASTFM_USERNAME" in SOURCE

    # A saved target makes a bare command a complete one, so the welcome screen must not replace the run
    def test_the_welcome_screen_waits_for_the_configuration(self):
        assert "if len(sys.argv) == 1 and not LASTFM_USERNAME:" in SOURCE
        assert SOURCE.index("load_config_file(cfg_path)") < SOURCE.index("if len(sys.argv) == 1 and not LASTFM_USERNAME:")

    def test_a_declined_target_ends_the_section_without_asking_to_persist_it(self, capsys):
        state = monitor.WizardSetupState("config", "env", {})
        script = Script(["", "n"])

        monitor._wizard_collect_target_section(state, input_func=script)

        assert state.target == ""
        assert "No target selected." in capsys.readouterr().out
        assert script.answers == []


class TestTheRefusals:

    def test_setup_needs_a_terminal(self, tmp_path):
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / "lastfm_monitor.py"), "--setup"], capture_output=True, text=True, cwd=tmp_path, stdin=subprocess.DEVNULL)

        assert result.returncode == 1
        assert "The setup wizard needs an interactive terminal (TTY)." in result.stdout
        assert "Guide:" in result.stdout
        assert list(tmp_path.iterdir()) == []

    # The dotenv file the wizard is about to write is its destination, so naming one that is absent is not a problem
    def test_setup_is_not_warned_that_the_dotenv_file_it_writes_is_missing(self, tmp_path):
        arguments = [sys.executable, str(PROJECT_ROOT / "lastfm_monitor.py"), "--setup", "--config-file", str(tmp_path / "absent.conf"), "--env-file", str(tmp_path / "absent.env")]
        result = subprocess.run(arguments, capture_output=True, text=True, cwd=tmp_path, stdin=subprocess.DEVNULL)

        assert "does not exist" not in result.stdout + result.stderr
        assert "The setup wizard needs an interactive terminal (TTY)." in result.stdout

    @pytest.mark.parametrize("config_file, env_file, expected", [
        ("none", None, "nowhere to write the configuration"),
        (None, "none", "nowhere to write the secrets"),
    ])
    def test_the_disabled_sentinel_leaves_nowhere_to_write(self, tmp_path, capsys, config_file, env_file, expected):
        code = monitor.run_setup_wizard(config_file=config_file or str(tmp_path / "lastfm_monitor.conf"), env_file=env_file or str(tmp_path / ".env"), interactive=True)

        assert code == 1
        output = capsys.readouterr().out
        assert expected in output
        assert "To fix: Replace" in output

    # A destination naming a file that is not there yet is what setup is for
    def test_a_missing_config_path_is_not_an_error_for_setup(self):
        assert "if not cfg_path and CLI_CONFIG_PATH and not CONFIG_DISCOVERY_DISABLED and not args.setup:" in SOURCE


class TestTheAnswerNormalizers:

    @pytest.mark.parametrize("answer, seconds", [("120", 120), ("30s", 30), ("2m", 120), ("1.5h", 5400), ("1h 30m", 5400), ("1d", 86400), ("0", None), ("", None), ("later", None), ("5x", None), ("5!", None), ("2 minutes", 120)])
    def test_a_duration_is_read_the_way_it_is_typed(self, answer, seconds):
        assert monitor.parse_duration_input(answer) == seconds

    @pytest.mark.parametrize("answer, username", [
        ("someuser", "someuser"),
        ("  someuser  ", "someuser"),
        ("https://www.last.fm/user/someuser", "someuser"),
        ("https://www.last.fm/user/someuser/library", "someuser"),
        ("last.fm/user/some.user", "some.user"),
        ("https://www.last.fm/pl/user/someuser", "someuser"),
        ("https://www.last.fm/user/some%20user", ""),
        ("https://www.last.fm/about", ""),
        ("", ""),
    ])
    def test_a_username_is_read_from_a_name_or_a_profile_url(self, answer, username):
        assert monitor.normalize_lastfm_username(answer) == username


class TestEveryRejectedAnswerHasAWayOut:

    # A loop that only re-asks never ends for anyone who cannot answer it, so each one offers the way out itself
    def test_every_wizard_loop_offers_an_escape(self):
        # Enter takes the shown default in these two, and the other two end through a helper that offers the escape
        answered_another_way = {"_wizard_ask_yes_no", "_wizard_ask_choice", "_wizard_collect_email_section", "_wizard_review_setup"}
        for node in ast.parse(SOURCE).body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("_wizard_"):
                continue
            if not any(isinstance(loop, ast.While) and isinstance(loop.test, ast.Constant) and loop.test.value is True for loop in ast.walk(node)):
                continue
            called = {call.func.id for call in ast.walk(node) if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)}
            assert "_wizard_offer_retry" in called or node.name in answered_another_way, f"{node.name} loops with no way out"

    def test_a_rejected_number_keeps_the_default(self, capsys):
        script = Script(["70000", "n"])

        assert monitor._wizard_ask_positive_int("SMTP port", 587, maximum=65535, input_func=script) == 587
        assert "Keeping 587." in capsys.readouterr().out
        assert script.answers == []

    def test_a_rejected_number_can_be_entered_again(self):
        assert monitor._wizard_ask_positive_int("SMTP port", 587, maximum=65535, input_func=Script(["70000", "y", "2525"])) == 2525

    def test_a_rejected_duration_keeps_the_default(self, capsys):
        script = Script(["later", "n"])

        assert monitor._wizard_ask_duration("Polling interval while the user is listening (seconds or use s/m/h/d)", 60, input_func=script) == 60
        assert "Keeping 60s - 1m." in capsys.readouterr().out
        # The hint the question carries belongs in the prompt, not in the offer that repeats it
        assert "Try entering the Polling interval while the user is listening again? [Y/n]: " in script.prompts

    def test_a_rejected_config_destination_keeps_the_current_one(self, tmp_path, capsys):
        state = monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(tmp_path / ".env"), {})

        monitor._wizard_collect_destination_section(state, input_func=Script([str(tmp_path), "n", ""]))

        assert Path(state.config_path) == tmp_path / "lastfm_monitor.conf"
        assert f"Keeping {tmp_path / 'lastfm_monitor.conf'}." in capsys.readouterr().out

    @pytest.mark.parametrize("answer", ["none", "{config}"])
    def test_a_rejected_dotenv_destination_keeps_the_current_one(self, tmp_path, capsys, answer):
        state = monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(tmp_path / ".env"), {})

        monitor._wizard_collect_destination_section(state, input_func=Script(["", answer.format(config=tmp_path / "lastfm_monitor.conf"), "n"]))

        assert Path(state.env_path) == tmp_path / ".env"
        assert state.config_values["DOTENV_FILE"] == str(tmp_path / ".env")
        assert f"Keeping {tmp_path / '.env'}." in capsys.readouterr().out


# Builds the state an email section starts from, with one shipped placeholder among the saved values
def email_state(**overrides):
    values = dict(monitor._config_template_defaults())
    values.update({"SMTP_HOST": "mail.example.test", "SMTP_PORT": 2525, "SMTP_USER": "user@example.test", "SENDER_EMAIL": "your_sender_email", "RECEIVER_EMAIL": "to@example.test"})
    values.update(overrides)
    return monitor.WizardSetupState("config", "env", values)


# The advice a failing sign-in returns, either kind
def smtp_advice(retryable):
    code = "smtp.connection" if retryable else "smtp.authentication"
    return monitor.make_recovery_advice(code, "The mail server refused the sign-in", "Use an app password", retryable)


class TestTheMailServerSignIn:

    def test_the_questions_come_in_one_order_with_the_saved_values_offered(self):
        state = email_state()
        script = Script(["y", "", "", "", "", "sender@example.test", "", "1"])

        monitor._wizard_collect_email_section(state, input_func=script, getpass_func=Script([""]))

        assert script.prompts == [
            "Configure email notifications? [Y/n]: ",
            "SMTP host [mail.example.test]: ",
            "SMTP port [2525]: ",
            "Enable TLS/SSL for SMTP? [Y/n]: ",
            "SMTP username [user@example.test]: ",
            # The shipped placeholder is filtered out, so setup never offers 'your_sender_email' back
            "Sender email: ",
            "Receiver email [to@example.test]: ",
            "Choose [1-3]: ",
        ]

    # The hidden prompt comes last, so every visible answer is on screen before the password is typed
    def test_the_password_is_asked_after_the_last_visible_answer(self):
        state = email_state()
        secrets = Script(["typed-password"])

        monitor._wizard_collect_email_section(state, input_func=Script(["y", "", "", "", "", "sender@example.test", "", "1"]), getpass_func=secrets)

        assert secrets.prompts == ["SMTP password: "]

    def test_the_sign_in_gets_the_collected_settings_once(self, monkeypatch):
        calls = []
        monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: calls.append((values, password)))
        state = email_state()

        monitor._wizard_collect_email_section(state, input_func=Script(["y", "smtp.example.test", "587", "", "user", "from@example.test", "to@example.test", "1"]), getpass_func=Script(["typed-password"]))

        assert len(calls) == 1
        assert calls[0] == ({"SMTP_HOST": "smtp.example.test", "SMTP_PORT": 587, "SMTP_SSL": True, "SMTP_USER": "user", "SENDER_EMAIL": "from@example.test", "RECEIVER_EMAIL": "to@example.test"}, "typed-password")

    def test_a_refused_sign_in_asks_the_settings_again(self, monkeypatch):
        outcomes = [smtp_advice(False), None]
        monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: outcomes.pop(0))
        state = email_state()
        # Answer the section, accept the retry, then answer it again with a different host
        script = Script(["y", "", "", "", "", "sender@example.test", "", "y", "smtp.second.test", "", "", "", "sender@example.test", "", "1"])

        monitor._wizard_collect_email_section(state, input_func=script, getpass_func=Script(["", ""]))

        assert outcomes == []
        assert state.config_values["SMTP_HOST"] == "smtp.second.test"
        assert state.config_values["ACTIVE_NOTIFICATION"] is True

    # A host that cannot be reached is usually a laptop offline, so six correct answers are not thrown away
    def test_declining_a_retryable_failure_keeps_the_settings(self, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: smtp_advice(True))
        state = email_state()

        monitor._wizard_collect_email_section(state, input_func=Script(["y", "smtp.example.test", "", "", "user", "from@example.test", "to@example.test", "n", "1"]), getpass_func=Script([""]))

        assert state.config_values["SMTP_HOST"] == "smtp.example.test"
        assert state.config_values["ACTIVE_NOTIFICATION"] is True
        assert "Run --doctor to check the sign-in again." in capsys.readouterr().out

    # A rejected sign-in cannot start working on its own, so half a mail server is never written
    def test_declining_a_rejected_sign_in_switches_every_email_alert_off(self, wizard, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: smtp_advice(False))

        code, _script = wizard(full_run_answers(email=["y", "smtp.example.test", "", "", "user", "from@example.test", "to@example.test", "n"]), secrets=("api-key", "api-secret", ""))

        assert code == 0
        written = config_values(tmp_path / "lastfm_monitor.conf")
        assert all(written[key] is False for key in monitor.WIZARD_EMAIL_NOTIFICATION_KEYS)
        assert written["SMTP_HOST"] == monitor._config_template_defaults()["SMTP_HOST"]

    # The check has to go through the same sign-in the real send uses, and leave no setting applied behind it
    def test_the_check_uses_the_real_sign_in_and_restores_the_globals(self, real_smtp_sign_in, monkeypatch):
        calls = []

        def sign_in(ssl_enabled, smtp_timeout=None):
            calls.append((ssl_enabled, smtp_timeout, monitor.SMTP_HOST, monitor.SMTP_PASSWORD))
            raise smtplib.SMTPAuthenticationError(535, b"denied")

        monkeypatch.setattr(monitor, "smtp_connect_and_login", sign_in)
        monkeypatch.setattr(monitor, "SMTP_HOST", "before.example.test")
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "saved-password")

        advice = monitor._wizard_verify_smtp({"SMTP_HOST": "typed.example.test", "SMTP_SSL": True}, "")

        assert calls == [(True, monitor.WIZARD_SMTP_TIMEOUT, "typed.example.test", "saved-password")]
        assert advice is not None and advice.code == "smtp.authentication"
        assert (monitor.SMTP_HOST, monitor.SMTP_PASSWORD) == ("before.example.test", "saved-password")


class TestASecretSwitchedOff:

    def test_the_disable_option_queues_an_empty_value(self, monkeypatch, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("NTFY_ACCESS_TOKEN=saved-token\n", encoding="utf-8")
        state = monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(env_path), {})

        monitor._wizard_collect_ntfy_access_token(state, input_func=Script(["3"]), getpass_func=Script([]))

        assert state.secret_updates == {"NTFY_ACCESS_TOKEN": ""}

    def test_saving_removes_the_assignment_from_the_dotenv_file(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("NTFY_ACCESS_TOKEN=saved-token\nSMTP_PASSWORD=kept\n", encoding="utf-8")

        monitor.update_dotenv_file(env_path, {"NTFY_ACCESS_TOKEN": ""})

        assert env_path.read_text(encoding="utf-8") == "SMTP_PASSWORD=kept\n"
        assert monitor._dotenv_contains_key(env_path, "NTFY_ACCESS_TOKEN") is False

    # Nothing to remove and nothing to store means no file, so a cleared secret cannot create an empty one
    def test_a_run_that_only_clears_a_missing_secret_writes_no_dotenv_file(self, wizard, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "already-configured")
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", "already-configured")
        monkeypatch.setenv("NTFY_ACCESS_TOKEN", "exported-token")
        monkeypatch.setenv("WEBHOOK_URL", "https://ntfy.sh/private-topic")

        # Keep the saved webhook URL, then switch the exported ntfy token off, so the only queued secret is the clear
        code, _script = wizard(full_run_answers(auth=["n"], webhook=["y", "2", "1", "3", "1"]), secrets=())

        assert code == 0
        assert not (tmp_path / ".env").exists()


class TestTheHiddenPrompt:

    # A debug trace fired while a secret is being typed is the one thing the tool must not print
    def test_the_wizard_reads_a_secret_with_debug_off(self, monkeypatch):
        monkeypatch.setattr(monitor, "DEBUG_MODE", True)
        seen = []

        def hidden(prompt=""):
            seen.append(monitor.DEBUG_MODE)
            return "api-key-value"

        assert monitor._wizard_ask_secret("Last.fm API key", getpass_func=hidden) == "api-key-value"
        assert seen == [False]
        assert monitor.DEBUG_MODE is True

    def test_an_interrupt_restores_the_debug_mode(self, monkeypatch):
        monkeypatch.setattr(monitor, "DEBUG_MODE", True)

        def interrupt(prompt=""):
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            monitor._wizard_ask_secret("Last.fm API key", getpass_func=interrupt)
        assert monitor.DEBUG_MODE is True


# Answers each question the way a terminal does, echoing the prompt and the answer into the transcript
class Terminal:
    def __init__(self, answers):
        self.answers = list(answers)

    def __call__(self, prompt=""):
        assert self.answers, f"the wizard asked more than the script answers: {prompt!r}"
        answer = self.answers.pop(0)
        print(f"{prompt}{answer}")
        return answer


# Echoes a hidden prompt without its answer, which is what a terminal shows while a secret is typed
class HiddenTerminal(Terminal):
    def __call__(self, prompt=""):
        answer = self.answers.pop(0)
        print(prompt)
        return answer


# Runs the wizard against an echoing terminal and returns everything it printed
@pytest.fixture
def transcript(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "_wizard_verify_lastfm_credentials", lambda api_key, api_secret: None)
    monkeypatch.setattr(monitor, "run_doctor", lambda **kwargs: 0)
    monkeypatch.chdir(tmp_path)

    runs = []

    def run(answers, secrets=("api-key", "api-secret")):
        # Each run gets its own destinations, so a second one is not asked to replace the first one's config
        workspace = tmp_path / f"run{len(runs)}"
        workspace.mkdir()
        runs.append(workspace)
        monitor.run_setup_wizard(config_file=str(workspace / "lastfm_monitor.conf"), env_file=str(workspace / ".env"), input_func=Terminal(answers), getpass_func=HiddenTerminal(secrets), interactive=True)
        return capsys.readouterr().out

    return run


# The frame is what a user recognizes when they set up the second tool, so it is pinned from the transcript
class TestTheFrameAroundTheQuestions:

    def test_the_destination_block_shares_one_column(self, transcript, tmp_path):
        printed = transcript(full_run_answers())

        assert "\nDetected install method: " in printed
        for label in ("Configuration:", "Dotenv:"):
            line = next(line for line in printed.splitlines() if line.startswith(label))
            assert line.index(line.split(":", 1)[1].strip()) == 24

    def test_every_question_group_opens_after_one_blank_line(self, transcript):
        printed = transcript(full_run_answers())

        for opener in [
            "Last.fm username or profile URL to monitor",
            "Polling interval while the user is not listening",
            "Create or view your Last.fm API key",
            "Use Spotify for track details?",
            "Watch for follower changes?",
            "Write the normal per-target log file?",
            "Configure email notifications?",
            "Set up webhook alerts",
        ]:
            assert f"\n\n{opener}" in printed, f"{opener!r} does not open a group"
        assert "\n\n\n" not in printed

    def test_each_block_heading_stands_alone(self, transcript):
        printed = transcript(full_run_answers())

        for heading in ("Setup summary", "Saved files", "Next steps"):
            assert f"\n\n{heading}\n\n" in printed

    def test_the_summary_values_share_one_column(self, transcript):
        printed = transcript(full_run_answers())

        summary = [line for line in printed.split("Setup summary\n\n", 1)[1].split("\n\n", 1)[0].splitlines() if ":" in line]

        offsets = {len(line) - len(line.split(":", 1)[1].lstrip()) for line in summary}
        # The width comes from the longest label rather than from a constant, so one column is the whole rule
        assert offsets == {max(len(line.split(":", 1)[0]) for line in summary) + 2}

    # A dotenv file that was never written must not appear as a saved file or in the commands printed under it
    def test_saved_files_and_the_printed_commands_name_only_what_exists(self, transcript, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "already-configured")
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", "already-configured")

        printed = transcript(full_run_answers(auth=["n"]), secrets=())

        assert not (tmp_path / "run0" / ".env").exists()
        assert "  Secrets:" not in printed
        assert "--env-file" not in printed.split("Next steps", 1)[1]

    def test_the_doctor_offer_follows_the_target(self, transcript):
        with_target = transcript(full_run_answers())
        without_target = transcript(full_run_answers(target=["", "n"], review=["1"], doctor=[]))

        assert "Run doctor now?" in with_target
        assert "Run doctor now?" not in without_target
        assert "\n\n\n" not in without_target


# Typing a secret only to be asked whether it may be stored is one question too late
class TestASavedCredentialIsSettledBeforeTheHiddenPrompt:

    # Builds a state whose dotenv file already holds the named secrets
    def state_with_saved_secrets(self, tmp_path, names, in_effect=True):
        env_path = tmp_path / ".env"
        env_path.write_text("".join(f"{name}=saved-{name.casefold()}\n" for name in names), encoding="utf-8")
        values = dict(monitor._config_template_defaults())
        if in_effect:
            values.update({name: f"saved-{name.casefold()}" for name in names})
        return monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(env_path), values)

    def test_the_lastfm_pair_is_asked_about_once(self, tmp_path):
        state = self.state_with_saved_secrets(tmp_path, ("LASTFM_API_KEY", "LASTFM_API_SECRET"))
        script = Script(["y"])

        monitor._wizard_collect_auth_section(state, input_func=script, getpass_func=Script(["new-key", "new-secret"]), validator=lambda api_key, api_secret: None)

        assert script.prompts == ["Replace the Last.fm API credentials already configured? [y/N]: "]
        assert state.secret_updates == {"LASTFM_API_KEY": "new-key", "LASTFM_API_SECRET": "new-secret"}

    def test_the_spotify_pair_is_asked_about_once(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "spotify_get_access_token", lambda client_id, client_secret: "token")
        state = self.state_with_saved_secrets(tmp_path, ("SP_CLIENT_ID", "SP_CLIENT_SECRET"))
        script = Script(["y", "y", "n", "y", ""])

        monitor._wizard_collect_spotify_section(state, input_func=script, getpass_func=Script(["new-id", "new-secret"]))

        assert script.prompts[3] == "Replace the Spotify app credentials already configured? [y/N]: "
        assert len(script.prompts) == 5
        assert state.secret_updates == {"SP_CLIENT_ID": "new-id", "SP_CLIENT_SECRET": "new-secret"}

    # A dotenv file the run never loaded still holds the value the wizard would overwrite
    def test_a_pair_saved_only_in_the_dotenv_file_still_gets_the_question(self, tmp_path):
        state = self.state_with_saved_secrets(tmp_path, ("LASTFM_API_KEY", "LASTFM_API_SECRET"), in_effect=False)
        script = Script(["n"])

        monitor._wizard_collect_auth_section(state, input_func=script, getpass_func=Script([]), validator=lambda api_key, api_secret: None)

        assert script.prompts == ["Replace the Last.fm API credentials already configured? [y/N]: "]
        assert state.secret_updates == {}

    def test_declining_the_replacement_never_opens_the_hidden_prompt(self, tmp_path):
        state = self.state_with_saved_secrets(tmp_path, ("LASTFM_API_KEY", "LASTFM_API_SECRET"))
        hidden = Script([])

        monitor._wizard_collect_auth_section(state, input_func=Script(["n"]), getpass_func=hidden, validator=lambda api_key, api_secret: None)

        assert hidden.prompts == []
        assert state.secret_updates == {}


# A required question that only re-asks is a trap, so every one of them is answered blank here and then declined
class TestEveryRequiredQuestionCanBeAbandoned:

    # How a blank answer is survivable at each prompt the wizard marks required
    COVERAGE = {
        ("_wizard_ask_positive_int", None): "the shown default is a number, so a blank answer is never empty",
        ("_wizard_collect_target_section", None): "declining ends the target section without asking to persist it",
        ("_wizard_collect_email_section", "SMTP host"): "declining switches email and its alerts off",
        ("_wizard_collect_email_section", "SMTP username"): "declining switches email and its alerts off",
        ("_wizard_collect_email_section", "Sender email"): "declining switches email and its alerts off",
        ("_wizard_collect_email_section", "Receiver email"): "declining switches email and its alerts off",
        ("_wizard_collect_destination_section", "Configuration file destination"): "the shown default is the current path",
        ("_wizard_collect_destination_section", "Dotenv file destination"): "the shown default is the current path",
    }

    def test_every_required_prompt_is_accounted_for(self):
        found = set()
        for node in ast.walk(ast.parse(SOURCE)):
            if not isinstance(node, ast.FunctionDef):
                continue
            for call in ast.walk(node):
                if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != "_wizard_ask_text":
                    continue
                if not any(keyword.arg == "required" and getattr(keyword.value, "value", False) is True for keyword in call.keywords):
                    continue
                question = call.args[0].value if call.args and isinstance(call.args[0], ast.Constant) else None
                found.add((node.name, question))
        assert found == set(self.COVERAGE)

    @pytest.mark.parametrize("answers, abandoned", [
        (["y", "", "n"], "SMTP host"),
        (["y", "smtp.example.test", "", "", "", "n"], "SMTP username"),
        (["y", "smtp.example.test", "", "", "user", "", "n"], "Sender email"),
        (["y", "smtp.example.test", "", "", "user", "from@example.test", "", "n"], "Receiver email"),
    ])
    def test_a_blank_mail_server_answer_switches_the_channel_off(self, capsys, answers, abandoned):
        state = monitor.WizardSetupState("config", "env", dict(monitor._config_template_defaults()))
        script = Script(answers)
        hidden = Script([])

        monitor._wizard_collect_email_section(state, input_func=script, getpass_func=hidden)

        assert script.answers == [], f"the section continued past the abandoned {abandoned}"
        assert hidden.prompts == [], "the password prompt opened for a channel that was switched off"
        assert f"Try entering the {abandoned} again?" in "".join(script.prompts)
        assert all(state.config_values[key] is False for key in monitor.WIZARD_EMAIL_NOTIFICATION_KEYS)
        assert monitor._wizard_email_enabled(state.config_values) is False
        # Half a mail server must not survive the answer that was abandoned
        assert state.config_values["SMTP_HOST"] == monitor._config_template_defaults()["SMTP_HOST"]
        assert "Email notifications stay off until every mail server setting is answered." in capsys.readouterr().out


# A blank answer at a hidden prompt means keep what is stored, which is only true if nothing is queued for it
class TestABlankSecretAnswer:

    def test_the_queue_helper_refuses_an_empty_value(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("SMTP_PASSWORD=saved-password\n", encoding="utf-8")
        state = monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(env_path), {})
        script = Script([])

        assert monitor._wizard_queue_secret(state, "SMTP_PASSWORD", "", input_func=script) is False
        assert script.prompts == []
        assert state.secret_updates == {}

    # The sign-in proves the stored password, so a blank answer must not be read as a replacement
    def test_a_blank_password_keeps_the_saved_one(self, tmp_path, monkeypatch):
        checked = []
        monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: checked.append(password))
        env_path = tmp_path / ".env"
        env_path.write_text("SMTP_PASSWORD=saved-password\n", encoding="utf-8")
        state = monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(env_path), dict(monitor._config_template_defaults()))
        script = Script(["y", "smtp.example.test", "", "", "user", "from@example.test", "to@example.test", "1"])

        monitor._wizard_collect_email_section(state, input_func=script, getpass_func=Script([""]))

        # The caller resolves the saved value, so the check signs in with it rather than leaving the fallback to do it
        assert checked == ["saved-password"]
        assert state.secret_updates == {}
        assert not any("Replace" in prompt for prompt in script.prompts)
        assert env_path.read_text(encoding="utf-8") == "SMTP_PASSWORD=saved-password\n"

    def test_a_blank_ntfy_token_queues_nothing(self, tmp_path):
        state = monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(tmp_path / ".env"), {})

        monitor._wizard_collect_ntfy_access_token(state, input_func=Script(["y"]), getpass_func=Script([""]))

        assert state.secret_updates == {}

    def test_a_secret_free_rerun_leaves_an_existing_dotenv_untouched(self, wizard, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "already-configured")
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", "already-configured")
        env_path = tmp_path / ".env"
        original = 'LASTFM_API_KEY="already-configured"\nSMTP_PASSWORD="saved-password"\n'
        env_path.write_text(original, encoding="utf-8")

        code, _script = wizard(full_run_answers(auth=["n"]), secrets=())

        assert code == 0
        assert env_path.read_bytes() == original.encode("utf-8")


# Four ways a run can reach the end: no target, a declined doctor, a failed doctor and a passed one
class TestTheFlowAfterSave:

    # Records what the wizard would have launched instead of replacing the test process
    @pytest.fixture
    def launched(self, monkeypatch):
        calls = []
        monkeypatch.setattr(monitor, "_wizard_launch_monitor", lambda arguments: calls.append(list(arguments)) or 0)
        return calls

    def test_without_a_target_neither_offer_is_made(self, wizard, launched, capsys):
        code, script = wizard(full_run_answers(target=["", "n"], review=["1"], doctor=[]))

        assert code == 0
        assert not any(prompt.startswith(("Run doctor now?", "Start monitoring now?")) for prompt in script.prompts)
        assert launched == []

    def test_a_declined_doctor_ends_on_the_next_steps_block(self, wizard, launched, capsys):
        code, script = wizard(full_run_answers(doctor=["n"]))

        assert code == 0
        assert any(prompt.startswith("Run doctor now?") for prompt in script.prompts)
        assert not any(prompt.startswith("Start monitoring now?") for prompt in script.prompts)
        assert "Start monitoring:" in capsys.readouterr().out
        assert launched == []

    # Only a doctor run that passed proves the saved setup can monitor
    def test_a_failed_doctor_removes_the_launch_offer(self, wizard, launched, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "run_doctor", lambda **kwargs: 1)

        code, script = wizard(full_run_answers(doctor=["y"]))

        assert code == 0
        assert "After Doctor passes, start monitoring:" in capsys.readouterr().out
        assert not any(prompt.startswith("Start monitoring now?") for prompt in script.prompts)
        assert launched == []

    def test_a_passed_doctor_offers_the_launch(self, wizard, launched, tmp_path, capsys):
        code, script = wizard(full_run_answers(doctor=["y", "y"]))

        assert code == 0
        assert any(prompt.startswith("Start monitoring now?") for prompt in script.prompts)
        assert "Start monitoring:" in capsys.readouterr().out
        assert launched and str(tmp_path / "lastfm_monitor.conf") in launched[0]

    def test_the_doctor_it_offers_is_the_one_the_command_runs(self):
        # One implementation, called from the flag and from the wizard, so the two verdicts cannot drift
        assert SOURCE.count("def run_doctor(") == 1
        assert "doctor_exit = run_doctor(" in SOURCE

    def test_setup_is_dispatched_before_the_connectivity_check(self):
        # The wizard writes files and needs no network, so an offline machine can still run it
        assert SOURCE.index("if args.setup:") < SOURCE.index("if not check_internet():")


# What Enter does on a rerun, channel by channel: a saved setup must not be switched off by accepting defaults
class TestTheValuesTheWizardStartsFrom:

    # The wizard saves the settings in effect, so a setting no question covers must not be switched on behind it
    def test_an_unset_flag_leaves_the_duration_mark_setting_alone(self, monkeypatch):
        monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", False)
        monkeypatch.setattr(monitor, "DO_NOT_SHOW_DURATION_MARKS", False)

        monitor.apply_cli_overrides(NoFlags())

        assert monitor.DO_NOT_SHOW_DURATION_MARKS is False

    def test_the_hide_flag_still_switches_the_marks_off(self, monkeypatch):
        monkeypatch.setattr(monitor, "DO_NOT_SHOW_DURATION_MARKS", False)

        monitor.apply_cli_overrides(NoFlags(hide_duration_source=True))

        assert monitor.DO_NOT_SHOW_DURATION_MARKS is True

    # Answering yes to the Spotify duration used to save a config that switched the marks off
    def test_taking_the_duration_from_spotify_keeps_the_marks_on(self, wizard, tmp_path):
        code, _script = wizard(full_run_answers(spotify=["y", "y", "n", "n"]))

        assert code == 0
        written = config_values(tmp_path / "lastfm_monitor.conf")
        assert written["USE_TRACK_DURATION_FROM_SPOTIFY"] is True
        assert written["DO_NOT_SHOW_DURATION_MARKS"] is False


class TestTheDefaultsOnARerun:

    def test_the_webhook_question_follows_the_saved_switch(self):
        values = dict(monitor._config_template_defaults())
        values["WEBHOOK_ENABLED"] = True
        state = monitor.WizardSetupState("config", "env", values)
        script = Script(["n"])

        monitor._wizard_collect_webhook_section(state, input_func=script, getpass_func=Script([]))

        assert script.prompts == ["Set up webhook alerts (Discord, ntfy etc.)? [Y/n]: "]

    @pytest.mark.parametrize("saved, hint, kept", [
        # Switching Spotify on for the first time proposes the duration, which is most of the reason to switch it on
        ({}, "[Y/n]", True),
        ({"USE_TRACK_DURATION_FROM_SPOTIFY": True}, "[Y/n]", True),
        ({"USE_TRACK_DURATION_FROM_SPOTIFY": False, "TRACK_SONGS": True}, "[y/N]", False),
    ])
    def test_the_duration_question_proposes_yes_until_it_has_been_answered(self, saved, hint, kept):
        values = dict(monitor._config_template_defaults())
        values.update(saved)
        state = monitor.WizardSetupState("config", "env", values)
        script = Script(["y", "", "", ""])

        monitor._wizard_collect_spotify_section(state, input_func=script, getpass_func=Script([]))

        assert script.prompts[1] == f"Take track duration from Spotify? Last.fm often lacks it or reports it wrong {hint}: "
        assert state.config_values["USE_TRACK_DURATION_FROM_SPOTIFY"] is kept

    @pytest.mark.parametrize("saved, hint", [
        ({}, "[y/N]"),
        ({"ACTIVE_NOTIFICATION": True}, "[Y/n]"),
        # The error alert ships on, so on its own it proposes email only once a mail server has been named
        ({"SMTP_HOST": "smtp.example.test"}, "[Y/n]"),
    ])
    def test_the_email_question_follows_the_saved_alerts(self, saved, hint):
        values = dict(monitor._config_template_defaults())
        values.update(saved)
        state = monitor.WizardSetupState("config", "env", values)
        script = Script(["n"])

        monitor._wizard_collect_email_section(state, input_func=script, getpass_func=Script([]))

        assert script.prompts == [f"Configure email notifications? {hint}: "]

    # Enter through the Custom branch must not switch alerts on that were never asked for
    def test_a_custom_alert_question_defaults_to_no(self):
        state = monitor.WizardSetupState("config", "env", dict(monitor._config_template_defaults()))
        available = monitor._wizard_available_alert_keys(state, monitor.WIZARD_EMAIL_NOTIFICATION_KEYS)
        script = Script(["3"] + [""] * len(available))

        monitor._wizard_collect_alert_preset(state, "Which email notifications should be enabled?", monitor.WIZARD_EMAIL_NOTIFICATION_KEYS, monitor.WIZARD_RECOMMENDED_EMAIL_KEYS, prefix="Email on ", input_func=script)

        assert all(prompt.endswith("[y/N]: ") for prompt in script.prompts[1:])
        assert all(state.config_values[key] is False for key in monitor.WIZARD_EMAIL_NOTIFICATION_KEYS)

    def test_a_declined_email_section_leaves_the_other_channel_alone(self):
        values = dict(monitor._config_template_defaults())
        values.update({"WEBHOOK_ACTIVE_NOTIFICATION": True, "WEBHOOK_ENABLED": True, "TRACK_SONGS": True})
        state = monitor.WizardSetupState("config", "env", values)

        monitor._wizard_collect_email_section(state, input_func=Script(["n"]), getpass_func=Script([]))

        assert state.config_values["WEBHOOK_ACTIVE_NOTIFICATION"] is True
        assert state.config_values["WEBHOOK_ENABLED"] is True
        assert state.config_values["TRACK_SONGS"] is True


# Setup reports the sign-in succeeded and then writes the files a restart reads, so the value it proves has to be
# the value the next run resolves. Startup prefers an export over the dotenv file and setup has to agree
def test_the_effective_secret_follows_the_startup_precedence(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text('SMTP_PASSWORD="saved-in-file"\n', encoding="utf-8")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "from-config-file", raising=False)

    assert monitor.effective_secret_after_setup("SMTP_PASSWORD", env_path, {}) == ("saved-in-file", False)
    assert monitor.effective_secret_after_setup("SMTP_PASSWORD", env_path, {"SMTP_PASSWORD": "accepted"}) == ("accepted", False)
    monkeypatch.setenv("SMTP_PASSWORD", "exported")
    assert monitor.effective_secret_after_setup("SMTP_PASSWORD", env_path, {"SMTP_PASSWORD": "accepted"}) == ("exported", True)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    assert monitor.effective_secret_after_setup("SMTP_PASSWORD", tmp_path / "absent.env", {}) == ("from-config-file", False)


# Keeping the saved password used to check the one just typed, which is the one thrown away
def test_a_declined_replacement_checks_the_password_that_is_kept(tmp_path, monkeypatch):
    checked = []
    env_path = tmp_path / ".env"
    env_path.write_text('SMTP_PASSWORD="saved-in-file"\n', encoding="utf-8")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password, **kwargs: checked.append(password))
    state = monitor.WizardSetupState(str(tmp_path / "lastfm_monitor.conf"), str(env_path), dict(monitor._config_template_defaults()))
    state.env_path = env_path

    monitor._wizard_collect_email_section(state, input_func=Script(["y", "smtp.example.test", "", "", "user", "from@example.test", "to@example.test", "n", "1"]), getpass_func=Script(["typed-new"]))

    assert checked == ["saved-in-file"]
    assert "SMTP_PASSWORD" not in state.secret_updates
