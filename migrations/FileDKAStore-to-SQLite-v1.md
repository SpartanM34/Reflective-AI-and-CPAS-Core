# Migrating FileDKAStore to the SQLite single-host profile

This migration preserves verified immutable DKA snapshots and their exact
digest/profile tuples. It does not treat legacy file events as authenticated
authority and it does not modify or delete the source store.

## Preconditions

- The source is a complete `FileDKAStore` directory with `snapshots`, `heads`,
  and parseable optional `events`.
- Every snapshot validates and verifies; every branch head matches its latest
  verified snapshot; all parent tuples form a resolvable acyclic graph.
- The source tree contains only ordinary, single-linked files/directories; the
  utility rejects symbolic links, hard-linked files, and special entries.
- The destination does not exist and its parent is a service-owned `0700`
  directory on a local filesystem on the same POSIX host.
- A tenant ID and deployment encryption/backup/retention plan are approved.

## Command

```bash
python migrations/migrate_file_dka_store_to_sqlite.py \
  /path/to/file-store /secure/local/path/tenant.db \
  --tenant tenant-123 \
  --local-filesystem-affirmed \
  --json > migration-report.json
```

The utility writes a temporary `0600` database in the destination directory,
imports snapshots in dependency order, compares every destination head with the
source, performs full SQLite/DKA/audit verification, then atomically renames the
new file into place. On failure it removes only its temporary destination; the
source remains untouched.

## Provenance semantics

- Snapshot JSON and digest/profile tuples remain exact.
- New audit events identify the migration principal and import operation.
- Legacy JSONL events are parsed and counted but not replayed as trusted audit
  events. They lack the v1 profile's context, transaction, sequence, and chain
  semantics. Keep the source read-only under its retention policy when those
  historical observations are required.
- The report includes a reproducible source tree digest definition, source event
  count, imported snapshot/branch counts, and destination verification result.
- A raw tree digest is integrity metadata, not authentication of the source.

## Post-migration

1. Store the report in the change/backup catalog and review every count/digest.
2. Run `tools/verify_sqlite_dka_store.py` independently against the new file.
3. Exercise an application read, authorized write/CAS conflict, backup, and
   restore-to-new-path under deployment identities.
4. Encrypt/back up the destination and complete the operations certification
   checklist before promotion.
5. Retain, archive, or delete the source only under explicit retention/privacy
   policy. The migration tool never decides that policy.

There is no automatic down-migration. Canonical snapshots can be exported, but
the SQLite tenant binding, authorization references, transactional audit chain,
tombstones, and recovery events have no faithful `FileDKAStore` equivalent.
