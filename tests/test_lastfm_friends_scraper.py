import unittest
from unittest.mock import patch

import pytest
from curl_cffi import requests as curl_requests

import lastfm_monitor as monitor


FOLLOWING_HTML = b"""<!doctype html>
<html>
<head><title>People NeonCipher Follows | Last.fm</title></head>
<body class="namespace--user_following">
<h1 class="header-title"><a href="/user/NeonCipher">NeonCipher</a></h1>
<h1 class="content-top-header">Following (1)</h1>
<ul class="user-list">
<li class="user-list-item"><h4 class="user-list-name"><a href="/user/EchoInTheShell">EchoInTheShell</a></h4></li>
<li class="user-list-item user-list-item-mobile-ad"><div>Advertisement</div></li>
</ul>
</body>
</html>"""

UNAVAILABLE_HTML = b"""<!doctype html>
<html>
<head><title>Last.fm - Temporarily Unavailable</title></head>
<body><h1>Temporarily unavailable</h1><div id="error">Error 503</div></body>
</html>"""

CHALLENGE_HTML = b"""<!doctype html>
<html><head><title>Client Challenge</title></head>
<body><noscript>JavaScript is disabled in your browser.</noscript></body></html>"""

PROFILE_HTML = b"""<!doctype html>
<html>
<body>
<h1 class="header-title"><a href="/user/NeonCipher">NeonCipher</a></h1>
<p class="header-title-secondary"><span class="header-title-display-name">Neon Cipher</span></p>
<div class="about-me-header"><p>First line</p><p>Second &amp; <a href="/tag/final">final</a> line</p></div>
<section class="about-me-sidebar"><h2>About Me</h2><p>Duplicate mobile bio</p></section>
</body>
</html>"""


class FakeResponse:
    # Stores the response fields used by the Last.fm scraper
    def __init__(self, status_code=200, content=FOLLOWING_HTML, content_type="text/html; charset=utf-8", location=None):
        self.status_code = status_code
        self.content = content
        self.headers = {'Content-Type': content_type}
        if location is not None:
            self.headers['Location'] = location
        self.url = "https://www.last.fm/user/NeonCipher/following"

    # Raises the HTTP error supplied by the website transport
    def raise_for_status(self):
        response = curl_requests.Response()
        response.status_code = self.status_code
        response.ok = 200 <= self.status_code < 400
        response.url = self.url
        response.raise_for_status()


class LastfmFriendsScraperTests(unittest.TestCase):
    # Leaves browser identity and compression negotiation to the impersonation profile
    def test_scrape_headers_do_not_force_brotli(self):
        self.assertNotIn('Accept-Encoding', monitor._lastfm_scrape_headers())
        self.assertNotIn('User-Agent', monitor._lastfm_scrape_headers())

    # Verifies Last.fm's nonstandard HTTP 600 error response is retried before parsing
    def test_http_600_is_retried(self):
        responses = [FakeResponse(status_code=600, content=UNAVAILABLE_HTML), FakeResponse()]
        with patch.object(curl_requests, 'get', side_effect=responses) as get, patch.object(monitor.time, 'sleep') as sleep:
            response = monitor._lastfm_http_get_with_retry("https://www.last.fm/user/NeonCipher/following", attempts=2, base_delay=0.01)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_count, 2)
        sleep.assert_called_once_with(0.01)

    # Verifies a soft temporarily unavailable page is retried even with HTTP 200
    def test_soft_unavailable_page_is_retried(self):
        responses = [FakeResponse(content=UNAVAILABLE_HTML), FakeResponse()]
        with patch.object(curl_requests, 'get', side_effect=responses), patch.object(monitor.time, 'sleep'):
            response = monitor._lastfm_http_get_with_retry("https://www.last.fm/user/NeonCipher/following", attempts=2, base_delay=0)
        self.assertEqual(response.content, FOLLOWING_HTML)

    # Verifies the current Last.fm list markup still yields the expected username
    def test_current_following_markup_is_parsed(self):
        with patch.object(monitor, '_lastfm_http_get_with_retry', return_value=FakeResponse()):
            users = monitor._lastfm_scrape_user_list("NeonCipher", "following")
        self.assertEqual(users, {"EchoInTheShell"})

    # Verifies profile tracking reads the public display name and one canonical About Me copy
    def test_current_profile_markup_is_parsed(self):
        with patch.object(monitor, '_lastfm_http_get_with_retry', return_value=FakeResponse(content=PROFILE_HTML)):
            profile = monitor.lastfm_get_profile("NeonCipher")
        self.assertEqual(profile, {"display_name": "Neon Cipher", "bio": "First line\nSecond & final line"})

    # Verifies a page for another account cannot replace the requested profile baseline
    def test_profile_owner_is_validated(self):
        with patch.object(monitor, '_lastfm_http_get_with_retry', return_value=FakeResponse(content=PROFILE_HTML)):
            with self.assertRaisesRegex(RuntimeError, "profile owner"):
                monitor.lastfm_get_profile("DifferentUser")


