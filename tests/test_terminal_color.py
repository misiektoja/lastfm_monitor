"""Coloured output: which colour lands on which token, and the boundaries colour is not allowed to cross."""

import argparse
from io import StringIO
import ast
import io
import re
import sys
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

API_KEY = "lastfmapikey00000000000000000000"
API_SECRET = "lastfmapisecret00000000000000000"


@pytest.fixture
def colored():
    """Turns colour on with the shipped theme and hands back the escape sequence of every part."""
    saved_enabled, saved_styles, saved_setting = monitor.COLOR_ENABLED, monitor._COLOR_STYLES, monitor.COLORED_OUTPUT
    monitor.COLORED_OUTPUT = True
    monitor.COLOR_ENABLED = True
    monitor._COLOR_STYLES = {name: monitor._build_ansi_sequence(style) for name, style in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(style)}
    yield dict(monitor._COLOR_STYLES)
    monitor.COLOR_ENABLED, monitor._COLOR_STYLES, monitor.COLORED_OUTPUT = saved_enabled, saved_styles, saved_setting


@pytest.fixture
def restored_globals():
    saved = {name: value for name, value in vars(monitor).items() if name.isupper()}
    yield
    for name, value in saved.items():
        setattr(monitor, name, value)


# Uncomments the COLOR_THEME block the configuration template ships, which exists to be read and edited
def template_theme():
    lines = monitor.CONFIG_BLOCK.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith("# COLOR_THEME = {"))
    end = next(index for index in range(start, len(lines)) if lines[index].rstrip() == "# }")
    namespace = {}
    exec("\n".join(line[2:] if line.startswith("# ") else line[1:] for line in lines[start:end + 1]), namespace)
    return namespace["COLOR_THEME"]


class TestTheThemeItself:
    def test_the_template_block_matches_the_built_in_theme(self):
        assert template_theme() == monitor.DEFAULT_COLOR_THEME

    def test_every_style_word_the_theme_ships_resolves(self):
        for name, value in monitor.DEFAULT_COLOR_THEME.items():
            assert monitor._build_ansi_sequence(value) or value == "", name

    # A key nothing reads is a documented setting that does nothing
    def test_no_theme_key_is_unused(self):
        assert sorted(set(monitor.DEFAULT_COLOR_THEME) - theme_keys_referenced()) == []

    # The reverse hole: a colorize call naming a key the theme lacks renders plain and nothing complains
    def test_no_colour_is_asked_for_by_a_name_the_theme_lacks(self):
        assert sorted(theme_keys_referenced() - set(monitor.DEFAULT_COLOR_THEME)) == []

    # A value drawn in the colour of the block enclosing it disappears
    def test_a_block_style_never_hides_a_name(self, colored):
        for block in monitor.BLOCK_STYLE_PARTS:
            for name in monitor.NAME_STYLE_PARTS:
                assert colored[name] != colored[block], f"{name} is invisible inside a {block} line"

    # The three shared identity parts are named and coloured the way every sibling names and colours them
    def test_the_shared_identity_parts_match_the_family(self):
        assert monitor.DEFAULT_COLOR_THEME["username"] == "bright_cyan underline"
        assert monitor.DEFAULT_COLOR_THEME["id"] == "bright_magenta"
        assert monitor.DEFAULT_COLOR_THEME["link"] == "blue underline"

    def test_the_timestamp_label_is_left_plain(self, colored):
        assert monitor.DEFAULT_COLOR_THEME["timestamp_label"] == ""
        assert "timestamp_label" not in colored


# Collects every theme key the module asks for, through colorize, a block style or one of the lookup tables
def theme_keys_referenced():
    referenced = set()
    for node in ast.walk(TREE):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("colorize", "_apply_style_nested"):
            argument = node.args[0] if node.func.id == "colorize" else node.args[1]
            for candidate in (argument.body, argument.orelse) if isinstance(argument, ast.IfExp) else (argument,):
                if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str):
                    referenced.add(candidate.value)
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in ("DOCTOR_MARK_STYLES", "WIZARD_SUMMARY_VALUE_STYLES"):
            referenced |= set(ast.literal_eval(node.value).values())
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "_LABEL_STYLES":
            referenced |= {style for _, style in ast.literal_eval(node.value)}
    return referenced


class TestBuildingAStyle:
    def test_two_attributes_combine_into_one_sequence(self):
        assert monitor._build_ansi_sequence("bright_cyan underline") == "\033[96;4m"

    def test_a_plus_separates_attributes_too(self):
        assert monitor._build_ansi_sequence("red+bold") == "\033[31;1m"

    def test_an_empty_style_produces_nothing(self):
        assert monitor._build_ansi_sequence("") == ""

    def test_an_unknown_word_produces_nothing(self):
        assert monitor._build_ansi_sequence("chartreuse") == ""


