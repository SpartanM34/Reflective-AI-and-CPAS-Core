# Migrating Clarence-9 / CPAS-Core v1.1 to the current architecture

This guide preserves the philosophical lineage while replacing obsolete
implementation assumptions. It is a parallel migration: historical v1.1 files
remain unchanged and reviewable in Git.

## 1. Freeze and inventory the source

Record the repository commit, source path, and SHA-256 digest for every CPAS
specification, IDP, SeedToken/PromptStamp, DKA/DKA-E record, T-BEEP message,
metaphor mapping, and application integration. Inventory external consumers and
state stores; the repository alone cannot reveal them.

Do not move or normalize historical artifacts. The v2 layout uses pointers under
`specs/v1.1/` and new artifacts under `specs/v2.0/`, `instances/current/`, and
`schemas/` so Git provenance stays intact.

## 2. Classify each mechanism honestly

Label every artifact as one of:

- conceptual specification;
- protocol/schema;
- reference/prototype implementation;
- runtime-verified capability;
- deployment-certified control.

Reclassify legacy “Full Compliance,” “signature,” “memory,” and benchmark claims
where evidence supports only schema validation, unkeyed integrity, symbolic
continuity, or local prototype performance. Preserve the old wording in history;
put the correction in the audit/migration record.

## 3. Migrate IDP declarations

Run the non-destructive utility into a new directory:

```bash
python migrations/migrate_idp_v1_to_v2.py \
  agents/json migrated-idps \
  --source-revision fdac6182061112b73553935661c2247403e12b3d \
  --maintainer Spartan-M34 \
  --migrated-at 2026-08-11T00:00:00Z
```

It retains the complete v1 document, separates the model into
`runtime_binding`, labels legacy capabilities `declared`, and activates only
declarative continuity. Review each generated draft manually:

1. refine stable identity summary, traits, and interaction commitments;
2. remove unsupported anthropomorphic or capability claims;
3. validate outward epistemic transparency and chain-of-thought privacy;
4. bind a runtime only after probing it;
5. declare real state layers, tools, retention, deletion, and authority;
6. review proposed governance roles, approval thresholds, succession, and
   vacancies without inferring authentication;
7. compare the stable identity digest before/after runtime rebinding.

Clarence-9’s reviewed result is
[`instances/current/Clarence-9-v2.0.json`](../instances/current/Clarence-9-v2.0.json).
Earlier v2 drafts that predate the required governance section use the
non-destructive
[`migrate_idp_v2_governance.py`](migrate_idp_v2_governance.py) utility and the
[governance migration guide](idp-v2-draft-governance.md).

## 4. Replace PromptStamp and SeedToken semantics

Keep the legacy token as source evidence. Create a new SeedToken v2 with a new
`token_id`, an exact IDP identity digest, state digests, capability profile,
continuity scope, and optional expiry/parent. Recompute v2 integrity using the
documented canonicalization and artifact-domain profile. See the explicit
[draft digest migration](canonicalization-v1-to-jcs-v1.md).

Do not copy a legacy `hash`, `chain_hash`, or SHA-256 “signature” into an
authenticator. If sender authentication is required, configure a trusted key
store and use the implemented HMAC profile (or define and implement a separately
reviewed public-key profile). Authorization remains an external decision.

## 5. Convert DKA and DKA-E state

For each legacy anchor:

1. extract the claim separately from metaphor;
2. type confidence with basis/calibration;
3. give assumptions, uncertainties, evidence, disputes, and dependencies stable
   IDs/references;
4. add validity horizon, review half-life, and concrete invalidation triggers;
5. record source and transformation provenance;
6. set metaphor under optional `presentation`;
7. seal the canonical record and verify the digest after a store round trip.

Imported history should be an explicit `migration` event, not invented revision
lineage. Embeddings are generated afterward as disposable indexes linked to the
canonical digest.

## 6. Configure persistence and safe rehydration

Select a backend based on concurrency, durability, audit, privacy, and query
requirements. Git is effective for reviewable low-frequency artifacts;
transactional databases/event stores are better for concurrent updates; object
stores suit immutable snapshots; graphs/vector stores are useful derived views.

The v1 [DKA-E store contract](../specs/v2.0/DKA-Store-Contract-v1.0.md)
separates portable semantics from backend guarantees. The first tested profile,
[`cpas-sqlite-rollback-single-host-v1`](../specs/v2.0/DKA-E-SQLite-Profile-v1.0.md),
is available only for one POSIX host/local filesystem and serialized writes.
Existing verified `FileDKAStore` state can be imported non-destructively with
the [migration utility](FileDKAStore-to-SQLite-v1.md); exact snapshot digests
are preserved and legacy events are retained only as source observations, not
upgraded into authenticated audit history.

