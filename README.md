# lastfm_monitor

lastfm_monitor is a Python script which allows for real-time monitoring of Last.fm users music activity. 

## Features

- Real-time monitoring of songs listened by Last.fm user (including detection when user gets online & offline)
- Showing when user pauses or resumes playback
- Information about how long the user listened to a song, if shorter/longer than track duration, if song has been skipped
- Email notifications for different events (user gets active/inactive, specific/all songs, new entries showed up while user was offline, errors)
- Saving all listened songs with timestamps to the CSV file
- Clickable Spotify, Apple and Genius search URLs printed in the console & included in email notifications
- Showing basic statistics for user's playing session (how long, time span, number of listened & skipped songs, time of paused playback)
- Support for detecting offline mode
- Support for detecting Spotify private mode (not 100% accurate)
- Possibility to control the running copy of the script via signals

<p align="center">
   <img src="./assets/lastfm_monitor.png" alt="lastfm_monitor_screenshot" width="80%"/>
</p>

## Change Log

Release notes can be found [here](RELEASE_NOTES.md)

## Disclaimer

I'm not a dev, project done as a hobby. Code is ugly and as-is, but it works (at least for me) ;-)

## Requirements

The script requires Python 3.x.

It uses [pylast](https://github.com/pylast/pylast) library, also requires requests, python-dateutil and urllib3.

It has been tested succesfully on Linux (Raspberry Pi Bullseye & Bookworm based on Debian) and Mac OS (Ventura & Sonoma). 

Should work on any other Linux OS and Windows with Python.

## Installation

Install the required Python packages:

```sh
python3 -m pip install requests python-dateutil urllib3 pylast
```

Or from requirements.txt:

```sh
pip3 install -r requirements.txt
```

Copy the *lastfm_monitor.py* file to the desired location. 

You might want to add executable rights if on Linux or MacOS:

```sh
chmod a+x lastfm_monitor.py
```

## Configuration

Edit the *lastfm_monitor.py* file and change any desired configuration variables in the marked **CONFIGURATION SECTION** (all parameters have detailed description in the comments).

### Last.fm 'API key' and 'Shared secret'

Mandatory activity is to create your Last.fm **API key** and **Shared secret** by going to [https://www.last.fm/api/account/create](https://www.last.fm/api/account/create) (or get your existing one from [https://www.last.fm/api/accounts](https://www.last.fm/api/accounts))

Change **LASTFM_API_KEY** & **LASTFM_API_SECRET** variables to respective values.

### Spotify sp_dc cookie

If you want to use ***'track_songs'*** functionality (-g parameter), so the script automatically plays the track listened by the user in your Spotify client, then you need to log in to Spotify web client [https://open.spotify.com/](https://open.spotify.com/) in your web browser and copy the value of sp_dc cookie to **SP_DC_COOKIE** variable. 

You can use Cookie-Editor by cgagnier to get it easily (available for all major web browsers): [https://cookie-editor.com/](https://cookie-editor.com/)

Newly generated Spotify's sp_dc cookie should be valid for 1 year. You will be informed by the tool once the cookie expires (proper message on the console and in email if errors notifications have not disabled).

### SMTP settings

If you want to use email notifications functionality you need to change the SMTP settings (host, port, user, password, sender, recipient).

### Other settings

All other variables can be left at their defaults, but feel free to experiment with it.

## Getting started

### List of supported parameters

To get the list of all supported parameters:

```sh
./lastfm_monitor.py -h
```

or 

```sh
python3 ./lastfm_monitor.py -h
```

### Monitoring mode

To monitor specific user activity, just type its Last.fm username as parameter (**misiektoja** in the example below):

```sh
./lastfm_monitor.py misiektoja
```

The tool will run infinitely and monitor the user until the script is interrupted (Ctrl+C) or killed the other way.

You can monitor multiple Last.fm users by spawning multiple copies of the script. 

It is suggested to use sth like **tmux** or **screen** to have the script running after you log out from the server.

The tool automatically saves its output to *lastfm_monitor_username.log* file (can be changed in the settings or disabled with -d).

The tool also saves the last activity information (artist, track, timestamp) to *lastfm_username_last_activity.json file*, so it can be reused in case the tool needs to be restarted.

### Listing mode

There is also other mode of the tool which prints the recently listened tracks for the user (-l parameter). You can also add -n to define how many tracks should be displayed, by default it shows 30 last tracks:

```sh
./lastfm_monitor.py -l misiektoja -n 50
```

You can use the -l functionality regardless if the monitoring is used or not (it does not interfere). 

## How to use other features

### Email notifications

If you want to get email notifications once user gets active (-a), inactive (-i) and new entries show up when user is offline (-f):

```sh
./lastfm_monitor.py misiektoja -a -i -f
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="./assets/lastfm_monitor_email_notifications.png" alt="lastfm_monitor_email_notifications" width="65%"/>
</p>

If you also want to be informed every time a user listens to specific songs, you can use **track_notification** functionality (-t). 

For that you need to create a file with list of songs you want to track (one track and/or album per line). The file needs to be indicated by -s parameter. The script checks if the listened track or album is in the file. Example file *lastfm_tracks_misiektoja*:

```
we fell in love in october
Like a Stone
Half Believing
Something Changed
I Will Be There
```

Then run the tool with -t & -s parameters:

```sh
./lastfm_monitor.py misiektoja -t -s ./lastfm_tracks_misiektoja
```

If you want to get email notifications for every listened song (-j):

```sh
./lastfm_monitor.py misiektoja -j
```

### Saving listened songs to the CSV file

If you want to save all the listened songs in the CSV file, use -b parameter with the name of the file (it will be automatically created if it does not exist):

```sh
./lastfm_monitor.py misiektoja -b lastfm_tracks_misiektoja.csv
```

### Automatic playing of tracks listened by the user in Spotify client

If you want the script to automatically track what the user listens and to play it in your Spotify client (-g):

```sh
./lastfm_monitor.py misiektoja -g
```

Currently the script only supports playing the songs in Spotify client in Mac OS. There are conditionals in the code prepared for Linux and Windows, so feel free to test it and add proper commands.

### Progress indicator

If you want to see nice progress indicator which should show you estimated position of what user is currently listening (-p):

```sh
./lastfm_monitor.py misiektoja -p
```

<p align="center">
   <img src="./assets/lastfm_monitor_progress_indicator.png" alt="lastfm_monitor_progress_indicator" width="80%"/>
</p>

For this functionality to work correctly it is suggested to have the active check interval (-k) set to low value (like 2-5 seconds).

### Check intervals and offline timer 

If you want to change the check interval when the user is offline to 10 seconds (-c) and active to 2 seconds (-k):

```sh
./lastfm_monitor.py misiektoja -c 10 -k 2
```

If you want to change the time required to mark the user as inactive to 2 mins - 120 seconds (the timer starts once user stops playing the music):

```sh
./lastfm_monitor.py misiektoja -o 120
```

### Controlling the script via signals


The tool has several signal handlers implemented which allow to change behaviour of the tool without a need to restart it with new parameters.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets active/inactive |
| USR2 | Toggle email notifications for every song |
| HUP  | Toggle showing of progress indicator |
| CONT | Toggle email notifications for tracked songs |
| TRAP | Increase the inactivity check timer (by 30 seconds) |
| ABRT | Decrease the inactivity check timer (by 30 seconds) |

So if you want to change functionality of the running tool, just send the proper signal to the desired copy of the script.

I personally use **pkill** tool, so for example to toggle showing of progress indicator for tool instance monitoring the *misiektoja* user:

```sh
pkill -f -HUP "python3 ./lastfm_monitor.py misiektoja"
```

### Private mode detection in Spotify

The script contains functionality to detect possible private mode used in Spotify and even estimates when private mode was used. It is enabled by default (not configurable).

It is NOT 100% accurate. I observed that very often when private mode is used (especially for longer time) it results in many duplicated entries created in Last.fm account after private mode is disabled. So different tracks have the same start timestamp.

I suspect it is related to some bug in Spotify and it mainly happens if the user has Spotify on multiple devices.

However keep in mind it is not 100% accurate. I observed duplicate entries also with no private mode, but in such case number of duplicate entries is limited. So do not treat it as something 100% certain, but it is pretty good indicator that private mode was used.

<p align="center">
   <img src="./assets/lastfm_monitor_private_mode.png" alt="lastfm_monitor_private_mode" width="80%"/>
</p>

There is one other method I discovered which is related to activity reported by Spotify Web API itself, but it requires deeper integration with it to detect it more reliably. I plan to cover it in the future.

### Other

Check other supported parameters using -h.

You can of course combine all the parameters mentioned earlier together.

## Limitations

The script has been tested with Last.fm account integrated with Spotify client, however it should work with other clients.

Currently the ***'track_songs'*** functionality (-g parameter) only supports playing the songs in Spotify client in Mac OS. There are conditionals in the code prepared for Linux and Windows, so feel free to test it and add proper commands.

## Colouring log output with GRC

If you use [GRC](https://github.com/garabik/grc) and want to have the output properly coloured you can use the configuration file available [here](grc/conf.monitor_logs)

Change your grc configuration (typically *.grc/grc.conf*) and add this part:

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the *conf.monitor_logs* to your .grc directory and lastfm_monitor log files should be nicely coloured.

## License

This project is licensed under the GPLv3 - see the [LICENSE](LICENSE) file for details
