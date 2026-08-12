#!/usr/bin/env python3
"""Verify an existing CPAS SQLite DKA-E store without modifying its records."""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import sys
from pathlib import Path
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cpas.dka_store import StoreContext  # noqa: E402
from cpas.sqlite_dka_store import SQLiteDKAStore  # noqa: E402


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Verify profile settings, SQLite structure, every DKA digest/head, "
            "tombstones, and the audit chain for an existing tenant store."
        )
    )
    result.add_argument("database", type=Path, help="existing SQLite store path")
    result.add_argument("--tenant", required=True, help="expected tenant binding")
    result.add_argument(
        "--local-filesystem-affirmed",
        action="store_true",
        help="affirm that the path is on the same host and a local filesystem",
    )
    result.add_argument("--json", action="store_true", help="emit JSON only")
    return result


def run(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if not arguments.local_filesystem_affirmed:
        parser().error(
            "--local-filesystem-affirmed is required; the library cannot attest mount topology"
        )
    if not arguments.database.is_file():
        parser().error("database must be an existing regular file")
    context = StoreContext(
        tenant_id=arguments.tenant,
        principal_id="operator:verify-sqlite-dka-store",
        permissions=frozenset({"dka:verify"}),
        authentication_ref="local-operator-context",
        authorization_ref="local-maintenance-invocation",
        request_id="verify-sqlite-dka-store",
        purpose="integrity-verification",
    )
    try:
        store = SQLiteDKAStore(
            arguments.database,
            tenant_id=arguments.tenant,
            local_filesystem=True,
        )
        report = {
            "passed": True,
            "environment": {
                "python": platform.python_version(),
                "sqlite": sqlite3.sqlite_version,
                "platform": platform.platform(),
            },
            "database": str(arguments.database.resolve()),
            "verification": store.verify(context=context),
            "limitations": [
                "local filesystem status was operator-affirmed, not attested",
                "verification does not test authentication, encryption, backup retention, or host hardening",
                "unkeyed audit digests are not signatures or tamper-proof logging",
            ],
        }
    except Exception as exc:  # CLI boundary returns a stable non-zero result.
        report = {
            "passed": False,
            "environment": {
                "python": platform.python_version(),
                "sqlite": sqlite3.sqlite_version,
                "platform": platform.platform(),
            },
            "database": str(arguments.database),
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }
    if arguments.json:
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
