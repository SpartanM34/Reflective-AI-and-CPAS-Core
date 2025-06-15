from __future__ import annotations

"""Utility class for generating and validating seed tokens."""


class SeedToken:
    """Token metadata for seed generation."""

    def __init__(self, id: str, model: str, timestamp: str,
                 alignment_profile: str, hash: str) -> None:
        self.id = id
        self.model = model
        self.timestamp = timestamp
        self.alignment_profile = alignment_profile
        self.hash = hash

    @classmethod
    def generate(cls, data: dict) -> "SeedToken":
        """Return a SeedToken generated from ``data``."""
        return cls(
            data.get("id", ""),
            data.get("model", ""),
            data.get("timestamp", ""),
            data.get("alignment_profile", ""),
            data.get("hash", "")
        )

    def validate(self, other_token: "SeedToken") -> bool:
        """Return True if token matches ``other_token`` on key fields."""
        return (
            self.id == other_token.id
            and self.alignment_profile == other_token.alignment_profile
            and self.hash == other_token.hash
        )

    def to_dict(self) -> dict:
        """Return dictionary representation of this token."""
        return {
            "id": self.id,
            "model": self.model,
            "timestamp": self.timestamp,
            "alignment_profile": self.alignment_profile,
            "hash": self.hash,
        }


__all__ = ["SeedToken"]
