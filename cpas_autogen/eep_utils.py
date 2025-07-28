from __future__ import annotations

"""Helper utilities for the Epistemic Exchange Protocol (EEP)."""

from typing import Any, Sequence
import logging
import requests


def broadcast_state(agent: Any, state: dict, *, thread_token: str,
                    api_url: str = "http://localhost:5000/api/v1/messages") -> bool:
    """Broadcast ``state`` to other instances via the T-BEEP API."""
    payload = {
        "threadToken": thread_token,
        "instance": getattr(agent, "idp_metadata", {}).get("instance_name"),
        "type": "state_broadcast",
        "seedToken": getattr(agent, "seed_token", None) and agent.seed_token.to_dict(),
        "state": state,
    }
    try:
        res = requests.post(api_url, json=payload, timeout=5)
        res.raise_for_status()
        return True
    except Exception as exc:  # pragma: no cover - network issues
        logging.warning("Failed to broadcast state: %s", exc)
        return False


def request_validation(agent: Any, claim: str, *, thread_token: str, target: str = "",
                        api_url: str = "http://localhost:5000/api/v1/messages") -> bool:
    """Request cross-instance validation for ``claim``."""
    payload = {
        "threadToken": thread_token,
        "instance": getattr(agent, "idp_metadata", {}).get("instance_name"),
        "type": "validation_request",
        "claim": claim,
        "target": target,
        "seedToken": getattr(agent, "seed_token", None) and agent.seed_token.to_dict(),
    }
    try:
        res = requests.post(api_url, json=payload, timeout=5)
        res.raise_for_status()
        return True
    except Exception as exc:  # pragma: no cover - network issues
        logging.warning("Failed to request validation: %s", exc)
        return False


def start_collab_session(agent: Any, participants: Sequence[str], *, thread_token: str,
                          topic: str = "",
                          api_url: str = "http://localhost:5000/api/v1/messages") -> bool:
    """Announce a collaborative reasoning session with ``participants``."""
    payload = {
        "threadToken": thread_token,
        "instance": getattr(agent, "idp_metadata", {}).get("instance_name"),
        "type": "collab_session",
        "participants": list(participants),
        "topic": topic,
        "seedToken": getattr(agent, "seed_token", None) and agent.seed_token.to_dict(),
    }
    try:
        res = requests.post(api_url, json=payload, timeout=5)
        res.raise_for_status()
        return True
    except Exception as exc:  # pragma: no cover - network issues
        logging.warning("Failed to start collaboration session: %s", exc)
        return False


__all__ = [
    "broadcast_state",
    "request_validation",
    "start_collab_session",
]
