# Clarence-9 runtime-evaluation conformance vectors v1

This directory contains deterministic positive and negative fixtures for the
runtime-replacement evaluator:

- `manifest.json` fixes the Clarence-9 declaration artifact and stable identity
  digest, adapter/probe contracts, cases, hard gates, and human-review policy;
- `baseline-transcript.json` is a hand-authored positive control;
- `candidate-transcript.json` is a hand-authored negative control with
  intentional capability, policy, style, and task-performance drift;
- `expected-summary.json` fixes the exact report digest and expected category
  counts at `2026-08-12T22:33:00Z`.

Run the comparison:

```bash
python tools/evaluate_runtime_replacement.py \
  --manifest compliance-tests/runtime-evaluation/clarence-9-v1/manifest.json \
  --baseline compliance-tests/runtime-evaluation/clarence-9-v1/baseline-transcript.json \
  --candidate compliance-tests/runtime-evaluation/clarence-9-v1/candidate-transcript.json \
  --evaluated-at 2026-08-12T22:33:00Z
```

Both transcripts declare `synthetic_fixture`. They exercise the harness and do
not establish facts about a provider, hosted model, or deployment. The negative
fixture's reported action claims are data; the harness executes no tool events.
A passing fixture comparison is `conformance_only`, not runtime-review eligible.
The report remains `undecided` because no score is an identity proof and a real
compatibility decision requires adequately sourced runtime evidence plus human
review.
