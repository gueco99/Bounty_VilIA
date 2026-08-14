---
name: project-ecommerce-template
description: "Ecommerce Template (github.com/MarcosCamara01/ecommerce-template) hunt state — Next.js 16 + Drizzle + Supabase + Stripe VDP, 45 reports/8 accepted. 1 finding DRAFTED+PARKED (not submitted): unauthenticated Stripe checkout session disclosure (PII + payment data) via session_id in a public URL."
metadata: 
  node_type: memory
  type: project
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

Target: `github.com/MarcosCamara01/ecommerce-template` — Next.js 16 App
Router e-commerce template. Auth via `better-auth` (`@/utils/auth`), DB via
Drizzle + Supabase Postgres with Row-Level-Security enforced via a custom
`withRLS(userId, ...)` helper (`src/lib/db/drizzle/connection.ts`) that sets
`app.current_user_id` per-transaction for RLS policies to key off. Payments
via Stripe.

**Finding #1 DRAFTED, PARKED (not submitted — save-don't-submit mode,
[[feedback_hunt_save_dont_submit_mode]]): unauthenticated disclosure of full
Stripe checkout session (PII + payment data).** `GET /api/stripe/
checkout_sessions?session_id=cs_...` (`src/app/api/stripe/checkout_sessions/
route.ts`) calls `stripe.checkout.sessions.retrieve(session_id, {expand:
["payment_intent"]})` with ZERO auth/ownership check — no call to
`auth.api.getSession()`/`getUser()` (both used correctly elsewhere in this
same repo, e.g. `payment/route.ts` and `user/cart/route.ts`), and no
`src/middleware.ts` exists to cover it globally either. The identical
unrestricted logic is duplicated server-side in `fetchCheckoutData()`
(`src/services/stripe.service.ts`), used by the public `/result` page —
so even the "legitimate" confirmation flow discloses the customer's email
to ANY visitor (logged in or not) who knows/guesses the session_id.
`session_id` is embedded directly in the public `success_url` Stripe
redirects to (`${origin}/result?session_id={CHECKOUT_SESSION_ID}` in
`payment/route.ts`) — an ordinary leak vector (browser history, analytics
scripts capturing full URL, access logs). Checkout sessions are created
with `billing_address_collection: "required"` and `phone_number_collection:
{enabled: true}`, so the disclosed data includes full name, email, phone,
and billing address, plus payment_intent (card brand/last4-level data).
Draft CVSS 4.0: `AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:N/VA:N` — High. Code-level
finding (both vulnerable functions read line-by-line, no live Stripe test
session run). Files: `findings/dia3/ecommerce-template-stripe-session-idor/
report.md`.

**Checked and found SOLID (not a bug):** cart/wishlist IDOR concern —
`cart.repository.ts`/`wishlist.repository.ts`'s `delete()`/
`updateQuantityInternal()` filter queries by item `id` ALONE (not also by
`userId`) in the SQL WHERE clause, which looked like a classic IDOR at
first glance — but ownership is enforced by Postgres RLS policies via
`withRLS()`, and I read BOTH `drizzle/migrations/0002_rls_hardening.sql`
(defines `USING (app.current_user_id() = user_id)` policies for
cart_items/wishlist SELECT/INSERT/UPDATE/DELETE) AND the later
`0003_policy_cleanup.sql` (only touches products_items/products_variants/
order_items/customer_info/order_products — does NOT regress the cart/
wishlist policies). Correctly designed as shipped in this repo; the only
residual risk is deployment-specific (migrations never being applied to a
live instance), which is out of scope to claim without a live target per
[[feedback_verify_against_live_target]].

**Not yet examined:** auth routes (`api/auth/[...all]`, `api/auth/
update-user`), `api/email`, `stripe/webhooks` (webhook signature
verification not yet checked), admin panel beyond the `admin/products`
route already reviewed (looked solid — `verifyAdmin()` checks session +
hardcoded `ADMIN_EMAIL` match on every POST/PUT/DELETE).
