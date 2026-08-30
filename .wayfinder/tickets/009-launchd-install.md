---
title: Install as launchd agent
labels: [wayfinder:task]
status: closed
assignee: nate.nolting@paulbunyan.coop
blocked-by: [008-build-state-daemon]
---

## Question

Make the daemon survive reboots and logouts: LaunchAgent plist, KeepAlive,
log routing, and the Bluetooth TCC grant for the daemon's own process
identity (first-run prompt or manual grant — document whichever works).
Includes pairing hygiene: verify device stays unpaired across restarts per
[ADR 0001](../../docs/adr/0001-unpaired-direct-rfcomm.md).

## Resolution

Installed 2026-08-30. LaunchAgent at
[launchd/com.natenolting.claude-display.plist](../../launchd/com.natenolting.claude-display.plist),
copied to `~/Library/LaunchAgents/` and loaded with
`launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.natenolting.claude-display.plist`.
RunAtLoad + KeepAlive (throttle 10 s); logs at
`~/Library/Logs/claude-display.log`.

Bluetooth TCC: macOS prompted once (dialog names "Python"); user allowed.
That grant belongs to the venv Python binary and is the agent's own
identity — no Terminal dependency anymore. Verified live: agent pid
running, frames reaching the device (IDLE x2 on the panel).

Manage: `launchctl bootout gui/$UID/com.natenolting.claude-display` stops
it; `launchctl kickstart -k gui/$UID/com.natenolting.claude-display`
restarts it.

Untested until the next reboot: RunAtLoad auto-start (expected to work)
and pairing hygiene after restart — if the display goes dead after a
reboot, check `blueutil --paired` first per ADR 0001.
