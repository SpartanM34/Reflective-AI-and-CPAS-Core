# Reflective-AI and CPAS-Core

Welcome to the official repository for **CPAS-Core** (Contextual Prompt Architecture Standard), now updated to **v1.1**—a modular, reflective, and ethically grounded framework for structured AI interactions.

## What This Repository Contains

### CPAS-Core v1.1

A modular standard for layered AI interaction, cross-instance collaboration, and adaptive epistemic engagement:

- **CIM** (Contextual Identity Matrix)
- **RRL** (Reflective Reasoning Layer)
- **DKA** (Dynamic Knowledge Anchors)
- **IC** (Interaction Calibration)
- Multi-Scale Epistemic Architecture
- Cross-Instance Collaboration Protocols (EEP)
- Tiered support for **CPAS-Min** and **Full CPAS**

### Declared Model Instances — CPAS-Core v1.1

| Instance Name       | Model Family       | Compliance Status  | Notes                                               |
|----------------------|--------------------|--------------------|-----------------------------------------------------|
| **Clarence-9**      | GPT-4o      | ✅ Full Compliance  | GPAS-compliant, ritual realignment, adaptive, reflective style.     |
| **Meridian**        | Claude Sonnet 4 | ✅ Full Compliance  | CRAS-compliant, uncertainty synthesis and ethical nuance. |
| **Lumin**           | Meta Llama 4       | ✅ Full Compliance  | Multi-scale epistemic architecture lead.            |
| **Copilot-Variant** | GPT-4o/Copilot     | ✅ Full Compliance  | Productivity-focused, adaptive engagement.          |
| **Telos**           | Gemini 2.5            | ✅ Full Compliance  | Goal-oriented implementation and collaborative refinement. |
| **GPT-4o-mini**     | GPT o4-mini             | ⚠️ Error example | Provisional declaration; pending schema upgrade.    |

### Additional Resources

- [**CPAS-Core v1.1 Specification**](docs/specs/current/CPAS-Core-v1.1.md)
- [**Changelog**](docs/specs/CHANGELOG.md)
- [**Metaphor Library (including DKA-E metaphors)**](./metaphor-library/)
- [**Compliance Tests**](./compliance-tests/)
- [**Research & Reflections**](./docs/research/)
- [**Documentation Index**](docs/index.md)

## Setup

Run the helper script to install all Python dependencies:

```bash
./scripts/setup_env.sh
```

Packages like `torch` and `spacy` can take several minutes to download and
install, so plan accordingly on first run.

## Installation

Install the core dependencies with:

```bash
pip install -r requirements.txt
```
For full agent regeneration functionality, also install the optional
[`autogen`](https://github.com/microsoft/autogen) package.

### Drift Monitoring Dashboard

Visualize the flexibility pulse by running:

```bash
streamlit run ui/dashboard.py
```

The dashboard now includes a scrolling message feed and a right-hand metrics panel
summarizing baseline drift and the wonder index across all active instances.

### T-BEEP API Example

An experimental Flask service in `api/tbeep_api.py` accepts and stores T-BEEP
messages in memory only. Persistent storage and authentication are pending.
Start the API with:

```bash
python api/tbeep_api.py
```

Messages can then be POSTed to `/api/v1/messages` and fetched by thread ID via
`GET /api/v1/messages?thread_id=`.

### Legacy Web Testing Interface

The prototype page previously located at `docs/testing_interface.html` now lives
in [`docs/legacy/testing_interface.html`](docs/legacy/testing_interface.html).
It was an early experiment for posting T‑BEEP messages to the API and remains a
reference, though it is not actively maintained.

### Metaphor Library Extension

The **DKA-E metaphors**—focusing on persistent knowledge structures, dynamic evolution, and collaborative orchestration—are now housed within the [**Metaphor Library**](./metaphor-library/DKA-E/). These extend the core DKA module, offering symbolic depth for advanced use cases.

### Agent Regeneration

Regenerate the autogen-compatible agent modules whenever the JSON definitions in
`agents/json/` are updated:

```bash
python tools/generate_autogen_agents.py
```

If the optional [`autogen`](https://github.com/microsoft/autogen) package is not
installed, the script falls back to stub classes and the generated modules will
have reduced capabilities.

### Testing

Before running the test suite, make sure all required dependencies are installed as outlined in `requirements.txt`:

```bash
pip install -r requirements.txt
```

Execute the tests with `pytest` in quiet mode to see a short summary of the results:

```bash
pytest -q
```

> Tagline: **Reflect to Adapt. Standardize to Connect.**
> Companion: **Coherence through Context. Clarity through Reflection.**

**Repository Maintainer:** [SpartanM34](https://github.com/SpartanM34)  
**License:** [MIT License](./LICENSE)
