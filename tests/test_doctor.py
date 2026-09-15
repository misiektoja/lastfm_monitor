"""The --doctor preflight: the row contract, every failure branch, the section order and the verdict."""

import inspect
import re
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")

REAL_KEY = "lastfmapikey00000000000000000000"


# Returns a report holding the given checks, so a renderer can be driven without running any check
def report_of(*checks):
    report = monitor.DoctorReport()
    report.checks.extend(checks)
    return report


# Builds one check without going through a section function
def check(section="Environment", status="PASS", label="A label", detail="", advice=None):
    return monitor.make_doctor_check(section, status, label, detail, advice)


def fix_advice(summary="Something broke", fix="Do the thing"):
    return monitor.make_recovery_advice("config.invalid", summary, fix, False)


@pytest.fixture
def quiet_config(monkeypatch):
    """Leaves every optional feature off so a section renders only the rows under test."""
    for name, value in (
        ("DISABLE_LOGGING", True), ("CSV_FILE", ""), ("MONITOR_LIST_FILE", ""), ("VERIFY_SSL", True),
        ("TRACK_SONGS", False), ("USE_TRACK_DURATION_FROM_SPOTIFY", False),
        ("TRACK_FOLLOWINGS", False), ("TRACK_FOLLOWERS", False), ("TRACK_BIO", False), ("TRACK_DISPLAY_NAME", False),
        ("LASTFM_CHECK_INTERVAL", 10), ("LASTFM_ACTIVE_CHECK_INTERVAL", 5), ("LASTFM_INACTIVITY_CHECK", 180),
        ("CHECK_INTERNET_TIMEOUT", 5), ("LIVENESS_CHECK_INTERVAL", 43200), ("LASTFM_BREAK_CHECK_MULTIPLIER", 4),
        ("FRIENDS_CHECK_INTERVAL", 900), ("FRIENDS_RETRY_INTERVAL", 90), ("SMTP_PORT", 587),
    ):
        monkeypatch.setattr(monitor, name, value)


