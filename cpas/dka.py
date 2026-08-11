"""DKA-E v2 records, integrity, validity, revision, and merge."""

from __future__ import annotations

import copy
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .provenance import canonical_json, load_json, sha256_digest, without_paths


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DKA_SCHEMA = REPOSITORY_ROOT / "schemas" / "dka-e-v2.0.schema.json"


def validate_record(record: Mapping[str, Any]) -> None:
    schema = load_json(DKA_SCHEMA)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(dict(record)), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValidationError(details)


def dka_digest(record: Mapping[str, Any]) -> str:
    return sha256_digest(without_paths(dict(record), [("integrity", "digest")]))


def seal_record(record: Mapping[str, Any], *, validate: bool = True) -> dict[str, Any]:
    sealed = copy.deepcopy(dict(record))
    sealed.setdefault("integrity", {})
    sealed["integrity"].update({"canonicalization": "cpas-canonical-json-v1"})
    sealed["integrity"].pop("digest", None)
    sealed["integrity"]["digest"] = dka_digest(sealed)
    if validate:
        validate_record(sealed)
    return sealed


def verify_record_integrity(record: Mapping[str, Any]) -> bool:
    expected = record.get("integrity", {}).get("digest", "")
    return bool(expected) and hmac.compare_digest(str(expected), dka_digest(record))


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def evaluate_staleness(
    record: Mapping[str, Any],
    *,
    at: datetime | None = None,
    fired_triggers: set[str] | None = None,
) -> dict[str, Any]:
    """Evaluate status without mutating the historical snapshot."""

    now = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    validity = record["validity"]
    status = str(validity["status"])
    reasons: list[str] = []

    terminal = {"invalidated", "superseded"}
    if status in terminal:
        reasons.append(f"record is already {status}")
        return {"status": status, "evaluated_at": now.isoformat(), "reasons": reasons}

    fired = fired_triggers or set()
    actions = {
        trigger["id"]: trigger["action"]
        for trigger in validity.get("invalidation_triggers", [])
        if trigger["id"] in fired
    }
    if "invalidate" in actions.values():
        status = "invalidated"
        reasons.append("an invalidation trigger fired")
    elif "mark_stale" in actions.values() or "review" in actions.values():
        status = "stale"
        reasons.append("a review/staleness trigger fired")

    valid_until = validity.get("valid_until")
    if status != "invalidated" and valid_until and now >= _parse_time(valid_until):
        status = "expired"
        reasons.append("valid_until has passed")

    half_life = validity.get("epistemic_half_life_seconds")
    if status not in {"invalidated", "expired"} and half_life:
        updated = _parse_time(record["provenance"]["updated_at"])
        if (now - updated).total_seconds() >= int(half_life):
            status = "stale"
            reasons.append("epistemic half-life elapsed; review is due")

    return {
        "status": status,
        "evaluated_at": now.isoformat(),
        "reasons": reasons or ["no staleness or invalidation condition observed"],
    }


def revise_record(
    record: Mapping[str, Any],
    changes: Mapping[str, Any],
    *,
    actor: str,
    updated_at: str,
    change_summary: str,
) -> dict[str, Any]:
    if not verify_record_integrity(record):
        raise ValueError("cannot revise a record with invalid integrity")
    forbidden = {"dka_id", "branch", "revision", "integrity", "evolution", "provenance"}
    overlap = forbidden.intersection(changes)
    if overlap:
        raise ValueError(f"revision cannot replace managed fields: {', '.join(sorted(overlap))}")
    revised = copy.deepcopy(dict(record))
    for key, value in changes.items():
        revised[key] = copy.deepcopy(value)
    revised["revision"] = int(record["revision"]) + 1
    revised["evolution"] = {
        "parent_digest": record["integrity"]["digest"],
        "merge_parents": [],
        "change_summary": change_summary,
    }
    revised["provenance"]["updated_at"] = updated_at
    revised["provenance"]["transformations"] = list(
        revised["provenance"].get("transformations", [])
    ) + [f"revision by {actor}: {change_summary}"]
    return seal_record(revised)


def _select_three_way(base: Any, left: Any, right: Any) -> tuple[Any, bool]:
    if left == right:
        return copy.deepcopy(left), False
    if left == base:
        return copy.deepcopy(right), False
    if right == base:
        return copy.deepcopy(left), False
    return copy.deepcopy(base), True


def _position(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def merge_records(
    base: Mapping[str, Any],
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    actor: str,
    updated_at: str,
    target_branch: str,
) -> dict[str, Any]:
    """Conservative field-level three-way merge.

    Conflicting values remain at the base value and are added to contested
    zones. This intentionally does not average confidence or choose a claim.
    """

    records = (base, left, right)
    if len({record["dka_id"] for record in records}) != 1:
        raise ValueError("merge records must share dka_id")
    if not all(verify_record_integrity(record) for record in records):
        raise ValueError("all merge inputs must pass integrity verification")

    merged = copy.deepcopy(dict(base))
    conflicts: list[tuple[str, Any, Any]] = []
    for field in ("title", "claim", "epistemic_state", "validity", "relationships", "presentation", "access"):
        if field not in base and field not in left and field not in right:
            continue
        value, conflict = _select_three_way(base.get(field), left.get(field), right.get(field))
        if value is None and field not in base:
            merged.pop(field, None)
        else:
            merged[field] = value
        if conflict:
            conflicts.append((field, left.get(field), right.get(field)))

    contested = list(merged["epistemic_state"].get("contested_zones", []))
    for index, (field, left_value, right_value) in enumerate(conflicts, start=1):
        positions = list(dict.fromkeys([_position(left_value), _position(right_value)]))
        if len(positions) == 1:
            continue
        contested.append(
            {
                "id": f"merge-conflict-{index}",
                "question": f"Conflicting changes to {field} require resolution.",
                "positions": positions,
                "resolution_status": "human_required",
            }
        )
    merged["epistemic_state"]["contested_zones"] = contested
    if conflicts and merged["validity"]["status"] == "active":
        merged["validity"]["status"] = "contested"
    merged["branch"] = target_branch
    merged["revision"] = max(int(left["revision"]), int(right["revision"])) + 1
    merged["evolution"] = {
        "parent_digest": base["integrity"]["digest"],
        "merge_parents": [left["integrity"]["digest"], right["integrity"]["digest"]],
        "change_summary": f"three-way merge by {actor}; {len(conflicts)} conflict(s) preserved",
    }
    merged["provenance"]["updated_at"] = updated_at
    merged["provenance"]["transformations"] = list(
        merged["provenance"].get("transformations", [])
    ) + [f"three-way merge by {actor}"]
    return seal_record(merged)
