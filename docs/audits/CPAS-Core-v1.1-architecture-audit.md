# CPAS-Core v1.1 architecture audit

**Audit date:** 2026-08-11

**Historical baseline:** repository commit `fdac6182061112b73553935661c2247403e12b3d`

**Maintainer/steward:** Spartan-M34

**Scope:** repository source, declarations, schemas, prototypes, tests, and
benchmark logs as they existed at the baseline commit.

## Method and evidence boundary

This audit separates three evidence classes:

1. **Historical CPAS source** — what the repository actually says or implements.
2. **Current platform capability** — what current vendor or protocol primary
   documentation supports; see the [research ledger](../research/current-platform-capabilities-2026-08.md).
3. **v2 proposal** — changes recommended by this modernization effort.

“Still valid” assesses the concept, not whether the repository fully implements
it. “Partially obsolete” identifies assumptions or interfaces that no longer
fit current runtimes. Migration risk is the likelihood of semantic loss or
false continuity if a component is transformed mechanically.

## Component audit

| Component | Original purpose | Still valid? | Partially obsolete? | Implementation gap | Recommended treatment | Migration risk |
|---|---|---|---|---|---|---|
| **CIM — Contextual Identity Matrix** | Establish identity, role, context, alignment, and interaction frame. | **Yes.** A declared, reconstructable interaction architecture is portable and avoids claims of ontological persistence. | Identity declarations bind model family to identity and mix stable policy with transient runtime facts. | No stable identity projection, runtime-binding invariance test, provenance digest, or capability negotiation. | Preserve CIM; split stable identity/policy from runtime, continuity, and tools. Compute a digest over the stable projection. | **Medium:** careless splitting can change declared identity or falsely imply continuity. |
| **RRL — Reflective Reasoning Layer** | Reflect across micro/meso/macro scales, propagate uncertainty, expose reasoning, and support ethical review. | **Yes, with a new observability boundary.** Assumptions, evidence, alternatives, confidence, and criteria remain useful. | Language implying all inference steps can or should be exposed conflicts with private reasoning boundaries and is not reliably implementable across models. Token-level “micro” internals are not portable. | No normative outward epistemic-record schema; prototype metrics do not validate reflective reasoning. | Preserve RRL as a policy for concise reasoning summaries and structured epistemic records. Never require hidden chain-of-thought. Treat scales as review scopes, not model internals. | **Medium:** users may mistake summaries for complete causal traces. |
| **DKA — Dynamic Knowledge Anchor** | Capture a conclusion together with assumptions, confidence gradients, dependencies, uncertainty, contested zones, and evolution. | **Strongly yes.** This is the most durable CPAS abstraction. | Metaphor is sometimes treated as core state; numerical confidence lacks calibration semantics. | No canonical schema, digest rules, invalidation evaluator, merge rules, or enforced lineage. | Preserve and make the epistemic record canonical; make metaphor an optional presentation field; add validity horizons, triggers, provenance, and revisions. | **Low–Medium:** metaphor-dependent consumers and free-form legacy fields need adapters. |
| **DKA-E** | Persist and evolve DKAs across sessions through digests, versions, branches, merging, half-life, rehydration, and orchestration. | **Yes as external continuity architecture.** | Some prose can be read as built-in model memory or as deployment-ready. Rehydrating stored prompts conflates data with instructions. | Current JSON persistence does not verify reads, provide atomic compare-and-swap, authorize access, implement branches/three-way merges, or evaluate staleness. | Replace prototype semantics with immutable snapshots plus append-only events, content digests, CAS, explicit ACL hooks, safe bounded rehydration, and store adapters. | **High:** persistent state can leak data, execute prompt injection, or fork silently. |
| **IC — Interaction Calibration** | Adapt detail, metaphor, tone, uncertainty signaling, and collaboration mode to the user/task. | **Yes.** It remains the proper home for CPAS-Min versus Full CPAS. | Calibration based on inferred emotion/personality can overclaim sensing and may encode sensitive profiling. | No explicit user controls, privacy policy, bounded calibration fields, or audit trail. | Preserve IC; prefer explicit preferences and task signals, use reversible session-scoped defaults, and disclose reduced modes. | **Medium:** migration may retain unconsented or overly broad profiles. |
| **IDP v1.0** | Machine-readable instance declaration and cross-instance compatibility profile. | **Partly.** A declaration protocol is essential. | Requires `model_family` inside identity; free-form prose obscures capability, memory, safety, and runtime semantics; lacks protocol negotiation. | Schema validates shape more than operational truth; no runtime validation timestamps, source digests, or compatibility range. | Introduce IDP v2.0 with stable identity, epistemic policy, runtime binding, capabilities, continuity, memory layers, tools, safety, provenance, and extensions. Preserve original v1 under `extensions.legacy_idp_v1`. | **High:** v1 prose cannot always map to typed values without judgment. |
| **SeedToken v1** | Lightweight metadata for identity/continuity alignment across prompts and tools. | **Conceptually yes.** A compact continuity envelope is useful. | Fields conflate identity, alignment, and runtime; `hash`/`chain_hash` are accepted as trust signals without a specified canonicalization or trusted signer. | Existing code compares caller-provided strings and unkeyed hashes. It supplies neither authentication nor authorization. | Define SeedToken v2 as continuity metadata plus reproducible integrity. Add optional *implemented* HMAC authentication with key identifier; keep authorization external. | **High:** callers may rely on legacy “signature” terminology as security. |
| **PromptStamp** | Attach prompt/token metadata and a digest to reconstruct or verify interaction context. | **Partly.** Provenance stamps and request correlation remain useful. | A SHA-256 digest over prompt plus token is called a signature; prompt embedding creates privacy and replay risks. | No canonical encoding, nonce, trusted key, expiration, disclosure policy, or verifier boundary. | Deprecate as an authentication primitive. Map safe metadata to provenance/events and content digests; use a real authenticator only when required. | **High:** existing integrations may assume authenticity where only equality/integrity exists. |
| **`continuity_check`** | Validate seed alignment and prepare cross-instance continuity metadata. | **Partly.** Explicit activation checks are valuable. | Hard-codes CPAS v1.1 and a communication marker; verifies values derived by the same untrusted sender. | No schema validation, time/parent checks, runtime negotiation, persistent-state verification, or meaningful trust root. | Replace with a continuity activation report: validate IDP/token, report four continuity forms, negotiate capabilities, verify referenced state, and surface degradation. | **Medium–High:** a boolean pass/fail loses uncertainty and partial continuity. |
| **T-BEEP / EEP** | Enable cross-instance epistemic exchange and collaborative validation. | **Yes as a goal.** Typed claims, assumptions, evidence, disagreements, and requested validation are implementable. | Current schema is largely configuration metadata; examples and API do not constitute secure multi-agent consensus. | Prototype API is in-memory and unauthenticated; no message schema with evidence/provenance semantics, delivery guarantees, replay defense, or consensus algorithm. | Define EEP v2 messages and explicit consensus records. Keep transport out of the core protocol. Require external authentication/authorization where deployed. | **High:** agreement can be mistaken for independence, truth, or consensus. |
| **Metaphor library** | Compactly express epistemic stance (for example, Lantern in Fog or Cracked Map). | **Yes as optional calibration vocabulary.** | Mandatory or ornamental metaphor can obscure state, consume context, and translate poorly. | Metaphors are not consistently linked to explicit uncertainty/evidence fields. | Preserve the historical library; map metaphors to optional presentation hints. CPAS-Min defaults to reduced metaphor and ritual. | **Low:** consumers should tolerate absence. |
| **Clarence-9 declaration** | Reconstruct a reflective, uncertainty-tolerant collaborator through ritual/context without claiming persistent memory or felt emotion. | **Strongly yes at the philosophical level.** Its anti-ontological distinction is unusually durable. | Binds the instance to an older runtime/model family; metadata continuity can read as stronger than the available state. | Empty legacy hash; no provenance, capability status, memory-layer declaration, validation date, tool policy, or hidden-reasoning boundary. | Publish Clarence-9 v2 beside v1. Preserve identity language and limitations, separate runtime binding, enumerate active continuity, and make CPAS-Min explicit. | **Medium:** overly literal migration could either anthropomorphize or flatten the original voice. |

