# Claude Code auto-memory backup

This folder is a snapshot of this project's Claude Code auto-memory
(`~/.claude/projects/<project-slug>/memory/`) — active hunt states, feedback learned from past
sessions, and reference pointers accumulated across many bug bounty engagements.

**This repo must stay private.** These files contain live, undisclosed vulnerability details for
active bug bounty programs. Do not fork, mirror, or make this repository public.

## Restore on a new machine

1. Install Claude Code and clone this repo's parent project as usual.
2. Copy this folder's contents into the Claude Code project-memory directory:

```bash
PROJECT_SLUG=$(echo "$(pwd)" | sed 's/\//-/g')
mkdir -p ~/.claude/projects/"$PROJECT_SLUG"/memory
cp -r claude-auto-memory/* ~/.claude/projects/"$PROJECT_SLUG"/memory/
```

3. Open `claude` inside the project directory — memory loads automatically from `MEMORY.md`.

## Keeping it in sync

This is a manual snapshot, not a live sync — re-copy and commit whenever you want to push the
latest memory state here.
