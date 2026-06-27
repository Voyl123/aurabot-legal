"""ROM loading + table read/write for FireRed (U) v1.0.

Wraps the 16 MiB ROM image in a mutable buffer and exposes typed accessors for
the four tables we touch: base stats, species names, the evolution table, and
level-up learnsets. On load it *validates* the ROM (game code + MD5) and runs a
cheap self-check (species #1 must decode to ``BULBASAUR`` with sane types) so a
wrong/dirty ROM fails loudly instead of silently corrupting output.
"""

from __future__ import annotations

import hashlib
import struct

from . import gen3text, romspec
from .structs import BaseStats, Evolution


class RomError(Exception):
    """Raised when the ROM fails identity/sanity validation."""


class Rom:
    def __init__(self, data: bytes) -> None:
        self.data = bytearray(data)

    # --- load / save ------------------------------------------------------ #
    @classmethod
    def load(cls, path: str, *, validate: bool = True) -> "Rom":
        with open(path, "rb") as fh:
            rom = cls(fh.read())
        if validate:
            rom.validate()
        return rom

    def save(self, path: str) -> None:
        with open(path, "wb") as fh:
            fh.write(self.data)

    @property
    def md5(self) -> str:
        return hashlib.md5(self.data).hexdigest()

    def validate(self) -> None:
        if len(self.data) != romspec.ROM_SIZE:
            raise RomError(f"unexpected ROM size {len(self.data)} (want {romspec.ROM_SIZE})")
        code = bytes(self.data[romspec.GAME_CODE_OFFSET:romspec.GAME_CODE_OFFSET + 4])
        if code != romspec.GAME_CODE:
            raise RomError(f"game code {code!r} is not FireRed ({romspec.GAME_CODE!r})")
        if self.md5 != romspec.EXPECTED_MD5:
            raise RomError(
                f"MD5 {self.md5} != expected clean FireRed (U) v1.0 "
                f"{romspec.EXPECTED_MD5}; offsets may not match this ROM"
            )
        # Offset self-check: species #1 must be BULBASAUR (Grass/Poison).
        name = self.read_name(1)
        if name.upper() != "BULBASAUR":
            raise RomError(f"self-check failed: species #1 decodes to {name!r}, not BULBASAUR")

    # --- base stats ------------------------------------------------------- #
    def _base_stats_off(self, species: int) -> int:
        return romspec.BASE_STATS_OFFSET + species * romspec.BASE_STATS_ENTRY

    def read_base_stats(self, species: int) -> BaseStats:
        off = self._base_stats_off(species)
        return BaseStats.unpack(self.data[off:off + romspec.BASE_STATS_ENTRY])

    def write_base_stats(self, species: int, stats: BaseStats) -> None:
        off = self._base_stats_off(species)
        self.data[off:off + romspec.BASE_STATS_ENTRY] = stats.pack()

    # --- names ------------------------------------------------------------ #
    def _name_off(self, species: int) -> int:
        return romspec.NAME_OFFSET + species * romspec.NAME_LENGTH

    def read_name(self, species: int) -> str:
        off = self._name_off(species)
        return gen3text.decode(self.data[off:off + romspec.NAME_LENGTH])

    def write_name(self, species: int, name: str) -> None:
        off = self._name_off(species)
        self.data[off:off + romspec.NAME_LENGTH] = gen3text.encode(
            name, romspec.NAME_LENGTH
        )

    # --- evolutions ------------------------------------------------------- #
    def _evo_off(self, species: int) -> int:
        return romspec.EVOLUTION_OFFSET + species * romspec.EVOLUTION_STRIDE

    def read_evolutions(self, species: int) -> list[Evolution]:
        base = self._evo_off(species)
        return [
            Evolution.unpack(self.data[base + i * romspec.EVOLUTION_ENTRY:
                                       base + (i + 1) * romspec.EVOLUTION_ENTRY])
            for i in range(romspec.EVOLUTIONS_PER_SPECIES)
        ]

    def write_evolutions(self, species: int, evolutions: list[Evolution]) -> None:
        base = self._evo_off(species)
        for i, evo in enumerate(evolutions[:romspec.EVOLUTIONS_PER_SPECIES]):
            off = base + i * romspec.EVOLUTION_ENTRY
            self.data[off:off + romspec.EVOLUTION_ENTRY] = evo.pack()

    # --- learnsets -------------------------------------------------------- #
    # Some species (e.g. internal #411, Chimecho) carry a NULL learnset pointer
    # in a clean ROM. A null/garbage pointer dereferences to offset 0 — writing
    # there corrupts the ROM's entry point and bricks it. Treat anything that
    # doesn't land in real ROM data as "no learnset".
    _MIN_LEARNSET_OFFSET = 0x200

    def _learnset_offset(self, species: int) -> int:
        ptr_off = romspec.LEARNSET_TABLE_OFFSET + species * romspec.LEARNSET_POINTER_ENTRY
        ptr = struct.unpack("<I", self.data[ptr_off:ptr_off + 4])[0]
        return romspec.ptr_to_offset(ptr)

    def _has_learnset(self, species: int) -> bool:
        off = self._learnset_offset(species)
        return self._MIN_LEARNSET_OFFSET <= off < len(self.data)

    def read_learnset(self, species: int) -> list[tuple[int, int]]:
        """Return ``[(level, move_id), …]`` from a species' level-up learnset.

        Returns ``[]`` for species whose learnset pointer is null/invalid."""
        if not self._has_learnset(species):
            return []
        off = self._learnset_offset(species)
        out: list[tuple[int, int]] = []
        while True:
            v = struct.unpack("<H", self.data[off:off + 2])[0]
            if v == 0xFFFF:
                break
            out.append((v >> 9, v & 0x1FF))
            off += 2
        return out

    def set_learnset_pointer(self, species: int, target_offset: int) -> None:
        """Point a species' learnset at ``target_offset`` (used to give a freshly
        repurposed species slot a valid, existing learnset)."""
        ptr_off = romspec.LEARNSET_TABLE_OFFSET + species * romspec.LEARNSET_POINTER_ENTRY
        self.data[ptr_off:ptr_off + 4] = struct.pack("<I", romspec.offset_to_ptr(target_offset))

    def inject_learnset_moves(self, species: int, move_ids: list[int]) -> int:
        """Overwrite the move id of the first entries with ``move_ids`` in place.

        Levels are preserved; the list never grows (so no repointing/free-space
        hunting is needed and the diff stays clean). Species with a null/invalid
        learnset pointer are skipped (returns 0) so we never write through a bad
        pointer and corrupt the ROM. Returns how many entries were rewritten.
        """
        if not self._has_learnset(species):
            return 0
        off = self._learnset_offset(species)
        written = 0
        for move in move_ids:
            v = struct.unpack("<H", self.data[off:off + 2])[0]
            if v == 0xFFFF:
                break  # learnset shorter than the moves we wanted to inject
            level = v >> 9
            new_v = (level << 9) | (move & 0x1FF)
            self.data[off:off + 2] = struct.pack("<H", new_v)
            off += 2
            written += 1
        return written
