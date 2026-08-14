---
name: feedback-demonstrable-impact-third-party-filter
description: "Before submitting a parked/drafted finding, filter for demonstrable security impact AND criticality to a third party, not just a real bug"
metadata:
  node_type: memory
  type: feedback
  originSessionId: b048d633-40a1-4ca7-b923-94baec60b234
---

When reviewing a backlog of parked findings for submission, the user added a second gate beyond
"is this a real bug": **hay que tener en cuenta que tenga impacto de seguridad demostrable y que
tenga criticidad a un tercero si fuera posible** — it must have demonstrable security impact AND
(ideally) affect a third party, not just the finder's own local environment.

**Why:** extends [[feedback_needs_real_victim]] (no plausible attacker path = not reportable) and
[[feedback_reproducibility_not_severity]] (reproducible ≠ automatically a security finding) — this
adds an explicit pre-submission filter pass across a batch of findings, not just a per-finding
check during investigation. Said right after reviewing a 9-finding backlog across 5 parked
programs (Peercoin, Prowler, Raylib, Ecommerce Template, CrystalReportsRunner) accumulated during
[[feedback_hunt_save_dont_submit_mode]].

**How to apply:** when triaging a batch of drafted-but-unsubmitted findings before sending, rank/
flag each by two axes: (1) is the security impact actually demonstrated (live PoC / compiled crash
/ confirmed data leak) vs. only argued from source review or platform documentation; (2) does the
vulnerable path have a real third party who is harmed (another user, a customer, any public node
operator) vs. only the local/self-inflicted case. Findings strong on both axes (e.g. an
unauthenticated remote crash affecting any node, or unauthenticated PII disclosure to any visitor)
are safe to submit as-is. Findings weak on the "demonstrable" axis (no live environment to verify
against, e.g. CrystalReportsRunner's Windows-only named-pipe findings tested only via source +
dependency review, no actual Windows box) should be flagged explicitly and confirmed with the user
before submitting, not submitted blind just because [[feedback_submit_everything_now]] is in
effect generally — that policy still assumes each finding already cleared the impact bar.
