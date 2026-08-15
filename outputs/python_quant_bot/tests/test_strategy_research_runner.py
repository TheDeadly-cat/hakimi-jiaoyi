from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import run_internal_strategy_research as research_runner
from exchange_terminal.services import strategy_research_evidence as research_evidence
from exchange_terminal.services.implementation_manifest import build_implementation_manifest
from exchange_terminal.services.strategy_research import build_legacy_parameter_stability_snapshot_v1
from exchange_terminal.services.strategy_benchmark import align_completed_daily_payloads
from exchange_terminal.services.market_calendar import build_market_calendar_contract
from exchange_terminal.services.strategy_selection_alignment import (
    build_strategy_selection_alignment_input_snapshot,
)
from exchange_terminal.services.strategy_research_evidence import (
    HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
    LEGACY_STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION,
    STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION,
    strategy_research_selection_cell_hash,
    strategy_research_selection_cell_hash_for_report,
    strategy_research_test_cell_hash,
    strategy_research_test_cell_hash_for_report,
    verify_strategy_research_report,
)
from exchange_terminal.services.strategy_research_pointer import (
    load_strategy_research_evidence_snapshot,
)
from exchange_terminal.services.strategy_research_protocol_artifact import (
    plan_strategy_research_protocol_artifact,
    publish_strategy_research_protocol_artifact_no_clobber,
)
from exchange_terminal.services.strategy_hypothesis_preregistration import (
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    build_strategy_hypothesis_preregistration,
)
from exchange_terminal.services.strategy_preregistered_failure_admission import (
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    StrategyMatrixRegistrationStore,
    build_strategy_matrix_protocol,
    verify_strategy_matrix_protocol,
)
from tests.portfolio_governance_fixtures import attested_clock


class StopBeforeDataLoad(RuntimeError):
    pass


class StrategyResearchRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_mode = patch.object(research_runner.server, "RUNTIME_READ_ONLY", False)
        runtime_mode.start()
        self.addCleanup(runtime_mode.stop)

    @staticmethod
    def hypothesis_v1(*, generation: str = "TEST") -> dict[str, object]:
        return build_strategy_hypothesis_preregistration({
            "schema_version": STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
            "hypothesis_id": "dual-ma-causal-persistence-v1",
            "research_generation": generation,
            "strategy_ids": ["dual_ma"],
            "mechanism_family": "causal moving-average persistence confirmation",
            "hypothesis_statement": (
                "Completed-bar moving-average persistence should retain positive "
                "benchmark excess after configured and stressed costs."
            ),
            "novelty_statement": (
                "This causal persistence mechanism does not reuse or retune the "
                "falsified pullback and squeeze entry families."
            ),
            "mechanism_specific_failure_conditions": [
                "Retire this hypothesis if fresh benchmark excess is not positive after stressed costs."
            ],
        })

    @staticmethod
    def hypothesis(*, generation: str = "TEST") -> dict[str, object]:
        return build_strategy_hypothesis_preregistration({
            "schema_version": (
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
            ),
            "hypothesis_id": "dual-ma-causal-persistence-v2",
            "research_generation": generation,
            "strategy_ids": ["dual_ma"],
            "mechanism_family": "causal moving-average persistence confirmation",
            "hypothesis_statement": (
                "Completed-bar moving-average persistence should retain positive "
                "benchmark excess after configured and stressed costs."
            ),
            "novelty_statement": (
                "This causal persistence mechanism does not reuse or retune the "
                "falsified pullback and squeeze entry families."
            ),
            "mechanism_specific_failure_conditions": [{
                "condition_id": "validation_excess_lost",
                "evidence_stage": "DEVELOPMENT_SELECTION",
                "metric": "median_validation_excess_return_pct",
                "operator": "LTE",
                "threshold": 0.0,
                "required_action": "BLOCK_RESEARCH",
            }],
        })

    @staticmethod
    def hypothesis_v3(*, generation: str = "TEST") -> dict[str, object]:
        payload = dict(
            StrategyResearchRunnerTests.hypothesis(generation=generation)
        )
        payload.pop("hypothesis_hash")
        payload.update({
            "schema_version": (
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
            ),
            "hypothesis_id": "dual-ma-causal-persistence-v3",
            "search_family_id": "dual-ma-causal-global-search",
        })
        payload["hypothesis_hash"] = research_runner.canonical_hash(payload)
        return payload

    def spec(
        self,
        *,
        policy: str = "BLIND_ONCE",
        report_schema_version: int = STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
    ) -> dict[str, object]:
        hypothesis = (
            self.hypothesis()
            if report_schema_version == MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION
            else self.hypothesis_v1()
        )
        return research_runner.build_research_batch_spec(
            selection_symbols=["AAPL"],
            holdout_symbols=["ON"],
            strategies=["dual_ma"],
            position_pct=20.0,
            take_profit_pct=8.0,
            stop_loss_pct=4.0,
            fee_rate=0.0005,
            slippage_bps=2.0,
            limit=780,
            max_test_candidates=1,
            research_generation="TEST",
            selection_test_policy=policy,
            hypothesis_preregistration=hypothesis,
            report_schema_version=report_schema_version,
        )

    @staticmethod
    def _selection_alignment_fixture(
        *,
        symbol: str,
        source: str,
        rows: list[dict[str, object]],
    ) -> tuple[dict[str, object], dict[str, object]]:
        market = research_runner.research_market_for_symbol(symbol)
        engine_manifest = research_runner.prepare_backtest_dataset(
            rows,
            symbol=symbol,
            source=source,
            timeframe="1D",
            minimum_rows=1,
            market=market,
        )["manifest"]
        manifest = {
            "role": "SELECTION",
            "symbol": symbol,
            "source": source,
            "status": engine_manifest.get("status"),
            "row_count": engine_manifest.get("row_count"),
            "first": engine_manifest.get("first"),
            "last": engine_manifest.get("last"),
            "data_hash": engine_manifest.get("data_hash"),
            "data_revision_evidence": {},
            "market_history_evidence": {},
            "blockers": list(engine_manifest.get("blockers") or []),
        }
        payloads = {symbol: {"source": source, "rows": rows}}
        _aligned, alignment = align_completed_daily_payloads(payloads)
        alignment["input_snapshot"] = (
            build_strategy_selection_alignment_input_snapshot(
                payloads,
                [manifest],
            )
        )
        return manifest, alignment

    def test_batch_spec_is_deterministic_and_freezes_variants(self) -> None:
        first = self.spec()
        second = self.spec()

        self.assertEqual(first, second)
        self.assertEqual(first["workflow"], research_runner.RESEARCH_WORKFLOW)
        self.assertEqual(first["confirmation_symbols"], ["ON"])
        self.assertEqual(first["holdout_symbols"], ["ON"])
        self.assertEqual(first["split_policy"], research_runner.MATRIX_SPLIT_POLICY)
        self.assertGreater(len(first["variants"]), 1)
        self.assertEqual(first["optimizer_used"], False)
        self.assertEqual(first["research_only"], True)
        self.assertEqual(first["paper_authorized"], False)
        self.assertEqual(first["live_order_allowed"], False)

    def test_current_writer_defaults_to_schema13_v2_and_schema12_remains_v1(self) -> None:
        self.assertEqual(STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION, 13)
        arguments = {
            "selection_symbols": ["AAPL"],
            "holdout_symbols": ["ON"],
            "strategies": ["dual_ma"],
            "position_pct": 20.0,
            "take_profit_pct": 8.0,
            "stop_loss_pct": 4.0,
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "limit": 780,
            "max_test_candidates": 1,
            "research_generation": "TEST",
            "selection_test_policy": "BLIND_ONCE",
        }
        schema12 = research_runner.build_research_batch_spec(
            **arguments,
            hypothesis_preregistration=self.hypothesis_v1(),
            report_schema_version=12,
        )
        self.assertEqual(
            schema12["hypothesis_preregistration"]["schema_version"],
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
        )
        schema13 = research_runner.build_research_batch_spec(
            **arguments,
            hypothesis_preregistration=self.hypothesis(),
        )
        self.assertEqual(schema13["report_schema_version"], 13)
        self.assertEqual(
            schema13["hypothesis_preregistration"]["schema_version"],
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
        )
        with tempfile.TemporaryDirectory() as directory:
            protocol = build_strategy_matrix_protocol(
                registration_id="research-protocol-schema13-test",
                research_generation="TEST",
                batch_spec=schema13,
                implementation_manifest=build_implementation_manifest([
                    Path(research_runner.__file__)
                ]),
                exposure_audit=self._clean_exposure(["ON"]),
                registration_clock_attestation=attested_clock(1_000_000),
                expires_at_ms=4_000_000,
                registry_path=Path(directory) / "research.sqlite3",
            )
            self.assertEqual(
                verify_strategy_matrix_protocol(protocol)["status"],
                "PASS",
            )
        for report_schema, hypothesis in (
            (12, self.hypothesis()),
            (13, self.hypothesis_v1()),
        ):
            with self.subTest(report_schema=report_schema), self.assertRaisesRegex(
                ValueError,
                "schema_binding_mismatch",
            ):
                research_runner.build_research_batch_spec(
                    **arguments,
                    hypothesis_preregistration=hypothesis,
                    report_schema_version=report_schema,
                )

    def test_batch_spec_is_accepted_by_single_use_protocol_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "research.sqlite3"
            spec = self.spec()
            self.assertEqual(spec["report_schema_version"], 13)
            protocol = build_strategy_matrix_protocol(
                registration_id="research-protocol-test",
                research_generation="TEST",
                batch_spec=spec,
                implementation_manifest=build_implementation_manifest([Path(research_runner.__file__)]),
                exposure_audit=self._clean_exposure(["ON"]),
                registration_clock_attestation=attested_clock(1_000_000),
                expires_at_ms=4_000_000,
                registry_path=registry,
            )

            verification = verify_strategy_matrix_protocol(protocol)

            self.assertEqual(verification["status"], "PASS")
            self.assertEqual(verification["blockers"], [])

            schema10_spec = self.spec(report_schema_version=10)
            schema10_protocol = build_strategy_matrix_protocol(
                registration_id="research-protocol-schema10-test",
                research_generation="TEST",
                batch_spec=schema10_spec,
                implementation_manifest=build_implementation_manifest(
                    [Path(research_runner.__file__)]
                ),
                exposure_audit=self._clean_exposure(["ON"]),
                registration_clock_attestation=attested_clock(1_000_000),
                expires_at_ms=4_000_000,
                registry_path=Path(directory) / "research-schema10.sqlite3",
            )
            schema10_verification = verify_strategy_matrix_protocol(
                schema10_protocol
            )
            self.assertEqual(
                schema10_verification["status"],
                "PASS",
                schema10_verification["blockers"],
            )

            schema8_spec = self.spec(report_schema_version=8)
            schema8_protocol = build_strategy_matrix_protocol(
                registration_id="research-protocol-schema8-test",
                research_generation="TEST",
                batch_spec=schema8_spec,
                implementation_manifest=build_implementation_manifest(
                    [Path(research_runner.__file__)]
                ),
                exposure_audit=self._clean_exposure(["ON"]),
                registration_clock_attestation=attested_clock(1_000_000),
                expires_at_ms=4_000_000,
                registry_path=Path(directory) / "research-schema8.sqlite3",
            )
            schema8_verification = verify_strategy_matrix_protocol(schema8_protocol)
            self.assertEqual(
                schema8_verification["status"],
                "PASS",
                schema8_verification["blockers"],
            )

            unsupported = research_runner.json.loads(
                research_runner.json.dumps(protocol)
            )
            unsupported["batch_spec"]["report_schema_version"] = 999
            unsupported["batch_spec"].pop("hypothesis_preregistration", None)
            unsupported["batch_spec"].pop("hypothesis_preregistration_hash", None)
            unsupported["batch_spec_hash"] = research_runner.canonical_hash(
                unsupported["batch_spec"]
            )
            protocol_content = dict(unsupported)
            protocol_content.pop("protocol_hash", None)
            unsupported["protocol_hash"] = research_runner.canonical_hash(
                protocol_content
            )
            unsupported_verification = verify_strategy_matrix_protocol(unsupported)
            self.assertEqual(unsupported_verification["status"], "BLOCK")
            self.assertIn(
                "matrix_protocol_research_report_schema_invalid",
                unsupported_verification["blockers"],
            )

            missing_hypothesis = research_runner.json.loads(
                research_runner.json.dumps(protocol)
            )
            missing_hypothesis["batch_spec"].pop("hypothesis_preregistration", None)
            missing_hypothesis["batch_spec"].pop("hypothesis_preregistration_hash", None)
            missing_hypothesis["batch_spec_hash"] = research_runner.canonical_hash(
                missing_hypothesis["batch_spec"]
            )
            protocol_content = dict(missing_hypothesis)
            protocol_content.pop("protocol_hash", None)
            missing_hypothesis["protocol_hash"] = research_runner.canonical_hash(
                protocol_content
            )
            missing_verification = verify_strategy_matrix_protocol(missing_hypothesis)
            self.assertEqual(missing_verification["status"], "BLOCK")
            self.assertIn(
                "matrix_protocol_hypothesis:strategy_hypothesis_type_invalid",
                missing_verification["blockers"],
            )

    def test_falsified_strategy_cannot_create_a_new_research_spec(self) -> None:
        with patch.object(research_runner.server, "choose_strategy") as choose_strategy:
            with self.assertRaisesRegex(
                ValueError,
                "falsified_strategy_requires_new_id_and_fresh_preregistration:squeeze_breakout",
            ):
                research_runner.build_research_batch_spec(
                    selection_symbols=["AAPL"],
                    holdout_symbols=["ON"],
                    strategies=["squeeze_breakout"],
                    position_pct=20.0,
                    take_profit_pct=8.0,
                    stop_loss_pct=4.0,
                    fee_rate=0.0005,
                    slippage_bps=2.0,
                    limit=780,
                    max_test_candidates=1,
                    research_generation="NEW",
                    selection_test_policy="DEVELOPMENT_ONLY",
                )
        choose_strategy.assert_not_called()

    def test_batch_spec_rejects_overlap_and_candidate_count_drift(self) -> None:
        base = {
            "selection_symbols": ["AAPL"],
            "holdout_symbols": ["ON"],
            "strategies": ["dual_ma"],
            "position_pct": 20.0,
            "take_profit_pct": 8.0,
            "stop_loss_pct": 4.0,
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "limit": 780,
            "max_test_candidates": 1,
            "research_generation": "TEST",
            "selection_test_policy": "BLIND_ONCE",
            "hypothesis_preregistration": self.hypothesis(),
        }
        for override in (
            {"holdout_symbols": ["AAPL"]},
            {"max_test_candidates": 2},
            {"limit": 359},
        ):
            with self.subTest(override=override), self.assertRaises(ValueError):
                research_runner.build_research_batch_spec(**{**base, **override})

    def test_development_projection_removes_protected_test_rows(self) -> None:
        rows = [
            {
                "date": f"2025-01-{index + 1:02d}",
                "open": 100.0 + index,
                "high": 101.0 + index,
                "low": 99.0 + index,
                "close": 100.5 + index,
                "volume": 1_000.0 + index,
                "complete": True,
            }
            for index in range(28)
        ]
        payloads = {
            "BTC-USDT": {
                "source": "OKX_TEST",
                "rows": rows,
                "market_history_evidence": {
                    "status": "PASS",
                    "cache_manifest": {},
                    "cache_admitted": False,
                },
            },
        }
        schedule = {
            "schema_version": "calendar-split-v1",
            "status": "PASS",
            "common_start": "2025-01-01",
            "common_end": "2025-01-28",
            "train_end": "2025-01-10",
            "validation_end": "2025-01-20",
            "train_ratio": 0.5,
            "validation_ratio": 0.25,
            "minimum_segment_rows": 5,
            "symbol_boundaries": {
                "BTC-USDT": {
                    "train_end_index": 10,
                    "validation_end_index": 20,
                    "counts": {"train": 10, "validation": 10, "test": 8},
                    "row_count": 28,
                },
            },
            "blockers": [],
        }
        evidence = {
            "status": "PASS",
            "dataset_lineage_id": "dev:BTC-USDT:train-validation",
        }

        with patch.object(
            research_runner.server,
            "build_history_dataset_evidence",
            return_value=evidence,
        ) as build_evidence:
            projected, projected_schedule, projected_alignment = (
                research_runner.project_development_selection_data(
                    payloads,
                    schedule,
                    dataset_lineage_prefix="dev",
                )
            )

        self.assertEqual(len(projected["BTC-USDT"]["rows"]), 20)
        self.assertEqual(projected["BTC-USDT"]["rows"][-1]["date"], "2025-01-20")
        self.assertEqual(projected_schedule["symbol_boundaries"]["BTC-USDT"]["counts"]["test"], 0)
        self.assertEqual(projected_schedule["protected_test_rows_persisted"], False)
        self.assertEqual(projected_alignment["common_as_of"], "2025-01-20")
        self.assertEqual(build_evidence.call_args.kwargs["rows"], rows[:20])

    def test_cell_evidence_v2_seals_nested_robustness_without_changing_legacy_hash(self) -> None:
        risk = {"position_pct": 20.0, "fee_rate": 0.0005, "slippage_bps": 2.0}
        cell = {
            "phase": "TRAIN_VALIDATION_SELECTION",
            "symbol": "BTC-USDT",
            "strategy_id": "dual_ma",
            "variant_id": "dual_ma:fixture",
            "param_hash": "param-fixture",
            "dataset_hash": "dataset-fixture",
            "selection_input_end": "2025-01-01",
            "fold_stability_status": "PASS",
            "fold_stability": {
                "status": "PASS",
                "evaluation_mode": "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
                "parameters_refit_per_fold": False,
                "walk_forward_optimization_claim_allowed": False,
                "folds": [{"fold": 1, "total_return_pct": 2.0}],
            },
            "cost_sensitivity_status": "PASS",
            "cost_sensitivity": {
                "status": "PASS",
                "scenarios": [{"name": "severe", "total_return_pct": 1.0}],
            },
            "lookahead_status": "PASS",
            "lookahead_issues": [],
            "cell_evidence_schema_version": (
                LEGACY_STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION
            ),
            "test_rows_evaluated": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        legacy_hash = strategy_research_selection_cell_hash(cell, risk)
        self.assertEqual(
            legacy_hash,
            "a81e2a529a3dec320232719c893e193e764a01f6f5f47a4c4ab2c9560df507cc",
        )
        sealed_hash = strategy_research_selection_cell_hash_for_report(
            cell,
            risk,
            report_schema_version=HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
        )

        mutations = (
            lambda item: item["fold_stability"]["folds"][0].__setitem__("total_return_pct", -9.0),
            lambda item: item["cost_sensitivity"]["scenarios"][0].__setitem__("total_return_pct", -9.0),
            lambda item: item["lookahead_issues"].append("tampered"),
        )
        for mutate in mutations:
            tampered = research_runner.json.loads(research_runner.json.dumps(cell))
            mutate(tampered)
            self.assertEqual(strategy_research_selection_cell_hash(tampered, risk), legacy_hash)
            self.assertNotEqual(
                strategy_research_selection_cell_hash_for_report(
                    tampered,
                    risk,
                    report_schema_version=HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
                ),
                sealed_hash,
            )

    def test_schema8_canonicalizes_high_precision_costs_without_weakening_exact_binding(self) -> None:
        fee_rate = 0.0005123456789
        slippage_bps = 2.123456
        arguments = {
            "selection_symbols": ["AAPL"],
            "holdout_symbols": ["ON"],
            "strategies": ["dual_ma"],
            "position_pct": 20.0,
            "take_profit_pct": 8.0,
            "stop_loss_pct": 4.0,
            "fee_rate": fee_rate,
            "slippage_bps": slippage_bps,
            "limit": 780,
            "max_test_candidates": 1,
            "research_generation": "TEST",
            "selection_test_policy": "DEVELOPMENT_ONLY",
            "hypothesis_preregistration": self.hypothesis(),
        }
        current = research_runner.build_research_batch_spec(**arguments)
        legacy = research_runner.build_research_batch_spec(
            **{
                **arguments,
                "hypothesis_preregistration": self.hypothesis_v1(),
                "report_schema_version": HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
            }
        )

        expected_fee = round(fee_rate, 8)
        expected_slippage = round(slippage_bps, 4)
        self.assertEqual(current["risk"]["fee_rate"], expected_fee)
        self.assertEqual(current["risk"]["slippage_bps"], expected_slippage)
        self.assertEqual(legacy["risk"]["fee_rate"], fee_rate)
        self.assertEqual(legacy["risk"]["slippage_bps"], slippage_bps)
        for variant in current["variants"]:
            self.assertEqual(variant["risk"]["fee_rate"], expected_fee)
            self.assertEqual(variant["risk"]["slippage_bps"], expected_slippage)
            self.assertEqual(
                variant["cost_stress_contract"]["configured"]["fee_rate"],
                expected_fee,
            )
            self.assertEqual(
                variant["cost_stress_contract"]["configured"]["slippage_bps"],
                expected_slippage,
            )

        variant = current["variants"][0]
        contract = variant["cost_stress_contract"]
        baseline = {
            **contract["configured"],
            "ok": True,
            "total_return_pct": 5.0,
            "max_drawdown_pct": 4.0,
            "trade_count": 3,
        }
        scenarios = [
            {
                **scenario,
                "ok": True,
                "total_return_pct": 2.0,
                "max_drawdown_pct": 6.0,
                "trade_count": 2,
            }
            for scenario in contract["selection_scenarios"]
        ]
        evidence = research_runner.build_strategy_cost_stress_evidence(
            stage=research_runner.SELECTION_COST_STRESS_STAGE,
            risk=variant["risk"],
            baseline=baseline,
            scenarios=scenarios,
        )
        self.assertEqual(evidence["verification_status"], "PASS")

        tampered_baseline = dict(baseline)
        tampered_baseline["fee_rate"] = expected_fee + 0.00000001
        tampered_evidence = research_runner.build_strategy_cost_stress_evidence(
            stage=research_runner.SELECTION_COST_STRESS_STAGE,
            risk=variant["risk"],
            baseline=tampered_baseline,
            scenarios=scenarios,
        )
        self.assertEqual(tampered_evidence["verification_status"], "BLOCK")
        self.assertIn(
            "cost_stress_baseline_config_mismatch:fee_rate",
            tampered_evidence["integrity_blockers"],
        )

        noncanonical = research_runner.json.loads(research_runner.json.dumps(current))
        noncanonical["risk"]["fee_rate"] = fee_rate
        self.assertIn(
            "research_batch_cost_risk_not_canonical:batch",
            research_evidence._verify_current_batch_spec_contract(noncanonical),
        )

        zero_arguments = {**arguments, "fee_rate": 0.0, "slippage_bps": 0.0}
        zero_current = research_runner.build_research_batch_spec(**zero_arguments)
        zero_legacy = research_runner.build_research_batch_spec(
            **{
                **zero_arguments,
                "hypothesis_preregistration": self.hypothesis_v1(),
                "report_schema_version": HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
            }
        )
        self.assertEqual(zero_current["variants"][0]["risk"]["fee_rate"], 0.0)
        self.assertEqual(zero_current["variants"][0]["risk"]["slippage_bps"], 0.0)
        self.assertEqual(zero_legacy["variants"][0]["risk"]["fee_rate"], 0.0005)
        self.assertEqual(zero_legacy["variants"][0]["risk"]["slippage_bps"], 2.0)

    def test_schema8_negative_cost_drawdowns_block_selection_and_test_evidence(self) -> None:
        risk = {
            "position_pct": 20.0,
            "take_profit_pct": 0.0,
            "stop_loss_pct": 8.0,
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "leverage": 1.0,
        }
        contract = research_runner.build_strategy_cost_stress_contract(risk)
        stages = (
            (
                research_runner.SELECTION_COST_STRESS_STAGE,
                contract["selection_scenarios"],
                "research_selection_cost_evidence_integrity_blocked:dual_ma:fixture:SYNTH",
            ),
            (
                research_runner.FROZEN_TEST_COST_STRESS_STAGE,
                contract["frozen_test_scenarios"],
                "research_test_cost_evidence_integrity_blocked:dual_ma:fixture:SYNTH",
            ),
        )
        for stage, configured_scenarios, expected_verifier_blocker in stages:
            for invalid_target in ("baseline", "scenario"):
                with self.subTest(stage=stage, invalid_target=invalid_target):
                    baseline = {
                        **contract["configured"],
                        "ok": True,
                        "total_return_pct": 5.0,
                        "max_drawdown_pct": 4.0,
                        "trade_count": 3,
                    }
                    scenarios = [
                        {
                            **scenario,
                            "ok": True,
                            "total_return_pct": 2.0,
                            "max_drawdown_pct": 6.0,
                            "trade_count": 2,
                        }
                        for scenario in configured_scenarios
                    ]
                    if invalid_target == "baseline":
                        baseline["max_drawdown_pct"] = -0.01
                        expected_integrity_blocker = "cost_stress_baseline_metrics_invalid"
                    else:
                        scenarios[0]["max_drawdown_pct"] = -0.01
                        expected_integrity_blocker = (
                            f"cost_stress_scenario_metrics_invalid:{scenarios[0]['name']}"
                        )
                    evidence = research_runner.build_strategy_cost_stress_evidence(
                        stage=stage,
                        risk=risk,
                        baseline=baseline,
                        scenarios=scenarios,
                    )
                    self.assertEqual(evidence["verification_status"], "BLOCK")
                    self.assertIn(
                        expected_integrity_blocker,
                        evidence["integrity_blockers"],
                    )

                    if stage == research_runner.SELECTION_COST_STRESS_STAGE:
                        cell = {
                            "cell_evidence_schema_version": (
                                research_runner.STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION
                            ),
                            "fold_stability_status": "BLOCK",
                            "fold_stability": {"status": "BLOCK"},
                            "cost_sensitivity_status": evidence["status"],
                            "cost_sensitivity": evidence,
                            "lookahead_status": "PASS",
                            "lookahead_issues": [],
                            "validation_ok": baseline["ok"],
                            "validation_return_pct": baseline["total_return_pct"],
                            "validation_max_drawdown_pct": baseline["max_drawdown_pct"],
                            "validation_trade_count": baseline["trade_count"],
                            "test_rows_evaluated": False,
                            "research_only": True,
                            "paper_authorized": False,
                            "live_order_allowed": False,
                        }
                        verifier_blockers = research_evidence._verify_selection_cell_evidence_v3(
                            cell,
                            variant_id="dual_ma:fixture",
                            symbol="SYNTH",
                            risk=risk,
                        )
                    else:
                        cell = {
                            "test_cell_evidence_schema_version": (
                                research_runner.STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION
                            ),
                            "cost_stress_evidence": evidence,
                            "test_cost_status": evidence["status"],
                            "test_ok": baseline["ok"],
                            "test_return_pct": baseline["total_return_pct"],
                            "test_max_drawdown_pct": baseline["max_drawdown_pct"],
                            "test_trade_count": baseline["trade_count"],
                            "test_severe_cost_return_pct": scenarios[0]["total_return_pct"],
                            "research_only": True,
                            "paper_authorized": False,
                            "live_order_allowed": False,
                        }
                        verifier_blockers = research_evidence._verify_test_cell_evidence_v1(
                            cell,
                            variant_id="dual_ma:fixture",
                            symbol="SYNTH",
                            risk=risk,
                        )
                    self.assertIn(expected_verifier_blocker, verifier_blockers)

        valid_cost = research_runner.build_strategy_cost_stress_evidence(
            stage=research_runner.SELECTION_COST_STRESS_STAGE,
            risk=risk,
            baseline={
                **contract["configured"],
                "ok": True,
                "total_return_pct": 5.0,
                "max_drawdown_pct": 4.0,
                "trade_count": 3,
            },
            scenarios=[
                {
                    **scenario,
                    "ok": True,
                    "total_return_pct": 2.0,
                    "max_drawdown_pct": 6.0,
                    "trade_count": 2,
                }
                for scenario in contract["selection_scenarios"]
            ],
        )
        negative_fold_cell = {
            "cell_evidence_schema_version": (
                research_runner.STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION
            ),
            "fold_stability_status": "PASS",
            "fold_stability": {
                "status": "PASS",
                "evaluation_mode": "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
                "parameters_refit_per_fold": False,
                "walk_forward_optimization_claim_allowed": False,
                "fold_count": 1,
                "usable_folds": 1,
                "positive_folds": 1,
                "total_trades": 2,
                "worst_drawdown_pct": -0.01,
                "folds": [{
                    "fold": 1,
                    "ok": True,
                    "total_return_pct": 2.0,
                    "max_drawdown_pct": -0.01,
                    "trade_count": 2,
                }],
            },
            "cost_sensitivity_status": valid_cost["status"],
            "cost_sensitivity": valid_cost,
            "lookahead_status": "PASS",
            "lookahead_issues": [],
            "validation_ok": True,
            "validation_return_pct": 5.0,
            "validation_max_drawdown_pct": 4.0,
            "validation_trade_count": 3,
            "test_rows_evaluated": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        fold_blockers = research_evidence._verify_selection_cell_evidence_v3(
            negative_fold_cell,
            variant_id="dual_ma:fixture",
            symbol="SYNTH",
            risk=risk,
        )
        self.assertIn(
            "research_selection_fold_drawdown_negative:dual_ma:fixture:SYNTH:1",
            fold_blockers,
        )

    def test_schema8_test_cost_evidence_rejects_resealed_severe_return(self) -> None:
        risk = {
            "position_pct": 20.0,
            "take_profit_pct": 0.0,
            "stop_loss_pct": 8.0,
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "leverage": 1.0,
        }
        contract = research_runner.build_strategy_cost_stress_contract(risk)
        severe_contract = dict(contract["frozen_test_scenarios"][0])
        baseline = {
            "name": "configured",
            "ok": True,
            "fee_rate": risk["fee_rate"],
            "slippage_bps": risk["slippage_bps"],
            "total_return_pct": 5.0,
            "max_drawdown_pct": 4.0,
            "trade_count": 3,
        }
        evidence = research_runner.build_strategy_cost_stress_evidence(
            stage=research_runner.FROZEN_TEST_COST_STRESS_STAGE,
            risk=risk,
            baseline=baseline,
            scenarios=[{
                **severe_contract,
                "ok": True,
                "total_return_pct": -99.0,
                "max_drawdown_pct": 20.0,
                "trade_count": 2,
            }],
        )
        cell: dict[str, object] = {
            "phase": "FROZEN_TEST_ONCE",
            "symbol": "SYNTH",
            "strategy_id": "dual_ma",
            "variant_id": "dual_ma:fixture",
            "params": {},
            "param_hash": "param-fixture",
            "implementation_fingerprint": "implementation-fixture",
            "dataset_status": "PASS",
            "dataset_hash": "dataset-fixture",
            "test_ok": True,
            "test_start": "2025-01-01",
            "test_end": "2025-03-01",
            "test_return_pct": 5.0,
            "test_excess_return_pct": 1.0,
            "test_trade_count": 3,
            "test_max_drawdown_pct": 4.0,
            "test_drawdown_improvement_pct": 1.0,
            "test_sharpe_excess": 0.1,
            "test_risk_efficiency_excess": 0.1,
            "test_severe_cost_return_pct": -99.0,
            "test_cost_status": "BLOCK",
            "test_cell_evidence_schema_version": (
                research_runner.STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION
            ),
            "cost_stress_evidence": evidence,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        cell["run_hash"] = strategy_research_test_cell_hash_for_report(
            cell,
            risk,
            report_schema_version=research_runner.COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
        )
        self.assertEqual(
            research_evidence._verify_test_cell_evidence_v1(
                cell,
                variant_id="dual_ma:fixture",
                symbol="SYNTH",
                risk=risk,
            ),
            [],
        )

        resealed = research_runner.json.loads(research_runner.json.dumps(cell))
        resealed["cost_stress_evidence"]["scenarios"][0]["total_return_pct"] = 999.0
        resealed["cost_stress_evidence"] = research_runner.build_strategy_cost_stress_evidence(
            stage=research_runner.FROZEN_TEST_COST_STRESS_STAGE,
            risk=risk,
            baseline=resealed["cost_stress_evidence"]["baseline"],
            scenarios=resealed["cost_stress_evidence"]["scenarios"],
        )
        resealed["test_cost_status"] = "PASS"
        resealed["run_hash"] = strategy_research_test_cell_hash_for_report(
            resealed,
            risk,
            report_schema_version=research_runner.COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
        )
        blockers = research_evidence._verify_test_cell_evidence_v1(
            resealed,
            variant_id="dual_ma:fixture",
            symbol="SYNTH",
            risk=risk,
        )
        self.assertIn(
            "research_test_severe_return_mismatch:dual_ma:fixture:SYNTH",
            blockers,
        )
        self.assertNotEqual(
            strategy_research_test_cell_hash(resealed, risk),
            resealed["run_hash"],
        )

    def test_schema9_fixed_slice_evidence_rejects_coherently_resealed_topology(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        rows = [
            {
                "date": (start + timedelta(days=index)).date().isoformat(),
                "ts_ms": int((start + timedelta(days=index)).timestamp() * 1000),
                "open": 100.0 + index,
                "high": 101.0 + index,
                "low": 99.0 + index,
                "close": 100.5 + index,
                "volume": 1_000.0 + index,
                "complete": True,
                "complete_attested": True,
                "source": "OKX_TEST",
            }
            for index in range(12)
        ]
        risk = research_runner.normalize_strategy_cost_risk({
            "position_pct": 20.0,
            "take_profit_pct": 8.0,
            "stop_loss_pct": 4.0,
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "leverage": 1.0,
        })
        plan = research_runner.chronological_folds(
            rows,
            fold_count=3,
            minimum_fold_rows=4,
        )

        def reports_for(plans: list[dict[str, object]]) -> list[dict[str, object]]:
            return [
                {
                    "fold": item.get("fold"),
                    "start": item.get("start"),
                    "end": item.get("end"),
                    "ok": True,
                    "total_return_pct": 1.0,
                    "max_drawdown_pct": 3.0,
                    "trade_count": 3,
                }
                for item in plans
            ]

        def build(plans: list[dict[str, object]]) -> dict[str, object]:
            return research_runner.build_fixed_chronological_slice_evidence(
                selection_rows=rows,
                symbol="BTC-USDT",
                source="SYNTHETIC",
                market="crypto",
                timeframe="1D",
                fold_plans=plans,
                fold_reports=reports_for(plans),
                minimum_fold_rows=4,
            )

        valid_evidence = build(list(plan["folds"]))
        cost_contract = research_runner.build_strategy_cost_stress_contract(risk)
        cost_evidence = research_runner.build_strategy_cost_stress_evidence(
            stage=research_runner.SELECTION_COST_STRESS_STAGE,
            risk=risk,
            baseline={
                "name": "configured",
                "ok": True,
                "fee_rate": risk["fee_rate"],
                "slippage_bps": risk["slippage_bps"],
                "total_return_pct": 5.0,
                "max_drawdown_pct": 5.0,
                "trade_count": 4,
            },
            scenarios=[
                {
                    **dict(scenario),
                    "ok": True,
                    "total_return_pct": 2.0,
                    "max_drawdown_pct": 7.0,
                    "trade_count": 3,
                }
                for scenario in cost_contract["selection_scenarios"]
            ],
        )
        cell: dict[str, object] = {
            "phase": "TRAIN_VALIDATION_SELECTION",
            "symbol": "BTC-USDT",
            "strategy_id": "dual_ma",
            "variant_id": "dual_ma:fixture",
            "params": {},
            "param_hash": "param-fixture",
            "implementation_fingerprint": "implementation-fixture",
            "dataset_status": "PASS",
            "dataset_hash": valid_evidence["selection_prefix"]["data_hash"],
            "selection_input_rows": len(rows),
            "selection_input_end": rows[-1]["date"],
            "test_rows_evaluated": False,
            "validation_ok": True,
            "validation_return_pct": 5.0,
            "validation_max_drawdown_pct": 5.0,
            "validation_trade_count": 4,
            "fold_stability_status": "PASS",
            "fold_stability": valid_evidence,
            "cost_sensitivity_status": cost_evidence["status"],
            "cost_sensitivity": cost_evidence,
            "lookahead_status": "PASS",
            "lookahead_issues": [],
            "cell_evidence_schema_version": (
                research_runner.STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V4
            ),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

        def verify(candidate: dict[str, object]) -> list[str]:
            candidate["run_hash"] = strategy_research_selection_cell_hash_for_report(
                candidate,
                risk,
                report_schema_version=(
                    research_runner.LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
                ),
            )
            return research_evidence._verify_selection_cell_evidence_v4(
                candidate,
                variant_id="dual_ma:fixture",
                symbol="BTC-USDT",
                risk=risk,
                selection_rows=rows,
                source="SYNTHETIC",
                market="crypto",
            )

        self.assertEqual(verify(cell), [])

        plans = [research_runner.deepcopy(item) for item in plan["folds"]]
        duplicate = [research_runner.deepcopy(item) for item in plans]
        duplicate[1] = research_runner.deepcopy(duplicate[0])
        duplicate[1]["fold"] = 2
        reordered = [research_runner.deepcopy(item) for item in reversed(plans)]
        overlap = [research_runner.deepcopy(item) for item in plans]
        overlap[1].update({
            "start_index": 3,
            "end_index": 8,
            "count": 5,
            "start": rows[3]["date"],
            "end": rows[7]["date"],
        })
        gap = [research_runner.deepcopy(item) for item in plans]
        gap[1].update({
            "start_index": 5,
            "end_index": 8,
            "count": 3,
            "start": rows[5]["date"],
            "end": rows[7]["date"],
        })

        attacked_evidence: dict[str, dict[str, object]] = {
            "duplicate_window": build(duplicate),
            "reordered": build(reordered),
            "overlap": build(overlap),
            "gap": build(gap),
            "fold_identity_hash": research_runner.deepcopy(valid_evidence),
        }
        attacked_evidence["fold_identity_hash"]["folds"][1]["dataset_identity"][
            "data_hash"
        ] = "f" * 64

        for name, evidence in attacked_evidence.items():
            with self.subTest(name=name):
                evidence["verification_status"] = "PASS"
                evidence["status"] = "PASS"
                evidence["integrity_blockers"] = []
                evidence["outcome_blockers"] = []
                evidence["blockers"] = []
                content = dict(evidence)
                content.pop("evidence_hash", None)
                evidence["evidence_hash"] = research_runner.canonical_hash(content)
                attacked = research_runner.deepcopy(cell)
                attacked["fold_stability"] = evidence
                attacked["fold_stability_status"] = "PASS"
                blockers = verify(attacked)
                self.assertTrue(any(
                    item.startswith("research_selection_fold_evidence_")
                    for item in blockers
                ), blockers)

        malformed_reports: dict[str, tuple[str, object, str]] = {
            "return_nan": (
                "total_return_pct",
                float("nan"),
                "chronological_fold_result_return_invalid:1",
            ),
            "drawdown_infinite": (
                "max_drawdown_pct",
                float("inf"),
                "chronological_fold_result_drawdown_invalid:1",
            ),
            "trade_count_bool": (
                "trade_count",
                True,
                "chronological_fold_result_trade_count_invalid:1",
            ),
            "drawdown_negative": (
                "max_drawdown_pct",
                -1.0,
                "chronological_fold_result_drawdown_invalid:1",
            ),
            "trade_count_negative": (
                "trade_count",
                -1,
                "chronological_fold_result_trade_count_invalid:1",
            ),
            "ok_truthy_string": (
                "ok",
                "true",
                "chronological_fold_result_ok_type_invalid:1",
            ),
        }
        for name, (field, value, expected_blocker) in malformed_reports.items():
            with self.subTest(name=name):
                malformed = reports_for(list(plan["folds"]))
                malformed[0][field] = value
                evidence = research_runner.build_fixed_chronological_slice_evidence(
                    selection_rows=rows,
                    symbol="BTC-USDT",
                    source="SYNTHETIC",
                    market="crypto",
                    timeframe="1D",
                    fold_plans=list(plan["folds"]),
                    fold_reports=malformed,
                    minimum_fold_rows=4,
                )
                self.assertEqual(evidence["verification_status"], "BLOCK")
                self.assertEqual(evidence["status"], "BLOCK")
                self.assertIn(expected_blocker, evidence["integrity_blockers"])
                attacked = research_runner.deepcopy(cell)
                attacked["fold_stability"] = evidence
                attacked["fold_stability_status"] = "BLOCK"
                blockers = verify(attacked)
                self.assertTrue(
                    any(item.startswith((
                        "research_selection_fold_evidence_integrity_blocked:",
                        "research_selection_fold_evidence_semantic_mismatch:",
                    )) for item in blockers),
                    blockers,
                )

        self.assertEqual(
            research_evidence.strategy_research_selection_cell_hash_v2(cell, risk),
            strategy_research_selection_cell_hash_for_report(
                cell,
                risk,
                report_schema_version=5,
            ),
        )
        self.assertEqual(
            research_evidence.strategy_research_selection_cell_hash_v3(cell, risk),
            strategy_research_selection_cell_hash_for_report(
                cell,
                risk,
                report_schema_version=8,
            ),
        )
        stable_cell = {
            key: value
            for key, value in cell.items()
            if key not in {"run_hash", "elapsed_ms"}
        }
        self.assertEqual(
            research_evidence.strategy_research_selection_cell_hash_v3(cell, risk),
            research_runner.canonical_hash({
                "cell_evidence_schema_version": (
                    "strategy-research-selection-cell-evidence-v3"
                ),
                "report_schema_version": 8,
                "cell": stable_cell,
                "risk": risk,
                "execution_model": research_runner.EXECUTION_MODEL_VERSION,
            }),
        )
        self.assertEqual(
            research_evidence.strategy_research_test_cell_hash_v2({}, risk),
            strategy_research_test_cell_hash_for_report(
                {},
                risk,
                report_schema_version=8,
            ),
        )

    def test_schema10_replays_fold_results_and_rejects_coherent_999_reseal(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        rows = [
            {
                "date": (start + timedelta(days=index)).date().isoformat(),
                "ts_ms": int((start + timedelta(days=index)).timestamp() * 1000),
                "open": 100.0 + index * 0.1,
                "high": 101.0 + index * 0.1,
                "low": 99.0 + index * 0.1,
                "close": 100.5 + index * 0.1,
                "volume": 1_000.0 + index,
                "complete": True,
                "complete_attested": True,
                "source": "SYNTHETIC",
            }
            for index in range(360)
        ]
        params = {"fast": 5, "slow": 20}
        param_hash = research_runner.canonical_hash(params)
        risk = research_runner.normalize_strategy_cost_risk({
            "position_pct": 20.0,
            "take_profit_pct": 8.0,
            "stop_loss_pct": 4.0,
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "leverage": 1.0,
        })
        evidence = research_runner.build_fixed_chronological_slice_evidence_v2(
            selection_rows=rows,
            symbol="BTC-USDT",
            source="OKX_TEST",
            market="crypto",
            timeframe="1D",
            strategy_id="dual_ma",
            params=params,
            param_hash=param_hash,
            risk=risk,
        )
        cost_contract = research_runner.build_strategy_cost_stress_contract(risk)
        cost_evidence = research_runner.build_strategy_cost_stress_evidence(
            stage=research_runner.SELECTION_COST_STRESS_STAGE,
            risk=risk,
            baseline={
                "name": "configured", "ok": True,
                "fee_rate": risk["fee_rate"], "slippage_bps": risk["slippage_bps"],
                "total_return_pct": 5.0, "max_drawdown_pct": 5.0, "trade_count": 4,
            },
            scenarios=[
                {**dict(item), "ok": True, "total_return_pct": 2.0,
                 "max_drawdown_pct": 7.0, "trade_count": 3}
                for item in cost_contract["selection_scenarios"]
            ],
        )
        cell: dict[str, object] = {
            "phase": "TRAIN_VALIDATION_SELECTION", "symbol": "BTC-USDT",
            "strategy_id": "dual_ma", "variant_id": "dual_ma:fixture",
            "params": params, "param_hash": param_hash,
            "implementation_fingerprint": "implementation-fixture",
            "dataset_status": "PASS",
            "dataset_hash": evidence["selection_prefix"]["data_hash"],
            "selection_input_rows": len(rows), "selection_input_end": rows[-1]["date"],
            "test_rows_evaluated": False, "validation_ok": True,
            "validation_return_pct": 5.0, "validation_max_drawdown_pct": 5.0,
            "validation_trade_count": 4, "fold_stability_status": evidence["status"],
            "fold_stability": evidence, "cost_sensitivity_status": cost_evidence["status"],
            "cost_sensitivity": cost_evidence, "lookahead_status": "PASS",
            "lookahead_issues": [],
            "cell_evidence_schema_version": research_evidence.STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION,
            "research_only": True, "paper_authorized": False, "live_order_allowed": False,
        }
        selection_replay = research_runner.build_strategy_selection_replay_evidence(
            selection_rows=rows,
            train_end_index=180,
            symbol="BTC-USDT",
            source="OKX_TEST",
            market="crypto",
            timeframe="1D",
            variant_id="dual_ma:fixture",
            strategy_id="dual_ma",
            params=params,
            param_hash=param_hash,
            implementation_fingerprint="implementation-fixture",
            risk=risk,
        )
        cell.update(selection_replay["flat_metric_projection"])
        cell["selection_replay"] = selection_replay

        def verify(candidate: dict[str, object]) -> list[str]:
            candidate["run_hash"] = strategy_research_selection_cell_hash_for_report(
                candidate,
                risk,
                report_schema_version=(
                    research_runner.FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
                ),
            )
            return research_evidence._verify_selection_cell_evidence_v5(
                candidate, variant_id="dual_ma:fixture", symbol="BTC-USDT",
                implementation_fingerprint="implementation-fixture",
                strategy_id="dual_ma", params=params, param_hash=param_hash, risk=risk,
                selection_rows=rows, train_end_index=180,
                source="OKX_TEST", market="crypto",
            )

        self.assertEqual(verify(cell), [])

        def reseal(candidate: dict[str, object]) -> None:
            result_content = dict(
                candidate["fold_stability"]["folds"][0]["result_projection"]
            )
            result_content.pop("result_hash", None)
            candidate["fold_stability"]["folds"][0]["result_projection"][
                "result_hash"
            ] = research_runner.canonical_hash(result_content)
            evidence_content = dict(candidate["fold_stability"])
            evidence_content.pop("evidence_hash", None)
            candidate["fold_stability"]["evidence_hash"] = research_runner.canonical_hash(
                evidence_content
            )

        attacks = {}
        attacked = research_runner.deepcopy(cell)
        fold = attacked["fold_stability"]["folds"][0]
        fold["total_return_pct"] = 999.0
        fold["trade_count"] = 999
        fold["result_projection"]["total_return_pct"] = 999.0
        fold["result_projection"]["trade_count"] = 999
        reseal(attacked)
        attacks["metrics_999"] = attacked
        for digest_field in ("equity_curve_hash", "trades_hash"):
            attacked = research_runner.deepcopy(cell)
            attacked["fold_stability"]["folds"][0]["result_projection"][digest_field] = "f" * 64
            reseal(attacked)
            attacks[digest_field] = attacked
        attacked = research_runner.deepcopy(cell)
        attacked["fold_stability"]["fold_policy"]["fold_count"] = 4
        reseal(attacked)
        attacks["fold_policy"] = attacked
        for name, attacked in attacks.items():
            with self.subTest(name=name):
                self.assertIn(
                    "research_selection_fold_result_semantic_mismatch:dual_ma:fixture:BTC-USDT",
                    verify(attacked),
                )

        def seal_result(result: dict[str, object]) -> None:
            content = dict(result)
            content.pop("result_hash", None)
            result["result_hash"] = research_runner.canonical_hash(content)

        def seal_selection(candidate: dict[str, object]) -> None:
            replay = candidate["selection_replay"]
            content = dict(replay)
            content.pop("evidence_hash", None)
            replay["evidence_hash"] = research_runner.canonical_hash(content)

        selection_attacks: dict[str, dict[str, object]] = {}
        attacked = research_runner.deepcopy(cell)
        replay = attacked["selection_replay"]
        validation = replay["validation_run"]["result_projection"]
        validation["total_return_pct"] = 999.0
        validation["trade_count"] = 999
        seal_result(validation)
        for cost_run in replay["cost_runs"]:
            cost_result = cost_run["result_projection"]
            cost_result["total_return_pct"] = 999.0
            cost_result["trade_count"] = 999
            seal_result(cost_result)
        replay["cost_sensitivity"] = (
            research_runner.build_strategy_cost_stress_evidence(
                stage=research_runner.SELECTION_COST_STRESS_STAGE,
                risk=risk,
                baseline=research_runner.project_cost_stress_observation(
                    "configured", validation
                ),
                scenarios=[
                    research_runner.project_cost_stress_observation(
                        cost_run["name"], cost_run["result_projection"]
                    )
                    for cost_run in replay["cost_runs"]
                ],
            )
        )
        flat = dict(replay["flat_metric_projection"])
        benchmark = replay["benchmark_run"]["result_projection"]
        benchmark_return = float(benchmark["total_return_pct"])
        validation_drawdown = float(validation["max_drawdown_pct"])
        benchmark_drawdown = float(benchmark["max_drawdown_pct"])
        validation_efficiency = 999.0 / max(validation_drawdown, 1.0)
        benchmark_efficiency = benchmark_return / max(benchmark_drawdown, 1.0)
        flat.update({
            "validation_return_pct": 999.0,
            "validation_trade_count": 999,
            "validation_excess_return_pct": round(999.0 - benchmark_return, 4),
            "validation_return_drawdown_efficiency": round(
                validation_efficiency, 6
            ),
            "validation_risk_efficiency_excess": round(
                validation_efficiency - benchmark_efficiency, 6
            ),
            "cost_sensitivity_status": replay["cost_sensitivity"]["status"],
            "cost_sensitivity": replay["cost_sensitivity"],
        })
        replay["flat_metric_projection"] = flat
        attacked.update(flat)
        seal_selection(attacked)
        selection_attacks["configured_and_cost_999"] = attacked

        attacked = research_runner.deepcopy(cell)
        replay = attacked["selection_replay"]
        replay["train_run"]["result_projection"]["total_return_pct"] = 999.0
        seal_result(replay["train_run"]["result_projection"])
        replay["flat_metric_projection"]["train_return_pct"] = 999.0
        attacked["train_return_pct"] = 999.0
        seal_selection(attacked)
        selection_attacks["train_999"] = attacked

        attacked = research_runner.deepcopy(cell)
        replay = attacked["selection_replay"]
        replay["validation_run"]["result_projection"]["equity_curve_hash"] = "e" * 64
        seal_result(replay["validation_run"]["result_projection"])
        seal_selection(attacked)
        selection_attacks["validation_curve_digest"] = attacked

        attacked = research_runner.deepcopy(cell)
        replay = attacked["selection_replay"]
        replay["lookahead"]["score"] = 100.0
        lookahead_content = dict(replay["lookahead"])
        lookahead_content.pop("lookahead_hash", None)
        replay["lookahead"]["lookahead_hash"] = research_runner.canonical_hash(
            lookahead_content
        )
        seal_selection(attacked)
        selection_attacks["lookahead"] = attacked

        for name, attacked in selection_attacks.items():
            with self.subTest(name=name):
                self.assertIn(
                    "research_selection_replay_semantic_mismatch:dual_ma:fixture:BTC-USDT",
                    verify(attacked),
                )

    def test_schema10_formal_rebuilds_calendar_split_before_selecting_replay_rows(self) -> None:
        start = datetime(2023, 1, 1, tzinfo=timezone.utc)
        rows = [
            {
                "date": (start + timedelta(days=index)).date().isoformat(),
                "ts_ms": int((start + timedelta(days=index)).timestamp() * 1000),
                "open": 100.0 + index * 0.01,
                "high": 101.0 + index * 0.01,
                "low": 99.0 + index * 0.01,
                "close": 100.5 + index * 0.01,
                "volume": 1_000.0 + index,
                "complete": True,
                "complete_attested": True,
            }
            for index in range(780)
        ]
        batch_spec = self.spec()
        expected_schedule = research_runner.build_calendar_split_schedule(
            {"AAPL": {"rows": rows}},
            **{
                "train_ratio": batch_spec["split_policy"]["train_ratio"],
                "validation_ratio": batch_spec["split_policy"]["validation_ratio"],
                "minimum_segment_rows": batch_spec["split_policy"][
                    "minimum_segment_rows"
                ],
            },
        )
        self.assertEqual(expected_schedule["status"], "PASS")
        attacked_schedule = research_runner.deepcopy(expected_schedule)
        attacked_boundary = attacked_schedule["symbol_boundaries"]["AAPL"]
        attacked_boundary["validation_end_index"] = len(rows)
        attacked_boundary["counts"]["validation"] = (
            len(rows) - attacked_boundary["train_end_index"]
        )
        attacked_boundary["counts"]["test"] = 0
        attacked_schedule["validation_end"] = rows[-1]["date"]
        expected_validation_end = expected_schedule["symbol_boundaries"]["AAPL"][
            "validation_end_index"
        ]
        variant = batch_spec["variants"][0]
        fold_evidence = {
            "schema_version": (
                research_evidence.STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION_V2
            ),
            "verification_status": "PASS",
            "status": "BLOCK",
            "evaluation_mode": "FIXED_PARAMETER_CHRONOLOGICAL_SLICES_REPLAYED",
            "selection_prefix": {},
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        cell = {
            "phase": "TRAIN_VALIDATION_SELECTION",
            "symbol": "AAPL",
            "strategy_id": variant["strategy_id"],
            "variant_id": variant["variant_id"],
            "params": variant["params"],
            "param_hash": variant["param_hash"],
            "implementation_fingerprint": variant["implementation_fingerprint"],
            "cell_evidence_schema_version": (
                research_evidence.STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V5
            ),
            "fold_stability": fold_evidence,
            "fold_stability_status": "BLOCK",
            "cost_sensitivity": {},
            "cost_sensitivity_status": "BLOCK",
            "lookahead_issues": [],
            "lookahead_status": "PASS",
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        selection_manifest, selection_alignment = self._selection_alignment_fixture(
            symbol="AAPL",
            source="UNIT_TEST",
            rows=rows,
        )
        report = {
            "schema_version": (
                research_runner.FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
            ),
            "dataset_manifest": [selection_manifest],
            "dataset_snapshot": {
                "datasets": [{
                    "role": "SELECTION",
                    "symbol": "AAPL",
                    "source": "UNIT_TEST",
                    "market": "stock",
                    "timeframe": "1D",
                    "rows": rows,
                }],
            },
            "selection_calendar_schedule": attacked_schedule,
            "selection_alignment": selection_alignment,
            "selection_cells": [cell],
            "validation_rankings": [],
            "parameter_stability": research_runner.build_parameter_stability_snapshot(
                [],
                frozen_variants=batch_spec["variants"],
            ),
            "validation_candidates": [],
            "frozen_candidates": [],
            "test_cells": [],
            "test_results": [],
            "holdout_alignment": {"status": "BLOCK"},
            "holdout_cells": [],
            "holdout_results": [],
            "forward_candidates": [],
        }
        replay_row_counts: list[int] = []

        def capture_replay_rows(**kwargs: object) -> dict[str, object]:
            replay_row_counts.append(len(kwargs["selection_rows"]))
            return research_runner.deepcopy(fold_evidence)

        with patch.object(
            research_evidence,
            "build_fixed_chronological_slice_evidence_v2",
            side_effect=capture_replay_rows,
        ):
            blockers = research_evidence._verify_research_semantics(
                report,
                batch_spec=batch_spec,
                formal=True,
            )
        self.assertIn(
            "research_selection_calendar_schedule_semantic_mismatch",
            blockers,
        )
        self.assertEqual(replay_row_counts, [expected_validation_end])
        self.assertLess(expected_validation_end, len(rows))

    def test_schema10_selection_runner_uses_pure_replay_not_server_backtest(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        rows = [
            {
                "date": (start + timedelta(days=index)).date().isoformat(),
                "ts_ms": int((start + timedelta(days=index)).timestamp() * 1000),
                "open": 100.0 + index * 0.1,
                "high": 101.0 + index * 0.1,
                "low": 99.0 + index * 0.1,
                "close": 100.5 + index * 0.1,
                "volume": 1_000.0 + index,
                "complete": True,
                "complete_attested": True,
            }
            for index in range(360)
        ]
        variant = dict(self.spec()["variants"][0])
        risk = dict(variant["risk"])
        boundaries = {
            "train_end_index": 180,
            "validation_end_index": len(rows),
        }
        with patch.object(
            research_runner.server,
            "run_strategy_backtest",
            side_effect=AssertionError("schema10_must_not_use_server_backtest"),
        ):
            cell = research_runner.run_selection_cell(
                symbol="BTC-USDC",
                variant=variant,
                payload={"source": "OKX_TEST", "rows": rows},
                risk=risk,
                boundaries=boundaries,
                report_schema_version=(
                    research_runner.FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
                ),
            )
        expected = research_runner.build_strategy_selection_replay_evidence(
            selection_rows=rows,
            train_end_index=180,
            symbol="BTC-USDC",
            source="OKX_TEST",
            market="crypto",
            timeframe="1D",
            variant_id=str(variant["variant_id"]),
            strategy_id=str(variant["strategy_id"]),
            params=dict(variant["params"]),
            param_hash=str(variant["param_hash"]),
            implementation_fingerprint=str(variant["implementation_fingerprint"]),
            risk=risk,
        )
        self.assertEqual(cell["selection_replay"], expected)
        for field, expected_value in expected["flat_metric_projection"].items():
            self.assertEqual(cell[field], expected_value, field)
        self.assertEqual(
            research_evidence._verify_selection_cell_evidence_v5(
                cell,
                variant_id=str(variant["variant_id"]),
                symbol="BTC-USDC",
                implementation_fingerprint=str(
                    variant["implementation_fingerprint"]
                ),
                strategy_id=str(variant["strategy_id"]),
                params=dict(variant["params"]),
                param_hash=str(variant["param_hash"]),
                risk=risk,
                selection_rows=rows,
                train_end_index=180,
                source="OKX_TEST",
                market="crypto",
            ),
            [],
        )

    def test_schema10_development_rebuilds_train_boundary_before_selection_replay(self) -> None:
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        rows = [
            {
                "date": (start + timedelta(days=index)).date().isoformat(),
                "ts_ms": int((start + timedelta(days=index)).timestamp() * 1000),
                "open": 100.0 + index * 0.01,
                "high": 101.0 + index * 0.01,
                "low": 99.0 + index * 0.01,
                "close": 100.5 + index * 0.01,
                "volume": 1_000.0 + index,
                "complete": True,
                "complete_attested": True,
            }
            for index in range(600)
        ]
        batch_spec = self.spec(policy="DEVELOPMENT_ONLY")
        split_policy = batch_spec["split_policy"]
        expected_schedule = research_runner.build_development_selection_prefix_schedule(
            {"AAPL": {"rows": rows}},
            train_ratio=split_policy["train_ratio"],
            validation_ratio=split_policy["validation_ratio"],
            minimum_segment_rows=split_policy["minimum_segment_rows"],
        )
        self.assertEqual(expected_schedule["status"], "PASS")
        expected_train_end = expected_schedule["symbol_boundaries"]["AAPL"][
            "train_end_index"
        ]
        attacked_schedule = research_runner.deepcopy(expected_schedule)
        attacked_boundary = attacked_schedule["symbol_boundaries"]["AAPL"]
        attacked_boundary["train_end_index"] = expected_train_end + 1
        attacked_boundary["train_end_date"] = rows[expected_train_end]["date"]
        attacked_boundary["counts"]["train"] = expected_train_end + 1
        attacked_boundary["counts"]["validation"] = len(rows) - expected_train_end - 1

        variant = batch_spec["variants"][0]
        fold_evidence = {
            "schema_version": (
                research_evidence.STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION_V2
            ),
            "verification_status": "PASS",
            "status": "BLOCK",
            "evaluation_mode": "FIXED_PARAMETER_CHRONOLOGICAL_SLICES_REPLAYED",
            "selection_prefix": {},
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        replay_evidence = {
            "schema_version": research_evidence.STRATEGY_SELECTION_REPLAY_SCHEMA_VERSION,
            "verification_status": "PASS",
            "status": "BLOCK",
            "flat_metric_projection": {},
        }
        cell = {
            "phase": "TRAIN_VALIDATION_SELECTION",
            "symbol": "AAPL",
            "strategy_id": variant["strategy_id"],
            "variant_id": variant["variant_id"],
            "params": variant["params"],
            "param_hash": variant["param_hash"],
            "implementation_fingerprint": variant["implementation_fingerprint"],
            "cell_evidence_schema_version": (
                research_evidence.STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V5
            ),
            "fold_stability": fold_evidence,
            "fold_stability_status": "BLOCK",
            "selection_replay": replay_evidence,
            "cost_sensitivity": {},
            "cost_sensitivity_status": "BLOCK",
            "lookahead_issues": [],
            "lookahead_status": "BLOCK",
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        selection_manifest, selection_alignment = self._selection_alignment_fixture(
            symbol="AAPL",
            source="UNIT_TEST",
            rows=rows,
        )
        selection_alignment["projection_policy"] = (
            research_evidence.DEVELOPMENT_SELECTION_SPLIT_POLICY
        )
        selection_alignment["protected_test_rows_persisted"] = False
        report = {
            "schema_version": (
                research_runner.FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
            ),
            "dataset_manifest": [selection_manifest],
            "dataset_snapshot": {
                "datasets": [{
                    "role": "SELECTION",
                    "symbol": "AAPL",
                    "source": "UNIT_TEST",
                    "market": "stock",
                    "timeframe": "1D",
                    "rows": rows,
                }],
            },
            "selection_calendar_schedule": attacked_schedule,
            "selection_alignment": selection_alignment,
            "selection_cells": [cell],
            "validation_rankings": [],
            "parameter_stability": research_runner.build_parameter_stability_snapshot(
                [], frozen_variants=batch_spec["variants"]
            ),
            "validation_candidates": [],
            "frozen_candidates": [],
            "test_cells": [],
            "test_results": [],
            "holdout_alignment": {"status": "BLOCK"},
            "holdout_cells": [],
            "holdout_results": [],
            "forward_candidates": [],
        }
        replay_train_ends: list[int] = []

        def capture_selection_replay(**kwargs: object) -> dict[str, object]:
            replay_train_ends.append(int(kwargs["train_end_index"]))
            return research_runner.deepcopy(replay_evidence)

        with (
            patch.object(
                research_evidence,
                "build_fixed_chronological_slice_evidence_v2",
                return_value=research_runner.deepcopy(fold_evidence),
            ),
            patch.object(
                research_evidence,
                "build_strategy_selection_replay_evidence",
                side_effect=capture_selection_replay,
            ),
        ):
            blockers = research_evidence._verify_research_semantics(
                report,
                batch_spec=batch_spec,
                formal=False,
            )
        self.assertIn(
            "research_development_selection_schedule_semantic_mismatch",
            blockers,
        )
        self.assertEqual(replay_train_ends, [expected_train_end])

    def test_schema9_cell_hash_v4_default_remains_bound_to_schema9(self) -> None:
        cell = {
            "cell_evidence_schema_version": (
                research_runner.STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V4
            ),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        risk = self.spec()["variants"][0]["risk"]
        default_hash = research_evidence.strategy_research_selection_cell_hash_v4(
            cell,
            risk,
        )
        schema9_hash = research_evidence.strategy_research_selection_cell_hash_v4(
            cell,
            risk,
            report_schema_version=(
                research_runner.LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
            ),
        )
        schema10_hash = research_evidence.strategy_research_selection_cell_hash_v4(
            cell,
            risk,
            report_schema_version=(
                research_runner.FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
            ),
        )
        self.assertEqual(default_hash, schema9_hash)
        self.assertNotEqual(default_hash, schema10_hash)

    def test_verifier_recomputes_development_rankings_semantically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            (runtime / "reports").mkdir(parents=True)
            start = datetime(2024, 1, 1, tzinfo=timezone.utc)
            rows = []
            for index in range(600):
                instant = start + timedelta(days=index)
                close = 100.0 + index * 0.1
                rows.append({
                    "date": instant.date().isoformat(),
                    "ts_ms": int(instant.timestamp() * 1000),
                    "open": close - 0.2,
                    "high": close + 0.5,
                    "low": close - 0.5,
                    "close": close,
                    "volume": 1_000.0 + index,
                    "complete": True,
                    "complete_attested": True,
                    "source": "OKX_TEST",
                })
            payload = {
                "source": "OKX_TEST",
                "rows": rows,
                "market_history_evidence": research_runner.server.build_history_dataset_evidence(
                    symbol="BTC-USDT",
                    rows=rows,
                    source="OKX_TEST",
                    dataset_lineage_id="fixture:BTC-USDT",
                ),
            }
            alignment = {
                "schema_version": "daily-batch-alignment-v2",
                "status": "PASS",
                "common_start": rows[0]["date"],
                "common_as_of": rows[-1]["date"],
                "blockers": [],
            }
            written: dict[str, object] = {}

            def fake_load(symbols: list[str], limit: int, **kwargs: object):
                self.assertEqual(symbols, ["BTC-USDT"])
                payloads = {"BTC-USDT": payload}
                manifests = [
                    {**item, "role": "SELECTION"}
                    for item in research_runner.dataset_manifests(
                        payloads,
                        require_frozen_revision=True,
                    )
                ]
                _aligned, rebuilt_alignment = align_completed_daily_payloads(
                    payloads
                )
                rebuilt_alignment["input_snapshot"] = (
                    build_strategy_selection_alignment_input_snapshot(
                        payloads,
                        manifests,
                    )
                )
                return payloads, manifests, rebuilt_alignment

            def fake_cell(**kwargs: object) -> dict[str, object]:
                variant = dict(kwargs["variant"])
                projected_payload = dict(kwargs["payload"])
                payload_rows = list(projected_payload["rows"])
                validation_end = int(
                    dict(kwargs["boundaries"])["validation_end_index"]
                )
                projected_rows = payload_rows[:validation_end]
                risk = dict(kwargs["risk"])
                manifest = research_runner.prepare_backtest_dataset(
                    projected_rows,
                    symbol="BTC-USDT",
                    source="OKX_TEST",
                    timeframe="1D",
                    minimum_rows=1,
                    market="crypto",
                )["manifest"]
                contract = dict(variant["cost_stress_contract"])
                stress_contract, severe_contract = [
                    dict(item) for item in contract["selection_scenarios"]
                ]
                cost_sensitivity = research_runner.build_strategy_cost_stress_evidence(
                    stage=research_runner.SELECTION_COST_STRESS_STAGE,
                    risk=risk,
                    baseline={
                        "name": "configured",
                        "ok": True,
                        "fee_rate": risk["fee_rate"],
                        "slippage_bps": risk["slippage_bps"],
                        "total_return_pct": 5.0,
                        "max_drawdown_pct": 5.0,
                        "trade_count": 4,
                    },
                    scenarios=[
                        {
                            **stress_contract,
                            "ok": True,
                            "total_return_pct": 3.0,
                            "max_drawdown_pct": 6.0,
                            "trade_count": 3,
                        },
                        {
                            **severe_contract,
                            "ok": True,
                            "total_return_pct": 1.0,
                            "max_drawdown_pct": 7.0,
                            "trade_count": 3,
                        },
                    ],
                )
                fold_stability = research_runner.build_fixed_chronological_slice_evidence_v2(
                    selection_rows=projected_rows,
                    symbol="BTC-USDT",
                    source="OKX_TEST",
                    market="crypto",
                    timeframe="1D",
                    strategy_id=str(variant["strategy_id"]),
                    params=dict(variant["params"]),
                    param_hash=str(variant["param_hash"]),
                    risk=risk,
                )
                selection_replay = (
                    research_runner.build_strategy_selection_replay_evidence(
                        selection_rows=projected_rows,
                        train_end_index=int(
                            dict(kwargs["boundaries"])["train_end_index"]
                        ),
                        symbol="BTC-USDT",
                        source="OKX_TEST",
                        market="crypto",
                        timeframe="1D",
                        variant_id=str(variant["variant_id"]),
                        strategy_id=str(variant["strategy_id"]),
                        params=dict(variant["params"]),
                        param_hash=str(variant["param_hash"]),
                        implementation_fingerprint=str(
                            variant["implementation_fingerprint"]
                        ),
                        risk=risk,
                    )
                )
                cell: dict[str, object] = {
                    "phase": "TRAIN_VALIDATION_SELECTION",
                    "symbol": "BTC-USDT",
                    "strategy_id": variant["strategy_id"],
                    "variant_id": variant["variant_id"],
                    "params": variant["params"],
                    "param_hash": variant["param_hash"],
                    "implementation_fingerprint": variant["implementation_fingerprint"],
                    "dataset_status": "PASS",
                    "dataset_hash": manifest["data_hash"],
                    "selection_input_rows": len(projected_rows),
                    "selection_input_end": projected_rows[-1]["date"],
                    "test_rows_evaluated": False,
                    "train_ok": True,
                    "train_return_pct": 5.0,
                    "validation_ok": True,
                    "validation_return_pct": 5.0,
                    "validation_excess_return_pct": 2.0,
                    "validation_trade_count": 4,
                    "validation_max_drawdown_pct": 5.0,
                    "validation_sharpe": 1.0,
                    "validation_drawdown_improvement_pct": 5.0,
                    "validation_sharpe_excess": 0.5,
                    "validation_risk_efficiency_excess": 0.5,
                    "fold_stability_status": fold_stability["status"],
                    "fold_stability": fold_stability,
                    "cost_sensitivity_status": "PASS",
                    "cost_sensitivity": cost_sensitivity,
                    "lookahead_status": "PASS",
                    "lookahead_issues": [],
                    "cell_evidence_schema_version": STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION,
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
                cell.update(selection_replay["flat_metric_projection"])
                cell["selection_replay"] = selection_replay
                cell["run_hash"] = strategy_research_selection_cell_hash_for_report(
                    cell,
                    risk,
                    report_schema_version=STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
                )
                return cell

            def capture_write(path: Path, report: dict[str, object]) -> None:
                written.update(report)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(research_runner._formal_report_bytes(report))

            argv = [
                "run_internal_strategy_research.py",
                "--selection-symbols", "BTC-USDT",
                "--holdout-symbols", "ETH-USDT",
                "--strategies", "dual_ma",
                "--research-generation", "TEST_DEVELOPMENT",
                "--hypothesis-file", "docs/test-hypothesis.json",
                "--max-test-candidates", "1",
                "--limit", "600",
                "--fee-rate", "0.0005123456789",
                "--slippage-bps", "2.123456",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(research_runner.server, "RUNTIME_DIR", runtime),
                patch.object(
                    research_runner,
                    "load_strategy_hypothesis_preregistration",
                    return_value=self.hypothesis(generation="TEST_DEVELOPMENT"),
                ),
                patch.object(research_runner, "load_payloads", side_effect=fake_load),
                patch.object(research_runner, "run_selection_cell", side_effect=fake_cell),
                patch.object(research_runner, "write_json_atomic", side_effect=capture_write),
            ):
                self.assertEqual(research_runner.main(), 0)

            self.assertTrue(
                (runtime / "reports" / "current_strategy_research_report.json").is_file()
            )
            current_snapshot = load_strategy_research_evidence_snapshot(
                runtime / "reports",
                strategy_id="dual_ma",
                implementation_fingerprint_fn=research_runner.server.strategy_implementation_fingerprint,
            )
            self.assertTrue(current_snapshot["ok"])
            self.assertEqual(current_snapshot["implementation_currentness_status"], "MATCH")
            self.assertTrue(current_snapshot["implementation_currentness_match"])
            self.assertTrue(
                current_snapshot["full_implementation_manifest_checked"],
                current_snapshot["full_implementation_currentness"],
            )
            self.assertEqual(current_snapshot["full_implementation_manifest_status"], "MATCH")
            self.assertTrue(current_snapshot["full_implementation_manifest_match"])

            valid = verify_strategy_research_report(written, require_formal=False)
            self.assertEqual(valid["status"], "PASS", valid["blockers"])
            self.assertEqual(
                written["schema_version"],
                STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
            )
            self.assertEqual(
                valid["implementation_manifest_verification"]["status"],
                "PASS",
            )
            self.assertEqual(
                written["parameter_stability"]["schema_version"],
                "strategy-parameter-plateau-v2",
            )

            self.assertEqual(
                written["preregistered_failure_admission"]["status"],
                "BLOCK",
            )
            self.assertEqual(
                written["preregistered_failure_admission"][
                    "admitted_variant_ids"
                ],
                [],
            )

            forged_alignment_block = research_runner.json.loads(
                research_runner.json.dumps(written)
            )
            forged_alignment_block["selection_alignment"]["status"] = "BLOCK"
            forged_alignment_block["selection_alignment"]["blockers"] = [
                "forged_alignment_block"
            ]
            forged_alignment_block["selection_cells"] = []
            forged_alignment_block["validation_rankings"] = []
            forged_alignment_block["parameter_stability"] = (
                research_runner.build_parameter_stability_snapshot(
                    [],
                    frozen_variants=forged_alignment_block["batch_spec"]["variants"],
                )
            )
            forged_alignment_block["validation_candidates"] = []
            forged_alignment_block["frozen_candidates"] = []
            forged_alignment_block["summary"]["selection_cells"] = 0
            forged_alignment_block["summary"]["validation_passed_variants"] = 0
            forged_alignment_block["summary"]["validation_raw_excess_candidates"] = 0
            forged_alignment_block["summary"]["validation_risk_adjusted_candidates"] = 0
            forged_alignment_block["summary"]["parameter_stability_status"] = (
                forged_alignment_block["parameter_stability"].get("status", "BLOCK")
            )
            forged_alignment_block["summary"]["parameter_stability_review_count"] = len([
                row
                for row in forged_alignment_block["parameter_stability"].get(
                    "strategies"
                )
                or []
                if row.get("status")
                in {"REVIEW", "NOT_ENOUGH_VARIANTS", "BLOCK"}
            ])
            forged_alignment_block["summary"]["selection_data_status"] = "BLOCK"
            forged_alignment_block["batch_run_hash"] = (
                research_runner.strategy_research_result_hash(forged_alignment_block)
            )
            forged_governance = dict(
                forged_alignment_block["research_governance"]
            )
            forged_governance.pop("governance_hash", None)
            forged_governance["governance_hash"] = research_runner.canonical_hash(
                forged_governance
            )
            forged_alignment_block["research_governance"] = forged_governance
            forged_alignment_verification = verify_strategy_research_report(
                forged_alignment_block,
                require_formal=False,
            )
            self.assertEqual(forged_alignment_verification["status"], "BLOCK")
            self.assertIn(
                "research_selection_alignment_semantic_mismatch",
                forged_alignment_verification["blockers"],
            )
            self.assertIn(
                "research_selection_cell_coverage_mismatch",
                forged_alignment_verification["blockers"],
            )

            missing_manifest = research_runner.json.loads(research_runner.json.dumps(written))
            missing_manifest.pop("implementation_manifest")
            missing_manifest["batch_run_hash"] = research_runner.strategy_research_result_hash(
                missing_manifest
            )
            missing_manifest_governance = dict(missing_manifest["research_governance"])
            missing_manifest_governance.pop("governance_hash", None)
            missing_manifest_governance["governance_hash"] = research_runner.canonical_hash(
                missing_manifest_governance
            )
            missing_manifest["research_governance"] = missing_manifest_governance
            missing_manifest_verification = verify_strategy_research_report(
                missing_manifest,
                require_formal=False,
            )
            self.assertEqual(missing_manifest_verification["status"], "BLOCK")
            self.assertIn(
                "research_field_type_invalid:implementation_manifest",
                missing_manifest_verification["blockers"],
            )

            def reseal_for_report_schema(report: dict[str, object], schema_version: int) -> None:
                report["schema_version"] = schema_version
                if schema_version < STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION:
                    report.pop("preregistered_failure_admission", None)
                    report["summary"].pop(
                        "preregistered_failure_admission_status",
                        None,
                    )
                    report["summary"].pop(
                        "preregistered_failure_admitted_candidates",
                        None,
                    )
                if schema_version < (
                    research_runner.FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
                ):
                    report["selection_calendar_schedule"]["projection_policy"] = (
                        "TRAIN_VALIDATION_ONLY"
                    )
                if schema_version < 7:
                    report["batch_spec"].pop("hypothesis_preregistration", None)
                    report["batch_spec"].pop("hypothesis_preregistration_hash", None)
                elif schema_version < MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION:
                    legacy_hypothesis = self.hypothesis_v1(
                        generation=str(
                            report["batch_spec"].get("research_generation") or ""
                        )
                    )
                    report["batch_spec"]["hypothesis_preregistration"] = (
                        legacy_hypothesis
                    )
                    report["batch_spec"]["hypothesis_preregistration_hash"] = (
                        legacy_hypothesis["hypothesis_hash"]
                    )
                if schema_version < research_runner.COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION:
                    for variant in report["batch_spec"]["variants"]:
                        variant.pop("cost_stress_contract", None)
                    for strategy_spec in report["batch_spec"]["strategy_specs"].values():
                        for variant in strategy_spec["variants"]:
                            variant.pop("cost_stress_contract", None)
                if schema_version < 6:
                    report.pop("implementation_manifest", None)
                    report["batch_spec"].pop("report_schema_version", None)
                else:
                    report["batch_spec"]["report_schema_version"] = schema_version
                report["batch_spec_hash"] = research_runner.canonical_hash(report["batch_spec"])
                report["dataset_snapshot"]["batch_spec_hash"] = report["batch_spec_hash"]
                snapshot = dict(report["dataset_snapshot"])
                snapshot.pop("snapshot_hash", None)
                report["dataset_snapshot"]["snapshot_hash"] = research_runner.canonical_hash(snapshot)
                variants_by_id = {
                    str(item["variant_id"]): item
                    for item in report["batch_spec"]["variants"]
                }
                selection_datasets = {
                    str(item.get("symbol") or "").upper(): item
                    for item in report["dataset_snapshot"]["datasets"]
                    if item.get("role") == "SELECTION"
                }
                selection_boundaries = report["selection_calendar_schedule"][
                    "symbol_boundaries"
                ]
                for cell in report["selection_cells"]:
                    if schema_version < (
                        research_runner.FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
                    ):
                        cell.pop("selection_replay", None)
                    if (
                        schema_version
                        == research_runner.LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
                    ):
                        dataset = selection_datasets[str(cell["symbol"]).upper()]
                        validation_end = int(
                            selection_boundaries[str(cell["symbol"]).upper()][
                                "validation_end_index"
                            ]
                        )
                        selection_rows = [
                            dict(item) for item in dataset["rows"][:validation_end]
                        ]
                        fold_plans = [
                            {
                                key: fold.get(key)
                                for key in (
                                    "fold", "count", "start_index", "end_index",
                                    "start", "end",
                                )
                            }
                            for fold in cell["fold_stability"]["folds"]
                        ]
                        fold_reports = [
                            {
                                "fold": fold.get("fold"),
                                "start": fold.get("start"),
                                "end": fold.get("end"),
                                "ok": True,
                                "total_return_pct": 1.0,
                                "max_drawdown_pct": 1.0,
                                "trade_count": 1,
                            }
                            for fold in cell["fold_stability"]["folds"]
                        ]
                        cell["fold_stability"] = (
                            research_runner.build_fixed_chronological_slice_evidence(
                                selection_rows=selection_rows,
                                symbol=cell["symbol"],
                                source=dataset["source"],
                                market=dataset["market"],
                                timeframe=dataset.get("timeframe") or "1D",
                                fold_plans=fold_plans,
                                fold_reports=fold_reports,
                                minimum_fold_rows=120,
                            )
                        )
                        cell["fold_stability_status"] = cell["fold_stability"]["status"]
                    elif schema_version < (
                        research_runner.FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
                    ):
                        fold_rows = [
                            {
                                key: fold.get(key)
                                for key in (
                                    "fold",
                                    "start",
                                    "end",
                                    "ok",
                                    "total_return_pct",
                                    "max_drawdown_pct",
                                    "trade_count",
                                )
                            }
                            for fold in cell["fold_stability"]["folds"]
                        ]
                        cell["fold_stability"] = research_runner.summarize_walk_forward(
                            fold_rows
                        )
                        cell["fold_stability_status"] = cell["fold_stability"]["status"]
                    if schema_version in {3, 4}:
                        cell.pop("cell_evidence_schema_version", None)
                    elif (
                        schema_version
                        == research_runner.LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
                    ):
                        cell["cell_evidence_schema_version"] = (
                            research_runner.STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V4
                        )
                    elif schema_version == research_runner.COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION:
                        cell["cell_evidence_schema_version"] = (
                            research_runner.STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V3
                        )
                    elif schema_version < research_runner.COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION:
                        cell["cell_evidence_schema_version"] = (
                            research_runner.LEGACY_STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION
                        )
                    variant = variants_by_id[str(cell["variant_id"])]
                    cell["run_hash"] = strategy_research_selection_cell_hash_for_report(
                        cell,
                        dict(variant["risk"]),
                        report_schema_version=schema_version,
                    )
                if schema_version < (
                    research_runner.FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
                ):
                    report["validation_rankings"] = [
                        research_runner.aggregate_validation_variant(
                            variant,
                            [
                                cell for cell in report["selection_cells"]
                                if cell["variant_id"] == variant["variant_id"]
                            ],
                            required_symbols=len(report["batch_spec"]["selection_symbols"]),
                            total_variant_trials=len(report["batch_spec"]["variants"]),
                        )
                        for variant in report["batch_spec"]["variants"]
                    ]
                    report["validation_rankings"].sort(
                        key=lambda row: float(row.get("adjusted_score") or -1e9),
                        reverse=True,
                    )
                    report["parameter_stability"] = (
                        research_runner.build_parameter_stability_snapshot(
                            report["validation_rankings"],
                            frozen_variants=report["batch_spec"]["variants"],
                        )
                    )
                    report["validation_candidates"] = (
                        research_runner.freeze_validation_candidates(
                            report["validation_rankings"],
                            max_candidates=report["batch_spec"]["max_test_candidates"],
                        )
                    )
                    if report["research_governance"].get("development_only") is True:
                        report["frozen_candidates"] = []
                report["batch_run_hash"] = research_runner.strategy_research_result_hash(report)
                governance = dict(report["research_governance"])
                governance.pop("governance_hash", None)
                governance["governance_hash"] = research_runner.canonical_hash(governance)
                report["research_governance"] = governance

            legacy_v10 = research_runner.json.loads(
                research_runner.json.dumps(written)
            )
            reseal_for_report_schema(legacy_v10, 10)
            legacy_v10_verification = verify_strategy_research_report(
                legacy_v10,
                require_formal=False,
            )
            self.assertEqual(
                legacy_v10_verification["status"],
                "PASS",
                legacy_v10_verification["blockers"],
            )

            legacy_v9 = research_runner.json.loads(
                research_runner.json.dumps(legacy_v10)
            )
            reseal_for_report_schema(legacy_v9, 9)
            legacy_v9_verification = verify_strategy_research_report(
                legacy_v9,
                require_formal=False,
            )
            self.assertEqual(
                legacy_v9_verification["status"],
                "PASS",
                legacy_v9_verification["blockers"],
            )

            for attack, expected_blocker in (
                ("missing", "research_parameter_stability_missing"),
                ("tampered", "research_parameter_stability_semantic_mismatch"),
            ):
                attacked_v9 = research_runner.json.loads(
                    research_runner.json.dumps(legacy_v9)
                )
                if attack == "missing":
                    attacked_v9.pop("parameter_stability")
                else:
                    attacked_v9["parameter_stability"]["strategies"][0][
                        "plateau_width"
                    ] = 99
                attacked_v9["batch_run_hash"] = (
                    research_runner.strategy_research_result_hash(attacked_v9)
                )
                attacked_governance = dict(attacked_v9["research_governance"])
                attacked_governance.pop("governance_hash", None)
                attacked_governance["governance_hash"] = research_runner.canonical_hash(
                    attacked_governance
                )
                attacked_v9["research_governance"] = attacked_governance
                attacked_verification = verify_strategy_research_report(
                    attacked_v9,
                    require_formal=False,
                )
                self.assertEqual(attacked_verification["status"], "BLOCK")
                self.assertIn(expected_blocker, attacked_verification["blockers"])

            legacy_v8 = research_runner.json.loads(research_runner.json.dumps(legacy_v9))
            reseal_for_report_schema(legacy_v8, 8)
            legacy_v8_verification = verify_strategy_research_report(
                legacy_v8,
                require_formal=False,
            )
            self.assertEqual(
                legacy_v8_verification["status"],
                "PASS",
                legacy_v8_verification["blockers"],
            )

            legacy_v7 = research_runner.json.loads(research_runner.json.dumps(legacy_v8))
            reseal_for_report_schema(legacy_v7, 7)
            legacy_v7_verification = verify_strategy_research_report(
                legacy_v7,
                require_formal=False,
            )
            self.assertEqual(
                legacy_v7_verification["status"],
                "PASS",
                legacy_v7_verification["blockers"],
            )
            self.assertEqual(
                legacy_v7_verification["hypothesis_preregistration_verification"]["status"],
                "PASS",
            )

            legacy_v6 = research_runner.json.loads(research_runner.json.dumps(legacy_v7))
            reseal_for_report_schema(legacy_v6, 6)
            legacy_v6_verification = verify_strategy_research_report(
                legacy_v6,
                require_formal=False,
            )
            self.assertEqual(
                legacy_v6_verification["status"],
                "PASS",
                legacy_v6_verification["blockers"],
            )
            self.assertEqual(
                legacy_v6_verification["hypothesis_preregistration_verification"]["status"],
                "NOT_REQUIRED",
            )

            legacy_v5 = research_runner.json.loads(research_runner.json.dumps(legacy_v6))
            reseal_for_report_schema(legacy_v5, 5)
            legacy_v5_verification = verify_strategy_research_report(
                legacy_v5,
                require_formal=False,
            )
            self.assertEqual(
                legacy_v5_verification["status"],
                "PASS",
                legacy_v5_verification["blockers"],
            )

            legacy_v4 = research_runner.json.loads(research_runner.json.dumps(legacy_v5))
            reseal_for_report_schema(legacy_v4, 4)
            legacy_v4_verification = verify_strategy_research_report(legacy_v4, require_formal=False)
            self.assertEqual(
                legacy_v4_verification["status"],
                "PASS",
                legacy_v4_verification["blockers"],
            )

            legacy = research_runner.json.loads(research_runner.json.dumps(legacy_v4))
            reseal_for_report_schema(legacy, 3)
            legacy["parameter_stability"] = build_legacy_parameter_stability_snapshot_v1(
                legacy["validation_rankings"]
            )
            legacy["batch_run_hash"] = research_runner.strategy_research_result_hash(legacy)
            legacy_verification = verify_strategy_research_report(legacy, require_formal=False)
            self.assertEqual(
                legacy_verification["status"],
                "PASS",
                legacy_verification["blockers"],
            )

            oldest_v3 = research_runner.json.loads(research_runner.json.dumps(legacy))
            oldest_v3.pop("parameter_stability")
            oldest_v3["batch_run_hash"] = research_runner.strategy_research_result_hash(oldest_v3)
            oldest_governance = dict(oldest_v3["research_governance"])
            oldest_governance.pop("governance_hash", None)
            oldest_governance["governance_hash"] = research_runner.canonical_hash(oldest_governance)
            oldest_v3["research_governance"] = oldest_governance
            oldest_verification = verify_strategy_research_report(oldest_v3, require_formal=False)
            self.assertEqual(
                oldest_verification["status"],
                "PASS",
                oldest_verification["blockers"],
            )

            downgraded = research_runner.json.loads(research_runner.json.dumps(written))
            downgraded["parameter_stability"] = build_legacy_parameter_stability_snapshot_v1(
                downgraded["validation_rankings"]
            )
            downgraded["batch_run_hash"] = research_runner.strategy_research_result_hash(downgraded)
            downgraded_governance = dict(downgraded["research_governance"])
            downgraded_governance.pop("governance_hash", None)
            downgraded_governance["governance_hash"] = research_runner.canonical_hash(downgraded_governance)
            downgraded["research_governance"] = downgraded_governance
            downgraded_verification = verify_strategy_research_report(
                downgraded,
                require_formal=False,
            )
            self.assertEqual(downgraded_verification["status"], "BLOCK")
            self.assertIn(
                "research_parameter_stability_schema_invalid",
                downgraded_verification["blockers"],
            )

            missing_stability = research_runner.json.loads(research_runner.json.dumps(written))
            missing_stability.pop("parameter_stability")
            missing_stability["batch_run_hash"] = research_runner.strategy_research_result_hash(
                missing_stability
            )
            missing_governance = dict(missing_stability["research_governance"])
            missing_governance.pop("governance_hash", None)
            missing_governance["governance_hash"] = research_runner.canonical_hash(missing_governance)
            missing_stability["research_governance"] = missing_governance
            missing_verification = verify_strategy_research_report(
                missing_stability,
                require_formal=False,
            )
            self.assertEqual(missing_verification["status"], "BLOCK")
            self.assertIn(
                "research_parameter_stability_missing",
                missing_verification["blockers"],
            )

            tampered_stability = research_runner.json.loads(research_runner.json.dumps(written))
            tampered_stability["parameter_stability"]["strategies"][0]["plateau_width"] = 99
            tampered_stability["batch_run_hash"] = research_runner.strategy_research_result_hash(
                tampered_stability
            )
            tampered_stability_governance = dict(tampered_stability["research_governance"])
            tampered_stability_governance.pop("governance_hash", None)
            tampered_stability_governance["governance_hash"] = research_runner.canonical_hash(
                tampered_stability_governance
            )
            tampered_stability["research_governance"] = tampered_stability_governance
            tampered_stability_verification = verify_strategy_research_report(
                tampered_stability,
                require_formal=False,
            )
            self.assertEqual(tampered_stability_verification["status"], "BLOCK")
            self.assertIn(
                "research_parameter_stability_semantic_mismatch",
                tampered_stability_verification["blockers"],
            )

            tampered_hypothesis = research_runner.json.loads(
                research_runner.json.dumps(written)
            )
            sealed_hypothesis = tampered_hypothesis["batch_spec"][
                "hypothesis_preregistration"
            ]
            sealed_hypothesis["cost_and_time_contract"][
                "stressed_return_must_remain_positive"
            ] = False
            hypothesis_content = dict(sealed_hypothesis)
            hypothesis_content.pop("hypothesis_hash", None)
            sealed_hypothesis["hypothesis_hash"] = research_runner.canonical_hash(
                hypothesis_content
            )
            tampered_hypothesis["batch_spec"][
                "hypothesis_preregistration_hash"
            ] = sealed_hypothesis["hypothesis_hash"]
            reseal_for_report_schema(
                tampered_hypothesis,
                STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
            )
            tampered_hypothesis_verification = verify_strategy_research_report(
                tampered_hypothesis,
                require_formal=False,
            )
            self.assertEqual(tampered_hypothesis_verification["status"], "BLOCK")
            self.assertIn(
                "research_hypothesis:strategy_hypothesis_semantic_or_hash_mismatch",
                tampered_hypothesis_verification["blockers"],
            )

            tampered_nested = research_runner.json.loads(research_runner.json.dumps(written))
            tampered_nested["selection_cells"][0]["cost_sensitivity"]["scenarios"][0][
                "total_return_pct"
            ] = -99.0
            tampered_nested_verification = verify_strategy_research_report(
                tampered_nested,
                require_formal=False,
            )
            self.assertEqual(tampered_nested_verification["status"], "BLOCK")
            self.assertTrue(any(
                item.startswith("research_selection_cell_hash_mismatch:")
                for item in tampered_nested_verification["blockers"]
            ))

            resealed_nested = research_runner.json.loads(research_runner.json.dumps(written))
            resealed_nested["selection_cells"][0]["cost_sensitivity"]["scenarios"][0][
                "total_return_pct"
            ] = -99.0
            reseal_for_report_schema(resealed_nested, STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION)
            resealed_nested_verification = verify_strategy_research_report(
                resealed_nested,
                require_formal=False,
            )
            self.assertEqual(resealed_nested_verification["status"], "BLOCK")
            self.assertTrue(any(
                item.startswith("research_selection_cost_summary_mismatch:")
                for item in resealed_nested_verification["blockers"]
            ))

            def reseal_current_report(report: dict[str, object]) -> None:
                variants = {
                    str(item["variant_id"]): item
                    for item in report["batch_spec"]["variants"]
                }
                for cell in report["selection_cells"]:
                    variant = variants[str(cell["variant_id"])]
                    cell["run_hash"] = strategy_research_selection_cell_hash_for_report(
                        cell,
                        dict(variant["risk"]),
                        report_schema_version=STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
                    )
                report["validation_rankings"] = [
                    research_runner.aggregate_validation_variant(
                        variant,
                        [
                            cell for cell in report["selection_cells"]
                            if cell["variant_id"] == variant["variant_id"]
                        ],
                        required_symbols=len(report["batch_spec"]["selection_symbols"]),
                        total_variant_trials=len(report["batch_spec"]["variants"]),
                    )
                    for variant in report["batch_spec"]["variants"]
                ]
                report["validation_rankings"].sort(
                    key=lambda row: float(row.get("adjusted_score") or -1e9),
                    reverse=True,
                )
                report["parameter_stability"] = research_runner.build_parameter_stability_snapshot(
                    report["validation_rankings"],
                    frozen_variants=report["batch_spec"]["variants"],
                )
                report["validation_candidates"] = research_runner.freeze_validation_candidates(
                    report["validation_rankings"],
                    max_candidates=report["batch_spec"]["max_test_candidates"],
                )
                report["frozen_candidates"] = []
                report["batch_run_hash"] = research_runner.strategy_research_result_hash(report)
                governance = dict(report["research_governance"])
                governance.pop("governance_hash", None)
                governance["governance_hash"] = research_runner.canonical_hash(governance)
                report["research_governance"] = governance

            for mutation in (
                lambda scenario: scenario.update({
                    "fee_rate": 0.0,
                    "slippage_bps": 0.0,
                }),
                lambda scenario: scenario.update({"name": "severe"}),
            ):
                resealed_cost_contract = research_runner.json.loads(
                    research_runner.json.dumps(written)
                )
                mutation(
                    resealed_cost_contract["selection_cells"][0]["cost_sensitivity"][
                        "scenarios"
                    ][0]
                )
                resealed_cost_contract["selection_cells"][0]["cost_sensitivity"] = (
                    research_runner.build_strategy_cost_stress_evidence(
                        stage=research_runner.SELECTION_COST_STRESS_STAGE,
                        risk=resealed_cost_contract["batch_spec"]["variants"][0]["risk"],
                        baseline=resealed_cost_contract["selection_cells"][0][
                            "cost_sensitivity"
                        ]["baseline"],
                        scenarios=resealed_cost_contract["selection_cells"][0][
                            "cost_sensitivity"
                        ]["scenarios"],
                    )
                )
                resealed_cost_contract["selection_cells"][0]["cost_sensitivity_status"] = (
                    resealed_cost_contract["selection_cells"][0]["cost_sensitivity"]["status"]
                )
                reseal_current_report(resealed_cost_contract)
                verification = verify_strategy_research_report(
                    resealed_cost_contract,
                    require_formal=False,
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertTrue(any(
                    item.startswith("research_selection_cost_evidence_integrity_blocked:")
                    for item in verification["blockers"]
                ), verification["blockers"])

            reordered = research_runner.json.loads(research_runner.json.dumps(written))
            reordered_cost = reordered["selection_cells"][0]["cost_sensitivity"]
            reordered_cost["scenarios"] = list(reversed(reordered_cost["scenarios"]))
            reordered["selection_cells"][0]["cost_sensitivity"] = (
                research_runner.build_strategy_cost_stress_evidence(
                    stage=research_runner.SELECTION_COST_STRESS_STAGE,
                    risk=reordered["batch_spec"]["variants"][0]["risk"],
                    baseline=reordered_cost["baseline"],
                    scenarios=reordered_cost["scenarios"],
                )
            )
            reordered["selection_cells"][0]["cost_sensitivity_status"] = (
                reordered["selection_cells"][0]["cost_sensitivity"]["status"]
            )
            reseal_current_report(reordered)
            reordered_verification = verify_strategy_research_report(
                reordered,
                require_formal=False,
            )
            self.assertEqual(reordered_verification["status"], "BLOCK")
            self.assertTrue(any(
                item.startswith("research_selection_cost_evidence_integrity_blocked:")
                for item in reordered_verification["blockers"]
            ), reordered_verification["blockers"])

            resealed_batch_contract = research_runner.json.loads(research_runner.json.dumps(written))
            resealed_batch_contract["batch_spec"]["max_test_candidates"] = "1"
            resealed_batch_contract["batch_spec"]["max_confirmation_candidates"] = "1"
            resealed_batch_contract["batch_spec_hash"] = research_runner.canonical_hash(
                resealed_batch_contract["batch_spec"]
            )
            resealed_batch_contract["batch_run_hash"] = research_runner.strategy_research_result_hash(
                resealed_batch_contract
            )
            resealed_batch_governance = dict(resealed_batch_contract["research_governance"])
            resealed_batch_governance.pop("governance_hash", None)
            resealed_batch_governance["governance_hash"] = research_runner.canonical_hash(
                resealed_batch_governance
            )
            resealed_batch_contract["research_governance"] = resealed_batch_governance
            resealed_batch_verification = verify_strategy_research_report(
                resealed_batch_contract,
                require_formal=False,
            )
            self.assertEqual(resealed_batch_verification["status"], "BLOCK")
            self.assertIn(
                "research_batch_numeric_contract_invalid:max_test_candidates",
                resealed_batch_verification["blockers"],
            )

            missing_cell_schema = research_runner.json.loads(research_runner.json.dumps(written))
            missing_cell_schema["selection_cells"][0].pop("cell_evidence_schema_version")
            reseal_for_report_schema(missing_cell_schema, STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION)
            missing_cell_schema_verification = verify_strategy_research_report(
                missing_cell_schema,
                require_formal=False,
            )
            self.assertEqual(missing_cell_schema_verification["status"], "BLOCK")
            self.assertTrue(any(
                item.startswith("research_selection_cell_evidence_schema_invalid:")
                for item in missing_cell_schema_verification["blockers"]
            ))

            authority_tampered = research_runner.json.loads(research_runner.json.dumps(written))
            authority_tampered["selection_cells"][0]["paper_authorized"] = True
            reseal_for_report_schema(authority_tampered, STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION)
            authority_verification = verify_strategy_research_report(
                authority_tampered,
                require_formal=False,
            )
            self.assertEqual(authority_verification["status"], "BLOCK")
            self.assertTrue(any(
                item.startswith("research_selection_cell_has_execution_authority:")
                for item in authority_verification["blockers"]
            ))

            tampered = research_runner.json.loads(research_runner.json.dumps(written))
            tampered["validation_rankings"][0]["adjusted_score"] += 100.0
            tampered["batch_run_hash"] = research_runner.strategy_research_result_hash(tampered)
            governance = dict(tampered["research_governance"])
            governance.pop("governance_hash", None)
            tampered["research_governance"]["governance_hash"] = research_runner.canonical_hash(governance)

            verification = verify_strategy_research_report(tampered, require_formal=False)

            self.assertEqual(verification["status"], "BLOCK")
            self.assertIn("research_validation_rankings_semantic_mismatch", verification["blockers"])

    def test_development_run_never_evaluates_test_or_loads_holdout_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            (runtime / "reports").mkdir(parents=True)
            calls: list[list[str]] = []
            written: dict[str, object] = {}

            def fake_load(symbols: list[str], limit: int, **kwargs: object):
                calls.append(list(symbols))
                return {}, [], {
                    "status": "BLOCK",
                    "common_start": "",
                    "common_as_of": "",
                    "blockers": ["test_fixture_no_data"],
                }

            def capture_write(path: Path, payload: dict[str, object]) -> None:
                written.update(payload)

            argv = [
                "run_internal_strategy_research.py",
                "--selection-symbols", "AAPL",
                "--holdout-symbols", "ON",
                "--strategies", "dual_ma",
                "--research-generation", "TEST_DEVELOPMENT",
                "--hypothesis-file", "docs/test-hypothesis.json",
                "--max-test-candidates", "1",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(research_runner.server, "RUNTIME_DIR", runtime),
                patch.object(
                    research_runner,
                    "load_strategy_hypothesis_preregistration",
                    return_value=self.hypothesis(generation="TEST_DEVELOPMENT"),
                ),
                patch.object(research_runner, "load_payloads", side_effect=fake_load),
                patch.object(research_runner, "write_json_atomic", side_effect=capture_write),
                patch.object(
                    research_runner,
                    "publish_strategy_research_report_pointer",
                    return_value={"status": "PUBLISHED", "published": True, "blockers": []},
                ) as publish_pointer,
                self.assertRaises(SystemExit) as failure,
            ):
                research_runner.main()

            self.assertEqual(calls, [["AAPL"]])
            response = research_runner.json.loads(str(failure.exception))
            self.assertEqual(response["error"], "research_selection_alignment_blocked")
            self.assertEqual(response["status"], "BLOCK")
            self.assertEqual(response["paper_authorized"], False)
            self.assertEqual(response["live_order_allowed"], False)
            self.assertEqual(written, {})
            publish_pointer.assert_not_called()

    @staticmethod
    def _clean_exposure(symbols: list[str]) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": "strategy-matrix-exposure-audit-v1",
            "status": "PASS",
            "evaluated_before_data_load": True,
            "symbols": symbols,
            "exposed_symbols": [],
            "evidence": {},
            "blockers": [],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        payload["audit_hash"] = research_runner.canonical_hash(payload)
        return payload

    def _registered_formal_fixture(
        self,
        directory: str,
        *,
        registration_id: str,
        batch_spec_override: dict[str, object] | None = None,
    ) -> dict[str, object]:
        runtime = Path(directory) / "runtime"
        reports = runtime / "reports"
        reports.mkdir(parents=True)
        registry = runtime / "research.sqlite3"
        output = reports / f"formal_{registration_id}.json"
        protocol_output = reports / f"protocol_{registration_id}.json"
        spec = batch_spec_override or self.spec()
        artifact_plan = plan_strategy_research_protocol_artifact(
            reports,
            registration_id=registration_id,
            registry_path=registry,
            requested_output=protocol_output,
        )
        self.assertEqual(artifact_plan["status"], "PASS", artifact_plan["blockers"])
        protocol = build_strategy_matrix_protocol(
            registration_id=registration_id,
            research_generation="TEST",
            batch_spec=spec,
            implementation_manifest=build_implementation_manifest([Path(research_runner.__file__)]),
            exposure_audit=self._clean_exposure(["ON"]),
            registration_clock_attestation=attested_clock(1_000_000),
            expires_at_ms=5_000_000,
            registry_path=registry,
            protocol_artifact=dict(artifact_plan["artifact_binding"]),
        )
        self.assertEqual(
            publish_strategy_research_protocol_artifact_no_clobber(
                protocol_output,
                protocol,
            )["status"],
            "PUBLISHED",
        )
        store = StrategyMatrixRegistrationStore(db_path=registry)
        self.assertEqual(store.register(protocol)["status"], "REGISTERED")
        return {
            "runtime": runtime,
            "reports": reports,
            "registry": registry,
            "output": output,
            "protocol": protocol,
            "store": store,
            "argv": [
                "run_internal_strategy_research.py",
                "--registration-id", registration_id,
                "--registry", str(registry),
                "--output", str(output),
                "--report-schema-version", "13",
            ],
        }

    @staticmethod
    def _blocked_formal_selection_load(
        symbols: list[str],
        limit: int,
        **kwargs: object,
    ) -> tuple[dict[str, object], list[object], dict[str, object]]:
        if symbols != ["AAPL"]:
            raise AssertionError(f"unexpected formal selection symbols: {symbols}")
        manifest, alignment = StrategyResearchRunnerTests._selection_alignment_fixture(
            symbol="AAPL",
            source="UNIT_TEST",
            rows=[],
        )
        return {}, [manifest], alignment

    @staticmethod
    def _passed_formal_selection_load(
        symbols: list[str],
        limit: int,
        **kwargs: object,
    ) -> tuple[dict[str, object], list[object], dict[str, object]]:
        if symbols != ["AAPL"]:
            raise AssertionError(f"unexpected formal selection symbols: {symbols}")
        calendar = build_market_calendar_contract(
            calendar_name="XNYS",
            start_date="2022-01-01",
            end_date="2026-12-31",
        )
        session_dates = list(calendar.get("expected_dates") or [])[:600]
        if len(session_dates) != 600:
            raise AssertionError("formal fixture calendar did not provide 600 sessions")
        rows = []
        for session_date in session_dates:
            instant = datetime.fromisoformat(
                f"{session_date}T00:00:00+00:00"
            )
            rows.append({
                "date": session_date,
                "ts_ms": int(instant.timestamp() * 1000),
                "open": 100.0,
                "high": 100.5,
                "low": 99.5,
                "close": 100.0,
                "volume": 1_000.0,
                "complete": True,
                "complete_attested": True,
                "source": "FORMAL_FIXTURE",
            })
        payloads: dict[str, object] = {
            "AAPL": {
                "source": "FORMAL_FIXTURE",
                "rows": rows,
                "data_revision_evidence": {
                    "status": "PASS",
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            }
        }
        manifests = [
            {**item, "role": "SELECTION"}
            for item in research_runner.dataset_manifests(
                payloads,
                require_frozen_revision=True,
            )
        ]
        aligned, alignment = align_completed_daily_payloads(payloads)
        alignment["input_snapshot"] = (
            build_strategy_selection_alignment_input_snapshot(
                payloads,
                manifests,
            )
        )
        return aligned, manifests, alignment

    def test_blind_once_without_registration_blocks_before_data_load(self) -> None:
        argv = [
            "run_internal_strategy_research.py",
            "--selection-test-policy", "BLIND_ONCE",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(research_runner, "load_payloads") as load,
            self.assertRaises(SystemExit) as raised,
        ):
            research_runner.main()

        self.assertIn("requires a pre-registered", str(raised.exception))
        load.assert_not_called()

    def test_development_run_requires_explicit_strategies_before_data_load(self) -> None:
        argv = [
            "run_internal_strategy_research.py",
            "--research-generation", "NEW_DEVELOPMENT",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(research_runner, "load_payloads") as load,
            self.assertRaises(SystemExit) as raised,
        ):
            research_runner.main()

        self.assertIn("--strategies is required", str(raised.exception))
        load.assert_not_called()

    def test_development_run_requires_explicit_generation_before_data_load(self) -> None:
        argv = [
            "run_internal_strategy_research.py",
            "--strategies", "dual_ma",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(research_runner, "load_payloads") as load,
            self.assertRaises(SystemExit) as raised,
        ):
            research_runner.main()

        self.assertIn("--research-generation is required", str(raised.exception))
        load.assert_not_called()

    def test_development_run_requires_hypothesis_before_data_load(self) -> None:
        argv = [
            "run_internal_strategy_research.py",
            "--strategies", "dual_ma",
            "--research-generation", "NEW_DEVELOPMENT",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(research_runner, "load_payloads") as load,
            self.assertRaises(SystemExit) as raised,
        ):
            research_runner.main()

        self.assertIn("--hypothesis-file is required", str(raised.exception))
        load.assert_not_called()

    def test_formal_run_claims_registration_before_any_market_data_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            (runtime / "reports").mkdir(parents=True)
            registry = runtime / "research.sqlite3"
            spec = self.spec()
            protocol = {
                "registration_id": "research-1",
                "batch_spec": spec,
                "batch_spec_hash": research_runner.canonical_hash(spec),
            }
            order: list[str] = []

            class FakeStore:
                def __init__(self, *, db_path: Path, **_kwargs: object) -> None:
                    order.append("store")

                def get(self, registration_id: str) -> dict[str, object]:
                    order.append("get")
                    return {"ok": True, "status": "REGISTERED", "protocol": protocol}

                def claim(self, registration_id: str, **kwargs: object) -> dict[str, object]:
                    order.append("claim")
                    return {
                        "ok": True,
                        "status": "CLAIMED",
                        "protocol": protocol,
                        "claim": {
                            "started_at_ms": 1_000_000,
                            "holdout_exposure_audit": {"status": "PASS"},
                        },
                    }

            def stop_at_load(*args: object, **kwargs: object) -> None:
                order.append("load")
                raise StopBeforeDataLoad

            argv = [
                "run_internal_strategy_research.py",
                "--registration-id", "research-1",
                "--registry", str(registry),
                "--report-schema-version", "13",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(research_runner.server, "RUNTIME_DIR", runtime),
                patch.object(research_runner, "StrategyMatrixRegistrationStore", FakeStore),
                patch.object(research_runner, "audit_strategy_matrix_holdout_exposure", return_value={"status": "PASS"}),
                patch.object(research_runner, "attest_utc_clock", return_value={"attested_now_ms": 1_000_000}),
                patch.object(research_runner, "load_payloads", side_effect=stop_at_load),
                self.assertRaises(StopBeforeDataLoad),
            ):
                research_runner.main()

            self.assertEqual(order, ["store", "get", "claim", "load"])

    def test_schema13_mechanism_block_never_runs_test_or_loads_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            schema13_spec = research_runner.build_research_batch_spec(
                selection_symbols=["AAPL"],
                holdout_symbols=["ON"],
                strategies=["dual_ma"],
                position_pct=20.0,
                take_profit_pct=8.0,
                stop_loss_pct=4.0,
                fee_rate=0.0005,
                slippage_bps=2.0,
                limit=780,
                max_test_candidates=1,
                research_generation="TEST",
                selection_test_policy="BLIND_ONCE",
                hypothesis_preregistration=self.hypothesis(),
                report_schema_version=(
                    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION
                ),
            )
            fixture = self._registered_formal_fixture(
                directory,
                registration_id="research-schema13-mechanism-block",
                batch_spec_override=schema13_spec,
            )
            loaded_symbols: list[list[str]] = []

            def selection_only_load(
                symbols: list[str],
                limit: int,
                **kwargs: object,
            ) -> tuple[dict[str, object], list[object], dict[str, object]]:
                loaded_symbols.append(list(symbols))
                if symbols != ["AAPL"]:
                    raise AssertionError(
                        f"schema13 BLOCK loaded confirmation symbols: {symbols}"
                    )
                return self._passed_formal_selection_load(
                    symbols,
                    limit,
                    **kwargs,
                )

            blocked_admission = {
                "schema_version": "strategy-preregistered-failure-admission-v2",
                "status": "BLOCK",
                "admitted_variant_ids": [],
                "blockers": [
                    "dual_ma:mechanism_condition_triggered:validation_excess_lost"
                ],
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            with (
                patch.object(sys, "argv", fixture["argv"]),
                patch.object(
                    research_runner.server,
                    "RUNTIME_DIR",
                    fixture["runtime"],
                ),
                patch.object(
                    research_runner,
                    "audit_strategy_matrix_holdout_exposure",
                    return_value=self._clean_exposure(["ON"]),
                ),
                patch.object(
                    research_runner,
                    "attest_utc_clock",
                    return_value=attested_clock(2_000_000),
                ),
                patch.object(
                    research_runner,
                    "load_payloads",
                    side_effect=selection_only_load,
                ),
                patch.object(
                    research_runner,
                    "build_strategy_preregistered_failure_admission_v2",
                    return_value=blocked_admission,
                ) as build_admission,
                patch.object(research_runner, "run_test_cell") as run_test,
                patch.object(
                    research_runner,
                    "finalize_formal_strategy_research_result",
                    side_effect=StopBeforeDataLoad,
                ),
                self.assertRaises(StopBeforeDataLoad),
            ):
                research_runner.main()

            self.assertEqual(loaded_symbols, [["AAPL"]])
            build_admission.assert_called_once()
            run_test.assert_not_called()

    def test_schema14_formal_block_uses_live_cumulative_lineage_and_no_protected_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            reports = runtime / "reports"
            reports.mkdir(parents=True)
            registry = runtime / "strategy_research_registrations.sqlite3"
            output = reports / "strategy_research_schema14_block.json"
            protocol_output = reports / "strategy_research_protocol_schema14-block.json"
            store = StrategyMatrixRegistrationStore(
                db_path=registry,
                canonical_runtime_root=runtime,
            )
            lineage_plan = store.derive_search_lineage(
                search_family_id="dual-ma-causal-global-search",
                current_trial_count=3,
            )
            self.assertEqual(lineage_plan["status"], "PASS")
            spec = research_runner.build_research_batch_spec(
                selection_symbols=["AAPL"],
                holdout_symbols=["ON"],
                strategies=["dual_ma"],
                position_pct=20.0,
                take_profit_pct=8.0,
                stop_loss_pct=4.0,
                fee_rate=0.0005,
                slippage_bps=2.0,
                limit=780,
                max_test_candidates=1,
                research_generation="TEST",
                selection_test_policy="BLIND_ONCE",
                hypothesis_preregistration=self.hypothesis_v3(),
                search_lineage=dict(lineage_plan["lineage"]),
                report_schema_version=(
                    STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION
                ),
            )
            artifact_plan = plan_strategy_research_protocol_artifact(
                reports,
                registration_id="schema14-block",
                registry_path=registry,
                requested_output=protocol_output,
            )
            self.assertEqual(artifact_plan["status"], "PASS")
            protocol = build_strategy_matrix_protocol(
                registration_id="schema14-block",
                research_generation="TEST",
                batch_spec=spec,
                implementation_manifest=build_implementation_manifest([
                    Path(research_runner.__file__)
                ]),
                exposure_audit=self._clean_exposure(["ON"]),
                registration_clock_attestation=attested_clock(1_000_000),
                expires_at_ms=5_000_000,
                registry_path=registry,
                protocol_artifact=dict(artifact_plan["artifact_binding"]),
            )
            self.assertEqual(
                publish_strategy_research_protocol_artifact_no_clobber(
                    protocol_output,
                    protocol,
                )["status"],
                "PUBLISHED",
            )
            self.assertEqual(store.register(protocol)["status"], "REGISTERED")
            loaded_symbols: list[list[str]] = []

            def selection_only_load(
                symbols: list[str],
                limit: int,
                **kwargs: object,
            ) -> tuple[dict[str, object], list[object], dict[str, object]]:
                loaded_symbols.append(list(symbols))
                if symbols != ["AAPL"]:
                    raise AssertionError(
                        f"schema14 BLOCK loaded confirmation symbols: {symbols}"
                    )
                return self._passed_formal_selection_load(
                    symbols,
                    limit,
                    **kwargs,
                )

            argv = [
                "run_internal_strategy_research.py",
                "--registration-id", "schema14-block",
                "--registry", str(registry),
                "--output", str(output),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(research_runner.server, "RUNTIME_DIR", runtime),
                patch.object(
                    research_runner,
                    "audit_strategy_matrix_holdout_exposure",
                    return_value=self._clean_exposure(["ON"]),
                ),
                patch.object(
                    research_runner,
                    "attest_utc_clock",
                    side_effect=[
                        attested_clock(2_000_000),
                        attested_clock(3_000_000),
                    ],
                ),
                patch.object(
                    research_runner,
                    "load_payloads",
                    side_effect=selection_only_load,
                ),
                patch.object(
                    research_runner,
                    "_publish_verified_strategy_research_pointer",
                    return_value={
                        "status": "PUBLISHED",
                        "published": True,
                        "blockers": [],
                    },
                ),
                patch.object(research_runner, "run_test_cell") as run_test,
                patch("builtins.print"),
            ):
                self.assertEqual(research_runner.main(), 0)

            report = research_runner.json.loads(
                output.read_text(encoding="utf-8")
            )
            self.assertEqual(loaded_symbols, [["AAPL"]])
            self.assertEqual(report["schema_version"], 14)
            self.assertEqual(
                report["batch_spec"]["search_lineage"][
                    "cumulative_trial_count"
                ],
                3,
            )
            self.assertEqual(
                report["preregistered_failure_admission"]["status"],
                "BLOCK",
            )
            self.assertEqual(report["frozen_candidates"], [])
            self.assertEqual(report["test_cells"], [])
            self.assertEqual(report["holdout_cells"], [])
            run_test.assert_not_called()
            verification = verify_strategy_research_report(report)
            self.assertEqual(
                verification["status"],
                "PASS",
                verification["blockers"],
            )
            self.assertFalse(
                verification[
                    "preregistered_failure_admission_verification"
                ]["live_registry_verified"]
            )
            self.assertEqual(
                verification[
                    "preregistered_failure_admission_verification"
                ]["verification_scope"],
                "OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY",
            )

    def test_formal_run_completes_single_use_registry_without_holdout_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            reports = runtime / "reports"
            reports.mkdir(parents=True)
            registry = runtime / "research.sqlite3"
            output = reports / "strategy_research_formal_test.json"
            protocol_output = reports / "strategy_research_protocol_research-complete.json"
            spec = self.spec()
            artifact_plan = plan_strategy_research_protocol_artifact(
                reports,
                registration_id="research-complete",
                registry_path=registry,
                requested_output=protocol_output,
            )
            self.assertEqual(artifact_plan["status"], "PASS", artifact_plan["blockers"])
            protocol = build_strategy_matrix_protocol(
                registration_id="research-complete",
                research_generation="TEST",
                batch_spec=spec,
                implementation_manifest=build_implementation_manifest([Path(research_runner.__file__)]),
                exposure_audit=self._clean_exposure(["ON"]),
                registration_clock_attestation=attested_clock(1_000_000),
                expires_at_ms=5_000_000,
                registry_path=registry,
                protocol_artifact=dict(artifact_plan["artifact_binding"]),
            )
            self.assertEqual(
                publish_strategy_research_protocol_artifact_no_clobber(
                    protocol_output,
                    protocol,
                )["status"],
                "PUBLISHED",
            )
            store = StrategyMatrixRegistrationStore(db_path=registry)
            self.assertEqual(store.register(protocol)["status"], "REGISTERED")

            def passed_selection_load(symbols: list[str], limit: int, **kwargs: object):
                self.assertEqual(symbols, ["AAPL"])
                return self._passed_formal_selection_load(symbols, limit, **kwargs)

            argv = [
                "run_internal_strategy_research.py",
                "--registration-id", "research-complete",
                "--registry", str(registry),
                "--output", str(output),
                "--report-schema-version", "13",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(research_runner.server, "RUNTIME_DIR", runtime),
                patch.object(
                    research_runner,
                    "audit_strategy_matrix_holdout_exposure",
                    return_value=self._clean_exposure(["ON"]),
                ),
                patch.object(
                    research_runner,
                    "attest_utc_clock",
                    side_effect=[attested_clock(2_000_000), attested_clock(3_000_000)],
                ),
                patch.object(research_runner, "load_payloads", side_effect=passed_selection_load),
                patch.object(research_runner, "run_test_cell") as run_test_cell,
            ):
                self.assertEqual(research_runner.main(), 0)

            report = research_runner.json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["research_governance"]["status"], "PREREGISTERED_BLIND_SINGLE_USE_COMPLETE")
            self.assertEqual(
                report["preregistered_failure_admission"]["status"],
                "BLOCK",
            )
            self.assertEqual(report["frozen_candidates"], [])
            self.assertEqual(report["test_cells"], [])
            self.assertEqual(report["holdout_cells"], [])
            self.assertEqual(report["forward_candidates"], [])
            run_test_cell.assert_not_called()
            self.assertEqual(report["paper_authorized"], False)
            self.assertEqual(report["live_order_allowed"], False)
            self.assertEqual(store.get("research-complete")["status"], "COMPLETED")
            verification = verify_strategy_research_report(report)
            self.assertEqual(verification["status"], "PASS", verification["blockers"])
            self.assertEqual(verification["formal_single_use"], True)
            tampered_admission = research_runner.json.loads(
                research_runner.json.dumps(report)
            )
            tampered_admission["preregistered_failure_admission"]["status"] = "PASS"
            admission_content = dict(
                tampered_admission["preregistered_failure_admission"]
            )
            admission_content.pop("admission_hash", None)
            tampered_admission["preregistered_failure_admission"][
                "admission_hash"
            ] = research_runner.canonical_hash(admission_content)
            tampered_admission["summary"][
                "preregistered_failure_admission_status"
            ] = "PASS"
            tampered_admission["batch_run_hash"] = (
                research_runner.strategy_research_result_hash(
                    tampered_admission
                )
            )
            self.assertIn(
                "research_preregistered_failure_admission_semantic_mismatch",
                verify_strategy_research_report(tampered_admission)["blockers"],
            )
            tampered = research_runner.json.loads(research_runner.json.dumps(report))
            tampered["research_governance"]["completion_hash"] = "0" * 64
            self.assertEqual(verify_strategy_research_report(tampered)["status"], "BLOCK")

    def test_formal_blocked_alignment_never_completes_or_publishes_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._registered_formal_fixture(
                directory,
                registration_id="research-alignment-blocked",
            )
            store = fixture["store"]
            assert isinstance(store, StrategyMatrixRegistrationStore)
            with (
                patch.object(sys, "argv", fixture["argv"]),
                patch.object(research_runner.server, "RUNTIME_DIR", fixture["runtime"]),
                patch.object(
                    research_runner,
                    "audit_strategy_matrix_holdout_exposure",
                    return_value=self._clean_exposure(["ON"]),
                ),
                patch.object(
                    research_runner,
                    "attest_utc_clock",
                    return_value=attested_clock(2_000_000),
                ),
                patch.object(
                    research_runner,
                    "load_payloads",
                    side_effect=self._blocked_formal_selection_load,
                ),
                patch.object(
                    research_runner,
                    "publish_strategy_research_report_pointer",
                ) as publish_pointer,
                self.assertRaises(SystemExit) as failure,
            ):
                research_runner.main()
            response = research_runner.json.loads(str(failure.exception))
            self.assertEqual(response["error"], "research_selection_alignment_blocked")
            self.assertEqual(response["status"], "BLOCK")
            self.assertEqual(store.get("research-alignment-blocked")["status"], "RUNNING")
            self.assertFalse(Path(fixture["output"]).exists())
            publish_pointer.assert_not_called()

    def test_running_prepared_result_recovers_without_research_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._registered_formal_fixture(
                directory,
                registration_id="research-running-recovery",
            )
            store = fixture["store"]
            assert isinstance(store, StrategyMatrixRegistrationStore)
            blocked_completion = {
                "ok": False,
                "status": "BLOCK",
                "blockers": ["synthetic_completion_failure"],
            }
            with (
                patch.object(sys, "argv", fixture["argv"]),
                patch.object(research_runner.server, "RUNTIME_DIR", fixture["runtime"]),
                patch.object(
                    research_runner,
                    "audit_strategy_matrix_holdout_exposure",
                    return_value=self._clean_exposure(["ON"]),
                ),
                patch.object(
                    research_runner,
                    "attest_utc_clock",
                    side_effect=[attested_clock(2_000_000), attested_clock(3_000_000)],
                ),
                patch.object(
                    research_runner,
                    "load_payloads",
                    side_effect=self._passed_formal_selection_load,
                ),
                patch.object(
                    StrategyMatrixRegistrationStore,
                    "complete",
                    return_value=blocked_completion,
                ),
                self.assertRaises(SystemExit) as first_failure,
            ):
                research_runner.main()
            self.assertIn("PREPARED_RECOVERY_REQUIRED", str(first_failure.exception))
            self.assertEqual(store.get("research-running-recovery")["status"], "RUNNING")
            self.assertFalse(Path(fixture["output"]).exists())

            with (
                patch.object(sys, "argv", fixture["argv"]),
                patch.object(research_runner.server, "RUNTIME_DIR", fixture["runtime"]),
                patch.object(
                    research_runner,
                    "build_research_batch_spec",
                    side_effect=AssertionError("recovery rebuilt research spec"),
                ),
                patch.object(
                    research_runner,
                    "audit_strategy_matrix_holdout_exposure",
                    side_effect=AssertionError("recovery repeated exposure audit"),
                ),
                patch.object(
                    research_runner,
                    "load_payloads",
                    side_effect=AssertionError("recovery loaded market data"),
                ),
                patch.object(
                    StrategyMatrixRegistrationStore,
                    "claim",
                    side_effect=AssertionError("recovery claimed registration twice"),
                ),
                patch.object(
                    research_runner,
                    "attest_utc_clock",
                    side_effect=AssertionError("recovery fetched a new clock"),
                ),
            ):
                self.assertEqual(research_runner.main(), 0)
            self.assertEqual(store.get("research-running-recovery")["status"], "COMPLETED")
            recovered = research_runner.json.loads(
                Path(fixture["output"]).read_text(encoding="utf-8")
            )
            self.assertEqual(verify_strategy_research_report(recovered)["status"], "PASS")

    def test_completed_prepared_result_restores_missing_final_without_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._registered_formal_fixture(
                directory,
                registration_id="research-completed-recovery",
            )
            with (
                patch.object(sys, "argv", fixture["argv"]),
                patch.object(research_runner.server, "RUNTIME_DIR", fixture["runtime"]),
                patch.object(
                    research_runner,
                    "audit_strategy_matrix_holdout_exposure",
                    return_value=self._clean_exposure(["ON"]),
                ),
                patch.object(
                    research_runner,
                    "attest_utc_clock",
                    side_effect=[attested_clock(2_000_000), attested_clock(3_000_000)],
                ),
                patch.object(
                    research_runner,
                    "load_payloads",
                    side_effect=self._passed_formal_selection_load,
                ),
            ):
                self.assertEqual(research_runner.main(), 0)
            output = Path(fixture["output"])
            output.unlink()
            (Path(fixture["reports"]) / "current_strategy_research_report.json").unlink()

            with (
                patch.object(sys, "argv", fixture["argv"]),
                patch.object(research_runner.server, "RUNTIME_DIR", fixture["runtime"]),
                patch.object(
                    research_runner,
                    "build_research_batch_spec",
                    side_effect=AssertionError("recovery rebuilt research spec"),
                ),
                patch.object(
                    research_runner,
                    "audit_strategy_matrix_holdout_exposure",
                    side_effect=AssertionError("recovery repeated exposure audit"),
                ),
                patch.object(
                    research_runner,
                    "load_payloads",
                    side_effect=AssertionError("recovery loaded market data"),
                ),
                patch.object(
                    StrategyMatrixRegistrationStore,
                    "claim",
                    side_effect=AssertionError("recovery claimed registration twice"),
                ),
                patch.object(
                    StrategyMatrixRegistrationStore,
                    "complete",
                    side_effect=AssertionError("completed recovery completed twice"),
                ),
                patch.object(
                    research_runner,
                    "attest_utc_clock",
                    side_effect=AssertionError("recovery fetched a new clock"),
                ),
            ):
                self.assertEqual(research_runner.main(), 0)
            self.assertTrue(output.is_file())
            recovered = research_runner.json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(verify_strategy_research_report(recovered)["status"], "PASS")

    def test_pointer_publication_failure_is_not_reported_as_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._registered_formal_fixture(
                directory,
                registration_id="research-pointer-failure",
            )
            with (
                patch.object(sys, "argv", fixture["argv"]),
                patch.object(research_runner.server, "RUNTIME_DIR", fixture["runtime"]),
                patch.object(
                    research_runner,
                    "audit_strategy_matrix_holdout_exposure",
                    return_value=self._clean_exposure(["ON"]),
                ),
                patch.object(
                    research_runner,
                    "attest_utc_clock",
                    side_effect=[attested_clock(2_000_000), attested_clock(3_000_000)],
                ),
                patch.object(
                    research_runner,
                    "load_payloads",
                    side_effect=self._passed_formal_selection_load,
                ),
                patch.object(
                    research_runner,
                    "publish_strategy_research_report_pointer",
                    return_value={
                        "status": "BLOCK",
                        "published": False,
                        "blockers": ["synthetic_pointer_failure"],
                    },
                ),
                self.assertRaises(SystemExit) as failure,
            ):
                research_runner.main()
            self.assertIn("POINTER_RECOVERY_REQUIRED", str(failure.exception))

    def test_runner_rejects_unbound_published_pointer_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report_dir = Path(directory)
            output = report_dir / "strategy_research_bound.json"
            report = {
                "schema_version": 12,
                "created_at": "2026-08-14T00:00:00+00:00",
                "batch_spec_hash": "a" * 64,
                "dataset_manifest_hash": "b" * 64,
                "batch_run_hash": "c" * 64,
                "research_governance": {"status": "DEVELOPMENT_SELECTION_ONLY"},
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            output.write_bytes(research_runner._formal_report_bytes(report))
            expectation = research_runner.build_strategy_research_pointer_publication_expectation(
                report,
                report_file=output.name,
                report_file_bytes=research_runner._formal_report_bytes(report),
            )
            forged_success = {
                "status": "PUBLISHED",
                "published": True,
                "blockers": [],
                "expectation_hash": expectation["expectation_hash"],
                "pointer_hash": "d" * 64,
                "report_hash": expectation["report_hash"],
                "report_file_sha256": expectation["report_file_sha256"],
                "report_file_size_bytes": expectation["report_file_size_bytes"],
                "report_schema_version": expectation["report_schema_version"],
                "batch_spec_hash": expectation["batch_spec_hash"],
                "dataset_manifest_hash": expectation["dataset_manifest_hash"],
                "batch_run_hash": expectation["batch_run_hash"],
                "governance_status": expectation["governance_status"],
                "created_at": expectation["created_at"],
                "source_verification_status": "PASS",
                "pointer_post_read_verified": True,
                "report_post_read_verified": True,
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            with patch.object(
                research_runner,
                "publish_strategy_research_report_pointer",
                return_value=forged_success,
            ):
                result = research_runner._publish_verified_strategy_research_pointer(
                    report_dir=report_dir,
                    output=output,
                    report=report,
                )

        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["published"])
        self.assertIn(
            "strategy_research_pointer_receipt_pointer_hash_mismatch",
            result["blockers"],
        )
        self.assertFalse(
            (report_dir / research_runner.DEFAULT_STRATEGY_RESEARCH_POINTER_FILE).exists()
        )
        self.assertNotIn(str(output), research_runner.json.dumps(result))

    def test_formal_nested_output_blocks_before_store_claim_or_data_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            (runtime / "reports").mkdir(parents=True)
            argv = [
                "run_internal_strategy_research.py",
                "--registration-id", "nested-output",
                "--registry", str(runtime / "research.sqlite3"),
                "--output", str(runtime / "reports" / "nested" / "report.json"),
                "--report-schema-version", "13",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(research_runner.server, "RUNTIME_DIR", runtime),
                patch.object(
                    research_runner,
                    "StrategyMatrixRegistrationStore",
                    side_effect=AssertionError("nested output opened registration store"),
                ),
                patch.object(
                    research_runner,
                    "load_payloads",
                    side_effect=AssertionError("nested output loaded research data"),
                ),
                self.assertRaises(SystemExit) as failure,
            ):
                research_runner.main()

        response = research_runner.json.loads(str(failure.exception))
        self.assertEqual(response["status"], "BLOCK")
        self.assertIn(
            "strategy_research_output_outside_report_root",
            response["blockers"],
        )

    def test_development_nested_output_blocks_before_hypothesis_build_or_data_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            (runtime / "reports").mkdir(parents=True)
            argv = [
                "run_internal_strategy_research.py",
                "--strategies", "dual_ma",
                "--research-generation", "NESTED_OUTPUT",
                "--hypothesis-file", "docs/not-loaded.json",
                "--output", str(runtime / "reports" / "nested" / "report.json"),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(research_runner.server, "RUNTIME_DIR", runtime),
                patch.object(
                    research_runner,
                    "load_strategy_hypothesis_preregistration",
                    side_effect=AssertionError("nested output loaded hypothesis"),
                ),
                patch.object(
                    research_runner,
                    "build_research_batch_spec",
                    side_effect=AssertionError("nested output built batch"),
                ),
                patch.object(
                    research_runner,
                    "load_payloads",
                    side_effect=AssertionError("nested output loaded research data"),
                ),
                self.assertRaises(SystemExit) as failure,
            ):
                research_runner.main()

        response = research_runner.json.loads(str(failure.exception))
        self.assertEqual(response["status"], "BLOCK")
        self.assertIn(
            "strategy_research_output_outside_report_root",
            response["blockers"],
        )

    def test_recovery_failure_response_does_not_expose_local_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._registered_formal_fixture(
                directory,
                registration_id="research-recovery-path-redaction",
            )
            private_path = str(
                Path(directory) / "private" / "prepared-result-with-local-path.json"
            )
            with (
                patch.object(sys, "argv", fixture["argv"]),
                patch.object(research_runner.server, "RUNTIME_DIR", fixture["runtime"]),
                patch.object(
                    research_runner,
                    "recover_formal_strategy_research_result",
                    return_value={
                        "ok": False,
                        "status": "BLOCK",
                        "blockers": ["synthetic_recovery_failure"],
                        "final_publication": {"path": private_path},
                    },
                ),
                self.assertRaises(SystemExit) as failure,
            ):
                research_runner.main()
            rendered = str(failure.exception)
            response = research_runner.json.loads(rendered)
            self.assertEqual(response["status"], "BLOCK")
            self.assertEqual(response["blockers"], ["synthetic_recovery_failure"])
            self.assertEqual(response["research_only"], True)
            self.assertEqual(response["paper_authorized"], False)
            self.assertEqual(response["live_order_allowed"], False)
            self.assertNotIn(private_path, rendered)
            self.assertNotIn("final_publication", response)

    def test_formal_run_rejects_command_line_parameter_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            (runtime / "reports").mkdir(parents=True)
            registry = runtime / "research.sqlite3"
            argv = [
                "run_internal_strategy_research.py",
                "--registration-id", "research-1",
                "--registry", str(registry),
                "--strategies", "dual_ma",
                "--report-schema-version", "13",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(research_runner.server, "RUNTIME_DIR", runtime),
                self.assertRaises(SystemExit) as raised,
            ):
                research_runner.main()

            self.assertIn("parameters come only from the registered protocol", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
