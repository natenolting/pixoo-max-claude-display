---
title: Build the state-screen daemon
labels: [wayfinder:task]
status: open
assignee: nate.nolting@paulbunyan.coop
blocked-by: [007-signal-live-experiment]
---

## Question

Build phase 1 per [Daemon architecture](005-daemon-architecture.md)'s
resolution: the five modules (`transport`, `renderer`, `state`, `signals`,
`daemon`), hook scripts + `~/.claude/settings.json` hook installation, and
a live end-to-end run — real sessions driving the real display through a
working day. Detection logic parameterized by
[Signal live experiment](007-signal-live-experiment.md)'s answers
(registry `status` enum, Notification payload, hook merge behavior).

Done when: Aggregate State + Count Badge track reality on the hardware,
per the semantics in CONTEXT.md and the Variant A design from
[State screen prototype](006-state-screen-prototype.md).
