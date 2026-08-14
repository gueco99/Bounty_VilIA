---
name: project-cogny
description: "cogny (github.com/Maalfer/cogny) hunt state — fresh CVE-eligible VDP, Django notes vault, 13 findings SUBMITTED incl. Critical stored XSS (#3150), a git-history infra/PII leak (#3174), a repeated multi-round SSRF whack-a-mole on the PDF-export sanitizer (redirect/CSS-escape/DNS-rebinding bypasses), a same-day UnicodeDecodeError DoS the maintainer's own fix missed (#3316), and an image decompression-bomb DoS in the WebP auto-recode path (#3317), active hunting continues"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

Target: `github.com/Maalfer/cogny` — Django self-hosted Markdown notes vault ("Obsidian-style"),
notes stored as files on disk (not DB), folders, PDF export via headless Chromium, ZIP
import/export, public share links, API with API keys, single shared vault per instance (roles
owner/editor/viewer only gate write/admin, not content — "la bóveda es una sola y compartida").
Fresh VDP (0 reports at start, program went active 2026-07-31 18:00), CVE-eligible, Safe Harbor,
all Spanish-language code/README/reports. 30-day window from 2026-07-31.

**Finding #1 SUBMITTED (report_id 3117): SSRF + LFI via PDF export.** `apps/notes/pdf.py`'s
`_SAFE_URI_RE` allows `http:`/`https:` schemes and bare absolute paths (which resolve to
`file://` since the render document is loaded via `file://`) in src/href attributes; the
`style` attribute isn't in `_URI_ATTRS` at all so its CSS content isn't filtered whatsoever.
Confirmed LIVE against the real code + real system Chromium (not just regex analysis): (1)
SSRF — outbound HTTP requests to an attacker-controlled listener via both `<img src=http://>`
and `style="background-image:url(http://)"`, real HeadlessChrome User-Agent captured; (2) LFI
— an absolute path to an image file outside any web-served directory got embedded in full,
visible, into the returned PDF (8693 bytes -> 134924 bytes, real `/Image`/`/FlateDecode`
markers). Reachable by the lowest-privilege authenticated role ("viewer") since `notes_pdf`
(views.py:339) has no `@require_write`, only `@login_required`.

**Vault access model already checked (relevant for future IDOR-style ideas on this program):**
all authenticated users (owner/editor/viewer) see the SAME shared vault — role only gates
write/admin, not content visibility. This kills most "user A reads user B's private notes"
IDOR framing for logged-in users; the only real privacy boundary on this app is
authenticated-vault vs. public share-link (unauthenticated) access.

**Noted but not yet pursued, needs more digging:** `shared_note_view`'s `_resolve_asset_ref`
falls back to searching the ENTIRE vault by filename (not just the shared note's own folder)
when a direct path match fails — an editor sharing a note that happens to reference a filename
colliding with an unrelated, private attachment elsewhere in the vault could inadvertently
expose that unrelated file to the public link. Weak/self-inflicted-leaning (the editor already
has full read access to that same file directly) — worth revisiting only if a stronger,
clearly-attacker-vs-victim framing emerges, per [[feedback_reproducibility_not_severity]].

**Finding #2 SUBMITTED (report_id 3133): ReDoS in PATCH /api/v1/notes/content.** The `find`
param with `"regex": true` goes straight into `re.subn(find, replace, new, count=count)`
(apps/api/views.py note_content(), PATCH branch) with zero length/complexity/timeout limit —
Python's `re` (unlike Go's RE2) is vulnerable to catastrophic backtracking. Confirmed live:
`(a+)+$` against 35 chars pegged CPU at 99% and never finished (46s CPU time accumulated in
~8s wall time before I killed it). Requires write access (editor/owner — an API key that isn't
read_only), but since the vault is one shared instance for everyone, this lets a lower-trust
"editor" (GUEST_ROLES, explicitly less trusted than owner) hang/exhaust all gunicorn workers
and deny service to the OWNER and every other user too — a real privilege-direction escalation,
not just self-DoS. Read through apps/api/views.py in full to find this (audited every endpoint:
notes/folders/files/shares/vault/profile/users/keys — no other obvious issues spotted there
besides this one and the already-submitted PDF finding).

