from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_shadow import (
    PortfolioShadowLedger,
    build_forward_observation_change,
    build_forward_state_contract,
    build_incremental_observation_plan,
    build_shadow_observation,
    seal_forward_status_artifact,
    verify_forward_status_artifact,
    verify_forward_observation_change,
    verify_forward_state_contract,
    verify_latest_forward_observation_receipt,
)
from exchange_terminal.services.trusted_clock import build_trusted_clock_attestation


def candidate() -> dict[str, object]:
    return {"candidate_hash": "candidate-1", "dataset_last": "2026-07-30"}


def backtest(signal_date: str = "2026-07-31") -> dict[str, object]:
    return {
        "ok": True,
        "execution_model": "test-forward-execution",
        "initial_cash": 100_000.0,
        "run_spec": {
            "evaluation_start_index": 0,
            "execution_model": "test-forward-execution",
        },
        "evaluation_window": {"start_index": 0, "start": signal_date, "end": signal_date},
        "dataset_manifest": {"data_hash": "data-new", "last": signal_date},
        "pending_decision_at_end": {
            "signal_date": signal_date,
            "target_symbols": ["AAPL", "NVDA"],
            "target_weights": {"AAPL": 0.6, "NVDA": 0.4},
            "target_allocation_pct": 45.0,
            "reason": "relative_strength_rebalance",
            "estimated_portfolio_volatility_pct": 14.0,
            "regime": {"regime_id": "UP_NORMAL"},
        },
    }


def sealed(payload: dict[str, object], hash_field: str) -> dict[str, object]:
    result = dict(payload)
    raw = json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    result[hash_field] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return result


