---
name: project_python_garminconnect
description: "python-garminconnect hunt state — fresh CVE-eligible VDP (github.com/cyberjunky/python-garminconnect), Python Garmin Connect API wrapper library"
metadata: 
  node_type: memory
  type: project
  originSessionId: 34489275-58f5-410f-8b5b-40d13626490b
---

Active 2026-08-07, CVE-eligible VDP, 0 prior reports at start, 30-day window. Local clone at
`recon/python-garminconnect/repo` (fetched full history via `git fetch --unshallow` after an
initial shallow clone — do this again if re-cloning, since git history mining is where the value
was found).

## False "Fixed" closure caught and reopened via new report (2026-08-08)
User pasted the Secur0 page for #3823 (delete_weigh_in/delete_blood_pressure traversal): triager
marked it "Fixed"/locked the thread, citing commit `9b4a549` (added `_validate_positive_integer`
for `weight_pk`/`version` + `_validate_date_format` for `cdate`) and an existing test class
`TestIdentifierValidation`. Checked both citations against the real repo (fresh `git fetch` +
`git cat-file -t 9b4a549` + `grep -rn TestIdentifierValidation .`): **neither exists anywhere in
the public repository.** Re-ran the exact original PoC against the actual current `origin/master`
tip (`46ab4eb...`, same commit as the FIT-fixture fix) with the same no-network monkeypatch
technique used throughout this session — all three escapes still work identically, real
`Authorization` header attached, `weight_pk`/`version`/`cdate` byte-for-byte unchanged from the
original vulnerable code. The closure rationale is factually false, not just an "wrong sibling
patched" case like the git-history one — the cited commit and test class don't exist at all.
Since the #3823 thread is locked (no dispute/comment endpoint in `secur0_api.py`), submitted a new
report (**#3929**, "Unvalidated weight and blood pressure IDs still allow path traversal after
Fixed closure") with the fresh evidence, asking for reopening rather than a duplicate-close. This
is the single strongest confirmation yet of [[feedback_verify_fixed_closures]] — always re-check a
cited fix commit hash actually exists before trusting a "Fixed" status, not just that it patches
the right function.

## Maintainer's rapid remediation wave (2026-08-08, ~09:00-16:15) — #3929/#3930 now moot, new gap found
The maintainer pushed ~20 new commits in a few hours directly responding to this session's reports:
`9b4a549` (the commit #3823's closure cited, which genuinely did not exist in the public repo when
checked — turned out to be sitting on a private/staging branch and was published for real shortly
after, per the maintainer's own follow-up comment on #3817 confirming this), plus a generic
`Client._run_request()` defense-in-depth check (`f136dcc`, rejects `..`/`?`/`#` in any path),
per-parameter UUID/int/date validation across every gear/activity/weight/blood-pressure method,
the FIT-fixture PII removal, cassette sanitiser hardening, MFA/login/token-refresh hardening, a
domain allowlist, JWT signature rejection, and more. **Re-verified all of #3817/#3823/#3824/#3843's
original PoCs against the final tip (`fca63bb00454b0c700e21b4de6a7c2533f4e938d`) and every single
one now correctly raises `ValueError` before any request is built.** This makes the two follow-up
reports filed earlier today (#3929 disputing #3823's closure, #3930 re-flagging the gear/activity
cluster) **factually obsolete** — they were accurate at the moment they were filed (the fix
genuinely wasn't live yet) but the real fix landed within the same session, before triage even
looked at them. Nothing to do about that after the fact except note it for calibration: this
program's actual turnaround on real reports is extremely fast once escalated, even though the
first-touch triage response (#3823, #3920) was sloppy. Don't auto-assume future "still vulnerable"
follow-ups will still be needed by the time they're read — always re-fetch immediately before
concluding.

**New finding from reading the fix commits themselves, not from re-testing the old ones:** commit
`3f8cc74` ("security: harden token load against symlink redirection") — the direct fix for the
already-submitted #3851 — only adds `O_NOFOLLOW` to the *final* `os.open()` in `Client.load()`.
`token_file_path()` (called just before that open) resolves the tokenstore with `Path.is_dir()`,
which follows symlinks, *before* the O_NOFOLLOW-protected open ever happens. Since
`~/.garminconnect` (a directory, not a direct `.json` path) is this library's own documented
default tokenstore (`README.md`, `example.py`), a local attacker only needs to plant *that
directory* as a symlink to their own real directory containing a crafted `garmin_tokens.json` —
no race needed if the directory doesn't exist yet (first run). Empirically confirmed, zero network
calls: `Client().load(<symlinked-directory-path>)` silently succeeds and adopts the attacker's
`di_token`/`di_refresh_token`/`di_client_id`. Submitted as **#3947**. This is now the *third*
distinct "the just-shipped fix has a narrower scope than the vulnerability class it claims to
close" finding on this target in one session (cassette YAML vs. FIT binary for PII-in-history;
`activity_id`-only vs. `gearUUID`/`userProfileNumber` for the original traversal cluster before
today's real fix; final-component-only vs. directory-component symlink-following here) — worth
treating as this program's dominant failure mode: fixes consistently protect the exact reported
case but not the sibling/adjacent case one level over.

## #3948 — the write-side twin of #3947, more severe (2026-08-08)
User said "revisa mejor" after the first full pass. Re-examined `dump()` (the write side of the
same `token_file_path()` helper #3947's `load()` bug lives in) and found it has the *identical*
gap: `p = token_file_path(path)` resolves the tokenstore directory via `Path.is_dir()` (follows
symlinks) *before* `dump()`'s `O_NOFOLLOW`-protected open ever runs. Empirically confirmed, zero
network calls: planted `~/.garminconnect`-equivalent as a symlink to an attacker-owned real
directory, then called `dump()` with the victim's real (simulated) `di_token`/`di_refresh_token`
already set — the victim's actual, valid session tokens landed in plaintext inside the attacker's
directory. This is a stronger finding than #3947: instead of an attacker injecting a *fake*
session into the victim (#3947), the victim's own `login()` (which auto-calls `dump()` after a
fresh credential login) hands its *real, persistent-access* credential straight to the attacker —
direct account-takeover-capable credential theft, not session confusion. Submitted as **#3948**.
**Lesson reinforced**: when a shared helper function has a bug reached from one call site, always
check every OTHER call site of that same helper before considering the finding complete —
`token_file_path()` is called from both `load()` and `dump()`, and only checking the one the
original report happened to name would have missed the more severe half.

## #3950 — third instance of the token_file_path() symlink gap, plus final sweep (2026-08-08)
Applying the lesson from #3948 (check every call site of a shared helper), found `token_file_path()`
has a *third* caller: `Garmin.logout()`, which calls `path.unlink()` on whatever it resolves to
with zero symlink protection at all (not even the O_NOFOLLOW that `load()`/`dump()` at least
attempt). Empirically confirmed: a symlinked tokenstore directory pointing at an arbitrary
attacker-chosen real directory causes `logout()` to delete a file there — a classic CWE-59
confused-deputy arbitrary-file-delete (the deletion runs with the *victim's* privileges, at a
location the *attacker* controls via the symlink, not necessarily a file the attacker could delete
themselves). Submitted as **#3950**. All three `token_file_path()` callers now have a
corresponding report: #3947 (load — session injection), #3948 (dump — real credential theft, most
severe), #3950 (logout — arbitrary delete).

**Maintainer pushed back on #3851** (the original symlink report) as a possible duplicate, citing
`test_load_refuses_symlink` and claiming `load()` already uses O_NOFOLLOW correctly. Their test
symlinks the **`.json` file itself** (`link = tmp_path / "garmin_tokens.json"`), which hits
`token_file_path()`'s early-return branch (`suffix == ".json"`) and never touches `is_dir()` — a
genuinely different, already-fixed scenario from the **directory**-symlink case (`~/.garminconnect`,
the library's own documented default) all three new reports demonstrate. Drafted a precise reply
distinguishing the two branches with a one-line `token_file_path()` repro, pointing triage at
#3947/#3948/#3950 instead of #3851 itself.

**Final sweep before concluding**: re-ran a comprehensive fuzzer (both `str`- and
`int | str`-accepting params, all 147 public methods) against the final tip — zero escapes, the
traversal family is genuinely fully closed. Grepped for every other `.is_dir()`/`.is_file()`/
`.exists()` call in the package: only `upload_activity()`/`import_activity()` remain, both reading
a caller-supplied *local* file path for upload (self-inflicted, not attacker-reachable, same
judgment call as `download_activity`'s `activity_id` in earlier notes — not pursued). Confirmed via
`tests/test_token_permissions.py` (permissions/atomicity only) and `tests/test_widget_mfa.py`
(thorough title/rate-limit/TOTP-vs-email coverage, no symlink scenario) that neither test suite
covers the directory-symlink case — corroborates that #3947/#3948/#3950 are genuinely new, not
already-tested-and-passing.

## #3947/#3948/#3950 now genuinely FIXED for real (commit dbe8ada, 2026-08-08 ~16:57)
Maintainer fixed `token_file_path()` at the root: rejects the tokenstore path if `token_path` or
`token_path.parent` `.is_symlink()`, closing `load()`/`dump()`/`logout()` all at once — exactly the
"fix the shared helper once" approach I recommended in all three reports. Re-ran all three original
PoCs against `dbe8ada`: `load()` and `dump()` now raise `ValueError`/`GarminConnectConnectionError`
("Token path must not be a symlink"), `logout()` no longer deletes the file outside the tokenstore.
**All three closed for real, no further action needed on those.** Considered whether a
multi-level-up symlink (grandparent directory rather than the immediate parent) still bypasses this
— decided not worth chasing: the immediate-parent-only check covers every realistic scenario (the
tokenstore directory itself, or the direct parent of a `.json`-suffixed tokenstore path); a
grandparent-level symlink would require the attacker to already control something like the
victim's home directory's own parent, which isn't a plausible local-attacker threat model on a
normal shared host. Applying the "does this have a real victim" filter *before* spending time on a
PoC now, not just before submitting — this is the point going forward per explicit user
instruction ("busca con ese criterio siempre").

## Investigated and KILLED — logout/refresh race leaves a stale token in memory, no victim
Checked whether `_clear_auth_state()` (called by `logout()`) shares `self._token_lock` with
`_refresh_di_token()`'s three-field write (`di_token`/`di_refresh_token`/`di_client_id`) — it
doesn't, and built a deterministic PoC (a hooked `dict.get()` that starts and joins a concurrent
`_clear_auth_state()` call at the exact interleaving point) proving that a `logout()` racing a
token refresh leaves `is_authenticated == False` while `di_refresh_token`/`di_client_id` still hold
the freshly-issued *real* values in memory. Real and reproducible, but user asked directly "tiene
impacto en una víctima? es de seguridad?" and the honest answer is no: this is a single
application's own instance, own account, own two threads — no external attacker, no cross-user/
cross-host boundary, no concrete second party who benefits. Recovering the stale value requires
*another*, unrelated bug in the calling application (logging it, persisting it, etc.) — same
self-inflicted-with-no-victim pattern as the dead MFA-shelving code earlier this session. Did NOT
submit. Worth remembering as a real internal-hygiene bug if the maintainer ever asks, but not
bounty-reportable on its own.

## Full commit-by-commit audit of the 20-commit wave (2026-08-08) — one finding, rest are clean
After #3947, read every remaining commit's diff individually (not just re-testing old PoCs) looking
for the same "narrower than it claims" pattern. Checked: `36485ac` (domain allowlist — exact-match
against a 2-item set, and the public `Garmin()` API can only ever pass literal `"garmin.com"`/
`"garmin.cn"` anyway, so no bypass surface exists at all); `12e3287` (JWT `alg:none` rejection —
the decoded payload was already read-only local bookkeeping never used as an auth decision, so this
is inconsequential hardening either way, not a real fix for a real gap); `de3c9d1`/`e488d7d` (moved
several query-string-in-path constructions to `requests`' own `params=` dict — closes out the
one query-parameter case from #3817 (`get_gear`'s `userProfilePk`) that was never a real path
traversal to begin with, now also validated as an integer); `3b196a2` (exception messages now only
surface an allowlisted `message`/`content` field instead of the raw response body/HTML — verified
the nested `detailedImportResult` extraction's possible `IndexError` on an empty `failures: []` is
already caught by the surrounding broad `except`, no crash); `d6ae582` (login failure messages no
longer embed the full SSO JSON response, avoiding `serviceTicketId`/`customerGuid` leakage);
`9136ec6` (token refresh now serialized under `self._token_lock`, a `threading.RLock` with a
correct double-checked-locking re-validation inside the lock); `60e8584` (tokenstore path-vs-JSON
detection switched from a `len() > 512` heuristic to `_looks_like_json()` structural check — a
literal path starting with `{`/`[` would misclassify, but that's a usability edge case, not
attacker-reachable); `40aa797`/`f67ead0` (clear plaintext password/local var after login — pure
hardening); `d1f9f62` (`~username` token-path rejection regex `^~[^/\\]` — correctly allows bare
`~`/`~/...`, correctly rejects `~otheruser`, no bypass found); `fca63bb` (interleaved-MFA
`_mfa_pending` guard, correctly reset in a `finally` in `resume_login()` so it can't get stuck);
`cc9c896` (removed manual `f'"{filename}"'` double-quoting in `import_activity`'s multipart upload
that could have let an embedded `"` in the filename break out of the Content-Disposition
`filename=` attribute — checked the sibling `upload_activity()` for the same pattern and it already
used the plain, unquoted filename, so no gap there either). **No further findings from this pass**
— the one genuine gap in this entire wave was #3947. Don't re-review these specific commits again
unless their surrounding code changes.

## Findings submitted
- #3812 (2026-08-07): committed VCR test-cassette YAML fixtures (`tests/cassettes/*.yaml`, 17
  files) contained real Garmin API response bodies with unredacted health/biometric PII (weight,
  height, birthDate, gender, sleep windows, daily steps/calories/HRV/stress/SpO2/hydration/body
  composition) tied to a persistent numeric profile ID (82413233 / 376735957), spanning the
  project's history up to commit `2ae0eb5`. The project's own sanitization (`tests/conftest.py`)
  redacted `Authorization`/`Cookie` headers and `display_name`/`fullName`/`userName` but never
  covered body-level PII fields. Commit `2cf7a20` ("security: harden local token and data
  handling", part of PR #379) deleted these files from HEAD but did NOT rewrite git history —
  confirmed live: a fresh `git clone` + `git show 2ae0eb5:tests/cassettes/test_body_composition.yaml`
  still recovers the real data today. Classic incomplete-remediation-of-a-labeled-security-fix
  pattern.

- #3817 (2026-08-07): `gearUUID` (and `userProfileNumber` in `get_gear`) is never format-
  validated before being f-string-interpolated into the request URL, unlike every numeric ID in
  the library (`_validate_positive_integer`) and unlike `hole_numbers`/`sport` after the project's
  own most recent commit `1cca0c6` explicitly fixed the identical class of bug ("closing an
  injection path"). `requests`/`urllib3` normalize `../` path segments client-side before
  sending, so a crafted `gearUUID` walks the request out of `gear-service` entirely into any other
  `connectapi.garmin.com` path — with the real `Authorization` header still attached (confused-
  deputy/SSRF-within-Garmin's-API-surface). Two of the four affected methods
  (`add_gear_to_activity`, `remove_gear_from_activity`) issue a **PUT**, not just a GET — live-
  verified with `requests.Session.send` monkeypatched to capture (not send) the real prepared
  request from the unmodified library: `remove_gear_from_activity("../../../usersummary-service/
  usersummary/daily/12345", 999)` produced `PUT https://connectapi.garmin.com/usersummary-
  service/usersummary/daily/12345/activity/999` with a real Authorization header, completely
  escaping the intended gear-service endpoint. Also found (NOT separately reported, same root
  cause + same fix already covers them, just noted for context): `get_gear_defaults`
  (`userProfileNumber` unvalidated, in a PATH position this time:
  `/gear-service/gear/user/{userProfileNumber}/activityTypes`) and `set_gear_default`
  (`gearUUID` AND `activityType` both unvalidated, dynamically issues PUT or DELETE depending on
  the `defaultGear` bool) — confirms this is a systemic gap across the whole gear feature area
  (6 functions total), not an isolated case.
- #3823 (2026-08-07): same root-cause bug, 2nd distinct cluster — `delete_weigh_in`'s
  `weight_pk` and `delete_blood_pressure`'s `version` (AND `delete_blood_pressure` also skips the
  `_validate_date_format` call on `cdate` that every other `cdate`-taking method in the file has —
  2 independently exploitable params in one function). Both issue **DELETE** (destructive, unlike
  gear's mixed GET/PUT). Live-verified: `delete_weigh_in("../../../../usersummary-service/
  usersummary/daily/12345", "2026-08-01")` → clean escape to `DELETE .../usersummary-service/
  usersummary/daily/12345` with real Authorization header; same for `delete_blood_pressure` via
  either `version` or `cdate` independently.
- #3824 (2026-08-07): 3rd distinct cluster — `set_activity_name`/`set_activity_type`/
  `set_activity_description` skip `activity_id` validation entirely, unlike every other
  `activity_id`-taking method in the file (a dozen+ siblings correctly validate it) — a clear
  isolated inconsistency on the library's single most-used resource ID, not "author never
  thought about it." All 3 issue PUT. Live-verified:
  `set_activity_name("../../../usersummary-service/usersummary/daily/12345", "x")` → clean
  escape to `PUT .../usersummary-service/usersummary/daily/12345` with real Authorization header.

**Pattern summary**: 3 separate reports (#3817/#3823/#3824) covering the identical root cause
(unvalidated string ID f-string-interpolated into request path; `requests`/`urllib3` normalize
`../` client-side; `Authorization` header always attached regardless of final path) recurring
independently across gear, weight/blood-pressure, and activity-metadata feature areas — strong
evidence for the "add a defense-in-depth `..`-segment check in `_run_request()`" fix recommended
in all three, since per-method validation has now been shown unreliable 3 times over in
otherwise-careful code (the project already validates activity_id correctly everywhere else).
Did NOT submit separate reports for `get_gear_defaults`/`set_gear_default` (same cluster as
#3817, noted above) — judgment call: same cluster+fix, vs. #3823/#3824 which are genuinely
different code areas.

- #3843 (2026-08-07): built an automated harness (introspect every public `Garmin` method,
  substitute a traversal payload into each string param in turn, capture the prepared request via
  monkeypatched `requests.Session.send`, no real network calls) to systematically confirm there
  were no MORE instances beyond the 3 already-reported clusters. Found 3 more:
  `get_gear_defaults` (userProfileNumber), `set_gear_default` (activityType AND gearUUID,
  dynamically PUT or DELETE depending on `defaultGear`), `download_activity` (activity_id, GET,
  returns raw bytes — an authenticated arbitrary-endpoint-read primitive). Also corrects a naming
  mistake in #3817: the function I called `get_activities_by_gear` there is actually named
  `get_gear_activities` in the source (the quoted code was right, only the label was wrong — no
  way to edit an already-submitted Secur0 report, so this went out as a note in #3843 instead).
  Confirmed via the fuzzer that these 4 reports (#3817/#3823/#3824/#3843) are now the COMPLETE
  set — every other string parameter across ~150 public methods is properly validated.

- #3920 (2026-08-08): re-checked the repo after the maintainer pushed new commits same-day
  (`cbbcb00`/`86d8ef4`/`4cce5ca`/`46ab4eb`, a security-hardening round: gitleaks pre-commit hook,
  cassette sanitiser unified for request+response, and `tests/12129115726_ACTIVITY.fit` — a real
  physical-device recording — replaced with a synthetic one). The new fixture-removal commit
  (`46ab4eb`) itself confirmed the old file was "a real physical-device recording containing
  biometric PII" but only deleted it from HEAD, same incomplete-remediation pattern as #3812 —
  except this is a genuinely different artifact (binary FIT, added by an unrelated 2023 commit
  `38ec4d9`, never touched by the original `2cf7a20` fix that only covered the YAML cassettes).
  Recovered via `git show 38ec4d9:tests/12129115726_ACTIVITY.fit`, decoded with `fitparse`: real
  gender/height/weight, sleep/wake times, HR zone thresholds, named paired Bluetooth devices
  (a Garmin HRM-Pro strap + Beats earbuds), and a real per-second heart-rate/temperature workout
  recording. Swept full history for any other non-`.py` test fixtures first (`git log --all
  --diff-filter=A --name-only -- 'tests/*'`) — confirmed only the 17 already-reported YAML
  cassettes + this one FIT file were ever committed, so this closes out the git-history-PII
  angle completely for this repo.

- #3851 (2026-08-07): genuinely NEW vulnerability class, not the path-traversal family — CWE-59
  symlink following. `Client.dump()` (writing tokens) was already hardened with explicit
  `O_NOFOLLOW` against symlink attacks by the prior fix for `GHSA-wjhr-76vg-2hvc`, but
  `Client.load()` (reading tokens back, reached from the primary public `Garmin.login(
  tokenstore=...)` entry point) still uses plain `Path.read_text()`, which follows symlinks with
  no protection at all — the fix only covered the write side. Live-verified, zero network calls:
  planted a symlink at a "victim" token path pointing to an attacker-controlled JSON file with
  fabricated `di_token`/`di_refresh_token`/`di_client_id`; `Client().load(victim_path)` silently
  adopted the attacker's values, `is_authenticated` became `True`. On a shared host (CI runner,
  shared dev box — the exact threat model the original GHSA already treats as legitimate), a
  local attacker can substitute their own Garmin session into a victim's automation before it
  runs, with no error. Distinct root cause from #3817/#3823/#3824/#3843 (auth/session-handling
  bug, not URL-construction) — found by re-reading the ALREADY-FIXED GHSA commit and asking "did
  this fix cover BOTH directions (read and write) of the same risk?", not by more fuzzing.

## IMPORTANT SAFETY LESSON — accidental live network calls during automated fuzzing (2026-08-07)

While building the systematic fuzzer for #3843, an early version called EVERY public method
including `login(tokenstore=<traversal payload>)`. Since the fake tokenstore path wasn't a valid
token file, the code fell through to the real credential-based login strategy chain using the
throwaway `poc@example.com`/`unused` credentials set at `Garmin()` construction. The mock only
patched Python's `requests.Session.send` — this library ALSO uses `curl_cffi` for some of its 5
login strategies, which is a SEPARATE HTTP stack not covered by that mock. Result: **3 real login
attempts with garbage credentials went out to Garmin's live authentication servers** (one got
HTTP 429 rate-limited, two failed cleanly) before this was caught mid-run. No real account was
touched (nonsense credentials), but it was real, unintended traffic to a live third-party
production service. Disclosed transparently to the user immediately upon discovery.

**Lesson for any future automated method-fuzzing on ANY target**: before writing an introspect-
and-call-every-method harness, explicitly identify and hard-exclude any method whose PURPOSE is
to reach a real external auth/session endpoint (`login`, `logout`, `resume_login` here — look for
the equivalent on other targets) BEFORE the first run, not after. Also check whether the target
library uses more than one HTTP stack (this one uses both `requests` and `curl_cffi`) and mock
ALL of them, not just the first one found — a partial mock is worse than no mock, because it
creates false confidence that network calls are contained.

## Codebase notes (well-hardened areas — checked, no finding)
- Token storage (`client.py`'s `dump()`): already fixed a real GHSA (GHSA-wjhr-76vg-2hvc,
  world-readable token file) via commit `77a3837` — now uses `os.open(O_CREAT|O_WRONLY|O_TRUNC,
  0o600)` with `O_NOFOLLOW`, 0o700 parent dir, unconditional chmod. Solid.
- No subprocess/eval/pickle/yaml.load/tarfile/zipfile/shell=True anywhere in `garminconnect/`.
- No XML parsing at all (no XXE surface) — Garmin's TCX/GPX handling is all pass-through bytes,
  never parsed locally.
- `fit.py` is FIT *encoding* only (library generates FIT files to upload from trusted internal
  data) — no untrusted-binary-parsing surface, unlike a typical FIT/GPX parser library.
- `exercises.py` (2635 lines) is a pure static data catalog (1527 exercise name/category tuples),
  not executable logic.
- JWT payload decoding (`_extract_client_id_from_jwt`/`_token_expires_soon` in `client.py`) is
  read-only local bookkeeping (expiry/client_id extraction), never used as an authorization
  decision — the token itself is verified server-side by Garmin, so missing signature
  verification locally is not a vulnerability here.
- MFA "shelving" mechanism (`_MFA_STATE_ATTRS`, `client.py` ~line 143-450) is complex but purely
  in-process/in-memory state during a single `login()` call (falling back between login
  strategies), not persisted, not a multi-user/session-confusion vector.
- No SSL verification bypass (`verify=False`), no secrets logged via `_LOGGER`.
- `download_activity()` takes `activity_id` unvalidated (unlike sibling methods that use
  `_validate_positive_integer`) and interpolates it into a Garmin API URL — but this is
  developer-supplied input in normal use (the calling app decides the activity_id), not
  attacker-reachable from outside the library itself; weak/self-inflicted story, not pursued.

## Technique notes
- `git log --oneline -i --grep="security|vulnerab|CVE|traversal|injection|leak|secret|sanitiz|permission|symlink"`
  across full history immediately surfaced both a real GHSA (already fixed, verified complete)
  and the incomplete-fix PII-in-history issue — very high-value first move on any GitHub-source
  VDP with real commit history. Do this before manual code reading.
- When a commit message says "security fix" and *deletes* files rather than rewriting history,
  always check whether the data is still reachable via `git show <old-commit>:<path>` — deletion
  alone never removes git history, and maintainers doing their own remediation frequently miss
  this distinction (matches [[feedback_verify_fixed_closures]]).
- When a maintainer pushes a same-day "security hardening" batch after a submitted finding
  (2026-08-08 here), don't assume it's just closing the reported issue — diff every touched file
  against what the original report actually covered. `46ab4eb` removed a fixture the reporter
  never mentioned (#3812 named 17 YAML cassettes, not this FIT binary), so it was a genuinely new,
  submittable instance of the same class, not a duplicate. Worth re-running the full-history sweep
  (`git log --all --diff-filter=A --name-only`) any time a new fixture-removal commit lands.

## Re-audit after maintainer's 2026-08-08 security-hardening commits
Local checkout's `master` had diverged from `origin/master` (522/523 commits apart — harmless,
probably an artifact of an earlier `git filter-repo`-style local experiment); used `git worktree
add <path> origin/master` to get a clean read-only copy of the real current tip without touching
the local branch. Built a two-pass no-network fuzzer (monkeypatches `requests.Session.send`, the
single choke point every API call funnels through via `Client._run_request` — much simpler and
safer than the original #3843 approach of mocking both `requests` and `curl_cffi`, and this repo's
login/logout/resume_login never touch `_run_request` at all so they're structurally excluded, not
just denylisted by name):
- Pass 1: every public method, every plain `str`-annotated param → traversal payload. Reproduced
  exactly the already-reported cluster (gear/weight/blood-pressure/activity-metadata/
  download_activity) and nothing new.
- Pass 2: every public method, every param typed as a `str`-accepting union (`int | str`,
  `int | str | None` — the newer workout/golf/scheduled-workout methods added since our reports
  use this pattern and pass 1's exact-`str`-annotation filter silently skipped all of them). Every
  one of these (`update_workout`, `schedule_workout`, `push_workout_to_device`, `delete_workout`,
  `download_workout`, `get_golf_scorecard`, `get_golf_shot_data`, `get_scheduled_workout_by_id`,
  `add_gear_to_activity`/`remove_gear_from_activity`, `get_activity_exercise_sets`,
  `get_training_plan_by_id`, `get_adaptive_training_plan_by_id`) now rejects the traversal payload
  before any request — they all do `_validate_positive_integer(int(x))`, so a non-numeric string
  raises `ValueError` immediately. Reads as the maintainer generalizing ID validation project-wide
  after #3817/#3823/#3824/#3843, not a coincidence.
- A few `[CALL]` hits were query-string values (`activityType`, `sortOrder` in `get_activities`/
  `get_activities_by_date`) with the traversal string properly percent-encoded (`%2F`) by
  `requests` — not exploitable, `/` inside a query value has no path-traversal semantics.
  `get_lactate_threshold`'s `start_date`/`end_date` are legitimately unused when `latest=True`
  (documented default, not a bug). `push_workout_to_device`'s one `[CALL]` was just the harness
  hitting `KeyError` on a mocked empty dict from `get_device_last_used()` before reaching its own
  `_validate_positive_integer(int(workout_id))` — confirmed safe by reading the source, not by a
  deeper mock.
- Re-swept full history for any non-`.py` test fixture beyond the 17 YAML cassettes + the one FIT
  file already reported (#3812/#3920) — none found; `tests/cassettes/` no longer exists in the
  tree and no cassette file was ever added after the original fix commit.
- `docs/graphql_queries.txt` (which the original PII fix commit rewrote from 23673 to 162 lines)
  is now template-only query strings, no real data.
- `activity_details.py`, `typed.py`, `workout.py`, `fit.py` (previously unexplored) — grepped for
  eval/exec/subprocess/pickle/yaml.load/os.system: none. `activity_details.py` read in full: pure
  dict-reindexing logic, no injection surface.
- **Conclusion: no new submittable finding found in this pass beyond #3920.** The library's
  attack surface for the vuln classes already mined (path traversal, PII-in-history) now reads as
  fully closed out and hardened.

## test_login_recovery.py / test_mfa_shelving.py review (2026-08-08) — checked, not submitted
Read both files manually, then dynamically verified the one interesting lead by fully mocking
`cffi_requests.Session` (injecting a fake module since curl_cffi isn't installed in this sandbox)
so the REAL `_widget_web_login()` body ran end-to-end against fabricated HTML — zero real network
calls, same safe pattern as the earlier `requests.Session.send` fuzzers, just one level lower
since login doesn't go through `_run_request`.

**Found (real, dynamically confirmed, but NOT security-relevant):** the "shelve uncertain widget
MFA" safety mechanism in `client.py`'s `login()` is dead code in production. `_mfa_delivery_uncertain`
is read at line ~414 to decide whether to shelve widget's MFA state and let later (portal)
strategies try first, and reset to `False` at the top of every strategy attempt — but grepping the
*entire* file shows it is **never set to `True` anywhere in the real strategy code**
(`_widget_web_login`, `_widget_request_mfa_code`), only inside `tests/test_mfa_shelving.py`'s mock
strategies that manually set it to simulate what the docstrings say should happen. Confirmed
dynamically: drove the real `_widget_web_login()` through a fabricated "email MFA, code not yet
sent" widget page (exactly the scenario the docstrings name as the trigger) and `_mfa_delivery_uncertain`
stayed `False` afterward. So widget+cffi's MFA state is always treated as fully trusted and resolved
immediately via `resolve_mfa()`, and portal's "known to trigger delivery" MFA flow never gets a
chance — contradicting 5 dedicated unit tests and multiple docstrings that describe the opposite
behavior.

**Why not submitted:** no attacker-controlled trigger — this only affects the account holder's own
login attempt with their own credentials, and `_complete_mfa`'s flow-based dispatch (`widget` ->
`_complete_mfa_widget`, others -> the shared JSON-API path) is otherwise correct, so there's no
session/credential cross-contamination between strategies (`_MFA_STATE_ATTRS` snapshot/restore
around shelving is correctly reference-safe too). Worst case is a wasted MFA attempt/extra login
failure for the legitimate user in an edge case, self-inflicted by the library, not attacker-
reachable — matches [[feedback_needs_real_victim]] and [[feedback_no_informational_reports]].
This is a correctness/reliability bug worth a plain GitHub issue, not a Secur0 report.

Everything else in both files checked out correctly against the real source: token self-healing
(poisoned cached token -> discard -> fresh chain -> retry), `_verify_token()` 401/403 vs 5xx
handling, `_clear_auth_state()`, `logout()` file clearing, and `_complete_mfa` flow-name routing
all match their real implementations with no discrepancy. Login-surface review is now complete for
this target — nothing further to chase here.

## Dedicated push for a "real victim + data exfil" finding beyond what's submitted (2026-08-08)
User explicitly asked to push further for victim-impact/data-exfiltration, since the MFA-shelving
bug above has none. Checked, in order of how promising each looked, all against the current
`origin/master` tree:
- **Shared/global mutable state across `Garmin()` instances** (the "one library instance leaks
  user A's data to user B" pattern that matters for any server-side/multi-tenant consumer of this
  library) — none found. No module-level cache dicts, no `@lru_cache`/`functools.cache`, only one
  `@functools.cached_property` (`__init__.py:587`) which is per-instance (`self.__dict__`), not
  shared. `EXERCISES`/`BY_NAME`/`CATEGORIES` in `exercises.py` are static read-only reference data.
- **Stored XSS in `demo.py`'s generated HTML health report** via attacker-influenceable fields
  (activity name, device name — an activity name IS settable by the account itself via
  `set_activity_name()`, and conceivably a synced third-party device could set a crafted device
  name) — ruled out. Every single interpolated value across all 21 `html_content +=` blocks goes
  through a dedicated `_html()` escaper (`demo.py:96`, `html.escape(str(value), quote=True)`,
  docstring literally says "Escape data returned by Garmin before inserting it into HTML") — no
  gaps found after reading the full block (`demo.py:940-1170`).
- **Path traversal in exported filenames** (the write-side analog of the 4 already-reported
  read-side URL-path traversal bugs) via activity/workout names in `demo.py`'s file-export code —
  ruled out. A dedicated `_safe_filename_component()` (`demo.py:101`) strips everything except
  `\w .-` then strips leading/trailing space/dot, consistently applied at every filename-from-
  API-data call site (`demo.py:709,1770-1771,2323-2324`); confirmed neither `/` nor `\` can survive
  the allowlist, and an all-`.`/all-space value collapses to empty -> falls back to `"export"`.
  `_open_private()` (`demo.py:77`) also independently hardened: `O_NOFOLLOW` + `0o600` + `fchmod`
  on every export file write, so no world-readable-local-file variant of the token-store GHSA
  either.
- **Response-driven SSRF** (library follows a URL *returned by* Garmin's API, as opposed to the
  already-reported request-side path-interpolation bugs) and **GraphQL injection** (a built-in
  method f-string-interpolating untrusted text into one of `docs/graphql_queries.txt`'s query
  templates) — grepped for both patterns project-wide, found no built-in method that constructs a
  GraphQL query string from a variable parameter (`query_garmin_graphql()` takes a pre-built
  `dict` — an intentional raw passthrough, caller's own responsibility) and no code that extracts
  and re-fetches a URL from a JSON response body.
- **CSV/formula injection** in any exported file — no CSV writer anywhere in the repo (`grep -rn
  "csv\."` returns nothing); the demo's "CSV" download format is actually just
  `get_activity_details()` dumped as JSON (`demo.py` ~1780), not an actual CSV serializer.

**Conclusion: no new victim-facing finding found.** This is now the third independent pass (this
session) confirming the same thing from different angles — the codebase's write/output-handling
paths are unusually thoroughly hardened (dedicated escaper + filename-sanitizer + O_NOFOLLOW
helpers already exist and are consistently applied everywhere they're needed), consistent with the
already-hardened surface documented above. Not recommending further time here without a new signal
(e.g. a future commit touching `demo.py`'s export code or adding a new response-following feature).
