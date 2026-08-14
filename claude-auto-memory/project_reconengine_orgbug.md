---
name: project-reconengine-orgbug
description: "Known bug in tools/recon_engine.sh Phase 8 — CI/CD org auto-detect scans unrelated third-party GitHub orgs, out-of-scope risk. Not yet fixed."
metadata: 
  node_type: memory
  type: project
  originSessionId: d7cba4a0-4d2a-40ea-82f0-a45d03eac667
---

`tools/recon_engine.sh` Phase 8 (CI/CD Workflow Scan, ~line 572-592) auto-detects GitHub orgs to scan by grepping any `github.com/<org>` string out of crawled URLs/JS/httpx output, with no relevance filter, then runs `sisakulint` (live GitHub API calls) against every org found.

**Confirmed impact:** during the [[project_lasrozasinnova]] recon run (2026-07-18), this fired against `org:supabase` and `org:VincentGarreau` — both unrelated to the target, almost certainly picked up from a footer badge or a JS library credit (e.g. particles.js) on the target site. Neither org has any relation to Las Rozas Innova's scope.

**Why it matters:** violates Critical Rule 1 (never touch an out-of-scope asset) — CLAUDE.md governs this repo's plugin behavior, and the recon tool itself is silently expanding beyond target scope on every run that has a GitHub link anywhere in crawled content. This has likely happened on other past hunts without being noticed, since CI/CD findings=0 gets treated as a clean signal rather than "we scanned the wrong org."

**How to apply:** user deferred the fix (2026-07-18, mid Las Rozas Innova hunt) to keep hunting momentum — do NOT fix proactively mid-hunt, but raise it again when there's a natural lull, or ask before starting the next `/recon` run whether to patch it first. Proposed fix (not yet implemented): restrict Phase 8 org auto-detect to orgs whose name contains the target's keyword (derived from `$TARGET`), or default to log-only (list detected orgs, don't scan) unless the org is explicitly allowlisted.
