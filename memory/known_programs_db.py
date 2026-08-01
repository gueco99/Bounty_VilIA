"""
Known-Secur0-programs store — used by tools/secur0_watcher.py to detect
new programs appearing on the platform.

Stored in a JSONL file, one entry per line, same conventions as PatternDB
(fcntl-locked append, size-based rotation, schema_version field).
"""

import fcntl
import json
import os
import sys
from pathlib import Path

from memory.rotation import DEFAULT_KEEP, DEFAULT_MAX_BYTES, rotate_if_needed
from memory.schemas import validate_program_entry, SchemaError


class KnownProgramsDB:
    """Read/write the set of Secur0 programs already seen by the watcher."""

    def __init__(
        self,
        path: str | Path,
        max_bytes: int = DEFAULT_MAX_BYTES,
        keep_backups: int = DEFAULT_KEEP,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.keep_backups = keep_backups
        # Dedup index of (platform, handle) keys, loaded lazily.
        self._known: set[tuple[str, str]] | None = None

    @staticmethod
    def _key(entry: dict) -> tuple[str, str]:
        return (entry.get("platform", ""), entry.get("handle", ""))

    def _load_known(self) -> set[tuple[str, str]]:
        keys: set[tuple[str, str]] = set()
        if not self.path.exists():
            return keys
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                keys.add(self._key(entry))
        return keys

    def is_known(self, platform: str, handle: str) -> bool:
        if self._known is None:
            self._known = self._load_known()
        return (platform, handle) in self._known

    def record(self, entry: dict) -> bool:
        """Validate and append a program entry. Returns True if it was new, False if already known."""
        validated = validate_program_entry(entry)

        if self._known is None:
            self._known = self._load_known()

        key = self._key(validated)
        if key in self._known:
            return False

        line = json.dumps(validated, separators=(",", ":")) + "\n"
        encoded = line.encode("utf-8")

        rotate_if_needed(self.path, max_bytes=self.max_bytes, keep=self.keep_backups)

        fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                written = os.write(fd, encoded)
                if written != len(encoded):
                    raise OSError(f"Partial write: {written}/{len(encoded)} bytes")
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

        self._known.add(key)
        return True

    def read_all(self, *, validate: bool = True) -> list[dict]:
        if not self.path.exists():
            return []

        entries = []
        with open(self.path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"WARNING: known_programs line {lineno} is corrupted (skipping): {e}", file=sys.stderr)
                    continue

                if validate:
                    try:
                        validate_program_entry(entry)
                    except SchemaError as e:
                        print(f"WARNING: known_programs line {lineno} failed validation (skipping): {e}", file=sys.stderr)
                        continue

                entries.append(entry)

        return entries
