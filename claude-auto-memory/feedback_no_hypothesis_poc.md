---
name: feedback-no-hypothesis-poc
description: "User requires fully demonstrated, non-hypothetical PoCs for a finding to be considered submittable — formal/statistical proof of a code-level flaw is not enough on its own if real-world exploitability (actual theft/impact) can't be shown"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 593c4a64-2b76-406e-93dc-712e72e5abad
---

For a report to be considered valid/submittable, the PoC must be perfect and never rely on hypothesis. Stated directly: "para que sea reportes validos necesito tener todo el poc perfecto nunca nada de hipotesis" (2026-08-14, during the Privy shamir-secret-sharing investigation).

**Why:** surfaced when investigating a real, confirmed, currently-shipping cryptographic regression in Privy's shamir-secret-sharing library — the code-level flaw was proven beyond doubt (checksum-verified live code, statistical PoC matching theory almost exactly), but full practical exploitability (e.g. actual private key theft) could not be demonstrated, since the leak is per-byte/independent and doesn't let an attacker brute-force the rest of a real key even with a fast verification oracle. The user's response was to not treat this as submission-ready and to ask whether pivoting to a different target made more sense.

**How to apply:** when a finding has strong formal/theoretical backing (matches a known vuln class, passes statistical validation, code is provably unpatched) but the chain from "flaw exists" to "attacker gets something real" has a gap (can't fully brute-force, can't reach raw production material, requires an unverifiable assumption), flag that gap explicitly and proactively rather than writing the report anyway. Offer the user the choice: keep digging for the missing link, accept a downgraded/more honest framing (e.g. documentation-gap angle instead of critical-vuln angle), or pivot to a target/finding where full end-to-end impact is provable — matches the standard already set on Keycloak Operator (video-recorded, credential-in-hand PoC) and should be the bar for future targets too. See [[project_privy_hackerone]] for the concrete case this came from.
