# CPAS-Core v2 release-candidate readiness audit

**Status:** issue #106 audit; proposed dispositions, not a release decision

**Date:** 2026-08-13

**Baseline:** merged PR #105, commit
`8503607560c907d49dbb40a349cece44c5099a75`

**Lineage:** CPAS-Core v1.1 by Spartan-M34 and the Clarence-9 corpus

## 1. Verdict

CPAS-Core v2 is **not ready to be tagged `2.0.0-rc.1`**.

Confidence in that verdict is **High**. The merged foundation is materially
stronger than the historical implementation: it has versioned schemas,
domain-separated digests, migration paths, governance records, a scoped DKA-E
backend, a runtime-evaluation harness, and multi-version CI. The remaining gap
is not a lack of polished prose. The repository has no single release contract
that says which artifacts constitute CPAS-Core v2, which are optional profiles,
which package/version is being released, and which open questions are excluded
from the stable core.

Four repository-controlled contradictions block an RC immediately:

1. version authority is split among core `2.0.0-draft.1`, Python
   `2.0.0.dev1`, and distribution `cpas_autogen` `0.1.0`;
2. the three runtime-evaluation schemas use placeholder `cpas.example` IDs
   while the other schemas use `cpas-core.org`;
3. there is no v2 changelog, release manifest, release procedure, or RC support
   boundary; and
4. several verification records still describe hosted CI or final-head checks
   as pending even though their PRs were merged.

External evidence and maintainer decisions also remain absent. Those absences
must be recorded as blockers or explicit exclusions; code cannot substitute for
them.

This verdict does **not** retract the implementation evidence already recorded.
It distinguishes a tested draft from a coherent release candidate.

## 2. Audit method and claim boundary

The audit inspected release-facing repository state at the baseline above:

- 11 files in [`specs/v2.0/`](../../specs/v2.0/);
- 8 Draft 2020-12 schemas in [`schemas/`](../../schemas/);
- 4 v2 JSON examples plus the current Clarence-9 declaration;
- 14 Python files in [`cpas/`](../../cpas/);
- 6 CPAS v2 verification records;
- canonicalization and runtime-evaluation conformance vectors;
- package metadata, dependency files, tags, changelog, CI, migration tools, and
  the [open-question ledger](../open-questions-v2.md).

The audit classifies repository evidence. It did not deploy a model, database,
identity provider, key infrastructure, package registry, or external consumer
integration. It did not appoint a reviewer or runtime operator. Proposed
dispositions below are recommendations for maintainer review, not silently
accepted protocol changes.

The maturity chain remains:

> conceptual specification → protocol → reference implementation → verified
> capability → deployment certification

No stage implies the next.

## 3. Version and release authority inventory

