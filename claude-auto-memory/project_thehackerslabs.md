---
name: project-thehackerslabs
description: "TheHackersLabs-Academy (github.com/CuriosidadesDeHackers/TheHackersLabs-Academy) — Django/DRF learning platform VDP on Secur0. Real program name on Secur0 is 'The Hackers Labs' (with spaces), NOT the repo slug."
metadata:
  node_type: memory
  type: project
  originSessionId: ff7451f9-ed99-4be8-8d13-3103f0c4f6ba
---

**Program name on Secur0 is "The Hackers Labs"** (handle 113, VDP) — the repo is
`TheHackersLabs-Academy` but `secur0_api.py submit`/`get_program_details` needs the exact
platform display name, not the GitHub slug. `submit ... VDP "TheHackersLabs-Academy"` 404s;
`submit ... VDP "The Hackers Labs"` works. Live site: `academy.thehackerslabs.com`.

**Prior history (before this session)**: 8 findings drafted in `findings/dia1/`
(course-instructor-mass-assignment, simulate-subscribe-membership-bypass,
lesson-completion-point-farming, hardcoded-secret-key-auth-bypass, lesson-idor-unpublished-course,
self-like-point-farming, media-unauthenticated-file-disclosure, leaderboard-point-farming). The
hardcoded-SECRET_KEY one was submitted as #2307 and had to be **retracted** — it only reproduced
against a local `.env` with the insecure fallback key deliberately set, not against the real
deployment (which has a proper custom key). See [[feedback_verify_against_live_target]] for the
full incident — this is the origin story of that rule.

## Session 2026-08-02: verified 9 days of upstream fix commits, found one real gap

