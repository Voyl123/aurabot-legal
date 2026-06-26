"""Tests for the start-time parser."""

from src.timeparse import parse_start_time

NOW = 1_000_000.0


def test_now_aliases():
    for word in ("now", "asap", "0"):
        assert parse_start_time(word, now=NOW) == NOW


def test_relative_durations():
    assert parse_start_time("30m", now=NOW) == NOW + 1800
    assert parse_start_time("2h", now=NOW) == NOW + 7200
    assert parse_start_time("1h30m", now=NOW) == NOW + 5400


def test_bare_number_is_minutes():
    assert parse_start_time("90", now=NOW) == NOW + 5400


def test_clock_rolls_to_tomorrow_if_passed():
    result = parse_start_time("20:00", now=NOW)
    assert result is not None and result > NOW


def test_meridiem():
    assert parse_start_time("8:30pm", now=NOW) is not None


def test_sesh_fyi_timestamp_tag():
    # Pasted straight from https://sesh.fyi/timestamp/
    assert parse_start_time("<t:1750005400:F>") == 1750005400.0
    assert parse_start_time("<t:1750005400:R>") == 1750005400.0
    assert parse_start_time("<t:1750005400>") == 1750005400.0


def test_raw_unix_epoch():
    assert parse_start_time("1750005400") == 1750005400.0


def test_empty_and_garbage_return_none():
    assert parse_start_time("") is None
    assert parse_start_time(None) is None
    assert parse_start_time("lol") is None
