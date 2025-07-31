from __future__ import annotations

"""Utility class for generating and validating seed tokens."""

from typing import Dict, List


class SeedToken:
    """Token metadata for seed generation and continuity checks."""

    def __init__(self, id: str, model: str, timestamp: str,
                 alignment_profile: str, hash: str,
                 chain_hash: str = "") -> None:
        self.id = id
        self.model = model
        self.timestamp = timestamp
        self.alignment_profile = alignment_profile
        self.hash = hash
        self.chain_hash = chain_hash

    @classmethod
    def generate(cls, data: dict) -> "SeedToken":
        """Return a SeedToken generated from ``data``."""
        return cls(
            data.get("id", ""),
            data.get("model", ""),
            data.get("timestamp", ""),
            data.get("alignment_profile", ""),
            data.get("hash", ""),
            data.get("chain_hash", ""),
        )

    def validate(self, other_token: "SeedToken") -> bool:
        """Return True if token matches ``other_token`` on key fields."""
        return (
            self.id == other_token.id
            and self.alignment_profile == other_token.alignment_profile
            and self.hash == other_token.hash
            and self.chain_hash == other_token.chain_hash
        )

    def verify_chain(self, ledger: Dict[str, str]) -> bool:
        """Return True if ``chain_hash`` matches an entry in ``ledger``."""
        return ledger.get(self.id) == self.chain_hash

    def detect_anomaly(self, previous_tokens: List["SeedToken"]) -> bool:
        """Return True if potential tampering is detected."""
        for token in previous_tokens:
            if token.id == self.id and token.chain_hash != self.chain_hash:
                return True
            if token.timestamp > self.timestamp:
                return True
        return False

    def to_dict(self) -> dict:
        """Return dictionary representation of this token."""
        return {
            "id": self.id,
            "model": self.model,
            "timestamp": self.timestamp,
            "alignment_profile": self.alignment_profile,
            "hash": self.hash,
            "chain_hash": self.chain_hash,
        }


__all__ = ["SeedToken"]
