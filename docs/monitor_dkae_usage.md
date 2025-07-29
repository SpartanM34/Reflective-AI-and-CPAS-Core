# DKA-E Monitoring Script

`tools/monitor_dkae.py` provides automated monitoring of the `/metaphor-library/DKA-E/` directory.
It computes the epistemic metrics defined in [monitoring_protocol.md](tech-specs/monitoring_protocol.md) and enforces rollback triggers when thresholds are breached.

## Running Manually

```bash
python tools/monitor_dkae.py
```

The script logs results to `docs/examples/monitor_log.json`. The first run also writes a baseline to `docs/examples/monitor_baseline.json`.

## Git Hook Integration

To execute the monitor after each commit, create `.git/hooks/post-commit` with the following content:

```bash
#!/bin/sh
python tools/monitor_dkae.py
```

Make the hook executable:

```bash
chmod +x .git/hooks/post-commit
```

The hook will revert the last commit automatically if a rollback trigger is activated.

## Adjusting Thresholds

`tools/monitor_dkae.py` and other utilities read drift thresholds from
`cpas_autogen/thresholds.json`. Edit that file to change the values for
`symbolic_density`, `interpretive_bandwidth`, or `divergence_score`. The new
thresholds will be applied the next time the monitor runs.
