"""The fusion engine.

Pure logic — no ROM/IO here, so it's trivially unit-testable. Given an
evolution *family* (an ordered list of stages, e.g. Bulbasaur→Ivysaur→Venusaur)
and a randomly chosen *partner* species, it produces a fused identity that is
applied **consistently across every stage** so the resulting evolution line
stays coherent:

* **Types** — the family's base type blended with the partner's (deduped, max
  2). Every stage shares this typing, so a Fire/Ghost stage-1 never evolves into
  something off-theme.
* **Name** — each stage keeps its own root and takes a shared suffix from the
  partner, so the line reads like a real evolutionary family.
* **Skills** — each stage is granted a signature move matching its new typing,
  growing stronger as the line evolves.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import pokedata, romspec


@dataclass(frozen=True)
class Mon:
    """A minimal view of a species, fed in from the ROM (or tests)."""

    species: int
    name: str
    types: tuple[int, ...]   # 1 or 2 Gen III type ids
    bst: int = 0


@dataclass(frozen=True)
class FusedStage:
    """The fused result for one stage of a family."""

    species: int
    name: str
    types: tuple[int, ...]   # 1 or 2 type ids, shared across the whole line
    moves: tuple[int, ...]   # signature move ids to inject (type-matched)


def _valid_types(types: tuple[int, ...]) -> list[int]:
    """Keep only real Gen III types (drops the unused ??? slot, dedups, order-stable)."""
    out: list[int] = []
    for t in types:
        if t in romspec.TYPE_NAMES and t not in out:
            out.append(t)
    return out


def fuse_types(family: list[Mon], partner: Mon) -> tuple[int, ...]:
    """Blend the family's base typing with the partner's, capped at two types."""
    base = _valid_types(family[0].types)
    donor = _valid_types(partner.types)
    fused: list[int] = []
    # Lead with the family's primary, then the partner's primary — the essence
    # of the "fusion". Fill the second slot from whatever distinct type remains.
    for t in ([base[0]] if base else []) + ([donor[0]] if donor else []):
        if t not in fused:
            fused.append(t)
    if len(fused) < 2:
        for t in donor + base:
            if t not in fused:
                fused.append(t)
            if len(fused) == 2:
                break
    return tuple(fused[:2]) if fused else tuple(base[:1] or [romspec.TYPE_IDS["Normal"]])


def _stage_moves(types: tuple[int, ...], power_rank: int) -> tuple[int, ...]:
    """One type-matched signature move per fused type, scaled to the stage."""
    moves: list[int] = []
    for tid in types:
        mv = pokedata.signature_move(romspec.TYPE_NAMES[tid], power_rank)
        if mv is not None and mv not in moves:
            moves.append(mv)
    return tuple(moves)


def fuse_family(family: list[Mon], partner: Mon) -> list[FusedStage]:
    """Fuse a whole evolution family with ``partner``.

    The returned stages line up 1:1 with ``family`` (same species ids, same
    order), all sharing the fused typing for evolutionary coherence.
    """
    if not family:
        raise ValueError("family must have at least one stage")
    types = fuse_types(family, partner)
    stages: list[FusedStage] = []
    for i, mon in enumerate(family):
        stages.append(FusedStage(
            species=mon.species,
            name=pokedata.portmanteau(mon.name, partner.name),
            types=types,
            moves=_stage_moves(types, power_rank=i),
        ))
    return stages
