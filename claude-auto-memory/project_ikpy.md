---
name: project-ikpy
description: "ikpy VDP on Secur0 — CVE-eligible, pure Python inverse-kinematics library (URDF/MJCF parsing + scipy-based IK solver), fresh target (0 reports before this session), 4 findings submitted incl. undisclosed phone-home telemetry on every import (#3368) and 2 path traversal bugs"
metadata:
  node_type: memory
  type: project
  originSessionId: ff7451f9-ed99-4be8-8d13-3103f0c4f6ba
---

Target: `github.com/Phylliade/ikpy` — "IKPy, an Universal Inverse Kinematics library". VDP,
CVE-eligible, Safe Harbor. 30 days 5h remaining at scope capture (2026-08-03). **0 total
reports, 0 accepted** — genuinely fresh, first-mover target, no dedup risk.

**What it is:** pure-Python (no compiling) inverse-kinematics library. Loads a kinematic chain
from a URDF file, a MuJoCo MJCF file, DH parameters, or a custom JSON+URDF sidecar pair; solves
IK via `scipy.optimize.least_squares`/`minimize`; optional experimental JAX backend for
autodiff-accelerated solving. Small codebase (~3500 lines across `src/ikpy/`), no web/HTTP
surface at all — pure source-code audit, same methodology as edge-python/chezmoi (clone, build
locally, no live app).

**Local clone:** `recon/ikpy/repo`. Venv at
`/tmp/claude-1000/-home-diego-claude-bug-bounty/ff7451f9-ed99-4be8-8d13-3103f0c4f6ba/scratchpad/ikpy_venv`
(scratchpad, ephemeral — `pip install -e .` from `recon/ikpy/repo` to rebuild). Python 3.13.14,
numpy 2.5.1, scipy 1.18.0.

**Finding #1 SUBMITTED (report_id 3338, 2026-08-03): path traversal via the JSON chain
loader.** `Chain.from_json_file()` (`src/ikpy/chain.py`) reads `chain_config["urdf_file"]`
straight from untrusted JSON content and concatenates it onto `chain_basedir` with plain string
`+` (no `os.path.join`, no containment check) before handing it to `from_urdf_file()` ->
`ET.parse()`. A single `../` in a shared/downloaded `chain.json`'s `urdf_file` field escapes the
intended sibling directory and loads any file on disk the process can read — classic zip-slip-
style bug. Confirmed the write side (`to_json_file()`) correctly stores only
`os.path.basename(...)`, proving this is a read/write asymmetry, not intentional design.
Live-verified end-to-end: crafted `chain.json` with `"urdf_file": "../victim_secret_dir/
secret_robot.urdf"`, loaded via `Chain.from_json_file()`, confirmed the "secret" file's joint
name (`secret_joint_marker_XYZ123`) appeared in the resulting `Chain` object. CVSS
`AV:N/AC:L/AT:P/PR:N/UI:P/VC:L/VI:N/VA:N` (Confidentiality kept Low, not High: the read is
constrained to files that parse far enough as XML/URDF to expose content, or at minimum an
existence/shape oracle via distinguishable error messages — not a guaranteed raw-content read
of arbitrary file types).

**Ruled out (verified live, not vulnerable):**
- **Classic XXE** via `xml.etree.ElementTree` (used by both `URDF.py` and `MJCF.py` parsers,
  not `lxml`) — a `<!ENTITY xxe SYSTEM "file://...">` payload raises a clean
  `ParseError: reference to external entity`, confirmed empirically. Python's built-in expat
  does not resolve external entities.
- **Billion-laughs / entity-expansion DoS** — same parser raises
  `ParseError: limit on input amplification factor (from DTD and entities) breached` — modern
  libexpat (bundled with this Python) has built-in amplification-factor protection.
- **No `eval`/`exec`/`pickle`/`subprocess`/`os.system`** anywhere in `src/ikpy/` (full-crate
  grep, zero hits) — no code-execution surface at all in this pure-math library.
- **`inverse_kinematics.py`'s IK solver** — uses `scipy.optimize.least_squares`/`minimize`,
  which have their own bounded internal iteration limits; no unbounded-loop DoS risk from
  adversarial targets/starting angles.
- **MJCF parser has no `<include file="...">` support** (checked `MJCF.py`/`mjcf/utils.py`) —
  MuJoCo's real include directive isn't implemented, so no analogous traversal via that path.
  URDF parser doesn't load referenced mesh files either (`<mesh filename="...">` is parsed as
  plain geometry data, never opened/read) — no mesh-path traversal or SSRF surface.

