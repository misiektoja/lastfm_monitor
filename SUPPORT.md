# Getting help

Start with the [documentation](https://misiektoja.github.io/lastfm_monitor/). [Installation](https://misiektoja.github.io/lastfm_monitor/installation/) and [Setup & First Run](https://misiektoja.github.io/lastfm_monitor/setup-and-first-run/) cover most first-run problems, [Configuration](https://misiektoja.github.io/lastfm_monitor/configuration/) explains every setting the tool reads and [Troubleshooting](https://misiektoja.github.io/lastfm_monitor/troubleshooting/) covers what to check when something fails.

## Check your setup first

Confirm which version you are running and that the notification channel actually works, then include the results when you ask:

```sh
lastfm_monitor --version
lastfm_monitor --send-test-email
```

Most reports come down to a rejected Last.fm API key or secret, Spotify credentials the tool can no longer use or an SMTP server that refuses the message. Rerun the failing command with `--debug` and keep the output.

## Where to ask

| You want to | Go to |
| --- | --- |
| Ask a question or discuss an idea | [Discussions](https://github.com/misiektoja/lastfm_monitor/discussions) |
| Report something broken | [Bug report](https://github.com/misiektoja/lastfm_monitor/issues/new?template=bug_report.yml) |
| Request a capability | [Feature request](https://github.com/misiektoja/lastfm_monitor/issues/new?template=feature_request.yml) |
| Report a vulnerability | [Private security advisory](https://github.com/misiektoja/lastfm_monitor/security/advisories/new), never a public issue |
| Contribute a change | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Before you post

Include the version, how you installed it (PyPI or manual script), your operating system, the monitored user you passed and what you expected instead. Run the failing command with `--debug` and attach the relevant part of the log, which the tool writes unless you pass `--disable-logging`.

Never post your Last.fm API key or secret, Spotify credentials, SMTP passwords, webhook URLs or a complete configuration file. Redact monitored usernames if they matter to you.

## What to expect

This is a project maintained in spare time, so replies are best effort with no response time attached. Only the latest release receives fixes, so reproduce the problem on the current version before reporting it.

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
