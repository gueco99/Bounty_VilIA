---
name: project-kubereq
description: "kubereq & flame_k8s_backend VDP on Secur0 — Elixir Kubernetes client + FLAME K8s backend, CVE-eligible, Safe Harbor. SUPERSEDED: a later session (2026-07-27/28) found 5 real, live-verified findings after this one concluded 'nothing exploitable' — read the UPDATE section first."
metadata:
  node_type: memory
  type: project
  originSessionId: 46360d1a-7024-4f70-b01a-c28082c84e12
---

## UPDATE (2026-07-31) — all 5 findings now SUBMITTED (confirmed by user), dashboard #2749/2740/2733/2671 reconciled.

## UPDATE (2026-07-27/28 session) — corrects the "nothing exploitable" conclusion below

A later session did NOT stop at code-reading — it live-tested against ~9 disposable
kind clusters (`KIND_EXPERIMENTAL_PROVIDER=podman`, kind/kubectl downloaded to
`recon/kubereq_flame/bin/`, no sudo needed) and found **5 real findings**, drafted in
full Secur0-format reports under `findings/dia2/`:

1. `kubereq-watcher-silent-event-loss` (Low) — **directly contradicts this memory's own
   "not reportable... just an extra LIST call, not a missed-event bug" conclusion
   below.** Live HTTP request tracing proved the reconnect's fresh LIST call returns
   the CURRENT resourceVersion at reconnect time, not the one at disconnect time —
   anything that changed in between (confirmed: resourceVersion 1344 -> reconnect
   listed 1346, skipping 1345) is silently never delivered. The prior pure-reasoning
   conclusion here was wrong; verify live before trusting a "traced but not executed"
   conclusion in future sessions.
2. `kubereq-auth-exec-hash-collision` (CVSS High ~7.5-8.5, strongest) — this memory's
   Auth review below concluded "no injection" (true, for command construction) but
   never checked the credential CACHE mechanism. `Kubereq.Auth.Exec.run/1` keys its
   Registry cache by `:erlang.phash2(config)` alone, no re-validation on a hit. Live
   end-to-end proof: a zero-RBAC ServiceAccount read another identity's real Secret
   AND created+deleted a real Deployment using the victim's credential, via a found
   phash2 collision. User confirmed this one was submitted to Secur0.
