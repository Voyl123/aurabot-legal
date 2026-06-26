"""Interactive UI: the persistent button view + the create-party modal."""

from __future__ import annotations

import re
import secrets

import discord

from . import config
from .embeds import build_party_embed
from .party import Party, PartyStore
from .timeparse import parse_start_time


# The store is injected by bot.py at startup via :func:`set_store`.
_store: PartyStore | None = None


def set_store(store: PartyStore) -> None:
    global _store
    _store = store


def store() -> PartyStore:
    assert _store is not None, "PartyStore not initialised"
    return _store


async def _refresh(interaction: discord.Interaction, party: Party) -> None:
    """Re-render the party message in response to a *component* interaction."""
    store().save()
    embed = build_party_embed(party)
    view = PartyView() if not party.closed else None
    await interaction.response.edit_message(embed=embed, view=view)


async def _rerender_card(client: discord.Client, party: Party) -> None:
    """Edit the party message out-of-band (used after a modal submit, where the
    interaction isn't attached to the party message)."""
    store().save()
    if party.message_id is None:
        return
    channel = client.get_channel(party.channel_id) or await client.fetch_channel(party.channel_id)
    message = await channel.fetch_message(party.message_id)
    view = PartyView() if not party.closed else None
    await message.edit(embed=build_party_embed(party), view=view)


