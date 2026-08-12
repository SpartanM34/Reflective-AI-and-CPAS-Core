# ADR-0002: declaration governance and identity evolution

- **Status:** Accepted for the CPAS v2 draft when this change is merged
- **Decision scope:** IDP v2 authority metadata, declaration change
  classification, transition records, lifecycle actions, and Clarence-9
  stewardship
- **Issue:** [#98](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/issues/98)
- **Date:** 2026-08-12

## Context

IDP v2 already separates the stable identity projection from runtime/model/tool
bindings. It can therefore detect that a stable identity digest did or did not
change. That binary result is insufficient for governance:

- it does not distinguish a runtime rebind from a continuity, provenance, or
  governance amendment;
- `provenance.maintainer` names a party but does not define authority;
- no rule says who may issue, review, supersede, roll back, or retire a
  declaration;
- no transition artifact records requested changes and approvals; and
- a Git author, repository account, digest, or merged pull request is not by
  itself a CPAS authentication or authorization mechanism.

These gaps permit symbolic stewardship language to be mistaken for an
implemented control. They also make runtime replacement and identity evolution
look deceptively similar when both produce a new JSON file.

## Decision

### 1. Keep governance outside declared identity

IDP v2 adds a required `governance` section, but the stable identity projection
remains:

- `idp_version`;
- `instance_id` and `instance_name`;
- `identity_profile`;
- `epistemic_policy`; and
- `safety`.

Changing role assignments, approval thresholds, succession metadata, or
declaration lifecycle state does not by itself claim that the interaction
identity changed. It is a compatible amendment and must be reviewed under the
incumbent governance policy.

This exclusion is not a security shortcut. An identity digest cannot detect
governance substitution. Consumers that need exact-file integrity must pin the
declaration artifact digest or retrieve it through a trusted repository/channel.
Authentication and authorization remain separate controls.

### 2. Define five roles without manufacturing authority

The core governance vocabulary is:

| Role | Protocol responsibility | What the declaration does **not** grant |
|---|---|---|
| Maintainer | Amend policy/metadata and manage lifecycle proposals | Repository write access |
| Reviewer | Provide an explicit review decision | Independence merely because a second model produced output |
| Issuer | Issue a new declaration or successor | Authentication of the named subject |
| Runtime operator | Bind/probe a runtime under external host grants | Tool, model, data, or deployment authority |
| Human override | Record consequential human intervention | Power to bypass law, platform safety, or external access controls |

A role assignment has a subject, actor type, status, enumerated authorities,
effective time, and evidence reference. Vacancies are explicit. A role may be
`conditional`, but the reference evaluator counts only `active` assignments.
The approval subject/type must match, its authority must be assigned, and its
timestamp cannot precede assignment or postdate the transition record.

### 3. Freeze deterministic change-classification precedence

`cpas-idp-change-v1` compares two JSON declarations and reports sorted JSON
Pointer paths. Classification uses this precedence:

| Condition | Classification | Identity digest |
|---|---|---|
| Documents are equal | `no_change` (non-transition result) | unchanged |
| `instance_id` differs | `new_identity` | normally changes; class is based on semantics, not collision assumptions |
| Any other stable identity field differs | `identity_evolution` | normally changes; class is based on semantics, not collision assumptions |
| Only substantive `runtime_binding` and/or `tools` fields differ | `runtime_rebind` | unchanged within one digest profile |
| Any other non-empty change | `compatible_amendment` | usually unchanged; an explicit digest-profile migration changes bytes |

For runtime-only classification, `$schema`, the derived identity
digest/profile, declaration revision, and transition references are
administrative evidence. They are reported in `changed_paths` but excluded
from `substantive_paths`. A substantive continuity, memory, protocol,
governance, or lifecycle change is a compatible amendment, not a runtime
rebind.

Provenance changes are substantive. A runtime operator cannot rewrite source or
maintainer provenance under the narrower runtime-rebind policy; runtime review
evidence belongs in the transition record.

`new_identity` takes precedence over all other changes. A changed name,
identity profile, epistemic policy, or safety policy with the same
`instance_id` is identity evolution. The classifier describes semantics; it
does not approve the result and never treats digest inequality alone as
identity evolution. ADR-0001 profile migration can change a digest while the
stable projection remains equal.

### 4. Evaluate the predecessor's policy

The predecessor declaration's governance policy determines the requirements
for a transition. A proposed declaration cannot authorize its own governance
replacement. Pre-governance draft documents require an explicit bootstrap
review through the repository's actual authority; the reference code refuses
to fabricate that approval.

Only an `active` policy can satisfy the evaluator. Proposed, suspended, and
retired policies remain inspectable but cannot authorize a transition.

Each policy names required `(role, authority)` pairs, minimum approval count,
whether actors must be distinct, and whether a human assignment is required.
`distinct_actors: true` requires at least two subjects; it does not require one
unique subject per role. This permits one maintainer to hold issuer authority
while still requiring a separate reviewer.
An authorized rejection blocks the transition. Vacant, conditional, revoked,
wrong-role, wrong-authority, and unknown-subject approvals do not count.

### 5. Separate semantic class from lifecycle operation

Classification describes the content difference. `operation` describes why
the transition is being performed:

- ordinary `runtime_rebind`, `amendment`, `identity_evolution`, or `issuance`;
- `supersession`, which links an incumbent to a replacement;
- `rollback`, which selects a previously reviewed artifact rather than erasing
  intervening provenance; or
- `retirement`, which produces a new, retired declaration record and does not
  delete history.

Supersession and rollback do not imply semantic equivalence. Their target is
classified normally and the lifecycle-specific approval policy is applied.
Retirement does not revoke external credentials automatically; operators must
perform that action in the systems that own those credentials.

### 6. Make transition evidence portable and inspectable

[`idp-transition-v2.0.schema.json`](../../schemas/idp-transition-v2.0.schema.json)
records:

- before/after instance IDs and identity digest tuples;
- operation and deterministic change class;
- complete and substantive changed paths;
- requester, reason, time, and source references;
- approval records and a snapshot of the incumbent policy; and
- evaluation results, including missing roles, rejections, unauthorized
  records, distinct-actor status, human involvement, and authentication state.

The record identifies identity semantics. Exact declaration bytes may be
identified separately with `raw-sha256`; absence of an artifact digest is
explicit and must not be interpreted as exact-file verification.

Every approval names the transition ID it addresses. Reuse under another ID is
rejected. Event stores must enforce transition-ID uniqueness, and deployments
that require exact proposal binding must also pin before/after artifact digests
or rely on an authenticated external review system.

### 7. Treat approvals as metadata until a host verifies them

The reference implementation can determine whether approval metadata matches
declared active roles and policy requirements. Its default successful status is
`requirements_met_metadata_only`.

Only a host trust adapter may supply approval IDs it independently verified.
The evaluator reports `requirements_met_host_authenticated` only when the
incumbent governance policy activates an external trust profile and every
counted approval carries matching `host_verified` profile/evidence metadata.
This is still an assertion about adapter input, not signature verification
implemented by CPAS. Supplying IDs under a metadata-only policy cannot upgrade
the result. No such profile is active for Clarence-9 in this repository.

Role metadata, approval sufficiency, authentication, external authorization,
and provenance are separate claims.

### 8. Adopt a conservative Clarence-9 stewardship policy

The current Clarence-9 declaration names `github:SpartanM34` as active human
maintainer, issuer, and human override. The reviewer and runtime-operator roles
are vacant. Therefore:

- compatible amendments can be proposed under maintainer authority;
- runtime rebinding remains blocked until an active operator is named;
- identity evolution, new identity, supersession, and rollback remain blocked
  until a distinct reviewer is appointed; and
- no successor is currently designated.

Succession requires an attributable appointment by Spartan-M34 or an actual
repository-owner action, an incumbent-policy amendment, and explicit review
evidence. If stewardship becomes vacant without that record, the declaration
is preserved as historical and high-impact lifecycle actions freeze. Existing
runtime grants neither transfer stewardship nor become CPAS authority.

The single-steward arrangement remains a concentration-of-authority risk. This
ADR exposes that fact rather than inventing a council or reviewer.

## Threat and failure model

| Threat/failure | Protocol mitigation | Residual boundary |
|---|---|---|
| Proposed policy lowers its own threshold | Evaluate the predecessor policy | Bootstrap from a pre-governance artifact still requires real repository authority |
| Forged actor/approval metadata | Default result remains `requirements_met_metadata_only` | A host trust profile must authenticate actors; CPAS core does not |
| Role or authority substitution | Exact active subject, role, actor type, and enumerated authority must match | Compromised incumbent policy/channel can still name a malicious subject |
| Approval replay | Approval must bind to the transition ID; IDs are unique within the store | Exact proposal binding additionally needs artifact digests/authenticated review |
| Stale or wrong predecessor | Transition carries before digest tuple and incumbent policy snapshot | Identity digest does not pin governance or exact file bytes |
| Runtime change mislabeled as continuity | Classifier reports all paths and distinguishes substantive roots | Behavioral compatibility still needs the separate runtime harness |
| Single-actor self-review | High-impact policies require at least two subjects | Reviewer independence and competence are deployment decisions |
| Authorized rejection omitted | Matching rejection makes evaluation `rejected` | Completeness depends on the event/review channel supplying all records |
| Emergency override abuse | Override is an explicit role/authority and does not bypass law/platform controls | External systems must enforce their own permissions and audit |
| Retirement mistaken for revocation/deletion | Retirement is only an IDP lifecycle record | Credentials, data, replicas, and immutable history require external actions |
| Governance file substitution | Pin raw artifact digest or use a trusted repository/channel | No signed governance envelope is implemented in this profile |

Transition IDs, evidence references, and timestamps improve provenance but are
not freshness, uniqueness, or authorization proofs unless the surrounding store
enforces those properties.

## Compatibility and migration

Adding required governance is a breaking change within the pre-release IDP v2
draft schema. Historical v1.0 declarations remain unchanged. The v1 migration
utility now emits a proposed, metadata-only governance policy; it leaves
reviewer and runtime-operator roles vacant and requires human review.

Earlier v2 draft declarations must be migrated by adding governance without
changing the stable identity projection. Their identity digest remains stable
under the same canonicalization/digest profile, while the exact file digest
and any SeedToken that pins that file must be resealed.

## Rejected alternatives

- **Put governance in the stable identity digest.** This would turn routine
  maintainer succession into identity evolution and conflate stewardship with
  interaction identity.
- **Treat Git/GitHub attribution as authentication.** Repository metadata is
  useful provenance, but CPAS does not possess or verify the platform's trust
  roots, account controls, or signing policy.
- **Let the proposed policy govern its own adoption.** That is circular and
  permits a replacement to lower its approval threshold before evaluation.
- **Classify every digest-preserving change as a runtime rebind.** Continuity,
  memory, provenance, governance, and lifecycle changes have different review
  consequences.
- **Add public-key signatures in this workstream.** Key ownership, rotation,
  revocation, recovery, and trust roots remain unresolved and belong to a
  separately reviewed trust profile.

## Consequences and remaining limits

- Governance and transition shape are machine-testable.
- Deterministic classification does not establish that a change is wise or
  behaviorally compatible.
- A matching approval record does not prove the actor authored it.
- The current Clarence-9 policy deliberately cannot complete identity evolution
  without appointing a reviewer.
- External consumers of the earlier v2 draft may require migration.
- Public-key trust, emergency succession, reviewer selection, and repository
  account-recovery policy remain unresolved production decisions.
