# CPAS-Core v2 open questions

Polished protocol text should not conceal unresolved design choices. Confidence
describes confidence that the question materially affects a production v2—not
confidence in a proposed answer.

| # | Open question | Why unresolved | Current leaning | Importance confidence |
|---|---|---|---|---|
| 1 | Which fields belong permanently in the stable identity projection? | Safety and epistemic policy constrain identity, but governance may need to update them without claiming a new instance. | Keep them stable within IDP major version; record reviewed identity evolution explicitly. | **High** |
| 2 | Who is authorized to issue, revise, or retire a Clarence-9 declaration? | Maintainer attribution is present, but no governance, key, or succession policy is implemented. | Define maintainer/reviewer roles and a signed release process before production claims. | **High** |
| 3 | Should SeedToken gain a public-key signature profile? | HMAC is implementable but unsuitable for public verification and non-repudiation; algorithm agility introduces complexity. | Draft a separate signed-envelope profile only after threat-model and key-governance review. | **High** |
| 5 | How are DKA deletions reconciled with immutable Git/event history and privacy law? | Tombstones retain evidence of deletion but Git history may retain the content; rewriting history harms provenance. | Classify sensitive records before storage and use erasable encrypted payloads or non-Git stores where deletion is mandatory. | **High** |
| 6 | What is the normative distributed DKA-E consistency model? | The file reference demonstrates local CAS only. Databases, Git, and object/event stores have different transaction and conflict guarantees. | Specify a minimal store contract plus backend profiles rather than promise universal transactions. | **High** |
| 7 | How should confidence be calibrated and propagated? | Subjective numbers are easy to serialize but may imply unsupported precision; different domains need different calibration evidence. | Require basis/calibration labels now; develop domain profiles and scoring rules later. | **High** |
| 8 | How is behavioral continuity evaluated across model replacements? | Identity digest invariance tests declaration continuity, not tone, judgment, safety, or task performance. | Maintain a versioned behavioral evaluation suite with human review and drift thresholds, without treating it as consciousness continuity. | **High** |
| 9 | How are correlated agent errors measured before consensus aggregation? | Provider/model/prompt/retrieval overlap can make “independent agents” highly dependent, and platforms expose incomplete lineage. | Record known shared dependencies and avoid independence weights unless empirically justified. | **High** |
| 10 | Which EEP transport/replay/authentication profile is normative? | The core message is transport-neutral; interoperable deployments still need delivery IDs, ordering, replay windows, identities, and trust roots. | Publish optional HTTP/queue/MCP profiles after core schema review. | **Medium–High** |
| 11 | How should invalidation conditions become executable without arbitrary code? | Natural-language triggers are portable but not automatically testable; executable predicates can be unsafe or backend-specific. | Use named, typed evaluator profiles and retain the human-readable condition. | **High** |
| 12 | Can externally restored policy ever become trusted instruction? | Treating everything as data is safe but limits managed policy updates; promotion creates a prompt-injection and governance boundary. | Require separate signed/authorized policy channels, never an ordinary DKA field. | **High** |
| 13 | What is the interoperability relationship among EEP, MCP, A2A-like protocols, and vendor agent messages? | MCP handles capabilities/context more than epistemic claims; other protocols evolve independently. | Keep EEP payload semantics independent and define adapters, not a universal transport. | **Medium** |
| 14 | How are platform memory and project state discovered accurately? | Hosted products may not expose full retention, scope, or per-item provenance through APIs. | Report `unknown` when unavailable; never infer from product branding. | **High** |
| 15 | What does CPAS-Min conformance minimally require? | Reducing ritual/metaphor is clear, but an overly thin mode can omit provenance or uncertainty and still use the label. | Require identity/limitations, task-relevant uncertainty, provenance, and safety; make richer fields conditional. | **Medium–High** |
| 16 | Should metaphor mappings be standardized across languages/cultures? | Metaphors compress stance but can mislead or translate poorly. | Keep them non-normative, locally calibrated, and always backed by explicit state. | **Medium** |
| 17 | What evidence qualifies `probed` versus `verified` and when does it expire? | A successful health check differs from task-relevant behavior; freshness varies by capability. | Define capability-specific test profiles and validation horizons. | **High** |
| 18 | What migration commitments exist for external consumers not visible in this repository? | No deployment/consumer inventory was supplied. Breaking changes may affect private integrations. | Do not release stable v2 until maintainers solicit and record consumer impact. | **High** |

## Decisions required before a stable 2.0.0

At minimum, maintainers should resolve declaration governance, production
persistence profiles, privacy/deletion handling,
capability evidence levels, SeedToken authentication direction, and a behavioral
runtime-replacement evaluation. Other questions can remain profiled extensions
if the stable core clearly labels them.

## Resolved during draft hardening

The former question 4 is resolved for the v2 draft by
[ADR-0001](adr/0001-canonicalization-and-digest-profiles.md): new semantic
digests use RFC 8785/JCS plus explicit artifact domains, while the former Python
profile remains frozen for legacy verification. The remaining pre-release task
is interoperability review against the published Python and Node vectors, not
selection of another encoding.