**Finding #2 SUBMITTED (report_id 3342, 2026-08-03): unbounded recursion in MJCF body-tree
traversal.** `mjcf/MJCF.py`'s `_traverse_body_tree()` recurses once per nested `<body>` element
with no depth cap (`current_depth` param is threaded through every call but never compared
against a limit) — a ~126 KiB MJCF file with 5,000 nested `<body>` tags (live-verified, 6-line
Python generator) causes `RecursionError` via the ordinary `Chain.from_mjcf_file()`/
`get_mjcf_parameters()` path; `ET.parse()` itself handles the nesting fine, the failure is
purely ikpy's own recursive walk. **Explicitly flagged the same ambiguity as chezmoi's parked
format-indent-width bomb**: self-contained/local-script framing is weak (self-inflicted), real
severity depends on an unproven "shared service embeds ikpy to process third-party MJCF files"
scenario — reported honestly with that caveat spelled out in the Impact section (not asserted
as demonstrated) rather than silently inflating or silently parking it; user explicitly said
send it anyway after seeing the caveat. Kept CVSS conservative (VA:L, not H) to match. Read
`link.py` fully while investigating (`sympy.lambdify()` is used for symbolic->numeric matrix
compilation, which internally uses `exec()` on generated source — noted as a real RCE primitive
*if* non-numeric/attacker-string content ever reached the symbolic expression, but every
current caller passes only `float()`-validated scalars into it, so no live injection path
found).

Also noted while reading `MJCF.py`: `_get_default_class()`'s inner `find_class()` helper calls
`element.getparent()` — an `lxml`-only method that doesn't exist on stdlib
`xml.etree.ElementTree.Element` (would raise `AttributeError` if ever called) — but this inner
function is defined and never actually invoked (dead code, the real logic uses a different loop
a few lines below). Not exploitable since unreachable; not reported.

**Full-codebase coverage reached this session — every file in `src/ikpy/` has now been read**:
`mjcf/utils.py` (quat/euler/axisangle/xyaxes/zaxis -> rotation-matrix/RPY conversions, pure
numpy math, no I/O) — noted one degenerate-input edge case (`xyaxes_to_rotation_matrix`
divides by `np.linalg.norm(x_axis)` with no zero-check, unlike its sibling
`axisangle_to_rotation_matrix` which does guard `norm < 1e-10`) but this only produces
NaN-poisoned output for a degenerate zero vector, not a crash — same "silent wrong number, no
trust boundary" shape already closed as informative on edge-python (#2522), so not reported.
`jax_backend.py` (540 lines, the experimental JAX backend) and `utils/jax_geometry.py` — pure
JAX numeric code, no file I/O/subprocess/pickle/exec anywhere (grepped explicitly). `link.py`
already covered above (`sympy.lambdify` note). `utils/geometry.py` — pure matrix-math helpers,
no I/O. `utils/plot.py` — matplotlib visualization only, no security surface.

**Finding #3 SUBMITTED (report_id 3350, 2026-08-03): write-side counterpart of #3338, more
severe.** User asked to keep checking "every corner" after the full-file read; re-reading
`chain.py`'s remaining ~200 unread lines (I'd only read `from_json_file`/`to_json_file`/
`from_urdf_file` before, not `_json_path`/`forward_kinematics`/`inverse_kinematics` wrapper/
`plot`) surfaced a second, independent traversal: `Chain._json_path` builds
`os.path.dirname(urdf_file) + "/" + self.name + ".json"`, and `self.name` is ALSO set directly
from untrusted JSON content by `from_json_file()` (the `"name"` field, separate from the
already-reported `"urdf_file"` field). Live-verified: `chain.json` with `"name": "../victim_
target_dir/pwned_config"` + a normal sibling URDF -> `Chain.from_json_file(...).to_json_file
(force=True)` wrote `pwned_config.json` outside the intended directory. Different property,
different field, arbitrary-file-**write** not read (by default limited to creating new files —
`force=False` raises `OSError` on an existing target — but `force=True` overwrites anything
`.json`-suffixed) — genuinely separate root cause/fix from #3338 per this program's own
per-endpoint fix granularity, so reported separately rather than folded in. CVSS
`AV:N/AC:L/AT:P/PR:N/UI:P/VC:N/VI:L/VA:N`.

**Also checked this pass, clean:** `.github/workflows/ci.yml` — `on: [push]` only (no
`pull_request_target`, no untrusted-fork-PR trust issue), publish job gated on tag push +
modern OIDC trusted publishing (no static PyPI token secret), zero free-text PR data
interpolated into any `run:` block. `contrib/transformations.py` and `scripts/hand_follow.py`
are standalone legacy example scripts depending on external `rospy`/`tf`/`poppy` packages not
part of ikpy's own dependencies and not included in the distributed package (`setup.cfg`'s
`package_dir` points only at `src/`) — out of the installable attack surface entirely.
`setup.cfg`'s `install_requires` has zero version pins (`numpy`, `scipy`, `sympy` unpinned) —
nothing to check for a known-vulnerable pinned version, always pulls latest.

