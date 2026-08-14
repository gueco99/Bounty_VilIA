---
name: project-autofac
description: "Autofac (.NET DI container) hunt state — CVE-eligible VDP, source-code-only audit of github.com/autofac/Autofac"
metadata: 
  node_type: memory
  type: project
  originSessionId: ff7451f9-ed99-4be8-8d13-3103f0c4f6ba
---

Active as of 2026-07-30. Program: **Autofac**, CVE-eligible VDP, safe harbor, 0 prior reports.
In-scope asset is only `https://github.com/autofac/Autofac` — this is a pure source-code audit
of a mature, widely-used .NET dependency-injection library, not a live web target.

**UPDATE 2026-07-31: all 5 findings below are now SUBMITTED (confirmed by user).** Any
"drafted, not yet submitted" phrasing further down in this file is stale — kept as-is for the
technical detail/methodology notes, but ignore the submission-status parts.

1 finding drafted and ready to submit (not yet submitted):
`findings/dia2/autofac-loadcontext-scope-reflectioncache-stackoverflow-dos/report_secur0.md` —
unrecoverable StackOverflowException (process crash) when disposing a
`BeginLoadContextLifetimeScope` scope, if any type anywhere in the process has a generic type
closing over an array of itself as its base type's generic argument (e.g.
`class Foo<T> : Base<Foo<T>[]>`). Root cause: `TypeAssemblyReferenceProvider.
PopulateAllReferencedAssemblies` only guards the generic-arguments recursion path against
cycles, not the array-element or base-type paths — an incomplete fix for previously-reported
and supposedly-closed issue autofac/Autofac#1437. Confirmed live: installed .NET 8/10 SDKs into
the scratchpad (no dotnet was present on this machine), built a throwaway console app with a
ProjectReference into `src/Autofac/Autofac.csproj`, and actually ran the crash (exit 134,
40k+ recursive frames) and the negative control (simple CRTP case, correctly guarded, exit 0).
Also patched the method locally and re-ran to confirm the suggested fix (add
`if (!activeWorkingSet.Add(inputType)) return;` at the top of the method) actually closes the
gap — then reverted the local patch (scratch clone at `recon/autofac/Autofac/`, not submitted
anywhere).

**Why the effort was high for one finding:** Autofac is an extremely mature, heavily tested
general-purpose library with no natural external-attacker-input trust boundary (its "input" is
developer-authored registration code, not remote user data), which structurally limits attack
surface for classic web vuln classes. Checked: no XML/deserialization/Process.Start/regex
surface exists in this repo at all. The `LifetimeScope.CreateSharedInstance`
double-checked-locking code looked correct (result fully constructed inside the lock before
being published). The productive angle here was auditing a *recently "fixed" GitHub issue*
for an incomplete fix, not blind fuzzing — worth trying that pattern again on other mature
libraries in this program if resuming.

**Second bug found, deliberately NOT reported (2026-07-30):** `Autofac.Core.Resolving.
SegmentedStack<T>` (public type) has a real, confirmed off-by-one in its `Enumerator.MoveNext()`
— the start condition `index > _activeSegmentBase` should be `>=`, so a segment with exactly 1
item enumerates 0 items via `foreach` (verified directly: `Count=1` but 0 items yielded).
This is the stack `CircularDependencyDetectorMiddleware` walks to detect direct cycles, so a
self-referencing component check gets silently skipped when exactly 1 prior request is on the
(sub-)stack — but `RequestDepth` (the independent global max-depth-50 circuit breaker in the
same middleware) is a separate counter untouched by segments, so the cycle is still caught one
level later regardless, and no stack overflow/DoS is actually reachable. Correct call per
[[feedback_no_informational_reports]] not to draft a report for this — real bug, no exploitable
security consequence once traced all the way through to the independent depth cap.

