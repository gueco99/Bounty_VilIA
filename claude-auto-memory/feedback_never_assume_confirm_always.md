---
name: feedback-never-assume-confirm-always
description: "Never let a hypothetical precondition ('if X is configured this way') stand in for a confirmed fact when building an impact/escalation chain — always go verify X against the real target before scoring or drafting."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

Never assume anything in an impact/escalation chain, not even as a stated hypothesis ("if the
downstream CI shares a workspace...", "if this is deployed behind...", "if an admin later
runs..."). Every precondition a report's severity depends on must be checked against the real
target, not left as an "if" the reader is trusted to evaluate themselves.

**Why:** On [[project_boost_iosx]], three findings (#2822, #2808, #2837) all leaned on the same
unconfirmed precondition — a persistent/shared CI workspace between an untrusted PR job and a
later trusted release job — framed honestly as "if a downstream project's CI runs untrusted PR
code with workspace/cache reuse enabled." All three were closed Informative same-day, same
triager, same reasoning: no realistic attacker-benefit scenario. When actually checked (fetched
the real `.github/workflows/main.yml`), the precondition was not just unconfirmed but actively
false: `runs-on: macos-latest` (GitHub-hosted, ephemeral per run, not self-hosted/persistent),
no `pull_request` trigger at all (only `release`/tag-push/`workflow_dispatch`, all requiring
existing write access), no `actions/cache` step. The hypothesis wasn't a reasonable unverified
guess — it was checkable in one API call and turned out backwards. The user's reaction:
hypotheses are not a substitute for confirmation, ever, even when clearly labeled as
conditional in the report.

**How to apply:** before drafting or scoring any finding whose severity depends on a downstream
condition (CI topology, deployment configuration, another system's behavior, a third party's
future action), go confirm that condition against the real target FIRST — read the actual CI
workflow file, check the actual deployed config, run the actual chain end-to-end. If it cannot
be confirmed one way or the other, say so explicitly and treat the finding as unconfirmed/weak
rather than writing the precondition as an "if" and letting the CVSS score imply confidence the
verification never earned. This is a stricter, more general version of
[[feedback_verify_before_confirming]] (API-response verification) and
[[feedback_verify_against_live_target]] (local-checkout verification) — this one specifically
targets *hypothetical downstream/environmental preconditions* inside an impact chain, which
neither of those memories called out on their own. Complements
[[feedback_reproducibility_not_severity]]: even a bug that's reproduced perfectly can still rest
on an unconfirmed "if" — check the "if" itself, not just the reproduction.
