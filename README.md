# lastfm_monitor

[![GitHub Release](https://img.shields.io/github/v/release/misiektoja/lastfm_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/lastfm_monitor/releases)
[![PyPI Version](https://img.shields.io/pypi/v/lastfm_monitor?style=flat-square&color=teal)](https://pypi.org/project/lastfm-monitor/)
[![GitHub Stars](https://img.shields.io/github/stars/misiektoja/lastfm_monitor?style=flat-square&color=magenta)](https://github.com/misiektoja/lastfm_monitor)
[![Python Versions](https://img.shields.io/badge/python-3.9+-blueviolet?style=flat-square)](https://pypi.org/project/lastfm-monitor/)
[![License](https://img.shields.io/github/license/misiektoja/lastfm_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/lastfm_monitor/blob/main/LICENSE)
[![OpenSSF Scorecard](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Flastfm_monitor&query=%24.score&label=openssf%20scorecard&style=flat-square)](https://scorecard.dev/viewer/?uri=github.com/misiektoja/lastfm_monitor)
[![Last Commit](https://img.shields.io/github/last-commit/misiektoja/lastfm_monitor?style=flat-square&color=green)](https://github.com/misiektoja/lastfm_monitor/commits/main)
[![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square)](https://github.com/misiektoja/lastfm_monitor)

Powerful real-time tracker for Last.fm that brings your music data to life with automated Spotify playback, instant activity alerts and deep scrobble analytics.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/assets/lastfm_monitor.png" alt="lastfm_monitor_screenshot" width="90%"/>
</p>

<a id="quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/lastfm_monitor/installation/#new-to-python-check-and-install) first.

Install from PyPI:

```sh
pip install lastfm_monitor
```

Run the setup wizard:

```sh
lastfm_monitor --setup
```

The wizard asks for the target, the Last.fm API credentials and optional notifications. Review the settings before saving them. See [Setup & First Run](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/) for how to get the Last.fm API key and shared secret and the required privacy settings.

For the manual single-file method, dependencies and upgrade commands, see [Installation](https://misiektoja.github.io/lastfm_monitor/installation/).

<a id="features"></a>
## Features

### 🔍 Listening and Profile Tracking

* **Listening activity**: Track songs, active and inactive periods, pauses and resumes.
* **Playback detail**: Show listening duration, skipped tracks and an optional progress indicator.
* **Profile changes**: Track followers, followed accounts, About Me bio and display name.
* **Activity gaps**: Detect offline listening and estimate Spotify private mode, which is not always accurate.

### 📊 Playback and Insights

* **Spotify playback**: Follow the tracked user's songs, pauses and resumes in your local Spotify client.
* **Session statistics**: Summarize listening time, tracks, skips, repeats and pauses.
* **Last.fm Wrapped**: Generate top artist, track and album statistics from CSV history.
* **Music and lyrics links**: Open configurable searches from console output and email.

### 🔔 Notifications and History

* **Event alerts**: Configure email, Discord and ntfy notifications for listening and profile changes.
* **CSV history**: Save listened tracks with timestamps.
* **Saved state**: Retain activity, friend lists and tracked profile fields across restarts.

### ⚙️ Setup and Configuration

* **Guided setup**: Configure the monitor with `--setup` and check readiness with `--doctor`.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Runtime controls**: Adjust the running monitor through supported signals.

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install--run) above for first-time setup. The table uses PyPI commands. For the manual script equivalents, see [Run Individual Commands](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/#run-individual-commands).

Replace the target placeholders with a Last.fm username. Monitoring requires the [Last.fm API key and shared secret](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/#lastfm-api-key-and-shared-secret) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `lastfm_monitor --setup` |
| Start monitoring with existing authentication | `lastfm_monitor <lastfm_username>` |
| Check authentication, connectivity and one target | `lastfm_monitor --doctor <lastfm_username>` |
| Enter or replace securely the Last.fm API key and shared secret | `lastfm_monitor --set-lastfm-credentials` |
| Enter or replace securely the optional Spotify credentials for track details | `lastfm_monitor --set-spotify-credentials` |
| Configure and test webhook alerts | Use the setup wizard or follow [Webhook Settings](https://misiektoja.github.io/lastfm_monitor/configuration/#webhook-settings) |
| Save an SMTP password for email alerts | `lastfm_monitor --set-smtp-password` |
| Send a test email | `lastfm_monitor --send-test-email` |
| Save a new webhook URL | `lastfm_monitor --set-webhook-url` |
| Send a test webhook | `lastfm_monitor --send-test-webhook` |
| List the ten most recent tracks | `lastfm_monitor <lastfm_username> -l -n 10` |
| Alert on the tracks and albums listed in a file | `lastfm_monitor <lastfm_username> -s tracks.txt` |
| Write every scrobble to a CSV file | `lastfm_monitor <lastfm_username> -b scrobbles.csv` |
| Play every scrobble in your own Spotify client | `lastfm_monitor <lastfm_username> -g` |
| Use a specific configuration and secrets file | `lastfm_monitor --config-file lastfm_monitor.conf --env-file .env <lastfm_username>` |
| List every supported command-line flag | `lastfm_monitor --help` |

The monitored account must expose the activity described in [User Privacy Settings](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/#user-privacy-settings).

Running the tool with no arguments offers the wizard if you have not saved a user. If a user is already saved, it starts monitoring that user.

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence and run multiple copies to monitor several users.

For credentials, saved users and notification setup, see the [full Setup & First Run guide](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/).

For the Spotify metadata backends, email and webhook setup, see [Configuration](https://misiektoja.github.io/lastfm_monitor/configuration/). For notification choices, listing commands, automatic playback and output files, see [Usage](https://misiektoja.github.io/lastfm_monitor/usage/).

If a run fails, start with [Doctor Preflight](https://misiektoja.github.io/lastfm_monitor/troubleshooting/#doctor-preflight).

<a id="documentation"></a>
## Documentation

Full documentation is available at **[misiektoja.github.io/lastfm_monitor](https://misiektoja.github.io/lastfm_monitor/)**:

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/lastfm_monitor/installation/) | Python walkthrough, PyPI or manual installation, upgrades |
| [Setup & First Run](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/) | Setup wizard, Last.fm credentials, privacy settings, the first monitoring run |
| [Configuration](https://misiektoja.github.io/lastfm_monitor/configuration/) | Config file, Spotify metadata backends, SMTP, webhooks, storing secrets, check intervals |
| [Usage](https://misiektoja.github.io/lastfm_monitor/usage/) | Monitoring mode, listing mode, notifications, CSV export, automatic playback, signals, terminal output |
| [Troubleshooting](https://misiektoja.github.io/lastfm_monitor/troubleshooting/) | `--doctor` preflight checks, what to do when something fails, `--verbose` and `--debug` output |
| [Testing](https://misiektoja.github.io/lastfm_monitor/testing/) | Running the offline suite, the linter and the docs build |
| [About](https://misiektoja.github.io/lastfm_monitor/about/) | Change log, contributing, security, license, support |

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/lastfm_monitor/blob/main/RELEASE_NOTES.md) for details.

<a id="contributing"></a>
## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/lastfm_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/lastfm_monitor/blob/main/CODE_OF_CONDUCT.md).

<a id="security"></a>
## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/lastfm_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/lastfm_monitor/blob/main/SECURITY.md) covers the reporting process, the supported versions and the security posture of stored credentials and configuration loading.

<a id="maintainers"></a>
## Maintainers

- **misiektoja** ([@misiektoja](https://github.com/misiektoja))

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/lastfm_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/lastfm_monitor/blob/main/THIRD_PARTY_NOTICES.md).

<a id="support"></a>
## Support

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/lastfm_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