@pytest.mark.parametrize("verify", [True, False])
# Uses browser impersonation with the configured TLS policy and timeout without calling requests
def test_website_transport_policy(monkeypatch, verify):
    monkeypatch.setattr(monitor, "VERIFY_SSL", verify)
    monkeypatch.setattr(monitor, "FUNCTION_TIMEOUT", 7)
    with patch.object(curl_requests, "get", return_value=FakeResponse()) as get, patch.object(monitor.req, "get") as ordinary_get:
        assert monitor.lastfm_get_friends("NeonCipher") == {"EchoInTheShell"}
    get.assert_called_once_with("https://www.last.fm/user/NeonCipher/following", impersonate="chrome", headers={"Accept-Language": "en-US,en;q=0.9"}, timeout=14, verify=verify, allow_redirects=False)
    ordinary_get.assert_not_called()


@pytest.mark.parametrize("status", [301, 302, 307, 308])
# Refuses a redirect instead of letting the response choose the host the scraper reads, and names where it pointed
def test_a_redirect_is_refused_and_not_retried(status):
    redirect = FakeResponse(status, content=b"", location="http://169.254.169.254/latest/meta-data/")
    with patch.object(curl_requests, "get", return_value=redirect) as get, patch.object(monitor.time, "sleep") as sleep:
        with pytest.raises(RuntimeError, match="169.254.169.254"):
            monitor.lastfm_get_friends("NeonCipher")
    # A redirect is a changed destination rather than a transient failure, so retrying it would only repeat the refusal
    get.assert_called_once()
    sleep.assert_not_called()


# Names the refusal even when the response withholds the destination, so the error never reads as a parsing failure
def test_a_redirect_without_a_location_is_still_refused():
    with patch.object(curl_requests, "get", return_value=FakeResponse(302, content=b"")), patch.object(monitor.time, "sleep"):
        with pytest.raises(RuntimeError, match="unspecified location"):
            monitor.lastfm_get_profile("NeonCipher")


@pytest.mark.parametrize("status", [200, 403])
# Retries a browser challenge before the list parser sees its missing header
def test_challenge_recovers(status):
    responses = [FakeResponse(status, CHALLENGE_HTML), FakeResponse()]
    with patch.object(curl_requests, "get", side_effect=responses) as get, patch.object(monitor.time, "sleep") as sleep:
        assert monitor.lastfm_get_friends("NeonCipher") == {"EchoInTheShell"}
    assert get.call_count == 2
    sleep.assert_called_once_with(2.0)


