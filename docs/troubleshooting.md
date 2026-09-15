# Troubleshooting

If a dotenv file cannot be opened or is not UTF-8, monitoring stops with the file path and the repair step for that cause. Doctor reports the failed load and continues the remaining checks.

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

The report covers **Environment**, **Configuration**, **Authentication**, **Spotify metadata**, **Connectivity**, **Target** and **Notifications**. Optional sections appear only when relevant features are enabled.

Only a `[FAIL]` changes the exit code, which is `1` when anything failed and `0` otherwise, so the command can gate a deployment. The report ends with the command that starts monitoring using the same configuration and dotenv files you passed to doctor.

Doctor checks Spotify app credentials without changing the token cache.

The credentials themselves are never displayed. A row that reports a secret names the setting and its source, not its value.

An unreadable or malformed friends list names the affected file and the expected username-list format. The next successful check rebuilds that baseline without follower or following change alerts. Older list-only files and unused count metadata still load.

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

Temporary failures are reported after two failed checks. Problems that need your action, such as a rejected key, are reported immediately. Use `--verbose` to see every first failure:

```
* Error: The Last.fm API is temporarily unavailable (retrying in 30 seconds)
To fix: This is usually a Last.fm outage. The tool will keep retrying
```

Continuing outages produce one reminder per hour, independently of `LIVENESS_CHECK_INTERVAL`:

```
* Monitoring degraded for <lastfm_username>. The Last.fm API is temporarily unavailable since Mon 08 Sep 2026, 09:15:05, 360 failed checks
Liveness check, timestamp:	Mon 08 Sep 2026, 10:15:05
```

When the failure clears, the run says so whatever flags it was started with. A failure that was never reported recovers quietly:

```
* Monitoring recovered for <lastfm_username> after 14 hours
```

Follow any new instructions if the failure changes. The old `ERROR_500_NUMBER_LIMIT`, `ERROR_500_TIME_LIMIT`, `ERROR_NETWORK_ISSUES_NUMBER_LIMIT` and `ERROR_NETWORK_ISSUES_TIME_LIMIT` settings are ignored.

## Last.fm Website Tracking

Follower, following and profile checks use `curl_cffi` with Chrome impersonation. Last.fm can return a `Client Challenge` page with HTTP 200 instead of the requested data. The tool recognizes this as browser verification and retries it. A rejected page cannot replace saved tracking data or produce change alerts.

