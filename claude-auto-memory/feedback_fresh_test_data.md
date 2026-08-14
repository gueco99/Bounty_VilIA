---
name: feedback-fresh-test-data
description: "Before claiming a bug reproduces, re-verify on a freshly created record — not a convenient leftover from an earlier, unrelated test batch."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46360d1a-7024-4f70-b01a-c28082c84e12
---

Records created earlier in the same engagement for a different test (quota-boundary seeding, race-condition batches, bulk fixtures) can end up in states that don't represent real app behavior — even if they're still sitting there, logged-in and reachable. Reusing them as "convenient" test subjects for a new, unrelated bug class risks a false positive that looks fully proven (right status codes, real created resources, even a genuine cross-origin PoC) but is actually just an artifact of the earlier test's side effects.

**Why:** On [[project_gestionominegocio]], claimed presupuestos #48-50 (leftover from a 2026-07-25 quota-boundary test, created via raw direct-API POSTs that bypassed the normal conversion flow) proved that an already-"Facturado" presupuesto could be reconverted into a duplicate factura. Built a real cross-origin CSRF PoC on top of it and everything checked out. Then re-tested against a genuinely fresh, untouched presupuesto (#3) and got the opposite result — reconversion was properly blocked, exactly matching an already-submitted sibling report's claim. The #48-50 batch had been left in an inconsistent state by the earlier raw-API test itself, not by a real app bug. The whole finding was retracted.

**How to apply:** When a bug's proof depends on a specific record's state (already-closed/converted/quota-maxed/etc.), and that record was created via anything other than the normal application flow (direct API calls, bulk seeding, a different test's leftover data), re-verify the claim on a **freshly created record that went through the real flow end-to-end** before writing it up or building further PoCs on it. A same-account, same-session "it's already sitting there" convenience is not the same as a clean repro. This sharpens [[feedback_real_csrf_cross_origin_proof]] (a real cross-origin PoC built on polluted data still isn't proof) and [[feedback_verify_before_confirming]] (verify the real downstream effect, not just the response code).
