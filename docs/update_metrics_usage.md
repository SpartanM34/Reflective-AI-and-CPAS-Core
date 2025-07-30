# Metrics Update Utility

`tools/update_metrics.py` appends session metrics to the monitoring logs and refreshes baseline values. The utility now records `epistemic_layering`, `eep_capabilities`, and `uncertainty_management` fields when present.

## Manual Usage

```bash
python tools/update_metrics.py path/to/session_metrics.json
```

`session_metrics.json` must provide `interpretive_bandwidth`, `symbolic_density` and `divergence_space` values. Optional keys `epistemic_layering`, `eep_capabilities`, and `uncertainty_management` will be stored alongside the core metrics.

An example metrics file with the new fields is provided at [docs/examples/session_metrics_sample.json](examples/session_metrics_sample.json).

## Cron Example

To run the update every day at 2am:

```
0 2 * * * /usr/bin/python /path/to/tools/update_metrics.py /path/to/session_metrics.json
```
## Message Logger Example

`cpas_autogen.message_logger.log_message` records each AI message to `examples/message_manifest.json`. It expects the conversation `threadToken`, UTC timestamp, instance name, seed token, message content hash and the fingerprint.

```python
from cpas_autogen.message_logger import log_message

log_message(
    thread_token="demo-thread-1",
    timestamp="2025-06-10T12:00:00Z",
    instance="Lumin",
    seed_token="seed-001",
    content_hash="d41d8cd98f00b204e9800998ecf8427e",
    fingerprint="fp-0001",
)
```
