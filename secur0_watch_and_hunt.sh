#!/usr/bin/env bash
# Secur0 new-program watch-and-hunt pipeline.
#
# Meant to be invoked by a crontab entry firing at 17:59 local time; this
# script sleeps to the exact target second (cron has no sub-minute
# granularity), then checks for new Secur0 programs and, for each one found,
# launches an unattended autopilot hunt in draft-only mode.
#
# Usage:
#   ./secur0_watch_and_hunt.sh --pre    # staging (test data) — safe to run anytime
#   ./secur0_watch_and_hunt.sh --prod   # production — only after --pre dry runs pass
#
# Report submission is NEVER done by this script. Drafted reports are queued
# in memory/pending_submissions.jsonl and the user is pushed a notification;
# actual submission only happens later, interactively, when the user replies
# "envia" in a live Claude Code session.
#
# Guidelines ARE signed automatically by this script for every new program
# (no confirmation gate -- explicit user instruction, 2026-07-31), via
# tools/secur0_api.py. This needs a cached session (memory/secur0_session.json,
# gitignored, written by `python3 tools/secur0_api.py save-session <id> <csrf>`
# after the user logs in themselves). If there's no valid cached session, the
# script logs a warning and skips guideline-signing + hunting for that
# program rather than failing the whole run -- the user renews the session
# next time they're in a live conversation.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_HOUR=18
TARGET_MIN=0
TARGET_SEC=5

MODE=""
for arg in "$@"; do
  case "$arg" in
    --pre) MODE="--pre" ;;
    --prod) MODE="" ;;
    *) echo "Unknown argument: $arg (use --pre or --prod)" >&2; exit 1 ;;
  esac
done
if [[ -z "${1:-}" ]]; then
  echo "Must specify --pre or --prod explicitly (no silent default, to avoid an accidental production run)." >&2
  exit 1
fi

sleep_until_target() {
  local now target_epoch
  now=$(date +%s)
  target_epoch=$(date -d "today ${TARGET_HOUR}:${TARGET_MIN}:${TARGET_SEC}" +%s 2>/dev/null || \
                 date -j -f "%Y-%m-%d %H:%M:%S" "$(date +%Y-%m-%d) ${TARGET_HOUR}:${TARGET_MIN}:${TARGET_SEC}" +%s)
  if (( target_epoch <= now )); then
    target_epoch=$((target_epoch + 86400))
  fi
  local wait_secs=$((target_epoch - now))
  echo "Sleeping ${wait_secs}s until ${TARGET_HOUR}:$(printf '%02d' $TARGET_MIN):$(printf '%02d' $TARGET_SEC) local time..."
  sleep "$wait_secs"
}

sleep_until_target

echo "Running secur0_watcher.py ${MODE:-(production)}..."
WATCH_RESULT=$(python3 "${REPO_DIR}/tools/secur0_watcher.py" ${MODE})
echo "$WATCH_RESULT"

NEW_COUNT=$(echo "$WATCH_RESULT" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['new_programs']))")

if [[ "$NEW_COUNT" -eq 0 ]]; then
  echo "No new programs detected. Done."
  exit 0
fi

echo "$NEW_COUNT new program(s) detected. Processing each."

echo "$WATCH_RESULT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for p in data['new_programs']:
    print(f\"{p['handle']}\t{p.get('name') or 'unknown'}\t{p.get('url') or ''}\t{p.get('program_type') or 'VDP'}\")
" | while IFS=$'\t' read -r handle name url program_type; do
  echo "=== New program: $name (id $handle, type $program_type) ==="

  # Look up scopes now (no auth needed) so the hunt prompt has real, in-scope
  # targets instead of guessing from the program name.
  DETAILS_JSON=$(python3 "${REPO_DIR}/tools/secur0_api.py" details "$program_type" "$name" 2>&1) || {
    echo "WARNING: could not fetch program details for $name, skipping this program." >&2
    continue
  }
  SCOPES=$(echo "$DETAILS_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
scopes = [s for s in d.get('scopes', []) if s.get('in_scope') and not s.get('is_deleted')]
for s in scopes:
    print(f\"{s['scope_id']}\t{s.get('pattern') or s.get('title') or ''}\")
")
  echo "In-scope targets:"
  echo "$SCOPES"

  # Sign guidelines automatically (no confirmation gate — explicit user
  # instruction). Requires a valid cached session; skip hunting this program
  # (don't fail the whole run) if the session is stale.
  SIGN_RESULT=$(python3 "${REPO_DIR}/tools/secur0_api.py" sign "$handle" 2>&1) && {
    echo "Guidelines signed for $name: $SIGN_RESULT"
  } || {
    echo "WARNING: could not sign guidelines for $name (session likely expired: $SIGN_RESULT)." >&2
    echo "WARNING: skipping hunt for $name until the user refreshes the Secur0 session." >&2
    continue
  }

  echo "Launching headless autopilot hunt for $name..."
  PROMPT="A new Secur0 program was just detected and its guidelines were auto-accepted: \
\"$name\" (program_id $handle, type $program_type, $url). Legal guidelines for this program \
were signed automatically as part of this pipeline (state this plainly in your final summary — \
never leave it silent). In-scope targets (scope_id<TAB>pattern):
$SCOPES

Read /home/diego/.claude/plans/lucky-wishing-bee.md for the full context of this pipeline. \
Launch the autopilot agent (subagent_type: autopilot) in --normal mode against the in-scope \
targets listed above (verify with scope_checker.py before any testing regardless). The agent \
must NEVER submit any report — it only drafts, following the existing \
findings/dia2/<slug>/report_secur0.md convention (no attachments, short titles, no \
CVSS/Endpoint/Colaboradores sections needed for this pipeline). When a report is drafted, add \
it to the pending-submissions queue via memory/pending_submissions_db.py's \
PendingSubmissionsDB.add(target=\"$name\", ...), then call PushNotification summarizing what \
was found AND mentioning the guideline auto-acceptance. If nothing worth reporting is found, \
call PushNotification saying so briefly (still mentioning guideline acceptance) and stop. Do \
not ask any clarifying questions — this is an unattended run; make reasonable calls and \
proceed."

  claude -p "$PROMPT" \
    --allowedTools "Bash,Read,Write,Edit,Grep,Glob,Agent,PushNotification" \
    2>&1 | tee -a "${REPO_DIR}/secur0_autohunt.log" || \
    echo "WARNING: headless claude invocation for program $handle failed, continuing to next" >&2
done

echo "Watch-and-hunt cycle complete."
