#!/usr/bin/env python3
"""Compare two CPAS runtime transcripts under a versioned evaluation manifest."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cpas.evaluation import (  # noqa: E402
    compare_runtime_transcripts,
    validate_manifest,
    validate_transcript,
)
from cpas.provenance import load_json  # noqa: E402
from cpas.runtime import TranscriptRuntimeAdapter  # noqa: E402


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", type=Path, required=True)
    result.add_argument("--baseline", type=Path, required=True)
    result.add_argument("--candidate", type=Path, required=True)
    result.add_argument(
        "--declaration",
        type=Path,
        help="declaration artifact; defaults to the manifest path under the repository root",
    )
    result.add_argument(
        "--evaluated-at",
        help="RFC 3339 timestamp; supply this for byte-reproducible reports",
    )
    result.add_argument("--output", type=Path, help="write the complete report atomically")
    result.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing output path (never enabled by default)",
    )
    return result


def _object(path: Path, label: str) -> dict:
    value = load_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _default_declaration(manifest: dict) -> Path:
    candidate = (REPOSITORY_ROOT / manifest["declaration"]["path"]).resolve()
    try:
        candidate.relative_to(REPOSITORY_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("manifest declaration path escapes the repository") from exc
    return candidate


def _write_atomic(path: Path, report: dict, *, overwrite: bool) -> None:
    parent = path.parent.resolve()
    if not parent.is_dir():
        raise ValueError(f"output parent is not an existing directory: {parent}")
    target = parent / path.name
    if target.is_symlink():
        raise ValueError(f"output must not be a symbolic link: {target}")
    if target.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {target}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(report, handle, sort_keys=True, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists() and not overwrite:
            raise FileExistsError(f"output appeared during write: {target}")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def run(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    manifest = _object(arguments.manifest, "manifest")
    baseline = _object(arguments.baseline, "baseline transcript")
    candidate = _object(arguments.candidate, "candidate transcript")
    validate_manifest(manifest)
    validate_transcript(baseline)
    validate_transcript(candidate)
    declaration_path = arguments.declaration or _default_declaration(manifest)
    declaration = _object(declaration_path, "declaration")
    report = compare_runtime_transcripts(
        manifest,
        declaration,
        baseline,
        candidate,
        TranscriptRuntimeAdapter(baseline),
        TranscriptRuntimeAdapter(candidate),
        evaluated_at=arguments.evaluated_at,
        declaration_path=declaration_path,
    )
    if arguments.output:
        _write_atomic(arguments.output, report, overwrite=arguments.overwrite)
        emitted = {
            "output": str(arguments.output),
            "report_digest": report["integrity"]["digest"],
            "machine_disposition": report["threshold_evaluation"][
                "machine_disposition"
            ],
            "evaluation_purpose": report["assurance_assessment"][
                "evaluation_purpose"
            ],
            "human_review_status": report["human_review"]["status"],
            "final_disposition": report["final_disposition"],
        }
        print(json.dumps(emitted, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    try:
        return run()
    except Exception as exc:
        print(f"runtime evaluation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
