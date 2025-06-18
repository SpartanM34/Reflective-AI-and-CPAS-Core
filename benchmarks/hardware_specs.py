from __future__ import annotations

"""Collect basic hardware specs and environment configuration."""

import json
import platform
from pathlib import Path

try:
    import psutil
except Exception:
    psutil = None


def gather_specs() -> dict[str, str | float | int]:
    info = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
    }
    if psutil:
        info.update({
            "cpu_count": psutil.cpu_count(logical=True),
            "memory_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        })
    return info


def main() -> None:
    specs = gather_specs()
    out = Path(__file__).with_name('results.log')
    with out.open('a', encoding='utf-8') as f:
        f.write(json.dumps({"hardware_specs": specs}) + '\n')
    print(specs)


if __name__ == '__main__':
    main()
