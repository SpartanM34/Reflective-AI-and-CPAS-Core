# DKA-E store contract v1.0

**Status:** normative draft interface and failure model

**Record protocol:** [DKA-E v2.0](DKA-E-v2.0.md)

This contract separates portable DKA-E semantics from backend-specific storage
claims. A backend conforms only to a named profile whose required behavior has
passed its reproducible suite. Conformance does not certify the surrounding
deployment.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, and **MAY** are
normative within this draft.

## 1. Boundary

A store persists canonical CPAS state. It does not establish the declared
instance identity, authenticate a human or service, grant external authority,
or make a claim true. A production adapter receives a host-authenticated
principal and host policy decision, enforces the resulting store permissions,
and records non-secret audit references to both decisions.

The reference `FileDKAStore` implements local mechanics only. The selected
production-oriented profile is
[`cpas-sqlite-rollback-single-host-v1`](DKA-E-SQLite-Profile-v1.0.md).

## 2. Request context

Every production operation MUST receive a context containing:

| Field | Meaning | Security status |
|---|---|---|
| `tenant_id` | Storage isolation domain | Enforced by the adapter; not an authenticated identity by itself |
| `principal_id` | Host-authenticated actor identifier | An assertion from the trusted host boundary |
| `permissions` | Host policy decision expressed as store capabilities | Enforced by the adapter; MUST NOT be accepted directly from an untrusted client |
| `authentication_ref` | Audit reference to the host authentication event/method | Metadata only; not a credential or proof |
| `authorization_ref` | Audit reference to the evaluated policy/decision | Metadata only; not authorization by itself |
| `request_id` | Correlation/replay/audit identifier | Trace metadata; uniqueness is a host responsibility |
| `purpose` | Declared processing purpose | Audit metadata; not consent or legal basis by itself |

Credentials, bearer tokens, encryption keys, raw biometric data, and session
secrets MUST NOT be placed in this context or in DKA audit events.

## 3. Interface

The executable protocol is `cpas.dka_store.DKAStore`:

```python
head(dka_id, branch="main", *, context) -> Head | None
get(dka_id, branch="main", revision=None, *, context) -> DKA
put(record, *, expected_head, expected_head_profile=None,
    event_type="commit", actor="unspecified", context) -> Head
history(dka_id, branch="main", *, context) -> list[DKA]
events(dka_id, *, context) -> list[Event]
branch(dka_id, *, source_branch, target_branch, actor,
       updated_at, context) -> Head
```

Backend profiles MAY expose administrative operations such as `verify`,
`backup`, `restore_copy`, `purge`, and derived-index rebuild. Those operations
MUST declare additional permissions and failure semantics.

## 4. Atomicity and compare-and-swap

`put` MUST validate the DKA schema and content digest before mutation. Within
one atomic commit it MUST:

1. compare the current branch head digest/profile tuple with the expected tuple;
2. validate revision ordering and lineage;
3. verify every named parent digest/profile resolves inside the same tenant and
   DKA namespace;
4. insert exactly one immutable snapshot;
5. create or update exactly one branch head; and
6. append exactly one audit event.

No snapshot, head, or event from a failed transaction may become visible.
`expected_head=None` means the target branch MUST be absent; it is not a
last-write-wins request. Digest comparison MUST include the profile because a
digest string without its canonicalization/domain profile is ambiguous.

## 5. Lifecycle behavior

| Behavior | Normative requirement |
|---|---|
| Commit/revision | The new revision MUST be greater than the current revision and link to the current head tuple. |
| Branch | The new branch MUST pin an exact, already persisted parent tuple. A source advancing after the read does not retarget the branch silently. |
| Merge | The host constructs a three-way result with `merge_records`; every base/parent tuple MUST resolve, and `put(..., event_type="merge")` commits it. Contested values are not averaged or silently selected. |
| Staleness | Time-based evaluation is derived state and MUST NOT rewrite an immutable snapshot. |
| Invalidation/supersession | A reviewed revision records the state change. Normal rehydration MUST exclude `invalidated` and `superseded` records. |
| Deletion | A profile MUST state whether deletion is logical, physical, cryptographic, or unsupported and identify retained audit/backup/index data. |
| Corruption | Schema, digest, head/snapshot, parent, relational, or audit-chain mismatch MUST fail closed. The store MUST NOT guess or reseal data. |

