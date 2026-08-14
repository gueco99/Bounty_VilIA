---
name: project-living4football
description: "living4football.club (TheL4FPRO Academy) VDP hunt state — football academy app, session-cookie auth, no memberships/billing in-app."
metadata: 
  node_type: memory
  type: project
  originSessionId: 46360d1a-7024-4f70-b01a-c28082c84e12
---

Active hunt on `app.living4football.club` (TheL4FPRO Academy — football training academy, Gijón). VDP, not yet confirmed which platform/report form is used (check before drafting — may differ from Secur0 used on Shi Shang).

**Test account:** `gueco+2@imnotahacker.com` / password `Guecogueco99+` (their first two guessed passwords, `Gueco99+` and one other, were wrong — this is the confirmed working one as of 2026-07-27). Account holder "test test" (`u=915`). A second real test player "SECUR0TEST gueco" (`u=916`) was created on this same account during testing (mass-assignment probe on `/perfil/jugadores/nuevo`) and is still active — no delete option found in the UI.

**Stack:** server-rendered pages (not an SPA), FastAPI-style backend (Pydantic 422 validation errors visible), forms POST directly with `csrf`/`csrf_token` hidden fields.

**Confirmed NOT vulnerable (tested and closed):**
- `/perfil/editar?u=<id>` — GET and POST both correctly 403 on foreign IDs, ownership checked before validation.
- `/perfil/jugadores/nuevo` — mass-assignment probe (active/is_active/estado/matricula_pagada/paid/role=admin) had zero effect; "Jugador activo" badge is just a same-account player switcher (no security/billing meaning), confirmed by toggling it.
- `/ajustes/password` — current_password properly validated server-side, rejects wrong password.
- Avatar upload (`/ajustes` POST `avatar` field) — SVG with embedded `<script>`/`onload` rejected server-side ("Formato de imagen no permitido..."); `.png`-renamed SVG (same forged content-type) uploaded with 200 and no error text, but avatar shown afterward was still the default — inconclusive, not confirmed exploitable, not worth re-chasing without a clearer signal.
- `POST /api/academia/progress` (`{lesson_id, completed}`) — Pydantic strictly typed, SQLi/array/null all rejected with clean 422, non-existent lesson_id returns clean 404 (no stack trace/info leak), extra mass-assignment fields (score/certificate/notify_coach/admin) silently ignored.
- Login `next=` query param — not read by any inline script, no open-redirect vector found there.
- `/recuperar-password` → `/verify-otp` OTP brute-force — locks after ~7-10 wrong attempts ("Demasiados intentos. Por favor solicita un nuevo código."); the 10-digit string initially thought "leaked" in the verify-otp page was just the input's `placeholder="1234567890"`, false positive.

**Parked (real bug, but no CVSS impact / already deprioritized by user):**
- Course-progress falsification: any student can call `/api/academia/progress` to mark any lesson (including unopened ones, in courses with dozens of lessons) complete instantly, own account only (cross-user injection of user_id/player_id silently ignored — not exploitable cross-account). Confirmed no downstream consumer: no coach/staff view found, `/about` has zero "coach reviews your progress" language, no certificate/badge/gating tied to completion. User decision 2026-07-27: park indefinitely, "hasta que no consigamos impacto".
- User enumeration on `/recuperar-password`: valid email redirects to `/verify-otp` with a different message (~270ms); invalid email stays on the same page (~75ms). Reproducible, three independent signals (URL/message/timing). Tried to chain into account takeover via OTP brute-force or OTP-leak-in-response — both closed off (see above). Per [[feedback_no_informational_reports]], not being reported since it scores pure Informational under CVSS 4.0 with no viable chain found.
- `living4football-otp-lockout-scope` (pre-existing drafted report, separate from the above): OTP lockout not scoped to account, allows locking out a legitimate user's OTP attempts. User explicitly said to drop this line of investigation ("olvida el bloqueo de otp") — do not revisit unless user brings it up again.

**Also on record from this account (pre-existing drafts, not modified this session):**
- `living4football-prebook-race` — ruled out via Turbo Intruder (see `RULED_OUT.md` in that finding folder).

**Mistake made and recovered:** navigated directly to `/logout` while probing for open-redirect params, which actually logged out the real working session (it wasn't a no-op/confirmation page). Had to re-authenticate with the password above. Lesson: don't navigate to `/logout`-style URLs during recon on this app without expecting it to actually terminate the session.
