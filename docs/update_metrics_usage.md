# Metrics Update Utility

`tools/update_metrics.py` appends session metrics to the monitoring logs and refreshes baseline values.

## Manual Usage

```bash
python tools/update_metrics.py path/to/session_metrics.json
```

`session_metrics.json` must provide `interpretive_bandwidth`, `symbolic_density` and `divergence_space` values.

## Cron Example

To run the update every day at 2am:

```
0 2 * * * /usr/bin/python /path/to/tools/update_metrics.py /path/to/session_metrics.json
```
