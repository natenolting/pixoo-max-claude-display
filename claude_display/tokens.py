"""Daily token count, polled off the main loop.

`npx ccusage daily --json` takes over two seconds, which would stall the
daemon's one-second tick and stutter the attention pulse, so it runs on a
background thread and the loop renders whatever the last good answer was.

The count is input + output only. ccusage's own `totalTokens` is dominated
by cache reads (79M of 82M on the day this was written), which makes it
enormous every day and therefore uninformative at a glance.
"""

import json
import subprocess
import threading
import time
from datetime import date

POLL_INTERVAL_S = 300
CCUSAGE_TIMEOUT_S = 90


def _today_input_output(payload: dict, today: str) -> int | None:
    """Sum input+output for today's aggregate row, or None if absent."""
    rows = payload.get("daily") or []
    for row in rows:
        # rows carry the date under "period"; "all" is the cross-agent total
        if row.get("period") == today and row.get("agent", "all") == "all":
            return int(row.get("inputTokens", 0)) + int(row.get("outputTokens", 0))
    return None


def fetch(today: str | None = None) -> int | None:
    today = today or date.today().isoformat()
    try:
        out = subprocess.run(
            ["npx", "ccusage", "daily", "--json"],
            capture_output=True, text=True, timeout=CCUSAGE_TIMEOUT_S,
        )
        if out.returncode != 0:
            return None
        return _today_input_output(json.loads(out.stdout), today)
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError, ValueError):
        return None


class TokenPoller:
    """Holds the most recent successful count; a failed poll keeps the old one."""

    def __init__(self, interval: float = POLL_INTERVAL_S):
        self.interval = interval
        self._value: int | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def value(self) -> int | None:
        with self._lock:
            return self._value

    def _run(self) -> None:
        while not self._stop.is_set():
            got = fetch()
            if got is not None:
                with self._lock:
                    self._value = got
            self._stop.wait(self.interval)


def compact(n: int) -> tuple[str, str]:
    """Render a count as (digits, unit) that fits 32 pixels: 293K, 1.2M, 82M."""
    if n < 1000:
        return str(n), ""
    if n < 1_000_000:
        return str(round(n / 1000)), "K"
    if n < 10_000_000:
        whole = n / 1_000_000
        return f"{whole:.1f}", "M"
    return str(round(n / 1_000_000)), "M"
