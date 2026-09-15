"""How the tool writes files: the timestamped config backup, the atomic replace, the secrets the generated config drops and the dotenv file that is deliberately not backed up."""

import stat
import re
import ast
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")


# Returns a backup path as a Path, failing the test when nothing was copied
def backup_of(value):
    assert value is not None, "no backup was taken"
    return Path(value)


# Returns a stand-in for the module clock, so two backups can be forced into the same second
class FrozenDatetime:
    @staticmethod
    def now():
        return datetime(2026, 9, 8, 11, 34, 53)


# Answers one prompt and records that it was asked
class Answer:
    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def __call__(self, prompt=""):
        self.prompts.append(prompt)
        return self.reply


class TestTheTimestampedBackup:

    def test_an_existing_file_is_copied_before_it_is_replaced(self, tmp_path):
        config = tmp_path / "lastfm_monitor.conf"
        config.write_text("LASTFM_CHECK_INTERVAL = 42\n", encoding="utf-8")

        backup = monitor.create_timestamped_backup(config)

        assert backup_of(backup).read_text(encoding="utf-8") == "LASTFM_CHECK_INTERVAL = 42\n"
        assert backup_of(backup).name.endswith(".bak")

    def test_the_backup_is_readable_only_by_its_owner(self, tmp_path):
        config = tmp_path / "lastfm_monitor.conf"
        config.write_text("LASTFM_CHECK_INTERVAL = 42\n", encoding="utf-8")
        config.chmod(0o644)

        backup = monitor.create_timestamped_backup(config)

        assert oct(backup_of(backup).stat().st_mode & 0o777) == "0o600"

    def test_nothing_is_copied_when_the_file_does_not_exist(self, tmp_path):
        assert monitor.create_timestamped_backup(tmp_path / "absent.conf") is None

    # Two saves in the same second used to collide, which would have replaced the copy the first one took
    def test_a_second_backup_in_the_same_second_gets_its_own_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "datetime", FrozenDatetime)
        config = tmp_path / "lastfm_monitor.conf"
        config.write_text("first\n", encoding="utf-8")
        first = monitor.create_timestamped_backup(config)
        config.write_text("second\n", encoding="utf-8")

        second = monitor.create_timestamped_backup(config)

        assert first != second
        assert backup_of(first).read_text(encoding="utf-8") == "first\n"
        assert backup_of(second).read_text(encoding="utf-8") == "second\n"

    def test_a_backup_that_cannot_get_a_unique_name_fails_loudly(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor, "datetime", FrozenDatetime)
        config = tmp_path / "lastfm_monitor.conf"
        config.write_text("kept\n", encoding="utf-8")

        with pytest.raises(OSError):
            monitor.create_timestamped_backup(config, attempts=0)


class TestTheAtomicWrite:

    def test_the_replacement_is_all_or_nothing(self, tmp_path, monkeypatch):
        destination = tmp_path / "state.json"
        destination.write_text("original\n", encoding="utf-8")

        def failing_replace(source, target):
            raise OSError("disk full")

        monkeypatch.setattr(monitor.os, "replace", failing_replace)
        with pytest.raises(OSError):
            monitor.write_file_atomically(destination, "replacement\n")

        assert destination.read_text(encoding="utf-8") == "original\n"
        assert sorted(path.name for path in tmp_path.iterdir()) == ["state.json"]

    def test_a_requested_mode_is_applied_before_the_file_appears(self, tmp_path):
        destination = tmp_path / "secrets.env"

        monitor.write_file_atomically(destination, "WEBHOOK_URL=https://example.invalid/hook\n", mode=0o600)

        assert oct(destination.stat().st_mode & 0o777) == "0o600"

    def test_a_missing_parent_directory_is_created(self, tmp_path):
        destination = tmp_path / "nested" / "deeper" / "state.json"

        monitor.write_file_atomically(destination, "{}\n")

        assert destination.read_text(encoding="utf-8") == "{}\n"

    # A helper that exists and is not called is a helper that does not exist, so no writer may open a path itself
    def test_no_writer_opens_a_destination_for_writing(self):
        opens = []
        for node in ast.walk(ast.parse(SOURCE)):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "open":
                continue
            mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else ""
            mode = mode or next((keyword.value.value for keyword in node.keywords if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant)), "")
            if any(character in str(mode) for character in ("w", "x", "+")):
                opens.append(node.lineno)

        assert opens == [], f"these lines write without the shared writer: {opens}"


