from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant_bot.backtest import BacktestEngine
from quant_bot.config import BotConfig
from quant_bot.data import build_data_provider
from quant_bot.engine import TradingEngine
from quant_bot.execution import build_broker
from quant_bot.logging_setup import setup_logging
from quant_bot.optimizer import ParameterOptimizer
from quant_bot.reporting import save_json_report
from quant_bot.risk import RiskManager
from quant_bot.strategies.templates import build_strategy


SUMMARY_FIELDS = [
    "total_return",
    "annualized_return",
    "max_drawdown",
    "win_rate",
    "sharpe_ratio",
    "trades",
    "final_equity",
]


def load_stack(config_path: str, with_broker: bool = True):
    config = BotConfig.from_file(config_path)
    setup_logging(config.logging.log_dir, config.logging.level)
    provider = build_data_provider(config)
    strategy = build_strategy(config.strategy.name, config.strategy.params)
    risk = RiskManager(config.risk)
    broker = build_broker(config) if with_broker else None
    return config, provider, strategy, risk, broker


def command_backtest(args: argparse.Namespace) -> None:
    config, provider, strategy, risk, _broker = load_stack(args.config, with_broker=False)
    data = provider.get_history(config.symbol, config.timeframe, config.data.history_limit)
    engine = BacktestEngine(config=config, strategy=strategy, risk_manager=risk)
    report = engine.run(data)
    output = save_json_report(report.to_dict(), "runtime/reports", f"backtest_{config.strategy.name}_{config.symbol}")
    summary = {field: getattr(report, field) for field in SUMMARY_FIELDS}
    summary.update({
        "strategy": config.strategy.name,
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "data_rows": len(data),
        "full_report": str(output),
    })
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def command_paper(args: argparse.Namespace) -> None:
    config, provider, strategy, risk, broker = load_stack(args.config)
    engine = TradingEngine(config=config, data_provider=provider, strategy=strategy, risk_manager=risk, broker=broker)
    engine.run(cycles=args.cycles)
    last_price = engine.last_price or 0.0
    summary = {
        "mode": config.mode,
        "strategy": config.strategy.name,
        "symbol": config.symbol,
        "cycles": args.cycles,
        "last_price": round(last_price, 4),
        "cash": round(engine.portfolio.cash, 2),
        "position_qty": round(engine.portfolio.position_qty, 8),
        "equity": round(engine.portfolio.equity(last_price), 2) if last_price else round(engine.portfolio.cash, 2),
        "log_file": config.logging.log_dir + "/bot.log",
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def command_optimize(args: argparse.Namespace) -> None:
    config, provider, _strategy, risk, _broker = load_stack(args.config, with_broker=False)
    data = provider.get_history(config.symbol, config.timeframe, config.data.history_limit)
    optimizer = ParameterOptimizer(config=config, risk_manager=risk)
    result = optimizer.run(data)
    output = save_json_report(result, "runtime/reports", f"optimize_{config.strategy.name}_{config.symbol}")
    summary = {
        "metric": result.get("metric"),
        "best": result.get("best"),
        "tested": len(result.get("results", [])),
        "full_report": str(output),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def command_list_strategies(_args: argparse.Namespace) -> None:
    from quant_bot.strategies.templates import STRATEGY_REGISTRY

    print("Available strategies:")
    for name in sorted(STRATEGY_REGISTRY):
        print(f"- {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Python Quant Bot")
    parser.add_argument("command", choices=["backtest", "paper", "optimize", "list-strategies"])
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--cycles", type=int, default=5)
    args = parser.parse_args()

    Path("runtime").mkdir(exist_ok=True)

    if args.command == "backtest":
        command_backtest(args)
    elif args.command == "paper":
        command_paper(args)
    elif args.command == "optimize":
        command_optimize(args)
    elif args.command == "list-strategies":
        command_list_strategies(args)


if __name__ == "__main__":
    main()
