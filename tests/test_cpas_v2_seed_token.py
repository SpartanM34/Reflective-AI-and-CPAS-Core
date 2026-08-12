from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cpas.seed_token import (
    SEED_TOKEN_AUTHENTICATION_PROFILE,
    add_hmac_authenticator,
    build_seed_token,
    seal_token,
    validate_token,
    verify_hmac,
    verify_integrity,
)
from cpas.provenance import (
    CAPABILITY_PROFILE_DIGEST_PROFILE,
    JCS_CANONICALIZATION,
    SEED_TOKEN_DIGEST_PROFILE,
)


ROOT = Path(__file__).resolve().parents[1]
KEY = b"documentation-only-test-key"


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_documented_token_integrity_and_hmac_verify():
    token = load("examples/v2/seed-token-v2.example.json")
    assert token["integrity"]["canonicalization"] == JCS_CANONICALIZATION
    assert token["integrity"]["digest_profile"] == SEED_TOKEN_DIGEST_PROFILE
    assert (
        token["capability_profile"]["digest_profile"]
        == CAPABILITY_PROFILE_DIGEST_PROFILE
    )
    assert (
        token["authenticator"]["authentication_profile"]
        == SEED_TOKEN_AUTHENTICATION_PROFILE
    )
    assert verify_integrity(token)
    assert verify_hmac(token, {"documentation-test-key": KEY})
    result = validate_token(
        token,
        expected_declaration=load("instances/current/Clarence-9-v2.0.json"),
        keys={"documentation-test-key": KEY},
        require_authentication=True,
        now=datetime(2026, 8, 12, tzinfo=timezone.utc),
    )
    assert result.valid, result.errors
    assert result.authentication_valid is True


def test_token_mutation_breaks_integrity_and_authentication():
    token = load("examples/v2/seed-token-v2.example.json")
    token["runtime"]["model"] = "substituted-model"
    assert not verify_integrity(token)
    assert not verify_hmac(token, {"documentation-test-key": KEY})


def test_capability_profile_digest_is_checked_separately():
    token = load("examples/v2/seed-token-v2.example.json")
    token["capability_profile"]["digest"] = "sha256:" + "0" * 64
    token = seal_token(token)
    result = validate_token(
        token,
        now=datetime(2026, 8, 12, tzinfo=timezone.utc),
    )
    assert not result.valid
    assert any("capability profile digest" in error for error in result.errors)


def test_wrong_hmac_key_fails_without_affecting_integrity():
    token = load("examples/v2/seed-token-v2.example.json")
    assert verify_integrity(token)
    assert not verify_hmac(token, {"documentation-test-key": b"wrong-key"})


def test_build_integrity_only_token_reports_no_authentication():
    declaration = load("instances/current/Clarence-9-v2.0.json")
    token = build_seed_token(
        declaration,
        token_id="seed-test-001",
        created_at="2026-08-11T00:00:00Z",
        expires_at="2026-09-11T00:00:00Z",
        issued_for="unit test",
        issuer="test suite",
        continuity_scope=["declarative"],
    )
    result = validate_token(
        token,
        expected_declaration=declaration,
        now=datetime(2026, 8, 12, tzinfo=timezone.utc),
    )
    assert result.valid
    assert result.authentication_valid is None
    assert "integrity-only" in result.warnings[0]


def test_optional_hmac_can_be_added_to_built_token():
    declaration = load("instances/current/Clarence-9-v2.0.json")
    token = build_seed_token(
        declaration,
        token_id="seed-test-002",
        created_at="2026-08-11T00:00:00Z",
        issued_for="unit test",
        issuer="test suite",
        continuity_scope=["declarative"],
    )
    authenticated = add_hmac_authenticator(token, key_id="test-key", secret=b"secret")
    assert verify_integrity(authenticated)
    assert verify_hmac(authenticated, {"test-key": b"secret"})


def test_expiration_and_parent_mismatch_are_errors():
    token = load("examples/v2/seed-token-v2.example.json")
    result = validate_token(
        token,
        expected_parent={
            "token_id": "different-parent",
            "integrity_digest": "sha256:" + "1" * 64,
        },
        keys={"documentation-test-key": KEY},
        now=datetime(2028, 1, 1, tzinfo=timezone.utc),
    )
    assert not result.valid
    assert any("expired" in error for error in result.errors)
    assert any("parent_seed" in error for error in result.errors)


def test_resealing_removes_stale_authenticator():
    token = load("examples/v2/seed-token-v2.example.json")
    resealed = seal_token(token)
    assert "authenticator" not in resealed
    assert verify_integrity(resealed)


def test_new_state_references_require_an_explicit_digest_profile():
    declaration = load("instances/current/Clarence-9-v2.0.json")
    with pytest.raises(ValueError, match="state references require digest_profile"):
        build_seed_token(
            declaration,
            token_id="seed-test-untyped-ref",
            created_at="2026-08-11T00:00:00Z",
            issued_for="unit test",
            issuer="test suite",
            continuity_scope=["epistemic"],
            state_refs=[
                {
                    "kind": "dka",
                    "ref": "example/main/1",
                    "digest": "sha256:" + "0" * 64,
                }
            ],
        )
