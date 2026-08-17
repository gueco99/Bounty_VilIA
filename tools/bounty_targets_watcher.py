#!/usr/bin/env python3
"""
HackerOne / Bugcrowd / YesWeHack new-program + scope-change watcher.

Pulls arkadiyt/bounty-targets-data (hourly-updated public dump, no auth,
no account needed) and reports:
  - brand-new programs (handle not in memory/known_bounty_programs.jsonl)
  - scope changes on already-known programs (in_scope asset_identifier set
    differs from the last recorded hash, tracked in
    memory/program_scope_hashes.json)

Mirrors tools/secur0_watcher.py's pattern; reuses the same
KnownProgramsDB/make_program_entry helpers with platform="hackerone" /
"bugcrowd" / "yeswehack".

Usage:
  python3 tools/bounty_targets_watcher.py                # check all 3, report new + changed
  python3 tools/bounty_targets_watcher.py --platform h1   # h1 | bc | ywh | all (default all)
  python3 tools/bounty_targets_watcher.py --seed          # seed-only, no "new" output
  python3 tools/bounty_targets_watcher.py --json          # machine-readable output
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory.known_programs_db import KnownProgramsDB
from memory.schemas import make_program_entry

DUMP_BASE = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data"
SOURCES = {
    "hackerone": f"{DUMP_BASE}/hackerone_data.json",
    "bugcrowd": f"{DUMP_BASE}/bugcrowd_data.json",
    "yeswehack": f"{DUMP_BASE}/yeswehack_data.json",
}
PLATFORM_ALIASES = {"h1": "hackerone", "bc": "bugcrowd", "ywh": "yeswehack", "all": None}

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "known_bounty_programs.jsonl"
DEFAULT_SCOPE_HASH_PATH = Path(__file__).resolve().parent.parent / "memory" / "program_scope_hashes.json"

USER_AGENT = "Mozilla/5.0 (compatible; bounty-targets-watcher/1.0)"


def fetch_programs(url: str, timeout: int = 30) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def scope_signature(raw: dict) -> str:
    """Stable hash of the in-scope asset set, order-independent."""
    targets = raw.get("targets") or {}
    in_scope = targets.get("in_scope") or []
    identifiers = sorted(
        str(a.get("asset_identifier", "")) for a in in_scope if isinstance(a, dict)
    )
    blob = "\n".join(identifiers).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def compact_summary(raw: dict, platform: str) -> str:
    """One short 'bounty:si scope:N' style string, no extra network calls."""
    targets = raw.get("targets") or {}
    scope_n = len(targets.get("in_scope") or [])
    if platform == "hackerone":
        bounty = raw.get("offers_bounties")
    elif platform == "bugcrowd":
        bounty = bool(raw.get("max_payout"))
    elif platform == "yeswehack":
        bounty = bool(raw.get("max_bounty"))
    else:
        bounty = None
    bounty_s = "si" if bounty else ("no" if bounty is not None else "?")
    return f"bounty:{bounty_s} scope:{scope_n}"


def handle_of(raw: dict, platform: str) -> str:
    if platform == "hackerone":
        return raw.get("handle") or raw.get("url", "").rstrip("/").rsplit("/", 1)[-1]
    if platform == "bugcrowd":
        return raw.get("handle") or raw.get("url", "").rstrip("/").rsplit("/", 1)[-1]
    if platform == "yeswehack":
        return raw.get("slug") or raw.get("handle") or raw.get("url", "").rstrip("/").rsplit("/", 1)[-1]
    return raw.get("handle", "")


def load_scope_hashes(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_scope_hashes(path: Path, hashes: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(hashes, indent=None, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="all", choices=["h1", "bc", "ywh", "all"])
    ap.add_argument("--seed", action="store_true", help="seed-only, suppress new/changed output")
    ap.add_argument("--db", default=str(DEFAULT_DB_PATH))
    ap.add_argument("--scope-hashes", default=str(DEFAULT_SCOPE_HASH_PATH))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    platforms = [PLATFORM_ALIASES[args.platform]] if args.platform != "all" else list(SOURCES.keys())

    db = KnownProgramsDB(args.db)
    scope_hash_path = Path(args.scope_hashes)
    scope_hashes = load_scope_hashes(scope_hash_path)

    new_programs = []
    changed_programs = []

    for platform in platforms:
        try:
            programs = fetch_programs(SOURCES[platform])
        except Exception as e:
            print(f"[!] {platform}: fetch failed: {e}", file=sys.stderr)
            continue

        for raw in programs:
            handle = handle_of(raw, platform)
            if not handle:
                continue
            name = raw.get("name") or handle
            url = raw.get("url")
            sig = scope_signature(raw)
            scope_key = f"{platform}:{handle}"

            is_new = not db.is_known(platform, handle)
            if is_new:
                db.record(make_program_entry(platform=platform, handle=handle, name=name, url=url))
                if not args.seed:
                    new_programs.append({"platform": platform, "handle": handle, "name": name, "url": url, "summary": compact_summary(raw, platform)})
            else:
                prev_sig = scope_hashes.get(scope_key)
                if prev_sig is not None and prev_sig != sig and not args.seed:
                    changed_programs.append({"platform": platform, "handle": handle, "name": name, "url": url})

            scope_hashes[scope_key] = sig

    save_scope_hashes(scope_hash_path, scope_hashes)

    if args.json:
        print(json.dumps({"new": new_programs, "changed": changed_programs}))
    else:
        if args.seed:
            print(f"Seeded. {len(scope_hashes)} programs recorded, no alerts on first run.")
        else:
            for p in new_programs:
                print(f"[NEW] {p['platform']} {p['name']} ({p['handle']}) {p.get('summary','')} -> \"caza {p['handle']}\"")
            for p in changed_programs:
                print(f"[SCOPE CHANGE] {p['platform']} {p['name']} ({p['handle']}) -> \"caza {p['handle']}\"")
            if not new_programs and not changed_programs:
                print("No new programs or scope changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
