"""Install detection and the commands the tool prints for it, including the paths a printed command has to carry."""

import inspect
import ast
import re
import shlex
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# A command the reader is meant to paste, written out by hand instead of rendered for their install
HARDCODED_COMMAND = re.compile(r"\blastfm_monitor\s+(?:--|<)|\bpython3\s+lastfm_monitor\.py\b")


# Returns every string literal that reaches the reader through a print or a piece of recovery advice
def printed_string_literals():
    tree = ast.parse((PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8"))
    literals = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id not in ("print", "advice", "make_recovery_advice", "print_recovery_error"):
            continue
        for argument in list(node.args) + [keyword.value for keyword in node.keywords]:
            for part in ast.walk(argument):
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    literals.append(part.value)
    return literals


class TestInstallDetection:
    def test_a_script_run_is_detected_as_a_manual_install(self, monkeypatch):
        monkeypatch.delenv(monitor.INSTALL_METHOD_ENV_VAR, raising=False)
        monkeypatch.setattr(monitor.sys, "argv", ["/opt/tools/lastfm_monitor.py", "someuser"])
        assert monitor.install_method() == monitor.INSTALL_METHOD_SCRIPT

    def test_a_console_script_run_is_detected_as_a_pypi_install(self, monkeypatch):
        monkeypatch.delenv(monitor.INSTALL_METHOD_ENV_VAR, raising=False)
        monkeypatch.setattr(monitor.sys, "argv", ["/usr/local/bin/lastfm_monitor", "someuser"])
        assert monitor.install_method() == monitor.INSTALL_METHOD_PYPI

    @pytest.mark.parametrize("override", ["pip", "manual", "PIP", " manual "])
    def test_the_environment_override_wins_over_detection(self, monkeypatch, override):
        monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, override)
        monkeypatch.setattr(monitor.sys, "argv", ["/opt/tools/lastfm_monitor.py"])
        assert monitor.install_method() == override.strip().casefold()

    def test_an_override_the_tool_cannot_produce_is_ignored(self, monkeypatch):
        monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, "docker")
        monkeypatch.setattr(monitor.sys, "argv", ["/opt/tools/lastfm_monitor.py"])
        assert monitor.install_method() == monitor.INSTALL_METHOD_SCRIPT

    def test_each_install_method_gets_its_own_command_prefix(self, monkeypatch):
        monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, "manual")
        monkeypatch.setattr(monitor.sys, "argv", ["/opt/tools/lastfm_monitor.py"])
        assert monitor.install_command_prefix() == ["python3", "lastfm_monitor.py"]
        monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, "pip")
        assert monitor.install_command_prefix() == ["lastfm_monitor"]


class TestArgumentQuoting:
    # A placeholder is documentation for the reader to replace, so quoting it would only be noise
    def test_a_placeholder_is_left_unquoted(self):
        assert monitor.quote_command_argument("<lastfm_username>") == "<lastfm_username>"

    # The property that matters is that pasting the rendered command yields one argument, not how it is quoted
    def test_a_path_with_a_space_survives_being_pasted(self):
        assert shlex.split(monitor.quote_command_argument("/tmp/some dir/.env")) == ["/tmp/some dir/.env"]

    def test_an_ordinary_value_is_left_alone(self):
        assert monitor.quote_command_argument("--send-test-webhook") == "--send-test-webhook"


