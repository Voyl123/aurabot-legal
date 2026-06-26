"""Parse a human-friendly start-time string into a Unix timestamp.

Supports:
  * ``now``
  * relative durations: ``30m``, ``2h``, ``1h30m``, ``90`` (minutes)
  * clock times: ``20:00`` / ``8:00pm`` (today, or tomorrow if already passed)
  * a Discord timestamp tag pasted straight from https://sesh.fyi/timestamp/
    e.g. ``<t:1750005400:F>``
  * a raw Unix timestamp, e.g. ``1750005400``

Returns ``None`` when the input is empty or can't be understood, in which case
the caller can simply omit the start time.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta


_REL_RE = re.compile(r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?", re.IGNORECASE)
_DURATION_RE = re.compile(r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?", re.IGNORECASE)
_CLOCK_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*(am|pm)?$", re.IGNORECASE)
# A Discord timestamp tag as produced by sesh.fyi: <t:1750005400:F>
_TAG_RE = re.compile(r"<t:(\d+)(?::[a-z])?>", re.IGNORECASE)

# Anything from this epoch onward (2001-09-09) is treated as an absolute Unix
# timestamp rather than "minutes from now".
_EPOCH_FLOOR = 1_000_000_000


def parse_start_time(text: str | None, now: float | None = None) -> float | None:
    if not text:
        return None
    text = text.strip().lower()
    base = now if now is not None else time.time()

    if text in {"now", "asap", "0"}:
        return base

    # A Discord timestamp tag pasted from sesh.fyi, e.g. "<t:1750005400:f>".
    tag = _TAG_RE.search(text)
    if tag:
        return float(tag.group(1))

    # A bare Unix timestamp (also what sesh.fyi can give you).
    if text.isdigit() and int(text) >= _EPOCH_FLOOR:
        return float(int(text))

    # Pure number → minutes from now.
    if text.isdigit():
        return base + int(text) * 60

    # Clock time, e.g. "20:00" or "8:30pm".
    clock = _CLOCK_RE.match(text)
    if clock:
        hour = int(clock.group(1))
        minute = int(clock.group(2))
        meridiem = clock.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        if 0 <= hour < 24 and 0 <= minute < 60:
            dt_now = datetime.fromtimestamp(base)
            target = dt_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target.timestamp() <= base:
                target += timedelta(days=1)  # roll to tomorrow
            return target.timestamp()

    # Relative duration, e.g. "1h30m", "45m", "2h".
    m = _REL_RE.fullmatch(text.replace(" ", ""))
    if m and (m.group(1) or m.group(2)):
        hours = int(m.group(1) or 0)
        minutes = int(m.group(2) or 0)
        if hours or minutes:
            return base + hours * 3600 + minutes * 60

    return None


def parse_duration(text: str | None) -> int | None:
    """Parse a "how long" string into seconds.

    Supports ``2h``, ``90m``, ``1h30m`` and a bare number (minutes). Returns
    ``None`` for empty / unparseable input.
    """
    if not text:
        return None
    text = text.strip().lower()
    if text.isdigit():  # bare number → minutes
        minutes = int(text)
        return minutes * 60 if minutes > 0 else None
    m = _DURATION_RE.fullmatch(text.replace(" ", ""))
    if m and (m.group(1) or m.group(2)):
        seconds = int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60
        return seconds or None
    return None


def humanize_duration(seconds: int | None) -> str:
    """Render seconds as a short human string, e.g. ``2h``, ``1h30m``, ``45m``."""
    if not seconds or seconds <= 0:
        return ""
    hours, minutes = divmod(seconds // 60, 60)
    if hours and minutes:
        return f"{hours}h{minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"
