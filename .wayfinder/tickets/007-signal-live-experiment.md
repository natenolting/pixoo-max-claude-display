---
title: Signal live experiment
labels: [wayfinder:task]
status: open
assignee:
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
