# CPAS v2 Python reference

This package demonstrates the machine-testable parts of the v2 proposal:

- stable identity projection and runtime rebinding;
- declaration governance, deterministic change classification, and approval-metadata evaluation;
- IDP validation and conservative v1 migration;
- capability profiling/negotiation and four-form continuity reports;
- versioned legacy/JCS canonicalization and domain-separated semantic digests;
- SeedToken integrity and optional HMAC validation;
- DKA integrity, staleness, revision, conservative merge, and local storage;
- bounded rehydration with untrusted-data labeling;
- EEP validation and explicit consensus recording.

It is deliberately small. It does not implement a model, private reasoning,
identity authentication, authorization, encryption, distributed transactions,
public-key signatures, production key management, vector search, hosted memory,
or vendor-specific agent adapters.

Install the focused dependencies and run the tests:

```bash
python -m pip install -r requirements-v2.txt
pytest -q
python tools/verify_canonicalization_vectors.py
node tools/verify_canonicalization_vectors.mjs
```

The legacy `cpas_autogen` package remains untouched for v1.1 compatibility.
