"""Cross-boundary contracts from the actual server source, without runtime I/O."""
import ast
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import Mock

from exchange_terminal.services.terminal_research import validate_terminal_strategy_params, _core_input_adapter

SERVER = Path(__file__).parents[1] / "exchange_terminal/server.py"
TREE = ast.parse(SERVER.read_text(encoding="utf-8-sig"))


def source_function(name, scope):
    node = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SERVER), "exec"), scope)
    return scope[name]


class Captured(Exception):
    pass


class TerminalIntegrationContracts(unittest.TestCase):
    def preview(self, query):
        seen = {}
        def capture(**kwargs):
            seen.update(kwargs)
            raise Captured()
        scope = {"Any": Any, "json": json, "math": math, "strategy_validation_capability": lambda _: {"known": True, "backtest_supported": True},
                 "clamp": lambda x, a, b: max(a, min(x, b)), "pct": float,
                 "backtest_market_rows": lambda *a, **kw: {"rows": [], "source": "synthetic-fixture"},
                 "choose_strategy": lambda _: {"id": "dual_ma", "params": {"fast_window": 10, "slow_window": 30}},
                 "validate_terminal_strategy_params": validate_terminal_strategy_params,
                 "strategy_implementation_fingerprint": lambda sid, params: json.dumps(params, sort_keys=True),
                 "backtest_reproducibility": capture, "EXECUTION_MODEL_VERSION": "fixture"}
        fn = source_function("strategy_backtest_report", scope)
        with self.assertRaises(Captured):
            fn(query)
        return seen

    def test_original_preview_uses_explicit_frozen_parameters_in_identity(self):
        result = self.preview({"strategy": "dual_ma", "strategyParams": json.dumps({"fast_window": 7, "slow_window": 25})})
        self.assertEqual(result["params"]["strategy_params"]["fast_window"], 7)
        self.assertEqual(result["params"]["strategy_params"]["slow_window"], 25)
        self.assertEqual(json.loads(result["strategy_fingerprint"])["fast_window"], 7)

    def test_original_preview_without_override_keeps_existing_defaults(self):
        result = self.preview({"strategy": "dual_ma"})
        self.assertEqual(result["params"]["strategy_params"], {"fast_window": 10, "slow_window": 30})

    def test_original_preview_rejects_duplicate_or_invalid_parameters(self):
        for encoded in ('{"fast_window":7,"fast_window":8}', '{"fast_window":0}', '{"unknown":1}'):
            with self.subTest(encoded=encoded), self.assertRaises(ValueError):
                self.preview({"strategy": "dual_ma", "strategyParams": encoded})

    def test_frozen_runner_uses_provided_rows_and_preserves_full_record_option(self):
        calls = []
        def engine(**kwargs):
            calls.append(kwargs)
            return {"ok": True, "trades": list(range(50)), "equity_curve": list(range(300))}
        market_fetch = Mock(side_effect=AssertionError("frozen runner must not fetch market data"))
        scope = {"Any": Any, "strategy_validation_capability": lambda _: {"backtest_supported": True},
                 "backtest_market_rows": market_fetch, "choose_strategy": lambda _: {"id": "dual_ma", "params": {"fast_window": 10}},
                 "run_causal_long_only_backtest": engine, "build_strategy_signal_fn": lambda sid, params: params,
                 "strategy_startup_candles": lambda *a: 30, "is_stock_symbol": lambda _: False,
                 "strategy_signal_input": lambda _: "CLOSES", "equity_segment_report": lambda _: [],
                 "backtest_risk_label": lambda _: "fixture", "EXECUTION_MODEL_VERSION": "fixture"}
        fn = source_function("run_strategy_backtest", scope)
        args = {"strategy_id": "dual_ma", "position_pct": 25, "take_profit_pct": 0, "stop_loss_pct": 8, "leverage": 1,
                "market_payload": {"rows": [{"close": 42}], "source": "frozen"}, "strategy_params": {"fast_window": 7}}
        full = fn(**args, include_full_history=True)
        legacy = fn(**args)
        self.assertEqual((len(full["trades"]), len(full["equity_curve"])), (50, 300))
        self.assertEqual((len(legacy["trades"]), len(legacy["equity_curve"])), (24, 240))
        self.assertEqual(calls[0]["rows"], [{"close": 42}])
        self.assertEqual(calls[0]["signal_fn"], {"fast_window": 7})
        market_fetch.assert_not_called()

    def test_return_path_never_silently_clamps_frozen_risk(self):
        for field, value in (("positionPct", ".5"), ("takeProfitPct", "100"), ("stopLossPct", "90"), ("leverage", "2"), ("positionPct", "nan")):
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, "not_compatible"):
                self.preview({"strategy": "dual_ma", "strategyParams": "{}", field: value})


