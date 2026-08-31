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
LABEL="local.claude-display"
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
paired=unknown
if command -v blueutil >/dev/null 2>&1; then
    paired_out=$(blueutil --paired 2>&1)
    if [ $? -ne 0 ]; then
        # blueutil aborts without the Bluetooth grant; empty output would
        # otherwise read as "not paired" and hide the very failure we check for
        echo "SKIP  blueutil could not read Bluetooth (run this from Terminal,"
        echo "      which holds the Bluetooth permission): ${paired_out%%$'\n'*}"
    elif grep -qi "$ADDR_DASH" <<<"$paired_out"; then
        paired=yes
    else
        paired=no
        echo "OK    Pixoo unpaired (as ADR 0001 requires)"
    fi
else
    echo "SKIP  blueutil not installed; cannot check pairing"
fi

# 3. are frames actually landing?
if [ -f "$LOG" ]; then
    # the log survives reboots, so only consider lines since the daemon's
    # most recent start — otherwise pre-reboot history reads as healthy
    recent=$(awk '/^\[daemon\] up;/{buf=""} {buf=buf $0 ORS} END{printf "%s", buf}' "$LOG")
    # judge by the LATEST frame line, not by whether an outage ever happened:
    # a rocky start that has since recovered is a healthy display
    latest=$(grep -E "^\[daemon\] (brightness|IDLE|WORKING|WAITING|NEEDS_PERMISSION|OFF|usage)" <<<"$recent" | tail -1)
    driving=no
    if [ -z "$latest" ]; then
        echo "WARN  agent started but has not pushed a frame yet"
    elif [[ "$latest" == *"device unreachable"* ]]; then
        echo "FAIL  daemon cannot reach the panel — last: $latest"
        fail=1
    else
        echo "OK    frames pushing — last: $latest"
        driving=yes
    fi

    # A pairing only blocks the NEXT connect; it cannot disturb a channel that
    # is already open. Calling it a failure while frames are flowing told the
    # user to unpair and restart a working display — advice that would break it.
    if [ "$paired" = yes ] && [ "$driving" = yes ]; then
        echo "NOTE  Pixoo is paired again (macOS does this); harmless while"
        echo "      frames are flowing — the daemon clears it at the next connect"
    elif [ "$paired" = yes ]; then
        echo "FAIL  Pixoo is PAIRED and the panel is not being driven —"
        echo "      macOS claims it as an audio device and RFCOMM is refused"
        fail=1
        if $FIX; then
            echo "      unpairing..."
            blueutil --unpair "$ADDR_DASH" && echo "      unpaired"
        else
            echo "      fix: blueutil --unpair $ADDR_DASH"
        fi
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
    if $FIX; then
        echo "--> problems found; fix attempted above. If the panel is still dark, power-cycle the Pixoo and rerun"
    else
        echo "--> problems found. Rerun with --fix to apply the fixes above"
    fi
fi
exit "$fail"
