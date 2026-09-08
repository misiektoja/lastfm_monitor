"""The startup summary: the rows a run prints, the order they come in and which view each one belongs to."""

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

# The rows every sibling tool prints, in the order the family agreed on
SHARED_ROW_ORDER = (
    "Target",
    "Polling intervals",
    "Notifications (email)",
    "Notifications (webhook)",
    "Output",
    "Output logging",
    "Config",
    "Dotenv",
    "Liveness output",
    "CSV output",
    "Install method",
    "Secrets from dotenv",
    "Secrets from environment",
    "Secrets from config file",
    "Secrets from command line",
    "TLS verification",
    "ASCII log separators",
    "Coloured output",
    "Verbose mode",
    "Debug mode",
    "More details",
)

# Every row this tool adds to band four, none of which may appear outside it
OWN_ROWS = (
    "Followings tracking",
    "Followers tracking",
    "Bio tracking",
    "Display name tracking",
    "Friends check interval",
    "Metadata backend",
    "Spotify token cache",
    "Spotify playback control",
    "Track duration from Spotify",
    "Duration marks",
    "Play break multiplier",
    "Progress indicator",
    "Monitored-track alerts",
    "Status file",
)


@pytest.fixture
def restored_globals():
    saved = {name: value for name, value in vars(monitor).items() if name.isupper()}
    yield
    for name, value in saved.items():
        setattr(monitor, name, value)


# Runs main with the output log switched on and returns the log file the run wrote
def run_main_with_logging(tmp_path, arguments=()):
    log_path = tmp_path / "run_someuser.log"
    saved_stdout = sys.stdout
    try:
        run_main_to_the_loop(tmp_path, config_body='DISABLE_LOGGING = False\nLF_LOGFILE = "run"\n', arguments=arguments)
    finally:
        sys.stdout = saved_stdout
    return log_path


def labels(rows):
    return [row.label for row in rows]


def row_named(rows, label):
    return next(row for row in rows if row.label == label)


# Runs main through the real config load and startup summary, stopping where the monitoring loop would start
def run_main_to_the_loop(tmp_path, config_body="", arguments=()):
    config_path = tmp_path / "lastfm.conf"
    config_path.write_text(f'LASTFM_API_KEY = "{API_KEY}"\nLASTFM_API_SECRET = "{API_SECRET}"\nDISABLE_LOGGING = True\n{config_body}', encoding="utf-8")
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(tmp_path)
        patch.setattr(monitor, "lastfm_monitor_user", lambda *args, **kwargs: sys.exit(0))
        patch.setattr(monitor, "check_internet", lambda *a, **k: True)
        patch.setattr(monitor.sys, "argv", ["lastfm_monitor", "someuser", "--config-file", str(config_path), "--env-file", "none", *arguments])
        with pytest.raises(SystemExit):
            monitor.main()


class TestTheRowContract:
    def test_the_routing_flags_default_to_the_family_values(self):
        row = monitor.StartupSummaryRow("Target", "someuser")
        assert (row.concise, row.full, row.log) == (False, True, True)

    # This is the check that found two overlong labels in a sibling after its own conversion
    def test_no_label_is_wider_than_the_column(self):
        overlong = []
        for node in ast.walk(TREE):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "StartupSummaryRow":
                first = node.args[0] if node.args else None
                assert isinstance(first, ast.Constant) and isinstance(first.value, str), f"line {node.lineno} does not name its row with a literal"
                if len(first.value) > 28:
                    overlong.append((node.lineno, first.value))
        assert overlong == []

    # Tabs move the column whenever a label crosses a multiple of eight, which is what this replaced
    def test_the_value_column_is_the_same_for_every_row(self, restored_globals, tmp_path, capsys):
        run_main_to_the_loop(tmp_path, arguments=["--verbose"])
        printed = capsys.readouterr().out.splitlines()
        summary_labels = set(labels(monitor.build_startup_summary("someuser")))
        columns = set()
        for line in printed:
            match = re.match(r"^\* (?P<label>[^:]+): +(?P<value>\S)", line)
            if match and match.group("label") in summary_labels:
                columns.add(match.start("value"))
        assert columns == {32}


