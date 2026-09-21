"""Tests for the HTML notification body, its Discord markdown form and its match with the plain text."""

import difflib
import html as html_module
import json
import os
import re
from pathlib import Path

import pytest

import lastfm_monitor as monitor

USERNAME = "someuser"


# Ends a bounded monitoring run once the scripted timeline is exhausted
class EndOfTimeline(BaseException):
    pass


# Reduces one HTML body back to the text it represents, independently of the module's own converter
def html_to_text(body_html):
    text = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or ""))
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    return html_module.unescape(text)


# Replaces every anchor with its destination, which is what the plain body prints on a service URL line
def links_as_destinations(line):
    return re.sub(r'(?is)<a\s[^>]*?href="([^"]*)"[^>]*>.*?</a>', r"\1", line)


# Reports whether one HTML line says what its plain counterpart says, whether it links a name or a bare URL
def line_agrees(plain_line, html_line):
    return plain_line in (html_to_text(html_line), html_to_text(links_as_destinations(html_line)))


# Reports whether one Discord line says what its plain counterpart says, whether it links a name or a bare URL
def discord_line_agrees(plain_line, discord_line):
    bare = discord_line.replace("**", "").replace("*", "")
    return plain_line in (re.sub(r"\[([^\]]*)\]\(([^)]*)\)", r"\1", bare), re.sub(r"\[([^\]]*)\]\(([^)]*)\)", r"\2", bare))


# Reports whether one paragraph lists music service links, which the HTML body shapes differently on purpose:
# it labels each link with the track name and folds the album URL into the album line above
def is_service_url_paragraph(paragraph):
    return "URL: " in paragraph


# Returns what differs between one plain paragraph and its HTML counterpart, empty when they say the same thing
def paragraph_diff(plain, rendered):
    if is_service_url_paragraph(plain):
        return ""
    plain_lines = plain.split("\n")
    html_lines = rendered.split("<br>")
    if len(plain_lines) == len(html_lines) and all(line_agrees(line, html_line) for line, html_line in zip(plain_lines, html_lines)):
        return ""
    return "\n".join(difflib.unified_diff(plain_lines, [html_to_text(line) for line in html_lines], fromfile="plain", tofile="html-reduced", lineterm=""))


# Returns what differs between the plain body and the HTML body, empty when their paragraphs and blank lines match
def structural_diff(body, body_html):
    plain_paragraphs = body.split("\n\n")
    html_paragraphs = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or "")).split("<br><br>")
    if len(plain_paragraphs) != len(html_paragraphs):
        return f"plain has {len(plain_paragraphs)} paragraphs, HTML has {len(html_paragraphs)}"
    return "\n".join(diff for diff in (paragraph_diff(*pair) for pair in zip(plain_paragraphs, html_paragraphs)) if diff)


# Advances only when the monitoring loop waits, so every alert is produced against a known time
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


# Serves one scripted timeline, so the loop walks from silence through two songs, an idle spell and a
# scrobble that only shows up in the history. A SCROBBLED entry records a play without reporting one live
SCROBBLED = "scrobbled while offline"


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
        if entry == SCROBBLED:
            self.scrobbles.append(FakePlayed(self.clock.now, FakeTrack("Offline Artist", "Offline Track")))
            return None
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


# The now-playing timeline the alerts are captured from, one entry per check
TIMELINE = [None, FakeTrack("First Artist", "First Track"), FakeTrack("Second Artist", "Second Track"), None, None, None, None, SCROBBLED, None]


@pytest.fixture
# Collects every alert the monitoring loop tries to send, without delivering any of them
def captured_alerts(monkeypatch):
    captured = []

    def fake_send(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None, **kwargs):
        captured.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html, "webhook_body": kwargs.get("webhook_body") or body, "discord": monitor.html_body_to_discord_markdown(kwargs.get("webhook_body_html") or body_html)})
        return True, True

    monkeypatch.setattr(monitor, "send_notification_channels", fake_send)
    return captured


@pytest.fixture
# Every alert the scripted timeline produces, driven through the real monitoring loop on a fake clock
def timeline_alerts(monkeypatch, tmp_path, captured_alerts, capsys):
    clock = FakeClock()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "time", clock)
    monkeypatch.setattr(monitor, "LASTFM_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "LASTFM_ACTIVE_CHECK_INTERVAL", 10)
    monkeypatch.setattr(monitor, "LASTFM_INACTIVITY_CHECK", 20)
    monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", 0)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 0)
    monkeypatch.setattr(monitor, "TRACK_FOLLOWERS", False)
    monkeypatch.setattr(monitor, "TRACK_FOLLOWINGS", False)
    monkeypatch.setattr(monitor, "TRACK_BIO", False)
    monkeypatch.setattr(monitor, "TRACK_DISPLAY_NAME", False)
    monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", False)
    monkeypatch.setattr(monitor, "PROGRESS_INDICATOR", False)
    monkeypatch.setattr(monitor, "TRACK_SONGS", False)
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "SONG_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "OFFLINE_ENTRIES_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "get_track_info", lambda *args, **kwargs: (0, None, ""))
    monkeypatch.setattr(monitor, "get_spotify_apple_genius_search_urls", lambda *args, **kwargs: tuple(f"https://example.test/service{index}" for index in range(13)))
    user = ScriptedUser(clock, TIMELINE)
    capsys.readouterr()
    with pytest.raises(EndOfTimeline):
        monitor.lastfm_monitor_user(user, FakeNetwork(user), USERNAME, [], "")
    capsys.readouterr()
    return captured_alerts


