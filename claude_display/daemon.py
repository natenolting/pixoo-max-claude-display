"""Main loop: spool + registry in, frames out.

Cadence per the daemon-architecture ticket: 1 s ticks (spool drain +
render check), registry sweep every 3rd tick, forced refresh every 30 s.
Rotation per the usage-screen semantics ticket: the State Screen holds the
display alone whenever a session needs the user; otherwise the two faces
alternate.
"""

import argparse
import signal
import sys
import functools
import time

from . import usage
from .renderer import render, render_usage
from .signals import SPOOL_DIR, RegistrySweeper, SpoolReader
from .state import SessionStore

# unbuffered logs: the daemon usually runs with stdout redirected
print = functools.partial(print, flush=True)

PIXOO_ADDR = "11-75-58-6e-bf-c1"
DRY_RUN_FRAME = "/tmp/claude-display/frame.png"
FORCED_REFRESH_S = 30
USAGE_POLL_S = 60
STATE_FACE_S = 12
USAGE_FACE_S = 8
# states that hold the display alone — never hide "Claude needs you"
DEMANDS_ATTENTION = ("NEEDS_PERMISSION", "WAITING")


def choose_face(state, count, util, clock):
    """Pick the face to show. Returns a tuple that doubles as a change key.

    `clock` is seconds since rotation last became eligible; it resets while
    a session demands attention so the State Screen always gets a full turn
    first once things calm down.
    """
    if state in DEMANDS_ATTENTION:
        return ("state", state, count)
    if clock % (STATE_FACE_S + USAGE_FACE_S) < STATE_FACE_S:
        return ("state", state, count)
    return ("usage", util.five_hour, util.seven_day)


def render_face(face):
    if face[0] == "usage":
        return render_usage(face[1], face[2])
    return render(face[1], face[2])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="claude_display")
    ap.add_argument("--dry-run", action="store_true",
                    help=f"render to {DRY_RUN_FRAME} instead of the device")
    ap.add_argument("--address", default=PIXOO_ADDR)
    ap.add_argument("--brightness", type=int, default=80)
    ap.add_argument("--spool", default=SPOOL_DIR)
    args = ap.parse_args(argv)

    spool = SpoolReader(args.spool)
    sweeper = RegistrySweeper()
    store = SessionStore()
    transport = None
    if not args.dry_run:
        from .transport import PixooTransport
        transport = PixooTransport(args.address)

    running = True

    def _stop(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    last_shown = None
    last_push = 0.0
    brightness_set = False
    tick = 0
    util = usage.read()
    last_usage_poll = time.monotonic()
    rotation_start = time.monotonic()
    print(f"[daemon] up; spool={args.spool} "
          f"{'DRY RUN' if args.dry_run else 'device=' + args.address}")

    while running:
        for event in spool.drain():
            store.ingest(event)
        if tick % 3 == 0:
            store.sweep(sweeper.sweep())
        tick += 1

        mono = time.monotonic()
        if mono - last_usage_poll >= USAGE_POLL_S:
            util = usage.read()
            last_usage_poll = mono

        state, count = store.aggregate()
        if state in DEMANDS_ATTENTION:
            rotation_start = mono
        face = choose_face(state, count, util, mono - rotation_start)

        now = time.time()
        if face != last_shown or now - last_push > FORCED_REFRESH_S:
            img = render_face(face)
            if args.dry_run:
                img.save(DRY_RUN_FRAME)
                pushed = True
            else:
                if not brightness_set:
                    brightness_set = transport.set_brightness(args.brightness)
                pushed = transport.push(img)
            if face != last_shown:
                label = (f"{face[1]} x{face[2]}" if face[0] == "state"
                         else f"usage 5h={face[1]}% 7d={face[2]}%")
                print(f"[daemon] {label}"
                      f"{'' if pushed else ' (device unreachable, will retry)'}")
            if pushed:
                last_shown = face
                last_push = now
        time.sleep(1)

    print("[daemon] shutting down")
    if transport is not None:
        transport.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
