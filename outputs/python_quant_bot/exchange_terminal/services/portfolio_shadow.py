from __future__ import annotations

from contextlib import closing
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import threading
from typing import Any

from .trusted_clock import verify_trusted_clock_attestation


PORTFOLIO_SHADOW_SCHEMA_VERSION = "portfolio-shadow-observation-v7"
PORTFOLIO_FORWARD_STATE_SCHEMA_VERSION = "portfolio-forward-state-v1"
PORTFOLIO_FORWARD_STATUS_SCHEMA_VERSION = "portfolio-forward-status-v1"
LATEST_FORWARD_OBSERVATION_RECEIPT_SCHEMA_VERSION = "latest-forward-observation-receipt-v1"
FORWARD_OBSERVATION_CHANGE_SCHEMA_VERSION = "forward-observation-change-v1"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _market_decision_hash(observation: dict[str, Any]) -> str:
    return _canonical_hash({
        "candidate_hash": str(observation.get("candidate_hash") or ""),
        "signal_date": str(observation.get("signal_date") or ""),
        "dataset_hash": str(observation.get("dataset_hash") or ""),
        "dataset_last": str(observation.get("dataset_last") or ""),
        "forward_state_contract_hash": str(observation.get("forward_state_contract_hash") or ""),
        "decision": dict(observation.get("decision") or {}),
    })


def _payload_hash(payload: dict[str, Any], field: str) -> str:
    clean = dict(payload)
    clean.pop(field, None)
    return _canonical_hash(clean)


