# Installation

## Requirements

* Python 3.9 or higher
* Libraries: [pyLast](https://github.com/pylast/pylast), `requests`, `python-dateutil`, [PyOTP](https://github.com/pyauth/pyotp), [Spotipy](https://github.com/spotipy-dev/spotipy), `python-dotenv`, `beautifulsoup4`

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia, Tahoe
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm, Trixie), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

## Install from PyPI

```sh
pip install lastfm_monitor
```

## Manual Installation

Download the *[lastfm_monitor.py](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/lastfm_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install pylast requests python-dateutil pyotp spotipy python-dotenv beautifulsoup4
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

## Upgrading

To upgrade to the latest version when installed from PyPI:

```sh
pip install lastfm_monitor -U
```

If you installed manually, download the newest *[lastfm_monitor.py](https://raw.githubusercontent.com/misiektoja/lastfm_monitor/refs/heads/main/lastfm_monitor.py)* file to replace your existing installation.

## How Commands Are Printed

Every command the tool suggests is written for the way it is installed: `lastfm_monitor ...` for a PyPI install and `python3 lastfm_monitor.py ...` for the downloaded script. The suggestion also repeats the `--config-file` and `--env-file` you started with, so pasting it checks the same setup that just failed.

Detection uses the name the tool was started under. If a wrapper script or a container image makes that misleading, set `LASTFM_MONITOR_INSTALL_METHOD` to `pip` or `manual` to fix the form:

```sh
export LASTFM_MONITOR_INSTALL_METHOD=pip
```
