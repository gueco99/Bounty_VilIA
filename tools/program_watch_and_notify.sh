#!/bin/bash
# Combined watcher: Secur0 + HackerOne/Bugcrowd/YesWeHack. Sends one Telegram
# alert per run if anything new/changed was found. Intended for cron.
#
# Usage: tools/program_watch_and_notify.sh          # normal run
#        tools/program_watch_and_notify.sh --seed   # first-run seeding, no alerts

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

SEED_FLAG=""
if [ "${1:-}" = "--seed" ]; then
  SEED_FLAG="--seed"
fi

SECUR0_OUT=$(python3 tools/secur0_watcher.py $SEED_FLAG 2>&1)
SECUR0_STATUS=$?

BOUNTY_OUT=$(python3 tools/bounty_targets_watcher.py $SEED_FLAG 2>&1)
BOUNTY_STATUS=$?

if [ -n "$SEED_FLAG" ]; then
  echo "=== Secur0 ==="; echo "$SECUR0_OUT"
  echo "=== H1/Bugcrowd/YesWeHack ==="; echo "$BOUNTY_OUT"
  exit 0
fi

# secur0_watcher.py emits JSON (new_programs: [...]), not [NEW]-prefixed lines
# like bounty_targets_watcher.py -- normalize it to the same line format here.
SECUR0_LINES=$(echo "$SECUR0_OUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for p in d.get('new_programs', []):
    name = p.get('name') or p.get('handle', '?')
    ptype = p.get('program_type') or '?'
    handle = p.get('handle','?')
    print(f\"[NEW] secur0 {name} ({handle}) type:{ptype} -> \\\"caza {handle}\\\"\")
" 2>/dev/null || true)

ALERT_LINES=""
for line in "$SECUR0_LINES" "$BOUNTY_OUT"; do
  filtered=$(echo "$line" | grep -E "^\[NEW\]|^\[SCOPE CHANGE\]" || true)
  if [ -n "$filtered" ]; then
    ALERT_LINES="${ALERT_LINES}${filtered}
"
  fi
done

if [ -n "$ALERT_LINES" ]; then
  COUNT=$(echo "$ALERT_LINES" | grep -c . || true)
  MSG="Vigilancia de programas — ${COUNT} novedad(es):
${ALERT_LINES}"
  echo "$MSG" | tools/telegram_notify.sh
else
  echo "$(date -Iseconds) no changes"
fi

if [ "$SECUR0_STATUS" -ne 0 ]; then
  echo "secur0_watcher failed:" >&2; echo "$SECUR0_OUT" >&2
fi
if [ "$BOUNTY_STATUS" -ne 0 ]; then
  echo "bounty_targets_watcher failed:" >&2; echo "$BOUNTY_OUT" >&2
fi
