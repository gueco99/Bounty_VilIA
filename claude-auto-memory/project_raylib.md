---
name: project-raylib
description: "Raylib (github.com/raysan5/raylib) hunt state — C game/graphics library, VDP, CVE-eligible, 15 reports/0 accepted historically. 1 finding DRAFTED+PARKED (not submitted): heap buffer over-read + real crash in LoadModel()/LoadIQM() via a crafted 124-byte .iqm file, double-PoC'd (ASAN + real non-instrumented SIGSEGV) against real unmodified source."
metadata:
  node_type: memory
  type: project
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

Target: `github.com/raysan5/raylib` — widely-used C game/graphics library
(rcore.c, rshapes.c, rtextures.c, rtext.c, raudio.c, rmodels.c). VDP,
CVE-eligible. 15 total reports, 0 accepted historically — strong signal
that prior reports were likely weak "malformed file crashes the parser"
claims without a real compiled PoC or a clear trust-boundary argument, OR
that this is a genuinely hard/well-scrutinized target. Decided the
response to a 0% acceptance rate is MORE rigor (real compiled PoCs against
unmodified source), not skipping the target.

**Finding #1 DRAFTED, PARKED (not submitted — save-don't-submit mode,
[[feedback_hunt_save_dont_submit_mode]]): heap buffer over-read + reliable
crash in LoadModel()/LoadIQM() via a crafted .iqm file.** `src/rmodels.c`'s
`LoadIQM()` (raylib's own hand-written IQM binary-format parser, reached
from the public `LoadModel(fileName)` API for any `.iqm` file) calls
`LoadFileData()` which returns the REAL file size into `dataSize` — but
`dataSize` is then never referenced again anywhere in the ~750-line
function. Every offset (`ofs_meshes`, `ofs_triangles`, `ofs_vertexarrays`,
`ofs_joints`, per-vertexarray `va[i].offset`, etc.) and count
(`num_meshes`, `num_triangles`, `num_vertexes`, ...) is read straight from
the untrusted file header and used directly as memcpy source/length with
ZERO validation against the actual buffer size — confirmed via grep that
literally no bounds check exists anywhere in the function. A SECOND,
independent issue: per-mesh `first_vertex`/`num_vertexes` (also fully
attacker-controlled) aren't validated against the file's global
`num_vertexes` used to size the intermediate vertex/normal/texcoord/color
buffers, allowing OOB reads even within otherwise-consistently-sized
buffers.

**Double PoC'd against the real, unmodified `src/rmodels.c`** (linked the
actual file against a small stub.c providing only the handful of external
symbols it references from other raylib .c files — none reached before
the crash):
1. ASAN build: a 124-byte crafted file (`num_meshes=1000`,
   `ofs_meshes=124` = EOF) triggers a precise
   `AddressSanitizer: heap-buffer-overflow READ of size 24000` at
   `rmodels.c:4799`, full stack trace `LoadModel -> LoadIQM -> memcpy`,
   confirming the exact 124-byte `LoadFileData` allocation it overruns.
2. Plain `-O2` release build, NO sanitizers: the same tiny file format
   with `num_meshes=4000000000` produces a REAL SIGSEGV (exit 139) —
   proving this isn't just an ASAN-only finding, it crashes ordinary
   production builds.

Draft CVSS 4.0: `AV:L/AC:L/AT:P/PR:N/UI:P/VC:L/VI:N/VA:H` — High. Scored
conservatively on the confirmed crash/OOB-read; did NOT claim a specific
information-disclosure exploit chain (heap garbage does get copied into
the resulting Model's name/material/vertex data, which COULD leak
depending on the host app, but I didn't build that further and said so
explicitly in the report).

Files: `findings/dia3/raylib-iqm-oob-read/` (report.md, build_and_run.sh,
run_output.txt, poc/{main.c,stub.c,malicious_asan.iqm,malicious_segv.iqm}).

**Build technique reused from the Peercoin C++ PoCs this session:**
compile the target's own real, unmodified source file, stub out only the
handful of externally-referenced symbols needed purely to satisfy the
linker (never actually called before the crash), and drive it from a
tiny main.c calling the real public API. For raylib specifically: had to
add `-DRAYMATH_STATIC_INLINE` to avoid needing to stub ~20 raymath.h
vector/matrix functions (they're `extern inline` by default, fully
`static inline` — i.e. zero-symbol — under that macro).

**Not yet examined:** LoadOBJ (uses vendored tinyobj_loader_c, lower
priority — external lib not this repo's own code), LoadGLTF (vendored
cgltf), LoadVOX (correctly passes real `dataSize` into
`Vox_LoadFromMemory` — checked, NOT vulnerable to the same pattern),
LoadM3D (not yet checked). rtextures.c, raudio.c, rtext.c, rshapes.c,
rcore.c not yet reviewed at all. Session paused here to await user
direction — resume this list if/when the user returns to Raylib.
