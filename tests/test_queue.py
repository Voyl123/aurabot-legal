"""Tests for the party queue store, matching, and create-time notifications."""

import asyncio
import tempfile

from src import views
from src.party import Party, PartyStore
from src.queues import QueueEntry, QueueStore


def _store():
    return QueueStore(tempfile.mktemp(suffix=".json"))


def test_add_replaces_same_user_activity():
    q = _store()
    q.add(QueueEntry(1, "A", 100, "Dungeon X", "dps"))
    q.add(QueueEntry(1, "A", 100, "Dungeon X", "tank"))  # same user+activity
    entries = q.for_user(1, 100)
    assert len(entries) == 1 and entries[0].role == "tank"


def test_matches_by_activity_and_role():
    q = _store()
    q.add(QueueEntry(1, "Tank", 100, "Dungeon X", "tank"))
    q.add(QueueEntry(2, "Dps", 100, "Dungeon X", "dps"))
    q.add(QueueEntry(3, "Any", 100, "Dungeon X", None))
    q.add(QueueEntry(4, "Other", 100, "Dungeon Y", "dps"))

    # A party for X with only DPS open matches the dps-seeker and the any-seeker.
    matched = q.matches(100, ["Dungeon X"], open_roles={"dps"})
    ids = {e.user_id for e in matched}
    assert ids == {2, 3}


def test_matches_respects_guild():
    q = _store()
    q.add(QueueEntry(1, "A", 100, "Dungeon X", "dps"))
    assert q.matches(999, ["Dungeon X"], {"dps"}) == []


def test_remove_user():
    q = _store()
    q.add(QueueEntry(1, "A", 100, "X", "dps"))
    q.add(QueueEntry(1, "A", 100, "Y", "tank"))
    assert q.remove_user(1, 100) == 2
    assert q.for_user(1, 100) == []


def test_persistence_roundtrip():
    path = tempfile.mktemp(suffix=".json")
    q = QueueStore(path)
    q.add(QueueEntry(1, "A", 100, "X", "dps"))
    assert QueueStore(path).for_user(1, 100)[0].activity == "X"


# --------------------------------------------------------------------------- #
# Create-time notification
# --------------------------------------------------------------------------- #
class _Followup:
    def __init__(self):
        self.msgs = []

    async def send(self, content=None, **kwargs):
        self.msgs.append(content)


class _Interaction:
    def __init__(self):
        self.followup = _Followup()


def test_notify_queue_pings_and_clears_matched():
    async def run():
        views.set_store(PartyStore(tempfile.mktemp(suffix=".json")))
        q = _store()
        views.set_queue_store(q)
        q.add(QueueEntry(20, "Waiting", 1, "Dungeon X", "dps"))
        q.add(QueueEntry(99, "Leader", 1, "Dungeon X", "dps"))  # also the leader

        party = Party(
            party_id="P", guild_id=1, channel_id=2, leader_id=99, leader_name="Leader",
            activity="Dungeon X", difficulty="Normal", notes="", slots={"dps": 4},
        )
        party.add_or_move(99, "Leader", "dps")

        interaction = _Interaction()
        await views._notify_queue(interaction, party)

        # The waiting DPS got pinged; the leader did not get pinged about their own party.
        assert interaction.followup.msgs and "<@20>" in interaction.followup.msgs[0]
        assert "<@99>" not in interaction.followup.msgs[0]
        # Matched entry was cleared from the queue.
        assert q.for_user(20, 1) == []
    asyncio.run(run())


def test_notify_queue_silent_when_no_match():
    async def run():
        views.set_store(PartyStore(tempfile.mktemp(suffix=".json")))
        q = _store()
        views.set_queue_store(q)
        q.add(QueueEntry(20, "W", 1, "Dungeon Y", "dps"))  # different dungeon

        party = Party(
            party_id="P", guild_id=1, channel_id=2, leader_id=99, leader_name="L",
            activity="Dungeon X", difficulty="Normal", notes="", slots={"dps": 4},
        )
        interaction = _Interaction()
        await views._notify_queue(interaction, party)
        assert interaction.followup.msgs == []
    asyncio.run(run())
