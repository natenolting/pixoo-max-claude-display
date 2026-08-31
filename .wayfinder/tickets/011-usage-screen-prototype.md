---
title: Usage screen prototype
labels: [wayfinder:prototype]
status: closed
assignee: owner
blocked-by: [010-usage-screen-semantics]
---

## Question

What does the Usage Screen look like on 32x32? Big-digit numerals and/or
utilization bars per the semantics ticket; render candidates on the real
device (transport recipe proven), user picks. Legibility across the room is
the bar.

## Resolution

**Variant A wins**, confirmed on the LEDs 2026-08-30: big 7-segment number
for the Five-Hour Utilization, a 5-hour fill bar beneath it, and a thin
dimmer 7-day bar at the bottom edge. Digits read across the room and the
severity ramp (blue < 70%, amber 70–89%, red ≥ 90%) landed on hardware.

Rejected: twin columns (spends half the canvas on bar chrome and shrinks
the numbers), perimeter ring (decorative — you cannot read 44% from 55%
off a ring).

Details: 7-segment digits in an 11x19 box, thickness 2, narrowing to 9 px
when three digits are needed at 100%. Assets:
[prototypes/usage_screen/proto.py](../../prototypes/usage_screen/proto.py),
[contact sheet](../../prototypes/usage_screen/contact_sheet.png).
