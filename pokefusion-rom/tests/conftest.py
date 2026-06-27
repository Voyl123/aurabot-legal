"""Shared fixtures — a synthetic, well-formed FireRed-shaped ROM.

We build a 16 MiB image with valid base-stats / name / evolution / learnset
tables for *all* 412 species (mono-Normal "DUMMY" placeholders), then overwrite
a handful of real evolution families and a legendary. No copyrighted data is
used — just the table *layout* at the verified offsets — so the randomizer can
be exercised end-to-end offline.
"""

import struct

import pytest

from pokefusion import romspec
from pokefusion.rom import Rom
from pokefusion.structs import BaseStats, Evolution


def _bs(hp, atk, df, spd, spa, spdf, t1, t2):
    return BaseStats(hp, atk, df, spd, spa, spdf, t1, t2, tail=bytes(20))


def _learnset_blob(entries):
    blob = b"".join(struct.pack("<H", (lv << 9) | mv) for lv, mv in entries)
    return blob + b"\xff\xff"


# (name, type_ids, [(method, param, target), …]) keyed by species id.
T = romspec.TYPE_IDS
SPECIES = {
    1: ("BULBASAUR", (T["Grass"], T["Poison"]), [(romspec.EVO_LEVEL, 16, 2)]),
    2: ("IVYSAUR",   (T["Grass"], T["Poison"]), [(romspec.EVO_LEVEL, 32, 3)]),
    3: ("VENUSAUR",  (T["Grass"], T["Poison"]), []),
    4: ("CHARMANDER", (T["Fire"],),             [(romspec.EVO_LEVEL, 16, 5)]),
    5: ("CHARMELEON", (T["Fire"],),             [(romspec.EVO_LEVEL, 36, 6)]),
    6: ("CHARIZARD",  (T["Fire"], T["Flying"]), []),
    7: ("SQUIRTLE",   (T["Water"],),            [(romspec.EVO_LEVEL, 16, 8)]),
    8: ("WARTORTLE",  (T["Water"],),            [(romspec.EVO_LEVEL, 36, 9)]),
    9: ("BLASTOISE",  (T["Water"],),            []),
    144: ("ARTICUNO", (T["Ice"], T["Flying"]),  []),   # 1-stage legendary
}
LEGENDARY = 144


@pytest.fixture
def fake_rom():
    data = bytearray(b"\x00" * romspec.ROM_SIZE)
    data[romspec.GAME_CODE_OFFSET:romspec.GAME_CODE_OFFSET + 4] = romspec.GAME_CODE
    rom = Rom(data)

    # A shared, valid dummy learnset every placeholder species can point at.
    scratch = 0x300000
    dummy_off = scratch
    blob = _learnset_blob([(1, 33), (7, 45)])
    rom.data[dummy_off:dummy_off + len(blob)] = blob
    scratch += len(blob)

    for sp in range(romspec.NUM_SPECIES):
        rom.write_base_stats(sp, _bs(50, 50, 50, 50, 50, 50, T["Normal"], T["Normal"]))
        rom.write_name(sp, "DUMMY")
        rom.write_evolutions(sp, [Evolution(0, 0, 0)] * romspec.EVOLUTIONS_PER_SPECIES)
        rom.set_learnset_pointer(sp, dummy_off)

    for sp, (name, types, evos) in SPECIES.items():
        if sp == LEGENDARY:
            bs = _bs(90, 85, 100, 85, 95, 125, types[0], types[1])  # BST 580
        else:
            t2 = types[1] if len(types) > 1 else types[0]
            bs = _bs(60, 62, 63, 60, 80, 80, types[0], t2)
        rom.write_base_stats(sp, bs)
        rom.write_name(sp, name)
        evolist = [Evolution(m, p, t) for (m, p, t) in evos]
        evolist += [Evolution(0, 0, 0)] * (romspec.EVOLUTIONS_PER_SPECIES - len(evolist))
        rom.write_evolutions(sp, evolist)
        own = scratch
        own_blob = _learnset_blob([(1, 33), (7, 45), (13, 52)])
        rom.data[own:own + len(own_blob)] = own_blob
        rom.set_learnset_pointer(sp, own)
        scratch += len(own_blob)

    return rom
