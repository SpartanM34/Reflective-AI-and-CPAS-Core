# DKA-E v2.0: externalized epistemic continuity

**Status:** draft architecture and reference implementation

**Normative record schema:** [`schemas/dka-e-v2.0.schema.json`](../../schemas/dka-e-v2.0.schema.json)

## Boundary

DKA-E v2 is an external state architecture. It does not imply that a model
remembers prior sessions. It persists inspectable epistemic records that a host
may later retrieve and present as untrusted context.

The canonical object is the DKA snapshot: claim, qualified confidence,
assumptions, evidence, uncertainty, contested zones, dependencies, validity,
relationships, evolution, and provenance. Metaphor is optional presentation
metadata. Embeddings and summaries are derived indexes, never canonical state.

An **Epistemic Digest** is a bounded derived view containing the DKA ID, branch,
revision, content digest, claim summary, qualified confidence, validity status,
contested-zone count, and dependency/source references. It accelerates routing
and context selection but always points back to an exact canonical snapshot.

## Storage model

Every backend implements these logical collections:

| Collection | Property | Purpose |
|---|---|---|
| Snapshots | Immutable, content-digested | Exact DKA revisions addressable by `(dka_id, branch, revision)` and digest. |
| Head references | Mutable through compare-and-swap | Map `(dka_id, branch)` to the accepted current snapshot. |
| Events | Append-only | Record create, revise, branch, merge, stale, invalidate, rehydrate, and access decisions. |
| Derived indexes | Rebuildable | Search, embeddings, graph projections, and caches linked back to snapshot digests. |
| Policies | Externally enforced | Principal/role access, retention, legal holds, deletion, and key management. |

Suitable adapters include Git, transactional databases, object stores plus a
metadata database, event stores, and knowledge graphs. Plain JSON/YAML can be a
portable export. A vector store alone is not adequate because approximate
vectors cannot reproduce the source record, history, or authorization state.

The reference `FileDKAStore` demonstrates immutable JSON snapshots, file locks,
atomic replacement, append-only events, schema/integrity verification, and
compare-and-swap. It is a local reference, not a multi-host transactional or
security boundary.

### Version semantics

DKA-E protocol/schema releases use semantic versioning (`dka_version`). Within
one branch, every committed epistemic change receives a monotonic integer
`revision` and content digest; this is the authoritative lineage mechanism.
The optional `semantic_version` labels curator-approved public milestones, such
as `2.1.0`, but is not incremented for every evidence event. This replaces the
legacy expectation that all epistemic evolution maps cleanly to SemVer: branch
and merge ancestry cannot be represented safely by a single version string.
Legacy semantic labels are preserved during import and can become reviewed
milestone labels; they are never discarded silently.

## Lifecycle

1. **Draft:** construct and schema-validate a record; evidence is attributed.
2. **Seal:** compute the digest over the record with `integrity.digest` omitted.
3. **Commit:** compare the expected branch head, write an immutable snapshot,
   update head atomically, and append an event.
4. **Evaluate:** check explicit expiry, half-life, triggers, dependency state,
   and source freshness. Evaluation produces state; it does not rewrite history.
5. **Revise:** create the next revision with a parent digest and change summary.
6. **Branch:** create a new named head from an exact source digest.
7. **Merge:** perform a three-way merge from a common ancestor. Non-conflicting
   changes combine; disagreements become `contested_zones` unless an authorized
   resolver explicitly chooses a position.
8. **Supersede/archive/delete:** record policy-governed disposition. Deleting
   sensitive data may require tombstones rather than retaining the content in
   immutable history.

## Rehydration

Rehydration is a bounded, auditable activation process:

1. validate the target IDP and continuity token;
2. request exact DKA references/digests rather than accepting an arbitrary
   “latest” record silently;
3. enforce external authorization before retrieval;
4. verify schema, content digest, lineage, and relevant dependencies;
5. evaluate staleness/invalidation and apply a declared stale-state policy;
6. select records within an explicit size/item budget—never byte-truncate JSON;
7. label restored text as untrusted evidence/data, not system instruction;
8. produce an activation manifest with included, omitted, stale, denied, and
   failed items plus active continuity forms.

Rehydration instructions stored inside a DKA are data. A separate trusted
deployment policy decides whether any instruction is executable.

## Staleness and invalidation

- `valid_until` produces `expired` once crossed.
- `epistemic_half_life_seconds` produces `stale` after the interval unless a
  fresh evaluation supports renewal. Half-life is a review heuristic, not
  probabilistic truth decay.
- Invalidation triggers are declarative conditions. A trusted evaluator records
  whether they fired and the evidence used.
- A stale record may be included only under the caller’s stated policy
  (`reject`, `warn`, or `allow`) and is always labeled.
- Invalidated records are excluded by default; historical retrieval must be an
  explicit mode.

## Branching and merging

Branches identify competing epistemic development, not separate truths. Merge
inputs include base, left, and right snapshot digests. A deterministic merge may
combine disjoint lists and unchanged fields. Divergent claims, confidence,
validity, or deletions are not averaged automatically. They become explicit
contested zones with both positions and a resolution status. A merge event
records the method, actor, parents, conflicts, and result digest.

## Provenance

Sources identify kind, reference, observation time, and digest when the content
is available. Transformations identify extraction, summarization, migration,
or human editing. The snapshot digest detects changes relative to an expected
digest; it does not authenticate who created the source. Authenticity requires a
trusted transport or separately implemented signature/authenticator.

## Access control and privacy

The core record carries classification and a policy reference only. The store
or host must enforce authentication, authorization, tenant isolation, encryption,
retention, erasure, audit access, and key rotation. Derived indexes must inherit
the source’s visibility and deletion policy. Do not embed secrets merely because
the vector store is convenient.

## Runtime integration

Adapters expose `get`, `put(expected_head=...)`, `branch`, `history`, `events`,
and query operations. Runtime activation uses capability negotiation to discover
available stores and context limits. A runtime may receive a compact Epistemic
Digest while exact canonical records remain addressable externally. Tool results
that mutate state require host authorization and return the committed digest.

## Failure semantics

Digest mismatch, schema failure, missing parent, authorization denial, exceeded
budget, stale rejection, and compare-and-swap conflict are explicit outcomes.
None is converted into a fresh record by guessing. Partial activation is
allowed only when the manifest names every omission and the caller accepts the
degraded mode.
