---
name: project_add_and_commit
description: "add-and-commit (GitHub Action, EndBug/add-and-commit) hunt state — 2 findings SUBMITTED (report_id 3919, 3922)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 34489275-58f5-410f-8b5b-40d13626490b
---

Active 2026-08-08, GitHub Action VDP (23 total reports historically, 0 accepted before this
session), repo `recon/add-and-commit/repo`, commit `a65f80b151f5a1d2af4c3d329730aec3b689893f`.
program_id 135, scope_id 530.

1 finding SUBMITTED (report_id 3919, 2026-08-08, per [[feedback_submit_everything_now]] which
ended the earlier save-don't-submit mode):
`findings/dia2/add-and-commit-upload-pack-abbreviation-rce/report_secur0.md` — arbitrary command
execution via the action's `pull`/`fetch` inputs. Root cause: the action passes user-supplied git
argument strings straight into `simple-git` with no sanitization of its own, relying entirely on
`simple-git`'s internal `preventUploadPack()` guard (regex requires the literal string
`--upload-pack`/`--receive-pack`). Git itself accepts unambiguous option abbreviations
(`--upload-pac` etc.), which the guard's regex does not account for — so the abbreviated form
sails straight through and git executes it exactly as the full flag. Live-verified real command
execution (not just theoretical) through the action's exact `matchGitArgs()` +
`simple-git.pull()`/`.fetch()` call sequence, against both the pinned `simple-git@3.33.0` and the
latest `3.36.0` — **not fixed by upgrading the dependency**, since the gap is in simple-git's own
guard regex.

Ruled out first: the public CVE-2026-6951 PoC uses `.clone()` + `--config protocol.ext.allow`,
but add-and-commit never calls `.clone()`, and empirically none of the subcommands it actually
uses (`add`/`rm`/`commit`/`tag`/`checkout`/`fetch`/`pull`/`push`) accept `--config` as valid
syntax — only `clone` does. Kept digging instead of reporting that non-functional angle, per
[[feedback_no_informational_reports]]; found the abbreviation bypass as the actually-reachable
variant.

