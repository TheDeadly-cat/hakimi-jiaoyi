from __future__ import annotations

import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import unittest

from exchange_terminal.application.synthetic_strategy_input_pathology_v1 import (
    SyntheticStrategyInputPathologyError,
    build_synthetic_strategy_input_pathology_v1,
    plan_synthetic_strategy_input_pathology_v1,
    render_synthetic_strategy_input_pathology_markdown_v1,
    replay_synthetic_strategy_input_pathology_v1,
    verify_synthetic_strategy_input_pathology_v1,
)
from hakimi_research.synthetic_input_pathology_gate import (
    SyntheticInputPathologyGateError,
    evaluate_synthetic_input_pathology_gate_v1,
)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _reseal(payload: dict[str, object], field: str) -> None:
    unsigned = {key: value for key, value in payload.items() if key != field}
    payload[field] = _sha256_json(unsigned)


class SyntheticStrategyInputPathologyV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.test_synthetic_strategy_benchmark_report_entrypoint_v11 import (
            SyntheticStrategyBenchmarkReportEntrypointV11Test,
        )

        source_class = SyntheticStrategyBenchmarkReportEntrypointV11Test
        if not hasattr(source_class, "report"):
            source_class.setUpClass()
        cls.source = source_class.report
        cls.bundle = build_synthetic_strategy_input_pathology_v1(
            cls.source, execute=True
        )
        cls.receipt = verify_synthetic_strategy_input_pathology_v1(
            cls.bundle, cls.source
        )
        cls.scenarios = {
            scenario["scenario_id"]: scenario
            for scenario in cls.bundle["scenarios"]
        }

    def test_01_plan_is_four_evaluations_six_probes_and_zero_runs(self) -> None:
        plan = plan_synthetic_strategy_input_pathology_v1()
        self.assertEqual(plan["pathology_evaluation_count"], 4)
        self.assertEqual(plan["capacity_probe_count"], 6)
        self.assertEqual(plan["additional_backtest_run_count"], 0)
        self.assertEqual(plan["source_logical_run_count"], 222)
        self.assertEqual(plan["total_logical_run_count"], 222)
        self.assertEqual(plan["source_module_file_count"], 57)

    def test_02_execute_flag_and_prebuilt_source_are_fail_closed(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    build_synthetic_strategy_input_pathology_v1(  # type: ignore[arg-type]
                        execute=value
                    )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_input_pathology_v1(execute=True)

    def test_03_source_frozen_control_passes_without_capacity_probe(self) -> None:
        evaluation = self.scenarios["source_frozen_control"]["evaluation"]
        self.assertTrue(evaluation["accepted"])
        self.assertEqual(evaluation["issue_codes"], [])
        self.assertEqual(evaluation["record_count"], 200)
        self.assertEqual(evaluation["capacity_probe_count"], 0)

    def test_04_missing_internal_bar_fails_closed(self) -> None:
        evaluation = self.scenarios["missing_internal_bar"]["evaluation"]
        self.assertFalse(evaluation["accepted"])
        self.assertEqual(evaluation["issue_codes"], ["MISSING_INTERVAL"])
        self.assertEqual(evaluation["missing_interval_count"], 1)
        self.assertEqual(evaluation["record_count"], 199)

    def test_05_ohlc_envelope_breach_fails_closed(self) -> None:
        evaluation = self.scenarios["ohlc_envelope_breach"]["evaluation"]
        self.assertFalse(evaluation["accepted"])
        self.assertEqual(
            evaluation["issue_codes"], ["OHLC_ENVELOPE_VIOLATION"]
        )
        self.assertEqual(evaluation["ohlc_violation_count"], 1)

    def test_06_capacity_probe_blocks_all_six_without_creating_fills(self) -> None:
        evaluation = self.scenarios[
            "insufficient_static_volume_capacity"
        ]["evaluation"]
        self.assertTrue(evaluation["data_accepted"])
        self.assertFalse(evaluation["capacity_accepted"])
        self.assertEqual(evaluation["capacity_probe_count"], 6)
        self.assertEqual(evaluation["insufficient_capacity_probe_count"], 6)
        for assessment in evaluation["capacity_assessments"]:
            self.assertAlmostEqual(float(assessment["capacity_ratio"]), 0.5)
            self.assertLess(
                Decimal(assessment["available_quantity_upper_bound"]),
                Decimal(assessment["requested_quantity"]),
            )
            self.assertFalse(assessment["partial_fill_created"])
            self.assertFalse(assessment["order_rejection_created"])

    def test_07_source_bindings_and_run_accounting_are_exact(self) -> None:
        self.assertEqual(
            self.bundle["source_report_v11_sha256"], self.source["report_sha256"]
        )
        self.assertEqual(self.bundle["additional_backtest_run_count"], 0)
        self.assertEqual(self.bundle["total_logical_run_count"], 222)
        self.assertEqual(self.receipt["pathology_evaluation_count"], 4)
        self.assertFalse(any(self.receipt["authority"].values()))

    def test_08_replay_is_exact(self) -> None:
        replay = replay_synthetic_strategy_input_pathology_v1(
            self.bundle, self.source
        )
        self.assertEqual(replay["replay_status"], "EXACT_MATCH")
        self.assertEqual(replay["bundle_sha256"], self.bundle["bundle_sha256"])

    def test_09_source_extension_manifest_hashes_three_files(self) -> None:
        root = Path(__file__).resolve().parents[3]
        manifest = self.bundle["source_extension_manifest"]
        self.assertEqual(manifest["file_count"], 3)
        for record in manifest["files"]:
            payload = (root / record["path"]).read_bytes()
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())

    def test_10_resealed_evaluation_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        scenario = tampered["scenarios"][1]
        scenario["evaluation"]["missing_interval_count"] = 99
        _reseal(scenario["evaluation"], "evaluation_sha256")
        _reseal(scenario, "scenario_sha256")
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyInputPathologyError):
            verify_synthetic_strategy_input_pathology_v1(tampered, self.source)

    def test_11_exact_native_aliases_and_authority_fail_closed(self) -> None:
        class ListAlias(list):
            pass

        control = self.scenarios["source_frozen_control"]["evaluation"]
        with self.assertRaises(SyntheticInputPathologyGateError):
            evaluate_synthetic_input_pathology_gate_v1(
                ListAlias([]), self.bundle["plan"]["policy"], []
            )
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyInputPathologyError):
            verify_synthetic_strategy_input_pathology_v1(tampered, self.source)
        self.assertTrue(control["accepted"])

    def test_12_renderer_is_non_current_neutral_and_ordered(self) -> None:
        markdown = render_synthetic_strategy_input_pathology_markdown_v1(
            self.bundle, self.source
        )
        self.assertIn("NON-CURRENT RESEARCH-ONLY CANDIDATE", markdown)
        self.assertLess(markdown.index("## SOURCE"), markdown.index("## GAP"))
        self.assertLess(markdown.index("## GAP"), markdown.index("## MATURITY"))
        self.assertLess(
            markdown.index("## MATURITY"), markdown.index("## PERMISSION")
        )
        self.assertIn("Profitability proven: FALSE", markdown)
        self.assertNotIn("Profitability proven: TRUE", markdown)


if __name__ == "__main__":
    unittest.main()
