from __future__ import annotations

"""Seed token comparison utilities."""


KEY_FIELDS = ["alignment_profile", "model", "hash"]


def similarity_score(token1: dict, token2: dict) -> float:
    """Return similarity score (0.0–1.0) for shared attributes.

    The score is the fraction of shared keys whose values match. If no
    common keys exist, ``0.0`` is returned.
    """
    shared = set(token1) & set(token2)
    if not shared:
        return 0.0
    matches = sum(1 for k in shared if token1.get(k) == token2.get(k))
    return matches / len(shared)


def compare_seed_tokens(token1: dict, token2: dict) -> dict:
    """Return diff report comparing key seed token fields.

    The report details whether ``alignment_profile``, ``model`` and ``hash``
    fields match between the two tokens and includes a ``similarity`` score.
    """
    report = {}
    for field in KEY_FIELDS:
        v1 = token1.get(field)
        v2 = token2.get(field)
        report[field] = {"token1": v1, "token2": v2, "match": v1 == v2}
    report["similarity"] = similarity_score(token1, token2)
    return report


__all__ = ["compare_seed_tokens", "similarity_score"]
