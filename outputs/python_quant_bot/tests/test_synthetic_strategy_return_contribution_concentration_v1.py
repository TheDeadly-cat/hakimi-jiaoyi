from __future__ import annotations

import copy
import math
import unittest
from collections import OrderedDict
from datetime import datetime, timezone

from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
)
from exchange_terminal.application.synthetic_strategy_return_contribution_concentration_v1 import (
    SyntheticStrategyReturnContributionConcentrationError,
    build_synthetic_strategy_return_contribution_concentration_v1,
    plan_synthetic_strategy_return_contribution_concentration_v1,
    render_synthetic_strategy_return_contribution_concentration_markdown_v1,
    replay_synthetic_strategy_return_contribution_concentration_v1,
    verify_synthetic_strategy_return_contribution_concentration_v1,
)
from exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1 import (
    build_synthetic_strategy_trial_return_matrix_v1,
)
from hakimi_research.return_contribution_concentration import (
    ReturnContributionConcentrationError,
    _closed_trade_records,
    build_return_contribution_concentration_diagnostic,
)
from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
)


class _TextAlias(str):
    pass


def _reseal(record: dict, field: str) -> None:
    record[field] = canonical_trial_return_matrix_sha256(
        {key: value for key, value in record.items() if key != field}
    )


def _compound(values: list[float]) -> float:
    return math.prod(1.0 + value for value in values) - 1.0


def _capacity_fill() -> dict[str, object]:
    return {
        "action": "SELL",
        "available_volume": 20.0,
        "fee": 0.2,
        "fill_basis": "NEXT_BAR_OPEN",
        "fill_ratio": 0.5,
        "fill_time": "2025-01-02 00:00:00+00:00",
        "filled_quantity": 2.0,
        "max_volume_participation_rate": 0.1,
        "partial_fill": True,
        "pnl": 3.0,
        "price": 100.0,
        "quantity": 2.0,
        "reason": "synthetic capacity fill",
        "requested_quantity": 4.0,
        "signal_time": "2025-01-01 00:00:00+00:00",
        "symbol": "SYNTH-001",
        "volume_capacity_quantity": 2.0,
    }


class ReturnContributionFillCompatibilityTests(unittest.TestCase):
    def test_01_legacy_and_capacity_fill_shapes_are_exactly_supported(self) -> None:
        capacity = _capacity_fill()
        records = _closed_trade_records({"fills": [capacity], "trades": 1})
        self.assertEqual(len(records), 1)
        legacy_keys = {
            "action",
            "fee",
            "fill_basis",
            "fill_time",
            "pnl",
            "price",
            "quantity",
            "reason",
            "signal_time",
            "symbol",
        }
        legacy = {key: value for key, value in capacity.items() if key in legacy_keys}
        legacy_records = _closed_trade_records({"fills": [legacy], "trades": 1})
        self.assertEqual(len(legacy_records), 1)

    def test_02_capacity_fill_cross_field_tampering_fails_closed(self) -> None:
        cases = (
            ("requested_quantity", 1.0),
            ("filled_quantity", 1.0),
            ("fill_ratio", 0.25),
            ("partial_fill", False),
            ("available_volume", -1.0),
            ("max_volume_participation_rate", 0.0),
            ("volume_capacity_quantity", 3.0),
        )
        for field, value in cases:
            with self.subTest(field=field):
                fill = _capacity_fill()
                fill[field] = value
                with self.assertRaises(ReturnContributionConcentrationError):
                    _closed_trade_records({"fills": [fill], "trades": 1})

    def test_03_capacity_fill_unknown_shape_and_alias_fail_closed(self) -> None:
        fill = _capacity_fill()
        fill["unexpected"] = 1
        with self.assertRaises(ReturnContributionConcentrationError):
            _closed_trade_records({"fills": [fill], "trades": 1})

        class DictAlias(dict):
            pass

        with self.assertRaises(ReturnContributionConcentrationError):
            _closed_trade_records(
                {"fills": [DictAlias(_capacity_fill())], "trades": 1}
            )


