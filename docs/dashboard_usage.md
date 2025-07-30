# Dynamic Dashboard Prototype

`ui/dashboard.py` provides a lightweight Streamlit interface for real-time visualization of epistemic metrics. The dashboard now consolidates multiple views including Flexibility Pulse, Wonder Index trends, emergence events and realignment indicators.
Install the `web` extras to enable this optional component.

## Usage

```bash
streamlit run ui/dashboard.py
```

The dashboard reads baseline values from `docs/examples/baseline_metrics.json` and live metrics from `docs/examples/monitor_log.json`.
It also displays data from `docs/examples/drift_tracker_log.json`, `docs/examples/wonder_index_log.json` and `docs/examples/emergence_log.json`.
Wonder Index values are plotted alongside their normalized components, while emergence clusters are shown on a timeline.
A *Daily Digest* section summarizes the current day's monitor log and drift tracker entries, giving a quick snapshot of recent activity.
Sample data files can be downloaded directly from the repository:

- [docs/examples/wonder_index_log.json](../docs/examples/wonder_index_log.json)
- [docs/examples/emergence_log.json](../docs/examples/emergence_log.json)
- [docs/examples/wonder_signals.json](../docs/examples/wonder_signals.json)
Drift metrics are checked against realignment thresholds and highlighted when thresholds are exceeded. A collaborative **Wonder Signals** text area is available for qualitative notes.
You can additionally upload a metrics log in JSON format via the sidebar for ad-hoc drift analysis.