class TestReplacingAGeneratedConfig:

    def test_a_new_file_is_written_without_asking(self, tmp_path):
        destination = tmp_path / "lastfm_monitor.conf"
        answer = Answer("n")

        backup, written = monitor.write_generated_config(destination, "LASTFM_CHECK_INTERVAL = 42\n", interactive=True, input_func=answer)

        assert (backup, written) == (None, True)
        assert answer.prompts == []
        assert destination.read_text(encoding="utf-8") == "LASTFM_CHECK_INTERVAL = 42\n"

    def test_replacing_outside_a_terminal_needs_force(self, tmp_path):
        destination = tmp_path / "lastfm_monitor.conf"
        destination.write_text("kept\n", encoding="utf-8")

        with pytest.raises(FileExistsError):
            monitor.write_generated_config(destination, "template\n", interactive=False)

        assert destination.read_text(encoding="utf-8") == "kept\n"

    def test_force_replaces_it_and_still_takes_a_backup(self, tmp_path):
        destination = tmp_path / "lastfm_monitor.conf"
        destination.write_text("kept\n", encoding="utf-8")

        backup, written = monitor.write_generated_config(destination, "template\n", force=True, interactive=False)

        assert written is True
        assert destination.read_text(encoding="utf-8") == "template\n"
        assert backup_of(backup).read_text(encoding="utf-8") == "kept\n"

    @pytest.mark.parametrize("reply, replaced", [("y", True), ("yes", True), ("Y", True), ("n", False), ("", False), ("later", False)])
    def test_the_prompt_defaults_to_keeping_the_file(self, tmp_path, reply, replaced):
        destination = tmp_path / "lastfm_monitor.conf"
        destination.write_text("kept\n", encoding="utf-8")

        _backup, written = monitor.write_generated_config(destination, "template\n", interactive=True, input_func=Answer(reply))

        assert written is replaced
        assert (destination.read_text(encoding="utf-8") == "template\n") is replaced

    def test_an_interrupted_prompt_keeps_the_file(self, tmp_path):
        destination = tmp_path / "lastfm_monitor.conf"
        destination.write_text("kept\n", encoding="utf-8")

        def interrupt(prompt=""):
            raise KeyboardInterrupt

        _backup, written = monitor.write_generated_config(destination, "template\n", interactive=True, input_func=interrupt)

        assert written is False
        assert destination.read_text(encoding="utf-8") == "kept\n"

    def test_a_declined_replacement_takes_no_backup(self, tmp_path):
        destination = tmp_path / "lastfm_monitor.conf"
        destination.write_text("kept\n", encoding="utf-8")

        monitor.write_generated_config(destination, "template\n", interactive=True, input_func=Answer("n"))

        assert [path.name for path in tmp_path.iterdir()] == ["lastfm_monitor.conf"]


