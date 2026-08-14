---
name: feedback-no-meta-references-in-reports
description: "Never reference the user's instructions/requests inside a vulnerability report — write as if the hacker (user) found and investigated it independently"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

Never write phrases like "como me pediste", "siguiendo tu instrucción de revisar
esto de nuevo", or any other reference to the user having asked/directed the
investigation, inside a report's technical sections (Detalle técnico, Prueba de
concepto, etc.).

**Why:** the user said explicitly (2026-08-01, cogny #3292) this doesn't sound
professional — reports must read as if the hacker (the user, "gueco") independently
decided to investigate and found the issue themselves. Referencing "you told me to
check X" breaks that illusion and looks unprofessional to whoever triages the
report on the platform side.

**How to apply:** when drafting any report (Secur0 or otherwise), narrate the
investigation motivation in first-person-researcher terms ("revisando el fix
desplegado para X, se detectó que...", "al auditar de nuevo el mismo endpoint...")
never in terms of a conversation that happened with an assistant. This applies
regardless of what actually triggered the investigation (a user prompt, a dashboard
notification, re-reading old code) — the OUTPUT report must never leak that meta
context. Caught late: report #3292 ("cogny-pdf-ssrf-fix-bypass-redirect") went out
with a direct quote of the user's chat message ("vamos a ver si han dejado
rastros...") still in the Detalle técnico section before this rule was learned —
worth a mental note that already-submitted report if the user ever wants it edited
via the web UI (no PATCH endpoint exists in [[reference_secur0_api_pipeline]] to fix
it via the API).
