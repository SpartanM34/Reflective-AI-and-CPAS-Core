"""SeedToken v2 integrity, optional HMAC, and structured validation."""

from __future__ import annotations

import copy
import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from .identity import identity_digest
from .provenance import canonical_json, load_json, sha256_digest, without_paths
from .runtime import capability_profile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SEED_SCHEMA = REPOSITORY_ROOT / "schemas" / "seed-token-v2.0.schema.json"


def _schema_errors(token: Mapping[str, Any]) -> list[str]:
    schema = load_json(SEED_SCHEMA)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(dict(token)), key=lambda item: list(item.path))
    ]


def seed_integrity_hash(token: Mapping[str, Any]) -> str:
    payload = without_paths(dict(token), [("integrity", "digest"), ("authenticator",)])
    return sha256_digest(payload)


def seal_token(token: Mapping[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(dict(token))
    sealed.pop("authenticator", None)
    sealed.setdefault("integrity", {})
    sealed["integrity"].update(
        {
            "algorithm": "sha-256",
            "canonicalization": "cpas-canonical-json-v1",
        }
    )
    sealed["integrity"].pop("digest", None)
    sealed["integrity"]["digest"] = seed_integrity_hash(sealed)
    return sealed


def verify_integrity(token: Mapping[str, Any]) -> bool:
    expected = token.get("integrity", {}).get("digest", "")
    return bool(expected) and hmac.compare_digest(str(expected), seed_integrity_hash(token))


def _hmac_payload(token: Mapping[str, Any]) -> bytes:
    payload = without_paths(dict(token), [("authenticator", "tag")])
    return canonical_json(payload)


def add_hmac_authenticator(
    token: Mapping[str, Any], *, key_id: str, secret: bytes
) -> dict[str, Any]:
    if not secret:
        raise ValueError("HMAC secret must not be empty")
    authenticated = copy.deepcopy(dict(token))
    if not verify_integrity(authenticated):
        raise ValueError("seal and verify token integrity before adding HMAC")
    authenticated["authenticator"] = {"type": "hmac-sha256", "key_id": key_id}
    tag = hmac.new(secret, _hmac_payload(authenticated), hashlib.sha256).hexdigest()
    authenticated["authenticator"]["tag"] = "hmac-sha256:" + tag
    return authenticated


def verify_hmac(token: Mapping[str, Any], keys: Mapping[str, bytes]) -> bool:
    authenticator = token.get("authenticator")
    if not isinstance(authenticator, Mapping) or authenticator.get("type") != "hmac-sha256":
        return False
    key_id = authenticator.get("key_id")
    supplied = authenticator.get("tag")
    if not isinstance(key_id, str) or not isinstance(supplied, str) or key_id not in keys:
        return False
    expected = "hmac-sha256:" + hmac.new(
        keys[key_id], _hmac_payload(token), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(supplied, expected)


def build_seed_token(
    declaration: Mapping[str, Any],
    *,
    token_id: str,
    created_at: str,
    issued_for: str,
    issuer: str,
    continuity_scope: list[str],
    state_refs: list[dict[str, Any]] | None = None,
    parent_seed: dict[str, str] | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    runtime = declaration["runtime_binding"]
    token = {
        "$schema": "../../schemas/seed-token-v2.0.schema.json",
        "seed_version": "2.0",
        "token_id": token_id,
        "instance_id": declaration["instance_id"],
        "instance_name": declaration["instance_name"],
        "identity_digest": identity_digest(declaration),
        "identity_profile": declaration["identity_profile"]["summary"],
        "cpas_version": "2.0.0-draft.1",
        "idp_version": declaration["idp_version"],
        "created_at": created_at,
        "expires_at": expires_at,
        "runtime": {
            "provider": runtime.get("provider"),
            "model": runtime.get("model"),
            "runtime_version": runtime.get("runtime_version"),
            "observed_at": runtime.get("last_runtime_validation") or runtime.get("bound_at"),
        },
        "capability_profile": capability_profile(runtime.get("capabilities", [])),
        "state_refs": copy.deepcopy(state_refs or []),
        "parent_seed": copy.deepcopy(parent_seed),
        "continuity_scope": list(continuity_scope),
        "provenance": {
            "issuer": issuer,
            "issued_for": issued_for,
            "source_refs": ["trusted IDP supplied by caller"],
        },
        "integrity": {
            "algorithm": "sha-256",
            "canonicalization": "cpas-canonical-json-v1",
        },
    }
    return seal_token(token)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("date-time must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class TokenValidationResult:
    valid: bool
    integrity_valid: bool
    authentication_valid: bool | None
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


def validate_token(
    token: Mapping[str, Any],
    *,
    expected_declaration: Mapping[str, Any] | None = None,
    expected_parent: Mapping[str, str] | None = None,
    keys: Mapping[str, bytes] | None = None,
    require_authentication: bool = False,
    now: datetime | None = None,
) -> TokenValidationResult:
    errors = _schema_errors(token)
    warnings: list[str] = []
    integrity_valid = verify_integrity(token)
    if not integrity_valid:
        errors.append("integrity digest mismatch")

    try:
        expected_capability_digest = capability_profile(
            token["capability_profile"]["capabilities"]
        )["digest"]
        if token["capability_profile"]["digest"] != expected_capability_digest:
            errors.append("capability profile digest mismatch")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"invalid capability profile: {exc}")

    authentication_valid: bool | None = None
    if token.get("authenticator") is not None:
        authentication_valid = verify_hmac(token, keys or {})
        if not authentication_valid:
            errors.append("HMAC authentication failed or key is unavailable")
    elif require_authentication:
        authentication_valid = False
        errors.append("authentication is required but token has no authenticator")
    else:
        warnings.append("token is integrity-only; issuer is not authenticated")

    try:
        created = _parse_datetime(str(token["created_at"]))
        expires_raw = token.get("expires_at")
        if expires_raw is not None:
            expires = _parse_datetime(str(expires_raw))
            if expires <= created:
                errors.append("expires_at must be later than created_at")
            reference_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
            if reference_time >= expires:
                errors.append("token has expired")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"invalid token time: {exc}")

    if expected_declaration is not None:
        if token.get("instance_id") != expected_declaration.get("instance_id"):
            errors.append("instance_id does not match expected declaration")
        if token.get("identity_digest") != identity_digest(expected_declaration):
            errors.append("identity_digest does not match expected declaration")

    if expected_parent is not None:
        parent = token.get("parent_seed")
        if parent != dict(expected_parent):
            errors.append("parent_seed does not match expected parent")

    return TokenValidationResult(
        valid=not errors,
        integrity_valid=integrity_valid,
        authentication_valid=authentication_valid,
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(dict.fromkeys(warnings)),
    )