If browser verification persists, [update the installation and its dependencies](installation.md#upgrading) and check the same Last.fm profile in a browser. Opening it there does not share browser cookies with the monitor. Keep the saved tracking files. Changing API credentials does not fix a website challenge.

Temporary website errors, including HTTP 600, also use bounded retries. Use `--debug` to see the HTTP status and retry attempts. The normal friend and profile check interval defaults to 90 minutes. Explicit saved intervals still apply.

## Verbose Output

`--verbose` adds the decisions a run made, in the same `*` lines as the rest of the output:

```sh
lastfm_monitor <lastfm_username> --verbose
```

It reports a channel switched off because its settings cannot work, a tracked field that could not be read together with the alert that silences and each alert that reached your inbox or your webhook. Nothing is printed per check, so a quiet run stays quiet.

A feature that stays unavailable is reported once, when it stops working, rather than on every check that follows. The repeated failures are left to `--debug`. It is reported again when it starts working, but only when the failure itself was printed, so a recovery never refers to something you never saw.

Verbose mode can also be turned on permanently with the `VERBOSE_MODE` configuration setting. Set `DELIVERY_CONFIRMATIONS = False` to keep verbose mode without the `* Email sent to ...` and `* Webhook sent through ...` lines, which is worth doing when alerts are frequent. The `--verbose` flag wins over a configuration file that sets `VERBOSE_MODE = False`.

Delivery confirmations name the email recipient or webhook provider without repeating the subject or message body. `DELIVERY_CONFIRMATIONS = False` hides those optional success receipts. Event output, send attempts and errors remain visible. Explicit notification tests report their result once. Generated email subjects and webhook titles use readable service names without a program-name prefix.

The two modes are independent. `--verbose` does not turn on debug output and `--debug` does not turn on verbose output. A run with neither ends its startup summary with a line naming both.

If long track titles or paths wrap and make the output hard to read, set `TRUNCATE_CHARS` or use the `--truncate N` flag to cut each screen line to a maximum width. Use `999` to auto-detect the terminal width. The log file always keeps the full line, so the setting is ignored when logging is disabled with `-d`. It is off by default. Install the optional `wcwidth` library for correct widths with wide characters, which otherwise count as one column and can run a line past the limit.

## Debug Output

`--debug` traces what the tool is doing in timestamped `[DEBUG HH:MM:SS]` lines:

```sh
lastfm_monitor <lastfm_username> --debug
```

Each line reads `Operation: key=value, key=value`. Fields depend on the operation. Some results report `outcome=OK`, `failed`, `degraded` or `skipped`. Webhook responses also use HTTP status and retry fields, so an outcome-only search does not find every failure.

```text
[DEBUG 12:00:00] HTTP GET: url=https://www.last.fm/user/someuser/following, timeout=30s, attempt=#1/3, status=200, outcome=OK
[DEBUG 12:00:00] Completed check: check=#7, user=someuser, state=online, track=Artist - Track
```

Debug output covers requests, settings, secret sources, polling, retries, file access, notifications and [Spotify metadata](configuration.md#spotify-metadata-backends). It includes token retrieval and track matching details. Some dependency operations have no individual trace.

Failures the tool recovers from on its own are traced too, so a feature that quietly does nothing can still be diagnosed.

That last group is the reason to reach for `--debug` first when track durations or automatic playback are not working. The trace names which backend answered, which candidate tracks came back and why one was chosen or rejected.

Debug mode can also be turned on permanently with the `DEBUG_MODE` configuration setting. The `--debug` flag wins over a configuration file that sets `DEBUG_MODE = False`.

Debug output is written to the terminal and to the log file.

Error text is redacted before it is printed. Configured secrets are replaced wherever they appear, as are `SETTING = value` lines for any of the secret settings, `Authorization: Bearer` and `Authorization: Basic` headers, signed Last.fm request parameters such as `api_key` and `api_sig`, and Discord webhook URLs. Redaction is a safety net rather than a guarantee, so still read the output before pasting it into a bug report.

## Installation and Command Problems

If Python or `pip` is missing, use the [Python install walkthrough](installation.md#new-to-python-install-everything).

If `lastfm_monitor` is not found after installation, close the terminal and open it again. On Windows with Python Install Manager, run `py install --refresh` to refresh command aliases. For a pipx installation, run `pipx ensurepath` then reopen the terminal. If you downloaded the script, use the [manual command](usage.md#command-format) from its directory.

If `pip` reports an externally managed environment, follow the pipx steps in [Installation](installation.md#install-lastfm-monitor-after-python-check). Use `pipx upgrade lastfm_monitor` for later upgrades.

If the tool cannot import a dependency, install the dependencies with the same Python interpreter that runs the script. On macOS or Linux use `python3 -m pip install -r requirements.txt`. On Windows use `python -m pip install -r requirements.txt`. Match the requirements file to your downloaded script.

If a new terminal cannot find your saved settings, return to the directory used during setup or pass both `--config-file` and `--env-file` explicitly. Run `lastfm_monitor --doctor <lastfm_username>` to see which settings are loaded.

## Invalid saved settings and state

If setup fails while saving, the configuration may already have changed. Correct the reported destination problem, rerun `--setup` with the same `--config-file` and `--env-file` paths then run `--doctor` before monitoring. The configuration backup restores non-secret settings only.

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

If a saved last-activity file has an invalid structure, monitoring stops before replacing it. Correct the named file or move it aside to start a fresh baseline. Keep a copy if you need the old history. Older valid records and extra trailing metadata remain accepted.

Malformed path settings and color-theme values are reported by Doctor with the setting name. Invalid color values are ignored while rendering help so you can still find the configuration commands.

A saved timestamp more than five minutes ahead of the machine clock is not used as history, because the tool wrote that file itself and a clock moved backwards is the usual reason. Monitoring warns, keeps the saved entry and times it from the moment it starts, so the run continues. Check the system clock if the warning repeats.
