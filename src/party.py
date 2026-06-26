"""Party data model + lightweight JSON persistence.

A :class:`Party` is the source of truth for a single recruitment post.  The
:class:`PartyStore` keeps every party in memory and mirrors it to a JSON file
so parties survive a bot restart (the persistent views are re-registered on
startup so the buttons keep working).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from threading import Lock

from . import config


DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "parties.json")


@dataclass
class Member:
    user_id: int
    display_name: str
    role: str  # one of config.ROLES keys
    gear_score: int | None = None  # the member's own Gear Score / CP
    weapons: list[str] = field(default_factory=list)  # canonical weapon names


@dataclass
class Party:
    party_id: str
    guild_id: int
    channel_id: int
    leader_id: int
    leader_name: str
    activity: str  # the primary dungeon / activity (used as the card title)
    difficulty: str
    notes: str
    # role key -> max slots for that role
    slots: dict[str, int]
    # Minimum Gear Score / Combat Power (CP) the leader wants applicants to have.
    # ``None`` means no requirement (informational only — not enforced on join).
    min_gear_score: int | None = None
    # Voice channel for the party to gather in. If the leader pastes a same-server
    # channel link/ID we keep the id (rendered as a clickable <#id>); any other URL
    # is kept verbatim in ``voice_link`` and rendered as a hyperlink.
    voice_channel_id: int | None = None
    voice_link: str | None = None
    # Additional dungeons this party also wants to run (besides ``activity``).
    extra_activities: list[str] = field(default_factory=list)
    # How long the party plans to run, in seconds (None = open-ended).
    duration_seconds: int | None = None
    members: list[Member] = field(default_factory=list)
    message_id: int | None = None
    created_at: float = field(default_factory=time.time)
    start_at: float | None = None
    closed: bool = False

    # -- derived helpers ---------------------------------------------------- #
    @property
    def capacity(self) -> int:
        return sum(self.slots.values())

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def is_full(self) -> bool:
        return self.size >= self.capacity

    @property
    def all_activities(self) -> list[str]:
        """The primary activity plus any extra dungeons, de-duplicated."""
        seen: list[str] = []
        for a in [self.activity, *self.extra_activities]:
            if a and a not in seen:
                seen.append(a)
        return seen

    @property
    def end_at(self) -> float | None:
        """When the party is scheduled to wrap up, if a duration was set."""
        if self.duration_seconds is None:
            return None
        return (self.start_at or self.created_at) + self.duration_seconds

    @property
    def is_expired(self) -> bool:
        end = self.end_at
        return end is not None and time.time() > end

    def wants(self, activity: str) -> bool:
        """True if this party is running the given activity."""
        return activity in self.all_activities

    @property
    def has_open_slot(self) -> bool:
        return any(self.open_slots(r) > 0 for r in self.slots)

    def members_for(self, role: str) -> list[Member]:
        return [m for m in self.members if m.role == role]

    def open_slots(self, role: str) -> int:
        return max(0, self.slots.get(role, 0) - len(self.members_for(role)))

    def find_member(self, user_id: int) -> Member | None:
        return next((m for m in self.members if m.user_id == user_id), None)

    # -- mutations ---------------------------------------------------------- #
    def add_or_move(
        self, user_id: int, display_name: str, role: str,
        gear_score: int | None = None, weapons: list[str] | None = None,
    ) -> tuple[bool, str]:
        """Add a member, or move them to a new role.

        Returns ``(changed, message)``.
        """
        if self.closed:
            return False, "This party has been disbanded."
        if role not in self.slots:
            return False, "That role isn't part of this party."

        existing = self.find_member(user_id)
        if existing and existing.role == role:
            return False, f"You're already signed up as **{config.ROLES[role].label}**."

        if self.open_slots(role) <= 0:
            return False, f"All **{config.ROLES[role].label}** slots are full."

        if existing:
            existing.role = role
            if gear_score is not None:
                existing.gear_score = gear_score
            if weapons:
                existing.weapons = weapons
            return True, f"Moved you to **{config.ROLES[role].label}**."

        self.members.append(Member(user_id, display_name, role, gear_score, weapons or []))
        return True, f"You joined as **{config.ROLES[role].label}**."

    def remove(self, user_id: int) -> tuple[bool, str]:
        member = self.find_member(user_id)
        if not member:
            return False, "You aren't in this party."
        self.members.remove(member)
        return True, "You left the party."

    # -- serialisation ------------------------------------------------------ #
    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Party":
        members = [Member(**m) for m in d.get("members", [])]
        d = {**d, "members": members}
        return cls(**d)


class PartyStore:
    """In-memory store of parties keyed by ``party_id``, mirrored to JSON."""

    def __init__(self, path: str = DATA_FILE):
        self.path = path
        self._parties: dict[str, Party] = {}
        self._lock = Lock()
        self._load()

    # -- persistence -------------------------------------------------------- #
    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            for pid, pdata in raw.items():
                self._parties[pid] = Party.from_dict(pdata)
        except (json.JSONDecodeError, TypeError, KeyError):
            # Corrupt file — start fresh rather than crash the bot.
            self._parties = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({pid: p.to_dict() for pid, p in self._parties.items()}, fh, indent=2)
        os.replace(tmp, self.path)

    # -- api ---------------------------------------------------------------- #
    def add(self, party: Party) -> None:
        with self._lock:
            self._parties[party.party_id] = party
            self._save()

    def get(self, party_id: str) -> Party | None:
        return self._parties.get(party_id)

    def save(self) -> None:
        with self._lock:
            self._save()

    def all(self) -> list[Party]:
        return list(self._parties.values())

    def active(self) -> list[Party]:
        return [p for p in self._parties.values() if not p.closed]
