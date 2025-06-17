from __future__ import annotations

"""Token continuity verification utilities."""

import logging

EXPECTED_PROFILE = "CPAS-Core v1.1"
THREAD_PREFIX = "#COMM_PROTO"


def continuity_check(seed_token: dict, thread_token: str) -> bool:
    """Return ``True`` if alignment profile and thread token prefix match.

    Parameters
    ----------
    seed_token : dict
        Seed token metadata.
    thread_token : str
        Thread token string to validate.
    """
    ok = True
    alignment = seed_token.get("alignment_profile", "")
    if alignment != EXPECTED_PROFILE:
        logging.warning(
            "Seed token alignment '%s' does not match expected '%s'",
            alignment,
            EXPECTED_PROFILE,
        )
        ok = False
    if not thread_token.startswith(THREAD_PREFIX):
        logging.warning(
            "Thread token '%s' does not start with expected prefix '%s'",
            thread_token,
            THREAD_PREFIX,
        )
        ok = False
    return ok


__all__ = ["continuity_check", "EXPECTED_PROFILE", "THREAD_PREFIX"]
