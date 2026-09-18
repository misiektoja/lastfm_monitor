"""Checks OAuth search recovery without making Spotify requests."""

from email.utils import formatdate
from unittest.mock import Mock

import pytest
import requests

import lastfm_monitor as monitor


# Returns a real HTTP response so status and Retry-After handling use requests semantics
def response(status, retry_after=""):
    result = requests.Response()
    result.status_code = status
    result.url = monitor.SPOTIFY_OAUTH_SEARCH_URL
    result._content = b'{"tracks":{"items":[]}}'
    if retry_after:
        result.headers["Retry-After"] = retry_after
    return result


@pytest.fixture
# Isolates app cooldowns and provides a controllable clock and web fallback
def backend(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(monitor.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(monitor, "SP_CLIENT_ID", "test-client")
    monkeypatch.setattr(monitor, "SP_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(monitor, "SP_OAUTH_SEARCH_COOLDOWNS", {})
    token = Mock(side_effect=["first-token", "fresh-token", "later-token"])
    web = Mock(return_value=("web-track", 123))
    monkeypatch.setattr(monitor, "spotify_get_access_token", token)
    monkeypatch.setattr(monitor, "spotify_search_song_trackid_duration", web)
    return now, token, web


@pytest.mark.parametrize("status", [401, 403, 429, 500])
# Stops changing query text after the endpoint rejects a request
def test_http_failure_stops_search_strategies(monkeypatch, status):
    get = Mock(return_value=response(status, "48"))
    monkeypatch.setattr(monitor.req, "get", get)
    with pytest.raises(requests.HTTPError):
        monitor.spotify_search_song_trackid_duration_oauth("token", "Artist", "Track", "Album")
    assert get.call_count == 1


# Refreshes a rejected token once and retains the successful OAuth result
def test_401_refreshes_once_before_success(monkeypatch, backend):
    _now, token, web = backend
    get = Mock(side_effect=[response(401), response(200)])
    monkeypatch.setattr(monitor.req, "get", get)
    monkeypatch.setattr(monitor, "spotify_search_process_track_items", lambda *_args, **_kwargs: ("oauth-track", 100))
    assert monitor.spotify_resolve_track_metadata("Artist", "Track", "Album") == ("oauth-track", 100)
    assert [call.kwargs["headers"]["Authorization"] for call in get.call_args_list] == ["Bearer first-token", "Bearer fresh-token"]
    assert token.call_args_list[0].kwargs == {}
    assert token.call_args_list[1].kwargs == {"force_refresh": True}
    web.assert_not_called()


# Repeated authorization failure falls back once and pauses subsequent app searches
def test_second_401_enters_cooldown(monkeypatch, backend):
    _now, token, web = backend
    get = Mock(return_value=response(401))
    monkeypatch.setattr(monitor.req, "get", get)
    for track in ("One", "Two"):
        assert monitor.spotify_resolve_track_metadata("Artist", track, "Album") == ("web-track", 123)
    assert get.call_count == token.call_count == 2
    assert web.call_count == 2


@pytest.mark.parametrize("status,delay", [(403, 300), (429, 1200)])
# Keeps the app idle until its permission recheck or full server cooldown expires
def test_app_cooldown_survives_track_changes(monkeypatch, backend, status, delay):
    now, token, web = backend
    get = Mock(return_value=response(status, str(delay)))
    monkeypatch.setattr(monitor.req, "get", get)
    monitor.spotify_resolve_track_metadata("Artist", "One", "Album")
    now[0] += delay - 1
    monitor.spotify_resolve_track_metadata("Artist", "Two", "Album")
    assert get.call_count == token.call_count == 1
    assert web.call_count == 2
    now[0] += 1
    get.return_value = response(200)
    monkeypatch.setattr(monitor, "spotify_search_process_track_items", lambda *_args, **_kwargs: ("oauth-track", 100))
    assert monitor.spotify_resolve_track_metadata("Artist", "Three", "Album") == ("oauth-track", 100)
    assert get.call_count == 2
    assert monitor.SP_CLIENT_ID not in monitor.SP_OAUTH_SEARCH_COOLDOWNS


# A different app can search while the original app retains its cooldown
def test_cooldown_is_bound_to_app(monkeypatch, backend):
    _now, _token, _web = backend
    get = Mock(return_value=response(429, "120"))
    monkeypatch.setattr(monitor.req, "get", get)
    monitor.spotify_resolve_track_metadata("Artist", "One")
    monkeypatch.setattr(monitor, "SP_CLIENT_SECRET", "rotated-secret")
    monitor.spotify_resolve_track_metadata("Artist", "Two")
    assert get.call_count == 1
    monkeypatch.setattr(monitor, "SP_CLIENT_ID", "second-client")
    monitor.spotify_resolve_track_metadata("Artist", "Three")
    assert get.call_count == 2


@pytest.mark.parametrize("header,expected", [("nonsense", 60), ("nan", 60), ("inf", 60), ("-5", 1), ("0", 1)])
# Bounds unusable Retry-After values without a busy retry loop
def test_invalid_retry_after_defaults(header, expected):
    assert monitor.spotify_oauth_search_cooldown(response(429, header)) == expected


# Supports an HTTP date without truncating a long server-requested cooldown
def test_http_date_retry_after(monkeypatch):
    monkeypatch.setattr(monitor.time, "time", lambda: 1_800_000_000)
    assert monitor.spotify_oauth_search_cooldown(response(429, formatdate(1_800_001_200, usegmt=True))) == 1200


# Explicit recovery bypasses the cached rejected token and still updates Spotipy's cache
def test_force_refresh_bypasses_spotipy_cache(monkeypatch):
    manager = Mock()
    manager.get_access_token.return_value = "fresh"
    monkeypatch.setattr("spotipy.oauth2.SpotifyClientCredentials", Mock(return_value=manager))
    monkeypatch.setattr(monitor, "SP_TOKENS_FILE", "")
    monkeypatch.setattr(monitor, "SP_OAUTH_MEMORY_CACHE_HANDLER", None)
    assert monitor.spotify_get_access_token("client", "secret", force_refresh=True) == "fresh"
    manager.get_access_token.assert_called_once_with(as_dict=False, check_cache=False)
