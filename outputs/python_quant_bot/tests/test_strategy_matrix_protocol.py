from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.implementation_manifest import build_implementation_manifest
from exchange_terminal.services.strategy_hypothesis_preregistration import (
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    build_strategy_hypothesis_preregistration,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    StrategyMatrixRegistrationStore,
    audit_strategy_matrix_holdout_exposure,
    build_strategy_matrix_protocol,
    canonical_hash,
    verify_strategy_research_canonical_registry_path,
    verify_strategy_matrix_protocol,
)
from exchange_terminal.services.strategy_preregistered_failure_admission import (
    build_strategy_preregistered_failure_admission_v3,
    verify_strategy_preregistered_failure_admission_v3_receipt,
)
from exchange_terminal.services.strategy_research import (
    aggregate_validation_variant,
    build_parameter_stability_snapshot,
    freeze_validation_candidates,
)
from exchange_terminal.services.strategy_research_protocol_artifact import (
    build_strategy_research_protocol_artifact_binding,
    publish_strategy_research_protocol_artifact_no_clobber,
)
from exchange_terminal.services.strategy_research_search_lineage import (
    build_strategy_research_search_lineage,
)
from tests.portfolio_governance_fixtures import attested_clock


def exposure_audit(symbols: list[str]) -> dict[str, object]:
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
    payload["audit_hash"] = canonical_hash(payload)
    return payload


