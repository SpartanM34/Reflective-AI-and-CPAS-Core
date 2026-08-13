# CPAS-Core v2 open questions

Polished protocol text should not conceal unresolved design choices. Confidence
describes confidence that the question materially affects a production v2—not
confidence in a proposed answer.

| # | Open question | Why unresolved | Current leaning | Importance confidence |
|---|---|---|---|---|
| 3 | Should SeedToken gain a public-key signature profile? | HMAC is implementable but unsuitable for public verification and non-repudiation; algorithm agility introduces complexity. | Draft a separate signed-envelope profile only after threat-model and key-governance review. | **High** |
| 5 | How are DKA deletions reconciled with immutable Git/event history and privacy law? | The SQLite profile can purge its live canonical payload and retain a tombstone, but backups, audit exports, derived indexes, Git history, and legal obligations remain deployment-specific. | Classify before storage; use erasable encrypted payloads/non-Git stores where deletion is mandatory; require every derivative/copy to join the retention decision. | **High** |
| 6 | What is the normative distributed DKA-E consistency model? | The v1 store contract and SQLite profile resolve single-host atomic/CAS semantics only. Databases, Git, object/event stores, replicas, and multiple writers need a separately tested model. | Add a PostgreSQL client/server profile with real server execution before claiming multi-host consistency; do not generalize SQLite results. | **High** |
| 7 | How should confidence be calibrated and propagated? | Subjective numbers are easy to serialize but may imply unsupported precision; different domains need different calibration evidence. | Require basis/calibration labels now; develop domain profiles and scoring rules later. | **High** |
| 8 | What empirical evidence is sufficient for behavioral compatibility across real model replacements? | The v1 gate-and-rubric harness now defines artifacts, drift categories, synthetic conformance vectors, and mandatory review, but no two hosted runtimes have been captured and reviewed. | Run the frozen suite against attributable real configurations, add task/domain samples, and calibrate reviewer agreement without treating the result as identity proof. | **High** |
| 9 | How are correlated agent errors measured before consensus aggregation? | Provider/model/prompt/retrieval overlap can make “independent agents” highly dependent, and platforms expose incomplete lineage. | Record known shared dependencies and avoid independence weights unless empirically justified. | **High** |
| 10 | Which EEP transport/replay/authentication profile is normative? | The core message is transport-neutral; interoperable deployments still need delivery IDs, ordering, replay windows, identities, and trust roots. | Publish optional HTTP/queue/MCP profiles after core schema review. | **Medium–High** |
| 11 | How should invalidation conditions become executable without arbitrary code? | Natural-language triggers are portable but not automatically testable; executable predicates can be unsafe or backend-specific. | Use named, typed evaluator profiles and retain the human-readable condition. | **High** |
| 12 | Can externally restored policy ever become trusted instruction? | Treating everything as data is safe but limits managed policy updates; promotion creates a prompt-injection and governance boundary. | Require separate signed/authorized policy channels, never an ordinary DKA field. | **High** |
| 13 | What is the interoperability relationship among EEP, MCP, A2A-like protocols, and vendor agent messages? | MCP handles capabilities/context more than epistemic claims; other protocols evolve independently. | Keep EEP payload semantics independent and define adapters, not a universal transport. | **Medium** |
| 14 | How are platform memory and project state discovered accurately? | Hosted products may not expose full retention, scope, or per-item provenance through APIs. | Report `unknown` when unavailable; never infer from product branding. | **High** |
| 15 | What does CPAS-Min conformance minimally require? | Reducing ritual/metaphor is clear, but an overly thin mode can omit provenance or uncertainty and still use the label. | Require identity/limitations, task-relevant uncertainty, provenance, and safety; make richer fields conditional. | **Medium–High** |
| 16 | Should metaphor mappings be standardized across languages/cultures? | Metaphors compress stance but can mislead or translate poorly. | Keep them non-normative, locally calibrated, and always backed by explicit state. | **Medium** |
| 17 | What evidence qualifies `probed` versus `verified` across all capabilities? | Runtime-evaluation v1 now enforces evidence kind, transcript assurance, and per-probe validity horizons, but verification criteria remain capability/domain-specific. | Reuse the v1 evidence boundary, then define named profiles and revalidation schedules per capability; never promote model-name or fixture evidence. | **High** |
| 18 | What migration commitments exist for external consumers not visible in this repository? | No deployment/consumer inventory was supplied. Breaking changes may affect private integrations. | Do not release stable v2 until maintainers solicit and record consumer impact. | **High** |

## Decisions required before a stable 2.0.0

At minimum, maintainers should resolve production trust/reviewer appointments,
multi-host persistence and privacy/deletion handling,
capability evidence levels, SeedToken authentication direction, and empirical
live-runtime replacement evidence. Other questions can remain profiled extensions
if the stable core clearly labels them.

## Resolved during draft hardening

The former question 4 is resolved for the v2 draft by
[ADR-0001](adr/0001-canonicalization-and-digest-profiles.md): new semantic
digests use RFC 8785/JCS plus explicit artifact domains, while the former Python
profile remains frozen for legacy verification. The remaining pre-release task
is interoperability review against the published Python and Node vectors, not
selection of another encoding.

Questions 1 and 2 are resolved at the protocol/profile level by
[ADR-0002](adr/0002-declaration-governance-and-identity-evolution.md) and the
[IDP governance profile](../specs/v2.0/IDP-Governance-v2.0.md). Governance is
outside the stable identity projection; deterministic classification records
runtime rebind, compatible amendment, identity evolution, or new identity;
and the predecessor policy governs transitions. Clarence-9 names Spartan-M34
as maintainer/issuer/human override while reviewer, runtime operator, and
successor remain vacant. Production actor authentication, reviewer appointment,
and emergency succession are deliberately still unresolved rather than being
inferred from repository metadata.

[ADR-0003](adr/0003-dka-e-single-host-sqlite-profile.md) resolves the first
production-oriented persistence profile at implementation-tested level. The
[store contract](../specs/v2.0/DKA-Store-Contract-v1.0.md) defines atomic CAS,
failure, authorization-input, audit, and rehydration boundaries; the
[SQLite profile](../specs/v2.0/DKA-E-SQLite-Profile-v1.0.md) verifies those on a
single POSIX host with rollback journaling. It deliberately does not resolve
distributed consistency, engine authentication, encryption/key management,
backup retention, complete erasure, or deployment certification, so questions
5 and 6 remain open in those narrower forms.

[ADR-0004](adr/0004-runtime-replacement-evaluation.md) resolves the protocol
shape of question 8 with exact manifests/configurations/transcripts, four
separate drift categories, zero-tolerance required capability/policy gates, no
aggregate identity score, and mandatory human review. The
[reference vectors](../compliance-tests/runtime-evaluation/clarence-9-v1/) are
synthetic; they verify harness behavior only. Provider adapters, two attributable
live-runtime captures, reviewer/runtime-operator appointments, semantic
calibration, and recurring drift baselines remain open.
