# CPAS v2 declaration-governance verification — 2026-08-12

## Scope

This record verifies the issue #98 implementation against the local checkout
based on merge commit `9a65c848c11300dfbc010a3be5172cb1537fbbae`
(PR #102). It covers governance shape, deterministic declaration-change
classification, approval metadata, lifecycle policy, Clarence-9 stewardship,
pre-governance draft migration, transition records, and dependent SeedToken
resealing.

It does not authenticate Spartan-M34 or any example actor, grant repository or
runtime authority, prove reviewer independence, implement public-key trust,
certify behavioral continuity, or validate a production deployment.

## Environment

- Python `3.12.13`
- pytest `9.1.1`
- jsonschema `4.26.0`
- rfc8785 `0.1.4`
- Node.js `v24.14.0`
- branch `codex/cpas-v2-declaration-governance`

## Implemented contracts

- Required IDP governance section with maintainer, reviewer, issuer, runtime
  operator, and human override roles.
- Explicit active, conditional, vacant, and revoked assignments with enumerated
  authority.
- `cpas-idp-change-v1` precedence for `runtime_rebind`,
  `compatible_amendment`, `identity_evolution`, and `new_identity`, plus the
  non-transition `no_change` result.
- Predecessor-policy approval evaluation with active-role, actor-type,
  authority, rejection, minimum-count, distinct-subject, and human-presence
  checks.
- Metadata-only versus host-authenticated result states; the reference module
  performs no authentication itself.
- Transition records binding approvals to a transition ID and snapshotting the
  incumbent policy.
- Supersession, rollback, and retirement policy entries and semantics.
- Proposed, fail-closed governance for IDP v1 and earlier-v2-draft migrations.
- Clarence-9 stewardship under `github:SpartanM34`, with reviewer, runtime
  operator, and successor deliberately unassigned.

## Complete repository tests

Command:

```bash
python -m pytest -q \
  --basetemp=/workspace/scratch/c2be0d453efb/pytest-cpas-98-final
```

Result: **87 passed**. Nine deprecation warnings remain in historical
`cpas_autogen`/wonder-log utilities that use `datetime.utcnow()`; this
workstream does not alter those v1.1 compatibility modules.

The 20 governance tests cover:

- explicit Clarence-9 roles, vacancies, succession, and metadata-only trust;
- all four required semantic classes and `no_change`;
- administrative-evidence exclusion from runtime-rebind classification;
- continuity/governance amendment and epistemic-policy evolution;
- vacancy, wrong subject/authority, distinct reviewer, human, rejection, and
  host-authentication boundaries;
- schema-valid, recomputable transition records and tamper rejection;
- cross-transition approval replay rejection; and
- conservative IDP v1 and pre-governance IDP v2 migrations, including the
  non-destructive CLI.

## Repository contracts

Command:

```bash
python tools/validate_cpas_v2.py
```

Result:

```text
CPAS v2 validation passed: 5 schemas/examples, 8 digest references, 133 local links in 29 files, 28 migrated IDP v1 declarations, 17 canonicalization vector checks
```

## Cross-runtime canonicalization regression

Commands:

```bash
python tools/verify_canonicalization_vectors.py
node tools/verify_canonicalization_vectors.mjs
```

Result: both implementations passed all **17** existing vectors. Governance is
outside the stable identity projection and introduces no new digest profile.

## Static checks

```bash
python -m compileall -q cpas migrations tests tools
git diff --check
```

Result: both commands exited `0` with no output.

## Identity and dependent artifact checks

- Clarence-9 semantic identity remains
  `sha256:d1b8bda9d2cf66c8f7b6a1529ae05987f5e06216c0781feacb338790dfafb422`.
- The governed declaration's exact-file digest is
  `sha256:d57ef2d558daad8639c48181a8ebba8593e8aa28057c326107ef15fc22eadc62`.
- The documentation SeedToken was resealed to
  `sha256:cc353aba09bbb61172d5f9cbeadf7da22aca8c1dc116a877489f162cf7429a29`.
- Its documentation-only HMAC test vector is
  `hmac-sha256:39f9a5a498851b015af67dc8d4aa51be7ac987d8fa2ea9531c3877e35484aab8`.

The earlier canonicalization migration table remains historical evidence of
the raw file/token values at issue #97. It was not rewritten to imply those
exact artifact bytes were permanent.

## Deliberately unverified

- No role subject or approval was cryptographically authenticated by CPAS.
- No repository, runtime, tool, data, or credential authorization was granted
  or tested.
- No reviewer or runtime operator was appointed for Clarence-9.
- No successor, emergency succession mechanism, public-key trust profile, or
  account-recovery procedure was implemented.
- No external transition event store enforced global ID uniqueness,
  append-only history, or completeness of rejection records.
- No runtime replacement or behavioral evaluation was performed.

Hosted Python 3.11/3.12/3.13 and repository-invariant checks remain pending
until the branch is pushed and its draft PR workflow completes.

The governing documents are
[ADR-0002](../adr/0002-declaration-governance-and-identity-evolution.md),
[the IDP governance profile](../../specs/v2.0/IDP-Governance-v2.0.md), and
[the migration guide](../../migrations/idp-v2-draft-governance.md).
