# 0001 — Keep the Pixoo Max unpaired; connect via direct IOBluetooth RFCOMM

Date: 2026-08-30. Status: accepted.

## Context

The obvious macOS route to a Bluetooth-SPP device is to pair it and use the
`/dev/cu.<name>` serial bridge. It worked exactly once (the first
freshly-paired session) and never again: once paired, macOS re-connects the
Pixoo as an A2DP headset the moment the device boots, and Divoom firmware
then refuses SPP/RFCOMM sessions — sync channel opens fail with
`kIOReturnError`, async opens hang. Hours of pairing/unpairing/power-cycling
confirmed the pattern; an unpaired device accepted direct RFCOMM channel 1
opens immediately and repeatedly.

## Decision

Never pair the Pixoo Max with macOS. Connect from the daemon via
IOBluetooth (pyobjc): open baseband, open RFCOMM channel 1 **async**
(sync open can fail where async succeeds), MTU 666, ~1 s settle before
first write, close channels cleanly on shutdown. If macOS silently
re-pairs during a session, un-pair (`blueutil --unpair`) before the next
connect.

## Consequences

- The daemon's host process needs the Bluetooth TCC grant (per-app; a
  launchd agent gets its own identity — install step).
- No `/dev/cu` serial path, so pyserial is out; pyobjc is a hard dependency.
- Device firmware wedges if a session dies unclosed; recovery is a device
  power cycle. The daemon must treat clean channel close as a correctness
  requirement, not a courtesy.

## Addendum, 2026-08-30: macOS re-pairs across a reboot

A cold boot was verified end to end. The launchd agent started correctly at
login, but the panel stayed dark: macOS had re-paired the Pixoo during
startup, so RFCOMM opens timed out (`open status: None`) exactly as this
ADR predicts. `RunAtLoad` is not sufficient on its own.

The daemon now undoes this itself. `_connect()` checks
`IOBluetoothDevice.isPaired()` and calls `remove()` before opening the
baseband link, using the Bluetooth grant the agent already holds. Pairing
is therefore reverted on every connect and every backoff retry, so the
display recovers without anyone noticing it was gone.

## Addendum 2, 2026-08-30: verified self-healing across a second reboot

The self-unpair was confirmed on a second cold boot. Sequence from the log:
macOS had paired the device during startup, the daemon unpaired it, two
RFCOMM opens then failed while the stack settled, and the third succeeded —
brightness and frames from then on. Total time to a working panel was about
fifteen seconds, with no human involvement.

macOS re-pairs aggressively: twice within five minutes during one testing
session, and again on every boot observed. Treat the pairing as something
that continuously reasserts itself, not as a one-off to undo at install
time. Undoing it on every connect attempt is the reason a rocky start
recovers on its own.
