"""Stable identity projection and runtime-independent comparison."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from .provenance import sha256_digest


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


def identity_digest(declaration: Mapping[str, Any]) -> str:
    return sha256_digest(identity_projection(declaration))


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
    return identity_digest(left) == identity_digest(right)
