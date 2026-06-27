"""Binary struct (un)packers for FireRed data tables.

Each dataclass mirrors an on-ROM struct. Fields we don't touch are preserved
verbatim (see ``BaseStats.tail``) so re-packing an unmodified entry reproduces
the original bytes exactly — important for clean diffs/patches.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from . import romspec


@dataclass
class BaseStats:
    """gBaseStats entry — 28 bytes. We expose the stats + types; the remaining
    20 bytes (catch rate, abilities, egg groups, …) are kept untouched."""

    hp: int
    attack: int
    defense: int
    speed: int
    sp_attack: int
    sp_defense: int
    type1: int
    type2: int
    tail: bytes  # bytes 8..28, preserved verbatim

    @classmethod
    def unpack(cls, raw: bytes) -> "BaseStats":
        if len(raw) != romspec.BASE_STATS_ENTRY:
            raise ValueError(f"base stats entry must be {romspec.BASE_STATS_ENTRY} bytes")
        return cls(
            hp=raw[0], attack=raw[1], defense=raw[2], speed=raw[3],
            sp_attack=raw[4], sp_defense=raw[5], type1=raw[6], type2=raw[7],
            tail=bytes(raw[8:]),
        )

    def pack(self) -> bytes:
        head = bytes([
            self.hp & 0xFF, self.attack & 0xFF, self.defense & 0xFF,
            self.speed & 0xFF, self.sp_attack & 0xFF, self.sp_defense & 0xFF,
            self.type1 & 0xFF, self.type2 & 0xFF,
        ])
        return head + self.tail

    @property
    def bst(self) -> int:
        return (self.hp + self.attack + self.defense
                + self.speed + self.sp_attack + self.sp_defense)

    @property
    def types(self) -> tuple[int, ...]:
        """Distinct type ids (one entry for mono-typed species)."""
        return (self.type1,) if self.type1 == self.type2 else (self.type1, self.type2)

    def set_types(self, types: tuple[int, ...]) -> None:
        """Apply 1 or 2 type ids; mono-type duplicates type1 into type2."""
        if not types:
            raise ValueError("need at least one type")
        self.type1 = types[0]
        self.type2 = types[1] if len(types) > 1 else types[0]


@dataclass
class Evolution:
    """One gEvolutionTable entry — 8 bytes (method, param, target, padding)."""

    method: int
    param: int
    target: int
    pad: int = 0

    @classmethod
    def unpack(cls, raw: bytes) -> "Evolution":
        method, param, target, pad = struct.unpack("<HHHH", raw)
        return cls(method, param, target, pad)

    def pack(self) -> bytes:
        return struct.pack("<HHHH", self.method, self.param, self.target, self.pad)

    @property
    def is_real(self) -> bool:
        return self.method != romspec.EVO_NONE and self.target != 0
