# DKA-E storage threat model

**Scope:** `DKAStore` contract and `cpas-sqlite-rollback-single-host-v1`

**Out of scope:** model consciousness/identity claims, truth of DKA claims,
general host compromise prevention, identity-provider correctness, and legal
determinations.

## Assets and trust boundaries

Protected assets are canonical DKA payloads, classification, branch heads,
lineage, provenance, audit events, tenant separation, availability, backups,
and deletion state. Trust crosses these boundaries:

1. untrusted user/model/tool output → application host;
2. authenticated principal/policy engine → `StoreContext`;
3. application process → SQLite file/local filesystem;
4. live database → backup/restore/derived indexes/audit export; and
5. stored DKA data → model/runtime rehydration.

The application host, service account, OS/filesystem, and supplied context are
trusted for the reference profile. This is a significant assumption: a caller
able to forge `StoreContext` or write the database file is already inside the
profile's security boundary.

## Threats, controls, and residual risk

| Threat | Implemented control | Residual/external requirement |
|---|---|---|
| Lost update / concurrent branch fork | Transactional digest/profile CAS; race tests | Caller must explicitly rebase/merge; one-writer throughput ceiling |
| Partial snapshot/head/event commit | One `BEGIN IMMEDIATE` transaction | Filesystem/hardware must honor SQLite sync semantics |
| Orphan or profile-substituted lineage | Parent resolution scoped to tenant/DKA and digest profile | Imported histories need reviewed migration |
| Cross-tenant read/write | Database-per-tenant binding plus context match | Host filesystem/process isolation; path inventory |
| Sensitive metadata disclosure | Classification and canonical digest check before head/history/payload return | Denial versus absence can reveal that an ID exists; do not encode secrets in DKA IDs; DB file reader sees storage; encryption/host access external |
| Caller forges actor/audit attribution | Actor must equal context principal | Host must authenticate and prevent client-built contexts |
| Payload, head, or index tampering | Schema, canonical digest, index/payload tuple, latest-head, and file-identity verification | Privileged attacker can deny service or rewrite all state |
| Audit event modification/reordering | Sequence/domain-separated digest chain plus active-snapshot/event and tombstone/purge correlation | Unkeyed chain is not tamper-proof; export authenticated checkpoints |
| Prompt injection in persisted text | Structured untrusted-data envelope; no instruction authority/promotion | Host must preserve role separation and independently authorize tools |
| Stale/invalid state activated | Explicit evaluation; stale policy; invalidated/superseded exclusion | Trigger evaluation/evidence may still require human/trusted service |
| Database lock exhaustion | Bounded busy timeout and typed retryable failure | Rate limits, queues, load tests, monitoring, client/server migration trigger |
| Network-filesystem corruption | Profile forbids network/shared filesystems and requires affirmation | Deployment must actually inspect mount/storage topology |
| WAL-reset corruption | Profile rejects WAL; uses rollback journal | Other SQLite/VFS defects remain possible; patch/runtime monitoring |
| Backup corruption | Online copy then structural, FK, payload, head, and audit verification | Off-host durability, catalog, restore drills, RPO/RTO external |
| Backup/confidentiality breach | New `0600` file and explicit encryption warning | Encryption/key management and temporary-file protection external |
| Incomplete deletion | CAS purge, SQLite page scrubbing, tombstone, VACUUM, and explicit no-physical-erasure result | Deleted rollback journals, filesystem free space/media, backups, snapshots, exports, derivatives, and virtual-table traces external |
| DKA ID resurrection after purge | Permanent tenant-local tombstone | Cross-system identifiers and restored old backups require policy checks |
| Symlink/path substitution | Service-owned `0700` parent, symlink/hard-link rejection, `0600`, and bound device/inode checks before/after open | Privileged host replacement and ancestor/mount manipulation remain outside the process boundary |
| SQL injection | Parameterized SQL; identifiers are not interpolated | Maintain query discipline in future adapters/features |
| Denial by oversized payload/history | DKA schema plus bounded rehydration | Store-level payload/history quotas and disk quotas are not implemented |
| Rollback to old but internally valid database | Tenant/profile binding and audit sequence | External monotonic checkpoint/catalog required for rollback detection |

## Security claims deliberately not made

- A digest establishes integrity relative to an expected value, not authorship.
- An audit chain is not a signature, authentication, authorization, trusted
  timestamp, non-repudiation proof, or immutable ledger.
- Database-per-tenant isolation is not a sandbox against the service account,
  database administrator, operating system, or backup operator.
- `secure_delete`/`VACUUM` is not guaranteed erasure across storage media and
  copies.
- `local_filesystem=True` does not detect or attest a mount.
- Backup success is not recovery readiness until restore/promotion is drilled.
- Passing repository tests does not establish host hardening or production
  certification.

## Required security tests

The profile conformance suite exercises CAS races, busy locks, missing/forged
permissions, tenant mismatch, sensitive-head access, missing parents, payload
tampering, audit tampering, backup/restore, stale state, purge, and prompt-like
stored content. Deployments should add storage fault/power-loss testing, quota
exhaustion, authentication/policy integration, encrypted backup restore, audit
checkpoint verification, and incident recovery under their actual stack.
