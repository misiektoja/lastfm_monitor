# lastfm_monitor

Powerful real-time tracker for Last.fm that brings your music data to life with automated Spotify playback, instant activity alerts and deep scrobble analytics.

<a id="-quick-install"></a>
<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install lastfm_monitor
```

Run the setup wizard:

```sh
lastfm_monitor --setup
```

The wizard asks for the target, authentication, polling intervals and optional notifications. Review the settings before saving them. See [Setup & First Run](setup-and-first-run.md) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](installation.md).

## Features

- **Real-time tracking** of songs listened by Last.fm users (including detection of when a user gets online or offline)
- Possibility to **automatically play songs** listened by the tracked user in your local Spotify client
- Information about when a **user pauses or resumes playback** with the option to show a **track progress indicator**
- Information about the **duration** the user listened to a song and whether the **song was skipped** and if it was **shorter or longer than the track duration**
- **Tracking** of a Last.fm user's **followers**, **followings**, **About Me bio** and **display name** with change notifications
- **Email notifications** for various events (user becomes active or inactive, specific or all songs, songs on loop, new entries appearing while user was offline, friend changes, profile changes, errors)
- **Webhook notifications** through **Discord**, **ntfy** and compatible integrations with event-specific controls
- **Saving all listened songs** with timestamps to the **CSV file**
- **Last.fm Wrapped tool** for generating Spotify Wrapped-style statistics (top artists, tracks, albums) from CSV data
- **Clickable** **Last.fm**, **Apple Music**, **YouTube Music**, **Amazon Music**, **Deezer**, **Tidal**, **Genius Lyrics**, **AZLyrics**, **Tekstowo.pl**, **Musixmatch** and **Lyrics.com** search URLs printed in the console and included in email notifications (configurable per service)
- Displaying **basic statistics for the user's playing session** (duration, time span, number of listened and skipped songs, songs on loop, paused playback time and number of pauses, songs played count)
- Support for detecting **offline mode**
- Support for detecting **Spotify's private mode** (not 100% accurate)
- **Status persistence** - automatically saves the last activity status, friend lists and tracked profile fields to JSON files to track changes across restarts
- **Flexible configuration** - support for config files, dotenv files, environment variables and command-line arguments
- Possibility to **control the running copy** of the script via signals
- **Functional, procedural Python** (minimal OOP)

## Screenshots

![lastfm_monitor](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/assets/lastfm_monitor.png)

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](usage.md#command-format) for manual-script equivalents.

Replace the target placeholders with a Last.fm username. Monitoring requires the [Last.fm API key and shared secret](setup-and-first-run.md#lastfm-api-key-and-shared-secret) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `lastfm_monitor --setup` |
| Start monitoring with saved credentials | `lastfm_monitor <lastfm_username>` |
| Check setup before monitoring | `lastfm_monitor --doctor <lastfm_username>` |
| Enter or replace credentials through hidden prompts | `lastfm_monitor --set-lastfm-credentials` |
| Use a specific configuration and secrets file | `lastfm_monitor --config-file lastfm_monitor.conf --env-file .env <lastfm_username>` |
| List the ten most recent tracks | `lastfm_monitor <lastfm_username> -l -n 10` |
| List every supported command-line option | `lastfm_monitor --help` |

The monitored account must expose the activity described in [User Privacy Settings](setup-and-first-run.md#user-privacy-settings).

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](usage.md). If a run fails, start with [Doctor Preflight](troubleshooting.md#doctor-preflight).

## Documentation

* [Installation](installation.md) - Python setup, package or manual install and upgrades
* [Setup & First Run](setup-and-first-run.md) - credentials, target selection and the setup wizard
* [Configuration](configuration.md) - settings, notifications and secret storage
* [Usage](usage.md) - monitoring, output and command options
* [Troubleshooting](troubleshooting.md) - Doctor checks and recovery steps
