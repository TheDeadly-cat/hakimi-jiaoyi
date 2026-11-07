"""Offline tests of captured strategy analysis; no server import, credentials or I/O."""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import Mock
import urllib.parse

from exchange_terminal import utils
from hakimi_research.stock_candle_quality import analyze_stock_candle_series, stock_candle_quality_public
from exchange_terminal.services.market_calendar import resolve_stock_candle_schedule_attestation
from exchange_terminal.services.deepseek_projection import build_deepseek_projection
from exchange_terminal.services.http_contract import POST_API_PATHS, MUTATION_PATHS
from exchange_terminal.services.strategy_signals import (
    SIGNAL_ENGINE_VERSION, build_strategy_signal_fn, strategy_signal_input,
    strategy_startup_candles_for_params, strategy_validation_capability,
)
from exchange_terminal.services.terminal_research import validate_terminal_strategy_params


SERVER = Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
TREE = ast.parse(SERVER.read_text(encoding="utf-8"))
NAMES = {"deepseek_strategy_snapshot_analysis", "_market_ai_frontend_snapshot",
         "analyze_strategy_context", "evaluate_strategy_signal", "strategy_startup_candles",
         "build_risk_config", "trade_direction_from_mode", "estimate_hit_probability"}
FUNCTIONS = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in NAMES]
STRATEGY = {"id": "dual_ma", "name": "双均线", "params": {
    "fast_window": 20, "slow_window": 60, "position_pct": .25, "stop_loss_pct": .03,
}}


def namespace():
    scope = {name: getattr(utils, name) for name in ("pct", "flag", "choice", "average", "clamp", "recent_volatility", "trend_score")}
    scope.update({
        "Any": Any, "json": json, "math": math, "hashlib": hashlib, "now_ms": lambda: 123,
        "ORDER_TYPES": {"MARKET", "LIMIT", "CURRENT"}, "SIGNAL_ENGINE_VERSION": SIGNAL_ENGINE_VERSION,
        "choose_strategy": lambda name: deepcopy(STRATEGY) if name == "dual_ma" else {"id": name, "unsupported": True},
        "strategy_validation_capability": strategy_validation_capability,
        "validate_terminal_strategy_params": validate_terminal_strategy_params,
        "strategy_signal_input": strategy_signal_input,
        "_strategy_startup_candles_for_params": strategy_startup_candles_for_params,
        "build_strategy_signal_fn": Mock(wraps=build_strategy_signal_fn),
        "is_stock_symbol": lambda symbol: symbol == "AAPL",
        "resolve_stock_candle_schedule_attestation": resolve_stock_candle_schedule_attestation,
        "analyze_stock_candle_series": analyze_stock_candle_series,
        "stock_candle_quality_public": stock_candle_quality_public,
        "deepseek_status": lambda: {"provider": "deepseek", "configured": True, "enabled": True, "model": "deepseek-v4-pro", "source": "env", "thinking": "disabled"},
        "deepseek_chat": Mock(return_value={"ok": True, "provider": "deepseek", "configured": True,
            "content": '{"summary":"模型解释"}', "json": {"summary": "模型解释"}, "request_attempts": 1}),
    })
    for name in ("strategy_candles_for_symbol", "read_stock_quote", "read_stock_candles",
                 "market_insights", "contract_center", "strategy_compare", "market_ai_candles"):
        scope[name] = Mock(side_effect=AssertionError("replacement market fetch prohibited"))
    exec(compile(ast.Module(body=FUNCTIONS, type_ignores=[]), str(SERVER), "exec"), scope)
    return scope


def payload(count=100):
    rows = [{"ts": 1700000000000 + index * 300000, "open": 100 + index / 10,
             "high": 102 + index / 10, "low": 99 + index / 10, "close": 101 + index / 10,
             "volume": 1000 + index, "complete": True, "provisional": False, "source": "YahooAdjusted"}
            for index in range(count)]
    return {"symbol": "AAPL", "bar": "5m", "price": 999999, "candles": rows,
            "strategy_id": "dual_ma", "strategy_params": {**STRATEGY["params"], "fast_window": 10, "slow_window": 30},
            "risk_config": {"riskSource": "MANUAL", "riskValueMode": "PCT", "takeProfitPct": "10", "stopLossPct": "5", "directionMode": "LONG_ONLY"},
            "chart_context": {"session": "regular", "snapshot_source": "YahooAdjusted",
                              "shared_snapshot": {"symbol": "AAPL", "bar": "5m", "session": "regular", "snapshot_id": "captured-test"}},
            "max_output_tokens": 768, "question": "解释图表、规则及限制。"}


