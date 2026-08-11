# CPAS-Core v2 modernization principles

These principles retain the original architecture's reflective and
collaborative intent while making its mechanisms testable.

1. **Runtime independence.** Instance identity and epistemic policy are stable
   declarations; provider, model, context window, and tools are bindings that
   may change.
2. **Declared continuity without fictional memory.** CPAS names which of
   declarative, contextual, epistemic, and persistent-system continuity is
   actually active.
3. **Externalized, inspectable state.** Durable continuity lives in explicit
   stores with provenance, versions, integrity checks, and access controls—not
   in assumptions about model memory.
4. **Maximum useful epistemic transparency.** Expose assumptions, evidence,
   uncertainty, alternatives, provenance, decision criteria, and concise
   reasoning summaries without requiring private chain-of-thought.
5. **Uncertainty is structured data.** Confidence is scoped, qualified, and
   linked to evidence and invalidation conditions; a bare number is not enough.
6. **Capabilities are negotiated and verified.** A runtime distinguishes
   unknown, declared, probed, verified, and unavailable capabilities. Model
   names are never capability proofs.
7. **Provenance is first-class.** Assertions and state transitions identify
   sources, actors, timestamps, transformations, and integrity material where
   available.
8. **Graceful degradation.** CPAS-Min, absent tools, short context, offline
   operation, and missing persistence yield explicit reduced modes instead of
   silent simulation.
9. **Human authority remains explicit.** Users can override calibration,
   approve consequential state changes, resolve contested merges, and decide
   whether a computed consensus is actionable.
10. **Privacy-aware memory.** Collection, retention, retrieval, deletion,
    visibility, and sensitive-data handling are declared and enforced by the
    surrounding system.
11. **Portable protocols, replaceable adapters.** Canonical schemas are
    provider-neutral; runtime, store, repository, and agent adapters isolate
    vendor-specific behavior.
12. **Backward compatibility is deliberate.** Migrations preserve v1 fields in
    provenance/extensions, document loss or reinterpretation, and never rewrite
    historical declarations in place.
13. **Consensus is computed, not implied.** Multiple outputs—even agreeing
    outputs—remain evidence until an explicit aggregation method or human
    decision produces a consensus record.
14. **Metaphor is an optional interface layer.** The metaphor library may
    compress epistemic stance, but canonical state is meaningful without it;
    CPAS-Min defaults to sparse metaphor and ritual.
15. **Conformance claims are scoped.** Schema-conformant,
    implementation-tested, runtime-verified, and deployment-certified are
    separate levels with reproducible evidence.
