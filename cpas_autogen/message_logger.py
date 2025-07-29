from __future__ import annotations

"""Utilities for logging agent messages to a manifest file."""

import json
from datetime import datetime
from pathlib import Path


# Default manifest path and size limit (~50KB)
MANIFEST_FILE = Path("examples/message_manifest.json")
MAX_MANIFEST_SIZE = 50_000


_BASE_MANIFEST = {
    "schema_version": "1.0",
    "description": "Manifest for logging and validating message continuity.",
    "message_schema": {
        "type": "object",
        "required": [
            "threadToken",
            "timestamp",
            "instance",
            "seedToken",
            "contentHash",
            "fingerprint",
        ],
        "properties": {
            "threadToken": {"type": "string", "description": "Conversation thread token"},
            "timestamp": {"type": "string", "format": "date-time"},
            "instance": {"type": "string", "description": "Generating instance"},
            "seedToken": {"type": "string", "description": "Seed for deterministic runs"},
            "contentHash": {"type": "string", "description": "Hash of message content"},
            "fingerprint": {"type": "string", "description": "Unique message fingerprint"},
        },
    },
    "messages": [],
}


def _iso_now() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _init_manifest(path: Path) -> None:
    """Create a new manifest file at ``path`` if it doesn't exist."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_BASE_MANIFEST, indent=2))


def _rotate_manifest(path: Path) -> None:
    """Rotate ``path`` to a timestamped file and start a new manifest."""
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    archive = path.with_name(f"{path.stem}-{timestamp}{path.suffix}")
    path.rename(archive)
    path.write_text(json.dumps(_BASE_MANIFEST, indent=2))


def log_message(thread_token: str, timestamp: str, instance: str, seed_token: str,
                content_hash: str, fingerprint: str) -> None:
    """Append a message entry to the manifest and rotate if needed."""
    path = MANIFEST_FILE
    _init_manifest(path)
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            data = dict(_BASE_MANIFEST)
            data["messages"] = []
    except Exception:
        data = dict(_BASE_MANIFEST)
        data["messages"] = []
    entry = {
        "threadToken": thread_token,
        "timestamp": timestamp,
        "instance": instance,
        "seedToken": seed_token,
        "contentHash": content_hash,
        "fingerprint": fingerprint,
    }
    data.setdefault("messages", []).append(entry)
    content = json.dumps(data, indent=2)
    if len(content.encode("utf-8")) > MAX_MANIFEST_SIZE:
        _rotate_manifest(path)
        data = dict(_BASE_MANIFEST)
        data["messages"] = [entry]
        content = json.dumps(data, indent=2)
    path.write_text(content)


__all__ = ["log_message", "MANIFEST_FILE", "MAX_MANIFEST_SIZE"]