class TestRenderedCommands:
    @pytest.fixture(autouse=True)
    def pypi_install(self, monkeypatch):
        monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, "pip")
        monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
        monkeypatch.setattr(monitor, "DOTENV_FILE", "")

    def test_a_command_starts_with_the_prefix_for_the_detected_install(self):
        assert monitor.render_command(["--send-test-webhook"]) == "lastfm_monitor --send-test-webhook"

    # A fix that tells the reader to retry against a different config sends them to check the wrong setup
    def test_the_files_this_run_was_given_are_carried_by_default(self, monkeypatch):
        monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/etc/lastfm.conf")
        monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/lastfm.env")
        assert monitor.render_command(["--send-test-email"]) == "lastfm_monitor --send-test-email --config-file /etc/lastfm.conf --env-file /etc/lastfm.env"

    def test_a_command_that_creates_a_new_file_carries_no_paths(self, monkeypatch):
        monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/etc/lastfm.conf")
        monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/lastfm.env")
        assert monitor.render_command(["--generate-config"], include_paths=False) == "lastfm_monitor --generate-config"

    def test_an_explicit_path_wins_over_the_active_one(self, monkeypatch):
        monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/lastfm.env")
        assert monitor.render_command(["--send-test-webhook"], env_path="/home/u/.env") == "lastfm_monitor --send-test-webhook --env-file /home/u/.env"

    def test_a_path_with_a_space_survives_the_paste(self, monkeypatch):
        monkeypatch.setattr(monitor, "DOTENV_FILE", "/tmp/some dir/.env")
        assert monitor.render_command(["--send-test-email"]) == "lastfm_monitor --send-test-email --env-file '/tmp/some dir/.env'"

    def test_a_placeholder_positional_stays_readable(self):
        assert monitor.render_command(["<lastfm_username>"]) == "lastfm_monitor <lastfm_username>"

    # "none" means dotenv loading is off, not that no file was named, so a retry has to read what this run read
    def test_a_reading_command_carries_the_dotenv_sentinel(self, monkeypatch):
        monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
        assert monitor.render_command(["--send-test-webhook"]) == "lastfm_monitor --send-test-webhook --env-file none"

    # The secret commands refuse the sentinel at their own argument gate, so carrying it would print a rejected command
    @pytest.mark.parametrize("flag", ["--set-lastfm-credentials", "--set-spotify-credentials", "--set-webhook-url"])
    def test_a_command_that_writes_the_dotenv_drops_the_sentinel(self, monkeypatch, flag):
        monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
        assert monitor.render_command([flag]) == f"lastfm_monitor {flag}"

    def test_a_command_that_writes_the_dotenv_still_carries_a_real_path(self, monkeypatch):
        monkeypatch.setattr(monitor, "DOTENV_FILE", "/etc/lastfm.env")
        assert monitor.render_command(["--set-webhook-url"]) == "lastfm_monitor --set-webhook-url --env-file /etc/lastfm.env"

    # Writing the dotenv says nothing about the config file, which the command still only reads
    def test_a_command_that_writes_the_dotenv_still_carries_the_config(self, monkeypatch):
        monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", "/etc/lastfm.conf")
        monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
        assert monitor.render_command(["--set-webhook-url"]) == "lastfm_monitor --set-webhook-url --config-file /etc/lastfm.conf"

    @pytest.mark.parametrize("arguments, writes", [(["--set-webhook-url"], True), (["--set-lastfm-credentials"], True), (["--send-test-webhook"], False), (["--generate-config"], False), ([], False)])
    def test_only_the_secret_commands_count_as_writing_the_dotenv(self, arguments, writes):
        assert monitor.command_writes_dotenv(arguments) is writes


class TestNoCommandBypassesTheRenderer:
    # A hand-built command reads correctly and is simply missing the flags, which is how the bypass hides
    def test_no_printed_command_spells_the_tool_name_by_hand(self):
        offenders = sorted({literal for literal in printed_string_literals() if HARDCODED_COMMAND.search(literal)})
        assert offenders == [], f"printed commands that bypass render_command: {offenders}"

    def test_the_guard_would_notice_a_hand_built_command(self):
        assert HARDCODED_COMMAND.search("verify with 'lastfm_monitor --send-test-webhook'")
        assert HARDCODED_COMMAND.search("run python3 lastfm_monitor.py --doctor")
        assert not HARDCODED_COMMAND.search("https://github.com/misiektoja/lastfm_monitor")


# Verifies the printed-command renderer takes the family's two shared parameters before any tool-specific one
def test_the_command_renderer_shares_one_contract():
    parameters = list(inspect.signature(monitor.render_command).parameters.values())
    assert [parameter.name for parameter in parameters[:2]] == ["arguments", "include_paths"]
    assert [parameter.default for parameter in parameters[:2]] == [None, True]
    # A tool-specific extra is keyword-only, so a positional call copied from a sibling cannot bind to it
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters[2:])


# Verifies the renderer with no arguments prints the bare command, which is what the help screen puts before each example
def test_the_renderer_with_no_arguments_prints_the_bare_command():
    prefix = monitor.render_command(include_paths=False)
    assert prefix and not prefix.endswith(" ")
    assert monitor.render_command(["--doctor"], include_paths=False) == f"{prefix} --doctor"
