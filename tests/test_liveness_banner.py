"""The liveness banner: what a quiet run prints, and how often it prints it."""

import ast
import re
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")

CONFIG_HEADER = """LASTFM_API_KEY = "lastfmapikey00000000000000000000"
LASTFM_API_SECRET = "lastfmapisecret00000000000000000"
DISABLE_LOGGING = True
"""


@pytest.fixture
def restored_globals():
    saved = {name: value for name, value in vars(monitor).items() if name.isupper()}
    yield
    for name, value in saved.items():
        setattr(monitor, name, value)


# Runs main through the real config load and argument handling, stopping where the monitoring loop would start
def run_main_to_the_loop(tmp_path, config_body, arguments=()):
    config_path = tmp_path / "lastfm.conf"
    config_path.write_text(CONFIG_HEADER + config_body, encoding="utf-8")
    settled = {}

    def stop_at_the_loop(user, network, username, tracks, csv_file_name):
        settled.update({name: getattr(monitor, name) for name in ("LIVENESS_CHECK_INTERVAL", "LIVENESS_REMINDER_SECONDS", "LASTFM_CHECK_INTERVAL")})
        raise SystemExit(0)

    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(tmp_path)
        patch.setattr(monitor, "lastfm_monitor_user", stop_at_the_loop)
        patch.setattr(monitor, "check_internet", lambda *a, **k: True)
        patch.setattr(monitor.sys, "argv", ["lastfm_monitor", "someuser", "--config-file", str(config_path), "--env-file", "none", *arguments])
        with pytest.raises(SystemExit):
            monitor.main()
    return settled


class FakeClock:
    def __init__(self, start=1757000000):
        self.now = start
        self.slept = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += int(seconds)


class FakeTrack:
    def __init__(self, artist="Artist", title="Track"):
        self.artist = artist
        self.title = title
        self.info = {"album": ""}

    def __eq__(self, other):
        return isinstance(other, FakeTrack) and (self.artist, self.title) == (other.artist, other.title)

    def __hash__(self):
        return hash((self.artist, self.title))

    def __str__(self):
        return f"{self.artist} - {self.title}"


class FakePlayed:
    def __init__(self, timestamp, track):
        self.timestamp = timestamp
        self.track = track
        self.album = ""


class FakeUser:
    def __init__(self, clock, now_playing, scrobbles):
        self.clock = clock
        self.now_playing = now_playing
        self.scrobbles = scrobbles

    def get_now_playing(self):
        return self.now_playing(self.clock.now)

    def get_recent_tracks(self, limit=1):
        return [FakePlayed(*self.scrobbles(self.clock.now))]


class FakeNetwork:
    def __init__(self, user):
        self.user = user

    def get_user(self, username):
        return self.user


# Runs the real monitoring loop on a fake clock advanced by each patched sleep and returns what it printed
def drive_loop(monkeypatch, capsys, tmp_path, now_playing, horizon, check_interval=30, active_interval=10, liveness=3600, scrobbles=None):
    clock = FakeClock()
    if scrobbles is None:
        first_scrobble, only_track = clock.now - 600, FakeTrack()
        scrobbles = lambda now: (first_scrobble, only_track)

    user = FakeUser(clock, now_playing, scrobbles)
    network = FakeNetwork(user)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "time", clock)
    monkeypatch.setattr(monitor, "LASTFM_CHECK_INTERVAL", check_interval)
    monkeypatch.setattr(monitor, "LASTFM_ACTIVE_CHECK_INTERVAL", active_interval)
    monkeypatch.setattr(monitor, "LASTFM_INACTIVITY_CHECK", 180)
    monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", liveness)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", liveness if liveness > 0 else 0)
    monkeypatch.setattr(monitor, "TRACK_FOLLOWINGS", False)
    monkeypatch.setattr(monitor, "TRACK_FOLLOWERS", False)
    monkeypatch.setattr(monitor, "TRACK_BIO", False)
    monkeypatch.setattr(monitor, "TRACK_DISPLAY_NAME", False)
    monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", False)
    monkeypatch.setattr(monitor, "PROGRESS_INDICATOR", False)
    monkeypatch.setattr(monitor, "TRACK_SONGS", False)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monkeypatch.setattr(monitor, "get_track_info", lambda *a, **k: (0, None, ""))
    monkeypatch.setattr(monitor, "get_spotify_apple_genius_search_urls", lambda *a, **k: tuple([""] * 13))
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *a, **k: (False, False))

    deadline = clock.now + horizon
    plain_sleep = clock.sleep

    def stopping_sleep(seconds):
        plain_sleep(seconds)
        if clock.now > deadline:
            raise KeyboardInterrupt

    clock.sleep = stopping_sleep

    capsys.readouterr()
    with pytest.raises((KeyboardInterrupt, SystemExit)):
        monitor.lastfm_monitor_user(user, network, "someuser", [], "")
    return capsys.readouterr().out, clock


# Returns the timestamp each banner printed, read back from the transcript
def banner_seconds(transcript):
    stamps = []
    for line in transcript.splitlines():
        if line.startswith("Liveness check, timestamp:"):
            stamps.append(line.split("\t", 1)[1])
    return stamps


class TestTheBannerItself:
    # A message and its timestamp printed by separate calls is how the two drifted into different modes
    def test_the_sentence_and_its_timestamp_come_from_one_call(self, capsys):
        monitor.print_liveness_banner("Monitoring healthy for someuser. The user is inactive")
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "* Monitoring healthy for someuser. The user is inactive"
        assert lines[1].startswith("Liveness check, timestamp:")

    # Nothing else in a plain run explains what a bare timestamp line is
    def test_a_plain_run_still_gets_the_sentence(self, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "DEBUG_MODE", False)
        monitor.print_liveness_banner("Monitoring healthy for someuser")
        assert "* Monitoring healthy for someuser" in capsys.readouterr().out

    def test_what_it_interpolates_is_sanitized(self, monkeypatch, capsys):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "lastfmapikey00000000000000000000")
        monitor.print_liveness_banner("Monitoring healthy for lastfmapikey00000000000000000000")
        assert "lastfmapikey00000000000000000000" not in capsys.readouterr().out


