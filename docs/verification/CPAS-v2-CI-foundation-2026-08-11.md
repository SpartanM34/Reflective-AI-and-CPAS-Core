# CPAS v2 CI foundation verification

**Date:** 2026-08-11

**Baseline:** merged `main` commit
`a24c767dfb2aecb2e305674664e1fb8152c1217e`

**Scope:** issue #96, local pre-publication verification. GitHub-hosted matrix
results belong to the pull request checks and are not claimed in this file.

## Test suite

Executed under Python 3.12.13 with the focused `requirements-v2.txt`
environment:

```bash
pytest -q --basetemp=/workspace/scratch/c2be0d453efb/pytest-temp-parent/ci-full
```

Result:

```text
.........................................................                [100%]
57 passed
```

This is 53 tests inherited from modernization PR #94 plus four repository-
validation tests. Nine pre-existing `datetime.utcnow()` deprecation warnings
remain in legacy modules and are unchanged.

## Repository validator

Command:

```bash
python tools/validate_cpas_v2.py --json
```

Result:

```json
{"digest_references": 8, "instances": 4, "markdown_files": 22, "markdown_links": 80, "migrated_idps": 28, "schemas": 4}
```

The validator first failed against the merged baseline because the DKA-E and
EEP examples referenced the architecture audit's digest from before a Markdown
whitespace correction. The repair performed in this branch:

1. updates the audit provenance digest;
2. reseals the DKA-E example;
3. updates EEP and SeedToken DKA references;
4. recomputes SeedToken integrity and the documentation HMAC.

The validator then passed, demonstrating that it detects cross-file provenance
drift that schema validation and internal content digests alone do not detect.

## Additional checks

- `compileall` passed for `cpas`, the repository validator, and IDP migration
  utility.
- `git diff --check` passed.
- The workflow parsed as YAML and contains the expected `tests` and
  `repository-invariants` jobs.
- Action release refs were read directly from their Git repositories:
  `actions/checkout` v7.0.1 resolves to `3d3c42e5...`; `actions/setup-python`
  v7.0.0 resolves to `5fda3b95...`. The workflow pins those full SHAs.

## Evidence boundary

This verification establishes local repository consistency and test behavior.
It does not establish that GitHub-hosted jobs have run, that another language
produces identical canonical bytes, or that any runtime/storage deployment is
certified. Those are separate evidence requirements.
