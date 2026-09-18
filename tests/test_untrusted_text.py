"""Text that comes from Last.fm: what the terminal, the log and an email body are allowed to receive."""

import ast
import sys
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TREE = ast.parse((PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8"))

API_KEY = "lastfmapikey00000000000000000000"
API_SECRET = "lastfmapisecret00000000000000000"
# A scrobble title is attacker-controlled text that reaches a terminal, so it is treated as hostile input.
# It carries an SGR sequence too, which the writers keep because this tool's own colours travel the same path
HOSTILE_TRACK = "\x1b[2J\x1b]0;pwned\x1b[31mTrack\x08\x00"


# Asserts nothing that moves the cursor, clears the screen or sets the title survived, allowing only inert SGR
def assert_no_terminal_controls(output):
    assert "\r" not in output and "\x07" not in output and "\x9b" not in output
    assert monitor.SGR_SEQUENCE_RE.sub("", output).count("\x1b") == 0


@pytest.fixture
def restored_globals():
    saved = {name: value for name, value in vars(monitor).items() if name.isupper()}
    yield
    for name, value in saved.items():
        setattr(monitor, name, value)


class TestTheSanitizerItself:
    def test_an_escape_sequence_is_removed(self):
        assert monitor.sanitize_terminal_text("before\x1b[2Jafter") == "beforeafter"

    # This tool's own colours re-enter the same writer, so a colour change is the one sequence that is kept.
    # A bare SGR sequence in upstream text survives with it, visible but unable to drive the terminal
    def test_a_colour_change_survives_because_the_tool_emits_them(self):
        assert monitor.sanitize_terminal_text("before\x1b[31mafter") == "before\x1b[31mafter"

    def test_a_cursor_move_next_to_a_colour_change_is_still_removed(self):
        assert monitor.sanitize_terminal_text("\x1b[31mred\x1b[2Jcleared") == "\x1b[31mredcleared"

    def test_a_window_title_sequence_cannot_survive(self):
        assert monitor.sanitize_terminal_text("\x1b]0;pwned\x07name") == "name"

    def test_control_characters_are_removed(self):
        assert monitor.sanitize_terminal_text("a\x00b\x08c\x7fd") == "abcd"

    # The tool builds its own blocks out of tabs and newlines, so stripping them would wreck every report
    def test_tabs_and_newlines_survive(self):
        assert monitor.sanitize_terminal_text("Timestamp:\t\tvalue\n") == "Timestamp:\t\tvalue\n"

    def test_a_carriage_return_cannot_redraw_a_line(self):
        assert monitor.sanitize_terminal_text("real line\rfake line") == "real linefake line"

    def test_a_value_that_is_not_text_is_returned_as_it_is(self):
        assert monitor.sanitize_terminal_text(None) is None


class TestEveryWriterSanitizes:
    def test_the_log_writer_cleans_both_destinations(self, tmp_path, capsys):
        stream = monitor.Logger(str(tmp_path / "run.log"))
        stream.write(f"* Last track:\t\t\t{HOSTILE_TRACK}\n")
        printed = capsys.readouterr().out
        logged = (tmp_path / "run.log").read_text(encoding="utf-8")
        assert_no_terminal_controls(printed)
        # The log file is plain text, so even the colour codes the terminal is allowed to keep are stripped
        assert "\x1b" not in logged
        assert "Track" in printed and "Track" in logged

    def test_each_single_channel_cleans_what_it_writes(self, tmp_path, capsys):
        stream = monitor.Logger(str(tmp_path / "run.log"))
        stream.terminal_only(f"{HOSTILE_TRACK}\n")
        stream.log_only(f"{HOSTILE_TRACK}\n")
        assert_no_terminal_controls(capsys.readouterr().out)
        assert "\x1b" not in (tmp_path / "run.log").read_text(encoding="utf-8")

    # With logging switched off nothing used to wrap stdout, so nothing sanitized what a run printed
    def test_a_run_without_a_log_file_still_sanitizes(self, capsys):
        stream = monitor.TerminalStream(sys.stdout)
        stream.write(f"{HOSTILE_TRACK}\n")
        printed = capsys.readouterr().out
        assert_no_terminal_controls(printed)
        assert "Track" in printed

    def test_the_terminal_stream_has_nowhere_to_log(self, capsys):
        stream = monitor.TerminalStream(sys.stdout)
        stream.log_only("only the log would take this\n")
        assert capsys.readouterr().out == ""

    @pytest.mark.parametrize("logging_setting, expected", [("DISABLE_LOGGING = True\n", "TerminalStream"), ("DISABLE_LOGGING = False\nLF_LOGFILE = \"run\"\n", "Logger")])
    def test_a_real_run_installs_a_sanitizing_stream_either_way(self, restored_globals, tmp_path, capsys, logging_setting, expected):
        config_path = tmp_path / "lastfm.conf"
        config_path.write_text(f'LASTFM_API_KEY = "{API_KEY}"\nLASTFM_API_SECRET = "{API_SECRET}"\n{logging_setting}', encoding="utf-8")
        installed = {}
        saved_stdout = sys.stdout

        def stop_at_the_loop(*args, **kwargs):
            installed["stream"] = type(sys.stdout).__name__
            raise SystemExit(0)

        try:
            with pytest.MonkeyPatch.context() as patch:
                patch.chdir(tmp_path)
                patch.setattr(monitor, "lastfm_monitor_user", stop_at_the_loop)
                patch.setattr(monitor, "check_internet", lambda *a, **k: True)
                patch.setattr(monitor.sys, "argv", ["lastfm_monitor", "someuser", "--config-file", str(config_path), "--env-file", "none"])
                with pytest.raises(SystemExit):
                    monitor.main()
        finally:
            sys.stdout = saved_stdout
        capsys.readouterr()
        assert installed["stream"] == expected


class TestSecretsInOrdinaryOutput:
    # Every line of output now passes the redactor, where a short secret is also an ordinary word
    def test_a_short_password_that_is_a_word_leaves_the_feed_alone(self, restored_globals, tmp_path, capsys):
        monitor.SMTP_PASSWORD = "monitor"
        stream = monitor.Logger(str(tmp_path / "run.log"))
        stream.write("* Last track:\t\t\tmonitor - monitoring\n")
        assert "<redacted>" not in capsys.readouterr().out

    def test_a_real_secret_is_still_replaced_everywhere(self, restored_globals, tmp_path, capsys):
        monitor.SMTP_PASSWORD = "chosen-smtp-password-value"
        stream = monitor.Logger(str(tmp_path / "run.log"))
        stream.write("* Error: the server rejected chosen-smtp-password-value\n")
        printed = capsys.readouterr().out
        assert "chosen-smtp-password-value" not in printed
        assert "<redacted>" in printed
        assert "chosen-smtp-password-value" not in (tmp_path / "run.log").read_text(encoding="utf-8")


class TestUpstreamTextInAnEmailBody:
    # A scrobble title reaches the HTML body of every listening alert, so the shared renderers escape it
    def test_the_shared_url_renderers_escape_the_track_and_artist(self):
        rendered = monitor.format_music_urls_email_html("https://open.spotify.com/x", "https://www.last.fm/x", "", "", "", "", "", "", "<b>Artist</b>", "<script>Track</script>", "https://open.spotify.com/x", "Spotify URL")
        rendered += monitor.format_lyrics_urls_email_html("https://genius.com/x", "", "", "", "", "<b>Artist</b>", "<script>Track</script>")
        assert "<b>Artist</b>" not in rendered
        assert "<script>" not in rendered
        assert "&lt;b&gt;Artist&lt;/b&gt;" in rendered

    # The alert bodies are built inline in the loop, so the guarantee is checked over the source rather than per branch
    def test_no_html_body_interpolates_an_upstream_name_unescaped(self):
        upstream = {"artist", "track", "album", "artist_old", "track_old", "album_old", "display_name", "bio", "previous_value", "current_value", "user", "username_changed"}
        unescaped = []
        for node in ast.walk(TREE):
            if not isinstance(node, ast.JoinedStr):
                continue
            literal = "".join(part.value for part in node.values if isinstance(part, ast.Constant) and isinstance(part.value, str))
            if not any(tag in literal for tag in ("<br>", "<b>", "<a href", "<html>")):
                continue
            for part in node.values:
                if isinstance(part, ast.FormattedValue) and isinstance(part.value, ast.Name) and part.value.id in upstream:
                    unescaped.append((node.lineno, part.value.id))
        assert unescaped == []
