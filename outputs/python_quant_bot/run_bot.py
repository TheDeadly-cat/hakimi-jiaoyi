from __future__ import annotations

import argparse
import json
from pathlib import Path

from exchange_terminal.domain.contracts import (
    build_product_capability_catalog,
    product_capability_status_for_cli_command,
    supported_cli_commands,
)
from quant_bot.backtest import BacktestEngine
from quant_bot.config import BotConfig
from quant_bot.data import build_data_provider
from quant_bot.execution import build_broker
from quant_bot.experiment_manifest import build_local_experiment_context
from quant_bot.logging_setup import setup_logging
from quant_bot.reporting import save_json_report
from quant_bot.risk import RiskManager
from quant_bot.strategies.templates import build_strategy


LEGACY_PAPER_ENABLED = False
LEGACY_OPTIMIZE_ENABLED = False


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
    engine = BacktestEngine(
        config=config,
        strategy=strategy,
        risk_manager=risk,
        experiment_context=build_local_experiment_context(Path(__file__).resolve().parent),
    )
    report = engine.run(data)
    report_payload = report.to_dict()
    experiment_id = str(report.experiment_manifest.get("experiment_id") or "")
    output = save_json_report(
        report_payload,
        "runtime/reports",
        f"backtest_{config.strategy.name}_{config.symbol}",
        artifact_id=experiment_id,
    )
    summary = {field: getattr(report, field) for field in SUMMARY_FIELDS}
    summary.update({
        "strategy": config.strategy.name,
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "data_rows": len(data),
        "experiment_id": experiment_id,
        "reproducibility_status": report.experiment_manifest.get("status"),
        "ranking_input_allowed": report.experiment_manifest.get("ranking_gate", {}).get(
            "input_allowed", False
        ),
        "full_report": str(output),
    })
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def command_paper(args: argparse.Namespace) -> None:
    if product_capability_status_for_cli_command("paper") != "Archived":
        raise RuntimeError("Product capability catalog rejected the paper boundary.")
    raise RuntimeError(
        "Legacy paper path is archived and permanently disabled in the research-only product."
    )


def command_optimize(args: argparse.Namespace) -> None:
    if product_capability_status_for_cli_command("optimize") != "Archived":
        raise RuntimeError("Product capability catalog rejected the optimize boundary.")
    raise RuntimeError(
        "Legacy optimize path is archived and permanently disabled in the research-only product."
    )


def command_capabilities(_args: argparse.Namespace) -> None:
    print(json.dumps(
        build_product_capability_catalog().to_dict(),
        indent=2,
        ensure_ascii=False,
    ))


def command_list_strategies(_args: argparse.Namespace) -> None:
    from quant_bot.strategies.templates import STRATEGY_REGISTRY

    print("Available strategies:")
    for name in sorted(STRATEGY_REGISTRY):
        print(f"- {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hakimi research-only strategy platform")
    parser.add_argument("command", choices=supported_cli_commands())
    parser.add_argument("--config", default="config.example.json")
    args = parser.parse_args()

    try:
        if args.command == "backtest":
            command_backtest(args)
        elif args.command == "capabilities":
            command_capabilities(args)
        elif args.command == "list-strategies":
            command_list_strategies(args)
        else:
            raise RuntimeError(f"Unsupported command: {args.command}")
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
