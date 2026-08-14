---
name: feedback_needs_real_victim
description: "A DoS/impact finding needs a plausible attacker-controlled data-flow into the vulnerable input, not just \"if someone puts a weird value there\" — self-inflicted isn't reportable"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 34489275-58f5-410f-8b5b-40d13626490b
---

Before drafting/submitting any finding that depends on "if this input receives attacker-influenced
data," check whether there's a *realistic* path for an external attacker to actually control that
specific input — not just that the input exists and *some* value could theoretically be
attacker-influenced. If the only realistic way the dangerous value gets there is the workflow
author (or the person who'd be harmed) typing it in themselves, there's no victim distinct from
the person taking the risky action, and it isn't a security finding.

**Why:** caught live on add-and-commit: I drafted a DoS report (js-yaml exponential-parse CVE via
the action's `add`/`remove` inputs) using the same "if a workflow routes less-trusted data into
this input" framing that worked for the RCE finding (`pull`/`fetch`/`push`, report #3919 — where
that framing is genuinely plausible, since branch/tag/ref values are commonly computed from
dynamic/PR-derived data in real workflows). But `add`/`remove` are just static file-glob patterns
virtually always written directly by the workflow author — there's no realistic way an external
attacker controls that value. The user caught it immediately: "pero hay victima? o solo yo? si es
self no me interesa." Killed the draft, didn't submit.

**How to apply:** for every "requires a consuming workflow to route untrusted data into input X"
precondition, ask concretely: *who* would populate X with attacker-reachable data, and *why* would
they do that for this specific input in realistic usage? If the answer is "no one would, except by
deliberately hurting themselves," it's self-DoS/self-inflicted — kill it, don't draft a report.
This is a sharper version of the precondition-honesty already covered by
[[feedback_never_assume_confirm_always]] and the "no informational" bar in
[[feedback_no_informational_reports]] — a real CVE with a real exponential blowup can still fail
this bar if it has no plausible victim distinct from the actor triggering it.
