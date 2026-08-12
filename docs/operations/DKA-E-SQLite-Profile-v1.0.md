# Operating the DKA-E SQLite rollback single-host profile

This runbook applies only to `cpas-sqlite-rollback-single-host-v1`. Passing the
repository suite establishes reference implementation behavior. It does not
certify a host, filesystem, identity provider, backup system, or legal/privacy
program.

## 1. Deployment gate

Do not deploy until every item has an owner and evidence:

- The application process and database file are on the same host and the file
  is not on NFS, SMB, a concurrently mounted shared volume, or a synchronization
  folder.
- The service account exclusively owns a `0700` directory and each database is
  `0600`; untrusted users cannot open, replace, link, or copy the files.
- One database path is allocated per tenant. The tenant binding is recorded in
  the database and the deployment inventory.
- Untrusted clients cannot construct `StoreContext`. A trusted API/service
  authenticates them, evaluates policy, then supplies the context internally.
- `authentication_ref`, `authorization_ref`, `request_id`, and `purpose` are
  non-secret audit identifiers with defined retention.
- At-rest and backup encryption are selected and keys are stored/rotated outside
  the repository, DKA payloads, audit events, and database file.
- Backup RPO/RTO, retention, off-host copy, restore-drill cadence, and media
  disposal are approved.
- Monitoring thresholds exist for `StoreBusy`, CAS conflicts, corruption,
  failed backup/restore, file-mode drift, disk capacity, and latency.
- A separately controlled audit destination receives authenticated event-chain
  checkpoints if tamper resistance or non-repudiation is required.
- DKA classification, retention/deletion, derived-index, incident response, and
  legal/privacy policies are approved.

If multiple hosts need direct database access or writers cannot queue, stop and
select a client/server profile. Do not place the SQLite file on a shared network
filesystem.

## 2. Initialization

Create the tenant directory under deployment configuration management, then
construct the store once:

```python
from cpas.sqlite_dka_store import SQLiteDKAStore

store = SQLiteDKAStore(
    "/var/lib/cpas/tenant-123/dka.db",
    tenant_id="tenant-123",
    local_filesystem=True,  # operator assertion after mount validation
    busy_timeout_ms=5000,
)
```

The adapter creates the database at `0600`, binds it to the tenant/profile and
file device/inode, and sets rollback journal mode. It rejects final-path/parent
symbolic links, hard links, ownership/mode drift, and file replacement while an
adapter is active. Deployment tooling must additionally validate parent
directories, mount topology, owner/group, quotas, storage durability, and
mandatory-access-control policy.

## 3. Request boundary

Construct a context only after host authentication and policy evaluation:

```python
from cpas.dka_store import StoreContext

request = StoreContext(
    tenant_id="tenant-123",
    principal_id="service:research-api",
    permissions=frozenset({"dka:read", "dka:write"}),
    authentication_ref="authn-event:01K...",
    authorization_ref="policy-decision:01K...",
    request_id="request:01K...",
    purpose="reviewed-research-continuity",
)
```

Never deserialize this object directly from a client body and never treat a
SeedToken, IDP declaration, DKA field, model output, or repository account as
authorization. Sensitive classifications additionally require
`dka:read:sensitive` or `dka:write:sensitive`. Restrict `dka:*`, audit, verify,
backup, restore, and retention capabilities to separate operational roles.
Grant `dka:migrate` only to reviewed import tooling; migration events preserve
the fact that a snapshot was imported rather than freshly authored.

## 4. Startup and health verification

At every startup, construction checks the profile and tenant binding. Run a
full integrity check on a maintenance cadence and after unclean shutdown,
storage incidents, or restore:

```python
report = store.verify(context=verification_context)
assert report["passed"] and report["profile"]["conformant"]
```

This verifies SQLite structure, foreign keys, all canonical snapshot digests
and index tuples, head targets, tombstone consistency, and the audit chain.
Treat any `CorruptionDetected` as an incident: stop writes, preserve evidence,
quarantine the database, assess backups, and restore to a new file. Do not
reseal or “repair” a corrupted record in place.

## 5. Writes, contention, and retries

Keep write transactions short. The adapter serializes mutation using
`BEGIN IMMEDIATE`; it performs validation, immutable insert, CAS head update,
and event append in one transaction.

