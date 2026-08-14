---
name: project-go-ios
description: "go-ios VDP on Secur0 — Go library/CLI for iOS device automation (UI tests, app install, etc.), CVE-eligible, Safe Harbor, 0 historical reports (genuinely fresh target)."
metadata:
  node_type: memory
  type: project
  originSessionId: 46360d1a-7024-4f70-b01a-c28082c84e12
---

**UPDATE 2026-07-31: all 22 drafted findings are now SUBMITTED (confirmed by user).**

Program: **go-ios** (`github.com/danielpaulus/go-ios`), VDP on Secur0, CVE-eligible + Safe
Harbor. In scope: `https://github.com/danielpaulus/go-ios` only. **0 total reports, 0 accepted**
— genuinely fresh/untouched target, captured 2026-07-28, 30 days remaining. Cloned to
`recon/go-ios/repo` (`git clone --depth 50`). ~46,195 lines across 279 Go files. Pure
source-code audit (no live device access in this environment).

**What it is:** an OS-independent Go implementation of iOS device protocols (lockdownd,
instruments, AFC, usbmux, etc.) — install/launch/kill apps, pull syslogs, screenshots, WDA
automation, etc. Used as a CLI (`ios` command) and as a library. Companies mentioned as users:
headspin.io, Sauce Labs (device-farm context matters for the finding below).

**FINDING #1, drafted and submitted this session —
`findings/dia2/go-ios-restapi-unauthenticated-0000-bind/`**: the experimental REST API
(`restapi/`) starts with `router.Run(":8080")` in `restapi/api/server.go` — binds to **all
network interfaces** (`0.0.0.0:8080`), not localhost, with **no hardcoded way to change it**.
Read every middleware (`restapi/api/middleware.go`, registered in `routes.go`) and every
exported handler in `app_endpoints.go`/`device_endpoints.go`/`streaming_endpoints.go`/`wda.go` —
**zero authentication anywhere**, despite `restapi/main.go`'s swagger annotation
`@securityDefinitions.basic BasicAuth` declaring an intended-but-never-implemented auth scheme.
Any network peer that can reach port 8080 gets full unauthenticated control: install/uninstall
apps, live screenshots (2FA/private-message leak risk), syslog/ostrace streaming, GPS spoofing,
WebDriverAgent UI-automation sessions (tap/swipe/type). CVSS 4.0 AV:A (network-adjacent by
default; AV:N if operator port-forwards or runs in a cloud VM with a public IP) —
VC:H/VI:H/VA:H. Given headspin.io/Sauce Labs are named users (device-farm/shared-cloud context),
this is a realistic, not just theoretical, exposure.

**Also checked and confirmed clean**: `InstallApp` (app_endpoints.go) writes the uploaded `.ipa`
to `path.Join(appDownloadFolder, uuid.New().String()+".ipa")` — server-generated UUID filename,
not user-controlled, so no path traversal on the upload-destination path despite taking a
multipart file upload.

**FINDING #2, drafted and submitted this session —
`findings/dia2/go-ios-protocol-decoders-integer-underflow-panic/`**: systemic unchecked
integer-underflow-before-`make()` pattern found in 3 independent protocol decoders, each
confirmed with a real passing/failing Go test (not just static analysis):
- `ios/afc/client.go: readPacket()` — `h.ThisLen - headerSize` (both `uint64`) underflows to
  ~2^64, `make()` **panics immediately** (`runtime error: makeslice: len out of range`). Test
  PASSED (caught the real panic).
- `ios/xpc/encoding.go: decodeBody()` — `h.BodyLen - 8` (`uint64`), same panic behavior. Test
  PASSED.
- `ios/usbmuxconnection.go: decode()` — `muxHeader.Length - 16`, but `Length` is `uint32` not
  `uint64`, so worst-case underflow is bounded to ~4.29GB — does NOT exceed Go's slice-length
  ceiling, so `make()` succeeds instead of panicking; `io.ReadFull` then just returns a normal
  EOF error. Test intentionally "FAILED" (asserted a panic, got the ~4.29GB-allocation
  behavior instead — this IS the proof, documented honestly in the report rather than forcing
  a false "it panics too" claim).
