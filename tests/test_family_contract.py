"""The output contract these tools share: the status markers, the report shape and the shared sentences.

Every string asserted here was taken from the seven sibling monitors (steam, spotify, spotify_profile,
psn, github, instagram, xbox) on 2026-09-08 and is printed by all of them, or by all of the ones that
have the surface at all. Their sources are not available to CI, so the contract is pinned against this
repo instead. Changing a sentence here means changing it in the siblings too.
"""

from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")

# The four markers, and no fifth. A neutral fifth marker is the single largest source of drift in the family
SHARED_MARKERS = ("PASS", "WARN", "FAIL", "SKIP")

# Every section name, in the order the family prints them. lastfm adds one section of its own for the
# optional Spotify metadata backend, which no sibling has
SHARED_SECTION_ORDER = ("Environment", "Configuration", "Authentication", "Connectivity", "Target", "Notifications")

SHARED_SENTENCES = (
    "Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval.",
    "Detected install method: ",
    "Minimum supported version: ",
    "Using built-in defaults and command-line overrides",
    "Using environment variables and other configured sources",
    "Nothing was read from a dotenv file, the environment, the configuration file or the command line",
    "Every outbound request checks the server certificate",
    "No SMTP connection was attempted and no email was sent",
    "Nothing will be monitored until one is given",
    "check(s) failed",
    "Fix the failures above before relying on the tool.",
    "After Doctor passes, start monitoring:",
    "Quickest start (already configured):",
    "Easiest start (guided setup wizard):",
    "Check setup before monitoring:",
    "Full options: ",
)

SHARED_WIZARD_SENTENCES = (
    "This asks a few questions and writes a ready-to-run configuration.",
    "Write the normal per-target log file?",
    "Setup needs a writable dotenv file and cannot use 'none'.",
    "Which email notifications should be enabled?",
    "Which webhook alerts should be sent?",
    "In Discord: Edit Channel > Integrations > Webhooks > New Webhook > Copy Webhook URL.",
    "In ntfy: choose a hard-to-guess topic. Paste its complete topic URL, or just the topic name when it is hosted on ntfy.sh.",
    "Paste the ntfy topic URL or ntfy.sh topic name",
    "Enter a complete HTTPS ntfy topic URL or a topic name containing up to 64 letters, numbers, dashes or underscores.",
    "That does not look like a complete HTTPS webhook URL. Copy it from the webhook service and try again.",
    "The settings were kept without being checked. Run --doctor to check the sign-in again.",
)


# The startup banner every sibling opens with: a boxed glyph beside the tool name, the shared "Monitor"
# wordmark under it and the version on its own line. Pinned here because the sibling sources are not
# available to CI, so nothing else would notice the shape drifting away from the family
class TestTheStartupBanner:
    BOX_TOP = " .---------------."
    BOX_BOTTOM = " '---------------'"

    def test_the_glyph_sits_in_the_family_box(self):
        lines = monitor.STARTUP_BANNER.strip("\n").splitlines()
        assert lines[0].startswith(self.BOX_TOP)
        closing = next(index for index, line in enumerate(lines) if line.startswith(self.BOX_BOTTOM))
        for line in lines[1:closing]:
            box = line[:17]
            assert box.startswith("|") and box.endswith("|"), box

    def test_the_wordmark_and_version_share_one_indent(self):
        lines = monitor.STARTUP_BANNER.strip("\n").splitlines()
        closing = next(index for index, line in enumerate(lines) if line.startswith(self.BOX_BOTTOM))
        wordmark = lines[closing + 1:]
        assert len(wordmark) == 5
        assert all(line.startswith(" " * 21) for line in wordmark), wordmark
        assert "|  \\/  | ___  _ __ (_) |_ ___  _ __" in wordmark[1]

    def test_the_printer_puts_the_version_under_the_wordmark(self, capsys, monkeypatch):
        monkeypatch.setattr(monitor, "COLOR_ENABLED", False)

        monitor.print_startup_banner()

        printed = capsys.readouterr().out.splitlines()
        banner_lines = monitor.STARTUP_BANNER.splitlines()
        assert printed[:len(banner_lines)] == banner_lines
        assert printed[-2] == f"{'':21}v{monitor.VERSION}"
        assert printed[-1] == ""


class TestTheStatusMarkers:
    def test_only_four_markers_exist(self):
        assert tuple(monitor.DOCTOR_MARK_STYLES) == SHARED_MARKERS

    @pytest.mark.parametrize("marker", SHARED_MARKERS)
    def test_each_marker_renders_in_square_brackets(self, marker):
        assert monitor.render_doctor_marker(marker).strip().startswith(f"[{marker}]")

    def test_the_status_list_itself_holds_no_fifth_marker(self):
        assert tuple(monitor.DOCTOR_STATUSES) == SHARED_MARKERS

    def test_a_fifth_marker_cannot_be_built(self):
        with pytest.raises(ValueError, match="Unsupported doctor status"):
            monitor.make_doctor_check("Environment", "INFO", "A neutral row nobody else has")


