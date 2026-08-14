---
name: feedback-otra-cosa-same-program
description: "'otra cosa' from this user means try a different angle/bug within the current program, not switch to a different program"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7b8fdcbb-25bc-4678-949f-f743502cf349
---

When this user says "otra cosa" (something else) mid-hunt on a program, it means "try a
different angle/vulnerability class within the program we're already on" — not "switch to a
different target program." I misread it once as a request to change programs entirely
(during a json-machine session where the user had been repeatedly saying "sigue" to keep
digging) and offered a menu of other VDPs to jump to; the user rejected that and corrected
"el mismo programa, no cambies" (same program, don't change).

**Why:** this user's session style is to exhaust one target thoroughly before moving on
(established elsewhere: "sigue buscando", "insiste con otras ideas y otras vuln" pattern
repeated many times per target this session) — "otra cosa" fits that same exhaustive-search
mindset, it's asking for a different bug/angle, not a different target.

**How to apply:** only interpret a request to switch programs when the user explicitly names
a new target, says something like "miramos otro programa" with a pasted program page, or
otherwise unambiguously signals leaving the current one. A bare "otra cosa"/"algo distinto"
said while mid-investigation should be read as "different vulnerability class, same target"
by default.
