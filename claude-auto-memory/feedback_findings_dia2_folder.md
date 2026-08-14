---
name: feedback-findings-dia2-folder
description: "New findings go in findings/dia4/ now (was dia3, dia2, dia1) — user rotates this folder per batch, always says so explicitly."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46360d1a-7024-4f70-b01a-c28082c84e12
---

Write new draft reports (report_secur0.md and its evidence/) into `findings/dia4/<slug>/`. `findings/dia1/`, `findings/dia2/`, and `findings/dia3/` are closed prior batches — leave them alone. (`dia3` ended up unused/empty — the user skipped straight from dia2 to dia4.)

**Why:** user rotates this folder per work batch. dia1 → dia2 ("los nuevos reportes ponlo en otra carpeta... ahora otra con dia2"), dia2 → dia3 (2026-07-29, close of go-ios session), dia3 → dia4 (2026-07-30, "podemos seguir reportando cosas como haciamos antes no? me lo pones todo en dia4").

**How to apply:** any time a new finding is drafted for ANY target, create its directory under `findings/dia4/` instead of an earlier one. When a further rotation happens, expect an explicit `dia5` (etc.) instruction rather than assuming or auto-incrementing on your own — the user always states the new folder name themselves rather than expecting me to infer it.
