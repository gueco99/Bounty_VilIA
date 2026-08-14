---
name: project-edgepython
description: "edge-python VDP (CVE-eligible) — sandboxed Python subset VM/compiler on GitHub, pure source-code audit target, no live web app."
metadata:
  node_type: memory
  type: project
  originSessionId: 594c75b1-c898-47af-ba80-5e78975b8a6a
---

**UPDATE 2026-07-31: all 4 edge-python findings are now SUBMITTED (confirmed by user).**

New hunt started 2026-07-24, pivoted from [[project_shishang_app]] (paused, not killed — 13
findings drafted there, all submitted, see its checklist before resuming).

**Program facts:**
- Program name: "edge-python", VDP with Safe Harbor, **CVE-eligible** (badge shown on the
  program page — findings here can get real CVE IDs, unlike the other Secur0 programs so far).
- Scope: **only** `https://github.com/dylan-sutton-chavez/edge-python` — nothing else in
  scope, nothing explicitly out of scope either (blank "Fuera de alcance"). This is a pure
  **source code security audit**, not a live web app — no HTTP endpoints, no Burp proxy
  workflow applies here at all.
- Brand new program: 0 total reports, 0 in 90 days, all wait-time stats 0h — first mover here,
  no dedup risk from prior reports (but also no signal on triage quality/speed yet).
- 30 days 5 hours remaining at time of scope capture (2026-07-24) — time-boxed, track the
  deadline (~2026-08-23).
- Standard VDP restrictions apply (no destructive testing, no DoS, proportionality) but these
  matter less here since there's no live shared infrastructure to damage — it's a local
  clone/build, so "destructive" testing (e.g., a PoC that crashes the interpreter) is fine
  since it only affects our own local copy, not shared production.
- Mandatory researcher ID headers (X-Secur0-Username, email alias, UA prefix) are listed as a
  participation requirement but are largely inapplicable to a pure source-code target with no
  HTTP surface — keep them ready in case any live component turns up, but don't force them
  into a GitHub issue/PR workflow if the program's actual submission channel is the Secur0
  report form (same as other programs).

**Target description (from program page):** "Single-pass SSA bytecode compiler and threaded-
code stack VM for a sandboxed Python subset."

**How to apply — hunting approach for this target (source-code audit, not web):**
This needs a completely different methodology from the rest of this repo's web/API-focused
skills. Priority order for a sandboxed language runtime:
1. **Sandbox escape** — the single highest-value bug class here by far. Look for: builtins or
   modules the sandbox is supposed to block but doesn't (`__import__`, `open`, `eval`, `exec`,
   `os`, `subprocess`, `ctypes`); attribute-traversal escapes via dunder chains
   (`().__class__.__bases__[0].__subclasses__()`-style, classic CPython sandbox escapes);
   whether the VM exposes any host Python objects/functions to sandboxed code that leak access
   to the real interpreter.
2. **Compiler bugs (SSA bytecode compiler)** — miscompilation that produces bytecode violating
   the VM's own safety invariants (e.g., a way to make the compiler emit a jump/stack-op that
   the VM trusts without re-validating, since "single-pass" compilers are more prone to this
   than multi-pass ones that can do a validation pass).
3. **VM/interpreter memory safety** — stack overflow/underflow in the threaded-code stack VM
   (push without matching pop, or vice versa, causing OOB read/write on the value stack);
   unchecked bytecode operands (jump targets, local variable indices, constant pool indices)
   that aren't bounds-checked at execution time — check what language the VM itself is
   implemented in (native code = classic memory corruption territory; pure Python/managed
   language = more likely logic-only bugs).
