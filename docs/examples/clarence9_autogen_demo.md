# Clarence-9 AutoGen Deployment Demo

This walkthrough shows how to showcase the **Clarence-9** agent using the AutoGen utilities bundled with CPAS-Core.

## Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Create the Agent

```python
from agents.python.Clarence_9 import create_agent, send_message
agent = create_agent(thread_token="demo-thread")
```

## Send a Message

```python
reply = send_message(agent, "Hello Clarence", thread_token="demo-thread")
print(reply)
```

## Reflection Simulation

Provide `end_session=True` and a populated `session_state` to generate a DKA-E digest:

```python
state = {
    "participating_instances": ["Clarence-9"],
    "core_metaphor": {"seed": "mirror"},
    "confidence_gradient": {"baseline": 0.8},
    "assumption_tree": {},
    "evolution_history": []
}
send_message(agent, "wrap up", thread_token="demo-thread", end_session=True, session_state=state)
```

## Cross-Instance Validation

```python
send_message(
    agent,
    "Claim: the sky is blue",
    thread_token="demo-thread",
    validation_request="Please cross-check"
)
```

## Drift Detection

Update live metrics and run the tracker:

```bash
python tools/monitor_dkae.py
python tools/metrics_drift_tracker.py
```

The resulting logs appear under `docs/examples/` for inspection.
