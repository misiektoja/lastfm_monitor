# lastfm_monitor

Powerful real-time tracker for Last.fm that brings your music data to life with automated Spotify playback, instant activity alerts and deep scrobble analytics.

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

## Get started

1. [Install it](installation.md)
2. [Get your API credentials and run it for the first time](setup-and-first-run.md)
3. [Tune the configuration](configuration.md)

If something does not work, [`--debug`](troubleshooting.md#debug-output) will show you what the tool is doing.

## Screenshots

![lastfm_monitor](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/assets/lastfm_monitor.png)
