from __future__ import annotations

"""Realignment trigger utility."""

import json
import logging
import inspect
from pathlib import Path
from typing import Dict, Any

# Threshold configuration
THRESHOLDS_FILE = Path(__file__).with_name("thresholds.json")
_DEFAULT_THRESHOLDS: Dict[str, float] = {
    "symbolic_density": 0.4,
    "interpretive_bandwidth": 0.6,
    "divergence_score": 0.5,
}


def _load_thresholds(path: Path) -> Dict[str, float]:
    """Load thresholds from ``path`` if it exists."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return {
                key: float(data[key])
                for key in _DEFAULT_THRESHOLDS
                if key in data
            }
    except Exception as exc:  # pragma: no cover - don't break on errors
        logging.warning("Failed to load thresholds from %s: %s", path, exc)
    return {}


# Thresholds for drift metrics that require realignment
DRIFT_THRESHOLDS: Dict[str, float] = dict(_DEFAULT_THRESHOLDS)
DRIFT_THRESHOLDS.update(_load_thresholds(THRESHOLDS_FILE))


def _thresholds_for_agent(agent: Any | None) -> Dict[str, float]:
    """Return thresholds, applying any agent-specific overrides."""
    if agent is None:
        return DRIFT_THRESHOLDS
    try:
        module = inspect.getmodule(agent)
        if module and hasattr(module, "__file__"):
            agent_file = Path(module.__file__)
        else:
            agent_file = Path(inspect.getfile(agent))
        override = _load_thresholds(agent_file.parent / "thresholds.json")
        if override:
            merged = dict(DRIFT_THRESHOLDS)
            merged.update(override)
            return merged
    except Exception as exc:  # pragma: no cover - don't break on errors
        logging.warning("Failed to determine thresholds for agent: %s", exc)
    return DRIFT_THRESHOLDS


def should_realign(drift_metrics: Dict[str, float], *, agent: Any | None = None,
                   context: str | None = None) -> bool:
    """Return ``True`` if any drift metric falls below its threshold.

    Parameters
    ----------
    drift_metrics:
        Mapping containing ``symbolic_density``, ``interpretive_bandwidth``,
        and ``divergence_score`` values.
    """
    thresholds = _thresholds_for_agent(agent)
    triggers = []
    for key, threshold in thresholds.items():
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
