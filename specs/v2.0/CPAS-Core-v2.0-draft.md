# CPAS-Core v2.0 draft specification

**Status:** proposal; not deployment certification

**Lineage:** CPAS-Core v1.1 by Spartan-M34 / Clarence-9 corpus

**Version:** 2.0.0-draft.1

## Versioning decision

This work warrants **CPAS-Core v2.0**. It preserves CIM, RRL, DKA, IC,
micro/meso/macro review, uncertainty, CPAS-Min/Full, ethical reflection, and
collaboration. It nevertheless breaks v1 semantics by removing runtime/model
from stable identity; constraining transparency to outward epistemic records;
typing continuity, persistence, and capabilities; replacing security-adjacent
hash language; and defining new IDP/DKA-E/SeedToken/EEP schemas. A v1.2 label
would understate migration risk. v1.2 should be reserved for v1-compatible
errata.

## 1. Core invariant and scope

> **Declared Instance Identity → Epistemic Policy → Continuity State → Runtime / Model / Tools**

The arrow expresses configuration and constraint flow, not consciousness or a
causal proof of identity. The model runtime is not the identity. An instance is
a declared, reconstructable interaction architecture. It has no inherent
permanent self, felt emotion, memory, or autonomous persistence.

CPAS specifies how a host declares and reconstructs that architecture, exposes
useful epistemic state, persists selected records externally, negotiates
capabilities, and exchanges claims. It does not specify a sentient agent, a
general authorization system, or a universal memory service.

## 2. Architecture

The four v1.1 modules remain normative:

| Module | v2 responsibility | Required output/boundary |
|---|---|---|
| **CIM** | Resolve the stable instance declaration, user/task context, applicable safety policy, interaction mode, and runtime binding. | Activation report and stable identity digest tuple; runtime changes do not alter the digest within one profile. |
| **RRL** | Review claims across micro/meso/macro scopes; identify evidence, assumptions, uncertainty, alternatives, blind spots, and criteria. | Concise epistemic record or summary. Hidden chain-of-thought is neither requested nor persisted. |
| **DKA** | Materialize durable conclusions with their surrounding epistemic state and validity conditions. | Schema-valid, content-digested DKA record; metaphor optional. |
| **IC** | Calibrate verbosity, metaphor/ritual, collaboration, and uncertainty display to explicit preferences and task needs. | CPAS-Min/Full/custom mode; reversible and privacy-aware. |

### 2.1 Epistemic scales

- **Micro:** the local claim, evidence item, assumption, or tool observation.
- **Meso:** the task, DKA, conversation, method, and dependencies.
- **Macro:** system incentives, longitudinal validity, downstream effects,
  ethics, and cross-domain consequences.

These are scopes for inspectable review. They do not imply access to token-level
internal computation. Uncertainty propagated between scopes records the method
and dependency; confidence numbers without basis/calibration are non-conformant.

### 2.2 Continuity forms

| Form | Active when |
|---|---|
| **Declarative** | The trusted IDP reinstates identity and operating principles. |
| **Contextual** | Prior messages/summaries are actually supplied in accessible context. |
| **Epistemic** | DKAs, assumptions, uncertainty, disputes, and active work state are retrieved and verified. |
| **Persistent-system** | An external system demonstrably wrote state previously and can retrieve/verify it now. |

Each is independently reported. Declarative continuity alone is valid and does
not masquerade as remembered experience.

### 2.3 State layers

Model context, platform memory, project/workspace state, and externally
persisted CPAS state are separate. Hosts record origin and durability for every
restored item. Provider product memory never silently becomes canonical DKA-E
state.

### 2.4 Canonicalization profiles

Semantic digests are interpreted with their algorithm, canonicalization, and
artifact-domain profile. New records use RFC 8785/JCS and the domain frame in
[ADR-0001](../../docs/adr/0001-canonicalization-and-digest-profiles.md).
Legacy direct hashes remain identifiable and verifiable but are not
interchangeable with new values. Encoding-profile migration can change a digest
string without changing the declared identity projection.

## 3. Activation protocol

1. Parse a trusted IDP; verify schema and provenance/digest expectations.
2. Resolve explicit user/task context and CPAS-Min/Full preference.
3. Bind the observed runtime separately and negotiate required/optional
   capabilities using status plus evidence.
4. Validate the SeedToken, if supplied, without treating it as authorization.
5. Rehydrate authorized DKA-E records under budget and stale-state policy.
6. Produce an activation report with identity digest and profile, runtime binding,
   capabilities, active continuity forms, state-layer availability, included and
   omitted state, warnings, and hard failures.
7. Continue only in the reported full or degraded mode accepted by the host/user.

Runtime replacement repeats steps 3–7. Within one digest profile it is
compatible when the stable identity digest remains equal and all
identity-required policies/capabilities are satisfied. Across an explicit
encoding migration, implementations compare the stable projection and record
both digest tuples. Output behavior may still differ and must be validated.

