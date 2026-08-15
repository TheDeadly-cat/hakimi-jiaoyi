from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from exchange_terminal import server
from exchange_terminal.services.forward_artifact_io import (
    MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
    read_forward_json_artifact,
    windows_safe_artifact_basename,
)
from exchange_terminal.services.portfolio_backtest import (
    prepare_attested_portfolio_dataset,
    prepare_portfolio_dataset,
    slice_portfolio_payload_through_date,
)
from exchange_terminal.services.portfolio_backtest_pack import (
    MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
    MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES,
    verify_statistical_audit_artifact,
)
from exchange_terminal.services.portfolio_forward import load_active_portfolio_candidate
from exchange_terminal.services.portfolio_forward_performance import (
    PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
    PortfolioForwardPerformanceLedger,
    build_forward_performance_readiness,
    build_forward_performance_settlement,
)
from exchange_terminal.services.portfolio_forward_statistical_audit import (
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
    audit_forward_portfolio_statistics,
    audit_forward_portfolio_statistics_v2,
    verify_forward_portfolio_statistical_audit_semantics,
    verify_forward_portfolio_statistical_audit_v2_semantics,
)
from exchange_terminal.services.portfolio_forward_scheduler import ForwardSchedulerLock
from exchange_terminal.services.portfolio_shadow import PortfolioShadowLedger
from exchange_terminal.services.trusted_clock import attest_utc_clock


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = Path(os.environ.get("HAKIMI_RUNTIME_DIR") or PROJECT_ROOT / "runtime")
REPORT_DIR = RUNTIME_DIR / "reports"
DEFAULT_PERFORMANCE_LEDGER = "portfolio_forward_performance.sqlite"
DEFAULT_SHADOW_LEDGER = "portfolio_shadow.sqlite"
DEFAULT_STATUS_PREFIX = "portfolio_forward_performance_status"
DEFAULT_LOCK_FILE = "portfolio_forward_performance.lock"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_forward_statistical_status(
    *,
    candidate: dict[str, Any],
    settlements: list[dict[str, Any]],
    historical_statistical_audit: dict[str, Any],
    shadow_audit: dict[str, Any],
    performance_summary: dict[str, Any],
    generated_at: int,
    audit_schema_version: str,
    readiness_schema_version: str,
) -> dict[str, Any]:
    """Build one explicitly versioned audit/readiness pair without I/O."""

    version_pair = (str(audit_schema_version or ""), str(readiness_schema_version or ""))
    if version_pair == (
        PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
        PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    ):
        audit_builder = audit_forward_portfolio_statistics
        audit_verifier = verify_forward_portfolio_statistical_audit_semantics
    elif version_pair == (
        PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
        PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
    ):
        audit_builder = audit_forward_portfolio_statistics_v2
        audit_verifier = verify_forward_portfolio_statistical_audit_v2_semantics
    else:
        raise ValueError(
            "unsupported_forward_statistical_version_pair:"
            f"{version_pair[0]}+{version_pair[1]}"
        )

    report = audit_builder(
        candidate=dict(candidate or {}),
        settlements=[dict(item or {}) for item in settlements or []],
        historical_statistical_audit=dict(historical_statistical_audit or {}),
        generated_at=int(generated_at),
    )
    verification = audit_verifier(
        report,
        candidate=dict(candidate or {}),
        settlements=[dict(item or {}) for item in settlements or []],
        historical_statistical_audit=dict(historical_statistical_audit or {}),
    )
    forward_audit = {
        **report,
        "verification_status": str(verification.get("status") or "BLOCK"),
        "verification_blockers": list(verification.get("blockers") or []),
        "semantic_recomputed": bool(
            verification.get("recomputed_from_verified_forward_settlements")
        ),
    }
    readiness = build_forward_performance_readiness(
        candidate=dict(candidate or {}),
        shadow_audit=dict(shadow_audit or {}),
        performance_summary=dict(performance_summary or {}),
        historical_statistical_audit=dict(historical_statistical_audit or {}),
        forward_statistical_audit=forward_audit,
        readiness_schema_version=readiness_schema_version,
    )
    return {
        "audit_schema_version": version_pair[0],
        "readiness_schema_version": version_pair[1],
        "forward_statistical_audit": forward_audit,
        "readiness": readiness,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_first_joint_maturity_statistical_status_preview(
    *,
    candidate: dict[str, Any],
    settlements: list[dict[str, Any]],
    historical_statistical_audit: dict[str, Any],
    shadow_audit: dict[str, Any],
    performance_summary: dict[str, Any],
    generated_at: int,
) -> dict[str, Any]:
    """Pure audit-v2/readiness-v3 builder; never writes status."""

    return build_forward_statistical_status(
        candidate=candidate,
        settlements=settlements,
        historical_statistical_audit=historical_statistical_audit,
        shadow_audit=shadow_audit,
        performance_summary=performance_summary,
        generated_at=generated_at,
        audit_schema_version=PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
        readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
    )


def build_legacy_full_series_statistical_status(
    *,
    candidate: dict[str, Any],
    settlements: list[dict[str, Any]],
    historical_statistical_audit: dict[str, Any],
    shadow_audit: dict[str, Any],
    performance_summary: dict[str, Any],
    generated_at: int,
) -> dict[str, Any]:
    """Explicit historical audit-v1/readiness-v2 compatibility builder."""

    return build_forward_statistical_status(
        candidate=candidate,
        settlements=settlements,
        historical_statistical_audit=historical_statistical_audit,
        shadow_audit=shadow_audit,
        performance_summary=performance_summary,
        generated_at=generated_at,
        audit_schema_version=PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
        readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    )


def _read_json(
    path: Path,
    *,
    byte_limit: int = MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
    size_limit_blocker: str = "portfolio_forward_performance_artifact_size_limit_exceeded",
) -> dict[str, Any]:
    """Read one strict, bounded JSON object without publishing its local path."""

    try:
        artifact = read_forward_json_artifact(
            path,
            byte_limit=byte_limit,
            size_limit_blocker=size_limit_blocker,
        )
    except (MemoryError, OSError, RecursionError, UnicodeError, ValueError):
        raise ValueError("portfolio_forward_performance_artifact_unreadable") from None
    if artifact.status != "PASS":
        raise ValueError(
            artifact.blocker or "portfolio_forward_performance_artifact_unreadable"
        )
    return dict(artifact.payload)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return path


def _emit(payload: dict[str, Any]) -> None:
    try:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print(json.dumps(payload, ensure_ascii=True, indent=2))


def _payload_metadata(
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
    return {
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


def _compact_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": str(manifest.get("status") or "UNKNOWN"),
        "blockers": list(manifest.get("blockers") or []),
        "warnings": list(manifest.get("warnings") or []),
        "row_count": int(manifest.get("row_count") or 0),
        "first": str(manifest.get("first") or ""),
        "last": str(manifest.get("last") or ""),
        "data_hash": str(manifest.get("data_hash") or ""),
        "manifest_hash": str(manifest.get("manifest_hash") or ""),
    }


def _active_research_report(
    report_dir: Path,
    active: dict[str, Any],
) -> tuple[Path, dict[str, Any], str]:
    registry = dict(active.get("registry") or {})
    candidate = dict(active.get("candidate") or {})
    receipt = dict(registry.get("experiment_completion_receipt") or {})
    report_file = str(receipt.get("report_file") or "")
    if windows_safe_artifact_basename(report_file) is None:
        raise ValueError("Active research report filename is invalid.")
    directory = Path(report_dir).resolve()
    path = directory / report_file
    if path.parent != directory:
        raise ValueError("Active research report path escapes the report directory.")
    try:
        artifact = read_forward_json_artifact(
            path,
            byte_limit=MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
            size_limit_blocker="active_research_report_size_limit_exceeded",
        )
    except (MemoryError, OSError, RecursionError, UnicodeError, ValueError):
        raise ValueError("Active research report is unavailable.") from None
    read_completed = artifact.status == "PASS" or artifact.blocker.startswith(
        "strict_json_"
    )
    if not read_completed:
        raise ValueError(
            f"Active research report is unavailable: "
            f"{artifact.blocker or 'artifact_unreadable'}."
        )
    file_hash = hashlib.sha256(artifact.raw).hexdigest()
    if file_hash != str(receipt.get("report_file_sha256") or ""):
        raise ValueError("Active research report file hash does not match its completion receipt.")
    if artifact.status != "PASS":
        if artifact.blocker == "strict_json_object_required":
            raise ValueError("Active research report must be a JSON object.")
        if artifact.blocker == "strict_json_utf8_invalid":
            raise ValueError("Active research report UTF-8 is invalid.")
        raise ValueError("Active research report JSON is invalid.")
    payload = dict(artifact.payload)
    if not isinstance(payload, dict):
        raise ValueError("Active research report must be a JSON object.")
    batch_hash = str(payload.get("batch_run_hash") or "")
    if batch_hash != str(receipt.get("batch_run_hash") or ""):
        raise ValueError("Active research report batch hash does not match its completion receipt.")
    if batch_hash != str(candidate.get("research_report_hash") or ""):
        raise ValueError("Active research report batch hash does not match the frozen candidate.")
    if str((payload.get("frozen_candidate") or {}).get("candidate_hash") or "") != str(
        candidate.get("candidate_hash") or ""
    ):
        raise ValueError("Active research report candidate hash does not match the frozen candidate.")
    return path, payload, file_hash


def _historical_statistical_audit(
    report_dir: Path,
    candidate_hash: str,
    *,
    research_report: dict[str, Any],
    research_file_sha256: str,
) -> dict[str, Any]:
    valid_matches: list[tuple[int, Path, dict[str, Any], dict[str, Any]]] = []
    rejected_matches: list[tuple[int, Path, dict[str, Any], dict[str, Any]]] = []
    research_batch_run_hash = str(research_report.get("batch_run_hash") or "")
    directory = Path(report_dir).resolve()
    for path in directory.glob("portfolio_statistical_audit_*.json"):
        if windows_safe_artifact_basename(path.name) is None:
            continue
        try:
            payload = _read_json(
                path,
                byte_limit=MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES,
                size_limit_blocker="portfolio_statistical_audit_size_limit_exceeded",
            )
        except ValueError:
            continue
        if str(payload.get("active_candidate_hash") or "") != candidate_hash:
            continue
        verification = verify_statistical_audit_artifact(
            payload,
            candidate_hash=candidate_hash,
            research_batch_run_hash=research_batch_run_hash,
            research_file_sha256=research_file_sha256,
            research_report=research_report,
        )
        record = (int(payload.get("generated_at") or 0), path, payload, verification)
        if verification.get("status") == "PASS":
            valid_matches.append(record)
        else:
            rejected_matches.append(record)
    if valid_matches:
        _, path, payload, verification = max(
            valid_matches,
            key=lambda item: (item[0], item[1].name),
        )
        return {
            **payload,
            "artifact_file": path.name,
            "verification_status": "PASS",
            "verification_blockers": [],
            "semantic_recomputed": bool(
                (verification.get("semantic_verification") or {}).get(
                    "recomputed_from_frozen_research"
                )
            ),
        }
    if rejected_matches:
        _, path, payload, verification = max(
            rejected_matches,
            key=lambda item: (item[0], item[1].name),
        )
        return {
            "status": "BLOCK",
            "claim_status": str(payload.get("status") or "BLOCK"),
            "conclusion": "HISTORICAL_STATISTICAL_AUDIT_VERIFICATION_BLOCKED",
            "audit_hash": str(payload.get("audit_hash") or ""),
            "artifact_hash": str(payload.get("artifact_hash") or ""),
            "artifact_file": path.name,
            "verification_status": "BLOCK",
            "verification_blockers": list(verification.get("blockers") or []),
            "semantic_recomputed": True,
        }
    else:
        return {
            "status": "MISSING",
            "conclusion": "HISTORICAL_STATISTICAL_AUDIT_MISSING",
            "audit_hash": "",
            "artifact_hash": "",
            "verification_status": "BLOCK",
            "verification_blockers": ["statistical_audit_missing"],
            "semantic_recomputed": False,
        }


def _load_observations(ledger: PortfolioShadowLedger, candidate_hash: str) -> dict[str, dict[str, Any]]:
    return {
        signal_date: dict(ledger.observation(candidate_hash, signal_date) or {})
        for signal_date in ledger.observation_dates(candidate_hash)
    }


def _prepare_current_dataset(
    candidate: dict[str, Any],
    *,
    requested_limit: int,
) -> dict[str, Any]:
    spec = dict(candidate.get("spec") or {})
    dataset_lineage_id = str(spec.get("experiment_id") or candidate.get("candidate_hash") or "").strip()
    benchmark = str(spec.get("benchmark_symbol") or "SPY").upper()
    tradables = [
        str(symbol).upper()
        for symbol in spec.get("tradable_symbols") or []
        if str(symbol).upper() != benchmark
    ]
    symbols = [benchmark, *tradables]
    universe_contract = dict(
        (candidate.get("research_governance") or {}).get("universe_contract") or {}
    )
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
        universe_contract=universe_contract,
    )
    if prepared.get("status") != "PASS":
        return prepared
    candidate_first = str(candidate.get("dataset_first") or "")
    if not candidate_first or str(dict(prepared.get("manifest") or {}).get("first") or "") > candidate_first:
        result = dict(prepared)
        result["status"] = "BLOCK"
        result["manifest"] = {
            **dict(prepared.get("manifest") or {}),
            "status": "BLOCK",
            "blockers": ["candidate_history_start_is_not_covered"],
        }
        return result
    continuation_payloads = {
        symbol: _payload_metadata(
            dict(prepared.get("payloads", {}).get(symbol) or {}),
            rows=[
                dict(row) for row in prepared.get("rows", {}).get(symbol) or []
                if str(row.get("date") or "") >= candidate_first
            ],
            adjustment_evidence=dict(
                dict(prepared.get("manifest", {})).get("adjustment_evidence", {}).get(symbol) or {}
            ),
        )
        for symbol in dict(prepared.get("manifest") or {}).get("symbols") or []
    }
    prepared = prepare_attested_portfolio_dataset(
        continuation_payloads,
        benchmark_symbol=benchmark,
        minimum_rows=180,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
        universe_contract=universe_contract,
    )
    if prepared.get("status") != "PASS":
        return prepared
    candidate_last = str(candidate.get("dataset_last") or "")
    frozen_payloads = {
        symbol: slice_portfolio_payload_through_date(
            dict(payload),
            candidate_last,
            attest_backtest_rows=server.attest_stock_backtest_rows,
            dataset_lineage_id=dataset_lineage_id,
        )
        for symbol, payload in dict(prepared.get("payloads") or {}).items()
    }
    frozen = prepare_attested_portfolio_dataset(
        frozen_payloads,
        benchmark_symbol=benchmark,
        minimum_rows=180,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
        universe_contract=universe_contract,
    )
    if (
        frozen.get("status") != "PASS"
        or str(dict(frozen.get("manifest") or {}).get("data_hash") or "")
        != str(candidate.get("dataset_hash") or "")
    ):
        result = dict(prepared)
        result["status"] = "BLOCK"
        result["manifest"] = {
            **dict(prepared.get("manifest") or {}),
            "status": "BLOCK",
            "blockers": ["frozen_dataset_hash_mismatch"],
            "candidate_dataset_hash": str(candidate.get("dataset_hash") or ""),
            "current_frozen_dataset_hash": str(dict(frozen.get("manifest") or {}).get("data_hash") or ""),
        }
        return result
    return prepared


def _prefix_dataset(
    prepared: dict[str, Any],
    *,
    benchmark: str,
    index: int,
    signal_date: str,
    universe_contract: dict[str, Any],
) -> dict[str, Any]:
    prefix_payloads = {
        symbol: _payload_metadata(
            dict(payload),
            rows=list(payload.get("rows") or [])[:index + 1],
            cutoff=signal_date,
        )
        for symbol, payload in dict(prepared.get("payloads") or {}).items()
    }
    return prepare_portfolio_dataset(
        prefix_payloads,
        benchmark_symbol=benchmark,
        minimum_rows=180,
        universe_contract=universe_contract,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Settle the captured portfolio candidate into a research-only forward performance ledger."
    )
    parser.add_argument("--scheduled", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--shadow-ledger", type=Path)
    parser.add_argument("--clock-timeout", type=float, default=2.5)
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lock = ForwardSchedulerLock(RUNTIME_DIR / DEFAULT_LOCK_FILE, now_ms=lambda: time.time_ns() // 1_000_000)
    lock_result = lock.acquire()
    if not lock_result.get("ok"):
        payload = {
            "ok": lock_result.get("status") == "BUSY",
            "status": f"PERFORMANCE_{lock_result.get('status') or 'LOCK_BLOCK'}",
            "lock": lock_result,
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        _emit(payload)
        return 0 if payload["ok"] else 2

    try:
        active = load_active_portfolio_candidate(REPORT_DIR)
        if active.get("status") != "PASS":
            payload = {
                "ok": False,
                "status": "ACTIVE_CANDIDATE_BLOCKED",
                "blockers": list(active.get("blockers") or []),
                "observation_only": True,
                "simulation_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            _emit(payload)
            return 3
        candidate = dict(active.get("candidate") or {})
        candidate_hash = str(candidate.get("candidate_hash") or "")
        spec = dict(candidate.get("spec") or {})
        benchmark = str(spec.get("benchmark_symbol") or "SPY").upper()
        shadow_path = args.shadow_ledger.resolve() if args.shadow_ledger else RUNTIME_DIR / DEFAULT_SHADOW_LEDGER
        performance_path = args.ledger.resolve() if args.ledger else RUNTIME_DIR / DEFAULT_PERFORMANCE_LEDGER
        shadow = PortfolioShadowLedger(shadow_path)
        performance = PortfolioForwardPerformanceLedger(performance_path)
        observations = _load_observations(shadow, candidate_hash)
        shadow_audit = shadow.audit(candidate_hash)
        _, research_report, research_file_sha256 = _active_research_report(REPORT_DIR, active)
        statistical_audit = _historical_statistical_audit(
            REPORT_DIR,
            candidate_hash,
            research_report=research_report,
            research_file_sha256=research_file_sha256,
        )
        recorded_dates = set(performance.settlement_dates(candidate_hash))
        unsettled_dates = sorted(set(observations) - recorded_dates)
        records: list[dict[str, Any]] = []
        dataset_manifest: dict[str, Any] = {}

        if unsettled_dates:
            clock = attest_utc_clock(timeout_seconds=max(float(args.clock_timeout), 0.1))
            if clock.get("status") != "PASS":
                payload = {
                    "ok": False,
                    "status": "CLOCK_ATTESTATION_BLOCKED",
                    "candidate_hash": candidate_hash,
                    "blockers": list(clock.get("blockers") or []),
                    "clock_attestation": clock,
                    "observation_only": True,
                    "simulation_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
                _emit(payload)
                return 4
            requested_limit = (
                int(args.limit)
                if int(args.limit) > 0
                else max(
                    int(candidate.get("dataset_row_count") or 0)
                    + int(spec.get("minimum_forward_observations") or 60)
                    + 10,
                    180,
                )
            )
            prepared = _prepare_current_dataset(candidate, requested_limit=requested_limit)
            dataset_manifest = dict(prepared.get("manifest") or {})
            if prepared.get("status") != "PASS":
                payload = {
                    "ok": False,
                    "status": "CURRENT_DATASET_BLOCKED",
                    "candidate_hash": candidate_hash,
                    "dataset_manifest": _compact_manifest(dataset_manifest),
                    "observation_only": True,
                    "simulation_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
                _emit(payload)
                return 5
            dates = [str(item) for item in prepared.get("dates") or []]
            date_indexes = {session_date: index for index, session_date in enumerate(dates)}
            for settlement_date in unsettled_dates:
                if settlement_date not in date_indexes:
                    records.append({
                        "settlement_date": settlement_date,
                        "status": "BLOCK",
                        "reason": "captured_observation_date_missing_from_current_dataset",
                    })
                    break
                index = date_indexes[settlement_date]
                prefix = _prefix_dataset(
                    prepared,
                    benchmark=benchmark,
                    index=index,
                    signal_date=settlement_date,
                    universe_contract=dict(
                        (candidate.get("research_governance") or {}).get("universe_contract") or {}
                    ),
                )
                observation = observations[settlement_date]
                if (
                    prefix.get("status") != "PASS"
                    or str(dict(prefix.get("manifest") or {}).get("data_hash") or "")
                    != str(observation.get("dataset_hash") or "")
                ):
                    records.append({
                        "settlement_date": settlement_date,
                        "status": "BLOCK",
                        "reason": "captured_observation_dataset_cannot_be_reproduced",
                        "captured_dataset_hash": str(observation.get("dataset_hash") or ""),
                        "current_prefix_dataset_hash": str(dict(prefix.get("manifest") or {}).get("data_hash") or ""),
                    })
                    break
                latest = performance.latest(candidate_hash)
                if latest:
                    previous_session_date = dates[index - 1] if index > 0 else ""
                    previous_observation = observations.get(previous_session_date)
                    if (
                        str(latest.get("settlement_date") or "") != previous_session_date
                        or not previous_observation
                    ):
                        records.append({
                            "settlement_date": settlement_date,
                            "status": "BLOCK",
                            "reason": "forward_observation_or_market_session_chain_gap",
                            "expected_previous_session_date": previous_session_date,
                            "latest_settlement_date": str(latest.get("settlement_date") or ""),
                        })
                        break
                else:
                    previous_session_date = ""
                    previous_observation = None
                settlement = build_forward_performance_settlement(
                    candidate=candidate,
                    current_observation=observation,
                    dataset_manifest=dict(prefix.get("manifest") or {}),
                    market_rows={
                        symbol: dict(rows[index])
                        for symbol, rows in dict(prepared.get("rows") or {}).items()
                    },
                    recorded_at=int(clock.get("attested_now_ms") or 0),
                    previous_settlement=latest,
                    previous_observation=previous_observation,
                    previous_session_date=previous_session_date,
                )
                if settlement.get("status") != "READY":
                    records.append({
                        "settlement_date": settlement_date,
                        "status": "BLOCK",
                        "reason": "settlement_build_blocked",
                        "blockers": list(settlement.get("blockers") or []),
                    })
                    break
                result = performance.record(settlement)
                records.append({
                    "settlement_date": settlement_date,
                    "status": str(result.get("status") or ""),
                    "settlement_hash": str(settlement.get("settlement_hash") or ""),
                    "strategy_equity": dict(settlement.get("strategy") or {}).get("equity"),
                    "benchmark_equity": dict(settlement.get("benchmark") or {}).get("equity"),
                    "order_count": len(dict(settlement.get("strategy") or {}).get("orders") or []),
                })
                if not result.get("ok"):
                    break

        summary = performance.summary(candidate_hash, observations=observations)
        settlements = performance.settlements(candidate_hash)
        forward_statistical_status = build_forward_statistical_status(
            candidate=candidate,
            settlements=settlements,
            historical_statistical_audit=statistical_audit,
            shadow_audit=shadow_audit,
            performance_summary=summary,
            generated_at=int(time.time_ns() // 1_000_000),
            audit_schema_version=PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        )
        forward_statistical_audit = dict(
            forward_statistical_status.get("forward_statistical_audit") or {}
        )
        readiness = dict(forward_statistical_status.get("readiness") or {})
        record_blocked = any(item.get("status") in {"BLOCK", "CONFLICT"} for item in records)
        status = "PERFORMANCE_SETTLEMENT_BLOCKED" if record_blocked else str(readiness.get("status") or "COLLECTING")
        payload = {
            "ok": not record_blocked and summary.get("status") == "PASS",
            "status": status,
            "generated_at": int(time.time_ns() // 1_000_000),
            "candidate_hash": candidate_hash,
            "candidate_file": Path(str(active.get("candidate_path") or "")).name,
            "scheduled_invocation": bool(args.scheduled),
            "records": records,
            "dataset_manifest": _compact_manifest(dataset_manifest) if dataset_manifest else {},
            "shadow_audit": shadow_audit,
            "shadow_audit_hash": _canonical_hash(shadow_audit),
            "performance": summary,
            "readiness": readiness,
            "historical_statistical_audit": {
                "status": str(statistical_audit.get("status") or "MISSING"),
                "conclusion": str(statistical_audit.get("conclusion") or ""),
                "audit_hash": str(statistical_audit.get("audit_hash") or ""),
                "artifact_hash": str(statistical_audit.get("artifact_hash") or ""),
                "artifact_file": str(statistical_audit.get("artifact_file") or ""),
                "verification_status": str(statistical_audit.get("verification_status") or "BLOCK"),
                "verification_blockers": list(statistical_audit.get("verification_blockers") or []),
                "semantic_recomputed": bool(statistical_audit.get("semantic_recomputed")),
            },
            "forward_statistical_audit": forward_statistical_audit,
            "ledger_path": str(performance_path.resolve()),
            "shadow_ledger_path": str(shadow_path.resolve()),
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        status_path = REPORT_DIR / f"{DEFAULT_STATUS_PREFIX}_{candidate_hash[:12] or 'unknown'}.json"
        _write_json_atomic(status_path, payload)
        payload["status_artifact"] = str(status_path.resolve())
        _emit(payload)
        return 0 if payload["ok"] else 6
    except Exception as exc:
        payload = {
            "ok": False,
            "status": "PERFORMANCE_UNHANDLED_ERROR",
            "error": str(exc)[:500],
            "error_type": type(exc).__name__,
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        _emit(payload)
        return 7
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
