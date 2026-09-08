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

from hakimi_research.bootstrap_confidence_evidence import (  # noqa: E402
    INSUFFICIENT_OBSERVATIONS_GAP,
    MINIMUM_OBSERVATION_COUNT,
    SCHEMA_VERSION,
    verify_bootstrap_confidence_evidence,
)
from hakimi_research.experiment_manifest import canonical_payload_hash  # noqa: E402
from hakimi_research.frozen_evaluation import (  # noqa: E402
    REPORT_SCHEMA_VERSION,
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_report,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


class FrozenBootstrapConfidenceV1Tests(unittest.TestCase):
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

    def test_canonical_source_and_frozen_report_are_versioned(self) -> None:
        source = SRC_ROOT / "hakimi_research" / "bootstrap_confidence_evidence.py"
        self.assertTrue(source.is_file())
        self.assertNotIn("outputs", source.relative_to(REPO_ROOT).parts)
        self.assertEqual(
            SCHEMA_VERSION,
            "paired-moving-block-bootstrap-confidence-evidence-v1",
        )
        self.assertEqual(REPORT_SCHEMA_VERSION, "frozen-evaluation-report-v22")

    def test_two_base_buy_and_hold_records_are_source_bound_without_new_runs(self) -> None:
        records = self.report["bootstrap_confidence_evidence"]
        self.assertEqual(
            {
                (record["role"], record["scenario_id"], record["benchmark_id"])
                for record in records
            },
            {
                ("VALIDATION", "BASE", "ENGINE_BUY_AND_HOLD"),
                ("FROZEN_TEST", "BASE", "ENGINE_BUY_AND_HOLD"),
            },
        )
        self.assertEqual(len(records), 2)
        for record in records:
            self.assertEqual(
                set(record),
                {
                    "role",
                    "scenario_id",
                    "benchmark_id",
                    "strategy_result_hash",
                    "benchmark_result_hash",
                    "dataset_hash",
                    "observation_class",
                    "evidence",
                },
            )
            strategy = next(
                item
                for item in self.report["strategy_runs"]
                if item["role"] == record["role"] and item["scenario_id"] == "BASE"
            )
            benchmark = next(
                item
                for item in self.report["benchmark_runs"]
                if item["role"] == record["role"]
                and item["scenario_id"] == "BASE"
                and item["benchmark_id"] == "ENGINE_BUY_AND_HOLD"
            )
            self.assertEqual(
                record["strategy_result_hash"],
                strategy["experiment_manifest"]["result_hash"],
            )
            self.assertEqual(
                record["benchmark_result_hash"],
                benchmark["experiment_manifest"]["result_hash"],
            )
            self.assertNotIn("result", record)
            receipt = verify_bootstrap_confidence_evidence(
                record["evidence"],
                strategy["result"]["equity_curve"],
                benchmark["result"]["equity_curve"],
                dataset_sha256=record["dataset_hash"],
                strategy_result_sha256=record["strategy_result_hash"],
                benchmark_result_sha256=record["benchmark_result_hash"],
                observation_class=record["observation_class"],
            )
            self.assertEqual(receipt["state"], "GAP")

    def test_insufficient_reference_observations_remain_explicit_gap(self) -> None:
        for record in self.report["bootstrap_confidence_evidence"]:
            evidence = record["evidence"]
            self.assertEqual(evidence["evidence_state"], "GAP")
            self.assertEqual(evidence["sample_summary"]["paired_observation_count"], 9)
            self.assertEqual(evidence["policy"]["minimum_observation_count"], 60)
            self.assertEqual(MINIMUM_OBSERVATION_COUNT, 60)
            self.assertEqual(evidence["replicate_count"], 0)
            self.assertEqual(evidence["intervals"], [])
            self.assertEqual(evidence["gaps"], [INSUFFICIENT_OBSERVATIONS_GAP])
        quality = self.report["quality_gate"]
        self.assertTrue(quality["bootstrap_confidence_matrix_complete"])
        self.assertFalse(quality["bootstrap_confidence_observation_complete"])
        self.assertIn(
            "BOOTSTRAP_CONFIDENCE_INSUFFICIENT_PAIRED_OBSERVATIONS",
            quality["blockers"],
        )

    def test_outer_identity_and_source_tamper_matrix_fails_after_reseal(self) -> None:
        cases = (
            ("role", "TRAIN", "identity_invalid"),
            ("scenario_id", "DOUBLE_COST", "identity_invalid"),
            ("benchmark_id", "ENGINE_CASH", "identity_invalid"),
            ("strategy_result_hash", "0" * 64, "binding_invalid"),
            ("benchmark_result_hash", "1" * 64, "binding_invalid"),
            ("dataset_hash", "2" * 64, "binding_invalid"),
            ("observation_class", "FROZEN_EVALUATION_ALIAS", "binding_invalid"),
        )
        for field, value, error_suffix in cases:
            with self.subTest(field=field):
                tampered = deepcopy(self.report)
                tampered["bootstrap_confidence_evidence"][0][field] = value
                core = {
                    key: item
                    for key, item in tampered.items()
                    if key not in {"report_id", "report_hash"}
                }
                tampered["report_hash"] = canonical_payload_hash(core)
                tampered["report_id"] = f"hfer-{tampered['report_hash'][:20]}"
                with self.assertRaisesRegex(
                    ValueError,
                    f"frozen_evaluation_bootstrap_confidence_{error_suffix}",
                ):
                    verify_frozen_evaluation_report(
                        tampered,
                        self.protocol,
                        self.frame,
                        self.config,
                        experiment_context=context(),
                    )

    def test_authority_and_markdown_remain_neutral(self) -> None:
        self.assertTrue(
            verify_frozen_evaluation_report(
                self.report,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )
        )
        self.assertTrue(all(value is False for value in self.report["authority"].values()))
        for record in self.report["bootstrap_confidence_evidence"]:
            self.assertTrue(
                all(value is False for value in record["evidence"]["authority"].values())
            )
        markdown = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("Paired moving-block Bootstrap confidence evidence", markdown)
        self.assertIn("INSUFFICIENT_PAIRED_OBSERVATIONS", markdown)
        self.assertIn("make no formal-inference, profitability, paper, live, or order claim", markdown)


if __name__ == "__main__":
    unittest.main()
