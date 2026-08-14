---
name: project-shopify-hackerone
description: "Shopify bug bounty program on HackerOne — focus on github.com/Shopify/* public repos (Source code scope), Medium severity/non-core, up to $200k max for Critical core"
metadata: 
  node_type: memory
  type: project
  originSessionId: 593c4a64-2b76-406e-93dc-712e72e5abad
---

Program: Shopify on HackerOne, launched Apr 2015, mature/high-volume (1950 reports/90 days, $9.48M total paid, response efficiency only 44% — expect slow/variable response). Average time to first response 5 days, to triage 2 weeks, to bounty 1 week 5 days, to resolution 4 months 2 weeks.

**Reward bands:** $500-$1,000 (33.7% of reports) / $1,000-$14,000 (55.1%) / $14,000-$50,000 (8.55%) / $50,000-$200,000 (2.64%, avg $82,090). Max $200k for Critical on core. Scored via Shopify's own Bug Bounty Calculator (CVSS-based); score <3 = flat $500, score >=3 = calculator-determined. Non-core properties get Environment Score C/I/A modifiers forced to Low — meaningfully caps payout even for a technically-Critical-looking bug in non-core scope.

**Session focus: `https://github.com/Shopify/*`** — "Public repositories available under the Shopify organization in GitHub." Type: Source code. Environment: Non-core. Max severity: Medium. Eligible. 35 resolved reports (1% of total) historically — low volume relative to the whole program, plausibly under-hunted relative to the live web assets.

**Critical account/testing rules (do not violate — explicit disqualification risk):**
- Must create the Shopify account using a `@wearehackerone.com` email alias (HackerOne-provided), not a personal email.
- Test ONLY against stores you created yourself via the registered account. **Testing against live merchant stores is explicitly prohibited** — closed as N/A and can cause disqualification from the whole program, not just the one report.
- Never contact Shopify Support as part of testing, to pre-validate reports, or to ask for status updates — this alone disqualifies from reward and risks a program ban.
- Leaked credentials: report immediately, do not test validity beyond authenticate-then-immediately-deauthenticate (no exercising functionality with them), never share the credentials outside the report.

**Other scope notes:**
- `admin.shopify.com`, `accounts.shopify.com`, `partners.shopify.com`, `*.myshopify.com` (dev stores), `shop.app`, `shopify.plus`, `arrive-server.shopifycloud.com`, `*.pci.shopifyinc.com` — all Core, Critical max, Eligible. NOT this session's focus (live-web, needs account setup + own dev store — a separate angle from source-code review).
- `*.shopifycs.com` (PCI-compliant card handling) — Non-core but still Critical max, worth remembering if a lead ever points there.
- Explicitly OOS/Ineligible: Shopify Third Party Store/Apps (report to the third-party dev first), `cdn.shopify.com` (file upload is intended functionality, not a bug), `community.shopify.com`/`community.shopify.dev`/`academy.shopify.com`/`investors.shopify.com`/`livechat.shopify.com` (third-party operated), `supplier-portal.shopifycloud.com`.
- `Shopify Developed Apps` (apps under apps.shopify.com/collections/made-by-shopify) — Non-core, Medium, Eligible, 237 resolved reports (10% of total) — high historical volume, likely picked over.
- Duplicate root-cause reports get closed as Duplicate — only first reporter of a given root cause is paid.
- IDOR eligibility depends on identifier predictability + data sensitivity + impact — not automatic.
- Reports must have a functional PoC demonstrating real impact on Shopify/Shop users/partners/merchants or get closed N/A — matches [[feedback_no_hypothesis_poc]] exactly, no adjustment needed to existing working style.

**How to apply:** start with recon of the `Shopify` GitHub org's public repo list to find smaller/less-scrutinized repos (same methodology as the Kubernetes git-sync hunt — avoid the flagship, heavily-audited repos like `liquid` or core Ruby-on-Rails app code that thousands of eyes have already been on; look for smaller CLI tools, internal-tooling-adjacent utilities, or recently-active-but-lower-profile repos). Cross-check any candidate against [[reference_h1_technique_corpus]] for prior disclosed Shopify reports before investing deep time.

**2026-08-14 session results (9 repos reviewed):**
- `shipit-engine` — webhook CI-status forgery → deploy bypass (integrity only, no data impact). DRAFTED, not submitted, parked pending decision. Also ruled out a cross-tenant-stack-visibility angle as documented/intended (flat trust model per `docs/setup.md`).
- `ejson-rails`, `identity_cache`, `maintenance_tasks`, `toxiproxy`, `hansel` — clean, no exploitable bug found.
- `shopify-app-js`, `shopify-api-php` — official app SDKs used by third-party app developers; extensively audited (HMAC compare, JWT session token, OAuth state cookie, shop-domain regex) — all correctly hardened, well-written, no bypass. Good signal these first-party SDKs are high-quality; deprioritize re-auditing the same primitives if revisiting.
- `themekit` — **SUBMITTED-READY finding**: `--proxy` flag (CLI/env/config.yml, fully documented, ordinary use case) sets `InsecureSkipVerify: true` on the HTTP transport used for ALL subsequent requests to Shopify's real API, silently exposing the user's live Theme Access token to any on-path MITM. Confirmed with a fully executed live PoC (real binary built from HEAD v1.3.3, real mitmproxy MITM with untrusted self-signed cert, real token captured in cleartext, request successfully forwarded to and answered by Shopify's real API). Real third-party victim: any merchant/developer using `--proxy`, cascading to that merchant's own customers if the stolen token is used to inject a storefront skimmer. Report + PoC in `findings/dia2/themekit-proxy-tls-verification-disabled/`.
- Not yet reviewed: `shopify-app-php`, `cli` (both cloned, good next candidates), `shopify-app-python` (cloned, tiny repo, not yet reviewed).
- Lesson: on official first-party SDKs (high scrutiny, many eyes), core crypto/auth primitives are unlikely to yield bugs — better ROI checking CLI tools that handle live credentials with less obvious "security-critical" framing (like themekit's proxy handling) than re-checking HMAC/JWT compare logic yet again.
