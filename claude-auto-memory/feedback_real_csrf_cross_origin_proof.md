---
name: feedback-real-csrf-cross-origin-proof
description: "Never claim a CSRF chain/exploit works from a same-origin fetch() test — build a real cross-origin PoC or don't claim it."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46360d1a-7024-4f70-b01a-c28082c84e12
---

A same-origin `fetch(url, {credentials:'include'})` executed from a tab already on the target domain proves nothing about CSRF exploitability — it only proves the endpoint works when you're logged in and already there. It is not evidence a third party can trigger the action against a victim.

**Why:** On [[project_gestionominegocio]], claimed the `presupuesto-double-conversion` finding chains with the already-reported CSRF finding to make it exploitable against a victim, based only on same-origin fetch tests. The user called it out directly: "pero estoy suponiendo, si no hay pruebas reales para encadenar no me vale" (I'm assuming — if there's no real proof to chain it, it's no good to me). Had to go build a real cross-origin PoC to back the claim.

**How to apply:** When a finding's severity or "this chains into X" argument depends on cross-site/CSRF exploitability, build the real thing before asserting it:
1. Write a minimal HTML page with the attack payload (e.g. `<meta http-equiv="refresh" content="0; url=TARGET">` for GET-based CSRF, or an auto-submitting form for POST).
2. Serve it from a genuinely different origin — `file://` and `data:` URLs are blocked by the Claude-in-Chrome extension ("Can't interact with browser-internal or unparseable URLs"), but `python3 -m http.server <port> --bind 127.0.0.1` works fine and is a legitimate stand-in attacker origin (different host/port = different site for SameSite purposes).
3. Open it in a **separate tab** while the authenticated session stays live in another tab (simulates "victim has the target open, clicks attacker's link").
4. Confirm the action actually fired (new resource created/state changed), then kill the local server.

Only write "demostrado" / "confirmed" language in the report after this real test passes — reframe as "sería explotable" (hypothetical) or drop the claim entirely if it can't be backed this way. Complements [[feedback_verify_before_confirming]] (verify real downstream effect) and feeds directly into [[feedback_no_informational_reports]] — a chain argument used to elevate a finding out of Informational must itself be real, not assumed.