class TestTheRowConstructor:
    def test_a_marker_outside_the_four_is_refused(self):
        with pytest.raises(ValueError):
            monitor.make_doctor_check("Environment", "INFO", "A label")

    @pytest.mark.parametrize("status", monitor.DOCTOR_STATUSES)
    def test_all_four_markers_are_accepted(self, status):
        advice = fix_advice() if status in ("WARN", "FAIL") else None
        assert monitor.make_doctor_check("Environment", status, "A label", advice=advice).status == status

    # A row the user has to act on without an action is a defect that should fail a test rather than a user
    @pytest.mark.parametrize("status", ["WARN", "FAIL"])
    def test_a_row_that_needs_an_action_cannot_be_built_without_one(self, status):
        with pytest.raises(ValueError):
            monitor.make_doctor_check("Environment", status, "A label", "A detail")
        with pytest.raises(ValueError):
            monitor.make_doctor_check("Environment", status, "A label", "A detail", monitor.make_recovery_advice("config.invalid", "s", "", False))

    # Several advice objects carry their summary as the detail and printing it twice reads as two problems
    def test_a_detail_that_repeats_its_label_is_dropped(self):
        assert check(label="Same text", detail=" Same text ").detail == ""

    def test_the_detail_is_sanitized(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        assert REAL_KEY not in check(detail=f"key {REAL_KEY} leaked").detail


class TestTheEnvironmentSection:
    def test_the_python_row_carries_the_same_floor_the_startup_gate_reads(self, quiet_config):
        row = monitor.doctor_check_environment()[0]
        assert row.status == "PASS"
        assert row.detail == f"Minimum supported version: {monitor.MINIMUM_PYTHON_VERSION_TEXT}"

    def test_an_unsupported_python_fails_and_still_names_the_floor(self, quiet_config):
        row = monitor.doctor_check_environment(version_info=(3, 8, 10))[0]
        assert row.status == "FAIL"
        assert monitor.MINIMUM_PYTHON_VERSION_TEXT in row.detail
        assert row.advice.fix.startswith(f"Install Python {monitor.MINIMUM_PYTHON_VERSION_TEXT} or newer")

    def test_a_missing_required_dependency_fails(self, quiet_config):
        rows = monitor.doctor_check_environment(spec_finder=lambda name: None if name == "pylast" else object())
        failed = [row for row in rows if row.status == "FAIL"]
        assert [row.label for row in failed] == ["Required dependency pylast is missing"]

    # A bare pip may belong to another interpreter than the one running this tool
    def test_the_install_command_names_this_interpreter(self, quiet_config):
        rows = monitor.doctor_check_environment(spec_finder=lambda name: None if name == "pylast" else object())
        assert monitor.sys.executable in rows[1].advice.fix
        assert "Install it with: " in rows[1].advice.fix

    # A missing optional dependency costs one feature, which the loop still starts without
    @pytest.mark.parametrize("module_name, package_name", [("dotenv", "python-dotenv"), ("spotipy", "spotipy"), ("bs4", "beautifulsoup4"), ("wcwidth", "wcwidth")])
    def test_a_missing_optional_dependency_warns_and_says_what_is_unaffected(self, quiet_config, module_name, package_name):
        rows = monitor.doctor_check_environment(spec_finder=lambda name: None if name == module_name else object())
        warned = [row for row in rows if row.status == "WARN"]
        assert [row.label for row in warned] == [f"Optional dependency {package_name} is not installed"]
        assert warned[0].detail.endswith("Every other feature is unaffected")

    def test_an_unimportable_parent_counts_as_absent(self, quiet_config):
        def raising_finder(name):
            if name == "bs4":
                raise ValueError("no parent package")
            return object()

        rows = monitor.doctor_check_environment(spec_finder=raising_finder)
        assert any(row.status == "WARN" and "beautifulsoup4" in row.label for row in rows)


class TestTheConfigurationSection:
    def test_the_files_in_effect_are_reported(self, quiet_config, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("", encoding="utf-8")
        rows = monitor.doctor_check_configuration(config_path="/etc/lastfm.conf", env_path=str(env_file))
        assert rows[0].label == "Configuration file loaded"
        assert rows[1].label == "Dotenv file loaded"

    # A file the user selected and the tool could not find is never a pass, and never a failure either
    def test_a_selected_dotenv_that_is_missing_warns(self, quiet_config, tmp_path):
        rows = monitor.doctor_check_configuration(env_path=str(tmp_path / "missing.env"))
        missing = [row for row in rows if row.label == "The requested dotenv file was not found"]
        assert [row.status for row in missing] == ["WARN"]
        assert missing[0].advice.fix.startswith("Create the file or select an existing path with --env-file")

    def test_nothing_selected_is_reported_as_defaults(self, quiet_config):
        rows = monitor.doctor_check_configuration()
        assert rows[0].label == "No configuration file selected"
        assert rows[1].label == "No dotenv file selected"

    def test_no_secret_anywhere_gets_the_full_list(self, quiet_config, monkeypatch):
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
        row = [row for row in monitor.doctor_check_configuration() if row.label == "No secrets loaded"][0]
        assert row.detail == "Nothing was read from a dotenv file, the environment, the configuration file or the command line"

    # Every tool spells the source the same way, since the reports are read side by side
    def test_each_source_gets_its_own_row_under_the_shared_name(self, quiet_config, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        monkeypatch.setattr(monitor, "SMTP_PASSWORD", "a-real-password")
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {"LASTFM_API_KEY": "config file", "SMTP_PASSWORD": "command line"})
        labels = [row.label for row in monitor.doctor_check_configuration()]
        assert "Secrets loaded from the configuration file" in labels
        assert "Secrets loaded from the command line" in labels

    def test_verification_left_on_takes_a_passing_row(self, quiet_config):
        assert [row.status for row in monitor.doctor_check_configuration() if "TLS certificate verification" in row.label] == ["PASS"]

    def test_verification_switched_off_warns(self, quiet_config, monkeypatch):
        monkeypatch.setattr(monitor, "VERIFY_SSL", False)
        row = [row for row in monitor.doctor_check_configuration() if "TLS certificate verification" in row.label][0]
        assert row.status == "WARN"
        assert "intercepted connection" in row.detail

    # A setting that is merely valid is not a result, so it takes no row
    def test_a_valid_interval_takes_no_row(self, quiet_config):
        labels = " ".join(row.label for row in monitor.doctor_check_configuration())
        assert "LASTFM_CHECK_INTERVAL" not in labels

    @pytest.mark.parametrize("name, value", [("LASTFM_CHECK_INTERVAL", 0), ("LASTFM_ACTIVE_CHECK_INTERVAL", -1), ("LIVENESS_CHECK_INTERVAL", -5), ("SMTP_PORT", 70000), ("CHECK_INTERNET_TIMEOUT", "five")])
    def test_an_invalid_number_is_still_a_failure(self, quiet_config, monkeypatch, name, value):
        monkeypatch.setattr(monitor, name, value)
        row = [row for row in monitor.doctor_check_configuration() if row.status == "FAIL"][0]
        assert name in row.detail

    def test_a_true_flag_is_not_mistaken_for_a_number(self, quiet_config, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_CHECK_INTERVAL", True)
        assert any("LASTFM_CHECK_INTERVAL" in error for error in monitor.runtime_configuration_errors())


class TestTheOutputDestinationRows:
    def test_a_writable_destination_passes_and_names_the_path(self, quiet_config, monkeypatch, tmp_path):
        monkeypatch.setattr(monitor, "CSV_FILE", str(tmp_path / "scrobbles.csv"))
        row = [row for row in monitor.doctor_output_destination_checks("someuser") if "CSV destination" in row.label][0]
        assert row.status == "PASS"
        assert row.detail == f"Path: {tmp_path / 'scrobbles.csv'}"

    def test_a_destination_that_cannot_be_created_fails(self, quiet_config, monkeypatch):
        monkeypatch.setattr(monitor, "CSV_FILE", "/proc/definitely/not/here/out.csv")
        assert [row.status for row in monitor.doctor_output_destination_checks("someuser") if row.status == "FAIL"] == ["FAIL"]

    def test_switched_off_outputs_say_so(self, quiet_config):
        labels = [row.label for row in monitor.doctor_output_destination_checks("someuser")]
        assert "Output logging is disabled" in labels
        assert "CSV logging is disabled" in labels

    # The log and status names carry the username, so without one there is no path to judge yet
    def test_the_target_derived_paths_wait_for_a_username(self, quiet_config, monkeypatch):
        monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
        monkeypatch.setattr(monitor, "LF_LOGFILE", "lastfm_monitor")
        labels = [row.label for row in monitor.doctor_output_destination_checks()]
        assert "Log destination will be finalized after a username is selected" in labels
        assert "Status file will be finalized after a username is selected" in labels

    def test_a_username_resolves_the_log_name_monitoring_will_write(self, quiet_config, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
        monkeypatch.setattr(monitor, "LF_LOGFILE", "lastfm_monitor")
        row = [row for row in monitor.doctor_output_destination_checks("someuser") if "Log destination" in row.label][0]
        assert row.detail.endswith("lastfm_monitor_someuser.log")

    # The profile state file only exists while a tracking switch is on, so a run that never writes it takes no row
    def test_the_profile_state_row_appears_only_with_tracking_on(self, quiet_config, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        assert not any("Profile state destination" in row.label for row in monitor.doctor_output_destination_checks("someuser"))
        monkeypatch.setattr(monitor, "TRACK_BIO", True)
        assert any("Profile state destination" in row.label for row in monitor.doctor_output_destination_checks("someuser"))

    def test_a_monitored_tracks_file_that_cannot_be_read_fails(self, quiet_config, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(monitor, "MONITOR_LIST_FILE", str(tmp_path / "absent.txt"))
        rows = [row for row in monitor.doctor_output_destination_checks("someuser") if row.status == "FAIL"]
        assert [row.advice.code for row in rows] == ["file.unreadable"]
        assert "absent.txt" in rows[0].label

    def test_a_readable_monitored_tracks_file_passes(self, quiet_config, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        listed = tmp_path / "tracks.txt"
        listed.write_text("Artist - Track\n", encoding="utf-8")
        monkeypatch.setattr(monitor, "MONITOR_LIST_FILE", str(listed))
        assert [row.status for row in monitor.doctor_output_destination_checks("someuser") if "Monitored tracks" in row.label] == ["PASS"]


class TestTheConnectivitySection:
    # The row checks the endpoint startup gates on, not an authenticated service call
    def test_the_reachable_endpoint_row_names_the_configured_url(self, monkeypatch):
        monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://example.invalid/probe")
        monkeypatch.setattr(monitor, "check_internet", lambda **kwargs: True)
        row = monitor.doctor_check_connectivity()[0]
        assert row.status == "PASS"
        assert row.detail == "Endpoint: https://example.invalid/probe"

    def test_an_unreachable_endpoint_fails_with_a_classified_cause(self, monkeypatch):
        monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://example.invalid/probe")

        def failing_check(**kwargs):
            monitor.LAST_CONNECTIVITY_ERROR = monitor.req.RequestException("connection timed out")
            return False

        monkeypatch.setattr(monitor, "check_internet", failing_check)
        row = monitor.doctor_check_connectivity()[0]
        assert row.status == "FAIL"
        assert row.advice.code == "network.timeout"

    # A check written to test one specific thing already knows why it failed
    def test_the_failure_never_ends_at_re_run_with_debug(self, monkeypatch):
        monkeypatch.setattr(monitor, "check_internet", lambda **kwargs: False)
        row = monitor.doctor_check_connectivity()[0]
        assert row.advice.code != "unknown"
        assert "--debug" not in row.advice.fix


class TestTheAuthenticationSection:
    def test_a_missing_credential_is_named_on_its_own(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", "your_lastfm_api_secret")
        row = monitor.doctor_check_authentication(monitor.DoctorReport())[0]
        assert row.status == "FAIL"
        assert row.detail == "LASTFM_API_SECRET is empty or still set to its placeholder"

    def test_both_missing_credentials_are_named_together(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "")
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", "")
        row = monitor.doctor_check_authentication(monitor.DoctorReport())[0]
        assert row.detail == "LASTFM_API_KEY or LASTFM_API_SECRET is empty or still set to its placeholder"

    # Checking that the values are non-empty proves nothing, so the row is decided by a real API call
    def test_a_rejected_key_fails_where_the_real_call_fails(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", REAL_KEY)

        class RejectingNetwork:
            def __init__(self, *args):
                pass

            def get_top_artists(self, limit=None):
                raise Exception("Invalid API key - You must be granted a valid key by last.fm")

        monkeypatch.setattr(monitor.pylast, "LastFMNetwork", RejectingNetwork)
        report = monitor.DoctorReport()
        row = monitor.doctor_check_authentication(report)[0]
        assert row.status == "FAIL"
        assert row.advice.code == "auth.api_key_invalid"
        assert report.network is None

    def test_an_accepted_key_passes_without_showing_it(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", REAL_KEY)

        class WorkingNetwork:
            def __init__(self, *args):
                pass

            def get_top_artists(self, limit=None):
                return []

        monkeypatch.setattr(monitor.pylast, "LastFMNetwork", WorkingNetwork)
        report = monitor.DoctorReport()
        row = monitor.doctor_check_authentication(report)[0]
        assert row.status == "PASS"
        assert REAL_KEY not in f"{row.label} {row.detail}"
        assert report.network is not None


class TestTheSpotifyMetadataSection:
    def test_no_section_while_nothing_needs_spotify(self, quiet_config):
        assert monitor.doctor_check_spotify_metadata(monitor.DoctorReport()) == []

    def test_the_anonymous_backend_needs_no_credentials(self, quiet_config, monkeypatch):
        monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", True)
        monkeypatch.setattr(monitor, "SP_CLIENT_ID", "")
        rows = monitor.doctor_check_spotify_metadata(monitor.DoctorReport())
        assert [row.status for row in rows] == ["PASS"]
        assert "anonymous Spotify web player" in rows[0].label

    # The OAuth app is optional, so credentials it refuses leave the run working on the other backend
    def test_refused_oauth_credentials_warn_rather_than_fail(self, quiet_config, monkeypatch):
        monkeypatch.setattr(monitor, "TRACK_SONGS", True)
        monkeypatch.setattr(monitor, "SP_CLIENT_ID", "abc123abc123abc123abc123abc123ab")
        monkeypatch.setattr(monitor, "SP_CLIENT_SECRET", "def456def456def456def456def456de")
        monkeypatch.setattr(monitor, "SP_TOKENS_FILE", "")
        monkeypatch.setattr(monitor, "spotify_get_access_token", lambda *args: (_ for _ in ()).throw(RuntimeError("invalid_client")))
        rows = monitor.doctor_check_spotify_metadata(monitor.DoctorReport())
        assert rows[0].status == "WARN"
        assert "falls back to the anonymous Spotify web player" in rows[0].detail

    def test_accepted_oauth_credentials_name_the_backend_order(self, quiet_config, monkeypatch):
        monkeypatch.setattr(monitor, "TRACK_SONGS", True)
        monkeypatch.setattr(monitor, "SP_CLIENT_ID", "abc123abc123abc123abc123abc123ab")
        monkeypatch.setattr(monitor, "SP_CLIENT_SECRET", "def456def456def456def456def456de")
        monkeypatch.setattr(monitor, "SP_TOKENS_FILE", "")
        monkeypatch.setattr(monitor, "spotify_get_access_token", lambda *args: "a-token")
        rows = monitor.doctor_check_spotify_metadata(monitor.DoctorReport())
        assert rows[0].status == "PASS"
        assert rows[1].label == "Spotify tokens are cached in memory only"

    # The cache belongs to the backend that writes it, not to the general output rows
    def test_the_token_cache_row_files_under_its_own_section(self, quiet_config, monkeypatch, tmp_path):
        monkeypatch.setattr(monitor, "TRACK_SONGS", True)
        monkeypatch.setattr(monitor, "SP_CLIENT_ID", "abc123abc123abc123abc123abc123ab")
        monkeypatch.setattr(monitor, "SP_CLIENT_SECRET", "def456def456def456def456def456de")
        monkeypatch.setattr(monitor, "SP_TOKENS_FILE", str(tmp_path / "tokens.json"))
        monkeypatch.setattr(monitor, "spotify_get_access_token", lambda *args: "a-token")
        rows = monitor.doctor_check_spotify_metadata(monitor.DoctorReport())
        assert [row.section for row in rows] == ["Spotify metadata", "Spotify metadata"]


class TestTheTargetSection:
    def test_no_username_warns_rather_than_fails(self):
        row = monitor.doctor_check_target(monitor.DoctorReport())[0]
        assert row.status == "WARN"
        assert row.advice.code == "target.missing"

    # One condition, one severity in every tool, since scripts read the exit code
    def test_a_target_left_unchecked_is_skipped_with_the_shared_wording(self):
        row = monitor.doctor_check_target(monitor.DoctorReport(), "someuser")[0]
        assert row.status == "SKIP"
        assert row.label == "The monitored profile was not checked"
        assert row.detail == "The Last.fm API key did not validate, so no lookup was attempted"
        assert row.advice is None

    def test_a_profile_that_cannot_be_fetched_fails(self, monkeypatch):
        report = monitor.DoctorReport()
        report.network = object()
        monkeypatch.setattr(monitor, "lastfm_get_recent_tracks", lambda *args: (_ for _ in ()).throw(Exception("User not found")))
        row = monitor.doctor_check_target(report, "someuser")[0]
        assert row.status == "FAIL"
        assert row.advice.code == "target.not_found"

    # Hidden listening history is the failure this tool sees most, and the loop cannot start from it
    def test_a_hidden_listening_history_fails_and_says_which_setting(self, monkeypatch):
        report = monitor.DoctorReport()
        report.network = object()
        monkeypatch.setattr(monitor, "lastfm_get_recent_tracks", lambda *args: (_ for _ in ()).throw(Exception("User required to be logged in")))
        row = monitor.doctor_check_target(report, "someuser")[0]
        assert row.status == "FAIL"
        assert row.advice.code == "target.not_visible"
        assert "Hide recent listening information" in row.advice.fix

    def test_a_readable_history_passes(self, monkeypatch):
        report = monitor.DoctorReport()
        report.network = type("Network", (), {"get_user": lambda self, name: name})()
        monkeypatch.setattr(monitor, "lastfm_get_recent_tracks", lambda *args: [object()])
        rows = monitor.doctor_check_target(report, "someuser")
        assert [row.status for row in rows] == ["PASS", "PASS"]
        assert rows[0].detail == "Last.fm user: someuser"

    # A fresh account is a state the loop already handles, so it is not a warning
    def test_an_account_with_no_scrobbles_still_passes(self, monkeypatch):
        report = monitor.DoctorReport()
        report.network = type("Network", (), {"get_user": lambda self, name: name})()
        monkeypatch.setattr(monitor, "lastfm_get_recent_tracks", lambda *args: [])
        rows = monitor.doctor_check_target(report, "someuser")
        assert [row.status for row in rows] == ["PASS", "PASS"]
        assert "waits for the first track" in rows[1].detail


class TestTheNotificationSection:
    @pytest.fixture(autouse=True)
    def email_off(self, monkeypatch):
        for name in ("ACTIVE_NOTIFICATION", "INACTIVE_NOTIFICATION", "TRACK_NOTIFICATION", "SONG_NOTIFICATION", "SONG_ON_LOOP_NOTIFICATION", "OFFLINE_ENTRIES_NOTIFICATION", "ERROR_NOTIFICATION", "FOLLOWERS_NOTIFICATION", "FOLLOWINGS_NOTIFICATION", "PROFILE_NOTIFICATION"):
            monkeypatch.setattr(monitor, name, False)
        for name in ("SMTP_HOST", "SENDER_EMAIL", "RECEIVER_EMAIL", "SMTP_USER", "SMTP_PASSWORD"):
            monkeypatch.setattr(monitor, name, "")

    def test_email_off_and_unconfigured_passes_without_connecting(self):
        row = monitor.doctor_check_email_notifications(monitor.DoctorReport())[0]
        assert row.status == "PASS"
        assert row.label == "Email notifications are disabled"

    # A channel switched on that cannot deliver is one warning, never a failure that changes the exit code
    def test_alerts_on_with_placeholder_settings_warn_and_name_only_what_is_unset(self, monkeypatch):
        monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
        monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.com")
        monkeypatch.setattr(monitor, "SENDER_EMAIL", "your_sender_email")
        monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "b@example.com")
        row = monitor.doctor_check_email_notifications(monitor.DoctorReport())[0]
        assert row.status == "WARN"
        assert row.label == monitor.EMAIL_UNUSABLE_CHECK_LABEL
        assert row.detail == "SENDER_EMAIL is empty or still set to its placeholder"

    def test_configured_email_with_no_alert_types_warns(self, monkeypatch):
        for name, value in (("SMTP_HOST", "smtp.example.com"), ("SENDER_EMAIL", "a@example.com"), ("RECEIVER_EMAIL", "b@example.com")):
            monkeypatch.setattr(monitor, name, value)
        row = monitor.doctor_check_email_notifications(monitor.DoctorReport())[0]
        assert row.status == "WARN"
        assert row.label == "Email is configured but no alert types are selected"

    def test_a_refused_sign_in_fails_where_a_real_send_would(self, monkeypatch):
        for name, value in (("SMTP_HOST", "smtp.example.com"), ("SENDER_EMAIL", "a@example.com"), ("RECEIVER_EMAIL", "b@example.com"), ("SMTP_USER", "someone"), ("SMTP_PASSWORD", "a-real-password")):
            monkeypatch.setattr(monitor, name, value)
        monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
        monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda *args, **kwargs: (_ for _ in ()).throw(Exception("535 authentication failed")))
        row = monitor.doctor_check_email_notifications(monitor.DoctorReport())[0]
        assert row.status == "FAIL"
        assert row.advice.code == "smtp.authentication"

    def test_a_working_sign_in_passes_and_marks_the_channel_ready(self, monkeypatch):
        for name, value in (("SMTP_HOST", "smtp.example.com"), ("SENDER_EMAIL", "a@example.com"), ("RECEIVER_EMAIL", "b@example.com"), ("SMTP_USER", "someone"), ("SMTP_PASSWORD", "a-real-password")):
            monkeypatch.setattr(monitor, name, value)
        monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
        quits = []
        monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda *args, **kwargs: type("Smtp", (), {"quit": lambda self: quits.append(True)})())
        report = monitor.DoctorReport()
        row = monitor.doctor_check_email_notifications(report)[0]
        assert row.status == "PASS"
        assert row.label == monitor.SMTP_READY_CHECK_LABEL
        assert report.email_ready is True
        assert quits == [True], "the passive check left an SMTP session open"

    # The preflight waits on a person, so it uses a shorter timeout than a delivery in the monitoring loop
    def test_the_passive_check_uses_the_preflight_timeout(self, monkeypatch):
        for name, value in (("SMTP_HOST", "smtp.example.com"), ("SENDER_EMAIL", "a@example.com"), ("RECEIVER_EMAIL", "b@example.com"), ("SMTP_USER", "someone"), ("SMTP_PASSWORD", "a-real-password")):
            monkeypatch.setattr(monitor, name, value)
        monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
        seen = {}
        monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda use_ssl, smtp_timeout=None: seen.update(timeout=smtp_timeout) or type("Smtp", (), {"quit": lambda self: None})())
        monitor.doctor_check_email_notifications(monitor.DoctorReport())
        assert seen == {"timeout": monitor.DOCTOR_SMTP_TIMEOUT}


class TestTheWebhookRows:
    @pytest.fixture(autouse=True)
    def webhook_off(self, monkeypatch):
        for name in ("WEBHOOK_ACTIVE_NOTIFICATION", "WEBHOOK_INACTIVE_NOTIFICATION", "WEBHOOK_TRACK_NOTIFICATION", "WEBHOOK_SONG_NOTIFICATION", "WEBHOOK_SONG_ON_LOOP_NOTIFICATION", "WEBHOOK_OFFLINE_ENTRIES_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION", "WEBHOOK_FOLLOWERS_NOTIFICATION", "WEBHOOK_FOLLOWINGS_NOTIFICATION", "WEBHOOK_PROFILE_NOTIFICATION"):
            monkeypatch.setattr(monitor, name, False)
        monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "")
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "")
        monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {})
        monkeypatch.setattr(monitor, "WEBHOOK_TEMPLATE", {})

    def test_webhooks_off_with_nothing_selected_passes(self):
        assert monitor.doctor_check_webhook_notifications(monitor.DoctorReport())[0].label == "Webhook alerts are disabled"

    def test_alert_types_selected_with_the_channel_off_warns(self, monkeypatch):
        monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_NOTIFICATION", True)
        row = monitor.doctor_check_webhook_notifications(monitor.DoctorReport())[0]
        assert row.status == "WARN"
        assert row.label == "Webhook alert types are selected but webhooks are switched off"

    def test_the_channel_on_with_no_alert_types_warns(self, monkeypatch):
        monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.sh/private-topic")
        row = monitor.doctor_check_webhook_notifications(monitor.DoctorReport())[0]
        assert row.status == "WARN"
        assert row.label == "Webhook alerts are on but no alert types are selected"
        assert row.advice.fix.startswith("Turn on at least one webhook alert in the configuration file, or set WEBHOOK_ENABLED to False")

    @pytest.mark.parametrize("provider, url", [("", "https://ntfy.sh/private-topic"), ("ntfy", "http://ntfy.sh/private-topic")])
    def test_an_unusable_destination_fails(self, monkeypatch, provider, url):
        monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", provider)
        monkeypatch.setattr(monitor, "WEBHOOK_URL", url)
        assert monitor.doctor_check_webhook_notifications(monitor.DoctorReport())[0].status == "FAIL"

    def test_a_usable_channel_passes_without_showing_the_link(self, monkeypatch):
        monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.sh/private-topic")
        monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_NOTIFICATION", True)
        report = monitor.DoctorReport()
        row = monitor.doctor_check_webhook_notifications(report)[0]
        assert row.status == "PASS"
        assert row.label == f"{monitor.WEBHOOK_READY_CHECK_LABEL} for ntfy"
        assert "private-topic" not in row.detail
        assert report.webhook_ready is True


class TestTheReport:
    def test_sections_render_in_the_fixed_order_whatever_order_they_ran_in(self):
        report = report_of(
            check("Notifications", "PASS", "Webhook alerts are disabled"),
            check("Environment", "PASS", "Python is supported"),
            check("Target", "PASS", "The monitored profile exists"),
        )
        rendered = monitor.render_doctor_sections(report)
        assert rendered.index("Environment") < rendered.index("Target") < rendered.index("Notifications")

    def test_an_empty_section_is_not_printed(self):
        rendered = monitor.render_doctor_sections(report_of(check("Environment", "PASS", "Python is supported")))
        assert "Connectivity" not in rendered

    # Every section a check can be filed under has to have a place in the report, or its rows vanish
    def test_every_section_a_check_uses_is_in_the_render_order(self):
        used = set(re.findall(r'make_doctor_check\(\s*"([A-Za-z ]+)"', SOURCE))
        used.update(re.findall(r'section="([A-Za-z ]+)"', SOURCE))
        assert used - set(monitor.DOCTOR_SECTIONS) - {monitor.DOCTOR_DELIVERY_SECTION} == set()

    # Delivery results are printed as they happen, so their section name stays outside the rendered tuple
    def test_delivery_results_are_not_rendered_inside_a_section(self):
        assert monitor.DOCTOR_DELIVERY_SECTION not in monitor.DOCTOR_SECTIONS

    def test_the_marker_starts_the_line_and_the_detail_is_indented(self):
        rendered = monitor.render_doctor_sections(report_of(check("Environment", "WARN", "A warning", "A detail", fix_advice())))
        lines = rendered.splitlines()
        assert "[WARN] A warning" in lines
        assert "  A detail" in lines
        assert "  To fix: Do the thing" in lines

    def test_a_passing_row_carries_no_action(self):
        rendered = monitor.render_doctor_sections(report_of(check("Environment", "PASS", "All good", "A detail", fix_advice())))
        assert "To fix:" not in rendered

    # The fix line carries its own guide, so both are indented rather than one sequence spanning the newline
    def test_a_multi_line_fix_is_indented_on_every_line(self):
        advice = monitor.make_recovery_advice("config.invalid", "Broken", monitor.recovery_fix_with_guide("Do the thing", monitor.CONFIG_FILE_GUIDE_URL), False)
        rendered = monitor.render_doctor_sections(report_of(check("Environment", "FAIL", "Broken", advice=advice)))
        assert f"  Guide: {monitor.CONFIG_FILE_GUIDE_URL}" in rendered.splitlines()

    def test_the_install_method_is_stated_once_rather_than_taking_a_row(self):
        rendered = monitor.render_doctor_sections(report_of(check()))
        assert f"Detected install method: {monitor.install_method()}" in rendered
        assert "[PASS] Detected install method" not in rendered

    def test_a_detail_is_redacted_when_the_row_is_built(self, monkeypatch):
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.sh/private-topic")
        assert "private-topic" not in check(detail="Path: https://ntfy.sh/private-topic").detail

    # The constructor only redacts the detail, so a label carrying an error message needs the render to redact too
    def test_a_label_is_redacted_when_the_report_is_rendered(self, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", REAL_KEY)
        rendered = monitor.render_doctor_sections(report_of(check(label=f"Last.fm rejected api_key={REAL_KEY}")))
        assert REAL_KEY not in rendered

    @pytest.mark.parametrize("checks, expected", [
        ([("PASS", None)], "All checks passed. You are good to go!"),
        ([("WARN", "advice")], "All critical checks passed with 1 warning(s). Review the warnings above."),
        ([("FAIL", "advice"), ("WARN", "advice")], "1 check(s) failed, 1 warning(s). Fix the failures above before relying on the tool."),
    ])
    def test_the_verdict_counts_what_the_report_showed(self, checks, expected):
        rows = [check(status=status, advice=fix_advice() if advice else None) for status, advice in checks]
        assert expected in monitor.render_doctor_summary(rows)

    def test_the_summary_ends_with_its_own_guide(self):
        assert monitor.render_doctor_summary([check()]).endswith(f"Guide: {monitor.DOCTOR_GUIDE_URL}")


class TestTheRunAndItsVerdict:
    @pytest.fixture
    def stubbed_checks(self, monkeypatch):
        """Replaces every section with a stub, so a run can be driven without touching the network."""
        produced = {"rows": []}
        for name in ("doctor_check_environment", "doctor_check_configuration", "doctor_check_connectivity", "doctor_check_authentication", "doctor_check_spotify_metadata", "doctor_check_target", "doctor_check_email_notifications", "doctor_check_webhook_notifications"):
            monkeypatch.setattr(monitor, name, lambda *args, **kwargs: [])
        monkeypatch.setattr(monitor, "doctor_check_environment", lambda *args, **kwargs: list(produced["rows"]))
        return produced

    def test_a_clean_run_exits_zero(self, stubbed_checks, capsys):
        stubbed_checks["rows"] = [check("Environment", "PASS", "All good")]
        assert monitor.run_doctor() == 0
        assert "All checks passed" in capsys.readouterr().out

    def test_a_warning_does_not_change_the_exit_code(self, stubbed_checks, capsys):
        stubbed_checks["rows"] = [check("Environment", "WARN", "A warning", advice=fix_advice())]
        assert monitor.run_doctor() == 0
        capsys.readouterr()

    def test_a_failure_exits_one(self, stubbed_checks, capsys):
        stubbed_checks["rows"] = [check("Environment", "FAIL", "Broken", advice=fix_advice())]
        assert monitor.run_doctor() == 1
        capsys.readouterr()

    # The report says it writes nothing, which is only worth saying if it is true
    def test_the_run_writes_no_files(self, stubbed_checks, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        stubbed_checks["rows"] = [check("Environment", "PASS", "All good")]
        monitor.run_doctor(target_value="someuser")
        capsys.readouterr()
        assert list(tmp_path.iterdir()) == []

    def test_the_notice_comes_before_the_first_check(self, stubbed_checks, capsys):
        stubbed_checks["rows"] = [check("Environment", "PASS", "All good")]
        monitor.run_doctor()
        output = capsys.readouterr().out
        assert output.index("No files will be written") < output.index("Doctor")

    # The block belongs to the command that asked for the report, so a wizard-driven run is not followed by a second copy
    def test_the_run_itself_prints_no_next_steps_block(self, stubbed_checks, capsys):
        stubbed_checks["rows"] = [check("Environment", "PASS", "All good")]
        monitor.run_doctor(target_value="someuser")
        assert "Next steps" not in capsys.readouterr().out

    # The report ends with the next action rather than leaving the reader to assemble the command
    def test_the_next_steps_block_closes_a_passing_report(self, capsys):
        monitor.print_doctor_next_steps("someuser", 0)
        output = capsys.readouterr().out
        assert "Start monitoring:" in output
        assert "After Doctor passes" not in output
        assert monitor.render_command(["someuser"]) in output

    def test_a_failing_report_still_prints_it_and_says_to_fix_first(self, capsys):
        monitor.print_doctor_next_steps("someuser", 1)
        assert "After Doctor passes, start monitoring:" in capsys.readouterr().out

    def test_the_command_falls_back_to_a_placeholder_without_a_username(self, capsys):
        monitor.print_doctor_next_steps()
        assert "<lastfm_username>" in capsys.readouterr().out

    # The verdict and the exit code have to describe the same run, delivery tests included
    def test_a_failed_delivery_test_reaches_the_verdict_and_the_exit_code(self, stubbed_checks, capsys, monkeypatch):
        stubbed_checks["rows"] = [check("Environment", "PASS", "All good")]

        def offer(report, input_func=None):
            failed = check(monitor.DOCTOR_DELIVERY_SECTION, "FAIL", "Doctor test email delivery failed", advice=fix_advice())
            report.checks.append(failed)
            return [failed]

        monkeypatch.setattr(monitor, "_doctor_offer_notification_tests", offer)
        assert monitor.run_doctor() == 1
        assert "1 check(s) failed" in capsys.readouterr().out


class TestTheDeliveryTests:
    @pytest.fixture
    def interactive(self, monkeypatch):
        monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr(monitor, "_doctor_terminal_stream", lambda: type("Terminal", (), {"isatty": lambda self: True})())

    def test_nothing_is_offered_without_a_ready_channel(self, interactive, capsys):
        assert monitor._doctor_offer_notification_tests(monitor.DoctorReport()) == []
        assert capsys.readouterr().out == ""

    # A real message is never sent without a separate yes, so an empty answer declines
    @pytest.mark.parametrize("answer", ["", "n", "no", "  "])
    def test_declining_sends_nothing_and_records_a_skip(self, interactive, capsys, monkeypatch, answer):
        sent = []
        monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: sent.append(True) or 0)
        report = monitor.DoctorReport()
        report.email_ready = True
        checks = monitor._doctor_offer_notification_tests(report, input_func=lambda prompt: answer)
        capsys.readouterr()
        assert sent == []
        assert [row.status for row in checks] == ["SKIP"]

    def test_approving_sends_exactly_one_message(self, interactive, capsys, monkeypatch):
        sent = []
        monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: sent.append(kwargs.get("smtp_timeout")) or 0)
        report = monitor.DoctorReport()
        report.email_ready = True
        checks = monitor._doctor_offer_notification_tests(report, input_func=lambda prompt: "y")
        capsys.readouterr()
        assert sent == [monitor.DOCTOR_SMTP_TIMEOUT]
        assert [row.status for row in checks] == ["PASS"]

    def test_a_refused_delivery_is_reported_as_a_failure(self, interactive, capsys, monkeypatch):
        monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: 1)
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
        report = monitor.DoctorReport()
        report.webhook_ready = True
        checks = monitor._doctor_offer_notification_tests(report, input_func=lambda prompt: "y")
        capsys.readouterr()
        assert [row.status for row in checks] == ["FAIL"]

    # A result recorded only in the returned list would leave the verdict describing a different run
    def test_every_delivery_result_is_recorded_on_the_report(self, interactive, capsys, monkeypatch):
        monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: 0)
        monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: 0)
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
        report = monitor.DoctorReport()
        report.email_ready = True
        report.webhook_ready = True
        checks = monitor._doctor_offer_notification_tests(report, input_func=lambda prompt: "y")
        capsys.readouterr()
        assert len(checks) == 2
        assert report.checks == checks

    def test_a_non_interactive_run_is_never_asked(self, monkeypatch, capsys):
        monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: False)
        monkeypatch.setattr(monitor, "_doctor_terminal_stream", lambda: type("Terminal", (), {"isatty": lambda self: True})())
        report = monitor.DoctorReport()
        report.email_ready = True
        assert monitor._doctor_offer_notification_tests(report) == []
        assert capsys.readouterr().out == ""

    def test_an_unreadable_answer_declines(self, interactive, capsys):
        def refusing(prompt):
            raise EOFError

        assert monitor._doctor_ask_yes_no("Send one?", input_func=refusing) is False
        assert "Delivery test skipped." in capsys.readouterr().out

    def test_an_unrecognized_answer_is_asked_again(self, interactive, capsys):
        answers = iter(["maybe", "y"])
        assert monitor._doctor_ask_yes_no("Send one?", input_func=lambda prompt: next(answers)) is True
        assert "Please answer 'y' or 'n'." in capsys.readouterr().out


