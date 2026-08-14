---
name: reference-secur0-api-pipeline
description: "Secur0's unofficial API endpoints, the automation pipeline built to use them (tools/secur0_api.py, secur0_watch_and_hunt.sh), and the hard rules around auth/consent that shape it"
metadata: 
  node_type: memory
  type: reference
  originSessionId: ff7451f9-ed99-4be8-8d13-3103f0c4f6ba
---

Built 2026-07-30/31. All endpoints discovered by reading captured browser traffic the user
pasted this session — none are officially documented, so re-verify if they ever start
returning unexpected errors (they can change without notice).

## Endpoints (base `https://api.secur0.com/api`, staging mirror at `preapi.secur0.com`)

- `GET /programs/list` — public, no auth, paginated. Used by `tools/secur0_watcher.py` to
  detect new programs (diffed against `memory/known_secur0_programs.jsonl`).
- `GET /programs/details?type={VDP|BBP}&name={name}` — public, no auth. Returns `program_id`,
  `is_guideline_signed`, and `scopes` (each with `scope_id`, `pattern`, `in_scope`,
  `is_deleted`). This is how to resolve a program name into the IDs `create_report` needs.
- `POST /guidelines/sign/{program_id}` — needs session cookies, empty body. Returns
  `{"message":"Guideline signed successfully"}`, or HTTP 400
  `{"error_code":"guideline_already_signed"}` if already done (treated as success, not an
  error, by `secur0_api.sign_guidelines()`). **Only needs to happen once per program, ever**
  — safe (and expected) to call it again before every subsequent report to the same program;
  it'll just no-op via the already-signed branch. Confirmed live 2026-07-31 against chezmoi
  (already signed from a prior session) before submitting finding #5 there.
- `POST /reports/create` — needs session cookies. Body: `{"program":{"program_id":N},
  "scope":{"scope_id":N},"title":<b64>,"payload":<b64>,"language":"en","description":<b64>,
  "proof_of_concept":<b64>,"impact":<b64>}`. Text fields are base64-encoded (confirmed by
  decoding a real captured request). Returns `{"report_id":N,"upload_token":"..."}` on
  success (201). **Does not accept CVSS/Endpoint/Colaboradores/Attachments** — those are
  presumably set via a separate PATCH + the upload_token, never mapped (user said to skip
  them, "me da igual").
- `POST /api/auth/login` (host `api.secur0.com`, not `/api/api/...`) — takes
  `username_or_email`/`password`/etc, sets `sessionid`+`csrftoken` cookies on success. **Never
  called by any script or by me directly — see Hard rules below.**

## Tooling built

- `tools/secur0_api.py` — the client module. Functions: `get_program_details`,
  `get_in_scope_targets`, `sign_guidelines`, `create_report`, `parse_report_markdown` (handles
  both the current `## Title` report template and the older `## Title (0/100)` fenced-code
  style), `submit_report_from_file`. CLI: `save-session`, `details`, `sign`, `parse`, `submit`.
- Session cookies live in `memory/secur0_session.json` (gitignored, chmod 600) — written only
  via `save_session()`/the `save-session` CLI subcommand, never fetched automatically.
- `secur0_watch_and_hunt.sh` — the cron-driven pipeline: watcher finds a new program → fetch
  its details/scopes (no auth) → auto-sign guidelines (no confirmation gate, see below) →
  launch `autopilot` agent with the real in-scope targets → draft-only, queues via
  `PendingSubmissionsDB` → `PushNotification`. Never submits on its own.

## Hard rules established this session (don't relitigate these)

1. **Never perform the login step myself, ever, with or without confirmation, with or
   without the password touching disk.** This came up four separate times in one session
   (paste-the-password, "just delete that rule", "write a script with no password, I'll type
   it", all declined) — it's the absolute-prohibited-actions category (entering credentials
   to authenticate), not the ask-first category, so no phrasing of "just this once" or "the
   script does it not you" changes it. The user login refresh path is: they log in via
   Firefox (I re-read `cookies.sqlite` for the `.secur0.com` domain cookies) or via `!curl`
   in a live session (they type the real command themselves with the `!` prefix; I only ever
   see the already-completed response). Twice now the user's real password ended up in the
   conversation transcript this way anyway (the `!` prefix still echoes the full command) —
   told them to rotate it both times, don't skip that reminder if it happens again.
