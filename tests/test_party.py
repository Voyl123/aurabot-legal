"""Tests for the Party model, embed rendering and JSON persistence."""

import tempfile

from src.party import Party, PartyStore
from src.embeds import build_party_embed


def make_party(**overrides) -> Party:
    base = dict(
        party_id="P1", guild_id=1, channel_id=2, leader_id=10, leader_name="Leader",
        activity="Field Boss", difficulty="Hard", notes="", slots={"tank": 1, "healer": 1, "dps": 2},
    )
    base.update(overrides)
    return Party(**base)


def test_join_move_leave():
    p = make_party()
    changed, _ = p.add_or_move(10, "Leader", "tank")
    assert changed and p.size == 1

    # Already that role -> no change
    changed, _ = p.add_or_move(10, "Leader", "tank")
    assert not changed

    # Move to another role
    changed, _ = p.add_or_move(10, "Leader", "dps")
    assert changed and p.find_member(10).role == "dps"
    assert p.size == 1  # still one member, just moved

    changed, _ = p.remove(10)
    assert changed and p.size == 0


def test_role_capacity_enforced():
    p = make_party()
    assert p.add_or_move(1, "a", "dps")[0]
    assert p.add_or_move(2, "b", "dps")[0]
    # third DPS rejected, only two slots
    changed, msg = p.add_or_move(3, "c", "dps")
    assert not changed and "full" in msg.lower()


def test_full_and_open_slots():
    p = make_party()
    p.add_or_move(1, "a", "tank")
    p.add_or_move(2, "b", "healer")
    p.add_or_move(3, "c", "dps")
    assert p.open_slots("dps") == 1
    p.add_or_move(4, "d", "dps")
    assert p.is_full and p.open_slots("dps") == 0


def test_closed_party_rejects_joins():
    p = make_party(closed=True)
    changed, msg = p.add_or_move(1, "a", "tank")
    assert not changed and "disbanded" in msg.lower()


def test_persistence_roundtrip():
    p = make_party(start_at=1750005400.0)
    p.add_or_move(10, "Leader", "tank")
    p.message_id = 555

    path = tempfile.mktemp(suffix=".json")
    store = PartyStore(path)
    store.add(p)

    reloaded = PartyStore(path).get("P1")
    assert reloaded is not None
    assert reloaded.start_at == 1750005400.0
    assert reloaded.message_id == 555
    assert [(m.display_name, m.role) for m in reloaded.members] == [("Leader", "tank")]


def test_embed_shows_timestamp_and_roster():
    p = make_party(start_at=1750005400.0, notes="CP 4k+")
    p.add_or_move(10, "Leader", "tank")
    embed = build_party_embed(p)

    assert "<t:1750005400:f>" in embed.description
    assert "<t:1750005400:R>" in embed.description
    field_names = [f.name for f in embed.fields]
    assert any("Tank" in n for n in field_names)
    assert any("Still need" in n for n in field_names)
    assert any("Notes" in n for n in field_names)


def test_embed_shows_gear_score_when_set():
    p = make_party(min_gear_score=4000)
    assert "4,000+ CP" in build_party_embed(p).description


def test_embed_omits_gear_score_when_unset():
    p = make_party()
    assert "CP required" not in build_party_embed(p).description


def test_gear_score_persists():
    p = make_party(min_gear_score=3500, voice_channel_id=12345)
    p.add_or_move(10, "Leader", "tank", gear_score=4800)
    path = tempfile.mktemp(suffix=".json")
    PartyStore(path).add(p)

    reloaded = PartyStore(path).get("P1")
    assert reloaded.min_gear_score == 3500
    assert reloaded.voice_channel_id == 12345
    assert reloaded.find_member(10).gear_score == 4800


def test_embed_shows_member_gear_score_and_voice():
    p = make_party(voice_channel_id=999888)
    p.add_or_move(10, "Leader", "dps", gear_score=4200)
    embed = build_party_embed(p)
    # Voice channel mention in the header...
    assert "<#999888>" in embed.description
    # ...and the member's gear score somewhere in the roster fields.
    assert any("4,200" in (f.value or "") for f in embed.fields)


def test_embed_shows_class_title_from_weapons():
    p = make_party()
    p.add_or_move(10, "Voyl", "dps", gear_score=4100, weapons=["Greatsword", "Daggers"])
    embed = build_party_embed(p)
    dps_field = next(f for f in embed.fields if "DPS" in f.name)
    assert "Bladedancer" in dps_field.value
    assert "4,100" in dps_field.value


def test_embed_renders_voice_link_fallback():
    p = make_party(voice_link="https://discord.gg/abcd")
    assert "[Voice](https://discord.gg/abcd)" in build_party_embed(p).description


def test_all_activities_dedupes():
    p = make_party(activity="A", extra_activities=["B", "A", "C"])
    assert p.all_activities == ["A", "B", "C"]
    assert p.wants("B") and not p.wants("Z")


def test_duration_end_and_expiry():
    import time
    p = make_party(duration_seconds=3600, start_at=time.time() - 10)
    # ended 10s in the past + 3600 still in the future → not expired
    assert not p.is_expired
    past = make_party(duration_seconds=60, start_at=time.time() - 3600)
    assert past.is_expired


def test_has_open_slot():
    p = make_party(slots={"tank": 1, "healer": 0, "dps": 0})
    assert p.has_open_slot
    p.add_or_move(1, "a", "tank")
    assert not p.has_open_slot


def test_embed_marks_leader_with_crown():
    p = make_party()
    p.add_or_move(10, "Leader", "tank")
    p.add_or_move(11, "Member", "healer", gear_score=4000)
    embed = build_party_embed(p)
    tank_field = next(f for f in embed.fields if "Tank" in f.name)
    healer_field = next(f for f in embed.fields if "Healer" in f.name)
    assert "👑" in tank_field.value          # leader gets the crown
    assert "👑" not in healer_field.value     # regular member does not
