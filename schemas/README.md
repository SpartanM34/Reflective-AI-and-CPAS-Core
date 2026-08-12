# CPAS v2 schemas

The canonical v2 JSON Schemas use JSON Schema Draft 2020-12:

- [`idp-v2.0.schema.json`](idp-v2.0.schema.json)
- [`idp-transition-v2.0.schema.json`](idp-transition-v2.0.schema.json)
- [`dka-e-v2.0.schema.json`](dka-e-v2.0.schema.json)
- [`seed-token-v2.0.schema.json`](seed-token-v2.0.schema.json)
- [`epistemic-exchange-v2.0.schema.json`](epistemic-exchange-v2.0.schema.json)

The historical IDP schema remains at
[`instances/schema/current/idp-v1.0-schema.json`](../instances/schema/current/idp-v1.0-schema.json).
Schemas validate document shape; semantic and deployment checks belong to the
reference implementation and hosting system.

New semantic digests use `rfc8785-jcs-v1` plus an artifact-specific profile.
The schemas continue to accept identifiable `cpas-canonical-json-v1` draft
records for migration. Compatibility rules and exact digest bytes are defined
by [ADR-0001](../docs/adr/0001-canonicalization-and-digest-profiles.md), not
by JSON Schema alone. Normative vectors live at
[`compliance-tests/canonicalization/cpas-canonicalization-v1.json`](../compliance-tests/canonicalization/cpas-canonicalization-v1.json).

IDP declaration governance is required by the current v2 draft. Transition
records separate deterministic change classification and attributed approvals
from authentication/authorization performed by an external trust system. See
[ADR-0002](../docs/adr/0002-declaration-governance-and-identity-evolution.md).
