#!/usr/bin/env python3
"""Create review-required IDP v2 drafts without changing v1 sources."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cpas.idp import migrate_idp_file
from cpas.provenance import load_json


def candidates(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    result: list[Path] = []
    for path in source.rglob("*.json"):
        try:
            value = load_json(path)
        except (OSError, ValueError):
            continue
        if isinstance(value, dict) and value.get("idp_version") == "1.0":
            result.append(path)
    return sorted(result)


def destination_for(source_root: Path, source_file: Path, output: Path) -> Path:
    if source_root.is_file():
        return output
    relative = source_file.relative_to(source_root)
    return output / relative.with_name(relative.stem + "-idp-v2.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="v1 JSON file or directory")
    parser.add_argument("output", type=Path, help="v2 JSON file or output directory")
    parser.add_argument("--source-revision", default="unrecorded")
    parser.add_argument("--maintainer", default="unassigned")
    parser.add_argument("--migrated-at", help="fixed RFC 3339 date-time for reproducible output")
    parser.add_argument("--force", action="store_true", help="replace existing generated output")
    parser.add_argument("--dry-run", action="store_true", help="validate migration without writing")
    args = parser.parse_args()

    if not args.source.exists():
        parser.error(f"source does not exist: {args.source}")
    files = candidates(args.source)
    if not files:
        parser.error("no IDP v1 JSON documents found")

    for source_file in files:
        target = destination_for(args.source, source_file, args.output)
        migrated = migrate_idp_file(
            source_file,
            source_revision=args.source_revision,
            migrated_at=args.migrated_at,
            maintainer=args.maintainer,
        )
        if args.dry_run:
            print(f"validated {source_file} -> {target}")
            continue
        if target.exists() and not args.force:
            raise SystemExit(f"refusing to overwrite {target}; use --force")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(migrated, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
