---
name: feedback_scope_pkill_by_port
description: "never pkill by a generic process-name pattern (e.g. \"manage.py runserver\") on a shared sandbox — scope to the specific port/pid you started, since another concurrent session may be running the same command"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 34489275-58f5-410f-8b5b-40d13626490b
---

On 2026-08-07, while restarting a local Django test server during a cogny hunt, I ran
`pkill -f "manage.py runserver"` to clear a stuck process before relaunching my own. This
pattern-matched and killed a **completely unrelated Django server from a different concurrent
session** on the same machine (a different scratchpad directory, `ff7451f9-...`, not mine,
running on port 8123). I had no way to know what that other session was doing with it, and
could not restart it on their behalf.

**Why this happened**: `pgrep -af`/`pkill -f` match on the full command line substring, not on
anything scoped to "processes I started." A generic command name like `manage.py runserver` is
extremely likely to be shared across concurrent sessions on a shared sandbox host.

**How to apply**: before killing any background process by name/pattern, first list matches
(`pgrep -af <pattern>`) and inspect them — if a match includes a port, path, or PID you didn't
start yourself, do NOT kill it. Prefer killing by the exact PID you captured when you launched
the process (`kill $MY_PID`), or scope the pattern as tightly as possible (e.g., include the
specific port you're using: `pkill -f "runserver 127.0.0.1:8000"` rather than bare
`"manage.py runserver"`). This is the same category of mistake as the earlier
"fuzzer must exclude auth methods" lesson — an insufficiently scoped bulk action on a shared
resource — just for process management instead of network calls.
