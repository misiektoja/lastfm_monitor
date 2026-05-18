import inspect
import os
import time
import unittest
from unittest.mock import Mock, call, patch

import requests

import lastfm_monitor as monitor


TRACK_ID = "4N1MFKjziFHH4IS3RYYUrU"
TRACK_URI = f"spotify:track:{TRACK_ID}"


class FakeResponse:
    # Stores a minimal requests-compatible response for backend tests
    def __init__(self, status_code=200, json_data=None, text="", headers=None, url="https://example.test"):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text
        self.headers = headers if headers is not None else {}
        self.url = url

    # Returns the configured JSON response body
    def json(self):
        return self._json_data

    # Raises an HTTP error for configured error status codes
    def raise_for_status(self):
        if self.status_code >= 400:
            response = requests.Response()
            response.status_code = self.status_code
            response.url = self.url
            raise requests.HTTPError(f"HTTP {self.status_code}", response=response)


# Returns representative current Pathfinder getTrack metadata
def web_track_fixture():
    return {"__typename": "Track", "uri": TRACK_URI, "name": "My Love", "duration": {"totalMilliseconds": 259933}, "sharingInfo": {"shareUrl": f"https://open.spotify.com/track/{TRACK_ID}?si=track"}, "firstArtist": {"items": [{"uri": "spotify:artist:1dgdvbogmctybPrGEcnYf6", "profile": {"name": "Route 94"}}]}, "otherArtists": {"items": []}, "albumOfTrack": {"uri": "spotify:album:4ZD1KnBqghtSAEyqrZAkU4", "name": "My Love", "sharingInfo": {"shareUrl": "https://open.spotify.com/album/4ZD1KnBqghtSAEyqrZAkU4?si=album"}}}


