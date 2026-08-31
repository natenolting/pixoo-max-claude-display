"""Settings, read once at import from an env file beside the repo.

Precedence: a real environment variable beats the file, which beats the
built-in default. The file is per-machine and gitignored; `.env.example`
documents every key.

Deliberately hand-rolled rather than pulling in python-dotenv: the format
is KEY=value, and a display daemon should not grow a dependency for
fifteen lines of parsing.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path(os.environ.get("CLAUDE_DISPLAY_ENV", REPO_ROOT / ".env"))


def _load(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        text = path.read_text()
    except OSError:
        return values  # no file is fine; every key has a default
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, raw = line.partition("=")
        raw = raw.strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
            raw = raw[1:-1]
        values[key.strip()] = raw
    return values


_FILE = _load(ENV_PATH)


def get(name: str, default, cast=str):
    """Value for `name`, falling back to `default` if unset or unparseable."""
    raw = os.environ.get(name, _FILE.get(name))
    if raw is None or raw == "":
        return default
    try:
        return cast(raw)
    except (TypeError, ValueError):
        print(f"[config] {name}={raw!r} is not valid; using {default!r}")
        return default


def _as_bool(raw: str) -> bool:
    return raw.strip().lower() in ("1", "true", "yes", "on")


def normalise_address(addr: str) -> str:
    """IOBluetooth wants dash-separated hex; accept colons too."""
    return addr.strip().replace(":", "-").lower()


# --- device ---------------------------------------------------------------
PIXOO_ADDRESS = normalise_address(get("PIXOO_ADDRESS", ""))

# --- faces ----------------------------------------------------------------
STATE_FACE_S = get("STATE_FACE_S", 12, int)
USAGE_FACE_S = get("USAGE_FACE_S", 8, int)
TOKENS_FACE_S = get("TOKENS_FACE_S", 8, int)
SHOW_USAGE_FACE = get("SHOW_USAGE_FACE", True, _as_bool)
SHOW_TOKENS_FACE = get("SHOW_TOKENS_FACE", True, _as_bool)

# --- brightness -----------------------------------------------------------
DAY_BRIGHTNESS = get("DAY_BRIGHTNESS", 80, int)
NIGHT_BRIGHTNESS = get("NIGHT_BRIGHTNESS", 15, int)
NIGHT_START_HOUR = get("NIGHT_START_HOUR", 22, int)
NIGHT_END_HOUR = get("NIGHT_END_HOUR", 7, int)
DIM_WHEN_LOCKED = get("DIM_WHEN_LOCKED", True, _as_bool)

# --- sessions -------------------------------------------------------------
# Sessions managed by cmux were excluded originally, on the theory that a
# fleet of idle ones would drown the signal. Precedence already handles that
# — one working session among eleven idle ones still reads WORKING — and for
# anyone who runs Claude inside cmux, excluding them means tracking nothing.
TRACK_CMUX_SESSIONS = get("TRACK_CMUX_SESSIONS", True, _as_bool)

# --- behaviour ------------------------------------------------------------
WAITING_DEMOTION_S = get("WAITING_DEMOTION_MIN", 30, int) * 60
TOKEN_POLL_S = get("TOKEN_POLL_MIN", 5, int) * 60
USAGE_POLL_S = get("USAGE_POLL_MIN", 2, int) * 60
SPOOL_DIR = get("SPOOL_DIR", "/tmp/claude-display/spool")
