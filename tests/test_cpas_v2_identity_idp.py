from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from cpas.identity import bind_runtime, identity_digest, same_declared_identity
from cpas.idp import migrate_idp_v1_to_v2, validate_idp
from cpas.provenance import (
    CAPABILITY_PROFILE_DIGEST_PROFILE,
    IDP_IDENTITY_DIGEST_PROFILE,
    JCS_CANONICALIZATION,
    LEGACY_CANONICALIZATION,
    LEGACY_DIGEST_PROFILE,
    DuplicateKeyError,
    loads_json,
)
from cpas.runtime import capability_profile, negotiate_capabilities


ROOT = Path(__file__).resolve().parents[1]
CLARENCE = ROOT / "instances" / "current" / "Clarence-9-v2.0.json"
LEGACY_CLARENCE = ROOT / "agents" / "json" / "openai-gpt4" / "Clarence-9.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_clarence_v2_validates_and_digest_matches():
    declaration = load(CLARENCE)
    validate_idp(declaration)
    assert declaration["continuity"]["identity_digest"] == identity_digest(declaration)
    assert declaration["provenance"]["canonicalization"] == JCS_CANONICALIZATION
    assert (
        declaration["continuity"]["identity_digest_profile"]
        == IDP_IDENTITY_DIGEST_PROFILE
    )
    assert declaration["identity_profile"]["claims"] == {
        "consciousness": False,
        "felt_emotion": False,
        "permanent_selfhood": False,
        "inherent_memory": False,
        "autonomous_persistence": False,
    }


def test_runtime_rebinding_does_not_change_identity():
    declaration = load(CLARENCE)
    runtime = copy.deepcopy(declaration["runtime_binding"])
    runtime.update(
        {
            "provider": "example-provider",
            "model": "replaceable-model",
            "runtime_version": "2026-08",
            "bound_at": "2026-08-11T12:00:00Z",
            "last_runtime_validation": "2026-08-11T12:01:00Z",
        }
    )
    rebound = bind_runtime(declaration, runtime)
    assert rebound["runtime_binding"] != declaration["runtime_binding"]
    assert same_declared_identity(declaration, rebound)
    assert identity_digest(rebound) == identity_digest(declaration)


def test_idp_rejects_a_stale_identity_digest():
    declaration = load(CLARENCE)
    declaration["identity_profile"]["summary"] = "Changed without resealing identity."
    with pytest.raises(ValidationError, match="identity_digest"):
        validate_idp(declaration)


def test_capability_profile_and_negotiation_are_explicit():
    capabilities = [
        {"name": "web", "status": "verified"},
        {"name": "files", "status": "declared"},
    ]
    profile = capability_profile(capabilities)
    assert profile["digest"].startswith("sha256:")
    assert profile["canonicalization"] == JCS_CANONICALIZATION
    assert profile["digest_profile"] == CAPABILITY_PROFILE_DIGEST_PROFILE
    negotiation = negotiate_capabilities(
        capabilities,
        required=["web"],
        optional=["files", "code"],
        minimum_status="probed",
    )
    assert negotiation["mode"] == "degraded"
    assert negotiation["missing_required"] == []
    assert negotiation["missing_optional"] == ["code", "files"]


def test_required_capability_blocks_activation():
    result = negotiate_capabilities([], required=["external_store"])
    assert result["mode"] == "blocked"
    assert result["missing_required"] == ["external_store"]


def test_v1_migration_is_conservative_and_valid():
    source = load(LEGACY_CLARENCE)
    migrated = migrate_idp_v1_to_v2(
        source,
        source_path="agents/json/openai-gpt4/Clarence-9.json",
        source_revision="test-revision",
        migrated_at="2026-08-11T00:00:00Z",
        maintainer="Spartan-M34",
    )
    validate_idp(migrated)
    assert migrated["provenance"]["canonicalization"] == JCS_CANONICALIZATION
    assert (
        migrated["continuity"]["identity_digest_profile"]
        == IDP_IDENTITY_DIGEST_PROFILE
    )
    assert migrated["runtime_binding"]["model"] == "GPT-5 Thinking"
    assert migrated["continuity"]["forms"]["declarative"]["active"] is True
    assert migrated["continuity"]["forms"]["contextual"]["active"] is False
    assert migrated["continuity"]["forms"]["epistemic"]["active"] is False
    assert migrated["continuity"]["forms"]["persistent_system"]["active"] is False
    assert migrated["extensions"]["legacy_idp_v1"] == source
    assert migrated["extensions"]["legacy_idp_v1"]["hash"] == ""
    assert all(
        capability["status"] == "declared"
        for capability in migrated["runtime_binding"]["capabilities"]
    )


def test_duplicate_json_members_are_rejected():
    with pytest.raises(DuplicateKeyError):
        loads_json('{"instance_id":"first","instance_id":"replacement"}')


def test_v1_migration_can_emit_an_explicit_legacy_compatibility_draft():
    migrated = migrate_idp_v1_to_v2(
        load(LEGACY_CLARENCE),
        source_path="agents/json/openai-gpt4/Clarence-9.json",
        source_revision="test-revision",
        migrated_at="2026-08-11T00:00:00Z",
        maintainer="Spartan-M34",
        canonicalization=LEGACY_CANONICALIZATION,
    )
    validate_idp(migrated)
    assert migrated["provenance"]["canonicalization"] == LEGACY_CANONICALIZATION
    assert (
        migrated["continuity"]["identity_digest_profile"]
        == LEGACY_DIGEST_PROFILE
    )
