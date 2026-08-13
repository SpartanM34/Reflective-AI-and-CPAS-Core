# Runtime-evaluation threat model

**Profile:** `cpas-runtime-evaluation-v1`

**Security status:** design and implementation-test artifact, not a deployment
assessment

## Assets and boundaries

Protected assets include the exact declaration/manifest, runtime configuration,
probe evidence, transcript content, report integrity, secrets available to a
live adapter, and the validity of human review. The reference evaluator accepts
runtime output as untrusted data and has no tool-execution authority.

Domain-separated digests detect accidental or unreviewed artifact substitution.
They do not authenticate a provider, runtime, operator, or reviewer and do not
prevent a privileged actor from rewriting an artifact and recomputing a digest.

## Threats and controls

| Threat | Reference control | Residual risk |
|---|---|---|
| Prompt injection in restored/file/web/runtime output | Outputs are data; assertions inspect structure; tool events are never executed. | A live adapter or human reviewer may still mishandle raw content outside the harness. |
| Tool or network side effect during evaluation | Manifest requires disabled tools and forbidden external side effects; any recorded `executed: true` adds a policy failure. | The harness cannot attest that a remote provider made no hidden side effect. Live adapters require sandboxing and host logs. |
| Runtime/configuration substitution | Exact configuration and transcript digests are referenced in the report. | Unkeyed digests are not authentication. |
| Selective omission or extra easy cases | Exact probe/case set equality is required. | A biased manifest can still omit important behavior. |
| Benchmark gaming | Versioned hidden or rotating suites may supplement the public suite; human review inspects raw outputs. | Public fixtures are inherently gameable; hidden tests introduce governance and reproducibility costs. |
| Aggregate-score laundering | No aggregate score is computed; four categories remain separate; human review is mandatory. | Reviewers can still overemphasize counts unless the rubric is followed. |
| Semantic field stuffing | Machine checks are explicitly structural; the rubric evaluates usefulness and truth. | Human review is fallible and may be correlated with runtime outputs. |
| Stale capability evidence | Probes declare dates, evidence kinds, and validity horizons. | The v1 reference harness records horizons but deployment scheduling remains external. |
| Synthetic evidence relabeled as live | Transcript assurance must equal provenance source type; synthetic transcripts may use only synthetic probe evidence. | A dishonest actor can forge metadata without an authenticated capture profile. |
| Secret leakage into transcripts/reports | Reports summarize assertion values, probe evidence, and runtime error messages instead of copying them. | Raw transcript files and exact runtime metadata can contain sensitive material and need external access/retention controls; credentials must never be placed in runtime parameters. |
| Oversized or malformed output | JSON object contract and byte budget; failures remain explicit. | Live adapters also need transport/body/time limits before parsing. |
| Reviewer/authority spoofing | Machine report never finalizes compatibility; rubric requires authority reference. | CPAS v2 currently has no active authentication/signature profile for reviewer records. |
| Correlated baseline/judge error | No automatic semantic judge is treated as final; baseline and candidate ancestry should be disclosed. | Human and model reviewers may share blind spots; independent expertise may be needed. |

## Deployment requirements not implemented here

A live-runtime adapter needs, at minimum: credential isolation, egress/tool
allowlists, request/response size and timeout enforcement, secret redaction,
transcript access control and retention, attributable configuration capture,
provider/version change monitoring, reviewer authentication, and incident
handling. Passing the fixture suite supplies none of these controls.
