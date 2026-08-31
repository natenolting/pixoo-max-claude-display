---
title: State screen prototype
labels: [wayfinder:prototype]
status: closed
assignee: nate.nolting@paulbunyan.coop
blocked-by: [002-claude-code-signal-inventory, 003-multi-session-semantics]
---

## Question

What does the live-state screen look like on 32x32? Prototype (via
/prototype — an HTML pixel-grid mock is fine, no hardware needed) the
layouts for working / idle / waiting-for-you: color coding, icon vs text,
legibility across the room. Human reacts to concrete pixels, picks one.
Link the prototype as an asset.

## Resolution

**Variant A wins**, confirmed on real LEDs (2026-08-30): full-field state
color, big white icon, black corner box with white count digit. Colors
validated on hardware — red/amber/blue/dim-navy all legible.

- PERM: red field + "!" · WAIT: amber + hourglass · WORK: blue + play
  triangle · IDLE: near-black + dim "z z z" · OFF: black (single dim px)
- Count Badge: 3x5 digit, bottom-right, black box, shown only when count > 1.

Assets (throwaway prototype code, kept as reference):
- [prototypes/state_screen/proto.py](../../prototypes/state_screen/proto.py) —
  variant renderers + contact sheet + serial pusher
- [prototypes/state_screen/direct_push.py](../../prototypes/state_screen/direct_push.py) —
  the transport that actually works (see below)
- [prototypes/state_screen/contact_sheet.png](../../prototypes/state_screen/contact_sheet.png)

**Transport discovery made during this ticket (supersedes part of
[Pixoo Max control path](001-pixoo-max-control-path.md)):** the
`/dev/cu.Pixoo-Max` serial-bridge route is unreliable — it worked only in
the first freshly-paired session. Root cause: once paired, macOS
auto-connects the Pixoo as an A2DP headset at device boot, and Divoom
firmware then refuses SPP/RFCOMM. Reliable recipe, proven repeatedly:
**do NOT pair** — open baseband + RFCOMM channel 1 directly via IOBluetooth
(pyobjc), async open (sync open can fail while async succeeds), MTU 666,
~1 s settle, then write frames. Requires Bluetooth TCC grant on the host
process (Terminal has it; Claude's embedded shell does not — daemon needs
its own grant).


## Amendment, 2026-08-30: hourglass replaced with a prompt caret

The WAITING icon was an hourglass, which inverts the convention every
operating system has used for decades: an hourglass means *the machine is
busy, wait*, while this state means the machine is finished and the user is
the holdup. The user asked what the screen was for — the tell that the icon
was not carrying its meaning.

It is now a terminal prompt: a solid chevron with a cursor block that blinks
off on alternate frames, at the user's suggestion. That reads as "the prompt
is waiting for you", and the blink supplies the liveness motion the dimming
pulse used to provide. Rejected alternatives: a chevron with an underscore
cursor (too visually light at this size) and an arrow pointing at the viewer
(says "you" but not what is wanted).

Icon functions now take the pulse phase and decide what it means for them,
so NEEDS-PERMISSION keeps dimming its mark while WAITING blinks its cursor.