class TestWhereDoctorSitsInStartup:
    # A user with several problems should get the whole report, not the first gate that exits
    @pytest.mark.parametrize("gate", [
        "if not check_internet():",
        "if not args.username:",
        "if not doctor_value_is_set(LASTFM_API_KEY):",
        "if not doctor_value_is_set(LASTFM_API_SECRET):",
        "with open(CSV_FILE, 'a', newline='', buffering=1, encoding=\"utf-8\") as _:",
        "import bs4  # type: ignore  # noqa: F401",
    ])
    def test_doctor_dispatches_before_every_startup_gate_that_can_exit(self, gate):
        assert SOURCE.index("if args.doctor:") < SOURCE.index(gate), f"a startup gate runs before doctor: {gate}"

    # Doctor reports the configuration a run would use, so the overrides are applied before it dispatches
    def test_the_command_line_overrides_are_applied_before_doctor(self):
        assert SOURCE.index("apply_cli_overrides(args)") < SOURCE.index("if args.doctor:")

    # A channel main would switch off before doctor ran would be reported as merely disabled
    def test_the_unusable_webhook_gate_runs_after_doctor(self):
        assert SOURCE.index("if args.doctor:") < SOURCE.index("if WEBHOOK_ENABLED and not validate_webhook_url():\n        verbose_print(\"Webhook notifications are off")

    def test_the_flag_is_advertised(self):
        assert '"--doctor",' in SOURCE
        assert "Run read-only preflight checks and report what is ready and what is not" in SOURCE


