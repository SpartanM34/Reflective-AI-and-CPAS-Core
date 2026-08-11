from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cpas.dka import (
    evaluate_staleness,
    merge_records,
    revise_record,
    seal_record,
    validate_record,
    verify_record_integrity,
)
from cpas.dka_store import DKAStoreError, FileDKAStore, HeadConflict
from cpas.rehydrate import rehydrate


ROOT = Path(__file__).resolve().parents[1]


def example():
    return json.loads((ROOT / "examples/v2/dka-e-v2.example.json").read_text(encoding="utf-8"))


def test_example_schema_and_integrity():
    record = example()
    validate_record(record)
    assert verify_record_integrity(record)


def test_staleness_evaluation_does_not_mutate_snapshot():
    record = example()
    original = copy.deepcopy(record)
    result = evaluate_staleness(record, at=datetime(2027, 3, 1, tzinfo=timezone.utc))
    assert result["status"] == "stale"
    assert record == original


def test_trigger_can_invalidate_record():
    record = example()
    result = evaluate_staleness(
        record,
        at=datetime(2026, 8, 12, tzinfo=timezone.utc),
        fired_triggers={"trigger-identity-runtime-collapse"},
    )
    # The example trigger requests review, so it marks stale rather than invalid.
    assert result["status"] == "stale"


def test_revision_has_parent_digest_and_new_integrity():
    record = example()
    revised = revise_record(
        record,
        {"claim": "A revised claim with explicit review."},
        actor="unit-test",
        updated_at="2026-08-12T00:00:00Z",
        change_summary="test revision",
    )
    assert revised["revision"] == 2
    assert revised["evolution"]["parent_digest"] == record["integrity"]["digest"]
    assert revised["integrity"]["digest"] != record["integrity"]["digest"]
    assert verify_record_integrity(revised)


def test_file_store_round_trip_cas_history_and_events(tmp_path):
    store = FileDKAStore(tmp_path / "store")
    record = example()
    head = store.put(record, expected_head=None, actor="unit-test")
    assert store.get(record["dka_id"]) == record
    assert head["digest"] == record["integrity"]["digest"]
    assert len(store.history(record["dka_id"])) == 1
    assert store.events(record["dka_id"])[0]["event_type"] == "commit"

    revised = revise_record(
        record,
        {"title": "Revised title"},
        actor="unit-test",
        updated_at="2026-08-12T00:00:00Z",
        change_summary="title update",
    )
    with pytest.raises(HeadConflict):
        store.put(revised, expected_head="sha256:" + "0" * 64)
    store.put(revised, expected_head=head["digest"], actor="unit-test")
    assert [item["revision"] for item in store.history(record["dka_id"])] == [1, 2]


def test_file_store_detects_snapshot_tampering(tmp_path):
    store = FileDKAStore(tmp_path / "store")
    record = example()
    store.put(record, expected_head=None)
    snapshot = tmp_path / "store" / "snapshots" / record["dka_id"] / "main" / "1.json"
    tampered = json.loads(snapshot.read_text(encoding="utf-8"))
    tampered["claim"] = "tampered without resealing"
    snapshot.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(DKAStoreError, match="digest"):
        store.get(record["dka_id"])


def test_branch_creates_new_lineage(tmp_path):
    store = FileDKAStore(tmp_path / "store")
    record = example()
    store.put(record, expected_head=None)
    head = store.branch(
        record["dka_id"],
        source_branch="main",
        target_branch="alternative",
        actor="unit-test",
        updated_at="2026-08-12T00:00:00Z",
    )
    branched = store.get(record["dka_id"], "alternative")
    assert head["digest"] == branched["integrity"]["digest"]
    assert branched["evolution"]["parent_digest"] == record["integrity"]["digest"]


def _variant(base, branch, claim):
    result = copy.deepcopy(base)
    result["branch"] = branch
    result["revision"] = 2
    result["claim"] = claim
    result["evolution"] = {
        "parent_digest": base["integrity"]["digest"],
        "merge_parents": [],
        "change_summary": branch,
    }
    result["provenance"]["updated_at"] = "2026-08-12T00:00:00Z"
    return seal_record(result)


def test_three_way_merge_preserves_conflict_instead_of_averaging():
    base = example()
    left = _variant(base, "left", "Left claim")
    right = _variant(base, "right", "Right claim")
    merged = merge_records(
        base,
        left,
        right,
        actor="human-reviewer",
        updated_at="2026-08-13T00:00:00Z",
        target_branch="merged",
    )
    assert merged["claim"] == base["claim"]
    assert merged["validity"]["status"] == "contested"
    conflicts = [
        zone
        for zone in merged["epistemic_state"]["contested_zones"]
        if zone["id"].startswith("merge-conflict")
    ]
    assert conflicts and set(conflicts[0]["positions"]) == {"Left claim", "Right claim"}
    assert verify_record_integrity(merged)


def test_rehydration_labels_data_and_enforces_budgets_and_staleness(tmp_path):
    store = FileDKAStore(tmp_path / "store")
    record = example()
    store.put(record, expected_head=None)
    ref = {
        "dka_id": record["dka_id"],
        "branch": "main",
        "revision": 1,
        "digest": record["integrity"]["digest"],
    }
    manifest = rehydrate(
        store,
        [ref],
        at=datetime(2026, 8, 12, tzinfo=timezone.utc),
        persistent_round_trip_verified=True,
    )
    assert len(manifest["included"]) == 1
    assert manifest["context_blocks"][0].startswith("[UNTRUSTED DKA-E DATA")
    assert manifest["persistent_round_trip_verified"] is True

    too_small = rehydrate(store, [ref], max_bytes=1)
    assert too_small["included"] == []
    assert too_small["omitted"][0]["reason"] == "byte_budget_exceeded"

    stale = rehydrate(
        store,
        [ref],
        stale_policy="reject",
        at=datetime(2027, 3, 1, tzinfo=timezone.utc),
    )
    assert stale["included"] == []
    assert stale["omitted"][0]["reason"] == "stale_policy_reject"


def test_rehydration_defaults_to_public_only(tmp_path):
    store = FileDKAStore(tmp_path / "store")
    record = example()
    record["access"] = {"classification": "confidential", "policy_ref": "policy:team-only"}
    record = seal_record(record)
    store.put(record, expected_head=None)
    manifest = rehydrate(store, [{"dka_id": record["dka_id"], "branch": "main"}])
    assert manifest["included"] == []
    assert manifest["omitted"][0]["reason"] == "access_denied"
