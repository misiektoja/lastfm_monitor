# Usage

## Monitoring Mode

To monitor specific user activity, just type Last.fm username as a command-line argument (`lastfm_username` in the example below):

```sh
lastfm_monitor <lastfm_username>
```

If you have not set `LASTFM_API_KEY` and `LASTFM_API_SECRET` secrets, you can use `-u` and `-w` flags:

```sh
lastfm_monitor <lastfm_username> -u "your_lastfm_api_key" -w "your_lastfm_api_secret"
```

To provide optional Spotify OAuth app credentials for one run, use `-z` / `--spotify-creds`:

```sh
lastfm_monitor <lastfm_username> -z "your_spotify_app_client_id:your_spotify_app_client_secret"
```

Settings come from a configuration file when one is found. [Configuration File](configuration.md#configuration-file) covers where the tool looks for it and how to select another one with `--config-file`.

If a run does not start, `--doctor` reports every check the tool makes before monitoring. See [Doctor Preflight](troubleshooting.md#doctor-preflight).

Before monitoring starts the tool prints the settings in effect: the monitored user, the polling intervals, both alert channels, the files the run reads and writes, and each optional feature that is switched on. `--verbose` and `--debug` print the complete list instead, including the settings left at their defaults and where each secret came from. See [Verbose Output](troubleshooting.md#verbose-output).

The log file always receives the complete list, whichever view the terminal was shown, so a log attached to a bug report carries every effective setting.

To enable tracking of followers and/or followings changes:
- set `TRACK_FOLLOWERS` and/or `TRACK_FOLLOWINGS` to `True`
- or use the `--track-followers` and/or `--track-followings` flags

```sh
lastfm_monitor <lastfm_username> --track-followers --track-followings
```

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple Last.fm users by running multiple copies of the script.

The tool automatically saves its output to `lastfm_monitor_<username>.log` file. It can be changed in the settings via `LF_LOGFILE` configuration option or disabled completely via `DISABLE_LOGGING` / `-d` flag.

Set `ASCII_LOG_SEPARATORS` to `"Auto"` (default) to use ASCII separator-only lines on Windows, `"On"` to use them on every operating system or `"Off"` to preserve Unicode separators in logs everywhere. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

The tool also saves the last activity information (artist, track, timestamp) to `lastfm_<username>_last_activity.json` file and the number and list of followings and followers to `lastfm_<username>_followings.json` and `lastfm_<username>_followers.json` files (if tracking is enabled), so this data can be reused if the tool is restarted.

## Listing Mode

There is another mode of the tool that prints the recently listened tracks for the user (`-l` flag).

You can also add the `-n` flag to specify how many tracks should be displayed, by default it shows the last 30 tracks:

```sh
lastfm_monitor <lastfm_username> -l  -n 10
```

![lastfm_monitor_listing](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/assets/lastfm_monitor_listing.png)

If you want to not only display, but also save the list of recently listened track to a CSV file, use the `-l` flag with `-b` indicating the CSV file. As before, you can add the `-n` flag to specify how many tracks should be displayed/saved:

```sh
lastfm_monitor <lastfm_username> -l -n 10 -b lastfm_tracks_username.csv
```

## Email Notifications

To enable email notifications when a user becomes active:
- set `ACTIVE_NOTIFICATION` to `True`
- or use the `-a` flag

```sh
lastfm_monitor <lastfm_username> -a
```

To be informed when a user gets inactive:
- set `INACTIVE_NOTIFICATION` to `True`
- or use the `-i` flag

```sh
lastfm_monitor <lastfm_username> -i
```

Inactivity emails include recent songs from the session with skipped and continued track status. Configure the number of recent songs to include via the `INACTIVE_EMAIL_RECENT_SONGS_COUNT` configuration option.

To be notified when new entries appear when the user is offline:
- set `OFFLINE_ENTRIES_NOTIFICATION` to `True`
- or use the `-f` flag

```sh
lastfm_monitor <lastfm_username> -f
```

To get email notifications when a monitored track or album plays:
- set `TRACK_NOTIFICATION` to `True`
- or use the `-t` flag

For that feature you also need to create a file with a list of songs you want to track (one track or album per line). Specify the file using the `MONITOR_LIST_FILE` or `-s` flag:

Example file `lastfm_tracks_username`:

```
we fell in love in october
Like a Stone
Half Believing
Something Changed
I Will Be There
```

You can comment out specific lines with # if needed.

Then run the tool with `-t` and `-s` flags:

```sh
lastfm_monitor <lastfm_username> -t -s lastfm_tracks_username
```

To enable email notifications for every song listened by the user:
- set `SONG_NOTIFICATION` to `True`
- or use the `-j` flag

```sh
lastfm_monitor <lastfm_username> -j
```

To be notified when a user listens to the same song on loop:
- set `SONG_ON_LOOP_NOTIFICATION` to `True`
- or use the `-x` flag

```sh
lastfm_monitor <lastfm_username> -x
```

To disable sending an email on errors (enabled by default):
- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
lastfm_monitor <lastfm_username> -e
```

To be notified when a user's followers change:
- set `FOLLOWERS_NOTIFICATION` to `True`
- or use the `--notify-followers` flag

```sh
lastfm_monitor <lastfm_username> --track-followers --notify-followers
```

To be notified when a user's followings (friends) change:
- set `FOLLOWINGS_NOTIFICATION` to `True`
- or use the `--notify-followings` flag

```sh
lastfm_monitor <lastfm_username> --track-followings --notify-followings
```

Notifications for changed followers and/or followings are only sent if tracking functionality is enabled (`--track-followers` and/or `--track-followings` flags).

To track changes to the editable **About You** text shown publicly as **About Me** or the user's display name:

```sh
lastfm_monitor <lastfm_username> --track-bio --track-display-name
```

Set `PROFILE_NOTIFICATION` to `True` or add `--notify-profile` to send email for confirmed profile changes. Each field is independently controlled through `TRACK_BIO` / `--track-bio` and `TRACK_DISPLAY_NAME` / `--track-display-name`. The baseline is stored in `lastfm_<username>_profile.json`.

You can also decide to use Last.fm or Spotify URL in "Last played:" / "Track:" field in HTML email notifications (see `USE_LASTFM_URL_IN_LAST_PLAYED` config option).

Make sure you defined your SMTP settings earlier (see [SMTP settings](configuration.md#smtp-settings)).

Example email:

![lastfm_monitor_email_notifications](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/assets/lastfm_monitor_email_notifications.png)

## Webhook Notifications

Webhook event choices mirror email controls while remaining independent. Enable the master switch in the config file or for one run:

```sh
lastfm_monitor <lastfm_username> --webhook
```

Choose events with config settings or matching command-line flags:

| Event | Config setting | Command-line flag |
|---|---|---|
| User becomes active | `WEBHOOK_ACTIVE_NOTIFICATION` | `--webhook-active` |
| User becomes inactive | `WEBHOOK_INACTIVE_NOTIFICATION` | `--webhook-inactive` |
| Monitored track or album plays | `WEBHOOK_TRACK_NOTIFICATION` | `--webhook-track` |
| Every song change | `WEBHOOK_SONG_NOTIFICATION` | `--webhook-song-changes` |
| Song plays on loop | `WEBHOOK_SONG_ON_LOOP_NOTIFICATION` | `--webhook-loop` |
| Offline scrobbles arrive | `WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION` | `--webhook-offline-entries` |
| Followers change | `WEBHOOK_FOLLOWERS_NOTIFICATION` | `--webhook-followers` |
| Followings change | `WEBHOOK_FOLLOWINGS_NOTIFICATION` | `--webhook-followings` |
| Tracked bio or display name changes | `WEBHOOK_PROFILE_NOTIFICATION` | `--webhook-profile` |
| Monitoring error occurs | `WEBHOOK_ERROR_NOTIFICATION` | `--webhook-errors` |

An event flag also enables the master switch for that run. Use `--no-webhook` to disable configured webhook delivery. Use `--no-webhook-error-notify` to disable only error webhooks.

Examples:

```sh
lastfm_monitor <lastfm_username> --webhook-active --webhook-inactive
lastfm_monitor <lastfm_username> --webhook-song-changes --webhook-loop
lastfm_monitor <lastfm_username> --track-followers --webhook-followers
```

Email and webhook delivery attempts remain independent. When loop, monitored-track and every-song choices overlap, Last.fm Monitor sends no more than one alert per channel for that song change.

See [Webhook Settings](configuration.md#webhook-settings) for Discord, ntfy, private URL setup, test delivery and advanced request customization.

## CSV Export

If you want to save all listened songs to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
lastfm_monitor <lastfm_username> -b lastfm_tracks_username.csv
```

The file will be automatically created if it does not exist.

## Last.fm Wrapped Tool

The *[lastfm_wrapped.py](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/tools/lastfm_wrapped.py)* script generates Spotify Wrapped-style statistics from CSV files created by `lastfm_monitor.py`.

It analyzes your listening data and provides insights including top artists, tracks and albums for a specified time period.

**Basic Usage:**

By default, it generates statistics for the current year (January 1 to November 15, similar to Spotify Wrapped):

```sh
python3 tools/lastfm_wrapped.py lastfm_tracks_username.csv
```

**Custom Date Range:**

You can specify a custom date range using `--from` and `--to` flags:

```sh
python3 tools/lastfm_wrapped.py lastfm_tracks_username.csv --from 2024-01-01 --to 2024-12-31
```

**Top N Items:**

By default, it shows the top 5 items in each category, just like Spotify Wrapped. You can change this with the `--top-n` flag:

```sh
python3 tools/lastfm_wrapped.py lastfm_tracks_username.csv --top-n 10
```

**Example Output:**

The tool displays:
- Total scrobbles for the period
- Top artists (by play count)
- Top tracks (by play count)
- Top albums (by play count)

## Automatic Playback of Listened Tracks in the Spotify Client

If you want the tool to automatically play the tracks listened to by the user in your local Spotify client:
- set `TRACK_SONGS` to `True`
- or use the `-g` flag

```sh
lastfm_monitor <lastfm_username> -g
```

Your Spotify client needs to be installed and running for this feature to work.

Automatic playback needs a Spotify track ID for every scrobble. The tool resolves that ID through the [Spotify metadata backends](configuration.md#spotify-metadata-backends). It tries the official OAuth app Web API when credentials are configured, then uses the anonymous web-player backend. OAuth app credentials are optional.

The local playback action itself uses the configured platform method such as AppleScript on macOS or D-Bus on Linux. It does not use Spotify Web API playback control.

The tool fully supports automatic playback on **Linux** and **macOS**. This means it will automatically play the changed track. It will also automatically pause and resume playback following the tracked user's actions. Additionally, it can pause or play an indicated track once the user becomes inactive (see the `SP_USER_GOT_OFFLINE_TRACK_ID` configuration option).

For **Windows**, it works in a semi-automatic way: if you have the Spotify client running and you are not listening to any song, then the first track will play automatically. However, subsequent tracks will be located in the client, but you will need to press the play button manually.

You can change the playback method per platform using the corresponding configuration option.

For **macOS** set `SPOTIFY_MACOS_PLAYING_METHOD` to one of the following values:
-  "**apple-script**" (recommended, **default**)
-  "trigger-url"

For **Linux** set `SPOTIFY_LINUX_PLAYING_METHOD` to one of the following values:
- "**dbus-send**" (most common one, **default**)
- "qdbus" (try if dbus-send does not work)
- "trigger-url"

For **Windows** set `SPOTIFY_WINDOWS_PLAYING_METHOD` to one of the following values:
- "**start-uri**" (recommended, **default**)
- "spotify-cmd"
- "trigger-url"

The recommended defaults should work for most people.

## Progress Indicator

If you want to see a real-time progress indicator showing the exact minute and second of the track the user is currently listening to:
- set `PROGRESS_INDICATOR` to `True`
- or use the `-p` flag

```sh
lastfm_monitor <lastfm_username> -p
```

![lastfm_monitor_progress_indicator](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/assets/lastfm_monitor_progress_indicator.png)

For this functionality to work correctly, it is suggested to set the active check interval (`LASTFM_ACTIVE_CHECK_INTERVAL` / `-k` flag) to a low value (such as 2-5 seconds).

## Getting Track Duration from Spotify

If you want the tool to fetch the track duration from Spotify instead of Last.fm, which very often reports the wrong duration (or none at all):
- set `USE_TRACK_DURATION_FROM_SPOTIFY` to `True`
- or use the `-r` flag

```sh
lastfm_monitor <lastfm_username> -r
```

Track duration is resolved through the [Spotify metadata backends](configuration.md#spotify-metadata-backends). The official OAuth app Web API is tried first when credentials are configured. The anonymous web-player backend runs next. Last.fm duration is used only if both Spotify backends fail or return incomplete metadata.

You will be able to tell if the track duration comes from Spotify as it has an S* suffix at the end (e.g. **3 minutes 42 seconds S\***), while those coming from Last.fm have an L* (e.g. **2 minutes 13 seconds L\***).

You can disable showing the track duration marks (L* S*) via the `-q` flag.

```sh
lastfm_monitor <lastfm_username> -r -q
```

Duration marks are not displayed if the functionality to retrieve track duration from Spotify is disabled.

## Private Mode Detection in Spotify

The tool includes functionality to detect when private mode is potentially used in Spotify and even estimates the duration of its usage. It is enabled by default and is not configurable.

It is not 100% accurate. I have observed that when private mode is used, especially for extended periods, it often results in many duplicate entries being created in a Last.fm account after private mode is disabled. This leads to different tracks having the same start timestamp.

I suspect this is related to a bug in Spotify and mainly occurs when the user has Spotify on multiple devices.

However, keep in mind that this is not 100% accurate. I have observed duplicate entries even without private mode, but in such cases, the number of duplicate entries is limited. Therefore, do not treat it as something completely certain, but it is a pretty good indicator that private mode was used.

![lastfm_monitor_private_mode](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/assets/lastfm_monitor_private_mode.png)

## Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets active/inactive or new offline entries show up (-a, -i, -f) |
| USR2 | Toggle email notifications for every song (-j) |
| URG  | Toggle showing of progress indicator (-p) |
| CONT | Toggle email notifications for tracked songs (-t) |
| PIPE | Toggle email notifications when user plays song on loop (-x) |
| TRAP | Increase the inactivity check timer (by 30 seconds) (-o) |
| ABRT | Decrease the inactivity check timer (by 30 seconds) (-o) |
| HUP | Reload secrets from .env file |

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "lastfm_monitor <lastfm_username>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

## Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to color logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using `grc` tool.

Example:

```sh
grc tail -F -n 100 lastfm_monitor_<username>.log
```