class TestWhenColourIsSwitchedOff:
    def test_colorize_returns_the_text_untouched(self):
        assert monitor.colorize("username", "someuser") == "someuser"

    def test_a_part_the_theme_lacks_renders_plain(self, colored):
        assert monitor.colorize("nothing_like_this", "value") == "value"

    @pytest.mark.parametrize("environment", [{"NO_COLOR": "1"}, {"TERM": "dumb"}, {"TERM": ""}])
    def test_the_environment_can_refuse_colour(self, monkeypatch, environment):
        monkeypatch.setattr(monitor.sys, "stdin", io.StringIO())
        monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True, raising=False)
        for key, value in environment.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("TERM", environment.get("TERM", "xterm-256color"))
        assert monitor._stream_supports_color(FakeTerminal(True)) is False

    def test_a_redirected_stream_gets_no_colour(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        assert monitor._stream_supports_color(FakeTerminal(False)) is False

    # Piped stdin usually means the run is being captured, and colour codes would land in the capture
    def test_a_piped_stdin_gets_no_colour(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        monkeypatch.setattr(monitor.sys, "stdin", FakeTerminal(False))
        assert monitor._stream_supports_color(FakeTerminal(True)) is False

    def test_the_setting_alone_can_switch_colour_off(self, restored_globals, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        monkeypatch.setattr(monitor.sys, "stdin", FakeTerminal(True))
        monitor.COLORED_OUTPUT = False
        monitor.init_color_output(FakeTerminal(True))
        assert monitor.COLOR_ENABLED is False and monitor._COLOR_STYLES == {}


class FakeTerminal:
    def __init__(self, interactive):
        self.interactive = interactive

    def isatty(self):
        return self.interactive

    def write(self, message):
        return len(message)

    def flush(self):
        return None


class TestTheConfiguredTheme:
    def test_a_configured_part_overrides_the_default(self, restored_globals, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        monkeypatch.setattr(monitor.sys, "stdin", FakeTerminal(True))
        monitor.COLORED_OUTPUT = True
        monitor.COLOR_THEME = {"username": "green"}
        monitor.init_color_output(FakeTerminal(True))
        assert monitor._COLOR_STYLES["username"] == "\033[32m"
        assert monitor._COLOR_STYLES["track"] == monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["track"])

    # The template is also the settings allowlist, so a setting shipped commented out has to stay loadable
    def test_a_config_setting_only_the_commented_theme_still_loads(self, tmp_path):
        config = tmp_path / "lastfm.conf"
        config.write_text('COLOR_THEME = { "username": "green" }\n', encoding="utf-8")
        assert monitor.parse_config_content(config.read_text(encoding="utf-8"), str(config)) == {"COLOR_THEME": {"username": "green"}}

    def test_the_commented_setting_is_in_the_allowlist(self):
        assert "COLOR_THEME" in monitor._config_allowed_names()


class TestTheIdentityRows:
    # The target row and the sentence under it name the same thing, so they have to agree
    def test_the_target_row_and_the_monitoring_line_agree(self, colored):
        row = monitor._colorize_line("* Target:                       someuser")
        sentence = monitor._colorize_line("Monitoring user someuser")
        assert row == f"* Target:                       {colored['username']}someuser{monitor.ANSI_RESET}"
        assert sentence == f"Monitoring user {colored['username']}someuser{monitor.ANSI_RESET}"

    def test_the_labelled_user_row_is_a_username(self, colored):
        assert monitor._colorize_line("Last.fm user:\t\t\tsomeuser") == f"Last.fm user:\t\t\t{colored['username']}someuser{monitor.ANSI_RESET}"

    @pytest.mark.parametrize("line", ["* Followings number changed by user someuser from 12 to 14 (+2)", "* Public profile changed for user someuser", "* Listing 10 tracks recently listened by someuser ..."])
    def test_a_named_account_inside_a_sentence_is_a_username(self, colored, line):
        assert f"{colored['username']}someuser{monitor.ANSI_RESET}" in monitor._colorize_line(line)

    def test_a_diagnostic_user_field_is_a_username(self, colored):
        rendered = monitor._colorize_line("[DEBUG 15:08:45] Monitoring loop start: user=someuser, interval=30s")
        assert f"user={colored['username']}someuser{monitor.ANSI_RESET}," in rendered

    # A machine identifier is not an account name, so it takes the family's id colour instead
    def test_a_diagnostic_id_field_is_an_identifier(self, colored):
        rendered = monitor._colorize_line("[DEBUG 15:08:45] Spotify metadata match: track_id=4uLU6hMCjMI75M1A2tKUQC, outcome=OK")
        assert f"track_id={colored['id']}4uLU6hMCjMI75M1A2tKUQC{monitor.ANSI_RESET}," in rendered

    def test_a_listing_row_names_the_account_and_links_the_profile(self, colored):
        rendered = monitor._colorize_line("- someuser [ https://www.last.fm/user/someuser ]")
        assert rendered == f"- {colored['username']}someuser{monitor.ANSI_RESET} [ {colored['link']}https://www.last.fm/user/someuser{monitor.ANSI_RESET} ]"


class TestTheMusicRows:
    def test_the_track_row_carries_the_track_colour(self, colored):
        assert monitor._colorize_line("Track:\t\t\t\tPink Floyd - Time") == f"Track:\t\t\t\t{colored['track']}Pink Floyd - Time{monitor.ANSI_RESET}"

    def test_the_album_row_carries_the_album_colour(self, colored):
        assert monitor._colorize_line("Album:\t\t\t\tThe Dark Side of the Moon") == f"Album:\t\t\t\t{colored['album']}The Dark Side of the Moon{monitor.ANSI_RESET}"

    # The longer label wins, so a duration row is not read as a track row
    def test_the_track_duration_row_is_a_duration(self, colored):
        assert monitor._colorize_line("* Last track duration:\t\t3 minutes 21 seconds") == f"* Last track duration:\t\t{colored['duration']}3 minutes 21 seconds{monitor.ANSI_RESET}"

    def test_a_music_link_row_is_a_link_and_not_an_album(self, colored):
        rendered = monitor._colorize_line("Last.fm album URL:\t\thttps://www.last.fm/music/Pink+Floyd/The+Dark+Side")
        assert rendered == f"Last.fm album URL:\t\t{colored['link']}https://www.last.fm/music/Pink+Floyd/The+Dark+Side{monitor.ANSI_RESET}"

    def test_the_listing_table_colours_its_columns(self, colored):
        assert monitor.colorize("artist", "Pink Floyd  ") == f"{colored['artist']}Pink Floyd  {monitor.ANSI_RESET}"

    # Each cell is padded before it is coloured, so a colour code never counts toward a column width
    def test_the_listing_table_pads_before_it_colours(self):
        listing = next(node for node in ast.walk(TREE) if isinstance(node, ast.FunctionDef) and node.name == "lastfm_list_tracks")
        colorized_ljust = [ast.unparse(node) for node in ast.walk(listing) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "colorize"]
        assert colorized_ljust, "the listing table no longer colours its cells"
        assert all(".ljust(" in call for call in colorized_ljust), "a cell is coloured before it is padded"


class TestTheActivityWords:
    @pytest.mark.parametrize("word, part", [("ACTIVE", "status_active"), ("PRIVATE MODE", "status_active"), ("LOOP", "status_active"), ("RESUMED", "status_active"), ("INACTIVE", "status_inactive"), ("SKIPPED", "status_inactive"), ("PAUSED", "status_inactive"), ("OFFLINE", "status_offline"), ("CONT", "status_change")])
    def test_each_listening_state_takes_its_own_colour(self, colored, word, part):
        assert f"{colored[part]}{word}{monitor.ANSI_RESET}" in monitor._colorize_line(f"*** User is {word} now")

    # ACTIVE sits inside INACTIVE, so the word boundary is what keeps the two apart
    def test_inactive_is_not_read_as_active(self, colored):
        assert monitor._colorize_line("*** User got INACTIVE") == f"*** User got {colored['status_inactive']}INACTIVE{monitor.ANSI_RESET}"


class TestTheNumbersAndDates:
    def test_a_rising_count_is_green_at_both_ends(self, colored):
        rendered = monitor._colorize_line("* Followers number changed for user someuser from 30 to 34 (+4)")
        assert f"from {colored['count_up']}30{monitor.ANSI_RESET} to {colored['count_up']}34{monitor.ANSI_RESET}" in rendered
        assert f"{colored['count_up']}(+4){monitor.ANSI_RESET}" in rendered

    def test_a_falling_count_is_red_at_both_ends(self, colored):
        rendered = monitor._colorize_line("* Followers number changed for user someuser from 30 to 28 (-2)")
        assert f"from {colored['count_down']}30{monitor.ANSI_RESET} to {colored['count_down']}28{monitor.ANSI_RESET}" in rendered
        assert f"{colored['count_down']}(-2){monitor.ANSI_RESET}" in rendered

    # A count that reports no change is not a change, so it stays plain the way the sibling tools leave it
    def test_a_static_count_is_left_plain(self):
        assert monitor._colorize_line("* Loading followings for user someuser from file (128)").endswith("(128)")

    def test_a_timestamp_row_colours_the_value_and_not_the_label(self, colored):
        assert monitor._colorize_line("Timestamp:\t\t\tSun 21 Apr 2024, 15:08:45") == f"Timestamp:\t\t\t{colored['timestamp_value']}Sun 21 Apr 2024, 15:08:45{monitor.ANSI_RESET}"

    def test_the_liveness_trailer_uses_the_same_timestamp_colours(self, colored):
        assert monitor._colorize_line("Liveness check, timestamp:\tSun 21 Apr 2024, 15:08:45") == f"Liveness check, timestamp:\t{colored['timestamp_value']}Sun 21 Apr 2024, 15:08:45{monitor.ANSI_RESET}"

    # A range is one value, so it must not be split into two separate dates
    def test_a_date_range_stays_one_span(self, colored):
        rendered = monitor._colorize_line("*** User played music from Sat 22 Nov 16:54 - 17:58")
        assert f"{colored['date_range']}Sat 22 Nov 16:54 - 17:58{monitor.ANSI_RESET}" in rendered

    def test_a_duration_is_coloured(self, colored):
        assert f"{colored['duration']}45 minutes{monitor.ANSI_RESET}" in monitor._colorize_line("* Retrying in 45 minutes")


class TestTheQuotedValues:
    def test_a_quoted_account_name_is_a_username(self, colored):
        rendered = monitor._colorize_line("* Cannot read the recent tracks of 'someuser'")
        assert f"'{colored['username']}someuser{monitor.ANSI_RESET}'" in rendered

    # Every other quoted value this tool prints is a path, a package or a menu answer
    @pytest.mark.parametrize("line", ["* Cannot save last status to '/tmp/lastfm_status.txt' file", "* Spotify player operation 'play' was sent", "  'notauser' is not a Last.fm username or profile URL."])
    def test_a_quoted_value_with_no_naming_context_stays_plain(self, colored, line):
        assert monitor._colorize_line(line) == line

    # The closing quote has to be followed by whitespace or punctuation, or a name's own apostrophe ends it early
    def test_a_name_containing_an_apostrophe_matches_whole(self):
        match = monitor._QUOTED_CONTENT_RE.search("user 'Tom Clancy's Rainbow Six' now")
        assert match is not None and match.group(2) == "Tom Clancy's Rainbow Six"

    # A greedy body would swallow everything between the first and the last quote on the line
    def test_two_quoted_values_on_one_line_stay_separate(self):
        assert monitor._QUOTED_CONTENT_RE.findall("changed from 'Halo' to 'Forza'") == [("'", "Halo", "'"), ("'", "Forza", "'")]


class TestTheReportLines:
    def test_a_doctor_marker_takes_its_status_colour(self, colored):
        assert monitor._colorize_line("[PASS] Required dependency pylast is installed") == f"{colored['boolean_true']}[PASS]{monitor.ANSI_RESET} Required dependency pylast is installed"

    def test_a_failing_marker_leaves_the_rest_of_its_row_plain(self, colored):
        rendered = monitor._colorize_line("[FAIL] Last.fm credentials are missing")
        assert rendered == f"{colored['error']}[FAIL]{monitor.ANSI_RESET} Last.fm credentials are missing"

    def test_the_notification_summary_row_colours_only_its_state(self, colored):
        assert monitor._colorize_line("* Notifications (email):        On (active)") == f"* Notifications (email):        {colored['boolean_true']}On{monitor.ANSI_RESET} (active)"

    @pytest.mark.parametrize("line, part", [("* Error: the service is unavailable", "error"), ("Sending email notification to someone@example.com", "email"), ("Sending webhook notification", "webhook"), ("To fix: run the tool again", "info")])
    def test_a_whole_line_report_takes_its_block_colour(self, colored, line, part):
        assert monitor._colorize_line(line).startswith(colored[part])

    # Warning and signal lines mark their own opening word instead of being painted end to end, so a value
    # inside them keeps the colour that says what it is
    def test_a_warning_marks_its_opening_word_and_leaves_the_rest(self, colored):
        assert monitor._colorize_line("* Warning: TLS verification is off") == f"* {colored['warning']}Warning:{monitor.ANSI_RESET} TLS verification is off"

    def test_a_signal_line_marks_the_signal_it_reports(self, colored):
        assert monitor._colorize_line("* Signal SIGUSR1 received") == f"* Signal {colored['signal']}SIGUSR1{monitor.ANSI_RESET} received"

    def test_a_warning_row_still_shows_the_value_inside_it(self, colored):
        rendered = monitor._colorize_line("* Warning: Cannot load followings state for user someuser")
        assert f"{colored['username']}someuser{monitor.ANSI_RESET}" in rendered

    # A debug trace records attempts that fail and are then handled, so it is not painted as the failure
    def test_a_debug_trace_is_not_painted_as_an_error(self, colored):
        assert not monitor._colorize_line("[DEBUG 15:08:45] Friends check: outcome=failed, attempt=#2").startswith(colored["error"])

    # A counter named in a diagnostic field is a number, not a report of a failure
    def test_a_failure_counter_field_does_not_paint_its_line(self, colored):
        assert not monitor._colorize_line("* Liveness: failures=3 since the last report").startswith(colored["error"])

    # An inner span must survive the block style rather than resetting the rest of the line to plain
    def test_a_block_style_resumes_after_an_inner_span(self, colored):
        rendered = monitor._colorize_line("* Error: the API is unavailable (retrying in 30 seconds)")
        assert rendered.startswith(colored["error"]) and rendered.endswith(monitor.ANSI_RESET)
        assert f"{colored['duration']}30 seconds{monitor.ANSI_RESET}{colored['error']}" in rendered


class TestNoRuleReclaimsAnother:
    # A later rule must not reach inside a span an earlier rule already opened
    def test_a_link_inside_a_coloured_span_is_not_recoloured(self, colored):
        line = f"{colored['info']}Guide: https://example.com/docs{monitor.ANSI_RESET}"
        assert monitor._sub_outside_color(monitor._URL_RE, lambda match: monitor.colorize("link", match.group(0)), line) == line

    def test_a_link_outside_every_span_is_coloured(self, colored):
        line = f"{colored['info']}Guide{monitor.ANSI_RESET} https://example.com/docs"
        rendered = monitor._sub_outside_color(monitor._URL_RE, lambda match: monitor.colorize("link", match.group(0)), line)
        assert rendered.endswith(f"{colored['link']}https://example.com/docs{monitor.ANSI_RESET}")

    # A later keyword rule reaching into a link would end the link span early and leave the rest plain
    def test_a_keyword_inside_a_link_does_not_break_the_link(self, colored):
        rendered = monitor._colorize_line("* See https://example.com/docs/True/ACTIVE for more")
        assert rendered == f"* See {colored['link']}https://example.com/docs/True/ACTIVE{monitor.ANSI_RESET} for more"

    def test_no_span_is_opened_inside_another(self, colored):
        rendered = monitor._colorize_line("* Followings number changed by user someuser from 12 to 14 (+2)")
        depth = 0
        for sequence in monitor.SGR_SEQUENCE_RE.findall(rendered):
            depth += -1 if sequence == monitor.ANSI_RESET else 1
            assert depth in (0, 1), rendered


class TestTheWriterStack:
    # The logger takes sys.stdout, so an already installed sanitizing stream would colourise every line twice
    def test_the_logger_unwraps_the_early_terminal_stream(self, tmp_path, monkeypatch):
        terminal = FakeTerminal(True)
        monkeypatch.setattr(monitor.sys, "stdout", monitor.TerminalStream(terminal))
        logger = monitor.Logger(str(tmp_path / "run.log"))
        assert logger.terminal is terminal
        logger.logfile.close()

    def test_one_line_is_coloured_exactly_once(self, colored, tmp_path):
        captured = io.StringIO()
        stream = monitor.Logger(str(tmp_path / "run.log"))
        stream.terminal = captured
        stream.write("Track:\t\t\t\tPink Floyd - Time\n")
        stream.logfile.close()
        assert captured.getvalue() == f"Track:\t\t\t\t{colored['track']}Pink Floyd - Time{monitor.ANSI_RESET}\n"

    def test_the_log_file_keeps_no_colour(self, colored, tmp_path):
        stream = monitor.Logger(str(tmp_path / "run.log"))
        stream.terminal = io.StringIO()
        stream.write("Track:\t\t\t\tPink Floyd - Time\n")
        stream.log_only("* Target:                       someuser\n")
        stream.logfile.close()
        assert "\x1b" not in (tmp_path / "run.log").read_text(encoding="utf-8")

    def test_the_terminal_only_channel_is_coloured_too(self, colored, tmp_path):
        captured = io.StringIO()
        stream = monitor.Logger(str(tmp_path / "run.log"))
        stream.terminal = captured
        stream.terminal_only("* Target:                       someuser\n")
        stream.logfile.close()
        assert captured.getvalue() == f"* Target:                       {colored['username']}someuser{monitor.ANSI_RESET}\n"

    def test_the_stream_without_a_log_file_colours_as_well(self, colored):
        terminal = io.StringIO()
        monitor.TerminalStream(terminal).write("Album:\t\t\t\tMeddle\n")
        assert terminal.getvalue() == f"Album:\t\t\t\t{colored['album']}Meddle{monitor.ANSI_RESET}\n"


class TestTheRedrawnLines:
    # The progress line is erased by writing exactly len(line) spaces, and an escape sequence is not width
    def test_the_doctor_progress_line_carries_no_escapes(self, monkeypatch):
        terminal = io.StringIO()
        terminal.isatty = lambda: True  # type: ignore[method-assign]
        monkeypatch.setattr(monitor.sys, "stdout", terminal)
        monkeypatch.setattr(monitor, "DOCTOR_PROGRESS_WIDTH", 0)
        monitor._doctor_progress("connectivity \x1b[31mred\x1b[0m")
        written = terminal.getvalue()
        assert "\x1b" not in written
        assert monitor.DOCTOR_PROGRESS_WIDTH == len(written.lstrip("\r"))

    def test_the_erase_covers_exactly_what_was_drawn(self, monkeypatch):
        terminal = io.StringIO()
        terminal.isatty = lambda: True  # type: ignore[method-assign]
        monkeypatch.setattr(monitor.sys, "stdout", terminal)
        monkeypatch.setattr(monitor, "DOCTOR_PROGRESS_WIDTH", 0)
        monitor._doctor_progress("connectivity")
        drawn = len(terminal.getvalue().lstrip("\r"))
        terminal.truncate(0)
        terminal.seek(0)
        monitor._doctor_progress_clear()
        assert terminal.getvalue() == "\r" + (" " * drawn) + "\r"


# Builds a report holding the given checks, since the report object collects them rather than taking them
def report_of(*checks):
    report = monitor.DoctorReport()
    report.checks.extend(checks)
    return report


class TestTheDoctorReport:
    def test_the_heading_and_sections_are_coloured(self, colored):
        rendered = monitor.render_doctor_sections(report_of(monitor.make_doctor_check("Environment", "PASS", "Python 3.13 is supported")))
        assert rendered.startswith(f"{colored['header']}Doctor{monitor.ANSI_RESET}")
        assert f"{colored['section']}Environment{monitor.ANSI_RESET}" in rendered

    def test_a_fix_line_is_drawn_as_guidance(self, colored):
        advice = monitor.make_recovery_advice("dependency.missing", "pylast is missing", "Install it with: pip3 install pylast", False)
        rendered = monitor.render_doctor_sections(report_of(monitor.make_doctor_check("Environment", "FAIL", advice.summary, advice=advice)))
        assert f"  {colored['info']}To fix: Install it with: pip3 install pylast{monitor.ANSI_RESET}" in rendered

    # The report is printed before any line colouriser is installed, so the renderer colours its own links
    def test_a_link_in_a_detail_line_is_a_link(self, colored):
        rendered = monitor.render_doctor_sections(report_of(monitor.make_doctor_check("Connectivity", "PASS", "Last.fm API is reachable", "Endpoint: https://ws.audioscrobbler.com/2.0/")))
        assert f"{colored['link']}https://ws.audioscrobbler.com/2.0/{monitor.ANSI_RESET}" in rendered

    @pytest.mark.parametrize("status, part", [("FAIL", "error"), ("WARN", "warning"), ("PASS", "boolean_true")])
    def test_the_verdict_is_coloured_by_what_it_says(self, colored, status, part):
        advice = monitor.make_recovery_advice("config.invalid", "row", "Fix it", False)
        checks = [monitor.make_doctor_check("Environment", status, "row", advice=advice if status != "PASS" else None)]
        assert colored[part] in monitor.render_doctor_summary(checks)

    def test_the_marker_table_covers_every_status(self, colored):
        assert set(monitor.DOCTOR_MARK_STYLES) == {"PASS", "WARN", "FAIL", "SKIP"}
        assert monitor.render_doctor_marker("SKIP") == f"{colored['info']}[SKIP]{monitor.ANSI_RESET}"


class TestTheSetupSurfaces:
    def test_a_printed_command_stands_out_from_its_label(self, colored, capsys):
        monitor._wizard_print_command("Start monitoring:", "lastfm_monitor someuser")
        printed = capsys.readouterr().out
        assert f"    {colored['section']}lastfm_monitor someuser{monitor.ANSI_RESET}" in printed
        assert printed.startswith("Start monitoring:")

    def test_a_wizard_prompt_is_drawn_as_a_question(self, colored):
        asked = {}
        monitor._wizard_input("Last.fm username: ", input_func=lambda prompt: asked.setdefault("prompt", prompt) or "someuser")
        assert asked["prompt"] == f"{colored['info']}Last.fm username: {monitor.ANSI_RESET}"

    def test_a_menu_number_is_drawn_apart_from_its_label(self, colored, capsys):
        monitor._wizard_ask_choice("What next?", [("Save settings", ""), ("Discard", "")], input_func=lambda prompt: "1")
        printed = capsys.readouterr().out
        assert f"  {colored['username']}1{monitor.ANSI_RESET}. Save settings{colored['info']} (default){monitor.ANSI_RESET}" in printed

    def test_a_summary_value_reports_its_own_state(self, colored):
        assert monitor._wizard_summary_value("Target", "someuser") == f"{colored['username']}someuser{monitor.ANSI_RESET}"
        assert monitor._wizard_summary_value("Output log", "enabled") == f"{colored['boolean_true']}enabled{monitor.ANSI_RESET}"
        assert monitor._wizard_summary_value("CSV output", "disabled") == f"{colored['boolean_false']}disabled{monitor.ANSI_RESET}"

    def test_the_welcome_screen_separates_commands_from_links(self, colored, capsys):
        monitor.print_welcome_screen(interactive=False)
        printed = capsys.readouterr().out
        assert colored["section"] in printed and colored["link"] in printed


class TestTheHelpScreen:
    def test_argparse_is_told_not_to_colour_itself(self):
        expected = {"color": False} if sys.version_info >= (3, 14) else {}
        assert monitor.argparse_color_kwargs() == expected

    # Without this the helper can keep returning the right answer while nothing passes it to argparse
    def test_the_parser_actually_receives_it(self):
        assert "**argparse_color_kwargs()" in SOURCE

    def test_the_flag_exists_and_says_what_it_does(self):
        assert '"--no-color"' in SOURCE and "Disable coloured output in the terminal" in SOURCE


class TestTheStartupPath:
    # The version line and the screen clear both run before argparse, so the setting has to be read first
    def test_colour_is_resolved_before_arguments_are_parsed(self):
        main = next(node for node in ast.walk(TREE) if isinstance(node, ast.FunctionDef) and node.name == "main")
        calls = [ast.unparse(node) for node in ast.walk(main) if isinstance(node, ast.Call)]
        assert calls.index("init_color_output(stdout_bck)") < next(index for index, call in enumerate(calls) if call.startswith("ColoredHelpParser("))

    def test_the_config_file_can_switch_colour_off_before_the_first_line(self, restored_globals, tmp_path, monkeypatch):
        config = tmp_path / "lastfm.conf"
        config.write_text("COLORED_OUTPUT = False\n", encoding="utf-8")
        monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor", "--config-file", str(config)])
        monitor.COLORED_OUTPUT = True
        monitor.apply_early_output_config()
        assert monitor.COLORED_OUTPUT is False

    def test_the_startup_summary_reports_what_colour_actually_did(self, restored_globals, capsys):
        monitor.COLORED_OUTPUT = True
        monitor.COLOR_ENABLED = False
        rows = monitor.build_startup_summary("someuser", "lastfm.conf", ".env", "lastfm.log")
        assert ("Coloured output", "False (setting: True)") in [(row.label, row.value) for row in rows]


class TestTheDocumentedTheme:
    # The table is what a reader edits COLOR_THEME from, so it has to list exactly the keys the theme ships
    def test_the_configuration_page_lists_every_theme_key(self):
        lines = (PROJECT_ROOT / "docs" / "configuration.md").read_text(encoding="utf-8").splitlines()
        start = lines.index("| Theme key | Colours |") + 2
        end = next(index for index in range(start, len(lines)) if not lines[index].startswith("|"))
        documented = set()
        for row in lines[start:end]:
            documented |= set(re.findall(r"`([a-z_]+)`", row.split("|")[1]))
        assert sorted(set(monitor.DEFAULT_COLOR_THEME) - documented) == []
        assert sorted(documented - set(monitor.DEFAULT_COLOR_THEME)) == []


# Verifies the TLS row colours its state word, the one setting whose off state weakens a security property
def test_the_tls_row_colours_its_state(colored):
    on_row = monitor._colorize_line("* TLS verification:             On")
    off_row = monitor._colorize_line("* TLS verification:             Off, server certificates are not checked")

    assert on_row == f"* TLS verification:             {colored['boolean_true']}On{monitor.ANSI_RESET}"
    assert off_row == f"* TLS verification:             {colored['boolean_false']}Off{monitor.ANSI_RESET}, server certificates are not checked"


HELP_SAMPLE = """usage: monitor [-h] [--config-file PATH] [TARGET]

positional arguments:
  TARGET                The target to monitor

Configuration & dotenv files:
  --config-file PATH    Path to a config file
  -m, --check-interval SECONDS
                        Time between checks (default: 60)

Examples:

Getting started:
  # Guided setup, see https://example.invalid/guide/
  python3 monitor.py --setup <target>

Guide: https://example.invalid/guide/
"""

HELP_SAMPLE_EPILOG = HELP_SAMPLE[HELP_SAMPLE.index("Examples:"):]


# Enables colour with the shipped theme and returns the escape sequence of every part
@pytest.fixture
def help_palette(monkeypatch):
    styles = {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", styles)
    return styles


# Returns the sample help screen with the help palette applied
@pytest.fixture
def colored_help(help_palette):
    return monitor.colorize_help_text(HELP_SAMPLE, HELP_SAMPLE_EPILOG)


# Verifies colouring changes no character of the screen, since argparse laid out its columns on the plain text
def test_the_coloured_help_keeps_the_plain_layout(colored_help):
    assert monitor.ANSI_ESCAPE_RE.sub("", colored_help) == HELP_SAMPLE


# Verifies the argument groups and the example tasks share one heading colour, the anchors the reader scans for
def test_the_help_headings_carry_the_heading_colour(help_palette, colored_help):
    for heading in ("positional arguments:", "Configuration & dotenv files:", "Examples:", "Getting started:"):
        assert f"{help_palette['help_heading']}{heading}{monitor.ANSI_RESET}" in colored_help


# Verifies an option name and the value it takes are coloured apart, in the usage block and in the option rows
def test_the_help_option_names_and_their_values_are_coloured_apart(help_palette, colored_help):
    option = f"{help_palette['help_option']}--config-file{monitor.ANSI_RESET}"
    metavar = f"{help_palette['help_metavar']}PATH{monitor.ANSI_RESET}"

    assert f"{option} {metavar}" in colored_help
    assert f"[{option} {metavar}]" in colored_help
    assert f"{help_palette['help_usage']}usage:{monitor.ANSI_RESET}" in colored_help
    assert f"{help_palette['help_metavar']}TARGET{monitor.ANSI_RESET}                The target to monitor" in colored_help


# Verifies the examples separate the comment from the command and mark the value the reader has to replace
def test_the_help_examples_mark_comments_commands_and_placeholders(help_palette, colored_help):
    assert f"{help_palette['help_comment']}  # Guided setup" in colored_help
    assert f"{help_palette['help_command']}  python3 monitor.py --setup" in colored_help
    assert f"{help_palette['help_placeholder']}<target>{monitor.ANSI_RESET}" in colored_help


# Verifies a default note is dimmed and a documentation link keeps the shared link colour
def test_the_help_default_notes_and_links_stay_secondary(help_palette, colored_help):
    assert f"{help_palette['help_default']}(default: 60){monitor.ANSI_RESET}" in colored_help
    assert f"{help_palette['link']}https://example.invalid/guide/{monitor.ANSI_RESET}" in colored_help


# Verifies the help screen stays plain while colour is switched off, so --no-color and NO_COLOR clear all of it
def test_the_help_palette_switches_off_with_colour():
    assert monitor.colorize_help_text(HELP_SAMPLE, HELP_SAMPLE_EPILOG) == HELP_SAMPLE


# Verifies the finished help screen reaches the terminal untouched, past the colouriser that paints monitoring output
def test_the_help_screen_is_not_repainted_by_the_monitoring_rules(help_palette):
    buffer = StringIO()
    parser = monitor.ColoredHelpParser(prog="monitor", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config-file", metavar="PATH", help="Path to a config file")
    parser.print_help(monitor.TerminalStream(buffer))

    written = buffer.getvalue()
    assert written == parser.format_help()
    assert help_palette["help_option"] in written


# Verifies the setup screens colour their links, since they print before the output stream colouriser is installed
def test_setup_screen_links_are_coloured(monkeypatch):
    link = monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["link"])
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {"link": link})

    assert monitor.colorize_links("Guide: https://example.test/page") == f"Guide: {link}https://example.test/page{monitor.ANSI_RESET}"


# Verifies no setup screen prints a link without colouring it, which is how a plain link gets in
def test_no_setup_screen_prints_a_plain_link():
    setup = re.compile(r"^(?:run_setup_wizard|run_scrobble_health_setup_wizard|_wizard_|run_set_|run_browser_cookie_import|print_welcome_screen|print_doctor_next_steps|print_spotify_scrobble_app_guidance)")
    tree = ast.parse(Path(monitor.__file__).read_text(encoding="utf-8"))
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    plain = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print"):
            continue
        nested = list(ast.walk(node))
        prints_link = any(isinstance(item, ast.Constant) and isinstance(item.value, str) and "http" in item.value for item in nested) or any(isinstance(item, ast.Name) and "URL" in item.id for item in nested)
        coloured = any(isinstance(item, ast.Name) and item.id in ("colorize", "colorize_links") for item in nested)
        owner, current = "", parents.get(node)
        while current is not None:
            if isinstance(current, ast.FunctionDef):
                owner = current.name
                break
            current = parents.get(current)
        if prints_link and not coloured and setup.match(owner):
            plain.append(f"{owner}:{node.lineno}")

    assert plain == []


# Verifies a fix block keeps its guide line a link while the rest of the block stays informational
def test_a_fix_block_guide_line_is_a_link(monkeypatch):
    link = monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["link"])
    info = monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["info"])
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {"link": link, "info": info})

    assert monitor.colorize_fix_line("To fix: Set the key then re-run") == f"{info}To fix: Set the key then re-run{monitor.ANSI_RESET}"
    assert monitor.colorize_fix_line("Guide: https://example.test/page") == f"Guide: {link}https://example.test/page{monitor.ANSI_RESET}"
    assert 'colorize("info", f"Guide:' not in Path(monitor.__file__).read_text(encoding="utf-8")


