from __future__ import annotations

"""Realignment trigger utility."""

import logging
from typing import Dict

# Thresholds for drift metrics that require realignment
DRIFT_THRESHOLDS: Dict[str, float] = {
    "symbolic_density": 0.4,
    "interpretive_bandwidth": 0.6,
    "divergence_score": 0.5,
}


def should_realign(drift_metrics: Dict[str, float]) -> bool:
    """Return ``True`` if any drift metric falls below its threshold.

    Parameters
    ----------
    drift_metrics:
        Mapping containing ``symbolic_density``, ``interpretive_bandwidth``,
        and ``divergence_score`` values.
    """
    triggers = []
    for key, threshold in DRIFT_THRESHOLDS.items():
        value = drift_metrics.get(key)
        if value is not None and value < threshold:
            triggers.append(f"{key}<{threshold}")
    if triggers:
        logging.info("Realignment triggered by: %s", ", ".join(triggers))
        return True
    return False


__all__ = ["should_realign", "DRIFT_THRESHOLDS"]
