from __future__ import annotations

from copy import deepcopy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research.experiment_manifest import canonical_payload_hash  # noqa: E402
from hakimi_research.frozen_evaluation import (  # noqa: E402
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_report,
)
from hakimi_research.volatility_target_baseline import (  # noqa: E402
    VOLATILITY_TARGET_AUTHORITY_LOCK,
    VOLATILITY_TARGET_BASELINE_ID,
    build_prior_window_volatility_target_calibration,
    build_prior_window_volatility_target_strategy,
    verify_prior_window_volatility_target_calibration,
    volatility_target_method_spec,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


class PriorWindowVolatilityTargetBaselineV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = synthetic_frame()
        cls.config = config()
        cls.protocol = protocol(cls.frame, cls.config)
        cls.report = build_frozen_evaluation_report(
            cls.protocol,
            cls.frame,
            cls.config,
            experiment_context=context(),
        )

    def test_protocol_preregisters_strict_prior_window_method(self) -> None:
        self.assertEqual(len(self.protocol["execution_baseline_methods"]), 1)
        method = self.protocol["execution_baseline_methods"][0]
        self.assertEqual(method["benchmark_id"], VOLATILITY_TARGET_BASELINE_ID)
        self.assertEqual(
            method["calibration_map"],
            [
                {"target_role": "VALIDATION", "calibration_role": "TRAIN"},
                {"target_role": "FROZEN_TEST", "calibration_role": "VALIDATION"},
            ],
        )
        self.assertEqual(method["exposure_cap"], 1.0)
        self.assertFalse(method["leverage_allowed"])
        self.assertFalse(method["paper_authorized"])
        self.assertFalse(method["live_authorized"])
        self.assertFalse(method["order_authorized"])
        core = {key: value for key, value in method.items() if key != "spec_hash"}
        self.assertEqual(method["spec_hash"], canonical_payload_hash(core))

    def test_report_has_complete_role_cost_execution_matrix(self) -> None:
        expected = {
            (role, scenario_id)
            for role in ("VALIDATION", "FROZEN_TEST")
            for scenario_id in ("BASE", "DOUBLE_COST", "TRIPLE_COST")
        }
        runs = self.report["volatility_target_benchmark_runs"]
        self.assertEqual(
            {(item["role"], item["scenario_id"]) for item in runs},
            expected,
        )
        self.assertEqual(len(runs), 6)
        self.assertTrue(
            self.report["quality_gate"]["volatility_target_execution_baseline_complete"]
        )
        for record in runs:
            calibration = record["calibration"]
            self.assertEqual(calibration["calibration_status"], "CALIBRATED")
            self.assertGreaterEqual(calibration["applied_exposure"], 0.0)
            self.assertLessEqual(calibration["applied_exposure"], 1.0)
            self.assertEqual(calibration["authority"], VOLATILITY_TARGET_AUTHORITY_LOCK)
            self.assertFalse(calibration["authority"]["paper"])
            self.assertFalse(calibration["authority"]["live"])
            self.assertFalse(calibration["authority"]["order"])

    def test_calibration_windows_precede_targets_and_rebuild(self) -> None:
        windows = {
            item["name"]: item
            for item in self.protocol["partition_plan"]["windows"]
        }
        method = self.protocol["execution_baseline_methods"][0]
        for mapping in method["calibration_map"]:
            target_role = mapping["target_role"]
            calibration_role = mapping["calibration_role"]
            self.assertLessEqual(
                windows[calibration_role]["end_position_exclusive"],
                windows[target_role]["start_position"],
            )
            strategy_record = next(
                item
                for item in self.report["strategy_runs"]
                if item["role"] == calibration_role and item["scenario_id"] == "BASE"
            )
            calibration_frame = self.frame.iloc[
                windows[calibration_role]["start_position"]:
                windows[calibration_role]["end_position_exclusive"]
            ].copy()
            expected = build_prior_window_volatility_target_calibration(
                strategy_record,
                calibration_frame,
                target_role=target_role,
                calibration_role=calibration_role,
                initial_equity=self.protocol["config"]["initial_cash"],
                market=self.protocol["config"]["market"],
                timeframe=self.protocol["config"]["timeframe"],
                warmup_rows=method["warmup_rows"],
                exposure_cap=method["exposure_cap"],
            )
            records = [
                item
                for item in self.report["volatility_target_benchmark_runs"]
                if item["role"] == target_role
            ]
            self.assertEqual(len(records), 3)
            for record in records:
                self.assertEqual(record["calibration"], expected)
                self.assertTrue(
                    verify_prior_window_volatility_target_calibration(
                        record["calibration"],
                        strategy_record,
                        calibration_frame,
                        target_role=target_role,
                        calibration_role=calibration_role,
                        initial_equity=self.protocol["config"]["initial_cash"],
                        market=self.protocol["config"]["market"],
                        timeframe=self.protocol["config"]["timeframe"],
                        warmup_rows=method["warmup_rows"],
                        exposure_cap=method["exposure_cap"],
                    )
                )

    def test_strategy_identity_is_calibration_bound_and_deterministic(self) -> None:
        calibration = self.report["volatility_target_benchmark_runs"][0]["calibration"]
        first = build_prior_window_volatility_target_strategy(calibration)
        second = build_prior_window_volatility_target_strategy(deepcopy(calibration))
        self.assertEqual(first.name, second.name)
        self.assertEqual(first.version, second.version)
        self.assertEqual(first.params, second.params)
        self.assertEqual(first.params["calibration_hash"], calibration["calibration_hash"])

    def test_calibration_and_run_tampering_fail_closed(self) -> None:
        for field, value in (
            ("applied_exposure", 2.0),
            ("calibration_role", "FROZEN_TEST"),
            ("calibration_hash", "0" * 64),
            ("authority", {"paper": True}),
        ):
            tampered = deepcopy(self.report)
            tampered["volatility_target_benchmark_runs"][0]["calibration"][field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    verify_frozen_evaluation_report(
                        tampered,
                        self.protocol,
                        self.frame,
                        self.config,
                        experiment_context=context(),
                    )
        missing = deepcopy(self.report)
        missing["volatility_target_benchmark_runs"].pop()
        with self.assertRaises(ValueError):
            verify_frozen_evaluation_report(
                missing,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )

    def test_method_spec_is_fresh_and_non_authorizing(self) -> None:
        first = volatility_target_method_spec()
        second = volatility_target_method_spec()
        first["calibration_map"].append(
            {"target_role": "FORGED", "calibration_role": "FROZEN_TEST"}
        )
        self.assertEqual(len(second["calibration_map"]), 2)
        self.assertTrue(second["research_simulator_executable"])
        self.assertFalse(second["paper_authorized"])
        self.assertFalse(second["live_authorized"])
        self.assertFalse(second["order_authorized"])

    def test_markdown_is_neutral_and_declares_execution_scope(self) -> None:
        rendered = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("Prior-window volatility-target research-simulator benchmark", rendered)
        self.assertIn("execution scope: `RESEARCH_SIMULATOR_ONLY`", rendered)
        self.assertIn("paper/live/order authorization: `false`", rendered)
        self.assertNotIn("VOLATILITY_MATCHED_EXECUTION_BASELINE_NOT_AVAILABLE", rendered)
        self.assertNotIn("READY", rendered)

    def test_source_envelope_includes_execution_baseline(self) -> None:
        source = (
            SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/volatility_target_baseline.py"', source)


if __name__ == "__main__":
    unittest.main()
