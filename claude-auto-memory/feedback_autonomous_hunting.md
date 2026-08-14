---
name: feedback-autonomous-hunting
description: "User wants autonomous execution during bug bounty hunting sessions, not step-by-step confirmation"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: eff95342-ff4b-4097-ac00-66e8b9e8a03a
---

During active bug bounty hunting (recon → hunt → validate → report), the user wants me to proceed autonomously through the pipeline without pausing to ask "should I continue?" at each step.

**Why:** Said explicitly ("no vuelvas a preguntar, tu hazlo hasta que encontremos algo") while I was running recon on api.codacy.com/app.codacy.com (HackerOne Codacy program) and kept offering to run the next tool rather than just running it.

**How to apply:** Once a target/program is confirmed in scope and the user has said to hunt, chain recon → vuln_scanner → candidate review → active testing without intermediate check-ins. Still stop and surface findings when something concrete turns up, and still respect hard safety boundaries (scope, destructive actions, credential attacks needing human go/no-go per [[credential-attack]] rules) — the "don't ask" applies to hunting pipeline progression, not to those guardrails.

**Update (same session, later):** User restated even more broadly: "acepto todo lo de esta sesion no es necesario que me pidas confirmacion, a no ser que me afecte negativamente" — i.e. proceed without asking unless an action would negatively affect the *user themselves* (their accounts, their legal/program standing, their machine). This still does not license skipping ethical/program-rule boundaries that protect *third parties* (real end-user PII, destructive actions against production systems, third-party ToS violations like automating account signup) — those aren't about the user's own downside, they're independent guardrails. Distinguish "don't ask about routine next steps" from "don't ask even about things that risk harming someone else or breaking program rules."
