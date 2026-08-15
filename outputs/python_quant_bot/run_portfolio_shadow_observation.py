from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from exchange_terminal import server
from exchange_terminal.services.portfolio_backtest import (
    prepare_attested_portfolio_dataset,
    relative_strength_settings_from_spec,
    run_causal_relative_strength_backtest,
    slice_portfolio_payload_through_date,
)
from exchange_terminal.services.portfolio_candidate import verify_frozen_portfolio_candidate
from exchange_terminal.services.portfolio_forward import (
    DEFAULT_ACTIVE_CANDIDATE_FILE,
    build_forward_capture_contract,
    build_forward_readiness,
    load_active_portfolio_candidate,
)
from exchange_terminal.services.portfolio_forward_performance import forward_evidence_thresholds_from_spec
from exchange_terminal.services.portfolio_risk import build_correlation_matrix
from exchange_terminal.services.portfolio_shadow import (
    PortfolioShadowLedger,
    build_forward_state_contract,
    build_incremental_observation_plan,
    build_shadow_observation,
    seal_forward_status_artifact,
)
from exchange_terminal.services.portfolio_shadow_risk import build_shadow_portfolio_risk
from exchange_terminal.services.trusted_clock import attest_utc_clock

def payload_metadata(
    payload: dict[str, Any],
    *,
    rows: list[dict[str, Any]],
    cutoff: str = "",
    adjustment_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actions = [dict(item) for item in payload.get("corporate_actions") or []]
    lifecycle = [dict(item) for item in payload.get("trading_status_events") or []]
    if cutoff:
        actions = [
            item for item in actions
            if str(item.get("event_date") or item.get("date") or "") <= cutoff
        ]
        lifecycle = [
            item for item in lifecycle
            if str(item.get("start_date") or item.get("event_date") or item.get("date") or "") <= cutoff
        ]
    result = {
        "symbol": str(payload.get("symbol") or "").upper(),
        "source": str(payload.get("source") or ""),
        "origin_source": str(payload.get("origin_source") or ""),
        "adjustment_basis": str(payload.get("adjustment_basis") or ""),
        "corporate_action_coverage": str(payload.get("corporate_action_coverage") or ""),
        "corporate_actions": actions,
        "adjustment_evidence": dict(adjustment_evidence or {}),
        "data_revision_evidence": dict(payload.get("data_revision_evidence") or {}),
        "trading_status_events": lifecycle,
        "market_calendar": str(payload.get("market_calendar") or ""),
        "rows": [dict(row) for row in rows],
    }
    return result


def engine_settings(spec: dict[str, Any]) -> dict[str, Any]:
    return relative_strength_settings_from_spec(spec)


def write_forward_status(report_dir: Path, candidate_hash: str, payload: dict[str, Any]) -> Path:
    path = report_dir / f"portfolio_forward_status_{candidate_hash[:12] or 'unknown'}.json"
    temporary = path.with_name(f".{path.name}.tmp")
    sealed = seal_forward_status_artifact(payload)
    payload.clear()
    payload.update(sealed)
    temporary.write_text(json.dumps(sealed, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return path


def compact_dataset_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": str(manifest.get("status") or "UNKNOWN"),
        "blockers": list(manifest.get("blockers") or []),
        "warnings": list(manifest.get("warnings") or []),
        "row_count": int(manifest.get("row_count") or 0),
        "first": str(manifest.get("first") or ""),
        "last": str(manifest.get("last") or ""),
        "data_hash": str(manifest.get("data_hash") or ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record future completed-bar portfolio decisions without placing paper orders.")
    parser.add_argument("--candidate", default="")
    parser.add_argument("--registry", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--ledger", default="")
    parser.add_argument("--scheduler-job-id", default="")
    parser.add_argument("--scheduler-previous-receipt-hash", default="")
    parser.add_argument(
        "--replay-recorded",
        action="store_true",
        help="Explicitly audit-replay recorded dates without capturing new dates.",
    )
    args = parser.parse_args()
    scheduler_job_id = str(args.scheduler_job_id or "")
    scheduler_previous_receipt_hash = str(args.scheduler_previous_receipt_hash or "")
    if scheduler_job_id and (
        len(scheduler_job_id) != 64
        or any(character not in "0123456789abcdef" for character in scheduler_job_id)
    ):
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "reason": "scheduler_job_id_invalid",
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False, indent=2))
        return 2
    if scheduler_previous_receipt_hash and (
        len(scheduler_previous_receipt_hash) != 64
        or any(character not in "0123456789abcdef" for character in scheduler_previous_receipt_hash)
    ):
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "reason": "scheduler_previous_receipt_hash_invalid",
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False, indent=2))
        return 2

    report_dir = Path(server.RUNTIME_DIR) / "reports"
    if args.candidate:
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "reason": "explicit_candidate_override_cannot_record_forward_evidence",
            "required_path": "active_candidate_registry",
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False, indent=2))
        return 2
    active_registry: dict[str, Any] = {}
    registry_path = Path(args.registry).resolve() if args.registry else report_dir / DEFAULT_ACTIVE_CANDIDATE_FILE
    active = load_active_portfolio_candidate(report_dir, registry_path=registry_path)
    if active["status"] != "PASS":
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "reason": "active_candidate_registry_blocked",
            "active_candidate": active,
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False, indent=2))
        return 2
    candidate_path = Path(str(active["candidate_path"]))
    candidate = dict(active["candidate"])
    verification = dict(active["candidate_verification"])
    active_registry = dict(active["registry"])
    if verification["status"] != "PASS":
        print(json.dumps({"ok": False, "status": "BLOCK", "candidate_verification": verification}, ensure_ascii=False, indent=2))
        return 2
    spec = dict(candidate.get("spec") or {})
    dataset_lineage_id = str(spec.get("experiment_id") or candidate.get("candidate_hash") or "").strip()
    settings = engine_settings(spec)
    settings["universe_contract"] = dict(
        (candidate.get("research_governance") or {}).get("universe_contract") or {}
    )
    benchmark = settings["benchmark_symbol"]
    symbols = [benchmark, *settings["tradable_symbols"]]
    requested_limit = int(args.limit) if int(args.limit) > 0 else max(int(candidate.get("dataset_row_count") or 0) + 60, 180)
    raw_payloads = {
        symbol: server.backtest_market_rows(
            symbol,
            requested_limit,
            dataset_lineage_id=dataset_lineage_id,
        )
        for symbol in symbols
    }
    prepared = prepare_attested_portfolio_dataset(
        raw_payloads,
        benchmark_symbol=benchmark,
        minimum_rows=180,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
        universe_contract=settings["universe_contract"],
    )
    if prepared["status"] != "PASS":
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "reason": "current_dataset_blocked",
            "dataset_manifest": compact_dataset_manifest(prepared["manifest"]),
        }, ensure_ascii=False, indent=2))
        return 3
    candidate_first = str(candidate.get("dataset_first") or "")
    candidate_last = str(candidate.get("dataset_last") or "")
    if not candidate_first or str(prepared["manifest"].get("first") or "") > candidate_first:
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "reason": "candidate_history_start_is_not_covered",
            "candidate_first": candidate_first,
            "available_first": prepared["manifest"].get("first"),
        }, ensure_ascii=False, indent=2))
        return 4
    continuation_payloads = {
        symbol: payload_metadata(
            prepared["payloads"].get(symbol) or {},
            rows=[dict(row) for row in prepared["rows"][symbol] if str(row.get("date") or "") >= candidate_first],
            adjustment_evidence=dict((prepared["manifest"].get("adjustment_evidence", {}).get(symbol) or {})),
        )
        for symbol in prepared["manifest"]["symbols"]
    }
    prepared = prepare_attested_portfolio_dataset(
        continuation_payloads,
        benchmark_symbol=benchmark,
        minimum_rows=180,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
        universe_contract=settings["universe_contract"],
    )
    if prepared["status"] != "PASS":
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "reason": "continuation_dataset_blocked",
            "dataset_manifest": compact_dataset_manifest(prepared["manifest"]),
        }, ensure_ascii=False, indent=2))
        return 5
    aligned_payloads = dict(prepared["payloads"])
    frozen_payloads = {
        symbol: slice_portfolio_payload_through_date(
            payload,
            candidate_last,
            attest_backtest_rows=server.attest_stock_backtest_rows,
            dataset_lineage_id=dataset_lineage_id,
        )
        for symbol, payload in aligned_payloads.items()
    }
    frozen_prepared = prepare_attested_portfolio_dataset(
        frozen_payloads,
        benchmark_symbol=benchmark,
        minimum_rows=180,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
        universe_contract=settings["universe_contract"],
    )
    current_frozen_hash = str(frozen_prepared["manifest"].get("data_hash") or "")
    if frozen_prepared["status"] != "PASS" or current_frozen_hash != str(candidate.get("dataset_hash") or ""):
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "reason": "frozen_dataset_hash_mismatch",
            "candidate_dataset_hash": candidate.get("dataset_hash"),
            "current_frozen_dataset_hash": current_frozen_hash,
            "frozen_dataset_manifest": compact_dataset_manifest(frozen_prepared["manifest"]),
        }, ensure_ascii=False, indent=2))
        return 6
    frozen_last = candidate_last
    dates = list(prepared.get("dates") or [])
    new_indexes = [index for index, trading_date in enumerate(dates) if str(trading_date) > frozen_last]
    ledger_path = Path(args.ledger) if args.ledger else Path(server.RUNTIME_DIR) / "portfolio_shadow.sqlite"
    ledger = PortfolioShadowLedger(ledger_path)
    candidate_hash = str(candidate.get("candidate_hash") or "")
    threshold_contract = forward_evidence_thresholds_from_spec(spec)
    if threshold_contract["status"] != "PASS":
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "reason": "candidate_forward_threshold_contract_invalid",
            "threshold_contract": threshold_contract,
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False, indent=2))
        return 7
    minimum_observations = int(threshold_contract["minimum_forward_observations"])
    minimum_rebalances = int(threshold_contract["minimum_planned_rebalances"])
    clock_attestation = attest_utc_clock()
    if clock_attestation.get("status") != "PASS":
        latest_audit = ledger.audit(candidate_hash)
        payload = {
            "ok": False,
            "status": "CLOCK_ATTESTATION_BLOCKED",
            "generated_at": server.now_ms(),
            "candidate_hash": candidate_hash,
            "scheduler_job_id": scheduler_job_id,
            "scheduler_previous_receipt_hash": scheduler_previous_receipt_hash,
            "candidate_path": str(candidate_path.resolve()),
            "active_candidate": active_registry,
            "clock_attestation": clock_attestation,
            "ledger": ledger.summary(candidate_hash),
            "latest_observation_receipt": ledger.latest_observation_receipt(
                candidate_hash,
                ledger_audit=latest_audit,
            ),
            "latest_observation_change": ledger.latest_observation_change(
                candidate_hash,
                ledger_audit=latest_audit,
            ),
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        status_path = write_forward_status(report_dir, candidate_hash, payload)
        payload["status_artifact"] = str(status_path.resolve())
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 8

    recorded_dates = set(ledger.observation_dates(candidate_hash))
    classified_event_dates = set(ledger.capture_event_dates(candidate_hash))
    ledger_audit = ledger.audit(candidate_hash)
    incremental_plan = build_incremental_observation_plan(
        candidate_hash=candidate_hash,
        all_dates=dates,
        frozen_last=frozen_last,
        recorded_dates=sorted(recorded_dates),
        classified_dates=sorted(classified_event_dates),
        ledger_audit=ledger_audit,
        data_revision_evidence=dict(prepared["manifest"].get("data_revision_evidence") or {}),
        replay_recorded=bool(args.replay_recorded),
    )
    if incremental_plan["status"] != "PASS":
        payload = {
            "ok": False,
            "status": "INCREMENTAL_OBSERVATION_PLAN_BLOCKED",
            "generated_at": server.now_ms(),
            "candidate_hash": candidate_hash,
            "scheduler_job_id": scheduler_job_id,
            "scheduler_previous_receipt_hash": scheduler_previous_receipt_hash,
            "candidate_path": str(candidate_path.resolve()),
            "active_candidate": active_registry,
            "clock_attestation": clock_attestation,
            "incremental_plan": incremental_plan,
            "blockers": list(incremental_plan.get("blockers") or []),
            "ledger": ledger.summary(candidate_hash),
            "latest_observation_receipt": ledger.latest_observation_receipt(
                candidate_hash,
                ledger_audit=ledger_audit,
            ),
            "latest_observation_change": ledger.latest_observation_change(
                candidate_hash,
                ledger_audit=ledger_audit,
            ),
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        status_path = write_forward_status(report_dir, candidate_hash, payload)
        payload["status_artifact"] = str(status_path.resolve())
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 9

    def finish(status: str, records: list[dict[str, Any]]) -> int:
        audit = ledger.audit(candidate_hash)
        latest_observation_receipt = ledger.latest_observation_receipt(
            candidate_hash,
            ledger_audit=audit,
        )
        latest_observation_change = ledger.latest_observation_change(
            candidate_hash,
            ledger_audit=audit,
        )
        readiness = build_forward_readiness(
            candidate=candidate,
            candidate_verification=verification,
            ledger_audit=audit,
            frozen_dataset_hash_matches=True,
            minimum_observations=minimum_observations,
            minimum_planned_rebalances=minimum_rebalances,
        )
        output_status = "FORWARD_VALIDATION_BLOCKED" if readiness["status"] == "BLOCK" else status
        payload = {
            "ok": readiness["status"] != "BLOCK",
            "status": output_status,
            "generated_at": server.now_ms(),
            "candidate_hash": candidate_hash,
            "scheduler_job_id": scheduler_job_id,
            "scheduler_previous_receipt_hash": scheduler_previous_receipt_hash,
            "candidate_path": str(candidate_path.resolve()),
            "active_candidate": active_registry,
            "clock_attestation": clock_attestation,
            "frozen_dataset_last": frozen_last,
            "current_dataset_last": prepared["manifest"].get("last"),
            "records": records,
            "latest_observation_receipt": latest_observation_receipt,
            "latest_observation_change": latest_observation_change,
            "incremental_plan": incremental_plan,
            "work_summary": {
                "mode": incremental_plan.get("mode"),
                "eligible_count": len(incremental_plan.get("eligible_dates") or []),
                "processing_count": len(incremental_plan.get("processing_dates") or []),
                "processed_count": len(records),
                "skipped_recorded_count": len(incremental_plan.get("skipped_recorded_dates") or []),
                "skipped_classified_count": len(incremental_plan.get("skipped_classified_dates") or []),
                "deferred_unrecorded_count": len(incremental_plan.get("deferred_unrecorded_dates") or []),
            },
            "readiness": readiness,
            "ledger": ledger.summary(candidate_hash),
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        status_path = write_forward_status(report_dir, candidate_hash, payload)
        payload["status_artifact"] = str(status_path.resolve())
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 7 if readiness["status"] == "BLOCK" else 0

    processing_dates = set(incremental_plan.get("processing_dates") or [])
    work_indexes = [index for index in new_indexes if str(dates[index]) in processing_dates]
    if not work_indexes:
        if args.replay_recorded:
            return finish("AUDIT_REPLAY_NOTHING_TO_REPLAY", [])
        if new_indexes:
            return finish("UP_TO_DATE_INCREMENTAL", [])
        return finish("WAITING_FOR_NEW_COMPLETED_BAR", [])

    records: list[dict[str, Any]] = []
    observed_at = int(clock_attestation.get("attested_now_ms") or 0)
    calendar_name = str(((prepared["manifest"].get("market_calendar") or {}).get("calendar_name") or ""))
    capture_contracts: dict[str, dict[str, Any]] = {}
    for index in new_indexes:
        prefix_date = str(dates[index])
        existing_observation = ledger.observation(candidate_hash, prefix_date)
        capture_contracts[prefix_date] = (
            dict(existing_observation.get("capture_contract") or {})
            if existing_observation
            else build_forward_capture_contract(
                calendar_name=calendar_name,
                signal_date=prefix_date,
                observed_at=observed_at,
                clock_attestation=clock_attestation,
                activation_registry=active_registry,
            )
        )
    active_indexes = [
        index for index in new_indexes
        if bool(capture_contracts[str(dates[index])].get("candidate_active_before_signal_close"))
    ]
    forward_evaluation_start_index = min(active_indexes) if active_indexes else -1
    forward_evaluation_start_date = (
        str(dates[forward_evaluation_start_index])
        if forward_evaluation_start_index >= 0 else ""
    )
    preactivation_completed_session_count = sum(
        index < forward_evaluation_start_index for index in new_indexes
    ) if forward_evaluation_start_index >= 0 else len(new_indexes)
    start_capture_contract = (
        capture_contracts.get(forward_evaluation_start_date) or {}
        if forward_evaluation_start_date else {}
    )
    for index in work_indexes:
        prefix_date = str(dates[index])
        existing_observation = ledger.observation(candidate_hash, prefix_date)
        if not existing_observation and prefix_date in classified_event_dates:
            records.append({
                "signal_date": prefix_date,
                "capture_status": "ALREADY_CLASSIFIED",
                "record_status": "IDEMPOTENT_EVENT_REPLAY",
            })
            continue
        capture_contract = dict(capture_contracts.get(prefix_date) or {})
        if prefix_date not in recorded_dates and capture_contract.get("status") != "PASS":
            if capture_contract.get("status") in {"PRE_ACTIVATION", "MISSED", "BLOCK"}:
                event_type = {
                    "PRE_ACTIVATION": "PRE_ACTIVATION_SKIPPED",
                    "MISSED": "MISSED_CAPTURE",
                    "BLOCK": "DATA_CONTRACT_BLOCK",
                }[str(capture_contract.get("status"))]
                event = ledger.record_capture_event({
                    "candidate_hash": candidate_hash,
                    "signal_date": prefix_date,
                    "event_type": event_type,
                    "reason": f"forward_capture_{str(capture_contract.get('status') or 'unknown').lower()}",
                    "observed_at": observed_at,
                    "dataset_hash": str(prepared["manifest"].get("data_hash") or ""),
                    "capture_contract": capture_contract,
                })
                records.append({
                    "signal_date": prefix_date,
                    "capture_status": capture_contract.get("status"),
                    "record_status": event.get("status"),
                    "event_type": event_type,
                })
            else:
                records.append({
                    "signal_date": prefix_date,
                    "capture_status": capture_contract.get("status"),
                    "record_status": "WAITING_FOR_SESSION_CLOSE",
                })
            continue
        prefix_raw = {
            symbol: slice_portfolio_payload_through_date(
                payload,
                prefix_date,
                attest_backtest_rows=server.attest_stock_backtest_rows,
                dataset_lineage_id=dataset_lineage_id,
            )
            for symbol, payload in aligned_payloads.items()
        }
        prefix_prepared = prepare_attested_portfolio_dataset(
            prefix_raw,
            benchmark_symbol=benchmark,
            minimum_rows=180,
            attest_backtest_rows=server.attest_stock_backtest_rows,
            dataset_lineage_id=dataset_lineage_id,
            universe_contract=settings["universe_contract"],
        )
        if prefix_prepared["status"] != "PASS":
            event = ledger.record_capture_event({
                "candidate_hash": candidate_hash,
                "signal_date": prefix_date,
                "event_type": "DATA_CONTRACT_BLOCK",
                "reason": "prefix_dataset_attestation_blocked",
                "observed_at": observed_at,
                "dataset_hash": str(prefix_prepared["manifest"].get("data_hash") or ""),
                "capture_contract": capture_contract,
            })
            records.append({
                "signal_date": prefix_date,
                "capture_status": capture_contract.get("status"),
                "record_status": event.get("status"),
                "event_type": "DATA_CONTRACT_BLOCK",
            })
            continue
        prefix_payloads = dict(prefix_prepared["payloads"])
        if forward_evaluation_start_index < 0 or index < forward_evaluation_start_index:
            records.append({
                "signal_date": prefix_date,
                "capture_status": capture_contract.get("status"),
                "record_status": "FORWARD_STATE_NOT_ACTIVE",
            })
            continue
        backtest = run_causal_relative_strength_backtest(
            payloads=prefix_payloads,
            evaluation_start_index=forward_evaluation_start_index,
            **settings,
        )
        correlation_matrix = build_correlation_matrix(prefix_payloads)
        risk_snapshot = build_shadow_portfolio_risk(
            candidate=candidate,
            backtest_report=backtest,
            correlation_matrix=correlation_matrix,
        )
        observation_observed_at = int(existing_observation.get("observed_at") or observed_at) if existing_observation else observed_at
        state_contract = build_forward_state_contract(
            candidate,
            backtest,
            capture_contract=capture_contract,
            evaluation_start_index=forward_evaluation_start_index,
            evaluation_start_date=forward_evaluation_start_date,
            preactivation_completed_session_count=preactivation_completed_session_count,
            start_capture_contract=start_capture_contract,
        )
        observation = build_shadow_observation(
            candidate,
            backtest,
            observed_at=observation_observed_at,
            risk_snapshot=risk_snapshot,
            capture_contract=capture_contract,
            forward_state_contract=state_contract,
        )
        result = ledger.record(observation)
        if result.get("status") in {"CONFLICT", "BLOCK"}:
            ledger.record_capture_event({
                "candidate_hash": candidate_hash,
                "signal_date": prefix_date,
                "event_type": "DECISION_REPLAY_CONFLICT" if result.get("status") == "CONFLICT" else "DATA_CONTRACT_BLOCK",
                "reason": str(result.get("reason") or result.get("status") or "shadow_record_blocked"),
                "observed_at": observed_at,
                "dataset_hash": str(observation.get("dataset_hash") or ""),
                "incoming_decision_hash": str(observation.get("decision_hash") or ""),
                "existing_decision_hash": str(result.get("existing_hash") or ""),
            })
        risk_record = (
            ledger.record_risk_reassessment(
                candidate_hash=candidate_hash,
                signal_date=str(observation.get("signal_date") or ""),
                risk_snapshot=risk_snapshot,
                observed_at=observed_at,
            )
            if result.get("ok") else {"status": "SKIPPED_MARKET_OBSERVATION_BLOCKED"}
        )
        records.append({
            "signal_date": observation.get("signal_date"),
            "target_symbols": observation.get("target_symbols"),
            "target_allocation_pct": observation.get("target_allocation_pct"),
            "reason": observation.get("reason"),
            "decision_hash": observation.get("decision_hash"),
            "risk_gate_status": observation.get("risk_gate_status"),
            "risk_snapshot_hash": risk_snapshot.get("risk_snapshot_hash"),
            "capture_status": observation.get("capture_status"),
            "record_status": result.get("status"),
            "risk_record_status": risk_record.get("status"),
        })
    return finish("FORWARD_OBSERVATIONS_UPDATED", records)


if __name__ == "__main__":
    raise SystemExit(main())
