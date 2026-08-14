---
name: feedback_secur0_title_constraints
description: "Secur0's report title field has a hard 100-character cap and rejects special characters"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 34489275-58f5-410f-8b5b-40d13626490b
---

The `title` field on Secur0's `/api/reports/create` endpoint rejects (HTTP 400
`{"title":["invalid_format"]}`) any value over 100 characters, and rejects special characters
(backticks, em/en dashes, likely other non-plain punctuation).

**Why:** confirmed directly by the user after `tools/secur0_api.py submit` failed on the
add-and-commit RCE report's title (143 chars, contained backticks and an em dash).

**How to apply:** when drafting any `report_secur0.md`'s `## Title` line, keep it under 100
plain-ASCII characters — no backticks around code identifiers, no em/en dashes, no smart quotes.
Prefer plain hyphens and straight quotes if punctuation is unavoidable. Check length before
attempting `secur0_api.py submit`, since [[feedback_dont_test_via_live_api]] means the live
create-report endpoint shouldn't be used to trial-and-error field validation.
