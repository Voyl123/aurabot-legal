"""Fusion engine: type blending, name portmanteaus, coherent 3-stage lines."""

from pokefusion import romspec
from pokefusion.fusion import Mon, fuse_family, fuse_types

T = romspec.TYPE_IDS


def _line(*mons):
    return list(mons)


def test_fuse_types_caps_at_two_and_dedups():
    fam = _line(Mon(1, "BULBASAUR", (T["Grass"], T["Poison"])))
    partner = Mon(7, "SQUIRTLE", (T["Water"],))
    fused = fuse_types(fam, partner)
    assert len(fused) <= 2
    assert len(set(fused)) == len(fused)
    assert fused[0] == T["Grass"]          # family primary leads
    assert T["Water"] in fused             # partner primary joins


def test_fuse_types_leads_with_family_then_partner():
    fam = _line(Mon(4, "CHARMANDER", (T["Fire"],)))
    partner = Mon(25, "PIKACHU", (T["Electric"],))
    assert fuse_types(fam, partner) == (T["Fire"], T["Electric"])


def test_fuse_types_all_valid_gen3_types():
    fam = _line(Mon(1, "X", (T["Ghost"], T["Poison"])))
    partner = Mon(2, "Y", (T["Fire"],))
    for tid in fuse_types(fam, partner):
        assert tid in romspec.TYPE_NAMES


def test_fuse_family_shares_typing_across_all_stages():
    fam = _line(
        Mon(1, "BULBASAUR", (T["Grass"], T["Poison"])),
        Mon(2, "IVYSAUR", (T["Grass"], T["Poison"])),
        Mon(3, "VENUSAUR", (T["Grass"], T["Poison"])),
    )
    partner = Mon(92, "GASTLY", (T["Ghost"], T["Poison"]))
    stages = fuse_family(fam, partner)
    assert len(stages) == 3
    assert {s.types for s in stages} == {stages[0].types}   # identical line typing
    assert [s.species for s in stages] == [1, 2, 3]         # species/order preserved


def test_fuse_family_names_are_portmanteaus():
    fam = _line(Mon(4, "CHARMANDER", (T["Fire"],)))
    partner = Mon(92, "GASTLY", (T["Ghost"], T["Poison"]))
    name = fuse_family(fam, partner)[0].name
    assert name.lower().startswith("char")     # keeps its own root
    assert name.lower().endswith("tly")         # takes the partner suffix
    assert 0 < len(name) <= 10


def test_fuse_family_moves_match_types_and_grow():
    fam = _line(
        Mon(4, "CHARMANDER", (T["Fire"],)),
        Mon(5, "CHARMELEON", (T["Fire"],)),
        Mon(6, "CHARIZARD", (T["Fire"], T["Flying"])),
    )
    partner = Mon(7, "SQUIRTLE", (T["Water"],))   # fused → Fire/Water
    stages = fuse_family(fam, partner)
    from pokefusion.pokedata import MOVES_BY_TYPE
    valid = set(MOVES_BY_TYPE["Fire"]) | set(MOVES_BY_TYPE["Water"])
    for st in stages:
        assert st.moves                       # every stage gets a signature move
        assert set(st.moves).issubset(valid)  # …matching the fused typing
    # Stage 3 should reach a stronger Fire move than stage 1.
    fire = MOVES_BY_TYPE["Fire"]
    assert fire.index(stages[2].moves[0]) >= fire.index(stages[0].moves[0])


def test_fuse_single_stage_legendary():
    fam = _line(Mon(144, "ARTICUNO", (T["Ice"], T["Flying"])))
    partner = Mon(150, "MEWTWO", (T["Psychic"],))
    stages = fuse_family(fam, partner)
    assert len(stages) == 1
    assert stages[0].types[0] == T["Ice"]
    assert T["Psychic"] in stages[0].types
