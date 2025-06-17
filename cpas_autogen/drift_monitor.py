from __future__ import annotations

"""Utility functions for retrieving latest drift metrics."""

import json
from pathlib import Path
from typing import Dict

from .config import DRIFT_LOG


def latest_metrics() -> Dict[str, float]:
    """Return the most recent drift metrics from ``DRIFT_LOG``.

    The metrics are extracted from the 7-day rolling averages in
    ``drift_tracker_log.json``. If the log is missing or malformed,
    an empty dictionary is returned.
    """
    if not DRIFT_LOG.exists():
        return {}
    try:
        data = json.loads(DRIFT_LOG.read_text())
    except Exception:
        return {}
    if isinstance(data, list) and data:
        last = data[-1]
        avg = last.get("avg_7_day", {})
        return {
            "interpretive_bandwidth": float(avg.get("interpretive_bandwidth", 0)),
            "symbolic_density": float(avg.get("symbolic_density", 0)),
            "divergence_score": float(avg.get("divergence_space", 0)),
        }
    return {}


__all__ = ["latest_metrics"]
