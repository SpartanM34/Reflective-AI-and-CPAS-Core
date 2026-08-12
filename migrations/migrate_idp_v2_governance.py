#!/usr/bin/env python3
"""Add proposed governance to a pre-governance IDP v2 draft."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cpas.idp import migrate_idp_v2_draft_governance_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="pre-governance IDP v2 JSON file")
    parser.add_argument("output", type=Path, help="new governed draft JSON file")
    parser.add_argument("--maintainer", help="override provenance maintainer metadata")
    parser.add_argument(
        "--migrated-at",
        help="fixed RFC 3339 date-time for reproducible output",
    )
    parser.add_argument("--force", action="store_true", help="replace existing output")
    parser.add_argument("--dry-run", action="store_true", help="validate without writing")
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"source is not a file: {args.source}")
    if args.source.resolve() == args.output.resolve():
        parser.error("source and output must differ; migration is non-destructive")

    migrated = migrate_idp_v2_draft_governance_file(
        args.source,
        migrated_at=args.migrated_at,
        maintainer=args.maintainer,
    )
    if args.dry_run:
        print(f"validated {args.source} -> {args.output}")
        return 0
    if args.output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {args.output}; use --force")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            migrated,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
