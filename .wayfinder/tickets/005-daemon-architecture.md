---
title: Daemon architecture
labels: [wayfinder:grilling]
status: open
assignee:
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
