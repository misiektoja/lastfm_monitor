# Setup & First Run

## Quick Start

Run the tool with no arguments to see the commands to start from, and to be offered the guided setup:

```sh
lastfm_monitor
```

## Guided Setup

The wizard asks a few questions and writes a ready-to-run configuration:

```sh
lastfm_monitor --setup
```

It covers the monitored user, the polling intervals, the Last.fm API credentials, optional Spotify track
details, follower and profile tracking, the files a run writes, email notifications and webhook alerts.

Things worth knowing before you run it:

- Nothing is written until you choose **Save** on the summary. Discarding leaves both destination files untouched.
- Secrets go to the dotenv file. Non-secret settings go to the config file. An existing config is replaced only after you agree, and a timestamped backup is kept.
- Credentials are checked while you enter them: the Last.fm pair against Last.fm, the mail server through a real sign-in that sends nothing.
- A credential already saved is offered for replacement before the hidden prompt, so nothing is typed only to be discarded. Declining keeps the saved value without displaying it.
- For an ntfy webhook the topic name alone is enough when the topic lives on `ntfy.sh`: typing `my-topic` saves `https://ntfy.sh/my-topic`. Any other host needs its complete HTTPS topic URL.
- Every answer it cannot use is explained and offered again. Declining the retry moves on: a value question keeps the default it showed, a channel such as email or webhook is switched off with its alerts, and a required answer ends its section.
- The summary can be reviewed section by section, so one answer can be changed without repeating the rest. Re-entering a section starts it over from the settings the run began with.
- After saving it offers [Doctor Preflight](troubleshooting.md#doctor-preflight), then prints the commands that check and start monitoring.

Choose the destinations with `--config-file` and `--env-file`. Both need a writable path, so `none` is refused:

```sh
lastfm_monitor --setup --config-file ~/lastfm_monitor.conf --env-file ~/.env-lastfm_monitor
```

The wizard needs an interactive terminal. In a script or a container use `--generate-config` and edit the files instead.

- Grab your [Last.fm API Key and Shared Secret](#lastfm-api-key-and-shared-secret) and track the `lastfm_username` music activities:

```sh
lastfm_monitor <lastfm_username> -u "your_lastfm_api_key" -w "your_lastfm_api_secret"
```

Or if you installed [manually](installation.md#manual-installation):

```sh
python3 lastfm_monitor.py <lastfm_username> -u "your_lastfm_api_key" -w "your_lastfm_api_secret"
```

To get the list of all supported command-line arguments / flags:

```sh
lastfm_monitor --help
```

To check the setup before the first run, without writing anything:

```sh
lastfm_monitor --doctor <lastfm_username>
```

See [Doctor Preflight](troubleshooting.md#doctor-preflight) for what it reports.

## Last.fm API Key and Shared Secret

- Create your Last.fm `API key` and `Shared secret` at: [https://www.last.fm/api/account/create](https://www.last.fm/api/account/create)
   - Or get your existing credentials from: [https://www.last.fm/api/accounts](https://www.last.fm/api/accounts)

- Provide the `LASTFM_API_KEY` and `LASTFM_API_SECRET` secrets using one of the following methods:
   - Recommended: run `lastfm_monitor --set-lastfm-credentials` and enter both values through hidden prompts
   - Pass it at runtime with `-u` / `--lastfm-api-key` and `-w` / `--lastfm-secret`
   - Set it as an [environment variable](configuration.md#storing-secrets) (e.g. `export LASTFM_API_KEY=...; export LASTFM_API_SECRET=...`)
   - Add it to [.env file](configuration.md#storing-secrets) (`LASTFM_API_KEY=...` and `LASTFM_API_SECRET=...`) for persistent use
   - Fallback: hard-code it in the code or config file

If you store the `LASTFM_API_KEY` and `LASTFM_API_SECRET` in a dotenv file you can update their values and send a `SIGHUP` signal to the process to reload the file with the new secret values without restarting the tool. More info in [Storing Secrets](configuration.md#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

The hidden setup command keeps both values out of shell history and process listings:

```sh
lastfm_monitor --set-lastfm-credentials
```

## User Privacy Settings

In order to monitor Last.fm user activity, proper privacy settings need to be enabled on the monitored user account.

The user should go to [Last.fm Privacy Settings](https://www.last.fm/settings/privacy).

The **Hide recent listening information** setting should be disabled.

Otherwise you will get this error message returned by the `pyLast` library: *'Login: User required to be logged in'*.
