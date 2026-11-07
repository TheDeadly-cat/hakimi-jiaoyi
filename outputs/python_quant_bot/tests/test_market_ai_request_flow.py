"""Offline tests of the real request functions; no server import or model access."""
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
import urllib.error
import urllib.request

from hakimi_research.stock_candle_quality import analyze_stock_candle_series, stock_candle_quality_public
from exchange_terminal.services.market_calendar import resolve_stock_candle_schedule_attestation
from exchange_terminal.services.market_ai_projection import build_market_ai_projection


SERVER = Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
SOURCE = SERVER.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
NAMES = {"openai_chat", "openai_message_text", "extract_json_object", "_market_ai_frontend_snapshot",
         "market_dual_ai_analysis", "local_market_ai_analysis", "normalize_frontend_candles",
         "true_range_average", "market_ai_drawing_levels", "market_ai_system_prompt"}
FUNCTIONS = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in NAMES]


def candles(count=40):
    return [{"ts": 1700000000000 + index * 86400000, "open": 100 + index / 10,
             "high": 102 + index / 10, "low": 99 + index / 10, "close": 101 + index / 10, "volume": 1000 + index}
            for index in range(count)]


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


def namespace(*, deepseek=False, openai=True):
    transport = SimpleNamespace(Request=urllib.request.Request, urlopen=Mock(side_effect=AssertionError("network disabled")))
    scope = {"Any": Any, "json": json, "hashlib": hashlib, "math": math,
             "os": SimpleNamespace(getenv=lambda name, default=None: default),
             "urllib": SimpleNamespace(request=transport, error=urllib.error),
             "runtime_secret": lambda *names: (names[0], "test-only-credential", "test"),
             "OPENAI_MODEL": "gpt-4o-mini", "OPENAI_BASE_URL": "https://api.openai.com/v1",
             "LIVE_TRADING_HARD_BLOCK": True, "now_ms": lambda: 123,
             "pct": lambda value, default=0: float(value or default),
             "average": lambda values: sum(values) / max(len(values), 1),
             "clamp": lambda value, low, high: max(low, min(high, value)),
             "recent_volatility": lambda *args: 0.01, "trend_score": lambda *args: 0.1,
             "safe_volume_ratio": lambda *args: 1.0, "estimate_hit_probability": lambda *args: 0.5,
             "is_stock_symbol": lambda symbol: symbol == "AAPL",
             "resolve_stock_candle_schedule_attestation": resolve_stock_candle_schedule_attestation,
        "analyze_stock_candle_series": analyze_stock_candle_series, "stock_candle_quality_public": stock_candle_quality_public,
             "deepseek_status": lambda: {"configured": deepseek, "model": "deepseek-test"},
             "openai_status": lambda: {"configured": openai, "model": "gpt-4o-mini"},
             "market_ai_candles": Mock(side_effect=AssertionError("must not fetch replacement candles")),
             "market_insights": Mock(side_effect=AssertionError("must not fetch extra market data")),
             "contract_center": Mock(side_effect=AssertionError("must not fetch extra contract data")),
             "deepseek_chat": Mock(return_value={"ok": True, "json": {"summary": "deepseek test"}})}
    exec(compile(ast.Module(body=FUNCTIONS, type_ignores=[]), str(SERVER), "exec"), scope)
    return scope, transport


def response(content='{"summary":"test only"}'):
    raw = json.dumps({"model": "gpt-4o-mini", "choices": [{"message": {"content": content}}], "usage": {"completion_tokens": 8}}).encode()
    return io.BytesIO(raw)


def http_error(status, *, code="invalid_api_key", issue_type="invalid_request_error", parameter=None, message="Incorrect API key provided: sk-test-secret-prefix", headers=None):
    raw = json.dumps({"error": {"code": code, "type": issue_type, "param": parameter, "message": message}}).encode()
    return urllib.error.HTTPError("https://api.openai.com/v1/chat/completions", status, "provider error", headers or {}, io.BytesIO(raw))


