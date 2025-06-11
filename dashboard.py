#!/usr/bin/env python3
"""Simple Streamlit dashboard for visualizing flexibility pulse."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st


def load_json(path: Path):
    """Return parsed JSON from file or None if missing."""
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def main():
    st.title("Flexibility Pulse Dashboard")

    data = load_json(Path("tools/drift_tracker_log.json"))
    if not data:
        st.info("No drift data found.")
        return

    df = pd.DataFrame(
        {
            "timestamp": [entry["timestamp"] for entry in data],
            "flexibility_pulse": [entry["flexibility_pulse"] for entry in data],
        }
    ).set_index("timestamp")

    st.line_chart(df)


if __name__ == "__main__":
    main()
