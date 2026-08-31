# claude-display

Drives a **Divoom Pixoo Max** (32×32 LED panel) as a live status display for
Claude Code sessions on macOS.

The panel rotates between three faces:

| Face | Shows | Duration |
|---|---|---|
| **State** | whether any session needs you — colour + icon + a count when more than one session shares that state | 12 s |
| **Rate limits** | five-hour utilisation as a big `NN%`, with five-hour and seven-day fill bars | 8 s |
| **Tokens** | today's input + output tokens, compacted (`293ᴷ`, `1.2ᴹ`) | 8 s |

Rotation stops whenever a session **needs permission** (red `!`) or is
**waiting on you** (amber hourglass) — those hold the panel alone and pulse,
so an urgent state is never hidden behind a number.

Everything runs locally. No API calls, no tokens consumed: hooks write small
JSON files, and the daemon reads those plus local caches and transcripts.

## Requirements

- macOS with Bluetooth (tested on Darwin 25 / Apple Silicon)
- **Python 3.10+** — *not* the system Python. `/usr/bin/python3` is 3.9 on
  macOS, and `pyobjc-core` will not build there (`Could not build wheels for
  pyobjc-core`). Use Homebrew's: `brew install python`
- `jq` — used by the hook script
- `blueutil` (`brew install blueutil`) — only for diagnostics
- Node/`npx` — only for the token face, via `ccusage`

## Install

```bash
cd ~/claude-display
/opt/homebrew/bin/python3 -m venv .venv     # NOT bare `python3` — see above
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import IOBluetooth, Quartz; print('deps ok')"
```

If that last line fails, the venv is on the wrong interpreter. Check with
`.venv/bin/python -V`; anything below 3.10 will not work.

**1. Do not pair the Pixoo.** This is the single most important rule — see
[ADR 0001](docs/adr/0001-unpaired-direct-rfcomm.md). A paired Pixoo is claimed
by macOS as an audio device and refuses the serial channel we need. The daemon
unpairs it automatically, but never pair it by hand.

**2. Install the hooks.** Merge the contents of
[`hooks/user-settings-hooks-snippet.json`](hooks/user-settings-hooks-snippet.json)
into the `hooks` object of `~/.claude/settings.json`, keeping any hooks already
there. `SessionEnd` must stay synchronous (`"timeout": 3`, no `"async"`) — an
async one loses the race against process exit and leaves a phantom session on
the panel.

**3. Install the launch agent.**

```bash
cp launchd/com.natenolting.claude-display.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.natenolting.claude-display.plist
```

**4. Approve Bluetooth.** macOS prompts once, naming *Python*. Allow it. The
grant belongs to the venv's Python binary, which is the agent's own identity —
so the daemon needs no terminal after this.

The panel should light within about fifteen seconds.

## Daily use

Nothing. It starts at login, reconnects on its own, dims at night, and blanks
itself when stopped.

```bash
./scripts/postboot-check.sh          # is it healthy?
./scripts/postboot-check.sh --fix    # unpair and restart if not
```

Run the check **from Terminal** — reading pairing state needs the Bluetooth
permission, which Terminal has. It says `SKIP` rather than lying when it
cannot look.

```bash
tail -f ~/Library/Logs/claude-display.log                     # watch it
launchctl kickstart -k gui/$UID/com.natenolting.claude-display  # restart
launchctl bootout gui/$UID/com.natenolting.claude-display       # stop
```

A **dark panel means nothing is driving it** — the daemon blanks the display
on a clean exit, so darkness is honest rather than a stale frame.

## When something is wrong

**Panel dark, log says `device unreachable`.** The daemon retries with backoff
and reports how long it has been out every five minutes. If it persists past a
few minutes the device has wedged, and it needs a power cycle **with the daemon
stopped** — power-cycling underneath a running daemon usually fails, because its
retries never give the device a quiet moment to come up:

