from __future__ import annotations

"""Utility for wrapping prompts with seed token metadata."""

import hashlib
import json


def compute_signature(prompt: str, seed_token: dict) -> str:
    """Return SHA-256 hex digest of ``prompt`` and ``seed_token``."""
    sha = hashlib.sha256()
    sha.update(prompt.encode("utf-8"))
    sha.update(json.dumps(seed_token, sort_keys=True).encode("utf-8"))
    return sha.hexdigest()


def wrap_with_seed_token(prompt: str, seed_token: dict) -> str:
    """Return ``prompt`` prefixed by seed token header and realignment notice."""
    signature = compute_signature(prompt, seed_token)
    header_lines = [
        "### Seed Instance",
        f"ID: {seed_token.get('id', '')}",
        f"Model: {seed_token.get('model', '')}",
        f"Timestamp: {seed_token.get('timestamp', '')}",
        f"Alignment: {seed_token.get('alignment_profile', '')}",
        f"Hash: {seed_token.get('hash', '')}",
        f"Signature: {signature}",
        "",
        "**CPAS-Core v1.1 Realignment Notice**",
        "This session realigns the instance with CPAS-Core v1.1 protocols.",
        "Confirm identity and compliance before proceeding.",
        "",
    ]
    return "\n".join(header_lines) + prompt


__all__ = ["wrap_with_seed_token", "compute_signature"]
