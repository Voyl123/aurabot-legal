"""End-to-end randomizer behaviour on the synthetic ROM."""

from pokefusion import romspec
from pokefusion.randomizer import detect_families, run

T = romspec.TYPE_IDS


def _family_species(rom):
    return {tuple(m.species for m in fam) for fam in detect_families(rom)}


def test_detects_three_stage_families(fake_rom):
    fams = _family_species(fake_rom)
    assert (1, 2, 3) in fams       # Bulbasaur line
    assert (4, 5, 6) in fams       # Charmander line
    assert (7, 8, 9) in fams       # Squirtle line
    assert (144,) in fams          # lone legendary


def test_run_makes_each_line_share_one_typing(fake_rom):
    run(fake_rom, seed=42)
    for line in [(1, 2, 3), (4, 5, 6), (7, 8, 9)]:
        types = {fake_rom.read_base_stats(sp).types for sp in line}
        assert len(types) == 1, f"line {line} has inconsistent typing {types}"


def test_run_rewrites_names_decodably(fake_rom):
    run(fake_rom, seed=42)
    for sp in (1, 2, 3, 4, 5, 6):
        name = fake_rom.read_name(sp)
        assert name and "?" not in name      # clean, decodable name


def test_run_is_deterministic_for_a_seed(fake_rom):
    import copy
    rom_a = fake_rom
    rom_b = copy.deepcopy(fake_rom)
    run(rom_a, seed=123)
    run(rom_b, seed=123)
    assert rom_a.data == rom_b.data


def test_different_seeds_differ(fake_rom):
    import copy
    rom_b = copy.deepcopy(fake_rom)
    run(fake_rom, seed=1)
    run(rom_b, seed=2)
    assert fake_rom.data != rom_b.data


def test_injected_moves_are_present(fake_rom):
    run(fake_rom, seed=42)
    moves = [mv for _lvl, mv in fake_rom.read_learnset(1)]
    types = fake_rom.read_base_stats(1).types
    from pokefusion.pokedata import MOVES_BY_TYPE
    expected = set()
    for tid in types:
        expected |= set(MOVES_BY_TYPE[romspec.TYPE_NAMES[tid]])
    assert expected & set(moves)             # a type-matched move was injected


def test_legendary_evos_wires_new_stage(fake_rom):
    run(fake_rom, seed=7, legendary_evos=True)
    evo = fake_rom.read_evolutions(144)[0]
    assert evo.is_real                        # legendary now evolves
    target = evo.target
    assert romspec.FIRST_UNUSED_SLOT <= target <= romspec.LAST_UNUSED_SLOT
    # the new stage shares the legendary's fused typing
    assert fake_rom.read_base_stats(target).types == fake_rom.read_base_stats(144).types


def test_legendary_evos_off_by_default(fake_rom):
    run(fake_rom, seed=7)
    assert not fake_rom.read_evolutions(144)[0].is_real
