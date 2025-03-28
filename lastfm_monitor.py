#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v2.0.1

Tool implementing real-time tracking of Last.fm users' music activity:
https://github.com/misiektoja/lastfm_monitor/

Python pip3 requirements:

pylast
spotipy (optional, only for Spotify-related features)
python-dateutil
requests
urllib3
"""

VERSION = "2.0.1"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Create your Last.fm 'API key' and 'Shared secret' by going to: https://www.last.fm/api/account/create
# Or get your existing one from: https://www.last.fm/api/accounts
# Put the respective values below (or use -u and -w parameters)
LASTFM_API_KEY = "your_lastfm_api_key"  # Last.fm API key
LASTFM_API_SECRET = "your_lastfm_api_secret"  # Last.fm Shared secret

# This setting is optional and only needed if you want to get track duration from Spotify (-r option, more accurate than Last.fm) or
# if you want to use -g option (track songs functionality), so we can find Spotify track ID and play it in your Spotify client
#
# Log in to Spotify Developer dashboard (https://developer.spotify.com/dashboard) and create a new app
# For the 'Redirect URL', you can use 'http://127.0.0.1:1234' (what we put here does not really matter as we are not using
# Authorization Code Flow, but Client Credentials Flow)
# Select 'Web API' for the API used
# Put the value of 'Client ID' and 'Client secret' below (or use -z parameter)
# The tool takes care of refreshing the access token so it should remain valid indefinitely
SP_CLIENT_ID = "your_spotify_app_client_id"  # Spotify Client ID
SP_CLIENT_SECRET = "your_spotify_app_client_secret"  # Spotify Client Secret

# SMTP settings for sending email notifications, you can leave it as is below and no notifications will be sent
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
# SMTP_HOST = "your_smtp_server_plaintext"
# SMTP_PORT = 25
# SMTP_USER = "your_smtp_user"
# SMTP_PASSWORD = "your_smtp_password"
# SMTP_SSL = False
# SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# How often do we perform checks for user activity when considered offline (not playing music right now); in seconds
# You can also use -c parameter
LASTFM_CHECK_INTERVAL = 10  # 10 seconds

# How often do we perform checks for user activity when online (playing music right now); in seconds
# You can also use -k parameter
LASTFM_ACTIVE_CHECK_INTERVAL = 3  # 3 seconds

# After what time period do we consider a user inactive (after their last activity); in seconds
# You can also use -o parameter
LASTFM_INACTIVITY_CHECK = 180  # 3 mins

# What method should we use to play the song listened by the tracked user in local Spotify client under macOS
# (i.e. when -g / --track_songs functionality is enabled)
# Methods:
#       "apple-script" (recommended)
#       "trigger-url"
SPOTIFY_MACOS_PLAYING_METHOD = "apple-script"

# What method should we use to play the song listened by the tracked user in local Spotify client under Linux OS
# (i.e. when -g / --track_songs functionality is enabled)
# Methods:
#       "dbus-send" (most common one)
#       "qdbus"
#       "trigger-url"
SPOTIFY_LINUX_PLAYING_METHOD = "dbus-send"

# What method should we use to play the song listened by the tracked user in local Spotify client under Windows OS
# (if -g / --track_songs functionality is enabled)
# Methods:
#       "start-uri" (recommended)
#       "spotify-cmd"
#       "trigger-url"
SPOTIFY_WINDOWS_PLAYING_METHOD = "start-uri"

# How many consecutive plays of the same song is considered as being on loop
SONG_ON_LOOP_VALUE = 3

# When do we consider the song as being skipped; this parameter is used if track duration is NOT available from Last.fm/Spotify
# in seconds
SKIPPED_SONG_THRESHOLD1 = 35  # song is treated as skipped if played for <=35 seconds

# When do we consider the song as being skipped; this parameter is used if track duration is available from Last.fm/Spotify; fraction
SKIPPED_SONG_THRESHOLD2 = 0.55  # song is treated as skipped if played for <=55% of track duration

# When do we consider the song as being played for longer than track duration; it will happen either if the play time is longer than 130% of track duration of if more than 30 seconds; fraction and seconds
LONGER_SONG_THRESHOLD1 = 1.30  # song is treated as being played longer than track duration if played longer than >= 130% of track duration
LONGER_SONG_THRESHOLD2 = 30  # song is treated as being played longer than track duration if played longer than >= 30 seconds of track duration

# Set the value of the variable below to True if you want to get the track duration from Spotify
# It is recommended since Last.fm very often does not have it or has inaccurate info
# We will try to get track duration from Spotify only if you have defined proper SP_CLIENT_ID & SP_CLIENT_SECRET values earlier
# (or via -z parameter)
# You can also use -r parameter
USE_TRACK_DURATION_FROM_SPOTIFY = False

# Type Spotify ID of the "finishing" track to play when user gets offline, only needed for track_songs functionality;
# leave empty to simply pause
# SP_USER_GOT_OFFLINE_TRACK_ID = "5wCjNjnugSUqGDBrmQhn0e"
SP_USER_GOT_OFFLINE_TRACK_ID = ""

# Delay after which the above track gets paused, type 0 to play infinitely until user pauses manually; in seconds
SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE = 5  # 5 seconds

# If the value is greater than 0, it will show when the user stops playing or resumes while active.
# The play break is assumed to be LASTFM_BREAK_CHECK_MULTIPLIER*LASTFM_ACTIVE_CHECK_INTERVAL
# So if LASTFM_BREAK_CHECK_MULTIPLIER = 4 and LASTFM_ACTIVE_CHECK_INTERVAL = 3, then music pause will be reported after 4*3=12 seconds of inactivity
# You can also use -m parameter
LASTFM_BREAK_CHECK_MULTIPLIER = 4

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL = 21600  # 6 hours

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL = 'http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# The name of the .log file; the tool by default will output its messages to lastfm_monitor_username.log file
LF_LOGFILE = "lastfm_monitor"

# Value used by signal handlers increasing/decreasing the inactivity check (LASTFM_INACTIVITY_CHECK); in seconds
LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# How many 50x errors need to show up in the defined time to display error message in the console - it is to suppress sporadic issues with Last.fm API endpoint; adjust the parameters according to the LASTFM_CHECK_INTERVAL & LASTFM_ACTIVE_CHECK_INTERVAL timers
# If more than 15 Last.fm API related issues in 2 mins - we will show the error message
ERROR_500_NUMBER_LIMIT = 15
ERROR_500_TIME_LIMIT = 120  # 2 min

# How many network related errors need to show up in the defined time to display error message in the console - it is to suppress sporadic issues with internet connectivity; adjust the parameters according to the LASTFM_CHECK_INTERVAL & LASTFM_ACTIVE_CHECK_INTERVAL timers
# If more than 15 network related issues in 2 mins - we will show the error message
ERROR_NETWORK_ISSUES_NUMBER_LIMIT = 15
ERROR_NETWORK_ISSUES_TIME_LIMIT = 120  # 2 min

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Strings removed from track names for generating proper Genius search URLs
re_search_str = r'remaster|extended|original mix|remix|original soundtrack|radio( |-)edit|\(feat\.|( \(.*version\))|( - .*version)'
re_replace_str = r'( - (\d*)( )*remaster$)|( - (\d*)( )*remastered( version)*( \d*)*.*$)|( \((\d*)( )*remaster\)$)|( - (\d+) - remaster$)|( - extended$)|( - extended mix$)|( - (.*); extended mix$)|( - extended version$)|( - (.*) remix$)|( - remix$)|( - remixed by .*$)|( - original mix$)|( - .*original soundtrack$)|( - .*radio( |-)edit$)|( \(feat\. .*\)$)|( \(\d+.*Remaster.*\)$)|( \(.*Version\))|( - .*version)'

# Default value for Spotify network-related timeouts in functions; in seconds
FUNCTION_TIMEOUT = 5  # 5 seconds

# How many recent tracks we fetch after start and every time user gets online
RECENT_TRACKS_NUMBER = 10

# Variables for caching functionality of the Spotify access token to avoid unnecessary refreshing
SP_CACHED_TOKEN = None

TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / LASTFM_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Artist', 'Track', 'Album']

active_notification = False
inactive_notification = False
song_notification = False
track_notification = False
offline_entries_notification = False
song_on_loop_notification = False
progress_indicator = False
track_songs = False
do_not_show_duration_marks = False

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"


import sys

if sys.version_info < (3, 9):
    print("* Error: Python version 3.9 or higher required !")
    sys.exit(1)

import time
import string
import json
import os
from datetime import datetime
from dateutil import relativedelta
import calendar
import requests as req
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import csv
import pylast
import urllib
from urllib.parse import quote_plus, quote
import subprocess
import platform
import re
import ipaddress
from itertools import tee, islice, chain
from html import escape


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.logfile.write(message)
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
        pass


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)


# Function to check internet connectivity
def check_internet():
    url = CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT)
        print("OK")
        return True
    except Exception as e:
        print(f"No connectivity, please check your network - {e}")
        sys.exit(1)


# Function to convert absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952),  # approximation
        ('months', 2629746),  # approximation
        ('weeks', 604800),    # 60 * 60 * 24 * 7
        ('days', 86400),      # 60 * 60 * 24
        ('hours', 3600),      # 60 * 60
        ('minutes', 60),
        ('seconds', 1),
    )
    result = []

    if seconds > 0:
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append(f"{value} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Function to calculate time span between two timestamps in seconds
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if type(timestamp1) is int:
        dt1 = datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is float:
        ts1 = int(round(ts1))
        dt1 = datetime.fromtimestamp(ts1)
    elif type(timestamp1) is datetime:
        dt1 = timestamp1
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2 = datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is float:
        ts2 = int(round(ts2))
        dt2 = datetime.fromtimestamp(ts2)
    elif type(timestamp2) is datetime:
        dt2 = timestamp2
        ts2 = int(round(dt2.timestamp()))
    else:
        return ""

    if ts1 >= ts2:
        ts_diff = ts1 - ts2
    else:
        ts_diff = ts2 - ts1
        dt1, dt2 = dt2, dt1

    if ts_diff > 0:
        date_diff = relativedelta.relativedelta(dt1, dt2)
        years = date_diff.years
        months = date_diff.months
        weeks = date_diff.weeks
        if not show_weeks:
            weeks = 0
        days = date_diff.days
        if weeks > 0:
            days = days - (weeks * 7)
        hours = date_diff.hours
        if (not show_hours and ts_diff > 86400):
            hours = 0
        minutes = date_diff.minutes
        if (not show_minutes and ts_diff > 3600):
            minutes = 0
        seconds = date_diff.seconds
        if (not show_seconds and ts_diff > 60):
            seconds = 0
        date_list = [years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval > 0:
                name = intervals[index]
                if interval == 1:
                    name = name.rstrip('s')
                result.append(f"{interval} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Function to send email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            print("Error sending email - SMTP settings are incorrect (invalid IP address/FQDN in SMTP_HOST)")
            return 1

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("Error sending email - SMTP settings are incorrect (invalid port number in SMTP_PORT)")
        return 1

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        print("Error sending email - SMTP settings are incorrect (invalid email in SENDER_EMAIL or RECEIVER_EMAIL)")
        return 1

    if not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password":
        print("Error sending email - SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD variables)")
        return 1

    if not subject or not isinstance(subject, str):
        print("Error sending email - SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    if not body and not body_html:
        print("Error sending email - SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
        return 1

    try:
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
        smtpObj.login(SMTP_USER, SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] = str(Header(subject, 'utf-8'))

        if body:
            part1 = MIMEText(body, 'plain')
            part1 = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
            email_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            part2 = MIMEText(body_html.encode('utf-8'), 'html', _charset='utf-8')
            email_msg.attach(part2)

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtpObj.quit()
    except Exception as e:
        print(f"Error sending email - {e}")
        return 1
    return 0


# Function to write CSV entry
def write_csv_entry(csv_file_name, timestamp, artist, track, album):
    try:
        csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Date': timestamp, 'Artist': artist, 'Track': track, 'Album': album})
        csv_file.close()
    except Exception:
        raise


# Function to return the timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]}, {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


# Function to print the current timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("---------------------------------------------------------------------------------------------------------")


# Function to return the timestamp/datetime object in human readable format (long version); eg. Sun, 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime("%d %b %Y, %H:%M:%S")}')


# Function to return the timestamp/datetime object in human readable format (short version); eg.
# Sun 21 Apr 15:08
# Sun 21 Apr 24, 15:08 (if show_year == True and current year is different)
# Sun 21 Apr (if show_hour == False)
def get_short_date_from_ts(ts, show_year=False, show_hour=True):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_hour:
        hour_strftime = " %H:%M"
    else:
        hour_strftime = ""

    if show_year and int(datetime.fromtimestamp(ts_new).strftime("%Y")) != int(datetime.now().strftime("%Y")):
        if show_hour:
            hour_prefix = ","
        else:
            hour_prefix = ""
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b %y{hour_prefix}{hour_strftime}")}')
    else:
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b{hour_strftime}")}')


# Function to return the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_seconds:
        out_strf = "%H:%M:%S"
    else:
        out_strf = "%H:%M"
    return (str(datetime.fromtimestamp(ts_new).strftime(out_strf)))


# Function to return the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False):
    if type(ts1) is datetime:
        ts1_new = int(round(ts1.timestamp()))
    elif type(ts1) is int:
        ts1_new = ts1
    elif type(ts1) is float:
        ts1_new = int(round(ts1))
    else:
        return ""

    if type(ts2) is datetime:
        ts2_new = int(round(ts2.timestamp()))
    elif type(ts2) is int:
        ts2_new = ts2
    elif type(ts2) is float:
        ts2_new = int(round(ts2))
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new, show_seconds=True)}"
    else:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_short_date_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_date_from_ts(ts2_new)}"
    return (str(out_str))


# Signal handler for SIGUSR1 allowing to switch active/inactive/offline entries email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global active_notification
    global inactive_notification
    global offline_entries_notification
    active_notification = not active_notification
    inactive_notification = not inactive_notification
    offline_entries_notification = not offline_entries_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active = {active_notification}] [inactive = {inactive_notification}] [offline entries = {offline_entries_notification}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGUSR2 allowing to switch every song email notifications
def toggle_song_notifications_signal_handler(sig, frame):
    global song_notification
    song_notification = not song_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [every song = {song_notification}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGHUP allowing to switch progress indicator in the output
def toggle_progress_indicator_signal_handler(sig, frame):
    global progress_indicator
    progress_indicator = not progress_indicator
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Progress indicator enabled: {progress_indicator}")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGCONT allowing to switch tracked songs email notifications
def toggle_track_notifications_signal_handler(sig, frame):
    global track_notification
    track_notification = not track_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [tracked = {track_notification}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGPIPE allowing to switch songs on loop email notifications
def toggle_songs_on_loop_notifications_signal_handler(sig, frame):
    global song_on_loop_notification
    song_on_loop_notification = not song_on_loop_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [songs on loop = {song_on_loop_notification}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGTRAP allowing to increase inactivity check interval by LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE seconds
def increase_inactivity_check_signal_handler(sig, frame):
    global LASTFM_INACTIVITY_CHECK
    LASTFM_INACTIVITY_CHECK = LASTFM_INACTIVITY_CHECK + LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Last.fm timers: [inactivity: {display_time(LASTFM_INACTIVITY_CHECK)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGABRT allowing to decrease inactivity check interval by LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE seconds
def decrease_inactivity_check_signal_handler(sig, frame):
    global LASTFM_INACTIVITY_CHECK
    if LASTFM_INACTIVITY_CHECK - LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE > 0:
        LASTFM_INACTIVITY_CHECK = LASTFM_INACTIVITY_CHECK - LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Last.fm timers: [inactivity: {display_time(LASTFM_INACTIVITY_CHECK)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Function to access the previous and next elements of the list
def previous_and_next(some_iterable):
    prevs, items, nexts = tee(some_iterable, 3)
    prevs = chain([None], prevs)
    nexts = chain(islice(nexts, 1, None), [None])
    return zip(prevs, items, nexts)


# Function preparing Spotify, Apple & Genius search URLs for specified track
def get_spotify_apple_genius_search_urls(artist, track):
    spotify_search_string = quote_plus(f"{artist} {track}")
    genius_search_string = f"{artist} {track}"
    if re.search(re_search_str, genius_search_string, re.IGNORECASE):
        genius_search_string = re.sub(re_replace_str, '', genius_search_string, flags=re.IGNORECASE)
    apple_search_string = quote(f"{artist} {track}")
    spotify_search_url = f"https://open.spotify.com/search/{spotify_search_string}?si=1"
    apple_search_url = f"https://music.apple.com/pl/search?term={apple_search_string}"
    genius_search_url = f"https://genius.com/search?q={quote_plus(genius_search_string)}"
    youtube_music_search_url = f"https://music.youtube.com/search?q={spotify_search_string}"
    return spotify_search_url, apple_search_url, genius_search_url, youtube_music_search_url


# Function returning the list of recently played Last.fm tracks
def lastfm_get_recent_tracks(username, network, number):
    try:
        recent_tracks = network.get_user(username).get_recent_tracks(limit=number)
        return recent_tracks
    except Exception:
        raise


# Function displaying the list of recently played Last.fm tracks
def lastfm_list_tracks(username, user, network, number):
    try:
        new_track = user.get_now_playing()
        recent_tracks = lastfm_get_recent_tracks(username, network, number)
    except Exception as e:
        print(f"* Error: cannot display recent tracks for the user - {e}")
        sys.exit(1)
    last_played = 0

    i = 0
    p = 0
    duplicate_entries = False
    for previous, t, nxt in previous_and_next(reversed(recent_tracks)):
        i += 1
        if i == len(recent_tracks):
            last_played = int(t.timestamp)
        print(f'{i}\t{datetime.fromtimestamp(int(t.timestamp)).strftime("%d %b %Y, %H:%M:%S")}\t{calendar.day_abbr[(datetime.fromtimestamp(int(t.timestamp))).weekday()]}\t{t.track}')
        if previous:
            if previous.timestamp == t.timestamp:
                p += 1
                duplicate_entries = True
                print("DUPLICATE ENTRY")
    print("---------------------------------------------------------------------------------------------------------")
    if last_played > 0 and not new_track:
        print(f"*** User played last time {calculate_timespan(int(time.time()), last_played, show_seconds=True)} ago! ({get_date_from_ts(last_played)})")

    if duplicate_entries:
        print(f"*** Duplicate entries ({p}) found, possible PRIVATE MODE")

    if new_track:
        artist = str(new_track.artist)
        track = str(new_track.title)
        album = str(new_track.info['album'])
        print("*** User is currently ACTIVE !")
        print(f"\nTrack:\t\t{artist} - {track}")
        print(f"Album:\t\t{album}")


# Function sending a lightweight request to check token validity since Spotipy deprecates as_dict=True and there is no
# get_cached_token() method implemented yet for client credentials auth flow
def check_token_validity(token):
    url = "https://api.spotify.com/v1/browse/categories"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": 1, "fields": "categories.items(id)"}

    try:
        return req.get(url, headers=headers, params=params, timeout=FUNCTION_TIMEOUT).status_code == 200
    except Exception:
        return False


# Function getting Spotify access token based on provided sp_client_id & sp_client_secret values
def spotify_get_access_token(sp_client_id, sp_client_secret):
    global SP_CACHED_TOKEN

    try:
        from spotipy.oauth2 import SpotifyClientCredentials
    except ImportError:
        print("* Warning: the 'spotipy' package is required for Spotify-related features, install it with `pip install spotipy`")
        return None

    if SP_CACHED_TOKEN and check_token_validity(SP_CACHED_TOKEN):
        return SP_CACHED_TOKEN

    auth_manager = SpotifyClientCredentials(client_id=sp_client_id, client_secret=sp_client_secret)
    SP_CACHED_TOKEN = auth_manager.get_access_token(as_dict=False)

    return SP_CACHED_TOKEN


# Function converting Spotify URI (e.g. spotify:user:username) to URL (e.g. https://open.spotify.com/user/username)
def spotify_convert_uri_to_url(uri):
    # add si parameter so link opens in native Spotify app after clicking
    si = "?si=1"
    # si=""

    url = ""
    if "spotify:user:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/user/{s_id}{si}"
    elif "spotify:artist:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/artist/{s_id}{si}"
    elif "spotify:track:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/track/{s_id}{si}"
    elif "spotify:album:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/album/{s_id}{si}"
    elif "spotify:playlist:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/playlist/{s_id}{si}"

    return url


# Function processing track items returned by Spotify search Web API
def spotify_search_process_track_items(track_items, track):
    sp_track_uri_id = None
    sp_track_duration = 0

    for item in track_items:
        if str(item.get("name")).lower() == str(track).lower():
            sp_track_uri_id = item.get("id")
            sp_track_duration = int(item.get("duration_ms") / 1000)
            break
    if not sp_track_uri_id:
        for item in track_items:
            if str(track).lower() in str(item.get("name")).lower():
                sp_track_uri_id = item.get("id")
                sp_track_duration = int(item.get("duration_ms") / 1000)
                break

    return sp_track_uri_id, sp_track_duration


# Function returning Spotify track ID & duration for specific artist, track and optionally album
def spotify_search_song_trackid_duration(access_token, artist, track, album=""):
    re_chars_to_remove = r'([\'])'
    artist_sanitized = re.sub(re_chars_to_remove, '', artist, flags=re.IGNORECASE)
    track_sanitized = re.sub(re_chars_to_remove, '', track, flags=re.IGNORECASE)
    album_sanitized = re.sub(re_chars_to_remove, '', album, flags=re.IGNORECASE)

    url1 = f'https://api.spotify.com/v1/search?q={quote_plus(f"artist:{artist_sanitized} track:{track_sanitized} album:{album_sanitized}")}&type=track&limit=5'
    url2 = f'https://api.spotify.com/v1/search?q={quote_plus(f"artist:{artist_sanitized} track:{track_sanitized}")}&type=track&limit=5'

    headers = {"Authorization": "Bearer " + access_token}

    sp_track_uri_id = None
    sp_track_duration = 0

    if album:
        try:
            response = req.get(url1, headers=headers, timeout=FUNCTION_TIMEOUT)
            response.raise_for_status()
            json_response = response.json()
            if json_response.get("tracks"):
                if json_response["tracks"].get("total") > 0:
                    sp_track_uri_id, sp_track_duration = spotify_search_process_track_items(json_response["tracks"]["items"], track)
        except Exception:
            pass

    if not sp_track_uri_id:
        try:
            response = req.get(url2, headers=headers, timeout=FUNCTION_TIMEOUT)
            response.raise_for_status()
            json_response = response.json()
            if json_response.get("tracks"):
                if json_response["tracks"].get("total") > 0:
                    sp_track_uri_id, sp_track_duration = spotify_search_process_track_items(json_response["tracks"]["items"], track)
        except Exception:
            pass

    return sp_track_uri_id, sp_track_duration


def spotify_macos_play_song(sp_track_uri_id, method=SPOTIFY_MACOS_PLAYING_METHOD):
    if method == "apple-script":    # apple-script
        script = f'tell app "Spotify" to play track "spotify:track:{sp_track_uri_id}"'
        proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        stdout, stderr = proc.communicate(script)
    else:                           # trigger-url - just trigger track URL in the client
        subprocess.call(('open', spotify_convert_uri_to_url(f"spotify:track:{sp_track_uri_id}")))


def spotify_macos_play_pause(action, method=SPOTIFY_MACOS_PLAYING_METHOD):
    if method == "apple-script":    # apple-script
        if str(action).lower() == "pause":
            script = 'tell app "Spotify" to pause'
            proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            stdout, stderr = proc.communicate(script)
        elif str(action).lower() == "play":
            script = 'tell app "Spotify" to play'
            proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            stdout, stderr = proc.communicate(script)


def spotify_linux_play_song(sp_track_uri_id, method=SPOTIFY_LINUX_PLAYING_METHOD):
    if method == "dbus-send":       # dbus-send
        subprocess.call((f"dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.OpenUri string:'spotify:track:{sp_track_uri_id}'"), shell=True)
    elif method == "qdbus":         # qdbus
        subprocess.call((f"qdbus org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.OpenUri spotify:track:{sp_track_uri_id}"), shell=True)
    else:                           # trigger-url - just trigger track URL in the client
        subprocess.call(('xdg-open', spotify_convert_uri_to_url(f"spotify:track:{sp_track_uri_id}")), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def spotify_linux_play_pause(action, method=SPOTIFY_LINUX_PLAYING_METHOD):
    if method == "dbus-send":       # dbus-send
        if str(action).lower() == "pause":
            subprocess.call((f"dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Pause"), shell=True)
        elif str(action).lower() == "play":
            subprocess.call((f"dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Play"), shell=True)
    elif method == "qdbus":         # qdbus
        if str(action).lower() == "pause":
            subprocess.call((f"qdbus org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Pause"), shell=True)
        elif str(action).lower() == "play":
            subprocess.call((f"qdbus org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Play"), shell=True)


def spotify_win_play_song(sp_track_uri_id, method=SPOTIFY_WINDOWS_PLAYING_METHOD):
    WIN_SPOTIFY_APP_PATH = r'%APPDATA%\Spotify\Spotify.exe'

    if method == "start-uri":       # start-uri
        subprocess.call((f"start spotify:track:{sp_track_uri_id}"), shell=True)
    elif method == "spotify-cmd":   # spotify-cmd
        subprocess.call((f"{WIN_SPOTIFY_APP_PATH} --uri=spotify:track:{sp_track_uri_id}"), shell=True)
    else:                           # trigger-url - just trigger track URL in the client
        os.startfile(spotify_convert_uri_to_url(f"spotify:track:{sp_track_uri_id}"))


# Main function monitoring activity of the specified Last.fm user
def lastfm_monitor_user(user, network, username, tracks, error_notification, csv_file_name, csv_exists):

    lf_active_ts_start = 0
    lf_active_ts_last = 0
    lf_track_ts_start = 0
    lf_track_ts_start_old = 0
    lf_track_ts_start_after_resume = 0
    lf_user_online = False
    alive_counter = 0
    track_duration = 0
    playing_paused = False
    playing_paused_ts = 0
    playing_resumed_ts = 0
    paused_counter = 0
    playing_track = None
    new_track = None
    listened_songs = 0
    looped_songs = 0
    skipped_songs = 0
    signal_previous_the_same = False
    artist = ""
    track = ""
    artist_old = ""
    track_old = ""
    song_on_loop = 0
    sp_track_uri_id = None
    sp_track_duration = 0
    duration_mark = ""
    pauses_number = 0
    error_500_counter = 0
    error_500_start_ts = 0
    error_network_issue_counter = 0
    error_network_issue_start_ts = 0

    try:
        if csv_file_name:
            csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print(f"* Error - {e}")

    lastfm_last_activity_file = f"lastfm_{username}_last_activity.json"
    last_activity_read = []
    last_activity_ts = 0
    last_activity_artist = ""
    last_activity_track = ""

    if os.path.isfile(lastfm_last_activity_file):
        try:
            with open(lastfm_last_activity_file, 'r', encoding="utf-8") as f:
                last_activity_read = json.load(f)
        except Exception as e:
            print(f"* Cannot load last status from '{lastfm_last_activity_file}' file - {e}")
        if last_activity_read:
            last_activity_ts = last_activity_read[0]
            last_activity_artist = last_activity_read[1]
            last_activity_track = last_activity_read[2]
            lastfm_last_activity_file_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(lastfm_last_activity_file)))
            lastfm_last_activity_file_mdate = lastfm_last_activity_file_mdate_dt.strftime("%d %b %Y, %H:%M:%S")
            lastfm_last_activity_file_mdate_weekday = str(calendar.day_abbr[(lastfm_last_activity_file_mdate_dt).weekday()])
            print(f"* Last activity loaded from file '{lastfm_last_activity_file}' ({lastfm_last_activity_file_mdate_weekday} {lastfm_last_activity_file_mdate})")

    try:
        new_track = user.get_now_playing()
        recent_tracks = lastfm_get_recent_tracks(username, network, RECENT_TRACKS_NUMBER)
    except Exception as e:
        print(f"* Error - {e}")
        sys.exit(1)

    last_track_start_ts_old2 = int(recent_tracks[0].timestamp)
    lf_track_ts_start_old = last_track_start_ts_old2

    # User is offline (does not play music at the moment)
    if new_track is None:
        app_started_and_user_offline = True
        playing_track = None
        last_track_start_ts_old = 0
        lf_user_online = False
        lf_active_ts_last = int(recent_tracks[0].timestamp)
        if lf_active_ts_last >= last_activity_ts:
            last_activity_artist = recent_tracks[0].track.artist
            last_activity_track = recent_tracks[0].track.title
        elif lf_active_ts_last < last_activity_ts and last_activity_ts > 0:
            lf_active_ts_last = last_activity_ts

        last_activity_dt = datetime.fromtimestamp(lf_active_ts_last).strftime("%d %b %Y, %H:%M:%S")
        last_activity_ts_weekday = str(calendar.day_abbr[(datetime.fromtimestamp(lf_active_ts_last)).weekday()])

        artist_old = str(last_activity_artist)
        track_old = str(last_activity_track)

        print(f"* Last activity:\t\t{last_activity_ts_weekday} {last_activity_dt}")
        print(f"* Last track:\t\t\t{last_activity_artist} - {last_activity_track}")

        spotify_search_url, apple_search_url, genius_search_url, youtube_music_search_url = get_spotify_apple_genius_search_urls(str(last_activity_artist), str(last_activity_track))

        print(f"\n* Spotify search URL:\t\t{spotify_search_url}")
        print(f"* Apple search URL:\t\t{apple_search_url}")
        print(f"* YouTube Music search URL:\t{youtube_music_search_url}")
        print(f"* Genius lyrics URL:\t\t{genius_search_url}\n")

        print(f"*** User is OFFLINE for {calculate_timespan(int(time.time()), lf_active_ts_last, show_seconds=False)} !")

    # User is online (plays music at the moment)
    else:
        app_started_and_user_offline = False
        lf_active_ts_start = int(time.time())
        lf_active_ts_last = lf_active_ts_start
        lf_track_ts_start = lf_active_ts_start
        lf_track_ts_start_after_resume = lf_active_ts_start
        playing_resumed_ts = lf_active_ts_start
        song_on_loop = 1
        artist = str(new_track.artist)
        track = str(new_track.title)
        album = str(new_track.info['album'])
        artist_old = artist
        track_old = track
        print(f"\nTrack:\t\t\t\t{artist} - {track}")
        print(f"Album:\t\t\t\t{album}")

        if (USE_TRACK_DURATION_FROM_SPOTIFY or track_songs) and SP_CLIENT_ID and SP_CLIENT_SECRET and SP_CLIENT_ID != "your_spotify_app_client_id" and SP_CLIENT_SECRET != "your_spotify_app_client_secret":
            accessToken = spotify_get_access_token(SP_CLIENT_ID, SP_CLIENT_SECRET)
            if accessToken:
                sp_track_uri_id, sp_track_duration = spotify_search_song_trackid_duration(accessToken, artist, track, album)
                if not USE_TRACK_DURATION_FROM_SPOTIFY:
                    sp_track_duration = 0

        if sp_track_duration > 0:
            track_duration = sp_track_duration
            if not do_not_show_duration_marks:
                duration_mark = " S*"
        else:
            try:
                track_duration = pylast.Track(new_track.artist, new_track.title, network).get_duration()
                if track_duration > 0:
                    if USE_TRACK_DURATION_FROM_SPOTIFY:
                        if not do_not_show_duration_marks:
                            duration_mark = " L*"
                    track_duration = int(str(track_duration)[0:-3])
            except Exception as e:
                track_duration = 0
                pass

        if track_duration > 0:
            print(f"Duration:\t\t\t{display_time(track_duration)}{duration_mark}")

        spotify_search_url, apple_search_url, genius_search_url, youtube_music_search_url = get_spotify_apple_genius_search_urls(str(artist), str(track))

        print(f"\nSpotify search URL:\t\t{spotify_search_url}")
        print(f"Apple search URL:\t\t{apple_search_url}")
        print(f"YouTube Music search URL:\t{youtube_music_search_url}")
        print(f"Genius lyrics URL:\t\t{genius_search_url}")

        print("\n*** User is currently ACTIVE !")

        listened_songs = 1

        last_activity_to_save = []
        last_activity_to_save.append(lf_track_ts_start)
        last_activity_to_save.append(artist)
        last_activity_to_save.append(track)
        last_activity_to_save.append(album)

        try:
            with open(lastfm_last_activity_file, 'w', encoding="utf-8") as f:
                json.dump(last_activity_to_save, f, indent=2)
        except Exception as e:
            print(f"* Cannot save last status to '{lastfm_last_activity_file}' file - {e}")

        try:
            if csv_file_name:
                write_csv_entry(csv_file_name, datetime.fromtimestamp(int(lf_track_ts_start)), artist, track, album)
        except Exception as e:
            print(f"* Cannot write CSV entry - {e}")

        duration_m_body = ""
        duration_m_body_html = ""
        if track_duration > 0:
            duration_m_body = f"\nDuration: {display_time(track_duration)}{duration_mark}"
            duration_m_body_html = f"<br>Duration: {display_time(track_duration)}{duration_mark}"

        m_subject = f"Last.fm user {username} is active: '{artist} - {track}'"
        m_body = f"Track: {artist} - {track}{duration_m_body}\nAlbum: {album}\n\nSpotify search URL: {spotify_search_url}\nApple search URL: {apple_search_url}\nYouTube Music search URL:{youtube_music_search_url}\nGenius lyrics URL: {genius_search_url}\n\nLast activity: {get_date_from_ts(lf_active_ts_last)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
        m_body_html = f"<html><head></head><body>Track: <b><a href=\"{spotify_search_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}<br>Album: {escape(album)}<br><br>Apple search URL: <a href=\"{apple_search_url}\">{escape(artist)} - {escape(track)}</a><br>YouTube Music search URL: <a href=\"{youtube_music_search_url}\">{escape(artist)} - {escape(track)}</a><br>Genius lyrics URL: <a href=\"{genius_search_url}\">{escape(artist)} - {escape(track)}</a><br><br>Last activity: <b>{get_date_from_ts(lf_active_ts_last)}</b>{get_cur_ts('<br>Timestamp: ')}</body></html>"

        if active_notification:
            print(f"Sending email notification to {RECEIVER_EMAIL}")
            send_email(m_subject, m_body, m_body_html, SMTP_SSL)

        playing_track = new_track
        last_track_start_ts_old = int(recent_tracks[0].timestamp)
        lf_user_online = True

        # If tracking functionality is enabled then play the current song via Spotify client
        if track_songs and sp_track_uri_id:
            if platform.system() == 'Darwin':       # macOS
                spotify_macos_play_song(sp_track_uri_id)
            elif platform.system() == 'Windows':    # Windows
                spotify_win_play_song(sp_track_uri_id)
            else:                                   # Linux variants
                spotify_linux_play_song(sp_track_uri_id)

    i = 0
    p = 0
    duplicate_entries = False
    print("\nList of recently listened tracks:\n")
    for previous, t, nxt in previous_and_next(reversed(recent_tracks)):
        i += 1
        print(f'{i}\t{datetime.fromtimestamp(int(t.timestamp)).strftime("%d %b %Y, %H:%M:%S")}\t{calendar.day_abbr[(datetime.fromtimestamp(int(t.timestamp))).weekday()]}\t{t.track}')
        if previous:
            if previous.timestamp == t.timestamp:
                p += 1
                duplicate_entries = True
                print("DUPLICATE ENTRY")

    if duplicate_entries:
        print(f"*** Duplicate entries ({p}) found, possible PRIVATE MODE")

    print(f"\nTracks/albums to monitor: {tracks}")

    print_cur_ts("\nTimestamp:\t\t\t")

    email_sent = False

    # Main loop
    while True:
        try:
            recent_tracks = lastfm_get_recent_tracks(username, network, 1)
            last_track_start_ts = int(recent_tracks[0].timestamp)
            new_track = user.get_now_playing()
            email_sent = False

            lf_current_ts = int(time.time()) - LASTFM_ACTIVE_CHECK_INTERVAL

            # Detecting new Last.fm entries when user is offline
            if not lf_user_online:
                if last_track_start_ts > last_track_start_ts_old2:
                    print("\n*** New last.fm entries showed up while user was offline!\n")
                    lf_track_ts_start_old = last_track_start_ts
                    duplicate_entries = False
                    i = 0
                    added_entries_list = ""
                    try:
                        recent_tracks_while_offline = lastfm_get_recent_tracks(username, network, 100)
                        for previous, t, nxt in previous_and_next(reversed(recent_tracks_while_offline)):
                            if int(t.timestamp) > int(last_track_start_ts_old2):
                                if 0 <= (lf_track_ts_start + LASTFM_ACTIVE_CHECK_INTERVAL - int(t.timestamp)) <= 60:
                                    continue
                                print(f'{datetime.fromtimestamp(int(t.timestamp)).strftime("%d %b %Y, %H:%M:%S")}\t{calendar.day_abbr[(datetime.fromtimestamp(int(t.timestamp))).weekday()]}\t{t.track}')
                                added_entries_list += f'{datetime.fromtimestamp(int(t.timestamp)).strftime("%d %b %Y, %H:%M:%S")}, {calendar.day_abbr[(datetime.fromtimestamp(int(t.timestamp))).weekday()]}: {t.track}\n'
                                i += 1
                                if previous:
                                    if previous.timestamp == t.timestamp:
                                        duplicate_entries = True
                                        print("DUPLICATE ENTRY")
                                if csv_file_name:
                                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(t.timestamp)), str(t.track.artist), str(t.track.title), str(t.album))
                    except Exception as e:
                        print(f"* Error - {e}")

                    if i > 0 and offline_entries_notification:
                        if added_entries_list:
                            added_entries_list_mbody = f"\n\n{added_entries_list}"
                        m_subject = f"Last.fm user {username}: new entries showed up while user was offline"
                        m_body = f"New last.fm entries showed up while user was offline!{added_entries_list_mbody}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, "", SMTP_SSL)

                    print_cur_ts("\nTimestamp:\t\t\t")

            # User is online (plays music at the moment)
            if new_track is not None:

                # User paused music earlier
                if playing_paused is True and lf_user_online:
                    playing_resumed_ts = lf_current_ts
                    lf_track_ts_start_after_resume += (playing_resumed_ts - playing_paused_ts)
                    paused_counter += (int(playing_resumed_ts) - int(playing_paused_ts))
                    print(f"User RESUMED playing after {calculate_timespan(int(playing_resumed_ts), int(playing_paused_ts))}")
                    print_cur_ts("\nTimestamp:\t\t\t")

                    # If tracking functionality is enabled then RESUME the current song via Spotify client
                    if track_songs:
                        if platform.system() == 'Darwin':       # macOS
                            spotify_macos_play_pause("play")
                        elif platform.system() == 'Windows':    # Windows
                            pass
                        else:                                   # Linux variants
                            spotify_linux_play_pause("play")

                playing_paused = False

                # Trying to overcome the issue with Last.fm API reporting newly played song (but still continues the same)
                if (lf_current_ts <= (lf_track_ts_start + 20)) and (last_track_start_ts > last_track_start_ts_old) and (new_track == playing_track):
                    last_track_start_ts_old = last_track_start_ts

                # Track has changed
                if (new_track != playing_track or (last_track_start_ts > last_track_start_ts_old and last_track_start_ts > lf_track_ts_start_old - 20)):

                    alive_counter = 0

                    if new_track == playing_track:
                        song_on_loop += 1
                        if song_on_loop == SONG_ON_LOOP_VALUE:
                            looped_songs += 1
                    else:
                        song_on_loop = 1

                    playing_track = new_track
                    artist = str(playing_track.artist)
                    track = str(playing_track.title)
                    album = str(playing_track.info['album'])
                    info = playing_track.info

                    played_for_m_body = ""
                    played_for_m_body_html = ""

                    # Handling how long user played the previous track, if skipped it etc. - in case track duration is available
                    if track_duration > 0 and lf_track_ts_start_after_resume > 0 and lf_user_online:
                        played_for_display = False
                        played_for_time = lf_current_ts - lf_track_ts_start_after_resume

                        listened_percentage = (played_for_time) / (track_duration - 1)

                        if (played_for_time) < (track_duration - LASTFM_ACTIVE_CHECK_INTERVAL - 1):
                            played_for = f"{display_time(played_for_time)} (out of {display_time(track_duration)})"
                            played_for_html = f"<b>{display_time(played_for_time)}</b> (out of {display_time(track_duration)})"
                            if listened_percentage <= SKIPPED_SONG_THRESHOLD2:
                                if signal_previous_the_same:
                                    played_for += f" - CONT ({int(listened_percentage * 100)}%)"
                                    played_for_html += f" - <b>CONT</b> ({int(listened_percentage * 100)}%)"
                                    signal_previous_the_same = False
                                else:
                                    played_for += f" - SKIPPED ({int(listened_percentage * 100)}%)"
                                    played_for_html += f" - <b>SKIPPED</b> ({int(listened_percentage * 100)}%)"
                                    skipped_songs += 1
                            else:
                                played_for += f" ({int(listened_percentage * 100)}%)"
                                played_for_html += f" ({int(listened_percentage * 100)}%)"
                            played_for_display = True
                        else:
                            played_for = display_time(played_for_time)
                            played_for_html = played_for
                            if listened_percentage >= LONGER_SONG_THRESHOLD1 or (played_for_time - track_duration >= LONGER_SONG_THRESHOLD2):
                                played_for += f" - LONGER than track duration (+ {display_time(played_for_time - track_duration)}, {int(listened_percentage * 100)}%)"
                                played_for_html += f" - <b>LONGER</b> than track duration (+ {display_time(played_for_time - track_duration)}, {int(listened_percentage * 100)}%)"
                                played_for_display = True

                        if played_for_display:
                            played_for_m_body = f"\n\nUser played the previous track ({artist_old} - {track_old}) for: {played_for}"
                            played_for_m_body_html = f"<br><br>User played the previous track (<b>{escape(artist_old)} - {escape(track_old)}</b>) for: {played_for_html}"
                            if progress_indicator:
                                print("---------------------------------------------------------------------------------------------------------")
                            print(f"User played the previous track for: {played_for}")
                            if not progress_indicator:
                                print("---------------------------------------------------------------------------------------------------------")
                    # Handling how long user played the previous track, if skipped it etc. - in case track duration is NOT available
                    elif track_duration <= 0 and lf_track_ts_start_after_resume > 0 and lf_user_online:
                        played_for = display_time(lf_current_ts - lf_track_ts_start_after_resume)
                        played_for_html = f"<b>{display_time(lf_current_ts - lf_track_ts_start_after_resume)}</b>"
                        if ((lf_current_ts - lf_track_ts_start_after_resume) <= SKIPPED_SONG_THRESHOLD1):
                            if signal_previous_the_same:
                                played_for_m_body = f"\n\nUser CONT the previous track ({artist_old} - {track_old}) for: {played_for}"
                                played_for_m_body_html = f"<br><br>User <b>CONT</b> the previous track (<b>{escape(artist_old)} - {escape(track_old)}</b>) for: {played_for_html}"
                                played_for_str = f"User CONT the previous track for {played_for}"
                                signal_previous_the_same = False
                            else:
                                skipped_songs += 1
                                played_for_m_body = f"\n\nUser SKIPPED the previous track ({artist_old} - {track_old}) after: {played_for}"
                                played_for_m_body_html = f"<br><br>User <b>SKIPPED</b> the previous track (<b>{escape(artist_old)} - {escape(track_old)}</b>) after: {played_for_html}"
                                played_for_str = f"User SKIPPED the previous track after {played_for}"
                        else:
                            played_for_m_body = f"\n\nUser played the previous track ({artist_old} - {track_old}) for: {played_for}"
                            played_for_m_body_html = f"<br><br>User played the previous track (<b>{escape(artist_old)} - {escape(track_old)}</b>) for: {played_for_html}"
                            played_for_str = f"User played the previous track for: {played_for}"

                        if progress_indicator:
                            print("---------------------------------------------------------------------------------------------------------")
                        print(played_for_str)
                        if not progress_indicator:
                            print("---------------------------------------------------------------------------------------------------------")

                    if progress_indicator:
                        print("---------------------------------------------------------------------------------------------------------")

                    print(f"Last.fm user:\t\t\t{username}\n")

                    listened_songs += 1

                    # Clearing the flag used to indicate CONT songs (continued from previous playing session)
                    if listened_songs == 2:
                        signal_previous_the_same = False

                    if lf_track_ts_start > 0:
                        lf_track_ts_start_old = lf_track_ts_start
                    lf_track_ts_start = lf_current_ts
                    lf_track_ts_start_after_resume = lf_track_ts_start
                    last_track_start_ts_old = last_track_start_ts

                    print(f"Track:\t\t\t\t{artist} - {track}")
                    print(f"Album:\t\t\t\t{album}")

                    sp_track_uri_id = None
                    sp_track_duration = 0
                    duration_mark = ""

                    if (USE_TRACK_DURATION_FROM_SPOTIFY or track_songs) and SP_CLIENT_ID and SP_CLIENT_SECRET and SP_CLIENT_ID != "your_spotify_app_client_id" and SP_CLIENT_SECRET != "your_spotify_app_client_secret":
                        accessToken = spotify_get_access_token(SP_CLIENT_ID, SP_CLIENT_SECRET)
                        if accessToken:
                            sp_track_uri_id, sp_track_duration = spotify_search_song_trackid_duration(accessToken, artist, track, album)
                            if not USE_TRACK_DURATION_FROM_SPOTIFY:
                                sp_track_duration = 0

                    if sp_track_duration > 0:
                        track_duration = sp_track_duration
                        if not do_not_show_duration_marks:
                            duration_mark = " S*"
                    else:
                        try:
                            track_duration = pylast.Track(playing_track.artist, playing_track.title, network).get_duration()
                            if track_duration > 0:
                                if USE_TRACK_DURATION_FROM_SPOTIFY:
                                    if not do_not_show_duration_marks:
                                        duration_mark = " L*"
                                track_duration = int(str(track_duration)[0:-3])
                        except Exception as e:
                            track_duration = 0
                            pass

                    if track_duration > 0:
                        print(f"Duration:\t\t\t{display_time(track_duration)}{duration_mark}")

                    spotify_search_url, apple_search_url, genius_search_url, youtube_music_search_url = get_spotify_apple_genius_search_urls(str(artist), str(track))

                    print(f"\nSpotify search URL:\t\t{spotify_search_url}")
                    print(f"Apple search URL:\t\t{apple_search_url}")
                    print(f"YouTube Music search URL:\t{youtube_music_search_url}")
                    print(f"Genius lyrics URL:\t\t{genius_search_url}")

                    last_activity_to_save = []
                    last_activity_to_save.append(lf_track_ts_start)
                    last_activity_to_save.append(artist)
                    last_activity_to_save.append(track)
                    last_activity_to_save.append(album)
                    try:
                        with open(lastfm_last_activity_file, 'w', encoding="utf-8") as f:
                            json.dump(last_activity_to_save, f, indent=2)
                    except Exception as e:
                        print(f"* Cannot save last status to '{lastfm_last_activity_file}' file - {e}")

                    duration_m_body = ""
                    duration_m_body_html = ""
                    if track_duration > 0:
                        duration_m_body = f"\nDuration: {display_time(track_duration)}{duration_mark}"
                        duration_m_body_html = f"<br>Duration: {display_time(track_duration)}{duration_mark}"

                    # If tracking functionality is enabled then play the current song via Spotify client
                    if track_songs and sp_track_uri_id:
                        if platform.system() == 'Darwin':       # macOS
                            spotify_macos_play_song(sp_track_uri_id)
                        elif platform.system() == 'Windows':    # Windows
                            spotify_win_play_song(sp_track_uri_id)
                        else:                                   # Linux variants
                            spotify_linux_play_song(sp_track_uri_id)

                    # User was offline and got active
                    if (not lf_user_online and (lf_track_ts_start - lf_active_ts_last) > LASTFM_INACTIVITY_CHECK and lf_active_ts_last > 0) or (not lf_user_online and lf_active_ts_last > 0 and app_started_and_user_offline):
                        app_started_and_user_offline = False
                        last_track_start_changed = ""
                        last_track_start_changed_html = ""
                        lf_active_ts_last_old = lf_active_ts_last
                        if last_track_start_ts > (lf_active_ts_last + 60) and (int(time.time()) - last_track_start_ts > 240):
                            last_track_start_changed = f"\n(last track start changed from {get_short_date_from_ts(lf_active_ts_last)} to {get_short_date_from_ts(last_track_start_ts)} - offline mode ?)"
                            last_track_start_changed_html = f"<br>(last track start changed from <b>{get_short_date_from_ts(lf_active_ts_last)}</b> to <b>{get_short_date_from_ts(last_track_start_ts)}</b> - offline mode ?)"
                            lf_active_ts_last = last_track_start_ts

                        duplicate_entries = False
                        private_mode = ""
                        private_mode_html = ""
                        try:
                            p = 0
                            recent_tracks_while_offline = lastfm_get_recent_tracks(username, network, RECENT_TRACKS_NUMBER)
                            for previous, t, nxt in previous_and_next(reversed(recent_tracks_while_offline)):
                                if previous:
                                    if previous.timestamp == t.timestamp:
                                        p += 1
                                        duplicate_entries = True
                        except Exception as e:
                            print(f"* Error - {e}")
                        if duplicate_entries:
                            private_mode = f"\n\nDuplicate entries ({p}) found, possible private mode ({get_range_of_dates_from_tss(lf_active_ts_last_old, lf_track_ts_start, short=True)})"
                            private_mode_html = f"<br><br>Duplicate entries ({p}) found, possible <b>private mode</b> (<b>{get_range_of_dates_from_tss(lf_active_ts_last_old, lf_track_ts_start, short=True)}</b>)"
                            print(f"\n*** Duplicate entries ({p}) found, possible PRIVATE MODE ({get_range_of_dates_from_tss(lf_active_ts_last_old, lf_track_ts_start, short=True)})")

                        print(f"\n*** User got ACTIVE after being offline for {calculate_timespan(int(lf_track_ts_start), int(lf_active_ts_last))}{last_track_start_changed}")
                        print(f"*** Last activity:\t\t{get_date_from_ts(lf_active_ts_last)}")
                        # We signal that the currently played song is the same as previous one before user got inactive, so might be continuation of previous track
                        if artist_old == artist and track_old == track:
                            signal_previous_the_same = True
                        else:
                            signal_previous_the_same = False
                        paused_counter = 0
                        listened_songs = 1
                        skipped_songs = 0
                        looped_songs = 0
                        pauses_number = 0
                        lf_active_ts_start = lf_track_ts_start
                        playing_resumed_ts = lf_track_ts_start
                        m_subject = f"Last.fm user {username} is active: '{artist} - {track}' (after {calculate_timespan(int(lf_track_ts_start), int(lf_active_ts_last), show_seconds=False)} - {get_short_date_from_ts(lf_active_ts_last)})"
                        m_body = f"Track: {artist} - {track}{duration_m_body}\nAlbum: {album}\n\nSpotify search URL: {spotify_search_url}\nApple search URL: {apple_search_url}\nYouTube Music search URL:{youtube_music_search_url}\nGenius lyrics URL: {genius_search_url}{played_for_m_body}\n\nFriend got active after being offline for {calculate_timespan(int(lf_track_ts_start), int(lf_active_ts_last))}{last_track_start_changed}{private_mode}\n\nLast activity: {get_date_from_ts(lf_active_ts_last)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Track: <b><a href=\"{spotify_search_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}<br>Album: {escape(album)}<br><br>Apple search URL: <a href=\"{apple_search_url}\">{escape(artist)} - {escape(track)}</a><br>YouTube Music search URL: <a href=\"{youtube_music_search_url}\">{escape(artist)} - {escape(track)}</a><br>Genius lyrics URL: <a href=\"{genius_search_url}\">{escape(artist)} - {escape(track)}</a>{played_for_m_body_html}<br><br>Friend got active after being offline for <b>{calculate_timespan(int(lf_track_ts_start), int(lf_active_ts_last))}</b>{last_track_start_changed_html}{private_mode_html}<br><br>Last activity: <b>{get_date_from_ts(lf_active_ts_last)}</b>{get_cur_ts('<br>Timestamp: ')}</body></html>"

                        if active_notification:
                            print(f"Sending email notification to {RECEIVER_EMAIL}")
                            send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                            email_sent = True

                    if (track_notification or song_notification) and not email_sent:
                        m_subject = f"Last.fm user {username}: '{artist} - {track}'"
                        m_body = f"Track: {artist} - {track}{duration_m_body}\nAlbum: {album}\n\nSpotify search URL: {spotify_search_url}\nApple search URL: {apple_search_url}\nYouTube Music search URL:{youtube_music_search_url}\nGenius lyrics URL: {genius_search_url}{played_for_m_body}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Track: <b><a href=\"{spotify_search_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}<br>Album: {escape(album)}<br><br>Apple search URL: <a href=\"{apple_search_url}\">{escape(artist)} - {escape(track)}</a><br>YouTube Music search URL: <a href=\"{youtube_music_search_url}\">{escape(artist)} - {escape(track)}</a><br>Genius lyrics URL: <a href=\"{genius_search_url}\">{escape(artist)} - {escape(track)}</a>{played_for_m_body_html}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"

                    if track.upper() in map(str.upper, tracks) or album.upper() in map(str.upper, tracks):
                        print("\n*** Track/album matched with the list!")

                        if track_notification and not email_sent:
                            print(f"Sending email notification to {RECEIVER_EMAIL}")
                            send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                            email_sent = True

                    if song_notification and not email_sent:
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                        email_sent = True

                    if song_on_loop == SONG_ON_LOOP_VALUE:
                        print("---------------------------------------------------------------------------------------------------------")
                        print(f"User plays song on LOOP ({song_on_loop} times)")
                        print("---------------------------------------------------------------------------------------------------------")

                    if song_on_loop == SONG_ON_LOOP_VALUE and song_on_loop_notification:
                        m_subject = f"Last.fm user {username} plays song on loop: '{artist} - {track}'"
                        m_body = f"Track: {artist} - {track}{duration_m_body}\nAlbum: {album}\n\nSpotify search URL: {spotify_search_url}\nApple search URL: {apple_search_url}\nYouTube Music search URL:{youtube_music_search_url}\nGenius lyrics URL: {genius_search_url}{played_for_m_body}\n\nUser plays song on LOOP ({song_on_loop} times){get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Track: <b><a href=\"{spotify_search_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}<br>Album: {escape(album)}<br><br>Apple search URL: <a href=\"{apple_search_url}\">{escape(artist)} - {escape(track)}</a><br>YouTube Music search URL: <a href=\"{youtube_music_search_url}\">{escape(artist)} - {escape(track)}</a><br>Genius lyrics URL: <a href=\"{genius_search_url}\">{escape(artist)} - {escape(track)}</a>{played_for_m_body_html}<br><br>User plays song on LOOP (<b>{song_on_loop}</b> times){get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, m_body_html, SMTP_SSL)

                    lf_user_online = True
                    lf_active_ts_last = int(time.time())

                    artist_old = artist
                    track_old = track

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(lf_track_ts_start)), artist, track, album)
                    except Exception as e:
                        print(f"* Cannot write CSV entry - {e}")

                    print_cur_ts("\nTimestamp:\t\t\t")
                # Track has not changed, user is online and continues playing
                else:
                    lf_active_ts_last = int(time.time())
                    # We display progress indicator if flag is enabled
                    if lf_user_online and progress_indicator:
                        ts = datetime.fromtimestamp(lf_active_ts_last).strftime('%H:%M:%S')
                        delta_ts = lf_active_ts_last - lf_track_ts_start_after_resume
                        if delta_ts > 0:
                            delta_diff_str = "%02d:%02d:%02d" % (delta_ts // 3600, delta_ts // 60 % 60, delta_ts % 60)
                        else:
                            delta_diff_str = "00:00:00"
                        print(f"# {ts} +{delta_diff_str}")
            # User is offline (does not play music at the moment)
            else:

                alive_counter += 1

                # User paused playing the music
                if ((int(time.time()) - lf_active_ts_last) > (LASTFM_ACTIVE_CHECK_INTERVAL * LASTFM_BREAK_CHECK_MULTIPLIER)) and lf_user_online and lf_active_ts_last > 0 and lf_active_ts_start > 0 and (LASTFM_ACTIVE_CHECK_INTERVAL * LASTFM_BREAK_CHECK_MULTIPLIER) < LASTFM_INACTIVITY_CHECK and LASTFM_BREAK_CHECK_MULTIPLIER > 0 and playing_paused is False:
                    playing_paused = True
                    playing_paused_ts = lf_active_ts_last
                    pauses_number += 1
                    if progress_indicator:
                        print("---------------------------------------------------------------------------------------------------------")
                    print(f"User PAUSED playing after {calculate_timespan(int(playing_resumed_ts), int(playing_paused_ts))} (inactivity timer: {display_time(LASTFM_BREAK_CHECK_MULTIPLIER * LASTFM_ACTIVE_CHECK_INTERVAL)})")
                    print(f"Last activity:\t\t\t{get_date_from_ts(lf_active_ts_last)}")
                    print_cur_ts("\nTimestamp:\t\t\t")
                    # If tracking functionality is enabled then PAUSE the current song via Spotify client
                    if track_songs:
                        if platform.system() == 'Darwin':       # macOS
                            spotify_macos_play_pause("pause")
                        elif platform.system() == 'Windows':    # Windows
                            pass
                        else:                                   # Linux variants
                            spotify_linux_play_pause("pause")
                # User got inactive
                if ((int(time.time()) - lf_active_ts_last) > LASTFM_INACTIVITY_CHECK) and lf_user_online and lf_active_ts_last > 0 and lf_active_ts_start > 0:

                    lf_user_online = False

                    played_for_m_body = ""
                    played_for_m_body_html = ""

                    # Handling how long user played the last track - in case track duration is available
                    if track_duration > 0 and lf_track_ts_start_after_resume > 0:
                        played_for_time = lf_active_ts_last - lf_track_ts_start_after_resume
                        listened_percentage = (played_for_time) / (track_duration - 1)

                        if (played_for_time) < (track_duration - LASTFM_ACTIVE_CHECK_INTERVAL - 1):
                            played_for = f"{display_time(played_for_time)} (out of {display_time(track_duration)})"
                            played_for_html = f"<b>{display_time(played_for_time)}</b> (out of {display_time(track_duration)})"
                            played_for += f" ({int(listened_percentage * 100)}%)"
                            played_for_html += f" ({int(listened_percentage * 100)}%)"
                        else:
                            played_for = display_time(played_for_time)
                            played_for_html = f"<b>{display_time(played_for_time)}</b>"

                        played_for_m_body = f"\n\nUser played the last track for: {played_for}"
                        played_for_m_body_html = f"<br><br>User played the last track for: {played_for_html}"
                        print(f"User played the last track for: {played_for}")
                        if not progress_indicator:
                            print("---------------------------------------------------------------------------------------------------------")
                    # Handling how long user played the last track - in case track duration is NOT available
                    elif track_duration <= 0 and lf_track_ts_start_after_resume > 0:
                        played_for = display_time((lf_active_ts_last) - lf_track_ts_start_after_resume)

                        played_for_m_body = f"\n\nUser played the last track for: {played_for}"
                        played_for_m_body_html = f"<br><br>User played the last track for: <b>{played_for}</b>"
                        played_for_str = f"User played the last track for: {played_for}"

                        print(played_for_str)
                        if not progress_indicator:
                            print("---------------------------------------------------------------------------------------------------------")

                    if progress_indicator:
                        print("---------------------------------------------------------------------------------------------------------")

                    print(f"*** User got INACTIVE after listening to music for {calculate_timespan(int(lf_active_ts_last), int(lf_active_ts_start))}")
                    print(f"*** User played music from {get_range_of_dates_from_tss(lf_active_ts_start, lf_active_ts_last, short=True, between_sep=' to ')}")
                    playing_resumed_ts = int(time.time())
                    paused_mbody = ""
                    paused_mbody_html = ""
                    pauses_number -= 1
                    if paused_counter > 0:
                        paused_percentage = int((paused_counter / (int(lf_active_ts_last) - int(lf_active_ts_start))) * 100)
                        print(f"*** User paused music {pauses_number} times for {display_time(paused_counter)} ({paused_percentage}%)")
                        paused_mbody = f"\nUser paused music {pauses_number} times for {display_time(paused_counter)} ({paused_percentage}%)"
                        paused_mbody_html = f"<br>User paused music <b>{pauses_number}</b> times for <b>{display_time(paused_counter)} ({paused_percentage}%)</b>"
                    paused_counter = 0

                    listened_songs_text = f"*** User played {listened_songs} songs"
                    listened_songs_mbody = f"\n\nUser played {listened_songs} songs"
                    listened_songs_mbody_html = f"<br><br>User played <b>{listened_songs}</b> songs"

                    if skipped_songs > 0:
                        skipped_songs_text = f", skipped {skipped_songs} songs ({int((skipped_songs / listened_songs) * 100)}%)"
                        listened_songs_text += skipped_songs_text
                        listened_songs_mbody += skipped_songs_text
                        listened_songs_mbody_html += f", skipped <b>{skipped_songs}</b> songs (<b>{int((skipped_songs / listened_songs) * 100)}%</b>)"

                    if looped_songs > 0:
                        looped_songs_text = f"\n*** User played {looped_songs} songs on loop"
                        looped_songs_mbody = f"\nUser played {looped_songs} songs on loop"
                        looped_songs_mbody_html = f"<br>User played <b>{looped_songs}</b> songs on loop"
                        listened_songs_text += looped_songs_text
                        listened_songs_mbody += looped_songs_mbody
                        listened_songs_mbody_html += looped_songs_mbody_html

                    print(f"{listened_songs_text}\n")

                    print(f"*** Last activity:\t\t{get_date_from_ts(lf_active_ts_last)} (inactive timer: {display_time(LASTFM_INACTIVITY_CHECK)})")
                    # If tracking functionality is enabled then either pause the current song via Spotify client or play the indicated SP_USER_GOT_OFFLINE_TRACK_ID "finishing" song
                    if track_songs:
                        if SP_USER_GOT_OFFLINE_TRACK_ID:
                            if platform.system() == 'Darwin':       # macOS
                                spotify_macos_play_song(SP_USER_GOT_OFFLINE_TRACK_ID)
                                if SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE > 0:
                                    time.sleep(SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE)
                                    spotify_macos_play_pause("pause")
                            elif platform.system() == 'Windows':    # Windows
                                pass
                            else:                                   # Linux variants
                                spotify_linux_play_song(SP_USER_GOT_OFFLINE_TRACK_ID)
                                if SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE > 0:
                                    time.sleep(SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE)
                                    spotify_linux_play_pause("pause")
                        else:
                            if platform.system() == 'Darwin':       # macOS
                                spotify_macos_play_pause("pause")
                            elif platform.system() == 'Windows':    # Windows
                                pass
                            else:                                   # Linux variants
                                spotify_linux_play_pause("pause")
                    last_activity_to_save = []
                    last_activity_to_save.append(lf_active_ts_last)
                    last_activity_to_save.append(artist)
                    last_activity_to_save.append(track)
                    last_activity_to_save.append(album)
                    try:
                        with open(lastfm_last_activity_file, 'w', encoding="utf-8") as f:
                            json.dump(last_activity_to_save, f, indent=2)
                    except Exception as e:
                        print(f"* Cannot save last status to '{lastfm_last_activity_file}' file - {e}")
                    if inactive_notification:
                        m_subject = f"Last.fm user {username} is inactive: '{artist} - {track}' (after {calculate_timespan(int(lf_active_ts_last), int(lf_active_ts_start), show_seconds=False)}: {get_range_of_dates_from_tss(lf_active_ts_start, lf_active_ts_last, short=True)})"
                        m_body = f"Last played: {artist} - {track}{duration_m_body}\nAlbum: {album}\n\nSpotify search URL: {spotify_search_url}\nApple search URL: {apple_search_url}\nYouTube Music search URL:{youtube_music_search_url}\nGenius lyrics URL: {genius_search_url}\n\nUser got inactive after listening to music for {calculate_timespan(int(lf_active_ts_last), int(lf_active_ts_start))}\nUser played music from {get_range_of_dates_from_tss(lf_active_ts_start, lf_active_ts_last, short=True, between_sep=' to ')}{paused_mbody}{listened_songs_mbody}{played_for_m_body}\n\nLast activity: {get_date_from_ts(lf_active_ts_last)}\nInactivity timer: {display_time(LASTFM_INACTIVITY_CHECK)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{spotify_search_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}<br>Album: {escape(album)}<br><br>Apple search URL: <a href=\"{apple_search_url}\">{escape(artist)} - {escape(track)}</a><br>YouTube Music search URL: <a href=\"{youtube_music_search_url}\">{escape(artist)} - {escape(track)}</a><br>Genius lyrics URL: <a href=\"{genius_search_url}\">{escape(artist)} - {escape(track)}</a><br><br>User got inactive after listening to music for <b>{calculate_timespan(int(lf_active_ts_last), int(lf_active_ts_start))}</b><br>User played music from <b>{get_range_of_dates_from_tss(lf_active_ts_start, lf_active_ts_last, short=True, between_sep='</b> to <b>')}</b>{paused_mbody_html}{listened_songs_mbody_html}{played_for_m_body_html}<br><br>Last activity: <b>{get_date_from_ts(lf_active_ts_last)}</b><br>Inactivity timer: {display_time(LASTFM_INACTIVITY_CHECK)}{get_cur_ts('<br>Timestamp: ')}</body></html>"

                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                        email_sent = True
                    lf_active_ts_start = 0
                    playing_track = None
                    last_track_start_ts = 0
                    listened_songs = 0
                    looped_songs = 0
                    skipped_songs = 0
                    pauses_number = 0
                    print_cur_ts("\nTimestamp:\t\t\t")

                if alive_counter >= TOOL_ALIVE_COUNTER:
                    print_cur_ts("Alive check, timestamp: ")
                    alive_counter = 0

            # Stuff to do regardless if the user is online or offline
            if last_track_start_ts > 0:
                last_track_start_ts_old2 = last_track_start_ts

            ERROR_500_ZERO_TIME_LIMIT = ERROR_500_TIME_LIMIT + LASTFM_CHECK_INTERVAL
            if LASTFM_CHECK_INTERVAL * ERROR_500_NUMBER_LIMIT > ERROR_500_ZERO_TIME_LIMIT:
                ERROR_500_ZERO_TIME_LIMIT = LASTFM_CHECK_INTERVAL * (ERROR_500_NUMBER_LIMIT + 1)

            if error_500_start_ts and ((int(time.time()) - error_500_start_ts) >= ERROR_500_ZERO_TIME_LIMIT):
                error_500_start_ts = 0
                error_500_counter = 0

            ERROR_NETWORK_ZERO_TIME_LIMIT = ERROR_NETWORK_ISSUES_TIME_LIMIT + LASTFM_CHECK_INTERVAL
            if LASTFM_CHECK_INTERVAL * ERROR_NETWORK_ISSUES_NUMBER_LIMIT > ERROR_NETWORK_ZERO_TIME_LIMIT:
                ERROR_NETWORK_ZERO_TIME_LIMIT = LASTFM_CHECK_INTERVAL * (ERROR_NETWORK_ISSUES_NUMBER_LIMIT + 1)

            if error_network_issue_start_ts and ((int(time.time()) - error_network_issue_start_ts) >= ERROR_NETWORK_ZERO_TIME_LIMIT):
                error_network_issue_start_ts = 0
                error_network_issue_counter = 0

        except Exception as e:

            str_matches = ["http code 500", "http code 504", "http code 503", "http code 502"]
            if any(x in str(e).lower() for x in str_matches):
                if not error_500_start_ts:
                    error_500_start_ts = int(time.time())
                    error_500_counter = 1
                else:
                    error_500_counter += 1

            str_matches = ["timed out", "timeout", "name resolution", "failed to resolve", "family not supported", "429 client", "aborted"]
            if any(x in str(e).lower() for x in str_matches) or str(e) == '':
                if not error_network_issue_start_ts:
                    error_network_issue_start_ts = int(time.time())
                    error_network_issue_counter = 1
                else:
                    error_network_issue_counter += 1

            if error_500_start_ts and (error_500_counter >= ERROR_500_NUMBER_LIMIT and (int(time.time()) - error_500_start_ts) >= ERROR_500_TIME_LIMIT):
                print(f"Error 50x ({error_500_counter}x times in the last {display_time((int(time.time()) - error_500_start_ts))}) - '{e}'")
                print_cur_ts("Timestamp:\t\t\t")
                error_500_start_ts = 0
                error_500_counter = 0

            elif error_network_issue_start_ts and (error_network_issue_counter >= ERROR_NETWORK_ISSUES_NUMBER_LIMIT and (int(time.time()) - error_network_issue_start_ts) >= ERROR_NETWORK_ISSUES_TIME_LIMIT):
                print(f"Error with network ({error_network_issue_counter}x times in the last {display_time((int(time.time()) - error_network_issue_start_ts))}) - '{e}'")
                print_cur_ts("Timestamp:\t\t\t")
                error_network_issue_start_ts = 0
                error_network_issue_counter = 0

            elif not error_500_start_ts and not error_network_issue_start_ts:
                print(f"Error - '{e}'")

                if 'Invalid API key' in str(e) or 'API Key Suspended' in str(e):
                    print("* API key might not be valid anymore!")
                    if error_notification and not email_sent:
                        m_subject = f"lastfm_monitor: API key error! (user: {username})"
                        m_body = f"API key might not be valid anymore: {e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>API key might not be valid anymore: {escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                        email_sent = True
                print_cur_ts("Timestamp:\t\t\t")

        if lf_user_online:
            time.sleep(LASTFM_ACTIVE_CHECK_INTERVAL)
        else:
            time.sleep(LASTFM_CHECK_INTERVAL)

        new_track = None


if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        print("* Cannot clear the screen contents")

    print(f"Last.fm Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser("lastfm_monitor")
    parser.add_argument("LASTFM_USERNAME", nargs="?", help="Last.fm username", type=str)
    parser.add_argument("-u", "--lastfm_api_key", help="Last.fm API key to override the value defined within the script (LASTFM_API_KEY)", type=str)
    parser.add_argument("-w", "--lastfm_shared_secret", help="Last.fm shared secret to override the value defined within the script (LASTFM_API_SECRET)", type=str)
    parser.add_argument("-z", "--spotify_client_id_and_secret", help="Spotify client id and secret to override the value defined within the script (SP_CLIENT_ID and SP_CLIENT_SECRET); specify it in the following format: SP_CLIENT_ID:SP_CLIENT_SECRET (both values separated by colon)", type=str)
    parser.add_argument("-a", "--active_notification", help="Send email notification once user gets active", action='store_true')
    parser.add_argument("-i", "--inactive_notification", help="Send email notification once user gets inactive", action='store_true')
    parser.add_argument("-t", "--track_notification", help="Send email notification once monitored track/album is found", action='store_true')
    parser.add_argument("-j", "--song_notification", help="Send email notification for every changed song", action='store_true')
    parser.add_argument("-f", "--offline_entries_notification", help="Send email notification in case new entries are detected while user is offline", action='store_true')
    parser.add_argument("-x", "--song_on_loop_notification", help="Send email notification if user plays a song on loop (>= SONG_ON_LOOP_VALUE times)", action='store_true')
    parser.add_argument("-e", "--error_notification", help="Disable sending email notifications in case of errors like invalid API key", action='store_false')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks if user is offline, in seconds", type=int)
    parser.add_argument("-k", "--active_check_interval", help="Time between monitoring checks if user is active, in seconds", type=int)
    parser.add_argument("-o", "--offline_timer", help="Time required to mark inactive user as offline, in seconds", type=int)
    parser.add_argument("-p", "--progress_indicator", help="Show progress indicator while user is listening", action='store_true')
    parser.add_argument("-g", "--track_songs", help="Automatically track listened songs by playing it in Spotify client", action='store_true')
    parser.add_argument("-m", "--play_break_multiplier", help="If more than 0 it will show when user stops playing/resumes (while active), play break is assumed to be play_break_multiplier*active_check_interval", type=int)
    parser.add_argument("-r", "--fetch_duration_from_spotify", help="Try to get the track duration from Spotify if SP_CLIENT_ID & SP_CLIENT_SECRET (-z) values are properly defined", action='store_true')
    parser.add_argument("-q", "--do_not_show_duration_marks", help="Do not display L* or S* marks indicating from where the track duration has been fetched (Last.fm or Spotify); it is showed only if fetching duration from Spotify (-r) is enabled", action='store_true')
    parser.add_argument("-b", "--csv_file", help="Write every listened track to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-s", "--lastfm_tracks", help="Filename with Last.fm tracks/albums to monitor", type=str, metavar="TRACKS_FILENAME")
    parser.add_argument("-l", "--list_recent_tracks", help="List recently played tracks for the user", action='store_true')
    parser.add_argument("-n", "--number_of_recent_tracks", help="Number of tracks to display if used with -l", type=int)
    parser.add_argument("-d", "--disable_logging", help="Disable output logging to file 'lastfm_monitor_user.log' file", action='store_true')
    parser.add_argument("-y", "--send_test_email_notification", help="Send test email notification to verify SMTP settings defined in the script", action='store_true')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.send_test_email_notification:
        print("* Sending test email notification ...\n")
        if send_email("lastfm_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if not args.LASTFM_USERNAME:
        print("* Error: LASTFM_USERNAME argument is required !")
        sys.exit(1)

    if args.lastfm_api_key:
        LASTFM_API_KEY = args.lastfm_api_key

    if args.lastfm_shared_secret:
        LASTFM_API_SECRET = args.lastfm_shared_secret

    if not LASTFM_API_KEY or LASTFM_API_KEY == "your_lastfm_api_key":
        print("* Error: LASTFM_API_KEY (-u / --lastfm_api_key) value is empty or incorrect")
        sys.exit(1)

    if not LASTFM_API_SECRET or LASTFM_API_SECRET == "your_lastfm_api_secret":
        print("* Error: LASTFM_API_SECRET (-w / --lastfm_shared_secret) value is empty or incorrect")
        sys.exit(1)

    if args.spotify_client_id_and_secret:
        try:
            SP_CLIENT_ID, SP_CLIENT_SECRET = args.spotify_client_id_and_secret.split(":")
        except ValueError:
            print("* Error: SPOTIFY_CLIENT_ID_AND_SECRET (-z / --spotify_client_id_and_secret) has invalid format - use SP_CLIENT_ID:SP_CLIENT_SECRET")
            sys.exit(1)

    if args.fetch_duration_from_spotify:
        USE_TRACK_DURATION_FROM_SPOTIFY = args.fetch_duration_from_spotify

    if args.check_interval:
        LASTFM_CHECK_INTERVAL = args.check_interval
        TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / LASTFM_CHECK_INTERVAL

    if args.active_check_interval:
        LASTFM_ACTIVE_CHECK_INTERVAL = args.active_check_interval

    if args.offline_timer:
        LASTFM_INACTIVITY_CHECK = args.offline_timer

    if args.play_break_multiplier:
        LASTFM_BREAK_CHECK_MULTIPLIER = args.play_break_multiplier

    network = pylast.LastFMNetwork(LASTFM_API_KEY, LASTFM_API_SECRET)
    user = network.get_user(args.LASTFM_USERNAME)

    if args.list_recent_tracks:
        if args.number_of_recent_tracks and args.number_of_recent_tracks > 0:
            tracks_n = args.number_of_recent_tracks
        else:
            tracks_n = 30
        print(f"* Listing {tracks_n} tracks recently listened by {args.LASTFM_USERNAME}:\n")
        lastfm_list_tracks(args.LASTFM_USERNAME, user, network, tracks_n)
        sys.exit(0)

    if args.lastfm_tracks:
        try:
            with open(args.lastfm_tracks, encoding="utf-8") as file:
                lf_tracks = file.read().splitlines()
            file.close()
        except Exception as e:
            print(f"* Error: file with Last.fm tracks cannot be opened - {e}")
            sys.exit(1)
    else:
        lf_tracks = []

    if args.csv_file:
        csv_enabled = True
        csv_exists = os.path.isfile(args.csv_file)
        try:
            csv_file = open(args.csv_file, 'a', newline='', buffering=1, encoding="utf-8")
        except Exception as e:
            print(f"* Error: CSV file cannot be opened for writing - {e}")
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled = False
        csv_file = None
        csv_exists = False

    if not args.disable_logging:
        LF_LOGFILE = f"{LF_LOGFILE}_{args.LASTFM_USERNAME}.log"
        sys.stdout = Logger(LF_LOGFILE)

    active_notification = args.active_notification
    inactive_notification = args.inactive_notification
    song_notification = args.song_notification
    track_notification = args.track_notification
    offline_entries_notification = args.offline_entries_notification
    song_on_loop_notification = args.song_on_loop_notification
    progress_indicator = args.progress_indicator
    track_songs = args.track_songs
    do_not_show_duration_marks = args.do_not_show_duration_marks
    error_notification = args.error_notification

    if not USE_TRACK_DURATION_FROM_SPOTIFY:
        do_not_show_duration_marks = True

    if SMTP_HOST == "your_smtp_server_ssl" or SMTP_HOST == "your_smtp_server_plaintext":
        active_notification = False
        inactive_notification = False
        song_notification = False
        track_notification = False
        offline_entries_notification = False
        song_on_loop_notification = False
        error_notification = False

    print(f"* Last.fm timers:\t\t\t[check interval: {display_time(LASTFM_CHECK_INTERVAL)}] [active check interval: {display_time(LASTFM_ACTIVE_CHECK_INTERVAL)}]\n*\t\t\t\t\t[inactivity: {display_time(LASTFM_INACTIVITY_CHECK)}]")
    print(f"* Email notifications:\t\t\t[active = {active_notification}] [inactive = {inactive_notification}] [tracked = {track_notification}] [every song = {song_notification}]\n*\t\t\t\t\t[songs on loop = {song_on_loop_notification}] [offline entries = {offline_entries_notification}] [errors = {error_notification}]")
    print(f"* Progress indicator enabled:\t\t{progress_indicator}")
    print(f"* Track listened songs:\t\t\t{track_songs}")
    print(f"* Get track duration from Spotify:\t{USE_TRACK_DURATION_FROM_SPOTIFY}")
    print(f"* Do not show duration marks (L*, S*):\t{do_not_show_duration_marks}")
    print(f"* Play break multiplier:\t\t{LASTFM_BREAK_CHECK_MULTIPLIER} ({display_time(LASTFM_BREAK_CHECK_MULTIPLIER * LASTFM_ACTIVE_CHECK_INTERVAL)})")
    if not args.disable_logging:
        print(f"* Output logging enabled:\t\t{not args.disable_logging} ({LF_LOGFILE})")
    else:
        print(f"* Output logging enabled:\t\t{not args.disable_logging}")
    if csv_enabled:
        print(f"* CSV logging enabled:\t\t\t{csv_enabled} ({args.csv_file})\n")
    else:
        print(f"* CSV logging enabled:\t\t\t{csv_enabled}\n")

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_song_notifications_signal_handler)
        signal.signal(signal.SIGHUP, toggle_progress_indicator_signal_handler)
        signal.signal(signal.SIGCONT, toggle_track_notifications_signal_handler)
        signal.signal(signal.SIGPIPE, toggle_songs_on_loop_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_inactivity_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_inactivity_check_signal_handler)

    out = f"Monitoring user {args.LASTFM_USERNAME}"
    print(out)
    print("-" * len(out))

    lastfm_monitor_user(user, network, args.LASTFM_USERNAME, lf_tracks, error_notification, args.csv_file, csv_exists)

    sys.stdout = stdout_bck
    sys.exit(0)
