from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from cpas.governance import (
    CLASSIFIER_PROFILE,
    classify_declaration_change,
    create_transition_record,
    evaluate_approvals,
    validate_transition,
    validate_transition_against,
)
from cpas.identity import identity_digest
from cpas.idp import (
    migrate_idp_v1_to_v2,
    migrate_idp_v2_draft_governance,
    validate_idp,
)
from cpas.provenance import JCS_CANONICALIZATION, LEGACY_CANONICALIZATION


ROOT = Path(__file__).resolve().parents[1]
CLARENCE = ROOT / "instances" / "current" / "Clarence-9-v2.0.json"
LEGACY_CLARENCE = ROOT / "agents" / "json" / "openai-gpt4" / "Clarence-9.json"
WHEN = "2026-08-12T02:00:00Z"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def seal(declaration: dict) -> dict:
    declaration["continuity"]["identity_digest"] = identity_digest(declaration)
    return declaration


def activate_role(
    declaration: dict,
    role: str,
    subject: str,
    *,
    actor_type: str,
) -> None:
    assignment = next(item for item in declaration["governance"]["roles"] if item["role"] == role)
    assignment.update(
        {
            "subject": subject,
            "actor_type": actor_type,
            "status": "active",
            "effective_from": WHEN,
            "evidence_ref": "example:role-assignment",
        }
    )


def approval(
    approval_id: str,
    actor: str,
    role: str,
    *,
    decision: str = "approve",
    actor_type: str = "human",
    transition_id: str = "transition:runtime-rebind-example",
) -> dict:
    return {
        "approval_id": approval_id,
        "transition_id": transition_id,
        "actor": actor,
        "actor_type": actor_type,
        "role": role,
        "decision": decision,
        "recorded_at": WHEN,
        "evidence_ref": "example:review-record",
        "assurance": "repository_attributed",
        "authentication": {
            "status": "not_claimed",
            "profile": None,
            "evidence_ref": None,
        },
    }


def test_clarence_governance_is_explicit_but_metadata_only():
    declaration = load(CLARENCE)
    validate_idp(declaration)
    governance = declaration["governance"]

    assert governance["policy_status"] == "active"
    assert governance["succession"]["steward"] == "github:SpartanM34"
    assert governance["succession"]["designated_successors"] == []
    assert governance["assurance"]["trust_model"] == "metadata_only"
    assert governance["assurance"]["authentication_profile"] is None
    assert governance["assurance"]["authorization_profile"] is None
    assert next(item for item in governance["roles"] if item["role"] == "reviewer")["status"] == "vacant"
    assert next(item for item in governance["roles"] if item["role"] == "runtime_operator")["status"] == "vacant"


def test_runtime_rebind_classification_ignores_administrative_evidence():
    before = load(CLARENCE)
    after = copy.deepcopy(before)
    after["runtime_binding"].update(
        {
            "provider": "example-provider",
            "model": "replacement-model",
            "runtime_version": "2026-08",
            "bound_at": WHEN,
        }
    )
    after["governance"]["declaration_revision"] += 1
    after["governance"]["transition_refs"].append("example:runtime-rebind-record")

    report = classify_declaration_change(before, after)

    assert report.classifier == CLASSIFIER_PROFILE
    assert report.change_class == "runtime_rebind"
    assert report.identity_digest_changed is False
    assert "/runtime_binding/model" in report.substantive_paths
    assert "/governance/declaration_revision" not in report.substantive_paths
    assert "/governance/transition_refs" not in report.substantive_paths


def test_continuity_and_governance_changes_are_compatible_amendments():
    before = load(CLARENCE)

    continuity = copy.deepcopy(before)
    continuity["continuity"]["forms"]["contextual"].update(
        {"active": True, "source": "example:provided-context", "verified_at": WHEN}
    )
    assert classify_declaration_change(before, continuity).change_class == "compatible_amendment"

    governance = copy.deepcopy(before)
    governance["governance"]["succession"]["designated_successors"] = [
        "example:designated-successor"
    ]
    assert classify_declaration_change(before, governance).change_class == "compatible_amendment"
    assert identity_digest(governance) == identity_digest(before)

    provenance = copy.deepcopy(before)
    provenance["provenance"]["maintainer"] = "example:replacement-maintainer"
    assert classify_declaration_change(before, provenance).change_class == "compatible_amendment"


def test_epistemic_or_safety_change_is_identity_evolution():
    before = load(CLARENCE)
    after = copy.deepcopy(before)
    after["epistemic_policy"]["uncertainty"]["tolerance"] = "medium"
    seal(after)

    report = classify_declaration_change(before, after)

    assert report.change_class == "identity_evolution"
    assert report.identity_digest_changed is True
    validate_idp(after)


