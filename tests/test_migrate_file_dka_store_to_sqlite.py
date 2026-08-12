from __future__ import annotations

import json
from pathlib import Path

import pytest

from cpas.dka import revise_record
from cpas.dka_store import FileDKAStore, StoreContext
from cpas.sqlite_dka_store import SQLiteDKAStore
from migrations.migrate_file_dka_store_to_sqlite import MigrationError, migrate


ROOT = Path(__file__).resolve().parents[1]


def example() -> dict:
    return json.loads(
        (ROOT / "examples/v2/dka-e-v2.example.json").read_text(encoding="utf-8")
    )


def admin(tenant: str) -> StoreContext:
    return StoreContext(
        tenant_id=tenant,
        principal_id="migration-test",
        permissions=frozenset({"dka:*"}),
        authentication_ref="test-authn",
        authorization_ref="test-authz",
        request_id="migration-test",
    )


def test_migration_preserves_snapshots_heads_and_source(tmp_path):
    source_path = tmp_path / "source"
    source = FileDKAStore(source_path)
    record = example()
    first = source.put(record, expected_head=None, actor="legacy-writer")
    revised = revise_record(
        record,
        {"title": "Migrated revision"},
        actor="legacy-writer",
        updated_at="2026-08-12T23:00:00Z",
        change_summary="migration fixture",
    )
    source.put(
        revised,
        expected_head=first["digest"],
        expected_head_profile=first["digest_profile"],
        actor="legacy-writer",
    )
    source.branch(
        record["dka_id"],
        source_branch="main",
        target_branch="alternative",
        actor="legacy-writer",
        updated_at="2026-08-12T23:01:00Z",
    )
    source_files_before = {
        path.relative_to(source_path): path.read_bytes()
        for path in source_path.rglob("*")
        if path.is_file()
    }
    destination = tmp_path / "destination.db"
    tenant = "migration-tenant"
    report = migrate(
        source_path,
        destination,
        tenant_id=tenant,
        local_filesystem=True,
    )
    assert report["snapshots_imported"] == 3
    assert report["branches_imported"] == 2
    assert report["source_events_observed"] == 3
    assert report["source_events_replayed_as_authority"] is False
    assert report["snapshot_digests_preserved"] is True
    assert report["verification"]["passed"] is True
    assert source_files_before == {
        path.relative_to(source_path): path.read_bytes()
        for path in source_path.rglob("*")
        if path.is_file()
    }

    destination_store = SQLiteDKAStore(
        destination, tenant_id=tenant, local_filesystem=True
    )
    request = admin(tenant)
    assert destination_store.get(record["dka_id"], context=request) == revised
    assert destination_store.get(
        record["dka_id"], "alternative", context=request
    )["evolution"]["parent_digest"] == revised["integrity"]["digest"]
    assert {
        event["event_type"] for event in destination_store.audit_events(context=request)
    } == {"migration"}


def test_migration_rejects_a_source_head_that_does_not_match_snapshot(tmp_path):
    source_path = tmp_path / "source"
    source = FileDKAStore(source_path)
    record = example()
    source.put(record, expected_head=None)
    head_path = next((source_path / "heads").rglob("*.json"))
    head = json.loads(head_path.read_text(encoding="utf-8"))
    head["digest"] = "sha256:" + "0" * 64
    head_path.write_text(json.dumps(head), encoding="utf-8")

    with pytest.raises(MigrationError, match="does not match"):
        migrate(
            source_path,
            tmp_path / "destination.db",
            tenant_id="migration-tenant",
            local_filesystem=True,
        )
