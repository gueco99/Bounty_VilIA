---
name: project-peercoin
description: "Peercoin (github.com/peercoin/peercoin) hunt state — C++ Bitcoin-Core fork with Proof-of-Stake, VDP, 9 reports/0 accepted historically. 4 findings DRAFTED+PARKED (not yet submitted, save-don't-submit mode): coinstake OOB read crash, unbounded PoS-temperature map DoS, block-message null-deref crash, dead-code tx-timestamp consensus check."
metadata: 
  node_type: memory
  type: project
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

Target: `github.com/peercoin/peercoin` — full Bitcoin Core fork adding
Proof-of-Stake (PoS)/minting. Large C++ codebase (~79MB checkout). VDP, CVE
eligible. 9 total reports, 0 accepted historically — suggests either prior
hunters submitted weak/inherited-Bitcoin-Core findings that don't apply, or
this is genuinely a hard target; Peercoin-SPECIFIC code (kernel.cpp, PoS/
minting logic) is the productive area since Bitcoin Core's own code has
already had years of professional audits — anything found there is unlikely
to be novel.

**Finding #1 DRAFTED, PARKED (not submitted — save-don't-submit mode,
[[feedback_hunt_save_dont_submit_mode]]): unauthenticated out-of-bounds read
in coinstake validation crashes any full node.** `src/kernel.cpp:
CheckProofOfStake()` does `txPrev->vout[tx->vin[nIn].prevout.n]` (and
`CheckStakeKernelHash()` right after does the same at
`txPrev->vout[prevout.n].nValue`) with ZERO bounds check that
`prevout.n < txPrev->vout.size()`. `CTransaction::IsCoinStake()` only
requires `vin.size()>0`, `!vin[0].prevout.IsNull()`, `vout.size()>=2`,
`vout[0].IsEmpty()` — nothing validates the index against the REFERENCED
tx's real output count (structurally impossible for IsCoinStake() to check,
since it only sees its own transaction). `CheckBlock()` is explicitly
context-free (can't look up other transactions) and
`PeercoinContextualBlockChecks()` (which calls CheckProofOfStake) runs
INSIDE `ConnectBlock()` BEFORE `CheckBlock()` is even invoked in that same
function. No signature, no real stake, no PoW needed to trigger — PoS
blocks skip the header PoW check entirely, and the crash happens while
SETTING UP the signature checker, before VerifyScript() runs. Confirmed
live with a real, compiled PoC linked directly against this repo's own
unmodified `src/primitives/transaction.cpp` (only a 2-line
GetAdjustedTime()/NodeClock::now() stub needed, to avoid requiring the
autotools-generated config header) — crashed in TWO separate build configs:
plain `-O2` release (SIGSEGV, exit 139, no sanitizers/hardening) AND
`-fsanitize=address,undefined` (libstdc++ `_GLIBCXX_ASSERTIONS` bounds
assertion abort, exit 134). Reachable via ordinary P2P: `net_processing.cpp`
handles incoming "block" messages via `ChainstateManager::ProcessNewBlock()`
(standard Bitcoin-Core-derived entry point), leading to
`Chainstate::ConnectBlock()` → `PeercoinContextualBlockChecks()` →
`CheckProofOfStake()`. Draft CVSS 4.0: `AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/
VA:H` — Critical. Files: `findings/dia3/peercoin-coinstake-prevout-oob-crash/`
(report.md, poc.cpp, stub.cpp, build_and_run.sh, run_output.txt).

**Build environment note:** got a minimal, targeted compile working WITHOUT
the full autotools build (which would need many dependencies + long build
time) by linking only the specific .cpp files needed
(`primitives/transaction.cpp`, `uint256.cpp`, `hash.cpp`,
`util/strencodings.cpp`, `crypto/sha256.cpp`, `crypto/sha512.cpp`,
`crypto/hmac_sha512.cpp`, `crypto/ripemd160.cpp`, `script/script.cpp`) plus
a 2-line stub for `GetAdjustedTime()`/`NodeClock::now()` (avoids
`util/time.cpp`'s `gmtime_s` Windows-ism and `timedata.cpp`'s
`PACKAGE_NAME`/autotools-config dependency). Useful pattern for future
targeted PoCs against this codebase without a full build.

**Finding #2 DRAFTED, PARKED (not submitted): unbounded `mapPoSTemperature`
map, never pruned — sustained memory-exhaustion DoS.** Peercoin's custom
per-peer-address anti-spam counter for free PoS headers
(`src/net.cpp: std::map<CNetAddr, int32_t> mapPoSTemperature`) is only ever
inserted-into (`operator[]` in 4 spots in net_processing.cpp) or read
(`.find()`), NEVER erased/cleared anywhere in the codebase (confirmed via
exhaustive grep) — no per-disconnect cleanup (unlike Peer/CNodeState objects
which DO get torn down in FinalizeNode()), no scheduled maintenance sweep
either. Any peer sending one valid-PoW, non-empty "headers" message (the
`operator[]` access happens BEFORE the header is validated) permanently
adds an entry for the life of the process. IPv6 makes distinct source
addresses free (a single /64 = 2^64 addresses), so no botnet needed — one
attacker machine, sustained over time, causes unbounded memory growth on
any publicly-reachable node. Lower urgency than finding #1 (requires
sustained effort, not instant), draft CVSS 4.0: `AV:N/AC:L/AT:P/PR:N/UI:N/
VC:N/VI:N/VA:L` — Medium. Static-analysis finding (grep-based, not a live
network PoC — appropriate for a "growth over sustained time" bug class).
Files: `findings/dia3/peercoin-postemperature-unbounded-map-dos/report.md`.

