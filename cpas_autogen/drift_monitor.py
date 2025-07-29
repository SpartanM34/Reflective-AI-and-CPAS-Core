from __future__ import annotations

"""Utility functions for retrieving latest drift metrics."""

import json
from pathlib import Path
from typing import Dict

from datetime import datetime, timedelta

from .config import DRIFT_LOG


def latest_averages() -> Dict[str, Dict[str, float]]:
    """Return the most recent 7- and 30-day averages from ``DRIFT_LOG``."""

    if not DRIFT_LOG.exists():
        return {}
    try:
        data = json.loads(DRIFT_LOG.read_text())
    except Exception:
        return {}
    if isinstance(data, list) and data:
        last = data[-1]
        avg7 = last.get("avg_7_day", {})
        avg30 = last.get("avg_30_day", {})
        return {
            "avg_7_day": {
                "interpretive_bandwidth": float(avg7.get("interpretive_bandwidth", 0)),
                "symbolic_density": float(avg7.get("symbolic_density", 0)),
                "divergence_space": float(avg7.get("divergence_space", 0)),
            },
            "avg_30_day": {
                "interpretive_bandwidth": float(avg30.get("interpretive_bandwidth", 0)),
                "symbolic_density": float(avg30.get("symbolic_density", 0)),
                "divergence_space": float(avg30.get("divergence_space", 0)),
            },
            "flexibility_pulse": float(last.get("flexibility_pulse", 0)),
        }
    return {}


def latest_metrics() -> Dict[str, float]:
    """Return the most recent 7-day drift metrics."""

    avgs = latest_averages()
    if not avgs:
        return {}
    avg = avgs.get("avg_7_day", {})
    return {
        "interpretive_bandwidth": float(avg.get("interpretive_bandwidth", 0)),
        "symbolic_density": float(avg.get("symbolic_density", 0)),
        "divergence_score": float(avg.get("divergence_space", 0)),
    }


__all__ = ["latest_metrics", "latest_averages"]
