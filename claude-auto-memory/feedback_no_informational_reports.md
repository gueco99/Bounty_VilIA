---
name: feedback-no-informational-reports
description: "Don't write up or submit findings that score pure Informational under CVSS 4.0 (no real exploitability/impact metric), even if reproducible."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46360d1a-7024-4f70-b01a-c28082c84e12
---

Do not draft or submit a report for a finding that has no real impact under CVSS 4.0 (i.e. it would score Informational — no meaningful Vulnerable System or Subsequent System impact), unless it can be chained with something else to produce real impact.

**Why:** Confirmed on [[project_living4football]] with a user-enumeration finding (`/recuperar-password`, email exists vs doesn't). It was reproducible and real, but the user pointed out triage would score it Informational under CVSS 4.0 with no chain available (brute-force was rate-limited, no OTP leak found), so it wasn't worth reporting. The user explicitly said: from now on, if what you find is informational and has no CVSS 4.0 impact, don't report it.

**How to apply:** Before proposing to draft/write up any finding, mentally score it under CVSS 4.0 first (exploitability + vulnerable-system impact + subsequent-system impact). If it lands on pure Informational with no plausible chain, say so and stop — don't offer to write it up "just in case" or for triager goodwill. Actively look for a chain (as was done here: enumeration → OTP brute-force attempt, OTP leak check) before concluding it's dead; only park it once the chain attempt genuinely comes up empty. This complements [[feedback_verify_before_confirming]] (verify impact) and [[feedback_verify_against_live_target]] (verify against live target) — this rule is specifically about the severity bar for deciding whether to write the report at all, not about verification correctness.

**Reconfirmed on [[project_go_ios]] (2026-07-28):** user explicitly repeated "solo quiero lo que tenga criticidad. asegurate siempre" after two findings this session got parked post-hoc (TSS TLS MITM — device-side crypto verification neutralized the MITM; InterfaceToStringSlice panic — CLI-only, no persistent/shared process, attacker gains nothing the operator wasn't already risking). The pattern in both: initially looked plausible, but tracing the FULL consequence chain (what does the device-side verification actually check? what's the blast radius of a CLI-only one-shot crash vs. a REST-reachable one?) downgraded them. Apply that same full-chain trace *before* drafting, not after — the standing instruction is now to front-load this check rather than let the user catch it in review.

**Reconfirmed and SUBMITTED anyway on [[project_chezmoi]] (2026-07-31, finding #5, report_id
3108):** drafted and submitted a decompression-bomb finding (unbounded `io.ReadAll` on
archive-external download/extraction) *quickly*, specifically to test a new submission
pipeline end-to-end, and skipped the usual full-chain impact interrogation because "it's just
a pipeline test." On the user asking "does this have impact?" afterward, honest
re-examination showed it's weak: `chezmoi apply` is a local, one-shot, user-invoked CLI
command — worst case is that single invocation OOMs and the user re-runs it after fixing their
config. No persistence, no effect on other users/processes. Compare to this same program's
other 4 findings (RCE, arbitrary file write via path traversal, arbitrary file read via
symlink, credential leak in logs) — all leave a lasting, concrete compromise; this one
doesn't. Assigned VA:H in the CVSS when VA:L was more honest. **The lesson: "I'm just testing
the pipeline/mechanism" is not an exception to this rule — the pipeline-test framing is
exactly the condition under which the impact check gets skipped, so it needs MORE deliberate
attention then, not less.** User's instruction afterward: "para los proximos, piensalo bien
antes. no quiero nada que pueda ser informativo" — apply the full CVSS-scoring gut-check
*every* time a report gets drafted, with zero exception for test/demo/pipeline-validation
submissions.

**Reconfirmed on [[project_script_server]] (2026-07-31):** a log-injection finding (forging
`user_id` in a script's own execution-history record via an unescaped newline in a parameter
value) looked real — confirmed live, with the actual access-control function affected — but the
user's one-line pushback ("si expongo mis cosas... si el atacante es el afectado es una tonteria
no?") exposed that the "impact" only ever surfaces the ATTACKER'S OWN data to a victim, never the
reverse; no chain existed where the attacker gains anything they didn't already have. The drafted
report was deleted, not submitted. Lesson reinforced: always ask "who ends up with access to
whose data" as the final gut-check before submitting, even after a technically-real bug is
confirmed with a working live PoC — technical correctness and real security impact are separate
questions, and a plausible-looking CVSS string (e.g. VI:H) can still be scoring the wrong
direction of harm.

**Confirmed post-hoc as Informational on [[project_codeweaver]] (#3039, seen on dashboard
2026-08-05):** the extension-backtick fence-break finding (a crafted file extension makes a
Markdown code-fence's opening delimiter longer than its closing one, swallowing every
subsequent file's header/content into one inert code block when the generated dump is
*rendered*) sat "Abierto" with CVSS still blank — informational in practice, despite a rock-solid
PoC (verified against the project's own pinned goldmark renderer, not just spec reasoning). Same
program's *sibling* finding — crafted extension breaks OUT of a fence to inject a fake Markdown
heading/prompt-injection text — WAS accepted with real severity. The distinguishing factor:
injecting fake structure gives an attacker a concrete, demonstrable consequence (forged content a
reviewer/LLM treats as real); suppressing/hiding real structure only produces "a reviewer *might*
overlook a file" — a plausible but soft, unfalsifiable harm with no concrete confidentiality/
integrity/availability consequence on its own. **Lesson: within the same vulnerability class
(rendered-Markdown structure manipulation), injecting fake content and hiding real content are
NOT symmetric in reportability — the injection direction chains to impact far more easily than
the suppression direction, which needs its own separate, concrete chain (e.g., proof a hidden
file actually caused a bad security decision) to clear the bar.**
