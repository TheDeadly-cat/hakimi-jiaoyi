from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_forward_scheduler import (
    ForwardSchedulerLock,
    build_forward_observer_job_receipt,
    build_forward_observer_artifact_evidence,
    build_forward_observation_dashboard,
    build_forward_scheduler_decision,
    build_forward_scheduler_attempt_evidence,
    build_forward_scheduler_status,
    load_forward_scheduler_job_chain_origin,
    load_forward_scheduler_status,
    record_forward_scheduler_status,
    verify_forward_observer_job_receipt,
    verify_forward_scheduler_attempt_evidence,
    verify_recent_observer_jobs,
)
from exchange_terminal.services.portfolio_shadow import seal_forward_status_artifact


def utc_ms(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(timezone.utc).timestamp() * 1000)


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def change_projection_hash(
    *,
    signal_date: str,
    observation_hash: str,
    target_symbols: list[str],
    allocation: str,
    reason: str,
    regime_id: str,
    risk_status: str,
) -> str:
    return canonical_hash({
        "candidate_hash": "candidate-g9",
        "signal_date": signal_date,
        "observation_hash": observation_hash,
        "target_symbols": target_symbols,
        "total_allocation_pct": allocation,
        "reason": reason,
        "regime_id": regime_id,
        "risk_gate_status": risk_status,
    })


def job_ledger_snapshot(
    *,
    candidate_hash: str = "candidate-g9",
    count: int,
    last_signal_date: str = "",
) -> dict[str, object]:
    latest_hash = canonical_hash({"candidate": candidate_hash, "date": last_signal_date}) if count else ""
    payload: dict[str, object] = {
        "status": "PASS",
        "candidate_hash": candidate_hash,
        "ledger_audit_hash": canonical_hash({"candidate": candidate_hash, "count": count, "date": last_signal_date}),
        "observation_chain_hash": canonical_hash({"chain": candidate_hash, "count": count, "date": last_signal_date}),
        "observation_chain_count": count,
        "last_signal_date": last_signal_date,
        "latest_observation_hash": latest_hash,
    }
    payload["snapshot_hash"] = canonical_hash(payload)
    return payload


def observer_job_payload(
    outcome: str,
    *,
    started_at: int,
    candidate_hash: str = "candidate-g9",
    activation_hash: str | None = None,
    pre_count: int = 1,
    pre_last_signal_date: str = "2026-07-30",
    previous_receipt_hash: str = "",
) -> dict[str, object]:
    clean_activation_hash = activation_hash or canonical_hash({"activation": candidate_hash})
    activated_at = 100
    pre = job_ledger_snapshot(
        candidate_hash=candidate_hash,
        count=pre_count,
        last_signal_date=pre_last_signal_date,
    )
    post = dict(pre)
    observer_status = "WAITING_FOR_NEW_COMPLETED_BAR"
    observer_ok = True
    return_code = 0
    process_state = "EXITED"
    processed_count = 0
    record_count = 0
    signal_dates: list[str] = []
    artifact_verified = True
    artifact_ledger_match = True
    observer_job_id = canonical_hash({"job": candidate_hash, "start": started_at})
    observer_candidate_hash = candidate_hash
    observer_blockers: list[str] = []
    if outcome == "PROCESSED_NEW_BARS":
        observer_status = "FORWARD_OBSERVATIONS_UPDATED"
        processed_count = 1
        record_count = 1
        signal_dates = ["2026-07-31"]
        post = job_ledger_snapshot(
            candidate_hash=candidate_hash,
            count=pre_count + 1,
            last_signal_date="2026-07-31",
        )
    elif outcome == "NO_WORK_ALREADY_ACCOUNTED":
        observer_status = "UP_TO_DATE_INCREMENTAL"
    elif outcome == "BLOCKED":
        observer_status = "FORWARD_VALIDATION_BLOCKED"
        observer_ok = False
        return_code = 7
        observer_blockers = ["forward_validation_blocked"]
    elif outcome == "FAILED":
        observer_status = "OBSERVER_TIMEOUT"
        observer_ok = False
        return_code = -1
        process_state = "TIMED_OUT"
        artifact_verified = False
        artifact_ledger_match = False
        observer_job_id = ""
        observer_candidate_hash = ""
        observer_blockers = ["observer_timeout"]
    due_dates = ["2026-07-31"]
    observer = {
        "ok": observer_ok,
        "job_id": canonical_hash({"job": candidate_hash, "start": started_at}),
        "observer_job_id": observer_job_id,
        "scheduler_previous_receipt_hash": previous_receipt_hash,
        "candidate_activation_registry_hash": clean_activation_hash,
        "candidate_activated_at": activated_at,
        "scheduled_decision_hash": canonical_hash({"decision": candidate_hash, "start": started_at}),
        "due_signal_dates": due_dates,
        "due_signal_dates_hash": canonical_hash(due_dates),
        "started_at_ms": started_at,
        "finished_at_ms": started_at + 10,
        "duration_ms": 10,
        "process_state": process_state,
        "return_code": return_code,
        "status": observer_status,
        "blockers": observer_blockers,
        "observer_artifact_hash": canonical_hash({"artifact": candidate_hash, "start": started_at}) if artifact_verified else "",
        "observer_artifact_verified": artifact_verified,
        "observer_artifact_post_ledger_match": artifact_ledger_match,
        "observer_evidence_consistent": outcome != "FAILED",
        "observer_candidate_hash": observer_candidate_hash,
        "post_candidate_hash": candidate_hash,
        "post_activation_registry_hash": clean_activation_hash,
        "post_activated_at": activated_at,
        "incremental_plan_hash": canonical_hash({"outcome": outcome}),
        "work_summary_hash": canonical_hash({"outcome": outcome, "processed_count": processed_count}),
        "records_hash": canonical_hash([{"signal_date": item} for item in signal_dates]),
        "processed_count": processed_count,
        "record_count": record_count,
        "processed_signal_dates": signal_dates,
        "pre_ledger": pre,
        "post_ledger": post,
    }
    return {
        "ok": observer_ok,
        "status": "OBSERVER_COMPLETED" if observer_ok else "OBSERVER_FAILED",
        "severity": "INFO" if observer_ok else "ERROR",
        "generated_at": started_at + 11,
        "candidate_hash": candidate_hash,
        "candidate_activation_registry_hash": clean_activation_hash,
        "candidate_activated_at": activated_at,
        "scheduled_invocation": True,
        "observer_invoked": True,
        "observer": observer,
        "blockers": [] if observer_ok else observer_blockers,
    }