2. **Signing guidelines is automatic, no confirmation, always surfaced in the
   notification/summary text.** Explicit user decision 2026-07-31, after I raised that this
   falls under "explicit permission required" in my own operating rules — they chose to
   accept the low stakes (standard boilerplate safe-harbor terms, not a real contract) over
   the friction. Keep it visible every time regardless.
3. **Report submission (`create_report`) always needs the user's explicit "yes" first**,
   same as the pre-existing "envía" convention — this one was never renegotiated, still holds
   even for pipeline test runs. Confirmed working 2026-07-31: submitted a genuinely new
   chezmoi finding (decompression bomb, report_id 3108) after the user said "sí" to a
   pre-submission summary.
4. **CVSS/Endpoint/Colaboradores/Attachments are deliberately left out of automated
   submissions** — explicit user instruction ("me da igual"), not an oversight. If this
   changes, the PATCH endpoint + upload_token flow still needs to be discovered/built.

## Bugs found and fixed in the tooling itself (2026-07-31, cogny)

- `parse_report_markdown`'s `extract()` had Spanish aliases for description/proof_of_concept/
  impact ("detalle técnico", "prueba de concepto", "impacto") but NOT for title — a
  Spanish-language report (`## Título`) parsed to an empty title, and `create_report` rejected
  it with `{"title":["This field may not be blank."]}`. Fixed: added "título"/"titulo" aliases.
- `language` was hardcoded to default "en" regardless of the report's actual content language.
  Fixed: `parse_report_markdown` now detects Spanish from which title-alias matched and returns
  `"language": "es"` accordingly, flowing through `submit_report_from_file`'s `**fields`.
  **Known gap:** cogny report #3117 was submitted BEFORE this fix, so it's tagged language=en
  despite Spanish content — no PATCH/edit endpoint discovered yet to correct it after the fact.
- Also hit `POST /guidelines/sign/{program_id}` returning `404 program_not_found` for a
  brand-new program (cogny, went active same-day at 18:00 same session) even though
  `GET /programs/details` resolved the same program_id fine and showed `is_guideline_signed:
  false`. Didn't guess at an alternate ID for a legally-binding NDA signature — asked the user
  to sign manually via the web UI instead, which worked; `create_report` itself had no issue
  once that was done. Re-test this specific case (very-recently-activated program) before
  assuming the sign endpoint is broken in general — could be provisioning lag specific to
  brand-new programs, not a lasting API regression.

- `POST /reports/create` rejects the `title` field with `{"title":["invalid_format"]}` if it
  contains an underscore-joined identifier-looking token — confirmed NOT limited to
  ALL_CAPS_WITH_UNDERSCORES: 2026-07-31 cogny hit it with "SECRET_KEY" (fixed by rewording to
  "Clave secreta"), and 2026-07-31 script-server hit it again with a plain lowercase token,
  "server_file" (fixed by rewording to "server file", two words, no underscore). Only the title
  field itself is validated this way — the same token appears freely elsewhere in the report
  body (description/payload/etc.) with no issue. If a future title submission fails with this
  exact error, reword ANY underscore-containing token (regardless of case) into separate plain
  words first before assuming something else is wrong.
- The same `invalid_format` title error also fires on other "non-plain-text" punctuation, not
  just underscores: 2026-08-02 cogny hit it with a `~` inside "~2 GB" (fixed by spelling it out
  as "varios GB"). Working theory: the title validator wants plain words/spaces and rejects at
  least `_` and `~`; if it recurs, strip any unusual punctuation from the title first (numbers,
  slashes like "/s/token", and normal Spanish accents/ñ have all gone through fine elsewhere).

- `POST /reports/create` can also return a bare `HTTP 500 {"error_code":"internal_error"}` (not
  the usual 400 `invalid_format`) when the title is too long — hit this 2026-08-06 on chezmoi
  with a 129-character title, fixed by shortening to ~65 chars, worked on the very next attempt.
  Don't retry-spam the live endpoint on a 500 (per [[feedback_dont_test_via_live_api]]) — check
  title length first (keep well under ~100 chars) before assuming a server outage.

## If resuming this pipeline

- The known-programs seed (`memory/known_secur0_programs.jsonl`) was seeded 2026-07-31 with
  43 real production programs — don't re-seed, just let the watcher run normally.
- No crontab entry has actually been installed yet (see `~/.claude/plans/lucky-wishing-bee.md`
  for the original design doc) — this session validated the mechanics manually, end to end,
  but the "runs by itself daily" automation step is still pending if the user wants it.
