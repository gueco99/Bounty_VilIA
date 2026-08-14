---
name: project-krossbow
description: "Krossbow (Kotlin STOMP client) VDP hunt state on Secur0 — 1 confirmed WebSocket-leak finding ready, 1 NUL-byte hypothesis tested and disproven against a real broker"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9b76b8f7-973e-4bc0-989b-7b32bc7d0ee0
---

**UPDATE 2026-07-31: the WebSocket-leak finding is now SUBMITTED (confirmed by user).**

Program: **Krossbow**, VDP on Secur0 (same platform as [[project_nanoffmpeg]]). Scope:
`github.com/joffrey-bion/krossbow` — a Kotlin multiplatform STOMP 1.2 client over WebSockets
(coroutine-based, adapters for OkHttp/Ktor/Spring/SockJS). Started 2026-07-23.

Local clone: `recon/krossbow/krossbow` (nested dir from `git clone`). Full Gradle build works
in this sandbox but the daemon OOMs on default settings (5.8GB RAM, ~1.1GB free) — always run
with `--no-daemon -Dorg.gradle.jvmargs="-Xmx1200m"`, and scope `--tests` to the specific class
needed rather than running the whole suite, or it's slow/flaky.

**Confirmed finding, reported**: `findings/krossbow-connect-failure-websocket-leak/` — the
generic `catch (e: Exception)` branch in `StompWsExtensions.kt`'s private `stomp()` function
(~line 87) does NOT call `stompSocket.close(e)` before rethrowing as `StompConnectionException`,
unlike the other two catch branches (`CancellationException`, `ConnectionTimeout`) which do.
Directly contradicts the function's own KDoc ("If the connection at the STOMP level fails, the
underlying web socket is closed"). Verified trigger: a CONNECTED frame with a malformed
`heart-beat` header (missing the required comma) throws `IndexOutOfBoundsException` in
`toHeartBeat()` (`StompConnectHeaders.kt:125`, unchecked destructuring of `split(',')`),
wrapped as `StompConnectionException`, leaking the underlying WebSocket. Verified via a real
JVM test run (`./gradlew :krossbow-stomp-core:jvmTest`) using the project's own
`WebSocketClientMock` — confirmed `wsSession.closed == false` after the exception. Impact:
resource-leak DoS in client apps with auto-reconnect logic against a hostile/buggy broker.

**Hypothesis tested and disproven**: thought `HeaderEscaper.escape()` (headers/HeaderEscaper.kt)
not escaping the NUL byte (frame terminator) in header values could let an attacker-controlled
header value smuggle a second, forged STOMP frame past the receiver (analogous to CRLF/HTTP
header injection). Confirmed the encoder-level defect is real (a raw NUL does end up mid-frame
on the wire), but verified end-to-end against a real, independent STOMP broker (`coilmq`,
installed via `pip install coilmq --break-system-packages`, run on 127.0.0.1:61613, tested by
sending krossbow's exact encoded bytes over raw TCP — WS framing doesn't change the STOMP
payload bytes so this is a valid substitute for testing without spinning up a WS-STOMP broker)
that real spec-compliant parsers read headers line-by-line, so the embedded NUL is just literal
header content, not a frame boundary. No frame splitting occurred; the single frame was
delivered intact to the intended destination and the connection stayed healthy afterward. Did
NOT write a report for this — would have been a false positive.

**Why:** this is a first-time target, no prior session context existed. The user explicitly
asked (2026-07-23) to verify the NUL-byte hypothesis further before reporting rather than
report with a caveat or drop it — matches [[feedback_verify_before_confirming]] and
[[feedback_verify_against_live_target]] precedent from other targets.

**How to apply:** on resume, check whether the WebSocket-leak report has been submitted via
Secur0 yet. Areas not yet audited: the WebSocket adapter modules
(`krossbow-websocket-okhttp`, `-ktor`, `-spring`, `-sockjs`, `-builtin`) and the
`krossbow-stomp-*serialization` (kxserialization-json/jackson/moshi) conversion modules —
`krossbow-stomp-core` (frame encode/decode, headers, session, heartbeats) is the module audited
so far. Docker/podman work in this sandbox (`systemctl --user start podman.socket` first) —
useful if further live-broker verification is needed again.
