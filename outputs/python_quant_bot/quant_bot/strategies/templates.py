from _canonical_source import activate_canonical_source

activate_canonical_source()

from hakimi_research.strategies.templates import (  # noqa: E402
    STRATEGY_REGISTRY,
    BollingerBandStrategy,
    DualMovingAverageStrategy,
    GridStrategy,
    MacdStrategy,
    MomentumStrategy,
    RsiStrategy,
    build_strategy,
)

__all__ = [
    "DualMovingAverageStrategy",
    "GridStrategy",
    "BollingerBandStrategy",
    "MacdStrategy",
    "RsiStrategy",
    "MomentumStrategy",
    "STRATEGY_REGISTRY",
    "build_strategy",
]