3. `flame-k8s-backend-error-path-crash` (Low) — `FlameK8sBackend.HTTP.request/4`
   references a non-existent `:headers` struct field, crashing on any transport error
   instead of the intended clean `{:error, ...}`. Not mentioned in this memory's flame
   backend section below (that section only covered manifest-building, not the HTTP
   client's error path).
4. `kubereq-can-i-wrong-json-key` (Medium) — `Kubereq.can_i?/3` sends path-based auth
   checks under the wrong JSON key (`resourceAttributes` instead of
   `nonResourceAttributes`), confirmed wrong in both directions against real RBAC. Not
   reviewed by this memory at all (can_i? isn't mentioned below).
5. `kubereq-vulnerable-mint-hpax-deps` (Low-Medium, weakest) — this memory's "mix.lock
   dependency audit" below says "all current/recent releases, no known-vulnerable
   pinned versions spotted" — that was true AT THE TIME but 5 CVEs against mint/hpax
   were published since (confirmed via OSV.dev against the exact locked versions:
   mint 1.9.0, hpax 1.0.3). Re-run a fresh OSV/CVE check rather than trusting an old
   "looked current" note - dependency freshness is time-sensitive in a way other
   conclusions here aren't.

**Unreconciled discrepancy, not resolved by this update:** [[feedback_check_dashboard_not_memory]]
notes the dashboard shows 4 open reports (#2749/#2740/#2733/#2671) from a prior
untracked session, never reconciled against either this memory's "0/69" framing or the
5 findings above. Check the actual Secur0 dashboard for overlap before assuming the 5
findings above are all novel.

**#2740 reconciled (2026-07-30) — closed Informational, confirmed correct, no pushback
filed.** This is the `flame-k8s-backend-error-path-crash` finding from item 3 above
(`FlameK8sBackend.HTTP.request/4` referencing non-existent `:headers` struct field ->
`KeyError` instead of clean `{:error, reason}`). Triager Cristian closed it as
Informational: "if the apiserver is unreachable the pool doesn't start either way."
User asked to verify before accepting. Traced the actual `FLAME.Pool` library code
(`deps/flame/lib/flame/pool.ex`, vendored in `recon/kubereq_flame/flame_k8s_backend/deps/`)
end-to-end: `start_child_runner/2` does `{:ok, pid} = DynamicSupervisor.start_child(...)`
with no fallback clause, so a backend-init failure crashes the pool via `MatchError`
even if `flame_k8s_backend` returned the "intended" clean `{:error, reason}` string
instead of crashing with `KeyError`. Same convergence confirmed on the post-startup
growth path (`async_boot_runner`/`handle_down`) — both a crash and a clean `{:error,
reason}` return end up handled identically via the `:DOWN` monitor message and retry
logic. **The bug only changes which exception type appears in the crash, never whether
the pool crashes or degrades gracefully** — there is no real availability delta to
demonstrate. Triage call confirmed correct; matches [[feedback_reproducibility_not_severity]].

**#2749 reconciled (2026-07-30) — closed Informational, confirmed correct, no pushback
filed.** This is the `kubereq-can-i-wrong-json-key` finding from item 4 above
(`Kubereq.can_i?/3`'s `:path` branch nests under `"resourceAttributes"` instead of
`"nonResourceAttributes"`, so it silently answers a different RBAC question than the
one asked — confirmed live false-positive on a real cluster: broad resource wildcard
grant + zero `nonResourceURLs` grant still returns `true` for an arbitrary non-resource
path). Triager Cristian: "The apiserver still authorises the real request correctly,
so nobody gains or loses access" — closed Informational. Verified the underlying bug
claim is real (confirmed the wrong JSON key in `lib/kubereq.ex:186-195`), but `grep`
across both `kubereq/lib/` and `flame_k8s_backend/lib/` found **zero internal callers**
of `can_i?/3` — it's a public, documented helper with no consumer in this VDP's scope.
Cristian's point holds: the actual K8s RBAC enforcement point (the real apiserver
request) is untouched, and the "impact" section of the report itself admits the risk
is entirely in what a hypothetical downstream application would do with the wrong
answer — no such application exists in scope to demonstrate the chain. Unlike #2740,
could not disprove the triager here (no code-level counter-evidence found); accepted
as fair. Matches [[feedback_reproducibility_not_severity]] and [[feedback_no_informational_reports]]
("don't submit pure-Informational findings unless chained into real impact" — the
chain doesn't exist here).

**Lesson for future sessions on this or similar "0/N accepted, heavily hunted" VDPs:**
a prior session's "nothing exploitable" conclusion built from code-reading alone is not
reliable evidence the target is clean — this target had 2 High/Medium-severity, live-
demonstrable bugs sitting in code this same memory file had already read carefully.
Live dynamic testing (spin up real infra, drive the real code, cross-check against
ground truth) found what static reading missed, twice (the collision bug and the
watcher's actual reconnect behavior). Don't let a "heavily hunted" acceptance-rate
framing suppress live verification.

---

## Original session notes (superseded in part by the UPDATE above — kept for the
## sections still accurate: TLS, shell/atom/YAML-deserialization checks, path
## traversal via Req's path_params, the removed-TLS-workaround commit investigation)


Program: **kubereq & flame_k8s_backend**, VDP on Secur0, CVE-eligible + Safe Harbor. In scope:
`https://github.com/mruoss/kubereq` and `https://github.com/mruoss/flame_k8s_backend` (pure
source-code audit, no live infra — small Elixir libraries: kubereq is a Kubernetes API client
built on `Req`, flame_k8s_backend is a FLAME elastic-compute backend that spins up K8s pods).
**69 total reports, 0 accepted** — a strong "heavily hunted, genuinely clean" signal (same
category as [[project_gestionominegocio]]'s 0/26), captured 2026-07-28. 29 days remaining at
capture time. Cloned to `recon/kubereq/repo-kubereq` and `recon/kubereq/repo-flame_k8s_backend`
(`git clone --depth 50`). ~4247 lines in kubereq, ~920 in flame_k8s_backend.

**First full pass (this session) — read essentially every file in both libraries' `lib/`
directories start to finish, found nothing exploitable:**

- **TLS**: `Kubereq.Step.TLS` defaults to `verify_peer`, only skips verification when the local
  kubeconfig explicitly sets `insecure-skip-tls-verify` (standard kubectl-parity behavior, opt-in
  not a bug). `FlameK8sBackend.HTTP` (the flame backend's own in-cluster HTTP client) also
  correctly does `verify: :verify_peer` + `cacertfile`, with a documented OTP<27 IP-SAN
  workaround. Verified the **websocket path is not a separate insecure code path**: `PodExec`/
  `PodLogs` go through `Kubereq.Connect`, which uses `Mint.HTTP.connect/4` directly (bypassing
  Req's Finch adapter) — initially looked like a candidate for "TLS settings not inherited,"
  but confirmed by reading Req's own source (`req/finch.ex`) that `connect_options:
  [transport_opts: [...]]` is exactly the shape both Finch AND raw `Mint.HTTP.connect/4` expect,
  and confirmed via `Kubereq.Step.attach/1`'s pipeline ordering that `Step.TLS` (and Auth,
  Impersonate, etc.) run as request_steps before the custom `adapter:` fires — so the websocket
  connection genuinely inherits the same cert/verify config. Not a vuln, but worth documenting
  since it looked promising at first glance.
- **Auth** (all 5 kubeconfig auth mechanisms checked): client-cert/key (file and base64-data
  variants), static `token`, `tokenFile` (re-read fresh each request, correct rotation support),
  basic auth, and `exec` credential plugins. `Kubereq.Auth.Exec` uses `System.cmd(config["command"],
  List.wrap(config["args"]), ...)` — array-form, not shell string interpolation, no injection;
  matches kubectl's own exec-plugin design. Parses the exec plugin's stdout as YAML via
  `YamlElixir` (yamerl-backed, not vulnerable to the Ruby/Python-style arbitrary-object-construction
  YAML deserialization class of bug).
- **JSON**: `Kubereq.JSON` delegates to stdlib `JSON`/`Jason` `decode`/`decode!` with **no**
  `keys: :atoms` option — no atom-table-exhaustion vector from untrusted API server responses
  (a real, known Elixir-ecosystem bug class this avoids correctly).
- **URL/path construction**: the main request path (`Kubereq.Step.Operation` +
  `Kubereq.Discovery.resource_path_mapping`) uses **Req's built-in `:path_params` mechanism**
  (`:namespace`/`:name` placeholders), confirmed by reading Req's source
  (`req/lib/req/steps.ex:put_path_params`) that substituted values are passed through
  `URI.encode(&URI.char_unreserved?/1)` — i.e. a `name` containing `../` or `/` gets
  percent-encoded (`%2F`) before being placed in the URL, not left as a literal path separator.
  This is the CORRECT defensive pattern (unlike `flame_k8s_backend/k8s_client.ex`'s `pod_path/2`,
  see below).
- **`flame_k8s_backend`'s `K8sClient.pod_path/2`** (`"/api/v1/namespaces/#{namespace}/pods/#{name}"`)
  does raw string interpolation with **zero URL-encoding** — technically a path-injection
  primitive if `namespace`/`name` were attacker-controlled. **Not exploitable in practice**:
  every call site's `namespace`/`name` originates from either (a) the pod's own
  `POD_NAMESPACE`/`POD_NAME` env vars (set via K8s downward API `fieldRef`, trusted, not
  attacker-writable without already having pod-spec-write access) or (b) the K8s API server's own
  `generateName`-produced response after `create_pod!` (server-generated, not client input).
  Documented here in case a future call site changes this, but not reportable as-is — no
  attacker-reachable path.
- **`Kubereq.Discovery.resource_path_for/3`** embeds `resource["name"]` (from the K8s API
  server's own `/apis/<group>` discovery response) directly into a URL template via string
  interpolation, also unencoded, also technically not sanitized — but this only matters if the
  configured API server itself is malicious/compromised, which is already total-compromise
  territory for a K8s client library (same trust-boundary reasoning as
  [[feedback_reproducibility_not_severity]]) — not a viable finding.
- **Field/label selectors** (`Kubereq.Step.FieldSelector`/`Kubereq.Step.LabelSelector`): build
  `key=value`/`key!=value` selector strings via plain interpolation, no escaping of selector
  metacharacters (`,`, `=`, `!`) within a value. Looked like a possible "selector injection"
  (a caller-supplied value containing a comma could inject an extra clause) — but this is an
  **inherent limitation of the Kubernetes selector API itself** (no client library escapes this,
  because K8s's own selector grammar has no escape mechanism), not a kubereq-specific bug.
  URL-encoding wouldn't even help since the K8s API server re-parses the decoded selector string
  server-side regardless. Not reportable.
- **Impersonation headers**: built from local kubeconfig `current_user` data only (trusted local
  file), not attacker-reachable at runtime.
- **`flame_k8s_backend/runner_pod_template.ex`**: builds Pod manifests from app-developer-supplied
  config (`:manifest`/`:env` options), not from any runtime network input — not a viable injection
  vector; this is app-author-controlled configuration, same trust level as the app's own source
  code. Notable but non-security observation: `RELEASE_COOKIE` (the Erlang distribution cookie)
  is placed into the runner pod's env vars in plaintext — a known/common pattern for Elixir
  clustering on K8s (same approach `libcluster` uses), gated by whatever RBAC already lets someone
  read pod specs in that namespace — likely falls under this VDP's "optional hardening" exclusion
  category, not pursued.
- **`Kubereq.Watcher`**: found a real typo bug — `event["object"]["metdata"]["resourceVersion"]`
  (line ~328, missing the "a" in "metadata") means `state.resource_version` is always `nil`.
  Traced the actual impact: on reconnect (`handle_chunk(:done, ...)`), the buggy nil value gets
  silently overridden by a fresh LIST-based resourceVersion lookup anyway (the `Keyword.pop_lazy`
  fallback in `connect/3` fires since no `:resource_version` opt is pre-supplied) — so the
  observable effect is just an extra LIST call per reconnect, not a missed-event or security bug.
  Confirmed via code tracing, not reportable (correctness bug, no security impact, no CVSS).
- **`kubeconfig/service_account.ex`**, **`kubeconfig/file.ex`**, **`kubeconfig/env.ex`**: all
  standard, local-trusted-file reads, `tokenFile` re-read per-request (correct rotation), no path
  traversal or injection surface (paths come from local config/env, not runtime network input).
- **`Kubereq.PodExec`/`Kubereq.PodLogs`**: `command` for exec is passed as an array via the K8s
  API's own `command=` repeated query params (not a shell string) — "Not executed within a shell"
  per its own docstring, confirmed correct, no shell injection.

**Bottom line: both libraries are carefully, defensively written — proper TLS everywhere,
no shell/atom/YAML-deserialization injection classes, correct use of Req's built-in
percent-encoding for path params.** This matches the 0/69 acceptance signal. The only genuine
code bug found (the `Watcher` typo) has no security impact.

**Second pass (same session, continued after user said "sigue buscando") — git history,
CHANGELOG, mix.lock CVE check, GitHub issue trackers, all clean too:**

- **`git log` regression-hunting angle** (the technique that worked on
  `shishang-rollitosgratis-fix-incomplete-sushitomo`): found one real lead —
  `a673ccb "remove temporary fix which broke wildcard TLS matching"` in kubereq, which deleted a
  custom `check_ips_as_dns_id/2` hostname-verification override (a workaround for
  [erlang/otp#7968](https://github.com/erlang/otp/issues/7968)). Looked promising — a "we removed
  a TLS-related workaround" commit is exactly the shape of a real regression. **Verified via
  WebFetch what OTP#7968 actually does**: it's an *availability/compatibility* bug only (TLS
  hostname verification incorrectly **rejects** valid certs with IP-address SANs, e.g. when
  connecting to a K8s API server by bare IP) — not a security bug, since it's over-restrictive,
  not permissive. So removing kubereq's workaround only means OTP<27 users might see a bare-IP
  cluster connection fail (a compatibility regression the maintainer accepted, since CI now
  targets Erlang 28-29), never that an invalid cert gets accepted. Confirmed `flame_k8s_backend`
  still keeps the equivalent workaround gated for `OTP < 27` (`http.ex`), so it's the *more*
  defensive of the two anyway. Not reportable — checked the actual bug direction empirically
  instead of assuming "removed workaround = regression," which would have been a false lead.
- **CHANGELOG.md** (both repos): only one security-relevant line, `"Upgrade req to v0.6.1
  (includes security fixes)"` — confirmed `mix.lock` already pins `req 0.6.1`, so current HEAD
  already has that fix, no gap.
- **mix.lock dependency audit**: `mint 1.9.0`, `req 0.6.1`, `yamerl 0.10.0`, `yaml_elixir 2.12.2`,
  `plug 1.19.2`, `finch 0.22.0` — all current/recent releases, no known-vulnerable pinned
  versions spotted.
- **GitHub issue trackers** (both repos, via raw `api.github.com/repos/.../issues`): scanned all
  ~50 issues/PRs each — exclusively Renovate dependency-bump noise and one API-spec question, no
  prior security reports, no hints of unresolved bugs.
- **Remaining unread files closed out**: `kubeconfig/stub.ex` is a pure `Req.Test` testing helper
  (no production code path, not reachable outside test suites — not in scope for a runtime vuln).
  `discovery/resource_path_mapping.ex` is just a large static `%{"Kind" => "url/template"}` map,
  no logic.

**Conclusion after two full passes (source read + history/changelog/deps/issues archaeology):**
this is a genuinely hard, clean target, consistent with 0/69 accepted. Every promising-looking
lead (websocket TLS inheritance, unencoded path segments, selector injection, the removed TLS
workaround commit) was chased to a concrete, verified conclusion (not just assumed clean) and
came back either not-a-bug or not-attacker-reachable. **How to apply if resumed:** don't re-chase
any of the leads listed above, all were conclusively closed. If more time is invested, the only
genuinely unexplored angles left are: (a) fuzzing the actual YAML kubeconfig parser
(`yamerl`/`yaml_elixir`) with malformed/adversarial YAML for a parser-level crash (would need a
local Elixir/mix setup — not available in this environment, `apt install elixir` needs sudo
password not available here); (b) diffing `kubereq`/`flame_k8s_backend` against sibling/competitor
Elixir K8s clients (e.g. `k8s`, `bonny`) for a design pattern one has and the other lacks; (c)
asking the maintainer directly (out of scope for a VDP hunt). Given the acceptance rate, expect
this to stay a dead end without a fundamentally new angle.
