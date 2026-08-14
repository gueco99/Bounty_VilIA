---
name: project-coupang-tw
description: "Coupang Taiwan H1 program hunt state — PAUSED 2026-07-18 in favor of [[project_lasrozasinnova]], scope, email alias, killed/parked leads, recon findings"
metadata: 
  node_type: memory
  type: project
  originSessionId: af7dde18-801c-473e-bf9a-1ea1802fac29
---

Active hunt on HackerOne program **coupang_tw** (Coupang Taiwan), started 2026-07-15.

**Program facts:**
- 47 in-scope assets (domains + iOS/Android apps). Full list saved at `recon/coupang_tw_scope.txt` (prioritized subset: payment/pay/checkout/cart/cart-front-api/fintech-aml-kyc/fileupload/fileupload-video/rs-open-api/developers.tw.coupangcorp.com/cash/mauth/id/loyalty/mc/notification-front-web).
- Severity ranges: Critical $4k-6k, High $1.5k-3k, Medium $400-600, Low $50-200.
- IDOR reports require proof of how the "unpredictable ID" was obtained — sequential-ID IDOR alone is rejected (Platform Standards deviation).
- TW and KR (+ iOS/Android) share backend code — only first submission across those wins; flag anything that looks shared.
- Must send `X-HackerOne-Researcher: gueco` header on all test traffic (see [[user_h1_username]]).
- Test account email for THIS program: **gueco@imnotahacker.com** (user's explicit choice, overriding the program's suggested `h1username@wearehackerone.com` alias convention — user directed this deliberately, don't "correct" it back).
- `wing.coupang.com` and `coupangtw.zendesk.com` are seen in redirect chains but are **NOT in the 47-asset scope list** — do not actively test them without program permission (per program rule on unscoped subdomains).

**Recon results (2026-07-15, `recon/coupang_tw_scope/`):**
- 16 live hosts, 258 leads ingested into Lead Board (`memory/leads/coupang_tw.jsonl`) — most are Next.js static-asset noise misclassified as `hunt-oauth` (path contains `/auth/v3/`).
- Subdomain takeover candidate on `developers.tw.coupangcorp.com` (CNAME→zendesk) — verified NOT vulnerable via subjack, killed.
- `developers.tw.coupangcorp.com/auth/v3/sso_bypass` — turned out to be Zendesk's own `login-ui-service` vendor code (title "Zendesk Auth - SSO bypass"), not Coupang-custom — low priority, parked as likely platform-wide non-Coupang-specific.
- `developers.tw.coupangcorp.com/access/login?return_to=` — forwards unsanitized return_to to `wing.coupang.com` (out of scope) — parked, can't verify final hop without program permission.
- `developers.tw.coupangcorp.com/agent/admin/ticket_fields` — killed, just a client-side JS redirect to login for unauth users (working as intended).
- `cart-front-api.tw.coupang.com` returned 503 during httpx probing — worth a re-check.
- Core commerce hosts (payment/pay/checkout/cart/fintech-aml-kyc/fileupload*) each returned only 1 URL from passive crawl — they're auth-gated SPAs; passive recon can't map them. Need an authenticated session + manual proxy-driven crawl (Burp/mitmproxy) to find real endpoints.

**Why:** IDOR/business-logic bugs are worth the most on this program (checkout/cart/payment/KYC = money) but require authenticated testing since these are SPAs.
**How to apply:** Next step is creating a test account on tw.coupang.com with gueco@imnotahacker.com and manually driving checkout/cart/payment flows through a proxy to map real endpoints before resuming automated hunting.
