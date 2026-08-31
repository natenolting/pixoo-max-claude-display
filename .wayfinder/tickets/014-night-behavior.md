---
title: Brightness and night behavior
labels: [wayfinder:grilling]
status: closed
assignee: natenolting
blocked-by: []
---

## Question

The panel runs at a fixed brightness of 80 around the clock, which is a
lighthouse in a dark room. Worse, when the Mac sleeps the daemon is
suspended with it, so whatever frame was last pushed glows all night.

What dims the display, what does dimmed mean (lower brightness, black
panel, or off), and does a session demanding attention override it?

Established: screen-lock state is readable via Quartz
(`CGSessionCopyCurrentDictionary` → `CGSSessionScreenIsLocked`), cheap and
subprocess-free. The daemon cannot act during system sleep, but the screen
locks before that and the daemon resumes on wake.

## Resolution

Decided and shipped 2026-08-30.
[claude_display/brightness.py](../../claude_display/brightness.py) owns the
policy; the daemon polls lock state every 5 s and pushes a brightness
command only when the target changes.

- **Two triggers, both dim**: Away (screen locked) and the Night Window
  (22:00–07:00 local). Lock does the heavy lifting — it is the honest
  "nobody is looking" signal and it fires on the way into system sleep,
  which is the case that used to leave the panel glowing all night. The
  schedule covers evenings at the desk.
- **Dimmed means brightness 15**, not a black panel. The faces keep
  rendering and rotating, so a 2 a.m. glance still answers the question;
  the panel simply stops lighting the room. Blanking would throw away the
  device's whole purpose, and freezing rotation would kill the liveness
  motion from [Staleness signaling](013-staleness-signaling.md).
- **Attention overrides night only while the user is present.** Late but
  unlocked and a session needs you → full brightness. Locked → stays dim
  regardless, because a bright red panel wakes nobody in an empty room and
  the Pulse is still there when the user returns.
- Day brightness stays 80, overridable with `--brightness`.

Verified: night window wraps midnight correctly (22:00–06:59 dim, 07:00
bright), all six present/away × night/day × attention combinations return
the intended level, and the lock probe fails safe to "present" so an
unreadable session dictionary can never leave the panel dark.
