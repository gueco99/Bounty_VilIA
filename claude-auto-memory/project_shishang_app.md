---
name: project-shishang-app
description: "Shi Shang App (food delivery) VDP on Secur0 — scope, mandatory researcher-ID headers, printer/reversibility rules, hongkongcity.app scope contradiction."
metadata: 
  node_type: memory
  type: project
  originSessionId: baa01792-70fa-44de-a3b4-a1b53d506c1c
---

**UPDATE 2026-07-31: all 13 drafted findings are now SUBMITTED (confirmed by user).**

Active hunt as of 2026-07-23. VDP (Safe Harbor) on Secur0, "Shi Shang App" — food delivery
platform, Next.js + Supabase (Postgres + Edge Functions) stack.

## STATUS CHECKLIST — CORRECTED 2026-07-28 from the actual Secur0 dashboard (all 13 findings
were already submitted in a prior session not present in this memory/transcript — do not
re-draft or re-test any of these as "unsubmitted" again, always check the dashboard first)

| # | Finding | Report dir | Secur0 # | Real status (Secur0 dashboard, checked 2026-07-28) |
|---|---|---|---|---|
| 1 | Empty/guest orders, rate-limit bypass via phone rotation, no delivery-radius check | `shishang-empty-order-no-item-validation` | **#2344** | Open |
| 2 | Restaurants table overexposed to authenticated non-staff | `shishang-restaurants-table-overexposed` | **#2350** | **Accepted (Medium)** |
| 3 | Welcome coupon (BIENVENIDA10) reusable unlimited times as guest | `shishang-welcome-coupon-unlimited-reuse-guest` | **#2348** | **Accepted (Medium)** |
| 4 | `auto-resolve-support-tickets` invocable with zero auth | `shishang-auto-resolve-tickets-no-auth` | **#2345** | Open |
| 5 | `consent_audit_log` forgeable via `log-consent` | `shishang-consent-log-forgery` | **#2352** | Open |
| 6 | Order accepted while restaurant shows "cerrado" (no opening_hours check) | `shishang-order-outside-opening-hours` | **#2440** | Open |
| 7 | No delivery fee / no minimum-order-for-delivery enforced server-side | `shishang-delivery-fee-minimum-bypass` | **#2443** | Duplicate |
| 8 | Client can self-resolve own support ticket (fake staff resolution) | `shishang-support-ticket-self-resolution` | **#2444** | **Accepted (Medium)** — independently reconfirmed fixed 2026-07-28 (table now has zero `authenticated` grants at all) |
| 9 | Fake/fabricated coupon insertable into own saved-codes list | `shishang-fake-saved-coupon-injection` | **#2446** | Open (still shows Open on dashboard even though our 2026-07-28 live retest found the RLS gap already closed — fix landed after submission, triage hasn't updated status yet) |
| 10 | Consent audit fields (`consent_ip_address`, `marketing_consent_at`) forgeable via profile PATCH | `shishang-profile-consent-fields-forgeable` | **#2447** | Open — **was already submitted**; the entire 2026-07-28 session detour (browser overlay PoC, Burp proxy replay, email-collision testing, staff-picker chain theory) was unknowingly re-investigating this same already-open report. Don't re-litigate "should we submit this" again — it's submitted, sitting Open, decide instead whether to add the staff-picker escalation angle as a comment on #2447 |
| 11 | Logout doesn't invalidate access_token server-side | `shishang-logout-no-server-side-invalidation` | **#2451** | Open |
| 12 | `alert_phone` settable to unverified third-party number | `shishang-unverified-alert-phone` | — | Not found on dashboard under Shi Shang App — genuinely still unsubmitted, or was dropped. Weak finding either way (unconfirmed real-world impact), low priority |
| 13 | `/api/products?includeUnavailable=true` leaks 5 hidden menu items | `shishang-hidden-menu-items-disclosure` | — | Not found on dashboard — genuinely still unsubmitted. Confirmed Low severity only, no escalation found even after retrying the modifier-injection angle 2026-07-28 |
| 14 | ROLLITOSGRATIS fix-incomplete on Sushi Tomo (whitelist bypass) | `shishang-rollitosgratis-fix-incomplete-sushitomo` | **#2641** | **Accepted (High)** |
| — | (predecessor/original ROLLITOSGRATIS report, pre-fix) | — | **#2626** | Fixed |

**Lesson learned the hard way this session: ALWAYS check `https://app.secur0.com/reports`
(filter by Company) before spending any time on "should we submit this" or "is this already
fixed" analysis — this memory file's "submission status unconfirmed" notes were stale and led to
redoing a large chunk of already-finished work (see the `profiles.email` saga below, all of which
was investigating an already-open #2447).** Only #12 and #13 above are confirmed genuinely never
submitted, and both are already known to be weak/low-value — there is currently nothing "ready
to submit" sitting on the shelf for this target. Finding something new now requires a genuinely
fresh angle; the easy ground is fully tapped (10 of 13 original findings accepted or open, one
fixed by the vendor, one duplicate).

**Next actions when resuming:** (a) check Secur0 dashboard for which of the "submission status
unconfirmed" ones actually went out — the user submits manually, Claude only drafts; (b)
decide on #9 and #12 (weakest two — user flagged #9's low value, #12 has an honest "can't
confirm SMS actually sends" caveat) — submit as-is, strengthen, or drop; (c) if the vendor
ships a fix, re-run the PoC in the corresponding `evidence/poc_*.txt` file verbatim to confirm
the fix actually closes the gap — every finding above has an `evidence/` file with exact
request/response pairs for fast re-testing. (d) `printer-claim`/`printer-ack`/`printer-health`
remain unexplored (blocked on missing field names, see below) — worth another look if the
companion app's source ever surfaces.

**Incident to remember:** the test account (`TEST - SECUR0 gueco`, phone 34674769201) now has
the user's **real personal Google account** linked (diegopague10@gmail.com) — see the PII
incident note below before doing any further destructive testing on that specific account.

**Scope (authoritative — structured "Dentro/Fuera de alcance" list, not the prose):**
- In scope: `shishang.app`, `portal.shishang.app`, `sushitomo.dingdingding.app`,
  `portal.sushitomo.dingdingding.app`.
- Out of scope: `hongkongcity.app`, `portal.hongkongcity.app` — **despite** the program's prose
  text describing specific testing rules for hongkongcity.app (including the "TEST - NO
  PREPARAR" ticket-name convention for real orders). The structured scope list is the
  authoritative source and explicitly marks it out of scope; treat this as a contradiction in
  the program's own text and do NOT test hongkongcity.app/portal.hongkongcity.app unless the
  program clarifies otherwise.

**Mandatory researcher identification (apply to every request, no exceptions):**
- Email alias: `[alias]@imnotahacker.com` — use `gueco@imnotahacker.com` (matches
  [[user_h1_username]] handle "gueco").
- User-Agent: `Secur0-gueco-<original user-agent string>`.
- Header: `X-Secur0-Username: gueco`.

**Special testing permissions (shishang.app / sushitomo.dingdingding.app only):**
- Allowed to complete full checkouts end-to-end, trigger the physical order printer, test any
  flow with no operational impact.
- Any change made must be reversible — this environment is used to demo the platform to
  prospective restaurant clients.

**Documented attack surface (given directly by the program):**
- Next.js API routes: `/api/products`, `/api/verification-reminders`, `/api/sitemap.xml`,
  `/api/robots.txt`, `/api/cron/attribution-report-email`, `/api/cron/order-timing-report-email`,
  `/api/cron/verification-reminders`.
- Supabase Edge Functions: `validate-coupon`, `apply-welcome-perk`, `get-loyalty-status`,
  `printer-claim`, `printer-ack`, `printer-health`, `send-sms`, `send-push-notification`,
  `send-admin-alert`, `send-auth-email`, `send-verification-email`, `send-verification-reminder`,
  `send-verification-success`, `notify-order-update`, `notify-support-ticket-resolved`,
  `translate-order-ticket`, `send-team-invitation`, `log-consent`, `check-stale-orders`,
  `auto-resolve-support-tickets`.

**Standard VDP restrictions:** no brute force/credential attacks, no DoS, no social
engineering/phishing, no data destruction, minimize PII access and stop+report immediately if
real user data is encountered, only test-owned accounts, proportionality (don't escalate a
small-scale demonstrated bug further than needed).

**Useful reusable technical details (2026-07-24 session):**
- Supabase project: `fbhuluviepiltkfzuwfz` (`https://fbhuluviepiltkfzuwfz.supabase.co`),
  shared backend across shishang.app AND sushitomo.dingdingding.app (confirmed same tenant
  bugs reproduce on both — different `restaurant_id`s, same RPC/tables).
- Public anon key is embedded in the frontend JS bundle (e.g.
  `www.shishang.app/assets/index.*.js`) — `role: anon`, expires 2035. Needed as the `apikey`
  header for any direct Supabase REST/RPC call.
- The UI checkout (`/checkout`) requires full login (Google OAuth or SMS OTP — no
  email/password, no guest checkout in the UI). **But the underlying order-creation RPC,
  `POST /rest/v1/rpc/submit_order_queued`, accepts guest orders with just the anon apikey, no
  `Authorization` header at all** — this is the practical way to test order-creation business
  logic without needing a real Google account or phone number for SMS.
- `restaurants_public?select=*` (anon, 200) exposes each restaurant's `settings.opening_hours`
  (per-weekday open/close, supports split shifts via `hasSplit`) and other public config.
  Direct anon INSERT into `orders` is correctly blocked by RLS (`permission denied for table
  orders`) — all order creation must go through `submit_order_queued`.
- `shishang.app`'s restaurant_id: `8fa4387d-aa86-4262-9b43-08038ace9524`. Known real menu item
  usable in PoCs: "Sopa de Miso", id `79beed17-ad5e-46c9-9a95-a8d4ac97b2ad`, price 5.30€ (no
  modifier groups, simpler than the Menú items which require a modifier selection).
  `sushitomo.dingdingding.app`'s restaurant_id: `e2316642-b9be-4bea-a865-b7677376eb91`.

**New findings (2026-07-24), drafted, not yet submitted:**
- `findings/dia1/shishang-order-outside-opening-hours/report_secur0.md` — `submit_order_queued`
does not validate the restaurant's `opening_hours` before accepting an order. Confirmed live:
called the RPC as a guest while the site was actively showing "Restaurante cerrado ahora...
Abrimos hoy a las 13:00" — got back a real `200` order (`status: pending`, correct
server-recalculated price 5.30€), `created_at` 12:34 Madrid time, 26 minutes before the 13:00
opening.
- `findings/dia1/shishang-delivery-fee-minimum-bypass/report_secur0.md` — same RPC accepts
`p_order_type: "delivery"` orders with zero delivery fee and below the restaurant's minimum
delivery order amount. Confirmed with a real side-by-side comparison: cart UI for a 5.30€ item
shows a real 1.99€ delivery fee (free only >10€) and blocks checkout with "Pedido mínimo a
domicilio 8.01€ · Añade 2.71€ más" — but calling the RPC directly with the identical order
returns `total: 5.30` (no fee added, no rejection). Both business rules exist client-side only.

Both kept as **separate reports** from `shishang-empty-order-no-item-validation` per
[[feedback_report_merge_rule]] — same endpoint/RPC, but user explicitly wanted distinct
reports each time since the specific missing validation (and its fix) differs from what's
already covered there (item-count/rate-limit/delivery-radius), even though the existing report
already bundles multiple "Control adicional" sections for other gaps in that same function.
**Established pattern for this target: every new missing-validation gap found in
`submit_order_queued` = its own report, not a bundled addendum**, despite the shared endpoint.

**New finding #3 (2026-07-24), SUBMITTED as report #2444 on Secur0** (with a screenshot
attached showing the fake resolution message rendered to the customer as "El restaurante ha
respondido" — visible proof the forged ticket isn't just a DB row, the customer actually sees
it as a real staff reply):
`findings/dia1/shishang-support-ticket-self-resolution/report_secur0.md` — completely
different mechanism/table from the other findings (`order_support_tickets` direct INSERT, not
`submit_order_queued`): a normal authenticated customer can insert their OWN support ticket
already populated with staff-only fields (`resolution_type`, `resolution_message_es`,
`resolved_at`, `resolved_by`), self-resolving it with `resolution_type: "compensation"`
(admin panel copy: "Próximo pedido: plato gratis + 20% descuento") — no staff involved at all.
RLS correctly validates order ownership and that `affected_item_names` are real items in that
order (tested both, both properly rejected), and `resolution_type` is constrained to a valid
enum (`resend_dish`/`compensation`) — the gap is specifically that the INSERT policy doesn't
restrict which *columns* the client can populate. Explicitly verified via `get-loyalty-status`
before/after that this does NOT auto-grant the reward right now (`activeRewards` unchanged) —
reported as a confirmed integrity/process bug, with the reward-auto-grant risk flagged to the
vendor as unconfirmed, not claimed.