def reseal_observation(payload: dict[str, object]) -> dict[str, object]:
    result = json.loads(json.dumps(payload))
    decision_payload = {
        "candidate_hash": str(result.get("candidate_hash") or ""),
        "signal_date": str(result.get("signal_date") or ""),
        "dataset_hash": str(result.get("dataset_hash") or ""),
        "dataset_last": str(result.get("dataset_last") or ""),
        "forward_state_contract_hash": str(result.get("forward_state_contract_hash") or ""),
        "decision": dict(result.get("decision") or {}),
    }
    decision_raw = json.dumps(
        decision_payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    decision_hash = hashlib.sha256(decision_raw.encode("utf-8")).hexdigest()
    result["market_decision_hash"] = decision_hash
    result["decision_hash"] = decision_hash
    result.pop("observation_hash", None)
    observation_raw = json.dumps(
        result,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    result["observation_hash"] = hashlib.sha256(observation_raw.encode("utf-8")).hexdigest()
    return result


def reseal_change(payload: dict[str, object]) -> dict[str, object]:
    result = json.loads(json.dumps(payload))
    result.pop("change_hash", None)
    raw = json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    result["change_hash"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return result


def capture(signal_date: str = "2026-07-31", *, observed_at: int = 2) -> dict[str, object]:
    stamp = int(observed_at)
    clock_evidence = sealed({
        "source": "TEST_CLOCK",
        "endpoint": "https://clock.test/time",
        "status": "PASS",
        "error": "",
        "requested_at_ms": stamp - 1,
        "received_at_ms": stamp + 1,
        "round_trip_ms": 2,
        "midpoint_local_ms": stamp,
        "server_time_ms": stamp,
        "offset_ms": 0,
    }, "evidence_hash")
    clock = build_trusted_clock_attestation(local_now_ms=stamp, provider_evidence=[clock_evidence])
    activation_stamp = 1
    activation_evidence = sealed({
        "source": "TEST_ACTIVATION_CLOCK",
        "endpoint": "https://clock.test/activation",
        "status": "PASS",
        "error": "",
        "requested_at_ms": activation_stamp,
        "received_at_ms": activation_stamp,
        "round_trip_ms": 0,
        "midpoint_local_ms": activation_stamp,
        "server_time_ms": activation_stamp,
        "offset_ms": 0,
    }, "evidence_hash")
    activation_clock = build_trusted_clock_attestation(
        local_now_ms=activation_stamp,
        provider_evidence=[activation_evidence],
    )
    return sealed({
        "status": "PASS",
        "signal_date": signal_date,
        "session_close_utc": f"{signal_date}T20:00:00+00:00",
        "timely": True,
        "backfill_allowed": False,
        "candidate_hash": "candidate-1",
        "candidate_activated_at": activation_stamp,
        "candidate_activation_registry_hash": "registry-hash",
        "candidate_active_before_signal_close": True,
        "activation_clock_attestation_hash": activation_clock["attestation_hash"],
        "activation_clock_attestation": activation_clock,
        "observed_at": stamp,
        "clock_attested": True,
        "clock_attestation_hash": clock["attestation_hash"],
        "clock_attestation": clock,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, "capture_contract_hash")


def risk(status: str = "PASS") -> dict[str, object]:
    return sealed({
        "status": status,
        "blockers": [] if status == "PASS" else ["blocked"],
        "paper_authorized": False,
        "live_order_allowed": False,
    }, "risk_snapshot_hash")


def state_contract(
    report: dict[str, object],
    capture_contract: dict[str, object],
) -> dict[str, object]:
    signal_date = str(dict(report.get("evaluation_window") or {}).get("start") or "")
    return build_forward_state_contract(
        candidate(),
        report,
        capture_contract=capture_contract,
        evaluation_start_index=0,
        evaluation_start_date=signal_date,
        preactivation_completed_session_count=0,
        start_capture_contract=capture_contract,
    )


class PortfolioShadowTests(unittest.TestCase):
    def test_forward_status_artifact_is_content_addressed_and_authority_free(self) -> None:
        artifact = seal_forward_status_artifact({
            "status": "UP_TO_DATE_INCREMENTAL",
            "candidate_hash": "candidate-1",
            "generated_at": 1,
            "work_summary": {"processed_count": 1},
        })
        verified = verify_forward_status_artifact(artifact, candidate_hash="candidate-1")
        tampered = dict(artifact)
        tampered["work_summary"] = {"processed_count": 99}
        rejected = verify_forward_status_artifact(tampered, candidate_hash="candidate-1")

        self.assertEqual(verified["status"], "PASS")
        self.assertTrue(artifact["observation_only"])
        self.assertTrue(artifact["simulation_only"])
        self.assertFalse(artifact["paper_authorized"])
        self.assertFalse(artifact["live_order_allowed"])
        self.assertEqual(rejected["status"], "BLOCK")
        self.assertIn("forward_status_artifact_hash_invalid", rejected["blockers"])

    @staticmethod
    def incremental_plan(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "candidate_hash": "candidate-1",
            "all_dates": ["2026-07-30", "2026-07-31", "2026-08-03", "2026-08-04"],
            "frozen_last": "2026-07-30",
            "recorded_dates": ["2026-07-31"],
            "classified_dates": ["2026-08-03"],
            "ledger_audit": {"status": "PASS", "candidate_hash": "candidate-1"},
            "data_revision_evidence": {
                "AAPL": {"status": "PASS", "evidence_hash": "revision-aapl", "cross_source": []},
            },
            "replay_recorded": False,
        }
        payload.update(overrides)
        return build_incremental_observation_plan(**payload)

    def test_incremental_plan_only_processes_unrecorded_unclassified_dates(self) -> None:
        plan = self.incremental_plan()

        self.assertEqual(plan["status"], "PASS")
        self.assertEqual(plan["mode"], "INCREMENTAL")
        self.assertEqual(plan["processing_dates"], ["2026-08-04"])
        self.assertEqual(plan["skipped_recorded_dates"], ["2026-07-31"])
        self.assertEqual(plan["skipped_classified_dates"], ["2026-08-03"])
        self.assertIs(plan["observation_only"], True)
        self.assertIs(plan["simulation_only"], True)
        self.assertIs(plan["paper_authorized"], False)
        self.assertIs(plan["live_order_allowed"], False)

    def test_incremental_plan_requires_passing_ledger_audit_before_skip(self) -> None:
        plan = self.incremental_plan(
            ledger_audit={"status": "BLOCK", "candidate_hash": "candidate-1"},
        )

        self.assertEqual(plan["status"], "BLOCK")
        self.assertIn("ledger_audit_not_pass:BLOCK", plan["blockers"])
        self.assertEqual(plan["processing_dates"], [])

    def test_incremental_plan_fails_closed_on_revision_or_identity_conflict(self) -> None:
        revision = self.incremental_plan(
            data_revision_evidence={
                "AAPL": {"status": "REVIEW", "evidence_hash": "revision-aapl", "cross_source": []},
            },
        )
        identity = self.incremental_plan(classified_dates=["2026-07-31"])

        self.assertEqual(revision["status"], "BLOCK")
        self.assertIn("data_revision_not_pass:AAPL:REVIEW", revision["blockers"])
        self.assertEqual(identity["status"], "BLOCK")
        self.assertIn("ledger_date_identity_conflict:2026-07-31", identity["blockers"])

    def test_explicit_replay_only_processes_recorded_dates(self) -> None:
        plan = self.incremental_plan(
            replay_recorded=True,
            data_revision_evidence={
                "AAPL": {"status": "REVIEW", "evidence_hash": "revision-aapl", "cross_source": []},
            },
        )

        self.assertEqual(plan["status"], "PASS")
        self.assertEqual(plan["mode"], "AUDIT_REPLAY")
        self.assertEqual(plan["processing_dates"], ["2026-07-31"])
        self.assertEqual(plan["deferred_unrecorded_dates"], ["2026-08-04"])
        self.assertIn("data_revision_review_audit_replay:AAPL", plan["warnings"])

    def test_resealed_string_activation_flag_is_rejected(self) -> None:
        report = backtest()
        contract = capture()
        forward_state = state_contract(report, contract)
        forward_state["candidate_active_before_start_close"] = "false"
        forward_state.pop("forward_state_contract_hash")
        forward_state = sealed(forward_state, "forward_state_contract_hash")

        verification = verify_forward_state_contract(
            forward_state,
            candidate_hash="candidate-1",
            backtest_report=report,
            capture_contract=contract,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("forward_state_started_before_candidate_activation", verification["blockers"])

    def test_malformed_forward_state_types_fail_closed_without_crashing(self) -> None:
        report = backtest()
        contract = capture()
        mutations = {
            "evaluation_start_index": {},
            "initial_cash": [],
            "candidate_activated_at": {},
            "initial_positions": "invalid",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                forward_state = state_contract(report, contract)
                forward_state[field] = value
                forward_state.pop("forward_state_contract_hash")
                forward_state = sealed(forward_state, "forward_state_contract_hash")

                verification = verify_forward_state_contract(
                    forward_state,
                    candidate_hash="candidate-1",
                    backtest_report=report,
                    capture_contract=contract,
                )

                self.assertEqual(verification["status"], "BLOCK")

    def test_resealed_string_timely_flag_does_not_create_observation(self) -> None:
        report = backtest()
        contract = capture()
        contract["timely"] = "false"
        contract.pop("capture_contract_hash")
        contract = sealed(contract, "capture_contract_hash")

        observation = build_shadow_observation(
            candidate(),
            report,
            observed_at=2,
            risk_snapshot=risk(),
            capture_contract=contract,
            forward_state_contract=state_contract(report, contract),
        )

        self.assertEqual(observation["status"], "WAITING")
        self.assertTrue(any(item.startswith("forward_capture_not_timely") for item in observation["blockers"]))

    def test_forward_state_contract_rejects_inherited_positions(self) -> None:
        report = backtest()
        contract = capture()
        forward_state = state_contract(report, contract)
        forward_state["initial_positions"] = {"AAPL": 10.0}
        forward_state["inherited_position_count"] = 1
        forward_state["forward_state_contract_hash"] = sealed(
            {
                key: value
                for key, value in forward_state.items()
                if key != "forward_state_contract_hash"
            },
            "forward_state_contract_hash",
        )["forward_state_contract_hash"]

        verification = verify_forward_state_contract(
            forward_state,
            candidate_hash="candidate-1",
            backtest_report=report,
            capture_contract=contract,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("forward_state_inherited_positions_present", verification["blockers"])

    def test_frozen_date_is_not_counted_as_forward_observation(self) -> None:
        report = backtest("2026-07-30")
        contract = capture("2026-07-30", observed_at=1)
        observation = build_shadow_observation(
            candidate(), report, observed_at=1, capture_contract=contract,
            forward_state_contract=state_contract(report, contract),
        )

        self.assertEqual(observation["status"], "WAITING")
        self.assertFalse(observation["paper_authorized"])

    def test_new_completed_bar_builds_a_read_only_observation(self) -> None:
        report = backtest()
        contract = capture()
        observation = build_shadow_observation(
            candidate(), report, observed_at=2, risk_snapshot=risk(), capture_contract=contract,
            forward_state_contract=state_contract(report, contract),
        )

        self.assertEqual(observation["status"], "READY")
        self.assertEqual(observation["target_symbols"], ["AAPL", "NVDA"])
        self.assertTrue(observation["decision_hash"])
        self.assertFalse(observation["live_order_allowed"])

    def test_missing_or_invalid_risk_snapshot_never_becomes_ready(self) -> None:
        report = backtest()
        contract = capture()
        for label, risk_snapshot in (
            ("missing", None),
            ("empty", {}),
            ("wrong_hash", {"status": "PASS", "risk_snapshot_hash": "0" * 64}),
        ):
            with self.subTest(label=label):
                observation = build_shadow_observation(
                    candidate(),
                    report,
                    observed_at=2,
                    risk_snapshot=risk_snapshot,
                    capture_contract=contract,
                    forward_state_contract=state_contract(report, contract),
                )
                self.assertEqual(observation["status"], "WAITING")
                self.assertIn("observation_risk_snapshot_hash_invalid", observation["blockers"])
                self.assertFalse(observation["paper_authorized"])
                self.assertFalse(observation["live_order_allowed"])

    def test_record_and_audit_reject_invalid_risk_snapshot_and_withhold_receipt(self) -> None:
        report = backtest()
        contract = capture()
        observation = build_shadow_observation(
            candidate(), report, observed_at=2, risk_snapshot=risk(), capture_contract=contract,
            forward_state_contract=state_contract(report, contract),
        )
        tampered = json.loads(json.dumps(observation))
        tampered["risk_snapshot"]["risk_snapshot_hash"] = "0" * 64
        tampered["risk_snapshot_hash"] = "0" * 64
        tampered = reseal_observation(tampered)

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir, "shadow.sqlite")
            ledger = PortfolioShadowLedger(database_path)
            rejected = ledger.record(tampered)
            self.assertEqual(ledger.record(observation)["status"], "RECORDED")
            with closing(sqlite3.connect(database_path)) as connection, connection:
                connection.execute(
                    "UPDATE portfolio_shadow_observations SET payload_json = ? WHERE candidate_hash = ? AND signal_date = ?",
                    (
                        json.dumps(tampered, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        "candidate-1",
                        "2026-07-31",
                    ),
                )
            audit = ledger.audit("candidate-1")
            receipt = ledger.latest_observation_receipt("candidate-1", ledger_audit=audit)

        self.assertEqual(rejected["status"], "BLOCK")
        self.assertEqual(rejected["reason"], "shadow_risk_snapshot_invalid")
        self.assertIn("observation_risk_snapshot_hash_invalid", rejected["blockers"])
        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(any("observation_risk_snapshot_hash_invalid" in item for item in audit["integrity_violations"]))
        self.assertEqual(receipt, {})

    def test_record_and_audit_require_exact_decision_projection(self) -> None:
        report = backtest()
        contract = capture()
        observation = build_shadow_observation(
            candidate(), report, observed_at=2, risk_snapshot=risk(), capture_contract=contract,
            forward_state_contract=state_contract(report, contract),
        )
        mutations = {
            "signal_date": ("2026-08-01", "observation_decision_signal_date_mismatch"),
            "target_symbols": (["AAPL"], "observation_decision_target_symbols_mismatch"),
            "target_weights": ({"AAPL": 1.0}, "observation_decision_target_weights_mismatch"),
            "target_allocation_pct": (46.0, "observation_decision_target_allocation_mismatch"),
            "reason": ("tampered", "observation_decision_reason_mismatch"),
            "regime_id": ("DOWN_HIGH", "observation_decision_regime_mismatch"),
            "estimated_portfolio_volatility_pct": (99.0, "observation_decision_volatility_mismatch"),
        }
        for field, (value, blocker) in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp_dir:
                tampered = json.loads(json.dumps(observation))
                tampered[field] = value
                tampered = reseal_observation(tampered)
                rejected = PortfolioShadowLedger(Path(temp_dir, "shadow.sqlite")).record(tampered)
                self.assertEqual(rejected["status"], "BLOCK")
                self.assertEqual(rejected["reason"], "shadow_decision_projection_invalid")
                self.assertIn(blocker, rejected["blockers"])

        audit_tampered = json.loads(json.dumps(observation))
        audit_tampered["reason"] = "tampered"
        audit_tampered = reseal_observation(audit_tampered)
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir, "shadow.sqlite")
            ledger = PortfolioShadowLedger(database_path)
            self.assertEqual(ledger.record(observation)["status"], "RECORDED")
            with closing(sqlite3.connect(database_path)) as connection, connection:
                connection.execute(
                    "UPDATE portfolio_shadow_observations SET payload_json = ? WHERE candidate_hash = ? AND signal_date = ?",
                    (
                        json.dumps(audit_tampered, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        "candidate-1",
                        "2026-07-31",
                    ),
                )
            audit = ledger.audit("candidate-1")
            receipt = ledger.latest_observation_receipt("candidate-1", ledger_audit=audit)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(any("observation_decision_reason_mismatch" in item for item in audit["integrity_violations"]))
        self.assertEqual(receipt, {})

    def test_latest_valid_observation_receipt_is_audited_sealed_and_status_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PortfolioShadowLedger(Path(temp_dir, "shadow.sqlite"))
            report = backtest()
            contract = capture()
            observation = build_shadow_observation(
                candidate(), report, observed_at=2, risk_snapshot=risk(), capture_contract=contract,
                forward_state_contract=state_contract(report, contract),
            )
            self.assertEqual(ledger.record(observation)["status"], "RECORDED")
            audit = ledger.audit("candidate-1")
            receipt = ledger.latest_observation_receipt("candidate-1", ledger_audit=audit)

        verification = verify_latest_forward_observation_receipt(
            receipt,
            candidate_hash="candidate-1",
            expected_signal_date="2026-07-31",
            ledger_audit=audit,
        )
        empty_risk_audit = dict(audit)
        empty_risk_audit["latest_observation_risk_snapshot_hash"] = ""
        empty_risk_receipt = dict(receipt)
        empty_risk_receipt["risk_snapshot_hash"] = ""
        empty_risk_receipt["ledger_audit_hash"] = hashlib.sha256(
            json.dumps(
                empty_risk_audit,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        empty_risk_receipt.pop("receipt_hash", None)
        empty_risk_receipt["receipt_hash"] = hashlib.sha256(
            json.dumps(
                empty_risk_receipt,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        empty_risk_verification = verify_latest_forward_observation_receipt(
            empty_risk_receipt,
            candidate_hash="candidate-1",
            expected_signal_date="2026-07-31",
            ledger_audit=empty_risk_audit,
        )
        artifact = seal_forward_status_artifact({
            "status": "UP_TO_DATE_INCREMENTAL",
            "candidate_hash": "candidate-1",
            "generated_at": 3,
            "records": [],
            "latest_observation_receipt": receipt,
        })
        tampered_artifact = dict(artifact)
        tampered_artifact["latest_observation_receipt"] = {
            **dict(receipt),
            "reason": "tampered",
        }

        self.assertEqual(receipt["schema_version"], "latest-forward-observation-receipt-v1")
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["signal_date"], "2026-07-31")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(empty_risk_verification["status"], "BLOCK")
        self.assertIn(
            "latest_observation_receipt_risk_hash_invalid",
            empty_risk_verification["blockers"],
        )
        self.assertEqual(
            verify_forward_status_artifact(artifact, candidate_hash="candidate-1")["status"],
            "PASS",
        )
        self.assertEqual(
            verify_forward_status_artifact(tampered_artifact, candidate_hash="candidate-1")["status"],
            "BLOCK",
        )
        self.assertIs(receipt["paper_authorized"], False)
        self.assertIs(receipt["live_order_allowed"], False)

    def test_latest_observation_change_seals_insufficient_evidence_without_claiming_no_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PortfolioShadowLedger(Path(temp_dir, "shadow.sqlite"))
            report = backtest()
            contract = capture()
            observation = build_shadow_observation(
                candidate(), report, observed_at=2, risk_snapshot=risk(), capture_contract=contract,
                forward_state_contract=state_contract(report, contract),
            )
            self.assertEqual(ledger.record(observation)["status"], "RECORDED")
            audit = ledger.audit("candidate-1")
            change = ledger.latest_observation_change("candidate-1", ledger_audit=audit)

        verification = verify_forward_observation_change(
            change,
            candidate_hash="candidate-1",
            expected_current_signal_date="2026-07-31",
            ledger_audit=audit,
        )
        self.assertEqual(change["status"], "NOT_ENOUGH_OBSERVATIONS")
        self.assertEqual(change["target_set"]["changed"], None)
        self.assertEqual(change["current"]["observation_hash"], observation["observation_hash"])
        self.assertEqual(audit["observation_chain_count"], 1)
        self.assertEqual(verification["status"], "PASS")
        self.assertFalse(change["paper_authorized"])
        self.assertFalse(change["live_order_allowed"])

    def test_latest_two_observations_produce_audited_descriptive_change_and_tamper_blocks(self) -> None:
        first_report = backtest("2026-07-31")
        first_capture = capture("2026-07-31", observed_at=2)
        first = build_shadow_observation(
            candidate(), first_report, observed_at=2, risk_snapshot=risk(), capture_contract=first_capture,
            forward_state_contract=state_contract(first_report, first_capture),
        )
        second_report = backtest("2026-08-01")
        second_decision = dict(second_report["pending_decision_at_end"])
        second_decision.update({
            "target_symbols": ["NVDA", "MSFT"],
            "target_weights": {"NVDA": 0.5, "MSFT": 0.5},
            "target_allocation_pct": 50.25,
            "reason": "risk_adjusted_rebalance",
            "regime": {"regime_id": "DOWN_HIGH"},
        })
        second_report["pending_decision_at_end"] = second_decision
        second_capture = capture("2026-08-01", observed_at=3)
        second = build_shadow_observation(
            candidate(), second_report, observed_at=3, risk_snapshot=risk("BLOCK"), capture_contract=second_capture,
            forward_state_contract=state_contract(second_report, second_capture),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PortfolioShadowLedger(Path(temp_dir, "shadow.sqlite"))
            self.assertEqual(ledger.record(first)["status"], "RECORDED")
            self.assertEqual(ledger.record(second)["status"], "RECORDED")
            audit = ledger.audit("candidate-1")
            change = ledger.latest_observation_change("candidate-1", ledger_audit=audit)

        self.assertEqual(change["status"], "VERIFIED")
        self.assertEqual(change["previous"]["observation_hash"], first["observation_hash"])
        self.assertEqual(change["current"]["observation_hash"], second["observation_hash"])
        self.assertTrue(change["target_set"]["changed"])
        self.assertEqual(change["target_set"]["added"], ["MSFT"])
        self.assertEqual(change["target_set"]["removed"], ["AAPL"])
        self.assertEqual(change["target_set"]["retained"], ["NVDA"])
        self.assertEqual(change["total_allocation_pct"], {"before": "45", "after": "50.25", "delta": "5.25"})
        self.assertTrue(change["reason"]["changed"])
        self.assertTrue(change["regime_id"]["changed"])
        self.assertEqual(change["risk_gate_status"], {"before": "PASS", "after": "BLOCK", "changed": True})
        self.assertTrue(change["descriptive_only"])
        self.assertFalse(change["direction_signal_allowed"])
        self.assertFalse(change["performance_claim_allowed"])
        self.assertEqual(
            verify_forward_observation_change(
                change,
                candidate_hash="candidate-1",
                expected_current_signal_date="2026-08-01",
                ledger_audit=audit,
            )["status"],
            "PASS",
        )

        mutations = {
            "previous_hash": lambda item: item["previous"].update({"observation_hash": "0" * 64}),
            "chain_hash": lambda item: item["evidence"].update({"observation_chain_hash": "0" * 64}),
            "paper_authority": lambda item: item.update({"paper_authorized": True}),
            "forged_target_claims": lambda item: item["target_set"].update({
                "changed": True,
                "after": ["NVDA", "GOOG"],
                "added": ["GOOG"],
                "removed": ["AAPL"],
                "retained": ["NVDA"],
            }),
            "forged_reason_claims": lambda item: item["reason"].update({
                "after": "forged_reason",
                "changed": True,
            }),
            "forged_risk_claims": lambda item: item["risk_gate_status"].update({
                "after": "PASS",
                "changed": False,
            }),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                tampered = json.loads(json.dumps(change))
                mutate(tampered)
                tampered = reseal_change(tampered)
                verification = verify_forward_observation_change(
                    tampered,
                    candidate_hash="candidate-1",
                    expected_current_signal_date="2026-08-01",
                    ledger_audit=audit,
                )
                self.assertEqual(verification["status"], "BLOCK")
                if label.startswith("forged_"):
                    self.assertIn(
                        "forward_observation_change_current_projection_mismatch",
                        verification["blockers"],
                    )

        directly_built = build_forward_observation_change(first, second, ledger_audit=audit)
        self.assertEqual(directly_built["change_hash"], change["change_hash"])

    def test_unattested_capture_is_rejected(self) -> None:
        untrusted = sealed({
            "status": "PASS",
            "signal_date": "2026-07-31",
            "timely": True,
            "backfill_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }, "capture_contract_hash")

        observation = build_shadow_observation(
            candidate(), backtest(), observed_at=2, risk_snapshot=risk(), capture_contract=untrusted,
            forward_state_contract={},
        )

        self.assertEqual(observation["status"], "WAITING")
        self.assertIn("forward_capture_clock_not_attested", observation["blockers"])

    def test_ledger_is_idempotent_and_rejects_conflicting_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PortfolioShadowLedger(Path(temp_dir, "shadow.sqlite"))
            report = backtest()
            contract = capture()
            observation = build_shadow_observation(
                candidate(), report, observed_at=2, risk_snapshot=risk(), capture_contract=contract,
                forward_state_contract=state_contract(report, contract),
            )
            first = ledger.record(observation)
            replay = ledger.record(observation)
            conflicting_backtest = backtest()
            conflicting_backtest["pending_decision_at_end"] = {
                **dict(conflicting_backtest["pending_decision_at_end"]),
                "target_symbols": ["AAPL"],
                "target_weights": {"AAPL": 1.0},
            }
            conflicting_capture = capture(observed_at=3)
            conflicting = build_shadow_observation(
                candidate(), conflicting_backtest, observed_at=3, risk_snapshot=risk(),
                capture_contract=conflicting_capture,
                forward_state_contract=state_contract(conflicting_backtest, conflicting_capture),
            )
            conflict = ledger.record(conflicting)
            summary = ledger.summary("candidate-1")

        self.assertEqual(first["status"], "RECORDED")
        self.assertEqual(replay["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(conflict["status"], "CONFLICT")
        self.assertEqual(summary["observation_count"], 1)

    def test_ledger_rejects_resealed_string_observation_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PortfolioShadowLedger(Path(temp_dir, "shadow.sqlite"))
            report = backtest()
            contract = capture()
            observation = build_shadow_observation(
                candidate(), report, observed_at=2, risk_snapshot=risk(), capture_contract=contract,
                forward_state_contract=state_contract(report, contract),
            )
            observation["observation_only"] = "false"
            observation.pop("observation_hash")
            observation = sealed(observation, "observation_hash")

            result = ledger.record(observation)

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason"], "shadow_observation_has_execution_authority")

    def test_risk_reassessment_is_append_only_and_does_not_replace_market_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PortfolioShadowLedger(Path(temp_dir, "shadow.sqlite"))
            report = backtest()
            contract = capture()
            observation = build_shadow_observation(
                candidate(), report, observed_at=2, risk_snapshot=risk(), capture_contract=contract,
                forward_state_contract=state_contract(report, contract),
            )
            ledger.record(observation)
            blocked = risk("BLOCK")
            passed = risk("PASS")
            first = ledger.record_risk_reassessment(
                candidate_hash="candidate-1", signal_date="2026-07-31", risk_snapshot=blocked, observed_at=3
            )
            second = ledger.record_risk_reassessment(
                candidate_hash="candidate-1", signal_date="2026-07-31", risk_snapshot=passed, observed_at=4
            )
            replay = ledger.record_risk_reassessment(
                candidate_hash="candidate-1", signal_date="2026-07-31", risk_snapshot=passed, observed_at=5
            )
            summary = ledger.summary("candidate-1")

        self.assertEqual(first["status"], "RECORDED")
        self.assertEqual(second["status"], "RECORDED")
        self.assertEqual(replay["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(summary["observation_count"], 1)
        self.assertEqual(summary["risk_reassessment_count"], 2)
        self.assertEqual(summary["risk_pass_count"], 1)
        self.assertEqual(summary["risk_block_count"], 1)
        self.assertEqual(summary["latest_risk_status"], "PASS")

    def test_capture_violation_is_append_only_and_blocks_forward_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PortfolioShadowLedger(Path(temp_dir, "shadow.sqlite"))
            first = ledger.record_capture_event({
                "candidate_hash": "candidate-1",
                "signal_date": "2026-07-31",
                "event_type": "MISSED_CAPTURE",
                "reason": "next_session_already_opened",
                "observed_at": 3,
            })
            replay = ledger.record_capture_event({
                "candidate_hash": "candidate-1",
                "signal_date": "2026-07-31",
                "event_type": "MISSED_CAPTURE",
                "reason": "next_session_already_opened",
                "observed_at": 4,
            })
            audit = ledger.audit("candidate-1")

        self.assertEqual(first["status"], "RECORDED")
        self.assertEqual(replay["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(audit["status"], "BLOCK")
        self.assertEqual(audit["missed_capture_count"], 1)

    def test_pre_activation_skip_is_audited_without_counting_as_a_capture_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PortfolioShadowLedger(Path(temp_dir, "shadow.sqlite"))
            ledger.record_capture_event({
                "candidate_hash": "candidate-1",
                "signal_date": "2026-07-31",
                "event_type": "PRE_ACTIVATION_SKIPPED",
                "reason": "candidate_not_active_before_signal_close",
                "observed_at": 3,
            })
            audit = ledger.audit("candidate-1")

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["capture_violation_count"], 0)
        self.assertEqual(audit["neutral_capture_event_count"], 1)


if __name__ == "__main__":
    unittest.main()
