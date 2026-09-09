"""The --help screen: the shared group names and order, the one-shot help sentences and the examples block."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

import lastfm_monitor as monitor

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GROUP_ORDER = (
    "Configuration & dotenv files",
    "API credentials",
    "Email notifications",
    "Webhook notifications",
    "Intervals & timers",
    "User information & listing",
    "Features & output",
)

EXAMPLE_HEADINGS = ("Getting started", "Notifications", "Listening extras", "Information and diagnostics")

# Copied verbatim from the sibling monitors, so two of these screens can be compared line by line
SHARED_SENTENCES = {
    "--doctor": "Run read-only preflight checks and report what is ready and what is not",
    "--set-webhook-url": "Save a Discord or ntfy webhook URL through a hidden prompt",
    "--send-test-email": "Send test email to verify SMTP settings",
    "--send-test-webhook": "Send one test webhook without starting monitoring",
}


@pytest.fixture(scope="module")
def help_screen():
    result = subprocess.run([sys.executable, str(PROJECT_ROOT / "lastfm_monitor.py"), "--help"], capture_output=True, text=True, cwd=PROJECT_ROOT, env={"PATH": "/usr/bin:/bin", "COLUMNS": "100"})
    assert result.returncode == 0, result.stderr
    return result.stdout


class TestArgumentGroups:

    @pytest.mark.parametrize("title", GROUP_ORDER)
    def test_the_shared_group_names_are_used(self, title, help_screen):
        assert f"\n{title}:\n" in help_screen

    def test_the_groups_are_in_the_shared_order(self, help_screen):
        positions = [help_screen.index(f"\n{title}:\n") for title in GROUP_ORDER]
        assert positions == sorted(positions)

    # A bare Notifications next to Webhook notifications reads as the parent of both
    def test_the_email_group_says_which_channel_it_is(self, help_screen):
        assert "\nNotifications:\n" not in help_screen[:help_screen.index("Examples:")]

    def test_every_one_shot_command_sits_with_the_files_it_is_about(self, help_screen):
        section = help_screen[help_screen.index("\nConfiguration & dotenv files:\n"):help_screen.index("\nAPI credentials:\n")]
        for flag in ("--config-file", "--generate-config", "--env-file", "--doctor", *monitor.SECRET_ACTION_FLAGS):
            assert flag in section, flag

    @pytest.mark.parametrize("flag, sentence", sorted(SHARED_SENTENCES.items()))
    def test_a_shared_flag_describes_itself_the_shared_way(self, flag, sentence, help_screen):
        collapsed = " ".join(help_screen.split())
        assert f"{flag} {sentence}" in collapsed or f"{flag}, {sentence}" in collapsed

    # The sentinel is only discoverable if the screen says it exists
    @pytest.mark.parametrize("flag", ["--config-file", "--env-file"])
    def test_both_file_flags_advertise_the_none_sentinel(self, flag, help_screen):
        collapsed = " ".join(help_screen.split())
        # The last occurrence is the description, the first is the usage line
        described = collapsed[collapsed.rindex(f"{flag} PATH"):]
        assert "disable with 'none'" in described[:160]


class TestExamples:

    def test_the_headings_appear_in_order(self, help_screen):
        block = help_screen[help_screen.index("Examples:"):]
        positions = [block.index(f"\n{heading}:\n") for heading in EXAMPLE_HEADINGS]
        assert positions == sorted(positions)

    # Every sibling opens with the wizard, which is the one command a first-time reader can run without knowing anything
    def test_the_wizard_is_the_first_example(self, help_screen):
        block = help_screen[help_screen.index("Examples:"):]
        first = [line.strip() for line in block.splitlines() if line.startswith("  ")][:2]
        assert first == ["# Guided setup, recommended for the first run", "python3 lastfm_monitor.py --setup"]

    def test_the_block_ends_with_the_guide(self, help_screen):
        assert help_screen.rstrip().endswith(f"Guide: {monitor.QUICK_START_GUIDE_URL}")

    # A command added without a comment is the drift this catches
    def test_every_example_command_has_a_comment_above_it(self, help_screen):
        lines = help_screen[help_screen.index("Examples:"):].splitlines()
        commands = [index for index, line in enumerate(lines) if line.startswith("  ") and not line.startswith("  #")]
        assert commands
        for index in commands:
            assert lines[index - 1].startswith("  #"), lines[index]

    def test_every_example_is_written_for_the_detected_install(self, help_screen):
        lines = help_screen[help_screen.index("Examples:"):].splitlines()
        commands = [line.strip() for line in lines if line.startswith("  ") and not line.startswith("  #")]
        assert len(commands) >= 10
        assert all(command.startswith("python3 lastfm_monitor.py ") for command in commands)

    def test_the_banner_is_printed_once(self, help_screen):
        assert help_screen.count(monitor.STARTUP_BANNER.strip("\n").splitlines()[-1]) == 1
        assert len(re.findall(r"^ {21}v\d", help_screen, re.MULTILINE)) == 1


class TestExampleRenderer:

    def test_a_note_without_a_command_is_rendered_on_its_own(self):
        rendered = monitor.render_help_examples((("Getting started", (("Sign in first", ""), ("Then run", "tool x"))),), "https://example.invalid/")
        assert rendered.splitlines()[3:7] == ["  # Sign in first", "", "  # Then run", "  tool x"]

    def test_a_multi_line_comment_keeps_one_prefix_per_line(self):
        rendered = monitor.render_help_examples((("Notifications", ((" first\nthen", "tool y"),)),), "https://example.invalid/")
        assert "  #  first\n  # then\n  tool y" in rendered

    def test_the_guide_closes_the_block(self):
        rendered = monitor.render_help_examples((("Getting started", (("Run it", "tool"),)),), "https://example.invalid/")
        assert rendered.startswith("Examples:\n\n") and rendered.endswith("\n\nGuide: https://example.invalid/\n")