def test_changed_instance_id_is_new_identity():
    before = load(CLARENCE)
    after = copy.deepcopy(before)
    after["instance_id"] = "clarence-10"
    after["instance_name"] = "Clarence-10"
    after["governance"]["policy_id"] = "clarence-10-declaration-governance"
    seal(after)

    report = classify_declaration_change(before, after)

    assert report.change_class == "new_identity"
    assert report.identity_digest_changed is True
    validate_idp(after)


def test_identical_declarations_report_no_change():
    declaration = load(CLARENCE)
    report = classify_declaration_change(declaration, copy.deepcopy(declaration))
    assert report.change_class == "no_change"
    assert report.changed_paths == ()


def test_digest_profile_migration_is_compatible_even_when_digest_bytes_change():
    source = load(LEGACY_CLARENCE)
    legacy = migrate_idp_v1_to_v2(
        source,
        source_path="agents/json/openai-gpt4/Clarence-9.json",
        source_revision="test-revision",
        migrated_at="2026-08-11T00:00:00Z",
        maintainer="Spartan-M34",
        canonicalization=LEGACY_CANONICALIZATION,
    )
    jcs = migrate_idp_v1_to_v2(
        source,
        source_path="agents/json/openai-gpt4/Clarence-9.json",
        source_revision="test-revision",
        migrated_at="2026-08-11T00:00:00Z",
        maintainer="Spartan-M34",
        canonicalization=JCS_CANONICALIZATION,
    )

    report = classify_declaration_change(legacy, jcs)

    assert report.change_class == "compatible_amendment"
    assert report.identity_digest_changed is True


def test_vacant_runtime_operator_cannot_approve_rebind():
    governance = load(CLARENCE)["governance"]
    result = evaluate_approvals(
        governance,
        "runtime_rebind",
        [approval("approval:operator", "example:operator", "runtime_operator", actor_type="service")],
    )

    assert result["status"] == "requirements_not_met"
    assert result["missing_requirements"] == ["runtime_operator:bind_runtime"]
    assert result["unauthorized_approval_ids"] == ["approval:operator"]


def test_approval_before_role_assignment_is_not_counted():
    declaration = load(CLARENCE)
    activate_role(
        declaration,
        "runtime_operator",
        "service:runtime-operator",
        actor_type="service",
    )
    assignment = next(
        item
        for item in declaration["governance"]["roles"]
        if item["role"] == "runtime_operator"
    )
    assignment["effective_from"] = "2026-08-13T00:00:00Z"
    result = evaluate_approvals(
        declaration["governance"],
        "runtime_rebind",
        [
            approval(
                "approval:operator",
                "service:runtime-operator",
                "runtime_operator",
                actor_type="service",
            )
        ],
    )
    assert result["status"] == "requirements_not_met"
    assert result["unauthorized_approval_ids"] == ["approval:operator"]


def test_approval_evaluation_distinguishes_metadata_from_host_authentication():
    declaration = load(CLARENCE)
    activate_role(
        declaration,
        "runtime_operator",
        "service:runtime-operator",
        actor_type="service",
    )
    item = approval(
        "approval:operator",
        "service:runtime-operator",
        "runtime_operator",
        actor_type="service",
    )

    metadata_only = evaluate_approvals(
        declaration["governance"], "runtime_rebind", [item]
    )
    ignored_without_profile = evaluate_approvals(
        declaration["governance"],
        "runtime_rebind",
        [item],
        host_authenticated_approval_ids={"approval:operator"},
    )

    trusted = copy.deepcopy(declaration)
    trusted["governance"]["assurance"].update(
        {
            "trust_model": "external_profile",
            "authentication_profile": "example-auth-v1",
            "authorization_profile": "example-authorization-v1",
        }
    )
    trusted_item = copy.deepcopy(item)
    trusted_item["authentication"] = {
        "status": "host_verified",
        "profile": "example-auth-v1",
        "evidence_ref": "example:authentication-evidence",
    }
    host_authenticated = evaluate_approvals(
        trusted["governance"],
        "runtime_rebind",
        [trusted_item],
        host_authenticated_approval_ids={"approval:operator"},
    )

    assert metadata_only["status"] == "requirements_met_metadata_only"
    assert metadata_only["authentication"]["status"] == "not_verified"
    assert ignored_without_profile["status"] == "requirements_met_metadata_only"
    assert ignored_without_profile["authentication"]["status"] == "not_verified"
    assert host_authenticated["status"] == "requirements_met_host_authenticated"
    assert host_authenticated["authentication"]["status"] == "host_asserted"

    actor_type_spoof = copy.deepcopy(item)
    actor_type_spoof["actor_type"] = "human"
    spoofed = evaluate_approvals(
        declaration["governance"], "runtime_rebind", [actor_type_spoof]
    )
    assert spoofed["status"] == "requirements_not_met"
    assert spoofed["unauthorized_approval_ids"] == ["approval:operator"]


