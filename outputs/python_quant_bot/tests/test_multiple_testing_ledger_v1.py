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
from hakimi_research.frozen_experiment_provenance import (  # noqa: E402
    verified_multiple_testing_receipt_hashes,
)
from hakimi_research.frozen_evaluation import (  # noqa: E402
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_report,
)
from hakimi_research.multiple_testing import (  # noqa: E402
    MULTIPLE_TESTING_AUTHORITY_LOCK,
    build_multiple_testing_ledger,
    multiple_testing_policy_spec,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


class MultipleTestingLedgerV1Tests(unittest.TestCase):
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

    def test_policy_is_preregistered_and_non_selecting(self) -> None:
        policy = self.protocol["multiple_testing_policy"]
        self.assertEqual(policy["expected_trial_count"], 21)
        self.assertEqual(policy["expected_observation_count"], 42)
        self.assertTrue(policy["all_observations_must_be_retained"])
        self.assertIsNone(policy["selected_trial_id"])
        self.assertFalse(policy["parameter_selection_allowed"])
        self.assertFalse(policy["ranking_allowed"])
        core = {key: value for key, value in policy.items() if key != "spec_hash"}
        self.assertEqual(policy["spec_hash"], canonical_payload_hash(core))

    def test_ledger_binds_every_trial_and_observation(self) -> None:
        ledger = self.report["multiple_testing_ledger"]
        self.assertEqual(ledger["family"]["trial_count"], 21)
        self.assertEqual(ledger["observation_count"], 42)
        self.assertEqual(ledger["validation_observation_count"], 21)
        self.assertEqual(ledger["synthetic_frozen_observation_count"], 21)
        self.assertEqual(len(ledger["observations"]), 42)
        self.assertEqual(
            len({(item["role"], item["cell_id"]) for item in ledger["observations"]}),
            42,
        )
        self.assertTrue(ledger["all_observed_results_retained"])
        self.assertIsNone(ledger["formal_frozen_consumption_count"])
        self.assertFalse(ledger["single_consumption_proven"])
        self.assertFalse(ledger["external_preregistration_receipt_present"])
        self.assertEqual(ledger["authority"], MULTIPLE_TESTING_AUTHORITY_LOCK)

    def test_corrections_are_blocked_not_fabricated(self) -> None:
        ledger = self.report["multiple_testing_ledger"]
        self.assertEqual(
            [item["correction_id"] for item in ledger["corrections"]],
            [
                "DEFLATED_SHARPE_RATIO",
                "PROBABILITY_OF_BACKTEST_OVERFITTING",
                "BLOCK_BOOTSTRAP_CONFIDENCE_INTERVAL",
            ],
        )
        for correction in ledger["corrections"]:
            self.assertIn(correction["status"], {"NOT_ESTIMABLE", "NOT_COMPUTED"})
            self.assertIsNone(correction["value"])
            self.assertTrue(correction["blockers"])
        self.assertIsNone(ledger["selected_trial_id"])
        self.assertFalse(ledger["parameter_selection_performed"])
        self.assertFalse(ledger["ranking_performed"])

    def test_ledger_rebuilds_exactly(self) -> None:
        all_run_records = [
            *self.report["strategy_runs"],
            *self.report["execution_adversity_runs"],
            *self.report["liquidity_capacity_runs"],
            *self.report["benchmark_runs"],
            *self.report["volatility_target_benchmark_runs"],
            *self.report["walk_forward_runs"],
            *self.report["parameter_stability_runs"],
        ]
        provenance_receipts = verified_multiple_testing_receipt_hashes(
            self.report["experiment_provenance"],
            all_run_records,
            expected_context=self.protocol["experiment_context"]["context"],
            protocol_hash=self.protocol["protocol_hash"],
            symbol=self.protocol["config"]["symbol"],
            timeframe=self.protocol["config"]["timeframe"],
        )
        expected = build_multiple_testing_ledger(
            self.protocol["parameter_stability"],
            self.report["parameter_stability_runs"],
            self.report["parameter_stability_summary"],
            self.protocol["walk_forward"],
            self.report["walk_forward_summary"],
            observation_provenance_receipts=provenance_receipts,
        )
        self.assertEqual(self.report["multiple_testing_ledger"], expected)
        self.assertTrue(self.report["quality_gate"]["multiple_testing_lineage_complete"])

    def test_policy_lineage_and_correction_tampering_fail_closed(self) -> None:
        tampered_protocol = deepcopy(self.protocol)
        tampered_protocol["multiple_testing_policy"]["ranking_allowed"] = True
        with self.assertRaises(ValueError):
            verify_frozen_evaluation_report(
                self.report,
                tampered_protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )
        for mutate in (
            lambda x: x["observations"].pop(),
            lambda x: x["observations"][0].__setitem__("run_hash", "0" * 64),
            lambda x: x["corrections"][0].__setitem__("value", 1.0),
            lambda x: x.__setitem__("selected_trial_id", "FORGED"),
            lambda x: x.__setitem__("ledger_hash", "0" * 64),
        ):
            tampered = deepcopy(self.report)
            mutate(tampered["multiple_testing_ledger"])
            with self.assertRaises(ValueError):
                verify_frozen_evaluation_report(
                    tampered,
                    self.protocol,
                    self.frame,
                    self.config,
                    experiment_context=context(),
                )

    def test_policy_spec_is_fresh(self) -> None:
        first = multiple_testing_policy_spec()
        second = multiple_testing_policy_spec()
        first["required_corrections"].append("FORGED")
        self.assertEqual(len(second["required_corrections"]), 3)

    def test_markdown_is_neutral_and_exposes_correction_blockers(self) -> None:
        rendered = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("Multiple-testing lineage ledger", rendered)
        self.assertIn("RECORDED_WITH_UNESTIMABLE_CORRECTIONS", rendered)
        self.assertIn("DEFLATED_SHARPE_RATIO", rendered)
        self.assertIn("PROBABILITY_OF_BACKTEST_OVERFITTING", rendered)
        self.assertIn("Formal Frozen consumption count: `UNKNOWN`", rendered)
        self.assertIn(
            "MULTIPLE_TESTING_CORRECTIONS_NOT_ESTIMABLE_TWO_SYNTHETIC_FOLDS",
            rendered,
        )
        self.assertNotIn("MULTIPLE_TESTING_LINEAGE_NOT_BOUND_TO_ADR0509", rendered)
        self.assertNotIn("READY", rendered)

    def test_source_envelope_includes_ledger_producer(self) -> None:
        source = (
            SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/multiple_testing.py"', source)


if __name__ == "__main__":
    unittest.main()
