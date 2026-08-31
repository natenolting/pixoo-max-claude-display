#!/bin/bash
# Post-reboot check for the Pixoo display daemon.
#
# Verifies the three things a cold boot can break: the launchd agent
# starting at login, macOS silently re-pairing the Pixoo (which makes the
# device refuse RFCOMM — see docs/adr/0001-unpaired-direct-rfcomm.md), and
# frames actually reaching the panel.
#
#   ./scripts/postboot-check.sh          report only
#   ./scripts/postboot-check.sh --fix    also unpair and restart if needed

set -uo pipefail
ADDR_DASH="11-75-58-6e-bf-c1"
LABEL="com.natenolting.claude-display"
LOG="$HOME/Library/Logs/claude-display.log"
FIX=false
[ "${1:-}" = "--fix" ] && FIX=true

fail=0

# 1. did launchd start it at login?
if launchctl print "gui/$UID/$LABEL" >/dev/null 2>&1; then
    pid=$(launchctl print "gui/$UID/$LABEL" 2>/dev/null | awk '/^\tpid = /{print $3}')
    if [ -n "$pid" ]; then
        echo "OK    agent running (pid $pid)"
    else
        echo "FAIL  agent loaded but not running"
        fail=1
    fi
else
    echo "FAIL  agent not loaded — launchctl bootstrap gui/\$UID ~/Library/LaunchAgents/$LABEL.plist"
    fail=1
fi

# 2. did macOS re-pair the device? (the failure that has bitten us repeatedly)
if command -v blueutil >/dev/null 2>&1; then
    paired_out=$(blueutil --paired 2>&1)
    if [ $? -ne 0 ]; then
        # blueutil aborts without the Bluetooth grant; empty output would
        # otherwise read as "not paired" and hide the very failure we check for
        echo "SKIP  blueutil could not read Bluetooth (run this from Terminal,"
        echo "      which holds the Bluetooth permission): ${paired_out%%$'\n'*}"
    elif grep -qi "$ADDR_DASH" <<<"$paired_out"; then
        echo "FAIL  Pixoo is PAIRED — macOS grabs it as an audio device and RFCOMM is refused"
        fail=1
        if $FIX; then
            echo "      unpairing..."
            blueutil --unpair "$ADDR_DASH" && echo "      unpaired"
        else
            echo "      fix: blueutil --unpair $ADDR_DASH"
        fi
    else
        echo "OK    Pixoo unpaired (as ADR 0001 requires)"
    fi
else
    echo "SKIP  blueutil not installed; cannot check pairing"
fi

# 3. are frames actually landing?
if [ -f "$LOG" ]; then
    recent=$(tail -20 "$LOG")
    if grep -q "device unreachable" <<<"$recent"; then
        echo "FAIL  daemon cannot reach the panel (last 20 log lines)"
        fail=1
    elif grep -qE "^\[daemon\] (brightness|IDLE|WORKING|WAITING|NEEDS_PERMISSION|usage)" <<<"$recent"; then
        echo "OK    frames pushing — last: $(grep -E '^\[daemon\]' <<<"$recent" | tail -1)"
    else
        echo "WARN  no recent frame activity in the log"
    fi
else
    echo "FAIL  no log at $LOG"
    fail=1
fi

if $FIX && [ "$fail" -ne 0 ]; then
    echo "restarting agent..."
    launchctl kickstart -k "gui/$UID/$LABEL" 2>/dev/null \
        || launchctl bootstrap "gui/$UID" "$HOME/Library/LaunchAgents/$LABEL.plist"
    sleep 6
    tail -3 "$LOG"
fi

if [ "$fail" -eq 0 ]; then
    echo "--> display is healthy"
else
    echo "--> problems found${FIX:+ (fix attempted above)}; if the panel is still dark, power-cycle the Pixoo and rerun"
fi
exit "$fail"
