from __future__ import annotations

from copy import deepcopy
import json
import unittest

from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.strategy_frozen_evaluation_replay import (
    FROZEN_TEST_ROLE,
    HOLDOUT_CONFIRMATION_ROLE,
    STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_post_selection_replay_summary import (
    STRATEGY_POST_SELECTION_REPLAY_SUMMARY_SCHEMA_VERSION,
    build_strategy_post_selection_replay_summary,
)
from exchange_terminal.services.strategy_research import (
    aggregate_frozen_test,
    aggregate_holdout_confirmation,
)


class StrategyPostSelectionReplaySummaryTests(unittest.TestCase):
    @staticmethod
    def _candidate(strategy_id: str = "dual_ma", variant_id: str = "secret-variant") -> dict[str, object]:
        return {
            "strategy_id": strategy_id,
            "variant_id": variant_id,
            "params": {"fast": 8, "slow": 24},
            "param_hash": "a" * 64,
            "implementation_fingerprint": "b" * 64,
            "selection_lane": "RAW_EXCESS",
            "frozen_before_test": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    @staticmethod
    def _replay(role: str, *, status: str = "PASS", verification: str = "PASS") -> dict[str, object]:
        holdout = role == HOLDOUT_CONFIRMATION_ROLE
        return {
            "schema_version": STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION,
            "role": role,
            "verification_status": verification,
            "status": status,
            "configured_run": {
                "result_projection": {
                    "ok": True,
                    "total_return_pct": 4.0,
                    "max_drawdown_pct": 5.0,
                    "trade_count": 3,
                },
            },
            "severe_cost_run": {
                "result_projection": {
                    "ok": True,
                    "total_return_pct": 1.0,
                    "max_drawdown_pct": 6.0,
                    "trade_count": 3,
                },
            },
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
    def _cell(
        cls,
        role: str,
        *,
        strategy_id: str = "dual_ma",
        variant_id: str = "secret-variant",
        symbol: str = "BTC-USDT",
    ) -> dict[str, object]:
        cell: dict[str, object] = {
            "phase": role,
            "symbol": symbol,
            "strategy_id": strategy_id,
            "variant_id": variant_id,
            "dataset_status": "PASS",
            "test_ok": True,
            "test_return_pct": 4.0,
            "test_excess_return_pct": 2.0,
            "test_trade_count": 3,
            "test_max_drawdown_pct": 5.0,
            "test_cost_status": "PASS",
            "frozen_evaluation_replay": cls._replay(role),
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if role == HOLDOUT_CONFIRMATION_ROLE:
            cell.update({
                "baseline_ok": True,
                "cost_sensitivity_status": "PASS",
                "temporal_status": "PASS",
                "walk_forward_status": "PASS",
                "lookahead_status": "PASS",
            })
        return cell

    @classmethod
    def _report(cls, schema_version: int = 11) -> dict[str, object]:
        candidate = cls._candidate()
        test_cell = cls._cell(FROZEN_TEST_ROLE)
        test_result = aggregate_frozen_test(candidate, [test_cell], required_symbols=1)
        holdout_cell = cls._cell(HOLDOUT_CONFIRMATION_ROLE)
        holdout_result = aggregate_holdout_confirmation(
            test_result,
            [holdout_cell],
            required_symbols=1,
        )
        holdout_result.update({
            "variant_id": test_result["variant_id"],
            "params": test_result["params"],
            "param_hash": test_result["param_hash"],
        })
        return {
            "schema_version": schema_version,
            "batch_spec": {
                "selection_symbols": ["BTC-USDT"],
                "confirmation_symbols": ["ETH-USDT"],
            },
            "frozen_candidates": [candidate],
            "test_cells": [test_cell],
            "test_results": [test_result],
            "holdout_cells": [{**holdout_cell, "symbol": "ETH-USDT"}],
            "holdout_results": [holdout_result],
            "forward_candidates": [test_result["variant_id"]],
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def test_happy_path_is_selected_strategy_only_native_and_non_authorizing(self) -> None:
        report = self._report()

        result = build_strategy_post_selection_replay_summary(
            report,
            strategy_id="dual_ma",
        )

        self.assertEqual(
            result["schema_version"],
            STRATEGY_POST_SELECTION_REPLAY_SUMMARY_SCHEMA_VERSION,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["frozen_test"]["stage"], FROZEN_TEST_ROLE)
        self.assertEqual(result["holdout_confirmation"]["stage"], HOLDOUT_CONFIRMATION_ROLE)
        self.assertEqual(result["frozen_test"]["minimum_configured_return_pct"], 4.0)
        self.assertEqual(result["holdout_confirmation"]["fixed_slice_pass_cell_count"], 1)
        self.assertEqual(result["holdout_confirmation"]["total_trades"], 3)
        self.assertEqual(authority_violations(result), [])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("secret-variant", serialized)
        self.assertNotIn("BTC-USDT", serialized)
        self.assertNotIn("ETH-USDT", serialized)
        self.assertNotIn('"params"', serialized)

    def test_inner_outcome_block_is_visible_with_verified_negative_metrics(self) -> None:
        report = self._report()
        report["test_cells"][0]["frozen_evaluation_replay"]["status"] = "BLOCK"

        result = build_strategy_post_selection_replay_summary(report, strategy_id="dual_ma")

        stage = result["frozen_test"]
        self.assertEqual(stage["status"], "BLOCK")
        self.assertEqual(stage["replay_verified_cell_count"], 1)
        self.assertEqual(stage["replay_pass_cell_count"], 0)
        self.assertEqual(stage["minimum_configured_return_pct"], 4.0)
        self.assertIn("post_selection_replay_outcome_not_preserved", stage["blockers"])

    def test_inner_verification_block_hides_all_performance_metrics(self) -> None:
        report = self._report()
        report["test_cells"][0]["frozen_evaluation_replay"]["verification_status"] = "BLOCK"

        stage = build_strategy_post_selection_replay_summary(
            report,
            strategy_id="dual_ma",
        )["frozen_test"]

        self.assertEqual(stage["status"], "BLOCK")
        for field in (
            "minimum_configured_return_pct",
            "minimum_excess_return_pct",
            "minimum_severe_cost_return_pct",
            "worst_drawdown_pct",
            "total_trades",
        ):
            self.assertIsNone(stage[field])
        self.assertIn("post_selection_replay_integrity_not_preserved", stage["blockers"])

    def test_aggregate_block_keeps_finite_negative_evidence_when_integrity_passes(self) -> None:
        report = self._report()
        cell = report["test_cells"][0]
        cell["test_return_pct"] = -2.0
        cell["test_excess_return_pct"] = -3.0
        replay = cell["frozen_evaluation_replay"]
        replay["status"] = "BLOCK"
        replay["configured_run"]["result_projection"]["total_return_pct"] = -2.0
        replay["flat_metric_projection"]["test_excess_return_pct"] = -3.0
        report["test_results"] = [
            aggregate_frozen_test(report["frozen_candidates"][0], [cell], required_symbols=1)
        ]
        report["holdout_cells"] = []
        report["holdout_results"] = []

        result = build_strategy_post_selection_replay_summary(report, strategy_id="dual_ma")

        self.assertEqual(result["frozen_test"]["status"], "BLOCK")
        self.assertEqual(result["frozen_test"]["minimum_configured_return_pct"], -2.0)
        self.assertEqual(result["frozen_test"]["minimum_excess_return_pct"], -3.0)

    def test_reported_aggregate_semantic_mismatch_blocks_and_hides_metrics(self) -> None:
        report = self._report()
        report["test_results"][0]["median_test_return_pct"] = 999.0

        stage = build_strategy_post_selection_replay_summary(
            report,
            strategy_id="dual_ma",
        )["frozen_test"]

        self.assertEqual(stage["status"], "BLOCK")
        self.assertIn(
            "post_selection_aggregate_semantics_not_preserved",
            stage["blockers"],
        )
        self.assertIsNone(stage["minimum_configured_return_pct"])
        self.assertIsNone(stage["total_trades"])

    def test_only_completely_empty_stage_is_not_run_and_partial_is_block(self) -> None:
        empty = {
            "schema_version": 12,
            "batch_spec": {
                "selection_symbols": ["BTC-USDT"],
                "confirmation_symbols": ["ETH-USDT"],
            },
            "frozen_candidates": [],
            "test_cells": [],
            "test_results": [],
            "holdout_cells": [],
            "holdout_results": [],
        }
        not_run = build_strategy_post_selection_replay_summary(empty, strategy_id="dual_ma")
        self.assertEqual(not_run["status"], "NOT_RUN")
        self.assertEqual(not_run["frozen_test"]["status"], "NOT_RUN")
        self.assertEqual(not_run["holdout_confirmation"]["status"], "NOT_RUN")

        partial = deepcopy(empty)
        partial["frozen_candidates"] = [self._candidate()]
        blocked = build_strategy_post_selection_replay_summary(partial, strategy_id="dual_ma")
        self.assertEqual(blocked["frozen_test"]["status"], "BLOCK")
        self.assertIsNone(blocked["frozen_test"]["total_trades"])

    def test_strategy_isolation_does_not_borrow_another_strategy_cells_or_results(self) -> None:
        report = self._report()
        other = self._candidate("other_strategy", "other-secret")
        other_cell = self._cell(
            FROZEN_TEST_ROLE,
            strategy_id="other_strategy",
            variant_id="other-secret",
        )
        report["frozen_candidates"].append(other)
        report["test_cells"].append(other_cell)
        report["test_results"].append(
            aggregate_frozen_test(other, [other_cell], required_symbols=1)
        )

        selected = build_strategy_post_selection_replay_summary(report, strategy_id="dual_ma")
        missing = build_strategy_post_selection_replay_summary(report, strategy_id="missing")

        self.assertEqual(selected["frozen_test"]["candidate_count"], 1)
        self.assertEqual(missing["status"], "NOT_RUN")
        self.assertNotIn("other-secret", json.dumps(selected))

    def test_selected_strategy_unknown_variant_and_non_mapping_rows_block_coverage(self) -> None:
        report = self._report()
        report["test_cells"].append(
            self._cell(FROZEN_TEST_ROLE, variant_id="unknown-selected-variant")
        )
        unknown_variant = build_strategy_post_selection_replay_summary(
            report,
            strategy_id="dual_ma",
        )["frozen_test"]
        self.assertEqual(unknown_variant["status"], "BLOCK")
        self.assertIn(
            "post_selection_cell_coverage_not_preserved",
            unknown_variant["blockers"],
        )
        self.assertIsNone(unknown_variant["minimum_configured_return_pct"])

        malformed = self._report()
        malformed["test_cells"].append("not-a-cell")
        malformed_stage = build_strategy_post_selection_replay_summary(
            malformed,
            strategy_id="dual_ma",
        )["frozen_test"]
        self.assertEqual(malformed_stage["status"], "BLOCK")
        self.assertIsNone(malformed_stage["total_trades"])

        only_malformed = {
            "schema_version": 11,
            "batch_spec": {
                "selection_symbols": ["BTC-USDT"],
                "confirmation_symbols": ["ETH-USDT"],
            },
            "frozen_candidates": ["not-a-candidate"],
            "test_results": [],
            "test_cells": [],
            "holdout_results": [],
            "holdout_cells": [],
        }
        self.assertEqual(
            build_strategy_post_selection_replay_summary(
                only_malformed,
                strategy_id="dual_ma",
            )["frozen_test"]["status"],
            "BLOCK",
        )

        malformed_container = deepcopy(only_malformed)
        malformed_container["frozen_candidates"] = {
            "strategy_id": "dual_ma",
            "variant_id": "must-not-be-normalized-to-empty",
        }
        malformed_container_stage = build_strategy_post_selection_replay_summary(
            malformed_container,
            strategy_id="dual_ma",
        )["frozen_test"]
        self.assertEqual(malformed_container_stage["status"], "BLOCK")
        self.assertIn(
            "post_selection_candidate_contract_invalid",
            malformed_container_stage["blockers"],
        )
        self.assertIsNone(malformed_container_stage["total_trades"])

    def test_schema14_is_explicitly_supported_and_unknown_schema15_fails_closed(self) -> None:
        schema14 = build_strategy_post_selection_replay_summary(
            self._report(schema_version=14),
            strategy_id="dual_ma",
        )
        self.assertEqual(schema14["report_schema_version"], 14)
        self.assertEqual(schema14["status"], "PASS")
        with self.assertRaisesRegex(ValueError, "report_schema_unsupported"):
            build_strategy_post_selection_replay_summary(
                {"schema_version": 15},
                strategy_id="dual_ma",
            )


if __name__ == "__main__":
    unittest.main()
