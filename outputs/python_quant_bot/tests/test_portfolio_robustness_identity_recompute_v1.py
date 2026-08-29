from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unittest

from exchange_terminal.services.portfolio_robustness import (
    PORTFOLIO_ROBUSTNESS_IDENTITY_CONTRACT_VERSION,
    PORTFOLIO_ROBUSTNESS_SCHEMA_VERSION,
    build_robustness_assessment,
    verify_robustness_report,
)
from tests.test_portfolio_robustness import result


def canonical_hash(payload: object) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def valid_report() -> dict[str, object]:
    return build_robustness_assessment(
        candidate_hash="candidate",
        dataset_hash="dataset",
        parameter_results=[result(f"P{index}") for index in range(7)],
        ablation_results=[result(f"A{index}") for index in range(8)],
        capital_results=[result("CAPITAL_100K"), result("CAPITAL_1M")],
        candidate_verification={"status": "PASS"},
    )


def reseal(report: dict[str, object]) -> dict[str, object]:
    changed = deepcopy(report)
    changed.pop("robustness_hash", None)
    changed["robustness_hash"] = canonical_hash(changed)
    return changed


class PortfolioRobustnessIdentityRecomputeV1Tests(unittest.TestCase):
    def test_valid_report_uses_v3_identity_contract(self) -> None:
        report = valid_report()
        verification = verify_robustness_report(report, candidate_hash="candidate")

        self.assertEqual(PORTFOLIO_ROBUSTNESS_SCHEMA_VERSION, "portfolio-robustness-diagnostic-v3")
        self.assertEqual(report["status"], "ROBUSTNESS_PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(
            verification["identity_contract_version"],
            PORTFOLIO_ROBUSTNESS_IDENTITY_CONTRACT_VERSION,
        )

    def test_duplicate_parameter_and_thin_ablation_identities_block(self) -> None:
        report = build_robustness_assessment(
            candidate_hash="candidate",
            dataset_hash="dataset",
            parameter_results=[result("P0") for _ in range(7)],
            ablation_results=[result("A0")],
            capital_results=[result("CAPITAL_100K"), result("CAPITAL_1M")],
            candidate_verification={"status": "PASS"},
        )

        self.assertEqual(report["status"], "ROBUSTNESS_BLOCK")
        self.assertFalse(report["checks"]["diagnostic_identity_contract_pass"])
        self.assertIn("parameter_results_labels_not_unique", report["contract_issues"])
        self.assertIn("ablation_results_count_below_4", report["contract_issues"])

    def test_duplicate_run_hashes_block_even_with_unique_labels(self) -> None:
        parameter_results = [result(f"P{index}") for index in range(7)]
        for item in parameter_results:
            item["run_hash"] = "same-run"

        report = build_robustness_assessment(
            candidate_hash="candidate",
            dataset_hash="dataset",
            parameter_results=parameter_results,
            ablation_results=[result(f"A{index}") for index in range(8)],
            capital_results=[result("CAPITAL_100K"), result("CAPITAL_1M")],
            candidate_verification={"status": "PASS"},
        )

        self.assertEqual(report["status"], "ROBUSTNESS_BLOCK")
        self.assertIn("parameter_results_run_hashes_not_unique", report["contract_issues"])

    def test_failed_capital_result_cannot_pass_on_positive_metric_alone(self) -> None:
        failed_capital = result("CAPITAL_100K")
        failed_capital["ok"] = False
        report = build_robustness_assessment(
            candidate_hash="candidate",
            dataset_hash="dataset",
            parameter_results=[result(f"P{index}") for index in range(7)],
            ablation_results=[result(f"A{index}") for index in range(8)],
            capital_results=[failed_capital, result("CAPITAL_1M")],
            candidate_verification={"status": "PASS"},
        )

        self.assertEqual(report["status"], "ROBUSTNESS_BLOCK")
        self.assertFalse(report["checks"]["baseline_capital_positive"])
        self.assertFalse(report["checks"]["all_diagnostics_ok"])

    def test_resealed_fragile_results_and_selection_authority_are_recomputed(self) -> None:
        attacked = valid_report()
        attacked["parameter_results"] = [
            result(f"P{index}", positive=False)
            for index in range(7)
        ]
        attacked["parameter_selection_allowed"] = True
        attacked = reseal(attacked)

        verification = verify_robustness_report(attacked, candidate_hash="candidate")

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("robustness_diagnostic_authority_invalid", verification["blockers"])
        self.assertIn("robustness_checks_mismatch", verification["blockers"])
        self.assertIn("robustness_derived_checks_not_passed", verification["blockers"])

    def test_non_object_report_fails_closed_without_exception(self) -> None:
        for report in (None, "report", ["report"]):
            with self.subTest(report=repr(report)):
                verification = verify_robustness_report(report, candidate_hash="candidate")
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(
                    verification["blockers"],
                    ["robustness_report_object_required"],
                )


if __name__ == "__main__":
    unittest.main()
