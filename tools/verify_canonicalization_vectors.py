#!/usr/bin/env python3
"""Verify CPAS canonicalization and domain-separated digest vectors."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping

import rfc8785

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cpas.provenance import (  # noqa: E402
    DIGEST_FRAME_MAGIC,
    JCS_CANONICALIZATION,
    LEGACY_CANONICALIZATION,
    LEGACY_DIGEST_PROFILE,
    DuplicateKeyError,
    canonicalize_json,
    load_json,
    loads_json,
    profiled_digest,
)

DEFAULT_VECTORS = (
    REPOSITORY_ROOT
    / "compliance-tests"
    / "canonicalization"
    / "cpas-canonicalization-v1.json"
)


class VectorFailure(RuntimeError):
    """Raised when a normative vector does not reproduce exactly."""


def _mapping(value: Any, *, owner: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VectorFailure(f"{owner}: expected an object")
    return value


def classify_negative_vector(input_json: str) -> str | None:
    """Return the normative failure class, or ``None`` if input is accepted."""

    try:
        value = loads_json(input_json)
    except DuplicateKeyError:
        return "duplicate_key"
    except ValueError as exc:
        if "non-finite JSON number" in str(exc):
            return "non_finite_number"
        return "json_parse"
    try:
        canonicalize_json(value, profile=JCS_CANONICALIZATION)
    except rfc8785.IntegerDomainError:
        return "integer_domain"
    except (rfc8785.CanonicalizationError, UnicodeEncodeError):
        return "invalid_unicode"
    return None


def verify_vectors(path: str | Path = DEFAULT_VECTORS) -> int:
    vectors = _mapping(load_json(path), owner="vector document")
    canonicalization = str(vectors.get("canonicalization"))
    if canonicalization != JCS_CANONICALIZATION:
        raise VectorFailure(f"unexpected canonicalization: {canonicalization}")

    frame = _mapping(vectors.get("digest_frame"), owner="digest_frame")
    if frame.get("magic_hex") != DIGEST_FRAME_MAGIC.hex():
        raise VectorFailure("digest frame magic does not match the implementation")

    checked = 0
    for raw_vector in vectors.get("positive", []):
        vector = _mapping(raw_vector, owner="positive vector")
        vector_id = str(vector.get("id", "<unnamed>"))
        canonical = canonicalize_json(vector.get("value"), profile=canonicalization)
        if canonical.hex() != vector.get("canonical_hex"):
            raise VectorFailure(f"{vector_id}: canonical bytes differ")
        if len(canonical) != vector.get("canonical_length"):
            raise VectorFailure(f"{vector_id}: canonical length differs")
        digests = _mapping(vector.get("digests"), owner=f"{vector_id} digests")
        for profile, expected in digests.items():
            actual = profiled_digest(
                vector.get("value"),
                canonicalization=canonicalization,
                digest_profile=str(profile),
            )
            if actual != expected:
                raise VectorFailure(f"{vector_id}: digest differs for {profile}")
            checked += 1

    legacy = _mapping(vectors.get("legacy"), owner="legacy vector")
    if legacy.get("canonicalization") != LEGACY_CANONICALIZATION:
        raise VectorFailure("legacy vector canonicalization marker differs")
    if legacy.get("digest_profile") != LEGACY_DIGEST_PROFILE:
        raise VectorFailure("legacy vector digest profile marker differs")
    legacy_value = legacy.get("value")
    legacy_bytes = canonicalize_json(
        legacy_value,
        profile=LEGACY_CANONICALIZATION,
    )
    if legacy_bytes.hex() != legacy.get("canonical_hex"):
        raise VectorFailure("legacy canonical bytes differ")
    legacy_digest = profiled_digest(
        legacy_value,
        canonicalization=LEGACY_CANONICALIZATION,
        digest_profile=LEGACY_DIGEST_PROFILE,
    )
    if legacy_digest != legacy.get("digest"):
        raise VectorFailure("legacy direct digest differs")
    checked += 1

    for raw_vector in vectors.get("negative", []):
        vector = _mapping(raw_vector, owner="negative vector")
        vector_id = str(vector.get("id", "<unnamed>"))
        actual = classify_negative_vector(str(vector.get("input_json", "")))
        if actual != vector.get("expected_error"):
            raise VectorFailure(
                f"{vector_id}: expected {vector.get('expected_error')}, observed {actual}"
            )
        checked += 1
    return checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_VECTORS)
    args = parser.parse_args(argv)
    try:
        checked = verify_vectors(args.path)
    except Exception as exc:
        print(f"canonicalization vector verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"canonicalization vector verification passed: {checked} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