- On `HeadConflict`, reread and explicitly rebase, merge, or abandon. Do not
  auto-retry with the new head.
- On `StoreBusy`, use bounded exponential backoff with jitter and a request-level
  idempotency policy. Alert on sustained contention.
- On `AccessDenied` or `ProfileViolation`, do not retry until policy/configuration
  changes.
- On disk-full/I/O/store errors, stop and assess transaction state, capacity,
  and storage health.

Load-test the actual host and storage. “Low/moderate concurrency” is a topology
constraint, not a universal transactions-per-second promise.

## 6. Backup

Create backups only at new paths owned by the service:

```python
manifest = store.backup(
    "/var/backups/cpas/tenant-123/dka-2026-08-12.db",
    context=backup_context,
)
```

The adapter builds and verifies a same-directory temporary file, then publishes
it without overwriting any path that appeared concurrently. The returned digest
covers the completed backup file and verification must pass. Immediately
encrypt/package the backup under the deployment's key policy,
write its manifest to the backup catalog, copy it off-host, and apply retention.
The raw `.db` remains unencrypted by this library. Protect temporary and failed
backup files too.

The live store records a `backup` audit event after the verified copy. That
event is not inside the copy it describes. If publication succeeds but this
audit append fails, `RecoveryError` names the already published path; quarantine
or catalog it and reconcile the audit incident rather than assuming no artifact
exists. Retain the returned manifest and live audit export together if this
relationship matters.

## 7. Restore and promotion

Restores always target a new path:

```python
restored = SQLiteDKAStore.restore_copy(
    encrypted_backup_staging_path,
    "/var/lib/cpas/tenant-123/dka-restored.db",
    tenant_id="tenant-123",
    local_filesystem=True,
    context=restore_context,
)
```

The method verifies that the source stays unchanged, builds and verifies a
temporary destination, appends a restore event, then publishes without
overwriting a concurrently created path. The operator must then:

1. compare the catalog digest and tenant/profile binding;
2. review verification and expected recovery point;
3. stop or drain writers;
4. promote the new path using the deployment's recoverable swap procedure;
5. restart and verify again;
6. retain/quarantine the old file under incident/retention policy; and
7. record measured RPO/RTO and drill evidence.

The library does not perform active-file replacement or failover.

## 8. Retention and deletion

`purge` requires the current digest/profile tuple for every branch, preventing a
stale retention job from deleting newly changed state. It removes canonical
payloads/heads, retains a minimal tombstone and content-free audit metadata, and
blocks DKA-ID reuse. Run `compact_after_purge` during maintenance to `VACUUM` the
live file. Its result deliberately says `physical_erasure_guaranteed=false`.

Deletion is incomplete until the same source digest/ID has been removed or
expired from:

- raw and encrypted backups and filesystem/volume snapshots;
- audit exports, crash dumps, traces, and application logs;
- search, vector, cache, graph, analytics, and model-training derivatives;
- staging, restore-test, incident, and developer copies; and
- any downstream EEP/SeedToken/state references governed by separate systems.

SQLite secure deletion does not establish cryptographic erasure and cannot
guarantee removal from deleted rollback journals, filesystem free space, or the
underlying medium. Prefer
per-tenant encryption/key destruction where the risk and governance justify it,
but specify and test that mechanism separately.

## 9. Rehydration and tool safety

Send `data_blocks` only through a data/tool-result channel. Do not interpolate
them into system/developer prompts. Enforce tool permissions outside the model,
validate exact DKA references/digests, and preserve item/byte/stale policies.
Stored instructions have no policy authority. The compatibility
`context_blocks` field has identical untrusted-data status.

## 10. Deployment certification record

An identified reviewer should record:

- application and CPAS commit/version;
- Python and linked SQLite versions;
- host OS, filesystem/mount, storage and power-loss assumptions;
- exact profile status and full conformance result;
- identity provider/policy engine and role mapping;
- encryption/key and secret-management controls;
- audit checkpoint/export controls;
- backup/restore drill date, RPO/RTO evidence, and retention;
- load/contention and failure-injection evidence;
- monitoring/incident runbooks and owners;
- privacy/legal review for classification and deletion; and
- every accepted exception, expiry, and compensating control.

Only that assessed deployment may use “deployment-certified,” and only under
the recorded scope/date. Repository CI alone remains implementation-tested.