def artifact_evidence_for_job(
    scheduler_payload: dict[str, object],
    *,
    previous_receipt_hash: str,
) -> dict[str, object]:
    attempt = build_forward_scheduler_attempt_evidence(
        scheduler_payload,
        previous_receipt_hash=previous_receipt_hash,
    )
    observer = dict(scheduler_payload["observer"])
    post_ledger = dict(observer["post_ledger"])
    outcome = str(attempt["outcome"])
    records = [{"signal_date": item} for item in attempt["processed_signal_dates"]]
    forward_audit = {
        "candidate": scheduler_payload["candidate_hash"],
        "count": post_ledger["observation_chain_count"],
        "date": post_ledger["last_signal_date"],
    }
    artifact = seal_forward_status_artifact({
        "ok": attempt["observer_ok"],
        "status": attempt["observer_status"],
        "candidate_hash": scheduler_payload["candidate_hash"],
        "scheduler_job_id": attempt["job_id"],
        "scheduler_previous_receipt_hash": previous_receipt_hash,
        "incremental_plan": {"outcome": outcome},
        "work_summary": {"outcome": outcome, "processed_count": attempt["processed_count"]},
        "records": records,
        "ledger": {"forward_audit": forward_audit},
        "scheduler_attempt_evidence": attempt,
    })
    return build_forward_observer_artifact_evidence(
        artifact,
        candidate_hash=str(scheduler_payload["candidate_hash"]),
    )


