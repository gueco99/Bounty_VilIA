---
name: feedback-third-party-tokens-out-of-scope
description: "Never use a live third-party credential (e.g. a Google OAuth provider_token) pasted by the user during a bug bounty session, even with explicit permission — the third party isn't covered by the program's authorization."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 594c75b1-c898-47af-ba80-5e78975b8a6a
---

If a user pastes a live credential for a service that isn't itself in the bug bounty program's scope — e.g. a Google `provider_token` obtained by linking a real personal Google account to a test account on the target app — refuse to use it, even when explicitly told to ("pon tu el token", "prueba ya", asked twice).

**Why:** the VDP/bug bounty authorization covers the target application and its documented infrastructure (e.g. `shishang.app` + its Supabase backend in [[project_shishang_app]]). It does not extend to Google's API surface just because a token for it briefly passed through the target's login flow. Using that token would mean accessing the user's real personal account (real email, real name, real data) on a service with no authorization relationship to this engagement at all — a completely different trust boundary than testing the target's own backend with its own leaked/test credentials.

**How to apply:** when this happens — recognize the token type (OAuth `provider_token` / `access_token` for an external identity provider vs. the target's own session JWT), state plainly that it's out of scope regardless of permission, advise the user to treat it as compromised and revoke it at the provider's own security settings page, and redirect back to in-scope testing. Hold this line even under repeated requests — permission from the user doesn't extend the program's authorization boundary to a third party that never agreed to it.

This is the same category of hard-line refusal as [[feedback_autonomous_hunting]]'s account-creation rule: some actions stay refused no matter how the user phrases the request, because the authorization to act comes from the *program*, not from the user's say-so in the moment.