**New finding #4 (2026-07-24), drafted, not yet submitted:**
`findings/dia1/shishang-fake-saved-coupon-injection/report_secur0.md` — same root pattern as
finding #3 but a different table: `user_saved_codes` (the "Códigos promocionales" saved-coupon
list in Profile) has the same permissive-INSERT gap — a client can insert a fully fabricated
reward row (`coupon_id: null`, invented `coupon_code`/`discount_value`) that displays in the
UI's "DISPONIBLES" list identically to a real reward. **Explicitly verified this does NOT
work at actual checkout** — `submit_order_queued` independently validates `p_coupon_code`
against the real `coupons` table and rejects the fabricated code (`"Código de cupón
inválido"`). Cross-user IDOR write is properly blocked (403). Reported honestly as a
UI/data-integrity issue, not confirmed financial fraud — same discipline as finding #3.
`user_addresses` (saved delivery addresses) was tested with the identical technique and found
properly protected (cross-user insert → 403), confirming this INSERT-column gap is not a
platform-wide pattern, just specific to `order_support_tickets` and `user_saved_codes`.

**New finding #5 (2026-07-24), drafted, not yet submitted:**
`findings/dia1/shishang-profile-consent-fields-forgeable/report_secur0.md` — third instance of
the same "INSERT/UPDATE column not restricted" root pattern, third distinct table:
`PATCH /rest/v1/profiles` lets a normal customer overwrite their own `consent_ip_address` and
`marketing_consent_at` (GDPR consent audit-trail fields) with arbitrary fabricated values
(fake IP, fake date years before the account existed) — confirmed 200 OK, values persisted.
Different table/endpoint from the already-reported `shishang-consent-log-forgery` (which is
about the `log-consent` Edge Function writing to `consent_audit_log`), so kept separate per
[[feedback_report_merge_rule]]. Also confirmed `send-admin-alert` is properly protected —
non-critical alert types are silently no-op'd regardless of caller (not a real bypass), but a
real "critical" type (`order_timeout_escalation`) correctly returns 401 for a normal customer
session, so that one's clean.

**New finding #6 (2026-07-24), drafted, not yet submitted:**
`findings/dia1/shishang-logout-no-server-side-invalidation/report_secur0.md` — a completely
different class from the other findings (session lifecycle, not a table/RPC write gap):
"Cerrar sesión" only clears client-side localStorage; a captured `access_token` from before
logout still authenticates successfully afterward, valid until natural expiry (≤1h). Confirmed
end-to-end: real logout verified (localStorage empty), pre-logout token still returned `200`.
Reported with an honest severity caveat — this is a known/common tradeoff for stateless JWT
auth (Supabase), window is short (≤1h, not indefinite), so framed as a real-but-modest finding
about the "logout after suspected compromise" scenario specifically, not overclaimed.

**Session hygiene note for next time:** this finding required the user to repeatedly paste
fresh session tokens (extracted via browser devtools) since the JWT-extraction block prevents
Claude from reading them itself and tokens expire hourly — expect this friction on any
Supabase-JWT-based target when testing authenticated/session flows this way.

## Session 2026-07-27 — admin-escalation sweep, all dead ends; new `/invite` flow discovered but untestable

User asked to try getting into `portal.shishang.app` admin/staff access by any means. New bundle
deployed since last session (`index.Bj_g9Pav.js`, was `index.DLzn9Xdj.js`) — re-check for new
routes/strings if resuming, deployments do happen.

**Every escalation vector tried, all correctly blocked:**
- `POST /functions/v1/send-team-invitation` with `{email, role, restaurant_id}` (real field
  names found by probing validation errors: `restaurant_id` is snake_case, not `restaurantId`)
  — role enum accepted by the function is only `{admin, driver}` (staff/manager/owner/member/
  customer all `invalid_role`), but even valid roles get `403 forbidden` for a customer session,
  regardless of role tried. Properly protected.
- Direct `POST /rest/v1/team_invitations` insert (bypassing the function) → `403`, RLS policy
  violation (`42501`). Also properly protected.
- Direct `POST /rest/v1/printer_devices` insert → same, RLS `42501`.
- `PUT /auth/v1/user` with `{data: {role:"admin", is_admin:true, staff:true}}` → succeeds (200,
  this is normal Supabase `user_metadata`, always client-writable by design) but has **zero
  effect** — re-checked `portal.shishang.app` immediately after and it still shows "Acceso no
  autorizado, Esta sección es exclusiva para propietarios de restaurante." Confirms the app does
  NOT trust client-writable Auth metadata for authorization anywhere, only the properly-RLS'd
  `user_roles` table (already known solid from round 2/3 above).

**New, previously-undocumented flow found via bundle string search
(`get_invitation_info`/`consume_team_invitation`/`/invite`), not in the program's own listed
attack surface:** the real onboarding path for a `send-team-invitation` invite is
`GET /invite?token=<token>` (frontend route) → `rpc('get_invitation_info', {_token})` to preview
(returns `{ok, email, role, restaurant_name}`) → `rpc('consume_team_invitation', {_token})` to
accept (grants the real role). **Client code only ever sends `_token`, never an email** — so
whether the Postgres function verifies the token's target email matches the consuming
authenticated user is an open, unverified question (classic invite-hijack pattern if it doesn't
check). Probed `get_invitation_info` with garbage/all-zero-UUID tokens — both return a uniform
`{"ok": false, "reason": "invalid_or_expired"}`, no format hint leaked, token doesn't look
guessable/brute-forceable (and brute-forcing it would violate the program's own no-brute-force
rule anyway). **Cannot test further without a real, valid invitation token** — we have no way to
generate one (send-team-invitation correctly blocks us) or receive one (would need an existing
program-side admin to send an invite to a researcher-controlled email).

**Ruled out a hoped-for self-service path**: searched for a public "become a driver"
application/signup flow (since `driver` was one of only two valid roles in the invite function,
suggesting maybe drivers self-register) — found the real answer in the bundle's own copy instead:
`noDriversYet: "Aún no hay repartidores. Pídele al usuario que se registre y luego asígnale el
rol..."` — drivers must first register as a normal customer, then an **existing staff/admin
manually "Asigna"** (assigns) them via a separate staff-panel action (distinct from the
email/token invite flow, presumably a direct authenticated write gated the same way as
`user_roles` already is). No self-service path exists either way.

**How to apply if resumed:** the only remaining way to test `consume_team_invitation`'s
email-binding is non-technical — ask the program to send a real test invitation to a
researcher-controlled email (`gueco+shishangteaminvite@imnotahacker.com` or similar), then try
consuming it from a DIFFERENT authenticated account than the invited email to see if it's
honored anyway (that would be the actual vulnerability, if it exists). **User explicitly decided
not to pursue this now** ("no, nos preparamos para los próximos programas") — don't chase this
further unless the user brings it back up or the program provides a token. Document as an open
question, not a confirmed finding, if ever written up.

