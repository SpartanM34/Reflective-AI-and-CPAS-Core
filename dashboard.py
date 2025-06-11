#!/usr/bin/env python3
"""Interactive metrics dashboard.

Usage:
    streamlit run dashboard.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import altair as alt
except Exception:  # pragma: no cover - altair optional
    alt = None


def load_json(path: Path):
    """Return parsed JSON from file or None if missing."""
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def main():
    st.title("Flexibility Pulse Dashboard")

    # Flexibility pulse trend
    pulse = load_json(Path("tools/drift_tracker_log.json"))
    if pulse:
        st.subheader("Flexibility Pulse")
        df = pd.DataFrame(
            {
                "timestamp": [entry["timestamp"] for entry in pulse],
                "flexibility_pulse": [entry["flexibility_pulse"] for entry in pulse],
            }
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        st.line_chart(df)
    else:
        st.info("No drift data found.")

    # Wonder Index and emergence events side by side
    cols = st.columns(2)

    with cols[0]:
        st.subheader("Wonder Index")
        wonder = load_json(Path("tools/wonder_index_log.json"))
        if wonder:
            w_df = pd.DataFrame(
                {
                    "timestamp": [e.get("timestamp") for e in wonder],
                    "wonder_index": [e.get("wonder_index") for e in wonder],
                }
            )
            w_df["timestamp"] = pd.to_datetime(w_df["timestamp"])
            w_df.set_index("timestamp", inplace=True)
            st.line_chart(w_df)
        else:
            st.info("No Wonder Index data found.")

    with cols[1]:
        st.subheader("Emergence Events")
        events = load_json(Path("tools/emergence_log.json"))
        if events:
            e_df = pd.DataFrame(events)
            if not e_df.empty and "timestamp" in e_df.columns:
                e_df["timestamp"] = pd.to_datetime(e_df["timestamp"])
                e_df.sort_values("timestamp", inplace=True)
                if alt:
                    chart = (
                        alt.Chart(e_df)
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
                    # fallback to simple scatter chart without tooltips
                    st.scatter_chart(e_df.set_index("timestamp")[[]])
            st.dataframe(e_df[["timestamp", "description"]])
        else:
            st.info("No emergence events found.")


if __name__ == "__main__":
    main()
