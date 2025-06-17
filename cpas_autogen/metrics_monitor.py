from __future__ import annotations

"""Utilities for comparing live metrics to baseline values."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from .instance_diff_engine import similarity_score
from .config import EXAMPLES_DIR, BASELINE_FILE

# Default interval for periodic checks (in minutes)
DEFAULT_INTERVAL = timedelta(minutes=30)


def load_baseline() -> Dict[str, float]:
    """Return the most recent baseline metrics."""
    if not BASELINE_FILE.exists():
        return {}
    try:
        data = json.loads(BASELINE_FILE.read_text())
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    latest_ts = sorted(data.keys())[-1]
    metrics = data.get(latest_ts, {})
    return {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}


def diff_report(current: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    """Return a diff report comparing ``current`` metrics with the baseline."""
    baseline = load_baseline()
    report: Dict[str, Dict[str, float]] = {}
    for key, base_val in baseline.items():
        cur_val = current.get(key)
        if cur_val is None:
            continue
        report[key] = {
            "baseline": base_val,
            "current": cur_val,
            "delta": cur_val - base_val,
        }
    report["similarity"] = similarity_score(
        {k: round(v, 3) for k, v in baseline.items()},
        {k: round(current.get(k, 0.0), 3) for k in baseline.keys()},
    )
    return report


def periodic_metrics_check(agent, current: Dict[str, float], *, interval: timedelta = DEFAULT_INTERVAL) -> None:
    """Log metric differences at most once per ``interval`` for ``agent``."""
    now = datetime.utcnow()
    last: datetime | None = getattr(agent, "_last_metrics_check", None)
    if last and now - last < interval:
        return
    report = diff_report(current)
    logging.info("Instance diff for %s: %s", getattr(agent, "idp_metadata", {}).get("instance_name", "agent"), report)
    agent._last_metrics_check = now
