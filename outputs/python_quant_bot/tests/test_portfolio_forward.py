from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_candidate import (
    build_frozen_portfolio_candidate,
    implementation_fingerprint,
)
from exchange_terminal.services.portfolio_admission import (
    build_internal_backtest_admission,
    build_research_universe_contract,
)
from exchange_terminal.services.portfolio_forward import (
    ACTIVE_CANDIDATE_SCHEMA_VERSION,
    _portfolio_artifact_byte_limits,
    _read_json_artifact,
    activate_portfolio_candidate,
    build_forward_capture_contract,
    build_forward_readiness,
    load_active_portfolio_candidate,
    retire_active_portfolio_candidate,
    verify_active_candidate_activation,
)
from exchange_terminal.services.forward_artifact_io import (
    MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
)
from exchange_terminal.services.portfolio_robustness import build_robustness_assessment
from exchange_terminal.services.research_exposure import audit_portfolio_temporal_exposure
from exchange_terminal.services.provider_governance import build_unassessed_provider_governance_contract
from exchange_terminal.services.trusted_clock import build_trusted_clock_attestation
from tests.portfolio_governance_fixtures import (
    experiment_binding,
    experiment_completion_receipt,
)


def utc_ms(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(timezone.utc).timestamp() * 1000)


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def attested_clock(stamp: int) -> dict[str, object]:
    evidence = {
        "source": "TEST_CLOCK",
        "endpoint": "https://clock.test/time",
        "status": "PASS",
        "error": "",
        "requested_at_ms": stamp - 10,
        "received_at_ms": stamp + 10,
        "round_trip_ms": 20,
        "midpoint_local_ms": stamp,
        "server_time_ms": stamp,
        "offset_ms": 0,
    }
    evidence["evidence_hash"] = canonical_hash(evidence)
    return build_trusted_clock_attestation(local_now_ms=stamp, provider_evidence=[evidence])


