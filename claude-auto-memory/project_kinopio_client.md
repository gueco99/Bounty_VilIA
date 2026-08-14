---
name: project-kinopio-client
description: "kinopio-client (github.com/kinopio-club/kinopio-client) hunt state — fresh CVE-eligible VDP (0 reports), Vue3 SPA canvas/notes app, 1 finding SUBMITTED (javascript: URI stored XSS via case-sensitive filter bypass)"
metadata:
  node_type: memory
  type: project
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

**Finding #9 SUBMITTED (report_id 3403, Medium, new vuln class — info disclosure via
console): live apiKey + arenaAccessToken printed to browser console on every app load.**
`userStore.getUserAllState` returns `{...this.$state}` (the ENTIRE store, including the
declared `apiKey: ''`/`arenaAccessToken: ''` fields — apiKey confirmed elsewhere as the
literal `Authorization` header value for every API request). `initializeUser()` does
`console.log('🍍 initializeUser', this.getUserAllState)` unconditionally — and
`initializeUser()` is called from `main.js` (app entry) and `router.js` (route nav),
i.e. every single load/navigation for any signed-in user, not a rare debug path. Also
flagged a likely second instance (`restoreRemoteUser()`'s
`console.info('🌸 Initialize user from remote', user)` — logs the raw server /user
response, probably same fields, couldn't fully confirm without kinopio-server). Checked
for a session-replay/log-aggregation vendor (FullStory/LogRocket/Sentry-style) that would
auto-capture console output and elevate this to instant third-party leak — found none
currently integrated (own analytics implementation only), but noted this logging
statement would become one immediately if such a tool were ever added. Real-world
exposure vectors: screen-share/recording while devtools open (most likely exactly when
debugging this same app), browser extensions with console access, shared/managed
computers. Found by pivoting to "otro tipo de vulnerabilidad" per user's explicit request
after business-logic angle also ran dry — first genuinely new vuln CLASS (not a variant
of prior findings) found this late in the session.

**Finding #8 SUBMITTED (report_id 3396, Low, genuinely different root cause): email
invite anti-spam limit is silently non-functional.** `EmailInvites.vue`'s `sendInvites()`
checks `state.emailsList.length > maxEmailsAllowed.value.length` — but
`maxEmailsAllowed.value` is `consts.maxInviteEmailsAllowedToSend`, a plain NUMBER (15),
not an array/string. `(15).length` is `undefined`, and any `> undefined` comparison is
always `false` — so the "max 15 invites at once" check (explicitly advertised in the
dialog's own UI copy) NEVER triggers regardless of list size. Confirmed with a plain
Node one-liner reproducing the exact expression. Unlike #3356/#3388/#3389/#3393 (all
rooted in the same userStore.id/isUpgraded mutable-state pattern, requiring devtools),
this is reachable via the completely ordinary UI — just paste >15 emails and click
Send, no console needed. Noticed I was about to report a 4th variation of the same
id-spoofing root cause (group admin role, via `getGroupUserIsAdmin`) and deliberately
pivoted away from it as repetitive/diminishing-value, searching instead for a distinct
bug class — this is what that pivot found.

**Considered but not submitted (repetitive, same root cause as #3389/#3393):**
`getGroupUserIsAdmin({userId, ...})` looks up `group.users.find(u => u.id === userId)`
and checks `role === 'admin'` — if called with `userStore.id` as the userId param
(typical usage), this is a 4th instance of the exact same id-spoofing pattern already
reported twice. Did not draft a separate report for this; the fix and root cause are
identical to #3389/#3393's recommendation.

**Finding #7 SUBMITTED (report_id 3393, High, broader sibling of #3389): any signed-in
user can self-grant FULL space membership (not just one card's ownership) via the same
userStore.id spoofing.** `getUserIsSpaceUser`/`getUserIsSpaceCollaborator` compare
`this.id` against `space.users`/`spaceStore.collaborators` id lists (ordinary, visible
data); `getUserIsSpaceMember` ORs them together; `getUserCanEditCard`/`getUserCanEditBox`/
`getUserCanEditSpace` all short-circuit `if (isSpaceMember) return true` UNCONDITIONALLY
— no per-item ownership check once "member". Any signed-in visitor to an open space
(no prior invite needed at all, unlike #3389 which at least required already being a
restricted collaborator) can set `userStore.id` to the space owner's or any
collaborator's id and become a full member, unlocking edit/delete on every card/box in
the space, not just one. Verified with a real vitest test: baseline blocked, then after
the id-spoof, `getUserIsSpaceMember`/`getUserCanEditCard`(arbitrary card)/
`getUserCanEditSpace` all flip to true. Same honest server-side-enforcement caveat as
#3356/#3388/#3389. Continues the "business logic" pivot: this and #3389 form a pair
(per-item ownership spoof vs. full-membership spoof), both rooted in the same
"client trusts its own mutable id field" anti-pattern discovered via #3356.

**Finding #6 SUBMITTED (report_id 3389, Medium-High, business-logic angle continued):
restricted "open space" collaborators can self-grant edit rights on ANY card/box via
userStore.id spoofing.** `getUserCanEditCard`/`getUserIsCardCreator` (and the box
equivalents `getUserCanEditBox`/`getUserIsBoxCreator`) gate the app's own documented
"can only edit cards they created" restriction (README's own "User States to Design For"
table) purely via `this.id === card.userId` — `userStore.id` being the exact same
freely-mutable Pinia field already flagged in #3356/#3388. A non-member, signed-in
participant in an "open" space (explicitly the lower-trust role this check targets) can
set `userStore.id = <any card's userId, already visible ordinary data>` from their own
console — no exploit needed, no websocket dispatch required — and the client considers
them the creator of that card, bypassing the restriction entirely. Verified with a real
vitest test against the actual store code: baseline confirmed blocked (false), then after
the id-spoof mutation, `getUserIsCardCreator`/`getUserCanEditCard` both flip to true for a
card the "attacker" never created. Same honest server-side-enforcement caveat applied as
#3356/#3388. This was found by continuing the "business logic" pivot the user requested —
checking whether edit-permission gates (not just paywall gates) followed the same
"client trusts client's own mutable id field" anti-pattern; they did.

**Finding #5 SUBMITTED (report_id 3388, Low-Medium, "business logic" angle explicitly
requested by user): free-tier paywall gated entirely by mutable client-side state.**
`userStore.isUpgraded` (plain Pinia field) solely controls both
`getUserCardsCreatedIsOverLimit()` (100-card free limit) and `utils.isFileTooBig()`
(5MB vs 256MB upload size) — `if (this.isUpgraded) return` / `if (userIsUpgraded)
sizeLimit=256mb`, no server round-trip or signature check anywhere in this codebase.
Any user can set `userStore.isUpgraded = true` via browser devtools/console on their
own account, no exploit needed. Verified with a real vitest test against the actual
`useUserStore`/`utils.isFileTooBig` code: both checks flip from blocked to bypassed
purely by toggling the one boolean. Same honest hedge applied as #3356/#3363: cannot
verify from this client-only repo whether kinopio-server independently re-validates
subscription status when persisting (createCard sync, S3 presigned-post policy) — framed
as "this is what the client does" rather than claiming confirmed free premium access.
User explicitly asked to pivot to "business logic?" as a category after ~6 rounds of
"sigue revisando" on technical vuln classes (XSS/injection/CSRF-adjacent) all came up
empty — this was the fruitful reframing that found something new.

**Areas re-confirmed safe this session (dead ends, listed so a future session doesn't
re-tread): OtherCardPreview.vue's `:href="props.url"` (URL always server/ID-constructed
via `utils.urlFromSpaceAndItem`, hardcoded domain prefix, can't inject a scheme) and
`spaceInviteUrl`; `@aguezz/qs-parse`'s `decode()` (only ever assigns string values,
`__proto__` setter silently no-ops on non-object values, no prototype pollution possible,
unlike the notorious `qs` package); `getAtUserMentionById` (reads only already-cached
local collaborator data, no arbitrary-ID server lookup, no IDOR); `useHistoryStore.js`
(undo/redo, purely local state, no network); VitePWA service worker (standard
Workbox `generateSW`, not hand-written, low bespoke-bug risk); markdown regex patterns
in `utils.js` (`linkPattern`/`boldPattern`/etc. — all non-greedy with fixed terminators
or negated character classes, no nested-quantifier ReDoS shape); nanoid-based
`collaboratorKey`/`readOnlyKey` generation (strong entropy, not predictable);
`Math.random()` usage (only decorative background colors, not security-relevant);
file-upload extension blocklist in `useUploadStore.js` (misses .html/.svg — real
denylist-vs-allowlist anti-pattern, but user chose to discard rather than report given
inability to confirm S3-policy-level server enforcement); group role management
(`useGroupStore.js` — real authorization would need to live server-side, nothing
client-exploitable found).

**Finding #4 SUBMITTED (report_id 3374, High): clickjacking chain escalates #3363+#3346
to zero-awareness silent card injection.** No clickjacking protection anywhere in the
app (no X-Frame-Options, no frame-ancestors CSP, no JS frame-busting — confirmed via
grep, nothing exists). Combined with #3363 (Add.vue postMessage no origin check) and
#3346 (javascript: URI XSS), built a real end-to-end PoC: attacker page has a visible
decoy button ("Claim Prize") positioned exactly over an invisible (`opacity:0`,
NOT `pointer-events:none`) iframe loading kinopio.club/add, which was pre-filled via
postMessage with a `[text](JavaScript:...)` payload before the victim ever looks.
Verified with `puppeteer-core` driving real Chromium via actual CDP
`Input.dispatchMouseEvent` (a genuine synthetic OS-level click, not a JS `.click()` which
would bypass real hit-testing) — measured the real "Add to Inbox" button's bounding box
first, aligned the decoy exactly, then confirmed the click landed on and activated the
real hidden button (iframe's own document title changed as its real handler would do).
Escalates #3363 from Low (needed victim to notice+submit prefilled form) and #3346 (needed
a malicious card to already exist) into one chain: one click on an unrelated page with
zero Kinopio branding visible, silently plants the payload; one more click on the
resulting card later triggers the XSS. This was a deliberate "chain new PoC, don't just
resubmit" call — user explicitly chose to build the full demonstrated chain over
continuing to look for something unrelated, via [[feedback_reproducibility_not_severity]]-
adjacent reasoning about what makes a chain a genuinely new finding vs. reinforcing an old
one.

**Finding #3 SUBMITTED (report_id 3363, Low severity): Add.vue's postMessage listener
has no origin check.** `src/views/Add.vue`'s `window.addEventListener('message', ...)`
calls `restoreValue(event.data)` unconditionally — no `event.origin` validation at all.
Two sibling listeners in the same codebase (`Space.vue`'s `addCardFromOutsideAppContext`,
`UpgradeUserApple.vue`'s `handleSubscriptionSuccess`) both correctly gate on
`consts.isSecureAppContext` (true only inside the iOS native app's WKWebView, never in a
normal browser) before trusting the message — proving the gate is a known, intentional
pattern elsewhere that was simply never applied to Add.vue. Impact is modest and I said
so honestly: this only pre-fills the "add card" textarea with attacker-chosen text (via
`window.open()` + postMessage, or iframe embedding — no X-Frame-Options/frame-ancestors
CSP configured anywhere in netlify.toml), the victim still has to notice and submit the
form themselves for a card to actually get created. Asked the user directly whether to
report at this modest severity vs. hold out for something bigger first — they said report
it anyway. Important correction made mid-session: initially thought `Space.vue`'s
postMessage handler (which directly calls `cardStore.createCard()`, no submit needed) was
the bigger, web-reachable finding, but caught my own error by actually tracing
`isSecureAppContext` — that one is iOS-app-gated and NOT reachable from a normal browser,
so did not report it separately.

**Finding #2 SUBMITTED (report_id 3356, likely the more severe of the two): websocket
messages dispatch arbitrary Pinia store actions with zero allowlist, incl. real
persisted deleteSpace.** `src/stores/plugins/webSocketPlugin.js`'s `receiveMessage()`/
`handleAction()` take `store`/`action`/`updates` directly from an incoming, attacker-
influenced websocket message and dispatch via `piniaStore[action](updates)` — no
allowlist of which action names are legitimate targets for a remote-triggered
broadcast. Confirmed via exhaustive grep of every real `broadcastStore.update(...)`
call site across the whole codebase that destructive actions like
`spaceStore.deleteSpace`/`removeSpace`, `cardStore.deleteCard(s)`/`removeCard(s)`, and
`userStore.updateUserState` are NEVER used as a legitimate broadcast action anywhere —
they're local-only, yet fully reachable via this dispatcher. Verified live with a real
vitest test (not a reimplementation) importing the actual `useSpaceStore`/`useApiStore`
and replicating the exact bracket-notation dispatch: calling `deleteSpace` this way
triggers a real `apiStore.addToQueue({name:'deleteSpace',...})` — i.e. a genuinely
persisted delete request using the RECEIVING (victim) client's own authenticated
session. Zero user interaction needed (fires automatically in `onmessage`), any
connected space participant (not necessarily the owner) can trigger it against every
OTHER connected client. `userStore.updateUserState(update)` is an equally unguarded
second primitive: blind `this[key]=update[key]` for every key of an attacker object,
letting a peer overwrite the victim's own `id`/`apiKey`/`arenaAccessToken`/
`isModerator`/`isUpgraded` fields client-side. Explicitly did NOT claim anything about
kinopio-server's own authorization (separate, out-of-scope repo, source unavailable) —
framed the finding around what's demonstrable purely from this client's own code.

Target: `github.com/kinopio-club/kinopio-client` — Vue 3 + Pinia SPA client for Kinopio,
a "spatial thinking canvas" app (cards/boxes/connections on an infinite canvas). Talks to
a separate `kinopio-server` (NOT in scope, different repo) via API + websockets, and uses
localStorage/IndexedDB for offline-first data. Fresh VDP, CVE-eligible, Safe Harbor, 0
reports at session start (2026-08-03). Includes Netlify Edge Functions (Deno, real
server-side code, in-repo and in-scope) for social-preview meta-tag rewriting.

**Finding #1 SUBMITTED (report_id 3346): stored XSS via `javascript:` URI in card
markdown links, case-sensitive filter bypass.** `src/utils.js`'s `linkPattern` regex
(`/\[([^[]+)\]\(([^\n ]+)\)/gmi`) parses `[text](url)` card-name markdown with NO scheme
restriction at all. The only defense is `NameSegment.vue`'s `escapedUrl()`:
`if (url.includes('javascript:')) return null` — case-SENSITIVE, so `JavaScript:`/
`JAVASCRIPT:`/any mixed case sails through unmodified, gets rendered as a real `<a href>`
AND passed to `window.open()` on click. Verified live: reproduced the exact filter+handler
logic standalone, confirmed the string survives the filter unchanged, then confirmed with
real headless Chromium that clicking the resulting `<a href="JavaScript:...">` genuinely
executes (page replaced with the JS expression's return value — the standard, unambiguous
signal of real javascript: URI execution, not just unescaped-string presence).
`NameSegment.vue` is the SINGLE shared renderer for card/box/list names used by `Card.vue`
(main view), `OtherCardPreview.vue` (link previews), and `CardCommentPreview.vue`
(comments) — so the payload propagates everywhere a card name is shown. Any collaborator
on an open/editable space (not just the owner) can plant it; requires one victim click on
attacker-controlled link text, no other precondition.

**Investigated and ruled out (verified before drafting, no false positives this round):**
- Netlify edge function `page-meta.js`'s `pageJsonLD()` builds unescaped JSON-LD
  (`item.name`/`space.description` not passed through the file's own `escapeHtml()`,
  unlike `pageBodyContent()` which does) and injects it via
  `element.setInnerContent(jsonLD)` into a `<script type="application/ld+json">` — LOOKED
  like a `</script>` breakout XSS, but empirically confirmed (via a real Deno + the actual
  `html-rewriter` WASM library, not just docs/assumption) that `setInnerContent()` without
  `{html:true}` DOES HTML-entity-escape `<`/`>` even inside a `<script>` tag context (output
  was literally `&lt;/script&gt;`, not `</script>`) — so this specific vector is closed,
  though it may still be a functional/SEO bug (legit `<`/`>` in card names would corrupt the
  JSON-LD's validity, not a security issue).
- `CodeBlock.vue`'s `v-html="syntaxHighlightHTML"` (from the `macrolight` npm package)
  looked promising (raw card code-block content → v-html) but `macrolight`'s `highlight()`
  DOES escape `&`/`<`/`>`/`"`/`'` by default (only skips escaping if the caller passes
  `dontEscape: true`, which `CodeBlock.vue` never does) — confirmed empirically with node
  directly against the installed package, payload came out safely escaped.
- `Textarea.vue`'s `v-html="safeHtmlStringWithMatches"` has an equally naive "sanitizer"
  (`string.replaceAll('script', '')` — same case-sensitivity flaw as escapedUrl, plus does
  nothing against event-handler-attribute XSS at all) but its ONLY call site
  (`EmailInvites.vue`) feeds it the CURRENT user's own textarea input reflected back to
  themselves — self-XSS only, no cross-user path found, so not reported per
  [[feedback_reproducibility_not_severity]]-style reasoning (real bug, no real trust
  boundary crossed as currently wired). Worth revisiting if `Textarea` with
  `htmlStringWithMatches` is ever reused elsewhere with cross-user content.
- GitHub Actions-style untrusted-context-injection pattern doesn't apply here (this repo's
  CI, if any, wasn't the focus — this session's recon centered on the client + edge
  functions).

**Not yet audited:** `src/stores/*` (Pinia state management, especially how server API
responses get merged into local state — potential prototype-pollution-adjacent surface if
any deep-merge is used on untrusted API/websocket payloads), websocket message handling,
`Add.vue` (browser-extension/iOS-share-sheet entry point, takes external input by design),
`CardTips.vue`/`FontPicker.vue` and other markdown-consuming dialogs listed by the earlier
`grep -l markdown` sweep, IndexedDB/localStorage data handling for injection into later
renders, image/file upload handling if any exists client-side.

## Program scope confirmed: repo-only, no live server — closes the "defend via live test" door

2026-08-06: #3389 (userStore.id card-ownership spoof) got closed as **Informativo** by
triage. User asked whether to defend it. Correct call to accept, not appeal: the
report's own honest hedge ("cannot verify from this client-only repo whether
kinopio-server independently re-validates...") is exactly the gap the triager cited, and
**the user confirmed the program's scope is the GitHub repo only — kinopio.club (the live
app/server) is explicitly NOT in scope.** This means there is no legitimate way to
produce the server-side evidence that would flip this back to a real finding — testing
the live server would itself be out-of-scope action.

**Applies to the whole userStore.id/isUpgraded family, not just #3389**: #3356 (id spoof
base), #3388 (isUpgraded paywall bypass), #3393 (full space-membership spoof), and the
considered-but-not-submitted `getGroupUserIsAdmin` variant all share the identical
"client-only, can't verify server-side" hedge. **If any of these get closed as
Informativo too, don't propose a live-server test again — the scope constraint already
rules it out permanently for this program.** Accept the informational outcome; it's the
correct, expected result of auditing a client-only repo whose entire security model for
these checks depends on a backend this engagement was never authorized to touch.

