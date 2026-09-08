"""What a bare, mistaken or one-shot invocation prints: the welcome screen, the missing-target block and the screen clear."""

import io
import subprocess
import sys
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")


# A stream that reports whether it is a terminal, since the clear is skipped for redirected output
class Stream(io.StringIO):
    def __init__(self, tty):
        super().__init__()
        self._tty = tty

    def isatty(self):
        return self._tty


# Records the shell commands the screen clear would have run instead of running them
@pytest.fixture
def cleared(monkeypatch):
    calls = []
    monkeypatch.setattr(monitor.os, "system", lambda command: calls.append(command))
    return calls


class TestScreenClear:

    def test_a_terminal_is_cleared(self, cleared, monkeypatch):
        monkeypatch.setattr(monitor.sys, "stdout", Stream(True))
        monitor.clear_screen(True)
        assert len(cleared) == 1

    def test_redirected_output_is_not_cleared(self, cleared, monkeypatch):
        monkeypatch.setattr(monitor.sys, "stdout", Stream(False))
        monitor.clear_screen(True)
        assert cleared == []

    # The logger wrapper the monitoring run installs answers no isatty at all
    def test_a_stream_without_the_question_is_not_cleared(self, cleared, monkeypatch):
        monkeypatch.setattr(monitor.sys, "stdout", io.StringIO())
        monitor.clear_screen(True)
        assert cleared == []

    def test_a_disabled_clear_never_reaches_the_terminal_check(self, cleared, monkeypatch):
        monkeypatch.setattr(monitor.sys, "stdout", Stream(True))
        monitor.clear_screen(False)
        assert cleared == []

    def test_the_guard_lives_in_the_helper_rather_than_at_the_call_site(self):
        assert SOURCE.count("clear_screen(") == 2
        assert 'if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():' in SOURCE.split("def clear_screen")[1].split("\ndef ")[0]


class TestKeepTerminalHistory:

    @pytest.mark.parametrize("flag", monitor.KEEP_HISTORY_FLAGS)
    def test_a_one_shot_command_keeps_the_scrollback(self, flag, monkeypatch):
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor.py", flag])
        assert monitor.keep_terminal_history() is True

    def test_a_monitoring_run_does_not(self, monkeypatch):
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor.py", "some_user", "--verbose"])
        assert monitor.keep_terminal_history() is False

    def test_every_secret_command_is_covered(self):
        assert set(monitor.SECRET_ACTION_FLAGS) <= set(monitor.KEEP_HISTORY_FLAGS)
        assert {"--doctor", "--send-test-email", "--send-test-webhook", "--help", "-h"} <= set(monitor.KEEP_HISTORY_FLAGS)

    # A module constant is evaluated at import, so splicing a tuple defined below it raises NameError
    def test_the_flag_list_is_defined_after_the_tuple_it_splices(self):
        assert SOURCE.index("SECRET_ACTION_FLAGS = (") < SOURCE.index("KEEP_HISTORY_FLAGS = (")

    def test_the_secret_commands_are_one_constant_rather_than_a_local_copy(self):
        assert "private_setup_flags" not in SOURCE
        assert SOURCE.count("SECRET_ACTION_FLAGS") >= 3

    def test_the_call_site_carries_the_policy(self):
        assert "clear_screen(CLEAR_SCREEN and not keep_terminal_history() and not DEBUG_MODE)" in SOURCE

    # argparse has not run when the screen is cleared, so the debug flag has to be read from the raw arguments
    def test_debug_mode_is_read_before_the_clear(self):
        assert SOURCE.index('if "--debug" in sys.argv:') < SOURCE.index("clear_screen(CLEAR_SCREEN and not")


