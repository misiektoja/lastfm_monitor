"""The guided setup: answers held until Save, the review summary, per-section editing and the files it writes."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")


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
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: None)
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
