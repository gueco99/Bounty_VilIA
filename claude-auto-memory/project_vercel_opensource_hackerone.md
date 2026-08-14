---
name: project-vercel-opensource-hackerone
description: "Vercel Open Source program on HackerOne — 19 in-scope repos (Next.js, Svelte, Nuxt, AI SDK, Turborepo, etc), Critical max, all Eligible, much more active/responsive than Shopify"
metadata:
  type: project
  originSessionId: 593c4a64-2b76-406e-93dc-712e72e5abad
---

Program: Vercel Open Source on HackerOne (`vercel-open-source`), launched Feb 2026. Response efficiency 90% (much better than Shopify's 44%), last report resolved 15 hours ago (Aug 14 2026) — actively triaged. 4,328 reports/90 days, 104 resolved, $242,435 total paid, avg bounty $628-$860.

**Reward bands (4 tiers, unlabeled severity names but inferred Low/Med/High/Crit from bounty ranges):**
- ~Low: avg $274, 25.74% of submissions, $50-$500
- ~Medium: avg $877, 48.51% of submissions, $250-$1,000
- ~High: avg $4,157, 20.79% of submissions, $750-$5,000
- ~Critical: avg $6,675, 4.95% of submissions, $2,750-$10,000

**19 in-scope assets, all Critical max / Eligible / Source code (except 3 "Tier N OSS / Other" buckets for experimental-feature bounty calc):**
- Tier 1/2/3 OSS (Other, catch-all buckets) — 39(38%)/16(15%)/4(4%) resolved
- `github.com/vercel/vercel` (main CLI/platform monorepo) — 0 resolved
- `github.com/vercel/next.js` — 4 resolved (tier 1, expect heavy prior scrutiny)
- `github.com/vercel/ai` (AI SDK) — 14 resolved (13% of all resolved reports — most picked-over repo in scope, deprioritize unless a very fresh angle)
- `github.com/vercel/turborepo` — 4 resolved
- `github.com/vercel/swr` — 0 resolved
- `github.com/vercel/ms` (tiny time-parsing lib) — 0 resolved, small surface, easy full-review candidate
- `github.com/vercel/flags` — 1 resolved
- `github.com/vercel/eve` — 0 resolved, **scope added Aug 3, 2026 — brand new, ~11 days old, essentially unhunted**
- `github.com/vercel/chat` — 0 resolved, **scope added Aug 3, 2026 — brand new, essentially unhunted, name suggests it may handle real user conversation data (worth checking for the "real third-party data" angle)**
- `github.com/vercel/async-sema` — 0 resolved
- `github.com/vercel-labs/skills` — 2 resolved
- `github.com/vercel-labs/agent-skills` — 0 resolved
- `github.com/sveltejs/svelte` — 6 resolved
- `github.com/nuxt/nuxt` — 7 resolved
- `github.com/nitrojs/nitro` — 1 resolved

**How to apply:** prioritize `vercel/eve` and `vercel/chat` first (newest scope, zero resolved reports, essentially unhunted — same "under-scrutinized" methodology that worked for the Kubernetes git-sync finding and the Shopify themekit finding). Deprioritize `vercel/ai` (14 resolved = most picked over). `vercel/ms` is small enough for a genuinely complete read if other leads dry up.

Session pivoted here 2026-08-14 mid-Shopify-hunt ("busca aqui mejor, ya regresaremos" — Shopify paused, not abandoned; resume via [[project_shopify_hackerone]] when told to go back). Standing bar carried over: no hypothesis, real executed PoC, prioritize genuine third-party data/impact over self-contained code-quality issues.
