"""Lazy-loading access to AutoGen instance modules."""

def __getattr__(name):
    if name.startswith('_'):
        raise AttributeError(name)
    try:
        module = __import__(f"agents.python.{name}", fromlist=[name])
    except Exception as exc:
        raise AttributeError(name) from exc
    globals()[name] = module
    return module

__all__ = []