| Surface | Observed version/status | Evidence | RC consequence |
|---|---|---|---|
| CPAS-Core specification | `2.0.0-draft.1`; proposal | [core draft](../../specs/v2.0/CPAS-Core-v2.0-draft.md) | Candidate version exists, but no release manifest freezes its component set. |
| Protocol records | IDP, DKA-E, SeedToken, EEP `2.0`; transition/store/runtime profiles `1.0` | [protocol set](../../specs/v2.0/CPAS-Core-v2.0-draft.md#10-protocol-set) | Independent protocol versions are reasonable only if one bundle manifest locks exact versions. |
| Python package API | `2.0.0.dev1` | [`cpas/__init__.py`](../../cpas/__init__.py) | Not synchronized with `2.0.0-draft.1`; no declared mapping between PEP 440 and SemVer. |
| Python distribution | `cpas_autogen` `0.1.0` containing legacy and v2 packages | [`setup.py`](../../setup.py) | A v2 release must not silently repurpose the legacy distribution/version. Packaging decision required. |
| Clarence-9 declaration | IDP `2.0`; compatibility `cpas-core-2.0-draft` | [declaration](../../instances/current/Clarence-9-v2.0.json) | Suitable as a declarative artifact, not evidence of a bound or verified runtime. |
| Git releases | only `v0.1-alpha` is tagged | repository tag inventory | No precedent defines how a v2 spec bundle and Python package share a tag. |
| Changelog | CPAS-Core `1.1.0` only | [historical changelog](../specs/CHANGELOG.md) | v2 changes, breaks, deprecations, and profile status have no release-facing ledger. |
| CI | pull requests and `main`; Python 3.11–3.13 plus repository invariants | [workflow](../../.github/workflows/cpas-v2-ci.yml) | Good draft guardrail; no package-build, artifact-reproducibility, release-manifest, or tag verification job. |

### Required version decision

Before RC, the maintainer should choose and document one of these models:

1. **Specification-bundle release:** tag the repository `v2.0.0-rc.1`, publish
   an exact component manifest, and label the Python code a reference artifact
   within the bundle.
2. **Specification plus separate package:** version the standard bundle and a
   new v2 Python distribution independently, with an explicit compatibility
   table.

Reusing `cpas_autogen` `0.1.0` as if it were CPAS-Core v2 is not recommended.
It conflates historical utilities, heavy legacy dependencies, and the small v2
reference package.

## 4. Proposed release-surface classification

This table is a proposed contract boundary. It requires maintainer approval.

| Surface | Current evidence | Proposed treatment | Required before RC |
|---|---|---|---|
| CPAS-Core architecture: CIM, RRL, DKA, IC; continuity layers; epistemic transparency | Draft prose with lineage and explicit non-claims | **Stable-core candidate** | Resolve minimum CPAS-Min and capability-evidence semantics; remove remaining ambiguous maturity language. |
| IDP v2 plus declaration governance and transition records | Schemas, migrations, deterministic classifier, tests, ADR | **Stable-core candidate** | Freeze role/trust boundary and state whether vacant Clarence roles block only runtime binding or the standard release. |
| RFC 8785/JCS and domain-separated digest profiles | Accepted draft ADR, Python/Node vectors, migrations | **Stable-core candidate** | Reconcile stale verification record and lock vector/version inventory in the release manifest. |
| DKA-E v2 record and lifecycle | Schema, reference code, tests | **Stable-core candidate** | Narrow deletion and invalidation claims; distinguish portable record semantics from backend guarantees. |
| SeedToken v2 | Schema, integrity and optional HMAC implementation, tests | **Stable-core candidate with integrity-only boundary** | Decide whether public verification is excluded from 2.0 core or delivered as a separately versioned profile. |
| EEP v2 payload and explicit consensus record | Schema, validation, tests | **Stable-core candidate for payload semantics only** | State that transport, replay protection, actor authentication, and independence weighting are not EEP core conformance. |
| DKA-E store contract v1 | Backend-neutral protocol and typed failures | **Optional implementation profile** | State whether store conformance is optional for CPAS-Core conformance. |
| SQLite rollback single-host profile v1 | Implementation-tested on one POSIX host; threat model/runbook | **Optional, implementation-tested profile** | Do not label deployment-certified; close final-head evidence drift. |
| Runtime-replacement evaluation v1 | Schemas, synthetic vectors, evaluator, rubric, threat model | **Optional evaluation profile** | Replace placeholder schema IDs; retain `conformance_only` for fixtures; define live-evidence follow-up separately. |
| `cpas/` Python code and migrations | Reference implementation with tests | **Reference implementation** | Define distribution name, version source, supported Python, dependency boundary, and build test if published. |
| Clarence-9 v2 declaration | Schema-valid active declaration; runtime unbound, capabilities unknown/unavailable, reviewer/runtime operator vacant | **Current instance declaration, not standard conformance evidence** | Explain that lifecycle `active` means declaration status, not an active runtime or approved runtime binding. |
| Canonicalization/runtime fixtures | Deterministic checked-in vectors | **Normative vectors for their named profiles** | Include exact digests/files in the release manifest. Synthetic runtime fixtures remain non-empirical. |
| `cpas_autogen`, Flask T-BEEP API, dashboard, drift/Wonder metrics, AutoGen generation | Historical/experimental implementation with different assumptions and dependencies | **Historical or experimental; excluded from v2 RC contract** | Label exclusion in release notes; preserve v1.1 lineage and files. |

## 5. Status and consistency defects

| ID | Finding | Evidence | Treatment | Risk |
|---|---|---|---|---|
| R1 | No authoritative component manifest connects the core version to protocol/schema/profile versions. | Core version and protocol table are prose only. | Add a machine-readable and human-readable RC manifest. | **High** |
| R2 | Package versions conflict: `2.0.0-draft.1`, `2.0.0.dev1`, and `0.1.0`. | Core spec, `cpas.__version__`, `setup.py`. | Choose release model and one version source per artifact. | **High** |
| R3 | Runtime schemas use `https://cpas.example/...`; other v2 schemas use `https://cpas-core.org/...`. | Three runtime-evaluation schema `$id` values. | Replace placeholders before RC and assess whether this is a breaking pre-release identifier change. | **High** |
| R4 | No v2 changelog or release notes exist. | Changelog ends at historical `1.1.0`. | Add v2 draft-to-RC changes, breaks, migrations, non-claims, and profile maturity. | **High** |
| R5 | Packaging combines legacy and v2 code under `cpas_autogen` and installs legacy ML/UI dependencies for the small v2 reference. | `setup.py`, `requirements.txt`, `requirements-v2.txt`. | Separate distribution or explicitly decline package publication for RC. | **High** |
| R6 | No `pyproject.toml`, package build CI, artifact checksums, release workflow, or tag verification is defined. | Repository root and CI workflow. | Required only if an installable artifact is part of RC; otherwise explicitly scope RC to a source/spec bundle. | **Medium–High** |
| R7 | Verification records have post-merge evidence drift. | Canonicalization says hosted CI remains pending; DKA/governance/runtime records defer final-head status to PR pages. | Publish one current roll-up with exact merged commits/runs and retain old records as dated evidence. | **Medium–High** |
| R8 | Core prose says task-relevant tests can yield `verified`, while question 17 says capability-specific verification criteria remain undefined. | Core section 6 and open-question ledger. | Require a named validation profile, environment, evidence, and validity horizon for `verified`; otherwise cap at `probed`. | **High** |
| R9 | CPAS-Min has descriptive requirements but no frozen minimum conformance profile. | Core section 7 and question 15. | Define a small normative output/behavior contract without requiring metaphor or hidden traces. | **High** |
| R10 | Clarence-9 is lifecycle `active` but has no bound runtime, no runtime validation, and vacant reviewer/runtime-operator roles. | Current IDP. | Keep declaration active if intended, but state the distinction prominently in release material. | **Medium** |
| R11 | Historical alpha/v1 documents contain implementation and performance language outside current v2 evidence levels. | Historical changelog and alpha documents. | Preserve them, but exclude them explicitly from the v2 release contract. | **Medium** |
| R12 | There is no external-consumer inventory or compatibility-response record. | Question 18 and repository evidence. | Solicit and record feedback; absence of visible consumers is not evidence that none exist. | **High** |

## 6. Open-question blocker ledger

`RC entry` means the disposition must be decided before an RC tag. `RC exit`
means empirical or external work may occur during the candidate period but must
finish before final `2.0.0`. `Profile/defer` means the stable core must state the
exclusion precisely; it does not mean the underlying problem is solved.

| Question | Proposed disposition | Dependency/owner | Rationale | Confidence |
|---|---|---|---|---|
| 3 — SeedToken public-key profile | **RC entry:** choose integrity/HMAC-only core with a separately versioned signed-envelope profile, unless public verification is an explicit 2.0 requirement. | Maintainer and key-governance decision; repository spec work. | A generic unused signature field would imply unsupported security. | **High** |
| 5 — deletion versus immutable history | **RC entry:** freeze a narrow portable lifecycle/tombstone contract and make legal erasure across derivatives a deployment privacy profile. **RC exit** only if 2.0 claims erasure compliance. | Maintainer scope decision; privacy/legal and operator input. | The reference store cannot prove deletion from backups, Git, exports, or indexes. | **High** |
| 6 — distributed DKA-E consistency | **RC entry:** explicitly exclude multi-host guarantees from core/store v1. A PostgreSQL profile can follow independently; it is required only before claiming multi-host conformance. | Maintainer scope decision; database infrastructure for any profile. | SQLite evidence cannot be generalized, but CPAS record portability need not require a distributed implementation. | **High** |
| 7 — confidence calibration | **Profile/defer:** stable core requires level, basis, limitations, and any calibration provenance; domain scoring remains profiled. | Domain research and datasets. | A universal numeric scale would imply false precision. | **High** |
| 8 — real runtime compatibility evidence | **RC exit:** run the frozen suite against two attributable configurations if Clarence-9 runtime-replacement compatibility is part of final 2.0 evidence. Keep the declaration unbound otherwise. | Authorized runtime access, runtime operator, reviewer, capture provenance. | Synthetic vectors verify the harness only. | **High** |
| 9 — correlated agent errors | **Profile/defer:** core EEP records known shared dependencies and forbids independence weighting without evidence. | Multi-agent empirical study. | Agreement is not independent validation or consensus. | **High** |
| 10 — EEP transport/replay/authentication | **RC entry:** limit EEP 2.0 core to payload semantics. Version HTTP/queue/MCP transport and trust profiles separately. | Trust-root and transport design. | A transport-neutral payload cannot guarantee delivery, ordering, replay defense, or actor identity. | **High** |
| 11 — executable invalidation | **Profile/defer:** core conditions remain declarative; executable evaluators must be named, typed, sandboxed profiles. | Evaluator design and backend safety testing. | Arbitrary predicates would create code-execution and portability risk. | **High** |
| 12 — promotion of restored policy | **RC entry:** codify a hard core rule that ordinary DKA/project/platform state is data only; promotion requires a separate authenticated and authorized policy channel. | Trust profile remains external. | This is a prompt-injection and authority boundary, not a memory feature. | **High** |
| 13 — EEP/MCP/A2A/vendor interoperability | **Profile/defer:** use versioned adapters; do not claim a universal transport. | External protocols and adapter tests. | Those protocols have different scopes and evolve independently. | **Medium–High** |
| 14 — platform memory discovery | **RC entry:** freeze `unknown` as the required state when retention/scope/provenance cannot be observed. | Platform APIs for stronger evidence. | Product branding is not persistence evidence. | **High** |
| 15 — CPAS-Min minimum | **RC entry:** define minimum identity/limitation, task-relevant uncertainty, provenance, and safety behavior; metaphor and ritual remain optional/off. | Repository protocol and conformance tests. | A named conformance mode needs a falsifiable minimum. | **High** |
| 16 — metaphor standardization | **Profile/defer:** keep mappings non-normative and require explicit epistemic state underneath. | Local language/cultural calibration. | Standardization could decrease clarity and portability. | **High** |
| 17 — `probed` versus `verified` | **RC entry:** require named capability validation profiles; without one, observations cannot exceed `probed`. Profiles define evidence, environment, freshness, and reviewer requirements. | Repository base semantics; domain-specific follow-ons. | Current wording is too permissive for a stable evidence label. | **High** |
| 18 — unseen external consumers | **RC entry:** publish a compatibility-impact request and response window. **RC exit:** record known consumers, responses, or the bounded fact that none responded. | Spartan-M34 and external consumers. | Repository inspection cannot establish absence of private integrations. | **High** |

## 7. Authority and dependency boundary

| Work | Repository can implement? | Required external input |
|---|---|---|
| Release manifest, version mapping, schema-ID correction, v2 changelog, status cleanup, CPAS-Min profile, base capability evidence rules | Yes | Maintainer approval of normative decisions |
| Python distribution split/build/release | Yes, if selected | Package name/registry ownership and release authority |
| SeedToken public-key trust profile | Partly | Key ownership, rotation, revocation, recovery, and trust-root governance |
| Clarence-9 reviewer/runtime-operator appointment | No | Attributable human appointment under declaration governance |
| Two-runtime empirical capture | Harness/adapters partly | Authorized provider/runtime access, exact configurations, reviewer |
| PostgreSQL/distributed DKA-E profile | Partly | Real server/test infrastructure and operational threat model |
| Privacy/legal erasure certification | No | Deployment inventory, retention policy, backups/derivatives, jurisdictional review |
| External-consumer compatibility | No | Consumer disclosure and feedback |

Vacant roles must remain vacant until an authorized human appointment is
recorded. Repository ownership, a model response, or a passing test cannot
silently fill them.

## 8. Proposed `2.0.0-rc.1` criteria

### 8.1 Entry criteria

All items are required before creating an RC tag:

- an approved release manifest lists every normative core artifact, optional
  profile, vector, schema ID, version, and digest;
- one documented version-authority model covers the repository tag, core spec,
  and any published Python distribution;
- placeholder identifiers are removed and pre-release identifier migrations
  are documented;
- a v2 changelog records breaking changes from v1.1 and from earlier v2 drafts;
- the stable-core/optional/reference/historical boundary is visible from the
  root README and v2 index;
- questions 3, 5, 6, 10, 12, 14, 15, and 17 have approved core dispositions,
  even where that disposition is explicit exclusion;
- a compatibility-impact request for question 18 is open with a stated response
  window;
- all normative schemas, examples, digest vectors, migrations, and reference
  tests pass from a clean checkout on supported runtimes;
- Python and Node canonicalization vectors agree;
- a current verification roll-up references the exact candidate commit and
  completed final-head CI;
- release notes list unresolved RC-exit work and the non-claims below.

### 8.2 Exit criteria for final `2.0.0`

- all accepted RC feedback is dispositioned with compatibility impact;
- external-consumer responses or non-responses are recorded without inferring
  invisible consumers away;
- the maintainer decides whether final 2.0 includes a Clarence-9 runtime binding;
  if it does, authorized real-runtime evidence and human review are required;
- any artifact published to a package registry builds reproducibly and matches
  the tagged source/release manifest;
- no unresolved issue changes stable-core semantics without a versioned decision
  and migration plan;
- the final tag points to the exact reviewed commit and all required CI jobs
  pass for that commit;
- final release notes preserve all applicable non-claims.

Passing these criteria would support a versioned protocol/reference release. It
would still not certify an arbitrary deployment.

## 9. Required non-claims for an RC

An RC must not claim:

- consciousness, emotion, permanent selfhood, inherent memory, or ontological
  continuity;
- identity proof or behavioral equivalence from an identity digest;
- live provider/runtime compatibility from synthetic fixtures;
- actor authentication, authorization, non-repudiation, or public verification
  from an integrity digest or unsigned declaration;
- multi-host consistency from the SQLite single-host profile;
- encryption, key management, complete erasure, privacy/legal compliance,
  disaster recovery, or deployment certification;
- independent multi-agent consensus from agreement alone;
- compatibility with external consumers that were not inventoried or tested.

## 10. Recommended follow-on sequence

1. **Release contract and metadata.** Add the release manifest, version policy,
   canonical schema IDs, v2 changelog, packaging decision, and current
   verification roll-up.
2. **Core semantic freeze.** Resolve CPAS-Min, capability evidence levels,
   restored-policy promotion, platform-memory unknown handling, and explicit
   EEP/store scope.
3. **Trust-direction decision.** Decide SeedToken public verification and record
   whether Clarence reviewer/runtime roles remain vacant for RC.
4. **Persistence/privacy scope ADR.** Decide what core deletion means and whether
   distributed persistence is excluded or scheduled as a separately tested
   profile.
5. **Consumer-impact window.** Solicit known users/integrators and record
   compatibility commitments.
6. **Optional empirical pilots.** Run real runtime replacement and/or a
   PostgreSQL profile only with the necessary access, authority, and evidence.
7. **RC review and tag.** Re-run clean-checkout verification, freeze the
   manifest, review non-claims, and create `2.0.0-rc.1` only if entry criteria
   pass.

Each step should be a bounded issue and reviewable PR. Steps 1 and 2 are the
next repository-controlled work. Steps 3–6 contain decisions or evidence that
must not be fabricated by the reference implementation.

## 11. Conclusion

The completed stabilization roadmap established a credible implementation-
tested draft foundation. The next defensible action is not a release tag. It is
to freeze a coherent release contract, resolve or exclude stable-core semantic
ambiguities, and obtain the external decisions/evidence that repository tests
cannot supply.

Preserving the lineage now requires tighter release boundaries, not broader
claims.
