---
title: Claude Code signal inventory
labels: [wayfinder:research]
status: closed
assignee: owner
blocked-by: []
---

## Question

What signals does Claude Code expose on this Mac for (a) live session state
(working / idle / waiting-for-user) and (b) usage aggregates (daily tokens,
cost)? Cover hook events and their stdin payloads, statusline JSON,
transcript JSONL fields, ccusage/OTEL options, and how to enumerate live
sessions vs dead transcripts. Recommend the minimal signal set per screen.

## Resolution

Full report: [docs/research/claude-code-signal-inventory.md](../../docs/research/claude-code-signal-inventory.md).

Gist: live state = **hooks** (push, ms latency, `session_id` in every payload;
events `UserPromptSubmit`/`Stop`/`Notification`/`SessionStart`/`SessionEnd`)
plus a **sweeper poll of `~/.claude/sessions/<pid>.json`** — a live session
registry with pid, sessionId, cwd, name, `status` field. Usage aggregates =
`npx ccusage daily --json` (cached, works) or own transcript parser with
`requestId` dedupe. OTEL rejected (heavier). Five unknowns need a live
experiment → spun out to [Signal live experiment](007-signal-live-experiment.md).
