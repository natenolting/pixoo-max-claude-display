# Claude Code Signal Sources — Mac Inventory (verified 2026-08-30)

Resolves [.wayfinder/tickets/002-claude-code-signal-inventory.md](../../.wayfinder/tickets/002-claude-code-signal-inventory.md).

## 1. Hooks (push, near-instant) — best live-state source

Configured in `~/.claude/settings.json` → `hooks`. Current config has only one
(`PostToolUse` matcher `Write|Edit` → obsidian mirror script); adding more is a
settings edit.

Hook events verified as string literals in CLI binary (v2.1.251):
`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`,
`PostToolUseFailure`, `Notification`, `Stop`, `SubagentStart`, `SubagentStop`,
`PreCompact`, `PermissionRequest`, `TeammateIdle`, `TaskCompleted`.

All hooks receive JSON on stdin with at least `session_id`, `transcript_path`,
`cwd`, `hook_event_name`. Notification types verified in binary:
`permission_prompt`, `idle_prompt`, `agent_needs_input`, `agent_completed`,
`elicitation_dialog`.

State-machine mapping:
- `UserPromptSubmit` → WORKING; `PreToolUse`/`PostToolUse` → WORKING heartbeat
- `Notification` (permission_prompt / idle_prompt) → WAITING
- `Stop` → turn finished; `SessionStart`/`SessionEnd` → lifecycle
- Push latency ms; every payload carries `session_id` → multi-session for free.

## 2. Statusline (push, per-render of active session)

`settings.json` → `statusLine`: `node ~/.claude/hooks/statusline.js`
(ctxline-claude variant). Verified stdin fields: `session_id`,
`model.display_name`, `workspace.current_dir`, `effort.level`,
`context_window.remaining_percentage`, `cost.total_cost_usd`,
`rate_limits.five_hour.used_percentage`/`.resets_at` (epoch seconds),
`rate_limits.seven_day.*`. Also reads `~/.claude/todos/<sessionId>-agent-*.json`
(`status: "in_progress"`, `activeForm`) and OAuth usage API
(`GET https://api.anthropic.com/api/oauth/usage`, keychain token, cached
30 s at `~/.claude/cache/usage-cache.json`). Good piggyback point: statusline
script could also drop a state file for the display daemon.

## 3. Live session registry — `~/.claude/sessions/<pid>.json` (poll) — big find

One JSON per CLI process, verified live (13 sessions now: 12 cmux-managed +
Desktop):

```json
{"pid":26589,"sessionId":"8d1af3df-…","cwd":"…","startedAt":0,
 "kind":"interactive","entrypoint":"cli","name":"paper-people-95",
 "messagingSocketPath":"/tmp/cc-socks/26589.sock",
 "status":"idle","updatedAt":0,"statusUpdatedAt":0}
```

- `status` observed: `"idle"`; binary enum candidates `working`,
  `needs_input`, `waiting`, `busy`, `running`, `compacting` (unconfirmed).
- Liveness: `kill -0 <pid>` + socket at `/tmp/cc-socks/<pid>.sock`; stale
  files outlive dead processes — always pid-check.
- Cleanest "enumerate concurrent sessions" answer: pid, sessionId, cwd,
  human name, status, timestamps in one poll.
- Secondary: `~/.claude/ide/<pid>.lock` IDE lockfiles.

## 4. Transcripts — `~/.claude/projects/<cwd-slug>/<sessionId>.jsonl` (poll/tail)

Verified field names. Assistant lines: `timestamp`, `sessionId`, `cwd`,
`gitBranch`, `requestId`, `isSidechain`, `message.model`,
`message.stop_reason`, `message.usage` (`input_tokens`, `output_tokens`,
`cache_creation_input_tokens`, `cache_read_input_tokens`,
`output_tokens_details.thinking_tokens`, `service_tier`).
`cost-state` lines: `totalCostUSD`, `totalAPIDuration`, `totalLinesAdded`,
`totalLinesRemoved`, `modelUsage{}` — running per-session aggregate, no math.
Files reach 20 MB+; aggregate by summing `message.usage` filtered by date,
dedupe by `requestId` (resumed/branched sessions duplicate — same as ccusage).

## 5. Usage aggregation tools

- `ccusage` v20.0.20 cached in npx → `npx ccusage daily --json` works.
  Reads all project transcripts, dedupes, prices via LiteLLM table. Easiest
  daily-usage path.
- `~/.claude/stats-cache.json`: `dailyActivity[]` (`date`, `messageCount`,
  `sessionCount`, `toolCallCount`) — no tokens/cost, lazy updates.
  Supplementary only.

## 6. OTEL (not enabled)

`CLAUDE_CODE_ENABLE_TELEMETRY=1` + `OTEL_METRICS_EXPORTER` etc. Metrics
exist (`claude_code.token.usage`, `.cost.usage`, `.session.count`, …) but
needs env vars in every launch context + collector with persistence.
Verdict: heavier than ccusage/transcripts for this use.

## Recommended minimal signal set

**(a) Live state screen**: hooks (`UserPromptSubmit`, `PreToolUse` throttled,
`Stop`, `Notification`, `SessionStart`, `SessionEnd`) each POSTing/writing
`{session_id, event, cwd}` for the daemon — plus a sweeper polling
`~/.claude/sessions/*.json` every few seconds (pid-liveness; catches sessions
whose `--settings` overrides may bypass user hooks, e.g. the cmux fleet).

**(b) Daily usage screen**: `npx ccusage daily --json` on 1–5 min poll, or
own parser over today's jsonl with `requestId` dedupe. Session cost:
`cost-state` lines or statusline `cost.total_cost_usd`.

## Unknowns needing live experiment

1. Exact registry `status` enum during generation vs permission wait, and
   `statusUpdatedAt` latency.
2. `Notification` hook firing conditions + exact payload fields.
3. Hook merge semantics: user settings.json hooks vs cmux `--settings` CLI
   overrides — do user hooks fire in those sessions?
4. Does `Stop` fire on interrupt (Esc) as well as natural end-of-turn?
5. `npx ccusage` offline behavior.
