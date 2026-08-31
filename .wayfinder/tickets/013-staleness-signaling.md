---
title: Staleness signaling
labels: [wayfinder:grilling]
status: closed
assignee: owner
blocked-by: []
---

## Question

The Pixoo holds its last frame forever. A dead daemon, a dropped Bluetooth
link, or a sleeping Mac therefore looks identical to a calm, healthy
display — and the dangerous case is a frozen IDLE face while a session is
actually waiting on the user.

A marker drawn at failure time is impossible: staleness means the daemon
cannot write to the device. Only motion can prove liveness. So: what
rhythm, on which faces, and what should the daemon do on graceful exit?

## Resolution

Decided and shipped 2026-08-30.

- **Failures worth catching**: a dropped Bluetooth link while the daemon
  lives, and a sleeping Mac or a hand-stopped agent. A crash is not one —
  launchd restarts within ~10 s, faster than a person would notice. A
  powered-off Pixoo announces itself.
- **Liveness proof is motion.** Rotation already supplies it during
  WORKING / IDLE / OFF: a display parked on one face for a minute is
  visibly wrong. The gap was the attention states, where rotation stops —
  exactly where a frozen frame lies most expensively.
- **Attention states pulse**: the icon dims to 45% and back on a 2 s
  period (1 s half-period) while the Aggregate State is NEEDS-PERMISSION
  or WAITING. The field colour holds steady. This buys the liveness proof
  and a better attention signal in one move — a pulsing red "!" catches
  peripheral vision better than a static one. A full on/off blink was
  rejected as reading like a malfunction.
- **Graceful exit blanks the panel.** A dark display unambiguously means
  nothing is driving it. A hard kill cannot blank, by definition — that is
  the case the pulse covers.

Verified in dry-run: icon alternates 255 → 115 with the field unchanged,
one log line per real face change rather than one per pulse tick, and a
fully black frame written on shutdown. A corner heartbeat pixel was
rejected as a signal nobody would study.
