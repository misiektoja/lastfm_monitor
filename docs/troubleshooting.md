# Troubleshooting

## Doctor Preflight

`--doctor` runs every check the tool needs before monitoring can start, then reports what is ready and what is not. It writes no files, and the email and webhook delivery tests only run after you approve each one separately.

```sh
lastfm_monitor --doctor <lastfm_username>
```

Each row is one result:

```text
Authentication
[FAIL] Last.fm rejected the configured API key or shared secret
  Invalid API key - You must be granted a valid key by last.fm
  To fix: Save a working pair with 'lastfm_monitor --set-lastfm-credentials'
  Guide: https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/#lastfm-api-key-and-shared-secret
```

* `[PASS]` the check succeeded
* `[WARN]` monitoring can start, but something is switched off or unreachable
* `[FAIL]` monitoring cannot start until it is fixed
* `[SKIP]` the check did not run, usually because an earlier one failed

The report groups its rows into **Environment** for the Python version and the libraries in use, **Configuration** for the configuration and dotenv files in effect, where each secret came from and every file the run will write, **Authentication** for the Last.fm credentials, **Spotify metadata** for the metadata backend when track duration or playback is on, **Connectivity** for the endpoint the tool checks before each run, **Target** for the monitored profile and **Notifications** for both alert channels. A section with nothing to report is left out.

Only a `[FAIL]` changes the exit code, which is `1` when anything failed and `0` otherwise, so the command can gate a deployment. The report ends with the command that starts monitoring using the same configuration and dotenv files you passed to doctor.

The credentials themselves are never displayed. A row that reports a secret names the setting and its source, not its value.

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

A failure is reported once, with the delay before the next attempt on the same line. A failure the tool can retry away, such as a Last.fm outage or a lost connection, is reported once the next check has failed too, so a blip of a single check between polls a few seconds apart prints nothing. A failure that needs you, such as a rejected key, is reported on the first check. With `--verbose` every first failing check is reported:

```
* Error: The Last.fm API is temporarily unavailable (retrying in 30 seconds)
To fix: This is usually a Last.fm outage. The tool will keep retrying
```

While it lasts the tool stays quiet and reminds you once an hour, with how many checks have failed so far, so a two day outage is a handful of lines rather than one block per check. The reminder has its own cadence and does not depend on `LIVENESS_CHECK_INTERVAL`:

```
* Monitoring degraded for <lastfm_username>. The Last.fm API is temporarily unavailable since Mon 08 Sep 2026, 09:15:05, 360 failed checks
Liveness check, timestamp:	Mon 08 Sep 2026, 10:15:05
```

When the failure clears, the run says so whatever flags it was started with. A failure that was never reported recovers quietly:

```
* Monitoring recovered for <lastfm_username> after 14 hours
```

An outage that starts failing differently is still one outage. A lost connection that reads as a timeout on one check and as an unreachable host on the next prints nothing new, and a change to another kind of failure that clears on its own, such as a rate limit after an outage, is one line, `* Monitoring failure changed for <lastfm_username>. <what fails now>`, rather than a second full report. A change to a failure that needs you is reported in full. The `ERROR_500_NUMBER_LIMIT`, `ERROR_500_TIME_LIMIT`, `ERROR_NETWORK_ISSUES_NUMBER_LIMIT` and `ERROR_NETWORK_ISSUES_TIME_LIMIT` settings of earlier versions are retired. A configuration file that still sets them is loaded with a note and they are ignored.

## Verbose Output

`--verbose` adds the decisions a run made, in the same `*` lines as the rest of the output:

```sh
lastfm_monitor <lastfm_username> --verbose
```

It reports a channel switched off because its settings cannot work, a tracked field that could not be read together with the alert that silences and each alert that reached your inbox or your webhook. Nothing is printed per check, so a quiet run stays quiet.

A feature that stays unavailable is reported once, when it stops working, rather than on every check that follows. The repeated failures are left to `--debug`. It is reported again when it starts working, but only when the failure itself was printed, so a recovery never refers to something you never saw.

Verbose mode can also be turned on permanently with the `VERBOSE_MODE` configuration setting. The `--verbose` flag wins over a configuration file that sets `VERBOSE_MODE = False`.

The two modes are independent. `--verbose` does not turn on debug output and `--debug` does not turn on verbose output. A run with neither ends its startup summary with a line naming both.

If long track titles or paths wrap and make the output hard to read, set `TRUNCATE_CHARS` or use the `--truncate N` flag to cut each screen line to a maximum width. Use `999` to auto-detect the terminal width. The log file always keeps the full line, so the setting is ignored when logging is disabled with `-d`. It is off by default and needs the optional `wcwidth` library to measure display width, otherwise lines are left untouched.

## Debug Output

`--debug` traces what the tool is doing in timestamped `[DEBUG HH:MM:SS]` lines:

```sh
lastfm_monitor <lastfm_username> --debug
```

Each line reads `Operation: key=value, key=value`, and an operation that finished reports `outcome=OK`, `failed`, `degraded` or `skipped`, so `grep outcome=failed` finds every failure in a long run.

```text
[DEBUG 12:00:00] HTTP GET: url=https://www.last.fm/user/someuser/following, timeout=30s, attempt=#1/3, status=200, outcome=OK
[DEBUG 12:00:00] Completed check: check=#7, user=someuser, state=online, track=Artist - Track
```

Traced operations include every outbound call with its address, timeout and result, where each secret resolved from, the configuration file and how many settings it applied, every completed check and the wait before the next one, every retry with its delay, each file the tool reads or writes, both notification channels with the destination host, the attempt and the delivery outcome, and the full [Spotify metadata](configuration.md#spotify-metadata-backends) path: server time, anonymous web-player token requests and refreshes, persisted-query hash discovery, OAuth app token retrieval and every search and match decision that resolves a track ID and duration.

Failures the tool recovers from on its own are traced too, so a feature that quietly does nothing can still be diagnosed.

That last group is the reason to reach for `--debug` first when track durations or automatic playback are not working. The trace names which backend answered, which candidate tracks came back and why one was chosen or rejected.

Debug mode can also be turned on permanently with the `DEBUG_MODE` configuration setting. The `--debug` flag wins over a configuration file that sets `DEBUG_MODE = False`.

Debug output is written to the terminal and to the log file.

Error text is redacted before it is printed. Configured secrets are replaced wherever they appear, as are `SETTING = value` lines for any of the secret settings, `Authorization: Bearer` and `Authorization: Basic` headers, signed Last.fm request parameters such as `api_key` and `api_sig`, and Discord webhook URLs. Redaction is a safety net rather than a guarantee, so still read the output before pasting it into a bug report.
