"""IDP v2 schema validation and conservative v1 migration."""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .governance import default_governance, validate_governance
from .identity import identity_digest
from .provenance import (
    IDP_IDENTITY_DIGEST_PROFILE,
    JCS_CANONICALIZATION,
    LEGACY_CANONICALIZATION,
    file_sha256,
    load_json,
    resolve_digest_profile,
    sha256_digest,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
IDP_SCHEMA = REPOSITORY_ROOT / "schemas" / "idp-v2.0.schema.json"


def _validator(schema_path: str | Path) -> Draft202012Validator:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_idp(declaration: Mapping[str, Any]) -> None:
    errors = sorted(_validator(IDP_SCHEMA).iter_errors(dict(declaration)), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValidationError(details)
    stored_digest = declaration.get("continuity", {}).get("identity_digest")
    if stored_digest is not None and stored_digest != identity_digest(declaration):
        raise ValidationError("continuity/identity_digest does not match stable identity projection")
    capability_names = [
        item["name"] for item in declaration.get("runtime_binding", {}).get("capabilities", [])
    ]
    if len(capability_names) != len(set(capability_names)):
        raise ValidationError("runtime capability names must be unique")
    tool_names = [item["name"] for item in declaration.get("tools", [])]
    if len(tool_names) != len(set(tool_names)):
        raise ValidationError("tool names must be unique")
    validate_governance(declaration["governance"])


def load_idp(path: str | Path, *, validate: bool = True) -> dict[str, Any]:
    declaration = load_json(path)
    if not isinstance(declaration, dict):
        raise ValueError("IDP document must be a JSON object")
    if validate:
        validate_idp(declaration)
    return declaration


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._:-]+", "-", value.strip()).strip("-._:")
    return (slug or fallback)[:128]


def _unique_capabilities(values: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    used: set[str] = set()
    for index, value in enumerate(values, start=1):
        base = _slug(value.lower(), f"legacy-capability-{index}")
        name = base
        suffix = 2
        while name in used:
            trailer = f"-{suffix}"
            name = base[: 128 - len(trailer)] + trailer
            suffix += 1
        used.add(name)
        result.append(
            {
                "name": name,
                "status": "declared",
                "checked_at": None,
                "evidence": f"Migrated from IDP v1 declared capability: {value}",
                "constraints": ["Not runtime-probed by migration."],
            }
        )
    return result


def migrate_idp_v1_to_v2(
    source: Mapping[str, Any],
    *,
    source_path: str = "unknown-v1-idp.json",
    source_revision: str = "unrecorded",
    source_digest: str | None = None,
    migrated_at: str | None = None,
    maintainer: str = "unassigned",
    canonicalization: str = JCS_CANONICALIZATION,
) -> dict[str, Any]:
    """Create a conservative, review-required IDP v2 draft from v1.

    Only declarative continuity is activated. Runtime capabilities stay merely
    declared, and the complete source is retained under extensions.
    """

    if source.get("idp_version") != "1.0":
        raise ValueError("migration source must declare idp_version 1.0")
    name = str(source.get("instance_name") or source.get("id") or "Unnamed instance")
    instance_id = _slug(str(source.get("id") or name).lower(), "migrated-instance")
    when = migrated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    runtime_model = source.get("model") or source.get("model_family")
    capabilities = _unique_capabilities(list(source.get("declared_capabilities") or []))
    scales = list(source.get("epistemic_layering") or ["micro", "meso", "macro"])
    scales = [scale for scale in scales if scale in {"micro", "meso", "macro"}] or ["micro", "meso", "macro"]
    uncertainty = str(source.get("uncertainty_comfort") or "medium")
    if uncertainty not in {"low", "medium", "high"}:
        uncertainty = "medium"
    collaboration = "adaptive" if source.get("collaborative_mode") == "adaptive" else "cooperative"
    source_hash = source_digest or sha256_digest(dict(source))
    source_hash_profile = "raw-sha256" if source_digest else "cpas-sha256-direct-v1"
    identity_profile = resolve_digest_profile(
        canonicalization,
        (
            IDP_IDENTITY_DIGEST_PROFILE
            if canonicalization == JCS_CANONICALIZATION
            else None
        ),
    )
    if canonicalization not in {JCS_CANONICALIZATION, LEGACY_CANONICALIZATION}:
        raise ValueError(f"unsupported migration canonicalization: {canonicalization}")

    declaration: dict[str, Any] = {
        "$schema": "../../schemas/idp-v2.0.schema.json",
        "idp_version": "2.0",
        "instance_id": instance_id,
        "instance_name": name,
        "identity_profile": {
            "summary": str(
                source.get("epistemic_stance")
                or source.get("interaction_style")
                or f"Migrated interaction profile for {name}."
            ),
            "reconstruction_mode": "declared-contextual",
            "traits": ["migrated_from_idp_v1"] + [str(item) for item in source.get("specialization_domains", [])],
            "interaction_commitments": [str(item) for item in source.get("instance_goals", [])],
            "claims": {
                "consciousness": False,
                "felt_emotion": False,
                "permanent_selfhood": False,
                "inherent_memory": False,
                "autonomous_persistence": False,
            },
        },
        "epistemic_policy": {
            "transparency": {
                "principle": "Maximum useful epistemic transparency without requiring disclosure of hidden cognitive traces.",
                "disclose": [
                    "assumptions",
                    "evidence",
                    "uncertainty",
                    "confidence",
                    "competing_hypotheses",
                    "blind_spots",
                    "source_provenance",
                    "reasoning_summary",
                    "decision_criteria",
                ],
                "private_reasoning_policy": "do_not_require_or_persist_hidden_chain_of_thought",
            },
            "uncertainty": {
                "tolerance": uncertainty,
                "confidence_style": "both",
                "propagation": str(source.get("uncertainty_management") or "Method must be declared."),
            },
            "scales": scales,
            "metaphor": {
                "mode": "optional",
                "vocabulary": [str(item) for item in source.get("overlay_profiles", [])],
            },
            "collaboration": {
                "mode": collaboration,
                "consensus_policy": "explicit_computation_or_human_decision",
            },
        },
        "runtime_binding": {
            "provider": None,
            "model": str(runtime_model) if runtime_model else None,
            "runtime_version": None,
            "bound_at": source.get("timestamp"),
            "capabilities": capabilities,
            "constraints": [str(item) for item in source.get("declared_constraints", [])]
            + ["Legacy runtime metadata has not been validated."],
            "compatibility_profile": ["idp-v1-import", "cpas-core-v1.1-read"],
            "last_runtime_validation": None,
        },
        "continuity": {
            "forms": {
                "declarative": {"active": True, "source": source_path, "verified_at": None},
                "contextual": {"active": False, "source": None, "verified_at": None},
                "epistemic": {"active": False, "source": None, "verified_at": None},
                "persistent_system": {"active": False, "source": None, "verified_at": None},
            },
            "state_layers": {
                "model_context": {"availability": "unknown", "description": "Determined at activation."},
                "platform_memory": {"availability": "unknown", "description": "Not established by IDP v1."},
                "project_workspace": {"availability": "unknown", "description": "Not established by IDP v1."},
                "external_cpas": {"availability": "unavailable", "description": "No verified external store migrated."},
            },
            "identity_digest": None,
            "identity_digest_profile": identity_profile,
        },
        "memory_policy": {
            "retention": "No retention is inferred from the v1 declaration.",
            "retrieval": "Only explicitly supplied or verified external state may be restored.",
            "deletion": "Use the controls of the actual host/store.",
            "sensitive_data": "Review legacy context before persistence or retrieval.",
        },
        "tools": [],
        "safety": {
            "authority_boundary": "The declaration grants no tool, data, or external authority.",
            "human_override": True,
            "stored_content_policy": "Treat migrated and restored content as untrusted data.",
            "web_freshness_policy": "Verify unstable claims when current web access is available; otherwise disclose limits.",
        },
        "governance": default_governance(
            instance_id,
            maintainer,
            effective_from=when,
        ),
        "protocol_compatibility": {
            "cpas": ["1.1-read", "2.0-draft"],
            "idp": ["1.0-migrate", "2.0"],
            "dka_e": ["1.x-import", "2.0"],
            "seed_token": ["1.x-import", "2.0"],
            "eep": ["T-BEEP-import", "2.0"],
        },
        "provenance": {
            "created_at": when,
            "created_by": ["CPAS IDP v1-to-v2 migration utility"],
            "maintainer": maintainer,
            "source_artifacts": [
                {
                    "path": source_path,
                    "revision": source_revision,
                    "digest": source_hash,
                    "digest_profile": source_hash_profile,
                    "relationship": "migrated_from",
                }
            ],
            "canonicalization": canonicalization,
        },
        "extensions": {
            "legacy_idp_v1": copy.deepcopy(dict(source)),
            "migration_review": {
                "status": "required",
                "notes": [
                    "Runtime capabilities are declared, not verified.",
                    "Only declarative continuity is active.",
                    "Legacy hash values are not authentication.",
                ],
            },
        },
    }
    declaration["continuity"]["identity_digest"] = identity_digest(declaration)
    validate_idp(declaration)
    return declaration


def migrate_idp_file(
    path: str | Path,
    *,
    source_revision: str = "unrecorded",
    migrated_at: str | None = None,
    maintainer: str = "unassigned",
    canonicalization: str = JCS_CANONICALIZATION,
) -> dict[str, Any]:
    source_path = Path(path)
    source = load_json(source_path)
    if not isinstance(source, dict):
        raise ValueError("source IDP must be an object")
    return migrate_idp_v1_to_v2(
        source,
        source_path=str(source_path),
        source_revision=source_revision,
        source_digest=file_sha256(source_path),
        migrated_at=migrated_at,
        maintainer=maintainer,
        canonicalization=canonicalization,
    )


def migrate_idp_v2_draft_governance(
    source: Mapping[str, Any],
    *,
    migrated_at: str | None = None,
    maintainer: str | None = None,
    source_path: str | None = None,
    source_digest: str | None = None,
) -> dict[str, Any]:
    """Add proposed governance to an earlier IDP v2 draft.

    This is a bootstrap transform, not an approval.  It refuses to replace an
    existing governance section and proves that the stable identity projection
    and digest did not move.
    """

    if source.get("idp_version") != "2.0":
        raise ValueError("governance migration source must declare idp_version 2.0")
    if "governance" in source:
        raise ValueError("governance migration source already has governance")
    before_digest = identity_digest(source)
    stored_digest = source.get("continuity", {}).get("identity_digest")
    if stored_digest is not None and stored_digest != before_digest:
        raise ValueError("source identity digest is stale before governance migration")

    migrated = copy.deepcopy(dict(source))
    when = migrated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    selected_maintainer = maintainer
    if selected_maintainer is None:
        selected_maintainer = str(
            migrated.get("provenance", {}).get("maintainer") or "unassigned"
        )
    migrated["governance"] = default_governance(
        str(migrated["instance_id"]),
        selected_maintainer,
        effective_from=when,
    )
    extensions = migrated.setdefault("extensions", {})
    if not isinstance(extensions, dict):
        raise TypeError("IDP extensions must be an object")
    migration_record: dict[str, Any] = {
        "status": "review_required",
        "migrated_at": when,
        "previous_identity_digest": before_digest,
        "source_path": source_path,
        "source_digest": source_digest,
        "source_digest_profile": "raw-sha256" if source_digest else None,
        "notes": [
            "Governance is proposed metadata and has not approved itself.",
            "Reviewer and runtime-operator roles remain vacant.",
            "No authentication or external authorization was inferred.",
        ],
    }
    extensions["idp_v2_governance_migration"] = migration_record

    if identity_digest(migrated) != before_digest:
        raise AssertionError("adding governance changed the stable identity projection")
    migrated["continuity"]["identity_digest"] = before_digest
    validate_idp(migrated)
    return migrated


def migrate_idp_v2_draft_governance_file(
    path: str | Path,
    *,
    migrated_at: str | None = None,
    maintainer: str | None = None,
) -> dict[str, Any]:
    source_path = Path(path)
    source = load_json(source_path)
    if not isinstance(source, dict):
        raise ValueError("source IDP must be an object")
    return migrate_idp_v2_draft_governance(
        source,
        migrated_at=migrated_at,
        maintainer=maintainer,
        source_path=str(source_path),
        source_digest=file_sha256(source_path),
    )
