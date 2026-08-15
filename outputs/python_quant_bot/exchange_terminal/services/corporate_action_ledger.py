from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .sqlite_runtime import connect_runtime_sqlite, require_runtime_writable

try:
    from market_data.stock_candle_quality import analyze_stock_candle_series
except ModuleNotFoundError:
    from exchange_terminal.market_data.stock_candle_quality import analyze_stock_candle_series


CORPORATE_ACTION_SCHEMA_VERSION = "stock-corporate-action-ledger-v5"
CORPORATE_ACTION_ATTESTATION_SCHEMA_VERSION = "corporate-action-source-attestation-v2"
CORPORATE_ACTION_SOURCE_EVIDENCE_SCHEMA_VERSION = "corporate-action-source-evidence-v1"
OFFICIAL_CORPORATE_ACTION_AUTHORITIES = {
    "OFFICIAL_EXCHANGE_FEED",
    "OFFICIAL_ISSUER_FEED",
    "REGULATORY_MASTER_DATA",
}
REQUIRED_OFFICIAL_ACTION_TYPES = {"SPLIT", "DIVIDEND", "SUSPENSION", "DELISTING"}
KNOWN_ADJUSTED_BASES = {
    "FORWARD_ADJUSTED_QFQ",
    "FORWARD_ADJUSTED_TOTAL_RETURN",
    "BACKWARD_ADJUSTED_HFQ",
    "SPLIT_ADJUSTED",
    "RAW_UNADJUSTED",
    "TEST_FIXTURE_CONTRACT",
}
ADJUSTMENT_ACCOUNTING_POLICIES = {
    "FORWARD_ADJUSTED_QFQ": {
        "price_basis": "SYNTHETIC_FORWARD_ADJUSTED",
        "split_mode": "EMBEDDED_IN_ADJUSTED_SERIES",
        "dividend_mode": "EMBEDDED_IN_ADJUSTED_RETURN",
        "requires_complete_actions": False,
        "cash_execution_supported": True,
    },
    "FORWARD_ADJUSTED_TOTAL_RETURN": {
        "price_basis": "SYNTHETIC_FORWARD_ADJUSTED_TOTAL_RETURN",
        "split_mode": "EMBEDDED_IN_ADJUSTED_SERIES",
        "dividend_mode": "EMBEDDED_IN_ADJUSTED_RETURN",
        "requires_complete_actions": False,
        "cash_execution_supported": True,
    },
    "TEST_FIXTURE_CONTRACT": {
        "price_basis": "DETERMINISTIC_TEST_FIXTURE",
        "split_mode": "EMBEDDED_IN_ADJUSTED_SERIES",
        "dividend_mode": "EMBEDDED_IN_ADJUSTED_RETURN",
        "requires_complete_actions": False,
        "cash_execution_supported": True,
    },
    "SPLIT_ADJUSTED": {
        "price_basis": "SPLIT_ADJUSTED_CASH_PRICE",
        "split_mode": "EMBEDDED_IN_ADJUSTED_SERIES",
        "dividend_mode": "EXPLICIT_PAY_DATE_CASH",
        "requires_complete_actions": True,
        "cash_execution_supported": True,
    },
    "RAW_UNADJUSTED": {
        "price_basis": "RAW_CASH_PRICE",
        "split_mode": "EXPLICIT_QUANTITY_ADJUSTMENT",
        "dividend_mode": "EXPLICIT_PAY_DATE_CASH",
        "requires_complete_actions": True,
        "cash_execution_supported": True,
    },
    "BACKWARD_ADJUSTED_HFQ": {
        "price_basis": "SYNTHETIC_BACKWARD_ADJUSTED",
        "split_mode": "EMBEDDED_IN_ADJUSTED_SERIES",
        "dividend_mode": "EMBEDDED_IN_ADJUSTED_RETURN",
        "requires_complete_actions": False,
        "cash_execution_supported": False,
    },
}


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _clean_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        return ""
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _valid_evidence_ref(value: Any) -> bool:
    text = str(value or "").strip()
    if text.startswith("urn:"):
        return len(text) > 4
    parsed = urlparse(text)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _positive(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return parsed if math.isfinite(parsed) and parsed > 0 else 0.0


def _event_date(value: Any, timestamp: Any = 0) -> str:
    text = str(value or "").strip()[:10]
    if len(text) == 10 and text[4:5] == "-" and text[7:8] == "-":
        return text
    try:
        numeric = int(float(timestamp or value or 0))
        if numeric > 10_000_000_000:
            numeric //= 1000
        if numeric > 0:
            return datetime.fromtimestamp(numeric, timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        pass
    return ""


def infer_adjustment_basis(source: str, explicit: str = "") -> str:
    supplied = str(explicit or "").strip().upper()
    if supplied:
        return supplied
    clean_source = str(source or "").strip().lower()
    if "futu" in clean_source:
        return "FORWARD_ADJUSTED_QFQ"
    if clean_source in {"test", "fixture", "unit_test"} or "test_fixture" in clean_source:
        return "TEST_FIXTURE_CONTRACT"
    if "yahoo_adjusted" in clean_source:
        return "FORWARD_ADJUSTED_TOTAL_RETURN"
    if "yahoo" in clean_source:
        return "YAHOO_CHART_CLOSE_UNVERIFIED"
    if "stooq" in clean_source:
        return "STOOQ_CLOSE_UNVERIFIED"
    return "UNKNOWN"


def normalize_corporate_actions(
    symbol: str,
    provider: str,
    actions: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    clean_symbol = str(symbol or "").upper()
    clean_provider = str(provider or "unknown").lower()
    normalized: list[dict[str, Any]] = []
    for raw in actions or []:
        if not isinstance(raw, dict):
            continue
        action_type = str(raw.get("action_type") or raw.get("type") or "").upper()
        if action_type not in {"SPLIT", "DIVIDEND"}:
            continue
        event_date = _event_date(
            raw.get("event_date") or raw.get("date"),
            raw.get("effective_ts_ms") or raw.get("timestamp"),
        )
        if not clean_symbol or not event_date:
            continue
        numerator = _positive(raw.get("numerator"))
        denominator = _positive(raw.get("denominator"))
        ratio = _positive(raw.get("ratio"))
        if action_type == "SPLIT":
            if ratio <= 0 and numerator > 0 and denominator > 0:
                ratio = numerator / denominator
            if ratio <= 0:
                continue
        amount = _positive(raw.get("cash_amount") or raw.get("amount")) if action_type == "DIVIDEND" else 0.0
        event_provider = str(raw.get("provider") or clean_provider).lower()
        try:
            effective_ts_ms = int(float(raw.get("effective_ts_ms") or raw.get("timestamp") or 0))
        except (TypeError, ValueError, OverflowError):
            effective_ts_ms = 0
        if 0 < effective_ts_ms < 10_000_000_000:
            effective_ts_ms *= 1000
        event = {
            "symbol": clean_symbol,
            "provider": event_provider,
            "action_type": action_type,
            "event_date": event_date,
            "effective_ts_ms": effective_ts_ms,
            "numerator": round(numerator, 8),
            "denominator": round(denominator, 8),
            "ratio": round(ratio, 8),
            "cash_amount": round(amount, 8),
            "currency": str(raw.get("currency") or "").upper(),
            "record_date": _event_date(raw.get("record_date")),
            "pay_date": _event_date(raw.get("pay_date") or raw.get("payment_date")),
            "provider_event_id": str(raw.get("provider_event_id") or raw.get("id") or ""),
        }
        event["action_id"] = _canonical_hash(event)
        normalized.append(event)
    return sorted(
        {item["action_id"]: item for item in normalized}.values(),
        key=lambda item: (item["event_date"], item["action_type"], item["action_id"]),
    )


def parse_yahoo_corporate_actions(symbol: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    events = dict((result or {}).get("events") or {})
    raw_actions: list[dict[str, Any]] = []
    for provider_id, raw in dict(events.get("splits") or {}).items():
        if not isinstance(raw, dict):
            continue
        numerator = _positive(raw.get("numerator"))
        denominator = _positive(raw.get("denominator"))
        ratio = _positive(raw.get("splitRatio"))
        if ratio <= 0:
            text = str(raw.get("splitRatio") or "")
            if ":" in text:
                left, right = text.split(":", 1)
                ratio = _positive(left) / max(_positive(right), 1e-12)
        raw_actions.append({
            "action_type": "SPLIT",
            "timestamp": raw.get("date"),
            "numerator": numerator,
            "denominator": denominator,
            "ratio": ratio,
            "provider_event_id": provider_id,
        })
    for provider_id, raw in dict(events.get("dividends") or {}).items():
        if not isinstance(raw, dict):
            continue
        raw_actions.append({
            "action_type": "DIVIDEND",
            "timestamp": raw.get("date"),
            "cash_amount": raw.get("amount"),
            "currency": raw.get("currency"),
            "provider_event_id": provider_id,
        })
    return normalize_corporate_actions(symbol, "yahoo", raw_actions)


def build_corporate_action_source_evidence(
    *,
    source_authority: str,
    source_name: str,
    evidence_ref: str,
    source_document_sha256: str,
    observed_at: str,
    coverage_types: list[str],
    record_count: int,
) -> dict[str, Any]:
    count = record_count if isinstance(record_count, int) and not isinstance(record_count, bool) else -1
    payload = {
        "schema_version": CORPORATE_ACTION_SOURCE_EVIDENCE_SCHEMA_VERSION,
        "source_authority": str(source_authority or "").strip().upper(),
        "source_name": str(source_name or "").strip(),
        "evidence_ref": str(evidence_ref or "").strip(),
        "source_document_sha256": str(source_document_sha256 or "").strip().lower(),
        "observed_at": _clean_timestamp(observed_at),
        "coverage_types": sorted({
            str(item or "").strip().upper()
            for item in coverage_types or []
            if str(item or "").strip()
        }),
        "record_count": count,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["evidence_sha256"] = _canonical_hash(payload)
    return payload


def build_official_corporate_action_attestation(
    *,
    source_authority: str,
    source_name: str,
    evidence_ref: str,
    evidence_sha256: str,
    observed_at: str,
    coverage_types: list[str],
    evidence_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    authority = str(source_authority or "").strip().upper()
    name = str(source_name or "").strip()
    reference = str(evidence_ref or "").strip()
    evidence_hash = str(evidence_sha256 or "").strip().lower()
    timestamp = _clean_timestamp(observed_at)
    types = sorted({str(item or "").strip().upper() for item in coverage_types or [] if str(item).strip()})
    source_evidence = dict(evidence_payload or {})
    blockers: list[str] = []
    if authority not in OFFICIAL_CORPORATE_ACTION_AUTHORITIES:
        blockers.append(f"corporate_action_source_not_official:{authority or '--'}")
    if not name or not _valid_evidence_ref(reference):
        blockers.append("corporate_action_source_evidence_missing")
    if not _valid_sha256(evidence_hash):
        blockers.append("corporate_action_source_evidence_hash_invalid")
    if not timestamp:
        blockers.append("corporate_action_source_observed_at_invalid")
    missing_types = sorted(REQUIRED_OFFICIAL_ACTION_TYPES - set(types))
    if missing_types:
        blockers.append(f"corporate_action_source_coverage_incomplete:{','.join(missing_types)}")
    source_hash_payload = dict(source_evidence)
    source_payload_hash = str(source_hash_payload.pop("evidence_sha256", "") or "")
    if not source_evidence:
        blockers.append("corporate_action_source_evidence_payload_missing")
    elif (
        str(source_evidence.get("schema_version") or "") != CORPORATE_ACTION_SOURCE_EVIDENCE_SCHEMA_VERSION
        or not _valid_sha256(source_payload_hash)
        or source_payload_hash != _canonical_hash(source_hash_payload)
        or evidence_hash != source_payload_hash
    ):
        blockers.append("corporate_action_source_evidence_payload_invalid")
    else:
        expected_source_fields = {
            "source_authority": authority,
            "source_name": name,
            "evidence_ref": reference,
            "observed_at": timestamp,
            "coverage_types": types,
        }
        if any(source_evidence.get(field) != value for field, value in expected_source_fields.items()):
            blockers.append("corporate_action_source_evidence_claim_mismatch")
        if not _valid_sha256(source_evidence.get("source_document_sha256")):
            blockers.append("corporate_action_source_document_hash_invalid")
        record_count = source_evidence.get("record_count")
        if isinstance(record_count, bool) or not isinstance(record_count, int) or record_count < 0:
            blockers.append("corporate_action_source_record_count_invalid")
        if (
            source_evidence.get("research_only") is not True
            or source_evidence.get("paper_authorized") is not False
            or source_evidence.get("live_order_allowed") is not False
        ):
            blockers.append("corporate_action_source_evidence_has_execution_authority")
    payload = {
        "schema_version": CORPORATE_ACTION_ATTESTATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "source_authority": authority,
        "source_name": name,
        "evidence_ref": reference,
        "evidence_sha256": evidence_hash,
        "evidence_payload": source_evidence,
        "observed_at": timestamp,
        "coverage_types": types,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["attestation_hash"] = _canonical_hash(payload)
    return payload


def verify_official_corporate_action_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    attestation = dict(attestation) if isinstance(attestation, dict) else {}
    payload = dict(attestation)
    expected_hash = str(payload.pop("attestation_hash", "") or "")
    blockers: list[str] = []
    if str(attestation.get("schema_version") or "") != CORPORATE_ACTION_ATTESTATION_SCHEMA_VERSION:
        blockers.append("corporate_action_attestation_schema_invalid")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("corporate_action_attestation_hash_invalid")
    coverage_value = attestation.get("coverage_types")
    if not isinstance(coverage_value, list):
        blockers.append("corporate_action_attestation_coverage_type_invalid")
        coverage_value = []
    rebuilt = build_official_corporate_action_attestation(
        source_authority=str(attestation.get("source_authority") or ""),
        source_name=str(attestation.get("source_name") or ""),
        evidence_ref=str(attestation.get("evidence_ref") or ""),
        evidence_sha256=str(attestation.get("evidence_sha256") or ""),
        observed_at=str(attestation.get("observed_at") or ""),
        coverage_types=list(coverage_value),
        evidence_payload=(
            dict(attestation.get("evidence_payload") or {})
            if isinstance(attestation.get("evidence_payload"), dict)
            else {}
        ),
    )
    for field in (
        "status",
        "blockers",
        "source_authority",
        "source_name",
        "evidence_ref",
        "evidence_sha256",
        "evidence_payload",
        "observed_at",
        "coverage_types",
    ):
        if attestation.get(field) != rebuilt.get(field):
            blockers.append(f"corporate_action_attestation_semantic_mismatch:{field}")
    blockers.extend(
        f"corporate_action_attestation_declared_blocker:{item}"
        for item in rebuilt.get("blockers") or []
    )
    if (
        attestation.get("research_only") is not True
        or attestation.get("paper_authorized") is not False
        or attestation.get("live_order_allowed") is not False
    ):
        blockers.append("corporate_action_attestation_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "attestation_hash": expected_hash,
        "official_source_verified": not blockers,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_adjustment_evidence(
    *,
    symbol: str,
    rows: list[dict[str, Any]],
    source: str,
    adjustment_basis: str = "",
    corporate_actions: list[dict[str, Any]] | None = None,
    corporate_action_coverage: str = "",
    corporate_action_attestation: dict[str, Any] | None = None,
    interval: str = "1d",
    session: str = "regular",
) -> dict[str, Any]:
    clean_symbol = str(symbol or "").upper()
    basis = infer_adjustment_basis(source, adjustment_basis)
    actions = normalize_corporate_actions(clean_symbol, str(source or "unknown"), corporate_actions)
    policy = dict(ADJUSTMENT_ACCOUNTING_POLICIES.get(basis) or {})
    coverage = str(corporate_action_coverage or "").strip().upper()
    source_attestation = dict(corporate_action_attestation or {})
    source_attestation_audit = verify_official_corporate_action_attestation(source_attestation)
    official_source_verified = source_attestation_audit.get("status") == "PASS"
    if not coverage and basis in {
        "FORWARD_ADJUSTED_QFQ",
        "FORWARD_ADJUSTED_TOTAL_RETURN",
        "TEST_FIXTURE_CONTRACT",
    }:
        coverage = "EMBEDDED_PROVIDER_CONTRACT"
    if not coverage:
        coverage = "UNKNOWN"
    quality = analyze_stock_candle_series(list(rows or []), minimum_analysis_rows=20)
    latest_break = dict(quality.get("latest_break") or {})
    matched_action: dict[str, Any] = {}
    if latest_break:
        break_date = _event_date(latest_break.get("date"))
        observed_ratio = _positive(latest_break.get("current_close")) / max(
            _positive(latest_break.get("previous_close")), 1e-12
        )
        for action in actions:
            if action.get("action_type") != "SPLIT" or action.get("event_date") != break_date:
                continue
            split_ratio = _positive(action.get("ratio"))
            expected_ratios = [split_ratio, 1.0 / max(split_ratio, 1e-12)]
            relative_error = min(abs(observed_ratio / max(item, 1e-12) - 1.0) for item in expected_ratios)
            if relative_error <= 0.20:
                matched_action = {**action, "observed_ratio": round(observed_ratio, 8), "relative_error": round(relative_error, 8)}
                break

    has_break = bool(latest_break)
    basis_known = basis in KNOWN_ADJUSTED_BASES and bool(policy)
    blockers: list[str] = []
    warnings: list[str] = []
    if has_break:
        if basis == "RAW_UNADJUSTED" and matched_action:
            warnings.append("raw_price_scale_break_accounted_by_declared_split")
        else:
            blockers.append("price_scale_break_requires_uniform_adjustment")
            if matched_action:
                warnings.append("scale_break_matches_declared_split_but_series_is_not_uniformly_adjusted")
            else:
                blockers.append("price_scale_break_without_matching_split_event")
    if not basis_known:
        blockers.append(f"adjustment_basis_unverified:{basis}")
    elif not bool(policy.get("cash_execution_supported")):
        blockers.append(f"adjustment_basis_not_cash_executable:{basis}")
    if bool(policy.get("requires_complete_actions")) and coverage != "COMPLETE":
        blockers.append(f"corporate_action_coverage_incomplete:{coverage}")
    if coverage in OFFICIAL_CORPORATE_ACTION_AUTHORITIES and not official_source_verified:
        blockers.append("official_corporate_action_attestation_missing_or_invalid")
    if str(policy.get("dividend_mode") or "") == "EXPLICIT_PAY_DATE_CASH":
        for action in actions:
            if action.get("action_type") == "DIVIDEND" and not action.get("pay_date"):
                blockers.append(f"dividend_pay_date_missing:{action.get('event_date') or '--'}")
    review_only = bool(blockers) and all(item.startswith("adjustment_basis_unverified:") for item in blockers)
    status = "PASS" if not blockers else "REVIEW" if review_only else "BLOCK"
    return_accounting = {
        **policy,
        "corporate_action_coverage": coverage,
        "explicit_action_count": len(actions),
        "double_count_protection": True,
    }
    payload = {
        "schema_version": CORPORATE_ACTION_SCHEMA_VERSION,
        "symbol": clean_symbol,
        "interval": str(interval or "1d").lower(),
        "session": str(session or "regular").lower(),
        "source": str(source or ""),
        "adjustment_basis": basis,
        "corporate_action_coverage": coverage,
        "return_accounting": return_accounting,
        "return_accounting_hash": _canonical_hash(return_accounting),
        "status": status,
        "backtest_eligible": not blockers,
        "has_scale_break": has_break,
        "latest_break": latest_break,
        "matched_action": matched_action,
        "corporate_action_count": len(actions),
        "corporate_actions": actions,
        "corporate_actions_hash": _canonical_hash(actions),
        "official_source_attestation": source_attestation,
        "official_source_attestation_hash": str(source_attestation.get("attestation_hash") or ""),
        "official_corporate_action_source_verified": official_source_verified,
        "blockers": blockers,
        "warnings": warnings,
        "automatic_price_rewrite": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["evidence_hash"] = _canonical_hash(payload)
    return payload


def verify_adjustment_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence = dict(evidence) if isinstance(evidence, dict) else {}
    payload = dict(evidence)
    expected_hash = str(payload.pop("evidence_hash", "") or "")
    blockers: list[str] = []
    if str(evidence.get("schema_version") or "") != CORPORATE_ACTION_SCHEMA_VERSION:
        blockers.append("adjustment_evidence_schema_invalid")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("adjustment_evidence_hash_invalid")
    return_accounting = (
        dict(evidence.get("return_accounting") or {})
        if isinstance(evidence.get("return_accounting"), dict)
        else {}
    )
    if str(evidence.get("return_accounting_hash") or "") != _canonical_hash(return_accounting):
        blockers.append("adjustment_return_accounting_hash_invalid")
    basis = str(evidence.get("adjustment_basis") or "")
    policy = dict(ADJUSTMENT_ACCOUNTING_POLICIES.get(basis) or {})
    coverage = str(evidence.get("corporate_action_coverage") or "").upper()
    actions_value = evidence.get("corporate_actions")
    actions = [dict(item) for item in actions_value or [] if isinstance(item, dict)] if isinstance(actions_value, list) else []
    normalized_actions = normalize_corporate_actions(
        str(evidence.get("symbol") or ""),
        str(evidence.get("source") or "unknown"),
        actions,
    )
    if not isinstance(actions_value, list):
        blockers.append("adjustment_corporate_actions_type_invalid")
    elif actions != normalized_actions:
        blockers.append("adjustment_corporate_actions_not_normalized")
    expected_accounting = {
        **policy,
        "corporate_action_coverage": coverage,
        "explicit_action_count": len(normalized_actions),
        "double_count_protection": True,
    }
    if not policy:
        blockers.append(f"adjustment_evidence_basis_unknown:{basis or '--'}")
    if return_accounting != expected_accounting:
        blockers.append("adjustment_return_accounting_semantic_mismatch")
    action_count = evidence.get("corporate_action_count")
    if isinstance(action_count, bool) or not isinstance(action_count, int) or action_count < 0:
        blockers.append("adjustment_corporate_action_count_invalid")
    elif action_count != len(normalized_actions):
        blockers.append("adjustment_corporate_action_count_mismatch")
    if str(evidence.get("corporate_actions_hash") or "") != _canonical_hash(normalized_actions):
        blockers.append("adjustment_corporate_actions_hash_invalid")
    has_scale_break = evidence.get("has_scale_break")
    latest_break = evidence.get("latest_break")
    matched_action = evidence.get("matched_action")
    if not isinstance(has_scale_break, bool):
        blockers.append("adjustment_scale_break_flag_invalid")
    if not isinstance(latest_break, dict) or bool(latest_break) is not (has_scale_break is True):
        blockers.append("adjustment_latest_break_semantic_mismatch")
    if not isinstance(matched_action, dict):
        blockers.append("adjustment_matched_action_type_invalid")
        matched_action = {}
    if matched_action:
        action_ids = {str(item.get("action_id") or "") for item in normalized_actions}
        if str(matched_action.get("action_id") or "") not in action_ids:
            blockers.append("adjustment_matched_action_not_in_ledger")
    attestation = (
        dict(evidence.get("official_source_attestation") or {})
        if isinstance(evidence.get("official_source_attestation"), dict)
        else {}
    )
    attestation_audit = verify_official_corporate_action_attestation(attestation)
    official_verified = attestation_audit.get("status") == "PASS"
    semantic_blockers: list[str] = []
    if has_scale_break is True:
        if basis != "RAW_UNADJUSTED" or not matched_action:
            semantic_blockers.append("price_scale_break_requires_uniform_adjustment")
            if not matched_action:
                semantic_blockers.append("price_scale_break_without_matching_split_event")
    if not policy:
        semantic_blockers.append(f"adjustment_basis_unverified:{basis or '--'}")
    elif not bool(policy.get("cash_execution_supported")):
        semantic_blockers.append(f"adjustment_basis_not_cash_executable:{basis}")
    if bool(policy.get("requires_complete_actions")) and coverage != "COMPLETE":
        semantic_blockers.append(f"corporate_action_coverage_incomplete:{coverage}")
    if coverage in OFFICIAL_CORPORATE_ACTION_AUTHORITIES and not official_verified:
        semantic_blockers.append("official_corporate_action_attestation_missing_or_invalid")
    if str(policy.get("dividend_mode") or "") == "EXPLICIT_PAY_DATE_CASH":
        semantic_blockers.extend(
            f"dividend_pay_date_missing:{item.get('event_date') or '--'}"
            for item in normalized_actions
            if item.get("action_type") == "DIVIDEND" and not item.get("pay_date")
        )
    semantic_blockers = list(dict.fromkeys(semantic_blockers))
    declared_value = evidence.get("blockers")
    declared_blockers = [str(item) for item in declared_value or [] if str(item)] if isinstance(declared_value, list) else []
    if not isinstance(declared_value, list):
        blockers.append("adjustment_declared_blockers_type_invalid")
    elif declared_blockers != semantic_blockers:
        blockers.append("adjustment_declared_blockers_semantic_mismatch")
    status = str(evidence.get("status") or "")
    backtest_eligible = evidence.get("backtest_eligible")
    if not isinstance(backtest_eligible, bool):
        blockers.append("adjustment_backtest_eligible_type_invalid")
    expected_status = (
        "PASS"
        if not semantic_blockers
        else "REVIEW"
        if all(item.startswith("adjustment_basis_unverified:") for item in semantic_blockers)
        else "BLOCK"
    )
    if status != expected_status:
        blockers.append("adjustment_status_semantic_mismatch")
    if backtest_eligible is not (not semantic_blockers):
        blockers.append("adjustment_backtest_eligibility_mismatch")
    if evidence.get("official_corporate_action_source_verified") is not official_verified:
        blockers.append("adjustment_official_source_flag_mismatch")
    expected_attestation_hash = str(attestation.get("attestation_hash") or "")
    if str(evidence.get("official_source_attestation_hash") or "") != expected_attestation_hash:
        blockers.append("adjustment_official_source_hash_mismatch")
    if coverage in OFFICIAL_CORPORATE_ACTION_AUTHORITIES and not official_verified:
        blockers.append("adjustment_official_source_not_verified")
    if (
        evidence.get("automatic_price_rewrite") is not False
        or evidence.get("research_only") is not True
        or evidence.get("paper_authorized") is not False
        or evidence.get("live_order_allowed") is not False
    ):
        blockers.append("adjustment_evidence_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "evidence_hash": expected_hash,
        "official_source_verified": official_verified and not blockers,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class CorporateActionLedger:
    """SQLite evidence ledger; it records provider facts and never rewrites candles."""

    def __init__(
        self,
        db_path: Path | str,
        now_ms: Callable[[], int],
        *,
        read_only: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.now_ms = now_ms
        self.read_only = bool(read_only)
        self._lock = threading.RLock()
        if not self.read_only:
            self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = connect_runtime_sqlite(self.db_path, read_only=self.read_only)
        connection.row_factory = sqlite3.Row
        if not self.read_only:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _ensure_schema(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS corporate_action_schema (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stock_corporate_actions (
                    action_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    observed_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_stock_actions_symbol_date
                    ON stock_corporate_actions(symbol, event_date DESC);
                CREATE TABLE IF NOT EXISTS stock_adjustment_evidence (
                    evidence_hash TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    session TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    observed_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_stock_evidence_latest
                    ON stock_adjustment_evidence(symbol, interval, session, observed_at DESC);
                """
            )
            connection.execute(
                "INSERT OR REPLACE INTO corporate_action_schema(key, value) VALUES('schema_version', ?)",
                (CORPORATE_ACTION_SCHEMA_VERSION,),
            )
            connection.commit()

    def record(
        self,
        *,
        symbol: str,
        provider: str,
        actions: list[dict[str, Any]] | None,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="corporate_action_ledger")
        normalized = normalize_corporate_actions(symbol, provider, actions)
        stamp = int(self.now_ms())
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            for action in normalized:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO stock_corporate_actions(
                        action_id, symbol, provider, action_type, event_date, observed_at, payload_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action["action_id"],
                        action["symbol"],
                        action["provider"],
                        action["action_type"],
                        action["event_date"],
                        stamp,
                        json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    ),
                )
            connection.execute(
                """
                INSERT OR IGNORE INTO stock_adjustment_evidence(
                    evidence_hash, symbol, interval, session, source, status, observed_at, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(evidence.get("evidence_hash") or _canonical_hash(evidence)),
                    str(evidence.get("symbol") or symbol).upper(),
                    str(evidence.get("interval") or "1d"),
                    str(evidence.get("session") or "regular"),
                    str(evidence.get("source") or provider),
                    str(evidence.get("status") or "REVIEW"),
                    stamp,
                    json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            connection.commit()
        return {
            "ok": True,
            "symbol": str(symbol or "").upper(),
            "action_count": len(normalized),
            "evidence_hash": str(evidence.get("evidence_hash") or ""),
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def actions(self, symbol: str) -> list[dict[str, Any]]:
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT payload_json FROM stock_corporate_actions WHERE symbol = ? ORDER BY event_date, action_id",
                (str(symbol or "").upper(),),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def latest_evidence(self, symbol: str, interval: str = "1d", session: str = "regular") -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM stock_adjustment_evidence
                WHERE symbol = ? AND interval = ? AND session = ?
                ORDER BY observed_at DESC, rowid DESC LIMIT 1
                """,
                (str(symbol or "").upper(), str(interval or "1d"), str(session or "regular")),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else {}

    def summary(self) -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            action_count = int(connection.execute("SELECT COUNT(*) FROM stock_corporate_actions").fetchone()[0])
            evidence_count = int(connection.execute("SELECT COUNT(*) FROM stock_adjustment_evidence").fetchone()[0])
            review_count = int(connection.execute(
                "SELECT COUNT(*) FROM stock_adjustment_evidence WHERE status != 'PASS'"
            ).fetchone()[0])
        return {
            "schema_version": CORPORATE_ACTION_SCHEMA_VERSION,
            "action_count": action_count,
            "evidence_count": evidence_count,
            "review_count": review_count,
            "path": str(self.db_path),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