class OpenAiRetryTests(unittest.TestCase):
    def test_ordinary_http_errors_never_retry_or_echo_provider_credentials(self):
        for status in (400, 401, 403, 429, 500, 503):
            for retry in (False, True):
                with self.subTest(status=status, retry=retry):
                    scope, transport = namespace()
                    transport.urlopen.side_effect = http_error(status)
                    result = scope["openai_chat"]([], "test", allow_compatibility_retry=retry)
                    self.assertFalse(result["ok"])
                    self.assertEqual(transport.urlopen.call_count, 1)
                    self.assertEqual(result["request_attempts"], 1)
                    self.assertNotIn("sk-", json.dumps(result))
                    self.assertNotIn("test-only-credential", json.dumps(result))

    def test_default_and_explicit_disabled_retry_make_exactly_one_attempt(self):
        for kwargs in ({}, {"allow_compatibility_retry": False}):
            scope, transport = namespace()
            transport.urlopen.side_effect = http_error(400, code="unsupported_parameter", parameter="max_tokens")
            result = scope["openai_chat"]([], "test", **kwargs)
            self.assertFalse(result["ok"])
            self.assertEqual(transport.urlopen.call_count, 1)

    def test_explicit_compatibility_retry_changes_only_reported_present_parameter(self):
        for status, parameter, code in ((400, "temperature", "unsupported_value"), (422, "max_tokens", "unsupported_parameter")):
            scope, transport = namespace()
            transport.urlopen.side_effect = [http_error(status, code=code, parameter=parameter), response()]
            result = scope["openai_chat"]([], "test", 256, allow_compatibility_retry=True)
            sent = [json.loads(call.args[0].data) for call in transport.urlopen.call_args_list]
            self.assertEqual(result["request_attempts"], 2)
            self.assertTrue(result["compatibility_retried"])
            self.assertNotIn(parameter, sent[1])
            if parameter == "temperature":
                self.assertEqual(sent[1]["max_tokens"], 256)
            else:
                self.assertEqual(sent[1]["max_completion_tokens"], 256)
                self.assertEqual(sent[1]["temperature"], 0.15)

    def test_unrelated_or_unstructured_error_cannot_trigger_compatibility_retry(self):
        for status, code, parameter in ((400, "unsupported_parameter", "not_sent"), (400, "invalid_request_error", "max_tokens"), (429, "unsupported_parameter", "max_tokens")):
            scope, transport = namespace()
            transport.urlopen.side_effect = http_error(status, code=code, parameter=parameter)
            result = scope["openai_chat"]([], "test", allow_compatibility_retry=True)
            self.assertFalse(result["ok"])
            self.assertEqual(transport.urlopen.call_count, 1)

    def test_transport_failure_is_not_retried_or_echoed(self):
        scope, transport = namespace()
        transport.urlopen.side_effect = TimeoutError("private diagnostic sk-test-secret-prefix")
        result = scope["openai_chat"]([], "test", allow_compatibility_retry=True)
        self.assertEqual(transport.urlopen.call_count, 1)
        self.assertNotIn("sk-", json.dumps(result))
        self.assertFalse(result["automatic_retry"])


