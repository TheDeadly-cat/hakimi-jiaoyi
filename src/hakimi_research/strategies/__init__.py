"""Lazy public exports keep benchmark subclasses independent of registration."""

__all__ = ["STRATEGY_REGISTRY", "build_strategy"]


def __getattr__(name: str):
    if name in __all__:
        from . import templates
        return getattr(templates, name)
    raise AttributeError(name)

__all__ = ["STRATEGY_REGISTRY", "build_strategy"]
