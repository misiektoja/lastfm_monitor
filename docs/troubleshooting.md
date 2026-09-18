# Troubleshooting

Examples on this page use the PyPI command `lastfm_monitor`. If you installed the manual script, replace that command with the matching [command prefix](usage.md#command-format-by-installation-method).

<a id="doctor-preflight"></a>
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

<a id="common-problems"></a>
## Common Problems

Every failure is reported in the same three-part shape: what went wrong, a `To fix:` action and a `Guide:` link to the page that covers it. The fix command matches how you installed the tool and carries the `--config-file` or `--env-file` you started with, so it can be pasted as it is. `--debug` appends a `Technical detail:` line for bug reports. Secrets are redacted from all three.

| Symptom | Likely cause | Where to look |
| --- | --- | --- |
| Last.fm error 17, `Login: User required to be logged in` | The monitored user hides recent listening information | [User Privacy Settings](setup-and-first-run.md#user-privacy-settings) |
| `Last.fm rejected the configured API key or shared secret` | The credentials are missing, wrong or suspended | Run `lastfm_monitor --set-lastfm-credentials` |
| `The Last.fm API is temporarily unavailable` | A Last.fm outage or a rate limit | Nothing to do, the tool keeps retrying |
| Track durations are missing | The optional Spotify credentials are not saved | [Spotify Metadata Backends](configuration.md#spotify-metadata-backends) |
| The run stops naming a file and a line number | A configuration line is not a plain `SETTING = value` assignment | [Configuration File](configuration.md#configuration-file) |
| Emails never arrive | Incomplete SMTP settings | [SMTP Settings](configuration.md#smtp-settings) then run `lastfm_monitor --send-test-email` |
| Webhook alerts never arrive | Provider mismatch or a stale destination | [Webhook Settings](configuration.md#webhook-settings) then run `lastfm_monitor --send-test-webhook` |
| `lastfm_monitor` is not found after installation | The shell has not picked up the new command | [Installation and Command Problems](#installation-and-command-problems) |
| Escape sequences such as `[36m` printed as text or no colour at all | The terminal cannot display ANSI colour or colour was switched off | [Terminal Colours Look Wrong](#terminal-colours-look-wrong) |

A continuing outage produces a `* Monitoring degraded` reminder once an hour, even when the [liveness reminder](usage.md#liveness-reminder) is switched off. `* Monitoring recovered` marks recovery. Use `--verbose` to see the first failed check.

If a dotenv file cannot be opened or is not UTF-8, monitoring stops with the file path and the repair step for that cause. Doctor reports the failed load and continues the remaining checks.

<a id="lastfm-website-tracking"></a>
## Last.fm Website Tracking

Follower, following and profile checks use `curl_cffi` with Chrome impersonation. Last.fm can return a `Client Challenge` page with HTTP 200 instead of the requested data. The tool recognizes this as browser verification and retries it. A rejected page cannot replace saved tracking data or produce change alerts.

If browser verification persists, [update the installation and its dependencies](installation.md#upgrading) and check the same Last.fm profile in a browser. Opening it there does not share browser cookies with the monitor. Keep the saved tracking files. Changing API credentials does not fix a website challenge.

Temporary website errors, including HTTP 600, also use bounded retries. Use `--debug` to see the HTTP status and retry attempts. The normal friend and profile check interval defaults to 90 minutes. Explicit saved intervals still apply.

<a id="terminal-colours-look-wrong"></a>
## Terminal Colours Look Wrong

If escape sequences such as `[36m` appear as literal text, the terminal does not understand ANSI colour. Start the tool with `--no-color` or set `COLORED_OUTPUT = False` in the configuration file. On Windows, `pip install colorama` fixes the classic Command Prompt.

If colour is missing where you expect it, check in this order: `--no-color` on the command line, `COLORED_OUTPUT` in the configuration file, a `NO_COLOR` environment variable and whether output is redirected or piped. Colour is switched off in all of those cases and also when `TERM` is unset or set to `dumb`.

Log files never contain colour by design. To colour a saved log while reading it, see [Coloring Log Output with GRC](usage.md#coloring-log-output-with-grc).

To change which colours are used, see [Terminal Colours](configuration.md#terminal-colours).

<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** reports activity changes and important errors
- **Verbose mode (`--verbose`)** adds occasional state changes, a line naming where each delivered alert went and a complete startup summary without private values. Set `DELIVERY_CONFIRMATIONS = False` to keep verbose mode without those delivery lines
- **Debug mode (`--debug`)** adds sanitized request flow, scheduling details and internal diagnostics

Delivery confirmations name the recipient or webhook provider. `DELIVERY_CONFIRMATIONS = False` hides these optional success messages. Monitoring events, send attempts and errors remain visible.

Both `--verbose` and `--debug` show the complete startup summary, including notification settings and credential sources. Use it to check which configuration is active without displaying private values.

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening a GitHub issue.

<a id="verbose-and-debug-output"></a>
## Verbose and Debug Output

`--verbose` adds the decisions a run made, in the same `*` lines as the rest of the output:

```sh
lastfm_monitor <lastfm_username> --verbose
```

`--debug` traces what the tool is doing in timestamped `[DEBUG HH:MM:SS]` lines:

```sh
lastfm_monitor <lastfm_username> --debug
```

Each line reads `Operation: key=value, key=value`. Fields depend on the operation. Some results report `outcome=OK`, `failed`, `degraded` or `skipped`.

<a id="installation-and-command-problems"></a>
## Installation and Command Problems

If Python or `pip` is missing, use the [Python install walkthrough](installation.md#new-to-python-check-and-install).

If `lastfm_monitor` is not found after installation, close the terminal and open it again. On Windows with Python Install Manager, run `py install --refresh` to refresh command aliases. For a pipx installation, run `pipx ensurepath` then reopen the terminal. If you downloaded the script, use the [manual command](usage.md#command-format-by-installation-method) from its directory.

If `pip` reports an externally managed environment, follow the pipx steps in [Installation](installation.md#install-lastfm-monitor). Use `pipx upgrade lastfm_monitor` for later upgrades.

If the tool cannot import a dependency, install the dependencies with the same Python interpreter that runs the script. On macOS or Linux use `python3 -m pip install -r requirements.txt`. On Windows use `python -m pip install -r requirements.txt`. Match the requirements file to your downloaded script.

If a new terminal cannot find your saved settings, return to the directory used during setup or pass both `--config-file` and `--env-file` explicitly. Run `lastfm_monitor --doctor <lastfm_username>` to see which settings are loaded.

<a id="invalid-saved-settings-and-state"></a>
## Invalid saved settings and state

If setup fails while saving, the configuration may already have changed. Correct the reported destination problem, rerun `--setup` with the same `--config-file` and `--env-file` paths then run `--doctor` before monitoring. The configuration backup restores non-secret settings only.

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

If a saved last-activity file has an invalid structure, monitoring stops before replacing it. Correct the named file or move it aside to start a fresh baseline. Keep a copy if you need the old history. Older valid records and extra trailing metadata remain accepted.

Malformed path settings and color-theme values are reported by Doctor with the setting name. Invalid color values are ignored while rendering help so you can still find the configuration commands.

A saved timestamp more than five minutes ahead of the machine clock is not used as history, because the tool wrote that file itself and a clock moved backwards is the usual reason. Monitoring warns, keeps the saved entry and times it from the moment it starts, so the run continues. Check the system clock if the warning repeats.
