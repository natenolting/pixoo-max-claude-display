---
title: Daemon architecture
labels: [wayfinder:grilling]
status: closed
assignee: owner
blocked-by: [001-pixoo-max-control-path, 002-claude-code-signal-inventory, 003-multi-session-semantics]
---

## Question

Shape of the daemon: how hook events reach it (file drop? unix socket? HTTP
on localhost?), process lifecycle (launchd? manual?), state machine from raw
signals to display state, poll cadence for aggregates, and reconnect
strategy when the Pixoo drops off BT. Decide module seams
(/codebase-design) before code.

Established transport facts to design against (from
[Hardware smoke test](004-hardware-smoke-test.md) and
[State screen prototype](006-state-screen-prototype.md)):

- Device must stay **unpaired**; daemon connects via IOBluetooth RFCOMM
  channel 1 (pyobjc, async open, MTU 666, ~1 s settle post-connect).
- Daemon's host process needs the Bluetooth TCC grant (launchd agent gets
  its own; Claude's embedded shell has none — a `blueutil`-style prompt
  flow or manual grant is part of install).
- macOS may silently re-pair during a session — daemon should tolerate or
  un-pair; A2DP auto-connect after re-pairing wedges SPP until unpaired.
- Device BT stack wedges if a session dies without close — daemon must
  close channels cleanly and expect power-cycle as user-level recovery.

## Resolution

Decisions (all grilled 2026-08-30):

- **Hook → daemon transport: file spool.** Each hook writes a small JSON
  event (`{session_id, event, ts, cwd}`) into a spool dir; daemon watches.
  Hooks stay dumb and fast, can't hang on a dead daemon, events survive
  daemon restarts. Sockets/HTTP rejected — extra failure modes, no benefit
  at a 1 s redraw floor.
- **Stack: Python 3** in this repo's `.venv` (pyobjc transport, PIL
  rendering — all proven).
- **Lifecycle: foreground CLI first**; launchd LaunchAgent is install-phase
  work ([Install as launchd agent](009-launchd-install.md)).
- **Connection policy: keep RFCOMM open, reconnect on write failure** with
  5 s → 60 s backoff. Connect-per-push rejected (wedge multiplication).
  Unpaired idle-drop behavior verified in
  [Signal live experiment](007-signal-live-experiment.md).
- **Cadences**: event-driven redraw, 1 s minimum interval; registry sweep
  every 3 s; WAITING→IDLE demotion evaluated each sweep.
- **Daemon derives Aggregate State**; hooks emit raw events only.

Module seams (deep modules, narrow interfaces):

- `transport` — `PixooTransport.push(img)`, `.set_brightness(n)`; hides
  IOBluetooth, reconnect, backoff, MTU chunking entirely.
- `renderer` — `render(aggregate_state, count) -> PIL.Image`; Variant A.
- `state` — `SessionStore.ingest(event)`, `.sweep(registry_rows)`,
  `.aggregate() -> (state, count)`; owns precedence + demotion clock.
- `signals` — spool watcher + registry sweeper; emits normalized events.
- `daemon` — wiring + main loop.

ADR: [0001 — Unpaired direct RFCOMM](../../docs/adr/0001-unpaired-direct-rfcomm.md).