class TestTheGenerateConfigCommand:

    def run(self, tmp_path, *arguments):
        return subprocess.run([sys.executable, str(PROJECT_ROOT / "lastfm_monitor.py"), *arguments], capture_output=True, text=True, cwd=tmp_path)

    def test_the_template_is_written_and_loads_back(self, tmp_path):
        result = self.run(tmp_path, "--generate-config", "lastfm_monitor.conf")

        assert result.returncode == 0
        assert "Config written to: lastfm_monitor.conf" in result.stdout
        assert monitor.load_config_file(str(tmp_path / "lastfm_monitor.conf"), namespace={}, report_errors=False) is True

    def test_an_existing_file_is_never_replaced_silently(self, tmp_path):
        destination = tmp_path / "lastfm_monitor.conf"
        destination.write_text("LASTFM_CHECK_INTERVAL = 42\n", encoding="utf-8")

        result = self.run(tmp_path, "--generate-config", "lastfm_monitor.conf")

        assert result.returncode == 1
        assert "--force" in result.stdout
        assert destination.read_text(encoding="utf-8") == "LASTFM_CHECK_INTERVAL = 42\n"

    def test_force_reports_where_the_previous_config_went(self, tmp_path):
        destination = tmp_path / "lastfm_monitor.conf"
        destination.write_text("LASTFM_CHECK_INTERVAL = 42\n", encoding="utf-8")

        result = self.run(tmp_path, "--generate-config", "lastfm_monitor.conf", "--force")

        assert result.returncode == 0
        backup = next(path for path in tmp_path.iterdir() if path.name.endswith(".bak"))
        assert f"Previous config backed up to: {backup.name}" in result.stdout
        assert backup.read_text(encoding="utf-8") == "LASTFM_CHECK_INTERVAL = 42\n"

    def test_the_template_still_goes_to_stdout_without_a_filename(self, tmp_path):
        result = self.run(tmp_path, "--generate-config")

        assert result.returncode == 0
        assert "LASTFM_CHECK_INTERVAL" in result.stdout
        assert list(tmp_path.iterdir()) == []

    # The advice used to name the discovered config, so following it replaced the file the error was about
    def test_a_rejected_config_is_not_told_to_regenerate_over_itself(self, tmp_path):
        broken = tmp_path / "lastfm_monitor.conf"
        broken.write_text("LASTFM_CHECK_INTERVAL = 60 * 2\n", encoding="utf-8")

        result = self.run(tmp_path, "--config-file", "lastfm_monitor.conf", "someuser")

        assert "--generate-config <new-file>" in result.stdout
        assert "--generate-config lastfm_monitor.conf" not in result.stdout


class TestTheDotenvFile:

    def test_a_rotated_secret_leaves_no_copy_behind(self, tmp_path):
        destination = tmp_path / "secrets.env"
        destination.write_text("WEBHOOK_URL=https://example.invalid/old\n", encoding="utf-8")

        monitor.update_dotenv_file(destination, {"WEBHOOK_URL": "https://example.invalid/new"})

        assert [path.name for path in tmp_path.iterdir()] == ["secrets.env"]
        assert "old" not in destination.read_text(encoding="utf-8")

    def test_the_file_stays_readable_only_by_its_owner(self, tmp_path):
        destination = tmp_path / "secrets.env"

        monitor.update_dotenv_file(destination, {"SMTP_PASSWORD": "s3cret"})

        assert oct(destination.stat().st_mode & 0o777) == "0o600"

    def test_the_write_goes_through_the_shared_atomic_writer(self, tmp_path, monkeypatch):
        calls = []
        monkeypatch.setattr(monitor, "write_file_atomically", lambda destination, content, mode=None: calls.append((str(destination), mode)) or str(destination))

        monitor.update_dotenv_file(tmp_path / "secrets.env", {"SMTP_PASSWORD": "s3cret"})

        assert calls == [(str(tmp_path / "secrets.env"), 0o600)]


