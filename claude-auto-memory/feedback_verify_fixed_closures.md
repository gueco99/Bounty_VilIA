---
name: feedback-verify-fixed-closures
description: "when a program marks a report \"Fixed\"/\"Resuelto\", cheaply verify the actual fix commit before trusting the closure — don't take triage status at face value"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ff7451f9-ed99-4be8-8d13-3103f0c4f6ba
---

When the user pastes or references a report that a program has closed as Fixed/Resuelto, don't
just accept that status — if the fix reference is checkable (a commit hash, PR link, or even
just "fixed in the latest release"), spend the (usually very cheap) effort to look at the actual
diff before moving on to something else.

**Why:** confirmed on [[project_chezmoi]] (2026-08-01, report #2889 → new report #3307). The
maintainer closed #2889 ("parseDirAttr missing dot-resolution guard, home-directory wipe") citing
commit `01b60ddec`. That commit is real and does fix a `name == "."` gap — but in the *sibling*
function (`parseFileAttr`), not the one #2889 actually named (`parseDirAttr`). A single
`git log --oneline --all -- <file>` plus re-running the original report's own PoC against a
freshly-fetched HEAD took a few minutes and conclusively proved the vulnerability was still
live. The maintainer likely conflated two similarly-worded, same-day reports about sibling
parser functions.

**How to apply:** when a "Fixed" closure references a specific commit, diff that commit against
the file/function the report actually described — not just the file's name, the actual code
path. If the commit doesn't touch the named function, or touches a different-but-similarly-named
sibling, re-verify the original PoC against the current HEAD (fresh fetch first — see
[[feedback_verify_against_live_target]]) before concluding either way. This applies whether the
closed report is the user's own or one they're reviewing out of curiosity — a locked/closed
report doesn't mean the underlying bug is gone, and a fresh, well-scoped follow-up report
("the fix for X didn't land, here's proof against current HEAD") is a legitimate, valuable
submission distinct from re-litigating the same report.

**Second confirmation, more extreme:** [[project_python_garminconnect]] #3823 (2026-08-08),
closed "Fixed" citing commit `9b4a549` and a test class `TestIdentifierValidation`. This time
neither existed at all — `git fetch origin && git cat-file -t 9b4a549` returned "not a valid
object name", and `grep -rn TestIdentifierValidation .` found nothing anywhere in the repo. Not a
wrong-sibling-patched case this time — a fully fabricated/hallucinated citation. Re-running the
original PoC against the actual current tip showed the vulnerable code byte-for-byte unchanged.
Lesson holds even harder here: cheaply check that a cited commit hash *exists* at all (one
`git cat-file -t <hash>` after a fresh fetch) before reading anything else into a "Fixed" status —
a nonexistent-commit citation is now something to explicitly expect, not just a wrong-target one.
When the closed thread is locked (no reopen/comment path available), a fresh new report with the
re-verification evidence and an explicit ask to reopen is the right move, same as the chezmoi case.
