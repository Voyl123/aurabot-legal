"""Tests for the small input parsers (gear score, voice link, roles, duration)."""

from src.views import CreatePartyModal, _parse_gear_score, parse_voice
from src.timeparse import parse_duration, humanize_duration


def test_parse_roles_slash_and_space():
    assert CreatePartyModal._parse_roles("2/1/3") == {"tank": 2, "healer": 1, "dps": 3}
    assert CreatePartyModal._parse_roles("2 1 3") == {"tank": 2, "healer": 1, "dps": 3}


def test_parse_roles_defaults_and_clamp():
    assert CreatePartyModal._parse_roles("") == {"tank": 1, "healer": 1, "dps": 4}
    assert CreatePartyModal._parse_roles("99/0/0")["tank"] == 20  # clamped


def test_parse_duration():
    assert parse_duration("2h") == 7200
    assert parse_duration("90m") == 5400
    assert parse_duration("1h30m") == 5400
    assert parse_duration("90") == 5400  # bare number = minutes
    assert parse_duration("") is None
    assert parse_duration("soon") is None


def test_humanize_duration():
    assert humanize_duration(7200) == "2h"
    assert humanize_duration(5400) == "1h30m"
    assert humanize_duration(2700) == "45m"
    assert humanize_duration(None) == ""


def test_gear_score_accepts_plain_and_formatted():
    assert _parse_gear_score("4200") == 4200
    assert _parse_gear_score("4,200") == 4200
    assert _parse_gear_score(" 4 200 ") == 4200


def test_gear_score_rejects_garbage():
    assert _parse_gear_score("") is None
    assert _parse_gear_score(None) is None
    assert _parse_gear_score("abc") is None


def test_voice_channel_link_extracts_id():
    cid, url = parse_voice("https://discord.com/channels/123456789/987654321")
    assert cid == 987654321 and url is None


def test_voice_bare_id():
    cid, url = parse_voice("987654321")
    assert cid == 987654321 and url is None


def test_voice_external_url_kept_as_link():
    cid, url = parse_voice("https://discord.gg/invite")
    assert cid is None and url == "https://discord.gg/invite"


def test_voice_empty():
    assert parse_voice("") == (None, None)
    assert parse_voice(None) == (None, None)