class TestTheRowOrder:
    def test_the_shared_rows_match_the_sibling_tools(self):
        rows = monitor.build_startup_summary("someuser", "lastfm.conf", ".env", "lastfm.log")
        assert [label for label in labels(rows) if label in SHARED_ROW_ORDER] == list(SHARED_ROW_ORDER)

    def test_every_label_is_unique(self):
        rows = monitor.build_startup_summary("someuser", "lastfm.conf", ".env", "lastfm.log")
        assert len(set(labels(rows))) == len(rows)

    # Band one carries the tool's own timers next to the intervals they belong with
    def test_the_inactivity_timer_follows_the_polling_intervals(self):
        printed = labels(monitor.build_startup_summary("someuser", "lastfm.conf", ".env", "lastfm.log"))
        assert printed.index("Inactivity timer") == printed.index("Polling intervals") + 1

    # This tool's own rows go in band four, between the files the run was given and the environment it runs in
    def test_this_tools_own_rows_stay_in_their_band(self):
        printed = labels(monitor.build_startup_summary("someuser", "lastfm.conf", ".env", "lastfm.log"))
        own_positions = [printed.index(label) for label in OWN_ROWS if label in printed]
        assert len(own_positions) == len(OWN_ROWS)
        assert min(own_positions) > printed.index("Notifications (webhook)")
        assert max(own_positions) < printed.index("Install method")

    # Ten rows between them in a sibling read as two unrelated settings
    def test_the_two_output_rows_stay_adjacent(self):
        printed = labels(monitor.build_startup_summary("someuser", "lastfm.conf", ".env", "lastfm.log"))
        assert printed.index("Output logging") == printed.index("Output") + 1

    # A row appended after the pointer row is invisible in both views, so it is a landmine for the next edit
    def test_nothing_follows_the_pointer_row(self):
        assert labels(monitor.build_startup_summary("someuser", "lastfm.conf", ".env", "lastfm.log"))[-1] == "More details"


class TestTheRouting:
    def test_only_the_two_pointer_rows_are_concise_only(self):
        rows = monitor.build_startup_summary("someuser", "lastfm.conf", ".env", "lastfm.log")
        assert [row.label for row in rows if row.concise and not row.full] == ["Output", "More details"]
        assert [row.label for row in rows if not row.log] == ["Output", "More details"]

    def test_every_other_row_reaches_the_full_view_and_the_log(self):
        rows = monitor.build_startup_summary("someuser", "lastfm.conf", ".env", "lastfm.log")
        assert all(row.full and row.log for row in rows if row.label not in ("Output", "More details"))

    # An optional feature is shown in the short view exactly while it is switched on
    @pytest.mark.parametrize("label, setting, on, off", [
        ("CSV output", "CSV_FILE", "played.csv", ""),
        ("Monitored-track alerts", "MONITOR_LIST_FILE", "tracks.txt", ""),
        ("Liveness output", "LIVENESS_CHECK_INTERVAL", 3600, 0),
        ("Followings tracking", "TRACK_FOLLOWINGS", True, False),
        ("Followers tracking", "TRACK_FOLLOWERS", True, False),
        ("Bio tracking", "TRACK_BIO", True, False),
        ("Display name tracking", "TRACK_DISPLAY_NAME", True, False),
        ("Progress indicator", "PROGRESS_INDICATOR", True, False),
        ("Spotify playback control", "TRACK_SONGS", True, False),
        ("Track duration from Spotify", "USE_TRACK_DURATION_FROM_SPOTIFY", True, False),
    ])
    def test_an_optional_row_is_concise_while_it_is_on(self, monkeypatch, label, setting, on, off):
        monkeypatch.setattr(monitor, setting, on)
        assert row_named(monitor.build_startup_summary("someuser"), label).concise is True
        monkeypatch.setattr(monitor, setting, off)
        assert row_named(monitor.build_startup_summary("someuser"), label).concise is False

    # A cache row for a backend the run never reaches reads as a feature that is on
    def test_the_token_cache_row_is_concise_only_while_that_backend_runs(self, monkeypatch):
        monkeypatch.setattr(monitor, "SP_TOKENS_FILE", "tokens.json")
        monkeypatch.setattr(monitor, "SP_CLIENT_ID", "an-app-client-id")
        monkeypatch.setattr(monitor, "SP_CLIENT_SECRET", "an-app-client-secret")
        monkeypatch.setattr(monitor, "TRACK_SONGS", False)
        monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", False)
        assert row_named(monitor.build_startup_summary("someuser"), "Spotify token cache").concise is False
        monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", True)
        assert row_named(monitor.build_startup_summary("someuser"), "Spotify token cache").concise is True
        monkeypatch.setattr(monitor, "SP_CLIENT_ID", "your_spotify_app_client_id")
        assert row_named(monitor.build_startup_summary("someuser"), "Spotify token cache").concise is False

    # The one row that is concise while it is off, since an intercepted connection cannot be told from the real one
    def test_the_tls_row_is_concise_only_while_verification_is_off(self, monkeypatch):
        monkeypatch.setattr(monitor, "VERIFY_SSL", True)
        assert row_named(monitor.build_startup_summary("someuser"), "TLS verification").concise is False
        monkeypatch.setattr(monitor, "VERIFY_SSL", False)
        assert row_named(monitor.build_startup_summary("someuser"), "TLS verification").concise is True

    @pytest.mark.parametrize("setting", ["VERBOSE_MODE", "DEBUG_MODE"])
    def test_a_mode_row_appears_in_the_short_view_while_that_mode_is_on(self, monkeypatch, setting):
        monkeypatch.setattr(monitor, setting, True)
        assert row_named(monitor.build_startup_summary("someuser"), setting.split("_")[0].capitalize() + " mode").concise is True


