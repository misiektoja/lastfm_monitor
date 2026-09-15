# lastfm_monitor

<p align="left">
  <img src="https://img.shields.io/github/v/release/misiektoja/lastfm_monitor?style=flat-square&color=blue" alt="GitHub Release" />
  <img src="https://img.shields.io/pypi/v/lastfm_monitor?style=flat-square&color=teal" alt="PyPI Version" />
  <img src="https://img.shields.io/github/stars/misiektoja/lastfm_monitor?style=flat-square&color=magenta" alt="GitHub Stars" />
  <img src="https://img.shields.io/badge/python-3.9+-blueviolet?style=flat-square" alt="Python Versions" />
  <img src="https://img.shields.io/github/license/misiektoja/lastfm_monitor?style=flat-square&color=blue" alt="License" />
  <img src="https://img.shields.io/github/last-commit/misiektoja/lastfm_monitor?style=flat-square&color=green" alt="Last Commit" />
  <img src="https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square" alt="Maintenance" />
</p>

Powerful real-time tracker for Last.fm that brings your music data to life with automated Spotify playback, instant activity alerts and deep scrobble analytics.

**Full documentation: [misiektoja.github.io/lastfm_monitor](https://misiektoja.github.io/lastfm_monitor/)**

<a id="-quick-install"></a>
<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/lastfm_monitor/installation/#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install lastfm_monitor
```

Run the setup wizard:

```sh
lastfm_monitor --setup
```

The wizard asks for the target, authentication, polling intervals and optional notifications. Review the settings before saving them. See [Setup & First Run](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](https://misiektoja.github.io/lastfm_monitor/installation/).

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/assets/lastfm_monitor.png" alt="lastfm_monitor_screenshot" width="90%"/>
</p>

## Features

- **Real-time tracking** of songs listened by Last.fm users, including when a user gets online or offline
- **Automatic playback** of the tracked user's songs in your local Spotify client, with pause and resume following their actions
- **Playback detail** covering pauses and resumes, an optional track progress indicator, listened duration and whether a song was skipped or ran past its length
- **Change tracking** for the user's followers, followings, About Me bio and display name
- **Email and webhook notifications** through Discord, ntfy and compatible services, configurable per event
- **CSV export** of every listened song with timestamps, plus the **Last.fm Wrapped tool** for top artists, tracks and albums
- **Clickable music and lyrics URLs** for Last.fm, Apple Music, YouTube Music, Amazon Music, Deezer, Tidal, Genius, AZLyrics, Tekstowo.pl, Musixmatch and Lyrics.com, configurable per service
- **Session statistics** and detection of **offline mode** and **Spotify private mode**
- **Guided setup wizard** that writes a ready-to-run configuration, and a **doctor preflight** that checks it before the first run
- **Status persistence** across restarts, **flexible configuration** through config files, dotenv files, environment variables and command-line arguments, and **signal controls** for the running copy

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](https://misiektoja.github.io/lastfm_monitor/usage/#command-format) for manual-script equivalents.

Replace the target placeholders with a Last.fm username. Monitoring requires the [Last.fm API key and shared secret](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/#lastfm-api-key-and-shared-secret) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `lastfm_monitor --setup` |
| Start monitoring with saved credentials | `lastfm_monitor <lastfm_username>` |
| Check setup before monitoring | `lastfm_monitor --doctor <lastfm_username>` |
| Enter or replace credentials through hidden prompts | `lastfm_monitor --set-lastfm-credentials` |
| Use a specific configuration and secrets file | `lastfm_monitor --config-file lastfm_monitor.conf --env-file .env <lastfm_username>` |
| List the ten most recent tracks | `lastfm_monitor <lastfm_username> -l -n 10` |
| List every supported command-line option | `lastfm_monitor --help` |

The monitored account must expose the activity described in [User Privacy Settings](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/#user-privacy-settings).

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](https://misiektoja.github.io/lastfm_monitor/usage/). If a run fails, start with [Doctor Preflight](https://misiektoja.github.io/lastfm_monitor/troubleshooting/#doctor-preflight).

## Documentation

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/lastfm_monitor/installation/) | Python walkthrough, PyPI or manual installation, upgrades |
| [Setup & First Run](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/) | Setup wizard, Last.fm credentials, privacy settings and first run |
| [Configuration](https://misiektoja.github.io/lastfm_monitor/configuration/) | Config file, Spotify metadata backends, SMTP, webhooks, storing secrets, check intervals |
| [Usage](https://misiektoja.github.io/lastfm_monitor/usage/) | Monitoring mode, listing mode, notifications, CSV export, automatic playback, progress indicator, signals, coloring logs with GRC |
| [Troubleshooting](https://misiektoja.github.io/lastfm_monitor/troubleshooting/) | Doctor preflight, installation recovery, verbose and debug output |
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

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/lastfm_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/lastfm_monitor/blob/main/THIRD_PARTY_NOTICES.md).

<a id="support"></a>
## Support

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/lastfm_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
