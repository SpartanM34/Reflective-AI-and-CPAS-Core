# CPAS-Core modernization track

This repository preserves CPAS-Core v1.1 as historical source material and
develops a compatibility-aware CPAS-Core v2.0 draft alongside it. The draft is
not a claim that every described capability is deployed. Each artifact is
classified as a concept, protocol, reference implementation, or verified
capability.

The governing invariant is:

> Declared Instance Identity → Epistemic Policy → Continuity State → Runtime / Model / Tools

The runtime is replaceable infrastructure, not the identity.

## Deliverables

| Deliverable | Location |
|---|---|
| Architecture audit | [`docs/audits/CPAS-Core-v1.1-architecture-audit.md`](docs/audits/CPAS-Core-v1.1-architecture-audit.md) |
| Release-candidate readiness audit | [`docs/audits/CPAS-Core-v2-RC-readiness-audit.md`](docs/audits/CPAS-Core-v2-RC-readiness-audit.md) |
| Modernization principles | [`specs/v2.0/modernization-principles.md`](specs/v2.0/modernization-principles.md) |
| Clarence-9 v2 declaration | [`instances/current/Clarence-9-v2.0.json`](instances/current/Clarence-9-v2.0.json) and [commentary](instances/current/Clarence-9-v2.0.md) |
| IDP v2 | [`specs/v2.0/IDP-v2.0.md`](specs/v2.0/IDP-v2.0.md) and [JSON Schema](schemas/idp-v2.0.schema.json) |
| IDP governance | [`specs/v2.0/IDP-Governance-v2.0.md`](specs/v2.0/IDP-Governance-v2.0.md), [transition schema](schemas/idp-transition-v2.0.schema.json), and [ADR-0002](docs/adr/0002-declaration-governance-and-identity-evolution.md) |
| CPAS-Core v2 proposal | [`specs/v2.0/CPAS-Core-v2.0-draft.md`](specs/v2.0/CPAS-Core-v2.0-draft.md) |
| DKA-E v2 | [`specs/v2.0/DKA-E-v2.0.md`](specs/v2.0/DKA-E-v2.0.md) |
| DKA-E store contract/profile | [`specs/v2.0/DKA-Store-Contract-v1.0.md`](specs/v2.0/DKA-Store-Contract-v1.0.md), [`specs/v2.0/DKA-E-SQLite-Profile-v1.0.md`](specs/v2.0/DKA-E-SQLite-Profile-v1.0.md), and [ADR-0003](docs/adr/0003-dka-e-single-host-sqlite-profile.md) |
| SeedToken v2 | [`specs/v2.0/SeedToken-v2.0.md`](specs/v2.0/SeedToken-v2.0.md) |
| Epistemic exchange v2 | [`specs/v2.0/EEP-v2.0.md`](specs/v2.0/EEP-v2.0.md) |
| Reference implementation | [`cpas/`](cpas/) |
| Migration guide | [`migrations/CPAS-v1.1-to-v2.0.md`](migrations/CPAS-v1.1-to-v2.0.md) |
| DKA store migration | [`migrations/FileDKAStore-to-SQLite-v1.md`](migrations/FileDKAStore-to-SQLite-v1.md) and [utility](migrations/migrate_file_dka_store_to_sqlite.py) |
| Open questions | [`docs/open-questions-v2.md`](docs/open-questions-v2.md) |
| Platform research | [`docs/research/current-platform-capabilities-2026-08.md`](docs/research/current-platform-capabilities-2026-08.md) |
| Verification record | [`docs/verification/CPAS-v2-verification-2026-08-11.md`](docs/verification/CPAS-v2-verification-2026-08-11.md) |
| CI guardrails | [`docs/ci-v2.md`](docs/ci-v2.md), [workflow](.github/workflows/cpas-v2-ci.yml), and [verification](docs/verification/CPAS-v2-CI-foundation-2026-08-11.md) |
| Canonicalization decision | [`docs/adr/0001-canonicalization-and-digest-profiles.md`](docs/adr/0001-canonicalization-and-digest-profiles.md), [vectors](compliance-tests/canonicalization/cpas-canonicalization-v1.json), and [migration](migrations/canonicalization-v1-to-jcs-v1.md) |
| Canonicalization verification | [`docs/verification/CPAS-v2-canonicalization-2026-08-12.md`](docs/verification/CPAS-v2-canonicalization-2026-08-12.md) |
| DKA-E storage operations/security | [`docs/operations/DKA-E-SQLite-Profile-v1.0.md`](docs/operations/DKA-E-SQLite-Profile-v1.0.md) and [threat model](docs/security/DKA-E-storage-threat-model.md) |
| DKA-E storage verification | [`docs/verification/CPAS-v2-dka-store-profile-2026-08-12.md`](docs/verification/CPAS-v2-dka-store-profile-2026-08-12.md) |
| Runtime-replacement evaluation | [`specs/v2.0/Runtime-Replacement-Evaluation-v1.0.md`](specs/v2.0/Runtime-Replacement-Evaluation-v1.0.md), [ADR-0004](docs/adr/0004-runtime-replacement-evaluation.md), [review rubric](docs/evaluation/Clarence-9-runtime-review-rubric-v1.0.md), and [conformance vectors](compliance-tests/runtime-evaluation/clarence-9-v1/) |
| Runtime-evaluation verification | [`docs/verification/CPAS-v2-runtime-evaluation-2026-08-12.md`](docs/verification/CPAS-v2-runtime-evaluation-2026-08-12.md) |

## Status vocabulary

- **Conceptual specification**: a design claim only.
- **Protocol**: a machine-checkable interchange contract.
- **Reference implementation**: executable code demonstrating one approach.
- **Verified capability**: behavior exercised under a stated runtime and test.

Schema validity is not deployment certification. A declared capability is not a
probed capability, and an integrity digest is not authentication.
