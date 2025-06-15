#!/usr/bin/env python3
"""Metrics Drift Dashboard.

Usage:
    streamlit run tools/drift_dashboard.py

This Streamlit app visualizes metric drift from a JSON log. Users upload a
metrics log containing ``symbolic_density``, ``interpretive_bandwidth`` and
``divergence_score`` over time. If the latest values fall below
predefined thresholds, a realignment suggestion is displayed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

from tools.realignment_trigger import DRIFT_THRESHOLDS, should_realign


def parse_log(file) -> List[Dict[str, Any]]:
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


def load_dataframe(entries: List[Dict[str, Any]]) -> pd.DataFrame:
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


def main() -> None:
    st.title("Metrics Drift Dashboard")
    uploaded = st.file_uploader("Upload metrics JSON", type="json")
    if not uploaded:
        st.info("Please upload a metrics log file.")
        return

    entries = parse_log(uploaded)
    if not entries:
        return
    df = load_dataframe(entries)
    if df.empty:
        st.error("No timestamped entries found.")
        return

    show_charts(df)
    suggest_realign(df)


if __name__ == "__main__":
    main()
