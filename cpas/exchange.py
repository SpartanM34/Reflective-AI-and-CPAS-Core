"""EEP v2 schema validation and explicit consensus records."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .provenance import load_json


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EEP_SCHEMA = REPOSITORY_ROOT / "schemas" / "epistemic-exchange-v2.0.schema.json"


def default_consensus() -> dict[str, Any]:
    return {"status": "not_computed", "method": "none", "decided_by": [], "basis": None}


def validate_message(message: Mapping[str, Any]) -> None:
    schema = load_json(EEP_SCHEMA)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(dict(message)), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValidationError(details)


def record_consensus(
    message: Mapping[str, Any],
    *,
    status: str,
    method: str,
    decided_by: Iterable[str],
    basis: str,
) -> dict[str, Any]:
    if status == "not_computed" or method == "none":
        raise ValueError("a consensus record requires a computed status and method")
    deciders = list(decided_by)
    if not deciders or not basis.strip():
        raise ValueError("a consensus record requires a decider and non-empty basis")
    result = copy.deepcopy(dict(message))
    result["message_type"] = "consensus_record"
    result["consensus"] = {
        "status": status,
        "method": method,
        "decided_by": deciders,
        "basis": basis,
    }
    validate_message(result)
    return result


def agreement_is_not_consensus(messages: Iterable[Mapping[str, Any]]) -> bool:
    materialized = list(messages)
    if len(materialized) < 2:
        return False
    claims = {message.get("claim") for message in materialized}
    all_uncomputed = all(
        message.get("consensus", {}).get("status") == "not_computed"
        for message in materialized
    )
    return len(claims) == 1 and all_uncomputed
