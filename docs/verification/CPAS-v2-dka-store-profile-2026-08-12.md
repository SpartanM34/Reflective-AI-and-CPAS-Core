# CPAS v2 DKA-E storage-profile verification — 2026-08-12

**Scope:** issue [#99](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/issues/99)

**Baseline:** merged `main`
`a129d2fbc914c395b8e8d7317dc531f7ae6ec1da` (PR #103)

**Branch:** `codex/cpas-v2-dka-production-profile`

**Conformance level established locally:** implementation-tested for
`cpas-sqlite-rollback-single-host-v1`; not deployment-certified

## Environment

| Item | Observed value |
|---|---|
| Date | 2026-08-12 UTC |
| OS | Linux 6.18.35 x86_64, glibc 2.39 |
| Python | 3.12.13 |
| SQLite linked by Python | 3.50.4 |
| Journal selected/tested | `DELETE` rollback journal |
| `synchronous` | `EXTRA` (`3`) |
| jsonschema | 4.26.0 |
| rfc8785 | 0.1.4 |
| pytest | 9.1.1 |
| Node.js | Independent canonicalization verifier executed; version reported by CI separately |

SQLite 3.50.4 was not used in WAL mode. SQLite's 2026 WAL advisory places it
inside the WAL-reset affected range and identifies fixed backports beginning at
3.50.7. The profile therefore rejects WAL and exercises rollback journal with
the stronger documented `EXTRA` sync setting. This local result does not attest
the storage hardware or filesystem.

Primary evidence:

- [SQLite WAL advisory](https://sqlite.org/wal.html#walreset)
- [SQLite transaction and `BEGIN IMMEDIATE` behavior](https://sqlite.org/lang_transaction.html)
- [SQLite rollback/synchronous settings](https://sqlite.org/pragma.html#pragma_synchronous)
- [SQLite deployment selection](https://sqlite.org/whentouse.html)
- [SQLite network-filesystem warning](https://sqlite.org/useovernet.html)
- [SQLite online backup API](https://sqlite.org/backup.html)

## Named profile suite

Command:

```bash
python -m pytest -q tests/test_cpas_v2_sqlite_store.py \
  --basetemp=/workspace/scratch/c2be0d453efb/pytest-cpas-99-profile-final
```

Result: **13 collected, 13 passed**.

The suite exercised:

- POSIX/local-filesystem, secure file/directory, profile/tenant/device-inode
  binding, replacement detection, rollback journal, sync, foreign-key,
  trusted-schema, and secure-delete settings;
- schema/digest validation, immutable snapshots, digest-profile CAS, exact
  parent resolution, revisions, branches, three-way contested merge, and audit;
- two simultaneous CAS writers with exactly one commit and one explicit
  conflict;
- a held write lock mapping to retryable `StoreBusy`;
- missing context, tenant mismatch, permission denial, sensitive payload/head/
  history denial, audit separation, and migration permission;
- payload, audit-event, missing-head, and active-state/event-correlation
  corruption detection;
- verified no-clobber online backup, restore-to-new-path, purge/tombstone, and
  compaction with no physical-erasure claim;
- typed/authorized invalidation, stale-state rejection, access-denied omission,
  and prompt-like stored content
  retained only in a no-instruction-authority/no-policy-promotion envelope.

## Full repository suite

Command:

```bash
python -m pytest -q \
  --basetemp=/workspace/scratch/c2be0d453efb/pytest-cpas-99-full-final
```

Result: **103 collected, 103 passed**.

Nine deprecation warnings remain in historical v1 utilities:
`cpas_autogen/dka_persistence.py`, `cpas_autogen/message_logger.py`, and
`tools/record_wonder.py` use `datetime.utcnow()`. They were pre-existing,
non-failing, and outside issue #99; the modernization did not silently alter
them.

## Repository invariants and independent vectors

Commands:

```bash
python tools/validate_cpas_v2.py --json
node tools/verify_canonicalization_vectors.mjs
python -m compileall -q cpas tools/validate_cpas_v2.py \
  tools/verify_canonicalization_vectors.py tools/verify_sqlite_dka_store.py \
  migrations/migrate_idp_v1_to_v2.py \
  migrations/migrate_idp_v2_governance.py \
  migrations/migrate_file_dka_store_to_sqlite.py
git diff --check
```

Results:

- five schema/example pairs valid;
- eight cross-file digest references valid;
- 166 local links across 36 modernization Markdown files valid;
- 28 discovered legacy IDP migrations valid;
- 17 Python canonicalization/digest checks valid;
- 17 independent Node.js vector checks passed;
- all named Python/migration modules compiled;
- no whitespace errors.

## Migration evidence

The full suite includes a FileDKAStore migration test that creates multiple
revisions and a branch, imports into a new SQLite tenant database, verifies
three exact snapshot digests and two heads, confirms three source events are
observed but not replayed as authority, verifies the destination/audit chain,
and byte-compares every source file before and after. A negative test rejects a
source head that does not match its latest canonical snapshot.

## Claims this evidence supports

- The named reference backend passes its reproducible suite under the stated
  environment and rollback-journal profile.
- Tested writes atomically combine snapshot, CAS head, and digest-linked event.
- Store permission/tenant checks and rehydration policy separation behave as
  described in the reference implementation.
- The tested backup/restore/migration paths verify canonical state and do not
  overwrite their source/active target.

## Claims this evidence does not support

- deployment authentication, authorization-policy correctness, or tenant
  isolation outside the adapter;
- encryption, key management, transport/API security, secret management, or
  complete erasure across backups/derived systems;
- a tamper-proof audit service, signature, non-repudiation, trusted timestamp,
  or protection from a privileged whole-database rewrite;
- network/shared-filesystem safety, multiple-host consistency, high write
  concurrency, high availability, failover, or PostgreSQL behavior;
- filesystem/hardware power-loss guarantees, operational RPO/RTO, monitoring,
  restore promotion, privacy/legal compliance, or deployment certification;
- truth of a DKA claim, model memory, consciousness, or identity persistence.

The [operations runbook](../operations/DKA-E-SQLite-Profile-v1.0.md) lists the
external controls required before any deployment-level claim.

## Remote CI status

Initial publication commit
[`c228d087e7f8fda1f6c4adf4d6d8cc8e7b1efd5a`](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/commit/c228d087e7f8fda1f6c4adf4d6d8cc8e7b1efd5a)
on draft pull request
[#104](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/pull/104)
completed
[CPAS v2 CI run #8](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/actions/runs/31645506263)
successfully on 2026-08-12 UTC.

| GitHub Actions job | Job ID | Result |
|---|---:|---|
| Tests (Python 3.11) | [94277985568](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/actions/runs/31645506263/job/94277985568) | success |
| Tests (Python 3.12) | [94277985664](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/actions/runs/31645506263/job/94277985664) | success |
| Tests (Python 3.13) | [94277985561](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/actions/runs/31645506263/job/94277985561) | success |
| Repository invariants | [94277985647](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/actions/runs/31645506263/job/94277985647) | success |

The follow-up documentation commit that records this evidence requires its own
successful CI run before the pull request is considered verified at its head.
