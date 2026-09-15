"""Credential validation and saved-state regressions through real HTTP clients."""

import errno
import json
import time

import pytest
import requests
from requests.adapters import HTTPAdapter
from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler

import lastfm_monitor as monitor


@pytest.mark.parametrize("surface", ["doctor", "wizard"])
@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("accepted", [False, True])
# Requires a live credential check while leaving file and shared memory caches untouched
def test_spotify_validation_ignores_caches(monkeypatch, tmp_path, capsys, surface, cached, accepted):
    cache = tmp_path / "oauth.json"
    old = {"access_token": "old-app-token", "expires_at": int(time.time()) + 3600, "token_type": "Bearer"}
    if cached:
        CacheFileHandler(cache_path=str(cache)).save_token_to_cache(old)
    previous = cache.read_bytes() if cached else None
    memory = MemoryCacheHandler(token_info=old)
    monkeypatch.setattr(monitor, "SP_TOKENS_FILE", str(cache))
    monkeypatch.setattr(monitor, "SP_OAUTH_MEMORY_CACHE_HANDLER", memory)
    monkeypatch.setattr(monitor, "SP_CLIENT_ID", "candidate-app-id" if surface == "doctor" else "old-client-id")
    monkeypatch.setattr(monitor, "SP_CLIENT_SECRET", "candidate-app-secret" if surface == "doctor" else "old-client-secret")
    monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", True)
    attempts = []

    # Rejects the candidate at Spotify's actual token endpoint
    def respond(adapter, request, **kwargs):
        attempts.append(request)
        response = requests.Response()
        response.request = request
        response.status_code = 200 if accepted else 400
        payload = {"access_token": "new-token", "expires_in": 3600, "token_type": "Bearer"} if accepted else {"error": "invalid_client", "error_description": "Rejected candidate-app-id candidate-app-secret"}
        response._content = json.dumps(payload).encode()
        return response

    monkeypatch.setattr(HTTPAdapter, "send", respond)
    if surface == "doctor":
        checks = monitor.doctor_check_spotify_metadata(monitor.DoctorReport())
        assert checks[0].status == ("PASS" if accepted else "WARN")
    else:
        state = monitor.WizardSetupState(tmp_path / "config", tmp_path / "env", monitor._config_template_defaults())
        answers = iter(["y", "y", "n", "y", "" if accepted else "y"])
        secrets = iter(["candidate-app-id", "candidate-app-secret"])
        monitor._wizard_collect_spotify_section(state, input_func=lambda _: next(answers), getpass_func=lambda _: next(secrets))
        assert ("SP_CLIENT_SECRET" in state.secret_updates) is accepted
    assert len(attempts) == 1
    assert attempts[0].url == "https://accounts.spotify.com/api/token"
    assert (cache.read_bytes() if cache.exists() else None) == previous
    assert memory.get_cached_token() == old
    output = capsys.readouterr()
    assert "candidate-app-secret" not in output.out + output.err
    assert "candidate-app-id" not in output.out + output.err


# Redacts unsaved Last.fm values while retaining the provider's typed error classification
def test_lastfm_candidate_redaction(monkeypatch):
    http = vars(monitor.pylast)["httpx"]
    requests_seen = []

    # Returns the provider's XML error through pylast's actual HTTP transport
    def respond(transport, request):
        requests_seen.append(request)
        return http.Response(200, request=request, text='<lfm status="failed"><error code="10">Rejected candidate-key candidate-secret</error></lfm>')

    monkeypatch.setattr(http.HTTPTransport, "handle_request", respond)
    advice = monitor._wizard_verify_lastfm_credentials("candidate-key", "candidate-secret")
    assert advice is not None
    assert advice.code == "auth.api_key_invalid"
    assert "candidate-key" not in str(advice)
    assert "candidate-secret" not in str(advice)
    assert len(requests_seen) == 1


@pytest.mark.parametrize("users", ["alice", 17, ["alice", 17], {"alice": True}, [""]])
# Rebuilds malformed friends data without reporting spurious additions or removals
def test_invalid_friends_state_rebuilds_quietly(monkeypatch, tmp_path, capsys, users):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "lastfm_reviewuser_followings.json"
    path.write_text(json.dumps({"users": users}), encoding="utf-8")
    attempts = []

    # Supplies a complete real Last.fm following page to the scraper
    def respond(adapter, request, **kwargs):
        attempts.append(request)
        response = requests.Response()
        response.request = request
        response.status_code = 200
        response._content = b'<html><h1>Following (1)</h1><ul class="user-list"><li class="user-list-item"><a href="/user/alice">alice</a></li></ul></html>'
        return response

    monkeypatch.setattr(HTTPAdapter, "send", respond)
    changes, states = monitor.check_friends_changes("reviewuser", True, False)
    assert changes == {}
    assert states == {"followings": {"alice"}}
    assert json.loads(path.read_text())["users"] == ["alice"]
    assert len(attempts) == 1
    output = capsys.readouterr().out
    assert "lastfm_reviewuser_followings.json" in output
    assert "rebuild" in output


@pytest.mark.parametrize("record", [["alice"], {"users": ["alice"], "count": -1, "note": "kept by user"}])
# Retains released list records and ignores count metadata that comparisons do not consume
def test_friends_legacy_records(monkeypatch, tmp_path, record):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "lastfm_reviewuser_followings.json").write_text(json.dumps(record), encoding="utf-8")
    assert monitor.load_friends_state("reviewuser", "followings") == {"alice"}


@pytest.mark.parametrize("surface", ["friends", "spotify", "doctor"])
# Stops after the first descriptor failure instead of retrying or trying another metadata backend
def test_resource_failure_stops_optional_requests(monkeypatch, surface):
    attempts = []
    monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", True)
    monkeypatch.setattr(monitor, "SP_CLIENT_ID", "test-client")
    monkeypatch.setattr(monitor, "SP_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(monitor, "SP_TOKENS_FILE", "")
    monkeypatch.setattr(monitor, "SP_OAUTH_MEMORY_CACHE_HANDLER", None)

    # Supplies a token then raises a real chained local socket failure
    def respond(adapter, request, **kwargs):
        attempts.append(request.url)
        if surface != "doctor" and request.url == "https://accounts.spotify.com/api/token":
            response = requests.Response()
            response.request = request
            response.status_code = 200
            response._content = b'{"access_token":"test-token","expires_in":3600,"token_type":"Bearer"}'
            return response
        raise requests.ConnectionError("Socket allocation failed") from OSError(errno.EMFILE, "Too many open files")

    monkeypatch.setattr(HTTPAdapter, "send", respond)
    with pytest.raises(SystemExit) as error:
        if surface == "friends":
            monitor._lastfm_http_get_with_retry("https://www.last.fm/user/reviewuser/following")
        elif surface == "doctor":
            monitor.doctor_check_spotify_metadata(monitor.DoctorReport())
        else:
            monitor.spotify_resolve_track_metadata("Artist", "Track", "Album")
    assert error.value.code == 1
    assert len(attempts) == (2 if surface == "spotify" else 1)
