#!/usr/bin/env python3
"""Append session metrics to monitoring logs.

Usage:
  python tools/update_metrics.py SESSION_METRICS.json

SESSION_METRICS.json should contain keys ``interpretive_bandwidth``,
``symbolic_density`` and ``divergence_space``. The script appends the
metrics to ``docs/examples/monitor_log.json`` and updates
drift metrics in ``docs/examples/drift_tracker_log.json``. Baseline
values are refreshed via ``tools/update_baselines.py``.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from cpas_autogen.config import MONITOR_LOG, DRIFT_LOG
from tools.metrics_drift_tracker import load_log, analyze
from tools.update_baselines import main as update_baselines_main


MetricDict = Dict[str, float]


def load_metrics(path: Path) -> MetricDict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "interpretive_bandwidth": float(data.get("interpretive_bandwidth", 0)),
        "symbolic_density": float(data.get("symbolic_density", 0)),
        "divergence_space": float(data.get("divergence_space", 0)),
    }


def append_monitor(entry: Dict[str, float]) -> None:
    log: List[dict] = []
    if MONITOR_LOG.exists():
        try:
            log = json.loads(MONITOR_LOG.read_text())
            if not isinstance(log, list):
                log = []
        except Exception:
            log = []
    log.append(entry)
    MONITOR_LOG.write_text(json.dumps(log, indent=2))


def append_drift() -> None:
    entries = load_log(MONITOR_LOG)
    results = analyze(entries)
    if not results:
        return
    last = results[-1]
    drift_entry = {
        "timestamp": last["timestamp"],
        "avg_7_day": {
            "interpretive_bandwidth": last["interpretive_bandwidth_7d"],
            "symbolic_density": last["symbolic_density_7d"],
            "divergence_space": last["divergence_space_7d"],
        },
        "avg_30_day": {
            "interpretive_bandwidth": last["interpretive_bandwidth_30d"],
            "symbolic_density": last["symbolic_density_30d"],
            "divergence_space": last["divergence_space_30d"],
        },
        "flexibility_pulse": last["flexibility_pulse"],
    }
    data: List[dict] = []
    if DRIFT_LOG.exists():
        try:
            data = json.loads(DRIFT_LOG.read_text())
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []
    data.append(drift_entry)
    DRIFT_LOG.write_text(json.dumps(data, indent=2))


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Update monitoring logs")
    parser.add_argument("metrics", help="Path to session metrics JSON file")
    args = parser.parse_args(argv)

    metrics = load_metrics(Path(args.metrics))
    entry = {"timestamp": datetime.utcnow().isoformat(), **metrics}
    append_monitor(entry)
    append_drift()

    try:
        update_baselines_main()
    except Exception as exc:
        print(f"Failed to update baselines: {exc}")


if __name__ == "__main__":
    main()