Attack model: whatever go-ios treats as "the device" on the AFC/RemoteXPC/usbmux connection
(malicious/compromised physical device, rogue USB gadget, compromised usbmuxd, or a MITM on
the wireless CoreDevice tunnel) sends one malformed packet → AFC/XPC crash the host process
outright (unrecovered panic, `gin.Recovery()` doesn't cover library/CLI code), usbmux forces a
~4.29GB allocation (OOM risk on constrained hosts). CVSS 4.0 `AV:P/AC:L/AT:N/PR:N/UI:N/VC:N/
VI:N/VA:H/SC:N/SI:N/SA:N`. `ios/pcap/pcap.go`'s `getPacket()` has the correct guard pattern
(`if iph.HdrSize > PacketHeaderSize` before subtracting) and was cited in the suggested fix as
the reference example. PoC test files + go-test output attached as evidence.

**FINDING #3, drafted this session, MOST SEVERE SO FAR —
`findings/dia2/go-ios-afc-pull-path-traversal/`**: `ios/afc/fsync.go: Pull()` (used by
`ios files pull --srcPath --dstPath`) recursively mirrors a device directory to the host. For
each entry returned by `Client.List()` (parses the AFC `readDir` response), it does
`dp := path.Join(dstPath, v)` where `v` is a raw device-supplied string — `List()` only filters
the literal strings `"."`/`".."`, nothing stops an entry like
`"../../../../../../tmp/pwned"`. That escaped `dp` is then passed straight into
`os.OpenFile(dstPath, O_CREATE|O_WRONLY|O_TRUNC, os.ModePerm)` in `PullSingleFile()`, writing
device-controlled bytes to an attacker-chosen path outside the intended destination —
**full arbitrary file write on the host**, not just a crash. Classic path-traversal /
zip-slip pattern applied to a live device protocol. Proven end-to-end with a real passing Go
test (`ios/afc/poc_pathtraversal_test.go`) that scripts a mock AFC connection through the
*actual* `Pull()`/`List()`/`PullSingleFile()` code (no mocking of the vulnerable logic itself)
and confirms a file lands at `/tmp/go_ios_poc_pwned_by_device` with attacker content, outside
the destination dir. Real-world impact: a compromised/rogue device answering `readDir` with an
entry like `../../../../home/<user>/.ssh/authorized_keys` gets written with attacker content
the next time someone runs `ios files pull` against it — realistic RCE path. CVSS 4.0
`AV:P/AC:L/AT:N/PR:N/UI:N/VC:N/VI:H/VA:N/SC:N/SI:N/SA:N`. Not yet submitted — ready for review.

**FINDING #4b, drafted this session, SEPARATE report (different fix than
#4a's underflow guard) —
`findings/dia2/go-ios-lockdown-plistcodec-unbounded-length-dos/`**:
`ios/plistcodec.go`'s `PlistCodec.Decode()`/`PlistCodecReadWriter.Read()` (the Lockdown
protocol codec underlying almost every non-AFC/non-XPC service handshake — instruments,
house_arrest, mcinstall, simlocation, accessibility, crashreport mover, etc.) reads a raw
4-byte device-controlled length prefix straight into `make([]byte, length)` with **no maximum-
size check at all** (not an underflow — just missing an upper bound). A malicious device can
claim up to ~4.29GB for a message with no real payload behind it, forcing a multi-GB allocation
attempt on the host. Confirmed with a real passing test
(`ios/poc_lockdown_dos_test.go`) — error message shows `expected: 4294967280`, confirming the
allocation was actually attempted. Kept as a SEPARATE report from Finding #4a (the
underflow-panic one) per this program's report-merge rule: same general vuln class (missing
bounds check on device-controlled length) but the actual code fix is different (max-size cap
vs. subtraction guard), and PlistCodec is reached far more broadly than any single one of the
other 3 decoders. CVSS 4.0 `AV:P/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N` (Low
availability — unlike AFC/XPC this doesn't reliably panic, just risks OOM on constrained hosts).

**SESSION STATUS (2026-07-29):** search phase closed. 22 findings drafted total this session (1
submitted — Finding #1, unauth REST API — plus 21 more drafted in `findings/dia2/`), 2 parked as
not-submittable (TSS TLS MITM — informational, device-side crypto neutralizes it;
InterfaceToStringSlice — Low, CLI-only self-inflicted). 17 distinct vulnerability classes
covered. User is now moving on to prep the next programs; future findings for ANY target
(including if go-ios is resumed) go in `findings/dia3/` per [[feedback_findings_dia2_folder]] —
dia2 is closed. The 21 dia2 reports are still pending user review/submission — check the actual
Secur0 dashboard before assuming any of them got submitted (per
[[feedback_check_dashboard_not_memory]] pattern).

**FINDING #17, drafted this session, EASIEST-TO-TRIGGER PANIC OF THE SESSION —
`findings/dia2/go-ios-installapp-nil-pointer-panic/`**: `restapi/api/app_endpoints.go: InstallApp()`
does `log.Printf("Received file: %s", file.Filename)` BEFORE checking the `err` from
`c.FormFile("file")` — gin's `FormFile` returns `(nil, err)` on every failure path, so a POST
missing the "file" field nil-pointer-panics. Unique among this session's panic findings: requires
ZERO device interaction/malicious device, just one malformed HTTP request against the
already-unauth REST API. Confirmed with a real test showing the actual panic stack trace pinning
`app_endpoints.go:160`. Caught by `gin.Recovery()` (per-request 500, not a process kill) — lower
severity than #13 (log.Fatal) but real, verified, trivially reachable. CVSS 4.0
`AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N`.

**FINDING #16, drafted this session, LIKELY HIGHEST-IMPACT FINDING OF THE SESSION (found by
grepping for other os.Chmod/0777/os.ModePerm instances after the dproxy finding) —
`findings/dia2/go-ios-supervision-key-world-readable/`**: `ios prepare create-cert`
(`cmd_device_management.go: runPrepareCommand()`) generates a genuine `IsCA:true` RSA CA
certificate + private key valid for 10 YEARS via `ios.CreateDERFormattedSupervisionCert()` — this
is THE org-wide trust anchor for Apple-Configurator-style supervised pairing
(`ios.PairSupervised()` consumes exactly this key/cert to silently pair/control devices with NO
user interaction). Both `supervision-private-key.key` and `.pem` get written via
`os.WriteFile(path, data, 0o777)` — world-readable under any common umask (022/002 both leave
world-read intact; only umask ≥077 would block it, not a realistic default anywhere). Confirmed
with a real test: generated an ACTUAL key via the real unmodified function, wrote it exactly as
the CLI does, measured resulting mode 775. Blast radius is the key differentiator from #5/#14/#15
(the other local-multiuser findings): this isn't "compromise this one host's session" — a leaked
key lets the attacker silently pair/control EVERY device across the whole org that trusts this
supervision identity, for the full 10-year cert validity. CVSS 4.0
`AV:L/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:H/SI:H/SA:N` — first finding this session scoring
BOTH vulnerable-system AND subsequent-system impact as High, reflecting that the consequence
extends far past the host where the key leaked.

**FINDING #15, drafted this session, FIRST REPORT WITH SHORT PLAIN TITLE (new rule, forward-only —
see [[feedback_secur0_report_structure]]) — `findings/dia2/go-ios-dproxy-world-writable-socket/`**:
`ios dproxy` (USB traffic MITM proxy) replaces the usbmuxd socket and does
`os.Chmod(socketPath, 0o777)` — world-writable, and Chmod bypasses umask entirely (proven exact
777 result regardless of umask). Also `setupDirectory()` (0777 dir) + `writeBytes()` (0644 files)
for the recorded traffic dumps (full usbmux/lockdown protocol capture of the session) — world-
readable even under a conservative umask 022. Same local-multi-user threat model as #5 (symlink)
and #14 (tunnel shutdown) — third instance of this pattern this session. Confirmed with 2 real
passing tests (chmod-bypasses-umask proven directly; setupDirectory/writeBytes called for real,
resulting 775/644 measured on this system). CVSS 4.0
`AV:L/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N` — VC:H/VI:H since the world-writable
socket gives full device-command access, not just DoS (stronger than #14's availability-only
local finding).

