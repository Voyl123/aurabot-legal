"""Orchestration: detect evolution families, fuse each, write the ROM.

This ties the pieces together:

1. Read every real species' name/types from the ROM.
2. Group species into evolution families by walking the evolution table.
3. For each family, pick a random partner family and fuse (types/name/moves)
   consistently across the whole line (see :mod:`pokefusion.fusion`).
4. Write the fused identity back into the base-stats, name and learnset tables.

Everything is driven by a seeded RNG, so a given ``(rom, seed)`` always
produces the same fusions — reproducible patches.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import romspec
from .fusion import Mon, FusedStage, fuse_family
from .rom import Rom
from .spritefuse import SpriteFuser
from .structs import BaseStats, Evolution

# A 1-stage family at or above this base-stat total is treated as a legendary
# for the optional --legendary-evos feature.
LEGENDARY_BST = 540


@dataclass
class FusedLine:
    """Reporting record for one fused family."""

    partner: str
    stages: list[FusedStage]
    extra_evos: list[tuple[int, str, tuple[int, ...]]] = field(default_factory=list)


def _is_real_slot(species: int) -> bool:
    return not (romspec.FIRST_UNUSED_SLOT <= species <= romspec.LAST_UNUSED_SLOT)


def _mon(rom: Rom, species: int) -> Mon:
    bs = rom.read_base_stats(species)
    return Mon(species=species, name=rom.read_name(species), types=bs.types, bst=bs.bst)


def detect_families(rom: Rom) -> list[list[Mon]]:
    """Group real species into evolution families (root first, then descendants)."""
    species = [s for s in range(1, romspec.NUM_SPECIES) if _is_real_slot(s)]
    species_set = set(species)

    evolves_to: dict[int, list[int]] = {}
    targets: set[int] = set()
    for s in species:
        nxt = [e.target for e in rom.read_evolutions(s)
               if e.is_real and e.target in species_set]
        evolves_to[s] = nxt
        targets.update(nxt)

    roots = [s for s in species if s not in targets]
    families: list[list[Mon]] = []
    for root in sorted(roots):                       # sorted → deterministic order
        chain: list[int] = []
        seen: set[int] = set()
        queue = [root]
        while queue:                                 # BFS keeps stage order
            cur = queue.pop(0)
            if cur in seen:
                continue
            seen.add(cur)
            chain.append(cur)
            queue.extend(evolves_to.get(cur, []))
        families.append([_mon(rom, s) for s in chain])
    return families


def _choose_partner(rng: random.Random, roots: list[Mon], exclude: set[int]) -> Mon:
    pool = [m for m in roots if m.species not in exclude]
    return rng.choice(pool or roots)


def _apply_stage(rom: Rom, stage: FusedStage) -> None:
    bs = rom.read_base_stats(stage.species)
    bs.set_types(stage.types)
    rom.write_base_stats(stage.species, bs)
    rom.write_name(stage.species, stage.name)
    if stage.moves:
        rom.inject_learnset_moves(stage.species, list(stage.moves))


def _bump(value: int, factor: float) -> int:
    return max(1, min(255, int(round(value * factor))))


def _grow_legendary(rom: Rom, legend: Mon, base_stage: FusedStage,
                    free_slots: list[int], count: int = 2
                    ) -> list[tuple[int, str, tuple[int, ...]]]:
    """EXPERIMENTAL: give a legendary further evolution stages in unused species
    slots. Wires stats/types/name/evolution/learnset so the line is *data*-valid;
    graphics/Pokédex for these placeholder slots remain glitchy (binary-patch
    limitation). Returns the created ``(species, name, types)`` tuples."""
    created: list[tuple[int, str, tuple[int, ...]]] = []
    legend_learnset = rom._learnset_offset(legend.species)
    base_bs = rom.read_base_stats(legend.species)
    prev = legend.species
    for i in range(count):
        if not free_slots:
            break
        slot = free_slots.pop(0)
        nb = BaseStats.unpack(base_bs.pack())
        factor = 1.12 ** (i + 1)
        nb.hp = _bump(base_bs.hp, factor)
        nb.attack = _bump(base_bs.attack, factor)
        nb.defense = _bump(base_bs.defense, factor)
        nb.speed = _bump(base_bs.speed, factor)
        nb.sp_attack = _bump(base_bs.sp_attack, factor)
        nb.sp_defense = _bump(base_bs.sp_defense, factor)
        nb.set_types(base_stage.types)
        rom.write_base_stats(slot, nb)

        suffix = ("X", "Z")[i] if i < 2 else str(i)
        name = (base_stage.name[:9] + suffix)[:romspec.NAME_LENGTH - 1]
        rom.write_name(slot, name)

        rom.set_learnset_pointer(slot, legend_learnset)

        evos = rom.read_evolutions(prev)
        evos[0] = Evolution(romspec.EVO_LEVEL, 55 + i * 5, slot)
        rom.write_evolutions(prev, evos)

        created.append((slot, name, base_stage.types))
        prev = slot
    return created


def run(rom: Rom, seed: int | None = None, *, legendary_evos: bool = False,
        sprites: bool = False) -> list[FusedLine]:
    """Fuse every family in ``rom`` in place. Returns a report of what changed.

    With ``sprites=True`` each fused species also gets a bitmap-merged sprite
    (partner head over its body) and an inverted-shiny palette.
    """
    rng = random.Random(seed)
    families = detect_families(rom)
    roots = [fam[0] for fam in families]
    free_slots = list(range(romspec.FIRST_UNUSED_SLOT, romspec.LAST_UNUSED_SLOT + 1))
    fuser = SpriteFuser(rom) if sprites else None

    report: list[FusedLine] = []
    for fam in families:
        partner = _choose_partner(rng, roots, exclude={m.species for m in fam})
        stages = fuse_family(fam, partner)
        for stage in stages:
            _apply_stage(rom, stage)
            if fuser is not None:
                fuser.fuse(stage.species, partner.species)

        extra: list[tuple[int, str, tuple[int, ...]]] = []
        if legendary_evos and len(fam) == 1 and fam[0].bst >= LEGENDARY_BST and free_slots:
            extra = _grow_legendary(rom, fam[0], stages[0], free_slots)
            if fuser is not None:
                for slot, _name, _types in extra:
                    fuser.fuse(slot, partner.species)
        report.append(FusedLine(partner=partner.name, stages=stages, extra_evos=extra))
    return report
