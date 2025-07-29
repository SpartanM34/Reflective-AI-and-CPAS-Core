from __future__ import annotations

"""Utilities for persisting Dynamic Knowledge Anchor (DKA) digests."""

from pathlib import Path
from typing import List, Dict
from datetime import datetime
import json
import hashlib
import uuid

# Default directory for storing digests
DIGEST_DIR = Path("docs/examples/dka_digests")


def _iso_now() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def generate_digest(session_state: Dict) -> Dict:
    """Return a digest dictionary for ``session_state`` following the spec."""
    now = _iso_now()
    digest = {
        "digest_version": "1.0",
        "digest_id": f"DKA_{uuid.uuid4()}",
        "creation_timestamp": now,
        "last_modified": now,
        "participating_instances": session_state.get("participating_instances", []),
        "core_metaphor": session_state.get("core_metaphor", {}),
        "confidence_gradient": session_state.get("confidence_gradient", {}),
        "assumption_tree": session_state.get("assumption_tree", {}),
        "evolution_history": session_state.get("evolution_history", []),
        "contested_zones": session_state.get("contested_zones", []),
        "temporal_metadata": session_state.get("temporal_metadata", {}),
        "inter_dka_linkages": session_state.get("inter_dka_linkages", []),
        "rehydration_instructions": session_state.get("rehydration_instructions", {}),
    }
    return digest


def _compute_hash(data: Dict) -> str:
    """Return SHA256 hash for ``data`` serialized as JSON."""
    dumped = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(dumped).hexdigest()


def store_digest(digest: Dict, path: Path = DIGEST_DIR) -> Path:
    """Store ``digest`` as JSON in ``path`` and return the file path."""
    path.mkdir(parents=True, exist_ok=True)
    digest_no_hash = dict(digest)
    digest_hash = _compute_hash(digest_no_hash)
    digest_no_hash["hash"] = digest_hash
    file_path = path / f"{digest_no_hash['digest_id']}.json"
    file_path.write_text(json.dumps(digest_no_hash, indent=2, sort_keys=True))
    return file_path


def retrieve_digests(context: Dict, path: Path = DIGEST_DIR) -> List[Dict]:
    """Return list of digests relevant to ``context`` from ``path``."""
    digests = []
    if not path.exists():
        return digests
    instances = set(context.get("instances", []))
    for file in path.glob("*.json"):
        try:
            data = json.loads(file.read_text())
        except Exception:
            continue
        parts = set(data.get("participating_instances", []))
        if not instances or parts & instances:
            digests.append(data)
    digests.sort(key=lambda d: d.get("creation_timestamp", ""), reverse=True)
    return digests


def rehydrate_context(digests: List[Dict], current_context: Dict) -> Dict:
    """Return ``current_context`` updated with rehydration data from ``digests``."""
    context = {**current_context}
    prompts = list(context.get("prompts", []))
    priority = list(context.get("priority_concepts", []))
    for digest in digests:
        inst = digest.get("rehydration_instructions", {})
        prompts.extend(inst.get("initialization_prompts", []))
        priority.extend(inst.get("priority_concepts", []))
    if prompts:
        context["prompts"] = prompts
    if priority:
        context["priority_concepts"] = priority
    context.setdefault("rehydrated_digests", []).extend(digests)
    return context


__all__ = [
    "generate_digest",
    "store_digest",
    "retrieve_digests",
    "rehydrate_context",
    "DIGEST_DIR",
]