**FINDING #14, drafted this session — `findings/dia2/go-ios-tunnel-agent-unauthenticated-shutdown/`**:
found by grepping for OTHER `log.Fatal`/`os.Exit` calls after #13 hit — `ios/tunnel/tunnel_api.go`'s
`tunnelInfoMux()` (the `ios tunnel start` agent's HTTP API, binds 127.0.0.1 by default, SAFELY
unlike other bind findings) has `GET /shutdown` (kills the whole agent via `os.Exit(0)`, 1s
delay) and `DELETE /tunnel/{udid}` (tears down one device's tunnel) with **zero authentication**
of any kind — not even for local access. Same local-multi-user threat model as Finding #5
(symlink), applied to a network endpoint instead of a file. Compounds with the main REST API:
`DeviceMiddleware()` calls `TunnelInfoForDevice()` on every device-scoped request for iOS17+
devices, so killing this agent breaks the main API's modern-device support too. Confirmed SAFELY
via the same subprocess-isolation technique as #13 (real `/shutdown` request sent, subprocess
exited cleanly via os.Exit(0) in ~1s, own session untouched). CVSS 4.0
`AV:L/AC:L/AT:N/PR:N/UI:N/VC:N/VI:L/VA:H/SC:N/SI:N/SA:L` — AV:L since default bind is safely
loopback-only (unlike #1/#7's AV:A/N), the vuln is the missing auth on top of that safe bind, not
the bind itself.

**FINDING #13, drafted this session, MOST SEVERE/EASIEST-TO-TRIGGER FINDING OF THE WHOLE
SESSION — `findings/dia2/go-ios-notifications-logfatal-killsprocess/`**: found while continuing
the business-logic search. `restapi/api/streaming_endpoints.go: Notifications()` calls
`log.Fatal(err)` (real `logrus.Fatal` → `os.Exit(1)`, NOT a panic) if
`instruments.ListenAppStateNotifications(device)` fails for ANY reason — no malicious device
needed, just a mundane connection failure (DDI not mounted, instruments already busy from
another concurrent op — made trivially likely given Finding #12's unbounded WDA sessions, a
transient hiccup). Unlike every panic-based finding this session, `gin.Recovery()` (registered in
server.go) CANNOT catch `os.Exit()` — it's not a panic — so this kills the ENTIRE server process
outright, not just the one request, taking down every other device/client being served
simultaneously. Confirmed SAFELY via the standard Go idiom for testing os.Exit-calling code:
re-exec the test binary as a subprocess (`exec.Command(os.Args[0], "-test.run=...")`) and assert
its exit code — verified subprocess exit status 1, own process untouched. Only 1 instance of
`log.Fatal`/`os.Exit` in all of `restapi/` (grepped, no siblings). CVSS 4.0
`AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:H` — SA:H (subsequent-system availability)
because every OTHER device/client loses service the instant the process dies, the key
distinction from the panic pile. Fix: `c.AbortWithStatusJSON` instead of `log.Fatal`, trivial
one-line change.

**FINDING #12, drafted this session, SECOND BUSINESS-LOGIC FINDING (user asked specifically for
more business logic, REST-reachable this time per the lesson from the parked
InterfaceToStringSlice one) — `findings/dia2/go-ios-wda-session-no-concurrency-limit/`**:
`POST /wda/session` (`CreateWdaSession`) has ZERO concurrency/rate limit — unlike `/apps/*`
(wrapped in `LimitNumClientsUDID`, even though THAT has its own race bug per Finding #9), this
endpoint has no equivalent check AT ALL. Every request unconditionally spawns a goroutine opening
2 new tunnel connections to the device's testmanagerd + drives a full XCTest session handshake —
expensive, stateful, per-request, zero throttling, unauthenticated. Confirmed with a real passing
test: 20/20 back-to-back requests for the SAME UDID all accepted (HTTP 200), 20 sessions
simultaneously live in `globalSessions`. This is a genuine "missing business rule" (not a race in
an existing one, like #9) — inconsistent security control application across the codebase (some
routes protected, this more-expensive one isn't). CVSS 4.0
`AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:L/SA:L`. Fix: apply `LimitNumClientsUDID()` (the
corrected version) to this route too.

**PARKED, Low/Informational (user pushback, correctly) —
`findings/dia2/go-ios-interfacetostringslice-broken-contract-PARKED-low/`**: `ios/utils.go:
InterfaceToStringSlice()`'s own doc comment says "It returns an empty slice in case of an
error" but does `result[i] = v.(string)` with no `, ok` check — panics on any non-all-string
input, confirmed with a real passing test. Reachable via `GetLanguage()` (backs `ios language`
CLI) feeding device-reported lockdown values into it. Initially drafted as Finding #11 (same
"broken promise" pattern as the screenshot.go one, found by grepping for "will not panic"/"safe
to"/"cannot fail" comments — good technique, worth reusing), but on reflection this instance is
the WEAKEST of the DoS pile: CLI-only (no REST route for `language`, unlike ostrace/screenshot
which ARE REST-reachable), one-shot command not a persistent/shared server process, and the
"attacker" is the same device the operator already deliberately chose to run the command
against — a panic vs. a clean error barely differs in practical harm for a one-off manual CLI
invocation. Parked rather than submitted, matching the earlier TSS precedent
([[feedback_no_informational_reports]]). The comment-grepping TECHNIQUE itself remains good and
found a real, higher-value hit (Finding #10, screenshot) — the lesson is to weigh REST-reachability
and persistent-process impact before drafting the next instance found this way, not to stop using
the technique.

**FINDING #10, drafted this session, "BROKEN PROMISE" BUG (found while hunting for more
business-logic candidates) — `findings/dia2/go-ios-screenshot-payload-panic/`**:
`ios/instruments/screenshot.go: TakeScreenshot()` does `msg.Payload[0].([]byte)` on the DTX
response with NO length check and NO type check — panics (index-out-of-range OR
interface-conversion) on a malformed-but-"successful" device response. Strong narrative: a
comment 15 lines away in `startScreenshotting()` (the MJPEG streamer's caller) explicitly says
"a screenshot failure must not take down a caller embedding go-ios" — but that only guards
against a returned `error`, not a panic INSIDE `TakeScreenshot()` itself, so the exact scenario
the code says must never crash the host is the exact scenario that does. Different mechanism
from the AFC/XPC/usbmux/DTX/ostrace/PlistCodec pile (those are raw binary length-prefix
underflows in wire decoders; this is an unchecked type-assertion+index on an already-deserialized
DTX method-call response) — application-level response validation, not protocol framing.
Reachable via `ios screenshot` CLI, the unauth REST API's `/screenshot`, and the MJPEG streaming
server. Confirmed with a real passing test (2 subtests) using this codebase's OWN established
convention for testing DTX responses (constructed `dtx.Message` values, matching
`processcontrol_test.go`'s `okMsg`/`transientErrMsg` pattern) rather than a full connection mock.
CVSS 4.0 `AV:P/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N`.

**FINDING #9, drafted this session, BUSINESS-LOGIC/RACE CONDITION (user explicitly asked for
"business logic" specifically) — `findings/dia2/go-ios-limitnumclients-race-condition/`**:
`restapi/api/middleware.go: LimitNumClientsUDID()` — the middleware wrapping all `/apps/*`
routes (install/uninstall/launch/kill/list), whose own doc comment states the business rule
"limits clients to one concurrent connection per device UDID at a time" — does `Load()` then
conditionally `Store()` on a `sync.Map` instead of the race-free `LoadOrStore()`. Two concurrent
FIRST-requests for the same new UDID can each create their own private semaphore channel, both
proceed into the "serialized" critical section at once. **Empirically confirmed real** (not just
theoretical) with a test hitting the actual unmodified middleware through a real gin router: 300
concurrent goroutines × 25 rounds, hit on round 3 with peak=2 concurrent. Honestly flagged as
medium-confidence on downstream impact in the report itself: the race is 100% proven, but the
concrete consequence (e.g. corrupted concurrent app installs) is reasoned/plausible rather than
verified against a real device (no device in this sandbox). CVSS 4.0
`AV:N/AC:H/AT:N/PR:N/UI:N/VC:N/VI:L/VA:L/SC:N/SI:N/SA:N` — AC:H reflects the narrow race window.
Fix: `sync.Map.LoadOrStore`. Also flagged incidentally: a stray `print("mid done")` debug
statement left in production code (not itself a finding, mentioned in the fix section).

**FINDING #8, drafted this session, YET ANOTHER DIFFERENT VULN CLASS —
`findings/dia2/go-ios-ui-install-no-integrity-check/`**: after user rejected a 7th "device sends
malformed data → panic" candidate (notificationproxy.go type-assertion panic, discarded, keep
searching for genuinely different classes) and asked to keep going, found:
`cmd_device_ui_install.go: downloadUIArtifact()` — `ios ui install wda`/`devicekit` downloads a
pre-built WebDriverAgent/DeviceKit runner from a HARDCODED THIRD-PARTY domain
(`deviceboxhq.com`, not Apple, not mentioned anywhere in the README) when operator doesn't pass
`--path`, with **zero integrity verification** (no checksum/signature check) before the artifact
gets signed with the OPERATOR'S OWN cert and installed on the device. TLS itself is fine here
(unlike the parked TSS finding) — the gap is purely missing content-integrity pinning. Classic
CWE-494 (Download of Code Without Integrity Check) — real supply-chain risk: domain
compromise/hijack/DNS-takeover of deviceboxhq.com = attacker code gets Apple-signed by the
operator and run on their device, inheriting the same unauthenticated WDA device-control surface
already established in Finding #7. Confirmed with a real passing test (in `package main`, calls
the actual unmodified function) proving substituted content is written with zero verification.
CVSS 4.0 `AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H` — first finding this session
with BOTH vulnerable-system AND subsequent-system impact scored (signing pipeline + the device).
This is the first report drafted under the NEW convention (see
[[feedback_secur0_report_structure]] update): PoC code + output embedded directly in Payload,
Attachments = None, no separate evidence/ files — user explicitly asked for this going forward
(not retroactive on earlier reports).

**FINDING #7, drafted this session (user explicitly asked for non-informational after parking
TSS) — `findings/dia2/go-ios-forward-binds-all-interfaces/`**: `ios/forward/forward.go: Forward()`
(backs `ios forward` CLI AND `ios ui run wda`/`devicekit` internally) hardcodes
`net.Listen("tcp", "0.0.0.0:"+hostPort)` with NO way to restrict to localhost. `ios ui run wda`
forwards WDA's port 8100 (confirmed via `devicePort:8100, healthPath:"/status"` — WDA's actual
port/health-check path) this way — WDA itself has ZERO auth (well-known), so this exposes full
unauthenticated UI-automation control (tap/swipe/type/launch apps) to the whole network,
completely independent of the already-reported REST API finding. Smoking-gun detail: `ios ui
run`'s own log line reports the URL as `http://127.0.0.1:<port>` even though the actual bind is
NOT loopback — clear evidence of a real bug (dev's own mental model was localhost-only), not
intentional design. Confirmed with a real passing test inspecting the actual bound address (this
sandbox resolved "0.0.0.0" to the even-broader IPv6 wildcard `[::]`, test asserts against either
form). CVSS 4.0 `AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N` — same severity class as
Finding #1 but a fully independent code path/fix (`ios/forward/forward.go`, not `restapi/`).

**PARKED, NOT SUBMITTABLE (informational only) —
`findings/dia2/go-ios-tss-tls-mitm-PARKED-informational/`**: `ios/imagemounter/tss.go:
getSignature()` disables TLS cert validation (`InsecureSkipVerify: true`) on a request to a REAL
internet-facing Apple server (`gs.apple.com/TSS`, iOS 17+ DDI personalization). Confirmed with a
real passing test that the config accepts any certificate. Initially drafted as Finding #6, but
on reflection (user pushback, correctly) the actual trust boundary — whether a developer disk
image gets authorized — is enforced by the DEVICE's own on-device signature verification
(SEP/AMFI) against Apple's real crypto keys, which this bug does NOT bypass; go-ios's broken TLS
here can at most cause a DoS of the mount (device rejects a MITM-forged ticket) or leak
non-secret device identifiers (ECID etc., already visible via other means). No concrete way to
leverage this into unauthorized-image-mounting or any other real impact was found → Informational
per [[feedback_no_informational_reports]] and [[feedback_reproducibility_not_severity]] (a
well-evidenced bug ≠ automatically a security finding; the trust-boundary question is separate
and decisive, and here the boundary holds). Kept the folder (renamed -PARKED-informational) and
PoC for reference but NOT going in the submission batch.

**FINDING #5, drafted this session, DIFFERENT VULN CLASS (not a length-validation bug) —
`findings/dia2/go-ios-debugserver-insecure-tmp-symlink/`**: after the user asked for something
with a different fix than the "add bounds check" pattern repeated across findings #2/#4a-g,
found: `ios/debugserver/debugserver.go: startLLDB()` writes its generated LLDB/Python scripts to
FIXED, predictable, world-writable `/tmp` paths (`PY_PATH="/tmp/go_ios_lldb.py"`,
`SCRIPT_PATH="/tmp/go_ios_lldb.sh"`, hardcoded consts) via
`os.OpenFile(path, O_CREATE|O_RDWR|O_TRUNC, 0o644)` — no `O_EXCL`, no per-invocation uniqueness.
Classic CWE-59/CWE-377 symlink attack: on any shared multi-user host (relevant given this
project's shared device-farm users), a local attacker pre-plants a symlink at that fixed path
pointing at any file the OPERATOR can write to; next `ios debug` run silently overwrites it.
Confirmed with a real passing test that plants a symlink to a throwaway victim file and shows
`startLLDB()` (real, unmodified) destroys its content via the followed symlink. CVSS 4.0
`AV:L/AC:L/AT:N/PR:N/UI:N/VC:N/VI:H/VA:N/SC:N/SI:N/SA:N` — AV:L (local multi-user threat model,
NOT the device-trust model of every other finding this session). Fix: `os.CreateTemp` instead of
fixed paths, or add `O_EXCL`. Distinct from #4a (RCE via template injection, same file — that one
is about unsafe CONTENT, this one is about unsafe DESTINATION path).

**FINDING #4g, drafted this session — `findings/dia2/go-ios-ostrace-unbounded-length-panic/`**:
SIXTH file with this pattern family: `ios/ostrace/ostrace.go` (backs `ios ostrace` CLI AND the
unauth REST API's `/device/{udid}/ostrace`). Two bundled instances (same file, same fix —
max-size cap): `startActivity()`'s handshake `plistLength` is a genuine device-controlled
**uint64** built via a byte-reversal trick with zero bound — confirmed with a real passing test
to **reliably panic** (`makeslice: len out of range`), same severity class as AFC/XPC's uint64
underflows but reached via direct declaration, not underflow. `ReadEntry()`'s per-log-entry
`length` (uint32) is the milder large-allocation variant, confirmed at safe demo scale (~500MB).
This is the most severe of the "unbounded length" (non-underflow) findings because it reliably
crashes rather than just risking OOM, and it's REST-reachable without auth.

**FINDING #4e, drafted this session — `findings/dia2/go-ios-dtx-payloadlength-underflow-panic/`**:
a FIFTH file with the same underflow-before-make() pattern, found independently:
`ios/dtx_codec/decoder.go`'s `Message.PayloadLength()` computes
`TotalPayloadLength - AuxiliaryLength` (both raw uint32 off the wire, no check) inside
`ReadMessage()`, the core DTX decoder underlying the `instruments` service (screenshot, process
launch/kill, device info — reachable via CLI AND the unauth REST API). Confirmed with a real
passing test building a full 64-byte DTX message. Same fix-class as #4a (subtraction guard), but
different file/protocol → separate report per this program's convention.

**FINDING #4f, drafted this session — `findings/dia2/go-ios-dtx-unbounded-length-dos/`**: same
`ios/dtx_codec/decoder.go` file as #4e but 2 DIFFERENT unbounded-length (not underflow) sites —
fragment-reassembly `MessageLength` and `AuxiliarySize` — same fix-class as #4b/#4c (max-size
cap), so bundled together but kept separate from #4e (different fix). Confirmed with 2 real
passing tests at safe demo scale (~500MB each, learned caution from #4c's OOM-kill).

**FINDING #4c, drafted this session, SEPARATE report (same file as #4a's xpc
underflow but different functions/fix) —
`findings/dia2/go-ios-xpc-object-decoders-unbounded-length-dos/`**: same
`ios/xpc/encoding.go` file as #4a, but 3 DIFFERENT functions with the missing-cap (not underflow)
pattern: `decodeString`/`decodeData` (1:1 byte amplification, same class as PlistCodec) and
`decodeArray` (16x-amplified — `make([]interface{}, numEntries)`, each slot 16 bytes, so a
malicious `numEntries` near uint32 max ≈ 64GB from one ~8-byte header). Confirmed with 2 real
passing tests using SAFE demo-scale values (10M entries ≈152MB measured; 500MB string) to avoid
risking this sandbox's ~5.8GB RAM. **Notably: an earlier test run using the full realistic
attack value (~4.29GB) actually got the Go test process OOM-killed by the kernel** — direct
empirical proof of impact, not just calculation (documented honestly in the report, then
swapped to a safe repeatable value for the shipped PoC). CVSS 4.0
`AV:P/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N` — VA:H (not Low like PlistCodec)
specifically because the OOM-kill was directly observed, not just theoretical.

