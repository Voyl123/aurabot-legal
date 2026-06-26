"""Static configuration for the Throne and Liberty party bot.

Everything that designers / server owners might want to tweak lives here:
the role definitions, the activity (dungeon / boss) list and the colour
palette used for the embeds.
"""

from __future__ import annotations

from dataclasses import dataclass


# --------------------------------------------------------------------------- #
# Roles
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Role:
    key: str          # internal id, also used in button custom_ids
    label: str        # human readable name
    emoji: str        # shown on the button / embed
    default_slots: int


# The three classic trinity roles used by Throne and Liberty group content.
ROLES: dict[str, Role] = {
    "tank": Role("tank", "Tank", "🛡️", 1),
    "healer": Role("healer", "Healer", "💚", 1),
    "dps": Role("dps", "DPS", "⚔️", 4),
}

# Order the roles appear in, in embeds and on the button row.
ROLE_ORDER: list[str] = ["tank", "healer", "dps"]


# --------------------------------------------------------------------------- #
# Activities (what the party is actually for)
# --------------------------------------------------------------------------- #
# Used to populate the autocomplete in the /create flow. Grouped by content
# type and ordered roughly by the Combat Power (CP) needed to enter, so the
# list doubles as a quick gear-check reference. The ★ count is the in-game
# Dimensional Circle difficulty tier.
ACTIVITIES: list[str] = [
    # ---- 12-player Raids -------------------------------------------------- #
    "⚔️ Raid — Altar of Calanthia (12p · 5000+ CP)",

    # ---- 1-Star Co-op Dungeons (1600 CP) ---------------------------------- #
    "★ Syleus's Abyss (1-Star)",
    "★ Saurodoma Island (1-Star)",
    "★ Temple of Slaughter (1-Star)",
    "★ Butcher's Canyon (1-Star)",
    "★ Cave of Destruction (1-Star)",
    "★ Shattered Temple (1-Star)",

    # ---- 2-Star Co-op Dungeons (2500 CP) ---------------------------------- #
    "★★ Carmine Rage Island (2-Star)",
    "★★ Island of Terror (2-Star)",
    "★★ Valley of Slaughter (2-Star)",
    "★★ Voidwastes (2-Star)",
    "★★ Torture Chamber of Screams (2-Star)",

    # ---- 3-Star Co-op Dungeons (3500 CP · Lv55) --------------------------- #
    "★★★ Tyrant's Isle (3-Star)",
    "★★★ Twisted Laboratory (3-Star)",
    "★★★ Rancorwood (3-Star)",
    "★★★ Halls of Tragedy (3-Star)",
    "★★★ Chapel of Madness (3-Star)",
    "★★★ Doomrot Grove (3-Star)",

    # ---- Endgame Co-op (5500 CP) ------------------------------------------ #
    "🔥 Hellfire Crucible (5500 CP)",
    "🔥 Deathless Queen's Lair (5500 CP)",

    # ---- Archbosses & world content --------------------------------------- #
    "👑 Archboss — Queen Bellandir",
    "👑 Archboss — Courte's Wraith Tevent",
    "👑 Archboss — Deluzhnoa",
    "👑 Archboss — Giant Cordy",
    "👑 Ascended Archboss",
    "🌍 Field Boss",
    "🌍 Open World Boss",
    "🏰 Guild Raid Boss",

    # ---- PvP / misc ------------------------------------------------------- #
    "🚚 Tax Delivery Run",
    "⚔️ GvG / Guild War",
    "🏹 Arena / PvP",
    "🗺️ Battlegrounds",
    "❓ Custom / Other",
]


# --------------------------------------------------------------------------- #
# Theming
# --------------------------------------------------------------------------- #
class Colors:
    # Discord int colours
    OPEN = 0x5865F2      # blurple   — party still recruiting
    FULL = 0x57F287      # green     — party is full / ready
    CLOSED = 0xED4245    # red       — party disbanded
    ACCENT = 0xFEE75C    # yellow    — info / accents


# Difficulty options offered when creating a party. Co-op dungeons use
# Normal / Elite / Epic; the 12-player raid uses Normal / Hard.
DIFFICULTIES: list[str] = [
    "Normal",
    "Elite",
    "Epic",
    "Hard",
    "Any",
    "Learning / Chill",
]
