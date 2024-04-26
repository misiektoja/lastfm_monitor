#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.1

Script implementing real-time monitoring of Last.fm users music activity:
https://github.com/misiektoja/lastfm_monitor/

Python pip3 requirements:

pylast
python-dateutil
requests
urllib3
"""

VERSION=1.1

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Create your Last.fm 'API key' and 'Shared secret' by going to: https://www.last.fm/api/account/create
# Or get your existing one from: https://www.last.fm/api/accounts
# Put the respective values below
LASTFM_API_KEY = "your_API_key" # Last.fm 'API key'
LASTFM_API_SECRET = "your_API_secret" # Last.fm 'Shared secret'

# Log in to Spotify web client (https://open.spotify.com/) and put the value of sp_dc cookie below
# Newly generated Spotify's sp_dc cookie should be valid for 1 year
# You can use Cookie-Editor by cgagnier to get it easily (available for all major web browsers): https://cookie-editor.com/
# It is needed only for track_songs functionality, so we can find track ID and trigger Spotify client to play it
SP_DC_COOKIE = "your_sp_dc_cookie_value"

# Type Spotify ID of the "finishing" track to play when user gets offline, only needed for track_songs functionality; 
# leave empty to simply pause
#SP_USER_GOT_OFFLINE_TRACK_ID="5wCjNjnugSUqGDBrmQhn0e"
SP_USER_GOT_OFFLINE_TRACK_ID=""

# Delay after which the above track gets paused, type 0 to play infinitely until user pauses manually; in seconds
SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE=5 # 5 seconds

# How often do we perform checks for user activity when considered offline (not playing music right now); in seconds
LASTFM_CHECK_INTERVAL=15 # 15 seconds

# How often do we perform checks for user activity when online (playing music right now); in seconds
LASTFM_ACTIVE_CHECK_INTERVAL=5 # 5 seconds

# After which time do we consider user as inactive (after last activity); in seconds
LASTFM_INACTIVITY_CHECK=180 # 3 mins

# If the value is more than 0 it will show when user stops playing/resumes (while active), play break is assumed to be LASTFM_BREAK_CHECK_MULTIPLIER*LASTFM_ACTIVE_CHECK_INTERVAL;
# So if LASTFM_BREAK_CHECK_MULTIPLIER=4 and LASTFM_ACTIVE_CHECK_INTERVAL=5, then music pause will be reported after 4*5=20 seconds of inactivity
LASTFM_BREAK_CHECK_MULTIPLIER=4

# When do we consider the song as being skipped; this parameter is used if track duration is NOT available from Last.fm; in seconds
SKIPPED_SONG_THRESHOLD1=50 # song is treated as skipped if played for <=50 seconds

# When do we consider the song as being skipped; this parameter is used if track duration is available from Last.fm; fraction 
SKIPPED_SONG_THRESHOLD2=0.6 # song is treated as skipped if played for <=60% of track duration

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL=21600 # 6 hours

# Default value for network-related timeouts in functions; in seconds
FUNCTION_TIMEOUT=15 # 15 seconds

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL='http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT=5

# SMTP settings for sending email notifications
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
#SMTP_HOST = "your_smtp_server_plaintext"
#SMTP_PORT = 25
#SMTP_USER = "your_smtp_user"
#SMTP_PASSWORD = "your_smtp_password"
#SMTP_SSL = False
#SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# Strings removed from track names for generating proper Genius search URLs
re_search_str=r'remaster|extended|original mix|remix|original soundtrack|radio( |-)edit|\(feat\.|( \(.*version\))|( - .*version)'
re_replace_str=r'( - (\d*)( )*remaster$)|( - (\d*)( )*remastered( version)*( \d*)*.*$)|( \((\d*)( )*remaster\)$)|( - (\d+) - remaster$)|( - extended$)|( - extended mix$)|( - (.*); extended mix$)|( - extended version$)|( - (.*) remix$)|( - remix$)|( - remixed by .*$)|( - original mix$)|( - .*original soundtrack$)|( - .*radio( |-)edit$)|( \(feat\. .*\)$)|( \(\d+.*Remaster.*\)$)|( \(.*Version\))|( - .*version)'

# The name of the .log file; the tool by default will output its messages to lastfm_monitor_username.log file
lf_logfile="lastfm_monitor"

# Value used by signal handlers increasing/decreasing the inactivity check (LASTFM_INACTIVITY_CHECK); in seconds
LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE=30 # 30 seconds

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

TOOL_ALIVE_COUNTER=TOOL_ALIVE_INTERVAL/LASTFM_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Artist', 'Track', 'Album']

active_notification=False
inactive_notification=False
song_notification=False
track_notification=False
offline_entries_notification=False
progress_indicator=False
track_songs=False

import sys
import time
import string
import json
import os
from datetime import datetime
from dateutil import relativedelta
import calendar
import requests as req
import signal
import smtplib, ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import csv
import pylast
import urllib
import subprocess
import platform
import re
from itertools import tee, islice, chain

# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1)

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
    url=CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT)
        print("OK")
        return True
    except Exception as e:
        print("No connectivity, please check your network -", e)
        sys.exit(1)
    return False

# Function to convert absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952), # approximation
        ('months', 2629746), # approximation
        ('weeks', 604800),  # 60 * 60 * 24 * 7
        ('days', 86400),    # 60 * 60 * 24
        ('hours', 3600),    # 60 * 60
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
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'

# Function to calculate time span between two timestamps in seconds
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals=['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1=timestamp1
    ts2=timestamp2

    if type(timestamp1) is int:
        dt1=datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is datetime:
        dt1=timestamp1
        ts1=int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2=datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is datetime:
        dt2=timestamp2
        ts2=int(round(dt2.timestamp()))
    else:
        return ""

    if ts1>=ts2:
        ts_diff=ts1-ts2
    else:
        ts_diff=ts2-ts1
        dt1, dt2 = dt2, dt1

    if ts_diff>0:
        date_diff=relativedelta.relativedelta(dt1, dt2)
        years=date_diff.years
        months=date_diff.months
        weeks=date_diff.weeks
        if not show_weeks:
            weeks=0
        days=date_diff.days
        if weeks > 0:
            days=days-(weeks*7)
        hours=date_diff.hours
        if (not show_hours and ts_diff>86400):
            hours=0
        minutes=date_diff.minutes
        if (not show_minutes and ts_diff>3600):
            minutes=0
        seconds=date_diff.seconds
        if (not show_seconds and ts_diff>60):
            seconds=0
        date_list=[years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval>0:
                name=intervals[index]
                if interval==1:
                    name = name.rstrip('s')
                result.append("{} {}".format(interval, name))
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'

# Function to send email notification
def send_email(subject,body,body_html,use_ssl):

    try:     
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
        smtpObj.login(SMTP_USER,SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] =  Header(subject, 'utf-8')

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
        print("Error sending email -", e)
        return 1
    return 0

# Function to write CSV entry
def write_csv_entry(csv_file_name, timestamp, artist, track, album):
    try:
        csv_file=open(csv_file_name, 'a', newline='', buffering=1)
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Date': timestamp, 'Artist': artist, 'Track': track, 'Album': album})
        csv_file.close()
    except Exception as e:
        raise 

# Function to return the timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (str(ts_str) + str(calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]) + ", " + str(datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")))

# Function to print the current timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("---------------------------------------------------------------------------------------------------------")

# Function to return the timestamp in human readable format (long version); eg. Sun, 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    return (str(calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]) + " " + str(datetime.fromtimestamp(ts).strftime("%d %b %Y, %H:%M:%S")))

# Function to return the timestamp in human readable format (short version); eg. Sun 21 Apr 15:08
def get_short_date_from_ts(ts):
    return (str(calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]) + " " + str(datetime.fromtimestamp(ts).strftime("%d %b %H:%M")))

# Function to return the timestamp in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts,show_seconds=False):
    if show_seconds:
        out_strf="%H:%M:%S"
    else:
        out_strf="%H:%M"
    return (str(datetime.fromtimestamp(ts).strftime(out_strf)))

# Function to return the range between two timestamps; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1,ts2,between_sep=" - ", short=False):
    ts1_strf=datetime.fromtimestamp(ts1).strftime("%Y%m%d")
    ts2_strf=datetime.fromtimestamp(ts2).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str=get_short_date_from_ts(ts1) + between_sep + get_hour_min_from_ts(ts2)
        else:
            out_str=get_date_from_ts(ts1) + between_sep + get_hour_min_from_ts(ts2,show_seconds=True)
    else:
        if short:
            out_str=get_short_date_from_ts(ts1) + between_sep + get_short_date_from_ts(ts2)
        else:
            out_str=get_date_from_ts(ts1) + between_sep + get_date_from_ts(ts2)       
    return (str(out_str))

# Signal handler for SIGUSR1 allowing to switch active/inactive email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global active_notification
    global inactive_notification
    active_notification=not active_notification
    inactive_notification=not inactive_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active = {active_notification}] [inactive = {inactive_notification}]")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGUSR2 allowing to switch every song email notifications
def toggle_song_notifications_signal_handler(sig, frame):
    global song_notification
    song_notification=not song_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [every song = {song_notification}]")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGHUP allowing to switch progress indicator in the output
def toggle_progress_indicator_signal_handler(sig, frame):
    global progress_indicator
    progress_indicator=not progress_indicator
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Progress indicator enabled: {progress_indicator}")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGCONT allowing to switch tracked songs email notifications
def toggle_track_notifications_signal_handler(sig, frame):
    global track_notification
    track_notification=not track_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [tracked = " + str(track_notification) + "]")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGTRAP allowing to increase inactivity check interval by LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE seconds
def increase_inactivity_check_signal_handler(sig, frame):
    global LASTFM_INACTIVITY_CHECK
    LASTFM_INACTIVITY_CHECK=LASTFM_INACTIVITY_CHECK+LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print("* Last.fm timers: [inactivity: " + display_time(LASTFM_INACTIVITY_CHECK) + "]")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGABRT allowing to decrease inactivity check interval by LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE seconds
def decrease_inactivity_check_signal_handler(sig, frame):
    global LASTFM_INACTIVITY_CHECK
    if LASTFM_INACTIVITY_CHECK-LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE>0:
        LASTFM_INACTIVITY_CHECK=LASTFM_INACTIVITY_CHECK-LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print("* Last.fm timers: [inactivity: " + display_time(LASTFM_INACTIVITY_CHECK) + "]")
    print_cur_ts("Timestamp:\t\t")

# Function to access the previous and next elements of the list
def previous_and_next(some_iterable):
    prevs, items, nexts = tee(some_iterable, 3)
    prevs = chain([None], prevs)
    nexts = chain(islice(nexts, 1, None), [None])
    return zip(prevs, items, nexts)

# Function preparing Spotify, Apple & Genius search URLs for specified track
def get_spotify_apple_genius_search_urls(artist,track):
    spotify_search_string=urllib.parse.quote_plus(str(artist) + " " + str(track))
    genius_search_string=str(artist) + " " + str(track)
    if re.search(re_search_str, genius_search_string, re.IGNORECASE):
        genius_search_string=re.sub(re_replace_str, '', genius_search_string, flags=re.IGNORECASE)        
    apple_search_string=urllib.parse.quote(str(artist) + " " + str(track))
    spotify_search_url="https://open.spotify.com/search/" + spotify_search_string + "?si=1"
    apple_search_url="https://music.apple.com/pl/search?term=" + apple_search_string
    genius_search_url="https://genius.com/search?q=" + urllib.parse.quote_plus(genius_search_string)
    return spotify_search_url,apple_search_url,genius_search_url

# Function returning the list of recently played Last.fm tracks
def lastfm_get_recent_tracks(username,network,number):
    try:
        recent_tracks = network.get_user(username).get_recent_tracks(limit=number)
    except Exception as e:
        print("* Error -", e)
        raise
    return recent_tracks

# Function displaying the list of recently played Last.fm tracks
def lastfm_list_tracks(username,user,network,number):
    try:
        recent_tracks=lastfm_get_recent_tracks(username,network,number)
        new_track=user.get_now_playing()
    except Exception as e:
        print("* Error -", e)
        raise
    last_played=0

    i = 0
    duplicate_entries=False
    for previous, t, nxt in previous_and_next(reversed(recent_tracks)):
        i+=1
        if i==len(recent_tracks):
            last_played=int(t.timestamp)
        print(str(i), "\t", datetime.fromtimestamp(int(t.timestamp)).strftime("%d %b %Y, %H:%M:%S"), "\t", str(calendar.day_abbr[(datetime.fromtimestamp(int(t.timestamp))).weekday()]), "\t", str(t.track))
        if previous:
            if previous.timestamp==t.timestamp:
                duplicate_entries=True
                print("DUPLICATE ENTRY")
    print("---------------------------------------------------------------------------------------------------------")
    if last_played>0 and not new_track:
        print("*** User played last time " + calculate_timespan(int(time.time()),last_played,show_seconds=True) + " ago! (" + get_date_from_ts(last_played) + ")")

    if duplicate_entries:
        print("*** Duplicate entries found, possible PRIVATE MODE")

    if new_track:
        artist=str(new_track.artist)
        track=str(new_track.title)
        album=str(new_track.info['album'])
        print("*** User is currently ACTIVE !") 
        print("\nTrack:\t" + artist + " - " + track)
        print("Album:\t" + album)

# Function getting Spotify access token based on provided sp_dc cookie value
def spotify_get_access_token(sp_dc):
    url = "https://open.spotify.com/get_access_token?reason=transport&productType=web_player"
    cookies = {"sp_dc": sp_dc}
    try:
        response = req.get(url, cookies=cookies, timeout=FUNCTION_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        print("spotify_get_access_token error -", e)
        if hasattr(e, 'response'):
            if hasattr(e.response, 'text'):
                print (e.response.text)
        raise
    return response.json()["accessToken"]

# Function converting Spotify URI (e.g. spotify:user:username) to URL (e.g. https://open.spotify.com/user/username)
def spotify_convert_uri_to_url(uri):
    # add si parameter so link opens in native Spotify app after clicking
    si="?si=1"
#    si=""

    url=""
    if "spotify:user:" in uri:
        s_id=uri.split(':', 2)[2]
        url="https://open.spotify.com/user/" + s_id + si
    elif "spotify:artist:" in uri:
        s_id=uri.split(':', 2)[2]
        url="https://open.spotify.com/artist/" + s_id + si
    elif "spotify:track:" in uri:
        s_id=uri.split(':', 2)[2]
        url="https://open.spotify.com/track/" + s_id + si
    elif "spotify:album:" in uri:
        s_id=uri.split(':', 2)[2]
        url="https://open.spotify.com/album/" + s_id + si           
    elif "spotify:playlist:" in uri:
        s_id=uri.split(':', 2)[2]
        url="https://open.spotify.com/playlist/" + s_id + si

    return url

# Function returning Spotify track ID for specific artist, track and optionally album
def spotify_search_song_trackid(access_token,artist,track,album=""):
    url = "https://api.spotify.com/v1/search?q=" + urllib.parse.quote_plus(str(artist) + " " + str(track)) + "&type=track&limit=1"
    headers = {"Authorization": "Bearer " + access_token}
    try:
        response = req.get(url, headers=headers, timeout=FUNCTION_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        print("spotify_search_song_trackid error -", e)
        if hasattr(e, 'response'):
            if hasattr(e.response, 'text'):
                print (e.response.text)
        raise
    json_response = response.json()
    if json_response["tracks"].get("total") > 0:
        sp_track_uri=json_response["tracks"]["items"][0].get("id")
    else:
        sp_track_uri=None
    return sp_track_uri
#    return json.dumps(response.json())

# Main function monitoring activity of the specified Last.fm user
def lastfm_monitor_user(user,network,username,tracks,error_notification,csv_file_name,csv_exists):

    lf_active_ts_start=0
    lf_active_ts_last=0
    lf_track_ts_start=0
    lf_track_ts_start_old=0    
    lf_track_ts_start_after_resume=0
    lf_user_online=False
    alive_counter = 0
    track_duration = 0
    playing_paused=False
    playing_paused_ts=0
    playing_resumed_ts=0
    paused_counter=0
    playing_track=None
    new_track=None
    listened_songs=0
    skipped_songs=0
    signal_previous_the_same=False
    artist=""
    track=""
    artist_old=""
    track_old=""

    try:
        if csv_file_name:
            csv_file=open(csv_file_name, 'a', newline='', buffering=1)
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print("* Error -", e)
  
    lastfm_last_activity_file = "lastfm_" + str(username) + "_last_activity.json"
    last_activity_read = []
    last_activity_ts = 0
    last_activity_artist = ""
    last_activity_track = ""

    try:
        if os.path.isfile(lastfm_last_activity_file):
            with open(lastfm_last_activity_file, 'r') as f:
                last_activity_read = json.load(f)
            if last_activity_read:
                last_activity_ts=last_activity_read[0]
                last_activity_artist=last_activity_read[1]
                last_activity_track=last_activity_read[2]
                lastfm_last_activity_file_mdate_dt=datetime.fromtimestamp(int(os.path.getmtime(lastfm_last_activity_file)))
                lastfm_last_activity_file_mdate=lastfm_last_activity_file_mdate_dt.strftime("%d %b %Y, %H:%M:%S")
                lastfm_last_activity_file_mdate_weekday=str(calendar.day_abbr[(lastfm_last_activity_file_mdate_dt).weekday()])
                print(f"* Last activity loaded from file '{lastfm_last_activity_file}' ({lastfm_last_activity_file_mdate_weekday} {lastfm_last_activity_file_mdate})")
    except Exception as e:
        print("Error -", e)

    try:
        new_track=user.get_now_playing()
        recent_tracks=lastfm_get_recent_tracks(username,network,10)
    except Exception as e:
        print("* Error -", e)
        sys.exit(1)

    last_track_start_ts_old2=int(recent_tracks[0].timestamp)
    lf_track_ts_start_old=last_track_start_ts_old2

    # User is offline (does not play music at the moment)
    if new_track is None:
        app_started_and_user_offline=True
        playing_track = None
        last_track_start_ts_old = 0   
        lf_user_online = False
        lf_active_ts_last=int(recent_tracks[0].timestamp)
        if lf_active_ts_last >= last_activity_ts:
            last_activity_artist=recent_tracks[0].track.artist
            last_activity_track=recent_tracks[0].track.title
        elif lf_active_ts_last<last_activity_ts and last_activity_ts>0:
            lf_active_ts_last=last_activity_ts

        last_activity_dt=datetime.fromtimestamp(lf_active_ts_last).strftime("%d %b %Y, %H:%M:%S")
        last_activity_ts_weekday=str(calendar.day_abbr[(datetime.fromtimestamp(lf_active_ts_last)).weekday()])

        artist_old=str(last_activity_artist)
        track_old=str(last_activity_track)

        print(f"* Last activity:\t{last_activity_ts_weekday} {last_activity_dt}")
        print(f"* Last track:\t\t{last_activity_artist} - {last_activity_track}")

        spotify_search_url,apple_search_url,genius_search_url=get_spotify_apple_genius_search_urls(str(last_activity_artist),str(last_activity_track))

        print("\n* Spotify search URL:\t" + spotify_search_url)
        print("* Apple search URL:\t" + apple_search_url)
        print("* Genius lyrics URL:\t" + genius_search_url + "\n")

        print("*** User is OFFLINE for",calculate_timespan(int(time.time()),lf_active_ts_last,show_seconds=False),"!")

    # User is online (plays music at the moment)
    else: 
        app_started_and_user_offline=False
        lf_active_ts_start=int(time.time())
        lf_active_ts_last=lf_active_ts_start
        lf_track_ts_start=lf_active_ts_start
        lf_track_ts_start_after_resume=lf_active_ts_start
        playing_resumed_ts=lf_active_ts_start
        artist=str(new_track.artist)
        track=str(new_track.title)
        album=str(new_track.info['album'])
        artist_old=artist
        track_old=track
        print("\nTrack:\t\t\t" + artist + " - " + track)
        print("Album:\t\t\t" + album)

        try:
            track_duration=pylast.Track(new_track.artist, new_track.title, network).get_duration()
            if track_duration>0:
                track_duration = int(str(track_duration)[0:-3])
                print("Duration:\t\t" + str(display_time(track_duration)))
        except Exception as e:
            pass

        spotify_search_url,apple_search_url,genius_search_url=get_spotify_apple_genius_search_urls(str(artist),str(track))

        print("\nSpotify search URL:\t" + spotify_search_url)
        print("Apple search URL:\t" + apple_search_url)
        print("Genius lyrics URL:\t" + genius_search_url)           

        print("\n*** User is currently ACTIVE !")

        listened_songs=1

        last_activity_to_save=[]
        last_activity_to_save.append(lf_track_ts_start)
        last_activity_to_save.append(artist)
        last_activity_to_save.append(track)
        last_activity_to_save.append(album)
        with open(lastfm_last_activity_file, 'w') as f:
            json.dump(last_activity_to_save, f, indent=2)              

        try: 
            if csv_file_name:
                write_csv_entry(csv_file_name, datetime.fromtimestamp(int(lf_track_ts_start)), artist, track, album)
        except Exception as e:
            print("* Cannot write CSV entry -", e)

        duration_m_body=""
        duration_m_body_html=""
        if track_duration>0:
            duration_m_body="\nDuration: " + display_time(track_duration)
            duration_m_body_html="<br>Duration: " + display_time(track_duration)

        m_subject="Last.fm user " + str(username) + " is active: '" + str(artist) + " - " + str(track) + "'"
        m_body="Track: " + str(artist) + " - " + str(track) + duration_m_body + "\nAlbum: " + str(album) + "\n\nSpotify search URL: " + spotify_search_url + "\nApple search URL: " + apple_search_url + "\nGenius lyrics URL: " + genius_search_url + "\n\nLast activity: " + get_date_from_ts(lf_active_ts_last) + get_cur_ts("\nTimestamp: ")
        m_body_html="<html><head></head><body>Track: <b><a href=\"" + spotify_search_url + "\">" + str(artist) + " - " + str(track) + "</a></b>" + duration_m_body_html + "<br>Album: " + str(album) + "<br><br>Apple search URL: <a href=\"" + apple_search_url + "\">" + str(artist) + " - " + str(track) + "</a>" + "<br>Genius lyrics URL: <a href=\"" + genius_search_url + "\">" + str(artist) + " - " + str(track) + "</a>" + "<br><br>Last activity: <b>" + get_date_from_ts(lf_active_ts_last) + "</b>" + get_cur_ts("<br>Timestamp: ") + "</body></html>"

        if active_notification:
            print("Sending email notification to",RECEIVER_EMAIL)
            send_email(m_subject,m_body,m_body_html,SMTP_SSL)

        playing_track=new_track
        last_track_start_ts_old=int(recent_tracks[0].timestamp)
        lf_user_online = True

        # If tracking functionality is enabled then play the current song via Spotify client
        if track_songs and SP_DC_COOKIE and SP_DC_COOKIE!="your_sp_dc_cookie_value":
            accessToken=spotify_get_access_token(SP_DC_COOKIE)
            sp_track_id=spotify_search_song_trackid(accessToken,artist,track,album)
            spotify_trigger_url=spotify_search_url
            if sp_track_id:                        
                spotify_trigger_url=spotify_convert_uri_to_url("spotify:track:" + sp_track_id)
                         
            if platform.system() == 'Darwin':       # macOS
                if sp_track_id:
                    script = 'tell app "Spotify" to play track "spotify:track:' + sp_track_id + '"'
                    proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                    stdout, stderr = proc.communicate(script)
                else:
                    subprocess.call(('open', spotify_trigger_url))
            elif platform.system() == 'Windows':    # Windows
                os.startfile(spotify_trigger_url)
            else:                                   # linux variants
                subprocess.call(('xdg-open', spotify_trigger_url))

    i = 0
    duplicate_entries=False
    print("\nList of recently listened tracks:\n")
    for previous, t, nxt in previous_and_next(reversed(recent_tracks)):
        i+=1
        print(str(i), "\t", datetime.fromtimestamp(int(t.timestamp)).strftime("%d %b %Y, %H:%M:%S"), "\t", str(calendar.day_abbr[(datetime.fromtimestamp(int(t.timestamp))).weekday()]), "\t", str(t.track))
        if previous:
            if previous.timestamp==t.timestamp:
                duplicate_entries=True
                print("DUPLICATE ENTRY")

    if duplicate_entries:
        print("*** Duplicate entries found, possible PRIVATE MODE")

    print("\nTracks/albums to monitor:", tracks)

    print_cur_ts("\nTimestamp:\t\t")

    # Main loop
    while True:
        try:
            recent_tracks=lastfm_get_recent_tracks(username,network,1)
            last_track_start_ts=int(recent_tracks[0].timestamp)
            new_track=user.get_now_playing()
            email_sent = False

            # Detecting new Last.fm entries when user is offline
            if not lf_user_online:
                if last_track_start_ts>last_track_start_ts_old2:
                    print("\n*** New last.fm entries showed up while user was offline!\n")
                    lf_track_ts_start_old=last_track_start_ts
                    duplicate_entries=False
                    i = 0
                    added_entries_list=""
                    try:
                        recent_tracks_while_offline=lastfm_get_recent_tracks(username,network,100)
                        for previous, t, nxt in previous_and_next(reversed(recent_tracks_while_offline)):
                            if int(t.timestamp)>int(last_track_start_ts_old2):
                                if 0 <= (lf_track_ts_start-int(t.timestamp)) <= 60:
                                    continue 
                                print(datetime.fromtimestamp(int(t.timestamp)).strftime("%d %b %Y, %H:%M:%S"), "\t", str(calendar.day_abbr[(datetime.fromtimestamp(int(t.timestamp))).weekday()]), "\t", str(t.track))
                                added_entries_list=added_entries_list + str(datetime.fromtimestamp(int(t.timestamp)).strftime("%d %b %Y, %H:%M:%S")) + ", " + str(calendar.day_abbr[(datetime.fromtimestamp(int(t.timestamp))).weekday()]) +  ": " + str(t.track) + "\n"
                                i+=1
                                if previous:
                                    if previous.timestamp==t.timestamp:
                                        duplicate_entries=True
                                        print("DUPLICATE ENTRY")                                
                                if csv_file_name:
                                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(t.timestamp)), str(t.track.artist), str(t.track.title), str(t.album))
                    except Exception as e:
                        print("* Error -", e)

                    if i>0 and offline_entries_notification:
                        if added_entries_list:
                            added_entries_list_mbody="\n\n" + added_entries_list
                        m_subject="Last.fm user " + str(username) + ": new entries showed up while user was offline"
                        m_body="New last.fm entries showed up while user was offline!" + added_entries_list_mbody + get_cur_ts("\nTimestamp: ")
                        print("Sending email notification to",RECEIVER_EMAIL)
                        send_email(m_subject,m_body,"",SMTP_SSL)                 
                    
                    print_cur_ts("\nTimestamp:\t\t")            

            # User is online (plays music at the moment)
            if new_track is not None:             

                # User paused music earlier
                if playing_paused==True and lf_user_online:
                    playing_resumed_ts=int(time.time())
                    lf_track_ts_start_after_resume=lf_track_ts_start_after_resume+(playing_resumed_ts-playing_paused_ts)-LASTFM_ACTIVE_CHECK_INTERVAL
                    paused_counter=paused_counter+(int(playing_resumed_ts)-int(playing_paused_ts))
                    print("User RESUMED playing after",calculate_timespan(int(playing_resumed_ts),int(playing_paused_ts)))
                    print_cur_ts("\nTimestamp:\t\t")
                    
                    # If tracking functionality is enabled then resume the current song via Spotify client
                    if track_songs:                                         
                        if platform.system() == 'Darwin':       # macOS
                            script = 'tell app "Spotify" to play'
                            proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                            stdout, stderr = proc.communicate(script)
                        elif platform.system() == 'Windows':    # Windows
                            pass
                            #os.startfile(spotify_trigger_url)
                        else:                                   # Linux variants
                            pass                               
                            #subprocess.call(('xdg-open', spotify_trigger_url))                    

                playing_paused=False

                # Trying to overcome the issue with Last.fm API reporting newly played song (but still continues the same)
                if (int(time.time())<=(lf_track_ts_start+20)) and (last_track_start_ts > last_track_start_ts_old) and (new_track == playing_track):
                    last_track_start_ts_old = last_track_start_ts

                # Track has changed
                if (new_track != playing_track or (last_track_start_ts > last_track_start_ts_old and last_track_start_ts>lf_track_ts_start_old-20)):

                    alive_counter = 0

                    playing_track=new_track
                    artist=str(playing_track.artist)
                    track=str(playing_track.title)
                    album=str(playing_track.info['album'])
                    info=playing_track.info                                     

                    # Handling how long user played the previous track, if skipped it etc. - in case track duration is available
                    if track_duration>0 and lf_track_ts_start_after_resume>0 and lf_user_online:
                        played_for_display=False
                        played_for_time=int(time.time())-lf_track_ts_start_after_resume
                        listened_percentage=(played_for_time) / (track_duration-LASTFM_ACTIVE_CHECK_INTERVAL-1)

                        if (played_for_time) < (track_duration-LASTFM_ACTIVE_CHECK_INTERVAL-1):
                            played_for=display_time(played_for_time) + " (out of " + display_time(track_duration) + ")"              
                            if listened_percentage <= SKIPPED_SONG_THRESHOLD2:
                                if signal_previous_the_same:
                                    played_for=played_for + " - CONT (" + str(int(listened_percentage*100)) + "%)"
                                    signal_previous_the_same=False
                                else:
                                    played_for=played_for + " - SKIPPED (" + str(int(listened_percentage*100)) + "%)"
                                    skipped_songs+=1
                            else:
                                played_for=played_for + " (" + str(int(listened_percentage*100)) + "%)"
                            played_for_display=True
                        else:
                            played_for=display_time(played_for_time)
                            if listened_percentage >= 1.20 or (played_for_time-track_duration>=15):
                                played_for=played_for + " - LONGER than track duration (+ " + display_time(played_for_time-track_duration) + ", " + str(int(listened_percentage*100)) + "%)"
                                played_for_display=True

                        if played_for_display:
                            played_for_m_body="\n\nUser played the previous track for: " + played_for
                            played_for_m_body_html="<br><br>User played the previous track for: " + played_for
                            if progress_indicator:
                                print("---------------------------------------------------------------------------------------------------------")
                            print("User played the previous track for: " + played_for)
                            if not progress_indicator:
                                print("---------------------------------------------------------------------------------------------------------")                    
                    # Handling how long user played the previous track, if skipped it etc. - in case track duration is NOT available
                    elif track_duration<=0 and lf_track_ts_start_after_resume>0 and lf_user_online:
                        played_for=display_time(int(time.time())-lf_track_ts_start_after_resume)
                        if ((int(time.time())-lf_track_ts_start_after_resume)<=SKIPPED_SONG_THRESHOLD1):
                            if signal_previous_the_same:
                                played_for_m_body="\n\nUser CONT the previous track for: " + played_for
                                played_for_m_body_html="<br><br>User CONT the previous track for: " + played_for
                                played_for_str="User CONT the previous track for " + played_for
                                signal_previous_the_same=False
                            else:
                                skipped_songs+=1
                                played_for_m_body="\n\nUser SKIPPED the previous track after: " + played_for
                                played_for_m_body_html="<br><br>User SKIPPED the previous track after: " + played_for
                                played_for_str="User SKIPPED the previous track after " + played_for
                        else:                            
                            played_for_m_body="\n\nUser played the previous track for: " + played_for
                            played_for_m_body_html="<br><br>User played the previous track for: " + played_for
                            played_for_str="User played the previous track for: " + played_for

                        if progress_indicator:
                            print("---------------------------------------------------------------------------------------------------------")
                        print(played_for_str)
                        if not progress_indicator:
                            print("---------------------------------------------------------------------------------------------------------")
                    else:
                        played_for_m_body=""
                        played_for_m_body_html="" 

                    if progress_indicator:
                        print("---------------------------------------------------------------------------------------------------------")

                    print("Last.fm user:\t\t" + str(username) + "\n")

                    listened_songs+=1

                    # Clearing the flag used to indicate CONT songs (continued from previous playing session)
                    if listened_songs==2:
                        signal_previous_the_same=False

                    if lf_track_ts_start>0:
                        lf_track_ts_start_old=lf_track_ts_start
                    lf_track_ts_start=int(time.time())
                    lf_track_ts_start_after_resume=lf_track_ts_start
                    last_track_start_ts_old = last_track_start_ts                    

                    print("Track:\t\t\t" + artist + " - " + track)
                    print("Album:\t\t\t" + album)

                    try:
                        track_duration=pylast.Track(playing_track.artist, playing_track.title, network).get_duration()
                        if track_duration>0:
                            track_duration = int(str(track_duration)[0:-3])
                            print("Duration:\t\t" + str(display_time(track_duration)))
                    except Exception as e:
                        track_duration = 0 
                        pass

                    spotify_search_url,apple_search_url,genius_search_url=get_spotify_apple_genius_search_urls(str(artist),str(track))

                    print("\nSpotify search URL:\t" + spotify_search_url)
                    print("Apple search URL:\t" + apple_search_url)
                    print("Genius lyrics URL:\t" + genius_search_url)                       

                    last_activity_to_save=[]
                    last_activity_to_save.append(lf_track_ts_start)
                    last_activity_to_save.append(artist)
                    last_activity_to_save.append(track)
                    last_activity_to_save.append(album)
                    with open(lastfm_last_activity_file, 'w') as f:
                        json.dump(last_activity_to_save, f, indent=2)         

                    duration_m_body=""
                    duration_m_body_html=""
                    if track_duration>0:
                        duration_m_body="\nDuration: " + display_time(track_duration)
                        duration_m_body_html="<br>Duration: " + display_time(track_duration)

                    # If tracking functionality is enabled then play the current song via Spotify client
                    if track_songs and SP_DC_COOKIE and SP_DC_COOKIE!="your_sp_dc_cookie_value":
                        accessToken=spotify_get_access_token(SP_DC_COOKIE)
                        sp_track_id=spotify_search_song_trackid(accessToken,artist,track,album)
                        spotify_trigger_url=spotify_search_url
                        if sp_track_id:                         
                            spotify_trigger_url=spotify_convert_uri_to_url("spotify:track:" + sp_track_id)
                                     
                        if platform.system() == 'Darwin':       # macOS
                            if sp_track_id:
                                script = 'tell app "Spotify" to play track "spotify:track:' + sp_track_id + '"'
                                proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                                stdout, stderr = proc.communicate(script)
                            else:
                                subprocess.call(('open', spotify_trigger_url))
                        elif platform.system() == 'Windows':    # Windows
                            os.startfile(spotify_trigger_url)
                        else:                                   # linux variants
                            subprocess.call(('xdg-open', spotify_trigger_url))

                    # User was offline and got active
                    if (not lf_user_online and (lf_track_ts_start-lf_active_ts_last) > LASTFM_INACTIVITY_CHECK and lf_active_ts_last>0) or (not lf_user_online and lf_active_ts_last>0 and app_started_and_user_offline):
                        app_started_and_user_offline=False
                        last_track_start_changed=""
                        last_track_start_changed_html=""
                        lf_active_ts_last_old=lf_active_ts_last
                        if last_track_start_ts>(lf_active_ts_last+60):
                            last_track_start_changed="\n(last track start changed from " + get_short_date_from_ts(lf_active_ts_last) + " to " + get_short_date_from_ts(last_track_start_ts) + " - offline mode ?)"
                            last_track_start_changed_html="<br>(last track start changed from <b>" + get_short_date_from_ts(lf_active_ts_last) + "</b> to <b>" + get_short_date_from_ts(last_track_start_ts) + "</b> - offline mode ?)"                            
                            lf_active_ts_last=last_track_start_ts

                        duplicate_entries=False
                        private_mode=""
                        private_mode_html=""
                        try:
                            recent_tracks_while_offline=lastfm_get_recent_tracks(username,network,10)
                            for previous, t, nxt in previous_and_next(reversed(recent_tracks_while_offline)):
                                if previous:
                                    if previous.timestamp==t.timestamp:
                                        duplicate_entries=True
                        except Exception as e:
                            print("* Error -", e)
                        if duplicate_entries:
                            private_mode="\n\nDuplicate entries found, possible private mode (" + get_range_of_dates_from_tss(lf_active_ts_last_old,lf_track_ts_start,short=True) + ")"
                            private_mode_html="<br><br>Duplicate entries found, possible <b>private mode</b> (<b>" + get_range_of_dates_from_tss(lf_active_ts_last_old,lf_track_ts_start,short=True) + "</b>)"                            
                            print("\n*** Duplicate entries found, possible PRIVATE MODE (" + get_range_of_dates_from_tss(lf_active_ts_last_old,lf_track_ts_start,short=True) + ")")

                        print("\n*** User got ACTIVE after being offline for",calculate_timespan(int(lf_track_ts_start),int(lf_active_ts_last)),last_track_start_changed)
                        print("*** Last activity:\t" + get_date_from_ts(lf_active_ts_last))
                        
                        # We signal that the currectly played song is the same as previous one before user got inactive, so might be continuation of previous track
                        if artist_old==artist and track_old==track:
                            signal_previous_the_same=True
                        else:
                            signal_previous_the_same=False
                        paused_counter=0
                        listened_songs=1
                        skipped_songs=0
                        lf_active_ts_start=lf_track_ts_start
                        playing_resumed_ts=lf_track_ts_start
                        m_subject="Last.fm user " + str(username) + " is active: '" + str(artist) + " - " + str(track) + "' (after " + calculate_timespan(int(lf_track_ts_start),int(lf_active_ts_last),show_seconds=False) + " - " + get_short_date_from_ts(lf_active_ts_last) + ")"
                        m_body="Track: " + str(artist) + " - " + str(track) + duration_m_body + "\nAlbum: " + str(album) + "\n\nSpotify search URL: " + spotify_search_url + "\nApple search URL: " + apple_search_url + "\nGenius lyrics URL: " + genius_search_url + played_for_m_body + "\n\nFriend got active after being offline for " + calculate_timespan(int(lf_track_ts_start),int(lf_active_ts_last)) + last_track_start_changed + private_mode + "\n\nLast activity: " + get_date_from_ts(lf_active_ts_last) + get_cur_ts("\nTimestamp: ")
                        m_body_html="<html><head></head><body>Track: <b><a href=\"" + spotify_search_url + "\">" + str(artist) + " - " + str(track) + "</a></b>" + duration_m_body_html + "<br>Album: " + str(album) + "<br><br>Apple search URL: <a href=\"" + apple_search_url + "\">" + str(artist) + " - " + str(track) + "</a>" + "<br>Genius lyrics URL: <a href=\"" + genius_search_url + "\">" + str(artist) + " - " + str(track) + "</a>" + played_for_m_body_html + "<br><br>Friend got active after being offline for <b>" + calculate_timespan(int(lf_track_ts_start),int(lf_active_ts_last)) + "</b>" + last_track_start_changed_html + private_mode_html + "<br><br>Last activity: <b>" + get_date_from_ts(lf_active_ts_last) + "</b>" + get_cur_ts("<br>Timestamp: ") + "</body></html>"

                        if active_notification:
                            print("Sending email notification to",RECEIVER_EMAIL)
                            send_email(m_subject,m_body,m_body_html,SMTP_SSL)
                            email_sent=True

                    if (track_notification or song_notification) and not email_sent:
                        m_subject="Last.fm user " + str(username) + ": '" + str(artist) + " - " + str(track) + "'"
                        m_body="Track: " + str(artist) + " - " + str(track) + duration_m_body + "\nAlbum: " + str(album) + "\n\nSpotify search URL: " + spotify_search_url + "\nApple search URL: " + apple_search_url + "\nGenius lyrics URL: " + genius_search_url + played_for_m_body + get_cur_ts("\n\nTimestamp: ")
                        m_body_html="<html><head></head><body>Track: <b><a href=\"" + spotify_search_url + "\">" + str(artist) + " - " + str(track) + "</a></b>" + duration_m_body_html + "<br>Album: " + str(album) + "<br><br>Apple search URL: <a href=\"" + apple_search_url + "\">" + str(artist) + " - " + str(track) + "</a>" + "<br>Genius lyrics URL: <a href=\"" + genius_search_url + "\">" + str(artist) + " - " + str(track) + "</a>" + played_for_m_body_html + get_cur_ts("<br><br>Timestamp: ") + "</body></html>"

                    if track.upper() in map(str.upper, tracks) or album.upper() in map(str.upper, tracks): 
                        print("\n*** Track/album matched with the list!")

                        if track_notification and not email_sent:
                            print("Sending email notification to",RECEIVER_EMAIL)
                            send_email(m_subject,m_body,m_body_html,SMTP_SSL)
                            email_sent=True

                    if song_notification and not email_sent:                     
                        print("Sending email notification to",RECEIVER_EMAIL)
                        send_email(m_subject,m_body,m_body_html,SMTP_SSL)
                        email_sent=True

                    lf_user_online=True
                    lf_active_ts_last=int(time.time())

                    artist_old=artist
                    track_old=track

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(lf_track_ts_start)), artist, track, album)
                    except Exception as e:
                        print("* Cannot write CSV entry -", e)

                    print_cur_ts("\nTimestamp:\t\t")
                
                # Track has not changed, user is online and continues playing
                else:
                    lf_active_ts_last=int(time.time())
                    # We display progress indicator if flag is enabled
                    if lf_user_online and progress_indicator:
                        ts=datetime.fromtimestamp(lf_active_ts_last).strftime('%H:%M:%S')
                        delta_ts=(lf_active_ts_last+LASTFM_ACTIVE_CHECK_INTERVAL)-lf_track_ts_start_after_resume
                        if delta_ts>0:
                            delta_diff_str="%02d:%02d:%02d" % (delta_ts // 3600, delta_ts // 60 % 60, delta_ts % 60)
                        else:
                            delta_diff_str="00:00:00"
                        print(f"# {ts} +{delta_diff_str}")
            
            # User is offline (does not play music at the moment)
            else:

                alive_counter+=1

                # User paused playing the music
                if ((int(time.time()) - lf_active_ts_last) > (LASTFM_ACTIVE_CHECK_INTERVAL*LASTFM_BREAK_CHECK_MULTIPLIER)) and lf_user_online and lf_active_ts_last>0 and lf_active_ts_start>0 and (LASTFM_ACTIVE_CHECK_INTERVAL*LASTFM_BREAK_CHECK_MULTIPLIER)<LASTFM_INACTIVITY_CHECK and LASTFM_BREAK_CHECK_MULTIPLIER>0 and playing_paused==False:
                    playing_paused=True
                    playing_paused_ts=lf_active_ts_last
                    if progress_indicator:
                        print("---------------------------------------------------------------------------------------------------------")
                    print("User PAUSED playing after " + calculate_timespan(int(playing_resumed_ts),int(playing_paused_ts)) + " (inactivity timer: " + display_time(LASTFM_BREAK_CHECK_MULTIPLIER*LASTFM_ACTIVE_CHECK_INTERVAL) + ")")
                    print("Last activity:\t\t" + get_date_from_ts(lf_active_ts_last))
                    print_cur_ts("\nTimestamp:\t\t")
                    
                    # If tracking functionality is enabled then pause the current song via Spotify client
                    if track_songs:                                         
                        if platform.system() == 'Darwin':       # macOS
                            script = 'tell app "Spotify" to pause'
                            proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                            stdout, stderr = proc.communicate(script)
                        elif platform.system() == 'Windows':    # Windows
                            pass
                            #os.startfile(spotify_trigger_url)
                        else:                                   # Linux variants
                            pass                               
                            #subprocess.call(('xdg-open', spotify_trigger_url))                      
               
                # User got inactive
                if ((int(time.time()) - lf_active_ts_last) > LASTFM_INACTIVITY_CHECK) and lf_user_online and lf_active_ts_last>0 and lf_active_ts_start>0:
                    if progress_indicator:
                        print("---------------------------------------------------------------------------------------------------------")
                    lf_user_online=False
                    print("*** User got INACTIVE after listening to music for",calculate_timespan(int(lf_active_ts_last),int(lf_active_ts_start)))
                    print("*** User played music from " + get_range_of_dates_from_tss(lf_active_ts_start,lf_active_ts_last,short=True,between_sep=" to "))
                    playing_resumed_ts=int(time.time())
                    paused_mbody=""
                    paused_mbody_html=""
                    if paused_counter>0:
                        paused_percentage=int((paused_counter/(int(lf_active_ts_last)-int(lf_active_ts_start)))*100)
                        print("*** User paused music for " + display_time(paused_counter) + " (" + str(paused_percentage) + "%)")
                        paused_mbody="\nUser paused music for " + display_time(paused_counter) + " (" + str(paused_percentage) + "%)"
                        paused_mbody_html="<br>User paused music for <b>" + display_time(paused_counter) + " (" + str(paused_percentage) + "%)</b>"
                    paused_counter=0

                    listened_songs_text="*** User played " + str(listened_songs) + " songs"
                    listened_songs_mbody="\n\nUser played " + str(listened_songs) + " songs"
                    listened_songs_mbody_html="<br><br>User played <b>" + str(listened_songs) + "</b> songs"
                    if skipped_songs>0:
                        skipped_songs_text=", skipped " + str(skipped_songs) + " songs (" + str(int((skipped_songs/listened_songs)*100)) + "%)"
                        listened_songs_text=listened_songs_text + skipped_songs_text
                        listened_songs_mbody=listened_songs_mbody + skipped_songs_text
                        listened_songs_mbody_html=listened_songs_mbody_html + ", skipped <b>" + str(skipped_songs) + "</b> songs <b>(" + str(int((skipped_songs/listened_songs)*100)) + "%)</b>"

                    print(listened_songs_text + "\n")

                    print("*** Last activity:\t" + get_date_from_ts(lf_active_ts_last) + " (inactive timer: " + display_time(LASTFM_INACTIVITY_CHECK) + ")")
                    
                    # If tracking functionality is enabled then either pause the current song via Spotify client or play the indicated SP_USER_GOT_OFFLINE_TRACK_ID "finishing" song
                    if track_songs:
                        sp_track_id=SP_USER_GOT_OFFLINE_TRACK_ID
                                     
                        if sp_track_id:
                            if platform.system() == 'Darwin':       # macOS
                                script = 'tell app "Spotify" to play track "spotify:track:' + sp_track_id + '"'
                                proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                                stdout, stderr = proc.communicate(script)
                                if SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE > 0:
                                    time.sleep(SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE)
                                    script = 'tell app "Spotify" to pause'
                                    proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)                                                     
                                    stdout, stderr = proc.communicate(script)
                        else:
                            script = 'tell app "Spotify" to pause'
                            proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)                                                     
                            stdout, stderr = proc.communicate(script)                                
                      
                    last_activity_to_save=[]
                    last_activity_to_save.append(lf_active_ts_last)
                    last_activity_to_save.append(artist)
                    last_activity_to_save.append(track)
                    last_activity_to_save.append(album)
                    with open(lastfm_last_activity_file, 'w') as f:
                        json.dump(last_activity_to_save, f, indent=2)                        
                    if inactive_notification:
                        m_subject="Last.fm user " + str(username) + " is inactive: '" + str(artist) + " - " + str(track) + "' (after " + calculate_timespan(int(lf_active_ts_last),int(lf_active_ts_start),show_seconds=False) + ": " + get_range_of_dates_from_tss(lf_active_ts_start,lf_active_ts_last,short=True) + ")"
                        m_body="Last played: " + str(artist) + " - " + str(track) + "\nAlbum: " + str(album) + "\n\nSpotify search URL: " + spotify_search_url + "\nApple search URL: " + apple_search_url + "\nGenius lyrics URL: " + genius_search_url + "\n\nUser got inactive after listening to music for " + calculate_timespan(int(lf_active_ts_last),int(lf_active_ts_start)) + "\nUser played music from " + get_range_of_dates_from_tss(lf_active_ts_start,lf_active_ts_last,short=True,between_sep=" to ") + paused_mbody + listened_songs_mbody + "\n\nLast activity: " + get_date_from_ts(lf_active_ts_last) + "\nInactivity timer: " + display_time(LASTFM_INACTIVITY_CHECK) + get_cur_ts("\nTimestamp: ")
                        m_body_html="<html><head></head><body>Last played: <b><a href=\"" + spotify_search_url + "\">" + str(artist) + " - " + str(track) + "</a></b>" + "<br>Album: " + str(album) + "<br><br>Apple search URL: <a href=\"" + apple_search_url + "\">" + str(artist) + " - " + str(track) + "</a>" + "<br>Genius lyrics URL: <a href=\"" + genius_search_url + "\">" + str(artist) + " - " + str(track) + "</a><br><br>User got inactive after listening to music for <b>" + calculate_timespan(int(lf_active_ts_last),int(lf_active_ts_start)) + "</b><br>User played music from <b>" + get_range_of_dates_from_tss(lf_active_ts_start,lf_active_ts_last,short=True,between_sep="</b> to <b>") + "</b>" + paused_mbody_html + listened_songs_mbody_html + "<br><br>Last activity: <b>" + get_date_from_ts(lf_active_ts_last) + "</b>" + "<br>Inactivity timer: " + display_time(LASTFM_INACTIVITY_CHECK) + get_cur_ts("<br>Timestamp: ") + "</body></html>"

                        print("Sending email notification to",RECEIVER_EMAIL)
                        send_email(m_subject,m_body,m_body_html,SMTP_SSL)
                        email_sent=True
                    lf_active_ts_start=0
                    playing_track = None
                    last_track_start_ts = 0
                    listened_songs=0
                    skipped_songs=0
                    print_cur_ts("\nTimestamp:\t\t")                                                

                if alive_counter >= TOOL_ALIVE_COUNTER:
                    print_cur_ts("Alive check, timestamp: ")
                    alive_counter = 0

            # Stuff to do regardless if the user is online or offline
            if last_track_start_ts>0:
                last_track_start_ts_old2=last_track_start_ts

        except Exception as e:
            print("Error -", e)
            if 'Invalid API key' in str(e) or 'API Key Suspended' in str(e):
                print("* API key might not be valid anymore!")
                if error_notification and not email_sent:
                    m_subject="lastfm_monitor: API key error! (user: " + str(username) + ")"
                    m_body="API key might not be valid anymore: " + str(e) + get_cur_ts("\n\nTimestamp: ")
                    m_body_html="<html><head></head><body>API key might not be valid anymore: " + str(e) + get_cur_ts("<br><br>Timestamp: ") + "</body></html>"
                    print("Sending email notification to",RECEIVER_EMAIL)
                    send_email(m_subject,m_body,m_body_html,SMTP_SSL)
                    email_sent=True
            print_cur_ts("Timestamp:\t\t")


        if lf_user_online:
            time.sleep(LASTFM_ACTIVE_CHECK_INTERVAL)
        else:
            time.sleep(LASTFM_CHECK_INTERVAL)

        new_track=None

if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        os.system('clear')
    except:
        print("* Cannot clear the screen contents")

    print("Last.fm Monitoring Tool",VERSION,"\n")

    parser = argparse.ArgumentParser("lastfm_monitor")
    parser.add_argument("user", nargs="?", default="test", help="Last.fm username", type=str)
    parser.add_argument("-s", "--lastfm_tracks", help="Filename with Last.fm tracks/albums to monitor", type=str, metavar="FILENAME")
    parser.add_argument("-l","--list_recent_tracks", help="List recently played tracks for the user", type=str, metavar="USERNAME")
    parser.add_argument("-n", "--number_of_recent_tracks", help="Number of tracks to display if used with -l", type=int)
    parser.add_argument("-b", "--csv_file", help="Write every listened track to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-a","--active_notification", help="Send email notification once user gets active", action='store_true')
    parser.add_argument("-i","--inactive_notification", help="Send email notification once user gets inactive", action='store_true')
    parser.add_argument("-t","--track_notification", help="Send email notification once monitored track/album is found", action='store_true')
    parser.add_argument("-j","--song_notification", help="Send email notification for every changed song", action='store_true')
    parser.add_argument("-e","--error_notification", help="Disable sending email notifications in case of errors like invalid API key", action='store_false')
    parser.add_argument("-f","--offline_entries_notification", help="Send email notification in case new entries are detected while user is offline", action='store_true')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks if user is offline, in seconds", type=int)
    parser.add_argument("-k", "--active_check_interval", help="Time between monitoring checks if user is active, in seconds", type=int)
    parser.add_argument("-o", "--offline_timer", help="Time required to mark inactive user as offline, in seconds", type=int)
    parser.add_argument("-d", "--disable_logging", help="Disable logging to file 'lastfm_monitor_user.log' file", action='store_true')
    parser.add_argument("-p", "--progress_indicator", help="Show progress indicator while user is listening", action='store_true')
    parser.add_argument("-g", "--track_songs", help="Automatically track listened songs by opening Spotify client", action='store_true')
    parser.add_argument("-m", "--play_break_multiplier", help="If more than 0 it will show when user stops playing/resumes (while active), play break is assumed to be play_break_multiplier*active_check_interval", type=int)
    args = parser.parse_args()

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.check_interval:
        LASTFM_CHECK_INTERVAL=args.check_interval
        TOOL_ALIVE_COUNTER=TOOL_ALIVE_INTERVAL/LASTFM_CHECK_INTERVAL

    if args.active_check_interval:
        LASTFM_ACTIVE_CHECK_INTERVAL=args.active_check_interval

    if args.offline_timer:
        LASTFM_INACTIVITY_CHECK=args.offline_timer

    if args.play_break_multiplier:
        LASTFM_BREAK_CHECK_MULTIPLIER=args.play_break_multiplier

    network = pylast.LastFMNetwork(LASTFM_API_KEY, LASTFM_API_SECRET)

    if args.list_recent_tracks:
        if args.number_of_recent_tracks and args.number_of_recent_tracks>0:
            tracks_n=args.number_of_recent_tracks
        else:
            tracks_n=30
        print("* Listing " + str(tracks_n) + " tracks recently listened by " + str(args.list_recent_tracks) + ":\n")
        user = network.get_user(args.list_recent_tracks)
        lastfm_list_tracks(args.list_recent_tracks,user,network,tracks_n)
        sys.exit(0)

    user = network.get_user(args.user)

    if args.lastfm_tracks:
        try:
            with open(args.lastfm_tracks) as file:
                lf_tracks = file.read().splitlines()
            file.close()
        except Exception as e:
            print("\n* Error, file with Last.fm tracks cannot be opened -", e)
            sys.exit(1)
    else:
        lf_tracks=[]

    if args.csv_file:
        csv_enabled=True
        csv_exists=os.path.isfile(args.csv_file)
        try:
            csv_file=open(args.csv_file, 'a', newline='', buffering=1)
        except Exception as e:
            print("\n* Error, CSV file cannot be opened for writing -", e)
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled=False
        csv_file=None
        csv_exists=False

    if not args.disable_logging:
        lf_logfile = lf_logfile + "_" + args.user + ".log"
        sys.stdout = Logger(lf_logfile)

    active_notification=args.active_notification
    inactive_notification=args.inactive_notification
    song_notification=args.song_notification
    track_notification=args.track_notification
    offline_entries_notification=args.offline_entries_notification
    progress_indicator=args.progress_indicator
    track_songs=args.track_songs

    print("* Last.fm timers:\t\t[check interval: " + display_time(LASTFM_CHECK_INTERVAL) + "] [active check interval: " + display_time(LASTFM_ACTIVE_CHECK_INTERVAL) + "] [inactivity: " + display_time(LASTFM_INACTIVITY_CHECK) + "]")
    print("* Email notifications:\t\t[active = " + str(active_notification) + "] [inactive = " + str(inactive_notification) + "] [tracked = " + str(track_notification) + "]\n* \t\t\t\t[every song = " + str(song_notification) + "] [offline entries = " + str(offline_entries_notification) + "] [errors = " + str(args.error_notification) + "]")
    print("* Output logging disabled:\t" + str(args.disable_logging))
    print("* Progress indicator enabled:\t" + str(progress_indicator))
    print("* Track listened songs:\t\t" + str(track_songs))
    print("* Play break multiplier:\t" + str(LASTFM_BREAK_CHECK_MULTIPLIER) + " (" + display_time(LASTFM_BREAK_CHECK_MULTIPLIER*LASTFM_ACTIVE_CHECK_INTERVAL) + ")")
    print("* CSV logging enabled:\t\t" + str(csv_enabled),"\n")

    signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
    signal.signal(signal.SIGUSR2, toggle_song_notifications_signal_handler)
    signal.signal(signal.SIGHUP, toggle_progress_indicator_signal_handler)
    signal.signal(signal.SIGCONT, toggle_track_notifications_signal_handler)
    signal.signal(signal.SIGTRAP, increase_inactivity_check_signal_handler)
    signal.signal(signal.SIGABRT, decrease_inactivity_check_signal_handler)

    out = "Monitoring user %s" % args.user
    print(out)
    print("-" * len(out))

    lastfm_monitor_user(user,network,args.user,lf_tracks,args.error_notification,args.csv_file,csv_exists)

    sys.stdout = stdout_bck
    sys.exit(0)