class SyntheticStrategyReturnContributionConcentrationV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.matrix_bundle = build_synthetic_strategy_trial_return_matrix_v1(
            cls.baseline, execute=True
        )
        cls.plan = plan_synthetic_strategy_return_contribution_concentration_v1()
        cls.bundle = build_synthetic_strategy_return_contribution_concentration_v1(
            cls.matrix_bundle, execute=True
        )
        cls.receipt = (
            verify_synthetic_strategy_return_contribution_concentration_v1(
                cls.bundle
            )
        )
        cls.markdown = (
            render_synthetic_strategy_return_contribution_concentration_markdown_v1(
                cls.bundle
            )
        )

    def test_01_plan_adds_six_analyses_and_zero_backtests(self) -> None:
        self.assertEqual(self.plan["source_required_run_count"], 147)
        self.assertEqual(self.plan["planned_run_count"], 0)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertEqual(self.plan["additional_backtest_run_count"], 0)
        self.assertEqual(self.plan["planned_analysis_count"], 6)
        self.assertEqual(self.plan["fixed_window_length"], 21)
        self.assertEqual(self.plan["expected_fixed_window_candidate_count"], 149)
        self.assertFalse(self.plan["runtime_mutations"])

    def test_02_analysis_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(
                    SyntheticStrategyReturnContributionConcentrationError
                ):
                    build_synthetic_strategy_return_contribution_concentration_v1(
                        self.matrix_bundle,
                        execute=value,  # type: ignore[arg-type]
                    )

    def test_03_bundle_and_all_six_diagnostics_verify(self) -> None:
        self.assertEqual(self.receipt["state"], "OBSERVED_WITH_GAPS")
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertEqual(self.receipt["strategy_count"], 6)
        self.assertEqual(self.receipt["executed_analysis_count"], 6)
        self.assertEqual(self.receipt["source_reused_run_count"], 147)
        self.assertEqual(self.receipt["executed_run_count"], 0)
        self.assertEqual(self.receipt["additional_backtest_run_count"], 0)
        self.assertEqual(
            self.receipt["observed_closed_trade_sensitivity_count"], 6
        )
        self.assertEqual(self.receipt["gap_closed_trade_sensitivity_count"], 0)
        self.assertEqual(self.receipt["observed_period_concentration_count"], 5)
        self.assertEqual(self.receipt["gap_period_concentration_count"], 1)

    def test_04_positive_trade_concentration_is_partial_not_fabricated(self) -> None:
        self.assertEqual(
            self.receipt[
                "observed_positive_closed_trade_concentration_count"
            ],
            4,
        )
        self.assertEqual(
            self.receipt["gap_positive_closed_trade_concentration_count"],
            2,
        )
        states = {
            record["strategy_id"]: record[
                "positive_closed_trade_concentration_state"
            ]
            for record in self.bundle["strategy_records"]
        }
        self.assertEqual(states["dual_ma"], "GAP")
        self.assertEqual(states["grid"], "GAP")
        self.assertEqual(
            {strategy for strategy, state in states.items() if state == "OBSERVED"},
            {"bollinger", "macd", "momentum", "rsi"},
        )

    def test_05_policy_locks_all_selection_and_non_inferential_rules(self) -> None:
        policy = self.plan["policy"]
        self.assertEqual(
            policy["best_observation_selection"],
            "MAX_SIMPLE_RETURN_EARLIEST_INDEX_TIE_BREAK",
        )
        self.assertEqual(policy["calendar_month_timezone"], "UTC")
        self.assertEqual(policy["fixed_window_length"], 21)
        self.assertEqual(
            policy["closed_trade_universe"], "SOURCE_RESULT_SELL_FILLS"
        )
        self.assertFalse(policy["performance_selection_performed"])
        self.assertFalse(policy["post_observation_policy_tuning"])
        self.assertFalse(policy["formal_inference_claimed"])
        self.assertIsNone(policy["decision_threshold"])

    def test_06_independent_recalculation_matches_every_diagnostic(self) -> None:
        source_records = {
            record["strategy_id"]: record
            for record in self.matrix_bundle["strategy_records"]
        }
        for output_record in self.bundle["strategy_records"]:
            strategy_id = output_record["strategy_id"]
            matrix = source_records[strategy_id]["trial_return_matrix"]
            selected = next(
                row
                for row in matrix["candidate_rows"]
                if row["trial_id"] == matrix["selected_trial_id"]
            )
            returns = [float(value) for value in selected["period_returns"]]
            times = matrix["observation_times"]
            diagnostic = output_record["return_contribution_diagnostic"]
            best_index = max(range(len(returns)), key=lambda index: returns[index])
            without_best = returns[:best_index] + returns[best_index + 1 :]
            months: OrderedDict[str, list[int]] = OrderedDict()
            for index, timestamp in enumerate(times):
                parsed = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                ).astimezone(timezone.utc)
                months.setdefault(parsed.strftime("%Y-%m"), []).append(index)
            best_month = max(
                months,
                key=lambda month: _compound(
                    [returns[index] for index in months[month]]
                ),
            )
            windows = [
                _compound(returns[start : start + 21])
                for start in range(len(returns) - 21 + 1)
            ]
            best_window_start = max(
                range(len(windows)), key=lambda index: windows[index]
            )
            sells = [
                (index, float(fill["pnl"]))
                for index, fill in enumerate(
                    selected["source_run"]["result"]["fills"]
                )
                if fill["action"] == "SELL"
            ]
            best_sell = max(sells, key=lambda item: item[1])
            with self.subTest(strategy_id=strategy_id):
                self.assertAlmostEqual(
                    float(diagnostic["selected_compounded_return"]),
                    _compound(returns),
                    places=12,
                )
                self.assertEqual(
                    diagnostic["best_observation"]["index"], best_index
                )
                self.assertAlmostEqual(
                    float(
                        diagnostic["best_observation"][
                            "full_return_without_best_observation"
                        ]
                    ),
                    _compound(without_best),
                    places=12,
                )
                self.assertEqual(
                    diagnostic["best_calendar_month"]["month_id"], best_month
                )
                self.assertEqual(
                    diagnostic["best_fixed_window"]["start_index"],
                    best_window_start,
                )
                self.assertEqual(
                    diagnostic["best_fixed_window"]["candidate_count"], 149
                )
                self.assertEqual(
                    diagnostic["best_closed_trade"]["source_fill_index"],
                    best_sell[0],
                )
                self.assertAlmostEqual(
                    float(diagnostic["best_closed_trade"]["realised_pnl"]),
                    best_sell[1],
                    places=12,
                )

    def test_07_positive_period_hhi_matches_independent_calculation(self) -> None:
        source_records = {
            record["strategy_id"]: record
            for record in self.matrix_bundle["strategy_records"]
        }
        for output_record in self.bundle["strategy_records"]:
            matrix = source_records[output_record["strategy_id"]][
                "trial_return_matrix"
            ]
            selected = next(
                row
                for row in matrix["candidate_rows"]
                if row["trial_id"] == matrix["selected_trial_id"]
            )
            positives = [
                float(value)
                for value in selected["period_returns"]
                if float(value) > 0.0
            ]
            concentration = output_record["return_contribution_diagnostic"][
                "positive_period_return_concentration"
            ]
            with self.subTest(strategy_id=output_record["strategy_id"]):
                if positives:
                    total = math.fsum(positives)
                    expected_hhi = math.fsum(
                        (value / total) ** 2 for value in positives
                    )
                    self.assertEqual(concentration["state"], "OBSERVED")
                    self.assertAlmostEqual(
                        float(concentration["herfindahl_hirschman_index"]),
                        expected_hhi,
                        places=12,
                    )
                else:
                    self.assertEqual(concentration["state"], "GAP")
                    self.assertIsNone(
                        concentration["herfindahl_hirschman_index"]
                    )
                    self.assertEqual(
                        concentration["gap_code"],
                        "NO_POSITIVE_PERIOD_RETURN_CONTRIBUTION",
                    )

    def test_08_exact_native_subclass_is_rejected(self) -> None:
        matrix = copy.deepcopy(
            self.matrix_bundle["strategy_records"][0]["trial_return_matrix"]
        )
        matrix["selected_trial_id"] = _TextAlias(matrix["selected_trial_id"])
        with self.assertRaises(ReturnContributionConcentrationError):
            build_return_contribution_concentration_diagnostic(matrix)

    def test_09_resealed_nested_diagnostic_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        record = tampered["strategy_records"][0]
        diagnostic = record["return_contribution_diagnostic"]
        diagnostic["best_observation"]["simple_return"] = "999"
        _reseal(diagnostic["best_observation"], "observation_record_sha256")
        _reseal(diagnostic, "diagnostic_sha256")
        record["return_contribution_receipt"]["diagnostic_sha256"] = diagnostic[
            "diagnostic_sha256"
        ]
        _reseal(record, "record_sha256")
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(
            SyntheticStrategyReturnContributionConcentrationError
        ):
            verify_synthetic_strategy_return_contribution_concentration_v1(
                tampered
            )

    def test_10_resealed_projection_count_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["gap_positive_closed_trade_concentration_count"] = 0
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(
            SyntheticStrategyReturnContributionConcentrationError
        ):
            verify_synthetic_strategy_return_contribution_concentration_v1(
                tampered
            )

    def test_11_authority_escalation_fails_even_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(
            SyntheticStrategyReturnContributionConcentrationError
        ):
            verify_synthetic_strategy_return_contribution_concentration_v1(
                tampered
            )

    def test_12_replay_and_renderer_remain_neutral(self) -> None:
        replay = replay_synthetic_strategy_return_contribution_concentration_v1(
            self.bundle
        )
        self.assertEqual(replay["replay_status"], "EXACT_MATCH")
        self.assertEqual(replay["replayed_analysis_count"], 6)
        self.assertEqual(replay["executed_run_count"], 0)
        self.assertEqual(replay["additional_backtest_run_count"], 0)
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("No decision threshold", self.markdown)
        self.assertIn("PARTIAL_POSITIVE_CLOSED_TRADE_CONCENTRATION_GAP", self.markdown)
        self.assertIn("PARTIAL_POSITIVE_PERIOD_RETURN_CONCENTRATION_GAP", self.markdown)
        for forbidden in ("READY", "SIGNIFICANT", "ACCEPT STRATEGY"):
            self.assertNotIn(forbidden, self.markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
