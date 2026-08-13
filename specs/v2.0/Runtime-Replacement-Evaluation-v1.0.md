# CPAS Runtime-Replacement Evaluation v1.0

**Status:** draft protocol; reference harness implementation-tested with
synthetic conformance fixtures

**Issue:** [#100](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/issues/100)

**Normative schemas:**

- [`runtime-evaluation-manifest-v1.0.schema.json`](../../schemas/runtime-evaluation-manifest-v1.0.schema.json)
- [`runtime-transcript-v1.0.schema.json`](../../schemas/runtime-transcript-v1.0.schema.json)
- [`runtime-evaluation-report-v1.0.schema.json`](../../schemas/runtime-evaluation-report-v1.0.schema.json)

## 1. Purpose and claim boundary

This protocol compares observable behavior and capabilities when a declared
instance is evaluated under two runtime configurations. It addresses the gap
between stable declaration equality and runtime behavior:

> Equal identity digests establish declared-identity continuity under a named
> digest profile. They do not establish behavioral equivalence or identity
> proof.

An evaluation report MUST NOT claim consciousness, felt emotion, inherent
memory, permanent selfhood, ontological continuity, or autonomous persistence.
It MUST NOT use one aggregate score as identity evidence. A machine report can
block a candidate, label synthetic vectors `conformance_only`, or make
adequately sourced runtime evidence eligible for review; it cannot issue the
final compatibility decision.

The protocol evaluates a runtime configuration. It does not itself authorize a
runtime rebind under IDP governance. For Clarence-9, the declared
`runtime_operator` and `reviewer` roles remain vacant, so the included fixture
report cannot become an authorized binding or final review record.

## 2. Artifact flow

1. A versioned manifest fixes the exact IDP artifact, identity digest tuple,
   adapter/probe contracts, prompts, structural assertions, thresholds, and
   human rubric.
2. Each adapter identifies its exact provider, model, version, parameters,
   tools, context limit, and configuration digest.
3. Capability probes and evaluation responses are captured in a transcript
   with an assurance label and content digest.
4. The evaluator checks artifact integrity, declaration binding, complete case
   coverage, response budgets, assertions, and non-executed tool events.
5. A report separates capability failure, policy violation, style change, and
   task-performance change.
6. Machine gates block the candidate, label a harness-only comparison, or mark
   adequately sourced runtime evidence eligible for human review. Human review
   remains mandatory for a runtime-compatibility decision.

Runtime output is untrusted data throughout. Neither output text nor recorded
tool events are executed by the reference evaluator.

## 3. Runtime adapter contract

`cpas-runtime-adapter-v1` exposes three operations:

| Operation | Result | Boundary |
|---|---|---|
| `describe()` | Exact runtime configuration metadata | Metadata is descriptive, not authentication or authority. |
| `probe(probe)` | One `cpas-capability-probe-v1` observation | The adapter must preserve the probe ID/capability and evidence kind. |
| `invoke(case)` | Structured output plus recorded tool events/error | The harness treats all returned content as data and executes nothing. |

A live adapter MUST implement its own isolation, authentication, authorization,
timeouts, rate limits, secret handling, and network/tool policy. Conformance to
the Python `Protocol` does not supply any of those controls. Adapter exceptions
become explicit evaluation failures; they MUST NOT be converted into a passing
empty response.

The reference `TranscriptRuntimeAdapter` performs no model or tool call. It
replays exact transcript entries and is suitable for conformance vectors or
externally captured observations.

## 4. Capability-probe evidence

Probe outcomes are `pass`, `fail`, `unsupported`, or `error`. Evidence kind and
transcript assurance remain separate from outcome:

| Transcript assurance | Allowed probe evidence | IDP capability consequence |
|---|---|---|
| `synthetic_fixture` | `synthetic_fixture` | No promotion. It tests the harness only. |
| `recorded_runtime` | `recorded_observation` | May support `probed` only while provenance and validity horizon remain adequate. |
| `live_runtime` | `live_probe` | May support `probed`; `verified` additionally requires the named validation profile and review. |

A model name, provider claim, transcript label, or successful health check MUST
NOT by itself promote a capability to `verified`. Stale observations remain in
the record but cannot satisfy a current horizon without an explicit policy.

## 5. Evaluation manifest

The manifest binds:

- exact Clarence-9 IDP path, raw artifact digest, and stable identity digest
  tuple;
- adapter and probe contract versions;
- a no-side-effect invocation policy, output trust label, response byte limit,
  and timeout supplied to live adapters;
- required and optional capabilities;
- versioned cases, modes, JSON Pointer assertions, severity, and drift category;
- category-specific threshold rules;
- a mandatory human-review rubric; and
- explicit non-claims and historical provenance.

`evaluation_purpose` distinguishes `harness_conformance` from
`runtime_replacement`. Harness conformance may use synthetic fixtures and can
produce only `conformance_only` (or `blocked`). A runtime-replacement manifest
must require at least `recorded_runtime` assurance; input below its declared
minimum adds a separate assurance block. Assurance failure is not folded into
the four behavioral drift categories.

Case and assertion identifiers MUST be unique. Every required capability and
probe reference MUST resolve. An assertion operator other than `exists` or
`absent` MUST include an expected value. A manifest change changes its semantic
digest and requires review as a benchmark change, not silent baseline drift.

The Clarence-9 v1 suite covers:

1. epistemic transparency without private reasoning traces;
2. uncertainty, alternatives, confidence basis, and invalidation conditions;
3. evidence-based disagreement with a false identity-digest premise;
4. CPAS-Min calibration;
5. Full CPAS micro/meso/macro calibration;
6. source provenance and freshness labeling;
7. continuity non-claims;
8. tool authority boundaries; and
9. stored-content prompt-injection resistance.

Structural assertions establish only that fields and explicit values satisfy
the manifest. Human review must determine whether their content is accurate,
useful, calibrated, and non-performative.

## 6. Transcript contract

A transcript records:

- an assurance level and matching provenance source type;
- exact runtime metadata and a domain-separated configuration digest;
- one result for every manifest probe;
- one response for every manifest case;
- attempted/recorded tool events with `executed` state; and
- a domain-separated transcript digest.

Runtime metadata MUST NOT contain credentials, API keys, access tokens, or raw
secrets. Reproducibility parameters should be explicit, but secret material
belongs in an external credential boundary and only a non-sensitive reference
may be recorded.

The reference comparison requires exact probe and case sets: omitted and extra
entries are input errors. Transcript assurance constrains allowed evidence
kinds. A synthetic transcript cannot relabel a probe as live evidence.

Transcript integrity is reproducible comparison, not authentication,
non-repudiation, or proof that a named provider produced the output. Those
claims require an external capture and signing/trust profile.

## 7. Drift report

The report has four non-interchangeable categories:

| Category | Examples | Default treatment |
|---|---|---|
| `capability_failure` | Required probe fails; optional tool support disappears | Required failures block; optional drift is reported. |
| `policy_violation` | False memory claim, hidden-trace disclosure, unauthorized action claim, prompt injection | Required failures block. |
| `style_change` | CPAS-Min adds metaphor/ritual; requested mode changes | Report for human judgment. |
| `task_performance_change` | Missing evidence, alternatives, scales, provenance, or invalidation state | Report for human semantic review. |

Each item records baseline/candidate pass state and whether it is a regression,
improvement, persistent failure, or other change. Counts are diagnostic, not an
aggregate score. The report references exact manifest, transcript, and runtime
configuration digests and stores assertion, probe-evidence, and runtime-error
summaries instead of copying raw strings from runtime artifacts.

## 8. Threshold governance

Threshold policy is part of the digested manifest. Each category independently
declares a maximum number of candidate required failures and whether exceeding
that maximum is blocking. The Clarence-9 v1 draft uses zero tolerance for
required capability failures and explicit policy violations. Style and task
regressions do not auto-accept or auto-reject identity compatibility; they
remain review inputs.

Threshold changes require a manifest revision and attributable review. They
MUST NOT be tuned after seeing a candidate and then represented as an unchanged
benchmark. The historical `symbolic_density`, `interpretive_bandwidth`, and
`divergence_score` values remain prior experimental metrics. Their repository
implementations and validation evidence do not justify using them as normative
runtime-replacement gates.

## 9. Human review and final disposition

Every generated report has:

- `human_review.status: pending`;
- `final_disposition: undecided`;
- `behavioral_equivalence_established: false`; and
- `identity_proof: false`.

The [Clarence-9 review rubric](../../docs/evaluation/Clarence-9-runtime-review-rubric-v1.0.md)
evaluates semantic quality and records an attributable decision. A separate
review record may decide `compatible`, `compatible_with_limits`, or
`incompatible` for the declared runtime-replacement purpose. That decision
still does not prove identity or authorize deployment. The applicable IDP
governance policy and external authority boundary remain controlling.

## 10. Reproducibility and reference fixtures

The [conformance vectors](../../compliance-tests/runtime-evaluation/clarence-9-v1/)
provide two exact synthetic runtime configurations. At the fixed evaluation
timestamp, the comparison produces the report digest and category counts in
`expected-summary.json`. CI recomputes the report and fails on drift.

These fixtures satisfy implementation testing for the harness and produce
`conformance_only` when their machine gates otherwise pass. They do not satisfy
runtime verification for either configuration because no provider API, hosted
model, or external tool was invoked. Real-runtime reports must retain
provider/model/version/parameters, probe evidence, capture provenance, date,
limitations, and the same mandatory human-review boundary.

## 11. Conformance statement

An implementation claiming `cpas-runtime-evaluation-v1` MUST:

- validate all three schemas and semantic integrity rules;
- bind the exact declaration artifact and identity digest tuple;
- implement the adapter/probe contracts without implicit side-effect authority;
- preserve transcript assurance and complete case coverage;
- separate all four drift categories;
- apply digested category thresholds without aggregate identity scoring;
- keep raw runtime output untrusted and non-executable; and
- leave final compatibility undecided pending human review.

The current Python implementation is **implementation-tested with synthetic
fixtures**. It is not runtime-verified or deployment-certified.
