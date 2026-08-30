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

from . import brightness, usage
from .renderer import render, render_blank, render_usage
from .signals import SPOOL_DIR, RegistrySweeper, SpoolReader
from .state import SessionStore

# unbuffered logs: the daemon usually runs with stdout redirected
print = functools.partial(print, flush=True)

PIXOO_ADDR = "11-75-58-6e-bf-c1"
DRY_RUN_FRAME = "/tmp/claude-display/frame.png"
FORCED_REFRESH_S = 30
USAGE_POLL_S = 60
LOCK_POLL_S = 5
STATE_FACE_S = 12
USAGE_FACE_S = 8
# states that hold the display alone — never hide "Claude needs you"
DEMANDS_ATTENTION = ("NEEDS_PERMISSION", "WAITING")
# half-period of the attention pulse; motion is the only proof of liveness,
# since a frame frozen by a lost link can never be overwritten with a marker
BLINK_HALF_PERIOD_S = 1.0


def choose_face(state, count, util, clock, blink=False):
    """Pick the face to show. Returns a tuple that doubles as a change key.

    `clock` is seconds since rotation last became eligible; it resets while
    a session demands attention so the State Screen always gets a full turn
    first once things calm down. `blink` is the pulse phase, carried in the
    key so the daemon redraws on every phase flip.
    """
    if state in DEMANDS_ATTENTION:
        return ("state", state, count, blink)
    if clock % (STATE_FACE_S + USAGE_FACE_S) < STATE_FACE_S:
        return ("state", state, count, False)
    return ("usage", util.five_hour, util.seven_day)


def render_face(face):
    if face[0] == "usage":
        return render_usage(face[1], face[2])
    return render(face[1], face[2], pulse=face[3])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="claude_display")
    ap.add_argument("--dry-run", action="store_true",
                    help=f"render to {DRY_RUN_FRAME} instead of the device")
    ap.add_argument("--address", default=PIXOO_ADDR)
    ap.add_argument("--brightness", type=int, default=brightness.DAY_BRIGHTNESS,
                    help="daytime panel brightness (night dims automatically)")
    ap.add_argument("--spool", default=SPOOL_DIR)
    args = ap.parse_args(argv)
    brightness.DAY_BRIGHTNESS = args.brightness

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
    shown_brightness = None
    tick = 0
    util = usage.read()
    away = brightness.is_away()
    last_usage_poll = last_lock_poll = time.monotonic()
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
        if mono - last_lock_poll >= LOCK_POLL_S:
            away = brightness.is_away()
            last_lock_poll = mono

        state, count = store.aggregate()
        if state in DEMANDS_ATTENTION:
            rotation_start = mono
        blink = int(mono / BLINK_HALF_PERIOD_S) % 2 == 1
        face = choose_face(state, count, util, mono - rotation_start, blink)

        want_brightness = brightness.target(
            away, brightness.in_night_window(), state in DEMANDS_ATTENTION
        )
        if want_brightness != shown_brightness:
            if args.dry_run or transport.set_brightness(want_brightness):
                reason = "away" if away else (
                    "night" if want_brightness == brightness.NIGHT_BRIGHTNESS else "day")
                print(f"[daemon] brightness {want_brightness} ({reason})")
                shown_brightness = want_brightness

        now = time.time()
        if face != last_shown or now - last_push > FORCED_REFRESH_S:
            img = render_face(face)
            if args.dry_run:
                img.save(DRY_RUN_FRAME)
                pushed = True
            else:
                pushed = transport.push(img)
            # the pulse flips every tick; log only real face changes
            changed = last_shown is None or face[:3] != last_shown[:3]
            if changed:
                label = (f"{face[1]} x{face[2]}" if face[0] == "state"
                         else f"usage 5h={face[1]}% 7d={face[2]}%")
                print(f"[daemon] {label}"
                      f"{'' if pushed else ' (device unreachable, will retry)'}")
            if pushed:
                last_shown = face
                last_push = now
        time.sleep(1)

    # blank the panel on the way out: a dark display unambiguously means
    # nothing is driving it, rather than a stale frame that looks healthy
    print("[daemon] shutting down")
    if args.dry_run:
        render_blank().save(DRY_RUN_FRAME)
    elif transport is not None:
        transport.push(render_blank())
        transport.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
