# Configuration

## Configuration File

Most settings can be configured via command-line arguments.

If you want to have it stored persistently, generate a default config template and save it to a file named `lastfm_monitor.conf`:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
lastfm_monitor --generate-config > lastfm_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
lastfm_monitor --generate-config lastfm_monitor.conf
```

> **IMPORTANT**: In Windows PowerShell, do not use `>` for this command. Some PowerShell versions write redirected text as UTF-16, which makes Last.fm Monitor report a "null bytes" error. Pass the filename to `--generate-config` so Last.fm Monitor writes a UTF-8 file itself.

When you include the filename, Last.fm Monitor writes the template directly as UTF-8. This avoids PowerShell changing the file encoding during redirection.

### Replacing an Existing Config

Passing a filename never replaces an existing file silently. On a terminal the tool asks first. Outside one, in a script or a container, it stops and names `--force`:

```sh
lastfm_monitor --generate-config lastfm_monitor.conf --force
```

Either way the previous file is copied to `lastfm_monitor.conf.<timestamp>.bak` before the new template is written, and the backup path is printed. Both files are readable only by their owner.

Shell redirection works differently: `> lastfm_monitor.conf` truncates the file before the tool starts, so nothing can back it up. Pass the filename when the destination already exists.

Edit the `lastfm_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

By default the tool looks for a configuration file named `lastfm_monitor.conf` in:

- current directory
- home directory (`~`)
- script directory

### The Monitored User

`LASTFM_USERNAME` in the config file saves the user to monitor, so the command needs no argument:

```sh
lastfm_monitor
```

A username passed on the command line overrides the saved one for that run. With neither, the tool prints the
welcome screen instead of starting.

If you saved it under a different name or in a different directory, select it with `--config-file`:

```sh
lastfm_monitor <lastfm_username> --config-file /path/lastfm_monitor_new.conf
```

To ignore any configuration file and run on the built-in defaults plus command-line flags, disable the search with `none`:

```sh
lastfm_monitor <lastfm_username> --config-file none
```

A path that does not exist is still an error. Only the literal `none` selects no file.

**New in v2.3:** The configuration file includes options to enable/disable music service URLs (Last.fm, Spotify, Apple Music, YouTube Music, Amazon Music, Deezer, Tidal) and lyrics service URLs (Genius, AZLyrics, Tekstowo.pl, Musixmatch, Lyrics.com) in console and email outputs.