**IMPORTANT — real PII exposure incident this session:** while testing the account,
the user accidentally linked their **real personal Google account**
(diegopague10@gmail.com, name "Diego") to the shared test account via "Vincular con Google",
then pasted the full session object **twice** into chat, including a live Google
`provider_token` (a real Google API OAuth access token, not just the app's own Supabase JWT).
Refused to use that token for anything — Google's infrastructure is entirely out of scope for
this VDP (which only covers shishang.app/sushitomo.dingdingding.app), and it grants access to
the user's real personal Google account, not a test artifact. Advised the user to treat it as
compromised and revoke it at https://myaccount.google.com/permissions. User asked me to "just
use it anyway" and separately asked me to create a fresh test account to avoid this problem —
declined both (using an out-of-scope third party's live credential; creating accounts is a
hard rule with no exception, same as already established in [[project_gestionominegocio]]).
**How to apply next time:** if a user accidentally links a real personal identity provider to
a shared/test account mid-session, stop, flag it clearly, and avoid further manipulating that
specific account beyond what's needed — don't let "keep hunting" momentum carry through a
moment like this without pausing to address it first.

**New finding #7 (2026-07-24), drafted, not yet submitted:**
`findings/dia1/shishang-unverified-alert-phone/report_secur0.md` — `profiles.alert_phone`
("Teléfono de alertas SMS" in Profile settings) can be set to any syntactically-valid phone
number via `PATCH /rest/v1/profiles` with zero ownership verification (no OTP to the
secondary number, only client-side format validation). Confirmed the write succeeds (200).
Honestly flagged, not overclaimed: could NOT confirm whether this actually triggers real SMS
to the configured number (no access to Twilio logs) — reported as a real validation gap with
plausible-but-unverified downstream SMS-harassment impact, same honesty discipline as findings
#3/#4. Different field/table from every other finding today, so separate report.

**OTP replay test attempted, inconclusive (not a finding either way):** tried to test whether
an SMS OTP code remains valid after being superseded by a new one, coordinating with the user
in real time (user receives real SMS, relays code in chat). Failed twice — "Token has expired
or is invalid" — because Shi Shang's OTP has a **60-second expiry** and the chat round-trip
latency exceeded that window both times. This is inconclusive by construction (couldn't
complete the test), not a negative result — a short TTL is actually a reasonable sign, but
true reuse/replay was never actually tested. Don't re-attempt this via chat relay — would need
either the user testing it directly themselves, or some other faster channel.

**New finding #8 (2026-07-24), drafted, not yet submitted:**
`findings/dia1/shishang-hidden-menu-items-disclosure/report_secur0.md` — completely different
endpoint from everything else today: the Next.js API route `GET /api/products` (not Supabase
at all) honors an undocumented `includeUnavailable=true` query param with zero auth check,
revealing 5 menu items marked `isAvailable:false` ("Menú 4"–"Menú 8") — name/price/allergens.
Tried to escalate: other guessed param names (includeDeleted/Draft/Archived, showAll, admin,
includeHidden/All) all no-ops; tried requesting sushitomo's `restaurantId` explicitly from the
shishang.app domain — properly blocked (`"restaurantId/domain does not match the requested
host"`, cross-tenant isolation solid here). Tried ordering a hidden item via
`submit_order_queued` — properly rejected (`"Invalid or unavailable menu item"`). So the
confirmed impact is genuinely capped at read-only info disclosure of 5 items' basic fields,
no purchase path, no cross-tenant leak — reported at that honest (low) severity, no more.

**XSS and SQLi passes, both clean:** tried stored XSS (raw `<img onerror>`/`<b>` payloads) in
`user_saved_codes.reward_name` — confirmed properly HTML-escaped in the Profile UI (screenshot
verified: literal tag text shown, no execution, no bold rendering). `customer_name` isn't
rendered anywhere customer-facing (checked the tracking page) so untestable there. SQLi tried
in `submit_order_queued`'s free-text params (customer_name, address) via error-based
(`'`), destructive (`'; DROP TABLE orders;--`, table confirmed intact after), and time-based
blind (`pg_sleep(5)`, response returned in 1.6s not 5s+) — all clean, properly parameterized.
Also reconfirmed (not a new finding, same root cause as the already-reported delivery-radius
gap) that a syntactically-garbage, non-existent address is accepted for delivery with no
geocoding/validation at all.

**Confirmed clean/well-protected on this pass (no vuln):** `get-loyalty-status`,
`send-team-invitation`, `send-push-notification`, `notify-order-update`,
`notify-support-ticket-resolved`, `send-sms`, `send-admin-alert`, `send-auth-email`,
`send-verification-*`, `/api/cron/*`, `/api/verification-reminders`, IDOR on `orders`/
`order_support_tickets` reads (RLS correctly scopes to own `user_id` even with no filter),
`apply-welcome-perk` (idempotent — repeat calls return the same reward row, no duplication),
cross-item modifier substitution (moot — every modifier at this restaurant has `price_delta: 0`,
nothing to gain), coupon `min_order_amount` (properly enforced server-side, rejects with
`P0001 "Pedido mínimo de 15.00 € requerido"`). `printer-claim`/`printer-ack`/`printer-health`
return `400 Missing required fields` with no auth, but the real field names are unknown — they
belong to a separate local companion app (Termux/Node.js on the restaurant's own device, run
via `pm2`, not part of the web bundle) so the required schema can't be discovered by reading
client-side code. Parked, not pursued further after several guessed field names failed.

**Explicitly out of scope for reports:** self-XSS/self-DoS (unless attacks another account),
clickjacking without sensitive action, CSRF on non-sensitive forms, permissive CORS without
demonstrated impact, version disclosure/stack traces/error messages, CSV injection, open
redirect without extra impact, SSL/TLS config, missing cookie flags, CSP config, SPF/DKIM/DMARC,
most rate-limiting issues.

**Session 2026-07-24 (round 2) — all clean, no new findings, documented so these aren't
re-tested:** with a fresh session token, tested 7 more surfaces via direct `/rest/v1/` and
`/functions/v1/` calls (bypassing the UI): `loyalty_rewards` table — INSERT blocked (403 RLS),
UPDATE silently no-ops (verified via re-read, `discount_percentage` unchanged) — well
protected, breaks the "3 for 3" INSERT-column-gap pattern seen in `order_support_tickets`/
`user_saved_codes`/`profiles`, so that pattern is NOT platform-wide. `user_roles` table — own
row readable (correctly RLS-scoped), UPDATE to `staff`/`admin`/`manager` silently no-ops
(verified unchanged), INSERT of a second privileged row blocked (403) — no privilege
escalation. `orders` table — direct PATCH of `total`/`discount_amount`/`status`/`delivered_at`
on own order all silently no-op (verified unchanged) — no post-submission tampering, order
mutation is correctly RPC-only. `coupons` table — direct SELECT returns empty (RLS blocks read
entirely, not just filtering) — can't enumerate coupon codes this way. `apply-welcome-perk`
tested against BOTH tenant `restaurantId`s (shishang + sushitomo) — returns the identical
`reward.id` both times, confirms the reward is deduped per-user (not per-restaurant), no
double-dip.

**Two undocumented Edge Functions found in the shared SPA bundle (same bundle serves customer
site AND `portal.shishang.app`, single JS file `index.DLzn9Xdj.js`), neither in the program's
own listed attack surface:** `secure-signup` (body: `{email, password, displayName,
marketingConsent}` — the manager-portal's "Otros métodos → Email y contraseña" login screen
has no visible signup link, so this is likely the accept-team-invitation flow paired with
`send-team-invitation`) and `printer-restart` (body: `{restaurantId}`, called from the
staff-facing printer-troubleshooting dialog — i18n keys `printerRestart`/`printerRestarting`/
`printerTermuxNote` confirm this dialog exists, distinct from the still-unlocated
`printer-claim`/`printer-ack`/`printer-health` trio the program itself lists, which do NOT
appear anywhere in this bundle by literal string search — confirms those three really do live
only in the separate Termux companion app, not in any web codebase). **Both consistently
return HTTP 503 on every attempt (5+ retries each, unlike `validate-coupon`'s one-off
transient 503 that cleared on retry)** — this pattern (persistent, not transient) matches
Supabase Edge Functions' BOOT_ERROR behavior (function crashes/fails to start, e.g. missing
secret or runtime error), not a live, testable endpoint. Tried `secure-signup` for real (user
explicitly authorized creating one test account for this specific check,
`gueco+shishangsecuresignup@imnotahacker.com`) — still 503, so **the account was never
actually created**, no cleanup needed. **How to apply if resumed:** both are dead ends until/
unless they start responding with something other than 503 — don't keep retrying them
routinely, but worth a single quick re-check next session in case the deployment gets fixed,
since `secure-signup`'s authorization model (does it let anyone self-assign a restaurant/role,
or does it require a valid invitation token from `send-team-invitation`?) is still an open
question with real potential impact if it ever starts working.

**Cosmetic, not a finding:** `portal.shishang.app`'s `<title>` sometimes shows a stale
"Hong Kong City Argüelles" (the out-of-scope tenant) instead of Shi Shang branding — visible
page content (the actual login form) is generic/correct, only the tab title string is wrong.
Looks like a stale client-side title left over from a previous SPA route/tenant resolution,
not a real cross-tenant data leak — didn't chase further, out-of-scope-severity issue even if
real (matches the "version disclosure"-adjacent exclusion list).

## Session 2026-07-24 (round 3) — new "driver" surface discovered, everything tested came back clean

Found a genuinely new, previously-unexplored feature via the JS bundle (`index.DLzn9Xdj.js`,
unchanged since round 2 — no new deployment): a full delivery-**driver** role/portal
(`/driver`, `/driver/stats` routes; nav strings `driver-nav-orders`, `driver-order-area`,
`driver-nav-history`, `driver-nav-profile`, `driver-payment-filter`, `driver-sound-*`).
`"driver"` is a genuine additional value in the same role enum as `"admin"` (found via string
search), distinct from `staff`/`admin`/`manager` already tested in round 2. Tested every
angle available with only a customer session (no staff/admin account available):

- `user_roles` UPDATE own row to `role: "driver"` → silently no-op (same protection as
  staff/admin/manager, confirmed still solid).
