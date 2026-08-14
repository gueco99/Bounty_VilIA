---
name: project-kubernetes-hackerone
description: "Kubernetes bug bounty program on HackerOne — 82 in-scope assets across kubernetes/* GitHub orgs, tiered rewards, CNCF-run. Active finding: git-sync RCE via --ref injection, confirmed live."
metadata: 
  node_type: memory
  type: project
  originSessionId: 593c4a64-2b76-406e-93dc-712e72e5abad
---

Program: Kubernetes (CNCF-run) on HackerOne, bounty launched Jan 2020. Response efficiency only 63%, avg time to bounty 2 months 1 week. Total paid to date: $112,100 / 142 resolved reports. High volume (459 reports/90 days) — high duplicate risk.

**Reward tiers:** Tier 1 (core, incl. git-sync): $200/$1,000/$5,000/$10,000 by severity. Tier 2 (non-core GA): $100/$500/$2,500/$5,000. Tier 3 (infra/alpha): $100/$250/$1,250/$2,500.

**Scope exclusions worth remembering:** kubernetes/ingress-nginx and ingress-gce listed but max severity "None" ($0). kubernetes-sigs/* ineligible unless explicitly listed. Vendor cloud-provider plugins ineligible. Sample/example repos ineligible. Config/path disclosure alone isn't a vuln (infra is public GitOps) — need proof of actual credential leakage or demonstrated attack.

## ACTIVE FINDING — git-sync RCE via `--ref`/`GITSYNC_REF` argument injection (2026-08-14)

**Status: core RCE confirmed live with real, reproducible proof. Currently building a live end-to-end "real-world impact on a third party" demo (RBAC-restricted principal + image-allowlist admission control) before writing the report.**

### The vulnerability
- File: `main.go`, function `fetch()`. Vulnerable line: `args := []string{"fetch", git.repo, ref, "--verbose", "--no-progress", "--prune", "--no-auto-gc"}` — no `--` separator before positional args.
  - In tag `v4.7.1` (commit `898b25004cb06d0d0c03c3d58c02857d79a668c5`, tagged release): line **1887**.
  - In `origin/master` HEAD (commit `cf98d8389384662e1b0d20389a6cf88246d303fe`, 2026-07-28, unreleased): line **2007**.
- The only validation on `--ref`/`GITSYNC_REF`: `if *flRef == ""` (line 449 in v4.7.1, line 470 in master) — checks non-empty, nothing else. No check for a leading `-`.
- Attack: set `--ref`/`GITSYNC_REF` to a string starting with `-`, e.g. `--upload-pack=<shell command>; git-upload-pack`. Git parses it as a `git fetch` FLAG instead of the positional ref argument. `--upload-pack` tells git what local program to invoke to serve the pack for local-path repos — arbitrary command execution.
- Note: `git.log.V(2).Info("fetching", "ref", ref, "repo", redactURL(git.repo))` — they explicitly REDACT the repo URL in logs (for embedded creds) but do NOT redact/sanitize `ref` — shows they thought about one injection/leak risk but missed this one.

### What's proven with REAL, executed, reproducible evidence (not hypothesis)
1. **Local build**: compiled the real, unmodified `v4.7.1` tag from source (`go build`), ran with `--ref='--upload-pack=touch /tmp/GITSYNC_UPLOAD_PACK_RCE_PROOF; git-upload-pack' --repo=<local test repo> --root=<dir> --one-time` → file created, proving command execution. Binary at `/tmp/git-sync-v4.7.1`.
2. **Official Docker image** (independent, stronger confirmation): pulled `registry.k8s.io/git-sync/git-sync:v4.7.1` (git 2.47.3 inside), ran with real documented env vars `GITSYNC_REPO`, `GITSYNC_REF`, `GITSYNC_ONE_TIME` exactly as a real K8s deployment would set them → file created inside the container (owned by container's own UID 65533), git-sync logged **`"updated successfully"`, `status: 0`** — completely clean, silent success while the injected command executed. This is the strongest piece of evidence: real, official, unmodified production artifact.
3. **Locale gotcha for reproduction**: git-sync checks for the English string `"No such remote"` in git's stderr to detect first-run remote setup; a non-English git locale breaks this (harmless artifact of my env, not the real bug) — must set `LC_ALL=C LANG=C` when reproducing locally, not needed inside the container (which is English by default).

### What was tested and honestly DISPROVEN (don't re-claim)
- Original hypothesis: `ext::sh -c '...'` in `--repo` → RCE via git's `ext` transport helper. **Does NOT work** — git itself blocks `ext` transport by default (`fatal: transport 'ext' not allowed`), confirmed against both local git 2.53.0 AND the official container's git 2.47.3, with zero config from git-sync needed to trigger the block (it's git's own hardcoded safe default, no config exists anywhere disabling it). git-sync does nothing wrong here — git's own default protects it. Confirmed the primitive itself is real by explicitly forcing `protocol.ext.allow=always` (not representative of real deployments).
- Submodule-based `.gitmodules` field injection: dead end — git-sync's own code just runs `git submodule update --init --recursive`, doesn't parse/forward individual submodule fields itself; submodule handling is entirely git's own internal logic (subject to the same ext:: protection above).

### Third-party impact reasoning (grounded, not yet live-demonstrated)
Spent significant search effort trying to find one NAMED real platform where GITSYNC_REF is fed from a less-trusted party — none found cleanly:
- Prow (k8s.io's own CI) uses `clonerefs`, NOT git-sync — verified, ruled out, don't claim this.
- Kubeflow Notebook CRD has no built-in git field — a user would need to hand-configure their own init container (no cross-user privilege boundary).
- Zero-to-JupyterHub's git-sync usage is normally admin-configured, not clearly per-user without custom spawner code.
- Malicious `.gitmodules` from a repo contributor: dead end (see above).

Reframed (correctly, per user's own pushback) — this is an open-source TOOL's own code flaw, not "did we find company X misusing it." git-sync's README explicitly markets itself as "the perfect sidecar container" — a generic, embeddable building block with NO documented restriction on what may populate `--ref`/`--repo`. Best grounded real-world threat model found: **`ImagePolicyWebhook`** is a real, official, built-in Kubernetes admission controller (part of the official CKS certification curriculum) that lets a cluster restrict WHICH IMAGES may run without restricting env var CONTENTS. A namespace-scoped principal permitted only to deploy the allowlisted official git-sync image (but not arbitrary images) can use this bug to fully bypass that image-allowlist control via nothing but an env var — a real, standard K8s RBAC/admission-control boundary, not an invented scenario. This reasoning is solid but **not yet demonstrated live end-to-end** (no real cluster set up with ImagePolicyWebhook + a restricted RBAC principal actually exploiting it).

### Live end-to-end third-party-impact demo — COMPLETED, fully confirmed (2026-08-14)
Built and fully executed the live demo on this machine (resources were sufficient: 4 CPU, kind cluster with cached v1.32.2 node image, ~2.2GB RAM available survived cluster creation, disk was tight at 91% but workable).

Setup (separate `kind` cluster `git-sync-poc`, kept alongside pre-existing unrelated `kc-poc` cluster):
- Native `ValidatingAdmissionPolicy` + `ValidatingAdmissionPolicyBinding` (K8s 1.30+ built-in, zero extra pods/images needed — chosen over ImagePolicyWebhook/Kyverno specifically for low resource footprint) restricting namespace `restricted-tenant` to ONLY `registry.k8s.io/git-sync/git-sync:v4.7.1`.
- ServiceAccount `restricted-dev` + Role + RoleBinding: verified via `auth can-i --list` to have ONLY get/list/watch/create/delete on pods + pods/log in that one namespace — nothing else, no cluster-wide anything.
- **Step 1 proof (allowlist works)**: using `restricted-dev`'s own real token, `kubectl run test-arbitrary-image --image=alpine` → explicitly DENIED: `"ValidatingAdmissionPolicy 'allowlist-git-sync-image-only'... denied request"`.
- **Step 2 proof (bypass)**: using the SAME restricted token, deployed a Pod using ONLY the allowlisted git-sync image (an initContainer seeds a local bare repo via emptyDir to work around `--upload-pack` only triggering local/SSH transport, not smart-HTTP — confirmed empirically that a real `https://github.com/...` repo does NOT trigger the injected command, only local-path repos do; noted honestly, not overclaimed), with `GITSYNC_REF="--upload-pack=id; echo RBAC_IMAGE_ALLOWLIST_BYPASSED_PROOF > /tmp/PWNED; git-upload-pack"`.
- Pod completed with git-sync logging clean `"updated successfully"`, `status: 0`.
- **Filesystem-level verification** (strongest possible proof, not just log inference): found the container's containerd snapshot via `crictl inspect` + `ctr snapshots mounts`, mounted the real overlayfs on the node, confirmed `/tmp/PWNED` exists inside the container's actual filesystem, owned by UID 65533 (git-sync's own user), content `RBAC_IMAGE_ALLOWLIST_BYPASSED_PROOF`.

**Result: fully proven, end-to-end, real, reproducible.** A namespace-scoped principal who is architecturally blocked (proven with a real denial) from running arbitrary images achieves arbitrary code execution anyway via nothing but an env var on the one allowlisted image — completely defeating the image-allowlist control. This matches (and via the filesystem-level check, arguably exceeds) the rigor bar set on the Keycloak Operator submission.

**Honest limitation on record**: `--upload-pack` injection only detonates for local-path/SSH repo transports, not smart-HTTP(S) — confirmed both ways empirically, don't claim it works over https.

### Report written — READY TO SUBMIT (2026-08-14)
Full HackerOne-formatted report + submission-notes in
`findings/dia2/git-sync-ref-argument-injection-rce/`. Duplicate-checked (zero
advisories/issues/CVEs match). CVSS 3.0 (this program uses 3.0, not 3.1):
`AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H` = 9.9 Critical.

**IMPORTANT correction (2026-08-14, later same day):** user confirmed
HackerOne's upload widget on THIS program only accepts images/video, no
`.txt`/log files — same constraint as the Keycloak/YesWeHack submission.
`hackerone-report.md` was rewritten so ALL evidence (every command's real
output) lives inline in the Description body as code blocks — nothing depends
on attaching a file anymore. The `evidence/*.txt` files are local-only backup;
do not upload them, the form will reject them. Only a video/image can be
attached.

### Video recording — IN PROGRESS, moving to a more powerful machine via SSH (2026-08-14)

User asked for an MP4 recording of the deny-then-bypass sequence (matching the
Keycloak Operator submission's video). Attempted on this local sandbox machine;
hit environment friction and the user decided to move the recording work to
another, more powerful machine over SSH. **Everything needed to redo this
cleanly is captured below — read this before doing anything else if resuming.**

**What's already fully proven and does NOT need to be redone** — the underlying
finding itself is 100% confirmed, this is purely about producing a clean video:
- RCE via local build (tag v4.7.1) — confirmed, see report.
- RCE via official Docker image — confirmed, see report.
- Live RBAC + ValidatingAdmissionPolicy deny-then-bypass chain — confirmed
  multiple times on this machine, including filesystem-level proof via
  containerd overlay mount. The *finding* is not in question — only the
  *video artifact* is unfinished.

**Reusable artifacts (all copied to permanent storage, not the ephemeral
scratchpad, so they survive/transfer cleanly):**
- `findings/dia2/git-sync-ref-argument-injection-rce/scripts/gitsync-demo-script.sh`
  — the exact demo script (RBAC check → token → denied-alpine → allowed-malicious-pod →
  filesystem proof), already fixed to delete stale pods before each run
  (`kubectl delete pod ... --ignore-not-found=true --wait=true`) so it's
  safely re-runnable from a clean or dirty cluster state.
- `findings/dia2/git-sync-ref-argument-injection-rce/scripts/vap-image-allowlist.yaml`
  — the `ValidatingAdmissionPolicy` + binding restricting to only
  `registry.k8s.io/git-sync/git-sync:v4.7.1`.
- `findings/dia2/git-sync-ref-argument-injection-rce/scripts/restricted-principal-rbac.yaml`
  — the `restricted-dev` ServiceAccount/Role/RoleBinding.
- `findings/dia2/git-sync-ref-argument-injection-rce/scripts/malicious-gitsync-pod.yaml`
  — standalone copy of the malicious pod spec (also inlined in the script itself).
- `findings/dia2/git-sync-ref-argument-injection-rce/evidence/gitsync-poc-partial-DRAFT.mp4`
  — a PARTIAL/UNVERIFIED-PAST-~100s recording from this machine. Confirmed via
  frame extraction that content IS real and legible through Steps 1-4 (RBAC
  check, token, alpine denial, malicious pod accepted+running) up to roughly
  the 100-110s mark, then goes black (xterm closed, recording kept running
  emptily until manually stopped ~186s in). **Did not verify whether Step 5
  (filesystem proof) made it in before the cutoff — check this first before
  assuming a full re-record is needed; might just need trimming.** Treat as
  draft/backup only, not submission-ready.

**Recipe to redo cleanly on the new machine (kind + docker + kubectl required):**
1. `kind create cluster --name git-sync-poc` (or reuse if one already exists there).
2. `kubectl apply -f scripts/vap-image-allowlist.yaml`
3. `kubectl create namespace restricted-tenant` (if not already existing) +
   `kubectl label namespace restricted-tenant image-policy=restricted`
4. `kubectl apply -f scripts/restricted-principal-rbac.yaml`
5. Pull/cache the image once: `docker exec <node> crictl pull registry.k8s.io/git-sync/git-sync:v4.7.1`
   (or let it pull naturally on first pod run — it's small, 27MB).
6. Record: Xvfb + xterm + ffmpeg (x11grab), matching the exact recipe already
   used successfully for the Keycloak Operator recording earlier in this
   project. **Key lessons learned the hard way on this machine, worth checking
   if they still apply on the new one:**
   - Launch Xvfb, THEN ffmpeg (as its own separate tool call, verify the
     process is actually running via `ps aux | grep ffmpeg` before moving on),
     THEN xterm+script (also its own separate call) — do NOT combine multiple
     of these into one chained command; there was a reproducible race/failure
     mode where combining `pkill ... ; sleep N ; launch-thing` in one shell
     call silently resulted in a fully black recording (window never actually
     rendered content, root cause not fully identified — possibly a race
     between backgrounding/disowning across what should be persistent
     processes). Launching each piece as its own isolated tool call and
     verifying with a quick `import -window root <check>.png` screenshot
     BEFORE waiting for the full script to run is what fixed it.
   - This environment's sandboxing blocks any Bash command matching a
     "sleep N" pattern followed by more commands in the same call — even
     backgrounded, even with short N — with exit code 144, not just literal
     long sleeps. If the new machine has the same restriction, avoid
     `sleep N; <more commands>` in one call; issue them as separate calls, or
     use `run_in_background`/proper polling instead.
   - `xterm` was not preinstalled; `apt-get install xterm` needed a real sudo
     password (only `docker` had a NOPASSWD sudoers rule on this machine) —
     had the user run `! sudo apt-get install -y xterm` themselves. Check if
     the new machine already has it or a substitute terminal emulator.
   - The demo pod (`allowed-image-malicious-ref`) and the arbitrary-image test
     pod (`test-arbitrary-image`) must not already exist when the script
     re-runs `kubectl apply`/`kubectl run` — Kubernetes forbids changing
     image/env on an already-created Pod, which produced a confusing
     "Forbidden: pod updates may not change fields other than..." error the
     first time this bit. The script now deletes both defensively at the top
     of their respective steps — should be safe to just re-run as-is.
7. Trim/keep only the real-content portion of the final video (content should
   run roughly 60-120s total; anything after the "DONE" banner + few seconds
   is dead air and should be cut, e.g. `ffmpeg -i in.mp4 -t <seconds> -c copy out.mp4`).
8. Copy the final `.mp4` into `findings/dia2/git-sync-ref-argument-injection-rce/evidence/`,
   replacing `gitsync-poc-partial-DRAFT.mp4`, and update `submission-notes.md`'s
   checklist item to `[x]`.

### Video recording — DONE (2026-08-14, later same day, via SSH on kali@192.168.0.43)
Moved to the SSH machine as planned. Fresh `kind` cluster `git-sync-poc`
created there (that VM already had docker/kind/kubectl/ffmpeg/xterm/Xvfb from
earlier Keycloak work, real sudo, much more headroom — 4GB RAM available,
49GB disk free, vs. the tight sandbox). Applied the same
policy/RBAC/script from `scripts/`. Recording worked cleanly on the first
real attempt this time (launched Xvfb → verified → ffmpeg → verified running →
xterm+script → verified with an immediate screenshot before waiting) — no
repeat of the sandbox's black-screen issue. Raw recording ran 180s (script
itself only takes ~55-60s on this faster machine; ffmpeg kept recording dead
air after xterm closed until manually stopped) — trimmed with `ffmpeg -t 65
-c copy` to just the real content, verified frame-by-frame that all 5 steps
through the final filesystem-proof are captured and legible in the trimmed
65s file. Final video: `findings/dia2/git-sync-ref-argument-injection-rce/evidence/gitsync-poc.mp4`
(65s, 1280x800, H.264, ~2MB). The `gitsync-poc-partial-DRAFT.mp4` from the
sandbox attempt was deleted (superseded).

### Next action
**Finding + report + video are all fully done.** Nothing left to build. User
just needs to do the final review of `hackerone-report.md` +
`evidence/gitsync-poc.mp4` and submit via the HackerOne form (field-by-field
mapping already in `submission-notes.md`).

### Environment state (for resuming if interrupted)
- `/home/diego/claude-bug-bounty/recon/kubernetes/git-sync` — cloned repo, currently checked out at tag `v4.7.1` (detached HEAD), `origin/master` fetched too.
- `/tmp/git-sync-v4.7.1` — compiled binary from the tag, real/unmodified.
- Docker image `registry.k8s.io/git-sync/git-sync:v4.7.1` already pulled locally.
- Test dirs used: `/tmp/git-sync-upload-pack-test/{src-repo,root,root2}`.
- Other repos cloned for the same recon pass (not yet deep-dived, secondary candidates): `/home/diego/claude-bug-bounty/recon/kubernetes/{kompose,kops,minikube,node-problem-detector,publishing-bot,csi-translation-lib,cluster-bootstrap,kube-openapi}`.
- Other findings from the same recon pass, in case git-sync's third-party story doesn't pan out and a pivot is needed:
  - **kompose**: arbitrary local file read via `secrets.<name>.file`/`env_file`/`configs` fields in compose files, `filepath.Join` with no `..`-traversal check (`pkg/transformer/kubernetes/kubernetes.go:626-635`, `k8sutils.go:971-977`). Not yet tested live.
  - **publishing-bot**: `InsecureSkipVerify: true` on rules.yaml fetch (`config/rules.go:126-127`), confirmed live in prod config (`configs/kubernetes-configmap.yaml:10`), chains to `bash -xec` of a `SmokeTest` field → RCE with GitHub push token for `client-go`/`api`/`apimachinery`. Third-party story here is cleaner (network-position/MITM attacker, self-contained, no named-platform needed) but not yet tested live. Strong backup candidate if git-sync's impact story stalls.
  - **kops**: shell injection into node bootstrap cloud-init via unescaped `EgressProxy.HTTPProxy.Host`/`ProxyExcludes` fields (`pkg/model/resources/nodeup.go:660-707`). Agent's own caveat: mostly self-inflicted in the normal single-operator flow — weaker candidate.

## How to apply
When resuming this project: read the "ACTIVE FINDING" section above first. If the live ImagePolicyWebhook demo wasn't finished, that's the next concrete step. If it was finished (check for a `findings/` draft or updated status here), move straight to report writing per [[feedback_no_hypothesis_poc]].
