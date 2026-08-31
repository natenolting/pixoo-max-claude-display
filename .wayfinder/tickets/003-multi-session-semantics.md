---
title: Multi-session semantics
labels: [wayfinder:grilling]
status: closed
assignee: owner
blocked-by: []
---

## Question

One display, potentially several concurrent Claude Code sessions. What does
the state screen mean then? Aggregate ("any session waiting for you" wins)?
Most-recently-active session only? Per-session slots on the 32x32 grid? And
what is the precedence order among states (waiting > working > idle > error?).
Defines the ubiquitous language for "session state" — glossary terms land in
CONTEXT.md when resolved.

## Resolution

Glossary captured in [CONTEXT.md](../../CONTEXT.md). Decisions:

- **Aggregation**: one Aggregate State fills the screen + Count Badge showing
  how many Tracked Sessions share it. No per-session slots.
- **States, precedence high→low**: NEEDS-PERMISSION > WAITING > WORKING >
  IDLE > OFF. NEEDS-PERMISSION distinct from WAITING (blocked work is more
  urgent than turn-done).
- **Demotion**: WAITING → IDLE after 30 min unanswered. NEEDS-PERMISSION
  never demotes.
- **Tracked Session scope**: interactive sessions the user drives directly.
  Excluded: subagents, cmux-managed fleet sessions. Exact registry
  discriminator for cmux → [Signal live experiment](007-signal-live-experiment.md).


## Amendment: cmux sessions are tracked by default

Excluding cmux-managed sessions was decided before anyone had watched the
display against real work. It rested on the idea that a fleet of idle cmux
sessions would drown the signal — but Precedence already handles that (one
working session among eleven idle ones still reads WORKING), and the user
runs every real session inside cmux, so the display tracked exactly one
session and never reacted to their actual work.

They are now tracked by default, with `TRACK_CMUX_SESSIONS=false` restoring
the exclusion for anyone whose cmux sessions genuinely are background.


## Amendment: WORKING now outranks WAITING

The original order put WAITING above WORKING — with one session, "you are
the holdup" beating "it is busy" was right. With a fleet it inverted: some
session has nearly always just finished a turn, so a stale WAITING masked
every session actually working, and because WAITING also froze the
rotation, the panel sat on the amber caret for up to the full demotion
window. The display looked broken while behaving exactly as specified.

Precedence is now NEEDS-PERMISSION > WORKING > WAITING > IDLE, and only
NEEDS-PERMISSION freezes the rotation. Nothing is lost: live work clears
itself, so the waiting signal resurfaces as soon as the work stops.

This separated two ideas that had been one constant: which states pulse
(attention) and which hold the panel alone (rotation). A test caught the
regression where WAITING silently stopped pulsing.
