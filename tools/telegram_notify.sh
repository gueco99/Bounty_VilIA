#!/bin/bash
# Send a plain text message to the paired Telegram chat via the Bot API directly.
# Independent of the claude-code-channels plugin/session — safe to call from cron.
#
# Reads the token from ~/.claude/channels/telegram/.env (same file the official
# plugin uses) and the chat id from ~/.claude/channels/telegram/access.json
# (first entry in allowFrom).
#
# Usage: tools/telegram_notify.sh "message text"
#        echo "message text" | tools/telegram_notify.sh

set -euo pipefail

STATE_DIR="${TELEGRAM_STATE_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/channels/telegram}"
ENV_FILE="$STATE_DIR/.env"
ACCESS_FILE="$STATE_DIR/access.json"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "telegram_notify: TELEGRAM_BOT_TOKEN not set (checked $ENV_FILE)" >&2
  exit 1
fi

CHAT_ID="${TELEGRAM_CHAT_ID:-}"
if [ -z "$CHAT_ID" ] && [ -f "$ACCESS_FILE" ]; then
  CHAT_ID=$(python3 -c "
import json
try:
    d = json.load(open('$ACCESS_FILE'))
    ids = d.get('allowFrom') or []
    print(ids[0] if ids else '')
except Exception:
    print('')
")
fi

if [ -z "$CHAT_ID" ]; then
  echo "telegram_notify: could not resolve chat id (checked TELEGRAM_CHAT_ID and $ACCESS_FILE)" >&2
  exit 1
fi

MSG="${1:-$(cat)}"
if [ -z "$MSG" ]; then
  echo "telegram_notify: empty message, nothing to send" >&2
  exit 1
fi

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${MSG}" \
  -o /dev/null -w "telegram_notify: HTTP %{http_code}\n"