4. **Resource exhaustion / DoS via the sandbox itself** — less valuable per VDP rules ("most
   rate-limiting issues" excluded) but an *uncontrolled* recursion/loop that bypasses whatever
   resource limits the sandbox claims to enforce could still be reportable if the sandbox's
   whole selling point is resource-limiting untrusted code.

**Environment set up this session:** Rust toolchain (rustup/cargo/rustc 1.97.1) installed
locally — wasn't present before. Repo cloned to
`/tmp/claude-1000/-home-diego-claude-bug-bounty/594c75b1-c898-47af-ba80-5e78975b8a6a/scratchpad/edge-python-audit/edge-python`
(scratchpad, ephemeral — re-clone if starting a fresh session: `git clone
https://github.com/dylan-sutton-chavez/edge-python.git`). Build/test with
`source "$HOME/.cargo/env"` then `cargo test --no-default-features -p edge-python --test tests
<name> -- --nocapture` (the `--no-default-features` skips a build.rs download of a prebuilt
compiler.wasm that isn't needed for local dev, per the repo's own README). Rust workspace,
`edition = "2024"`.

**Architecture notes (own analysis, not from docs):** Written in Rust, `#![no_std]`-style
(`alloc::` imports throughout), compiles to a `cdylib` WASM binary as the shipped artifact plus
an `rlib` for Rust host embedders. Core value type `Val` (`compiler/src/modules/vm/types/mod.rs`)
is an 8-byte NaN-boxed `u64` wrapper — tuple field is `pub(crate)`, so any code in the crate CAN
construct a `Val` from a raw `u64` bypassing the safe constructors (`Val::int`, `Val::heap`,
etc.), even though those constructors themselves are careful/correct. Only 3 call sites in the
whole crate do this raw construction: `compiler/src/modules/vm/snapshot.rs:97` (snapshot
deserialization) and two spots in `compiler/src/main/abi_bridge.rs` (WASM host ABI boundary,
where the embedding host is the trusted party passing back a `Val::raw()` it previously
received — that one looks like an intentional, documented trust boundary, not yet audited
further). **No `get_unchecked`/unchecked indexing exists anywhere in the crate** (verified via
full-crate grep) — this caps the severity of any bad-`Val` bug at a Rust bounds-check panic
(crash/DoS), not raw memory corruption, since `[profile.release] panic = "abort"` still makes
that panic an unrecoverable process/WASM-instance abort with no `catch_unwind` recovery
possible in the shipped artifact.

**Finding #1, drafted, not yet submitted:**
`findings/dia1/edgepython-snapshot-restore-unvalidated-val/report_secur0.md` —
`snapshot::restore()` deserializes every `Val` in a snapshot blob via `Val(raw_u64)` with zero
validation that heap-tagged Vals have an index within the restored heap's actual slot count.
The project's OWN test (`compiler/tests/snapshot.rs::corrupt_blobs`) documents the intended
invariant in its comment — *"Corrupt, truncated and cross-program blobs fail cleanly, never
panic"* — but only tests structural corruption (magic/format/truncation/trailing bytes/
cross-program fingerprint mismatch), never a corrupted `Val` payload inside an otherwise
well-formed, correctly-fingerprinted blob. Built and ran a real PoC (Rust integration test,
`cargo test`-executable, full source + backtrace saved in the finding's `evidence/` dir):
corrupt just one heap-tagged `Val`'s 28-bit index to the max value inside a legitimately-saved
blob → `restore()` silently returns `Ok(())` (accepts it, no error) → the very next standard
host call to resume the paused script, `vm.push_event("go")`, panics immediately inside
`HeapPool::get_mut` (`types/mod.rs:625`) via `VM::inject_event` (`vm/init.rs:73`) —
`index out of bounds: the len is 100 but the index is 268435455`. Confirmed via full-crate
grep that no `unsafe`/unchecked indexing exists anywhere, so this caps at a deterministic
panic/DoS (not memory corruption) — but under this crate's own `[profile.release] panic =
"abort"` (the real shipped WASM config), that panic is an unrecoverable process abort, which
is what makes it worth reporting despite not being memory-unsafe. Reported at CVSS
Availability:High / Confidentiality:None / Integrity:None, Local-not-Network attack vector
(conservative, since edge-python itself has no network endpoint — the risk is entirely about
what a host does with snapshot blobs it treats as portable/transportable, per the README's own
"restore anywhere" framing).

**How to apply next in this hunt:** the `pub(crate) u64` field on `Val` + the "only 3 raw
construction sites" search technique is a reusable technique for this codebase — any new
raw-`Val`-construction site found later is worth the same treatment: build a PoC that corrupts
the value and see what dereferences it.

**Ruled out (analyzed, no bug — don't re-investigate without new info):**
`cache.rs::fuse_method_calls()`'s `targeted` array never checks `targeted[i]` (the LoadAttr
instruction that starts a fusion window) — looked like a bytecode-relocation bug (a jump could
converge exactly on `i`, e.g. a ternary's true-branch `Jump` landing where `(a if cond else
b).method(x)`'s `.method` starts). Built and ran a real PoC
(`(a if cond else b).method(10,20,30)` with different `C`/`D` classes) — output was correct
(`60`). Confirmed benign: `CallMethod`'s design is receiver-position-independent (its operand
carries the attribute name; it just needs the receiver already on the stack below the args,
which every legitimate convergence point onto a LoadAttr's index structurally guarantees,
since branches converging there always computed the same object-expression prefix). Also ruled
out (by arithmetic, not a running PoC) an arity-collision variant where a nested inner `Call`
inside an argument list could be mistaken for the outer method's terminating `Call` — the
"+1 instruction to load the callee itself" structurally prevents the arity formula from ever
matching. `compiler/src/main/abi_bridge.rs`'s two raw-`Val` sites (`Val(bits)` in
`host_edge_encode`, `Val(bits)` in `wire_to_val`'s `WireValue::Int` arm) — the `Int` one is
safe (bits come from `inline_int_bits()`, a validated pure function). The `host_edge_encode`
one is where **Finding #2** (below) actually is.

**Finding #2, drafted, not yet submitted:**
`findings/dia1/edgepython-abi-float-nanbox-collision/report_secur0.md` — separate report from
Finding #1 (different endpoint: `compiler/src/abi.rs::classify_encode()` / the
`host_edge_encode` ABI entry point, not `snapshot.rs`; different fix location — per
[[feedback_report_merge_rule]]). `Val::float()` (the safe constructor,
`types/mod.rs`) deliberately canonicalizes any NaN whose bits collide with the VM's NaN-boxing
tag space (`(bits & QNAN) == QNAN` → forced to a fixed `CANON_NAN`) specifically to prevent a
float from ever aliasing a heap reference. But `classify_encode()`'s `Tag::Float` arm — the
function `host_edge_encode` (the WASM ABI's host-facing "encode any value" entry point) calls
— skips this entirely, passing `f64::from_le_bytes(bytes).to_bits()` straight into
`EncodeRequest::Direct`, which `host_edge_encode` then wraps with a raw, unvalidated
`Val(bits)`. Any real IEEE-754 NaN payload chosen to also satisfy `is_heap()` (tag nibble ≥4,
sign clear) forges a `Val` the VM treats as a heap reference with an attacker/host-controlled
index — no snapshot round-trip needed, a single ABI call with 8 crafted bytes is enough. Built
and ran a real PoC (Rust integration test, evidence in `evidence/`): confirmed
`classify_encode` passes the dangerous NaN through unmodified (while `Val::float()` on the
*same* bits correctly canonicalizes it — proving this is an inconsistency between two codepaths
in the same file, not a fundamental limitation), then completed the round-trip via the public
`VM::inject_event()` (same entry point real ABI event-delivery uses) → immediate panic in
`HeapPool::get`, `index out of bounds: the len is 97 but the index is 268435455`. Same
`unsafe`-free-crate caveat as Finding #1 (caps severity at deterministic panic/DoS under
`panic = "abort"`, not memory corruption) — but *more* severe in reach than Finding #1 since it
needs no snapshot infrastructure at all, just the ABI's most basic value-encoding call, and
it's a regression of a safety net (`Val::float()`) that demonstrably already exists elsewhere
in this exact codebase. Noted but not built: an in-range-index variant would cause type
confusion (aliasing a real but wrong-typed heap object) rather than a panic — flagged in the
report as an unexplored, potentially more interesting variant.

**Ruled out #2:** classic CPython sandbox-escape dunders (`__class__`, `__bases__`,
`__subclasses__`, `__globals__`, `__builtins__`, `__import__`) — full-crate grep found zero
occurrences of any of them. This VM only implements ordinary operator-overload dunders
(`__add__`/`__len__`/`__iter__`/etc.) plus `__name__`/`__self__`/`__func__` (bound-method
internals) — the whole classic attribute-traversal escape surface simply doesn't exist here.
Don't re-chase this angle without new info (e.g. a future version adding reflection).

**Finding #3, drafted, not yet submitted (found by chasing the `cache.rs`/`dispatch.rs`
`unsafe` blocks noted as unexplored):**
`findings/dia1/edgepython-stale-instance-cache-dunder/report_secur0.md` — separate report,
third distinct endpoint+fix (per [[feedback_report_merge_rule]]), and a genuinely different bug
*class* from #1/#2: no corrupted `Val`, no panic — a pure VM correctness/soundness bug, 100%
reachable from plain Python source with zero ABI/host interaction. The instance-dunder inline
cache (`cache.rs::InstanceCache`, promoted after `QUICK_THRESH=4` hits at a call site, consumed
by `dispatch.rs::exec_inst`) guards only receiver-**class-identity**
(`class_val.as_heap() != inst.class`) before dispatching straight to a frozen
`method_bits: u64` recorded at promotion time. But `HeapObj::Class`'s members are documented as
mutable elsewhere in this same codebase (`cls.attr = ...` / `setattr(cls, ...)`), and neither
`exec_store_attr`'s nor `call_setattr`'s `HeapObj::Class` branch (both in
`builtins/attr.rs`/`dispatch.rs`) calls `invalidate_inst` or anything equivalent — the *only*
call to `invalidate_inst` in the whole crate is a runtime class-identity `TypeMiss`, never a
class-mutation event. Built and ran a real PoC (evidence in `evidence/`): a class overloading
`__add__`, called 8x in a loop with the reassignment `C.__add__ = new_add` happening at
iteration 5 (after the site promotes at iteration 4) — expected `["1","1","1","1","1","999",
"999","999"]`, got `["1","1","1","1","1","1","1","1"]`: the reassignment is *permanently and
silently* ignored at that call site, forever, no error of any kind. (First PoC draft placed the
post-reassignment call as a textually separate `print(c + 1)` after the loop — that compiles to
a *different* bytecode `ip` with its own fresh, unpromoted cache slot, so it accidentally
re-resolved correctly and masked the bug; fixed by moving the reassignment inside the same loop,
same call site. Confirmed root cause via temporary eprintln instrumentation of
`record_inst`/`exec_inst`, showing exactly `hits=4,promoted=true` at iteration i=3 and the fast
path firing on every subsequent iteration including post-reassignment ones — reverted before
finalizing the PoC.) Arguably the most interesting of the three findings precisely *because* it
isn't a crash: it's silent semantic corruption, the class of bug that's historically been
treated as a real security issue in JS-engine inline caches (V8/JSC) for the same reason — any
host or in-sandbox logic that assumes dynamic dispatch is correct (permission revocation via
method reassignment, state machines, decorators) can be silently defeated once a call site has
warmed up.

**Finding #4, drafted, not yet submitted — the most severe so far:**
`findings/dia1/edgepython-constfold-ternary-miscompile/report_secur0.md` — separate report,
fourth distinct endpoint+fix. A genuine **compiler miscompilation** bug, not an edge-case VM
invariant violation: `optimizer.rs::constant_fold()`/`try_fold_binop()` decides whether to fold
a binop purely by walking *textually/positionally* backward (`prev_live`, skips only
already-dead instructions) to find its "two operands" — with **no `targeted[]`-style check**
for whether a jump can reach that position via a different control path (unlike
`fuse_method_calls` in `cache.rs`, which does track this, even though that particular check
turned out unnecessary there). A ternary `(a if cond else b)` compiles to `[cond]
[JumpIfFalse→L_else][LoadConst a][Jump→L_merge]  L_else:[LoadConst b]  L_merge:...`
(`parser/expr.rs::ternary_tail`) — when used as a binop operand, `L_merge` is where the true
branch (via `Jump`) and false branch (via fallthrough) converge, but `try_fold_binop` only ever
sees the false-branch's `LoadConst b` sitting positionally before the binop, and folds it in
unconditionally, then `compact_with_jump_remap` deletes/relocates code and remaps the true
branch's `Jump` to point at whatever survives — losing the true branch's own operand
entirely. Built and ran a real PoC (evidence in `evidence/`):
`cond=True; x=(1 if cond else 2)+3; print(x); print("done")` → expected `["4","done"]`, got
`["1","done"]` — the `+3` silently vanishes, no error, no crash (the `cond=False` case happens
to print the coincidentally-correct `5` since that's the branch the compiler actually folded
against). Confirmed via `exports.rs:48` that `constant_fold` is **unconditionally applied to
every compiled program** in the real pipeline — this isn't opt-in. Most severe of the four
because it needs zero setup (no cache warm-up, no ABI trickery, no snapshot) — a single
ordinary-looking line of Python silently computes the wrong answer. Noted but not built: same
positional-scan risk likely applies to `try_fold_unary` (same `prev_live` helper) — flagged in
the report as an unexplored sibling case.

**Confirmed (not yet PoC'd as a submittable finding) — `try_fold_unary` shares Finding #4's
bug:** quick follow-up test (`x = -(5 if True else 9)`) reproduced the identical miscompilation
(`5` instead of `-5`) via the exact same `prev_live` mechanism. Same file, same fix as Finding
#4 → belongs merged into that report, not a separate one, per
[[feedback_report_merge_rule]]. Not yet folded into the report file itself — do that before
submitting Finding #4.

**Finding #4 (report #2522) CLOSED as informative (2026-08-03).** Triager (Cristian, edge-python)
confirmed the root cause is real ("we confirmed the incorrect folding... looks backwards by
position without accounting for a Jump converging there") but closed as non-security: "the
effect is a wrong numeric result in your own program, without crossing any trust boundary."
This matches the exact caveat our own report already stated up front (subsequent-system
integrity scored "Ninguna/Baja... no demostrado en esta PoC, riesgo condicional") — a fair,
consistent closure, not a case of the triager missing something we'd shown. Not worth appealing
without new evidence that some real host embeds edge-python and trusts its arithmetic for a
security decision (don't have that). **Implication for the other 3 findings on this program**:
Finding #3 (stale instance-cache dunder, silent method-dispatch corruption after `__add__`
reassignment) has a stronger security framing than #4 — same "silent semantic corruption"
shape, but the V8/JSC inline-cache precedent (treated as a real security bug class historically)
applies more directly since dynamic-dispatch correctness is often relied on for permission
revocation / state-machine logic, not just arithmetic. If #3 also gets closed informative,
that's the point to reconsider the framing; don't preemptively downgrade it based on #4's
outcome alone.

**Promising but UNCONFIRMED lead, do not report without a working PoC — `mro_cache` never
invalidated on GC sweep:** `VM::mro_cache: HashMap<u64, Rc<Vec<Val>>>` (`vm/mod.rs`) is keyed
by a class's raw NaN-boxed `Val` bits (`cls.0`, which only encodes its heap **slot index** —
see `Val::heap(idx) = TAG_HEAP | (idx<<4)`), populated on every class definition
(`dispatch.rs` ~line 1040) and read on every class attribute/method lookup
(`handlers/methods.rs::lookup_class_member`/`lookup_class_member_after`, both call
`self.heap.get(c)` for each cached MRO entry `c` with **no `is_heap()`/liveness check**).
Verified by full read of `gc.rs::collect()` that `mro_cache` is **not** among the ~20 root
sources it marks (neither is `slot_pool`/`slot_templates`/`default_slots`, noted but not yet
individually chased). `HeapPool::sweep()` (`types/mod.rs`) confirmed to free a swept slot's
index onto a `free_list` that `alloc()` later pops and reuses for **any** new object — so in
theory a class that becomes fully unreachable, gets swept, and has its slot reused by an
unrelated new class should leave a stale `mro_cache` entry keyed by a colliding `Val`, causing
either a `HeapPool::get` panic (same crash class as Findings #1/#2, but via internal
cache-invalidation, not external/host input — would be a **different endpoint+fix**, so a
separate report) or, worse, cross-class method/data leakage if the reused slot happens to hold
another `Class`. Spent significant effort (session 2026-07-24) trying to build a real PoC:
confirmed `needs_gc()` (`dispatch.rs:899`) is checked **only inside the `ForIter` opcode
handler** — a `while` loop never triggers GC at all, `for` loops do. With a `for`-loop PoC,
confirmed via temporary `eprintln!` instrumentation of `collect()` that sweeps DO run
repeatedly and free hundreds of objects each time — but across ~2000 newly-defined candidate
classes, the orphaned `Derived` class's specific slot index (confirmed via `id()`, which
returns raw NaN-boxed bits per `builtins/identity.rs::call_id` — exposes the heap index
directly as `4 + idx*16`) never reappeared, while a neighboring slot index (`Base`'s, one
below `Derived`'s) did cycle back into use repeatedly. This suggests `Derived` specifically
stays reachable through some path not yet identified (contradicts the expectation that nothing
should reference it after its defining function returns) — possibly `slot_pool`/call-frame-slot
reuse retaining a stale reference in a way that coincidentally still gets marked, or a
subtlety in how a class's own `return id(X)` expression is compiled. **How to apply if resumed:**
before trying again, either (a) instrument `collect()`'s mark phase (not just sweep) to log
exactly what's marking Derived's specific Val, or (b) try a structurally simpler unreachability
scenario (e.g. a class assigned to a local variable that's then explicitly reassigned/`del`'d
at module top level, rather than orphaned via a function return) to rule out call-frame/
slot-pool interference. Do not submit this as a report until a clean, real PoC (panic or
observed cross-class data leak) is in hand — this is exactly the kind of claim
[[feedback_verify_before_confirming]] warns against making on inference alone.
