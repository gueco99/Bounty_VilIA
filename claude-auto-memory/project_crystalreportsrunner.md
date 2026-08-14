---
name: project-crystalreportsrunner
description: "CrystalReportsRunner (github.com/gerardo-lijs/CrystalReportsRunner) hunt state — C# .NET named-pipe IPC bridge for Crystal Reports, VDP, 6 reports/3 accepted. 1 finding DRAFTED+PARKED (not submitted): named pipe has no ACL, leaks plaintext DB credentials to any local user. Not live-verified (no Windows env available)."
metadata: 
  node_type: memory
  type: project
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

Target: `github.com/gerardo-lijs/CrystalReportsRunner` — small C# library
(~4000 lines) bridging modern .NET (Core/5+) apps to Crystal Reports (which
only runs in .NET Framework 4.8) via a separate "runner" process
communicating over a named pipe. VDP, 6 reports/3 accepted historically.

**Finding #1 DRAFTED, PARKED (not submitted — save-don't-submit mode,
[[feedback_hunt_save_dont_submit_mode]]): named pipe has no ACL, leaks
plaintext DB credentials to any local Windows user.**
`CrystalReportsEngine.cs` creates the pipe server
(`PipeServerWithCallback<...>`) with no `PipeSecurity` parameter anywhere;
confirmed the underlying transport dependency (NuGet `PipeMethodCalls`
v4.0.3, github.com/RandomEngy/PipeMethodCalls) ALSO never passes
`PipeSecurity` to its internal `NamedPipeServerStream` construction (read
PipeServer.cs directly from that repo). .NET's documented default ACL for
an unconfigured `NamedPipeServerStream` grants "Everyone"/anonymous READ
access. `Report.Connection` (`CrystalReportsConnection`, in
`Report.cs`/`CrystalReportsConnectionFactory.cs`) carries plaintext
`Username`/`Password` and is a parameter on every single RPC call
(`Print`/`Export`/`ExportToMemoryMappedFile`/`ShowReport`/
`ShowReportDialog`) — meaning every report render sends DB credentials
over this unprotected pipe. Real-world relevant since Crystal Reports is
commonly deployed on multi-user Windows Terminal Server/Citrix/RDS boxes.
Draft CVSS 4.0: `AV:L/AC:L/AT:P/PR:L/UI:N/VC:H/VI:N/VA:N` — Medium-High.

**Caveat, explicitly flagged in the report itself:** could NOT live-verify
on a real Windows machine (no such environment available in this session's
sandbox) — the finding rests on (a) direct source review of both this repo
and its exact pipe-transport dependency, confirmed via WebSearch/WebFetch
against PipeMethodCalls' own GitHub, and (b) well-documented, longstanding
.NET/Windows platform behavior for unconfigured named pipe ACLs (same bug
class as several real historical CVEs in other Windows software). Should
be verified end-to-end (second unprivileged Windows user reading the pipe
while another user renders a report) before/if submitting — flagged this
explicitly to the user as a "needs live confirmation" caveat rather than
overclaiming a tested PoC.

Files: `findings/dia3/crystalreportsrunner-namedpipe-no-acl/report.md`.

**Checked and ruled out (not independently reportable):** `document.Load(report.Filename)`
(no sanitization, but only reachable via the same pipe as finding #1, not
a separate root cause); `GetRunnerPath()`'s subfolder-based runner .exe
discovery (standard install-directory trust model, same as any app with a
plugins folder — not a novel risk); `ODBCHelper.cs` (only touches
HKEY_CURRENT_USER, no privilege boundary crossed); `ProcessJobTracker.cs`
(standard, widely-reused "kill child on parent exit" Job Object pattern,
not security-relevant).

