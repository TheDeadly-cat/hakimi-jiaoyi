from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from _canonical_source import activate_canonical_source

activate_canonical_source()

from exchange_terminal.application.strategy_research_validation_evidence_adapter_v1 import (
    StrategyResearchValidationEvidenceAdapterError,
    build_multiple_testing_ledger_from_verified_strategy_research_report,
    build_validation_evidence_from_formal_search_lineage,
)
from exchange_terminal.services.strategy_research_search_lineage import (
    build_strategy_research_search_lineage_v2,
)
from hakimi_research.validation_evidence import verify_validation_evidence
from test_validation_evidence_report_v1 import REPORT, _components, _distribution_evidence


ADAPTER_MODULE = "exchange_terminal.application.strategy_research_validation_evidence_adapter_v1"
SEARCH_FAMILY_ID = "synthetic-trial-ledger-family-v1"


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _variant(variant_id: str) -> dict[str, object]:
    return {
        "variant_id": variant_id,
        "strategy_id": "dual_ma",
        "param_hash": _hash(f"params-{variant_id}"),
        "implementation_fingerprint": _hash(f"implementation-{variant_id}"),
    }


def _formal_report() -> dict[str, object]:
    variant_ids = ["parameter-3", "parameter-1", "parameter-2"]
    selection_cells = []
    for variant_id in variant_ids:
        for symbol in ("NVDA", "AAPL"):
            selection_cells.append({
                "variant_id": variant_id,
                "symbol": symbol,
                "run_hash": _hash(f"selection-{variant_id}-{symbol}"),
            })
    return {
        "schema_version": 16,
        "batch_run_hash": _hash("formal-report-v1"),
        "batch_spec": {"variants": [_variant(item) for item in variant_ids]},
        "selection_cells": selection_cells,
        "validation_rankings": [
            {"variant_id": "parameter-3", "status": "BLOCK", "blockers": ["RAW_EXCESS:score_not_positive"]},
            {"variant_id": "parameter-1", "status": "PASS", "blockers": []},
            {"variant_id": "parameter-2", "status": "BLOCK", "blockers": ["RISK_ADJUSTED:stability_gap"]},
        ],
        "frozen_candidates": [{"variant_id": "parameter-1"}],
        "test_cells": [
            {"variant_id": "parameter-1", "symbol": "FRESH", "run_hash": _hash("test-parameter-1-FRESH")},
        ],
        "test_results": [
            {"variant_id": "parameter-1", "status": "PASS", "blockers": []},
        ],
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verified_ledger(report: dict[str, object] | None = None) -> dict[str, object]:
    with patch(
        f"{ADAPTER_MODULE}.verify_strategy_research_report",
        return_value={"status": "PASS", "blockers": []},
    ):
        return build_multiple_testing_ledger_from_verified_strategy_research_report(
            _formal_report() if report is None else report
        )


class StrategyResearchTrialLedgerAdapterV1Tests(unittest.TestCase):
    def test_verified_report_projects_sorted_per_trial_receipts_and_block_decisions(self) -> None:
        ledger = _verified_ledger()
        self.assertEqual(
            ledger["preregistered_trial_ids"],
            ["parameter-1", "parameter-2", "parameter-3"],
        )
        self.assertEqual(ledger["selected_parameter_id"], "parameter-1")
        self.assertEqual(ledger["producer_report_sha256"], _hash("formal-report-v1"))
        outcomes = {item["trial_id"]: item for item in ledger["trial_outcomes"]}
        self.assertEqual(outcomes["parameter-1"]["decision_status"], "PASS")
        self.assertEqual(outcomes["parameter-2"]["decision_status"], "BLOCK")
        self.assertEqual(
            outcomes["parameter-2"]["decision_blockers"],
            ["RISK_ADJUSTED:stability_gap"],
        )
        self.assertTrue(all(item["status"] == "OBSERVED" for item in outcomes.values()))
        self.assertTrue(all(len(item["result_sha256"]) == 64 for item in outcomes.values()))

    def test_producer_verifier_block_prevents_projection(self) -> None:
        with patch(
            f"{ADAPTER_MODULE}.verify_strategy_research_report",
            return_value={"status": "BLOCK", "blockers": ["synthetic_formal_block"]},
        ):
            with self.assertRaisesRegex(
                StrategyResearchValidationEvidenceAdapterError,
                "formal report verification blocked",
            ):
                build_multiple_testing_ledger_from_verified_strategy_research_report(_formal_report())

    def test_one_cell_receipt_change_changes_only_its_trial_receipt(self) -> None:
        baseline = _verified_ledger()
        changed_report = _formal_report()
        changed_report["selection_cells"][0]["run_hash"] = _hash("changed-cell")
        changed = _verified_ledger(changed_report)
        baseline_hashes = {item["trial_id"]: item["result_sha256"] for item in baseline["trial_outcomes"]}
        changed_hashes = {item["trial_id"]: item["result_sha256"] for item in changed["trial_outcomes"]}
        self.assertNotEqual(baseline_hashes["parameter-3"], changed_hashes["parameter-3"])
        self.assertEqual(baseline_hashes["parameter-1"], changed_hashes["parameter-1"])
        self.assertEqual(baseline_hashes["parameter-2"], changed_hashes["parameter-2"])

    def test_duplicate_variant_or_ranking_is_rejected(self) -> None:
        duplicate_variant = _formal_report()
        duplicate_variant["batch_spec"]["variants"].append(deepcopy(duplicate_variant["batch_spec"]["variants"][0]))
        with self.assertRaisesRegex(StrategyResearchValidationEvidenceAdapterError, "variant_id values must be unique"):
            _verified_ledger(duplicate_variant)

        duplicate_ranking = _formal_report()
        duplicate_ranking["validation_rankings"].append(deepcopy(duplicate_ranking["validation_rankings"][0]))
        with self.assertRaisesRegex(StrategyResearchValidationEvidenceAdapterError, "exactly one aggregate ranking"):
            _verified_ledger(duplicate_ranking)

    def test_zero_or_multiple_frozen_selections_are_rejected(self) -> None:
        zero = _formal_report()
        zero["frozen_candidates"] = []
        two = _formal_report()
        two["frozen_candidates"].append({"variant_id": "parameter-2"})
        for report in (zero, two):
            with self.assertRaisesRegex(
                StrategyResearchValidationEvidenceAdapterError,
                "exactly one preregistered frozen selection",
            ):
                _verified_ledger(report)

    def test_authority_escalation_and_malformed_cell_hash_are_rejected(self) -> None:
        escalation = _formal_report()
        escalation["live_order_allowed"] = True
        with self.assertRaisesRegex(StrategyResearchValidationEvidenceAdapterError, "live_order_allowed"):
            _verified_ledger(escalation)

        malformed = _formal_report()
        malformed["selection_cells"][0]["run_hash"] = "not-a-digest"
        with self.assertRaisesRegex(StrategyResearchValidationEvidenceAdapterError, "SHA-256"):
            _verified_ledger(malformed)

    def test_exact_dict_subclass_is_rejected_before_producer_verifier(self) -> None:
        class EvilDict(dict):
            pass

        with patch(f"{ADAPTER_MODULE}.verify_strategy_research_report") as verifier:
            with self.assertRaisesRegex(StrategyResearchValidationEvidenceAdapterError, "unsupported non-native type"):
                build_multiple_testing_ledger_from_verified_strategy_research_report(EvilDict(_formal_report()))
        verifier.assert_not_called()

    def test_trial_ledger_and_formal_count_lineage_compose_into_adr0510(self) -> None:
        ledger = _verified_ledger()
        lineage = build_strategy_research_search_lineage_v2(
            search_family_id=SEARCH_FAMILY_ID,
            prior_registrations=[],
            current_trial_count=3,
        )
        walk, stability, _synthetic_ledger, regimes = _components()
        evidence = build_validation_evidence_from_formal_search_lineage(
            REPORT,
            experiment_id="synthetic-per-trial-composition-v1",
            formal_search_lineage=lineage,
            distribution_evidence=_distribution_evidence(),
            expected_search_family_id=SEARCH_FAMILY_ID,
            expected_current_trial_count=3,
            expected_prior_registrations=[],
            walk_forward=walk,
            parameter_stability=stability,
            multiple_testing=ledger,
            market_regimes=regimes,
        )
        summary = verify_validation_evidence(evidence, REPORT)
        self.assertEqual(summary["formal_search_lineage"]["state"], "OBSERVED")
        self.assertEqual(summary["multiple_testing"]["state"], "OBSERVED")
        self.assertEqual(evidence["multiple_testing"]["producer_report_sha256"], _hash("formal-report-v1"))
        self.assertFalse(any(evidence["authority"].values()))


if __name__ == "__main__":
    unittest.main()