class SpotifyWebBackendTests(unittest.TestCase):
    # Resets shared Spotify backend state before each test
    def setUp(self):
        monitor.SP_CLIENT_ID = ""
        monitor.SP_CLIENT_SECRET = ""
        monitor.SP_TOKENS_FILE = ""
        monitor.SP_OAUTH_MEMORY_CACHE_HANDLER = None
        monitor.SP_CACHED_WEB_ACCESS_TOKEN = None
        monitor.SP_WEB_ACCESS_TOKEN_EXPIRES_AT = 0
        monitor.SP_CACHED_WEB_CLIENT_ID = ""
        monitor.SP_CACHED_TRACK_QUERY_HASH = ""
        monitor.SP_CACHED_SEARCH_QUERY_HASH = ""
        monitor.USE_TRACK_DURATION_FROM_SPOTIFY = False
        monitor.TRACK_SONGS = False
        monitor.DO_NOT_SHOW_DURATION_MARKS = False

    # Verifies the embedded v61 cipher generates the expected TOTP
    def test_generates_expected_v61_totp(self):
        self.assertEqual(monitor.SPOTIFY_TOTP_VERSION, 61)
        self.assertEqual(monitor.generate_totp().at(1700000000), "371599")

    # Verifies a configured TOTP override flows through to the generated token
    def test_totp_config_override_is_used(self):
        with patch.object(monitor, "SPOTIFY_TOTP_VERSION", 99), patch.object(monitor, "SPOTIFY_TOTP_SECRET_CIPHER_BYTES", (12, 34, 56, 78)):
            token = monitor.generate_totp()
        self.assertEqual(len(token.now()), 6)

    # Verifies invalid configured TOTP parameters raise an actionable error
    def test_generate_totp_rejects_invalid_config(self):
        with patch.object(monitor, "SPOTIFY_TOTP_SECRET_CIPHER_BYTES", ()):
            with self.assertRaises(ValueError):
                monitor.generate_totp()
        with patch.object(monitor, "SPOTIFY_TOTP_SECRET_CIPHER_BYTES", ("bad", 55)):
            with self.assertRaises(ValueError):
                monitor.generate_totp()
        with patch.object(monitor, "SPOTIFY_TOTP_VERSION", 0):
            with self.assertRaises(ValueError):
                monitor.generate_totp()

    # Verifies anonymous token retrieval performs no authenticated validity request
    def test_anonymous_token_skips_authenticated_validity_checks(self):
        response = FakeResponse(json_data={"accessToken": "anonymous-token", "accessTokenExpirationTimestampMs": 1700003600000, "clientId": "web-client"})
        session = Mock()
        session.get.return_value = response
        with patch.object(monitor, "spotify_fetch_server_time", return_value=1700000000):
            token_data = monitor.spotify_refresh_web_access_token(session)
        self.assertEqual(token_data["access_token"], "anonymous-token")
        session.get.assert_called_once()
        self.assertEqual(session.get.call_args.args[0], monitor.SPOTIFY_TOKEN_URL)
        self.assertNotIn("Authorization", session.get.call_args.kwargs["headers"])
        self.assertNotIn("Cookie", session.get.call_args.kwargs["headers"])

    # Verifies anonymous token data is reused until its expiration window
    def test_anonymous_token_caching(self):
        token_data = {"access_token": "anonymous-token", "expires_at": 1700003600, "client_id": "web-client"}
        with patch.object(monitor.time, "time", return_value=1700000000), patch.object(monitor, "spotify_refresh_web_access_token", return_value=token_data) as refresh:
            first = monitor.spotify_get_web_access_token_data()
            second = monitor.spotify_get_web_access_token_data()
        self.assertEqual(first, second)
        refresh.assert_called_once_with()

    # Verifies tokens inside the expiration window are refreshed
    def test_anonymous_token_expiration_window(self):
        monitor.SP_CACHED_WEB_ACCESS_TOKEN = "expiring-token"
        monitor.SP_CACHED_WEB_CLIENT_ID = "old-client"
        monitor.SP_WEB_ACCESS_TOKEN_EXPIRES_AT = 1700000030
        token_data = {"access_token": "fresh-token", "expires_at": 1700003600, "client_id": "new-client"}
        with patch.object(monitor.time, "time", return_value=1700000000), patch.object(monitor, "spotify_refresh_web_access_token", return_value=token_data) as refresh:
            result = monitor.spotify_get_web_access_token_data()
        self.assertEqual(result, token_data)
        refresh.assert_called_once_with()

    # Verifies Spotipy handles OAuth token expiration without a Web API validity probe
    def test_oauth_token_uses_spotipy_expiration_cache(self):
        cache_handler = Mock()
        auth_manager = Mock()
        auth_manager.get_access_token.return_value = "oauth-token"
        with patch("spotipy.cache_handler.MemoryCacheHandler", return_value=cache_handler) as memory_cache, patch("spotipy.oauth2.SpotifyClientCredentials", return_value=auth_manager) as credentials, patch.object(monitor.req, "get") as get:
            first = monitor.spotify_get_access_token("client-id", "client-secret")
            second = monitor.spotify_get_access_token("client-id", "client-secret")
        self.assertEqual(first, "oauth-token")
        self.assertEqual(second, "oauth-token")
        memory_cache.assert_called_once_with()
        self.assertEqual(credentials.call_count, 2)
        credentials.assert_called_with(client_id="client-id", client_secret="client-secret", requests_timeout=monitor.FUNCTION_TIMEOUT, cache_handler=cache_handler)
        self.assertEqual(auth_manager.get_access_token.call_args_list, [call(as_dict=False), call(as_dict=False)])
        get.assert_not_called()

    # Verifies OAuth tokens use the configured persistent cache path
    def test_oauth_token_uses_file_cache(self):
        monitor.SP_TOKENS_FILE = ".oauth-cache-test.json"
        cache_handler = Mock()
        auth_manager = Mock()
        auth_manager.get_access_token.return_value = "oauth-token"
        with patch("spotipy.cache_handler.CacheFileHandler", return_value=cache_handler) as file_cache, patch("spotipy.oauth2.SpotifyClientCredentials", return_value=auth_manager):
            result = monitor.spotify_get_access_token("client-id", "client-secret")
        self.assertEqual(result, "oauth-token")
        file_cache.assert_called_once_with(cache_path=".oauth-cache-test.json")
        auth_manager.get_access_token.assert_called_once_with(as_dict=False)

    # Verifies Pathfinder fields normalize to the legacy Spotify track shape
    def test_get_track_response_normalization(self):
        result = monitor.spotify_normalize_web_track(web_track_fixture())
        self.assertEqual(result["duration_ms"], 259933)
        self.assertEqual(result["name"], "My Love")
        self.assertEqual(result["id"], TRACK_ID)
        self.assertEqual(result["uri"], TRACK_URI)
        self.assertEqual(result["artists"][0]["name"], "Route 94")
        self.assertEqual(result["artists"][0]["uri"], "spotify:artist:1dgdvbogmctybPrGEcnYf6")
        self.assertEqual(result["album"]["name"], "My Love")
        self.assertEqual(result["album"]["uri"], "spotify:album:4ZD1KnBqghtSAEyqrZAkU4")
        self.assertTrue(result["external_urls"]["spotify"].startswith("https://open.spotify.com/track/"))
        self.assertTrue(result["artists"][0]["external_urls"]["spotify"].startswith("https://open.spotify.com/artist/"))
        self.assertTrue(result["album"]["external_urls"]["spotify"].startswith("https://open.spotify.com/album/"))

    # Verifies the current desktop bundle hashes are discovered and cached
    def test_persisted_query_discovery_and_cache(self):
        track_hash = "a" * 64
        search_hash = "b" * 64
        html = '<script src="https://open.spotifycdn.com/cdn/build/web-player/web-player.test.js"></script>'
        bundle = f'new Query("getTrack","query","{track_hash}",null);new Query("assistedCurationSearch","query","{search_hash}",null)'
        with patch.object(monitor.SPOTIFY_SESSION, "get", side_effect=[FakeResponse(text=html), FakeResponse(text=bundle)]) as get:
            first = monitor.spotify_discover_track_query_hash()
            second = monitor.spotify_discover_track_query_hash()
            search = monitor.spotify_discover_search_query_hash()
        self.assertEqual(first, track_hash)
        self.assertEqual(second, track_hash)
        self.assertEqual(search, search_hash)
        self.assertEqual(get.call_count, 2)

    # Verifies HTTP 401 clears the anonymous token and retries once
    def test_http_401_refreshes_anonymous_token(self):
        monitor.SP_CACHED_WEB_ACCESS_TOKEN = "expired-token"
        monitor.SP_CACHED_WEB_CLIENT_ID = "web-client"
        monitor.SP_WEB_ACCESS_TOKEN_EXPIRES_AT = int(time.time()) + 3600
        token_data = [{"access_token": "expired-token", "expires_at": int(time.time()) + 3600, "client_id": "web-client"}, {"access_token": "fresh-token", "expires_at": int(time.time()) + 3600, "client_id": "web-client"}]
        responses = [FakeResponse(status_code=401), FakeResponse(json_data={"data": {"trackUnion": web_track_fixture()}})]
        with patch.object(monitor, "spotify_get_web_access_token_data", side_effect=token_data) as token, patch.object(monitor, "spotify_discover_web_query_hash", return_value="a" * 64), patch.object(monitor.SPOTIFY_SESSION, "post", side_effect=responses):
            result = monitor.spotify_web_metadata_query("getTrack", {"uri": TRACK_URI})
        self.assertEqual(result["trackUnion"]["uri"], TRACK_URI)
        self.assertEqual(token.call_count, 2)
        self.assertIsNone(monitor.SP_CACHED_WEB_ACCESS_TOKEN)

    # Verifies a stale persisted query forces one hash rediscovery
    def test_stale_persisted_query_refreshes_hash(self):
        token_data = {"access_token": "anonymous-token", "expires_at": int(time.time()) + 3600, "client_id": "web-client"}
        responses = [FakeResponse(json_data={"errors": [{"message": "PersistedQueryNotFound"}]}), FakeResponse(json_data={"data": {"trackUnion": web_track_fixture()}})]
        with patch.object(monitor, "spotify_get_web_access_token_data", return_value=token_data), patch.object(monitor, "spotify_discover_web_query_hash", side_effect=["a" * 64, "b" * 64]) as discover, patch.object(monitor.SPOTIFY_SESSION, "post", side_effect=responses):
            result = monitor.spotify_web_metadata_query("getTrack", {"uri": TRACK_URI})
        self.assertEqual(result["trackUnion"]["uri"], TRACK_URI)
        self.assertEqual(discover.call_args_list, [call("getTrack", force=False), call("getTrack", force=True)])

    # Verifies successful web metadata lookup returns normalized public track data
    def test_successful_spotify_web_metadata(self):
        with patch.object(monitor, "spotify_web_metadata_query", return_value={"trackUnion": web_track_fixture()}) as query:
            result = monitor.spotify_get_track_info_web(TRACK_URI)
        self.assertEqual(result["id"], TRACK_ID)
        self.assertEqual(result["duration_ms"], 259933)
        query.assert_called_once_with("getTrack", {"uri": TRACK_URI})

    # Verifies anonymous search results are resolved through getTrack metadata
    def test_successful_spotify_web_search_and_metadata(self):
        normalized = monitor.spotify_normalize_web_track(web_track_fixture())
        with patch.object(monitor, "spotify_web_search_track_uris", return_value=[TRACK_URI]), patch.object(monitor, "spotify_get_track_info_web", return_value=normalized):
            track_id, duration = monitor.spotify_search_song_trackid_duration("Route 94", "My Love", "My Love")
        self.assertEqual(track_id, TRACK_ID)
        self.assertEqual(duration, 259)

    # Verifies exact track and album matches bridge localized Spotify artist aliases
    def test_localized_artist_alias_match(self):
        localized_item = {"id": "localized-track", "name": "TOKYO NITE", "artists": [{"name": "Localized Artist Alias"}], "album": {"name": "MATOUSIC"}, "duration_ms": 254000}
        self.assertEqual(monitor.spotify_search_process_track_items([localized_item], "Anna Takeuchi", "TOKYO NITE", original_album="MATOUSIC"), ("localized-track", 254))
        self.assertEqual(monitor.spotify_search_process_track_items([localized_item], "Different Artist", "TOKYO NITE"), (None, 0))

    # Verifies OAuth app search reuses the legacy strategies and normalized matcher
    def test_successful_spotify_oauth_search(self):
        normalized = monitor.spotify_normalize_web_track(web_track_fixture())
        with patch.object(monitor, "spotify_oauth_search_track_items", side_effect=[[], [], [normalized]]) as search:
            track_id, duration = monitor.spotify_search_song_trackid_duration_oauth("oauth-token", "Route 94", "My Love", "My Love")
        self.assertEqual(track_id, TRACK_ID)
        self.assertEqual(duration, 259)
        self.assertEqual([item.args[2] for item in search.call_args_list], ["specific_full", "specific_field", "specific_phrase"])

    # Verifies OAuth metadata is preferred when complete
    def test_oauth_metadata_precedes_anonymous_web(self):
        monitor.SP_CLIENT_ID = "client-id"
        monitor.SP_CLIENT_SECRET = "client-secret"
        with patch.object(monitor, "spotify_get_access_token", return_value="oauth-token") as token, patch.object(monitor, "spotify_search_song_trackid_duration_oauth", return_value=(TRACK_ID, 259)) as oauth, patch.object(monitor, "spotify_search_song_trackid_duration") as web:
            result = monitor.spotify_resolve_track_metadata("Route 94", "My Love", "My Love")
        self.assertEqual(result, (TRACK_ID, 259))
        token.assert_called_once_with("client-id", "client-secret")
        oauth.assert_called_once_with("oauth-token", "Route 94", "My Love", "My Love")
        web.assert_not_called()

    # Verifies anonymous metadata follows an OAuth app failure
    def test_anonymous_web_follows_oauth_failure(self):
        monitor.SP_CLIENT_ID = "client-id"
        monitor.SP_CLIENT_SECRET = "client-secret"
        with patch.object(monitor, "spotify_get_access_token", side_effect=RuntimeError("OAuth unavailable")), patch.object(monitor, "spotify_search_song_trackid_duration", return_value=(TRACK_ID, 259)) as web:
            result = monitor.spotify_resolve_track_metadata("Route 94", "My Love", "My Love")
        self.assertEqual(result, (TRACK_ID, 259))
        web.assert_called_once_with("Route 94", "My Love", "My Love")

    # Verifies anonymous metadata follows an OAuth search miss
    def test_anonymous_web_follows_oauth_miss(self):
        monitor.SP_CLIENT_ID = "client-id"
        monitor.SP_CLIENT_SECRET = "client-secret"
        with patch.object(monitor, "spotify_get_access_token", return_value="oauth-token"), patch.object(monitor, "spotify_search_song_trackid_duration_oauth", return_value=(None, 0)), patch.object(monitor, "spotify_search_song_trackid_duration", return_value=(TRACK_ID, 259)) as web:
            result = monitor.spotify_resolve_track_metadata("Route 94", "My Love", "My Love")
        self.assertEqual(result, (TRACK_ID, 259))
        web.assert_called_once_with("Route 94", "My Love", "My Love")

    # Verifies incomplete OAuth metadata is completed by anonymous metadata
    def test_anonymous_web_completes_oauth_metadata(self):
        monitor.SP_CLIENT_ID = "client-id"
        monitor.SP_CLIENT_SECRET = "client-secret"
        with patch.object(monitor, "spotify_get_access_token", return_value="oauth-token"), patch.object(monitor, "spotify_search_song_trackid_duration_oauth", return_value=("oauth-track", 0)), patch.object(monitor, "spotify_search_song_trackid_duration", return_value=(TRACK_ID, 259)):
            result = monitor.spotify_resolve_track_metadata("Route 94", "My Love", "My Love")
        self.assertEqual(result, (TRACK_ID, 259))

    # Verifies Last.fm duration is consulted only after Spotify web metadata fails
    def test_lastfm_duration_is_final_fallback(self):
        monitor.USE_TRACK_DURATION_FROM_SPOTIFY = True
        lastfm_track = Mock()
        lastfm_track.get_duration.return_value = 300000
        with patch.object(monitor, "spotify_resolve_track_metadata", return_value=(TRACK_ID, 259)), patch.object(monitor.pylast, "Track") as lastfm:
            spotify_result = monitor.get_track_info("Route 94", "My Love", "My Love", object())
        self.assertEqual(spotify_result, (259, TRACK_ID, " S*"))
        lastfm.assert_not_called()
        with patch.object(monitor, "spotify_resolve_track_metadata", return_value=(None, 0)), patch.object(monitor.pylast, "Track", return_value=lastfm_track) as lastfm:
            fallback_result = monitor.get_track_info("Route 94", "My Love", "My Love", object())
        self.assertEqual(fallback_result, (300, None, " L*"))
        lastfm.assert_called_once()
        with patch.object(monitor, "spotify_resolve_track_metadata", return_value=(TRACK_ID, 0)), patch.object(monitor.pylast, "Track", return_value=lastfm_track) as lastfm:
            incomplete_result = monitor.get_track_info("Route 94", "My Love", "My Love", object())
        self.assertEqual(incomplete_result, (300, TRACK_ID, " L*"))
        lastfm.assert_called_once()

    # Verifies Spotify OAuth app credentials remain optional
    def test_oauth_app_credentials_are_not_required(self):
        self.assertTrue(hasattr(monitor, "SP_CLIENT_ID"))
        self.assertTrue(hasattr(monitor, "SP_CLIENT_SECRET"))
        self.assertTrue(hasattr(monitor, "SP_TOKENS_FILE"))
        self.assertIn("SP_CLIENT_ID", monitor.SECRET_KEYS)
        self.assertIn("SP_CLIENT_SECRET", monitor.SECRET_KEYS)
        self.assertEqual(list(inspect.signature(monitor.spotify_search_song_trackid_duration).parameters), ["artist", "track", "album"])
        self.assertIn("SP_CLIENT_ID", monitor.CONFIG_BLOCK)
        self.assertIn("spotify_creds", inspect.getsource(monitor.main))
        with patch.object(monitor, "spotify_get_access_token") as token, patch.object(monitor, "spotify_search_song_trackid_duration", return_value=(TRACK_ID, 259)):
            result = monitor.spotify_resolve_track_metadata("Route 94", "My Love", "My Love")
        self.assertEqual(result, (TRACK_ID, 259))
        token.assert_not_called()


