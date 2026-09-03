from __future__ import annotations

import itertools

import pandas as pd

from quant_bot.backtest import BacktestEngine
from quant_bot.config import BotConfig
from quant_bot.risk import RiskManager
from quant_bot.strategies.templates import build_strategy


class ParameterOptimizer:
    def __init__(self, config: BotConfig, risk_manager: RiskManager):
        self.config = config
        self.risk_manager = risk_manager

    def run(self, data: pd.DataFrame) -> dict:
        grid = self.config.optimizer.grid
        keys = list(grid.keys())
        if not keys:
            return {"best": None, "results": []}
        results = []
        metric_fields = [
            "total_return",
            "annualized_return",
            "max_drawdown",
            "win_rate",
            "sharpe_ratio",
            "trades",
            "final_equity",
        ]
        for values in itertools.product(*(grid[key] for key in keys)):
            params = dict(self.config.strategy.params)
            params.update(dict(zip(keys, values)))
            strategy = build_strategy(self.config.strategy.name, params)
            risk = RiskManager(self.config.risk)
            report = BacktestEngine(self.config, strategy, risk).run(data)
            item = {"params": params}
            item.update({field: getattr(report, field) for field in metric_fields})
            results.append(item)
        metric = self.config.optimizer.metric
        best = max(results, key=lambda item: item.get(metric, 0))
        return {"metric": metric, "best": best, "results": results}
