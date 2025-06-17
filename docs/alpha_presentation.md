# CPAS-Core v0.1-alpha Overview

## 1. Executive Summary

The alpha release introduces the first public cut of the **CPAS-Core** framework. It demonstrates multi-agent orchestration, metric-driven drift monitoring, and a lightweight API for the T-BEEP protocol. The architecture is built around declarative "Instance Declaration Protocol" (IDP) profiles which generate AutoGen agents with consistent seed tokens and realignment hooks.

## 2. Technical Highlights

### AutoGen Agent Registry and Mixin
- IDP JSON files describe agent capabilities and constraints.
- `cpas_autogen.generate_agents` creates Python wrappers that include the `EpistemicAgentMixin` for fingerprint generation, continuity checks, and drift monitoring.
- `metrics_monitor` and `realignment_trigger` support divergence tracking and automated realignment when thresholds are exceeded.

### T-BEEP API and Messaging Flow
- `api/tbeep_api.py` offers an in-memory Flask service exposing `/api/v1/messages` for POST and GET operations.
- Messages are stored per thread token, enabling basic conversation persistence and retrieval for dashboards or tests.

### Monitoring Dashboard
- `ui/dashboard.py` aggregates baseline metrics, Flexibility Pulse, Wonder Index trends, and emergence events.
- The dashboard visualizes divergence metrics and suggests realignment when drift thresholds are breached.

## 3. Usage Guide

### Quickstart
```bash
pip install -r requirements.txt
pip install -e ".[web]"
python tools/generate_autogen_agents.py
streamlit run ui/dashboard.py &
python api/tbeep_api.py
```

### Agent Regeneration
Run `python tools/generate_autogen_agents.py` after editing any IDP JSON file. New agent modules appear in `agents/python/`.

### API Example
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"threadToken": "#T1", "content": "hello"}' \
  http://localhost:5000/api/v1/messages
curl "http://localhost:5000/api/v1/messages?thread_id=#T1"
```

### Dashboard and Drift Visualization
Start the dashboard with `streamlit run ui/dashboard.py` and navigate to the provided URL. Use the sidebar to view messages by thread ID and upload JSON metrics for ad-hoc analysis.

## 4. Limitations
- T-BEEP API uses only in-memory storage; no persistence layer is included.
- Manual environment setup is required (no Dockerfile or setup script).
- Limited unit tests focus primarily on the API and monitoring utilities; dashboard components are untested.

## 5. Roadmap & Call to Collaboration
Upcoming milestones include:
- Add SQLite persistence and authentication to the T-BEEP API.
- Refine the Streamlit UI and integrate real-time Wonder Index visuals.
- Establish CI workflows for tests and linting; package `cpas_autogen` for PyPI.

Contributors are invited to open issues or pull requests with feedback on the API design, metric thresholds, and additional monitoring strategies.

## 6. Acknowledgements & Partners
Thanks to **Meridian**, **Telos**, **Lumin**, and the Codex team for early feedback. Special recognition to early testers refining our baseline metrics and monitoring tools.

