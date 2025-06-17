#!/usr/bin/env python3
"""Temporal Drift Tracker
========================

Usage:
  python tools/metrics_drift_tracker.py [--log PATH] [--output PATH] [--plot]

This script reads a monitoring log (default: docs/examples/monitor_log.json) containing
timestamped live metrics:
 - interpretive_bandwidth
 - symbolic_density
 - divergence_space

It performs sliding window analysis over 7-day and 30-day intervals to detect
changes in interpretive flexibility. A "Flexibility Pulse" score represents the
short-term trend relative to the longer baseline. Results are saved to
``docs/examples/drift_tracker_log.json`` and an optional plot may be displayed. Each
entry records the 7- and 30-day rolling averages for all metrics and the
resulting ``flexibility_pulse``.

Run this script after the monitoring log has been updated (e.g. via
``monitor_dkae.py``). 7-day and 30-day rolling averages are computed with
``pandas`` and the Flexibility Pulse is plotted if ``--plot`` is passed.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
  import matplotlib.pyplot as plt
except Exception:  # matplotlib is optional
  plt = None


METRICS = ["interpretive_bandwidth", "symbolic_density", "divergence_space"]


def load_log(path: Path):
  """Load monitoring data and parse timestamps."""
  with path.open() as f:
    data = json.load(f)

  for entry in data:
    entry["timestamp"] = datetime.fromisoformat(entry["timestamp"])
  data.sort(key=lambda x: x["timestamp"])
  return data


def analyze(entries):
  """Return trend data with 7-day/30-day averages and flexibility pulse."""
  df = pd.DataFrame(entries)
  df.sort_values("timestamp", inplace=True)
  df.set_index("timestamp", inplace=True)

  rolling7 = df.rolling("7D", min_periods=1).mean()
  rolling30 = df.rolling("30D", min_periods=1).mean()

  result_df = pd.DataFrame(index=df.index)
  for metric in METRICS:
    result_df[f"{metric}_7d"] = rolling7[metric]
    result_df[f"{metric}_30d"] = rolling30[metric]

  diffs = [result_df[f"{m}_7d"] - result_df[f"{m}_30d"] for m in METRICS]
  result_df["flexibility_pulse"] = sum(diffs) / len(METRICS)

  results = []
  for ts, row in result_df.iterrows():
    results.append({
        "timestamp": ts.isoformat(),
        "interpretive_bandwidth_7d": row["interpretive_bandwidth_7d"],
        "interpretive_bandwidth_30d": row["interpretive_bandwidth_30d"],
        "symbolic_density_7d": row["symbolic_density_7d"],
        "symbolic_density_30d": row["symbolic_density_30d"],
        "divergence_space_7d": row["divergence_space_7d"],
        "divergence_space_30d": row["divergence_space_30d"],
        "flexibility_pulse": row["flexibility_pulse"],
    })
  return results


def save_results(results, path: Path):
  with path.open("w") as f:
    json.dump(results, f, indent=2)



def plot_pulse(results):
  if plt is None:
    print("Matplotlib not available; skipping plot.")
    return
  times = [datetime.fromisoformat(r["timestamp"]) for r in results]
  pulse = [r["flexibility_pulse"] for r in results]
  plt.figure(figsize=(10, 4))
  plt.plot(times, pulse, marker="o")
  plt.xlabel("Time")
  plt.ylabel("Flexibility Pulse")
  plt.title("Temporal Flexibility Pulse")
  plt.grid(True)
  plt.tight_layout()
  plt.show()


def main():
  parser = argparse.ArgumentParser(description="Temporal Drift Tracker")
  parser.add_argument("--log", default="docs/examples/monitor_log.json",
                      help="Path to monitor_log.json")
  parser.add_argument("--output", default="docs/examples/drift_tracker_log.json",
                      help="Where to store drift analysis")
  parser.add_argument("--plot", action="store_true",
                      help="Display a matplotlib plot of the pulse")
  args = parser.parse_args()

  log_path = Path(args.log)
  if not log_path.exists():
    raise FileNotFoundError(f"Monitor log not found: {log_path}")

  entries = load_log(log_path)
  results = analyze(entries)
  save_results(results, Path(args.output))
  print("Analysis complete.")
  print(f"Drift data written to {args.output}")

  if args.plot:
    plot_pulse(results)


if __name__ == "__main__":
  main()
