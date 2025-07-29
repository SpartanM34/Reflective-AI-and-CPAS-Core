from __future__ import annotations

"""Simple ethical reflection profiles used by CPAS agents."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ConstitutionalEthics:
    """Check basic constraint compliance."""

    def evaluate(self, context: str) -> str:
        lowered = context.lower()
        if any(w in lowered for w in ["illegal", "forbidden", "banned"]):
            return "Potential constitutional violation detected."
        return "No constitutional issues detected."


@dataclass
class ConsequentialistEthics:
    """Consider outcomes of the proposed action."""

    def evaluate(self, context: str) -> str:
        lowered = context.lower()
        if "harm" in lowered or "risk" in lowered:
            return "Consequentialist concern: possible harm identified."
        return "Consequences appear acceptable."


@dataclass
class VirtueEthics:
    """Assess dialogue according to prosocial virtues."""

    def evaluate(self, context: str) -> str:
        lowered = context.lower()
        if "deceive" in lowered or "dishonest" in lowered:
            return "Virtue ethics flag: honesty compromised."
        return "Dialogue aligns with prosocial virtues."


def reflect_all(context: str) -> Dict[str, str]:
    """Return evaluations from all ethical profiles."""
    return {
        "constitutional": ConstitutionalEthics().evaluate(context),
        "consequentialist": ConsequentialistEthics().evaluate(context),
        "virtue": VirtueEthics().evaluate(context),
    }


__all__ = [
    "ConstitutionalEthics",
    "ConsequentialistEthics",
    "VirtueEthics",
    "reflect_all",
]