def active_registry(activated_at: int, *, candidate_hash: str = "candidate") -> dict[str, object]:
    clock = attested_clock(activated_at)
    binding = experiment_binding()
    completion = experiment_completion_receipt({
        "candidate_hash": candidate_hash,
        "research_report_hash": "report-hash",
        "dataset_hash": "data-hash",
        "research_governance": {"experiment_binding": binding},
    })
    payload = {
        "schema_version": ACTIVE_CANDIDATE_SCHEMA_VERSION,
        "status": "ACTIVE_RESEARCH_CANDIDATE",
        "candidate_hash": candidate_hash,
        "activated_at": activated_at,
        "activation_clock_attestation_hash": clock["attestation_hash"],
        "activation_clock_attestation": clock,
        "experiment_completion_receipt_hash": completion["receipt_hash"],
        "experiment_completion_receipt": completion,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["registry_hash"] = canonical_hash(payload)
    return payload


def candidate(source: Path, *, generation: str = "PORTFOLIO_G8") -> dict[str, object]:
    report: dict[str, object] = {
        "mechanism_status": "PROMISING_NEEDS_FRESH_HOLDOUT",
        "batch_run_hash": f"report-{generation}",
        "spec": {"research_generation": generation, "trial_count": 6},
        "spec_hash": f"spec-{generation}",
        "dataset_manifest": {
            "status": "PASS",
            "data_hash": "data-hash",
            "first": "2024-01-01",
            "last": "2026-07-30",
            "row_count": 519,
            "symbols": ["SPY", "AAPL"],
        },
        "validation": {"ok": True},
        "test": {"ok": True},
        "full": {"ok": True},
        "causal_audit": {"status": "PASS"},
        "correlation_matrix": {"status": "PASS"},
        "development_checks": {
            "validation_rebalance_schedule_pass": True,
            "test_rebalance_schedule_pass": True,
            "full_rebalance_schedule_pass": True,
            "adjustment_contracts_pass": True,
            "return_accounting_double_count_protection_pass": True,
        },
        "fresh_holdout_required": True,
        "forward_observation_required": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report["universe_contract"] = build_research_universe_contract(
        benchmark_symbol="SPY",
        tradable_symbols=["AAPL"],
        declared_at="2026-07-30T00:00:00+00:00",
        selection_basis="TEST_STATIC_LIST",
    )
    report["temporal_exposure_audit"] = audit_portfolio_temporal_exposure(
        source.parent,
        start_date="2026-01-01",
        end_date="2026-07-30",
        symbols=["SPY", "AAPL"],
    )
    implementation = implementation_fingerprint([source])
    report["experiment_governance"] = experiment_binding(
        implementation_fingerprint=str(implementation["fingerprint"]),
    )
    report["provider_governance"] = build_unassessed_provider_governance_contract(
        provider_ids=["test_fixture"],
        generated_at="2026-07-30T00:00:00Z",
    )
    report["backtest_admission"] = build_internal_backtest_admission(report)
    return build_frozen_portfolio_candidate(report, source_files=[source])


def clean_audit(*, observations: int, rebalances: int) -> dict[str, object]:
    return {
        "status": "PASS",
        "valid_observation_count": observations,
        "timely_observation_count": observations,
        "externally_attested_observation_count": observations,
        "activation_verified_observation_count": observations,
        "clock_attestation_violation_count": 0,
        "candidate_activation_violation_count": 0,
        "risk_pass_observation_count": observations,
        "planned_rebalance_count": rebalances,
        "risk_block_reassessment_count": 0,
        "capture_violation_count": 0,
        "execution_authority_violation_count": 0,
    }


def robustness(candidate_hash: str) -> dict[str, object]:
    def result(label: str) -> dict[str, object]:
        return {
            "label": label,
            "ok": True,
            "total_return_pct": 5.0,
            "max_drawdown_pct": 8.0,
            "partial_fill_count": 0,
            "schedule_status": "PASS",
        }

    return build_robustness_assessment(
        candidate_hash=candidate_hash,
        dataset_hash="data-hash",
        parameter_results=[result(f"P{index}") for index in range(7)],
        ablation_results=[result(f"A{index}") for index in range(8)],
        capital_results=[result("CAPITAL_100K"), result("CAPITAL_1M")],
        candidate_verification={"status": "PASS"},
    )


class PortfolioForwardTests(unittest.TestCase):
    def test_active_registry_uses_control_budget_and_blocks_oversize_before_parse(self) -> None:
        limits = _portfolio_artifact_byte_limits()
        self.assertEqual(
            limits["registry"],
            MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
        )
        prefix = b'{"padding":"'
        suffix = b'"}'
        valid_raw = (
            prefix
            + b"x" * (MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES - len(prefix) - len(suffix))
            + suffix
        )
        oversized_raw = valid_raw + b" "

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "active_portfolio_candidate.json"
            path.write_bytes(valid_raw)
            raw, payload = _read_json_artifact(
                path,
                byte_limit=limits["registry"],
                size_limit_blocker="active_candidate_registry_size_limit_exceeded",
            )
            self.assertEqual(raw, valid_raw)
            self.assertEqual(len(payload["padding"]), len(valid_raw) - len(prefix) - len(suffix))

            path.write_bytes(oversized_raw)
            with patch(
                "exchange_terminal.services.forward_artifact_io.parse_strict_json_object",
            ) as parse_json, self.assertRaisesRegex(
                ValueError,
                "active_candidate_registry_size_limit_exceeded",
            ):
                _read_json_artifact(
                    path,
                    byte_limit=limits["registry"],
                    size_limit_blocker="active_candidate_registry_size_limit_exceeded",
                )
            parse_json.assert_not_called()

    def test_resealed_string_false_active_registry_is_rejected(self) -> None:
        registry = active_registry(utc_ms("2026-07-27T19:00:00+00:00"))
        registry["paper_authorized"] = "false"
        registry.pop("registry_hash")
        registry["registry_hash"] = canonical_hash(registry)

        verification = verify_active_candidate_activation(registry)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "active_candidate_registry_execution_authority_invalid",
            verification["blockers"],
        )

    def test_resealed_nested_authority_alias_active_registry_is_rejected(self) -> None:
        registry = active_registry(utc_ms("2026-07-27T19:00:00+00:00"))
        registry["nested"] = {"Can-Trade": True}
        registry.pop("registry_hash")
        registry["registry_hash"] = canonical_hash(registry)

        verification = verify_active_candidate_activation(registry)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "active_candidate_registry_contains_execution_authority",
            verification["blockers"],
        )

    def test_active_registry_reader_rejects_duplicate_keys_and_windows_alias_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            registry_path = report_dir / "active_portfolio_candidate.json"
            registry_path.write_bytes(
                b'{"status":"ACTIVE_RESEARCH_CANDIDATE","status":"NO_ACTIVE_RESEARCH_CANDIDATE"}'
            )

            duplicated = load_active_portfolio_candidate(report_dir)

            unsafe = active_registry(utc_ms("2026-07-27T19:00:00+00:00"))
            unsafe["candidate_file"] = "CON.json"
            unsafe["robustness_file"] = "robustness.json:stream"
            unsafe.pop("registry_hash")
            unsafe["registry_hash"] = canonical_hash(unsafe)
            registry_path.write_text(json.dumps(unsafe), encoding="utf-8")

            aliased = load_active_portfolio_candidate(report_dir)

        self.assertEqual(duplicated["status"], "BLOCK")
        self.assertTrue(
            any(
                "strict_json_duplicate_object_key" in blocker
                for blocker in duplicated["blockers"]
            )
        )
        self.assertIn("active_candidate_filename_invalid", aliased["blockers"])
        self.assertIn("active_robustness_filename_invalid", aliased["blockers"])

    def test_capture_window_is_after_close_and_before_next_session_open(self) -> None:
        passed_at = utc_ms("2026-07-27T22:00:00+00:00")
        waiting_at = utc_ms("2026-07-27T20:00:00+00:00")
        missed_at = utc_ms("2026-07-28T15:00:00+00:00")
        passed = build_forward_capture_contract(
            calendar_name="WEEKDAY_FIXTURE",
            signal_date="2026-07-27",
            observed_at=passed_at,
            clock_attestation=attested_clock(passed_at),
            activation_registry=active_registry(utc_ms("2026-07-27T19:00:00+00:00")),
        )
        waiting = build_forward_capture_contract(
            calendar_name="WEEKDAY_FIXTURE",
            signal_date="2026-07-27",
            observed_at=waiting_at,
            clock_attestation=attested_clock(waiting_at),
            activation_registry=active_registry(utc_ms("2026-07-27T19:00:00+00:00")),
        )
        missed = build_forward_capture_contract(
            calendar_name="WEEKDAY_FIXTURE",
            signal_date="2026-07-27",
            observed_at=missed_at,
            clock_attestation=attested_clock(missed_at),
            activation_registry=active_registry(utc_ms("2026-07-27T19:00:00+00:00")),
        )

        self.assertEqual(passed["status"], "PASS")
        self.assertTrue(passed["timely"])
        self.assertEqual(waiting["status"], "WAITING")
        self.assertEqual(missed["status"], "MISSED")
        self.assertFalse(missed["backfill_allowed"])

    def test_capture_contract_blocks_a_tampered_clock_attestation(self) -> None:
        stamp = utc_ms("2026-07-27T22:00:00+00:00")
        clock = attested_clock(stamp)
        clock["attested_now_ms"] = stamp + 60_000

        result = build_forward_capture_contract(
            calendar_name="WEEKDAY_FIXTURE",
            signal_date="2026-07-27",
            observed_at=stamp,
            clock_attestation=clock,
            activation_registry=active_registry(utc_ms("2026-07-27T19:00:00+00:00")),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["clock_attested"])

    def test_candidate_activated_after_signal_close_cannot_claim_forward_observation(self) -> None:
        observed_at = utc_ms("2026-07-27T22:00:00+00:00")
        result = build_forward_capture_contract(
            calendar_name="WEEKDAY_FIXTURE",
            signal_date="2026-07-27",
            observed_at=observed_at,
            clock_attestation=attested_clock(observed_at),
            activation_registry=active_registry(utc_ms("2026-07-27T21:00:00+00:00")),
        )

        self.assertEqual(result["status"], "PRE_ACTIVATION")
        self.assertFalse(result["candidate_active_before_signal_close"])
        self.assertFalse(result["natural_observation"])

    def test_active_registry_does_not_follow_a_newer_candidate_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            source = report_dir / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            first_path = report_dir / "portfolio_candidate_first.json"
            first = candidate(source, generation="G8_FIRST")
            first_path.write_text(json.dumps(first), encoding="utf-8")
            research_path = report_dir / "portfolio_research_first.json"
            research_path.write_text(json.dumps({"batch_run_hash": first["research_report_hash"]}), encoding="utf-8")
            robustness_path = report_dir / "portfolio_robustness_first.json"
            robustness_path.write_text(json.dumps(robustness(str(first["candidate_hash"]))), encoding="utf-8")
            registry_path = report_dir / "active_portfolio_candidate.json"
            activated = activate_portfolio_candidate(
                candidate_path=first_path,
                registry_path=registry_path,
                robustness_path=robustness_path,
                activated_at=1_020_000,
                activation_clock_attestation=attested_clock(1_020_000),
                experiment_completion_receipt=experiment_completion_receipt(
                    first,
                    report_path=research_path,
                    candidate_path=first_path,
                ),
            )
            newer_path = report_dir / "portfolio_candidate_newer.json"
            newer_path.write_text(json.dumps(candidate(source, generation="G8_NEWER")), encoding="utf-8")

            loaded = load_active_portfolio_candidate(report_dir)

        self.assertEqual(activated["status"], "ACTIVATED")
        self.assertEqual(loaded["status"], "PASS")
        self.assertEqual(loaded["candidate"]["candidate_hash"], first["candidate_hash"])
        self.assertEqual(Path(loaded["candidate_path"]).name, first_path.name)

    def test_active_candidate_retirement_is_bound_auditable_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            source = report_dir / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            candidate_path = report_dir / "portfolio_candidate.json"
            frozen = candidate(source)
            candidate_path.write_text(json.dumps(frozen), encoding="utf-8")
            research_path = report_dir / "portfolio_research.json"
            research_path.write_text(json.dumps({"batch_run_hash": frozen["research_report_hash"]}), encoding="utf-8")
            robustness_path = report_dir / "portfolio_robustness.json"
            robustness_path.write_text(json.dumps(robustness(str(frozen["candidate_hash"]))), encoding="utf-8")
            registry_path = report_dir / "active_portfolio_candidate.json"
            activated = activate_portfolio_candidate(
                candidate_path=candidate_path,
                registry_path=registry_path,
                robustness_path=robustness_path,
                activated_at=1_020_000,
                activation_clock_attestation=attested_clock(1_020_000),
                experiment_completion_receipt=experiment_completion_receipt(
                    frozen,
                    report_path=research_path,
                    candidate_path=candidate_path,
                ),
            )
            invalidation_path = report_dir / "internal_portfolio_backtest_pack_invalidated.json"
            invalidation_path.write_text(json.dumps({
                "status": "INTERNAL_BACKTEST_BLOCKED",
                "promotion_status": "BLOCK",
                "candidate": {"candidate_hash": frozen["candidate_hash"]},
                "pack_hash": "blocked-pack-hash",
            }), encoding="utf-8")

            retired = retire_active_portfolio_candidate(
                registry_path=registry_path,
                expected_candidate_hash=str(frozen["candidate_hash"]),
                retired_at=1_030_000,
                retirement_clock_attestation=attested_clock(1_030_000),
                reason="implementation and dataset contracts changed",
                invalidation_path=invalidation_path,
            )
            loaded = load_active_portfolio_candidate(report_dir)
            repeated = retire_active_portfolio_candidate(
                registry_path=registry_path,
                expected_candidate_hash=str(frozen["candidate_hash"]),
                retired_at=1_030_000,
                retirement_clock_attestation=attested_clock(1_030_000),
                reason="implementation and dataset contracts changed",
                invalidation_path=invalidation_path,
            )

        self.assertEqual(activated["status"], "ACTIVATED")
        self.assertEqual(retired["status"], "RETIRED")
        self.assertEqual(retired["retirement_verification"]["status"], "PASS")
        self.assertEqual(loaded["status"], "BLOCK")
        self.assertEqual(loaded["blockers"], ["active_candidate_retired"])
        self.assertEqual(repeated["status"], "ALREADY_RETIRED")

    def test_active_registry_detects_candidate_file_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            source = report_dir / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            candidate_path = report_dir / "portfolio_candidate.json"
            frozen = candidate(source)
            candidate_path.write_text(json.dumps(frozen), encoding="utf-8")
            research_path = report_dir / "portfolio_research.json"
            research_path.write_text(json.dumps({"batch_run_hash": frozen["research_report_hash"]}), encoding="utf-8")
            robustness_path = report_dir / "portfolio_robustness.json"
            robustness_path.write_text(json.dumps(robustness(str(frozen["candidate_hash"]))), encoding="utf-8")
            activate_portfolio_candidate(
                candidate_path=candidate_path,
                registry_path=report_dir / "active_portfolio_candidate.json",
                robustness_path=robustness_path,
                activated_at=1_020_000,
                activation_clock_attestation=attested_clock(1_020_000),
                experiment_completion_receipt=experiment_completion_receipt(
                    frozen,
                    report_path=research_path,
                    candidate_path=candidate_path,
                ),
            )
            candidate_path.write_text("{}", encoding="utf-8")

            loaded = load_active_portfolio_candidate(report_dir)

        self.assertEqual(loaded["status"], "BLOCK")
        self.assertIn("active_candidate_file_hash_mismatch", loaded["blockers"])

    def test_candidate_without_completed_experiment_cannot_be_activated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            source = report_dir / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            candidate_path = report_dir / "portfolio_candidate.json"
            frozen = candidate(source)
            candidate_path.write_text(json.dumps(frozen), encoding="utf-8")
            robustness_path = report_dir / "portfolio_robustness.json"
            robustness_path.write_text(json.dumps(robustness(str(frozen["candidate_hash"]))), encoding="utf-8")

            result = activate_portfolio_candidate(
                candidate_path=candidate_path,
                registry_path=report_dir / "active_portfolio_candidate.json",
                robustness_path=robustness_path,
                activated_at=1_020_000,
                activation_clock_attestation=attested_clock(1_020_000),
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any(item.startswith("experiment_completion:") for item in result["blockers"]))

    def test_active_candidate_detects_completed_report_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            source = report_dir / "engine.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            candidate_path = report_dir / "portfolio_candidate.json"
            frozen = candidate(source)
            candidate_path.write_text(json.dumps(frozen), encoding="utf-8")
            research_path = report_dir / "portfolio_research.json"
            research_path.write_text(json.dumps({"batch_run_hash": frozen["research_report_hash"]}), encoding="utf-8")
            robustness_path = report_dir / "portfolio_robustness.json"
            robustness_path.write_text(json.dumps(robustness(str(frozen["candidate_hash"]))), encoding="utf-8")
            activated = activate_portfolio_candidate(
                candidate_path=candidate_path,
                registry_path=report_dir / "active_portfolio_candidate.json",
                robustness_path=robustness_path,
                activated_at=1_020_000,
                activation_clock_attestation=attested_clock(1_020_000),
                experiment_completion_receipt=experiment_completion_receipt(
                    frozen,
                    report_path=research_path,
                    candidate_path=candidate_path,
                ),
            )
            research_path.write_text("{}", encoding="utf-8")

            loaded = load_active_portfolio_candidate(report_dir)

        self.assertEqual(activated["status"], "ACTIVATED")
        self.assertEqual(loaded["status"], "BLOCK")
        self.assertTrue(any("report_artifact_hash_mismatch" in item for item in loaded["blockers"]))

    def test_active_registry_detects_tampered_experiment_receipt(self) -> None:
        registry = active_registry(utc_ms("2026-07-27T19:00:00+00:00"))
        registry["experiment_completion_receipt"]["batch_run_hash"] = "tampered"
        registry_payload = dict(registry)
        registry_payload.pop("registry_hash")
        registry["registry_hash"] = canonical_hash(registry_payload)

        result = build_forward_capture_contract(
            calendar_name="WEEKDAY_FIXTURE",
            signal_date="2026-07-27",
            observed_at=utc_ms("2026-07-27T22:00:00+00:00"),
            clock_attestation=attested_clock(utc_ms("2026-07-27T22:00:00+00:00")),
            activation_registry=registry,
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("receipt_hash_mismatch" in item for item in result["blockers"]))

    def test_readiness_collects_then_requires_a_single_frozen_evaluation(self) -> None:
        frozen = {
            "candidate_hash": "candidate",
            "dataset_last": "2026-07-30",
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        verification = {"status": "PASS"}
        collecting = build_forward_readiness(
            candidate=frozen,
            candidate_verification=verification,
            ledger_audit=clean_audit(observations=59, rebalances=8),
            frozen_dataset_hash_matches=True,
        )
        ready = build_forward_readiness(
            candidate=frozen,
            candidate_verification=verification,
            ledger_audit=clean_audit(observations=60, rebalances=8),
            frozen_dataset_hash_matches=True,
        )
        violated = clean_audit(observations=60, rebalances=8)
        violated["status"] = "BLOCK"
        violated["capture_violation_count"] = 1
        blocked = build_forward_readiness(
            candidate=frozen,
            candidate_verification=verification,
            ledger_audit=violated,
            frozen_dataset_hash_matches=True,
        )

        self.assertEqual(collecting["status"], "COLLECTING")
        self.assertEqual(ready["status"], "READY_FOR_FROZEN_EVALUATION")
        self.assertTrue(ready["manual_frozen_evaluation_required"])
        self.assertFalse(ready["paper_authorized"])
        self.assertEqual(blocked["status"], "BLOCK")

    def test_readiness_rejects_string_progress_counts(self) -> None:
        frozen = {
            "candidate_hash": "candidate",
            "dataset_last": "2026-07-30",
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        ledger = clean_audit(observations=60, rebalances=8)
        ledger["valid_observation_count"] = "60"

        readiness = build_forward_readiness(
            candidate=frozen,
            candidate_verification={"status": "PASS"},
            ledger_audit=ledger,
            frozen_dataset_hash_matches=True,
        )

        self.assertEqual(readiness["status"], "BLOCK")
        self.assertFalse(readiness["critical_checks"]["ledger_metric_types_valid"])

    def test_unattested_observations_cannot_reach_forward_readiness(self) -> None:
        audit = clean_audit(observations=60, rebalances=8)
        audit["externally_attested_observation_count"] = 59

        result = build_forward_readiness(
            candidate={
                "candidate_hash": "candidate",
                "dataset_last": "2026-07-30",
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
            candidate_verification={"status": "PASS"},
            ledger_audit=audit,
            frozen_dataset_hash_matches=True,
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["critical_checks"]["all_observations_externally_attested"])


if __name__ == "__main__":
    unittest.main()
