"""Main loop: spool + registry in, frames out.

Cadence per the daemon-architecture ticket: 1 s ticks (spool drain +
render check), registry sweep every 3rd tick, forced refresh every 30 s.
"""

import argparse
import signal
import sys
import functools
import time

from .renderer import render
from .signals import SPOOL_DIR, RegistrySweeper, SpoolReader
from .state import SessionStore

# unbuffered logs: the daemon usually runs with stdout redirected
print = functools.partial(print, flush=True)

PIXOO_ADDR = "11-75-58-6e-bf-c1"
DRY_RUN_FRAME = "/tmp/claude-display/frame.png"
FORCED_REFRESH_S = 30


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
    print(f"[daemon] up; spool={args.spool} "
          f"{'DRY RUN' if args.dry_run else 'device=' + args.address}")

    while running:
        for event in spool.drain():
            store.ingest(event)
        if tick % 3 == 0:
            store.sweep(sweeper.sweep())
        tick += 1

        current = store.aggregate()
        now = time.time()
        if current != last_shown or now - last_push > FORCED_REFRESH_S:
            state, count = current
            img = render(state, count)
            if args.dry_run:
                img.save(DRY_RUN_FRAME)
                pushed = True
            else:
                if not brightness_set:
                    brightness_set = transport.set_brightness(args.brightness)
                pushed = transport.push(img)
            if current != last_shown:
                print(f"[daemon] {state} x{count}"
                      f"{'' if pushed else ' (device unreachable, will retry)'}")
            if pushed:
                last_shown = current
                last_push = now
        time.sleep(1)

    print("[daemon] shutting down")
    if transport is not None:
        transport.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
