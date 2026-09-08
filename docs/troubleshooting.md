# Troubleshooting

## When Something Goes Wrong

When the tool cannot continue, it reports the failure in the same three-line form: what went wrong, what to do about it and a link to the page that covers it.

```text
* Error: The monitored user hides their recent listening information
To fix: Ask the user to turn off 'Hide recent listening information' in their Last.fm privacy settings
Guide: https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/#user-privacy-settings
```

Two failures stop a first run more often than the rest.

**The monitored account hides its listening history.** Last.fm answers with error code 17, *'Login: User required to be logged in'*. The monitored user has to disable **Hide recent listening information** in their [Last.fm Privacy Settings](https://www.last.fm/settings/privacy). See [User Privacy Settings](setup-and-first-run.md#user-privacy-settings).

**The API credentials are missing or wrong.** A missing key stops the run before monitoring starts. A key Last.fm rejects, including a suspended one and a wrong shared secret, is reported as *Last.fm rejected the configured API key or shared secret*. Save a working pair through the hidden prompt rather than passing it on the command line:

```sh
lastfm_monitor --set-lastfm-credentials
```

Each notification channel has a command that delivers one real message, so you can tell a broken channel from a channel that has nothing to say:

```sh
lastfm_monitor --send-test-email
lastfm_monitor --send-test-webhook
```

Both run without a username and without starting monitoring.

A configuration file that cannot be parsed stops the run and names the file, the line and the reason. Configuration files are read as data rather than executed, so only documented `SETTING = value` lines with plain literal values are accepted.

Failures that clear on their own, such as a Last.fm outage or a rate limit, say that the tool keeps retrying. Failures that need you, such as a rejected key or a hidden profile, do not.

## Debug Output

`--debug` traces what the tool is doing in timestamped `[DEBUG HH:MM:SS]` lines:

```sh
lastfm_monitor <lastfm_username> --debug
```

Traced operations include where each secret resolved from, the Last.fm polling cycle, the sleep interval before each check, offline entries being detected, CSV initialization, email delivery attempts and the full [Spotify metadata](configuration.md#spotify-metadata-backends) path: server time, anonymous web-player token requests and refreshes, persisted-query hash discovery, OAuth app token retrieval and every search and match decision that resolves a track ID and duration.

That last group is the reason to reach for `--debug` first when track durations or automatic playback are not working. The trace names which backend answered, which candidate tracks came back and why one was chosen or rejected.

Debug mode can also be turned on permanently with the `DEBUG_MODE` configuration setting. The `--debug` flag wins over a configuration file that sets `DEBUG_MODE = False`.

Debug output is written to the terminal and to the log file.

Error text is redacted before it is printed. Configured secrets are replaced wherever they appear, as are `SETTING = value` lines for any of the secret settings, `Authorization: Bearer` and `Authorization: Basic` headers, signed Last.fm request parameters such as `api_key` and `api_sig`, and Discord webhook URLs. Redaction is a safety net rather than a guarantee, so still read the output before pasting it into a bug report.