class OpenAiQuotaClassificationTests(unittest.TestCase):
    def classify(self, **kwargs):
        scope, transport = namespace()
        transport.urlopen.side_effect = http_error(429, **kwargs)
        result = scope["openai_chat"]([], "test", allow_compatibility_retry=True)
        self.assertFalse(result["ok"])
        self.assertEqual(transport.urlopen.call_count, 1)
        self.assertEqual(result["request_attempts"], 1)
        self.assertFalse(result["automatic_retry"])
        self.assertNotIn("sk-", json.dumps(result))
        return result

    def test_confirmed_credit_balance_shape_survives_actual_market_projection(self):
        scope, transport = namespace()
        transport.urlopen.side_effect = http_error(
            429, code="credit_balance_exhausted", issue_type="insufficient_quota",
            message="You have no credits remaining. Add credits. sk-test-secret-prefix",
        )
        result = build_market_ai_projection(scope["market_dual_ai_analysis"](MarketAiSnapshotTests().payload()))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"]["analysis"], "unavailable")
        self.assertEqual(result["gpt"]["error_code"], "credit_balance_exhausted")
        self.assertIn("余额已用完", result["gpt"]["error"])
        self.assertIn("充值", result["gpt"]["error"])
        self.assertNotIn("限流", result["gpt"]["error"])
        self.assertNotIn("sk-", json.dumps(result))
        self.assertNotIn("You have no credits", json.dumps(result))
        self.assertEqual(result["gpt"]["request_attempts"], 1)
        self.assertEqual(transport.urlopen.call_count, 1)

    def test_spend_and_usage_limits_have_distinct_safe_remediation(self):
        cases = (
            ("organization_spend_limit_exceeded", "组织消费"),
            ("project_spend_limit_exceeded", "项目消费"),
            ("organization_usage_limit_exceeded", "组织 API 使用额度"),
        )
        for code, phrase in cases:
            with self.subTest(code=code):
                result = self.classify(code=code, issue_type="insufficient_quota")
                self.assertEqual(result["error_code"], code)
                self.assertIn(phrase, result["error"])
                self.assertNotIn("充值", result["error"])
                self.assertNotIn("retry_after_seconds", result)

    def test_unknown_or_generic_code_cannot_hide_recognized_quota_type(self):
        for code in ("unknown_sk-private-code", "invalid_request_error", None):
            result = self.classify(code=code, issue_type="insufficient_quota")
            self.assertEqual(result["error_code"], "insufficient_quota")
            self.assertIn("配额不足", result["error"])

    def test_rate_limits_parse_only_bounded_numeric_retry_after_without_retry(self):
        for code in ("rate_limit_exceeded", "slow_down"):
            result = self.classify(code=code, headers={"Retry-After": "2.5"})
            self.assertEqual(result["error_code"], code)
            self.assertEqual(result["retry_after_seconds"], 2.5)
            self.assertNotIn("余额", result["error"])
            for header in ("nan", "inf", "-1", "86401", "Wed, 21 Oct 2026 07:28:00 GMT", "sk-private-header"):
                result = self.classify(code=code, headers={"Retry-After": header})
                self.assertNotIn("retry_after_seconds", result)

    def test_rate_limit_type_is_recognized_but_explicit_quota_keeps_priority(self):
        for code in (None, "unknown", "invalid_request_error"):
            result = self.classify(code=code, issue_type="rate_limit_error")
            self.assertEqual(result["error_code"], "rate_limit_exceeded")
            self.assertIn("速率限制", result["error"])
        result = self.classify(code="credit_balance_exhausted", issue_type="rate_limit_error")
        self.assertEqual(result["error_code"], "credit_balance_exhausted")
        result = self.classify(code="rate_limit_exceeded", issue_type="insufficient_quota")
        self.assertEqual(result["error_code"], "insufficient_quota")

    def test_unknown_429_remains_unknown_instead_of_guessing_from_raw_message(self):
        result = self.classify(code="unrecognized", issue_type="unrecognized", message="No credits or rate limit? sk-private-message")
        self.assertEqual(result["error_code"], "provider_request_failed")
        self.assertIn("无法判定", result["error"])
        self.assertNotIn("No credits", result["error"])

    def test_meeting_summary_prefers_safe_error_code_over_legacy_error_body(self):
        nodes = [node for node in ast.walk(TREE) if isinstance(node, ast.FunctionDef) and node.name in {"_note_body", "_note_summary"}]
        scope = {"Any": Any, "json": json}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SERVER), "exec"), scope)
        result = scope["_note_summary"]({
            "provider": "openai", "ok": False, "http_status": 429,
            "error_code": "credit_balance_exhausted",
            "http_error": '{"error":{"code":"rate_limit_exceeded","message":"sk-private-legacy"}}',
            "error": "sk-private-error",
        })
        self.assertIn("余额已用完", result)
        self.assertIn("充值", result)
        self.assertNotIn("sk-", result)
        unknown = scope["_note_summary"]({"provider": "openai", "http_status": 429, "error_code": "provider_request_failed", "error": "sk-private-error"})
        self.assertIn("无法判定", unknown)
        self.assertNotIn("sk-", unknown)


