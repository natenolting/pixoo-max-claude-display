"""Panel brightness: day, night window, and away-from-keyboard.

Decided in the night-behavior ticket. The panel dims when the user is Away
(screen locked) or inside the Night Window. An attention state pulls it
back to full brightness only while the user is present — a bright red
panel wakes nobody in an empty room.
"""

from datetime import datetime

from . import config

DAY_BRIGHTNESS = config.DAY_BRIGHTNESS
NIGHT_BRIGHTNESS = config.NIGHT_BRIGHTNESS
NIGHT_START_HOUR = config.NIGHT_START_HOUR
NIGHT_END_HOUR = config.NIGHT_END_HOUR


def in_night_window(now: datetime | None = None) -> bool:
    hour = (now or datetime.now()).hour
    return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR


def is_away() -> bool:
    """True when the screen is locked. Unreadable session state reads as
    present, so a failure here leaves the panel usable rather than dark."""
    if not config.DIM_WHEN_LOCKED:
        return False
    try:
        from Quartz import CGSessionCopyCurrentDictionary

        session = CGSessionCopyCurrentDictionary()
        if not session:
            return False
        return bool(session.get("CGSSessionScreenIsLocked", False))
    except Exception:
        return False


def target(away: bool, night: bool, demands_attention: bool) -> int:
    """Brightness for the current conditions."""
    if away:
        return NIGHT_BRIGHTNESS  # nobody is looking; attention cannot override
    if night:
        return DAY_BRIGHTNESS if demands_attention else NIGHT_BRIGHTNESS
    return DAY_BRIGHTNESS
