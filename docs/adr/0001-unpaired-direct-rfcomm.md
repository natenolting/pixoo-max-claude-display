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

## Addendum 3, 2026-08-30: shutdown must not reconnect

The device wedged once mid-session, needing a physical power cycle, and the
shutdown path is the likeliest cause. It pushed a final blank frame through
the normal `push()` call, which runs `_ensure_connected()` — so a shutdown
with the link already down would attempt a *fresh* connection, burning up to
ten seconds in the RFCOMM open pump before it ever reached `close()`. launchd
SIGKILLs a slow exit, and a SIGKILL leaves the channel unclosed, which is what
wedges the firmware.

`blank_if_connected()` now writes the final frame only over a channel that is
already open and never reconnects, and the plist sets an explicit
`ExitTimeOut` of 10 s. Measured shutdown is 0.6 s when idle. It can still
approach ten seconds if SIGTERM lands while a connect attempt is inside the
runloop pump — Python cannot run the signal handler until the runloop yields —
but no channel is open in that window, so nothing is left dangling.

Unpairing was also made less aggressive. It had been running on every connect
attempt, including every backoff retry; since `remove()` makes macOS forget the
device entirely, that churned the link far harder than the problem required. It
now runs on the first attempt of a daemon run and after any failed attempt,
which still clears a pairing macOS introduced while we were down.

This is a hypothesis supported by code reading and timing, not a reproduction.
The wedge was seen once and has not recurred.

## Addendum 4, 2026-08-30: recovery needs a quiet device

A wedged Pixoo will not come back from a power cycle performed while the daemon
is running. Three attempts failed in a row with the daemon retrying every few
seconds throughout; stopping the agent first, then power-cycling, then starting
it again connected on the first attempt with no failures and no pairing to undo.

The device apparently needs an uninterrupted moment after boot to reach a state
where it will accept an RFCOMM open, and a retry landing inside that window
puts it back where it started. The documented recovery is therefore ordered:
stop the agent, power-cycle, wait, start.

Repeated rapid restarts are themselves a cause. This wedged the device three
times in one evening of deploy-test cycles, and never once during ordinary
running.
