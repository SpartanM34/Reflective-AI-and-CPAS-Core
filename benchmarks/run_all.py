from __future__ import annotations

"""Run all benchmark scripts and log results."""

import subprocess
from pathlib import Path

SCRIPTS = [
    'hardware_specs.py',
    'token_processing.py',
    'update_throughput.py',
]


def main() -> None:
    bench_dir = Path(__file__).resolve().parent
    for name in SCRIPTS:
        subprocess.run(['python', str(bench_dir / name)], check=True)


if __name__ == '__main__':
    main()
