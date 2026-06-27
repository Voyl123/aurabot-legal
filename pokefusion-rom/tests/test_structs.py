"""BaseStats / Evolution pack-unpack symmetry."""

from pokefusion import romspec
from pokefusion.structs import BaseStats, Evolution


def test_base_stats_roundtrip_preserves_all_bytes():
    raw = bytes(range(romspec.BASE_STATS_ENTRY))  # 0..27
    bs = BaseStats.unpack(raw)
    assert bs.pack() == raw                       # tail preserved verbatim


def test_base_stats_types_property():
    dual = BaseStats(50, 50, 50, 50, 50, 50, 12, 3, tail=bytes(20))
    mono = BaseStats(50, 50, 50, 50, 50, 50, 10, 10, tail=bytes(20))
    assert dual.types == (12, 3)
    assert mono.types == (10,)


def test_base_stats_set_types_mono_duplicates():
    bs = BaseStats(50, 50, 50, 50, 50, 50, 0, 0, tail=bytes(20))
    bs.set_types((11,))
    assert (bs.type1, bs.type2) == (11, 11)
    bs.set_types((10, 16))
    assert (bs.type1, bs.type2) == (10, 16)


def test_base_stats_bst():
    bs = BaseStats(10, 20, 30, 40, 50, 60, 0, 0, tail=bytes(20))
    assert bs.bst == 210


def test_evolution_roundtrip_and_is_real():
    evo = Evolution(romspec.EVO_LEVEL, 16, 2)
    assert Evolution.unpack(evo.pack()) == evo
    assert evo.is_real
    assert not Evolution(0, 0, 0).is_real
