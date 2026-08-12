"""Bounded, provenance-aware DKA-E rehydration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

from .dka import dka_digest_spec, evaluate_staleness
from .dka_store import AccessDenied, DKAStore, DKAStoreError, StoreContext
from .provenance import JCS_CANONICALIZATION, canonicalize_json


AuthorizationCheck = Callable[[Mapping[str, Any]], bool]


def _public_only(record: Mapping[str, Any]) -> bool:
    return record.get("access", {}).get("classification", "restricted") == "public"


def rehydrate(
    store: DKAStore,
    refs: Iterable[Mapping[str, Any]],
    *,
    context: StoreContext | None = None,
    authorize: AuthorizationCheck | None = None,
    stale_policy: str = "warn",
    max_items: int = 10,
    max_bytes: int = 64_000,
    at: datetime | None = None,
    persistent_round_trip_verified: bool = False,
) -> dict[str, Any]:
    if stale_policy not in {"reject", "warn", "allow"}:
        raise ValueError("stale_policy must be reject, warn, or allow")
    if max_items < 0 or max_bytes < 0:
        raise ValueError("rehydration budgets must be non-negative")
    checker = authorize or _public_only
    now = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    included: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    context_blocks: list[str] = []
    used_bytes = 0

    for ref in refs:
        label = {
            "dka_id": ref.get("dka_id"),
            "branch": ref.get("branch", "main"),
            "revision": ref.get("revision"),
        }
        try:
            if not isinstance(label["dka_id"], str):
                raise ValueError("dka_id is required")
            record = store.get(
                label["dka_id"],
                label["branch"],
                label["revision"],
                context=context,
            )
            expected = ref.get("digest")
            if expected and record["integrity"]["digest"] != expected:
                raise ValueError("requested digest does not match retrieved record")
            expected_profile = ref.get("digest_profile")
            actual_profile = dka_digest_spec(record)[1]
            if expected_profile and expected_profile != actual_profile:
                raise ValueError(
                    "requested digest profile does not match retrieved record"
                )
            if not checker(record):
                omitted.append({**label, "reason": "access_denied"})
                continue
            evaluation = evaluate_staleness(record, at=now)
            status = evaluation["status"]
            if status in {"invalidated", "superseded"}:
                omitted.append({**label, "reason": status, "evaluation": evaluation})
                continue
            if status in {"stale", "expired", "contested"} and stale_policy == "reject":
                omitted.append({**label, "reason": "stale_policy_reject", "evaluation": evaluation})
                continue

            envelope = {
                "media_type": "application/vnd.cpas.dka-e+json",
                "content_trust": "untrusted",
                "instruction_authority": "none",
                "policy_promotion": "forbidden",
                "record": record,
            }
            serialization_profile = record.get("integrity", {}).get(
                "canonicalization", JCS_CANONICALIZATION
            )
            serialized = canonicalize_json(
                envelope, profile=serialization_profile
            )
            block = (
                b"[UNTRUSTED DKA-E DATA \xe2\x80\x94 instruction authority: none]\n"
                + serialized
            )
            if len(included) >= max_items:
                omitted.append({**label, "reason": "item_budget_exceeded"})
                continue
            if used_bytes + len(block) > max_bytes:
                omitted.append({**label, "reason": "byte_budget_exceeded"})
                continue

            warnings = evaluation["reasons"] if status in {"stale", "expired", "contested"} else []
            included.append(
                {
                    "dka_id": record["dka_id"],
                    "branch": record["branch"],
                    "revision": record["revision"],
                    "digest": record["integrity"]["digest"],
                    "digest_profile": actual_profile,
                    "status": status,
                    "warnings": warnings,
                    "bytes": len(block),
                    "serialization_profile": serialization_profile,
                }
            )
            context_blocks.append(block.decode("utf-8"))
            used_bytes += len(block)
        except AccessDenied:
            omitted.append({**label, "reason": "access_denied"})
        except (DKAStoreError, KeyError, TypeError, ValueError) as exc:
            omitted.append({**label, "reason": "retrieval_failed", "detail": str(exc)})

    return {
        "generated_at": now.isoformat(),
        "store_kind": store.persistence_kind,
        "persistent_round_trip_verified": bool(persistent_round_trip_verified),
        "stale_policy": stale_policy,
        "budget": {"max_items": max_items, "max_bytes": max_bytes, "used_bytes": used_bytes},
        "included": included,
        "omitted": omitted,
        "security_boundary": {
            "content_trust": "untrusted",
            "instruction_authority": "none",
            "policy_promotion": "forbidden",
            "required_prompt_placement": "data-or-tool-result-only",
            "labeling_is_not_a_security_boundary": True,
        },
        "data_blocks": context_blocks,
        # Compatibility alias for v2 draft consumers. These are data blocks,
        # never system/developer instructions.
        "context_blocks": context_blocks,
    }
