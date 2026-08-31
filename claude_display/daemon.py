"""Main loop: spool + registry in, frames out.

Cadence per the daemon-architecture ticket: 1 s ticks (spool drain +
render check), registry sweep every 3rd tick, forced refresh every 30 s.
Rotation per the usage-screen semantics ticket: the State Screen holds the
display alone whenever a session needs the user; otherwise the faces take
turns.
"""

import argparse
import signal
import sys
import time

from . import brightness, config, tokens as tokens_mod, usage
from .log import log as _log
from .renderer import render, render_blank, render_tokens, render_usage
from .signals import SPOOL_DIR, RegistrySweeper, SpoolReader
from .state import SessionStore



DRY_RUN_FRAME = "/tmp/claude-display/frame.png"
FORCED_REFRESH_S = 30
USAGE_POLL_S = 60
LOCK_POLL_S = 5
STATE_FACE_S = config.STATE_FACE_S
# a face turned off in config gets no time in the rotation
USAGE_FACE_S = config.USAGE_FACE_S if config.SHOW_USAGE_FACE else 0
TOKENS_FACE_S = config.TOKENS_FACE_S if config.SHOW_TOKENS_FACE else 0
# states that hold the display alone — never hide "Claude needs you"
DEMANDS_ATTENTION = ("NEEDS_PERMISSION", "WAITING")
# half-period of the attention pulse; motion is the only proof of liveness,
# since a frame frozen by a lost link can never be overwritten with a marker
BLINK_HALF_PERIOD_S = 1.0
# how long the panel may stay dark before the log says so again; a single
# "unreachable" line an hour ago is indistinguishable from a brief blip
OUTAGE_REMINDER_S = 300


def outage_announcement(down_for, already_logged, since_last_notice):
    """What, if anything, to say about an unreachable device.

    Returns "first", "reminder", or None. Extracted from the loop because
    inline it grew three interacting conditions and produced two wrong
    answers in a row: reporting a failure during the startup settle window
    when nothing had been tried yet, and firing the five-minute reminder
    immediately because its timestamp started at zero.
    """
    if down_for <= 0:
        return None  # nothing has failed — e.g. still inside the settle window
    if not already_logged:
        return "first"
    if since_last_notice >= OUTAGE_REMINDER_S:
        return "reminder"
    return None


def choose_face(state, count, util, token_count, clock, blink=False):
    """Pick the face to show. Returns a tuple that doubles as a change key.

    `clock` is seconds since rotation last became eligible; it resets while
    a session demands attention so the State Screen always gets a full turn
    first once things calm down. `blink` is the pulse phase, carried in the
    key so the daemon redraws on every phase flip.
    """
    if state in DEMANDS_ATTENTION:
        return ("state", state, count, blink)
    pos = clock % (STATE_FACE_S + USAGE_FACE_S + TOKENS_FACE_S)
    if pos < STATE_FACE_S:
        return ("state", state, count, False)
    if pos < STATE_FACE_S + USAGE_FACE_S:
        return ("usage", util.five_hour, util.seven_day)
    return ("tokens", token_count)


def render_face(face):
    if face[0] == "usage":
        return render_usage(face[1], face[2])
    if face[0] == "tokens":
        return render_tokens(face[1])
    return render(face[1], face[2], pulse=face[3])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="claude_display")
    ap.add_argument("--dry-run", action="store_true",
                    help=f"render to {DRY_RUN_FRAME} instead of the device")
    ap.add_argument("--address", default=config.PIXOO_ADDRESS,
                    help="Pixoo Bluetooth address (default: PIXOO_ADDRESS in .env)")
    ap.add_argument("--brightness", type=int, default=brightness.DAY_BRIGHTNESS,
                    help="daytime panel brightness (night dims automatically)")
    ap.add_argument("--spool", default=SPOOL_DIR)
    args = ap.parse_args(argv)
    brightness.DAY_BRIGHTNESS = args.brightness
    if not args.dry_run and not args.address:
        ap.error("no Pixoo address configured — set PIXOO_ADDRESS in "
                 f"{config.ENV_PATH} (see .env.example), or pass --address")

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
    last_logged = None
    last_aggregate = None
    unreachable_logged = False
    last_outage_notice = time.monotonic()
    last_push = 0.0
    shown_brightness = None
    tick = 0
    util = usage.read()
    away = brightness.is_away()
    token_poller = tokens_mod.TokenPoller()
    token_poller.start()  # ccusage is far too slow for the 1 s tick
    last_usage_poll = last_lock_poll = time.monotonic()
    rotation_start = time.monotonic()
    _log("[daemon] up; spool=" + args.spool,
         "DRY RUN" if args.dry_run else "device=" + args.address)

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
        # Any change of state snaps back to the State Screen, so work that
        # starts while a number face is up is seen immediately. Without this
        # the panel only showed a change if the state face happened to be its
        # turn — brief work could begin and end inside a number slot and never
        # appear at all, which reads as the display ignoring you.
        if (state, count) != last_aggregate:
            rotation_start = mono
            last_aggregate = (state, count)
        if state in DEMANDS_ATTENTION:
            rotation_start = mono
        blink = int(mono / BLINK_HALF_PERIOD_S) % 2 == 1
        face = choose_face(state, count, util, token_poller.value(),
                           mono - rotation_start, blink)

        want_brightness = brightness.target(
            away, brightness.in_night_window(), state in DEMANDS_ATTENTION
        )
        if want_brightness != shown_brightness:
            if args.dry_run or transport.set_brightness(want_brightness):
                reason = "away" if away else (
                    "night" if want_brightness == brightness.NIGHT_BRIGHTNESS else "day")
                _log(f"[daemon] brightness {want_brightness} ({reason})")
                shown_brightness = want_brightness

        now = time.time()
        if face != last_shown or now - last_push > FORCED_REFRESH_S:
            img = render_face(face)
            if args.dry_run:
                img.save(DRY_RUN_FRAME)
                pushed = True
            else:
                pushed = transport.push(img)
            if face[0] == "state":
                label = f"{face[1]} x{face[2]}"
            elif face[0] == "usage":
                label = f"usage 5h={face[1]}% 7d={face[2]}%"
            else:
                label = f"tokens {face[1] if face[1] is not None else 'pending'}"
            if pushed:
                # the pulse flips every tick; log only real face changes
                if face[:3] != last_logged:
                    _log(f"[daemon] {label}")
                    last_logged = face[:3]
                unreachable_logged = False
                last_shown = face
                last_push = now
            elif transport is not None:
                down = transport.down_for()
                say = outage_announcement(down, unreachable_logged,
                                          mono - last_outage_notice)
                if say == "first":
                    _log(f"[daemon] {label} (device unreachable, will retry)")
                elif say == "reminder":
                    # a dark panel must not stay silent for hours
                    _log(f"[daemon] still unreachable after {int(down // 60)} min"
                         f" — if this persists, power-cycle the Pixoo")
                if say:
                    unreachable_logged = True
                    last_outage_notice = mono
        time.sleep(1)

    # blank the panel on the way out: a dark display unambiguously means
    # nothing is driving it, rather than a stale frame that looks healthy
    _log("[daemon] shutting down")
    token_poller.stop()
    if args.dry_run:
        render_blank().save(DRY_RUN_FRAME)
    elif transport is not None:
        # never reconnect on the way out: launchd will SIGKILL a slow exit and
        # an unclosed channel is what wedges the device (ADR 0001)
        transport.blank_if_connected(render_blank())
        transport.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
