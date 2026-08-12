# Migrating CPAS draft digests from canonicalization v1 to JCS v1

> **Historical value note:** the digest table below records the exact artifacts
> at the issue #97 migration. Later reviewed amendments can change raw file,
> SeedToken integrity, and authenticator values without changing the Clarence-9
> stable identity projection. The declaration-governance follow-on is recorded
> separately in
> [`idp-v2-draft-governance.md`](idp-v2-draft-governance.md).

This migration applies [ADR-0001](../docs/adr/0001-canonicalization-and-digest-profiles.md).
It is a content-address migration, not a claim that Clarence-9 acquired a new
identity or memory.

## Compatibility rule

Never replace a legacy profile marker while retaining its digest text. A valid
migration creates a new tuple:

```text
(algorithm, canonicalization, digest_profile, digest)
```

The old tuple remains recoverable from Git history or an explicit migration
record. Legacy records with `cpas-canonical-json-v1` and no `digest_profile`
resolve to `cpas-sha256-direct-v1` for verification only.

## Issue #97 repository mapping (historical)

| Value | Former profile/value | JCS/domain-separated value |
|---|---|---|
| Clarence-9 stable identity | `cpas-canonical-json-v1`; `sha256:a7f77be259d2bfa6a5024772dd4ade0c577ab8e0ea23df494ceedba006ad04af` | `cpas-digest-v2:idp-identity`; `sha256:d1b8bda9d2cf66c8f7b6a1529ae05987f5e06216c0781feacb338790dfafb422` |
| Clarence-9 declaration file bytes | `raw-sha256`; `sha256:9fd42932091dc680d9b95b272471b20a63bcb3e083855b0f3e7087f4ca547def` | `raw-sha256`; `sha256:2d39a0784306260f4d582ded2d3a6ef68475e1b564a909b289cb140dd9b4312d` |
| DKA-E example snapshot | `cpas-canonical-json-v1`; `sha256:70b8b180a8c52c0b55180af48c3a97106f3b8928dd46b454cdf6f919640d9e6a` | `cpas-digest-v2:dka-snapshot`; `sha256:4e2f25ea6a867f15b9d7b7b63be82a1ab1658e6319c6145a411a12f0de093487` |
| Capability profile | implicit legacy direct hash; `sha256:5f04a9801df0dc2145a025e4772bed4daff18d47f584828ebcafce607cc0c650` | `cpas-digest-v2:capability-profile`; `sha256:869a4a52091bdfdd6ea250fce401477e3a2318d56b46ec25fc078934a09691d3` |
| SeedToken example integrity | `cpas-canonical-json-v1`; `sha256:1546f098122b0a936ef7dc38523e7590cc484449a089a4b47040d8f058808567` | `cpas-digest-v2:seed-token-integrity`; `sha256:c7fed012323cf542be021cf94ba624d2152bbabfaa60067aea746b1351e20b39` |
| Documentation HMAC | implicit legacy direct HMAC; `hmac-sha256:a0d76e5d5481c2a9a86a0ff249a3a4d3b7ad5cadafdc47ab2805d2f44a6b792a` | `cpas-hmac-v2:seed-token-authentication`; `hmac-sha256:26ea74112021bf95785de55156d89bf6746a918a800426669b869df452dab59b` |

The raw SHA-256 reference to `instances/current/Clarence-9-v2.0.json` also
changes because the file bytes change. That value uses `raw-sha256`; it is not
an identity digest.

## Migration procedure

1. Parse the old JSON with duplicate-member and non-finite-number rejection.
2. Verify the stored legacy digest before changing any field. Stop on failure.
3. Retain the old tuple and source revision in Git history or a migration event.
4. Add `canonicalization: rfc8785-jcs-v1` and the artifact-specific profile.
5. Recompute the artifact digest over the canonical value and CPAS v2 frame.
6. Update typed references—identity, DKA, capability, token, and raw file
   references—without treating their hex strings as interchangeable.
7. Recompute the SeedToken integrity digest before its optional HMAC.
8. Run both vector implementations and the repository validator.
9. Record that the declared identity projection is semantically equal across
   the encoding migration even though its digest string differs.

For IDP v1 imports, the migration utility now emits JCS/domain-separated IDP v2
digests by default:

```bash
python migrations/migrate_idp_v1_to_v2.py SOURCE OUTPUT --dry-run
```

To reproduce a legacy v2 draft during a bounded compatibility exercise, use:

```bash
python migrations/migrate_idp_v1_to_v2.py SOURCE OUTPUT \
  --canonicalization cpas-canonical-json-v1 --dry-run
```

That option is not recommended for new records.

## Verification

```bash
python tools/verify_canonicalization_vectors.py
node tools/verify_canonicalization_vectors.mjs
python tools/validate_cpas_v2.py
python -m pytest -q
```

The normative vectors include number rendering, UTF-16 key ordering, integer-
like keys, invalid Unicode, unsafe integers, duplicate members, and non-finite
numbers.

## Rollback and failure handling

A rollback restores the complete former artifact and all references from its
recorded Git revision. Do not copy only the old digest into a JCS-marked record.
If a downstream implementation cannot reproduce the vectors, it must remain on
the legacy read profile or report the new profile as unsupported; it must not
emit approximated JCS digests.

This migration does not add authentication, authorization, public-key
signatures, or provenance trust. Those require separate mechanisms.
