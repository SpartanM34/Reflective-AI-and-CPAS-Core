"""Local reference store for immutable DKA-E snapshots and events."""

from __future__ import annotations

import contextlib
import copy
import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
from urllib.parse import quote

from .dka import seal_record, validate_record, verify_record_integrity
from .provenance import load_json


class DKAStoreError(RuntimeError):
    pass


class HeadConflict(DKAStoreError):
    pass


class RecordNotFound(DKAStoreError):
    pass


def _component(value: str) -> str:
    if not value or value in {".", ".."}:
        raise ValueError("unsafe empty/dot path component")
    encoded = quote(value, safe="")
    if encoded in {"", ".", ".."}:
        raise ValueError("unsafe path component")
    return encoded


class FileDKAStore:
    """Single-host demonstration store.

    File locks, atomic head replacement, and compare-and-swap avoid ordinary
    local races. This is not a distributed transaction, access-control, backup,
    or encryption implementation.
    """

    persistence_kind = "local-filesystem-reference"

    def __init__(self, root: str | Path):
        self.root = Path(root)
        for child in ("snapshots", "heads", "events", "locks"):
            (self.root / child).mkdir(parents=True, exist_ok=True)

    def _snapshot_path(self, dka_id: str, branch: str, revision: int) -> Path:
        return self.root / "snapshots" / _component(dka_id) / _component(branch) / f"{revision}.json"

    def _head_path(self, dka_id: str, branch: str) -> Path:
        return self.root / "heads" / _component(dka_id) / f"{_component(branch)}.json"

    def _event_path(self, dka_id: str) -> Path:
        return self.root / "events" / f"{_component(dka_id)}.jsonl"

    def _lock_path(self, dka_id: str, branch: str) -> Path:
        return self.root / "locks" / f"{_component(dka_id)}--{_component(branch)}.lock"

    @contextlib.contextmanager
    def _lock(self, dka_id: str, branch: str) -> Iterator[None]:
        lock_path = self._lock_path(dka_id, branch)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary_path = Path(temporary)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _read_head(self, dka_id: str, branch: str) -> dict[str, Any] | None:
        path = self._head_path(dka_id, branch)
        if not path.exists():
            return None
        value = load_json(path)
        if not isinstance(value, dict):
            raise DKAStoreError("head document is not an object")
        return value

    def head(self, dka_id: str, branch: str = "main") -> dict[str, Any] | None:
        return self._read_head(dka_id, branch)

    def put(
        self,
        record: Mapping[str, Any],
        *,
        expected_head: str | None,
        event_type: str = "commit",
        actor: str = "unspecified",
    ) -> dict[str, Any]:
        candidate = copy.deepcopy(dict(record))
        validate_record(candidate)
        if not verify_record_integrity(candidate):
            raise DKAStoreError("record integrity verification failed")
        dka_id = candidate["dka_id"]
        branch = candidate["branch"]
        revision = int(candidate["revision"])

        with self._lock(dka_id, branch):
            current = self._read_head(dka_id, branch)
            actual = current["digest"] if current else None
            if actual != expected_head:
                raise HeadConflict(f"expected head {expected_head!r}, found {actual!r}")
            if current:
                evolution = candidate["evolution"]
                linked = evolution.get("parent_digest") == actual or actual in evolution.get(
                    "merge_parents", []
                )
                if not linked:
                    raise DKAStoreError("new snapshot lineage does not reference the current head")
            snapshot = self._snapshot_path(dka_id, branch, revision)
            if snapshot.exists():
                raise DKAStoreError(f"immutable snapshot already exists: {dka_id}/{branch}/{revision}")
            if current and revision <= int(current["revision"]):
                raise DKAStoreError("new revision must be greater than current head revision")

            self._atomic_json(snapshot, candidate)
            head = {
                "dka_id": dka_id,
                "branch": branch,
                "revision": revision,
                "digest": candidate["integrity"]["digest"],
                "updated_at": candidate["provenance"]["updated_at"],
            }
            self._atomic_json(self._head_path(dka_id, branch), head)
            event = {
                "event_type": event_type,
                "actor": actor,
                "dka_id": dka_id,
                "branch": branch,
                "revision": revision,
                "digest": head["digest"],
                "previous_head": actual,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            event_path = self._event_path(dka_id)
            event_path.parent.mkdir(parents=True, exist_ok=True)
            with event_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return head

    def get(
        self, dka_id: str, branch: str = "main", revision: int | None = None
    ) -> dict[str, Any]:
        if revision is None:
            head = self._read_head(dka_id, branch)
            if head is None:
                raise RecordNotFound(f"no head for {dka_id}/{branch}")
            revision = int(head["revision"])
            expected_digest = head["digest"]
        else:
            expected_digest = None
        path = self._snapshot_path(dka_id, branch, revision)
        if not path.exists():
            raise RecordNotFound(f"no snapshot for {dka_id}/{branch}/{revision}")
        record = load_json(path)
        if not isinstance(record, dict):
            raise DKAStoreError("snapshot is not an object")
        validate_record(record)
        if not verify_record_integrity(record):
            raise DKAStoreError("snapshot digest verification failed")
        if expected_digest and record["integrity"]["digest"] != expected_digest:
            raise DKAStoreError("head digest does not match snapshot")
        return record

    def history(self, dka_id: str, branch: str = "main") -> list[dict[str, Any]]:
        directory = self.root / "snapshots" / _component(dka_id) / _component(branch)
        if not directory.exists():
            return []
        revisions = sorted(int(path.stem) for path in directory.glob("*.json") if path.stem.isdigit())
        return [self.get(dka_id, branch, revision) for revision in revisions]

    def events(self, dka_id: str) -> list[dict[str, Any]]:
        path = self._event_path(dka_id)
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise DKAStoreError("event is not an object")
            events.append(value)
        return events

    def branch(
        self,
        dka_id: str,
        *,
        source_branch: str,
        target_branch: str,
        actor: str,
        updated_at: str,
    ) -> dict[str, Any]:
        if self.head(dka_id, target_branch) is not None:
            raise HeadConflict(f"target branch already exists: {target_branch}")
        source = self.get(dka_id, source_branch)
        branched = copy.deepcopy(source)
        branched["branch"] = target_branch
        branched["revision"] = 1
        branched["evolution"] = {
            "parent_digest": source["integrity"]["digest"],
            "merge_parents": [],
            "change_summary": f"branched from {source_branch} by {actor}",
        }
        branched["provenance"]["updated_at"] = updated_at
        branched["provenance"]["transformations"] = list(
            branched["provenance"].get("transformations", [])
        ) + [f"branch created by {actor}"]
        branched = seal_record(branched)
        return self.put(branched, expected_head=None, event_type="branch", actor=actor)
