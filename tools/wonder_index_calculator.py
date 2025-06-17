#!/usr/bin/env python3
"""Wonder Index Calculator
=======================

Usage:
  python tools/wonder_index_calculator.py [--drift DRIFT_LOG] [--div DIV_LOG]
                                         [--signals SIGNALS_JSON]
                                         [--output OUT_FILE] [--plot]

This script synthesizes interpretive metrics from the drift tracker,
instance divergence log, and optional Wonder Signals to produce a
composite Wonder Index (0-1) for each timestamp. Metrics are
min-max normalised and averaged. Optionally a matplotlib plot of the
index trend is displayed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime

from typing import Dict, List

try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # matplotlib optional
    plt = None


MetricDict = Dict[str, float]


def load_drift(path: Path) -> Dict[str, MetricDict]:
    """Load 7-day averages from drift tracker log."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    result: Dict[str, MetricDict] = {}
    for entry in data:
        ts = entry.get("timestamp")
        avg = entry.get("avg_7_day", {})
        if ts:
            result[ts] = {
                "interpretive_bandwidth": avg.get("interpretive_bandwidth"),
                "symbolic_density": avg.get("symbolic_density"),
                "divergence": avg.get("divergence_space"),
            }
    return result


def load_divergence(path: Path) -> Dict[str, MetricDict]:
    """Return divergence metric averaged across matrix values."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    result: Dict[str, MetricDict] = {}
    for entry in data:
        ts = entry.get("timestamp")
        matrix = entry.get("matrix")
        if ts and matrix:
            n = len(matrix)
            values: List[float] = []
            for i in range(n):
                for j in range(i + 1, n):
                    values.append(matrix[i][j])
            avg = sum(values) / len(values) if values else 0.0
            result[ts] = {"divergence": avg}
    return result


def load_wonder_signals(path: Path) -> Dict[str, MetricDict]:
    """Load optional Wonder Signals JSON (timestamp -> value)."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    result: Dict[str, MetricDict] = {}
    for entry in data:
        ts = entry.get("timestamp")
        val = entry.get("wonder_signal")
        if ts and val is not None:
            result[ts] = {"wonder_signal": float(val)}
    return result


def combine_metrics(*sources: Dict[str, MetricDict]) -> Dict[str, MetricDict]:
    """Merge metric dictionaries keyed by timestamp."""
    combined: Dict[str, MetricDict] = {}
    for source in sources:
        for ts, metrics in source.items():
            combined.setdefault(ts, {}).update(metrics)
    return combined


def normalise(entries: Dict[str, MetricDict]) -> Dict[str, MetricDict]:
    """Min-max normalise metrics across all timestamps."""
    metrics = {m for v in entries.values() for m in v}
    ranges: Dict[str, tuple[float, float]] = {}
    for m in metrics:
        values = [v[m] for v in entries.values() if m in v and v[m] is not None]
        if not values:
            continue
        ranges[m] = (min(values), max(values))
    normed: Dict[str, MetricDict] = {}
    for ts, vals in entries.items():
        normed_vals: MetricDict = {}
        for m, value in vals.items():
            low, high = ranges.get(m, (0.0, 0.0))
            if high != low:
                normed_vals[m] = (value - low) / (high - low)
            else:
                normed_vals[m] = 0.0
        normed[ts] = normed_vals
    return normed


def compute_wonder_index(normed: Dict[str, MetricDict]) -> List[dict]:
    """Return sorted list of entries with Wonder Index."""
    results = []
    for ts, metrics in normed.items():
        values = [v for v in metrics.values() if v is not None]
        index = sum(values) / len(values) if values else 0.0
        result = {
            "timestamp": ts,
            **{f"{k}_norm": v for k, v in metrics.items()},
            "wonder_index": index,
        }
        results.append(result)
    results.sort(key=lambda x: x["timestamp"])
    return results


def save_results(results: List[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def plot_index(results: List[dict]) -> None:
    if plt is None:
        print("Matplotlib not available; skipping plot.")
        return
    times = [datetime.fromisoformat(r["timestamp"]) for r in results]
    values = [r["wonder_index"] for r in results]
    plt.figure(figsize=(10, 4))
    plt.plot(times, values, marker="o")
    plt.xlabel("Time")
    plt.ylabel("Wonder Index")
    plt.title("Wonder Index Trend")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Wonder Index")
    parser.add_argument("--drift", default="docs/examples/drift_tracker_log.json")
    parser.add_argument("--div", default="docs/examples/divergence_log.json")
    parser.add_argument("--signals", default="docs/examples/wonder_signals.json")
    parser.add_argument("--output", default="docs/examples/wonder_index_log.json")
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()

    drift = load_drift(Path(args.drift))
    divergence = load_divergence(Path(args.div))
    signals = load_wonder_signals(Path(args.signals))

    combined = combine_metrics(drift, divergence, signals)
    normed = normalise(combined)
    results = compute_wonder_index(normed)

    save_results(results, Path(args.output))
    print(f"Wonder Index written to {args.output}")

    if args.plot:
        plot_index(results)


if __name__ == "__main__":
    main()
