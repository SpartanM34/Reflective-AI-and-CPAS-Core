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

from .identity import identity_digest, identity_digest_spec
from .provenance import (
    JCS_CANONICALIZATION,
    LEGACY_CANONICALIZATION,
    SEED_TOKEN_DIGEST_PROFILE,
    canonicalize_json,
    load_json,
    profiled_digest,
    resolve_digest_profile,
    without_paths,
)
from .runtime import capability_profile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SEED_SCHEMA = REPOSITORY_ROOT / "schemas" / "seed-token-v2.0.schema.json"
LEGACY_AUTHENTICATION_PROFILE = "cpas-hmac-direct-v1"
SEED_TOKEN_AUTHENTICATION_PROFILE = "cpas-hmac-v2:seed-token-authentication"
HMAC_FRAME_MAGIC = b"CPAS-HMAC-V2\x00"
_UNSET = object()


def _schema_errors(token: Mapping[str, Any]) -> list[str]:
    schema = load_json(SEED_SCHEMA)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(dict(token)), key=lambda item: list(item.path))
    ]


def seed_digest_spec(token: Mapping[str, Any]) -> tuple[str, str]:
    integrity = token.get("integrity", {})
    if not isinstance(integrity, Mapping):
        raise TypeError("SeedToken integrity metadata must be an object")
    canonicalization = str(
        integrity.get("canonicalization", LEGACY_CANONICALIZATION)
    )
    profile = resolve_digest_profile(
        canonicalization,
        integrity.get("digest_profile"),
    )
    if (
        profile != SEED_TOKEN_DIGEST_PROFILE
        and canonicalization != LEGACY_CANONICALIZATION
    ):
        raise ValueError(
            f"SeedToken digest requires profile {SEED_TOKEN_DIGEST_PROFILE}, got {profile}"
        )
    return canonicalization, profile


def seed_integrity_hash(token: Mapping[str, Any]) -> str:
    payload = without_paths(dict(token), [("integrity", "digest"), ("authenticator",)])
    canonicalization, profile = seed_digest_spec(token)
    return profiled_digest(
        payload,
        canonicalization=canonicalization,
        digest_profile=profile,
        expected_v2_profile=SEED_TOKEN_DIGEST_PROFILE,
    )


def seal_token(
    token: Mapping[str, Any],
    *,
    canonicalization: str | None = None,
    digest_profile: str | None | object = _UNSET,
) -> dict[str, Any]:
    sealed = copy.deepcopy(dict(token))
    sealed.pop("authenticator", None)
    integrity = sealed.setdefault("integrity", {})
    if not isinstance(integrity, dict):
        raise TypeError("SeedToken integrity metadata must be an object")
    had_canonicalization = "canonicalization" in integrity
    selected_canonicalization = (
        canonicalization
        if canonicalization is not None
        else integrity.get("canonicalization", JCS_CANONICALIZATION)
    )
    if digest_profile is _UNSET:
        selected_profile = integrity.get("digest_profile")
        if not had_canonicalization or canonicalization is not None:
            selected_profile = (
                SEED_TOKEN_DIGEST_PROFILE
                if selected_canonicalization == JCS_CANONICALIZATION
                else None
            )
    else:
        selected_profile = digest_profile
        if selected_profile is not None and not isinstance(selected_profile, str):
            raise TypeError("digest_profile must be a string or None")
    resolved_profile = resolve_digest_profile(
        str(selected_canonicalization),
        selected_profile if isinstance(selected_profile, str) else None,
    )
    if (
        selected_canonicalization != LEGACY_CANONICALIZATION
        and resolved_profile != SEED_TOKEN_DIGEST_PROFILE
    ):
        raise ValueError(f"SeedTokens require {SEED_TOKEN_DIGEST_PROFILE}")
    integrity.update(
        {"algorithm": "sha-256", "canonicalization": selected_canonicalization}
    )
    if selected_profile is None and selected_canonicalization == LEGACY_CANONICALIZATION:
        integrity.pop("digest_profile", None)
    else:
        integrity["digest_profile"] = resolved_profile
    integrity.pop("digest", None)
    integrity["digest"] = seed_integrity_hash(sealed)
    return sealed


def verify_integrity(token: Mapping[str, Any]) -> bool:
    expected = token.get("integrity", {}).get("digest", "")
    try:
        actual = seed_integrity_hash(token)
    except (TypeError, ValueError):
        return False
    return bool(expected) and hmac.compare_digest(str(expected), actual)


