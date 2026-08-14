---
name: feedback-check-dashboard-not-memory
description: "Before treating a finding as unsubmitted, unconfirmed, or still-open, check the actual Secur0/platform dashboard — memory notes about submission status go stale fast and can't be trusted on their own."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46360d1a-7024-4f70-b01a-c28082c84e12
---

Memory files can say "drafted, submission status unconfirmed" about a finding that was actually
submitted (and even accepted) in a session with no surviving transcript. Don't take that note as
current fact — it's a snapshot from whenever it was last written, not a live status.

**Why:** On [[project_shishang_app]] (2026-07-28), spent a large chunk of a session
re-investigating, re-testing, and building fresh PoC evidence (browser overlay, Burp proxy
replay, email-collision testing, a staff-picker escalation theory) for a finding
(`shishang-profile-consent-fields-forgeable`) that turned out to already be submitted and sitting
Open on the dashboard as #2447 — from a prior session not present in the current transcript or
memory. Checking `https://app.secur0.com/reports` (filter by company) at the start of that
detour would have shown this in under a minute. Same story for most of the rest of that target's
"STATUS CHECKLIST" — 10 of 13 items were already submitted (open/accepted/duplicate), only 2 were
genuinely never sent.

**How to apply:** before spending nontrivial time deciding "should we submit this" or re-proving
a finding "unconfirmed" in memory, check the actual platform dashboard for that program first —
it takes seconds and is authoritative in a way memory notes never can be. This applies any time a
memory file's "submission status unconfirmed" note is more than a session or two old, or when
resuming a target after a gap. Don't assume a quiet memory file means quiet real-world status.
