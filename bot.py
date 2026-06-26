"""AuraBot — Throne and Liberty Dungeon Party Creator.

Entry point. Run with:  python bot.py
Requires a DISCORD_TOKEN environment variable (see .env.example).
"""

from __future__ import annotations

import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass

from src import config
from src.party import PartyStore
from src.views import CreatePartyModal, PartyView, set_store, store


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aurabot")


# --------------------------------------------------------------------------- #
# Bot setup
# --------------------------------------------------------------------------- #
class AuraBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        # We only use slash commands + interactions, so no privileged intents
        # (message content / members) are required.
        super().__init__(command_prefix="!aura ", intents=intents)
        self.store = PartyStore()
        set_store(self.store)

    async def setup_hook(self) -> None:
        # Register the persistent view so buttons survive restarts.
        self.add_view(PartyView())

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
                type=discord.ActivityType.watching, name="for parties • /create"
            )
        )


bot = AuraBot()


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
):
    diff = difficulty.value if difficulty else "Any"
    # Open the modal to collect slot counts + notes before posting.
    await interaction.response.send_modal(
        CreatePartyModal(activity=activity, difficulty=diff, gear_score=gear_score)
    )


@bot.tree.command(name="parties", description="List the parties currently recruiting in this server.")
async def parties(interaction: discord.Interaction):
    active = [
        p for p in store().active()
        if p.guild_id == (interaction.guild_id or 0) and not p.is_full
    ]
    if not active:
        await interaction.response.send_message(
            "No parties are recruiting right now. Be the first — use `/create`! ⚔️",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title="🗺️ Parties currently recruiting",
        color=config.Colors.ACCENT,
    )
    for p in active[:25]:
        needs = ", ".join(
            f"{config.ROLES[r].emoji} {p.open_slots(r)} {config.ROLES[r].label}"
            for r in config.ROLE_ORDER if p.open_slots(r) > 0
        )
        link = f"https://discord.com/channels/{p.guild_id}/{p.channel_id}/{p.message_id}"
        gs = f" • ⚡ {p.min_gear_score:,}+ CP" if p.min_gear_score else ""
        embed.add_field(
            name=f"{p.activity} ({p.difficulty}) — {p.size}/{p.capacity}{gs}",
            value=f"Needs: {needs or '—'}\n[Jump to party]({link})",
            inline=False,
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="help", description="How to use the party bot.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚔️ AuraBot — Party Creator",
        description="Find Tanks, Healers and DPS for your Throne and Liberty runs.",
        color=config.Colors.OPEN,
    )
    embed.add_field(
        name="/create",
        value="Start a new party. Pick an activity (raids, 1★–3★ dungeons, archbosses…), "
              "a difficulty, and an optional **minimum Gear Score (CP)**. Then set how "
              "many of each role you need and the bot posts a live party card with join buttons.",
        inline=False,
    )
    embed.add_field(
        name="/parties",
        value="See every party still looking for members, and what roles they need.",
        inline=False,
    )
    embed.add_field(
        name="Joining a party",
        value="Click 🛡️ **Tank**, 💚 **Healer** or ⚔️ **DPS** on any party card. "
              "Use 🚪 **Leave** to drop out. The leader can 🔒 **Disband**.",
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
