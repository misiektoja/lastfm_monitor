#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v2.7

Tool implementing real-time tracking of Last.fm users music activity:
https://github.com/misiektoja/lastfm_monitor/

Python pip3 requirements:

pylast
requests
python-dateutil
pyotp
spotipy (optional, only for Spotify-related features)
python-dotenv (optional)
beautifulsoup4 (optional, only for friends and profile tracking)
colorama (optional, only for coloured output in the classic Windows Command Prompt)
"""

VERSION = "2.7"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
# Create your Last.fm API key and shared secret at:
# https://www.last.fm/api/account/create
#
# Or retrieve an existing one from:
# https://www.last.fm/api/accounts
#
# Provide the LASTFM_API_KEY and LASTFM_API_SECRET secrets using one of the following methods:
#   - Pass it at runtime with -u / --lastfm-api-key and -w / --lastfm-secret
#   - Set it as an environment variable (e.g. export LASTFM_API_KEY=...; export LASTFM_API_SECRET=...)
#   - Add it to ".env" file (LASTFM_API_KEY=... and LASTFM_API_SECRET=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
LASTFM_API_KEY = "your_lastfm_api_key"
LASTFM_API_SECRET = "your_lastfm_api_secret"

# Last.fm username to monitor
# A username given on the command line overrides this value
LASTFM_USERNAME = ""

# Spotify Client Credentials OAuth Flow (OAuth app) is optional
# When configured, the official Web API is tried before the anonymous web-player backend
#
# Only needed if you want to:
#   - Get track duration from Spotify (via USE_TRACK_DURATION_FROM_SPOTIFY / -r), which is more accurate than Last.fm
#   - Use automatic playback functionality (via TRACK_SONGS / -g), which requires Spotify track IDs
#
# To obtain the credentials for the Web API:
#   - Log in to Spotify Developer dashboard: https://developer.spotify.com/dashboard
#   - Create a new app
#   - For 'Redirect URL', use: http://127.0.0.1:1234
#   - Select 'Web API' as the intended API
#   - Copy the 'Client ID' and 'Client Secret'
#
# Provide the SP_CLIENT_ID and SP_CLIENT_SECRET secrets using one of the following methods:
#   - Pass it at runtime with -z / --spotify-creds (use SP_CLIENT_ID:SP_CLIENT_SECRET format - note the colon separator)
#   - Set it as an environment variable (e.g. export SP_CLIENT_ID=...; export SP_CLIENT_SECRET=...)
#   - Add it to ".env" file (SP_CLIENT_ID=... and SP_CLIENT_SECRET=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
#
# The tool automatically refreshes the access token, so it remains valid indefinitely
SP_CLIENT_ID = "your_spotify_app_client_id"
SP_CLIENT_SECRET = "your_spotify_app_client_secret"

# Path used by Spotipy to cache OAuth app access tokens across restarts
# Set to an empty string to use an in-memory cache
SP_TOKENS_FILE = ".lastfm-monitor-oauth-app.json"

# ----------------------------------------------
# Advanced Spotify web-player TOTP options
# Modifying the values below is NOT recommended!
# ----------------------------------------------

# TOTP parameters used to sign anonymous Spotify web-player token requests
#
# The Spotify web player derives a time-based one-time password from a versioned secret embedded in its
# JavaScript bundle and sends it with every anonymous token request. These options ship set to v61, the
# version the web player has selected since January 2026.
#
# You only need to change them if Spotify rotates the secret and the anonymous web-player metadata backend
# starts failing to obtain a token. To refresh them:
#   - Run the spotify_monitor_secret_grabber tool to extract the current version and cipher bytes from the
#     live web-player bundle
#   - Set SPOTIFY_TOTP_VERSION to the extracted version identifier (a positive integer)
#   - Set SPOTIFY_TOTP_SECRET_CIPHER_BYTES to the extracted cipher bytes (a non-empty sequence of integers)
SPOTIFY_TOTP_VERSION = 61
SPOTIFY_TOTP_SECRET_CIPHER_BYTES = (44, 55, 47, 42, 70, 40, 34, 114, 76, 74, 50, 111, 120, 97, 75, 76, 94, 102, 43, 69, 49, 120, 118, 80, 64, 78)

# SMTP settings for sending email notifications
# If left as-is, no notifications will be sent
#
# Provide the SMTP_PASSWORD secret using one of the following methods:
#   - Set it as an environment variable (e.g. export SMTP_PASSWORD=...)
#   - Add it to ".env" file (SMTP_PASSWORD=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# Whether to send an email when user becomes active
# Can also be enabled via the -a flag
ACTIVE_NOTIFICATION = False

# Whether to send an email when user goes inactive
# Can also be enabled via the -i flag
INACTIVE_NOTIFICATION = False

# Whether to send an email when a monitored track/album plays
# Can also be enabled via the -t flag
TRACK_NOTIFICATION = False

# Whether to send an email on every song change
# Can also be enabled via the -j flag
SONG_NOTIFICATION = False

# Whether to send an email when user plays a song on loop
# Triggered if the same song is played more than SONG_ON_LOOP_VALUE times
# Can also be enabled via the -x flag
SONG_ON_LOOP_NOTIFICATION = False

# Whether to send an email when new scrobbles arrive while user is offline
# Can also be enabled via the -f flag
OFFLINE_ENTRIES_NOTIFICATION = False

# Whether to send an email on errors
# Can also be disabled via the -e flag
ERROR_NOTIFICATION = True

# ----------------------------
# Webhook Notifications
# ----------------------------

# Master switch for webhook notifications through Discord or ntfy
# Event settings below select which notifications are sent
# Can also be enabled via the --webhook flag
WEBHOOK_ENABLED = False

# Service used to deliver webhook notifications: "discord" or "ntfy"
# Known Discord and ntfy.sh URLs correct a mismatched configured value at runtime
# Can also be set via the --webhook-provider flag
WEBHOOK_PROVIDER = "discord"

# Private destination used to send webhook notifications
# Discord: Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL
# ntfy: complete topic URL such as https://ntfy.sh/your-private-topic
# Prefer --set-webhook-url, an environment variable or a dotenv file instead of storing this private URL here
# The --webhook-url flag is available for one-run overrides but may leave the private URL in shell history
WEBHOOK_URL = "your_webhook_url"

# Discord display name (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_USERNAME = "Last.fm Monitor"

# Discord avatar URL (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_AVATAR_URL = ""

# Whether to send a webhook notification when the user becomes active
# Can also be enabled via the --webhook-active flag
WEBHOOK_ACTIVE_NOTIFICATION = False

# Whether to send a webhook notification when the user goes inactive
# Can also be enabled via the --webhook-inactive flag
WEBHOOK_INACTIVE_NOTIFICATION = False

# Whether to send a webhook notification when a monitored track or album plays
# Can also be enabled via the --webhook-track flag
WEBHOOK_TRACK_NOTIFICATION = False

# Whether to send a webhook notification on every song change
# Can also be enabled via the --webhook-song-changes flag
WEBHOOK_SONG_NOTIFICATION = False

# Whether to send a webhook notification when the user plays a song on loop
# Can also be enabled via the --webhook-loop flag
WEBHOOK_SONG_ON_LOOP_NOTIFICATION = False

# Whether to send a webhook notification when new scrobbles arrive while the user is offline
# Can also be enabled via the --webhook-offline-entries flag
WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION = False

# Whether to send a webhook notification when followers change
# Can also be enabled via the --webhook-followers flag
WEBHOOK_FOLLOWERS_NOTIFICATION = False

# Whether to send a webhook notification when followings change
# Can also be enabled via the --webhook-followings flag
WEBHOOK_FOLLOWINGS_NOTIFICATION = False

# Whether to send a webhook notification when the user's bio or display name changes
# Can also be enabled via the --webhook-profile flag
WEBHOOK_PROFILE_NOTIFICATION = False

# Whether to send a webhook notification on monitoring errors
# Can also be enabled via --webhook-errors or disabled via --no-webhook-error-notify
WEBHOOK_ERROR_NOTIFICATION = True

# Optional request headers for advanced webhook integrations
# Values support the same placeholders as WEBHOOK_TEMPLATE
WEBHOOK_HEADERS = {}

# ----------------------------
# Advanced Webhook Settings
# ----------------------------

# Discord-format webhook request payload template
# Applies only when WEBHOOK_PROVIDER is "discord". The "ntfy" provider needs no template and ignores this
# value: it sends the alert body as a native ntfy message with the subject as its title. Use WEBHOOK_HEADERS
# to add ntfy options such as priority or tags
# Supported placeholders include title, description, version, fields, fields_str, color, timestamp,
# username and avatar_url
WEBHOOK_TEMPLATE = {
    "username": "{username}",
    "avatar_url": "{avatar_url}",
    "allowed_mentions": {
        "parse": [],
    },
    "embeds": [{
        "title": "{title}",
        "description": "{description}",
        "color": "{color}",
        "footer": {
            "text": "Last.fm Monitor v{version}",
        },
        "timestamp": "{timestamp}",
    }],
}

# Optional transformations applied to WEBHOOK_TEMPLATE and WEBHOOK_HEADERS values
# Tuple format: (field_to_target, method_name, *optional_arguments)
#
# Examples:
#   [
#       ("title", "upper"),
#       ("description", "replace", "**", ""),
#       ("description", "strip"),
#   ]
WEBHOOK_TRANSFORMS = []

# Optional ntfy access token for Bearer authentication
# Prefer an environment variable or dotenv file instead of storing this token here
NTFY_ACCESS_TOKEN = ""

# Whether to use compact ntfy alert titles and bodies for smaller screens
# Discord webhook and email content remain unchanged
NTFY_SHORT = False

# How often to check for user activity when the user is considered offline (not playing music); in seconds
# Can also be set using the -c flag
LASTFM_CHECK_INTERVAL = 10  # 10 seconds

# How often to check for user activity when the user is online (currently playing); in seconds
# Can also be set using the -k flag
LASTFM_ACTIVE_CHECK_INTERVAL = 5  # 5 seconds

# Time after which a user is considered inactive, based on the last activity; in seconds
# Can also be set using the -o flag
LASTFM_INACTIVITY_CHECK = 180  # 3 mins

# Whether to auto-play each listened song in your Spotify client
# Can also be set using the -g flag
TRACK_SONGS = False

# Whether to display a real-time progress indicator showing the exact minute and second of the track the user
# is currently listening to
# Can also be set using the -p flag
PROGRESS_INDICATOR = False

# Set to True to retrieve track duration from Spotify instead of Last.fm
# Recommended, as Last.fm often lacks this info or reports inaccurate values
# Uses OAuth app metadata first when configured, then anonymous web-player metadata
# Can also be set with the -r flag
USE_TRACK_DURATION_FROM_SPOTIFY = False

# Whether to hide if duration came from Last.fm or Spotify
# Duration marks are not displayed if the functionality to retrieve track duration from Spotify is disabled
# Can also be set using the -q flag
DO_NOT_SHOW_DURATION_MARKS = False

# Multiplier for detecting short breaks in playback
# The pause is detected after: LASTFM_BREAK_CHECK_MULTIPLIER * LASTFM_ACTIVE_CHECK_INTERVAL seconds of inactivity
# Can be disabled by setting it to 0
# Can also be set using the -m flag
LASTFM_BREAK_CHECK_MULTIPLIER = 4

# How many recent tracks we fetch after start and every time user gets online
RECENT_TRACKS_NUMBER = 10

# How many recently listened songs to display in the inactive notification email
# Set to 0 to disable the recently listened songs list
INACTIVE_EMAIL_RECENT_SONGS_COUNT = 5

# Method used to play the song listened by the tracked user in local Spotify client under macOS
# (i.e. when TRACK_SONGS / -g functionality is enabled)
# Methods:
#       "apple-script" (recommended)
#       "trigger-url"
SPOTIFY_MACOS_PLAYING_METHOD = "apple-script"

# Method used to play the song listened by the tracked user in local Spotify client under Linux OS
# (i.e. when TRACK_SONGS / -g functionality is enabled)
# Methods:
#       "dbus-send" (most common one)
#       "qdbus"
#       "trigger-url"
SPOTIFY_LINUX_PLAYING_METHOD = "dbus-send"

# Method used to play the song listened by the tracked user in local Spotify client under Windows OS
# (if TRACK_SONGS / -g functionality is enabled)
# Methods:
#       "start-uri" (recommended)
#       "spotify-cmd"
#       "trigger-url"
SPOTIFY_WINDOWS_PLAYING_METHOD = "start-uri"

# Number of consecutive plays of the same song considered to be on loop
SONG_ON_LOOP_VALUE = 3

# Threshold for treating a song as skipped, when track duration is unknown (not available from Last.fm/Spotify); in seconds
SKIPPED_SONG_THRESHOLD1 = 35  # considered skipped if played for <= 35 seconds

# Threshold for treating a song as skipped, when track duration is known; fraction
SKIPPED_SONG_THRESHOLD2 = 0.55  # considered skipped if played for <= 55% of its duration

# Thresholds for treating a song as "played longer than track duration":
# Either if played for >= 130% of duration (fraction) or 30+ seconds beyond expected length
LONGER_SONG_THRESHOLD1 = 1.30  # 130% of track duration
LONGER_SONG_THRESHOLD2 = 30  # 30 seconds beyond track duration

# Spotify track ID to play when the user goes offline (used with track_songs feature)
# Leave empty to simply pause
# SP_USER_GOT_OFFLINE_TRACK_ID = "5wCjNjnugSUqGDBrmQhn0e"
SP_USER_GOT_OFFLINE_TRACK_ID = ""

# Delay before pausing the above track after the user goes offline; in seconds
# Set to 0 to keep playing indefinitely until manually paused
SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE = 5  # 5 seconds

# Whether to print extra startup and runtime detail
# Independent of DEBUG_MODE, so enable both to see everything
# Can also be enabled via the --verbose flag, which turns it on regardless of this setting
VERBOSE_MODE = False

# Whether to print timestamped diagnostic detail, including every outbound call,
# each notification delivery attempt and the technical cause of failures
# Independent of VERBOSE_MODE, so enable both to see everything
# Can also be enabled via the --debug flag, which turns it on regardless of this setting
DEBUG_MODE = False

# How often to print a "liveness check" message to the output; in seconds
# Set to 0 to disable
LIVENESS_CHECK_INTERVAL = 86400  # 24 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://ws.audioscrobbler.com/'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# Whether to verify TLS certificates on every connection the tool makes, including Last.fm, Spotify, webhooks and the mail server
# Turn this off only on a network that intercepts TLS with its own certificate authority, since an intercepted
# connection then cannot be told apart from the real service
VERIFY_SSL = True

# Threshold for displaying Last.fm 50x errors - it is to suppress sporadic issues with Last.fm API endpoint
# Adjust the values according to the LASTFM_CHECK_INTERVAL and LASTFM_ACTIVE_CHECK_INTERVAL timers
# If more than 15 Last.fm API related errors in 2 minutes, show an alert
ERROR_500_NUMBER_LIMIT = 15
ERROR_500_TIME_LIMIT = 120  # 2 min

# Threshold for displaying network errors - it is to suppress sporadic issues with internet connectivity
# Adjust the values according to the LASTFM_CHECK_INTERVAL and LASTFM_ACTIVE_CHECK_INTERVAL timers
# If more than 15 network related errors in 2 minutes, show an alert
ERROR_NETWORK_ISSUES_NUMBER_LIMIT = 15
ERROR_NETWORK_ISSUES_TIME_LIMIT = 120  # 2 min

# CSV file to write every scrobble
# Can also be set using the -b flag
CSV_FILE = ""

# Filename with Last.fm tracks/albums to alert on
# Can also be set using the -s flag
MONITOR_LIST_FILE = ""

# Location of the optional dotenv file which can keep secrets
# If not specified it will try to auto-search for .env files
# To disable auto-search, set this to the literal string "none"
# Can also be set using the --env-file flag
DOTENV_FILE = ""

# Base name for the log file. Output will be saved to lastfm_monitor_<username>.log
# Can include a directory path to specify the location, e.g. ~/some_dir/lastfm_monitor
LF_LOGFILE = "lastfm_monitor"

# Whether to disable logging to lastfm_monitor_<username>.log
# Can also be disabled via the -d flag
DISABLE_LOGGING = False

# Controls conversion of separator-only log lines to ASCII:
#   "Auto" - enable on Windows only (default)
#   "On"   - enable on every operating system
#   "Off"  - preserve Unicode separators in logs
ASCII_LOG_SEPARATORS = "Auto"

# Max characters per line when printing to screen to avoid line wrapping
# Does not affect log file output
# Set to 999 to auto-detect terminal width
# Applies only when DISABLE_LOGGING is False
# Can also be set via the --truncate flag
TRUNCATE_CHARS = 0

# Width of horizontal line
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
# Ignored when output is redirected, in debug mode and for commands that print a result and exit
CLEAR_SCREEN = True

# Whether to use coloured output in the terminal (auto-disabled if the terminal
# does not appear to support colours or when output is redirected to a file)
# Can also be disabled via the --no-color flag
COLORED_OUTPUT = True

# Colour theme used for different parts of the output
# Keys are logical names used by the tool, values are colour/style strings
# You can combine multiple attributes with spaces or '+', for example:
#   "bright_cyan bold", "yellow", "red underline", "bright_magenta bold underline", "red bold blink"
# Valid colour names: black, red, green, yellow, blue, magenta, cyan, white,
# and their bright_ variants (bright_red, bright_green, ...).
# The defaults below are what the tool uses while this block stays commented out. Uncomment it to override
# them and keep only the lines you want to change, so the rest keep following the tool's own defaults.
# COLOR_THEME = {
#     # Headings and commands the wizard tells you to run
#     "header": "bright_cyan",
#     "section": "bright_white",
#     # Identity
#     "username": "bright_cyan underline",
#     "id": "bright_magenta",
#     # Listening status values
#     "status_active": "green",
#     "status_inactive": "red",
#     "status_offline": "red",
#     # Music info
#     "artist": "bright_yellow",
#     "track": "bright_yellow",
#     "album": "yellow",
#     "duration": "green",
#     # Activity info
#     "status_change": "yellow",
#     # Misc
#     "timestamp_label": "",
#     "timestamp_value": "cyan",
#     "info": "cyan",
#     "warning": "yellow",
#     "error": "red",
#     "signal": "yellow",
#     "email": "bright_cyan",
#     "webhook": "bright_blue",
#     # Dates
#     "date": "magenta",
#     "date_range": "magenta",
#     # Boolean values
#     "boolean_true": "green",
#     "boolean_false": "red",
#     # Counters and differences
#     "count_up": "green",
#     "count_down": "red",
#     "link": "blue underline",
# }

# Value added/subtracted via signal handlers to adjust inactivity timeout (LASTFM_INACTIVITY_CHECK); in seconds
LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# Whether to show Spotify URL in console and emails
ENABLE_SPOTIFY_URL = True

# Whether to show Last.fm URL in console and emails
ENABLE_LASTFM_URL = True

# Whether to show Last.fm album URL in console and emails
ENABLE_LASTFM_ALBUM_URL = True

# Whether to show Apple Music URL in console and emails
ENABLE_APPLE_MUSIC_URL = True

# Whether to show YouTube Music URL in console and emails
ENABLE_YOUTUBE_MUSIC_URL = True

# Whether to show Amazon Music URL in console and emails
ENABLE_AMAZON_MUSIC_URL = False

# Whether to show Deezer URL in console and emails
ENABLE_DEEZER_URL = False

# Whether to show Tidal URL in console and emails
# Note: Tidal requires users to be logged in to their account in the web browser to use the search functionality
ENABLE_TIDAL_URL = False

# Whether to show Genius lyrics URL in console and emails
ENABLE_GENIUS_LYRICS_URL = True

# Whether to show AZLyrics URL in console and emails
ENABLE_AZLYRICS_URL = False

# Whether to show Tekstowo.pl lyrics URL in console and emails
ENABLE_TEKSTOWO_URL = False

# Whether to show Musixmatch lyrics URL in console and emails
# Note: Musixmatch requires users to be logged in to their account in the web browser to use the search functionality
ENABLE_MUSIXMATCH_URL = False

# Whether to show Lyrics.com lyrics URL in console and emails
ENABLE_LYRICS_COM_URL = False

# Whether to use Last.fm URL in "Last played:" field in HTML email notifications (default: True)
# When True: "Last played:" uses Last.fm URL and the secondary URL field shows Spotify URL
# When False: "Last played:" uses Spotify URL and the secondary URL field shows Last.fm URL (old behavior)
USE_LASTFM_URL_IN_LAST_PLAYED = True

# Whether to track user's followings (friends) changes
# Can also be enabled via the --track-followings flag
TRACK_FOLLOWINGS = False

# Whether to track user's followers changes
# Can also be enabled via the --track-followers flag
TRACK_FOLLOWERS = False

# Whether to track changes in the user's About You bio
# Can also be enabled via the --track-bio flag
TRACK_BIO = False

# Whether to track changes in the user's display name
# Can also be enabled via the --track-display-name flag
TRACK_DISPLAY_NAME = False

# How often to check for friend and profile changes in seconds
# Can also be set using the --friends-check-interval flag
FRIENDS_CHECK_INTERVAL = 900  # 15 minutes

# Whether to send an email when followers change
# Can also be enabled via the --notify-followers flag
FOLLOWERS_NOTIFICATION = False

# Whether to send an email when followings change
# Can also be enabled via the --notify-followings flag
FOLLOWINGS_NOTIFICATION = False

# Whether to send an email when the user's bio or display name changes
# Can also be enabled via the --notify-profile flag
PROFILE_NOTIFICATION = False

# Number of consecutive checks required to confirm a friend or profile change
# to avoid false notifications caused by transient API glitches
# Also used as the threshold for suppressing repeated error messages
# Can also be set using the --friends-change-counter flag
FRIENDS_CHANGE_COUNTER = 3

# Timeout used when confirming transient changes; in seconds
# If this is set higher than FRIENDS_CHECK_INTERVAL, it effectively throttles the checks
# during the confirmation phase
# Can also be set using the --friends-retry-interval flag
FRIENDS_RETRY_INTERVAL = 90
"""

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Default dummy values so linters shut up
# Do not change values below - modify them in the configuration section or config file instead
LASTFM_API_KEY = ""
LASTFM_API_SECRET = ""
LASTFM_USERNAME = ""
SP_CLIENT_ID = ""
SP_CLIENT_SECRET = ""
SP_TOKENS_FILE = ""
SPOTIFY_TOTP_VERSION = 0
SPOTIFY_TOTP_SECRET_CIPHER_BYTES: tuple[int, ...] = ()
SMTP_HOST = ""
SMTP_PORT = 0
SMTP_USER = ""
SMTP_PASSWORD = ""
SMTP_SSL = False
SENDER_EMAIL = ""
RECEIVER_EMAIL = ""
ACTIVE_NOTIFICATION = False
INACTIVE_NOTIFICATION = False
TRACK_NOTIFICATION = False
SONG_NOTIFICATION = False
SONG_ON_LOOP_NOTIFICATION = False
OFFLINE_ENTRIES_NOTIFICATION = False
ERROR_NOTIFICATION = False
WEBHOOK_ENABLED = False
WEBHOOK_PROVIDER = ""
WEBHOOK_URL = ""
WEBHOOK_USERNAME = ""
WEBHOOK_AVATAR_URL = ""
WEBHOOK_ACTIVE_NOTIFICATION = False
WEBHOOK_INACTIVE_NOTIFICATION = False
WEBHOOK_TRACK_NOTIFICATION = False
WEBHOOK_SONG_NOTIFICATION = False
WEBHOOK_SONG_ON_LOOP_NOTIFICATION = False
WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION = False
WEBHOOK_FOLLOWERS_NOTIFICATION = False
WEBHOOK_FOLLOWINGS_NOTIFICATION = False
WEBHOOK_PROFILE_NOTIFICATION = False
WEBHOOK_ERROR_NOTIFICATION = False
WEBHOOK_HEADERS = {}
WEBHOOK_TEMPLATE = {}
WEBHOOK_TRANSFORMS = []
NTFY_ACCESS_TOKEN = ""
NTFY_SHORT = False
LASTFM_CHECK_INTERVAL = 0
LASTFM_ACTIVE_CHECK_INTERVAL = 0
LASTFM_INACTIVITY_CHECK = 0
TRACK_SONGS = False
PROGRESS_INDICATOR = False
USE_TRACK_DURATION_FROM_SPOTIFY = False
DO_NOT_SHOW_DURATION_MARKS = False
LASTFM_BREAK_CHECK_MULTIPLIER = 0
RECENT_TRACKS_NUMBER = 0
INACTIVE_EMAIL_RECENT_SONGS_COUNT = 0
SPOTIFY_MACOS_PLAYING_METHOD = ""
SPOTIFY_LINUX_PLAYING_METHOD = ""
SPOTIFY_WINDOWS_PLAYING_METHOD = ""
SONG_ON_LOOP_VALUE = 0
SKIPPED_SONG_THRESHOLD1 = 0
SKIPPED_SONG_THRESHOLD2 = 0
LONGER_SONG_THRESHOLD1 = 0
LONGER_SONG_THRESHOLD2 = 0
SP_USER_GOT_OFFLINE_TRACK_ID = ""
SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE = 0
LIVENESS_CHECK_INTERVAL = 0
CHECK_INTERNET_URL = ""
CHECK_INTERNET_TIMEOUT = 0
VERIFY_SSL = True
ERROR_500_NUMBER_LIMIT = 0
ERROR_500_TIME_LIMIT = 0
ERROR_NETWORK_ISSUES_NUMBER_LIMIT = 0
ERROR_NETWORK_ISSUES_TIME_LIMIT = 0
CSV_FILE = ""
MONITOR_LIST_FILE = ""
DOTENV_FILE = ""
LF_LOGFILE = ""
DISABLE_LOGGING = False
ASCII_LOG_SEPARATORS = "Auto"
TRUNCATE_CHARS = 0
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
COLORED_OUTPUT = False
COLOR_THEME: dict = {}
LASTFM_INACTIVITY_CHECK_SIGNAL_VALUE = 0
ENABLE_GENIUS_LYRICS_URL = False
ENABLE_AZLYRICS_URL = False
ENABLE_TEKSTOWO_URL = False
ENABLE_MUSIXMATCH_URL = False
ENABLE_LYRICS_COM_URL = False
USE_LASTFM_URL_IN_LAST_PLAYED = False
ENABLE_SPOTIFY_URL = False
ENABLE_LASTFM_URL = False
ENABLE_LASTFM_ALBUM_URL = False
ENABLE_APPLE_MUSIC_URL = False
ENABLE_YOUTUBE_MUSIC_URL = False
ENABLE_AMAZON_MUSIC_URL = False
ENABLE_DEEZER_URL = False
ENABLE_TIDAL_URL = False
TRACK_FOLLOWINGS = False
TRACK_FOLLOWERS = False
TRACK_BIO = False
TRACK_DISPLAY_NAME = False
FRIENDS_CHECK_INTERVAL = 0
FOLLOWERS_NOTIFICATION = False
FOLLOWINGS_NOTIFICATION = False
PROFILE_NOTIFICATION = False
FRIENDS_CHANGE_COUNTER = 0
FRIENDS_RETRY_INTERVAL = 0
VERBOSE_MODE = False
DEBUG_MODE = False
LASTFM_USERNAME_GLOBAL = ""

exec(CONFIG_BLOCK, globals())

# True once monitoring has printed its header, so a verbose notice after that closes its own block
MONITORING_ACTIVE = False

# True while a check has printed verbose lines that still need the timestamp trailer under them
PENDING_NOTICE_BLOCK = False

# The tool's own name, printed where a message has to say which monitor sent it
TOOL_NAME = "lastfm_monitor"

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "lastfm_monitor.conf"

# List of secret keys to load from env/config
SECRET_KEYS = ("LASTFM_API_KEY", "LASTFM_API_SECRET", "SP_CLIENT_ID", "SP_CLIENT_SECRET", "SMTP_PASSWORD", "WEBHOOK_URL", "NTFY_ACCESS_TOKEN")

# Where each secret's effective value came from, recorded as precedence is applied rather than reconstructed afterwards
SECRET_SOURCES = {}

# The sources a secret can resolve from, in the order precedence applies them
SECRET_SOURCE_ORDER = ("config file", "dotenv file", "environment", "command line")

# Secrets whose length the provider issues, so reporting it discloses nothing a pasted support transcript should not carry
FIXED_LENGTH_SECRET_KEYS = ("LASTFM_API_KEY", "LASTFM_API_SECRET", "SP_CLIENT_ID", "SP_CLIENT_SECRET")

# Below this length a configured value is as likely to be an ordinary word as a credential, so replacing it would corrupt the text it appears in
MIN_REDACTABLE_SECRET_LENGTH = 12

# Documentation links, kept as constants so messages, help text and the guides they point at cannot drift apart
PROJECT_URL = "https://github.com/misiektoja/lastfm_monitor"
DOCS_BASE_URL = "https://misiektoja.github.io/lastfm_monitor"
GUIDE_URL = f"{DOCS_BASE_URL}/"
INSTALL_GUIDE_URL = f"{DOCS_BASE_URL}/installation/"
QUICK_START_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/"
LASTFM_API_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#lastfm-api-key-and-shared-secret"
PRIVACY_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#user-privacy-settings"
CONFIG_FILE_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#configuration-file"
SECRETS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#storing-secrets"
SMTP_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#smtp-settings"
WEBHOOK_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#webhook-settings"
TLS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#tls-verification"
USAGE_GUIDE_URL = f"{DOCS_BASE_URL}/usage/#monitoring-mode"
TERMINAL_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#terminal-output"
SPOTIFY_APP_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#optional-spotify-oauth-app-setup"
DOCTOR_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#doctor-preflight"
DIAGNOSTICS_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#debug-output"
INTERVALS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#check-intervals"

# A preflight check waits on the user, so it uses a shorter timeout than a delivery in the monitoring loop
DOCTOR_SMTP_TIMEOUT = 5

# One wording per test message, shared with the sibling monitors. The subject names the tool because the
# message lands beside the real alerts, and the body names the command because it can arrive minutes later
TEST_EMAIL_SUBJECT = f"{TOOL_NAME}: test email"
TEST_EMAIL_BODY = "This test email was sent by --send-test-email. Your SMTP settings work."
TEST_WEBHOOK_TITLE = f"{TOOL_NAME}: test webhook"
TEST_WEBHOOK_BODY = "This test notification was sent by --send-test-webhook. Your webhook settings work."
DOCTOR_TEST_EMAIL_SUBJECT = f"{TOOL_NAME}: doctor test email"
DOCTOR_TEST_EMAIL_BODY = "This test email was sent after approval in --doctor. Your SMTP delivery settings work."
DOCTOR_TEST_WEBHOOK_TITLE = f"{TOOL_NAME}: doctor test webhook"
DOCTOR_TEST_WEBHOOK_BODY = "This test notification was sent after approval in --doctor. Your webhook delivery settings work."

# Check labels shared with the sibling monitors, so one report reads the same as the next
SMTP_READY_CHECK_LABEL = "SMTP connection and login succeeded"
WEBHOOK_READY_CHECK_LABEL = "Webhook URL, headers and alert choices look valid"
EMAIL_UNUSABLE_CHECK_LABEL = "Email alerts are enabled but unusable"

# Pages where the user creates or views the credentials this tool reads
LASTFM_API_REGISTRATION_URL = "https://www.last.fm/api/account/create"
LASTFM_API_ACCOUNTS_URL = "https://www.last.fm/api/accounts"
SPOTIFY_DASHBOARD_URL = "https://developer.spotify.com/dashboard"

# The accepted form of the positional target, shared by the welcome screen and the invalid-target error
LASTFM_TARGET_FORMS = "username exactly as it appears on the user's Last.fm profile page"

# Commands that write a secret to the dotenv file and exit
SECRET_ACTION_FLAGS = ("--set-webhook-url", "--set-lastfm-credentials", "--set-spotify-credentials", "--set-smtp-password")

# Install methods the tool can detect, used to tailor every command it prints
INSTALL_METHOD_PYPI = "pip"
INSTALL_METHOD_SCRIPT = "manual"
INSTALL_METHOD_ENV_VAR = "LASTFM_MONITOR_INSTALL_METHOD"

# Strings removed from track names for generating proper Genius search URLs
re_search_str = r'remaster|extended|original mix|remix|rework|vocal mix|original soundtrack|radio( |-)edit|\(feat\.|( \(.*version\))|( - .*version)'
re_replace_str = r'( - (\d*)( )*remaster$)|( - (\d*)( )*remastered( version)*( \d*)*.*$)|( \((\d*)( )*remaster\)$)|( - (\d+) - remaster$)|( - extended$)|( - extended mix$)|( - (.*); extended mix$)|( - extended version$)|( - (.*) remix$)|( - remix$)|( - remixed by .*$)|( - (.*) rework$)|( - rework$)|( - vocal mix$)|( - original mix$)|( - .*original soundtrack$)|( - .*radio( |-)edit$)|( \(feat\. .*\)$)|( \(\d+.*Remaster.*\)$)|( \(.*Version\))|( - .*version)'

# Default value for Spotify network-related timeouts in functions; in seconds
FUNCTION_TIMEOUT = 5  # 5 seconds

# Reuses Spotipy's in-memory OAuth cache when no cache file is configured
SP_OAUTH_MEMORY_CACHE_HANDLER = None

# Spotify Web API endpoint used for OAuth app track search
SPOTIFY_OAUTH_SEARCH_URL = "https://api.spotify.com/v1/search"

# Caches the anonymous Spotify web-player token until its expiration window
SP_CACHED_WEB_ACCESS_TOKEN = None
SP_WEB_ACCESS_TOKEN_EXPIRES_AT = 0
SP_CACHED_WEB_CLIENT_ID = ""

# Caches persisted-query hashes discovered from the current Spotify web-player bundle
SP_CACHED_TRACK_QUERY_HASH = ""
SP_CACHED_SEARCH_QUERY_HASH = ""

# Spotify web-player token and Pathfinder settings
SPOTIFY_TOKEN_URL = "https://open.spotify.com/api/token"
SPOTIFY_SERVER_TIME_URL = "https://open.spotify.com/"
SPOTIFY_WEB_PLAYER_URL = "https://open.spotify.com/"
SPOTIFY_WEB_QUERY_URL = "https://api-partner.spotify.com/pathfinder/v2/query"
SPOTIFY_WEB_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
SPOTIFY_WEB_TOKEN_EXPIRY_WINDOW = 60

# Seconds rather than checks, because an active user is polled on a different interval than an inactive one
LIVENESS_REMINDER_SECONDS = LIVENESS_CHECK_INTERVAL if LIVENESS_CHECK_INTERVAL > 0 else 0

stdout_bck = None
csvfieldnames = ['Date', 'Artist', 'Track', 'Album']

CLI_CONFIG_PATH = None

# Set once when --config-file selects the 'none' sentinel, so no caller falls back to the search path
CONFIG_DISCOVERY_DISABLED = False

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"

STARTUP_BANNER = r"""
 .---------------.    _              _      __
|    _______     |   | |    __ _ ___| |_   / _|_ __ ___
|   / _____ \    |   | |   / _` / __| __| | |_| '_ ` _ \
|  | |  o  | |   |   | |__| (_| \__ \ |_ _|  _| | | | | |
|   \_______/    |   |_____\__,_|___/\__(_)_| |_| |_| |_|
 '---------------'
                      __  __             _ _
                     |  \/  | ___  _ __ (_) |_ ___  _ __
                     | |\/| |/ _ \| '_ \| | __/ _ \| '__|
                     | |  | | (_) | | | | | || (_) | |
                     |_|  |_|\___/|_| |_|_|\__\___/|_|"""


import sys

# The lowest Python this tool supports, kept as one constant so the runtime gate, the documentation
# and the packaging metadata cannot drift apart
MINIMUM_PYTHON_VERSION = (3, 9)
MINIMUM_PYTHON_VERSION_TEXT = ".".join(str(part) for part in MINIMUM_PYTHON_VERSION)

if sys.version_info < MINIMUM_PYTHON_VERSION:
    print(f"* Error: Python version {MINIMUM_PYTHON_VERSION_TEXT} or higher required !")
    print(f"To fix: Upgrade to Python {MINIMUM_PYTHON_VERSION_TEXT} or newer, since this is Python {sys.version.split()[0]}")
    print(f"Guide: {INSTALL_GUIDE_URL}")
    sys.exit(1)

import time
import textwrap
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
import ast
import csv
import importlib.util
try:
    import pylast
except ModuleNotFoundError:
    raise SystemExit(f"Error: Couldn't find the pyLast library !\n\nTo install it, run:\n    pip install pylast\n\nOnce installed, re-run this tool.\n\nGuide: {INSTALL_GUIDE_URL}")
from urllib.parse import quote_plus, quote, unquote, urljoin, urlsplit
try:
    from colorama import init as colorama_init  # type: ignore[import]
except ImportError:
    colorama_init = None
import subprocess
import platform
import re
import ipaddress
import getpass
import shlex
import tempfile
from itertools import tee, islice, chain
from collections import namedtuple
from html import escape
import contextlib
import functools
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, cast
import base64
import hashlib
import hmac
from email.utils import parsedate_to_datetime
import pyotp


SPOTIFY_SESSION = req.Session()
WEBHOOK_SESSION = req.Session()

from requests.adapters import HTTPAdapter
import urllib3
from urllib3.util.retry import Retry

# Cap server-provided Retry-After to avoid long blocking sleeps on 429 responses
SPOTIFY_MAX_RETRY_AFTER_SECONDS = 60
WEBHOOK_MAX_ATTEMPTS = 2
WEBHOOK_MAX_RETRY_AFTER_SECONDS = 5.0
WEBHOOK_FALLBACK_RETRY_SECONDS = 1.0
WEBHOOK_TIMEOUT_SECONDS = 10
WEBHOOK_EMBED_TITLE_LIMIT = 256
WEBHOOK_EMBED_DESCRIPTION_LIMIT = 4096
NTFY_MESSAGE_LIMIT_BYTES = 4000
NTFY_TRUNCATION_SUFFIX = "\n\n[Notification truncated to fit ntfy's 4 KB message limit]"


class SpotifyCappedRetry(Retry):
    def get_retry_after(self, response):
        retry_after = super().get_retry_after(response)
        if retry_after is None:
            return None
        return min(retry_after, SPOTIFY_MAX_RETRY_AFTER_SECONDS)


# Every Spotify request on this session is an idempotent read or token fetch, so retry transient failures
# (including the web-player GraphQL POST) with capped backoff
spotify_retry = SpotifyCappedRetry(
    total=5,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD", "OPTIONS", "POST"],
    raise_on_status=False,
    respect_retry_after_header=True
)

spotify_adapter = HTTPAdapter(max_retries=spotify_retry, pool_connections=100, pool_maxsize=100)
SPOTIFY_SESSION.mount("https://", spotify_adapter)
SPOTIFY_SESSION.mount("http://", spotify_adapter)

# Keep webhook delivery on its own bounded retry path
webhook_adapter = HTTPAdapter(max_retries=Retry(total=0))
WEBHOOK_SESSION.mount("https://", webhook_adapter)
WEBHOOK_SESSION.mount("http://", webhook_adapter)


# Reports whether separator-only log lines should use ASCII on this system
def ascii_log_separators_enabled():
    mode = str(ASCII_LOG_SEPARATORS).strip().lower()
    if mode not in {"auto", "on", "off"}:
        raise ValueError("ASCII_LOG_SEPARATORS must be 'Auto', 'On' or 'Off'")
    return mode == "on" or (mode == "auto" and platform.system() == "Windows")


# Converts Unicode-only horizontal separator lines to ASCII when configured
def normalize_log_separators(message):
    if not ascii_log_separators_enabled():
        return message
    return re.sub(r"(?m)^─+$", lambda match: match.group(0).replace("─", "-"), message)


# Matches the escape sequences a terminal acts on: CSI, OSC and the two-character forms
ANSI_ESCAPE_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)?|[@-Z\\-_])")

# The only escape sequence this tool emits is an SGR colour/style change, so it is the only one worth keeping
SGR_SEQUENCE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Drops every remaining control character except tab and newline. A carriage return would let Last.fm-supplied
# text overwrite an already printed line, and the doctor progress line that uses one writes to the terminal directly
TERMINAL_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


# Removes terminal control sequences, since track, artist and profile text arrives from Last.fm rather than the tool
# An SGR colour change is kept, because this tool's own colours re-enter the same writer and cannot be told apart
# here from an upstream one. A bare SGR sequence only changes how the rest of the line looks, so it stays inert
def sanitize_terminal_text(message):
    if not isinstance(message, str) or not message:
        return message
    parts = []
    position = 0
    for match in SGR_SEQUENCE_RE.finditer(message):
        parts.append(TERMINAL_CONTROL_RE.sub("", ANSI_ESCAPE_RE.sub("", message[position:match.start()])))
        parts.append(match.group(0))
        position = match.end()
    parts.append(TERMINAL_CONTROL_RE.sub("", ANSI_ESCAPE_RE.sub("", message[position:])))
    return "".join(parts)


# Internal flag and style map for colour handling
COLOR_ENABLED = False
_COLOR_STYLES: dict = {}

# Default built-in colour theme. Values can be overridden via COLOR_THEME in config
DEFAULT_COLOR_THEME = {
    # Headings and commands the wizard tells you to run
    "header": "bright_cyan",
    "section": "bright_white",
    # Identity
    "username": "bright_cyan underline",
    "id": "bright_magenta",
    # Listening status values
    "status_active": "green",
    "status_inactive": "red",
    "status_offline": "red",
    # Music info
    "artist": "bright_yellow",
    "track": "bright_yellow",
    "album": "yellow",
    "duration": "green",
    # Activity info
    "status_change": "yellow",
    # Misc
    "timestamp_label": "",
    "timestamp_value": "cyan",
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "signal": "yellow",
    "email": "bright_cyan",
    "webhook": "bright_blue",
    # Dates
    "date": "magenta",
    "date_range": "magenta",
    # Boolean values
    "boolean_true": "green",
    "boolean_false": "red",
    # Counters and differences
    "count_up": "green",
    "count_down": "red",
    "link": "blue underline",
}

# Styles that can paint a whole line, and the value styles a painted line can enclose. A value drawn in its
# block's own colour would disappear inside it, so the two sets are kept disjoint. Warnings and signals are
# not on the block list: both were yellow, which is the album colour, so they mark their own opening words
# instead of painting the line and the values inside keep carrying the meaning
BLOCK_STYLE_PARTS = ("error", "email", "webhook", "info")
NAME_STYLE_PARTS = ("username", "id", "artist", "track", "album", "link")

ANSI_RESET = "\033[0m"

# Mapping of style names to ANSI SGR codes
_STYLE_CODES = {
    "bold": "1",
    "dim": "2",
    "underline": "4",
    "blink": "5",
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}

# Output labels whose value is coloured with one theme style, the longer label first so a prefix cannot win
_LABEL_STYLES = (
    (("Last.fm user:", "Target:"), "username"),
    (("Last track duration:", "Duration:"), "duration"),
    (("Last track:", "Track:"), "track"),
    (("Last album:", "Album:"), "album"),
)

# Pre-compiled regexes used for line-level colourisation
_FROM_TO_COUNT_RE = re.compile(r"(from\s+)(\d+)(\s+to\s+)(\d+)")
_DIFF_COUNT_UP_RE = re.compile(r"(\(\+\d+\))")
_DIFF_COUNT_DOWN_RE = re.compile(r"(\(-\d+\))")
# The monitored account named inside a sentence. A Last.fm handle carries no spaces, so the name ends at the
# first one, and the prose forms 'the user is active' or 'user to monitor' keep their next word plain
_USER_TAG_RE = re.compile(r"((?:Last\.fm user|for user|by user|of user|Monitoring user|listened by))([\t ]+)([\w.-]{2,})")

# A labelled 'user' field names its value directly, so the key=value diagnostic field 'user=john' tags any value
_USER_FIELD_RE = re.compile(r"(\buser)(=)([\w.-]+)")

# A key=value diagnostic field whose key ends in '_id' carries a machine identifier, such as a Spotify track ID
_ID_FIELD_RE = re.compile(r"(\b[a-z][a-z_]*_id)(=)([\w.:-]+)")

# The token right before a quoted value decides what it is. Only these say the value is an account name, and
# every other quoted value this tool prints is a path, a package or a menu answer, so it stays plain
_QUOTED_USERNAME_CONTEXT_RE = re.compile(r"\buser\s+$|\blistened by\s+$|\btracks of\s+$", re.IGNORECASE)
_DURATION_RE = re.compile(r"~?\b[0-9]{1,20}[ \t]{1,20}(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b", re.IGNORECASE)
_LONG_DATE_RE = re.compile(r"\b(?:\w{3}\s+)?\d{1,2}\s+\w{3}(?:\s+\d{2,4})?[\s,]*\d{2}:\d{2}(:\d{2})?(\s*[AP]M)?\b", re.IGNORECASE)
_TIME_ONLY_RE = re.compile(r"(?<![\w:])(~?(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?:\s*[AP]M)?)(?![\w:])", re.IGNORECASE)
_SHORT_RANGE_DATE_RE = re.compile(r"\(\w{3}\s+\d{1,2}\s+\w{3}\s+\d{2}:\d{2}(\s*[AP]M)?\s*-\s*\d{2}:\d{2}(\s*[AP]M)?\)", re.IGNORECASE)
_DATE_RANGE_RE = re.compile(r"\b\w{3}\s+\d{1,2}\s+\w{3}\s+\d{2}:\d{2}(\s*[AP]M)?\s*-\s*\d{2}:\d{2}(\s*[AP]M)?\b", re.IGNORECASE)
_HOUR_RANGE_RE = re.compile(r"\b\d{2}:\d{2}(\s*[AP]M)?\s*-\s*\d{2}:\d{2}(\s*[AP]M)?\b", re.IGNORECASE)
# Sentence punctuation, a closing bracket or a closing quote right after a link is not part of it
_URL_RE = re.compile(r"(https?://[^\s\]]+?)(?=[.,;:!?'\")>]*(?:[\s\]]|$))")
_PERCENTAGE_RE = re.compile(r"\(\d{1,3}%")
_BOOLEAN_TRUE_RE = re.compile(r"\bTrue\b|\bEnabled\b")
_BOOLEAN_FALSE_RE = re.compile(r"\bFalse\b|\bDisabled\b")
_NOTIFICATION_SUMMARY_STATE_RE = re.compile(r"^(\* Notifications \((?:email|webhook)\):\s+)(On|Off)(.*)$")
# The opening word of a warning line, marked on its own so the rest of the line keeps its own value colours
_WARNING_LABEL_RE = re.compile(r"^\*+\s*(Warning:|Caution:)")
# The signal a handler reports, which is the one value on the line worth marking
_SIGNAL_NAME_RE = re.compile(r"(?<=^\* Signal )(\w+)(?= received$)")
# Words that report a problem. The same word used as a key in a 'key=value' diagnostic detail names a setting
# such as 'timeout=15' or a counter such as 'failures=3', so it leaves its line unpainted
_ERROR_KEYWORD_RE = re.compile(r"\b(?:failures?|failed|forbidden|timeout)\b(?!\s*=)")
# A debug trace line records what the tool tried, including attempts that fail and are then handled, so it keeps
# its own colours instead of being painted as the failure it reports
_DEBUG_LINE_RE = re.compile(r"^\[debug \d{2}:\d{2}:\d{2}\]")
# Doctor status markers, coloured with the same theme parts the sibling tools use for them
_DOCTOR_MARK_RE = re.compile(r"^\[(PASS|WARN|FAIL|SKIP)\]")
# Quoted names such as track and album titles. At least one word character is required so a run of punctuation
# between two apostrophes is not read as a name. The closing quote has to be followed by whitespace, punctuation
# or the end of the line, so a title's own apostrophe does not end it early: "Tom Clancy's Rainbow Six Siege"
_QUOTED_CONTENT_RE = re.compile(r"(')([^\n]*?\w[^\n]*?)(')(?=[\s.,;:!?)\]]|$)")

# Quoted values shaped like a file name or a filesystem path stay plain, since a log or state destination is
# not content. Track and album titles routinely contain slashes and dots, so only these two shapes are excluded
_QUOTED_FILE_LIKE_RE = re.compile(r"^[~.]?[\\/]|^[A-Za-z]:[\\/]|\.[A-Za-z0-9]{1,8}$")

# A quoted '<name>' inside a printed command is the placeholder the reader has to replace, not a track title
_QUOTED_PLACEHOLDER_RE = re.compile(r"^<[^<>]*>$")

# A quoted command-line option is an instruction to retype, not a name
_QUOTED_OPTION_RE = re.compile(r"^-")

# A quoted piece of a URL, such as the '?code=' a prompt points at. Only a leading '?' or '&' counts, so a title
# may end in a question mark and a title such as 'Peaches & Cream' is still a name
_QUOTED_URL_PART_RE = re.compile(r"^[?&]|://")

# Follower and following listing rows, for example "- someuser [ https://www.last.fm/user/someuser ]"
_LIST_ITEM_NAME_RE = re.compile(r"^\s*-\s+([\w.-]+)(\s+\[)")
_PLAYBACK_STOPPED_RE = re.compile(r"\b(SKIPPED|PAUSED)\b")
_PLAYBACK_STARTED_RE = re.compile(r"\b(RESUMED|LOOP)\b")
_PLAYBACK_CHANGED_RE = re.compile(r"\b(CONT)\b")
_ACTIVE_WORD_RE = re.compile(r"\b(ACTIVE|PRIVATE MODE)\b")
_INACTIVE_WORD_RE = re.compile(r"\b(INACTIVE)\b")
_OFFLINE_WORD_RE = re.compile(r"\b(OFFLINE)\b")


# Builds an ANSI escape sequence from a style description string
def _build_ansi_sequence(style_str):
    if not style_str:
        return ""
    codes = [_STYLE_CODES[part] for part in re.split(r"[+ ]+", style_str.strip().lower()) if part in _STYLE_CODES]
    if not codes:
        return ""
    return f"\033[{';'.join(codes)}m"


# Detects whether the given output stream likely supports ANSI colours
def _stream_supports_color(stream):
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if os.getenv("NO_COLOR"):
        return False
    # On Windows with colorama, skip the TERM check since colorama handles the ANSI translation itself
    if not (colorama_init and platform.system() == "Windows"):
        if os.getenv("TERM", "").lower() in ("", "dumb", "unknown"):
            return False
    # A piped stdin means the output is likely being captured, so colour codes would land in a file
    if hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
        return False
    return True


# Initializes colour handling from the configured setting and the terminal's capabilities
def init_color_output(stream):
    global COLOR_ENABLED, _COLOR_STYLES

    # colorama is started first on Windows, since it can turn on the ANSI support the isatty check then sees
    if colorama_init and platform.system() == "Windows":
        try:
            colorama_init(autoreset=False)
        except Exception as e:
            debug_print("Colorama initialisation", outcome="failed", error=f"{type(e).__name__}: {e}")

    COLOR_ENABLED = bool(globals().get("COLORED_OUTPUT", False)) and _stream_supports_color(stream)

    if not COLOR_ENABLED:
        _COLOR_STYLES = {}
        return

    user_theme = globals().get("COLOR_THEME") if isinstance(globals().get("COLOR_THEME"), dict) else {}
    theme = {**DEFAULT_COLOR_THEME, **(user_theme or {})}
    _COLOR_STYLES = {name: sequence for name, sequence in ((name, _build_ansi_sequence(style)) for name, style in theme.items()) if sequence}


# Applies a configured colour style, named by logical part, to the given text
def colorize(part, text):
    if not COLOR_ENABLED:
        return text
    start = _COLOR_STYLES.get(part)
    if not start:
        return text
    return f"{start}{text}{ANSI_RESET}"


# Splits a recognized output label from its value without applying a backtracking expression
def _split_output_label(value, labels):
    body = value.rstrip("\n")
    cursor = len(body) - len(body.lstrip())
    if body[cursor:cursor + 1] == "*":
        cursor += 1
        cursor += len(body[cursor:]) - len(body[cursor:].lstrip())
    for label in labels:
        if not body.startswith(label, cursor):
            continue
        value_start = cursor + len(label)
        value_start += len(body[value_start:]) - len(body[value_start:].lstrip())
        if value_start == cursor + len(label):
            return None
        return body[:value_start], body[value_start:]
    return None


# Applies a whole-line style while preserving the highlights already inside the line
def _apply_style_nested(line, style_name):
    start_style = _COLOR_STYLES.get(style_name)
    if not start_style:
        return line
    # An internal reset returns to the block style instead of to plain text, so the rest of the line keeps it
    line = f"{start_style}{line}{ANSI_RESET}"
    line = line.replace(ANSI_RESET, f"{ANSI_RESET}{start_style}")
    if line.endswith(f"{ANSI_RESET}{start_style}"):
        line = line[:-len(start_style)]
    return line


# Applies one substitution only to the parts of a line that are not already inside a colour span, so a later
# rule cannot reclaim text an earlier rule has already coloured
def _sub_outside_color(pattern, replacement, line):
    if ANSI_RESET not in line:
        return pattern.sub(replacement, line)
    parts = []
    position = 0
    inside = False
    for match in SGR_SEQUENCE_RE.finditer(line):
        segment = line[position:match.start()]
        parts.append(segment if inside else pattern.sub(replacement, segment))
        parts.append(match.group(0))
        inside = match.group(0) != ANSI_RESET
        position = match.end()
    trailing = line[position:]
    parts.append(trailing if inside else pattern.sub(replacement, trailing))
    return "".join(parts)


# Colours one quoted account name, leaving the value alone when its shape or the token before it says otherwise
def _colorize_quoted_name(match):
    name = match.group(2)
    if not _QUOTED_USERNAME_CONTEXT_RE.search(match.string[:match.start()]):
        return match.group(0)
    if _QUOTED_FILE_LIKE_RE.search(name) or _QUOTED_PLACEHOLDER_RE.match(name) or _QUOTED_OPTION_RE.match(name) or _QUOTED_URL_PART_RE.search(name):
        return match.group(0)
    return f"{match.group(1)}{colorize('username', name)}{match.group(3)}"


# Applies the colour rules to a single output line
def _colorize_line(line):
    lowered = line.lower()

    # Notification summary rows carry their own On/Off state word
    notification_match = _NOTIFICATION_SUMMARY_STATE_RE.match(line)
    if notification_match:
        prefix, state, suffix = notification_match.groups()
        return f"{prefix}{colorize('boolean_true' if state == 'On' else 'boolean_false', state)}{suffix}"

    # Doctor status markers keep the rest of their line plain so long labels stay readable
    doctor_match = _DOCTOR_MARK_RE.match(line)
    if doctor_match:
        return colorize(DOCTOR_MARK_STYLES[doctor_match.group(1)], doctor_match.group(0)) + line[doctor_match.end():]

    # Timestamp lines get a plain label and a coloured value
    labeled_value = _split_output_label(line, ("Timestamp:", "Liveness check, timestamp:"))
    if labeled_value:
        label, rest = labeled_value
        return f"{colorize('timestamp_label', label)}{colorize('timestamp_value', rest)}" + ("\n" if line.endswith("\n") else "")

    # Any '<something> URL:' row is a link, checked before the label table so 'Last.fm album URL:' is not an album
    if _split_output_label(line, ("URL:",)) or " URL:" in line:
        return _sub_outside_color(_URL_RE, lambda mo: colorize("link", mo.group(0)), line)

    # Labelled music rows keep their label plain and colour only the value
    for labels, style_name in _LABEL_STYLES:
        labeled_value = _split_output_label(line, labels)
        if not labeled_value:
            continue
        label, rest = labeled_value
        return f"{label}{colorize(style_name, rest)}" + ("\n" if line.endswith("\n") else "")

    # A follower or following listing row names one account followed by its profile link
    line = _sub_outside_color(_LIST_ITEM_NAME_RE, lambda mo: f"{mo.group(0)[:mo.start(1) - mo.start(0)]}{colorize('username', mo.group(1))}{mo.group(2)}", line)

    # Highlight the monitored account named inside a sentence, and the identifiers in a diagnostic field
    line = _sub_outside_color(_USER_TAG_RE, lambda mo: f"{mo.group(1)}{mo.group(2)}{colorize('username', mo.group(3))}", line)
    line = _sub_outside_color(_USER_FIELD_RE, lambda mo: f"{mo.group(1)}{mo.group(2)}{colorize('username', mo.group(3))}", line)
    line = _sub_outside_color(_ID_FIELD_RE, lambda mo: f"{mo.group(1)}{mo.group(2)}{colorize('id', mo.group(3))}", line)

    # Highlight counters and their differences
    line = _sub_outside_color(_FROM_TO_COUNT_RE, lambda mo: f"{mo.group(1)}{colorize('count_up' if int(mo.group(4)) >= int(mo.group(2)) else 'count_down', mo.group(2))}{mo.group(3)}{colorize('count_up' if int(mo.group(4)) >= int(mo.group(2)) else 'count_down', mo.group(4))}", line)
    line = _sub_outside_color(_DIFF_COUNT_UP_RE, lambda mo: colorize("count_up", mo.group(0)), line)
    line = _sub_outside_color(_DIFF_COUNT_DOWN_RE, lambda mo: colorize("count_down", mo.group(0)), line)

    # Highlight durations and listening percentages
    line = _sub_outside_color(_DURATION_RE, lambda mo: colorize("duration", mo.group(0)), line)
    line = _sub_outside_color(_PERCENTAGE_RE, lambda mo: f"({colorize('count_up', mo.group(0)[1:])}", line)

    # Highlight date ranges before single dates so a range is not split into two dates
    line = _sub_outside_color(_SHORT_RANGE_DATE_RE, lambda mo: colorize("date_range", mo.group(0)), line)
    line = _sub_outside_color(_DATE_RANGE_RE, lambda mo: colorize("date_range", mo.group(0)), line)
    line = _sub_outside_color(_HOUR_RANGE_RE, lambda mo: colorize("date_range", mo.group(0)), line)
    line = _sub_outside_color(_LONG_DATE_RE, lambda mo: colorize("date", mo.group(0)), line)
    line = _sub_outside_color(_TIME_ONLY_RE, lambda mo: colorize("date", mo.group(0)), line)

    # Highlight links
    line = _sub_outside_color(_URL_RE, lambda mo: colorize("link", mo.group(0)), line)

    # Highlight a quoted account name. A line that is only a quoted string is a free-form description, so it
    # stays plain instead of being read as a name
    if not line.lstrip().startswith("'"):
        line = _sub_outside_color(_QUOTED_CONTENT_RE, _colorize_quoted_name, line)

    # Highlight boolean values
    line = _sub_outside_color(_BOOLEAN_TRUE_RE, lambda mo: colorize("boolean_true", mo.group(0)), line)
    line = _sub_outside_color(_BOOLEAN_FALSE_RE, lambda mo: colorize("boolean_false", mo.group(0)), line)

    # Mark the opening word of a warning and the name of a reported signal, rather than painting the whole line
    line = _sub_outside_color(_WARNING_LABEL_RE, lambda mo: mo.group(0)[:mo.start(1) - mo.start(0)] + colorize("warning", mo.group(1)), line)
    line = _sub_outside_color(_SIGNAL_NAME_RE, lambda mo: colorize("signal", mo.group(0)), line)

    # Highlight playback and presence keywords
    line = _sub_outside_color(_PLAYBACK_STOPPED_RE, lambda mo: colorize("status_inactive", mo.group(0)), line)
    line = _sub_outside_color(_PLAYBACK_STARTED_RE, lambda mo: colorize("status_active", mo.group(0)), line)
    line = _sub_outside_color(_PLAYBACK_CHANGED_RE, lambda mo: colorize("status_change", mo.group(0)), line)
    line = _sub_outside_color(_ACTIVE_WORD_RE, lambda mo: colorize("status_active", mo.group(0)), line)
    line = _sub_outside_color(_INACTIVE_WORD_RE, lambda mo: colorize("status_inactive", mo.group(0)), line)
    line = _sub_outside_color(_OFFLINE_WORD_RE, lambda mo: colorize("status_offline", mo.group(0)), line)

    # Whole-line highlighting, applied last so the colours added above survive the nesting logic
    is_debug_line = bool(_DEBUG_LINE_RE.match(lowered))
    is_error = not is_debug_line and (bool(_ERROR_KEYWORD_RE.search(lowered)) or "critical:" in lowered or ("* error" in lowered and "[errors =" not in lowered))

    if lowered.startswith("to fix:"):
        line = _apply_style_nested(line, "info")
    elif is_error:
        line = _apply_style_nested(line, "error")
    elif "sending email" in lowered:
        line = _apply_style_nested(line, "email")
    elif "sending webhook" in lowered:
        line = _apply_style_nested(line, "webhook")

    return line


# Applies colourisation to multi-line text, preserving line breaks
def apply_color_to_text(text):
    if not COLOR_ENABLED or not isinstance(text, str):
        return text
    parts = []
    for chunk in text.splitlines(keepends=True):
        if chunk.endswith(("\n", "\r")):
            stripped = chunk.rstrip("\r\n")
            parts.append(_colorize_line(stripped) + chunk[len(stripped):])
        else:
            parts.append(_colorize_line(chunk))
    return "".join(parts)


# Truncates each line to a display width, expanding tabs and counting double-width characters correctly
def truncate_string_per_line(message, truncate_width, tabsize=8):
    try:
        from wcwidth import wcwidth
    except ImportError:
        return message
    truncated_lines = []
    for line in message.split("\n"):
        expanded_line = line.expandtabs(tabsize)
        current_width = 0
        truncated = []
        position = 0
        while position < len(expanded_line):
            # A colour sequence is copied through free of charge, so styling never eats into the visible width
            escape = SGR_SEQUENCE_RE.match(expanded_line, position)
            if escape:
                truncated.append(escape.group(0))
                position = escape.end()
                continue
            char = expanded_line[position]
            char_width = wcwidth(char)
            if char_width is None or char_width < 0:
                char_width = 0
            if current_width + char_width > truncate_width:
                break
            truncated.append(char)
            current_width += char_width
            position += 1
        truncated_lines.append("".join(truncated))
    return "\n".join(truncated_lines)


# Resolves CLI and configured truncation settings while expanding the terminal-width sentinel
def resolve_truncate_chars(cli_value, configured_value, logging_disabled):
    truncate_chars = configured_value if cli_value is None else cli_value
    if logging_disabled:
        return 0
    if truncate_chars == 999:
        terminal_size = shutil.get_terminal_size()
        print(f"The detected terminal screen width is: {terminal_size.columns} characters\n")
        return terminal_size.columns
    return truncate_chars


# Returns the text the terminal should be given, shortened to the configured width when one is set
def for_terminal(message):
    return truncate_string_per_line(message, TRUNCATE_CHARS) if TRUNCATE_CHARS else message


# Wraps stdout while logging is disabled, so output is sanitized on the path that keeps no log file
class TerminalStream(object):
    # Stores the wrapped terminal stream
    def __init__(self, stream):
        self.terminal = stream

    # Writes one sanitized and coloured message to the terminal
    def write(self, message):
        self.terminal.write(apply_color_to_text(for_terminal(sanitize_terminal_text(sanitize_error_text(message)))))
        self.terminal.flush()

    # Writes one terminal-only message, which is every message this stream receives
    def terminal_only(self, message):
        self.write(message)

    # Discards log-only output while logging is disabled
    def log_only(self, message):
        return

    # Flushes the wrapped terminal
    def flush(self):
        self.terminal.flush()

    # Forwards other stream attributes, so isatty and encoding still answer for the real terminal
    def __getattr__(self, name):
        return getattr(self.terminal, name)


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = unwrap_terminal_stream(sys.stdout)
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        safe_message = sanitize_terminal_text(sanitize_error_text(message))
        self.terminal.write(apply_color_to_text(for_terminal(safe_message)))
        # Colour codes are stripped so the log file stays plain text whatever the terminal was shown
        self.logfile.write(normalize_log_separators(ANSI_ESCAPE_RE.sub("", safe_message).expandtabs(8)))
        self.terminal.flush()
        self.logfile.flush()

    # Writes one message only to the terminal, so a line that orients a reader at a screen stays out of the log
    def terminal_only(self, message):
        self.terminal.write(apply_color_to_text(for_terminal(sanitize_terminal_text(sanitize_error_text(message)))))
        self.terminal.flush()

    # Writes one message only to the log, so the file keeps the full view whichever one the terminal was shown
    def log_only(self, message):
        self.logfile.write(normalize_log_separators(ANSI_ESCAPE_RE.sub("", sanitize_terminal_text(sanitize_error_text(message))).expandtabs(8)))
        self.logfile.flush()

    def flush(self):
        pass


# Returns the real terminal underneath any stream the tool installed over stdout
def unwrap_terminal_stream(stream):
    while isinstance(stream, (Logger, TerminalStream)):
        stream = stream.terminal
    return stream


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)


# Restores Python's own Ctrl+C behavior for the length of one prompt, so an interrupt there raises
# KeyboardInterrupt for the caller to answer instead of reaching the handler that terminates the tool
@contextlib.contextmanager
def default_interrupt_handling():
    try:
        previous_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.default_int_handler)
    except (ValueError, OSError):
        # Handlers can only be replaced from the main thread, which is where every prompt runs
        yield
        return
    try:
        yield
    finally:
        try:
            signal.signal(signal.SIGINT, previous_handler)
        except (ValueError, OSError):
            pass


# Reads one visible answer with Python's default Ctrl+C behavior
def read_interactively(reader, *args, **kwargs):
    with default_interrupt_handling():
        return reader(*args, **kwargs)


# Reads one hidden answer with Python's default Ctrl+C behavior. Kept apart from the visible reader so a
# secret typed here is never confused with an ordinary answer that is later printed back to the user
def read_secret_interactively(reader, *args, **kwargs):
    with default_interrupt_handling():
        return reader(*args, **kwargs)


# Silences debug output while a raw secret is entered or validated, then restores the previous mode
@contextlib.contextmanager
def debug_output_suppressed():
    global DEBUG_MODE
    previous_debug_mode = DEBUG_MODE
    DEBUG_MODE = False
    try:
        yield
    finally:
        DEBUG_MODE = previous_debug_mode


# Silences debug output for the whole of a function that handles a raw secret
def suppresses_debug_output(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with debug_output_suppressed():
            return func(*args, **kwargs)
    return wrapper


# The last connectivity failure, so a quiet caller can classify it instead of the check printing it
LAST_CONNECTIVITY_ERROR = None


# Checks internet connectivity
def check_internet(url=None, timeout=None, quiet=False):
    # Resolved here rather than as argument defaults, which would freeze the shipped values before the config file is read
    selected_url = CHECK_INTERNET_URL if url is None else url
    selected_timeout = CHECK_INTERNET_TIMEOUT if timeout is None else timeout
    try:
        pylast_version = getattr(pylast, '__version__', 'unknown')
        headers = {'User-Agent': f'pylast/{pylast_version}'}
        response = req.get(selected_url, timeout=selected_timeout, headers=headers, verify=VERIFY_SSL)
        debug_print("Connectivity check", url=selected_url, timeout=f"{selected_timeout}s", status=response.status_code, outcome="OK")
        return True
    except req.RequestException as e:
        # Quiet callers render the failure themselves, which doctor needs so nothing lands on its progress line
        global LAST_CONNECTIVITY_ERROR
        LAST_CONNECTIVITY_ERROR = e
        debug_print("Connectivity check", url=selected_url, timeout=f"{selected_timeout}s", outcome="failed", error=f"{type(e).__name__}: {e}")
        if not quiet:
            print_recovery_error(e, context="connectivity")
        return False


# Clears the terminal screen
def clear_screen(enabled=True):
    if not enabled:
        return
    # Don't clear screen if stdout is redirected (not a TTY)
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return
    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        print("* Cannot clear the screen contents")


# Commands that print a one-shot result and exit, so the screen keeps whatever is already on it
KEEP_HISTORY_FLAGS = (*SECRET_ACTION_FLAGS, "--doctor", "--send-test-email", "--send-test-webhook", "--help", "-h")


# Returns True when the running command is a one-shot whose output has to stay scrollable
def keep_terminal_history():
    return any(flag in sys.argv for flag in KEEP_HISTORY_FLAGS)


# Prints the ASCII startup banner with a separately aligned version
def print_startup_banner():
    print("\n".join(colorize("header", line) if line else line for line in STARTUP_BANNER.splitlines()))
    print(colorize("info", f"{'':21}v{VERSION}") + "\n")


# Converts absolute value of seconds to human readable format
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


# Calculates time span between two timestamps, accepts timestamp integers, floats and datetime objects
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


# Sends email notification
# Opens one authenticated SMTP session, shared so a preflight check fails where a real send would
def smtp_connect_and_login(use_ssl, smtp_timeout=15):
    smtp_object = smtplib.SMTP(SMTP_HOST, int(SMTP_PORT), timeout=smtp_timeout)
    try:
        if use_ssl:
            smtp_object.starttls(context=tls_context())
        smtp_object.login(SMTP_USER, SMTP_PASSWORD)
        return smtp_object
    except Exception:
        try:
            smtp_object.quit()
        except Exception as cleanup_error:
            debug_swallowed_exception("SMTP session cleanup", cleanup_error)
        raise


# Sends an email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    debug_print("Email delivery attempt", host=SMTP_HOST, port=SMTP_PORT, recipient=RECEIVER_EMAIL, subject=subject)
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            print_recovery_error(context="email", detail="The SMTP settings are incorrect (invalid IP address/FQDN in SMTP_HOST)")
            return 1

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print_recovery_error(context="email", detail="The SMTP settings are incorrect (invalid port number in SMTP_PORT)")
        return 1

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        print_recovery_error(context="email", detail="The SMTP settings are incorrect (invalid email in SENDER_EMAIL or RECEIVER_EMAIL)")
        return 1

    if not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password":
        print_recovery_error(context="email", detail="The SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD variables)")
        return 1

    if not subject or not isinstance(subject, str):
        print_recovery_error(context="email", detail="The SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    if not body and not body_html:
        print_recovery_error(context="email", detail="The SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
        return 1

    try:
        smtpObj = smtp_connect_and_login(use_ssl, smtp_timeout=smtp_timeout)
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
        debug_print("Email delivery", host=SMTP_HOST, port=SMTP_PORT, recipient=RECEIVER_EMAIL, outcome="OK")
    except Exception as e:
        debug_print("Email delivery", host=SMTP_HOST, port=SMTP_PORT, recipient=RECEIVER_EMAIL, outcome="failed", error=f"{type(e).__name__}: {e}")
        print_recovery_error(e, context="email")
        return 1
    verbose_print(f"Email delivered to {RECEIVER_EMAIL}: {subject}")
    return 0


# Returns the TLS context every connection outside requests uses, unverified while VERIFY_SSL is off so they follow the same switch
def tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    if not VERIFY_SSL:
        # check_hostname has to be cleared first, since setting CERT_NONE while it is on raises
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


# Applies the configured TLS verification setting to the connections a session or a library owns rather than each call site
def apply_tls_verification_setting() -> None:
    SPOTIFY_SESSION.verify = VERIFY_SSL
    WEBHOOK_SESSION.verify = VERIFY_SSL
    # pylast builds its own httpx client from this module global, so the switch has to reach it there.
    # A release that renames it would otherwise leave a new attribute nothing reads, which is worse than an error.
    if hasattr(pylast, "SSL_CONTEXT"):
        pylast.SSL_CONTEXT = tls_context()
    else:
        debug_print("TLS setting applied to pylast", outcome="skipped", reason="pylast no longer exposes SSL_CONTEXT")
    if not VERIFY_SSL:
        # Silenced only once the config file has been read, so the shipped default never decides this
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print_recovery_advice(make_recovery_advice("config.insecure", "TLS certificate verification is off, so an intercepted connection cannot be told apart from the real service", recovery_fix_with_guide("Set VERIFY_SSL back to True unless this network intercepts TLS with its own certificate authority", TLS_GUIDE_URL), False), label="Warning")
        print()


# Returns how the tool was started, either as the installed console script or as a downloaded standalone script
def install_method() -> str:
    override = os.environ.get(INSTALL_METHOD_ENV_VAR, "").strip().casefold()
    if override in (INSTALL_METHOD_PYPI, INSTALL_METHOD_SCRIPT):
        return override
    if os.path.basename(sys.argv[0] or "").casefold().endswith(".py"):
        return INSTALL_METHOD_SCRIPT
    return INSTALL_METHOD_PYPI


# Returns the install method in the words the startup summary uses, rather than the code the detector returns
def install_method_display_name(method=None) -> str:
    selected = install_method() if method is None else method
    return {INSTALL_METHOD_PYPI: "PyPI install", INSTALL_METHOD_SCRIPT: "downloaded script"}.get(selected, selected)


# Returns the argv prefix that invokes this tool for the detected install method
def install_command_prefix() -> List[str]:
    if install_method() == INSTALL_METHOD_SCRIPT:
        return ["python3", os.path.basename(sys.argv[0]) or "lastfm_monitor.py"]
    return ["lastfm_monitor"]


# Returns one command-line argument quoted for the shell the user is most likely pasting into
def quote_command_argument(argument: Any) -> str:
    text = str(argument)
    # A <placeholder> is documentation for the reader to replace, so quoting it would only be noise
    if text.startswith("<") and text.endswith(">"):
        return text
    if platform.system() == "Windows":
        return f'"{text}"' if (not text or any(char.isspace() for char in text)) else text
    return shlex.quote(text)


# True when a command writes the dotenv file itself, so it refuses an --env-file that switches dotenv loading off
def command_writes_dotenv(arguments=()) -> bool:
    return any(str(argument) == "--setup" or str(argument).startswith("--set-") for argument in arguments)


# Returns a copy-pasteable command line for the detected install method, carrying the config and dotenv files this run was given
def render_command(arguments=None, include_paths: bool = True, *, config_path=None, env_path=None) -> str:
    parts = list(install_command_prefix())
    parts.extend(str(argument) for argument in (arguments or []))
    # An explicitly passed path is always rendered, while include_paths only governs falling back to the active ones
    selected_config = config_path if config_path is not None else (CLI_CONFIG_PATH if include_paths else None)
    selected_env = env_path if env_path is not None else (DOTENV_FILE if include_paths else None)
    if selected_config:
        parts.extend(["--config-file", str(selected_config)])
    # The "none" sentinel is carried so a printed command reads the setup this run read, except into a command
    # that writes the dotenv file, since those refuse the sentinel at their own argument gate
    if selected_env and not (str(selected_env).casefold() == "none" and command_writes_dotenv(arguments or ())):
        parts.extend(["--env-file", str(selected_env)])
    return " ".join(quote_command_argument(part) for part in parts)


# Returns the command that installs one package into the interpreter running this tool
def install_dependency_command(package_name: str) -> str:
    return f'{quote_command_argument(sys.executable)} -m pip install "{package_name}"'


# True when a setting holds a real value rather than nothing or the placeholder the config template ships
def doctor_value_is_set(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("your_")


# Returns the diagnostic fields describing one secret, adding the length only for keys whose length the provider issues
def secret_fields(value: Any, name: str = "") -> Dict[str, Any]: return {"value": "set" if doctor_value_is_set(value) else "not set", "chars": len(str(value).strip()) if name in FIXED_LENGTH_SECRET_KEYS and doctor_value_is_set(value) else None}


# Records where one secret resolved from and traces it, so a later layer overwrites the earlier answer instead of adding to it
def record_secret_source(name: str, source: str, value: Any = None) -> None:
    if source not in SECRET_SOURCE_ORDER:
        raise ValueError(f"Unsupported secret source: {source}")
    resolved = globals().get(name) if value is None else value
    # A placeholder is not a value, so it earns neither a source nor a row
    if not doctor_value_is_set(resolved):
        SECRET_SOURCES.pop(name, None)
        return
    SECRET_SOURCES[name] = source
    debug_print("Secret resolution", name=name, source=source, **secret_fields(resolved, name))


# Groups the configured secret names by the source each value actually came from, never by value
def secrets_by_source() -> List[Tuple[str, List[str]]]:
    grouped = {}
    for name, source in SECRET_SOURCES.items():
        if doctor_value_is_set(globals().get(name)):
            grouped.setdefault(source, []).append(name)
    return [(source, sorted(grouped[source])) for source in SECRET_SOURCE_ORDER if source in grouped]


# Returns the private values worth replacing wherever they appear, skipping any too short to tell apart from an ordinary word
def known_secret_values() -> List[str]:
    values = []
    for key in SECRET_KEYS:
        secret = globals().get(key)
        if isinstance(secret, str) and len(secret) >= MIN_REDACTABLE_SECRET_LENGTH and not secret.startswith("your_"):
            values.append(secret)
    if isinstance(WEBHOOK_HEADERS, dict):
        for name, value in WEBHOOK_HEADERS.items():
            if isinstance(name, str) and name.casefold() == "authorization" and isinstance(value, str) and len(value) >= MIN_REDACTABLE_SECRET_LENGTH:
                values.append(value)
    return values


# Redacts configured private values and common credential shapes from diagnostic text
def sanitize_error_text(value: Any) -> str:
    text = str(value)
    # Longest first, so a secret that contains another one is not left half replaced
    for secret in sorted(known_secret_values(), key=len, reverse=True):
        text = text.replace(secret, "<redacted>")
    patterns = (
        # A config parse error quotes the offending source line, which is how a password reaches the terminal and the log
        (r"(?m)(\b(?:LASTFM_API_KEY|LASTFM_API_SECRET|SP_CLIENT_ID|SP_CLIENT_SECRET|SMTP_PASSWORD|WEBHOOK_URL|NTFY_ACCESS_TOKEN)\b\s*=\s*).*$", r"\1<redacted>"),
        # spotipy authenticates the Spotify app with Basic while Spotify and ntfy both carry Bearer, so this tool sends two schemes
        (r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?(?:bearer|basic)\s+)[^\s,;'\"}]+", r"\1<redacted>"),
        (r"(?i)(['\"]?(?:lastfm_api_key|lastfm_api_secret|sp_client_id|sp_client_secret|smtp_password|webhook_url|ntfy_access_token|access_token|refresh_token)['\"]?\s*[:=]\s*['\"]?)[^\s,;'\"}]+", r"\1<redacted>"),
        # pylast signs each request with api_sig and sends api_key and the session key as parameters
        (r"(?i)([?&](?:api_key|api_sig|sk|token|secret|password)=)[^&#\s]+", r"\1<redacted>"),
        (r"(?i)https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api(?:/v[0-9]+)?/webhooks/[0-9]+/[^\s'\"<>]+", "<redacted>"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


# Every recovery category the tool can report, kept closed so a message is testable, deduplicable and translatable later
RECOVERY_CODES = frozenset({
    "config.missing", "config.invalid", "config.insecure",
    "dependency.missing",
    "secret.missing", "secret.entry",
    "auth.api_key_invalid",
    "network.unavailable", "network.timeout",
    "lastfm.rate_limited", "lastfm.unavailable",
    "target.missing", "target.invalid", "target.not_found", "target.not_visible",
    "smtp.invalid", "smtp.authentication", "smtp.connection",
    "webhook.invalid", "webhook.rejected", "webhook.rate_limited", "webhook.connection",
    "file.unreadable", "file.unwritable", "file.exists",
    "resource.exhausted",
    "unknown",
})

# Carries one classified failure: what happened, what to do about it and whether retrying can help
RecoveryAdvice = namedtuple("RecoveryAdvice", ["code", "summary", "fix", "retryable", "detail"])
RecoveryAdvice.__new__.__defaults__ = ("",)


# Carries structured recovery advice across an exception boundary without exposing technical detail
class RecoveryError(Exception):
    # Initializes a structured recovery exception, keeping the original cause attached for debug output
    def __init__(self, advice, cause=None):
        self.advice = advice
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause
        super().__init__(advice.summary)


# Builds one piece of recovery advice, refusing any code outside the closed set and sanitizing every field
def make_recovery_advice(code, summary, fix, retryable, detail=""):
    if code not in RECOVERY_CODES:
        raise ValueError(f"Unsupported recovery code: {code}")
    return RecoveryAdvice(code, sanitize_error_text(summary), sanitize_error_text(fix), bool(retryable), sanitize_error_text(detail) if detail else "")


# Adds a directly relevant documentation link on its own line
def recovery_fix_with_guide(fix, guide_url):
    return f"{fix}\nGuide: {guide_url}"


# Returns the advice an optional library that is missing carries, naming what the run loses and how to install it
def missing_dependency_advice(package, effect, alternative=""): return make_recovery_advice("dependency.missing", f"{effect} because the optional '{package}' library is missing", recovery_fix_with_guide(f"Install it with: {install_dependency_command(package)}" + (f". {alternative}" if alternative else ""), INSTALL_GUIDE_URL), False)


# Returns the advice a cancelled secret command reports, worded the same way by every one-shot secret command
def secret_entry_cancelled_advice(subject, flag, guide_url, plural=False):
    return make_recovery_advice("secret.entry", f"{subject[:1].upper()}{subject[1:]} setup was cancelled and the dotenv file was not changed", recovery_fix_with_guide(f"Run {render_command([flag])} again when you have the {'values' if plural else 'value'} ready", guide_url), False)


# Returns the advice a declined secret replacement reports, since the saved value stands and asking again changes nothing
def secret_replacement_declined_advice(subject, flag, guide_url, plural=False):
    kept = "were left as they are" if plural else "was left as it is"
    return make_recovery_advice("secret.entry", f"The saved {subject} {kept} and the dotenv file was not changed", recovery_fix_with_guide(f"Run {render_command([flag])} again and answer y to replace the saved {'values' if plural else 'value'}", guide_url), False)


# Returns the HTTP status carried by an error, when it has one
def recovery_http_status(error):
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


# Returns the numeric status pylast attaches to a web service error, which is a Last.fm error code or an HTTP code
def recovery_lastfm_status(error):
    status = getattr(error, "status", None)
    if isinstance(status, int):
        return status
    if isinstance(status, str):
        try:
            return int(status)
        except ValueError:
            return None
    return None


# Yields the exception and each cause or context up to max_depth, to walk an exception chain
def iter_exc_chain(error, max_depth=8):
    current = error
    for _ in range(max_depth):
        if current is None:
            return
        yield current
        current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)


# Reports whether any exception in the chain is the local file descriptor limit rather than a remote failure
def is_too_many_open_files(error):
    for current in iter_exc_chain(error):
        if isinstance(current, OSError) and getattr(current, "errno", None) == 24:
            return True
        message = str(current).lower()
        if "too many open files" in message or "errno 24" in message:
            return True
    return False

# Returns the next step for a failure no rule recognized, since a run already printing the technical cause cannot be told to re-run for it
def unknown_failure_fix(): return "Open an issue with this output if the failure continues" if DEBUG_MODE else "Re-run with --debug to see the technical cause"



# Maps one exception plus its status and calling context to stable recovery advice
def classify_recovery_error(error=None, context="runtime", detail=""):
    if isinstance(error, RecoveryError):
        return error.advice
    # Both are matched, since a caller that adds context would otherwise hide the error text the rules read
    message = " ".join(part for part in (str(detail or ""), str(error or "")) if part).lower()
    safe_detail = sanitize_error_text(detail or error) if (detail or error) else ""
    lastfm_status = recovery_lastfm_status(error)
    http_status = recovery_http_status(error)

    def advice(code, summary, fix, retryable, guide_url=None):
        return make_recovery_advice(code, summary, recovery_fix_with_guide(fix, guide_url) if guide_url else fix, retryable, safe_detail)

    # Checked ahead of every context, since a local descriptor limit is not a failure of whatever call hit it
    if error is not None and is_too_many_open_files(error):
        return advice("resource.exhausted", "This process ran out of file descriptors, which is a local limit and not a Last.fm problem", "Raise the file descriptor limit, for example with 'ulimit -n 4096', or set LimitNOFILE= if you run under systemd, then restart the tool", False, DIAGNOSTICS_GUIDE_URL)

    if context == "config":
        if "does not exist" in message or "no such file" in message:
            return advice("config.missing", safe_detail or "The configuration file was not found", f"Create one with '{render_command(['--generate-config', DEFAULT_CONFIG_FILENAME], include_paths=False)}' or correct the --config-file path", False, CONFIG_FILE_GUIDE_URL)
        return advice("config.invalid", safe_detail or "The configuration file could not be read", f"Correct the reported line, or write a fresh template to a different path with '{render_command(['--generate-config', '<new-file>'], include_paths=False)}'", False, CONFIG_FILE_GUIDE_URL)

    if context in ("set_lastfm_credentials", "set_spotify_credentials", "set_webhook_url", "set_smtp_password"):
        flag = f"--{context.replace('_', '-')}"
        guide = {"set_lastfm_credentials": LASTFM_API_GUIDE_URL, "set_spotify_credentials": SPOTIFY_APP_GUIDE_URL, "set_smtp_password": SMTP_GUIDE_URL}.get(context, WEBHOOK_GUIDE_URL)
        if "interactive terminal" in message:
            return advice("secret.entry", safe_detail or f"{flag} requires an interactive terminal", f"Run {render_command([flag])} in a terminal window so the value stays hidden while you paste it", False, guide)
        if "cancelled" in message:
            return advice("secret.entry", safe_detail or "Setup was cancelled and the dotenv file was not changed", f"Run {render_command([flag])} again when you have the value ready", False, guide)
        if "--env-file none" in message:
            return advice("secret.entry", safe_detail or "There is nowhere to save the value", f"Drop --env-file none, or name a writable dotenv file with --env-file PATH, then run {render_command([flag])} again", False, SECRETS_GUIDE_URL)
        if "could not save" in message or "could not read" in message:
            return advice("file.unwritable", safe_detail or "The private settings file could not be updated", "Check file permissions or choose another path with --env-file PATH", False, SECRETS_GUIDE_URL)
        if context == "set_smtp_password":
            if "incomplete" in message:
                return advice("config.invalid", safe_detail or "The mail server settings are incomplete", f"Set SMTP_HOST, SMTP_USER, SENDER_EMAIL and RECEIVER_EMAIL in the configuration file, then run {render_command([flag])} again", False, guide)
            if "did not accept" in message:
                return advice("smtp.authentication", safe_detail or "The mail server refused the password", f"Check SMTP_USER and use an app password where the provider requires one, then run {render_command([flag])} again", False, guide)
        if context == "set_webhook_url":
            return advice("webhook.invalid", safe_detail or "The webhook URL was not changed", f"Copy a complete Discord or ntfy webhook URL then run {render_command([flag])} again", False, guide)
        return advice("secret.entry", safe_detail or "No value was saved and the dotenv file was not changed", f"Run {render_command([flag])} again and paste each value when it is asked for", False, guide)

    if context == "target.missing":
        return advice("target.missing", safe_detail or "No Last.fm username was provided", f"Pass the username to monitor: {render_command(['<lastfm_username>'])}", False, QUICK_START_GUIDE_URL)

    if context == "secret.missing":
        return advice("secret.missing", safe_detail or "A required Last.fm credential is missing", f"Save the API key and shared secret with '{render_command(['--set-lastfm-credentials'])}'", False, LASTFM_API_GUIDE_URL)

    if context == "connectivity":
        # Classified from the error, because the detail names the endpoint rather than the failure. No guide,
        # since no page covers this check and the doctor report already ends with the troubleshooting link
        cause = str(error or "").lower()
        if "timed out" in cause or "timeout" in cause:
            return advice("network.timeout", "The connectivity endpoint did not answer in time", "Check network, DNS, proxy and CHECK_INTERNET_URL settings", True)
        return advice("network.unavailable", "The connectivity endpoint could not be reached", "Check network, DNS, proxy and CHECK_INTERNET_URL settings", True)

    if context == "email":
        if any(term in message for term in ("authentication", "auth", "username and password", "535")):
            return advice("smtp.authentication", "The SMTP server rejected the sign-in", "Check SMTP_USER and SMTP_PASSWORD, and use an app password if the provider requires one", False, SMTP_GUIDE_URL)
        if "not set" in message or "incomplete" in message:
            return advice("smtp.invalid", safe_detail or "The mail server settings are incomplete", "Set the missing settings in the configuration file, or turn the email alerts off", False, SMTP_GUIDE_URL)
        if any(term in message for term in ("settings are incorrect", "invalid")):
            return advice("smtp.invalid", safe_detail or "The SMTP settings are incomplete or invalid", "Check SMTP_HOST, SMTP_PORT, SENDER_EMAIL and RECEIVER_EMAIL in the configuration file", False, SMTP_GUIDE_URL)
        return advice("smtp.connection", "The SMTP server could not be reached", "Check SMTP_HOST, SMTP_PORT and SMTP_SSL, then confirm the host is reachable from this machine", True, SMTP_GUIDE_URL)

    if context == "webhook":
        if http_status == 429 or "rate limit" in message:
            return advice("webhook.rate_limited", "The webhook service is rate limiting deliveries", "Reduce how many alert types are enabled, or wait for the service to accept deliveries again", True, WEBHOOK_GUIDE_URL)
        if any(term in message for term in ("must contain", "must be discord", "could not be formatted", "could not apply", "header", "priority", "tags")):
            return advice("webhook.invalid", safe_detail or "The webhook configuration is not usable", f"Check WEBHOOK_URL, WEBHOOK_PROVIDER and the alert settings, then verify with '{render_command(['--send-test-webhook'])}'", False, WEBHOOK_GUIDE_URL)
        if any(term in message for term in ("could not be reached", "connection", "timed out")):
            return advice("webhook.connection", "The webhook service could not be reached", "Check connectivity and the webhook host, then try again", True, WEBHOOK_GUIDE_URL)
        return advice("webhook.rejected", safe_detail or "The webhook service refused the delivery", f"Confirm the webhook still exists and the URL is current, then verify with '{render_command(['--send-test-webhook'])}'", http_status is not None and http_status >= 500, WEBHOOK_GUIDE_URL)

    if context == "file.exists":
        return advice("file.exists", safe_detail or "The destination file already exists", f"Re-run with --force to replace it after a timestamped backup, or write to a different path with '{render_command(['--generate-config', '<new-file>'], include_paths=False)}'", False, CONFIG_FILE_GUIDE_URL)

    if context == "file.unwritable":
        return advice("file.unwritable", safe_detail or "A file the tool keeps could not be written", "Check that the directory exists and is writable, or choose another path", False, DIAGNOSTICS_GUIDE_URL)

    if context == "file":
        if any(term in message for term in ("cannot load", "cannot be opened", "unreadable", "not valid utf-8", "no such file", "cannot be read")):
            return advice("file.unreadable", safe_detail or "A file the tool keeps could not be read", "Check the path and its permissions, or delete the file so it is recreated", False, DIAGNOSTICS_GUIDE_URL)
        return advice("file.unwritable", safe_detail or "A file the tool keeps could not be written", "Check that the directory exists and is writable, or choose another path", False, DIAGNOSTICS_GUIDE_URL)

    # Runtime, which is the monitoring loop, the listing mode and every Last.fm call either of them makes.
    # The pylast status is checked first, because Last.fm answers HTTP 200 with a numeric error code in the body.
    if lastfm_status == 17:
        return advice("target.not_visible", "The monitored user hides their recent listening information", "Ask the user to turn off 'Hide recent listening information' in their Last.fm privacy settings", False, PRIVACY_GUIDE_URL)
    if lastfm_status in (10, 13, 26):
        return advice("auth.api_key_invalid", "Last.fm rejected the configured API key or shared secret", f"Save a working pair with '{render_command(['--set-lastfm-credentials'])}'", False, LASTFM_API_GUIDE_URL)
    if lastfm_status == 29:
        return advice("lastfm.rate_limited", "Last.fm is rate limiting requests", "The tool will wait and retry. Increase the check intervals if this repeats", True, INTERVALS_GUIDE_URL)
    if lastfm_status in (6, 7):
        return advice("target.not_found", safe_detail or "Last.fm has no user with that name", "Check the username, since a deleted or renamed account cannot be monitored", False, USAGE_GUIDE_URL)
    if lastfm_status in (8, 11, 16) or (lastfm_status is not None and lastfm_status >= 500):
        return advice("lastfm.unavailable", "The Last.fm API is temporarily unavailable", "This is usually a Last.fm outage. The tool will keep retrying", True, DIAGNOSTICS_GUIDE_URL)

    if http_status == 429 or "http code 429" in message or "429 client" in message or "rate limit" in message or "too many requests" in message:
        return advice("lastfm.rate_limited", "Last.fm is rate limiting requests", "The tool will wait and retry. Increase the check intervals if this repeats", True, INTERVALS_GUIDE_URL)
    if "invalid api key" in message or "api key suspended" in message or "invalid method signature" in message:
        return advice("auth.api_key_invalid", "Last.fm rejected the configured API key or shared secret", f"Save a working pair with '{render_command(['--set-lastfm-credentials'])}'", False, LASTFM_API_GUIDE_URL)
    if "user required to be logged in" in message:
        return advice("target.not_visible", "The monitored user hides their recent listening information", "Ask the user to turn off 'Hide recent listening information' in their Last.fm privacy settings", False, PRIVACY_GUIDE_URL)
    if "user not found" in message or "no user with that name" in message or http_status == 404:
        return advice("target.not_found", safe_detail or "Last.fm has no user with that name", "Check the username, since a deleted or renamed account cannot be monitored", False, USAGE_GUIDE_URL)
    if (http_status is not None and http_status >= 500) or re.search(r"http code 5\d\d", message) or "temporarily unavailable" in message or "service unavailable" in message or "bad gateway" in message:
        return advice("lastfm.unavailable", "The Last.fm API is temporarily unavailable", "This is usually a Last.fm outage. The tool will keep retrying", True, DIAGNOSTICS_GUIDE_URL)
    if "timed out" in message or "timeout" in message:
        return advice("network.timeout", "The Last.fm request timed out", "Check connectivity. The tool will keep retrying", True, DIAGNOSTICS_GUIDE_URL)
    if any(term in message for term in ("connection", "name resolution", "failed to resolve", "network is unreachable", "no connectivity", "family not supported", "aborted")):
        return advice("network.unavailable", "Last.fm could not be reached", "Check connectivity, DNS and any proxy. The tool will keep retrying", True, DIAGNOSTICS_GUIDE_URL)
    if "invalid" in message and "username" in message:
        return advice("target.invalid", safe_detail or "That is not a usable Last.fm username", f"Pass the {LASTFM_TARGET_FORMS}", False, USAGE_GUIDE_URL)
    return advice("unknown", safe_detail or "The request could not be completed", unknown_failure_fix(), True, DIAGNOSTICS_GUIDE_URL)


# Renders one built advice as the shared Error, To fix and optional Technical detail block
def render_recovery_advice(advice, debug=None, retry_note="", with_fix=True, label="Error"):
    lines = [f"* {label}: {advice.summary}" + (f" ({retry_note})" if retry_note else "")]
    if with_fix:
        lines.append(f"To fix: {advice.fix}")
        # A detail that only repeats the summary spends a line saying nothing
        if (DEBUG_MODE if debug is None else debug) and advice.detail and advice.detail != advice.summary:
            lines.append(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return "\n".join(lines)


# Classifies one failure and renders it through the shared recovery block
def render_recovery_error(error=None, context="runtime", debug=None, detail="", retry_note="", with_fix=True, label="Error"):
    return render_recovery_advice(classify_recovery_error(error, context, detail), debug, retry_note, with_fix, label)


# Tracks one failure category over time, so a lasting outage is reported once instead of on every check
class OutageReporter:
    # Starts with no failure recorded, so the first failure of any category is reported in full
    def __init__(self):
        self.code = None
        self.since = 0
        self.reported_at = 0

    # Records one failed check and returns "full" for a new failure, "degraded" once the liveness interval has passed,
    # "repeat" while the liveness banner is switched off or "" while the same failure is merely continuing
    def failed(self, advice, liveness_interval):
        now = int(time.time())
        if advice.code != self.code:
            self.code = advice.code
            self.since = now
            self.reported_at = now
            return "full"
        # With the liveness banner off there is nothing to carry the reminder, so the summary keeps its old cadence
        if not liveness_interval:
            return "repeat"
        # Timed rather than counted, because a failing run usually retries on a different interval than a healthy one
        if now - self.reported_at >= liveness_interval:
            self.reported_at = now
            return "degraded"
        return ""

    # Clears the failure after a successful check and returns how long it lasted, or None when none was active
    def recovered(self):
        if not self.code:
            return None
        lasted = int(time.time()) - self.since
        self.code = None
        self.since = 0
        self.reported_at = 0
        return lasted


# Reports that nothing changed, so a quiet run still says it is alive on the liveness cadence
def print_liveness_banner(message):
    print(f"* {sanitize_error_text(message)}")
    print_cur_ts("Liveness check, timestamp:\t")


# Reports a lasting failure on the liveness cadence, so a broken run still says it is alive without repeating itself
def print_outage_liveness(target, advice, since):
    print(f"* Monitoring degraded for {target}. {advice.summary} since {get_date_from_ts(since)}")
    print_cur_ts("Liveness check, timestamp:\t")


# Reports that a failure cleared, since a throttled failure no longer stops printing when it is over
def print_outage_recovery(target, lasted):
    print(f"* Monitoring recovered for {target} after {display_time(max(1, lasted))}")
    print_cur_ts("Timestamp:\t\t\t")


# Tracks the last uninterrupted recovery category so a long outage cannot repeat the same hint every cycle
class RecoveryHintTracker:
    # Starts with no category, so the first failure of any kind always renders its hint
    def __init__(self):
        self.last_code = None

    # Returns True for the first category and again only when the failure category changes
    def should_render(self, advice):
        if advice.code == self.last_code:
            return False
        self.last_code = advice.code
        return True

    # Clears suppression after a successful cycle, so a recurrence is reported again
    def reset(self):
        self.last_code = None


# Prints one built advice through the shared recovery block and returns it
def print_recovery_advice(advice, debug=None, retry_note="", with_fix=True, label="Error", tracker=None):
    print(render_recovery_advice(advice, debug, retry_note, with_fix and (tracker is None or tracker.should_render(advice)), label))
    return advice


# Classifies one failure, prints it through the shared recovery block and returns its stable advice
def print_recovery_error(error=None, context="runtime", debug=None, detail="", retry_note="", with_fix=True, label="Error", tracker=None):
    return print_recovery_advice(classify_recovery_error(error, context, detail), debug, retry_note, with_fix, label, tracker)


# Returns whether a webhook URL is a complete private HTTPS link
def validate_webhook_url(url: Any = None) -> bool:
    selected_url = WEBHOOK_URL if url is None else url
    if not isinstance(selected_url, str) or not selected_url.strip():
        return False
    try:
        parsed = urlsplit(selected_url.strip())
    except ValueError:
        return False
    return parsed.scheme.casefold() == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and bool(parsed.path.strip("/"))


# Accepts a complete webhook URL or expands a bare ntfy.sh topic name into one
def normalize_ntfy_topic_url(value: Any = None) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if validate_webhook_url(normalized):
        return normalized
    if re.fullmatch(r"[-_A-Za-z0-9]{1,64}", normalized):
        return f"https://ntfy.sh/{normalized}"
    return ""


# Returns the normalized configured webhook provider or an empty string when unsupported
def normalized_webhook_provider(provider: Any = None) -> str:
    selected_provider = WEBHOOK_PROVIDER if provider is None else provider
    if not isinstance(selected_provider, str):
        return ""
    normalized = selected_provider.strip().casefold()
    return normalized if normalized in ("discord", "ntfy") else ""


# Returns the spelling each webhook service uses for itself, since the stored value is casefolded for comparisons
def webhook_provider_display_name(provider: Any = None) -> str:
    normalized = normalized_webhook_provider(provider)
    return {"discord": "Discord", "ntfy": "ntfy"}.get(normalized, normalized or "an unset provider")


# Detects Discord and public ntfy webhook providers from distinctive URL shapes
def detect_webhook_provider(url: Any) -> str:
    if not validate_webhook_url(url):
        return ""
    try:
        parsed = urlsplit(str(url).strip())
    except ValueError:
        return ""
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    if hostname == "ntfy.sh":
        return "ntfy"
    discord_host = hostname in ("discord.com", "discordapp.com") or hostname.endswith(".discord.com") or hostname.endswith(".discordapp.com")
    discord_path = re.match(r"^/api(?:/v[0-9]+)?/webhooks/[0-9]+/[^/]+/?$", parsed.path) is not None
    return "discord" if discord_host and discord_path else ""


# Returns enabled email notification category names in display order
def _startup_email_notification_categories() -> List[str]:
    settings = (
        (ACTIVE_NOTIFICATION, "active"),
        (INACTIVE_NOTIFICATION, "inactive"),
        (TRACK_NOTIFICATION, "tracked"),
        (SONG_NOTIFICATION, "songs"),
        (SONG_ON_LOOP_NOTIFICATION, "loops"),
        (OFFLINE_ENTRIES_NOTIFICATION, "offline"),
        (ERROR_NOTIFICATION, "errors"),
        (FOLLOWERS_NOTIFICATION, "followers"),
        (FOLLOWINGS_NOTIFICATION, "followings"),
        (PROFILE_NOTIFICATION, "profile"),
    )
    return [label for enabled, label in settings if enabled]


# Returns the webhook notification categories that are switched on, whether or not the channel itself is
def _selected_webhook_notification_categories() -> List[str]:
    settings = (
        (WEBHOOK_ACTIVE_NOTIFICATION, "active"),
        (WEBHOOK_INACTIVE_NOTIFICATION, "inactive"),
        (WEBHOOK_TRACK_NOTIFICATION, "tracked"),
        (WEBHOOK_SONG_NOTIFICATION, "songs"),
        (WEBHOOK_SONG_ON_LOOP_NOTIFICATION, "loops"),
        (WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION, "offline"),
        (WEBHOOK_ERROR_NOTIFICATION, "errors"),
        (WEBHOOK_FOLLOWERS_NOTIFICATION, "followers"),
        (WEBHOOK_FOLLOWINGS_NOTIFICATION, "followings"),
        (WEBHOOK_PROFILE_NOTIFICATION, "profile"),
    )
    return [label for enabled, label in settings if enabled]


# Returns the webhook notification categories a run would actually deliver, for the startup rollup
def _startup_webhook_notification_categories() -> List[str]:
    return _selected_webhook_notification_categories() if WEBHOOK_ENABLED else []


# Rolls one channel's enabled alerts into the state its summary row reports
def _startup_notification_state(categories: List[str]) -> str:
    return "On (" + ", ".join(categories) + ")" if categories else "Off"


# Returns whether one configured webhook alert is enabled independently of email settings
def webhook_event_enabled(notification_type: str) -> bool:
    settings = {
        "active": WEBHOOK_ACTIVE_NOTIFICATION,
        "inactive": WEBHOOK_INACTIVE_NOTIFICATION,
        "track": WEBHOOK_TRACK_NOTIFICATION,
        "song": WEBHOOK_SONG_NOTIFICATION,
        "loop": WEBHOOK_SONG_ON_LOOP_NOTIFICATION,
        "offline_entries": WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION,
        "followers": WEBHOOK_FOLLOWERS_NOTIFICATION,
        "followings": WEBHOOK_FOLLOWINGS_NOTIFICATION,
        "profile": WEBHOOK_PROFILE_NOTIFICATION,
        "error": WEBHOOK_ERROR_NOTIFICATION,
    }
    return bool(WEBHOOK_ENABLED and settings.get(notification_type, False))


# Returns the webhook host alone, so a delivery can be traced without printing the private URL it carries
def webhook_destination_host(url: Any = None) -> str:
    try:
        return urlsplit(str(WEBHOOK_URL if url is None else url).strip()).hostname or "unknown host"
    except ValueError:
        return "unknown host"


# Parses a webhook rate-limit delay and caps untrusted server values to a short wait
def webhook_retry_after_seconds(response: Any) -> float:
    candidates: List[Any] = []
    headers = getattr(response, "headers", {}) or {}
    if hasattr(headers, "get"):
        candidates.append(headers.get("Retry-After"))
    try:
        payload = response.json()
    except Exception as exc:
        debug_swallowed_exception("Webhook retry delay payload read", exc)
        payload = None
    if isinstance(payload, dict):
        candidates.append(payload.get("retry_after"))
    for candidate in candidates:
        if candidate is None or candidate == "":
            continue
        try:
            seconds = float(candidate)
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(candidate))
                seconds = (retry_at - datetime.now(retry_at.tzinfo)).total_seconds()
            except Exception as exc:
                debug_swallowed_exception("Webhook retry delay header read", exc)
                continue
        return max(0.0, min(seconds, WEBHOOK_MAX_RETRY_AFTER_SECONDS))
    return WEBHOOK_FALLBACK_RETRY_SECONDS


# Applies configured placeholders recursively to a webhook template
def format_webhook_payload(template: Any, values: dict) -> Any:
    if isinstance(template, dict):
        return {key: format_webhook_payload(value, values) for key, value in template.items()}
    if isinstance(template, list):
        return [format_webhook_payload(value, values) for value in template]
    if isinstance(template, tuple):
        return tuple(format_webhook_payload(value, values) for value in template)
    if isinstance(template, str):
        if template == "{fields}":
            return values.get("fields", [])
        if template == "{color}":
            return values.get("color", 0xD92323)
        try:
            return template.format(**values)
        except KeyError:
            return template
    return template


# Returns a configuration error for unsafe or unsupported webhook customization
def validate_webhook_customization(provider: Any = None) -> Optional[str]:
    selected_provider = normalized_webhook_provider(provider)
    if selected_provider == "discord":
        if not isinstance(WEBHOOK_USERNAME, str):
            return "WEBHOOK_USERNAME must be a string"
        if not isinstance(WEBHOOK_AVATAR_URL, str):
            return "WEBHOOK_AVATAR_URL must be a string"
        if WEBHOOK_AVATAR_URL.strip() and not validate_webhook_url(WEBHOOK_AVATAR_URL):
            return "WEBHOOK_AVATAR_URL must contain a complete HTTPS link without embedded credentials"
        if not isinstance(WEBHOOK_TEMPLATE, (dict, list, str)):
            return "WEBHOOK_TEMPLATE must be a dictionary, list or string"
    if not isinstance(NTFY_SHORT, bool):
        return "NTFY_SHORT must be a boolean"
    if not isinstance(WEBHOOK_TRANSFORMS, (list, tuple)):
        return "WEBHOOK_TRANSFORMS must be a list or tuple"
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        if not isinstance(transform, (list, tuple)) or len(transform) < 2 or not isinstance(transform[0], str) or not isinstance(transform[1], str):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} must contain a field name and string method name"
        if transform[1].startswith("_") or not callable(getattr("", transform[1], None)):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} uses an unsupported string method"
    return None


# Applies configured string transformations to one webhook value mapping
def apply_webhook_transforms(values: dict) -> dict:
    transformed = dict(values)
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        field = transform[0]
        method_name = transform[1]
        if field not in transformed or not isinstance(transformed[field], str):
            continue
        try:
            transformed[field] = getattr(transformed[field], method_name)(*transform[2:])
        except Exception as exc:
            raise ValueError(f"WEBHOOK_TRANSFORMS entry {index + 1} could not apply {field}.{method_name}") from exc
    return transformed


# Builds bounded placeholder values shared by webhook templates and headers
def build_webhook_values(title: str, description: str, notification_type: str) -> dict:
    colors = {"active": 0x2ECC71, "inactive": 0x747F8D, "track": 0xD92323, "song": 0x3498DB, "loop": 0x9B59B6, "offline_entries": 0xF39C12, "followers": 0x1ABC9C, "followings": 0x16A085, "error": 0xE74C3C}
    safe_title = str(title).replace("\x00", "")[:WEBHOOK_EMBED_TITLE_LIMIT] or "Last.fm Monitor"
    safe_description = str(description).replace("\x00", "")[:WEBHOOK_EMBED_DESCRIPTION_LIMIT]
    username = WEBHOOK_USERNAME.strip()[:80] if isinstance(WEBHOOK_USERNAME, str) else ""
    avatar_url = WEBHOOK_AVATAR_URL.strip() if isinstance(WEBHOOK_AVATAR_URL, str) else ""
    values = {"title": safe_title, "description": safe_description, "version": VERSION, "fields": [], "fields_str": "", "color": colors.get(notification_type, 0xD92323), "timestamp": datetime.now().astimezone().isoformat(), "username": username, "avatar_url": avatar_url}
    return apply_webhook_transforms(values)


# Builds one customized Discord-format payload while keeping mentions disabled
def build_webhook_payload(title: str, description: str, notification_type: str, payload_values: Optional[dict] = None) -> Any:
    values = build_webhook_values(title, description, notification_type) if payload_values is None else payload_values
    try:
        payload = format_webhook_payload(WEBHOOK_TEMPLATE, values)
    except Exception as exc:
        raise ValueError("WEBHOOK_TEMPLATE could not be formatted with the supported placeholders") from exc
    if isinstance(payload, dict):
        if payload.get("username") == "":
            payload.pop("username")
        if payload.get("avatar_url") == "":
            payload.pop("avatar_url")
        payload["allowed_mentions"] = {"parse": []}
    return payload


# Truncates text to a UTF-8 byte limit without returning a partial character
def truncate_utf8_bytes(text: str, max_bytes: int, suffix: str = "") -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    encoded_suffix = suffix.encode("utf-8")
    if len(encoded_suffix) >= max_bytes:
        return encoded_suffix[:max_bytes].decode("utf-8", errors="ignore")
    return encoded[:max_bytes - len(encoded_suffix)].decode("utf-8", errors="ignore") + suffix


# Builds one bounded ntfy title and message pair
def build_ntfy_webhook_message(title: str, description: str) -> Tuple[str, str]:
    safe_title = str(title).replace("\x00", "")[:WEBHOOK_EMBED_TITLE_LIMIT] or "Last.fm Monitor"
    safe_message = truncate_utf8_bytes(str(description).replace("\x00", ""), NTFY_MESSAGE_LIMIT_BYTES, NTFY_TRUNCATION_SUFFIX)
    return safe_title, safe_message


# Returns a safe validation error for one custom webhook header mapping
def _validate_webhook_header_mapping(headers: Any) -> Optional[str]:
    if not isinstance(headers, dict):
        return "WEBHOOK_HEADERS must be a dictionary of string header names and values"
    normalized_names = set()
    for name, value in headers.items():
        if not isinstance(name, str) or not re.fullmatch(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", name):
            return "WEBHOOK_HEADERS contains an invalid HTTP header name"
        normalized_name = name.casefold()
        if normalized_name in normalized_names:
            return "WEBHOOK_HEADERS contains duplicate case-insensitive header names"
        normalized_names.add(normalized_name)
        if not isinstance(value, str):
            return f"WEBHOOK_HEADERS value for {name} must be a string"
        if "\r" in value or "\n" in value:
            return f"WEBHOOK_HEADERS value for {name} must not contain line breaks"
    return None


# Returns a safe configuration error for custom webhook headers or ntfy access tokens
def validate_webhook_headers(provider: Any = None) -> Optional[str]:
    selected_provider = normalized_webhook_provider(provider)
    header_error = _validate_webhook_header_mapping(WEBHOOK_HEADERS)
    if header_error is not None:
        return header_error
    if selected_provider == "ntfy":
        if not isinstance(NTFY_ACCESS_TOKEN, str):
            return "NTFY_ACCESS_TOKEN must be a string"
        token = NTFY_ACCESS_TOKEN.strip()
        if "\r" in token or "\n" in token:
            return "NTFY_ACCESS_TOKEN must not contain line breaks"
        if token.casefold().startswith(("bearer ", "basic ")):
            return "NTFY_ACCESS_TOKEN must contain only the access token without an Authorization scheme"
    return None


# Builds provider-specific headers while formatting placeholders and applying private ntfy authentication
def build_webhook_headers(provider: str, values: dict) -> dict:
    validation_error = validate_webhook_headers(provider)
    if validation_error is not None:
        raise ValueError(validation_error)
    try:
        formatted_headers = format_webhook_payload(WEBHOOK_HEADERS, values)
    except Exception as exc:
        raise ValueError("WEBHOOK_HEADERS could not be formatted with the supported placeholders") from exc
    formatted_error = _validate_webhook_header_mapping(formatted_headers)
    if formatted_error is not None:
        raise ValueError(formatted_error)
    headers = dict(cast(dict[str, str], formatted_headers))
    if not any(name.casefold() == "user-agent" for name in headers):
        headers["User-Agent"] = f"LastfmMonitor/{VERSION}"
    if provider == "ntfy":
        headers = {name: value for name, value in headers.items() if name.casefold() != "content-type"}
        headers["Content-Type"] = "text/plain; charset=utf-8"
        token = NTFY_ACCESS_TOKEN.strip()
        if token:
            headers = {name: value for name, value in headers.items() if name.casefold() != "authorization"}
            headers["Authorization"] = f"Bearer {token}"
    return headers


# Sends one webhook request with the destination, deadline and redirect policy every delivery shares
def post_webhook_request(**request_kwargs: Any) -> Any:
    destination = str(WEBHOOK_URL or "").strip()
    # Revalidated here because a dotenv reload can replace the destination after the delivery started
    if not validate_webhook_url(destination):
        raise req.exceptions.InvalidURL("WEBHOOK_URL must contain a complete HTTPS link")
    return WEBHOOK_SESSION.post(destination, timeout=WEBHOOK_TIMEOUT_SECONDS, verify=VERIFY_SSL, allow_redirects=False, **request_kwargs)


# Sends one webhook through an isolated bounded retry path
def send_webhook(title: str, description: str, notification_type: str = "song", force: bool = False, sleeper: Optional[Callable[[float], None]] = None) -> int:
    if not force and not webhook_event_enabled(notification_type):
        return 1
    if not validate_webhook_url():
        print_recovery_error(context="webhook", detail="WEBHOOK_URL must contain a complete HTTPS link")
        return 1
    provider = normalized_webhook_provider()
    if not provider:
        print_recovery_error(context="webhook", detail="WEBHOOK_PROVIDER must be discord or ntfy")
        return 1
    customization_error = validate_webhook_customization(provider)
    if customization_error is not None:
        print_recovery_error(context="webhook", detail=customization_error)
        return 1
    header_error = validate_webhook_headers(provider)
    if header_error is not None:
        print_recovery_error(context="webhook", detail=header_error)
        return 1
    try:
        webhook_values = build_webhook_values(title, description, notification_type)
        request_headers = build_webhook_headers(provider, webhook_values)
        discord_payload = build_webhook_payload(title, description, notification_type, webhook_values) if provider == "discord" else None
    except ValueError as exc:
        print_recovery_error(exc, context="webhook")
        return 1
    sleep_func = time.sleep if sleeper is None else sleeper
    ntfy_title, ntfy_message = build_ntfy_webhook_message(str(webhook_values["title"]), str(webhook_values["description"])) if provider == "ntfy" else ("", "")
    ntfy_params = {"title": ntfy_title}
    for attempt in range(WEBHOOK_MAX_ATTEMPTS):
        try:
            if provider == "ntfy":
                response = post_webhook_request(data=ntfy_message.encode("utf-8"), params=ntfy_params, headers=request_headers)
            elif isinstance(discord_payload, str):
                response = post_webhook_request(data=discord_payload, headers=request_headers)
            else:
                response = post_webhook_request(json=discord_payload, headers=request_headers)
            attempt_label = f"#{attempt + 1}/{WEBHOOK_MAX_ATTEMPTS}"
            if 200 <= response.status_code <= 299:
                verbose_print(f"Webhook delivered through {provider}: {webhook_values['title']}")
                debug_print("Webhook delivery", provider=provider, host=webhook_destination_host(), attempt=attempt_label, status=response.status_code, outcome="OK")
                return 0
            retryable = response.status_code == 429 or 500 <= response.status_code <= 599
            if not retryable or attempt == WEBHOOK_MAX_ATTEMPTS - 1:
                debug_print("Webhook delivery", provider=provider, host=webhook_destination_host(), attempt=attempt_label, status=response.status_code, retryable=retryable, outcome="failed")
                print_recovery_error(req.HTTPError(response=response), context="webhook", detail=f"The webhook service returned HTTP {response.status_code}")
                return 1
            delay = webhook_retry_after_seconds(response) if response.status_code == 429 else WEBHOOK_FALLBACK_RETRY_SECONDS
            debug_print("Webhook delivery retry", provider=provider, host=webhook_destination_host(), attempt=attempt_label, status=response.status_code, delay=f"{delay:g}s", outcome="failed")
            sleep_func(delay)
        except req.RequestException as exc:
            attempt_label = f"#{attempt + 1}/{WEBHOOK_MAX_ATTEMPTS}"
            if attempt == WEBHOOK_MAX_ATTEMPTS - 1:
                debug_print("Webhook delivery", provider=provider, host=webhook_destination_host(), attempt=attempt_label, outcome="failed", error=f"{type(exc).__name__}: {exc}")
                print_recovery_error(exc, context="webhook", detail=f"The webhook service could not be reached ({type(exc).__name__})")
                return 1
            debug_print("Webhook delivery retry", provider=provider, host=webhook_destination_host(), attempt=attempt_label, delay=f"{WEBHOOK_FALLBACK_RETRY_SECONDS:g}s", outcome="failed", error=f"{type(exc).__name__}: {exc}")
            sleep_func(WEBHOOK_FALLBACK_RETRY_SECONDS)
    return 1


# Sends one alert through the enabled email and webhook channels
def send_notification_channels(notification_type: str, subject: str, body: str, body_html: str = "", email_enabled: bool = False, webhook_enabled: Optional[bool] = None, subject_short: str = "", body_short: str = "") -> Tuple[bool, bool]:
    email_attempted = bool(email_enabled)
    webhook_attempted = webhook_event_enabled(notification_type) if webhook_enabled is None else bool(webhook_enabled)
    email_delivered = False
    webhook_delivered = False
    if email_attempted:
        print(f"Sending email notification to {RECEIVER_EMAIL}")
        email_delivered = send_email(subject, body, body_html, SMTP_SSL) == 0
        debug_print("Notification dispatch", type=notification_type, channel="email", outcome="OK" if email_delivered else "failed")
    if webhook_attempted:
        print("Sending webhook notification")
        use_short_content = NTFY_SHORT is True and normalized_webhook_provider() == "ntfy"
        webhook_subject = (subject_short or subject) if use_short_content else subject
        webhook_body = (body_short or body) if use_short_content else body
        webhook_delivered = send_webhook(webhook_subject, webhook_body, notification_type, force=True) == 0
        debug_print("Notification dispatch", type=notification_type, channel="webhook", outcome="OK" if webhook_delivered else "failed")
    # Delivery rather than the attempt, so a channel that failed is tried again while one that arrived is not sent twice
    return email_delivered, webhook_delivered


# Initializes the CSV file
def init_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
        debug_print("CSV file initialization", path=csv_file_name, outcome="OK")
    except Exception as e:
        debug_print("CSV file initialization", path=csv_file_name, outcome="failed", error=f"{type(e).__name__}: {e}")
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")


# Writes CSV entry
def write_csv_entry(csv_file_name, timestamp, artist, track, album):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Date': timestamp, 'Artist': artist, 'Track': track, 'Album': album})
        debug_print("CSV entry write", path=csv_file_name, outcome="OK")

    except Exception as e:
        debug_print("CSV entry write", path=csv_file_name, outcome="failed", error=f"{type(e).__name__}: {e}")
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]} {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


# Prints the current date/time in human readable format with separator; eg. Sun 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    global PENDING_NOTICE_BLOCK
    PENDING_NOTICE_BLOCK = False
    print(get_cur_ts(str(ts_str)))
    print("─" * HORIZONTAL_LINE)


# Renders one diagnostic line as an operation followed by comma-separated key=value fields, dropping unset ones
def format_diagnostic_line(operation, fields):
    rendered = ", ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    return f"{operation}: {rendered}" if rendered else str(operation)


# Prints one timestamped and sanitized diagnostic line only when debug mode is enabled
def debug_print(_operation, **fields):
    if DEBUG_MODE:
        # Sanitized here rather than at each call site, since one caller interpolating a secret is enough to leak it
        message = format_diagnostic_line(_operation, fields)
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] {sanitize_error_text(message)}")


# Prints one sanitized operational detail only when verbose mode is enabled
def verbose_print(message):
    if VERBOSE_MODE:
        print(f"* {sanitize_error_text(message)}")


# Prints verbose-only notices as one block, so a standalone line is not left without the timestamp trailer
def verbose_notice(*messages):
    if not VERBOSE_MODE or not messages:
        return
    for message in messages:
        verbose_print(message)
    # Before monitoring starts the notice belongs to the startup screen, which the monitoring header closes
    if MONITORING_ACTIVE:
        print_cur_ts("Timestamp:\t\t\t")


# Marks the point where output stops being the startup screen, so later notices close their own block
def mark_monitoring_started():
    global MONITORING_ACTIVE
    MONITORING_ACTIVE = True


# Closes the block of verbose lines a check printed on its own, so they are never left without a timestamp
def close_pending_notice_block():
    if PENDING_NOTICE_BLOCK:
        print_cur_ts("Timestamp:\t\t\t")


# Records a swallowed exception in debug output so a silently degraded feature can still be diagnosed
def debug_swallowed_exception(context, exc):
    debug_print(context, outcome="failed", error=f"{type(exc).__name__}: {exc}")


# Names the alert a feature feeds when that feature could not be read and reports whether the reader saw it
def verbose_degraded_feature(feature, alert, error=None):
    global PENDING_NOTICE_BLOCK
    debug_print(feature, outcome="degraded", alert=alert, error=None if error is None else f"{type(error).__name__}: {error}")
    verbose_print(f"{feature} is unavailable, so {alert} cannot fire")
    # A degraded feature can be reported from inside a report, so the check closes the block instead of this line
    if VERBOSE_MODE and MONITORING_ACTIVE:
        PENDING_NOTICE_BLOCK = True
    return bool(VERBOSE_MODE)


# Returns the timestamp/datetime object in human readable format (long version); eg. Sun 21 Apr 2024, 15:08:45
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


# Returns the timestamp/datetime object in human readable format (short version); eg.
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


# Returns the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
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


# Returns the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
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
    global ACTIVE_NOTIFICATION
    global INACTIVE_NOTIFICATION
    global OFFLINE_ENTRIES_NOTIFICATION
    ACTIVE_NOTIFICATION = not ACTIVE_NOTIFICATION
    INACTIVE_NOTIFICATION = not INACTIVE_NOTIFICATION
    OFFLINE_ENTRIES_NOTIFICATION = not OFFLINE_ENTRIES_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active = {ACTIVE_NOTIFICATION}] [inactive = {INACTIVE_NOTIFICATION}] [offline entries = {OFFLINE_ENTRIES_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGUSR2 allowing to switch every song email notifications
def toggle_song_notifications_signal_handler(sig, frame):
    global SONG_NOTIFICATION
    SONG_NOTIFICATION = not SONG_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [every song = {SONG_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGURG allowing to switch progress indicator in the output
def toggle_progress_indicator_signal_handler(sig, frame):
    global PROGRESS_INDICATOR
    PROGRESS_INDICATOR = not PROGRESS_INDICATOR
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Progress indicator: {PROGRESS_INDICATOR}")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGCONT allowing to switch tracked songs email notifications
def toggle_track_notifications_signal_handler(sig, frame):
    global TRACK_NOTIFICATION
    TRACK_NOTIFICATION = not TRACK_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [tracked = {TRACK_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGPIPE allowing to switch songs on loop email notifications
def toggle_songs_on_loop_notifications_signal_handler(sig, frame):
    global SONG_ON_LOOP_NOTIFICATION
    SONG_ON_LOOP_NOTIFICATION = not SONG_ON_LOOP_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [songs on loop = {SONG_ON_LOOP_NOTIFICATION}]")
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


# Signal handler for SIGHUP allowing to reload secrets from .env
def reload_secrets_signal_handler(sig, frame):
    global SP_OAUTH_MEMORY_CACHE_HANDLER, WEBHOOK_PROVIDER
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")

    # disable autoscan if DOTENV_FILE set to none
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        # reload .env if python-dotenv is installed
        try:
            from dotenv import load_dotenv, find_dotenv
            if DOTENV_FILE:
                env_path = DOTENV_FILE
            else:
                env_path = find_dotenv()
            if env_path:
                load_dotenv(env_path, override=True, interpolate=False)
            else:
                print("* No .env file found, skipping env-var reload")
        except ImportError:
            env_path = None
            print_recovery_advice(missing_dependency_advice("python-dotenv", "The env-var reload was skipped"), label="Warning")

    oauth_credentials_changed = False
    webhook_url_changed = False
    if env_path:
        for secret in SECRET_KEYS:
            old_val = globals().get(secret)
            val = os.getenv(secret)
            if val is not None and val != old_val:
                globals()[secret] = val
                if secret in ("SP_CLIENT_ID", "SP_CLIENT_SECRET"):
                    oauth_credentials_changed = True
                if secret == "WEBHOOK_URL":
                    webhook_url_changed = True
                record_secret_source(secret, "dotenv file")
                debug_print("Secret reload", name=secret, path=env_path, **secret_fields(val, secret))
                print(f"* Reloaded {secret} from {env_path}")
    if oauth_credentials_changed:
        SP_OAUTH_MEMORY_CACHE_HANDLER = None
    if webhook_url_changed:
        detected_provider = detect_webhook_provider(WEBHOOK_URL)
        if detected_provider and detected_provider != normalized_webhook_provider():
            WEBHOOK_PROVIDER = detected_provider
            print(f"* Updated webhook provider to {webhook_provider_display_name(detected_provider)}")

    print_cur_ts("Timestamp:\t\t\t")


# Accesses the previous and next elements of the list
def previous_and_next(some_iterable):
    prevs, items, nexts = tee(some_iterable, 3)
    prevs = chain([None], prevs)
    nexts = chain(islice(nexts, 1, None), [None])
    return zip(prevs, items, nexts)


# Prepares Spotify, Apple & lyrics search URLs for specified track and Last.fm URLs for track and album
def get_spotify_apple_genius_search_urls(artist, track, album=None, network=None, track_obj=None):
    spotify_search_string = quote_plus(f"{artist} {track}")
    # Clean search string for lyrics services (remove remaster, extended, etc.)
    lyrics_search_string = f"{artist} {track}"
    if re.search(re_search_str, lyrics_search_string, re.IGNORECASE):
        lyrics_search_string = re.sub(re_replace_str, '', lyrics_search_string, flags=re.IGNORECASE)
    apple_search_string = quote(f"{artist} {track}")
    spotify_search_url = f"https://open.spotify.com/search/{spotify_search_string}?si=1"
    apple_search_url = f"https://music.apple.com/pl/search?term={apple_search_string}"
    genius_search_url = f"https://genius.com/search?q={quote_plus(lyrics_search_string)}"
    azlyrics_search_url = f"https://www.azlyrics.com/search/?q={quote_plus(lyrics_search_string)}"
    tekstowo_search_url = f"https://www.tekstowo.pl/szukaj,{quote_plus(lyrics_search_string)}.html"
    musixmatch_search_url = f"https://www.musixmatch.com/search?query={quote_plus(lyrics_search_string)}"
    lyrics_com_search_url = f"https://www.lyrics.com/serp.php?st={quote_plus(lyrics_search_string)}&qtype=1"
    youtube_music_search_url = f"https://music.youtube.com/search?q={spotify_search_string}"
    amazon_music_search_url = f"https://music.amazon.com/search/{spotify_search_string}"
    deezer_search_url = f"https://www.deezer.com/search/{spotify_search_string}"
    tidal_search_url = f"https://tidal.com/search?q={spotify_search_string}"

    # Get Last.fm URL - use track object if available, otherwise construct manually
    lastfm_url = ""
    if track_obj and hasattr(track_obj, 'get_url'):
        try:
            lastfm_url = track_obj.get_url()
        except Exception as exc:
            debug_swallowed_exception("Last.fm track URL read", exc)
            # Fallback to manual construction if get_url() fails
            artist_encoded = quote_plus(str(artist))
            track_encoded = quote_plus(str(track))
            lastfm_url = f"https://www.last.fm/music/{artist_encoded}/_/{track_encoded}"
    elif network:
        # If we have network but no track object, try creating one
        try:
            track_obj_temp = pylast.Track(artist, track, network)
            lastfm_url = track_obj_temp.get_url()
        except Exception as exc:
            debug_swallowed_exception("Last.fm track URL read", exc)
            # Fallback to manual construction
            artist_encoded = quote_plus(str(artist))
            track_encoded = quote_plus(str(track))
            lastfm_url = f"https://www.last.fm/music/{artist_encoded}/_/{track_encoded}"
    else:
        # No track object or network, construct manually
        artist_encoded = quote_plus(str(artist))
        track_encoded = quote_plus(str(track))
        lastfm_url = f"https://www.last.fm/music/{artist_encoded}/_/{track_encoded}"
    # Get Last.fm album URL if album provided
    lastfm_album_url = ""
    if album:
        if network:
            try:
                lastfm_album_url = pylast.Album(artist, album, network).get_url()
            except Exception as exc:
                debug_swallowed_exception("Last.fm album URL read", exc)
                try:
                    # Fallback to manual construction
                    artist_encoded = quote_plus(str(artist))
                    album_encoded = quote_plus(str(album))
                    lastfm_album_url = f"https://www.last.fm/music/{artist_encoded}/{album_encoded}"
                except Exception as build_error:
                    debug_swallowed_exception("Last.fm album URL construction", build_error)
                    lastfm_album_url = ""
        else:
            try:
                artist_encoded = quote_plus(str(artist))
                album_encoded = quote_plus(str(album))
                lastfm_album_url = f"https://www.last.fm/music/{artist_encoded}/{album_encoded}"
            except Exception as exc:
                debug_swallowed_exception("Last.fm album URL construction", exc)
                lastfm_album_url = ""

    return spotify_search_url, apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, lastfm_url, lastfm_album_url


# Formats lyrics URLs for console output based on configuration
def format_lyrics_urls_console(genius_url, azlyrics_url, tekstowo_url, musixmatch_url, lyrics_com_url):
    lines = []
    if ENABLE_GENIUS_LYRICS_URL:
        lines.append(f"Genius lyrics URL:\t\t{genius_url}")
    if ENABLE_AZLYRICS_URL:
        lines.append(f"AZLyrics URL:\t\t\t{azlyrics_url}")
    if ENABLE_TEKSTOWO_URL:
        lines.append(f"Tekstowo.pl URL:\t\t{tekstowo_url}")
    if ENABLE_MUSIXMATCH_URL:
        lines.append(f"Musixmatch URL:\t\t\t{musixmatch_url}")
    if ENABLE_LYRICS_COM_URL:
        lines.append(f"Lyrics.com URL:\t\t\t{lyrics_com_url}")
    return "\n".join(lines) if lines else ""


# Formats lyrics URLs for plain text email body based on configuration
def format_lyrics_urls_email_text(genius_url, azlyrics_url, tekstowo_url, musixmatch_url, lyrics_com_url):
    lines = []
    if ENABLE_GENIUS_LYRICS_URL:
        lines.append(f"Genius lyrics URL: {genius_url}")
    if ENABLE_AZLYRICS_URL:
        lines.append(f"AZLyrics URL: {azlyrics_url}")
    if ENABLE_TEKSTOWO_URL:
        lines.append(f"Tekstowo.pl URL: {tekstowo_url}")
    if ENABLE_MUSIXMATCH_URL:
        lines.append(f"Musixmatch URL: {musixmatch_url}")
    if ENABLE_LYRICS_COM_URL:
        lines.append(f"Lyrics.com URL: {lyrics_com_url}")
    return "\n".join(lines) if lines else ""


# Formats lyrics URLs for HTML email body based on configuration
def format_lyrics_urls_email_html(genius_url, azlyrics_url, tekstowo_url, musixmatch_url, lyrics_com_url, artist, track):
    lines = []
    escaped_artist = escape(artist)
    escaped_track = escape(track)
    if ENABLE_GENIUS_LYRICS_URL:
        lines.append(f'Genius lyrics URL: <a href="{genius_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_AZLYRICS_URL:
        lines.append(f'AZLyrics URL: <a href="{azlyrics_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_TEKSTOWO_URL:
        lines.append(f'Tekstowo.pl URL: <a href="{tekstowo_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_MUSIXMATCH_URL:
        lines.append(f'Musixmatch URL: <a href="{musixmatch_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_LYRICS_COM_URL:
        lines.append(f'Lyrics.com URL: <a href="{lyrics_com_url}">{escaped_artist} - {escaped_track}</a>')
    return "<br>".join(lines) if lines else ""


# Formats music service URLs for console output based on configuration
# Note: This excludes the primary "Track:" URL which is controlled by USE_LASTFM_URL_IN_LAST_PLAYED
def format_music_urls_console(spotify_url, lastfm_url, lastfm_album_url, apple_music_url, youtube_music_url, amazon_music_url, deezer_url, tidal_url):
    lines = []
    if ENABLE_SPOTIFY_URL:
        lines.append(f"Spotify URL:\t\t\t{spotify_url}")
    if ENABLE_LASTFM_URL:
        lines.append(f"Last.fm URL:\t\t\t{lastfm_url}")
    if ENABLE_LASTFM_ALBUM_URL and lastfm_album_url:
        lines.append(f"Last.fm album URL:\t\t{lastfm_album_url}")
    if ENABLE_APPLE_MUSIC_URL:
        lines.append(f"Apple Music URL:\t\t{apple_music_url}")
    if ENABLE_YOUTUBE_MUSIC_URL:
        lines.append(f"YouTube Music URL:\t\t{youtube_music_url}")
    if ENABLE_AMAZON_MUSIC_URL:
        lines.append(f"Amazon Music URL:\t\t{amazon_music_url}")
    if ENABLE_DEEZER_URL:
        lines.append(f"Deezer URL:\t\t\t{deezer_url}")
    if ENABLE_TIDAL_URL:
        lines.append(f"Tidal URL:\t\t\t{tidal_url}")
    return "\n".join(lines) if lines else ""


# Formats music service URLs for plain text email body based on configuration
# Note: This excludes the primary "Track:" / "Last played:" URL which is controlled by USE_LASTFM_URL_IN_LAST_PLAYED
def format_music_urls_email_text(spotify_url, lastfm_url, lastfm_album_url, apple_music_url, youtube_music_url, amazon_music_url, deezer_url, tidal_url):
    lines = []
    if ENABLE_SPOTIFY_URL:
        lines.append(f"Spotify URL: {spotify_url}")
    if ENABLE_LASTFM_URL:
        lines.append(f"Last.fm URL: {lastfm_url}")
    if ENABLE_LASTFM_ALBUM_URL and lastfm_album_url:
        lines.append(f"Last.fm album URL: {lastfm_album_url}")
    if ENABLE_APPLE_MUSIC_URL:
        lines.append(f"Apple Music URL: {apple_music_url}")
    if ENABLE_YOUTUBE_MUSIC_URL:
        lines.append(f"YouTube Music URL: {youtube_music_url}")
    if ENABLE_AMAZON_MUSIC_URL:
        lines.append(f"Amazon Music URL: {amazon_music_url}")
    if ENABLE_DEEZER_URL:
        lines.append(f"Deezer URL: {deezer_url}")
    if ENABLE_TIDAL_URL:
        lines.append(f"Tidal URL: {tidal_url}")
    return "\n".join(lines) if lines else ""


# Formats music service URLs for HTML email body based on configuration
# Note: This excludes the primary "Track:" / "Last played:" URL which is controlled by USE_LASTFM_URL_IN_LAST_PLAYED
# Note: Last.fm album URL is not included here as it's part of the Album line in HTML emails
# secondary_url and secondary_url_label are the URL and label for the secondary URL field (Spotify or Last.fm)
def format_music_urls_email_html(spotify_url, lastfm_url, lastfm_album_url, apple_music_url, youtube_music_url, amazon_music_url, deezer_url, tidal_url, artist, track, secondary_url, secondary_url_label):
    lines = []
    escaped_artist = escape(artist)
    escaped_track = escape(track)
    # Secondary URL (Spotify or Last.fm) - only show if enabled
    if secondary_url_label == "Spotify URL" and ENABLE_SPOTIFY_URL:
        lines.append(f'{secondary_url_label}: <a href="{secondary_url}">{escaped_artist} - {escaped_track}</a>')
    elif secondary_url_label == "Last.fm URL" and ENABLE_LASTFM_URL:
        lines.append(f'{secondary_url_label}: <a href="{secondary_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_APPLE_MUSIC_URL:
        lines.append(f'Apple Music URL: <a href="{apple_music_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_YOUTUBE_MUSIC_URL:
        lines.append(f'YouTube Music URL: <a href="{youtube_music_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_AMAZON_MUSIC_URL:
        lines.append(f'Amazon Music URL: <a href="{amazon_music_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_DEEZER_URL:
        lines.append(f'Deezer URL: <a href="{deezer_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_TIDAL_URL:
        lines.append(f'Tidal URL: <a href="{tidal_url}">{escaped_artist} - {escaped_track}</a>')
    return "<br>".join(lines) if lines else ""


# Returns the file one run keeps its last activity in, named after the user it monitors
def resolve_status_file(target):
    return f"lastfm_{target}_last_activity.json"


# Writes the last activity snapshot the next run starts from
def save_last_activity_state(path, last_activity):
    try:
        write_json_atomically(path, last_activity)
        debug_print("Last activity write", path=path, entries=len(last_activity), outcome="OK")
    except Exception as e:
        debug_print("Last activity write", path=path, outcome="failed", error=f"{type(e).__name__}: {e}")
        print_recovery_error(e, context="file.unwritable", detail=f"Cannot save the last status to '{path}' file: {e}")


# Returns the track the user is playing right now, or None when nothing is playing
def lastfm_get_now_playing(username, user):
    try:
        now_playing = user.get_now_playing()
        debug_print("Last.fm now playing fetch", user=username, track=str(now_playing) if now_playing else None, outcome="OK")
        return now_playing
    except Exception as exc:
        debug_print("Last.fm now playing fetch", user=username, outcome="failed", error=f"{type(exc).__name__}: {exc}")
        raise


# Returns the list of recently played Last.fm tracks
def lastfm_get_recent_tracks(username, network, number):
    try:
        recent_tracks = network.get_user(username).get_recent_tracks(limit=number)
        debug_print("Last.fm recent tracks fetch", user=username, limit=number, tracks=len(recent_tracks or []), outcome="OK")
        return recent_tracks
    except Exception as exc:
        debug_print("Last.fm recent tracks fetch", user=username, limit=number, outcome="failed", error=f"{type(exc).__name__}: {exc}")
        raise


# Returns Last.fm HTTP headers crafted to look like a real browser so the WAF is less likely to block low-volume scraping
def _lastfm_scrape_headers():
    return {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


# Returns an error description when a Last.fm response should be retried
def _lastfm_retryable_response_error(response):
    if response.status_code == 429 or response.status_code >= 500:
        return f"HTTP {response.status_code} from Last.fm"

    content_type = response.headers.get('Content-Type', '').lower()
    if 'text/html' in content_type:
        body = response.content.lower()
        if b'temporarily unavailable' in body and b'error 503' in body:
            return "Last.fm returned its temporarily unavailable page"

    return None


# Fetches a URL with backoff for transient Last.fm HTTP and soft error responses then raises RuntimeError on final failure
def _lastfm_http_get_with_retry(url, attempts=3, base_delay=2.0):
    last_exc = None
    timeout = FUNCTION_TIMEOUT * 2
    for i in range(attempts):
        attempt_label = f"#{i + 1}/{attempts}"
        status = None
        try:
            response = req.get(url, headers=_lastfm_scrape_headers(), timeout=timeout, verify=VERIFY_SSL)
            status = response.status_code
            retryable_error = _lastfm_retryable_response_error(response)
            if retryable_error:
                last_exc = RuntimeError(retryable_error)
                debug_print("HTTP GET", url=url, timeout=f"{timeout}s", attempt=attempt_label, status=status, outcome="failed", error=retryable_error)
            else:
                response.raise_for_status()
                debug_print("HTTP GET", url=url, timeout=f"{timeout}s", attempt=attempt_label, status=status, outcome="OK")
                return response
        except (req.Timeout, req.ConnectionError) as e:
            last_exc = e
            debug_print("HTTP GET", url=url, timeout=f"{timeout}s", attempt=attempt_label, outcome="failed", error=f"{type(e).__name__}: {e}")
        except req.HTTPError as e:
            # Non-retryable 4xx (except 429 handled above) propagates immediately
            debug_print("HTTP GET", url=url, timeout=f"{timeout}s", attempt=attempt_label, status=status, outcome="failed", error=f"{type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to fetch from Last.fm: {e}")
        if i < attempts - 1:
            delay = base_delay * (2 ** i)
            debug_print("Last.fm request retry", url=url, attempt=attempt_label, delay=f"{delay:g}s", status=status, outcome="failed")
            time.sleep(delay)
    raise RuntimeError(f"Failed to fetch from Last.fm after {attempts} attempts: {last_exc}")


# Parses the "(N)" suffix from the h1 header on a followers/following page and returns N as int or None if not found
def _lastfm_parse_count_from_h1(soup):
    for h1 in soup.find_all('h1'):
        txt = h1.get_text(' ', strip=True)
        m = re.search(r'\((\d+)\)', txt)
        if m:
            return int(m.group(1))
    return None


# Scrapes a user's followers or following list from Last.fm using structural selectors and cross-checks the parsed count against the page's own header count to avoid silent empty returns; kind must be 'followers' or 'following'
def _lastfm_scrape_user_list(username, kind):
    from bs4 import BeautifulSoup  # type: ignore

    if kind not in ('followers', 'following'):
        raise ValueError(f"Invalid kind: {kind!r}")

    url = f"https://www.last.fm/user/{quote_plus(username)}/{kind}"
    try:
        response = _lastfm_http_get_with_retry(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Authoritative count from the page's h1 (e.g. "Followers (1)" / "Following (1)")
        header_count = _lastfm_parse_count_from_h1(soup)
        if header_count is None:
            raise RuntimeError(f"Could not find {kind} count in page header (layout may have changed)")

        if header_count == 0:
            return set()

        # Structural container: ul.user-list > li.user-list-item, with ad items skipped
        users = set()
        for ul in soup.select('ul.user-list'):
            for li in ul.find_all('li', recursive=False):
                classes = li.get('class') or []
                if any('ad' in c.lower() for c in classes):
                    continue
                a = li.select_one('.user-list-name a[href^="/user/"]') or li.select_one('a[href^="/user/"]')
                if not a:
                    continue
                href = str(a.get('href', ''))
                parts = href.split('/')
                if len(parts) < 3 or parts[1] != 'user':
                    continue
                user_from_href = parts[2].split('?')[0].split('#')[0]
                if user_from_href and user_from_href.lower() != username.lower():
                    users.add(user_from_href)

        # Cross-check: the parsed set must match the authoritative header count; otherwise the page rendered unexpectedly and we must not silently return wrong data
        if len(users) != header_count:
            raise RuntimeError(
                f"Parsed {kind} count mismatch: header says {header_count}, parsed {len(users)} "
                f"(possible layout change, partial render, or bot-check page)"
            )

        return users
    except req.RequestException as e:
        raise RuntimeError(f"Failed to scrape {kind} from Last.fm: {e}")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to parse {kind} page: {e}")


# Returns a set of usernames that the user is following (friends) - scraped from web
def lastfm_get_friends(username):
    return _lastfm_scrape_user_list(username, 'following')


# Returns a set of usernames that are following the user (scraped from web)
def lastfm_get_followers(username):
    return _lastfm_scrape_user_list(username, 'followers')


# Converts profile bio markup into stable plain text while retaining block line breaks
def _lastfm_profile_bio_text(bio_element):
    if bio_element is None:
        return ''
    for line_break in bio_element.select('br'):
        line_break.replace_with('\n')
    for block in bio_element.select('p, div, li'):
        block.append('\n')
    lines = [re.sub(r'[ \t\f\v]+', ' ', line).strip() for line in bio_element.get_text().splitlines()]
    return '\n'.join(line for line in lines if line)


# Returns the current public display name and About Me bio scraped from the user's profile
def lastfm_get_profile(username):
    from bs4 import BeautifulSoup  # type: ignore

    url = f"https://www.last.fm/user/{quote_plus(username)}"
    try:
        response = _lastfm_http_get_with_retry(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        profile_username = soup.select_one('h1.header-title a[href^="/user/"]')
        if profile_username is None or profile_username.get_text(' ', strip=True).casefold() != username.casefold():
            raise RuntimeError("Could not validate the Last.fm profile owner (layout may have changed)")
        display_name_element = soup.select_one('.header-title-display-name')
        if display_name_element is None:
            raise RuntimeError("Could not find the display name (layout may have changed)")
        bio_element = soup.select_one('.about-me-header') or soup.select_one('.about-me-sidebar')
        return {
            'display_name': display_name_element.get_text(' ', strip=True),
            'bio': _lastfm_profile_bio_text(bio_element),
        }
    except req.RequestException as e:
        raise RuntimeError(f"Failed to scrape profile from Last.fm: {e}")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to parse profile page: {e}")


# Copies an existing file to a timestamped private backup before it is replaced, returning the backup path or None
def create_timestamped_backup(destination, attempts=100):
    destination_path = Path(destination).expanduser()
    if not destination_path.is_file():
        return None
    existing_bytes = destination_path.read_bytes()
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    for attempt in range(attempts):
        suffix = f".{stamp}.bak" if attempt == 0 else f".{stamp}-{attempt}.bak"
        backup_path = destination_path.with_name(destination_path.name + suffix)
        try:
            # O_EXCL so a backup can never overwrite an earlier one, even under a concurrent run
            descriptor = os.open(str(backup_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(descriptor, "wb") as backup_file:
                backup_file.write(existing_bytes)
                backup_file.flush()
                os.fsync(backup_file.fileno())
        except Exception:
            try:
                os.unlink(str(backup_path))
            except OSError as cleanup_error:
                debug_swallowed_exception("Failed backup cleanup", cleanup_error)
            raise
        debug_print("File backup", path=str(destination_path), backup=str(backup_path), outcome="OK")
        return str(backup_path)
    raise OSError(f"Could not create a unique backup for '{destination_path}' after {attempts} attempts")


# Writes one file through a temporary file in the same directory, so a crash cannot leave a half-written file
def write_file_atomically(destination, content, mode=None):
    destination_path = Path(destination).expanduser()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if mode is not None and os.name == "posix":
            os.chmod(str(temporary_path), mode)
        os.replace(str(temporary_path), str(destination_path))
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return str(destination_path)


# Saves one JSON state file atomically, so an interrupted run cannot strand a half-written file
def write_json_atomically(destination, payload, ensure_ascii=True):
    return write_file_atomically(destination, json.dumps(payload, indent=2, ensure_ascii=ensure_ascii) + "\n")


# Confirms replacing one existing generated config, or requires --force when there is nobody to ask
def confirm_generated_config_replacement(destination, force=False, interactive=None, input_func=input):
    destination_path = Path(destination).expanduser()
    if not destination_path.exists() or force:
        return True
    terminal_is_interactive = bool(sys.stdin.isatty()) if interactive is None else bool(interactive)
    if not terminal_is_interactive:
        raise FileExistsError(f"Config file '{destination_path}' already exists and there is no terminal to confirm replacing it")
    try:
        answer = str(read_interactively(input_func, f"Config file '{destination_path}' exists. Replace it and keep a timestamped backup? [y/N]: ")).strip().casefold()
    except (EOFError, KeyboardInterrupt):
        print()
        answer = ""
    return answer in ("y", "yes")


# Writes one generated config atomically, backing up whatever was there first
def write_generated_config(output_file, content, force=False, interactive=None, input_func=input):
    destination = Path(output_file).expanduser()
    if not confirm_generated_config_replacement(destination, force, interactive, input_func):
        return None, False
    backup_path = create_timestamped_backup(destination)
    write_file_atomically(destination, content)
    return backup_path, True


# Loads previous friends/followers state from JSON file
def load_friends_state(username, friends_type):
    filename = f"lastfm_{username}_{friends_type}.json"
    if os.path.isfile(filename):
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                data = json.load(f)
                saved_users = set(data) if isinstance(data, list) else set(data['users']) if isinstance(data, dict) and 'users' in data else set()
                debug_print("Friends state load", path=filename, type=friends_type, users=len(saved_users), outcome="OK")
                return saved_users
        except Exception as e:
            debug_print("Friends state load", path=filename, type=friends_type, outcome="failed", error=f"{type(e).__name__}: {e}")
            print_recovery_error(e, context="file", detail=f"Cannot load the {friends_type} state from '{filename}': {e}")
            return set()
    debug_print("Friends state load", path=filename, type=friends_type, outcome="skipped", reason="no saved state")
    return set()


# Saves current friends/followers state to JSON file
def save_friends_state(username, friends_type, users_set):
    filename = f"lastfm_{username}_{friends_type}.json"
    try:
        data = {
            'users': sorted(list(users_set)),
            'count': len(users_set),
            'last_updated': int(time.time())
        }
        write_json_atomically(filename, data)
        debug_print("Friends state write", path=filename, type=friends_type, users=len(users_set), outcome="OK")
    except Exception as e:
        debug_print("Friends state write", path=filename, type=friends_type, outcome="failed", error=f"{type(e).__name__}: {e}")
        print_recovery_error(e, context="file.unwritable", detail=f"Cannot save the {friends_type} state to '{filename}': {e}")


# Loads the saved profile fields used as the comparison baseline
def load_profile_state(username):
    filename = f"lastfm_{username}_profile.json"
    if not os.path.isfile(filename):
        return {}
    try:
        with open(filename, 'r', encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("profile state must be a JSON object")
        saved_profile = {key: data[key] for key in ('display_name', 'bio') if isinstance(data.get(key), str)}
        debug_print("Profile state load", path=filename, fields=len(saved_profile), outcome="OK")
        return saved_profile
    except Exception as e:
        debug_print("Profile state load", path=filename, outcome="failed", error=f"{type(e).__name__}: {e}")
        print_recovery_error(e, context="file", detail=f"Cannot load the profile state from '{filename}': {e}")
        return {}


# Saves tracked profile fields while retaining baselines for fields disabled during this run
def save_profile_state(username, profile):
    filename = f"lastfm_{username}_profile.json"
    try:
        data = load_profile_state(username)
        data.update({key: value for key, value in profile.items() if key in ('display_name', 'bio') and isinstance(value, str)})
        data['last_updated'] = int(time.time())
        write_json_atomically(filename, data, ensure_ascii=False)
        debug_print("Profile state write", path=filename, fields=len(profile), outcome="OK")
    except Exception as e:
        debug_print("Profile state write", path=filename, outcome="failed", error=f"{type(e).__name__}: {e}")
        print_recovery_error(e, context="file.unwritable", detail=f"Cannot save the profile state to '{filename}': {e}")


# Returns whether at least one friend or profile field is enabled for the shared timer
def friends_check_enabled():
    return TRACK_FOLLOWINGS or TRACK_FOLLOWERS or TRACK_BIO or TRACK_DISPLAY_NAME


# Persists the exact states produced by one successful shared timer check
def save_friends_check_states(username, current_states):
    for key in ('followings', 'followers'):
        if key in current_states:
            save_friends_state(username, key, current_states[key])
    if 'profile' in current_states:
        save_profile_state(username, current_states['profile'])


# Checks friends and profile fields then returns changes with the exact fetched states for later persistence
def check_friends_changes(username, track_followings, track_followers, track_bio=False, track_display_name=False, save_state=True, raise_on_error=False):
    changes = {}
    current_states = {}

    if track_followings:
        try:
            previous_friends = load_friends_state(username, 'followings')
            current_friends = lastfm_get_friends(username)
            current_states['followings'] = current_friends

            added_friends = current_friends - previous_friends
            removed_friends = previous_friends - current_friends

            if added_friends or removed_friends:
                changes['followings'] = {
                    'added': sorted(list(added_friends)),
                    'removed': sorted(list(removed_friends)),
                    'current_count': len(current_friends),
                    'previous_count': len(previous_friends)
                }

            if save_state:
                save_friends_state(username, 'followings', current_friends)
        except Exception as e:
            if raise_on_error:
                raise e
            verbose_degraded_feature("Followings check", "following change alerts", e)

    if track_followers:
        try:
            previous_followers = load_friends_state(username, 'followers')
            current_followers = lastfm_get_followers(username)
            current_states['followers'] = current_followers

            added_followers = current_followers - previous_followers
            removed_followers = previous_followers - current_followers

            if added_followers or removed_followers:
                changes['followers'] = {
                    'added': sorted(list(added_followers)),
                    'removed': sorted(list(removed_followers)),
                    'current_count': len(current_followers),
                    'previous_count': len(previous_followers)
                }

            if save_state:
                save_friends_state(username, 'followers', current_followers)
        except Exception as e:
            if raise_on_error:
                raise e
            verbose_degraded_feature("Followers check", "follower change alerts", e)

    if track_bio or track_display_name:
        try:
            previous_profile = load_profile_state(username)
            fetched_profile = lastfm_get_profile(username)
            current_profile = {}
            profile_changes = {}
            tracked_fields = (('display_name', track_display_name), ('bio', track_bio))
            for field, enabled in tracked_fields:
                if not enabled:
                    continue
                current_profile[field] = fetched_profile[field]
                if field in previous_profile and previous_profile[field] != fetched_profile[field]:
                    profile_changes[field] = {'previous': previous_profile[field], 'current': fetched_profile[field]}
            current_states['profile'] = current_profile
            if profile_changes:
                changes['profile'] = profile_changes
            if save_state:
                save_profile_state(username, current_profile)
        except Exception as e:
            if raise_on_error:
                raise e
            verbose_degraded_feature("Profile check", "profile change alerts", e)

    return changes, current_states


# Sends console and configured channel notifications for confirmed friend or profile changes
def notify_friends_changes(username, changes, skip_initial_line=False):
    if not changes:
        return

    current_time = int(time.time())
    check_interval_str = display_time(FRIENDS_CHECK_INTERVAL) if FRIENDS_CHECK_INTERVAL > 0 else "N/A"
    check_range = get_range_of_dates_from_tss(current_time - FRIENDS_CHECK_INTERVAL, current_time, short=True) if FRIENDS_CHECK_INTERVAL > 0 else ""

    # Handle followings changes
    if 'followings' in changes:
        f_changes = changes['followings']
        added = f_changes['added']
        removed = f_changes['removed']
        current_count = f_changes['current_count']
        previous_count = f_changes['previous_count']
        change_count = len(added) - len(removed)

        if not skip_initial_line:
            print("─" * HORIZONTAL_LINE)
        change_str = f"{change_count:+d}" if change_count != 0 else "0"
        print(f"* Followings number changed by user {username} from {previous_count} to {current_count} ({change_str})")

        if added:
            print(f"\nAdded followings:")
            print()
            for user in added:
                user_url = f"https://www.last.fm/user/{quote_plus(user)}"
                print(f"- {user} [ {user_url} ]")

        if removed:
            if not added:
                print()
            elif added:
                print()
            print(f"Removed followings:")
            print()
            for user in removed:
                user_url = f"https://www.last.fm/user/{quote_plus(user)}"
                print(f"- {user} [ {user_url} ]")

        if FOLLOWINGS_NOTIFICATION or webhook_event_enabled("followings"):
            change_str = f"{change_count:+d}" if change_count != 0 else "0"
            subject = f"Last.fm user {username} followings number has changed! ({change_str}, {previous_count} -> {current_count})"

            body_parts = []
            body_parts.append(f"Followings number changed by user {username} from {previous_count} to {current_count} ({change_str})")
            body_parts.append("")

            if added:
                body_parts.append("Added followings:")
                body_parts.append("")
                for user in added:
                    body_parts.append(f"- {user}")

            if removed:
                if added:
                    body_parts.append("")
                body_parts.append("Removed followings:")
                body_parts.append("")
                for user in removed:
                    body_parts.append(f"- {user}")

            body_parts.append("")
            if check_range:
                body_parts.append(f"Check interval: {check_interval_str} ({check_range})")
            body_parts.append(f"Timestamp: {get_cur_ts('')}")

            html_parts = []
            html_parts.append(f"Followings number changed by user <b>{escape(username)}</b> from <b>{previous_count}</b> to <b>{current_count}</b> (<b>{change_str}</b>)")
            html_parts.append("<br><br>")

            if added:
                html_parts.append("<b>Added followings:</b>")
                html_parts.append("<br><br>")
                for user in added:
                    user_url = f"https://www.last.fm/user/{quote_plus(user)}"
                    html_parts.append(f'- <a href="{user_url}">{escape(user)}</a><br>')

            if removed:
                if added:
                    html_parts.append("<br>")
                html_parts.append("<b>Removed followings:</b>")
                html_parts.append("<br><br>")
                for user in removed:
                    user_url = f"https://www.last.fm/user/{quote_plus(user)}"
                    html_parts.append(f'- <a href="{user_url}">{escape(user)}</a><br>')

            html_parts.append("<br>")
            if check_range:
                html_parts.append(f"Check interval: <b>{check_interval_str}</b> ({check_range})")
            html_parts.append(f"<br>Timestamp: {get_cur_ts('')}")

            body = "\n".join(body_parts)
            body_html = f"<html><head></head><body>{''.join(html_parts)}</body></html>"

            print()
            send_notification_channels("followings", subject, body, body_html, email_enabled=FOLLOWINGS_NOTIFICATION)

        if check_range:
            print(f"\nCheck interval:\t\t\t{check_interval_str} ({check_range})")
        print_cur_ts("Timestamp:\t\t\t")

    # Handle followers changes
    if 'followers' in changes:
        f_changes = changes['followers']
        added = f_changes['added']
        removed = f_changes['removed']
        current_count = f_changes['current_count']
        previous_count = f_changes['previous_count']
        change_count = len(added) - len(removed)

        if not skip_initial_line:
            print("─" * HORIZONTAL_LINE)
        change_str = f"{change_count:+d}" if change_count != 0 else "0"
        print(f"* Followers number changed for user {username} from {previous_count} to {current_count} ({change_str})")

        if added:
            print(f"\nAdded followers:")
            print()
            for user in added:
                user_url = f"https://www.last.fm/user/{quote_plus(user)}"
                print(f"- {user} [ {user_url} ]")

        if removed:
            if not added:
                print()
            elif added:
                print()
            print(f"Removed followers:")
            print()
            for user in removed:
                user_url = f"https://www.last.fm/user/{quote_plus(user)}"
                print(f"- {user} [ {user_url} ]")

        if FOLLOWERS_NOTIFICATION or webhook_event_enabled("followers"):
            change_str = f"{change_count:+d}" if change_count != 0 else "0"
            subject = f"Last.fm user {username} followers number has changed! ({change_str}, {previous_count} -> {current_count})"

            body_parts = []
            body_parts.append(f"Followers number changed for user {username} from {previous_count} to {current_count} ({change_str})")
            body_parts.append("")

            if added:
                body_parts.append("Added followers:")
                body_parts.append("")
                for user in added:
                    body_parts.append(f"- {user}")

            if removed:
                if added:
                    body_parts.append("")
                body_parts.append("Removed followers:")
                body_parts.append("")
                for user in removed:
                    body_parts.append(f"- {user}")

            body_parts.append("")
            if check_range:
                body_parts.append(f"Check interval: {check_interval_str} ({check_range})")
            body_parts.append(f"Timestamp: {get_cur_ts('')}")

            html_parts = []
            html_parts.append(f"Followers number changed for user <b>{escape(username)}</b> from <b>{previous_count}</b> to <b>{current_count}</b> (<b>{change_str}</b>)")
            html_parts.append("<br><br>")

            if added:
                html_parts.append("<b>Added followers:</b>")
                html_parts.append("<br><br>")
                for user in added:
                    user_url = f"https://www.last.fm/user/{quote_plus(user)}"
                    html_parts.append(f'- <a href="{user_url}">{escape(user)}</a><br>')

            if removed:
                if added:
                    html_parts.append("<br>")
                html_parts.append("<b>Removed followers:</b>")
                html_parts.append("<br><br>")
                for user in removed:
                    user_url = f"https://www.last.fm/user/{quote_plus(user)}"
                    html_parts.append(f'- <a href="{user_url}">{escape(user)}</a><br>')

            html_parts.append("<br>")
            if check_range:
                html_parts.append(f"Check interval: <b>{check_interval_str}</b> ({check_range})")
            html_parts.append(f"<br>Timestamp: {get_cur_ts('')}")

            body = "\n".join(body_parts)
            body_html = f"<html><head></head><body>{''.join(html_parts)}</body></html>"

            print()
            send_notification_channels("followers", subject, body, body_html, email_enabled=FOLLOWERS_NOTIFICATION)

        if check_range:
            print(f"\nCheck interval:\t\t\t{check_interval_str} ({check_range})")
        print_cur_ts("Timestamp:\t\t\t")

    # Handle public profile changes
    if 'profile' in changes:
        profile_changes = changes['profile']
        labels = {'display_name': 'Display name', 'bio': 'Bio'}
        if not skip_initial_line:
            print("─" * HORIZONTAL_LINE)
        print(f"* Public profile changed for user {username}")
        for field in ('display_name', 'bio'):
            if field not in profile_changes:
                continue
            field_change = profile_changes[field]
            previous_value = field_change['previous'] or "(empty)"
            current_value = field_change['current'] or "(empty)"
            print(f"\n{labels[field]} changed:")
            print(f"Previous: {previous_value}")
            print(f"Current: {current_value}")

        if PROFILE_NOTIFICATION or webhook_event_enabled("profile"):
            changed_labels = [labels[field].lower() for field in ('display_name', 'bio') if field in profile_changes]
            subject = f"Last.fm user {username} profile has changed! ({' and '.join(changed_labels)})"
            body_parts = [f"Public profile changed for user {username}", ""]
            html_parts = [f'Public profile changed for user <a href="https://www.last.fm/user/{quote_plus(username)}">{escape(username)}</a>', "<br><br>"]
            rendered_fields = []
            for field in ('display_name', 'bio'):
                if field not in profile_changes:
                    continue
                if rendered_fields:
                    body_parts.append("")
                    html_parts.append("<br>")
                field_change = profile_changes[field]
                previous_value = field_change['previous'] or "(empty)"
                current_value = field_change['current'] or "(empty)"
                body_parts.extend([f"{labels[field]} changed:", f"Previous: {previous_value}", f"Current: {current_value}"])
                previous_html = escape(previous_value).replace('\n', '<br>')
                current_html = escape(current_value).replace('\n', '<br>')
                html_parts.extend([f"<b>{labels[field]} changed:</b><br>", f"Previous: {previous_html}<br>", f"Current: {current_html}<br>"])
                rendered_fields.append(field)
            body_parts.append("")
            if check_range:
                body_parts.append(f"Check interval: {check_interval_str} ({check_range})")
                html_parts.append(f"<br>Check interval: <b>{check_interval_str}</b> ({check_range})")
            body_parts.append(f"Timestamp: {get_cur_ts('')}")
            html_parts.append(f"<br>Timestamp: {get_cur_ts('')}")
            body = "\n".join(body_parts)
            body_html = f"<html><head></head><body>{''.join(html_parts)}</body></html>"
            print()
            send_notification_channels("profile", subject, body, body_html, email_enabled=PROFILE_NOTIFICATION)

        if check_range:
            print(f"\nCheck interval:\t\t\t{check_interval_str} ({check_range})")
        print_cur_ts("Timestamp:\t\t\t")


# Displays the list of recently played Last.fm tracks
def lastfm_list_tracks(username, user, network, number, csv_file_name):

    list_operation = "* Listing & saving" if csv_file_name else "* Listing"

    print(f"{list_operation} {number} tracks recently listened by {username} ...\n")

    try:
        new_track = lastfm_get_now_playing(username, user)
        recent_tracks = lastfm_get_recent_tracks(username, network, number)
    except Exception as e:
        print_recovery_error(e, detail=f"Cannot read the recent tracks of '{username}'")
        sys.exit(1)

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print_recovery_error(e, context="file.unwritable")

    # Helper function to shorten strings in the middle
    def _shorten_middle(s, max_len, ellipsis="..."):
        if s is None:
            return ""
        s = str(s)
        if len(s) <= max_len:
            return s
        keep = max_len - len(ellipsis)
        if keep <= 0:
            return ellipsis[:max_len]
        left = keep // 2
        right = keep - left
        return f"{s[:left]}{ellipsis}{s[-right:]}"

    # Collect track data and identify duplicates
    track_entries = []
    last_played = 0
    p = 0
    duplicate_entries = False

    for previous, t, _nxt in previous_and_next(reversed(recent_tracks)):
        i = len(track_entries) + 1
        if i == len(recent_tracks):
            last_played = int(t.timestamp)

        artist = str(t.track.artist) if t.track.artist else ""
        title = str(t.track.title) if t.track.title else ""
        album = str(t.album) if t.album else ""
        timestamp = int(t.timestamp)
        date_str = datetime.fromtimestamp(timestamp).strftime("%d %b %Y, %H:%M:%S")
        day_str = calendar.day_abbr[datetime.fromtimestamp(timestamp).weekday()]

        is_duplicate = False
        if previous and previous.timestamp == t.timestamp:
            p += 1
            duplicate_entries = True
            is_duplicate = True

        track_entries.append({
            'num': i,
            'artist': artist,
            'title': title,
            'album': album,
            'date': date_str,
            'day': day_str,
            'is_duplicate': is_duplicate
        })

        try:
            if csv_file_name:
                write_csv_entry(csv_file_name, datetime.fromtimestamp(timestamp), artist, title, album)
        except Exception as e:
            print_recovery_error(e, context="file.unwritable")

    # Calculate column widths based on terminal size
    try:
        term_width = shutil.get_terminal_size(fallback=(100, 24)).columns
    except Exception as exc:
        debug_swallowed_exception("Terminal width probe", exc)
        term_width = 100

    w_num = 4
    w_day = 4
    w_date = 24

    # Find the maximum lengths needed for artist, title, and album
    max_artist_len = 0
    max_title_len = 0
    max_album_len = 0
    for entry in track_entries:
        artist_len = len(str(entry['artist'])) if entry['artist'] else 0
        title_len = len(str(entry['title'])) if entry['title'] else 0
        album_len = len(str(entry['album'])) if entry['album'] else 0
        if artist_len > max_artist_len:
            max_artist_len = artist_len
        if title_len > max_title_len:
            max_title_len = title_len
        if album_len > max_album_len:
            max_album_len = album_len

    # Calculate spacing and fixed widths for table width calculation
    # Format: "#  Day  Date/Time  Artist  Title  Album"
    # Total spacing: 2 + 2 + 2 + 2 + 2 = 10 spaces
    spacing_between_cols = 2
    total_spacing = 5 * spacing_between_cols  # 5 gaps between 6 columns
    fixed_cols_width = w_num + w_day + w_date

    # Calculate available width for variable columns (artist, title, album)
    available_width = term_width - fixed_cols_width - total_spacing

    # Allocate space: prioritize artist and title, but always ensure album is visible
    # Ensure minimum widths
    w_artist_min = 15
    w_title_min = 15
    w_album_min = 20  # Album must always be visible with at least this width

    # Calculate ideal widths (what we'd like if we had unlimited space)
    ideal_artist = max(w_artist_min, max_artist_len)
    ideal_title = max(w_title_min, max_title_len)
    ideal_album = max(w_album_min, max_album_len)

    # Strategy: Always reserve minimum for album, then prioritize artist and title
    # First, ensure we have enough space for minimums
    min_total_needed = w_artist_min + w_title_min + w_album_min
    if available_width < min_total_needed:
        # Very narrow terminal: scale everything proportionally but keep minimums
        scale = available_width / min_total_needed
        w_artist = max(10, int(w_artist_min * scale))  # Absolute minimum 10
        w_title = max(10, int(w_title_min * scale))
        w_album = max(10, int(w_album_min * scale))
        # Distribute any remainder
        remaining = available_width - (w_artist + w_title + w_album)
        if remaining > 0:
            # Give remainder to title (highest priority after artist)
            w_title += remaining
    else:
        # We have at least minimum space - allocate intelligently
        # Always reserve minimum for album first
        space_for_artist_title = available_width - w_album_min

        # Calculate ideal needs for artist and title
        if max_artist_len < w_artist_min:
            # Artist is shorter than minimum - use actual length, give extra to title
            ideal_artist_actual = max_artist_len
            extra_for_title = w_artist_min - max_artist_len
            ideal_title_actual = max(w_title_min, max_title_len + extra_for_title)
        else:
            ideal_artist_actual = ideal_artist
            ideal_title_actual = ideal_title

        ideal_artist_title_needed = ideal_artist_actual + ideal_title_actual

        if space_for_artist_title >= ideal_artist_title_needed:
            # Plenty of space: give artist and title their ideal lengths
            w_artist = ideal_artist_actual
            w_title = ideal_title_actual
            # Album gets what's left (at least minimum, up to ideal)
            remaining_for_album = available_width - (w_artist + w_title)
            w_album = min(ideal_album, remaining_for_album)
        elif space_for_artist_title >= w_artist_min + w_title_min:
            # Can fit minimums, but need to scale artist/title proportionally
            if max_artist_len + max_title_len > 0:
                # Scale proportionally based on their ideal lengths
                total_ideal = ideal_artist_actual + ideal_title_actual
                w_artist = int(ideal_artist_actual * space_for_artist_title / total_ideal)
                # Ensure minimums
                if max_artist_len < w_artist_min:
                    w_artist = min(w_artist, max_artist_len)
                else:
                    w_artist = max(w_artist, w_artist_min)
                w_title = max(w_title_min, space_for_artist_title - w_artist)
                # Use all available space
                if w_artist + w_title < space_for_artist_title:
                    w_title = space_for_artist_title - w_artist
            else:
                w_artist = w_artist_min if max_artist_len >= w_artist_min else max_artist_len
                w_title = w_title_min
            w_album = w_album_min
        else:
            # Very constrained: use minimums for all
            w_artist = w_artist_min if max_artist_len >= w_artist_min else max_artist_len
            w_title = w_title_min
            w_album = w_album_min

    # Final verification: ensure total width doesn't exceed terminal width
    total_row_width = w_num + w_day + w_date + w_artist + w_title + w_album + total_spacing
    if total_row_width > term_width:
        # We need to reduce, but album must stay at minimum
        excess = total_row_width - term_width
        # Try to reduce album first, but not below minimum
        if w_album > w_album_min:
            reduction = min(excess, w_album - w_album_min)
            w_album -= reduction
            excess -= reduction

        # If still too wide, reduce artist and title proportionally
        if excess > 0:
            total_row_width = w_num + w_day + w_date + w_artist + w_title + w_album + total_spacing
            if total_row_width > term_width:
                excess = total_row_width - term_width
                current_artist_title = w_artist + w_title
                if current_artist_title > excess:
                    # Scale proportionally, but ensure album stays at minimum
                    scale = (current_artist_title - excess) / current_artist_title
                    w_artist = max(10, int(w_artist * scale))  # Absolute minimum 10
                    w_title = max(10, int(w_title * scale))
                    # Ensure album is at minimum
                    w_album = w_album_min

    # Print table header
    if track_entries:
        print()
        hdr = colorize("section", (
            f"{'#'.ljust(w_num)}  "
            f"{'Day'.ljust(w_day)}  "
            f"{'Date/Time'.ljust(w_date)}  "
            f"{'Artist'.ljust(w_artist)}  "
            f"{'Title'.ljust(w_title)}  "
            f"{'Album'.ljust(w_album)}"
        ))
        sep = (
            f"{'-' * w_num}  "
            f"{'-' * w_day}  "
            f"{'-' * w_date}  "
            f"{'-' * w_artist}  "
            f"{'-' * w_title}  "
            f"{'-' * w_album}"
        )
        print(hdr)
        print(sep)

        # Print table rows
        for entry in track_entries:
            # For duplicates, reserve space for [DUP] prefix
            dup_prefix_len = 6  # "[DUP] "
            if entry['is_duplicate']:
                artist_fmt = _shorten_middle(entry['artist'], w_artist - dup_prefix_len)
                title_fmt = _shorten_middle(entry['title'], w_title - dup_prefix_len)
                artist_fmt = f"[DUP] {artist_fmt}"
                title_fmt = f"[DUP] {title_fmt}"
            else:
                artist_fmt = _shorten_middle(entry['artist'], w_artist)
                title_fmt = _shorten_middle(entry['title'], w_title)
            album_fmt = _shorten_middle(entry['album'], w_album)

            # Each cell is padded first and coloured second, so a colour code never counts toward a column width
            row = (
                f"{str(entry['num']).ljust(w_num)}  "
                f"{colorize('date', entry['day'].ljust(w_day))}  "
                f"{colorize('date', entry['date'].ljust(w_date))}  "
                f"{colorize('artist', artist_fmt.ljust(w_artist))}  "
                f"{colorize('track', title_fmt.ljust(w_title))}  "
                f"{colorize('album', album_fmt.ljust(w_album))}"
            )
            print(row)

    # Use the calculated table width for the horizontal line
    print("─" * total_row_width)
    if last_played > 0 and not new_track:
        print(f"*** User played last time {calculate_timespan(int(time.time()), last_played, show_seconds=True)} ago! ({get_date_from_ts(last_played)})")

    if duplicate_entries:
        print(f"*** Duplicate entries ({p}) found, possible PRIVATE MODE")

    if new_track:
        artist = str(new_track.artist)
        track = str(new_track.title)
        album = str(new_track.info.get('album', '')) if new_track.info.get('album') else ""
        print("*** User is currently ACTIVE !")
        print(f"\nTrack:\t\t{artist} - {track}")
        if album:
            print(f"Album:\t\t{album}")


# Reports whether complete non-placeholder Spotify OAuth app credentials are configured
def spotify_oauth_app_configured():
    invalid_client_ids = ("", "your_spotify_app_client_id")
    invalid_client_secrets = ("", "your_spotify_app_client_secret")
    return SP_CLIENT_ID not in invalid_client_ids and SP_CLIENT_SECRET not in invalid_client_secrets


# Returns an expiration-aware Spotify OAuth app token through Spotipy's cache handler
def spotify_get_access_token(sp_client_id, sp_client_secret):
    global SP_OAUTH_MEMORY_CACHE_HANDLER
    try:
        from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler
        from spotipy.oauth2 import SpotifyClientCredentials
    except ImportError as error:
        raise RuntimeError("Spotipy is required for the Spotify OAuth app backend") from error

    if SP_TOKENS_FILE:
        cache_handler = CacheFileHandler(cache_path=SP_TOKENS_FILE)
        cache_description = "file"
    else:
        if SP_OAUTH_MEMORY_CACHE_HANDLER is None:
            SP_OAUTH_MEMORY_CACHE_HANDLER = MemoryCacheHandler()
        cache_handler = SP_OAUTH_MEMORY_CACHE_HANDLER
        cache_description = "memory"

    # Spotipy accepts a Session here and only falls back to building its own when this is a bool, which its annotation does not express
    auth_manager = SpotifyClientCredentials(client_id=sp_client_id, client_secret=sp_client_secret, requests_timeout=FUNCTION_TIMEOUT, cache_handler=cache_handler, requests_session=SPOTIFY_SESSION)  # pyright: ignore[reportArgumentType]
    access_token = auth_manager.get_access_token(as_dict=False)
    if not access_token:
        raise RuntimeError("Spotify OAuth app token response was empty")
    debug_print("Spotify OAuth app token", cache=cache_description, token_len=len(access_token), outcome="OK")
    return access_token


# Fetches Spotify edge-server Unix time for anonymous token generation
def spotify_fetch_server_time(session=SPOTIFY_SESSION):
    headers = {"Accept": "*/*", "User-Agent": SPOTIFY_WEB_USER_AGENT}
    response = session.head(SPOTIFY_SERVER_TIME_URL, headers=headers, timeout=FUNCTION_TIMEOUT)
    debug_print("HTTP HEAD", url=SPOTIFY_SERVER_TIME_URL, purpose="Spotify server time", timeout=f"{FUNCTION_TIMEOUT}s", status=response.status_code, outcome="OK" if response.status_code < 400 else "failed")
    response.raise_for_status()
    date_header = response.headers.get("Date")
    if not date_header:
        raise RuntimeError("Spotify server-time response is missing the Date header")
    return int(parsedate_to_datetime(date_header).timestamp())


# Builds a pyotp TOTP object from the configured Spotify web-player cipher bytes
def generate_totp():
    cipher_bytes = SPOTIFY_TOTP_SECRET_CIPHER_BYTES
    if not cipher_bytes or not all(isinstance(value, int) and not isinstance(value, bool) for value in cipher_bytes):
        raise ValueError("SPOTIFY_TOTP_SECRET_CIPHER_BYTES must be a non-empty sequence of integers; refresh it with the spotify_monitor_secret_grabber tool if Spotify rotated the web-player secret")
    if not isinstance(SPOTIFY_TOTP_VERSION, int) or isinstance(SPOTIFY_TOTP_VERSION, bool) or SPOTIFY_TOTP_VERSION <= 0:
        raise ValueError("SPOTIFY_TOTP_VERSION must be a positive integer; refresh it with the spotify_monitor_secret_grabber tool if Spotify rotated the web-player secret")

    transformed = [value ^ ((index % 33) + 9) for index, value in enumerate(cipher_bytes)]
    joined = "".join(str(number) for number in transformed)
    hex_string = joined.encode().hex()
    secret = base64.b32encode(bytes.fromhex(hex_string)).decode().rstrip("=")
    return pyotp.TOTP(secret, digits=6, interval=30)


# Requests a fresh anonymous Spotify web-player access token
def spotify_refresh_web_access_token(session=SPOTIFY_SESSION):
    server_time = spotify_fetch_server_time(session)
    otp_value = generate_totp().at(server_time)
    headers = {"Accept": "application/json", "App-Platform": "WebPlayer", "Referer": SPOTIFY_WEB_PLAYER_URL, "User-Agent": SPOTIFY_WEB_USER_AGENT}
    last_error = ""

    for reason in ("transport", "init"):
        params = {"productType": "web-player", "reason": reason, "totp": otp_value, "totpServer": otp_value, "totpVer": SPOTIFY_TOTP_VERSION}
        try:
            response = session.get(SPOTIFY_TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT)
            debug_print("HTTP GET", url=SPOTIFY_TOKEN_URL, purpose="Spotify anonymous web token", reason=reason, timeout=f"{FUNCTION_TIMEOUT}s", status=response.status_code, outcome="OK" if response.status_code < 400 else "failed")
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                last_error = "invalid token data"
                continue
            access_token = data.get("accessToken", "")
            expires_at = int(data.get("accessTokenExpirationTimestampMs", 0) / 1000)
            client_id = data.get("clientId", "")
            if access_token and expires_at and client_id:
                debug_print("Spotify anonymous web token", token_len=len(access_token), outcome="OK")
                return {"access_token": access_token, "client_id": client_id, "expires_at": expires_at}
            last_error = "incomplete token data"
        except (req.RequestException, TypeError, ValueError) as error:
            last_error = type(error).__name__
            debug_print("Spotify anonymous web token", reason=reason, outcome="failed", error=f"{type(error).__name__}: {error}")

    raise RuntimeError(f"Spotify anonymous web-player token request failed: {last_error or 'unknown error'}")


# Returns a cached or freshly generated anonymous Spotify web-player token
def spotify_get_web_access_token_data():
    global SP_CACHED_WEB_ACCESS_TOKEN, SP_WEB_ACCESS_TOKEN_EXPIRES_AT, SP_CACHED_WEB_CLIENT_ID
    now = time.time()
    if SP_CACHED_WEB_ACCESS_TOKEN and SP_CACHED_WEB_CLIENT_ID and now < SP_WEB_ACCESS_TOKEN_EXPIRES_AT - SPOTIFY_WEB_TOKEN_EXPIRY_WINDOW:
        debug_print("Spotify anonymous web token", source="cache", outcome="OK")
        return {"access_token": SP_CACHED_WEB_ACCESS_TOKEN, "client_id": SP_CACHED_WEB_CLIENT_ID, "expires_at": SP_WEB_ACCESS_TOKEN_EXPIRES_AT}

    token_data = spotify_refresh_web_access_token()
    SP_CACHED_WEB_ACCESS_TOKEN = token_data["access_token"]
    SP_CACHED_WEB_CLIENT_ID = token_data["client_id"]
    SP_WEB_ACCESS_TOKEN_EXPIRES_AT = token_data["expires_at"]
    return token_data


# Clears the cached hash for one Spotify Pathfinder operation
def spotify_clear_web_query_hash(operation_name):
    global SP_CACHED_TRACK_QUERY_HASH, SP_CACHED_SEARCH_QUERY_HASH
    if operation_name == "getTrack":
        SP_CACHED_TRACK_QUERY_HASH = ""
    elif operation_name == "assistedCurationSearch":
        SP_CACHED_SEARCH_QUERY_HASH = ""
    else:
        raise ValueError(f"Unsupported Spotify web-player operation: {operation_name}")


# Discovers and caches persisted-query hashes from the current Spotify web-player bundle
def spotify_discover_web_query_hash(operation_name, force=False):
    global SP_CACHED_TRACK_QUERY_HASH, SP_CACHED_SEARCH_QUERY_HASH
    if operation_name == "getTrack":
        cached_hash = SP_CACHED_TRACK_QUERY_HASH
    elif operation_name == "assistedCurationSearch":
        cached_hash = SP_CACHED_SEARCH_QUERY_HASH
    else:
        raise ValueError(f"Unsupported Spotify web-player operation: {operation_name}")

    if cached_hash and not force:
        return cached_hash

    headers = {"Accept": "text/html,application/xhtml+xml", "User-Agent": SPOTIFY_WEB_USER_AGENT}
    response = SPOTIFY_SESSION.get(SPOTIFY_WEB_PLAYER_URL, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    debug_print("HTTP GET", url=SPOTIFY_WEB_PLAYER_URL, purpose="Spotify query discovery", query=operation_name, timeout=f"{FUNCTION_TIMEOUT}s", status=response.status_code, outcome="OK" if response.status_code < 400 else "failed")
    response.raise_for_status()

    script_urls = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', response.text, flags=re.IGNORECASE)
    bundle_url = ""
    for script_url in script_urls:
        if re.search(r'/web-player/web-player\.[^/?]+\.js(?:\?|$)', script_url):
            bundle_url = urljoin(SPOTIFY_WEB_PLAYER_URL, script_url)
            break
    if not bundle_url:
        raise RuntimeError("Cannot find the Spotify desktop web-player JavaScript bundle")

    bundle_response = SPOTIFY_SESSION.get(bundle_url, headers={"User-Agent": SPOTIFY_WEB_USER_AGENT}, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    debug_print("HTTP GET", url=bundle_url, purpose="Spotify query bundle", query=operation_name, timeout=f"{FUNCTION_TIMEOUT}s", status=bundle_response.status_code, outcome="OK" if bundle_response.status_code < 400 else "failed")
    bundle_response.raise_for_status()

    discovered_hashes = {}
    for discovered_operation in ("getTrack", "assistedCurationSearch"):
        hash_match = re.search(rf'["\']{re.escape(discovered_operation)}["\']\s*,\s*["\']query["\']\s*,\s*["\']([0-9a-f]{{64}})["\']', bundle_response.text)
        if hash_match and discovered_operation == "getTrack":
            SP_CACHED_TRACK_QUERY_HASH = hash_match.group(1)
            discovered_hashes[discovered_operation] = hash_match.group(1)
        elif hash_match:
            SP_CACHED_SEARCH_QUERY_HASH = hash_match.group(1)
            discovered_hashes[discovered_operation] = hash_match.group(1)

    discovered_hash = discovered_hashes.get(operation_name, "")
    if not discovered_hash:
        raise RuntimeError(f"Cannot find the {operation_name} persisted-query hash in the Spotify web-player bundle")
    debug_print("Spotify persisted-query hash discovery", query=operation_name, bundle=bundle_url, outcome="OK")
    return discovered_hash


# Discovers and caches the getTrack persisted-query hash
def spotify_discover_track_query_hash(force=False):
    return spotify_discover_web_query_hash("getTrack", force)


# Discovers and caches the anonymous search persisted-query hash
def spotify_discover_search_query_hash(force=False):
    return spotify_discover_web_query_hash("assistedCurationSearch", force)


# Executes a Spotify Pathfinder query with one token refresh and one hash refresh
def spotify_web_metadata_query(operation_name, variables):
    global SP_CACHED_WEB_ACCESS_TOKEN, SP_WEB_ACCESS_TOKEN_EXPIRES_AT, SP_CACHED_WEB_CLIENT_ID
    token_refreshed = False
    hash_refreshed = False
    force_query_hash = False
    last_error = ""

    for _ in range(3):
        token_data = spotify_get_web_access_token_data()
        query_hash = spotify_discover_web_query_hash(operation_name, force=force_query_hash)
        force_query_hash = False
        headers = {"Accept": "application/json", "App-Platform": "WebPlayer", "Authorization": f"Bearer {token_data['access_token']}", "Client-Id": token_data["client_id"], "Content-Type": "application/json", "User-Agent": SPOTIFY_WEB_USER_AGENT}
        payload = {"extensions": {"persistedQuery": {"sha256Hash": query_hash, "version": 1}}, "operationName": operation_name, "variables": variables}
        response = SPOTIFY_SESSION.post(SPOTIFY_WEB_QUERY_URL, headers=headers, json=payload, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print("HTTP POST", url=SPOTIFY_WEB_QUERY_URL, purpose="Spotify web metadata", query=operation_name, timeout=f"{FUNCTION_TIMEOUT}s", status=response.status_code, outcome="OK" if response.status_code < 400 else "failed")

        try:
            json_response = response.json()
        except ValueError:
            response.raise_for_status()
            raise RuntimeError(f"Spotify web-player operation '{operation_name}' returned invalid JSON")

        errors = json_response.get("errors") if isinstance(json_response, dict) else None
        error_message = " | ".join(str(error.get("message", error)) if isinstance(error, dict) else str(error) for error in (errors or []))
        last_error = error_message or f"HTTP {response.status_code}"

        if response.status_code == 401 and not token_refreshed:
            SP_CACHED_WEB_ACCESS_TOKEN = None
            SP_WEB_ACCESS_TOKEN_EXPIRES_AT = 0
            SP_CACHED_WEB_CLIENT_ID = ""
            token_refreshed = True
            debug_print("Spotify anonymous web token refresh", query=operation_name, reason="token rejected", outcome="degraded")
            continue

        persisted_query_rejected = bool(errors) and any(marker in error_message.lower() for marker in ("persistedquery", "persisted query", "sha256"))
        if persisted_query_rejected and not hash_refreshed:
            spotify_clear_web_query_hash(operation_name)
            hash_refreshed = True
            force_query_hash = True
            debug_print("Spotify persisted-query hash refresh", query=operation_name, reason="query rejected", outcome="degraded")
            continue

        if errors:
            raise RuntimeError(f"Spotify web-player operation '{operation_name}' failed: {error_message}")

        response.raise_for_status()
        data = json_response.get("data") if isinstance(json_response, dict) else None
        if not isinstance(data, dict):
            raise RuntimeError(f"Spotify web-player operation '{operation_name}' returned no data")
        return data

    raise RuntimeError(f"Spotify web-player operation '{operation_name}' failed after refresh: {last_error}")


# Builds a Spotify share URL from web-player data or an entity URI
def spotify_get_web_entity_url(entity, uri):
    sharing_info = entity.get("sharingInfo") or {} if isinstance(entity, dict) else {}
    share_url = sharing_info.get("shareUrl", "") if isinstance(sharing_info, dict) else ""
    return share_url or spotify_convert_uri_to_url(uri)


# Normalizes Spotify getTrack data to the legacy track item shape
def spotify_normalize_web_track(track):
    if not isinstance(track, dict) or track.get("__typename") != "Track":
        raise ValueError("Spotify web-player track data is missing or malformed")

    duration_data = track.get("duration") or track.get("trackDuration") or {}
    duration_ms = duration_data.get("totalMilliseconds") if isinstance(duration_data, dict) else None
    track_uri = track.get("uri", "")
    track_name = track.get("name")
    if duration_ms is None or not track_uri.startswith("spotify:track:") or not track_name:
        raise ValueError("Spotify web-player track metadata is incomplete")

    artist_items = []
    for artist_group_name in ("firstArtist", "otherArtists"):
        artist_group = track.get(artist_group_name) or {}
        if isinstance(artist_group, dict):
            artist_items.extend(artist_group.get("items") or [])

    artists = []
    seen_artist_uris = set()
    for artist in artist_items:
        if not isinstance(artist, dict):
            continue
        artist_profile = artist.get("profile") or {}
        artist_name = artist_profile.get("name") if isinstance(artist_profile, dict) else None
        artist_uri = artist.get("uri", "")
        if artist_name and artist_uri not in seen_artist_uris:
            artists.append({"external_urls": {"spotify": spotify_get_web_entity_url(artist, artist_uri)}, "name": artist_name, "uri": artist_uri})
            seen_artist_uris.add(artist_uri)
    if not artists:
        raise ValueError("Spotify web-player track artist is missing or malformed")

    album = track.get("albumOfTrack") or {}
    if not isinstance(album, dict):
        album = {}
    album_uri = album.get("uri", "")
    return {"album": {"external_urls": {"spotify": spotify_get_web_entity_url(album, album_uri)}, "name": album.get("name", ""), "uri": album_uri}, "artists": artists, "duration_ms": int(duration_ms), "external_urls": {"spotify": spotify_get_web_entity_url(track, track_uri)}, "id": track_uri.rsplit(":", 1)[-1], "name": track_name, "uri": track_uri}


# Fetches and normalizes public track metadata from Spotify Pathfinder
def spotify_get_track_info_web(track_uri):
    data = spotify_web_metadata_query("getTrack", {"uri": track_uri})
    return spotify_normalize_web_track(data.get("trackUnion"))


# Returns public Spotify track URIs for a web-player search term
def spotify_web_search_track_uris(search_term):
    variables = {"limit": 5, "numberOfTopResults": 5, "term": search_term}
    data = spotify_web_metadata_query("assistedCurationSearch", variables)
    search_data = data.get("searchV2") or {}
    track_items = (search_data.get("tracksV2") or {}).get("items") or [] if isinstance(search_data, dict) else []
    track_uris = []
    for item in track_items:
        item_data = (item.get("item") or {}).get("data") or {} if isinstance(item, dict) else {}
        track_uri = item_data.get("uri", "") if isinstance(item_data, dict) else ""
        if track_uri.startswith("spotify:track:") and track_uri not in track_uris:
            track_uris.append(track_uri)
    debug_print("Spotify anonymous search", term=search_term, tracks=len(track_uris), outcome="OK")
    return track_uris


# Converts Spotify URI (e.g. spotify:user:username) to URL (e.g. https://open.spotify.com/user/username)
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


# Processes normalized Spotify track items returned by web-player search
def spotify_search_process_track_items(track_items, original_artist, original_track, cleaned_track=None, original_album=None):
    sp_track_uri_id = None
    sp_track_duration = 0

    best_item = None
    best_score = -1

    for item in track_items:
        item_name = str(item.get("name"))
        item_artists_list = [a.get("name") for a in item.get("artists", [])]
        item_artists_str = ", ".join(item_artists_list)
        item_album_name = item.get("album", {}).get("name", "")
        item_duration = int(item.get("duration_ms", 0) / 1000)
        exact_track_match = item_name.casefold() == original_track.casefold()
        cleaned_track_match = bool(cleaned_track and item_name.casefold() == cleaned_track.casefold())
        album_match = bool(original_album and item_album_name and item_album_name.casefold() == original_album.casefold())

        debug_print("Spotify search candidate", artist=item_artists_str, track=item_name, album=item_album_name, duration=f"{item_duration}s")

        # Artist match check
        artist_match = any(original_artist.casefold() in a.casefold() for a in item_artists_list)
        alias_match = exact_track_match and album_match
        if not artist_match and not alias_match:
            debug_print("Spotify search candidate", track=item_name, outcome="skipped", reason="artist mismatch")
            continue
        if not artist_match:
            debug_print("Spotify search candidate", track=item_name, outcome="OK", reason="artist alias matched through exact track and album")

        score = 0
        if exact_track_match:
            score = 100  # Perfect match with original name
        elif cleaned_track_match:
            score = 80   # Match with cleaned name
        elif original_track.casefold() in item_name.casefold() or item_name.casefold() in original_track.casefold():
            score = 50   # Partial match

        # Album match bonus (+20 points)
        if album_match:
            score += 20
            debug_print("Spotify search candidate scoring", track=item_name, bonus="album match", outcome="OK")

        if score > best_score:
            best_score = score
            best_item = item
            debug_print("Spotify search candidate scoring", track=item_name, score=score, best=True, outcome="OK")
        else:
            debug_print("Spotify search candidate scoring", track=item_name, score=score, best=False, outcome="OK")

    if best_item and best_score > 0:
        sp_track_uri_id = best_item.get("id")
        sp_track_duration = int(best_item.get("duration_ms", 0) / 1000)

    return sp_track_uri_id, sp_track_duration


# Returns normalized Spotify Web API search items for one OAuth app strategy
def spotify_oauth_search_track_items(access_token, search_query, strategy):
    headers = {"Authorization": f"Bearer {access_token}", "User-Agent": SPOTIFY_WEB_USER_AGENT}
    params = {"q": search_query, "type": "track", "limit": 5}
    response = req.get(SPOTIFY_OAUTH_SEARCH_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    debug_print("HTTP GET", url=SPOTIFY_OAUTH_SEARCH_URL, purpose="Spotify OAuth app search", strategy=strategy, timeout=f"{FUNCTION_TIMEOUT}s", status=response.status_code, outcome="OK" if response.status_code < 400 else "failed")
    response.raise_for_status()
    json_response = response.json()
    tracks = json_response.get("tracks") if isinstance(json_response, dict) else None
    if not isinstance(tracks, dict):
        raise RuntimeError("Spotify OAuth app search returned no track collection")
    items = tracks.get("items") or []
    debug_print("Spotify OAuth app search", strategy=strategy, tracks=len(items), outcome="OK")
    return items


# Resolves a Spotify track ID and duration through official OAuth app search
def spotify_search_song_trackid_duration_oauth(access_token, artist, track, album=""):
    artist, track = map(str, (artist, track))
    album = str(album) if album else ""
    quote_chars = r'(["\'])'
    artist_sanitized = re.sub(quote_chars, '', artist, flags=re.IGNORECASE)
    track_sanitized = re.sub(quote_chars, '', track, flags=re.IGNORECASE)
    album_sanitized = re.sub(quote_chars, '', album, flags=re.IGNORECASE)
    track_cleaned = ""
    if re.search(re_search_str, track, re.IGNORECASE):
        track_cleaned = re.sub(re_replace_str, '', track, flags=re.IGNORECASE).strip()
        track_cleaned = re.sub(quote_chars, '', track_cleaned, flags=re.IGNORECASE)

    strategies = []
    if album_sanitized:
        strategies.append(("specific_full", f'artist:"{artist_sanitized}" track:"{track_sanitized}" album:"{album_sanitized}"'))
    strategies.append(("specific_field", f'artist:"{artist_sanitized}" track:"{track_sanitized}"'))
    strategies.append(("specific_phrase", f'"{artist_sanitized}" "{track_sanitized}"'))
    if track_cleaned and track_cleaned.casefold() != track_sanitized.casefold():
        strategies.append(("cleaned_field", f'artist:"{artist_sanitized}" track:"{track_cleaned}"'))
    strategies.append(("broad", f'"{artist_sanitized}" "{track_cleaned or track_sanitized}"'))

    for strategy, search_query in dict.fromkeys(strategies):
        try:
            track_items = spotify_oauth_search_track_items(access_token, search_query, strategy)
        except (req.RequestException, RuntimeError, TypeError, ValueError) as error:
            debug_print("Spotify OAuth app search", strategy=strategy, outcome="failed", error=f"{type(error).__name__}: {error}")
            continue
        sp_track_uri_id, sp_track_duration = spotify_search_process_track_items(track_items, artist, track, cleaned_track=track_cleaned or None, original_album=album)
        if sp_track_uri_id:
            debug_print("Spotify OAuth app metadata match", track_id=sp_track_uri_id, duration=f"{sp_track_duration}s", outcome="OK")
            return sp_track_uri_id, sp_track_duration

    return None, 0


# Returns a matching Spotify track ID and duration through anonymous web-player queries
def spotify_search_song_trackid_duration(artist, track, album=""):
    artist, track = map(str, (artist, track))
    album = str(album) if album else ""

    track_cleaned = ""
    if re.search(re_search_str, track, re.IGNORECASE):
        track_cleaned = re.sub(re_replace_str, '', track, flags=re.IGNORECASE).strip()

    search_terms = []
    if album:
        search_terms.append(f"{artist} {track} {album}")
    search_terms.append(f"{artist} {track}")
    if track_cleaned and track_cleaned.lower() != track.lower():
        search_terms.append(f"{artist} {track_cleaned}")

    for search_term in dict.fromkeys(search_terms):
        debug_print("Spotify anonymous web metadata search", artist=artist, track=track, album=album)
        track_items = []
        for track_uri in spotify_web_search_track_uris(search_term):
            try:
                track_items.append(spotify_get_track_info_web(track_uri))
            except (req.RequestException, RuntimeError, TypeError, ValueError) as error:
                debug_print("Spotify getTrack candidate", outcome="failed", error=f"{type(error).__name__}: {error}")

        sp_track_uri_id, sp_track_duration = spotify_search_process_track_items(track_items, artist, track, cleaned_track=track_cleaned or None, original_album=album)
        if sp_track_uri_id:
            debug_print("Spotify anonymous web metadata match", track_id=sp_track_uri_id, duration=f"{sp_track_duration}s", outcome="OK")
            return sp_track_uri_id, sp_track_duration

    return None, 0


# Resolves Spotify metadata through OAuth app search then anonymous web-player search
def spotify_resolve_track_metadata(artist, track, album=""):
    sp_track_uri_id = None
    sp_track_duration = 0

    if spotify_oauth_app_configured():
        try:
            access_token = spotify_get_access_token(SP_CLIENT_ID, SP_CLIENT_SECRET)
            sp_track_uri_id, sp_track_duration = spotify_search_song_trackid_duration_oauth(access_token, artist, track, album)
            debug_print("Spotify OAuth app metadata", track_id=sp_track_uri_id, duration=f"{sp_track_duration}s", outcome="OK")
        except Exception as error:
            debug_print("Spotify OAuth app metadata", outcome="failed", error=f"{type(error).__name__}: {error}")

    if not sp_track_uri_id or sp_track_duration <= 0:
        try:
            web_track_uri_id, web_track_duration = spotify_search_song_trackid_duration(artist, track, album)
            debug_print("Spotify anonymous web metadata", track_id=web_track_uri_id, duration=f"{web_track_duration}s", outcome="OK")
            if web_track_uri_id:
                sp_track_uri_id = web_track_uri_id
            if web_track_duration > 0:
                sp_track_duration = web_track_duration
        except Exception as error:
            debug_print("Spotify anonymous web metadata", outcome="failed", error=f"{type(error).__name__}: {error}")

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
        # os.startfile exists only on Windows, so the lookup stays dynamic to keep the type checker quiet on other platforms
        getattr(os, "startfile")(spotify_convert_uri_to_url(f"spotify:track:{sp_track_uri_id}"))  # noqa: B009


# Raised when private values cannot be checked or saved safely
class PrivateSettingsError(Exception):
    pass


# Resolves a writable dotenv destination without searching parent directories
def resolve_private_settings_path(env_file=None, cwd=None) -> Path:
    if env_file is not None and str(env_file).casefold() == "none":
        raise PrivateSettingsError("Private setup requires a dotenv destination and cannot use --env-file none")
    base_directory = Path.cwd() if cwd is None else Path(cwd)
    destination = base_directory / ".env" if not env_file else Path(env_file).expanduser()
    return destination.resolve()


# Checks whether a dotenv file already contains one named assignment
def _dotenv_contains_key(destination, key) -> bool:
    destination_path = Path(destination)
    if not destination_path.exists():
        return False
    try:
        lines = destination_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise PrivateSettingsError(f"Could not read private settings file '{destination_path}'. Check that it is a readable UTF-8 file") from None
    assignment_pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")
    return any(assignment_pattern.match(line) for line in lines)


# Quotes one private value for lossless parsing by python-dotenv
def _format_dotenv_value(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Dotenv values must be strings")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    return f'"{escaped}"'


# Updates allowed private values in a dotenv file through an atomic replacement
def update_dotenv_file(destination, updates):
    if not hasattr(updates, "items"):
        raise TypeError("Dotenv updates must be a mapping")
    update_items = list(updates.items())
    for key, value in update_items:
        if not isinstance(key, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or key not in SECRET_KEYS:
            raise ValueError(f"Unsupported dotenv key: {key!r}")
        if not isinstance(value, str):
            raise TypeError(f"Dotenv value for {key} must be a string")
    destination_path = Path(destination).expanduser()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = destination_path.read_text(encoding="utf-8").splitlines() if destination_path.exists() else []
    update_keys = {key for key, _ in update_items}
    values_by_key = dict(update_items)
    seen_keys = set()
    output_lines = []
    assignment_pattern = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
    for line in existing_lines:
        match = assignment_pattern.match(line)
        key = match.group(1) if match else None
        if key not in update_keys:
            output_lines.append(line)
            continue
        if key in seen_keys:
            continue
        seen_keys.add(key)
        # A secret cleared by its owner is removed rather than emptied, so a disabled value cannot linger here
        if not values_by_key[key]:
            continue
        output_lines.append(f"{key}={_format_dotenv_value(values_by_key[key])}")
    for key, value in update_items:
        if key not in seen_keys and value:
            output_lines.append(f"{key}={_format_dotenv_value(value)}")
            seen_keys.add(key)
    content = "\n".join(output_lines) + ("\n" if output_lines else "")
    # No backup here on purpose: a rotated secret must not be left behind in a second file
    return write_file_atomically(destination_path, content, mode=0o600)


# Collects hidden private values and saves them together after overwrite confirmation
@suppresses_debug_output
def _run_set_private_values(option_name: str, prompts: List[Tuple[str, str]], env_file=None, interactive=None, input_func=None, getpass_func=None, guidance: Optional[List[str]] = None, subject: str = "private settings", guide_url: Optional[str] = None, plural: bool = False) -> str:
    destination = resolve_private_settings_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise PrivateSettingsError(f"{option_name} requires an interactive terminal so private values stay hidden")
    existing_keys = [key for key, _ in prompts if _dotenv_contains_key(destination, key)]
    prompt = input if input_func is None else input_func
    if existing_keys:
        try:
            confirmed = read_interactively(prompt, f"Replace {', '.join(existing_keys)} in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            # Ctrl+C echoes nothing, so without this the error would continue the prompt line
            print()
            raise RecoveryError(secret_entry_cancelled_advice(subject, option_name, guide_url, plural=plural)) from None
        if not confirmed:
            raise RecoveryError(secret_replacement_declined_advice(subject, option_name, guide_url, plural=plural))
    for line in guidance or []:
        print(f"* {line}")
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    updates = {}
    try:
        for key, prompt_text in prompts:
            value = read_secret_interactively(hidden_prompt, prompt_text).strip()
            if not value or "\r" in value or "\n" in value:
                raise PrivateSettingsError(f"No valid value was entered for {key}. The dotenv file was not changed")
            updates[key] = value
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice(subject, option_name, guide_url, plural=plural)) from None
    try:
        update_dotenv_file(destination, updates)
    except PrivateSettingsError:
        raise
    except Exception:
        raise PrivateSettingsError(f"Could not save private values in '{destination}'. Check file permissions or choose another path with --env-file") from None
    print(f"* Updated private settings file: {destination}")
    print(f"* Saved: {', '.join(updates)}")
    return str(destination)


# Without these there is no email channel at all, which is a different question from what one delivery needs
MAIL_DESTINATION_SETTINGS = ("SMTP_HOST", "SENDER_EMAIL", "RECEIVER_EMAIL")
MAIL_SIGN_IN_SETTINGS = ("SMTP_HOST", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL")
# Every send signs in first, so a delivery needs the password as well
MAIL_DELIVERY_SETTINGS = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SENDER_EMAIL", "RECEIVER_EMAIL")


# Returns the named mail settings that are still unset, so every caller reports the same missing ones
def mail_settings_missing(names=MAIL_DESTINATION_SETTINGS):
    return [name for name in names if not doctor_value_is_set(str(globals().get(name) or ""))]


# Signs in to the configured mail server with one entered password, so nothing is saved that cannot deliver
def smtp_sign_in(password, timeout=15):
    global SMTP_PASSWORD

    candidate = str(password or "")
    if not candidate or not doctor_value_is_set(candidate):
        raise PrivateSettingsError("No SMTP password was entered. The dotenv file was not changed")
    missing = mail_settings_missing(MAIL_SIGN_IN_SETTINGS)
    if missing:
        raise PrivateSettingsError(f"The mail server settings are incomplete, {join_setting_names(missing, 'and')} {'is' if len(missing) == 1 else 'are'} not set")
    previous_password = SMTP_PASSWORD
    SMTP_PASSWORD = candidate
    smtp_object = None
    try:
        smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=timeout)
    finally:
        if smtp_object is not None:
            try:
                smtp_object.quit()
            except Exception as cleanup_error:
                debug_swallowed_exception("SMTP session cleanup", cleanup_error)
        SMTP_PASSWORD = previous_password
    return str(SMTP_USER)


# Privately checks one SMTP password against the mail server and atomically stores it
@suppresses_debug_output
def run_set_smtp_password(env_file=None, interactive=None, input_func=None, getpass_func=None, sign_in=None) -> str:
    destination = resolve_private_settings_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise PrivateSettingsError("--set-smtp-password requires an interactive terminal so the password stays hidden")
    # Checked before the prompts, so nobody types a password only to be told the mail server was never configured
    missing = mail_settings_missing(MAIL_SIGN_IN_SETTINGS)
    if missing:
        raise PrivateSettingsError(f"The mail server settings are incomplete, {join_setting_names(missing, 'and')} {'is' if len(missing) == 1 else 'are'} not set")
    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "SMTP_PASSWORD"):
        try:
            confirmed = read_interactively(prompt, f"Replace SMTP_PASSWORD in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            raise RecoveryError(secret_entry_cancelled_advice("SMTP password", "--set-smtp-password", SMTP_GUIDE_URL)) from None
        if not confirmed:
            raise RecoveryError(secret_replacement_declined_advice("SMTP password", "--set-smtp-password", SMTP_GUIDE_URL))
    print(f"* The password is checked by signing in to {SMTP_HOST} as {SMTP_USER}. Nothing is sent")
    print(f"* Guide: {SMTP_GUIDE_URL}")
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        smtp_password = str(read_secret_interactively(hidden_prompt, "Enter the SMTP password (input hidden): ")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice("SMTP password", "--set-smtp-password", SMTP_GUIDE_URL)) from None
    check = smtp_sign_in if sign_in is None else sign_in
    try:
        signed_in_user = check(smtp_password, timeout=DOCTOR_SMTP_TIMEOUT)
    except PrivateSettingsError:
        raise
    except Exception as exc:
        raise PrivateSettingsError(f"The mail server did not accept the password: {type(exc).__name__}: {sanitize_error_text(exc)}. The dotenv file was not changed") from None
    try:
        update_dotenv_file(destination, {"SMTP_PASSWORD": smtp_password})
    except PrivateSettingsError:
        raise
    except Exception:
        raise PrivateSettingsError(f"Could not save the SMTP password in '{destination}'. Check file permissions or choose another path with --env-file") from None
    print(f"* The mail server accepted the password for {signed_in_user}")
    print(f"* Updated private settings file: {destination}")
    print(f"* Test it with: {render_command(['--send-test-email'], env_path=destination)}")
    return str(destination)


# Safely stores one privately entered webhook URL
@suppresses_debug_output
def run_set_webhook_url(env_file=None, interactive=None, input_func=None, getpass_func=None) -> str:
    destination = resolve_private_settings_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise PrivateSettingsError("--set-webhook-url requires an interactive terminal so the webhook URL stays hidden")
    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "WEBHOOK_URL"):
        try:
            confirmed = read_interactively(prompt, f"Replace WEBHOOK_URL in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            raise RecoveryError(secret_entry_cancelled_advice("webhook URL", "--set-webhook-url", WEBHOOK_GUIDE_URL)) from None
        if not confirmed:
            raise RecoveryError(secret_replacement_declined_advice("webhook URL", "--set-webhook-url", WEBHOOK_GUIDE_URL))
    print("* Discord: Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL")
    print("* ntfy: the complete topic URL, such as https://ntfy.sh/your-private-topic")
    print(f"* Guide: {WEBHOOK_GUIDE_URL}")
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        webhook_url = read_secret_interactively(hidden_prompt, "Paste the Discord or ntfy webhook URL (input hidden): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice("webhook URL", "--set-webhook-url", WEBHOOK_GUIDE_URL)) from None
    if not validate_webhook_url(webhook_url):
        raise PrivateSettingsError("That does not look like a complete HTTPS webhook URL. The dotenv file was not changed")
    try:
        update_dotenv_file(destination, {"WEBHOOK_URL": webhook_url})
    except Exception:
        raise PrivateSettingsError(f"Could not save the webhook URL in '{destination}'. Check file permissions or choose another path with --env-file") from None
    print("* Webhook URL looks valid")
    print(f"* Updated private settings file: {destination}")
    print(f"* Test it with: {render_command(['--send-test-webhook'], env_path=destination)}")
    return str(destination)


# Safely stores privately entered Last.fm API credentials
@suppresses_debug_output
def run_set_lastfm_credentials(env_file=None, interactive=None, input_func=None, getpass_func=None) -> str:
    prompts = [("LASTFM_API_KEY", "Enter the Last.fm API key privately: "), ("LASTFM_API_SECRET", "Enter the Last.fm shared secret privately: ")]
    guidance = [
        f"Create your API key and shared secret at {LASTFM_API_REGISTRATION_URL}",
        f"View the credentials of an application you already registered at {LASTFM_API_ACCOUNTS_URL}",
        f"Guide: {LASTFM_API_GUIDE_URL}",
    ]
    return _run_set_private_values("--set-lastfm-credentials", prompts, env_file, interactive, input_func, getpass_func, guidance, subject="Last.fm API credentials", guide_url=LASTFM_API_GUIDE_URL, plural=True)


# Safely stores privately entered Spotify OAuth app credentials
@suppresses_debug_output
def run_set_spotify_credentials(env_file=None, interactive=None, input_func=None, getpass_func=None) -> str:
    prompts = [("SP_CLIENT_ID", "Enter the Spotify client ID privately: "), ("SP_CLIENT_SECRET", "Enter the Spotify client secret privately: ")]
    guidance = [
        f"Create an app at {SPOTIFY_DASHBOARD_URL} with 'Web API' selected and a redirect URI of http://127.0.0.1:1234",
        "Then copy its Client ID and, through 'View client secret', its Client Secret.",
        f"Guide: {SPOTIFY_APP_GUIDE_URL}",
    ]
    return _run_set_private_values("--set-spotify-credentials", prompts, env_file, interactive, input_func, getpass_func, guidance, subject="Spotify OAuth app credentials", guide_url=SPOTIFY_APP_GUIDE_URL, plural=True)


# Finds an optional config file
def find_config_file(cli_path=None):
    """
    Search for an optional config file in:
      1) CLI-provided path (must exist if given)
      2) ./{DEFAULT_CONFIG_FILENAME}
      3) ~/.{DEFAULT_CONFIG_FILENAME}
      4) script-directory/{DEFAULT_CONFIG_FILENAME}

    The literal 'none' selects no file at all, which also switches the search off.
    """

    if CONFIG_DISCOVERY_DISABLED or str(cli_path or "").casefold() == "none":
        return None

    if cli_path:
        p = Path(os.path.expanduser(cli_path))
        return str(p) if p.is_file() else None

    candidates = [
        Path.cwd() / DEFAULT_CONFIG_FILENAME,
        Path.home() / f".{DEFAULT_CONFIG_FILENAME}",
        Path(__file__).parent / DEFAULT_CONFIG_FILENAME,
    ]

    for p in candidates:
        if p.is_file():
            return str(p)
    return None


# Keeps argparse from colouring its own help, so the help screen is coloured by this tool alone and --no-color is
# not left with a second palette to silence. From Python 3.14 argparse colours the help by default on a terminal
def argparse_color_kwargs() -> dict[str, Any]:
    return {"color": False} if sys.version_info >= (3, 14) else {}


# Reads the --config-file path straight from the raw arguments, for the settings needed before argparse runs
def early_config_file_argument(arguments=None):
    values = list(sys.argv[1:] if arguments is None else arguments)
    for index, argument in enumerate(values):
        if argument == "--config-file" and index + 1 < len(values):
            return values[index + 1]
        if argument.startswith("--config-file="):
            return argument.split("=", 1)[1]
    return None


# Applies the terminal settings needed before argument parsing, leaving any failure to normal config loading
def apply_early_output_config():
    global CLEAR_SCREEN, COLORED_OUTPUT
    try:
        cli_path = early_config_file_argument()
        config_path = find_config_file(os.path.expanduser(cli_path) if cli_path else None)
        if not config_path:
            return
        values = parse_config_content(Path(config_path).read_text(encoding="utf-8"), str(config_path))
    except (MemoryError, OSError, RecursionError, SyntaxError, UnicodeError, ValueError):
        return
    if isinstance(values.get("CLEAR_SCREEN"), bool):
        CLEAR_SCREEN = values["CLEAR_SCREEN"]
    if isinstance(values.get("COLORED_OUTPUT"), bool):
        COLORED_OUTPUT = values["COLORED_OUTPUT"]


# Settings an older version wrote that this version no longer defines, ignored instead of rejected
RETIRED_CONFIG_SETTINGS = frozenset(())

# Settings the template ships commented out, so the tool's own defaults apply until a user uncomments them.
# They are still accepted from a configuration file, since the template is also the settings allowlist
COMMENTED_CONFIG_SETTINGS = frozenset({"COLOR_THEME"})


# Collects the setting names the built-in configuration template defines
def _config_allowed_names():
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    return frozenset(statement.targets[0].id for statement in template_tree.body if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name)) | COMMENTED_CONFIG_SETTINGS


# Returns the values the built-in template ships, so a section the user declines is written as shipped
def _config_template_defaults():
    defaults = {}
    for statement in ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec").body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            continue
        try:
            defaults[statement.targets[0].id] = ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            continue
    return defaults


# Renders one configuration file from the built-in template with the chosen values substituted in
def generate_config_with_current_values(config_values):
    tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    replacements = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            continue
        name = statement.targets[0].id
        # A secret belongs in the dotenv file, so its template placeholder stays even when the running values hold the real one
        if name not in config_values or name in SECRET_KEYS:
            continue
        replacements[name] = (statement.lineno, getattr(statement, "end_lineno", statement.lineno), repr(config_values[name]))
    lines = CONFIG_BLOCK.strip("\n").split("\n")
    # The template keeps its own leading blank line, so template line numbers are one ahead of this list
    offset = 1 if CONFIG_BLOCK.startswith("\n") else 0
    skip_until = 0
    output = []
    for number, line in enumerate(lines, 1):
        template_line = number + offset
        if template_line < skip_until:
            continue
        replaced = next((name for name, (start, _end, _value) in replacements.items() if start == template_line), None)
        if replaced is None:
            output.append(line)
            continue
        start, end, rendered = replacements[replaced]
        output.append(f"{replaced} = {rendered}")
        skip_until = end + 1
    return "\n".join(output) + "\n"


# Parses allowlisted literal config assignments without executing any file content
def parse_config_content(content, filename="<config>", retired_out=None, reference_values=None):
    tree = ast.parse(content, filename, "exec")
    allowed_names = _config_allowed_names()
    parsed_values = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            raise ValueError(f"Line {getattr(statement, 'lineno', '?')}: only NAME = value assignments are allowed")
        name = statement.targets[0].id
        if name in RETIRED_CONFIG_SETTINGS and name not in allowed_names:
            if retired_out is not None and name not in retired_out:
                retired_out.append(name)
            continue
        if name not in allowed_names:
            raise ValueError(f"Line {statement.lineno}: unsupported configuration setting {name!r}")
        # One setting may reuse another, which the built-in template does and existing configs copy
        if isinstance(statement.value, ast.Name):
            referenced = statement.value.id
            if referenced not in allowed_names:
                raise ValueError(f"Line {statement.lineno}: {name} may only reference another configuration setting")
            source = parsed_values if referenced in parsed_values else (reference_values if reference_values is not None else globals())
            if referenced not in source:
                raise ValueError(f"Line {statement.lineno}: {name} references {referenced!r} before it has a value")
            parsed_values[name] = source[referenced]
            continue
        try:
            parsed_values[name] = ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as exc:
            raise ValueError(f"Line {statement.lineno}: {name} must be a plain value such as a number, string, True, False, None, list, tuple or dict") from exc
    return parsed_values


# Validates config content through the same restricted parser used at startup
def validate_config_content(content, filename="<generated-config>"):
    parse_config_content(content, filename)


# Reports settings an older version wrote that this version no longer defines
def describe_retired_settings(names, quoted_path):
    listed = ", ".join(sorted(names))
    return f"Config file {quoted_path} contains settings this version no longer uses, which were ignored: {listed}"


# Loads a config file as data and applies only recognized literal settings
def load_config_file(config_path, namespace=None, report_errors=True):
    selected_namespace = globals() if namespace is None else namespace
    retired_settings = []
    try:
        content = Path(config_path).read_text(encoding="utf-8")
        # Parsed as data rather than executed, so a config file picked up from the working directory cannot run code
        parsed_values = parse_config_content(content, str(config_path), retired_settings)
        selected_namespace.update(parsed_values)
        debug_print("Configuration applied", path=str(config_path), settings=len(parsed_values), retired=len(retired_settings) or None, outcome="OK")
        if retired_settings and report_errors:
            print(f"* Note: {describe_retired_settings(retired_settings, chr(39) + str(config_path) + chr(39))}")
        return True
    except SyntaxError as exc:
        detail = f"Config file '{config_path}' has invalid Python syntax"
        if exc.lineno is not None:
            detail += f" at line {exc.lineno}"
        if exc.text:
            detail += f" | Source: {exc.text.rstrip()}"
        detail += f" | Parser: {exc.msg}"
    # Checked before ValueError because UnicodeDecodeError derives from it
    except UnicodeDecodeError:
        detail = f"Config file '{config_path}' is not valid UTF-8"
    except ValueError as exc:
        detail = f"Config file '{config_path}' contains unsupported content: {exc}"
    except Exception as exc:
        detail = f"Config file '{config_path}' failed with {type(exc).__name__}: {exc}"
    debug_print("Configuration load", path=str(config_path), outcome="failed", error=detail)
    if report_errors:
        print_recovery_error(context="config", detail=detail)
        print("* Config files are read as data. Only documented SETTING = value lines with plain literal values are accepted.")
    return False


# Resolves Spotify track metadata first then falls back to Last.fm duration
def get_track_info(artist, track, album, network):
    sp_track_uri_id = None
    sp_track_duration = 0
    track_duration = 0
    duration_mark = ""

    debug_print("Track metadata lookup", artist=artist, track=track, album=album)

    if USE_TRACK_DURATION_FROM_SPOTIFY or TRACK_SONGS:
        sp_track_uri_id, sp_track_duration = spotify_resolve_track_metadata(artist, track, album)
        if not USE_TRACK_DURATION_FROM_SPOTIFY:
            sp_track_duration = 0

    if sp_track_duration > 0:
        track_duration = sp_track_duration
        if not DO_NOT_SHOW_DURATION_MARKS:
            duration_mark = " S*"
    else:
        try:
            lf_track = pylast.Track(artist, track, network)
            lf_duration = lf_track.get_duration()
            debug_print("Last.fm track duration fallback", artist=artist, track=track, duration=f"{lf_duration}ms", outcome="OK")
            if lf_duration and lf_duration > 0:
                if USE_TRACK_DURATION_FROM_SPOTIFY and not DO_NOT_SHOW_DURATION_MARKS:
                    duration_mark = " L*"
                # Last.fm returns duration in milliseconds
                track_duration = int(lf_duration / 1000)
        except Exception as e:
            debug_print("Last.fm track duration fallback", artist=artist, track=track, outcome="failed", error=f"{type(e).__name__}: {e}")
            track_duration = 0

    debug_print("Track metadata lookup", artist=artist, track=track, duration=f"{track_duration}s", mark=duration_mark or None, outcome="OK")

    return track_duration, sp_track_uri_id, duration_mark


# Returns the hex salt and PBKDF2 iteration count used for key derivation
def _get_kdf_params() -> Tuple[str, int]:
    salt_hex = "10368003bf43b4c3230602b970a37e95"
    iterations = 200000
    return salt_hex, iterations


# Derive a 32-byte key from the provided password using PBKDF2-HMAC-SHA256.
def _derive_key(password: str, salt_hex: str, iterations: int) -> bytes:
    salt = bytes.fromhex(salt_hex)
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)


# Returns the base64 payload containing HMAC plus ciphertext
def get_payload() -> str:
    return "JMFkEQDf9n4Cl+c7w4thPigWUj7lTsclulxPBsQznBo8h268HncHU3qwLg=="


# Derive the key from password, verify HMAC, XOR-decrypt and return plaintext
# The password must be a date in YYYYMMDD format
def decode(password: str) -> str:
    payload_b64 = get_payload()
    try:
        raw = base64.b64decode(payload_b64)
    except Exception as exc:
        raise ValueError("payload is not valid base64") from exc

    if len(raw) <= 32:
        raise ValueError("payload too short")

    mac_received = raw[:32]
    cipher = raw[32:]

    salt_hex, iterations = _get_kdf_params()
    key = _derive_key(password, salt_hex, iterations)

    mac_calc = hmac.new(key, cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(mac_calc, mac_received):
        raise ValueError("HMAC verification failed")

    plaintext_bytes = bytes(c ^ key[i % len(key)] for i, c in enumerate(cipher))
    try:
        return plaintext_bytes.decode("utf-8")
    except Exception as exc:
        raise ValueError("decrypted bytes are not valid UTF-8") from exc


# Main function that monitors activity of the specified Last.fm user
def lastfm_monitor_user(user, network, username, tracks, csv_file_name):  # pyright: ignore[reportGeneralTypeIssues]

    lf_active_ts_start = 0
    lf_active_ts_last = 0
    lf_track_ts_start = 0
    lf_track_ts_start_old = 0
    lf_track_ts_start_after_resume = 0
    lf_user_online = False
    alive_since = int(time.time())
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
    recent_songs_session = []
    sp_track_uri_id = None
    duration_mark = ""
    pauses_number = 0
    error_500_counter = 0
    error_500_start_ts = 0
    error_network_issue_counter = 0
    error_network_issue_start_ts = 0
    friends_check_last_ts = 0
    check_count = 0

    # Output after this point is no longer the startup screen, so a verbose notice closes its own block
    mark_monitoring_started()
    debug_print("Monitoring loop start", user=username, interval=f"{LASTFM_CHECK_INTERVAL}s", active_interval=f"{LASTFM_ACTIVE_CHECK_INTERVAL}s")
    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print_recovery_error(e, context="file.unwritable")

    lastfm_last_activity_file = resolve_status_file(username)
    last_activity_read = []
    last_activity_ts = 0
    last_activity_artist = ""
    last_activity_track = ""
    last_activity_album = ""

    if os.path.isfile(lastfm_last_activity_file):
        try:
            with open(lastfm_last_activity_file, 'r', encoding="utf-8") as f:
                last_activity_read = json.load(f)
            debug_print("Last activity read", path=lastfm_last_activity_file, entries=len(last_activity_read), outcome="OK")
        except Exception as e:
            debug_print("Last activity read", path=lastfm_last_activity_file, outcome="failed", error=f"{type(e).__name__}: {e}")
            print_recovery_error(e, context="file", detail=f"Cannot load the last status from '{lastfm_last_activity_file}'")
        if last_activity_read:
            last_activity_ts = last_activity_read[0]
            last_activity_artist = last_activity_read[1]
            last_activity_track = last_activity_read[2]
            # Album is stored at index 3 if available
            if len(last_activity_read) > 3:
                last_activity_album = last_activity_read[3]
            lastfm_last_activity_file_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(lastfm_last_activity_file)))
            lastfm_last_activity_file_mdate = lastfm_last_activity_file_mdate_dt.strftime("%d %b %Y, %H:%M:%S")
            lastfm_last_activity_file_mdate_weekday = str(calendar.day_abbr[(lastfm_last_activity_file_mdate_dt).weekday()])
            print(f"* Last activity loaded from file '{lastfm_last_activity_file}' ({lastfm_last_activity_file_mdate_weekday} {lastfm_last_activity_file_mdate})")

    try:
        new_track = lastfm_get_now_playing(username, user)
        recent_tracks = lastfm_get_recent_tracks(username, network, RECENT_TRACKS_NUMBER)
    except Exception as e:
        print_recovery_error(e, detail=f"Cannot read the recent tracks of '{username}'")
        sys.exit(1)

    # Handle case where user has no tracks yet (fresh account)
    if not recent_tracks or len(recent_tracks) == 0:
        print("\n*** User has no tracks yet (fresh account). Waiting for first track to appear...\n")
        last_track_start_ts_old2 = 0
        lf_track_ts_start_old = 0
        last_track_start_ts_old = 0

        # If user is currently playing music but has no history yet, handle it
        if new_track is not None:
            app_started_and_user_offline = False
            lf_active_ts_start = int(time.time())
            lf_active_ts_last = lf_active_ts_start
            lf_track_ts_start = lf_active_ts_start
            lf_track_ts_start_after_resume = lf_active_ts_start
            playing_resumed_ts = lf_active_ts_start
            song_on_loop = 1
            artist = str(new_track.artist)
            track = str(new_track.title)
            album = str(new_track.info.get('album', '')) if new_track.info.get('album') else ""
            artist_old = artist
            track_old = track
            last_activity_artist = artist
            last_activity_track = track
            playing_track = new_track
            lf_user_online = True
            debug_print("User state change", user=username, state="online", reason="track playing at startup")
            print(f"\nTrack:\t\t\t\t{artist} - {track}")
            if album:
                print(f"Album:\t\t\t\t{album}")

            track_duration, sp_track_uri_id, duration_mark = get_track_info(artist, track, album, network)

            if track_duration > 0:
                print(f"Duration:\t\t\t{display_time(track_duration)}{duration_mark}")

            spotify_search_url, apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, lastfm_url, lastfm_album_url = get_spotify_apple_genius_search_urls(str(artist), str(track), album, network, playing_track)

            music_urls_output = format_music_urls_console(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
            lyrics_output = format_lyrics_urls_console(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
            if music_urls_output or lyrics_output:
                print()  # Always add newline before first section (music URLs or lyrics)
            if music_urls_output:
                print(music_urls_output)
            if lyrics_output:
                print(lyrics_output)

            print("\n*** User is currently ACTIVE (first track) !")

            listened_songs = 1
            recent_songs_session = [{'artist': artist, 'track': track, 'timestamp': lf_track_ts_start, 'skipped': False, 'cont': False}]

            last_activity_to_save = []
            last_activity_to_save.append(lf_track_ts_start)
            last_activity_to_save.append(artist)
            last_activity_to_save.append(track)
            last_activity_to_save.append(album)

            save_last_activity_state(lastfm_last_activity_file, last_activity_to_save)

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(lf_track_ts_start)), artist, track, album)
            except Exception as e:
                print_recovery_error(e, context="file.unwritable")

            duration_m_body = ""
            duration_m_body_html = ""
            if track_duration > 0:
                duration_m_body = f"\nDuration: {display_time(track_duration)}{duration_mark}"
                duration_m_body_html = f"<br>Duration: {display_time(track_duration)}{duration_mark}"

            m_subject = f"Last.fm user {username} is active: '{artist} - {track}'"
            lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
            lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, artist, track)
            lyrics_section_text = f"\n{lyrics_urls_text}\n\n" if lyrics_urls_text else "\n\n"
            lyrics_section_html = f"<br>{lyrics_urls_html}<br><br>" if lyrics_urls_html else "<br><br>"
            # Determine URLs for "Track:" and secondary URL field based on configuration
            if USE_LASTFM_URL_IN_LAST_PLAYED:
                track_url = lastfm_url
                secondary_url = spotify_search_url
                secondary_url_label = "Spotify URL"
            else:
                track_url = spotify_search_url
                secondary_url = lastfm_url
                secondary_url_label = "Last.fm URL"
            music_urls_text = format_music_urls_email_text(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
            music_urls_html = format_music_urls_email_html(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, artist, track, secondary_url, secondary_url_label)
            music_section_text = f"\n\n{music_urls_text}\n" if music_urls_text else "\n"
            music_section_html = f"<br><br>{music_urls_html}" if music_urls_html else ""
            # When both music and lyrics are empty, use single <br><br> instead of <br> + <br><br>
            if not music_urls_html and not lyrics_urls_html:
                music_section_html = "<br><br>"
                lyrics_section_html = ""
            elif not music_urls_html:
                music_section_html = "<br>"
            album_line = f"Album: {album}" if album else ""
            m_body = f"Track: {artist} - {track}{duration_m_body}\n{album_line}{music_section_text}{lyrics_section_text}Last activity: {get_date_from_ts(lf_active_ts_last)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
            album_html = f'<a href="{lastfm_album_url}">{escape(album)}</a>' if (ENABLE_LASTFM_ALBUM_URL and lastfm_album_url) else escape(album)
            album_html_line = f"<br>Album: {album_html}" if album else ""
            m_body_html = f"<html><head></head><body>Track: <b><a href=\"{track_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}{album_html_line}{music_section_html}{lyrics_section_html}Last activity: <b>{get_date_from_ts(lf_active_ts_last)}</b>{get_cur_ts('<br>Timestamp: ')}</body></html>"

            if ACTIVE_NOTIFICATION or webhook_event_enabled("active"):
                send_notification_channels("active", m_subject, m_body, m_body_html, email_enabled=ACTIVE_NOTIFICATION, subject_short=f"{username} is active", body_short="\n".join(value for value in (track, artist, album) if value))

            # If tracking functionality is enabled then play the current song via Spotify client
            if TRACK_SONGS and sp_track_uri_id:
                if platform.system() == 'Darwin':       # macOS
                    spotify_macos_play_song(sp_track_uri_id)
                elif platform.system() == 'Windows':    # Windows
                    spotify_win_play_song(sp_track_uri_id)
                else:                                   # Linux variants
                    spotify_linux_play_song(sp_track_uri_id)
        else:
            app_started_and_user_offline = True
            playing_track = None
            lf_user_online = False
            lf_active_ts_last = 0
            last_activity_artist = ""
            last_activity_track = ""
            artist_old = ""
            track_old = ""
            print(f"* Last activity:\t\tNo tracks yet")
            print(f"* Last track:\t\t\tNo tracks yet")
            print(f"\n*** User is OFFLINE (no tracks yet) !")
    else:
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
                if recent_tracks[0].album:
                    last_activity_album = str(recent_tracks[0].album)
            elif lf_active_ts_last < last_activity_ts and last_activity_ts > 0:
                lf_active_ts_last = last_activity_ts

            last_activity_dt = datetime.fromtimestamp(lf_active_ts_last).strftime("%d %b %Y, %H:%M:%S")
            last_activity_ts_weekday = str(calendar.day_abbr[(datetime.fromtimestamp(lf_active_ts_last)).weekday()])

            artist_old = str(last_activity_artist)
            track_old = str(last_activity_track)

            print(f"* Last activity:\t\t{last_activity_ts_weekday} {last_activity_dt}")
            print(f"* Last track:\t\t\t{last_activity_artist} - {last_activity_track}")
            if last_activity_album:
                print(f"* Last album:\t\t\t{last_activity_album}")

            track_duration, sp_track_uri_id, duration_mark = get_track_info(last_activity_artist, last_activity_track, last_activity_album, network)

            if track_duration > 0:
                print(f"* Last track duration:\t\t{display_time(track_duration)}{duration_mark}")

            spotify_search_url, apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, lastfm_url, lastfm_album_url = get_spotify_apple_genius_search_urls(str(last_activity_artist), str(last_activity_track), last_activity_album, network)

            music_urls_output = format_music_urls_console(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
            lyrics_output = format_lyrics_urls_console(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
            if music_urls_output or lyrics_output:
                print()  # Always add newline before first section (music URLs or lyrics)
            if music_urls_output:
                print(music_urls_output)
            if lyrics_output:
                print(f"{lyrics_output}\n")
            elif not music_urls_output:
                print()  # Add newline before "User is OFFLINE" when both music and lyrics are disabled
            elif music_urls_output:
                print()  # Add newline after music URLs when lyrics are disabled

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
            album = str(new_track.info.get('album', '')) if new_track.info.get('album') else ""
            artist_old = artist
            track_old = track
            print(f"\nTrack:\t\t\t\t{artist} - {track}")
            if album:
                print(f"Album:\t\t\t\t{album}")

            track_duration, sp_track_uri_id, duration_mark = get_track_info(artist, track, album, network)

            if track_duration > 0:
                print(f"Duration:\t\t\t{display_time(track_duration)}{duration_mark}")

            spotify_search_url, apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, lastfm_url, lastfm_album_url = get_spotify_apple_genius_search_urls(str(artist), str(track), album, network, new_track)

            music_urls_output = format_music_urls_console(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
            lyrics_output = format_lyrics_urls_console(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
            if music_urls_output or lyrics_output:
                print()  # Always add newline before first section (music URLs or lyrics)
            if music_urls_output:
                print(music_urls_output)
            if lyrics_output:
                print(lyrics_output)

            print("\n*** User is currently ACTIVE !")

            listened_songs = 1
            recent_songs_session = [{'artist': artist, 'track': track, 'timestamp': lf_track_ts_start, 'skipped': False, 'cont': False}]

            last_activity_to_save = []
            last_activity_to_save.append(lf_track_ts_start)
            last_activity_to_save.append(artist)
            last_activity_to_save.append(track)
            last_activity_to_save.append(album)

            save_last_activity_state(lastfm_last_activity_file, last_activity_to_save)

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(lf_track_ts_start)), artist, track, album)
            except Exception as e:
                print_recovery_error(e, context="file.unwritable")

            duration_m_body = ""
            duration_m_body_html = ""
            if track_duration > 0:
                duration_m_body = f"\nDuration: {display_time(track_duration)}{duration_mark}"
                duration_m_body_html = f"<br>Duration: {display_time(track_duration)}{duration_mark}"

            m_subject = f"Last.fm user {username} is active: '{artist} - {track}'"
            lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
            lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, artist, track)
            lyrics_section_text = f"\n{lyrics_urls_text}\n\n" if lyrics_urls_text else "\n\n"
            lyrics_section_html = f"<br>{lyrics_urls_html}<br><br>" if lyrics_urls_html else "<br><br>"
            # Determine URLs for "Track:" and secondary URL field based on configuration
            if USE_LASTFM_URL_IN_LAST_PLAYED:
                track_url = lastfm_url
                secondary_url = spotify_search_url
                secondary_url_label = "Spotify URL"
            else:
                track_url = spotify_search_url
                secondary_url = lastfm_url
                secondary_url_label = "Last.fm URL"
            music_urls_text = format_music_urls_email_text(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
            music_urls_html = format_music_urls_email_html(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, artist, track, secondary_url, secondary_url_label)
            music_section_text = f"\n\n{music_urls_text}\n" if music_urls_text else "\n"
            music_section_html = f"<br><br>{music_urls_html}" if music_urls_html else ""
            # When both music and lyrics are empty, use single <br><br> instead of <br> + <br><br>
            if not music_urls_html and not lyrics_urls_html:
                music_section_html = "<br><br>"
                lyrics_section_html = ""
            elif not music_urls_html:
                music_section_html = "<br>"
            album_line = f"Album: {album}" if album else ""
            m_body = f"Track: {artist} - {track}{duration_m_body}\n{album_line}{music_section_text}{lyrics_section_text}Last activity: {get_date_from_ts(lf_active_ts_last)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
            album_html = f'<a href="{lastfm_album_url}">{escape(album)}</a>' if (ENABLE_LASTFM_ALBUM_URL and lastfm_album_url) else escape(album)
            album_html_line = f"<br>Album: {album_html}" if album else ""
            m_body_html = f"<html><head></head><body>Track: <b><a href=\"{track_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}{album_html_line}{music_section_html}{lyrics_section_html}Last activity: <b>{get_date_from_ts(lf_active_ts_last)}</b>{get_cur_ts('<br>Timestamp: ')}</body></html>"

            if ACTIVE_NOTIFICATION or webhook_event_enabled("active"):
                send_notification_channels("active", m_subject, m_body, m_body_html, email_enabled=ACTIVE_NOTIFICATION, subject_short=f"{username} is active", body_short="\n".join(value for value in (track, artist, album) if value))

            playing_track = new_track
            # If user has tracks, use the first one's timestamp, otherwise use current time
            if recent_tracks and len(recent_tracks) > 0:
                last_track_start_ts_old = int(recent_tracks[0].timestamp)
            else:
                last_track_start_ts_old = lf_active_ts_start
            lf_user_online = True

            # If tracking functionality is enabled then play the current song via Spotify client
            # Only play when user is online and actively playing
            if TRACK_SONGS and sp_track_uri_id:
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
    if not recent_tracks or len(recent_tracks) == 0:
        print("(No tracks yet)")
    else:
        for previous, t, _nxt in previous_and_next(reversed(recent_tracks)):
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
    webhook_sent = False

    tracks_upper = {t.upper() for t in tracks}

    # Initialize friend and profile tracking if enabled
    if friends_check_enabled():
        print("* Friends/profile tracking enabled")

        # Do initial check
        try:
            followings_file_exists = os.path.isfile(f"lastfm_{username}_followings.json")
            followers_file_exists = os.path.isfile(f"lastfm_{username}_followers.json")
            profile_file_exists = os.path.isfile(f"lastfm_{username}_profile.json")

            # Load existing state if available
            if TRACK_FOLLOWINGS and followings_file_exists:
                followings_loaded = load_friends_state(username, 'followings')
                followings_count = len(followings_loaded)
                print(f"* Loading followings for user {username} from file lastfm_{username}_followings.json ({followings_count})")

            if TRACK_FOLLOWERS and followers_file_exists:
                followers_loaded = load_friends_state(username, 'followers')
                followers_count = len(followers_loaded)
                print(f"* Loading followers for user {username} from file lastfm_{username}_followers.json ({followers_count})")

            if (TRACK_BIO or TRACK_DISPLAY_NAME) and profile_file_exists:
                profile_loaded = load_profile_state(username)
                profile_fields = ', '.join(field for field in ('display_name', 'bio') if field in profile_loaded)
                print(f"* Loading profile baseline for user {username} from file lastfm_{username}_profile.json ({profile_fields or 'no valid fields'})")

            # Perform initial check to build baseline
            # We use raise_on_error=True so initialization failures (e.g. scraping issues) are visible
            initial_changes, _ = check_friends_changes(username, TRACK_FOLLOWINGS, TRACK_FOLLOWERS, TRACK_BIO, TRACK_DISPLAY_NAME, save_state=True, raise_on_error=True)

            # Announce baseline creation for missing files
            if TRACK_FOLLOWINGS and not followings_file_exists:
                if os.path.isfile(f"lastfm_{username}_followings.json"):
                    followings_count = len(load_friends_state(username, 'followings'))
                    print(f"* Saving followings for user {username} to file lastfm_{username}_followings.json ({followings_count})")

            if TRACK_FOLLOWERS and not followers_file_exists:
                if os.path.isfile(f"lastfm_{username}_followers.json"):
                    followers_count = len(load_friends_state(username, 'followers'))
                    print(f"* Saving followers for user {username} to file lastfm_{username}_followers.json ({followers_count})")

            if (TRACK_BIO or TRACK_DISPLAY_NAME) and not profile_file_exists and os.path.isfile(f"lastfm_{username}_profile.json"):
                print(f"* Saving profile baseline for user {username} to file lastfm_{username}_profile.json")

            # Only notify if there are real changes (not initial fetch/baseline build)
            if initial_changes:
                # Filter out initial additions (baseline) from notification
                to_notify = {}
                if 'followings' in initial_changes and not followings_file_exists:
                    pass  # Handled by "Saving baseline" above
                elif 'followings' in initial_changes:
                    to_notify['followings'] = initial_changes['followings']

                if 'followers' in initial_changes and not followers_file_exists:
                    pass  # Handled by "Saving baseline" above
                elif 'followers' in initial_changes:
                    to_notify['followers'] = initial_changes['followers']

                if 'profile' in initial_changes:
                    to_notify['profile'] = initial_changes['profile']

                if to_notify:
                    notify_friends_changes(username, to_notify, skip_initial_line=True)
                else:
                    # Baseline was built but no "real" changes to report
                    print_cur_ts("\nTimestamp:\t\t\t")
            else:
                # No changes detected during baseline build
                print_cur_ts("\nTimestamp:\t\t\t")
        except Exception as e:
            print_recovery_error(e, detail=f"Cannot complete the initial friend and profile check: {e}")
            print_cur_ts("\nTimestamp:\t\t\t")

        friends_check_last_ts = int(time.time())

    # Main loop
    friends_pending_changes = None
    friends_streak = 0
    friends_failure_announced = False
    outage = OutageReporter()
    recovery_hint_tracker = RecoveryHintTracker()
    friends_next_check_ts = 0

    while True:
        try:
            # Reported by the completed-check trace at the end of this iteration, which one failure handler shares
            # with the healthy path, so the trace says which of the two ran
            check_outcome = "OK"

            # Check for friend or profile changes if enabled and interval has passed
            if friends_check_enabled() and FRIENDS_CHECK_INTERVAL > 0:
                current_ts = int(time.time())

                # Determine if it's time for a regular check or a retry check
                do_check = False
                is_retry = False

                if friends_streak != 0:
                    # We are in a confirmation/retry streak (change or error)
                    if current_ts >= friends_next_check_ts:
                        do_check = True
                        is_retry = True
                elif (current_ts - friends_check_last_ts) >= FRIENDS_CHECK_INTERVAL:
                    # Regular check interval reached
                    do_check = True

                if do_check:
                    try:
                        # Use save_state=False by default to avoid saving to file during suspected transient changes
                        # Use raise_on_error=True to detect check failures and avoid resetting streak
                        # current_states holds the exact data we just fetched so confirmation never needs a second request
                        changes, current_states = check_friends_changes(username, TRACK_FOLLOWINGS, TRACK_FOLLOWERS, TRACK_BIO, TRACK_DISPLAY_NAME, save_state=False, raise_on_error=True)

                        # Reset error streak on any successful check
                        if friends_streak < 0:
                            failed_checks = abs(friends_streak)
                            debug_print("Friends/profile check", outcome="OK", failures=failed_checks)
                            # A recovery is only news if the failure was, so an outage nobody saw clears in silence
                            if friends_failure_announced:
                                print(f"* Friends/profile check is available again after {failed_checks} failed check{'' if failed_checks == 1 else 's'}, so friend and profile change alerts can fire again")
                                print_cur_ts("Timestamp:\t\t\t")
                            friends_streak = 0

                        if changes:
                            if changes == friends_pending_changes:
                                friends_streak += 1
                            else:
                                friends_pending_changes = changes
                                friends_streak = 1

                            if friends_streak >= FRIENDS_CHANGE_COUNTER:
                                # Final confirmation after enough checks then persist the exact fetched state
                                save_friends_check_states(username, current_states)
                                notify_friends_changes(username, changes, skip_initial_line=not PROGRESS_INDICATOR)
                                friends_streak = 0
                                friends_pending_changes = None
                                friends_check_last_ts = current_ts
                            else:
                                # Suspected transient change, schedule retry
                                retry_interval = FRIENDS_RETRY_INTERVAL
                                friends_next_check_ts = current_ts + retry_interval

                                # Show streak info with details
                                change_details = []
                                for key in ['followings', 'followers']:
                                    if key in changes:
                                        c = changes[key]
                                        diff = c['current_count'] - c['previous_count']
                                        diff_str = f"{diff:+d}" if diff != 0 else "0"
                                        change_details.append(f"{key}: {c['previous_count']} -> {c['current_count']} ({diff_str})")

                                if 'profile' in changes:
                                    changed_fields = ', '.join('display name' if field == 'display_name' else 'bio' for field in changes['profile'])
                                    change_details.append(f"profile: {changed_fields}")

                                detail_str = "; ".join(change_details)
                                print(f"* Suspected transient change ({detail_str}) (streak {friends_streak}/{FRIENDS_CHANGE_COUNTER}); will confirm in {display_time(retry_interval)}")
                                print_cur_ts("Timestamp:\t\t\t")
                        else:
                            # No changes or back to baseline
                            if friends_streak > 0:
                                # Recovered from a suspected change
                                print(f"* Friend/profile state recovered back to the baseline after {friends_streak} suspected transient checks")
                                print_cur_ts("Timestamp:\t\t\t")

                            friends_streak = 0
                            friends_pending_changes = None
                            if not is_retry:
                                friends_check_last_ts = current_ts
                                # Refresh baseline timestamps with the exact data fetched by this check
                                save_friends_check_states(username, current_states)
                    except Exception as e:
                        if friends_streak == 0:
                            # Start measuring error streak (negative values)
                            friends_streak = -1
                            # Nothing else is printed until the streak reaches its alert threshold, which reads as a check that stopped running
                            friends_failure_announced = verbose_degraded_feature("Friends/profile check", "friend and profile change alerts", e)
                        elif friends_streak < 0:
                            # Continue error streak
                            friends_streak -= 1
                            # The notice above reports the outage once, so the repeats are left to debug
                            debug_print("Friends/profile check", outcome="failed", attempt=f"#{abs(friends_streak)}", error=f"{type(e).__name__}: {e}")

                        if friends_streak > 0:
                            # We were tracking a change but hit an error
                            retry_interval = FRIENDS_RETRY_INTERVAL
                            friends_next_check_ts = current_ts + retry_interval
                            friends_failure_announced = True
                            print_recovery_error(e, detail=f"Cannot confirm the friend and profile state: {e}")
                            print(f"* Keeping the confirmation streak ({friends_streak}/{FRIENDS_CHANGE_COUNTER}); will retry in {display_time(retry_interval)}")
                            print_cur_ts("Timestamp:\t\t\t")
                        else:
                            # Error streak logic (negative streak)
                            current_error_streak = abs(friends_streak)

                            # Throttling: Alert on threshold, then every 10 attempts
                            if current_error_streak == FRIENDS_CHANGE_COUNTER or (current_error_streak > FRIENDS_CHANGE_COUNTER and (current_error_streak - FRIENDS_CHANGE_COUNTER) % 10 == 0):
                                friends_failure_announced = True
                                print_recovery_error(e, detail=f"Cannot confirm the friend and profile state (attempt {current_error_streak}): {e}")
                                print_cur_ts("Timestamp:\t\t\t")

                            retry_interval = FRIENDS_RETRY_INTERVAL
                            friends_next_check_ts = current_ts + retry_interval

            debug_print("Now playing and recent tracks fetch", user=username)
            recent_tracks = lastfm_get_recent_tracks(username, network, 1)

            # A throttled failure stops printing, so nothing else marks the moment it cleared
            outage_lasted = outage.recovered()
            if outage_lasted is not None:
                print_outage_recovery(username, outage_lasted)
                alive_since = int(time.time())
            recovery_hint_tracker.reset()
            # Handle case where user still has no tracks
            if not recent_tracks or len(recent_tracks) == 0:
                # Wait for first track to appear
                debug_print("Waiting for the first scrobble", user=username, interval=f"{LASTFM_ACTIVE_CHECK_INTERVAL}s")
                close_pending_notice_block()
                time.sleep(LASTFM_ACTIVE_CHECK_INTERVAL)
                continue
            last_track_start_ts = int(recent_tracks[0].timestamp)
            new_track = lastfm_get_now_playing(username, user)
            email_sent = False
            webhook_sent = False

            lf_current_ts = int(time.time()) - LASTFM_ACTIVE_CHECK_INTERVAL

            # Detecting new Last.fm entries when user is offline
            if not lf_user_online:
                # If this is the first track appearing (user had no tracks before)
                if last_track_start_ts_old2 == 0:
                    debug_print("First scrobble appeared", user=username, outcome="OK")
                    print("\n*** First track appeared! Starting monitoring...\n")
                    last_track_start_ts_old2 = last_track_start_ts
                    lf_track_ts_start_old = last_track_start_ts
                if last_track_start_ts > last_track_start_ts_old2:
                    debug_print("New scrobbles while offline", user=username, latest=last_track_start_ts, previous=last_track_start_ts_old2)
                    print("\n*** New last.fm entries showed up while user was offline!\n")
                    lf_track_ts_start_old = last_track_start_ts
                    duplicate_entries = False
                    i = 0
                    added_entries_list = ""
                    try:
                        recent_tracks_while_offline = lastfm_get_recent_tracks(username, network, 100)
                        for previous, t, _nxt in previous_and_next(reversed(recent_tracks_while_offline)):
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
                        print_recovery_error(e, detail=f"Cannot list the tracks played while the tool was offline: {e}")

                    if i > 0 and (OFFLINE_ENTRIES_NOTIFICATION or webhook_event_enabled("offline_entries")):
                        if added_entries_list:
                            added_entries_list_mbody = f"\n\n{added_entries_list}"
                        m_subject = f"Last.fm user {username}: new entries showed up while user was offline"
                        m_body = f"New last.fm entries showed up while user was offline!{added_entries_list_mbody}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        send_notification_channels("offline_entries", m_subject, m_body, email_enabled=OFFLINE_ENTRIES_NOTIFICATION, subject_short=f"{username}: {i} new offline scrobbles", body_short=added_entries_list.strip())

                    print_cur_ts("\nTimestamp:\t\t\t")
                    alive_since = int(time.time())

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
                    if TRACK_SONGS:
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

                    alive_since = int(time.time())

                    if new_track == playing_track:
                        song_on_loop += 1
                        if song_on_loop == SONG_ON_LOOP_VALUE:
                            looped_songs += 1
                    else:
                        song_on_loop = 1

                    playing_track = new_track
                    artist = str(playing_track.artist)
                    track = str(playing_track.title)
                    album = str(playing_track.info.get('album', '')) if playing_track.info.get('album') else ""

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
                                    # Mark previous track as CONT in recent_songs_session
                                    if len(recent_songs_session) > 0 and recent_songs_session[-1]['artist'] == artist_old and recent_songs_session[-1]['track'] == track_old:
                                        recent_songs_session[-1]['cont'] = True
                                else:
                                    played_for += f" - SKIPPED ({int(listened_percentage * 100)}%)"
                                    played_for_html += f" - <b>SKIPPED</b> ({int(listened_percentage * 100)}%)"
                                    skipped_songs += 1
                                    # Mark previous track as skipped in recent_songs_session
                                    if len(recent_songs_session) > 0 and recent_songs_session[-1]['artist'] == artist_old and recent_songs_session[-1]['track'] == track_old:
                                        recent_songs_session[-1]['skipped'] = True
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
                            if PROGRESS_INDICATOR:
                                print("─" * HORIZONTAL_LINE)
                            print(f"User played the previous track for: {played_for}")
                            if not PROGRESS_INDICATOR:
                                print("─" * HORIZONTAL_LINE)
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
                                # Mark previous track as CONT in recent_songs_session
                                if len(recent_songs_session) > 0 and recent_songs_session[-1]['artist'] == artist_old and recent_songs_session[-1]['track'] == track_old:
                                    recent_songs_session[-1]['cont'] = True
                            else:
                                skipped_songs += 1
                                played_for_m_body = f"\n\nUser SKIPPED the previous track ({artist_old} - {track_old}) after: {played_for}"
                                played_for_m_body_html = f"<br><br>User <b>SKIPPED</b> the previous track (<b>{escape(artist_old)} - {escape(track_old)}</b>) after: {played_for_html}"
                                played_for_str = f"User SKIPPED the previous track after {played_for}"
                                # Mark previous track as skipped in recent_songs_session
                                if len(recent_songs_session) > 0 and recent_songs_session[-1]['artist'] == artist_old and recent_songs_session[-1]['track'] == track_old:
                                    recent_songs_session[-1]['skipped'] = True
                        else:
                            played_for_m_body = f"\n\nUser played the previous track ({artist_old} - {track_old}) for: {played_for}"
                            played_for_m_body_html = f"<br><br>User played the previous track (<b>{escape(artist_old)} - {escape(track_old)}</b>) for: {played_for_html}"
                            played_for_str = f"User played the previous track for: {played_for}"

                        if PROGRESS_INDICATOR:
                            print("─" * HORIZONTAL_LINE)
                        print(played_for_str)
                        if not PROGRESS_INDICATOR:
                            print("─" * HORIZONTAL_LINE)

                    if PROGRESS_INDICATOR:
                        print("─" * HORIZONTAL_LINE)

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

                    # Add current song to recent songs session list
                    recent_songs_session.append({
                        'artist': artist,
                        'track': track,
                        'timestamp': lf_track_ts_start,
                        'skipped': False,
                        'cont': False
                    })
                    # Keep only last INACTIVE_EMAIL_RECENT_SONGS_COUNT songs (or 5 if not set)
                    max_songs = INACTIVE_EMAIL_RECENT_SONGS_COUNT if INACTIVE_EMAIL_RECENT_SONGS_COUNT > 0 else 5
                    if len(recent_songs_session) > max_songs:
                        recent_songs_session.pop(0)

                    print(f"Track:\t\t\t\t{artist} - {track}")
                    if album:
                        print(f"Album:\t\t\t\t{album}")

                    track_duration, sp_track_uri_id, duration_mark = get_track_info(artist, track, album, network)

                    if track_duration > 0:
                        print(f"Duration:\t\t\t{display_time(track_duration)}{duration_mark}")

                    spotify_search_url, apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, lastfm_url, lastfm_album_url = get_spotify_apple_genius_search_urls(str(artist), str(track), album, network, playing_track)

                    music_urls_output = format_music_urls_console(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                    if music_urls_output:
                        print(f"\n{music_urls_output}")
                    lyrics_output = format_lyrics_urls_console(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                    if lyrics_output:
                        if not music_urls_output:
                            print()  # Add newline before lyrics when music URLs are disabled
                        print(lyrics_output)

                    last_activity_to_save = []
                    last_activity_to_save.append(lf_track_ts_start)
                    last_activity_to_save.append(artist)
                    last_activity_to_save.append(track)
                    last_activity_to_save.append(album)
                    save_last_activity_state(lastfm_last_activity_file, last_activity_to_save)

                    duration_m_body = ""
                    duration_m_body_html = ""
                    if track_duration > 0:
                        duration_m_body = f"\nDuration: {display_time(track_duration)}{duration_mark}"
                        duration_m_body_html = f"<br>Duration: {display_time(track_duration)}{duration_mark}"

                    # If tracking functionality is enabled then play the current song via Spotify client
                    if TRACK_SONGS and sp_track_uri_id:
                        if platform.system() == 'Darwin':       # macOS
                            spotify_macos_play_song(sp_track_uri_id)
                        elif platform.system() == 'Windows':    # Windows
                            spotify_win_play_song(sp_track_uri_id)
                        else:                                   # Linux variants
                            spotify_linux_play_song(sp_track_uri_id)

                    # User was offline and got active
                    # Handle case where user had no tracks initially and is becoming active for the first time
                    if (not lf_user_online and lf_active_ts_start == 0) or (not lf_user_online and (lf_track_ts_start - lf_active_ts_last) > LASTFM_INACTIVITY_CHECK and lf_active_ts_last > 0) or (not lf_user_online and lf_active_ts_last > 0 and app_started_and_user_offline):
                        app_started_and_user_offline = False
                        last_track_start_changed = ""
                        last_track_start_changed_html = ""
                        lf_active_ts_last_old = lf_active_ts_last
                        # If user had no tracks initially, lf_active_ts_last will be 0, so skip the check
                        if lf_active_ts_last > 0 and last_track_start_ts > (lf_active_ts_last + 60) and (int(time.time()) - last_track_start_ts > 240):
                            last_track_start_changed = f"\n(last track start changed from {get_short_date_from_ts(lf_active_ts_last)} to {get_short_date_from_ts(last_track_start_ts)} - offline mode ?)"
                            last_track_start_changed_html = f"<br>(last track start changed from <b>{get_short_date_from_ts(lf_active_ts_last)}</b> to <b>{get_short_date_from_ts(last_track_start_ts)}</b> - offline mode ?)"
                            lf_active_ts_last = last_track_start_ts

                        duplicate_entries = False
                        private_mode = ""
                        private_mode_html = ""
                        try:
                            p = 0
                            recent_tracks_while_offline = lastfm_get_recent_tracks(username, network, RECENT_TRACKS_NUMBER)
                            for previous, t, _nxt in previous_and_next(reversed(recent_tracks_while_offline)):
                                if previous:
                                    if previous.timestamp == t.timestamp:
                                        p += 1
                                        duplicate_entries = True
                        except Exception as e:
                            print_recovery_error(e, detail=f"Cannot re-read the recent tracks to check for duplicates: {e}")
                        if duplicate_entries:
                            private_mode = f"\n\nDuplicate entries ({p}) found, possible private mode ({get_range_of_dates_from_tss(lf_active_ts_last_old, lf_track_ts_start, short=True)})"
                            private_mode_html = f"<br><br>Duplicate entries ({p}) found, possible <b>private mode</b> (<b>{get_range_of_dates_from_tss(lf_active_ts_last_old, lf_track_ts_start, short=True)}</b>)"
                            print(f"\n*** Duplicate entries ({p}) found, possible PRIVATE MODE ({get_range_of_dates_from_tss(lf_active_ts_last_old, lf_track_ts_start, short=True)})")

                        # Only show timespan if user had previous activity
                        if lf_active_ts_last > 0:
                            print(f"\n*** User got ACTIVE after being offline for {calculate_timespan(int(lf_track_ts_start), int(lf_active_ts_last))}{last_track_start_changed}")
                            print(f"*** Last activity:\t\t{get_date_from_ts(lf_active_ts_last)}")
                        else:
                            print(f"\n*** User got ACTIVE (first track)")
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
                        recent_songs_session = [{'artist': artist, 'track': track, 'timestamp': lf_track_ts_start, 'skipped': False, 'cont': False}]
                        # Handle email subject and body - only include timespan if user had previous activity
                        if lf_active_ts_last > 0:
                            m_subject = f"Last.fm user {username} is active: '{artist} - {track}' (after {calculate_timespan(int(lf_track_ts_start), int(lf_active_ts_last), show_seconds=False)} - {get_short_date_from_ts(lf_active_ts_last)})"
                            offline_timespan = calculate_timespan(int(lf_track_ts_start), int(lf_active_ts_last))
                            last_activity_text = f"\n\nLast activity: {get_date_from_ts(lf_active_ts_last)}"
                            last_activity_html = f"<br><br>Last activity: <b>{get_date_from_ts(lf_active_ts_last)}</b>"
                        else:
                            m_subject = f"Last.fm user {username} is active: '{artist} - {track}'"
                            offline_timespan = ""
                            last_activity_text = ""
                            last_activity_html = ""
                        lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                        lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, artist, track)
                        lyrics_section_text = f"\n{lyrics_urls_text}" if lyrics_urls_text else ""
                        lyrics_section_html = f"<br>{lyrics_urls_html}" if lyrics_urls_html else ""
                        # Determine URLs for "Track:" and secondary URL field based on configuration
                        if USE_LASTFM_URL_IN_LAST_PLAYED:
                            track_url = lastfm_url
                            secondary_url = spotify_search_url
                            secondary_url_label = "Spotify URL"
                        else:
                            track_url = spotify_search_url
                            secondary_url = lastfm_url
                            secondary_url_label = "Last.fm URL"
                        music_urls_text = format_music_urls_email_text(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                        music_urls_html = format_music_urls_email_html(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, artist, track, secondary_url, secondary_url_label)
                        music_section_text = f"\n\n{music_urls_text}\n" if music_urls_text else "\n"
                        music_section_html = f"<br><br>{music_urls_html}" if music_urls_html else ""
                        # When both music and lyrics are empty, don't add <br><br> here because there's a hardcoded <br><br> after played_for_m_body_html
                        if not music_urls_html and not lyrics_urls_html:
                            music_section_html = ""
                            lyrics_section_html = ""
                        elif not music_urls_html:
                            music_section_html = "<br>"
                        album_line = f"Album: {album}" if album else ""
                        album_html = f'<a href="{lastfm_album_url}">{escape(album)}</a>' if (ENABLE_LASTFM_ALBUM_URL and lastfm_album_url) else escape(album)
                        album_html_line = f"<br>Album: {album_html}" if album else ""
                        if lf_active_ts_last > 0:
                            m_body = f"Track: {artist} - {track}{duration_m_body}\n{album_line}{music_section_text}{lyrics_section_text}{played_for_m_body}\n\nFriend got active after being offline for {offline_timespan}{last_track_start_changed}{private_mode}{last_activity_text}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                            m_body_html = f"<html><head></head><body>Track: <b><a href=\"{track_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}{album_html_line}{music_section_html}{lyrics_section_html}{played_for_m_body_html}<br><br>Friend got active after being offline for <b>{offline_timespan}</b>{last_track_start_changed_html}{private_mode_html}{last_activity_html}{get_cur_ts('<br>Timestamp: ')}</body></html>"
                        else:
                            lyrics_section_text_fresh = f"\n{lyrics_urls_text}\n" if lyrics_urls_text else "\n"
                            lyrics_section_html_fresh = f"<br>{lyrics_urls_html}<br>" if lyrics_urls_html else "<br>"
                            # When both music and lyrics are empty, check if played_for_m_body_html is empty
                            # If it's empty, we need <br><br> before timestamp; if not, it already starts with <br><br>
                            if not music_urls_html and not lyrics_urls_html:
                                if not played_for_m_body_html:
                                    music_section_html = "<br><br>"
                                else:
                                    music_section_html = ""
                                lyrics_section_html_fresh = ""
                            elif not music_urls_html:
                                music_section_html = "<br>"
                            m_body = f"Track: {artist} - {track}{duration_m_body}\n{album_line}{music_section_text}{lyrics_section_text_fresh}{played_for_m_body}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                            m_body_html = f"<html><head></head><body>Track: <b><a href=\"{track_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}{album_html_line}{music_section_html}{lyrics_section_html_fresh}{played_for_m_body_html}{get_cur_ts('<br>Timestamp: ')}</body></html>"

                        if ACTIVE_NOTIFICATION or webhook_event_enabled("active"):
                            email_delivered, webhook_delivered = send_notification_channels("active", m_subject, m_body, m_body_html, email_enabled=ACTIVE_NOTIFICATION, subject_short=f"{username} is active", body_short="\n".join(value for value in (track, artist, album) if value))
                            email_sent = email_sent or email_delivered
                            webhook_sent = webhook_sent or webhook_delivered

                    track_matched = track.upper() in tracks_upper or album.upper() in tracks_upper
                    email_song_enabled = ((TRACK_NOTIFICATION and track_matched) or SONG_NOTIFICATION) and not email_sent
                    webhook_song_enabled = ((webhook_event_enabled("track") and track_matched) or webhook_event_enabled("song")) and not webhook_sent
                    if email_song_enabled or webhook_song_enabled:
                        timespan_str = f"\n\nSongs Played: {listened_songs}"
                        timespan_str_html = f"<br><br>Songs Played: {listened_songs}"
                        # Only show timespan if lf_active_ts_start is properly set (not 0) and different from current track start
                        if lf_active_ts_start > 0 and lf_track_ts_start != lf_active_ts_start:
                            timespan = calculate_timespan(int(lf_track_ts_start), int(lf_active_ts_start))
                            timespan_str += f" ({timespan})"
                            timespan_str_html += f" ({timespan})"
                        m_subject = f"Last.fm user {username}: '{artist} - {track}'"
                        lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                        lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, artist, track)
                        # Determine URLs for "Track:" and secondary URL field based on configuration
                        if USE_LASTFM_URL_IN_LAST_PLAYED:
                            track_url = lastfm_url
                            secondary_url = spotify_search_url
                            secondary_url_label = "Spotify URL"
                        else:
                            track_url = spotify_search_url
                            secondary_url = lastfm_url
                            secondary_url_label = "Last.fm URL"
                        music_urls_text = format_music_urls_email_text(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                        music_urls_html = format_music_urls_email_html(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, artist, track, secondary_url, secondary_url_label)
                        music_section_text = f"\n\n{music_urls_text}\n" if music_urls_text else "\n"
                        music_section_html = f"<br><br>{music_urls_html}" if music_urls_html else ""
                        lyrics_section_text = f"\n{lyrics_urls_text}" if lyrics_urls_text else ""
                        lyrics_section_html = f"<br>{lyrics_urls_html}" if lyrics_urls_html else ""
                        # When both music and lyrics are empty, don't add <br><br> here because there's a hardcoded <br><br> in get_cur_ts
                        if not music_urls_html and not lyrics_urls_html:
                            music_section_html = ""
                            lyrics_section_html = ""
                        elif not music_urls_html:
                            music_section_html = "<br>"
                        album_line = f"Album: {album}" if album else ""
                        album_html = f'<a href="{lastfm_album_url}">{escape(album)}</a>' if (ENABLE_LASTFM_ALBUM_URL and lastfm_album_url) else escape(album)
                        album_html_line = f"<br>Album: {album_html}" if album else ""
                        m_body = f"Track: {artist} - {track}{duration_m_body}\n{album_line}{music_section_text}{lyrics_section_text}{played_for_m_body}{timespan_str}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Track: <b><a href=\"{track_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}{album_html_line}{music_section_html}{lyrics_section_html}{played_for_m_body_html}{timespan_str_html}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"

                    # Check for loop first, before track/song notifications
                    if song_on_loop == SONG_ON_LOOP_VALUE:
                        print("─" * HORIZONTAL_LINE)
                        print(f"User plays song on LOOP ({song_on_loop} times)")
                        print("─" * HORIZONTAL_LINE)

                    loop_email_enabled = song_on_loop == SONG_ON_LOOP_VALUE and SONG_ON_LOOP_NOTIFICATION and not email_sent
                    loop_webhook_enabled = song_on_loop == SONG_ON_LOOP_VALUE and webhook_event_enabled("loop") and not webhook_sent
                    if loop_email_enabled or loop_webhook_enabled:
                        timespan_str = f"\n\nSongs Played: {listened_songs}"
                        timespan_str_html = f"<br><br>Songs Played: {listened_songs}"
                        # Only show timespan if lf_active_ts_start is properly set (not 0) and different from current track start
                        if lf_active_ts_start > 0 and lf_track_ts_start != lf_active_ts_start:
                            timespan = calculate_timespan(int(lf_track_ts_start), int(lf_active_ts_start))
                            timespan_str += f" ({timespan})"
                            timespan_str_html += f" ({timespan})"
                        m_subject = f"Last.fm user {username} plays song on loop: '{artist} - {track}'"
                        lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                        lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, artist, track)
                        # Determine URLs for "Track:" and secondary URL field based on configuration
                        if USE_LASTFM_URL_IN_LAST_PLAYED:
                            track_url = lastfm_url
                            secondary_url = spotify_search_url
                            secondary_url_label = "Spotify URL"
                        else:
                            track_url = spotify_search_url
                            secondary_url = lastfm_url
                            secondary_url_label = "Last.fm URL"
                        music_urls_text = format_music_urls_email_text(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                        music_urls_html = format_music_urls_email_html(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, artist, track, secondary_url, secondary_url_label)
                        music_section_text = f"\n\n{music_urls_text}\n" if music_urls_text else "\n"
                        music_section_html = f"<br><br>{music_urls_html}" if music_urls_html else ""
                        lyrics_section_text = f"\n{lyrics_urls_text}" if lyrics_urls_text else ""
                        lyrics_section_html = f"<br>{lyrics_urls_html}" if lyrics_urls_html else ""
                        # When both music and lyrics are empty, don't add <br><br> here because there's a hardcoded <br><br> before "User plays song on LOOP"
                        if not music_urls_html and not lyrics_urls_html:
                            music_section_html = ""
                            lyrics_section_html = ""
                        elif not music_urls_html:
                            music_section_html = "<br>"
                        album_line = f"Album: {album}" if album else ""
                        album_html = f'<a href="{lastfm_album_url}">{escape(album)}</a>' if (ENABLE_LASTFM_ALBUM_URL and lastfm_album_url) else escape(album)
                        album_html_line = f"<br>Album: {album_html}" if album else ""
                        m_body = f"Track: {artist} - {track}{duration_m_body}\n{album_line}{music_section_text}{lyrics_section_text}{played_for_m_body}\n\nUser plays song on LOOP ({song_on_loop} times){timespan_str}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Track: <b><a href=\"{track_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}{album_html_line}{music_section_html}{lyrics_section_html}{played_for_m_body_html}<br><br>User plays song on LOOP (<b>{song_on_loop}</b> times){timespan_str_html}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                        email_delivered, webhook_delivered = send_notification_channels("loop", m_subject, m_body, m_body_html, email_enabled=loop_email_enabled, webhook_enabled=loop_webhook_enabled, subject_short=f"{username} is playing a song on loop", body_short="\n".join(value for value in (track, artist, album) if value))
                        email_sent = email_sent or email_delivered
                        webhook_sent = webhook_sent or webhook_delivered

                    # Send track/song notifications only if loop notification was not sent
                    if track_matched:
                        print("\n*** Track/album matched with the list!")

                        track_email_enabled = TRACK_NOTIFICATION and not email_sent
                        track_webhook_enabled = webhook_event_enabled("track") and not webhook_sent
                        if track_email_enabled or track_webhook_enabled:
                            email_delivered, webhook_delivered = send_notification_channels("track", m_subject, m_body, m_body_html, email_enabled=track_email_enabled, webhook_enabled=track_webhook_enabled, subject_short=f"{username}: monitored track", body_short="\n".join(value for value in (track, artist, album) if value))
                            email_sent = email_sent or email_delivered
                            webhook_sent = webhook_sent or webhook_delivered

                    song_email_enabled = SONG_NOTIFICATION and not email_sent
                    song_webhook_enabled = webhook_event_enabled("song") and not webhook_sent
                    if song_email_enabled or song_webhook_enabled:
                        email_delivered, webhook_delivered = send_notification_channels("song", m_subject, m_body, m_body_html, email_enabled=song_email_enabled, webhook_enabled=song_webhook_enabled, subject_short=f"{username}: song changed", body_short="\n".join(value for value in (track, artist, album) if value))
                        email_sent = email_sent or email_delivered
                        webhook_sent = webhook_sent or webhook_delivered

                    lf_user_online = True
                    lf_active_ts_last = int(time.time())

                    artist_old = artist
                    track_old = track

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(lf_track_ts_start)), artist, track, album)
                    except Exception as e:
                        print_recovery_error(e, context="file.unwritable")
                    if listened_songs:
                        if lf_track_ts_start == lf_active_ts_start:
                            print(f"\nSongs Played:\t\t\t{listened_songs}")
                        else:
                            # Only show timespan if lf_active_ts_start is properly set (not 0) and different from current track start
                            if lf_active_ts_start > 0 and lf_track_ts_start != lf_active_ts_start:
                                print(f"\nSongs Played:\t\t\t{listened_songs} ({calculate_timespan(int(lf_track_ts_start), int(lf_active_ts_start))})")
                            else:
                                print(f"\nSongs Played:\t\t\t{listened_songs}")

                    print_cur_ts("\nTimestamp:\t\t\t")
                # Track has not changed, user is online and continues playing
                else:
                    lf_active_ts_last = int(time.time())
                    # We display progress indicator if flag is enabled
                    if lf_user_online and PROGRESS_INDICATOR:
                        ts = datetime.fromtimestamp(lf_active_ts_last).strftime('%H:%M:%S')
                        delta_ts = lf_active_ts_last - lf_track_ts_start_after_resume
                        if delta_ts > 0:
                            delta_diff_str = "%02d:%02d:%02d" % (delta_ts // 3600, delta_ts // 60 % 60, delta_ts % 60)
                        else:
                            delta_diff_str = "00:00:00"
                        print(f"# {ts} +{delta_diff_str}")
            # User is offline (does not play music at the moment)
            else:

                # User paused playing the music
                if ((int(time.time()) - lf_active_ts_last) > (LASTFM_ACTIVE_CHECK_INTERVAL * LASTFM_BREAK_CHECK_MULTIPLIER)) and lf_user_online and lf_active_ts_last > 0 and lf_active_ts_start > 0 and (LASTFM_ACTIVE_CHECK_INTERVAL * LASTFM_BREAK_CHECK_MULTIPLIER) < LASTFM_INACTIVITY_CHECK and LASTFM_BREAK_CHECK_MULTIPLIER > 0 and playing_paused is False:
                    playing_paused = True
                    playing_paused_ts = lf_active_ts_last
                    pauses_number += 1
                    if PROGRESS_INDICATOR:
                        print("─" * HORIZONTAL_LINE)
                    print(f"User PAUSED playing after {calculate_timespan(int(playing_resumed_ts), int(playing_paused_ts))} (inactivity timer: {display_time(LASTFM_BREAK_CHECK_MULTIPLIER * LASTFM_ACTIVE_CHECK_INTERVAL)})")
                    print(f"Last activity:\t\t\t{get_date_from_ts(lf_active_ts_last)}")
                    print_cur_ts("\nTimestamp:\t\t\t")
                    # If tracking functionality is enabled then PAUSE the current song via Spotify client
                    if TRACK_SONGS:
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
                        if not PROGRESS_INDICATOR:
                            print("─" * HORIZONTAL_LINE)
                    # Handling how long user played the last track - in case track duration is NOT available
                    elif track_duration <= 0 and lf_track_ts_start_after_resume > 0:
                        played_for = display_time((lf_active_ts_last) - lf_track_ts_start_after_resume)

                        played_for_m_body = f"\n\nUser played the last track for: {played_for}"
                        played_for_m_body_html = f"<br><br>User played the last track for: <b>{played_for}</b>"
                        played_for_str = f"User played the last track for: {played_for}"

                        print(played_for_str)
                        if not PROGRESS_INDICATOR:
                            print("─" * HORIZONTAL_LINE)

                    if PROGRESS_INDICATOR:
                        print("─" * HORIZONTAL_LINE)

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
                    if TRACK_SONGS:
                        if SP_USER_GOT_OFFLINE_TRACK_ID:
                            if platform.system() == 'Darwin':       # macOS
                                spotify_macos_play_song(SP_USER_GOT_OFFLINE_TRACK_ID)
                                if SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE > 0:
                                    debug_print("Waiting before pausing the finishing track", delay=f"{SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE}s")
                                    time.sleep(SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE)
                                    spotify_macos_play_pause("pause")
                            elif platform.system() == 'Windows':    # Windows
                                pass
                            else:                                   # Linux variants
                                spotify_linux_play_song(SP_USER_GOT_OFFLINE_TRACK_ID)
                                if SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE > 0:
                                    debug_print("Waiting before pausing the finishing track", delay=f"{SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE}s")
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
                    save_last_activity_state(lastfm_last_activity_file, last_activity_to_save)
                    if INACTIVE_NOTIFICATION or webhook_event_enabled("inactive"):
                        # Format recently listened songs list for email (skip if only 1 song)
                        recent_songs_mbody = ""
                        recent_songs_mbody_html = ""
                        if listened_songs > 1 and len(recent_songs_session) > 0 and INACTIVE_EMAIL_RECENT_SONGS_COUNT > 0:
                            # Get last up to INACTIVE_EMAIL_RECENT_SONGS_COUNT songs
                            songs_to_show = recent_songs_session[-min(INACTIVE_EMAIL_RECENT_SONGS_COUNT, len(recent_songs_session)):]
                            recent_songs_list = []
                            recent_songs_list_html = []
                            for song in songs_to_show:
                                song_date = get_date_from_ts(song['timestamp'])
                                marker = ""
                                marker_html = ""
                                if song.get('cont', False):
                                    marker = ", CONT"
                                    marker_html = ", <b>CONT</b>"
                                elif song.get('skipped', False):
                                    marker = ", SKIPPED"
                                    marker_html = ", <b>SKIPPED</b>"
                                recent_songs_list.append(f"{song['artist']} - {song['track']} ({song_date}{marker})")
                                recent_songs_list_html.append(f"<b>{escape(song['artist'])} - {escape(song['track'])}</b> ({song_date}{marker_html})")
                            if recent_songs_list:
                                recent_songs_mbody = f"\n\nRecently listened songs in this session:\n" + "\n".join(recent_songs_list)
                                recent_songs_mbody_html = f"<br><br>Recently listened songs in this session:<br>" + "<br>".join(recent_songs_list_html)

                        m_subject = f"Last.fm user {username} is inactive: '{artist} - {track}' (after {calculate_timespan(int(lf_active_ts_last), int(lf_active_ts_start), show_seconds=False)}: {get_range_of_dates_from_tss(lf_active_ts_start, lf_active_ts_last, short=True)})"
                        # Get URLs for the last played track
                        spotify_search_url, apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, lastfm_url, lastfm_album_url = get_spotify_apple_genius_search_urls(str(artist), str(track), album, network)
                        lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                        lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, artist, track)
                        lyrics_section_text = f"\n{lyrics_urls_text}\n\n" if lyrics_urls_text else "\n\n"
                        lyrics_section_html = f"<br>{lyrics_urls_html}<br><br>" if lyrics_urls_html else "<br><br>"
                        # Determine URLs for "Last played:" and secondary URL field based on configuration
                        if USE_LASTFM_URL_IN_LAST_PLAYED:
                            last_played_url = lastfm_url
                            secondary_url = spotify_search_url
                            secondary_url_label = "Spotify URL"
                        else:
                            last_played_url = spotify_search_url
                            secondary_url = lastfm_url
                            secondary_url_label = "Last.fm URL"
                        music_urls_text = format_music_urls_email_text(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                        music_urls_html = format_music_urls_email_html(spotify_search_url, lastfm_url, lastfm_album_url, apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, artist, track, secondary_url, secondary_url_label)
                        music_section_text = f"\n\n{music_urls_text}\n" if music_urls_text else "\n"
                        music_section_html = f"<br><br>{music_urls_html}" if music_urls_html else ""
                        # When both music and lyrics are empty, use single <br><br> instead of <br> + <br><br>
                        if not music_urls_html and not lyrics_urls_html:
                            music_section_html = "<br><br>"
                            lyrics_section_html = ""
                        elif not music_urls_html:
                            music_section_html = "<br>"
                        album_line = f"Album: {album}" if album else ""
                        album_html = f'<a href="{lastfm_album_url}">{escape(album)}</a>' if (ENABLE_LASTFM_ALBUM_URL and lastfm_album_url) else escape(album)
                        album_html_line = f"<br>Album: {album_html}" if album else ""
                        m_body = f"Last played: {artist} - {track}{duration_m_body}\n{album_line}{music_section_text}{lyrics_section_text}User got inactive after listening to music for {calculate_timespan(int(lf_active_ts_last), int(lf_active_ts_start))}\nUser played music from {get_range_of_dates_from_tss(lf_active_ts_start, lf_active_ts_last, short=True, between_sep=' to ')}{paused_mbody}{listened_songs_mbody}{played_for_m_body}{recent_songs_mbody}\n\nLast activity: {get_date_from_ts(lf_active_ts_last)}\nInactivity timer: {display_time(LASTFM_INACTIVITY_CHECK)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{last_played_url}\">{escape(artist)} - {escape(track)}</a></b>{duration_m_body_html}{album_html_line}{music_section_html}{lyrics_section_html}User got inactive after listening to music for <b>{calculate_timespan(int(lf_active_ts_last), int(lf_active_ts_start))}</b><br>User played music from <b>{get_range_of_dates_from_tss(lf_active_ts_start, lf_active_ts_last, short=True, between_sep='</b> to <b>')}</b>{paused_mbody_html}{listened_songs_mbody_html}{played_for_m_body_html}{recent_songs_mbody_html}<br><br>Last activity: <b>{get_date_from_ts(lf_active_ts_last)}</b><br>Inactivity timer: {display_time(LASTFM_INACTIVITY_CHECK)}{get_cur_ts('<br>Timestamp: ')}</body></html>"

                        email_delivered, webhook_delivered = send_notification_channels("inactive", m_subject, m_body, m_body_html, email_enabled=INACTIVE_NOTIFICATION, subject_short=f"{username} is inactive", body_short="\n".join(value for value in (track, artist, album) if value))
                        email_sent = email_sent or email_delivered
                        webhook_sent = webhook_sent or webhook_delivered
                    lf_active_ts_start = 0
                    playing_track = None
                    last_track_start_ts = 0
                    listened_songs = 0
                    looped_songs = 0
                    skipped_songs = 0
                    pauses_number = 0
                    recent_songs_session = []
                    print_cur_ts("\nTimestamp:\t\t\t")
                    alive_since = int(time.time())

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

            # Not gated on the user being offline, since a user who listens for days is exactly when a silent run looks dead
            if LIVENESS_REMINDER_SECONDS and int(time.time()) - alive_since >= LIVENESS_REMINDER_SECONDS:
                print_liveness_banner(f"Monitoring healthy for {username}. The user is {'active' if lf_user_online else 'inactive'} with no activity change since the last check")
                alive_since = int(time.time())

        except Exception as e:

            debug_print("Monitoring cycle", check=f"#{check_count + 1}", user=username, outcome="failed", error=f"{type(e).__name__}: {e}")
            check_outcome = "failed"

            advice = classify_recovery_error(e, context="runtime")
            sleep_interval = LASTFM_ACTIVE_CHECK_INTERVAL if lf_user_online else LASTFM_CHECK_INTERVAL
            retry_note = f"retrying in {display_time(sleep_interval)}"

            if advice.code == "lastfm.unavailable":
                if not error_500_start_ts:
                    error_500_start_ts = int(time.time())
                    error_500_counter = 1
                else:
                    error_500_counter += 1

            if advice.code in ("network.unavailable", "network.timeout", "lastfm.rate_limited") or str(e) == '':
                if not error_network_issue_start_ts:
                    error_network_issue_start_ts = int(time.time())
                    error_network_issue_counter = 1
                else:
                    error_network_issue_counter += 1

            # A failure that has not changed is left to the liveness cadence rather than repeated on every check
            outage_outcome = outage.failed(advice, LIVENESS_REMINDER_SECONDS)
            report_in_full = outage_outcome == "full"
            reported = False

            # With the liveness banner off the aggregated 50x and network summaries keep their old cadence
            if outage_outcome == "repeat":
                if error_500_start_ts and (error_500_counter >= ERROR_500_NUMBER_LIMIT and (int(time.time()) - error_500_start_ts) >= ERROR_500_TIME_LIMIT):
                    print_recovery_error(e, "runtime", retry_note=retry_note, label=f"Error 50x ({error_500_counter}x times in the last {display_time((int(time.time()) - error_500_start_ts))})", tracker=recovery_hint_tracker)
                    reported = True
                    error_500_start_ts = 0
                    error_500_counter = 0

                elif error_network_issue_start_ts and (error_network_issue_counter >= ERROR_NETWORK_ISSUES_NUMBER_LIMIT and (int(time.time()) - error_network_issue_start_ts) >= ERROR_NETWORK_ISSUES_TIME_LIMIT):
                    print_recovery_error(e, "runtime", retry_note=retry_note, label=f"Error with network ({error_network_issue_counter}x times in the last {display_time((int(time.time()) - error_network_issue_start_ts))})", tracker=recovery_hint_tracker)
                    reported = True
                    error_network_issue_start_ts = 0
                    error_network_issue_counter = 0

                elif not error_500_start_ts and not error_network_issue_start_ts:
                    report_in_full = True

            if outage_outcome == "degraded":
                print_outage_liveness(username, advice, outage.since)
                alive_since = int(time.time())

            elif report_in_full:
                print_recovery_error(e, "runtime", retry_note=retry_note, tracker=recovery_hint_tracker)
                reported = True

            # Attempted on every failing check rather than only on the report, so a channel that failed is tried again
            error_email_enabled = ERROR_NOTIFICATION and not email_sent and advice.code == "auth.api_key_invalid"
            error_webhook_enabled = webhook_event_enabled("error") and not webhook_sent
            if error_email_enabled or error_webhook_enabled:
                if advice.code == "auth.api_key_invalid":
                    m_subject = f"lastfm_monitor: API key error! (user: {username})"
                else:
                    m_subject = f"lastfm_monitor: monitoring error (user: {username})"
                m_body = f"{advice.summary}{nl_ch}{nl_ch}To fix: {advice.fix}{nl_ch}{nl_ch}Last.fm Monitor will retry in {display_time(sleep_interval)}.{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                m_body_html = f"<html><head></head><body>{escape(advice.summary)}<br><br>To fix: {escape(advice.fix)}<br><br>Last.fm Monitor will retry in {escape(display_time(sleep_interval))}.{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                email_delivered, webhook_delivered = send_notification_channels("error", m_subject, m_body, m_body_html, email_enabled=error_email_enabled, webhook_enabled=error_webhook_enabled)
                email_sent = email_sent or email_delivered
                webhook_sent = webhook_sent or webhook_delivered
                reported = True

            # One trailer for whatever this check printed, since a retry can be the only thing on the screen
            if reported:
                print_cur_ts("Timestamp:\t\t\t")

        if lf_user_online:
            check_interval = LASTFM_ACTIVE_CHECK_INTERVAL
        else:
            check_interval = LASTFM_CHECK_INTERVAL

        # Any verbose line this check printed on its own is closed here, so one check never leaves a floating line
        close_pending_notice_block()

        check_count += 1
        wait_reason = "the last check failed" if check_outcome == "failed" else ("the user is online" if lf_user_online else "the user is offline")
        debug_print("Completed check", check=f"#{check_count}", user=username, outcome=check_outcome, state="online" if lf_user_online else "offline", track=str(playing_track) if playing_track else None)
        debug_print("Waiting for the next check", check=f"#{check_count}", interval=f"{check_interval}s", reason=wait_reason, state="online" if lf_user_online else "offline")
        time.sleep(check_interval)

        new_track = None


# Applies only the explicitly supplied --verbose and --debug flags so the command line always wins over the config file
def apply_diagnostic_cli_flags(args):
    global VERBOSE_MODE, DEBUG_MODE
    if getattr(args, "verbose", None):
        VERBOSE_MODE = True
    if getattr(args, "debug_mode", None):
        DEBUG_MODE = True


# Applies validated one-run webhook command-line overrides to runtime settings
def apply_webhook_cli_overrides(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    global WEBHOOK_ENABLED, WEBHOOK_URL, WEBHOOK_PROVIDER, WEBHOOK_ACTIVE_NOTIFICATION, WEBHOOK_INACTIVE_NOTIFICATION, WEBHOOK_TRACK_NOTIFICATION, WEBHOOK_SONG_NOTIFICATION, WEBHOOK_SONG_ON_LOOP_NOTIFICATION, WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION, WEBHOOK_FOLLOWERS_NOTIFICATION, WEBHOOK_FOLLOWINGS_NOTIFICATION, WEBHOOK_PROFILE_NOTIFICATION, WEBHOOK_ERROR_NOTIFICATION
    if args.webhook_provider is not None:
        WEBHOOK_PROVIDER = str(args.webhook_provider)
    if args.webhook_url is not None:
        if not validate_webhook_url(args.webhook_url):
            parser.error("--webhook-url must contain a complete HTTPS link without embedded credentials")
        WEBHOOK_URL = str(args.webhook_url).strip()
        WEBHOOK_ENABLED = True
        record_secret_source("WEBHOOK_URL", "command line")
    if args.webhook_enabled is not None:
        WEBHOOK_ENABLED = args.webhook_enabled
    event_overrides = (
        (args.webhook_active, "WEBHOOK_ACTIVE_NOTIFICATION"),
        (args.webhook_inactive, "WEBHOOK_INACTIVE_NOTIFICATION"),
        (args.webhook_track, "WEBHOOK_TRACK_NOTIFICATION"),
        (args.webhook_song_changes, "WEBHOOK_SONG_NOTIFICATION"),
        (args.webhook_loop, "WEBHOOK_SONG_ON_LOOP_NOTIFICATION"),
        (args.webhook_offline_entries, "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION"),
        (args.webhook_followers, "WEBHOOK_FOLLOWERS_NOTIFICATION"),
        (args.webhook_followings, "WEBHOOK_FOLLOWINGS_NOTIFICATION"),
        (args.webhook_profile, "WEBHOOK_PROFILE_NOTIFICATION"),
    )
    for enabled, setting in event_overrides:
        if enabled is True:
            WEBHOOK_ENABLED = True
            globals()[setting] = True
    if args.webhook_errors is not None:
        WEBHOOK_ERROR_NOTIFICATION = args.webhook_errors
        if args.webhook_errors:
            WEBHOOK_ENABLED = True
    if args.webhook_provider is None:
        detected_provider = detect_webhook_provider(WEBHOOK_URL)
        configured_provider = normalized_webhook_provider()
        if detected_provider and detected_provider != configured_provider:
            WEBHOOK_PROVIDER = detected_provider
            print(f"* Warning: Configured webhook provider did not match the URL. Using {webhook_provider_display_name(detected_provider)}.")


# The four shared status markers. A fifth neutral marker is the single biggest source of drift between these
# tools, because every state it would cover is a state the others already call PASS
DOCTOR_STATUSES = ("PASS", "WARN", "FAIL", "SKIP")

# The fixed section order the report renders in, chosen so each section depends only on the ones above it
DOCTOR_SECTIONS = ("Environment", "Configuration", "Authentication", "Spotify metadata", "Connectivity", "Target", "Notifications")

# Delivery results are printed as they happen rather than inside a section, but they still count in the summary
DOCTOR_DELIVERY_SECTION = "Optional delivery tests"

# Width of the transient progress line currently on screen, so the next write can erase exactly what it drew
DOCTOR_PROGRESS_WIDTH = 0

# The theme entry each doctor result marker is drawn in, so a failure reads as one at a glance
DOCTOR_MARK_STYLES = {"PASS": "boolean_true", "WARN": "warning", "FAIL": "error", "SKIP": "info"}


# One doctor result, held until the whole report is rendered
DoctorCheck = namedtuple("DoctorCheck", ["section", "status", "label", "detail", "advice"])
DoctorCheck.__new__.__defaults__ = ("", None)


# Collects doctor checks plus the work later checks reuse, so nothing is fetched or authenticated twice
class DoctorReport:
    # Starts an empty report with no Last.fm client and no channel marked ready for a delivery test
    def __init__(self):
        self.checks: List[Any] = []
        self.network: Any = None
        self.user: Any = None
        # Structural flags, so offering a delivery test never depends on matching a rendered label
        self.email_ready = False
        self.webhook_ready = False


# Builds one doctor check, keeping construction in one place so the shape cannot drift between sections
def make_doctor_check(section, status, label, detail="", advice=None):
    if status not in DOCTOR_STATUSES:
        raise ValueError(f"Unsupported doctor status: {status}")
    # A row the user has to act on is useless without an action, so the row is rejected rather than printed bare
    if status in ("WARN", "FAIL") and (advice is None or not advice.fix):
        raise ValueError(f"Doctor {status} rows require a fix")
    # Several advice objects carry the same text as their summary and printing it twice reads as two problems
    return DoctorCheck(section, status, label, "" if str(detail).strip() == str(label).strip() else sanitize_error_text(detail), advice)


# Joins setting names the way every doctor detail and action in this family lists them
def join_setting_names(names, conjunction):
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} {conjunction} {names[-1]}"


# Reports the Python version and every library the tool imports, required ones apart from optional ones
def doctor_check_environment(version_info=None, spec_finder=None):
    checks = []
    selected_version = sys.version_info if version_info is None else version_info
    version_text = ".".join(str(part) for part in tuple(selected_version)[:3])
    minimum_detail = f"Minimum supported version: {MINIMUM_PYTHON_VERSION_TEXT}"
    if tuple(selected_version)[:2] >= MINIMUM_PYTHON_VERSION:
        checks.append(make_doctor_check("Environment", "PASS", f"Python {version_text} is supported", minimum_detail))
    else:
        advice = make_recovery_advice("dependency.missing", f"Python {version_text} is unsupported", recovery_fix_with_guide(f"Install Python {MINIMUM_PYTHON_VERSION_TEXT} or newer then retry", INSTALL_GUIDE_URL), False)
        checks.append(make_doctor_check("Environment", "FAIL", advice.summary, minimum_detail, advice))

    find_spec = importlib.util.find_spec if spec_finder is None else spec_finder

    # Returns whether one module can be located, treating an unimportable parent as absent
    def module_present(module_name):
        try:
            return find_spec(module_name) is not None
        except (ImportError, ValueError):
            return False

    for module_name, package_name in (("pylast", "pylast"), ("requests", "requests"), ("dateutil", "python-dateutil"), ("pyotp", "pyotp")):
        if module_present(module_name):
            checks.append(make_doctor_check("Environment", "PASS", f"Required dependency {package_name} is installed"))
        else:
            advice = make_recovery_advice("dependency.missing", f"Required dependency {package_name} is missing", recovery_fix_with_guide(f'Install it with: {install_dependency_command(package_name)}', INSTALL_GUIDE_URL), False)
            checks.append(make_doctor_check("Environment", "FAIL", advice.summary, advice=advice))

    optional = [
        ("dotenv", "python-dotenv", "Secrets can only come from environment variables or the configuration file", "Used only for reading secrets from a dotenv file"),
        ("spotipy", "spotipy", "The Spotify OAuth app metadata backend is unavailable, leaving the anonymous web player", "Used only for the Spotify OAuth app metadata backend"),
        ("bs4", "beautifulsoup4", "Follower, following and profile tracking cannot run", "Used only for follower, following and profile tracking"),
        ("wcwidth", "wcwidth", "Screen truncation is disabled and lines are printed in full", "Used only to measure display width for screen truncation"),
    ]
    # The classic Command Prompt is the only place this library changes anything, so a machine it cannot
    # affect is not warned about a package it does not need
    if platform.system() == "Windows":
        optional.append(("colorama", "colorama", "Coloured output may not render in the classic Windows Command Prompt", "Used only for coloured output in the older Windows Command Prompt"))
    for module_name, package_name, purpose, use in optional:
        if module_present(module_name):
            checks.append(make_doctor_check("Environment", "PASS", f"Optional dependency {package_name} is installed", use))
        else:
            advice = make_recovery_advice("dependency.missing", f"Optional dependency {package_name} is not installed", recovery_fix_with_guide(f'Install it with: {install_dependency_command(package_name)}', INSTALL_GUIDE_URL), False)
            checks.append(make_doctor_check("Environment", "WARN", advice.summary, f"{purpose}. Every other feature is unaffected", advice))
    return checks


# The name each secret source is reported under, spelled the way every sibling monitor spells it
DOCTOR_SECRET_SOURCE_LABELS = {"config file": "configuration file", "dotenv file": "dotenv file", "environment": "environment", "command line": "command line"}


# Reports which secrets are in effect and where each one was read from, by name and never by value
def doctor_secret_checks():
    checks = [make_doctor_check("Configuration", "PASS", f"Secrets loaded from the {DOCTOR_SECRET_SOURCE_LABELS[source]}", ", ".join(names)) for source, names in secrets_by_source()]
    if not checks:
        checks.append(make_doctor_check("Configuration", "PASS", "No secrets loaded", "Nothing was read from a dotenv file, the environment, the configuration file or the command line"))
    return checks


# Returns the log file monitoring will actually write, which needs the target-derived suffix
def build_log_path(base_path, suffix):
    log_path = Path(os.path.expanduser(str(base_path)))
    if log_path.suffix == "" and suffix:
        log_path = log_path.parent / f"{log_path.name}_{suffix}.log"
    return log_path


# Returns the closest parent that exists, so writability is judged without creating anything
def nearest_existing_parent(path):
    candidate = Path(path).expanduser()
    if candidate.exists():
        return candidate if candidate.is_dir() else candidate.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


# Reports whether one file monitoring will write can be created, without creating anything
def doctor_destination_check(label, destination, section="Configuration"):
    selected = Path(destination).expanduser()
    parent = nearest_existing_parent(selected)
    if parent.is_dir() and os.access(parent, os.W_OK):
        return make_doctor_check(section, "PASS", f"{label} appears writable", f"Path: {selected}")
    advice = classify_recovery_error(context="file", detail=f"{label} is not writable: {selected}")
    return make_doctor_check(section, "FAIL", advice.summary, advice.detail, advice)


# Reports each file monitoring will write or read, resolving the target-derived names once a username is known
def doctor_output_destination_checks(target_value=None):
    checks = []
    suffix = str(target_value) if target_value else ""
    if DISABLE_LOGGING:
        checks.append(make_doctor_check("Configuration", "PASS", "Output logging is disabled"))
    elif LF_LOGFILE:
        if suffix:
            checks.append(doctor_destination_check("Log destination", build_log_path(LF_LOGFILE, suffix)))
        else:
            checks.append(make_doctor_check("Configuration", "PASS", "Log destination will be finalized after a username is selected", f"Base path: {Path(os.path.expanduser(LF_LOGFILE))}"))
    if CSV_FILE:
        checks.append(doctor_destination_check("CSV destination", CSV_FILE))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "CSV logging is disabled"))
    if suffix:
        checks.append(doctor_destination_check("Status destination", f"lastfm_{suffix}_last_activity.json"))
        if friends_check_enabled():
            checks.append(doctor_destination_check("Profile state destination", f"lastfm_{suffix}_profile.json"))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "Status file will be finalized after a username is selected", "Base name: lastfm_<lastfm_username>_last_activity.json in the working directory"))
    if MONITOR_LIST_FILE:
        monitored = Path(os.path.expanduser(MONITOR_LIST_FILE))
        if monitored.is_file() and os.access(monitored, os.R_OK):
            checks.append(make_doctor_check("Configuration", "PASS", "Monitored tracks file is readable", f"Path: {monitored}"))
        else:
            advice = classify_recovery_error(context="file", detail=f"The file with Last.fm tracks cannot be opened: {monitored}")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice))
    return checks


# Returns all type and range errors in settings that control runtime timing or counts
def runtime_configuration_errors():
    errors = []
    positive_numbers = (("LASTFM_CHECK_INTERVAL", LASTFM_CHECK_INTERVAL), ("LASTFM_ACTIVE_CHECK_INTERVAL", LASTFM_ACTIVE_CHECK_INTERVAL), ("LASTFM_INACTIVITY_CHECK", LASTFM_INACTIVITY_CHECK), ("CHECK_INTERNET_TIMEOUT", CHECK_INTERNET_TIMEOUT))
    nonnegative_numbers = (("LIVENESS_CHECK_INTERVAL", LIVENESS_CHECK_INTERVAL), ("LASTFM_BREAK_CHECK_MULTIPLIER", LASTFM_BREAK_CHECK_MULTIPLIER), ("FRIENDS_CHECK_INTERVAL", FRIENDS_CHECK_INTERVAL), ("FRIENDS_RETRY_INTERVAL", FRIENDS_RETRY_INTERVAL))
    for name, value in positive_numbers:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            errors.append(f"{name} must be a number greater than zero, not {value!r}")
    for name, value in nonnegative_numbers:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            errors.append(f"{name} must be a number zero or greater, not {value!r}")
    if not isinstance(SMTP_PORT, int) or isinstance(SMTP_PORT, bool) or not 1 <= SMTP_PORT <= 65535:
        errors.append(f"SMTP_PORT must be an integer from 1 through 65535, not {SMTP_PORT!r}")
    return errors


# Reports the configuration and dotenv files in effect plus every file the tool will write
def doctor_check_configuration(config_path=None, env_path=None, target_value=None):
    checks = []
    if config_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Configuration file loaded", f"Path: {config_path}"))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No configuration file selected", "Using built-in defaults and command-line overrides"))
    if env_path and os.path.isfile(str(env_path)):
        checks.append(make_doctor_check("Configuration", "PASS", "Dotenv file loaded", f"Path: {env_path}"))
    elif env_path:
        advice = make_recovery_advice("config.missing", "The requested dotenv file was not found", recovery_fix_with_guide("Create the file or select an existing path with --env-file", SECRETS_GUIDE_URL), False, f"Path: {env_path}")
        checks.append(make_doctor_check("Configuration", "WARN", advice.summary, advice.detail, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No dotenv file selected", "Using environment variables and other configured sources"))
    checks.extend(doctor_secret_checks())

    if VERIFY_SSL:
        checks.append(make_doctor_check("Configuration", "PASS", "TLS certificate verification is on", "Every outbound request checks the server certificate"))
    else:
        advice = make_recovery_advice("config.insecure", "TLS certificate verification is off", recovery_fix_with_guide("Set VERIFY_SSL back to True unless this network intercepts TLS with its own certificate authority", TLS_GUIDE_URL), False)
        checks.append(make_doctor_check("Configuration", "WARN", advice.summary, "VERIFY_SSL is False, so an intercepted connection cannot be told apart from the real service", advice))

    numeric_errors = runtime_configuration_errors()
    if numeric_errors:
        numeric_detail = "Invalid numeric settings: " + "; ".join(numeric_errors)
        advice = make_recovery_advice("config.invalid", "One or more numeric settings are invalid", recovery_fix_with_guide("Correct the reported settings in the configuration file", CONFIG_FILE_GUIDE_URL), False, numeric_detail)
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, numeric_detail, advice))

    checks.extend(doctor_output_destination_checks(target_value))
    return checks


# Confirms the configured connectivity endpoint is reachable, reusing the settings monitoring will use
def doctor_check_connectivity():
    global LAST_CONNECTIVITY_ERROR
    LAST_CONNECTIVITY_ERROR = None
    if check_internet(quiet=True):
        return [make_doctor_check("Connectivity", "PASS", "The connectivity endpoint is reachable", f"Endpoint: {CHECK_INTERNET_URL}")]
    advice = classify_recovery_error(LAST_CONNECTIVITY_ERROR, context="connectivity", detail=f"Could not reach {CHECK_INTERNET_URL}")
    return [make_doctor_check("Connectivity", "FAIL", "The connectivity endpoint could not be reached", f"Endpoint: {CHECK_INTERNET_URL}", advice)]


# Validates the Last.fm credential pair with one real API call and keeps the client for the target check
def doctor_check_authentication(report):
    unset = [name for name in ("LASTFM_API_KEY", "LASTFM_API_SECRET") if not doctor_value_is_set(globals().get(name))]
    if unset:
        advice = classify_recovery_error(context="secret.missing", detail=f"{join_setting_names(unset, 'or')} is empty or still set to its placeholder")
        return [make_doctor_check("Authentication", "FAIL", "The Last.fm credentials are incomplete", advice.detail, advice)]
    try:
        report.network = pylast.LastFMNetwork(LASTFM_API_KEY, LASTFM_API_SECRET)
        report.network.get_top_artists(limit=1)
    except Exception as exc:
        report.network = None
        advice = classify_recovery_error(exc)
        return [make_doctor_check("Authentication", "FAIL", advice.summary, advice.detail, advice)]
    return [make_doctor_check("Authentication", "PASS", "Last.fm accepted the configured API key", "The shared secret is set. Neither value was displayed")]


# Reports which Spotify metadata backend a run will use, and only while a feature actually needs one
def doctor_check_spotify_metadata(report):
    if not (TRACK_SONGS or USE_TRACK_DURATION_FROM_SPOTIFY):
        return []
    checks = []
    if not spotify_oauth_app_configured():
        return [make_doctor_check("Spotify metadata", "PASS", "The anonymous Spotify web player supplies track metadata", "No OAuth app is configured, which needs no credentials")]
    try:
        spotify_get_access_token(SP_CLIENT_ID, SP_CLIENT_SECRET)
    except Exception as exc:
        advice = make_recovery_advice("auth.api_key_invalid", "Spotify did not accept the OAuth app credentials", recovery_fix_with_guide(f"Check SP_CLIENT_ID and SP_CLIENT_SECRET, or save a working pair with '{render_command(['--set-spotify-credentials'])}'", SPOTIFY_APP_GUIDE_URL), False, sanitize_error_text(exc))
        checks.append(make_doctor_check("Spotify metadata", "WARN", advice.summary, "Track metadata falls back to the anonymous Spotify web player", advice))
    else:
        checks.append(make_doctor_check("Spotify metadata", "PASS", "Spotify accepted the configured OAuth app credentials", "Track metadata uses the OAuth app first, then the anonymous web player"))
    if SP_TOKENS_FILE:
        checks.append(doctor_destination_check("Spotify token cache destination", SP_TOKENS_FILE, section="Spotify metadata"))
    else:
        checks.append(make_doctor_check("Spotify metadata", "PASS", "Spotify tokens are cached in memory only", "SP_TOKENS_FILE is empty, so nothing is written to disk"))
    return checks


# Confirms the monitored user exists and their listening history is readable, which is what the loop reads first
def doctor_check_target(report, target_value=None):
    if not target_value:
        advice = classify_recovery_error(context="target.missing")
        return [make_doctor_check("Target", "WARN", advice.summary, "Nothing will be monitored until one is given", advice)]
    if report.network is None:
        return [make_doctor_check("Target", "SKIP", "The monitored profile was not checked", "The Last.fm API key did not validate, so no lookup was attempted")]
    try:
        recent_tracks = lastfm_get_recent_tracks(target_value, report.network, 1)
    except Exception as exc:
        advice = classify_recovery_error(exc, context="runtime", detail=f"Cannot read the recent tracks of '{target_value}'")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice)]
    report.user = report.network.get_user(target_value)
    checks = [make_doctor_check("Target", "PASS", "The monitored profile exists", f"Last.fm user: {target_value}")]
    if recent_tracks:
        checks.append(make_doctor_check("Target", "PASS", "The recent listening history is readable", "Scrobbles are visible, so activity can be detected"))
    else:
        checks.append(make_doctor_check("Target", "PASS", "The recent listening history is readable but empty", "No scrobbles yet, so monitoring waits for the first track"))
    return checks


# Returns the doctor row for email alerts whose settings cannot deliver, worded the same way by every sibling monitor
def doctor_email_unusable_check(detail, fix):
    advice = make_recovery_advice("smtp.invalid", EMAIL_UNUSABLE_CHECK_LABEL, recovery_fix_with_guide(fix, SMTP_GUIDE_URL), False, detail)
    return make_doctor_check("Notifications", "WARN", EMAIL_UNUSABLE_CHECK_LABEL, detail, advice)


# Checks email alert settings then confirms the SMTP sign-in without sending anything
def doctor_check_email_notifications(report):
    enabled_categories = _startup_email_notification_categories()
    unset = mail_settings_missing()
    # The error alert ships on by default, so it alone cannot mean the channel is switched on
    deliberate_categories = [category for category in enabled_categories if category != "errors"]
    if not deliberate_categories and unset:
        return [make_doctor_check("Notifications", "PASS", "Email notifications are disabled", "No SMTP connection was attempted and no email was sent")]
    if unset:
        return [doctor_email_unusable_check(f"{join_setting_names(unset, 'or')} is empty or still set to its placeholder", f"Set {join_setting_names(unset, 'and')} or turn the email alerts off")]
    if not enabled_categories:
        advice = make_recovery_advice("smtp.invalid", "Email is configured but no alert types are selected", recovery_fix_with_guide("Turn on at least one email alert in the configuration file", SMTP_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be emailed", advice)]
    if not doctor_value_is_set(SMTP_USER) or not doctor_value_is_set(SMTP_PASSWORD):
        return [doctor_email_unusable_check("SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder", "Set SMTP_USER and SMTP_PASSWORD or turn the email alerts off")]
    smtp_object = None
    try:
        smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=DOCTOR_SMTP_TIMEOUT)
    except Exception as exc:
        advice = classify_recovery_error(exc, "email")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    finally:
        if smtp_object is not None:
            try:
                smtp_object.quit()
            except Exception as cleanup_error:
                debug_swallowed_exception("SMTP session cleanup", cleanup_error)
    report.email_ready = True
    return [make_doctor_check("Notifications", "PASS", SMTP_READY_CHECK_LABEL, f"Alerts: {', '.join(enabled_categories)}. No email was sent during this passive check")]


# Checks webhook alert settings without sending anything, asking whether the channel can fire before validating it
def doctor_check_webhook_notifications(report):
    selected_categories = _selected_webhook_notification_categories()
    deliberate_categories = [category for category in selected_categories if category != "errors"]
    if not WEBHOOK_ENABLED and not deliberate_categories:
        return [make_doctor_check("Notifications", "PASS", "Webhook alerts are disabled")]
    if not WEBHOOK_ENABLED:
        advice = make_recovery_advice("webhook.invalid", "Webhook alert types are selected but webhooks are switched off", recovery_fix_with_guide("Set WEBHOOK_ENABLED to True, or turn the alert types off", WEBHOOK_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be delivered", advice)]
    if not normalized_webhook_provider():
        advice = classify_recovery_error(context="webhook", detail="WEBHOOK_PROVIDER must be discord or ntfy")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not validate_webhook_url():
        advice = classify_recovery_error(context="webhook", detail="WEBHOOK_URL must contain a complete HTTPS link")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    for validation_error in (validate_webhook_customization(normalized_webhook_provider()), validate_webhook_headers(normalized_webhook_provider())):
        if validation_error is not None:
            advice = classify_recovery_error(context="webhook", detail=validation_error)
            return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not selected_categories:
        advice = make_recovery_advice("webhook.invalid", "Webhook alerts are on but no alert types are selected", recovery_fix_with_guide("Turn on at least one webhook alert in the configuration file, or set WEBHOOK_ENABLED to False", WEBHOOK_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be delivered", advice)]
    report.webhook_ready = True
    return [make_doctor_check("Notifications", "PASS", f"{WEBHOOK_READY_CHECK_LABEL} for {webhook_provider_display_name()}", f"Alerts: {', '.join(selected_categories)}. The private link was not displayed. No webhook was sent during this passive check")]


# Colours every link in a doctor detail line, since the report is printed before the line colouriser is installed
def _colorize_doctor_links(text):
    return _sub_outside_color(_URL_RE, lambda mo: colorize("link", mo.group(0)), text)


# Renders one doctor result marker in the colour its status calls for
def render_doctor_marker(status):
    return colorize(DOCTOR_MARK_STYLES.get(status, "info"), f"[{status}]")


# Prints one result the way the report renders it, so a row printed after the report matches the rows above it
def print_doctor_check(check):
    print(f"{render_doctor_marker(check.status)} {check.label}")
    if check.detail:
        print(f"  {check.detail}")


# Renders the heading and every non-empty section, with a fix line on the rows that are not a pass
def render_doctor_sections(report):
    # The install method is context rather than a check: it cannot fail, so it is stated once here
    # instead of occupying a result row that no marker describes
    lines = [colorize("header", "Doctor"), f"Detected install method: {colorize('username', install_method())}"]
    for section in DOCTOR_SECTIONS:
        section_checks = [check for check in report.checks if check.section == section]
        if not section_checks:
            continue
        lines.extend(("", colorize("section", section)))
        for check in section_checks:
            lines.append(f"{render_doctor_marker(check.status)} {check.label}")
            if check.detail:
                lines.append(f"  {_colorize_doctor_links(check.detail)}")
            if check.status != "PASS" and check.advice is not None:
                # The fix carries its own guide line, so each line is indented and styled on its own rather
                # than leaving one colour sequence open across the newline
                lines.extend(f"  {colorize('info', advice_line)}" for advice_line in f"To fix: {check.advice.fix}".splitlines())
    return sanitize_error_text("\n".join(lines))


# Renders the one sentence that says whether the setup is usable and where to read more
def render_doctor_summary(checks):
    failures = sum(check.status == "FAIL" for check in checks)
    warnings = sum(check.status == "WARN" for check in checks)
    if failures:
        summary_line = colorize("error", f"  {failures} check(s) failed, {warnings} warning(s). Fix the failures above before relying on the tool.")
    elif warnings:
        summary_line = colorize("warning", f"  All critical checks passed with {warnings} warning(s). Review the warnings above.")
    else:
        summary_line = colorize("boolean_true", "  All checks passed. You are good to go!")
    return "\n".join(("", colorize("header", "Summary"), summary_line, "", colorize("info", f"Guide: {DOCTOR_GUIDE_URL}")))


# Returns the real terminal underneath the installed stream, so progress can move the cursor safely
def _doctor_terminal_stream():
    return unwrap_terminal_stream(sys.stdout)


# Shows one transient doctor step, only on an interactive terminal
# The line stays uncoloured on purpose: it is erased by writing exactly len(line) spaces, and escape
# sequences would make that width wrong and leave a styled remnant behind
def _doctor_progress(label):
    global DOCTOR_PROGRESS_WIDTH
    terminal = _doctor_terminal_stream()
    if terminal.isatty():
        if DOCTOR_PROGRESS_WIDTH:
            terminal.write("\r" + (" " * DOCTOR_PROGRESS_WIDTH) + "\r")
        line = f"* Checking {ANSI_ESCAPE_RE.sub('', sanitize_terminal_text(label))} ..."
        DOCTOR_PROGRESS_WIDTH = len(line)
        terminal.write("\r" + line)
        terminal.flush()


# Clears the transient doctor progress line on an interactive terminal
def _doctor_progress_clear():
    global DOCTOR_PROGRESS_WIDTH
    terminal = _doctor_terminal_stream()
    if terminal.isatty() and DOCTOR_PROGRESS_WIDTH:
        terminal.write("\r" + (" " * DOCTOR_PROGRESS_WIDTH) + "\r")
        terminal.flush()
    DOCTOR_PROGRESS_WIDTH = 0


# States what doctor will and will not do, before the first slow check starts rather than after
def render_doctor_notice():
    print("Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval.\n")


# Prompts for explicit delivery consent and defaults safely to no
def _doctor_ask_yes_no(question, input_func=None):
    prompt = input if input_func is None else input_func
    while True:
        try:
            value = prompt(colorize("info", f"{question} [y/N]: ")).strip().casefold()
        except EOFError:
            print("\nDelivery test skipped.")
            return False
        except KeyboardInterrupt:
            # Ctrl+C ends the run here the way it does anywhere else, rather than only declining this one test
            signal_handler(signal.SIGINT, None)
            raise
        if not value or value in ("n", "no"):
            return False
        if value in ("y", "yes"):
            return True
        print("  Please answer 'y' or 'n'.")


# Offers one real delivery per ready channel, only after separate interactive approval
def _doctor_offer_notification_tests(report, input_func=None):
    # The terminal underneath any logger wrapper, since that wrapper answers no isatty of its own
    if not sys.stdin.isatty() or not _doctor_terminal_stream().isatty():
        return []
    if not report.email_ready and not report.webhook_ready:
        return []
    print("\n" + colorize("section", DOCTOR_DELIVERY_SECTION) + "\n")
    print("Doctor will not write files. Each approved test sends one real message.\n")
    checks = []
    if report.email_ready:
        if _doctor_ask_yes_no("Send one test email now? This will deliver a real message", input_func=input_func):
            delivered = send_email(DOCTOR_TEST_EMAIL_SUBJECT, DOCTOR_TEST_EMAIL_BODY, "", SMTP_SSL, smtp_timeout=DOCTOR_SMTP_TIMEOUT) == 0
            if delivered:
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS", "Doctor test email delivered", "One real test email was sent after confirmation")
            else:
                advice = make_recovery_advice("smtp.connection", "Doctor test email delivery failed", recovery_fix_with_guide("Review the SMTP error above and correct the email settings", SMTP_GUIDE_URL), True)
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "FAIL", advice.summary, "The approved test email could not be delivered", advice)
        else:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", "Test email was not sent", "You declined the real delivery test. Run doctor again and approve the email test when ready")
        checks.append(check)
        # Recorded on the report so the summary sentence and the exit code cannot disagree about the same run
        report.checks.append(check)
        print_doctor_check(check)
    if report.webhook_ready:
        provider = webhook_provider_display_name()
        if _doctor_ask_yes_no(f"Send one test webhook through {provider} now? This will publish a real notification", input_func=input_func):
            delivered = send_webhook(DOCTOR_TEST_WEBHOOK_TITLE, DOCTOR_TEST_WEBHOOK_BODY, "song", force=True) == 0
            if delivered:
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS", f"Doctor test webhook through {provider} delivered", "One real test webhook was sent after confirmation")
            else:
                advice = make_recovery_advice("webhook.connection", f"Doctor test webhook through {provider} delivery failed", recovery_fix_with_guide("Review the webhook error above and correct the destination settings", WEBHOOK_GUIDE_URL), True)
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "FAIL", advice.summary, "The approved test webhook could not be delivered", advice)
        else:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", f"Test webhook through {provider} was not sent", "You declined the real delivery test. Run doctor again and approve the webhook test when ready")
        checks.append(check)
        report.checks.append(check)
        print_doctor_check(check)
    return checks


# One startup summary setting, routed to the concise view, the verbose view or both. The log keeps the verbose view
StartupSummaryRow = namedtuple("StartupSummaryRow", ["label", "value", "concise", "full"])
StartupSummaryRow.__new__.__defaults__ = (False, True)


# Returns whether the full startup summary should be shown, which either diagnostic mode implies
def full_startup_summary_enabled():
    return bool(VERBOSE_MODE or DEBUG_MODE)


# Formats one summary row with an aligned value column, wrapping only the rollups that grow long
def format_startup_summary_row(row):
    prefix = f"* {(row.label + ':'):<30}"
    if row.label in ("Notifications (email)", "Notifications (webhook)"):
        return textwrap.fill(str(row.value), width=100, initial_indent=prefix, subsequent_indent=" " * len(prefix), break_long_words=False, break_on_hyphens=False) + "\n"
    return f"{prefix}{row.value}\n"


# Prints the summary, showing the concise rows unless the full view was asked for. The log file always keeps
# the complete set, so a bug report made from a log carries every effective setting whatever the terminal showed
def emit_startup_summary(rows, show_full=False, stream=None):
    destination = sys.stdout if stream is None else stream
    # A stream that does not split its output has no log file to hold the full view, so those writes go nowhere
    write_log = getattr(destination, "log_only", lambda line: None)
    write_terminal = getattr(destination, "terminal_only", None)
    if write_terminal is None:
        write_terminal = destination.write
    for row in rows:
        line = format_startup_summary_row(row)
        if row.full:
            write_log(line)
        if row.full if show_full else row.concise:
            write_terminal(line)
    write_log("\n")
    write_terminal("\n")
    destination.flush()


# Names the Spotify metadata backends this run would try, in the order it tries them
def spotify_metadata_backend_description():
    if not (TRACK_SONGS or USE_TRACK_DURATION_FROM_SPOTIFY):
        return "Disabled"
    return "OAuth app, then anonymous web player" if spotify_oauth_app_configured() else "Anonymous web player"


# Builds every startup summary row, deciding per row whether it belongs in the concise view, the full view and the log
def build_startup_summary(target=None, config_path=None, env_path=None, log_path=None):
    grouped_secrets = dict(secrets_by_source())
    logging_enabled = bool(log_path) and not DISABLE_LOGGING
    tracked_fields = (TRACK_FOLLOWINGS, TRACK_FOLLOWERS, TRACK_BIO, TRACK_DISPLAY_NAME)
    return [
        StartupSummaryRow("Target", str(target) if target else "None", concise=True),
        StartupSummaryRow("Polling intervals", f"[offline: {display_time(LASTFM_CHECK_INTERVAL)}] [active: {display_time(LASTFM_ACTIVE_CHECK_INTERVAL)}]", concise=True),
        StartupSummaryRow("Inactivity timer", display_time(LASTFM_INACTIVITY_CHECK), concise=True),
        StartupSummaryRow("Notifications (email)", _startup_notification_state(_startup_email_notification_categories()), concise=True),
        StartupSummaryRow("Notifications (webhook)", _startup_notification_state(_startup_webhook_notification_categories()), concise=True),
        StartupSummaryRow("Output", str(log_path) if logging_enabled else "Terminal only (logging disabled)", concise=True, full=False),
        StartupSummaryRow("Output logging", str(log_path) if logging_enabled else "Disabled"),
        StartupSummaryRow("Config", str(config_path) if config_path else "None", concise=True),
        StartupSummaryRow("Dotenv", str(env_path) if env_path else "None", concise=True),
        # Each tracked feature earns a concise row only while it is actually switched on
        StartupSummaryRow("Followings tracking", str(TRACK_FOLLOWINGS), concise=bool(TRACK_FOLLOWINGS)),
        StartupSummaryRow("Followers tracking", str(TRACK_FOLLOWERS), concise=bool(TRACK_FOLLOWERS)),
        StartupSummaryRow("Bio tracking", str(TRACK_BIO), concise=bool(TRACK_BIO)),
        StartupSummaryRow("Display name tracking", str(TRACK_DISPLAY_NAME), concise=bool(TRACK_DISPLAY_NAME)),
        StartupSummaryRow("Friends check interval", display_time(FRIENDS_CHECK_INTERVAL) if FRIENDS_CHECK_INTERVAL > 0 else "Disabled", concise=bool(any(tracked_fields) and FRIENDS_CHECK_INTERVAL > 0)),
        StartupSummaryRow("Metadata backend", spotify_metadata_backend_description(), concise=bool(TRACK_SONGS or USE_TRACK_DURATION_FROM_SPOTIFY)),
        # A cache row for a backend this run never reaches would read as a feature that is on
        StartupSummaryRow("Spotify token cache", SP_TOKENS_FILE or "Memory only", concise=bool(SP_TOKENS_FILE and (TRACK_SONGS or USE_TRACK_DURATION_FROM_SPOTIFY) and spotify_oauth_app_configured())),
        StartupSummaryRow("Spotify playback control", str(TRACK_SONGS), concise=bool(TRACK_SONGS)),
        StartupSummaryRow("Track duration from Spotify", str(USE_TRACK_DURATION_FROM_SPOTIFY), concise=bool(USE_TRACK_DURATION_FROM_SPOTIFY)),
        StartupSummaryRow("Duration marks", str(not DO_NOT_SHOW_DURATION_MARKS)),
        StartupSummaryRow("Play break multiplier", f"{LASTFM_BREAK_CHECK_MULTIPLIER} ({display_time(LASTFM_BREAK_CHECK_MULTIPLIER * LASTFM_ACTIVE_CHECK_INTERVAL)})"),
        StartupSummaryRow("Progress indicator", str(PROGRESS_INDICATOR), concise=bool(PROGRESS_INDICATOR)),
        StartupSummaryRow("Liveness output", display_time(LIVENESS_CHECK_INTERVAL) if LIVENESS_CHECK_INTERVAL else "Disabled", concise=bool(LIVENESS_CHECK_INTERVAL)),
        StartupSummaryRow("CSV output", CSV_FILE or "Disabled", concise=bool(CSV_FILE)),
        StartupSummaryRow("Monitored-track alerts", MONITOR_LIST_FILE or "Disabled", concise=bool(MONITOR_LIST_FILE)),
        StartupSummaryRow("Status file", resolve_status_file(target) if target else "None"),
        StartupSummaryRow("Terminal truncation", f"{TRUNCATE_CHARS} chars" if TRUNCATE_CHARS else "Disabled", concise=bool(TRUNCATE_CHARS)),
        StartupSummaryRow("Install method", install_method_display_name()),
        StartupSummaryRow("Secrets from dotenv", ", ".join(grouped_secrets.get("dotenv file", [])) or "None"),
        StartupSummaryRow("Secrets from environment", ", ".join(grouped_secrets.get("environment", [])) or "None"),
        StartupSummaryRow("Secrets from config file", ", ".join(grouped_secrets.get("config file", [])) or "None"),
        StartupSummaryRow("Secrets from command line", ", ".join(grouped_secrets.get("command line", [])) or "None"),
        StartupSummaryRow("TLS verification", "On" if VERIFY_SSL else "Off, server certificates are not checked", concise=not VERIFY_SSL),
        StartupSummaryRow("ASCII log separators", f"{ascii_log_separators_enabled()} (mode: {ASCII_LOG_SEPARATORS})"),
        StartupSummaryRow("Coloured output", f"{COLOR_ENABLED} (setting: {COLORED_OUTPUT})"),
        StartupSummaryRow("Verbose mode", str(VERBOSE_MODE), concise=bool(VERBOSE_MODE)),
        StartupSummaryRow("Debug mode", str(DEBUG_MODE), concise=bool(DEBUG_MODE)),
        # Points at the two modes for a reader who does not know they exist, so the full view drops it
        StartupSummaryRow("More details", "use --verbose or --debug", concise=True, full=False),
    ]


# Renders the --help examples: one heading per task, then a comment and the command it describes
def render_help_examples(groups, guide_url):
    blocks = []
    for title, entries in groups:
        block = [f"{title}:"]
        for comment, command in entries:
            if len(block) > 1:
                block.append("")
            block.extend(f"  # {line}" for line in comment.split("\n"))
            if command:
                block.append(f"  {command}")
        blocks.append("\n".join(block))
    return "Examples:\n\n" + "\n\n".join(blocks) + f"\n\nGuide: {guide_url}\n"


# Returns the --help epilog, listing the commands worth knowing rather than every command there is
def help_examples():
    prefix = render_command(include_paths=False)
    groups = (
        ("Getting started", (
            ("Guided setup, recommended for the first run", f"{prefix} --setup"),
            ("Or save the Last.fm API key and shared secret through hidden prompts", f"{prefix} --set-lastfm-credentials"),
            ("Check the setup before relying on it", f"{prefix} --doctor <lastfm_username>"),
            ("Start monitoring", f"{prefix} <lastfm_username>"),
        )),
        ("Notifications", (
            ("Email when the user starts and stops listening", f"{prefix} <lastfm_username> -a -i"),
            ("Send one test email", f"{prefix} --send-test-email"),
            ("Send one test webhook", f"{prefix} --send-test-webhook"),
        )),
        ("Listening extras", (
            ("Play every scrobble in your own Spotify client", f"{prefix} <lastfm_username> -g"),
            ("Alert on the tracks and albums listed in a file", f"{prefix} <lastfm_username> -s tracks.txt"),
            ("Write every scrobble to a CSV file", f"{prefix} <lastfm_username> -b scrobbles.csv"),
        )),
        ("Information and diagnostics", (
            ("List the most recent tracks and exit", f"{prefix} -l <lastfm_username>"),
            ("Trace what the tool is doing", f"{prefix} <lastfm_username> --debug"),
        )),
    )
    return render_help_examples(groups, QUICK_START_GUIDE_URL)


# Prints one labelled command on its own indented line, the shared shape across these tools
def _wizard_print_command(label, command, suffix=""):
    print(label)
    print(f"    {colorize('section', command)}{colorize('info', suffix) if suffix else ''}\n")


# Prints the command that starts monitoring with the files this run checked, so a report read on its own
# ends with the next action rather than leaving the reader to assemble the command
def print_doctor_next_steps(target_value=None, doctor_exit=0):
    print(colorize("header", "\nNext steps\n"))
    label = "After Doctor passes, start monitoring:" if doctor_exit else "Start monitoring:"
    _wizard_print_command(label, render_command([target_value] if target_value else ['<lastfm_username>']))
    # No trailing blank line: the command printer already left one and the report must not end on two
    print(f"Guide: {colorize('link', QUICK_START_GUIDE_URL)}")


# Prints the commands a newcomer needs next, instead of an argparse usage error
def print_welcome_screen(input_func=None, interactive=None):
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    print(f"For <lastfm_username>, use the {LASTFM_TARGET_FORMS}.\n")
    _wizard_print_command("Quickest start (already configured):", render_command(["<lastfm_username>"], include_paths=False))
    setup_suffix = "   (or just answer Y below)" if terminal_is_interactive else ""
    _wizard_print_command("Easiest start (guided setup wizard):", render_command(["--setup"], include_paths=False), setup_suffix)
    _wizard_print_command("Check setup before monitoring:", render_command(["--doctor", "<lastfm_username>"], include_paths=False))
    _wizard_print_command("Show recent tracks and exit:", render_command(["-l", "<lastfm_username>"], include_paths=False))
    print(f"Full options: {colorize('section', render_command(['--help'], include_paths=False))}")
    print(f"\nGuide:        {colorize('link', QUICK_START_GUIDE_URL)}\n")
    if terminal_is_interactive:
        try:
            start_setup = _wizard_ask_yes_no("Run the guided setup wizard now?", default=True, input_func=input_func)
        except (EOFError, KeyboardInterrupt):
            # This prompt sits outside the wizard, which handles its own interrupts
            print(colorize("warning", "Setup cancelled."))
            return 1
        if start_setup:
            print()
            return run_setup_wizard(input_func=input_func)
    # Without a terminal there was nothing to answer, so a bare invocation stays the usage error it was
    return 0 if terminal_is_interactive else 1


# Runs every preflight check, then the approved delivery tests, returning zero only when nothing failed
def run_doctor(target_value=None, config_path=None, env_path=None, input_func=None):
    report = DoctorReport()
    progress = _doctor_progress if _doctor_terminal_stream().isatty() else None
    render_doctor_notice()
    try:
        for label, collect in (
            ("environment", lambda: doctor_check_environment()),
            ("configuration", lambda: doctor_check_configuration(config_path, env_path, target_value)),
            ("connectivity", lambda: doctor_check_connectivity()),
            ("authentication", lambda: doctor_check_authentication(report)),
            ("Spotify metadata", lambda: doctor_check_spotify_metadata(report)),
            ("the monitored profile", lambda: doctor_check_target(report, target_value)),
            ("notifications", lambda: doctor_check_email_notifications(report) + doctor_check_webhook_notifications(report)),
        ):
            if progress is not None:
                progress(label)
            report.checks.extend(collect())
    finally:
        _doctor_progress_clear()
    print(render_doctor_sections(report))
    _doctor_offer_notification_tests(report, input_func=input_func)
    print(render_doctor_summary(report.checks))
    return 1 if any(check.status == "FAIL" for check in report.checks) else 0


# Reads a duration written the way people type one, returning whole seconds or None when it is not one
def parse_duration_input(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    if not isinstance(value, str):
        return None
    text = value.strip().casefold().replace(",", ".")
    if not text:
        return None
    units = {"s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
             "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
             "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
             "d": 86400, "day": 86400, "days": 86400}
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*([a-z]*)", text)
    # Reject anything the pattern did not fully consume, so "5x" or "abc" cannot read as a bare number
    if not matches or re.sub(r"(\d+(?:\.\d+)?)\s*([a-z]*)", "", text).strip():
        return None
    total = 0.0
    for amount, unit in matches:
        if unit and unit not in units:
            return None
        total += float(amount) * units.get(unit, 1)
    seconds = int(round(total))
    return seconds if seconds > 0 else None


# Reads a Last.fm username from a bare name or any profile URL, returning an empty string when it is neither
def normalize_lastfm_username(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if "/" in text or text.casefold().startswith(("http://", "https://", "www.", "last.fm")):
        match = re.search(r"last\.fm/(?:[a-z]{2}/)?user/([^/?#]+)", text, re.IGNORECASE)
        if not match:
            return ""
        text = unquote(match.group(1)).strip()
    # Last.fm allows a wide range of names, so only the characters a URL or a shell would break on are refused
    return text if re.fullmatch(r"[^\s/?#@]+", text) else ""


# Returns a stored value only when it is a real answer, so template placeholders are never offered as defaults
def _wizard_default(value):
    return str(value) if doctor_value_is_set(value if isinstance(value, str) else str(value or "")) else ""


# Prints the shared line telling the user how defaults and cancelling work
def _wizard_print_default_guidance():
    print("Press Enter to accept the shown default. Ctrl+C cancels.\n")


# Reads one setup line. Cancelling propagates to the one handler in run_setup_wizard, which reports that nothing was written
def _wizard_input(prompt_text, input_func=None):
    prompt = input if input_func is None else input_func
    try:
        return read_interactively(prompt, colorize("info", prompt_text))
    except (EOFError, KeyboardInterrupt):
        # The interrupted prompt owns the line break, so every handler prints its message alone
        print()
        raise


# Asks one free-text question, returning the shown default when the answer is empty
def _wizard_ask_text(question, default="", required=False, input_func=None):
    suffix = f" [{default}]" if default else ""
    while True:
        answer = _wizard_input(f"{question}{suffix}: ", input_func=input_func).strip()
        if not answer:
            answer = default
        if answer or not required:
            return answer
        print("  This value is required.")
        if not _wizard_offer_retry(question, input_func=input_func):
            return ""


# Asks one yes or no question with a visible default
def _wizard_ask_yes_no(question, default=True, input_func=None):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = _wizard_input(f"{question} {hint}: ", input_func=input_func).strip().casefold()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Offers the one way out after an entry the wizard cannot use, so declining keeps every answer already given
def _wizard_offer_retry(label, consequence="", input_func=None):
    if consequence:
        return not _wizard_ask_yes_no(f"Continue without the {label}? {consequence}", default=False, input_func=input_func)
    return _wizard_ask_yes_no(f"Try entering the {label} again?", default=True, input_func=input_func)


# Trims the parenthetical hint from a question, so the retry offer that repeats it stays one readable line
def _wizard_retry_label(question):
    return question.split(" (")[0].strip()


# Asks one numbered multiple-choice question and returns the chosen index
def _wizard_ask_choice(question, options, default_index=0, input_func=None):
    print()
    print(question)
    for index, (label, description) in enumerate(options, 1):
        marker = " (default)" if index - 1 == default_index else ""
        print(f"  {colorize('username', str(index))}. {label}{colorize('info', marker)}")
        if description:
            for line in description.splitlines():
                print(f"     {line}")
    while True:
        answer = _wizard_input(f"Choose [1-{len(options)}]: ", input_func=input_func).strip()
        if not answer:
            return default_index
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"  Enter a number between 1 and {len(options)}.")


# Asks until the user provides a positive whole number or accepts the default
def _wizard_ask_positive_int(question, default, maximum=None, input_func=None):
    while True:
        answer = _wizard_ask_text(question, default=str(default), required=True, input_func=input_func)
        # An empty answer means the retry offer was declined, so the default stands instead of asking again
        if not answer:
            return int(default)
        try:
            parsed = int(answer)
        except ValueError:
            parsed = 0
        if parsed > 0 and (maximum is None or parsed <= maximum):
            return parsed
        print(f"  Enter a whole number from 1 through {maximum}." if maximum is not None else "  Enter a positive whole number.")
        # A value the helper cannot use is a rejected entry, so it gets the same way out an empty one gets
        if not _wizard_offer_retry(_wizard_retry_label(question), input_func=input_func):
            print(f"  Keeping {default}.")
            return int(default)


# Renders a wizard duration as raw seconds plus a readable form, so the stored config value stays visible
def _wizard_format_duration(seconds):
    remaining = seconds
    parts = []
    for suffix, count in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        value, remaining = divmod(remaining, count)
        if value:
            parts.append(f"{value}{suffix}")
    raw = f"{seconds}s"
    readable = " ".join(parts) or raw
    return raw if readable == raw else f"{raw} - {readable}"


# Asks one duration, accepting the formats people actually type
def _wizard_ask_duration(question, default, input_func=None):
    prompt_text = f"{question} [{_wizard_format_duration(default)}]: "
    while True:
        answer = _wizard_input(prompt_text, input_func=input_func).strip()
        if not answer:
            return default
        seconds = parse_duration_input(answer)
        if seconds is not None:
            return seconds
        print("  Enter a positive duration such as 120, 2m, 1.5h, 1h 30m or 1d.")
        if not _wizard_offer_retry(_wizard_retry_label(question), input_func=input_func):
            print(f"  Keeping {_wizard_format_duration(default)}.")
            return default


# Asks one secret through a hidden prompt, so it never reaches the screen or the shell history
def _wizard_ask_secret(question, getpass_func=None):
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        with debug_output_suppressed():
            return str(read_secret_interactively(hidden_prompt, colorize("info", f"{question}: "))).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise


# Checks one setup destination without creating or modifying it, so an unwritable path is caught before any question
def _wizard_validate_destination(path, label):
    destination = Path(path).expanduser().resolve()
    if destination.exists() and destination.is_dir():
        raise ValueError(f"{label} must be a file path, not a directory")
    parent = nearest_existing_parent(destination)
    if not parent.is_dir():
        raise ValueError(f"{label} does not have a usable parent directory")
    if not os.access(str(parent), os.W_OK):
        raise ValueError(f"{label} is not writable through parent '{parent}'")
    return destination


# Resolves both setup destinations, refusing the disabled settings that leave nowhere to write
def _wizard_destinations(config_file=None, env_file=None):
    # The sentinel is a deliberate choice rather than a broken path, so it gets the fix that undoes it
    if config_file is not None and str(config_file).casefold() == "none":
        raise RecoveryError(make_recovery_advice("config.invalid", "--setup has nowhere to write the configuration", recovery_fix_with_guide(f"Replace '--config-file none' with a writable path, or drop the flag to write {DEFAULT_CONFIG_FILENAME} in the current directory", CONFIG_FILE_GUIDE_URL), False))
    if env_file is not None and str(env_file).casefold() == "none":
        raise RecoveryError(make_recovery_advice("secret.entry", "--setup has nowhere to write the secrets", recovery_fix_with_guide("Replace '--env-file none' with a writable path, or drop the flag to write .env in the current directory", SECRETS_GUIDE_URL), False))
    config_path = Path(config_file).expanduser() if config_file is not None else Path.cwd() / DEFAULT_CONFIG_FILENAME
    env_path = Path(env_file).expanduser() if env_file is not None else Path.cwd() / ".env"
    return _wizard_validate_destination(config_path, "Configuration destination"), _wizard_validate_destination(env_path, "Dotenv destination")


# Confirms replacing an existing config before any question is asked, so a long run cannot end in a surprise
def _wizard_choose_config_destination(config_path, input_func=None):
    selected = Path(config_path)
    while selected.exists() and not _wizard_ask_yes_no(f"Configuration file '{selected}' exists. A timestamped backup is kept. Rebuild it from your answers, starting from its current settings?", default=False, input_func=input_func):
        alternative = _wizard_ask_text("Another config destination or leave empty to cancel", input_func=input_func)
        if not alternative:
            return None
        try:
            selected = _wizard_validate_destination(alternative, "Configuration destination")
        except ValueError as exc:
            print(f"  {exc}.")
    return selected


# Reports whether a usable secret is already saved, without reading its value into the transcript
def _wizard_existing_secret(key, env_path):
    try:
        if _dotenv_contains_key(env_path, key):
            return True
    except PrivateSettingsError:
        return False
    return doctor_value_is_set(os.environ.get(key))


# Queues one secret for the save step, asking first when the dotenv file already assigns it
def _wizard_queue_secret(state, key, value, input_func=None):
    if not value:
        return False
    if _dotenv_contains_key(state.env_path, key) and not _wizard_ask_yes_no(f"The dotenv file already contains {key}. Replace that value?", default=False, input_func=input_func):
        print(f"  Existing {key} will be retained without being displayed or rewritten.")
        return False
    state.secret_updates[key] = value
    return True


# Holds every wizard answer until the user explicitly saves, so nothing is written during questioning
class WizardSetupState:
    # Starts from the values already in effect, which become both the defaults and the revert target
    def __init__(self, config_path, env_path, baseline_values):
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self.baseline_values = dict(baseline_values)
        self.config_values = dict(baseline_values)
        self.secret_updates = {}
        self.target = ""
        self.persist_target = True


# The mail server settings the wizard collects, and how long its sign-in check waits for the server
WIZARD_SMTP_CONFIG_KEYS = ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL")
WIZARD_SMTP_TIMEOUT = 5

# The email and webhook alert settings the wizard offers, in the order the questions are asked
WIZARD_EMAIL_NOTIFICATION_KEYS = ("ACTIVE_NOTIFICATION", "INACTIVE_NOTIFICATION", "TRACK_NOTIFICATION", "SONG_NOTIFICATION", "SONG_ON_LOOP_NOTIFICATION", "OFFLINE_ENTRIES_NOTIFICATION", "FOLLOWERS_NOTIFICATION", "FOLLOWINGS_NOTIFICATION", "PROFILE_NOTIFICATION", "ERROR_NOTIFICATION")
WIZARD_WEBHOOK_NOTIFICATION_KEYS = ("WEBHOOK_ACTIVE_NOTIFICATION", "WEBHOOK_INACTIVE_NOTIFICATION", "WEBHOOK_TRACK_NOTIFICATION", "WEBHOOK_SONG_NOTIFICATION", "WEBHOOK_SONG_ON_LOOP_NOTIFICATION", "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION", "WEBHOOK_FOLLOWERS_NOTIFICATION", "WEBHOOK_FOLLOWINGS_NOTIFICATION", "WEBHOOK_PROFILE_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION")

# The alerts the recommended preset switches on, named rather than counted: a message per song change is
# too much for a default, and the alerts that need a monitored list or profile tracking are asked for there
WIZARD_RECOMMENDED_EMAIL_KEYS = ("ACTIVE_NOTIFICATION", "INACTIVE_NOTIFICATION", "OFFLINE_ENTRIES_NOTIFICATION", "ERROR_NOTIFICATION")
WIZARD_RECOMMENDED_WEBHOOK_KEYS = ("WEBHOOK_ACTIVE_NOTIFICATION", "WEBHOOK_INACTIVE_NOTIFICATION", "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION")

# What each alert is called in the questions and in the setup summary
WIZARD_ALERT_LABELS = {
    "ACTIVE_NOTIFICATION": "starts listening",
    "INACTIVE_NOTIFICATION": "stops listening",
    "TRACK_NOTIFICATION": "monitored track or album",
    "SONG_NOTIFICATION": "every song change",
    "SONG_ON_LOOP_NOTIFICATION": "song on loop",
    "OFFLINE_ENTRIES_NOTIFICATION": "scrobbles added while offline",
    "FOLLOWERS_NOTIFICATION": "follower changes",
    "FOLLOWINGS_NOTIFICATION": "following changes",
    "PROFILE_NOTIFICATION": "profile changes",
    "ERROR_NOTIFICATION": "errors",
}

# The setting each alert needs before it can ever fire, so the wizard never offers an alert this setup cannot produce
WIZARD_ALERT_REQUIREMENTS = {
    "TRACK_NOTIFICATION": ("MONITOR_LIST_FILE",),
    "FOLLOWERS_NOTIFICATION": ("TRACK_FOLLOWERS",),
    "FOLLOWINGS_NOTIFICATION": ("TRACK_FOLLOWINGS",),
    "PROFILE_NOTIFICATION": ("TRACK_BIO", "TRACK_DISPLAY_NAME"),
}

# The Spotify settings the wizard collects, and the tracking settings the friend and profile alerts depend on
WIZARD_SPOTIFY_CONFIG_KEYS = ("USE_TRACK_DURATION_FROM_SPOTIFY", "TRACK_SONGS", "SP_TOKENS_FILE")
WIZARD_TRACKING_CONFIG_KEYS = ("TRACK_FOLLOWERS", "TRACK_FOLLOWINGS", "TRACK_BIO", "TRACK_DISPLAY_NAME", "FRIENDS_CHECK_INTERVAL")


# Each editable section: internal name, menu label and description, then the keys reverted when it is re-entered
WIZARD_SECTIONS = (
    ("Target", "Target", "Change the Last.fm user that is monitored.", ("LASTFM_USERNAME",), ()),
    ("Polling", "Polling intervals", "Change how often Last.fm is checked.", ("LASTFM_CHECK_INTERVAL", "LASTFM_ACTIVE_CHECK_INTERVAL", "LASTFM_INACTIVITY_CHECK"), ()),
    ("Authentication", "Authentication", "Enter the Last.fm API key and shared secret again.", (), ("LASTFM_API_KEY", "LASTFM_API_SECRET")),
    ("Spotify", "Spotify track details", "Change track duration, playback and Spotify app credentials.", WIZARD_SPOTIFY_CONFIG_KEYS, ("SP_CLIENT_ID", "SP_CLIENT_SECRET")),
    ("Tracking", "Profile tracking", "Change follower, following and profile tracking.", WIZARD_TRACKING_CONFIG_KEYS, ()),
    ("Output", "Output files", "Change the log, CSV and monitored track list destinations.", ("DISABLE_LOGGING", "CSV_FILE", "MONITOR_LIST_FILE"), ()),
    ("Email", "Email notifications", "Change SMTP details and email events.", WIZARD_SMTP_CONFIG_KEYS + WIZARD_EMAIL_NOTIFICATION_KEYS, ("SMTP_PASSWORD",)),
    ("Webhook", "Webhook alerts", "Change Discord or ntfy details and events.", ("WEBHOOK_ENABLED", "WEBHOOK_PROVIDER") + WIZARD_WEBHOOK_NOTIFICATION_KEYS, ("WEBHOOK_URL", "NTFY_ACCESS_TOKEN")),
    ("Destinations", "File destinations", "Change the configuration or dotenv output path.", (), ()),
)


# Restores one section to the values setup started with and drops any secret it had queued
def _wizard_reset_section(state, config_keys, secret_keys):
    for key in config_keys:
        if key in state.baseline_values:
            state.config_values[key] = state.baseline_values[key]
        else:
            state.config_values.pop(key, None)
    for key in secret_keys:
        state.secret_updates.pop(key, None)


# Returns one declined section to the built-in template values, so nothing the user turned down is written
def _wizard_clear_section(state, config_keys, secret_keys=()):
    defaults = _config_template_defaults()
    for key in config_keys:
        if key in defaults:
            state.config_values[key] = defaults[key]
        else:
            state.config_values.pop(key, None)
    for key in secret_keys:
        state.secret_updates.pop(key, None)


# Mirrors the settled target into the config values, so an unpersisted target is left out of the file
def _wizard_apply_target(state):
    state.config_values["LASTFM_USERNAME"] = state.target if state.persist_target and state.target else ""


# Asks for the monitored user, accepting a username or any Last.fm profile URL
def _wizard_collect_target_section(state, initial_target=None, input_func=None):
    question = "Last.fm username or profile URL to monitor"
    while True:
        answer = _wizard_ask_text(question, default=str(initial_target or state.target or ""), required=True, input_func=input_func)
        if not answer:
            # The question already offered another attempt and it was declined, so the section ends instead of asking again
            break
        username = normalize_lastfm_username(answer)
        if username:
            state.target = username
            break
        print(f"  '{answer}' is not a Last.fm username or profile URL.")
        if not _wizard_offer_retry(question, input_func=input_func):
            break
    if not state.target:
        print("  No target selected. Nothing can be monitored until one is set. Run --setup again or pass the target on the command line.")
        _wizard_apply_target(state)
        return
    state.persist_target = _wizard_ask_yes_no("Persist this target in the generated config?", default=state.persist_target, input_func=input_func)
    _wizard_apply_target(state)


# Asks how often the tool checks and when a user counts as inactive
def _wizard_collect_polling_section(state, input_func=None):
    state.config_values["LASTFM_CHECK_INTERVAL"] = _wizard_ask_duration("Polling interval while the user is not listening (seconds or use s/m/h/d)", int(state.config_values.get("LASTFM_CHECK_INTERVAL") or LASTFM_CHECK_INTERVAL), input_func=input_func)
    state.config_values["LASTFM_ACTIVE_CHECK_INTERVAL"] = _wizard_ask_duration("Polling interval while the user is listening (seconds or use s/m/h/d)", int(state.config_values.get("LASTFM_ACTIVE_CHECK_INTERVAL") or LASTFM_ACTIVE_CHECK_INTERVAL), input_func=input_func)
    state.config_values["LASTFM_INACTIVITY_CHECK"] = _wizard_ask_duration("Silence after the last scrobble before the user counts as inactive", int(state.config_values.get("LASTFM_INACTIVITY_CHECK") or LASTFM_INACTIVITY_CHECK), input_func=input_func)


# Signs in to Last.fm with the entered pair, so a rejected credential is caught during setup
def _wizard_verify_lastfm_credentials(api_key, api_secret):
    try:
        pylast.LastFMNetwork(api_key, api_secret).get_top_artists(limit=1)
    except Exception as exc:
        return classify_recovery_error(exc)
    return None


# Asks for the Last.fm API key and shared secret as one credential and checks the pair against Last.fm
def _wizard_collect_auth_section(state, input_func=None, getpass_func=None, validator=None):
    print(f"Create or view your Last.fm API key and shared secret: {LASTFM_API_REGISTRATION_URL}")
    print(f"Credentials of an application you already registered: {LASTFM_API_ACCOUNTS_URL}")
    configured = all(doctor_value_is_set(state.config_values.get(name)) or _wizard_existing_secret(name, state.env_path) for name in ("LASTFM_API_KEY", "LASTFM_API_SECRET"))
    # The key and the secret are one credential, so the replace question covers the pair rather than each value
    if configured and not _wizard_ask_yes_no("Replace the Last.fm API credentials already configured?", default=False, input_func=input_func):
        return
    verify = _wizard_verify_lastfm_credentials if validator is None else validator
    while True:
        api_key = _wizard_ask_secret("Last.fm API key", getpass_func=getpass_func)
        api_secret = _wizard_ask_secret("Last.fm shared secret", getpass_func=getpass_func)
        if not api_key or not api_secret:
            # Monitoring cannot run without the pair, so leaving it unset has to be a decision rather than a fallthrough
            if not _wizard_offer_retry("Last.fm API credentials", "Nothing can be monitored until both values are set", input_func=input_func):
                return
            continue
        # Last.fm is contacted here, which takes long enough to look like a hang without a notice
        print("  Checking the credentials with Last.fm ...")
        advice = verify(api_key, api_secret)
        if advice is None:
            state.secret_updates["LASTFM_API_KEY"] = api_key
            state.secret_updates["LASTFM_API_SECRET"] = api_secret
            print("  Last.fm accepted the credentials.")
            return
        print(f"  {advice.summary}: {advice.detail}" if advice.detail else f"  {advice.summary}")
        if advice.retryable:
            # Being offline is the usual reason a correct pair fails here, so the values are kept rather than discarded
            state.secret_updates["LASTFM_API_KEY"] = api_key
            state.secret_updates["LASTFM_API_SECRET"] = api_secret
            print("  The credentials were saved without being checked. Run --doctor to check them again.")
            return
        # A pair Last.fm keeps rejecting cannot be corrected from inside the loop, so the wizard must be leavable here too
        if not _wizard_offer_retry("Last.fm API credentials", input_func=input_func):
            return


# Switches the Spotify metadata features off together, so a declined section leaves no half-configured app behind
def _wizard_disable_spotify(state):
    _wizard_clear_section(state, WIZARD_SPOTIFY_CONFIG_KEYS, ("SP_CLIENT_ID", "SP_CLIENT_SECRET"))
    state.config_values["USE_TRACK_DURATION_FROM_SPOTIFY"] = False
    state.config_values["TRACK_SONGS"] = False


# Asks whether Spotify supplies track details and collects the optional app credentials behind that one gate
def _wizard_collect_spotify_section(state, input_func=None, getpass_func=None):
    enabled = bool(state.config_values.get("USE_TRACK_DURATION_FROM_SPOTIFY") or state.config_values.get("TRACK_SONGS"))
    if not _wizard_ask_yes_no("Use Spotify for track details?", default=enabled, input_func=input_func):
        _wizard_disable_spotify(state)
        return
    # A fresh opt-in has no earlier answer to keep, and the duration is the main reason to reach for Spotify at all
    duration_default = bool(state.config_values.get("USE_TRACK_DURATION_FROM_SPOTIFY")) if enabled else True
    state.config_values["USE_TRACK_DURATION_FROM_SPOTIFY"] = _wizard_ask_yes_no("Take track duration from Spotify? Last.fm often lacks it or reports it wrong", default=duration_default, input_func=input_func)
    state.config_values["TRACK_SONGS"] = _wizard_ask_yes_no("Play each scrobbled track in your own Spotify client?", default=bool(state.config_values.get("TRACK_SONGS")), input_func=input_func)
    if not (state.config_values["USE_TRACK_DURATION_FROM_SPOTIFY"] or state.config_values["TRACK_SONGS"]):
        _wizard_disable_spotify(state)
        return
    print(f"  Without app credentials the anonymous Spotify web player supplies the metadata. Create an app at {SPOTIFY_DASHBOARD_URL}")
    configured = all(doctor_value_is_set(state.config_values.get(name)) or _wizard_existing_secret(name, state.env_path) for name in ("SP_CLIENT_ID", "SP_CLIENT_SECRET"))
    question = "Replace the Spotify app credentials already configured?" if configured else "Add Spotify app credentials? They are optional and are tried before the anonymous backend"
    if not _wizard_ask_yes_no(question, default=False, input_func=input_func):
        if not configured:
            print("  Keeping the anonymous Spotify web player, which needs no credentials.")
        return
    while True:
        client_id = _wizard_ask_secret("Spotify client ID", getpass_func=getpass_func)
        client_secret = _wizard_ask_secret("Spotify client secret", getpass_func=getpass_func)
        if not client_id or not client_secret:
            if not _wizard_offer_retry("Spotify app credentials", "The anonymous Spotify web player is used instead", input_func=input_func):
                return
            continue
        print("  Checking the credentials with Spotify ...")
        try:
            spotify_get_access_token(client_id, client_secret)
        except Exception as exc:
            print(f"  Spotify did not accept the credentials: {sanitize_error_text(exc)}")
            if not _wizard_offer_retry("Spotify app credentials", "The anonymous Spotify web player is used instead", input_func=input_func):
                return
            continue
        state.secret_updates["SP_CLIENT_ID"] = client_id
        state.secret_updates["SP_CLIENT_SECRET"] = client_secret
        print("  Spotify accepted the credentials.")
        state.config_values["SP_TOKENS_FILE"] = _wizard_normalize_json_path(_wizard_ask_text("Token cache file (blank keeps the tokens in memory only)", default=str(state.config_values.get("SP_TOKENS_FILE") or ""), input_func=input_func))
        return


# Asks which profile changes are watched, and how often, since one timer covers all of them
def _wizard_collect_tracking_section(state, input_func=None):
    questions = (
        ("TRACK_FOLLOWERS", "Watch for follower changes?"),
        ("TRACK_FOLLOWINGS", "Watch for following changes?"),
        ("TRACK_DISPLAY_NAME", "Watch for display name changes?"),
        ("TRACK_BIO", "Watch for About Me changes?"),
    )
    for key, question in questions:
        state.config_values[key] = _wizard_ask_yes_no(question, default=bool(state.config_values.get(key)), input_func=input_func)
    if any(state.config_values.get(key) for key, _question in questions):
        state.config_values["FRIENDS_CHECK_INTERVAL"] = _wizard_ask_duration("How often to check for those changes", int(state.config_values.get("FRIENDS_CHECK_INTERVAL") or FRIENDS_CHECK_INTERVAL), input_func=input_func)


# Adds the .csv extension when the answer carries none, so a bare name still names a CSV file
def _wizard_normalize_csv_path(answer):
    text = str(answer).strip()
    if not text or Path(text).suffix:
        return text
    return text + ".csv"


# Adds the .json extension when the answer carries none, so a bare name still names a JSON file
def _wizard_normalize_json_path(answer):
    text = str(answer).strip()
    if not text or Path(text).suffix:
        return text
    return text + ".json"


# Collects the files monitoring writes and the optional list of tracks to alert on
def _wizard_collect_output_section(state, input_func=None):
    state.config_values["DISABLE_LOGGING"] = not _wizard_ask_yes_no("Write the normal per-target log file?", default=not bool(state.config_values.get("DISABLE_LOGGING")), input_func=input_func)
    state.config_values["CSV_FILE"] = _wizard_normalize_csv_path(_wizard_ask_text("Optional CSV output path (blank disables it)", default=str(state.config_values.get("CSV_FILE") or ""), input_func=input_func))
    while True:
        answer = _wizard_ask_text("Optional file listing tracks and albums to alert on (blank disables it)", default=str(state.config_values.get("MONITOR_LIST_FILE") or ""), input_func=input_func).strip()
        if not answer or Path(answer).expanduser().is_file():
            state.config_values["MONITOR_LIST_FILE"] = answer
            return
        print(f"  '{answer}' does not exist. The alerts it drives would never fire.")
        if not _wizard_offer_retry("track list file", "Monitored track alerts stay off", input_func=input_func):
            state.config_values["MONITOR_LIST_FILE"] = ""
            return


# Returns the alerts this setup can actually produce, so a question is never asked about one that cannot fire
def _wizard_available_alert_keys(state, keys):
    available = []
    for key in keys:
        requirements = WIZARD_ALERT_REQUIREMENTS.get(key.replace("WEBHOOK_", "", 1) if key.startswith("WEBHOOK_") else key, ())
        if requirements and not any(state.config_values.get(name) for name in requirements):
            continue
        available.append(key)
    return tuple(available)


# Switches every email alert off together, so an abandoned answer cannot leave half a mail server configured
def _wizard_disable_email(state):
    _wizard_clear_section(state, WIZARD_SMTP_CONFIG_KEYS, ("SMTP_PASSWORD",))
    # Only the alerts the wizard offers are cleared, so alerts enabled by hand survive a declined email section
    for key in WIZARD_EMAIL_NOTIFICATION_KEYS:
        state.config_values[key] = False


# Signs in to the collected mail server without sending anything, so a refused login is caught during setup
def _wizard_verify_smtp(values, password):
    names = ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SMTP_PASSWORD", "SENDER_EMAIL", "RECEIVER_EMAIL")
    previous = {name: globals()[name] for name in names}
    smtp_object = None
    try:
        globals().update(values)
        # A blank answer keeps the password already stored, which is the one the sign-in must then prove
        globals()["SMTP_PASSWORD"] = password or previous["SMTP_PASSWORD"]
        smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=WIZARD_SMTP_TIMEOUT)
        return None
    except Exception as exc:
        return classify_recovery_error(exc, "email")
    finally:
        if smtp_object is not None:
            try:
                smtp_object.quit()
            except Exception as cleanup_error:
                debug_swallowed_exception("SMTP session cleanup", cleanup_error)
        globals().update(previous)


# Reports the outcome of the sign-in check: True to continue, False to ask again, None to switch email off
def _wizard_smtp_sign_in_accepted(values, password, input_func=None):
    print("  Checking the sign-in with the mail server ...")
    advice = _wizard_verify_smtp(values, password)
    if advice is None:
        print("  The mail server accepted the sign-in. No email was sent.")
        return True
    print(f"  {advice.summary}: {advice.detail}" if advice.detail else f"  {advice.summary}")
    print(f"  To fix: {advice.fix}")
    if _wizard_offer_retry("mail server settings", input_func=input_func):
        return False
    if advice.retryable:
        # Being offline is the usual reason a correct setup fails here, so the answers are kept rather than discarded
        print("  The settings were kept without being checked. Run --doctor to check the sign-in again.")
        return True
    print("  Email notifications stay off until the mail server accepts the settings.")
    return None


# Reports whether one required mail server answer was abandoned, switching the channel off when it was
def _wizard_email_answer_missing(state, key):
    if state.config_values.get(key):
        return False
    print("  Email notifications stay off until every mail server setting is answered.")
    _wizard_disable_email(state)
    return True


# Reports whether the saved settings already send email, so a rerun proposes keeping the channel it has
def _wizard_email_enabled(config_values):
    # The error alert ships switched on, so on its own it counts only once a mail server has been named
    for key in WIZARD_EMAIL_NOTIFICATION_KEYS:
        if key != "ERROR_NOTIFICATION" and bool(config_values.get(key)):
            return True
    return bool(config_values.get("ERROR_NOTIFICATION")) and doctor_value_is_set(config_values.get("SMTP_HOST"))


# Asks which alerts one channel sends, from the presets plus a custom branch over the alerts this setup can produce
def _wizard_collect_alert_preset(state, question, keys, recommended, prefix="", input_func=None):
    available = _wizard_available_alert_keys(state, keys)
    recommended_available = tuple(key for key in recommended if key in available)
    preset = _wizard_ask_choice(question, [
        ("Activity and errors, recommended", "Alerts when listening starts or stops, when offline scrobbles arrive and when monitoring has a problem."),
        ("Every supported alert", "Includes an alert on every single song change."),
        ("Custom", "Choose each alert separately."),
    ], input_func=input_func)
    if preset == 0:
        selected = {key: key in recommended_available for key in keys}
    elif preset == 1:
        selected = {key: key in available for key in keys}
    else:
        print()
        selected = {}
        for key in keys:
            if key not in available:
                selected[key] = False
                continue
            label = WIZARD_ALERT_LABELS[key.replace("WEBHOOK_", "", 1) if key.startswith("WEBHOOK_") else key]
            selected[key] = _wizard_ask_yes_no(f"{prefix}{label}?", default=False, input_func=input_func)
    state.config_values.update(selected)


# Asks whether to send email alerts and collects only the settings that choice needs
def _wizard_collect_email_section(state, input_func=None, getpass_func=None):
    if not _wizard_ask_yes_no("Configure email notifications?", default=_wizard_email_enabled(state.config_values), input_func=input_func):
        _wizard_disable_email(state)
        return
    while True:
        state.config_values["SMTP_HOST"] = _wizard_ask_text("SMTP host", default=_wizard_default(state.config_values.get("SMTP_HOST")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SMTP_HOST"):
            return
        state.config_values["SMTP_PORT"] = _wizard_ask_positive_int("SMTP port", int(state.config_values.get("SMTP_PORT") or 587), maximum=65535, input_func=input_func)
        state.config_values["SMTP_SSL"] = _wizard_ask_yes_no("Enable TLS/SSL for SMTP?", default=bool(state.config_values.get("SMTP_SSL")), input_func=input_func)
        state.config_values["SMTP_USER"] = _wizard_ask_text("SMTP username", default=_wizard_default(state.config_values.get("SMTP_USER")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SMTP_USER"):
            return
        state.config_values["SENDER_EMAIL"] = _wizard_ask_text("Sender email", default=_wizard_default(state.config_values.get("SENDER_EMAIL")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SENDER_EMAIL"):
            return
        state.config_values["RECEIVER_EMAIL"] = _wizard_ask_text("Receiver email", default=_wizard_default(state.config_values.get("RECEIVER_EMAIL")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "RECEIVER_EMAIL"):
            return
        password = _wizard_ask_secret("SMTP password", getpass_func=getpass_func)
        if password:
            _wizard_queue_secret(state, "SMTP_PASSWORD", password, input_func=input_func)
        outcome = _wizard_smtp_sign_in_accepted({name: state.config_values[name] for name in WIZARD_SMTP_CONFIG_KEYS}, password, input_func=input_func)
        if outcome is None:
            _wizard_disable_email(state)
            return
        if outcome:
            break
    _wizard_collect_alert_preset(state, "Which email notifications should be enabled?", WIZARD_EMAIL_NOTIFICATION_KEYS, WIZARD_RECOMMENDED_EMAIL_KEYS, prefix="Email on ", input_func=input_func)


# Switches the channel and every alert it owns off together, so a half-configured webhook cannot be written
def _wizard_disable_webhook(state):
    _wizard_clear_section(state, ("WEBHOOK_PROVIDER",), ("WEBHOOK_URL", "NTFY_ACCESS_TOKEN"))
    state.config_values["WEBHOOK_ENABLED"] = False
    state.config_values.update({name: False for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS})


# Asks whether to send webhook alerts and collects the provider, the hidden URL and the alert choices
def _wizard_collect_webhook_section(state, input_func=None, getpass_func=None):
    if not _wizard_ask_yes_no("Set up webhook alerts (Discord, ntfy etc.)?", default=bool(state.config_values.get("WEBHOOK_ENABLED")), input_func=input_func):
        _wizard_disable_webhook(state)
        return
    provider_choice = _wizard_ask_choice("Which webhook service should receive alerts?", [
        ("Discord", "Sends a Discord embed to one channel webhook."),
        ("ntfy", "Sends a native notification to one ntfy topic URL."),
    ], default_index=0 if normalized_webhook_provider(state.config_values.get("WEBHOOK_PROVIDER")) != "ntfy" else 1, input_func=input_func)
    provider = "discord" if provider_choice == 0 else "ntfy"
    state.config_values["WEBHOOK_PROVIDER"] = provider
    if provider == "discord":
        print("  In Discord: Edit Channel > Integrations > Webhooks > New Webhook > Copy Webhook URL.")
    else:
        print("  In ntfy: choose a hard-to-guess topic. Paste its complete topic URL, or just the topic name when it is hosted on ntfy.sh.")
    replace_webhook = True
    if _wizard_existing_secret("WEBHOOK_URL", state.env_path):
        choice = _wizard_ask_choice("Which webhook URL should be used?", [
            ("Keep the saved URL", "Keeps the private value without displaying or changing it."),
            ("Paste a new URL", "Uses a hidden prompt then saves the new private value in the dotenv file."),
        ], input_func=input_func)
        replace_webhook = choice == 1
    if replace_webhook:
        while True:
            answer = _wizard_ask_secret("Paste the Discord webhook URL" if provider == "discord" else "Paste the ntfy topic URL or ntfy.sh topic name", getpass_func=getpass_func)
            webhook_url = normalize_ntfy_topic_url(answer) if provider == "ntfy" else answer.strip()
            if validate_webhook_url(webhook_url):
                state.secret_updates["WEBHOOK_URL"] = webhook_url
                break
            # Nothing can be delivered without a destination, so giving up has to stay reachable from the prompt.
            # The branch is chosen by what was typed rather than by the normalized value, since a rejected ntfy
            # topic normalizes to an empty string and would otherwise be reported as nothing entered
            if not answer.strip():
                if not _wizard_offer_retry("webhook URL", "Webhook alerts stay off until one is set", input_func=input_func):
                    _wizard_disable_webhook(state)
                    return
                continue
            if provider == "ntfy":
                print("  Enter a complete HTTPS ntfy topic URL or a topic name containing up to 64 letters, numbers, dashes or underscores.")
            else:
                print("  That does not look like a complete HTTPS webhook URL. Copy it from the webhook service and try again.")
            if not _wizard_offer_retry("webhook URL", input_func=input_func):
                _wizard_disable_webhook(state)
                return
    if provider == "ntfy":
        _wizard_collect_ntfy_access_token(state, input_func=input_func, getpass_func=getpass_func)
    state.config_values["WEBHOOK_ENABLED"] = True
    _wizard_collect_alert_preset(state, "Which webhook alerts should be sent?", WIZARD_WEBHOOK_NOTIFICATION_KEYS, WIZARD_RECOMMENDED_WEBHOOK_KEYS, prefix="Send a webhook alert on ", input_func=input_func)


# Collects an optional ntfy access token without displaying it or contacting the service
def _wizard_collect_ntfy_access_token(state, input_func=None, getpass_func=None):
    if _wizard_existing_secret("NTFY_ACCESS_TOKEN", state.env_path):
        choice = _wizard_ask_choice("Which ntfy authentication should be used?", [
            ("Keep the saved access token", "Keeps the private value without displaying or changing it."),
            ("Paste a new access token", "Uses a hidden prompt then saves the replacement in the dotenv file."),
            ("Do not use an access token", "Disables the saved token. Authentication in the topic URL still works."),
        ], input_func=input_func)
        if choice == 0:
            return
        if choice == 2:
            state.secret_updates["NTFY_ACCESS_TOKEN"] = ""
            print("  The saved ntfy access token will be disabled without being displayed.")
            return
    elif not _wizard_ask_yes_no("Authenticate this ntfy topic with a separate access token?", default=False, input_func=input_func):
        print("  No separate access token selected. Authentication already present in the topic URL still works.")
        return
    while True:
        token = _wizard_ask_secret("Paste the ntfy access token only", getpass_func=getpass_func)
        if not token or ("\r" not in token and "\n" not in token and not token.casefold().startswith(("bearer ", "basic "))):
            if token:
                state.secret_updates["NTFY_ACCESS_TOKEN"] = token
            return
        print("  Paste only the access token without a Bearer or Basic prefix.")
        if not _wizard_offer_retry("ntfy access token", input_func=input_func):
            return


# Changes where setup writes, re-asking the sections that hold secrets when the dotenv destination moves
def _wizard_collect_destination_section(state, input_func=None, getpass_func=None):
    current_config = Path(state.config_path).expanduser().resolve()
    current_env = Path(state.env_path).expanduser().resolve()
    while True:
        config_text = _wizard_ask_text("Configuration file destination", default=str(state.config_path), required=True, input_func=input_func)
        try:
            selected_config = _wizard_validate_destination(config_text, "Configuration destination")
            break
        except ValueError as exc:
            print(f"  {exc}.")
            # Declining keeps the destination this run started with rather than asking for a path forever
            if not _wizard_offer_retry("configuration destination", input_func=input_func):
                print(f"  Keeping {state.config_path}.")
                selected_config = current_config
                break
    # Both sides are compared resolved, so an unchanged answer written a different way is not read as a move
    if selected_config != current_config:
        chosen_config = _wizard_choose_config_destination(selected_config, input_func=input_func)
        # Giving up on every offered path keeps the current destination rather than cancelling the whole setup
        if chosen_config is not None:
            state.config_path = chosen_config
    while True:
        env_text = _wizard_ask_text("Dotenv file destination", default=str(state.env_path), required=True, input_func=input_func)
        selected_env = current_env
        problem = ""
        if env_text.casefold() == "none":
            problem = "Setup needs a writable dotenv file and cannot use 'none'."
        else:
            try:
                selected_env = _wizard_validate_destination(env_text, "Dotenv destination")
            except ValueError as exc:
                problem = f"{exc}."
            else:
                # One file cannot hold both, since saving the configuration would overwrite the secrets beside it
                if selected_env == Path(state.config_path).expanduser().resolve():
                    problem = "The dotenv file has to be a different file from the configuration."
        if not problem:
            break
        print(f"  {problem}")
        if not _wizard_offer_retry("dotenv destination", input_func=input_func):
            print(f"  Keeping {state.env_path}.")
            selected_env = current_env
            break
    state.config_values["DOTENV_FILE"] = str(selected_env)
    if selected_env == current_env:
        return
    state.env_path = selected_env
    # A secret kept rather than retyped was never queued, so it would be missing from a dotenv file that just moved
    print("  The dotenv destination changed. Re-enter authentication and notification settings that may contain secrets.")
    _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func)
    print()
    _wizard_collect_spotify_section(state, input_func=input_func, getpass_func=getpass_func)
    print()
    _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func)
    print()
    _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func)


# Runs one editable section again after resetting only the keys it owns
def _wizard_edit_setup_section(state, input_func=None, getpass_func=None):
    options = [(label, description) for _name, label, description, _config_keys, _secret_keys in WIZARD_SECTIONS]
    options.append(("Return to summary", "Keep every current answer."))
    choice = _wizard_ask_choice("Which setup section should be changed?", options, input_func=input_func)
    if choice == len(WIZARD_SECTIONS):
        return
    name, _label, _description, config_keys, secret_keys = WIZARD_SECTIONS[choice]
    _wizard_reset_section(state, config_keys, secret_keys)
    if name == "Target":
        state.target = ""
    print()
    collectors = {
        "Target": lambda: _wizard_collect_target_section(state, input_func=input_func),
        "Polling": lambda: _wizard_collect_polling_section(state, input_func=input_func),
        "Authentication": lambda: _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func),
        "Spotify": lambda: _wizard_collect_spotify_section(state, input_func=input_func, getpass_func=getpass_func),
        "Tracking": lambda: _wizard_collect_tracking_section(state, input_func=input_func),
        "Output": lambda: _wizard_collect_output_section(state, input_func=input_func),
        "Email": lambda: _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func),
        "Webhook": lambda: _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func),
        "Destinations": lambda: _wizard_collect_destination_section(state, input_func=input_func, getpass_func=getpass_func),
    }
    collectors[name]()


# The theme part each setup summary row draws its value in, for rows whose value has a known kind
WIZARD_SUMMARY_VALUE_STYLES = {
    "Target": "username",
    "Polling interval while idle": "duration",
    "Polling interval while listening": "duration",
    "Inactivity threshold": "duration",
}


# Colours one setup summary value from its row label
def _wizard_summary_value(label, value):
    text = str(value)
    part = WIZARD_SUMMARY_VALUE_STYLES.get(label)
    if part:
        return colorize(part, text)
    if text.startswith("enabled") or text in ("complete", "yes"):
        return colorize("boolean_true", text)
    if text in ("disabled", "incomplete", "no", "none", "not set"):
        return colorize("boolean_false", text)
    return text


# Prints one aligned label and value block, so every summary row lines up
def _wizard_print_summary_rows(rows):
    width = max(len(label) for label, _ in rows) + 1
    for label, value in rows:
        print(f"  {(label + ':'):<{width}} {_wizard_summary_value(label, value)}")


# Names the alerts one channel will send, or says none
def _wizard_enabled_alerts(state, keys):
    labels = [WIZARD_ALERT_LABELS[key.replace("WEBHOOK_", "", 1) if key.startswith("WEBHOOK_") else key] for key in keys if state.config_values.get(key)]
    return ", ".join(labels) if labels else "none"


# Shows everything that is about to be written, by name and never by secret value
def _wizard_print_setup_summary(state):
    credentials_set = all(key in state.secret_updates or doctor_value_is_set(state.config_values.get(key)) for key in ("LASTFM_API_KEY", "LASTFM_API_SECRET"))
    tracked = [label for key, label in (("TRACK_FOLLOWERS", "followers"), ("TRACK_FOLLOWINGS", "followings"), ("TRACK_DISPLAY_NAME", "display name"), ("TRACK_BIO", "About Me")) if state.config_values.get(key)]
    spotify_enabled = bool(state.config_values.get("USE_TRACK_DURATION_FROM_SPOTIFY") or state.config_values.get("TRACK_SONGS"))
    spotify_app = "SP_CLIENT_ID" in state.secret_updates or doctor_value_is_set(state.config_values.get("SP_CLIENT_ID"))
    email_alerts = _wizard_enabled_alerts(state, WIZARD_EMAIL_NOTIFICATION_KEYS)
    webhook_alerts = _wizard_enabled_alerts(state, WIZARD_WEBHOOK_NOTIFICATION_KEYS) if state.config_values.get("WEBHOOK_ENABLED") else "none"
    rows = [
        ("Target", state.target or "not set"),
        ("Persist target", "yes" if state.persist_target else "no"),
        ("Polling interval while idle", _wizard_format_duration(int(state.config_values.get("LASTFM_CHECK_INTERVAL") or 0))),
        ("Polling interval while listening", _wizard_format_duration(int(state.config_values.get("LASTFM_ACTIVE_CHECK_INTERVAL") or 0))),
        ("Inactivity threshold", _wizard_format_duration(int(state.config_values.get("LASTFM_INACTIVITY_CHECK") or 0))),
        ("Authentication status", "complete" if credentials_set else "incomplete"),
        ("Spotify track details", ("enabled with an app" if spotify_app else "enabled, anonymous backend") if spotify_enabled else "disabled"),
        ("Profile tracking", ", ".join(tracked) if tracked else "disabled"),
        ("Email", "enabled" if email_alerts != "none" else "disabled"),
        ("Email notifications", email_alerts),
        ("Webhook", f"enabled ({webhook_provider_display_name(state.config_values.get('WEBHOOK_PROVIDER'))})" if state.config_values.get("WEBHOOK_ENABLED") else "disabled"),
        ("Webhook alerts", webhook_alerts),
        ("Output log", "disabled" if state.config_values.get("DISABLE_LOGGING") else "enabled"),
        ("CSV output", state.config_values.get("CSV_FILE") or "disabled"),
        ("Monitored track list", state.config_values.get("MONITOR_LIST_FILE") or "disabled"),
        ("Config destination", state.config_path),
        ("Dotenv destination", state.env_path),
        ("Install method", install_method()),
    ]
    print(colorize("header", "\nSetup summary\n"))
    _wizard_print_summary_rows(rows)


# Loops on the summary until the user saves or explicitly discards, so nothing is written by accident
def _wizard_review_setup(state, input_func=None, getpass_func=None):
    while True:
        _wizard_print_setup_summary(state)
        action = _wizard_ask_choice("What would you like to do?", [
            ("Save settings", "Write the displayed settings to the selected files."),
            ("Review or change settings", "Edit one section without losing the other answers."),
            ("Discard answers and exit", "Leave the destination files unchanged."),
        ], input_func=input_func)
        if action == 0:
            return True
        if action == 1:
            _wizard_edit_setup_section(state, input_func=input_func, getpass_func=getpass_func)
            continue
        print()
        if _wizard_ask_yes_no("Discard all entered answers and exit?", default=False, input_func=input_func):
            return False
        print("  Setup answers retained.")


# Prints where setup will write and which install method the printed commands are written for
def _wizard_print_setup_destinations(method, config_path, env_path):
    print(f"Detected install method: {colorize('username', method)}")
    print(f"Configuration:          {config_path}")
    print(f"Dotenv:                 {env_path}\n")


# Puts the values setup just saved into effect, so doctor checks the written files instead of the pre-setup state
def _wizard_apply_saved_values(state, env_path=None):
    # Config values first: they carry the unset placeholders for every secret, which would otherwise
    # overwrite the secrets applied below and make doctor report a working setup as unconfigured
    globals().update(state.config_values)
    for secret in SECRET_KEYS:
        record_secret_source(secret, "config file")
    saved_in_dotenv = frozenset()
    if env_path:
        try:
            from dotenv import dotenv_values, load_dotenv
            # Read before the load, because it is the only way to tell a value the file supplied from one already exported
            saved_in_dotenv = frozenset(name for name in dotenv_values(str(env_path)) if name in SECRET_KEYS)
            load_dotenv(str(env_path), override=True, interpolate=False)
        except Exception as exc:
            # Reading the file back needs python-dotenv, so the entered values are applied directly below
            debug_swallowed_exception("Dotenv reload after save", exc)
    for secret in SECRET_KEYS:
        value = os.environ.get(secret)
        if value is not None:
            globals()[secret] = value
            record_secret_source(secret, "dotenv file" if secret in saved_in_dotenv else "environment")
    # Secrets exported before startup keep winning here, exactly as they will when monitoring runs
    for key, value in state.secret_updates.items():
        if os.environ.get(key) is None and value:
            globals()[key] = value
            record_secret_source(key, "dotenv file")


# Builds the exact local command that starts this monitor, used when setup offers to launch it
def _wizard_local_command_args(target=None, config_path=None, env_path=None):
    executable = sys.executable or ("python" if platform.system() == "Windows" else "python3")
    arguments = [executable, "-m", TOOL_NAME] if install_method() == INSTALL_METHOD_PYPI else [executable, str(Path(__file__).resolve())]
    if target:
        arguments.append(str(target))
    if config_path:
        arguments.extend(["--config-file", str(config_path)])
    if env_path:
        arguments.extend(["--env-file", str(env_path)])
    return arguments


# Hands the terminal to the monitor, replacing this process where the platform allows it
def _wizard_launch_monitor(arguments):
    command = [str(argument) for argument in arguments]
    if platform.system() == "Windows":
        try:
            return subprocess.run(command, check=False).returncode
        except KeyboardInterrupt:
            return 0
    os.execv(command[0], command)
    return 0


# Runs the guided setup, holding every answer until the user saves
def run_setup_wizard(initial_target=None, config_file=None, env_file=None, input_func=None, getpass_func=None, interactive=None):
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        print("The setup wizard needs an interactive terminal (TTY).")
        print("Run --setup from an interactive shell or use --generate-config and edit the files manually.")
        print(f"Guide: {QUICK_START_GUIDE_URL}")
        return 1

    try:
        config_path, env_path = _wizard_destinations(config_file, env_file)
    except (ValueError, RecoveryError) as exc:
        print_recovery_error(exc, context="file", detail=str(exc))
        return 1

    print(colorize("header", "Setup Wizard\n"))
    print("This asks a few questions and writes a ready-to-run configuration.")
    _wizard_print_default_guidance()
    print("Secrets go to the dotenv file. Non-secret settings go to the config file.")
    print()
    _wizard_print_setup_destinations(install_method(), config_path, env_path)

    baseline_values = {name: value for name, value in globals().items() if name in _config_allowed_names()}
    state = WizardSetupState(config_path, env_path, baseline_values)
    state.config_values["DOTENV_FILE"] = str(env_path)

    try:
        # Asked before anything else, so a config that has to be replaced is agreed to rather than discovered at Save
        config_existed = Path(config_path).exists()
        chosen_config = _wizard_choose_config_destination(config_path, input_func=input_func)
        if chosen_config is None:
            print("\n" + colorize("warning", "Setup cancelled. Destination files were not changed."))
            return 1
        state.config_path = chosen_config
        # A destination nothing was asked about printed nothing, so the separator would leave a blank gap
        if config_existed:
            print()
        _wizard_collect_target_section(state, initial_target, input_func=input_func)
        print()
        _wizard_collect_polling_section(state, input_func=input_func)
        print()
        _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_spotify_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_tracking_section(state, input_func=input_func)
        print()
        _wizard_collect_output_section(state, input_func=input_func)
        print()
        _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func)
        if not _wizard_review_setup(state, input_func=input_func, getpass_func=getpass_func):
            print("\n" + colorize("warning", "Setup cancelled. Destination files were not changed."))
            return 1
    except (EOFError, KeyboardInterrupt):
        print(colorize("warning", "Setup cancelled. Destination files were not changed."))
        return 1

    # Everything above only filled the state, so this is the first and only point anything reaches disk
    try:
        backup_path, _written = write_generated_config(state.config_path, generate_config_with_current_values(state.config_values), force=True)
    except Exception as exc:
        print_recovery_error(exc, context="file", detail=f"Could not write the configuration to '{state.config_path}'")
        return 1
    dotenv_path = None
    # A cleared secret only has to leave a file that exists, so setup never creates one holding nothing
    if any(state.secret_updates.values()) or (state.secret_updates and Path(state.env_path).expanduser().is_file()):
        try:
            dotenv_path = update_dotenv_file(state.env_path, state.secret_updates)
        except Exception as exc:
            print_recovery_error(exc, context="file", detail=f"Could not write secrets to '{state.env_path}'")
            return 1

    print(colorize("header", "\nSaved files\n"))
    print(f"  Configuration: {state.config_path}")
    if backup_path:
        print(f"  Backup:        {backup_path}")
    if dotenv_path:
        print(f"  Secrets:       {dotenv_path}")

    doctor_exit = None
    if state.target:
        print()
    try:
        if state.target and _wizard_ask_yes_no("Run doctor now? It writes no files and offers real delivery tests only with separate approval.", default=True, input_func=input_func):
            print()
            _wizard_apply_saved_values(state, env_path=state.env_path if dotenv_path else None)
            doctor_exit = run_doctor(target_value=state.target, config_path=str(state.config_path), env_path=str(state.env_path) if dotenv_path else None)
    except (EOFError, KeyboardInterrupt):
        # The files are already written, so an interrupt here only skips the optional check
        print(colorize("warning", "Setup is saved. Use the commands below when ready."))

    env_argument = str(state.env_path) if dotenv_path else ""
    # A persisted target is already in the config file, so the printed commands stay short
    target_arguments = [] if state.persist_target or not state.target else [state.target]
    print(colorize("header", "\nNext steps\n"))
    _wizard_print_command("Check setup again:", render_command(["--doctor"] + target_arguments, config_path=str(state.config_path), env_path=env_argument))
    start_label = "After Doctor passes, start monitoring:" if doctor_exit not in (None, 0) else "Start monitoring:"
    _wizard_print_command(start_label, render_command(target_arguments, config_path=str(state.config_path), env_path=env_argument))
    print(f"Guide: {QUICK_START_GUIDE_URL}\n")

    try:
        # Only a doctor run that passed proves the saved setup can monitor, so the launch offer waits for it
        start_monitoring = bool(state.target and doctor_exit == 0 and _wizard_ask_yes_no("Start monitoring now? Monitoring will continue until Ctrl+C.", default=True, input_func=input_func))
    except (EOFError, KeyboardInterrupt):
        # The files are already written, so an interrupt here only skips the optional launch
        print(colorize("warning", "Setup is saved. Start monitoring with the command above when ready."))
        return 0
    if start_monitoring:
        launch_arguments = _wizard_local_command_args(target=None if state.persist_target else state.target, config_path=state.config_path, env_path=state.env_path if dotenv_path else None)
        sys.stdout.flush()
        return _wizard_launch_monitor(launch_arguments)
    return 0

# Names one parsed argument the way the user could have typed it, since an argparse destination is not
# always a flag: --debug is stored as debug_mode and a positional has no flag at all
def conflicting_argument_name(parser, dest, argv=None):
    typed = set(sys.argv[1:] if argv is None else argv)
    # argparse exposes no public listing of its arguments, so the actions it holds are read directly
    for action in getattr(parser, "_actions", ()):
        if action.dest != dest:
            continue
        if not action.option_strings:
            return str(action.metavar or dest.upper())
        return next((option for option in action.option_strings if option in typed), action.option_strings[0])
    return f"--{dest.replace('_', '-')}"


# Applies every command-line override that only assigns a setting, so the preflight report and the
# monitoring run are decided by the same values rather than by where in main each flag was handled
def apply_cli_overrides(args):
    global LASTFM_API_KEY, LASTFM_API_SECRET, SP_CLIENT_ID, SP_CLIENT_SECRET, SP_TOKENS_FILE, USE_TRACK_DURATION_FROM_SPOTIFY, LASTFM_CHECK_INTERVAL, LASTFM_ACTIVE_CHECK_INTERVAL, LASTFM_INACTIVITY_CHECK, LASTFM_BREAK_CHECK_MULTIPLIER, LIVENESS_REMINDER_SECONDS, CSV_FILE, MONITOR_LIST_FILE, DISABLE_LOGGING, ACTIVE_NOTIFICATION, INACTIVE_NOTIFICATION, TRACK_NOTIFICATION, SONG_NOTIFICATION, OFFLINE_ENTRIES_NOTIFICATION, SONG_ON_LOOP_NOTIFICATION, ERROR_NOTIFICATION, FOLLOWERS_NOTIFICATION, FOLLOWINGS_NOTIFICATION, PROFILE_NOTIFICATION, TRACK_FOLLOWINGS, TRACK_FOLLOWERS, TRACK_BIO, TRACK_DISPLAY_NAME, FRIENDS_CHECK_INTERVAL, FRIENDS_CHANGE_COUNTER, FRIENDS_RETRY_INTERVAL, TRACK_SONGS, PROGRESS_INDICATOR, DO_NOT_SHOW_DURATION_MARKS

    if args.lastfm_api_key:
        LASTFM_API_KEY = args.lastfm_api_key
        record_secret_source("LASTFM_API_KEY", "command line")

    if args.lastfm_secret:
        LASTFM_API_SECRET = args.lastfm_secret
        record_secret_source("LASTFM_API_SECRET", "command line")

    if args.spotify_creds:
        SP_CLIENT_ID, separator, SP_CLIENT_SECRET = args.spotify_creds.partition(":")
        if not separator or not SP_CLIENT_ID or not SP_CLIENT_SECRET:
            print_recovery_error(RecoveryError(make_recovery_advice("config.invalid", "-z / --spotify-creds is not in the expected format", recovery_fix_with_guide("Pass the client id and the client secret as one value separated by a colon", SPOTIFY_APP_GUIDE_URL), False)))
            sys.exit(1)
        record_secret_source("SP_CLIENT_ID", "command line")
        record_secret_source("SP_CLIENT_SECRET", "command line")

    # Emitted once every layer has been applied, so a support transcript answers where each credential came from
    grouped_secrets = secrets_by_source()
    # One line per source rather than one field per secret, since a secret name followed by = is what the redaction pass removes
    for secret_source, secret_names in grouped_secrets or [("none", [])]:
        debug_print("Secret sources", source=secret_source, names=" ".join(secret_names) or None)

    if SP_TOKENS_FILE:
        SP_TOKENS_FILE = os.path.expanduser(SP_TOKENS_FILE)

    if args.fetch_duration:
        USE_TRACK_DURATION_FROM_SPOTIFY = args.fetch_duration

    if args.check_interval:
        LASTFM_CHECK_INTERVAL = args.check_interval

    if args.active_interval:
        LASTFM_ACTIVE_CHECK_INTERVAL = args.active_interval

    if args.offline_timer:
        LASTFM_INACTIVITY_CHECK = args.offline_timer

    if args.break_multiplier:
        LASTFM_BREAK_CHECK_MULTIPLIER = args.break_multiplier

    # The interval can come from a config file, so the reminder is settled once every layer has been applied
    LIVENESS_REMINDER_SECONDS = LIVENESS_CHECK_INTERVAL if LIVENESS_CHECK_INTERVAL > 0 else 0

    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    else:
        if CSV_FILE:
            CSV_FILE = os.path.expanduser(CSV_FILE)

    if args.monitor_list:
        MONITOR_LIST_FILE = os.path.expanduser(args.monitor_list)
    else:
        if MONITOR_LIST_FILE:
            MONITOR_LIST_FILE = os.path.expanduser(MONITOR_LIST_FILE)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    if args.notify_active is True:
        ACTIVE_NOTIFICATION = True

    if args.notify_inactive is True:
        INACTIVE_NOTIFICATION = True

    if args.notify_track is True:
        TRACK_NOTIFICATION = True

    if args.notify_song_changes is True:
        SONG_NOTIFICATION = True

    if args.notify_offline_entries is True:
        OFFLINE_ENTRIES_NOTIFICATION = True

    if args.notify_loop is True:
        SONG_ON_LOOP_NOTIFICATION = True

    if args.notify_errors is False:
        ERROR_NOTIFICATION = False

    if args.notify_followers is True:
        FOLLOWERS_NOTIFICATION = True

    if args.notify_followings is True:
        FOLLOWINGS_NOTIFICATION = True

    if args.notify_profile is True:
        PROFILE_NOTIFICATION = True

    if args.track_followings is True:
        TRACK_FOLLOWINGS = True

    if args.track_followers is True:
        TRACK_FOLLOWERS = True

    if args.track_bio is True:
        TRACK_BIO = True

    if args.track_display_name is True:
        TRACK_DISPLAY_NAME = True

    if args.friends_check_interval:
        FRIENDS_CHECK_INTERVAL = args.friends_check_interval

    if args.friends_change_counter:
        FRIENDS_CHANGE_COUNTER = args.friends_change_counter

    if args.friends_retry_interval:
        FRIENDS_RETRY_INTERVAL = args.friends_retry_interval

    if args.track_in_spotify is True:
        TRACK_SONGS = True

    if args.progress is True:
        PROGRESS_INDICATOR = True

    if args.hide_duration_source is True:
        DO_NOT_SHOW_DURATION_MARKS = True

    if args.fetch_duration is True:
        USE_TRACK_DURATION_FROM_SPOTIFY = True

    if not USE_TRACK_DURATION_FROM_SPOTIFY:
        DO_NOT_SHOW_DURATION_MARKS = True


# Runs the command-line interface
def main():
    global CLI_CONFIG_PATH, CONFIG_DISCOVERY_DISABLED, DOTENV_FILE, CLEAR_SCREEN, COLORED_OUTPUT, COLOR_THEME, LIVENESS_REMINDER_SECONDS, LASTFM_USERNAME, LASTFM_API_KEY, LASTFM_API_SECRET, SP_CLIENT_ID, SP_CLIENT_SECRET, SP_TOKENS_FILE, CSV_FILE, MONITOR_LIST_FILE, FILE_SUFFIX, DISABLE_LOGGING, LF_LOGFILE, ACTIVE_NOTIFICATION, INACTIVE_NOTIFICATION, TRACK_NOTIFICATION, SONG_NOTIFICATION, SONG_ON_LOOP_NOTIFICATION, OFFLINE_ENTRIES_NOTIFICATION, ERROR_NOTIFICATION, WEBHOOK_ENABLED, WEBHOOK_URL, WEBHOOK_PROVIDER, WEBHOOK_ACTIVE_NOTIFICATION, WEBHOOK_INACTIVE_NOTIFICATION, WEBHOOK_TRACK_NOTIFICATION, WEBHOOK_SONG_NOTIFICATION, WEBHOOK_SONG_ON_LOOP_NOTIFICATION, WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION, WEBHOOK_FOLLOWERS_NOTIFICATION, WEBHOOK_FOLLOWINGS_NOTIFICATION, WEBHOOK_PROFILE_NOTIFICATION, WEBHOOK_ERROR_NOTIFICATION, LASTFM_CHECK_INTERVAL, LASTFM_ACTIVE_CHECK_INTERVAL, LASTFM_INACTIVITY_CHECK, TRACK_SONGS, PROGRESS_INDICATOR, USE_TRACK_DURATION_FROM_SPOTIFY, DO_NOT_SHOW_DURATION_MARKS, LASTFM_BREAK_CHECK_MULTIPLIER, SMTP_PASSWORD, stdout_bck, TRACK_FOLLOWINGS, TRACK_FOLLOWERS, TRACK_BIO, TRACK_DISPLAY_NAME, FRIENDS_CHECK_INTERVAL, FOLLOWERS_NOTIFICATION, FOLLOWINGS_NOTIFICATION, PROFILE_NOTIFICATION, FRIENDS_CHANGE_COUNTER, FRIENDS_RETRY_INTERVAL, VERBOSE_MODE, DEBUG_MODE, TRUNCATE_CHARS, LASTFM_USERNAME_GLOBAL

    if "--generate-config" in sys.argv and not any(flag in sys.argv for flag in SECRET_ACTION_FLAGS):
        config_content = CONFIG_BLOCK.strip("\n") + "\n"
        try:
            idx = sys.argv.index("--generate-config")
            if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
                # Writing the file directly avoids the UTF-16 output redirection in some Windows PowerShell versions
                output_file = sys.argv[idx + 1]
                backup_path, written = write_generated_config(output_file, config_content, force="--force" in sys.argv)
                if not written:
                    print("Config was not replaced. The existing file is unchanged")
                    sys.exit(1)
                print(f"Config written to: {output_file}")
                if backup_path:
                    print(f"Previous config backed up to: {backup_path}")
                sys.exit(0)
        except (ValueError, IndexError):
            pass
        except FileExistsError as exc:
            print_recovery_error(exc, context="file.exists", detail=str(exc))
            sys.exit(1)
        except OSError as exc:
            print_recovery_error(exc, context="file", detail=f"The config file could not be written: {exc}")
            sys.exit(1)
        sys.stdout.buffer.write(config_content.encode("utf-8"))
        sys.stdout.buffer.flush()
        sys.exit(0)

    if "--version" in sys.argv and not any(flag in sys.argv for flag in SECRET_ACTION_FLAGS):
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # The screen clearing and the version line both run before argparse, so the settings that decide
    # them are resolved from the config file first rather than from the built-in defaults alone
    apply_early_output_config()

    # Read straight from sys.argv because argparse has not run yet, and the screen is cleared and the
    # version line printed before it does. Debug mode is read first so it also traces the colour setup
    if "--debug" in sys.argv:
        DEBUG_MODE = True

    if "--no-color" in sys.argv:
        COLORED_OUTPUT = False

    init_color_output(stdout_bck)

    if CLEAR_SCREEN and DEBUG_MODE:
        debug_print("Terminal screen clear", outcome="skipped", reason="debug mode is active")

    clear_screen(CLEAR_SCREEN and not keep_terminal_history() and not DEBUG_MODE)

    print_startup_banner()

    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=(f"Monitor a Last.fm user's scrobbles and send customizable email or webhook alerts [ {PROJECT_URL}/ ]"), epilog=help_examples(), formatter_class=argparse.RawTextHelpFormatter, **argparse_color_kwargs()
    )

    # Positional
    parser.add_argument(
        "username",
        nargs="?",
        metavar="LASTFM_USERNAME",
        help="Last.fm username to monitor"
    )

    # Version, just to list in help, it is handled earlier
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s v{VERSION}"
    )

    # Configuration & dotenv files
    conf = parser.add_argument_group("Configuration & dotenv files")
    conf.add_argument(
        "--config-file",
        dest="config_file",
        metavar="PATH",
        help="Location of the optional config file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--doctor",
        dest="doctor",
        action="store_true",
        default=None,
        help="Run read-only preflight checks and report what is ready and what is not"
    )
    conf.add_argument(
        "--generate-config",
        nargs="?",
        const=True,
        metavar="FILENAME",
        help="Print default config template and exit (on Windows PowerShell, specify a filename to avoid redirect encoding issues)",
    )
    conf.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help="Let --generate-config replace an existing file, after a timestamped backup",
    )
    conf.add_argument(
        "--setup",
        dest="setup",
        action="store_true",
        help="Run the guided setup and write a ready-to-run configuration",
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--set-webhook-url",
        dest="set_webhook_url",
        action="store_true",
        help="Save a Discord or ntfy webhook URL through a hidden prompt",
    )
    conf.add_argument(
        "--set-smtp-password",
        dest="set_smtp_password",
        action="store_true",
        help="Enter the SMTP password privately, check it against the mail server and save it to the dotenv file",
    )
    conf.add_argument(
        "--set-lastfm-credentials",
        dest="set_lastfm_credentials",
        action="store_true",
        help="Save Last.fm API credentials through hidden prompts",
    )
    conf.add_argument(
        "--set-spotify-credentials",
        dest="set_spotify_credentials",
        action="store_true",
        help="Save optional Spotify OAuth app credentials through hidden prompts",
    )

    # API credentials
    creds = parser.add_argument_group("API credentials")
    creds.add_argument(
        "-u", "--lastfm-api-key",
        dest="lastfm_api_key",
        metavar="LASTFM_API_KEY",
        help="Last.fm API key"
    )
    creds.add_argument(
        "-w", "--lastfm-secret",
        dest="lastfm_secret",
        metavar="LASTFM_API_SECRET",
        help="Last.fm API secret"
    )
    creds.add_argument(
        "-z", "--spotify-creds",
        dest="spotify_creds",
        metavar="SPOTIFY_CLIENT_ID:SPOTIFY_CLIENT_SECRET",
        help="Optional Spotify OAuth app credentials"
    )
    # Email notifications
    notify = parser.add_argument_group("Email notifications")
    notify.add_argument(
        "-a", "--notify-active",
        dest="notify_active",
        action="store_true",
        default=None,
        help="Email when user becomes active"
    )
    notify.add_argument(
        "-i", "--notify-inactive",
        dest="notify_inactive",
        action="store_true",
        default=None,
        help="Email when user goes inactive"
    )
    notify.add_argument(
        "-t", "--notify-track",
        dest="notify_track",
        action="store_true",
        default=None,
        help="Email when a monitored track/album plays"
    )
    notify.add_argument(
        "-j", "--notify-song-changes",
        dest="notify_song_changes",
        action="store_true",
        default=None,
        help="Email on every song change"
    )
    notify.add_argument(
        "-f", "--notify-offline-entries",
        dest="notify_offline_entries",
        action="store_true",
        default=None,
        help="Email when new scrobbles arrive while user is offline"
    )
    notify.add_argument(
        "-x", "--notify-loop",
        dest="notify_loop",
        action="store_true",
        default=None,
        help="Email when user plays a song on loop"
    )
    notify.add_argument(
        "--notify-followers",
        dest="notify_followers",
        action="store_true",
        default=None,
        help="Email when followers change"
    )
    notify.add_argument(
        "--notify-followings",
        dest="notify_followings",
        action="store_true",
        default=None,
        help="Email when followings (friends) change"
    )
    notify.add_argument(
        "--notify-profile",
        dest="notify_profile",
        action="store_true",
        default=None,
        help="Email when a tracked bio or display name changes"
    )
    notify.add_argument(
        "-e", "--no-error-notify",
        action="store_false",
        dest="notify_errors",
        default=None,
        help="Disable email on errors (e.g. invalid API key)"
    )
    notify.add_argument(
        "--send-test-email",
        dest="send_test_email",
        action="store_true",
        help="Send test email to verify SMTP settings"
    )

    webhook_notify = parser.add_argument_group("Webhook notifications")
    webhook_toggle = webhook_notify.add_mutually_exclusive_group()
    webhook_toggle.add_argument("--webhook", dest="webhook_enabled", action="store_true", default=None, help="Enable the configured webhook alerts")
    webhook_toggle.add_argument("--no-webhook", dest="webhook_enabled", action="store_false", default=None, help="Disable the configured webhook alerts")
    webhook_notify.add_argument("--webhook-url", dest="webhook_url", metavar="URL", type=str, help="Use one Discord webhook or ntfy topic URL for this run (may remain in shell history)")
    webhook_notify.add_argument("--webhook-provider", dest="webhook_provider", choices=("discord", "ntfy"), help="Webhook request format for this run (default: configured provider)")
    webhook_notify.add_argument("--webhook-active", dest="webhook_active", action="store_true", default=None, help="Send a webhook alert when the user becomes active")
    webhook_notify.add_argument("--webhook-inactive", dest="webhook_inactive", action="store_true", default=None, help="Send a webhook alert when the user goes inactive")
    webhook_notify.add_argument("--webhook-track", dest="webhook_track", action="store_true", default=None, help="Send a webhook alert when a monitored track or album plays")
    webhook_notify.add_argument("--webhook-song-changes", dest="webhook_song_changes", action="store_true", default=None, help="Send a webhook alert on every song change")
    webhook_notify.add_argument("--webhook-loop", dest="webhook_loop", action="store_true", default=None, help="Send a webhook alert when the user plays a song on loop")
    webhook_notify.add_argument("--webhook-offline-entries", dest="webhook_offline_entries", action="store_true", default=None, help="Send a webhook alert when new scrobbles arrive while the user is offline")
    webhook_notify.add_argument("--webhook-followers", dest="webhook_followers", action="store_true", default=None, help="Send a webhook alert when followers change")
    webhook_notify.add_argument("--webhook-followings", dest="webhook_followings", action="store_true", default=None, help="Send a webhook alert when followings change")
    webhook_notify.add_argument("--webhook-profile", dest="webhook_profile", action="store_true", default=None, help="Send a webhook alert when a tracked bio or display name changes")
    webhook_error_toggle = webhook_notify.add_mutually_exclusive_group()
    webhook_error_toggle.add_argument("--webhook-errors", dest="webhook_errors", action="store_true", default=None, help="Send webhook alerts when monitoring has a problem")
    webhook_error_toggle.add_argument("--no-webhook-error-notify", dest="webhook_errors", action="store_false", default=None, help="Disable webhook alerts when monitoring has a problem")
    webhook_notify.add_argument("--send-test-webhook", dest="send_test_webhook", action="store_true", help="Send one test webhook without starting monitoring")

    # Intervals & Timers
    times = parser.add_argument_group("Intervals & timers")
    times.add_argument(
        "-c", "--check-interval",
        dest="check_interval",
        metavar="SECONDS",
        type=int,
        help="Polling interval when user is offline"
    )
    times.add_argument(
        "-k", "--active-interval",
        dest="active_interval",
        metavar="SECONDS",
        type=int,
        help="Polling interval when user is active"
    )
    times.add_argument(
        "-o", "--offline-timer",
        dest="offline_timer",
        metavar="SECONDS",
        type=int,
        help="Time to mark inactive user as offline"
    )
    times.add_argument(
        "-m", "--break-multiplier",
        dest="break_multiplier",
        metavar="N",
        type=int,
        help="Detect play breaks as N×active-interval"
    )
    times.add_argument(
        "--friends-check-interval",
        dest="friends_check_interval",
        metavar="SECONDS",
        type=int,
        help="How often to check for friend and profile changes"
    )
    times.add_argument(
        "--friends-change-counter",
        dest="friends_change_counter",
        metavar="N",
        type=int,
        help="Number of consecutive checks to confirm friend or profile changes"
    )
    times.add_argument(
        "--friends-retry-interval",
        dest="friends_retry_interval",
        metavar="SECONDS",
        type=int,
        help="Retry timeout for friend or profile change confirmation"
    )

    # Listing mode
    listing = parser.add_argument_group("User information & listing")

    listing.add_argument(
        "-l", "--list-recent",
        dest="list_recent",
        action="store_true",
        help="Print the user's most recent tracks"
    )
    listing.add_argument(
        "-n", "--recent-count",
        dest="recent_count",
        metavar="N",
        type=int,
        help="Number of recent tracks to list (use with -l)"
    )

    # Features & Output
    opts = parser.add_argument_group("Features & output")
    opts.add_argument(
        "-p", "--progress",
        dest="progress",
        action="store_true",
        default=None,
        help="Show a progress indicator while user is listening"
    )
    opts.add_argument(
        "-g", "--track-in-spotify",
        dest="track_in_spotify",
        action="store_true",
        default=None,
        help="Auto-play each scrobble in your Spotify client"
    )
    opts.add_argument(
        "-r", "--fetch-duration",
        dest="fetch_duration",
        action="store_true",
        default=None,
        help="Fetch track duration through Spotify OAuth app or anonymous web metadata"
    )
    opts.add_argument(
        "-q", "--hide-duration-source",
        dest="hide_duration_source",
        action="store_true",
        default=None,
        help="Do not show whether duration came from Last.fm or Spotify"
    )
    opts.add_argument(
        "-b", "--csv-file",
        dest="csv_file",
        metavar="CSV_FILE",
        type=str,
        help="Write every scrobble to a CSV file"
    )
    opts.add_argument(
        "-s", "--monitor-list",
        dest="monitor_list",
        metavar="TRACKS_FILE",
        type=str,
        help="Filename with tracks/albums to alert on"
    )
    opts.add_argument(
        "--track-followings",
        dest="track_followings",
        action="store_true",
        default=None,
        help="Track changes in user's followings (friends)"
    )
    opts.add_argument(
        "--track-followers",
        dest="track_followers",
        action="store_true",
        default=None,
        help="Track changes in user's followers"
    )
    opts.add_argument(
        "--track-bio",
        dest="track_bio",
        action="store_true",
        default=None,
        help="Track changes in user's About You bio"
    )
    opts.add_argument(
        "--track-display-name",
        dest="track_display_name",
        action="store_true",
        default=None,
        help="Track changes in user's public display name"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        default=None,
        help="Disable logging to lastfm_monitor_<username>.log"
    )
    opts.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        default=None,
        help="Disable coloured output in the terminal"
    )
    opts.add_argument(
        "--truncate",
        dest="truncate",
        metavar="N",
        type=int,
        help="Max characters per screen line (not log), use 999 to auto-detect terminal width, ignored if -d is set"
    )
    opts.add_argument(
        "--verbose",
        dest="verbose",
        action="store_true",
        default=None,
        help="Print extra startup and runtime detail (overrides VERBOSE_MODE)"
    )
    opts.add_argument(
        "--debug",
        dest="debug_mode",
        action="store_true",
        default=None,
        help="Enable debug mode (full API traces, internal logic logs)"
    )

    args = parser.parse_args()

    # Applied before the config file so its own failures and the secret resolution traces are visible, then
    # applied again afterwards so a saved VERBOSE_MODE or DEBUG_MODE of False cannot erase the command line
    apply_diagnostic_cli_flags(args)

    if args.config_file:
        CONFIG_DISCOVERY_DISABLED = args.config_file.casefold() == "none"
        # The sentinel is kept unexpanded, so every command this run prints reads back the setup it used
        CLI_CONFIG_PATH = args.config_file if CONFIG_DISCOVERY_DISABLED else os.path.expanduser(args.config_file)

    cfg_path = find_config_file(CLI_CONFIG_PATH)

    # A missing path is still an error, since only the literal 'none' is a selection.
    # Setup is allowed to name a file that does not exist yet, since creating it is the point
    if not cfg_path and CLI_CONFIG_PATH and not CONFIG_DISCOVERY_DISABLED and not args.setup:
        print_recovery_error(context="config", detail=f"Config file '{CLI_CONFIG_PATH}' does not exist")
        sys.exit(1)

    if cfg_path:
        if not load_config_file(cfg_path):
            sys.exit(1)

    apply_diagnostic_cli_flags(args)

    if args.no_color is True:
        COLORED_OUTPUT = False

    # Re-initialised so a COLORED_OUTPUT or COLOR_THEME the config file sets reaches everything printed from here
    init_color_output(stdout_bck)

    # Runs after the config file is read, so a saved LASTFM_USERNAME counts as a target
    if len(sys.argv) == 1 and not LASTFM_USERNAME:
        sys.exit(print_welcome_screen())

    apply_tls_verification_setting()

    # Anything already set once the config file has been read came from the settings, edited in place or loaded
    for secret in SECRET_KEYS:
        record_secret_source(secret, "config file")

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    private_actions = {
        "set_webhook_url": args.set_webhook_url,
        "set_lastfm_credentials": args.set_lastfm_credentials,
        "set_spotify_credentials": args.set_spotify_credentials,
        # Runs after the config file is read, so the mail server it signs in to is the one monitoring would use
        "set_smtp_password": args.set_smtp_password,
    }
    selected_private_actions = [name for name, enabled in private_actions.items() if enabled]
    if len(selected_private_actions) > 1:
        parser.error("Private setup commands cannot be combined")
    if selected_private_actions:
        allowed_private_args = {"config_file", "env_file", *private_actions}
        conflicts = [name for name, value in vars(args).items() if name not in allowed_private_args and value is not None and value is not False]
        if conflicts:
            parser.error(f"--{selected_private_actions[0].replace('_', '-')} cannot be combined with " + ", ".join(conflicting_argument_name(parser, name) for name in conflicts))
        private_env_file = DOTENV_FILE or None
        runners = {
            "set_webhook_url": run_set_webhook_url,
            "set_lastfm_credentials": run_set_lastfm_credentials,
            "set_spotify_credentials": run_set_spotify_credentials,
            "set_smtp_password": run_set_smtp_password,
        }
        try:
            runners[selected_private_actions[0]](env_file=private_env_file)
        except (PrivateSettingsError, RecoveryError) as exc:
            print_recovery_error(exc, context=selected_private_actions[0])
            sys.exit(1)
        sys.exit(0)

    exported_secrets = frozenset(secret for secret in SECRET_KEYS if os.getenv(secret) is not None)

    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        try:
            from dotenv import load_dotenv, find_dotenv

            # An exported variable wins over the file at startup, matching python-dotenv's own default, so a
            # one-off secret or one injected by systemd or a container is not silently shadowed by the dotenv.
            # The SIGHUP reload still overrides, because there the edited file is exactly what must take effect.
            if DOTENV_FILE:
                env_path = DOTENV_FILE
                # A command that is about to write that file is naming its destination, not a missing file
                if not os.path.isfile(env_path) and not command_writes_dotenv(sys.argv[1:]):
                    print(f"* Warning: dotenv file '{env_path}' does not exist\n")
                else:
                    load_dotenv(env_path, override=False, interpolate=False)
            else:
                env_path = find_dotenv() or None
                if env_path:
                    load_dotenv(env_path, override=False, interpolate=False)
        except ImportError:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            if env_path:
                print_recovery_advice(missing_dependency_advice("python-dotenv", f"The dotenv file '{env_path}' was not loaded", "Or export the secrets as environment variables"), label="Warning")

    # Environment variables are a documented alternative to a dotenv file, so they apply even when no file was loaded
    for secret in SECRET_KEYS:
        val = os.getenv(secret)
        if val is not None:
            globals()[secret] = val
            record_secret_source(secret, "environment" if secret in exported_secrets else "dotenv file")

    apply_webhook_cli_overrides(args, parser)
    apply_cli_overrides(args)

    # The positional wins over the saved setting, and every read below sees the settled target
    if not args.username and LASTFM_USERNAME:
        args.username = LASTFM_USERNAME

    if args.setup:
        # Runs here rather than earlier so the values already in effect become the defaults it offers
        sys.exit(run_setup_wizard(initial_target=args.username, config_file=args.config_file or cfg_path, env_file=args.env_file or env_path))

    if args.doctor:
        doctor_exit = run_doctor(target_value=args.username, config_path=cfg_path, env_path=env_path)
        # Printed here rather than inside the run, so the wizard's own next steps are not followed by a second copy
        print_doctor_next_steps(args.username, doctor_exit)
        sys.exit(doctor_exit)

    # A target is optional only for the utility actions below. Checked after the dotenv file is resolved so the
    # command this prints carries the files this run was given, and before the credentials because the username
    # is on the command line the user just typed while a key may live in a file they have never created
    if not args.username and not (args.send_test_email or args.send_test_webhook):
        print_recovery_error(context="target.missing")
        sys.exit(1)

    if args.send_test_email:
        missing = mail_settings_missing(MAIL_DELIVERY_SETTINGS)
        if missing:
            print_recovery_error(context="email", detail=f"The mail server settings are incomplete, {join_setting_names(missing, 'and')} {'is' if len(missing) == 1 else 'are'} not set")
            sys.exit(1)
        print("* Sending test email notification ...\n")
        if send_email(TEST_EMAIL_SUBJECT, TEST_EMAIL_BODY, "", SMTP_SSL, smtp_timeout=DOCTOR_SMTP_TIMEOUT) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if args.send_test_webhook:
        if not validate_webhook_url():
            print_recovery_error(context="webhook", detail="WEBHOOK_URL must contain a complete HTTPS link")
            sys.exit(1)
        print("* Sending test webhook notification ...\n")
        if send_webhook(TEST_WEBHOOK_TITLE, TEST_WEBHOOK_BODY, "song", force=True) == 0:
            print("* Webhook sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if WEBHOOK_ENABLED and not validate_webhook_url():
        print("* Webhook alerts are off because WEBHOOK_URL is not a complete HTTPS link\n")
        WEBHOOK_ENABLED = False

    if not check_internet():
        sys.exit(1)

    # Kept as a backstop, so every path below reads a target that is known to be set
    if not args.username:
        print_recovery_error(context="target.missing")
        sys.exit(1)

    if not doctor_value_is_set(LASTFM_API_KEY):
        print_recovery_error(context="secret.missing", detail="LASTFM_API_KEY (-u / --lastfm-api-key) is empty or still the placeholder value")
        sys.exit(1)

    if not doctor_value_is_set(LASTFM_API_SECRET):
        print_recovery_error(context="secret.missing", detail="LASTFM_API_SECRET (-w / --lastfm-secret) is empty or still the placeholder value")
        sys.exit(1)

    LASTFM_USERNAME_GLOBAL = args.username

    network = pylast.LastFMNetwork(LASTFM_API_KEY, LASTFM_API_SECRET)
    user = network.get_user(args.username)

    if CSV_FILE:
        try:
            with open(CSV_FILE, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
            debug_print("CSV destination check", path=CSV_FILE, outcome="OK")
        except Exception as e:
            debug_print("CSV destination check", path=CSV_FILE, outcome="failed", error=f"{type(e).__name__}: {e}")
            print_recovery_error(e, context="file.unwritable", detail=f"The CSV file '{CSV_FILE}' cannot be opened for writing")
            sys.exit(1)

    if args.list_recent:
        if args.recent_count and args.recent_count > 0:
            tracks_n = args.recent_count
        else:
            tracks_n = 30
        try:
            lastfm_list_tracks(args.username, user, network, tracks_n, CSV_FILE)
        except Exception as e:
            print_recovery_error(e)
            sys.exit(1)
        sys.exit(0)

    if MONITOR_LIST_FILE:
        try:
            try:
                with open(MONITOR_LIST_FILE, encoding="utf-8") as file:
                    lines = file.read().splitlines()
            except UnicodeDecodeError:
                with open(MONITOR_LIST_FILE, encoding="cp1252") as file:
                    lines = file.read().splitlines()

            lf_tracks = [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
            debug_print("Monitored tracks read", path=MONITOR_LIST_FILE, tracks=len(lf_tracks), outcome="OK")
        except Exception as e:
            debug_print("Monitored tracks read", path=MONITOR_LIST_FILE, outcome="failed", error=f"{type(e).__name__}: {e}")
            print_recovery_error(e, context="file", detail=f"The file with Last.fm tracks '{MONITOR_LIST_FILE}' cannot be opened")
            sys.exit(1)
    else:
        lf_tracks = []

    try:
        ascii_log_separators_enabled()
    except ValueError as e:
        print_recovery_error(RecoveryError(make_recovery_advice("config.invalid", str(e), recovery_fix_with_guide('Set ASCII_LOG_SEPARATORS to "Auto", "On" or "Off"', TERMINAL_GUIDE_URL), False)))
        sys.exit(1)

    TRUNCATE_CHARS = resolve_truncate_chars(args.truncate, TRUNCATE_CHARS, DISABLE_LOGGING)

    if not DISABLE_LOGGING:
        # The same helper the doctor reports from, so the reported destination is the one the run writes to
        log_path = build_log_path(LF_LOGFILE, args.username)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        FINAL_LOG_PATH = str(log_path)
        sys.stdout = Logger(FINAL_LOG_PATH)
    else:
        FINAL_LOG_PATH = None
        # Upstream text still reaches the terminal without a log file, so it is sanitized by a stream either way
        sys.stdout = TerminalStream(sys.stdout)

    # Check for beautifulsoup4 if friend or profile tracking is enabled
    if friends_check_enabled():
        try:
            # Imported only to check availability and report a friendly install command when it is missing
            import bs4  # type: ignore  # noqa: F401
        except ImportError:
            print_recovery_error(RecoveryError(make_recovery_advice("dependency.missing", "Friend and profile tracking needs beautifulsoup4, which is not installed", recovery_fix_with_guide(f"Install it with: {install_dependency_command('beautifulsoup4')}", INSTALL_GUIDE_URL), False)))
            sys.exit(1)

    if SMTP_HOST.startswith("your_smtp_server_"):
        ACTIVE_NOTIFICATION = False
        INACTIVE_NOTIFICATION = False
        SONG_NOTIFICATION = False
        TRACK_NOTIFICATION = False
        OFFLINE_ENTRIES_NOTIFICATION = False
        SONG_ON_LOOP_NOTIFICATION = False
        PROFILE_NOTIFICATION = False
        ERROR_NOTIFICATION = False
        verbose_notice("Email notifications are off because SMTP_HOST is still the shipped placeholder")

    emit_startup_summary(build_startup_summary(args.username, cfg_path, env_path, FINAL_LOG_PATH), show_full=full_startup_summary_enabled())

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_song_notifications_signal_handler)
        signal.signal(signal.SIGURG, toggle_progress_indicator_signal_handler)
        signal.signal(signal.SIGCONT, toggle_track_notifications_signal_handler)
        signal.signal(signal.SIGPIPE, toggle_songs_on_loop_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_inactivity_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_inactivity_check_signal_handler)
        signal.signal(signal.SIGHUP, reload_secrets_signal_handler)

    out = f"Monitoring user {args.username}"
    print(out)
    # print("-" * len(out))
    print("─" * HORIZONTAL_LINE)

    lastfm_monitor_user(user, network, args.username, lf_tracks, CSV_FILE)

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()