class TestTheDetailShapes:
    # A detail is a Key: value pair, a comma-separated list of names or a sentence the label did not say
    @pytest.mark.parametrize("rows", [
        lambda: monitor.doctor_check_environment(),
        lambda: monitor.doctor_check_configuration(),
        lambda: monitor.doctor_check_target(monitor.DoctorReport()),
    ])
    def test_no_detail_joins_two_pairs_with_a_pipe(self, quiet_config, rows):
        assert [row.label for row in rows() if "|" in row.detail] == []

    def test_no_passing_row_gives_an_instruction(self, quiet_config):
        instructions = [row.label for row in monitor.doctor_check_configuration() if row.status == "PASS" and row.detail.startswith(("Set ", "Run ", "Install ", "Turn "))]
        assert instructions == []

    # unknown and Re-run with --debug are for a surprise in the loop, not for a check written to test one thing
    def test_no_check_ends_at_re_run_with_debug(self, quiet_config, monkeypatch):
        monkeypatch.setattr(monitor, "LASTFM_API_KEY", "")
        monkeypatch.setattr(monitor, "LASTFM_API_SECRET", "")
        rows = monitor.doctor_check_environment(version_info=(3, 8)) + monitor.doctor_check_configuration() + monitor.doctor_check_authentication(monitor.DoctorReport()) + monitor.doctor_check_target(monitor.DoctorReport())
        assert [row.label for row in rows if row.advice is not None and row.advice.code == "unknown"] == []


