"""D20 — Throne and Liberty Dungeon Party Creator.

Entry point. Run with:  python bot.py
Requires a DISCORD_TOKEN environment variable (see .env.example).
"""

from __future__ import annotations

import logging
import os

import discord
from discord import app_commands
from discord.ext import commands, tasks

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass

from src import config
from src.party import PartyStore
from src.queues import QueueEntry, QueueStore
from src.views import (
    CreatePartyModal,
    PartyView,
    _rerender_card,
    parse_voice,
    queue_store,
    set_queue_store,
    set_store,
    store,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("d20")


# --------------------------------------------------------------------------- #
# Bot setup
# --------------------------------------------------------------------------- #
class D20Bot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        # We only use slash commands + interactions, so no privileged intents
        # (message content / members) are required.
        super().__init__(command_prefix="!d20 ", intents=intents)
        self.store = PartyStore()
        self.queue = QueueStore()
        set_store(self.store)
        set_queue_store(self.queue)

    async def setup_hook(self) -> None:
        # Register the persistent view so buttons survive restarts.
        self.add_view(PartyView())
        if not self.expire_parties.is_running():
            self.expire_parties.start()

        # Sync slash commands. If DISCORD_GUILD_ID is set we sync to that guild
        # for instant availability during development; otherwise sync globally.
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Synced commands to guild %s", guild_id)
        else:
            await self.tree.sync()
            log.info("Synced commands globally (may take up to 1h to appear)")

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id=%s)", self.user, self.user.id if self.user else "?")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="for parties • /lfg"
            )
        )

    @tasks.loop(minutes=1)
    async def expire_parties(self) -> None:
        """Close parties whose running time has elapsed and update their cards."""
        for party in self.store.active():
            if party.is_expired:
                party.closed = True
                try:
                    await _rerender_card(self, party)
                except (discord.HTTPException, discord.NotFound):
                    self.store.save()  # at least persist the closed state

    @expire_parties.before_loop
    async def _before_expire(self) -> None:
        await self.wait_until_ready()


bot = D20Bot()


# --------------------------------------------------------------------------- #
# Slash commands
# --------------------------------------------------------------------------- #
async def _activity_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    current = (current or "").lower()
    matches = [a for a in config.ACTIVITIES if current in a.lower()][:25]
    return [app_commands.Choice(name=a, value=a) for a in matches]


@bot.tree.command(name="create", description="Create a Throne and Liberty party to find Tanks, Healers & DPS.")
@app_commands.describe(
    activity="What is the party for? (boss, dungeon, event…)",
    difficulty="Difficulty / vibe of the run",
    gear_score="Minimum Gear Score / Combat Power applicants should have (optional)",
    voice="Paste a voice channel link or ID for the party to gather in (optional)",
)
@app_commands.autocomplete(activity=_activity_autocomplete)
@app_commands.choices(
    difficulty=[app_commands.Choice(name=d, value=d) for d in config.DIFFICULTIES]
)
async def create(
    interaction: discord.Interaction,
    activity: str,
    difficulty: app_commands.Choice[str] | None = None,
    gear_score: app_commands.Range[int, 0, 10000] | None = None,
    voice: str | None = None,
):
    diff = difficulty.value if difficulty else "Any"
    voice_channel_id, voice_link = parse_voice(voice)
    # Open the modal to collect slot counts + notes before posting.
    await interaction.response.send_modal(
        CreatePartyModal(
            activity=activity,
            difficulty=diff,
            gear_score=gear_score,
            voice_channel_id=voice_channel_id,
            voice_link=voice_link,
        )
    )


_ROLE_CHOICES = [
    app_commands.Choice(name=config.ROLES[r].label, value=r) for r in config.ROLE_ORDER
]


def _find_parties(guild_id: int, activity: str | None = None, role: str | None = None):
    """Active parties that are recruiting (open, not full, not expired)."""
    out = []
    for p in store().active():
        if p.guild_id != guild_id or p.is_full or p.is_expired:
            continue
        if activity and not p.wants(activity):
            continue
        if role and p.open_slots(role) <= 0:
            continue
        if not role and not p.has_open_slot:
            continue
        out.append(p)
    return out


def _party_line(p) -> tuple[str, str]:
    needs = " · ".join(
        f"{config.ROLES[r].emoji} {p.open_slots(r)} {config.ROLES[r].label}"
        for r in config.ROLE_ORDER if p.open_slots(r) > 0
    )
    link = f"https://discord.com/channels/{p.guild_id}/{p.channel_id}/{p.message_id}"
    gs = f" • ⚡ {p.min_gear_score:,}+ CP" if p.min_gear_score else ""
    return (
        f"{p.activity} ({p.difficulty}) — {p.size}/{p.capacity}{gs}",
        f"Needs: {needs or '—'}\n[Jump to party]({link})",
    )


