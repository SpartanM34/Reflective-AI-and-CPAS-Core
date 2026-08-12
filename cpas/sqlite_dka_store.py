"""SQLite rollback-journal profile for externally persistent DKA-E state.

This adapter is intentionally scoped to a local filesystem on one host with
low or moderate writer concurrency. It is not a distributed database, an
authenticator, an encryption system, or deployment certification.
"""

from __future__ import annotations

import contextlib
import copy
import os
import sqlite3
import stat
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from .dka import dka_digest_spec, seal_record, validate_record, verify_record_integrity
from .dka_store import (
    AccessDenied,
    CorruptionDetected,
    DKAStoreError,
    HeadConflict,
    ProfileViolation,
    RecordNotFound,
    RecoveryError,
    StoreBusy,
    StoreContext,
    assert_lineage,
)
from .provenance import (
    DKA_STORE_EVENT_DIGEST_PROFILE,
    JCS_CANONICALIZATION,
    LEGACY_DIGEST_PROFILE,
    canonicalize_json,
    file_sha256,
    loads_json,
    profiled_digest,
    without_paths,
)


PROFILE_ID = "cpas-sqlite-rollback-single-host-v1"
PROFILE_VERSION = "1.0.0"
SCHEMA_VERSION = "1"
MINIMUM_SQLITE = (3, 31, 0)

READ = "dka:read"
READ_SENSITIVE = "dka:read:sensitive"
WRITE = "dka:write"
WRITE_SENSITIVE = "dka:write:sensitive"
BRANCH = "dka:branch"
MERGE = "dka:merge"
LIFECYCLE = "dka:lifecycle"
AUDIT = "dka:audit"
VERIFY = "dka:verify"
BACKUP = "dka:backup"
RESTORE = "dka:restore"
RETENTION = "dka:retention"
MIGRATE = "dka:migrate"