# Verifies a value taken from Last.fm is escaped before it reaches the HTML body
def test_untrusted_text_is_escaped():
    assert monitor.html_text("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert monitor.html_text("line\nbreak") == "line<br>break"
    assert monitor.escape_html_attr('" onload="x') == "&quot; onload=&quot;x"


# Verifies a bare URL in an alert becomes a link while one already inside an attribute is left alone
def test_bare_urls_are_linked_once():
    assert monitor.html_autolink_urls("Guide: https://example.test/a") == 'Guide: <a href="https://example.test/a">https://example.test/a</a>'
    assert monitor.html_autolink_urls('<a href="https://example.test/a">x</a>') == '<a href="https://example.test/a">x</a>'


# Verifies the Discord body carries the email's emphasis and links instead of raw markup
def test_discord_markdown_mirrors_the_html_body():
    body_html = monitor.html_email_body('Track: <b>Artist - Track</b><br><br>Guide: <a href="https://example.test/a">docs</a>')

    assert monitor.html_body_to_discord_markdown(body_html) == "Track: **Artist - Track**\n\nGuide: [docs](https://example.test/a)"


# Verifies the failure alert bolds its summary and the two values that say how bad the outage is
def test_the_failure_alert_bolds_its_summary_and_outage_fields(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    advice = monitor.make_recovery_advice("lastfm.unavailable", "Last.fm is unreachable", "Retry later", True)

    rendered = monitor.recovery_alert_body_html(advice, 60, failed_checks=2, failing_since=1700000000)

    assert rendered.startswith("<html><head></head><body><b>Last.fm is unreachable</b><br><br>")
    assert "Failed checks in a row: <b>2</b>" in rendered
    assert "Failing since: <b>" in rendered
    # The retry delay is configured rather than observed, so it carries no emphasis
    assert "Next retry in: 1 minute" in rendered
    assert rendered.endswith("</body></html>")


# Verifies the timeline reaches several alert types, so the structural check is not silently narrow
def test_the_timeline_covers_several_alert_types(timeline_alerts):
    assert {"active", "song", "inactive", "offline_entries"} <= {alert["type"] for alert in timeline_alerts}


# Verifies every alert carries an HTML body next to its plain one
def test_every_alert_has_an_html_body(timeline_alerts):
    assert [alert["subject"] for alert in timeline_alerts if not alert["body_html"]] == []


# Verifies each HTML body reduces back to its plain body, so no line break was added or lost
def test_html_bodies_match_the_plain_text(timeline_alerts):
    mismatches = [f"{alert['type']}: {alert['subject']}\n{structural_diff(alert['body'], alert['body_html'])}" for alert in timeline_alerts if structural_diff(alert["body"], alert["body_html"])]

    assert mismatches == []


# Verifies every HTML body is one complete document, so no fragment reaches a mail client unwrapped
def test_html_bodies_are_complete_documents(timeline_alerts):
    for alert in timeline_alerts:
        assert alert["body_html"].startswith("<html><head></head><body>")
        assert alert["body_html"].endswith("</body></html>")


# Verifies the Discord body keeps the wording the ntfy body carries once its markers are removed
def test_discord_bodies_keep_the_plain_wording(timeline_alerts):
    for alert in timeline_alerts:
        plain_paragraphs = alert["webhook_body"].strip().split("\n\n")
        discord_paragraphs = alert["discord"].split("\n\n")

        assert len(plain_paragraphs) == len(discord_paragraphs)
        for plain, rendered in zip(plain_paragraphs, discord_paragraphs):
            if is_service_url_paragraph(plain):
                continue
            assert all(discord_line_agrees(*pair) for pair in zip(plain.split("\n"), rendered.split("\n")))


# Verifies the track is the bold subject of every alert that names one
def test_alerts_bold_the_track_they_name(timeline_alerts):
    named = [alert for alert in timeline_alerts if alert["body"].startswith("Track: ")]

    assert named
    for alert in named:
        assert "Track: <b>" in alert["body_html"]


# Writes the captured alerts as JSON when PREVIEW_ALERTS_JSON names a destination, so a preview tool can render them
@pytest.mark.skipif(not os.environ.get("PREVIEW_ALERTS_JSON"), reason="set PREVIEW_ALERTS_JSON to dump the alerts")
def test_dump_the_alerts_for_a_preview(timeline_alerts):
    Path(os.environ["PREVIEW_ALERTS_JSON"]).write_text(json.dumps(timeline_alerts, indent=2), encoding="utf-8")
