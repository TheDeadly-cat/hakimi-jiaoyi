from __future__ import annotations

from copy import deepcopy
from itertools import combinations
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as budget_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v4 as subject,
)
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
    evaluate_strategy_correlation_strata_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class StrategyCorrelationClusterEffectiveBetBudgetV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.before = [
            {"symbol": "A", "notional": 2_500, "direction": "LONG"},
            {"symbol": "B", "notional": 1_000, "direction": "SHORT"},
        ]
        self.after_long_reduction = [
            {"symbol": "A", "notional": 2_000, "direction": "LONG"},
            {"symbol": "B", "notional": 1_000, "direction": "SHORT"},
        ]
        self.long_reduction_kwargs = {
            "proposed_symbol": "A",
            "proposed_notional": 500,
            "proposed_direction": "SHORT",
        }
        self.long_transition = (
            subject.build_strategy_correlation_cluster_risk_reduction_transition_v1(
                self.before,
                self.after_long_reduction,
                **self.long_reduction_kwargs,
            )
        )

        self.preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": "cluster-a", "members": ["A"]},
                {"cluster_id": "cluster-b", "members": ["B"]},
                {"cluster_id": "cluster-c", "members": ["C"]},
            ]
        )
        correlations = {
            pair: 0.10
            for pair in combinations(self.preregistration["symbols"], 2)
        }
        self.matrix = build_correlation_matrix_contract(
            self.preregistration["symbols"], correlations
        )
        self.audit = build_correlation_cluster_complete_link_audit(
            self.preregistration, self.matrix
        )
        cells = [
            {
                "gate_status": "PASS",
                "lane": "RAW_EXCESS",
                "strategy_id": "synthetic-strategy",
                "symbol": symbol,
                "variant_id": "synthetic-variant",
            }
            for symbol in self.preregistration["symbols"]
        ]
        self.complete_link_gate = evaluate_correlation_cluster_gate_v2(
            self.preregistration,
            self.matrix,
            cells,
            strategy_id="synthetic-strategy",
            variant_id="synthetic-variant",
            lane="RAW_EXCESS",
        )
        self.strata_registration = (
            build_strategy_correlation_strata_preregistration(
                self.preregistration,
                [
                    {
                        "dimension_id": "asset-family",
                        "strata": [
                            {
                                "stratum_id": "family-a",
                                "cluster_ids": ["cluster-a"],
                            },
                            {
                                "stratum_id": "family-b",
                                "cluster_ids": ["cluster-b"],
                            },
                            {
                                "stratum_id": "family-c",
                                "cluster_ids": ["cluster-c"],
                            },
                        ],
                    }
                ],
            )
        )
        self.strata_gate = evaluate_strategy_correlation_strata_gate(
            self.strata_registration,
            self.complete_link_gate,
            source_preregistration=self.preregistration,
        )

    def evaluate_reduction(self, **overrides):
        kwargs = {
            "strata_registration": None,
            "strata_gate": None,
            "complete_link_gate": None,
            "equity": 10_000,
            "positions": self.before,
            **self.long_reduction_kwargs,
            "max_cluster_gross_pct": 45.0,
            "risk_increasing": False,
            "positions_after": self.after_long_reduction,
            "risk_reduction_transition": self.long_transition,
        }
        kwargs.update(overrides)
        return subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v4(
            None, None, None, **kwargs
        )

    def test_reproduces_v3_caller_flag_bypass_gap(self) -> None:
        document = (
            budget_v3.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
                None,
                None,
                None,
                strata_registration=None,
                strata_gate=None,
                complete_link_gate=None,
                equity=10_000,
                positions=[
                    {"symbol": "A", "notional": 1_000, "direction": "LONG"}
                ],
                proposed_symbol="A",
                proposed_notional=500,
                proposed_direction="LONG",
                risk_increasing=False,
            )
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["decision"], "RISK_REDUCTION_PATH")
        self.assertIsNone(document["portfolio"]["symbol_ticket_count"])

    def test_verified_long_reduction_passes_without_cluster_sources(self) -> None:
        document = self.evaluate_reduction()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "PASS_VERIFIED_RISK_REDUCTION_TRANSITION",
        )
        self.assertTrue(
            document["facts"][
                "risk_reduction_derived_from_position_transition"
            ]
        )
        self.assertFalse(
            document["facts"]["caller_risk_reduction_flag_sufficient"]
        )
        self.assertEqual(
            document["transition_summary"]["portfolio_gross_reduction"],
            500.0,
        )
        receipt = (
            subject.verify_strategy_correlation_cluster_risk_reduction_transition_v1(
                self.long_transition,
                self.before,
                self.after_long_reduction,
                **self.long_reduction_kwargs,
            )
        )
        self.assertEqual(receipt["status"], "PASS")

    def test_verified_short_reduction_passes(self) -> None:
        after = [
            {"symbol": "A", "notional": 2_500, "direction": "LONG"},
            {"symbol": "B", "notional": 700, "direction": "SHORT"},
        ]
        kwargs = {
            "proposed_symbol": "B",
            "proposed_notional": 300,
            "proposed_direction": "LONG",
        }
        transition = (
            subject.build_strategy_correlation_cluster_risk_reduction_transition_v1(
                self.before, after, **kwargs
            )
        )
        document = self.evaluate_reduction(
            positions_after=after,
            risk_reduction_transition=transition,
            **kwargs,
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["transition_summary"]["position_direction"], "SHORT"
        )
        self.assertEqual(
            document["transition_summary"]["order_direction"], "LONG"
        )

    def test_same_direction_add_labeled_reduction_is_blocked(self) -> None:
        after = [
            {"symbol": "A", "notional": 3_000, "direction": "LONG"},
            {"symbol": "B", "notional": 1_000, "direction": "SHORT"},
        ]
        with self.assertRaises(subject.VerifiedRiskReductionBudgetError):
            subject.build_strategy_correlation_cluster_risk_reduction_transition_v1(
                self.before,
                after,
                proposed_symbol="A",
                proposed_notional=500,
                proposed_direction="LONG",
            )
        document = self.evaluate_reduction(
            positions_after=after,
            risk_reduction_transition=self.long_transition,
            proposed_direction="LONG",
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "verified_risk_reduction_transition_invalid",
            document["blockers"],
        )

    def test_overclose_or_crossing_is_blocked(self) -> None:
        after = [{"symbol": "B", "notional": 1_000, "direction": "SHORT"}]
        with self.assertRaises(subject.VerifiedRiskReductionBudgetError):
            subject.build_strategy_correlation_cluster_risk_reduction_transition_v1(
                self.before,
                after,
                proposed_symbol="A",
                proposed_notional=3_000,
                proposed_direction="SHORT",
            )

    def test_mismatched_target_after_is_blocked(self) -> None:
        after = [
            {"symbol": "A", "notional": 2_100, "direction": "LONG"},
            {"symbol": "B", "notional": 1_000, "direction": "SHORT"},
        ]
        with self.assertRaises(subject.VerifiedRiskReductionBudgetError):
            subject.build_strategy_correlation_cluster_risk_reduction_transition_v1(
                self.before, after, **self.long_reduction_kwargs
            )

    def test_other_position_change_is_blocked(self) -> None:
        after = [
            {"symbol": "A", "notional": 2_000, "direction": "LONG"},
            {"symbol": "B", "notional": 900, "direction": "SHORT"},
        ]
        with self.assertRaises(subject.VerifiedRiskReductionBudgetError):
            subject.build_strategy_correlation_cluster_risk_reduction_transition_v1(
                self.before, after, **self.long_reduction_kwargs
            )

    def test_new_symbol_in_after_snapshot_is_blocked(self) -> None:
        after = self.after_long_reduction + [
            {"symbol": "C", "notional": 100, "direction": "LONG"}
        ]
        with self.assertRaises(subject.VerifiedRiskReductionBudgetError):
            subject.build_strategy_correlation_cluster_risk_reduction_transition_v1(
                self.before, after, **self.long_reduction_kwargs
            )

    def test_duplicate_boolean_nonfinite_and_direction_aliases_fail_closed(self) -> None:
        cases = [
            (
                self.before + [deepcopy(self.before[0])],
                self.after_long_reduction,
                self.long_reduction_kwargs,
            ),
            (
                self.before,
                self.after_long_reduction,
                self.long_reduction_kwargs | {"proposed_notional": True},
            ),
            (
                self.before,
                self.after_long_reduction,
                self.long_reduction_kwargs
                | {"proposed_notional": float("inf")},
            ),
            (
                self.before,
                self.after_long_reduction,
                self.long_reduction_kwargs
                | {"proposed_direction": "FLAT"},
            ),
        ]
        for before, after, kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(
                    subject.VerifiedRiskReductionBudgetError
                ):
                    subject.build_strategy_correlation_cluster_risk_reduction_transition_v1(
                        before, after, **kwargs
                    )

    def test_caller_flag_without_proof_is_blocked(self) -> None:
        document = self.evaluate_reduction(
            positions_after=None,
            risk_reduction_transition=None,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "verified_risk_reduction_transition_missing",
            document["blockers"],
        )

    def test_risk_increasing_path_preserves_exact_v3_pass(self) -> None:
        document = (
            subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v4(
                self.preregistration,
                self.matrix,
                self.audit,
                strata_registration=self.strata_registration,
                strata_gate=self.strata_gate,
                complete_link_gate=self.complete_link_gate,
                equity=10_000,
                positions=[
                    {"symbol": "A", "notional": 2_500, "direction": "LONG"}
                ],
                proposed_symbol="B",
                proposed_notional=2_500,
                proposed_direction="LONG",
                max_cluster_gross_pct=45.0,
                risk_increasing=True,
            )
        )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "PASS_VERIFIED_RISK_INCREASING_BUDGET",
        )
        self.assertTrue(
            document["facts"]["risk_increasing_v3_decision_preserved"]
        )

    def test_risk_increasing_path_rejects_transition_alias(self) -> None:
        document = (
            subject.evaluate_strategy_correlation_cluster_effective_bet_budget_v4(
                self.preregistration,
                self.matrix,
                self.audit,
                strata_registration=self.strata_registration,
                strata_gate=self.strata_gate,
                complete_link_gate=self.complete_link_gate,
                equity=10_000,
                positions=self.before,
                proposed_symbol="A",
                proposed_notional=500,
                proposed_direction="SHORT",
                risk_increasing=True,
                positions_after=self.after_long_reduction,
                risk_reduction_transition=self.long_transition,
            )
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "unexpected_risk_reduction_transition", document["blockers"]
        )

    def test_exact_verifier_rejects_resealed_permission_promotion(self) -> None:
        document = self.evaluate_reduction()
        receipt = (
            subject.verify_strategy_correlation_cluster_effective_bet_budget_v4(
                document,
                None,
                None,
                None,
                strata_registration=None,
                strata_gate=None,
                complete_link_gate=None,
                equity=10_000,
                positions=self.before,
                **self.long_reduction_kwargs,
                max_cluster_gross_pct=45.0,
                risk_increasing=False,
                positions_after=self.after_long_reduction,
                risk_reduction_transition=self.long_transition,
            )
        )
        self.assertEqual(receipt["status"], "PASS")
        promoted = deepcopy(document)
        promoted["authority"]["current_admission_allowed"] = True
        promoted = seal_strict_canonical_document(
            promoted, "budget_v4_hash"
        )
        receipt = (
            subject.verify_strategy_correlation_cluster_effective_bet_budget_v4(
                promoted,
                None,
                None,
                None,
                strata_registration=None,
                strata_gate=None,
                complete_link_gate=None,
                equity=10_000,
                positions=self.before,
                **self.long_reduction_kwargs,
                max_cluster_gross_pct=45.0,
                risk_increasing=False,
                positions_after=self.after_long_reduction,
                risk_reduction_transition=self.long_transition,
            )
        )
        self.assertEqual(receipt["status"], "BLOCK")

    def test_output_is_summary_only_deterministic_and_inputs_are_immutable(self) -> None:
        before = deepcopy(
            [
                self.before,
                self.after_long_reduction,
                self.long_transition,
            ]
        )
        first = self.evaluate_reduction()
        second = self.evaluate_reduction()
        self.assertEqual(first, second)
        encoded = json.dumps(first, sort_keys=True)
        for forbidden in (
            '"positions":',
            '"positions_before":',
            '"positions_after":',
            '"cluster_exposures":',
            '"strata":',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(
            before,
            [
                self.before,
                self.after_long_reduction,
                self.long_transition,
            ],
        )
        self.assertTrue(
            all(
                value is False
                for key, value in first["authority"].items()
                if key != "descriptive_only"
            )
        )
        self.assertTrue(first["authority"]["descriptive_only"])

    def test_production_has_no_io_runtime_or_legacy_precomputed_acceptance(self) -> None:
        source = Path(subject.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "open(",
            "Path(",
            "socket",
            "subprocess",
            "time.time",
            "datetime.now",
            "runtime/",
            'precomputed_predecessor_result_accepted": True',
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
