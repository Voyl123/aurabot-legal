"""Tests for the small input parsers in views (gear score, voice link)."""

from src.views import _parse_gear_score, parse_voice


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