---
name: feedback-hunt-save-dont-submit-mode
description: "ENDED 2026-08-08. Workflow mode where findings across multiple user-named programs get hunted and documented (with PoC) but held back from submission until the program's current validity is confirmed"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

**ENDED 2026-08-08** — superseded by [[feedback_submit_everything_now]]: the user explicitly
ended this mode ("a partir ahora quiero que envies todo lo que encuentres incluso este ultimo")
and asked for the already-parked add-and-commit finding to be submitted along with everything
found going forward. Kept below for historical context only — do not apply this hold-back
behavior unless the user explicitly re-introduces it.

Starting 2026-08-05, the user introduced a batch-hunting mode: they name a
series of programs one at a time; for each, hunt and build a fully-documented
finding (with real PoC, same rigor as a normal submission) but **do not
submit** it yet. Findings get saved/parked. Only submit later, per-program,
once the user confirms that specific program is still active/in-scope at
that later point in time.

**Why:** the user's own words: "vamos a buscar cosas. para guardarla y no
enviarlas de momento. si resulta que despues esta el programa pues lo
enviamos te voy diciendo los programas" — they want a backlog of ready-to-go
findings across several programs, decoupled from the immediate
submit-per-finding rhythm used in normal single-target hunts.

**How to apply:** when this mode is active (user says "te voy diciendo los
programas" / lists multiple targets in sequence for this purpose): still do
full rigor (real PoC, 7-Question-Gate-equivalent quality) before saving a
finding, but skip the usual "¿envío?" checkpoint — write it to
`findings/dia*/` as normal and note it's parked for this batch, don't call
`create_report`. Only submit when the user later confirms (per program) that
it's time. This doesn't override [[feedback_no_informational_reports]] —
still don't bother documenting pure-informational findings even in this
mode, since "save for later" isn't a reason to lower the severity bar.
