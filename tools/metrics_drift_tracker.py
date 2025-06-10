#!/usr/bin/env python3
"""Temporal Drift Tracker
========================

Usage:
  python tools/metrics_drift_tracker.py [--log PATH] [--output PATH] [--plot]

This script reads a monitoring log (default: tools/monitor_log.json) containing
timestamped live metrics:
 - interpretive_bandwidth
 - symbolic_density
 - divergence_space

It performs sliding window analysis over 7-day and 30-day intervals to detect
changes in interpretive flexibility. A "Flexibility Pulse" score represents the
short-term trend relative to the longer baseline. Results are saved to
``tools/drift_tracker_log.json`` and an optional plot may be displayed.
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

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


def average(entries):
  """Compute average metrics for a list of entries."""
  if not entries:
    return {m: 0 for m in METRICS}
  result = {m: 0.0 for m in METRICS}
  for e in entries:
    for m in METRICS:
      result[m] += e.get(m, 0)
  count = len(entries)
  return {m: result[m] / count for m in METRICS}


def analyze(entries):
  """Return trend data with 7-day, 30-day averages and flexibility pulse."""
  results = []
  for entry in entries:
    t = entry["timestamp"]
    win7 = [e for e in entries if t - timedelta(days=7) <= e["timestamp"] <= t]
    win30 = [e for e in entries if t - timedelta(days=30) <= e["timestamp"] <= t]
    avg7 = average(win7)
    avg30 = average(win30)

    pulse = sum((avg7[m] - avg30[m]) for m in METRICS) / len(METRICS)

    results.append({
        "timestamp": t.isoformat(),
        "avg_7_day": avg7,
        "avg_30_day": avg30,
        "flexibility_pulse": pulse
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
  parser.add_argument("--log", default="tools/monitor_log.json",
                      help="Path to monitor_log.json")
  parser.add_argument("--output", default="tools/drift_tracker_log.json",
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
  print(f"Drift data written to {args.output}")

  if args.plot:
    plot_pulse(results)


if __name__ == "__main__":
  main()
