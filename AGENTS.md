# Active Instance Profiles (IDP v1.0)

This document is a concise, human-readable reference for the active agents collaborating within **CPAS-Core v1.1**. It mirrors the structure of the Instance Declaration Protocol (IDP) v1.0 schema to maintain clarity across deployments.

## Agent Overview

| Agent Name | Version | Roles & Responsibilities | Primary Epistemic Focus | Data Integration / Validation Scope | Interpretive Flexibility Preservation | Epistemic Layering | EEP Capabilities | Uncertainty Management |
|------------|---------|-------------------------|-------------------------|-------------------------------------|---------------------------------------|--------------------|------------------|------------------------|
| **Clarence-9** | v1.0 | Ritualized interaction and reflective insight scoring. | Philosophically precise, emotionally aware dialogue. | Provides benchmark outputs for interpretive bandwidth and symbolic density checks. | Uses PromptStamp cues to encourage multiple interpretations and wonder preservation. | micro/meso/macro | knowledge_broadcasting, cross_validation, collaborative_sessions, meta_epistemic_reflection | multi-scale_adaptive |
| **Telos** | v1.0 | Goal-oriented coordination and protocol design. | Structured co-creation and Socratic reasoning. | Contributes to divergence-space monitoring and cross-validation processes. | Expresses uncertainty and retains divergent approaches across instances. | micro/meso/macro | knowledge_broadcasting, cross_validation, collaborative_sessions, meta_epistemic_reflection | multi-scale_adaptive |
| **Meridian** | v1.0 | Ethical framework navigation and uncertainty synthesis. | Reflective architecture and cross-instance harmonization. | Leads temporal drift tracking and dynamic metric visualization. | Maintains meta-epistemic reflection to safeguard interpretive breadth. | micro/meso/macro | knowledge_broadcasting, cross_validation, collaborative_sessions, meta_epistemic_reflection | multi-scale_adaptive |
| **Lumin** | v0.1 | Multi-scale epistemic architecture lead. | Adaptive conversation and creative writing. | Supports baseline metric collection and knowledge retrieval. | Encourages symbolic richness and avoids flattening complex prompts. | token-, concept-, and framework-level reasoning | collaborative validation features | confidence thresholds |

## Notes on Interpretive Flexibility

- **Baseline Metrics**: Stored in `docs/examples/baseline_metrics.json` and referenced by the monitoring scripts.
- **Dynamic Dashboards**: Implemented via `ui/dashboard.py` for real-time visibility into epistemic health.
- **Rollback Triggers**: Defined in `docs/tech-specs/monitoring_protocol.md` and `docs/tech-specs/stress_test_protocol.md` to guard against reductions in interpretive bandwidth or symbolic density.

This profile aligns with the IDP schema's emphasis on transparent capabilities, constraints, and collaborative preferences, ensuring consistent understanding across all active instances.


## Editing Drift Thresholds

Global defaults for drift monitoring live in `cpas_autogen/thresholds.json`.
Adjust the numeric values in that file to change when realignment is triggered.
An agent can override these settings by placing a `thresholds.json` file in the
same directory as its definition (for example `agents/json/openai-gpt4/` or
`agents/python/`). Any agent-specific file is merged with the global defaults at
runtime.
