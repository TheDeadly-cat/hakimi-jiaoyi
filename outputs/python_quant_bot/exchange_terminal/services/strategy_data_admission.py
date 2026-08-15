from __future__ import annotations

import hashlib
import json
from typing import Any

from .corporate_action_ledger import verify_adjustment_evidence
from .market_data_revision_ledger import verify_cross_source_evidence


STRATEGY_DATA_ADMISSION_SCHEMA_VERSION = "strategy-data-admission-v1"
_AUTHORITY_FIELDS = {"paper_authorized", "live_order_allowed", "automatic_paper_activation_allowed"}


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sequence(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _native_nonnegative_int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _authority_violations(payload: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            if key in _AUTHORITY_FIELDS and value is not False:
                violations.append(child_path)
            violations.extend(_authority_violations(value, child_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            violations.extend(_authority_violations(value, f"{path}[{index}]"))
    return violations


def _completion_summary(rows: list[Any], *, generated_at: int, market: str) -> dict[str, Any]:
    grace_ms = 4 * 86_400_000 if market == "stock" else 2 * 86_400_000
    explicit_count = 0
    elapsed_count = 0
    incomplete_count = 0
    invalid_count = 0
    future_count = 0
    unattested_recent_count = 0
    for row in rows:
        if not isinstance(row, dict):
            invalid_count += 1
            continue
        complete = row.get("complete") is True
        ts_ms = _native_nonnegative_int(row.get("ts_ms"))
        if not complete or not ts_ms:
            incomplete_count += 1
            continue
        if ts_ms > generated_at + 5 * 60_000:
            future_count += 1
            continue
        if row.get("complete_attested") is True:
            explicit_count += 1
        elif generated_at - ts_ms >= grace_ms:
            elapsed_count += 1
        else:
            unattested_recent_count += 1
    eligible_count = explicit_count + elapsed_count
    return {
        "policy": "EXPLICIT_PROVIDER_CONFIRM_OR_TIME_ELAPSED",
        "grace_ms": grace_ms,
        "input_row_count": len(rows),
        "eligible_row_count": eligible_count,
        "explicit_attestation_count": explicit_count,
        "time_elapsed_attestation_count": elapsed_count,
        "incomplete_count": incomplete_count,
        "invalid_count": invalid_count,
        "future_timestamp_count": future_count,
        "unattested_recent_count": unattested_recent_count,
    }


def _cross_source_pass(revision: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    audits: list[dict[str, Any]] = []
    passed = False
    for item in _sequence(revision.get("cross_source")):
        if not isinstance(item, dict):
            audits.append({"status": "BLOCK", "blockers": ["cross_source_record_type_invalid"]})
            continue
        audit = verify_cross_source_evidence(item)
        audits.append(audit)
        if (
            audit.get("status") == "PASS"
            and item.get("status") == "PASS"
            and item.get("independent_provider_families") is True
        ):
            passed = True
    return passed, audits


def _evaluate(payload: dict[str, Any], *, verification_at: int) -> tuple[list[str], list[str]]:
    research_blockers: list[str] = []
    paper_blockers: list[str] = []
    dataset = _mapping(payload.get("dataset"))
    completion = _mapping(payload.get("completion"))
    contracts = _mapping(payload.get("contracts"))
    mode = str(payload.get("mode") or "").upper()
    market = str(dataset.get("market") or "").lower()
    row_count = _native_nonnegative_int(dataset.get("row_count"))
    input_row_count = _native_nonnegative_int(completion.get("input_row_count"))

    if payload.get("schema_version") != STRATEGY_DATA_ADMISSION_SCHEMA_VERSION:
        research_blockers.append("data_admission_schema_invalid")
    if market not in {"stock", "crypto"}:
        research_blockers.append("market_type_invalid")
    symbol = str(dataset.get("symbol") or "").strip().upper()
    if not symbol:
        research_blockers.append("dataset_symbol_missing")
    else:
        expected_market = "crypto" if "-USDT" in symbol or symbol.endswith("-SWAP") else "stock"
        if market != expected_market:
            research_blockers.append("dataset_market_symbol_mismatch")
    if not str(dataset.get("source") or "").strip():
        research_blockers.append("dataset_source_missing")
    if any(token in str(dataset.get("source") or "").lower() for token in ("synthetic", "preview_seed", "offline-seed")):
        research_blockers.append("synthetic_dataset_source")
    if dataset.get("status") != "PASS" or dataset.get("hash_scope") != "FULL_OHLCV":
        research_blockers.append("structural_dataset_contract")
    if not _valid_sha256(dataset.get("data_hash")):
        research_blockers.append("dataset_hash_invalid")
    if row_count <= 0 or input_row_count != row_count:
        research_blockers.append("dataset_row_count_mismatch")
    if (
        _native_nonnegative_int(completion.get("eligible_row_count")) != row_count
        or _native_nonnegative_int(completion.get("incomplete_count"))
        or _native_nonnegative_int(completion.get("invalid_count"))
        or _native_nonnegative_int(completion.get("future_timestamp_count"))
        or _native_nonnegative_int(completion.get("unattested_recent_count"))
    ):
        research_blockers.append("completed_candle_attestation")

    last_ts_ms = _native_nonnegative_int(dataset.get("last_ts_ms"))
    freshness_limit_ms = _native_nonnegative_int(dataset.get("freshness_limit_ms"))
    if not last_ts_ms or not freshness_limit_ms:
        research_blockers.append("dataset_freshness_contract_missing")
    elif last_ts_ms > verification_at + 5 * 60_000:
        research_blockers.append("dataset_timestamp_in_future")
    elif verification_at - last_ts_ms > freshness_limit_ms:
        research_blockers.append("dataset_stale")

    if mode != "FROZEN":
        paper_blockers.append("immutable_dataset_lineage_missing")
    lineage_id = str(payload.get("dataset_lineage_id") or "").strip()
    if not lineage_id or len(lineage_id) > 160:
        paper_blockers.append("dataset_lineage_id_invalid")
    if not _valid_sha256(payload.get("lineage_hash")):
        paper_blockers.append("dataset_lineage_hash_invalid")
    else:
        expected_lineage_hash = canonical_hash({
            "dataset_lineage_id": lineage_id,
            "symbol": str(dataset.get("symbol") or "").upper(),
            "source": str(dataset.get("source") or ""),
            "data_hash": str(dataset.get("data_hash") or ""),
        })
        if str(payload.get("lineage_hash") or "") != expected_lineage_hash:
            paper_blockers.append("dataset_lineage_hash_mismatch")

    if market == "stock":
        adjustment = _mapping(contracts.get("adjustment_evidence"))
        adjustment_audit = verify_adjustment_evidence(adjustment)
        if adjustment_audit.get("status") != "PASS" or adjustment.get("backtest_eligible") is not True:
            research_blockers.append("stock_adjustment_contract")
        revision = _mapping(contracts.get("data_revision_evidence"))
        accepted = _mapping(revision.get("accepted_cache"))
        backtest = _mapping(revision.get("backtest_dataset"))
        current = _mapping(backtest.get("current"))
        if revision.get("status") != "PASS" or accepted.get("status") != "PASS" or backtest.get("status") != "PASS":
            paper_blockers.append("stock_revision_ledger")
        if (
            not _valid_sha256(_mapping(accepted.get("current")).get("snapshot_hash"))
            or not _valid_sha256(current.get("snapshot_hash"))
        ):
            paper_blockers.append("stock_revision_snapshot_hash")
        if (
            str(current.get("lineage_id") or "") != lineage_id
            or str(current.get("role") or "").upper() != "BACKTEST_DATASET"
            or str(current.get("symbol") or "").upper() != str(dataset.get("symbol") or "").upper()
            or _native_nonnegative_int(current.get("row_count")) != row_count
        ):
            paper_blockers.append("stock_revision_lineage_binding")
        cross_source_ok, _ = _cross_source_pass(revision)
        if not cross_source_ok:
            paper_blockers.append("independent_cross_source_evidence")
    elif contracts.get("adjustment_evidence") or contracts.get("data_revision_evidence"):
        research_blockers.append("crypto_must_not_claim_stock_data_contracts")

    authority_paths = _authority_violations(payload)
    if authority_paths:
        research_blockers.append("data_evidence_has_execution_authority")

    return list(dict.fromkeys(research_blockers)), list(dict.fromkeys([*research_blockers, *paper_blockers]))


def build_strategy_data_admission(
    *,
    market_payload: dict[str, Any],
    dataset_manifest: dict[str, Any],
    dataset_lineage_id: str,
    market: str,
    generated_at: int,
) -> dict[str, Any]:
    payload = _mapping(market_payload)
    manifest = _mapping(dataset_manifest)
    rows = _sequence(payload.get("rows"))
    clean_market = str(market or "").strip().lower()
    clean_lineage_id = str(dataset_lineage_id or "").strip()
    mode = "FROZEN" if clean_lineage_id else "PREVIEW"
    freshness_limit_ms = 10 * 86_400_000 if clean_market == "stock" else 4 * 86_400_000
    dataset = {
        "symbol": str(manifest.get("symbol") or payload.get("symbol") or "").upper(),
        "market": clean_market,
        "timeframe": str(manifest.get("timeframe") or payload.get("bar") or "1D"),
        "source": str(manifest.get("source") or payload.get("source") or ""),
        "retrieval_source": str(payload.get("retrieval_source") or payload.get("source") or ""),
        "origin_sources": [str(item) for item in _sequence(payload.get("origin_sources")) if str(item)],
        "status": str(manifest.get("status") or "BLOCK"),
        "hash_scope": str(manifest.get("hash_scope") or ""),
        "data_hash": str(manifest.get("data_hash") or ""),
        "row_count": _native_nonnegative_int(manifest.get("row_count")),
        "first": str(manifest.get("first") or ""),
        "last": str(manifest.get("last") or ""),
        "first_ts_ms": _native_nonnegative_int(manifest.get("first_ts_ms")),
        "last_ts_ms": _native_nonnegative_int(manifest.get("last_ts_ms")),
        "freshness_limit_ms": freshness_limit_ms,
        "structural_blockers": list(manifest.get("blockers") or []) if isinstance(manifest.get("blockers"), list) else [],
    }
    lineage_hash = canonical_hash({
        "dataset_lineage_id": clean_lineage_id,
        "symbol": dataset["symbol"],
        "source": dataset["source"],
        "data_hash": dataset["data_hash"],
    }) if clean_lineage_id else ""
    result = {
        "schema_version": STRATEGY_DATA_ADMISSION_SCHEMA_VERSION,
        "generated_at": int(generated_at),
        "mode": mode,
        "dataset_lineage_id": clean_lineage_id,
        "lineage_hash": lineage_hash,
        "dataset": dataset,
        "completion": _completion_summary(rows, generated_at=int(generated_at), market=clean_market),
        "source_warning": str(payload.get("warning") or ""),
        "contracts": {
            "adjustment_evidence": dict(_mapping(payload.get("adjustment_evidence"))) if clean_market == "stock" else {},
            "data_revision_evidence": dict(_mapping(payload.get("data_revision_evidence"))) if clean_market == "stock" else {},
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    research_blockers, paper_blockers = _evaluate(result, verification_at=int(generated_at))
    result["research_blockers"] = research_blockers
    result["blockers"] = paper_blockers
    result["research_gate_status"] = "PASS" if not research_blockers else "BLOCK"
    result["paper_gate_status"] = "PASS" if mode == "FROZEN" and not paper_blockers else "BLOCK"
    result["status"] = (
        "BLOCK"
        if research_blockers or (mode == "FROZEN" and paper_blockers)
        else "PASS"
        if result["paper_gate_status"] == "PASS"
        else "REVIEW"
    )
    result["evidence_hash"] = canonical_hash(result)
    return result


def verify_strategy_data_admission(
    evidence: dict[str, Any] | Any,
    *,
    expected_symbol: str,
    expected_data_hash: str,
    expected_lineage_id: str = "",
    verification_at: int,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(evidence, dict):
        blockers.append("data_admission_type_invalid")
    payload = _mapping(evidence)
    clean = dict(payload)
    expected_hash = str(clean.pop("evidence_hash", "") or "")
    if not expected_hash or canonical_hash(clean) != expected_hash:
        blockers.append("data_admission_evidence_hash_invalid")
    dataset = _mapping(payload.get("dataset"))
    if str(dataset.get("symbol") or "").upper() != str(expected_symbol or "").upper():
        blockers.append("data_admission_symbol_mismatch")
    if str(dataset.get("data_hash") or "") != str(expected_data_hash or ""):
        blockers.append("data_admission_dataset_hash_mismatch")
    if expected_lineage_id and str(payload.get("dataset_lineage_id") or "") != str(expected_lineage_id):
        blockers.append("data_admission_lineage_mismatch")
    research_blockers, paper_blockers = _evaluate(payload, verification_at=int(verification_at))
    if payload.get("research_blockers") != research_blockers:
        blockers.append("data_admission_research_semantics_mismatch")
    if payload.get("blockers") != paper_blockers:
        blockers.append("data_admission_paper_semantics_mismatch")
    expected_research_status = "PASS" if not research_blockers else "BLOCK"
    expected_paper_status = "PASS" if payload.get("mode") == "FROZEN" and not paper_blockers else "BLOCK"
    expected_status = (
        "BLOCK"
        if research_blockers or (payload.get("mode") == "FROZEN" and paper_blockers)
        else "PASS"
        if expected_paper_status == "PASS"
        else "REVIEW"
    )
    if payload.get("research_gate_status") != expected_research_status:
        blockers.append("data_admission_research_status_mismatch")
    if payload.get("paper_gate_status") != expected_paper_status:
        blockers.append("data_admission_paper_status_mismatch")
    if payload.get("status") != expected_status:
        blockers.append("data_admission_status_mismatch")
    if expected_status != "PASS":
        blockers.extend(paper_blockers or ["data_admission_not_frozen"])
    return {
        "schema_version": STRATEGY_DATA_ADMISSION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "evidence_hash": expected_hash,
        "dataset_lineage_id": str(payload.get("dataset_lineage_id") or ""),
        "blockers": list(dict.fromkeys(blockers)),
        "paper_authorized": False,
        "live_order_allowed": False,
    }
