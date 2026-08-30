---
title: Install as launchd agent
labels: [wayfinder:task]
status: open
assignee:
blocked-by: [008-build-state-daemon]
---

## Question

Make the daemon survive reboots and logouts: LaunchAgent plist, KeepAlive,
log routing, and the Bluetooth TCC grant for the daemon's own process
identity (first-run prompt or manual grant — document whichever works).
Includes pairing hygiene: verify device stays unpaired across restarts per
[ADR 0001](../../docs/adr/0001-unpaired-direct-rfcomm.md).
