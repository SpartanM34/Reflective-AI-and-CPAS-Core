from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.validate_cpas_v2 import (
    ValidationFailure,
    require_file_digest,
    validate_local_links,
    validate_repository,
)


ROOT = Path(__file__).resolve().parents[1]


def test_repository_validation_contract_passes():
    report = validate_repository(ROOT)
    assert report.schemas == 8
    assert report.instances == 9
    assert report.digest_references >= 9
    assert report.markdown_links > 0
    assert report.migrated_idps == 28
    assert report.canonicalization_vector_checks == 17
    assert report.runtime_evaluation_checks == 19


def test_cross_file_digest_mismatch_is_rejected(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("reviewed content\n", encoding="utf-8")
    with pytest.raises(ValidationFailure, match="digest mismatch"):
        require_file_digest(
            tmp_path,
            "artifact.txt",
            "sha256:" + "0" * 64,
            owner="test provenance",
        )


def test_broken_modernization_link_is_rejected(tmp_path):
    document = tmp_path / "index.md"
    document.write_text("[missing](not-present.md)\n", encoding="utf-8")
    with pytest.raises(ValidationFailure, match="broken local link"):
        validate_local_links(tmp_path, [document])


def test_json_cli_report_is_machine_readable():
    result = subprocess.run(
        [sys.executable, "tools/validate_cpas_v2.py", "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    assert report["schemas"] == 8
    assert report["migrated_idps"] == 28
    assert report["canonicalization_vector_checks"] == 17
    assert report["runtime_evaluation_checks"] == 19
