---
name: project-naxusai
description: "NaxusAI VDP on Secur0 — AI-driven autonomous vulnerability-hunting SaaS ('Mythos-style'), fresh target (0 reports), Safe Harbor."
metadata:
  node_type: memory
  type: project
  originSessionId: 46360d1a-7024-4f70-b01a-c28082c84e12
---

Program: **NaxusAI**, VDP on Secur0, Safe Harbor. Captured 2026-07-29, 30 days remaining.
0 total reports, 0 accepted — genuinely fresh/untouched target.

**What it is:** "Mythos-style autonomous zero-day hunting" — static and dynamic agents that find
and verify vulnerabilities across code and infrastructure, producing PoCs and remediations. An
AI-security/AppSec-tooling SaaS company (ironic target for a security researcher).

**In scope:** `naxusai.com`, `*.naxusai.com` — web/infra target, not a source-code repo (unlike
the prior go-ios engagement). Standard recon pipeline applies (subdomain enum, live host
discovery, crawling, nuclei).

**Required participation headers (must be sent on every test request):**
- Email alias: `[handle]@imnotahacker.com` → use `gueco@imnotahacker.com` per [[user_h1_username]]
- User-Agent: `Secur0-gueco-[user-agent]`
- Header: `X-Secur0-Username: gueco`

**Program rules worth remembering during testing:**
- No compensation/bounty — pure VDP, Safe Harbor only.
- Explicit "always" list to respect: minimize data access on sensitive-data findings, stop
  and report immediately if real user PII/PHI/payment data is encountered, proportionality
  (no more exploitation than needed to prove the bug, no availability disruption).
- Never-in-scope list is the program's STANDARD exclusion set (matches this toolkit's own
  `skills/security-arsenal` always-rejected list closely): theoretical/self-XSS/self-DoS,
  clickjacking without sensitive action, CSRF without sensitive action, permissive CORS without
  demonstrated impact, version/error disclosure, CSV injection, open redirect without further
  impact, SSL/TLS config, missing SSL pinning, cookie flags, CSP config, SPF/DKIM/DMARC, most
  rate-limiting issues.
- No password/credential brute-forcing allowed per the explicit prohibited-actions list
  ("robo de contraseñas o ataques de fuerza bruta") — this RULES OUT the credential-attack
  pipeline (wordlist-gen/osint-employees/spray) for this program specifically; don't suggest it.

**How to apply:** standard `/recon naxusai.com` → lead_board ingest → `/hunt` workflow. No prior
findings, no prior recon — this is a cold start.
