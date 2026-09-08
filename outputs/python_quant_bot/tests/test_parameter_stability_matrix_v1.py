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
from hakimi_research.parameter_stability import (  # noqa: E402
    PARAMETER_STABILITY_AUTHORITY_LOCK,
    build_dual_ma_parameter_stability_cells,
    build_parameter_stability_summary,
    fixed_parameter_stability_method_spec,
    verify_dual_ma_parameter_stability_cells,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


class ParameterStabilityMatrixV1Tests(unittest.TestCase):
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

    def test_protocol_binds_unique_complete_matrix(self) -> None:
        contract = self.protocol["parameter_stability"]
        cells = contract["cells"]
        self.assertTrue(
            verify_dual_ma_parameter_stability_cells(
                cells,
                self.config.strategy.params,
            )
        )
        self.assertEqual(len(cells), 21)
        self.assertEqual(len({item["cell_id"] for item in cells}), 21)
        self.assertEqual(len({item["params_hash"] for item in cells}), 21)
        self.assertEqual(sum(item["is_center"] for item in cells), 1)
        self.assertEqual(sum(item["segment"] == "TIMING_GRID" for item in cells), 15)
        self.assertEqual(sum(item["segment"] == "RISK_OAT" for item in cells), 6)
        method = contract["method"]
        core = {key: value for key, value in method.items() if key != "spec_hash"}
        self.assertEqual(method["spec_hash"], canonical_payload_hash(core))

    def test_report_retains_all_role_cells_without_ranking(self) -> None:
        expected = {
            (role, cell["cell_id"])
            for role in ("VALIDATION", "FROZEN_TEST")
            for cell in self.protocol["parameter_stability"]["cells"]
        }
        runs = self.report["parameter_stability_runs"]
        self.assertEqual({(item["role"], item["cell_id"]) for item in runs}, expected)
        self.assertEqual(len(runs), 42)
        self.assertTrue(self.report["quality_gate"]["parameter_stability_matrix_complete"])
        for record in runs:
            manifest = record["experiment_manifest"]
            self.assertEqual(manifest["evaluation_role"], "UNCLASSIFIED")
            self.assertFalse(manifest["ranking_gate"]["input_allowed"])
            self.assertFalse(manifest["parameter_selection_allowed"])
            self.assertFalse(manifest["paper_authorized"])
            self.assertFalse(manifest["live_order_allowed"])
            self.assertFalse(manifest["order_entry_allowed"])

    def test_summary_is_descriptive_and_selects_nothing(self) -> None:
        summary = self.report["parameter_stability_summary"]
        expected = build_parameter_stability_summary(
            self.report["parameter_stability_runs"],
            self.protocol["parameter_stability"]["cells"],
        )
        self.assertEqual(summary, expected)
        self.assertEqual(summary["cell_count"], 21)
        self.assertTrue(summary["all_cells_retained"])
        self.assertIsNone(summary["selected_cell_id"])
        self.assertFalse(summary["parameter_selection_performed"])
        self.assertFalse(summary["ranking_performed"])
        self.assertEqual(summary["authority"], PARAMETER_STABILITY_AUTHORITY_LOCK)
        self.assertTrue(
            all(item["observed_cell_count"] == 21 for item in summary["role_summaries"])
        )

    def test_cell_method_run_and_summary_tampering_fail_closed(self) -> None:
        for mutate in (
            lambda x: x["parameter_stability"]["cells"].pop(),
            lambda x: x["parameter_stability"]["cells"][0].__setitem__("cell_hash", "0" * 64),
            lambda x: x["parameter_stability"]["method"].__setitem__("ranking_allowed", True),
        ):
            tampered_protocol = deepcopy(self.protocol)
            mutate(tampered_protocol)
            with self.assertRaises(ValueError):
                verify_frozen_evaluation_report(
                    self.report,
                    tampered_protocol,
                    self.frame,
                    self.config,
                    experiment_context=context(),
                )
        for field, value in (
            ("cell_id", "FORGED"),
            ("params_hash", "0" * 64),
            ("params", {}),
            ("result", []),
            ("experiment_manifest", []),
        ):
            tampered = deepcopy(self.report)
            tampered["parameter_stability_runs"][0][field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    verify_frozen_evaluation_report(
                        tampered,
                        self.protocol,
                        self.frame,
                        self.config,
                        experiment_context=context(),
                    )
        summary = deepcopy(self.report)
        summary["parameter_stability_summary"]["selected_cell_id"] = "FORGED"
        with self.assertRaises(ValueError):
            verify_frozen_evaluation_report(summary, self.protocol, self.frame, self.config, experiment_context=context())

    def test_method_and_cells_are_fresh_and_exact(self) -> None:
        first = fixed_parameter_stability_method_spec()
        second = fixed_parameter_stability_method_spec()
        first["roles"].append("TRAIN")
        self.assertEqual(second["roles"], ["VALIDATION", "FROZEN_TEST"])
        left = build_dual_ma_parameter_stability_cells(self.config.strategy.params)
        right = build_dual_ma_parameter_stability_cells(self.config.strategy.params)
        left[0]["params"]["fast_window"] = 99
        self.assertNotEqual(left, right)
        for invalid in (
            {},
            {**self.config.strategy.params, "extra": 1},
            {**self.config.strategy.params, "fast_window": True},
            {**self.config.strategy.params, "position_pct": 2.0},
        ):
            with self.assertRaises(ValueError):
                build_dual_ma_parameter_stability_cells(invalid)

    def test_markdown_contains_heatmaps_without_selection_language(self) -> None:
        rendered = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("Parameter-stability observations", rendered)
        self.assertIn("VALIDATION timing-grid total return", rendered)
        self.assertIn("FROZEN_TEST timing-grid total return", rendered)
        self.assertIn("all cells retained: `true`", rendered)
        self.assertIn("selected cell: `null`", rendered)
        self.assertIn("PARAMETER_STABILITY_ONLY_DUAL_MA_SYNTHETIC_GRID", rendered)
        self.assertNotIn("PARAMETER_STABILITY_NOT_BOUND_TO_ADR0509", rendered)
        self.assertNotIn("READY", rendered)

    def test_source_envelope_includes_stability_producer(self) -> None:
        source = (
            SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/parameter_stability.py"', source)


if __name__ == "__main__":
    unittest.main()
