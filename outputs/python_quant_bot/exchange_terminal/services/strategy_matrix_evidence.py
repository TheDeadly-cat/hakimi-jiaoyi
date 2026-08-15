from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .backtest_engine import prepare_backtest_dataset
from .market_history_store import build_history_dataset_evidence
from .strategy_matrix_protocol import (
    verify_strategy_matrix_claim,
    verify_strategy_matrix_completion,
    verify_strategy_matrix_protocol,
)

MATRIX_EVIDENCE_VERSION = "strategy-matrix-evidence-v2"
MATRIX_REPORT_SCHEMA_VERSION = 7
MATRIX_BENCHMARK_SCHEMA_VERSION = "strategy-benchmark-v7"
MATRIX_RESULT_HASH_VERSION = "strategy-matrix-result-hash-v1"
MATRIX_RUN_HASH_VERSION = "strategy-matrix-run-hash-v4"
MATRIX_RESEARCH_GOVERNANCE_VERSION = "strategy-matrix-governance-v2"


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sequence(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def strategy_matrix_result_hash(report: dict[str, Any] | Any) -> str:
    clean_report = _mapping(report)
    bound_fields = (
        "created_at",
        "batch_spec_hash",
        "dataset_manifest_hash",
        "dataset_snapshot",
        "selection_alignment",
        "selection_calendar_schedule",
        "selection_regime_evidence",
        "selection_correlation_matrix",
        "selection_cells",
        "selection_rankings",
        "confirmation_candidates",
        "confirmation_alignment",
        "confirmation_calendar_schedule",
        "confirmation_regime_evidence",
        "confirmation_cells",
        "confirmations",
        "forward_candidates",
        "summary",
    )
    return canonical_hash({
        "version": MATRIX_RESULT_HASH_VERSION,
        **{field: clean_report.get(field) for field in bound_fields},
    })


def strategy_matrix_run_hash(report: dict[str, Any] | Any) -> str:
    clean_report = _mapping(report)
    research_governance = _mapping(clean_report.get("research_governance"))
    return canonical_hash({
        "version": MATRIX_RUN_HASH_VERSION,
        "result_hash": str(clean_report.get("matrix_result_hash") or ""),
        "research_governance_hash": str(research_governance.get("governance_hash") or ""),
    })


def _embedded_hash_matches(payload: Any, field: str) -> bool:
    if not isinstance(payload, dict):
        return False
    expected = str(payload.get(field) or "")
    if not expected:
        return False
    canonical_payload = {key: value for key, value in payload.items() if key != field}
    return canonical_hash(canonical_payload) == expected


def _created_at_ms(value: Any) -> int:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    except (TypeError, ValueError):
        return 0


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def verify_matrix_research_governance(
    governance: Any,
    *,
    report_created_at_ms: int,
    batch_spec_hash: str = "",
    result_hash: str = "",
    dataset_manifest_hash: str = "",
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = _mapping(governance)
    if not isinstance(governance, dict):
        blockers.append("matrix_research_governance_type_invalid")
    clean = dict(payload)
    expected_hash = str(clean.pop("governance_hash", "") or "")
    if payload.get("schema_version") != MATRIX_RESEARCH_GOVERNANCE_VERSION:
        blockers.append("matrix_research_governance_schema_invalid")
    if not expected_hash or canonical_hash(clean) != expected_hash:
        blockers.append("matrix_research_governance_hash_invalid")
    if payload.get("status") != "PREREGISTERED_BLIND_SINGLE_USE_COMPLETE":
        blockers.append("matrix_not_preregistered_blind_single_use")
    if payload.get("selection_test_policy") != "BLIND_ONCE":
        blockers.append("matrix_selection_test_policy_invalid")
    if payload.get("development_only") is not False or payload.get("single_use_claim") is not True:
        blockers.append("matrix_single_use_claim_invalid")
    if not str(payload.get("registration_id") or ""):
        blockers.append("matrix_registration_id_missing")
    if not _valid_sha256(payload.get("protocol_hash")):
        blockers.append("matrix_protocol_hash_invalid")
    protocol = _mapping(payload.get("protocol"))
    claim = _mapping(payload.get("single_use_claim_receipt"))
    completion = _mapping(payload.get("completion_receipt"))
    protocol_verification = verify_strategy_matrix_protocol(
        protocol,
        verify_current_implementation=False,
    )
    claim_verification = verify_strategy_matrix_claim(claim, protocol=protocol)
    completion_verification = verify_strategy_matrix_completion(
        completion,
        protocol=protocol,
        claim=claim,
    )
    if protocol_verification.get("status") != "PASS":
        blockers.extend(
            f"matrix_governance_protocol:{item}"
            for item in protocol_verification.get("blockers") or []
        )
    if claim_verification.get("status") != "PASS":
        blockers.extend(
            f"matrix_governance_claim:{item}"
            for item in claim_verification.get("blockers") or []
        )
    if completion_verification.get("status") != "PASS":
        blockers.extend(
            f"matrix_governance_completion:{item}"
            for item in completion_verification.get("blockers") or []
        )
    if str(payload.get("registration_id") or "") != str(protocol.get("registration_id") or ""):
        blockers.append("matrix_governance_registration_mismatch")
    if str(payload.get("protocol_hash") or "") != str(protocol.get("protocol_hash") or ""):
        blockers.append("matrix_governance_protocol_hash_mismatch")
    if str(payload.get("claim_hash") or "") != str(claim.get("claim_hash") or ""):
        blockers.append("matrix_governance_claim_hash_mismatch")
    if str(payload.get("completion_hash") or "") != str(completion.get("completion_hash") or ""):
        blockers.append("matrix_governance_completion_hash_mismatch")
    if batch_spec_hash and str(protocol.get("batch_spec_hash") or "") != batch_spec_hash:
        blockers.append("matrix_governance_batch_spec_mismatch")
    if result_hash and str(completion.get("result_hash") or "") != result_hash:
        blockers.append("matrix_governance_result_hash_mismatch")
    if dataset_manifest_hash and str(completion.get("dataset_manifest_hash") or "") != dataset_manifest_hash:
        blockers.append("matrix_governance_dataset_hash_mismatch")
    registered_at_ms = payload.get("registered_at_ms")
    started_at_ms = payload.get("started_at_ms")
    completed_at_ms = payload.get("completed_at_ms")
    timestamps = (registered_at_ms, started_at_ms, completed_at_ms)
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in timestamps):
        blockers.append("matrix_governance_timestamp_invalid")
    elif not (registered_at_ms <= started_at_ms <= completed_at_ms <= report_created_at_ms + 5_000):
        blockers.append("matrix_governance_temporal_order_invalid")
    if (
        registered_at_ms != protocol.get("registered_at_ms")
        or started_at_ms != claim.get("started_at_ms")
        or completed_at_ms != completion.get("completed_at_ms")
    ):
        blockers.append("matrix_governance_receipt_timestamp_mismatch")
    exposure = _mapping(payload.get("holdout_exposure_audit"))
    if not _embedded_hash_matches(exposure, "audit_hash"):
        blockers.append("matrix_holdout_exposure_audit_hash_invalid")
    if (
        exposure.get("status") != "PASS"
        or exposure.get("evaluated_before_data_load") is not True
        or _sequence(exposure.get("exposed_symbols"))
    ):
        blockers.append("matrix_holdout_was_not_blind")
    claim_exposure = _mapping(claim.get("holdout_exposure_audit"))
    if str(exposure.get("audit_hash") or "") != str(claim_exposure.get("audit_hash") or ""):
        blockers.append("matrix_governance_exposure_receipt_mismatch")
    if (
        payload.get("research_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("matrix_research_governance_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "governance_hash": expected_hash,
        "protocol_hash": str(protocol.get("protocol_hash") or ""),
        "claim_hash": str(claim.get("claim_hash") or ""),
        "completion_hash": str(completion.get("completion_hash") or ""),
        "protocol_verification": protocol_verification,
        "claim_verification": claim_verification,
        "completion_verification": completion_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_strategy_matrix_evidence(
    report: dict[str, Any] | Any,
    *,
    strategy_id: str,
    strategy_params: dict[str, Any],
    implementation_fingerprint: str,
    risk: dict[str, Any],
    symbol: str,
    now_ms: int,
    max_age_ms: int = 7 * 24 * 60 * 60 * 1000,
    _report_only: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(report, dict):
        blockers.append("matrix_report_type_invalid")
    report = _mapping(report)
    required_types = {
        "batch_spec": dict,
        "dataset_manifest": list,
        "dataset_snapshot": dict,
        "selection_cells": list,
        "confirmation_cells": list,
        "selection_rankings": list,
        "confirmation_candidates": list,
        "confirmations": list,
        "forward_candidates": list,
        "selection_alignment": dict,
        "selection_calendar_schedule": dict,
        "selection_regime_evidence": dict,
        "selection_correlation_matrix": dict,
        "confirmation_alignment": dict,
        "confirmation_calendar_schedule": dict,
        "confirmation_regime_evidence": dict,
        "summary": dict,
        "research_governance": dict,
    }
    for field, expected_type in required_types.items():
        if not isinstance(report.get(field), expected_type):
            blockers.append(f"matrix_field_type_invalid:{field}")
    batch_spec = _mapping(report.get("batch_spec"))
    if report.get("schema_version") != MATRIX_REPORT_SCHEMA_VERSION:
        blockers.append("matrix_report_schema_mismatch")
    if batch_spec.get("schema_version") != MATRIX_BENCHMARK_SCHEMA_VERSION:
        blockers.append("matrix_benchmark_schema_mismatch")
    data_policy = _mapping(batch_spec.get("data_policy"))
    if (
        data_policy.get("timeframe") != "1D"
        or data_policy.get("completed_candles_only") is not True
        or data_policy.get("alignment_schema_version") != "daily-batch-alignment-v2"
        or data_policy.get("max_endpoint_skew_days") != 3
        or data_policy.get("max_boundary_skew_days") != 7
        or data_policy.get("frozen_stock_revision_evidence_required") is not True
        or data_policy.get("frozen_crypto_history_evidence_required") is not True
        or data_policy.get("exact_dataset_snapshot_required") is not True
    ):
        blockers.append("matrix_dataset_policy_not_frozen")
    dataset_manifest = _sequence(report.get("dataset_manifest"))
    expected_batch_hash = canonical_hash(batch_spec)
    expected_dataset_hash = canonical_hash(dataset_manifest)
    expected_result_hash = strategy_matrix_result_hash(report)
    expected_run_hash = strategy_matrix_run_hash(report)
    if str(report.get("batch_spec_hash") or "") != expected_batch_hash:
        blockers.append("batch_spec_hash_mismatch")
    if str(report.get("dataset_manifest_hash") or "") != expected_dataset_hash:
        blockers.append("dataset_manifest_hash_mismatch")
    snapshot = _mapping(report.get("dataset_snapshot"))
    if snapshot.get("schema_version") != "strategy-matrix-dataset-snapshot-v1":
        blockers.append("matrix_dataset_snapshot_schema_invalid")
    if not _embedded_hash_matches(snapshot, "snapshot_hash"):
        blockers.append("matrix_dataset_snapshot_hash_invalid")
    if str(snapshot.get("batch_spec_hash") or "") != expected_batch_hash:
        blockers.append("matrix_dataset_snapshot_batch_mismatch")
    if (
        canonical_hash(_sequence(snapshot.get("dataset_manifest"))) != expected_dataset_hash
        or str(snapshot.get("dataset_manifest_hash") or "") != expected_dataset_hash
    ):
        blockers.append("matrix_dataset_snapshot_manifest_mismatch")
    if (
        snapshot.get("research_only") is not True
        or snapshot.get("paper_authorized") is not False
        or snapshot.get("live_order_allowed") is not False
    ):
        blockers.append("matrix_dataset_snapshot_has_execution_authority")
    snapshot_datasets = [
        item for item in _sequence(snapshot.get("datasets")) if isinstance(item, dict)
    ]
    if len(snapshot_datasets) != len(_sequence(snapshot.get("datasets"))):
        blockers.append("matrix_dataset_snapshot_dataset_type_invalid")
    if snapshot.get("dataset_count") != len(snapshot_datasets):
        blockers.append("matrix_dataset_snapshot_count_mismatch")
    if snapshot.get("row_count") != sum(len(_sequence(item.get("rows"))) for item in snapshot_datasets):
        blockers.append("matrix_dataset_snapshot_row_count_mismatch")
    manifest_by_symbol = {
        str(item.get("symbol") or "").upper(): item
        for item in dataset_manifest
        if isinstance(item, dict) and str(item.get("symbol") or "").strip()
    }
    if len(manifest_by_symbol) != len(dataset_manifest):
        blockers.append("matrix_dataset_manifest_symbols_not_unique")
    selection_symbol_set = {
        str(symbol or "").upper() for symbol in _sequence(batch_spec.get("selection_symbols"))
    }
    confirmation_symbol_set = {
        str(symbol or "").upper() for symbol in _sequence(batch_spec.get("confirmation_symbols"))
    }
    snapshot_symbols: set[str] = set()
    for item in snapshot_datasets:
        symbol = str(item.get("symbol") or "").upper()
        source = str(item.get("source") or "")
        market = str(item.get("market") or "")
        rows = _sequence(item.get("rows"))
        if not symbol or symbol in snapshot_symbols:
            blockers.append(f"matrix_dataset_snapshot_symbol_invalid:{symbol or 'UNKNOWN'}")
            continue
        snapshot_symbols.add(symbol)
        manifest_item = _mapping(manifest_by_symbol.get(symbol))
        if not manifest_item:
            blockers.append(f"matrix_dataset_snapshot_manifest_missing:{symbol}")
            continue
        expected_role = (
            "SELECTION" if symbol in selection_symbol_set
            else "CONFIRMATION" if symbol in confirmation_symbol_set
            else ""
        )
        if str(item.get("role") or "") != expected_role or not expected_role:
            blockers.append(f"matrix_dataset_snapshot_role_mismatch:{symbol}")
        if str(manifest_item.get("source") or "") != source:
            blockers.append(f"matrix_dataset_snapshot_source_mismatch:{symbol}")
        if market == "stock" and (
            _mapping(item.get("data_revision_evidence")).get("status") != "PASS"
            or _mapping(manifest_item.get("data_revision_evidence")).get("status") != "PASS"
        ):
            blockers.append(f"matrix_dataset_revision_not_passed:{symbol}")
        if market == "crypto":
            market_history = _mapping(item.get("market_history_evidence"))
            manifest_history = _mapping(manifest_item.get("market_history_evidence"))
            if (
                market_history.get("status") != "PASS"
                or manifest_history.get("status") != "PASS"
            ):
                blockers.append(f"matrix_crypto_history_evidence_not_passed:{symbol}")
            rebuilt_history = build_history_dataset_evidence(
                symbol=symbol,
                rows=rows,
                source=source,
                dataset_lineage_id=str(market_history.get("dataset_lineage_id") or ""),
                cache_manifest=dict(market_history.get("cache_manifest") or {}),
                cache_admitted=market_history.get("cache_admitted") is True,
            )
            if market_history != rebuilt_history:
                blockers.append(f"matrix_crypto_history_evidence_mismatch:{symbol}")
            if market_history != manifest_history:
                blockers.append(f"matrix_crypto_history_manifest_mismatch:{symbol}")
        recomputed = prepare_backtest_dataset(
            rows,
            symbol=symbol,
            source=source,
            timeframe="1D",
            minimum_rows=1,
            market=market,
        )["manifest"]
        for field in ("data_hash", "row_count", "first", "last"):
            if recomputed.get(field) != manifest_item.get(field):
                blockers.append(f"matrix_dataset_snapshot_{field}_mismatch:{symbol}")
        if manifest_item.get("status") != "PASS" or _sequence(manifest_item.get("blockers")):
            blockers.append(f"matrix_dataset_manifest_not_passed:{symbol}")
    if snapshot_symbols != set(manifest_by_symbol):
        blockers.append("matrix_dataset_snapshot_symbol_set_mismatch")
    if str(report.get("matrix_result_hash") or "") != expected_result_hash:
        blockers.append("matrix_result_hash_mismatch")
    if str(report.get("batch_run_hash") or "") != expected_run_hash:
        blockers.append("batch_run_hash_mismatch")
    selection_regime = report.get("selection_regime_evidence")
    if not _embedded_hash_matches(selection_regime, "evidence_hash"):
        blockers.append("selection_regime_evidence_hash_mismatch")
    selection_correlation = report.get("selection_correlation_matrix")
    if not _embedded_hash_matches(selection_correlation, "matrix_hash"):
        blockers.append("selection_correlation_matrix_hash_mismatch")
    confirmation_regime = report.get("confirmation_regime_evidence")
    if not _embedded_hash_matches(confirmation_regime, "evidence_hash"):
        blockers.append("confirmation_regime_evidence_hash_mismatch")

    created_at_ms = _created_at_ms(report.get("created_at"))
    governance_audit = verify_matrix_research_governance(
        report.get("research_governance"),
        report_created_at_ms=created_at_ms,
        batch_spec_hash=expected_batch_hash,
        result_hash=expected_result_hash,
        dataset_manifest_hash=expected_dataset_hash,
    )
    blockers.extend(governance_audit.get("blockers") or [])
    if str(snapshot.get("registration_id") or "") != str(
        _mapping(report.get("research_governance")).get("registration_id") or ""
    ):
        blockers.append("matrix_dataset_snapshot_registration_mismatch")
    summary = _mapping(report.get("summary"))
    if summary.get("paper_authorized") is not False or summary.get("live_order_allowed") is not False:
        blockers.append("matrix_must_not_authorize_execution")
    if _report_only:
        completion = _mapping(_mapping(report.get("research_governance")).get("completion_receipt"))
        if not created_at_ms:
            blockers.append("matrix_created_at_missing")
        elif created_at_ms != int(completion.get("completed_at_ms") or 0):
            blockers.append("matrix_created_at_completion_mismatch")
        return {
            "version": MATRIX_EVIDENCE_VERSION,
            "status": "PASS" if not blockers else "BLOCK",
            "batch_run_hash": str(report.get("batch_run_hash") or ""),
            "matrix_result_hash": str(report.get("matrix_result_hash") or ""),
            "created_at": str(report.get("created_at") or ""),
            "research_governance_hash": str(governance_audit.get("governance_hash") or ""),
            "blockers": list(dict.fromkeys(blockers)),
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    age_ms = max(int(now_ms) - created_at_ms, 0) if created_at_ms else max_age_ms + 1
    if not created_at_ms:
        blockers.append("matrix_created_at_missing")
    elif age_ms > max(0, int(max_age_ms)):
        blockers.append(f"matrix_age_ms:{age_ms}>{max(0, int(max_age_ms))}")

    clean_strategy_id = str(strategy_id or "").strip().lower()
    forward_candidates = [str(item).lower() for item in _sequence(report.get("forward_candidates"))]
    if clean_strategy_id not in forward_candidates:
        blockers.append("strategy_not_forward_candidate")
    confirmation = next(
        (
            item for item in _sequence(report.get("confirmations"))
            if isinstance(item, dict)
            and str(item.get("strategy_id") or "").lower() == clean_strategy_id
        ),
        {},
    )
    if confirmation.get("status") != "PASS" or confirmation.get("forward_candidate") is not True:
        blockers.append("confirmation_not_passed")
    if _mapping(report.get("selection_alignment")).get("status") != "PASS":
        blockers.append("selection_alignment_not_passed")
    if _mapping(report.get("selection_calendar_schedule")).get("status") != "PASS":
        blockers.append("selection_calendar_not_passed")
    if _mapping(report.get("selection_regime_evidence")).get("status") != "PASS":
        blockers.append("selection_regime_not_passed")
    if _mapping(report.get("selection_correlation_matrix")).get("status") != "PASS":
        blockers.append("selection_correlation_not_passed")
    if _mapping(report.get("confirmation_alignment")).get("status") != "PASS":
        blockers.append("confirmation_alignment_not_passed")
    if _mapping(report.get("confirmation_calendar_schedule")).get("status") != "PASS":
        blockers.append("confirmation_calendar_not_passed")
    if _mapping(report.get("confirmation_regime_evidence")).get("status") != "PASS":
        blockers.append("confirmation_regime_not_passed")
    if _mapping(report.get("summary")).get("selection_gate_status") != "PASS":
        blockers.append("selection_gate_not_passed")

    strategy_specs = _mapping(batch_spec.get("strategy_specs"))
    strategy_spec = _mapping(strategy_specs.get(clean_strategy_id))
    if canonical_hash(strategy_spec.get("params") or {}) != canonical_hash(strategy_params):
        blockers.append("strategy_params_mismatch")
    if str(strategy_spec.get("implementation_fingerprint") or "") != str(implementation_fingerprint or ""):
        blockers.append("strategy_implementation_mismatch")
    if canonical_hash(strategy_spec.get("risk") or {}) != canonical_hash(risk):
        blockers.append("risk_params_mismatch")
    covered_symbols = {
        str(item).upper()
        for item in [
            *_sequence(batch_spec.get("selection_symbols")),
            *_sequence(batch_spec.get("confirmation_symbols")),
        ]
    }
    if str(symbol or "").upper() not in covered_symbols:
        blockers.append("symbol_not_covered_by_matrix")
    if summary.get("paper_authorized") is not False or summary.get("live_order_allowed") is not False:
        blockers.append("matrix_must_not_authorize_execution")

    return {
        "version": MATRIX_EVIDENCE_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "strategy_id": clean_strategy_id,
        "symbol": str(symbol or "").upper(),
        "batch_run_hash": str(report.get("batch_run_hash") or ""),
        "created_at": str(report.get("created_at") or ""),
        "age_ms": age_ms,
        "research_governance_hash": str(governance_audit.get("governance_hash") or ""),
        "common_start": str(_mapping(report.get("selection_alignment")).get("common_start") or ""),
        "common_as_of": str(_mapping(report.get("selection_alignment")).get("common_as_of") or ""),
        "blockers": list(dict.fromkeys(blockers)),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_strategy_matrix_report(report: dict[str, Any] | Any) -> dict[str, Any]:
    """Verify a complete matrix report without asserting candidate promotion.

    This reuses the exact schema, hash, dataset, governance, authority and
    semantic checks of ``verify_strategy_matrix_evidence``. Only report age and
    strategy/parameter/risk/symbol candidate assertions are omitted so a valid
    formal report with zero forward candidates can be sealed before registry
    completion.
    """

    return verify_strategy_matrix_evidence(
        report,
        strategy_id="",
        strategy_params={},
        implementation_fingerprint="",
        risk={},
        symbol="",
        now_ms=0,
        _report_only=True,
    )


def latest_strategy_matrix_evidence(
    reports_dir: Path,
    *,
    strategy_id: str,
    strategy_params: dict[str, Any],
    implementation_fingerprint: str,
    risk: dict[str, Any],
    symbol: str,
    now_ms: int,
) -> dict[str, Any]:
    paths = sorted(reports_dir.glob("strategy_matrix_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    latest_block: dict[str, Any] | None = None
    for path in paths[:20]:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        evidence = verify_strategy_matrix_evidence(
            report,
            strategy_id=strategy_id,
            strategy_params=strategy_params,
            implementation_fingerprint=implementation_fingerprint,
            risk=risk,
            symbol=symbol,
            now_ms=now_ms,
        )
        evidence["report_path"] = str(path)
        if evidence["status"] == "PASS":
            return evidence
        if latest_block is None:
            latest_block = evidence
    return latest_block or {
        "version": MATRIX_EVIDENCE_VERSION,
        "status": "BLOCK",
        "strategy_id": str(strategy_id or "").lower(),
        "symbol": str(symbol or "").upper(),
        "report_path": "",
        "blockers": ["no_strategy_matrix_report"],
        "paper_authorized": False,
        "live_order_allowed": False,
    }
