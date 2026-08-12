"""Capability declaration, probing status, and negotiation."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .provenance import (
    CAPABILITY_PROFILE_DIGEST_PROFILE,
    JCS_CANONICALIZATION,
    profiled_digest,
    resolve_digest_profile,
)


CAPABILITY_RANK = {
    "unavailable": -1,
    "unknown": 0,
    "declared": 1,
    "probed": 2,
    "verified": 3,
}


def capability_profile(
    capabilities: Iterable[Mapping[str, Any]],
    *,
    canonicalization: str = JCS_CANONICALIZATION,
    digest_profile: str | None = CAPABILITY_PROFILE_DIGEST_PROFILE,
) -> dict[str, Any]:
    items = sorted(
        ({"name": str(item["name"]), "status": str(item["status"])} for item in capabilities),
        key=lambda item: item["name"],
    )
    if len({item["name"] for item in items}) != len(items):
        raise ValueError("capability names must be unique")
    for item in items:
        if item["status"] not in CAPABILITY_RANK:
            raise ValueError(f"unknown capability status: {item['status']}")
    resolved_profile = resolve_digest_profile(canonicalization, digest_profile)
    return {
        "canonicalization": canonicalization,
        "digest_profile": resolved_profile,
        "digest": profiled_digest(
            items,
            canonicalization=canonicalization,
            digest_profile=resolved_profile,
            expected_v2_profile=CAPABILITY_PROFILE_DIGEST_PROFILE,
        ),
        "capabilities": items,
    }


def negotiate_capabilities(
    capabilities: Iterable[Mapping[str, Any]],
    *,
    required: Iterable[str] = (),
    optional: Iterable[str] = (),
    minimum_status: str = "probed",
) -> dict[str, Any]:
    if minimum_status not in CAPABILITY_RANK:
        raise ValueError(f"unknown minimum status: {minimum_status}")
    materialized = list(capabilities)
    observed = {str(item["name"]): str(item["status"]) for item in materialized}
    if len(observed) != len(materialized):
        raise ValueError("capability names must be unique")
    invalid = sorted(set(observed.values()) - set(CAPABILITY_RANK))
    if invalid:
        raise ValueError(f"unknown capability status: {', '.join(invalid)}")
    needed_rank = CAPABILITY_RANK[minimum_status]

    def missing(names: Iterable[str]) -> list[str]:
        return sorted(
            name
            for name in set(names)
            if CAPABILITY_RANK.get(observed.get(name, "unknown"), 0) < needed_rank
        )

    missing_required = missing(required)
    missing_optional = missing(optional)
    mode = "blocked" if missing_required else ("degraded" if missing_optional else "full")
    return {
        "mode": mode,
        "minimum_status": minimum_status,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "observed": observed,
    }