def stock_daily_candles(count):
    """Synthetic prices on the real offline XNYS calendar; no provider receipt."""
    schedule = resolve_stock_candle_schedule_attestation(
        benchmark_symbol="AAPL", source="YahooAdjusted",
        rows=[{"date": "2024-01-02"}, {"date": "2024-06-28"}],
    )
    if not isinstance(schedule, dict) or len(schedule.get("sessions", [])) < count:
        raise AssertionError("The installed exchange calendar must cover the daily fixture")
    return [{"ts": int(datetime.fromisoformat(session["open_utc"]).timestamp() * 1000),
             "date": session["date"], "open": 100 + index / 10, "high": 102 + index / 10,
             "low": 99 + index / 10, "close": 101 + index / 10, "volume": 1000 + index,
             "complete": True, "provisional": False, "source": "YahooAdjusted"}
            for index, session in enumerate(schedule["sessions"][:count])]


def daily_payload(count=100):
    data = payload(count)
    data["bar"] = data["chart_context"]["shared_snapshot"]["bar"] = "1Dutc"
    data["candles"] = stock_daily_candles(count)
    return data


class CapturedStrategyTests(unittest.TestCase):
    def assert_no_fetch(self, scope):
        for name in ("strategy_candles_for_symbol", "read_stock_quote", "read_stock_candles",
                     "market_insights", "contract_center", "strategy_compare", "market_ai_candles"):
            scope[name].assert_not_called()

    def test_original_rules_and_signal_use_edited_params_and_only_completed_captured_rows(self):
        scope = namespace()
        data = payload()
        data["candles"][-1]["complete"] = False
        data["candles"][-1]["provisional"] = True
        before = deepcopy(data)
        result = scope["deepseek_strategy_snapshot_analysis"](data)
        self.assertEqual(data, before)
        self.assertTrue(result["ok"])
        self.assertEqual(result["completion_counts"], {"total": 100, "complete": 99, "provisional": 1, "unknown": 0})
        self.assertEqual(result["input_identity"]["source"], "YahooAdjusted")
        self.assertEqual(result["input_identity"]["bar"], "5m")
        self.assertEqual(result["input_identity"]["session"], "regular")
        self.assertEqual(result["local"]["candle_count"], 99)
        self.assertTrue(result["local"]["signal"]["calculated"])
        self.assertEqual(result["local"]["signal"]["availability"], "CALCULATED")
        self.assertEqual(result["local"]["signal"]["reason"], result["local"]["signal"]["result"]["reason"])
        self.assertNotIn("\u9884\u70ed", result["local"]["signal"]["reason"])
        self.assertEqual(result["local"]["signal"]["row_count"], 99)
        self.assertEqual(result["strategy_context"]["strategy_params"]["fast_window"], 10)
        scope["build_strategy_signal_fn"].assert_called_once_with("dual_ma", result["strategy_context"]["strategy_params"])
        completed = data["candles"][:-1]
        expected = build_strategy_signal_fn("dual_ma", result["strategy_context"]["strategy_params"])(
            [row["close"] for row in completed], completed[-1]["close"], False, 0, 0)
        self.assertEqual(result["local"]["signal"]["result"]["action"], expected["action"])
        self.assertEqual(result["local"]["signal"]["result"]["reason"], expected["reason"])
        self.assertEqual(result["local"]["price"], data["candles"][-1]["close"])
        self.assertAlmostEqual(result["local"]["risk_config"]["manual_take_profit"], data["candles"][-1]["close"] * 1.1)
        self.assertEqual(result["analysis"]["deepseek"]["summary"], "模型解释")
        self.assertNotEqual(result["local"].get("reason"), "模型解释")
        scope["deepseek_chat"].assert_called_once()
        prompt = json.loads(scope["deepseek_chat"].call_args.args[0][1]["content"])
        self.assertEqual(prompt["chart_candles"][-1]["complete"], False)
        self.assertEqual(prompt["local_deterministic"]["signal"]["row_count"], 99)
        self.assert_no_fetch(scope)

    def test_59_complete_rows_do_not_invent_local_probability_or_original_signal(self):
        scope = namespace(); data = payload(60)
        data["candles"][-1]["complete"] = False
        result = scope["deepseek_strategy_snapshot_analysis"](data)
        self.assertTrue(result["ok"])
        self.assertFalse(result["local"]["ok"])
        self.assertIsNone(result["local"]["profit_probability"])
        self.assertFalse(result["local"]["signal"]["calculated"])
        self.assertEqual(result["local"]["signal"]["availability"], "INSUFFICIENT_COMPLETED_HISTORY")
        self.assertIn("\u9884\u70ed", result["local"]["signal"]["reason"])
        self.assertEqual(result["local"]["signal"]["row_count"], 59)
        self.assertEqual(result["local"]["signal"]["required_rows"], 80)
        scope["deepseek_chat"].assert_called_once()
        self.assert_no_fetch(scope)

    def test_unknown_completion_is_not_guessed_complete_and_price_digest_stays_six_fields(self):
        scope = namespace(); data = payload()
        annotated, first_identity, _ = scope["_market_ai_frontend_snapshot"]("AAPL", "5m", data["candles"], data["chart_context"])
        self.assertTrue(annotated[0]["complete"])
        self.assertEqual(first_identity["completion_counts"], {"total": 100, "complete": 100, "provisional": 0, "unknown": 0})
        for row in data["candles"]:
            row.pop("complete"); row.pop("provisional"); row.pop("source")
        _, second_identity, _ = scope["_market_ai_frontend_snapshot"]("AAPL", "5m", data["candles"], data["chart_context"])
        self.assertEqual(first_identity["rows_sha256"], second_identity["rows_sha256"])
        self.assertEqual(second_identity["completion_counts"], {"total": 100, "complete": 0, "provisional": 0, "unknown": 100})
        result = scope["deepseek_strategy_snapshot_analysis"](data)
        self.assertEqual(result["completion_counts"]["unknown"], 100)
        self.assertFalse(result["local"]["signal"]["calculated"])
        self.assertIsNone(result["local"]["profit_probability"])

    def test_invalid_session_completion_source_or_params_pause_before_model(self):
        cases = []
        data = payload(); data["chart_context"]["session"] = "pre"; cases.append(data)
        data = payload(); data["candles"][0]["complete"] = 1; cases.append(data)
        data = payload(); data["candles"][0]["provisional"] = True; cases.append(data)
        data = payload(); data["chart_context"]["snapshot_source"] = "client_quote_preview"; cases.append(data)
        data = payload(); data["strategy_params"]["fast_window"] = 60; cases.append(data)
        data = payload(); data["risk_config"]["takeProfitPct"] = "NaN"; cases.append(data)
        data = payload(); data["strategy_id"] = "unknown"; cases.append(data)
        for data in cases:
            scope = namespace(); result = scope["deepseek_strategy_snapshot_analysis"](data)
            self.assertFalse(result["ok"])
            self.assertTrue(result["local"]["analysis_paused"])
            self.assertEqual(result["deepseek"]["request_attempts"], 0)
            scope["deepseek_chat"].assert_not_called()
            self.assert_no_fetch(scope)

    def test_attested_daily_rows_keep_identity_and_edited_parameters(self):
        for include_model in (False, True):
            with self.subTest(include_model=include_model):
                scope = namespace(); data = daily_payload(); before = deepcopy(data)
                result = scope["deepseek_strategy_snapshot_analysis"](data, include_model=include_model)
                self.assertEqual(data, before)
                self.assertTrue(result["ok"])
                self.assertTrue(result["data_quality"]["structure_complete"])
                self.assertTrue(result["data_quality"]["temporal_conformance_complete"])
                self.assertFalse(result["data_quality"]["has_break"])
                self.assertEqual(result["input_identity"]["row_count"], 100)
                self.assertEqual(result["input_identity"]["source"], "YahooAdjusted")
                self.assertFalse(result["input_identity"]["source_authenticated"])
                self.assertEqual(result["strategy_context"]["strategy_params"], data["strategy_params"])
                self.assertTrue(result["local"]["signal"]["calculated"])
                self.assertEqual(scope["deepseek_chat"].call_count, int(include_model))
                self.assert_no_fetch(scope)

    def test_unverified_daily_rows_never_reach_local_signal_or_provider(self):
        for fault in ("missing_date", "date_timestamp_mismatch", "unknown_source", "unknown_completion"):
            with self.subTest(fault=fault):
                scope = namespace(); data = daily_payload()
                if fault == "missing_date":
                    for row in data["candles"]: row.pop("date")
                elif fault == "date_timestamp_mismatch":
                    data["candles"][0]["date"] = "2024-01-03"
                elif fault == "unknown_source":
                    data["chart_context"]["snapshot_source"] = "unverified-provider"
                    for row in data["candles"]: row["source"] = "unverified-provider"
                else:
                    data["candles"][0].pop("complete")
                    data["candles"][0].pop("provisional")
                result = scope["deepseek_strategy_snapshot_analysis"](data)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error_code"], "strategy_snapshot_quality_unverified")
                self.assertTrue(result["local"]["analysis_paused"])
                self.assertEqual(result["deepseek"]["request_attempts"], 0)
                scope["build_strategy_signal_fn"].assert_not_called()
                scope["deepseek_chat"].assert_not_called()
                self.assert_no_fetch(scope)

    def test_daily_price_scale_break_keeps_the_quality_gate_closed(self):
        scope = namespace(); data = daily_payload()
        for row in data["candles"][-5:]:
            for key in ("open", "high", "low", "close"):
                row[key] /= 4
        result = scope["deepseek_strategy_snapshot_analysis"](data)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_code"], "strategy_snapshot_scale_break")
        scope["deepseek_chat"].assert_not_called()
        self.assert_no_fetch(scope)

    def test_model_failure_preserves_local_rule_receipt_and_safe_error(self):
        scope = namespace()
        scope["deepseek_chat"].return_value = {"ok": False, "configured": True, "error": "DeepSeek API 余额不足", "error_code": "insufficient_balance", "request_attempts": 1}
        result = build_deepseek_projection(scope["deepseek_strategy_snapshot_analysis"](payload()))
        self.assertFalse(result["ok"])
        self.assertEqual(result["deepseek"]["error_code"], "insufficient_balance")
        self.assertTrue(result["local"]["signal"]["calculated"])
        self.assertEqual(result["local"]["signal"]["engine_version"], SIGNAL_ENGINE_VERSION)
        self.assertFalse(result["local"]["signal"]["execution_allowed"])
        self.assertTrue(result["local"]["signal"]["result"]["action"].startswith("RESEARCH_"))
        self.assertEqual(result["analysis"]["deepseek"], {})
        self.assertIsInstance(result["status"], dict)
        self.assertTrue(result["status"]["configured"])
        self.assertEqual(result["provider_status"]["model"], "deepseek-v4-pro")
        self.assertFalse(result["order_allowed"])

    def test_local_only_mode_reuses_identical_calculation_without_calling_model(self):
        scope = namespace()
        result = scope["deepseek_strategy_snapshot_analysis"](payload(), include_model=False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["analysis_status"], "LOCAL_ONLY")
        self.assertTrue(result["local"]["signal"]["calculated"])
        self.assertTrue(result["deepseek"]["skipped"])
        self.assertEqual(result["deepseek"]["request_attempts"], 0)
        scope["deepseek_chat"].assert_not_called()
        self.assert_no_fetch(scope)

    def test_macd_period_survives_actual_post_projection_without_direction_authority(self):
        handler = next(node for node in ast.walk(TREE) if isinstance(node, ast.FunctionDef) and node.name == "do_POST")
        strategy = {"id": "macd", "name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}}
        for path, local_only in (("/api/ai/deepseek/analyze", False), ("/api/strategy/analyze", True)):
            with self.subTest(path=path):
                scope = namespace()
                scope["choose_strategy"] = lambda _: deepcopy(strategy)
                scope.update({"urllib": SimpleNamespace(parse=urllib.parse), "POST_API_PATHS": POST_API_PATHS,
                              "MUTATION_PATHS": MUTATION_PATHS, "RUNTIME_READ_ONLY": False, "LOCAL_ONLY": False,
                              "block_non_loopback_client": lambda _: False, "QUANT_WORKSPACE": SimpleNamespace(handle=lambda _: False),
                              "allowed_cors_origin": lambda _: True, "json_response": Mock(),
                              "build_deepseek_projection": build_deepseek_projection})
                exec(compile(ast.Module(body=[handler], type_ignores=[]), str(SERVER), "exec"), scope)
                data = payload(); data["strategy_id"] = "macd"; data["strategy_params"] = dict(strategy["params"])
                raw = json.dumps(data).encode()
                request = SimpleNamespace(path=path, headers={"Content-Length": str(len(raw)), "Origin": "http://127.0.0.1:8765"}, rfile=io.BytesIO(raw))
                scope["do_POST"](request)
                result = scope["json_response"].call_args.args[1]
                self.assertTrue(result["ok"])
                self.assertEqual(result["strategy_context"]["strategy_params"], strategy["params"])
                for section in ("local", "analysis"):
                    self.assertEqual(result[section]["strategy_params"], strategy["params"])
                    signal = result[section]["signal"]
                    self.assertEqual(signal["strategy_params"], strategy["params"])
                    self.assertTrue(signal["calculated"])
                    self.assertTrue(signal["result"]["action"].startswith("RESEARCH_"))
                    self.assertFalse(signal["execution_allowed"])
                self.assertFalse(result["order_allowed"])
                self.assertEqual(scope["deepseek_chat"].call_count, 0 if local_only else 1)
                self.assert_no_fetch(scope)

    def test_post_routes_are_allowed_bounded_and_preserve_existing_request_guards(self):
        handler = next(node for node in ast.walk(TREE) if isinstance(node, ast.FunctionDef) and node.name == "do_POST")
        for path, local_only in (("/api/ai/deepseek/analyze", False), ("/api/strategy/analyze", True)):
            scope = namespace()
            scope.update({"urllib": SimpleNamespace(parse=urllib.parse), "POST_API_PATHS": POST_API_PATHS,
                          "MUTATION_PATHS": MUTATION_PATHS, "RUNTIME_READ_ONLY": False, "LOCAL_ONLY": False,
                          "block_non_loopback_client": lambda _: False, "QUANT_WORKSPACE": SimpleNamespace(handle=lambda _: False),
                          "allowed_cors_origin": lambda _: True, "json_response": Mock(),
                          "build_deepseek_projection": build_deepseek_projection})
            exec(compile(ast.Module(body=[handler], type_ignores=[]), str(SERVER), "exec"), scope)
            raw = json.dumps(payload()).encode()
            self.assertGreater(len(raw), 4096)
            request = SimpleNamespace(path=path, headers={"Content-Length": str(len(raw)), "Origin": "http://127.0.0.1:8765"}, rfile=io.BytesIO(raw))
            scope["do_POST"](request)
            result = scope["json_response"].call_args.args[1]
            self.assertTrue(result["ok"])
            self.assertEqual(scope["deepseek_chat"].call_count, 0 if local_only else 1)
            scope["RUNTIME_READ_ONLY"] = True
            request.rfile = io.BytesIO(raw)
            scope["do_POST"](request)
            result = scope["json_response"].call_args.args[1]
            self.assertTrue(result["ok"])
            self.assertTrue(result["read_only"])
            self.assertFalse(result["order_allowed"])
            self.assertFalse(result["paper_authorized"])
            self.assertFalse(result["live_order_allowed"])
            self.assertEqual(scope["deepseek_chat"].call_count, 0 if local_only else 2)
            write_request = SimpleNamespace(path="/api/profile/settings", headers=request.headers, rfile=io.BytesIO(b"{}"))
            scope["do_POST"](write_request)
            self.assertEqual(scope["json_response"].call_args.args[2], 423)
            self.assertEqual(scope["deepseek_chat"].call_count, 0 if local_only else 2)
            scope["RUNTIME_READ_ONLY"] = False
            scope["allowed_cors_origin"] = lambda _: False
            scope["do_POST"](request)
            self.assertEqual(scope["json_response"].call_args.args[2], 403)
            self.assertEqual(scope["deepseek_chat"].call_count, 0 if local_only else 2)


if __name__ == "__main__":
    unittest.main()