class TestTheCadenceIsMeasuredInSeconds:
    def test_the_reminder_is_the_interval_itself(self):
        assert monitor.LIVENESS_REMINDER_SECONDS == monitor.LIVENESS_CHECK_INTERVAL

    # A cadence derived from the poll interval drifts as soon as the run polls at a different one
    def test_nothing_divides_the_interval_by_a_poll_interval(self):
        assert "LIVENESS_CHECK_COUNTER" not in SOURCE
        assert not re.search(r"LIVENESS_CHECK_INTERVAL\s*(?://|/)\s*", SOURCE)

    # An interval a config file switched off has to leave the reminder off too
    @pytest.mark.parametrize("interval, expected", [(300, 300), (0, 0), (-1, 0)])
    def test_the_configured_interval_is_what_the_loop_reminds_on(self, restored_globals, tmp_path, capsys, interval, expected):
        settled = run_main_to_the_loop(tmp_path, f"LIVENESS_CHECK_INTERVAL = {interval}\n")
        capsys.readouterr()
        assert settled["LIVENESS_REMINDER_SECONDS"] == expected

    # The reminder used to be derived only when the poll interval was overridden on the command line
    def test_a_config_file_alone_settles_the_reminder(self, restored_globals, tmp_path, capsys):
        settled = run_main_to_the_loop(tmp_path, "LIVENESS_CHECK_INTERVAL = 300\n")
        capsys.readouterr()
        assert settled["LIVENESS_REMINDER_SECONDS"] == settled["LIVENESS_CHECK_INTERVAL"] == 300


class TestTheCadenceThroughTheRealLoop:
    # The setting names seconds, so an inactive run reminds once per interval no matter how often it polls
    def test_an_inactive_run_reminds_once_per_interval(self, monkeypatch, capsys, tmp_path):
        transcript, clock = drive_loop(monkeypatch, capsys, tmp_path, lambda now: None, horizon=86400)
        assert len(clock.slept) > 2000, "the run was too short to show a cadence"
        assert transcript.count("* Monitoring healthy for someuser. The user is inactive") == 24

    # An active target is polled on the shorter interval, which is where a counted cadence drifts
    def test_an_active_run_reminds_on_the_same_wall_clock_cadence(self, monkeypatch, capsys, tmp_path):
        transcript, clock = drive_loop(monkeypatch, capsys, tmp_path, lambda now: FakeTrack(), horizon=86400)
        assert set(clock.slept) == {10}, "the active run did not poll on the active interval"
        assert transcript.count("* Monitoring healthy for someuser. The user is active") == 24

    # A target that stays online for a week is exactly when a silent run looks dead
    def test_an_active_run_is_not_left_silent(self, monkeypatch, capsys, tmp_path):
        transcript, _ = drive_loop(monkeypatch, capsys, tmp_path, lambda now: FakeTrack(), horizon=7200)
        assert "Liveness check, timestamp:" in transcript

    def test_switching_the_banner_off_prints_nothing(self, monkeypatch, capsys, tmp_path):
        transcript, _ = drive_loop(monkeypatch, capsys, tmp_path, lambda now: None, horizon=86400, liveness=0)
        assert "Liveness check, timestamp:" not in transcript

    # Something the run printed is itself the evidence it is alive, so the quiet period starts again
    def test_a_printed_event_restarts_the_quiet_period(self, monkeypatch, capsys, tmp_path):
        start = FakeClock().now
        changed_at = start + 1800

        def scrobbles(now):
            return (start - 600, FakeTrack()) if now < changed_at else (changed_at, FakeTrack("Artist", "Second"))

        transcript, _ = drive_loop(monkeypatch, capsys, tmp_path, lambda now: None, horizon=7200, scrobbles=scrobbles)
        assert "*** New last.fm entries showed up while user was offline!" in transcript
        assert len(banner_seconds(transcript)) == 1, "the event did not restart the quiet period"

    def test_the_same_run_without_the_event_reminds_twice(self, monkeypatch, capsys, tmp_path):
        transcript, _ = drive_loop(monkeypatch, capsys, tmp_path, lambda now: None, horizon=7200)
        assert len(banner_seconds(transcript)) == 2


class TestWhereTheCallSiteSits:
    # Inside the offline branch the banner never fires for a target who keeps listening
    def test_the_call_site_is_not_nested_in_the_offline_branch(self):
        tree = ast.parse(SOURCE)
        loop = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "lastfm_monitor_user")
        calls = [node for node in ast.walk(loop) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print_liveness_banner"]
        assert len(calls) == 1, f"expected one banner call site, found {len(calls)}"
        gates = [node.test for node in ast.walk(loop) if isinstance(node, ast.If) and any(call in ast.walk(node) for call in calls)]
        assert not any("lf_user_online" in ast.dump(gate) for gate in gates), "the banner is gated on the target's state"

    def test_the_reminder_is_not_conditional_on_a_flag(self):
        settled = SOURCE.index("    LIVENESS_REMINDER_SECONDS = LIVENESS_CHECK_INTERVAL if LIVENESS_CHECK_INTERVAL > 0 else 0")
        line_start = SOURCE.rindex("\n", 0, settled)
        preceding = SOURCE[:line_start].rsplit("\n", 3)[-3:]
        assert not any(line.strip().startswith("if ") for line in preceding), f"the reminder is settled inside a branch: {preceding}"
