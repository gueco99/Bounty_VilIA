---
name: project-prowler
description: "Prowler (github.com/Prowler-cloud/prowler) hunt state — Django/Next.js multi-tenant cloud-security SaaS + Python CLI/SDK scan engine, CVE-eligible VDP. api/ backend reviewed clean (RLS/tenant isolation, secrets, Jira/Lighthouse SSRF all solid). 1 finding SUBMITTED (report_id 3729): CSV/compliance report outputs write cloud resource names/tags unescaped across 3 files (main CSV + all compliance CSV exports), real CSV Formula injection (CWE-1236), PoC'd against real unmodified code."
metadata:
  node_type: memory
  type: project
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

Target: `github.com/Prowler-cloud/prowler` — large monorepo: `prowler/`
(Python CLI/SDK, the actual cloud-security scan engine for AWS/Azure/GCP/K8s),
`api/` (Django REST backend for "Prowler App", the SaaS product, multi-tenant),
`ui/` (Next.js frontend), `mcp_server/`, `dashboard/`. CVE-eligible VDP.

**Areas reviewed in `api/` (Django backend) — all solid, no findings:**
- **Tenant isolation**: real Postgres Row-Level-Security (`api/rls.py`,
  `FORCE ROW LEVEL SECURITY` + policy keyed on `current_setting('api.tenant_id')`).
  Traced the full trust chain: JWT issuance (`generate_tokens`) and tenant
  switching (`TokenSwitchTenantSerializer`) both gate on
  `user.is_member_of_tenant(tenant_id)` before minting a token; the DRF
  view layer (`BaseRLSViewSet.initial()`) sources the RLS session var ONLY
  from `request.auth.get("tenant_id")` (the signed JWT claim), never from
  client-supplied params. Tenant deletion view correctly `OWNER`-gated.
- **Provider credential storage** (`ProviderSecretViewSet`/`ProviderSecretSerializer`):
  the `secret` field is `write_only` on create/update serializers and
  absent entirely from the read serializer — plaintext AWS/Azure/GCP
  credentials never come back out of the API.
- **Jira integration SSRF**: self-hosted/basic-auth domain field is
  validated via a strict `ATLASSIAN_SITE_NAME_REGEX` (`\A[a-zA-Z0-9][a-zA-Z0-9-]*\Z`,
  fullmatch) and always interpolated as `https://{domain}.atlassian.net/...`
  — no way to point it at an arbitrary host.
- **Lighthouse (bring-your-own-LLM feature) SSRF**: `tasks/jobs/lighthouse_providers.py`
  + `api/validators.py` — genuinely the best SSRF defense seen in this
  entire session. Custom httpx transport (`_LighthouseOpenAICompatibleHTTPTransport`)
  resolves DNS once, validates every resolved IP is `is_global` (Python
  ipaddress), connects directly to the validated IP (not a re-resolved
  hostname — correct anti-DNS-rebinding pattern), disables redirect
  following, and explicitly handles IPv4-mapped/6to4/NAT64 IPv6 transition
  addresses (a bypass class most SSRF filters miss entirely). Blocks known
  metadata hostnames/IPs (169.254.169.254, fd00:ec2::254,
  metadata.google.internal, etc.) plus an operator-only allowlist escape
  hatch (env-configured, not attacker-reachable).

**Conclusion:** the `api/` backend shows real security engineering
maturity — consistent with an 11/20 accepted-report rate (real bugs exist
but the basics are covered). Did not find a concrete exploitable issue
after a thorough pass.

