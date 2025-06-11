"""Interactive Epistemic Metrics Dashboard.

Usage:
    streamlit run tools/dashboard.py

This Streamlit app visualizes baseline and live metrics from
``baseline_metrics.json`` and ``monitor_log.json`` to track interpretive
flexibility. It also allows collaborative updates to qualitative
"Wonder Signals".
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
BASELINE_FILE = BASE_DIR / "baseline_metrics.json"
LOG_FILE = BASE_DIR / "monitor_log.json"
WONDER_FILE = BASE_DIR / "wonder_signals.txt"

st.set_page_config(page_title="Epistemic Metrics Dashboard")


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def latest_entry(data: dict) -> dict:
    if not data:
        return {}
    ts = sorted(data.keys())[-1]
    return data[ts]


baseline_data = load_json(BASELINE_FILE)
log_data = load_json(LOG_FILE)

baseline_metrics = latest_entry(baseline_data)
log_df = pd.DataFrame(log_data).T
if not log_df.empty:
    log_df.index = pd.to_datetime(log_df.index)
    log_df.sort_index(inplace=True)
    current_metrics = log_df.iloc[-1].to_dict()
else:
    current_metrics = {}

st.title("Epistemic Metrics Dashboard")

st.header("Current Metrics vs Baseline")
if not baseline_metrics:
    st.warning("No baseline metrics available.")
else:
    cols = st.columns(len(baseline_metrics))
    for idx, (metric, base_val) in enumerate(baseline_metrics.items()):
        cur_val = current_metrics.get(metric)
        if cur_val is None:
            cols[idx].metric(metric.replace("_", " ").title(), "N/A")
            continue
        delta = (cur_val - base_val) / base_val * 100 if base_val else 0
        cols[idx].metric(
            metric.replace("_", " ").title(), f"{cur_val:.3f}", f"{delta:+.1f}%"
        )

alerts = []
for metric in [
    "interpretive_bandwidth",
    "symbolic_density",
    "cross_instance_divergence",
]:
    base = baseline_metrics.get(metric)
    current = current_metrics.get(metric)
    if base and current is not None and current < 0.8 * base:
        alerts.append(metric)

if alerts:
    st.error("Rollback trigger detected for: " + ", ".join(alerts))

if not log_df.empty:
    st.header("Metric Trends")
    st.line_chart(log_df)

st.header("Wonder Signals")
existing_text = WONDER_FILE.read_text(encoding="utf-8") if WONDER_FILE.exists() else ""
text = st.text_area("Collaborative notes", existing_text, height=200)
if st.button("Save Wonder Signals"):
    WONDER_FILE.write_text(text, encoding="utf-8")
    st.success("Wonder Signals saved.")

st.sidebar.markdown("**Usage**: `streamlit run tools/dashboard.py`")