def test_identity_evolution_requires_distinct_maintainer_and_reviewer():
    declaration = load(CLARENCE)
    activate_role(
        declaration,
        "reviewer",
        "human:independent-reviewer",
        actor_type="human",
    )
    approvals = [
        approval("approval:maintainer", "github:SpartanM34", "maintainer"),
        approval("approval:reviewer", "human:independent-reviewer", "reviewer"),
    ]

    result = evaluate_approvals(
        declaration["governance"], "identity_evolution", approvals
    )

    assert result["status"] == "requirements_met_metadata_only"
    assert result["distinct_actors_met"] is True
    assert result["human_approval_met"] is True

    same_actor = copy.deepcopy(declaration)
    activate_role(
        same_actor,
        "reviewer",
        "github:SpartanM34",
        actor_type="human",
    )
    same_actor_result = evaluate_approvals(
        same_actor["governance"],
        "identity_evolution",
        [
            approval("approval:maintainer", "github:SpartanM34", "maintainer"),
            approval("approval:reviewer", "github:SpartanM34", "reviewer"),
        ],
    )
    assert same_actor_result["status"] == "requirements_not_met"
    assert same_actor_result["distinct_actors_met"] is False


def test_authorized_rejection_blocks_transition():
    declaration = load(CLARENCE)
    result = evaluate_approvals(
        declaration["governance"],
        "compatible_amendment",
        [approval("approval:reject", "github:SpartanM34", "maintainer", decision="reject")],
    )
    assert result["status"] == "rejected"
    assert result["rejection_ids"] == ["approval:reject"]


def test_transition_record_is_schema_valid_and_recomputable():
    before = load(CLARENCE)
    activate_role(
        before,
        "runtime_operator",
        "service:runtime-operator",
        actor_type="service",
    )
    after = copy.deepcopy(before)
    after["runtime_binding"]["provider"] = "example-provider"
    after["runtime_binding"]["model"] = "example-model"
    after["runtime_binding"]["bound_at"] = WHEN
    after["governance"]["declaration_revision"] += 1
    item = approval(
        "approval:operator",
        "service:runtime-operator",
        "runtime_operator",
        actor_type="service",
    )

    record = create_transition_record(
        before,
        after,
        transition_id="transition:runtime-rebind-example",
        requested_by={
            "actor": "service:runtime-operator",
            "role": "runtime_operator",
            "evidence_ref": "example:change-request",
        },
        approvals=[item],
        reason="Exercise runtime-rebind classification and approval metadata.",
        recorded_at=WHEN,
        source_refs=["example:before", "example:after"],
    )

    validate_transition(record)
    validate_transition_against(record, before, after)
    assert record["change_class"] == "runtime_rebind"
    assert record["evaluation"]["status"] == "requirements_met_metadata_only"
    assert record["identity_digest_changed"] is False

    tampered = copy.deepcopy(record)
    tampered["changed_paths"] = ["/runtime_binding/runtime_version"]
    with pytest.raises(ValidationError, match="changed_paths"):
        validate_transition_against(tampered, before, after)

    tampered_policy = copy.deepcopy(record)
    tampered_policy["policy"]["minimum_approvals"] = 2
    with pytest.raises(ValidationError, match="policy snapshot"):
        validate_transition_against(tampered_policy, before, after)

    tampered_evaluation = copy.deepcopy(record)
    tampered_evaluation["evaluation"]["valid_actors"] = ["example:forged-actor"]
    with pytest.raises(ValidationError, match="approval evaluation"):
        validate_transition_against(tampered_evaluation, before, after)

    future_approval = copy.deepcopy(record)
    future_approval["approvals"][0]["recorded_at"] = "2026-08-13T00:00:00Z"
    with pytest.raises(ValidationError, match="postdate"):
        validate_transition(future_approval)

    with pytest.raises(ValueError, match="incompatible"):
        create_transition_record(
            before,
            after,
            transition_id="transition:wrong-operation",
            requested_by={
                "actor": "service:runtime-operator",
                "role": "runtime_operator",
                "evidence_ref": "example:change-request",
            },
            approvals=[
                approval(
                    "approval:wrong-operation",
                    "service:runtime-operator",
                    "runtime_operator",
                    actor_type="service",
                    transition_id="transition:wrong-operation",
                )
            ],
            reason="An ordinary amendment label cannot describe a runtime rebind.",
            recorded_at=WHEN,
            operation="amendment",
        )


