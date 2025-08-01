# Reflective-AI and CPAS-Core

Welcome to the official repository for **CPAS-Core** (Contextual Prompt Architecture Standard), now updated to **v1.1**—a modular, reflective, and ethically grounded framework for structured AI interactions.

## What This Repository Contains

### CPAS-Core v1.1

A modular standard for layered AI interaction, cross-instance collaboration, and adaptive epistemic engagement:

Cross-instance compatibility now references a multi-layer ethical framework for consistent behavior across deployments.
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

## Quickstart
```bash
git clone https://github.com/SpartanM34/Reflective-AI-and-CPAS-Core.git
cd Reflective-AI-and-CPAS-Core
pip install -r requirements.txt
pip install -e ".[web]"
python tools/generate_autogen_agents.py
streamlit run ui/dashboard.py
# For Flask >=2.2 you can use ``--app``; older versions require setting
# the ``FLASK_APP`` environment variable first. On PowerShell:
#     $env:FLASK_APP = "api/tbeep_api.py"
# then run:
flask run
```

## Installation

Install the core dependencies with:

```bash
pip install -r requirements.txt
pip install -e .
```

Install optional dashboard and API features with:

```bash
pip install -e ".[web]"
```

### Drift Monitoring Dashboard

Visualize the flexibility pulse (requires the `web` extras) by running:

```bash
streamlit run ui/dashboard.py
```
See [docs/update_metrics_usage.md](docs/update_metrics_usage.md) for automated log updates with the new metrics fields.

The dashboard now includes a scrolling message feed and a right-hand metrics panel
summarizing baseline drift and the wonder index across all active instances.

### Logging Wonder Signals

Short reflective notes can be appended to `docs/examples/wonder_signals.json`
using:

```bash
python tools/record_wonder.py "A brief insight"
```

Each invocation adds a timestamped JSON object of the form
`{"timestamp": "...", "text": "..."}` which is later consumed by the Wonder
Index calculator.

### T-BEEP API Example

An experimental Flask service in `api/tbeep_api.py` accepts and stores T-BEEP
messages in memory only. Persistent storage and authentication are pending. This
feature also requires the `web` extras. Start the API with:

```bash
# Either run the module directly
python api/tbeep_api.py
# or, with Flask's CLI (PowerShell syntax shown):
# $env:FLASK_APP = "api/tbeep_api.py"
# flask run
```

Messages can then be POSTed to `/api/v1/messages` and fetched by thread ID via `GET /api/v1/messages?thread_id=`.

Example usage:
```bash
curl -X POST -H "Content-Type: application/json" -d {"threadToken": "#T1", "content": "hello"} http://localhost:5000/api/v1/messages
curl "http://localhost:5000/api/v1/messages?thread_id=#T1"
```
### Legacy Web Testing Interface

The prototype page at `docs/legacy/testing_interface.html` was an early
experiment for posting T‑BEEP messages to the API. It remains as a reference but
is not actively maintained.

### Metaphor Library Extension

The **DKA-E metaphors**—focusing on persistent knowledge structures, dynamic evolution, and collaborative orchestration—are now housed within the [**Metaphor Library**](./metaphor-library/DKA-E/). These extend the core DKA module, offering symbolic depth for advanced use cases.

### Testing

Install the test dependencies (including `pytest` and `pytest-cov`) along with the core requirements:

```bash
pip install -r requirements.txt
```

Then run the suite using `pytest` in quiet mode:

```bash
pytest -q
```

### Post-Commit Monitoring Hook

Enable automatic metric checks after each commit by installing the provided
`post-commit` hook:

```bash
cp .githooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

The hook runs `tools/monitor_dkae.py` and will revert the commit if metrics
fall below the defined thresholds.
## Contributing
Contributions are welcome! Please open issues or pull requests via GitHub.


> Tagline: **Reflect to Adapt. Standardize to Connect.**
> Companion: **Coherence through Context. Clarity through Reflection.**

**Repository Maintainer:** [SpartanM34](https://github.com/SpartanM34)  
**License:** [MIT License](./LICENSE)