@unittest.skipUnless(os.getenv("SPOTIFY_LIVE_TESTS") == "1", "set SPOTIFY_LIVE_TESTS=1 to run live Spotify checks")
class SpotifyWebBackendLiveTests(unittest.TestCase):
    # Resets live Spotify backend caches before each test
    def setUp(self):
        monitor.SP_CACHED_WEB_ACCESS_TOKEN = None
        monitor.SP_WEB_ACCESS_TOKEN_EXPIRES_AT = 0
        monitor.SP_CACHED_WEB_CLIENT_ID = ""
        monitor.SP_CACHED_TRACK_QUERY_HASH = ""
        monitor.SP_CACHED_SEARCH_QUERY_HASH = ""

    # Verifies a real public track through the anonymous web backend
    def test_real_public_spotify_track(self):
        result = monitor.spotify_get_track_info_web(TRACK_URI)
        self.assertEqual(result["id"], TRACK_ID)
        self.assertEqual(result["name"], "My Love")
        self.assertEqual(result["artists"][0]["name"], "Route 94")
        self.assertEqual(result["album"]["name"], "My Love")
        self.assertEqual(result["duration_ms"], 259933)

    # Verifies live anonymous search resolves the real public track ID and duration
    def test_real_public_spotify_search(self):
        track_id, duration = monitor.spotify_search_song_trackid_duration("Route 94", "My Love", "My Love")
        self.assertEqual(track_id, TRACK_ID)
        self.assertEqual(duration, 259)