class TestWelcomeScreen:

    @pytest.fixture(autouse=True)
    def as_a_pip_install(self, monkeypatch):
        monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, monitor.INSTALL_METHOD_PYPI)

    @pytest.fixture
    def screen(self, capsys):
        exit_code = monitor.print_welcome_screen()
        return exit_code, capsys.readouterr().out

    def test_the_accepted_target_form_opens_the_screen(self, screen):
        assert screen[1].splitlines()[0] == f"For <lastfm_username>, use the {monitor.LASTFM_TARGET_FORMS}."

    # One constant, so the welcome line and the rejection a mistyped target gets cannot drift apart
    def test_the_target_form_is_the_one_the_invalid_target_error_prints(self):
        advice = monitor.classify_recovery_error(ValueError("Invalid username supplied"))
        assert monitor.LASTFM_TARGET_FORMS in advice.fix

    @pytest.mark.parametrize("label, command", [
        ("Quickest start (already configured):", "lastfm_monitor <lastfm_username>"),
        ("Easiest start (guided setup wizard):", "lastfm_monitor --setup"),
        ("Check setup before monitoring:", "lastfm_monitor --doctor <lastfm_username>"),
        ("Show recent tracks and exit:", "lastfm_monitor -l <lastfm_username>"),
    ])
    def test_each_entry_is_a_label_then_its_indented_command(self, screen, label, command):
        lines = screen[1].splitlines()
        position = lines.index(label)
        assert lines[position + 1] == f"    {command}"
        assert lines[position + 2] == ""

    # A pipx user must not read a command that only works from a clone
    def test_every_command_is_rendered_for_the_detected_install(self, screen, monkeypatch):
        commands = [line.strip() for line in screen[1].splitlines() if line.startswith("    ")]
        assert commands and all(command.startswith("lastfm_monitor ") for command in commands)

    def test_the_two_single_lines_are_aligned_with_each_other(self, screen):
        lines = [line for line in screen[1].splitlines() if line.startswith(("Full options:", "Guide:"))]
        assert [line.index("lastfm_monitor") for line in lines[:1]] == [len("Full options: ")]
        assert lines[1].index("https://") == len("Full options: ")

    def test_the_guide_opens_the_page_rather_than_one_of_its_sections(self, screen):
        assert monitor.QUICK_START_GUIDE_URL.endswith("/setup-and-first-run/")
        assert f"Guide:        {monitor.QUICK_START_GUIDE_URL}" in screen[1]

    # Nothing on this screen was a question, so the bare invocation is still the usage error argparse reported
    def test_a_screen_that_asked_nothing_exits_as_a_usage_error(self, screen):
        assert screen[0] == 1

    def test_the_full_option_list_is_no_longer_what_an_empty_command_prints(self):
        assert "parser.print_help(sys.stderr)" not in SOURCE
        assert "if len(sys.argv) == 1 and not LASTFM_USERNAME:\n        sys.exit(print_welcome_screen())" in SOURCE

    def test_the_screen_and_the_doctor_print_a_command_the_same_way(self):
        assert SOURCE.count("_wizard_print_command(") == 8


