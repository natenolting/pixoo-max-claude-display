---
title: Usage screen semantics
labels: [wayfinder:grilling]
status: closed
assignee: owner
blocked-by: []
---

## Question

Which numbers earn 1024 pixels, and when does the Usage Screen show instead
of the State Screen? Candidates: daily cost, daily tokens, 5-hour/7-day
rate-limit utilization, model mix. Rotation policy between screens is part
of this decision (fog item "screen rotation" folds in here). Data sources
already verified: `npx ccusage daily --json`,
`~/.claude/cache/usage-cache.json` (rate limits), transcript `cost-state`
lines.

## Resolution

Decided 2026-08-30.

- **Headline number: 5-hour rate-limit utilization**, as a percentage.
  Chosen over cost and token counts because it is the only one that changes
  what the user does next ("am I about to hit the wall"). Cost and token
  totals are dropped entirely — ccusage stays unused by the daemon.
- **Second number: 7-day utilization**, subordinate. Big digits + bar for
  the 5-hour window; a thin secondary bar for the 7-day.
- **Rotation: the State Screen always wins when a session needs the user.**
  While the Aggregate State is NEEDS-PERMISSION or WAITING, only the State
  Screen shows. While WORKING, IDLE, or OFF, the two screens alternate:
  12 s State Screen, 8 s Usage Screen. (This resolves the old
  "screen rotation" fog patch.)
- **Data source: `~/.claude/cache/usage-cache.json`, polled every 60 s.**
  No subprocess, no credentials — the same source the user's statusline
  trusts. Verified shape:
  `{"timestamp": <ms>, "data": {"fiveHour": {"percentage": N, "resetsAt": <ISO>},
  "weekly": {...}}}`.
- **Staleness rule**: the cache only refreshes when a session renders its
  statusline, so it goes cold while the user is idle (observed 27 min old).
  When a window's `resetsAt` has passed, the daemon shows **0%** for that
  window rather than the stale figure. Fetching the OAuth usage API from
  the daemon (keychain token, as the statusline does) was rejected for now:
  it puts credential handling in a display daemon for a number that is only
  wrong while nothing is being consumed. Revisit if staleness annoys in
  practice.
