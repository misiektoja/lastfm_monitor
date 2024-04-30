# lastfm_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.2 (30 Apr 2024)

**Features and Improvements**:

- New feature to detect songs listened on loop; if user plays the same song consecutively SONG_ON_LOOP_VALUE times (3 by default, configurable in the .py file) then there will be proper message on the console + you can get email notification (new -x / --song_on_loop_notification parameter); the alarm is triggered only once, when the SONG_ON_LOOP_VALUE is reached and once the user changes the song the timer is zeroed
- Information about how long the user played the last song (after getting offline) is now put into the console & inactive email notification
- Code related to string concatenation has been cleaned up

**Bugfixes**:

- Fix for missing last track duration in inactive email notification

# Changes in 1.1 (25 Apr 2024)

**Features and Improvements**:

- Better way of handling situations where historical Last.fm entries are not in sync and behind few songs; it happens very rarely, but it results in intepreting the current song as skipped and played on loop
- Detection of wrongly set SP_DC_COOKIE variable (empty or default value) - it will prevent track_songs functionality (-g) from kicking in

# Changes in 1.0 (22 Apr 2024)

**Features and Improvements**:

- Support for showing how long user played the song and if it has been skipped
- Support for detecting if user listened for the song longer than its duration (for example due to seeking through it)
- Support for showing if user paused/resumed playback
- Support for detecting new tracks when user is offline
- Support for detecting Spotify private mode (not 100% accurate)
- Support for basic statistics for user's playing session (how many listened and skipped songs)
- Additional search/replace strings to sanitize tracks for Genius URLs

**Bugfixes**:

- Fix for "Object of type Track is not JSON serializable" error in some cases
