# lastfm_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 2.7 (TBD)

Version **2.7** adds **Last.fm profile change tracking** for the public display name and About Me bio. The documentation now lives on its **own searchable website** instead of one long README. It also clarifies **ntfy webhook customization**. Release downloads are now verifiable, the repository can be cited directly from its GitHub page and an automated defect check runs on every change. **Configuration files are now read as data instead of executed**, so a configuration file sitting in the working directory can no longer run code. **Secrets exported as environment variables now work without a dotenv file** and take precedence over one. **Follower and following alert emails list each changed user on its own line** again. The project itself gains a published security policy with private vulnerability reporting, guided issue and pull request templates, contribution and dependency licensing documentation plus a PyPI release that cannot publish until the full test suite passes.

**Features and improvements**:

- **NEW:** **Profile change tracking** - Track the editable **About You** text shown publicly as **About Me** with `TRACK_BIO` or `--track-bio`. Track the public **display name** with `TRACK_DISPLAY_NAME` or `--track-display-name`. Both fields use the existing `FRIENDS_CHECK_INTERVAL` timer plus the same consecutive confirmation and retry controls as follower or following changes. Confirmed values persist in `lastfm_<username>_profile.json` across restarts. Console output is automatic while `PROFILE_NOTIFICATION` / `--notify-profile` and `WEBHOOK_PROFILE_NOTIFICATION` / `--webhook-profile` control email or webhook delivery. The startup screen wraps the shared timer settings into aligned rows so profile tracking controls remain clear next to the independent notification rows
- **IMPROVE:** **Published security and contribution policies** - A **security policy** documents private vulnerability reporting through GitHub advisories, the supported versions and what a report must never contain, including how the tool loads its configuration file. New **issue forms** route suspected vulnerabilities away from public issues and collect the version, install method and affected area up front, while a **pull request template**, **contribution guidance**, a **code of conduct** and a **third-party dependency licensing notice** describe the development setup, the checks CI enforces and the license of every declared dependency. A **test suite guide** maps every test file to the area it covers
- **IMPROVE:** **Gated and verifiable release automation** - **The offline test suite now runs in CI** on every push and pull request across Python 3.9 through 3.14, alongside the linter that already ran, and **publishing to PyPI now runs that suite first and stops if it fails**, so no untested build is released under the project's name. Every workflow now **pins third-party actions to a commit SHA** with the released version recorded alongside it, so a moved tag cannot change what runs in the jobs that hold publishing credentials, and the release tag reaches the archive script through the environment instead of being pasted into a shell. **CodeQL** analyzes the source with GitHub's `security-extended` queries, **OpenSSF Scorecard** rates the project's security practices and a **supply chain workflow** audits dependencies, publishes a CycloneDX SBOM and scans commit history for leaked credentials. New contract tests fail the build if any of this regresses
- **NEW:** **TLS verification switch** - The new **`VERIFY_SSL`** setting controls certificate verification for **every** connection the tool makes: Last.fm, the Spotify metadata backends, webhook delivery, the mail server handshake and the startup connectivity check. It defaults to `True`. Set it to `False` on a network that intercepts TLS with its own certificate authority, where verification would otherwise fail with an error that reads like a bug in the tool. While it is off the tool says so at startup, since an intercepted connection cannot be told apart from the real service
- **IMPROVE:** **Clearer message on an unsupported Python** - Starting the tool on a Python older than **3.9** now names the version it found and links the installation page, instead of only stating the requirement
- **IMPROVE:** **`--debug` says where each secret came from** - Every secret now reports the source that supplied its effective value: the configuration file, the dotenv file, an exported environment variable or a command-line argument. **A value passed on the command line is identified as such**, which matters because it is visible in `ps` output and shell history while a configuration file is not. The trace names the secret and its source, never the value, and includes a length only for the secrets whose length the provider issues. A secret still holding its `your_...` placeholder counts as unset. The documentation now states which source wins when the same secret is set in more than one place
- **IMPROVE:** **Secrets stay out of error output** - Error text and log lines now have configured secrets removed along with the shapes that carry them: a `SETTING = value` line for any secret setting, `Authorization: Bearer` and `Authorization: Basic` headers, signed Last.fm request parameters such as `api_key` and `api_sig`, and Discord webhook URLs. This matters most for a **configuration file that fails to parse**, which quotes the offending line back to you and could previously print a password with it. A configured value shorter than 12 characters is redacted only in those shapes, so a short password that is also an ordinary word no longer corrupts unrelated output
- **IMPROVE:** **Failures say what to do next** - When the tool cannot continue it now reports the failure in one consistent form: what went wrong, a **`To fix:`** line with the concrete next step and a **`Guide:`** link to the page that covers it. Last.fm answers HTTP 200 with a numeric error code in the body, so the tool now reads that code instead of guessing from the text: a hidden listening history, a rejected or suspended API key, a wrong shared secret, an unknown user, a rate limit and a Last.fm outage are each named and told apart. Failures that clear on their own say the tool keeps retrying. The same form covers the configuration file, the `--set-*` commands, the connectivity check, email and webhook delivery, and the files the tool reads and writes. Pass `--debug` to add the technical cause under the fix. **Every command in a fix is written for the way you installed the tool**, `lastfm_monitor ...` or `python3 lastfm_monitor.py ...`, and repeats the `--config-file` and `--env-file` this run was given so pasting it checks the same setup. Set `LASTFM_MONITOR_INSTALL_METHOD` to `pip` or `manual` if a wrapper makes that detection wrong
- **IMPROVE:** **Documentation website** - The documentation is now published at [misiektoja.github.io/lastfm_monitor](https://misiektoja.github.io/lastfm_monitor/) as a searchable site with a page per topic: installation, setup and first run, configuration, usage, troubleshooting, testing and about. The README becomes a landing page with the feature list and a map of the pages. A new **Troubleshooting** page collects what to check when a run does not start, including the privacy setting the monitored account has to change, and explains what `--debug` traces. The tool now points at these pages where it can help: `--help` ends with a link to the site, the `--set-lastfm-credentials`, `--set-spotify-credentials` and `--set-webhook-url` prompts show where to create each credential before asking for it, and a missing dependency names the installation page. The site build runs in CI on every change and fails on a broken link or a missing page
- **IMPROVE:** **Clearer ntfy webhook customization** - Documentation and the generated configuration now state that `WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` apply only to Discord and are ignored by ntfy, which needs no template. Customize ntfy delivery through `WEBHOOK_HEADERS` such as `X-Priority` or `X-Tags`
- **IMPROVE:** **Verifiable release downloads** - Each published release now attaches a **`SHA256SUMS.txt`** file next to the `zip` and `tar.gz` archives, and both archives carry a signed build provenance attestation. The attestation bundle is attached too, as an **`.intoto.jsonl`** asset, so provenance can be checked from the downloaded files alone. You can confirm a download really came from this repository before you unpack it with `gh attestation verify lastfm_monitor_<tag>.zip --repo misiektoja/lastfm_monitor`
- **IMPROVE:** **Automated defect checks on every change** - A pinned [Ruff](https://docs.astral.sh/ruff/) lint pass now runs in CI on every change, reporting unused names, undefined names and common bug patterns. Added optional pre-commit hooks and a shared [.editorconfig](https://github.com/misiektoja/lastfm_monitor/blob/main/.editorconfig) that records the project's existing style
- **IMPROVE:** **Cite the project and find help faster** - The repository page now offers **Cite this repository**, which exports a ready-made BibTeX or APA entry from the new [CITATION.cff](https://github.com/misiektoja/lastfm_monitor/blob/main/CITATION.cff). The new [SUPPORT.md](https://github.com/misiektoja/lastfm_monitor/blob/main/SUPPORT.md) shows where a question, a bug report and a vulnerability each belong and what to include

**Bug fixes**:

- **BUGFIX:** **An unusable webhook URL switches the channel off once** - With `WEBHOOK_ENABLED = True` and a `WEBHOOK_URL` that is not a complete HTTPS link, the tool used to print a delivery error on every single alert for the rest of the run. It now says so once at startup and turns webhook alerts off
- **BUGFIX:** **`--debug` covers the configuration file load** - The flag was applied after the configuration file had already been read, so nothing that happened during the load was traced. It is now applied as soon as the arguments are parsed and applied again afterwards, so a saved `DEBUG_MODE = False` still cannot override the flag
- **BUGFIX:** **Connectivity check settings are read from the configuration file** - `CHECK_INTERNET_URL` and `CHECK_INTERNET_TIMEOUT` were frozen at their shipped values, so changing either in a configuration file had no effect and the startup check always used the default Last.fm endpoint and a 5 second timeout. Both are now read when the check runs
- **BUGFIX:** **Exported secrets work without a dotenv file and take precedence over one** - Secrets exported as environment variables, such as `LASTFM_API_KEY`, `LASTFM_API_SECRET`, `SP_CLIENT_ID`, `SP_CLIENT_SECRET`, `SMTP_PASSWORD`, `WEBHOOK_URL` or `NTFY_ACCESS_TOKEN`, were applied only when a dotenv file also existed, so an export-only setup silently fell back to the shipped defaults. They are now honored on their own, including with `--env-file none`. An exported value also wins over the same key in the dotenv file, matching how `python-dotenv` and container or service-manager setups already behave. Reloading with **`SIGHUP`** still applies the edited dotenv file, so rotating a secret there keeps working
- **BUGFIX:** **Readable follower and following alert emails** - Emails reporting **follower and following changes** now put every added or removed user on its own line. Previously the HTML email ran the names together, so `- Angie_Sullivan- HakikazuHatsu` arrived as one line. Each name still links to its Last.fm profile, and the plain text email and webhook messages are unchanged because they were already correct

# Changes in 2.6.2 (04 Aug 2026)

**Bug fixes**:

- **BUGFIX:** **Webhook deliveries refuse redirects** - Every Discord and ntfy delivery now takes one shared request path that **refuses redirects**, so a webhook address that redirects can no longer hand your alert and its headers to another host. The destination is rechecked at delivery time, so a `WEBHOOK_URL` replaced through a dotenv reload cannot be posted to unchecked
- **BUGFIX:** **Declarative configuration files** - Configuration files are now **read as data instead of being executed as Python**. Previously the tool ran the first configuration it found in the current working directory, so starting it in a directory someone else could write to would run their code. Only documented `SETTING = value` lines with plain literal values are accepted, plus a setting that reuses another setting, and imports, function calls, expressions or control flow are now rejected without being run. The rejected line and setting are named, and a file that fails leaves every setting at its previous value instead of applying the lines before the bad one
- **BUGFIX:** Fixed indentation of ASCII log separators in summary screen

# Changes in 2.6.1 (04 Aug 2026)

Version **2.6.1** makes saved logs easier to read consistently across platforms and prevents Windows PowerShell from creating incompatible configuration files.

**Features and improvements**:

- **IMPROVE:** **Consistent log alignment** - Tabs are expanded to spaces when saved to log files so columns stay aligned in viewers that render tabs differently. Terminal output is unchanged
- **IMPROVE:** **Portable log separators** - The new `ASCII_LOG_SEPARATORS` setting controls whether separator-only lines saved to log files use ASCII hyphens. `"Auto"` enables them on Windows by default, `"On"` enables them on every operating system and `"Off"` preserves Unicode separators. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.
- **IMPROVE:** **UTF-8 configuration generation** - `lastfm_monitor --generate-config FILENAME` now writes the template directly to the specified file as UTF-8. In Windows PowerShell, it should be used instead of output redirection to avoid UTF-16 files and `null bytes` errors

# Changes in 2.6 (30 Jul 2026)

Version **2.6** adds independent **Discord and ntfy webhook notifications**, safer **private credential setup** and clearer **per-channel notification controls**.

**Features and improvements**:

- **NEW:** Added independent **Discord and ntfy webhook notifications** with per-event controls for active, inactive, monitored-track, every-song, loop, offline-entry, follower, following and monitoring-error alerts
- **NEW:** Added private **webhook URL setup** with `--set-webhook-url`, one-run provider and URL overrides plus `--send-test-webhook` for delivery checks
- **NEW:** Added **customizable Discord-format payloads** plus native ntfy topic delivery with protected-topic authentication and compact text-only alerts through `NTFY_SHORT`
- **NEW:** Added safe **Last.fm and Spotify credential setup** through `--set-lastfm-credentials` and `--set-spotify-credentials`, with atomic owner-only dotenv writes that keep secrets out of shell history and process listings
- **IMPROVE:** Added **bounded webhook retries**, automatic provider correction and per-channel duplicate suppression while keeping email and webhook delivery independent
- **IMPROVE:** Added compact **email and webhook category rollups** with short labels while extending `SIGHUP` secret reloads to webhook destinations and ntfy access tokens

# Changes in 2.5 (21 Jul 2026)

**Features and Improvements**:

- **NEW:** Added an anonymous Spotify web-player metadata backend that supplies the track information needed for duration lookup and automatic playback. This serves as an automatic fallback following optional OAuth app metadata.
- **NEW:** Added Spotify server-time retrieval and shipped the stable v61 TOTP cipher bytes for anonymous token generation, exposed as the `SPOTIFY_TOTP_VERSION` and `SPOTIFY_TOTP_SECRET_CIPHER_BYTES` config options so a future Spotify rotation can be patched from the config file without a code release

**Bug fixes**:

- **BUGFIX:** Restored Spotify track IDs and duration lookup without relying on Web API endpoints affected by Development Mode restrictions
- **BUGFIX:** Removed the restricted category request that falsely rejected otherwise valid OAuth app tokens
- **BUGFIX:** Matched localized Spotify artist aliases when the track title and album are exact matches

# Changes in 2.4.4 (05 May 2026)

**Features and Improvements**:

- **IMPROVE:** Hardened followers and followings scraping to avoid silent empty returns by adding retry and backoff plus structural parsing validation against Last.fm header counts

**Bug fixes**:

- **BUGFIX:** Prevented follower and following state corruption by persisting exactly the already-scraped sets instead of re-scraping during confirmation and baseline updates

# Changes in 2.4.3 (06 Feb 2026)

**Features and Improvements**:

- **IMPROVE:** Enhanced display of album information in notifications and outputs when album info is missing

# Changes in 2.4.2 (13 Jan 2026)

**Features and Improvements**:

- **IMPROVE:** Enhanced **Spotify track search logic** with improved matching to address recent Spotify API changes
- **NEW:** Implemented **Debug Mode** (`--debug` flag or `DEBUG_MODE` config option) - provides full technical logging and internal state changes

# Changes in 2.4.1 (12 Jan 2026)

**Features and Improvements**:

- **NEW:** Implement **consecutive checks** for confirming friend changes to **reduce false notifications** (configurable via `FRIENDS_CHANGE_COUNTER` and `FRIENDS_RETRY_INTERVAL`)
- **IMPROVE:** **Suppress repetitive error messages** for followers/followings tracking during transient outages
- **IMPROVE:** Better mechanism for scraping followers and followings

**Bug fixes**:

- **BUGFIX:** Ensure href and class attributes are properly validated during web scraping

# Changes in 2.4 (04 Jan 2026)

**Features and Improvements**:

- **NEW:** Added support for **tracking changes** in Last.fm user's **followers** and **followings** with console and email notifications (see `TRACK_FOLLOWINGS` / `--track-followings` and `TRACK_FOLLOWERS` / `--track-followers`)
- **NEW:** Added **Last.fm Wrapped tool** for generating Spotify Wrapped-style statistics (top artists, tracks, albums) from CSV data
- **NEW:** Separate check intervals for followers/followings tracking (independent from music polling intervals, see `FRIENDS_CHECK_INTERVAL` config option and `--friends-check-interval` flag)
- **NEW:** **Persistent state storage** in JSON files (`lastfm_{username}_followings.json` and `lastfm_{username}_followers.json`) to **track changes across restarts**
- **NEW:** **Web scraping implementation** for retrieving followers and followings (Last.fm API doesn't provide direct endpoints)
- **NEW:** Added **clickable Last.fm profile links** for added/removed users

**Dependencies**:

- **NEW:** Added **beautifulsoup4** dependency for **followers/followings tracking** functionality

# Changes in 2.3 (11 Nov 2025)

**Features and Improvements**:

- **NEW:** Added support for **Amazon Music**, **Deezer** and **Tidal** URLs in console and email outputs
- **NEW:** Added support for **AZLyrics**, **Tekstowo.pl**, **Musixmatch** and **Lyrics.com** lyrics services
- **NEW:** Added Last.fm track and album URLs in email notifications and console output
- **NEW:** Added configuration options to enable/disable music service URLs in console and email outputs (see `ENABLE_SPOTIFY_URL`, `ENABLE_LASTFM_URL`, `ENABLE_LASTFM_ALBUM_URL`, `ENABLE_APPLE_MUSIC_URL`, `ENABLE_YOUTUBE_MUSIC_URL`, `ENABLE_AMAZON_MUSIC_URL`, `ENABLE_DEEZER_URL` and `ENABLE_TIDAL_URL` config options)
- **NEW:** Added configuration options to enable/disable lyrics service URLs in console and email outputs (see `ENABLE_GENIUS_LYRICS_URL`, `ENABLE_AZLYRICS_URL`, `ENABLE_TEKSTOWO_URL`, `ENABLE_MUSIXMATCH_URL` and `ENABLE_LYRICS_COM_URL` config options)
- **NEW:** Added songs played count and session duration to email notifications and console output
- **NEW:** Added recent songs tracking in session with inclusion in inactivity emails, including skipped and continued track status (see `INACTIVE_EMAIL_RECENT_SONGS_COUNT` config option)
- **NEW:** Added support for user activity tracking for fresh Last.fm accounts with no tracks yet
- **NEW:** Added configurable option to use Last.fm or Spotify URL in "Last played:" / "Track:" field in HTML email notifications (see `USE_LASTFM_URL_IN_LAST_PLAYED` config option, defaults to True)
- **IMPROVE:** Redesigned track listing output (`-l` flag) to display tracks in a formatted table with proper column alignment
- **IMPROVE:** Standardized User-Agent header construction and added it to Spotify API requests and internet connectivity checks
- **IMPROVE:** Updated print statements and email body to consistently use "Spotify URL" instead of "Spotify search URL"

**Bug fixes**:

- **BUGFIX:** Prevented duplicate emails when songs on loop also match track/song alerts
- **BUGFIX:** Fixed missing album information handling by using default empty string

# Changes in 2.2 (18 Jun 2025)

**Features and Improvements**:

- **NEW:** Added display of last played track duration at startup when user is offline
- **NEW:** Added option to customize the path for OAuth app access token cache file with possibility to use in-memory only cache
- **IMPROVE:** Restored old SP_CLIENT_ID:SP_CLIENT_SECRET format for -z / --spotify-creds flag (more reliable in corner cases)
- **IMPROVE:** Updated captions shown for Apple and YouTube Music links

**Bug fixes**:

- **BUGFIX:** Added exception handling when retrieving Spotify access tokens to prevent crashes
- **BUGFIX:** Coerced artist, track and album to strings before sanitization

# Changes in 2.1.1 (13 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Fixed config file generation to work reliably on Windows systems

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
