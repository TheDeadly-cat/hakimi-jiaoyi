from __future__ import annotations

from copy import deepcopy
import unittest

from hakimi_research.distribution_evidence import (
    DISTRIBUTION_EVIDENCE_VERSION,
    DistributionEvidenceError,
    build_distribution_evidence,
    verify_distribution_evidence,
)
from tests.test_validation_evidence_report_v1 import REPORT


def _build(report: dict[str, object] | None = None) -> dict[str, object]:
    return build_distribution_evidence(
        REPORT if report is None else report,
        source_result_path=["backtest_result"],
        periods_per_year=252,
    )


class DistributionEvidenceV1Tests(unittest.TestCase):
    def test_complete_result_builds_deterministic_tail_distribution_evidence(self) -> None:
        first = _build()
        second = _build()
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], DISTRIBUTION_EVIDENCE_VERSION)
        self.assertEqual(first["status"], "PARTIAL")
        self.assertIn("FEE_LOAD_UNAVAILABLE_TOTAL_FEES_MISSING", first["gaps"])
        self.assertGreaterEqual(first["metrics"]["period_return_count"], 100)
        self.assertEqual(first["metrics"]["closed_trade_count"], 3)
        self.assertIsNotNone(first["metrics"]["tail_cvar_99"])
        self.assertGreaterEqual(len(first["monthly_returns"]), 12)
        self.assertGreaterEqual(len(first["yearly_returns"]), 2)

    def test_verifier_recomputes_source_and_rejects_equity_mutation(self) -> None:
        evidence = _build()
        self.assertEqual(verify_distribution_evidence(evidence, REPORT)["state"], "PARTIAL")
        changed = deepcopy(REPORT)
        changed["backtest_result"]["equity_curve"][20]["equity"] += 1.0
        with self.assertRaisesRegex(DistributionEvidenceError, "does not exactly match recomputed"):
            verify_distribution_evidence(evidence, changed)

    def test_source_path_is_exact_and_hash_bound(self) -> None:
        evidence = _build()
        self.assertEqual(evidence["source_result_path"], ["backtest_result"])
        self.assertEqual(len(evidence["source_report_sha256"]), 64)
        self.assertEqual(len(evidence["source_result_sha256"]), 64)
        with self.assertRaisesRegex(DistributionEvidenceError, "does not resolve"):
            build_distribution_evidence(REPORT, source_result_path=["missing"], periods_per_year=252)

    def test_nonmonotonic_time_and_nonpositive_equity_are_rejected(self) -> None:
        nonmonotonic = deepcopy(REPORT)
        nonmonotonic["backtest_result"]["equity_curve"][2]["time"] = nonmonotonic["backtest_result"]["equity_curve"][1]["time"]
        with self.assertRaisesRegex(DistributionEvidenceError, "strictly increasing"):
            _build(nonmonotonic)

        nonpositive = deepcopy(REPORT)
        nonpositive["backtest_result"]["equity_curve"][2]["equity"] = 0.0
        with self.assertRaisesRegex(DistributionEvidenceError, "positive"):
            _build(nonpositive)

    def test_fill_replay_rejects_negative_position_and_malformed_actions(self) -> None:
        negative = deepcopy(REPORT)
        negative["backtest_result"]["fills"][0]["action"] = "SELL"
        with self.assertRaisesRegex(DistributionEvidenceError, "position replay became negative"):
            _build(negative)

        malformed = deepcopy(REPORT)
        malformed["backtest_result"]["fills"][0]["action"] = "HOLD"
        with self.assertRaisesRegex(DistributionEvidenceError, "BUY or SELL"):
            _build(malformed)

    def test_small_sample_is_partial_and_never_fills_unknown_metrics_with_zero(self) -> None:
        small = deepcopy(REPORT)
        small["backtest_result"]["equity_curve"] = small["backtest_result"]["equity_curve"][:10]
        small["backtest_result"]["fills"] = []
        evidence = _build(small)
        self.assertEqual(evidence["status"], "PARTIAL")
        self.assertIn("TAIL_SAMPLE_LT_20", evidence["gaps"])
        self.assertIn("TAIL_SAMPLE_LT_100", evidence["gaps"])
        self.assertIsNone(evidence["metrics"]["tail_var_95"])
        self.assertIsNone(evidence["metrics"]["profit_factor"])

    def test_one_sided_trades_keep_profit_factor_and_payoff_unknown(self) -> None:
        one_sided = deepcopy(REPORT)
        for fill in one_sided["backtest_result"]["fills"]:
            if fill["action"] == "SELL":
                fill["pnl"] = abs(fill["pnl"]) + 1.0
        evidence = _build(one_sided)
        self.assertEqual(evidence["status"], "PARTIAL")
        self.assertIn("PROFIT_FACTOR_AND_PAYOFF_UNDEFINED_ONE_SIDED_TRADES", evidence["gaps"])
        self.assertIsNone(evidence["metrics"]["profit_factor"])
        self.assertIsNone(evidence["metrics"]["payoff_ratio"])

    def test_turnover_exposure_and_concentration_are_observations_not_authority(self) -> None:
        evidence = _build()
        self.assertIsNotNone(evidence["metrics"]["turnover_ratio"])
        self.assertIsNotNone(evidence["metrics"]["market_exposure_ratio"])
        self.assertIsNone(evidence["metrics"]["fee_load_ratio"])
        self.assertIn("FEE_LOAD_UNAVAILABLE_TOTAL_FEES_MISSING", evidence["gaps"])
        self.assertIsNotNone(evidence["concentration"]["top_positive_period_return_share"])
        self.assertIsNotNone(evidence["concentration"]["positive_period_return_hhi"])
        self.assertIsNotNone(evidence["concentration"]["top_positive_month_share"])
        self.assertIsNotNone(evidence["concentration"]["top_positive_trade_pnl_share"])
        self.assertIsNotNone(evidence["concentration"]["positive_trade_pnl_hhi"])
        self.assertEqual(
            evidence["concentration"]["best_fixed_21_period_window"]["state"],
            "OBSERVED",
        )
        self.assertFalse(any(evidence["authority"].values()))

    def test_small_sample_retains_fixed_window_and_hhi_gaps(self) -> None:
        small = deepcopy(REPORT)
        small["backtest_result"]["equity_curve"] = small["backtest_result"][
            "equity_curve"
        ][:10]
        small["backtest_result"]["fills"] = []
        evidence = _build(small)
        fixed = evidence["concentration"]["best_fixed_21_period_window"]
        self.assertEqual(fixed["state"], "GAP")
        self.assertEqual(fixed["gap_code"], "FIXED_21_PERIOD_WINDOW_UNAVAILABLE")
        self.assertIn("FIXED_21_PERIOD_WINDOW_UNAVAILABLE", evidence["gaps"])

    def test_concentration_tamper_is_rejected(self) -> None:
        evidence = _build()
        evidence["concentration"]["positive_period_return_hhi"] = "0"
        with self.assertRaisesRegex(
            DistributionEvidenceError,
            "does not exactly match recomputed",
        ):
            verify_distribution_evidence(evidence, REPORT)

    def test_authority_escalation_is_rejected_before_recompute_equality(self) -> None:
        evidence = _build()
        evidence["authority"]["paper_authorized"] = True
        with self.assertRaisesRegex(DistributionEvidenceError, "must be exact false"):
            verify_distribution_evidence(evidence, REPORT)

    def test_evidence_metric_tamper_is_rejected(self) -> None:
        evidence = _build()
        evidence["metrics"]["sortino_ratio"] = "999"
        with self.assertRaisesRegex(DistributionEvidenceError, "does not exactly match recomputed"):
            verify_distribution_evidence(evidence, REPORT)

    def test_nonfinite_source_number_is_rejected(self) -> None:
        report = deepcopy(REPORT)
        report["backtest_result"]["equity_curve"][5]["equity"] = float("nan")
        with self.assertRaisesRegex(DistributionEvidenceError, "finite"):
            _build(report)

    def test_exact_container_subclasses_are_rejected(self) -> None:
        class EvilDict(dict):
            pass

        with self.assertRaisesRegex(DistributionEvidenceError, "unsupported non-native type"):
            _build(EvilDict(REPORT))


if __name__ == "__main__":
    unittest.main()
