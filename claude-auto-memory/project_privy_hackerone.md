---
name: project-privy-hackerone
description: "Privy bug bounty program on HackerOne — Web3/crypto auth SDK, open-source npm packages in scope, live web assets also in scope"
metadata: 
  node_type: memory
  type: project
  originSessionId: 593c4a64-2b76-406e-93dc-712e72e5abad
---

Program: Privy (privy-bbp) on HackerOne, public bounty, launched Jan 2025. Response efficiency 96%. Rewards: $100-$500 (Low) / $500-$2,500 (Med) / $2,500-$5,000 (High) / $5,000-$10,000 (Critical, avg n/a — few/no paid yet). Top bounty range seen: $2,500-$20,000.

Product: developer onboarding tool for web3 — wallet connectors (third-party wallet connect), embedded self-custodial wallets, an auth system underlying both, and a public API + console.

**In scope (16 assets, all max severity Critical, all bounty-eligible):**
- Open-source npm packages (session focus, per user request — "prefiere el open source"):
  - `@privy-io/react-auth` — explicitly typed "Source code" on the scope table (the others are typed "Other")
  - `@privy-io/wagmi`
  - `@privy-io/js-sdk-core`
  - `@privy-io/expo`
  - `@privy-io/cross-app-provider`
  - `@privy-io/cross-app-connect`
  - "@privy-io controlled namespace dependencies" — explicitly covers supply-chain/dependency-confusion angle
- Live web domains: `recovery.privy.io`, `home.privy.io`, `dashboard.privy.io`, `auth.privy.io`, `api.privy.io`
- OpenAPI spec for the public API: https://dashboard.privy.io/api/v1/openapi.json
- `demo.privy.io` exists and is usable to exercise flows, but demo-specific bugs are NOT considered — only look for issues that are real Privy vulns surfaced through it, not bugs in the demo app itself.

**Out of scope entirely:** privy.io (main site), docs.privy.io, blog.privy.io, demo.privy.io (as an asset — see above nuance).

**Account setup requirement (critical, easy to miss):** to be bounty-eligible, must create a Privy account (dashboard.privy.io signup) with the string "(BBP)" in the "Project or company name" field, AND sign up using the hacker's HackerOne email alias (username@hackerone.com) — not a personal email. Without this the submission won't be associated with the program correctly.

**Long out-of-scope vuln list (check before drafting any finding):** race conditions on soft account limits, credit-card bypass to move to production, viewing public App ID configs, permissive CORS, OAuth redirect to any domain (unless bypasses the documented allowlist), hard-to-remove team resources, admin-removes-admin, JWT session expiry (low timeout by design), public JWKS, third-party auth creating separate accounts (except Google OAuth), PNG-upload-bypass-to-other-filetype, feature-gating/billing bypasses (soft boundaries, includes webhook + 3rd-party auth features), physical-access attacks, MITM-required attacks, obsolete-browser-only attacks, missing best-practices headers without demonstrated impact, clickjacking/CSRF on unauthenticated no-sensitive-action pages, open redirect without demonstrated impact, self-XSS/self-DoS (including against your own team), missing postMessage origin validation when host app has no CSP, missing postMessage origin validation specifically in `cross-app-connect`/`cross-app-provider`/`react-auth`/`js-sdk-core` client SDKs (explicitly called out as OOS), content/CSV/text injection without impact, version disclosure/banners/stack traces, attacks needing unlikely victim interaction, "perceived" weaknesses without demonstrated impact.

**Program rules:** one vuln per report unless chaining for impact; duplicates only pay the first fully-reproducible report; multiple vulns from one root cause = one bounty; no social engineering of customers/employees; don't touch Privy customer sites/domains/apps (that's OOS entirely, applies to any third party built on Privy); no DoS/DDoS/volumetric.

**How to apply:** this session's plan is to start with source-code review of the open-source npm packages (same methodology as the recent Keycloak Operator work — clone the real GitHub repo behind the npm package, audit, build live PoC) since that's a stronger fit than live API testing which needs the (BBP)-tagged account + API keys first. `@privy-io/react-auth` is the one explicitly flagged "Source code" scope type — good first target. The "@privy-io controlled namespace dependencies" scope line specifically invites supply-chain research (dependency confusion, typosquatting, malicious transitive deps) — worth a dedicated pass.

**2026-08-14 session outcome — paused, not abandoned:**
- Deep-dived `privy-io/shamir-secret-sharing` (the only genuinely open-source, non-minified repo). Found a real, confirmed, currently-shipping regression: the non-zero-leading-coefficient check (originally fixed per audit finding PVY-01-002, 2023) was deliberately removed again in Jan 2025 (PR #22) after a ~2-year, multi-firm (Cure53 + Zellic + Cypher Stack) deliberation, publicly explained in a Privy blog post. Confirmed via git+npm registry cross-check (gitHead field, checksum-verified fresh downloads) that npm "latest" (0.0.4) ships the reverted/vulnerable code. Built rigorous statistical PoCs (200k+ trials) matching theoretical 1/256-per-byte leak rate almost exactly, against Privy's own documented n=2,t=2 (or possibly 3-share/2-of-3, sources conflict) production config.
- **Why not submitted:** this was a deliberate, publicly-reasoned engineering trade-off by Privy (not an oversight), so framing it as "critical vuln" risks a credibility-damaging "won't fix, already considered" response. Real exploitability is capped — the leak is per-byte/independent, so even with a free verification oracle (deriving a wallet address from a candidate key) an attacker can't brute-force the remaining ~30 unknown bytes of a real key; no path to full key theft was found. Confirmed there's no way to test raw share material against real production infra either (export features only return the final reconstructed key, never raw shares — correct-by-design, but means no live PoC beyond the library level is achievable). Given [[feedback_privy_no_hypothesis_poc]], this doesn't meet the bar of a submittable finding without further angle work.
- Also checked: client SDKs (react-auth, js-sdk-core, cross-app-connect, cross-app-provider) ship only minified JS in their npm tarballs (no readable TS source, 765 files in react-auth alone) — and the most natural bug class there (postMessage origin validation) is explicitly listed OOS for exactly those packages. Checked full `@privy-io/*` internal dependency tree for dependency confusion — all packages properly published, no gap found.
- **Resume point if returning to Privy:** the shamir-secret-sharing finding's documentation-gap angle (README's "Security considerations" doesn't disclose the ~11%-per-32-byte-split accepted risk, unlike the separate blog post) is the most defensible remaining angle — low severity but real and actionable. Full investigation trail (git commits 8d6d39d/3333451/ab86736, PRs #2/#12/#22, issues #11/#12, blog posts) is in this session's transcript if picked back up.
