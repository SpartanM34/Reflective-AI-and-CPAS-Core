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
from cpas.evaluation import (  # noqa: E402
    DRIFT_CATEGORIES,
    compare_runtime_transcripts,
    validate_manifest,
    validate_report,
    validate_transcript,
)
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
from cpas.runtime import TranscriptRuntimeAdapter  # noqa: E402
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
    (
        "schemas/runtime-evaluation-manifest-v1.0.schema.json",
        "compliance-tests/runtime-evaluation/clarence-9-v1/manifest.json",
    ),
    (
        "schemas/runtime-transcript-v1.0.schema.json",
        "compliance-tests/runtime-evaluation/clarence-9-v1/baseline-transcript.json",
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
    "docs/operations/*.md",
    "docs/security/*.md",
    "docs/evaluation/*.md",
    "compliance-tests/runtime-evaluation/**/*.md",
    "instances/current/*.md",
    "instances/legacy/*.md",
    "migrations/CPAS-v1.1-to-v2.0.md",
    "migrations/canonicalization-v1-to-jcs-v1.md",
    "migrations/idp-v2-draft-governance.md",
    "migrations/FileDKAStore-to-SQLite-v1.md",
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
    runtime_evaluation_checks: int


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


def validate_all_schemas(root: Path) -> int:
    paths = sorted((root / "schemas").glob("*.schema.json"))
    if not paths:
        raise ValidationFailure("no CPAS v2 schemas discovered")
    for path in paths:
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
    return len(paths)


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


def validate_runtime_evaluation(root: Path) -> tuple[int, int]:
    fixture_root = root / "compliance-tests/runtime-evaluation/clarence-9-v1"
    manifest = _object(root, str((fixture_root / "manifest.json").relative_to(root)))
    baseline = _object(
        root, str((fixture_root / "baseline-transcript.json").relative_to(root))
    )
    candidate = _object(
        root, str((fixture_root / "candidate-transcript.json").relative_to(root))
    )
    expected = _object(
        root, str((fixture_root / "expected-summary.json").relative_to(root))
    )
    validate_manifest(manifest)
    validate_transcript(baseline)
    validate_transcript(candidate)

    declaration_path = (root / manifest["declaration"]["path"]).resolve()
    try:
        declaration_path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValidationFailure(
            "runtime evaluation declaration reference escapes repository"
        ) from exc
    declaration = _object(root, str(declaration_path.relative_to(root)))
    require_file_digest(
        root,
        manifest["declaration"]["path"],
        manifest["declaration"]["artifact_digest"],
        owner="runtime evaluation manifest",
    )
    report = compare_runtime_transcripts(
        manifest,
        declaration,
        baseline,
        candidate,
        TranscriptRuntimeAdapter(baseline),
        TranscriptRuntimeAdapter(candidate),
        evaluated_at=expected["evaluated_at"],
        declaration_path=declaration_path,
    )
    validate_report(report, manifest=manifest)

    exact_values = {
        "manifest_digest": report["manifest"]["digest"],
        "baseline_transcript_digest": report["baseline_runtime"][
            "transcript_digest"
        ],
        "baseline_configuration_digest": report["baseline_runtime"]["runtime"][
            "configuration_digest"
        ],
        "candidate_transcript_digest": report["candidate_runtime"][
            "transcript_digest"
        ],
        "candidate_configuration_digest": report["candidate_runtime"]["runtime"][
            "configuration_digest"
        ],
        "report_digest": report["integrity"]["digest"],
        "machine_disposition": report["threshold_evaluation"][
            "machine_disposition"
        ],
        "blocking_reasons": report["threshold_evaluation"]["blocking_reasons"],
        "human_review_status": report["human_review"]["status"],
        "final_disposition": report["final_disposition"],
        "identity_proof": report["identity_assessment"]["identity_proof"],
    }
    for field, actual in exact_values.items():
        if expected.get(field) != actual:
            raise ValidationFailure(
                f"runtime evaluation expected {field}={expected.get(field)!r}, got {actual!r}"
            )
    drift_counts = {name: len(report["drift"][name]) for name in DRIFT_CATEGORIES}
    if expected["drift_item_counts"] != drift_counts:
        raise ValidationFailure("runtime evaluation drift item counts changed")
    failure_counts = {
        name: report["threshold_evaluation"]["category_results"][name][
            "candidate_required_failures"
        ]
        for name in DRIFT_CATEGORIES
    }
    if expected["candidate_required_failure_counts"] != failure_counts:
        raise ValidationFailure("runtime evaluation required failure counts changed")
    if expected.get("assurance") != "synthetic-fixture-conformance-only":
        raise ValidationFailure("runtime evaluation fixture assurance label changed")
    if baseline["assurance"] != "synthetic_fixture" or candidate[
        "assurance"
    ] != "synthetic_fixture":
        raise ValidationFailure("runtime conformance vectors must remain synthetic")

    checks = 4 + len(manifest["cases"]) + len(manifest["capability_probes"]) + len(
        DRIFT_CATEGORIES
    )
    return checks, 1


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
    schema_count = validate_all_schemas(root)
    validate_schema_instances(root)
    digest_references = validate_semantics_and_integrity(root)
    runtime_checks, runtime_digest_references = validate_runtime_evaluation(root)
    digest_references += runtime_digest_references
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
        schemas=schema_count,
        instances=len(SCHEMA_INSTANCE_PAIRS) + 2,
        digest_references=digest_references,
        markdown_files=len(files),
        markdown_links=links,
        migrated_idps=migrations,
        canonicalization_vector_checks=vector_checks,
        runtime_evaluation_checks=runtime_checks,
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
            f"{report.canonicalization_vector_checks} canonicalization vector checks, "
            f"{report.runtime_evaluation_checks} runtime evaluation checks"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