**New in v2.5:** The [track duration](usage.md#getting-track-duration-from-spotify) and [automatic playback](usage.md#automatic-playback-of-listened-tracks-in-the-spotify-client) features use the official OAuth app Web API when optional app credentials are configured. The anonymous web-player backend is the new automatic fallback and requires no Spotify credentials.

## Spotify Metadata Backends

The [track duration feature](usage.md#getting-track-duration-from-spotify) and [automatic playback feature](usage.md#automatic-playback-of-listened-tracks-in-the-spotify-client) both need Spotify track metadata:

- Duration lookup needs the Spotify track duration
- Automatic playback needs the Spotify track ID so the local Spotify client knows which track to play

Spotify app credentials are not mandatory for either feature. The tool can obtain the required metadata from the anonymous web-player backend. If you configure OAuth app credentials, the official Spotify Web API is tried first.

Version 2.5 uses this metadata order:

1. Official Spotify Web API search through optional OAuth app Client Credentials
2. Anonymous web-player search and Pathfinder `getTrack` metadata
3. Last.fm duration as the final fallback

### Optional Spotify OAuth App Setup

Follow these steps if you want the official Spotify Web API to be the primary metadata backend:

1. Log in to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Select **Create app**
3. Enter an app name and description
4. For **Redirect URI**, enter `http://127.0.0.1:1234`
   - The Client Credentials flow does not redirect a user, but Spotify's app form requests a redirect URI
   - Use the numeric loopback address exactly as shown because Spotify does not allow `localhost`
5. Under the API selection, choose **Web API**
6. Accept Spotify's Developer Terms of Service and create the app
7. Open the app settings
8. Copy the **Client ID**
9. Select **View client secret** and copy the **Client Secret**

Spotify currently requires the owner of a Development Mode app to have an active Spotify Premium subscription. See Spotify's [February 2026 Development Mode migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) for the current restrictions.

Provide `SP_CLIENT_ID` and `SP_CLIENT_SECRET` using one of these methods:

- Recommended: run `lastfm_monitor --set-spotify-credentials` and enter both values through hidden prompts
- Pass them at runtime with `-z` / `--spotify-creds`
  - Use the `SP_CLIENT_ID:SP_CLIENT_SECRET` format with a colon between the values
- Set them as [environment variables](#storing-secrets), for example `export SP_CLIENT_ID=...` and `export SP_CLIENT_SECRET=...`
- Add them to a [dotenv file](#storing-secrets) as `SP_CLIENT_ID=...` and `SP_CLIENT_SECRET=...`
- Add them to `lastfm_monitor.conf`
- As a final fallback, hard-code them in `lastfm_monitor.py`

Command-line example:

```sh
lastfm_monitor <lastfm_username> -z "your_spotify_app_client_id:your_spotify_app_client_secret"
```

The `-z` value may remain visible in shell history or process listings. Prefer the hidden setup command for persistent credentials:

```sh
lastfm_monitor --set-spotify-credentials
```

The tool refreshes OAuth app access tokens automatically. The token cache path is configured through `SP_TOKENS_FILE` and defaults to `.lastfm-monitor-oauth-app.json`. Set `SP_TOKENS_FILE` to an empty string to use memory-only caching.

If you store `SP_CLIENT_ID` and `SP_CLIENT_SECRET` in a dotenv file, you can update them and send `SIGHUP` to reload the values without restarting the tool. See [Storing Secrets](#storing-secrets) and [Signal Controls](usage.md#signal-controls-macoslinuxunix).

The OAuth backend relies on Spotipy's expiration-aware Client Credentials cache. It does not call a separate Web API endpoint to validate tokens. If credentials are absent, token retrieval fails or OAuth search returns incomplete metadata, the anonymous backend runs automatically.

The tool fetches Spotify server time before generating the required v61 TOTP parameters. It caches the anonymous token until its expiration window and discovers the current persisted-query hashes from the active web-player bundle. An HTTP 401 refreshes the token once. A rejected persisted query refreshes its hash once.

The v61 version and cipher bytes ship as the `SPOTIFY_TOTP_VERSION` and `SPOTIFY_TOTP_SECRET_CIPHER_BYTES` config options. If Spotify rotates the secret you can update them from the config file using the [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_secret_grabber.py) tool without a code change.

Spotify metadata supplies the track duration, title, artists, album, URI and external URL. Last.fm duration remains the final fallback when Spotify web metadata is unavailable or incomplete.

With `-r`, a successful duration from either Spotify backend is marked `S*`. Last.fm fallback duration is marked `L*`. Without `-r`, Last.fm remains the duration source while Spotify metadata can still resolve a track ID for `-g` playback.

## SMTP Settings

If you want to use email notifications functionality, configure SMTP settings in the `lastfm_monitor.conf` file.

Save the password itself through a hidden prompt instead of editing the dotenv file by hand:

```sh
lastfm_monitor --set-smtp-password
```

The command signs in to the configured mail server and writes the password only if the server accepts it. Nothing is sent. Configure `SMTP_HOST`, `SMTP_USER`, `SENDER_EMAIL` and `RECEIVER_EMAIL` first, since the sign-in needs them.

Verify your SMTP settings by using `--send-test-email` flag (the tool will try to send a test email notification):

```sh
lastfm_monitor --send-test-email
```

The message arrives as `lastfm_monitor: test email` and its body names the command that sent it, so a mailbox holding alerts from more than one monitor says which is which. With the mail settings incomplete, the command reports what is missing instead of attempting a send.

## Webhook Settings

Webhook alerts work independently from email. Discord and ntfy are supported directly. Compatible services can use the Discord request format or the advanced payload and header settings.

First save the private destination through a hidden prompt:

```sh
lastfm_monitor --set-webhook-url
```

The command validates that the destination is a complete HTTPS URL then updates only `WEBHOOK_URL` in `.env`. Existing values require confirmation. Use `--env-file PATH` to select another private settings file.

Set `WEBHOOK_ENABLED = True` in `lastfm_monitor.conf` then choose `WEBHOOK_PROVIDER = "discord"` or `WEBHOOK_PROVIDER = "ntfy"`. Standard Discord and `ntfy.sh` URLs correct a mismatched configured provider automatically. This also applies to a `WEBHOOK_URL` replaced in the dotenv file and reloaded with `SIGHUP`: swapping a Discord webhook for an ntfy topic moves the provider with it, and the tool says so. A destination it does not recognize leaves the configured provider alone.

Enable the events you want through the `WEBHOOK_*_NOTIFICATION` settings. Last.fm Monitor supports active, inactive, monitored track, every song, loop, offline entry, follower, following and error alerts. Matching command-line switches are listed under [Webhook Notifications](usage.md#webhook-notifications).

Test delivery without starting monitoring:

```sh
lastfm_monitor --send-test-webhook
```

For automation or one-run tests, `--webhook-url URL` overrides the saved destination and enables webhooks. This value may remain visible in shell history or process listings, so `--set-webhook-url` is recommended for normal setup. `--webhook-provider {discord,ntfy}` overrides the request format for one run.

Protected ntfy topics can use `NTFY_ACCESS_TOKEN` from an environment variable or dotenv file. The token is sent with Bearer authentication. A custom `Authorization` header can also be supplied through `WEBHOOK_HEADERS`.

`WEBHOOK_USERNAME`, `WEBHOOK_AVATAR_URL`, `WEBHOOK_TEMPLATE`, `WEBHOOK_TRANSFORMS` and `WEBHOOK_HEADERS` provide the same Discord-format customization model as Spotify Monitor. Header values and template values support placeholders such as `{title}`, `{description}`, `{version}`, `{color}`, `{timestamp}`, `{username}` and `{avatar_url}`. `NTFY_SHORT = True` uses compact activity text on smaller screens without changing Discord or email content.

`WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` apply only to Discord and are ignored when `WEBHOOK_PROVIDER` is `"ntfy"`. The ntfy provider needs no template: it sends the alert body as a native ntfy message with the subject as its title. Customize ntfy delivery through `WEBHOOK_HEADERS` (for example `X-Priority` or `X-Tags`).

Last.fm Monitor does not attach artwork to ntfy alerts because it does not retrieve a trusted artwork source. Webhook delivery remains text-only.

### When Alerts Are Switched Off

If `WEBHOOK_ENABLED` is on but `WEBHOOK_URL` is not a complete HTTPS link, the tool says so once at startup and turns webhook alerts off, rather than failing on every alert for the rest of the run.

### When One Channel Fails

Email and webhook alerts are delivered independently, and the tool tracks which one arrived. If an error alert reaches the webhook but the mail server rejects the message, the next check sends the email again and leaves the webhook alone, so a failed channel is retried without delivering the same alert twice.

## Storing Secrets

It is recommended to store secrets like `LASTFM_API_KEY`, `LASTFM_API_SECRET`, `SP_CLIENT_ID`, `SP_CLIENT_SECRET`, `SMTP_PASSWORD`, `WEBHOOK_URL` or `NTFY_ACCESS_TOKEN` as either an environment variable or in a dotenv file.

The safest interactive entry methods write only the selected values to `.env` through hidden prompts:

```sh
lastfm_monitor --set-lastfm-credentials
lastfm_monitor --set-spotify-credentials
lastfm_monitor --set-webhook-url
lastfm_monitor --set-smtp-password
```

Each command accepts `--env-file PATH`. Existing values require confirmation and the update is atomic. `--env-file none` is rejected because these commands must save their values.

The dotenv file is replaced in one step and is never backed up, so a rotated secret is not left behind in a second file. Keep your own copy if you need one. A secret you switch off, such as the ntfy access token in the setup wizard, has its line removed rather than left as an empty value.

Answering `n` to the replacement question keeps the saved value and says so. Pressing Ctrl+C at any prompt cancels the command and exits with a failure code. Neither answer changes the dotenv file.

Whatever you store, the tool redacts these values from its error output and from the log file. A configured value shorter than 12 characters is only redacted in the forms that identify it as a secret, such as `SMTP_PASSWORD = ...` or an `Authorization` header, because replacing a short value everywhere would corrupt ordinary text that happens to contain the same word.

The same writer removes terminal control sequences from everything the tool prints. Track, artist and album names, display names and About Me text all come from Last.fm and can contain anything, including escape sequences that would clear your screen or retitle the window when a report or a log file is read. They are stripped before the text reaches the terminal and the log, and escaped before it reaches an HTML email body.

Set the needed environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

```sh
export LASTFM_API_KEY="your_lastfm_api_key"
export LASTFM_API_SECRET="your_lastfm_api_secret"
export SP_CLIENT_ID="your_spotify_app_client_id"
export SP_CLIENT_SECRET="your_spotify_app_client_secret"
export SMTP_PASSWORD="your_smtp_password"
export WEBHOOK_URL="your_private_webhook_url"
export NTFY_ACCESS_TOKEN="your_ntfy_access_token"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

Alternatively store them persistently in a dotenv file (recommended):

```ini
LASTFM_API_KEY="your_lastfm_api_key"
LASTFM_API_SECRET="your_lastfm_api_secret"
SP_CLIENT_ID="your_spotify_app_client_id"
SP_CLIENT_SECRET="your_spotify_app_client_secret"
SMTP_PASSWORD="your_smtp_password"
WEBHOOK_URL="your_private_webhook_url"
NTFY_ACCESS_TOKEN="your_ntfy_access_token"
```

By default the tool will auto-search for dotenv file named `.env` in current directory and then upward from it.

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
lastfm_monitor <lastfm_username> --env-file /path/.env-lastfm_monitor
```

 You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
lastfm_monitor <lastfm_username> --env-file none
```

As a fallback, you can also store secrets in the configuration file or source code.

### Which Source Wins

The same secret can be set in several places. The later source in this list wins:

1. the configuration file, or the settings in the script itself
2. the dotenv file
3. an exported environment variable
4. a command-line argument such as `-u`, `-w`, `-z` or `--webhook-url`

An exported variable therefore beats the dotenv file, which is what `python-dotenv`, systemd, Docker and a one-off `LASTFM_API_KEY=... lastfm_monitor ...` all assume. The exception is reloading with `SIGHUP`, where the edited dotenv file is exactly what has to take effect and so it wins.

A forgotten `export` can shadow the file invisibly, so `--debug` names each secret and the source it resolved from, never the value:

```text
[DEBUG 12:00:00] Secret resolution: name=LASTFM_API_KEY, source=environment, value=set, chars=32
[DEBUG 12:00:00] Secret resolution: name=SMTP_PASSWORD, source=dotenv file, value=set
[DEBUG 12:00:00] Secret sources: source=dotenv file, names=SMTP_PASSWORD
[DEBUG 12:00:00] Secret sources: source=environment, names=LASTFM_API_KEY
```

A secret still holding its `your_...` placeholder counts as unset and is left out. Lengths appear only for the secrets whose length the provider issues, never for a password you chose.

When a `--set-*` command or the setup wizard replaces a secret, it rewrites that one assignment in place and leaves every other line alone. A line you wrote as `export NAME=...` keeps its `export`, so a dotenv file you also source in a shell still exports it. A value you clear has its line removed rather than left empty.

## TLS Verification

Every connection the tool makes verifies the server's certificate: Last.fm, the Spotify metadata backends, webhook delivery, the mail server handshake and the startup connectivity check.

On a network that intercepts TLS with its own certificate authority, that verification fails and the error reads like a bug in the tool. Set `VERIFY_SSL` to `False` to accept the intercepting certificate:

```python
VERIFY_SSL = False
```

The tool then says so at startup, because an intercepted connection can no longer be told apart from the real service. Leave it at the default `True` everywhere else.

## Terminal Output

The tool clears the terminal when monitoring starts. Set `CLEAR_SCREEN` to `False` to keep whatever is already on the screen.

The screen is never cleared when output is redirected to a file or a pipe, in debug mode, or for a command that prints a result and exits, such as `--doctor`, `--help` and the test senders.

Two settings add detail to what a run prints. `VERBOSE_MODE` adds the decisions the run made and `DEBUG_MODE` adds timestamped technical traces. Both are off by default, both are independent of each other and both have a flag that wins over the file, `--verbose` and `--debug`. `DELIVERY_CONFIRMATIONS` is on by default and controls whether verbose mode confirms each delivered email and webhook alert. See [Verbose Output](troubleshooting.md#verbose-output) and [Debug Output](troubleshooting.md#debug-output).

## Terminal Colours

`COLORED_OUTPUT` controls whether terminal output is coloured. It defaults to `True` and is read before the first line is printed, so a configured value applies from the version line onwards. `--no-color` disables colour for one run. Colour also switches itself off when output is redirected or piped, when `TERM` is unset or `dumb` and when the standard [`NO_COLOR`](https://no-color.org/) environment variable is set. Log files are always written with the escape sequences stripped.

`COLOR_THEME` overrides individual colours. It is merged over the built-in theme, so name only the parts you want to change:

```ini
COLOR_THEME = { "track": "bright_magenta bold", "username": "green" }
```

Generated configuration files ship this block commented out, so the built-in defaults apply and a later change to them reaches you. Uncomment only the lines you want to change and the rest keep following the defaults.

A value combines one colour with any number of style attributes, separated by spaces or `+`, for example `"bright_cyan bold"`, `"red underline"` or `"bright_magenta bold underline"`. An empty string leaves that part uncoloured.

| Colours | Styles |
| --- | --- |
| `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` and the matching `bright_` variants such as `bright_red` | `bold`, `dim`, `underline`, `blink` |

Parts with the same name mean the same thing in the sibling monitors, so a `COLOR_THEME` block can be shared between them. Each tool lists only the parts it actually colours, so a few names appear in one and not the other.

| Theme key | Colours |
| --- | --- |
| `header` | The version line plus the Setup Wizard and Doctor headings |
| `section` | Commands the wizard tells you to run, the Doctor section names and the recent-tracks table header |
| `username` | Last.fm account names, including the `Target` row and the follower and following listings |
| `id` | Machine identifiers in debug traces, such as a Spotify track ID |
| `status_active` | `ACTIVE`, `PRIVATE MODE`, `RESUMED` and `LOOP` |
| `status_inactive` | `INACTIVE`, `SKIPPED` and `PAUSED` |
| `status_offline` | `OFFLINE` |
| `artist` | The Artist column of the recent-tracks table |
| `track` | `Track:` rows and the Title column |
| `album` | `Album:` rows and the Album column |
| `duration` | Track durations and elapsed times |
| `status_change` | The `CONT` marker on a resumed track |
| `timestamp_label` | The `Timestamp:` label. Empty by default, so the label stays plain like in the sibling monitors |
| `timestamp_value` | The timestamp value |
| `info` | `To fix:` lines, setup prompts and the Doctor guide line |
| `warning` | The `Warning:` opening word, the Doctor `WARN` marker and setup cancellations |
| `error` | Error lines and the Doctor `FAIL` marker |
| `signal` | The name of a signal a handler reports |
| `email`, `webhook` | Notification delivery lines |
| `date`, `date_range` | Single dates and times, and date or hour ranges |
| `boolean_true`, `boolean_false` | `True` / `Enabled` and `False` / `Disabled` |
| `count_up`, `count_down` | Reported changes only, such as `from 10 to 12` and the `(+2)` / `(-2)` differences. A static count is left plain |
| `link` | URLs |

Warning and signal lines mark their opening word rather than being painted end to end, so the values inside them keep the colour that says what they are.

On Windows, install the optional `colorama` package for the best results in the classic Command Prompt. Windows Terminal needs nothing extra.

To colour saved log files when you view them later, see [Coloring Log Output with GRC](usage.md#coloring-log-output-with-grc).

## Check Intervals

If you want to customize music polling intervals, use `-k` and `-c` flags (or corresponding configuration options):

```sh
lastfm_monitor <lastfm_username> -k 2 -c 10
```

* `LASTFM_ACTIVE_CHECK_INTERVAL`, `-k`: check interval when the user is online, i.e. currently playing (seconds)
* `LASTFM_CHECK_INTERVAL`, `-c`: check interval when the user is considered offline, i.e. not playing music (seconds)

If you want to change the time required to mark the user as inactive (the timer starts once the user stops playing the music), use `-o` flag (or `LASTFM_INACTIVITY_CHECK` configuration option):

```sh
lastfm_monitor <lastfm_username> -o 120
```

Friend and profile tracking uses one separate check interval which you can set via the `FRIENDS_CHECK_INTERVAL` configuration option or `--friends-check-interval` flag. This timer covers followings, followers, the About Me bio and the display name. It is independent from the music polling intervals.

To avoid false notifications caused by transient Last.fm responses, friend and profile changes are only confirmed after a number of consecutive checks (default: 3). You can configure this via the `FRIENDS_CHANGE_COUNTER` option or `--friends-change-counter` flag. This setting also controls the threshold for suppressing repeated error messages.

You can also configure the retry timeout used when confirming transient changes or errors via `FRIENDS_RETRY_INTERVAL` configuration option or `--friends-retry-interval` flag.

### Liveness Reminder

While nothing changes, the tool prints one reminder that it is still running:

```
* Monitoring healthy for <lastfm_username>. The user is inactive with no activity change since the last check
Liveness check, timestamp:	Mon 08 Sep 2026, 09:15:05
```

The reminder is timed in seconds, so it arrives at the same rate whether the user is listening or not. Set `LIVENESS_CHECK_INTERVAL` to change it (default: 86400, i.e. 24 hours), or to 0 to switch it off.

Anything the tool prints about the user restarts the countdown, so a busy run stays quiet.
