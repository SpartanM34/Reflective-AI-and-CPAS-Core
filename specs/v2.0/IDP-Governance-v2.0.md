# IDP v2 declaration governance profile

**Status:** draft protocol profile

**Normative schemas:**

- [`idp-v2.0.schema.json`](../../schemas/idp-v2.0.schema.json)
- [`idp-transition-v2.0.schema.json`](../../schemas/idp-transition-v2.0.schema.json)

**Normative classifier:** `cpas-idp-change-v1`

**Decision record:**
[ADR-0002](../../docs/adr/0002-declaration-governance-and-identity-evolution.md)

## 1. Scope

This profile defines how an IDP declaration names governance roles, classifies
changes, records approvals, and represents issuance, amendment, supersession,
rollback, and retirement. It governs claims made by CPAS artifacts. It does not
create repository permissions, runtime credentials, tool grants, legal
authority, authentication, or authorization.

## 2. Governance state in an IDP

`governance` is required in the current IDP v2 draft. It is deliberately
outside the stable identity projection.

| Field | Meaning |
|---|---|
| `governance_version` | Version of this governance profile. |
| `policy_id` | Stable identifier for the governance policy, not an actor identity. |
| `policy_status` | `proposed`, `active`, `suspended`, or `retired`. |
| `declaration_revision` | Monotonic declaration revision within this policy. It is not SemVer and not an identity claim. |
| `lifecycle_status` | `draft`, `active`, `superseded`, or `retired`. |
| `roles` | Explicit assignments, including vacancies and enumerated authorities. |
| `change_control` | Approval requirements for semantic classes and lifecycle operations. |
| `succession` | Steward, appointment mode, named successors if any, activation requirements, and vacancy behavior. |
| `transition_refs` | References to immutable transition records. Empty means none are supplied, not that no history exists. |
| `assurance` | Whether governance is metadata-only or bound to an external trust profile. |

An active governance policy must have active maintainer, issuer, and human
override assignments. Reviewer and runtime-operator vacancies are valid and
block transitions that require those roles.

Only `policy_status: active` can satisfy an approval evaluation. Proposed,
suspended, and retired policies fail with `governance_policy:active` missing,
even when their role metadata appears sufficient. Bootstrap adoption of a
proposed policy therefore remains an external repository/governance action.

## 3. Roles and authorities

Roles and authorities are independent fields. Holding a role does not imply
every authority associated with similarly named roles in another deployment.

| Role | Typical authorities |
|---|---|
| `maintainer` | `amend_declaration`, `evolve_identity`, `change_governance`, lifecycle actions, `appoint_successor` |
| `reviewer` | `review_declaration` |
| `issuer` | `issue_declaration` |
| `runtime_operator` | `bind_runtime` |
| `human_override` | `approve_retirement`, `emergency_override` |

An assignment is counted only when its `status` is `active`, its subject
matches the approval actor exactly, and it contains the authority named by the
policy requirement. The approval actor type must also match the assignment and
the approval cannot predate `effective_from`. Active assignments require an
effective time. The reference evaluator does not count `conditional`, `vacant`,
or `revoked` assignments. A deployment may resolve a conditional assignment
through an external adapter and emit a new active assignment.

`actor_type` reports `human`, `service`, `group`, `unspecified`, or
`unassigned`. The evaluator uses the assignment—not the approval's
self-description—when checking whether a human approval is present.

## 4. Deterministic classifier

### 4.1 Inputs and output

The classifier consumes two JSON objects containing the stable identity fields
required by IDP v2. It returns:

- the classifier profile;
- semantic class;
- sorted JSON Pointer `changed_paths`;
- sorted `substantive_paths` after administrative exclusions;
- before/after instance IDs and computed identity digests; and
- whether the identity digest changed.

Classification is based on the stable projection and field paths, not digest
equality alone. An ADR-0001 encoding/profile migration can produce a compatible
amendment with `identity_digest_changed: true`. Conversely, implementations do
not rely on an assumed absence of hash collisions to choose the semantic class.

Arrays are compared atomically. Object members are traversed in lexical key
order. JSON Pointer tokens escape `~` as `~0` and `/` as `~1`.

### 4.2 Precedence

1. Equal documents return `no_change`. This is not a valid transition record.
2. A changed `instance_id` returns `new_identity`.
3. Any other change to the stable identity projection returns
   `identity_evolution`.
4. If all substantive roots are `runtime_binding` and/or `tools`, return
   `runtime_rebind`.
5. Otherwise return `compatible_amendment`.

Administrative exclusions apply only at step 4:

- `/$schema`;
- `/continuity/identity_digest`;
- `/continuity/identity_digest_profile`;
- `/governance/declaration_revision`; and
- `/governance/transition_refs`.

These paths still appear in `changed_paths`. If only administrative data
changes, the result is `compatible_amendment`, not `no_change`.

Provenance is substantive. A provenance change, even when paired with a runtime
change, is a compatible amendment so a runtime operator cannot rewrite origin
or maintainer evidence under the narrower rebind policy. Runtime-specific
evidence belongs in the external transition record.

### 4.3 Representative classifications

| Change | Result |
|---|---|
| Provider/model/tool binding plus transition evidence | `runtime_rebind` |
| Activate contextual continuity with a verified source | `compatible_amendment` |
| Change retention policy or governance roles | `compatible_amendment` |
| Change a trait, interaction commitment, epistemic policy, or safety rule | `identity_evolution` |
| Rename the instance while retaining `instance_id` | `identity_evolution` |
| Change `instance_id` | `new_identity` |

