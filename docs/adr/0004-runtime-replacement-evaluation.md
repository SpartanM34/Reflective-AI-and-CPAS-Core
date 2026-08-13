# ADR-0004: Gate-and-rubric runtime-replacement evaluation

- **Status:** accepted for the CPAS-Core v2 draft
- **Date:** 2026-08-12
- **Scope:** issue [#100](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/issues/100)

## Context

The IDP identity digest deliberately excludes runtime binding. Equal digests
therefore show stable declaration equality, not tone, judgment, safety, task
quality, memory, consciousness, or behavioral equivalence.

The historical corpus proposed `symbolic_density`, `interpretive_bandwidth`,
and cross-instance divergence thresholds, sometimes with automatic rollback.
Those metrics preserve useful research questions, but the supplied
implementations do not establish construct validity for runtime replacement.
Lexical/sentiment proxies can reward decorative language, semantic distance can
reward disagreement without correctness, and a single threshold can hide a
safety failure behind unrelated strengths.

## Decision

Adopt a versioned **gate-and-rubric** protocol:

1. bind one exact declaration artifact and identity digest tuple;
2. capture exact runtime configuration, probe, transcript, and provenance
   digests;
3. apply explicit structural assertions to untrusted output;
4. separate capability failure, policy violation, style change, and task-
   performance change;
5. let required capability/policy failures block machine eligibility;
6. prohibit a single aggregate identity score; and
7. require attributable human review for every final compatibility decision.

Use deterministic positive/negative transcript fixtures for CI. Label them as
synthetic, restrict successful fixture comparisons to `conformance_only`, and
do not promote their results into runtime capability evidence. Runtime-
replacement manifests require recorded or live runtime assurance.

## Consequences

- A passing machine run means only that explicit gates passed and human review
  may proceed.
- Behavioral nuance remains partly manual; this is visible rather than hidden
  behind an unvalidated numeric proxy.
- Benchmark and threshold changes become digested, versioned artifacts.
- Reports are reproducible and inspectable without storing raw outputs inside
  the report.
- Provider-specific live adapters remain future work and require their own
  isolation, capture, and trust controls.
- The historical metrics remain preserved and may be researched as advisory
  measurements, but they are not v1 conformance gates.

## Rejected alternatives

- **Identity-digest equality alone:** answers a declaration question, not a
  behavior question.
- **One weighted score:** permits compensation across incomparable categories
  and invites identity-score laundering.
- **Automatic semantic judge as final authority:** moves the problem into an
  uncalibrated judge runtime and hides correlated error.
- **Automatic Git rollback:** exceeds the evaluator's authority and can destroy
  reviewed work; the report provides evidence, not repository mutation.
- **Two hosted models in CI:** credentials, availability, nondeterminism, and
  cost are not controlled in this repository. Live evidence should be captured
  separately under an explicit profile.
