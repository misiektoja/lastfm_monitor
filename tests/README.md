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

`test_offline_e2e.py` starts a loopback HTTP server and a subprocess, so it is marked
`e2e` if you want to run or skip it on its own:

```bash
python -m pytest -m e2e
```

## Layout

| File | Area under test |
| --- | --- |
| `test_configuration_notification_boundaries.py` | Invalid output settings, CLI precedence and strict webhook fields with legacy JSON support |
| `test_credentials_state_boundaries.py` | Fresh credential validation, candidate redaction, damaged friends state and resource failures with real HTTP clients |
| `test_boundary_regressions.py` | Real notification transports, literal secret resolution and malformed startup paths |
| `test_resource_boundaries.py` | Optional network work stops after real transport resource exhaustion |
| `test_release_boundaries.py` | Real HTTP retries, Discord mention safety, unrenderable templates, SMTP password round trips, split terminal writes and the width cap without wcwidth |
| `test_compact_commands.py` | Literal short command prefixes, real help output and dependency hints |
| `test_release_safety.py` | Credential preservation, private error rendering, runtime timing validation and saved-state compatibility |
| `test_partial_outage.py` | Real pylast history success followed by a now-playing outage and recovery |
| `test_recovery_safety.py` | Real dotenv reloads, setup backups, oversized counts and provider-error privacy |
| `test_smtp_error_privacy.py` | Short and escaped passwords in rejected SMTP sign-ins through commands, setup, Doctor and delivery |
| `test_setup_resolution_regressions.py` | Saved dotenv destinations, empty secrets, export precedence and recovery paths |
| `test_spotipy_request_policy.py` | TLS policy at the Spotipy request boundary for token exchanges and refreshes |
| `test_dotenv_quoted_keys.py` | Quoted dotenv keys, export prefixes, multiline values and duplicate removal |
| `test_documentation_layout.py` | Unique anchors, main screenshot placement and matching entry-page feature summaries |
| `test_config_loading.py` | Config files read as data and never executed |
| `test_config_writers.py` | The timestamped config backup, the atomic replace, the secrets the generated config drops and the dotenv file that is deliberately not backed up |
| `test_doctor.py` | The preflight row contract, every check's failure branches, the section order and the verdict |
| `test_family_contract.py` | The output contract shared with the sibling monitors: the four status markers, the report shape and the sentences every tool prints |
| `test_entry_points.py` | The welcome screen an empty command prints, the missing-target block, the argument combinations a secret command refuses and when the screen is cleared |
| `test_diagnostics_output.py` | The verbose and debug printers: the grammar every debug line follows, what each mode covers and what neither prints when both are off |
| `test_delivery_tests.py` | The messages both test commands send, the doctor's delivery tests and what each does with nothing to send |
| `test_documentation.py` | Documentation site structure, its internal links, the links pointing into it from the repository and the guide constants the module prints |
| `test_install_method_commands.py` | Install detection and the commands the tool prints, including the paths each one carries |
| `test_help_screen.py` | The argument groups, the shared one-shot help sentences and the examples block |
| `test_friends_notifications.py` | Friend and profile change alerts plus one user per line in plain text and HTML |
| `test_lastfm_friends_scraper.py` | Scrape headers, retry behavior, following markup and public profile parsing |
| `test_liveness_banner.py` | What a quiet run prints, when it prints it and what restarts the countdown |
| `test_recovery_errors.py` | Failure classification, the advice each failure produces and the error block it renders |
| `test_properties.py` | Generated inputs for the answer normalizers: every profile form, every duration unit, path completion and the dotenv round trip |
| `test_profile_tracking.py` | Profile baseline creation, independent field controls and deferred persistence |
| `test_private_settings.py` | Hidden credential entry with debug output silenced, atomic dotenv updates and refusal to save invalid input |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and the CI contract |
| `test_repository_metadata.py` | Governance files, citation, funding, line endings, the declared editor style, the pinned linter, the declared Python floor and release integrity |
| `test_setup_wizard.py` | The guided setup: answers held until Save, the mail server sign-in, the escape from every rejected answer, the frame around its questions, the review summary, per-section editing and the files it writes |
| `test_partial_setup_save.py` | Real wizard inputs and filesystem failures after configuration replacement |
| `test_startup_summary.py` | The startup summary rows: the shared order, the label column, which view each row belongs to and the values it reports |
| `test_secret_sources.py` | The placeholder predicate, where each secret resolved from and how the sources are reported |
| `test_notification_delivery.py` | What the two-channel sender reports and which channel a later attempt sends again |
| `test_offline_e2e.py` | A whole run end to end: the real CLI against a Last.fm fixture on loopback, one monitoring cycle, the files it writes and the same cycle on a real terminal |
| `test_startup_summary_channels.py` | Summary rows naming the webhook provider, the mail server, the masked recipient, the delivery confirmations and the runtime |
| `test_untrusted_text.py` | Text arriving from Last.fm: terminal control sequences stripped at every writer and markup escaped in email bodies |
| `test_terminal_color.py` | Coloured output: the theme and its template block, which colour lands on which token, the single colour pass through the writers and the plain log file |
| `test_spotify_web_backend.py` | TOTP generation and config override, anonymous token handling and caching |
| `test_tls_verification.py` | The TLS verification switch, the call sites that read it and the library sessions it reaches |
| `test_webhook_notifications.py` | Webhook settings coverage, startup rollups, URL validation and independent event switches |

The configuration template every released version shipped is checked in under `data/config_templates/`, so
`test_config_loading.py` can replay each of them through the current parser. See the README there before adding
or changing one.

## Conventions

* Keep every test offline. If a code path needs network access, stub it with
  `monkeypatch` rather than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a
  leaked global affects whatever runs next.
* Replace Last.fm calls and notification delivery with test doubles.
* Never use a real Last.fm API key and secret, SMTP password or webhook URL.
* Write a fake credential so a secret scanner can tell it is fake. Keep the length
  the code reports, 32 characters for the API key and secret, then use a word
  naming the setting and pad the rest with zeros, as in
  `lastfmapikey00000000000000000000`. A random-looking value is reported as a
  leaked credential by the scan CI runs over the full history.

A change to the monitoring loop, authentication or Last.fm data handling is not
verified by this suite alone. Exercise it against a real account and say so in the
pull request, without usernames or credentials.
