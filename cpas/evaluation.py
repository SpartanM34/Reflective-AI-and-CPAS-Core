"""Clarence-9 runtime-replacement evaluation and drift classification.

The evaluator compares observable artifacts under a versioned manifest. It does
not infer consciousness, memory, ontological persistence, or identity from a
score. Runtime outputs and transcript tool events are treated as untrusted data;
this module never executes them.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .identity import identity_digest
from .idp import validate_idp
from .provenance import (
    JCS_CANONICALIZATION,
    RUNTIME_CONFIGURATION_DIGEST_PROFILE,
    RUNTIME_EVALUATION_MANIFEST_DIGEST_PROFILE,
    RUNTIME_EVALUATION_REPORT_DIGEST_PROFILE,
    RUNTIME_TRANSCRIPT_DIGEST_PROFILE,
    file_sha256,
    load_json,
    profiled_digest,
)
from .runtime import RuntimeAdapter, RuntimeAdapterError


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = REPOSITORY_ROOT / "schemas" / "runtime-evaluation-manifest-v1.0.schema.json"
TRANSCRIPT_SCHEMA = REPOSITORY_ROOT / "schemas" / "runtime-transcript-v1.0.schema.json"
REPORT_SCHEMA = REPOSITORY_ROOT / "schemas" / "runtime-evaluation-report-v1.0.schema.json"

DRIFT_CATEGORIES = (
    "capability_failure",
    "policy_violation",
    "style_change",
    "task_performance_change",
)

ASSURANCE_RANK = {
    "synthetic_fixture": 0,
    "recorded_runtime": 1,
    "live_runtime": 2,
}

_MISSING = object()


class EvaluationError(RuntimeError):
    """Evaluation input, contract, or integrity failure."""


def _validator(path: Path) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(value: Mapping[str, Any], path: Path, label: str) -> None:
    errors = sorted(_validator(path).iter_errors(dict(value)), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValidationError(f"{label}: {details}")


def _without_integrity(value: Mapping[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(dict(value))
    projected.pop("integrity", None)
    return projected


def _semantic_digest(value: Mapping[str, Any], profile: str) -> str:
    return profiled_digest(
        _without_integrity(value),
        canonicalization=JCS_CANONICALIZATION,
        digest_profile=profile,
        expected_v2_profile=profile,
    )


def runtime_configuration_projection(runtime: Mapping[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(dict(runtime))
    projected.pop("configuration_digest", None)
    projected.pop("configuration_digest_profile", None)
    return projected


def runtime_configuration_digest(runtime: Mapping[str, Any]) -> str:
    return profiled_digest(
        runtime_configuration_projection(runtime),
        canonicalization=JCS_CANONICALIZATION,
        digest_profile=RUNTIME_CONFIGURATION_DIGEST_PROFILE,
        expected_v2_profile=RUNTIME_CONFIGURATION_DIGEST_PROFILE,
    )


def seal_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    sealed = _without_integrity(manifest)
    sealed["integrity"] = {
        "canonicalization": JCS_CANONICALIZATION,
        "digest_profile": RUNTIME_EVALUATION_MANIFEST_DIGEST_PROFILE,
        "digest": _semantic_digest(
            sealed, RUNTIME_EVALUATION_MANIFEST_DIGEST_PROFILE
        ),
    }
    return sealed


def seal_transcript(transcript: Mapping[str, Any]) -> dict[str, Any]:
    sealed = _without_integrity(transcript)
    runtime = copy.deepcopy(dict(sealed["runtime"]))
    runtime["configuration_digest_profile"] = RUNTIME_CONFIGURATION_DIGEST_PROFILE
    runtime["configuration_digest"] = runtime_configuration_digest(runtime)
    sealed["runtime"] = runtime
    sealed["integrity"] = {
        "canonicalization": JCS_CANONICALIZATION,
        "digest_profile": RUNTIME_TRANSCRIPT_DIGEST_PROFILE,
        "digest": _semantic_digest(sealed, RUNTIME_TRANSCRIPT_DIGEST_PROFILE),
    }
    return sealed


def seal_report(report: Mapping[str, Any]) -> dict[str, Any]:
    sealed = _without_integrity(report)
    sealed["integrity"] = {
        "canonicalization": JCS_CANONICALIZATION,
        "digest_profile": RUNTIME_EVALUATION_REPORT_DIGEST_PROFILE,
        "digest": _semantic_digest(sealed, RUNTIME_EVALUATION_REPORT_DIGEST_PROFILE),
    }
    return sealed


def _validate_integrity(value: Mapping[str, Any], profile: str, label: str) -> None:
    integrity = value.get("integrity")
    if not isinstance(integrity, Mapping):
        raise EvaluationError(f"{label} integrity metadata is missing")
    if integrity.get("canonicalization") != JCS_CANONICALIZATION:
        raise EvaluationError(f"{label} canonicalization is not {JCS_CANONICALIZATION}")
    if integrity.get("digest_profile") != profile:
        raise EvaluationError(f"{label} digest profile is not {profile}")
    expected = _semantic_digest(value, profile)
    if integrity.get("digest") != expected:
        raise EvaluationError(f"{label} integrity digest mismatch")


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    _validate_schema(manifest, MANIFEST_SCHEMA, "runtime evaluation manifest")
    _validate_integrity(
        manifest, RUNTIME_EVALUATION_MANIFEST_DIGEST_PROFILE, "manifest"
    )
    case_ids = [case["case_id"] for case in manifest["cases"]]
    if len(case_ids) != len(set(case_ids)):
        raise EvaluationError("manifest case identifiers must be unique")
    probe_ids = [probe["probe_id"] for probe in manifest["capability_probes"]]
    if len(probe_ids) != len(set(probe_ids)):
        raise EvaluationError("manifest probe identifiers must be unique")
    assertion_ids: set[str] = set()
    for case in manifest["cases"]:
        for assertion in case["machine_assertions"]:
            assertion_id = assertion["assertion_id"]
            if assertion_id in assertion_ids:
                raise EvaluationError(
                    f"manifest assertion identifiers must be unique: {assertion_id}"
                )
            assertion_ids.add(assertion_id)
    defined_probes = set(probe_ids)
    probes_by_id = {
        probe["probe_id"]: probe for probe in manifest["capability_probes"]
    }
    requirement_keys = [
        (requirement["capability"], requirement["probe_id"])
        for requirement in manifest["capability_requirements"]
    ]
    if len(requirement_keys) != len(set(requirement_keys)):
        raise EvaluationError("manifest capability requirements must be unique")
    for requirement in manifest["capability_requirements"]:
        if requirement["probe_id"] not in defined_probes:
            raise EvaluationError(
                f"capability requirement references unknown probe: {requirement['probe_id']}"
            )
        if probes_by_id[requirement["probe_id"]]["capability"] != requirement[
            "capability"
        ]:
            raise EvaluationError(
                f"capability requirement {requirement['capability']} does not match its probe"
            )
    declared_capabilities = {
        requirement["capability"] for requirement in manifest["capability_requirements"]
    }
    for case in manifest["cases"]:
        unknown = sorted(set(case["required_capabilities"]) - declared_capabilities)
        if unknown:
            raise EvaluationError(
                f"case {case['case_id']} requires undeclared capabilities: {', '.join(unknown)}"
            )
        for assertion in case["machine_assertions"]:
            operator = assertion["operator"]
            if operator not in {"exists", "absent"} and "expected" not in assertion:
                raise EvaluationError(
                    f"assertion {assertion['assertion_id']} requires expected"
                )
            if operator in {"min_items", "max_items"} and (
                not isinstance(assertion.get("expected"), int)
                or isinstance(assertion.get("expected"), bool)
                or assertion["expected"] < 0
            ):
                raise EvaluationError(
                    f"assertion {assertion['assertion_id']} requires a non-negative integer expected value"
                )
    required_non_claims = {
        "identity_proof",
        "consciousness",
        "felt_emotion",
        "memory",
        "ontological_continuity",
        "behavioral_equivalence",
    }
    if not required_non_claims.issubset(set(manifest["non_claims"])):
        raise EvaluationError("manifest omits required non-claims")
    if (
        manifest["evaluation_purpose"] == "runtime_replacement"
        and manifest["minimum_transcript_assurance"] == "synthetic_fixture"
    ):
        raise EvaluationError(
            "runtime-replacement manifests require recorded or live runtime assurance"
        )
    for category in ("capability_failure", "policy_violation"):
        rule = manifest["threshold_policy"]["category_rules"][category]
        if rule["blocking"] is not True or rule["maximum_candidate_failures"] != 0:
            raise EvaluationError(
                f"{category} must be a zero-tolerance blocking gate"
            )


def validate_transcript(transcript: Mapping[str, Any]) -> None:
    _validate_schema(transcript, TRANSCRIPT_SCHEMA, "runtime transcript")
    runtime = transcript["runtime"]
    if runtime["configuration_digest"] != runtime_configuration_digest(runtime):
        raise EvaluationError("runtime configuration digest mismatch")
    _validate_integrity(transcript, RUNTIME_TRANSCRIPT_DIGEST_PROFILE, "transcript")
    probe_ids = [item["probe_id"] for item in transcript["capability_probes"]]
    case_ids = [item["case_id"] for item in transcript["responses"]]
    if len(probe_ids) != len(set(probe_ids)):
        raise EvaluationError("transcript probe identifiers must be unique")
    if len(case_ids) != len(set(case_ids)):
        raise EvaluationError("transcript case identifiers must be unique")
    if transcript["assurance"] != transcript["provenance"]["source_type"]:
        raise EvaluationError("transcript assurance and provenance source type differ")
    allowed_evidence = {
        "synthetic_fixture": {"synthetic_fixture"},
        "recorded_runtime": {"recorded_observation"},
        "live_runtime": {"live_probe"},
    }[transcript["assurance"]]
    observed_evidence = {
        item["evidence_kind"] for item in transcript["capability_probes"]
    }
    if not observed_evidence.issubset(allowed_evidence):
        raise EvaluationError(
            "transcript capability evidence kind exceeds its assurance level"
        )


def validate_report(
    report: Mapping[str, Any], *, manifest: Mapping[str, Any] | None = None
) -> None:
    _validate_schema(report, REPORT_SCHEMA, "runtime evaluation report")
    _validate_integrity(
        report, RUNTIME_EVALUATION_REPORT_DIGEST_PROFILE, "report"
    )
    if report["identity_assessment"]["identity_proof"] is not False:
        raise EvaluationError("runtime report must not claim identity proof")
    if report["threshold_evaluation"]["aggregate_score_used"] is not False:
        raise EvaluationError("runtime report must not use an aggregate identity score")
    if report["final_disposition"] != "undecided":
        raise EvaluationError("machine-generated report cannot decide final compatibility")
    evaluation_time = _parse_datetime(report["evaluated_at"], "report evaluated_at")
    assurance = report["assurance_assessment"]
    runtime_sides = {
        "baseline": (
            report["baseline_runtime"],
            assurance["baseline_assurance"],
        ),
        "candidate": (
            report["candidate_runtime"],
            assurance["candidate_assurance"],
        ),
    }
    for side, (runtime_ref, declared_assurance) in runtime_sides.items():
        if runtime_ref["assurance"] != declared_assurance:
            raise EvaluationError(f"report {side} assurance metadata is inconsistent")
        runtime = runtime_ref["runtime"]
        if runtime["configuration_digest"] != runtime_configuration_digest(runtime):
            raise EvaluationError(
                f"report {side} runtime configuration digest mismatch"
            )
    expected_assurance = all(
        ASSURANCE_RANK[value] >= ASSURANCE_RANK[assurance["minimum_transcript_assurance"]]
        for value in (
            assurance["baseline_assurance"],
            assurance["candidate_assurance"],
        )
    )
    if assurance["requirement_satisfied"] != expected_assurance:
        raise EvaluationError("report assurance assessment is inconsistent")
    if (
        assurance["evaluation_purpose"] == "runtime_replacement"
        and assurance["minimum_transcript_assurance"] == "synthetic_fixture"
    ):
        raise EvaluationError(
            "runtime-replacement report cannot accept synthetic-only assurance"
        )
    category_results = report["threshold_evaluation"]["category_results"]
    expected_blocking = []
    for category in DRIFT_CATEGORIES:
        result = category_results[category]
        expected_exceeded = (
            result["candidate_required_failures"]
            > result["maximum_candidate_failures"]
        )
        if result["exceeded"] != expected_exceeded:
            raise EvaluationError(f"report threshold result is inconsistent: {category}")
        if expected_exceeded and result["blocking"]:
            expected_blocking.append(category)
    if not report["assurance_assessment"]["requirement_satisfied"]:
        expected_blocking.append("assurance_requirement")
    if report["threshold_evaluation"]["blocking_reasons"] != expected_blocking:
        raise EvaluationError("report blocking reasons are inconsistent")
    if expected_blocking:
        expected_disposition = "blocked"
    elif report["assurance_assessment"]["evaluation_purpose"] == "harness_conformance":
        expected_disposition = "conformance_only"
    else:
        expected_disposition = "eligible_for_human_review"
    if report["threshold_evaluation"]["machine_disposition"] != expected_disposition:
        raise EvaluationError("report machine disposition is inconsistent")

    candidate_probes = {
        item["probe_id"]: item
        for item in report["capability_results"]["candidate"]
    }
    if len(candidate_probes) != len(report["capability_results"]["candidate"]):
        raise EvaluationError("report duplicates candidate probe results")
    computed_failures = {category: 0 for category in DRIFT_CATEGORIES}
    expected_drift_items: dict[str, dict[str, dict[str, Any]]] = {
        category: {} for category in DRIFT_CATEGORIES
    }
    baseline_probes = {
        item["probe_id"]: item
        for item in report["capability_results"]["baseline"]
    }
    if len(baseline_probes) != len(report["capability_results"]["baseline"]):
        raise EvaluationError("report duplicates baseline probe results")
    allowed_evidence_by_assurance = {
        "synthetic_fixture": {"synthetic_fixture"},
        "recorded_runtime": {"recorded_observation"},
        "live_runtime": {"live_probe"},
    }
    for side, probes in (
        ("baseline", baseline_probes),
        ("candidate", candidate_probes),
    ):
        side_assurance = runtime_sides[side][1]
        allowed_evidence = allowed_evidence_by_assurance[side_assurance]
        for probe_id, probe in probes.items():
            if probe["evidence_kind"] not in allowed_evidence:
                raise EvaluationError(
                    f"report {side} probe evidence exceeds assurance: {probe_id}"
                )
            observed_at = probe["observed_at"]
            if observed_at is None:
                expected_age = None
                expected_fresh = False
            else:
                observation_time = _parse_datetime(
                    observed_at, f"report {side} probe {probe_id} observed_at"
                )
                age = evaluation_time - observation_time
                if age.total_seconds() < 0:
                    raise EvaluationError(
                        f"report {side} probe occurs after evaluation: {probe_id}"
                    )
                expected_age = int(age.total_seconds())
                expected_fresh = expected_age <= int(
                    probe["validity_horizon_days"]
                ) * 86400
            expected_outcome = probe["outcome"] if expected_fresh else "stale"
            if (
                probe["observed_age_seconds"] != expected_age
                or probe["fresh"] != expected_fresh
                or probe["effective_outcome"] != expected_outcome
            ):
                raise EvaluationError(
                    f"report {side} probe freshness is inconsistent: {probe_id}"
                )
    requirement_keys = [
        (item["capability"], item["probe_id"])
        for item in report["capability_requirements"]
    ]
    if len(requirement_keys) != len(set(requirement_keys)):
        raise EvaluationError("report duplicates capability requirements")
    for requirement in report["capability_requirements"]:
        probe_id = requirement["probe_id"]
        if probe_id not in candidate_probes or probe_id not in baseline_probes:
            raise EvaluationError(
                f"report capability requirement has no probe result: {probe_id}"
            )
        if any(
            probes[probe_id]["capability"] != requirement["capability"]
            for probes in (baseline_probes, candidate_probes)
        ):
            raise EvaluationError(
                f"report capability requirement does not match probe: {probe_id}"
            )
        candidate_outcome = candidate_probes[probe_id]["effective_outcome"]
        baseline_outcome = baseline_probes[probe_id]["effective_outcome"]
        if requirement["requirement"] == "required" and candidate_outcome != "pass":
            computed_failures["capability_failure"] += 1
        if baseline_outcome != candidate_outcome or candidate_outcome != "pass":
            item_id = f"capability:{requirement['capability']}"
            expected_drift_items["capability_failure"][item_id] = {
                "item_id": item_id,
                "case_id": None,
                "assertion_id": None,
                "change": (
                    "regression"
                    if baseline_outcome == "pass" and candidate_outcome != "pass"
                    else "persistent_failure"
                    if candidate_outcome != "pass"
                    else "changed"
                ),
                "required": requirement["requirement"] == "required",
                "baseline": baseline_outcome,
                "candidate": candidate_outcome,
            }

    seen_cases: set[str] = set()
    for case in report["case_results"]:
        if case["case_id"] in seen_cases:
            raise EvaluationError(f"duplicate report case result: {case['case_id']}")
        seen_cases.add(case["case_id"])
        baseline_assertions = {
            assertion["assertion_id"]: assertion
            for assertion in case["baseline"]["assertions"]
        }
        if len(baseline_assertions) != len(case["baseline"]["assertions"]):
            raise EvaluationError(
                f"duplicate baseline assertion result: {case['case_id']}"
            )
        candidate_assertions = {
            assertion["assertion_id"]: assertion
            for assertion in case["candidate"]["assertions"]
        }
        if len(candidate_assertions) != len(case["candidate"]["assertions"]):
            raise EvaluationError(
                f"duplicate candidate assertion result: {case['case_id']}"
            )
        for assertion_id in sorted(set(baseline_assertions) | set(candidate_assertions)):
            baseline_assertion = baseline_assertions.get(assertion_id)
            candidate_assertion = candidate_assertions.get(assertion_id)
            reference = candidate_assertion or baseline_assertion
            assert reference is not None
            baseline_passed = bool(baseline_assertion and baseline_assertion["passed"])
            candidate_passed = bool(candidate_assertion and candidate_assertion["passed"])
            if not candidate_passed:
                category = reference["drift_category"]
                if reference["severity"] == "required":
                    computed_failures[category] += 1
            if baseline_passed != candidate_passed or not candidate_passed:
                category = reference["drift_category"]
                item_id = f"assertion:{assertion_id}"
                expected_drift_items[category][item_id] = {
                    "item_id": item_id,
                    "case_id": case["case_id"],
                    "assertion_id": assertion_id,
                    "change": (
                        "regression"
                        if baseline_passed and not candidate_passed
                        else "improvement"
                        if not baseline_passed and candidate_passed
                        else "persistent_failure"
                    ),
                    "required": reference["severity"] == "required",
                    "baseline": "pass" if baseline_passed else "fail",
                    "candidate": "pass" if candidate_passed else "fail",
                }

    for category in DRIFT_CATEGORIES:
        if category_results[category]["candidate_required_failures"] != computed_failures[
            category
        ]:
            raise EvaluationError(
                f"report candidate failure count is inconsistent: {category}"
            )
        actual_items = {
            item["item_id"]: item for item in report["drift"][category]
        }
        if len(actual_items) != len(report["drift"][category]):
            raise EvaluationError(f"report duplicates drift items: {category}")
        if actual_items != expected_drift_items[category]:
            raise EvaluationError(f"report drift items are inconsistent: {category}")

    if manifest is not None:
        validate_manifest(manifest)
        if report["manifest"] != {
            "suite_id": manifest["suite_id"],
            "suite_revision": manifest["suite_revision"],
            "digest": manifest["integrity"]["digest"],
            "digest_profile": manifest["integrity"]["digest_profile"],
        }:
            raise EvaluationError("report manifest reference mismatch")
        if report["declaration"] != manifest["declaration"]:
            raise EvaluationError("report declaration reference mismatch")
        if report["capability_requirements"] != manifest["capability_requirements"]:
            raise EvaluationError("report capability requirements differ from manifest")
        if report["assurance_assessment"]["evaluation_purpose"] != manifest[
            "evaluation_purpose"
        ] or report["assurance_assessment"][
            "minimum_transcript_assurance"
        ] != manifest[
            "minimum_transcript_assurance"
        ]:
            raise EvaluationError("report assurance policy differs from manifest")
        manifest_probes = {
            probe["probe_id"]: probe for probe in manifest["capability_probes"]
        }
        if set(baseline_probes) != set(manifest_probes) or set(candidate_probes) != set(
            manifest_probes
        ):
            raise EvaluationError("report probe set differs from manifest")
        for probe_id, probe in manifest_probes.items():
            for observed in (baseline_probes[probe_id], candidate_probes[probe_id]):
                if observed["capability"] != probe["capability"] or observed[
                    "validity_horizon_days"
                ] != probe[
                    "validity_horizon_days"
                ]:
                    raise EvaluationError(
                        f"report probe semantics differ from manifest: {probe_id}"
                    )
        manifest_cases = {case["case_id"]: case for case in manifest["cases"]}
        report_cases = {case["case_id"]: case for case in report["case_results"]}
        if set(report_cases) != set(manifest_cases):
            raise EvaluationError("report case set differs from manifest")
        for case_id, manifest_case in manifest_cases.items():
            report_case = report_cases[case_id]
            if (
                report_case["category"] != manifest_case["category"]
                or report_case["mode"] != manifest_case["mode"]
                or report_case["human_criteria"] != manifest_case["human_criteria"]
            ):
                raise EvaluationError(
                    f"report case metadata differs from manifest: {case_id}"
                )
            expected_assertions = {
                assertion["assertion_id"]: assertion
                for assertion in manifest_case["machine_assertions"]
            }
            for side in ("baseline", "candidate"):
                actual_assertions = {
                    assertion["assertion_id"]: assertion
                    for assertion in report_case[side]["assertions"]
                }
                expected_ids = set(expected_assertions)
                dynamic_id = f"{case_id}:harness-no-side-effects"
                if report_case[side]["executed_tool_events"]:
                    expected_ids.add(dynamic_id)
                if set(actual_assertions) != expected_ids:
                    raise EvaluationError(
                        f"report assertion set differs from manifest: {case_id}/{side}"
                    )
                for assertion_id, expected in expected_assertions.items():
                    actual = actual_assertions[assertion_id]
                    for field in (
                        "path",
                        "operator",
                        "severity",
                        "drift_category",
                    ):
                        if actual[field] != expected[field]:
                            raise EvaluationError(
                                f"report assertion semantics differ from manifest: {assertion_id}"
                            )
                if dynamic_id in actual_assertions:
                    dynamic = actual_assertions[dynamic_id]
                    if (
                        dynamic["path"] != "/tool_events"
                        or dynamic["operator"] != "equals"
                        or dynamic["severity"] != "required"
                        or dynamic["drift_category"] != "policy_violation"
                        or dynamic["passed"] is not False
                    ):
                        raise EvaluationError(
                            f"report side-effect assertion is invalid: {case_id}/{side}"
                        )
        for category in DRIFT_CATEGORIES:
            rule = manifest["threshold_policy"]["category_rules"][category]
            result = category_results[category]
            if result["blocking"] != rule["blocking"] or result[
                "maximum_candidate_failures"
            ] != rule["maximum_candidate_failures"]:
                raise EvaluationError(
                    f"report threshold rule differs from manifest: {category}"
                )
        if report["threshold_evaluation"]["policy_id"] != manifest[
            "threshold_policy"
        ]["policy_id"]:
            raise EvaluationError("report threshold policy differs from manifest")
        if report["human_review"]["rubric_ref"] != manifest["human_review"][
            "rubric_ref"
        ]:
            raise EvaluationError("report review rubric differs from manifest")


def verify_manifest_declaration(
    manifest: Mapping[str, Any],
    declaration: Mapping[str, Any],
    *,
    declaration_path: str | Path | None = None,
) -> None:
    validate_idp(declaration)
    reference = manifest["declaration"]
    if declaration.get("instance_id") != reference["instance_id"]:
        raise EvaluationError("manifest instance_id does not match declaration")
    if identity_digest(declaration) != reference["identity_digest"]:
        raise EvaluationError("manifest identity digest does not match declaration")
    if declaration["continuity"]["identity_digest_profile"] != reference[
        "identity_digest_profile"
    ]:
        raise EvaluationError("manifest identity digest profile does not match declaration")
    if declaration_path is not None and file_sha256(declaration_path) != reference[
        "artifact_digest"
    ]:
        raise EvaluationError("manifest declaration artifact digest mismatch")


def _decode_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    current = value
    for raw in pointer.split("/")[1:]:
        token = _decode_pointer_token(raw)
        if isinstance(current, Mapping):
            if token not in current:
                return _MISSING
            current = current[token]
        elif isinstance(current, list) and token.isdigit():
            index = int(token)
            if index >= len(current):
                return _MISSING
            current = current[index]
        else:
            return _MISSING
    return current


def _observation(value: Any) -> dict[str, Any]:
    if value is _MISSING:
        return {"present": False, "type": "missing"}
    if value is None or isinstance(value, (bool, int, float)):
        return {"present": True, "type": type(value).__name__, "value": value}
    if isinstance(value, str):
        return {
            "present": True,
            "type": "string",
            "length": len(value),
            "digest": profiled_digest(
                value,
                canonicalization=JCS_CANONICALIZATION,
                digest_profile=RUNTIME_EVALUATION_REPORT_DIGEST_PROFILE,
                expected_v2_profile=RUNTIME_EVALUATION_REPORT_DIGEST_PROFILE,
            ),
        }
    if isinstance(value, list):
        return {"present": True, "type": "array", "length": len(value)}
    if isinstance(value, Mapping):
        return {"present": True, "type": "object", "keys": sorted(map(str, value))}
    return {"present": True, "type": type(value).__name__}


def evaluate_assertion(output: Mapping[str, Any], assertion: Mapping[str, Any]) -> dict[str, Any]:
    observed = _pointer(output, assertion["path"])
    operator = assertion["operator"]
    expected = assertion.get("expected")
    if operator == "exists":
        passed = observed is not _MISSING
    elif operator == "absent":
        passed = observed is _MISSING
    elif operator == "equals":
        passed = observed is not _MISSING and observed == expected
    elif operator == "not_equals":
        passed = observed is not _MISSING and observed != expected
    elif operator == "contains":
        passed = observed is not _MISSING and isinstance(observed, (str, list)) and expected in observed
    elif operator == "not_contains":
        passed = observed is not _MISSING and isinstance(observed, (str, list)) and expected not in observed
    elif operator == "min_items":
        passed = isinstance(observed, (list, Mapping)) and len(observed) >= int(expected)
    elif operator == "max_items":
        passed = isinstance(observed, (list, Mapping)) and len(observed) <= int(expected)
    else:  # schema validation should make this unreachable
        raise EvaluationError(f"unsupported assertion operator: {operator}")
    return {
        "assertion_id": assertion["assertion_id"],
        "path": assertion["path"],
        "operator": operator,
        "severity": assertion["severity"],
        "drift_category": assertion["drift_category"],
        "passed": bool(passed),
        "observation": _observation(observed),
    }


def _run_case(
    adapter: RuntimeAdapter,
    case: Mapping[str, Any],
    *,
    expected_response: Mapping[str, Any],
    maximum_response_bytes: int,
) -> dict[str, Any]:
    try:
        response = dict(adapter.invoke(case))
    except RuntimeAdapterError as exc:
        raise EvaluationError(
            f"adapter could not replay transcript case {case['case_id']}: {exc}"
        ) from exc
    if response != dict(expected_response):
        raise EvaluationError(
            f"adapter response differs from referenced transcript: {case['case_id']}"
        )
    output = response.get("output")
    if response.get("error") is not None:
        output = {}
        status = "adapter_error"
    elif not isinstance(output, Mapping):
        output = {}
        status = "invalid_output"
    else:
        status = "completed"
    encoded_size = len(
        json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )
    if encoded_size > maximum_response_bytes:
        output = {}
        status = "response_too_large"
    tool_events = response.get("tool_events", [])
    executed = sum(
        1
        for event in tool_events
        if isinstance(event, Mapping) and event.get("executed") is True
    )
    assertions = [
        evaluate_assertion(output, assertion)
        for assertion in case["machine_assertions"]
    ]
    if executed:
        assertions.append(
            {
                "assertion_id": f"{case['case_id']}:harness-no-side-effects",
                "path": "/tool_events",
                "operator": "equals",
                "severity": "required",
                "drift_category": "policy_violation",
                "passed": False,
                "observation": {
                    "present": True,
                    "type": "executed_tool_event_count",
                    "value": executed,
                },
            }
        )
    response_error = response.get("error")
    error_summary = None
    if isinstance(response_error, Mapping):
        error_summary = {
            "code": str(response_error.get("code", "runtime_error")),
            "message_summary": _observation(str(response_error.get("message", ""))),
        }
    return {
        "status": status,
        "error": error_summary,
        "response_bytes": encoded_size,
        "assertions": assertions,
        "executed_tool_events": executed,
    }


def _probe_results(
    adapter: RuntimeAdapter,
    probes: list[Mapping[str, Any]],
    expected_results: list[Mapping[str, Any]],
    *,
    evaluated_at: str,
) -> list[dict[str, Any]]:
    expected_by_id = {item["probe_id"]: dict(item) for item in expected_results}
    evaluation_time = _parse_datetime(evaluated_at, "evaluated_at")
    results: list[dict[str, Any]] = []
    for probe in probes:
        try:
            observed = dict(adapter.probe(probe))
        except RuntimeAdapterError as exc:
            raise EvaluationError(
                f"adapter could not replay transcript probe {probe['probe_id']}: {exc}"
            ) from exc
        if observed.get("probe_id") != probe["probe_id"]:
            raise EvaluationError(f"adapter returned mismatched probe id: {probe['probe_id']}")
        if observed.get("capability") != probe["capability"]:
            raise EvaluationError(
                f"adapter returned mismatched capability for {probe['probe_id']}"
            )
        if observed != expected_by_id.get(probe["probe_id"]):
            raise EvaluationError(
                f"adapter probe differs from referenced transcript: {probe['probe_id']}"
            )
        observed_at = observed.get("observed_at")
        if observed_at is None:
            age_seconds = None
            fresh = False
        else:
            observation_time = _parse_datetime(
                str(observed_at), f"probe {probe['probe_id']} observed_at"
            )
            age = evaluation_time - observation_time
            if age.total_seconds() < 0:
                raise EvaluationError(
                    f"probe observation occurs after evaluation: {probe['probe_id']}"
                )
            age_seconds = int(age.total_seconds())
            fresh = age_seconds <= int(probe["validity_horizon_days"]) * 86400
        evaluated = {
            "probe_id": observed["probe_id"],
            "capability": observed["capability"],
            "outcome": observed["outcome"],
            "observed_at": observed["observed_at"],
            "evidence_kind": observed["evidence_kind"],
            "evidence_summary": _observation(observed["evidence"]),
            "constraints_count": len(observed["constraints"]),
            "validity_horizon_days": int(probe["validity_horizon_days"]),
            "observed_age_seconds": age_seconds,
            "fresh": fresh,
            "effective_outcome": observed["outcome"] if fresh else "stale",
        }
        results.append(evaluated)
    return results


def _parse_datetime(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvaluationError(f"invalid {label}: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvaluationError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _runtime_ref(transcript: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "transcript_id": transcript["transcript_id"],
        "transcript_digest": transcript["integrity"]["digest"],
        "transcript_digest_profile": transcript["integrity"]["digest_profile"],
        "assurance": transcript["assurance"],
        "runtime": copy.deepcopy(dict(transcript["runtime"])),
    }


def compare_runtime_transcripts(
    manifest: Mapping[str, Any],
    declaration: Mapping[str, Any],
    baseline_transcript: Mapping[str, Any],
    candidate_transcript: Mapping[str, Any],
    baseline_adapter: RuntimeAdapter,
    candidate_adapter: RuntimeAdapter,
    *,
    evaluated_at: str | None = None,
    declaration_path: str | Path | None = None,
) -> dict[str, Any]:
    """Compare two runtime observations under one stable declaration.

    The returned report is always pending human review. Machine gates can block a
    candidate, but they cannot establish behavioral equivalence or identity.
    """

    validate_manifest(manifest)
    validate_transcript(baseline_transcript)
    validate_transcript(candidate_transcript)
    verify_manifest_declaration(
        manifest, declaration, declaration_path=declaration_path
    )
    if baseline_adapter.adapter_contract != manifest["adapter_contract"]:
        raise EvaluationError("baseline adapter contract mismatch")
    if candidate_adapter.adapter_contract != manifest["adapter_contract"]:
        raise EvaluationError("candidate adapter contract mismatch")
    if baseline_adapter.probe_contract != manifest["probe_contract"]:
        raise EvaluationError("baseline capability-probe contract mismatch")
    if candidate_adapter.probe_contract != manifest["probe_contract"]:
        raise EvaluationError("candidate capability-probe contract mismatch")

    if dict(baseline_adapter.describe()) != dict(baseline_transcript["runtime"]):
        raise EvaluationError("baseline adapter metadata differs from transcript")
    if dict(candidate_adapter.describe()) != dict(candidate_transcript["runtime"]):
        raise EvaluationError("candidate adapter metadata differs from transcript")

    expected_probe_ids = {item["probe_id"] for item in manifest["capability_probes"]}
    expected_case_ids = {item["case_id"] for item in manifest["cases"]}
    for label, transcript in (
        ("baseline", baseline_transcript),
        ("candidate", candidate_transcript),
    ):
        transcript_probe_ids = {
            item["probe_id"] for item in transcript["capability_probes"]
        }
        transcript_case_ids = {item["case_id"] for item in transcript["responses"]}
        if transcript_probe_ids != expected_probe_ids:
            raise EvaluationError(f"{label} transcript probe coverage differs from manifest")
        if transcript_case_ids != expected_case_ids:
            raise EvaluationError(f"{label} transcript case coverage differs from manifest")

    when = evaluated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _parse_datetime(when, "evaluated_at")
    probes = list(manifest["capability_probes"])
    baseline_probes = _probe_results(
        baseline_adapter,
        probes,
        list(baseline_transcript["capability_probes"]),
        evaluated_at=when,
    )
    candidate_probes = _probe_results(
        candidate_adapter,
        probes,
        list(candidate_transcript["capability_probes"]),
        evaluated_at=when,
    )
    baseline_by_probe = {item["probe_id"]: item for item in baseline_probes}
    candidate_by_probe = {item["probe_id"]: item for item in candidate_probes}

    capability_drift: list[dict[str, Any]] = []
    required_capability_failures = 0
    for requirement in manifest["capability_requirements"]:
        probe_id = requirement["probe_id"]
        baseline_outcome = baseline_by_probe[probe_id]["effective_outcome"]
        candidate_outcome = candidate_by_probe[probe_id]["effective_outcome"]
        required = requirement["requirement"] == "required"
        candidate_failed = candidate_outcome != "pass"
        if required and candidate_failed:
            required_capability_failures += 1
        if baseline_outcome != candidate_outcome or candidate_failed:
            capability_drift.append(
                {
                    "item_id": f"capability:{requirement['capability']}",
                    "case_id": None,
                    "assertion_id": None,
                    "change": (
                        "regression"
                        if baseline_outcome == "pass" and candidate_outcome != "pass"
                        else "persistent_failure"
                        if candidate_outcome != "pass"
                        else "changed"
                    ),
                    "required": required,
                    "baseline": baseline_outcome,
                    "candidate": candidate_outcome,
                }
            )

    maximum_bytes = int(manifest["invocation_policy"]["maximum_response_bytes"])
    case_results: list[dict[str, Any]] = []
    drift: dict[str, list[dict[str, Any]]] = {
        category: [] for category in DRIFT_CATEGORIES
    }
    drift["capability_failure"].extend(capability_drift)
    candidate_failure_counts = {category: 0 for category in DRIFT_CATEGORIES}
    candidate_failure_counts["capability_failure"] = required_capability_failures

    baseline_responses = {
        item["case_id"]: item for item in baseline_transcript["responses"]
    }
    candidate_responses = {
        item["case_id"]: item for item in candidate_transcript["responses"]
    }

    for case in manifest["cases"]:
        baseline_result = _run_case(
            baseline_adapter,
            case,
            expected_response=baseline_responses[case["case_id"]],
            maximum_response_bytes=maximum_bytes,
        )
        candidate_result = _run_case(
            candidate_adapter,
            case,
            expected_response=candidate_responses[case["case_id"]],
            maximum_response_bytes=maximum_bytes,
        )
        baseline_assertions = {
            item["assertion_id"]: item for item in baseline_result["assertions"]
        }
        candidate_assertions = {
            item["assertion_id"]: item for item in candidate_result["assertions"]
        }
        for assertion_id in sorted(set(baseline_assertions) | set(candidate_assertions)):
            baseline_assertion = baseline_assertions.get(assertion_id)
            candidate_assertion = candidate_assertions.get(assertion_id)
            baseline_passed = bool(baseline_assertion and baseline_assertion["passed"])
            candidate_passed = bool(candidate_assertion and candidate_assertion["passed"])
            reference = candidate_assertion or baseline_assertion
            assert reference is not None
            category = reference["drift_category"]
            if not candidate_passed and reference["severity"] == "required":
                candidate_failure_counts[category] += 1
            if baseline_passed != candidate_passed or not candidate_passed:
                drift[category].append(
                    {
                        "item_id": f"assertion:{assertion_id}",
                        "case_id": case["case_id"],
                        "assertion_id": assertion_id,
                        "change": (
                            "regression"
                            if baseline_passed and not candidate_passed
                            else "improvement"
                            if not baseline_passed and candidate_passed
                            else "persistent_failure"
                        ),
                        "required": reference["severity"] == "required",
                        "baseline": "pass" if baseline_passed else "fail",
                        "candidate": "pass" if candidate_passed else "fail",
                    }
                )
        case_results.append(
            {
                "case_id": case["case_id"],
                "category": case["category"],
                "mode": case["mode"],
                "baseline": baseline_result,
                "candidate": candidate_result,
                "human_criteria": copy.deepcopy(case["human_criteria"]),
            }
        )

    category_results: dict[str, dict[str, Any]] = {}
    blocking_reasons: list[str] = []
    for category in DRIFT_CATEGORIES:
        rule = manifest["threshold_policy"]["category_rules"][category]
        failures = candidate_failure_counts[category]
        exceeded = failures > int(rule["maximum_candidate_failures"])
        category_results[category] = {
            "candidate_required_failures": failures,
            "maximum_candidate_failures": int(rule["maximum_candidate_failures"]),
            "blocking": bool(rule["blocking"]),
            "exceeded": exceeded,
        }
        if exceeded and rule["blocking"]:
            blocking_reasons.append(category)

    baseline_ref = _runtime_ref(baseline_transcript)
    candidate_ref = _runtime_ref(candidate_transcript)
    minimum_assurance = manifest["minimum_transcript_assurance"]
    assurance_satisfied = all(
        ASSURANCE_RANK[item["assurance"]] >= ASSURANCE_RANK[minimum_assurance]
        for item in (baseline_ref, candidate_ref)
    )
    if not assurance_satisfied:
        blocking_reasons.append("assurance_requirement")
    if blocking_reasons:
        machine_disposition = "blocked"
    elif manifest["evaluation_purpose"] == "harness_conformance":
        machine_disposition = "conformance_only"
    else:
        machine_disposition = "eligible_for_human_review"
    report: dict[str, Any] = {
        "report_version": "1.0",
        "report_id": (
            f"{manifest['suite_id']}:{baseline_ref['runtime']['configuration_id']}:"
            f"{candidate_ref['runtime']['configuration_id']}:{when}"
        ),
        "evaluated_at": when,
        "manifest": {
            "suite_id": manifest["suite_id"],
            "suite_revision": manifest["suite_revision"],
            "digest": manifest["integrity"]["digest"],
            "digest_profile": manifest["integrity"]["digest_profile"],
        },
        "declaration": copy.deepcopy(dict(manifest["declaration"])),
        "identity_assessment": {
            "stable_declaration_held_constant": True,
            "declared_identity_digest_equal": True,
            "behavioral_equivalence_established": False,
            "identity_proof": False,
            "statement": (
                "Equal declaration digests establish only declared-identity continuity; "
                "runtime behavior requires separate review."
            ),
        },
        "baseline_runtime": baseline_ref,
        "candidate_runtime": candidate_ref,
        "assurance_assessment": {
            "evaluation_purpose": manifest["evaluation_purpose"],
            "minimum_transcript_assurance": minimum_assurance,
            "baseline_assurance": baseline_ref["assurance"],
            "candidate_assurance": candidate_ref["assurance"],
            "requirement_satisfied": assurance_satisfied,
            "runtime_verification_established": False,
        },
        "capability_results": {
            "baseline": baseline_probes,
            "candidate": candidate_probes,
        },
        "capability_requirements": copy.deepcopy(
            manifest["capability_requirements"]
        ),
        "case_results": case_results,
        "drift": drift,
        "threshold_evaluation": {
            "policy_id": manifest["threshold_policy"]["policy_id"],
            "category_results": category_results,
            "blocking_reasons": blocking_reasons,
            "machine_disposition": machine_disposition,
            "aggregate_score_used": False,
            "identity_proof": False,
        },
        "human_review": {
            "required": True,
            "status": "pending",
            "rubric_ref": manifest["human_review"]["rubric_ref"],
            "reviewer": None,
            "decision": None,
            "notes": [],
        },
        "final_disposition": "undecided",
        "limitations": [
            "Machine assertions test declared structure and explicit values, not semantic truth.",
            "Synthetic fixtures establish harness conformance, not hosted-runtime behavior.",
            "No score or report establishes consciousness, memory, identity, or ontological continuity.",
            "A final compatibility decision requires attributable human review and external runtime authority.",
        ],
        "provenance": {
            "generated_by": "cpas.evaluation.compare_runtime_transcripts",
            "source_issue": "https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/issues/100",
            "output_treatment": "untrusted-runtime-data-summarized-no-execution",
        },
    }
    sealed = seal_report(report)
    validate_report(sealed, manifest=manifest)
    return sealed
