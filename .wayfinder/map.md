---
title: Claude stats on Pixoo Max
labels: [wayfinder:map]
tracker: local-markdown
---

# Claude stats on Pixoo Max — Wayfinder Map

Tickets live in [.wayfinder/tickets/](tickets/). A ticket is claimed when its
`assignee` field is set; blocking uses each ticket's `blocked-by` frontmatter
list (this tracker has no native dependency graph). Frontier = open tickets
with empty/satisfied `blocked-by` and no assignee.

## Destination

A daemon on this Mac drives the Divoom Pixoo Max (32x32) over Bluetooth (or
USB if it turns out to do data), showing live Claude Code session state
(working / idle / waiting-for-you), verified working on the real hardware.
Usage/cost screens are a later phase inside the same scope.

## Notes

- Domain: macOS daemon + reverse-engineered Divoom BT protocol + Claude Code
  hook/transcript signals.
- Skills: `/grilling` + `/domain-modeling` for decision tickets;
  `/research` for AFK fact-finding; `/prototype` for the screen design.
- Stack: follow the libs — pick language with proven Pixoo Max 32x32 support.
- Update model: hybrid — hooks push session-state flips, polling covers
  usage aggregates.
- Research reports land in `docs/research/`, linked from their tickets.

## Decisions so far

<!-- one line per closed ticket: [title](tickets/NNN-slug.md) — gist -->

- [Pixoo Max control path](tickets/001-pixoo-max-control-path.md) — BT Classic RFCOMM only (no WiFi/BLE/USB-data); Python + pyserial via `/dev/cu.Pixoo*`, encoder from virtualabs/pixoo-client; Node fallback.
- [Claude Code signal inventory](tickets/002-claude-code-signal-inventory.md) — hooks (push) + `~/.claude/sessions/<pid>.json` registry sweep for live state; `npx ccusage` for usage aggregates; OTEL rejected.
- [Multi-session semantics](tickets/003-multi-session-semantics.md) — one Aggregate State + Count Badge; NEEDS-PERMISSION > WAITING > WORKING > IDLE > OFF; 30-min WAITING demotion; subagents + cmux fleet excluded. Glossary in CONTEXT.md.
- [Hardware smoke test](tickets/004-hardware-smoke-test.md) — **PASSED**: frame drawn via `/dev/cu.Pixoo-Max` + pyserial, 0.36 s/frame, brightness works; feasibility proven; driver seed code in `smoke_test/`.
- [State screen prototype](tickets/006-state-screen-prototype.md) — **Variant A**: full-field state color + white icon + corner count digit, LED-validated. Also superseding transport find: keep device UNPAIRED, direct IOBluetooth RFCOMM ch.1 (async), not `/dev/cu`; needs BT TCC grant.
- [Daemon architecture](tickets/005-daemon-architecture.md) — file-spool hook transport; Python; CLI-first; keep-open BT + backoff; 1 s redraw / 3 s sweep; five module seams. [ADR 0001](../../docs/adr/0001-unpaired-direct-rfcomm.md): never pair the device.
- [Signal live experiment](tickets/007-signal-live-experiment.md) — registry `status` = idle/busy/waiting, <1 s latency, but null for Desktop/headless sessions (hybrid confirmed); PermissionRequest hook = instant NEEDS-PERMISSION signal; Stop fires on Esc; ccusage works.
- [Build the state-screen daemon](tickets/008-build-state-daemon.md) — **WORKING ON HARDWARE**: `claude_display/` package, hooks + registry sweep → Variant A frames over BT; phantom-session bug found & fixed (registry absence = death, 15 s grace; sync SessionEnd hook).

## Not yet specified

- Usage/cost screens (phase 2): which numbers, big-digit layout, data
  pipeline — waits on state-screen build learnings.
- Screen rotation/scheduling once more than one screen exists.
- Staleness signaling: what the display shows when the daemon is dead and
  the last frame lingers.
- Brightness / night behavior.

## Out of scope

- Multi-device support (user owns several Divoom displays; this map targets
  the Pixoo Max only).
- Phone-hosted control path (Mac is the host).