class TestTheValues:
    def test_the_four_secret_rows_list_names_and_never_values(self, monkeypatch, restored_globals):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", API_KEY)
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "not-a-real-password")
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {"LASTFM_API_KEY": "config file", "SMTP_PASSWORD": "dotenv file"})
        rows = monitor.build_startup_summary("someuser")
        assert row_named(rows, "Secrets from config file").value == "LASTFM_API_KEY"
        assert row_named(rows, "Secrets from dotenv").value == "SMTP_PASSWORD"
        assert row_named(rows, "Secrets from environment").value == "None"
        assert row_named(rows, "Secrets from command line").value == "None"
        assert API_KEY not in str([row.value for row in rows])

    # A file row is the path or Disabled, not True with the path in parentheses
    @pytest.mark.parametrize("label, setting, value", [("CSV output", "CSV_FILE", "played.csv"), ("Monitored-track alerts", "MONITOR_LIST_FILE", "tracks.txt")])
    def test_a_file_row_is_the_path_itself(self, monkeypatch, label, setting, value):
        monkeypatch.setattr(monitor, setting, value)
        assert row_named(monitor.build_startup_summary("someuser"), label).value == value
        monkeypatch.setattr(monitor, setting, "")
        assert row_named(monitor.build_startup_summary("someuser"), label).value == "Disabled"

    def test_the_liveness_row_is_the_interval_itself(self, monkeypatch):
        monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", 43200)
        assert row_named(monitor.build_startup_summary("someuser"), "Liveness output").value == "12 hours"
        monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", 0)
        assert row_named(monitor.build_startup_summary("someuser"), "Liveness output").value == "Disabled"

    def test_the_two_output_rows_answer_different_questions(self, monkeypatch):
        monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
        rows = monitor.build_startup_summary("someuser", log_path="lastfm_someuser.log")
        assert row_named(rows, "Output").value == "lastfm_someuser.log"
        assert row_named(rows, "Output logging").value == "lastfm_someuser.log"
        monkeypatch.setattr(monitor, "DISABLE_LOGGING", True)
        rows = monitor.build_startup_summary("someuser", log_path=None)
        assert row_named(rows, "Output").value == "Terminal only (logging disabled)"
        assert row_named(rows, "Output logging").value == "Disabled"

    def test_the_metadata_row_names_the_backends_in_the_order_they_are_tried(self, monkeypatch):
        monkeypatch.setattr(monitor, "TRACK_SONGS", True)
        monkeypatch.setattr(monitor, "SP_CLIENT_ID", "an-app-client-id")
        monkeypatch.setattr(monitor, "SP_CLIENT_SECRET", "an-app-client-secret")
        assert row_named(monitor.build_startup_summary("someuser"), "Metadata backend").value == "OAuth app, then anonymous web player"
        monkeypatch.setattr(monitor, "SP_CLIENT_ID", "your_spotify_app_client_id")
        assert row_named(monitor.build_startup_summary("someuser"), "Metadata backend").value == "Anonymous web player"
        monkeypatch.setattr(monitor, "TRACK_SONGS", False)
        monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", False)
        assert row_named(monitor.build_startup_summary("someuser"), "Metadata backend").value == "Disabled"

    def test_the_notification_rows_roll_up_the_alerts_each_channel_sends(self, monkeypatch):
        monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
        monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
        monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
        rows = monitor.build_startup_summary("someuser")
        assert row_named(rows, "Notifications (email)").value == "On (active, errors)"
        assert row_named(rows, "Notifications (webhook)").value == "Off"

    def test_the_target_row_names_the_monitored_user(self):
        assert row_named(monitor.build_startup_summary("someuser"), "Target").value == "someuser"
        assert row_named(monitor.build_startup_summary(None), "Target").value == "None"


