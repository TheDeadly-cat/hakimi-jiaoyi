"""Display contracts against existing native defaults, without running research."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import unittest

from exchange_terminal.services.strategy_presentation import (
    PRESENTATION_VERSION,
    strategy_parameter_fields,
    strategy_presentation,
)
from exchange_terminal.services.terminal_research import validate_terminal_strategy_params, terminal_strategy_presentation


def original_catalog():
    # Reading the literal avoids importing the server and initializing runtime.
    source = Path(__file__).parents[1] / "exchange_terminal" / "server.py"
    for node in ast.parse(source.read_text(encoding="utf-8-sig")).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "STRATEGIES" for target in node.targets):
            return {row["id"]: row for row in ast.literal_eval(node.value)}
    raise AssertionError("Original catalog literal not found")


class StrategyPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = original_catalog()

    def test_actual_strategy_api_normalizes_display_without_mutating_fingerprint_source(self):
        from types import SimpleNamespace
        from exchange_terminal.services.strategy_signals import strategy_validation_capability
        from exchange_terminal.services.strategy_risk_profiles import strategy_research_risk_profile
        from exchange_terminal.services.http_contract import RETIRED_MANAGEMENT_PATHS
        source = Path(__file__).parents[1] / "exchange_terminal" / "server.py"
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        handler = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ExchangeTerminalHandler")
        method = next(node for node in handler.body if isinstance(node, ast.FunctionDef) and node.name == "handle_api")
        responses, strategies = [], list(deepcopy(self.catalog).values())
        before = deepcopy(strategies)
        namespace = {"LOCAL_ONLY": True, "RETIRED_MANAGEMENT_PATHS": RETIRED_MANAGEMENT_PATHS,
                     "archived_execution_route_state": lambda *_: "READ",
                     "STRATEGIES": strategies, "terminal_strategy_presentation": terminal_strategy_presentation,
                     "strategy_validation_capability": strategy_validation_capability,
                     "strategy_research_risk_profile": strategy_research_risk_profile,
                     "json_response": lambda _self, data, *args: responses.append(data), "Any": object}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(source), "exec"), namespace)
        namespace["handle_api"](SimpleNamespace(command="GET"), "/api/strategies", {})
        items = {row["id"]: row for row in responses[0]["strategies"]}
        self.assertEqual(strategies, before)
        self.assertEqual(items["volume_trend"]["params"]["atr_window"], 14)
        self.assertEqual(items["volume_trend"]["params"]["fast_window"], 50)
        self.assertEqual(items["volume_trend"]["params"]["max_extension_pct"], .12)
        threshold = next(field for field in items["momentum"]["parameter_fields"] if field["key"] == "threshold")
        self.assertEqual(threshold["display_scale"], 100)
        self.assertEqual(threshold["value"], .015)
        self.assertIn("快均线高于慢均线", items["dual_ma"]["research_description"])
        self.assertIn("无需当日发生", "".join(items["dual_ma"]["rule_notes"]))

    def test_nine_research_strategies_receive_metadata_without_granting_capability(self):
        supported = {"dual_ma", "bollinger", "macd", "rsi", "momentum", "livermore", "turtle", "darvas", "volume_trend"}
        for identity, row in self.catalog.items():
            before = deepcopy(row)
            display = strategy_presentation(identity, row["params"])
            self.assertEqual(bool(display), identity in supported)
            self.assertEqual(row, before)
            if display:
                self.assertEqual(display["presentation_version"], PRESENTATION_VERSION)
                self.assertNotIn("params", display)
                self.assertNotIn("capability", display)
                self.assertNotIn("implementation_fingerprint", display)
        self.assertEqual(strategy_presentation("unknown", {}), {})

    def test_normalized_catalog_values_are_authoritative_including_volume_overrides(self):
        expected = {
            "dual_ma": {"fast_window": 20, "slow_window": 60},
            "bollinger": {"window": 20, "std_mult": 2.0},
            "macd": {"fast": 12, "slow": 26, "signal": 9},
            "rsi": {"window": 14, "oversold": 30, "overbought": 70},
            "momentum": {"window": 20, "threshold": .015},
            "livermore": {"pivot_window": 60, "confirm_pct": .006},
            "turtle": {"entry_window": 20, "exit_window": 10},
            "darvas": {"box_window": 40, "confirm_pct": .004},
            "volume_trend": {"trend_window": 100, "fast_window": 50, "breakout_window": 20,
                "exit_window": 10, "volume_window": 20, "atr_window": 14, "volume_ratio": 1.1,
                "min_atr_pct": .01, "max_atr_pct": .08, "max_extension_pct": .12},
        }
        for identity, values in expected.items():
            with self.subTest(strategy=identity):
                canonical = validate_terminal_strategy_params(self.catalog[identity], {})
                before = deepcopy(canonical)
                fields = strategy_parameter_fields(identity, canonical)
                self.assertEqual({item["key"]: item["value"] for item in fields}, values)
                self.assertTrue(all(item["recorded"] for item in fields))
                self.assertEqual(canonical, before)
                self.assertNotIn("position_pct", {item["key"] for item in fields})
                self.assertNotIn("take_profit_atr", {item["key"] for item in fields})

    def test_percent_ratio_multiplier_oscillator_and_count_units_are_distinct(self):
        examples = [
            ("momentum", "threshold", .015, "ratio_percent", 100, "%", 1.5),
            ("livermore", "confirm_pct", .006, "ratio_percent", 100, "%", .6),
            ("darvas", "confirm_pct", .004, "ratio_percent", 100, "%", .4),
            ("volume_trend", "min_atr_pct", .01, "ratio_percent", 100, "%", 1),
            ("volume_trend", "max_atr_pct", .08, "ratio_percent", 100, "%", 8),
            ("volume_trend", "max_extension_pct", .12, "ratio_percent", 100, "%", 12),
            ("volume_trend", "volume_ratio", 1.1, "multiplier", 1, "倍", 1.1),
            ("bollinger", "std_mult", 2, "multiplier", 1, "倍", 2),
            ("rsi", "oversold", 30, "oscillator_points", 1, "点", 30),
            ("macd", "signal", 9, "count", 1, "根", 9),
        ]
        for identity, key, raw, kind, scale, unit, shown in examples:
            with self.subTest(strategy=identity, parameter=key):
                item = next(field for field in strategy_parameter_fields(identity, {key: raw}) if field["key"] == key)
                self.assertEqual((item["unit"], item["display_scale"], item["display_unit"]), (kind, scale, unit))
                self.assertAlmostEqual(item["value"] * scale, shown)
                self.assertEqual(item["step"], 1 if kind == "count" else "any")
                self.assertEqual(item["display_minimum"], item["minimum"] * scale)
                self.assertEqual(item["display_maximum"], item["maximum"] * scale)

    def test_historical_missing_fields_are_not_defaulted_and_unknown_fields_are_untouched(self):
        saved = {"fast_window": 50, "position_pct": .22, "future_metadata": {"note": "keep"}}
        before = json.dumps(saved, ensure_ascii=False, sort_keys=True)
        fields = strategy_parameter_fields("volume_trend", saved)
        known = {field["key"]: field for field in fields}
        self.assertEqual(known["fast_window"]["value"], 50)
        for key in ("atr_window", "min_atr_pct", "max_atr_pct", "max_extension_pct"):
            self.assertFalse(known[key]["recorded"])
            self.assertNotIn("value", known[key])
            self.assertEqual(known[key]["missing_text"], "未记录")
        self.assertNotIn("position_pct", known)
        self.assertNotIn("future_metadata", known)
        self.assertEqual(json.dumps(saved, ensure_ascii=False, sort_keys=True), before)

    def test_saved_values_are_not_rounded_defaulted_or_coerced_in_display_metadata(self):
        for raw in (0, 1e-12, .012345678901234567, None):
            with self.subTest(raw=raw):
                saved = {"window": 20, "threshold": raw}
                item = next(field for field in strategy_parameter_fields("momentum", saved) if field["key"] == "threshold")
                self.assertTrue(item["recorded"])
                self.assertEqual(item["value"], raw)
                self.assertIs(type(item["value"]), type(raw))
                self.assertEqual(saved, {"window": 20, "threshold": raw})
        # Displaying an old zero is not permission to submit it as new input.
        with self.assertRaises(ValueError):
            validate_terminal_strategy_params(self.catalog["momentum"], {"threshold": 0})

    def test_returned_metadata_does_not_alias_caller_or_future_views(self):
        params = {"threshold": {"old_unknown_value": [1, 2]}}
        display = strategy_presentation("momentum", params)
        field = next(item for item in display["parameter_fields"] if item["key"] == "threshold")
        field["value"]["old_unknown_value"].append(3)
        display["limitations"].clear()
        display["rule_notes"].clear()
        self.assertEqual(params, {"threshold": {"old_unknown_value": [1, 2]}})
        self.assertTrue(strategy_presentation("momentum", params)["limitations"])
        self.assertTrue(strategy_presentation("momentum", params)["rule_notes"])

    def test_rules_name_current_state_negative_threshold_and_actual_exit_basis(self):
        ma = strategy_presentation("dual_ma", {})
        self.assertIn("高于", ma["entry_rule"])
        self.assertIn("无需当日", "".join(ma["rule_notes"]))
        momentum = strategy_presentation("momentum", {})
        self.assertIn("负阈值", momentum["exit_rule"])
        self.assertIn("−1.5%", momentum["exit_rule"])
        self.assertIn("不小于", strategy_presentation("macd", {})["entry_rule"])
        self.assertIn("全部退出", strategy_presentation("bollinger", {})["exit_rule"])
        self.assertIn("最高收盘价", strategy_presentation("turtle", {})["entry_rule"])
        self.assertIn("99.5%", strategy_presentation("livermore", {})["exit_rule"])
        volume = strategy_presentation("volume_trend", {})
        self.assertIn("最高价", volume["entry_rule"])
        self.assertIn("最低价", volume["exit_rule"])
        self.assertNotIn("最低收盘价", volume["exit_rule"])


if __name__ == "__main__":
    unittest.main()