def _hmac_payload(token: Mapping[str, Any]) -> bytes:
    payload = without_paths(dict(token), [("authenticator", "tag")])
    canonicalization, _ = seed_digest_spec(token)
    authenticator = token.get("authenticator", {})
    if not isinstance(authenticator, Mapping):
        raise TypeError("SeedToken authenticator must be an object")
    authentication_profile = authenticator.get("authentication_profile")
    if canonicalization == LEGACY_CANONICALIZATION:
        if authentication_profile not in {None, LEGACY_AUTHENTICATION_PROFILE}:
            raise ValueError(
                f"authentication profile {authentication_profile} is incompatible with "
                f"{canonicalization}"
            )
        return canonicalize_json(payload, profile=canonicalization)
    if authentication_profile != SEED_TOKEN_AUTHENTICATION_PROFILE:
        raise ValueError(
            f"SeedToken HMAC requires {SEED_TOKEN_AUTHENTICATION_PROFILE}"
        )
    return (
        HMAC_FRAME_MAGIC
        + SEED_TOKEN_AUTHENTICATION_PROFILE.encode("ascii")
        + b"\x00"
        + canonicalization.encode("ascii")
        + b"\x00"
        + canonicalize_json(payload, profile=canonicalization)
    )


def add_hmac_authenticator(
    token: Mapping[str, Any], *, key_id: str, secret: bytes
) -> dict[str, Any]:
    if not secret:
        raise ValueError("HMAC secret must not be empty")
    authenticated = copy.deepcopy(dict(token))
    if not verify_integrity(authenticated):
        raise ValueError("seal and verify token integrity before adding HMAC")
    canonicalization, _ = seed_digest_spec(authenticated)
    authentication_profile = (
        SEED_TOKEN_AUTHENTICATION_PROFILE
        if canonicalization == JCS_CANONICALIZATION
        else LEGACY_AUTHENTICATION_PROFILE
    )
    authenticated["authenticator"] = {
        "type": "hmac-sha256",
        "authentication_profile": authentication_profile,
        "key_id": key_id,
    }
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
    try:
        payload = _hmac_payload(token)
    except (TypeError, ValueError):
        return False
    expected = "hmac-sha256:" + hmac.new(keys[key_id], payload, hashlib.sha256).hexdigest()
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
    _, declaration_identity_profile = identity_digest_spec(declaration)
    state_references = copy.deepcopy(state_refs or [])
    for reference in state_references:
        if not isinstance(reference, Mapping) or not reference.get("digest_profile"):
            raise ValueError("new SeedToken state references require digest_profile")
    parent_reference = copy.deepcopy(parent_seed)
    if parent_reference is not None:
        if not isinstance(parent_reference, Mapping) or not parent_reference.get(
            "integrity_digest_profile"
        ):
            raise ValueError(
                "new SeedToken parent references require integrity_digest_profile"
            )
    token = {
        "$schema": "../../schemas/seed-token-v2.0.schema.json",
        "seed_version": "2.0",
        "token_id": token_id,
        "instance_id": declaration["instance_id"],
        "instance_name": declaration["instance_name"],
        "identity_digest": identity_digest(declaration),
        "identity_digest_profile": declaration_identity_profile,
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
        "state_refs": state_references,
        "parent_seed": parent_reference,
        "continuity_scope": list(continuity_scope),
        "provenance": {
            "issuer": issuer,
            "issued_for": issued_for,
            "source_refs": ["trusted IDP supplied by caller"],
        },
        "integrity": {
            "algorithm": "sha-256",
            "canonicalization": JCS_CANONICALIZATION,
            "digest_profile": SEED_TOKEN_DIGEST_PROFILE,
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
        supplied_capability_profile = token["capability_profile"]
        capability_canonicalization = supplied_capability_profile.get(
            "canonicalization", LEGACY_CANONICALIZATION
        )
        expected_capability_digest = capability_profile(
            supplied_capability_profile["capabilities"],
            canonicalization=capability_canonicalization,
            digest_profile=supplied_capability_profile.get("digest_profile"),
        )["digest"]
        if supplied_capability_profile["digest"] != expected_capability_digest:
            errors.append("capability profile digest mismatch")
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
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
        _, expected_identity_profile = identity_digest_spec(expected_declaration)
        supplied_identity_profile = token.get("identity_digest_profile")
        if (
            supplied_identity_profile is not None
            and supplied_identity_profile != expected_identity_profile
        ):
            errors.append("identity_digest_profile does not match expected declaration")

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
