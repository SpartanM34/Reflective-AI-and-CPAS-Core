#!/usr/bin/env python3
"""Wonder Signal Recorder
======================

Usage:
  python tools/record_wonder.py "My reflection" [--file PATH]

Append a short reflection to ``wonder_signals.txt`` with a UTC timestamp.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

DEFAULT_FILE = Path("docs/examples/wonder_signals.txt")


def main() -> None:
    parser = ArgumentParser(description="Record a brief wonder signal")
    parser.add_argument("text", help="Reflection text")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help="Output file path")
    args = parser.parse_args()

    path = args.file
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.utcnow().isoformat()} {args.text.strip()}\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
    print(f"Appended to {path}")


if __name__ == "__main__":
    main()
