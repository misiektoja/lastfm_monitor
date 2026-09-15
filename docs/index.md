# lastfm_monitor

Powerful real-time tracker for Last.fm that brings your music data to life with automated Spotify playback, instant activity alerts and deep scrobble analytics.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/assets/lastfm_monitor.png" alt="lastfm_monitor_screenshot" width="90%"/>
</p>

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
* [Testing](testing.md) - automated checks and documentation builds
* [About](about.md) - contributing, security, licensing and support