def candidate() -> dict[str, object]:
    return {
        "candidate_hash": "candidate-g9",
        "dataset_last": "2026-07-30",
        "spec": {"benchmark_symbol": "SPY"},
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def audit(status: str = "PASS") -> dict[str, object]:
    return {
        "status": status,
        "candidate_hash": "candidate-g9",
        "capture_violation_count": 0 if status == "PASS" else 1,
    }


class PortfolioForwardSchedulerTests(unittest.TestCase):
    @staticmethod
    def dashboard_status(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": "COLLECTING",
            "candidate_hash": "candidate-g9",
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
            "readiness": {"progress": {"externally_attested_observations": 3}},
            "experiment_registry": {"status": "PASS"},
            "scheduler": {
                "status": "UP_TO_DATE",
                "health": "PASS",
                "generated_at": utc_ms("2026-08-01T10:00:00+00:00"),
                "candidate_hash": "candidate-g9",
                "decision": {
                    "status": "UP_TO_DATE",
                    "action": "NONE",
                    "due_signal_dates": [],
                    "overdue_signal_dates": [],
                    "next_check_at_ms": utc_ms("2026-08-03T20:05:00+00:00"),
                    "calendar_contract_hash": "calendar-contract",
                    "calendar_schedule_hash": "calendar-schedule",
                    "next_capture_window": {
                        "signal_date": "2026-08-03",
                        "session_close_ms": utc_ms("2026-08-03T20:00:00+00:00"),
                        "capture_not_before_ms": utc_ms("2026-08-03T20:05:00+00:00"),
                        "capture_deadline_ms": utc_ms("2026-08-04T13:25:00+00:00"),
                        "next_session_date": "2026-08-04",
                    },
                },
                "observation_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
            "observation": {
                "status": "UP_TO_DATE_INCREMENTAL",
                "generated_at": utc_ms("2026-08-01T09:59:00+00:00"),
                "candidate_hash": "candidate-g9",
                "frozen_dataset_last": "2026-07-30",
                "current_dataset_last": "2026-07-31",
                "incremental_plan": {
                    "status": "PASS",
                    "mode": "INCREMENTAL",
                    "candidate_hash": "candidate-g9",
                    "ledger_audit_status": "PASS",
                    "observation_only": True,
                    "simulation_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
                "work_summary": {
                    "mode": "INCREMENTAL",
                    "eligible_count": 1,
                    "processing_count": 1,
                    "processed_count": 1,
                    "skipped_recorded_count": 2,
                    "skipped_classified_count": 1,
                    "deferred_unrecorded_count": 0,
                },
                "ledger": {
                    "candidate_hash": "candidate-g9",
                    "last_signal_date": "2026-07-31",
                    "latest_risk_status": "PASS",
                    "forward_audit": {
                        "status": "PASS",
                        "candidate_hash": "candidate-g9",
                        "last_signal_date": "2026-07-31",
                        "latest_dataset_hash": "forward-dataset",
                        "latest_decision_hash": canonical_hash({"kind": "decision"}),
                        "latest_observation_hash": canonical_hash({"kind": "observation"}),
                        "latest_forward_state_contract_hash": canonical_hash({"kind": "forward-state"}),
                        "latest_observation_risk_snapshot_hash": canonical_hash({"kind": "risk"}),
                        "observation_chain": [
                            {
                                "signal_date": "2026-07-30",
                                "observation_hash": canonical_hash({"kind": "previous-observation"}),
                                "change_projection_hash": change_projection_hash(
                                    signal_date="2026-07-30",
                                    observation_hash=canonical_hash({"kind": "previous-observation"}),
                                    target_symbols=["AAPL"],
                                    allocation="40",
                                    reason="hold",
                                    regime_id="SIDEWAYS",
                                    risk_status="BLOCK",
                                ),
                            },
                            {
                                "signal_date": "2026-07-31",
                                "observation_hash": canonical_hash({"kind": "observation"}),
                                "change_projection_hash": change_projection_hash(
                                    signal_date="2026-07-31",
                                    observation_hash=canonical_hash({"kind": "observation"}),
                                    target_symbols=["AAPL", "NVDA"],
                                    allocation="45",
                                    reason="relative_strength_rebalance",
                                    regime_id="UP_NORMAL",
                                    risk_status="PASS",
                                ),
                            },
                        ],
                        "observation_chain_count": 2,
                        "observation_chain_hash": canonical_hash([
                            {
                                "signal_date": "2026-07-30",
                                "observation_hash": canonical_hash({"kind": "previous-observation"}),
                                "change_projection_hash": change_projection_hash(
                                    signal_date="2026-07-30",
                                    observation_hash=canonical_hash({"kind": "previous-observation"}),
                                    target_symbols=["AAPL"],
                                    allocation="40",
                                    reason="hold",
                                    regime_id="SIDEWAYS",
                                    risk_status="BLOCK",
                                ),
                            },
                            {
                                "signal_date": "2026-07-31",
                                "observation_hash": canonical_hash({"kind": "observation"}),
                                "change_projection_hash": change_projection_hash(
                                    signal_date="2026-07-31",
                                    observation_hash=canonical_hash({"kind": "observation"}),
                                    target_symbols=["AAPL", "NVDA"],
                                    allocation="45",
                                    reason="relative_strength_rebalance",
                                    regime_id="UP_NORMAL",
                                    risk_status="PASS",
                                ),
                            },
                        ]),
                        "capture_violation_count": 0,
                    },
                },
                "latest_observation_receipt": {},
                "observation_only": True,
                "simulation_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        observation = dict(payload["observation"])
        ledger_audit = dict(observation["ledger"]["forward_audit"])
        latest_receipt = {
            "schema_version": "latest-forward-observation-receipt-v1",
            "status": "VERIFIED",
            "blockers": [],
            "candidate_hash": "candidate-g9",
            "signal_date": "2026-07-31",
            "observed_at": utc_ms("2026-08-01T09:58:00+00:00"),
            "dataset_hash": "forward-dataset",
            "dataset_last": "2026-07-31",
            "target_symbols": ["AAPL", "NVDA"],
            "target_allocation_pct": 45.0,
            "reason": "relative_strength_rebalance",
            "risk_gate_status": "PASS",
            "risk_snapshot_hash": canonical_hash({"kind": "risk"}),
            "decision_hash": canonical_hash({"kind": "decision"}),
            "observation_hash": canonical_hash({"kind": "observation"}),
            "forward_state_contract_hash": canonical_hash({"kind": "forward-state"}),
            "ledger_audit_hash": canonical_hash(ledger_audit),
            "record_status": "VERIFIED_LEDGER_OBSERVATION",
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        latest_receipt["receipt_hash"] = canonical_hash(latest_receipt)
        observation["latest_observation_receipt"] = latest_receipt
        latest_change = {
            "schema_version": "forward-observation-change-v1",
            "status": "VERIFIED",
            "blockers": [],
            "candidate_hash": "candidate-g9",
            "basis": "LATEST_TWO_CONSECUTIVE_AUDITED_LEDGER_OBSERVATIONS",
            "previous": {
                "signal_date": "2026-07-30",
                "observation_hash": canonical_hash({"kind": "previous-observation"}),
                "change_projection_hash": change_projection_hash(
                    signal_date="2026-07-30",
                    observation_hash=canonical_hash({"kind": "previous-observation"}),
                    target_symbols=["AAPL"],
                    allocation="40",
                    reason="hold",
                    regime_id="SIDEWAYS",
                    risk_status="BLOCK",
                ),
            },
            "current": {
                "signal_date": "2026-07-31",
                "observation_hash": canonical_hash({"kind": "observation"}),
                "change_projection_hash": change_projection_hash(
                    signal_date="2026-07-31",
                    observation_hash=canonical_hash({"kind": "observation"}),
                    target_symbols=["AAPL", "NVDA"],
                    allocation="45",
                    reason="relative_strength_rebalance",
                    regime_id="UP_NORMAL",
                    risk_status="PASS",
                ),
            },
            "target_set": {
                "changed": True,
                "before": ["AAPL"],
                "after": ["AAPL", "NVDA"],
                "added": ["NVDA"],
                "removed": [],
                "retained": ["AAPL"],
            },
            "total_allocation_pct": {"before": "40", "after": "45", "delta": "5"},
            "reason": {"before": "hold", "after": "relative_strength_rebalance", "changed": True},
            "regime_id": {"before": "SIDEWAYS", "after": "UP_NORMAL", "changed": True},
            "risk_gate_status": {"before": "BLOCK", "after": "PASS", "changed": True},
            "evidence": {
                "ledger_audit_hash": canonical_hash(ledger_audit),
                "observation_chain_hash": ledger_audit["observation_chain_hash"],
                "observation_chain_count": 2,
                "pair_consecutive": True,
            },
            "descriptive_only": True,
            "direction_signal_allowed": False,
            "performance_claim_allowed": False,
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        latest_change["change_hash"] = canonical_hash(latest_change)
        observation["latest_observation_change"] = latest_change
        plan = dict(observation["incremental_plan"])
        plan["ledger_audit_hash"] = canonical_hash(observation["ledger"]["forward_audit"])
        plan["data_revision_evidence_hash"] = "revision-evidence"
        plan["plan_hash"] = canonical_hash(plan)
        observation["incremental_plan"] = plan
        payload["observation"] = observation
        readiness = {
            "status": "COLLECTING",
            "candidate_hash": "candidate-g9",
            "progress": {"externally_attested_observations": 3},
            "ledger_audit": dict(observation["ledger"]["forward_audit"]),
            "automatic_paper_activation_allowed": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        readiness["readiness_hash"] = canonical_hash(readiness)
        payload["readiness"] = readiness
        payload.update(overrides)
        return payload

    def test_dashboard_separates_scheduler_observer_and_completed_bar_watermarks(self) -> None:
        result = build_forward_observation_dashboard(
            self.dashboard_status(),
            now_ms=utc_ms("2026-08-01T10:01:00+00:00"),
            live_trading_hard_block=True,
        )

        self.assertEqual(result["status"], "UP_TO_DATE")
        self.assertEqual(result["service"]["status"], "PASS")
        self.assertEqual(result["observer"]["status"], "UP_TO_DATE_INCREMENTAL")
        self.assertEqual(result["latest_completed_bar"]["date"], "2026-07-31")
        self.assertEqual(result["data"]["last_accounted_date"], "2026-07-31")
        self.assertEqual(result["skipped"]["total"], 3)
        self.assertEqual(result["next_check"]["mode"], "AT")
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_dashboard_keeps_verified_latest_receipt_when_current_run_has_no_new_bar(self) -> None:
        payload = self.dashboard_status()
        observation = dict(payload["observation"])
        observation["records"] = []
        observation["work_summary"] = {
            **dict(observation["work_summary"]),
            "processing_count": 0,
            "processed_count": 0,
            "skipped_recorded_count": 1,
            "skipped_classified_count": 0,
        }
        payload["observation"] = observation

        result = build_forward_observation_dashboard(
            payload,
            now_ms=utc_ms("2026-08-01T10:01:00+00:00"),
            live_trading_hard_block=True,
        )

        self.assertEqual(result["schema_version"], "portfolio-forward-dashboard-v4")
        self.assertEqual(result["status"], "UP_TO_DATE")
        self.assertEqual(result["data"]["processed_count"], 0)
        self.assertTrue(result["latest_observation"]["known"])
        self.assertEqual(result["latest_observation"]["signal_date"], "2026-07-31")
        self.assertEqual(result["latest_observation"]["target_symbols"], ["AAPL", "NVDA"])
        self.assertEqual(result["latest_observation"]["source"], "VERIFIED_LEDGER_RECEIPT")
        self.assertTrue(result["latest_observation"]["receipt_hash"])
        self.assertTrue(result["latest_observation_change"]["known"])
        self.assertEqual(result["latest_observation_change"]["previous_signal_date"], "2026-07-30")
        self.assertEqual(result["latest_observation_change"]["current_signal_date"], "2026-07-31")
        self.assertEqual(result["latest_observation_change"]["added_symbols"], ["NVDA"])
        self.assertEqual(result["latest_observation_change"]["risk_status_before"], "BLOCK")
        self.assertEqual(result["latest_observation_change"]["risk_status_after"], "PASS")
        self.assertEqual(
            result["latest_observation_change"]["change_hash"],
            observation["latest_observation_change"]["change_hash"],
        )

    def test_dashboard_v4_projects_only_verified_neutral_observer_job_summary(self) -> None:
        payload = self.dashboard_status()
        scheduler = dict(payload["scheduler"])
        first_receipt = build_forward_observer_job_receipt(
            observer_job_payload("PROCESSED_NEW_BARS", started_at=1_000),
            sequence=1,
            previous_receipt_hash="",
        )
        latest_job_payload = observer_job_payload(
            "NO_NEW_BAR",
            started_at=1_100,
            pre_count=2,
            pre_last_signal_date="2026-07-31",
            previous_receipt_hash=str(first_receipt["receipt_hash"]),
        )
        latest_receipt = build_forward_observer_job_receipt(
            latest_job_payload,
            sequence=2,
            previous_receipt_hash=str(first_receipt["receipt_hash"]),
        )
        jobs = [first_receipt, latest_receipt]
        scheduler["schema_version"] = "portfolio-forward-scheduler-status-v2"
        scheduler["recent_observer_jobs"] = jobs
        scheduler["recent_observer_jobs_hash"] = canonical_hash(jobs)
        scheduler["observer_job_chain_head_hash"] = latest_receipt["receipt_hash"]
        payload["scheduler"] = scheduler
        evidence = artifact_evidence_for_job(
            latest_job_payload,
            previous_receipt_hash=str(first_receipt["receipt_hash"]),
        )
        self.assertEqual(evidence["status"], "PASS")

        result = build_forward_observation_dashboard(
            payload,
            now_ms=utc_ms("2026-08-01T10:01:00+00:00"),
            live_trading_hard_block=True,
            observer_artifact_evidence=evidence,
        )

        self.assertEqual(result["schema_version"], "portfolio-forward-dashboard-v4")
        self.assertEqual(len(result["recent_observer_jobs"]), 2)
        self.assertEqual(result["observer"]["last_job_status"], latest_receipt["observer_status"])
        self.assertEqual(result["observer"]["last_job_duration_ms"], latest_receipt["duration_ms"])
        summary = result["recent_observer_jobs"][-1]
        self.assertEqual(summary["outcome"], "NO_NEW_BAR")
        self.assertEqual(summary["processed_count"], 0)
        self.assertTrue(summary["descriptive_only"])
        self.assertFalse(summary["direction_signal_allowed"])
        self.assertFalse(summary["performance_claim_allowed"])
        self.assertFalse(summary["paper_authorized"])
        self.assertFalse(summary["live_order_allowed"])

        resealed = json.loads(json.dumps(payload))
        resealed_jobs = list(resealed["scheduler"]["recent_observer_jobs"])
        older = dict(resealed_jobs[0])
        older["status_only_reseal"] = True
        older.pop("receipt_hash", None)
        older["receipt_hash"] = canonical_hash(older)
        newer = dict(resealed_jobs[1])
        newer["previous_receipt_hash"] = older["receipt_hash"]
        newer.pop("receipt_hash", None)
        newer["receipt_hash"] = canonical_hash(newer)
        resealed_jobs = [older, newer]
        resealed["scheduler"]["recent_observer_jobs"] = resealed_jobs
        resealed["scheduler"]["recent_observer_jobs_hash"] = canonical_hash(resealed_jobs)
        resealed["scheduler"]["observer_job_chain_head_hash"] = newer["receipt_hash"]
        blocked = build_forward_observation_dashboard(
            resealed,
            now_ms=utc_ms("2026-08-01T10:01:00+00:00"),
            live_trading_hard_block=True,
            observer_artifact_evidence=evidence,
        )
        self.assertEqual(blocked["status"], "BLOCK")
        self.assertEqual(blocked["recent_observer_jobs"], [])
        self.assertIn("recent_observer_job_artifact_evidence_mismatch", blocked["blockers"])

        for mutation in ("empty", "downgrade", "truncate_latest"):
            hidden = json.loads(json.dumps(payload))
            if mutation == "empty":
                hidden_jobs: list[dict[str, object]] = []
            elif mutation == "truncate_latest":
                hidden_jobs = [dict(hidden["scheduler"]["recent_observer_jobs"][0])]
            else:
                hidden_jobs = list(hidden["scheduler"]["recent_observer_jobs"])
                hidden["scheduler"]["schema_version"] = "portfolio-forward-scheduler-v1"
            hidden["scheduler"]["recent_observer_jobs"] = hidden_jobs
            hidden["scheduler"]["recent_observer_jobs_hash"] = canonical_hash(hidden_jobs)
            hidden["scheduler"]["observer_job_chain_head_hash"] = (
                str(hidden_jobs[-1]["receipt_hash"]) if hidden_jobs else ""
            )
            hidden_result = build_forward_observation_dashboard(
                hidden,
                now_ms=utc_ms("2026-08-01T10:01:00+00:00"),
                live_trading_hard_block=True,
                observer_artifact_evidence=evidence,
            )
            with self.subTest(mutation=mutation):
                self.assertEqual(hidden_result["status"], "BLOCK")
                self.assertEqual(hidden_result["recent_observer_jobs"], [])

    def test_dashboard_blocks_nonempty_receipt_tampering_but_tolerates_legacy_absence(self) -> None:
        legacy_payload = self.dashboard_status()
        legacy_observation = dict(legacy_payload["observation"])
        legacy_observation.pop("latest_observation_receipt", None)
        legacy_observation.pop("latest_observation_change", None)
        legacy_payload["observation"] = legacy_observation
        legacy = build_forward_observation_dashboard(
            legacy_payload,
            now_ms=utc_ms("2026-08-01T10:01:00+00:00"),
            live_trading_hard_block=True,
        )
        self.assertNotEqual(legacy["status"], "BLOCK")
        self.assertFalse(legacy["latest_observation"]["known"])

        mutations = {
            "candidate_hash": "candidate-other",
            "signal_date": "2026-07-30",
            "paper_authorized": True,
            "decision_hash": canonical_hash({"kind": "tampered-decision"}),
            "receipt_hash": "0" * 64,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                payload = self.dashboard_status()
                observation = dict(payload["observation"])
                receipt = dict(observation["latest_observation_receipt"])
                receipt[field] = value
                if field != "receipt_hash":
                    receipt.pop("receipt_hash", None)
                    receipt["receipt_hash"] = canonical_hash(receipt)
                observation["latest_observation_receipt"] = receipt
                payload["observation"] = observation

                result = build_forward_observation_dashboard(
                    payload,
                    now_ms=utc_ms("2026-08-01T10:01:00+00:00"),
                    live_trading_hard_block=True,
                )
                self.assertEqual(result["status"], "BLOCK")
                self.assertFalse(result["latest_observation"]["known"])

    def test_dashboard_blocks_nonempty_observation_change_tampering(self) -> None:
        mutations = {
            "previous_hash": lambda item: item["previous"].update({"observation_hash": "0" * 64}),
            "chain_hash": lambda item: item["evidence"].update({"observation_chain_hash": "0" * 64}),
            "paper_authority": lambda item: item.update({"paper_authorized": True}),
            "forged_reason_claims": lambda item: item["reason"].update({
                "after": "forged_reason",
                "changed": True,
            }),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                payload = self.dashboard_status()
                observation = dict(payload["observation"])
                change = json.loads(json.dumps(observation["latest_observation_change"]))
                mutate(change)
                change.pop("change_hash", None)
                change["change_hash"] = canonical_hash(change)
                observation["latest_observation_change"] = change
                payload["observation"] = observation

                result = build_forward_observation_dashboard(
                    payload,
                    now_ms=utc_ms("2026-08-01T10:01:00+00:00"),
                    live_trading_hard_block=True,
                )
                self.assertEqual(result["status"], "BLOCK")
                self.assertFalse(result["latest_observation_change"]["known"])

    def test_dashboard_due_window_is_not_claimed_as_a_new_observation(self) -> None:
        payload = self.dashboard_status()
        scheduler = dict(payload["scheduler"])
        scheduler["decision"] = {
            "status": "CAPTURE_WINDOW_OPEN",
            "action": "RUN_OBSERVER",
            "due_signal_dates": ["2026-08-03"],
            "overdue_signal_dates": [],
            "next_check_at_ms": 0,
        }
        payload["scheduler"] = scheduler

        result = build_forward_observation_dashboard(
            payload,
            now_ms=utc_ms("2026-08-03T20:10:00+00:00"),
            live_trading_hard_block=True,
        )

        self.assertEqual(result["status"], "DUE")
        self.assertEqual(result["pending"]["dates"], ["2026-08-03"])
        self.assertEqual(result["next_check"]["mode"], "NOW")
        self.assertEqual(result["data"]["latest_completed_date"], "2026-07-31")

    def test_dashboard_never_turns_missing_skip_evidence_into_zero(self) -> None:
        payload = self.dashboard_status()
        observation = dict(payload["observation"])
        plan = dict(observation["incremental_plan"])
        plan["ledger_audit_status"] = "MISSING"
        plan.pop("plan_hash", None)
        plan["plan_hash"] = canonical_hash(plan)
        observation["incremental_plan"] = plan
        observation["work_summary"] = {}
        payload["observation"] = observation

        result = build_forward_observation_dashboard(
            payload,
            now_ms=utc_ms("2026-08-01T10:01:00+00:00"),
            live_trading_hard_block=True,
        )

        self.assertFalse(result["skipped"]["known"])
        self.assertIsNone(result["skipped"]["total"])
        self.assertIsNone(result["data"]["processed_count"])

    def test_dashboard_pauses_stale_scheduler_and_blocks_authority_drift(self) -> None:
        stale_payload = self.dashboard_status()
        stale_scheduler = dict(stale_payload["scheduler"])
        stale_scheduler["health"] = "STALE"
        stale_payload["scheduler"] = stale_scheduler
        stale = build_forward_observation_dashboard(
            stale_payload,
            now_ms=utc_ms("2026-08-01T12:00:00+00:00"),
            live_trading_hard_block=True,
        )
        unsafe_payload = self.dashboard_status(live_order_allowed=True)
        unsafe = build_forward_observation_dashboard(
            unsafe_payload,
            now_ms=utc_ms("2026-08-01T10:01:00+00:00"),
            live_trading_hard_block=False,
        )

        self.assertEqual(stale["status"], "PAUSED")
        self.assertTrue(stale["pause"]["paused"])
        self.assertEqual(unsafe["status"], "BLOCK")
        self.assertIn("forward_execution_authority_invalid", unsafe["blockers"])
        self.assertIn("live_trading_hard_block_missing", unsafe["blockers"])
        self.assertFalse(unsafe["live_order_allowed"])

    def test_candidate_string_false_authority_blocks_scheduling(self) -> None:
        unsafe = candidate()
        unsafe["research_only"] = "false"

        result = build_forward_scheduler_decision(
            candidate=unsafe,
            attested_now_ms=utc_ms("2026-07-31T22:00:00+00:00"),
            observed_dates=[],
            capture_event_dates=[],
            ledger_audit=audit(),
            calendar_name="WEEKDAY_FIXTURE",
        )

        self.assertEqual(result["status"], "SCHEDULER_DECISION_BLOCKED")
        self.assertIn("candidate_execution_authority_invalid", result["blockers"])

    def test_open_capture_window_runs_the_observer(self) -> None:
        result = build_forward_scheduler_decision(
            candidate=candidate(),
            attested_now_ms=utc_ms("2026-07-31T22:00:00+00:00"),
            observed_dates=[],
            capture_event_dates=[],
            ledger_audit=audit(),
            calendar_name="WEEKDAY_FIXTURE",
        )

        self.assertEqual(result["status"], "CAPTURE_WINDOW_OPEN")
        self.assertEqual(result["action"], "RUN_OBSERVER")
        self.assertEqual(result["due_signal_dates"], ["2026-07-31"])

    def test_accounted_capture_waits_for_the_next_session(self) -> None:
        result = build_forward_scheduler_decision(
            candidate=candidate(),
            attested_now_ms=utc_ms("2026-08-01T10:00:00+00:00"),
            observed_dates=["2026-07-31"],
            capture_event_dates=[],
            ledger_audit=audit(),
            calendar_name="WEEKDAY_FIXTURE",
        )

        self.assertEqual(result["status"], "UP_TO_DATE")
        self.assertEqual(result["action"], "NONE")
        self.assertGreater(result["next_check_at_ms"], result["attested_now_ms"])
        self.assertEqual(result["next_capture_window"]["signal_date"], "2026-08-03")
        self.assertGreater(
            result["next_capture_window"]["capture_deadline_ms"],
            result["next_capture_window"]["capture_not_before_ms"],
        )

    def test_overdue_unaccounted_session_requires_audit_run(self) -> None:
        result = build_forward_scheduler_decision(
            candidate=candidate(),
            attested_now_ms=utc_ms("2026-08-03T15:00:00+00:00"),
            observed_dates=[],
            capture_event_dates=[],
            ledger_audit=audit(),
            calendar_name="WEEKDAY_FIXTURE",
        )

        self.assertEqual(result["status"], "OVERDUE_CAPTURE_AUDIT_REQUIRED")
        self.assertEqual(result["severity"], "CRITICAL")
        self.assertIn("2026-07-31", result["overdue_signal_dates"])

    def test_blocked_forward_ledger_stops_automatic_collection(self) -> None:
        result = build_forward_scheduler_decision(
            candidate=candidate(),
            attested_now_ms=utc_ms("2026-08-01T10:00:00+00:00"),
            observed_dates=[],
            capture_event_dates=["2026-07-31"],
            ledger_audit=audit("BLOCK"),
            calendar_name="WEEKDAY_FIXTURE",
        )

        self.assertEqual(result["status"], "FORWARD_LEDGER_BLOCKED")
        self.assertEqual(result["action"], "NONE")

    def test_unverified_forward_ledger_cannot_account_capture_dates(self) -> None:
        unverified = audit("MISSING")
        result = build_forward_scheduler_decision(
            candidate=candidate(),
            attested_now_ms=utc_ms("2026-08-01T10:00:00+00:00"),
            observed_dates=[],
            capture_event_dates=["2026-07-31"],
            ledger_audit=unverified,
            calendar_name="WEEKDAY_FIXTURE",
        )

        self.assertEqual(result["status"], "SCHEDULER_DECISION_BLOCKED")
        self.assertEqual(result["action"], "NONE")
        self.assertIn("forward_ledger_not_verified:MISSING", result["blockers"])

    def test_lock_prevents_concurrent_scheduler_runs_and_recovers_stale_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lock_path = Path(temporary) / "scheduler.lock"
            first = ForwardSchedulerLock(lock_path, now_ms=lambda: 100, pid_exists=lambda pid: pid > 0)
            second = ForwardSchedulerLock(lock_path, now_ms=lambda: 200, pid_exists=lambda pid: pid > 0)
            self.assertEqual(first.acquire()["status"], "ACQUIRED")
            self.assertEqual(second.acquire()["status"], "BUSY")
            first.release()

            lock_path.write_text(json.dumps({"pid": 999999, "token": "stale", "created_at": 1}), encoding="utf-8")
            recovered = ForwardSchedulerLock(lock_path, now_ms=lambda: 300, pid_exists=lambda pid: False)
            self.assertEqual(recovered.acquire()["status"], "ACQUIRED")
            recovered.release()
            self.assertTrue(any(Path(temporary).glob("scheduler.lock.stale.*")))

    def test_status_hash_and_staleness_are_audited(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            alert_path = Path(temporary) / "alerts.jsonl"
            record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload={
                    "ok": True,
                    "status": "UP_TO_DATE",
                    "severity": "INFO",
                    "generated_at": 1_000,
                    "candidate_hash": "candidate-g9",
                    "scheduled_invocation": True,
                },
            )
            fresh = load_forward_scheduler_status(status_path, now_ms=2_000, stale_after_ms=5_000)
            stale = load_forward_scheduler_status(status_path, now_ms=10_000, stale_after_ms=5_000)
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            payload["status"] = "TAMPERED"
            status_path.write_text(json.dumps(payload), encoding="utf-8")
            tampered = load_forward_scheduler_status(status_path, now_ms=2_000, stale_after_ms=5_000)

        self.assertEqual(fresh["health"], "PASS")
        self.assertEqual(stale["health"], "STALE")
        self.assertEqual(tampered["health"], "BLOCK")
        self.assertIn("scheduler_status_hash_mismatch", tampered["blockers"])

    def test_observer_job_chain_origin_is_genesis_or_verified_head_and_blocks_damage(self) -> None:
        activation_hash = canonical_hash({"activation": "candidate-g9"})
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            alert_path = Path(temporary) / "alerts.jsonl"
            genesis = load_forward_scheduler_job_chain_origin(
                status_path,
                candidate_hash="candidate-g9",
                candidate_activation_registry_hash=activation_hash,
                candidate_activated_at=100,
            )
            recorded = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=observer_job_payload("PROCESSED_NEW_BARS", started_at=1_000),
            )
            continued = load_forward_scheduler_job_chain_origin(
                status_path,
                candidate_hash="candidate-g9",
                candidate_activation_registry_hash=activation_hash,
                candidate_activated_at=100,
            )
            failed = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=observer_job_payload(
                    "FAILED",
                    started_at=1_100,
                    pre_count=2,
                    pre_last_signal_date="2026-07-31",
                    previous_receipt_hash=str(recorded["observer_job_chain_head_hash"]),
                ),
            )
            reconciliation_blocked = load_forward_scheduler_job_chain_origin(
                status_path,
                candidate_hash="candidate-g9",
                candidate_activation_registry_hash=activation_hash,
                candidate_activated_at=100,
            )
            damaged = json.loads(status_path.read_text(encoding="utf-8"))
            damaged["status"] = "RESEALED_WITHOUT_HASH_UPDATE"
            status_path.write_text(json.dumps(damaged), encoding="utf-8")
            blocked = load_forward_scheduler_job_chain_origin(
                status_path,
                candidate_hash="candidate-g9",
                candidate_activation_registry_hash=activation_hash,
                candidate_activated_at=100,
            )

        self.assertEqual(genesis["origin"], "GENESIS")
        self.assertEqual(continued["origin"], "CONTINUE")
        self.assertEqual(
            continued["previous_receipt_hash"],
            recorded["observer_job_chain_head_hash"],
        )
        self.assertTrue(failed["recent_observer_jobs"][-1]["reconciliation_required"])
        self.assertEqual(reconciliation_blocked["origin"], "BLOCKED")
        self.assertIn(
            "scheduler_job_chain_reconciliation_required",
            reconciliation_blocked["blockers"],
        )
        self.assertEqual(blocked["status"], "BLOCK")

    def test_observer_job_receipt_classifies_only_proven_outcomes(self) -> None:
        for expected_outcome in (
            "PROCESSED_NEW_BARS",
            "NO_NEW_BAR",
            "NO_WORK_ALREADY_ACCOUNTED",
            "BLOCKED",
            "FAILED",
        ):
            with self.subTest(outcome=expected_outcome):
                payload = observer_job_payload(expected_outcome, started_at=1_000)
                receipt = build_forward_observer_job_receipt(
                    payload,
                    sequence=1,
                    previous_receipt_hash="",
                )
                verification = verify_forward_observer_job_receipt(
                    receipt,
                    candidate_hash="candidate-g9",
                )
                attempt = build_forward_scheduler_attempt_evidence(
                    payload,
                    previous_receipt_hash="",
                )
                attempt_verification = verify_forward_scheduler_attempt_evidence(
                    attempt,
                    candidate_hash="candidate-g9",
                )
                self.assertEqual(receipt["outcome"], expected_outcome)
                self.assertEqual(verification["status"], "PASS")
                self.assertEqual(attempt_verification["status"], "PASS")
                self.assertEqual(attempt["outcome"], receipt["outcome"])
                self.assertIs(attempt["reconciliation_required"], receipt["reconciliation_required"])
                self.assertIs(
                    receipt["reconciliation_required"],
                    expected_outcome == "FAILED",
                )

        launch_failed = observer_job_payload("FAILED", started_at=1_500)
        launch_observer = dict(launch_failed["observer"])
        launch_observer.update({
            "process_state": "LAUNCH_FAILED",
            "status": "OBSERVER_LAUNCH_FAILED",
            "blockers": ["observer_launch_failed:FileNotFoundError"],
        })
        launch_failed["observer"] = launch_observer
        launch_attempt = build_forward_scheduler_attempt_evidence(
            launch_failed,
            previous_receipt_hash="",
        )
        self.assertEqual(
            verify_forward_scheduler_attempt_evidence(
                launch_attempt,
                candidate_hash="candidate-g9",
            )["status"],
            "PASS",
        )
        self.assertEqual(launch_attempt["outcome"], "FAILED")
        self.assertTrue(launch_attempt["reconciliation_required"])

        blocked_after_mutation = observer_job_payload("BLOCKED", started_at=2_000)
        blocked_observer = dict(blocked_after_mutation["observer"])
        blocked_observer["post_ledger"] = job_ledger_snapshot(
            count=2,
            last_signal_date="2026-07-31",
        )
        blocked_after_mutation["observer"] = blocked_observer
        blocked_receipt = build_forward_observer_job_receipt(
            blocked_after_mutation,
            sequence=1,
            previous_receipt_hash="",
        )
        self.assertEqual(blocked_receipt["outcome"], "FAILED")
        self.assertTrue(blocked_receipt["reconciliation_required"])

        no_new_with_blocked_audit = observer_job_payload("NO_NEW_BAR", started_at=3_000)
        no_new_observer = dict(no_new_with_blocked_audit["observer"])
        blocked_snapshot = dict(no_new_observer["post_ledger"])
        blocked_snapshot["status"] = "BLOCK"
        blocked_snapshot.pop("snapshot_hash", None)
        blocked_snapshot["snapshot_hash"] = canonical_hash(blocked_snapshot)
        no_new_observer["post_ledger"] = blocked_snapshot
        no_new_with_blocked_audit["observer"] = no_new_observer
        no_new_receipt = build_forward_observer_job_receipt(
            no_new_with_blocked_audit,
            sequence=1,
            previous_receipt_hash="",
        )
        self.assertEqual(no_new_receipt["outcome"], "FAILED")
        self.assertTrue(no_new_receipt["reconciliation_required"])

    def test_recent_observer_jobs_carry_append_trim_and_reset_on_candidate_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            alert_path = Path(temporary) / "alerts.jsonl"
            first = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=observer_job_payload("PROCESSED_NEW_BARS", started_at=1_000),
            )
            first_jobs = json.loads(json.dumps(first["recent_observer_jobs"]))
            carried = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload={
                    "ok": True,
                    "status": "UP_TO_DATE",
                    "severity": "INFO",
                    "generated_at": 1_050,
                    "candidate_hash": "candidate-g9",
                    "candidate_activation_registry_hash": canonical_hash({"activation": "candidate-g9"}),
                    "candidate_activated_at": 100,
                    "scheduled_invocation": True,
                },
            )
            second = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=observer_job_payload(
                    "NO_NEW_BAR",
                    started_at=1_100,
                    pre_count=2,
                    pre_last_signal_date="2026-07-31",
                    previous_receipt_hash=str(first["observer_job_chain_head_hash"]),
                ),
            )
            third = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=observer_job_payload(
                    "NO_WORK_ALREADY_ACCOUNTED",
                    started_at=1_200,
                    pre_count=2,
                    pre_last_signal_date="2026-07-31",
                    previous_receipt_hash=str(second["observer_job_chain_head_hash"]),
                ),
            )
            reset = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload={
                    "ok": True,
                    "status": "UP_TO_DATE",
                    "severity": "INFO",
                    "generated_at": 1_300,
                    "candidate_hash": "candidate-new",
                    "candidate_activation_registry_hash": canonical_hash({"activation": "candidate-new"}),
                    "candidate_activated_at": 200,
                    "scheduled_invocation": True,
                },
            )

        self.assertEqual(carried["recent_observer_jobs"], first_jobs)
        self.assertEqual(carried["observer_job_chain_head_hash"], first["observer_job_chain_head_hash"])
        self.assertEqual([job["sequence"] for job in second["recent_observer_jobs"]], [1, 2])
        self.assertEqual(
            second["recent_observer_jobs"][1]["previous_receipt_hash"],
            second["recent_observer_jobs"][0]["receipt_hash"],
        )
        self.assertEqual([job["sequence"] for job in third["recent_observer_jobs"]], [2, 3])
        self.assertEqual(
            verify_recent_observer_jobs(third, candidate_hash="candidate-g9")["status"],
            "PASS",
        )
        self.assertEqual(reset["recent_observer_jobs"], [])
        self.assertEqual(reset["observer_job_chain_head_hash"], "")

    def test_resealed_observer_job_chain_tampering_blocks_load(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            alert_path = Path(temporary) / "alerts.jsonl"
            first = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=observer_job_payload("PROCESSED_NEW_BARS", started_at=1_000),
            )
            record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload=observer_job_payload(
                    "NO_NEW_BAR",
                    started_at=1_100,
                    pre_count=2,
                    pre_last_signal_date="2026-07-31",
                    previous_receipt_hash=str(first["observer_job_chain_head_hash"]),
                ),
            )
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            newer = dict(payload["recent_observer_jobs"][1])
            newer["previous_receipt_hash"] = "0" * 64
            newer.pop("receipt_hash", None)
            newer["receipt_hash"] = canonical_hash(newer)
            payload["recent_observer_jobs"][1] = newer
            payload["recent_observer_jobs_hash"] = canonical_hash(payload["recent_observer_jobs"])
            payload["observer_job_chain_head_hash"] = newer["receipt_hash"]
            payload.pop("status_hash", None)
            payload["status_hash"] = canonical_hash(payload)
            status_path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_forward_scheduler_status(status_path, now_ms=1_200)

            current_without_history = build_forward_scheduler_status({
                "ok": True,
                "status": "UP_TO_DATE",
                "severity": "INFO",
                "generated_at": 1_000,
                "candidate_hash": "candidate-g9",
                "scheduled_invocation": True,
            })
            for field in (
                "recent_observer_jobs",
                "recent_observer_jobs_hash",
                "observer_job_chain_head_hash",
            ):
                current_without_history.pop(field, None)
            current_without_history.pop("status_hash", None)
            current_without_history["status_hash"] = canonical_hash(current_without_history)
            status_path.write_text(json.dumps(current_without_history), encoding="utf-8")
            missing_current = load_forward_scheduler_status(status_path, now_ms=1_200)

            legacy_without_history = dict(current_without_history)
            legacy_without_history["schema_version"] = "portfolio-forward-scheduler-v1"
            legacy_without_history.pop("status_hash", None)
            legacy_without_history["status_hash"] = canonical_hash(legacy_without_history)
            status_path.write_text(json.dumps(legacy_without_history), encoding="utf-8")
            accepted_legacy = load_forward_scheduler_status(status_path, now_ms=1_200)

        self.assertEqual(loaded["health"], "BLOCK")
        self.assertIn("recent_observer_job_chain_broken", loaded["blockers"])
        self.assertEqual(missing_current["health"], "BLOCK")
        self.assertIn("scheduler_observer_job_history_missing", missing_current["blockers"])
        self.assertEqual(accepted_legacy["health"], "PASS")

    def test_resealed_string_observation_flag_blocks_scheduler_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            payload = build_forward_scheduler_status({
                "ok": True,
                "status": "UP_TO_DATE",
                "severity": "INFO",
                "generated_at": 1_000,
                "candidate_hash": "candidate-g9",
                "scheduled_invocation": True,
            })
            payload["observation_only"] = "false"
            payload.pop("status_hash")
            payload["status_hash"] = canonical_hash(payload)
            status_path.write_text(json.dumps(payload), encoding="utf-8")

            loaded = load_forward_scheduler_status(status_path, now_ms=2_000, stale_after_ms=5_000)

        self.assertEqual(loaded["health"], "BLOCK")
        self.assertIn("scheduler_status_has_execution_authority", loaded["blockers"])

    def test_invalid_or_future_scheduler_heartbeat_and_reported_blockers_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "status.json"

            invalid = build_forward_scheduler_status({
                "ok": True,
                "status": "UP_TO_DATE",
                "severity": "INFO",
                "generated_at": "not-a-time",
                "candidate_hash": "candidate-g9",
                "scheduled_invocation": True,
            })
            path.write_text(json.dumps(invalid), encoding="utf-8")
            invalid_loaded = load_forward_scheduler_status(path, now_ms=1_000)

            future = build_forward_scheduler_status({
                "ok": True,
                "status": "UP_TO_DATE",
                "severity": "INFO",
                "generated_at": 10_000,
                "candidate_hash": "candidate-g9",
                "scheduled_invocation": True,
            })
            path.write_text(json.dumps(future), encoding="utf-8")
            future_loaded = load_forward_scheduler_status(path, now_ms=1_000)

            reported = build_forward_scheduler_status({
                "ok": True,
                "status": "UP_TO_DATE",
                "severity": "INFO",
                "generated_at": 1_000,
                "candidate_hash": "candidate-g9",
                "blockers": ["data_revision_unverified"],
                "scheduled_invocation": True,
            })
            path.write_text(json.dumps(reported), encoding="utf-8")
            reported_loaded = load_forward_scheduler_status(path, now_ms=2_000)

            failed = build_forward_scheduler_status({
                "ok": False,
                "status": "OBSERVER_FAILED",
                "severity": "INFO",
                "generated_at": 1_000,
                "candidate_hash": "candidate-g9",
                "blockers": [],
                "scheduled_invocation": True,
            })
            path.write_text(json.dumps(failed), encoding="utf-8")
            failed_loaded = load_forward_scheduler_status(path, now_ms=2_000)

        self.assertEqual(invalid_loaded["health"], "BLOCK")
        self.assertIn("scheduler_generated_at_invalid", invalid_loaded["blockers"])
        self.assertEqual(future_loaded["health"], "BLOCK")
        self.assertIn("scheduler_generated_at_from_future", future_loaded["blockers"])
        self.assertEqual(reported_loaded["health"], "BLOCK")
        self.assertIn("data_revision_unverified", reported_loaded["blockers"])
        self.assertEqual(failed_loaded["health"], "BLOCK")
        self.assertIn("scheduler_status_not_ok", failed_loaded["blockers"])

    def test_identical_critical_condition_is_alerted_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            alert_path = Path(temporary) / "alerts.jsonl"
            for generated_at in (1_000, 2_000):
                record_forward_scheduler_status(
                    status_path=status_path,
                    alert_path=alert_path,
                    payload={
                        "ok": False,
                        "status": "OBSERVER_FAILED",
                        "severity": "ERROR",
                        "generated_at": generated_at,
                        "candidate_hash": "candidate-g9",
                        "blockers": ["DATA_UNAVAILABLE"],
                        "scheduled_invocation": True,
                    },
                )

            alerts = alert_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(alerts), 1)

    def test_dry_run_preview_does_not_replace_recorded_scheduler_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            status_path = Path(temporary) / "status.json"
            alert_path = Path(temporary) / "alerts.jsonl"
            record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload={
                    "ok": True,
                    "status": "UP_TO_DATE",
                    "severity": "INFO",
                    "generated_at": 1_000,
                    "candidate_hash": "candidate-g9",
                    "scheduled_invocation": True,
                },
            )
            recorded_bytes = status_path.read_bytes()

            preview = build_forward_scheduler_status({
                "ok": True,
                "status": "DRY_RUN_UP_TO_DATE",
                "severity": "INFO",
                "generated_at": 2_000,
                "candidate_hash": "candidate-g9",
                "scheduled_invocation": False,
                "dry_run": True,
                "persistence": "PREVIEW_ONLY_NOT_RECORDED",
            })
            loaded = load_forward_scheduler_status(status_path, now_ms=2_000, stale_after_ms=5_000)
            persisted_bytes = status_path.read_bytes()

        self.assertEqual(preview["status"], "DRY_RUN_UP_TO_DATE")
        self.assertEqual(preview["persistence"], "PREVIEW_ONLY_NOT_RECORDED")
        self.assertEqual(persisted_bytes, recorded_bytes)
        self.assertEqual(loaded["status"], "UP_TO_DATE")
        self.assertEqual(loaded["health"], "PASS")


if __name__ == "__main__":
    unittest.main()
