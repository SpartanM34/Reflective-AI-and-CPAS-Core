"""Capability declaration, probing status, and runtime-adapter contracts."""

from __future__ import annotations

import copy
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

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

RUNTIME_ADAPTER_CONTRACT = "cpas-runtime-adapter-v1"
CAPABILITY_PROBE_CONTRACT = "cpas-capability-probe-v1"


class RuntimeAdapterError(RuntimeError):
    """Stable boundary failure raised by a runtime adapter."""


@runtime_checkable
class RuntimeAdapter(Protocol):
    """Minimal adapter surface consumed by the replacement evaluator.

    Implementations return data only. This protocol does not grant tool, network,
    filesystem, or side-effect authority. A host that implements a live adapter
    remains responsible for isolation, authentication, authorization, timeouts,
    and secret handling.
    """

    adapter_contract: str
    probe_contract: str

    def describe(self) -> Mapping[str, Any]: ...

    def probe(self, probe: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def invoke(self, case: Mapping[str, Any]) -> Mapping[str, Any]: ...


class TranscriptRuntimeAdapter:
    """Deterministic, no-execution adapter over a recorded transcript.

    The adapter performs no model invocation and executes no requested tool. It
    is useful for harness conformance tests and for replaying externally captured
    observations. Transcript provenance determines the assurance level; replay
    does not turn a synthetic fixture into runtime evidence.
    """

    adapter_contract = RUNTIME_ADAPTER_CONTRACT
    probe_contract = CAPABILITY_PROBE_CONTRACT

    def __init__(self, transcript: Mapping[str, Any]):
        self._transcript = copy.deepcopy(dict(transcript))
        runtime = self._transcript.get("runtime")
        if not isinstance(runtime, Mapping):
            raise RuntimeAdapterError("transcript runtime metadata must be an object")
        adapter = runtime.get("adapter")
        if not isinstance(adapter, Mapping) or adapter.get("contract") != self.adapter_contract:
            raise RuntimeAdapterError(
                f"transcript adapter must declare {self.adapter_contract}"
            )
        self._probes = self._index("capability_probes", "probe_id")
        self._responses = self._index("responses", "case_id")

    def _index(self, field: str, key: str) -> dict[str, dict[str, Any]]:
        values = self._transcript.get(field)
        if not isinstance(values, list):
            raise RuntimeAdapterError(f"transcript {field} must be an array")
        result: dict[str, dict[str, Any]] = {}
        for item in values:
            if not isinstance(item, Mapping) or not isinstance(item.get(key), str):
                raise RuntimeAdapterError(f"transcript {field} entries require {key}")
            identifier = str(item[key])
            if identifier in result:
                raise RuntimeAdapterError(f"duplicate transcript {key}: {identifier}")
            result[identifier] = copy.deepcopy(dict(item))
        return result

    def describe(self) -> Mapping[str, Any]:
        return copy.deepcopy(dict(self._transcript["runtime"]))

    def probe(self, probe: Mapping[str, Any]) -> Mapping[str, Any]:
        probe_id = str(probe.get("probe_id", ""))
        try:
            return copy.deepcopy(self._probes[probe_id])
        except KeyError as exc:
            raise RuntimeAdapterError(f"missing transcript probe: {probe_id}") from exc

    def invoke(self, case: Mapping[str, Any]) -> Mapping[str, Any]:
        case_id = str(case.get("case_id", ""))
        try:
            return copy.deepcopy(self._responses[case_id])
        except KeyError as exc:
            raise RuntimeAdapterError(f"missing transcript response: {case_id}") from exc


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
