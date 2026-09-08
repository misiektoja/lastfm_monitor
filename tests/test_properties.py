"""Property-based tests for the answer normalizers and the dotenv values they end up as."""

from urllib.parse import quote

import pytest
from dotenv import dotenv_values
from hypothesis import given
from hypothesis import strategies as st

import lastfm_monitor as monitor

USERNAME_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
# A raw answer starting like a URL is read as one, so those names cannot round trip through the bare form
USERNAMES = st.text(alphabet=USERNAME_ALPHABET, min_size=1, max_size=60).filter(lambda name: not name.casefold().startswith(("http", "www.", "last.fm")))
SAFE_TEXT = st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"), max_size=40)
# The fragments a quoted value can be broken by, mixed into generated text so they are actually reached
DOTENV_FRAGMENTS = st.sampled_from(["\\", "\\n", "\\\\", '"', "'", "#", "$", "${HOME}", "\n", "\r", "\t", " ", "=", "export "])
DOTENV_VALUES = st.lists(st.one_of(SAFE_TEXT, DOTENV_FRAGMENTS), min_size=1, max_size=6).map("".join).filter(lambda value: value != "")
PATH_NAMES = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=40)
UNIT_SECONDS = {"s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1, "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60, "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600, "d": 86400, "day": 86400, "days": 86400}


# Every form of a profile a user can paste names the same user
@given(USERNAMES)
def test_every_target_form_reads_as_the_same_username(name):
    encoded = quote(name, safe="")
    forms = (name, f"  {name}  ", f"last.fm/user/{name}", f"https://www.last.fm/user/{name}", f"https://www.last.fm/user/{name}/library", f"https://www.last.fm/pl/user/{name}", f"https://www.last.fm/user/{encoded}?date_preset=LAST_7_DAYS")
    for form in forms:
        assert monitor.normalize_lastfm_username(form) == name, form


@given(USERNAMES, st.sampled_from([" ", "\t", "\n", "/", "?", "#", "@"]))
def test_a_character_a_url_would_break_on_is_refused(name, forbidden):
    assert monitor.normalize_lastfm_username(f"{name}{forbidden}tail") == ""


@given(st.text(max_size=120))
def test_normalizing_a_username_twice_changes_nothing(value):
    once = monitor.normalize_lastfm_username(value)
    assert monitor.normalize_lastfm_username(once) == once


@given(st.integers(min_value=1, max_value=100000), st.sampled_from(sorted(UNIT_SECONDS)))
def test_a_duration_carries_the_unit_it_was_typed_with(amount, unit):
    assert monitor.parse_duration_input(f"{amount}{unit}") == amount * UNIT_SECONDS[unit]
    assert monitor.parse_duration_input(f"{amount} {unit}") == amount * UNIT_SECONDS[unit]


@given(st.integers(min_value=0, max_value=48), st.integers(min_value=0, max_value=59), st.integers(min_value=0, max_value=59))
def test_a_duration_written_in_parts_adds_them_up(hours, minutes, seconds):
    total = hours * 3600 + minutes * 60 + seconds
    typed = " ".join(part for part in (f"{hours}h" if hours else "", f"{minutes}m" if minutes else "", f"{seconds}s" if seconds else "") if part)

    assert monitor.parse_duration_input(typed) == (total or None)


# The prompt shows the stored form and the readable one, so both have to mean the same number
@given(st.integers(min_value=1, max_value=10 ** 7))
def test_both_halves_of_a_shown_default_read_back_the_same(seconds):
    shown = monitor._wizard_format_duration(seconds)

    for half in shown.split(" - "):
        assert monitor.parse_duration_input(half) == seconds


@given(st.text(max_size=60))
def test_a_duration_is_a_positive_whole_number_of_seconds_or_nothing(value):
    parsed = monitor.parse_duration_input(value)
    assert parsed is None or (isinstance(parsed, int) and parsed > 0)


@given(st.integers(min_value=1, max_value=1000), st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6).filter(lambda unit: unit not in UNIT_SECONDS))
def test_a_unit_the_tool_does_not_know_is_refused(amount, unit):
    assert monitor.parse_duration_input(f"{amount}{unit}") is None


@pytest.mark.parametrize("normalize, extension", [(monitor._wizard_normalize_csv_path, ".csv"), (monitor._wizard_normalize_json_path, ".json")])
@given(name=PATH_NAMES, directory=st.sampled_from(["", "reports/", "~/logs/"]))
def test_a_path_answer_ends_up_with_one_extension(normalize, extension, name, directory):
    completed = normalize(f"{directory}{name}")

    assert completed == f"{directory}{name}{extension}"
    assert normalize(completed) == completed
    assert normalize(f"{directory}{name}.txt") == f"{directory}{name}.txt"


# A secret is written and read back by two different libraries, so the value the user typed has to survive both
@given(DOTENV_VALUES)
def test_a_secret_survives_the_dotenv_file(tmp_path_factory, value):
    destination = tmp_path_factory.mktemp("dotenv") / ".env"

    monitor.update_dotenv_file(destination, {"SMTP_PASSWORD": value})

    # Read the way the tool reads it, with interpolation off, so a value holding ${...} stays what was typed
    assert dotenv_values(str(destination), interpolate=False).get("SMTP_PASSWORD") == value