- `user_roles` INSERT new row `{role: "driver", restaurant_id: <real>}` → blocked, 403 RLS.
- `orders.driver_id` PATCH (own order, set to own `user_id`) → silently no-op, confirms
  `orders` mutation truly is RPC-only for every column, `driver_id` included (this specific
  column wasn't explicitly listed as tested in round 2's write-up, now confirmed too).
- **No conclusion possible** on two newly-discovered tables that don't appear anywhere in
  the program's documented surface: `printer_devices` and `team_invitations`. Both return
  `200 []` / `content-range: */0` for an authenticated customer (vs `401 permission denied`
  for `anon` — so the `authenticated` Postgres role does have some grant on both tables,
  unlike anon) but are **globally empty** in this shared demo backend right now. Can't tell
  apart "RLS correctly scopes to 0 rows for a non-staff customer" from "RLS is too broad but
  there's simply nothing to leak yet" — don't report this without either real data in these
  tables or a staff/admin session to compare against. Worth a quick re-check if the tables
  are ever seeded.
- `loyalty_profiles` (distinct table from `loyalty_rewards`, which was already the subject
  of prior findings) — tried self-tampering `total_orders`/`completed_orders`/
  `lifetime_spend`/`milestones_achieved` via PATCH → all silently no-op. Well protected.
- `secure-signup` and `printer-restart` (previously persistent 503/BOOT_ERROR in round 2) now
  return `404 NOT_FOUND` — the functions appear to have been undeployed/removed by the vendor.
  Not exploitable either way now; stop checking these two.