# Verifies the early peek carries the theme, since --help is printed and exited from inside argparse before the config load
def test_the_early_output_config_carries_the_help_theme(monkeypatch, tmp_path):
    (tmp_path / "lastfm_monitor.conf").write_text('COLOR_THEME = {"help_heading": "bright_red"}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "COLOR_THEME", {})
    monkeypatch.setattr(monitor, "CONFIG_DISCOVERY_DISABLED", False)
    monkeypatch.setattr(monitor.sys, "argv", ["lastfm_monitor", "--help"])

    monitor.apply_early_output_config()

    assert monitor.COLOR_THEME == {"help_heading": "bright_red"}


# Verifies a settings row is never painted as a log line, since a label or a value can read like an error keyword
@pytest.mark.parametrize("label,value", [("Error retry timer", "3 minutes"), ("Polling interval", "5 minutes, longer after a failure")])
def test_a_summary_row_is_not_painted_by_a_log_keyword(monkeypatch, label, value):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: f"<{name}>" for name in monitor.DEFAULT_COLOR_THEME})
    line = monitor.format_startup_summary_row(monitor.StartupSummaryRow(label, value)).rstrip("\n")

    # The value highlights still apply, so only the whole-row block styles have to be absent
    coloured = monitor._colorize_line(line)

    assert "<error>" not in coloured and "<warning>" not in coloured


# Verifies an ordinary error line still carries the block colour the summary rows opt out of
def test_an_error_line_is_still_painted(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {"error": "<error>"})

    assert "<error>" in monitor._colorize_line("* Error: the request failed")


# Verifies the row shape the colouriser matches is the one the summary emitter prints, so the two cannot drift
def test_every_summary_row_is_recognised_by_its_value_column():
    for row in (monitor.StartupSummaryRow("Target", "someone"), monitor.StartupSummaryRow("Email transport", "Not configured")):
        line = monitor.format_startup_summary_row(row).rstrip("\n")
        assert monitor.is_startup_summary_row(line)
        assert line.index(row.value.split(" ")[0]) == monitor.STARTUP_SUMMARY_VALUE_COLUMN

    assert not monitor.is_startup_summary_row("* Error: something failed")
    assert not monitor.is_startup_summary_row("* Warning: a timeout was hit")
