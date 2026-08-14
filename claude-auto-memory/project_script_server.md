---
name: project-script-server
description: "script-server (github.com/bugy/script-server) hunt state — Python/Tornado web UI for running admin-configured scripts, CVE-eligible VDP, 0 reports at start"
metadata: 
  node_type: memory
  type: project
  originSessionId: ff7451f9-ed99-4be8-8d13-3103f0c4f6ba
---

Active as of 2026-07-31. Program: **script-server**, CVE-eligible VDP, safe harbor, 0 prior
reports. In scope: `github.com/bugy/script-server` only. Web UI (Python/Tornado backend +
Vue frontend) that lets an admin register scripts and grant specific users access to run them
with validated parameters via a web form — the core security promise is "users can only run
the specific scripts they're allowed to, with the specific parameters offered."

**Finding #1 — SUBMITTED (report_id 3153, 2026-07-31), CRITICAL, high confidence:**
`findings/script-server-file-upload-arbitrary-write/report_secur0.md` — the multipart-upload
`filename` field (100% client-controlled) flows unsanitized into
`os.path.join(files_path, self.filename)` in `_FormDataPart.__init__`
(`src/web/streaming_form_reader.py`), then gets opened for writing. An absolute path or `../`
traversal in `filename` writes the uploaded content to an arbitrary location on disk. Any user
permitted to run even ONE script with a `file_upload` parameter (a normal, common parameter
type) can exploit this — a direct route to overwriting `conf/access_config.json` (self-granted
admin), cron/systemd/authorized_keys (RCE), or other users' data. Confirmed with TWO real PoCs:
(1) isolated unit-level test of the unmodified `StreamingFormReader` class, (2) full,
real HTTP end-to-end request (including proper XSRF token handling) against a locally-run
instance built from source — both wrote to an attacker-chosen absolute path
(`/tmp/PWNED_...txt`), confirmed via `cat` on the actual resulting file.

**Finding #2 — SUBMITTED (report_id 3179, 2026-07-31), HIGH, high confidence:**
`findings/dia2/script-server-server-file-parameter-path-traversal-file-read/report_secur0.md` —
`ParameterModel._validate_recursive_path()` (`src/model/parameter_config.py`) rejects a `path`
list only if some element is *exactly* `'.'`/`'..'` (list-membership, not substring search), so
a non-final segment like `'../.'` sails through, and `_build_list_file_path()`
(`os.path.normpath(os.path.join(...))`) resolves it outside `file_dir` anyway. The final-segment
check (`file not in allowed_files`) only re-validates the last element, never that the escaped
`dir_path` is still inside `file_dir`. `normalize_user_value()` passes lists through untouched,
and submitting the same multipart form field name twice (`put_multivalue` in
`src/utils/collection_utils.py`) is enough to build the attacker's multi-element list — no
traversal-in-a-single-string needed. This validated-but-unsafe value flows straight into
`map_to_script()` → the actual script's command-line argument, so it's a real arbitrary-file-read
via the normal `/executions/start` execution path, not just an auxiliary listing/browsing UI.
CVSS: `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:H/SI:N/SA:N`. Confirmed with a full
live HTTP PoC against a locally-run instance: two `myfile` form fields (`../.` + `secret.txt`)
made the executed script `cat` and return the real content of a file one directory above the
configured `file_dir` (`SECRET_CONTENT_OUTSIDE_ALLOWED_DIR`), verified via
`GET /history/execution_log/long/<id>`. Same attacker model as Finding #1 (any user permitted to
run one script with this common parameter type), same suggested fix pattern
(`os.path.realpath`/`commonpath` containment check).

**Finding #3 — SUBMITTED (report_id 3184, 2026-07-31), HIGH, high confidence:**
`findings/dia2/script-server-outputfiles-parameter-traversal-arbitrary-file-read/report_secur0.md`
— `model_helper.fill_parameter_values()` substitutes a parameter's raw `mapped_script_value`
into an `output_files` template (`"${paramName}"`) via naive string `.replace()`, with zero
path validation, and `file_download_feature._prepare_downloadable_files()` then `copyfile()`s
whatever that resolves to (via `file_utils.normalize_path()`, which returns an absolute value
verbatim) straight into the requesting user's own results folder — which is downloadable
through the normal, fully-authorized `/result_files/*` endpoint since it's now genuinely inside
their own per-user folder. Broader than Finding #2: works with **any plain parameter type**
referenced in `output_files`, not just `server_file` — and it's the exact pattern the project's
own bundled sample ships (`samples/configs/write_file.json`: `"output_files": ["~/${filename}"]`
with an unrestricted `filename` text parameter). Confirmed with a full live HTTP PoC: a script
that does nothing with the parameter (`echo done`) still let an absolute-path `filename` value
pointing at a file completely outside the script's directory get copied into
`temp/resultFiles/<user>/<ts>/` and then downloaded via `GET /result_files/<user>/<ts>/<name>`
with its real secret content, HTTP 200. CVSS: same shape as Finding #2,
`CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:H/SI:N/SA:N`.