# One row shape and one advice shape across the family: the advice rides on the row and its fix carries the
# guide, so a row or an advice copied from a sibling means the same thing here
def test_the_doctor_row_and_its_advice_share_one_contract():
    row_parameters = list(inspect.signature(monitor.make_doctor_check).parameters.values())
    advice_parameters = list(inspect.signature(monitor.make_recovery_advice).parameters.values())

    assert [parameter.name for parameter in row_parameters] == ["section", "status", "label", "detail", "advice"]
    assert [parameter.default for parameter in row_parameters[3:]] == ["", None]
    assert [parameter.name for parameter in advice_parameters] == ["code", "summary", "fix", "retryable", "detail"]
    assert monitor.recovery_fix_with_guide("do the thing", "https://example.invalid/page") == "do the thing\nGuide: https://example.invalid/page"


# A non-pass row is refused without advice and keeps the advice it was given, which is where its fix and guide live
def test_a_row_carries_its_advice_and_refuses_to_go_without():
    advice = monitor.make_recovery_advice("config.invalid", "a warning row", monitor.recovery_fix_with_guide("do the thing", monitor.DOCTOR_GUIDE_URL), False)

    row = monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping", advice)

    assert row.advice is advice
    assert not hasattr(advice, "guide_url")
    with pytest.raises(ValueError):
        monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping")


# A string such as "false" counts as on, so an on/off setting holding anything but True or False is named in one row
def test_invalid_boolean_settings_are_reported_in_one_row(monkeypatch):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", "false", raising=False)
    monkeypatch.setattr(monitor, "SMTP_SSL", 1, raising=False)

    rows = [item for item in monitor.doctor_check_configuration() if item.label == "One or more on/off settings are invalid"]

    assert [item.status for item in rows] == ["FAIL"]
    assert "ERROR_NOTIFICATION must be True or False, not 'false'" in rows[0].detail
    assert "SMTP_SSL must be True or False, not 1" in rows[0].detail
    assert rows[0].advice.fix.startswith("Set the reported settings to True or False")


# The shipped defaults are all real booleans, so a run with nothing overridden never sees the on/off row
def test_the_shipped_defaults_pass_the_boolean_check():
    assert monitor.runtime_boolean_errors() == []
