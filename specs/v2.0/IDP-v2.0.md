# Instance Declaration Protocol v2.0

**Status:** draft protocol

**Normative schema:** [`schemas/idp-v2.0.schema.json`](../../schemas/idp-v2.0.schema.json)

## Purpose

IDP v2 declares a reconstructable interaction identity and its epistemic policy,
then binds that declaration to currently available state and infrastructure. It
does not prove consciousness, persistence, ownership, authentication, or tool
authority.

The stable identity projection consists of:

- `idp_version`, `instance_id`, and `instance_name`;
- `identity_profile`;
- `epistemic_policy`;
- `safety`.

`runtime_binding`, continuity availability, memory, and tools are deliberately
outside that projection. Governance roles, approval policy, and lifecycle state
are also outside it so stewardship can change without pretending the
interaction identity changed. Replacing any excluded section must not change
the identity digest, although it can change behavior, trust, or activation and
requires the applicable governance/compatibility validation.

## Sections

| Section | Semantics |
|---|---|
| `identity_profile` | Human-readable identity summary, reconstruction mode, traits/commitments, and explicit non-claims. |
| `epistemic_policy` | Transparency boundary, uncertainty treatment, scales, metaphor mode, and collaboration rules. |
| `runtime_binding` | Provider/model/version observation, capabilities, constraints, compatibility profile, and validation time. Null means unbound—not unlimited. |
| `continuity` | Four continuity forms and four state layers, each reported independently. |
| `memory_policy` | Retention, retrieval, deletion, and sensitive-data expectations. Enforcement belongs to the host/store. |
| `tools` | Names, observed status, input-schema availability, constraints, and externally granted authority. |
| `safety` | Human authority, stored-content treatment, and freshness rules. |
| `governance` | Declared roles, enumerated authorities, change-control rules, lifecycle state, succession, transition references, and assurance limits. |
| `protocol_compatibility` | Versions an implementation can parse/emit; this is not proof of full conformance. |
| `provenance` | Authors, maintainer, timestamp, historical source paths/revisions/digests, and canonicalization profile. |
| `extensions` | Namespaced data that remains outside core semantics. |

## Identity digest

New declarations serialize the stable projection with `rfc8785-jcs-v1` and use
the domain-separated profile `cpas-digest-v2:idp-identity`. The exact byte frame
is normative in
[ADR-0001](../../docs/adr/0001-canonicalization-and-digest-profiles.md).
`continuity.identity_digest_profile` must travel with the digest.

Legacy v2 draft declarations using `cpas-canonical-json-v1` remain readable.
An omitted profile on those declarations resolves to
`cpas-sha256-direct-v1`; it must not be relabeled as a JCS value. Two
declarations can retain the same semantic stable projection across this
encoding migration even though their digest strings differ.

The digest provides reproducible comparison. It authenticates neither the
declaration nor its maintainer.

## Declaration governance and evolution

The governance section and transition-record schema implement
`cpas-idp-change-v1`. The classifier deterministically reports runtime rebind,
compatible amendment, identity evolution, or new identity; it does not decide
whether a transition is authorized. Approval evaluation uses the predecessor's
policy and distinguishes metadata sufficiency from authentication performed by
an external host.

Clarence-9 currently declares Spartan-M34 as maintainer, issuer, and human
override. Reviewer and runtime-operator assignments are vacant, so operations
that require them fail closed. No successor is inferred from repository access
or model/runtime operation.

The normative semantics, lifecycle rules, and assurance boundary are in the
[IDP governance profile](IDP-Governance-v2.0.md) and
[ADR-0002](../../docs/adr/0002-declaration-governance-and-identity-evolution.md).

## Capability negotiation

Capabilities progress through `unknown`, `declared`, `probed`, `verified`, or
`unavailable`. Consumers request required and optional capabilities. Missing
required capabilities create an explicit degraded/blocked result; they must not
be simulated based on model name. Evidence should identify the check and its
date.

## Transparency boundary

IDP v2 requires useful epistemic disclosure—assumptions, evidence, uncertainty,
confidence qualifications, alternatives, blind spots, provenance, concise
reasoning summaries, and decision criteria—as appropriate to the task. It
forbids making hidden chain-of-thought disclosure or persistence an identity
requirement.

## Migration from IDP v1.0

| v1.0 source | v2 destination | Rule |
|---|---|---|
| `identity.name` or equivalent | `instance_name` | Copy without normalizing historical spelling. |
| identity/model family | `runtime_binding.model` and `extensions.legacy_idp_v1` | Remove from stable identity; label status `declared` unless independently tested. |
| alignment/identity prose | `identity_profile`, `epistemic_policy`, `safety` | Automated migration uses conservative defaults; human review is required. |
| reflection/transparency prose | `epistemic_policy.transparency` | Translate to outward epistemic disclosure; do not migrate a demand for hidden traces. |
| memory/continuity prose | `continuity` | Default only declarative continuity to active unless concrete context/store evidence is provided. |
| token/hash fields | legacy extension or SeedToken v2 | Never upgrade a legacy hash into authentication. |
| unknown fields | `extensions.legacy_idp_v1` | Retain the complete original document to prevent silent loss. |
| absent declaration governance | `governance` | Emit a proposed metadata-only policy; leave reviewer/runtime operator vacant and require human review. |

The migration utility at
[`migrations/migrate_idp_v1_to_v2.py`](../../migrations/migrate_idp_v1_to_v2.py)
produces a reviewable draft. It does not claim semantic equivalence or runtime
validation. It emits JCS/domain-separated identity digests by default and has
an explicit legacy option for bounded compatibility. See the
[canonicalization migration](../../migrations/canonicalization-v1-to-jcs-v1.md).
Earlier IDP v2 drafts without governance require the separate
[governance migration](../../migrations/idp-v2-draft-governance.md); adding the
section does not alter the stable identity projection but does change exact file
digests.

## Compatibility

An IDP v2 consumer may ingest v1 through an explicit adapter. A v1 consumer
cannot safely infer v2 continuity, memory, safety, or capability semantics, so
down-conversion is lossy and must be labeled as such. Unknown v2 extensions may
be retained; unknown core fields are rejected to catch mistakes.
