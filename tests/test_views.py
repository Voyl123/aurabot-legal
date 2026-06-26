"""Tests for the button interaction flow using mocked Discord interactions.

We avoid a live gateway connection by faking the bits of ``discord.Interaction``
the callbacks actually touch (``user``, ``message``, ``response``, ``followup``).
``asyncio.run`` drives the coroutine callbacks so we don't need pytest-asyncio.
"""

import asyncio
import tempfile
import types

from src import views
from src.party import Party, PartyStore


# --------------------------------------------------------------------------- #
# Mocks
# --------------------------------------------------------------------------- #
class MockResponse:
    def __init__(self):
        self.edited = None
        self.sent = []

    async def edit_message(self, **kwargs):
        self.edited = kwargs

    async def send_message(self, content=None, **kwargs):
        self.sent.append((content, kwargs))


class MockFollowup:
    def __init__(self):
        self.msgs = []

    async def send(self, content=None, **kwargs):
        self.msgs.append(content)


class MockUser:
    def __init__(self, uid, name, mod=False):
        self.id = uid
        self.display_name = name
        self.guild_permissions = types.SimpleNamespace(
            manage_messages=mod, administrator=mod
        )


class MockInteraction:
    def __init__(self, user, message_id):
        self.user = user
        self.message = types.SimpleNamespace(id=message_id)
        self.response = MockResponse()
        self.followup = MockFollowup()


def _setup():
    store = PartyStore(tempfile.mktemp(suffix=".json"))
    views.set_store(store)
    p = Party(
        party_id="P1", guild_id=1, channel_id=2, leader_id=10, leader_name="Leader",
        activity="Field Boss", difficulty="Hard", notes="", slots={"tank": 1, "healer": 1, "dps": 2},
    )
    p.message_id = 555
    p.add_or_move(10, "Leader", "tank")
    store.add(p)
    return store, views.PartyView()


def _button(view, custom_id):
    return next(c for c in view.children if c.custom_id == custom_id)


async def _click(view, custom_id, user, message_id=555):
    interaction = MockInteraction(user, message_id)
    await _button(view, custom_id).callback(interaction)
    return interaction


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_join_updates_card_and_confirms():
    async def run():
        store, view = _setup()
        i = await _click(view, "party:join:healer", MockUser(11, "Healz"))
        assert i.response.edited is not None          # card was re-rendered
        assert i.followup.msgs == ["You joined as **Healer**."]
        assert store.get("P1").size == 2
    asyncio.run(run())


def test_full_role_rejected():
    async def run():
        store, view = _setup()
        await _click(view, "party:join:dps", MockUser(12, "D1"))
        await _click(view, "party:join:dps", MockUser(13, "D2"))
        i = await _click(view, "party:join:dps", MockUser(14, "D3"))
        assert i.response.sent and "full" in i.response.sent[0][0].lower()
        # The DPS role is full (the healer slot is still open, so the party isn't).
        assert store.get("P1").open_slots("dps") == 0
    asyncio.run(run())


def test_leave():
    async def run():
        store, view = _setup()
        await _click(view, "party:join:dps", MockUser(12, "D1"))
        i = await _click(view, "party:leave", MockUser(12, "D1"))
        assert i.followup.msgs == ["You left the party."]
        assert store.get("P1").find_member(12) is None
    asyncio.run(run())


def test_disband_permissions():
    async def run():
        store, view = _setup()
        # Non-leader, non-mod is denied.
        i = await _click(view, "party:disband", MockUser(11, "Healz"))
        assert i.response.sent and "leader" in i.response.sent[0][0].lower()
        assert not store.get("P1").closed

        # A moderator can disband; the refreshed card drops its buttons.
        i = await _click(view, "party:disband", MockUser(99, "Mod", mod=True))
        assert store.get("P1").closed
        assert i.response.edited.get("view") is None
    asyncio.run(run())


def test_click_on_missing_party():
    async def run():
        _, view = _setup()
        i = await _click(view, "party:join:tank", MockUser(11, "Healz"), message_id=999)
        assert i.response.sent and "no longer exists" in i.response.sent[0][0].lower()
    asyncio.run(run())
