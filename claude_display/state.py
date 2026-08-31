"""Session state store: hook events + registry sweeps in, Aggregate State out.

Semantics per CONTEXT.md: precedence NEEDS_PERMISSION > WAITING > WORKING >
IDLE; WAITING demotes to IDLE after a configurable delay;
NEEDS_PERMISSION never demotes.
"""

import time
from dataclasses import dataclass, field

from . import config

PRECEDENCE = ["NEEDS_PERMISSION", "WAITING", "WORKING", "IDLE"]
WAITING_DEMOTION_S = config.WAITING_DEMOTION_S
# a clean exit DELETES the session's registry file (no dead-pid row ever
# appears) and the async SessionEnd hook can lose the race against process
# exit — so absence from the registry is itself the death signal, after a
# short grace for hook-before-registry startup ordering
NOT_IN_REGISTRY_GRACE_S = 15

EVENT_STATE = {
    "PermissionRequest": "NEEDS_PERMISSION",
    "UserPromptSubmit": "WORKING",
    "PreToolUse": "WORKING",
    "Stop": "WAITING",
    "SessionStart": "IDLE",
}

REGISTRY_STATE = {
    "busy": "WORKING",
    "waiting": "NEEDS_PERMISSION",
}


@dataclass
class _Session:
    state: str = "IDLE"
    since: float = field(default_factory=time.time)
    last_signal: float = field(default_factory=time.time)

    def set(self, state: str, now: float) -> None:
        if state != self.state:
            self.state = state
            self.since = now
        self.last_signal = now


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, _Session] = {}

    def ingest(self, event: dict) -> None:
        sid = event.get("session_id")
        name = event.get("hook_event_name")
        if not sid or not name:
            return
        now = time.time()
        if name == "SessionEnd":
            self._sessions.pop(sid, None)
            return
        state = EVENT_STATE.get(name)
        if state is None:
            return
        s = self._sessions.setdefault(sid, _Session())
        s.set(state, now)

    def sweep(self, rows: list[dict]) -> None:
        """rows: {sessionId, status, alive} for every tracked registry entry."""
        now = time.time()
        live = set()
        for row in rows:
            sid = row.get("sessionId")
            if not sid:
                continue
            if not row.get("alive"):
                self._sessions.pop(sid, None)
                continue
            live.add(sid)
            status = row.get("status")
            s = self._sessions.setdefault(sid, _Session())
            if status in REGISTRY_STATE:
                s.set(REGISTRY_STATE[status], now)
            elif status == "idle":
                # prompt gone / turn over; don't disturb an existing
                # WAITING or IDLE (would reset the demotion clock)
                if s.state in ("WORKING", "NEEDS_PERMISSION"):
                    s.set("WAITING", now)
                else:
                    s.last_signal = now
            else:
                s.last_signal = now  # null status: liveness only (Desktop)
        for sid, s in list(self._sessions.items()):
            if sid not in live and now - s.last_signal > NOT_IN_REGISTRY_GRACE_S:
                del self._sessions[sid]

    def aggregate(self) -> tuple[str, int]:
        now = time.time()
        for s in self._sessions.values():
            if s.state == "WAITING" and now - s.since > WAITING_DEMOTION_S:
                s.set("IDLE", now)
        if not self._sessions:
            return "OFF", 0
        for state in PRECEDENCE:
            count = sum(1 for s in self._sessions.values() if s.state == state)
            if count:
                return state, count
        return "OFF", 0
