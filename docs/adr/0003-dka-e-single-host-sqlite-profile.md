# ADR-0003: DKA-E single-host SQLite rollback profile

- **Status:** Accepted for the CPAS v2 draft when this change is merged
- **Date:** 2026-08-12
- **Decision owners:** Spartan-M34 stewardship; implementation proposal by OpenAI Codex
- **Issue:** [#99](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/issues/99)

## Context

`FileDKAStore` demonstrates immutable snapshots, local CAS, events, branching,
and corruption checks but has no production authorization, tenant, recovery, or
audit profile. Issue #99 requires a named backend to pass reproducible tests in
the available environment, while remaining honest about external controls.

## Options considered

| Option | Strength | Blocking weakness in this workstream |
|---|---|---|
| Keep `FileDKAStore` | No new dependency; preserves local reference | Snapshot/head/event are not one transaction; no tenant/auth/recovery profile |
| PostgreSQL | Strong multi-host and concurrency path; engine roles/RLS available | No server, client, driver, or container runtime available, so no honest backend execution claim |
| SQLite WAL | Concurrent readers/writer and common embedded deployment | Available SQLite 3.50.4 is in the documented WAL-reset bug range; WAL also forbids multi-host/network filesystems |
| SQLite rollback journal | Transactional, standard-library executable, online backup, strong single-host fit | One writer, no server authentication/RLS, encryption and several operational controls external |

## Decision

Adopt `cpas-sqlite-rollback-single-host-v1` as the first
production-oriented—not universally production-ready—profile. Require
`journal_mode=DELETE`, `synchronous=EXTRA`, local filesystem affirmation,
database-per-tenant isolation, `0600`, trusted host contexts, application-level
permission enforcement, immutable snapshots, transactional CAS/head/event,
digest-linked audit events, verified backup/restore, and explicit purge.

Retain `FileDKAStore` unchanged in status as a compatibility/reference adapter.
Defer a multi-host PostgreSQL profile until it can run against an actual named
server/version and adversarial suite. Do not silently switch this profile to
WAL when the runtime is upgraded; WAL has different failure and checkpoint
semantics and needs its own profile/version.

## Consequences

- CPAS now has a normative backend-neutral interface and stable failure classes.
- One executable backend passes races, denial, corruption, stale state, and
  recovery tests without adding a database dependency.
- The profile is suitable only behind an application/service boundary on the
  same host as its local database and for workloads that can serialize writes.
- Authentication, encrypted storage/backup, key management, external audit
  anchoring, RPO/RTO, legal retention decisions, monitoring, and host hardening
  remain deployment responsibilities.
- Database-per-tenant improves query isolation and deletion scope but increases
  operational file/backup management.

## Revisit triggers

Create a new profile rather than mutating this one when any of these apply:

- multiple application hosts need direct concurrent database access;
- sustained writer contention exceeds the documented service objective;
- engine-enforced network identities or row-level policy are required;
- high availability/failover needs a database service;
- an encrypted SQLite distribution is selected and key semantics become part
  of the backend claim; or
- WAL is desired after a fixed runtime and checkpoint/recovery suite exist.
