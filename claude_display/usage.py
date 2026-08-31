"""Rate-limit utilization.

Read live from the OAuth usage endpoint, on a background thread so the
display loop never blocks on the network. `~/.claude/cache/usage-cache.json`
— written by the status line — is only a fallback, because it refreshes just
when a session renders one: it was found 70 minutes stale, reporting 7% when
the true figure was 18%, and a confidently wrong number defeats the point of
the face.

The access token is read the same way the user's own status line reads it
and is used for exactly one request. It is never logged, cached, or written
anywhere.
"""

import json
import os
import subprocess
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from . import config
from .log import log as _log

CACHE_PATH = os.path.expanduser("~/.claude/cache/usage-cache.json")
CREDENTIALS_PATH = os.path.expanduser("~/.claude/.credentials.json")
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
REQUEST_TIMEOUT_S = 10


@dataclass(frozen=True)
class Utilization:
    five_hour: int
    seven_day: int


def _pct(value) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


# --------------------------------------------------------------- live fetch
def _access_token() -> str | None:
    """The OAuth token, from the credentials file or the macOS keychain."""
    try:
        with open(CREDENTIALS_PATH) as f:
            token = json.load(f).get("claudeAiOauth", {}).get("accessToken")
            if token:
                return token
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    try:
        raw = subprocess.run(
            ["security", "find-generic-password", "-s",
             "Claude Code-credentials", "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if raw.returncode == 0:
            return json.loads(raw.stdout.strip()).get("claudeAiOauth", {}).get("accessToken")
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError, AttributeError):
        pass
    return None


def fetch() -> Utilization | None:
    """Live utilization, or None with a reason logged."""
    token = _access_token()
    if not token:
        _log("[usage] no credentials found; falling back to the status line cache")
        return None
    req = urllib.request.Request(USAGE_URL, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "anthropic-beta": "oauth-2025-04-20",
    })
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        _log(f"[usage] usage endpoint returned {e.code}")
        return None
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as e:
        _log(f"[usage] could not reach the usage endpoint: {e}")
        return None
    five = payload.get("five_hour") or {}
    seven = payload.get("seven_day") or {}
    if "utilization" not in five:
        _log("[usage] response had no five-hour window")
        return None
    return Utilization(_pct(five.get("utilization")), _pct(seven.get("utilization")))


# ------------------------------------------------------------ cache fallback
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
    return _pct(entry.get("percentage", 0))


def read(path: str = CACHE_PATH) -> Utilization:
    """The status line's cached figures; all-zero when unreadable."""
    try:
        with open(path) as f:
            data = json.load(f).get("data", {})
    except (OSError, json.JSONDecodeError, AttributeError):
        return Utilization(0, 0)
    now = datetime.now(timezone.utc)
    return Utilization(_window(data.get("fiveHour"), now),
                       _window(data.get("weekly"), now))


class UsagePoller:
    """Live figures when the endpoint answers, the cache when it does not."""

    def __init__(self, interval: float = config.USAGE_POLL_S):
        self.interval = interval
        self._value = read()
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def value(self) -> Utilization:
        with self._lock:
            return self._value

    def _run(self) -> None:
        while not self._stop.is_set():
            got = fetch() or read()
            with self._lock:
                self._value = got
            self._stop.wait(self.interval)
