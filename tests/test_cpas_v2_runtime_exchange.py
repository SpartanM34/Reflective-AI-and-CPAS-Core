from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cpas.continuity import build_activation_report, compare_declared_continuity
from cpas.exchange import (
    agreement_is_not_consensus,
    default_consensus,
    record_consensus,
    validate_message,
)
from cpas.identity import bind_runtime


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_eep_example_validates_with_uncomputed_consensus():
    message = load("examples/v2/epistemic-exchange-v2.example.json")
    validate_message(message)
    assert message["consensus"] == default_consensus()


def test_agreeing_agent_outputs_are_not_automatically_consensus():
    first = load("examples/v2/epistemic-exchange-v2.example.json")
    second = copy.deepcopy(first)
    second["message_id"] = "eep-example-002"
    second["sender"] = {"id": "second-agent", "kind": "agent"}
    assert agreement_is_not_consensus([first, second])
    assert first["consensus"]["status"] == "not_computed"


def test_consensus_requires_explicit_method_and_decider():
    message = load("examples/v2/epistemic-exchange-v2.example.json")
    with pytest.raises(ValueError):
        record_consensus(
            message,
            status="accepted",
            method="none",
            decided_by=[],
            basis="Agents agreed.",
        )
    decided = record_consensus(
        message,
        status="provisional",
        method="human_decision",
        decided_by=["Spartan-M34"],
        basis="Human review accepted the claim provisionally pending runtime tests.",
    )
    assert decided["message_type"] == "consensus_record"
    assert decided["consensus"]["decided_by"] == ["Spartan-M34"]


def test_activation_report_keeps_continuity_forms_separate():
    declaration = load("instances/current/Clarence-9-v2.0.json")
    report = build_activation_report(declaration)
    assert report["continuity_forms"]["declarative"]["active"] is True
    assert report["continuity_forms"]["contextual"]["active"] is False
    assert report["continuity_forms"]["epistemic"]["active"] is False
    assert report["continuity_forms"]["persistent_system"]["active"] is False


def test_verified_rehydration_activates_only_supported_forms():
    declaration = load("instances/current/Clarence-9-v2.0.json")
    report = build_activation_report(
        declaration,
        rehydration_manifest={
            "included": [{"dka_id": "example"}],
            "persistent_round_trip_verified": False,
        },
    )
    assert report["continuity_forms"]["epistemic"]["active"] is True
    assert report["continuity_forms"]["persistent_system"]["active"] is False


def test_runtime_change_is_reported_without_identity_break():
    declaration = load("instances/current/Clarence-9-v2.0.json")
    runtime = copy.deepcopy(declaration["runtime_binding"])
    runtime["provider"] = "another-provider"
    runtime["model"] = "another-model"
    rebound = bind_runtime(declaration, runtime)
    comparison = compare_declared_continuity(declaration, rebound)
    assert comparison["compatible"] is True
    assert comparison["runtime_changed"] is True
