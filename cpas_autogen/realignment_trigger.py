from __future__ import annotations

"""Realignment trigger utility."""

import json
import logging
from pathlib import Path
from typing import Dict, Any

# Threshold configuration
THRESHOLDS_FILE = Path(__file__).with_name("thresholds.json")
_DEFAULT_THRESHOLDS: Dict[str, float] = {
    "symbolic_density": 0.4,
    "interpretive_bandwidth": 0.6,
    "divergence_score": 0.5,
}

# Thresholds for drift metrics that require realignment
DRIFT_THRESHOLDS: Dict[str, float] = dict(_DEFAULT_THRESHOLDS)
if THRESHOLDS_FILE.exists():
    try:
        data = json.loads(THRESHOLDS_FILE.read_text())
        if isinstance(data, dict):
            for key in DRIFT_THRESHOLDS:
                if key in data:
                    DRIFT_THRESHOLDS[key] = float(data[key])
    except Exception as exc:  # pragma: no cover - don't break on errors
        logging.warning("Failed to load thresholds: %s", exc)


def should_realign(drift_metrics: Dict[str, float], *, agent: Any | None = None,
                   context: str | None = None) -> bool:
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
        if agent and hasattr(agent, "reflect_ethics"):
            try:
                agent.reflect_ethics(context or "")
            except Exception as exc:  # pragma: no cover - don't break on errors
                logging.warning("Ethical reflection failed: %s", exc)
        return True
    return False


__all__ = ["should_realign", "DRIFT_THRESHOLDS"]
