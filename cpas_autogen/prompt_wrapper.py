from __future__ import annotations

"""Utility for wrapping prompts with seed token metadata."""


def wrap_with_seed_token(prompt: str, seed_token: dict) -> str:
    """Return ``prompt`` prefixed by seed token header and realignment notice."""
    header_lines = [
        "### Seed Instance",
        f"ID: {seed_token.get('id', '')}",
        f"Model: {seed_token.get('model', '')}",
        f"Timestamp: {seed_token.get('timestamp', '')}",
        f"Alignment: {seed_token.get('alignment_profile', '')}",
        f"Hash: {seed_token.get('hash', '')}",
        "",
        "**CPAS-Core v1.1 Realignment Notice**",
        "This session realigns the instance with CPAS-Core v1.1 protocols.",
        "Confirm identity and compliance before proceeding.",
        "",
    ]
    return "\n".join(header_lines) + prompt


__all__ = ["wrap_with_seed_token"]
