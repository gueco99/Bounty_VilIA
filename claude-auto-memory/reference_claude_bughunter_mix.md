---
name: reference_claude_bughunter_mix
description: "elementalsouls/Claude-BugHunter — 74 extra skills mixed into ~/.claude/skills/ alongside this project's own 13, skills-only (no commands)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 168bc3f5-0334-4868-b69d-effcd7969405
---

Installed 2026-08-12 at the user's request ("mix" it in to make a "super Claude"). Reviewed the
repo before installing (cloned to scratch, checked `.claude-plugin` manifest, `install.sh` /
`install-community-skills.sh` for network calls/eval/curl-pipe patterns — none found, all local
file-copy, non-destructive with automatic backup-on-collision — and grepped every skill/command
file for prompt-injection red flags — none found beyond expected legitimate pentest-technique
mentions of exfiltration/OOB).

**What's actually installed**: only the 74 skill directories whose names didn't already exist in
`~/.claude/skills/` (`comm -13` diff), copied directly — not run via their `install.sh`. This
project's own 13 skills (`bb-methodology`, `bug-bounty`, `cicd-security`, `credential-attack`,
`graphql-audit`, `meme-coin-audit`, `mobile-pentest`, `report-writing`, `security-arsenal`,
`triage-validation`, `web2-recon`, `web2-vuln-classes`, `web3-audit`) were left untouched — no
overwrite. **Zero of Claude-BugHunter's 15 commands were installed** — all 15 collide by name
with commands already wired to this project's `tools/*.sh` (scope_checker.py, audit_log.py,
lead_board.py); installing theirs would have silently replaced the project-integrated versions
with generic ones. Documented the full rationale in this project's `CLAUDE.md` under "Extended
attack skills."

**Provenance**: Claude-BugHunter (3.5k★/535 forks) explicitly vendors 8 of its 82 skills from
`shuvonsec/claude-bug-bounty` — the same lineage as the `claude-bug-bounty` project this session
is running in — so this is an additive superset, not a competing/foreign toolset.

**High-value additions for enterprise-perimeter targets** (the specific gap identified this
session, on Repsol's Azure AD/Entra-gated SPAs and F5 BIG-IP APM gateway):
`m365-entra-attack`, `okta-attack`, `vmware-vcenter-attack`, `enterprise-vpn-attack` (covers
Cisco ASA/AnyConnect, FortiGate/FortiOS, Citrix NetScaler/ADC, Palo Alto GlobalProtect, Pulse/
Ivanti Connect Secure, SonicWall, F5 Big-IP — CVE matrix 2018-2026), `hunt-sharepoint`,
`cloud-iam-deep`. Also ~50 individual `hunt-<vulnclass>` skills (finer-grained than this
project's `web2-vuln-classes` bundle) and `apk-redteam-pipeline`/`ios-redteam-pipeline` for
mobile (relevant to the parked Waylet dynamic-analysis lead — see [[project_repsol]]).

**Not installed / left as-is**: the `cbh` Python CLI runner and `engine/` (their `/hunt`
orchestrator internals) — those are a standalone tool requiring separate Python setup, out of
scope for a skills-only mix; can revisit if the slash-command layer is ever wanted despite the
naming collision (would need renaming their commands first).
