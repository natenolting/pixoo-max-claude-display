"""Signal ingestion: hook-event spool reader + session-registry sweeper."""

import glob
import json
import os
import subprocess

SPOOL_DIR = "/tmp/claude-display/spool"
REGISTRY_GLOB = os.path.expanduser("~/.claude/sessions/*.json")


class SpoolReader:
    def __init__(self, spool_dir: str = SPOOL_DIR):
        self.spool_dir = spool_dir
        os.makedirs(spool_dir, exist_ok=True)

    def drain(self) -> list[dict]:
        events = []
        for path in sorted(glob.glob(os.path.join(self.spool_dir, "*.json"))):
            try:
                with open(path) as f:
                    events.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                pass
            try:
                os.unlink(path)
            except OSError:
                pass
        return events


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


class RegistrySweeper:
    """Enumerates live sessions from ~/.claude/sessions/<pid>.json.

    Excludes fleet-managed (cmux) sessions per the Tracked Session
    definition in CONTEXT.md; ancestry lookups are cached per pid.
    """

    def __init__(self):
        self._ancestry_cache: dict[int, bool] = {}

    def _is_cmux(self, pid: int) -> bool:
        cached = self._ancestry_cache.get(pid)
        if cached is not None:
            return cached
        excluded = False
        cur = pid
        for _ in range(10):
            try:
                out = subprocess.run(
                    ["ps", "-o", "ppid=,comm=", "-p", str(cur)],
                    capture_output=True, text=True, timeout=5,
                ).stdout.strip()
            except (subprocess.SubprocessError, OSError):
                break
            if not out:
                break
            ppid_s, _, comm = out.partition(" ")
            if "cmux" in os.path.basename(comm.strip()).lower():
                excluded = True
                break
            try:
                cur = int(ppid_s)
            except ValueError:
                break
            if cur <= 1:
                break
        self._ancestry_cache[pid] = excluded
        return excluded

    def sweep(self) -> list[dict]:
        rows = []
        for path in glob.glob(REGISTRY_GLOB):
            try:
                with open(path) as f:
                    d = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            pid = d.get("pid")
            sid = d.get("sessionId")
            if not sid or not pid:
                continue
            alive = _pid_alive(pid)
            if alive and self._is_cmux(pid):
                continue
            rows.append({"sessionId": sid, "status": d.get("status"), "alive": alive})
        return rows
