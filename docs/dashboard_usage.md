# Dynamic Dashboard Prototype

`tools/dashboard.py` provides a lightweight Streamlit interface for real-time visualization of epistemic metrics. The dashboard now consolidates multiple views including Flexibility Pulse, Wonder Index trends, emergence events and realignment indicators.

## Usage

```bash
streamlit run tools/dashboard.py
```

The dashboard reads baseline values from `tools/baseline_metrics.json` and live metrics from `tools/monitor_log.json`.
It also displays data from `tools/drift_tracker_log.json`, `tools/wonder_index_log.json` and `tools/emergence_log.json`.
Drift metrics are checked against realignment thresholds and highlighted when thresholds are exceeded. A collaborative **Wonder Signals** text area is available for qualitative notes.
