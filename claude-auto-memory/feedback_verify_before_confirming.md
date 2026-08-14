---
name: feedback-verify-before-confirming
description: "Always verify a finding end-to-end (actual rendered/charged value, not just an API's 200 response) before reporting it as confirmed"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 25970122-8653-46c2-a5e0-ef59987a33db
---

Never report a vulnerability as confirmed based only on an API returning a "successful" response (e.g. HTTP 200, a valid-looking session/URL). A success response only proves the request was accepted — it does not prove the manipulated value was actually used downstream.

**Why:** On the 0xTHUG program (2026-07-21), I reported a checkout price-manipulation bug because `POST /api/checkout` returned 200 with a valid `cs_live_...` Stripe Checkout Session URL when I sent a tampered `price` (0.01€/0€ instead of the real 15€). The user then checked the actual Stripe-hosted page and the price was still 15€ — the backend was correctly recalculating the real price server-side and simply ignoring the client-supplied field. The report had to be retracted. The API accepting the request said nothing about whether the tampered field was honored.

**How to apply:** Before writing up or submitting any finding, especially ones involving business logic / financial values / server-side recalculation (prices, quotas, permissions, amounts), verify the *actual downstream effect* — load the real resulting page/state, check the value that would actually be charged/applied/persisted — not just the immediate API response code. If I can't verify it myself (e.g., can't safely load a live payment page), explicitly say so and ask the user to check before treating it as confirmed, rather than presenting it as settled. This applies across targets, not just 0xTHUG.
