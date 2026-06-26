"""Weapons → class title.

Throne and Liberty has no fixed classes — your "class" is your two-weapon combo.
This module normalises free-text weapon input (abbreviations welcome) and maps a
combo to a popular community build name, falling back to the abbreviated combo
(e.g. ``GS/Dagger``) when there's no well-known name.
"""

from __future__ import annotations

# Canonical weapon names.
GREATSWORD = "Greatsword"
SWORD = "Sword & Shield"
DAGGERS = "Daggers"
CROSSBOWS = "Crossbows"
LONGBOW = "Longbow"
STAFF = "Staff"
WAND = "Wand & Tome"
SPEAR = "Spear"

# Short label used in the combo display.
ABBR: dict[str, str] = {
    GREATSWORD: "GS",
    SWORD: "SnS",
    DAGGERS: "Dagger",
    CROSSBOWS: "Xbow",
    LONGBOW: "Bow",
    STAFF: "Staff",
    WAND: "Wand",
    SPEAR: "Spear",
}

# Aliases (lower-cased) → canonical name.
_ALIASES: dict[str, str] = {
    "greatsword": GREATSWORD, "great sword": GREATSWORD, "gs": GREATSWORD, "2h": GREATSWORD,
    "sword & shield": SWORD, "sword and shield": SWORD, "sns": SWORD, "snb": SWORD,
    "sword": SWORD, "shield": SWORD, "s&s": SWORD,
    "dagger": DAGGERS, "daggers": DAGGERS, "dag": DAGGERS, "dg": DAGGERS, "knives": DAGGERS,
    "crossbow": CROSSBOWS, "crossbows": CROSSBOWS, "xbow": CROSSBOWS, "xb": CROSSBOWS, "cbow": CROSSBOWS,
    "longbow": LONGBOW, "long bow": LONGBOW, "bow": LONGBOW, "lb": LONGBOW,
    "staff": STAFF, "stave": STAFF,
    "wand & tome": WAND, "wand and tome": WAND, "wand": WAND, "tome": WAND, "w&t": WAND,
    "spear": SPEAR, "lance": SPEAR, "polearm": SPEAR,
}

# Community build names per combo (order-independent). Best-effort — unknown
# combos simply display as the abbreviated weapon pair.
_COMBO_NAMES: dict[frozenset, str] = {
    frozenset({GREATSWORD, SWORD}): "Juggernaut",
    frozenset({SWORD, WAND}): "Paladin",
    frozenset({SWORD, LONGBOW}): "Vanguard",
    frozenset({SWORD, DAGGERS}): "Sentinel",
    frozenset({SWORD, STAFF}): "Warlock",
    frozenset({SWORD, CROSSBOWS}): "Gunlancer",
    frozenset({GREATSWORD, DAGGERS}): "Bladedancer",
    frozenset({GREATSWORD, LONGBOW}): "Skirmisher",
    frozenset({GREATSWORD, STAFF}): "Spellblade",
    frozenset({GREATSWORD, WAND}): "Crusader",
    frozenset({GREATSWORD, CROSSBOWS}): "Gunbreaker",
    frozenset({DAGGERS, LONGBOW}): "Ranger",
    frozenset({DAGGERS, CROSSBOWS}): "Cutthroat",
    frozenset({DAGGERS, STAFF}): "Nightshade",
    frozenset({DAGGERS, WAND}): "Trickster",
    frozenset({LONGBOW, CROSSBOWS}): "Sharpshooter",
    frozenset({LONGBOW, STAFF}): "Stormbringer",
    frozenset({LONGBOW, WAND}): "Liberator",
    frozenset({STAFF, WAND}): "Sage",
    frozenset({CROSSBOWS, STAFF}): "Arcanist",
    frozenset({CROSSBOWS, WAND}): "Marksman",
    frozenset({SPEAR, SWORD}): "Dragoon",
    frozenset({SPEAR, DAGGERS}): "Lancer",
    frozenset({SPEAR, GREATSWORD}): "Warlord",
    frozenset({SPEAR, STAFF}): "Valkyrie",
    frozenset({SPEAR, WAND}): "Templar",
    frozenset({SPEAR, LONGBOW}): "Hunter",
    frozenset({SPEAR, CROSSBOWS}): "Harrier",
}


def parse_weapons(text: str | None) -> list[str]:
    """Normalise free text like ``"gs/dagger"`` into up to two canonical weapons."""
    if not text:
        return []
    # Split on common separators (but not "&", which appears inside "Sword & Shield").
    for sep in ("+", ",", "|", " / "):
        text = text.replace(sep, "/")
    out: list[str] = []
    for tok in text.split("/"):
        canon = _ALIASES.get(tok.strip().lower())
        if canon and canon not in out:
            out.append(canon)
        if len(out) == 2:
            break
    return out


def class_title(weapons: list[str]) -> str:
    """A short class title for a weapon combo, or '' if no weapons given."""
    if not weapons:
        return ""
    if len(weapons) == 1:
        return ABBR.get(weapons[0], weapons[0])
    combo = "/".join(ABBR.get(w, w) for w in weapons[:2])
    name = _COMBO_NAMES.get(frozenset(weapons[:2]))
    return f"{name} ({combo})" if name else combo
