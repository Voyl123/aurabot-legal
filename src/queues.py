"""Party queue — players waiting for a party for a given dungeon / role.

When someone runs ``/queue`` and no matching party exists yet, we remember them
here. The moment a matching party is created, they get pinged. Mirrored to a
JSON file so the queue survives restarts.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from threading import Lock


DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "queue.json")


@dataclass
class QueueEntry:
    user_id: int
    user_name: str
    guild_id: int
    activity: str
    role: str | None = None  # tank / healer / dps, or None for "any role"
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()


class QueueStore:
    def __init__(self, path: str = DATA_FILE):
        self.path = path
        self._entries: list[QueueEntry] = []
        self._lock = Lock()
        self._load()

    # -- persistence -------------------------------------------------------- #
    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                self._entries = [QueueEntry(**e) for e in json.load(fh)]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._entries = []

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump([asdict(e) for e in self._entries], fh, indent=2)
        os.replace(tmp, self.path)

    # -- api ---------------------------------------------------------------- #
    def add(self, entry: QueueEntry) -> None:
        """Add an entry, replacing any existing one for the same user+activity."""
        with self._lock:
            self._entries = [
                e for e in self._entries
                if not (e.user_id == entry.user_id
                        and e.guild_id == entry.guild_id
                        and e.activity == entry.activity)
            ]
            self._entries.append(entry)
            self._save()

    def remove_user(self, user_id: int, guild_id: int | None = None) -> int:
        """Remove all of a user's queue entries (optionally within one guild)."""
        with self._lock:
            before = len(self._entries)
            self._entries = [
                e for e in self._entries
                if e.user_id != user_id or (guild_id is not None and e.guild_id != guild_id)
            ]
            removed = before - len(self._entries)
            if removed:
                self._save()
            return removed

    def remove_entries(self, entries: list[QueueEntry]) -> None:
        ids = {id(e) for e in entries}
        with self._lock:
            self._entries = [e for e in self._entries if id(e) not in ids]
            self._save()

    def for_user(self, user_id: int, guild_id: int) -> list[QueueEntry]:
        return [e for e in self._entries if e.user_id == user_id and e.guild_id == guild_id]

    def matches(self, guild_id: int, activities: list[str], open_roles: set[str]) -> list[QueueEntry]:
        """Queue entries that a newly-formed party would satisfy.

        ``open_roles`` is the set of role keys that still have space (plus the
        catch-all: an entry with ``role=None`` matches as long as *some* role
        is open).
        """
        any_open = bool(open_roles)
        out: list[QueueEntry] = []
        for e in self._entries:
            if e.guild_id != guild_id or e.activity not in activities:
                continue
            if e.role is None and any_open:
                out.append(e)
            elif e.role in open_roles:
                out.append(e)
        return out

    def all(self) -> list[QueueEntry]:
        return list(self._entries)
