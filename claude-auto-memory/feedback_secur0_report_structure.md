---
name: feedback-secur0-report-structure
description: "Exact field structure and CVSS version required for report_secur0.md files, matching the Secur0 platform's submission form"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: baa01792-70fa-44de-a3b4-a1b53d506c1c
---

`report_secur0.md` files must follow the Secur0 platform's actual submission form fields, in
this exact order, using these exact headings:

1. **Título** — descriptive title (form limit 100 chars)
2. **Alcance** — the in-scope asset (e.g. `github.com/m32/endesive`)
3. **Endpoint (Opcional)** — affected URL/endpoint/function (form limit 500 chars)
4. **Detalle técnico** — vulnerability description (form limit 5000 chars)
5. **Payload** — exact payload/code used to reproduce (form limit 20000 chars)
6. **Impacto** — potential impact (form limit 5000 chars)
7. **Prueba de concepto** — reproduction steps (form limit 5000 chars). This is a REQUIRED
   field distinct from Payload — do not delete it even if it looks redundant. Keep it
   procedural/narrative (numbered steps, environment setup, what to run in what order) while
   Payload holds the raw exact code/commands — don't just re-paste Payload's content here.
8. **Criticidad** — **CVSS v4.0**, not v3.1. The form splits impact into two groups, not a
   single "Scope" metric:
   - Métricas de explotabilidad: Vector de ataque / Complejidad del ataque / Requisitos del
     ataque / Privilegios requeridos / Interacción del usuario
   - Métricas de impacto del **sistema vulnerable**: Confidencialidad / Integridad /
     Disponibilidad
   - Métricas de impacto del **sistema subsiguiente**: Confidencialidad / Integridad /
     Disponibilidad
   (Cross-tenant/multi-party impact, e.g. hijacking another company's data in a multi-tenant
   app, or forging trust anchored to a third-party CA, goes under "sistema subsiguiente", not
   "sistema vulnerable".)
9. **Adjuntos (Opcional)** — reference the evidence file(s). **Only accepts
   png/jpg/jpeg/gif/txt/mp4** — no zip/tar/binary PoC files, and this also rules out
   `.rs`/`.py`/`.kt`/`.json`/etc source-code PoC files: **any PoC source code must be saved
   with a literal `.txt` extension** (rename after writing, e.g.
   `poc_something.rs` → `poc_something.txt`), with a one-line note in Payload/Adjuntos telling
   the reviewer to rename it back before compiling/running. When the PoC is a crafted binary
   (malicious archive, exploit blob, etc.), don't try to attach it: embed it as base64 text
   directly inside **Payload** (limit 20000 chars, plenty of room for small PoCs) alongside the
   exact commands to rebuild it (`base64 -d > file`), and skip the Adjuntos field entirely.
   Confirmed 2026-07-24 on the chezmoi program (`.tar.gz` PoC wouldn't upload) and again
   2026-07-24 on edge-python (user explicitly rejected `.rs` evidence files, had to rename 3
   PoC files to `.txt` after already writing them — check the extension *before* writing next
   time, not after).
10. **Información Adicional y Sugerencia de Solución (Opcional)** — fix code + methodology notes
11. **Colaboradores (Opcional)** — skip, not report content

**Why:** the user pasted the actual submission form fields on 2026-07-22 after finding my
CVSS v3.1 usage and missing/merged "Prueba de concepto" section didn't match the platform,
saying explicitly to remember this structure for future reports.

**How to apply:** every future `report_secur0.md` (for any target/program using Secur0) must
use exactly these 11 headings in this order, CVSS v4.0 with the VS/SS split. Before finalizing
a Secur0 report, check it against this list — **including actually running `wc -c` on the
Detalle técnico / Impacto / Prueba de concepto sections against their 5000-char limits**
(caught going over on 2/3 edge-python reports on 2026-07-24 despite the limit already being
documented here; the fix is to check the count as a normal step before calling a report done,
not just know the number exists) — and confirm every Adjuntos file extension is one of
png/jpg/jpeg/gif/txt/mp4 before writing it to disk. See [[feedback_verify_before_confirming]]
for the related PoC-rigor expectation on this same user.

**No attachments, ever, for any program (standing rule, confirmed three times — 2026-07-28
go-ios session, reconfirmed 2026-07-29 when prepping for the next programs, reconfirmed again
2026-07-30 at the start of the Autofac session):** don't rely on the
Adjuntos field for PoC source/output — embed the full PoC test file(s)/script(s) and their run
output as fenced code blocks directly inside **Payload** (20000-char limit, normally plenty of
room), and leave Adjuntos empty/"None". Reason given: avoids the extra step of
renaming/uploading files on Secur0's form entirely, not just avoiding disallowed extensions.
When a PoC is genuinely too large to fit in the Payload char limit even after trimming
comments/whitespace, that's the one case where an attachment is still needed — pick `.txt` per
the extension rule above. Applies to every report drafted from 2026-07-28 onward, for any
target/program, not just go-ios.

**Short, plain titles, no special characters (standing rule, confirmed twice — 2026-07-28 go-ios
session, reconfirmed 2026-07-29 when prepping for the next programs):** the Título field must be
short and contain no special characters — no backticks, parentheses, em-dashes, or slashes; plain
descriptive sentence fragments only (e.g. "Race condition bypasses per-device concurrency limit"
not "Race condition in `LimitNumClientsUDID` (Load-then-Store on sync.Map) lets multiple
concurrent requests bypass..."). Applies to every report drafted from 2026-07-28 onward, for any
target/program, not just go-ios.

**Forward-only application (both rules above):** when the user gives a new report-formatting
rule, apply it to reports drafted from that point on — do NOT retroactively rewrite
already-drafted reports unless explicitly asked to. Caught myself starting to "fix" old titles
unprompted once and the user stopped me ("no cambies lo que ya esta escrito, solo para lo
nuevo") — check for this reflex before touching prior work whenever a new stylistic preference
is (re)stated, including when it's being reconfirmed rather than introduced for the first time.
