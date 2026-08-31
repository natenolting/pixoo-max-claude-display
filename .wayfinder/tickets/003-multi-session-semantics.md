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