class TestWhatEachViewPrints:
    def test_the_short_view_prints_only_the_concise_rows(self, restored_globals, tmp_path, capsys):
        run_main_to_the_loop(tmp_path)
        printed = [line for line in capsys.readouterr().out.splitlines() if line.startswith("* ")]
        assert any(line.startswith("* More details:") for line in printed)
        assert not any(line.startswith("* Install method:") for line in printed)
        assert not any(line.startswith("* Output logging:") for line in printed)

    def test_the_full_view_prints_every_other_row(self, restored_globals, tmp_path, capsys):
        run_main_to_the_loop(tmp_path, arguments=["--verbose"])
        printed = [line for line in capsys.readouterr().out.splitlines() if line.startswith("* ")]
        rendered = {line.split(":", 1)[0][2:] for line in printed}
        assert set(SHARED_ROW_ORDER) - {"Output", "More details"} <= rendered
        assert set(OWN_ROWS) <= rendered
        assert not any(line.startswith("* More details:") for line in printed)

    # The rollup grows past the terminal width once every alert is on, so it wraps into the value column
    def test_a_long_rollup_wraps_under_its_own_value_column(self, monkeypatch):
        for setting in ("ACTIVE_NOTIFICATION", "INACTIVE_NOTIFICATION", "TRACK_NOTIFICATION", "SONG_NOTIFICATION", "SONG_ON_LOOP_NOTIFICATION", "OFFLINE_ENTRIES_NOTIFICATION", "ERROR_NOTIFICATION", "FOLLOWERS_NOTIFICATION", "FOLLOWINGS_NOTIFICATION", "PROFILE_NOTIFICATION"):
            monkeypatch.setattr(monitor, setting, True)
        rendered = monitor.format_startup_summary_row(row_named(monitor.build_startup_summary("someuser"), "Notifications (email)"))
        lines = rendered.rstrip("\n").splitlines()
        assert lines[0].startswith("* Notifications (email):        On (active, inactive")
        assert lines[1].startswith(" " * 32)
        assert all(len(line) <= 100 for line in lines)


class TestTheLogAlwaysGetsTheFullView:
    def test_the_logger_writes_each_channel_on_its_own(self, tmp_path, capsys):
        stream = monitor.Logger(str(tmp_path / "split.log"))
        stream.terminal_only("terminal\n")
        stream.log_only("log\n")
        stream.write("both\n")
        assert capsys.readouterr().out == "terminal\nboth\n"
        assert (tmp_path / "split.log").read_text(encoding="utf-8") == "log\nboth\n"

    # The log file is written for a reader with no terminal, so it gets the same tab expansion as every other line
    def test_the_log_channel_expands_tabs_like_the_shared_writer(self, tmp_path, capsys):
        stream = monitor.Logger(str(tmp_path / "tabs.log"))
        stream.log_only("a\tb\n")
        capsys.readouterr()
        assert (tmp_path / "tabs.log").read_text(encoding="utf-8") == "a       b\n"

    # A log attached to a bug report has to carry every effective setting, whichever view the reporter saw
    def test_a_full_view_row_reaches_the_log_but_not_the_terminal(self, restored_globals, tmp_path, capsys):
        log_path = run_main_with_logging(tmp_path)
        printed = capsys.readouterr().out
        logged = log_path.read_text(encoding="utf-8")
        assert "* Install method:" in logged
        assert "* Install method:" not in printed
        assert "* Output logging:" in logged
        assert "* Output logging:" not in printed

    # Both pointer rows orient a reader at a terminal, so neither belongs in the file that already answers them
    def test_the_two_pointer_rows_stay_out_of_the_log(self, restored_globals, tmp_path, capsys):
        log_path = run_main_with_logging(tmp_path)
        printed = capsys.readouterr().out
        logged = log_path.read_text(encoding="utf-8")
        assert "* More details:" in printed
        assert "* More details:" not in logged
        assert "* Output:" in printed
        assert "* Output:" not in logged

    def test_the_full_view_run_logs_the_same_rows(self, restored_globals, tmp_path, capsys):
        log_path = run_main_with_logging(tmp_path, arguments=["--verbose"])
        capsys.readouterr()
        logged = log_path.read_text(encoding="utf-8")
        rendered = {line.split(":", 1)[0][2:] for line in logged.splitlines() if line.startswith("* ") and ":" in line}
        assert set(SHARED_ROW_ORDER) - {"Output", "More details"} <= rendered
        assert set(OWN_ROWS) <= rendered

    # A plain buffer has no log channel, which is what lets a test render the summary without capturing stdout
    def test_a_stream_without_the_two_channels_still_gets_the_terminal_view(self):
        buffer = io.StringIO()
        monitor.emit_startup_summary(monitor.build_startup_summary("someuser"), show_full=False, stream=buffer)
        assert "* More details:" in buffer.getvalue()
        assert "* Install method:" not in buffer.getvalue()
