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

    # ---- T1 · 1-Star Co-op Dungeons (1600 CP) ----------------------------- #
    "★ T1 · Syleus's Abyss",
    "★ T1 · Saurodoma Island",
    "★ T1 · Temple of Slaughter",
    "★ T1 · Butcher's Canyon",
    "★ T1 · Cave of Destruction",
    "★ T1 · Shattered Temple",

    # ---- T2 · 2-Star Co-op Dungeons (2500 CP) ----------------------------- #
    "★★ T2 · Carmine Rage Island",
    "★★ T2 · Island of Terror",
    "★★ T2 · Valley of Slaughter",
    "★★ T2 · Voidwastes",
    "★★ T2 · Torture Chamber of Screams",

    # ---- T3 · 3-Star Co-op Dungeons (3500 CP · Lv55) ---------------------- #
    "★★★ T3 · Tyrant's Isle",
    "★★★ T3 · Twisted Laboratory",
    "★★★ T3 · Rancorwood",
    "★★★ T3 · Halls of Tragedy",
    "★★★ T3 · Chapel of Madness",
    "★★★ T3 · Doomrot Grove",

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

# Specs / playstyles a party can ask for, and that players list as preferences.
# A party with no spec set means "don't mind".
SPECS: list[str] = [
    "Tank",
    "Healer",
    "DPS",
    "Bomber",
    "Support",
    "PvP",
    "PvE",
]