Local clone was 9 days stale (`4f3a040d` → `a878f23` on `origin/main`). Fetched fresh and found
~11 new commits, most explicitly fixing our own prior findings plus 2 the maintainer found
independently (post-attachment authorship, is_banned not enforced anywhere). Verified each
against the actual current code, and live-tested the config-dependent ones locally with
`DEBUG=False` (not against the live prod site — set up a local venv +
`python manage.py runserver` instead, per explicit user instruction this session to test safely
locally rather than repeat the #2307 mistake pattern via a *different* untested path).

**All CONFIRMED fully fixed, no residual gaps found:**
- Media unauthenticated disclosure (`bce4824`) — 3-layer verified live: direct `/media/...` path
  404s, new download endpoints require `IsAuthenticated` (401) then `HasActiveMembership` (403).
- `SimulateSubscribeView` membership bypass (`9ce0344`) — now gates on `settings.DEBUG` instead
  of the DB-editable `SiteConfig.stripe_secret_key`. Live-verified with `DEBUG=False`: 404.
- Course-instructor mass assignment (`7166a28`) — `validate_instructor()` correctly restricts
  reassignment to admins only.
- Unpublished-lesson IDOR (`936d156`) — centralized `_visible_lessons()` helper applied to all
  3 affected endpoints; grepped for other unfiltered `Lesson.objects` uses, the remaining ones
  are all `IsAdminOrOwnerInstructor`-gated write endpoints, a different threat model, not a gap.
- Post-attachment authorship (`a2ea025`, maintainer's own finding) — correct, including the
  manual `check_object_permissions()` call needed since `ListCreateAPIView.create()` doesn't
  auto-invoke object-level checks the way retrieve/update/destroy views do.
- Banned-user enforcement (`8d10e96`, maintainer's own finding) — `ActiveUserJWTAuthentication`
  checks `is_banned` on every authenticated request, not just login. Checked the refresh-token
  edge case specifically (refresh itself doesn't re-check ban status) — not exploitable, since
  the freshly-refreshed access token is immediately rejected the moment it's used for anything,
  as every authenticated call re-validates.
- Like/lesson-completion point-farming cycling (`52e1977`) — idempotent via `get_or_create` +
  explicit delete-and-recalculate on revert + DB `UniqueConstraint(user, action, reference_id)`
  as defense in depth. Also blocks self-like now.

**Finding — SUBMITTED (report_id 3310, 2026-08-02), gap in an adjacent fix**:
`findings/dia2/thehackerslabs-leaderboard-point-farming-not-fixed/report_secur0.md`. `52e1977`'s
commit message only mentions "like y lección completada" — it does NOT touch
`PostListCreateView`/`CommentListCreateView`, which is a **distinct root cause** from the
original `thehackerslabs-leaderboard-point-farming` finding (unlimited POST/COMMENT creation,
no `throttle_scope`, unconditional `LeaderboardPoint.objects.create()` per post/comment). The
new `UniqueConstraint` doesn't accidentally cover this either, since each new post/comment gets
its own `reference_id` — the constraint only blocks re-farming the SAME post/comment, not
creating unlimited new ones. Live-exploited on our own local instance (`DEBUG=False`): 30 rapid
1-character comments took points from 10 → 160 (exactly `10 + 30*5`), no throttling whatsoever.

**Lesson**: when several related bugs get fixed in one focused commit, always check whether the
commit message's own scope ("like y lección completada") is narrower than what the *original*
report actually covered (3 separate point-farming vectors were reported: like-cycling,
lesson-completion-cycling, and unlimited-post/comment-creation) — a fix can be completely correct
for what it targets while leaving a sibling, differently-shaped instance of the same class of bug
untouched. Same shape as the chezmoi #2889 lesson, but caught proactively this time by reading
the commit message's own stated scope critically rather than assuming "leaderboard fix" meant
"all three leaderboard findings."

## Session 2026-08-02 continued: business logic / race condition sweep, one near-miss

Checked profile mass-assignment (clean, `role`/`points`/`is_banned` correctly read-only), member
directory (clean), chat/notifications/events/certificates (all clean, properly scoped to
request.user or intentionally public), all admin endpoints (clean, `IsAdminRole`-gated), password
reset flow (standard Django token generator, correct anti-enumeration). Checked for race
conditions in the like/lesson-completion toggle views — safe, backed by real DB-level
`unique_together`/`UniqueConstraint`, Django's `get_or_create` retry-on-IntegrityError handles
the concurrent case correctly. Checked Stripe webhook idempotency (`update_or_create`/absolute
`end_date` assignment, not additive) — safe against duplicate event delivery.

**Near-miss, correctly caught before submitting**: `StripeWebhookView`'s entry gate checks
`config.stripe_secret_key` but the actual signature check uses a *different* field,
`config.stripe_webhook_secret`. Confirmed via the real `stripe` Python library that
`stripe.Webhook.construct_event()` accepts a forged signature when the endpoint secret is an
empty string (attacker just HMAC-signs with the same empty key, no real secret needed) — this
would have been a complete Stripe payment bypass (forge `checkout.session.completed` with
`payment_status: paid` for any `user_id`/`plan_id`, including lifetime, for free) if
`stripe_webhook_secret` were empty in production, exactly the same *shape* of bug as this
program's two prior false positives ([[feedback_verify_against_live_target]]: hardcoded
SECRET_KEY, DEBUG leak). **Verified safely against the real production endpoint** (user's
explicit instruction) using a harmless probe: signed a webhook payload with `"type": "ping"`
(not handled by any branch in `StripeWebhookView.post()`, so even if accepted it triggers zero
side effects — no membership granted, no state changed) with the empty-key forged signature, and
POSTed it to `https://academy.thehackerslabs.com/api/memberships/webhook/`. Got **HTTP 400** —
signature correctly rejected, `stripe_webhook_secret` is properly configured in production. Not
exploitable. Not drafted, not submitted.

**Lesson reinforced (3rd time on this specific program)**: any finding whose exploitability
hinges on "an admin-configurable secret/key field is left empty" needs a live-target check before
being taken seriously, and — new this time — that check can often be done *safely*, with zero
real-world side effects, by choosing a proof method that only tests the specific broken
precondition (here: an unhandled event type that can't trigger the payment-bypass consequence
even if the signature check is bypassed) rather than the full exploit chain. Worth applying this
"minimal safe probe" pattern generally: when a finding's precondition is checkable via a
side-effect-free request, do that instead of either skipping verification or fully exploiting.

**How to apply if resuming**: local dev setup works — `python3 -m venv`, `pip install -r
backend/requirements.txt`, `DEBUG=False python manage.py runserver 127.0.0.1:8123` to test
against a prod-like posture without touching the real site. `f6fe3ae` (subscriptions user list
filters) and `2a966b0` (`payment_status=paid` requirement) and `0a1b518`
(video preview frame) were not deeply audited — looked like non-security/cosmetic on a skim, low
priority if resuming.
