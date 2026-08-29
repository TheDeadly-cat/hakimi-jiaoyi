from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cluster_gate import build_correlation_cluster_preregistration
from exchange_terminal.services.strategy_correlation_multiplicity_protocol import build_strategy_correlation_multiplicity_protocol_registration
from exchange_terminal.services.strategy_correlation_multiplicity_registration import build_strategy_correlation_multiplicity_family_registration
from exchange_terminal.services.strategy_correlation_protocol_binding import build_strategy_correlation_protocol_registration_v2
from exchange_terminal.services.strategy_hypothesis_preregistration import STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3, build_strategy_hypothesis_preregistration
from exchange_terminal.services.strategy_matrix_protocol import StrategyMatrixRegistrationStore, build_strategy_matrix_protocol
from exchange_terminal.services.strategy_matrix_multiplicity_report import build_strategy_matrix_multiplicity_report, verify_strategy_matrix_multiplicity_report
from exchange_terminal.services.strategy_lab_projection import build_strategy_lab_projection
from exchange_terminal.services.strategy_research_evidence import STRATEGY_RESEARCH_MULTIPLICITY_REPORT_SCHEMA_VERSION, strategy_research_result_hash, verify_strategy_research_report
from tests import test_strategy_research_runner as fixtures

import run_internal_strategy_research as research_runner