**Finding #3 SUBMITTED (report_id 3145): default SECRET_KEY enables signing forgery →
vault-wide unauthenticated file read.** `config/settings/base.py:23` and
`docker-compose.yml:8` both fall back to a hardcoded, public SECRET_KEY if
`DJANGO_SECRET_KEY` isn't set. README's "### Con Docker" section (`docker compose up
--build`) never mentions creating/filling a `.env`, unlike the separate "Desarrollo local"
section right above it that explicitly does — a real, documented-quickstart-driven path to
the insecure default, not just operator negligence. That SECRET_KEY directly signs
`shared_note_asset`'s `p` parameter via `django.core.signing` (apps/notes/views.py) — and
that endpoint is fully unauthenticated and never re-checks the file extension at serve time
(only the URL-building side restricts to images/PDF). Verified live with real
`django.core.signing.dumps/loads` using the exact known default string: forged a valid
signature for an arbitrary vault path with zero server interaction. Chain: known/default
SECRET_KEY (code-level defect, framed carefully as NOT a claim about any specific live
deployment's current state — lesson from the retracted #2307 SECRET_KEY/DEBUG finding on
another program) → forge signature → read ANY file in the whole shared vault (not just
images/PDFs, not just the shared note), fully unauthenticated, needing only one existing
no-password share token to already exist anywhere in the instance.

