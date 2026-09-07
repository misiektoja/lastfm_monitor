# Troubleshooting

## When Something Goes Wrong

Start by checking the two things that stop a first run most often.

**The monitored account hides its listening history.** Last.fm returns *'Login: User required to be logged in'* through the `pyLast` library. The monitored user has to disable **Hide recent listening information** in their [Last.fm Privacy Settings](https://www.last.fm/settings/privacy). See [User Privacy Settings](setup-and-first-run.md#user-privacy-settings).

**The API credentials are missing or wrong.** The tool reports `LASTFM_API_KEY (-u / --lastfm_api_key) value is empty or incorrect` and exits before monitoring starts. Confirm which value is in effect and where it came from, then save it through the hidden prompt rather than the command line:

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

## Debug Output

`--debug` traces what the tool is doing in timestamped `[DEBUG HH:MM:SS]` lines:

```sh
lastfm_monitor <lastfm_username> --debug
```

Traced operations include the Last.fm polling cycle, the sleep interval before each check, offline entries being detected, CSV initialization, email delivery attempts and the full [Spotify metadata](configuration.md#spotify-metadata-backends) path: server time, anonymous web-player token requests and refreshes, persisted-query hash discovery, OAuth app token retrieval and every search and match decision that resolves a track ID and duration.

That last group is the reason to reach for `--debug` first when track durations or automatic playback are not working. The trace names which backend answered, which candidate tracks came back and why one was chosen or rejected.

Debug mode can also be turned on permanently with the `DEBUG_MODE` configuration setting. The `--debug` flag wins over a configuration file that sets `DEBUG_MODE = False`.

Debug output is written to the terminal and to the log file. Read it before pasting it into a bug report.
