---
title: Pixoo Max control path
labels: [wayfinder:research]
status: closed
assignee: nate.nolting@paulbunyan.coop
blocked-by: []
---

## Question

How do we programmatically control the Pixoo Max (32x32) from macOS? Is it
Bluetooth-only or does USB carry data? BT Classic SPP or BLE? Which existing
libraries have proven Pixoo Max 32x32 support (not just Timebox Evo /
Pixoo 16x16), what frame-push mechanics and refresh rates are achievable,
and what macOS-specific pairing quirks exist?

Resolution decides the stack (follow the libs) and feeds the hardware smoke
test.

## Resolution

Full report: [docs/research/pixoo-max-control-path.md](../../docs/research/pixoo-max-control-path.md).

Gist: Pixoo Max is **Bluetooth Classic RFCOMM only** (FCC-confirmed — no WiFi,
no BLE, USB power-only). Protocol reverse-engineered; palette-indexed frames,
static-image cmd `0x44`. Chosen path: **Python + pyserial → `/dev/cu.Pixoo*`**
(macOS IOBluetooth SPP bridge), frame encoding ported from
virtualabs/pixoo-client's `PixooMax` class; fallback Node +
`node-bluetooth-serial-port` (proven macOS route). Stack decision resolved:
**Python primary**. Throughput ample for 1–10 s refresh. Hands-on unknowns
(does `/dev/cu` port appear; A2DP interference) transferred to
[Hardware smoke test](004-hardware-smoke-test.md).