## 6. Authorization semantics

Production profiles MUST deny missing context, tenant mismatch, and missing
permission. Authorization applies to head metadata, history, events, backups,
and derived indexes as well as payload reads. A classification copied into an
index is not a substitute for verifying the canonical payload and digest.

The reference permissions are:

| Permission | Operations |
|---|---|
| `dka:read` | Public/internal payload and head reads |
| `dka:read:sensitive` | Additional confidential/restricted reads |
| `dka:write` | Public/internal commits |
| `dka:write:sensitive` | Additional confidential/restricted commits |
| `dka:branch` | Branch creation, also requiring read/write |
| `dka:merge` | Merge commits, also requiring write access and two resolved merge parents |
| `dka:lifecycle` | Invalidation/supersession events, also requiring write access and matching record status |
| `dka:audit` | Audit event access |
| `dka:verify` | Full integrity verification, including sensitive payloads |
| `dka:backup` / `dka:restore` | Backup and recovery operations |
| `dka:retention` | Purge and post-purge compaction operations |
| `dka:migrate` | Explicit import/migration events, also requiring write access |
| `dka:*` | Administrative wildcard; MUST be restricted by the host |

The store MUST prevent a caller from attributing a mutation to an actor other
than the principal named by the trusted context.

## 7. Audit semantics

An audit event records the profile, tenant, operation, exact result and prior
head tuples, principal and decision references, request/purpose, time, and a
digest link to the prior event. The event chain detects accidental changes and
partial tampering when an expected root is retained. It is **not** an
authentication mechanism, signature, non-repudiation proof, or tamper-proof log.
A database administrator who can rewrite the whole chain can compute new
unkeyed digests. Deployments requiring stronger assurance MUST export and
authenticate checkpoints in a separately controlled audit system.
Profile verification MUST correlate every active canonical snapshot with its
mutation event and every tombstone with its purge event; checking each table in
isolation is insufficient.

## 8. Failure model

| Code / exception | Retry? | Meaning |
|---|---:|---|
| `record_not_found` / `RecordNotFound` | No | Requested canonical state is absent. |
| `head_conflict` / `HeadConflict` | No, until reread/rebase | Expected CAS tuple or branch absence did not match. |
| `access_denied` / `AccessDenied` | No | Context, tenant, classification, or permission check failed. |
| `corruption_detected` / `CorruptionDetected` | No | Integrity or internal consistency failed; quarantine/investigate. |
| `store_busy` / `StoreBusy` | Yes, bounded backoff | Backend could not acquire its write/maintenance lock. |
| `profile_violation` / `ProfileViolation` | No | Environment, lineage, or configuration violates the selected profile. |
| `recovery_error` / `RecoveryError` | Conditional | Backup/restore could not complete or verify. |
| `store_error` / `DKAStoreError` | Profile-specific | Non-classified backend failure; fail closed. |

Retries MUST reuse an idempotency/request policy at the host boundary and MUST
still perform CAS. A retry MUST NOT silently replace `expected_head` with the
new latest value.

## 9. Rehydration policy boundary

Every restored DKA is untrusted evidence/data with `instruction_authority=none`.
It MUST be placed only in a data/tool-result channel, never concatenated into
system or developer policy. Stored text, including text under `extensions`,
MUST NOT promote itself to instructions, tools, permissions, or policy.

The reference manifest returns a structured envelope, a `data_blocks` field,
and an explicit promotion prohibition. The legacy `context_blocks` name is a
compatibility alias only. Labels reduce ambiguity but are not a complete prompt
injection defense; the host MUST maintain role/channel separation and constrain
tool authority independently.

## 10. Conformance

A backend-profile claim MUST name the profile/version, database/runtime
versions, journal/consistency settings, filesystem/deployment topology, suite
commit, test command, date, and results. It MUST list external controls that
were not tested. “Production-ready,” without that evidence, is non-conformant.
