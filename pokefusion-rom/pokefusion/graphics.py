"""Sprite & palette graphics: decode, composite-merge, quantize, encode.

FireRed mon sprites are 64×64, 4bpp (16-colour), stored as 8×8 tiles. Palette
index 0 is transparent. A species' single 16-colour palette is shared by its
front and back sprite.

The fusion sprite is a **bitmap merge**: the partner's head (top rows) over the
base's body (bottom rows), per-pixel, honouring transparency. Front and back
are merged against one shared palette, which we build by quantising the merged
colours down to 15 (+ transparent).
"""

from __future__ import annotations

import struct

DIM = 64                      # mon sprites are 64×64
TILES = DIM // 8              # 8×8 tile grid
TILE_BYTES = 32              # 8×8 px @ 4bpp
SPRITE_BYTES = TILES * TILES * TILE_BYTES  # 2048

RGB = tuple[int, int, int]


# --------------------------------------------------------------------------- #
# Tile (4bpp) <-> 2D index grid
# --------------------------------------------------------------------------- #
def decode_tiles(data: bytes) -> list[list[int]]:
    """2048-byte 4bpp tile blob → ``[y][x]`` palette indices (0..15)."""
    px = [[0] * DIM for _ in range(DIM)]
    for ty in range(TILES):
        for tx in range(TILES):
            base = (ty * TILES + tx) * TILE_BYTES
            for row in range(8):
                for col in range(4):
                    byte = data[base + row * 4 + col]
                    x = tx * 8 + col * 2
                    y = ty * 8 + row
                    px[y][x] = byte & 0x0F
                    px[y][x + 1] = (byte >> 4) & 0x0F
    return px


def encode_tiles(px: list[list[int]]) -> bytes:
    """Inverse of :func:`decode_tiles`."""
    out = bytearray(SPRITE_BYTES)
    for ty in range(TILES):
        for tx in range(TILES):
            base = (ty * TILES + tx) * TILE_BYTES
            for row in range(8):
                for col in range(4):
                    x = tx * 8 + col * 2
                    y = ty * 8 + row
                    lo = px[y][x] & 0x0F
                    hi = px[y][x + 1] & 0x0F
                    out[base + row * 4 + col] = lo | (hi << 4)
    return bytes(out)


# --------------------------------------------------------------------------- #
# Palette (BGR555) <-> list of RGB tuples (each channel 0..31)
# --------------------------------------------------------------------------- #
def decode_palette(data: bytes) -> list[RGB]:
    colors: list[RGB] = []
    for i in range(16):
        c = struct.unpack("<H", data[i * 2:i * 2 + 2])[0]
        colors.append((c & 31, (c >> 5) & 31, (c >> 10) & 31))
    return colors


def encode_palette(colors: list[RGB]) -> bytes:
    out = bytearray()
    for (r, g, b) in colors[:16]:
        out += struct.pack("<H", (r & 31) | ((g & 31) << 5) | ((b & 31) << 10))
    out += bytes(32 - len(out))
    return bytes(out)


def invert_palette(colors: list[RGB]) -> list[RGB]:
    """Inverted-shiny palette: invert colours 1..15, keep 0 (transparent)."""
    out = [colors[0]]
    for (r, g, b) in colors[1:]:
        out.append((31 - r, 31 - g, 31 - b))
    return out


# --------------------------------------------------------------------------- #
# The merge
# --------------------------------------------------------------------------- #
def _to_rgb(px: list[list[int]], pal: list[RGB]) -> list[list[RGB | None]]:
    """Indexed image → RGB image; index 0 becomes ``None`` (transparent)."""
    return [[None if px[y][x] == 0 else pal[px[y][x]] for x in range(DIM)]
            for y in range(DIM)]


def _composite(top: list[list[RGB | None]], bot: list[list[RGB | None]],
               split: int) -> list[list[RGB | None]]:
    """Rows < split come from ``top`` (partner head), else ``bot`` (base body);
    transparent pixels fall back to the other source."""
    out: list[list[RGB | None]] = []
    for y in range(DIM):
        primary, secondary = (top, bot) if y < split else (bot, top)
        out.append([primary[y][x] if primary[y][x] is not None else secondary[y][x]
                    for x in range(DIM)])
    return out


def _quantize(images: list[list[list[RGB | None]]], transparent: RGB
              ) -> list[RGB]:
    """Build a 16-colour palette (index 0 transparent) covering all images,
    keeping the 15 most frequent colours."""
    freq: dict[RGB, int] = {}
    for img in images:
        for row in img:
            for c in row:
                if c is not None:
                    freq[c] = freq.get(c, 0) + 1
    chosen = sorted(freq, key=lambda c: -freq[c])[:15]
    return [transparent] + chosen + [(0, 0, 0)] * (15 - len(chosen))


def _remap(img: list[list[RGB | None]], pal: list[RGB]) -> list[list[int]]:
    """Map an RGB image onto ``pal`` indices (nearest colour for 1..15)."""
    lut: dict[RGB | None, int] = {None: 0}
    opts = pal[1:]
    out = [[0] * DIM for _ in range(DIM)]
    for y in range(DIM):
        for x in range(DIM):
            c = img[y][x]
            idx = lut.get(c)
            if idx is None:
                best, bd = 1, 1 << 30
                for i, p in enumerate(opts, start=1):
                    d = (c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 + (c[2] - p[2]) ** 2
                    if d < bd:
                        bd, best = d, i
                idx = lut[c] = best
            out[y][x] = idx
    return out


def merge_fusion(base_front: bytes, base_back: bytes, base_pal: bytes,
                 partner_front: bytes, partner_back: bytes, partner_pal: bytes,
                 split: int = 26) -> tuple[bytes, bytes, list[RGB]]:
    """Bitmap-merge a base mon with a partner.

    Returns ``(front_tiles, back_tiles, palette)`` — front/back as 2048-byte
    4bpp blobs and a shared 16-colour palette (RGB tuples).
    """
    bpal, ppal = decode_palette(base_pal), decode_palette(partner_pal)
    bf = _to_rgb(decode_tiles(base_front), bpal)
    pf = _to_rgb(decode_tiles(partner_front), ppal)
    bb = _to_rgb(decode_tiles(base_back), bpal)
    pb = _to_rgb(decode_tiles(partner_back), ppal)

    front = _composite(pf, bf, split)     # partner head over base body
    back = _composite(pb, bb, split)

    pal = _quantize([front, back], transparent=bpal[0])
    return encode_tiles(_remap(front, pal)), encode_tiles(_remap(back, pal)), pal
