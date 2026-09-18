# Setup & First Run

<a id="run-the-setup-wizard"></a>
## Run the setup wizard

Already installed? Run the setup command below for your installation and follow the prompts. Otherwise, start with [Installation](installation.md).

Setup asks who to monitor, the Last.fm API credentials, how often to check and which alerts and output files you want. You can review your answers before saving. Regular settings go in `lastfm_monitor.conf` and private values go in `.env`. Keep `.env` private.

Press Enter to accept a default or Ctrl+C to cancel. Cancelling before saving leaves your files untouched. Cancelling after saving keeps the saved settings. For changes to an existing setup, see [Configuration File](configuration.md#configuration-file).

After saving, follow the offered Doctor checks and monitoring steps.

=== "PyPI"

    ```sh
    lastfm_monitor --setup
    ```

=== "Manual Python script on macOS or Linux"

    ```sh
    python3 lastfm_monitor.py --setup
    ```

=== "Manual Python script on Windows"

    ```powershell
    python lastfm_monitor.py --setup
    ```

A **target** is the Last.fm user whose scrobbles you want to monitor. The wizard asks for your Last.fm API key and shared secret. See [Last.fm API Key and Shared Secret](#lastfm-api-key-and-shared-secret) for how to get them.

The polling prompts accept plain seconds or the `s`, `m`, `h` and `d` units. They show both the seconds and a readable form of the default.

With a saved target, running Last.fm Monitor without a target starts monitoring that user. If no target is saved, an interactive no-argument run offers setup.

<a id="before-you-start"></a>
## Before you start

You need three things before the first monitoring run:

1. A Last.fm target. Use the Last.fm username of the account you want to monitor.
2. A Last.fm API key and shared secret. See [Last.fm API Key and Shared Secret](#lastfm-api-key-and-shared-secret).
3. The monitored account must publish its recent listening. See [User Privacy Settings](#user-privacy-settings).

<a id="lastfm-api-key-and-shared-secret"></a>
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

<a id="user-privacy-settings"></a>
## User Privacy Settings

In order to monitor Last.fm user activity, proper privacy settings need to be enabled on the monitored user account.

The user should go to [Last.fm Privacy Settings](https://www.last.fm/settings/privacy).

The **Hide recent listening information** setting should be disabled.

Otherwise you will get this error message returned by the `pyLast` library: *'Login: User required to be logged in'*.

<a id="not-sure-which-command-you-need"></a>
## Not sure which command you need?

| I want to... | Run this |
| --- | --- |
| Set up Last.fm Monitor for the first time | Use the setup command for your installation above |
| Start monitoring with existing credentials | `lastfm_monitor <lastfm_username>`, where the target is a Last.fm username |
| Start the user saved in `LASTFM_USERNAME` | `lastfm_monitor --config-file lastfm_monitor.conf` |
| Check credentials, connectivity and one user | `lastfm_monitor --doctor <lastfm_username>` |
| Most securely enter or replace the Last.fm API key and shared secret | Run `lastfm_monitor --set-lastfm-credentials` and enter both at the hidden prompts |
| Save optional Spotify credentials for track details | Run `lastfm_monitor --set-spotify-credentials` |
| Save an SMTP password for email alerts | Run `lastfm_monitor --set-smtp-password` |
| Send a test email | Run `lastfm_monitor --send-test-email` |
| Set up webhook alerts | Run the setup wizard and choose webhook alerts |
| Save a new webhook URL | Run `lastfm_monitor --set-webhook-url` |
| Send a test webhook | Run `lastfm_monitor --send-test-webhook` |
| List the ten most recent tracks | `lastfm_monitor <lastfm_username> -l -n 10` |
| Alert on the tracks and albums listed in a file | `lastfm_monitor <lastfm_username> -s tracks.txt` |
| Write every scrobble to a CSV file | `lastfm_monitor <lastfm_username> -b scrobbles.csv` |
| Use a specific configuration and secrets file | `lastfm_monitor --config-file lastfm_monitor.conf --env-file .env <lastfm_username>` |
| List every supported command-line flag | `lastfm_monitor --help` |

<a id="run-individual-commands"></a>
## Run Individual Commands

The examples below use PyPI. For a manual script, replace `lastfm_monitor` with `python3 lastfm_monitor.py` on macOS or Linux. Use `python lastfm_monitor.py` on Windows and run it from the directory holding the script or give its full path. See [Command Format by Installation Method](usage.md#command-format-by-installation-method).

Throughout this page `<lastfm_username>` means the Last.fm username you want to monitor.

<a id="save-the-lastfm-credentials"></a>
### Save the Last.fm credentials

To configure credentials without the wizard, `--set-lastfm-credentials` is the recommended and most secure entry method. It reads the API key and shared secret through hidden prompts, so neither value appears on screen or in the command line, then saves them as `LASTFM_API_KEY` and `LASTFM_API_SECRET`. Replacing existing values requires confirmation and unrelated `.env` settings are preserved. Run `--doctor` afterwards to confirm Last.fm accepts them.

```sh
lastfm_monitor --set-lastfm-credentials
```

Use `--env-file PATH` to select another `.env` file. The `-u` and `-w` options still work, but their values may appear in shell history or process listings.

Spotify track details are optional. Save those credentials the same way:

```sh
lastfm_monitor --set-spotify-credentials
```

See [Spotify Metadata Backends](configuration.md#spotify-metadata-backends) for what they add and when they are needed.

<a id="save-notification-credentials"></a>
### Save notification credentials

The SMTP password is entered through a hidden prompt, checked against the mail server and saved as `SMTP_PASSWORD` in `.env`:

```sh
lastfm_monitor --set-smtp-password
```

A webhook URL is the private address used to deliver notifications. Treat it like a password because anyone who has it may be able to post through it. Follow the [webhook setup steps](configuration.md#webhook-settings) then save the link:

```sh
lastfm_monitor --set-webhook-url
```

The link is entered through a hidden prompt and saved as `WEBHOOK_URL` in `.env`. This command only saves the link. It does not turn on webhook alerts or send a message. See [Webhook Settings](configuration.md#webhook-settings) to choose your alerts then run `lastfm_monitor --send-test-webhook` to test them.

<a id="start-monitoring"></a>
### Start monitoring

The first example uses a positional username. The second uses a saved `LASTFM_USERNAME`:

```sh
lastfm_monitor <lastfm_username>
lastfm_monitor --config-file lastfm_monitor.conf
```

For a [manual script](installation.md#install-the-manual-script):

```sh
python3 lastfm_monitor.py <lastfm_username>
```

To check the setup before the first run, without writing anything:

```sh
lastfm_monitor --doctor <lastfm_username>
```

See [Doctor Preflight](troubleshooting.md#doctor-preflight) for what it reports.

To see all supported command-line arguments and flags:

```sh
lastfm_monitor --help
```

<a id="next-step"></a>
## Next Step

Run [Doctor](troubleshooting.md#doctor-preflight) before an unattended run to confirm credentials, connectivity and notification settings.

With credentials saved and a first run working, continue to [Configuration](configuration.md) for the monitored user, Spotify metadata backends, SMTP, webhooks and secrets. See [Usage](usage.md) for command formats, monitoring, listing commands, notifications and output files.
