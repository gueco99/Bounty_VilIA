---
name: feedback_fuzzer_exclude_auth_methods
description: "before writing an introspect-and-call-every-method fuzzer against a client library, hard-exclude login/logout/session methods and mock every HTTP stack the library uses, not just the first one found"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 34489275-58f5-410f-8b5b-40d13626490b
---

When building an automated harness that introspects a class and calls every public method with a
fuzzed argument (e.g. a path-traversal payload), always do two things BEFORE the first run, not
after:

1. **Hard-exclude any method whose purpose is to reach a real external auth/session endpoint**
   (`login`, `logout`, `resume_login`, `connect`, `authenticate`, etc.). A fuzzed argument that
   fails validation often falls through to the library's REAL default behavior rather than
   erroring cleanly — for a login method, that means a real credential-based network attempt.
2. **Mock every HTTP stack the library uses, not just the first one found.** A library can use
   more than one transport (e.g. `requests` AND `curl_cffi` in the same codebase, one for most
   calls and another for specific strategies/fallbacks). Mocking only one gives false confidence
   — the unmocked path still makes real, unintended network calls.

**Why**: on python-garminconnect (2026-08-07), an early version of a method-fuzzer included
`login(tokenstore=<traversal payload>)` in its sweep. The invalid tokenstore path caused a
fallthrough to the real credential-based login chain using throwaway fake credentials, and since
only `requests.Session.send` was mocked (not `curl_cffi`, which some of that library's login
strategies use), 3 real login attempts went out to the target's live authentication servers
before this was caught mid-run and disclosed to the user immediately. No account was touched
(garbage credentials), but it was real, unintended traffic to a live third-party production
service — exactly the kind of unscoped live-target interaction that should never happen by
accident.

**How to apply**: before running any introspect-and-call-every-method harness against a client
library (auth wrappers, API SDKs, anything with a "connect"/"login" step), explicitly list which
methods are pure local-state/read operations vs which ones intentionally reach the network, and
exclude the latter category by name from the fuzz loop — don't rely on args being "obviously
fake" to fail safely, since fallthrough-to-default behavior is common and easy to miss when
scanning dozens of methods at once.
