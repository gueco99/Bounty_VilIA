---
name: project-codeweaver
description: "CodeWeaver (github.com/tesserato/CodeWeaver) hunt state — 10 findings drafted in findings/dia3/, all pending submission as of 2026-07-31"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6e44c650-1937-496e-bf7e-7d83940504bd
---

**UPDATE 2026-07-31: all 10 drafted findings are now SUBMITTED (confirmed by user).**

Target: `github.com/tesserato/CodeWeaver` (Go CLI, single 727-line main.go, codebase→Markdown
tool). CVE-eligible VDP, 0 historical reports at start, 30-day window from 2026-07-30.
Pure source-code audit — no live app, single-file scope made exhaustive coverage feasible.

**10 findings drafted in `findings/dia3/`, none yet confirmed submitted:**
1. codeweaver-symlink-arbitrary-file-disclosure — read-side symlink escape, embeds arbitrary
   host files into output (High)
2. codeweaver-write-side-symlink-overwrite — default output filename "codebase.md" follows
   symlinks on write, silently destroys arbitrary files with zero non-default flags (High) —
   arguably the most severe, fires on the tool's single most common invocation
3. codeweaver-ignore-directory-bypass — `-ignore` matching a directory doesn't stop WalkDir
   (returns nil instead of fs.SkipDir), children re-tested independently and can leak (High).
   **Confirmed via git history as a real regression**, not a novel edge case: fixed once
   (2025-05-05, `4eadfab`), broke `-include` a week later, "fixed" by blanket-disabling
   SkipDir (2025-05-12, `8ab28fd` + `0caa650`) instead of scoping it to `-ignore` only —
   reopening the original bug, unpatched since. Independently corroborated by a real user
   (issue #2, "How to exclude node_modules") where even the maintainer's own public suggested
   regex fix doesn't work.
4. codeweaver-filename-markdown-prompt-injection — embedded newlines in filenames inject fake
   headings/links (incl. javascript:) with zero fence protection; also breaks the tree view's
   fixed-length fence via backticks (Medium-High)
5. codeweaver-extension-fence-break-content-hiding — backtick in a file's extension breaks the
   dynamic content fence, swallowing all subsequent files' headers/content into one code
   block; verified against a real goldmark (CommonMark) renderer, not just spec-reading
   (Medium-High)
6. codeweaver-sparse-file-oom-crash — `truncate -s 500G` sparse file (0 real bytes) crashes
   the process instantly via os.ReadFile's size-based pre-allocation; verified a 134-byte
   `tar --sparse` archive reconstitutes the same attack on extraction, no git needed
   (Medium-High)
7. codeweaver-treeview-quadratic-dos — treeBuilder's O(dirs×files) prefix scan; directly
   measured (not extrapolated) 45.6s at N=64000 dirs/files, 502MB — normal repo size
   (Medium-High)
8. codeweaver-terminal-escape-injection — raw ANSI/OSC codes in filenames hit the terminal
   log unfiltered (cursor manipulation, title spoofing, OSC52 clipboard on supporting
   terminals) (Medium)
9. codeweaver-fifo-blocking-read-dos — a mkfifo with no writer hangs the tool forever,
   confirmed via timeout (Medium)
10. codeweaver-world-readable-output-permissions — output + paths-files written 0644
    (hardcoded), readable by any other local user on shared/CI systems; **independently
    corroborated** by an unmerged external security-hardening PR (#12, "S3 — Tighten output
    permissions", proposing 0600) that also independently found findings #1 and #6's root
    causes (S2 symlink guard, S4 size cap) — closed without merging, so all 10 remain live in
    main (Medium-High)

**Key technique that paid off repeatedly this session:** mining the real GitHub issue tracker
and any open/unmerged PRs for the actual target repo, not just reading source. Found finding
#10 this way, plus strong corroborating evidence (git-history regression forensics for #3,
external independent PR audit for #1/#6/#10). Do this early on future source-code-audit VDPs,
not as a last resort.

**Judgment calls made and held under repeated pressure to keep hunting further:** discarded a
paths-file line-injection idea and an RTLO-filename idea as duplicates/no-direct-impact:
correctly resisted a long "sigue buscando" instruction to keep manufacturing findings past
genuine exhaustion. See [[feedback_reproducibility_not_severity]] for the general principle
this session repeatedly applied.

**Status:** all 10 ready; user has not yet confirmed submission to Secur0 as of last check.
Verify actual dashboard state before assuming any are live (per [[feedback_check_dashboard_not_memory]]).