**Log-injection / user_id forgery in execution history — investigated, correctly NOT submitted:**
`ExecutionLoggingService.start_logging()` writes an unescaped `command:` line into a
`key:value`-parsed log header, and a parameter value with an embedded newline + `user_id:X` can
make `_parse_history_parameters` overwrite the real `user_id` field with an attacker-chosen
string (confirmed live: real owner `127.0.0.1` locked out, forged `FORGED_ADMIN_IDENTITY` let in
by `is_same_user()`). Looked like a real CWE-117+CWE-863 bug at first (drafted, CVSS
VI:H/VC:L), but the user's pushback caught the actual flaw: the forgery only ever applies to the
ATTACKER'S OWN newly-created execution record — it can't touch a pre-existing file belonging to
someone else. So the "cross-user disclosure" angle was backwards (a victim who ends up seeing
the entry sees the ATTACKER'S OWN command/output, not their own data — the attacker gains
nothing). The only surviving angle is soft audit-trail non-repudiation (an attacker's action
could be misattributed if someone trusts the field during a forensic review) — real but
indirect, no concrete "attacker gains access to something they shouldn't" chain. Correctly
killed per [[feedback_no_informational_reports]] and [[feedback_reproducibility_not_severity]].
Don't re-chase this unless a genuine cross-user WRITE path into someone else's own log file is
found (not just relabeling your own).

**Hypotheses investigated and correctly DISPROVEN this session (don't re-chase these):**
- Windows command injection via `prepare_cmd_for_win` only escaping `&` — REAL bug, but the
  maintainer's own README ("Security" section) already explicitly discloses this exact
  limitation ("Command injection protection is fully supported for Linux, but only for .bat
  and .exe files on Windows") — not a novel/reportable finding.
- XSS via `output_format=html`/script description rendering (`v-html`) — both go through
  DOMPurify correctly, no bypass found, matches the README's OWASP-cheat-sheet claim (only
  disclosed exception is `output_format=html_iframe`, not investigated further as it's already
  disclosed too).
- Unauthenticated 500 crash on `/theme/../...` traversal — real (uncaught `ValueError` in
  `file_utils.relative_path` inside `AuthorizedStaticFileHandler.validate_absolute_path`,
  confirmed live against a running instance) but LOW impact: single-request crash, Tornado
  doesn't die, no data disclosed (debug mode is off, client only sees the generic 500 page).
  Correctly did NOT draft/submit this — matches [[feedback_no_informational_reports]].
- Missing-trailing-slash prefix bug in the SAME `relative_path()` function (naive `.startswith()`
  without separator check) — real code smell, confirmed it silently lets `web-src` pass a check
  meant for `web` — but Tornado's own downstream `validate_absolute_path` (called via `super()`
  right after) correctly catches and 403s it anyway, so no actual bypass results.
- LDAP authentication bypass via empty password ("unauthenticated bind") — the single most
  promising-looking hypothesis, DISPROVEN via a real test: `ldap3` (the library script-server
  uses) itself raises `LDAPPasswordIsMandatoryError` for empty-password simple binds, and
  script-server's own `KNOWN_REJECTIONS` list already treats that exact error string as an
  auth rejection. No bypass.
- Missing `@check_authorization` decorator on `Admin*Endpoint` classes (only `@requires_admin_
  rights`) — looked like a possible full pre-auth bypass, but `has_admin_rights` →
  `identify_user` → `identification.identify()` transitively requires a validly HMAC-signed
  Tornado secure cookie (can't be forged) and throws if absent — safe by construction.
- Open redirect via `next` query param in `tornado_auth.py`'s OAuth callback (`redirect_relative`
  using `urljoin`, naive `startswith('http')` filter bypassed by `//evil.com` protocol-relative
  URLs — confirmed this bypass works via direct `urljoin` testing). **Not drafted**: bare open
  redirects are excluded on essentially every Secur0 VDP program's standard policy template
  seen this session ("unless additional security impact can be demonstrated") and no chain was
  found (HttpOnly cookie, no token leak identified). Parked, not dropped — worth revisiting if
  a chain angle appears, or if the program's actual policy text turns out not to have this
  exclusion (never verified for this specific program).

**Also checked and DISPROVEN/clean this session** (OAuth/authz/admin/history sweep, don't
re-chase): OAuth providers use no `state` param anywhere (auth_abstract_oauth.py) but this is
the already-parked, Tornado-XSRF-covered gap from earlier; Keycloak/Authentik OpenID verify via
a real call to the IdP's `userinfo` endpoint (not manual JWT decoding) — safe; `authorization.py`
`_matches_email_domain_pattern`/`_is_allowed_internal` domain-pattern matching correctly requires
the literal `@domain` boundary, no subdomain/prefix bypass; `AdminScriptEndpoint`/
`AdminUpdateScriptEndpoint`/`AdminGetScriptCodeEndpoint` all properly gated by
`@requires_admin_rights` (safe by construction per the earlier HMAC-cookie finding); execution
history access (`ExecutionLoggingService._can_access_entry`) correctly checks same-user-or-full-
history-access before `find_history_entry`/`find_log` ever run.

**How to apply if resuming**: 3 confirmed, submitted findings now (file-upload write, server_file
read, output_files read) all share the same missing "resolved path must stay inside the intended
root" containment check — worth flagging as one systemic root cause if writing a summary/wrap-up
comment. Unexplored remaining surface: `excluded_files_matcher`/`FileMatcher` glob-pattern
matching itself (could have its own bypass quirks distinct from the containment bugs already
found), the `schedule` feature (`AddSchedule` endpoint, recurring executions — not looked at
yet), and `GetShortHistoryEntriesHandler` (short-history listing, only long-entry access was
checked). Local dev setup: `tools/init.py --no-npm` (downloads a prebuilt `web/` folder from a
GitHub release zip) then `python3 launcher.py` — runs on port 5000, no auth configured by
default in a fresh checkout.
