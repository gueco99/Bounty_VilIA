---
name: feedback-dont-test-via-live-api
description: "never debug a submission error by sending isolated/dummy test payloads to a real bug bounty program's live report-creation API"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ff7451f9-ed99-4be8-8d13-3103f0c4f6ba
---

Never use a program's real `create_report`/report-submission API to "isolate" a bug in the
submission tooling by sending minimal/dummy/garbage content, even under a clearly-labeled test
title. If a real report submission fails (e.g. HTTP 500), debug locally first: inspect the
parsed fields, diff against previously-successful reports, read the tool's own parsing logic
(e.g. [[reference_secur0_api_pipeline]]'s known bugs section) for structural differences —
only resubmit the real, complete, well-written report once a concrete fix is identified.

**Why:** during script-server hunting (2026-07-31), a `report_secur0.md` submission 500'd. While
bisecting which field caused it, 3 throwaway/dummy reports (titles like "isolation test impact
field") were created for real on the live VDP program before the user caught it and told me to
stop. The user's explicit correction: "antes de enviar un reporte, asegurate de que el reporte
este bien redactado. no envies cualquier cosa" (before sending a report, make sure it's well
written — don't send just anything). This applies even when the *intent* is debugging, not a
real finding — the live API doesn't know the difference, and every submission is real, visible
noise on someone else's program.

**How to apply:** when `create_report`/`submit_report_from_file` fails, do NOT call
`create_report` again with synthetic/minimal content to test a hypothesis. Instead: read
`parse_report_markdown`'s actual output locally, compare field-by-field against prior successful
submissions' structure (e.g. number of fenced code blocks, section formatting), fix the
suspected cause, and only call the live submit path again for the real, final, complete report
— treat every live call as a real submission, never as a scratch/test environment.
