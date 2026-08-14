---
name: reference-h1-technique-corpus
description: Local corpus of 230+ full disclosed HackerOne reports (real exploitation write-ups) + the fixed/extended HackerOne MCP tool that built it
metadata: 
  node_type: memory
  type: reference
  originSessionId: ff7451f9-ed99-4be8-8d13-3103f0c4f6ba
---

`memory/h1_technique_corpus/*.jsonl` holds 230 unique, real disclosed HackerOne reports with FULL write-ups (summary, code, steps to reproduce, PoC, impact, suggested fix) — one JSON object per line, split into 20 files by vuln class (ssrf.jsonl, idor.jsonl, xss.jsonl, sql_injection.jsonl, rce.jsonl, race_condition.jsonl, ssti.jsonl, xxe.jsonl, csrf.jsonl, open_redirect.jsonl, graphql.jsonl, jwt.jsonl, oauth.jsonl, privilege_escalation.jsonl, business_logic.jsonl, access_control.jsonl, authentication_bypass.jsonl, path_traversal.jsonl, deserialization.jsonl, prototype_pollution.jsonl). Grep these for real technique examples before hunting a given vuln class — much richer than YesWeHack, which only exposes CWE+hunter+date, no content ([[project_boomingmusic]] session established this contrast 2026-08-05).

**Why:** user asked to be "fed" with published bug bounty reports for new exploitation techniques; `mcp/hackerone-mcp/server.py`'s `search_disclosed_reports()` was completely broken (HackerOne retired the `hacktivity_items` GraphQL field it used) and never fetched full report bodies even when working — fixed both, then built the corpus so future hunts don't need manual browser research each time.

**How to apply:** grow the corpus anytime with `python3 tools/h1_technique_corpus.py --keyword "<vuln class>" --limit 20` (safe to re-run, skips already-fetched IDs by report id) or `--sweep` to redo the full default 20-category pass. Query a single report directly with `python3 mcp/hackerone-mcp/server.py report <id>`.

Key technical facts learned reverse-engineering hackerone.com's frontend (network interception via Chrome MCP, no GraphQL introspection available — `__schema` is blocked):
- Hacktivity search now goes through `search(index: CompleteHacktivityReportIndex, query_string, from, size, sort)`, not the old `hacktivity_items` field.
- The query-string search syntax (`disclosed:true`, `cwe:`, `severity_rating:`, `team:`, `cve_ids:`, `substate:`, `disclosed_at:`, `total_awarded_amount:`) requires filters joined with literal `" AND "`/`" OR "` (all caps) — a bare space between terms is silently ignored by HackerOne's own search (reproduced this exact quirk live on hackerone.com itself, not just in the local tool).
- The full markdown report body (`vulnerability_information`) is NOT reachable via GraphQL at all — the report page fetches it via a plain unauthenticated REST GET to `https://hackerone.com/reports/<id>.json`, which also has `attachments[].expiring_url` (time-limited S3 links to the reporter's actual PoC files/screenshots).
- `get_program_stats()` was also broken (`default_currency`/`average_time_to_bounty_awarded`/`average_time_to_first_program_response` all removed from the `Team` GraphQL type at some point) — fixed with the currently-valid field names; the two response-time metrics have no direct replacement and were dropped from the tool's output.
