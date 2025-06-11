# Dynamic Dashboard Prototype

`tools/dashboard.py` provides a lightweight Streamlit interface for real-time visualization of epistemic metrics.

## Usage

```bash
streamlit run tools/dashboard.py
```

The dashboard reads baseline values from `tools/baseline_metrics.json` and live metrics from `tools/monitor_log.json`.
It highlights drift, signals potential rollback triggers, and offers a collaborative **Wonder Signals** text area.
