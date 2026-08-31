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
- **State Screen** — the display face showing Aggregate State + Count Badge.
- **Usage Screen** — the display face showing rate-limit utilization: the
  Five-Hour Utilization as the headline, the Seven-Day Utilization as a
  subordinate reading.
- **Five-Hour Utilization** — the percentage of the rolling five-hour rate
  limit consumed, with the instant it resets.
- **Seven-Day Utilization** — the same for the rolling seven-day limit.
- **Rotation** — which face the display shows. The State Screen holds the
  display alone whenever the Aggregate State is NEEDS-PERMISSION or
  WAITING; otherwise the two faces alternate.
- **Pulse** — the alternation of the State Screen icon while a session
  demands attention. It is both an attention signal and the only available
  proof that the display is still live: a frame frozen by a lost link can
  never be overwritten with a marker saying so. WAITING blinks its cursor
  block on and off like a terminal prompt; NEEDS-PERMISSION dims its mark
  and restores it.
- **Away** — the user's screen is locked. Distinct from the Night Window:
  either one dims the panel, but only Away suppresses the attention
  override, because a bright panel wakes nobody in an empty room.
- **Night Window** — the hours during which the panel dims by default.
