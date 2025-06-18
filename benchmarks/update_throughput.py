from __future__ import annotations

"""Benchmark script for measuring update throughput of the T-BEEP API."""

import json
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.tbeep_api import app


def benchmark(count: int = 100) -> dict[str, float]:
    client = app.test_client()
    payload = {
        "threadToken": "#BENCH_001.0",
        "instance": "Bench",
        "reasoningLevel": "Basic",
        "confidence": "High",
        "collaborationMode": "Benchmark",
        "timestamp": "2025-01-01T00:00:00Z",
        "version": "#BENCH.v1.0",
        "content": "x",
    }
    start = time.perf_counter()
    for _ in range(count):
        client.post("/api/v1/messages", json=payload)
    elapsed = time.perf_counter() - start
    ups = count / elapsed if elapsed else 0.0
    return {"updates": count, "seconds": elapsed, "updates_per_second": ups}


def main() -> None:
    result = benchmark()
    out = Path(__file__).with_name('results.log')
    with out.open('a', encoding='utf-8') as f:
        f.write(json.dumps({"update_throughput": result}) + '\n')
    print(result)


if __name__ == '__main__':
    main()
