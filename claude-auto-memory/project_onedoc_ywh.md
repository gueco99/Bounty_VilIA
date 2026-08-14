---
name: project-onedoc-ywh
description: "OneDoc (YesWeHack) bug bounty program — scope, hard compliance rules, test-account setup, findings so far"
metadata: 
  node_type: memory
  type: project
  originSessionId: af7dde18-801c-473e-bf9a-1ea1802fac29
---

Active hunt on YesWeHack program **OneDoc** (onedoc.ch), a Swiss digital-health platform. Started 2026-07-15, switched to from Coupang TW mid-session (see [[project_coupang_tw]] for that program's parked state).

**Scope (4 assets):**
- `https://api.onedoc.ch` — API, asset value **Critical** (Low €100 / Med €500 / High €2,500 / Crit €5,000) — highest priority, most valuable scope.
- `https://www.onedoc.ch` — patient-facing web app, asset value High.
- `https://pro.onedoc.ch` — healthcare-professional app, only verified pros should log in — patients logging in here would be a finding. Asset value High.
- `https://telehealth.onedoc.ch` — video consultation app, patients must not access a room not created for them. Asset value High.

**Hard compliance rules:** fake doctor "Dr Bug Bounty" ONLY (real doctors forbidden), UA suffix `-BugBounty-onedoc-31337`, max 5 req/s, no PII in reports/screenshots (redact), don't extract full leaked data if found (describe/list only), don't use a compromised account to hunt further post-auth bugs, no bulk notifications (>30), no public disclosure ever. Full list in prior version of this memory / the program page.

**Tooling incident (fixed):** `tools/recon_engine.sh`'s katana crawl phase had NO rate-limit flag and fired ~339k requests in ~5min (~1100 req/s) against OneDoc before being killed — way over the 5 req/s cap. Fixed by adding `-rl "$RATE_LIMIT"` to katana (recon_engine.sh line ~379), plus added the same `RATE_LIMIT`/`NUC_RATE_LIMIT` wiring to `tools/vuln_scanner.sh` (nuclei SQLi call + dalfox worker/delay), which had no rate-limit at all before. Always export `BB_RATE_LIMIT=5` (and `NUC_RATE_LIMIT=5`) before running recon/vuln_scanner against this program. User decided not to disclose the incident to the program ("arregla y sigue buscando, no importa lo demas").

**Test account (live, created 2026-07-15):**
- Email: `gueco-ywh-cec455c3232b7382@yeswehack.ninja`, password `hsm9JWWnh2B1euHe`, phone +34 674249691.
- Patient userId: **3198241**, clientId 31863094, name "gueco blue" (fictitious test identity, DOB 1999-02-08).
- Confirmed appointment with Dr. Bug Bounty (professionalId 2527818, entityId 45488, appointmentTypeId 143455 = "telehealth" testing type) — 2026-07-16 11:40, video consultation.
- Telehealth room: `https://telehealth.onedoc.ch/en/join/af30f8c4-dbea-4dab-b523-2510bfe101ab` (clientLookupId, UUIDv4). Professional's lookupId for same appointment: `a0e20799-353d-4497-bdde-488fd0c4d986`.
- Browser session kept alive independently via a detached Chromium process on `--remote-debugging-port=9333` (profile dir `/tmp/.../scratchpad/pw/chrome-profile`), reconnect anytime with Playwright `chromium.connectOverCDP('http://localhost:9333')` rather than relaunching — avoids repeating registration/OTP. Cookies also snapshotted to `scratchpad/pw/authenticated_state.json`.

**Findings tested so far — all properly defended (no confirmed vuln yet):**
1. `GET /api/users/{otherUserId}/appointment-events` with my session → 403 "not authorized". IDOR by user-id: blocked.
2. Swapping `professionalLookupId` into the patient `/en/join/{id}` telehealth URL → 403 on `/api/remote-consultations/{id}`. Role confusion: blocked.
3. Telehealth room join has a server-enforced time gate (rejects >15min before appointment) — not just client-side.
4. Room tokens are UUIDv4, not sequentially enumerable.
5. Patient/pro cookie sessions are domain-scoped (no shared session cookie between www./pro./telehealth.onedoc.ch) — no accidental cross-app session leak.
6. **Interesting but not yet conclusive**: patient credentials DO authenticate successfully against `pro.onedoc.ch`'s `/api/v1/auth/tokens` (shared identity/auth backend across patient and pro apps), returning valid access+refresh tokens. But `GET /api/v1/auth/accesses?application=pro` correctly returns `"accessible": false, "roles": []` for a patient account, and the pro.onedoc.ch frontend respects this (shows "You cannot access this page", bounces to login). **Not yet tested**: whether that authorization check is also enforced server-side on actual pro data endpoints (patient lists, calendars, etc.) when hitting them directly with the valid bearer accessToken, bypassing the frontend route guard — this is the standard way this class of bug turns into a real BOLA/broken-function-level-authorization finding. No concrete pro-only data endpoint identified yet (would need the pro.onedoc.ch JS bundle mapped).

**Further testing (2026-07-15, same session) — also all properly defended:**
7. `GET pro.onedoc.ch/api/v1/clients` (found via pro_main.js bundle grep for `/${p.Kd.Clients}` route names) requires header `X-API-Version: 1.1.0` (format `X.Y.Z`, from `_addApiVersionHeader` in the bundle, default `"1.1.0"`). Unscoped call → 200 with empty data (red herring, not a bypass — just nothing to return). Scoped call with `professionalId=2527818` (the fictitious test doctor, safe to test) → 403 "not authorized". So this endpoint DOES enforce authorization once a real target is specified — initial empty-200 was a false alarm, not exploitable.
8. `api.onedoc.ch` is a separate bearer-token backend (not cookie-based), confirmed via `www-authenticate: Bearer realm="Login"` on 401s, `access-control-allow-origin: *` (open CORS, but no cookies/credentials involved so not itself exploitable). Guessed REST paths (`/v1/professionals/{id}`, `/v1/users/{id}`) are wrong — 404, real route structure not yet mapped beyond the one endpoint below.
9. `GET api.onedoc.ch/professionals/{professionalId}/appointment-events/{eventId}.ics` (calendar export, found via the `iCalendarUrl` field in an appointment-events response) — my patient bearer token correctly fetches MY OWN appointment (200, `text/calendar`). Tested IDOR by requesting neighboring `eventId` values (2046693144, 2046693145, 2046693147 — likely other bug-bounty hunters' test bookings with the same fake doctor, so safe territory) → all **401** ("not authorized"), never leaked another booking. Properly protected.

**Status as of 2026-07-15 end of session: no confirmed vulnerability on OneDoc.** 9 distinct hypotheses tested (IDOR by user-id, telehealth role confusion, room time-gating, cross-app cookie leakage, shared-auth cross-app token, unscoped vs scoped clients-endpoint authz, calendar-export IDOR by sequential event id) — all correctly defended. This is a genuinely well-hardened app on every vector tried so far.

**Why this matters:** IDOR/broken-auth on api.onedoc.ch pays the most (Critical, up to €5,000), so it was worth the thorough pass, but the low-hanging fruit is gone.
**How to apply / untried angles for next session:** api.onedoc.ch's real route structure (beyond the one `.ics` endpoint) is still unmapped — would need the mobile app's APK/IPA decompiled (see [[project_onedoc_ywh]] scope: this API very likely backs the OneDoc mobile app, not the web frontends) to find more real paths, since guessing REST conventions failed. Other untried angles: booking "Someone else (child, parent, etc.)" flow for cross-account data association bugs, appointment cancel/reschedule race conditions, and file upload if any exists in the patient/pro flow (not yet located). Don't re-test the 9 items above — they're confirmed secure.
