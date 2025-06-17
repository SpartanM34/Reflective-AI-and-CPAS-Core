from __future__ import annotations

"""Epistemic fingerprint generation utilities."""

from datetime import datetime
import hashlib


def generate_fingerprint(prompt: str, seed_token: dict) -> dict:
    """Return fingerprint metadata for the given ``prompt`` and ``seed_token``.

    The fingerprint is an SHA-256 hash of the prompt text combined with the
    model name and alignment profile from ``seed_token``. The result can be
    used to compare reasoning traces across sessions or tools.
    """
    model = seed_token.get("model", "")
    alignment = seed_token.get("alignment_profile", "")

    sha = hashlib.sha256()
    sha.update(prompt.encode("utf-8"))
    sha.update(model.encode("utf-8"))
    sha.update(alignment.encode("utf-8"))
    digest = sha.hexdigest()

    return {
        "fingerprint": digest,
        "timestamp": datetime.utcnow().isoformat(),
        "prompt": prompt,
        "model": model,
        "alignment_profile": alignment,
    }


__all__ = ["generate_fingerprint"]
