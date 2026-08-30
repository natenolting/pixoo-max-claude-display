"""Rate-limit utilization readings from Claude Code's usage cache.

The cache is written by the statusline, so it only refreshes while a
session is rendering. A window whose reset instant has passed reads 0
rather than reporting a stale figure — see the usage-screen semantics
ticket for why we don't fetch the API ourselves.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

CACHE_PATH = os.path.expanduser("~/.claude/cache/usage-cache.json")


@dataclass(frozen=True)
class Utilization:
    five_hour: int
    seven_day: int


def _window(entry: dict, now: datetime) -> int:
    if not isinstance(entry, dict):
        return 0
    resets_at = entry.get("resetsAt")
    if resets_at:
        try:
            if datetime.fromisoformat(resets_at) <= now:
                return 0  # window rolled over; the cached figure is spent
        except ValueError:
            pass
    try:
        return max(0, min(100, int(round(float(entry.get("percentage", 0))))))
    except (TypeError, ValueError):
        return 0


def read(path: str = CACHE_PATH) -> Utilization:
    """Current utilization; all-zero when the cache is missing or unreadable."""
    try:
        with open(path) as f:
            data = json.load(f).get("data", {})
    except (OSError, json.JSONDecodeError, AttributeError):
        return Utilization(0, 0)
    now = datetime.now(timezone.utc)
    return Utilization(_window(data.get("fiveHour"), now),
                       _window(data.get("weekly"), now))