**FINDING #4a, drafted this session, MOST SEVERE OVERALL — full RCE —
`findings/dia2/go-ios-debugserver-lldb-template-injection-rce/`**: `ios debug <app_path>` CLI
command (`ios/debugserver/debugserver.go: Start()`/`startLLDB()`) fetches the app's on-device
container path via `installationproxy.AppInfo.Path()` — a raw `map[string]any` value decoded
straight from the connected DEVICE's plist response, zero validation. That device-controlled
`container` string is rendered into a generated LLDB script using `text/template` (NOT
`html/template` — zero escaping), embedded directly inside a Python string literal:
`script device_app="{{.Container}}"`. A device reporting a container path like
`X"; import os; os.system("id > /tmp/pwned"); x="` breaks out of the string literal and injects
a real Python statement that LLDB's `script` command executes when
`exec.Command(LLDB_SHELL, "-s", SCRIPT_PATH)` runs — **full arbitrary code execution on the
host**, triggered just by running `ios debug` against a malicious/compromised/spoofed device.
Proven with a real passing Go test (`ios/debugserver/poc_template_injection_test.go`) that
parses+executes the actual unmodified `LLDB_FMT` template constant and shows the generated
script containing the injected `import os; os.system(...)` line verbatim (lldb itself isn't
installed in this sandbox, so the exec step wasn't run, but the vulnerable
template-rendering step — where the injection actually happens — is 100% real project code, not
reimplemented). CLI-only (not reachable via the REST API — no `/debug` route exists). CVSS 4.0
`AV:P/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N`. Not yet submitted — ready for review.
This is the most severe of the 4 findings from this session (crash < crash < arbitrary file
write < RCE).

**How to apply if resumed:** this is a big codebase (46k lines); `restapi/` (~1572 lines) and a
meaningful chunk of `ios/` (afc, usbmux, xpc, tlspsk, pcap) have been read now. Untouched areas
worth checking next: `ios/zipconduit/` (the app-install zip streaming used by both CLI and REST
API), `ios/house_arrest` (sandbox file access, similar path-risk profile to AFC — worth a
path-traversal-specific pass), `usbmuxdbuild/`, and the `cmd/` CLI argument parsing. The REST
API's other endpoints (`wda.go`, `device_endpoints.go`'s pairing/condition/image-mount
handlers) were skimmed for auth only, not for individual logic bugs (e.g. does `PairDevice` or
`InstallImage` have injection or path issues of their own, independent of the missing-auth
finding). Also worth a systemic grep across the rest of the codebase for the same
length-subtraction-before-`make()` pattern beyond the 4 instances already checked (3 vulnerable
+ 1 safe/pcap) — this may not be exhaustive.