class TestTheReportShape:
    def test_the_sections_are_the_family_order(self):
        shared = tuple(name for name in monitor.DOCTOR_SECTIONS if name in SHARED_SECTION_ORDER)
        assert shared == SHARED_SECTION_ORDER

    def test_the_one_section_this_tool_adds_sits_with_the_other_credential_sections(self):
        sections = list(monitor.DOCTOR_SECTIONS)
        assert sections.index("Authentication") < sections.index("Spotify metadata") < sections.index("Connectivity")

    def test_every_optional_dependency_row_says_what_it_is_used_for(self):
        report = monitor.DoctorReport()
        report.checks.extend(monitor.doctor_check_environment())
        optional = [check for check in report.checks if check.label.startswith("Optional dependency") and check.status == "PASS"]
        assert optional
        for check in optional:
            assert check.detail.startswith("Used only for"), f"{check.label} carries no detail"

    @pytest.mark.parametrize("statuses,sentence", [
        (("FAIL", "WARN"), "1 check(s) failed, 1 warning(s). Fix the failures above before relying on the tool."),
        (("WARN",), "All critical checks passed with 1 warning(s). Review the warnings above."),
        ((), "All checks passed. You are good to go!"),
    ])
    def test_each_verdict_is_the_one_shared_sentence(self, statuses, sentence):
        advice = monitor.make_recovery_advice("config.invalid", "Something happened", "Do the thing", False)
        checks = [monitor.make_doctor_check("Environment", status, f"Something {status}", advice=advice) for status in statuses]
        assert sentence in monitor.render_doctor_summary(checks)


class TestTheSharedSentences:
    @pytest.mark.parametrize("sentence", SHARED_SENTENCES)
    def test_the_report_and_welcome_wording_is_the_family_wording(self, sentence):
        assert sentence in SOURCE

    @pytest.mark.parametrize("sentence", SHARED_WIZARD_SENTENCES)
    def test_the_wizard_wording_is_the_family_wording(self, sentence):
        assert sentence in SOURCE


class TestTheNtfyTopicName:
    @pytest.mark.parametrize("answer,expected", [
        ("my-topic", "https://ntfy.sh/my-topic"),
        ("my_topic99", "https://ntfy.sh/my_topic99"),
        ("https://ntfy.example.com/private", "https://ntfy.example.com/private"),
    ])
    def test_a_bare_topic_name_becomes_a_topic_url(self, answer, expected):
        assert monitor.normalize_ntfy_topic_url(answer) == expected

    @pytest.mark.parametrize("answer", ["", "   ", "bad topic!!", "http://ntfy.sh/plain", "a" * 65, None])
    def test_anything_that_is_neither_is_refused(self, answer):
        assert monitor.normalize_ntfy_topic_url(answer) == ""


class TestTheWebhookProviderWarning:
    def test_it_names_the_service_the_way_the_service_spells_it(self, capsys, monkeypatch):
        monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/1/abc", raising=False)
        monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy", raising=False)
        args = monitor.argparse.Namespace(**{name: None for name in ("webhook_provider", "webhook_url", "webhook_enabled", "webhook_active", "webhook_inactive", "webhook_track", "webhook_song_changes", "webhook_loop", "webhook_offline_entries", "webhook_followers", "webhook_followings", "webhook_profile", "webhook_errors")})
        monitor.apply_webhook_cli_overrides(args, monitor.argparse.ArgumentParser())
        printed = capsys.readouterr().out
        assert "Using Discord." in printed
        assert "Using discord" not in printed


# Replays scripted answers to the wizard and records the prompts it asked
class Script:
    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def __call__(self, prompt=""):
        self.prompts.append(str(prompt))
        assert self.answers, f"the wizard asked more than the script answers: {prompt!r}"
        return self.answers.pop(0)


class TestTheWizardExplainsARejectedTopic:
    def test_a_topic_that_cannot_be_expanded_is_explained_rather_than_called_empty(self, capsys):
        state = monitor.WizardSetupState("config", "env", dict(monitor._config_template_defaults()))
        # Set up webhooks, choose ntfy, type an impossible topic, then decline the retry
        answers = Script(["y", "2", "n"])
        secrets = Script(["not a topic!!"])

        monitor._wizard_collect_webhook_section(state, input_func=answers, getpass_func=secrets)

        printed = capsys.readouterr().out
        # Every sibling normalizes the answer before this branch, which makes their own ntfy hint unreachable
        assert "Enter a complete HTTPS ntfy topic URL or a topic name containing up to 64 letters, numbers, dashes or underscores." in printed
        assert not any("Continue without the webhook URL?" in prompt for prompt in answers.prompts)

    def test_a_bare_topic_name_typed_into_the_wizard_is_saved_as_a_url(self):
        state = monitor.WizardSetupState("config", "env", dict(monitor._config_template_defaults()))
        # Set up webhooks, choose ntfy, then decline the access token and take every alert default
        answers = Script(["y", "2", "n", "1"])
        secrets = Script(["my-private-topic"])

        monitor._wizard_collect_webhook_section(state, input_func=answers, getpass_func=secrets)

        assert state.secret_updates["WEBHOOK_URL"] == "https://ntfy.sh/my-private-topic"

    def test_nothing_entered_still_offers_to_give_up(self):
        state = monitor.WizardSetupState("config", "env", dict(monitor._config_template_defaults()))
        # The give-up question asks whether to continue without the URL, so yes is the answer that stops
        answers = Script(["y", "2", "y"])
        secrets = Script(["   "])

        monitor._wizard_collect_webhook_section(state, input_func=answers, getpass_func=secrets)

        assert any("Continue without the webhook URL? Webhook alerts stay off until one is set" in prompt for prompt in answers.prompts)
        assert state.config_values["WEBHOOK_ENABLED"] is False
