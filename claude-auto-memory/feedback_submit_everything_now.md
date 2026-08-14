---
name: feedback_submit_everything_now
description: "2026-08-08 — user ended save-don't-submit mode; submit every finding going forward, no more parking"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 34489275-58f5-410f-8b5b-40d13626490b
---

The user ended [[feedback_hunt_save_dont_submit_mode]]: "a partir ahora quiero que envies todo lo
que encuentres incluso este ultimo" — explicitly including the add-and-commit RCE finding that
was sitting parked at the time.

**Why:** they no longer want a batch of held-back drafts; they want each finding submitted as
soon as it's validated, matching the normal single-target rhythm ([[feedback_autonomous_hunting]]
/ [[feedback_demonstrate_dont_ask_overlap]] already establish "act, don't ask" for the
investigation side — this extends the same posture to the submission step).

**How to apply:** once a finding passes the usual bar (real demonstrated impact, not
informational — [[feedback_no_informational_reports]] still applies), submit it via
`tools/secur0_api.py submit` right away instead of just writing it to `findings/dia2/` and
stopping. Don't ask "¿lo envío?" per finding anymore — that checkpoint is gone unless the user
reintroduces it. Still respect all other submission-safety memories: check title length/format
first ([[feedback_secur0_title_constraints]]), don't debug the live create-report endpoint with
throwaway payloads ([[feedback_dont_test_via_live_api]]), verify against the live target first
([[feedback_verify_against_live_target]]).
