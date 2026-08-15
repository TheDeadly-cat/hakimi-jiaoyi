from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.strategy_research_failure_conditions import (
    build_strategy_research_failure_conditions,
    build_strategy_research_failure_conditions_v2,
    build_strategy_research_failure_conditions_v3,
    build_strategy_research_failure_conditions_v4,
)


class StrategyResearchFailureConditionsTests(unittest.TestCase):
    @staticmethod
    def _evidence() -> dict[str, dict[str, object]]:
        return {
            "parameter": {
                "status": "PASS",
                "plateau_width": 2,
                "adjacent_near_best_variant_count": 1,
                "best_adjusted_score": 4.25,
                "peak_only": False,
                "blockers": [],
            },
            "cost": {
                "status": "PASS",
                "break_even_preserved": True,
                "worst_stressed_return_pct": 1.25,
                "blockers": [],
            },
            "time": {
                "status": "PASS",
                "usable_fold_count": 6,
                "positive_fold_count": 5,
                "blockers": [],
            },
            "signal": {"status": "MATCH", "blockers": []},
            "full": {"status": "MATCH", "blockers": []},
        }

    @staticmethod
    def _build(evidence: dict[str, dict[str, object]], *, strategy_id: str = "dual_ma") -> dict[str, object]:
        return build_strategy_research_failure_conditions(
            strategy_id=strategy_id,
            parameter_stability=evidence["parameter"],
            cost_sensitivity=evidence["cost"],
            chronological_slices=evidence["time"],
            implementation_currentness=evidence["signal"],
            full_implementation_currentness=evidence["full"],
        )

    def test_checked_dimensions_remain_descriptive_gaps_and_do_not_mutate_inputs(self) -> None:
        evidence = self._evidence()
        before = deepcopy(evidence)

        result = self._build(evidence)

        self.assertEqual(evidence, before)
        self.assertEqual(result["status"], "GAPS")
        self.assertEqual(result["observed"], [])
        self.assertIn("dataset_currentness_not_checked", result["evidence_gaps"])
        self.assertIn("report_age_policy_not_checked", result["evidence_gaps"])
        self.assertIn(
            "natural_forward_performance_not_proven_by_strategy_report",
            result["evidence_gaps"],
        )
        self.assertEqual([row["triggered"] for row in result["conditions"]], [False] * 5)
        self.assertFalse(result["profitability_proven"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_observed_failures_are_condition_ids_and_preserve_blocker_details(self) -> None:
        evidence = self._evidence()
        evidence["parameter"].update({
            "status": "REVIEW",
            "blockers": ["parameter_stability_peak_without_adjacent_plateau"],
        })
        evidence["cost"].update({
            "status": "BLOCK",
            "break_even_preserved": False,
            "worst_stressed_return_pct": -0.5,
        })
        evidence["signal"].update({
            "status": "MISMATCH",
            "blockers": ["strategy_signal_implementation_fingerprint_changed"],
        })

        result = self._build(evidence)

        self.assertEqual(result["status"], "TRIGGERED")
        self.assertEqual(result["observed"], [
            "parameter_plateau_not_preserved",
            "cost_stress_break_even_not_preserved",
            "strategy_signal_implementation_changed",
        ])
        self.assertNotIn(
            "parameter_stability_peak_without_adjacent_plateau",
            result["observed"],
        )
        self.assertEqual(
            result["conditions"][0]["blockers"],
            ["parameter_stability_peak_without_adjacent_plateau"],
        )

    def test_inconsistent_pass_claims_fail_closed_as_observed_conditions(self) -> None:
        evidence = self._evidence()
        evidence["parameter"]["plateau_width"] = 1
        evidence["cost"]["worst_stressed_return_pct"] = 0.0
        evidence["time"]["positive_fold_count"] = 0

        result = self._build(evidence)

        self.assertEqual(result["status"], "TRIGGERED")
        self.assertEqual(result["observed"], [
            "parameter_plateau_not_preserved",
            "cost_stress_break_even_not_preserved",
            "fixed_parameter_time_slice_robustness_not_preserved",
        ])

    def test_missing_strategy_never_borrows_another_strategy_failure_contract(self) -> None:
        result = self._build(self._evidence(), strategy_id="")

        self.assertEqual(result["status"], "NOT_IN_REPORT")
        self.assertEqual(result["conditions"], [])
        self.assertEqual(result["observed"], ["strategy_not_in_frozen_research_report"])
        self.assertIn(
            "strategy_specific_parameter_cost_and_time_evidence_missing",
            result["evidence_gaps"],
        )
        self.assertFalse(result["parameter_selection_allowed"])

    def test_v2_maps_replay_pass_block_and_not_run_without_changing_v1(self) -> None:
        evidence = self._evidence()
        common = {
            "strategy_id": "dual_ma",
            "parameter_stability": evidence["parameter"],
            "cost_sensitivity": evidence["cost"],
            "chronological_slices": evidence["time"],
            "implementation_currentness": evidence["signal"],
            "full_implementation_currentness": evidence["full"],
        }
        legacy = build_strategy_research_failure_conditions(**common)
        result = build_strategy_research_failure_conditions_v2(
            **common,
            post_selection_replay_summary={
                "frozen_test": {"status": "PASS", "blockers": []},
                "holdout_confirmation": {
                    "status": "BLOCK",
                    "blockers": ["post_selection_replay_outcome_not_preserved"],
                },
            },
        )

        self.assertEqual(legacy["schema_version"], "strategy-research-failure-conditions-v1")
        self.assertEqual(result["schema_version"], "strategy-research-failure-conditions-v2")
        replay_conditions = result["conditions"][-2:]
        self.assertEqual(
            [item["condition_id"] for item in replay_conditions],
            [
                "frozen_test_replay_not_preserved",
                "holdout_confirmation_replay_not_preserved",
            ],
        )
        self.assertEqual([item["triggered"] for item in replay_conditions], [False, True])
        self.assertIn("holdout_confirmation_replay_not_preserved", result["observed"])

        not_run = build_strategy_research_failure_conditions_v2(
            **common,
            post_selection_replay_summary={
                "frozen_test": {"status": "NOT_RUN", "blockers": []},
                "holdout_confirmation": {"status": "NOT_RUN", "blockers": []},
            },
        )
        self.assertIsNone(not_run["conditions"][-2]["triggered"])
        self.assertIn(
            "frozen_test_replay_not_preserved_not_checked",
            not_run["evidence_gaps"],
        )

    def test_v3_maps_mechanism_trigger_and_gap_and_never_promotes_not_due(self) -> None:
        evidence = self._evidence()
        common = {
            "strategy_id": "dual_ma",
            "parameter_stability": evidence["parameter"],
            "cost_sensitivity": evidence["cost"],
            "chronological_slices": evidence["time"],
            "implementation_currentness": evidence["signal"],
            "full_implementation_currentness": evidence["full"],
            "post_selection_replay_summary": {
                "frozen_test": {"status": "PASS", "blockers": []},
                "holdout_confirmation": {"status": "PASS", "blockers": []},
            },
        }

        result = build_strategy_research_failure_conditions_v3(
            **common,
            preregistered_failure_admission={
                "status": "BLOCK",
                "blockers": ["preregistered_failure_admission_blocked"],
                "checks": [
                    {
                        "condition_kind": "MECHANISM_SPECIFIC",
                        "condition_id": "validation_edge_lost",
                        "status": "BLOCK",
                        "triggered": True,
                        "blockers": ["mechanism_condition_triggered"],
                    },
                    {
                        "condition_kind": "MECHANISM_SPECIFIC",
                        "condition_id": "validation_drawdown_unknown",
                        "status": "BLOCK",
                        "triggered": None,
                        "blockers": ["mechanism_condition_unresolved"],
                    },
                ],
                "future_standard_checks": [
                    {
                        "condition_id": "fresh_single_use_holdout_failure",
                        "status": "NOT_DUE",
                        "triggered": False,
                        "blockers": [],
                    },
                ],
            },
        )

        self.assertEqual(
            result["schema_version"],
            "strategy-research-failure-conditions-v3",
        )
        self.assertIn(
            "mechanism_failure:validation_edge_lost",
            result["observed"],
        )
        self.assertIn(
            "mechanism_failure:validation_drawdown_unknown_not_checked",
            result["evidence_gaps"],
        )
        self.assertIn(
            "future_standard_failure:fresh_single_use_holdout_failure_not_checked",
            result["evidence_gaps"],
        )
        not_due = next(
            row for row in result["conditions"]
            if row["condition_id"]
            == "future_standard_failure:fresh_single_use_holdout_failure"
        )
        self.assertIsNone(not_due["triggered"])
        self.assertFalse(result["profitability_proven"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_v4_adds_live_at_selection_condition_without_changing_v3(self) -> None:
        evidence = self._evidence()
        common = {
            "strategy_id": "dual_ma",
            "parameter_stability": evidence["parameter"],
            "cost_sensitivity": evidence["cost"],
            "chronological_slices": evidence["time"],
            "implementation_currentness": evidence["signal"],
            "full_implementation_currentness": evidence["full"],
            "post_selection_replay_summary": {
                "frozen_test": {"status": "NOT_RUN", "blockers": []},
                "holdout_confirmation": {"status": "NOT_RUN", "blockers": []},
            },
            "preregistered_failure_admission": {
                "status": "PASS",
                "blockers": [],
                "checks": [],
                "future_standard_checks": [],
            },
        }
        legacy_v3 = build_strategy_research_failure_conditions_v3(**common)
        bound = build_strategy_research_failure_conditions_v4(
            **common,
            search_lineage={"status": "BOUND", "blockers": []},
        )

        self.assertEqual(
            legacy_v3["schema_version"],
            "strategy-research-failure-conditions-v3",
        )
        self.assertNotIn("search_lineage_status", legacy_v3)
        self.assertEqual(
            bound["schema_version"],
            "strategy-research-failure-conditions-v4",
        )
        self.assertEqual(bound["search_lineage_status"], "BOUND")
        lineage_condition = bound["conditions"][-1]
        self.assertEqual(
            lineage_condition["condition_id"],
            "search_lineage_live_at_selection_not_verified",
        )
        self.assertIs(lineage_condition["triggered"], False)
        self.assertNotIn(lineage_condition["condition_id"], bound["observed"])

    def test_v4_receipt_only_is_triggered_and_missing_lineage_is_a_gap(self) -> None:
        evidence = self._evidence()
        common = {
            "strategy_id": "dual_ma",
            "parameter_stability": evidence["parameter"],
            "cost_sensitivity": evidence["cost"],
            "chronological_slices": evidence["time"],
            "implementation_currentness": evidence["signal"],
            "full_implementation_currentness": evidence["full"],
            "post_selection_replay_summary": {
                "frozen_test": {"status": "NOT_RUN", "blockers": []},
                "holdout_confirmation": {"status": "NOT_RUN", "blockers": []},
            },
            "preregistered_failure_admission": {
                "status": "BLOCK",
                "blockers": ["preregistered_failure_admission_blocked"],
                "checks": [],
                "future_standard_checks": [],
            },
        }
        receipt_only = build_strategy_research_failure_conditions_v4(
            **common,
            search_lineage={
                "status": "BLOCK",
                "blockers": [
                    "strategy_search_lineage_live_registry_verification_required"
                ],
            },
        )
        missing = build_strategy_research_failure_conditions_v4(
            **common,
            search_lineage=None,
        )

        condition_id = "search_lineage_live_at_selection_not_verified"
        self.assertEqual(receipt_only["status"], "TRIGGERED")
        self.assertIn(condition_id, receipt_only["observed"])
        self.assertEqual(
            receipt_only["conditions"][-1]["blockers"],
            ["strategy_search_lineage_live_registry_verification_required"],
        )
        self.assertIsNone(missing["conditions"][-1]["triggered"])
        self.assertIn(f"{condition_id}_not_checked", missing["evidence_gaps"])

    def test_v4_missing_strategy_isolated_view_has_no_lineage_condition(self) -> None:
        evidence = self._evidence()
        result = build_strategy_research_failure_conditions_v4(
            strategy_id="",
            parameter_stability=evidence["parameter"],
            cost_sensitivity=evidence["cost"],
            chronological_slices=evidence["time"],
            implementation_currentness=evidence["signal"],
            full_implementation_currentness=evidence["full"],
            post_selection_replay_summary=None,
            preregistered_failure_admission={"status": "NOT_IN_REPORT"},
            search_lineage={"status": "NOT_IN_REPORT"},
        )

        self.assertEqual(result["status"], "NOT_IN_REPORT")
        self.assertEqual(result["search_lineage_status"], "NOT_IN_REPORT")
        self.assertEqual(result["conditions"], [])


if __name__ == "__main__":
    unittest.main()
