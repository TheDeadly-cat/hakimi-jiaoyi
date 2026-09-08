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
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_report,
)
from hakimi_research.frozen_execution_adversity import (  # noqa: E402
    SCENARIO_IDS,
    UNMODELLED_GAPS,
    execution_adversity_policy_v2,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


class FrozenExecutionAdversityV1Tests(unittest.TestCase):
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

    def test_canonical_source_is_outside_outputs(self) -> None:
        source = SRC_ROOT / "hakimi_research" / "frozen_execution_adversity.py"
        self.assertTrue(source.is_file())
        self.assertNotIn("outputs", source.relative_to(REPO_ROOT).parts)

    def test_policy_preregisters_three_unselected_scenarios(self) -> None:
        policy = execution_adversity_policy_v2()
        self.assertEqual(policy["schema_version"], "frozen-execution-adversity-policy-v2")
        self.assertEqual(
            [item["scenario_id"] for item in policy["scenarios"]],
            list(SCENARIO_IDS),
        )
        self.assertTrue(
            all(item["performance_selected"] is False for item in policy["scenarios"])
        )
        self.assertEqual(policy["unmodelled_gaps"], list(UNMODELLED_GAPS))
        self.assertEqual(
            policy["liquidity_capacity_probe"]["source_benchmark_id"],
            "ENGINE_BUY_AND_HOLD",
        )
        self.assertEqual(
            policy["liquidity_capacity_probe"]["max_volume_participation_rate"],
            0.001,
        )
        self.assertFalse(
            policy["liquidity_capacity_probe"]["performance_selected"]
        )
        self.assertEqual(
            policy["liquidity_rejection_probe"]["scenario_id"],
            "minimum_executable_quantity_rejection",
        )
        self.assertNotIn("ORDER_REJECTION_NOT_MODELLED", policy["unmodelled_gaps"])
        self.assertIn(
            "PARTIAL_FILL_REMAINDER_LIFECYCLE_NOT_MODELLED",
            policy["unmodelled_gaps"],
        )
        self.assertFalse(policy["parameter_selection_allowed"])
        self.assertFalse(policy["paper_authorized"])
        self.assertFalse(policy["live_order_allowed"])

    def test_report_has_complete_role_scenario_cartesian_product(self) -> None:
        expected = [
            (role, scenario_id)
            for role in ("VALIDATION", "FROZEN_TEST")
            for scenario_id in SCENARIO_IDS
        ]
        observed = [
            (item["role"], item["scenario_id"])
            for item in self.report["execution_adversity_runs"]
        ]
        self.assertEqual(observed, expected)
        self.assertTrue(
            self.report["quality_gate"]["execution_adversity_matrix_complete"]
        )
        self.assertTrue(
            all(
                item["observation_status"] == "UNOBSERVED_SOURCE_ACTIVITY"
                for item in self.report["execution_adversity_runs"]
            )
        )
        self.assertFalse(
            self.report["quality_gate"]["execution_adversity_observation_complete"]
        )
        self.assertIn(
            "EXECUTION_ADVERSITY_TARGET_SOURCE_ACTIVITY_INSUFFICIENT",
            self.report["quality_gate"]["blockers"],
        )

    def test_fixed_liquidity_probe_observes_volume_capped_partial_fill(self) -> None:
        records = self.report["liquidity_capacity_runs"]
        self.assertEqual(
            [(item["role"], item["scenario_id"]) for item in records],
            [
                ("VALIDATION", "volume_participation_cap_0_1pct"),
                ("FROZEN_TEST", "volume_participation_cap_0_1pct"),
            ],
        )
        self.assertTrue(
            self.report["quality_gate"]["liquidity_capacity_matrix_complete"]
        )
        self.assertTrue(
            self.report["quality_gate"]["liquidity_capacity_partial_fill_observed"]
        )
        for record in records:
            summary = record["liquidity_capacity_summary"]
            self.assertEqual(record["source_benchmark_id"], "ENGINE_BUY_AND_HOLD")
            self.assertEqual(record["run_kind"], "REGISTERED_LIQUIDITY_CAPACITY_PROBE")
            self.assertEqual(
                record["source_input_dataset_hash"],
                record["stressed_input_dataset_hash"],
            )
            self.assertEqual(summary["status"], "OBSERVED")
            self.assertGreater(summary["partial_fill_count"], 0)
            self.assertFalse(summary["remainder_lifecycle_modelled"])
            self.assertFalse(summary["shared_bar_volume_budget_modelled"])
            for fill in record["result"]["fills"]:
                self.assertLessEqual(
                    fill["filled_quantity"],
                    fill["volume_capacity_quantity"] + 1e-12,
                )
                self.assertEqual(fill["max_volume_participation_rate"], 0.001)
                self.assertTrue(fill["partial_fill"])
            self.assertFalse(record["experiment_manifest"]["paper_authorized"])
            self.assertFalse(record["experiment_manifest"]["live_order_allowed"])
            self.assertFalse(record["experiment_manifest"]["order_entry_allowed"])

    def test_source_bound_liquidity_rejection_is_observed_without_submission(self) -> None:
        records = self.report["liquidity_rejection_evidence"]
        self.assertEqual([item["role"] for item in records], ["VALIDATION", "FROZEN_TEST"])
        self.assertTrue(
            self.report["quality_gate"]["liquidity_rejection_probe_matrix_complete"]
        )
        self.assertTrue(self.report["quality_gate"]["liquidity_rejection_observed"])
        for record in records:
            self.assertEqual(record["decision"]["status"], "REJECTED")
            self.assertEqual(
                record["decision"]["reason"],
                "MINIMUM_EXECUTABLE_QUANTITY_NOT_MET",
            )
            self.assertLess(
                record["decision"]["executable_quantity"],
                record["decision"]["minimum_executable_quantity"],
            )
            self.assertFalse(record["portfolio_mutated"])
            self.assertTrue(all(value is False for value in record["authority"].values()))

    def test_delay_and_drop_reuse_source_dataset(self) -> None:
        for record in self.report["execution_adversity_runs"]:
            if record["scenario_id"] == "source_fill_adverse_open_2pct":
                continue
            self.assertEqual(
                record["source_input_dataset_hash"],
                record["stressed_input_dataset_hash"],
            )

    def test_delay_drop_and_adverse_open_metadata_are_semantic(self) -> None:
        for record in self.report["execution_adversity_runs"]:
            metadata = record["scenario_metadata"]
            if record["scenario_id"] == "one_bar_signal_release_delay":
                self.assertEqual(metadata["unreleased_terminal_signal_count"], 1)
                self.assertEqual(
                    metadata["generated_signal_count"],
                    metadata["released_signal_count"] + 1,
                )
            elif record["scenario_id"] == "drop_every_third_actionable_signal":
                self.assertEqual(
                    metadata["dropped_signal_count"],
                    metadata["actionable_signal_count"] // 3,
                )
            else:
                self.assertEqual(
                    metadata["adverse_open_event_count"],
                    len(metadata["adverse_open_events"]),
                )
                for event in metadata["adverse_open_events"]:
                    expected = 1.02 if event["source_action"] == "BUY" else 0.98
                    self.assertAlmostEqual(
                        event["stressed_open"] / event["source_open"],
                        expected,
                        places=14,
                    )

    def test_result_deltas_recompute_from_bound_base_run(self) -> None:
        source = {
            item["role"]: item
            for item in self.report["strategy_runs"]
            if item["scenario_id"] == "BASE"
        }
        for record in self.report["execution_adversity_runs"]:
            delta = record["source_result_delta"]
            self.assertAlmostEqual(
                delta["total_return_delta"],
                record["result"]["total_return"]
                - source[record["role"]]["result"]["total_return"],
                places=14,
            )

    def test_resealed_delta_tamper_fails_semantic_verification(self) -> None:
        tampered = deepcopy(self.report)
        delta = tampered["execution_adversity_runs"][0]["source_result_delta"]
        delta["trade_count_delta"] = 999
        delta_core = {
            key: value for key, value in delta.items() if key != "delta_hash"
        }
        delta["delta_hash"] = canonical_payload_hash(delta_core)
        report_core = {
            key: value
            for key, value in tampered.items()
            if key not in {"report_id", "report_hash"}
        }
        tampered["report_hash"] = canonical_payload_hash(report_core)
        tampered["report_id"] = f"hfer-{tampered['report_hash'][:20]}"
        with self.assertRaisesRegex(ValueError, "execution_adversity"):
            verify_frozen_evaluation_report(
                tampered,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )

    def test_resealed_liquidity_summary_tamper_fails_semantic_verification(self) -> None:
        tampered = deepcopy(self.report)
        summary = tampered["liquidity_capacity_runs"][0][
            "liquidity_capacity_summary"
        ]
        summary["partial_fill_count"] = 0
        summary_core = {
            key: value for key, value in summary.items() if key != "summary_hash"
        }
        summary["summary_hash"] = canonical_payload_hash(summary_core)
        report_core = {
            key: value
            for key, value in tampered.items()
            if key not in {"report_id", "report_hash"}
        }
        tampered["report_hash"] = canonical_payload_hash(report_core)
        tampered["report_id"] = f"hfer-{tampered['report_hash'][:20]}"
        with self.assertRaisesRegex(ValueError, "liquidity"):
            verify_frozen_evaluation_report(
                tampered,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )

    def test_resealed_liquidity_rejection_tamper_fails_semantic_verification(self) -> None:
        tampered = deepcopy(self.report)
        evidence = tampered["liquidity_rejection_evidence"][0]
        evidence["decision"]["status"] = "ACCEPTED"
        evidence_core = {
            key: value for key, value in evidence.items() if key != "evidence_hash"
        }
        evidence["evidence_hash"] = canonical_payload_hash(evidence_core)
        report_core = {
            key: value
            for key, value in tampered.items()
            if key not in {"report_id", "report_hash"}
        }
        tampered["report_hash"] = canonical_payload_hash(report_core)
        tampered["report_id"] = f"hfer-{tampered['report_hash'][:20]}"
        with self.assertRaisesRegex(ValueError, "liquidity_rejection"):
            verify_frozen_evaluation_report(
                tampered,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )

    def test_markdown_is_neutral_and_names_unmodelled_execution_gaps(self) -> None:
        rendered = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("Registered execution-adversity observations", rendered)
        self.assertIn("Fixed liquidity-capacity execution probe", rendered)
        self.assertIn("Fixed liquidity-rejection admission probe", rendered)
        self.assertIn("MINIMUM_EXECUTABLE_QUANTITY_NOT_MET", rendered)
        self.assertIn("not target-strategy robustness evidence", rendered)
        self.assertIn("UNOBSERVED_SOURCE_ACTIVITY", rendered)
        self.assertNotIn("READY", rendered)
        self.assertFalse(self.report["authority"]["paper"])
        self.assertFalse(self.report["authority"]["live"])
        self.assertFalse(self.report["authority"]["order"])


if __name__ == "__main__":
    unittest.main()
