# CONTEXT — Claude stats on Pixoo Max

Glossary of the ubiquitous language. No implementation details here.

## Terms

- **Tracked Session** — a Claude Code session the user drives directly in an
  interactive terminal. Subagents and fleet-managed (cmux) sessions are not
  Tracked Sessions.
- **Session State** — the state of one Tracked Session. Exactly one of:
  - **NEEDS-PERMISSION** — session is blocked on a permission prompt; work
    is stalled mid-turn until the user acts.
  - **WAITING** — the turn finished; Claude awaits the user's next input.
  - **WORKING** — Claude is mid-turn, actively executing.
  - **IDLE** — session is open but nothing is happening (including a WAITING
    session the user has ignored past the demotion threshold).
  - **OFF** — not a per-session state: the Aggregate State when no Tracked
    Sessions are live.
- **Precedence** — ordering that decides which Session State wins when
  sessions disagree: NEEDS-PERMISSION > WAITING > WORKING > IDLE.
- **Aggregate State** — the single state shown on the display: the highest-
  precedence Session State across all Tracked Sessions, or OFF when there
  are none.
- **Count Badge** — small numeral alongside the Aggregate State: how many
  Tracked Sessions currently share that state.
- **Demotion** — WAITING becomes IDLE after 30 minutes without user
  response. NEEDS-PERMISSION never demotes.
- **State Screen** — the display face showing Aggregate State + Count Badge
  (phase 1).
- **Usage Screen** — the display face showing usage/cost aggregates
  (phase 2, not yet specified).
