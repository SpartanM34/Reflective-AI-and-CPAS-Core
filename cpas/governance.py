"""Declaration governance, change classification, and approval metadata.

The reference code evaluates declared roles and approval records.  It does not
authenticate actors or grant external authorization.  A host may provide the
IDs of approval records it independently authenticated; that assertion remains
outside CPAS-Core.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Collection, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .identity import identity_digest, same_declared_identity
from .provenance import load_json


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TRANSITION_SCHEMA = REPOSITORY_ROOT / "schemas" / "idp-transition-v2.0.schema.json"

CLASSIFIER_PROFILE = "cpas-idp-change-v1"
CHANGE_CLASSES = (
    "runtime_rebind",
    "compatible_amendment",
    "identity_evolution",
    "new_identity",
)
NO_CHANGE = "no_change"
ROLE_TYPES = (
    "maintainer",
    "reviewer",
    "issuer",
    "runtime_operator",
    "human_override",
)
LIFECYCLE_ACTIONS = ("supersession", "rollback", "retirement")
_ORDINARY_OPERATIONS = {
    "runtime_rebind": "runtime_rebind",
    "amendment": "compatible_amendment",
    "identity_evolution": "identity_evolution",
    "issuance": "new_identity",
}

_RUNTIME_ROOTS = {"runtime_binding", "tools"}
_CLASSIFICATION_METADATA_PATHS = {
    "/continuity/identity_digest",
    "/continuity/identity_digest_profile",
    "/governance/declaration_revision",
    "/governance/transition_refs",
}


@dataclass(frozen=True)
class ChangeReport:
    """Deterministic semantic classification of two declaration documents."""

    classifier: str
    change_class: str
    changed_paths: tuple[str, ...]
    substantive_paths: tuple[str, ...]
    instance_id_before: str
    instance_id_after: str
    identity_digest_before: str
    identity_digest_after: str
    identity_digest_changed: bool

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["changed_paths"] = list(self.changed_paths)
        result["substantive_paths"] = list(self.substantive_paths)
        return result


def _pointer_token(value: object) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def _changed_paths(left: Any, right: Any, path: str = "") -> list[str]:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        changed: list[str] = []
        for key in sorted(set(left) | set(right), key=str):
            child = f"{path}/{_pointer_token(key)}"
            if key not in left or key not in right:
                changed.append(child)
            else:
                changed.extend(_changed_paths(left[key], right[key], child))
        return changed
    if left != right:
        return [path or "/"]
    return []


def _is_classification_metadata(path: str) -> bool:
    if path == "/$schema":
        return True
    return path in _CLASSIFICATION_METADATA_PATHS


def _root(path: str) -> str:
    return path.lstrip("/").split("/", 1)[0]


def _timestamp(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires a timezone")
    return parsed.astimezone(timezone.utc)


def classify_declaration_change(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> ChangeReport:
    """Classify a declaration change independently of claimed approvals.

    Precedence is normative: a changed ``instance_id`` is a new identity; a
    changed stable identity projection is identity evolution; runtime/tool-only
    substantive changes are a runtime rebind; every other non-empty change is
    a compatible amendment.  Administrative evidence is reported but ignored
    when deciding whether a runtime-only change is a rebind.
    """

    changed = tuple(_changed_paths(before, after))
    substantive = tuple(path for path in changed if not _is_classification_metadata(path))
    before_id = str(before.get("instance_id", ""))
    after_id = str(after.get("instance_id", ""))
    before_digest = identity_digest(before)
    after_digest = identity_digest(after)

    if not changed:
        change_class = NO_CHANGE
    elif before_id != after_id:
        change_class = "new_identity"
    elif not same_declared_identity(before, after):
        change_class = "identity_evolution"
    elif substantive and {_root(path) for path in substantive} <= _RUNTIME_ROOTS:
        change_class = "runtime_rebind"
    else:
        change_class = "compatible_amendment"

    return ChangeReport(
        classifier=CLASSIFIER_PROFILE,
        change_class=change_class,
        changed_paths=changed,
        substantive_paths=substantive,
        instance_id_before=before_id,
        instance_id_after=after_id,
        identity_digest_before=before_digest,
        identity_digest_after=after_digest,
        identity_digest_changed=before_digest != after_digest,
    )


def _policy(
    required_approvals: Sequence[tuple[str, str]],
    *,
    distinct_actors: bool,
    human_approval_required: bool,
) -> dict[str, Any]:
    return {
        "required_approvals": [
            {"role": role, "authority": authority}
            for role, authority in required_approvals
        ],
        "minimum_approvals": len(required_approvals),
        "distinct_actors": distinct_actors,
        "human_approval_required": human_approval_required,
    }


def default_governance(
    instance_id: str,
    maintainer: str = "unassigned",
    *,
    effective_from: str | None = None,
) -> dict[str, Any]:
    """Return conservative governance metadata for a migrated declaration.

    The result is proposed/draft and metadata-only.  Reviewer and runtime
    operator assignments stay vacant until a human review names them.
    """

    assigned = bool(maintainer.strip()) and maintainer.strip().lower() != "unassigned"
    subject = maintainer.strip() if assigned else None

    def assignment(
        role: str,
        authorities: Sequence[str],
        *,
        active: bool,
    ) -> dict[str, Any]:
        return {
            "role": role,
            "subject": subject if active else None,
            "actor_type": "unspecified" if active else "unassigned",
            "status": "active" if active else "vacant",
            "authorities": list(authorities),
            "effective_from": effective_from if active else None,
            "evidence_ref": None,
        }

    roles = [
        assignment(
            "maintainer",
            [
                "amend_declaration",
                "evolve_identity",
                "change_governance",
                "supersede_declaration",
                "rollback_declaration",
                "retire_declaration",
                "appoint_successor",
            ],
            active=assigned,
        ),
        assignment("reviewer", ["review_declaration"], active=False),
        assignment("issuer", ["issue_declaration"], active=assigned),
        assignment("runtime_operator", ["bind_runtime"], active=False),
        assignment(
            "human_override",
            ["approve_retirement", "emergency_override"],
            active=assigned,
        ),
    ]
    return {
        "governance_version": "1.0",
        "policy_id": f"{instance_id}-declaration-governance",
        "policy_status": "proposed",
        "declaration_revision": 1,
        "lifecycle_status": "draft",
        "roles": roles,
        "change_control": {
            "runtime_rebind": _policy(
                [("runtime_operator", "bind_runtime")],
                distinct_actors=False,
                human_approval_required=False,
            ),
            "compatible_amendment": _policy(
                [("maintainer", "amend_declaration")],
                distinct_actors=False,
                human_approval_required=True,
            ),
            "identity_evolution": _policy(
                [
                    ("maintainer", "evolve_identity"),
                    ("reviewer", "review_declaration"),
                ],
                distinct_actors=True,
                human_approval_required=True,
            ),
            "new_identity": _policy(
                [
                    ("issuer", "issue_declaration"),
                    ("reviewer", "review_declaration"),
                ],
                distinct_actors=True,
                human_approval_required=True,
            ),
            "supersession": _policy(
                [
                    ("maintainer", "supersede_declaration"),
                    ("issuer", "issue_declaration"),
                    ("reviewer", "review_declaration"),
                ],
                distinct_actors=True,
                human_approval_required=True,
            ),
            "rollback": _policy(
                [
                    ("maintainer", "rollback_declaration"),
                    ("reviewer", "review_declaration"),
                ],
                distinct_actors=True,
                human_approval_required=True,
            ),
            "retirement": _policy(
                [
                    ("maintainer", "retire_declaration"),
                    ("human_override", "approve_retirement"),
                ],
                distinct_actors=False,
                human_approval_required=True,
            ),
        },
        "succession": {
            "steward": subject,
            "mode": "explicit_appointment",
            "designated_successors": [],
            "activation_requirements": [
                "Record the appointing authority and repository evidence.",
                "Amend role assignments under the incumbent policy.",
                "Do not inherit authentication or authorization claims implicitly.",
            ],
            "vacancy_behavior": (
                "Freeze identity evolution, supersession, and retirement until "
                "an authorized human authority resolves stewardship."
            ),
        },
        "transition_refs": [],
        "assurance": {
            "trust_model": "metadata_only",
            "authentication_profile": None,
            "authorization_profile": None,
            "statement": (
                "Role assignments and approvals are attributable metadata only; "
                "they do not authenticate an actor or grant external authority."
            ),
        },
    }


def validate_governance(governance: Mapping[str, Any]) -> None:
    """Apply semantic checks that JSON Schema cannot express compactly."""

    roles = list(governance.get("roles", []))
    represented = {item.get("role") for item in roles if isinstance(item, Mapping)}
    missing_roles = sorted(set(ROLE_TYPES) - represented)
    if missing_roles:
        raise ValidationError("governance roles missing: " + ", ".join(missing_roles))

    assignments: set[tuple[object, object]] = set()
    for item in roles:
        role = item.get("role")
        subject = item.get("subject")
        status = item.get("status")
        if status in {"active", "conditional"} and not subject:
            raise ValidationError(f"{role} assignment requires a subject")
        if status == "active" and not item.get("effective_from"):
            raise ValidationError(f"active {role} assignment requires effective_from")
        if status == "vacant" and subject is not None:
            raise ValidationError(f"vacant {role} assignment must have a null subject")
        if subject is not None and status != "revoked":
            key = (role, subject)
            if key in assignments:
                raise ValidationError(f"duplicate governance assignment: {role}/{subject}")
            assignments.add(key)

    control = governance.get("change_control", {})
    expected_policies = set(CHANGE_CLASSES) | set(LIFECYCLE_ACTIONS)
    missing_policies = sorted(expected_policies - set(control))
    if missing_policies:
        raise ValidationError(
            "governance change-control policies missing: " + ", ".join(missing_policies)
        )
    for name in expected_policies:
        policy = control[name]
        required = list(policy["required_approvals"])
        if policy["minimum_approvals"] < len(required):
            raise ValidationError(
                f"governance policy {name} minimum_approvals is smaller than its requirements"
            )
        if policy["distinct_actors"] and policy["minimum_approvals"] < 2:
            raise ValidationError(
                f"governance policy {name} requires distinct actors but fewer than two approvals"
            )
        for requirement in required:
            if requirement["role"] not in represented:
                raise ValidationError(
                    f"governance policy {name} refers to absent role {requirement['role']}"
                )
            if not any(
                item.get("role") == requirement["role"]
                and requirement["authority"] in item.get("authorities", [])
                for item in roles
            ):
                raise ValidationError(
                    f"governance policy {name} has no {requirement['role']} assignment "
                    f"with {requirement['authority']} authority"
                )

    if governance.get("policy_status") == "active":
        for required_role in ("maintainer", "issuer", "human_override"):
            if not any(
                item.get("role") == required_role and item.get("status") == "active"
                for item in roles
            ):
                raise ValidationError(
                    f"active governance policy requires an active {required_role}"
                )
        if not any(
            item.get("role") == "human_override"
            and item.get("status") == "active"
            and item.get("actor_type") == "human"
            for item in roles
        ):
            raise ValidationError(
                "active governance policy requires a human active human_override"
            )

    assurance = governance.get("assurance", {})
    if assurance.get("trust_model") == "metadata_only" and (
        assurance.get("authentication_profile") is not None
        or assurance.get("authorization_profile") is not None
    ):
        raise ValidationError("metadata-only governance cannot name active trust profiles")
    if assurance.get("trust_model") == "external_profile" and (
        not assurance.get("authentication_profile")
        or not assurance.get("authorization_profile")
    ):
        raise ValidationError("external-profile governance requires named trust profiles")


def _active_assignments(governance: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in governance.get("roles", [])
        if item.get("status") == "active" and item.get("subject")
    ]


def evaluate_approvals(
    governance: Mapping[str, Any],
    policy_key: str,
    approvals: Sequence[Mapping[str, Any]],
    *,
    expected_transition_id: str | None = None,
    host_authenticated_approval_ids: Collection[str] = (),
) -> dict[str, Any]:
    """Evaluate declared approvals under the supplied governance policy.

    ``host_authenticated_approval_ids`` is an assertion from an external trust
    adapter.  This module does not verify signatures, accounts, or credentials.
    """

    validate_governance(governance)
    control = governance["change_control"]
    if policy_key not in control:
        raise ValueError(f"unknown governance policy: {policy_key}")
    policy = control[policy_key]
    policy_active = governance.get("policy_status") == "active"
    assignments = _active_assignments(governance)
    assurance = governance["assurance"]
    trust_profile_active = assurance.get("trust_model") == "external_profile"
    authenticated = (
        set(host_authenticated_approval_ids) if trust_profile_active else set()
    )

    def matching_assignment(
        approval: Mapping[str, Any], authority: str
    ) -> Mapping[str, Any] | None:
        for assignment in assignments:
            if (
                assignment["role"] == approval.get("role")
                and assignment["subject"] == approval.get("actor")
                and assignment["actor_type"] == approval.get("actor_type")
                and authority in assignment.get("authorities", [])
            ):
                try:
                    if _timestamp(approval.get("recorded_at")) < _timestamp(
                        assignment.get("effective_from")
                    ):
                        return None
                except (TypeError, ValueError):
                    return None
                return assignment
        return None

    required = list(policy["required_approvals"])
    approved_matches: dict[
        tuple[str, str], list[tuple[Mapping[str, Any], Mapping[str, Any]]]
    ] = {}
    authenticated_matches: dict[
        tuple[str, str], list[tuple[Mapping[str, Any], Mapping[str, Any]]]
    ] = {}
    rejection_ids: set[str] = set()
    unauthorized_ids: set[str] = set()

    for approval in approvals:
        approval_id = str(approval.get("approval_id", ""))
        relevant = False
        if (
            expected_transition_id is not None
            and approval.get("transition_id") != expected_transition_id
        ):
            if approval.get("decision") in {"approve", "reject"}:
                unauthorized_ids.add(approval_id)
            continue
        for requirement in required:
            role = requirement["role"]
            authority = requirement["authority"]
            if approval.get("role") != role:
                continue
            assignment = matching_assignment(approval, authority)
            if assignment is None:
                continue
            relevant = True
            key = (role, authority)
            if approval.get("decision") == "reject":
                rejection_ids.add(approval_id)
            elif approval.get("decision") == "approve":
                approved_matches.setdefault(key, []).append((approval, assignment))
                approval_authentication = approval.get("authentication", {})
                if (
                    approval_id in authenticated
                    and approval_authentication.get("status") == "host_verified"
                    and approval_authentication.get("profile")
                    == assurance.get("authentication_profile")
                    and approval_authentication.get("evidence_ref")
                ):
                    authenticated_matches.setdefault(key, []).append(
                        (approval, assignment)
                    )
        if approval.get("decision") in {"approve", "reject"} and not relevant:
            unauthorized_ids.add(approval_id)

    def assess(
        matches: Mapping[
            tuple[str, str], list[tuple[Mapping[str, Any], Mapping[str, Any]]]
        ]
    ) -> tuple[list[str], set[str], set[str], bool, bool]:
        missing = [
            f"{item['role']}:{item['authority']}"
            for item in required
            if (item["role"], item["authority"]) not in matches
        ]
        records = {
            str(approval["approval_id"])
            for values in matches.values()
            for approval, _assignment in values
        }
        actors = {
            str(approval["actor"])
            for values in matches.values()
            for approval, _assignment in values
        }
        has_human = any(
            assignment.get("actor_type") == "human"
            for values in matches.values()
            for _approval, assignment in values
        )
        count_met = len(records) >= policy["minimum_approvals"]
        distinct_met = not policy["distinct_actors"] or len(actors) >= 2
        human_met = not policy["human_approval_required"] or has_human
        return missing, records, actors, count_met and human_met, distinct_met

    missing, valid_ids, actors, base_met, distinct_met = assess(approved_matches)
    if not policy_active:
        missing.append("governance_policy:active")
    auth_missing, auth_ids, auth_actors, auth_base_met, auth_distinct_met = assess(
        authenticated_matches
    )
    requirements_met = (
        policy_active
        and not missing
        and base_met
        and distinct_met
        and not rejection_ids
    )
    authenticated_met = (
        policy_active
        and trust_profile_active
        and bool(authenticated)
        and not auth_missing
        and auth_base_met
        and auth_distinct_met
        and not rejection_ids
    )
    if not policy_active:
        status = "requirements_not_met"
    elif rejection_ids:
        status = "rejected"
    elif not requirements_met:
        status = "requirements_not_met"
    elif authenticated_met:
        status = "requirements_met_host_authenticated"
    else:
        status = "requirements_met_metadata_only"

    return {
        "status": status,
        "policy_key": policy_key,
        "missing_requirements": missing,
        "valid_approval_ids": sorted(valid_ids),
        "valid_actors": sorted(actors),
        "rejection_ids": sorted(rejection_ids),
        "unauthorized_approval_ids": sorted(unauthorized_ids),
        "distinct_actors_met": distinct_met,
        "human_approval_met": (
            not policy["human_approval_required"]
            or any(
                assignment.get("actor_type") == "human"
                for values in approved_matches.values()
                for _approval, assignment in values
            )
        ),
        "authentication": {
            "status": "host_asserted" if authenticated_met else "not_verified",
            "approval_ids": sorted(auth_ids),
            "actors": sorted(auth_actors),
        },
    }


def _transition_validator() -> Draft202012Validator:
    schema = load_json(TRANSITION_SCHEMA)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_transition(record: Mapping[str, Any]) -> None:
    errors = sorted(
        _transition_validator().iter_errors(dict(record)),
        key=lambda error: list(error.path),
    )
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValidationError(details)
    paths = list(record["changed_paths"])
    if paths != sorted(set(paths)):
        raise ValidationError("changed_paths must be sorted and unique")
    substantive_paths = list(record["substantive_paths"])
    if substantive_paths != sorted(set(substantive_paths)):
        raise ValidationError("substantive_paths must be sorted and unique")
    approval_ids = [item["approval_id"] for item in record["approvals"]]
    if len(approval_ids) != len(set(approval_ids)):
        raise ValidationError("approval IDs must be unique")
    if any(
        item["transition_id"] != record["transition_id"]
        for item in record["approvals"]
    ):
        raise ValidationError("approval transition IDs must match the record")
    try:
        record_time = _timestamp(record["recorded_at"])
        if any(_timestamp(item["recorded_at"]) > record_time for item in record["approvals"]):
            raise ValidationError("approval cannot postdate the transition record")
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"invalid transition timestamp: {exc}") from exc
    known_approvals = set(approval_ids)
    evaluation = record["evaluation"]
    classified_ids = {
        "valid_approval_ids": set(evaluation["valid_approval_ids"]),
        "rejection_ids": set(evaluation["rejection_ids"]),
        "unauthorized_approval_ids": set(evaluation["unauthorized_approval_ids"]),
        "authentication.approval_ids": set(
            evaluation["authentication"]["approval_ids"]
        ),
    }
    for field, values in classified_ids.items():
        if not values <= known_approvals:
            raise ValidationError(f"{field} refers to an unknown approval ID")
    if classified_ids["valid_approval_ids"] & classified_ids["rejection_ids"]:
        raise ValidationError("an approval ID cannot be both valid and rejecting")
    if classified_ids["unauthorized_approval_ids"] & (
        classified_ids["valid_approval_ids"] | classified_ids["rejection_ids"]
    ):
        raise ValidationError("an unauthorized approval ID cannot also be counted")
    if record["policy"]["policy_key"] != record["evaluation"]["policy_key"]:
        raise ValidationError("transition policy and evaluation keys must match")
    auth_status = record["evaluation"]["authentication"]["status"]
    if (
        record["evaluation"]["status"] == "requirements_met_host_authenticated"
        and auth_status != "host_asserted"
    ):
        raise ValidationError("host-authenticated evaluation requires host assertion")
    if auth_status == "host_asserted" and record["evaluation"]["status"] != (
        "requirements_met_host_authenticated"
    ):
        raise ValidationError("host assertion is inconsistent with evaluation status")
    ordinary_class = _ORDINARY_OPERATIONS.get(record["operation"])
    if ordinary_class is not None and ordinary_class != record["change_class"]:
        raise ValidationError("ordinary operation does not match the change class")


def create_transition_record(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    transition_id: str,
    requested_by: Mapping[str, Any],
    approvals: Sequence[Mapping[str, Any]],
    reason: str,
    recorded_at: str,
    operation: str | None = None,
    source_refs: Iterable[str] = (),
    host_authenticated_approval_ids: Collection[str] = (),
) -> dict[str, Any]:
    """Build and validate an inspectable transition record for two IDPs."""

    # Local import avoids the module-level IDP/governance validation cycle.
    from .idp import validate_idp

    validate_idp(before)
    validate_idp(after)
    report = classify_declaration_change(before, after)
    if report.change_class == NO_CHANGE:
        raise ValueError("cannot create a transition record for identical declarations")
    default_operations = {value: key for key, value in _ORDINARY_OPERATIONS.items()}
    selected_operation = operation or default_operations[report.change_class]
    ordinary_class = _ORDINARY_OPERATIONS.get(selected_operation)
    if ordinary_class is not None and ordinary_class != report.change_class:
        raise ValueError(
            f"operation {selected_operation} is incompatible with {report.change_class}"
        )
    policy_key = (
        selected_operation
        if selected_operation in LIFECYCLE_ACTIONS
        else report.change_class
    )
    governance = before.get("governance")
    if not isinstance(governance, Mapping):
        raise ValueError(
            "the predecessor lacks governance; bootstrap approval must be handled externally"
        )
    evaluation = evaluate_approvals(
        governance,
        policy_key,
        approvals,
        expected_transition_id=transition_id,
        host_authenticated_approval_ids=host_authenticated_approval_ids,
    )
    policy = copy.deepcopy(governance["change_control"][policy_key])
    record = {
        "$schema": "../../schemas/idp-transition-v2.0.schema.json",
        "transition_version": "1.0",
        "transition_id": transition_id,
        "operation": selected_operation,
        "change_class": report.change_class,
        "instance_id_before": report.instance_id_before,
        "instance_id_after": report.instance_id_after,
        "from": {
            "identity_digest": report.identity_digest_before,
            "identity_digest_profile": before["continuity"]["identity_digest_profile"],
        },
        "to": {
            "identity_digest": report.identity_digest_after,
            "identity_digest_profile": after["continuity"]["identity_digest_profile"],
        },
        "changed_paths": list(report.changed_paths),
        "substantive_paths": list(report.substantive_paths),
        "identity_digest_changed": report.identity_digest_changed,
        "requested_by": copy.deepcopy(dict(requested_by)),
        "reason": reason,
        "recorded_at": recorded_at,
        "approvals": [copy.deepcopy(dict(item)) for item in approvals],
        "policy": {
            "policy_id": governance["policy_id"],
            "governance_version": governance["governance_version"],
            "policy_key": policy_key,
            **policy,
        },
        "evaluation": evaluation,
        "provenance": {
            "classifier": CLASSIFIER_PROFILE,
            "generated_by": "cpas.governance.create_transition_record",
            "source_refs": list(source_refs),
        },
    }
    validate_transition(record)
    return record


def validate_transition_against(
    record: Mapping[str, Any],
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> None:
    """Verify that a transition record describes the supplied declarations."""

    from .idp import validate_idp

    validate_idp(before)
    validate_idp(after)
    validate_transition(record)
    report = classify_declaration_change(before, after)
    expected = {
        "change_class": report.change_class,
        "instance_id_before": report.instance_id_before,
        "instance_id_after": report.instance_id_after,
        "changed_paths": list(report.changed_paths),
        "substantive_paths": list(report.substantive_paths),
        "identity_digest_changed": report.identity_digest_changed,
    }
    for field, value in expected.items():
        if record[field] != value:
            raise ValidationError(f"transition {field} does not match declarations")
    if record["from"]["identity_digest"] != report.identity_digest_before:
        raise ValidationError("transition from identity digest does not match predecessor")
    if record["to"]["identity_digest"] != report.identity_digest_after:
        raise ValidationError("transition to identity digest does not match successor")

    governance = before["governance"]
    policy_key = record["policy"]["policy_key"]
    expected_policy = {
        "policy_id": governance["policy_id"],
        "governance_version": governance["governance_version"],
        "policy_key": policy_key,
        **copy.deepcopy(governance["change_control"][policy_key]),
    }
    if record["policy"] != expected_policy:
        raise ValidationError("transition policy snapshot does not match predecessor")
    host_ids = (
        record["evaluation"]["authentication"]["approval_ids"]
        if record["evaluation"]["authentication"]["status"] == "host_asserted"
        else []
    )
    expected_evaluation = evaluate_approvals(
        governance,
        policy_key,
        record["approvals"],
        expected_transition_id=record["transition_id"],
        host_authenticated_approval_ids=host_ids,
    )
    if record["evaluation"] != expected_evaluation:
        raise ValidationError("transition approval evaluation does not match predecessor")
