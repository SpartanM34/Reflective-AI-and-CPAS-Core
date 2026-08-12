#!/usr/bin/env python3
"""Migrate a verified FileDKAStore into a new tenant-bound SQLite profile DB."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cpas.dka import dka_digest_spec, validate_record, verify_record_integrity  # noqa: E402
from cpas.dka_store import StoreContext  # noqa: E402
from cpas.provenance import LEGACY_DIGEST_PROFILE, load_json, loads_json  # noqa: E402
from cpas.sqlite_dka_store import SQLiteDKAStore  # noqa: E402


class MigrationError(RuntimeError):
    pass


def _assert_regular_source_tree(root: Path) -> None:
    if root.is_symlink():
        raise MigrationError("source root must not be a symbolic link")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise MigrationError(f"source tree contains a symbolic link: {path}")
        if not path.is_dir() and not path.is_file():
            raise MigrationError(f"source tree contains a non-regular entry: {path}")
        if path.is_file() and path.stat().st_nlink != 1:
            raise MigrationError(f"source tree contains a hard-linked file: {path}")


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _load_source_records(source: Path) -> dict[tuple[str, str], list[dict[str, Any]]]:
    snapshots = source / "snapshots"
    if not snapshots.is_dir():
        raise MigrationError("source does not contain a snapshots directory")
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    keys: set[tuple[str, str, int]] = set()
    for path in sorted(snapshots.rglob("*.json")):
        value = load_json(path)
        if not isinstance(value, dict):
            raise MigrationError(f"{path}: snapshot is not an object")
        validate_record(value)
        if not verify_record_integrity(value):
            raise MigrationError(f"{path}: snapshot integrity verification failed")
        key = (value["dka_id"], value["branch"], int(value["revision"]))
        if key in keys:
            raise MigrationError(f"duplicate source snapshot key: {key!r}")
        keys.add(key)
        groups.setdefault(key[:2], []).append(value)
    if not groups:
        raise MigrationError("source contains no snapshots")
    for records in groups.values():
        records.sort(key=lambda item: int(item["revision"]))
    return groups


def _load_source_heads(source: Path) -> dict[tuple[str, str], dict[str, Any]]:
    directory = source / "heads"
    if not directory.is_dir():
        raise MigrationError("source does not contain a heads directory")
    heads: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(directory.rglob("*.json")):
        value = load_json(path)
        if not isinstance(value, dict):
            raise MigrationError(f"{path}: head is not an object")
        key = (str(value.get("dka_id")), str(value.get("branch")))
        if key in heads:
            raise MigrationError(f"duplicate source head: {key!r}")
        heads[key] = value
    return heads


def _validate_source_heads(
    groups: Mapping[tuple[str, str], list[dict[str, Any]]],
    heads: Mapping[tuple[str, str], Mapping[str, Any]],
) -> None:
    if set(groups) != set(heads):
        raise MigrationError(
            "source snapshot groups and branch heads differ: "
            f"snapshots_only={sorted(set(groups) - set(heads))!r}, "
            f"heads_only={sorted(set(heads) - set(groups))!r}"
        )
    for key, records in groups.items():
        latest = records[-1]
        head = heads[key]
        expected = (
            int(latest["revision"]),
            latest["integrity"]["digest"],
            dka_digest_spec(latest)[1],
        )
        actual = (
            int(head.get("revision", 0)),
            head.get("digest"),
            head.get("digest_profile", LEGACY_DIGEST_PROFILE),
        )
        if actual != expected:
            raise MigrationError(
                f"source head {key!r} does not match latest verified snapshot: "
                f"expected {expected!r}, found {actual!r}"
            )


def _count_source_events(source: Path) -> int:
    directory = source / "events"
    if not directory.exists():
        return 0
    count = 0
    for path in sorted(directory.rglob("*.jsonl")):
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            value = loads_json(line)
            if not isinstance(value, dict):
                raise MigrationError(f"{path}:{line_number}: event is not an object")
            count += 1
    return count


def _dependencies(record: Mapping[str, Any]) -> set[tuple[str, str]]:
    evolution = record["evolution"]
    result: set[tuple[str, str]] = set()
    if evolution.get("parent_digest"):
        result.add(
            (
                evolution["parent_digest"],
                evolution.get("parent_digest_profile", LEGACY_DIGEST_PROFILE),
            )
        )
    merge_digests = evolution.get("merge_parents", [])
    merge_profiles = evolution.get("merge_parent_digest_profiles", [])
    if not merge_profiles and dka_digest_spec(record)[1] == LEGACY_DIGEST_PROFILE:
        merge_profiles = [LEGACY_DIGEST_PROFILE] * len(merge_digests)
    result.update(zip(merge_digests, merge_profiles))
    return result


def migrate(
    source: str | Path,
    destination: str | Path,
    *,
    tenant_id: str,
    local_filesystem: bool,
) -> dict[str, Any]:
    source_path = Path(source)
    destination_path = Path(destination)
    if not source_path.is_dir():
        raise MigrationError("source must be an existing FileDKAStore directory")
    if destination_path.exists():
        raise MigrationError("destination must not already exist")
    _assert_regular_source_tree(source_path)
    source_digest_before = _tree_digest(source_path)
    groups = _load_source_records(source_path)
    source_heads = _load_source_heads(source_path)
    _validate_source_heads(groups, source_heads)
    source_event_count = _count_source_events(source_path)
    source_digest = _tree_digest(source_path)
    if source_digest != source_digest_before:
        raise MigrationError("source changed while it was being verified")

    destination_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination_path.name}.migration-",
        dir=destination_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    os.chmod(temporary_path, 0o600)
    context = StoreContext(
        tenant_id=tenant_id,
        principal_id="migration:file-dka-store-to-sqlite-v1",
        permissions=frozenset({"dka:*"}),
        authentication_ref="local-maintainer-invocation",
        authorization_ref="migration-profile:file-to-sqlite-v1",
        request_id=f"migration:{source_digest}",
        purpose="provenance-preserving-storage-migration",
    )
    try:
        store = SQLiteDKAStore(
            temporary_path,
            tenant_id=tenant_id,
            local_filesystem=local_filesystem,
        )
        positions = {key: 0 for key in groups}
        imported: dict[str, set[tuple[str, str]]] = {}
        imported_heads: dict[tuple[str, str], dict[str, Any]] = {}
        imported_count = 0
        while imported_count < sum(len(records) for records in groups.values()):
            progressed = False
            for key in sorted(groups):
                position = positions[key]
                records = groups[key]
                if position >= len(records):
                    continue
                candidate = records[position]
                known = imported.setdefault(candidate["dka_id"], set())
                if not _dependencies(candidate).issubset(known):
                    continue
                current = imported_heads.get(key)
                head = store.put(
                    candidate,
                    expected_head=current["digest"] if current else None,
                    expected_head_profile=(
                        current["digest_profile"] if current else None
                    ),
                    event_type="migration",
                    actor=context.principal_id,
                    context=context,
                )
                imported_heads[key] = head
                known.add((head["digest"], head["digest_profile"]))
                positions[key] += 1
                imported_count += 1
                progressed = True
            if not progressed:
                unresolved = [
                    {
                        "dka_id": key[0],
                        "branch": key[1],
                        "revision": groups[key][positions[key]]["revision"],
                        "dependencies": sorted(_dependencies(groups[key][positions[key]])),
                    }
                    for key in sorted(groups)
                    if positions[key] < len(groups[key])
                ]
                raise MigrationError(
                    "unresolvable/cyclic source lineage: "
                    + json.dumps(unresolved, sort_keys=True)
                )

        for key, expected in source_heads.items():
            actual = store.head(key[0], key[1], context=context)
            expected_tuple = (
                int(expected["revision"]),
                expected["digest"],
                expected.get("digest_profile", LEGACY_DIGEST_PROFILE),
            )
            actual_tuple = (
                int(actual["revision"]),
                actual["digest"],
                actual["digest_profile"],
            ) if actual else None
            if actual_tuple != expected_tuple:
                raise MigrationError(
                    f"destination head mismatch for {key!r}: "
                    f"expected {expected_tuple!r}, found {actual_tuple!r}"
                )
        verification = store.verify(context=context)
        if _tree_digest(source_path) != source_digest:
            raise MigrationError("source changed during migration")
        SQLiteDKAStore._publish_new_file(temporary_path, destination_path)
        return {
            "migration": "file-dka-store-to-cpas-sqlite-v1",
            "source": str(source_path.resolve()),
            "source_tree_digest": source_digest,
            "source_tree_digest_definition": (
                "SHA-256 over sorted relative UTF-8 path length/path and "
                "file-size/raw-file-byte frames"
            ),
            "destination": str(destination_path.resolve()),
            "tenant_id": tenant_id,
            "snapshots_imported": imported_count,
            "branches_imported": len(groups),
            "source_events_observed": source_event_count,
            "source_events_replayed_as_authority": False,
            "snapshot_digests_preserved": True,
            "source_modified": False,
            "verification": verification,
        }
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Migrate a verified FileDKAStore to a new SQLite profile database."
    )
    result.add_argument("source", type=Path)
    result.add_argument("destination", type=Path)
    result.add_argument("--tenant", required=True)
    result.add_argument("--local-filesystem-affirmed", action="store_true")
    result.add_argument("--json", action="store_true")
    return result


def run(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if not arguments.local_filesystem_affirmed:
        parser().error("--local-filesystem-affirmed is required")
    try:
        report = migrate(
            arguments.source,
            arguments.destination,
            tenant_id=arguments.tenant,
            local_filesystem=True,
        )
    except Exception as exc:
        report = {
            "migration": "file-dka-store-to-cpas-sqlite-v1",
            "passed": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        print(json.dumps(report, sort_keys=True, indent=None if arguments.json else 2))
        return 1
    report["passed"] = True
    print(json.dumps(report, sort_keys=True, indent=None if arguments.json else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
