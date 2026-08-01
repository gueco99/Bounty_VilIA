"""
Pending-submission queue — drafted reports waiting for the user's "envia"
confirmation before being submitted to Secur0.

Written by the automated new-program hunt pipeline (see
secur0_watch_and_hunt.sh + tools/secur0_watcher.py). Read back by a later,
possibly separate, conversation when the user confirms a submission, so the
queue must survive across sessions — hence a JSONL file, not in-memory state.
"""

import fcntl
import json
import os
import sys
import uuid
from pathlib import Path

from memory.rotation import DEFAULT_KEEP, DEFAULT_MAX_BYTES, rotate_if_needed
from memory.schemas import (
    make_pending_submission_entry,
    validate_pending_submission_entry,
    SchemaError,
)


class PendingSubmissionsDB:
    """Append-only queue of drafted-but-unsent reports, with status updates."""

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

    def _append_raw(self, entry: dict) -> None:
        line = json.dumps(entry, separators=(",", ":")) + "\n"
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

    def add(self, target: str, finding_title: str, report_path: str, notes: str | None = None) -> dict:
        """Queue a newly-drafted report as pending. Returns the created entry (with its id)."""
        entry = make_pending_submission_entry(
            id=str(uuid.uuid4()),
            target=target,
            finding_title=finding_title,
            report_path=report_path,
            notes=notes,
        )
        self._append_raw(entry)
        return entry

    def _mark(self, entry_id: str, status: str, submitted_at: str | None = None) -> bool:
        """Append a status-update row for entry_id. Readers use the LAST row per id (log-structured update)."""
        entries = self.read_all()
        current = next((e for e in reversed(entries) if e["id"] == entry_id), None)
        if current is None:
            return False
        updated = dict(current)
        updated["status"] = status
        if submitted_at is not None:
            updated["submitted_at"] = submitted_at
        validated = validate_pending_submission_entry(updated)
        self._append_raw(validated)
        return True

    def mark_submitted(self, entry_id: str, submitted_at: str) -> bool:
        return self._mark(entry_id, "submitted", submitted_at=submitted_at)

    def mark_dismissed(self, entry_id: str) -> bool:
        return self._mark(entry_id, "dismissed")

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
                    print(f"WARNING: pending_submissions line {lineno} is corrupted (skipping): {e}", file=sys.stderr)
                    continue

                if validate:
                    try:
                        validate_pending_submission_entry(entry)
                    except SchemaError as e:
                        print(f"WARNING: pending_submissions line {lineno} failed validation (skipping): {e}", file=sys.stderr)
                        continue

                entries.append(entry)

        return entries

    def pending(self) -> list[dict]:
        """Return the current (latest-row-wins per id) set of entries still in 'pending' status."""
        latest_by_id: dict[str, dict] = {}
        for entry in self.read_all():
            latest_by_id[entry["id"]] = entry
        return [e for e in latest_by_id.values() if e["status"] == "pending"]