def batch_spec() -> dict[str, object]:
    risk = {
        "position_pct": 20.0,
        "take_profit_pct": 8.0,
        "stop_loss_pct": 4.0,
        "fee_rate": 0.0005,
        "slippage_bps": 2.0,
        "leverage": 1.0,
    }
    return {
        "schema_version": "strategy-benchmark-v7",
        "selection_symbols": ["AAPL"],
        "confirmation_symbols": ["FRESH"],
        "strategies": ["dual_ma"],
        "strategy_specs": {
            "dual_ma": {
                "params": {"fast_window": 20, "slow_window": 60},
                "implementation_fingerprint": "strategy-fingerprint",
                "risk": risk,
            },
        },
        "risk": risk,
        "limit": 780,
        "max_confirmation_candidates": 1,
        "selection_rule": "fixed_params_common_calendar_cross_symbol_oos_then_top2_holdout",
        "split_policy": {
            "schema_version": "calendar-split-v1",
            "train_ratio": 0.50,
            "validation_ratio": 0.25,
            "minimum_segment_rows": 120,
        },
        "data_policy": {
            "timeframe": "1D",
            "completed_candles_only": True,
            "alignment_schema_version": "daily-batch-alignment-v2",
            "max_endpoint_skew_days": 3,
            "max_boundary_skew_days": 7,
            "frozen_stock_revision_evidence_required": True,
            "exact_dataset_snapshot_required": True,
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def frozen_variant(index: int, *, prefix: str = "variant") -> dict[str, object]:
    params = {"period": index + 1}
    risk = dict(batch_spec()["risk"])
    risk_profile: dict[str, object] = {
        "version": "strategy-risk-profile-v1",
        "profile_id": "TEST_FROZEN_RISK",
        "strategy_id": "dual_ma",
        "risk": risk,
        "rationale": "Frozen unit-test research risk profile.",
    }
    risk_profile["risk_hash"] = canonical_hash(risk_profile)
    return {
        "strategy_id": "dual_ma",
        "variant_label": f"candidate-{index}",
        "variant_id": f"{prefix}-{index}",
        "params": params,
        "param_hash": canonical_hash(params),
        "implementation_fingerprint": "strategy-fingerprint",
        "risk_profile": risk_profile,
        "risk": risk,
        "risk_hash": risk_profile["risk_hash"],
    }


def selection_cell(variant: dict[str, object]) -> dict[str, object]:
    return {
        "strategy_id": variant["strategy_id"],
        "variant_id": variant["variant_id"],
        "symbol": "AAPL",
        "dataset_status": "PASS",
        "train_ok": True,
        "validation_ok": True,
        "train_return_pct": 8.0,
        "validation_return_pct": 6.0,
        "validation_excess_return_pct": 4.0,
        "validation_trade_count": 4,
        "validation_max_drawdown_pct": 5.0,
        "validation_sharpe": 1.5,
        "validation_drawdown_improvement_pct": 5.0,
        "validation_sharpe_excess": 0.8,
        "validation_risk_efficiency_excess": 0.8,
        "lookahead_status": "PASS",
        "cost_sensitivity_status": "PASS",
        "cost_sensitivity": {
            "status": "PASS",
            "verification_status": "PASS",
            "stage": "DEVELOPMENT_SELECTION",
            "break_even_preserved": True,
            "worst_return_pct": 1.0,
            "blockers": [],
        },
        "fold_stability_status": "PASS",
        "fold_stability": {
            "schema_version": "strategy-fixed-chronological-slice-evidence-v2",
            "verification_status": "PASS",
            "status": "PASS",
            "parameters_refit_per_fold": False,
            "walk_forward_optimization_claim_allowed": False,
            "usable_folds": 3,
            "positive_folds": 2,
            "blockers": [],
        },
    }


class StrategyMatrixProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.reports = self.root / "reports"
        self.runtime = self.root / "runtime"
        self.reports.mkdir()
        self.runtime.mkdir()
        self.source = self.root / "matrix_source.py"
        self.source.write_text("VALUE = 1\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def protocol(self, *, registration_id: str = "matrix-registration-1") -> dict[str, object]:
        return build_strategy_matrix_protocol(
            registration_id=registration_id,
            research_generation="G47_TEST",
            batch_spec=batch_spec(),
            implementation_manifest=build_implementation_manifest([self.source]),
            exposure_audit=exposure_audit(["FRESH"]),
            registration_clock_attestation=attested_clock(1_000_000),
            expires_at_ms=4_000_000,
            registry_path=self.runtime / f"{registration_id}.sqlite3",
        )

    def test_schema14_registry_path_is_one_active_runtime_root_file(self) -> None:
        for name in ("alternate-a", "alternate-b"):
            subdir = self.runtime / name
            subdir.mkdir()
            alternate = subdir / "strategy_research_registrations.sqlite3"
            with self.subTest(name=name), self.assertRaisesRegex(
                ValueError,
                "strategy_research_registry_path_preflight",
            ):
                StrategyMatrixRegistrationStore(
                    db_path=alternate,
                    canonical_runtime_root=self.runtime,
                )
            self.assertFalse(alternate.exists())

        relative_path = Path(
            f"schema14-relative-no-touch-{id(self)}"
        ) / "strategy_research_registrations.sqlite3"
        relative = verify_strategy_research_canonical_registry_path(
            relative_path,
            active_runtime_root=self.runtime,
        )
        self.assertEqual(relative["status"], "BLOCK")
        self.assertIn(
            "strategy_research_registry_path_relative",
            relative["blockers"],
        )
        with self.assertRaisesRegex(
            ValueError,
            "strategy_research_registry_path_preflight",
        ):
            StrategyMatrixRegistrationStore(
                db_path=relative_path,
                canonical_runtime_root=self.runtime,
            )
        self.assertFalse(relative_path.exists())

        alias_root = self.root / "alias-runtime"
        alias_root.mkdir()
        alias = (
            alias_root
            / "alias-component"
            / ".."
            / "strategy_research_registrations.sqlite3"
        )
        alias_verification = verify_strategy_research_canonical_registry_path(
            alias,
            active_runtime_root=alias_root,
        )
        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertIn(
            "strategy_research_registry_path_alias",
            alias_verification["blockers"],
        )
        with self.assertRaisesRegex(
            ValueError,
            "strategy_research_registry_path_preflight",
        ):
            StrategyMatrixRegistrationStore(
                db_path=alias,
                canonical_runtime_root=alias_root,
            )
        self.assertFalse(
            (alias_root / "strategy_research_registrations.sqlite3").exists()
        )

        link_root = self.root / "link-runtime"
        link_target = self.root / "link-target"
        link_target.mkdir()
        link_target_db = (
            link_target / "strategy_research_registrations.sqlite3"
        )
        link_target_db.write_bytes(b"untouched-reparse-target")
        try:
            link_root.symlink_to(link_target, target_is_directory=True)
        except OSError:
            link_root = None
        if link_root is not None:
            linked = link_root / "strategy_research_registrations.sqlite3"
            linked_verification = verify_strategy_research_canonical_registry_path(
                linked,
                active_runtime_root=link_root,
            )
            self.assertEqual(linked_verification["status"], "BLOCK")
            self.assertTrue(any(
                "reparse" in item
                for item in linked_verification["blockers"]
            ))
            with self.assertRaisesRegex(
                ValueError,
                "strategy_research_registry_path_preflight",
            ):
                StrategyMatrixRegistrationStore(
                    db_path=linked,
                    canonical_runtime_root=link_root,
                )
            self.assertEqual(
                link_target_db.read_bytes(),
                b"untouched-reparse-target",
            )
        else:
            simulated_root = self.root / "simulated-reparse-runtime"
            simulated_root.mkdir()
            simulated_db = (
                simulated_root / "strategy_research_registrations.sqlite3"
            )
            original_is_symlink = Path.is_symlink

            def simulated_is_symlink(candidate: Path) -> bool:
                return candidate == simulated_root or original_is_symlink(candidate)

            with patch.object(Path, "is_symlink", simulated_is_symlink):
                simulated = verify_strategy_research_canonical_registry_path(
                    simulated_db,
                    active_runtime_root=simulated_root,
                )
                self.assertEqual(simulated["status"], "BLOCK")
                self.assertIn(
                    "strategy_research_registry_path_reparse_point",
                    simulated["blockers"],
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "strategy_research_registry_path_preflight",
                ):
                    StrategyMatrixRegistrationStore(
                        db_path=simulated_db,
                        canonical_runtime_root=simulated_root,
                    )
            self.assertFalse(simulated_db.exists())

        canonical = self.runtime / "strategy_research_registrations.sqlite3"
        verification = verify_strategy_research_canonical_registry_path(
            canonical,
            active_runtime_root=self.runtime,
        )
        self.assertEqual(verification["status"], "PASS")
        store = StrategyMatrixRegistrationStore(
            db_path=canonical,
            canonical_runtime_root=self.runtime,
        )
        self.assertEqual(store.audit()["status"], "PASS")

    def test_schema14_admission_requires_live_canonical_registry_transaction(self) -> None:
        registry_path = self.runtime / "strategy_research_registrations.sqlite3"
        store = StrategyMatrixRegistrationStore(
            db_path=registry_path,
            canonical_runtime_root=self.runtime,
        )
        protocol = self.schema14_protocol(store=store)
        self.assertEqual(verify_strategy_matrix_protocol(protocol)["status"], "PASS")
        self.assertEqual(store.register(protocol)["status"], "REGISTERED")
        claim = store.claim(
            "schema14-live",
            clock_attestation=attested_clock(2_000_000),
            exposure_audit=exposure_audit(["FRESH"]),
        )
        self.assertEqual(claim["status"], "CLAIMED")
        live = store.verify_search_lineage_live("schema14-live")
        self.assertEqual(live["status"], "PASS")
        self.assertEqual(live["cumulative_trial_count"], 3)

        spec = protocol["batch_spec"]
        variants = list(spec["variants"])
        cells = [selection_cell(variant) for variant in variants]
        rankings = [
            aggregate_validation_variant(
                variant,
                [item for item in cells if item["variant_id"] == variant["variant_id"]],
                required_symbols=1,
                total_variant_trials=3,
            )
            for variant in variants
        ]
        rankings.sort(key=lambda row: float(row["adjusted_score"]), reverse=True)
        plateau = build_parameter_stability_snapshot(
            rankings,
            frozen_variants=variants,
        )
        candidates = freeze_validation_candidates(rankings, max_candidates=1)

        receipt_only = build_strategy_preregistered_failure_admission_v3(
            batch_spec=spec,
            hypothesis_preregistration=spec["hypothesis_preregistration"],
            parameter_stability=plateau,
            selection_cells=cells,
            validation_candidates=candidates,
            registration_context=live["registration_context"],
        )
        self.assertEqual(receipt_only["status"], "BLOCK")
        self.assertEqual(receipt_only["admitted_variant_ids"], [])
        self.assertIn(
            "strategy_search_lineage_live_registry_verification_required",
            receipt_only["blockers"],
        )
        self.assertEqual(
            receipt_only["registration_binding"]["verification_scope"],
            "SELF_CONSISTENT_RECEIPT_ONLY",
        )

        admitted = store.build_search_lineage_admission(
            "schema14-live",
            parameter_stability=plateau,
            selection_cells=cells,
            validation_candidates=candidates,
        )
        self.assertEqual(admitted["status"], "PASS")
        self.assertEqual(len(admitted["admitted_variant_ids"]), 1)
        self.assertEqual(
            admitted["registration_binding"]["status"],
            "LIVE_REGISTRY_VERIFIED",
        )
        offline = verify_strategy_preregistered_failure_admission_v3_receipt(
            admitted,
            batch_spec=spec,
            hypothesis_preregistration=spec["hypothesis_preregistration"],
            parameter_stability=plateau,
            selection_cells=cells,
            validation_candidates=candidates,
            registration_context=live["registration_context"],
        )
        self.assertEqual(offline["status"], "PASS", offline["blockers"])
        self.assertEqual(
            offline["verification_scope"],
            "OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY",
        )
        self.assertFalse(offline["live_registry_verified"])

        claim_tampered = deepcopy(admitted)
        claim_tampered["registration_binding"]["claim_hash"] = "f" * 64
        claim_tampered_content = dict(claim_tampered)
        claim_tampered_content.pop("admission_hash")
        claim_tampered["admission_hash"] = canonical_hash(
            claim_tampered_content
        )
        self.assertEqual(
            verify_strategy_preregistered_failure_admission_v3_receipt(
                claim_tampered,
                batch_spec=spec,
                hypothesis_preregistration=spec[
                    "hypothesis_preregistration"
                ],
                parameter_stability=plateau,
                selection_cells=cells,
                validation_candidates=candidates,
                registration_context=live["registration_context"],
            )["status"],
            "BLOCK",
        )

        peer = StrategyMatrixRegistrationStore(
            db_path=registry_path,
            canonical_runtime_root=self.runtime,
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            concurrent_live = list(executor.map(
                lambda current: current.verify_search_lineage_live(
                    "schema14-live"
                ),
                (store, peer),
            ))
        self.assertTrue(all(
            item["status"] == "PASS" for item in concurrent_live
        ))
        self.assertEqual(
            concurrent_live[0]["live_registry_binding"],
            concurrent_live[1]["live_registry_binding"],
        )

        connection = sqlite3.connect(registry_path)
        connection.execute(
            """
            UPDATE strategy_matrix_registration_events
            SET previous_event_hash = ?
            WHERE registration_id = ? AND event_type = 'CLAIMED'
            """,
            ("f" * 64, "schema14-live"),
        )
        connection.commit()
        connection.close()
        tampered = store.verify_search_lineage_live("schema14-live")
        self.assertEqual(tampered["status"], "BLOCK")
        self.assertTrue(any(
            "registry_integrity" in item
            or "previous_tail" in item
            for item in tampered["blockers"]
        ))

    def lineage_protocol(
        self,
        *,
        registry_path: Path,
        registration_id: str,
        lineage: dict[str, object],
        registered_at_ms: int,
    ) -> dict[str, object]:
        spec = batch_spec()
        spec["variants"] = [
            frozen_variant(index)
            for index in range(int(lineage["current_trial_count"]))
        ]
        # Registry lineage mechanics are isolated from the schema-14 nested
        # writer contract in these transaction tests.
        spec["report_schema_version"] = 13
        spec["search_lineage"] = dict(lineage)
        return build_strategy_matrix_protocol(
            registration_id=registration_id,
            research_generation=f"SEARCH-{registration_id}",
            batch_spec=spec,
            implementation_manifest=build_implementation_manifest([self.source]),
            exposure_audit=exposure_audit(["FRESH"]),
            registration_clock_attestation=attested_clock(registered_at_ms),
            expires_at_ms=registered_at_ms + 3_000_000,
            registry_path=registry_path,
        )

    def schema14_protocol(
        self,
        *,
        store: StrategyMatrixRegistrationStore,
        registration_id: str = "schema14-live",
    ) -> dict[str, object]:
        variants = [frozen_variant(index) for index in range(3)]
        lineage_plan = store.derive_search_lineage(
            search_family_id="causal-trend-global-search",
            current_trial_count=len(variants),
        )
        self.assertEqual(lineage_plan["status"], "PASS")
        hypothesis = build_strategy_hypothesis_preregistration({
            "schema_version": (
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
            ),
            "hypothesis_id": "schema14-live-hypothesis",
            "research_generation": "SCHEMA14-LIVE",
            "search_family_id": "causal-trend-global-search",
            "strategy_ids": ["dual_ma"],
            "mechanism_family": "causal trend persistence",
            "hypothesis_statement": (
                "Completed-bar causal trend persistence should retain positive "
                "benchmark excess under the frozen contract."
            ),
            "novelty_statement": (
                "This mechanism is independently registered and does not retune "
                "a previously falsified strategy family."
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
        spec = batch_spec()
        spec.update({
            "workflow": "NESTED_VARIANT_RESEARCH",
            "report_schema_version": 14,
            "research_generation": "SCHEMA14-LIVE",
            "selection_test_policy": "BLIND_ONCE",
            "max_test_candidates": 1,
            "variants": variants,
            "search_lineage": lineage_plan["lineage"],
            "hypothesis_preregistration": hypothesis,
            "hypothesis_preregistration_hash": hypothesis["hypothesis_hash"],
        })
        artifact_path = self.reports / f"{registration_id}.json"
        protocol = build_strategy_matrix_protocol(
            registration_id=registration_id,
            research_generation="SCHEMA14-LIVE",
            batch_spec=spec,
            implementation_manifest=build_implementation_manifest([self.source]),
            exposure_audit=exposure_audit(["FRESH"]),
            registration_clock_attestation=attested_clock(1_000_000),
            expires_at_ms=4_000_000,
            registry_path=store.db_path,
            protocol_artifact=(
                build_strategy_research_protocol_artifact_binding(artifact_path)
            ),
        )
        publication = publish_strategy_research_protocol_artifact_no_clobber(
            artifact_path,
            protocol,
        )
        self.assertEqual(publication["status"], "PUBLISHED")
        return protocol

    def test_holdout_exposure_audit_detects_report_sqlite_and_service_log(self) -> None:
        clean = audit_strategy_matrix_holdout_exposure(self.reports, self.runtime, ["FRESH"])
        self.assertEqual(clean["status"], "PASS")

        report = {
            "dataset_manifest": [{"symbol": "REPORT-HIT"}],
            "selection_cells": [],
            "confirmation_cells": [],
        }
        (self.reports / "strategy_matrix_prior.json").write_text(
            json.dumps(report),
            encoding="utf-8",
        )
        database_dir = self.runtime / "nested"
        database_dir.mkdir()
        connection = sqlite3.connect(database_dir / "exposure.sqlite3")
        connection.execute("CREATE TABLE candles(symbol TEXT NOT NULL)")
        connection.execute("INSERT INTO candles(symbol) VALUES ('SQL-HIT')")
        connection.commit()
        connection.close()
        (self.runtime / "service_stdout.log").write_text(
            "GET /api/market/candles?symbol=LOG-HIT&bar=1D\n",
            encoding="utf-8",
        )

        result = audit_strategy_matrix_holdout_exposure(
            self.reports,
            self.runtime,
            ["REPORT-HIT", "SQL-HIT", "LOG-HIT"],
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["exposed_symbols"], ["LOG-HIT", "REPORT-HIT", "SQL-HIT"])
        self.assertEqual(result["paper_authorized"], False)
        self.assertEqual(result["live_order_allowed"], False)

    def test_protocol_verifier_rejects_tampering_and_string_false_authority(self) -> None:
        protocol = self.protocol()
        self.assertEqual(verify_strategy_matrix_protocol(protocol)["status"], "PASS")

        tampered = deepcopy(protocol)
        tampered["batch_spec"]["limit"] = 900
        self.assertIn(
            "matrix_protocol_hash_invalid",
            verify_strategy_matrix_protocol(tampered)["blockers"],
        )

        authority = deepcopy(protocol)
        authority["batch_spec"]["paper_authorized"] = "false"
        authority["batch_spec_hash"] = canonical_hash(authority["batch_spec"])
        authority.pop("protocol_hash")
        authority["protocol_hash"] = canonical_hash(authority)
        result = verify_strategy_matrix_protocol(authority)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("matrix_protocol_batch_has_execution_authority", result["blockers"])

        source_tamper = deepcopy(protocol)
        source_tamper["implementation_source_snapshot"]["files"][0]["content_base64"] = "VkFMVUUgPSA5Cg=="
        source_tamper.pop("protocol_hash")
        source_tamper["protocol_hash"] = canonical_hash(source_tamper)
        result = verify_strategy_matrix_protocol(source_tamper, verify_current_implementation=False)
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("source_snapshot" in item for item in result["blockers"]))

    def test_registry_single_use_completion_and_integrity_audit(self) -> None:
        store = StrategyMatrixRegistrationStore(db_path=self.runtime / "matrix-registration-1.sqlite3")
        protocol = self.protocol()
        registered = store.register(protocol)
        claimed = store.claim(
            "matrix-registration-1",
            clock_attestation=attested_clock(2_000_000),
            exposure_audit=exposure_audit(["FRESH"]),
        )
        second = store.claim(
            "matrix-registration-1",
            clock_attestation=attested_clock(2_100_000),
            exposure_audit=exposure_audit(["FRESH"]),
        )
        completed = store.complete(
            "matrix-registration-1",
            result_hash="a" * 64,
            dataset_manifest_hash="b" * 64,
            clock_attestation=attested_clock(3_000_000),
        )

        self.assertEqual(registered["status"], "REGISTERED")
        self.assertEqual(claimed["status"], "CLAIMED")
        self.assertEqual(second["status"], "BLOCK")
        self.assertIn("matrix_registration_already_consumed:RUNNING", second["blockers"])
        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(store.get("matrix-registration-1")["status"], "COMPLETED")
        self.assertEqual(store.audit()["status"], "PASS")

        connection = sqlite3.connect(self.runtime / "matrix-registration-1.sqlite3")
        connection.execute(
            "UPDATE strategy_matrix_registrations SET claim_json = ? WHERE registration_id = ?",
            ("{}", "matrix-registration-1"),
        )
        connection.commit()
        connection.close()
        self.assertEqual(store.audit()["status"], "BLOCK")

    def test_source_change_blocks_claim_without_consuming_registration(self) -> None:
        store = StrategyMatrixRegistrationStore(db_path=self.runtime / "source-change.sqlite3")
        store.register(self.protocol(registration_id="source-change"))
        self.source.write_text("VALUE = 2\n", encoding="utf-8")

        result = store.claim(
            "source-change",
            clock_attestation=attested_clock(2_000_000),
            exposure_audit=exposure_audit(["FRESH"]),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("implementation_source_changed" in item for item in result["blockers"]))
        self.assertEqual(store.get("source-change")["status"], "REGISTERED")

    def test_concurrent_claim_allows_exactly_one_consumer(self) -> None:
        path = self.runtime / "concurrent.sqlite3"
        StrategyMatrixRegistrationStore(db_path=path).register(
            self.protocol(registration_id="concurrent")
        )

        def claim_once() -> dict[str, object]:
            return StrategyMatrixRegistrationStore(db_path=path).claim(
                "concurrent",
                clock_attestation=attested_clock(2_000_000),
                exposure_audit=exposure_audit(["FRESH"]),
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: claim_once(), range(2)))

        self.assertEqual(sum(result["status"] == "CLAIMED" for result in results), 1)
        self.assertEqual(sum(result["status"] == "BLOCK" for result in results), 1)

    def test_completion_time_cannot_precede_claim(self) -> None:
        store = StrategyMatrixRegistrationStore(db_path=self.runtime / "time-order.sqlite3")
        store.register(self.protocol(registration_id="time-order"))
        store.claim(
            "time-order",
            clock_attestation=attested_clock(2_000_000),
            exposure_audit=exposure_audit(["FRESH"]),
        )

        result = store.complete(
            "time-order",
            result_hash="a" * 64,
            dataset_manifest_hash="b" * 64,
            clock_attestation=attested_clock(1_500_000),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("matrix_completion_temporal_order_invalid", result["blockers"])
        self.assertEqual(store.get("time-order")["status"], "RUNNING")

    def test_source_change_after_claim_blocks_completion(self) -> None:
        store = StrategyMatrixRegistrationStore(db_path=self.runtime / "completion-source.sqlite3")
        store.register(self.protocol(registration_id="completion-source"))
        store.claim(
            "completion-source",
            clock_attestation=attested_clock(2_000_000),
            exposure_audit=exposure_audit(["FRESH"]),
        )
        self.source.write_text("VALUE = 3\n", encoding="utf-8")

        result = store.complete(
            "completion-source",
            result_hash="a" * 64,
            dataset_manifest_hash="b" * 64,
            clock_attestation=attested_clock(3_000_000),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("implementation_source_changed" in item for item in result["blockers"]))
        self.assertEqual(store.get("completion-source")["status"], "RUNNING")

    def test_registry_derives_and_transactionally_binds_cumulative_search_trials(self) -> None:
        registry_path = self.runtime / "search-lineage.sqlite3"
        store = StrategyMatrixRegistrationStore(db_path=registry_path)
        first_plan = store.derive_search_lineage(
            search_family_id="causal-breakout-v1",
            current_trial_count=3,
        )
        self.assertEqual(first_plan["status"], "PASS")
        first = self.lineage_protocol(
            registry_path=registry_path,
            registration_id="search-registration-1",
            lineage=first_plan["lineage"],
            registered_at_ms=1_000_000,
        )
        self.assertEqual(store.register(first)["status"], "REGISTERED")

        legacy_spec = batch_spec()
        legacy_spec.update({
            "workflow": "NESTED_VARIANT_RESEARCH",
            "report_schema_version": 6,
            "research_generation": "LEGACY-BETWEEN-LINEAGE-RUNS",
            "variants": [
                frozen_variant(index, prefix="legacy-variant")
                for index in range(3)
            ],
        })
        legacy = build_strategy_matrix_protocol(
            registration_id="search-registration-legacy",
            research_generation="LEGACY-BETWEEN-LINEAGE-RUNS",
            batch_spec=legacy_spec,
            implementation_manifest=build_implementation_manifest([self.source]),
            exposure_audit=exposure_audit(["FRESH"]),
            registration_clock_attestation=attested_clock(1_500_000),
            expires_at_ms=4_500_000,
            registry_path=registry_path,
        )
        self.assertEqual(
            verify_strategy_matrix_protocol(legacy)["status"],
            "PASS",
        )
        self.assertEqual(store.register(legacy)["status"], "REGISTERED")

        second_plan = store.derive_search_lineage(
            search_family_id="renamed-family-cannot-reset",
            current_trial_count=3,
        )
        second_lineage = second_plan["lineage"]
        self.assertEqual(
            second_lineage["trial_count_scope"],
            "GLOBAL_REGISTERED_STRATEGY_RESEARCH",
        )
        self.assertEqual(
            second_lineage["search_family_id"],
            "renamed-family-cannot-reset",
        )
        self.assertEqual(second_lineage["prior_trial_count"], 6)
        self.assertEqual(second_lineage["cumulative_trial_count"], 9)
        self.assertEqual(
            second_lineage["parent_registration_hash"],
            legacy["protocol_hash"],
        )
        self.assertEqual(len(second_lineage["parent_registry_event_hash"]), 64)
        second = self.lineage_protocol(
            registry_path=registry_path,
            registration_id="search-registration-2",
            lineage=second_lineage,
            registered_at_ms=2_000_000,
        )
        self.assertEqual(store.register(second)["status"], "REGISTERED")

        final_plan = store.derive_search_lineage(
            search_family_id="causal-breakout-v1",
            current_trial_count=3,
        )
        self.assertEqual(final_plan["lineage"]["prior_registration_count"], 3)
        self.assertEqual(final_plan["lineage"]["prior_trial_count"], 9)
        self.assertEqual(final_plan["lineage"]["cumulative_trial_count"], 12)
        self.assertEqual(store.audit()["status"], "PASS")

    def test_malformed_legacy_variants_cannot_poison_global_trial_ledger(self) -> None:
        registry_path = self.runtime / "malformed-legacy-lineage.sqlite3"
        store = StrategyMatrixRegistrationStore(db_path=registry_path)
        malformed_spec = batch_spec()
        malformed_spec.update({
            "workflow": "NESTED_VARIANT_RESEARCH",
            "report_schema_version": 6,
            "research_generation": "MALFORMED-LEGACY",
            "variants": {"variant_id": "not-a-frozen-list"},
        })
        malformed = build_strategy_matrix_protocol(
            registration_id="malformed-legacy",
            research_generation="MALFORMED-LEGACY",
            batch_spec=malformed_spec,
            implementation_manifest=build_implementation_manifest([self.source]),
            exposure_audit=exposure_audit(["FRESH"]),
            registration_clock_attestation=attested_clock(1_000_000),
            expires_at_ms=4_000_000,
            registry_path=registry_path,
        )

        verification = verify_strategy_matrix_protocol(malformed)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "matrix_protocol_variants_type_invalid",
            verification["blockers"],
        )
        registration = store.register(malformed)
        self.assertEqual(registration["status"], "BLOCK")
        self.assertEqual(store.get("malformed-legacy")["status"], "NOT_FOUND")
        audit = store.audit()
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["event_count"], 0)

        next_plan = store.derive_search_lineage(
            search_family_id="clean-after-malformed-legacy",
            current_trial_count=3,
        )
        self.assertEqual(next_plan["status"], "PASS")
        self.assertEqual(next_plan["lineage"]["prior_registration_count"], 0)
        self.assertEqual(next_plan["lineage"]["prior_trial_count"], 0)
        self.assertEqual(next_plan["lineage"]["cumulative_trial_count"], 3)

    def test_stale_or_parallel_lineage_plan_cannot_reset_family_trial_count(self) -> None:
        registry_path = self.runtime / "search-lineage-race.sqlite3"
        store = StrategyMatrixRegistrationStore(db_path=registry_path)
        genesis = build_strategy_research_search_lineage(
            search_family_id="causal-breakout-v1",
            prior_registrations=[],
            current_trial_count=3,
        )
        first = self.lineage_protocol(
            registry_path=registry_path,
            registration_id="search-race-parent",
            lineage=genesis,
            registered_at_ms=1_000_000,
        )
        stale = self.lineage_protocol(
            registry_path=registry_path,
            registration_id="search-race-stale",
            lineage=genesis,
            registered_at_ms=1_100_000,
        )
        self.assertEqual(store.register(first)["status"], "REGISTERED")
        stale_result = store.register(stale)
        self.assertEqual(stale_result["status"], "BLOCK")
        self.assertIn(
            "matrix_registry_search_lineage_transaction_mismatch",
            stale_result["blockers"],
        )

        shared_plan = store.derive_search_lineage(
            search_family_id="causal-breakout-v1",
            current_trial_count=3,
        )["lineage"]
        parallel = [
            self.lineage_protocol(
                registry_path=registry_path,
                registration_id=f"search-race-child-{index}",
                lineage=shared_plan,
                registered_at_ms=2_000_000 + index,
            )
            for index in range(2)
        ]
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(store.register, parallel))
        self.assertEqual(sum(item["status"] == "REGISTERED" for item in results), 1)
        self.assertEqual(sum(item["status"] == "BLOCK" for item in results), 1)
        blocked = next(item for item in results if item["status"] == "BLOCK")
        self.assertIn(
            "matrix_registry_search_lineage_transaction_mismatch",
            blocked["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
