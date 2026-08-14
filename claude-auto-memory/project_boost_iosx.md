---
name: project-boost-iosx
description: "boost-iosx (github.com/apotocki/boost-iosx) hunt state — VDP. First 8 findings ALL closed Informative by 2026-07-31 (build.sh/CI variants). Reopened 2026-08-02 with a genuinely new angle: CocoaPods prepare_command reachability (report_id 3309, pending triage)."
metadata: 
  node_type: memory
  type: project
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

Target: `github.com/apotocki/boost-iosx` (iOS/macOS XCFramework build scripts for Boost).
Public VDP. Source-code audit style hunt, focused on `scripts/build.sh` and CI/CD.

**FINAL OUTCOME (2026-07-31): every one of the 6 findings checked on the dashboard closed
Informative** — 3 directly (#2822, #2808, #2837, all "lacks sufficient impact... no realistic
scenario in which an attacker could benefit") and 3 more marked Duplicado (#2852
unpinned-github-actions, #2794 icu4c-unpinned-git-rce, #2773 icu-unverified-download) that,
per the user, also resolve back to Informative — i.e. even the 3 findings this session assessed
as "well-founded, real trust-boundary crossed" (confirmed live against the actual current
build.sh/README/CI workflow, not hypothetical) still did not land as valid/unique findings on
this specific program. Remaining 2 (icu-cache-ignores-upstream-updates, gitignore-gap-
marker-files) presumed to follow the same pattern, not separately confirmed on dashboard.

8 findings drafted in `findings/dia2/`:
- boost-iosx-gitignore-gap-marker-files
- boost-iosx-hash-verification-bypass-via-cache
- boost-iosx-icu4c-unpinned-git-rce
- boost-iosx-icu-cache-ignores-upstream-updates
- boost-iosx-icu-unverified-download
- boost-iosx-marker-file-skips-entire-build (= #2822)
- boost-iosx-staged-library-cache-bypass
- boost-iosx-unpinned-github-actions

**#2822 (marker-file-skips-entire-build) closed as Informative, 2026-07-31, triager Darío Rivas:**
"lacks sufficient impact... we don't consider there to be a realistic scenario in which an
attacker could benefit, but we do think it's worth fixing."

**Why the closure was fair (see [[feedback_reproducibility_not_severity]] for the general
pattern):** the report's own Impact section hedged the escalation behind an unconfirmed CI
precondition ("**if** a downstream project's CI runs untrusted PR code with workspace/cache
reuse enabled") rather than confirming boost-iosx's actual CI exhibits that shared-workspace-
between-trust-levels topology. The core technical claim (marker files bypass SHA256
verification without checking `frameworks/`'s actual content) is real, but the attacker
already needs build-directory write access to plant tampered markers — access that would
already let them overwrite `frameworks/` directly, with or without the bug. Flagged this
weakness to the user *before* triage closed it, independently reaching the same conclusion.

**How to apply to the remaining 7 boost-iosx findings (and to any future report on this
program):** before finalizing severity, ask "what can the attacker do with this bug that they
couldn't already do with the access the exploitation scenario assumes they have?" If the
answer is "nothing new" without a *confirmed* (not hypothetical/hedged) escalation path, expect
an Informative close. Worth revisiting the other 7 (especially anything else framed around
cache/workspace reuse) with this same lens before they go to triage, or proactively softening
severity language that leans on unconfirmed downstream CI assumptions.

## Session 2026-08-02: reopened with a genuinely new angle — CocoaPods prepare_command

User pushed to re-audit despite the "CLOSED" status, explicitly asking for a different angle
than build.sh/CI cache-trust variants. Found it in `boost-iosx.podspec`:
`s.prepare_command = "sh scripts/build.sh"` — a standard CocoaPods hook that runs automatically
on **every consumer's own machine** during an ordinary `pod install`, not just boost-iosx's own
CI. This directly invalidates the precondition reasoning ("attacker already needs
build-directory/CI access") that got every one of the 6 checked findings closed as Informative —
the same code (`icu4c-iosx` unpinned git clone-and-execute) is reachable by any of potentially
thousands of developers who add this pod, with the "attacker" precondition being "compromise the
separate `icu4c-iosx` repo," not "already have the access this bug would grant."

**Finding #9 — SUBMITTED (report_id 3309, 2026-08-02)**:
`findings/dia2/boost-iosx-preparecommand-consumer-rce/report_secur0.md`. User explicitly pushed
back on an earlier version of this PoC that only used a harmless marker-script stand-in for
`scripts/build.sh` ("pero tiene impacto real. quiero que haya pruebas contundentes") — correctly
caught that this only proved the trigger mechanism, not that the real script reaches the
vulnerable block. Rebuilt the PoC to run the REAL, byte-for-byte unmodified `scripts/build.sh`
(md5sum-verified) via only two harmless OS-detection shims (`sysctl`, `xcode-select` — macOS-only
prerequisites absent on the Linux reproduction host, touching zero lines of the actual vulnerable
logic) and captured a REAL `git clone` of the live `https://github.com/apotocki/icu4c-iosx`
happening (confirmed via `git log -1` on the resulting checkout: real commit
`5ba78682c9f8b97f413ecc25ee87cf3dc2c022d5`), which then executed that clone's own
`scripts/build.sh`, which itself cloned a *third* repo (`unicode-org/icu`, tag-pinned this time).
Full real chain, not a hypothesis. **Lesson**: even after building what felt like a solid PoC,
the user's "pruebas contundentes" pushback was correct — a stand-in script proves reachability of
the TRIGGER, not that the real vulnerable CODE actually executes when triggered; for a supply-
chain-reachability finding like this, both halves need real, live proof, not one assumed from the
other.

**Calibration lesson from the final outcome:** this triager/program's bar for build-script/CI
hardening findings on this specific repo is high enough that even a live-verified, real
trust-boundary-crossing bug (unpinned git-clone-and-execute of a sibling repo on the
documented default path, unverified binary download on a documented opt-in path, mutable
Action tag with demonstrated tag-mobility) did not land as valid/unique — whether via
Informative or Duplicado. Don't read "I confirmed this against the live target, not a
hypothesis" (see [[feedback_never_assume_confirm_always]]) as a guarantee of acceptance on
this program — it's a necessary bar, not a sufficient one, here. **This program is CLOSED for
further hunting** unless a genuinely different angle emerges (not another variant of
"unpinned dependency" / "cached state trusted without reverification" on build.sh/CI, which
is now exhausted across 6+ attempts).
