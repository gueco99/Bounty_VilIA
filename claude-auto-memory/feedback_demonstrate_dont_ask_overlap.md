---
name: feedback-demonstrate-dont-ask-overlap
description: "When unsure whether a finding overlaps too much with an already-submitted one, build a real PoC proving impact and submit directly rather than asking the user a framing/overlap question"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

When a candidate finding shares a code location or root cause with an
already-submitted report, don't stop to ask the user whether it's worth
reporting separately. Verify it has real, demonstrable impact (a working
PoC against the real, unmodified code — not just static analysis) and, if
it holds up, submit it directly.

**Why:** confirmed 2026-08-04 on sodapy — raised a legitimate-sounding
concern via AskUserQuestion about a finding (`assetId`/`blobId` unescaped
in `download_attachments`'s download URL) overlapping with an
already-submitted report (#3494, same function, same untrusted metadata
source). The user declined the question and said, in effect: it has
impact, prove it properly, and if so just send it (report_id 3522). This
extends [[feedback_autonomous_hunting]] — the "don't pause for
confirmation mid-pipeline" principle applies not just to whether to keep
hunting, but specifically to procedural/framing doubts about whether a
finding is "different enough" from a prior one.

**How to apply:** when a new lead overlaps with a submitted finding,
default to: (1) build the strongest real PoC you can (live code, real
network/filesystem effects where applicable, not mocked-away impact
claims), (2) if the PoC demonstrates genuine additional impact or a
genuinely separate code location whose fix wouldn't be covered by the
earlier report's suggested fix, submit it, (3) only ask the user first if
the PoC comes back weak/inconclusive or the overlap is so total that a
new report would be pure duplication with no new fix surface.
