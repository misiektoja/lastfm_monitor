# lastfm_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 2.1 (22 May 2025)

**Features and Improvements**:

- **NEW:** The tool can now be installed via pip: `pip install lastfm_monitor`
- **NEW:** Added support for external config files, environment-based secrets and dotenv integration with auto-discovery
- **NEW:** Added support for saving recent tracks to CSV when using `-l` with `-b`
- **IMPROVE:** Improved parsing of tracks file: supports CP1252 encoding, comment lines (starting with `#`) and ignores empty lines
- **IMPROVE:** Refactored comparison logic between listed and played tracks for better accuracy
- **IMPROVE:** Enhanced startup summary to show loaded config, dotenv and monitored tracks file paths
- **IMPROVE:** Simplified and renamed command-line arguments for improved usability
- **NEW:** Implemented SIGHUP handler for dynamic reload of secrets from dotenv files (previous handler for progress indicator has been assigned to SIGURG)
- **NEW:** Added configuration option to control clearing the terminal screen at startup
- **IMPROVE:** Changed connectivity check to use Last.fm Audio Scrobbler endpoint for reliability
- **IMPROVE:** Added check for missing pip dependencies with install guidance
- **IMPROVE:** Allow disabling liveness check by setting interval to 0 (default changed to 12h)
- **IMPROVE:** Improved handling of log file creation
- **IMPROVE:** Refactored CSV file initialization and processing
- **NEW:** Added support for `~` path expansion across all file paths
- **IMPROVE:** Refactored code structure to support packaging for PyPI
- **IMPROVE:** Enforced configuration option precedence: code defaults < config file < env vars < CLI flags
- **IMPROVE:** Updated horizontal line for improved output aesthetics
- **IMPROVE:** Removed short option for `--send-test-email` to avoid ambiguity

**Bug fixes**:

- **BUGFIX:** Fixed issue handling 'track songs' files encoded in Windows-1252/CP1252 

# Changes in 2.0.1 (25 Mar 2025)

**Bug fixes**:

- **BUGFIX:** Fixes the issue with using the incorrect Spotify API endpoint for validation (it consistently returned a 401 error since the client credentials flow does not provide access to it)

# Changes in 2.0 (21 Mar 2025)

**Features and Improvements**:

- **NEW:** Added support for the Spotify Web API (client credentials flow) to address recent changes in the Spotify Web Player token endpoint; it requires the spotipy pip module (optional, only for Spotify-related features)
- **NEW:** Caching mechanism to avoid unnecessary Spotify token refreshes
- **IMPROVE:** Email notification flags are now automatically disabled if the SMTP configuration is invalid
- **IMPROVE:** Exception handling in few places
- **IMPROVE:** Code cleanup & linting fixes

# Changes in 1.9 (03 Nov 2024)

**Features and Improvements**:

- **NEW:** Support for YouTube Music search URLs

**Bug fixes**:

- **BUGFIX:** Fixed small bug with occasionally wrongly reported new offline entries

# Changes in 1.8 (15 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new parameter (**-y** / **--send_test_email_notification**) which allows to send test email notification to verify SMTP settings defined in the script
- **IMPROVE:** Checking if correct version of Python (>=3.8) is installed
- **IMPROVE:** Possibility to define email sending timeout (default set to 15 secs)

**Bug fixes**:

- **BUGFIX:** Fixed "SyntaxError: f-string: unmatched (" issue in older Python versions
- **BUGFIX:** Fixed "SyntaxError: f-string expression part cannot include a backslash" issue in older Python versions

# Changes in 1.7 (07 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new signal handler for SIGPIPE allowing to switch songs on loop email notifications
- **IMPROVE:** Better handling of situations when new offline entries show up just before user gets online
- **IMPROVE:** Switching offline entries notifications included in SIGUSR1 signal handler
- **IMPROVE:** Better way of checking for error strings (without case sensitivity) + some additional ones added to the list
- **NEW:** Support for float type of timestamps added in date/time related functions + get_short_date_from_ts() rewritten to display year if show_year == True and current year is different, also can omit displaying hour and minutes if show_hours == False

**Bug fixes**:

- **BUGFIX:** Escaping of exception error string fixed

# Changes in 1.6 (24 May 2024)

**Features and Improvements**:

- **NEW:** Suppressing repeating API or network related errors (check **ERROR_500_NUMBER_LIMIT**, **ERROR_500_TIME_LIMIT**, **ERROR_NETWORK_ISSUES_NUMBER_LIMIT** and **ERROR_NETWORK_ISSUES_TIME_LIMIT** variables)
- **IMPROVE:** Information about log file name visible in the start screen
- **IMPROVE:** Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime

**Bug fixes**:

- **BUGFIX:** Fixed issues with sporadic broken links in HTML emails (vars with special characters are now escaped properly)
- **BUGFIX:** One very important space removed in the subject of active email notification

# Changes in 1.5 (18 May 2024)

**Features and Improvements**:

- **NEW:** Full support for real-time playing of tracked songs (**-g**) in Spotify client in **Linux**
- **NEW:** New way of playing tracked songs (**-g**) in Spotify client in **Windows**
- **NEW:** Rewritten code for playing tracked songs (**-g**) in Spotify client in **macOS**
- **IMPROVE:** Improvements for running the code in Python under Windows
- **IMPROVE:** Better checking for wrong command line arguments
- **IMPROVE:** Showing listened percentage for last listened track
- **IMPROVE:** Duplicate entries are counted now and displayed in the console & emails (more entries indicate higher chance of private mode)
- **IMPROVE:** pep8 style convention corrections

