"""Embed rendering — turns a :class:`Party` into the rich UI message."""

from __future__ import annotations

import datetime as dt

import discord

from . import config
from .party import Party


def _roster_block(party: Party, role_key: str) -> str:
    role = config.ROLES[role_key]
    members = party.members_for(role_key)
    lines: list[str] = []
    for m in members:
        lines.append(f"`✓` <@{m.user_id}>")
    # Show empty slots so people can see what's still needed.
    for _ in range(party.open_slots(role_key)):
        lines.append("`○` *open*")
    if not lines:
        lines.append("*—*")
    return "\n".join(lines)


def build_party_embed(party: Party) -> discord.Embed:
    if party.closed:
        color = config.Colors.CLOSED
        status = "🔒 Disbanded"
    elif party.is_full:
        color = config.Colors.FULL
        status = "✅ Party Full — ready to go!"
    else:
        color = config.Colors.OPEN
        status = f"🟢 Recruiting — {party.size}/{party.capacity} filled"

    description_lines = [
        f"**Difficulty:** {party.difficulty}",
        f"**Status:** {status}",
    ]
    if party.start_at:
        ts = int(party.start_at)
        # Discord timestamp markdown renders in each viewer's local timezone:
        #   <t:UNIX:F>  -> "Friday, 26 June 2026 20:00"
        #   <t:UNIX:R>  -> "in 30 minutes" (auto-updating, relative)
        description_lines.append(f"**Starts:** <t:{ts}:F> (<t:{ts}:R>)")

    embed = discord.Embed(
        title=f"⚔️ {party.activity}",
        description="\n".join(description_lines),
        color=color,
        timestamp=dt.datetime.fromtimestamp(party.created_at, tz=dt.timezone.utc),
    )

    embed.set_author(name=f"{party.leader_name}'s Party")

    # One column per role.
    for role_key in config.ROLE_ORDER:
        role = config.ROLES[role_key]
        filled = len(party.members_for(role_key))
        total = party.slots.get(role_key, 0)
        if total == 0:
            continue
        embed.add_field(
            name=f"{role.emoji} {role.label}  ({filled}/{total})",
            value=_roster_block(party, role_key),
            inline=True,
        )

    # A plain-language summary of what's still needed.
    if not party.closed and not party.is_full:
        needs = [
            f"{config.ROLES[r].emoji} **{party.open_slots(r)}** {config.ROLES[r].label}"
            for r in config.ROLE_ORDER
            if party.open_slots(r) > 0
        ]
        embed.add_field(name="🔎 Looking for", value="  •  ".join(needs), inline=False)

    if party.notes:
        embed.add_field(name="📝 Notes", value=party.notes, inline=False)

    footer = f"Party ID: {party.party_id}"
    if party.closed:
        footer += " • Closed"
    else:
        footer += " • Use the buttons below to join"
    embed.set_footer(text=footer)
    return embed