Implement authentication, authorization, encryption, tenant isolation,
retention/deletion, backups, recovery, and key rotation outside the core record.
Test immutable writes, compare-and-swap conflicts, corrupt snapshots, stale
records, denied access, missing dependencies, and context budgets. Never promote
stored prompts to trusted instructions during rehydration.

## 7. Migrate T-BEEP/EEP integrations

Build an explicit gateway from legacy messages to EEP v2. Populate sender,
receiver, instance/runtime profile, task, claim, qualified confidence,
assumptions, evidence, uncertainty, disagreement, requested validation, DKA
digests, provenance, and timestamp. Put unknown/unmappable material in an
extension and flag it for review.

Initialize consensus as `not_computed`. Choose a human or documented aggregation
method only after checking correlated agents, evidence quality, conflicts, and
decision authority. Add transport authentication/authorization separately.

## 8. Calibrate CPAS-Min and Full CPAS

Preserve the historical metaphor library. Move metaphor to optional
presentation. CPAS-Min defaults to concise assumptions/evidence/uncertainty and
little ritual; Full CPAS can add multiscale review and metaphor. Neither mode
disables provenance or safety. Prefer explicit user preferences over inferred
emotional/personality profiles.

## 9. Validate runtime replacement

For every target provider/model/tool set:

1. bind runtime metadata outside stable identity;
2. probe required and optional capabilities;
3. test supported schema dialects, tool calls, context limits, file/web access,
   and state adapters;
4. record constraints, test evidence, and `last_runtime_validation`;
5. select and review a versioned runtime-evaluation manifest;
6. capture exact runtime configuration, capability probes, transcript assurance,
   and raw outputs under a no-side-effect policy;
7. run `tools/evaluate_runtime_replacement.py` to separate capability, policy,
   style, and task-performance drift;
8. review raw outputs with the human rubric and record an attributable decision;
9. confirm identity digest invariance without labeling it identity proof.

A runtime can be technically compatible while producing materially different
style or judgment. Identity-digest equality is necessary for declared
continuity, not sufficient for behavioral equivalence.
The checked-in Clarence-9 baseline/candidate transcripts are synthetic harness
vectors and must not be migrated into `last_runtime_validation` as provider
evidence.

## 10. Stage and release

- Release the protocol as `2.0.0` only after schemas and migration semantics are
  reviewed; pre-release drafts use SemVer prerelease tags.
- Version schemas immutably and document every breaking change.
- Publish conformance level and dated evidence; avoid unqualified compliance.
- Exercise migration and rollback against copies of real state.
- Keep v1.1 readers during a stated compatibility window.
- Require human review for security semantics, contested merges, and deletion of
  persisted data.
- Evaluate declaration transitions under the predecessor governance policy;
  never allow a proposed replacement policy to approve itself.

## Rollback

Because v1 files are untouched, applications can continue reading v1 while v2
adapters are disabled. Do not down-convert v2 state in place: export a labeled,
lossy v1-compatible view if required. Preserve v2 events and exact digests for a
later retry.

## Migration acceptance checklist

- [ ] Historical files and commit/digests preserved.
- [ ] Every claim assigned a maturity/conformance level.
- [ ] Stable identity digest is runtime-independent.
- [ ] Four continuity forms and four state layers reported truthfully.
- [ ] Hidden chain-of-thought is neither required nor persisted.
- [ ] DKA-E records validate, round-trip, and surface stale/conflict states.
- [ ] Token integrity/authentication/authorization are not conflated.
- [ ] Stored/retrieved content remains untrusted data.
- [ ] Agent agreement is not silently labeled consensus.
- [ ] Runtime/tool capabilities are dated and probed/verified.
- [ ] Runtime comparison fixes exact manifest/transcript/configuration digests,
      separates four drift categories, and retains mandatory human review.
- [ ] Synthetic fixtures are not relabeled as live runtime evidence or identity
      proof.
- [ ] Governance roles, vacancies, succession, and approval evidence are
      explicit and are not mislabeled as authentication/authorization.
- [ ] Runtime rebind, compatible amendment, identity evolution, and new
      identity classifications match `cpas-idp-change-v1`.
- [ ] Tests and limitations are published without fabricated results.