class TestMissingTarget:

    def test_the_startup_gate_and_the_doctor_row_are_one_sentence(self, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
        report = monitor.DoctorReport()
        row = monitor.doctor_check_target(report)[0]
        advice = monitor.print_recovery_error(context="target.missing")
        assert row.label == advice.summary
        assert advice.summary in capsys.readouterr().out

    def test_the_block_is_printed_rather_than_the_help_screen(self, capsys):
        monitor.print_recovery_error(context="target.missing")
        printed = capsys.readouterr().out
        assert "* Error:" in printed and "To fix:" in printed and "Guide:" in printed
        assert len(printed.splitlines()) <= 5

    # The username is on the command line the user just typed, a credential may live in a file they never created
    def test_the_target_is_named_before_the_credentials(self):
        assert SOURCE.index('if not args.username and not (args.send_test_email or args.send_test_webhook):') < SOURCE.index('if not doctor_value_is_set(LASTFM_API_KEY):')

    # A forgotten username must not be reported as a network problem
    def test_the_target_is_named_before_the_connectivity_check(self):
        assert SOURCE.index('if not args.username and not (args.send_test_email or args.send_test_webhook):') < SOURCE.index("if not check_internet():")

    def test_the_gate_runs_after_the_dotenv_file_is_resolved(self):
        assert SOURCE.index('record_secret_source(secret, "environment" if secret in exported_secrets else "dotenv file")') < SOURCE.index('if not args.username and not (args.send_test_email or args.send_test_webhook):')

    # Both senders finish without a target, so neither may be turned into a target error
    def test_the_modes_that_need_no_target_are_named_in_the_condition(self):
        assert "not (args.send_test_email or args.send_test_webhook)" in SOURCE

    def test_the_narrow_check_stays_as_a_backstop(self):
        assert SOURCE.count('print_recovery_error(context="target.missing")') == 2


class TestEarlyOutputConfig:

    @pytest.fixture(autouse=True)
    def restore_setting(self):
        saved = monitor.CLEAR_SCREEN
        yield
        monitor.CLEAR_SCREEN = saved

    @pytest.mark.parametrize("arguments, expected", [
        (["--config-file", "custom.conf", "some_user"], "custom.conf"),
        (["--config-file=custom.conf"], "custom.conf"),
        (["some_user", "--verbose"], None),
        (["--config-file"], None),
    ])
    def test_the_config_path_is_read_from_the_raw_arguments(self, arguments, expected):
        assert monitor.early_config_file_argument(arguments) == expected

    def test_the_setting_is_applied_before_argparse_runs(self, tmp_path, monkeypatch):
        config = tmp_path / "lastfm_monitor.conf"
        config.write_text("CLEAR_SCREEN = False\n", encoding="utf-8")
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor.py", "--config-file", str(config), "some_user"])
        monitor.CLEAR_SCREEN = True
        monitor.apply_early_output_config()
        assert monitor.CLEAR_SCREEN is False

    def test_a_value_of_another_type_is_left_to_the_normal_config_load(self, tmp_path, monkeypatch):
        config = tmp_path / "lastfm_monitor.conf"
        config.write_text('CLEAR_SCREEN = "yes"\n', encoding="utf-8")
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor.py", "--config-file", str(config), "some_user"])
        monitor.CLEAR_SCREEN = True
        monitor.apply_early_output_config()
        assert monitor.CLEAR_SCREEN is True

    # The config file's own error reporting runs later, so this pass must stay silent whatever it finds
    @pytest.mark.parametrize("content", ["CLEAR_SCREEN = (\n", "import os\n", "UNKNOWN_SETTING = 1\n"])
    def test_an_unreadable_config_file_is_left_to_the_normal_config_load(self, tmp_path, monkeypatch, capsys, content):
        config = tmp_path / "lastfm_monitor.conf"
        config.write_text(content, encoding="utf-8")
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor.py", "--config-file", str(config), "some_user"])
        monitor.CLEAR_SCREEN = True
        monitor.apply_early_output_config()
        assert monitor.CLEAR_SCREEN is True
        assert capsys.readouterr().out == ""

    def test_a_missing_file_changes_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor.py", "--config-file", str(tmp_path / "absent.conf")])
        monitor.CLEAR_SCREEN = True
        monitor.apply_early_output_config()
        assert monitor.CLEAR_SCREEN is True

    def test_the_config_file_is_read_before_the_screen_is_cleared(self):
        assert SOURCE.index("apply_early_output_config()\n\n    # Read straight from sys.argv") < SOURCE.index("clear_screen(CLEAR_SCREEN and not")


class TestConfigDiscoveryDisabled:

    @pytest.fixture(autouse=True)
    def restore_flag(self):
        saved = (monitor.CONFIG_DISCOVERY_DISABLED, monitor.CLEAR_SCREEN)
        yield
        monitor.CONFIG_DISCOVERY_DISABLED, monitor.CLEAR_SCREEN = saved

    @pytest.fixture
    def discoverable(self, tmp_path, monkeypatch):
        config = tmp_path / monitor.DEFAULT_CONFIG_FILENAME
        config.write_text("CLEAR_SCREEN = False\n", encoding="utf-8")
        # A file actually named 'none', so the sentinel cannot be satisfied by the path simply not existing
        (tmp_path / "none").write_text("CLEAR_SCREEN = False\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        return config

    def test_a_config_file_in_the_working_directory_is_found(self, discoverable):
        assert monitor.find_config_file() == str(discoverable)

    @pytest.mark.parametrize("sentinel", ["none", "NONE", "None"])
    def test_the_sentinel_selects_no_file(self, sentinel, discoverable):
        assert monitor.find_config_file(sentinel) is None

    # Clearing the path is not enough, since a caller that runs discovery again would read the working directory
    def test_the_flag_switches_the_search_off_for_a_caller_that_passes_no_path(self, discoverable):
        monitor.CONFIG_DISCOVERY_DISABLED = True
        assert monitor.find_config_file() is None

    def test_a_missing_path_is_still_an_error(self, tmp_path):
        assert monitor.find_config_file(str(tmp_path / "absent.conf")) is None
        assert 'if not cfg_path and CLI_CONFIG_PATH and not CONFIG_DISCOVERY_DISABLED and not args.setup:' in SOURCE

    # A printed command has to read back the setup the run used, so the sentinel is carried unexpanded
    def test_a_printed_command_carries_the_sentinel(self, monkeypatch):
        monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "none")
        monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
        monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, monitor.INSTALL_METHOD_PYPI)
        assert monitor.render_command(["<lastfm_username>"]) == "lastfm_monitor <lastfm_username> --config-file none --env-file none"

    def test_a_real_run_prints_the_command_it_was_given(self, tmp_path):
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / "lastfm_monitor.py"), "--config-file", "none", "--env-file", "none"], capture_output=True, text=True, cwd=tmp_path)
        assert result.returncode == 1
        assert "<lastfm_username> --config-file none --env-file none" in result.stdout

    def test_the_early_output_pass_reads_no_file_either(self, discoverable, monkeypatch):
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor.py", "--config-file", "none", "some_user"])
        monitor.CLEAR_SCREEN = True
        monitor.apply_early_output_config()
        assert monitor.CLEAR_SCREEN is True

    # One state, one row: the sentinel and an empty search report the same pair
    def test_the_doctor_reports_one_row_for_no_configuration_file(self):
        labels = [check.label for check in monitor.doctor_check_configuration()]
        assert "No configuration file selected" in labels
        assert "No dotenv file selected" in labels
