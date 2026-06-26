"""Tests for the /lfg party-search filter (_find_parties)."""

import tempfile
import time

import bot
from src import views
from src.party import Party, PartyStore


def _seed():
    store = PartyStore(tempfile.mktemp(suffix=".json"))
    views.set_store(store)
    return store


def _party(pid, activity, slots, guild_id=1, **kw):
    return Party(
        party_id=pid, guild_id=guild_id, channel_id=2, leader_id=1, leader_name="L",
        activity=activity, difficulty="Normal", notes="", slots=slots, **kw,
    )


def test_find_parties_filters_full_and_other_guild():
    store = _seed()
    open_p = _party("A", "Dungeon X", {"dps": 4})
    full_p = _party("B", "Dungeon X", {"dps": 1})
    full_p.add_or_move(2, "x", "dps")  # now full
    other_guild = _party("C", "Dungeon X", {"dps": 4}, guild_id=2)
    for p in (open_p, full_p, other_guild):
        store.add(p)

    found = bot._find_parties(1)
    ids = {p.party_id for p in found}
    assert ids == {"A"}


def test_find_parties_by_activity_includes_extra_dungeons():
    store = _seed()
    p = _party("A", "Dungeon X", {"dps": 4}, extra_activities=["Dungeon Y"])
    store.add(p)
    assert {p.party_id for p in bot._find_parties(1, activity="Dungeon Y")} == {"A"}
    assert bot._find_parties(1, activity="Nope") == []


def test_find_parties_by_role():
    store = _seed()
    p = _party("A", "Dungeon X", {"tank": 1, "dps": 0})
    p.add_or_move(2, "t", "tank")  # tank now full, no dps slots at all
    store.add(p)
    assert bot._find_parties(1, role="tank") == []
    assert bot._find_parties(1, role="healer") == []  # no healer slots


def test_find_parties_excludes_expired():
    store = _seed()
    p = _party("A", "Dungeon X", {"dps": 4}, duration_seconds=60,
               start_at=time.time() - 3600)
    store.add(p)
    assert bot._find_parties(1) == []
