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
# Used to populate the autocomplete / dropdown in the /create flow.
ACTIVITIES: list[str] = [
    "Open World Boss",
    "Field Boss",
    "Archboss",
    "Dungeon — Syleus's Abyss",
    "Dungeon — Cave of Destruction",
    "Dungeon — Temple of Slaughter",
    "Dungeon — Saurodoma Island",
    "Dungeon — Carmine Vault",
    "Dungeon — Shattered Temple",
    "Tax Delivery Run",
    "Guild / GvG Event",
    "Arena / PvP",
    "Riftstone Contract",
    "Co-op Dungeon (any)",
    "Custom / Other",
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


# Difficulty options offered when creating a party.
DIFFICULTIES: list[str] = ["Normal", "Hard", "Any", "Learning / Chill"]
