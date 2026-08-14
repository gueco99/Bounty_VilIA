---
name: project-sodapy
description: "sodapy (github.com/afeld/sodapy) hunt state — fresh CVE-eligible VDP, Python client for Socrata Open Data API. 4 findings SUBMITTED: #3494 path traversal (Critical), #3500 set_permission no validation (Low), #3506 delete row_id=0 truthy bug (High), #3512 unescaped dataset_identifier/row_id URL path IDOR (Medium)"
metadata:
  node_type: memory
  type: project
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

Target: `github.com/afeld/sodapy` — small, focused Python client library for the Socrata
Open Data API (used by many government/open-data portals). Fresh VDP, went active
2026-08-04 18:00, CVE-eligible, Safe Harbor, 0 reports at session start. Small codebase
(`sodapy/socrata.py`, `sodapy/utils.py`, `sodapy/constants.py`) — the only method that
writes to the local filesystem is `download_attachments`.

**Finding #1 SUBMITTED (report_id 3494, Critical): path traversal in
`download_attachments()` → arbitrary file overwrite.** `Socrata.download_attachments()`
builds `file_path = os.path.join(download_dir, attachment["filename"])` where
`attachment["filename"]` comes directly from the dataset's metadata as returned by the
configured Socrata domain (i.e. attacker-controlled if the attacker owns/can edit any
dataset's attachment metadata on a shared/open Socrata instance) — zero sanitization of
`../` sequences, no `os.path.basename()`, no containment check. `utils.download_file()`
then does `open(local_filename, "wb")` and streams the attachment content straight in,
truncating/overwriting whatever's at that resolved path. Confirmed live with a full,
runnable PoC (poc.py, attached to the report) that imports the REAL, unmodified
`sodapy.Socrata` class (only mocks `get_metadata()`'s return value and `requests.get`,
i.e. only the network layer) — a crafted `filename: "../../.bashrc"` completely
overwrote a real, pre-existing `.bashrc` file with attacker-chosen content
(`curl ... | sh`), outside the intended `download_dir` entirely. No caveats needed here
(unlike most of the kinopio-client findings this session) — the entire vulnerable
code path (path join + file write) lives in this repo, no assumption about
out-of-scope server behavior required.

**Finding #2 SUBMITTED (report_id 3500, Low, business-logic angle): set_permission()
has zero input validation on a security-critical parameter.** `value: "public.read" if
permission == "public" else permission` — only the exact string "public" gets
translated; EVERYTHING else (the documented "private" default, any typo/casing/
whitespace mistake, None) passes through completely unvalidated and unchanged to the
server, with no exception, no warning, no signal to the caller that anything went
wrong. Confirmed the exact pass-through behavior for 9 different inputs. Same honest
"can't verify server-side handling of invalid values" caveat as most kinopio-client
business-logic reports — framed around the concrete, verifiable client-side gap (no
early feedback loop for a security-critical "make this dataset private" operation)
rather than claiming confirmed public-data exposure.

**Finding #3 SUBMITTED (report_id 3506, High, most severe sodapy finding so far):
`delete(dataset_id, row_id=0)` deletes the ENTIRE dataset instead of one row.**
`if row_id:` is a truthiness check, not `is not None` — integer `0` (an entirely
ordinary, legitimate row identifier value) is falsy, so it falls through to the SAME
branch as "no row_id provided at all", building a whole-dataset-delete request instead
of a single-row-delete request. Confirmed deterministically from the client code alone
(no server-behavior assumption needed, unlike #3500/#3494's framing) — the wrong HTTP
request gets constructed before the server is ever involved. `row_id=""` has the same
issue. This is the strongest of the three sodapy findings precisely because it needs
zero hedging: it's a pure client-side logic bug with a 100%-reproducible, unambiguous
consequence (irreversible full dataset loss instead of a minor row edit).

**Finding #4 SUBMITTED (report_id 3512, Medium, broadest-impact sodapy finding):
unescaped dataset_identifier/row_id in URL path construction, affects nearly every
method.** `format_old_api_request`/`format_new_api_request` (utils.py) interpolate
`dataid`/`row_id` directly into the URL path via plain `.format()`, no
`urllib.parse.quote()`, no rejection of `/`/`..`. Affects `get`, `get_all`, `upsert`,
`replace`, `get_metadata`, `update_metadata`, `set_permission`, `publish`, `delete` —
essentially every method taking a dataset/row identifier. Confirmed with a REAL local
HTTP server + real `requests.get()` call (not just string analysis) that `requests`
itself normalizes `../` sequences in the URL path BEFORE sending — server received
`/victim-dataset-id/some-row.json` with zero trace of the intended prefix, fully
client-side-confirmed traversal with no server-behavior assumption needed. Realistic
trigger: any app built on sodapy that lets an end user specify "which of MY rows" to
touch, passing that value straight through as row_id (natural, common integration
pattern) — classic IDOR/broken-object-level-auth via path traversal. This was found
by reconsidering `format_new_api_request`/`format_old_api_request` (already read once
for #3506) with fresh eyes per the user's explicit "mira en cosas poco exploradas"
prompt — the row_id fix I'd just recommended for #3506 uses `format_new_api_request`
directly, and re-reading THAT function is what surfaced the unescaped-interpolation
issue.

**Finding #5 SUBMITTED (report_id 3522, High, strongest-demonstrated-impact sodapy
finding): download_attachments' assetId/blobId (not filename) also unescaped in URL,
redirects the VICTIM's own authenticated request to an unrelated path.** Separate,
uncovered code location within the same function as #3494 — `attachment["assetId"]`/
`attachment["blobId"]` interpolated unescaped into the download URL path (distinct
from the already-fixed-recommendation `filename`-in-local-path issue). Built a full
end-to-end PoC (poc.py + poc_server.py, both attached) using the REAL unmodified
sodapy code against a REAL local HTTP server (only `get_metadata()` mocked — the
actual `requests.get()` network call is 100% real) with two distinguishable paths (a
generic one and a "CONFIDENTIAL" one). Result: the real HTTP request landed exactly on
the crafted traversal target, and the confidential content got written locally under
an attacker-chosen innocuous filename. Framed as confused-deputy/SSRF-adjacent:
because the request uses the VICTIM's own authenticated session (whatever
app_token/basic-auth/OAuth token they configured), the attacker can potentially reach
paths on the domain THEY themselves could never access, using the victim's identity to
do the fetching. User's explicit call after I raised the overlap-with-#3494 concern via
AskUserQuestion (which they declined, saying just build a real PoC and send if it
holds up) — did exactly that, impact confirmed live, submitted directly per their
"si es asi envialo" instruction rather than re-asking.

**Finding #6 SUBMITTED (report_id 3536, High, deepest-dig sodapy finding): dataset_identifier
alone (not just attachment filename) escapes download_attachments' base directory —
my own #3494 fix suggestion was incomplete.** `download_dir = os.path.join(os.path.
expanduser(download_dir), dataset_identifier)` runs BEFORE the attachment loop, with
zero sanitization of `dataset_identifier` itself (the method's own first argument).
Built a PoC with a COMPLETELY BENIGN attachment filename ("totally-normal-report.pdf",
zero traversal chars) and only a malicious `dataset_identifier` — the file still
escaped, actually landing OUTSIDE even the test's own temp sandbox (one level further
than expected, confirming the escape is more severe than initially modeled). Verified
by actually opening and reading back the file at the resolved path (not just inspecting
the returned path string). This means: a maintainer who applies ONLY my #3494 fix
recommendation (sanitize `attachment["filename"]`) would leave this exact impact class
fully open — both values need independent validation. Found by following the user's
explicit "profundiza mucho mas" instruction — went back to an ALREADY-submitted finding
(#3494) and re-read the SAME function one line earlier than where I'd focused before,
rather than surveying new files.

**Finding #7 SUBMITTED (report_id 3543, Low-Medium, genuinely new vuln class): app_token
leaks to a different host on cross-domain HTTP redirect.** `self.session.headers.update({
"X-App-token": app_token})` — a sticky, session-level custom header. `requests` has
built-in protection stripping the STANDARD `Authorization` header (and a couple others)
on a cross-host 3xx redirect, but has no way to know an arbitrary custom header like
`X-App-token` is sensitive, so it's NOT stripped. Confirmed side-by-side, empirically,
with the same client/same redirect: `Authorization` correctly withheld from the
different host, `X-App-token` sent in full. This came from FIRST verifying (not
assuming) that the Authorization-header protection I'd been relying on as a "closed"
assumption in earlier reports actually holds for sodapy specifically — it does — and
then asking "does the SAME protection extend to app_token specifically" (a genuinely
different header, set via a different mechanism) rather than treating the whole
credential-handling area as settled. Found by continuing to "profundiza"/"sigue
buscando" into credential handling one layer deeper than the earlier "no
cross-domain Authorization leak" note in the second-pass re-audit already covered.

**Pipeline note:** this program's `GET /programs/details` showed `is_guideline_signed:
false` even AFTER a successful `POST /guidelines/sign/{id}` call (which itself then
returned `"already_signed": true` on retry) — confirms the previously-documented
"brand-new program provisioning lag" ([[reference_secur0_api_pipeline]]) is a genuine,
reproducible read-after-write staleness on Secur0's side, not a one-off. Retrying the
actual `create_report` call (not the sign call) succeeded despite the stale details
read — don't be blocked by a stale `is_guideline_signed:false` on a same-day-activated
program if the sign endpoint itself reports success/already-signed.

**2026-08-04 second-pass re-audit (full re-read of socrata.py + utils.py, all 651 lines):**
covered everything previously marked "not yet audited" — get/get_all/upsert/replace/
create/create_non_data_file/replace_non_data_file, SoQL `$where`/`$query` construction
(caller-controlled params passed through as-is, injection responsibility sits with the
calling app, not sodapy), basic-auth-over-Session credential handling (no cross-domain
Authorization leak — requests strips it on cross-host redirect; plaintext-HTTP exposure
would require the caller to opt into a custom `session_adapter`, not a sodapy bug),
`constants.py` (trivial). No `eval`/`exec`/`pickle`/`yaml.load`/`subprocess` anywhere in
the codebase. One candidate considered and correctly KILLED per the 7-Question Gate:
`utils.download_file()` passes no `timeout` to `requests.get()` (unlike every other
request, which goes through `_perform_request()`'s `kwargs["timeout"] = self.timeout`) —
confirmed live with a real non-responding TCP listener (hung past an 8s budget, no
`Timeout` raised). Killed because: (1) impact is just a hung call, no data loss, no
confirmed thread-pool exhaustion (that was unverified speculation); (2) exploiting it
needs the exact same attacker precondition as the already-submitted Critical #3494, so
it's a strict downgrade for an attacker who already has that access, not a new
escalation; (3) any ordinary slow server triggers identical behavior, blurring
robustness-bug vs. attacker-specific vuln; (4) near-neighbor of "Rate limit on
non-critical forms" on this repo's own NEVER SUBMIT LIST. Conclusion: the 4 submitted
findings appear to be full coverage of this codebase's real, non-theoretical bugs.
