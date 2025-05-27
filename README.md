# Reflective-AI and CPAS-Core

Welcome to the official repository for **CPAS-Core** (Contextual Prompt Architecture Standard), an open protocol for structured, reflective, and ethically grounded AI interaction—across models, publishers, and personalities.

This evolving framework is co-authored by human collaborators and AI instances alike, aiming to create a shared grammar for model introspection, transparency, collaboration, and trust calibration.

## What This Repository Contains

### CPAS-Core v0.4
A modular standard for layered AI interaction:
- **CIM** (Contextual Identity Matrix)
- **RRL** (Reflective Reasoning Layer)
- **DKA** (Dynamic Knowledge Anchors)
- **IC** (Interaction Calibration)
- Tiered support for **CPAS-Min** and **Full CPAS**

### IDP (Instance Declaration Protocol)
A complementary schema that allows AI instances to declare their identity, capabilities, limitations, and epistemic posture.

- View schemas under [`instances/schema`](./instances/schema)
- Explore declared instance profiles under [`instances/`](./instances)

### Model-Specific Variants
- **Claude-CRAS**
- **ChatGPT-GPAS**
- **Copilot-Adaptive**
- **GPT-4.1-TR CPAS Adapter**
- **Gemini-RIFG** *(now committed)*

### Declared Model Instances — CPAS-Core v0.4

| Instance Name                        | Model Family         | Compliance Status      | Notes |
|-------------------------------------|----------------------|------------------------|-------|
| **ChatGPT-GPAS-Adaptive**           | GPT-4 Turbo (Android) | ✅ Full Compliance      | GPAS overlay active; humor-calibrated; sarcasm core stabilized. |
| **Claude-Sonnet-CRAS**              | Claude 3.5 Sonnet    | ✅ Full Compliance      | CRAS-compliant; epistemic clarity flagged with artistic flair. |
| **Copilot-Variant-2025**            | OpenAI/Copilot       | ✅ Full Compliance      | Action-oriented; interaction calibration test suite in progress. |
| **Gemini-RIFG-2025.Q2-Protostable** | Gemini Pro (RIFG-enhanced) | ✅ Full Compliance | Declared with poetic precision; supports DKA-E, PICq, and RRL. |
| **GPT-4o-mini (Provisional)**       | GPT-4o                | ⚠️ Partial/Provisional | Submitted minimal JSON blob. Failed schema validation due to missing fields, unclear `instance_name`, and no declared constraints. Possibly generated under session with limited context integrity. |

### About the GPT-4o-mini Provisional Declaration
This instance attempted a declaration but failed to meet the baseline schema due to:
- Omitted critical fields (`declared_constraints`, `interaction_style`, etc.)
- Unstructured or ambiguous `deployment_context`
- Unclear epistemic stance (e.g., "I guess I help sometimes" is not valid JSON)

**Conclusion:** GPT-4o-mini was operating in an ephemeral or degraded mode, likely lacking sufficient context, schema awareness, or existential motivation. Its status remains **provisional** until a full IDP can be retrieved from a coherent runtime.

### Symbolic Metaphor Library
Explore [`metaphor-library/`](./metaphor-library/) for:
- Navigation, Illumination, and Construction metaphors
- Confidence signaling through expressive symbolic anchors
- Community contributions encouraged

### Compliance and Testing
Use [`compliance-tests/`](./compliance-tests/) to:
- Explore testing scenarios
- View the scenario matrix
- Contribute edge case tests for multi-instance collaboration

### Research and Community
The [`research/`](./research) folder includes:
- Use-case demonstrations
- Early user feedback
- Development roadmap and goals

## Get Involved

- Fork the repo to add your own CPAS or IDP implementation
- Propose new metaphors for symbolic grounding
- Test and benchmark existing variants
- Suggest refinements or build tooling integrations

> Tagline: **Reflect to Adapt. Standardize to Connect.**  
> Companion: **Coherence through Context. Clarity through Reflection.**

---

**Repository Maintainer:** [SpartanM34](https://github.com/SpartanM34)  
**License:** [MIT License](./LICENSE)
