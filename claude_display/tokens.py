"""Daily token count, polled off the main loop.

`npx ccusage daily --json` takes over two seconds, which would stall the
daemon's one-second tick and stutter the attention pulse, so it runs on a
background thread and the loop renders whatever the last good answer was.

The count is input + output only. ccusage's own `totalTokens` is dominated
by cache reads (79M of 82M on the day this was written), which makes it
enormous every day and therefore uninformative at a glance.
"""

import json
import os
import shutil
import subprocess
import threading
from datetime import date

from . import config
from .log import log as _log

POLL_INTERVAL_S = config.TOKEN_POLL_S
CCUSAGE_TIMEOUT_S = 90

# launchd hands agents a bare PATH (/usr/bin:/bin:/usr/sbin:/sbin), which does
# not include Homebrew, so npx is invisible unless we go looking for it
NPX_FALLBACKS = (
    "/opt/homebrew/bin/npx",
    "/usr/local/bin/npx",
    os.path.expanduser("~/.local/bin/npx"),
)


def _find_npx() -> str | None:
    found = shutil.which("npx")
    if found:
        return found
    for path in NPX_FALLBACKS:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _today_input_output(payload: dict, today: str) -> int | None:
    """Sum input+output for today's aggregate row, or None if absent."""
    rows = payload.get("daily") or []
    for row in rows:
        # rows carry the date under "period"; "all" is the cross-agent total
        if row.get("period") == today and row.get("agent", "all") == "all":
            return int(row.get("inputTokens", 0)) + int(row.get("outputTokens", 0))
    return None


def fetch(today: str | None = None) -> int | None:
    """Today's input+output count, or None with a reason logged.

    Every failure path is reported: a silent None cannot be told apart from
    a genuine "no usage yet today", which hid a missing npx for a full
    deploy cycle.
    """
    today = today or date.today().isoformat()
    npx = _find_npx()
    if npx is None:
        _log("[tokens] npx not found; token screen will stay blank")
        return None
    # npx shells out to node, which is in the same bin directory and equally
    # invisible on launchd's PATH — hand the child a PATH that includes it
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(
        [os.path.dirname(npx), env.get("PATH", "/usr/bin:/bin")]
    )
    try:
        out = subprocess.run(
            [npx, "ccusage", "daily", "--json"],
            capture_output=True, text=True, timeout=CCUSAGE_TIMEOUT_S, env=env,
        )
    except subprocess.TimeoutExpired:
        _log(f"[tokens] ccusage timed out after {CCUSAGE_TIMEOUT_S}s")
        return None
    except (subprocess.SubprocessError, OSError) as e:
        _log(f"[tokens] could not run ccusage: {e}")
        return None
    if out.returncode != 0:
        _log(f"[tokens] ccusage exited {out.returncode}: "
              f"{out.stderr.strip()[:120]}")
        return None
    try:
        value = _today_input_output(json.loads(out.stdout), today)
    except (json.JSONDecodeError, ValueError) as e:
        _log(f"[tokens] could not parse ccusage output: {e}")
        return None
    if value is None:
        _log(f"[tokens] no row for {today} in ccusage output")
    return value


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