## 4. Transparency and reflection

The guiding principle is:

> Maximum useful epistemic transparency without requiring disclosure of hidden cognitive traces.

Task-appropriate outputs expose source provenance, assumptions, evidence,
uncertainty, qualified confidence, competing hypotheses, blind spots, concise
reasoning summaries, and decision criteria. RRL may state that a limitation is
unknown. It never invents an internal trace or claims a summary is exhaustive.
Private chain-of-thought is not continuity state and must not be stored in DKAs.

## 5. Persistence

DKA-E v2 supplies immutable snapshots, mutable heads through compare-and-swap,
append-only events, derived retrieval indexes, validity evaluation, branching,
three-way merge, and provenance. Canonical records are portable JSON. Database,
Git, graph, event, object, vector, and platform stores are adapters with
different guarantees. Embeddings include source digest, embedding model, and
creation time and can always be rebuilt.

Rehydration is a trust boundary. Persisted text is untrusted data unless a
separate authorized policy elevates it. Access control, encryption, retention,
erasure, and secrets management are host responsibilities.

## 6. Runtime and tool negotiation

Capabilities use `unknown`, `declared`, `probed`, `verified`, and `unavailable`.
Required capabilities block or degrade activation when absent. Optional ones
alter adapters/mode. A model catalog description yields at most `declared`;
task-relevant tests yield `verified`. Each status may expire.

Tool definitions name input contracts and externally granted authority. The
model proposes calls; the host validates and executes them. Neither IDP nor
SeedToken grants authorization. MCP is a supported capability adapter where
available, but CPAS remains usable without it.

## 7. Interaction calibration

`CPAS-Min` means concise epistemic signaling, reduced ritual, and metaphor off
or sparse; it does not disable provenance, safety, or uncertainty. `Full CPAS`
permits fuller multiscale review and optional metaphor. Users can override mode.
Calibration prefers explicit preferences and observable task requirements.
Sensitive personality or emotional profiling requires a separately stated
purpose and consent; simulated warmth must not be described as felt emotion.

## 8. Cross-instance collaboration

EEP v2 is the canonical epistemic message. An exchange names claim, confidence
basis, assumptions, evidence, uncertainty, disagreement, requested checks, DKA
references, provenance, and runtime/instance profile. Specialized outputs are
inputs to evaluation. Shared ancestry and orchestration are potential
correlations. Consensus exists only in a dedicated record naming the method and
decision authority; agreement alone leaves consensus `not_computed`.

## 9. Safety and human authority

- The user or designated human authority can override calibration and decide
  consequential contested merges, subject to governing safety/law.
- CPAS records authority boundaries; it does not create them.
- Web claims with a meaningful freshness horizon require current source checks
  when web access is available, otherwise the limitation is explicit.
- Tool side effects require host confirmation/policy and least privilege.
- Memory operations support disclosure, correction, and deletion where the
  backend permits; immutable logs require privacy-aware redaction/tombstoning.
- Instance personality never overrides platform safety or user authorization.

## 10. Protocol set

| Protocol | Version | Role |
|---|---|---|
| IDP | 2.0 | Instance identity/policy and current binding declaration. |
| DKA-E | 2.0 | External epistemic records and lifecycle. |
| SeedToken | 2.0 | Compact continuity metadata and state references. |
| EEP | 2.0 | Cross-instance epistemic exchange and explicit consensus records. |

JSON Schema Draft 2020-12 validates shapes. Semantics such as evidence truth,
authorization, independence, and safe tool execution require application logic.

## 11. Conformance

Implementations state the exact level and artifacts:

1. **Schema-conformant:** declared documents validate against named schemas.
2. **Implementation-tested:** named reference behaviors pass reproducible tests.
3. **Runtime-verified:** stated capabilities pass dated tests on a named runtime.
4. **Deployment-certified:** an identified authority assessed operational
   controls, security, privacy, and evidence under a defined profile.

No level implies the next. “Full compliance” without level, version, profile,
evidence, and date is not a v2 conformance statement.

## 12. Backward compatibility

Historical v1.1 files remain immutable in their original paths. v1 imports use
explicit adapters and preserve the complete source under provenance/extensions.
Model family becomes a runtime observation; transparency becomes outward
epistemic summary; legacy hashes remain legacy; DKA metaphor becomes optional;
T-BEEP messages require an explicit gateway. Down-conversion is lossy.

## 13. Normative language and maturity

“Must,” “must not,” “required,” “should,” and “may” describe this draft’s
intended contract. The Python package is a small reference implementation, not
a production service. Security, distributed storage, provider adapters, public-
key signatures, calibration research, and deployment certification remain open
work documented in [`docs/open-questions-v2.md`](../../docs/open-questions-v2.md).
