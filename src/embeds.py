"""Embed rendering — turns a :class:`Party` into the rich UI message.

The goal is a card that reads at a glance: a status line, a fill bar, a single
compact meta row (difficulty · gear · voice · start), then one tidy column per
role with the roster.
"""

from __future__ import annotations

import datetime as dt

import discord

from . import config
from . import weapons as weapons_mod
from .party import Party
from .timeparse import humanize_duration


def _fill_bar(size: int, capacity: int, width: int = 12) -> str:
    """A little progress bar, e.g. ``▰▰▰▱▱▱``. One block per slot when it fits."""
    if capacity <= 0:
        return ""
    width = min(capacity, width)
    filled = min(width, round(size / capacity * width))
    return "▰" * filled + "▱" * (width - filled)


def _roster_block(party: Party, role_key: str) -> str:
    """The list of members (+ open slots) shown under a role column."""
    lines: list[str] = []
    for m in party.members_for(role_key):
        crown = "👑 " if m.user_id == party.leader_id else ""
        extras = []
        title = weapons_mod.class_title(m.weapons)
        if title:
            extras.append(title)
        if m.specs:
            extras.append("/".join(m.specs))
        if m.gear_score:
            extras.append(f"`{m.gear_score:,}`")
        suffix = (" · " + " · ".join(extras)) if extras else ""
        lines.append(f"{crown}<@{m.user_id}>{suffix}")
    for _ in range(party.open_slots(role_key)):
        lines.append("`+ open`")
    return "\n".join(lines) if lines else "`—`"


def build_party_embed(party: Party) -> discord.Embed:
    if party.closed:
        color = config.Colors.CLOSED
        status = "🔒 **Disbanded**"
    elif party.is_full:
        color = config.Colors.FULL
        status = "✅ **Full — ready to go!**"
    else:
        color = config.Colors.OPEN
        status = "🟢 **Recruiting**"

    # --- Header: status + fill bar ---------------------------------------- #
    description_lines = [
        status,
        f"{_fill_bar(party.size, party.capacity)}  `{party.size}/{party.capacity}`",
        "",
    ]

    # --- One compact meta row --------------------------------------------- #
    meta = [f"🎮 {party.difficulty}"]
    if party.min_gear_score:
        meta.append(f"⚡ {party.min_gear_score:,}+ CP")
    meta.append(f"🧭 {party.required_spec}" if party.required_spec else "🧭 any spec")
    if party.runs:
        meta.append(f"🔁 {party.runs} run{'s' if party.runs != 1 else ''}")
    if party.voice_channel_id:
        meta.append(f"🔊 <#{party.voice_channel_id}>")
    elif party.voice_link:
        meta.append(f"🔊 [Voice]({party.voice_link})")
    description_lines.append(" · ".join(meta))

    if party.start_at:
        ts = int(party.start_at)
        # Discord renders <t:..> in each viewer's own timezone; :R auto-counts down.
        description_lines.append(f"🕒 <t:{ts}:f> · <t:{ts}:R>")

    if party.duration_seconds:
        line = f"⏳ Running for {humanize_duration(party.duration_seconds)}"
        if party.end_at and not party.closed:
            line += f" · ends <t:{int(party.end_at)}:R>"
        description_lines.append(line)

    embed = discord.Embed(
        title=party.activity,
        description="\n".join(description_lines),
        color=color,
        timestamp=dt.datetime.fromtimestamp(party.created_at, tz=dt.timezone.utc),
    )
    embed.set_author(name=f"Party Finder · led by {party.leader_name}")

    # --- One column per role ---------------------------------------------- #
    for role_key in config.ROLE_ORDER:
        total = party.slots.get(role_key, 0)
        if total == 0:
            continue
        role = config.ROLES[role_key]
        filled = len(party.members_for(role_key))
        embed.add_field(
            name=f"{role.emoji} {role.label} · {filled}/{total}",
            value=_roster_block(party, role_key),
            inline=True,
        )

    # --- Other dungeons this party is also running ------------------------ #
    if party.extra_activities:
        embed.add_field(
            name="🎯 Also running",
            value="\n".join(f"• {a}" for a in party.extra_activities),
            inline=False,
        )

    # --- What's still needed ---------------------------------------------- #
    if not party.closed and not party.is_full:
        needs = [
            f"{config.ROLES[r].emoji} **{party.open_slots(r)}** {config.ROLES[r].label}"
            for r in config.ROLE_ORDER
            if party.open_slots(r) > 0
        ]
        embed.add_field(name="🔎 Still need", value=" · ".join(needs), inline=False)

    if party.notes:
        embed.add_field(name="📝 Notes", value=party.notes, inline=False)

    if party.closed:
        embed.set_footer(text=f"Party #{party.party_id} · closed")
    else:
        embed.set_footer(text=f"Party #{party.party_id} · tap a role below to join")
    return embed
