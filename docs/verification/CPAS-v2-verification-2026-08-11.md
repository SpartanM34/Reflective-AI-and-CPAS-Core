# CPAS v2 modernization verification

**Date:** 2026-08-11

**Baseline commit:** `fdac6182061112b73553935661c2247403e12b3d`

**Environment:** Python 3.12.13, pytest 9.1.1, jsonschema 4.26.0,
Flask 3.1.3, requests 2.34.2.

This report records executed checks. It is implementation-test evidence, not a
runtime capability certification or production security assessment.

## Full test suite

Command:

```bash
pytest -q --basetemp=/workspace/scratch/c2be0d453efb/pytest-temp-parent/final-run
```

Result:

```text
.....................................................                    [100%]
53 passed
```

The run includes 31 CPAS v2 tests and 22 legacy tests. Nine warnings remain in
legacy modules: five from `cpas_autogen/dka_persistence.py`, two from
`cpas_autogen/message_logger.py`, and two from `tools/record_wonder.py`, all for
deprecated `datetime.utcnow()` use. They are documented but not changed in this
modernization branch to avoid unrelated v1.1 behavior changes.

The v2 tests exercise:

- Clarence-9 IDP schema and identity-digest consistency;
- runtime rebinding without stable identity drift;
- conservative IDP v1 migration and capability negotiation;
- duplicate-key rejection and canonical digests;
- SeedToken integrity, capability digest, expiry, parent checks, and HMAC;
- DKA schema/integrity, staleness, triggers, revisions, local CAS, corruption
  detection, branching, conservative merge, access defaults, and rehydration
  budgets;
- EEP schema, explicit consensus, agreement-without-consensus, and four-form
  continuity reports.

## Legacy IDP migration sweep

The migration utility was run in `--dry-run` mode against `agents/json` at the
baseline revision with a fixed migration timestamp. It found, migrated, and
schema/semantic-validated **28 of 28 discovered IDP v1 documents**. It wrote no
output during this check.

## Schema and artifact checks

JSON Schema Draft 2020-12 meta-schema checks and instance validation passed for:

- `instances/current/Clarence-9-v2.0.json` against IDP v2;
- `examples/v2/dka-e-v2.example.json` against DKA-E v2;
- `examples/v2/seed-token-v2.example.json` against SeedToken v2;
- `examples/v2/epistemic-exchange-v2.example.json` against EEP v2.

Reference-package and migration modules passed `python -m compileall`. Local
Markdown targets in the modernization index, v2 specifications, audit,
migration guide, and documentation index resolved. `git diff --check` reported
no whitespace errors.

## Deliberately unverified

- No provider/model runtime was bound to Clarence-9 v2.
- No hosted memory, MCP server, vector database, Git backend, or external DKA-E
  service was deployed.
- No public-key signature, authorization system, encryption, distributed
  transaction, disaster recovery, or privacy certification was tested.
- Current platform documentation was researched, but feature availability for a
  particular account/deployment was not inferred.
- No performance claim was made for reflective reasoning, durable updates, or
  model inference.

These limits are architectural facts, not pending test results.