```bash
launchctl bootout gui/$UID/com.natenolting.claude-display   # stop first
# power-cycle the Pixoo, wait a few seconds
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.natenolting.claude-display.plist
```

If that still fails, reset the Mac's Bluetooth stack with `sudo pkill bluetoothd`
(it respawns in a couple of seconds) and repeat.

Restarting the daemon repeatedly in quick succession is itself a way to wedge
the device — each restart tears down and rebuilds the Bluetooth session. In
normal use it starts once at login and this never arises; it mainly bites while
iterating on the code.

**Panel dark after a reboot.** Expected to self-heal: macOS re-pairs the device
during startup, the daemon notices and unpairs it, and the panel comes up after
a couple of retries. If it does not, power-cycle the Pixoo.

**Token face blank / log says `npx not found`.** launchd gives agents a bare
`PATH`, so Node must be findable. The daemon looks in `/opt/homebrew/bin`,
`/usr/local/bin` and `~/.local/bin`; add yours to `NPX_FALLBACKS` in
[`claude_display/tokens.py`](claude_display/tokens.py) if it lives elsewhere.

**Panel shows a session that has ended.** A session's registry file disappears
on exit and the daemon drops it after a 15 s grace. If phantoms persist, check
that the `SessionEnd` hook is synchronous.

**Nothing in the log at all.** The agent is not running:
`launchctl print gui/$UID/com.natenolting.claude-display`.

## Configuration

Constants, all in-code:

| Setting | Where | Default |
|---|---|---|
| Device address | `daemon.py` `PIXOO_ADDR` | `11-75-58-6e-bf-c1` |
| Face durations | `daemon.py` `*_FACE_S` | 12 / 8 / 8 s |
| Day / night brightness | `brightness.py` | 80 / 15 |
| Night window | `brightness.py` | 22:00–07:00 |
| Waiting → idle demotion | `state.py` | 30 min |
| Token poll interval | `tokens.py` | 5 min |

`--brightness N` overrides the daytime level; `--dry-run` renders to
`/tmp/claude-display/frame.png` instead of the device, which needs no
Bluetooth and is the easiest way to test changes:

```bash
.venv/bin/python -m claude_display --dry-run
```

## How it works

```
Claude Code hooks ─→ /tmp/claude-display/spool/*.json ─┐
~/.claude/sessions/<pid>.json  (swept every 3 s) ──────┼─→ state ─┐
~/.claude/cache/usage-cache.json  (60 s)  ─────────────┤          ├─→ renderer ─→ transport ─→ Pixoo
npx ccusage  (5 min, background thread) ───────────────┘          │
                                                     brightness ──┘
```

| Module | Responsibility |
|---|---|
| `signals.py` | reads the spool and sweeps the session registry; excludes cmux-managed sessions by process ancestry |
| `state.py` | one state per session, precedence, the 30-minute demotion |
| `usage.py` / `tokens.py` | rate-limit and token readings |
| `brightness.py` | day / night / away policy |
| `renderer.py` | the three faces, 32×32 |
| `transport.py` | IOBluetooth RFCOMM, reconnect with backoff, auto-unpair |
| `daemon.py` | the loop, rotation, and the pulse |

Vocabulary lives in [CONTEXT.md](CONTEXT.md); the decisions and the reasoning
behind them are in [`.wayfinder/`](.wayfinder/map.md) and
[`docs/adr/`](docs/adr/). Read [ADR 0001](docs/adr/0001-unpaired-direct-rfcomm.md)
before touching the transport — it is the hardest-won part of this repo.

## Known limits

- **One device.** The address is a constant.
- **A wedged Pixoo needs a physical power cycle.** Nothing in software recovers it.
- **The rate-limit cache goes stale while you are idle**, since only an active
  session refreshes it. A window past its reset instant reads `0%` rather than
  reporting a stale figure.
- **Desktop-app sessions** report no status in the registry, so they are tracked
  through hooks alone.