Scoping precondition disclosed honestly in the report (not overclaimed): exploitation requires a
consuming workflow to route less-trusted data (PR title/branch name/etc. — a documented "pwn
request" pattern) into the `pull`/`fetch`/`push`/`tag_push` input, since those are workflow-author
strings by default. The demonstrated command execution itself is real and PoC'd, not theoretical.

Also confirmed (same root cause, no separate report per [[feedback_report_merge_rule]] since fix
is identical): the `push` input is independently vulnerable to the same `--receive-pac`
abbreviation bypass (git.push(undefined, undefined, matchGitArgs(pushOption), cb) — attacker
fully controls the "remote" argument too here, more flexible than pull/fetch).

Ruled out: git-config-value argument injection via `author_name`/`author_email` (sourced from the
GitHub actor's public profile name/email through `getUserInfo()`, then passed to
`git.addConfig()`). Empirically confirmed `git config <name> <value>` always treats `<value>` as
a literal positional argument, never as an option, even when it looks like a flag
(`--edit`, `--upload-pack=...`) — simple-git's `addConfigTask` commands array
(`["config", "--scope", key, value]`) is safe. Not exploitable.

`tag_push` input not exploitable via this vector: its remote is hardcoded to `'origin'` (a real
configured GitHub remote, not an attacker-controlled local/ext path), so `--receive-pack`
overrides would be sent to GitHub's real git server, not executed locally.

**Strongest possible verification (2026-08-08):** ran the actual committed `lib/index.js`
(ncc-bundled artifact, the literal bytes GitHub Actions executes per `action.yml`'s
`main: lib/index.js` — not a hand-rolled reproduction) as a real action invocation, with
`INPUT_PULL` set to the malicious payload via env vars exactly as the Actions runner would set
them. Confirmed the marker file gets created through this exact end-to-end path, removing any
doubt that ncc's bundling/minification could have altered the vulnerable behavior. Worth adding
as a note to #3919.

**Third independently confirmed abbreviation vector (2026-08-08):** `simple-git`'s
`preventUploadPack()` also blocks `git push --exec=<program>` (`/^\s*--exec\b/`, push-specific
receive-pack-equivalent primitive) but the same literal-string-regex flaw applies: `--exe`
(missing trailing "c") is an unambiguous abbreviation git itself accepts, and it bypasses the
check exactly like `--upload-pac`/`--receive-pac` did. Live-confirmed real command execution via
`git.push(undefined, undefined, matchGitArgs(pushOption), cb)` with payload
`"--exe=touch <marker>;" ../another_local_repo master`. Same root cause, no separate report
(per [[feedback_report_merge_rule]]) — but this means the report's originally suggested fix
("reject args starting with --u or --r") is **incomplete**, since `--exec` starts with `--e`.
Communicated as a follow-up note on report #3919 along with a CVSS revision (AC:H→AC:L, SC:N→SC:H
per user's prompt to reconsider severity).

Also explored: `isConfigSwitch()` only matches the literal string `-c`, not `--config` — a real
imprecision in simple-git's own guard, but NOT independently reachable through add-and-commit,
since git itself rejects `--config` as invalid syntax for fetch/pull/push/tag (only `clone`
accepts it, which add-and-commit never calls), and literal `-c` IS correctly caught by the
existing check. Not a new finding.

Codebase is small (3 source files, ~450 lines) and now very thoroughly reviewed across all 4
confirmed abbreviation-bypass angles (upload-pack via pull/fetch, receive-pack via push, exec via
push). Diminishing returns on further random-function search in this specific repo.

**Killed, not submitted:** js-yaml 5.2.1's exponential-parse DoS (GHSA-pm4m-ph32-ghv5, CVSS 7.5)
IS reachable via `parseInputArray()` (called for `add`/`remove` inputs) — empirically confirmed
real exponential blowup (n=26 → 37s from a 183-byte payload) through the action's actual code.
Killed anyway per [[feedback_needs_real_victim]]: unlike `pull`/`fetch`/`push` (plausibly dynamic
in real workflows), `add`/`remove` are near-always static file-glob patterns the workflow author
writes themselves — no realistic path for an external attacker to control that value, so this is
self-DoS, not a security finding. User caught this immediately when I proposed drafting it.

**2nd finding SUBMITTED (report_id 3922, 2026-08-08), genuinely different root cause (CI supply
chain, not code logic):** `findings/dia2/add-and-commit-versioning-workflow-supply-chain/report_secur0.md`.
`.github/workflows/versioning.yml` (triggered on every `release: [published, edited]` — frequent,
normal maintenance activity) uses `Actions-R-Us/actions-tagger@v2` — a different maintainer than
EndBug, pinned to a mutable tag, no `permissions:` block. Confirmed via that action's own
`action.yml`/README that its entire purpose (auto-promoting major-version tags) requires
`contents: write`, so the ambient `GITHUB_TOKEN` for this job necessarily carries that scope.
Real, distinct victim (unlike the killed YAML-DoS draft): add-and-commit's own README documents
`EndBug/add-and-commit@v10` (major-tag) as the recommended consumption pattern for every
downstream user — if `actions-tagger`'s tag is ever compromised, the next release-publish
executes malicious code with `contents: write` on add-and-commit's own repo, letting an attacker
repoint add-and-commit's own release tags and silently compromise every one of its (numerous)
downstream consumers. Same finding *shape* as the earlier Autofac reusable-workflow report
([[project_autofac]]) but a stronger blast-radius story here since add-and-commit is itself a
widely-consumed Action, not just an application repo.

Initially dismissed a weaker sibling of this same class (`export-labels.yml`/`label-sync.yml`,
`workflow_dispatch`-only trigger, unclear token scope) as too speculative — correctly, in
retrospect: `versioning.yml` was the strong instance worth pursuing, found only after actually
checking the third-party action's documented permission requirements instead of guessing.

**Strong corroboration found via issue mining (2026-08-08):** closed issue #737 ("Enable release
immutability for this action's releases") has the maintainer (EndBug) explicitly confirming, in
their own words, the exact mechanism #3922 is about: "I keep the major version tags updated on
purpose... if for example tomorrow I release v10.0.1 the v10 tag will be updated to point to the
new release... If users want to pin a specific version, the most reliable way to do that is to
pin a specific commit." They declined GitHub's platform-level release-immutability feature
because they *want* v10 to keep moving — but #3922 isn't asking for that; it's asking to pin the
*third-party tool that performs the move* (`actions-tagger`), which doesn't conflict with their
stated design intent at all. Worth citing as a comment on #3922 — proves the tag-update mechanism
is real, intentional, and exactly as described, not a hypothetical. Also found (not directly
useful, but good context): issue #692, a spam/social-engineering PR proposing a workflow that
would forward 5 secrets to a third-party reusable workflow — maintainer correctly caught and
rejected it ("This is spam"), showing baseline vigilance against this exact finding class.

Issue/PR history mining otherwise unproductive for new bugs (dependency-bump PRs, unrelated
permission-troubleshooting issues for consumers, no other open security threads). Codebase and
now issue tracker both very thoroughly covered; further "never-looked-at angle" search here has
reached genuine diminishing returns.
