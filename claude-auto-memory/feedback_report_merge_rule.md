---
name: feedback-report-merge-rule
description: "When to merge a new discovery into an existing unsubmitted report vs. write a separate one — user's explicit rule based on whether the fix is the same."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 594c75b1-c898-47af-ba80-5e78975b8a6a
---

When finding something new mid-session that relates to an already-drafted (unsubmitted) finding, decide merge-vs-separate by **whether the fix would be identical**, not by broad vulnerability-class similarity.

- **Merge into the existing report** when it's the same root cause explored deeper — e.g., after finding a leaked DB credential via a Symfony profiler leak, later confirming that credential has `ALL PRIVILEGES WITH GRANT OPTION` (not just read access) is the same bug, more fully proven. One fix (rotate the secret, disable the profiler) covers both.
- **Write a separate report** when it's a different endpoint with a different specific fix, even under the same broad vulnerability class. Example: a static/hardcoded CSRF token on `/login` (fix: generate a real per-session token) vs. a completely absent CSRF token on a GET-based state-changing endpoint elsewhere (fix: add a token *and* change the HTTP verb from GET to POST) — both are "CSRF" but different bugs with different fixes, so separate reports on [[project_gestionominegocio]].

**Why:** the user corrected an in-progress merge attempt with "si tiene el mismo fix no me vale, a no ser que sea en otro endpoint" (2026-07-24) — they don't want new discoveries folded into already-drafted reports just because the vulnerability class matches; each report should map to one distinct fix.

**How to apply:** before merging a new observation into an existing draft, ask: would the remediation section need a genuinely new bullet point describing a different code change, on a different endpoint? If yes, it's a separate report. If the existing remediation already covers it (same secret, same code path, just more impact proven), merge it in. When ambiguous, ask the user rather than guessing — they will correct a wrong merge, but treat that as a signal to ask earlier next time, not just this once.