**Finding #2 DRAFTED, PARKED (not submitted): unsafe `Type.GetType()` on
attacker-influenced string during DataTable JSON deserialization — STILL
UNPATCHED in the latest published NuGet package (v1.5.1, 2025-12-04).**
`DataSetJsonConverter.cs`'s `DataTableJsonConverter.ReadJson()` did
`Type.GetType(jsonDataColumn.DataType)` on an unvalidated string from
pipe-received JSON, then used the result to construct a live
`DataColumn`. `Report.DataSets` (sent on EVERY `ICrystalReportsRunner` RPC
call — Print/Export/ExportToMemoryMappedFile/ShowReport/ShowReportDialog)
is the reachable path. This is the textbook .NET deserialization
gadget-chain primitive (same family as BinaryFormatter/TypeNameHandling
CVEs). **The maintainer found and fixed this themselves** (commit
4d06f09, "Enhance DataTable JSON deserialization type safety", replaces it
with a strict allowlist of primitive types) — but that fix commit is
chronologically AFTER the `v1.5.1` version-bump commit and was NEVER
released: confirmed by checking out the `v1.5.1` git tag directly (still
has the raw `Type.GetType()` call) AND independently confirming via
NuGet.org that v1.5.1 (2025-12-04) is still the latest published version.
Every current consumer (`dotnet add package LijsDev.CrystalReportsRunner.Core`)
is exposed. Could not build a full RCE gadget chain (no Windows/.NET
runtime available, and would need to know what's loaded in a real
CrystalReportsRunner.exe process) — framed the report around confirmed
type-resolution/DoS impact as the floor, with the maintainer's own "for
security" fix commit message as evidence the real risk is rated higher
than that. Draft CVSS 4.0: `AV:L/AC:L/AT:P/PR:L/UI:N/VC:L/VI:L/VA:H` — High.
Separate root cause/fix from finding #1 (pipe ACL) — different bug, per
[[feedback_report_merge_rule]]. Files:
`findings/dia3/crystalreportsrunner-unsafe-typegettype-deserialization/report.md`.

**Lead investigated, added as a secondary note to finding #1 (not its own
report):** `MemoryMappedFileUtils.CreateFromStream()` /
`ReportExporter.ExportToMemoryMappedFile()` has the SAME "no explicit
security descriptor" pattern (`MemoryMappedFile.CreateNew()` with no
`MemoryMappedFileSecurity`) exposing the FULLY RENDERED report output
(real business data, not just connection metadata) under an
enumerable-prefix name. Researched whether this is exploitable the same
cross-session way as the pipe — got genuinely conflicting signals
(github.com/dotnet/runtime/issues/111591 suggests memory-mapped files
without an explicit `Global\` prefix may be session-isolated by default,
unlike named pipes which live in a single machine-wide namespace) — did
NOT write this up as its own scored finding given the real uncertainty;
added as an unscored "worth checking" note inside finding #1's report
instead of overclaiming.

**Finding #3 DRAFTED, PARKED (not submitted) — strongest of the three:
local named pipe squatting/impersonation via the project's own shipped
runner .exe.** `Shell.cs`'s `LijsDev.CrystalReportsRunner.exe` is a
standalone executable that connects to WHATEVER `--pipe-name` it's given
via plain CLI arg, with zero authentication. `CrystalReportsEngine.cs`
tolerates up to 60s for the legitimate runner to connect
(`WaitForConnectionAsync`), with no post-connection identity check.
Confirmed via the PipeMethodCalls dependency's own source
(github.com/RandomEngy/PipeMethodCalls) that `maxNumberOfServerInstances`
defaults to 1 (first-come-first-served, no re-validation). Combined: a
local attacker who discovers the (enumerable, fixed-prefix) pipe name and
launches their OWN copy of the SAME legitimately-installed .exe with that
pipe name, racing the real runner, wins and becomes the trusted RPC
endpoint — receiving every `Report` (DB creds per finding #1) and able to
return arbitrary fake results. No custom tooling needed, just the
product's own shipped binary + winning an ordinary race. Draft CVSS 4.0:
`AV:L/AC:L/AT:P/PR:L/UI:N/VC:H/VI:H/VA:L` — High. Found by reading
`Shell.cs` in full for the first time (had only seen it referenced before)
— the user's explicit "vuelve a mirar algo, una función random o nueva"
prompt is what led to actually opening this file. Files:
`findings/dia3/crystalreportsrunner-pipe-squatting-impersonation/report.md`.

**Session-productive pattern reused here:** checking a project's OWN recent
commit history for security-flavored fixes, then verifying whether that
fix actually made it into a published release — the same "check the fix
for completeness" instinct as the cogny/CodeWeaver sessions, but applied
to "was it released at all" rather than "does the fix have a gap."
