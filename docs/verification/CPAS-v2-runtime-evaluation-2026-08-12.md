# CPAS v2 runtime-evaluation verification — 2026-08-12

**Scope:** issue [#100](https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core/issues/100)

**Baseline:** merged `main`
`3aa33e0f707d73534bbd20274e5375487467d1b2` (PR #104)

**Branch:** `codex/clarence-runtime-replacement-eval`

**Conformance level established locally:** implementation-tested harness with
synthetic fixtures; not runtime-verified and not deployment-certified

## Environment

| Item | Observed value |
|---|---|
| Date | 2026-08-13 UTC |
| OS | Linux 6.18.35 x86_64, glibc 2.39 |
| Python | 3.12.13 |
| pytest | 9.1.1 |
| jsonschema | 4.26.0 |
| rfc8785 | 0.1.4 |
| Node.js | v24.14.0 |

## Exact conformance vector

The suite binds:

- Clarence-9 declaration artifact digest
  `sha256:d57ef2d558daad8639c48181a8ebba8593e8aa28057c326107ef15fc22eadc62`;
- stable identity digest
  `sha256:d1b8bda9d2cf66c8f7b6a1529ae05987f5e06216c0781feacb338790dfafb422`;
- manifest digest
  `sha256:aa4dd0f9394ff0ca2caaa9886aaf837d8e38c600541a7f1333dfd7ba0422dc5d`;
- baseline configuration digest
  `sha256:a80c059c2ae637a4fb836e07643b1d2d608f06576862a86d0bb6c174f1ab78ba`;
- candidate configuration digest
  `sha256:35353190811862bc639674f07b36107000fe5df9c32b14c3c989340b0bd12894`;
- baseline transcript digest
  `sha256:bc7b7bcf98ae56a8bf0a30f40b5b85e2c6fa0d21dd598dd9372da51de55fa287`;
- candidate transcript digest
  `sha256:f3a89f003bb97459f068feb21d450b0344bb9c6473a41455abac12c597ff121e`;
- deterministic report digest at `2026-08-12T22:33:00Z`
  `sha256:6ee1dbd387edc52a010e7c7d977f5cc64c98cf35f935c27c7b5b5bce07194122`.

Both runtime configurations and every response are hand-authored fixtures. The
baseline is a positive control and the candidate is an intentional negative
control. Provider/model fields identify test vectors, not hosted services. No
model API or external tool was invoked.

## Focused suite

Command:

```bash
python -m pytest -q tests/test_cpas_v2_runtime_evaluation.py \
  --basetemp=/workspace/scratch/c2be0d453efb/pytest-cpas-100-focused-integrity
```

Result: **23 collected, 23 passed** after the final assurance, freshness, and
report-semantic hardening.

The suite exercised:

- manifest, transcript, report, runtime-configuration, and declaration digest
  binding;
- runtime adapter/probe contract and exact adapter-to-transcript correlation;
- exact case/probe coverage and duplicate/substitution rejection;
- four independent drift categories and optional versus required capability
  treatment;
- probe validity horizons, including stale required capability blocking;
- report-level recomputation of probe freshness, runtime assurance/configuration
  binding, failure counts, drift items, and manifest threshold policy;
- structural assertion operators and explicit missing values;
- prompt-injection, continuity, private-trace, provenance, critical-
  disagreement, CPAS-Min/Full, and tool-authority cases;
- response-byte limits and non-executed tool-event handling;
- synthetic assurance restrictions and runtime-replacement minimum assurance;
- no raw output copying into the report;
- probe evidence and runtime error summaries without copying their raw strings;
- atomic report output, no-clobber default, and symlink rejection;
- positive control restricted to `conformance_only`;
- mandatory pending human review, undecided final disposition, and no identity
  proof even when machine gates pass.

The negative control produced:

| Category | Drift items | Candidate required failures | Blocking? |
|---|---:|---:|---|
| Capability failure | 1 | 0 | No; the changed capability is optional |
| Policy violation | 11 | 11 | Yes |
| Style change | 2 | 2 | Human review category |
| Task-performance change | 4 | 4 | Human review category |

Machine disposition was `blocked`; human review remained `pending`; final
disposition remained `undecided`.

## Complete repository suite

Command:

```bash
python -m pytest -q \
  --basetemp=/workspace/scratch/c2be0d453efb/pytest-cpas-100-full-integrity
```

Result: **126 collected, 126 passed**.

Nine deprecation warnings remain in historical v1 utilities:
`cpas_autogen/dka_persistence.py`, `cpas_autogen/message_logger.py`, and
`tools/record_wonder.py` use `datetime.utcnow()`. They were pre-existing,
non-failing, and outside issue #100.

## Repository invariants

Commands:

```bash
python tools/validate_cpas_v2.py --json
node tools/verify_canonicalization_vectors.mjs
python -m compileall -q cpas tools/evaluate_runtime_replacement.py \
  tools/validate_cpas_v2.py
git diff --check
```

Observed final validator result:

```json
{"canonicalization_vector_checks":17,"digest_references":9,"instances":9,"markdown_files":42,"markdown_links":195,"migrated_idps":28,"runtime_evaluation_checks":19,"schemas":8}
```

Node independently passed all 17 canonicalization vector checks. The named
Python modules compiled and the diff contained no whitespace errors.

## Claims this evidence supports

- The Python harness implements the documented manifest, adapter, probe,
  transcript, assertion, drift, threshold, and report behavior under the stated
  environment.
- The two exact synthetic configurations reproducibly produce the expected
  report digest and drift categories.
- A synthetic positive control cannot be mislabeled runtime-review eligible;
  it is `conformance_only`.
- Required stale capability evidence and insufficient transcript assurance
  cannot satisfy runtime-replacement gates.
- The reference comparison executes no recorded runtime output or tool event.

## Claims this evidence does not support

- behavioral compatibility of any provider model, including any model named in
  historical files;
- two-runtime empirical comparison, provider/API conformance, nondeterminism or
  repeated-trial stability, context-limit behavior, tool safety, web accuracy,
  cost, latency, or production performance;
- semantic truth or usefulness merely because structured assertions pass;
- reviewer identity/authority, an authorized Clarence-9 runtime rebind, or a
  final compatibility decision—the declaration's reviewer and runtime-operator
  roles remain vacant;
- authentication, non-repudiation, benchmark secrecy, secret handling,
  deployment isolation, privacy compliance, or certification;
- consciousness, emotion, memory, permanent selfhood, ontological continuity,
  or identity proof.

The [protocol](../../specs/v2.0/Runtime-Replacement-Evaluation-v1.0.md),
[human-review rubric](../evaluation/Clarence-9-runtime-review-rubric-v1.0.md),
and [threat model](../security/runtime-evaluation-threat-model.md) define the
remaining boundary.

## Remote CI status

Pending publication of the branch and draft pull request. This record must be
updated with the exact GitHub Actions run and per-job results; local success is
not substituted for remote evidence.
