---
name: project-nanoffmpeg
description: "nano-ffmpeg VDP hunt state — 3 findings ready to submit via Secur0 (2 terminal-escape-injection, 1 ffconcat directive injection), 0/6 historical acceptance rate"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9b76b8f7-973e-4bc0-989b-7b32bc7d0ee0
---

**UPDATE 2026-07-31: all 3 findings are now SUBMITTED (confirmed by user).**

Program: **nano-ffmpeg**, VDP (no bounty) with CVE eligibility + Safe Harbor signed, on the
Secur0 platform. Scope: `github.com/dgr8akki/nano-ffmpeg` (Go TUI app,
`charmbracelet/bubbletea`). As of 2026-07-23: 30 days 5h remaining on the program window, 6
total historical reports / 0 accepted (same caution signal as [[project_gestionominegocio]] —
low acceptance rate, be extra rigorous before submitting).

Local state: `recon/nano-ffmpeg/repo` (cloned repo), **3 findings** fully written and ready:
- `findings/nano-ffmpeg-terminal-escape-injection/` (CWE-150, filename/dirname → terminal
  escape sequences, persists via `~/.config/nano-ffmpeg/config.json` "Recent Files")
- `findings/nano-ffmpeg-metadata-escape-injection/` (CWE-150, same class but via the
  `language` tag of a subtitle track inside `.mkv` — stealthier, MP4/MOV truncates the field
  to 3 bytes so it's MKV-specific)
- `findings/nano-ffmpeg-merge-ffconcat-injection/` (CWE-88, broken `'`-escaping in
  `writeMergeConcatFile()` when building the `.ffconcat` script for the "Merge" operation —
  a filename with an embedded literal newline injects a new `file` directive, forcing
  ffmpeg to splice content from **any other same-directory file** into the merge output,
  bypassing the app's own extension filter. Verified end-to-end against the real installed
  ffmpeg 8.1.2: output had 75 frames instead of the expected 50, with frames 50-74 proven
  (color-coded PoC) to be the non-selected file's content, not the selected clip's. `/` can't
  appear in a single Unix filename component, so this is same-directory-only, not arbitrary
  filesystem path traversal.)

Each has `report_secur0.md` (11-field Secur0 format, CVSS v4.0) + `evidence/` (PoC captures —
`go test` output for the two escape-injection findings; generated `.ffconcat` script +
`ffprobe` frame count + extracted PNG frames for the merge-injection finding).

**Why:** the reports were fully drafted and evidenced in a prior session but never recorded to
memory, so continuity was lost mid-hunt. On 2026-07-23 the user asked to keep hunting rather
than submit immediately, which surfaced the third (merge/ffconcat) finding via code audit +
live verification against the real ffmpeg binary.

**How to apply:** all 3 reports were submitted via Secur0 on 2026-07-23. Next check on resume
is whether Secur0 has triaged/responded to any of them (program has 0/6 historical acceptance,
so don't assume silence means rejection — check status directly).

**Whole-repo sweep completed 2026-07-23** (not just Go source): `.github/workflows/{ci,release}.yml`
(no injection — no `pull_request_target`, no untrusted `${{ github.event.* }}` interpolated
into `run:`, secrets only reach same-repo-branch runs), `.goreleaser.yaml` +
`homebrew/nano-ffmpeg.rb` (standard supply-chain templates, tokens via env, nothing hardcoded),
`website/` (static Next.js marketing site — no API routes, no fetch calls, no dynamic/user
input anywhere, all `target="_blank"` links already have `rel="noopener noreferrer"`),
`go.mod` (standard charmbracelet/cobra ecosystem deps, nothing unusual; the `go-osc52`
dependency is transitive only — the app's own "copy to clipboard" `c` key handler in
settings.go is an unimplemented no-op stub, not a real feature, so no clipboard-write
exploitation path), full git history (`git log --all -p` grepped for secrets/keys/tokens —
none found, only npm lockfile package-name false positives).

**Full source audit completed 2026-07-23** (100% of ~5000 non-test Go lines: main.go,
cmd/root.go, app/, ffmpeg/* — command/runner/config/probe/detect/capabilities/errors/progress
— screens/* — filepicker/settings/home/result/progress/operations — preset.go, ui/*). No
further exploitable issues beyond the 3 reported. Notable disproven hypothesis: thought
`screens/progress.go`'s raw stderr "Live Log" passthrough might extend the metadata-escape
finding to any operation via title/comment tags — verified against real ffmpeg 8.1.2 that
ffmpeg's own human-readable log dump (`dump_format`) already strips control bytes
(ESC/BEL → `?`) before writing to stderr, so that path is NOT exploitable (unlike the ffprobe
JSON path the reported finding uses, which preserves raw bytes). Don't re-investigate this
path unless ffmpeg's dump_format sanitization changes.
