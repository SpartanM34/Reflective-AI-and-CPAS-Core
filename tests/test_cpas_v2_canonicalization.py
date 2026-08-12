from __future__ import annotations

import copy
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from cpas.dka import seal_record, validate_record, verify_record_integrity
from cpas.identity import identity_digest, same_declared_identity
from cpas.idp import validate_idp
from cpas.provenance import (
    CAPABILITY_PROFILE_DIGEST_PROFILE,
    DKA_SNAPSHOT_DIGEST_PROFILE,
    IDP_IDENTITY_DIGEST_PROFILE,
    JCS_CANONICALIZATION,
    LEGACY_CANONICALIZATION,
    LEGACY_DIGEST_PROFILE,
    canonicalize_json,
    profiled_digest,
)
from cpas.seed_token import seal_token, validate_token, verify_integrity
from tools.verify_canonicalization_vectors import verify_vectors


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_normative_vectors_pass_in_python():
    assert verify_vectors() == 17


def test_normative_vectors_pass_in_independent_node_implementation():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    result = subprocess.run(
        [node, "tools/verify_canonicalization_vectors.mjs"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "17 checks" in result.stdout


def test_digest_domains_are_not_substitutable():
    value = {"claim": "same canonical content"}
    identity = profiled_digest(
        value,
        canonicalization=JCS_CANONICALIZATION,
        digest_profile=IDP_IDENTITY_DIGEST_PROFILE,
    )
    dka = profiled_digest(
        value,
        canonicalization=JCS_CANONICALIZATION,
        digest_profile=DKA_SNAPSHOT_DIGEST_PROFILE,
    )
    capability = profiled_digest(
        value,
        canonicalization=JCS_CANONICALIZATION,
        digest_profile=CAPABILITY_PROFILE_DIGEST_PROFILE,
    )
    assert len({identity, dka, capability}) == 3


def test_legacy_profile_is_frozen_and_new_profiles_require_jcs():
    value = {"z": 0, "a": "legacy"}
    assert canonicalize_json(value, profile=LEGACY_CANONICALIZATION) == (
        b'{"a":"legacy","z":0}'
    )
    assert profiled_digest(
        value,
        canonicalization=LEGACY_CANONICALIZATION,
        digest_profile=None,
    ) == "sha256:cec138b0d41b2d7395a0857e584041a5e271b82d01f193dfa74b04aa28b6dda7"
    with pytest.raises(ValueError, match="incompatible"):
        profiled_digest(
            value,
            canonicalization=LEGACY_CANONICALIZATION,
            digest_profile=IDP_IDENTITY_DIGEST_PROFILE,
        )
    with pytest.raises(ValueError, match="<missing>"):
        profiled_digest(
            value,
            canonicalization=JCS_CANONICALIZATION,
            digest_profile=None,
        )


def test_legacy_dka_and_seedtoken_records_remain_verifiable():
    record = load("examples/v2/dka-e-v2.example.json")
    record = seal_record(
        record,
        canonicalization=LEGACY_CANONICALIZATION,
        digest_profile=None,
    )
    assert "digest_profile" not in record["integrity"]
    assert verify_record_integrity(record)

    token = load("examples/v2/seed-token-v2.example.json")
    token = seal_token(
        token,
        canonicalization=LEGACY_CANONICALIZATION,
        digest_profile=None,
    )
    assert "digest_profile" not in token["integrity"]
    assert verify_integrity(token)
    result = validate_token(
        token,
        now=datetime(2026, 8, 12, tzinfo=timezone.utc),
    )
    assert result.valid, result.errors


def test_digest_profile_migration_does_not_change_declared_identity_semantics():
    declaration = load("instances/current/Clarence-9-v2.0.json")
    legacy = copy.deepcopy(declaration)
    legacy["provenance"]["canonicalization"] = LEGACY_CANONICALIZATION
    legacy["continuity"]["identity_digest_profile"] = LEGACY_DIGEST_PROFILE
    legacy["continuity"]["identity_digest"] = identity_digest(legacy)
    current = copy.deepcopy(declaration)
    current["provenance"]["canonicalization"] = JCS_CANONICALIZATION
    current["continuity"]["identity_digest_profile"] = IDP_IDENTITY_DIGEST_PROFILE
    current["continuity"]["identity_digest"] = identity_digest(current)
    assert same_declared_identity(legacy, current)
    assert identity_digest(legacy) != identity_digest(current)


def test_jcs_artifacts_fail_closed_when_required_profiles_are_missing():
    declaration = load("instances/current/Clarence-9-v2.0.json")
    declaration["continuity"].pop("identity_digest_profile")
    with pytest.raises(ValidationError, match="identity_digest_profile"):
        validate_idp(declaration)

    record = load("examples/v2/dka-e-v2.example.json")
    record["integrity"].pop("digest_profile")
    with pytest.raises(ValidationError, match="digest_profile"):
        validate_record(record)

    token = load("examples/v2/seed-token-v2.example.json")
    token["state_refs"][0].pop("digest_profile")
    result = validate_token(
        token,
        now=datetime(2026, 8, 12, tzinfo=timezone.utc),
    )
    assert not result.valid
    assert any("digest_profile" in error for error in result.errors)