class StrategyResearchSchema16Tests(unittest.TestCase):
    @staticmethod
    def _price_payloads(symbols: list[str]) -> dict[str, dict]:
        calendar = fixtures.build_market_calendar_contract(
            calendar_name="XNYS", start_date="2022-01-01", end_date="2026-12-31"
        )
        dates = list(calendar.get("expected_dates") or [])[:600]
        if len(dates) != 600:
            raise AssertionError("schema16 fixture requires 600 market sessions")

        def daily_return(symbol: str, index: int) -> float:
            if symbol == symbols[0]:
                return 0.002 * math.sin(index * 2.0 * math.pi / 7.0)
            if len(symbols) == 1 or symbol == symbols[1]:
                return 0.002 * math.sin(index * 2.0 * math.pi / 11.0)
            shared = 0.002 * math.sin(index * 2.0 * math.pi / 17.0)
            if symbol == symbols[2]:
                return shared
            if symbol == symbols[3]:
                return shared * 0.98 + 0.00004 * math.sin(index * 2.0 * math.pi / 5.0)
            return shared * 1.02 + 0.00004 * math.cos(index * 2.0 * math.pi / 5.0)

        payloads: dict[str, dict] = {}
        for symbol in symbols:
            price = 100.0
            rows = []
            for index, session_date in enumerate(dates):
                price *= 1.0 + daily_return(symbol, index)
                instant = datetime.fromisoformat(f"{session_date}T00:00:00+00:00")
                rows.append({
                    "date": session_date,
                    "ts_ms": int(instant.timestamp() * 1000),
                    "open": price,
                    "high": price * 1.002,
                    "low": price * 0.998,
                    "close": price,
                    "volume": 1_000.0 + index,
                    "complete": True,
                    "complete_attested": True,
                    "source": "READ_ONLY_UNIT_SOURCE",
                })
            payloads[symbol] = {
                "source": "READ_ONLY_UNIT_SOURCE",
                "rows": rows,
                "data_revision_evidence": {
                    "status": "PASS",
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            }
        return payloads

    @staticmethod
    def _aligned_fixture(payloads: dict[str, dict], *, role: str):
        manifests = [
            {**item, "role": role, "timeframe": "1D"}
            for item in research_runner.dataset_manifests(payloads, require_frozen_revision=True)
        ]
        aligned, alignment = research_runner.align_completed_daily_payloads(payloads)
        if role == "SELECTION":
            alignment["input_snapshot"] = research_runner.build_strategy_selection_alignment_input_snapshot(payloads, manifests)
        return aligned, manifests, alignment

    def test_schema16_runs_real_selection_replay_and_never_publishes_current_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            reports = runtime / "reports"
            reports.mkdir(parents=True)
            registry = runtime / "strategy_research_registrations.sqlite3"
            output = reports / "schema16.json"
            protocol_output = reports / "schema16-protocol.json"
            selection_symbols = ["AAPL", "NVDA", "MSFT", "MU", "WDC"]
            holdout_symbols = ["FRESH"]
            selection_payloads = self._price_payloads(selection_symbols)
            selection_fixture = self._aligned_fixture(selection_payloads, role="SELECTION")
            holdout_fixture = self._aligned_fixture(self._price_payloads(holdout_symbols), role="CONFIRMATION")
            store = StrategyMatrixRegistrationStore(db_path=registry, canonical_runtime_root=runtime)
            base_params = dict(research_runner.server.choose_strategy("dual_ma").get("params") or {})
            trial_count = len(research_runner.build_parameter_variants("dual_ma", base_params))
            lineage_plan = store.derive_search_lineage(
                search_family_id="schema16-correlation-family", current_trial_count=trial_count
            )
            self.assertEqual(lineage_plan["status"], "PASS")
            hypothesis = build_strategy_hypothesis_preregistration({
                "schema_version": STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
                "hypothesis_id": "schema16-correlation-hypothesis",
                "research_generation": "SCHEMA16-UNIT",
                "search_family_id": "schema16-correlation-family",
                "strategy_ids": ["dual_ma"],
                "mechanism_family": "causal trend persistence",
                "hypothesis_statement": "Completed-bar trend evidence must survive a preregistered cross-cluster multiplicity gate.",
                "novelty_statement": "The correlation family and selection identity are frozen before the isolated return replay.",
                "mechanism_specific_failure_conditions": [{
                    "condition_id": "validation_excess_lost",
                    "evidence_stage": "DEVELOPMENT_SELECTION",
                    "metric": "median_validation_excess_return_pct",
                    "operator": "LTE",
                    "threshold": 0.0,
                    "required_action": "BLOCK_RESEARCH",
                }],
            })
            spec = research_runner.build_research_batch_spec(
                selection_symbols=selection_symbols,
                holdout_symbols=holdout_symbols,
                strategies=["dual_ma"],
                position_pct=20.0,
                take_profit_pct=8.0,
                stop_loss_pct=4.0,
                fee_rate=0.0005,
                slippage_bps=2.0,
                limit=780,
                max_test_candidates=1,
                research_generation="SCHEMA16-UNIT",
                selection_test_policy="BLIND_ONCE",
                hypothesis_preregistration=hypothesis,
                search_lineage=lineage_plan["lineage"],
                report_schema_version=STRATEGY_RESEARCH_MULTIPLICITY_REPORT_SCHEMA_VERSION,
            )
            preregistration = build_correlation_cluster_preregistration([
                {"cluster_id": "cluster-a", "members": [selection_symbols[0]]},
                {"cluster_id": "cluster-b", "members": [selection_symbols[1]]},
                {"cluster_id": "cluster-c", "members": selection_symbols[2:]},
            ])
            variant = spec["variants"][0]
            source_registration = build_strategy_correlation_protocol_registration_v2(
                preregistration,
                cutoff_date=selection_payloads[selection_symbols[0]]["rows"][-1]["date"],
                selection_alignment_input_hash=selection_fixture[2]["input_snapshot"]["input_hash"],
                evaluations=[{
                    "strategy_id": variant["strategy_id"],
                    "variant_id": variant["variant_id"],
                    "lane": "RAW_EXCESS",
                }],
            )
            family = build_strategy_correlation_multiplicity_family_registration(source_registration)
            correlation_registration = build_strategy_correlation_multiplicity_protocol_registration(family)
            artifact_plan = fixtures.plan_strategy_research_protocol_artifact(
                reports,
                registration_id="schema16-unit",
                registry_path=registry,
                requested_output=protocol_output,
            )
            self.assertEqual(artifact_plan["status"], "PASS", artifact_plan["blockers"])
            exposure = {
                "schema_version": "strategy-matrix-exposure-audit-v1",
                "status": "PASS",
                "evaluated_before_data_load": True,
                "symbols": holdout_symbols,
                "exposed_symbols": [],
                "evidence": {},
                "blockers": [],
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            exposure["audit_hash"] = research_runner.canonical_hash(exposure)
            protocol = build_strategy_matrix_protocol(
                registration_id="schema16-unit",
                research_generation="SCHEMA16-UNIT",
                batch_spec=spec,
                implementation_manifest=fixtures.build_implementation_manifest([Path(research_runner.__file__)]),
                exposure_audit=exposure,
                registration_clock_attestation=fixtures.attested_clock(1_000_000),
                expires_at_ms=5_000_000,
                registry_path=registry,
                protocol_artifact=dict(artifact_plan["artifact_binding"]),
                correlation_multiplicity_protocol_registration=correlation_registration,
            )
            publication = fixtures.publish_strategy_research_protocol_artifact_no_clobber(protocol_output, protocol)
            self.assertEqual(publication["status"], "PUBLISHED")
            self.assertEqual(store.register(protocol)["status"], "REGISTERED")

            def load_payloads(symbols: list[str], limit: int, **kwargs: object):
                if symbols == selection_symbols:
                    return deepcopy(selection_fixture)
                if symbols == holdout_symbols:
                    return deepcopy(holdout_fixture)
                raise AssertionError(f"unexpected symbols: {symbols}")

            argv = [
                "run_internal_strategy_research.py",
                "--registration-id", "schema16-unit",
                "--registry", str(registry),
                "--output", str(output),
                "--report-schema-version", "16",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(research_runner.server, "RUNTIME_DIR", runtime),
                patch.object(research_runner.server, "RUNTIME_READ_ONLY", False),
                patch.object(research_runner, "audit_strategy_matrix_holdout_exposure", return_value=exposure),
                patch.object(research_runner, "attest_utc_clock", side_effect=[fixtures.attested_clock(2_000_000), fixtures.attested_clock(3_000_000)]),
                patch.object(research_runner, "load_payloads", side_effect=load_payloads),
                patch("builtins.print"),
            ):
                self.assertEqual(research_runner.main(), 0)

            report = json.loads(output.read_text(encoding="utf-8"))
            verification = verify_strategy_research_report(report)
            self.assertEqual(verification["status"], "PASS", verification["blockers"])
            self.assertEqual(report["schema_version"], 16)
            self.assertEqual(report["correlation_multiplicity_evidence"]["status"], "PASS")
            self.assertIn(report["correlation_multiplicity_evidence"]["decision_status"], {"PASS", "BLOCK"})
            envelope = build_strategy_matrix_multiplicity_report(report)
            envelope_verification = verify_strategy_matrix_multiplicity_report(envelope)
            self.assertEqual(
                envelope_verification["status"],
                "PASS",
                envelope_verification["blockers"],
            )
            self.assertEqual(envelope["schema_version"], 8)
            self.assertEqual(envelope["inner_report_hash"], research_runner.canonical_hash(report))
            self.assertEqual(envelope["decision_status"], report["correlation_multiplicity_evidence"]["decision_status"])
            self.assertFalse(envelope["current_writer_activation_allowed"])
            self.assertFalse(envelope["current_admission_allowed"])
            public_projection = build_strategy_lab_projection(report)
            public_summary = public_projection["correlation_multiplicity_summary"]
            expected_public_status = (
                "OBSERVED_NO_FAMILY_WISE_BLOCK"
                if report["correlation_multiplicity_evidence"]["decision_status"]
                == "PASS"
                else "OBSERVED_FAMILY_WISE_BLOCK"
            )
            self.assertEqual(public_summary["status"], expected_public_status)
            self.assertEqual(
                public_summary["decision_status"],
                report["correlation_multiplicity_evidence"]["decision_status"],
            )
            self.assertEqual(public_summary["expected_family_size"], 7)
            self.assertEqual(public_summary["observed_family_size"], 7)
            self.assertAlmostEqual(
                public_summary["per_pair_alpha"],
                0.05 / 7,
                places=15,
            )
            self.assertEqual(public_projection["rows"], [])
            self.assertNotIn("research_governance", public_projection)
            forbidden_keys = {
                "correlation_multiplicity_evidence",
                "multiplicity_audit",
                "family_binding_assessment",
                "protocol_hash",
                "family_registration_hash",
                "cluster_preregistration_hash",
            }
            forbidden_values = set(selection_symbols)

            def assert_public_identity_redacted(value: object) -> None:
                if isinstance(value, dict):
                    self.assertTrue(forbidden_keys.isdisjoint(value))
                    for item in value.values():
                        assert_public_identity_redacted(item)
                elif isinstance(value, list):
                    for item in value:
                        assert_public_identity_redacted(item)
                elif isinstance(value, str):
                    self.assertNotIn(value, forbidden_values)

            assert_public_identity_redacted(public_projection)
            self.assertEqual(store.get("schema16-unit")["status"], "COMPLETED")
            self.assertFalse(report["paper_authorized"])
            self.assertFalse(report["live_order_allowed"])
            self.assertFalse((reports / research_runner.DEFAULT_STRATEGY_RESEARCH_POINTER_FILE).exists())
            missing = deepcopy(report)
            missing.pop("correlation_multiplicity_evidence")
            missing["batch_run_hash"] = strategy_research_result_hash(missing)
            self.assertIn(
                "research_field_type_invalid:correlation_multiplicity_evidence",
                verify_strategy_research_report(missing)["blockers"],
            )


if __name__ == "__main__":
    unittest.main()