**Finding #4 SUBMITTED (report_id 3150): stored XSS via unsanitized raw HTML in Markdown,
editor→owner privilege escalation. Most severe cogny finding — CVSS Critical.** Both
`notes.js` (the authenticated editor) and `shared.js` (public unauthenticated share view)
configure `marked.js` v12.0.2 (confirmed via the file's own header) with zero sanitization —
marked dropped its own `sanitize` option in v1.0, upstream-documented decision, recommends
DOMPurify separately, never added here — then assign the result straight to `.innerHTML` (5
call sites total across both files). Verified in two stages, precisely distinguishing what
was live-tested from what was code-verified: (1) ran the exact bundled `marked.min.js` via
real `node`, confirmed `<img src=x onerror=...>` and `<script>` both pass through completely
unescaped; (2) reproduced the exact `marked.use(...) + innerHTML=...` pattern in a minimal
HTML page and opened it with the real system Chromium (`--headless --dump-dom`) — page
`<title>` changed to "XSS-EXECUTED-", confirming actual `onerror` execution, not just raw-tag
presence (script tags are inert via innerHTML per HTML5 spec, but event-handler attributes
fire normally — this is what's exploited, not `<script>`). Because the vault is single/shared
(no per-user isolation), any "editor" (GUEST_ROLES, explicitly lower-trust than owner) writing
a note with this payload gets it executed in the OWNER's session the moment they view that
note. `static/js/csrf.js` globally monkey-patches `window.fetch` to auto-attach the CSRF
token to any same-origin non-GET call, so the payload needs no token-stealing step at all —
confirmed the exact escalation target by reading real code: `POST /api/apikeys/create`
(apps/accounts/urls.py, mounted at root via config/urls.py, view is
`@login_required @require_owner` — session-based, not API-key-based) lets the XSS mint a
brand-new owner-privileged API key and exfiltrate it, giving full persistent API access far
beyond the attacking editor's own role. Explicitly did NOT claim the fetch()-based
account-takeover chain was live-tested end-to-end against a running server (no live instance
available) — report clearly separates the live-confirmed core mechanism (JS execution via
onerror/innerHTML) from the code-verified-but-not-live-chained escalation path, to avoid
overclaiming.

**#3150 addendum, 2026-07-31: full editor→owner escalation chain now confirmed end-to-end**
against a real locally-running Django instance (exact pinned deps, real migrations, real
Client-based HTTP requests) — not just code-verified anymore. Editor saves XSS note (200) →
separate owner session reads it back raw/unsanitized (confirmed byte-identical to what
notes.js would pass to innerHTML) → simulated onerror fetch() using the owner's session
against /api/apikeys/create succeeds (200) and persists a real, full-privilege
(read_only=False) API key under the OWNER's account, verified via direct DB query
(count 0->1, key.user == owner not editor). Closes the one gap the original report flagged.
Also ran pip-audit against requirements.txt (Django 6.0.7/gunicorn 26.0.0/whitenoise
6.12.0/Pillow 12.3.0) — clean, no known CVEs.

**Finding #5 SUBMITTED (report_id 3174): sensitive infra/PII permanently exposed in public git
history.** Commit `089ae55` accidentally replaced the public README with an internal ops
document, reverted one commit later (`fe23b6e`) — but git history is append-only, so
`git show 089ae55:README.md` still recovers it in full, forever, regardless of the later
revert. Contents: the REAL production domain behind Cloudflare (`cogny.fatimaymariosecasan.es`
— domain pattern itself appears to encode the maintainer's/partner's personal names, i.e.
PII), and critically a SECOND subdomain explicitly documented as existing specifically to
**bypass Cloudflare** for large uploads (`subir-cogny.*`) — a real origin-server access path
that evades whatever WAF/DDoS protection Cloudflare provides for the main domain. Also leaks
exact systemd unit name and internal reverse-proxy port. Found via git-history archaeology
(same technique that paid off on CodeWeaver) — checked every commit's diff/message for
security-relevant keywords, this one wasn't caught by grep alone, found by reading full commit
stats/messages one by one. Deliberately did NOT attempt to resolve/reach the disclosed domains
(out of this program's declared scope — repo only, not live infra) — report is scoped strictly
to the disclosure itself. Flagged the PII angle to the user before drafting and got explicit
go-ahead ("si. si tiene impacto y es perjudicial si").

**Also confirmed via git history (folded into existing #3117 addendum, not a new report):**
commit `97b215e` shows the maintainer had ALREADY identified and attempted to fix the exact
PDF-export SSRF/LFI class reported in #3117 — commit message and code comment explicitly
describe blocking `file://` to prevent "leer notas de otro usuario o el .env (SECRET_KEY)",
but the fix (`_SAFE_URI_RE`) only blocked the `file:` scheme by name, never closed the
equivalent bare-absolute-path route that resolves identically once loaded in a `file://`
document — exactly what #3117's PoC demonstrates. Strong corroborating evidence this is a
real, previously-recognized-by-the-maintainer threat model, not a novel/theoretical one.

**Audited clean this session (2026-08-02), no findings:** core/context_processors.py,
core/templatetags/cogny_tags.py (avatar_url — safe), api/openapi.py + api/views.py's
docs()/openapi() (spec is JSON, docs.html has no injectable context, self-reflected Host
header in build_absolute_uri isn't attacker-exploitable), static/js/settings.js (all
`innerHTML` template-literal interpolations of note names/paths/API-key names go through
a real `esc()` HTML-escaper, checked both `shared-links` and `knowledge-links` panels —
no XSS), apps/notes/static/notes/md-ctxmenu.js (`menu.innerHTML` built only from
hardcoded static menu-option labels, never user data), scripts/docker-entrypoint.sh,
scripts/cogny.service (both boring, no injection, matches already-reported #3174 leak).

**Noted but NOT yet exploited (needs a concrete escalation before it's reportable):**
`vault.sanitize_name()` (strips `< > : " | ? * ` + control chars from filenames) is only
applied on the web `create()`/rename flow — ZIP import (`import_zip`/`safe_path`) does NOT
call it at all, only checks for `..`-traversal and path depth. So a ZIP entry can land a
note with a filename containing raw `<`, `>`, `"` etc. Confirmed this does NOT reach
settings.js's shared-links/API-keys panels (properly `esc()`-escaped). Have not yet found
a spot where a raw note NAME (as opposed to its content, already covered by #3150/#3294)
gets interpolated into HTML unescaped anywhere else (notes.js's file-tree rendering not yet
re-checked with this specific angle in mind — worth a dedicated pass).

**Remaining unaudited:** tests/*.py (haven't read actual assertions, only inferred coverage
from commit messages), static/js/notes.js's file-tree rendering (re-check specifically for
the raw-filename-from-ZIP-import angle above), static/js/knowledge*.js if present.

**Finding #10 SUBMITTED (report_id 3297): the ReDoS fix's own mitigation deadlocks
forever, restoring the original bug with a simpler payload.** Commit `f6e7d1c`
fixed #3133 by running `re.subn()` in a forked child process
(`_safe_regex_subn`/`_regex_subn_worker`) with a 2s `proc.join()` timeout, killing
the child if it overruns. Gap: `_regex_subn_worker` only catches `re.error`. A
repeat-count quantifier exceeding Python's internal 32-bit limit (`a{4294967296}`,
i.e. `2**32`) raises `OverflowError` — NOT a subclass of `re.error` — so the child
crashes immediately without ever calling `out.put()`. Since the child already
exited, `proc.is_alive()` is False (skips the TimeoutError branch entirely), and
the parent falls through to a bare `out.get()` with no timeout — blocking forever
on a queue that will never receive data. Live-verified against the actual current
code (worktree at 9573e03): called `_safe_regex_subn` directly, saw the real
multiprocessing traceback (child crash confirmed) printed to stderr, and the
parent Python process hung — had to be killed by an outer `timeout 15` shell
wrapper (exit 124), confirming it exceeds the promised 2s cap by 7.5x+ and would
hang indefinitely in production. Payload is simpler than the original catastrophic-
backtracking pattern — just a literal number in `{}`. This was found after the user
insisted (2026-08-01) there was "another fix" to check when git fetch showed
nothing new yet — redirected effort to re-attacking the two most recent commits
(ReDoS fix + is_active fix) more adversarially instead of accepting "looks solid"
at face value, which is exactly what surfaced this.

**Finding #9 SUBMITTED (report_id 3294): API v1's file_content() missed the
same-day 545b635 fix, full stored XSS with editor→owner escalation.** Commit
`545b635` ("Forzar descarga de adjuntos ejecutables") correctly patched
`apps/notes/views.py:asset()` (hardcoded Content-Type allowlist for images/PDF,
`application/octet-stream`+`as_attachment=True` for everything else) after the
maintainer found that unrestricted-extension uploads (sanitize_name never filters
extension) + guessed Content-Type let an uploaded `.html` execute same-origin via
`<script src>` (their own commit message names this exact mechanism: nonce-based CSP
blocks inline scripts but not same-origin external `<script src>`). But the fix only
touched the web view — `apps/api/views.py:file_content()` is the parallel API v1
endpoint serving the exact same attachment store, and it was never touched: still
bare `mimetypes.guess_type()`, no `as_attachment`. Live-verified end-to-end against
a `git worktree` checkout of the actual current origin/main (a98f8f7) with full
Django middleware (real CSP included): uploaded payload.js + evil.html via
`POST /api/v1/files` (API key, editor role), fetched evil.html via
`GET /api/v1/files/content` (Content-Type: text/html, Content-Disposition: inline —
unpatched), served the exact bytes+headers via local HTTP server, opened with real
Chromium — `<title>` became "API-STORED-XSS-EXECUTED", confirming the same-origin
`<script src>` executed under the genuine CSP. Same escalation chain as #3150
(fetch() to `/api/apikeys/create` mints an owner-privileged key) but via a
completely different surface (raw file upload/serve, no marked.js/DOMPurify
involved at all) that #3150's fix had no reason to cover. Root cause: the app's own
documented pattern is "one shared helper for web+API to avoid two security rules
diverging" (apps/api/views.py's own docstring) — this one specific piece of logic
broke that pattern and diverged.

**Parked, NOT submitted (2026-08-01): CSS `image-set()` bare-string bypass of the
same `_sanitize_css` (a98f8f7).** A third distinct bypass technique beyond #3292/
#3293: `-webkit-image-set("http://...")` needs no `url()` wrapper at all per the
CSS Images spec, so `_CSS_URL_RE`/`_CSS_IMPORT_STR_RE` (which only match literal
"url("/"@import" text) never even look at it — confirmed live (real Chromium fetch
captured, same SSRF/LFI class). User's explicit call: hold this one in reserve
rather than submit alongside #3293 (three bypass reports against the same 3-commit
fix chain in one day risks looking like spam) — re-verify against whatever the
maintainer's NEXT fix attempt on `_sanitize_css` looks like before reporting. Full
technical writeup saved at
findings/dia3/cogny-pdf-css-escape-sanitizer-bypass/parked_imageset_bypass.md.

**Finding #8 SUBMITTED (report_id 3293): CSS identifier-escape bypasses the
`<style>`-tag sanitizer entirely, restores full SSRF+LFI.** After #3292, a THIRD
fix landed same day: commit `a98f8f7` extended `_sanitize_css` (renamed from
`_sanitize_style`) to also scan `<style>` tag CDATA content for `url(...)`/
`@import "..."` (previously only the `style=` attribute was checked) — this was
apparently one of 3 findings the user said got accepted from other researchers
around the same time. Found and live-verified a much more direct bypass than
#3292's redirect trick: `_CSS_URL_RE`/`_CSS_IMPORT_STR_RE` match the LITERAL ASCII
text "url(" / "@import", but CSS spec allows escaping any identifier character via
`\XX` hex sequences — `\75rl(...)` decodes to `url(...)` in any spec-compliant
renderer (Chromium included), but the naive regex never recognizes it, so
`_is_safe_uri`/`_is_safe_http_host` NEVER EVEN RUN on this content — it passes
`sanitize_html()` byte-for-byte unmodified. Confirmed live against the actual
just-patched pdf.py (pulled from origin/main) + real Chromium: SSRF (real HTTP
request captured, genuine HeadlessChrome UA in the log) and LFI (local file outside
the vault embedded and visible in the resulting PDF, /Image+/FlateDecode markers).
Unlike #3292 (needs an attacker-hosted redirect server), this needs zero extra
infrastructure — a single string in the note body. Fully restores #3117's original
impact through the THIRD consecutive fix attempt on the same endpoint.

**#3117 maintainer fix (commits 60db353 SSRF-host-check + 1149291 LFI-scheme-lockdown)
BYPASSED, finding #7 SUBMITTED (report_id 3292): SSRF fix defeated by HTTP
redirect.** The fix adds `_is_safe_http_host()` (resolves hostname via
`socket.getaddrinfo`, rejects private/loopback/link-local/reserved/metadata IPs) —
solid logic, but it's a one-time check in the Python sanitizer BEFORE a completely
separate Chromium subprocess is spawned to actually fetch/render. Chromium does its
own independent DNS resolution and network fetch, so it transparently follows any
HTTP redirect the "safe" attacker-controlled origin issues toward an internal
target — the check never re-fires on the redirect's Location. Live-verified against
the actual patched pdf.py pulled from origin/main (not a hypothetical): local
"redirector" server (simulating attacker's public, check-passing host) returns 302
to a local "internal" server; real Chromium (via `render()`) followed it, and the
internal server's PNG got embedded in the resulting PDF (confirmed via /Image and
/FlateDecode markers, same verification method as the original report). DNS
rebinding would be an equally valid bypass of the same root cause (check-time vs.
fetch-time TOCTOU) but wasn't empirically demonstrated (no controllable DNS infra
in this sandbox) — the redirect variant was chosen because it's fully reproducible
without external infrastructure. This was found by fetching origin/main after the
user reported #3117 "Arreglado" (CVSS 6.9) on the dashboard and asking to check for
"rastros" (whether the same underlying issue survives via a different angle) — it
did. Also noted in passing: commit 545b635 ("Forzar descarga de adjuntos
ejecutables") independently fixed almost exactly the same upload-content-type XSS
gap this session's SVG-upload testing had been probing minutes earlier (same-origin
`<script src>` bypass of the nonce-based CSP, not the inline-script/onload vector
already tested and confirmed blocked) — already patched, not separately reported.

**Finding #6 SUBMITTED (report_id 3198): shared-note asset resolution leaks arbitrary
vault files to the public internet.** `_resolve_asset_ref` (apps/notes/views.py) falls
back to a vault-wide `root.rglob("*")` filename match when a note-embed reference
(`![[name]]`) doesn't resolve by exact path — correct for the internal attachments
flow (all attachments land in one shared `Adjuntos/` folder by design, confirmed via
`save_upload`'s own docstring), but this same fallback also runs for PUBLIC share
links, where authenticated-vs-public is the one privacy boundary this app actually
enforces. Live-verified end-to-end (fresh Django test-client instance, real pinned
deps, no live server): editor_t creates `Publico/nota.md` containing
`![[secreto-privado.jpg]]` referencing an unrelated file in `Documentos/` (never
attached to anything), shares it with no password, then a fully anonymous client
(never authenticated) fetches `/s/<token>/asset?p=...` and gets the real private
file bytes back (200, contents confirmed byte-for-byte). Escalation direction:
"editor" (GUEST_ROLES, explicitly lower-trust than owner) can unilaterally expose ANY
vault file to the public internet just by knowing its filename (which it already
has via normal vault-wide read access) — and the owner has zero visibility into this
via the Settings "Enlaces compartidos" panel, which only shows the shared note itself,
never the collateral files it drags in. This was the exact lead flagged in this same
memory file weeks earlier as "weak, not pursued" — revisited and live-tested per the
user's "revisa todo otra vez, prueba cosas que no se prueban realmente" directive,
and turned out to hold up as a real, novel, previously-unreported finding.

**Finding #11 SUBMITTED (report_id 3314, 2026-08-02): DNS-rebinding SSRF closes the exact
hypothesis #3292 left open.** #3292's own report text explicitly flagged "DNS rebinding would
be an equally valid bypass of the same root cause (check-time vs. fetch-time TOCTOU) but wasn't
empirically demonstrated (no controllable DNS infra in this sandbox)" — this session had the
same sandbox limitation (confirmed: `socket.getaddrinfo` itself fails locally, no outbound DNS
at all), so instead of live DNS infra, proved the mechanism by mocking `_resolve_host()` to
return a public IP (simulating what an attacker's rebinding-capable DNS server returns on the
FIRST/validation-time query) and confirming the real `sanitize_html()` leaves the attacker
hostname unpinned in the output — Chromium re-resolves independently at fetch time with no
proxy/host-resolver-rules pinning it to the validated IP. Same root cause family as #3292
(redirect bypass) and #3293 (CSS escape bypass) — a different *technique* against the same
"`_is_safe_uri()` validates once, hostname passes through unpinned" gap — but genuinely a
different fix (pin resolved IP / `--host-resolver-rules`, not "disable redirects" or "widen the
regex"), so kept as a separate report per [[feedback_report_merge_rule]]. CVSS Attack Complexity
scored High (not Low like the redirect variant) specifically because this one needs real
rebinding-capable DNS infrastructure to weaponize, not just a redirect from an attacker-owned
static server — noted this honestly in the report rather than inflating it to match #3292's
score.

**Disproven this session (2026-08-02): `shared_note_asset` "unauth stored XSS via
![[evil.html]]" hypothesis.** Looked real on a partial read (`_extract_asset_refs`
doesn't filter by extension), but the full read of `_resolve_asset_ref` shows it
DOES filter by `_SHARE_ASSET_EXTS` (images+PDF only) in both the direct-path and
`Adjuntos/`-fallback branches, and `_SHARE_ASSET_SALT` is only ever signed inside
that same gated function — no other path to a valid `p` token exists. Correctly
killed without building the PoC once the full function was read. Textbook
[[feedback_never_assume_confirm_always]] catch.

**Finding #12 SUBMITTED (report_id 3316, 2026-08-02): UnicodeDecodeError DoS on
note-content reads, same root cause as today's own read_order() fix, wider blast
radius.** Commit `0599829` (same day) fixed an uncaught `UnicodeDecodeError` in
`read_order()` (it's a `ValueError` subclass, not `OSError`, so existing
`except OSError` blocks miss it) and explicitly named 4 other already-protected
call sites — but never touched the note-CONTENT read sites, which share the exact
same gap: `apps/notes/views.py` `file_get()` (line 66) and `shared_note_view()`
(line 542, the fully public/unauthenticated `/s/<token>/` view) call
`.read_text(encoding="utf-8")` with zero try/except. Precondition (an editor
importing a ZIP with a `.md` containing invalid UTF-8 bytes) is enabled by
`vault._extract()` writing raw ZIP bytes with no encoding validation — same
mechanism the maintainer's own fix commit describes. Live-verified end-to-end
with Django `Client()` against real unmodified views: ZIP import succeeds (200,
no validation) -> editor's own `file_get` on that note 500s (can't even reopen it
to fix it via the UI) -> sharing it and hitting `/s/<token>/` with a fresh
never-authenticated client 500s too, permanently, for any anonymous visitor.
Also flagged (code-verified only, not independently live-tested) the same exact
pattern in `apps/api/views.py:271/299` (API v1 GET/PATCH) and
`apps/knowledge/views.py:87` (public knowledge API). CVSS
`AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L` — kept Low on VA since impact is scoped
to the one affected note/page, not the whole app, but flagged as aggravated by
having literally no in-app recovery path once a note is corrupted.

**Finding #13 SUBMITTED (report_id 3317, 2026-08-02): image decompression bomb in
the auto-WebP recode path, no timeout/pixel-limit of its own.** `vault.to_webp()`
(called from `save_upload()`, used by both `POST /api/notes/upload` and
`POST /api/v1/files`, and also from `optimize_images()` once per image) trusts
Pillow's own `MAX_IMAGE_PIXELS` guard entirely — but between 1x and 2x that
threshold (~89.5M-179M pixels) Pillow only issues a `DecompressionBombWarning`
(non-blocking), so a small solid-color PNG with huge declared dimensions still
gets fully decoded+re-encoded synchronously in the gunicorn thread, no app-level
timeout or memory cap at all (unlike #3133/#3297's regex path, which at least
tried a subprocess timeout). Live-verified against the real unmodified
`to_webp()`: a 12000x12000 solid-color PNG (449 KB on disk, Pillow-generated)
took 28.88s wall time and peaked at 1.94 GB RSS; pushed to 13377x13377 (549 KB,
just under Pillow's hard-block threshold) -> 20.09s / 2.39 GB RSS. Same
`PR:L`/editor-role precondition and same "low-trust role degrades service for
everyone on the single shared vault" escalation direction as #3133/#3297, but a
genuinely new surface (image upload, not find/replace) — found by creatively
asking "what other CPU/memory-unbounded operation touches attacker-controlled
input" after #3133/#3297/#3316 had already covered regex and encoding-error
DoS classes. CVSS `AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:H`. Title needed a retry
— the `~` character in "~2 GB" tripped the title `invalid_format` validator (not
just underscores, as previously known).

## 2026-08-07 continuation: 11 new upstream commits, "revisa funciones random"

Pulled origin/main (5 days stale) — 11 new commits, including a batch of `fix(security):`
commits closing several previously-unreported gaps + a brand-new "export PDF via API with
network+JS Chromium" feature (`apps/notes/pdf_headless.py`, `apps/notes/themes.py`). The
maintainer's own commit message for `e1064fa` (egress-proxy fix for the PRINT Chromium)
explicitly flags this new pipeline as unreviewed: "no se ha analizado si el mismo patrón de
evasión aplica ahí... queda pendiente de una revisión propia" — an open invitation to check it.

**Investigated but DISPROVEN empirically (do not re-report without new evidence):**
- Hypothesized SSRF via `prepareExportHtml()`'s `fetch(img.src)` call in `notes.js` (used by
  `pdf_headless.py`'s network+JS Chromium to convert `<img>` tags to data: URIs before PDF
  export) — since this Chromium instance has NO egress-proxy of its own (unlike the print
  Chromium after `e1064fa`). Built a full local end-to-end test: real Django dev server (own
  `.env`, isolated `DATA_ROOT`, real migrations), real Playwright + system Chromium
  (`playwright install chromium` + `pip install playwright` both work in this sandbox), a fake
  "internal victim" HTTP server on 127.0.0.1:9999. Result: **no SSRF** — the app's global CSP
  (`connect-src 'self'`, `img-src 'self' data:` — `apps/core/middleware.py`
  `ContentSecurityPolicyMiddleware`, applied to every response) blocks the cross-origin
  `fetch()` before it reaches the network. Confirmed via `pdf_headless.render_note_to_html()`
  called directly: the raw HTML output still contains the UNCONVERTED
  `http://127.0.0.1:9999/...` string (proving the fetch failed, image never became a data:
  URI), and the final PDF contains neither the URL nor any exfiltrated bytes. Two independent
  layers protect this in practice: CSP blocks the live fetch, and `pdf.sanitize_html()` (same
  Python sanitizer as the other pipeline) is STILL applied to `pdf_headless.py`'s output before
  printing, so even an unconverted unsafe src would get stripped there too.
- Hypothesized DOMPurify mXSS bypass (`notes.js`'s `renderMarkdown()` now uses
  `DOMPurify.sanitize(html, {USE_PROFILES:{html:true,mathMl:true,svg:true}})` — MathML/SVG
  profiles are historically where DOMPurify bypasses have been found, and the maintainer's own
  most recent commit `17a9719` was about an analogous MathML mXSS bug in their OWN Python
  sanitizer). Checked bundled version: `static/vendor/dompurify/purify.min.js` is DOMPurify
  **3.4.12** — WebSearch found real 2026 CVEs (CVE-2026-47423 `selectedcontent` re-clone bypass,
  CVE-2026-41238/41239/41240 prototype-pollution bypass, CVE-2026-0540 MathML/SVG mXSS) but all
  affect versions below what's bundled here. Verified directly against the actual shipped file
  (not just trusting the version string): `selectedcontent` appears in DOMPurify's internal
  "special CDATA-like handling" tag set (`Dt` array alongside `script`/`style`/`template`), not
  the naively-allowed set — confirms the CVE-2026-47423 fix IS present in the bundled copy.
- Hypothesized SVG-XSS via malicious theme images (`apps/notes/themes.py`'s `add_image` accepts
  SVG uploads via `theme_image_upload`, gated only by `@require_write` — i.e. an EDITOR, not
  just owner, can plant a malicious SVG in a THEME that's global/shared across the instance,
  matching the established editor→owner escalation pattern). Disproven: `pdf.py`'s
  `_UNSAFE_TAGS = {"script","iframe","object","embed","link","meta","base","applet","form"}`
  already strips `<object>`/`<embed>`/`<iframe>` — the only tags that would let an
  SVG-as-data-URI execute embedded `<script>`. `<img src="data:image/svg+xml...">` and CSS
  `background-image: url(data:...)` (the only surviving ways to reference the image) don't
  execute SVG scripts per browser spec (image context, not document context). Confirmed
  `themes.fill()` runs BEFORE `sanitize_html()` (`pdf.py:582`,
  `sanitize_html(themes.fill(...))`), so the substituted data: URI genuinely does pass through
  the sanitizer — but the sanitizer's tag-stripping is what closes the gap, not URI-scheme
  filtering.

**Finding #14 SUBMITTED (report_id 3873, 2026-08-07): share_status bypasses the same-day
share_list fix.** Commit `042756e` (same session, hours earlier) added `@require_write` to
`share_list` after recognizing a viewer/read-only-API-key could bulk-list every shared note's
unauthenticated token+URL — but left its sibling `share_status` (returns the IDENTICAL
`token`/`url` fields, just for one note at a time via `?path=`) at `@login_required` only.
Since every authenticated role has full read access to the shared vault's note-path tree
(`GET /api/notes/tree`, never role-restricted), a viewer trivially reconstructs the exact same
bulk result `share_list`'s fix was built to prevent: enumerate all paths, call
`share_status?path=<each>` for each one. Live-verified end-to-end against a real local Django
instance running the actual current code: created a `viewer` user, real login session (cookies,
CSRF), a `SharedNote` with a known token — `GET /api/notes/share/list` correctly 403'd
("Tu acceso es de sólo lectura"), but `GET /api/notes/share/status?path=malicious.md` returned
200 with the full token, and `GET /api/notes/tree` (unrestricted for any role) supplied the
path to query. Found by reading the fix's own commit message closely enough to notice it
explicitly changes `notes.js` to call `share/status` INSTEAD of `share/create` for the
"just checking" UI flow — meaning the author already knew `share_status` stays reachable by
everyone, and didn't extend the permission check to it too.

**Finding #15 SUBMITTED (report_id 3879, 2026-08-07): attachment-owner path-reuse bypasses
the same-day e4320bc fix.** `e4320bc` (hours earlier, same day) registers `Adjuntos/.owners.json`
keyed by `note_path` (a plain string) to fix editors sharing arbitrary attachments — but
`rename`/`move`/`create`/`delete` are ALL `@require_write` (editor-level), and `rename()`'s own
fix updates `SharedNote` records via `vault.move_shares()` but never touches
`Adjuntos/.owners.json`. An editor can: rename the victim's note away (freeing its path) →
create a brand-new note of their own at that exact freed path → reference the victim's
attachment by name in the new note → share it. `attachment_owner(root, candidate) != note_path`
now compares against the ATTACKER's note (same path), passes incorrectly. Live-verified fully
end-to-end against a real Django instance running the actual `e4320bc` commit: owner uploads
`secret.png` tied to `Documentos/privado.md` (confirmed real `.owners.json` entry) → sanity-check
the legit share resolves it correctly, then revoke → editor session renames the note away,
creates a new note at the freed path, embeds `![[secret.png]]`, shares it → fully anonymous curl
request to the resulting public link downloads bytes `diff`-identical to the owner's original
upload. Fully deterministic, four sequential POSTs, no race window needed. Third fix attempt on
this exact mechanism in one day (`5f925a2` → prior researcher/#3198-era finding → `e4320bc` →
this). Found by applying the "verify same-day fix is complete" lens to `e4320bc`'s own commit
message, specifically noticing it names `vault.move_shares()` as the thing rename() keeps in
sync but never mentions the brand-new owners.json mechanism at all.

**Disproven this session (2026-08-07): ZIP-import raw-filename XSS hypothesis.** An old memory
note flagged that `import_zip`'s `safe_path()` doesn't call `sanitize_name()` (only blocks `..`
traversal + depth), so a ZIP entry can land a note/folder with a raw `<img src=x onerror=...>`-
shaped filename — confirmed true at the filesystem level. But the CLIENT-side rendering
(`notes.js`'s tree, tabs, note-open flow) uses `esc()`/`textContent` consistently everywhere a
filename reaches the DOM. Verified with the most rigorous method available: real Chromium via
Playwright, real Django server, real ZIP import as an `editor` session, both a malicious FILE
name and a malicious FOLDER name, checked the tree HTML directly (`&lt;img src=x
onerror=alert(1)&gt;` — properly escaped) AND opened the malicious note directly via `?open=`.
Zero dialogs fired, zero raw markup. User independently opened/checked and also saw nothing.
Fully dead — do not re-investigate without a genuinely new angle.

**New session-setup capability learned:** this sandbox can run a full local Django dev instance
+ real Playwright + system Chromium end-to-end (no bundled browser download needed if
`playwright install chromium` is run once — ~300MB download, worked fine). Useful default
pattern for any future cogny (or similar Django+Chromium) live verification: isolated `.env` in
scratch dir pointing `DATA_ROOT`/`VAULT_ROOT`/`DB_PATH` outside the repo checkout,
`manage.py migrate`, create test users directly via `manage.py shell -c`, real HTTP requests via
curl with cookie jars for session-based auth or `Authorization: Bearer <key>` for API-key auth.

**Weak lead explicitly set aside, not pursued:** shared-note password has no minimum
length/complexity requirement, and `shared_note_view`'s password POST has no rate limiting —
but cogny's own VDP policy explicitly lists "la mayoría de los problemas relacionados con
*rate limiting*" as out of scope, so this wasn't drafted (would likely bounce on their own
stated policy without a much stronger, separately-demonstrated impact).
