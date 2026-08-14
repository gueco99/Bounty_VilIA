---
name: feedback-evidence-must-be-in-report-body
description: "All PoC evidence must be embedded directly in the report's own text fields (Payload/PoC/Impact) — never rely on a separate attachment, since the user often can't upload binary evidence files"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 594c75b1-c898-47af-ba80-5e78975b8a6a
---

Secur0 (and likely other platforms) restrict attachments to a narrow set of types (png/jpg/jpeg/gif/txt/mp4). The user cannot always attach arbitrary evidence (binaries, zips, etc.) — sometimes not even a .txt, depending on the submission flow. Treat attachments as unavailable by default.

**Why:** user explicitly said (2026-07-25, chezmoi symlink-escape finding) "recuerda todo tiene que quedar dentro el informe, no puedo aportar evidencia" (remember everything has to stay inside the report, I can't provide evidence) after being told a .txt transcript could be attached separately.

**How to apply:** for every finding, put the full reproduction transcript, raw payload bytes/scripts, and command output directly inside the report's own Payload/Proof-of-concept/Impact text fields — write it so the report is 100% self-contained and provable without needing any attachment. Only mention attachments as optional/supplementary, never as load-bearing for the report to make sense. See also [[feedback_secur0_report_structure]].
