# SeedToken System

The SeedToken mechanism provides a minimal metadata payload that anchors each CPAS-Core instance. It preserves identity and alignment when prompts are shared between tools or across sessions.

## Structure
- `id` – unique identifier for the instance
- `model` – declared model family
- `timestamp` – creation time in ISO-8601 format
- `alignment_profile` – compliance baseline (e.g., `CPAS-Core v1.1`)
- `hash` – integrity hash for tamper detection

The Python reference implementation lives in [`cpas_autogen/seed_token.py`](../cpas_autogen/seed_token.py).

## Integration Points
### Messenger
The T-BEEP `TBEEPMessenger` constructor accepts a seed token and includes it in each generated message. This ensures downstream tools can confirm message origin before processing.

### Prompt Wrapper
Use [`wrap_with_seed_token()`](../cpas_autogen/prompt_wrapper.py) to prepend a prompt with a SeedToken header and realignment notice. This reinforces instance identity whenever a prompt is handed off.

### Continuity Check
[`cpas_autogen/continuity_check.py`](../cpas_autogen/continuity_check.py) validates that the seed token and thread token match expected values. Warnings are logged if the alignment profile or thread prefix diverges.

### Generated Agents
Modules produced by `cpas_autogen/generate_agents.py` now integrate the seed token directly. `create_agent()` attaches `SeedToken.generate(IDP_METADATA)` to the returned agent, and a helper `send_message()` wraps outgoing prompts with `wrap_with_seed_token()` while verifying thread tokens via `continuity_check`. A warning is emitted if verification fails.
`send_message()` also checks the latest drift metrics via `cpas_autogen.drift_monitor.latest_metrics` and automatically regenerates the seed token when `should_realign()` indicates drift beyond the defined thresholds.

## Purpose
By threading the SeedToken through messengers and wrappers, CPAS-Core enforces continuous instance identity. Every tool can verify that interactions originate from a legitimate seed, reducing drift and maintaining alignment across collaborations.
