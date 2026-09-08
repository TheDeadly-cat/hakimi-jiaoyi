from __future__ import annotations

import ast
import math
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research.backtest import (  # noqa: E402
    BACKTEST_SCHEMA_VERSION,
    BacktestEngine,
    BacktestReport,
)
from hakimi_research.config import BotConfig, RiskConfig  # noqa: E402
from hakimi_research.risk import RiskManager  # noqa: E402
from quant_bot import backtest as legacy_backtest  # noqa: E402
from quant_bot.strategies.base import StrategyBase  # noqa: E402


LEGACY_PATH = OUTPUT_ROOT / "quant_bot" / "backtest.py"


class MinimalStrategy(StrategyBase):
    def generate_signal(self, data, portfolio):
        raise AssertionError("not used")


class CanonicalResearchBacktestSourceV1Tests(unittest.TestCase):
    def test_schema_and_legacy_identity_are_canonical(self) -> None:
        self.assertEqual(BACKTEST_SCHEMA_VERSION, "research-backtest-core-v2")
        self.assertIs(legacy_backtest.BacktestEngine, BacktestEngine)
        self.assertIs(legacy_backtest.BacktestReport, BacktestReport)

    def test_legacy_module_is_definition_free(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(any(isinstance(node, definitions) for node in ast.walk(tree)))

    def test_engine_detaches_config_strategy_risk_and_context(self) -> None:
        config = BotConfig()
        strategy = MinimalStrategy(params={"window": 1})
        risk = RiskManager(config.risk)
        context = {"source": {"label": "original"}}
        engine = BacktestEngine(config, strategy, risk, context)

        config.initial_cash = 1.0
        strategy.params["window"] = 9
        risk.trading_halted = True
        context["source"]["label"] = "mutated"

        self.assertEqual(engine.config.initial_cash, 10_000.0)
        self.assertEqual(engine.strategy.params, {"window": 1})
        self.assertFalse(engine.risk.trading_halted)
        self.assertEqual(engine.experiment_context, {"source": {"label": "original"}})

    def test_engine_rejects_fake_or_mismatched_dependencies(self) -> None:
        config = BotConfig()
        fake_strategy = SimpleNamespace(
            params={},
            name="fake",
            version="v1",
            generate_signal=lambda data, portfolio: None,
        )
        with self.assertRaises(ValueError):
            BacktestEngine(config, fake_strategy, RiskManager(config.risk))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            BacktestEngine(config, MinimalStrategy(), SimpleNamespace())  # type: ignore[arg-type]

        mismatched = RiskConfig()
        mismatched.max_position_pct = 0.1
        with self.assertRaises(ValueError):
            BacktestEngine(config, MinimalStrategy(), RiskManager(mismatched))

    def test_engine_dependencies_and_context_are_protected(self) -> None:
        config = BotConfig()
        engine = BacktestEngine(config, MinimalStrategy(), RiskManager(config.risk))
        with self.assertRaises(AttributeError):
            engine.execution_simulator = "replaced"  # type: ignore[assignment]
        with self.assertRaises(AttributeError):
            engine.config = config  # type: ignore[misc]
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        with self.assertRaises(ValueError):
            BacktestEngine(
                config,
                MinimalStrategy(),
                RiskManager(config.risk),
                cyclic,
            )

    def test_run_requires_exact_dataframe(self) -> None:
        class FrameSubclass(pd.DataFrame):
            pass

        config = BotConfig()
        engine = BacktestEngine(config, MinimalStrategy(), RiskManager(config.risk))
        with self.assertRaises(ValueError):
            engine.run(FrameSubclass())

    def test_report_rejects_invalid_metrics_and_shapes(self) -> None:
        base = {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "trades": 0,
            "final_equity": 1_000.0,
            "equity_curve": [],
            "fills": [],
            "total_fees": 0.0,
            "ambiguous_intrabar_count": 0,
            "execution_model": "research_next_open",
            "reproducibility": {},
            "experiment_manifest": {},
        }
        invalid = (
            {"total_return": math.nan},
            {"annualized_return": math.inf},
            {"win_rate": 1.1},
            {"trades": -1},
            {"final_equity": math.nan},
            {"equity_curve": ()},
            {"total_fees": -1.0},
            {"ambiguous_intrabar_count": -1},
            {"execution_model": ""},
        )
        for changes in invalid:
            values = dict(base)
            values.update(changes)
            with self.assertRaises(ValueError):
                BacktestReport(**values)

    def test_report_is_detached_and_read_only(self) -> None:
        curve = [{"time": "t0", "equity": 1_000.0}]
        fills = [{"action": "BUY"}]
        reproducibility = {"status": "PASS"}
        manifest = {"status": "PASS"}
        report = BacktestReport(
            total_return=0.0,
            annualized_return=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            sharpe_ratio=0.0,
            trades=0,
            final_equity=1_000.0,
            equity_curve=curve,
            fills=fills,
            total_fees=0.0,
            ambiguous_intrabar_count=0,
            execution_model="research_next_open",
            reproducibility=reproducibility,
            experiment_manifest=manifest,
        )
        curve[0]["equity"] = 1.0
        fills[0]["action"] = "MUTATED"
        reproducibility["status"] = "MUTATED"
        manifest["status"] = "MUTATED"
        self.assertEqual(report.equity_curve[0]["equity"], 1_000.0)
        self.assertEqual(report.fills[0]["action"], "BUY")
        self.assertEqual(report.reproducibility["status"], "PASS")
        self.assertEqual(report.experiment_manifest["status"], "PASS")
        with self.assertRaises(FrozenInstanceError):
            report.total_return = 1.0  # type: ignore[misc]

        exported = report.to_dict()
        exported["equity_curve"][0]["equity"] = 2.0
        self.assertEqual(report.equity_curve[0]["equity"], 1_000.0)


if __name__ == "__main__":
    unittest.main()
