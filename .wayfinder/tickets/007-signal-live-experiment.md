---
title: Signal live experiment
labels: [wayfinder:task]
status: closed
assignee: natenolting
blocked-by: []
---

## Question

Verify on this machine the five unknowns from
[Claude Code signal inventory](002-claude-code-signal-inventory.md):

1. What `status` values does `~/.claude/sessions/<pid>.json` actually take
   while generating / waiting on permission, and how fast does
   `statusUpdatedAt` move?
2. When does the `Notification` hook fire, and with what payload fields?
3. Do user-level settings.json hooks fire in sessions launched with
   `--settings` overrides (the cmux fleet)?
4. Does `Stop` fire on interrupt (Esc) as well as natural end-of-turn?
5. Does `npx ccusage` work offline?

Mostly AFK (instrument hooks with a logging script, run a throwaway session);
permission-prompt and Esc-interrupt cases need a human hand. Answers pin the
daemon's state-detection design.

## Resolution

Ran 2026-08-30: logging hooks in project settings
([.claude/settings.json](../../.claude/settings.json) →
[log_hook.sh](../../prototypes/signal_experiment/log_hook.sh)), 1 s registry
watcher, headless `-p` guinea pig, HITL interactive session with permission
prompt + Esc interrupt. Raw logs were in `/tmp/claude-display-exp/`.

1. **Registry `status` enum (verified live): `idle` / `busy` / `waiting`.**
   `busy` = mid-turn, `waiting` = permission prompt showing, `idle` = turn
   done. Transitions matched hook timeline exactly; `statusUpdatedAt` moves
   in **<1 s**. HUGE: one polled file yields nearly the whole state machine.
   CAVEAT: `status` was **null** for the Desktop-app session (CLI 2.1.247
   embedded) and for a headless `-p` run — registry status is only reliable
   for plain CLI sessions. Hooks remain necessary for Desktop → hybrid
   design confirmed.
2. **Permission signals**: `PermissionRequest` hook fires the instant the
   prompt renders (payload has `tool_name`). `Notification`
   (`notification_type: "permission_prompt"`, message "Claude needs your
   permission") fires ~6 s later as the nudge. Use PermissionRequest for
   NEEDS-PERMISSION; approval is visible as the next PreToolUse or registry
   `busy`.
3. **Hook merge vs cmux `--settings`**: not tested — moot, cmux sessions are
   excluded from Tracked Sessions and the registry sweep sees them anyway.
   Project-scope hooks proved sufficient for experiment; build installs at
   user scope (auto-mode classifier blocks agent edits to
   `~/.claude/settings.json` — the user applies that edit by hand).
4. **Stop on Esc interrupt: yes** — Stop fired and registry went `idle`
   after a mid-count Esc.
5. **ccusage**: `npx ccusage daily --json` works from npx cache (v20.0.20),
   includes per-agent breakdowns (even codex). Strict-offline untested; low
   risk.

Bonus findings: hooks fire in headless `-p` sessions (full lifecycle incl.
`SessionEnd` reason `other`; interactive exit gives `prompt_input_exit`);
headless sessions register as `kind: "interactive"` too, so kind alone can't
filter them; sessions launched in this repo also log SessionStart within 1 s.
State mapping for the daemon: PermissionRequest → NEEDS-PERMISSION;
UserPromptSubmit/PreToolUse/registry `busy` → WORKING; Stop/registry `idle`
→ WAITING (turn done, awaiting user); registry entry dead (pid gone) →
session gone. Logger hooks left in project settings as the ingest skeleton
for [Build the state-screen daemon](008-build-state-daemon.md).