**Finding #3 DRAFTED, PARKED (not submitted) — even cheaper to trigger than
finding #1: unauthenticated null-pointer-deref crash via a single
unsolicited "block" P2P message.** `net_processing.cpp`'s BLOCK message
handler (~line 4714) does `CBlockIndex* prev_block =
LookupBlockIndex(pblock2->hashPrevBlock)` (returns nullptr for ANY
unrecognized parent hash — completely normal/expected), correctly
null-guards it a few lines later (`if (prev_block && ...)` for the
mutation check and anti-DoS work-threshold check), but then INSIDE the
`if (!fRequested)` branch dereferences it with NO null check:
`if (!prev_block->IsValid(BLOCK_VALID_TRANSACTIONS))`. `fRequested` is
keyed on the block's OWN hash (mapBlocksInFlight), unrelated to whether
prev_block is null — an attacker controls both independently. No stake,
no signature, no PoW needed — just any block-shaped payload with an
unrecognized hashPrevBlock (e.g. all-zero). Confirmed live with a real
compiled PoC linking directly against this repo's own unmodified
`CBlockIndex::IsValid()` (src/chain.h) — SIGSEGV, exit 139, on the first
attempt, with only a trivial `cs_main` stub needed for linking (no bearing
on the actual crash, which is a pure null `this->nStatus` read). Did NOT
build a full 2-node network PoC (net_processing.cpp's ProcessMessage() is
too dependency-heavy to isolate standalone like kernel.cpp was) — reachability
chain verified by careful direct source reading instead. Draft CVSS 4.0:
`AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H` — Critical, arguably stronger
candidate than finding #1 since it needs no valid transaction/coinstake
structure at all. Found by grepping net_processing.cpp for OTHER
Peercoin-specific (`peercoin:`-commented) customizations beyond the
already-covered PoS-temperature mechanism, per the user's "sigue mirando"
follow-up. Files: `findings/dia3/peercoin-block-message-null-deref/report.md`.

**Lead investigated, NOT pursued as its own finding:** `mapBlocksWait`
(net_processing.cpp, another Peercoin-specific in-memory map, holds full
`shared_ptr<CBlock>` payloads keyed by parent CBlockIndex* while waiting to
connect) looked like a possible unbounded-growth sibling to finding #2
(mapPoSTemperature) — but unlike that map, this one DOES have real
eviction logic (60s staleness check + erase on parent-rejection), so
didn't pursue it further as an independent memory-exhaustion report;
finding this map's cleanup-path code is what led to spotting the
un-null-checked `prev_block` dereference nearby (finding #3).

**Not yet examined:** the rest of kernel.cpp's stake-modifier logic (looked
thorough on read, no further issue spotted yet), wallet-side minting code
(`src/qt/minting*`, `CWallet::CreateCoinStake` in wallet.cpp — large,
~400-line function, self-referential/not network-attacker-reachable so
lower priority), `src/kernelrecord.cpp`, and the broader validation.cpp
PoS-specific sections beyond what was needed to trace these two bugs'
reachability. Session paused here per user's "busca otro programa" —
resume this list if/when the user returns to Peercoin.
