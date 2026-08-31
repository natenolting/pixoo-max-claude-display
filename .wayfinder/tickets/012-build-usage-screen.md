---
title: Build the usage screen
labels: [wayfinder:task]
status: closed
assignee: natenolting
blocked-by: [010-usage-screen-semantics, 011-usage-screen-prototype]
---

## Question

Extend the daemon: usage data provider (per semantics ticket's sources and
cadence), usage renderer (per prototype), rotation logic between State
Screen and Usage Screen. Done when both screens run on hardware through a
working day under the launchd agent.

## Resolution

Shipped 2026-08-30. New module
[claude_display/usage.py](../../claude_display/usage.py) reads
`~/.claude/cache/usage-cache.json` every 60 s; `render_usage` added to
the renderer; `choose_face` in the daemon owns Rotation.

Verified on hardware under the launchd agent: State Screen 12 s → Usage
Screen 8 s → State Screen, frames landing with no unreachable warnings.

The staleness rule proved itself on the first real read: the cached
five-hour figure said 44% while that window had reset minutes earlier, so
the daemon correctly showed 0%. Without the `resetsAt` check the display
would have been lying.
