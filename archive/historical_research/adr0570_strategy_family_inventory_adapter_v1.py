from __future__ import annotations

from typing import Any

from hakimi_research.strategy_family_inventory import build_strategy_family_inventory
from hakimi_research.strategies.base import StrategyBase
from hakimi_research.strategies.templates import STRATEGY_REGISTRY


class StrategyFamilyInventoryAdapterError(ValueError):
    """Raised when the live source registry is not an exact strategy-class registry."""


def build_current_strategy_family_inventory() -> dict[str, Any]:
    if type(STRATEGY_REGISTRY) is not dict:
        raise StrategyFamilyInventoryAdapterError("STRATEGY_REGISTRY must be an exact dict")
    strategy_ids: list[str] = []
    for strategy_id, strategy_class in STRATEGY_REGISTRY.items():
        if type(strategy_id) is not str:
            raise StrategyFamilyInventoryAdapterError("strategy registry keys must be exact str values")
        if type(strategy_class) is not type or not issubclass(strategy_class, StrategyBase):
            raise StrategyFamilyInventoryAdapterError(
                f"strategy registry value is not a StrategyBase class: {strategy_id}"
            )
        strategy_ids.append(strategy_id)
    return build_strategy_family_inventory(strategy_ids)


__all__ = [
    "StrategyFamilyInventoryAdapterError",
    "build_current_strategy_family_inventory",
]
