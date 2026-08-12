"""Local reference store for immutable DKA-E snapshots and events."""

from __future__ import annotations

import contextlib
import copy
import fcntl
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol, runtime_checkable
from urllib.parse import quote

from .dka import dka_digest_spec, seal_record, validate_record, verify_record_integrity
from .provenance import LEGACY_DIGEST_PROFILE, load_json


class DKAStoreError(RuntimeError):
    """Base store failure with stable machine-facing classification."""

    code = "store_error"
    retryable = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "retryable": self.retryable,
        }


class HeadConflict(DKAStoreError):
    code = "head_conflict"


class RecordNotFound(DKAStoreError):
    code = "record_not_found"


class AccessDenied(DKAStoreError):
    code = "access_denied"


class CorruptionDetected(DKAStoreError):
    code = "corruption_detected"


class StoreBusy(DKAStoreError):
    code = "store_busy"
    retryable = True


class ProfileViolation(DKAStoreError):
    code = "profile_violation"


class RecoveryError(DKAStoreError):
    code = "recovery_error"


@dataclass(frozen=True)
class StoreContext:
    """Host-asserted request identity and authorization decision.

    ``authentication_ref`` and ``authorization_ref`` are audit references, not
    credentials and not cryptographic proof. A production host is responsible
    for authenticating the principal and constructing this object only after a
    policy decision. Store adapters enforce the resulting permissions.
    """

    tenant_id: str
    principal_id: str
    permissions: frozenset[str]
    authentication_ref: str
    authorization_ref: str
    request_id: str
    purpose: str = "unspecified"

    def __post_init__(self) -> None:
        maximum_lengths = {
            "tenant_id": 128,
            "principal_id": 256,
            "authentication_ref": 512,
            "authorization_ref": 512,
            "request_id": 256,
            "purpose": 512,
        }
        for field_name in (
            "tenant_id",
            "principal_id",
            "authentication_ref",
            "authorization_ref",
            "request_id",
            "purpose",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
            if len(value) > maximum_lengths[field_name]:
                raise ValueError(
                    f"{field_name} must be at most {maximum_lengths[field_name]} characters"
                )
            if any(ord(character) < 32 for character in value):
                raise ValueError(f"{field_name} must not contain control characters")
        if isinstance(self.permissions, (str, bytes)):
            raise ValueError("permissions must be a collection of permission strings")
        object.__setattr__(self, "permissions", frozenset(self.permissions))
        if len(self.permissions) > 64 or not all(
            isinstance(item, str)
            and item
            and len(item) <= 128
            and not any(ord(character) < 32 for character in item)
            for item in self.permissions
        ):
            raise ValueError(
                "permissions must contain at most 64 non-empty strings of at most 128 characters"
            )

    def allows(self, permission: str) -> bool:
        return permission in self.permissions or "dka:*" in self.permissions


@runtime_checkable
class DKAStore(Protocol):
    """Normative DKA-E store surface implemented by reference adapters."""

    persistence_kind: str

    def head(
        self,
        dka_id: str,
        branch: str = "main",
        *,
        context: StoreContext | None = None,
    ) -> dict[str, Any] | None: ...

    def put(
        self,
        record: Mapping[str, Any],
        *,
        expected_head: str | None,
        expected_head_profile: str | None = None,
        event_type: str = "commit",
        actor: str = "unspecified",
        context: StoreContext | None = None,
    ) -> dict[str, Any]: ...

    def get(
        self,
        dka_id: str,
        branch: str = "main",
        revision: int | None = None,
        *,
        context: StoreContext | None = None,
    ) -> dict[str, Any]: ...

    def history(
        self,
        dka_id: str,
        branch: str = "main",
        *,
        context: StoreContext | None = None,
    ) -> list[dict[str, Any]]: ...

    def events(
        self,
        dka_id: str,
        *,
        context: StoreContext | None = None,
    ) -> list[dict[str, Any]]: ...

    def branch(
        self,
        dka_id: str,
        *,
        source_branch: str,
        target_branch: str,
        actor: str,
        updated_at: str,
        context: StoreContext | None = None,
    ) -> dict[str, Any]: ...


def assert_lineage(
    candidate: Mapping[str, Any], current: Mapping[str, Any] | None
) -> None:
    """Validate revision and digest/profile linkage against a branch head."""

    if current is None:
        return
    actual = current["digest"]
    current_profile = current.get("digest_profile", LEGACY_DIGEST_PROFILE)
    evolution = candidate["evolution"]
    linked = False
    if evolution.get("parent_digest") == actual:
        linked = (
            evolution.get("parent_digest_profile", LEGACY_DIGEST_PROFILE)
            == current_profile
        )
    else:
        merge_parents = evolution.get("merge_parents", [])
        if actual in merge_parents:
            position = merge_parents.index(actual)
            merge_profiles = evolution.get("merge_parent_digest_profiles", [])
            if (
                not merge_profiles
                and dka_digest_spec(candidate)[1] == LEGACY_DIGEST_PROFILE
            ):
                merge_profiles = [LEGACY_DIGEST_PROFILE] * len(merge_parents)
            linked = (
                position < len(merge_profiles)
                and merge_profiles[position] == current_profile
            )
    if not linked:
        raise DKAStoreError(
            "new snapshot lineage does not reference the current head tuple"
        )
    if int(candidate["revision"]) <= int(current["revision"]):
        raise DKAStoreError("new revision must be greater than current head revision")


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
    profile_id = "cpas-file-reference-v1"

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

    def head(
        self,
        dka_id: str,
        branch: str = "main",
        *,
        context: StoreContext | None = None,
    ) -> dict[str, Any] | None:
        return self._read_head(dka_id, branch)

    def put(
        self,
        record: Mapping[str, Any],
        *,
        expected_head: str | None,
        expected_head_profile: str | None = None,
        event_type: str = "commit",
        actor: str = "unspecified",
        context: StoreContext | None = None,
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
            actual_profile = (
                current.get("digest_profile", LEGACY_DIGEST_PROFILE)
                if current
                else None
            )
            if actual != expected_head or (
                expected_head_profile is not None
                and actual_profile != expected_head_profile
            ):
                raise HeadConflict(
                    "expected head tuple "
                    f"({expected_head!r}, {expected_head_profile!r}), found "
                    f"({actual!r}, {actual_profile!r})"
                )
            assert_lineage(candidate, current)
            snapshot = self._snapshot_path(dka_id, branch, revision)
            if snapshot.exists():
                raise DKAStoreError(f"immutable snapshot already exists: {dka_id}/{branch}/{revision}")

            self._atomic_json(snapshot, candidate)
            head = {
                "dka_id": dka_id,
                "branch": branch,
                "revision": revision,
                "digest": candidate["integrity"]["digest"],
                "digest_profile": dka_digest_spec(candidate)[1],
                "updated_at": candidate["provenance"]["updated_at"],
            }
            self._atomic_json(self._head_path(dka_id, branch), head)
            event = {
                "event_type": event_type,
                "actor": (
                    context.principal_id
                    if context is not None and actor == "unspecified"
                    else actor
                ),
                "dka_id": dka_id,
                "branch": branch,
                "revision": revision,
                "digest": head["digest"],
                "digest_profile": head["digest_profile"],
                "previous_head": actual,
                "previous_head_digest_profile": (
                    current.get("digest_profile", LEGACY_DIGEST_PROFILE)
                    if current
                    else None
                ),
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
        self,
        dka_id: str,
        branch: str = "main",
        revision: int | None = None,
        *,
        context: StoreContext | None = None,
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

    def history(
        self,
        dka_id: str,
        branch: str = "main",
        *,
        context: StoreContext | None = None,
    ) -> list[dict[str, Any]]:
        directory = self.root / "snapshots" / _component(dka_id) / _component(branch)
        if not directory.exists():
            return []
        revisions = sorted(int(path.stem) for path in directory.glob("*.json") if path.stem.isdigit())
        return [
            self.get(dka_id, branch, revision, context=context)
            for revision in revisions
        ]

    def events(
        self,
        dka_id: str,
        *,
        context: StoreContext | None = None,
    ) -> list[dict[str, Any]]:
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
        context: StoreContext | None = None,
    ) -> dict[str, Any]:
        if self.head(dka_id, target_branch, context=context) is not None:
            raise HeadConflict(f"target branch already exists: {target_branch}")
        source = self.get(dka_id, source_branch, context=context)
        branched = copy.deepcopy(source)
        branched["branch"] = target_branch
        branched["revision"] = 1
        branched["evolution"] = {
            "parent_digest": source["integrity"]["digest"],
            "parent_digest_profile": dka_digest_spec(source)[1],
            "merge_parents": [],
            "merge_parent_digest_profiles": [],
            "change_summary": f"branched from {source_branch} by {actor}",
        }
        branched["provenance"]["updated_at"] = updated_at
        branched["provenance"]["transformations"] = list(
            branched["provenance"].get("transformations", [])
        ) + [f"branch created by {actor}"]
        branched = seal_record(branched)
        return self.put(
            branched,
            expected_head=None,
            event_type="branch",
            actor=actor,
            context=context,
        )
