#!/bin/bash
# Render the launch agent and hook config for wherever this repo happens to
# live, then load the agent. launchd does not expand ~, so the plist needs a
# real absolute path — hence a template rather than a checked-in file that
# would be wrong for everyone but its author.
#
#   ./scripts/install.sh            render, install and load
#   ./scripts/install.sh --render   render only, install nothing

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="local.claude-display"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
RENDER_ONLY=false
[ "${1:-}" = "--render" ] && RENDER_ONLY=true

render() {  # template -> stdout, with this machine's paths filled in
    sed -e "s|__REPO__|$REPO|g" -e "s|__HOME__|$HOME|g" "$1"
}

echo "repo: $REPO"

# --- per-machine settings --------------------------------------------------
if [ ! -f "$REPO/.env" ]; then
    cp "$REPO/.env.example" "$REPO/.env"
    echo "created $REPO/.env from the example"
fi
if ! grep -qE '^PIXOO_ADDRESS=.+' "$REPO/.env"; then
    echo "error: set PIXOO_ADDRESS in $REPO/.env before installing." >&2
    echo "       Find the address in System Settings > Bluetooth, or with" >&2
    echo "       blueutil --inquiry 10. Do not pair the device." >&2
    exit 1
fi

# --- preflight: the venv must exist and carry the Bluetooth bindings --------
if [ ! -x "$REPO/.venv/bin/python" ]; then
    echo "error: no venv at $REPO/.venv — see the Install section of README.md" >&2
    exit 1
fi
if ! "$REPO/.venv/bin/python" -c "import IOBluetooth, Quartz, PIL" 2>/dev/null; then
    echo "error: venv is missing dependencies (or is on a Python older than 3.10)." >&2
    echo "       $("$REPO/.venv/bin/python" -V 2>&1); run:" >&2
    echo "       $REPO/.venv/bin/pip install -r $REPO/requirements.txt" >&2
    exit 1
fi

# --- hook config, ready to merge into ~/.claude/settings.json ---------------
OUT="$REPO/hooks/user-settings-hooks.generated.json"
render "$REPO/hooks/user-settings-hooks-snippet.json" > "$OUT"
echo "wrote $OUT"
echo "  -> merge its entries into the \"hooks\" object of ~/.claude/settings.json"

if $RENDER_ONLY; then
    render "$REPO/launchd/$LABEL.plist.template"
    exit 0
fi

# --- launch agent ----------------------------------------------------------
mkdir -p "$HOME/Library/LaunchAgents"
render "$REPO/launchd/$LABEL.plist.template" > "$PLIST"
plutil -lint "$PLIST" >/dev/null
echo "wrote $PLIST"

# a running agent must be stopped before reloading, and the device needs a
# quiet moment afterwards or it refuses the next connect (see ADR 0001)
if launchctl print "gui/$UID/$LABEL" >/dev/null 2>&1; then
    echo "stopping the running agent..."
    launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
    sleep 3
fi

launchctl bootstrap "gui/$UID" "$PLIST"
echo "agent loaded. macOS may now prompt to allow Bluetooth for Python — allow it."
echo "watch it come up:  tail -f $HOME/Library/Logs/claude-display.log"
