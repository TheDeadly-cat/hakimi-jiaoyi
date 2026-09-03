from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
BOT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for candidate in (str(SRC_ROOT), str(BOT_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from hakimi_research.experiment_manifest import canonical_payload_hash  # noqa: E402
from hakimi_research.frozen_evaluation import (  # noqa: E402
    REPORT_SCHEMA_VERSION,
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_report,
)
from hakimi_research.frozen_statistical_correction import (  # noqa: E402
    SCHEMA_VERSION,
    FrozenStatisticalCorrectionError,
    build_frozen_statistical_correction_evidence,
    verify_frozen_statistical_correction_evidence,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


class FrozenStatisticalCorrectionV1Tests(unittest.TestCase):
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

    def test_canonical_source_and_report_versions_are_current(self) -> None:
        source = SRC_ROOT / "hakimi_research" / "frozen_statistical_correction.py"
        self.assertTrue(source.is_file())
        self.assertNotIn("outputs", source.relative_to(REPO_ROOT).parts)
        self.assertEqual(SCHEMA_VERSION, "frozen-statistical-correction-evidence-v1")
        self.assertEqual(REPORT_SCHEMA_VERSION, "frozen-evaluation-report-v22")

    def test_two_source_bound_matrices_reuse_all_stability_runs(self) -> None:
        records = self.report["statistical_correction_evidence"]
        self.assertEqual(len(records), 2)
        self.assertEqual([record["role"] for record in records], ["VALIDATION", "FROZEN_TEST"])
        self.assertEqual(len(self.report["parameter_stability_runs"]), 42)
        for record in records:
            matrix = record["trial_matrix"]
            self.assertEqual(matrix["trial_count"], 21)
            self.assertEqual(matrix["observation_count"], 9)
            self.assertEqual(
                matrix["selection_rule"],
                "PREREGISTERED_CENTER_NO_PERFORMANCE_SELECTION",
            )
            self.assertEqual(record["additional_backtest_run_count"], 0)
            self.assertNotIn("candidate_rows", matrix)

    def test_dsr_and_pbo_precondition_failures_remain_explicit_gaps(self) -> None:
        quality = self.report["quality_gate"]
        self.assertTrue(quality["statistical_correction_matrix_complete"])
        self.assertFalse(quality["statistical_correction_estimable"])
        self.assertIn("FROZEN_STATISTICAL_CORRECTIONS_UNESTIMABLE", quality["blockers"])
        for record in self.report["statistical_correction_evidence"]:
            self.assertEqual(record["evidence_state"], "GAP")
            self.assertEqual(record["deflated_sharpe"]["state"], "GAP")
            self.assertEqual(
                record["deflated_sharpe"]["gap_code"],
                "DSR_TRIAL_RETURN_VARIANCE_NON_POSITIVE",
            )
            self.assertEqual(record["cscv_pbo"]["state"], "GAP")
            self.assertEqual(
                record["cscv_pbo"]["gap_code"],
                "PBO_INSUFFICIENT_OBSERVATIONS_FOR_EIGHT_PARTITIONS",
            )
            self.assertTrue(all(value is False for value in record["authority"].values()))

    def test_every_record_recomputes_from_current_parameter_runs(self) -> None:
        for role, record in zip(
            ("VALIDATION", "FROZEN_TEST"),
            self.report["statistical_correction_evidence"],
        ):
            receipt = verify_frozen_statistical_correction_evidence(
                record,
                role=role,
                strategy_id=self.protocol["strategy"]["name"],
                stability_contract=self.protocol["parameter_stability"],
                stability_runs=self.report["parameter_stability_runs"],
                stability_summary=self.report["parameter_stability_summary"],
                periods_per_year=252,
            )
            self.assertEqual(receipt["state"], "GAP")
            self.assertEqual(receipt["trial_count"], 21)
            self.assertEqual(receipt["observation_count"], 9)
            self.assertEqual(receipt["additional_backtest_run_count"], 0)

    def test_resealed_matrix_projection_tamper_fails_report_verification(self) -> None:
        tampered = deepcopy(self.report)
        tampered["statistical_correction_evidence"][0]["trial_matrix"][
            "matrix_sha256"
        ] = "f" * 64
        evidence = tampered["statistical_correction_evidence"][0]
        evidence["evidence_sha256"] = canonical_payload_hash({
            key: value for key, value in evidence.items() if key != "evidence_sha256"
        })
        core = {
            key: value
            for key, value in tampered.items()
            if key not in {"report_id", "report_hash"}
        }
        tampered["report_hash"] = canonical_payload_hash(core)
        tampered["report_id"] = f"hfer-{tampered['report_hash'][:20]}"
        with self.assertRaisesRegex(
            ValueError,
            "frozen_evaluation_statistical_correction_invalid",
        ):
            verify_frozen_evaluation_report(
                tampered,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )

    def test_exact_native_role_boundary_rejects_subclasses(self) -> None:
        class TextAlias(str):
            pass

        with self.assertRaisesRegex(FrozenStatisticalCorrectionError, "exact supported role"):
            build_frozen_statistical_correction_evidence(
                role=TextAlias("VALIDATION"),
                strategy_id=self.protocol["strategy"]["name"],
                stability_contract=self.protocol["parameter_stability"],
                stability_runs=self.report["parameter_stability_runs"],
                stability_summary=self.report["parameter_stability_summary"],
                periods_per_year=252,
            )

    def test_markdown_is_neutral_and_retains_gap_reasons(self) -> None:
        markdown = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("Frozen statistical-correction evidence", markdown)
        self.assertIn("DSR_TRIAL_RETURN_VARIANCE_NON_POSITIVE", markdown)
        self.assertIn("PBO_INSUFFICIENT_OBSERVATIONS_FOR_EIGHT_PARTITIONS", markdown)
        self.assertNotIn("SIGNIFICANT", markdown)
        self.assertNotIn("ACCEPT STRATEGY", markdown)


if __name__ == "__main__":
    unittest.main()