**Found but NOT submitted — parked, same self-inflicted question as MJCF DoS, user's call this
time was to skip it:** cyclic URDF causes a genuine, uncatchable infinite loop (not just a
`RecursionError`) in `get_urdf_parameters()`/`_find_next_joint()`/`_find_next_link()` — neither
tracks visited link/joint names, so a joint whose child eventually cycles back to an
already-visited link makes `has_next` stay `True` forever. Live-verified: a 484-byte, 2-joint
cyclic URDF hung `Chain.from_urdf_file()` past an 8s external `timeout` kill, zero output, zero
exception. User asked the same "does this only harm me" question as chezmoi's
format-indent-width bomb; honest answer given: yes, in the single-script scenario it's
self-inflicted like the others, but this ONE is categorically worse than the MJCF
recursion/format-indent-width siblings because no `try/except` in the embedding application can
ever catch it (no exception is ever raised — the thread simply never returns), unlike
`RecursionError`/memory-bomb exceptions which a defensively-written host CAN guard against.
User's final call: don't submit if it doesn't harm anyone else — parked, not sent. Full draft
kept in case a stronger multi-tenant-embedding argument surfaces later:
`findings/dia3/ikpy-urdf-cyclic-infinite-loop/report_secur0.md`.

**Also noted, NOT a security finding, functional bug only:** `DHLink.__init__`
(`src/ikpy/link.py`) calls `Link.__init__(self, use_symbolic_matrix, length=length,
bounds=bounds)` — passes the `use_symbolic_matrix` bool as the positional `name` argument,
so `self.name` ends up being `True`/`False` instead of the caller's intended `name` string.
Real bug (DH links get mislabeled), but purely a correctness issue with no trust-boundary
angle — not reported.

**Finding #4 SUBMITTED (report_id 3368, 2026-08-03): undisclosed phone-home telemetry on
every import — the strongest finding of the whole ikpy session, and unlike #1-3, needs NO
"who's the victim" caveat since it affects literally every user unconditionally.** User pushed
me to keep looking at "corners not yet checked" — `src/ikpy/__init__.py` (41 lines, never read
before this pass) turned out to unconditionally spawn a background daemon thread on package
import that makes a real HTTP GET to `https://static.scarf.sh/a.png` with
`ikpy_version`/`python_version` params and a `User-Agent: ikpy/<version>` header — introduced
deliberately by commit `39a8a14` ("Add Scarf analytics pixel to track library usage"). Checked
EVERY doc file (README, doc/, SUMMARY.md, tutorials.md, CITATION.cff) for any disclosure —
zero mentions of scarf/analytics/telemetry/phone-home anywhere; the only "tracking" hits in
README are the unrelated "trajectory tracking" robotics feature. No `DO_NOT_TRACK` env var
check, no opt-out flag, no config gate of any kind — fires on bare `import ikpy`, before any
function is ever called. Live-verified via mocking `urllib.request.urlopen` (captured the real
call the unmodified code makes, without needing to actually hit the third-party service):
confirmed exact URL/headers/timeout. This affects EVERY install/import — individual devs, CI
pipelines, security scanners just inspecting the package, production deployments — silently
revealing the importing machine's IP + version fingerprint to a third party
(static.scarf.sh/Scarf Systems) with zero consent. CVSS `AV:N/AC:L/AT:N/PR:N/UI:P/VC:L/VI:N/
VA:N` — real but modest confidentiality impact (IP + version metadata, not credentials/app
data), scored honestly rather than inflated, but genuinely the most universally-reachable
issue found on this target since there's no attacker/victim precondition at all, just
"install and import the library."

**Strengthened evidence for #3338 (not a new report, same root cause/fix — per report-merge-
rule this is an addendum, not a separate finding):** the read-side traversal doesn't need `../`
at all if the victim calls `Chain.from_json_file("chain.json")` with a bare filename (no
directory prefix) — the single most natural way to reference it after `cd`-ing into a shared
folder. `os.path.dirname("chain.json")` is `""`, so `chain_basedir + "/" + urdf_file` becomes
`"/" + urdf_file` — a plain ABSOLUTE path in the JSON's `urdf_file` field (no dots, nothing
suspicious-looking at all) then resolves directly, no relative traversal needed. Live-verified:
`urdf_file: "<absolute path>"` with `Chain.from_json_file("chain.json")` invoked from inside the
shared directory loaded the absolute-path file directly. `secur0_api.py` has no
comment-on-existing-report capability, only `create_report` — didn't build one ad hoc. If the
user wants this added to #3338 later, they'd need to comment on the Secur0 dashboard
themselves; this note preserves the exact repro for that.

**Session conclusion (revised):** every `.py` file in `src/ikpy/` plus the CI workflow and
non-package example scripts have now been read. 3 findings submitted (3338 read-side JSON
traversal, 3342 MJCF recursion DoS, 3350 write-side JSON traversal), all live-verified. If
resuming further: `tests/` directory itself not yet read (could reveal an edge case the
maintainer already considered and guarded against, worth checking before re-deriving); next
genuinely untested angle beyond that is dynamic/fuzzing-style testing of the URDF/MJCF parsers
with a wide corpus of malformed files rather than more manual hypothesis-driven reading.
