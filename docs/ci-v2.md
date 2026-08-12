# CPAS v2 continuous integration

The CPAS v2 CI foundation protects the merged draft's executable contracts. It
does not certify a model runtime, production storage system, security control,
or the semantic truth of an epistemic claim.

## Local validation

Install the focused dependencies and run the same high-level checks used by CI:

```bash
python -m pip install -r requirements-v2.txt
python tools/validate_cpas_v2.py
node tools/verify_canonicalization_vectors.mjs
python -m pytest -q
python -m compileall -q cpas tools/validate_cpas_v2.py tools/verify_canonicalization_vectors.py migrations/migrate_idp_v1_to_v2.py
git diff --check
```

For machine-readable validation output:

```bash
python tools/validate_cpas_v2.py --json
```

## Repository validation contract

`tools/validate_cpas_v2.py` performs these checks:

- Draft 2020-12 meta-schema and example-instance validation for IDP, DKA-E,
  SeedToken, and EEP;
- semantic IDP identity-digest consistency;
- DKA-E content integrity;
- SeedToken integrity, capability-profile digest, static documentation-vector
  time checks, and HMAC verification with the intentionally public test key;
- cross-file provenance and state-reference digests;
- EEP identity/DKA references;
- RFC 8785/JCS canonical bytes, legacy compatibility, domain-separated digests,
  and negative parser/data-model vectors in Python;
- all discovered legacy IDP v1 migrations using a fixed test timestamp;
- local links in modernization documents;
- strict JSON loading through the reference implementation, including duplicate
  key and non-finite number rejection.

The static SeedToken vector is evaluated at `2026-08-12T00:00:00Z`. This tests
the published bytes independently of wall-clock expiry. Deployments must still
validate tokens using their current trusted clock.

## GitHub Actions workflow

`.github/workflows/cpas-v2-ci.yml` runs on pull requests to `main`, pushes to
`main`, and manual dispatch. It contains:

- the complete test suite on Python 3.11, 3.12, and 3.13;
- repository invariants and compile checks on Python 3.12;
- independent execution of the same canonicalization/digest vectors on Node.js
  24;
- changed-diff whitespace validation;
- read-only `contents` permission, no persisted checkout credential, bounded
  timeouts, and concurrency cancellation.

GitHub recommends `setup-python` for consistent Python selection in Actions.
The workflow pins immutable action commits rather than floating tags:

- `actions/checkout` `3d3c42e5...` — release v7.0.1;
- `actions/setup-python` `5fda3b95...` — release v7.0.0.
- `actions/setup-node` `82076278...` — release v7.0.0.

Primary references, checked 2026-08-12:

- [GitHub: Building and testing Python](https://docs.github.com/actions/guides/building-and-testing-python)
- [`actions/checkout` releases](https://github.com/actions/checkout/releases)
- [`actions/setup-python` releases](https://github.com/actions/setup-python/releases)
- [`actions/setup-node` releases](https://github.com/actions/setup-node/releases)
- [GitHub: `GITHUB_TOKEN` permissions](https://docs.github.com/actions/reference/authentication-in-a-workflow)

## What a green check means

A green workflow establishes that the checked-out repository is internally
consistent under the stated Python/dependency matrix and that its tests pass. It
does **not** establish:

- canonicalization behavior beyond the published Python/Node vectors or on an
  untested implementation;
- identity authentication, authorization, or non-repudiation;
- production DKA-E durability, privacy, or access control;
- runtime/model compatibility or behavioral continuity;
- independent deployment certification.

Those remain separate workstreams under tracking issue #95.
