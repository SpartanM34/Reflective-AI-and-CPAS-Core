#!/usr/bin/env python3
"""Wonder Signal Recorder
=======================

Usage:
  python tools/record_wonder.py "My reflection" [--file PATH]

Append a short reflection with a UTC timestamp to ``wonder_signals.json``. Each
entry is stored as ``{"timestamp": ..., "text": ...}``.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
import json

DEFAULT_FILE = Path("docs/examples/wonder_signals.json")


def main() -> None:
    parser = ArgumentParser(description="Record a brief wonder signal")
    parser.add_argument("text", help="Reflection text")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help="Output file path")
    args = parser.parse_args()

    path = args.file
    path.parent.mkdir(parents=True, exist_ok=True)

    data = []
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, list):
                data = []
        except Exception:
            data = []

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "text": args.text.strip(),
    }
    data.append(entry)
    path.write_text(json.dumps(data, indent=2))
    print(f"Appended to {path}")


if __name__ == "__main__":
    main()