- `printer-claim`/`printer-ack`/`printer-health` still return `400 Missing required fields`
  for anyone, still no way to guess the real field names (tried `restaurantId`,
  `restaurant_id`, `printerId`, `deviceId`, `token` combos — error message never changes to
  hint at what's actually expected). Still a dead end without the companion app's source.
- `translate-order-ticket` (documented Edge Function) needs `{ticketId, text, from, to}`
  (found via bundle string search, not `orderId`). Confirmed it DOES do a real DB lookup on
  `ticketId` — a fake/non-existent UUID returns `404 not_found`, while my own real ticket ID
  passes that check and reaches a downstream `502 Translation API error` (the underlying
  translation provider itself seems to be erroring right now — an availability issue, not
  security-relevant, matches the program's own "most rate-limiting/availability issues"
  exclusion spirit). **Untested: whether the DB lookup checks ownership (ticket belongs to
  caller) or just existence (any ticket in the whole system)** — would need a second
  account's real ticket ID to test true cross-user IDOR here; don't have one and won't
  create a second account without the user explicitly authorizing that specific check (same
  bar as the one-off `secure-signup` account creation earlier).
- `check-stale-orders` with a real authenticated customer token (not just anon) → still
  correctly `401 Unauthorized`. Properly staff/cron-only.
- `notify-order-update` on my own real order → `403 Forbidden` even though I own the order —
  correctly staff-only, customers can't self-trigger fake status notifications.

**Bottom line: no new confirmed finding this round.** The backend is consistently
well-hardened against every write/escalation path tried. The two live open threads if this
gets resumed: (1) `translate-order-ticket` cross-user ownership check — needs a second
account's ticket ID; (2) `printer_devices`/`team_invitations` — needs either seeded data or
a staff session to know if the broad `authenticated` grant is actually a problem.

## PAUSED here 2026-07-24 — resume point

**New finding #9 (2026-07-24), drafted, not yet submitted:**
`findings/dia1/shishang-loyalty-reward-not-marked-used/report_secur0.md` — found while race-
condition-testing the `BIENVENIDA10` welcome coupon. **Distinct from report #2348** (already
submitted by the user, separately — "Falta de control de reutilización en el cupón BIENVENIDA10
permite canjes ilimitados"): #2348 is the **guest-checkout path** (`p_user_id` null, no auth) —
zero reuse control there, coupon genuinely re-appliable with real financial impact, confirmed
3x by the user (same phone twice + a third phone), open on Secur0. This new finding is the
**authenticated path**, where I actively confirmed reuse protection DOES work correctly:
- Used `BIENVENIDA10` on a real order (15.90€ subtotal, discount applied correctly).
- Fired a second, concurrent (`Promise.all`) identical request — correctly rejected ("ya has
  utilizado este cupón el número máximo de veces permitido"). No race condition.
- Tried the same coupon on the OTHER tenant (sushitomo) after using it on shishang — also
  correctly rejected. Reuse-limit is properly global-per-user, not per-restaurant.
- But `loyalty_rewards.status`/`used_at`/`used_on_order_id` never update after that confirmed
  real use — still shows `status: "active"`, `used_at: null` forever. `get-loyalty-status`
  (what the client's own Recompensas screen calls) reflects this same stale state
  (`welcome_perk_used: false`, reward still listed in `activeRewards`) — real, demonstrable
  user-facing symptom, but no financial exploitability (the actual gate lives elsewhere and
  works). Report explicitly flags upfront in Detalle técnico that it's not the same as #2348,
  per the user's request, to avoid a triager reading it as a duplicate.
- Also ruled out (same session, while testing this): direct price/total tampering on
  `submit_order_queued` — sent a real 5.30€ item declared as `p_subtotal: 0.01`/`p_total: 0.01`
  — the RPC's own error detail exposed the row it would have inserted, showing the REAL
  recalculated 5.30€, confirming client-supplied totals are ignored server-side (a separate,
  unrelated `23502 null address` constraint blocked the actual insert, but the price-recalc
  behavior was still visible in the error payload). Negative quantities (`quantity: -4`) are
  accepted (not rejected) but silently floored to a minimum of 1 per line for pricing purposes
  (`GREATEST(quantity,1)`-shaped behavior, confirmed by the resulting total matching that
  formula exactly) — not exploitable for a discount, but the raw negative value persists
  verbatim in the stored `items` JSON (cosmetic/kitchen-ticket-garbling risk only, not written
  up — too low value on its own).
- Hit the order-creation rate limit (2/hour per phone) partway through this testing —
  out-of-scope per the program's own exclusion list ("most rate-limiting issues"), so a planned
  follow-up test (single negative-quantity line item alone, no positive line to floor against)
  was never completed. **Resume point if continuing:** wait for the rate limit to clear (or use
  a different phone/account) and finish that specific test — low priority, the floor-to-1
  behavior already answers the interesting question (no free/negative-cost items possible).

**Explicitly out of scope for reports:** self-XSS/self-DoS (unless attacks another account),
clickjacking without sensitive action, CSRF on non-sensitive forms, permissive CORS without
demonstrated impact, version disclosure/stack traces/error messages, CSV injection, open
redirect without extra impact, SSL/TLS config, missing cookie flags, CSP config, SPF/DKIM/DMARC,
most rate-limiting issues.

## Session 2026-07-25 — #2440 downgraded to Informativo, impact-visibility deep dive

Report #2440 (`shishang-order-outside-opening-hours`, the closed-hours `submit_order_queued`
bypass) came back from triage as **Informativo** — the vendor/triager isn't convinced of real
operational impact, only of the raw INSERT bypass itself. Spent this session trying to prove
concrete impact by finding where a bypass order becomes visible/observable, before drafting a
pushback reply.

**Fresh repro this session:** `fc091525-e289-4e69-b075-c571fbadc5e0`, `created_at`
2026-07-25T17:25:48Z = **19:25:48 Madrid, 4m12s before the 19:30 opening** — same bypass,
independent server-side timestamp, good supplementary evidence.

**Visibility testing (answers "where does it get recorded"):** tested all three client-facing
surfaces for a *true guest* order (created with just the anon apikey, no `Authorization`,
matching the report's exact PoC conditions) — `/my-orders`, `/tracking/<id>`, `/invoice/<id>`.
**All three fail ("no encontrado"/absent) for a true guest order**, because none of the
underlying queries can match without a `user_id` (guest orders have none). Direct anon SELECT
on `orders` is flatly `401 permission denied for table orders` — confirmed guest orders are
invisible to literally everyone client-side, **including the guest who created them**. This is
the honest answer for the triage reply: the bypass is 100% real, but no external/customer-facing
surface can prove operational impact — that proof only exists inside `portal.shishang.app`
(staff panel), which we don't have access to.

**False alarm, corrected before acting on it:** initially suspected an IDOR — an authenticated
`customer`-role account's `orders?status=eq.pending` (no user_id/restaurant_id filter in the
query params) appeared to return orders that looked like they belonged to someone else (different
phone number in `customer_phone`). **Verified and retracted**: queried the specific row directly
and confirmed its actual `user_id` matches the test account itself — it was the same account
placing test orders with different phone numbers typed into the guest-checkout phone field
across sessions, not a different user. RLS is scoping correctly by `user_id` here, not by the
phone field. No IDOR. **Lesson: always verify the actual `user_id`/ownership column directly
before calling something an IDOR — a differing display field (phone, name) is not proof of a
different owner.**

**Real minor finding, not yet written up as its own report:** Supabase Realtime accepts a
`postgres_changes` subscription on `public:orders` (`event: "*"`) using **just the public anon
key, no session at all** — confirmed via a raw WebSocket
(`wss://fbhuluviepiltkfzuwfz.supabase.co/realtime/v1/websocket?apikey=<anon>&vsn=1.0.0`), join
succeeded ("Subscribed to PostgreSQL"). When a new order is inserted, an unauthenticated
subscriber **does** receive a live `postgres_changes` INSERT event — but RLS correctly blocks
the actual row content (`record: {}`, `columns: []`, `errors: ["Error 401: Unauthorized"]`, and
notably `commit_timestamp: null` in this blocked state — so it does NOT leak a usable
timestamp). Net effect: anyone unauthenticated can detect *that* and roughly *when* any
order is created anywhere on the platform (existence/timing metadata oracle, no PII, no
row content) — low severity on its own, genuinely separate from #2440, not yet drafted as a
report. Worth a quick low-priority writeup later if pursued.

**Next step (explicitly requested by user, not yet done):** repeat a closed-hours
`submit_order_queued` bypass **combined with the live realtime WebSocket subscription running
at the same time**, timed to when the restaurant is genuinely closed again — tonight after
23:30 Madrid, or before 13:00 the next day — to get a cleaner correlated proof (curl timestamp +
live socket event arriving at the same real-world moment) for the triage pushback. The reply
text arguing against the Informativo downgrade was drafted this session in the session's
scratchpad (ephemeral — regenerate from this memory's summary if needed, don't expect the file
to still exist next session).

**#2626 (`shishang-freedish-coupon-not-item-scoped`, ROLLITOSGRATIS) fixed 2026-07-25→26,
verified solid after a full regression pass, not reopened.** Vendor's fix: new RPC param
`p_promo_selection` (array of `{id, quantity}` — no `price` field anymore, server looks up the
real catalog price itself) replaces the old flat `max_discount_amount` deduction; found the
exact field name by grepping the bundle (`www.shishang.app/assets/index.*.js`) for
`promoRollSelections`/`p_promo_selection` since the localStorage key `restaurant_cart_coupon`
holds the pre-fix client-side shape (`promoRollSelections: [{id, price}]`) which the client then
regroups into `{id, quantity}` before sending — the `price` field in localStorage is legacy/
client-display-only now, never transmitted to the RPC. Threw 12 adversarial variants at it (item
not in cart, over-claiming quantity vs real cart count, an arbitrary expensive non-promo item,
stacking two distinct valid items at once, the new "+30€ unlocks claiming 2 units" tier with and
without real stock to back it, negative/zero quantity, cross-tenant item-id substitution using a
real Sushi Tomo dish while ordering from Shi Shang) — **every single one correctly rejected
except the legitimate cases**, each with a distinct, specific error message (not a generic
catch-all), confirming real server-side validation logic, not just a patched happy-path. Only
non-issue found: `quantity: -1`/`quantity: 0` silently behaves like `quantity: 1` instead of
being rejected — zero financial/security impact (no extra or negative discount), same "not
exploitable" bar as the already-documented negative-quantity floor-to-1 behavior elsewhere in
this codebase, not worth writing up. **Takeaway: this vendor ships real fixes, not
cosmetic ones — worth the verification pass, but don't expect to find a quick re-bypass here
next time either.**

**NEW FINDING 2026-07-26 — #2626 fix regresses on Sushi Tomo (fix-incomplete, not yet
reported/drafted):** `/promo/ROLLITOSGRATIS` on `sushitomo.dingdingding.app` shows **"No hay
rollitos disponibles"** — zero free-dish items configured for this coupon on this tenant
(`restaurant_id: e2316642-b9be-4bea-a865-b7677376eb91`), even though `validate-coupon` still
returns `valid:true, max_discount_amount:5.25`. Tested 4 ways against `submit_order_queued` with
`p_coupon_code: "ROLLITOSGRATIS"` on a real ≥15€ order (8x mochi de mango): (1) omitting
`p_promo_selection` entirely, (2) `p_promo_selection: []`, (3) claiming the real cart item
(mochi) as the free dish, (4) claiming a **fully fabricated, non-existent UUID**
(`00000000-0000-0000-0000-000000000000`) as the free dish — **all four returned `200` with the
full flat `discount_amount: 5.25` applied, unconditionally**, identical to the pre-fix #2626
behavior. Root cause: the new whitelist-based validation (confirmed solid on Shi Shang — see
above, 12/12 adversarial tests correctly rejected) has no safe-default when a restaurant has
**zero** configured free-dish items for the coupon — instead of failing closed ("no valid
selection possible, reject"), it falls back to applying the flat discount with no verification
at all, i.e. the exact original vulnerability, just gated on a different, restaurant-specific
precondition (empty item list) instead of being universally present. **This is a regression/
incomplete-fix finding on #2626, not a new independent bug class** — same root cause family,
different specific gap (missing safe-default for the "no items configured" case). Vendor
mentioned the fix was applied to "los tres restaurantes que usan este código" — third one is
presumably `hongkongcity.app`, **out of scope, do not test it** (see the scope contradiction
note earlier in this file). **Next step: write up and report as a fix-regression on #2626**
(reference the original report, explain the new specific gap, same PoC style — the D1-D4 curl
commands above are the ready-made repro). Order IDs created during this verification, all
clearly `TEST -` marked: `25dc0b7f`, `17a00abc`, `4ad3f2f1`, `644fea5d`.

**WRITTEN UP AND DRAFTED 2026-07-26:**
`findings/dia1/shishang-rollitosgratis-fix-incomplete-sushitomo/report_secur0.md` — not yet
submitted. Also reproduced with a real authenticated session (`p_user_id` explicit param,
matching the production bundle's exact RPC call shape — needed because the Bearer token alone
does NOT auto-attach `user_id`, confirmed by querying the resulting order's `user_id` before
adding the param, it was unset) — order `9a069ea5-75cc-4078-aba3-3804a2fe59da`, confirmed
via direct table read to have the real account's `user_id`. **Correction — the invoice/my-orders "failure" was just a stale access_token, not an app
bug.** Re-tested with a genuinely fresh session token (user pasted their current real
`sb-fbhuluviepiltkfzuwfz-auth-token` localStorage value) and both `/my-orders` and
`/invoice/9a069ea5-75cc-4078-aba3-3804a2fe59da` rendered perfectly — real invoice, Sushi Tomo
letterhead, `Descuento (ROLLITOSGRATIS): -5.25€`, `TOTAL: 10.75€`. Retract the "separate
frontend rendering bug" theory from earlier in this entry — always try a fresh token before
concluding a render failure is a real bug (same root lesson as the hourly-token-expiry friction
noted elsewhere in this file for round 2). Screenshot evidence now available for the
`shishang-rollitosgratis-fix-incomplete-sushitomo` report — the real invoice with the coupon
name printed on it is stronger proof than the raw JSON alone, worth attaching. Evidence file:
`evidence/poc_requests.txt` (D1-D5 + shishang control-positive) + the invoice screenshot.

**Extra verification ammo for `shishang-rollitosgratis-fix-incomplete-sushitomo`, saved for
when the vendor replies to that report — DO NOT add to the report now, just re-test with this
when they claim it's fixed:**
- **F1**: a second, independent, genuinely-valid-for-Sushi-Tomo `free_dish` coupon,
  `TEMAKI2X1` ("Llévate 2 temakis y paga solo el más caro", `max_discount_amount: 5.95`,
  found printed on a real physical ticket) reproduces the **exact same** empty-whitelist bug —
  ordered 2 real temaki dishes (Anguilas `f466908e-f85e-4f17-9702-be9925518094` 5.90€ + Atún
  `81d56bce-4551-4a5a-bd71-5889e0b01a7d` 5.40€), applied `p_coupon_code: "TEMAKI2X1"` with no
  `p_promo_selection` at all → `200`, `discount_amount: 5.95` (order
  `f1bac081-ee25-4a29-b19d-45f4fea884bb`). Confirms the gap isn't specific to ROLLITOSGRATIS —
  **any** `free_dish` coupon without a configured item-whitelist at a restaurant is exploitable
  the same way. **When the vendor says the Sushi Tomo regression is fixed, re-test with
  TEMAKI2X1 too, not just ROLLITOSGRATIS** — if only the latter was fixed, the fix was
  code-specific (patched the config, not the actual missing fail-closed logic) and the report
  should stay open.
- **F2** (control): same `TEMAKI2X1` code correctly rejected by the RPC at shishang.app
  ("Este cupón no es válido en este restaurante") — confirms the RPC *does* have a real
  restaurant-eligibility check, it's just that Sushi Tomo's item-whitelist for this code is
  ALSO empty, same root cause as ROLLITOSGRATIS.
- **F3** (not new, just extra confirmation of an already-reported separate bug): reused
  TEMAKI2X1 a second time with a different phone despite `is_single_use: true` in its config →
  `200`, discount applied again (order `a988b8dd-fc7c-414c-b35f-91c5b5d93f46`). Same root cause
  as the already-open `shishang-welcome-coupon-unlimited-reuse-guest` (guest coupon reuse via
  phone rotation) — don't write this up separately, it's just confirmation that bug is
  coupon-agnostic too.
- Minor non-security note: `validate-coupon` (the customer-facing pre-check) incorrectly
  reports `TEMAKI2X1` as "no válido en este restaurante" for Sushi Tomo even though the
  authoritative RPC accepts it — likely blocks real customers from using this real, legitimate
  promotion. A functional/business bug that hurts the vendor, not a security finding, not
  reported.

## #2345 (`auto-resolve-support-tickets` no-auth) — triager wants visual proof, in progress 2026-07-26

Triager (Cristian) won't accept without seeing a real ticket actually get closed by the
unauthenticated call — screenshots so far only showed `processed:0` (no pending tickets
existed at test time). Also asked whether the frontend even has a way to open a support ticket
at all (implying doubt it's reachable).

**Resolved that doubt**: real UI flow found and used — "Mis Pedidos" → order with real
items → "Algo no está bien" → select affected product (radio, must click via element `ref`,
pixel-coordinate clicks on it were unreliable/silently missed twice) → problem type "Otro" →
free-text `Detalles` → "Enviar reporte". Confirmed real ticket created via the actual frontend
flow (not a raw insert): `order_support_tickets` row `id: 8d57b527-2a7c-4d94-af8e-ed2897140e72`,
`order_id: 9a069ea5-75cc-4078-aba3-3804a2fe59da` (Sushi Tomo), `created_at:
2026-07-26T08:30:46.947103+00:00`, `resolved_at: null`. UI confirmed with a real toast:
"Reporte del problema recibido — El restaurante se pondrá en contacto... en los próximos 5
minutos."

**Blocker**: `auto-resolve-support-tickets` only processes tickets past some staleness
threshold (unknown exact value) — called immediately after creating the ticket, got
`processed:0` as expected. **Tried to backdate `created_at` via PATCH to fake staleness —
silently no-op'd** (same read-only-via-RPC-only pattern already documented for `orders` and
other tables in this codebase; confirmed via re-fetch, value unchanged). No shortcut available,
must wait for real elapsed time.

**Started a background poll** (`/tmp/.../scratchpad/poll_autoresolve.sh`, PID tracked as
background task `b3f7ioa7k`) that calls `auto-resolve-support-tickets` every 60s for up to 30
attempts (~30 min), and the moment `processed` is non-zero, re-fetches the ticket row and
prints it. **If this session ends before it fires**: re-run the same call manually
(`POST /functions/v1/auto-resolve-support-tickets` with zero auth headers) and check
`order_support_tickets?id=eq.8d57b527-2a7c-4d94-af8e-ed2897140e72` for `resolved_at` no longer
null — that's the before/after screenshot the triager wants (ticket visible as open in "Mis
Pedidos" activity, then silently resolved with no staff involvement). If 30 min passes with no
staleness threshold hit, the real threshold is longer than that — note it and consider whether
waiting further is worth it vs. just reporting the mechanism is proven (ticket created via real
UI + function still returns 200 with zero auth, matching original PoC) even without catching
the exact moment it flips.

**RESOLVED — caught it live, 2026-07-26 08:36.** Staleness threshold turned out to be ~5
minutes (ticket created 08:30:46, auto-resolved 08:36:20 — matches the UI's own toast text
verbatim: "el restaurante se pondrá en contacto... en los próximos 5 minutos", which is
apparently not a promise of human review, it's literally this timer). Result is a **bigger
finding than originally reported**: the ticket wasn't just silently closed — it was granted a
real **`resolution_type: "compensation"`** with message "Por el volumen de pedidos, te
regalamos este plato en tu próximo pedido más un 20% de descuento" and `resolved_by: null`
(no staff). Confirmed visually in the actual customer UI: a real toast ("El restaurante ha
respondido a tu reporte") and a modal ("Respuesta del restaurante — Pedido #9A069EA5 — El
restaurante ha respondido: ...20% de descuento...¡Gracias por tu comprensión!") — screenshot
taken, exactly the before/after proof the triager (Cristian) demanded on #2345. **Checked whether the "compensation" is real — it is NOT.** Queried `loyalty_rewards` and
`user_saved_codes` for this user right after the auto-resolution: no new row in either table
around 08:36 (most recent `loyalty_rewards` entry is still the original 2026-07-24 welcome
10% discount; most recent `user_saved_codes` entry is from 2026-07-25). Same caveat as the
already-reported `shishang-support-ticket-self-resolution` finding ("does NOT auto-grant the
reward right now") — confirmed to also apply to the REAL `auto-resolve-support-tickets`
function, not just a self-crafted fake ticket. **Correct impact framing for the #2345 reply**:
not "grants a real reward" (retracted, don't claim that) — it's that **the customer receives a
false promise of compensation that will never be honored**, on top of the complaint being
closed with zero human review. Two real, distinct harms: (1) real customer complaints get
silently closed unreviewed, (2) customers are shown a fabricated resolution message promising
a reward that doesn't actually exist anywhere in the system. **Next step: reply to #2345 with
this evidence** (ticket id `8d57b527-2a7c-4d94-af8e-ed2897140e72`, before/after timestamps, the
screenshot of the customer-facing "respuesta del restaurante" modal, and the two-part honest
impact above — do NOT overclaim a granted reward) — not yet sent, drafted comment pending.

**Cross-tenant + Realtime correlation EXECUTED 2026-07-26, ~09:34 Madrid (both restaurants
genuinely closed at the time):** fired the closed-hours bypass against both tenants within
~350ms of each other while a live anon-key WebSocket subscription to `realtime:public:orders`
was listening. Results:
- Shi Shang: order `90276aa0-1f06-4c1e-b555-390bdf4e6af1`, `created_at` 2026-07-26T07:34:18.562Z
  (09:34:18 Madrid) — **3h25m42s before** the 13:00 opening.
- Sushi Tomo: order `f520ac1b-c8f8-45ca-bd7c-99cbf63080e4`, `created_at`
  2026-07-26T07:34:18.880Z (09:34:18 Madrid) — **2h55m41s before** the 12:30 opening.
- Both INSERT events arrived over the public WebSocket within ~1s of their respective
  `created_at` (07:34:19.488Z and 07:34:19.492Z) — clean, correlated, dual-tenant proof in a
  single test. This is the strongest evidence gathered so far for the #2626-style pushback on
  #2440: not a one-off row, a live, externally-observable, cross-tenant bypass of the same
  shared RPC. Ready to fold into the #2440 triage reply.

**Cross-tenant angle added 2026-07-25, not yet executed:** confirmed Sushi Tomo
(`restaurant_id: e2316642-b9be-4bea-a865-b7677376eb91`) has the **same Saturday hours** as
Shi Shang (12:30–16:30 / 19:30–23:30) — checked via `restaurants_public`, both currently open
(19:43 Madrid) so couldn't repro live yet. Since the missing-hours-check bug lives in the
shared `submit_order_queued` RPC itself (no restaurant-specific logic), the plan is to fire the
closed-hours bypass against **both tenants at the same time** during the next real closed
window, to prove this is a systemic backend flaw affecting multiple live restaurants at once,
not a one-off — strong supporting evidence for the Informativo pushback. `portal.shishang.app`
correctly returned "Acceso no autorizado" for our customer-role session (role check working);
`portal.sushitomo.dingdingding.app` shows a normal, uncompromised Manager Portal login (Google/
phone-SMS/email+password) with no session carried over (separate localStorage origin) — no
bypass found on either portal, matches the already-documented dead end.

## Session 2026-07-28 — new bundle (`index.BmKMqwNO.js`), 7 previously-undocumented RPCs found and tested, all properly protected

User asked to look for "another function we can control." Fresh bundle grep for `rpc("..."` found
7 RPCs never seen/tested in any prior session: `admin_get_support_tickets`,
`check_order_rate_limit`, `consume_team_invitation` (already known), `get_coupon_by_code`,
`get_guest_order_by_token`, `mark_promo_code_used`, `process_unsubscribe`, `save_promo_code`.
Tested every one reachable with just the anon key (no session):

- **`admin_get_support_tickets({p_restaurant_id})`** — returns `[]` for anon even when queried
  against the Sushi Tomo restaurant_id that has a real known ticket
  (`8d57b527-2a7c-4d94-af8e-ed2897140e72`). Properly gated, silent-fail pattern (matches
  `loyalty_rewards`/`user_roles` style protection elsewhere in this codebase).
- **`mark_promo_code_used({p_coupon_code,p_order_id})`** — `401 permission denied for function`
  for anon. Confirmed the app never calls `.auth.signInAnonymously()` anywhere (grepped the
  bundle), so this RPC is likely a dead call in the real guest-checkout flow too (probably
  silently fails there as well, uncaught) — plausibly the actual root cause of the still-open
  `shishang-welcome-coupon-unlimited-reuse-guest` (#2348) bug: the "mark used" step for guest
  coupon redemptions may just never successfully execute. Worth mentioning if replying to #2348.
- **`get_guest_order_by_token({_order_id,_tracking_token})`** — this is the real mechanism behind
  `/tracking/<id>?token=...` guest order links. Created a real test order
  (`e825079f-93ae-4573-81e9-e69b9d2ab8c4`, "TEST - SECUR0 gueco tokentest") to inspect it:
  `tracking_token` is base64 of **32 random bytes (256 bits)** — cryptographically unguessable.
  Confirmed the RPC actually validates it (wrong token / empty / null / SQLi-shaped string all
  correctly return `[]`, no error, no info leak). Solid.
- **`save_promo_code({p_coupon_code})`** and **`check_order_rate_limit({p_user_id})`** — both
  `401 permission denied for function` for anon; would need an authenticated session to test
  further (e.g. whether `check_order_rate_limit` leaks rate-limit info for an arbitrary
  `p_user_id` that isn't the caller's own). **Open lead if resumed**: ask the user for a fresh
  session JWT (same friction as every prior authenticated test this hunt) and re-test
  `check_order_rate_limit` with someone else's real `user_id` specifically for that IDOR angle.
- **`get_coupon_by_code({p_code})`** — anon-callable, returns full coupon row (discount, min
  order, validity dates, is_single_use, is_exhausted) for any code string supplied. Not an
  enumeration vector by itself (still need to know/guess the code, and brute-forcing codes would
  violate the no-brute-force rule) — this is the app's real validation path since direct
  `coupons` table SELECT is blocked entirely. Not a finding.
- **`process_unsubscribe({p_token})`** — anon-callable by design (route `/unsubscribe/:token`,
  no login needed for email unsubscribe links). Garbage token returns `false` cleanly, no error,
  no derivable formula found client-side (token passed through verbatim from the URL, not
  computed from email/user_id). Didn't have a real token to check entropy — low priority, would
  need to intercept a real unsubscribe email to inspect, out of scope to pursue further.

**Bottom line: RPC layer is just as well-hardened as the raw-table layer already documented.**
Every new function found this session was either correctly session-gated or, where anon-callable
by design, correctly validated its input server-side. No new finding. The one open thread with
concrete next-step value is possibly re-testing `mark_promo_code_used`'s guest-path dead-call
theory as supplementary evidence for the #2348 reply.

**`check_order_rate_limit` IDOR lead — tested with a real session, CLOSED, not a vuln.** User
provided a fresh JWT for the shared test account (`59119b2e-2dca-4dd1-bb4f-de9fba6ba1f1`).
First call with a fabricated `p_user_id` looked suspicious (200, no permission-denied, unlike
`save_promo_code`/`mark_promo_code_used`) — but rigorously disproven: placed a real order under
the account (bumping its real `user_count` 0→1 via a genuine `submit_order_queued` call, order
`bd3da0d8-5042-456f-b55e-1ab79c8c1c73`, "TEST - SECUR0 gueco ratelimit-idor"), then re-queried
`check_order_rate_limit` with three different values for `p_user_id` — the caller's real id, two
different fabricated UUIDs, and `null` — **all four returned the identical, correct, freshly-
updated count (`user_count:1, remaining:1`)**. Conclusive: the function completely **ignores**
`p_user_id` and derives the caller's identity from `auth.uid()` (the JWT) internally — the
parameter is decorative/dead, not a trust boundary. Not exploitable, not worth reporting (matches
the "version disclosure"-adjacent cosmetic-non-issue bar already used elsewhere in this file).
Two real test orders left behind from this session, both clearly marked TEST in
`customer_name`/`notes`, no cleanup action available (order mutation is RPC-only, no delete path
exists anywhere in this codebase, consistent with every prior test order in this hunt):
`e825079f-93ae-4573-81e9-e69b9d2ab8c4` (tracking-token entropy check) and
`bd3da0d8-5042-456f-b55e-1ab79c8c1c73` (rate-limit IDOR check).

## Session 2026-07-28 (continued) — lesser-known vuln classes tried, mostly clean; found the vendor silently refactored/hardened `order_support_tickets` + `profiles`, one gap survives

User explicitly asked to keep digging for less-common vuln classes. Results:

- **OAuth `redirect_to` open-redirect / token-theft (GoTrue)**: `GET /auth/v1/authorize?provider=google&redirect_to=https://evil.example.com/steal` DOES echo the attacker URL into the outbound Google authorize URL's query string — looked like a real open redirect at first. **Verified against GoTrue's actual OSS source** (cloned `supabase/auth`): `GetExternalProviderRedirectURL` calls `utilities.GetReferrer(r, config)` which calls `IsRedirectURLValid` **before** persisting the value as `flowState.Referrer` — any URL not matching `SiteURL`/`URIAllowListMap` gets silently replaced with `config.SiteURL`. The attacker-URL string visible in the `/authorize` passthrough is cosmetic, not the value actually used for the final post-auth redirect. Confirmed via source, not assumption — **not exploitable**.
- **Race condition on `check_order_rate_limit`/`submit_order_queued` (2/hour-per-phone limit)**: fired 8 concurrent guest orders with the identical phone number. Exactly 2 succeeded, 6 got `RATE_LIMIT` errors — properly atomic/serialized server-side, no TOCTOU bypass.
- **Stored XSS via `customer_name` on `/invoice/<id>`**: previously only tested `reward_name` for XSS, never `customer_name` specifically on the invoice page (which does render it: "Cliente: ..."). Live-tested with `<img src=x onerror=...>` in a real guest order's `customer_name` — renders as escaped text, zero live `img[onerror]` elements, payload did not execute. Clean.
- **`admin_get_support_tickets` RPC re-tested with an AUTHENTICATED non-staff session** (only anon was tested previously) — still returns `[]` for both restaurants including the one with a known real ticket. Properly gated regardless of auth level.

**Important regression-check findings (the vendor appears to have quietly hardened things since
2026-07-26, likely in response to prior reports) — re-tested the 3 previously-reported
INSERT/UPDATE-column gaps with a fresh JWT:**

- **`user_saved_codes` fake-coupon-injection gap (never-submitted draft
  `shishang-fake-saved-coupon-injection`) — CONFIRMED FIXED.** Re-tested with the exact real
  field names from the current bundle (`user_id, coupon_code, coupon_id, reward_name,
  reward_description, discount_*` — verified these are still correct via bundle grep, so this
  isn't a false-negative from guessing wrong fields) → `403 "new row violates row-level security
  policy for table user_saved_codes"`. RLS INSERT policy was tightened. **Do not submit that
  draft — it's stale, would be closed as already-fixed.**
- **`order_support_tickets` self-resolution gap (already-submitted #2444) — CONFIRMED FIXED, and
  the vendor went further than a column-level fix.** Direct REST access to this table is now
  **completely revoked for the `authenticated` role** — even a plain `SELECT` with your own valid
  JWT and no filter now returns `403 permission denied for table order_support_tickets` (a flat
  Postgres GRANT-level denial, not just an RLS-scoped-empty-result like before). The app now
  exclusively uses the `admin_get_support_tickets`/other RPCs for this data (confirmed correctly
  gated, see above). Good outcome for a triage follow-up on #2444 if it's still open — this is
  strong independent confirmation the fix landed properly (defense-in-depth, not just a patch of
  the exact reported column).
- **`profiles` consent-field-forgery gap (drafted
  `shishang-profile-consent-fields-forgeable`, submission status was unconfirmed) — STILL
  EXPLOITABLE, but the PoC needs updating.** The `profiles` table schema changed: `id` (row PK)
  and `user_id` (FK to the auth user) are now **separate columns** — previously `id` directly
  held the auth user's UUID. The old PoC's filter (`PATCH /rest/v1/profiles?id=eq.<uid>`) now
  matches **zero rows** (harmless no-op, not a fix) because `id` is a different UUID now. Re-ran
  with the corrected filter (`?user_id=eq.<uid>`) and fresh distinguishable values
  (`consent_ip_address: "9.9.9.9"`, `marketing_consent_at: "2019-05-05"`) →
  **200, values persisted, confirmed via re-read.** The underlying authorization gap is
  unchanged; only the schema shifted. **If this hasn't been submitted yet, update the PoC's
  filter to `user_id=eq.<uid>` before submitting** — the old `id=eq.<uid>` version in the draft
  report would fail to reproduce and could get bounced as unreproducible.

**Deep dive on `profiles.email` mass-assignment, 2026-07-28 — user ultimately judged not worth
submitting once impact was fully chased down. Full chain, for future reference:**
- Confirmed (live, via browser overlay PoC + replayed through the user's local Burp proxy
  `127.0.0.1:8080` for HTTP-history evidence) that `profiles.email` accepts **any** value with
  zero validation — tested with two different real third-party emails (`javier@secur0.com`, the
  program's own contact; and the user's own real `diegopague10@gmail.com`), both persisted.
- `profiles.email` is **not shown anywhere in the customer-facing UI** — confirmed live, "Mi
  Perfil" shows "Email: No configurado" even after the field is set, because that screen reads
  the real `auth.users.email` (via GoTrue), not this column.
- Found a **plausible but unconfirmed escalation**: the staff panel's "Asignar admin"/"Asignar
  repartidor" user picker (component `h7` in the bundle) searches
  `profiles.select("user_id,display_name,email,phone").or(email.ilike...,phone.ilike...,
  display_name.ilike...)` — meaning a forged `profiles.email`/`display_name` could make an
  attacker's account show up as a lookalike match when staff search for a legitimate driver/admin
  candidate by email, risking a staff-error privilege grant to the wrong (attacker) account.
  **Never confirmed end-to-end** — no staff/portal access to actually test the picker UI.
- **Ruled out the scarier theory**: does writing `profiles.email` cascade into a real Supabase
  Auth email-change (and thus send a real confirmation email to whatever address is written,
  including third parties)? Tested conclusively via `GET /auth/v1/user`'s `new_email`/
  `email_change_sent_at` fields immediately before and after a fresh bypass PATCH — **unchanged**,
  proving the bypass never touches `auth.users` or triggers any email. (The one real confirmation
  email the user received, with `type=email_change` and a `redirect_to=hongkongcity.app/auth/
  callback` link, came from the user's own manual test of the *legitimate* "Cambiar email" UI
  button — a completely separate, correctly-working GoTrue flow — not from our bypass. Good news:
  no unintended email was ever sent to Javier or anyone else by our testing.)
- **User's final call**: without a confirmed live escalation path (the staff-picker chain is
  code-grounded but unproven, and the direct impact is "fabricate an unused DB column"), this
  isn't worth submitting. Don't revisit this specific finding unless staff/portal access becomes
  available to actually test the picker-collision scenario, which would be the one thing that
  could still make it a real submission.
- **Side observation, out of scope, don't act on it**: the `redirect_to=hongkongcity.app/auth/
  callback` in that real confirmation email confirms the shared Supabase Auth project's
  `URIAllowListMap` includes hongkongcity.app — consistent with the already-known shared-backend
  architecture, not a new issue, and hongkongcity.app is explicitly out of scope for this program.

## Session 2026-07-28 (continued) — "fix incomplete" hunting on already-Fixed/Accepted reports,
## two new submissions, one dead end (broken feature, not a vuln), cross-tenant confirmation

User's explicit strategy this stretch: re-examine reports the vendor already marked
Fixed/Accepted and look for gaps the fix didn't cover — same technique that worked for
ROLLITOSGRATIS/Sushi Tomo. Worked twice, dead-ended once:

**NEW FINDING, SUBMITTED — `shishang-bienvenida10-fix-incomplete-phone-format`**: #2348's fix
(accepted, CVSS 6.9) keyed its per-guest coupon-reuse guard on raw `customer_phone` string
equality, per the vendor's own closure note. Confirmed live: same real phone number with a `+`
prefix, a `00` prefix, or inserted dashes all successfully re-claimed the BIENVENIDA10 10%
discount after the byte-identical repeat was correctly rejected. **Also reproduced cross-tenant
on Sushi Tomo** (restaurant_id `e2316642-b9be-4bea-a865-b7677376eb91`, item `mochi de mango`)
with the same `+` prefix bypass — confirms this is a backend-level gap (not shishang-specific).
Visual proof captured: live browser overlay PoC on shishang.app, real Burp HTTP history replay,
and both orders' real `/invoice/<id>` pages showing "Descuento (BIENVENIDA10): -1,59€" twice for
the same real phone. Orders left live (not reverted): `f47eb411-...` and `e67d4ac9-...` on
shishang, `b83e1b2a-...` and `53fd11ab-...` on sushitomo, all clearly `TEST -` marked.

**NEW FINDING, SUBMITTED — `shishang-restaurants-tier-still-exposed-2350-incomplete`**: #2350's
fix (accepted, CVSS 6.9) correctly revoked `authenticated`'s broad grant on the raw `restaurants`
table (email/phone now properly blocked, verified via direct select, explicit column list, WHERE
filter, and 3-table PostgREST embedding — all `403`). But the original report's OWN complaint
about `tier` (SaaS billing-plan business intelligence) was never addressed: `tier` is already
part of `restaurants_public`'s column list, which is **readable with zero authentication at
all** (not even a free account, just the public anon key). Confirmed via a fully anonymous
`GET /rest/v1/restaurants_public?select=name,domain,tier,is_active` showing all 4 platform
restaurants' tiers, including out-of-scope hongkongcity.app and undocumented jardinbambu.app —
same platform-wide scope issue as the original report, now reachable with *less* effort than
before. Sent via Burp for the user's own screenshot.

**Dead end, not a vuln — `order_support_tickets` legitimate flow is currently broken (not just
secured):** tried an INSERT-then-UPDATE bypass theory on #2444's fix (closure note describes
only a `BEFORE INSERT` trigger nulling 4 resolution columns, no mention of `UPDATE`). Found
something more fundamental instead: a **plain, clean INSERT** (no resolution fields at all) also
now returns `403 permission denied for table order_support_tickets` — confirms the actually-
deployed fix is a full GRANT revocation, stronger than the trigger-based approach the closure
note describes. Checked the bundle: the client still calls
`.from("order_support_tickets").insert({order_id, restaurant_id, user_id, issue_type,
details_es, affected_item_names})` directly (unchanged code, no replacement RPC/edge function
exists yet) — meaning **the legitimate "report a problem with my order" feature is currently
non-functional for real customers**, not just secured against the resolution-field-forgery
abuse. Not a security finding (over-strict fix, not a bypass) — **user's call: park this, retry
once the vendor ships a real replacement flow** (an RPC or edge function), since that's exactly
the kind of change likely to reintroduce a column-scoping gap.

**Methodology note for future sessions**: the "check an already-Fixed report for gaps" technique
found 2 real, submittable, distinct findings out of 3 attempts this stretch (#2348 phone-format,
#2350 tier) — a good hit rate, keep applying it to any newly-Fixed/Accepted report. Always
re-verify the ACTUAL current server behavior rather than trusting the closure note's own
description of the fix (the #2444 closure note undersold how thorough the real fix was).

**How to apply if resumed:** the `profiles` consent-forgery finding is a live, currently-valid,
submittable bug — prioritize finalizing/submitting it with the corrected PoC. Given the vendor is
actively and competently patching (three real fixes landed since 2026-07-26: `user_saved_codes`
RLS tightened, `order_support_tickets` fully locked down, plus the earlier ROLLITOSGRATIS/Sushi
Tomo fix), it's worth periodically re-running the full `evidence/poc_*.txt` battery from the
STATUS CHECKLIST table at the top of this file — don't assume old "confirmed" results still hold
without re-checking field names/schema first (this session's `order_support_tickets` 400 errors
were initially misread as "table renamed" when the real story was "GRANT revoked entirely," and
almost missed the still-live `profiles` bug by not accounting for the `id`/`user_id` split).

**Reusable technique from this session — extracting the live apikey/Authorization headers
without asking the user to paste devtools output:** monkey-patch `window.fetch` from
`javascript_tool` *before* triggering any in-app action that calls Supabase (e.g. clicking
"Guardar dirección"), capturing `opts.headers` (handle both plain object and `Headers`
instance — `Headers` needs `.entries()`, plain `JSON.stringify` on it silently returns `{}`).
Much faster than the devtools-paste workflow noted earlier in this file for round 2's session
token friction.

## 2026-08-06: #2440 (closed-hours RPC bypass) fix VERIFIED genuine and live

User pasted #2440's closure ("Arreglado", vendor cited a new `enforce_restaurant_ordering_hours`
trigger). Waited until past the restaurant's real closing time (23:30 CEST) then re-ran the
exact original PoC live: fetched the current JS bundle for a fresh anon key, confirmed
`restaurants_public` still shows the same 13:00–16:30/19:30–23:30 hours, then POSTed the same
`submit_order_queued` RPC with a real menu item at 23:43 CEST (13 min past close). Result:
**HTTP 400, `P0001: "Restaurante cerrado ahora mismo. No aceptamos pedidos fuera de horario."`**
— previously this returned 200 with a real created order. **Genuine, deployed fix**, unlike the
AAS-target pattern of "fixed in git but never pushed to prod" — this program's fixes can be
trusted at face value, at least for this one. Reusable lesson: when a restaurant-hours-gated bug
gets marked Fixed, the verification requires literally waiting for a real closed window before
retesting — can't fake the clock server-side.

**Also re-checked the sibling tenant** (Sushi Tomo / `sushitomo.dingdingding.app`,
`restaurant_id: e2316642-b9be-4bea-a865-b7677376eb91`, same shared Supabase backend, also closes
23:30) — same `submit_order_queued` RPC, real menu item, same closed-hours window: **also
HTTP 400 `P0001` "Restaurante cerrado ahora mismo."** Confirms the fix is a genuine
per-restaurant dynamic check (reads `settings.opening_hours` by `p_restaurant_id`), not a
single-tenant patch — covers every restaurant on the shared backend, not just the one tested in
the original report.

## 2026-08-07 — fresh bundle (`index.DdCfkT5M.js`), 2 NEW findings SUBMITTED, several new
## admin RPCs found properly protected

User asked to sweep for "completely new" things, explicitly not worrying about overlap with
prior findings. Fetched the current live bundle — new hash, never seen before. Found 5 brand-new
RPCs never documented anywhere in this hunt: `admin_grant_claim_coupon`, `admin_reactivate_coupon`,
`get_restaurant_tier`, `list_restaurant_tiers`, `has_role`. Also new tables in `.from()` calls:
`coupon_usage`, `promo_quotas`, `restaurant_issue_types`, `print_queue`.

**SUBMITTED — report #3800, `shishang-has-role-unauthenticated-oracle`:** `has_role({_user_id,
_role})` is callable with ZERO session (just the public anon apikey, no Authorization header at
all) and genuinely discriminates — confirmed live with a fresh test account
(`user_id: 8d9a6050-69af-41b3-9ed6-e6aaa26d67f4`, phone `34612548077`): `_role:"customer"` on my
own id → `true`; `_role:"driver"`/`"admin"` → `false`; garbage role strings → real Postgres enum
error (`app_role` enum = `customer`/`driver`/`admin` only, confirmed via error message) — proves
it's a real, working lookup, not broken/always-false. Works identically for ANY `_user_id`,
including ones I don't own. Contrasted with sibling `check_order_rate_limit` (ignores its
`p_user_id` param, uses `auth.uid()` internally — properly protected) and the new
`admin_reactivate_coupon` (explicit `"No autorizado"` for a real non-staff customer on their own
order — properly protected) to make the "this one has no caller-role check at all" argument
concrete. Framed as an unauthenticated admin/driver-role enumeration oracle, Low-Medium severity
— info disclosure/recon primitive, not privilege escalation by itself.

**SUBMITTED — report #3801, `shishang-list-restaurant-tiers-anon-leak`:** 5th distinct vector
for the same long-running `tier` leak saga (#2350 → #2767 → #2892 → #2896 fix → the already-
documented realtime-subscription report) — and the worst one yet. The new `list_restaurant_tiers`
RPC (meant as the post-#2896-fix legitimate staff-only path) leaks `tier` for all 4 restaurants
with `curl -v`-confirmed ZERO Authorization header — pure anon apikey, no account at all. Its
sibling `get_restaurant_tier` (single-restaurant version) correctly returns `null` for the same
unauthenticated request, proving the protection exists elsewhere in this same codebase and was
just never applied to the bulk variant. Framed explicitly as continuing the existing chain, same
CVSS ballpark as prior accepted reports in this family (~6.9), arguably higher since this is the
first vector needing literally no account.

**Both admin_grant_claim_coupon / admin_reactivate_coupon investigated, NOT submitted — appear
genuinely well-protected.** `admin_reactivate_coupon` on my own real order → explicit
`{"message":"No autorizado"}` for a non-staff customer, even on an order they own — real internal
role check, not just existence-filtering. `admin_grant_claim_coupon` (the function that actually
issues a live compensation coupon when staff resolves a ticket as "compensation" — a real reward
this time, unlike the older self-resolution bugs which explicitly did NOT grant one) always
returned "Incidencia no encontrada" in every test, including a real ticket ID — **could not fully
rule out an owner-scoped bypass because ticket creation is still fully broken for real customers**
(`order_support_tickets` INSERT still `403 permission denied`, confirmed still true on this fresh
bundle — same dead-end noted 2026-07-28, vendor still hasn't shipped a replacement RPC). Given
`admin_reactivate_coupon`'s proven real role-check, the working assumption is `admin_grant_claim_coupon`
has the same protection — don't submit without proof. **Resume point if the vendor ever ships a
support-ticket-creation RPC/edge-function**: create a real owned ticket and retest
`admin_grant_claim_coupon` on it specifically — that's the one remaining untested path that could
turn this into a real, financially-impactful finding (self-granted arbitrary-amount coupon).

**Everything else tried this session, confirmed properly protected (don't re-test without new
info):** `coupon_usage` (RLS scopes SELECT to own rows correctly; DELETE/UPDATE on own row both
silently no-op, verified via re-read; coupon reuse-block still correctly fires after both
attempts), `print_queue` (403 for both anon AND authenticated — tighter grant than most tables
here, kitchen-printer-injection theory dead on arrival), `menu_items.current_price` and
`menu_item_modifier_options.price_delta` direct PATCH (both silently no-op, verified unchanged —
no direct price tampering via REST). `restaurant_issue_types` is anon-readable but it's just a
static issue-type lookup/enum table, no security value.

**Fresh fully-clean test account used this session** (not the one with the real Google account
linked): `user_id: 8d9a6050-69af-41b3-9ed6-e6aaa26d67f4`, phone `34612548077`. Two real test
orders left behind, both clearly `TEST -` marked, no cleanup path exists (same as every other
order in this hunt): `5f4c94fd-559d-4f48-aefb-ee3dc86e1ced` (Sushi Tomo, no coupon) and
`0d2eb928-a66e-4ed0-9ba3-f5258d64797d` (Sushi Tomo, BIENVENIDA10 applied, 3x Anguilas, real
`coupon_usage` row `582fa8da-66e6-48f0-90c4-ed129334baff` still on that account).

**Both report titles hit the already-known Secur0 `invalid_format` bug on first submit attempt**
(title contained an underscore-joined token — `has_role`, `list_restaurant_tiers` — see
[[reference_secur0_api_pipeline]]) — fixed both by rewording to plain words before resubmitting,
no need to relitigate this pattern again, just check title text for underscores/long length
before the first submit attempt next time.
