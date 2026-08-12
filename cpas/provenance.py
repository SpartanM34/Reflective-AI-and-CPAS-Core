"""Versioned canonical JSON and digest helpers for CPAS v2.

``cpas-canonical-json-v1`` is retained byte-for-byte for verification of
existing draft artifacts. New semantic digests use RFC 8785/JCS plus an
artifact-specific CPAS digest profile. The profile identifier is part of the
hashed preimage, so equal JSON values in different protocol domains do not
share a digest.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import rfc8785


LEGACY_CANONICALIZATION = "cpas-canonical-json-v1"
JCS_CANONICALIZATION = "rfc8785-jcs-v1"

LEGACY_DIGEST_PROFILE = "cpas-sha256-direct-v1"
IDP_IDENTITY_DIGEST_PROFILE = "cpas-digest-v2:idp-identity"
DKA_SNAPSHOT_DIGEST_PROFILE = "cpas-digest-v2:dka-snapshot"
CAPABILITY_PROFILE_DIGEST_PROFILE = "cpas-digest-v2:capability-profile"
SEED_TOKEN_DIGEST_PROFILE = "cpas-digest-v2:seed-token-integrity"
DKA_STORE_EVENT_DIGEST_PROFILE = "cpas-digest-v2:dka-store-event"

V2_DIGEST_PROFILES = frozenset(
    {
        IDP_IDENTITY_DIGEST_PROFILE,
        DKA_SNAPSHOT_DIGEST_PROFILE,
        CAPABILITY_PROFILE_DIGEST_PROFILE,
        SEED_TOKEN_DIGEST_PROFILE,
        DKA_STORE_EVENT_DIGEST_PROFILE,
    }
)

DIGEST_FRAME_MAGIC = b"CPAS-DIGEST-V2\x00"


class DuplicateKeyError(ValueError):
    """Raised when JSON contains duplicate object members."""


def _reject_duplicates(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_json(text: str) -> Any:
    """Load JSON while rejecting duplicate keys and non-finite numbers."""

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    return json.loads(
        text,
        object_pairs_hook=_reject_duplicates,
        parse_constant=reject_constant,
    )


def load_json(path: str | Path) -> Any:
    return loads_json(Path(path).read_text(encoding="utf-8"))


def canonicalize_json(value: Any, *, profile: str) -> bytes:
    """Serialize JSON using a named, supported canonicalization profile.

    JCS constrains values to the I-JSON data model. The ``rfc8785`` package
    therefore rejects non-finite numbers, integers outside its safe domain,
    and invalid Unicode instead of silently coercing them.
    """

    if profile == JCS_CANONICALIZATION:
        return rfc8785.dumps(value)
    if profile != LEGACY_CANONICALIZATION:
        raise ValueError(f"unsupported canonicalization profile: {profile}")

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json(value: Any) -> bytes:
    """Serialize the frozen ``cpas-canonical-json-v1`` legacy profile.

    This deliberately makes no RFC 8785 claim. CPAS protocol documents are
    constrained to ordinary JSON types and finite numbers.
    """

    return canonicalize_json(value, profile=LEGACY_CANONICALIZATION)


def resolve_digest_profile(canonicalization: str, digest_profile: str | None) -> str:
    """Resolve omitted legacy markers and reject incompatible combinations."""

    if canonicalization == LEGACY_CANONICALIZATION:
        resolved = digest_profile or LEGACY_DIGEST_PROFILE
        if resolved != LEGACY_DIGEST_PROFILE:
            raise ValueError(
                f"digest profile {resolved} is incompatible with {canonicalization}"
            )
        return resolved
    if canonicalization == JCS_CANONICALIZATION:
        if digest_profile not in V2_DIGEST_PROFILES:
            supplied = digest_profile or "<missing>"
            raise ValueError(
                f"digest profile {supplied} is incompatible with {canonicalization}"
            )
        return str(digest_profile)
    raise ValueError(f"unsupported canonicalization profile: {canonicalization}")


def digest_preimage(
    value: Any,
    *,
    canonicalization: str,
    digest_profile: str,
) -> bytes:
    """Return the exact framed preimage for a CPAS v2 semantic digest."""

    resolved = resolve_digest_profile(canonicalization, digest_profile)
    if resolved == LEGACY_DIGEST_PROFILE:
        raise ValueError("legacy direct hashes do not use the CPAS v2 digest frame")
    return (
        DIGEST_FRAME_MAGIC
        + resolved.encode("ascii")
        + b"\x00"
        + canonicalization.encode("ascii")
        + b"\x00"
        + canonicalize_json(value, profile=canonicalization)
    )


def profiled_digest(
    value: Any,
    *,
    canonicalization: str,
    digest_profile: str | None,
    expected_v2_profile: str | None = None,
) -> str:
    """Hash JSON according to an explicitly negotiated digest profile.

    A missing profile is accepted only for the frozen legacy canonicalization.
    ``expected_v2_profile`` prevents one artifact type from claiming another
    artifact's domain.
    """

    resolved = resolve_digest_profile(canonicalization, digest_profile)
    if expected_v2_profile is not None and resolved not in {
        LEGACY_DIGEST_PROFILE,
        expected_v2_profile,
    }:
        raise ValueError(
            f"digest profile {resolved} does not match expected domain "
            f"{expected_v2_profile}"
        )
    if resolved == LEGACY_DIGEST_PROFILE:
        preimage = canonicalize_json(value, profile=canonicalization)
    else:
        preimage = digest_preimage(
            value,
            canonicalization=canonicalization,
            digest_profile=resolved,
        )
    return "sha256:" + hashlib.sha256(preimage).hexdigest()


def sha256_digest(value: Any) -> str:
    """Compute the frozen legacy direct SHA-256 digest."""

    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def without_paths(value: dict[str, Any], paths: Iterable[tuple[str, ...]]) -> dict[str, Any]:
    """Return a deep copy with selected object paths omitted."""

    result = copy.deepcopy(value)
    for path in paths:
        cursor: Any = result
        for part in path[:-1]:
            if not isinstance(cursor, dict) or part not in cursor:
                break
            cursor = cursor[part]
        else:
            if isinstance(cursor, dict):
                cursor.pop(path[-1], None)
    return result
