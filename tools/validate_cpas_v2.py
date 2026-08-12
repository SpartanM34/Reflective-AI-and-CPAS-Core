#!/usr/bin/env python3
"""Validate CPAS v2 repository contracts and cross-file integrity references."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator, FormatChecker

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cpas.dka import validate_record, verify_record_integrity  # noqa: E402
from cpas.exchange import validate_message  # noqa: E402
from cpas.governance import validate_transition  # noqa: E402
from cpas.idp import migrate_idp_v1_to_v2, validate_idp  # noqa: E402
from cpas.provenance import (  # noqa: E402
    CAPABILITY_PROFILE_DIGEST_PROFILE,
    DKA_SNAPSHOT_DIGEST_PROFILE,
    IDP_IDENTITY_DIGEST_PROFILE,
    JCS_CANONICALIZATION,
    SEED_TOKEN_DIGEST_PROFILE,
    file_sha256,
    load_json,
)
from cpas.seed_token import validate_token  # noqa: E402
from tools.verify_canonicalization_vectors import verify_vectors  # noqa: E402


SCHEMA_INSTANCE_PAIRS = (
    ("schemas/idp-v2.0.schema.json", "instances/current/Clarence-9-v2.0.json"),
    ("schemas/dka-e-v2.0.schema.json", "examples/v2/dka-e-v2.example.json"),
    ("schemas/seed-token-v2.0.schema.json", "examples/v2/seed-token-v2.example.json"),
    (
        "schemas/idp-transition-v2.0.schema.json",
        "examples/v2/idp-transition-v2.example.json",
    ),
    (
        "schemas/epistemic-exchange-v2.0.schema.json",
        "examples/v2/epistemic-exchange-v2.example.json",
    ),
)

MARKDOWN_GLOBS = (
    "MODERNIZATION.md",
    "README.md",
    "cpas/README.md",
    "docs/ci-v2.md",
    "docs/index.md",
    "docs/audits/*.md",
    "docs/adr/*.md",
    "docs/open-questions-v2.md",
    "docs/research/current-platform-capabilities-*.md",
    "docs/verification/CPAS-v2-*.md",
    "instances/current/*.md",
    "instances/legacy/*.md",
    "migrations/CPAS-v1.1-to-v2.0.md",
    "migrations/canonicalization-v1-to-jcs-v1.md",
    "migrations/idp-v2-draft-governance.md",
    "schemas/README.md",
    "specs/v1.1/*.md",
    "specs/v2.0/*.md",
)

LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
DOCUMENTATION_HMAC_KEY = b"documentation-only-test-key"
DOCUMENTATION_VECTOR_TIME = datetime(2026, 8, 12, tzinfo=timezone.utc)


class ValidationFailure(RuntimeError):
    """Raised when a repository-level CPAS invariant fails."""


@dataclass(frozen=True)
class ValidationReport:
    schemas: int
    instances: int
    digest_references: int
    markdown_files: int
    markdown_links: int
    migrated_idps: int
    canonicalization_vector_checks: int


def _object(root: Path, relative: str) -> dict[str, Any]:
    value = load_json(root / relative)
    if not isinstance(value, dict):
        raise ValidationFailure(f"{relative}: expected a JSON object")
    return value


def validate_schema_instances(root: Path) -> None:
    for schema_relative, instance_relative in SCHEMA_INSTANCE_PAIRS:
        schema = _object(root, schema_relative)
        instance = _object(root, instance_relative)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
        if errors:
            first = errors[0]
            location = "/".join(map(str, first.path)) or "<root>"
            raise ValidationFailure(f"{instance_relative}:{location}: {first.message}")


def require_file_digest(root: Path, ref: str, expected: str, *, owner: str) -> None:
    path = (root / ref).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValidationFailure(f"{owner}: source reference escapes repository: {ref}") from exc
    if not path.is_file():
        raise ValidationFailure(f"{owner}: referenced file does not exist: {ref}")
    actual = file_sha256(path)
    if actual != expected:
        raise ValidationFailure(
            f"{owner}: digest mismatch for {ref}: expected {expected}, computed {actual}"
        )


def validate_semantics_and_integrity(root: Path) -> int:
    declaration = _object(root, "instances/current/Clarence-9-v2.0.json")
    dka = _object(root, "examples/v2/dka-e-v2.example.json")
    token = _object(root, "examples/v2/seed-token-v2.example.json")
    transition = _object(root, "examples/v2/idp-transition-v2.example.json")
    exchange = _object(root, "examples/v2/epistemic-exchange-v2.example.json")

    validate_idp(declaration)
    if declaration["provenance"]["canonicalization"] != JCS_CANONICALIZATION:
        raise ValidationFailure("current IDP does not use the JCS canonicalization profile")
    if declaration["continuity"].get("identity_digest_profile") != IDP_IDENTITY_DIGEST_PROFILE:
        raise ValidationFailure("current IDP identity digest profile is not domain-separated")
    validate_record(dka)
    if not verify_record_integrity(dka):
        raise ValidationFailure("DKA-E example integrity digest mismatch")
    if dka["integrity"].get("digest_profile") != DKA_SNAPSHOT_DIGEST_PROFILE:
        raise ValidationFailure("DKA-E example digest profile is not domain-separated")
    validate_message(exchange)
    validate_transition(transition)

    token_result = validate_token(
        token,
        expected_declaration=declaration,
        keys={"documentation-test-key": DOCUMENTATION_HMAC_KEY},
        require_authentication=True,
        now=DOCUMENTATION_VECTOR_TIME,
    )
    if not token_result.valid:
        raise ValidationFailure("SeedToken example invalid: " + "; ".join(token_result.errors))
    if token["integrity"].get("digest_profile") != SEED_TOKEN_DIGEST_PROFILE:
        raise ValidationFailure("SeedToken example digest profile is not domain-separated")
    if token["capability_profile"].get("digest_profile") != CAPABILITY_PROFILE_DIGEST_PROFILE:
        raise ValidationFailure("capability profile digest is not domain-separated")

    checked = 0
    for source in declaration["provenance"]["source_artifacts"]:
        if source.get("digest_profile") != "raw-sha256":
            raise ValidationFailure("Clarence-9 source artifact lacks raw-sha256 profile")
        require_file_digest(
            root,
            source["path"],
            source["digest"],
            owner="Clarence-9 v2 provenance",
        )
        checked += 1

    for source in dka["provenance"]["sources"]:
        if source["kind"] == "repository" and source.get("digest"):
            if source.get("digest_profile") != "raw-sha256":
                raise ValidationFailure("DKA-E repository source lacks raw-sha256 profile")
            require_file_digest(
                root,
                source["ref"],
                source["digest"],
                owner="DKA-E example provenance",
            )
            checked += 1

    dka_ref = f"{dka['dka_id']}/{dka['branch']}/{dka['revision']}"
    for state_ref in token["state_refs"]:
        if state_ref["kind"] == "idp":
            if state_ref.get("digest_profile") != "raw-sha256":
                raise ValidationFailure("SeedToken IDP state ref lacks raw-sha256 profile")
            require_file_digest(
                root,
                state_ref["ref"],
                state_ref["digest"],
                owner="SeedToken state reference",
            )
            checked += 1
        elif state_ref["kind"] == "dka":
            if state_ref.get("digest_profile") != DKA_SNAPSHOT_DIGEST_PROFILE:
                raise ValidationFailure("SeedToken DKA ref has the wrong digest profile")
            if state_ref["ref"] != dka_ref:
                raise ValidationFailure(
                    f"SeedToken DKA ref {state_ref['ref']} does not identify example {dka_ref}"
                )
            if state_ref["digest"] != dka["integrity"]["digest"]:
                raise ValidationFailure("SeedToken DKA digest does not match DKA-E example")
            checked += 1

    if exchange["instance_profile"]["identity_digest"] != declaration["continuity"][
        "identity_digest"
    ]:
        raise ValidationFailure("EEP identity digest does not match Clarence-9 v2")
    if exchange["instance_profile"].get("identity_digest_profile") != IDP_IDENTITY_DIGEST_PROFILE:
        raise ValidationFailure("EEP identity digest profile does not match Clarence-9 v2")
    checked += 1

    for evidence in exchange["evidence"]:
        if evidence.get("digest"):
            if evidence.get("digest_profile") != "raw-sha256":
                raise ValidationFailure("EEP repository evidence lacks raw-sha256 profile")
            require_file_digest(
                root,
                evidence["source_ref"],
                evidence["digest"],
                owner="EEP evidence",
            )
            checked += 1
    for reference in exchange["dka_refs"]:
        if reference["dka_id"] == dka["dka_id"]:
            if reference.get("digest_profile") != DKA_SNAPSHOT_DIGEST_PROFILE:
                raise ValidationFailure("EEP DKA ref has the wrong digest profile")
            if reference["digest"] != dka["integrity"]["digest"]:
                raise ValidationFailure("EEP DKA digest does not match DKA-E example")
            checked += 1
    return checked


def markdown_files(root: Path) -> list[Path]:
    files: set[Path] = set()
    for pattern in MARKDOWN_GLOBS:
        files.update(path for path in root.glob(pattern) if path.is_file())
    return sorted(files)


def validate_local_links(root: Path, files: Iterable[Path]) -> int:
    checked = 0
    repository_root = root.resolve()
    for markdown in files:
        text = markdown.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = raw_target.strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            candidate = (markdown.parent / unquote(parsed.path)).resolve()
            try:
                candidate.relative_to(repository_root)
            except ValueError as exc:
                raise ValidationFailure(
                    f"{markdown.relative_to(root)}: local link escapes repository: {target}"
                ) from exc
            if not candidate.exists():
                raise ValidationFailure(
                    f"{markdown.relative_to(root)}: broken local link: {target}"
                )
            checked += 1
    return checked


def validate_legacy_migrations(root: Path) -> int:
    count = 0
    source_root = root / "agents" / "json"
    for path in sorted(source_root.rglob("*.json")):
        source = load_json(path)
        if not isinstance(source, Mapping) or source.get("idp_version") != "1.0":
            continue
        migrate_idp_v1_to_v2(
            source,
            source_path=str(path.relative_to(root)),
            source_revision="repository-snapshot-under-test",
            source_digest=file_sha256(path),
            migrated_at="2026-08-11T00:00:00Z",
            maintainer="Spartan-M34",
        )
        count += 1
    if count == 0:
        raise ValidationFailure("no IDP v1 migration inputs discovered")
    return count


def validate_repository(root: Path = REPOSITORY_ROOT) -> ValidationReport:
    root = root.resolve()
    validate_schema_instances(root)
    digest_references = validate_semantics_and_integrity(root)
    files = markdown_files(root)
    links = validate_local_links(root, files)
    migrations = validate_legacy_migrations(root)
    vector_checks = verify_vectors(
        root
        / "compliance-tests"
        / "canonicalization"
        / "cpas-canonicalization-v1.json"
    )
    return ValidationReport(
        schemas=len(SCHEMA_INSTANCE_PAIRS),
        instances=len(SCHEMA_INSTANCE_PAIRS),
        digest_references=digest_references,
        markdown_files=len(files),
        markdown_links=links,
        migrated_idps=migrations,
        canonicalization_vector_checks=vector_checks,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--json", action="store_true", help="emit the success report as JSON")
    args = parser.parse_args(argv)
    try:
        report = validate_repository(args.root)
    except Exception as exc:  # CLI boundary: retain a concise CI annotation
        print(f"CPAS v2 validation failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(asdict(report), sort_keys=True))
    else:
        print(
            "CPAS v2 validation passed: "
            f"{report.schemas} schemas/examples, "
            f"{report.digest_references} digest references, "
            f"{report.markdown_links} local links in {report.markdown_files} files, "
            f"{report.migrated_idps} migrated IDP v1 declarations, "
            f"{report.canonicalization_vector_checks} canonicalization vector checks"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