**Confirmed the rule generalizes beyond that family: #3396 (email invite anti-spam limit,
a genuinely different root cause) closed Informativo 2026-08-07 for the identical
"can't verify kinopio-server independently enforces this" hedge.** Any future finding in
this program that carries this same client-only caveat should be expected to close the
same way — it's not specific to the id-spoofing bugs, it's structural to auditing a
repo-only-scope client whose real security boundary lives in an out-of-scope server.
Don't propose live-server verification as a rescue for ANY finding in this program.

**Working strategy for this program going forward (validated 2026-08-07): only hunt bug
classes whose impact is provable entirely within the client, without any assumption about
what kinopio-server does.** That rules out anything shaped like "the client trusts its own
mutable local state to decide who's authorized" (the whole id-spoofing family). It does NOT
rule out: XSS (#3346), clickjacking (#3374), secret-in-console leaks (#3403), real-session
hijack via the websocket dispatcher using the VICTIM's own already-authenticated session
rather than impersonating anyone (#3356 — this one is a genuinely different shape from the
id-spoof family even though it lives in the same dispatcher, because it doesn't need the
server to trust a fake identity), or third-party integration bugs entirely within Kinopio's
own code (see #3796 below). When searching for new bugs here, actively filter OUT anything
that would need a "can't verify server-side" hedge before spending time drafting it.

**Finding #10 SUBMITTED (report_id 3796, Low, new vuln class — insecure OAuth transport):
Are.na "Authorize Kinopio" link uses http:// instead of https://, unconditionally,
including production.** `ImportArenaChannel.vue`'s `authorizeUrl` computed property
hardcodes `http://dev.are.na/oauth/authorize?...` — the only Are.na URL in the whole file
that isn't https://; the other three (api.are.na fetch, are.na channel link, placeholder
text) are all correct. Confirmed via `git log --follow -p` this has never been https:// in
the file's history. Confirmed live against the real dev.are.na (single passive anonymous
GET, no account touched): the http:// request gets a 301 to https, but that 301 response
carries no HSTS header (HSTS only arrives on the https response, and without `preload`) —
so any user connecting Are.na for the first time has their initial request go out in
cleartext, the textbook SSL-stripping precondition. Found by systematically grepping for
`v-html`/`innerHTML`/blind-key-assignment/ReDoS/JSON-import patterns across previously
"not yet audited" areas after #3396 closed — most leads were dead ends or corroborated
already-reported root causes (e.g. `useSpaceStore.updateSpace` has the exact same
blind-`this[key]=update[key]` pattern as #3356's websocket dispatcher — not a new report,
just confirms that bug is systemic across stores, not a one-off). This OAuth-transport bug
was the one genuinely new, self-contained finding from that pass — exactly the kind the
new working strategy above was aimed at surfacing.

