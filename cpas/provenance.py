"""Deterministic JSON and digest helpers for CPAS v2."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


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


def canonical_json(value: Any) -> bytes:
    """Serialize the repository's cpas-canonical-json-v1 profile.

    This deliberately makes no RFC 8785 claim. CPAS protocol documents are
    constrained to ordinary JSON types and finite numbers.
    """

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_digest(value: Any) -> str:
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
