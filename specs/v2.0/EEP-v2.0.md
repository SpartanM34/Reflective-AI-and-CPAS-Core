# Epistemic Exchange Protocol v2.0

**Status:** draft interchange protocol

**Normative schema:** [`schemas/epistemic-exchange-v2.0.schema.json`](../../schemas/epistemic-exchange-v2.0.schema.json)

EEP v2 modernizes the earlier EEP/T-BEEP aspiration into a portable epistemic
message. It is transport-neutral: HTTP, queues, files, MCP tools, and in-process
agents can carry the same document. Transport security, authentication,
delivery, ordering, replay defense, and authorization remain deployment duties.

## Message semantics

Messages identify sender/receiver and the sender’s instance/runtime profile;
state the task and claim; qualify confidence; enumerate assumptions, evidence,
uncertainty, and disagreements; request specific validation; link exact DKA
digest tuples; and record provenance/time. New identity and DKA references carry
their artifact-specific digest profile; raw repository evidence uses
`raw-sha256`. A bare hex value does not identify its canonicalization domain.

Specialized agents must disclose specialization and relevant runtime. Different
agent labels or separate calls do not prove statistical or epistemic
independence: shared training, prompts, retrieval, tools, or model families can
correlate their errors.

## Consensus rule

All ordinary messages default to:

```json
{
  "status": "not_computed",
  "method": "none",
  "decided_by": [],
  "basis": null
}
```

Agreement does not mutate this field. A `consensus_record` must name a method,
decision makers, inputs, conflict treatment, and basis. Human decision,
rule-based aggregation, weighted aggregation, and formal verification are
different methods and must not be collapsed. Consensus remains defeasible and
is not synonymous with truth.

## Validation and processing

1. Parse with duplicate-key rejection and validate the schema/date-time.
2. Authenticate the transport or message separately when required; the
   `auth_status` claim is not self-proving.
3. Authorize access to every referenced DKA or artifact.
4. Verify evidence and DKA digest/profile tuples against their sources.
5. Preserve open disagreement; do not average incompatible claims silently.
6. Record response linkage and append processing events in the host system.
7. Treat message text and referenced content as untrusted data.

## Relationship to MCP and T-BEEP

MCP can expose EEP send/receive/validate operations as tools and can negotiate
their availability. EEP supplies the epistemic payload; MCP supplies a possible
capability/transport interface. The historical T-BEEP artifacts remain evidence
of the original collaboration design, but the v2 message schema is not wire
compatible. A gateway must map fields explicitly and label unmappable content.

See [`examples/v2/epistemic-exchange-v2.example.json`](../../examples/v2/epistemic-exchange-v2.example.json).