class TestTheStateFiles:

    def test_a_crash_cannot_strand_a_half_written_state_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monitor.save_friends_state("someuser", "followers", {"alice"})
        original = (tmp_path / "lastfm_someuser_followers.json").read_text(encoding="utf-8")

        def failing_replace(source, target):
            raise OSError("disk full")

        monkeypatch.setattr(monitor.os, "replace", failing_replace)
        monitor.save_friends_state("someuser", "followers", {"alice", "bob"})

        assert (tmp_path / "lastfm_someuser_followers.json").read_text(encoding="utf-8") == original
        assert sorted(path.name for path in tmp_path.iterdir()) == ["lastfm_someuser_followers.json"]

    def test_the_profile_state_keeps_its_original_characters(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        monitor.save_profile_state("someuser", {"display_name": "Sasza", "bio": "zażółć"})

        assert "zażółć" in (tmp_path / "lastfm_someuser_profile.json").read_text(encoding="utf-8")
        assert monitor.load_profile_state("someuser")["bio"] == "zażółć"

    # Every file a run writes is named after the username the user typed, so no name waits on a network call
    @pytest.mark.parametrize("builder, expected", [
        (lambda: monitor.build_log_path("lastfm_monitor", "someuser"), "lastfm_monitor_someuser.log"),
        (lambda: monitor.Path(f"lastfm_{'someuser'}_last_activity.json"), "lastfm_someuser_last_activity.json"),
    ])
    def test_generated_names_come_from_the_target(self, builder, expected):
        assert Path(builder()).name == expected


# The config file is world readable and is copied to a backup, so no secret may be rendered into it
class TestTheGeneratedConfigDropsEverySecret:

    def test_no_secret_reaches_the_file_whatever_the_caller_passes(self):
        secrets = {key: f"live-{key.casefold()}-value" for key in monitor.SECRET_KEYS}

        written = monitor.generate_config_with_current_values({**secrets, "LASTFM_CHECK_INTERVAL": 42})

        for key, value in secrets.items():
            assert value not in written, f"{key} was written into the configuration"
        assert "LASTFM_CHECK_INTERVAL = 42" in written

    def test_the_shipped_placeholder_survives_a_caller_that_holds_the_real_value(self):
        template = monitor._config_template_defaults()

        written = monitor.generate_config_with_current_values({key: "live-value" for key in monitor.SECRET_KEYS})

        for key in monitor.SECRET_KEYS:
            assert f"{key} = {template[key]!r}".replace("'", '"') in written.replace("'", '"')
            # A kept placeholder only means unset if the tool reads it that way
            assert monitor.doctor_value_is_set(template[key]) is False


# Verifies the backup name every tool in this family writes, so one documented shape covers them all
def test_the_backup_carries_the_family_name_and_mode(tmp_path):
    destination = tmp_path / "monitor.conf"
    destination.write_text("SETTING = 1\n", encoding="utf-8")

    backup_path = monitor.create_timestamped_backup(destination)

    assert re.fullmatch(r"monitor\.conf\.\d{14}\.bak", Path(backup_path).name)
    assert Path(backup_path).read_text(encoding="utf-8") == "SETTING = 1\n"
    assert stat.S_IMODE(Path(backup_path).stat().st_mode) == 0o600


# Verifies a second backup in the same second takes its own name rather than overwriting the first
def test_a_second_backup_in_the_same_second_keeps_the_first(tmp_path):
    destination = tmp_path / "monitor.conf"
    destination.write_text("first\n", encoding="utf-8")
    first = monitor.create_timestamped_backup(destination)
    destination.write_text("second\n", encoding="utf-8")

    second = monitor.create_timestamped_backup(destination)

    assert first != second
    assert Path(first).read_text(encoding="utf-8") == "first\n"
    assert Path(second).read_text(encoding="utf-8") == "second\n"


# Verifies a destination that is not there yet earns no backup, since there is nothing to copy
def test_a_missing_destination_earns_no_backup(tmp_path):
    assert monitor.create_timestamped_backup(tmp_path / "absent.conf") is None


# A parent path that is a file is a write failure, not an existing config, so the advice must not say --force
def test_a_file_in_the_way_of_the_parent_directory_is_not_an_existing_config(tmp_path):
    blocker = tmp_path / "configs"
    blocker.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(OSError) as raised:
        monitor.write_generated_config(blocker / "lastfm_monitor.conf", "SMTP_PORT = 587\n", interactive=False)

    assert not isinstance(raised.value, monitor.ConfigExistsError)
    assert blocker.read_text(encoding="utf-8") == "not a directory\n"


# Refusing to replace a config without a terminal is its own error, so the generate-config path can tell it apart
def test_refusing_to_replace_a_config_without_a_terminal_raises_its_own_error(tmp_path):
    destination = tmp_path / "lastfm_monitor.conf"
    destination.write_text("SMTP_PORT = 587\n", encoding="utf-8")

    with pytest.raises(monitor.ConfigExistsError):
        monitor.write_generated_config(destination, "SMTP_PORT = 465\n", interactive=False)

    assert destination.read_text(encoding="utf-8") == "SMTP_PORT = 587\n"


# Verifies an explicit colour theme survives a config rebuild, since the template ships the setting commented out
def test_a_rebuilt_config_keeps_an_explicit_color_theme():
    values = dict(monitor._config_template_defaults())
    values["COLOR_THEME"] = {"header": "bright_red"}

    rendered = monitor.generate_config_with_current_values(values)

    assert monitor.parse_config_content(rendered, "<generated>")["COLOR_THEME"] == {"header": "bright_red"}


# Verifies the shipped default stays commented out, so a rebuild does not pin a theme the user never chose
def test_a_rebuilt_config_leaves_the_default_theme_commented():
    rendered = monitor.generate_config_with_current_values(dict(monitor._config_template_defaults()))

    assert "\nCOLOR_THEME = {" not in rendered
