---
title: Build the state-screen daemon
labels: [wayfinder:task]
status: closed
assignee: owner
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

## Resolution

Built and verified on hardware 2026-08-30. Package
[claude_display/](../../claude_display/): `transport` (IOBluetooth per ADR
0001, backoff reconnect), `renderer` (Variant A), `state` (precedence +
demotion), `signals` (spool reader + registry sweeper with cmux
process-ancestry filter), `daemon` (1 s tick / 3 s sweep / 30 s forced
refresh, `--dry-run` mode). Hook script
[hooks/claude-display-hook.sh](../../hooks/claude-display-hook.sh) spools
events; project settings wired; user-scope snippet at
[hooks/user-settings-hooks-snippet.json](../../hooks/user-settings-hooks-snippet.json)
(user merges by hand — classifier blocks agent edits there).

Verified live: IDLE → WORKING (blue) → WAITING (amber) → IDLE on the
device, including concurrent sessions (`WORKING x2` badge) and cmux
exclusion (13 fleet sessions filtered).

Bug found & fixed during verification: a cleanly-exiting session DELETES
its registry file (no dead-pid row) and its async SessionEnd hook can lose
the race against process exit → phantom WAITING. Fix: absence from the
registry drops a session after a 15 s grace (`NOT_IN_REGISTRY_GRACE_S`),
and the SessionEnd hook runs synchronous (timeout 3), mirroring cmux's own
config.

Run: `.venv/bin/python -m claude_display` from Terminal (Bluetooth TCC).
Outstanding user action: merge the hooks snippet into
`~/.claude/settings.json` for Desktop-session coverage + instant
permission flips.
