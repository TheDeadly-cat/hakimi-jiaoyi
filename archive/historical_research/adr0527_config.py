from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DataConfig:
    provider: str = "synthetic"
    history_limit: int = 500
    csv_path: str = ""
    cache_dir: str = "runtime/cache"
    use_cache: bool = True


@dataclass
class StrategyConfig:
    name: str = "dual_ma"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskConfig:
    max_position_pct: float = 0.35
    max_single_loss_pct: float = 0.03
    max_daily_loss_pct: float = 0.05
    max_leverage: float = 2.0
    min_cash_pct: float = 0.05


@dataclass
class ExecutionConfig:
    broker: str = "paper"
    exchange: str = "okx"
    fee_rate: float = 0.0008
    slippage_pct: float = 0.0005
    poll_seconds: int = 5
    live_trading_enabled: bool = False



@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_dir: str = "runtime/logs"


@dataclass
class BotConfig:
    name: str = "quant_bot"
    mode: str = "backtest"
    market: str = "crypto"
    symbol: str = "BTC-USDT"
    timeframe: str = "1h"
    initial_cash: float = 10000.0
    data: DataConfig = field(default_factory=DataConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_file(cls, path: str | Path) -> "BotConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if raw.get("mode") == "optimize" or "optimizer" in raw:
            raise ValueError(
                "Legacy optimizer configuration is archived and permanently disabled "
                "in the research-only product."
            )
        execution = ExecutionConfig(**raw.get("execution", {}))
        execution.broker = "paper"
        execution.live_trading_enabled = False
        return cls(
            name=raw.get("name", "quant_bot"),
            mode="backtest",
            market=raw.get("market", "crypto"),
            symbol=raw.get("symbol", "BTC-USDT"),
            timeframe=raw.get("timeframe", "1h"),
            initial_cash=float(raw.get("initial_cash", 10000)),
            data=DataConfig(**raw.get("data", {})),
            strategy=StrategyConfig(**raw.get("strategy", {})),
            risk=RiskConfig(**raw.get("risk", {})),
            execution=execution,
            logging=LoggingConfig(**raw.get("logging", {})),
        )
