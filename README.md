# lastfm_monitor

lastfm_monitor is a Python tool which allows for real-time monitoring of Last.fm users music activity. 

## Features

- Real-time tracking of songs listened by Last.fm users (including detection when user gets online & offline)
- Possibility to automatically play songs listened by tracked user in your local Spotify client
- Showing when user pauses or resumes playback, possibility to display track progress indicator
- Information about how long the user listened to a song, if shorter/longer than track duration, if song has been skipped
- Email notifications for different events (user gets active/inactive, specific/all songs, songs on loop, new entries showed up while user was offline, errors)
- Saving all listened songs with timestamps to the CSV file
- Clickable Spotify, Apple Music, YouTube Music and Genius Lyrics search URLs printed in the console & included in email notifications
- Showing basic statistics for user's playing session (how long, time span, number of listened & skipped songs, songs on loop, time of paused playback, number of pauses)
- Support for detecting offline mode
- Support for detecting Spotify private mode (not 100% accurate)
- Possibility to control the running copy of the script via signals

<p align="center">
   <img src="./assets/lastfm_monitor.png" alt="lastfm_monitor_screenshot" width="90%"/>
</p>

## Change Log

Release notes can be found [here](RELEASE_NOTES.md)

## Disclaimer

I'm not a dev, project done as a hobby. Code is ugly and as-is, but it works (at least for me) ;-)

## Requirements

The tool requires Python 3.8 or higher.

