"""Tests for the commands the monitoring loop sends to the local Spotify client when playback tracking is on."""

import pytest

import lastfm_monitor as monitor

USERNAME = "someuser"
TRACK_ID = "trackid0000000000000000"
FINISHING_TRACK_ID = "finishingtrack0000000000"


# Ends a bounded monitoring run once the scripted timeline is exhausted
class EndOfTimeline(BaseException):
    pass


# Advances only when the monitoring loop waits, so every check runs against a known time
class FakeClock:
    def __init__(self, start=1757000000):
        self.now = start

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += int(seconds)


# Stands in for one Last.fm track, carrying the fields the loop reads from it
class FakeTrack:
    def __init__(self, artist="Artist", title="Track", album="Album"):
        self.artist = artist
        self.title = title
        self.info = {"album": album}

    def __eq__(self, other):
        return isinstance(other, FakeTrack) and (self.artist, self.title) == (other.artist, other.title)

    def __hash__(self):
        return hash((self.artist, self.title))

    def __str__(self):
        return f"{self.artist} - {self.title}"


# Stands in for one scrobble in the recent tracks list
class FakePlayed:
    def __init__(self, timestamp, track, album="Album"):
        self.timestamp = timestamp
        self.track = track
        self.album = album


# Serves one now-playing entry per check and records each reported track as a scrobble
class ScriptedUser:
    def __init__(self, clock, timeline):
        self.clock = clock
        self.timeline = timeline
        self.index = 0
        self.scrobbles = [FakePlayed(clock.now - 600, FakeTrack("Older Artist", "Older Track"))]

    def get_now_playing(self):
        if self.index >= len(self.timeline):
            raise EndOfTimeline()
        entry = self.timeline[self.index]
        self.index += 1
        if entry is not None:
            self.scrobbles.append(FakePlayed(self.clock.now, entry))
        return entry

    def get_recent_tracks(self, limit=1):
        return list(reversed(self.scrobbles))[:limit]


# Stands in for the Last.fm network, which the loop only asks for the monitored user
class FakeNetwork:
    def __init__(self, user):
        self.user = user

    def get_user(self, username):
        return self.user


# One song followed by silence that outlasts both the break timer (40s) and the inactivity timer (120s)
TIMELINE = [None, FakeTrack("First Artist", "First Track")] + [None] * 16


@pytest.fixture
# Runs the real monitoring loop on a fake clock as macOS and returns every Spotify command it sent plus its output
def run_playback(monkeypatch, tmp_path, capsys):
    def run(break_multiplier=4, finishing_track_id=""):
        clock = FakeClock()
        commands = []
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(monitor, "time", clock)
        monkeypatch.setattr(monitor.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(monitor, "LASTFM_CHECK_INTERVAL", 30)
        monkeypatch.setattr(monitor, "LASTFM_ACTIVE_CHECK_INTERVAL", 10)
        monkeypatch.setattr(monitor, "LASTFM_INACTIVITY_CHECK", 120)
        monkeypatch.setattr(monitor, "LASTFM_BREAK_CHECK_MULTIPLIER", break_multiplier)
        monkeypatch.setattr(monitor, "SP_USER_GOT_OFFLINE_TRACK_ID", finishing_track_id)
        monkeypatch.setattr(monitor, "SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE", 5)
        monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", 0)
        monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 0)
        monkeypatch.setattr(monitor, "TRACK_FOLLOWERS", False)
        monkeypatch.setattr(monitor, "TRACK_FOLLOWINGS", False)
        monkeypatch.setattr(monitor, "TRACK_BIO", False)
        monkeypatch.setattr(monitor, "TRACK_DISPLAY_NAME", False)
        monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", False)
        monkeypatch.setattr(monitor, "PROGRESS_INDICATOR", False)
        monkeypatch.setattr(monitor, "TRACK_SONGS", True)
        monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", False)
        monkeypatch.setattr(monitor, "INACTIVE_NOTIFICATION", False)
        monkeypatch.setattr(monitor, "SONG_NOTIFICATION", False)
        monkeypatch.setattr(monitor, "send_notification_channels", lambda *args, **kwargs: (False, False))
        monkeypatch.setattr(monitor, "get_track_info", lambda *args, **kwargs: (0, TRACK_ID, ""))
        monkeypatch.setattr(monitor, "get_spotify_apple_genius_search_urls", lambda *args, **kwargs: tuple(f"https://example.test/service{index}" for index in range(13)))
        monkeypatch.setattr(monitor, "spotify_macos_play_song", lambda track_id, *args, **kwargs: commands.append(("play track", track_id)))
        monkeypatch.setattr(monitor, "spotify_macos_play_pause", lambda action, *args, **kwargs: commands.append((action,)))
        user = ScriptedUser(clock, TIMELINE)
        capsys.readouterr()
        with pytest.raises(EndOfTimeline):
            monitor.lastfm_monitor_user(user, FakeNetwork(user), USERNAME, [], "")
        return commands, capsys.readouterr().out

    return run


# Verifies the client is paused once at the break and left alone when the user later becomes inactive,
# so music started locally after the break keeps playing
def test_inactivity_does_not_pause_again_after_a_break_pause(run_playback):
    commands, output = run_playback()

    assert "User PAUSED playing" in output
    assert "User got INACTIVE" in output
    assert commands == [("play track", TRACK_ID), ("pause",)]


# Verifies inactivity still pauses the client when break detection is off and nothing paused it earlier
def test_inactivity_pauses_when_break_detection_is_disabled(run_playback):
    commands, output = run_playback(break_multiplier=0)

    assert "User PAUSED playing" not in output
    assert "User got INACTIVE" in output
    assert commands == [("play track", TRACK_ID), ("pause",)]


# Verifies a configured finishing track still plays on inactivity after a break pause and is then paused
def test_finishing_track_still_plays_on_inactivity_after_a_break_pause(run_playback):
    commands, _ = run_playback(finishing_track_id=FINISHING_TRACK_ID)

    assert commands == [("play track", TRACK_ID), ("pause",), ("play track", FINISHING_TRACK_ID), ("pause",)]