_SENSITIVE_CLASSIFICATIONS = {"confidential", "restricted"}
_PUT_EVENT_TYPES = {
    "commit",
    "branch",
    "merge",
    "invalidation",
    "supersede",
    "migration",
}
_ADMIN_EVENT_TYPES = {"backup", "restore", "purge"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_identifier(value: str, *, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError(f"{name} must be a non-empty string of at most 128 characters")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{name} must not contain control characters")
    return value


def _event_digest(event: Mapping[str, Any]) -> str:
    return profiled_digest(
        without_paths(dict(event), [("integrity", "digest")]),
        canonicalization=JCS_CANONICALIZATION,
        digest_profile=DKA_STORE_EVENT_DIGEST_PROFILE,
        expected_v2_profile=DKA_STORE_EVENT_DIGEST_PROFILE,
    )


class SQLiteDKAStore:
    """Production-oriented, single-host SQLite DKA-E store profile.

    The caller must affirm that the database is on a local filesystem. One
    database file is permanently bound to one tenant. Authentication happens
    outside this adapter; each operation requires the host's ``StoreContext``
    and the adapter enforces its declared permissions.
    """

    persistence_kind = "externally-persisted-cpas-state"
    profile_id = PROFILE_ID

    def __init__(
        self,
        path: str | Path,
        *,
        tenant_id: str,
        local_filesystem: bool,
        busy_timeout_ms: int = 5_000,
    ):
        if os.name != "posix":
            raise ProfileViolation(
                f"{PROFILE_ID} v1 is defined only for POSIX file semantics"
            )
        if sqlite3.sqlite_version_info < MINIMUM_SQLITE:
            required = ".".join(map(str, MINIMUM_SQLITE))
            raise ProfileViolation(
                f"{PROFILE_ID} requires SQLite >= {required}; found {sqlite3.sqlite_version}"
            )
        if not local_filesystem:
            raise ProfileViolation(
                f"{PROFILE_ID} forbids network/shared-filesystem database paths"
            )
        if not isinstance(busy_timeout_ms, int) or busy_timeout_ms < 0:
            raise ValueError("busy_timeout_ms must be a non-negative integer")
        self.path = Path(path)
        self.tenant_id = _safe_identifier(tenant_id, name="tenant_id")
        self.busy_timeout_ms = busy_timeout_ms
        is_empty = self._prepare_database_file(self.path)
        self._file_identity = self._path_identity(self.path)
        if is_empty:
            self._initialize()
        else:
            self._validate_binding()

    @staticmethod
    def _path_identity(path: Path) -> tuple[int, int]:
        file_stat = path.lstat()
        if not stat.S_ISREG(file_stat.st_mode):
            raise ProfileViolation("database path must be a regular, non-symbolic file")
        return file_stat.st_dev, file_stat.st_ino

    def _assert_bound_path(self) -> None:
        if not self.path.exists() and not self.path.is_symlink():
            raise ProfileViolation("bound database path no longer exists")
        self._prepare_database_file(self.path)
        if self._path_identity(self.path) != self._file_identity:
            raise ProfileViolation(
                "database file identity changed after profile binding; reopen only "
                "through a reviewed promotion/restart"
            )

    @staticmethod
    def _prepare_database_file(path: Path) -> bool:
        if path.parent.exists() and path.parent.is_symlink():
            raise ProfileViolation("database parent directory must not be a symbolic link")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        parent_stat = path.parent.stat()
        parent_mode = parent_stat.st_mode & 0o777
        if parent_mode != 0o700:
            raise ProfileViolation(
                "database parent permissions must be exactly 700; "
                f"found {parent_mode:03o}"
            )
        if parent_stat.st_uid != os.geteuid():
            raise ProfileViolation("database parent must be owned by the service account")
        if path.exists() and path.is_symlink():
            raise ProfileViolation("database path must not be a symbolic link")
        if not path.exists():
            descriptor = os.open(
                path,
                os.O_CREAT
                | os.O_EXCL
                | os.O_RDWR
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            os.close(descriptor)
        file_stat = path.lstat()
        if not stat.S_ISREG(file_stat.st_mode):
            raise ProfileViolation("database path must be a regular file")
        if file_stat.st_nlink != 1:
            raise ProfileViolation("database file must have exactly one hard link")
        if file_stat.st_uid != os.geteuid():
            raise ProfileViolation("database file must be owned by the service account")
        mode = file_stat.st_mode & 0o777
        if mode != 0o600:
            raise ProfileViolation(
                f"database file permissions must be exactly 600; found {mode:03o}"
            )
        return path.stat().st_size == 0

    @classmethod
    def _temporary_destination(cls, target: Path) -> Path:
        if target.exists() or target.is_symlink():
            raise RecoveryError("destination must not already exist")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.cpas-",
            dir=target.parent,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        os.chmod(temporary, 0o600)
        cls._prepare_database_file(temporary)
        return temporary

    @staticmethod
    def _publish_new_file(temporary: Path, target: Path) -> None:
        """Publish without overwriting a path created by a concurrent actor."""

        try:
            os.link(temporary, target, follow_symlinks=False)
        except FileExistsError as exc:
            raise RecoveryError("destination appeared during publication") from exc
        except OSError as exc:
            raise RecoveryError(f"could not publish verified database: {exc}") from exc
        try:
            temporary.unlink()
        except OSError as exc:
            try:
                target.unlink()
            except OSError as rollback_exc:
                raise RecoveryError(
                    "verified destination was linked but neither temporary-name "
                    "cleanup nor publication rollback completed"
                ) from rollback_exc
            raise RecoveryError(
                "publication was rolled back because temporary-name cleanup failed"
            ) from exc
        try:
            directory_descriptor = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError as exc:
            raise RecoveryError(
                f"verified destination exists at {target}, but directory sync failed"
            ) from exc

    def _connect(self, *, query_only: bool = False) -> sqlite3.Connection:
        self._assert_bound_path()
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                self.path,
                timeout=self.busy_timeout_ms / 1000,
                isolation_level=None,
            )
            connection.row_factory = sqlite3.Row
            connection.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("PRAGMA secure_delete=ON")
            connection.execute("PRAGMA temp_store=MEMORY")
            connection.execute("PRAGMA synchronous=EXTRA")
            if query_only:
                connection.execute("PRAGMA query_only=ON")
            self._assert_bound_path()
            return connection
        except sqlite3.Error as exc:
            if connection is not None:
                connection.close()
            raise self._translate_error(exc) from exc
        except Exception:
            if connection is not None:
                connection.close()
            raise

    @staticmethod
    def _translate_error(exc: sqlite3.Error) -> DKAStoreError:
        name = getattr(exc, "sqlite_errorname", "")
        if name.startswith("SQLITE_BUSY") or name.startswith("SQLITE_LOCKED"):
            return StoreBusy(str(exc))
        if name.startswith("SQLITE_CORRUPT") or name == "SQLITE_NOTADB":
            return CorruptionDetected(str(exc))
        return DKAStoreError(f"SQLite backend failure ({name or 'unknown'}): {exc}")

    @contextlib.contextmanager
    def _write_transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except sqlite3.Error as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise self._translate_error(exc) from exc
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            journal_mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
            if str(journal_mode).lower() != "delete":
                raise ProfileViolation("SQLite refused required DELETE journal mode")
            values = {
                "profile_id": PROFILE_ID,
                "profile_version": PROFILE_VERSION,
                "schema_version": SCHEMA_VERSION,
                "tenant_id": self.tenant_id,
                "created_at": _utc_now(),
            }
            connection.execute("BEGIN IMMEDIATE")
            for statement in (
                """
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """,
                """
                CREATE TABLE snapshots (
                    tenant_id TEXT NOT NULL,
                    dka_id TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    digest TEXT NOT NULL,
                    digest_profile TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, dka_id, branch, revision)
                )
                """,
                """
                CREATE INDEX snapshots_digest
                    ON snapshots (tenant_id, digest_profile, digest)
                """,
                """
                CREATE TABLE heads (
                    tenant_id TEXT NOT NULL,
                    dka_id TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    digest TEXT NOT NULL,
                    digest_profile TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, dka_id, branch),
                    FOREIGN KEY (tenant_id, dka_id, branch, revision)
                        REFERENCES snapshots (tenant_id, dka_id, branch, revision)
                )
                """,
                """
                CREATE TABLE audit_events (
                    sequence INTEGER PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    dka_id TEXT,
                    event_type TEXT NOT NULL,
                    event_digest TEXT NOT NULL UNIQUE,
                    previous_event_digest TEXT,
                    recorded_at TEXT NOT NULL,
                    event_json TEXT NOT NULL
                )
                """,
                """
                CREATE INDEX audit_events_dka
                    ON audit_events (tenant_id, dka_id, sequence)
                """,
                """
                CREATE TABLE tombstones (
                    tenant_id TEXT NOT NULL,
                    dka_id TEXT NOT NULL,
                    deleted_at TEXT NOT NULL,
                    deleted_by TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, dka_id)
                )
                """,
            ):
                connection.execute(statement)
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)", values.items()
            )
            connection.execute("PRAGMA user_version=1")
            connection.execute("COMMIT")
        except sqlite3.Error as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise self._translate_error(exc) from exc
        finally:
            connection.close()

    def _metadata(self, connection: sqlite3.Connection) -> dict[str, str]:
        try:
            return {
                str(row["key"]): str(row["value"])
                for row in connection.execute("SELECT key, value FROM metadata")
            }
        except sqlite3.Error as exc:
            raise self._translate_error(exc) from exc

    def _validate_binding(self) -> None:
        connection = self._connect(query_only=True)
        try:
            metadata = self._metadata(connection)
            expected = {
                "profile_id": PROFILE_ID,
                "profile_version": PROFILE_VERSION,
                "schema_version": SCHEMA_VERSION,
                "tenant_id": self.tenant_id,
            }
            for key, value in expected.items():
                if metadata.get(key) != value:
                    raise ProfileViolation(
                        f"database {key} mismatch: expected {value!r}, found {metadata.get(key)!r}"
                    )
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
            if journal_mode.lower() != "delete":
                raise ProfileViolation(
                    f"{PROFILE_ID} requires DELETE journal mode, found {journal_mode}"
                )
        finally:
            connection.close()

    def _require(self, context: StoreContext | None, permission: str) -> StoreContext:
        if context is None:
            raise AccessDenied("production store operations require StoreContext")
        if context.tenant_id != self.tenant_id:
            raise AccessDenied("request tenant does not match database tenant binding")
        if not context.allows(permission):
            raise AccessDenied(f"permission required: {permission}")
        return context

    @staticmethod
    def _classification(record: Mapping[str, Any]) -> str:
        return str(record.get("access", {}).get("classification", "restricted"))

    def _authorize_record(
        self, context: StoreContext, record: Mapping[str, Any], *, operation: str
    ) -> None:
        classification = self._classification(record)
        self._authorize_classification(context, classification, operation=operation)

    @staticmethod
    def _authorize_classification(
        context: StoreContext, classification: str, *, operation: str
    ) -> None:
        if classification not in _SENSITIVE_CLASSIFICATIONS:
            return
        permission = READ_SENSITIVE if operation == "read" else WRITE_SENSITIVE
        if not context.allows(permission):
            raise AccessDenied(
                f"{classification} record requires permission: {permission}"
            )

    @staticmethod
    def _head_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "dka_id": row["dka_id"],
            "branch": row["branch"],
            "revision": int(row["revision"]),
            "digest": row["digest"],
            "digest_profile": row["digest_profile"],
            "updated_at": row["updated_at"],
        }

    def _read_head(
        self, connection: sqlite3.Connection, dka_id: str, branch: str
    ) -> dict[str, Any] | None:
        row = connection.execute(
            """
            SELECT dka_id, branch, revision, digest, digest_profile, updated_at
            FROM heads WHERE tenant_id=? AND dka_id=? AND branch=?
            """,
            (self.tenant_id, dka_id, branch),
        ).fetchone()
        return self._head_from_row(row)

    def head(
        self,
        dka_id: str,
        branch: str = "main",
        *,
        context: StoreContext | None = None,
    ) -> dict[str, Any] | None:
        request = self._require(context, READ)
        _safe_identifier(dka_id, name="dka_id")
        _safe_identifier(branch, name="branch")
        connection = self._connect(query_only=True)
        try:
            head = self._read_head(connection, dka_id, branch)
            if head is None:
                return None
            row = connection.execute(
                """
                SELECT dka_id, branch, revision, digest, digest_profile,
                       classification, updated_at, payload_json
                FROM snapshots
                WHERE tenant_id=? AND dka_id=? AND branch=? AND revision=?
                """,
                (self.tenant_id, dka_id, branch, head["revision"]),
            ).fetchone()
            if row is None:
                raise CorruptionDetected("head references a missing snapshot")
            self._authorize_classification(
                request, str(row["classification"]), operation="read"
            )
            record = self._decode_record(row)
            if (
                record["integrity"]["digest"] != head["digest"]
                or dka_digest_spec(record)[1] != head["digest_profile"]
                or record["provenance"]["updated_at"] != head["updated_at"]
            ):
                raise CorruptionDetected("head tuple does not match its snapshot")
            return head
        except sqlite3.Error as exc:
            raise self._translate_error(exc) from exc
        finally:
            connection.close()

    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        context: StoreContext,
        event_type: str,
        dka_id: str | None,
        branch: str | None,
        result_head: Mapping[str, Any] | None,
        previous_head: Mapping[str, Any] | None,
        detail: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        last = connection.execute(
            "SELECT sequence, event_digest FROM audit_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        sequence = int(last["sequence"]) + 1 if last else 1
        previous_event_digest = str(last["event_digest"]) if last else None
        recorded_at = _utc_now()
        event: dict[str, Any] = {
            "event_version": "1.0",
            "event_id": str(uuid.uuid4()),
            "sequence": sequence,
            "profile_id": PROFILE_ID,
            "tenant_id": self.tenant_id,
            "event_type": event_type,
            "actor": {
                "principal_id": context.principal_id,
                "authentication_ref": context.authentication_ref,
                "authorization_ref": context.authorization_ref,
            },
            "request": {
                "request_id": context.request_id,
                "purpose": context.purpose,
            },
            "dka_ref": (
                {"dka_id": dka_id, "branch": branch}
                if dka_id is not None
                else None
            ),
            "previous_head": dict(previous_head) if previous_head else None,
            "result_head": dict(result_head) if result_head else None,
            "detail": dict(detail or {}),
            "recorded_at": recorded_at,
            "previous_event_digest": previous_event_digest,
            "integrity": {
                "canonicalization": JCS_CANONICALIZATION,
                "digest_profile": DKA_STORE_EVENT_DIGEST_PROFILE,
            },
        }
        event["integrity"]["digest"] = _event_digest(event)
        serialized = canonicalize_json(event, profile=JCS_CANONICALIZATION).decode("utf-8")
        connection.execute(
            """
            INSERT INTO audit_events(
                sequence, tenant_id, dka_id, event_type, event_digest,
                previous_event_digest, recorded_at, event_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sequence,
                self.tenant_id,
                dka_id,
                event_type,
                event["integrity"]["digest"],
                previous_event_digest,
                recorded_at,
                serialized,
            ),
        )
        return event

    def _assert_parents_exist(
        self, connection: sqlite3.Connection, candidate: Mapping[str, Any]
    ) -> None:
        evolution = candidate["evolution"]
        references: list[tuple[str, str, str]] = []
        parent_digest = evolution.get("parent_digest")
        if parent_digest:
            references.append(
                (
                    "parent",
                    parent_digest,
                    evolution.get("parent_digest_profile", LEGACY_DIGEST_PROFILE),
                )
            )
        merge_digests = evolution.get("merge_parents", [])
        merge_profiles = evolution.get("merge_parent_digest_profiles", [])
        if not merge_profiles and dka_digest_spec(candidate)[1] == LEGACY_DIGEST_PROFILE:
            merge_profiles = [LEGACY_DIGEST_PROFILE] * len(merge_digests)
        references.extend(
            ("merge parent", digest, merge_profiles[index])
            for index, digest in enumerate(merge_digests)
        )
        for kind, digest, profile in references:
            row = connection.execute(
                """
                SELECT 1 FROM snapshots
                WHERE tenant_id=? AND dka_id=? AND digest=? AND digest_profile=?
                LIMIT 1
                """,
                (self.tenant_id, candidate["dka_id"], digest, profile),
            ).fetchone()
            if row is None:
                raise ProfileViolation(
                    f"{kind} tuple ({digest!r}, {profile!r}) does not resolve in this tenant/DKA"
                )

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
        request = self._require(context, WRITE)
        if event_type not in _PUT_EVENT_TYPES:
            raise ProfileViolation(
                f"put event_type must be one of {sorted(_PUT_EVENT_TYPES)!r}"
            )
        if event_type == "migration":
            self._require(request, MIGRATE)
        elif event_type == "branch":
            self._require(request, BRANCH)
        elif event_type == "merge":
            self._require(request, MERGE)
        elif event_type in {"invalidation", "supersede"}:
            self._require(request, LIFECYCLE)
        if actor not in {"unspecified", request.principal_id}:
            raise AccessDenied("event actor must match the authenticated principal context")
        candidate = copy.deepcopy(dict(record))
        validate_record(candidate)
        if not verify_record_integrity(candidate):
            raise CorruptionDetected("record integrity verification failed before commit")
        self._authorize_record(request, candidate, operation="write")
        dka_id = _safe_identifier(candidate["dka_id"], name="dka_id")
        branch = _safe_identifier(candidate["branch"], name="branch")
        revision = int(candidate["revision"])
        digest = candidate["integrity"]["digest"]
        digest_profile = dka_digest_spec(candidate)[1]
        classification = self._classification(candidate)
        serialized = canonicalize_json(
            candidate, profile=candidate["integrity"]["canonicalization"]
        ).decode("utf-8")

        with self._write_transaction() as connection:
            tombstone = connection.execute(
                "SELECT 1 FROM tombstones WHERE tenant_id=? AND dka_id=?",
                (self.tenant_id, dka_id),
            ).fetchone()
            if tombstone:
                raise ProfileViolation(f"DKA has been tombstoned and cannot be recreated: {dka_id}")
            current = self._read_head(connection, dka_id, branch)
            actual = current["digest"] if current else None
            actual_profile = (
                current.get("digest_profile", LEGACY_DIGEST_PROFILE) if current else None
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
            self._assert_parents_exist(connection, candidate)
            merge_parents = candidate["evolution"].get("merge_parents", [])
            parent_digest = candidate["evolution"].get("parent_digest")
            validity_status = candidate["validity"]["status"]
            if event_type == "branch" and (
                current is not None or not parent_digest or merge_parents
            ):
                raise ProfileViolation(
                    "branch events require an absent target head, one parent, and no merge parents"
                )
            if event_type == "merge" and len(merge_parents) != 2:
                raise ProfileViolation("merge events require exactly two merge parents")
            if merge_parents and event_type not in {"merge", "migration"}:
                raise ProfileViolation(
                    "records with merge parents require a merge or migration event"
                )
            if event_type == "invalidation" and validity_status != "invalidated":
                raise ProfileViolation(
                    "invalidation events require validity.status=invalidated"
                )
            if event_type == "supersede" and validity_status != "superseded":
                raise ProfileViolation(
                    "supersede events require validity.status=superseded"
                )
            try:
                connection.execute(
                    """
                    INSERT INTO snapshots(
                        tenant_id, dka_id, branch, revision, digest,
                        digest_profile, classification, updated_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.tenant_id,
                        dka_id,
                        branch,
                        revision,
                        digest,
                        digest_profile,
                        classification,
                        candidate["provenance"]["updated_at"],
                        serialized,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ProfileViolation(
                    f"immutable snapshot already exists or violates storage constraints: "
                    f"{dka_id}/{branch}/{revision}"
                ) from exc
            head = {
                "dka_id": dka_id,
                "branch": branch,
                "revision": revision,
                "digest": digest,
                "digest_profile": digest_profile,
                "updated_at": candidate["provenance"]["updated_at"],
            }
            if current is None:
                connection.execute(
                    """
                    INSERT INTO heads(
                        tenant_id, dka_id, branch, revision, digest,
                        digest_profile, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.tenant_id,
                        dka_id,
                        branch,
                        revision,
                        digest,
                        digest_profile,
                        head["updated_at"],
                    ),
                )
            else:
                changed = connection.execute(
                    """
                    UPDATE heads SET revision=?, digest=?, digest_profile=?, updated_at=?
                    WHERE tenant_id=? AND dka_id=? AND branch=?
                      AND digest=? AND digest_profile=?
                    """,
                    (
                        revision,
                        digest,
                        digest_profile,
                        head["updated_at"],
                        self.tenant_id,
                        dka_id,
                        branch,
                        actual,
                        actual_profile,
                    ),
                ).rowcount
                if changed != 1:
                    raise HeadConflict("branch head changed during compare-and-swap")
            self._append_event(
                connection,
                context=request,
                event_type=event_type,
                dka_id=dka_id,
                branch=branch,
                result_head=head,
                previous_head=current,
            )
            return head

    def _decode_record(self, row: sqlite3.Row) -> dict[str, Any]:
        try:
            record = loads_json(str(row["payload_json"]))
            if not isinstance(record, dict):
                raise TypeError("snapshot payload is not an object")
            validate_record(record)
            if not verify_record_integrity(record):
                raise ValueError("snapshot digest verification failed")
            expected = {
                "dka_id": row["dka_id"],
                "branch": row["branch"],
                "revision": int(row["revision"]),
                "digest": row["digest"],
                "digest_profile": row["digest_profile"],
                "classification": row["classification"],
                "updated_at": row["updated_at"],
            }
            actual = {
                "dka_id": record["dka_id"],
                "branch": record["branch"],
                "revision": int(record["revision"]),
                "digest": record["integrity"]["digest"],
                "digest_profile": dka_digest_spec(record)[1],
                "classification": self._classification(record),
                "updated_at": record["provenance"]["updated_at"],
            }
            if actual != expected:
                raise ValueError(
                    f"snapshot index/payload mismatch: expected {expected!r}, found {actual!r}"
                )
            return record
        except (KeyError, TypeError, ValueError) as exc:
            raise CorruptionDetected(str(exc)) from exc

    def get(
        self,
        dka_id: str,
        branch: str = "main",
        revision: int | None = None,
        *,
        context: StoreContext | None = None,
    ) -> dict[str, Any]:
        request = self._require(context, READ)
        _safe_identifier(dka_id, name="dka_id")
        _safe_identifier(branch, name="branch")
        if revision is not None and (not isinstance(revision, int) or revision < 1):
            raise ValueError("revision must be a positive integer")
        connection = self._connect(query_only=True)
        try:
            selected_revision = revision
            expected_head: dict[str, Any] | None = None
            if selected_revision is None:
                expected_head = self._read_head(connection, dka_id, branch)
                if expected_head is None:
                    raise RecordNotFound(f"no head for {dka_id}/{branch}")
                selected_revision = int(expected_head["revision"])
            row = connection.execute(
                """
                SELECT dka_id, branch, revision, digest, digest_profile,
                       classification, updated_at, payload_json
                FROM snapshots
                WHERE tenant_id=? AND dka_id=? AND branch=? AND revision=?
                """,
                (self.tenant_id, dka_id, branch, selected_revision),
            ).fetchone()
            if row is None:
                raise RecordNotFound(
                    f"no snapshot for {dka_id}/{branch}/{selected_revision}"
                )
            self._authorize_classification(
                request, str(row["classification"]), operation="read"
            )
            record = self._decode_record(row)
            if expected_head and (
                record["integrity"]["digest"] != expected_head["digest"]
                or dka_digest_spec(record)[1] != expected_head["digest_profile"]
            ):
                raise CorruptionDetected("head tuple does not match its snapshot")
            return record
        except sqlite3.Error as exc:
            raise self._translate_error(exc) from exc
        finally:
            connection.close()

    def history(
        self,
        dka_id: str,
        branch: str = "main",
        *,
        context: StoreContext | None = None,
    ) -> list[dict[str, Any]]:
        request = self._require(context, READ)
        _safe_identifier(dka_id, name="dka_id")
        _safe_identifier(branch, name="branch")
        connection = self._connect(query_only=True)
        try:
            rows = connection.execute(
                """
                SELECT dka_id, branch, revision, digest, digest_profile,
                       classification, updated_at, payload_json
                FROM snapshots
                WHERE tenant_id=? AND dka_id=? AND branch=?
                ORDER BY revision
                """,
                (self.tenant_id, dka_id, branch),
            ).fetchall()
            for row in rows:
                self._authorize_classification(
                    request, str(row["classification"]), operation="read"
                )
            return [self._decode_record(row) for row in rows]
        except sqlite3.Error as exc:
            raise self._translate_error(exc) from exc
        finally:
            connection.close()

    def _validate_audit_rows(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        event_ids: set[str] = set()
        previous: str | None = None
        expected_sequence = 1
        for row in rows:
            try:
                event = loads_json(str(row["event_json"]))
                if not isinstance(event, dict):
                    raise TypeError("audit event is not an object")
                if int(row["sequence"]) != expected_sequence:
                    raise ValueError("audit event sequence is not contiguous")
                if event.get("sequence") != expected_sequence:
                    raise ValueError("audit event payload sequence mismatch")
                if event.get("event_version") != "1.0":
                    raise ValueError("audit event version mismatch")
                event_id = str(event.get("event_id", ""))
                parsed_event_id = uuid.UUID(event_id)
                if str(parsed_event_id) != event_id or parsed_event_id.version != 4:
                    raise ValueError("audit event ID is not a canonical UUIDv4")
                if event_id in event_ids:
                    raise ValueError("duplicate audit event ID")
                event_ids.add(event_id)
                if event.get("profile_id") != PROFILE_ID:
                    raise ValueError("audit event profile mismatch")
                if event.get("tenant_id") != self.tenant_id:
                    raise ValueError("audit event tenant mismatch")
                event_type = event.get("event_type")
                if event_type not in _PUT_EVENT_TYPES | _ADMIN_EVENT_TYPES:
                    raise ValueError("audit event type is not permitted by this profile")
                if row["tenant_id"] != self.tenant_id:
                    raise ValueError("audit event index tenant mismatch")
                if row["event_type"] != event_type:
                    raise ValueError("audit event index type mismatch")
                if row["recorded_at"] != event.get("recorded_at"):
                    raise ValueError("audit event index timestamp mismatch")
                recorded_at = datetime.fromisoformat(
                    str(event.get("recorded_at", "")).replace("Z", "+00:00")
                )
                if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
                    raise ValueError("audit event timestamp must include an offset")
                dka_ref = event.get("dka_ref")
                payload_dka_id = dka_ref.get("dka_id") if isinstance(dka_ref, dict) else None
                if row["dka_id"] != payload_dka_id:
                    raise ValueError("audit event index DKA mismatch")
                actor = event.get("actor")
                request = event.get("request")
                if not isinstance(actor, dict) or not all(
                    isinstance(actor.get(key), str) and actor[key]
                    for key in (
                        "principal_id",
                        "authentication_ref",
                        "authorization_ref",
                    )
                ):
                    raise ValueError("audit event actor metadata is incomplete")
                if not isinstance(request, dict) or not all(
                    isinstance(request.get(key), str) and request[key]
                    for key in ("request_id", "purpose")
                ):
                    raise ValueError("audit event request metadata is incomplete")
                if not isinstance(event.get("detail"), dict):
                    raise ValueError("audit event detail must be an object")
                result_head = event.get("result_head")
                if event_type in _PUT_EVENT_TYPES:
                    if not isinstance(dka_ref, dict) or not isinstance(result_head, dict):
                        raise ValueError(
                            "DKA mutation events require DKA and result-head references"
                        )
                    required_head = (
                        "dka_id",
                        "branch",
                        "revision",
                        "digest",
                        "digest_profile",
                        "updated_at",
                    )
                    if not all(key in result_head for key in required_head):
                        raise ValueError("audit result head is incomplete")
                    if (
                        not isinstance(dka_ref.get("dka_id"), str)
                        or not isinstance(dka_ref.get("branch"), str)
                        or not isinstance(result_head.get("revision"), int)
                        or result_head["revision"] < 1
                        or not all(
                            isinstance(result_head.get(key), str)
                            and result_head[key]
                            for key in (
                                "dka_id",
                                "branch",
                                "digest",
                                "digest_profile",
                                "updated_at",
                            )
                        )
                    ):
                        raise ValueError("audit result-head field types are invalid")
                    if (
                        result_head["dka_id"] != dka_ref.get("dka_id")
                        or result_head["branch"] != dka_ref.get("branch")
                    ):
                        raise ValueError("audit result head and DKA reference disagree")
                elif event_type in {"backup", "restore"} and (
                    dka_ref is not None or result_head is not None
                ):
                    raise ValueError(
                        "backup/restore events must not claim a DKA result head"
                    )
                elif event_type == "purge" and (
                    not isinstance(dka_ref, dict)
                    or not isinstance(dka_ref.get("dka_id"), str)
                    or not dka_ref.get("dka_id")
                    or dka_ref.get("branch") is not None
                    or result_head is not None
                ):
                    raise ValueError("purge event reference shape is invalid")
                integrity = event.get("integrity")
                if not isinstance(integrity, dict) or (
                    integrity.get("canonicalization") != JCS_CANONICALIZATION
                    or integrity.get("digest_profile")
                    != DKA_STORE_EVENT_DIGEST_PROFILE
                ):
                    raise ValueError("audit event integrity profile mismatch")
                if event.get("previous_event_digest") != previous:
                    raise ValueError("audit event chain predecessor mismatch")
                digest = event.get("integrity", {}).get("digest")
                if digest != row["event_digest"] or digest != _event_digest(event):
                    raise ValueError("audit event digest mismatch")
                if row["previous_event_digest"] != previous:
                    raise ValueError("audit event index predecessor mismatch")
                events.append(event)
                previous = digest
                expected_sequence += 1
            except (KeyError, TypeError, ValueError) as exc:
                raise CorruptionDetected(str(exc)) from exc
        return events

    def audit_events(
        self,
        *,
        context: StoreContext | None = None,
        dka_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self._require(context, AUDIT)
        connection = self._connect(query_only=True)
        try:
            rows = connection.execute(
                """
                SELECT sequence, tenant_id, dka_id, event_type, event_digest,
                       previous_event_digest, recorded_at, event_json
                FROM audit_events WHERE tenant_id=? ORDER BY sequence
                """,
                (self.tenant_id,),
            ).fetchall()
            events = self._validate_audit_rows(rows)
            if dka_id is None:
                return events
            return [
                event
                for event in events
                if (event.get("dka_ref") or {}).get("dka_id") == dka_id
            ]
        except sqlite3.Error as exc:
            raise self._translate_error(exc) from exc
        finally:
            connection.close()

    def events(
        self,
        dka_id: str,
        *,
        context: StoreContext | None = None,
    ) -> list[dict[str, Any]]:
        _safe_identifier(dka_id, name="dka_id")
        return self.audit_events(context=context, dka_id=dka_id)

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
        request = self._require(context, BRANCH)
        self._require(request, READ)
        self._require(request, WRITE)
        if actor != request.principal_id:
            raise AccessDenied("branch actor must match the authenticated principal context")
        if self.head(dka_id, target_branch, context=request) is not None:
            raise HeadConflict(f"target branch already exists: {target_branch}")
        source = self.get(dka_id, source_branch, context=request)
        self._authorize_record(request, source, operation="write")
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
        return self.put(
            seal_record(branched),
            expected_head=None,
            event_type="branch",
            actor=actor,
            context=request,
        )

    def profile_status(
        self, *, context: StoreContext | None = None
    ) -> dict[str, Any]:
        self._require(context, VERIFY)
        connection = self._connect(query_only=True)
        try:
            metadata = self._metadata(connection)
            file_stat = self.path.lstat()
            parent_stat = self.path.parent.stat()
            status = {
                "profile_id": metadata.get("profile_id"),
                "profile_version": metadata.get("profile_version"),
                "schema_version": metadata.get("schema_version"),
                "tenant_id": metadata.get("tenant_id"),
                "sqlite_version": sqlite3.sqlite_version,
                "journal_mode": str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower(),
                "synchronous": int(connection.execute("PRAGMA synchronous").fetchone()[0]),
                "foreign_keys": bool(connection.execute("PRAGMA foreign_keys").fetchone()[0]),
                "trusted_schema": bool(connection.execute("PRAGMA trusted_schema").fetchone()[0]),
                "secure_delete": bool(connection.execute("PRAGMA secure_delete").fetchone()[0]),
                "file_mode": f"{file_stat.st_mode & 0o777:03o}",
                "parent_mode": f"{parent_stat.st_mode & 0o777:03o}",
                "service_owned": (
                    file_stat.st_uid == os.geteuid()
                    and parent_stat.st_uid == os.geteuid()
                ),
                "hard_links": file_stat.st_nlink,
                "file_identity_bound": (
                    (file_stat.st_dev, file_stat.st_ino) == self._file_identity
                ),
                "deployment_scope": "single-host-local-filesystem",
            }
            status["conformant"] = all(
                (
                    status["profile_id"] == PROFILE_ID,
                    status["profile_version"] == PROFILE_VERSION,
                    status["schema_version"] == SCHEMA_VERSION,
                    status["tenant_id"] == self.tenant_id,
                    status["journal_mode"] == "delete",
                    status["synchronous"] == 3,
                    status["foreign_keys"] is True,
                    status["trusted_schema"] is False,
                    status["secure_delete"] is True,
                    status["file_mode"] == "600",
                    status["parent_mode"] == "700",
                    status["service_owned"] is True,
                    status["hard_links"] == 1,
                    status["file_identity_bound"] is True,
                )
            )
            return status
        finally:
            connection.close()

    def _verify_internal(self) -> dict[str, Any]:
        connection = self._connect(query_only=True)
        try:
            integrity_rows = [
                str(row[0]) for row in connection.execute("PRAGMA integrity_check")
            ]
            if integrity_rows != ["ok"]:
                raise CorruptionDetected("SQLite integrity_check: " + "; ".join(integrity_rows))
            foreign_key_rows = list(connection.execute("PRAGMA foreign_key_check"))
            if foreign_key_rows:
                raise CorruptionDetected("SQLite foreign_key_check reported violations")
            snapshot_rows = connection.execute(
                """
                SELECT dka_id, branch, revision, digest, digest_profile,
                       classification, updated_at, payload_json
                FROM snapshots WHERE tenant_id=?
                ORDER BY dka_id, branch, revision
                """,
                (self.tenant_id,),
            ).fetchall()
            grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
            for row in snapshot_rows:
                record = self._decode_record(row)
                try:
                    self._assert_parents_exist(connection, record)
                except DKAStoreError as exc:
                    raise CorruptionDetected(str(exc)) from exc
                grouped.setdefault((record["dka_id"], record["branch"]), []).append(
                    record
                )
            for key, records in grouped.items():
                records.sort(key=lambda item: int(item["revision"]))
                for previous, candidate in zip(records, records[1:]):
                    previous_head = {
                        "revision": previous["revision"],
                        "digest": previous["integrity"]["digest"],
                        "digest_profile": dka_digest_spec(previous)[1],
                    }
                    try:
                        assert_lineage(candidate, previous_head)
                    except DKAStoreError as exc:
                        raise CorruptionDetected(
                            f"branch lineage failure for {key!r}: {exc}"
                        ) from exc
            head_rows = connection.execute(
                """
                SELECT h.dka_id, h.branch, h.revision, h.digest, h.digest_profile,
                       h.updated_at, s.digest AS snapshot_digest,
                       s.digest_profile AS snapshot_profile,
                       s.updated_at AS snapshot_updated_at
                FROM heads h
                JOIN snapshots s ON s.tenant_id=h.tenant_id AND s.dka_id=h.dka_id
                    AND s.branch=h.branch AND s.revision=h.revision
                WHERE h.tenant_id=?
                """,
                (self.tenant_id,),
            ).fetchall()
            for row in head_rows:
                if (
                    row["digest"] != row["snapshot_digest"]
                    or row["digest_profile"] != row["snapshot_profile"]
                    or row["updated_at"] != row["snapshot_updated_at"]
                ):
                    raise CorruptionDetected("head tuple does not match indexed snapshot")
            indexed_heads = {
                (row["dka_id"], row["branch"]): int(row["revision"])
                for row in head_rows
            }
            latest_revisions = {
                key: int(records[-1]["revision"]) for key, records in grouped.items()
            }
            if indexed_heads != latest_revisions:
                raise CorruptionDetected(
                    "branch heads do not exactly identify every latest snapshot: "
                    f"expected {latest_revisions!r}, found {indexed_heads!r}"
                )
            event_rows = connection.execute(
                """
                SELECT sequence, tenant_id, dka_id, event_type, event_digest,
                       previous_event_digest, recorded_at, event_json
                FROM audit_events WHERE tenant_id=? ORDER BY sequence
                """,
                (self.tenant_id,),
            ).fetchall()
            events = self._validate_audit_rows(event_rows)
            tombstone_rows = connection.execute(
                """
                SELECT dka_id, deleted_at, deleted_by, reason
                FROM tombstones WHERE tenant_id=? ORDER BY dka_id
                """,
                (self.tenant_id,),
            ).fetchall()
            tombstones = {str(row["dka_id"]): row for row in tombstone_rows}
            orphaned = connection.execute(
                """
                SELECT COUNT(*) FROM tombstones t
                WHERE t.tenant_id=? AND EXISTS (
                    SELECT 1 FROM snapshots s
                    WHERE s.tenant_id=t.tenant_id AND s.dka_id=t.dka_id
                )
                """,
                (self.tenant_id,),
            ).fetchone()[0]
            if orphaned:
                raise CorruptionDetected("tombstoned DKAs still have canonical snapshots")
            snapshot_tuples = {
                (
                    record["dka_id"],
                    record["branch"],
                    int(record["revision"]),
                    record["integrity"]["digest"],
                    dka_digest_spec(record)[1],
                )
                for records in grouped.values()
                for record in records
            }
            active_event_tuples: set[tuple[str, str, int, str, str]] = set()
            purge_events: dict[str, dict[str, Any]] = {}
            for event in events:
                event_type = event["event_type"]
                dka_ref = event.get("dka_ref") or {}
                dka_id = dka_ref.get("dka_id")
                if event_type in _PUT_EVENT_TYPES and dka_id not in tombstones:
                    result = event["result_head"]
                    active_event_tuples.add(
                        (
                            result["dka_id"],
                            result["branch"],
                            int(result["revision"]),
                            result["digest"],
                            result["digest_profile"],
                        )
                    )
                elif event_type == "purge":
                    if dka_id in purge_events:
                        raise CorruptionDetected("multiple purge events for one tombstone")
                    purge_events[str(dka_id)] = event
            if active_event_tuples != snapshot_tuples:
                raise CorruptionDetected(
                    "active snapshot/audit result tuples differ: "
                    f"snapshots_only={sorted(snapshot_tuples - active_event_tuples)!r}, "
                    f"events_only={sorted(active_event_tuples - snapshot_tuples)!r}"
                )
            if set(purge_events) != set(tombstones):
                raise CorruptionDetected(
                    "purge events and tombstones do not identify the same DKAs"
                )
            for dka_id, row in tombstones.items():
                event = purge_events[dka_id]
                if (
                    event["detail"].get("deleted_at") != row["deleted_at"]
                    or event["detail"].get("reason") != row["reason"]
                    or event["actor"]["principal_id"] != row["deleted_by"]
                ):
                    raise CorruptionDetected(
                        f"purge event/tombstone metadata mismatch for {dka_id}"
                    )
            return {
                "passed": True,
                "snapshots": len(snapshot_rows),
                "heads": len(head_rows),
                "events": len(event_rows),
                "sqlite_integrity": "ok",
                "foreign_keys": "ok",
                "audit_chain": "ok",
                "snapshot_event_correlation": "ok",
                "tombstones": len(tombstones),
            }
        except sqlite3.Error as exc:
            raise self._translate_error(exc) from exc
        finally:
            connection.close()

    def verify(self, *, context: StoreContext | None = None) -> dict[str, Any]:
        self._require(context, VERIFY)
        report = self._verify_internal()
        report["profile"] = self.profile_status(context=context)
        if not report["profile"]["conformant"]:
            raise ProfileViolation("database settings do not conform to the selected profile")
        return report

    def backup(
        self,
        destination: str | Path,
        *,
        context: StoreContext | None = None,
    ) -> dict[str, Any]:
        request = self._require(context, BACKUP)
        target = Path(destination)
        temporary = self._temporary_destination(target)
        try:
            source = self._connect(query_only=True)
            destination_connection: sqlite3.Connection | None = None
            try:
                destination_connection = sqlite3.connect(
                    temporary, isolation_level=None
                )
                source.backup(destination_connection)
                destination_connection.execute("PRAGMA synchronous=EXTRA")
            except sqlite3.Error as exc:
                raise RecoveryError(str(self._translate_error(exc))) from exc
            finally:
                if destination_connection is not None:
                    destination_connection.close()
                source.close()
            descriptor = os.open(temporary, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            backup_store = SQLiteDKAStore(
                temporary,
                tenant_id=self.tenant_id,
                local_filesystem=True,
                busy_timeout_ms=self.busy_timeout_ms,
            )
            verification = backup_store._verify_internal()
            digest = file_sha256(temporary)
            self._publish_new_file(temporary, target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        try:
            with self._write_transaction() as connection:
                self._append_event(
                    connection,
                    context=request,
                    event_type="backup",
                    dka_id=None,
                    branch=None,
                    result_head=None,
                    previous_head=None,
                    detail={"backup_digest": digest, "verification": "passed"},
                )
        except DKAStoreError as exc:
            raise RecoveryError(
                f"backup was published and verified at {target}, but its live-store "
                "audit event failed: {exc}"
            ) from exc
        return {
            "profile_id": PROFILE_ID,
            "tenant_id": self.tenant_id,
            "backup_digest": digest,
            "verification": verification,
            "encryption": "external-control-required",
        }

    @classmethod
    def restore_copy(
        cls,
        backup_path: str | Path,
        destination: str | Path,
        *,
        tenant_id: str,
        local_filesystem: bool,
        context: StoreContext,
        busy_timeout_ms: int = 5_000,
    ) -> "SQLiteDKAStore":
        if context.tenant_id != tenant_id or not context.allows(RESTORE):
            raise AccessDenied("restore requires matching tenant and dka:restore")
        source_path = Path(backup_path)
        target = Path(destination)
        if not source_path.is_file():
            raise RecoveryError("backup source does not exist")
        source_store = cls(
            source_path,
            tenant_id=tenant_id,
            local_filesystem=local_filesystem,
            busy_timeout_ms=busy_timeout_ms,
        )
        source_store._verify_internal()
        source_digest = file_sha256(source_path)
        temporary = cls._temporary_destination(target)
        try:
            source = source_store._connect(query_only=True)
            restored: sqlite3.Connection | None = None
            try:
                restored = sqlite3.connect(temporary, isolation_level=None)
                source.backup(restored)
            except sqlite3.Error as exc:
                raise RecoveryError(str(cls._translate_error(exc))) from exc
            finally:
                if restored is not None:
                    restored.close()
                source.close()
            if file_sha256(source_path) != source_digest:
                raise RecoveryError("backup source changed during restore")
            temporary_store = cls(
                temporary,
                tenant_id=tenant_id,
                local_filesystem=local_filesystem,
                busy_timeout_ms=busy_timeout_ms,
            )
            temporary_store._verify_internal()
            with temporary_store._write_transaction() as connection:
                temporary_store._append_event(
                    connection,
                    context=context,
                    event_type="restore",
                    dka_id=None,
                    branch=None,
                    result_head=None,
                    previous_head=None,
                    detail={"source_backup_digest": source_digest},
                )
            temporary_store._verify_internal()
            cls._publish_new_file(temporary, target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return cls(
            target,
            tenant_id=tenant_id,
            local_filesystem=local_filesystem,
            busy_timeout_ms=busy_timeout_ms,
        )

    def purge(
        self,
        dka_id: str,
        *,
        expected_heads: Mapping[str, tuple[str, str]],
        reason: str,
        context: StoreContext | None = None,
    ) -> dict[str, Any]:
        request = self._require(context, RETENTION)
        _safe_identifier(dka_id, name="dka_id")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 256:
            raise ValueError("reason must be a non-empty string of at most 256 characters")
        with self._write_transaction() as connection:
            rows = connection.execute(
                """
                SELECT dka_id, branch, revision, digest, digest_profile, updated_at
                FROM heads WHERE tenant_id=? AND dka_id=? ORDER BY branch
                """,
                (self.tenant_id, dka_id),
            ).fetchall()
            current = {row["branch"]: self._head_from_row(row) for row in rows}
            if not current:
                raise RecordNotFound(f"no DKA to purge: {dka_id}")
            current_tuples = {
                branch: (head["digest"], head["digest_profile"])
                for branch, head in current.items()
                if head is not None
            }
            if dict(expected_heads) != current_tuples:
                raise HeadConflict(
                    f"purge expected heads {dict(expected_heads)!r}, found {current_tuples!r}"
                )
            deleted_at = _utc_now()
            connection.execute(
                "DELETE FROM heads WHERE tenant_id=? AND dka_id=?",
                (self.tenant_id, dka_id),
            )
            connection.execute(
                "DELETE FROM snapshots WHERE tenant_id=? AND dka_id=?",
                (self.tenant_id, dka_id),
            )
            connection.execute(
                """
                INSERT INTO tombstones(tenant_id, dka_id, deleted_at, deleted_by, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                (self.tenant_id, dka_id, deleted_at, request.principal_id, reason),
            )
            self._append_event(
                connection,
                context=request,
                event_type="purge",
                dka_id=dka_id,
                branch=None,
                result_head=None,
                previous_head=None,
                detail={
                    "branches": sorted(current),
                    "deleted_at": deleted_at,
                    "reason": reason,
                    "retained_audit_metadata": True,
                },
            )
            return {
                "dka_id": dka_id,
                "deleted_at": deleted_at,
                "deleted_by": request.principal_id,
                "audit_metadata_retained": True,
                "backup_expiry_required": True,
            }

    def compact_after_purge(
        self, *, context: StoreContext | None = None
    ) -> dict[str, Any]:
        self._require(context, RETENTION)
        connection = self._connect()
        try:
            connection.execute("VACUUM")
        except sqlite3.Error as exc:
            raise self._translate_error(exc) from exc
        finally:
            connection.close()
        return {
            "completed": True,
            "sqlite_secure_delete": True,
            "scope": "live-database-file-only",
            "backup_expiry_required": True,
            "physical_erasure_guaranteed": False,
        }
