"""IPS build/apply round-trips."""

from pokefusion.patch import apply_ips, build_ips


def test_build_apply_roundtrip():
    original = bytes(1000)
    modified = bytearray(original)
    modified[10:13] = b"\x01\x02\x03"
    modified[500] = 0xAB
    patch = build_ips(original, bytes(modified))
    assert patch.startswith(b"PATCH")
    assert patch.endswith(b"EOF")
    assert apply_ips(original, patch) == bytes(modified)


def test_no_changes_makes_empty_patch():
    data = bytes(256)
    patch = build_ips(data, data)
    assert patch == b"PATCH" + b"EOF"
    assert apply_ips(data, patch) == data


def test_unequal_length_rejected():
    import pytest
    with pytest.raises(ValueError):
        build_ips(bytes(10), bytes(11))
