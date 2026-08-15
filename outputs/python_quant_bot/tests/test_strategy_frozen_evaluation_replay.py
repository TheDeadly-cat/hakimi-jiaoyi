from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import math
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import run_internal_strategy_research as research_runner
from exchange_terminal.services import strategy_research_evidence
from exchange_terminal.services.strategy_benchmark import (
    build_calendar_split_schedule,
)
from exchange_terminal.services.strategy_cost_stress import (
    normalize_strategy_cost_risk,
)
from exchange_terminal.services.strategy_frozen_evaluation_replay import (
    FROZEN_TEST_ROLE,
    HOLDOUT_CONFIRMATION_ROLE,
    STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION,
    rebuild_strategy_frozen_confirmation_context,
)
from exchange_terminal.services.strategy_research import canonical_hash


class StrategyFrozenEvaluationReplayTests(unittest.TestCase):
    @staticmethod
    def rows(*, offset: int = 0) -> list[dict[str, object]]:
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        rows: list[dict[str, object]] = []
        for index in range(780):
            instant = start + timedelta(days=index)
            close = (
                100.0
                + 12.0 * math.sin((index + offset) * 2.0 * math.pi / 120.0)
                + index * 0.04
            )
            rows.append({
                "date": instant.date().isoformat(),
                "ts_ms": int(instant.timestamp() * 1000),
                "open": round(close * 0.999, 6),
                "high": round(close * 1.01, 6),
                "low": round(close * 0.99, 6),
                "close": round(close, 6),
                "volume": 1_000.0 + index,
                "complete": True,
                "complete_attested": True,
                "source": "UNIT_TEST",
            })
        return rows

    @staticmethod
    def candidate() -> dict[str, object]:
        params = {
            "fast_window": 10,
            "slow_window": 50,
            "position_pct": 0.25,
            "stop_loss_pct": 0.03,
        }
        risk = normalize_strategy_cost_risk({
            "position_pct": 20.0,
            "take_profit_pct": 0.0,
            "stop_loss_pct": 8.0,
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "leverage": 1.0,
        })
        return {
            "strategy_id": "dual_ma",
            "variant_id": "dual_ma:unit-test",
            "params": params,
            "param_hash": canonical_hash(params),
            "implementation_fingerprint": "unit-test-implementation-v1",
            "risk": risk,
            "risk_hash": canonical_hash(risk),
            "selection_lane": "RAW_EXCESS",
            "frozen_before_test": True,
        }

    @staticmethod
    def boundaries(rows: list[dict[str, object]]) -> dict[str, object]:
        schedule = build_calendar_split_schedule(
            {"BTC-USDT": {"source": "UNIT_TEST", "rows": rows}},
            train_ratio=0.5,
            validation_ratio=0.25,
            minimum_segment_rows=120,
        )
        if schedule.get("status") != "PASS":
            raise AssertionError(schedule)
        return dict(schedule["symbol_boundaries"]["BTC-USDT"])

    @staticmethod
    def reseal_result(result: dict[str, object]) -> None:
        content = {
            key: value for key, value in result.items()
            if key != "result_hash"
        }
        result["result_hash"] = canonical_hash(content)

    @staticmethod
    def reseal_replay(replay: dict[str, object]) -> None:
        content = {
            key: value for key, value in replay.items()
            if key != "evidence_hash"
        }
        replay["evidence_hash"] = canonical_hash(content)

    def assert_replay_verifies(
        self,
        cell: dict[str, object],
        *,
        role: str,
        symbol: str,
        rows: list[dict[str, object]],
        boundaries: dict[str, object],
    ) -> None:
        candidate = self.candidate()
        blockers = (
            strategy_research_evidence._verify_frozen_evaluation_cell_replay(
                cell,
                role=role,
                variant_id=str(candidate["variant_id"]),
                symbol=symbol,
                candidate=candidate,
                rows=rows,
                train_end_index=int(boundaries["train_end_index"]),
                validation_end_index=int(
                    boundaries["validation_end_index"]
                ),
                source="UNIT_TEST",
                market="crypto",
                timeframe="1D",
            )
        )
        self.assertEqual(blockers, [])

    def test_schema11_runner_uses_pure_test_and_holdout_replay(self) -> None:
        rows = self.rows()
        boundaries = self.boundaries(rows)
        candidate = self.candidate()
        with (
            patch.object(
                research_runner.server,
                "run_strategy_backtest",
                side_effect=AssertionError("schema11_must_use_pure_replay"),
            ),
            patch.object(
                research_runner,
                "run_holdout_cell",
                side_effect=AssertionError("schema11_must_not_use_legacy_holdout"),
            ),
        ):
            test_cell = research_runner.run_test_cell(
                symbol="BTC-USDT",
                candidate=candidate,
                payload={"source": "UNIT_TEST", "rows": rows},
                risk=dict(candidate["risk"]),
                boundaries=boundaries,
                report_schema_version=11,
            )
            holdout_cell = research_runner.run_holdout_replay_cell(
                symbol="BTC-USDT",
                candidate=candidate,
                payload={"source": "UNIT_TEST", "rows": rows},
                risk=dict(candidate["risk"]),
                boundaries=boundaries,
                report_schema_version=11,
            )

        for cell, role in (
            (test_cell, FROZEN_TEST_ROLE),
            (holdout_cell, HOLDOUT_CONFIRMATION_ROLE),
        ):
            replay = dict(cell["frozen_evaluation_replay"])
            self.assertEqual(
                replay["schema_version"],
                STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION,
            )
            self.assertEqual(replay["role"], role)
            self.assertEqual(replay["verification_status"], "PASS")
            self.assertIn("configured_run", replay)
            self.assertIn("benchmark_run", replay)
            self.assertIn("severe_cost_run", replay)
            self.assertIn("cost_stress_evidence", replay)
            self.assertFalse(cell["paper_authorized"])
            self.assertFalse(cell["live_order_allowed"])
            self.assert_replay_verifies(
                cell,
                role=role,
                symbol="BTC-USDT",
                rows=rows,
                boundaries=boundaries,
            )
        self.assertIsNone(
            test_cell["frozen_evaluation_replay"]["fixed_slice_scope"]
        )
        self.assertEqual(
            holdout_cell["frozen_evaluation_replay"]["fixed_slice_scope"],
            "FULL_FROZEN_CONFIRMATION_DATASET",
        )

    def test_schema11_test_rejects_999_and_wrong_boundary_after_reseal(self) -> None:
        rows = self.rows()
        boundaries = self.boundaries(rows)
        candidate = self.candidate()
        cell = research_runner.run_test_cell(
            symbol="BTC-USDT",
            candidate=candidate,
            payload={"source": "UNIT_TEST", "rows": rows},
            risk=dict(candidate["risk"]),
            boundaries=boundaries,
            report_schema_version=11,
        )
        attacked = deepcopy(cell)
        replay = attacked["frozen_evaluation_replay"]
        configured = replay["configured_run"]["result_projection"]
        configured["total_return_pct"] = 999.0
        configured["trade_count"] = 999
        self.reseal_result(configured)
        replay["flat_metric_projection"]["test_return_pct"] = 999.0
        replay["flat_metric_projection"]["test_trade_count"] = 999
        attacked["test_return_pct"] = 999.0
        attacked["test_trade_count"] = 999
        self.reseal_replay(replay)
        attacked["run_hash"] = (
            strategy_research_evidence.strategy_research_test_cell_hash_for_report(
                attacked,
                dict(candidate["risk"]),
                report_schema_version=11,
            )
        )
        self.assertEqual(
            attacked["run_hash"],
            strategy_research_evidence.strategy_research_test_cell_hash_for_report(
                attacked,
                dict(candidate["risk"]),
                report_schema_version=11,
            ),
        )
        blockers = (
            strategy_research_evidence._verify_frozen_evaluation_cell_replay(
                attacked,
                role=FROZEN_TEST_ROLE,
                variant_id=str(candidate["variant_id"]),
                symbol="BTC-USDT",
                candidate=candidate,
                rows=rows,
                train_end_index=int(boundaries["train_end_index"]),
                validation_end_index=int(
                    boundaries["validation_end_index"]
                ),
                source="UNIT_TEST",
                market="crypto",
                timeframe="1D",
            )
        )
        self.assertIn(
            "research_frozen_test_replay_semantic_mismatch:dual_ma:unit-test:BTC-USDT",
            blockers,
        )

        wrong_boundaries = dict(boundaries)
        wrong_boundaries["validation_end_index"] = (
            int(boundaries["validation_end_index"]) + 1
        )
        wrong_boundary_cell = research_runner.run_test_cell(
            symbol="BTC-USDT",
            candidate=candidate,
            payload={"source": "UNIT_TEST", "rows": rows},
            risk=dict(candidate["risk"]),
            boundaries=wrong_boundaries,
            report_schema_version=11,
        )
        wrong_blockers = (
            strategy_research_evidence._verify_frozen_evaluation_cell_replay(
                wrong_boundary_cell,
                role=FROZEN_TEST_ROLE,
                variant_id=str(candidate["variant_id"]),
                symbol="BTC-USDT",
                candidate=candidate,
                rows=rows,
                train_end_index=int(boundaries["train_end_index"]),
                validation_end_index=int(
                    boundaries["validation_end_index"]
                ),
                source="UNIT_TEST",
                market="crypto",
                timeframe="1D",
            )
        )
        self.assertIn(
            "research_frozen_test_replay_semantic_mismatch:dual_ma:unit-test:BTC-USDT",
            wrong_blockers,
        )

    def test_schema11_holdout_rejects_999_and_legacy_source_hash(self) -> None:
        rows = self.rows()
        boundaries = self.boundaries(rows)
        candidate = self.candidate()
        cell = research_runner.run_holdout_replay_cell(
            symbol="BTC-USDT",
            candidate=candidate,
            payload={"source": "UNIT_TEST", "rows": rows},
            risk=dict(candidate["risk"]),
            boundaries=boundaries,
            report_schema_version=11,
        )
        attacked = deepcopy(cell)
        attacked["source_run_hash"] = "f" * 64
        replay = attacked["frozen_evaluation_replay"]
        configured = replay["configured_run"]["result_projection"]
        configured["total_return_pct"] = 999.0
        configured["trade_count"] = 999
        self.reseal_result(configured)
        replay["flat_metric_projection"]["test_return_pct"] = 999.0
        replay["flat_metric_projection"]["baseline_return_pct"] = 999.0
        replay["flat_metric_projection"]["test_trade_count"] = 999
        replay["flat_metric_projection"]["baseline_trade_count"] = 999
        for field in (
            "test_return_pct",
            "baseline_return_pct",
            "test_trade_count",
            "baseline_trade_count",
        ):
            attacked[field] = replay["flat_metric_projection"][field]
        self.reseal_replay(replay)
        attacked["run_hash"] = (
            strategy_research_evidence.strategy_research_holdout_cell_hash_for_report(
                attacked,
                candidate,
                report_schema_version=11,
            )
        )
        blockers = (
            strategy_research_evidence._verify_frozen_evaluation_cell_replay(
                attacked,
                role=HOLDOUT_CONFIRMATION_ROLE,
                variant_id=str(candidate["variant_id"]),
                symbol="BTC-USDT",
                candidate=candidate,
                rows=rows,
                train_end_index=int(boundaries["train_end_index"]),
                validation_end_index=int(
                    boundaries["validation_end_index"]
                ),
                source="UNIT_TEST",
                market="crypto",
                timeframe="1D",
            )
        )
        self.assertIn(
            "research_holdout_replay_semantic_mismatch:dual_ma:unit-test:BTC-USDT",
            blockers,
        )
        self.assertIn(
            "research_holdout_legacy_source_hash_forbidden:dual_ma:unit-test:BTC-USDT",
            blockers,
        )
        wrong_boundaries = dict(boundaries)
        wrong_boundaries["validation_end_index"] = (
            int(boundaries["validation_end_index"]) + 1
        )
        wrong_boundary_cell = research_runner.run_holdout_replay_cell(
            symbol="BTC-USDT",
            candidate=candidate,
            payload={"source": "UNIT_TEST", "rows": rows},
            risk=dict(candidate["risk"]),
            boundaries=wrong_boundaries,
            report_schema_version=11,
        )
        wrong_boundary_blockers = (
            strategy_research_evidence._verify_frozen_evaluation_cell_replay(
                wrong_boundary_cell,
                role=HOLDOUT_CONFIRMATION_ROLE,
                variant_id=str(candidate["variant_id"]),
                symbol="BTC-USDT",
                candidate=candidate,
                rows=rows,
                train_end_index=int(boundaries["train_end_index"]),
                validation_end_index=int(
                    boundaries["validation_end_index"]
                ),
                source="UNIT_TEST",
                market="crypto",
                timeframe="1D",
            )
        )
        self.assertIn(
            "research_holdout_replay_semantic_mismatch:dual_ma:unit-test:BTC-USDT",
            wrong_boundary_blockers,
        )

    def test_confirmation_context_rebuilds_alignment_and_rejects_skew(self) -> None:
        rows = self.rows()
        sources = {
            "BTC-USDT": "UNIT_TEST",
            "ETH-USDT": "UNIT_TEST",
        }
        datasets = {
            symbol: {
                "role": "CONFIRMATION",
                "symbol": symbol,
                "source": source,
                "market": "crypto",
                "timeframe": "1D",
                "rows": deepcopy(rows),
            }
            for symbol, source in sources.items()
        }
        manifests = [
            {
                "role": "CONFIRMATION",
                "symbol": symbol,
                "source": source,
                "status": "PASS",
                "blockers": [],
            }
            for symbol, source in sources.items()
        ]
        kwargs = {
            "datasets": datasets,
            "expected_symbols": set(sources),
            "manifests": manifests,
            "split_policy": {
                "train_ratio": 0.5,
                "validation_ratio": 0.25,
                "minimum_segment_rows": 120,
            },
            "data_policy": {
                "max_endpoint_skew_days": 0,
                "max_boundary_skew_days": 0,
            },
            "required_start": rows[0]["date"],
            "required_as_of": rows[-1]["date"],
        }
        rebuilt = rebuild_strategy_frozen_confirmation_context(**kwargs)
        self.assertEqual(rebuilt["status"], "PASS", rebuilt["blockers"])
        verified = rebuild_strategy_frozen_confirmation_context(
            **kwargs,
            reported_alignment=deepcopy(rebuilt["alignment"]),
            reported_schedule=deepcopy(rebuilt["schedule"]),
        )
        self.assertEqual(verified["status"], "PASS", verified["blockers"])

        forged_reported = deepcopy(rebuilt["alignment"])
        forged_reported["status"] = "BLOCK"
        forged_reported["blockers"] = ["forged_reported_block"]
        forged = rebuild_strategy_frozen_confirmation_context(
            **kwargs,
            reported_alignment=forged_reported,
            reported_schedule=deepcopy(rebuilt["schedule"]),
        )
        self.assertIn(
            "holdout_alignment_semantic_mismatch",
            forged["blockers"],
        )

        skewed_kwargs = deepcopy(kwargs)
        skewed_kwargs["datasets"]["ETH-USDT"]["rows"].pop(400)
        skewed = rebuild_strategy_frozen_confirmation_context(
            **skewed_kwargs,
            reported_alignment=deepcopy(rebuilt["alignment"]),
            reported_schedule=deepcopy(rebuilt["schedule"]),
        )
        self.assertEqual(skewed["status"], "BLOCK")
        self.assertTrue(any(
            blocker.startswith("holdout_aligned_rows_mismatch:")
            or blocker == "holdout_alignment_semantic_mismatch"
            for blocker in skewed["blockers"]
        ))

    def test_schema10_hash_contracts_keep_legacy_semantics(self) -> None:
        candidate = self.candidate()
        selection_cell = {
            "phase": "TRAIN_VALIDATION_SELECTION",
            "symbol": "BTC-USDT",
            "selection_replay": {"schema_version": "unit-test"},
        }
        default_selection_hash = (
            strategy_research_evidence.strategy_research_selection_cell_hash_v5(
                selection_cell,
                dict(candidate["risk"]),
            )
        )
        self.assertEqual(
            default_selection_hash,
            strategy_research_evidence.strategy_research_selection_cell_hash_v5(
                selection_cell,
                dict(candidate["risk"]),
                report_schema_version=10,
            ),
        )
        self.assertNotEqual(
            default_selection_hash,
            strategy_research_evidence.strategy_research_selection_cell_hash_v5(
                selection_cell,
                dict(candidate["risk"]),
                report_schema_version=11,
            ),
        )
        test_cell = {
            "phase": "FROZEN_TEST_ONCE",
            "symbol": "BTC-USDT",
            "test_return_pct": 1.0,
            "elapsed_ms": 99,
        }
        self.assertEqual(
            strategy_research_evidence.strategy_research_test_cell_hash_for_report(
                test_cell,
                dict(candidate["risk"]),
                report_schema_version=10,
            ),
            strategy_research_evidence.strategy_research_test_cell_hash_v2(
                test_cell,
                dict(candidate["risk"]),
                report_schema_version=10,
            ),
        )

    def test_schema11_no_candidate_cannot_forge_holdout_pass(self) -> None:
        report = {
            "schema_version": 11,
            "dataset_snapshot": {"datasets": []},
            "dataset_manifest": [],
            "selection_cells": [],
            "selection_calendar_schedule": {},
            "selection_alignment": {},
            "validation_rankings": [],
            "parameter_stability": (
                research_runner.build_parameter_stability_snapshot(
                    [],
                    frozen_variants=[],
                )
            ),
            "validation_candidates": [],
            "frozen_candidates": [],
            "test_cells": [],
            "test_results": [],
            "holdout_alignment": {"status": "PASS", "blockers": []},
            "holdout_calendar_schedule": {
                "status": "PASS",
                "blockers": [],
                "symbol_boundaries": {},
            },
            "holdout_cells": [],
            "holdout_results": [],
            "forward_candidates": [],
        }
        batch_spec = {
            "variants": [],
            "selection_symbols": ["BTC-USDT"],
            "confirmation_symbols": ["ETH-USDT"],
            "split_policy": {
                "train_ratio": 0.5,
                "validation_ratio": 0.25,
                "minimum_segment_rows": 120,
            },
            "data_policy": {
                "max_endpoint_skew_days": 0,
                "max_boundary_skew_days": 0,
            },
            "max_test_candidates": 1,
        }
        blockers = strategy_research_evidence._verify_research_semantics(
            report,
            batch_spec=batch_spec,
            formal=True,
        )
        self.assertIn(
            "research_holdout_alignment_not_run_semantic_mismatch",
            blockers,
        )
        self.assertIn(
            "research_holdout_calendar_schedule_not_run_semantic_mismatch",
            blockers,
        )

    def test_schema11_identity_and_authority_aliases_fail_closed(self) -> None:
        rows = self.rows()
        boundaries = self.boundaries(rows)
        candidate = self.candidate()
        test_cell = research_runner.run_test_cell(
            symbol="BTC-USDT",
            candidate=candidate,
            payload={"source": "UNIT_TEST", "rows": rows},
            risk=dict(candidate["risk"]),
            boundaries=boundaries,
            report_schema_version=11,
        )
        test_cell["frozen_before_test"] = False
        holdout_cell = research_runner.run_holdout_replay_cell(
            symbol="BTC-USDT",
            candidate=candidate,
            payload={"source": "UNIT_TEST", "rows": rows},
            risk=dict(candidate["risk"]),
            boundaries=boundaries,
            report_schema_version=11,
        )
        holdout_cell["phase"] = "FORGED_PHASE"
        test_blockers = (
            strategy_research_evidence._verify_frozen_evaluation_cell_replay(
                test_cell,
                role=FROZEN_TEST_ROLE,
                variant_id=str(candidate["variant_id"]),
                symbol="BTC-USDT",
                candidate=candidate,
                rows=rows,
                train_end_index=int(boundaries["train_end_index"]),
                validation_end_index=int(
                    boundaries["validation_end_index"]
                ),
                source="UNIT_TEST",
                market="crypto",
                timeframe="1D",
            )
        )
        holdout_blockers = (
            strategy_research_evidence._verify_frozen_evaluation_cell_replay(
                holdout_cell,
                role=HOLDOUT_CONFIRMATION_ROLE,
                variant_id=str(candidate["variant_id"]),
                symbol="BTC-USDT",
                candidate=candidate,
                rows=rows,
                train_end_index=int(boundaries["train_end_index"]),
                validation_end_index=int(
                    boundaries["validation_end_index"]
                ),
                source="UNIT_TEST",
                market="crypto",
                timeframe="1D",
            )
        )
        self.assertTrue(any(
            item.startswith(
                "research_frozen_test_not_frozen_before_evaluation:"
            )
            for item in test_blockers
        ))
        self.assertTrue(any(
            item.startswith("research_holdout_phase_invalid:")
            for item in holdout_blockers
        ))

        authority_payload = {
            "canTrade": True,
            "nested": [
                {"live-order-allowed": True},
                ({"parameter_selection_authority": True},),
            ],
        }
        paths = strategy_research_evidence.authority_violations(
            authority_payload
        )
        self.assertEqual(
            paths,
            [
                "$.canTrade",
                "$.nested[0].live-order-allowed",
                "$.nested[1][0].parameter_selection_authority",
            ],
        )
        report = {
            "schema_version": 11,
            "canTrade": True,
            "nested": authority_payload["nested"],
        }
        report["batch_run_hash"] = (
            strategy_research_evidence.strategy_research_result_hash(report)
        )
        verification = (
            strategy_research_evidence.verify_strategy_research_report(
                report,
                require_formal=False,
            )
        )
        self.assertIn(
            "research_execution_authority:$.canTrade",
            verification["blockers"],
        )
        self.assertIn(
            "research_execution_authority:$.nested[0].live-order-allowed",
            verification["blockers"],
        )
        self.assertIn(
            "research_execution_authority:$.nested[1][0].parameter_selection_authority",
            verification["blockers"],
        )
        holdout_cell = {
            "phase": "HOLDOUT_CONFIRMATION",
            "symbol": "BTC-USDT",
            "strategy_id": candidate["strategy_id"],
            "variant_id": candidate["variant_id"],
            "source_run_hash": "legacy-source",
            "dataset_hash": "legacy-dataset",
        }
        self.assertEqual(
            strategy_research_evidence.strategy_research_holdout_cell_hash_for_report(
                holdout_cell,
                candidate,
                report_schema_version=10,
            ),
            strategy_research_evidence.strategy_research_holdout_cell_hash(
                holdout_cell,
                candidate,
            ),
        )


if __name__ == "__main__":
    unittest.main()
