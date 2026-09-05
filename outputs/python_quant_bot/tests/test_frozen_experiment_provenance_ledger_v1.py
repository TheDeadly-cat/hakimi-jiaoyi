from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from _canonical_source import activate_canonical_source


activate_canonical_source()

from hakimi_research.experiment_manifest import canonical_payload_hash  # noqa: E402
from hakimi_research.frozen_evaluation import (  # noqa: E402
    build_frozen_evaluation_report,
    verify_frozen_evaluation_report,
)
from hakimi_research.frozen_experiment_provenance import (  # noqa: E402
    FROZEN_EXPERIMENT_PROVENANCE_LEDGER_VERSION,
    FROZEN_EXPERIMENT_PROVENANCE_TRUST_MODEL,
    verified_multiple_testing_receipt_hashes,
    verify_frozen_experiment_provenance_ledger,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _run_records(report: dict) -> list[dict]:
    return [
        *report["strategy_runs"],
        *report["execution_adversity_runs"],
        *report["liquidity_capacity_runs"],
        *report["benchmark_runs"],
        *report["volatility_target_benchmark_runs"],
        *report["walk_forward_runs"],
        *report["parameter_stability_runs"],
    ]


def _reseal_report(report: dict) -> None:
    core = {
        key: value
        for key, value in report.items()
        if key not in {"report_id", "report_hash"}
    }
    report["report_hash"] = canonical_payload_hash(core)
    report["report_id"] = f"hfer-{report['report_hash'][:20]}"


class FrozenExperimentProvenanceLedgerV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = synthetic_frame()
        cls.config = config()
        cls.context = context()
        cls.protocol = protocol(cls.frame, cls.config)
        cls.report = build_frozen_evaluation_report(
            cls.protocol,
            cls.frame,
            cls.config,
            experiment_context=cls.context,
        )
        cls.records = _run_records(cls.report)

    def test_all_frozen_and_multiple_testing_consumers_are_bound(self) -> None:
        ledger = self.report["experiment_provenance"]
        self.assertEqual(
            ledger["schema_version"],
            FROZEN_EXPERIMENT_PROVENANCE_LEDGER_VERSION,
        )
        self.assertEqual(
            ledger["trust_model"],
            FROZEN_EXPERIMENT_PROVENANCE_TRUST_MODEL,
        )
        self.assertEqual(ledger["entry_count"], 99)
        self.assertEqual(
            sum(
                entry["multiple_testing_receipt"] is not None
                for entry in ledger["entries"]
            ),
            42,
        )
        self.assertTrue(verify_frozen_experiment_provenance_ledger(
            ledger,
            self.records,
            expected_context=self.protocol["experiment_context"]["context"],
            protocol_hash=self.protocol["protocol_hash"],
            symbol=self.protocol["config"]["symbol"],
            timeframe=self.protocol["config"]["timeframe"],
        ))

    def test_multiple_testing_observations_use_verified_receipt_hashes(self) -> None:
        receipt_hashes = verified_multiple_testing_receipt_hashes(
            self.report["experiment_provenance"],
            self.records,
            expected_context=self.protocol["experiment_context"]["context"],
            protocol_hash=self.protocol["protocol_hash"],
            symbol=self.protocol["config"]["symbol"],
            timeframe=self.protocol["config"]["timeframe"],
        )
        self.assertEqual(len(receipt_hashes), 42)
        self.assertEqual(
            {item["provenance_receipt_hash"] for item in self.report[
                "multiple_testing_ledger"
            ]["observations"]},
            set(receipt_hashes.values()),
        )

    def test_resealed_expected_reproducibility_drift_fails_closed(self) -> None:
        attacked = deepcopy(self.report)
        ledger = attacked["experiment_provenance"]
        ledger["entries"][0]["expected_reproducibility"]["config_hash"] = (
            "0" * 64
        )
        ledger_core = {
            key: value
            for key, value in ledger.items()
            if key != "ledger_hash"
        }
        ledger["ledger_hash"] = canonical_payload_hash(ledger_core)
        _reseal_report(attacked)

        with self.assertRaisesRegex(
            ValueError,
            "provenance_ledger_verification_failed",
        ):
            verify_frozen_evaluation_report(
                attacked,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=self.context,
            )

    def test_ledger_is_non_authorizing_and_externally_anchored(self) -> None:
        ledger = self.report["experiment_provenance"]
        self.assertTrue(ledger["external_artifact_hash_required"])
        for field in (
            "ranking_allowed",
            "paper_authorized",
            "live_order_allowed",
            "order_entry_allowed",
            "result_is_profitability_proof",
        ):
            self.assertIs(ledger[field], False)


if __name__ == "__main__":
    unittest.main()
