"""Generation III text codec.

Pokémon GBA games store text in a proprietary single-byte encoding, not ASCII.
This module converts between Python ``str`` and the Gen III byte encoding so we
can read and rewrite species names. We only need the printable subset (letters,
digits, a little punctuation); the full control-code space is left untouched.

``0xFF`` terminates a string (EOS); unused trailing bytes in a fixed-width field
are also padded with ``0xFF``.
"""

from __future__ import annotations

EOS = 0xFF  # end-of-string / padding byte

# Byte → character for the printable subset we care about.
_DECODE: dict[int, str] = {0x00: " "}
for _i in range(10):  # 0xA1..0xAA → '0'..'9'
    _DECODE[0xA1 + _i] = chr(ord("0") + _i)
for _i in range(26):  # 0xBB..0xD4 → 'A'..'Z'
    _DECODE[0xBB + _i] = chr(ord("A") + _i)
for _i in range(26):  # 0xD5..0xEE → 'a'..'z'
    _DECODE[0xD5 + _i] = chr(ord("a") + _i)
_DECODE.update({
    0xAB: "!", 0xAC: "?", 0xAD: ".", 0xAE: "-",
    0xB1: "“", 0xB2: "”", 0xB3: "‘", 0xB4: "’",
    0xB5: "♂", 0xB6: "♀", 0xB8: ",", 0xBA: "/",
    0xF0: ":",
})

# Character → byte (reverse map) for everything we can faithfully round-trip.
_ENCODE: dict[str, int] = {v: k for k, v in _DECODE.items()}


def decode(raw: bytes) -> str:
    """Decode a Gen III byte string up to the first EOS terminator."""
    out: list[str] = []
    for b in raw:
        if b == EOS:
            break
        out.append(_DECODE.get(b, "?"))
    return "".join(out)


def encode(text: str, length: int) -> bytes:
    """Encode ``text`` into a fixed ``length``-byte field (EOS-terminated/padded).

    Characters that can't be represented are dropped. The result is always
    exactly ``length`` bytes: the encoded text, an ``0xFF`` terminator when it
    fits, then ``0xFF`` padding.
    """
    body = bytearray()
    for ch in text:
        b = _ENCODE.get(ch)
        if b is None:
            continue
        if len(body) >= length - 1:   # leave room for the EOS terminator
            break
        body.append(b)
    # Terminate + pad with EOS to the fixed width.
    body.append(EOS)
    body.extend([EOS] * (length - len(body)))
    return bytes(body[:length])