class OpenAiResponseTests(unittest.TestCase):
    def call(self, payload):
        scope, transport = namespace()
        transport.urlopen.side_effect = None
        transport.urlopen.return_value = io.BytesIO(json.dumps(payload).encode())
        result = scope["openai_chat"]([], "test", allow_compatibility_retry=True)
        self.assertEqual(transport.urlopen.call_count, 1)
        self.assertEqual(result["request_attempts"], 1)
        return result

    def test_empty_and_malformed_responses_fail_safely_without_retry(self):
        cases = [None, [], "sk-private-example", {}, {"choices": []}, {"choices": {}}, {"choices": [None]},
                 {"choices": [{"message": None}]}, {"choices": [{"message": {"content": 123}}]},
                 {"choices": [{"message": {"content": ["sk-private-example"]}}]},
                 {"error": {"message": "sk-private-example"}},
                 *({"choices": [{"message": {"content": value}}]} for value in (None, "", "  ", []))]
        for payload in cases:
            with self.subTest(shape=type(payload).__name__):
                result = self.call(payload)
                self.assertFalse(result["ok"])
                self.assertIn(result["error_code"], {"empty_response", "invalid_response"})
                self.assertFalse(result["automatic_retry"])
                self.assertNotIn("sk-", json.dumps(result))

    def test_refusal_and_filter_use_fixed_failure_without_raw_response(self):
        for message, finish in (({"content": None, "refusal": "sk-private-refusal"}, "stop"),
                                ({"content": "sk-private-filter"}, "content_filter")):
            result = self.call({"choices": [{"message": message, "finish_reason": finish}]})
            self.assertFalse(result["ok"])
            self.assertEqual(result["error_code"], "response_refused")
            self.assertNotIn("sk-", json.dumps(result))

    def test_length_finish_is_incomplete_even_if_text_is_valid_json(self):
        for content in ('{"summary":"only partial"}', 'truncated text', None):
            result = self.call({"choices": [{"message": {"content": content}, "finish_reason": "length"}]})
            self.assertFalse(result["ok"])
            self.assertTrue(result["incomplete"])
            self.assertEqual(result["completion_status"], "incomplete")
            self.assertEqual(result["finish_reason"], "length")
            self.assertEqual(result["content"], content or "")
            self.assertIsNone(result["json"])
            self.assertFalse(result["automatic_retry"])

    def test_nonempty_plain_text_and_supported_text_blocks_remain_displayable(self):
        for content in ("Public market explanation.", [{"type": "text", "text": "Public market explanation."}]):
            result = self.call({"choices": [{"message": {"content": content}, "finish_reason": "stop"}]})
            self.assertTrue(result["ok"])
            self.assertEqual(result["content"], "Public market explanation.")
            self.assertIsNone(result["json"])
            self.assertFalse(result["incomplete"])
            self.assertEqual(result["completion_status"], "complete")