**Bug fixes**:

- **BUGFIX:** Fixed bug when **track_songs** functionality (**-g**) was not working without **-r**
- **BUGFIX:** Improved exception handling while processing JSON files
- **BUGFIX:** Better handling of Spotify HTTP requests exceptions when getting track ID and duration in spotify_search_song_trackid_duration()
- **BUGFIX:** Better handling of exceptions when listing tracks

# Changes in 1.4 (11 May 2024)

**Features and Improvements**:

- **NEW:** Possibility to fetch track duration from Spotify, instead of Last.fm which very often reports wrong duration (or none at all); if you enable **USE_TRACK_DURATION_FROM_SPOTIFY** to **True** in *[lastfm_monitor.py](lastfm_monitor.py)* file (or use **-r** / **--fetch_duration_from_spotify** parameter) and have SP_DC_COOKIE set in the script (or via new -z / --spotify_dc_cookie parameter) then the tool will try to get the track duration from Spotify; you will be able to tell if the track duration comes from Spotify as it has S* suffix at the end (e.g. 3 minutes, 42 seconds S*), while those coming from Last.fm have L* (e.g. 2 minutes, 13 seconds L*); you can disable showing the track duration marks (L*, S*) via **-q** / **--do_not_show_duration_marks** parameter; duration marks are not shown if the functionality to get track duration from Spotify is disabled
- **IMPROVE:** Function to search for Spotify track ID of the currently listened song (-g / --track_songs functionality) has been rewritten to also return track duration and to better detect proper song; previously sometimes wrong results were returned as we relied on the best single guess of Spotify; in this version we narrowed down the filters (specific artist, track, album) + we perform deterministic case insensitive search for the best fitting track out of the 5 search results, first by doing exact track name comparison and if it fails also sub-string one; once it fails we perform the search again without album name, so we do 4 different attempts to find the proper track
- **NEW:** Possibility to define SP_DC_COOKIE via command line argument (**-z** / **--spotify_dc_cookie**)
- **NEW:** The tool now counts and displays number of times the user paused music in the session, it is also included in email notifications
- **IMPROVE:** Fine-tuned different parameters and thresholds for detecting skipped songs and those played longer than its track duration

**Bug fixes**:

- **BUGFIX:** Spotify track ID was not returned for track names containing single apostrophe characters

# Changes in 1.3 (08 May 2024)

**Features and Improvements**:

- **NEW:** Possibility to define LASTFM_API_KEY via command line argument (-u / --lastfm_api_key)
- **NEW:** Possibility to define LASTFM_API_SECRET via command line argument (-w / --lastfm_shared_secret)
- **IMPROVE:** The artist and track are included in notification emails when informing how long the previous track was played
- **IMPROVE:** Email sending function send_email() has been rewritten to detect invalid SMTP settings
- **IMPROVE:** Strings have been converted to f-strings for better code visibility
- **IMPROVE:** Info about CSV file name in the start screen
- **IMPROVE:** Better calculations for how long the user played the previous track
- **IMPROVE:** Corrected HTML formatting for some notification emails

**Bug fixes**:

- **BUGFIX:** If user played only one track its "played for" time was always greater by LASTFM_ACTIVE_CHECK_INTERVAL than overall playing time

# Changes in 1.2 (30 Apr 2024)

**Features and Improvements**:

- **NEW:** Support for detection of songs listened on loop; if user plays the same song consecutively SONG_ON_LOOP_VALUE times (3 by default, configurable in the .py file) then there will be proper message on the console + you can get email notification (new -x / --song_on_loop_notification parameter); the alarm is triggered only once, when the SONG_ON_LOOP_VALUE is reached and once the user changes the song the timer is zeroed
- **IMPROVE:** Information about how long the user played the last song (after getting offline) is now put into the console & inactive email notification
- **IMPROVE:** More accurate calculations of how long the user played the song
- **IMPROVE:** Code related to string concatenation has been cleaned up

**Bug fixes**:

- **BUGFIX:** Fix for missing last track duration in inactive email notification
- **BUGFIX:** Fix for displaying wrong "played for" information in loop song email notifications

# Changes in 1.1 (25 Apr 2024)

**Features and Improvements**:

- **IMPROVE:** Better way of handling situations where historical Last.fm entries are not in sync and behind few songs; it happens very rarely, but it results in interpreting the current song as skipped and played on loop
- **IMPROVE:** Detection of wrongly set SP_DC_COOKIE variable (empty or default value) - it will prevent track_songs functionality (-g) from kicking in

# Changes in 1.0 (22 Apr 2024)

**Features and Improvements**:

- **NEW:** Support for showing how long user played the song and if it has been skipped
- **NEW:** Support for detecting if user listened for the song longer than its duration (for example due to seeking through it)
- **NEW:** Support for showing if user paused/resumed playback
- **NEW:** Support for detecting new tracks when user is offline
- **NEW:** Support for detecting Spotify private mode (not 100% accurate)
- **NEW:** Support for basic statistics for user's playing session (how many listened and skipped songs)
- **IMPROVE:** Additional search/replace strings to sanitize tracks for Genius URLs

**Bug fixes**:

- **BUGFIX:** Fix for "Object of type Track is not JSON serializable" error in some cases