@pytest.mark.parametrize("field", ["followings", "followers", "profile"])
# Preserves saved tracking state when every website attempt returns a challenge
def test_persistent_challenge_preserves_state(monkeypatch, field):
    monkeypatch.setattr(monitor, "load_friends_state", lambda *args: {"SavedUser"})
    monkeypatch.setattr(monitor, "load_profile_state", lambda *args: {"display_name": "Saved name", "bio": "Saved bio"})
    with patch.object(curl_requests, "get", return_value=FakeResponse(content=CHALLENGE_HTML)) as get, patch.object(monitor.time, "sleep"), patch.object(monitor, "save_friends_state") as save_friends, patch.object(monitor, "save_profile_state") as save_profile:
        with pytest.raises(RuntimeError, match="browser verification page") as raised:
            monitor.check_friends_changes("NeonCipher", field == "followings", field == "followers", track_bio=field == "profile", track_display_name=field == "profile", raise_on_error=True)
    assert get.call_count == 3
    save_friends.assert_not_called()
    save_profile.assert_not_called()
    advice = monitor.classify_recovery_error(raised.value)
    assert advice.code == "lastfm.challenge"
    assert advice.retryable is True
    assert "curl_cffi" in advice.fix
    assert "layout" not in advice.summary


# Does not classify ordinary profile text as a browser challenge
def test_challenge_words_in_profile_are_not_an_error():
    content = PROFILE_HTML.replace(b"First line", b"Client Challenge: JavaScript is disabled in your browser")
    assert monitor._lastfm_retryable_response_error(FakeResponse(content=content)) is None


@pytest.mark.parametrize("error_type", [curl_requests.exceptions.Timeout, curl_requests.exceptions.ConnectionError, curl_requests.exceptions.RequestException])
# Retries native curl transport failures with bounded backoff
def test_curl_transport_errors_are_retried(error_type):
    error = error_type("temporary transport failure")
    with patch.object(curl_requests, "get", side_effect=error) as get, patch.object(monitor.time, "sleep") as sleep:
        with pytest.raises(RuntimeError, match="after 2 attempts") as raised:
            monitor._lastfm_http_get_with_retry("https://www.last.fm/user/example/following", attempts=2, base_delay=0.1)
    assert get.call_count == 2
    sleep.assert_called_once_with(0.1)
    assert raised.value.__cause__ is error


@pytest.mark.parametrize("status", [403, 404])
# Stops permanent HTTP failures immediately while retaining the native cause
def test_permanent_http_failure_is_not_retried(status):
    with patch.object(curl_requests, "get", return_value=FakeResponse(status_code=status)) as get, patch.object(monitor.time, "sleep") as sleep:
        with pytest.raises(RuntimeError, match="Failed to fetch from Last.fm") as raised:
            monitor._lastfm_http_get_with_retry("https://www.last.fm/user/example/following")
    assert isinstance(raised.value.__cause__, curl_requests.exceptions.HTTPError)
    get.assert_called_once()
    sleep.assert_not_called()


# Names the nonstandard status Last.fm answers the website with, which carries no response object to read it from
def test_a_lasting_nonstandard_status_is_reported_as_a_website_failure():
    with patch.object(curl_requests, "get", return_value=FakeResponse(status_code=600)), patch.object(monitor.time, "sleep"):
        with pytest.raises(RuntimeError, match="after 3 attempts") as raised:
            monitor._lastfm_http_get_with_retry("https://www.last.fm/user/NeonCipher/following")
    advice = monitor.classify_recovery_error(raised.value)
    assert advice.code == "lastfm.website_error"
    assert "600" in advice.summary
    assert advice.retryable is True
    assert monitor.WEBSITE_TRACKING_GUIDE_URL in advice.fix


@pytest.mark.parametrize("fetch", [monitor.lastfm_get_friends, monitor.lastfm_get_followers, monitor.lastfm_get_profile])
# Keeps missing transport guidance intact across the public parsing functions
def test_missing_curl_dependency_reports_installation(monkeypatch, fetch):
    monkeypatch.setattr(monitor, "curl_req", None)
    with pytest.raises(monitor.RecoveryError) as raised:
        fetch("NeonCipher")
    assert raised.value.advice.code == "dependency.missing"
    assert "curl_cffi" in raised.value.advice.fix


if __name__ == '__main__':
    unittest.main()
