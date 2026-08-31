import unittest
from unittest.mock import patch

import requests

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
    # Stores the minimal requests response fields used by the Last.fm scraper
    def __init__(self, status_code=200, content=FOLLOWING_HTML, content_type="text/html; charset=utf-8"):
        self.status_code = status_code
        self.content = content
        self.headers = {'Content-Type': content_type}
        self.url = "https://www.last.fm/user/NeonCipher/following"

    # Raises the same HTTP error range that requests uses
    def raise_for_status(self):
        response = requests.Response()
        response.status_code = self.status_code
        response.url = self.url
        response.raise_for_status()


class LastfmFriendsScraperTests(unittest.TestCase):
    # Verifies compression negotiation is left to requests and its installed decoders
    def test_scrape_headers_do_not_force_brotli(self):
        self.assertNotIn('Accept-Encoding', monitor._lastfm_scrape_headers())

    # Verifies Last.fm's nonstandard HTTP 600 error response is retried before parsing
    def test_http_600_is_retried(self):
        responses = [FakeResponse(status_code=600, content=UNAVAILABLE_HTML), FakeResponse()]
        with patch.object(monitor.req, 'get', side_effect=responses) as get, patch.object(monitor.time, 'sleep') as sleep:
            response = monitor._lastfm_http_get_with_retry("https://www.last.fm/user/NeonCipher/following", attempts=2, base_delay=0.01)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_count, 2)
        sleep.assert_called_once_with(0.01)

    # Verifies a soft temporarily unavailable page is retried even with HTTP 200
    def test_soft_unavailable_page_is_retried(self):
        responses = [FakeResponse(content=UNAVAILABLE_HTML), FakeResponse()]
        with patch.object(monitor.req, 'get', side_effect=responses), patch.object(monitor.time, 'sleep'):
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


if __name__ == '__main__':
    unittest.main()
