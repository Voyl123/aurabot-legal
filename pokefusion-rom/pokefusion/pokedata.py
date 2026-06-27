"""Fusion-flavour data and helpers.

Two things live here:

* :data:`MOVES_BY_TYPE` — a curated pool of FireRed move ids per type, ordered
  weakest→strongest, used to grant a fused species a signature move that
  matches its new typing. (All ids are valid FRLG moves, so even an imperfect
  pick can never corrupt the learnset — worst case it's a different move of the
  right flavour.)
* name helpers — split species names into fragments and build portmanteaus for
  fused names.
"""

from __future__ import annotations

# Move ids are FireRed/LeafGreen internal indices, ordered weak → strong so a
# later evolution stage can be granted a stronger move of the same type.
MOVES_BY_TYPE: dict[str, list[int]] = {
    "Normal":   [33, 129, 34, 63],     # Tackle, Swift, Body Slam, Hyper Beam
    "Fire":     [52, 53, 126],         # Ember, Flamethrower, Fire Blast
    "Water":    [55, 57, 56],          # Water Gun, Surf, Hydro Pump
    "Electric": [84, 85, 87],          # Thunder Shock, Thunderbolt, Thunder
    "Grass":    [22, 75, 76],          # Vine Whip, Razor Leaf, Solar Beam
    "Ice":      [181, 58, 59],         # Powder Snow, Ice Beam, Blizzard
    "Fighting": [2, 280, 238],         # Karate Chop, Brick Break, Cross Chop
    "Poison":   [51, 124, 188],        # Acid, Sludge, Sludge Bomb
    "Ground":   [189, 91, 89],         # Mud-Slap, Dig, Earthquake
    "Flying":   [16, 17, 332],         # Gust, Wing Attack, Aerial Ace
    "Psychic":  [93, 60, 94],          # Confusion, Psybeam, Psychic
    "Bug":      [141, 42, 224],        # Leech Life, Pin Missile, Megahorn
    "Rock":     [88, 157, 246],        # Rock Throw, Rock Slide, Ancient Power
    "Ghost":    [310, 101, 247],       # Astonish, Night Shade, Shadow Ball
    "Dragon":   [239, 225, 337],       # Twister, Dragon Breath, Dragon Claw
    "Dark":     [44, 185, 242],        # Bite, Faint Attack, Crunch
    "Steel":    [232, 211, 231],       # Metal Claw, Steel Wing, Iron Tail
}


def signature_move(type_name: str, power_rank: int) -> int | None:
    """A type's move at a given power rank (0=weak), clamped to what's available."""
    pool = MOVES_BY_TYPE.get(type_name)
    if not pool:
        return None
    return pool[min(power_rank, len(pool) - 1)]


# --------------------------------------------------------------------------- #
# Name fragment helpers — build readable portmanteau fusion names
# --------------------------------------------------------------------------- #
def name_head(name: str, head_chars: int | None = None) -> str:
    """The leading fragment of a name (Title-cased), e.g. ``BULBASAUR`` → ``Bulba``.

    ``head_chars`` overrides the default half-length cut — used to lengthen the
    root until sibling evolution stages get distinct fused names."""
    n = name.strip().title()
    cut = head_chars if head_chars is not None else max(2, (len(n) + 1) // 2)
    return n[:max(2, cut)]


def name_tail(name: str) -> str:
    """The trailing fragment of a name (lower-cased), e.g. ``GASTLY`` → ``tly``."""
    n = name.strip().lower()
    cut = max(2, len(n) // 2)
    return n[cut:] or n[-2:]


def portmanteau(head_name: str, tail_name: str, max_len: int = 10,
                head_chars: int | None = None) -> str:
    """Fuse two names: front of ``head_name`` + back of ``tail_name``.

    Capped at ``max_len`` (FireRed names hold 10 characters).
    """
    fused = name_head(head_name, head_chars) + name_tail(tail_name)
    fused = fused[:max_len]
    return fused or head_name[:max_len].title()


def unique_portmanteau(head_name: str, tail_name: str, taken: set[str],
                       max_len: int = 10) -> str:
    """A portmanteau that avoids names already in ``taken``.

    Lengthens the head root one character at a time (the part that distinguishes
    sibling evolution stages, e.g. CHAR**M**ANDER vs CHAR**M**ELEON) until the
    fused name is unique; falls back to a numeric suffix if it still collides.
    """
    for head_chars in range(max(2, (len(head_name) + 1) // 2), len(head_name) + 1):
        cand = portmanteau(head_name, tail_name, max_len, head_chars)
        if cand and cand not in taken:
            return cand
    base = portmanteau(head_name, tail_name, max_len - 1)
    n = 2
    while f"{base}{n}"[:max_len] in taken:
        n += 1
    return f"{base}{n}"[:max_len]
