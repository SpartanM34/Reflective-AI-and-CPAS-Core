"""Lazy-loading access to AutoGen instance modules.

Standard agents are loaded from ``agents.python``. Agents considered
"adversarial" (used only during stress testing) live under
``agents.adversarial.python`` and are only importable when the environment
variable ``STRESS_TEST`` is explicitly set to ``"1"``.
"""

import os

_ADVERSARIAL = {"Echo-7", "Fray-5"}


def __getattr__(name):
    if name.startswith("_"):
        raise AttributeError(name)

    if name in _ADVERSARIAL:
        if os.environ.get("STRESS_TEST") != "1":
            raise AttributeError(name)
        module_path = f"agents.adversarial.python.{name}"
    else:
        module_path = f"agents.python.{name}"

    try:
        module = __import__(module_path, fromlist=[name])
    except Exception as exc:
        raise AttributeError(name) from exc
    globals()[name] = module
    return module

__all__ = []
