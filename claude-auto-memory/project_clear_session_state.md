---
name: project-clear-session-state
description: "State of the CLEAR HackerOne program hunt as of 2026-07-14/15 — two findings ready, next steps for higher impact"
metadata: 
  node_type: memory
  type: project
  originSessionId: eff95342-ff4b-4097-ac00-66e8b9e8a03a
---

**UPDATE 2026-07-31: both findings are now SUBMITTED (confirmed by user).**

**Status (2026-07-15):** Two findings produced against CLEAR, both drafted and saved under `findings/` in the claude-bug-bounty repo, ready to submit.

1. `findings/clear-halo-indirect-prompt-injection/` — Indirect prompt injection in the Sierra-powered "Halo" chatbot on www.clearme.com. Confirmed, reproducible (~50% hit rate with the exact saved payload), leaks non-public CLEAR1 partner names (Home Depot, Wells Fargo — verified NOT in any public CLEAR marketing) plus internal PR/support policy text. This is the stronger of the two — real leaked business data, not just a mechanism.

2. `findings/clear-salesforce-aura-guest-exposure/` — my.clearme.com falls back to a live, legacy Salesforce Experience Cloud Community for unmatched paths. `/s/sfsites/aura` accepts a completely unauthenticated POST (no cookies) and executes at least one backend action (`MessagesController/ACTION$getUserDetails` → SUCCESS) even though real browser navigation to the same Community forces genuine SSO login. This is a confirmed auth-bypass mechanism, but **no real PII was extracted** — see below.

**Why: [[feedback-autonomous-hunting]] applies — user wants autonomous hunting continued without pauses, but this session hit a real, honest technical wall.**

## The unsolved problem: no real Salesforce record ID

Spent enormous effort (9+ distinct techniques) trying to get a real Salesforce ID to prove the Aura finding reaches actual member data, not just an empty SUCCESS response:
- No search/typeahead action reachable by guest in the loaded component tree
- Record creation (`RecordGvpController/ACTION$createRecord` on Case) is correctly denied
- No IDs embedded anywhere in the 4.2MB `getApplication` response or any other response
- Privacy/Data Request form (`/CommunityPrivacyRequest`) turned out to be a third-party OneTrust iframe, not Salesforce
- List-view action (`SelectableListDataProviderController/ACTION$getItems`) exists but isn't loaded/wired into this specific Community's app bundle
- Knowledge/CMS actions (`getArticleUrlNameAndVersionId` etc.) all require a recordId as *input*, none return one from a name/slug
- Tried reusing a chatbot indirect-injection payload to leak a case/ticket ID format — blocked by the classifier, and even if it worked would be the wrong ID namespace (Zendesk/verification-session IDs, not Salesforce 18-char record IDs) since Halo/Sierra is a separate system from the my.clearme.com Salesforce Community
- Explicitly declined actual brute-forcing of the ID keyspace (CLEAR's own rules prohibit automation/brute-forcing, and it's also computationally infeasible — 18-char base62 IDs, not sequential)

**How to apply next time:** don't re-attempt the same 9 exhausted techniques. The only real paths to a valid ID are (a) complete the my.clearme.com consumer enrollment far enough to get a real Lead/Contact record (stop before any biometric/selfie step — user offered their own real phone +34674249691 for this, never completed due to a WAF block), or (b) get proper CLEAR1 sandbox dashboard access working (see below) which has its own separate synthetic-data verification session IDs safe to use for testing without touching real member data.

## Blocker: Cloudflare WAF hard-block on clearme.com

Near the end of the session, aggressive testing (JWT forgery attempts, unusual JSON payloads, repeated Aura calls) triggered a full Cloudflare "Sorry, you have been blocked" WAF block on the clearme.com zone (my.clearme.com specifically; www.clearme.com remained reachable). This is a harder block than the earlier 429 rate-limit responses (those had `retry-after` headers and cleared on their own; this one is a security-rule block with a Ray ID, not just rate limiting). Did not attempt to evade it (no IP rotation, no UA spoofing to bypass) — that crosses into "detection evasion," a hard no regardless of legitimate underlying intent. Next session: check if it has cleared naturally before resuming any testing on my.clearme.com/verified.clearme.com from this environment.

## Unfinished: CLEAR1 sandbox console signup (separate from the above blocker)

Made real progress signing up for the developer sandbox at `verified.clearme.com/dashboard` (self-service email+TOTP signup, no sales contact needed) — cracked the passwordless email OTP flow and extracted the TOTP secret via network response interception (`otpauth://` URI in a `Flows/Event` JSON response). But repeatedly hit `https://verified.clearme.com/dashboard/error` (a 404) after entering a valid TOTP code. Eventually found via full (untruncated) response inspection that the backend actually returns `"screen_type":"success"` with a `redirect_url` — **the login itself succeeds server-side**; the frontend SPA has a routing bug that fails to complete the transition to the real dashboard. Never found a workaround (manual navigation to the `redirect_url`, waiting longer, console-error inspection all failed to reach the actual dashboard UI). This is a separate, real, minor frontend bug worth noting but not yet itself written up as a finding — low priority compared to actually completing the flow to get sandbox access for further testing (OAuth, verification session APIs with synthetic data).

## Key technical learnings for future CLEAR (or similar Salesforce Experience Cloud) sessions

- CLEAR's `X-CLEAR-CorrelationInfo` header format on my.clearme.com's `/v3/api/*` is `[sessionId='X'], [requestId='X'], [clientId='X'], [deviceId='X']` — single-quoted, not colon-delimited. Found by extracting `generateCIString` from a JS chunk. Required on every v3 API call or you get a generic "Correlation info missing/malformed" error that masks the real endpoint behavior.
- Setting a custom header like `X-Bug-Bounty` via Playwright's `browser.new_context(extra_http_headers=...)` applies it to EVERY request including third-party cross-origin ones (fonts, LaunchDarkly, etc.), breaking their CORS preflight and causing real app malfunctions (LaunchDarkly feature-flag init failures) that look like unrelated bugs. Use `page.route()` to scope custom headers to only the target domain.
- Playwright's `page.locator(...).fill()` looped over individual OTP input boxes can silently produce a DIFFERENT final value than intended (observed generated TOTP "601156" got submitted as "602404" due to focus-race with the app's own auto-advance JS). Use `page.keyboard.type(code, delay=100)` after clicking the first box instead — matches human typing and avoids the corruption.
- Salesforce Aura RPC protocol basics that worked: `generateCIString`-style `aura.context` needs a real `fwuid` (extract from any `getApplication` response) and the `loaded` map needs the actual app's `APPLICATION@markup://...` key for actions to be recognized — otherwise the framework silently returns `"actions":[]` with no error, which looks like "action doesn't exist" but can also just mean the referenced controller isn't part of THIS community's loaded bundle (true negative, not a config error on our end).