**Finding #11 SUBMITTED (report_id 3797, Low-Medium, new vuln class — reverse
tabnabbing): `window.open(url)` with no `noopener` on attacker-controlled card link URLs
in NameSegment.vue/Card.vue/UrlPreviewCard.vue's `openUrl()`.** Any collaborator (or any
visitor to an open space — no invite needed) can set a card's markdown link or
`urlPreviewUrl` to an arbitrary external site; clicking it opens that site via
`window.open(url)` with no second argument, so the destination page gets a live
`window.opener` reference back to the original, still-authenticated Kinopio tab and can
navigate it to a phishing page (classic CWE-1022). Found by grepping all `window.open(`
call sites after the Are.na finding — most (OtherSpacePreviewCard/GroupInvitePreview/
Header) only ever open same-origin kinopio.club URLs the app itself builds, not
attacker data, so those are NOT vulnerable and weren't included. Verified end-to-end with
a REAL headless Chromium run (puppeteer-core + CDP, not a claim) reproducing the exact
vulnerable call: a genuine click opened a second real window that successfully navigated
the first tab to an attacker URL (`victimUrlAfter`/`victimTitleAfter` both confirmed the
redirect happened). Continues the working strategy: entirely self-contained in the
client, no "can't verify server" hedge needed.

**Hit the known long-title HTTP 500 again with #3797** (133-char title, same failure mode
already documented in [[reference_secur0_api_pipeline]] from the 2026-08-06 chezmoi
incident) — should have checked title length against that memory BEFORE the first submit
attempt instead of rediscovering it live. Fixed the same way: shortened to <100 chars,
resubmitted successfully. Reminder for next time: check known pipeline gotchas in
[[reference_secur0_api_pipeline]] before calling `secur0_api.py submit`, not after a 500.
