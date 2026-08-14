---
name: feedback-verify-against-live-target
description: "Never submit a finding based only on a local checkout — always reproduce it against the real deployed target before reporting, especially anything that depends on config defaults (SECRET_KEY, DEBUG, env vars)."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: baa01792-70fa-44de-a3b4-a1b53d506c1c
---

Always reproduce a finding against the real, live deployed target before writing/submitting a
report — a local checkout of the repo is not proof the same behavior exists in production.

**Why:** During the TheHackersLabs-Academy audit, two findings that looked solid locally
turned out to be false positives against the real target (`academy.thehackerslabs.com`):
- `thehackerslabs-unhandled-doesnotexist-debug-leak`: reproduced the 500 crash in prod, but
  prod has `DEBUG=False` (generic "Server Error (500)" page, no traceback) — the actual
  info-disclosure impact didn't exist outside my local `.env` where I'd left `DEBUG=True`.
- `thehackerslabs-hardcoded-secret-key-auth-bypass` (already submitted to Secur0 as #2307
  before this was caught): forging a JWT with the code's default `SECRET_KEY` got a clean 401
  in prod — the real deployment has a proper custom `SECRET_KEY`, unlike my local `.env` where
  I'd deliberately set the insecure default to simulate the scenario. Had to draft a public
  retraction after the report was already open.

Both false positives shared the same shape: the vulnerability required a specific
environment-variable misconfiguration (`DEBUG`/`SECRET_KEY` left at the code's fallback
default) that I had manually reproduced in my own local `.env` to build the PoC, and then
never re-checked against the real system before writing the report.

**How to apply:**
- Any finding whose exploitability hinges on a config default (`DEBUG`, `SECRET_KEY`, CORS
  origins, env-var fallbacks, feature flags) — test it against the live target's actual
  response, not just the local dev checkout, before considering it confirmed.
- Findings that are pure application-logic/access-control bugs in the code itself (IDOR,
  missing rate limits, missing ownership checks, unauthenticated file serving) are safer bets
  locally since they don't depend on deployment config — but even those should get a live
  confirmation pass when there's an authenticated session available, per this session's later
  practice of re-testing `/media/` file disclosure directly against
  `academy.thehackerslabs.com` before finalizing that report.
- If a finding was already submitted before this check was done and turns out to be invalid
  in production, draft a prompt, honest retraction rather than leaving it open for a triager to
  mark N/A.
