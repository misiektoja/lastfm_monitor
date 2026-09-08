# Offline test suite

These tests cover logic in `lastfm_monitor.py` that can run without network access.
Last.fm and Spotify calls are replaced with test doubles.

## Running

From the repository root:

```bash
pip install -e '.[test]'
python -m pytest
```

`pyproject.toml` puts the repository root first on `sys.path`, so the tests use the
working tree instead of an installed copy of the module.

Lint the same way CI does:

```bash
pip install -e '.[lint]'
python -m ruff check lastfm_monitor.py tools tests
```

CI runs both on every push and pull request, across Python 3.9 through 3.14,
and again before anything is published to PyPI.

## Layout

| File | Area under test |
| --- | --- |
| `test_config_loading.py` | Config files read as data and never executed |
| `test_documentation.py` | Documentation site structure, its internal links, the links pointing into it from the repository and the guide constants the module prints |
| `test_friends_notifications.py` | Friend and profile change alerts plus one user per line in plain text and HTML |
| `test_lastfm_friends_scraper.py` | Scrape headers, retry behavior, following markup and public profile parsing |
| `test_recovery_errors.py` | Failure classification, the advice each failure produces and the error block it renders |
| `test_profile_tracking.py` | Profile baseline creation, independent field controls and deferred persistence |
| `test_private_settings.py` | Hidden credential entry, atomic dotenv updates and refusal to save invalid input |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and the CI contract |
| `test_repository_metadata.py` | Governance files, citation, funding, line endings, the declared editor style, the pinned linter and release integrity |
| `test_spotify_web_backend.py` | TOTP generation and config override, anonymous token handling and caching |
| `test_webhook_notifications.py` | Webhook settings coverage, startup rollups, URL validation and independent event switches |

## Conventions

* Keep every test offline. If a code path needs network access, stub it with
  `monkeypatch` rather than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a
  leaked global affects whatever runs next.
* Replace Last.fm calls and notification delivery with test doubles.
* Never use a real Last.fm API key and secret, SMTP password or webhook URL.

A change to the monitoring loop, authentication or Last.fm data handling is not
verified by this suite alone. Exercise it against a real account and say so in the
pull request, without usernames or credentials.
