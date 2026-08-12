# CPAS v2 canonicalization verification — 2026-08-12

## Scope

This record verifies the issue #97 implementation against the local checkout
based on merge commit `1bfb02c20eaf633ce5e5d16652fb32e0f74f571c` (PR #101).
It covers version/profile negotiation, RFC 8785/JCS bytes, domain-separated
digests, legacy direct-hash compatibility, schema/example consistency, and an
independent Node.js implementation.

It does not certify cryptographic authentication, authorization, a model
runtime, production DKA-E storage, or untested language implementations.

## Environment

- Python `3.12.13`
- Node.js `v24.14.0`
- `rfc8785` `0.1.4`
- branch `codex/cpas-v2-canonicalization`

## Results

### Complete repository tests

```bash
python -m pytest -q \
  --basetemp=/workspace/scratch/c2be0d453efb/pytest-cpas-97-final
```

Result: **67 passed**. Nine deprecation warnings remain in historical
`cpas_autogen`/wonder-log utilities that use `datetime.utcnow()`; this change
does not alter those v1.1 compatibility modules.

### Repository contracts

```bash
python tools/validate_cpas_v2.py
```

Result:

```text
CPAS v2 validation passed: 4 schemas/examples, 8 digest references, 103 local links in 25 files, 28 migrated IDP v1 declarations, 17 canonicalization vector checks
```

### Independent-language vectors

```bash
node tools/verify_canonicalization_vectors.mjs
```

Result:

```text
canonicalization vector verification passed: 17 checks (Node.js)
```

The Python vector implementation runs as part of the repository validator and
reproduces the same 17 checks. Vectors cover JCS primitive/number rendering,
UTF-16 and integer-like property ordering, the frozen legacy digest, four CPAS
digest domains, duplicate members, non-finite numbers, unsafe integer tokens,
and lone surrogates.

### Static checks

```bash
python -m compileall -q cpas tools/validate_cpas_v2.py \
  tools/verify_canonicalization_vectors.py \
  migrations/migrate_idp_v1_to_v2.py
git diff --check
```

Result: both commands exited `0` with no output.

## Verified compatibility behavior

- Existing `cpas-canonical-json-v1` DKA and SeedToken records verify without a
  new profile marker.
- An omitted profile is inferred only for that legacy canonicalization.
- JCS records fail closed when their required artifact-domain profile is
  missing or incompatible.
- Equal canonical JSON in IDP, DKA, capability, and SeedToken domains produces
  distinct SHA-256 values.
- Declared identity semantics remain equal across a digest-profile migration
  even though the digest string changes.
- DKA branch heads, lineage, rehydration manifests, and events carry/check
  digest-profile metadata.
- Current Clarence-9, DKA-E, SeedToken, and EEP examples have consistent new
  digest/profile references.

## Remaining verification

Hosted Python 3.11/3.12/3.13 and Node.js 24 checks are defined in
[the CI workflow](../../.github/workflows/cpas-v2-ci.yml) but were not run from
this local record. The branch must be pushed and the draft PR workflow observed
before issue #97 can be closed.

The governing decision and migration mapping are
[ADR-0001](../adr/0001-canonicalization-and-digest-profiles.md) and
[the canonicalization migration guide](../../migrations/canonicalization-v1-to-jcs-v1.md).
