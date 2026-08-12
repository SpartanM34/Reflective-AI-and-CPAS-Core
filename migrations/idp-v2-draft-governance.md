# Migrating an earlier IDP v2 draft to declaration governance

This migration applies to pre-release IDP v2 documents created before
`governance` became required. It does not change IDP v1 sources and does not
authorize its own output.

## Compatibility effect

Governance is outside the stable identity projection. If the source declaration
is internally consistent, adding the section preserves its semantic identity
digest and profile. The JSON file bytes change, so all raw file digests,
SeedToken state references, HMAC tags, manifests, and external indexes that pin
the file must be updated through their normal reviewed workflows.

The schema change is breaking for earlier v2 draft consumers because
`governance` is now required. It is not a stable-v2 compatibility promise; the
protocol remains a draft.

## Automated transform

Write to a new path:

```bash
python migrations/migrate_idp_v2_governance.py \
  path/to/pre-governance-idp-v2.json \
  path/to/governed-idp-v2.json \
  --maintainer Spartan-M34 \
  --migrated-at 2026-08-12T02:00:00Z
```

Use `--dry-run` to validate without writing. The utility refuses an in-place
source/output path and refuses to overwrite an existing destination unless
`--force` is explicit.

The transform:

1. requires `idp_version: "2.0"` and rejects an existing governance section;
2. verifies any stored stable identity digest before migration;
3. adds a proposed, draft, metadata-only governance policy;
4. assigns the supplied/provenance maintainer to maintainer, issuer, and human
   override roles with actor type `unspecified`;
5. leaves reviewer and runtime-operator roles vacant;
6. records the source path/raw digest and review-required status under
   `extensions.idp_v2_governance_migration`;
7. proves the stable identity digest did not move; and
8. validates the result against the current IDP schema and semantic checks.

The utility does not claim the maintainer is human, authenticate the named
subject, approve the policy, appoint a reviewer/operator, or change external
permissions.

## Required human review

Before changing `policy_status` to `active` or `lifecycle_status` to `active`:

- confirm the maintainer and issuer subjects through the repository's actual
  authority channel;
- set correct actor types;
- decide whether reviewer independence is required and appoint a reviewer if
  identity evolution, issuance, supersession, or rollback must be possible;
- name runtime operators only after external host authority exists;
- review every `(role, authority)` assignment and approval threshold;
- define succession and vacancy behavior without inventing a successor;
- retain `trust_model: metadata_only` unless a separately implemented and
  tested trust profile exists; and
- record the bootstrap review outside the proposed artifact, because a new
  policy cannot approve itself.

## Classification check

Compare the source and migrated documents with
`cpas.governance.classify_declaration_change`. The expected result is
`compatible_amendment`, and `identity_digest_changed` must be `false`.

Do not use digest equality as approval evidence. It proves only that the stable
identity projection stayed equal under the declared digest profile.

## Dependent artifact updates

After approval:

1. store the governed declaration as a new artifact/revision;
2. compute its `raw-sha256` file digest;
3. update SeedToken IDP state references and reseal token integrity;
4. recompute an HMAC tag only with the authorized key holder/process;
5. update transition/manifests that pin exact declaration bytes;
6. run schema, classifier, token, link, and repository conformance checks; and
7. retain the predecessor file/digest in provenance.

The canonicalization migration table remains historical evidence of the values
at that earlier change. Do not rewrite it to make those raw file/token values
appear permanent.

## Rollback

Rollback selects the preserved pre-governance artifact and disables consumers
that require the new schema. Do not remove the failed migration or approval
records. Any SeedToken resealed for the governed file must not be relabeled as
valid for the predecessor; restore or issue a token that pins the exact
predecessor bytes.
