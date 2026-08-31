---
title: Hardware smoke test
labels: [wayfinder:task]
status: closed
assignee: owner
blocked-by: [001-pixoo-max-control-path]
---

## Question

Feasibility gate: pair the Pixoo Max to the Mac and push one full 32x32
frame using the control path chosen by [Pixoo Max control path](001-pixoo-max-control-path.md).
Measure achievable frame rate and note pairing steps. If no frame can be
drawn, the map's destination is unreachable as scoped — surface that
immediately rather than continuing.

Partly HITL: pairing and physical device fiddling may need the human.

## Resolution

**PASSED — destination reachable.** Frame drawn on hardware, user confirmed
visually (2026-08-30).

Facts established:
- Route A works: macOS creates **`/dev/cu.Pixoo-Max`** after standard
  System Settings pairing (SPP SDP record present). No pyobjc/Node needed.
- Pairing: no pairing mode exists — device discoverable whenever on;
  phone/Divoom-app connection must be released first. Paired as
  `11:75:58:6E:BF:C1`, minor type "Headset".
- Push: 287-byte static frame (cmd `0x44`, 32x32, small palette) wrote in
  0.36 s; brightness cmd `0x74` worked; device ACKs with framed replies
  (31 bytes observed). Comfortable for ~1 s refresh cadence.
- USB confirmed power-only (no enumeration in `system_profiler SPUSBDataType`).
- Working script: [smoke_test/pixoo_smoke.py](../../smoke_test/pixoo_smoke.py)
  (pyserial + PixooMax encoding ported from virtualabs/pixoo-client) —
  seed code for the daemon's display driver.
- A2DP audio-grab quirk did not interfere with RFCOMM.
