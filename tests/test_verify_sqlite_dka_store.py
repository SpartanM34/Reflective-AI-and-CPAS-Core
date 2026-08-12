from __future__ import annotations

import json
from pathlib import Path

from cpas.dka_store import StoreContext
from cpas.sqlite_dka_store import SQLiteDKAStore
from tools.verify_sqlite_dka_store import run


ROOT = Path(__file__).resolve().parents[1]


def test_verify_cli_reports_an_existing_store(tmp_path, capsys):
    tenant = "verify-cli-tenant"
    database = tmp_path / "verify.db"
    store = SQLiteDKAStore(
        database, tenant_id=tenant, local_filesystem=True
    )
    context = StoreContext(
        tenant_id=tenant,
        principal_id="test-writer",
        permissions=frozenset({"dka:*"}),
        authentication_ref="test-authn",
        authorization_ref="test-authz",
        request_id="test-request",
    )
    record = json.loads(
        (ROOT / "examples/v2/dka-e-v2.example.json").read_text(encoding="utf-8")
    )
    store.put(record, expected_head=None, context=context, actor="test-writer")

    status = run(
        [
            str(database),
            "--tenant",
            tenant,
            "--local-filesystem-affirmed",
            "--json",
        ]
    )
    result = json.loads(capsys.readouterr().out)
    assert status == 0
    assert result["passed"] is True
    assert result["verification"]["snapshots"] == 1
    assert result["verification"]["profile"]["conformant"] is True