**Finding #1 DRAFTED, PARKED (not submitted — save-don't-submit mode,
[[feedback_hunt_save_dont_submit_mode]]): CSV Formula/Injection (CWE-1236)
in the CSV report output.** `prowler/lib/outputs/csv/csv.py`'s
`CSV.batch_write_data_to_file()` writes finding fields (RESOURCE_NAME,
RESOURCE_TAGS, ACCOUNT_TAGS, RESOURCE_DETAILS, ...) straight from
`resource.name` (cloud-provider-returned, settable by anyone with
tag/rename permission in the SCANNED account — `finding.py:626`) into CSV
cells via stdlib `csv.DictWriter`, with zero neutralization of a leading
`=`/`+`/`-`/`@`. `csv.DictWriter`'s RFC4180 quoting is pure CSV-syntax
escaping and does NOT defang spreadsheet formula interpretation — proven
by round-tripping the real output back through `csv.DictReader` (same
unescaping a spreadsheet app performs) and confirming the payload
survives 100% intact. Confirmed via direct comparison that HTML output
(`html.py`) DOES correctly wrap the same fields in `markupsafe.escape()`
— so this is specifically a CSV-path gap, not a project-wide unawareness
of the risk. Real PoC built and run against Prowler's own unmodified
`CSV`/`Finding` classes (no reimplementation) — took real effort to set
up (missing deps chain: pydantic v1, requests, pyyaml, packaging,
jsonschema, colorama; hit a `/tmp` tmpfs full-disk error using the
default venv location, fixed by creating the venv on the real disk
instead under the findings dir). Draft CVSS 4.0:
`AV:L/AC:L/AT:P/PR:L/UI:P/VC:H/VI:L/VA:N` — High. No spreadsheet app
available in this sandbox to screenshot live formula execution — flagged
that explicitly rather than claiming a rendering screenshot I don't have.
Files: `findings/dia3/prowler-csv-injection/` (report.md,
poc/poc_csv_injection.py, poc/run_output.txt, poc/requirements.txt).
**Scope broadened after further digging**: confirmed the identical
missing-escaping root cause (raw Finding data → `csv.DictWriter`, no
escaping helper anywhere in `prowler/lib/outputs/`) also affects
`compliance/compliance_output.py` (the SHARED base class for every
CIS/ENS/C5/ISO27001/KISA-ISMSP/MITRE-ATT&CK/etc. compliance CSV export —
~20+ framework modules all affected) and
`compliance/universal/universal_output.py` — added to the same report as
"Additional scope confirmed" rather than separate reports, since it's the
same root cause and same fix, per [[feedback_report_merge_rule]].
Checked for other common Python vuln patterns across the whole repo
(unsafe `yaml.load`, `eval`/`exec`, `subprocess` with `shell=True`,
`pickle.load`) — all clean, none found.

**M365 PowerShell integration reviewed, one code smell NOT written up
(likely non-exploitable):** `prowler/lib/powershell/powershell.py`'s
`PowerShellSession.execute()` writes the raw command string directly to
a persistent PowerShell subprocess's stdin with NO enforced sanitization
— a `sanitize()` helper exists but is opt-in per caller, not applied
inside `execute()` itself. Audited `prowler/providers/m365/lib/powershell/m365_powershell.py`
(~1192 lines, ~40 `.execute()` call sites) in full: the vast majority are
fixed/parameterless cmdlets (safe by construction). Found ONE real gap —
`init_credential()` embeds `credentials.tenant_domains[0]` into a
DOUBLE-quoted PowerShell string (`$tenantDomain = "{...}"`, which DOES
support variable/subexpression expansion) with NO `sanitize()` call,
inconsistent with the SAME function's careful single-quoting +
`sanitize()`/apostrophe-doubling treatment of `client_id`/`tenant_id`/
`client_secret` a few lines above. Traced `tenant_domains` back to a live
Microsoft Graph "Domains" API response (`identity.tenant_domains.append(domain.id)`,
`m365_provider.py:1002`) — i.e. genuinely sourced from the SCANNED
tenant's own config, not pure self-input, which would make this a real
cross-trust-boundary PowerShell injection IF exploitable. Did NOT write
this up: Microsoft Graph domain names are constrained to valid DNS
hostname syntax (letters/digits/hyphens/dots only), which structurally
excludes the `$`, `(`, `)`, `"` characters needed for PowerShell
double-quote-string injection — concluded likely not practically
exploitable without live M365 tenant access to test DNS-validation edge
cases I couldn't verify statically. Also checked the one M365 fixer using
`.execute()` (`exchange_organization_delicensing_resiliency_enabled_fixer.py`)
— no parameter interpolation, safe.

**Not yet reviewed:** the rest of `prowler/providers/` (AWS/Azure/GCP/K8s
service modules — the actual check logic, ~30+ provider directories),
other output formats (JSON/OCSF, ASFF, compliance-specific tabular
outputs that reuse the same unescaped `unroll_dict`/`unroll_list`
helpers — worth checking for the SAME CSV-injection-adjacent issue if
they also feed a spreadsheet-consumed format), `ui/` (Next.js frontend),
`mcp_server/`. Session paused here awaiting user direction.
