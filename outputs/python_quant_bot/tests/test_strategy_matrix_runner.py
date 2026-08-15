from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import run_internal_strategy_matrix as matrix_runner
from exchange_terminal.services.implementation_manifest import build_implementation_manifest
from exchange_terminal.services.strategy_matrix_evidence import (
    verify_strategy_matrix_evidence,
    verify_strategy_matrix_report,
)
from exchange_terminal.services.prepared_research_result import prepared_research_result_path
from exchange_terminal.services.strategy_matrix_protocol import (
    StrategyMatrixRegistrationStore,
    build_strategy_matrix_protocol,
)
from tests.portfolio_governance_fixtures import attested_clock


class StopBeforeDataLoad(RuntimeError):
    pass


class StrategyMatrixRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_mode = patch.object(matrix_runner.server, "RUNTIME_READ_ONLY", False)
        runtime_mode.start()
        self.addCleanup(runtime_mode.stop)

    def spec(self) -> dict[str, object]:
        return matrix_runner.build_matrix_batch_spec(
            selection_symbols=["AAPL"],
            confirmation_symbols=["FRESH"],
            strategies=["dual_ma"],
            position_pct=20.0,
            take_profit_pct=8.0,
            stop_loss_pct=4.0,
            fee_rate=0.0005,
            slippage_bps=2.0,
            limit=780,
            max_confirmation_candidates=1,
        )

    def formal_fixture(
        self,
        directory: str,
        *,
        registration_id: str,
    ) -> tuple[Path, Path, Path, dict[str, object], StrategyMatrixRegistrationStore]:
        runtime = Path(directory) / "runtime"
        reports = runtime / "reports"
        reports.mkdir(parents=True)
        registry_path = runtime / "registrations.sqlite3"
        output = reports / f"strategy_matrix_{registration_id}.json"
        spec = self.spec()
        exposure: dict[str, object] = {
            "schema_version": "strategy-matrix-exposure-audit-v1",
            "status": "PASS",
            "evaluated_before_data_load": True,
            "symbols": ["FRESH"],
            "exposed_symbols": [],
            "evidence": {},
            "blockers": [],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        exposure["audit_hash"] = matrix_runner.canonical_hash(exposure)
        protocol = build_strategy_matrix_protocol(
            registration_id=registration_id,
            research_generation="SYNTHETIC_RECOVERY_TEST",
            batch_spec=spec,
            implementation_manifest=build_implementation_manifest([Path(matrix_runner.__file__)]),
            exposure_audit=exposure,
            registration_clock_attestation=attested_clock(1_000_000),
            expires_at_ms=4_000_000,
            registry_path=registry_path,
        )
        store = StrategyMatrixRegistrationStore(db_path=registry_path)
        self.assertEqual(store.register(protocol)["status"], "REGISTERED")
        return runtime, registry_path, output, protocol, store

    @staticmethod
    def empty_data_load(*_args: object, **_kwargs: object):
        return {}, [], {
            "status": "BLOCK",
            "common_start": "",
            "common_as_of": "",
            "blockers": ["synthetic_data_unavailable"],
        }

    def run_empty_formal(
        self,
        *,
        runtime: Path,
        registry_path: Path,
        output: Path,
        registration_id: str,
    ) -> int:
        exposure: dict[str, object] = {
            "schema_version": "strategy-matrix-exposure-audit-v1",
            "status": "PASS",
            "evaluated_before_data_load": True,
            "symbols": ["FRESH"],
            "exposed_symbols": [],
            "evidence": {},
            "blockers": [],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        exposure["audit_hash"] = matrix_runner.canonical_hash(exposure)
        argv = [
            "run_internal_strategy_matrix.py",
            "--registration-id", registration_id,
            "--registry", str(registry_path),
            "--output", str(output),
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(matrix_runner.server, "RUNTIME_DIR", runtime),
            patch.object(matrix_runner, "audit_strategy_matrix_holdout_exposure", return_value=exposure),
            patch.object(
                matrix_runner,
                "attest_utc_clock",
                side_effect=[attested_clock(2_000_000), attested_clock(3_000_000)],
            ),
            patch.object(matrix_runner, "load_payloads", side_effect=self.empty_data_load),
            patch("builtins.print"),
        ):
            return matrix_runner.main()

    def recover_without_research_work(
        self,
        *,
        runtime: Path,
        registry_path: Path,
        output: Path,
        registration_id: str,
    ) -> int:
        argv = [
            "run_internal_strategy_matrix.py",
            "--registration-id", registration_id,
            "--registry", str(registry_path),
            "--output", str(output),
        ]
        forbidden = AssertionError("matrix research work must not rerun during recovery")
        with (
            patch.object(sys, "argv", argv),
            patch.object(matrix_runner.server, "RUNTIME_DIR", runtime),
            patch.object(matrix_runner, "build_matrix_batch_spec", side_effect=forbidden),
            patch.object(matrix_runner, "audit_strategy_matrix_holdout_exposure", side_effect=forbidden),
            patch.object(StrategyMatrixRegistrationStore, "claim", side_effect=forbidden),
            patch.object(matrix_runner, "attest_utc_clock", side_effect=forbidden),
            patch.object(matrix_runner, "load_payloads", side_effect=forbidden),
            patch("builtins.print"),
        ):
            return matrix_runner.main()

    def test_batch_spec_is_deterministic_and_freezes_split_and_authority(self) -> None:
        first = self.spec()
        second = self.spec()

        self.assertEqual(first, second)
        self.assertEqual(first["split_policy"], matrix_runner.MATRIX_SPLIT_POLICY)
        self.assertEqual(first["research_only"], True)
        self.assertEqual(first["paper_authorized"], False)
        self.assertEqual(first["live_order_allowed"], False)
        self.assertTrue(matrix_runner.server.is_stock_symbol("ANET"))
        self.assertTrue(matrix_runner.server.is_stock_symbol("MRVL"))

    def test_volume_trend_spec_freezes_bar_inputs_parameters_and_risk(self) -> None:
        spec = matrix_runner.build_matrix_batch_spec(
            selection_symbols=["AAPL", "BTC-USDT"],
            confirmation_symbols=["ON", "MCHP"],
            strategies=["volume_trend"],
            position_pct=20.0,
            take_profit_pct=6.0,
            stop_loss_pct=4.0,
            fee_rate=0.0005,
            slippage_bps=2.0,
            limit=780,
            max_confirmation_candidates=1,
        )

        strategy = spec["strategy_specs"]["volume_trend"]
        self.assertEqual(strategy["signal_input"], "BARS")
        self.assertEqual(strategy["params"], {
            "trend_window": 100,
            "fast_window": 50,
            "breakout_window": 20,
            "exit_window": 10,
            "volume_window": 20,
            "volume_ratio": 1.1,
            "position_pct": 0.22,
        })
        self.assertEqual(strategy["risk"]["position_pct"], 20.0)
        self.assertEqual(strategy["risk"]["take_profit_pct"], 0.0)
        self.assertEqual(strategy["risk"]["stop_loss_pct"], 8.0)
        self.assertEqual(strategy["risk"]["leverage"], 1.0)
        self.assertTrue(matrix_runner.server.is_stock_symbol("ON"))
        self.assertTrue(matrix_runner.server.is_stock_symbol("MCHP"))

    def test_falsified_strategy_cannot_create_a_new_matrix_spec(self) -> None:
        with patch.object(matrix_runner.server, "choose_strategy") as choose_strategy:
            with self.assertRaisesRegex(
                ValueError,
                "falsified_strategy_requires_new_id_and_fresh_preregistration:trend_pullback",
            ):
                matrix_runner.build_matrix_batch_spec(
                    selection_symbols=["AAPL"],
                    confirmation_symbols=["ON"],
                    strategies=["trend_pullback"],
                    position_pct=20.0,
                    take_profit_pct=8.0,
                    stop_loss_pct=4.0,
                    fee_rate=0.0005,
                    slippage_bps=2.0,
                    limit=780,
                    max_confirmation_candidates=1,
                )
        choose_strategy.assert_not_called()

    def test_batch_spec_rejects_overlap_nonfinite_and_too_short_history(self) -> None:
        cases = [
            {"selection_symbols": ["AAPL"], "confirmation_symbols": ["AAPL"]},
            {"position_pct": math.nan},
            {"limit": 359},
            {"max_confirmation_candidates": 2},
        ]
        base = {
            "selection_symbols": ["AAPL"],
            "confirmation_symbols": ["FRESH"],
            "strategies": ["dual_ma"],
            "position_pct": 20.0,
            "take_profit_pct": 8.0,
            "stop_loss_pct": 4.0,
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "limit": 780,
            "max_confirmation_candidates": 1,
        }
        for override in cases:
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    matrix_runner.build_matrix_batch_spec(**{**base, **override})

    def test_unavailable_evidence_is_hash_sealed_and_non_authoritative(self) -> None:
        regime = matrix_runner.unavailable_regime_evidence(
            status="NOT_RUN",
            blocker="no_selection_candidate",
        )
        regime_hash = regime.pop("evidence_hash")
        self.assertEqual(regime_hash, matrix_runner.canonical_hash(regime))
        self.assertEqual(regime["paper_authorized"], False)
        self.assertEqual(regime["live_order_allowed"], False)

        correlation = matrix_runner.unavailable_correlation_matrix(
            blocker="selection_alignment_blocked",
        )
        matrix_hash = correlation.pop("matrix_hash")
        self.assertEqual(matrix_hash, matrix_runner.canonical_hash(correlation))
        self.assertEqual(correlation["paper_authorized"], False)
        self.assertEqual(correlation["live_order_allowed"], False)

    def test_formal_run_claims_registration_before_any_market_data_load(self) -> None:
        order: list[str] = []
        protocol = {
            "batch_spec": self.spec(),
            "batch_spec_hash": matrix_runner.canonical_hash(self.spec()),
        }

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
                    "claim": {"started_at_ms": 1_000_000},
                }

        def stop_at_load(*args: object, **kwargs: object) -> None:
            order.append("load")
            raise StopBeforeDataLoad

        registry = Path(matrix_runner.server.RUNTIME_DIR) / "test-formal-registry.sqlite3"
        argv = [
            "run_internal_strategy_matrix.py",
            "--registration-id", "formal-1",
            "--registry", str(registry),
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(matrix_runner, "StrategyMatrixRegistrationStore", FakeStore),
            patch.object(matrix_runner, "audit_strategy_matrix_holdout_exposure", return_value={"status": "PASS"}),
            patch.object(matrix_runner, "attest_utc_clock", return_value={"attested_now_ms": 1_000_000}),
            patch.object(matrix_runner, "load_payloads", side_effect=stop_at_load),
            self.assertRaises(StopBeforeDataLoad),
        ):
            matrix_runner.main()

        self.assertEqual(order, ["store", "get", "claim", "load"])

    def test_formal_run_rejects_command_line_strategy_overrides(self) -> None:
        registry = Path(matrix_runner.server.RUNTIME_DIR) / "test-formal-registry.sqlite3"
        argv = [
            "run_internal_strategy_matrix.py",
            "--registration-id", "formal-1",
            "--registry", str(registry),
            "--selection-symbols", "AAPL",
        ]

        with patch.object(sys, "argv", argv), self.assertRaises(SystemExit) as raised:
            matrix_runner.main()

        self.assertIn("parameters come only from the registered protocol", str(raised.exception))

    def test_formal_run_completes_registry_and_emits_self_verifying_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            reports = runtime / "reports"
            reports.mkdir(parents=True)
            registry_path = runtime / "registrations.sqlite3"
            output = reports / "strategy_matrix_formal_test.json"
            spec = self.spec()
            exposure: dict[str, object] = {
                "schema_version": "strategy-matrix-exposure-audit-v1",
                "status": "PASS",
                "evaluated_before_data_load": True,
                "symbols": ["FRESH"],
                "exposed_symbols": [],
                "evidence": {},
                "blockers": [],
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            exposure["audit_hash"] = matrix_runner.canonical_hash(exposure)
            protocol = build_strategy_matrix_protocol(
                registration_id="formal-complete",
                research_generation="TEST",
                batch_spec=spec,
                implementation_manifest=build_implementation_manifest([Path(matrix_runner.__file__)]),
                exposure_audit=exposure,
                registration_clock_attestation=attested_clock(1_000_000),
                expires_at_ms=4_000_000,
                registry_path=registry_path,
            )
            store = StrategyMatrixRegistrationStore(db_path=registry_path)
            self.assertEqual(store.register(protocol)["status"], "REGISTERED")

            def fake_load(symbols: list[str], limit: int, **kwargs: object):
                payloads = {}
                manifests = []
                for symbol in symbols:
                    rows = [
                        {
                            "date": f"2025-01-{index + 1:02d}",
                            "ts_ms": 1_735_689_600_000 + index * 86_400_000,
                            "open": 100.0 + index,
                            "high": 101.0 + index,
                            "low": 99.0 + index,
                            "close": 100.5 + index,
                            "volume": 1_000 + index,
                            "complete": True,
                        }
                        for index in range(10)
                    ]
                    market = "stock" if matrix_runner.server.is_stock_symbol(symbol) else "crypto"
                    lineage_prefix = str(kwargs.get("dataset_lineage_prefix") or "")
                    market_history_evidence = (
                        matrix_runner.server.build_history_dataset_evidence(
                            symbol=symbol,
                            rows=rows,
                            source="TEST_SOURCE",
                            dataset_lineage_id=f"{lineage_prefix}:{symbol}",
                        )
                        if market == "crypto"
                        else {}
                    )
                    payloads[symbol] = {
                        "rows": rows,
                        "source": "TEST_SOURCE",
                        "data_revision_evidence": {"status": "PASS"},
                        "market_history_evidence": market_history_evidence,
                    }
                    prepared = matrix_runner.prepare_backtest_dataset(
                        rows,
                        symbol=symbol,
                        source="TEST_SOURCE",
                        timeframe="1D",
                        minimum_rows=1,
                        market=market,
                    )["manifest"]
                    manifests.append({
                        "symbol": symbol,
                        "source": "TEST_SOURCE",
                        "status": "PASS",
                        "row_count": prepared["row_count"],
                        "first": prepared["first"],
                        "last": prepared["last"],
                        "data_hash": prepared["data_hash"],
                        "data_revision_evidence": {"status": "PASS"},
                        "market_history_evidence": market_history_evidence,
                        "blockers": [],
                    })
                return payloads, manifests, {
                    "status": "PASS",
                    "common_start": "2023-01-01",
                    "common_as_of": "2026-01-01",
                    "blockers": [],
                }

            def fake_schedule(payloads: dict[str, dict[str, object]]) -> dict[str, object]:
                return {
                    "schema_version": "calendar-split-v1",
                    "status": "PASS",
                    "common_start": "2023-01-01",
                    "common_end": "2026-01-01",
                    "train_end": "2024-07-01",
                    "validation_end": "2025-04-01",
                    "train_ratio": 0.5,
                    "validation_ratio": 0.25,
                    "minimum_segment_rows": 120,
                    "span_days": 1096,
                    "symbol_boundaries": {
                        symbol: {"train_end_index": 390, "validation_end_index": 585}
                        for symbol in payloads
                    },
                    "blockers": [],
                }

            def fake_regime(payloads: dict[str, dict[str, object]], schedule: dict[str, object]) -> dict[str, object]:
                payload: dict[str, object] = {
                    "status": "PASS",
                    "symbols": [{"symbol": symbol, "status": "PASS"} for symbol in payloads],
                    "observation_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
                payload["evidence_hash"] = matrix_runner.canonical_hash(payload)
                return payload

            def fake_correlation(payloads: dict[str, dict[str, object]]) -> dict[str, object]:
                payload: dict[str, object] = {
                    "status": "PASS",
                    "symbols": list(payloads),
                    "pairs": {},
                    "observation_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
                payload["matrix_hash"] = matrix_runner.canonical_hash(payload)
                return payload

            def fake_cell(**kwargs: object) -> dict[str, object]:
                symbol = str(kwargs["symbol"])
                strategy_id = str(kwargs["strategy_id"])
                strategy_spec = spec["strategy_specs"][strategy_id]
                payload: dict[str, object] = {
                    "symbol": symbol,
                    "strategy_id": strategy_id,
                    "dataset_status": "PASS",
                    "baseline_ok": True,
                    "validation_return_pct": 2.0,
                    "test_return_pct": 3.0,
                    "test_excess_return_pct": 1.0,
                    "test_trade_count": 3,
                    "test_max_drawdown_pct": 4.0,
                    "test_sharpe": 1.5,
                    "cost_sensitivity_status": "PASS",
                    "temporal_status": "PASS",
                    "walk_forward_status": "PASS",
                    "lookahead_status": "PASS",
                    "implementation_fingerprint": strategy_spec["implementation_fingerprint"],
                    "strategy_params": strategy_spec["params"],
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
                payload["run_hash"] = matrix_runner.canonical_hash(payload)
                return payload

            argv = [
                "run_internal_strategy_matrix.py",
                "--registration-id", "formal-complete",
                "--registry", str(registry_path),
                "--output", str(output),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(matrix_runner.server, "RUNTIME_DIR", runtime),
                patch.object(matrix_runner, "audit_strategy_matrix_holdout_exposure", return_value=exposure),
                patch.object(matrix_runner, "attest_utc_clock", side_effect=[attested_clock(2_000_000), attested_clock(3_000_000)]),
                patch.object(matrix_runner, "load_payloads", side_effect=fake_load),
                patch.object(matrix_runner, "build_matrix_split_schedule", side_effect=fake_schedule),
                patch.object(matrix_runner, "build_regime_evidence", side_effect=fake_regime),
                patch.object(matrix_runner, "build_correlation_matrix", side_effect=fake_correlation),
                patch.object(matrix_runner, "run_cell", side_effect=fake_cell),
                patch("builtins.print"),
            ):
                self.assertEqual(matrix_runner.main(), 0)

            report = __import__("json").loads(output.read_text(encoding="utf-8"))
            self.assertEqual(store.get("formal-complete")["status"], "COMPLETED")
            result = verify_strategy_matrix_evidence(
                report,
                strategy_id="dual_ma",
                strategy_params=spec["strategy_specs"]["dual_ma"]["params"],
                implementation_fingerprint=spec["strategy_specs"]["dual_ma"]["implementation_fingerprint"],
                risk=spec["strategy_specs"]["dual_ma"]["risk"],
                symbol="AAPL",
                now_ms=3_000_000,
            )
            self.assertEqual(result["status"], "PASS", result["blockers"])
            self.assertEqual(report["research_governance"]["paper_authorized"], False)
            self.assertEqual(report["research_governance"]["live_order_allowed"], False)

    def test_zero_forward_candidate_formal_report_passes_report_level_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registration_id = "matrix-zero-candidate"
            runtime, registry_path, output, _protocol, store = self.formal_fixture(
                directory,
                registration_id=registration_id,
            )

            self.assertEqual(self.run_empty_formal(
                runtime=runtime,
                registry_path=registry_path,
                output=output,
                registration_id=registration_id,
            ), 0)

            report = json.loads(output.read_text(encoding="utf-8"))
            verification = verify_strategy_matrix_report(report)
            self.assertEqual(report["forward_candidates"], [])
            self.assertEqual(report["summary"]["forward_candidates"], 0)
            self.assertEqual(verification["status"], "PASS", verification["blockers"])
            self.assertEqual(store.get(registration_id)["status"], "COMPLETED")

    def test_running_prepared_result_recovers_without_research_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registration_id = "matrix-running-recovery"
            runtime, registry_path, output, protocol, store = self.formal_fixture(
                directory,
                registration_id=registration_id,
            )
            completion_block = {
                "ok": False,
                "status": "BLOCK",
                "blockers": ["synthetic_completion_interruption"],
            }
            with (
                patch.object(
                    StrategyMatrixRegistrationStore,
                    "complete",
                    return_value=completion_block,
                ),
                self.assertRaises(SystemExit) as raised,
            ):
                self.run_empty_formal(
                    runtime=runtime,
                    registry_path=registry_path,
                    output=output,
                    registration_id=registration_id,
                )

            prepared = prepared_research_result_path(
                output.parent,
                protocol_hash=str(protocol["protocol_hash"]),
            )
            self.assertIn("PREPARED_RECOVERY_REQUIRED", str(raised.exception))
            self.assertTrue(prepared.exists())
            self.assertFalse(output.exists())
            self.assertEqual(store.get(registration_id)["status"], "RUNNING")
            self.assertEqual(self.recover_without_research_work(
                runtime=runtime,
                registry_path=registry_path,
                output=output,
                registration_id=registration_id,
            ), 0)
            self.assertTrue(output.exists())
            self.assertEqual(store.get(registration_id)["status"], "COMPLETED")

    def test_completed_prepared_result_recovers_missing_final_without_research_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registration_id = "matrix-completed-recovery"
            runtime, registry_path, output, _protocol, store = self.formal_fixture(
                directory,
                registration_id=registration_id,
            )
            self.assertEqual(self.run_empty_formal(
                runtime=runtime,
                registry_path=registry_path,
                output=output,
                registration_id=registration_id,
            ), 0)
            output.unlink()

            with patch.object(
                StrategyMatrixRegistrationStore,
                "complete",
                side_effect=AssertionError("COMPLETED recovery must not complete again"),
            ):
                self.assertEqual(self.recover_without_research_work(
                    runtime=runtime,
                    registry_path=registry_path,
                    output=output,
                    registration_id=registration_id,
                ), 0)
            self.assertTrue(output.exists())
            self.assertEqual(store.get(registration_id)["status"], "COMPLETED")

    def test_resealed_semantic_tamper_in_prepared_report_blocks_before_research_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registration_id = "matrix-tamper-recovery"
            runtime, registry_path, output, protocol, _store = self.formal_fixture(
                directory,
                registration_id=registration_id,
            )
            self.assertEqual(self.run_empty_formal(
                runtime=runtime,
                registry_path=registry_path,
                output=output,
                registration_id=registration_id,
            ), 0)
            output.unlink()
            prepared_path = prepared_research_result_path(
                output.parent,
                protocol_hash=str(protocol["protocol_hash"]),
            )
            prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
            report = prepared["report"]
            snapshot = report["dataset_snapshot"]
            snapshot["registration_id"] = "different-registration"
            snapshot["snapshot_hash"] = matrix_runner.canonical_hash({
                key: value for key, value in snapshot.items() if key != "snapshot_hash"
            })
            report["matrix_result_hash"] = matrix_runner.strategy_matrix_result_hash(report)
            governance = report["research_governance"]
            completion = governance["completion_receipt"]
            completion["result_hash"] = report["matrix_result_hash"]
            completion["completion_hash"] = matrix_runner.canonical_hash({
                key: value for key, value in completion.items() if key != "completion_hash"
            })
            governance["completion_hash"] = completion["completion_hash"]
            governance["governance_hash"] = matrix_runner.canonical_hash({
                key: value for key, value in governance.items() if key != "governance_hash"
            })
            report["batch_run_hash"] = matrix_runner.strategy_matrix_run_hash(report)
            prepared["result_hash"] = report["matrix_result_hash"]
            prepared["prepared_hash"] = matrix_runner.canonical_hash({
                key: value for key, value in prepared.items() if key != "prepared_hash"
            })
            prepared_path.write_text(
                json.dumps(prepared, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit) as raised:
                self.recover_without_research_work(
                    runtime=runtime,
                    registry_path=registry_path,
                    output=output,
                    registration_id=registration_id,
                )
            self.assertIn(
                "prepared_result_report:matrix_dataset_snapshot_registration_mismatch",
                str(raised.exception),
            )
            self.assertFalse(output.exists())

    def test_conflicting_final_blocks_recovery_before_research_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registration_id = "matrix-final-conflict"
            runtime, registry_path, output, _protocol, _store = self.formal_fixture(
                directory,
                registration_id=registration_id,
            )
            self.assertEqual(self.run_empty_formal(
                runtime=runtime,
                registry_path=registry_path,
                output=output,
                registration_id=registration_id,
            ), 0)
            output.write_text('{"conflict":true}', encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                self.recover_without_research_work(
                    runtime=runtime,
                    registry_path=registry_path,
                    output=output,
                    registration_id=registration_id,
                )
            self.assertIn("strategy_matrix_final_output_conflict", str(raised.exception))
            self.assertEqual(output.read_text(encoding="utf-8"), '{"conflict":true}')

    def test_final_publish_failure_is_non_success_after_registry_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registration_id = "matrix-final-publish-failure"
            runtime, registry_path, output, _protocol, store = self.formal_fixture(
                directory,
                registration_id=registration_id,
            )
            publication_failure = {
                "status": "BLOCK",
                "blockers": ["synthetic_final_publish_failure"],
                "published": False,
                "path": str(output),
            }
            with (
                patch.object(
                    matrix_runner,
                    "publish_json_no_clobber",
                    return_value=publication_failure,
                ),
                self.assertRaises(SystemExit) as raised,
            ):
                self.run_empty_formal(
                    runtime=runtime,
                    registry_path=registry_path,
                    output=output,
                    registration_id=registration_id,
                )

            self.assertIn("FINAL_RECOVERY_REQUIRED", str(raised.exception))
            self.assertEqual(store.get(registration_id)["status"], "COMPLETED")
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
