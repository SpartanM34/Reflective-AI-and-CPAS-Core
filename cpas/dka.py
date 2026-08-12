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

from .provenance import (
    DKA_SNAPSHOT_DIGEST_PROFILE,
    JCS_CANONICALIZATION,
    LEGACY_CANONICALIZATION,
    load_json,
    profiled_digest,
    resolve_digest_profile,
    without_paths,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DKA_SCHEMA = REPOSITORY_ROOT / "schemas" / "dka-e-v2.0.schema.json"
_UNSET = object()


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
    evolution = record.get("evolution", {})
    merge_parents = evolution.get("merge_parents", [])
    merge_profiles = evolution.get("merge_parent_digest_profiles")
    if merge_profiles is not None and len(merge_profiles) != len(merge_parents):
        raise ValidationError(
            "evolution/merge_parent_digest_profiles must align with merge_parents"
        )
    if evolution.get("parent_digest") is None and evolution.get("parent_digest_profile"):
        raise ValidationError(
            "evolution/parent_digest_profile requires parent_digest"
        )


def dka_digest_spec(record: Mapping[str, Any]) -> tuple[str, str]:
    integrity = record.get("integrity", {})
    if not isinstance(integrity, Mapping):
        raise TypeError("DKA integrity metadata must be an object")
    canonicalization = str(
        integrity.get("canonicalization", LEGACY_CANONICALIZATION)
    )
    profile = resolve_digest_profile(
        canonicalization,
        integrity.get("digest_profile"),
    )
    if (
        profile != DKA_SNAPSHOT_DIGEST_PROFILE
        and canonicalization != LEGACY_CANONICALIZATION
    ):
        raise ValueError(
            f"DKA digest requires profile {DKA_SNAPSHOT_DIGEST_PROFILE}, got {profile}"
        )
    return canonicalization, profile


def dka_digest(record: Mapping[str, Any]) -> str:
    canonicalization, profile = dka_digest_spec(record)
    return profiled_digest(
        without_paths(dict(record), [("integrity", "digest")]),
        canonicalization=canonicalization,
        digest_profile=profile,
        expected_v2_profile=DKA_SNAPSHOT_DIGEST_PROFILE,
    )


def seal_record(
    record: Mapping[str, Any],
    *,
    canonicalization: str | None = None,
    digest_profile: str | None | object = _UNSET,
    validate: bool = True,
) -> dict[str, Any]:
    sealed = copy.deepcopy(dict(record))
    integrity = sealed.setdefault("integrity", {})
    if not isinstance(integrity, dict):
        raise TypeError("DKA integrity metadata must be an object")
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
                DKA_SNAPSHOT_DIGEST_PROFILE
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
        and resolved_profile != DKA_SNAPSHOT_DIGEST_PROFILE
    ):
        raise ValueError(f"DKA records require {DKA_SNAPSHOT_DIGEST_PROFILE}")
    integrity["canonicalization"] = selected_canonicalization
    if selected_profile is None and selected_canonicalization == LEGACY_CANONICALIZATION:
        integrity.pop("digest_profile", None)
    else:
        integrity["digest_profile"] = resolved_profile
    sealed["integrity"].pop("digest", None)
    sealed["integrity"]["digest"] = dka_digest(sealed)
    if validate:
        validate_record(sealed)
    return sealed


def verify_record_integrity(record: Mapping[str, Any]) -> bool:
    expected = record.get("integrity", {}).get("digest", "")
    try:
        actual = dka_digest(record)
    except (TypeError, ValueError):
        return False
    return bool(expected) and hmac.compare_digest(str(expected), actual)


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
        "parent_digest_profile": dka_digest_spec(record)[1],
        "merge_parents": [],
        "merge_parent_digest_profiles": [],
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
    digest_specs = {dka_digest_spec(record) for record in records}
    if len(digest_specs) != 1:
        raise ValueError(
            "mixed DKA digest profiles require explicit migration before merge"
        )

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
        "parent_digest_profile": dka_digest_spec(base)[1],
        "merge_parents": [left["integrity"]["digest"], right["integrity"]["digest"]],
        "merge_parent_digest_profiles": [
            dka_digest_spec(left)[1],
            dka_digest_spec(right)[1],
        ],
        "change_summary": f"three-way merge by {actor}; {len(conflicts)} conflict(s) preserved",
    }
    merged["provenance"]["updated_at"] = updated_at
    merged["provenance"]["transformations"] = list(
        merged["provenance"].get("transformations", [])
    ) + [f"three-way merge by {actor}"]
    return seal_record(merged)
