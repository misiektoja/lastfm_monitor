import re

import pytest

import lastfm_monitor as monitor


# Captures the notification payloads generated for one set of friends changes
def capture_notifications(monkeypatch, changes):
    captured = []

    def fake_send(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None, subject_short="", body_short=""):
        captured.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html})
        return True, True

    monkeypatch.setattr(monitor, "send_notification_channels", fake_send)
    monkeypatch.setattr(monitor, "FOLLOWINGS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "FOLLOWERS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "PROFILE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "FRIENDS_CHECK_INTERVAL", 10800)
    monitor.notify_friends_changes("NeonCipher", changes)
    return {entry["type"]: entry for entry in captured}


# Converts an HTML notification body to plain lines the way a mail client renders it
def render_html(body_html):
    text = body_html.replace("<br>", "\n")
    text = re.sub(r"<[^>]+>", "", text)
    return text.splitlines()


# Builds a single friends change entry
def make_change(added, removed, previous_count, current_count):
    return {"added": added, "removed": removed, "current_count": current_count, "previous_count": previous_count}


@pytest.mark.parametrize("event,label", [("followings", "followings"), ("followers", "followers")])
def test_added_users_each_get_their_own_html_line(monkeypatch, event, label):
    changes = {event: make_change(["Angie_Sullivan", "HakikazuHatsu"], [], 1, 3)}
    notifications = capture_notifications(monkeypatch, changes)

    lines = render_html(notifications[event]["body_html"])
    assert f"Added {label}:" in lines
    assert lines.count("- Angie_Sullivan") == 1
    assert lines.count("- HakikazuHatsu") == 1
    assert "- Angie_Sullivan- HakikazuHatsu" not in "\n".join(lines)


@pytest.mark.parametrize("event", ["followings", "followers"])
def test_added_users_each_get_their_own_plain_text_line(monkeypatch, event):
    changes = {event: make_change(["Angie_Sullivan", "HakikazuHatsu"], [], 1, 3)}
    notifications = capture_notifications(monkeypatch, changes)

    lines = notifications[event]["body"].splitlines()
    assert "- Angie_Sullivan" in lines
    assert "- HakikazuHatsu" in lines


@pytest.mark.parametrize("event,label", [("followings", "followings"), ("followers", "followers")])
def test_html_body_matches_plain_text_layout(monkeypatch, event, label):
    changes = {event: make_change(["Angie_Sullivan"], ["OldFan", "GoneUser"], 5, 4)}
    notifications = capture_notifications(monkeypatch, changes)

    notification = notifications[event]
    assert render_html(notification["body_html"]) == notification["body"].splitlines()

    lines = notification["body"].splitlines()
    assert lines.index(f"Added {label}:") < lines.index(f"Removed {label}:")
    assert lines.count("") == 5


@pytest.mark.parametrize("event,label", [("followings", "followings"), ("followers", "followers")])
def test_removed_only_change_keeps_one_user_per_line(monkeypatch, event, label):
    changes = {event: make_change([], ["OldFan", "GoneUser"], 3, 1)}
    notifications = capture_notifications(monkeypatch, changes)

    notification = notifications[event]
    assert render_html(notification["body_html"]) == notification["body"].splitlines()
    assert f"Added {label}:" not in notification["body"]


@pytest.mark.parametrize("event", ["followings", "followers"])
def test_html_links_to_each_changed_user_profile(monkeypatch, event):
    changes = {event: make_change(["Angie Sullivan"], ["OldFan"], 2, 2)}
    notifications = capture_notifications(monkeypatch, changes)

    body_html = notifications[event]["body_html"]
    assert '<a href="https://www.last.fm/user/Angie+Sullivan">Angie Sullivan</a><br>' in body_html
    assert '<a href="https://www.last.fm/user/OldFan">OldFan</a><br>' in body_html


# Verifies one profile alert reports both old and new values without treating bio markup as HTML
def test_profile_notification_reports_display_name_and_bio_safely(monkeypatch):
    changes = {"profile": {"display_name": {"previous": "Old Name", "current": "New Name"}, "bio": {"previous": "Old bio", "current": "New <b>bio</b>\nSecond line"}}}
    notifications = capture_notifications(monkeypatch, changes)

    notification = notifications["profile"]
    assert "Display name changed:\nPrevious: Old Name\nCurrent: New Name" in notification["body"]
    assert "Bio changed:\nPrevious: Old bio\nCurrent: New <b>bio</b>\nSecond line" in notification["body"]
    assert "New &lt;b&gt;bio&lt;/b&gt;<br>Second line" in notification["body_html"]
