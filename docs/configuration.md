# Configuration

Examples on this page use the PyPI command `lastfm_monitor`. Manual script users should keep the shown options and use the matching prefix under [Command Format by Installation Method](usage.md#command-format-by-installation-method).

<a id="configuration-file"></a>
## Configuration File

You can pass most settings as command-line options or save them in a configuration file for later runs.

The easiest way to create this file is `lastfm_monitor --setup`.

To edit every available setting yourself, generate a default configuration file:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
lastfm_monitor --generate-config > lastfm_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
lastfm_monitor --generate-config lastfm_monitor.conf
```

> **Windows PowerShell:** Pass the filename directly to `--generate-config`. PowerShell redirection can write UTF-16, which the tool rejects with a "null bytes" error.

When the named file already exists, `--generate-config` asks before replacing it and keeps a timestamped `.bak` backup next to it. Add `--force` to replace it without the question.

The file contains a short explanation above each setting.

A configuration file is read as data, not executed. The tool accepts only `SETTING = value` lines where the name is one of the documented settings and the value is a plain literal such as a string, number, `True`, `False`, `None`, a list or a dictionary. Comments and blank lines are fine.

Imports, function calls, expressions and unknown settings are rejected with the setting and line number to correct.

If the same setting appears in more than one place, the item later in this list wins:

1. Built-in defaults
2. The discovered or explicitly selected configuration file
3. Values from the selected `.env` file
4. Secret environment variables
5. Command-line options

By default the tool looks for a configuration file named `lastfm_monitor.conf` in the current directory, the home directory (`~`) and the script directory. Use `--config-file` to name another location or `--config-file none` to disable automatic config discovery for one run.

<a id="monitored-target"></a>
## Monitored Target

The Last.fm username is a positional argument. It is required to start monitoring:

```sh
lastfm_monitor <lastfm_username>
```

Use the username as it appears in the profile URL, `https://www.last.fm/user/<lastfm_username>`.

To stop repeating it, save it in the configuration file:

```ini
LASTFM_USERNAME = "lastfm_username"
```

Then `lastfm_monitor` alone starts monitoring that user. A positional argument still wins, so you can watch someone else for one run without editing the file:

```sh
lastfm_monitor other_username
```

<a id="spotify-metadata-backends"></a>
## Spotify Metadata Backends

The [track duration feature](usage.md#getting-track-duration-from-spotify) and [automatic playback feature](usage.md#automatic-playback-of-listened-tracks-in-the-spotify-client) both need Spotify track metadata:

- Duration lookup needs the Spotify track duration
- Automatic playback needs the Spotify track ID so the local Spotify client knows which track to play

Spotify app credentials are not mandatory for either feature. The tool can obtain the required metadata from the anonymous web-player backend. If you configure OAuth app credentials, the official Spotify Web API is tried first.

Version 2.5 uses this metadata order:

1. Official Spotify Web API search through optional OAuth app Client Credentials
2. Anonymous web-player search and Pathfinder `getTrack` metadata
3. Last.fm duration as the final fallback

<a id="optional-spotify-oauth-app-setup"></a>
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

The tool fetches Spotify server time before generating the required v61 TOTP parameters. The v61 version and cipher bytes ship as the `SPOTIFY_TOTP_VERSION` and `SPOTIFY_TOTP_SECRET_CIPHER_BYTES` config options. If Spotify rotates the secret you can update them from the config file using the [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_secret_grabber.py) tool without a code change.

Spotify metadata supplies the track duration, title, artists, album, URI and external URL. Last.fm duration remains the final fallback when Spotify web metadata is unavailable or incomplete.

With `-r`, a successful duration from either Spotify backend is marked `S*`. Last.fm fallback duration is marked `L*`. Without `-r`, Last.fm remains the duration source while Spotify metadata can still resolve a track ID for `-g` playback.

<a id="smtp-settings"></a>
## SMTP Settings

Email notifications need SMTP server details for the sending account. Add them to `lastfm_monitor.conf` or use the setup wizard. Setup checks the login without sending an email. To replace only the password, run `lastfm_monitor --set-smtp-password`. Password entry is hidden and preserves spaces.

Send one test message to verify the settings:

```sh
lastfm_monitor --send-test-email
```

Configure `SMTP_HOST`, `SMTP_USER`, `SENDER_EMAIL` and `RECEIVER_EMAIL` before saving the password, since the sign-in needs them. An exported `SMTP_PASSWORD` wins over the saved one at startup.

<a id="webhook-settings"></a>
## Webhook Settings

Last.fm Monitor can send activity alerts through Discord or the native [ntfy publish API](https://docs.ntfy.sh/publish/). Webhook alerts work with or without email. Run `lastfm_monitor --setup`, choose webhook alerts and select Discord or ntfy.

`WEBHOOK_PROVIDER` defaults to `"discord"`. Standard Discord and public `ntfy.sh` URLs are recognized automatically, including after a `SIGHUP` reload. Set the provider explicitly for a self-hosted ntfy server or a compatible endpoint. For one run, use `--webhook-provider discord` or `--webhook-provider ntfy`.

Set `WEBHOOK_ENABLED = True` in `lastfm_monitor.conf` then enable the events you want through the `WEBHOOK_*_NOTIFICATION` settings. Last.fm Monitor supports active, inactive, monitored track, every song, loop, offline entry, follower, following and error alerts. Matching command-line switches are listed under [Webhook Notifications](usage.md#webhook-notifications).

`WEBHOOK_ERROR_NOTIFICATION` covers both the alert a lasting monitoring failure sends and the recovery alert that follows when it clears. `--no-webhook-error-notify` switches off the pair for one run, and `ERROR_NOTIFICATION` with `-e` / `--no-error-notify` does the same for email. See [Connection Problems](troubleshooting.md#connection-problems) for what the failure alerts report.

Test delivery without starting monitoring:

```sh
lastfm_monitor --send-test-webhook
```

<a id="ntfy"></a>
### ntfy

For ntfy.sh or a self-hosted ntfy server:

1. Choose a hard-to-guess topic such as `lastfm-monitor-long-random-value`.
2. In the setup wizard, paste either the bare ntfy.sh topic name or its complete topic URL such as `https://ntfy.sh/lastfm-monitor-long-random-value`. A bare topic name is expanded to an ntfy.sh URL. For a self-hosted server, use the complete HTTPS topic URL.
3. Public `ntfy.sh` URLs are recognized automatically. Set the provider in `lastfm_monitor.conf` for a self-hosted ntfy server:

```ini
WEBHOOK_PROVIDER = "ntfy"
```

4. When configuring without the setup wizard, save the complete topic URL privately:

```sh
lastfm_monitor --set-webhook-url
```

The ntfy provider needs no template. Last.fm Monitor sends the alert body as a native UTF-8 ntfy message and sends the alert subject as its title. Long messages are truncated with a visible marker so they remain notifications rather than attachments.

Last.fm Monitor does not attach artwork to ntfy alerts because it does not retrieve a trusted artwork source. Webhook delivery remains text-only.

For compact activity notifications on phones and smartwatches, enable the short ntfy format in `lastfm_monitor.conf`:

```ini
NTFY_SHORT = True
```

The default is `False`. This setting affects only ntfy. Discord and email content remain unchanged.

For a protected topic, the setup wizard can collect an ntfy access token through a hidden prompt. It saves the token in `.env` without displaying it. For manual setup, add the token to `.env`:

```ini
NTFY_ACCESS_TOKEN="tk_your_ntfy_access_token"
```

Last.fm Monitor sends this value as `Authorization: Bearer <token>`. `NTFY_ACCESS_TOKEN` takes precedence over an `Authorization` entry in `WEBHOOK_HEADERS`.

For compatibility with advanced webhook integrations, custom headers are also supported in `lastfm_monitor.conf`:

```ini
WEBHOOK_HEADERS = {
    "X-Webhook-Title": "{title}",
}
```

Header values support the same placeholders as `WEBHOOK_TEMPLATE`. They must be strings without line breaks. Headers apply to both Discord and ntfy. Prefer `NTFY_ACCESS_TOKEN` in `.env` for Bearer authentication. Basic authentication is available through a custom `Authorization` header. Customize ntfy delivery further through `WEBHOOK_HEADERS`, for example `X-Priority` or `X-Tags`.

<a id="discord"></a>
### Discord

If you are new to Discord, follow these steps to get your private webhook URL:

1. Open your Discord server and choose the channel that should receive the alerts.
2. Click **Edit Channel** then open **Integrations** > **Webhooks**.
3. Click **New Webhook**, choose a name if you want then click **Copy Webhook URL**.
4. Return to the terminal and run:

```sh
lastfm_monitor --set-webhook-url
```

Paste the copied link at the hidden prompt. The command validates that the destination is a complete HTTPS URL then updates only `WEBHOOK_URL` in `.env`, so it does not appear in your command history. Replacing an existing value requires confirmation. Use `--env-file PATH` to select another private settings file. Treat this link like a password because anyone who has it can post through it.

For a one-run override, `--webhook-url URL` uses a complete HTTPS destination without changing `.env` and enables webhooks for that run. The URL may remain visible in shell history or process listings, so prefer `--set-webhook-url` for normal setup.

Keep the default provider in `lastfm_monitor.conf`:

```ini
WEBHOOK_PROVIDER = "discord"
```

Discord alerts carry the same emphasis as the HTML email, since Discord renders markdown in an embed. Bold values stay bold and links stay clickable. Only Discord gets that wording: ntfy receives the plain body, because it would show the markers literally.

<a id="advanced-discord-format-customization"></a>
### Advanced Discord-format customization

`WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` change the sender name and HTTPS avatar for Discord-format payloads:

```ini
WEBHOOK_USERNAME = "Last.fm Monitor"
WEBHOOK_AVATAR_URL = "https://example.com/path/avatar.png"
```

`WEBHOOK_TEMPLATE` controls the Discord-format request body. The generated configuration contains the safe default template. It supports these placeholders:

- `{title}`
- `{description}`
- `{version}`
- `{image_url}`
- `{fields}` and `{fields_str}`
- `{color}`
- `{timestamp}`
- `{username}`
- `{avatar_url}`

Discord templates must produce a JSON object. Use a dictionary or a JSON string encoding an object, including legacy strings with doubled object braces. Lists, non-JSON strings and unsupported placeholders are rejected before delivery. Alert text is kept literal and all payloads replace `allowed_mentions` with `{"parse": []}` so alert text cannot trigger Discord mentions. Reloaded settings apply to the next delivery.

`WEBHOOK_TRANSFORMS` applies string methods to shared placeholder values before the template and headers are rendered:

```ini
WEBHOOK_TRANSFORMS = [
    ("title", "upper"),
    ("description", "replace", "**", ""),
    ("description", "strip"),
]
```

The tuple format is `(field_to_target, method_name, *optional_arguments)`. Invalid templates, avatar URLs, transforms or formatted headers fail before a webhook request is attempted. `WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` apply only to the Discord request format and are ignored when `WEBHOOK_PROVIDER` is `"ntfy"`. ntfy continues to use its native publish API while transformations and header placeholders use the same shared title and description values.

Topics on the public ntfy.sh service are public unless protected through an account reservation. Treat an unprotected topic name like a password and do not reuse the example topic above.

<a id="storing-secrets"></a>
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

Replaced secrets are not backed up. Keep your own copy if you need one.

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

<a id="tls-verification"></a>
## TLS Verification

Every connection the tool makes verifies the server's certificate: Last.fm, the Spotify metadata backends, webhook delivery, the mail server handshake and the startup connectivity check.

On a network that intercepts TLS with its own certificate authority, that verification fails and the error reads like a bug in the tool. Set `VERIFY_SSL` to `False` to accept the intercepting certificate:

```python
VERIFY_SSL = False
```

The tool then says so at startup, because an intercepted connection can no longer be told apart from the real service. Leave it at the default `True` everywhere else.

<a id="terminal-colours"></a>
## Terminal Colours

`COLORED_OUTPUT` controls whether terminal output is coloured. It defaults to `True` and is read before the first line is printed, so a configured value applies from the version line onwards. `--no-color` disables colour for one run. Colour also switches itself off when output is redirected or piped, when `TERM` is unset or `dumb` and when the standard [`NO_COLOR`](https://no-color.org/) environment variable is set. Log files are always written with the escape sequences stripped.

The `--help` screen is coloured too. Group headings, option names, the values those options take, the example commands and the comments above them each get their own colour, so the screen can be scanned instead of read.

`COLOR_THEME` overrides individual colours. It is merged over the built-in theme, so name only the parts you want to change:

```ini
COLOR_THEME = { "track": "bright_magenta bold", "username": "green" }
```

Generated configuration files ship this block commented out, so the built-in defaults apply and a later change to them reaches you. Overrides you added are written back as a real block when setup rebuilds the file, so they are not lost. Uncomment only the lines you want to change and the rest keep following the defaults.

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
| `help_heading` | The `--help` group headings and example task names |
| `help_usage` | The `usage:` label |
| `help_option` | Option names such as `--doctor` |
| `help_metavar` | The value each option takes, such as a path or a number of seconds |
| `help_placeholder` | Values to replace in the help examples |
| `help_command` | The commands in the help examples |
| `help_comment` | The `#` comment above each help example |
| `help_default` | The `(default: ...)` notes |

Warning and signal lines mark their opening word rather than being painted end to end, so the values inside them keep the colour that says what they are.

On Windows, install the optional `colorama` package for the best results in the classic Command Prompt. Windows Terminal needs nothing extra.

To colour saved log files when you view them later, see [Coloring Log Output with GRC](usage.md#coloring-log-output-with-grc).
