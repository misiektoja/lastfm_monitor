# Setup & First Run

## Quick Start

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
