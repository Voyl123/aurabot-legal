"""IPS patch generation + application.

IPS is the classic, dead-simple ROM patch format and is all we need: our edits
live far below the 16 MiB / ``0xFFFFFF`` offset ceiling. Producing a ``.ips``
lets the user share the hack legally — recipients apply it to their own clean
FireRed ROM.

Format: ``"PATCH"`` header, then records of ``[3-byte offset][2-byte size][data]``
(big-endian), terminated by ``"EOF"``.
"""

from __future__ import annotations

_HEADER = b"PATCH"
_EOF = b"EOF"
_EOF_OFFSET = 0x454F46  # the integer "EOF" — an offset may never equal this
_MAX_RECORD = 0xFFFF


def build_ips(original: bytes, modified: bytes) -> bytes:
    """Diff two equal-length images into an IPS patch."""
    if len(original) != len(modified):
        raise ValueError("IPS requires images of equal length")
    out = bytearray(_HEADER)
    i = 0
    n = len(original)
    while i < n:
        if original[i] == modified[i]:
            i += 1
            continue
        start = i
        while i < n and original[i] != modified[i] and (i - start) < _MAX_RECORD:
            i += 1
        # An offset can never be the literal "EOF"; nudge the record back one
        # byte (re-including an unchanged byte) if it would collide.
        if start == _EOF_OFFSET and start > 0:
            start -= 1
        chunk = modified[start:i]
        out += start.to_bytes(3, "big") + len(chunk).to_bytes(2, "big") + chunk
    out += _EOF
    return bytes(out)


def apply_ips(original: bytes, patch: bytes) -> bytes:
    """Apply an IPS patch to ``original`` and return the result (used by tests)."""
    if patch[:5] != _HEADER:
        raise ValueError("not an IPS patch (bad header)")
    data = bytearray(original)
    pos = 5
    while True:
        if patch[pos:pos + 3] == _EOF:
            break
        offset = int.from_bytes(patch[pos:pos + 3], "big"); pos += 3
        size = int.from_bytes(patch[pos:pos + 2], "big"); pos += 2
        if size == 0:  # RLE record
            run = int.from_bytes(patch[pos:pos + 2], "big"); pos += 2
            value = patch[pos]; pos += 1
            data[offset:offset + run] = bytes([value]) * run
        else:
            data[offset:offset + size] = patch[pos:pos + size]; pos += size
    return bytes(data)
