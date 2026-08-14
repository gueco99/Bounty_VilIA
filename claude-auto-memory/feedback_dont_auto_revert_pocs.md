---
name: feedback-dont-auto-revert-pocs
description: "Don't automatically clean up/revert PoC test data after confirming a finding — ask first, user wants to screenshot the live state"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 594c75b1-c898-47af-ba80-5e78975b8a6a
---

After confirming a live finding by manipulating test data (e.g. setting an invoice's
retención/IVA to an invalid value, adding a negative-price line), don't immediately revert it
back to the clean/original state as a matter of habit.

**Why:** on gestionominegocio (2026-07-24), after confirming `arbitrary-retencion-rate` the
user said explicitly "no restaures las cosas, porque quiero hacer fotos" — they wanted to
capture their own screenshot/Burp evidence of the live manipulated state before it got cleaned
up. This session's default pattern up to that point (test → confirm → immediately revert) was
actively working against that need.

**How to apply:** after confirming a finding via a live PoC, ask whether to leave the state as
manipulated for the user to inspect/screenshot, rather than reverting right away. Only clean up
once the user confirms they've captured what they need (or explicitly says to revert). This
applies broadly, not just to this one target — any time a PoC leaves visible, capturable
evidence in a UI (an altered total, a forged badge, a wrong status), assume the user may want
to see/capture it live before it disappears.
