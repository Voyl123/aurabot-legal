"""Apply bitmap-merged fusion sprites + inverted-shiny palettes to the ROM.

For each fused species we composite its sprite with the partner's (partner head
over the species' body), build a shared 16-colour palette, and write:

* a new **front** and **back** sprite,
* a new **normal palette** (the fused colours),
* a new **shiny palette** = the inverted fused colours.

New blobs are appended to ROM free space and the sprite/palette tables are
repointed. Partner sprites are cached, since many families share a partner.
"""

from __future__ import annotations

from . import graphics, romspec
from .rom import Rom

_TABLES = (romspec.FRONT_PIC_TABLE, romspec.BACK_PIC_TABLE, romspec.PALETTE_TABLE)


class SpriteFuser:
    def __init__(self, rom: Rom, split: int = 26) -> None:
        self.rom = rom
        self.split = split
        self._partner_cache: dict[int, tuple[bytes, bytes, bytes]] = {}

    def _partner_gfx(self, species: int) -> tuple[bytes, bytes, bytes] | None:
        if species in self._partner_cache:
            return self._partner_cache[species]
        if not self._has_all(species):
            return None
        gfx = (self.rom.read_gfx(romspec.FRONT_PIC_TABLE, species),
               self.rom.read_gfx(romspec.BACK_PIC_TABLE, species),
               self.rom.read_gfx(romspec.PALETTE_TABLE, species))
        self._partner_cache[species] = gfx
        return gfx

    def _has_all(self, species: int) -> bool:
        return all(self.rom.has_valid_gfx(t, species) for t in _TABLES)

    def fuse(self, species: int, partner_species: int) -> bool:
        """Merge ``species`` with ``partner_species`` and write sprites+palettes.

        Returns False (a no-op) if either side lacks valid graphics."""
        if not self._has_all(species):
            return False
        partner = self._partner_gfx(partner_species)
        if partner is None:
            return False
        base_front = self.rom.read_gfx(romspec.FRONT_PIC_TABLE, species)
        base_back = self.rom.read_gfx(romspec.BACK_PIC_TABLE, species)
        base_pal = self.rom.read_gfx(romspec.PALETTE_TABLE, species)
        p_front, p_back, p_pal = partner

        front, back, pal = graphics.merge_fusion(
            base_front, base_back, base_pal, p_front, p_back, p_pal, self.split)

        self.rom.write_gfx(romspec.FRONT_PIC_TABLE, species, front)
        self.rom.write_gfx(romspec.BACK_PIC_TABLE, species, back)
        self.rom.write_gfx(romspec.PALETTE_TABLE, species, graphics.encode_palette(pal))
        self.rom.write_gfx(romspec.SHINY_PALETTE_TABLE, species,
                           graphics.encode_palette(graphics.invert_palette(pal)))
        return True