# --------------------------------------------------------------------------- #
# Persistent button view
# --------------------------------------------------------------------------- #
class PartyView(discord.ui.View):
    """Buttons attached to every party message.

    ``timeout=None`` + stable ``custom_id``s make the view *persistent*, so the
    buttons keep working after a bot restart.
    """

    def __init__(self) -> None:
        super().__init__(timeout=None)

    # -- helpers ------------------------------------------------------------ #
    def _party_from(self, interaction: discord.Interaction) -> Party | None:
        # The party id is encoded in the message; we look it up by message id.
        msg_id = interaction.message.id if interaction.message else None
        if msg_id is None:
            return None
        return next((p for p in store().all() if p.message_id == msg_id), None)

    async def _join(self, interaction: discord.Interaction, role_key: str) -> None:
        party = self._party_from(interaction)
        if party is None:
            await interaction.response.send_message(
                "This party no longer exists.", ephemeral=True
            )
            return
        # Reject early (before showing the modal) if the role is already full,
        # unless the user is just confirming the role they already hold.
        existing = party.find_member(interaction.user.id)
        if party.open_slots(role_key) <= 0 and not (existing and existing.role == role_key):
            await interaction.response.send_message(
                f"All **{config.ROLES[role_key].label}** slots are full.", ephemeral=True
            )
            return
        # Ask for the player's Gear Score, then complete the join on submit.
        await interaction.response.send_modal(JoinModal(party.party_id, role_key, existing))

    # -- buttons ------------------------------------------------------------ #
    @discord.ui.button(label="Tank", emoji="🛡️", style=discord.ButtonStyle.primary,
                       custom_id="party:join:tank", row=0)
    async def join_tank(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._join(interaction, "tank")

    @discord.ui.button(label="Healer", emoji="💚", style=discord.ButtonStyle.success,
                       custom_id="party:join:healer", row=0)
    async def join_healer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._join(interaction, "healer")

    @discord.ui.button(label="DPS", emoji="⚔️", style=discord.ButtonStyle.danger,
                       custom_id="party:join:dps", row=0)
    async def join_dps(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._join(interaction, "dps")

    @discord.ui.button(label="Leave", emoji="🚪", style=discord.ButtonStyle.secondary,
                       custom_id="party:leave", row=1)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        party = self._party_from(interaction)
        if party is None:
            await interaction.response.send_message(
                "This party no longer exists.", ephemeral=True
            )
            return
        changed, msg = party.remove(interaction.user.id)
        if not changed:
            await interaction.response.send_message(msg, ephemeral=True)
            return
        await _refresh(interaction, party)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="Disband", emoji="🔒", style=discord.ButtonStyle.secondary,
                       custom_id="party:disband", row=1)
    async def disband(self, interaction: discord.Interaction, button: discord.ui.Button):
        party = self._party_from(interaction)
        if party is None:
            await interaction.response.send_message(
                "This party no longer exists.", ephemeral=True
            )
            return
        if interaction.user.id != party.leader_id and not _is_manager(interaction):
            await interaction.response.send_message(
                "Only the party leader (or a server moderator) can disband this party.",
                ephemeral=True,
            )
            return
        party.closed = True
        await _refresh(interaction, party)
        await interaction.followup.send("Party disbanded.", ephemeral=True)


def _is_manager(interaction: discord.Interaction) -> bool:
    perms = getattr(interaction.user, "guild_permissions", None)
    return bool(perms and (perms.manage_messages or perms.administrator))


def _parse_gear_score(value: str | None) -> int | None:
    """Parse a gear-score text input (digits, optionally with commas/spaces)."""
    if not value:
        return None
    cleaned = value.replace(",", "").replace(" ", "").strip()
    if not cleaned.isdigit():
        return None
    return int(cleaned)


_CHANNEL_LINK_RE = re.compile(r"channels/\d+/(\d+)")


def parse_voice(text: str | None) -> tuple[int | None, str | None]:
    """Turn a pasted voice link / ID into ``(channel_id, url)``.

    - a Discord channel link (``…/channels/<guild>/<channel>``) → that channel id
    - a bare numeric channel id → that id
    - any other http(s) URL → kept as a raw link
    """
    if not text:
        return None, None
    text = text.strip()
    m = _CHANNEL_LINK_RE.search(text)
    if m:
        return int(m.group(1)), None
    if text.isdigit():
        return int(text), None
    if text.startswith(("http://", "https://")):
        return None, text
    return None, None


# --------------------------------------------------------------------------- #
# Join modal — asks the applicant for their Gear Score
# --------------------------------------------------------------------------- #
class JoinModal(discord.ui.Modal, title="Join Party"):
    def __init__(self, party_id: str, role_key: str, existing) -> None:
        super().__init__()
        self._party_id = party_id
        self._role_key = role_key
        # Pre-fill with the player's previously entered score, if any.
        if existing is not None and existing.gear_score is not None:
            self.gear_score.default = str(existing.gear_score)

    gear_score = discord.ui.TextInput(
        label="Your Gear Score (CP)",
        placeholder="e.g. 4200",
        required=True,
        max_length=6,
    )

    async def on_submit(self, interaction: discord.Interaction):
        party = store().get(self._party_id)
        if party is None or party.closed:
            await interaction.response.send_message(
                "This party no longer exists.", ephemeral=True
            )
            return

        gs = _parse_gear_score(self.gear_score.value)
        if gs is None:
            await interaction.response.send_message(
                "Please enter your Gear Score as a number, e.g. `4200`.", ephemeral=True
            )
            return
        if party.min_gear_score and gs < party.min_gear_score:
            await interaction.response.send_message(
                f"This party requires **{party.min_gear_score:,}+ CP** — yours is "
                f"**{gs:,}**. Gear up and try again! 💪",
                ephemeral=True,
            )
            return

        changed, msg = party.add_or_move(
            interaction.user.id, interaction.user.display_name, self._role_key, gear_score=gs
        )
        if not changed:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        await _rerender_card(interaction.client, party)
        await interaction.response.send_message(f"{msg} (Gear Score: {gs:,})", ephemeral=True)


# --------------------------------------------------------------------------- #
# Create-party modal
# --------------------------------------------------------------------------- #
class CreatePartyModal(discord.ui.Modal, title="Create a Party"):
    def __init__(self, activity: str, difficulty: str, gear_score: int | None = None,
                 voice_channel_id: int | None = None, voice_link: str | None = None) -> None:
        super().__init__()
        self._activity = activity
        self._difficulty = difficulty
        self._gear_score = gear_score
        self._voice_channel_id = voice_channel_id
        self._voice_link = voice_link

    start_time = discord.ui.TextInput(
        label="Start time (optional)",
        placeholder="now • 30m • 20:00 • or paste a sesh.fyi timestamp",
        required=False,
        max_length=40,
    )
    notes = discord.ui.TextInput(
        label="Notes (optional)",
        placeholder="e.g. CP 4k+, voice required, bring potions…",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300,
    )
    # Slots: defaults give the classic 1 Tank / 1 Healer / 4 DPS six-stack.
    tanks = discord.ui.TextInput(
        label="Tank slots", default="1", max_length=2, required=False
    )
    healers = discord.ui.TextInput(
        label="Healer slots", default="1", max_length=2, required=False
    )
    dps = discord.ui.TextInput(
        label="DPS slots", default="4", max_length=2, required=False
    )

    @staticmethod
    def _to_int(value: str, fallback: int) -> int:
        try:
            return max(0, min(20, int(value.strip())))
        except (ValueError, AttributeError):
            return fallback

    async def on_submit(self, interaction: discord.Interaction):
        slots = {
            "tank": self._to_int(self.tanks.value, 1),
            "healer": self._to_int(self.healers.value, 1),
            "dps": self._to_int(self.dps.value, 4),
        }
        if sum(slots.values()) == 0:
            await interaction.response.send_message(
                "A party needs at least one slot. Try again.", ephemeral=True
            )
            return

        party = Party(
            party_id=secrets.token_hex(3).upper(),
            guild_id=interaction.guild_id or 0,
            channel_id=interaction.channel_id or 0,
            leader_id=interaction.user.id,
            leader_name=interaction.user.display_name,
            activity=self._activity,
            difficulty=self._difficulty,
            notes=(self.notes.value or "").strip(),
            slots=slots,
            min_gear_score=self._gear_score,
            voice_channel_id=self._voice_channel_id,
            voice_link=self._voice_link,
            start_at=parse_start_time(self.start_time.value),
        )
        # Leader auto-joins the first available role.
        for role_key in ("tank", "healer", "dps"):
            if slots.get(role_key, 0) > 0:
                party.add_or_move(interaction.user.id, interaction.user.display_name, role_key)
                break

        store().add(party)

        embed = build_party_embed(party)
        view = PartyView()
        await interaction.response.send_message(
            content="@here a new party is forming! 🎉",
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(everyone=True),
        )
        sent = await interaction.original_response()
        party.message_id = sent.id
        store().save()
