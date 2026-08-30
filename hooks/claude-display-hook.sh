#!/bin/bash
# Claude Code hook -> display daemon spool. Reads the hook payload on stdin,
# writes one small JSON event file. Atomic via tmp+rename; never fails the
# hook (daemon down or spool unwritable must not disturb the session).
d=/tmp/claude-display/spool
mkdir -p "$d" 2>/dev/null || exit 0
t="$d/.tmp.$$"
jq -c '{session_id, hook_event_name, cwd, ts: now}' > "$t" 2>/dev/null \
  && mv "$t" "$d/$(date +%s).$$.json" 2>/dev/null
exit 0