class FrozenMarketWrapperContracts(unittest.TestCase):
    """Use actual server wrapper, symbol heuristic, signals and native engine.

    Only the program's global boot/I/O are omitted. Prices and declarations are
    fabricated QA fixtures; no retained UNKNOWN operation is read or replayed.
    """
    def setUp(self):
        from exchange_terminal.market_data.stocks import is_stock_symbol
        from exchange_terminal.services.backtest_engine import run_causal_long_only_backtest
        from exchange_terminal.services.strategy_signals import (build_strategy_signal_fn, strategy_signal_input,
                strategy_startup_candles_for_params, strategy_validation_capability)
        from tests.test_terminal_research import build_core_import_qa_fixture
        snapshot = build_core_import_qa_fixture()
        from hakimi_terminal_research.equity_dataset import verify_equity_snapshot

        snapshot = verify_equity_snapshot(snapshot)
        frozen = _core_input_adapter(snapshot, "a" * 24, "b" * 64)
        self.market = {"symbol": frozen["symbol"], "source": frozen["source"], "rows": frozen["rows"],
                       "meta": frozen["meta"], "bar": "1D", "frozen_input": True, "input_id": frozen["id"]}
        self.engine = Mock(wraps=run_causal_long_only_backtest)
        self.fetch = Mock(side_effect=AssertionError("frozen input must not fetch data"))
        strategies = next(node for node in TREE.body if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "STRATEGIES" for target in node.targets))
        scope = {"Any": Any, "strategy_validation_capability": strategy_validation_capability,
                 "backtest_market_rows": self.fetch, "run_causal_long_only_backtest": self.engine,
                 "build_strategy_signal_fn": build_strategy_signal_fn,
                 "_strategy_startup_candles_for_params": strategy_startup_candles_for_params,
                 "is_stock_symbol": is_stock_symbol, "strategy_signal_input": strategy_signal_input,
                 "average": lambda values: sum(values) / len(values) if values else 0.0}
        exec(compile(ast.Module(body=[strategies], type_ignores=[]), str(SERVER), "exec"), scope)
        for name in ("choose_strategy", "strategy_startup_candles", "max_drawdown", "sharpe_ratio",
                     "equity_segment_report", "backtest_risk_label"):
            source_function(name, scope)
        self.run_backtest = source_function("run_strategy_backtest", scope)
        self.args = {"strategy_id": "macd", "position_pct": 25, "take_profit_pct": 0, "stop_loss_pct": 8,
                     "leverage": 1, "symbol": "QADEMO", "market_payload": self.market,
                     "strategy_params": {"fast": 12, "slow": 26, "signal": 9, "position_pct": .25, "stop_loss_pct": .035},
                     "include_full_history": True}

    def test_six_letter_core_equity_uses_retained_identity_through_actual_wrapper(self):
        from exchange_terminal.market_data.stocks import is_stock_symbol
        self.assertFalse(is_stock_symbol("QADEMO"))
        result = self.run_backtest(**self.args)
        self.assertTrue(result["ok"], result.get("dataset_manifest"))
        self.assertEqual(self.engine.call_args.kwargs["market"], "stock")
        self.assertEqual(result["dataset_manifest"]["market"], "stock")
        self.assertEqual(result["dataset_manifest"]["market_calendar"]["status"], "PASS")
        self.assertEqual(result["dataset_manifest"]["row_count"], 146)
        self.assertGreater(result["order_event_count"], 0)
        self.assertEqual(result["order_event_count"], len(result["trades"]))
        self.assertEqual(result["evaluation_window"]["evaluated_rows"], len(result["equity_curve"]))
        self.assertEqual(self.engine.call_args.kwargs["rows"], self.market["rows"])
        self.fetch.assert_not_called()

    def test_ordinary_api_retains_legacy_symbol_classification(self):
        self.market.pop("frozen_input")
        result = self.run_backtest(**self.args)
        self.assertFalse(result["ok"])
        self.assertEqual(self.engine.call_args.kwargs["market"], "crypto")
        self.assertEqual(result["dataset_manifest"]["blockers"], ["temporal_gaps_exceed_policy:32"])
        self.fetch.assert_not_called()

    def test_unknown_or_conflicting_frozen_asset_identity_does_not_fallback(self):
        for meta, symbol in (({}, "QADEMO"), ({"asset_class": "UNKNOWN"}, "QADEMO"),
                             (None, "QADEMO"), ({"asset_class": "US_EQUITY"}, "DIFFERENT")):
            with self.subTest(meta=meta, symbol=symbol):
                payload = {**self.market, "meta": meta, "symbol": symbol}
                with self.assertRaisesRegex(ValueError, "frozen_input_market_identity_invalid"):
                    self.run_backtest(**{**self.args, "market_payload": payload})
        self.engine.assert_not_called()
        self.fetch.assert_not_called()

    def test_frozen_equity_identity_does_not_bypass_marked_source_guard(self):
        self.market["source"] = "SYNTHETIC_TEST"
        result = self.run_backtest(**self.args)
        self.assertFalse(result["ok"])
        self.assertIn("synthetic_or_preview_source", result["dataset_manifest"]["blockers"])
        self.assertEqual(result["dataset_manifest"]["market"], "stock")
        self.fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