class MarketAiSnapshotTests(unittest.TestCase):
    def payload(self, symbol="BTC-USDT"):
        return {"symbol": symbol, "bar": "1Dutc", "price": 999999, "question": "Explain this public test data.",
                "candles": candles(), "max_output_tokens": 256,
                "chart_context": {"snapshot_source": "test-public-declaration", "shared_snapshot": {"symbol": symbol, "bar": "1d", "snapshot_id": "test-snapshot"}}}

    def stock_payload(self):
        data = self.payload("AAPL")
        data["candles"] = stock_daily_candles(40)
        data["chart_context"]["snapshot_source"] = "YahooAdjusted"
        data["chart_context"]["session"] = "regular"
        data["chart_context"]["shared_snapshot"]["session"] = "regular"
        return data

    def assert_no_external(self, scope, transport):
        scope["market_ai_candles"].assert_not_called()
        scope["market_insights"].assert_not_called()
        scope["contract_center"].assert_not_called()
        scope["deepseek_chat"].assert_not_called()
        transport.urlopen.assert_not_called()

    def test_openai_only_uses_exact_chart_and_reports_partial_without_fake_review(self):
        scope, transport = namespace()
        transport.urlopen.side_effect = None
        transport.urlopen.return_value = response()
        payload = self.payload(); before = deepcopy(payload)
        result = scope["market_dual_ai_analysis"](payload)
        self.assertEqual(payload, before)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"]["analysis"], "partial")
        self.assertEqual(result["status"]["providers_completed"], ["openai"])
        self.assertTrue(result["deepseek"]["skipped"])
        self.assertEqual(transport.urlopen.call_count, 1)
        sent = json.loads(transport.urlopen.call_args.args[0].data)
        self.assertEqual(sent["max_tokens"], 256)
        prompt = json.loads(sent["messages"][1]["content"])
        self.assertNotIn("deepseek_first_pass", prompt)
        self.assertEqual(prompt["price"], payload["candles"][-1]["close"])
        self.assertEqual(result["input_identity"]["row_count"], 40)
        self.assertFalse(result["input_identity"]["source_authenticated"])
        self.assertEqual(result["external_supplement"]["status"], "SKIPPED")
        scope["deepseek_chat"].assert_not_called()
        scope["market_ai_candles"].assert_not_called()
        scope["market_insights"].assert_not_called()
        scope["contract_center"].assert_not_called()

    def test_deepseek_only_and_dual_provider_paths_remain_available(self):
        for openai in (False, True):
            scope, transport = namespace(deepseek=True, openai=openai)
            transport.urlopen.side_effect = None; transport.urlopen.return_value = response()
            result = scope["market_dual_ai_analysis"](self.payload())
            scope["deepseek_chat"].assert_called_once()
            self.assertEqual(result["status"]["analysis"], "complete" if openai else "partial")
            self.assertEqual(transport.urlopen.call_count, int(openai))
            if openai:
                sent=json.loads(transport.urlopen.call_args.args[0].data)
                self.assertIn("deepseek_first_pass", json.loads(sent["messages"][1]["content"]))
            else:
                self.assertTrue(result["gpt"]["skipped"])

    def test_no_configured_provider_is_unavailable_not_success(self):
        scope, transport = namespace(openai=False)
        result = scope["market_dual_ai_analysis"](self.payload())
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"]["analysis"], "unavailable")
        self.assert_no_external(scope, transport)

    def test_invalid_supplied_rows_or_context_pause_without_fetch_or_model(self):
        cases=[]
        for value in (None, [], candles(29), candles(301)):
            payload=self.payload();payload["candles"]=value;cases.append(payload)
        for field, value in (("ts", 0), ("close", math.nan), ("volume", math.inf), ("open", True), ("low", 200), ("high", 1)):
            payload=self.payload();payload["candles"][1][field]=value;cases.append(payload)
        payload=self.payload();payload["candles"][1]["ts"]=payload["candles"][0]["ts"];cases.append(payload)
        for field, value in (("symbol", "AAPL"), ("bar", "1h")):
            payload=self.payload();payload["chart_context"]["shared_snapshot"][field]=value;cases.append(payload)
        payload=self.payload();payload["chart_context"]=None;cases.append(payload)
        for index,payload in enumerate(cases):
            with self.subTest(case=index):
                scope, transport=namespace()
                result=scope["market_dual_ai_analysis"](payload)
                self.assertEqual(result["status"]["analysis"], "paused_data_quality")
                self.assert_no_external(scope, transport)

    def test_attested_stock_daily_chart_preserves_temporal_metadata(self):
        scope, transport = namespace()
        transport.urlopen.side_effect = None; transport.urlopen.return_value = response()
        payload = self.stock_payload(); before = deepcopy(payload)
        result = scope["market_dual_ai_analysis"](payload)
        self.assertEqual(payload, before)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"]["analysis"], "partial")
        self.assertTrue(result["local"]["data_quality"]["structure_complete"])
        self.assertTrue(result["local"]["data_quality"]["temporal_conformance_complete"])
        self.assertFalse(result["local"]["data_quality"]["has_break"])
        self.assertEqual(result["input_identity"]["row_count"], 40)
        self.assertFalse(result["input_identity"]["source_authenticated"])
        self.assertEqual(transport.urlopen.call_count, 1)
        scope["deepseek_chat"].assert_not_called()
        for name in ("market_ai_candles", "market_insights", "contract_center"):
            scope[name].assert_not_called()

    def test_unverified_stock_daily_rows_pause_without_any_provider(self):
        for fault in ("missing_date", "date_timestamp_mismatch", "unknown_source", "unknown_completion"):
            with self.subTest(fault=fault):
                scope, transport = namespace(deepseek=True)
                payload = self.stock_payload()
                if fault == "missing_date":
                    for row in payload["candles"]: row.pop("date")
                elif fault == "date_timestamp_mismatch":
                    payload["candles"][0]["date"] = "2024-01-03"
                elif fault == "unknown_source":
                    payload["chart_context"]["snapshot_source"] = "unverified-provider"
                    for row in payload["candles"]: row["source"] = "unverified-provider"
                else:
                    payload["candles"][0].pop("complete")
                    payload["candles"][0].pop("provisional")
                result = scope["market_dual_ai_analysis"](payload)
                self.assertEqual(result["status"]["analysis"], "paused_data_quality")
                self.assertFalse(result["local"]["data_quality"]["temporal_conformance_complete"])
                self.assertEqual(result["deepseek"]["request_attempts"], 0)
                self.assertEqual(result["gpt"]["request_attempts"], 0)
                self.assert_no_external(scope, transport)

    def test_actual_stock_scale_break_gate_remains_closed(self):
        scope, transport=namespace()
        payload=self.stock_payload()
        for row in payload["candles"][-5:]:
            for key in ("open","high","low","close"):row[key]/=4
        result=scope["market_dual_ai_analysis"](payload)
        self.assertEqual(result["status"]["analysis"], "paused_data_quality")
        self.assertTrue(result["local"]["analysis_paused"])
        self.assertTrue(result["local"]["data_quality"]["temporal_conformance_complete"])
        self.assertTrue(result["local"]["data_quality"]["has_break"])
        self.assert_no_external(scope, transport)

    def test_absent_candles_preserves_legacy_fetch_path(self):
        scope, transport=namespace(openai=False)
        scope["market_ai_candles"].side_effect=None;scope["market_ai_candles"].return_value={"bar":"1H","source":"test-legacy","candles":candles()}
        scope["market_insights"].side_effect=None;scope["market_insights"].return_value={"ok":True}
        scope["contract_center"].side_effect=None;scope["contract_center"].return_value={"ok":True}
        result=scope["market_dual_ai_analysis"]({"symbol":"BTC-USDT","bar":"1H"})
        scope["market_ai_candles"].assert_called_once();scope["market_insights"].assert_called_once();scope["contract_center"].assert_called_once()
        self.assertEqual(result["external_supplement"]["status"], "REQUESTED")
        transport.urlopen.assert_not_called()

    def test_short_output_uses_a_bounded_summary_instead_of_the_full_trade_schema(self):
        for limit in (768, 1800):
            scope, transport = namespace()
            transport.urlopen.side_effect = None
            transport.urlopen.return_value = response()
            payload = self.payload()
            payload["max_output_tokens"] = limit
            result = scope["market_dual_ai_analysis"](payload)
            self.assertTrue(result["ok"])
            self.assertEqual(transport.urlopen.call_count, 1)
            sent = json.loads(transport.urlopen.call_args.args[0].data)
            context = json.loads(sent["messages"][1]["content"])
            self.assertEqual("long_win_rate_pct" in context["output_schema"], limit == 1800)
            self.assertEqual("final_decision" in context["output_schema"], limit == 1800)
            self.assertEqual(sent["max_tokens"], limit)

    def test_output_limit_rejects_invalid_values_before_any_request(self):
        for value in (127,1801,True,"256"):
            scope,transport=namespace();payload=self.payload();payload["max_output_tokens"]=value
            with self.assertRaisesRegex(ValueError,"max_output_tokens"):
                scope["market_dual_ai_analysis"](payload)
            self.assert_no_external(scope,transport)


if __name__ == "__main__":
    unittest.main()