@unittest.skipUnless(os.getenv("SPOTIFY_OAUTH_LIVE_TESTS") == "1", "set SPOTIFY_OAUTH_LIVE_TESTS=1 with app credentials to run live OAuth checks")
class SpotifyOAuthBackendLiveTests(unittest.TestCase):
    # Configures live OAuth credentials without enabling a persistent token cache
    def setUp(self):
        monitor.SP_CLIENT_ID = os.getenv("SP_CLIENT_ID", "")
        monitor.SP_CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET", "")
        monitor.SP_TOKENS_FILE = ""
        monitor.SP_OAUTH_MEMORY_CACHE_HANDLER = None
        self.assertTrue(monitor.spotify_oauth_app_configured())

    # Verifies a real track through official Spotify OAuth app search
    def test_real_public_spotify_oauth_search(self):
        token = monitor.spotify_get_access_token(monitor.SP_CLIENT_ID, monitor.SP_CLIENT_SECRET)
        track_id, duration = monitor.spotify_search_song_trackid_duration_oauth(token, "Lost Frequencies", "Back To You", "All Stand Together")
        self.assertEqual(track_id, "4PdSICTVRI1xrXZM1sOSCe")
        self.assertEqual(duration, 156)


if __name__ == "__main__":
    unittest.main()
