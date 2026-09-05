from _canonical_source import activate_canonical_source

activate_canonical_source()

from hakimi_research.strategies import STRATEGY_REGISTRY, build_strategy  # noqa: E402

__all__ = ["STRATEGY_REGISTRY", "build_strategy"]
