"""ROM specification for Pokémon FireRed (U) v1.0.

Every game-specific constant lives here so the rest of the codebase stays
ROM-agnostic. **All offsets below were verified by signature-scanning a clean
FireRed (U) v1.0 ROM** (game code ``BPRE``, MD5 ``e26ee0d4…``), not copied
blindly from a reference — the commonly-cited base-stats offset ``0x2547F4`` is
actually wrong for this ROM, which is exactly why we validate.

If you ever need to support another revision/region, this is the only file
that should change.
"""

from __future__ import annotations

# --- ROM identity --------------------------------------------------------- #
GAME_CODE = b"BPRE"                 # bytes 0xAC..0xB0 of the GBA header
GAME_CODE_OFFSET = 0xAC
EXPECTED_MD5 = "e26ee0d44e809351c8ce2d73c7400cdd"
ROM_SIZE = 16 * 1024 * 1024         # 16 MiB

# --- Pointer encoding ----------------------------------------------------- #
ROM_BASE = 0x08000000               # GBA maps the cartridge here
POINTER_MASK = 0x01FFFFFF           # strip the base to get a file offset


def ptr_to_offset(ptr: int) -> int:
    """GBA ROM pointer → file offset."""
    return ptr & POINTER_MASK


def offset_to_ptr(offset: int) -> int:
    """File offset → GBA ROM pointer."""
    return (offset & POINTER_MASK) | ROM_BASE


# --- Species count -------------------------------------------------------- #
# FireRed has 412 internal species slots (0 = SPECIES_NONE). Indices 252..276
# are unused placeholder ("?") slots.
NUM_SPECIES = 412
FIRST_UNUSED_SLOT = 252             # 252..276 are the placeholder slots
LAST_UNUSED_SLOT = 276

# --- Table offsets (verified) --------------------------------------------- #
BASE_STATS_OFFSET = 0x254784        # gBaseStats[]      — 28 bytes/entry
BASE_STATS_ENTRY = 28

EVOLUTION_OFFSET = 0x259754         # gEvolutionTable[] — 5 × 8 bytes/species
EVOLUTION_ENTRY = 8                 # one evolution entry
EVOLUTIONS_PER_SPECIES = 5
EVOLUTION_STRIDE = EVOLUTION_ENTRY * EVOLUTIONS_PER_SPECIES  # 40

NAME_OFFSET = 0x245EE0              # gSpeciesNames[]   — 11 bytes/entry
NAME_LENGTH = 11                   # 10 chars + EOS

LEARNSET_TABLE_OFFSET = 0x25D7B8   # gLevelUpLearnsets[] — 4-byte pointers
LEARNSET_POINTER_ENTRY = 4

# --- Evolution method ids (subset we care about) -------------------------- #
EVO_NONE = 0x0000
EVO_LEVEL = 4                       # plain level-up evolution

# --- Type ids (Gen III internal order) ------------------------------------ #
# NOTE: id 9 ("???"/Mystery) is unused, and there is NO Fairy type in Gen III.
TYPE_IDS: dict[str, int] = {
    "Normal": 0, "Fighting": 1, "Flying": 2, "Poison": 3, "Ground": 4,
    "Rock": 5, "Bug": 6, "Ghost": 7, "Steel": 8,
    "Fire": 10, "Water": 11, "Grass": 12, "Electric": 13, "Psychic": 14,
    "Ice": 15, "Dragon": 16, "Dark": 17,
}
TYPE_NAMES: dict[int, str] = {v: k for k, v in TYPE_IDS.items()}
