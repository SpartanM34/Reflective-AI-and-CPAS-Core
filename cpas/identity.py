"""Stable identity projection and runtime-independent comparison."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from .provenance import (
    IDP_IDENTITY_DIGEST_PROFILE,
    LEGACY_CANONICALIZATION,
    profiled_digest,
    resolve_digest_profile,
)


IDENTITY_FIELDS = (
    "idp_version",
    "instance_id",
    "instance_name",
    "identity_profile",
    "epistemic_policy",
    "safety",
)


def identity_projection(declaration: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in IDENTITY_FIELDS if field not in declaration]
    if missing:
        raise ValueError(f"missing identity fields: {', '.join(missing)}")
    return {field: copy.deepcopy(declaration[field]) for field in IDENTITY_FIELDS}


def identity_digest_spec(declaration: Mapping[str, Any]) -> tuple[str, str]:
    """Return the canonicalization and resolved identity digest profile."""

    provenance = declaration.get("provenance", {})
    continuity = declaration.get("continuity", {})
    if not isinstance(provenance, Mapping) or not isinstance(continuity, Mapping):
        raise TypeError("identity digest metadata must be objects")
    canonicalization = str(
        provenance.get("canonicalization", LEGACY_CANONICALIZATION)
    )
    profile = resolve_digest_profile(
        canonicalization,
        continuity.get("identity_digest_profile"),
    )
    if (
        profile != IDP_IDENTITY_DIGEST_PROFILE
        and canonicalization != LEGACY_CANONICALIZATION
    ):
        raise ValueError(
            f"identity digest requires profile {IDP_IDENTITY_DIGEST_PROFILE}, got {profile}"
        )
    return canonicalization, profile


def identity_digest(declaration: Mapping[str, Any]) -> str:
    canonicalization, profile = identity_digest_spec(declaration)
    return profiled_digest(
        identity_projection(declaration),
        canonicalization=canonicalization,
        digest_profile=profile,
        expected_v2_profile=IDP_IDENTITY_DIGEST_PROFILE,
    )


def bind_runtime(
    declaration: Mapping[str, Any], runtime_binding: Mapping[str, Any]
) -> dict[str, Any]:
    """Return a bound declaration and prove the stable projection did not move."""

    before = identity_digest(declaration)
    bound = copy.deepcopy(dict(declaration))
    bound["runtime_binding"] = copy.deepcopy(dict(runtime_binding))
    after = identity_digest(bound)
    if before != after:  # defensive: the projection deliberately excludes binding
        raise AssertionError("runtime binding changed stable identity")
    return bound


def same_declared_identity(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    """Compare declared identity semantics independently of digest encoding."""

    return identity_projection(left) == identity_projection(right)
