from __future__ import annotations

import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_research_pointer as pointer_module
from exchange_terminal.services.implementation_manifest import build_implementation_manifest
from exchange_terminal.services.strategy_research_pointer import (
    DEFAULT_STRATEGY_RESEARCH_POINTER_FILE,
    build_strategy_research_pointer_publication_expectation,
    load_strategy_research_evidence_snapshot,
    publish_strategy_research_report_pointer,
    strategy_research_pointer_publication_eligibility,
    verify_strategy_research_pointer_publication_receipt,
)
from exchange_terminal.services.strategy_hypothesis_preregistration import (
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    build_strategy_hypothesis_preregistration,
)
from exchange_terminal.services.strategy_frozen_evaluation_replay import (
    FROZEN_TEST_ROLE,
    HOLDOUT_CONFIRMATION_ROLE,
    STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_research import (
    aggregate_frozen_test,
    aggregate_holdout_confirmation,
)
from exchange_terminal.services.strategy_research_search_lineage import (
    build_strategy_research_search_lineage,
)


class StrategyResearchPointerTests(unittest.TestCase):
    @staticmethod
    def _post_selection_replay(role: str) -> dict[str, object]:
        holdout = role == HOLDOUT_CONFIRMATION_ROLE
        return {
            "schema_version": STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION,
            "role": role,
            "verification_status": "PASS",
            "status": "PASS",
            "configured_run": {"result_projection": {
                "ok": True,
                "total_return_pct": 4.0,
                "max_drawdown_pct": 5.0,
                "trade_count": 3,
            }},
            "severe_cost_run": {"result_projection": {
                "ok": True,
                "total_return_pct": 1.0,
                "max_drawdown_pct": 6.0,
                "trade_count": 3,
            }},
            "flat_metric_projection": {"test_excess_return_pct": 2.0},
            "fixed_slice_evidence": {"status": "PASS"} if holdout else None,
            "prefix_invariance": {"status": "PASS"} if holdout else None,
            "lookahead": {"status": "PASS"} if holdout else None,
            "historical_backtest_only": True,
            "profitability_proven": False,
            "parameter_selection_authority": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    @classmethod
    def _with_post_selection_replay(cls, report: dict[str, object]) -> dict[str, object]:
        candidate = {
            "strategy_id": "dual_ma",
            "variant_id": "private-pointer-variant",
            "params": {"fast": 8, "slow": 24},
            "param_hash": "a" * 64,
            "implementation_fingerprint": "d" * 64,
            "selection_lane": "RAW_EXCESS",
            "frozen_before_test": True,
        }
        test_cell = {
            "phase": FROZEN_TEST_ROLE,
            "symbol": "BTC-USDT",
            "strategy_id": "dual_ma",
            "variant_id": candidate["variant_id"],
            "dataset_status": "PASS",
            "test_ok": True,
            "test_return_pct": 4.0,
            "test_excess_return_pct": 2.0,
            "test_trade_count": 3,
            "test_max_drawdown_pct": 5.0,
            "test_cost_status": "PASS",
            "frozen_evaluation_replay": cls._post_selection_replay(FROZEN_TEST_ROLE),
        }
        test_result = aggregate_frozen_test(candidate, [test_cell], required_symbols=1)
        holdout_cell = {
            **test_cell,
            "phase": HOLDOUT_CONFIRMATION_ROLE,
            "symbol": "ETH-USDT",
            "baseline_ok": True,
            "cost_sensitivity_status": "PASS",
            "temporal_status": "PASS",
            "walk_forward_status": "PASS",
            "lookahead_status": "PASS",
            "frozen_evaluation_replay": cls._post_selection_replay(
                HOLDOUT_CONFIRMATION_ROLE
            ),
        }
        holdout_result = aggregate_holdout_confirmation(
            test_result,
            [holdout_cell],
            required_symbols=1,
        )
        holdout_result.update({
            "variant_id": candidate["variant_id"],
            "params": candidate["params"],
            "param_hash": candidate["param_hash"],
        })
        report["batch_spec"]["selection_symbols"] = ["BTC-USDT"]
        report["batch_spec"]["confirmation_symbols"] = ["ETH-USDT"]
        report["frozen_candidates"] = [candidate]
        report["test_cells"] = [test_cell]
        report["test_results"] = [test_result]
        report["holdout_cells"] = [holdout_cell]
        report["holdout_results"] = [holdout_result]
        return report

    @staticmethod
    def _hypothesis() -> dict[str, object]:
        return build_strategy_hypothesis_preregistration({
            "schema_version": STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
            "hypothesis_id": "pointer-causal-persistence-v1",
            "research_generation": "POINTER_CONTRACT_TEST",
            "strategy_ids": ["dual_ma"],
            "mechanism_family": "causal moving-average persistence confirmation",
            "hypothesis_statement": (
                "Completed-bar persistence should retain positive benchmark excess "
                "after configured and stressed transaction costs."
            ),
            "novelty_statement": (
                "This mechanism does not reuse or retune the falsified pullback "
                "and squeeze entry families."
            ),
            "mechanism_specific_failure_conditions": [
                "Retire this hypothesis when fresh excess is not positive after stressed costs."
            ],
        })

    @staticmethod
    def _hypothesis_v2() -> dict[str, object]:
        return build_strategy_hypothesis_preregistration({
            "schema_version": STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
            "hypothesis_id": "pointer-causal-persistence-v2",
            "research_generation": "POINTER_CONTRACT_TEST",
            "strategy_ids": ["dual_ma"],
            "mechanism_family": "causal moving-average persistence confirmation",
            "hypothesis_statement": (
                "Completed-bar persistence should retain positive benchmark excess "
                "after configured and stressed transaction costs; private/path and "
                "BTC-USDT remain non-public research detail."
            ),
            "novelty_statement": (
                "This mechanism does not reuse or retune the falsified pullback "
                "and squeeze entry families; must-not-leak-schema13-text."
            ),
            "mechanism_specific_failure_conditions": [{
                "condition_id": "validation_edge_lost",
                "evidence_stage": "DEVELOPMENT_SELECTION",
                "metric": "median_validation_excess_return_pct",
                "operator": "LTE",
                "threshold": 0.0,
                "required_action": "BLOCK_RESEARCH",
            }],
        })

    @staticmethod
    def _hypothesis_v3() -> dict[str, object]:
        return build_strategy_hypothesis_preregistration({
            "schema_version": STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
            "hypothesis_id": "pointer-causal-persistence-v3",
            "research_generation": "POINTER_CONTRACT_TEST",
            "search_family_id": "causal-trend-global-search",
            "strategy_ids": ["dual_ma"],
            "mechanism_family": "causal moving-average persistence confirmation",
            "hypothesis_statement": (
                "Completed-bar persistence should retain positive benchmark excess "
                "after configured and stressed transaction costs; private/path and "
                "BTC-USDT remain non-public research detail."
            ),
            "novelty_statement": (
                "This mechanism does not reuse or retune the falsified pullback "
                "and squeeze entry families; must-not-leak-schema14-text."
            ),
            "mechanism_specific_failure_conditions": [{
                "condition_id": "validation_edge_lost",
                "evidence_stage": "DEVELOPMENT_SELECTION",
                "metric": "median_validation_excess_return_pct",
                "operator": "LTE",
                "threshold": 0.0,
                "required_action": "BLOCK_RESEARCH",
            }],
        })

    @staticmethod
    def _report() -> dict[str, object]:
        return {
            "schema_version": 5,
            "created_at": "2026-08-12T02:03:04+00:00",
            "batch_spec": {
                "strategies": ["dual_ma"],
                "selection_test_policy": "DEVELOPMENT_ONLY",
                "research_generation": "POINTER_CONTRACT_TEST",
                "variants": [
                    {
                        "strategy_id": "dual_ma",
                        "variant_id": "dual_ma:fast",
                        "params": {"fast": 8, "slow": 24},
                        "implementation_fingerprint": "d" * 64,
                    },
                    {
                        "strategy_id": "dual_ma",
                        "variant_id": "dual_ma:balanced",
                        "params": {"fast": 12, "slow": 36},
                        "implementation_fingerprint": "d" * 64,
                    },
                    {
                        "strategy_id": "dual_ma",
                        "variant_id": "dual_ma:slow",
                        "params": {"fast": 20, "slow": 60},
                        "implementation_fingerprint": "d" * 64,
                    },
                ],
            },
            "batch_spec_hash": "a" * 64,
            "dataset_manifest_hash": "b" * 64,
            "batch_run_hash": "c" * 64,
            "selection_alignment": {
                "status": "PASS",
                "common_as_of": "2026-08-10",
            },
            "summary": {
                "strategies": 1,
                "parameter_variants": 3,
                "selection_symbols": 2,
                "selection_cells": 2,
                "frozen_test_candidates": 0,
                "test_cells": 0,
                "forward_candidates": 0,
                "common_as_of": "2026-08-10",
            },
            "research_governance": {
                "status": "DEVELOPMENT_SELECTION_ONLY",
                "paper_authorized": False,
                "live_order_allowed": False,
            },
            "parameter_stability": {
                "schema_version": "strategy-parameter-plateau-v2",
                "topology_basis": "FROZEN_VARIANT_SEQUENCE_ADJACENCY",
                "numeric_parameter_distance_checked": False,
                "strategies": [
                    {
                        "strategy_id": "dual_ma",
                        "status": "PASS",
                        "frozen_variant_count": 3,
                        "eligible_variant_count": 2,
                        "near_best_eligible_variant_count": 2,
                        "adjacent_near_best_variant_count": 1,
                        "plateau_width": 2,
                        "best_adjusted_score": 4.25,
                        "best_variant_id": "must-not-leak",
                        "params": {"fast": 10, "slow": 30},
                        "peak_only": False,
                        "blockers": [],
                    }
                ],
                "parameter_selection_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
            "selection_cells": [
                {
                    "strategy_id": "dual_ma",
                    "cost_sensitivity_status": "PASS",
                    "cost_sensitivity": {
                        "worst_return_pct": 1.25,
                        "worst_drawdown_pct": 7.5,
                        "break_even_preserved": True,
                        "blockers": [],
                    },
                    "fold_stability_status": "PASS",
                    "fold_stability": {
                        "evaluation_mode": "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
                        "usable_folds": 3,
                        "positive_folds": 2,
                        "worst_drawdown_pct": 6.0,
                        "parameters_refit_per_fold": False,
                        "walk_forward_optimization_claim_allowed": False,
                        "blockers": [],
                    },
                    "private_debug_path": "must-not-leak",
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            ],
            "summary": {
                "strategies": 1,
                "parameter_variants": 3,
                "selection_symbols": 1,
                "selection_cells": 1,
                "frozen_test_candidates": 0,
                "test_cells": 0,
                "forward_candidates": 0,
            },
            "unknown_private_marker": "must-not-leak",
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    @classmethod
    def _schema13_report(cls) -> dict[str, object]:
        report = cls._report()
        hypothesis = cls._hypothesis_v2()
        report["schema_version"] = 13
        report["batch_spec"]["report_schema_version"] = 13
        report["batch_spec"]["hypothesis_preregistration"] = hypothesis
        report["batch_spec"]["hypothesis_preregistration_hash"] = hypothesis[
            "hypothesis_hash"
        ]
        report.update({
            "frozen_candidates": [],
            "test_cells": [],
            "test_results": [],
            "holdout_cells": [],
            "holdout_results": [],
        })
        report["preregistered_failure_admission"] = {
            "schema_version": "strategy-preregistered-failure-admission-v2",
            "status": "BLOCK",
            "admission_scope": "HYPOTHESIS_BATCH",
            "hypothesis_id": "pointer-causal-persistence-v2",
            "strategies": [{
                "strategy_id": "dual_ma",
                "status": "BLOCK",
                "candidate_variant_ids": ["must-not-leak-schema13-variant"],
                "admitted_variant_ids": [],
                "checks": [{
                    "condition_id": "validation_edge_lost",
                    "condition_kind": "MECHANISM_SPECIFIC",
                    "evidence_stage": "DEVELOPMENT_SELECTION",
                    "metric": "median_validation_excess_return_pct",
                    "operator": "LTE",
                    "threshold": 0.0,
                    "required_action": "BLOCK_RESEARCH",
                    "status": "BLOCK",
                    "triggered": True,
                    "metric_value": -0.25,
                    "blockers": [
                        "dual_ma:BTC-USDT:must-not-leak-schema13-variant:private/path"
                    ],
                }],
                "blockers": ["must-not-leak-strategy-blocker"],
            }],
            "mechanism_condition_ids": ["validation_edge_lost"],
            "future_standard_checks": [
                {
                    "condition_id": "fresh_single_use_holdout_failure",
                    "condition_kind": "STANDARD",
                    "evidence_stage": "PREREGISTERED_BLIND_SINGLE_USE",
                    "required_action": "RETIRE_OR_NEW_REGISTRATION",
                    "status": "NOT_DUE",
                    "triggered": False,
                    "blockers": [],
                },
                {
                    "condition_id": "natural_forward_statistical_failure",
                    "condition_kind": "STANDARD",
                    "evidence_stage": "NATURAL_FORWARD_MATURITY",
                    "required_action": "RETIRE_HYPOTHESIS",
                    "status": "NOT_DUE",
                    "triggered": False,
                    "blockers": [],
                },
            ],
            "admitted_variant_ids": [],
            "blockers": [
                "dual_ma:mechanism_condition_triggered:validation_edge_lost"
            ],
            "admission_hash": "f" * 64,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        return report

    @classmethod
    def _schema14_report(cls, *, receipt_only: bool = False) -> dict[str, object]:
        report = cls._schema13_report()
        hypothesis = cls._hypothesis_v3()
        variants = report["batch_spec"]["variants"]
        lineage = build_strategy_research_search_lineage(
            search_family_id=hypothesis["search_family_id"],
            prior_registrations=[{
                "registration_id": "private-prior-registration",
                "protocol_hash": "1" * 64,
                "registered_event_hash": "2" * 64,
                "search_family_id": hypothesis["search_family_id"],
                "report_schema_version": 14,
                "lineage_mode": "BOUND",
                "current_trial_count": 5,
                "cumulative_trial_count": 5,
            }],
            current_trial_count=len(variants),
        )
        report["schema_version"] = 14
        report["batch_spec"]["report_schema_version"] = 14
        report["batch_spec"]["hypothesis_preregistration"] = hypothesis
        report["batch_spec"]["hypothesis_preregistration_hash"] = hypothesis[
            "hypothesis_hash"
        ]
        report["batch_spec"]["search_lineage"] = lineage
        admission = report["preregistered_failure_admission"]
        admission["schema_version"] = "strategy-preregistered-failure-admission-v3"
        admission["hypothesis_id"] = hypothesis["hypothesis_id"]
        admission["search_lineage_binding"] = {
            "report_schema_version": 14,
            "status": "PASS",
            "lineage_hash": lineage["lineage_hash"],
            "search_family_id": lineage["search_family_id"],
            "trial_count_scope": lineage["trial_count_scope"],
            "current_trial_count": lineage["current_trial_count"],
            "cumulative_trial_count": lineage["cumulative_trial_count"],
            "derived_before_selection": True,
            "blockers": [],
        }
        admission["registration_binding"] = {
            "status": (
                "SELF_CONSISTENT_RECEIPT"
                if receipt_only
                else "LIVE_REGISTRY_VERIFIED"
            ),
            "verification_scope": (
                "SELF_CONSISTENT_RECEIPT_ONLY"
                if receipt_only
                else "LIVE_REGISTRY_AUDIT_AND_PREREGISTRATION_RECEIPT"
            ),
            "registration_id": "private-current-registration",
            "protocol_hash": "3" * 64,
            "claim_hash": "4" * 64,
            "registry_anchor_hash": "5" * 64,
            "registry_status": "RUNNING",
            "registry_audit_status": "PASS",
            "blockers": [],
        }
        if receipt_only:
            admission["status"] = "BLOCK"
            admission["admitted_variant_ids"] = []
            for strategy in admission["strategies"]:
                strategy["status"] = "BLOCK"
                strategy["admitted_variant_ids"] = []
            admission["blockers"] = list(dict.fromkeys([
                *admission["blockers"],
                "strategy_search_lineage_live_registry_verification_required",
            ]))
        return report

    @classmethod
    def _schema12_pass_report(cls) -> dict[str, object]:
        report = cls._report()
        hypothesis = cls._hypothesis()
        report["schema_version"] = 12
        report["batch_spec"]["report_schema_version"] = 12
        report["batch_spec"]["selection_test_policy"] = "BLIND_ONCE"
        report["batch_spec"]["hypothesis_preregistration"] = hypothesis
        report["batch_spec"]["hypothesis_preregistration_hash"] = hypothesis[
            "hypothesis_hash"
        ]
        report = cls._with_post_selection_replay(report)
        report["summary"].update({
            "frozen_test_candidates": 1,
            "test_cells": 1,
            "forward_candidates": 1,
        })
        report["preregistered_failure_admission"] = {
            "schema_version": "strategy-preregistered-failure-admission-v1",
            "status": "PASS",
            "admission_scope": "HYPOTHESIS_BATCH",
            "hypothesis_id": "pointer-causal-persistence-v1",
            "strategies": [{
                "strategy_id": "dual_ma",
                "status": "PASS",
                "candidate_variant_ids": ["private-pointer-variant"],
                "admitted_variant_ids": ["private-pointer-variant"],
                "checks": [
                    {
                        "condition_id": "parameter_plateau_absent",
                        "status": "PASS",
                        "triggered": False,
                        "blockers": [],
                    },
                    {
                        "condition_id": "cost_break_even_lost",
                        "status": "PASS",
                        "triggered": False,
                        "blockers": [],
                    },
                    {
                        "condition_id": "fixed_parameter_time_slice_instability",
                        "status": "PASS",
                        "triggered": False,
                        "blockers": [],
                    },
                ],
                "blockers": [],
            }],
            "admitted_variant_ids": ["private-pointer-variant"],
            "blockers": [],
        }
        return report

    @staticmethod
    def _verification() -> dict[str, object]:
        return {
            "status": "PASS",
            "blockers": [],
            "formal_single_use": False,
        }

    @staticmethod
    def _write(path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _publish(report_dir: Path, report_path: Path) -> dict[str, object]:
        raw = report_path.read_bytes()
        report = json.loads(raw.decode("utf-8"))
        expectation = build_strategy_research_pointer_publication_expectation(
            report,
            report_file=report_path.name,
            report_file_bytes=raw,
        )
        return publish_strategy_research_report_pointer(
            report_dir,
            report_path,
            expectation=expectation,
        )

    def test_publish_and_load_projects_only_verified_descriptive_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_20260812.json"
            self._write(report_path, self._report())

            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                published = self._publish(report_dir, report_path)
                snapshot = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
                    observed_at_ms=1786507384000,
                )

            self.assertEqual(published["status"], "PUBLISHED")
            pointer_path = report_dir / DEFAULT_STRATEGY_RESEARCH_POINTER_FILE
            self.assertTrue(pointer_path.is_file())
            pointer_payload = json.loads(pointer_path.read_text(encoding="utf-8"))
            self.assertEqual(set(pointer_payload), pointer_module._POINTER_FIELDS)
            self.assertEqual(
                pointer_payload["schema_version"],
                "strategy-research-report-pointer-v1",
            )
            self.assertNotIn(
                "preregistered_failure_admission_status",
                pointer_payload,
            )
            self.assertNotIn("post_selection_replay_status", pointer_payload)
            self.assertNotIn("post_selection_replay_summary", pointer_payload)
            self.assertTrue(snapshot["ok"])
            self.assertEqual(snapshot["source_verification_status"], "PASS")
            self.assertEqual(
                snapshot["evidence_contract"]["schema_version"],
                "strategy-lab-frozen-evidence-v3",
            )
            self.assertNotIn("preregistered_failure_admission", snapshot)
            self.assertNotIn(
                "preregistered_failure_admission_status",
                snapshot["evidence_contract"],
            )
            self.assertEqual(snapshot["strategy_match_status"], "MATCHED")
            self.assertEqual(snapshot["selected_strategy_id"], "dual_ma")
            self.assertEqual(snapshot["parameter_stability"]["status"], "PASS")
            self.assertEqual(
                snapshot["hypothesis_preregistration"]["status"],
                "LEGACY_NOT_BOUND",
            )
            self.assertEqual(snapshot["parameter_stability"]["plateau_width"], 2)
            self.assertEqual(snapshot["cost_sensitivity"]["worst_stressed_return_pct"], 1.25)
            self.assertEqual(
                snapshot["chronological_slices"]["evaluation_mode"],
                "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
            )
            self.assertFalse(
                snapshot["chronological_slices"]["walk_forward_optimization_claim_allowed"]
            )
            self.assertFalse(snapshot["parameter_selection_allowed"])
            self.assertFalse(snapshot["profitability_proven"])
            self.assertTrue(snapshot["implementation_currentness_checked"])
            self.assertEqual(snapshot["implementation_currentness_status"], "MATCH")
            self.assertTrue(snapshot["implementation_currentness_match"])
            self.assertFalse(snapshot["full_implementation_manifest_checked"])
            self.assertFalse(snapshot["dataset_currentness_checked"])
            self.assertFalse(snapshot["report_age_policy_checked"])
            self.assertEqual(snapshot["currentness_facts"]["status"], "FACTS_AVAILABLE")
            self.assertEqual(snapshot["currentness_facts"]["report_age_ms"], 7_200_000)
            self.assertEqual(snapshot["currentness_facts"]["dataset_as_of"], "2026-08-10")
            self.assertEqual(
                snapshot["currentness_facts"]["calendar_days_since_dataset_as_of"],
                2,
            )
            self.assertFalse(snapshot["currentness_facts"]["threshold_applied"])
            self.assertEqual(
                snapshot["failure_conditions"]["schema_version"],
                "strategy-research-failure-conditions-v1",
            )
            self.assertEqual(snapshot["failure_conditions"]["status"], "GAPS")
            self.assertEqual(snapshot["failure_conditions"]["observed"], [])
            self.assertIn(
                "dataset_currentness_not_checked",
                snapshot["failure_conditions"]["evidence_gaps"],
            )
            self.assertEqual(len(snapshot["failure_conditions"]["conditions"]), 5)
            self.assertFalse(snapshot["paper_authorized"])
            self.assertFalse(snapshot["live_order_allowed"])
            serialized = json.dumps(snapshot, ensure_ascii=False)
            self.assertNotIn("must-not-leak", serialized)
            self.assertNotIn(report_path.name, serialized)
            self.assertNotIn("best_variant_id", serialized)
            self.assertNotIn('"params"', serialized)

    def test_schema9_projects_bound_hypothesis_and_rechecks_nested_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_20260812.json"
            report = self._report()
            hypothesis = self._hypothesis()
            report["schema_version"] = 9
            report["batch_spec"]["report_schema_version"] = 9
            report["batch_spec"]["hypothesis_preregistration"] = hypothesis
            report["batch_spec"]["hypothesis_preregistration_hash"] = hypothesis[
                "hypothesis_hash"
            ]
            self._write(report_path, report)
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                bound = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
                )

                report["batch_spec"]["hypothesis_preregistration"][
                    "cost_and_time_contract"
                ]["stressed_return_must_remain_positive"] = False
                self._write(report_path, report)
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                tampered = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
                )

        summary = bound["hypothesis_preregistration"]
        self.assertEqual(bound["evidence_contract"]["schema_version"], "strategy-lab-frozen-evidence-v3")
        self.assertEqual(summary["status"], "BOUND")
        self.assertTrue(summary["contract_checked"])
        self.assertEqual(summary["hypothesis_id"], "pointer-causal-persistence-v1")
        self.assertEqual(summary["parameter_topology_basis"], "FROZEN_VARIANT_SEQUENCE_ADJACENCY")
        self.assertFalse(summary["numeric_parameter_distance_claimed"])
        self.assertEqual(summary["minimum_natural_forward_outcomes"], 60)
        self.assertEqual(summary["minimum_executed_rebalances"], 8)
        self.assertFalse(summary["paper_authorized"])
        self.assertFalse(summary["live_order_allowed"])
        self.assertEqual(tampered["hypothesis_preregistration"]["status"], "BLOCK")
        self.assertIn(
            "strategy_hypothesis_semantic_or_hash_mismatch",
            tampered["hypothesis_preregistration"]["blockers"],
        )

    def test_schema12_through_7_are_hypothesis_bound_while_schema6_is_legacy(self) -> None:
        hypothesis = self._hypothesis()
        for schema_version, expected_status in (
            (12, "BOUND"),
            (11, "BOUND"),
            (10, "BOUND"),
            (9, "BOUND"),
            (8, "BOUND"),
            (7, "BOUND"),
            (6, "LEGACY_NOT_BOUND"),
        ):
            with self.subTest(schema_version=schema_version):
                report = self._report()
                report["schema_version"] = schema_version
                report["batch_spec"]["report_schema_version"] = schema_version
                if schema_version in {7, 8, 9, 10, 11, 12}:
                    report["batch_spec"]["hypothesis_preregistration"] = hypothesis
                    report["batch_spec"]["hypothesis_preregistration_hash"] = hypothesis[
                        "hypothesis_hash"
                    ]
                projected = pointer_module._hypothesis_projection(report, "dual_ma")
                self.assertEqual(projected["status"], expected_status)

    def test_schema12_projects_admission_and_replay_summary_in_v5_without_candidate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_schema12.json"
            report = self._report()
            hypothesis = self._hypothesis()
            report["schema_version"] = 12
            report["batch_spec"]["report_schema_version"] = 12
            report["batch_spec"]["hypothesis_preregistration"] = hypothesis
            report["batch_spec"]["hypothesis_preregistration_hash"] = hypothesis[
                "hypothesis_hash"
            ]
            report.update({
                "frozen_candidates": [],
                "test_cells": [],
                "test_results": [],
                "holdout_cells": [],
                "holdout_results": [],
            })
            report["preregistered_failure_admission"] = {
                "schema_version": "strategy-preregistered-failure-admission-v1",
                "status": "BLOCK",
                "admission_scope": "HYPOTHESIS_BATCH",
                "hypothesis_id": "pointer-causal-persistence-v1",
                "strategies": [{
                    "strategy_id": "dual_ma",
                    "status": "BLOCK",
                    "candidate_variant_ids": ["must-not-leak-candidate"],
                    "admitted_variant_ids": [],
                    "checks": [{
                        "condition_id": "parameter_plateau_absent",
                        "status": "BLOCK",
                        "triggered": True,
                        "blockers": ["parameter_stability_peak_without_adjacent_plateau"],
                    }],
                }],
                "admitted_variant_ids": [],
                "blockers": [
                    "dual_ma:parameter_stability_peak_without_adjacent_plateau"
                ],
            }
            self._write(report_path, report)
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                snapshot = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
                )

        self.assertEqual(
            snapshot["evidence_contract"]["schema_version"],
            "strategy-lab-frozen-evidence-v5",
        )
        self.assertEqual(snapshot["post_selection_replay_status"], "NOT_RUN")
        self.assertEqual(
            snapshot["evidence_contract"]["post_selection_replay_status"],
            "NOT_RUN",
        )
        self.assertEqual(
            snapshot["post_selection_replay_summary"]["schema_version"],
            "strategy-post-selection-replay-summary-v1",
        )
        self.assertEqual(
            snapshot["failure_conditions"]["schema_version"],
            "strategy-research-failure-conditions-v2",
        )
        self.assertEqual(snapshot["preregistered_failure_admission_status"], "BLOCK")
        self.assertEqual(
            snapshot["evidence_contract"][
                "preregistered_failure_admission_status"
            ],
            "BLOCK",
        )
        projected = snapshot["preregistered_failure_admission"]
        self.assertEqual(projected["selected_strategy_candidate_count"], 1)
        self.assertEqual(projected["admitted_candidate_count"], 0)
        self.assertEqual(projected["checks"][0]["status"], "BLOCK")
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("must-not-leak-candidate", serialized)

    def test_schema12_missing_strategy_cannot_borrow_other_strategy_pass_admission(self) -> None:
        report = self._schema12_pass_report()
        pointer = pointer_module._build_pointer("frozen.json", "f" * 64, report)
        verification = {**self._verification(), "formal_single_use": True}

        snapshot = pointer_module._evidence_projection(
            report,
            pointer,
            verification,
            requested_strategy_id="missing_strategy",
            implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
            observed_at_ms=None,
        )

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["strategy_match_status"], "NOT_IN_REPORT")
        self.assertIsNone(snapshot["selected_strategy_id"])
        admission = snapshot["preregistered_failure_admission"]
        self.assertEqual(snapshot["preregistered_failure_admission_status"], "NOT_IN_REPORT")
        self.assertEqual(
            snapshot["evidence_contract"]["preregistered_failure_admission_status"],
            "NOT_IN_REPORT",
        )
        self.assertEqual(admission["schema_version"], "strategy-preregistered-failure-admission-v1")
        self.assertEqual(admission["status"], "NOT_IN_REPORT")
        self.assertEqual(admission["selected_strategy_status"], "NOT_IN_REPORT")
        self.assertIsNone(admission["hypothesis_id"])
        self.assertEqual(admission["selected_strategy_candidate_count"], 0)
        self.assertEqual(admission["selected_strategy_admitted_count"], 0)
        self.assertEqual(admission["admitted_candidate_count"], 0)
        self.assertEqual(admission["checks"], [])
        self.assertEqual(
            admission["blockers"],
            ["strategy_not_in_frozen_research_report"],
        )
        replay = snapshot["post_selection_replay_summary"]
        self.assertEqual(snapshot["post_selection_replay_status"], "NOT_RUN")
        self.assertEqual(replay["status"], "NOT_RUN")
        self.assertEqual(replay["frozen_test"]["status"], "NOT_RUN")
        self.assertEqual(replay["holdout_confirmation"]["status"], "NOT_RUN")
        for stage in (replay["frozen_test"], replay["holdout_confirmation"]):
            self.assertEqual(stage["candidate_count"], 0)
            self.assertIsNone(stage["minimum_configured_return_pct"])
            self.assertIsNone(stage["minimum_excess_return_pct"])
            self.assertIsNone(stage["minimum_severe_cost_return_pct"])
        self.assertEqual(snapshot["failure_conditions"]["status"], "NOT_IN_REPORT")
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("private-pointer-variant", serialized)

    def test_schema12_matched_strategy_retains_historical_pass_admission(self) -> None:
        report = self._schema12_pass_report()
        pointer = pointer_module._build_pointer("frozen.json", "f" * 64, report)
        verification = {**self._verification(), "formal_single_use": True}

        snapshot = pointer_module._evidence_projection(
            report,
            pointer,
            verification,
            requested_strategy_id="dual_ma",
            implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
            observed_at_ms=None,
        )

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["strategy_match_status"], "MATCHED")
        self.assertEqual(snapshot["selected_strategy_id"], "dual_ma")
        admission = snapshot["preregistered_failure_admission"]
        self.assertEqual(snapshot["preregistered_failure_admission_status"], "PASS")
        self.assertEqual(
            snapshot["evidence_contract"]["preregistered_failure_admission_status"],
            "PASS",
        )
        self.assertEqual(admission["status"], "PASS")
        self.assertEqual(admission["selected_strategy_status"], "PASS")
        self.assertEqual(admission["hypothesis_id"], "pointer-causal-persistence-v1")
        self.assertEqual(admission["selected_strategy_candidate_count"], 1)
        self.assertEqual(admission["selected_strategy_admitted_count"], 1)
        self.assertEqual(admission["admitted_candidate_count"], 1)
        self.assertEqual(len(admission["checks"]), 3)
        self.assertEqual(snapshot["post_selection_replay_status"], "PASS")
        self.assertEqual(snapshot["failure_conditions"]["schema_version"], "strategy-research-failure-conditions-v2")
        self.assertNotIn(
            "private-pointer-variant",
            json.dumps(snapshot, ensure_ascii=False),
        )

    def test_schema11_uses_v5_replay_contract_without_schema12_admission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_schema11.json"
            report = self._report()
            hypothesis = self._hypothesis()
            report["schema_version"] = 11
            report["batch_spec"]["report_schema_version"] = 11
            report["batch_spec"]["hypothesis_preregistration"] = hypothesis
            report["batch_spec"]["hypothesis_preregistration_hash"] = hypothesis[
                "hypothesis_hash"
            ]
            report = self._with_post_selection_replay(report)
            self._write(report_path, report)
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                snapshot = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
                )

        self.assertEqual(
            snapshot["evidence_contract"]["schema_version"],
            "strategy-lab-frozen-evidence-v5",
        )
        self.assertEqual(snapshot["post_selection_replay_status"], "PASS")
        self.assertIn("post_selection_replay_summary", snapshot)
        self.assertEqual(
            snapshot["post_selection_replay_summary"]["frozen_test"][
                "minimum_configured_return_pct"
            ],
            4.0,
        )
        self.assertNotIn("preregistered_failure_admission", snapshot)
        self.assertNotIn(
            "preregistered_failure_admission_status",
            snapshot["evidence_contract"],
        )
        self.assertEqual(
            snapshot["failure_conditions"]["schema_version"],
            "strategy-research-failure-conditions-v2",
        )
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("private-pointer-variant", serialized)
        self.assertNotIn("BTC-USDT", json.dumps(snapshot["post_selection_replay_summary"]))

    def test_schema13_projects_strict_v6_mechanism_admission_without_private_identity(self) -> None:
        report = self._schema13_report()
        pointer = pointer_module._build_pointer("frozen.json", "f" * 64, report)

        snapshot = pointer_module._evidence_projection(
            report,
            pointer,
            self._verification(),
            requested_strategy_id="dual_ma",
            implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
            observed_at_ms=None,
        )

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["pointer_schema_version"], "strategy-research-report-pointer-v1")
        contract = snapshot["evidence_contract"]
        self.assertEqual(contract["schema_version"], "strategy-lab-frozen-evidence-v6")
        self.assertEqual(
            contract["hypothesis_preregistration_schema_version"],
            "strategy-hypothesis-preregistration-v2",
        )
        self.assertEqual(
            contract["preregistered_failure_admission_schema_version"],
            "strategy-preregistered-failure-admission-v2",
        )
        hypothesis = snapshot["hypothesis_preregistration"]
        self.assertEqual(
            hypothesis["schema_version"],
            "strategy-hypothesis-preregistration-summary-v2",
        )
        self.assertEqual(hypothesis["source_schema_version"], "strategy-hypothesis-preregistration-v2")
        self.assertEqual(hypothesis["research_generation"], "POINTER_CONTRACT_TEST")
        self.assertEqual(
            hypothesis["mechanism_family"],
            "causal moving-average persistence confirmation",
        )
        self.assertNotIn("hypothesis_statement", hypothesis)
        self.assertNotIn("novelty_statement", hypothesis)
        self.assertEqual(
            set(hypothesis["mechanism_specific_failure_conditions"][0]),
            {
                "condition_id",
                "evidence_stage",
                "metric",
                "operator",
                "threshold",
                "required_action",
            },
        )
        admission = snapshot["preregistered_failure_admission"]
        self.assertEqual(admission["selected_strategy_candidate_count"], 1)
        self.assertEqual(admission["mechanism_condition_ids"], ["validation_edge_lost"])
        self.assertEqual(admission["checks"][0]["status"], "BLOCK")
        self.assertEqual(admission["checks"][0]["blockers"], ["mechanism_condition_triggered"])
        self.assertEqual(admission["future_standard_checks"][0]["status"], "NOT_DUE")
        failures = snapshot["failure_conditions"]
        self.assertEqual(failures["schema_version"], "strategy-research-failure-conditions-v3")
        self.assertIn("mechanism_failure:validation_edge_lost", failures["observed"])
        self.assertIn(
            "future_standard_failure:fresh_single_use_holdout_failure_not_checked",
            failures["evidence_gaps"],
        )
        self.assertEqual(snapshot["post_selection_replay_status"], "NOT_RUN")
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("must-not-leak", serialized)
        self.assertNotIn("BTC-USDT", serialized)
        self.assertNotIn("private/path", serialized)
        self.assertNotIn('"symbol"', serialized)
        self.assertNotIn('"variant_id"', serialized)

    def test_schema13_invalid_nested_v2_contract_fails_closed_even_if_outer_verifier_passes(self) -> None:
        report = self._schema13_report()
        report["batch_spec"]["hypothesis_preregistration"]["failure_contract"][
            "mechanism_specific_conditions"
        ][0]["metric"] = "private_unlisted_metric"
        pointer = pointer_module._build_pointer("frozen.json", "f" * 64, report)

        snapshot = pointer_module._evidence_projection(
            report,
            pointer,
            self._verification(),
            requested_strategy_id="dual_ma",
            implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
            observed_at_ms=None,
        )

        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["source_verification_status"], "BLOCK")
        self.assertIn(
            "strategy_research_public_capability_contract_invalid",
            snapshot["blockers"],
        )
        self.assertIsNone(snapshot["hypothesis_preregistration"])
        self.assertNotIn("preregistered_failure_admission", snapshot)

    def test_schema13_missing_requested_strategy_returns_isolated_not_in_report_view(self) -> None:
        report = self._schema13_report()
        admission_source = report["preregistered_failure_admission"]
        admission_source["status"] = "PASS"
        admission_source["admitted_variant_ids"] = [
            "must-not-leak-schema13-variant"
        ]
        admission_source["blockers"] = []
        strategy_source = admission_source["strategies"][0]
        strategy_source["status"] = "PASS"
        strategy_source["admitted_variant_ids"] = [
            "must-not-leak-schema13-variant"
        ]
        strategy_source["blockers"] = []
        mechanism_source = strategy_source["checks"][0]
        mechanism_source["status"] = "PASS"
        mechanism_source["triggered"] = False
        mechanism_source["metric_value"] = 0.25
        mechanism_source["blockers"] = []
        pointer = pointer_module._build_pointer("frozen.json", "f" * 64, report)

        snapshot = pointer_module._evidence_projection(
            report,
            pointer,
            self._verification(),
            requested_strategy_id="missing_strategy",
            implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
            observed_at_ms=None,
        )

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["strategy_match_status"], "NOT_IN_REPORT")
        self.assertIsNone(snapshot["selected_strategy_id"])
        hypothesis = snapshot["hypothesis_preregistration"]
        self.assertEqual(hypothesis["status"], "BLOCK")
        self.assertFalse(hypothesis["selected_strategy_match"])
        admission = snapshot["preregistered_failure_admission"]
        self.assertEqual(snapshot["preregistered_failure_admission_status"], "NOT_IN_REPORT")
        self.assertEqual(
            snapshot["evidence_contract"]["preregistered_failure_admission_status"],
            "NOT_IN_REPORT",
        )
        self.assertEqual(admission["status"], "NOT_IN_REPORT")
        self.assertEqual(admission["selected_strategy_status"], "NOT_IN_REPORT")
        self.assertIsNone(admission["hypothesis_id"])
        self.assertEqual(admission["selected_strategy_candidate_count"], 0)
        self.assertEqual(admission["selected_strategy_admitted_count"], 0)
        self.assertEqual(admission["admitted_candidate_count"], 0)
        self.assertEqual(admission["mechanism_condition_ids"], [])
        self.assertEqual(admission["checks"], [])
        self.assertEqual(admission["future_standard_checks"], [])
        replay = snapshot["post_selection_replay_summary"]
        self.assertEqual(replay["status"], "NOT_RUN")
        self.assertEqual(replay["frozen_test"]["status"], "NOT_RUN")
        self.assertEqual(replay["holdout_confirmation"]["status"], "NOT_RUN")
        self.assertEqual(snapshot["failure_conditions"]["status"], "NOT_IN_REPORT")
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("must-not-leak-schema13-variant", serialized)

    def test_schema14_projects_deidentified_live_at_selection_lineage_v7(self) -> None:
        report = self._schema14_report()
        pointer = pointer_module._build_pointer("frozen.json", "f" * 64, report)

        snapshot = pointer_module._evidence_projection(
            report,
            pointer,
            self._verification(),
            requested_strategy_id="dual_ma",
            implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
            observed_at_ms=None,
        )

        self.assertTrue(snapshot["ok"])
        self.assertEqual(
            snapshot["evidence_contract"]["schema_version"],
            "strategy-lab-frozen-evidence-v7",
        )
        lineage = snapshot["search_lineage"]
        self.assertEqual(
            lineage["schema_version"],
            "strategy-research-search-lineage-public-v1",
        )
        self.assertEqual(lineage["status"], "BOUND")
        self.assertTrue(lineage["family_bound"])
        self.assertEqual(
            lineage["trial_count_scope"],
            "GLOBAL_REGISTERED_STRATEGY_RESEARCH",
        )
        self.assertEqual(lineage["prior_trial_count"], 5)
        self.assertEqual(lineage["current_trial_count"], 3)
        self.assertEqual(lineage["cumulative_trial_count"], 8)
        self.assertEqual(
            lineage["selection_binding_scope"],
            "LIVE_REGISTRY_AUDIT_AND_PREREGISTRATION_RECEIPT",
        )
        self.assertEqual(
            lineage["offline_verification_scope"],
            "OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY",
        )
        self.assertEqual(lineage["admission_status"], "BLOCK")
        hypothesis = snapshot["hypothesis_preregistration"]
        self.assertEqual(
            hypothesis["schema_version"],
            "strategy-hypothesis-preregistration-summary-v3",
        )
        self.assertTrue(hypothesis["search_family_bound"])
        admission = snapshot["preregistered_failure_admission"]
        self.assertEqual(
            admission["schema_version"],
            "strategy-preregistered-failure-admission-v3",
        )
        self.assertEqual(admission["search_lineage_status"], "BOUND")
        failures = snapshot["failure_conditions"]
        self.assertEqual(
            failures["schema_version"],
            "strategy-research-failure-conditions-v4",
        )
        lineage_condition = next(
            row for row in failures["conditions"]
            if row["condition_id"]
            == "search_lineage_live_at_selection_not_verified"
        )
        self.assertIs(lineage_condition["triggered"], False)
        self.assertEqual(snapshot["post_selection_replay_status"], "NOT_RUN")
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("causal-trend-global-search", serialized)
        self.assertNotIn("private-prior-registration", serialized)
        self.assertNotIn("private-current-registration", serialized)
        self.assertNotIn("private/path", serialized)
        self.assertNotIn('"variant_id"', serialized)
        self.assertNotIn("registry_path", serialized)

    def test_schema14_missing_strategy_isolates_lineage_as_not_in_report(self) -> None:
        report = self._schema14_report()
        pointer = pointer_module._build_pointer("frozen.json", "f" * 64, report)

        snapshot = pointer_module._evidence_projection(
            report,
            pointer,
            self._verification(),
            requested_strategy_id="missing_strategy",
            implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
            observed_at_ms=None,
        )

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["strategy_match_status"], "NOT_IN_REPORT")
        lineage = snapshot["search_lineage"]
        self.assertEqual(lineage["status"], "NOT_IN_REPORT")
        self.assertFalse(lineage["family_bound"])
        self.assertIsNone(lineage["prior_trial_count"])
        self.assertIsNone(lineage["current_trial_count"])
        self.assertIsNone(lineage["cumulative_trial_count"])
        self.assertEqual(lineage["admission_status"], "NOT_IN_REPORT")
        admission = snapshot["preregistered_failure_admission"]
        self.assertEqual(admission["status"], "NOT_IN_REPORT")
        self.assertEqual(admission["search_lineage_status"], "NOT_IN_REPORT")
        self.assertEqual(snapshot["failure_conditions"]["status"], "NOT_IN_REPORT")
        self.assertEqual(snapshot["failure_conditions"]["conditions"], [])
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("causal-trend-global-search", serialized)
        self.assertNotIn("private-prior-registration", serialized)
        self.assertNotIn("private-current-registration", serialized)

    def test_schema14_receipt_only_cannot_become_available_public_evidence(self) -> None:
        report = self._schema14_report(receipt_only=True)
        pointer = pointer_module._build_pointer("frozen.json", "f" * 64, report)

        snapshot = pointer_module._evidence_projection(
            report,
            pointer,
            self._verification(),
            requested_strategy_id="dual_ma",
            implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
            observed_at_ms=None,
        )

        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["status"], "UNKNOWN")
        self.assertEqual(snapshot["source_verification_status"], "BLOCK")
        self.assertIn(
            "strategy_research_public_capability_contract_invalid",
            snapshot["blockers"],
        )
        self.assertIn(
            "public_search_lineage_live_at_selection_required",
            snapshot["blockers"],
        )
        self.assertIsNone(snapshot["evidence_contract"])
        self.assertIsNone(snapshot["failure_conditions"])

    def test_schema14_private_lineage_drift_and_receipt_only_forgery_fail_closed(self) -> None:
        mutations = {
            "source_family": lambda report: report["batch_spec"]["search_lineage"].__setitem__(
                "search_family_id", "different-private-search-family"
            ),
            "binding_family": lambda report: report[
                "preregistered_failure_admission"
            ]["search_lineage_binding"].__setitem__(
                "search_family_id", "different-private-search-family"
            ),
            "binding_current_count": lambda report: report[
                "preregistered_failure_admission"
            ]["search_lineage_binding"].__setitem__("current_trial_count", 4),
            "binding_cumulative_count": lambda report: report[
                "preregistered_failure_admission"
            ]["search_lineage_binding"].__setitem__("cumulative_trial_count", 9),
            "binding_hash": lambda report: report[
                "preregistered_failure_admission"
            ]["search_lineage_binding"].__setitem__("lineage_hash", "9" * 64),
            "registration_status": lambda report: report[
                "preregistered_failure_admission"
            ]["registration_binding"].__setitem__("status", "SELF_CONSISTENT_RECEIPT"),
            "registration_scope": lambda report: report[
                "preregistered_failure_admission"
            ]["registration_binding"].__setitem__(
                "verification_scope", "SELF_CONSISTENT_RECEIPT_ONLY"
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                report = self._schema14_report()
                mutate(report)
                pointer = pointer_module._build_pointer(
                    "frozen.json", "f" * 64, report
                )
                snapshot = pointer_module._evidence_projection(
                    report,
                    pointer,
                    self._verification(),
                    requested_strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
                    observed_at_ms=None,
                )
                self.assertFalse(snapshot["ok"])
                self.assertEqual(snapshot["status"], "UNKNOWN")
                self.assertIn(
                    "strategy_research_public_capability_contract_invalid",
                    snapshot["blockers"],
                )

        forged = self._schema14_report(receipt_only=True)
        forged["preregistered_failure_admission"]["status"] = "PASS"
        pointer = pointer_module._build_pointer("frozen.json", "f" * 64, forged)
        snapshot = pointer_module._evidence_projection(
            forged,
            pointer,
            self._verification(),
            requested_strategy_id="dual_ma",
            implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
            observed_at_ms=None,
        )
        self.assertFalse(snapshot["ok"])
        self.assertIn(
            "public_search_lineage_receipt_only_status_invalid",
            snapshot["blockers"],
        )

    def test_pointer_expectation_and_receipt_v1_field_sets_are_unchanged(self) -> None:
        self.assertEqual(
            pointer_module.STRATEGY_RESEARCH_POINTER_SCHEMA_VERSION,
            "strategy-research-report-pointer-v1",
        )
        self.assertEqual(
            pointer_module.STRATEGY_RESEARCH_POINTER_PUBLICATION_EXPECTATION_SCHEMA_VERSION,
            "strategy-research-pointer-publication-expectation-v1",
        )
        self.assertEqual(pointer_module._POINTER_FIELDS, {
            "schema_version", "status", "report_file", "report_file_sha256",
            "report_schema_version", "batch_spec_hash", "dataset_manifest_hash",
            "batch_run_hash", "governance_status", "created_at", "research_only",
            "descriptive_only", "profitability_proven", "performance_claim_allowed",
            "parameter_selection_allowed", "automatic_paper_activation_allowed",
            "paper_authorized", "live_order_allowed", "pointer_hash",
        })
        self.assertEqual(pointer_module._PUBLICATION_EXPECTATION_FIELDS, {
            "schema_version", "report_file", "report_hash", "report_file_sha256",
            "report_file_size_bytes", "report_schema_version", "batch_spec_hash",
            "dataset_manifest_hash", "batch_run_hash", "governance_status",
            "created_at", "research_only", "paper_authorized", "live_order_allowed",
            "expectation_hash",
        })
        self.assertEqual(pointer_module._PUBLICATION_RECEIPT_FIELDS, {
            "status", "published", "blockers", "expectation_hash", "pointer_hash",
            "report_hash", "report_file_sha256", "report_file_size_bytes",
            "report_schema_version", "batch_spec_hash", "dataset_manifest_hash",
            "batch_run_hash", "governance_status", "created_at",
            "source_verification_status", "pointer_post_read_verified",
            "report_post_read_verified", "research_only", "paper_authorized",
            "live_order_allowed",
        })

    def test_public_versions_are_explicit_and_unknown_schema15_fails_closed(self) -> None:
        self.assertEqual(
            pointer_module.STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V4,
            "strategy-lab-frozen-evidence-v4",
        )
        self.assertEqual(
            pointer_module.STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V5,
            "strategy-lab-frozen-evidence-v5",
        )
        self.assertEqual(
            pointer_module.STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V6,
            "strategy-lab-frozen-evidence-v6",
        )
        self.assertEqual(
            pointer_module.STRATEGY_LAB_FROZEN_EVIDENCE_SCHEMA_VERSION_V7,
            "strategy-lab-frozen-evidence-v7",
        )
        for schema_version in range(3, 11):
            with self.subTest(legacy_public_schema=schema_version):
                report = self._report()
                report["schema_version"] = schema_version
                pointer = pointer_module._build_pointer(
                    "frozen.json",
                    "f" * 64,
                    report,
                )
                snapshot = pointer_module._evidence_projection(
                    report,
                    pointer,
                    self._verification(),
                    requested_strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
                    observed_at_ms=None,
                )
                self.assertEqual(
                    snapshot["evidence_contract"]["schema_version"],
                    "strategy-lab-frozen-evidence-v3",
                )
                self.assertNotIn("post_selection_replay_summary", snapshot)
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_schema15.json"
            report = self._report()
            report["schema_version"] = 15
            self._write(report_path, report)
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                snapshot = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                )

        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["source_verification_status"], "BLOCK")
        self.assertIn("strategy_research_public_schema_unsupported", snapshot["blockers"])

    def test_current_signal_fingerprint_mismatch_is_visible_without_corrupting_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_20260812.json"
            self._write(report_path, self._report())
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                snapshot = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "e" * 64,
                )

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["source_verification_status"], "PASS")
        self.assertTrue(snapshot["implementation_currentness_checked"])
        self.assertEqual(snapshot["implementation_currentness_status"], "MISMATCH")
        self.assertFalse(snapshot["implementation_currentness_match"])
        self.assertEqual(
            snapshot["implementation_currentness"]["mismatched_variant_count"],
            3,
        )
        self.assertIn(
            "strategy_signal_implementation_fingerprint_changed",
            snapshot["implementation_currentness"]["blockers"],
        )
        self.assertFalse(snapshot["paper_authorized"])
        self.assertFalse(snapshot["live_order_allowed"])

    def test_current_signal_fingerprint_provider_failure_is_a_closed_projection(self) -> None:
        def unavailable_fingerprint(_strategy: str, _params: dict[str, object]) -> str:
            raise RuntimeError("synthetic provider failure")

        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_20260812.json"
            self._write(report_path, self._report())
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                snapshot = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=unavailable_fingerprint,
                )

        self.assertTrue(snapshot["ok"])
        self.assertEqual(snapshot["source_verification_status"], "PASS")
        self.assertEqual(snapshot["implementation_currentness_status"], "BLOCK")
        self.assertFalse(snapshot["implementation_currentness_checked"])
        self.assertIsNone(snapshot["implementation_currentness_match"])
        self.assertFalse(snapshot["paper_authorized"])
        self.assertFalse(snapshot["live_order_allowed"])

    def test_schema6_full_manifest_currentness_matches_then_detects_source_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_dir = root / "reports"
            report_dir.mkdir()
            source = root / "strategy_engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            report = self._report()
            report["schema_version"] = 6
            report["batch_spec"]["report_schema_version"] = 6
            report["implementation_manifest"] = build_implementation_manifest([source])
            report_path = report_dir / "strategy_research_20260812.json"
            self._write(report_path, report)

            with (
                patch(
                    "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                    return_value=self._verification(),
                ),
                patch.object(pointer_module, "_research_source_path_allowed", return_value=True),
                patch.object(pointer_module, "_research_manifest_entrypoints", return_value=[source]),
            ):
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                matched = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
                )
                source.write_text("VALUE = 2\n", encoding="utf-8")
                changed = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
                )
                report["schema_version"] = 5
                report["batch_spec"].pop("report_schema_version", None)
                self._write(report_path, report)
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                legacy_unbound = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "d" * 64,
                )

        self.assertTrue(matched["ok"])
        self.assertTrue(matched["full_implementation_manifest_checked"])
        self.assertEqual(matched["full_implementation_manifest_status"], "MATCH")
        self.assertTrue(matched["full_implementation_manifest_match"])
        self.assertEqual(matched["full_implementation_currentness"]["expected_source_count"], 1)
        self.assertEqual(changed["source_verification_status"], "PASS")
        self.assertTrue(changed["full_implementation_manifest_checked"])
        self.assertEqual(changed["full_implementation_manifest_status"], "MISMATCH")
        self.assertFalse(changed["full_implementation_manifest_match"])
        self.assertFalse(changed["paper_authorized"])
        self.assertFalse(changed["live_order_allowed"])
        self.assertFalse(legacy_unbound["full_implementation_manifest_checked"])
        self.assertEqual(
            legacy_unbound["full_implementation_manifest_status"],
            "NOT_AVAILABLE",
        )
        self.assertEqual(legacy_unbound["failure_conditions"]["status"], "GAPS")
        self.assertIn(
            "research_implementation_closure_changed_not_checked",
            legacy_unbound["failure_conditions"]["evidence_gaps"],
        )

    def test_failure_conditions_project_observed_failures_without_promoting_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_20260812.json"
            report = self._report()
            report["parameter_stability"]["strategies"][0]["status"] = "REVIEW"
            report["parameter_stability"]["strategies"][0]["blockers"] = [
                "parameter_stability_peak_without_adjacent_plateau"
            ]
            report["selection_cells"][0]["cost_sensitivity_status"] = "BLOCK"
            report["selection_cells"][0]["cost_sensitivity"]["worst_return_pct"] = -0.5
            report["selection_cells"][0]["cost_sensitivity"]["break_even_preserved"] = False
            self._write(report_path, report)
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                snapshot = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                    implementation_fingerprint_fn=lambda _strategy, _params: "e" * 64,
                )

        failures = snapshot["failure_conditions"]
        self.assertEqual(failures["status"], "TRIGGERED")
        self.assertIn("parameter_plateau_not_preserved", failures["observed"])
        self.assertIn("cost_stress_break_even_not_preserved", failures["observed"])
        self.assertIn("strategy_signal_implementation_changed", failures["observed"])
        self.assertFalse(failures["profitability_proven"])
        self.assertFalse(failures["parameter_selection_allowed"])
        self.assertFalse(failures["paper_authorized"])
        self.assertFalse(failures["live_order_allowed"])

    def test_public_manifest_path_policy_rejects_runtime_and_sensitive_names(self) -> None:
        project_root = Path(pointer_module.__file__).resolve().parents[2]
        self.assertTrue(pointer_module._research_source_path_allowed(
            project_root / "exchange_terminal" / "services" / "strategy_signals.py"
        ))
        self.assertFalse(pointer_module._research_source_path_allowed(
            project_root / "runtime_backup" / "source" / "strategy_signals.py"
        ))
        self.assertTrue(pointer_module._research_source_path_allowed(
            project_root / "exchange_terminal" / "runtime_adapter.py"
        ))
        self.assertFalse(pointer_module._research_source_path_allowed(project_root / ".env.py"))

    def test_missing_pointer_fails_closed_without_guessing_a_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = load_strategy_research_evidence_snapshot(
                Path(temporary),
                strategy_id="dual_ma",
            )

        self.assertFalse(snapshot["ok"])
        self.assertEqual(snapshot["status"], "UNKNOWN")
        self.assertEqual(snapshot["source_verification_status"], "BLOCK")
        self.assertIsNone(snapshot["pointer_hash"])
        self.assertFalse(snapshot["paper_authorized"])
        self.assertFalse(snapshot["live_order_allowed"])

    def test_report_tampering_after_pointer_publication_blocks_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_20260812.json"
            report = self._report()
            self._write(report_path, report)
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                self.assertTrue(
                    self._publish(report_dir, report_path)["published"]
                )
                report["selection_cells"][0]["cost_sensitivity"]["worst_return_pct"] = 99.0
                self._write(report_path, report)
                snapshot = load_strategy_research_evidence_snapshot(
                    report_dir,
                    strategy_id="dual_ma",
                )

        self.assertFalse(snapshot["ok"])
        self.assertIn(
            "strategy_research_pointer_file_sha256_mismatch",
            snapshot["blockers"],
        )

    def test_nested_execution_authority_blocks_pointer_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_20260812.json"
            report = self._report()
            report["selection_cells"][0]["can_trade"] = True
            self._write(report_path, report)

            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                result = self._publish(report_dir, report_path)

        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["published"])
        self.assertTrue(
            any("authority_not_false" in blocker for blocker in result["blockers"])
        )

    def test_publication_scope_skips_external_outputs_and_reserves_pointer_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_dir = root / "reports"
            report_dir.mkdir()
            external_dir = root / "external"
            external_dir.mkdir()

            skipped = strategy_research_pointer_publication_eligibility(
                report_dir,
                external_dir / "strategy_research.json",
            )
            blocked = strategy_research_pointer_publication_eligibility(
                report_dir,
                report_dir / DEFAULT_STRATEGY_RESEARCH_POINTER_FILE,
            )

        self.assertEqual(skipped["status"], "SKIP")
        self.assertFalse(skipped["publish"])
        self.assertEqual(blocked["status"], "BLOCK")
        self.assertFalse(blocked["publish"])

    def test_publication_expectation_binds_memory_report_bytes_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_bound.json"
            report = self._report()
            self._write(report_path, report)
            raw = report_path.read_bytes()
            expectation = build_strategy_research_pointer_publication_expectation(
                report,
                report_file=report_path.name,
                report_file_bytes=raw,
            )
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                receipt = publish_strategy_research_report_pointer(
                    report_dir,
                    report_path,
                    expectation=expectation,
                )

        self.assertEqual(receipt["status"], "PUBLISHED")
        self.assertTrue(receipt["pointer_post_read_verified"])
        self.assertTrue(receipt["report_post_read_verified"])
        self.assertEqual(receipt["report_file_sha256"], expectation["report_file_sha256"])
        self.assertEqual(receipt["report_file_size_bytes"], len(raw))
        verification = verify_strategy_research_pointer_publication_receipt(
            receipt,
            expectation=expectation,
        )
        self.assertEqual(verification["status"], "PASS", verification["blockers"])
        forged = dict(receipt)
        forged["batch_run_hash"] = "0" * 64
        self.assertEqual(
            verify_strategy_research_pointer_publication_receipt(
                forged,
                expectation=expectation,
            )["status"],
            "BLOCK",
        )

    def test_stale_expectation_blocks_before_pointer_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_bound.json"
            report = self._report()
            self._write(report_path, report)
            raw = report_path.read_bytes()
            expectation = build_strategy_research_pointer_publication_expectation(
                report,
                report_file=report_path.name,
                report_file_bytes=raw,
            )
            report["batch_run_hash"] = "9" * 64
            self._write(report_path, report)
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                result = publish_strategy_research_report_pointer(
                    report_dir,
                    report_path,
                    expectation=expectation,
                )

            self.assertEqual(result["status"], "BLOCK")
            self.assertFalse(result["published"])
            self.assertIn(
                "strategy_research_pointer_expectation_report_file_sha256_mismatch",
                result["blockers"],
            )
            self.assertFalse(
                (report_dir / DEFAULT_STRATEGY_RESEARCH_POINTER_FILE).exists()
            )

    def test_post_publish_report_swap_is_detected_by_exact_double_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_bound.json"
            report = self._report()
            self._write(report_path, report)
            expectation = build_strategy_research_pointer_publication_expectation(
                report,
                report_file=report_path.name,
                report_file_bytes=report_path.read_bytes(),
            )
            changed = dict(report)
            changed["batch_run_hash"] = "9" * 64
            changed_raw = json.dumps(changed, ensure_ascii=False).encode("utf-8")
            source_reads = 0
            original_read = pointer_module._read_bytes

            def swapped_read(path: Path) -> bytes:
                nonlocal source_reads
                if path == report_path.resolve():
                    source_reads += 1
                    if source_reads > 1:
                        return changed_raw
                return original_read(path)

            with (
                patch(
                    "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                    return_value=self._verification(),
                ),
                patch.object(pointer_module, "_read_bytes", side_effect=swapped_read),
            ):
                result = publish_strategy_research_report_pointer(
                    report_dir,
                    report_path,
                    expectation=expectation,
                )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("strategy_research_report_post_read_mismatch", result["blockers"])

    def test_windows_alias_basename_policy_is_casefolded_and_device_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            for basename in (
                "CURRENT_STRATEGY_RESEARCH_REPORT.JSON",
                "report.json.",
                "report.json ",
                "report.json:stream",
                "CON.json",
                "lpt1.txt",
            ):
                with self.subTest(basename=basename):
                    result = strategy_research_pointer_publication_eligibility(
                        report_dir,
                        report_dir / basename,
                    )
                    self.assertEqual(result["status"], "BLOCK")
                    self.assertFalse(result["publish"])

    def test_shared_authority_scanner_blocks_case_and_separator_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_alias.json"
            report = self._report()
            report["selection_cells"][0]["Live-Ready"] = True
            self._write(report_path, report)
            with patch(
                "exchange_terminal.services.strategy_research_pointer.verify_strategy_research_report",
                return_value=self._verification(),
            ):
                result = self._publish(report_dir, report_path)

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("authority_not_false" in item for item in result["blockers"]))

    def test_unexpected_publisher_exception_is_flat_and_path_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            report_path = report_dir / "strategy_research_bound.json"
            self._write(report_path, self._report())
            raw = report_path.read_bytes()
            expectation = build_strategy_research_pointer_publication_expectation(
                self._report(),
                report_file=report_path.name,
                report_file_bytes=raw,
            )
            with patch.object(
                pointer_module,
                "_publish_strategy_research_report_pointer",
                side_effect=RuntimeError(str(report_path)),
            ):
                result = publish_strategy_research_report_pointer(
                    report_dir,
                    report_path,
                    expectation=expectation,
                )

        rendered = json.dumps(result)
        self.assertEqual(result["status"], "BLOCK")
        self.assertNotIn(str(report_path), rendered)
        self.assertEqual(
            result["blockers"],
            ["strategy_research_pointer_publication_unexpected_failure"],
        )

    def test_http_route_is_read_only_and_does_not_rebuild_or_scan_reports(self) -> None:
        server_path = Path(__file__).parents[1] / "exchange_terminal" / "server.py"
        tree = ast.parse(server_path.read_text(encoding="utf-8"))
        route = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.If)
            and any(
                isinstance(item, ast.Constant)
                and item.value == "/api/strategy/research-evidence"
                for item in ast.walk(node.test)
            )
        )
        calls = {
            item.func.id
            for statement in route.body
            for item in ast.walk(statement)
            if isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
        }

        self.assertIn("load_strategy_research_evidence_snapshot", calls)
        self.assertNotIn("strategy_backtest_report", calls)
        self.assertNotIn("collect_internal_backtest_evidence", calls)
        self.assertNotIn("glob", calls)
        self.assertIn(
            "implementation_fingerprint_fn=strategy_implementation_fingerprint",
            ast.unparse(route),
        )


if __name__ == "__main__":
    unittest.main()