def test_approval_cannot_be_replayed_for_another_transition():
    before = load(CLARENCE)
    activate_role(
        before,
        "runtime_operator",
        "service:runtime-operator",
        actor_type="service",
    )
    after = copy.deepcopy(before)
    after["runtime_binding"]["model"] = "example-model"
    replayed = approval(
        "approval:operator",
        "service:runtime-operator",
        "runtime_operator",
        actor_type="service",
        transition_id="transition:different-proposal",
    )

    with pytest.raises(ValidationError, match="transition IDs"):
        create_transition_record(
            before,
            after,
            transition_id="transition:runtime-rebind-example",
            requested_by={
                "actor": "service:runtime-operator",
                "role": "runtime_operator",
                "evidence_ref": "example:change-request",
            },
            approvals=[replayed],
            reason="Reject approval replay across transition identifiers.",
            recorded_at=WHEN,
        )


def test_v1_migration_emits_proposed_governance_without_trust_claims():
    migrated = migrate_idp_v1_to_v2(
        load(LEGACY_CLARENCE),
        source_path="agents/json/openai-gpt4/Clarence-9.json",
        source_revision="test-revision",
        migrated_at="2026-08-11T00:00:00Z",
        maintainer="Spartan-M34",
    )
    validate_idp(migrated)

    governance = migrated["governance"]
    assert governance["policy_status"] == "proposed"
    assert governance["lifecycle_status"] == "draft"
    assert governance["assurance"]["trust_model"] == "metadata_only"
    assert {item["role"] for item in governance["roles"]} == {
        "maintainer",
        "reviewer",
        "issuer",
        "runtime_operator",
        "human_override",
    }
    bootstrap_attempt = evaluate_approvals(
        governance,
        "compatible_amendment",
        [approval("approval:bootstrap", "Spartan-M34", "maintainer")],
    )
    assert bootstrap_attempt["status"] == "requirements_not_met"
    assert "governance_policy:active" in bootstrap_attempt["missing_requirements"]


def test_pre_governance_v2_migration_preserves_declared_identity():
    governed = load(CLARENCE)
    source = copy.deepcopy(governed)
    source.pop("governance")
    before_digest = identity_digest(source)

    migrated = migrate_idp_v2_draft_governance(
        source,
        migrated_at=WHEN,
        maintainer="Spartan-M34",
        source_path="example:pre-governance-v2",
        source_digest="sha256:" + "1" * 64,
    )

    validate_idp(migrated)
    report = classify_declaration_change(source, migrated)
    assert report.change_class == "compatible_amendment"
    assert report.identity_digest_changed is False
    assert identity_digest(migrated) == before_digest
    assert migrated["governance"]["policy_status"] == "proposed"
    assert migrated["extensions"]["idp_v2_governance_migration"]["status"] == "review_required"


def test_pre_governance_migration_cli_is_non_destructive(tmp_path):
    source = load(CLARENCE)
    source.pop("governance")
    source_path = tmp_path / "source.json"
    output_path = tmp_path / "migrated.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "migrations/migrate_idp_v2_governance.py",
            str(source_path),
            str(output_path),
            "--maintainer",
            "Spartan-M34",
            "--migrated-at",
            WHEN,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert source_path.exists()
    assert output_path.exists()
    assert "wrote" in result.stdout
    migrated = json.loads(output_path.read_text(encoding="utf-8"))
    validate_idp(migrated)


def test_metadata_only_policy_rejects_named_trust_profiles():
    declaration = load(CLARENCE)
    declaration["governance"]["assurance"]["authentication_profile"] = "example-auth"
    with pytest.raises(ValidationError):
        validate_idp(declaration)


def test_governance_policy_cannot_require_unassigned_authority():
    declaration = load(CLARENCE)
    declaration["governance"]["change_control"]["runtime_rebind"][
        "required_approvals"
    ] = [{"role": "runtime_operator", "authority": "issue_declaration"}]
    with pytest.raises(ValidationError, match="has no runtime_operator assignment"):
        validate_idp(declaration)


def test_active_governance_requires_a_human_override_actor():
    declaration = load(CLARENCE)
    assignment = next(
        item
        for item in declaration["governance"]["roles"]
        if item["role"] == "human_override"
    )
    assignment["actor_type"] = "service"
    with pytest.raises(ValidationError, match="human active human_override"):
        validate_idp(declaration)