It uses [pyLast](https://github.com/pylast/pylast) library, also requires requests, python-dateutil and urllib3.

It has been tested successfully on:
- macOS (Ventura, Sonoma & Sequoia)
- Linux:
   - Raspberry Pi Bullseye & Bookworm
   - Ubuntu 24
   - Kali Linux 2024
- Windows (10 & 11)

It should work on other versions of macOS, Linux, Unix and Windows as well.

## Installation

Install the required Python packages:

```sh
python3 -m pip install requests python-dateutil urllib3 pylast
```

Or from requirements.txt:

```sh
pip3 install -r requirements.txt
```

Copy the *[lastfm_monitor.py](lastfm_monitor.py)* file to the desired location. 

You might want to add executable rights if on Linux/Unix/macOS:

```sh
chmod a+x lastfm_monitor.py
```

## Configuration

Edit the *[lastfm_monitor.py](lastfm_monitor.py)* file and change any desired configuration variables in the marked **CONFIGURATION SECTION** (all parameters have detailed description in the comments).

### Last.fm 'API key' and 'Shared secret'

Mandatory activity is to create your Last.fm **API key** and **Shared secret** by going to [https://www.last.fm/api/account/create](https://www.last.fm/api/account/create) (or get your existing one from [https://www.last.fm/api/accounts](https://www.last.fm/api/accounts))

Then change **LASTFM_API_KEY** and **LASTFM_API_SECRET** variables to respective values (or use **-u** and **-w** parameters).

### User privacy settings

In order to monitor Last.fm user activity, proper privacy settings need to be enabled on the monitored user account, i.e. in Last.fm *'Settings'* -> *'Privacy'*, the *'Hide recent listening information'* setting should be disabled. Otherwise you will get this error message returned by pyLast library: *'Login: User required to be logged in'*.

### Spotify sp_dc cookie

If you want to get track duration from Spotify (**-r** parameter) or you want to use ***track_songs*** functionality (**-g** parameter), so the script automatically plays the track listened by the user in your Spotify client, then you need to log in to Spotify web client [https://open.spotify.com/](https://open.spotify.com/) in your web browser and copy the value of sp_dc cookie to **SP_DC_COOKIE** variable (or use **-z** parameter). 

You can use Cookie-Editor by cgagnier to get it easily (available for all major web browsers): [https://cookie-editor.com/](https://cookie-editor.com/)

Newly generated Spotify's sp_dc cookie should be valid for 1 year. You will be informed by the tool once the cookie expires (proper message on the console and in email if error notifications have not been disabled via **-e** parameter).

### SMTP settings

If you want to use email notifications functionality you need to change the SMTP settings (host, port, user, password, sender, recipient) in the *[lastfm_monitor.py](lastfm_monitor.py)* file. If you leave the default settings then no notifications will be sent.

You can verify if your SMTP settings are correct by using **-y** parameter (the tool will try to send a test email notification):

```sh
./lastfm_monitor.py -y
```

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

To monitor specific user activity, just type Last.fm username as parameter (**misiektoja** in the example below):

```sh
./lastfm_monitor.py misiektoja
```

If you have not changed **LASTFM_API_KEY** & **LASTFM_API_SECRET** variables in the *[lastfm_monitor.py](lastfm_monitor.py)* file, you can use **-u** and **-w** parameters:

```sh
./lastfm_monitor.py misiektoja -u "your_lastfm_api_key" -w "your_lastfm_api_secret"
```

The tool will run infinitely and monitor the user until the script is interrupted (Ctrl+C) or killed the other way.

You can monitor multiple Last.fm users by spawning multiple copies of the script. 

It is suggested to use sth like **tmux** or **screen** to have the script running after you log out from the server (unless you are running it on your desktop).

The tool automatically saves its output to *lastfm_monitor_{username}.log* file (can be changed in the settings via **LF_LOGFILE** variable or disabled completely with **-d** parameter).

The tool also saves the last activity information (artist, track, timestamp) to *lastfm_{username}_last_activity.json file*, so it can be reused in case the tool needs to be restarted.

### Listing mode

There is also other mode of the tool which prints the recently listened tracks for the user (**-l** parameter). You can also add **-n** parameter to define how many tracks should be displayed, by default it shows 30 last tracks:

```sh
./lastfm_monitor.py -l misiektoja -n 10
```

<p align="center">
   <img src="./assets/lastfm_monitor_listing.png" alt="lastfm_monitor_listing" width="95%"/>
</p>

You can use the **-l** functionality regardless if the monitoring is used or not (it does not interfere). 

## How to use other features

### Email notifications

If you want to get email notifications once user gets active (**-a**), inactive (**-i**) and new entries show up when user is offline (**-f**):

```sh
./lastfm_monitor.py misiektoja -a -i -f
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="./assets/lastfm_monitor_email_notifications.png" alt="lastfm_monitor_email_notifications" width="90%"/>
</p>

If you also want to be informed every time a user listens to specific songs, you can use **track_notification** functionality (**-t** parameter). 

For that you need to create a file with list of songs you want to track (one track and/or album per line). The file needs to be indicated by **-s** parameter. The script checks if the listened track or album is in the file. Example file *lastfm_tracks_misiektoja*:

```
we fell in love in october
Like a Stone
Half Believing
Something Changed
I Will Be There
```

Then run the tool with **-t** and **-s** parameters:

```sh
./lastfm_monitor.py misiektoja -t -s ./lastfm_tracks_misiektoja
```

If you want to get email notifications for every listened song use **-j** parameter:

```sh
./lastfm_monitor.py misiektoja -j
```

If you want to get email notifications when user listens to the same song on loop use **-x** parameter:

```sh
./lastfm_monitor.py misiektoja -x
```

### Saving listened songs to the CSV file

If you want to save all listened songs in the CSV file, use **-b** parameter with the name of the file (it will be automatically created if it does not exist):

```sh
./lastfm_monitor.py misiektoja -b lastfm_tracks_misiektoja.csv
```

### Automatic playing of tracks listened by the user in Spotify client

If you want the script to automatically play the tracks listened by the user in your local Spotify client use **-g** parameter:

```sh
./lastfm_monitor.py misiektoja -g
```

Your Spotify client needs to be installed & started for this feature to work.

In order to use this functionality you also need to have properly defined sp_dc cookie value as described [here](#spotify-sp_dc-cookie).

The script has full support for playing songs listened by the tracked user under **Linux** and **macOS**. It means it will automatically play the changed track, it will also automatically pause and resume playback following tracked user actions. It can also pause (or play indicated track) once user gets inactive (see **SP_USER_GOT_OFFLINE_TRACK_ID** variable).

For **Windows** it works in semi-way, i.e. if you have Spotify client running and you are not listening to any song, then the first song will be played automatically, but for others it will only do search and indicate the changed track in Spotify client, but you need to press the play button manually. I have not found better way to handle it locally on Windows yet (without using remote Spotify Web API).

You can change the method used for playing the songs under Linux, macOS and Windows by changing respective variables in *[lastfm_monitor.py](lastfm_monitor.py)* file. 

For **macOS** change **SPOTIFY_MACOS_PLAYING_METHOD** variable to one of the following values:
-  "**apple-script**" (recommended, **default**)
-  "trigger-url"

For **Linux** change **SPOTIFY_LINUX_PLAYING_METHOD** variable to one of the following values:
- "**dbus-send**" (most common one, **default**)
- "qdbus"
- "trigger-url"

For **Windows** change **SPOTIFY_WINDOWS_PLAYING_METHOD** variable to one of the following values:
- "**start-uri**" (recommended, **default**)
- "spotify-cmd"
- "trigger-url"

The recommended defaults should work for most people.

### Progress indicator

If you want to see nice progress indicator which should show you estimated position of what user is currently listening use **-p** parameter:

```sh
./lastfm_monitor.py misiektoja -p
```

<p align="center">
   <img src="./assets/lastfm_monitor_progress_indicator.png" alt="lastfm_monitor_progress_indicator" width="90%"/>
</p>

For this functionality to work correctly it is suggested to have the active check interval (**-k** parameter) set to low value (like 2-5 seconds).

### Getting track duration from Spotify

If you want the tool to fetch track duration from Spotify, instead of Last.fm which very often reports wrong duration (or none at all), then enable **USE_TRACK_DURATION_FROM_SPOTIFY** to **True** in *[lastfm_monitor.py](lastfm_monitor.py)* file or use **-r** parameter:

```sh
./lastfm_monitor.py misiektoja -r
```

In order to use this functionality you need to have properly defined sp_dc cookie value as described [here](#spotify-sp_dc-cookie).

You will be able to tell if the track duration comes from Spotify as it has S* suffix at the end (e.g. 3 minutes, 42 seconds S*), while those coming from Last.fm have L* (e.g. 2 minutes, 13 seconds L*).

You can disable showing the track duration marks (L*, S*) via **-q** parameter:

```sh
./lastfm_monitor.py misiektoja -r -q
```

Duration marks are not shown if the functionality to get track duration from Spotify is disabled.

### Check intervals and offline timer 

If you want to change the check interval when the user is offline to 10 seconds use **-c** parameter and when the user is active to 2 seconds use **-k** parameter:

```sh
./lastfm_monitor.py misiektoja -c 10 -k 2
```

If you want to change the time required to mark the user as inactive to 2 mins (120 seconds) use **-o** parameter (the timer starts once the user stops playing the music):

```sh
./lastfm_monitor.py misiektoja -o 120
```

### Controlling the script via signals (only macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new parameters.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets active/inactive or new offline entries show up (-a, -i, -f) |
| USR2 | Toggle email notifications for every song (-j) |
| HUP  | Toggle showing of progress indicator (-p) |
| CONT | Toggle email notifications for tracked songs (-t) |
| PIPE | Toggle email notifications when user plays song on loop (-x) |
| TRAP | Increase the inactivity check timer (by 30 seconds) (-o) |
| ABRT | Decrease the inactivity check timer (by 30 seconds) (-o) |

So if you want to change functionality of the running tool, just send the proper signal to the desired copy of the script.

I personally use **pkill** tool, so for example to toggle showing of progress indicator for tool instance monitoring the *misiektoja* user:

```sh
pkill -f -HUP "python3 ./lastfm_monitor.py misiektoja"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

### Private mode detection in Spotify

The script contains functionality to detect possible private mode used in Spotify and even estimates when private mode was used. It is enabled by default (not configurable).

It is NOT 100% accurate. I observed that very often when private mode is used (especially for longer time) it results in many duplicated entries created in Last.fm account after private mode is disabled. So different tracks have the same start timestamp.

I suspect it is related to some bug in Spotify and it mainly happens if the user has Spotify on multiple devices.

However keep in mind it is not 100% accurate. I observed duplicate entries also with no private mode, but in such case number of duplicate entries is limited. So do not treat it as something 100% certain, but it is pretty good indicator that private mode was used.

<p align="center">
   <img src="./assets/lastfm_monitor_private_mode.png" alt="lastfm_monitor_private_mode" width="90%"/>
</p>

### Other

Check other supported parameters using **-h**.

You can combine all the parameters mentioned earlier in monitoring mode (listing mode only supports **-l** and **-n**).

## Limitations

The script has been tested with Last.fm account integrated with Spotify client, however it should work with other clients as well.

## Coloring log output with GRC

If you use [GRC](https://github.com/garabik/grc) and want to have the tool's log output properly colored you can use the configuration file available [here](grc/conf.monitor_logs)

Change your grc configuration (typically *.grc/grc.conf*) and add this part:

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the *conf.monitor_logs* to your *.grc* directory and lastfm_monitor log files should be nicely colored when using *grc* tool.

## License

This project is licensed under the GPLv3 - see the [LICENSE](LICENSE) file for details
