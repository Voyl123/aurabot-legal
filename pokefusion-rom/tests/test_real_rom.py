"""Integration test against a real clean FireRed (U) v1.0 ROM.

Skips unless a ROM is provided via the ``POKEFUSION_TEST_ROM`` env var (CI and
other machines won't have one — no copyrighted data is committed).
"""

import copy
import os

import pytest

from pokefusion import romspec
from pokefusion.patch import apply_ips, build_ips
from pokefusion.randomizer import detect_families, run
from pokefusion.rom import Rom

ROM_PATH = os.environ.get("POKEFUSION_TEST_ROM")
pytestmark = pytest.mark.skipif(
    not (ROM_PATH and os.path.exists(ROM_PATH)),
    reason="set POKEFUSION_TEST_ROM to a clean FireRed (U) v1.0 ROM to run",
)


def _load():
    return Rom.load(ROM_PATH)        # validate=True → exercises MD5 + self-check


def test_validation_passes_and_self_check():
    rom = _load()
    assert rom.read_name(1).upper() == "BULBASAUR"
    assert rom.read_name(4).upper() == "CHARMANDER"


def test_detects_starter_families():
    fams = {tuple(m.species for m in f) for f in detect_families(_load())}
    assert (1, 2, 3) in fams
    assert (4, 5, 6) in fams
    assert (7, 8, 9) in fams


def test_full_run_keeps_lines_coherent():
    rom = _load()
    run(rom, seed=42)
    for line in [(1, 2, 3), (4, 5, 6), (7, 8, 9)]:
        types = {rom.read_base_stats(sp).types for sp in line}
        assert len(types) == 1


def test_ips_roundtrip_reproduces_patched_rom():
    rom = _load()
    original = bytes(rom.data)
    run(rom, seed=42)
    patched = bytes(rom.data)
    ips = build_ips(original, patched)
    assert apply_ips(original, ips) == patched
