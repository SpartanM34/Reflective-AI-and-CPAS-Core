# Benchmark Suite

This directory contains simple benchmark scripts for CPAS-Core.

- `hardware_specs.py` records hardware and environment information.
- `token_processing.py` measures token processing speed using spaCy.
- `update_throughput.py` measures how quickly the T-BEEP API can store messages.
- `run_all.py` executes all benchmarks in sequence and appends results to `results.log`.

Run the suite with:

```bash
python benchmarks/run_all.py
```

Results are appended to `results.log` in JSON-lines format.