@bot.tree.command(name="lfg", description="Find parties looking for members (optionally filter by dungeon/role).")
@app_commands.describe(
    activity="Only show parties running this dungeon/activity (optional)",
    role="Only show parties that still need this role (optional)",
)
@app_commands.autocomplete(activity=_activity_autocomplete)
@app_commands.choices(role=_ROLE_CHOICES)
async def lfg(
    interaction: discord.Interaction,
    activity: str | None = None,
    role: app_commands.Choice[str] | None = None,
):
    role_key = role.value if role else None
    found = _find_parties(interaction.guild_id or 0, activity, role_key)
    if not found:
        hint = " Try `/queue` to get pinged when one forms." if activity else ""
        await interaction.response.send_message(
            f"No parties are looking for members right now.{hint} Or start one with `/create`! ⚔️",
            ephemeral=True,
        )
        return

    embed = discord.Embed(title="🔎 Looking for group", color=config.Colors.ACCENT)
    for p in found[:25]:
        name, value = _party_line(p)
        embed.add_field(name=name, value=value, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="queue", description="Queue for a dungeon — see matching parties now, or get pinged when one forms.")
@app_commands.describe(
    activity="The dungeon/activity you want to run",
    role="The role you'll play (optional)",
)
@app_commands.autocomplete(activity=_activity_autocomplete)
@app_commands.choices(role=_ROLE_CHOICES)
async def queue(
    interaction: discord.Interaction,
    activity: str,
    role: app_commands.Choice[str] | None = None,
):
    role_key = role.value if role else None
    guild_id = interaction.guild_id or 0

    # First, look through parties already made / looking.
    found = _find_parties(guild_id, activity, role_key)
    if found:
        embed = discord.Embed(
            title=f"🔎 Parties already running {activity}",
            description="Jump in below — no need to wait!",
            color=config.Colors.ACCENT,
        )
        for p in found[:25]:
            name, value = _party_line(p)
            embed.add_field(name=name, value=value, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # None yet — add them to the queue to be pinged when a party forms.
    queue_store().add(QueueEntry(
        user_id=interaction.user.id,
        user_name=interaction.user.display_name,
        guild_id=guild_id,
        activity=activity,
        role=role_key,
    ))
    role_txt = f" as **{config.ROLES[role_key].label}**" if role_key else ""
    await interaction.response.send_message(
        f"🎟️ You're queued for **{activity}**{role_txt}. I'll ping you the moment a "
        f"matching party is created. Use `/unqueue` to leave the queue.",
        ephemeral=True,
    )


@bot.tree.command(name="unqueue", description="Leave the party queue.")
async def unqueue(interaction: discord.Interaction):
    removed = queue_store().remove_user(interaction.user.id, interaction.guild_id or 0)
    msg = (
        f"✅ Removed you from {removed} queue{'s' if removed != 1 else ''}."
        if removed else "You weren't in any queues."
    )
    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="help", description="How to use the party bot.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎲 D20 — Party Creator",
        description="Find Tanks, Healers and DPS for your Throne and Liberty runs.",
        color=config.Colors.OPEN,
    )
    embed.add_field(
        name="/create",
        value="Start a party. Pick an activity (raids, T1–T3 dungeons, archbosses…), a "
              "difficulty, an optional **min Gear Score (CP)** and a **voice link**. In the "
              "form you can set roles, a **start time**, how long it's **running for**, and "
              "**other dungeons** you'll also run. The bot posts a live party card.",
        inline=False,
    )
    embed.add_field(
        name="/lfg",
        value="Find parties looking for members. Filter by dungeon and/or the role you play.",
        inline=False,
    )
    embed.add_field(
        name="/queue · /unqueue",
        value="`/queue` a dungeon: if a party's already looking you'll see it instantly — "
              "otherwise you're queued and **pinged the moment a matching party forms**. "
              "`/unqueue` leaves the queue.",
        inline=False,
    )
    embed.add_field(
        name="Joining & leaving",
        value="Click 🛡️ **Tank**, 💚 **Healer** or ⚔️ **DPS** on any card — you'll be asked "
              "for your **Gear Score (CP)**, which shows next to your name. Click 🚪 **Leave** "
              "any time to drop out. The leader can 🔒 **Disband**.",
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit(
            "DISCORD_TOKEN is not set. Copy .env.example to .env and add your bot token, "
            "then `source .env` (or use a process manager that loads it)."
        )
    bot.run(token)


if __name__ == "__main__":
    main()