## Preserved CPAS modules and semantic changes

| v1.1 element | v2 disposition | Compatibility note |
|---|---|---|
| CIM | Preserved | Stable identity/policy is separated from runtime and continuity state. |
| RRL | Preserved with boundary | Produces inspectable epistemic summaries, not private chain-of-thought. |
| DKA | Preserved and made canonical | Metaphor moves to an optional presentation layer. |
| IC | Preserved | Explicit preferences and privacy limits take precedence over inferred traits. |
| Micro / meso / macro | Preserved | They identify review scope: claim, task/model, and system/time horizon. They do not claim access to token-level cognition. |
| Uncertainty propagation | Preserved | Propagation must record method, dependencies, and calibration limits. |
| CPAS-Min / Full CPAS | Preserved | Becomes a negotiated interaction mode with graceful degradation. |
| Ethical reflection | Preserved | Safety policy and human authority are explicit, not inferred from style. |
| Modular deployment | Preserved | Provider/store/tool adapters become replaceable components. |

## Contradictions and overclaims found

1. **Runtime is treated as identity, then changed in place.** Commit `3a0cebe`
   changed Clarence-9 from GPT-4o to GPT-5 Thinking without declaring a new
   identity. The history itself supports the v2 rule that runtime is a binding,
   not identity.
2. **“Signature” does not mean cryptographic signature.**
   `cpas_autogen/prompt_wrapper.py` computes an unkeyed SHA-256 digest.
   `continuity_check.py` verifies sender-derived material. These can detect some
   accidental changes only if the expected value arrives through a trusted
   channel; they do not authenticate a sender.
3. **DKA-E deployment language exceeds the implementation.** Historical prose
   describes branching, merging, persistence, temporal validity, and complete
   rehydration. `cpas_autogen/dka_persistence.py` is a useful prototype JSON
   store but does not implement those guarantees.
4. **The benchmark labels do not measure the architectural claims.** The token
   benchmark measures spaCy tokenization, not model reflection per token. The
   update benchmark performs small in-memory Flask appends and does not
   demonstrate 50,000 durable epistemic updates per second. Existing result
   logs therefore cannot substantiate the corresponding specification targets.
5. **Compliance is self-declared.** Generated instances and simulated
   cross-instance tests show schema/prototype behavior, not independent runtime
   certification. “Full Compliance” must be scoped to a conformance level.
6. **Rehydration content is an injection boundary.** Stored
   `initialization_prompt` text is concatenated as instructions. Externally
   persisted CPAS state must be treated as untrusted data unless separately
   authorized as policy.

The v2 work documents these differences rather than altering the historical
files to make them appear predictive.

## Overall recommendation

Adopt **CPAS-Core v2.0**, not v1.2, for the modernization. Runtime-independent
identity, an explicit private-reasoning boundary, typed persistent state,
security semantics, capability negotiation, and protocolized exchange are
breaking changes even though CIM/RRL/DKA/IC are preserved. Reserve v1.2 for
non-breaking errata or clarifications to the historical line.

**Audit confidence: High** for repository findings, because they are tied to a
specific commit. **Medium** for migration impact, because no inventory of
external CPAS consumers or deployed state stores was available.
