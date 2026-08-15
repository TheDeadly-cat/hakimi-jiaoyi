from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from quant_bot.models import Portfolio, Signal


@dataclass
class StrategyBase:
    params: dict[str, Any] = field(default_factory=dict)
    name: str = "base"

    def get(self, key: str, default: Any) -> Any:
        return self.params.get(key, default)

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        raise NotImplementedError
