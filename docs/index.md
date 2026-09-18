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

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-check-and-install) first.

Install from PyPI:

```sh
pip install lastfm_monitor
```

Run the setup wizard:

```sh
lastfm_monitor --setup
```

The wizard asks for the target, the Last.fm API credentials and optional notifications. Review the settings before saving them. See [Setup & First Run](setup-and-first-run.md) for how to get the Last.fm API key and shared secret and the required privacy settings.

For the manual single-file method, dependencies and upgrade commands, see [Installation](installation.md).

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
