#!/usr/bin/env python3
"""
Secur0 new-program watcher.

Polls Secur0's public programs API and reports any program not already in
memory/known_secur0_programs.jsonl. On first run (empty DB), every current
program is recorded as known WITHOUT being reported as "new" (seeding) --
otherwise the very first run would report all 40+ existing programs as new.

API discovered by reading the app's own JS bundle this session (2026-07-30):
  production: https://api.secur0.com/api/programs/list
  staging:    https://preapi.secur0.com/api/programs/list  (test data only,
              use --pre for dry runs so real hunts never fire against it)
Both are public/unauthenticated, paginated (`next`/`previous`/`results`).

Usage:
  python3 tools/secur0_watcher.py                 # check production, report new
  python3 tools/secur0_watcher.py --pre            # check staging instead
  python3 tools/secur0_watcher.py --seed           # force seed-only (no "new" output)
  python3 tools/secur0_watcher.py --db path.jsonl  # override known-programs store path
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory.known_programs_db import KnownProgramsDB
from memory.schemas import make_program_entry

PROD_API_BASE = "https://api.secur0.com/api"
PRE_API_BASE = "https://preapi.secur0.com/api"
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "known_secur0_programs.jsonl"

USER_AGENT = "Mozilla/5.0 (compatible; secur0-watcher/1.0)"


def fetch_all_programs(api_base: str, timeout: int = 20) -> list[dict]:
    """Fetch every program from the paginated /programs/list endpoint."""
    programs = []
    url = f"{api_base}/programs/list"
    seen_urls = set()
    while url:
        if url in seen_urls:
            break  # defensive: avoid an infinite loop if pagination ever cycles
        seen_urls.add(url)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        programs.extend(payload.get("results", []))
        url = payload.get("next")
    return programs


def to_program_entry(raw: dict) -> dict:
    company = raw.get("company") or {}
    return make_program_entry(
        platform="secur0",
        handle=str(raw["program_id"]),
        name=company.get("commercial_name"),
        url=f"https://app.secur0.com/programs/{raw['program_id']}",
        program_type=raw.get("type") if raw.get("type") in ("VDP", "BBP") else None,
        has_cves=raw.get("has_cves"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pre", action="store_true", help="Check the pre.secur0.com staging API instead of production")
    parser.add_argument("--seed", action="store_true", help="Record all current programs as known without reporting any as new (use on first setup)")
    parser.add_argument("--db", type=str, default=str(DEFAULT_DB_PATH), help="Path to the known-programs JSONL store")
    args = parser.parse_args()

    api_base = PRE_API_BASE if args.pre else PROD_API_BASE
    db = KnownProgramsDB(args.db)

    is_first_run = not Path(args.db).exists()

    try:
        raw_programs = fetch_all_programs(api_base)
    except Exception as e:
        print(json.dumps({"error": str(e), "api_base": api_base}), file=sys.stderr)
        return 1

    new_programs = []
    for raw in raw_programs:
        entry = to_program_entry(raw)
        was_new = db.record(entry)
        if was_new and not is_first_run and not args.seed:
            new_programs.append(entry)

    result = {
        "api_base": api_base,
        "checked_at_count": len(raw_programs),
        "first_run_seed": is_first_run or args.seed,
        "new_programs": new_programs,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