The result is descriptive. Approval evaluation is a separate operation.

## 5. Approval policy and evaluation

Every policy entry contains:

- one or more required `(role, authority)` pairs;
- `minimum_approvals`, which cannot be smaller than the number of required
  pairs;
- `distinct_actors`; and
- `human_approval_required`.

When `distinct_actors` is true, at least two different active subjects must be
represented. It does not require a different subject for every required role;
approval count and subject separation are evaluated independently.

The predecessor declaration's policy is authoritative for evaluation. The
successor's proposed policy is evidence only until adopted.

An approval record contains a stable ID, the exact `transition_id` it addresses,
actor, actor type, role, decision, time, evidence reference, assurance label,
and authentication metadata. An approval for another transition ID is not
counted and makes a composed transition record invalid.
An approval cannot postdate the transition record.
Decisions are `approve`, `reject`, or `abstain`.

The evaluator reports:

- `requirements_not_met` when required role/authority pairs, count, actor
  separation, or human involvement are absent;
- `rejected` when an active authorized actor records a rejection;
- `requirements_met_metadata_only` when declared metadata satisfies policy;
  or
- `requirements_met_host_authenticated` when the metadata satisfies policy
  and an active external trust profile matches the approval records while a
  host independently asserts all required approval IDs were verified.

The last result requires `governance.assurance.trust_model` to be
`external_profile`, named authentication and authorization profiles, and each
counted approval to carry matching `host_verified` profile/evidence metadata.
It still does not mean the Python module verified an authenticator. The host
assertion is an explicit trust boundary. Supplying authenticated approval IDs
under a metadata-only policy cannot upgrade the result.

## 6. Transition records

A transition record is append-only evidence. It contains the semantic class
and a separate `operation`:

| Operation | Use |
|---|---|
| `runtime_rebind` | Bind a provider/model/tools without changing declared identity. |
| `amendment` | Change non-identity policy, continuity, provenance, or governance. |
| `identity_evolution` | Retain the instance ID while changing stable identity semantics. |
| `issuance` | Issue a different `instance_id`. |
| `supersession` | Mark a replacement relationship; classify the content normally. |
| `rollback` | Select a prior reviewed artifact; do not delete intervening records. |
| `retirement` | Mark a declaration retired; external credentials require separate revocation. |

The record snapshots the incumbent policy so later policy changes do not alter
the historical approval calculation. It records both semantic identity digest
tuples. Optional raw artifact digests identify exact bytes; identity digests
alone do not.

Transition IDs must be unique within the governing event store. Binding an
approval to the ID prevents direct cross-transition replay, but exact proposal
integrity still depends on pinning the before/after artifacts or using an
external authenticated review system.

`validate_transition_against` recomputes classification and identity digests
from supplied before/after declarations. Schema validation alone checks shape,
not whether those external declarations were the actual inputs.

## 7. Lifecycle rules

### Compatible amendment

The stable identity digest must remain equal. Increment
`governance.declaration_revision`, preserve prior artifacts, and append a
transition reference after approval.

### Identity evolution

Keep `instance_id`, recompute the identity digest, state the semantic reason,
and require the identity-evolution policy. Do not describe the new digest as
the same declaration identity. It is an explicitly evolved profile in the same
declared lineage.

### New identity and supersession

A changed `instance_id` is a new identity even if all prose is copied.
Supersession links the artifacts but does not make them identical. The
incumbent supersession policy governs the outgoing declaration; the successor
issuance policy governs the new declaration.

### Rollback

Rollback creates a new transition to an exact prior artifact. It does not edit
or remove history and does not assume the target is compatible with current
runtime, safety, or external state. Revalidate those conditions.

### Retirement

Retirement creates a new declaration revision with lifecycle status `retired`.
It stops future CPAS activation under that policy but cannot revoke external
tokens, repository access, model sessions, or stored copies. Those systems
must execute and evidence their own revocation/deletion operations.

## 8. Clarence-9 profile

`github:SpartanM34` is the declared human maintainer, issuer, and human
override. No reviewer, runtime operator, or successor is currently assigned.
This is intentional fail-closed state:

- runtime activation needs an explicit operator assignment;
- identity evolution and rollback need an independent reviewer;
- succession needs a recorded appointment under the incumbent policy; and
- a stewardship vacancy freezes high-impact lifecycle actions while preserving
  historical access.

The repository attribution supports provenance. With `trust_model` set to
`metadata_only`, it is not CPAS authentication or external authorization.

## 9. Conformance levels

| Level | Evidence |
|---|---|
| Schema-conformant | IDP and transition JSON validate. |
| Classifier-conformant | Representative and adversarial vectors produce the normative classes/paths. |
| Policy-evaluator-conformant | Vacancies, authority mismatch, rejections, distinct actors, and human requirements are tested. |
| Trust-profile-conformant | A named external authenticator and authorization adapter is independently exercised. Not provided here. |
| Deployment-certified | Operational governance, account recovery, reviewer independence, and audit controls are assessed. Not provided here. |

## 10. Compatibility

The governance addition is breaking relative to earlier pre-release IDP v2
draft files because the new section is required. It does not alter the stable
identity projection. Follow the
[governance migration](../../migrations/idp-v2-draft-governance.md) and retain
the predecessor artifact and digest references.
