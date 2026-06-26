"""Tests for the party queue store, matching, and create-time notifications."""

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


def test_candidates_match_activity_or_any_longest_first():
    q = _store()
    q.add(QueueEntry(1, "Old", 100, "Dungeon X", "dps", created_at=100))
    q.add(QueueEntry(2, "AnyDungeon", 100, None, "tank", created_at=200))
    q.add(QueueEntry(3, "OtherDungeon", 100, "Dungeon Y", "dps", created_at=150))
    q.add(QueueEntry(4, "New", 100, "Dungeon X", "healer", created_at=300))

    cands = q.candidates(100, ["Dungeon X"])
    # Dungeon Y is excluded; the rest are ordered oldest-first by created_at.
    assert [e.user_id for e in cands] == [1, 2, 4]


def test_candidates_respect_guild():
    q = _store()
    q.add(QueueEntry(1, "A", 100, "Dungeon X", "dps"))
    assert q.candidates(999, ["Dungeon X"]) == []


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


def test_for_user_scoped_to_guild():
    q = _store()
    q.add(QueueEntry(1, "A", 100, "X", "dps"))
    q.add(QueueEntry(1, "A", 200, "Y", "tank"))  # different guild
    mine = q.for_user(1, 100)
    assert len(mine) == 1 and mine[0].activity == "X"


# --------------------------------------------------------------------------- #
# Auto-fill on party creation (longest-queued first)
# --------------------------------------------------------------------------- #
def _wire():
    views.set_store(PartyStore(tempfile.mktemp(suffix=".json")))
    q = _store()
    views.set_queue_store(q)
    return q


def _party(slots, **kw):
    return Party(
        party_id="P", guild_id=1, channel_id=2, leader_id=99, leader_name="Leader",
        activity="Dungeon X", difficulty="Normal", notes="", slots=slots, **kw,
    )


def test_fill_places_longest_queued_first_and_clears_them():
    q = _wire()
    q.add(QueueEntry(10, "First", 1, "Dungeon X", "dps", created_at=100))
    q.add(QueueEntry(11, "Second", 1, "Dungeon X", "dps", created_at=200))
    q.add(QueueEntry(12, "Third", 1, "Dungeon X", "dps", created_at=300))
    q.add(QueueEntry(99, "Leader", 1, "Dungeon X", "dps", created_at=50))  # the leader

    party = _party({"dps": 2})
    party.add_or_move(99, "Leader", "dps")  # leader takes one of two dps slots

    placed = views.fill_party_from_queue(party)

    # Only one dps slot was open → the oldest non-leader queuer (user 10) fills it.
    assert placed == [10]
    assert party.find_member(10) is not None
    assert party.find_member(11) is None       # no room
    assert q.for_user(10, 1) == []             # cleared from queue
    assert {e.user_id for e in q.all()} == {11, 12, 99}


def test_fill_respects_requested_role_and_any():
    q = _wire()
    q.add(QueueEntry(10, "TankSeeker", 1, "Dungeon X", "tank", created_at=100))
    q.add(QueueEntry(11, "AnyRole", 1, None, None, created_at=200))  # any dungeon, any role

    party = _party({"tank": 1, "healer": 1})
    placed = views.fill_party_from_queue(party)

    assert set(placed) == {10, 11}
    assert party.find_member(10).role == "tank"
    assert party.find_member(11).role == "healer"  # any-role took the remaining slot


def test_fill_skips_specific_role_when_full():
    q = _wire()
    q.add(QueueEntry(10, "Wants tank", 1, "Dungeon X", "tank", created_at=100))
    party = _party({"tank": 1, "dps": 2})
    party.add_or_move(99, "Leader", "tank")  # tank already full

    placed = views.fill_party_from_queue(party)
    assert placed == []  # wanted tank specifically, none open


def test_fill_returns_empty_when_no_candidates():
    _wire()
    party = _party({"dps": 4})
    assert views.fill_party_from_queue(party) == []
