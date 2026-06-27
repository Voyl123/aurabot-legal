"""Gen III text codec round-trips."""

from pokefusion import gen3text
from pokefusion.romspec import NAME_LENGTH


def test_roundtrip_letters_digits():
    for s in ("Bulbtly", "CHARIZARD", "Mew2", "ab Cd"):
        assert gen3text.decode(gen3text.encode(s, NAME_LENGTH)) == s


def test_encode_is_fixed_width_and_terminated():
    raw = gen3text.encode("Pika", NAME_LENGTH)
    assert len(raw) == NAME_LENGTH
    assert raw[4] == gen3text.EOS          # terminator right after the text
    assert all(b == gen3text.EOS for b in raw[4:])


def test_encode_truncates_to_field():
    raw = gen3text.encode("ABCDEFGHIJKLMNOP", NAME_LENGTH)
    assert len(raw) == NAME_LENGTH
    assert gen3text.decode(raw) == "ABCDEFGHIJ"   # 10 chars fit, rest dropped


def test_decode_stops_at_terminator():
    raw = gen3text.encode("Hi", NAME_LENGTH)
    assert gen3text.decode(raw) == "Hi"


def test_unknown_chars_dropped():
    # '@' has no Gen III mapping; it should simply be skipped.
    assert gen3text.decode(gen3text.encode("A@B", NAME_LENGTH)) == "AB"
