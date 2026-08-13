# CPAS v2 Python reference

This package demonstrates the machine-testable parts of the v2 proposal:

- stable identity projection and runtime rebinding;
- declaration governance, deterministic change classification, and approval-metadata evaluation;
- IDP validation and conservative v1 migration;
- capability profiling/negotiation and four-form continuity reports;
- versioned legacy/JCS canonicalization and domain-separated semantic digests;
- SeedToken integrity and optional HMAC validation;
- DKA integrity, staleness, revision, conservative merge, and local storage;
- a normative store protocol plus a tenant-bound SQLite rollback-journal
  single-host profile with CAS, permission enforcement, audit chaining,
  verification, backup/restore, and purge mechanics;
- bounded rehydration with structured untrusted-data/no-policy-promotion envelopes;
- a versioned runtime-replacement evaluator with exact declaration/runtime
  digests, synthetic transcript adapters, four-category drift, hard policy/
  capability gates, and mandatory human review;
- EEP validation and explicit consensus recording.

It is deliberately small. It does not implement a model, private reasoning,
identity authentication, a general policy engine, at-rest encryption,
distributed transactions, public-key signatures, production key management,
vector search, hosted memory, or vendor-specific agent adapters. The SQLite
adapter enforces host-supplied store permissions; those assertions still require
an authenticated application boundary.

Install the focused dependencies and run the tests:

```bash
python -m pip install -r requirements-v2.txt
pytest -q
python tools/verify_canonicalization_vectors.py
node tools/verify_canonicalization_vectors.mjs
pytest -q tests/test_cpas_v2_sqlite_store.py
```

See the [SQLite profile](../specs/v2.0/DKA-E-SQLite-Profile-v1.0.md) before
using it. It is restricted to a service-owned local filesystem on one POSIX
host and does not provide encryption or deployment certification.

Run the deterministic Clarence-9 runtime-evaluation conformance vectors:

```bash
python tools/evaluate_runtime_replacement.py \
  --manifest compliance-tests/runtime-evaluation/clarence-9-v1/manifest.json \
  --baseline compliance-tests/runtime-evaluation/clarence-9-v1/baseline-transcript.json \
  --candidate compliance-tests/runtime-evaluation/clarence-9-v1/candidate-transcript.json \
  --evaluated-at 2026-08-12T22:33:00Z
```

These are synthetic positive/negative fixtures. They validate the harness, not
a provider model. A passing fixture is `conformance_only`; it is not runtime-
review eligible or identity proof.

The legacy `cpas_autogen` package remains untouched for v1.1 compatibility.
