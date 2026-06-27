"""GBA LZ77 (BIOS type 0x10) codec.

FireRed stores sprites and palettes as LZ77-compressed blobs referenced by
pointer tables. We need to decompress originals (to merge them) and compress
new data (to write back).

The compressor emits a *literal-only* stream: valid LZ77 the BIOS decompresses
correctly, just without back-references. It's simple, fast and — crucially —
can never produce an out-of-range copy that corrupts VRAM. The ~12.5% size
overhead is irrelevant given the ROM's multi-MiB of free space.
"""

from __future__ import annotations


def decompress(data: bytes, offset: int = 0) -> bytes:
    """Decompress a GBA LZ77 (0x10) blob starting at ``offset``."""
    if data[offset] != 0x10:
        raise ValueError(f"not an LZ77 stream (header byte {data[offset]:#x})")
    size = data[offset + 1] | (data[offset + 2] << 8) | (data[offset + 3] << 16)
    out = bytearray()
    pos = offset + 4
    while len(out) < size:
        flags = data[pos]; pos += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> bit):
                b1 = data[pos]; b2 = data[pos + 1]; pos += 2
                length = (b1 >> 4) + 3
                disp = ((b1 & 0x0F) << 8 | b2) + 1
                start = len(out) - disp
                for k in range(length):
                    out.append(out[start + k])
            else:
                out.append(data[pos]); pos += 1
    return bytes(out)


def compress(data: bytes) -> bytes:
    """Compress ``data`` into a literal-only LZ77 (0x10) stream."""
    n = len(data)
    out = bytearray()
    out.append(0x10)
    out += bytes((n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF))
    i = 0
    while i < n:
        chunk = data[i:i + 8]          # up to 8 literals per flag byte
        out.append(0x00)               # all-literal flag
        out += chunk
        i += 8
    return bytes(out)


def compressed_size(raw_len: int) -> int:
    """Byte length of the literal-only stream for ``raw_len`` input bytes."""
    blocks = (raw_len + 7) // 8
    return 4 + blocks + raw_len