**Second finding SUBMITTED-READY (2026-07-30):**
`findings/dia2/autofac-opengeneric-multiservice-override-silent-bypass/report_secur0.md` —
silent, resolution-order-dependent bypass of a service override when an open-generic component
provides multiple services and a narrower override is registered for just one of them
(`AB<T>:IA<T>,IB<T>` + `AOverride<T>:IA<T>` + `BOverride<T>:IB<T>`: whichever of IA/IB is
resolved *first* correctly gets its override, the other silently gets the shared `AB<T>`
default instead, no error). Live-verified both directions symmetric. **Important nuance: this
traces back to a PUBLIC, already-open GitHub issue (autofac/Autofac#1465), filed purely as a
correctness bug with no security framing.** I added the novel contribution (a concrete
security-relevant repro — a "hardened override silently never applied" scenario — plus CVSS
and root-cause tracing into `OpenGenericRegistrationSource`/`ServiceRegistrationInfo`), and the
report cites #1465 transparently rather than claiming sole discovery. Flagged this duplicate-
of-public-issue tension to the user before drafting (asked via AskUserQuestion, user's answer
was "pues haz el reporte" — draft it, transparent citation was judged acceptable). Worth
recording as a pattern: **when a public, non-security-framed GitHub issue reproduces a real
bug, check whether it has a security-relevant framing nobody has articulated yet — that's a
legitimate, valuable contribution distinct from the original report, as long as it's cited
openly, not passed off as novel discovery.**

**Third finding SUBMITTED to Secur0 (2026-07-30, confirmed by user):**
`findings/dia2/autofac-root-tag-collision-splits-matching-scope-singleton/report_secur0.md` —
`LifetimeScope.CheckTagIsUnique()`'s loop (`while (parentScope != RootLifetimeScope)`) never
compares the true root scope's own tag against a candidate tag, at any depth, because the loop
exits the instant `parentScope` becomes the root object — so `BeginLifetimeScope(LifetimeScope.
RootTag)` silently succeeds anywhere in the tree instead of throwing `DuplicateTagDetected`
(verified every OTHER ancestor tag IS correctly rejected — bug is specific to root). Result:
`InstancePerMatchingLifetimeScope(RootTag)` — a real, documented way to bind a cross-cutting
"singleton" to the root tag — silently splits into two independent instances for any subtree
that creates a root-tagged shadow scope. Live-verified crash-free repro (Counter#1 vs Counter#2,
true root unaffected) AND verified the suggested fix (check `RootLifetimeScope.Tag` explicitly
before the loop) actually closes it, then reverted the local patch. This is the finding that
came from taking the user's "business logic con criticidad" prompt literally: scope/tag-based
lifetime matching (`InstancePerMatchingLifetimeScope`) is the closest thing Autofac has to
"business logic" — it's literally how multi-tenant/plugin-hosting apps enforce sharing/isolation
guarantees, so a silent break there has real product-security consequences.

**Fourth finding drafted (2026-07-30), different discipline — CI/CD, not C# source:**
`findings/dia2/autofac-unpinned-reusable-workflow-nuget-publish-secret/report_secur0.md` —
`.github/workflows/main.yml` calls a reusable workflow in a DIFFERENT repo
(`autofac/.github/.github/workflows/ci.yml@main`) unpinned (mutable branch, not a SHA) with
`secrets: inherit`. Confirmed by reading the referenced file's public content that it's not
theoretical: that shared workflow has a `publish` job that ships packages straight to
NuGet.org using `NUGET_API_KEY`. So a compromise of `autofac/.github`'s main branch =
automatic ability to publish a malicious `Autofac` NuGet package to a huge downstream
consumer base. Found by finally trying the `cicd-security` skill/discipline on this repo
after 3 rounds of exhausting the C# source itself — **the lesson: when a source-code VDP
audit plateaus, switch discipline entirely (CI/CD, dependencies, docs) rather than re-reading
the same code tree again.** No exploit attempted (out of scope: would require compromising
the other repo) — verification is the standard, accepted method for this finding class,
matching the precedent set by an earlier `findings/dia2/boost-iosx-unpinned-github-actions`
report for a different program.

**Fifth finding drafted (2026-07-30), probably the most severe of the five, zero preconditions:**
`findings/dia2/autofac-leaked-private-strongname-key/report_secur0.md` — `Autofac.snk` in the
repo root is a FULL private+public RSA keypair (confirmed via raw bytes: `0x07` +
`"RSA2"` magic = PRIVATEKEYBLOB, not a delay-sign public-only file), and it's the REAL,
live production key: built `Autofac.csproj` from this exact repo, inspected the resulting
`Autofac.dll` via `AssemblyName.GetPublicKeyToken()` → `17863af14b0044da`, which is Autofac's
well-documented real public key token used in `<bindingRedirect>` entries across the whole
.NET ecosystem for over a decade (confirmed via WebSearch). Concrete impact: anyone can compile
an assembly named `Autofac.Test`, sign it with this leaked key, and it will pass the repo's own
`[InternalsVisibleTo("Autofac.Test, PublicKey=...")]` check — full internal-API access, no
compromise needed, key is sitting in the repo right now. Handled the honest nuance carefully:
Microsoft's official position is that strong-name signing alone isn't a security boundary (so
I didn't overclaim "supply-chain package takeover" — that's the separate NUGET_API_KEY finding,
different mechanism), but `InternalsVisibleTo` specifically IS documented as access-control, so
that's the angle actually scored in CVSS. Found by finally checking a file (`Autofac.snk`)
referenced dozens of times across `.csproj` files that I'd been walking past all session
without ever opening — **lesson: any `.snk`/`.pfx`/key-looking file committed to a repo is
worth 30 seconds of `xxd | head` before moving on, regardless of how deep into a session you
already are.**

**Extra verification round (2026-07-30):** ran the project's own test suites end to end
(Autofac.Test 870/870 pass, Autofac.Specification.Test 498/498 pass) — no undetected
regressions. Downloaded the actual published NuGet package (v9.3.1) and confirmed it matches
source (same PublicKeyToken, clean strings scan, no supply-chain tampering already present —
negative but important result). Ran gitleaks across full git history (2922 commits) — only
hits are false positives in an old Sandcastle docs folder, confirming Autofac.snk is the only
real secret in the whole repo's history. Found and read the maintainers' own regression test
for #1437 (`TypeAssemblyReferenceProviderTests.cs`) — it tests exactly the simple CRTP case and
passes, with zero coverage of the array-wrapped variant, which is airtight confirmation finding
#1 is a real untested gap, not a fluke — added this citation to that report. Re-verified (more
rigorously) that net8.0/net10.0 don't define NETSTANDARD2_1, so they get the hard 50-depth cap
unconditionally — reconfirms (didn't change) the earlier call to not report the SegmentedStack
off-by-one standalone.

**How to apply:** if resuming this target, next candidate areas not yet audited:
`Features/Scanning` assembly-scanning extensions, `Core/Registration` sources, and the
`Disposer`/`SemaphoreSlim` TOCTOU race I spotted but didn't pursue (AddInternal's `IsDisposed`
check happens before acquiring `_synchRoot`, but `Disposable.IsDisposed` is set atomically
*before* `Dispose(bool)` runs, so the simple race I first suspected turned out not to be
exploitable — only a narrower semaphore-disposed-during-wait race remains, likely too low
severity/reproducibility to be worth more time).
