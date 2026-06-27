"""LZ77 codec + sprite/palette graphics round-trips and the merge."""

import os
import random

from pokefusion import graphics, lz77


def test_lz77_roundtrip_random():
    rng = random.Random(0)
    for size in (0, 1, 7, 8, 9, 32, 2048):
        data = bytes(rng.randrange(256) for _ in range(size))
        assert lz77.decompress(lz77.compress(data)) == data


def test_lz77_header_and_size():
    raw = os.urandom(2048)
    comp = lz77.compress(raw)
    assert comp[0] == 0x10
    assert (comp[1] | comp[2] << 8 | comp[3] << 16) == 2048
    assert len(comp) == lz77.compressed_size(2048)


def test_tile_roundtrip():
    rng = random.Random(1)
    px = [[rng.randrange(16) for _ in range(64)] for _ in range(64)]
    assert graphics.decode_tiles(graphics.encode_tiles(px)) == px


def test_palette_roundtrip_and_invert():
    rng = random.Random(2)
    colors = [(rng.randrange(32), rng.randrange(32), rng.randrange(32)) for _ in range(16)]
    raw = graphics.encode_palette(colors)
    assert len(raw) == 32
    assert graphics.decode_palette(raw) == colors
    inv = graphics.invert_palette(colors)
    assert inv[0] == colors[0]                       # transparent kept
    assert inv[1] == (31 - colors[1][0], 31 - colors[1][1], 31 - colors[1][2])


def _solid_sprite(index):
    return graphics.encode_tiles([[index] * 64 for _ in range(64)])


def test_merge_outputs_valid_shapes():
    # base = solid index 1 (green), partner = solid index 1 (purple); distinct palettes
    base_pal = graphics.encode_palette([(0, 0, 0), (0, 31, 0)] + [(0, 0, 0)] * 14)
    part_pal = graphics.encode_palette([(0, 0, 0), (31, 0, 31)] + [(0, 0, 0)] * 14)
    front, back, pal = graphics.merge_fusion(
        _solid_sprite(1), _solid_sprite(1), base_pal,
        _solid_sprite(1), _solid_sprite(1), part_pal, split=26)
    assert len(front) == graphics.SPRITE_BYTES
    assert len(back) == graphics.SPRITE_BYTES
    assert len(pal) == 16
    # top rows should map to the partner colour, bottom rows to the base colour
    fpx = graphics.decode_tiles(front)
    assert pal[fpx[0][0]] == (31, 0, 31)             # head = partner
    assert pal[fpx[63][0]] == (0, 31, 0)             # body = base
