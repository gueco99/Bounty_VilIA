---
name: feedback-confirm-before-submit-garminconnect
description: "on python-garminconnect (2026-08-08 onward), show the drafted report and wait for explicit confirmation before calling secur0_api.py submit — do not auto-submit"
metadata:
  type: feedback
  originSessionId: unknown
---

Starting 2026-08-08, on the python-garminconnect hunt specifically, the user asked to be shown a
drafted report and to confirm before it gets submitted via `secur0_api.py submit`, instead of
submitting autonomously as soon as a finding is verified.

**Why:** during a single session the maintainer pushed ~20 rapid-fire fix commits in response to
live reports, which made two autonomously-submitted reports (#3929, #3930) obsolete within
minutes of submission — the fix landed on the public branch before the report was even read. The
user wants a chance to sanity-check timing/relevance before a report goes out, given how fast this
particular program's remediation loop is turning out to be.

**How to apply:** on this target, after drafting a `report_secur0.md` and verifying it empirically,
present the title + a summary of the finding and payload to the user and wait for an explicit go
before running `secur0_api.py submit`. This overrides the general
[[feedback_autonomous_hunting]]/[[feedback_demonstrate_dont_ask_overlap]] default of submitting
confirmed findings without pausing — that default still applies to other targets unless the user
says otherwise there too. Also worth doing on any other target where the maintainer is visibly
shipping fixes in near-real-time during the same session, since that's the specific condition that
triggered this preference (fast-moving target, not distrust of the verification process itself).
