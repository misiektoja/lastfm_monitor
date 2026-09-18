import json

import lastfm_monitor as monitor


# Verifies the first profile check creates a baseline without reporting the current values as changes
def test_initial_profile_check_creates_silent_baseline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "lastfm_get_profile", lambda username: {"display_name": "Neon Cipher", "bio": "Initial bio"})

    changes, current_states = monitor.check_friends_changes("NeonCipher", False, False, True, True)

    assert changes == {}
    assert current_states == {"profile": {"display_name": "Neon Cipher", "bio": "Initial bio"}}
    state = json.loads((tmp_path / "lastfm_NeonCipher_profile.json").read_text(encoding="utf-8"))
    assert state["display_name"] == "Neon Cipher"
    assert state["bio"] == "Initial bio"


# Verifies bio and display-name differences use the same pending state contract as friend changes
def test_profile_changes_return_exact_current_state_without_early_persistence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monitor.save_profile_state("NeonCipher", {"display_name": "Old Name", "bio": "Old bio"})
    monkeypatch.setattr(monitor, "lastfm_get_profile", lambda username: {"display_name": "New Name", "bio": "New bio"})

    changes, current_states = monitor.check_friends_changes("NeonCipher", False, False, True, True, save_state=False, raise_on_error=True)

    assert changes == {"profile": {"display_name": {"previous": "Old Name", "current": "New Name"}, "bio": {"previous": "Old bio", "current": "New bio"}}}
    assert current_states == {"profile": {"display_name": "New Name", "bio": "New bio"}}
    assert monitor.load_profile_state("NeonCipher") == {"display_name": "Old Name", "bio": "Old bio"}


# Verifies disabled profile fields are neither compared nor discarded from the saved baseline
def test_profile_fields_are_independently_controlled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monitor.save_profile_state("NeonCipher", {"display_name": "Old Name", "bio": "Old bio"})
    monkeypatch.setattr(monitor, "lastfm_get_profile", lambda username: {"display_name": "New Name", "bio": "New bio"})

    changes, current_states = monitor.check_friends_changes("NeonCipher", False, False, True, False, save_state=False, raise_on_error=True)
    monitor.save_friends_check_states("NeonCipher", current_states)

    assert changes == {"profile": {"bio": {"previous": "Old bio", "current": "New bio"}}}
    assert monitor.load_profile_state("NeonCipher") == {"display_name": "Old Name", "bio": "New bio"}
