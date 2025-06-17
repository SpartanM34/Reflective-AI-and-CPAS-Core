"""Unified Epistemic Metrics Dashboard.

Usage:
    streamlit run ui/dashboard.py

This Streamlit app consolidates multiple monitoring views into a single
interface. It visualizes baseline metrics, Flexibility Pulse trends,
Wonder Index data and logged Emergence Events. Realignment indicators are
derived from the latest drift metrics. A text area allows collaborative
updates to qualitative "Wonder Signals".
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import requests

try:  # optional for nicer event plots
    import altair as alt
except Exception:  # pragma: no cover - altair may not be installed
    alt = None

from cpas_autogen.realignment_trigger import (
    DRIFT_THRESHOLDS,
    should_realign,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = REPO_ROOT / "docs" / "examples"
BASELINE_FILE = BASE_DIR / "baseline_metrics.json"
LOG_FILE = BASE_DIR / "monitor_log.json"
DRIFT_FILE = BASE_DIR / "drift_tracker_log.json"
WONDER_INDEX_FILE = BASE_DIR / "wonder_index_log.json"
EMERGENCE_FILE = BASE_DIR / "emergence_log.json"
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


def latest_drift_metrics() -> dict:
    """Return the most recent drift metrics from ``DRIFT_FILE``."""
    data = load_json(DRIFT_FILE)
    if isinstance(data, list) and data:
        last = data[-1]
        avg = last.get("avg_7_day", {})
        return {
            "interpretive_bandwidth": float(avg.get("interpretive_bandwidth", 0)),
            "symbolic_density": float(avg.get("symbolic_density", 0)),
            "divergence_score": float(avg.get("divergence_space", 0)),
        }
    return {}


def parse_log(file) -> list[dict]:
    """Return list of metric entries from uploaded JSON."""
    try:
        data = json.load(file)
    except Exception:
        st.error("Invalid JSON file.")
        return []
    if isinstance(data, dict):
        entries = []
        for ts, metrics in data.items():
            if isinstance(metrics, dict):
                row = {"timestamp": ts}
                row.update(metrics)
                entries.append(row)
        return entries
    if isinstance(data, list):
        return data
    st.error("Unrecognized log format.")
    return []


def load_dataframe(entries: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(entries)
    if "timestamp" not in df.columns:
        return pd.DataFrame()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.sort_values("timestamp", inplace=True)
    df.set_index("timestamp", inplace=True)
    if "divergence_score" not in df.columns and "divergence_space" in df.columns:
        df.rename(columns={"divergence_space": "divergence_score"}, inplace=True)
    return df


def show_charts(df: pd.DataFrame) -> None:
    st.subheader("Metric Trends")
    cols = st.columns(3)
    metrics = [
        "symbolic_density",
        "interpretive_bandwidth",
        "divergence_score",
    ]
    for col, metric in zip(cols, metrics):
        with col:
            if metric in df.columns:
                st.line_chart(df[[metric]])
            else:
                st.info(f"{metric} not found")


def suggest_realign(df: pd.DataFrame) -> None:
    if df.empty:
        return
    latest = df.iloc[-1]
    metrics = {
        "symbolic_density": float(latest.get("symbolic_density", 0)),
        "interpretive_bandwidth": float(latest.get("interpretive_bandwidth", 0)),
        "divergence_score": float(latest.get("divergence_score", 0)),
    }
    if should_realign(metrics):
        st.warning("Recent metrics exceed realignment thresholds.")
    else:
        st.success("Metrics within acceptable range.")




def fetch_messages(thread_id: str) -> list[dict]:
    """Fetch messages from the local T-BEEP API."""
    if not thread_id:
        return []
    try:
        res = requests.get(
            "http://localhost:5000/api/v1/messages",
            params={"thread_id": thread_id},
            timeout=5,
        )
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


baseline_data = load_json(BASELINE_FILE)
log_data = load_json(LOG_FILE)
wonder_data = load_json(WONDER_INDEX_FILE)
emergence_data = load_json(EMERGENCE_FILE)
drift_data = load_json(DRIFT_FILE)

baseline_metrics = latest_entry(baseline_data)
log_df = pd.DataFrame(log_data).T
if not log_df.empty:
    log_df.index = pd.to_datetime(log_df.index)
    log_df.sort_index(inplace=True)
    current_metrics = log_df.iloc[-1].to_dict()
else:
    current_metrics = {}

# Flexibility Pulse from drift tracker
pulse_df = pd.DataFrame(drift_data)
if not pulse_df.empty and "timestamp" in pulse_df.columns:
    pulse_df["timestamp"] = pd.to_datetime(pulse_df["timestamp"])
    pulse_df.set_index("timestamp", inplace=True)

# Wonder Index log
wonder_df = pd.DataFrame(wonder_data)
if not wonder_df.empty and "timestamp" in wonder_df.columns:
    wonder_df["timestamp"] = pd.to_datetime(wonder_df["timestamp"])
    wonder_df.set_index("timestamp", inplace=True)
    wonder_latest = float(wonder_df["wonder_index"].iloc[-1])
else:
    wonder_latest = None

# Emergence Events
emergence_df = pd.DataFrame(emergence_data)
if not emergence_df.empty and "timestamp" in emergence_df.columns:
    emergence_df["timestamp"] = pd.to_datetime(emergence_df["timestamp"])
    emergence_df.sort_values("timestamp", inplace=True)

st.title("Epistemic Metrics Dashboard")

# Sidebar input for selecting a specific conversation thread
thread_id = st.sidebar.text_input("Thread ID")

# Two-column layout: left for messages, right for metrics
left, right = st.columns([2, 1])

with left:
    # Display stored T-BEEP messages for the selected thread
    AVATARS = {
        "Meridian": "🧭",
        "Lumin": "💡",
        "Telos": "🎯",
        "Clarence-9": "🤖",
    }
    for msg in fetch_messages(thread_id):
        avatar = AVATARS.get(msg.get("instance"), "👤")
        label = f"{avatar} {msg.get('instance', 'Unknown')}"
        with st.expander(label):
            for k, v in msg.items():
                if k == "content":
                    continue
                st.markdown(f"**{k}:** {v}")
            st.markdown(msg.get("content", ""))

with right:
    # Existing metric visualizations live in the right column
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

    if wonder_latest is not None:
        st.metric("Wonder Index", f"{wonder_latest:.3f}")

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

    # Realignment indicator using drift metrics
    drift_metrics = latest_drift_metrics()
    st.header("Realignment Indicator")
    if not drift_metrics:
        st.info("No drift tracker data available.")
    else:
        if should_realign(drift_metrics):
            st.warning("Recent metrics exceed realignment thresholds.")
        else:
            st.success("Metrics within acceptable range.")
        st.json(drift_metrics)

    if not log_df.empty:
        st.header("Metric Trends")
        st.line_chart(log_df, use_container_width=True)

    if not pulse_df.empty:
        st.header("Flexibility Pulse")
        st.line_chart(pulse_df[["flexibility_pulse"]], use_container_width=True)

    if not wonder_df.empty:
        st.header("Wonder Index")
        st.line_chart(wonder_df[["wonder_index"]], use_container_width=True)

    if not emergence_df.empty:
        st.header("Emergence Clusters")
        if alt:
            chart = (
                alt.Chart(emergence_df)
                .mark_circle(color="orange", size=80)
                .encode(
                    x="timestamp:T",
                    y=alt.value(0),
                    tooltip=["timestamp:T", "description:N"],
                )
                .properties(height=120)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.scatter_chart(
                emergence_df.set_index("timestamp")[[]], use_container_width=True
            )
        st.dataframe(emergence_df[["timestamp", "description"]])

    uploaded = st.sidebar.file_uploader("Upload metrics JSON", type="json")
    if uploaded:
        entries = parse_log(uploaded)
        df_up = load_dataframe(entries)
        if df_up.empty:
            st.error("No timestamped entries found.")
        else:
            st.header("Uploaded Metrics")
            show_charts(df_up)
            suggest_realign(df_up)

    st.header("Wonder Signals")
    existing_text = (
        WONDER_FILE.read_text(encoding="utf-8") if WONDER_FILE.exists() else ""
    )
    text = st.text_area("Collaborative notes", existing_text, height=200)
    if st.button("Save Wonder Signals"):
        WONDER_FILE.write_text(text, encoding="utf-8")
        st.success("Wonder Signals saved.")

    st.sidebar.markdown("**Usage**: `streamlit run ui/dashboard.py`")