def _sha256_hex(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _decimal_text(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not result.is_finite():
        return None
    if result == 0:
        return "0"
    text = format(result.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _forward_change_projection_hash(projection: dict[str, Any]) -> str:
    return _canonical_hash({
        "candidate_hash": str(projection.get("candidate_hash") or ""),
        "signal_date": str(projection.get("signal_date") or ""),
        "observation_hash": str(projection.get("observation_hash") or ""),
        "target_symbols": list(projection.get("target_symbols") or []),
        "total_allocation_pct": str(projection.get("total_allocation_pct") or ""),
        "reason": str(projection.get("reason") or ""),
        "regime_id": str(projection.get("regime_id") or ""),
        "risk_gate_status": str(projection.get("risk_gate_status") or ""),
    })


def seal_forward_status_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    result = {
        **dict(payload),
        "schema_version": PORTFOLIO_FORWARD_STATUS_SCHEMA_VERSION,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    result.pop("artifact_hash", None)
    result["artifact_hash"] = _canonical_hash(result)
    return result


def verify_forward_status_artifact(
    payload: dict[str, Any],
    *,
    candidate_hash: str,
) -> dict[str, Any]:
    clean_candidate_hash = str(candidate_hash or "")
    artifact = dict(payload or {})
    blockers: list[str] = []
    if artifact.get("schema_version") != PORTFOLIO_FORWARD_STATUS_SCHEMA_VERSION:
        blockers.append("forward_status_schema_invalid")
    expected_hash = str(artifact.get("artifact_hash") or "")
    if not expected_hash or _payload_hash(artifact, "artifact_hash") != expected_hash:
        blockers.append("forward_status_artifact_hash_invalid")
    if not clean_candidate_hash or str(artifact.get("candidate_hash") or "") != clean_candidate_hash:
        blockers.append("forward_status_candidate_identity_mismatch")
    if (
        artifact.get("observation_only") is not True
        or artifact.get("simulation_only") is not True
        or artifact.get("paper_authorized") is not False
        or artifact.get("live_order_allowed") is not False
    ):
        blockers.append("forward_status_execution_authority_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "candidate_hash": clean_candidate_hash,
        "artifact_hash": expected_hash,
        "blockers": blockers,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _strict_date(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) != 10:
        return ""
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return ""


def build_incremental_observation_plan(
    *,
    candidate_hash: str,
    all_dates: list[str],
    frozen_last: str,
    recorded_dates: list[str],
    classified_dates: list[str],
    ledger_audit: dict[str, Any],
    data_revision_evidence: dict[str, Any],
    replay_recorded: bool = False,
) -> dict[str, Any]:
    """Select incremental forward dates without trusting unverified ledger or revision state."""
    blockers: list[str] = []
    warnings: list[str] = []
    clean_candidate_hash = str(candidate_hash or "").strip()
    clean_frozen_last = _strict_date(frozen_last)
    if not clean_candidate_hash:
        blockers.append("candidate_hash_missing")
    if not clean_frozen_last:
        blockers.append("frozen_last_invalid")

    def normalize_dates(values: list[str], label: str) -> list[str]:
        clean: list[str] = []
        invalid: list[str] = []
        for value in values:
            parsed = _strict_date(value)
            if parsed:
                clean.append(parsed)
            else:
                invalid.append(str(value or ""))
        if invalid:
            blockers.append(f"{label}_dates_invalid")
        if len(clean) != len(set(clean)):
            blockers.append(f"{label}_date_identity_duplicate")
        return list(dict.fromkeys(clean))

    normalized_dates = normalize_dates(all_dates, "dataset")
    normalized_recorded = normalize_dates(recorded_dates, "recorded")
    normalized_classified = normalize_dates(classified_dates, "classified")
    eligible_dates = [item for item in normalized_dates if clean_frozen_last and item > clean_frozen_last]
    eligible_set = set(eligible_dates)
    recorded_set = set(normalized_recorded)
    classified_set = set(normalized_classified)

    identity_overlap = sorted(recorded_set.intersection(classified_set))
    if identity_overlap:
        blockers.extend(f"ledger_date_identity_conflict:{item}" for item in identity_overlap)
    pre_frozen = sorted(
        item for item in recorded_set.union(classified_set)
        if clean_frozen_last and item <= clean_frozen_last
    )
    if pre_frozen:
        blockers.extend(f"ledger_date_not_forward:{item}" for item in pre_frozen)
    missing_from_dataset = sorted(
        item for item in recorded_set.union(classified_set)
        if item not in eligible_set
    )
    if missing_from_dataset:
        blockers.extend(f"ledger_date_missing_from_current_dataset:{item}" for item in missing_from_dataset)

    audit_status = str(ledger_audit.get("status") or "MISSING").upper()
    audit_candidate_hash = str(ledger_audit.get("candidate_hash") or "")
    if audit_status != "PASS":
        blockers.append(f"ledger_audit_not_pass:{audit_status}")
    if audit_candidate_hash != clean_candidate_hash:
        blockers.append("ledger_audit_candidate_identity_mismatch")

    revisions = data_revision_evidence if isinstance(data_revision_evidence, dict) else {}
    if not revisions:
        blockers.append("data_revision_evidence_missing")
    for symbol, raw_revision in sorted(revisions.items()):
        clean_symbol = str(symbol or "").strip().upper()
        if not clean_symbol or not isinstance(raw_revision, dict):
            blockers.append(f"data_revision_evidence_invalid:{clean_symbol or 'UNKNOWN'}")
            continue
        revision = dict(raw_revision)
        revision_status = str(revision.get("status") or "MISSING").upper()
        if not revision.get("evidence_hash"):
            blockers.append(f"data_revision_evidence_hash_missing:{clean_symbol}")
        if revision_status != "PASS":
            if replay_recorded and revision_status == "REVIEW":
                warnings.append(f"data_revision_review_audit_replay:{clean_symbol}")
            else:
                blockers.append(f"data_revision_not_pass:{clean_symbol}:{revision_status}")
        cross_source = revision.get("cross_source") or []
        if not isinstance(cross_source, list):
            blockers.append(f"data_revision_cross_source_invalid:{clean_symbol}")
            continue
        for index, raw_cross_source in enumerate(cross_source):
            if not isinstance(raw_cross_source, dict):
                blockers.append(f"data_revision_cross_source_invalid:{clean_symbol}:{index}")
                continue
            cross_status = str(raw_cross_source.get("status") or "MISSING").upper()
            if cross_status != "PASS":
                if replay_recorded and cross_status == "REVIEW":
                    warnings.append(f"cross_source_review_audit_replay:{clean_symbol}:{index}")
                else:
                    blockers.append(f"cross_source_not_pass:{clean_symbol}:{index}:{cross_status}")

    if blockers:
        processing_dates: list[str] = []
    elif replay_recorded:
        processing_dates = [item for item in eligible_dates if item in recorded_set]
    else:
        processing_dates = [
            item for item in eligible_dates
            if item not in recorded_set and item not in classified_set
        ]

    skipped_recorded_dates = [] if replay_recorded else [
        item for item in eligible_dates if item in recorded_set
    ]
    skipped_classified_dates = [item for item in eligible_dates if item in classified_set]
    deferred_unrecorded_dates = [
        item for item in eligible_dates
        if replay_recorded and item not in recorded_set and item not in classified_set
    ]
    result = {
        "status": "BLOCK" if blockers else "PASS",
        "mode": "AUDIT_REPLAY" if replay_recorded else "INCREMENTAL",
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": list(dict.fromkeys(warnings)),
        "candidate_hash": clean_candidate_hash,
        "frozen_last": clean_frozen_last,
        "eligible_dates": eligible_dates,
        "processing_dates": processing_dates,
        "skipped_recorded_dates": skipped_recorded_dates,
        "skipped_classified_dates": skipped_classified_dates,
        "deferred_unrecorded_dates": deferred_unrecorded_dates,
        "ledger_audit_status": audit_status,
        "ledger_audit_hash": _canonical_hash(dict(ledger_audit or {})),
        "data_revision_evidence_hash": _canonical_hash(revisions) if revisions else "",
        "replay_recorded": replay_recorded is True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    result["plan_hash"] = _canonical_hash(result)
    return result


def _strict_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _strict_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _risk_snapshot_contract_blockers(observation: Any) -> list[str]:
    payload = dict(observation) if isinstance(observation, dict) else {}
    raw_snapshot = payload.get("risk_snapshot")
    if not isinstance(raw_snapshot, dict):
        return ["observation_risk_snapshot_invalid"]
    snapshot = dict(raw_snapshot)
    blockers: list[str] = []
    risk_status = snapshot.get("status")
    if risk_status not in {"PASS", "BLOCK"}:
        blockers.append("observation_risk_status_invalid")
    if payload.get("risk_gate_status") != risk_status:
        blockers.append("observation_risk_gate_status_mismatch")
    inner_hash = str(snapshot.get("risk_snapshot_hash") or "")
    outer_hash = str(payload.get("risk_snapshot_hash") or "")
    if outer_hash != inner_hash:
        blockers.append("observation_risk_snapshot_hash_reference_mismatch")
    if not _sha256_hex(inner_hash) or inner_hash != _payload_hash(snapshot, "risk_snapshot_hash"):
        blockers.append("observation_risk_snapshot_hash_invalid")
    return blockers


def _decision_projection_blockers(observation: Any) -> list[str]:
    payload = dict(observation) if isinstance(observation, dict) else {}
    raw_decision = payload.get("decision")
    if not isinstance(raw_decision, dict):
        return ["observation_decision_invalid"]
    decision = dict(raw_decision)
    blockers: list[str] = []
    if str(payload.get("signal_date") or "") != str(decision.get("signal_date") or ""):
        blockers.append("observation_decision_signal_date_mismatch")
    target_symbols = decision.get("target_symbols")
    if not isinstance(target_symbols, list) or payload.get("target_symbols") != target_symbols:
        blockers.append("observation_decision_target_symbols_mismatch")
    target_weights = decision.get("target_weights")
    if not isinstance(target_weights, dict) or payload.get("target_weights") != target_weights:
        blockers.append("observation_decision_target_weights_mismatch")
    expected_allocation = _strict_number(decision.get("target_allocation_pct"))
    actual_allocation = _strict_number(payload.get("target_allocation_pct"))
    if expected_allocation is None:
        expected_allocation = 0.0 if decision.get("target_allocation_pct") is None else None
    if actual_allocation is None or expected_allocation is None or actual_allocation != expected_allocation:
        blockers.append("observation_decision_target_allocation_mismatch")
    if str(payload.get("reason") or "") != str(decision.get("reason") or ""):
        blockers.append("observation_decision_reason_mismatch")
    regime = decision.get("regime")
    if regime is None:
        regime = {}
    if not isinstance(regime, dict):
        blockers.append("observation_decision_regime_invalid")
        regime = {}
    if str(payload.get("regime_id") or "") != str(regime.get("regime_id") or ""):
        blockers.append("observation_decision_regime_mismatch")
    expected_volatility = _strict_number(decision.get("estimated_portfolio_volatility_pct"))
    actual_volatility = _strict_number(payload.get("estimated_portfolio_volatility_pct"))
    if expected_volatility is None:
        expected_volatility = 0.0 if decision.get("estimated_portfolio_volatility_pct") is None else None
    if actual_volatility is None or expected_volatility is None or actual_volatility != expected_volatility:
        blockers.append("observation_decision_volatility_mismatch")
    return blockers


def build_latest_forward_observation_receipt(
    observation: Any,
    *,
    ledger_audit: Any,
) -> dict[str, Any]:
    """Project the newest audited observation into a small, sealed read-only receipt."""

    source = dict(observation) if isinstance(observation, dict) else {}
    audit = dict(ledger_audit) if isinstance(ledger_audit, dict) else {}
    blockers: list[str] = []
    candidate_hash = str(source.get("candidate_hash") or "")
    signal_date = _strict_date(source.get("signal_date"))
    audit_last_signal_date = _strict_date(audit.get("last_signal_date"))
    observed_at = _strict_integer(source.get("observed_at"))
    allocation = _strict_number(source.get("target_allocation_pct"))
    target_symbols_raw = source.get("target_symbols")
    target_symbols = (
        [str(item) for item in target_symbols_raw]
        if isinstance(target_symbols_raw, list)
        and all(isinstance(item, str) and item for item in target_symbols_raw)
        else []
    )

    if not source:
        blockers.append("latest_observation_missing")
    if source.get("schema_version") != PORTFOLIO_SHADOW_SCHEMA_VERSION:
        blockers.append("latest_observation_schema_invalid")
    if source.get("status") != "READY":
        blockers.append("latest_observation_status_invalid")
    if not candidate_hash or str(audit.get("candidate_hash") or "") != candidate_hash:
        blockers.append("latest_observation_candidate_identity_mismatch")
    if str(audit.get("status") or "").upper() != "PASS":
        blockers.append("latest_observation_ledger_audit_not_pass")
    if not signal_date or not audit_last_signal_date or signal_date != audit_last_signal_date:
        blockers.append("latest_observation_ledger_date_mismatch")
    if observed_at is None or observed_at <= 0:
        blockers.append("latest_observation_observed_at_invalid")
    if not isinstance(target_symbols_raw, list) or len(target_symbols) != len(target_symbols_raw):
        blockers.append("latest_observation_target_symbols_invalid")
    if allocation is None or allocation < 0 or allocation > 100:
        blockers.append("latest_observation_target_allocation_invalid")
    decision_hash = str(source.get("decision_hash") or "")
    market_decision_hash = str(source.get("market_decision_hash") or "")
    if not decision_hash or decision_hash != market_decision_hash or decision_hash != _market_decision_hash(source):
        blockers.append("latest_observation_decision_hash_invalid")
    observation_hash = str(source.get("observation_hash") or "")
    if not observation_hash or observation_hash != _payload_hash(source, "observation_hash"):
        blockers.append("latest_observation_hash_invalid")
    blockers.extend(_risk_snapshot_contract_blockers(source))
    blockers.extend(_decision_projection_blockers(source))
    for source_field, audit_field in (
        ("dataset_hash", "latest_dataset_hash"),
        ("decision_hash", "latest_decision_hash"),
        ("observation_hash", "latest_observation_hash"),
        ("forward_state_contract_hash", "latest_forward_state_contract_hash"),
        ("risk_snapshot_hash", "latest_observation_risk_snapshot_hash"),
    ):
        if str(source.get(source_field) or "") != str(audit.get(audit_field) or ""):
            blockers.append(f"latest_observation_audit_{source_field}_mismatch")
    if (
        source.get("observation_only") is not True
        or source.get("paper_authorized") is not False
        or source.get("live_order_allowed") is not False
    ):
        blockers.append("latest_observation_execution_authority_invalid")

    receipt = {
        "schema_version": LATEST_FORWARD_OBSERVATION_RECEIPT_SCHEMA_VERSION,
        "status": "VERIFIED" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_hash": candidate_hash,
        "signal_date": signal_date,
        "observed_at": observed_at if observed_at is not None and observed_at > 0 else 0,
        "dataset_hash": str(source.get("dataset_hash") or ""),
        "dataset_last": str(source.get("dataset_last") or ""),
        "target_symbols": target_symbols,
        "target_allocation_pct": allocation if allocation is not None else None,
        "reason": str(source.get("reason") or ""),
        "risk_gate_status": str(source.get("risk_gate_status") or ""),
        "risk_snapshot_hash": str(source.get("risk_snapshot_hash") or ""),
        "decision_hash": decision_hash,
        "observation_hash": observation_hash,
        "forward_state_contract_hash": str(source.get("forward_state_contract_hash") or ""),
        "ledger_audit_hash": _canonical_hash(audit) if audit else "",
        "record_status": "VERIFIED_LEDGER_OBSERVATION" if not blockers else "BLOCK",
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    receipt["receipt_hash"] = _payload_hash(receipt, "receipt_hash")
    return receipt


def verify_latest_forward_observation_receipt(
    receipt: Any,
    *,
    candidate_hash: str,
    expected_signal_date: str = "",
    ledger_audit: Any = None,
) -> dict[str, Any]:
    """Verify receipt identity, authority and hashes without reading the ledger."""

    payload = dict(receipt) if isinstance(receipt, dict) else {}
    audit = dict(ledger_audit) if isinstance(ledger_audit, dict) else {}
    clean_candidate_hash = str(candidate_hash or "")
    clean_expected_date = _strict_date(expected_signal_date)
    blockers: list[str] = []
    if not payload:
        return {
            "status": "NOT_CHECKED",
            "blockers": [],
            "receipt": {},
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if payload.get("schema_version") != LATEST_FORWARD_OBSERVATION_RECEIPT_SCHEMA_VERSION:
        blockers.append("latest_observation_receipt_schema_invalid")
    if payload.get("status") != "VERIFIED" or payload.get("record_status") != "VERIFIED_LEDGER_OBSERVATION":
        blockers.append("latest_observation_receipt_status_invalid")
    if payload.get("blockers") != []:
        blockers.append("latest_observation_receipt_reports_blockers")
    if not clean_candidate_hash or str(payload.get("candidate_hash") or "") != clean_candidate_hash:
        blockers.append("latest_observation_receipt_candidate_mismatch")
    signal_date = _strict_date(payload.get("signal_date"))
    if not signal_date:
        blockers.append("latest_observation_receipt_date_invalid")
    if clean_expected_date and signal_date != clean_expected_date:
        blockers.append("latest_observation_receipt_ledger_date_mismatch")
    observed_at = _strict_integer(payload.get("observed_at"))
    if observed_at is None or observed_at <= 0:
        blockers.append("latest_observation_receipt_observed_at_invalid")
    target_symbols = payload.get("target_symbols")
    if not isinstance(target_symbols, list) or any(not isinstance(item, str) or not item for item in target_symbols):
        blockers.append("latest_observation_receipt_target_symbols_invalid")
    allocation = _strict_number(payload.get("target_allocation_pct"))
    if allocation is None or allocation < 0 or allocation > 100:
        blockers.append("latest_observation_receipt_target_allocation_invalid")
    if not _sha256_hex(payload.get("decision_hash")):
        blockers.append("latest_observation_receipt_decision_hash_invalid")
    if not _sha256_hex(payload.get("observation_hash")):
        blockers.append("latest_observation_receipt_observation_hash_invalid")
    if not _sha256_hex(payload.get("forward_state_contract_hash")):
        blockers.append("latest_observation_receipt_forward_state_hash_invalid")
    risk_snapshot_hash = str(payload.get("risk_snapshot_hash") or "")
    if not _sha256_hex(risk_snapshot_hash):
        blockers.append("latest_observation_receipt_risk_hash_invalid")
    if (
        payload.get("observation_only") is not True
        or payload.get("simulation_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("latest_observation_receipt_execution_authority_invalid")
    expected_receipt_hash = str(payload.get("receipt_hash") or "")
    if not _sha256_hex(expected_receipt_hash) or expected_receipt_hash != _payload_hash(payload, "receipt_hash"):
        blockers.append("latest_observation_receipt_hash_invalid")
    if audit:
        if str(audit.get("status") or "").upper() != "PASS":
            blockers.append("latest_observation_receipt_ledger_audit_not_pass")
        if str(audit.get("candidate_hash") or "") != clean_candidate_hash:
            blockers.append("latest_observation_receipt_ledger_candidate_mismatch")
        audit_last_signal_date = _strict_date(audit.get("last_signal_date"))
        if not audit_last_signal_date or audit_last_signal_date != signal_date:
            blockers.append("latest_observation_receipt_ledger_audit_date_mismatch")
        for receipt_field, audit_field in (
            ("dataset_hash", "latest_dataset_hash"),
            ("decision_hash", "latest_decision_hash"),
            ("observation_hash", "latest_observation_hash"),
            ("forward_state_contract_hash", "latest_forward_state_contract_hash"),
            ("risk_snapshot_hash", "latest_observation_risk_snapshot_hash"),
        ):
            if str(payload.get(receipt_field) or "") != str(audit.get(audit_field) or ""):
                blockers.append(f"latest_observation_receipt_ledger_{receipt_field}_mismatch")
        if (
            not _sha256_hex(payload.get("ledger_audit_hash"))
            or str(payload.get("ledger_audit_hash") or "") != _canonical_hash(audit)
        ):
            blockers.append("latest_observation_receipt_ledger_audit_hash_invalid")
    else:
        blockers.append("latest_observation_receipt_ledger_audit_missing")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "receipt": payload if not blockers else {},
        "receipt_hash": expected_receipt_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verified_observation_chain(
    ledger_audit: Any,
    *,
    candidate_hash: str,
) -> tuple[list[dict[str, str]], list[str]]:
    audit = dict(ledger_audit) if isinstance(ledger_audit, dict) else {}
    blockers: list[str] = []
    raw_chain = audit.get("observation_chain")
    chain: list[dict[str, str]] = []
    if not isinstance(raw_chain, list):
        blockers.append("forward_observation_chain_invalid")
        raw_chain = []
    for item in raw_chain:
        if not isinstance(item, dict) or set(item) != {
            "signal_date",
            "observation_hash",
            "change_projection_hash",
        }:
            blockers.append("forward_observation_chain_entry_invalid")
            continue
        signal_date = _strict_date(item.get("signal_date"))
        observation_hash = str(item.get("observation_hash") or "")
        change_projection_hash = str(item.get("change_projection_hash") or "")
        if not signal_date or not _sha256_hex(observation_hash) or not _sha256_hex(change_projection_hash):
            blockers.append("forward_observation_chain_entry_invalid")
            continue
        chain.append({
            "signal_date": signal_date,
            "observation_hash": observation_hash,
            "change_projection_hash": change_projection_hash,
        })
    if len(chain) != len(raw_chain):
        blockers.append("forward_observation_chain_entry_invalid")
    dates = [item["signal_date"] for item in chain]
    if dates != sorted(set(dates)):
        blockers.append("forward_observation_chain_order_invalid")
    chain_count = _strict_integer(audit.get("observation_chain_count"))
    if chain_count is None or chain_count != len(chain):
        blockers.append("forward_observation_chain_count_invalid")
    chain_hash = str(audit.get("observation_chain_hash") or "")
    if not _sha256_hex(chain_hash) or chain_hash != _canonical_hash(chain):
        blockers.append("forward_observation_chain_hash_invalid")
    if str(audit.get("status") or "").upper() != "PASS":
        blockers.append("forward_observation_ledger_audit_not_pass")
    if not candidate_hash or str(audit.get("candidate_hash") or "") != candidate_hash:
        blockers.append("forward_observation_ledger_candidate_mismatch")
    if chain:
        if _strict_date(audit.get("last_signal_date")) != chain[-1]["signal_date"]:
            blockers.append("forward_observation_chain_latest_date_mismatch")
        if str(audit.get("latest_observation_hash") or "") != chain[-1]["observation_hash"]:
            blockers.append("forward_observation_chain_latest_hash_mismatch")
    elif str(audit.get("last_signal_date") or "") or str(audit.get("latest_observation_hash") or ""):
        blockers.append("forward_observation_chain_empty_latest_mismatch")
    return chain, list(dict.fromkeys(blockers))


def _forward_change_source(
    observation: Any,
    *,
    candidate_hash: str,
    label: str,
) -> tuple[dict[str, Any], list[str]]:
    source = dict(observation) if isinstance(observation, dict) else {}
    blockers: list[str] = []
    if not source:
        return {}, [f"forward_observation_change_{label}_missing"]
    if source.get("schema_version") != PORTFOLIO_SHADOW_SCHEMA_VERSION or source.get("status") != "READY":
        blockers.append(f"forward_observation_change_{label}_status_invalid")
    if str(source.get("candidate_hash") or "") != candidate_hash:
        blockers.append(f"forward_observation_change_{label}_candidate_mismatch")
    signal_date = _strict_date(source.get("signal_date"))
    if not signal_date:
        blockers.append(f"forward_observation_change_{label}_date_invalid")
    observed_at = _strict_integer(source.get("observed_at"))
    if observed_at is None or observed_at <= 0:
        blockers.append(f"forward_observation_change_{label}_observed_at_invalid")
    decision_hash = str(source.get("decision_hash") or "")
    if (
        not _sha256_hex(decision_hash)
        or decision_hash != str(source.get("market_decision_hash") or "")
        or decision_hash != _market_decision_hash(source)
    ):
        blockers.append(f"forward_observation_change_{label}_decision_hash_invalid")
    observation_hash = str(source.get("observation_hash") or "")
    if not _sha256_hex(observation_hash) or observation_hash != _payload_hash(source, "observation_hash"):
        blockers.append(f"forward_observation_change_{label}_observation_hash_invalid")
    blockers.extend(
        f"forward_observation_change_{label}:{item}"
        for item in _decision_projection_blockers(source)
    )
    blockers.extend(
        f"forward_observation_change_{label}:{item}"
        for item in _risk_snapshot_contract_blockers(source)
    )
    raw_symbols = source.get("target_symbols")
    symbols = (
        list(raw_symbols)
        if isinstance(raw_symbols, list)
        and all(isinstance(item, str) and bool(item) for item in raw_symbols)
        else []
    )
    if not isinstance(raw_symbols, list) or len(symbols) != len(raw_symbols) or len(set(symbols)) != len(symbols):
        blockers.append(f"forward_observation_change_{label}_target_symbols_invalid")
    allocation = _strict_number(source.get("target_allocation_pct"))
    allocation_text = _decimal_text(source.get("target_allocation_pct"))
    if allocation is None or allocation_text is None or allocation < 0 or allocation > 100:
        blockers.append(f"forward_observation_change_{label}_allocation_invalid")
    risk_status = str(source.get("risk_gate_status") or "")
    if risk_status not in {"PASS", "BLOCK"}:
        blockers.append(f"forward_observation_change_{label}_risk_status_invalid")
    if (
        source.get("observation_only") is not True
        or source.get("paper_authorized") is not False
        or source.get("live_order_allowed") is not False
    ):
        blockers.append(f"forward_observation_change_{label}_execution_authority_invalid")
    projection = {
        "candidate_hash": str(source.get("candidate_hash") or ""),
        "signal_date": signal_date,
        "observation_hash": observation_hash,
        "target_symbols": symbols,
        "total_allocation_pct": allocation_text,
        "reason": str(source.get("reason") or ""),
        "regime_id": str(source.get("regime_id") or ""),
        "risk_gate_status": risk_status,
    }
    projection["change_projection_hash"] = _forward_change_projection_hash(projection)
    return projection, list(dict.fromkeys(blockers))


def _empty_forward_change_claims() -> dict[str, Any]:
    return {
        "target_set": {
            "changed": None,
            "before": [],
            "after": [],
            "added": [],
            "removed": [],
            "retained": [],
        },
        "total_allocation_pct": {"before": None, "after": None, "delta": None},
        "reason": {"before": "", "after": "", "changed": None},
        "regime_id": {"before": "", "after": "", "changed": None},
        "risk_gate_status": {"before": "", "after": "", "changed": None},
    }


def build_forward_observation_change(
    previous_observation: Any,
    current_observation: Any,
    *,
    ledger_audit: Any,
) -> dict[str, Any]:
    """Seal a descriptive diff of the latest two consecutive audited observations."""

    audit = dict(ledger_audit) if isinstance(ledger_audit, dict) else {}
    candidate_hash = str(audit.get("candidate_hash") or "")
    chain, blockers = _verified_observation_chain(audit, candidate_hash=candidate_hash)
    previous: dict[str, Any] = {}
    current: dict[str, Any] = {}
    claims = _empty_forward_change_claims()

    if len(chain) == 0:
        if previous_observation is not None or current_observation is not None:
            blockers.append("forward_observation_change_query_count_mismatch")
    elif len(chain) == 1:
        if previous_observation is not None:
            blockers.append("forward_observation_change_previous_unexpected")
        current, current_blockers = _forward_change_source(
            current_observation,
            candidate_hash=candidate_hash,
            label="current",
        )
        blockers.extend(current_blockers)
        if current and {
            "signal_date": current.get("signal_date"),
            "observation_hash": current.get("observation_hash"),
            "change_projection_hash": current.get("change_projection_hash"),
        } != chain[0]:
            blockers.append("forward_observation_change_current_chain_mismatch")
    else:
        previous, previous_blockers = _forward_change_source(
            previous_observation,
            candidate_hash=candidate_hash,
            label="previous",
        )
        current, current_blockers = _forward_change_source(
            current_observation,
            candidate_hash=candidate_hash,
            label="current",
        )
        blockers.extend(previous_blockers)
        blockers.extend(current_blockers)
        previous_reference = {
            "signal_date": previous.get("signal_date"),
            "observation_hash": previous.get("observation_hash"),
            "change_projection_hash": previous.get("change_projection_hash"),
        }
        current_reference = {
            "signal_date": current.get("signal_date"),
            "observation_hash": current.get("observation_hash"),
            "change_projection_hash": current.get("change_projection_hash"),
        }
        if previous_reference != chain[-2]:
            blockers.append("forward_observation_change_previous_chain_mismatch")
        if current_reference != chain[-1]:
            blockers.append("forward_observation_change_current_chain_mismatch")
        if previous.get("signal_date") and current.get("signal_date") and previous["signal_date"] >= current["signal_date"]:
            blockers.append("forward_observation_change_date_order_invalid")
        if not blockers:
            before_symbols = list(previous["target_symbols"])
            after_symbols = list(current["target_symbols"])
            before_set = set(before_symbols)
            after_set = set(after_symbols)
            before_allocation = Decimal(str(previous["total_allocation_pct"]))
            after_allocation = Decimal(str(current["total_allocation_pct"]))
            claims = {
                "target_set": {
                    "changed": before_set != after_set,
                    "before": before_symbols,
                    "after": after_symbols,
                    "added": sorted(after_set - before_set),
                    "removed": sorted(before_set - after_set),
                    "retained": sorted(before_set & after_set),
                },
                "total_allocation_pct": {
                    "before": previous["total_allocation_pct"],
                    "after": current["total_allocation_pct"],
                    "delta": _decimal_text(after_allocation - before_allocation),
                },
                "reason": {
                    "before": previous["reason"],
                    "after": current["reason"],
                    "changed": previous["reason"] != current["reason"],
                },
                "regime_id": {
                    "before": previous["regime_id"],
                    "after": current["regime_id"],
                    "changed": previous["regime_id"] != current["regime_id"],
                },
                "risk_gate_status": {
                    "before": previous["risk_gate_status"],
                    "after": current["risk_gate_status"],
                    "changed": previous["risk_gate_status"] != current["risk_gate_status"],
                },
            }

    clean_blockers = list(dict.fromkeys(blockers))
    status = "BLOCK" if clean_blockers else "VERIFIED" if len(chain) >= 2 else "NOT_ENOUGH_OBSERVATIONS"
    result = {
        "schema_version": FORWARD_OBSERVATION_CHANGE_SCHEMA_VERSION,
        "status": status,
        "blockers": clean_blockers,
        "candidate_hash": candidate_hash,
        "basis": "LATEST_TWO_CONSECUTIVE_AUDITED_LEDGER_OBSERVATIONS",
        "previous": (
            {
                "signal_date": previous.get("signal_date"),
                "observation_hash": previous.get("observation_hash"),
                "change_projection_hash": previous.get("change_projection_hash"),
            }
            if previous
            else {}
        ),
        "current": (
            {
                "signal_date": current.get("signal_date"),
                "observation_hash": current.get("observation_hash"),
                "change_projection_hash": current.get("change_projection_hash"),
            }
            if current
            else {}
        ),
        **claims,
        "evidence": {
            "ledger_audit_hash": _canonical_hash(audit) if audit else "",
            "observation_chain_hash": str(audit.get("observation_chain_hash") or ""),
            "observation_chain_count": _strict_integer(audit.get("observation_chain_count")),
            "pair_consecutive": status == "VERIFIED",
        },
        "descriptive_only": True,
        "direction_signal_allowed": False,
        "performance_claim_allowed": False,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    result["change_hash"] = _payload_hash(result, "change_hash")
    return result


def verify_forward_observation_change(
    change: Any,
    *,
    candidate_hash: str,
    expected_current_signal_date: str = "",
    ledger_audit: Any = None,
) -> dict[str, Any]:
    """Verify the sealed change without reading market data or the ledger."""

    payload = dict(change) if isinstance(change, dict) else {}
    if not payload:
        return {
            "status": "NOT_CHECKED",
            "blockers": [],
            "change": {},
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    audit = dict(ledger_audit) if isinstance(ledger_audit, dict) else {}
    clean_candidate_hash = str(candidate_hash or "")
    blockers: list[str] = []
    if payload.get("schema_version") != FORWARD_OBSERVATION_CHANGE_SCHEMA_VERSION:
        blockers.append("forward_observation_change_schema_invalid")
    change_status = str(payload.get("status") or "")
    if change_status not in {"VERIFIED", "NOT_ENOUGH_OBSERVATIONS"}:
        blockers.append("forward_observation_change_status_invalid")
    if payload.get("blockers") != []:
        blockers.append("forward_observation_change_reports_blockers")
    if not clean_candidate_hash or str(payload.get("candidate_hash") or "") != clean_candidate_hash:
        blockers.append("forward_observation_change_candidate_mismatch")
    if payload.get("basis") != "LATEST_TWO_CONSECUTIVE_AUDITED_LEDGER_OBSERVATIONS":
        blockers.append("forward_observation_change_basis_invalid")
    if (
        payload.get("descriptive_only") is not True
        or payload.get("direction_signal_allowed") is not False
        or payload.get("performance_claim_allowed") is not False
        or payload.get("observation_only") is not True
        or payload.get("simulation_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("forward_observation_change_execution_authority_invalid")
    expected_change_hash = str(payload.get("change_hash") or "")
    if not _sha256_hex(expected_change_hash) or expected_change_hash != _payload_hash(payload, "change_hash"):
        blockers.append("forward_observation_change_hash_invalid")

    chain, chain_blockers = _verified_observation_chain(audit, candidate_hash=clean_candidate_hash)
    blockers.extend(chain_blockers)
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
        blockers.append("forward_observation_change_evidence_invalid")
    if (
        not _sha256_hex(evidence.get("ledger_audit_hash"))
        or str(evidence.get("ledger_audit_hash") or "") != _canonical_hash(audit)
    ):
        blockers.append("forward_observation_change_ledger_audit_hash_invalid")
    if str(evidence.get("observation_chain_hash") or "") != str(audit.get("observation_chain_hash") or ""):
        blockers.append("forward_observation_change_chain_hash_mismatch")
    if _strict_integer(evidence.get("observation_chain_count")) != len(chain):
        blockers.append("forward_observation_change_chain_count_mismatch")

    previous = payload.get("previous")
    current = payload.get("current")
    if not isinstance(previous, dict) or not isinstance(current, dict):
        blockers.append("forward_observation_change_pair_invalid")
        previous = {}
        current = {}
    clean_expected_date = _strict_date(expected_current_signal_date)
    if expected_current_signal_date and not clean_expected_date:
        blockers.append("forward_observation_change_expected_date_invalid")

    if change_status == "VERIFIED":
        if len(chain) < 2 or evidence.get("pair_consecutive") is not True:
            blockers.append("forward_observation_change_pair_not_consecutive")
        else:
            if previous != chain[-2]:
                blockers.append("forward_observation_change_previous_chain_mismatch")
            if current != chain[-1]:
                blockers.append("forward_observation_change_current_chain_mismatch")
        if clean_expected_date and _strict_date(current.get("signal_date")) != clean_expected_date:
            blockers.append("forward_observation_change_current_date_mismatch")

        target_set = payload.get("target_set")
        if not isinstance(target_set, dict):
            target_set = {}
            blockers.append("forward_observation_change_target_set_invalid")
        symbol_lists: dict[str, list[str]] = {}
        for field in ("before", "after", "added", "removed", "retained"):
            raw_symbols = target_set.get(field)
            if (
                not isinstance(raw_symbols, list)
                or any(not isinstance(item, str) or not item for item in raw_symbols)
                or len(set(raw_symbols)) != len(raw_symbols)
            ):
                blockers.append(f"forward_observation_change_target_{field}_invalid")
                symbol_lists[field] = []
            else:
                symbol_lists[field] = list(raw_symbols)
        before_set = set(symbol_lists["before"])
        after_set = set(symbol_lists["after"])
        if target_set.get("changed") is not (before_set != after_set):
            blockers.append("forward_observation_change_target_changed_invalid")
        if symbol_lists["added"] != sorted(after_set - before_set):
            blockers.append("forward_observation_change_target_added_invalid")
        if symbol_lists["removed"] != sorted(before_set - after_set):
            blockers.append("forward_observation_change_target_removed_invalid")
        if symbol_lists["retained"] != sorted(before_set & after_set):
            blockers.append("forward_observation_change_target_retained_invalid")

        allocation = payload.get("total_allocation_pct")
        if not isinstance(allocation, dict):
            allocation = {}
            blockers.append("forward_observation_change_allocation_invalid")
        before_text = allocation.get("before")
        after_text = allocation.get("after")
        delta_text = allocation.get("delta")
        canonical_before = _decimal_text(before_text)
        canonical_after = _decimal_text(after_text)
        canonical_delta = _decimal_text(delta_text)
        if (
            not isinstance(before_text, str)
            or not isinstance(after_text, str)
            or not isinstance(delta_text, str)
            or canonical_before != before_text
            or canonical_after != after_text
            or canonical_delta != delta_text
        ):
            blockers.append("forward_observation_change_allocation_decimal_invalid")
        else:
            before_decimal = Decimal(before_text)
            after_decimal = Decimal(after_text)
            if before_decimal < 0 or before_decimal > 100 or after_decimal < 0 or after_decimal > 100:
                blockers.append("forward_observation_change_allocation_range_invalid")
            if _decimal_text(after_decimal - before_decimal) != delta_text:
                blockers.append("forward_observation_change_allocation_delta_invalid")

        for field in ("reason", "regime_id", "risk_gate_status"):
            transition = payload.get(field)
            if not isinstance(transition, dict):
                blockers.append(f"forward_observation_change_{field}_invalid")
                continue
            before_value = transition.get("before")
            after_value = transition.get("after")
            if not isinstance(before_value, str) or not isinstance(after_value, str):
                blockers.append(f"forward_observation_change_{field}_value_invalid")
            if transition.get("changed") is not (before_value != after_value):
                blockers.append(f"forward_observation_change_{field}_changed_invalid")
            if field == "risk_gate_status" and (
                before_value not in {"PASS", "BLOCK"} or after_value not in {"PASS", "BLOCK"}
            ):
                blockers.append("forward_observation_change_risk_status_invalid")
        reason_transition = payload.get("reason")
        regime_transition = payload.get("regime_id")
        risk_transition = payload.get("risk_gate_status")
        projection_claims_valid = (
            isinstance(reason_transition, dict)
            and isinstance(regime_transition, dict)
            and isinstance(risk_transition, dict)
            and isinstance(reason_transition.get("before"), str)
            and isinstance(reason_transition.get("after"), str)
            and isinstance(regime_transition.get("before"), str)
            and isinstance(regime_transition.get("after"), str)
            and risk_transition.get("before") in {"PASS", "BLOCK"}
            and risk_transition.get("after") in {"PASS", "BLOCK"}
            and isinstance(before_text, str)
            and isinstance(after_text, str)
            and canonical_before == before_text
            and canonical_after == after_text
        )
        if projection_claims_valid:
            previous_projection = {
                "candidate_hash": clean_candidate_hash,
                "signal_date": str(previous.get("signal_date") or ""),
                "observation_hash": str(previous.get("observation_hash") or ""),
                "target_symbols": symbol_lists["before"],
                "total_allocation_pct": before_text,
                "reason": reason_transition["before"],
                "regime_id": regime_transition["before"],
                "risk_gate_status": risk_transition["before"],
            }
            current_projection = {
                "candidate_hash": clean_candidate_hash,
                "signal_date": str(current.get("signal_date") or ""),
                "observation_hash": str(current.get("observation_hash") or ""),
                "target_symbols": symbol_lists["after"],
                "total_allocation_pct": after_text,
                "reason": reason_transition["after"],
                "regime_id": regime_transition["after"],
                "risk_gate_status": risk_transition["after"],
            }
            if str(previous.get("change_projection_hash") or "") != _forward_change_projection_hash(
                previous_projection
            ):
                blockers.append("forward_observation_change_previous_projection_mismatch")
            if str(current.get("change_projection_hash") or "") != _forward_change_projection_hash(
                current_projection
            ):
                blockers.append("forward_observation_change_current_projection_mismatch")
    elif change_status == "NOT_ENOUGH_OBSERVATIONS":
        if len(chain) >= 2 or evidence.get("pair_consecutive") is not False:
            blockers.append("forward_observation_change_insufficient_status_invalid")
        expected_current = chain[-1] if chain else {}
        if previous != {} or current != expected_current:
            blockers.append("forward_observation_change_insufficient_pair_invalid")
        if clean_expected_date and _strict_date(current.get("signal_date")) != clean_expected_date:
            blockers.append("forward_observation_change_current_date_mismatch")
        empty_claims = _empty_forward_change_claims()
        for field, expected in empty_claims.items():
            if payload.get(field) != expected:
                blockers.append(f"forward_observation_change_insufficient_{field}_invalid")

    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "change": payload if not blockers else {},
        "change_hash": expected_change_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _capture_activation_valid(capture: dict[str, Any], candidate_hash: str) -> bool:
    activation_clock = dict(capture.get("activation_clock_attestation") or {})
    activated_at = _strict_integer(capture.get("candidate_activated_at"))
    try:
        signal_close_ms = int(
            datetime.fromisoformat(str(capture.get("session_close_utc") or ""))
            .astimezone(timezone.utc)
            .timestamp()
            * 1000
        )
    except (OSError, OverflowError, TypeError, ValueError):
        signal_close_ms = 0
    return (
        bool(candidate_hash)
        and str(capture.get("candidate_hash") or "") == str(candidate_hash)
        and bool(capture.get("candidate_activation_registry_hash"))
        and capture.get("candidate_active_before_signal_close") is True
        and activated_at is not None
        and activated_at > 0
        and signal_close_ms > 0
        and activated_at < signal_close_ms
        and verify_trusted_clock_attestation(activation_clock).get("status") == "PASS"
        and str(capture.get("activation_clock_attestation_hash") or "")
        == str(activation_clock.get("attestation_hash") or "")
        and _strict_integer(activation_clock.get("attested_now_ms")) is not None
        and abs(activated_at - int(activation_clock["attested_now_ms"])) <= 5_000
    )


def build_forward_state_contract(
    candidate: dict[str, Any],
    backtest_report: dict[str, Any],
    *,
    capture_contract: dict[str, Any],
    evaluation_start_index: int,
    evaluation_start_date: str,
    preactivation_completed_session_count: int,
    start_capture_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_spec = dict(backtest_report.get("run_spec") or {})
    evaluation_window = dict(backtest_report.get("evaluation_window") or {})
    capture = dict(capture_contract or {})
    start_capture = dict(start_capture_contract or capture)
    contract = {
        "schema_version": PORTFOLIO_FORWARD_STATE_SCHEMA_VERSION,
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "start_policy": "FIRST_CANDIDATE_ACTIVE_SESSION_CASH",
        "evaluation_start_index": int(evaluation_start_index),
        "evaluation_start_date": str(evaluation_start_date or ""),
        "backtest_evaluation_start_index": int(run_spec.get("evaluation_start_index", -1)),
        "backtest_evaluation_start_date": str(evaluation_window.get("start") or ""),
        "initial_cash": float(backtest_report.get("initial_cash") or 0.0),
        "initial_positions": {},
        "inherited_position_count": 0,
        "preactivation_completed_session_count": max(int(preactivation_completed_session_count), 0),
        "candidate_activated_at": int(start_capture.get("candidate_activated_at") or 0),
        "candidate_activation_registry_hash": str(start_capture.get("candidate_activation_registry_hash") or ""),
        "candidate_active_before_start_close": start_capture.get("candidate_active_before_signal_close") is True,
        "execution_model": str(backtest_report.get("execution_model") or run_spec.get("execution_model") or ""),
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    contract["forward_state_contract_hash"] = _payload_hash(contract, "forward_state_contract_hash")
    return contract


def verify_forward_state_contract(
    contract: dict[str, Any],
    *,
    candidate_hash: str,
    backtest_report: dict[str, Any] | None = None,
    capture_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(contract or {})
    blockers: list[str] = []
    if payload.get("schema_version") != PORTFOLIO_FORWARD_STATE_SCHEMA_VERSION:
        blockers.append("forward_state_schema_invalid")
    if str(payload.get("candidate_hash") or "") != str(candidate_hash or ""):
        blockers.append("forward_state_candidate_mismatch")
    if payload.get("start_policy") != "FIRST_CANDIDATE_ACTIVE_SESSION_CASH":
        blockers.append("forward_state_start_policy_invalid")
    evaluation_start_index = _strict_integer(payload.get("evaluation_start_index"))
    if evaluation_start_index is None or evaluation_start_index < 0:
        blockers.append("forward_state_start_index_invalid")
    if not str(payload.get("evaluation_start_date") or ""):
        blockers.append("forward_state_start_date_missing")
    if payload.get("candidate_active_before_start_close") is not True:
        blockers.append("forward_state_started_before_candidate_activation")
    initial_cash = _strict_number(payload.get("initial_cash"))
    if initial_cash is None or initial_cash <= 0:
        blockers.append("forward_state_initial_cash_invalid")
    inherited_position_count = _strict_integer(payload.get("inherited_position_count"))
    initial_positions = payload.get("initial_positions")
    if not isinstance(initial_positions, dict) or initial_positions or inherited_position_count != 0:
        blockers.append("forward_state_inherited_positions_present")
    candidate_activated_at = _strict_integer(payload.get("candidate_activated_at"))
    if candidate_activated_at is None or candidate_activated_at <= 0:
        blockers.append("forward_state_activation_time_invalid")
    if str(payload.get("forward_state_contract_hash") or "") != _payload_hash(
        payload,
        "forward_state_contract_hash",
    ):
        blockers.append("forward_state_contract_hash_invalid")
    if (
        payload.get("observation_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("forward_state_execution_authority_invalid")
    if backtest_report is not None:
        run_spec = dict(backtest_report.get("run_spec") or {})
        evaluation_window = dict(backtest_report.get("evaluation_window") or {})
        backtest_start_index = _strict_integer(run_spec.get("evaluation_start_index"))
        if (
            evaluation_start_index is None
            or backtest_start_index is None
            or evaluation_start_index != backtest_start_index
        ):
            blockers.append("forward_state_backtest_start_index_mismatch")
        if str(payload.get("evaluation_start_date") or "") != str(evaluation_window.get("start") or ""):
            blockers.append("forward_state_backtest_start_date_mismatch")
        backtest_initial_cash = _strict_number(backtest_report.get("initial_cash"))
        if initial_cash is None or backtest_initial_cash is None or initial_cash != backtest_initial_cash:
            blockers.append("forward_state_backtest_initial_cash_mismatch")
        if str(payload.get("execution_model") or "") != str(
            backtest_report.get("execution_model") or run_spec.get("execution_model") or ""
        ):
            blockers.append("forward_state_execution_model_mismatch")
    if capture_contract is not None:
        capture = dict(capture_contract or {})
        capture_activated_at = _strict_integer(capture.get("candidate_activated_at"))
        if (
            candidate_activated_at is None
            or capture_activated_at is None
            or candidate_activated_at != capture_activated_at
        ):
            blockers.append("forward_state_activation_time_mismatch")
        if str(payload.get("candidate_activation_registry_hash") or "") != str(
            capture.get("candidate_activation_registry_hash") or ""
        ):
            blockers.append("forward_state_activation_registry_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_shadow_observation(
    candidate: dict[str, Any],
    backtest_report: dict[str, Any],
    *,
    observed_at: int,
    risk_snapshot: dict[str, Any] | None = None,
    capture_contract: dict[str, Any] | None = None,
    forward_state_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_decision = backtest_report.get("pending_decision_at_end")
    decision = dict(raw_decision) if isinstance(raw_decision, dict) else {}
    raw_manifest = backtest_report.get("dataset_manifest")
    manifest = dict(raw_manifest) if isinstance(raw_manifest, dict) else {}
    candidate_hash = str(candidate.get("candidate_hash") or "")
    signal_date = str(decision.get("signal_date") or manifest.get("last") or "")
    frozen_last = str(candidate.get("dataset_last") or "")
    shadow_risk = dict(risk_snapshot) if isinstance(risk_snapshot, dict) else {}
    capture = dict(capture_contract) if isinstance(capture_contract, dict) else {}
    state_contract = dict(forward_state_contract) if isinstance(forward_state_contract, dict) else {}
    blockers: list[str] = []
    if not isinstance(risk_snapshot, dict):
        blockers.append("observation_risk_snapshot_invalid")
    if not candidate_hash:
        blockers.append("candidate_hash_missing")
    if backtest_report.get("ok") is not True:
        blockers.append("portfolio_backtest_failed")
    if not signal_date:
        blockers.append("signal_date_missing")
    if frozen_last and signal_date <= frozen_last:
        blockers.append(f"no_new_completed_bar:{signal_date}<={frozen_last}")
    if capture.get("status") != "PASS" or capture.get("timely") is not True:
        blockers.append(f"forward_capture_not_timely:{capture.get('status') or 'MISSING'}")
    if (
        capture.get("observation_only") is not True
        or capture.get("paper_authorized") is not False
        or capture.get("live_order_allowed") is not False
    ):
        blockers.append("forward_capture_execution_authority_invalid")
    if str(capture.get("capture_contract_hash") or "") != _payload_hash(capture, "capture_contract_hash"):
        blockers.append("forward_capture_contract_hash_invalid")
    if int(capture.get("observed_at") or 0) != int(observed_at or 0):
        blockers.append("forward_capture_observed_at_mismatch")
    clock_verification = verify_trusted_clock_attestation(dict(capture.get("clock_attestation") or {}))
    if capture.get("clock_attested") is not True or clock_verification.get("status") != "PASS":
        blockers.append("forward_capture_clock_not_attested")
    if str(capture.get("signal_date") or "") != signal_date:
        blockers.append("forward_capture_signal_date_mismatch")
    if not _capture_activation_valid(capture, candidate_hash):
        blockers.append("forward_capture_candidate_activation_invalid")
    state_verification = verify_forward_state_contract(
        state_contract,
        candidate_hash=candidate_hash,
        backtest_report=backtest_report,
        capture_contract=capture,
    )
    blockers.extend(state_verification.get("blockers") or [])
    evidence = {
        "candidate_hash": candidate_hash,
        "signal_date": signal_date,
        "dataset_hash": str(manifest.get("data_hash") or ""),
        "dataset_last": str(manifest.get("last") or ""),
        "decision": decision,
    }
    target_symbols = decision.get("target_symbols")
    target_weights = decision.get("target_weights")
    allocation = _strict_number(decision.get("target_allocation_pct"))
    volatility = _strict_number(decision.get("estimated_portfolio_volatility_pct"))
    regime = decision.get("regime") if isinstance(decision.get("regime"), dict) else {}
    observation = {
        "schema_version": PORTFOLIO_SHADOW_SCHEMA_VERSION,
        "status": "WAITING",
        "blockers": [],
        "candidate_hash": candidate_hash,
        "signal_date": signal_date,
        "observed_at": int(observed_at),
        "dataset_hash": evidence["dataset_hash"],
        "dataset_last": evidence["dataset_last"],
        "target_symbols": list(target_symbols) if isinstance(target_symbols, list) else [],
        "target_weights": dict(target_weights) if isinstance(target_weights, dict) else {},
        "target_allocation_pct": allocation if allocation is not None else 0.0,
        "reason": str(decision.get("reason") or ""),
        "regime_id": str(regime.get("regime_id") or ""),
        "estimated_portfolio_volatility_pct": volatility if volatility is not None else 0.0,
        "decision": decision,
        "risk_gate_status": str(shadow_risk.get("status") or ""),
        "risk_snapshot_hash": str(shadow_risk.get("risk_snapshot_hash") or ""),
        "risk_snapshot": shadow_risk,
        "capture_status": str(capture.get("status") or "MISSING"),
        "capture_contract_hash": str(capture.get("capture_contract_hash") or ""),
        "capture_contract": capture,
        "forward_state_contract_hash": str(state_contract.get("forward_state_contract_hash") or ""),
        "forward_state_contract": state_contract,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    blockers.extend(_risk_snapshot_contract_blockers(observation))
    blockers.extend(_decision_projection_blockers(observation))
    observation["blockers"] = list(dict.fromkeys(blockers))
    observation["status"] = "READY" if not blockers else "WAITING"
    observation["market_decision_hash"] = _market_decision_hash(observation)
    observation["decision_hash"] = observation["market_decision_hash"]
    observation["observation_hash"] = _payload_hash(observation, "observation_hash")
    return observation


class PortfolioShadowLedger:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_shadow_observations (
                    candidate_hash TEXT NOT NULL,
                    signal_date TEXT NOT NULL,
                    decision_hash TEXT NOT NULL,
                    observed_at INTEGER NOT NULL,
                    dataset_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(candidate_hash, signal_date)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_shadow_risk_reassessments (
                    candidate_hash TEXT NOT NULL,
                    signal_date TEXT NOT NULL,
                    risk_snapshot_hash TEXT NOT NULL,
                    risk_status TEXT NOT NULL,
                    observed_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(candidate_hash, signal_date, risk_snapshot_hash)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_shadow_capture_events (
                    event_key TEXT PRIMARY KEY,
                    event_hash TEXT NOT NULL,
                    candidate_hash TEXT NOT NULL,
                    signal_date TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    observed_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
            """)

    def record(self, observation: dict[str, Any]) -> dict[str, Any]:
        candidate_hash = str(observation.get("candidate_hash") or "")
        signal_date = str(observation.get("signal_date") or "")
        decision_hash = str(observation.get("decision_hash") or "")
        if observation.get("status") != "READY":
            return {"ok": False, "status": "WAITING", "observation": observation}
        if not candidate_hash or not signal_date or not decision_hash:
            return {"ok": False, "status": "BLOCK", "reason": "shadow_observation_identity_missing"}
        if decision_hash != _market_decision_hash(observation):
            return {"ok": False, "status": "BLOCK", "reason": "shadow_decision_hash_invalid"}
        if str(observation.get("observation_hash") or "") != _payload_hash(observation, "observation_hash"):
            return {"ok": False, "status": "BLOCK", "reason": "shadow_observation_hash_invalid"}
        decision_projection_blockers = _decision_projection_blockers(observation)
        if decision_projection_blockers:
            return {
                "ok": False,
                "status": "BLOCK",
                "reason": "shadow_decision_projection_invalid",
                "blockers": decision_projection_blockers,
            }
        risk_snapshot_blockers = _risk_snapshot_contract_blockers(observation)
        if risk_snapshot_blockers:
            return {
                "ok": False,
                "status": "BLOCK",
                "reason": "shadow_risk_snapshot_invalid",
                "blockers": risk_snapshot_blockers,
            }
        capture = dict(observation.get("capture_contract") or {})
        if capture.get("status") != "PASS" or capture.get("timely") is not True:
            return {"ok": False, "status": "BLOCK", "reason": "shadow_capture_contract_invalid"}
        if str(capture.get("capture_contract_hash") or "") != _payload_hash(capture, "capture_contract_hash"):
            return {"ok": False, "status": "BLOCK", "reason": "shadow_capture_contract_hash_invalid"}
        if str(capture.get("signal_date") or "") != signal_date:
            return {"ok": False, "status": "BLOCK", "reason": "shadow_capture_signal_date_mismatch"}
        if int(capture.get("observed_at") or 0) != int(observation.get("observed_at") or 0):
            return {"ok": False, "status": "BLOCK", "reason": "shadow_capture_observed_at_mismatch"}
        clock_verification = verify_trusted_clock_attestation(dict(capture.get("clock_attestation") or {}))
        if (
            capture.get("clock_attested") is not True
            or clock_verification.get("status") != "PASS"
            or str(capture.get("clock_attestation_hash") or "") != str((capture.get("clock_attestation") or {}).get("attestation_hash") or "")
        ):
            return {"ok": False, "status": "BLOCK", "reason": "shadow_capture_clock_not_attested"}
        if not _capture_activation_valid(capture, candidate_hash):
            return {"ok": False, "status": "BLOCK", "reason": "shadow_capture_candidate_activation_invalid"}
        state_contract = dict(observation.get("forward_state_contract") or {})
        state_verification = verify_forward_state_contract(
            state_contract,
            candidate_hash=candidate_hash,
            capture_contract=capture,
        )
        if state_verification.get("status") != "PASS":
            return {
                "ok": False,
                "status": "BLOCK",
                "reason": "shadow_forward_state_contract_invalid",
                "blockers": list(state_verification.get("blockers") or []),
            }
        if str(observation.get("forward_state_contract_hash") or "") != str(
            state_contract.get("forward_state_contract_hash") or ""
        ):
            return {"ok": False, "status": "BLOCK", "reason": "shadow_forward_state_contract_reference_mismatch"}
        if (
            observation.get("observation_only") is not True
            or observation.get("paper_authorized") is not False
            or observation.get("live_order_allowed") is not False
        ):
            return {"ok": False, "status": "BLOCK", "reason": "shadow_observation_has_execution_authority"}
        payload_json = json.dumps(observation, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        with self._lock, closing(self._connect()) as connection, connection:
            existing = connection.execute(
                "SELECT decision_hash, payload_json FROM portfolio_shadow_observations WHERE candidate_hash = ? AND signal_date = ?",
                (candidate_hash, signal_date),
            ).fetchone()
            if existing:
                if str(existing["decision_hash"]) != decision_hash:
                    existing_payload = json.loads(str(existing["payload_json"]))
                    if _market_decision_hash(existing_payload) == _market_decision_hash(observation):
                        return {
                            "ok": True,
                            "status": "IDEMPOTENT_MARKET_REPLAY",
                            "observation": existing_payload,
                        }
                    return {
                        "ok": False,
                        "status": "CONFLICT",
                        "reason": "same_candidate_and_date_has_different_decision_hash",
                        "existing_hash": str(existing["decision_hash"]),
                        "incoming_hash": decision_hash,
                    }
                return {
                    "ok": True,
                    "status": "IDEMPOTENT_REPLAY",
                    "observation": json.loads(str(existing["payload_json"])),
                }
            connection.execute(
                """
                INSERT INTO portfolio_shadow_observations(
                    candidate_hash, signal_date, decision_hash, observed_at,
                    dataset_hash, status, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_hash,
                    signal_date,
                    decision_hash,
                    int(observation.get("observed_at") or 0),
                    str(observation.get("dataset_hash") or ""),
                    str(observation.get("status") or "READY"),
                    payload_json,
                ),
            )
        return {"ok": True, "status": "RECORDED", "observation": observation}

    def observation_dates(self, candidate_hash: str) -> list[str]:
        clean_hash = str(candidate_hash or "")
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT signal_date FROM portfolio_shadow_observations WHERE candidate_hash = ? ORDER BY signal_date",
                (clean_hash,),
            ).fetchall()
        return [str(row["signal_date"] or "") for row in rows]

    def capture_event_dates(self, candidate_hash: str) -> list[str]:
        clean_hash = str(candidate_hash or "")
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT DISTINCT signal_date FROM portfolio_shadow_capture_events WHERE candidate_hash = ? ORDER BY signal_date",
                (clean_hash,),
            ).fetchall()
        return [str(row["signal_date"] or "") for row in rows]

    def observation(self, candidate_hash: str, signal_date: str) -> dict[str, Any] | None:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM portfolio_shadow_observations WHERE candidate_hash = ? AND signal_date = ?",
                (str(candidate_hash or ""), str(signal_date or "")),
            ).fetchone()
        return json.loads(str(row["payload_json"])) if row else None

    def latest_observation_receipt(
        self,
        candidate_hash: str,
        *,
        ledger_audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_hash = str(candidate_hash or "")
        audit = dict(ledger_audit) if isinstance(ledger_audit, dict) else self.audit(clean_hash)
        if str(audit.get("status") or "").upper() != "PASS":
            return {}
        signal_date = _strict_date(audit.get("last_signal_date"))
        if not signal_date:
            return {}
        observation = self.observation(clean_hash, signal_date)
        if not isinstance(observation, dict):
            return {}
        return build_latest_forward_observation_receipt(observation, ledger_audit=audit)

    def latest_observation_change(
        self,
        candidate_hash: str,
        *,
        ledger_audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Read the latest pair once under the ledger lock and seal a descriptive diff."""

        clean_hash = str(candidate_hash or "")
        with self._lock:
            audit = dict(ledger_audit) if isinstance(ledger_audit, dict) else self.audit(clean_hash)
            with closing(self._connect()) as connection:
                rows = connection.execute(
                    """
                    SELECT payload_json
                    FROM portfolio_shadow_observations
                    WHERE candidate_hash = ?
                    ORDER BY signal_date DESC
                    LIMIT 2
                    """,
                    (clean_hash,),
                ).fetchall()
            observations: list[dict[str, Any]] = []
            for row in reversed(rows):
                try:
                    payload = json.loads(str(row["payload_json"]))
                except (json.JSONDecodeError, TypeError, ValueError):
                    payload = {}
                observations.append(payload if isinstance(payload, dict) else {})
            previous = observations[-2] if len(observations) >= 2 else None
            current = observations[-1] if observations else None
            return build_forward_observation_change(previous, current, ledger_audit=audit)

    def record_capture_event(self, event: dict[str, Any]) -> dict[str, Any]:
        candidate_hash = str(event.get("candidate_hash") or "")
        signal_date = str(event.get("signal_date") or "")
        event_type = str(event.get("event_type") or "").upper()
        if not candidate_hash or not signal_date or not event_type:
            return {"ok": False, "status": "BLOCK", "reason": "capture_event_identity_missing"}
        payload = {
            "schema_version": PORTFOLIO_SHADOW_SCHEMA_VERSION,
            **dict(event),
            "candidate_hash": candidate_hash,
            "signal_date": signal_date,
            "event_type": event_type,
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        identity = {
            "candidate_hash": candidate_hash,
            "signal_date": signal_date,
            "event_type": event_type,
            "reason": str(payload.get("reason") or ""),
            "dataset_hash": str(payload.get("dataset_hash") or ""),
        }
        event_key = _canonical_hash(identity)
        payload["event_key"] = event_key
        payload["event_hash"] = _payload_hash(payload, "event_hash")
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        with self._lock, closing(self._connect()) as connection, connection:
            existing = connection.execute(
                "SELECT payload_json FROM portfolio_shadow_capture_events WHERE event_key = ?",
                (event_key,),
            ).fetchone()
            if existing:
                return {"ok": True, "status": "IDEMPOTENT_REPLAY", "event": json.loads(str(existing["payload_json"]))}
            connection.execute(
                """
                INSERT INTO portfolio_shadow_capture_events(
                    event_key, event_hash, candidate_hash, signal_date,
                    event_type, observed_at, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_key,
                    str(payload["event_hash"]),
                    candidate_hash,
                    signal_date,
                    event_type,
                    int(payload.get("observed_at") or 0),
                    payload_json,
                ),
            )
        return {"ok": True, "status": "RECORDED", "event": payload}

    def record_risk_reassessment(
        self,
        *,
        candidate_hash: str,
        signal_date: str,
        risk_snapshot: dict[str, Any],
        observed_at: int,
    ) -> dict[str, Any]:
        clean_candidate = str(candidate_hash or "")
        clean_date = str(signal_date or "")
        snapshot = dict(risk_snapshot or {})
        risk_hash = str(snapshot.get("risk_snapshot_hash") or "")
        if not clean_candidate or not clean_date or not risk_hash:
            return {"ok": False, "status": "BLOCK", "reason": "risk_reassessment_identity_missing"}
        if risk_hash != _payload_hash(snapshot, "risk_snapshot_hash"):
            return {"ok": False, "status": "BLOCK", "reason": "risk_snapshot_hash_invalid"}
        if snapshot.get("paper_authorized") is not False or snapshot.get("live_order_allowed") is not False:
            return {"ok": False, "status": "BLOCK", "reason": "risk_snapshot_has_execution_authority"}
        payload = {
            "schema_version": PORTFOLIO_SHADOW_SCHEMA_VERSION,
            "candidate_hash": clean_candidate,
            "signal_date": clean_date,
            "risk_snapshot_hash": risk_hash,
            "risk_status": str(snapshot.get("status") or "BLOCK"),
            "observed_at": int(observed_at),
            "risk_snapshot": snapshot,
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        with self._lock, closing(self._connect()) as connection, connection:
            observation = connection.execute(
                "SELECT 1 FROM portfolio_shadow_observations WHERE candidate_hash = ? AND signal_date = ?",
                (clean_candidate, clean_date),
            ).fetchone()
            if not observation:
                return {"ok": False, "status": "BLOCK", "reason": "market_observation_missing"}
            existing = connection.execute(
                """
                SELECT payload_json FROM portfolio_shadow_risk_reassessments
                WHERE candidate_hash = ? AND signal_date = ? AND risk_snapshot_hash = ?
                """,
                (clean_candidate, clean_date, risk_hash),
            ).fetchone()
            if existing:
                return {"ok": True, "status": "IDEMPOTENT_REPLAY", "reassessment": json.loads(existing["payload_json"])}
            connection.execute(
                """
                INSERT INTO portfolio_shadow_risk_reassessments(
                    candidate_hash, signal_date, risk_snapshot_hash, risk_status, observed_at, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (clean_candidate, clean_date, risk_hash, payload["risk_status"], int(observed_at), payload_json),
            )
        return {"ok": True, "status": "RECORDED", "reassessment": payload}

    def audit(self, candidate_hash: str) -> dict[str, Any]:
        clean_hash = str(candidate_hash or "")
        with self._lock, closing(self._connect()) as connection:
            observations = connection.execute(
                "SELECT * FROM portfolio_shadow_observations WHERE candidate_hash = ? ORDER BY signal_date",
                (clean_hash,),
            ).fetchall()
            risks = connection.execute(
                "SELECT * FROM portfolio_shadow_risk_reassessments WHERE candidate_hash = ? ORDER BY observed_at, rowid",
                (clean_hash,),
            ).fetchall()
            events = connection.execute(
                "SELECT * FROM portfolio_shadow_capture_events WHERE candidate_hash = ? ORDER BY observed_at, rowid",
                (clean_hash,),
            ).fetchall()

        integrity_violations: list[str] = []
        timely_count = 0
        externally_attested_count = 0
        activation_verified_count = 0
        forward_state_verified_count = 0
        clock_attestation_violation_count = 0
        candidate_activation_violation_count = 0
        valid_count = 0
        risk_pass_observation_count = 0
        planned_rebalance_count = 0
        execution_authority_violation_count = 0
        signal_dates: list[str] = []
        valid_observation_evidence: dict[str, dict[str, str]] = {}
        for row in observations:
            row_date = str(row["signal_date"] or "")
            row_violations: list[str] = []
            try:
                payload = json.loads(str(row["payload_json"]))
            except json.JSONDecodeError:
                integrity_violations.append(f"{row_date}:observation_json_invalid")
                continue
            if str(payload.get("candidate_hash") or "") != clean_hash or str(payload.get("signal_date") or "") != row_date:
                row_violations.append("observation_identity_mismatch")
            if str(payload.get("dataset_hash") or "") != str(row["dataset_hash"] or ""):
                row_violations.append("observation_dataset_hash_mismatch")
            expected_decision_hash = _market_decision_hash(payload)
            if str(payload.get("decision_hash") or "") != expected_decision_hash or str(row["decision_hash"] or "") != expected_decision_hash:
                row_violations.append("observation_decision_hash_mismatch")
            if str(payload.get("observation_hash") or "") != _payload_hash(payload, "observation_hash"):
                row_violations.append("observation_payload_hash_mismatch")
            row_violations.extend(_decision_projection_blockers(payload))
            capture = dict(payload.get("capture_contract") or {})
            capture_hash_valid = (
                bool(capture.get("capture_contract_hash"))
                and str(capture.get("capture_contract_hash")) == _payload_hash(capture, "capture_contract_hash")
            )
            capture_timely = (
                payload.get("schema_version") == PORTFOLIO_SHADOW_SCHEMA_VERSION
                and capture_hash_valid
                and capture.get("status") == "PASS"
                and capture.get("timely") is True
                and capture.get("backfill_allowed") is False
                and str(capture.get("signal_date") or "") == row_date
            )
            clock = dict(capture.get("clock_attestation") or {})
            clock_verification = verify_trusted_clock_attestation(clock)
            clock_attestation_valid = (
                capture.get("clock_attested") is True
                and clock_verification.get("status") == "PASS"
                and str(capture.get("clock_attestation_hash") or "") == str(clock.get("attestation_hash") or "")
                and abs(int(clock.get("attested_now_ms") or 0) - int(capture.get("observed_at") or 0)) <= 5_000
            )
            if not capture_timely:
                row_violations.append("observation_capture_contract_invalid")
            else:
                timely_count += 1
            if clock_attestation_valid:
                externally_attested_count += 1
            else:
                clock_attestation_violation_count += 1
                row_violations.append("observation_clock_attestation_invalid")
            activation_valid = _capture_activation_valid(capture, clean_hash)
            if activation_valid:
                activation_verified_count += 1
            else:
                candidate_activation_violation_count += 1
                row_violations.append("observation_candidate_activation_invalid")
            state_contract = dict(payload.get("forward_state_contract") or {})
            state_verification = verify_forward_state_contract(
                state_contract,
                candidate_hash=clean_hash,
                capture_contract=capture,
            )
            if state_verification.get("status") != "PASS":
                row_violations.extend(state_verification.get("blockers") or ["forward_state_contract_invalid"])
            else:
                forward_state_verified_count += 1
            if str(payload.get("forward_state_contract_hash") or "") != str(
                state_contract.get("forward_state_contract_hash") or ""
            ):
                row_violations.append("forward_state_contract_reference_mismatch")
            risk_snapshot_blockers = _risk_snapshot_contract_blockers(payload)
            row_violations.extend(risk_snapshot_blockers)
            if payload.get("risk_gate_status") == "PASS" and not risk_snapshot_blockers:
                risk_pass_observation_count += 1
            if (
                payload.get("observation_only") is not True
                or payload.get("paper_authorized") is not False
                or payload.get("live_order_allowed") is not False
            ):
                execution_authority_violation_count += 1
                row_violations.append("observation_execution_authority_invalid")
            if str(payload.get("reason") or "") == "relative_strength_rebalance":
                planned_rebalance_count += 1
            change_target_symbols_raw = payload.get("target_symbols")
            change_target_symbols = (
                list(change_target_symbols_raw)
                if isinstance(change_target_symbols_raw, list)
                and all(isinstance(item, str) and bool(item) for item in change_target_symbols_raw)
                else []
            )
            if (
                not isinstance(change_target_symbols_raw, list)
                or len(change_target_symbols) != len(change_target_symbols_raw)
                or len(set(change_target_symbols)) != len(change_target_symbols)
            ):
                row_violations.append("observation_change_projection_target_symbols_invalid")
            change_allocation = _strict_number(payload.get("target_allocation_pct"))
            change_allocation_text = _decimal_text(payload.get("target_allocation_pct"))
            if (
                change_allocation is None
                or change_allocation_text is None
                or change_allocation < 0
                or change_allocation > 100
            ):
                row_violations.append("observation_change_projection_allocation_invalid")
            change_projection = {
                "candidate_hash": clean_hash,
                "signal_date": row_date,
                "observation_hash": str(payload.get("observation_hash") or ""),
                "target_symbols": change_target_symbols,
                "total_allocation_pct": change_allocation_text or "",
                "reason": str(payload.get("reason") or ""),
                "regime_id": str(payload.get("regime_id") or ""),
                "risk_gate_status": str(payload.get("risk_gate_status") or ""),
            }
            if row_violations:
                integrity_violations.extend(f"{row_date}:{item}" for item in row_violations)
            else:
                valid_count += 1
                signal_dates.append(row_date)
                valid_observation_evidence[row_date] = {
                    "dataset_hash": str(payload.get("dataset_hash") or ""),
                    "decision_hash": str(payload.get("decision_hash") or ""),
                    "observation_hash": str(payload.get("observation_hash") or ""),
                    "forward_state_contract_hash": str(payload.get("forward_state_contract_hash") or ""),
                    "risk_snapshot_hash": str(payload.get("risk_snapshot_hash") or ""),
                    "change_projection_hash": _forward_change_projection_hash(change_projection),
                }

        risk_block_count = 0
        for row in risks:
            row_date = str(row["signal_date"] or "")
            if str(row["risk_status"] or "") != "PASS":
                risk_block_count += 1
            try:
                payload = json.loads(str(row["payload_json"]))
            except json.JSONDecodeError:
                integrity_violations.append(f"{row_date}:risk_json_invalid")
                continue
            snapshot = dict(payload.get("risk_snapshot") or {})
            if (
                str(payload.get("candidate_hash") or "") != clean_hash
                or str(payload.get("signal_date") or "") != row_date
                or str(payload.get("risk_snapshot_hash") or "") != str(row["risk_snapshot_hash"] or "")
                or str(snapshot.get("risk_snapshot_hash") or "") != _payload_hash(snapshot, "risk_snapshot_hash")
            ):
                integrity_violations.append(f"{row_date}:risk_reassessment_integrity_invalid")
            if (
                payload.get("observation_only") is not True
                or payload.get("paper_authorized") is not False
                or payload.get("live_order_allowed") is not False
            ):
                execution_authority_violation_count += 1
                integrity_violations.append(f"{row_date}:risk_reassessment_execution_authority_invalid")

        missed_capture_count = 0
        decision_conflict_count = 0
        capture_event_types: dict[str, int] = {}
        neutral_capture_event_count = 0
        violation_capture_event_count = 0
        for row in events:
            event_type = str(row["event_type"] or "")
            capture_event_types[event_type] = capture_event_types.get(event_type, 0) + 1
            missed_capture_count += int(event_type == "MISSED_CAPTURE")
            decision_conflict_count += int(event_type == "DECISION_REPLAY_CONFLICT")
            neutral_capture_event_count += int(event_type == "PRE_ACTIVATION_SKIPPED")
            violation_capture_event_count += int(event_type != "PRE_ACTIVATION_SKIPPED")
            try:
                payload = json.loads(str(row["payload_json"]))
            except json.JSONDecodeError:
                integrity_violations.append(f"{row['signal_date']}:capture_event_json_invalid")
                continue
            if (
                str(payload.get("event_key") or "") != str(row["event_key"] or "")
                or str(payload.get("event_hash") or "") != str(row["event_hash"] or "")
                or str(payload.get("event_hash") or "") != _payload_hash(payload, "event_hash")
                or str(payload.get("candidate_hash") or "") != clean_hash
                or str(payload.get("signal_date") or "") != str(row["signal_date"] or "")
                or str(payload.get("event_type") or "") != event_type
            ):
                integrity_violations.append(f"{row['signal_date']}:capture_event_integrity_invalid")
            if (
                payload.get("observation_only") is not True
                or payload.get("paper_authorized") is not False
                or payload.get("live_order_allowed") is not False
            ):
                execution_authority_violation_count += 1
                integrity_violations.append(f"{row['signal_date']}:capture_event_execution_authority_invalid")

        capture_violation_count = violation_capture_event_count
        last_signal_date = max(signal_dates) if signal_dates else ""
        latest_observation_evidence = dict(valid_observation_evidence.get(last_signal_date) or {})
        observation_chain = [
            {
                "signal_date": signal_date,
                "observation_hash": str(valid_observation_evidence[signal_date].get("observation_hash") or ""),
                "change_projection_hash": str(
                    valid_observation_evidence[signal_date].get("change_projection_hash") or ""
                ),
            }
            for signal_date in sorted(signal_dates)
        ]
        return {
            "schema_version": PORTFOLIO_SHADOW_SCHEMA_VERSION,
            "status": "PASS" if not integrity_violations and capture_violation_count == 0 else "BLOCK",
            "candidate_hash": clean_hash,
            "observation_count": len(observations),
            "valid_observation_count": valid_count,
            "timely_observation_count": timely_count,
            "externally_attested_observation_count": externally_attested_count,
            "activation_verified_observation_count": activation_verified_count,
            "forward_state_verified_observation_count": forward_state_verified_count,
            "clock_attestation_violation_count": clock_attestation_violation_count,
            "candidate_activation_violation_count": candidate_activation_violation_count,
            "risk_pass_observation_count": risk_pass_observation_count,
            "planned_rebalance_count": planned_rebalance_count,
            "first_signal_date": min(signal_dates) if signal_dates else "",
            "last_signal_date": last_signal_date,
            "observation_chain": observation_chain,
            "observation_chain_count": len(observation_chain),
            "observation_chain_hash": _canonical_hash(observation_chain),
            "latest_dataset_hash": str(latest_observation_evidence.get("dataset_hash") or ""),
            "latest_decision_hash": str(latest_observation_evidence.get("decision_hash") or ""),
            "latest_observation_hash": str(latest_observation_evidence.get("observation_hash") or ""),
            "latest_forward_state_contract_hash": str(
                latest_observation_evidence.get("forward_state_contract_hash") or ""
            ),
            "latest_observation_risk_snapshot_hash": str(
                latest_observation_evidence.get("risk_snapshot_hash") or ""
            ),
            "risk_reassessment_count": len(risks),
            "risk_block_reassessment_count": risk_block_count,
            "capture_violation_count": capture_violation_count,
            "neutral_capture_event_count": neutral_capture_event_count,
            "missed_capture_count": missed_capture_count,
            "decision_replay_conflict_count": decision_conflict_count,
            "capture_event_types": capture_event_types,
            "execution_authority_violation_count": execution_authority_violation_count,
            "integrity_violations": list(dict.fromkeys(integrity_violations)),
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def summary(self, candidate_hash: str = "") -> dict[str, Any]:
        clean_hash = str(candidate_hash or "")
        where = "WHERE candidate_hash = ?" if clean_hash else ""
        params: tuple[Any, ...] = (clean_hash,) if clean_hash else ()
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS count, MIN(signal_date) AS first_date, MAX(signal_date) AS last_date FROM portfolio_shadow_observations {where}",
                params,
            ).fetchone()
            risk_row = connection.execute(
                f"""
                SELECT COUNT(*) AS count,
                       SUM(CASE WHEN risk_status = 'PASS' THEN 1 ELSE 0 END) AS pass_count,
                       SUM(CASE WHEN risk_status != 'PASS' THEN 1 ELSE 0 END) AS block_count
                FROM portfolio_shadow_risk_reassessments {where}
                """,
                params,
            ).fetchone()
            latest_risk = connection.execute(
                f"""
                SELECT risk_status, signal_date, risk_snapshot_hash
                FROM portfolio_shadow_risk_reassessments {where}
                ORDER BY observed_at DESC, rowid DESC LIMIT 1
                """,
                params,
            ).fetchone()
        result = {
            "schema_version": PORTFOLIO_SHADOW_SCHEMA_VERSION,
            "candidate_hash": clean_hash,
            "observation_count": int(row["count"] or 0),
            "first_signal_date": str(row["first_date"] or ""),
            "last_signal_date": str(row["last_date"] or ""),
            "risk_reassessment_count": int(risk_row["count"] or 0),
            "risk_pass_count": int(risk_row["pass_count"] or 0),
            "risk_block_count": int(risk_row["block_count"] or 0),
            "latest_risk_status": str(latest_risk["risk_status"] or "") if latest_risk else "",
            "latest_risk_signal_date": str(latest_risk["signal_date"] or "") if latest_risk else "",
            "latest_risk_snapshot_hash": str(latest_risk["risk_snapshot_hash"] or "") if latest_risk else "",
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if clean_hash:
            result["forward_audit"] = self.audit(clean_hash)
        return result
