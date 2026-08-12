# DKA-E SQLite rollback single-host profile v1.0

**Profile ID:** `cpas-sqlite-rollback-single-host-v1`

**Status:** production-oriented backend profile; reference implementation tested,
deployment certification external

**Store contract:** [DKA-E store contract v1.0](DKA-Store-Contract-v1.0.md)

## 1. Selection decision

This profile selects SQLite with the `DELETE` rollback journal for a narrowly
defined deployment: application and database on one host and local filesystem,
low or moderate writer concurrency, and one database file per tenant.

The selection is evidence-driven:

- SQLite describes device-local storage with low writer concurrency as an
  appropriate use and states that only one writer operates at a time.
  [SQLite: Appropriate Uses](https://sqlite.org/whentouse.html)
- SQLite warns against direct multi-host/network-filesystem access and advises
  a client/server database when data is separated from the application.
  [SQLite Over a Network](https://sqlite.org/useovernet.html)
- `BEGIN IMMEDIATE` acquires the write transaction at its start, while competing
  writers receive `SQLITE_BUSY`; the adapter maps that to a retryable bounded
  failure. [SQLite transactions](https://sqlite.org/lang_transaction.html)
- Rollback journal plus `synchronous=EXTRA` adds a directory sync after journal
  unlink and is SQLite's stronger documented rollback durability setting.
  [SQLite PRAGMA synchronous](https://sqlite.org/pragma.html#pragma_synchronous)
- SQLite supplies an online backup API, `integrity_check`,
  `foreign_key_check`, `secure_delete`, and `VACUUM`; each has limits reflected
  below. [Backup API](https://sqlite.org/backup.html),
  [integrity checks](https://sqlite.org/pragma.html#pragma_integrity_check),
  [VACUUM](https://sqlite.org/lang_vacuum.html)

### Why this is not a WAL profile

The available verification runtime links SQLite 3.50.4. SQLite's March 2026
advisory says a rare WAL-reset corruption bug affects WAL versions through
3.51.2, with fixes in 3.51.3 and backports including 3.50.7 and 3.44.6.
[SQLite WAL documentation and advisory](https://sqlite.org/wal.html#walreset)
This implementation therefore requires rollback journal mode and rejects a
database bound to WAL. A future WAL profile requires a fixed build and separate
conformance evidence; it is not an automatic setting change.

### Why PostgreSQL is not claimed here

PostgreSQL is the likely next profile for multi-host service deployments,
engine-enforced roles/row security, and higher write concurrency. No PostgreSQL
server, client, driver, or container runtime was available in the verification
environment. Publishing an adapter without executing it would not meet issue
#99's named-backend acceptance criterion. This is an implementation/evidence
limit, not a conclusion that SQLite is universally preferable.

## 2. Required topology and settings

| Requirement | Profile value |
|---|---|
| SQLite | `>=3.31.0`; exact linked version reported |
| Operating system | POSIX file ownership/mode semantics; v1 reference adapter rejects other platforms |
| Journal | `DELETE`; WAL, memory, and journal-off modes forbidden |
| Sync | `EXTRA` on every connection |
| Transactions | `BEGIN IMMEDIATE` for mutation; bounded busy timeout |
| Filesystem | Local filesystem on the same host as the issuing process/application service |
| Tenancy | One database file permanently bound to one `tenant_id` |
| File/directory | Service-owned `0600` file in a service-owned `0700` directory; final path/parent symlinks, hard-linked DB files, and post-binding inode replacement rejected |
| Foreign keys | Enabled on every connection and checked during verification |
| Trusted schema | Disabled on every connection |
| Secure delete | Enabled on every connection; see deletion limits |
| Temporary data | Memory-backed SQLite temporary store |
| Payload | Canonical DKA JSON plus digest/profile columns |

`local_filesystem=True` is an operator affirmation, not reliable mount-type
detection. Deployment tooling MUST validate the actual mount and storage stack.
Network filesystems, shared volumes concurrently mounted by multiple hosts, and
direct client access to the database file violate this profile.

## 3. Data model

- `metadata` binds profile/version/schema/tenant and creation time.
- `snapshots` stores immutable canonical JSON, digest/profile,
  classification, and revision key.
- `heads` points to one snapshot per DKA/branch with a foreign key.
- `audit_events` stores a global per-database sequence and digest-linked event.
- `tombstones` prevents silent recreation after policy purge.
- ordinary B-tree indexes accelerate digest and event lookup; they are covered
  by purge/VACUUM but are not semantic/vector search indexes.

Snapshot, head, and event are written in one transaction. CAS compares both
digest and digest profile. All parent tuples must resolve inside the same
tenant-bound database and DKA ID.

## 4. Security boundary

Authentication is external. The adapter requires a `StoreContext`, enforces
its tenant and permissions, and records authentication/authorization references.
Those references and the context are host assertions; they do not become proof
because they were stored.

Tenant isolation is database-per-tenant plus context matching. It protects
against cross-tenant query mistakes in the adapter, not a hostile operating
system user with file access. Host process isolation and least-privilege file
ownership remain required.

SQLite in this profile provides no built-in at-rest encryption or key manager.
Production deployments handling non-public data MUST use an assessed encrypted
volume/filesystem or a separately specified encrypted SQLite build, with keys
outside the repository/database and independently protected backups. Transport
encryption belongs to the application/API boundary because the database is not
accessed over a network.

## 5. Concurrency, lifecycle, and failure

Readers may run concurrently, but writers serialize. A writer holds one short
`BEGIN IMMEDIATE` transaction for validation, snapshot/head mutation, and the
audit append. `SQLITE_BUSY` and `SQLITE_LOCKED` map to retryable `StoreBusy`;
CAS conflict is non-retryable until the caller rereads/rebases.

Branch creation pins the exact source snapshot. Merge uses the portable
three-way merge routine, verifies all named parents are stored, and commits a
`merge` event. Staleness is evaluated without mutation. Invalidated and
superseded snapshots are excluded from normal rehydration; historical access
remains an explicit authorized read.

## 6. Backup and recovery

`backup(destination)`:

1. requires `dka:backup` and a new `0600` destination;
2. uses SQLite's online backup API;
3. syncs and reopens the copy;
4. runs database integrity, foreign-key, every snapshot digest/index tuple,
   every head tuple, event/snapshot correlation, tombstone/purge correlation,
   and audit-chain checks; and
5. returns a raw SHA-256 file digest and an explicit
   `encryption=external-control-required` marker.

Both backup and restore write a same-directory temporary file and publish by an
atomic no-clobber link only after verification. `restore_copy` also verifies
that the source did not change, appends a restore event before publication, and
never overwrites the active database. A backup may be validly published even if
the subsequent live-store backup audit append fails; that condition is returned
as `RecoveryError` and requires operator reconciliation. Operator-controlled
promotion/swap, RPO/RTO, backup encryption,
off-host replication, restore drills, retention, and media disposal are outside
the library and MUST be documented by the deployment.

## 7. Retention, deletion, and derived indexes

`purge` requires a CAS map for every current branch, deletes snapshots and
heads, retains a minimal tombstone and content-free audit metadata, and blocks
recreation of the DKA ID. `secure_delete=ON` overwrites ordinary deleted table
content; `compact_after_purge` runs `VACUUM` against the live file and explicitly
reports that physical erasure is not guaranteed.

These operations do **not** guarantee erasure from deleted rollback journals,
filesystem free space/storage media, prior backups, filesystem snapshots, audit
exports, crash dumps, logs, or external indexes. SQLite also documents limits
for secure deletion of virtual-table shadow data. Deployments MUST expire every
copy under the same retention decision. Audit reasons SHOULD use policy codes,
not sensitive prose.

No vector/full-text/embedding index is implemented. Any derived index MUST be
rebuildable, carry tenant/classification/source digest/creation metadata, deny
access at least as strictly as its source, and participate in purge and backup
policy. Derived output never becomes canonical DKA state.

## 8. Prompt-injection boundary

Rehydration emits structured, canonical JSON envelopes marked
`content_trust=untrusted`, `instruction_authority=none`, and
`policy_promotion=forbidden`. Hosts MUST place them only as data/tool results.
Neither a stored “rehydration instruction” nor any prompt-like claim can grant
tools, change system policy, or promote itself. Labels alone are not sufficient;
role/channel separation and independent tool authorization are deployment
requirements.

## 9. Reproducible conformance

The named suite is:

```bash
python -m pytest -q tests/test_cpas_v2_sqlite_store.py
```

It covers profile settings, local-only affirmation, tenant/file binding,
permissions and classification, atomic CAS and races, busy behavior,
lineage/branch/merge/invalidation, audit and canonical-state correlation,
payload/event/head tampering, no-clobber backup/restore, purge/compaction, stale
state, access-denied rehydration, and the no-policy-promotion envelope.

Passing this suite is **implementation-tested** conformance. Deployment
certification still requires the operational controls in
[`docs/operations/DKA-E-SQLite-Profile-v1.0.md`](../../docs/operations/DKA-E-SQLite-Profile-v1.0.md).
Existing file reference stores can use the non-destructive
[FileDKAStore migration](../../migrations/FileDKAStore-to-SQLite-v1.md).
