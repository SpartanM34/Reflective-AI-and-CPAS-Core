#!/usr/bin/env python3
"""Update baseline metrics from monitoring logs.

This utility appends the most recent entries from ``monitor_log.json`` and
``drift_tracker_log.json`` to ``baseline_metrics.json``. If the live metrics
fall below the thresholds defined in ``cpas_autogen.realignment_trigger`` the
last commit is automatically reverted using ``git revert``.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from cpas_autogen.config import BASELINE_FILE, MONITOR_LOG, DRIFT_LOG
from cpas_autogen.realignment_trigger import should_realign

logging.basicConfig(level=logging.INFO, format="%(message)s")


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _latest_monitor() -> dict:
    data = _load_json(MONITOR_LOG)
    if isinstance(data, list) and data:
        last = data[-1]
        return {
            "interpretive_bandwidth": float(last.get("interpretive_bandwidth", 0)),
            "symbolic_density": float(last.get("symbolic_density", 0)),
            "divergence_space": float(last.get("divergence_space", 0)),
        }
    return {}


def _latest_drift() -> dict:
    data = _load_json(DRIFT_LOG)
    if isinstance(data, list) and data:
        last = data[-1]
        avg7 = last.get("avg_7_day", {})
        avg30 = last.get("avg_30_day", {})
        return {
            "interpretive_bandwidth_7d": float(avg7.get("interpretive_bandwidth", 0)),
            "symbolic_density_7d": float(avg7.get("symbolic_density", 0)),
            "divergence_space_7d": float(avg7.get("divergence_space", 0)),
            "interpretive_bandwidth_30d": float(avg30.get("interpretive_bandwidth", 0)),
            "symbolic_density_30d": float(avg30.get("symbolic_density", 0)),
            "divergence_space_30d": float(avg30.get("divergence_space", 0)),
            "flexibility_pulse": float(last.get("flexibility_pulse", 0)),
        }
    return {}


def _rollback(reason: str) -> None:
    logging.error("Rollback triggered: %s", reason)
    try:
        subprocess.run(["git", "revert", "--no-edit", "HEAD"], check=True)
    except subprocess.CalledProcessError as exc:
        logging.error("Automatic revert failed: %s", exc)


def main() -> None:
    monitor_metrics = _latest_monitor()
    drift_metrics = _latest_drift()

    if not monitor_metrics and not drift_metrics:
        logging.info("No metrics available; baseline not updated.")
        return

    check_metrics = {
        "symbolic_density": monitor_metrics.get("symbolic_density"),
        "interpretive_bandwidth": monitor_metrics.get("interpretive_bandwidth"),
        "divergence_score": monitor_metrics.get("divergence_space"),
    }

    if should_realign(check_metrics):
        _rollback("Metrics below thresholds")
        return

    combined = {**monitor_metrics, **drift_metrics}

    data = {}
    if BASELINE_FILE.exists():
        try:
            data = json.loads(BASELINE_FILE.read_text())
        except Exception:
            data = {}

    data[datetime.utcnow().isoformat()] = combined
    BASELINE_FILE.write_text(json.dumps(data, indent=2))
    logging.info("Baseline metrics updated.")


if __name__ == "__main__":
    main()
