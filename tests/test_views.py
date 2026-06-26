"""Tests for the button + modal interaction flow using mocked Discord objects.

We avoid a live gateway connection by faking the bits of ``discord.Interaction``
the callbacks actually touch. ``asyncio.run`` drives the coroutine callbacks so
we don't need pytest-asyncio.
"""

import asyncio
import tempfile
import types

from src import views
from src.party import Party, PartyStore


# --------------------------------------------------------------------------- #
# Mocks
# --------------------------------------------------------------------------- #
class MockMessage:
    def __init__(self):
        self.edited = None

    async def edit(self, **kwargs):
        self.edited = kwargs


class MockChannel:
    def __init__(self, message):
        self._message = message

    async def fetch_message(self, _id):
        return self._message


class MockClient:
    """Stands in for interaction.client used by _rerender_card."""
    def __init__(self):
        self.message = MockMessage()
        self._channel = MockChannel(self.message)

    def get_channel(self, _id):
        return self._channel


class MockResponse:
    def __init__(self):
        self.edited = None
        self.sent = []
        self.modal = None

    async def edit_message(self, **kwargs):
        self.edited = kwargs

    async def send_message(self, content=None, **kwargs):
        self.sent.append((content, kwargs))

    async def send_modal(self, modal):
        self.modal = modal


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
    def __init__(self, user, message_id=555, client=None):
        self.user = user
        self.message = types.SimpleNamespace(id=message_id)
        self.response = MockResponse()
        self.followup = MockFollowup()
        self.client = client or MockClient()


def _setup(min_gear_score=None):
    store = PartyStore(tempfile.mktemp(suffix=".json"))
    views.set_store(store)
    p = Party(
        party_id="P1", guild_id=1, channel_id=2, leader_id=10, leader_name="Leader",
        activity="Field Boss", difficulty="Hard", notes="",
        slots={"tank": 1, "healer": 1, "dps": 2}, min_gear_score=min_gear_score,
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


async def _join_with_gs(view, role_custom_id, user, gear_score):
    """Click a join button (opens a modal), then submit the modal."""
    click = await _click(view, role_custom_id, user)
    modal = click.response.modal
    assert modal is not None, "join button should open a gear-score modal"
    modal.gear_score._value = str(gear_score)
    submit = MockInteraction(user)
    await modal.on_submit(submit)
    return submit


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_join_asks_for_gear_score_then_records_it():
    async def run():
        store, view = _setup()
        submit = await _join_with_gs(view, "party:join:healer", MockUser(11, "Healz"), 4200)
        # The applicant gets an ephemeral confirmation including their score.
        assert submit.response.sent and "4,200" in submit.response.sent[0][0]
        # The card was re-rendered out-of-band.
        assert submit.client.message.edited is not None
        member = store.get("P1").find_member(11)
        assert member.role == "healer" and member.gear_score == 4200
    asyncio.run(run())


def test_join_below_min_gear_score_rejected():
    async def run():
        store, view = _setup(min_gear_score=4000)
        submit = await _join_with_gs(view, "party:join:dps", MockUser(12, "Low"), 3000)
        assert submit.response.sent and "requires" in submit.response.sent[0][0].lower()
        assert store.get("P1").find_member(12) is None
    asyncio.run(run())


def test_join_meeting_min_gear_score_allowed():
    async def run():
        store, view = _setup(min_gear_score=4000)
        await _join_with_gs(view, "party:join:dps", MockUser(12, "Ok"), 4500)
        assert store.get("P1").find_member(12).gear_score == 4500
    asyncio.run(run())


def test_join_invalid_gear_score_rejected():
    async def run():
        store, view = _setup()
        submit = await _join_with_gs(view, "party:join:dps", MockUser(13, "Oops"), "abc")
        assert submit.response.sent and "number" in submit.response.sent[0][0].lower()
        assert store.get("P1").find_member(13) is None
    asyncio.run(run())


def test_full_role_rejected_before_modal():
    async def run():
        store, view = _setup()
        await _join_with_gs(view, "party:join:dps", MockUser(12, "D1"), 3000)
        await _join_with_gs(view, "party:join:dps", MockUser(13, "D2"), 3000)
        # DPS now full (2 slots); a third gets an immediate ephemeral, no modal.
        i = await _click(view, "party:join:dps", MockUser(14, "D3"))
        assert i.response.modal is None
        assert i.response.sent and "full" in i.response.sent[0][0].lower()
    asyncio.run(run())


def test_leave():
    async def run():
        store, view = _setup()
        await _join_with_gs(view, "party:join:dps", MockUser(12, "D1"), 3000)
        i = await _click(view, "party:leave", MockUser(12, "D1"))
        assert i.followup.msgs == ["You left the party."]
        assert store.get("P1").find_member(12) is None
    asyncio.run(run())


def test_disband_permissions():
    async def run():
        store, view = _setup()
        i = await _click(view, "party:disband", MockUser(11, "Healz"))
        assert i.response.sent and "leader" in i.response.sent[0][0].lower()
        assert not store.get("P1").closed

        i = await _click(view, "party:disband", MockUser(99, "Mod", mod=True))
        assert store.get("P1").closed
        assert i.response.edited.get("view") is None
    asyncio.run(run())


def test_click_on_missing_party():
    async def run():
        _, view = _setup()
        i = await _click(view, "party:join:tank", MockUser(11, "Healz"), message_id=999)
        assert i.response.modal is None
        assert i.response.sent and "no longer exists" in i.response.sent[0][0].lower()
    asyncio.run(run())
