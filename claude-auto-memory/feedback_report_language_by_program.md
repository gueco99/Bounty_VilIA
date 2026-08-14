---
name: feedback-report-language-by-program
description: "Write bug bounty reports in English for international/English-native programs (e.g. chezmoi on GitHub), even though the global rule is to converse with the user in Spanish"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 594c75b1-c898-47af-ba80-5e78975b8a6a
---

Report *content* (Título/Detalle técnico/Payload/etc.) should match the program's own language, not the conversation language. For chezmoi (English-language GitHub project, international maintainers), write reports in English — even though [[feedback_respond_in_spanish]] means all chat replies to the user stay in Spanish.

**Why:** user explicitly asked to switch chezmoi's draft report to English on 2026-07-25, after 3 earlier chezmoi reports had already been written (and submitted) in Spanish by default, matching the conversational language instead of the target audience.

**How to apply:** before drafting a report for a new program, check whether the program/project is Spanish-native (e.g. gestionominegocio, a Spanish company) or English/international (e.g. chezmoi, most GitHub OSS projects, most CVE-eligible VDPs) and write the report fields in that language. The chat replies to the user always stay in Spanish regardless. If unsure, ask rather than defaulting to Spanish.
