from __future__ import annotations

from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import threading
from typing import Any

from .execution_authority import authority_violations
from .portfolio_backtest import (
    portfolio_revision_evidence_hash,
    relative_strength_numeric_contract_issues,
    relative_strength_settings_from_spec,
)
from .portfolio_shadow import verify_forward_state_contract
from .trusted_clock import verify_trusted_clock_attestation


PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION = "portfolio-forward-performance-v3"
PORTFOLIO_FORWARD_EXECUTION_MODEL = "captured-close-next-open-shadow-account-v3"
LEGACY_PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION = PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION
PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION = "portfolio-forward-readiness-v2"
PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION = "portfolio-forward-readiness-v3"
EXPECTED_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION = "portfolio-forward-statistical-audit-v1"
EXPECTED_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION = "portfolio-forward-statistical-audit-v2"
EXPECTED_FORWARD_DECISION_WINDOW_SCHEMA_VERSION = (
    "portfolio-forward-first-joint-maturity-decision-v1"
)
EXPECTED_FORWARD_RISK_ACCEPTANCE_SCHEMA_VERSION = (
    "portfolio-forward-first-joint-maturity-risk-acceptance-v1"
)
EXPECTED_FORWARD_DECISION_POLICY = "FIRST_JOINT_MATURITY_SINGLE_LOOK"
_MAX_SAFE_INTEGER = 9_007_199_254_740_991


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _payload_hash(payload: dict[str, Any], field: str) -> str:
    clean = dict(payload)
    clean.pop(field, None)
    return _canonical_hash(clean)


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def _strict_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _nonnegative_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _v3_safe_integer(value: Any, *, minimum: int = 0) -> int | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > _MAX_SAFE_INTEGER
    ):
        return None
    return value


def _v3_finite_native_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def _v3_container_cycle_detected(payload: Any) -> bool:
    """Detect built-in container cycles without recursive traversal."""

    if not isinstance(payload, (dict, list, tuple)):
        return False
    active: set[int] = set()
    complete: set[int] = set()
    stack: list[tuple[Any, bool]] = [(payload, False)]
    while stack:
        value, exiting = stack.pop()
        if not isinstance(value, (dict, list, tuple)):
            continue
        identity = id(value)
        if exiting:
            active.discard(identity)
            complete.add(identity)
            continue
        if identity in active:
            return True
        if identity in complete:
            continue
        active.add(identity)
        stack.append((value, True))
        children = value.values() if isinstance(value, dict) else value
        stack.extend((child, False) for child in children)
    return False


def forward_evidence_thresholds_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    source = dict(spec or {})
    issues: list[str] = []

    def positive_integer(name: str, default: int) -> int:
        value = source[name] if name in source and source[name] is not None else default
        parsed = _strict_number(value)
        if isinstance(value, bool) or parsed is None or parsed < 1 or not parsed.is_integer():
            issues.append(f"{name}:positive_integer_required")
            return int(default)
        return int(parsed)

    observations = positive_integer("minimum_forward_observations", 60)
    outcomes = (
        positive_integer("minimum_forward_performance_outcomes", observations)
        if "minimum_forward_performance_outcomes" in source
        and source["minimum_forward_performance_outcomes"] is not None
        else observations
    )
    rebalances = positive_integer("minimum_planned_rebalances", 8)
    return {
        "minimum_forward_observations": observations,
        "minimum_forward_performance_outcomes": outcomes,
        "minimum_planned_rebalances": rebalances,
        "issues": issues,
        "status": "PASS" if not issues else "BLOCK",
    }


def forward_evidence_thresholds_v3_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Return the current strict single-look forward-evidence thresholds."""

    source = dict(spec or {})
    issues: list[str] = []

    def positive_safe_integer(name: str, default: int) -> int:
        value = source[name] if name in source and source[name] is not None else default
        parsed = _v3_safe_integer(value, minimum=1)
        if parsed is None:
            issues.append(f"{name}:positive_safe_integer_required")
            return int(default)
        return parsed

    observations = positive_safe_integer("minimum_forward_observations", 60)
    outcomes = (
        positive_safe_integer("minimum_forward_performance_outcomes", observations)
        if "minimum_forward_performance_outcomes" in source
        and source["minimum_forward_performance_outcomes"] is not None
        else observations
    )
    rebalances = positive_safe_integer("minimum_planned_rebalances", 8)
    return {
        "minimum_forward_observations": observations,
        "minimum_forward_performance_outcomes": outcomes,
        "minimum_planned_rebalances": rebalances,
        "issues": issues,
        "status": "PASS" if not issues else "BLOCK",
    }


def _rounded(value: float, digits: int = 10) -> float:
    return round(float(value), digits)


def _close(left: Any, right: Any, *, tolerance: float = 1e-5) -> bool:
    return abs(_number(left) - _number(right)) <= tolerance


def _market_decision_hash(observation: dict[str, Any]) -> str:
    return _canonical_hash({
        "candidate_hash": str(observation.get("candidate_hash") or ""),
        "signal_date": str(observation.get("signal_date") or ""),
        "dataset_hash": str(observation.get("dataset_hash") or ""),
        "dataset_last": str(observation.get("dataset_last") or ""),
        "forward_state_contract_hash": str(observation.get("forward_state_contract_hash") or ""),
        "decision": dict(observation.get("decision") or {}),
    })


def verify_shadow_observation(
    observation: dict[str, Any],
    *,
    candidate_hash: str,
    signal_date: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = dict(observation or {})
    if payload.get("status") != "READY":
        blockers.append("observation_not_ready")
    if str(payload.get("candidate_hash") or "") != str(candidate_hash or ""):
        blockers.append("observation_candidate_mismatch")
    if str(payload.get("signal_date") or "") != str(signal_date or ""):
        blockers.append("observation_signal_date_mismatch")
    if str(payload.get("dataset_last") or "") != str(signal_date or ""):
        blockers.append("observation_dataset_last_mismatch")
    if not str(payload.get("dataset_hash") or ""):
        blockers.append("observation_dataset_hash_missing")
    expected_decision_hash = _market_decision_hash(payload)
    if (
        str(payload.get("decision_hash") or "") != expected_decision_hash
        or str(payload.get("market_decision_hash") or "") != expected_decision_hash
    ):
        blockers.append("observation_decision_hash_invalid")
    if str(payload.get("observation_hash") or "") != _payload_hash(payload, "observation_hash"):
        blockers.append("observation_hash_invalid")
    decision = dict(payload.get("decision") or {})
    if str(decision.get("signal_date") or "") != str(signal_date or ""):
        blockers.append("decision_signal_date_mismatch")
    capture = dict(payload.get("capture_contract") or {})
    if (
        capture.get("status") != "PASS"
        or capture.get("timely") is not True
        or capture.get("backfill_allowed") is not False
        or str(capture.get("signal_date") or "") != str(signal_date or "")
        or str(capture.get("candidate_hash") or "") != str(candidate_hash or "")
        or capture.get("observation_only") is not True
        or capture.get("paper_authorized") is not False
        or capture.get("live_order_allowed") is not False
    ):
        blockers.append("observation_capture_contract_invalid")
    if str(capture.get("capture_contract_hash") or "") != _payload_hash(capture, "capture_contract_hash"):
        blockers.append("observation_capture_hash_invalid")
    if str(payload.get("capture_contract_hash") or "") != str(capture.get("capture_contract_hash") or ""):
        blockers.append("observation_capture_reference_mismatch")
    clock = dict(capture.get("clock_attestation") or {})
    if (
        capture.get("clock_attested") is not True
        or verify_trusted_clock_attestation(clock).get("status") != "PASS"
        or str(capture.get("clock_attestation_hash") or "") != str(clock.get("attestation_hash") or "")
    ):
        blockers.append("observation_clock_attestation_invalid")
    risk = dict(payload.get("risk_snapshot") or {})
    if risk and str(risk.get("risk_snapshot_hash") or "") != _payload_hash(risk, "risk_snapshot_hash"):
        blockers.append("observation_risk_snapshot_hash_invalid")
    if risk and str(payload.get("risk_snapshot_hash") or "") != str(risk.get("risk_snapshot_hash") or ""):
        blockers.append("observation_risk_snapshot_reference_mismatch")
    if str(payload.get("risk_gate_status") or "") == "PASS" and not risk:
        blockers.append("observation_pass_risk_snapshot_missing")
    state_contract = dict(payload.get("forward_state_contract") or {})
    state_verification = verify_forward_state_contract(
        state_contract,
        candidate_hash=candidate_hash,
        capture_contract=capture,
    )
    blockers.extend(state_verification.get("blockers") or [])
    if str(payload.get("forward_state_contract_hash") or "") != str(
        state_contract.get("forward_state_contract_hash") or ""
    ):
        blockers.append("observation_forward_state_contract_reference_mismatch")
    if (
        payload.get("observation_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("observation_execution_authority_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
    }


def _manifest_binding(
    manifest: dict[str, Any],
    *,
    observation: dict[str, Any],
    required_symbols: list[str],
) -> tuple[dict[str, Any], list[str]]:
    payload = dict(manifest or {})
    blockers: list[str] = []
    signal_date = str(observation.get("signal_date") or "")
    dataset_hash = str(observation.get("dataset_hash") or "")
    if payload.get("status") != "PASS":
        blockers.append("dataset_manifest_blocked")
    if str(payload.get("data_hash") or "") != dataset_hash:
        blockers.append("dataset_manifest_hash_observation_mismatch")
    if str(payload.get("last") or "") != signal_date:
        blockers.append("dataset_manifest_last_mismatch")
    manifest_symbols = sorted(str(symbol).upper() for symbol in payload.get("symbols") or [])
    if manifest_symbols != sorted(required_symbols):
        blockers.append("dataset_manifest_symbols_mismatch")

    market_calendar = dict(payload.get("market_calendar") or {})
    if market_calendar.get("status") != "PASS":
        blockers.append("market_calendar_contract_blocked")
    if str(market_calendar.get("contract_hash") or "") != _payload_hash(market_calendar, "contract_hash"):
        blockers.append("market_calendar_contract_hash_invalid")
    lifecycle = dict(payload.get("security_lifecycle") or {})
    adjustments = dict(payload.get("adjustment_evidence") or {})
    revisions = dict(payload.get("data_revision_evidence") or {})
    actions = dict(payload.get("corporate_actions") or {})
    for symbol in required_symbols:
        lifecycle_contract = dict(lifecycle.get(symbol) or {})
        adjustment = dict(adjustments.get(symbol) or {})
        accounting = dict(adjustment.get("return_accounting") or {})
        revision = dict(revisions.get(symbol) or {})
        if lifecycle_contract.get("status") != "PASS":
            blockers.append(f"security_lifecycle_blocked:{symbol}")
        expected_lifecycle_hash = _canonical_hash({
            key: value
            for key, value in lifecycle_contract.items()
            if key not in {"contract_hash", "rows"}
        })
        if str(lifecycle_contract.get("contract_hash") or "") != expected_lifecycle_hash:
            blockers.append(f"security_lifecycle_hash_invalid:{symbol}")
        if adjustment.get("backtest_eligible") is not True:
            blockers.append(f"adjustment_contract_blocked:{symbol}")
        if str(adjustment.get("evidence_hash") or "") != _payload_hash(adjustment, "evidence_hash"):
            blockers.append(f"adjustment_evidence_hash_invalid:{symbol}")
        if accounting.get("cash_execution_supported") is not True:
            blockers.append(f"cash_execution_accounting_unsupported:{symbol}")
        if accounting.get("double_count_protection") is not True:
            blockers.append(f"return_double_count_protection_missing:{symbol}")
        if (
            str(accounting.get("split_mode") or "") != "EMBEDDED_IN_ADJUSTED_SERIES"
            or str(accounting.get("dividend_mode") or "") != "EMBEDDED_IN_ADJUSTED_RETURN"
        ):
            blockers.append(f"forward_corporate_action_accounting_unsupported:{symbol}")
        if str(revision.get("status") or "PASS").upper() == "BLOCK":
            blockers.append(f"data_revision_blocked:{symbol}")
        if str(revision.get("evidence_hash") or "") != portfolio_revision_evidence_hash(revision):
            blockers.append(f"data_revision_evidence_hash_invalid:{symbol}")

    contract = {
        "schema_version": str(payload.get("schema_version") or ""),
        "data_hash": str(payload.get("data_hash") or ""),
        "market_calendar_hash": str(market_calendar.get("contract_hash") or ""),
        "security_lifecycle_hashes": {
            symbol: str(dict(lifecycle.get(symbol) or {}).get("contract_hash") or "")
            for symbol in sorted(required_symbols)
        },
        "adjustment_evidence_hashes": {
            symbol: str(dict(adjustments.get(symbol) or {}).get("evidence_hash") or "")
            for symbol in sorted(required_symbols)
        },
        "data_revision_evidence_hashes": {
            symbol: str(dict(revisions.get(symbol) or {}).get("evidence_hash") or "")
            for symbol in sorted(required_symbols)
        },
        "corporate_action_hashes": {
            symbol: _canonical_hash(list(actions.get(symbol) or []))
            for symbol in sorted(required_symbols)
        },
    }
    expected_manifest_hash = _canonical_hash(contract)
    if str(payload.get("manifest_hash") or "") != expected_manifest_hash:
        blockers.append("dataset_manifest_contract_hash_invalid")
    binding = {
        **contract,
        "manifest_hash": str(payload.get("manifest_hash") or ""),
        "first": str(payload.get("first") or ""),
        "last": str(payload.get("last") or ""),
        "row_count": int(payload.get("row_count") or 0),
        "benchmark_symbol": str(payload.get("benchmark_symbol") or "").upper(),
        "symbols": manifest_symbols,
        "sources": {
            str(symbol).upper(): str(source or "")
            for symbol, source in dict(payload.get("sources") or {}).items()
        },
    }
    binding["binding_hash"] = _canonical_hash(binding)
    return binding, blockers


def _normalize_market_rows(
    rows_by_symbol: dict[str, dict[str, Any]],
    *,
    signal_date: str,
    required_symbols: list[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    rows: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    for symbol in required_symbols:
        raw = dict(rows_by_symbol.get(symbol) or {})
        complete_source = (
            raw.get("complete")
            if "complete" in raw
            else raw.get("confirm")
            if "confirm" in raw
            else not raw.get("provisional")
            if isinstance(raw.get("provisional"), bool)
            else True
        )
        boolean_fields = {
            "complete": complete_source,
            "tradable": raw.get("tradable", True),
            "valuation_only": raw.get("valuation_only", False),
            "mandatory_cash_settlement": raw.get("mandatory_cash_settlement", False),
        }
        for name, value in boolean_fields.items():
            if not isinstance(value, bool):
                blockers.append(f"market_row_boolean_invalid:{symbol}:{name}")
        try:
            row = {
                "date": str(raw.get("date") or "")[:10],
                "ts_ms": int(raw.get("ts_ms") or raw.get("ts") or 0),
                "open": float(raw.get("open")),
                "high": float(raw.get("high")),
                "low": float(raw.get("low")),
                "close": float(raw.get("close")),
                "volume": float(raw.get("volume") or 0.0),
                "complete": complete_source if isinstance(complete_source, bool) else False,
                "tradable": raw.get("tradable") if isinstance(raw.get("tradable"), bool) else "tradable" not in raw,
                "trading_status": str(raw.get("trading_status") or "TRADABLE").upper(),
                "valuation_only": raw.get("valuation_only") if isinstance(raw.get("valuation_only"), bool) else False,
                "valuation_basis": str(raw.get("valuation_basis") or ""),
                "mandatory_cash_settlement": (
                    raw.get("mandatory_cash_settlement")
                    if isinstance(raw.get("mandatory_cash_settlement"), bool)
                    else False
                ),
                "lifecycle_event_hash": str(raw.get("lifecycle_event_hash") or ""),
            }
        except (TypeError, ValueError, OverflowError):
            blockers.append(f"market_row_invalid:{symbol}")
            continue
        prices = [row["open"], row["high"], row["low"], row["close"]]
        if row["date"] != signal_date:
            blockers.append(f"market_row_date_mismatch:{symbol}")
        if row["ts_ms"] <= 0:
            blockers.append(f"market_row_timestamp_invalid:{symbol}")
        if not row["complete"]:
            blockers.append(f"market_row_incomplete:{symbol}")
        if not all(math.isfinite(value) and value > 0 for value in prices):
            blockers.append(f"market_row_price_invalid:{symbol}")
        if not math.isfinite(row["volume"]) or row["volume"] < 0:
            blockers.append(f"market_row_volume_invalid:{symbol}")
        elif not math.isfinite(row["close"] * row["volume"]):
            blockers.append(f"market_row_dollar_volume_invalid:{symbol}")
        if row["high"] < max(row["open"], row["close"], row["low"]):
            blockers.append(f"market_row_high_invalid:{symbol}")
        if row["low"] > min(row["open"], row["close"], row["high"]):
            blockers.append(f"market_row_low_invalid:{symbol}")
        row["row_hash"] = _canonical_hash(row)
        rows[symbol] = row
    return rows, blockers


def _blocked(candidate_hash: str, settlement_date: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "schema_version": PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION,
        "status": "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_hash": str(candidate_hash or ""),
        "settlement_date": str(settlement_date or ""),
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_stored_settlement_integrity(settlement: dict[str, Any]) -> list[str]:
    payload = dict(settlement or {})
    blockers: list[str] = []
    if payload.get("schema_version") != PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION:
        blockers.append("settlement_schema_invalid")
    if payload.get("status") != "READY":
        blockers.append("settlement_not_ready")
    if str(payload.get("settlement_hash") or "") != _payload_hash(payload, "settlement_hash"):
        blockers.append("settlement_hash_invalid")
    snapshot = dict(payload.get("market_snapshot") or {})
    if str(snapshot.get("market_snapshot_hash") or "") != _payload_hash(snapshot, "market_snapshot_hash"):
        blockers.append("market_snapshot_hash_invalid")
    for account_name in ("strategy", "benchmark"):
        state = dict(dict(payload.get(account_name) or {}).get("state") or {})
        if not _verify_state_hash(state):
            blockers.append(f"{account_name}_state_hash_invalid")
    if (
        payload.get("observation_only") is not True
        or payload.get("simulation_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("settlement_execution_authority_invalid")
    return blockers


def _state(
    *,
    cash: float,
    quantities: dict[str, float],
    total_fees: float,
    turnover: float,
    peak_equity: float,
    max_drawdown_pct: float,
    order_count: int,
    execution_event_count: int,
    started: bool = True,
) -> dict[str, Any]:
    result = {
        "cash": _rounded(cash, 10),
        "quantities": {
            symbol: _rounded(max(_number(quantity), 0.0), 12)
            for symbol, quantity in sorted(quantities.items())
        },
        "total_fees": _rounded(total_fees, 10),
        "turnover": _rounded(turnover, 10),
        "peak_equity": _rounded(peak_equity, 10),
        "max_drawdown_pct": _rounded(max_drawdown_pct, 8),
        "order_count": int(order_count),
        "execution_event_count": int(execution_event_count),
        "started": bool(started),
    }
    result["state_hash"] = _canonical_hash(result)
    return result


def _execution_terms(
    *,
    requested_notional: float,
    liquidity: dict[str, Any],
    maximum_participation: float,
    impact_bps_at_full_participation: float,
    side: str,
) -> dict[str, Any]:
    median_dollar_volume = max(_number(liquidity.get("median_dollar_volume")), 0.0)
    capacity_notional = median_dollar_volume * maximum_participation
    capacity_limited = requested_notional > capacity_notional + 1e-9
    fill_notional = min(max(requested_notional, 0.0), max(capacity_notional, 0.0))
    participation = fill_notional / max(median_dollar_volume, 1e-12) if median_dollar_volume > 0 else 0.0
    ratio = participation / max(maximum_participation, 1e-12) if maximum_participation > 0 else 0.0
    impact_bps = impact_bps_at_full_participation * math.sqrt(max(0.0, min(ratio, 1.0)))
    return {
        "median_dollar_volume": median_dollar_volume,
        "capacity_notional": capacity_notional,
        "fill_notional": fill_notional,
        "participation_pct": participation * 100.0,
        "impact_bps": impact_bps,
        "exit_fallback": False,
        "capacity_limited": capacity_limited,
    }


def _apply_mandatory_cash_settlements(
    *,
    cash: float,
    quantities: dict[str, float],
    rows: dict[str, dict[str, Any]],
) -> tuple[float, list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    for symbol in sorted(quantities):
        quantity = max(_number(quantities.get(symbol)), 0.0)
        row = dict(rows.get(symbol) or {})
        if quantity <= 1e-12 or row.get("mandatory_cash_settlement") is not True:
            continue
        price = _number(row.get("open"))
        amount = quantity * price
        cash += amount
        quantities[symbol] = 0.0
        events.append({
            "event_type": "MANDATORY_CASH_SETTLEMENT",
            "symbol": symbol,
            "quantity": _rounded(quantity, 12),
            "price": _rounded(price, 8),
            "amount": _rounded(amount, 10),
            "lifecycle_event_hash": str(row.get("lifecycle_event_hash") or ""),
        })
    return cash, events


def _execute_strategy_decision(
    *,
    decision: dict[str, Any],
    source_signal_date: str,
    rows: dict[str, dict[str, Any]],
    previous_rows: dict[str, dict[str, Any]],
    quantities: dict[str, float],
    cash: float,
    spec: dict[str, Any],
) -> tuple[float, list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    blockers: list[str] = []
    orders: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    tradable_symbols = sorted(quantities)
    target_symbols = [str(symbol).upper() for symbol in decision.get("target_symbols") or []]
    if len(target_symbols) != len(set(target_symbols)):
        blockers.append("decision_target_symbols_duplicate")
    held_symbols = {symbol for symbol, quantity in quantities.items() if quantity > 1e-12}
    retained_symbols = {str(symbol).upper() for symbol in decision.get("retained_symbols") or []}
    invalid_retained = sorted(retained_symbols - held_symbols)
    if invalid_retained:
        blockers.extend(f"decision_retention_state_mismatch:{symbol}" for symbol in invalid_retained)
    invalid_targets = sorted(set(target_symbols) - set(tradable_symbols))
    if invalid_targets:
        blockers.extend(f"decision_target_outside_candidate:{symbol}" for symbol in invalid_targets)
    if decision.get("target_quantities_override"):
        blockers.append("state_external_quantity_override_unsupported")
    raw_allocation = _strict_number(decision.get("target_allocation_pct"))
    if raw_allocation is None or raw_allocation < 0:
        blockers.append("decision_target_allocation_invalid")
        allocation = 0.0
    else:
        allocation = raw_allocation / 100.0
    gross_limit = max(_number(spec.get("gross_target_pct"), 60.0) / 100.0, 0.0)
    if allocation > gross_limit + 1e-8:
        blockers.append("decision_target_allocation_above_frozen_gross_limit")
    raw_target_weights = {
        str(symbol).upper(): _strict_number(weight)
        for symbol, weight in dict(decision.get("target_weights") or {}).items()
    }
    if any(weight is None or weight < 0 for weight in raw_target_weights.values()):
        blockers.append("decision_target_weights_nonfinite_or_negative")
    target_weights = {
        symbol: float(weight)
        for symbol, weight in raw_target_weights.items()
        if weight is not None and weight >= 0
    }
    if target_symbols and not target_weights:
        target_weights = {symbol: 1.0 / len(target_symbols) for symbol in target_symbols}
    elif set(target_weights) != set(target_symbols):
        blockers.append("decision_target_weight_symbols_mismatch")
    if not target_symbols and allocation > 1e-12:
        blockers.append("decision_allocation_without_targets")
    weight_sum = sum(target_weights.get(symbol, 0.0) for symbol in target_symbols)
    max_position_weight = max(_number(spec.get("max_position_weight_pct"), 50.0) / 100.0, 0.0)
    if target_symbols and (weight_sum <= 0 or weight_sum > 1.000001):
        blockers.append("decision_target_weights_invalid")
    if any(target_weights.get(symbol, 0.0) > max_position_weight + 1e-8 for symbol in target_symbols):
        blockers.append("decision_position_weight_above_frozen_limit")
    if blockers:
        return cash, orders, events, blockers

    fee_rate = max(0.0, min(_number(spec.get("fee_rate"), 0.0005), 0.02))
    slippage_rate = max(0.0, min(_number(spec.get("slippage_bps"), 2.0), 500.0)) / 10_000.0
    minimum_trade_fraction = max(0.0, min(_number(spec.get("minimum_trade_pct"), 1.0), 100.0)) / 100.0
    entry_participation = max(0.0, min(_number(spec.get("max_entry_participation_pct"), 1.0), 100.0)) / 100.0
    exit_participation = max(0.0, min(_number(spec.get("max_exit_participation_pct"), 2.0), 100.0)) / 100.0
    maximum_entry_gap = max(0.0, min(_number(spec.get("max_entry_open_gap_pct"), 12.0), 100.0)) / 100.0
    impact_bps = max(0.0, min(_number(spec.get("impact_bps_at_full_participation"), 15.0), 500.0))
    open_prices = {symbol: _number(rows[symbol].get("open")) for symbol in tradable_symbols}
    equity_open = cash + sum(quantities[symbol] * open_prices[symbol] for symbol in tradable_symbols)
    minimum_trade_notional = equity_open * minimum_trade_fraction
    decision_liquidity = dict(decision.get("liquidity") or {})
    target_quantities = {
        symbol: (
            equity_open * allocation * target_weights.get(symbol, 0.0)
            / max(open_prices[symbol] * (1.0 + slippage_rate), 1e-12)
            if symbol in target_symbols else 0.0
        )
        for symbol in tradable_symbols
    }
    execution_ineligible = {str(symbol).upper() for symbol in decision.get("universe_ineligible_symbols") or []}
    for symbol in execution_ineligible:
        if symbol in target_quantities:
            target_quantities[symbol] = 0.0

    for symbol in tradable_symbols:
        sell_quantity = max(quantities[symbol] - target_quantities[symbol], 0.0)
        if sell_quantity <= 1e-12:
            continue
        requested_notional = sell_quantity * open_prices[symbol]
        if target_quantities[symbol] > 1e-12 and requested_notional < minimum_trade_notional:
            continue
        row = rows[symbol]
        if row.get("tradable") is not True:
            events.append({
                "event_type": "BLOCKED_NON_TRADABLE",
                "symbol": symbol,
                "side": "SELL",
                "requested_notional": _rounded(requested_notional, 8),
                "trading_status": str(row.get("trading_status") or "UNKNOWN"),
            })
            continue
        terms = _execution_terms(
            requested_notional=requested_notional,
            liquidity=dict(decision_liquidity.get(symbol) or {}),
            maximum_participation=exit_participation,
            impact_bps_at_full_participation=impact_bps,
            side="SELL",
        )
        execution_rate = slippage_rate + _number(terms["impact_bps"]) / 10_000.0
        execution_price = open_prices[symbol] * (1.0 - execution_rate)
        filled_quantity = min(
            sell_quantity,
            _number(terms["fill_notional"]) / max(execution_price, 1e-12),
        )
        if filled_quantity <= 1e-12:
            events.append({
                "event_type": "BLOCKED_NO_LIQUIDITY",
                "symbol": symbol,
                "side": "SELL",
                "requested_notional": _rounded(requested_notional, 8),
            })
            continue
        notional = filled_quantity * execution_price
        fee = notional * fee_rate
        cash += notional - fee
        quantities[symbol] = max(quantities[symbol] - filled_quantity, 0.0)
        orders.append({
            "signal_date": source_signal_date,
            "symbol": symbol,
            "side": "SELL",
            "requested_quantity": _rounded(sell_quantity, 12),
            "quantity": _rounded(filled_quantity, 12),
            "price": _rounded(execution_price, 10),
            "notional": _rounded(notional, 10),
            "fee": _rounded(fee, 10),
            "status": "PARTIAL" if filled_quantity + 1e-12 < sell_quantity else "FILLED",
            "median_dollar_volume": _rounded(_number(terms["median_dollar_volume"]), 2),
            "participation_pct": _rounded(_number(terms["participation_pct"]), 8),
            "impact_bps": _rounded(_number(terms["impact_bps"]), 8),
            "exit_liquidity_fallback": bool(terms["exit_fallback"]),
            "reason": "universe_membership_exit" if symbol in execution_ineligible else str(decision.get("reason") or ""),
            "fill_basis": "NEXT_BAR_OPEN",
        })

    for symbol in tradable_symbols:
        buy_quantity = max(target_quantities[symbol] - quantities[symbol], 0.0)
        if buy_quantity <= 1e-12:
            continue
        requested_notional = buy_quantity * open_prices[symbol]
        if quantities[symbol] > 1e-12 and requested_notional < minimum_trade_notional:
            continue
        row = rows[symbol]
        if row.get("tradable") is not True:
            events.append({
                "event_type": "BLOCKED_NON_TRADABLE",
                "symbol": symbol,
                "side": "BUY",
                "requested_notional": _rounded(requested_notional, 8),
                "trading_status": str(row.get("trading_status") or "UNKNOWN"),
            })
            continue
        previous_close = _number(dict(previous_rows.get(symbol) or {}).get("close"))
        if previous_close <= 0:
            blockers.append(f"previous_close_missing:{symbol}")
            continue
        open_gap = abs(open_prices[symbol] / previous_close - 1.0)
        if open_gap > maximum_entry_gap:
            events.append({
                "event_type": "BLOCKED_ENTRY_GAP",
                "symbol": symbol,
                "side": "BUY",
                "open_gap_pct": _rounded(open_gap * 100.0, 8),
                "maximum_open_gap_pct": _rounded(maximum_entry_gap * 100.0, 8),
                "requested_notional": _rounded(requested_notional, 8),
            })
            continue
        terms = _execution_terms(
            requested_notional=requested_notional,
            liquidity=dict(decision_liquidity.get(symbol) or {}),
            maximum_participation=entry_participation,
            impact_bps_at_full_participation=impact_bps,
            side="BUY",
        )
        if _number(terms["fill_notional"]) <= 0:
            events.append({
                "event_type": "BLOCKED_NO_LIQUIDITY",
                "symbol": symbol,
                "side": "BUY",
                "requested_notional": _rounded(requested_notional, 8),
            })
            continue
        execution_rate = slippage_rate + _number(terms["impact_bps"]) / 10_000.0
        execution_price = open_prices[symbol] * (1.0 + execution_rate)
        affordable = cash / max(execution_price * (1.0 + fee_rate), 1e-12)
        capacity_quantity = (
            _number(terms["fill_notional"]) / max(execution_price, 1e-12)
            if bool(terms["capacity_limited"])
            else buy_quantity
        )
        filled_quantity = min(buy_quantity, capacity_quantity, max(affordable, 0.0))
        if filled_quantity <= 1e-12:
            events.append({
                "event_type": "BLOCKED_INSUFFICIENT_CASH",
                "symbol": symbol,
                "side": "BUY",
                "requested_notional": _rounded(requested_notional, 8),
            })
            continue
        notional = filled_quantity * execution_price
        fee = notional * fee_rate
        cash -= notional + fee
        quantities[symbol] += filled_quantity
        orders.append({
            "signal_date": source_signal_date,
            "symbol": symbol,
            "side": "BUY",
            "requested_quantity": _rounded(buy_quantity, 12),
            "quantity": _rounded(filled_quantity, 12),
            "price": _rounded(execution_price, 10),
            "notional": _rounded(notional, 10),
            "fee": _rounded(fee, 10),
            "status": "PARTIAL" if filled_quantity + 1e-12 < buy_quantity else "FILLED",
            "open_gap_pct": _rounded(open_gap * 100.0, 8),
            "median_dollar_volume": _rounded(_number(terms["median_dollar_volume"]), 2),
            "participation_pct": _rounded(_number(terms["participation_pct"]), 8),
            "impact_bps": _rounded(_number(terms["impact_bps"]), 8),
            "reason": str(decision.get("reason") or ""),
            "fill_basis": "NEXT_BAR_OPEN",
        })
    return cash, orders, events, blockers


def _execute_benchmark_entry(
    *,
    cash: float,
    quantity: float,
    row: dict[str, Any],
    spec: dict[str, Any],
    source_signal_date: str,
) -> tuple[float, float, list[dict[str, Any]], list[str]]:
    if quantity > 1e-12:
        return cash, quantity, [], []
    if row.get("tradable") is not True:
        return cash, quantity, [], ["benchmark_not_tradable_at_initial_execution"]
    fee_rate = max(0.0, min(_number(spec.get("fee_rate"), 0.0005), 0.02))
    slippage_rate = max(0.0, min(_number(spec.get("slippage_bps"), 2.0), 500.0)) / 10_000.0
    allocation = min(max(_number(spec.get("gross_target_pct"), 60.0) / 100.0, 0.0), 1.0)
    if allocation <= 1e-12:
        return cash, quantity, [], []
    open_price = _number(row.get("open"))
    equity_open = cash + quantity * open_price
    budget = min(cash, equity_open * allocation)
    execution_price = open_price * (1.0 + slippage_rate)
    notional = budget / (1.0 + fee_rate)
    fee = notional * fee_rate
    filled_quantity = notional / max(execution_price, 1e-12)
    cash -= notional + fee
    quantity += filled_quantity
    order = {
        "signal_date": source_signal_date,
        "symbol": str(row.get("symbol") or ""),
        "side": "BUY",
        "requested_quantity": _rounded(filled_quantity, 12),
        "quantity": _rounded(filled_quantity, 12),
        "price": _rounded(execution_price, 10),
        "notional": _rounded(notional, 10),
        "fee": _rounded(fee, 10),
        "status": "FILLED",
        "reason": "buy_and_hold_benchmark_entry",
        "fill_basis": "NEXT_BAR_OPEN",
    }
    return cash, quantity, [order], []


def _observation_evidence(observation: dict[str, Any]) -> dict[str, Any]:
    capture = dict(observation.get("capture_contract") or {})
    return {
        "candidate_hash": str(observation.get("candidate_hash") or ""),
        "signal_date": str(observation.get("signal_date") or ""),
        "dataset_hash": str(observation.get("dataset_hash") or ""),
        "observation_hash": str(observation.get("observation_hash") or ""),
        "decision_hash": str(observation.get("decision_hash") or ""),
        "capture_contract_hash": str(observation.get("capture_contract_hash") or ""),
        "clock_attestation_hash": str(capture.get("clock_attestation_hash") or ""),
        "risk_snapshot_hash": str(observation.get("risk_snapshot_hash") or ""),
        "risk_gate_status": str(observation.get("risk_gate_status") or ""),
        "forward_state_contract_hash": str(observation.get("forward_state_contract_hash") or ""),
        "observed_at": int(observation.get("observed_at") or 0),
    }


def build_forward_performance_settlement(
    *,
    candidate: dict[str, Any],
    current_observation: dict[str, Any],
    dataset_manifest: dict[str, Any],
    market_rows: dict[str, dict[str, Any]],
    recorded_at: int,
    previous_settlement: dict[str, Any] | None = None,
    previous_observation: dict[str, Any] | None = None,
    previous_session_date: str = "",
    initial_cash: float = 100_000.0,
) -> dict[str, Any]:
    candidate_hash = str(candidate.get("candidate_hash") or "")
    settlement_date = str(current_observation.get("signal_date") or "")
    blockers: list[str] = []
    spec = dict(candidate.get("spec") or {})
    benchmark_symbol = str(spec.get("benchmark_symbol") or "SPY").upper()
    tradable_symbols = sorted({
        str(symbol).upper()
        for symbol in spec.get("tradable_symbols") or []
        if str(symbol).upper() != benchmark_symbol
    })
    required_symbols = sorted([benchmark_symbol, *tradable_symbols])
    parsed_initial_cash = _strict_number(initial_cash)
    clean_initial_cash = parsed_initial_cash if parsed_initial_cash is not None else 0.0
    frozen_settings: dict[str, Any] = {}
    try:
        frozen_settings = relative_strength_settings_from_spec(spec)
    except (TypeError, ValueError, OverflowError):
        blockers.append("candidate_numeric_settings_invalid")
    if frozen_settings:
        numeric_issues = relative_strength_numeric_contract_issues({
            **frozen_settings,
            "initial_cash": clean_initial_cash,
            "evaluation_start_index": None,
        })
        blockers.extend(f"candidate_numeric_contract:{issue}" for issue in numeric_issues)
    if not candidate_hash:
        blockers.append("candidate_hash_missing")
    if not settlement_date:
        blockers.append("settlement_date_missing")
    if clean_initial_cash <= 0:
        blockers.append("initial_cash_invalid")
    if (
        candidate.get("research_only") is not True
        or candidate.get("paper_authorized") is not False
        or candidate.get("live_order_allowed") is not False
    ):
        blockers.append("candidate_execution_authority_invalid")
    current_verification = verify_shadow_observation(
        current_observation,
        candidate_hash=candidate_hash,
        signal_date=settlement_date,
    )
    blockers.extend(f"current:{item}" for item in current_verification.get("blockers") or [])
    if int(recorded_at or 0) < int(current_observation.get("observed_at") or 0):
        blockers.append("settlement_recorded_before_observation")

    manifest_binding, manifest_blockers = _manifest_binding(
        dataset_manifest,
        observation=current_observation,
        required_symbols=required_symbols,
    )
    blockers.extend(manifest_blockers)
    rows, row_blockers = _normalize_market_rows(
        market_rows,
        signal_date=settlement_date,
        required_symbols=required_symbols,
    )
    blockers.extend(row_blockers)
    for symbol, row in rows.items():
        row["symbol"] = symbol
        row["row_hash"] = _canonical_hash({key: value for key, value in row.items() if key != "row_hash"})
    baseline = previous_settlement is None
    if baseline != (previous_observation is None):
        blockers.append("previous_settlement_observation_pair_invalid")

    previous_verification: dict[str, Any] = {"status": "PASS", "blockers": []}
    if previous_settlement is not None:
        previous_integrity_blockers = _verify_stored_settlement_integrity(previous_settlement)
        blockers.extend(f"previous:{item}" for item in previous_integrity_blockers)
        previous_date = str(previous_settlement.get("settlement_date") or "")
        if str(previous_session_date or "") != previous_date:
            blockers.append("market_session_chain_gap")
        if not previous_date or settlement_date <= previous_date:
            blockers.append("settlement_date_not_increasing")
        previous_observation_payload = dict(previous_observation or {})
        source_verification = verify_shadow_observation(
            previous_observation_payload,
            candidate_hash=candidate_hash,
            signal_date=previous_date,
        )
        blockers.extend(f"source:{item}" for item in source_verification.get("blockers") or [])
        prior_current_evidence = dict(dict(previous_settlement.get("observation_evidence") or {}).get("current") or {})
        if str(prior_current_evidence.get("observation_hash") or "") != str(
            previous_observation_payload.get("observation_hash") or ""
        ):
            blockers.append("source_observation_not_bound_to_previous_settlement")
        if str(previous_observation_payload.get("forward_state_contract_hash") or "") != str(
            current_observation.get("forward_state_contract_hash") or ""
        ):
            blockers.append("forward_state_contract_changed_within_candidate")
        if str(previous_settlement.get("candidate_hash") or "") != candidate_hash:
            blockers.append("previous_settlement_candidate_mismatch")
    if blockers:
        return _blocked(candidate_hash, settlement_date, blockers)

    market_snapshot = {
        "dataset_binding": manifest_binding,
        "rows": rows,
    }
    market_snapshot["market_snapshot_hash"] = _canonical_hash(market_snapshot)

    if baseline:
        strategy_cash = clean_initial_cash
        strategy_quantities = {symbol: 0.0 for symbol in tradable_symbols}
        strategy_fees = 0.0
        strategy_turnover = 0.0
        strategy_peak = clean_initial_cash
        strategy_max_drawdown = 0.0
        strategy_order_count = 0
        strategy_event_count = 0
        benchmark_cash = clean_initial_cash
        benchmark_quantity = 0.0
        benchmark_fees = 0.0
        benchmark_turnover = 0.0
        benchmark_peak = clean_initial_cash
        benchmark_max_drawdown = 0.0
        benchmark_order_count = 0
        benchmark_event_count = 0
        benchmark_started = False
        strategy_orders: list[dict[str, Any]] = []
        strategy_events: list[dict[str, Any]] = []
        benchmark_orders: list[dict[str, Any]] = []
        benchmark_events: list[dict[str, Any]] = []
        execution_status = "BASELINE_AWAITING_NEXT_OPEN"
        source_observation_payload: dict[str, Any] = {}
        source_decision: dict[str, Any] = {}
    else:
        prior_strategy = dict(dict(previous_settlement.get("strategy") or {}).get("state") or {})
        prior_benchmark = dict(dict(previous_settlement.get("benchmark") or {}).get("state") or {})
        strategy_cash = _number(prior_strategy.get("cash"))
        strategy_quantities = {
            symbol: max(_number(dict(prior_strategy.get("quantities") or {}).get(symbol)), 0.0)
            for symbol in tradable_symbols
        }
        strategy_fees = _number(prior_strategy.get("total_fees"))
        strategy_turnover = _number(prior_strategy.get("turnover"))
        strategy_peak = _number(prior_strategy.get("peak_equity"), clean_initial_cash)
        strategy_max_drawdown = _number(prior_strategy.get("max_drawdown_pct"))
        strategy_order_count = int(prior_strategy.get("order_count") or 0)
        strategy_event_count = int(prior_strategy.get("execution_event_count") or 0)
        benchmark_cash = _number(prior_benchmark.get("cash"))
        benchmark_quantity = max(_number(dict(prior_benchmark.get("quantities") or {}).get(benchmark_symbol)), 0.0)
        benchmark_fees = _number(prior_benchmark.get("total_fees"))
        benchmark_turnover = _number(prior_benchmark.get("turnover"))
        benchmark_peak = _number(prior_benchmark.get("peak_equity"), clean_initial_cash)
        benchmark_max_drawdown = _number(prior_benchmark.get("max_drawdown_pct"))
        benchmark_order_count = int(prior_benchmark.get("order_count") or 0)
        benchmark_event_count = int(prior_benchmark.get("execution_event_count") or 0)
        if not isinstance(prior_benchmark.get("started"), bool):
            return _blocked(candidate_hash, settlement_date, ["benchmark_started_flag_invalid"])
        benchmark_started = prior_benchmark.get("started") is True
        previous_rows = dict(dict(previous_settlement.get("market_snapshot") or {}).get("rows") or {})

        strategy_cash, lifecycle_events = _apply_mandatory_cash_settlements(
            cash=strategy_cash,
            quantities=strategy_quantities,
            rows=rows,
        )
        strategy_events = list(lifecycle_events)
        source_observation_payload = dict(previous_observation or {})
        source_decision = dict(source_observation_payload.get("decision") or {})
        if str(source_observation_payload.get("risk_gate_status") or "") != "PASS":
            strategy_orders = []
            strategy_events.append({
                "event_type": "BLOCKED_BY_CAPTURED_RISK_GATE",
                "signal_date": str(source_observation_payload.get("signal_date") or ""),
                "risk_snapshot_hash": str(source_observation_payload.get("risk_snapshot_hash") or ""),
            })
            execution_status = "RISK_BLOCKED"
        elif source_decision.get("execute") is False:
            strategy_orders = []
            execution_status = "NO_ACTION"
        elif source_decision.get("execute") is True:
            strategy_cash, strategy_orders, decision_events, execution_blockers = _execute_strategy_decision(
                decision=source_decision,
                source_signal_date=str(source_observation_payload.get("signal_date") or ""),
                rows=rows,
                previous_rows=previous_rows,
                quantities=strategy_quantities,
                cash=strategy_cash,
                spec=frozen_settings,
            )
            if execution_blockers:
                return _blocked(candidate_hash, settlement_date, execution_blockers)
            strategy_events.extend(decision_events)
            execution_status = "EXECUTED" if strategy_orders else "EXECUTED_NO_FILL"
        else:
            return _blocked(candidate_hash, settlement_date, ["source_decision_execute_flag_invalid"])
        strategy_fees += sum(_number(order.get("fee")) for order in strategy_orders)
        strategy_turnover += sum(_number(order.get("notional")) for order in strategy_orders)
        strategy_order_count += len(strategy_orders)
        strategy_event_count += len(strategy_events)

        benchmark_quantities = {benchmark_symbol: benchmark_quantity}
        benchmark_cash, benchmark_events = _apply_mandatory_cash_settlements(
            cash=benchmark_cash,
            quantities=benchmark_quantities,
            rows={benchmark_symbol: rows[benchmark_symbol]},
        )
        benchmark_quantity = benchmark_quantities[benchmark_symbol]
        benchmark_cash, benchmark_quantity, benchmark_orders, benchmark_blockers = _execute_benchmark_entry(
            cash=benchmark_cash,
            quantity=benchmark_quantity,
            row=rows[benchmark_symbol],
            spec=frozen_settings,
            source_signal_date=str(source_observation_payload.get("signal_date") or ""),
        )
        if benchmark_blockers:
            return _blocked(candidate_hash, settlement_date, benchmark_blockers)
        benchmark_started = benchmark_started or bool(benchmark_orders) or benchmark_quantity > 1e-12
        benchmark_fees += sum(_number(order.get("fee")) for order in benchmark_orders)
        benchmark_turnover += sum(_number(order.get("notional")) for order in benchmark_orders)
        benchmark_order_count += len(benchmark_orders)
        benchmark_event_count += len(benchmark_events)

    strategy_position_values = {
        symbol: strategy_quantities[symbol] * _number(rows[symbol].get("close"))
        for symbol in tradable_symbols
        if strategy_quantities[symbol] > 1e-12
    }
    strategy_position_value = sum(strategy_position_values.values())
    strategy_equity = strategy_cash + strategy_position_value
    strategy_peak = max(strategy_peak, strategy_equity)
    strategy_drawdown = max(0.0, 1.0 - strategy_equity / max(strategy_peak, 1e-12)) * 100.0
    strategy_max_drawdown = max(strategy_max_drawdown, strategy_drawdown)
    benchmark_position_value = benchmark_quantity * _number(rows[benchmark_symbol].get("close"))
    benchmark_equity = benchmark_cash + benchmark_position_value
    benchmark_peak = max(benchmark_peak, benchmark_equity)
    benchmark_drawdown = max(0.0, 1.0 - benchmark_equity / max(benchmark_peak, 1e-12)) * 100.0
    benchmark_max_drawdown = max(benchmark_max_drawdown, benchmark_drawdown)

    if baseline:
        prior_strategy_equity = clean_initial_cash
        prior_benchmark_equity = clean_initial_cash
    else:
        prior_strategy_equity = _number(dict(previous_settlement.get("strategy") or {}).get("equity"), clean_initial_cash)
        prior_benchmark_equity = _number(dict(previous_settlement.get("benchmark") or {}).get("equity"), clean_initial_cash)
    strategy_daily_return = strategy_equity / max(prior_strategy_equity, 1e-12) - 1.0 if not baseline else 0.0
    benchmark_daily_return = benchmark_equity / max(prior_benchmark_equity, 1e-12) - 1.0 if not baseline else 0.0

    strategy_state = _state(
        cash=strategy_cash,
        quantities=strategy_quantities,
        total_fees=strategy_fees,
        turnover=strategy_turnover,
        peak_equity=strategy_peak,
        max_drawdown_pct=strategy_max_drawdown,
        order_count=strategy_order_count,
        execution_event_count=strategy_event_count,
    )
    benchmark_state = _state(
        cash=benchmark_cash,
        quantities={benchmark_symbol: benchmark_quantity},
        total_fees=benchmark_fees,
        turnover=benchmark_turnover,
        peak_equity=benchmark_peak,
        max_drawdown_pct=benchmark_max_drawdown,
        order_count=benchmark_order_count,
        execution_event_count=benchmark_event_count,
        started=benchmark_started,
    )
    source_evidence = _observation_evidence(source_observation_payload) if source_observation_payload else {}
    current_evidence = _observation_evidence(current_observation)
    settlement = {
        "schema_version": PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION,
        "status": "READY",
        "blockers": [],
        "settlement_type": "BASELINE" if baseline else "DAILY_CLOSE",
        "candidate_hash": candidate_hash,
        "settlement_date": settlement_date,
        "recorded_at": int(recorded_at),
        "previous_session_date": str(previous_session_date or ""),
        "previous_settlement_hash": str((previous_settlement or {}).get("settlement_hash") or ""),
        "execution_model": PORTFOLIO_FORWARD_EXECUTION_MODEL,
        "account_contract": {
            "initial_cash": _rounded(clean_initial_cash, 2),
            "currency": "USD",
            "strategy_start_policy": "CASH_UNTIL_FIRST_CAPTURED_EXECUTABLE_DECISION",
            "decision_execution_policy": "CAPTURED_CLOSE_TO_NEXT_SESSION_OPEN",
            "benchmark_policy": "SPY_BUY_AND_HOLD_AT_FROZEN_GROSS_TARGET",
            "benchmark_symbol": benchmark_symbol,
            "benchmark_target_pct": _rounded(_number(spec.get("gross_target_pct"), 60.0), 8),
            "fee_rate": _rounded(_number(spec.get("fee_rate"), 0.0005), 8),
            "slippage_bps": _rounded(_number(spec.get("slippage_bps"), 2.0), 8),
            "impact_bps_at_full_participation": _rounded(
                _number(spec.get("impact_bps_at_full_participation"), 15.0), 8
            ),
        },
        "observation_evidence": {
            "source": source_evidence,
            "current": current_evidence,
        },
        "market_snapshot": market_snapshot,
        "decision_execution": {
            "status": execution_status,
            "source_signal_date": str(source_observation_payload.get("signal_date") or ""),
            "source_decision_hash": str(source_observation_payload.get("decision_hash") or ""),
            "reason": str(source_decision.get("reason") or ""),
            "execute": source_decision.get("execute") is True if source_decision else False,
            "risk_gate_status": str(source_observation_payload.get("risk_gate_status") or ""),
        },
        "strategy": {
            "state": strategy_state,
            "orders": strategy_orders,
            "execution_events": strategy_events,
            "positions": {
                symbol: {
                    "quantity": _rounded(strategy_quantities[symbol], 12),
                    "close": _rounded(_number(rows[symbol].get("close")), 8),
                    "market_value": _rounded(value, 8),
                }
                for symbol, value in sorted(strategy_position_values.items())
            },
            "position_value": _rounded(strategy_position_value, 8),
            "equity": _rounded(strategy_equity, 8),
            "gross_exposure_pct": _rounded(strategy_position_value / max(strategy_equity, 1e-12) * 100.0, 8),
            "daily_return_pct": _rounded(strategy_daily_return * 100.0, 8),
            "cumulative_return_pct": _rounded((strategy_equity / clean_initial_cash - 1.0) * 100.0, 8),
            "drawdown_pct": _rounded(strategy_drawdown, 8),
        },
        "benchmark": {
            "state": benchmark_state,
            "orders": benchmark_orders,
            "execution_events": benchmark_events,
            "position_value": _rounded(benchmark_position_value, 8),
            "equity": _rounded(benchmark_equity, 8),
            "gross_exposure_pct": _rounded(benchmark_position_value / max(benchmark_equity, 1e-12) * 100.0, 8),
            "daily_return_pct": _rounded(benchmark_daily_return * 100.0, 8),
            "cumulative_return_pct": _rounded((benchmark_equity / clean_initial_cash - 1.0) * 100.0, 8),
            "drawdown_pct": _rounded(benchmark_drawdown, 8),
        },
        "active_return_pct": _rounded((strategy_daily_return - benchmark_daily_return) * 100.0, 8),
        "cumulative_excess_return_pct": _rounded(
            (strategy_equity / clean_initial_cash - benchmark_equity / clean_initial_cash) * 100.0,
            8,
        ),
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    settlement["settlement_hash"] = _payload_hash(settlement, "settlement_hash")
    return settlement


def _verify_state_hash(state: dict[str, Any]) -> bool:
    clean = dict(state)
    supplied = str(clean.pop("state_hash", ""))
    return bool(supplied) and supplied == _canonical_hash(clean)


def _verify_account_transition(
    *,
    account_name: str,
    account: dict[str, Any],
    previous_account: dict[str, Any] | None,
    initial_cash: float,
    close_prices: dict[str, float],
) -> list[str]:
    blockers: list[str] = []
    state = dict(account.get("state") or {})
    quantities = {
        str(symbol): _number(quantity)
        for symbol, quantity in dict(state.get("quantities") or {}).items()
    }
    cash = _number(state.get("cash"), -1.0)
    if cash < -1e-5:
        blockers.append(f"{account_name}_cash_negative")
    if any(quantity < -1e-9 for quantity in quantities.values()):
        blockers.append(f"{account_name}_quantity_negative")
    if not _verify_state_hash(state):
        blockers.append(f"{account_name}_state_hash_invalid")
    expected_position_value = sum(
        quantity * close_prices.get(symbol, 0.0)
        for symbol, quantity in quantities.items()
    )
    expected_equity = cash + expected_position_value
    if not _close(account.get("position_value"), expected_position_value, tolerance=2e-4):
        blockers.append(f"{account_name}_position_value_invalid")
    if not _close(account.get("equity"), expected_equity, tolerance=2e-4):
        blockers.append(f"{account_name}_equity_invalid")
    expected_gross_exposure = expected_position_value / max(expected_equity, 1e-12) * 100.0
    if not _close(account.get("gross_exposure_pct"), expected_gross_exposure, tolerance=2e-5):
        blockers.append(f"{account_name}_gross_exposure_invalid")
    expected_cumulative_return = (expected_equity / max(initial_cash, 1e-12) - 1.0) * 100.0
    if not _close(account.get("cumulative_return_pct"), expected_cumulative_return, tolerance=2e-5):
        blockers.append(f"{account_name}_cumulative_return_invalid")
    orders = [dict(item) for item in account.get("orders") or []]
    events = [dict(item) for item in account.get("execution_events") or []]
    if previous_account is None:
        if orders or events:
            blockers.append(f"{account_name}_baseline_contains_execution")
        if not _close(cash, initial_cash) or any(abs(quantity) > 1e-9 for quantity in quantities.values()):
            blockers.append(f"{account_name}_baseline_state_invalid")
        if not _close(state.get("total_fees"), 0.0) or not _close(state.get("turnover"), 0.0):
            blockers.append(f"{account_name}_baseline_costs_invalid")
        if not _close(state.get("peak_equity"), initial_cash):
            blockers.append(f"{account_name}_baseline_peak_invalid")
        if not _close(state.get("max_drawdown_pct"), 0.0) or not _close(account.get("drawdown_pct"), 0.0):
            blockers.append(f"{account_name}_baseline_drawdown_invalid")
        return blockers

    previous_state = dict(previous_account.get("state") or {})
    expected_cash = _number(previous_state.get("cash"))
    expected_quantities = {
        str(symbol): _number(quantity)
        for symbol, quantity in dict(previous_state.get("quantities") or {}).items()
    }
    for symbol in quantities:
        expected_quantities.setdefault(symbol, 0.0)
    for event in events:
        if str(event.get("event_type") or "") != "MANDATORY_CASH_SETTLEMENT":
            continue
        symbol = str(event.get("symbol") or "")
        quantity = _number(event.get("quantity"))
        amount = _number(event.get("amount"))
        if quantity < -1e-9 or amount < -1e-6:
            blockers.append(f"{account_name}_cash_settlement_invalid")
            continue
        if not _close(expected_quantities.get(symbol), quantity, tolerance=1e-6):
            blockers.append(f"{account_name}_cash_settlement_quantity_invalid")
        expected_quantities[symbol] = 0.0
        expected_cash += amount
    order_fees = 0.0
    order_turnover = 0.0
    for order in orders:
        symbol = str(order.get("symbol") or "")
        side = str(order.get("side") or "").upper()
        quantity = _number(order.get("quantity"), -1.0)
        price = _number(order.get("price"), -1.0)
        notional = _number(order.get("notional"), -1.0)
        fee = _number(order.get("fee"), -1.0)
        if quantity <= 0 or price <= 0 or notional <= 0 or fee < 0:
            blockers.append(f"{account_name}_order_values_invalid")
            continue
        if not _close(notional, quantity * price, tolerance=2e-4):
            blockers.append(f"{account_name}_order_notional_invalid")
        expected_quantities.setdefault(symbol, 0.0)
        if side == "BUY":
            expected_quantities[symbol] += quantity
            expected_cash -= notional + fee
        elif side == "SELL":
            expected_quantities[symbol] -= quantity
            expected_cash += notional - fee
        else:
            blockers.append(f"{account_name}_order_side_invalid")
        order_fees += fee
        order_turnover += notional
    if not _close(cash, expected_cash, tolerance=4e-4):
        blockers.append(f"{account_name}_cash_transition_invalid")
    for symbol in sorted(set(expected_quantities) | set(quantities)):
        if not _close(quantities.get(symbol), expected_quantities.get(symbol), tolerance=2e-7):
            blockers.append(f"{account_name}_quantity_transition_invalid:{symbol}")
    if not _close(
        state.get("total_fees"),
        _number(previous_state.get("total_fees")) + order_fees,
        tolerance=4e-4,
    ):
        blockers.append(f"{account_name}_fee_transition_invalid")
    if not _close(
        state.get("turnover"),
        _number(previous_state.get("turnover")) + order_turnover,
        tolerance=4e-4,
    ):
        blockers.append(f"{account_name}_turnover_transition_invalid")
    if int(state.get("order_count") or 0) != int(previous_state.get("order_count") or 0) + len(orders):
        blockers.append(f"{account_name}_order_count_invalid")
    if int(state.get("execution_event_count") or 0) != int(
        previous_state.get("execution_event_count") or 0
    ) + len(events):
        blockers.append(f"{account_name}_event_count_invalid")
    expected_peak = max(_number(previous_state.get("peak_equity"), initial_cash), expected_equity)
    expected_drawdown = max(0.0, 1.0 - expected_equity / max(expected_peak, 1e-12)) * 100.0
    expected_max_drawdown = max(_number(previous_state.get("max_drawdown_pct")), expected_drawdown)
    if not _close(state.get("peak_equity"), expected_peak, tolerance=2e-4):
        blockers.append(f"{account_name}_peak_transition_invalid")
    if not _close(account.get("drawdown_pct"), expected_drawdown, tolerance=2e-5):
        blockers.append(f"{account_name}_drawdown_invalid")
    if not _close(state.get("max_drawdown_pct"), expected_max_drawdown, tolerance=2e-5):
        blockers.append(f"{account_name}_max_drawdown_transition_invalid")
    return blockers


def verify_forward_performance_settlement(
    settlement: dict[str, Any],
    previous_settlement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(settlement or {})
    blockers: list[str] = []
    if payload.get("schema_version") != PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION:
        blockers.append("settlement_schema_invalid")
    if payload.get("status") != "READY":
        blockers.append("settlement_not_ready")
    if not str(payload.get("candidate_hash") or "") or not str(payload.get("settlement_date") or ""):
        blockers.append("settlement_identity_missing")
    if str(payload.get("settlement_hash") or "") != _payload_hash(payload, "settlement_hash"):
        blockers.append("settlement_hash_invalid")
    if payload.get("execution_model") != PORTFOLIO_FORWARD_EXECUTION_MODEL:
        blockers.append("settlement_execution_model_invalid")
    if (
        payload.get("observation_only") is not True
        or payload.get("simulation_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("settlement_execution_authority_invalid")

    snapshot = dict(payload.get("market_snapshot") or {})
    supplied_snapshot_hash = str(snapshot.get("market_snapshot_hash") or "")
    if supplied_snapshot_hash != _payload_hash(snapshot, "market_snapshot_hash"):
        blockers.append("market_snapshot_hash_invalid")
    rows = dict(snapshot.get("rows") or {})
    settlement_date = str(payload.get("settlement_date") or "")
    close_prices: dict[str, float] = {}
    for symbol, raw_row in rows.items():
        row = dict(raw_row or {})
        supplied_row_hash = str(row.get("row_hash") or "")
        if supplied_row_hash != _payload_hash(row, "row_hash"):
            blockers.append(f"market_row_hash_invalid:{symbol}")
        if str(row.get("date") or "") != settlement_date:
            blockers.append(f"market_row_settlement_date_mismatch:{symbol}")
        prices = [_number(row.get(key), -1.0) for key in ("open", "high", "low", "close")]
        if row.get("complete") is not True:
            blockers.append(f"market_row_incomplete:{symbol}")
        if not all(value > 0 for value in prices):
            blockers.append(f"market_row_price_invalid:{symbol}")
        elif prices[1] < max(prices[0], prices[2], prices[3]) or prices[2] > min(prices[0], prices[1], prices[3]):
            blockers.append(f"market_row_ohlc_invalid:{symbol}")
        if _number(row.get("volume"), -1.0) < 0:
            blockers.append(f"market_row_volume_invalid:{symbol}")
        elif not math.isfinite(prices[3] * _number(row.get("volume"), -1.0)):
            blockers.append(f"market_row_dollar_volume_invalid:{symbol}")
        close_prices[str(symbol)] = _number(row.get("close"))
    binding = dict(snapshot.get("dataset_binding") or {})
    supplied_binding_hash = str(binding.get("binding_hash") or "")
    if supplied_binding_hash != _payload_hash(binding, "binding_hash"):
        blockers.append("dataset_binding_hash_invalid")
    manifest_contract = {
        "schema_version": str(binding.get("schema_version") or ""),
        "data_hash": str(binding.get("data_hash") or ""),
        "market_calendar_hash": str(binding.get("market_calendar_hash") or ""),
        "security_lifecycle_hashes": dict(binding.get("security_lifecycle_hashes") or {}),
        "adjustment_evidence_hashes": dict(binding.get("adjustment_evidence_hashes") or {}),
        "data_revision_evidence_hashes": dict(binding.get("data_revision_evidence_hashes") or {}),
        "corporate_action_hashes": dict(binding.get("corporate_action_hashes") or {}),
    }
    if str(binding.get("manifest_hash") or "") != _canonical_hash(manifest_contract):
        blockers.append("dataset_manifest_hash_invalid")
    current_evidence = dict(dict(payload.get("observation_evidence") or {}).get("current") or {})
    if (
        str(current_evidence.get("candidate_hash") or "") != str(payload.get("candidate_hash") or "")
        or str(current_evidence.get("signal_date") or "") != settlement_date
        or str(current_evidence.get("dataset_hash") or "") != str(binding.get("data_hash") or "")
    ):
        blockers.append("current_observation_binding_invalid")
    if int(payload.get("recorded_at") or 0) < int(current_evidence.get("observed_at") or 0):
        blockers.append("settlement_recorded_before_current_observation")

    contract = dict(payload.get("account_contract") or {})
    initial_cash = _number(contract.get("initial_cash"), -1.0)
    if initial_cash <= 0:
        blockers.append("account_initial_cash_invalid")
    strategy = dict(payload.get("strategy") or {})
    benchmark = dict(payload.get("benchmark") or {})
    baseline = payload.get("settlement_type") == "BASELINE"
    if baseline != (previous_settlement is None):
        blockers.append("settlement_chain_baseline_invalid")
    if previous_settlement is None:
        if str(payload.get("previous_settlement_hash") or "") or str(payload.get("previous_session_date") or ""):
            blockers.append("baseline_previous_link_present")
        if dict(dict(payload.get("observation_evidence") or {}).get("source") or {}):
            blockers.append("baseline_source_observation_present")
    else:
        previous_hash = str(previous_settlement.get("settlement_hash") or "")
        previous_date = str(previous_settlement.get("settlement_date") or "")
        if str(payload.get("previous_settlement_hash") or "") != previous_hash:
            blockers.append("previous_settlement_hash_mismatch")
        if str(payload.get("previous_session_date") or "") != previous_date:
            blockers.append("previous_session_date_mismatch")
        if settlement_date <= previous_date:
            blockers.append("settlement_chain_date_not_increasing")
        if str(previous_settlement.get("candidate_hash") or "") != str(payload.get("candidate_hash") or ""):
            blockers.append("settlement_chain_candidate_mismatch")
        source = dict(dict(payload.get("observation_evidence") or {}).get("source") or {})
        prior_current = dict(dict(previous_settlement.get("observation_evidence") or {}).get("current") or {})
        if (
            str(source.get("signal_date") or "") != previous_date
            or str(source.get("observation_hash") or "") != str(prior_current.get("observation_hash") or "")
            or str(source.get("decision_hash") or "") != str(
                dict(payload.get("decision_execution") or {}).get("source_decision_hash") or ""
            )
        ):
            blockers.append("source_observation_chain_invalid")
        if str(source.get("forward_state_contract_hash") or "") != str(
            current_evidence.get("forward_state_contract_hash") or ""
        ):
            blockers.append("forward_state_contract_chain_mismatch")

    blockers.extend(_verify_account_transition(
        account_name="strategy",
        account=strategy,
        previous_account=dict(previous_settlement.get("strategy") or {}) if previous_settlement else None,
        initial_cash=initial_cash,
        close_prices=close_prices,
    ))
    blockers.extend(_verify_account_transition(
        account_name="benchmark",
        account=benchmark,
        previous_account=dict(previous_settlement.get("benchmark") or {}) if previous_settlement else None,
        initial_cash=initial_cash,
        close_prices=close_prices,
    ))
    if previous_settlement is not None:
        previous_strategy_equity = _number(dict(previous_settlement.get("strategy") or {}).get("equity"))
        previous_benchmark_equity = _number(dict(previous_settlement.get("benchmark") or {}).get("equity"))
        expected_strategy_return = _number(strategy.get("equity")) / max(previous_strategy_equity, 1e-12) - 1.0
        expected_benchmark_return = _number(benchmark.get("equity")) / max(previous_benchmark_equity, 1e-12) - 1.0
    else:
        expected_strategy_return = 0.0
        expected_benchmark_return = 0.0
    decision_execution = dict(payload.get("decision_execution") or {})
    decision_status = str(decision_execution.get("status") or "")
    strategy_orders = list(strategy.get("orders") or [])
    if previous_settlement is None:
        if decision_status != "BASELINE_AWAITING_NEXT_OPEN":
            blockers.append("baseline_decision_execution_status_invalid")
    elif str(decision_execution.get("risk_gate_status") or "") != "PASS":
        if decision_status != "RISK_BLOCKED" or strategy_orders:
            blockers.append("risk_blocked_decision_execution_invalid")
    elif decision_execution.get("execute") is False:
        if decision_status != "NO_ACTION" or strategy_orders:
            blockers.append("no_action_decision_execution_invalid")
    elif decision_execution.get("execute") is not True:
        blockers.append("decision_execution_flag_invalid")
    elif decision_status not in {"EXECUTED", "EXECUTED_NO_FILL"}:
        blockers.append("executable_decision_status_invalid")
    if not _close(strategy.get("daily_return_pct"), expected_strategy_return * 100.0, tolerance=2e-5):
        blockers.append("strategy_daily_return_invalid")
    if not _close(benchmark.get("daily_return_pct"), expected_benchmark_return * 100.0, tolerance=2e-5):
        blockers.append("benchmark_daily_return_invalid")
    if not _close(
        payload.get("active_return_pct"),
        (expected_strategy_return - expected_benchmark_return) * 100.0,
        tolerance=2e-5,
    ):
        blockers.append("active_return_invalid")
    expected_excess = (
        _number(strategy.get("equity")) / max(initial_cash, 1e-12)
        - _number(benchmark.get("equity")) / max(initial_cash, 1e-12)
    ) * 100.0
    if not _close(payload.get("cumulative_excess_return_pct"), expected_excess, tolerance=2e-5):
        blockers.append("cumulative_excess_return_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_hash": str(payload.get("candidate_hash") or ""),
        "settlement_date": settlement_date,
        "settlement_hash": str(payload.get("settlement_hash") or ""),
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class PortfolioForwardPerformanceLedger:
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
                CREATE TABLE IF NOT EXISTS portfolio_forward_performance_settlements (
                    candidate_hash TEXT NOT NULL,
                    settlement_date TEXT NOT NULL,
                    settlement_hash TEXT NOT NULL UNIQUE,
                    previous_settlement_hash TEXT NOT NULL,
                    current_observation_hash TEXT NOT NULL,
                    source_decision_hash TEXT NOT NULL,
                    dataset_hash TEXT NOT NULL,
                    recorded_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(candidate_hash, settlement_date)
                )
            """)

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return json.loads(str(row["payload_json"])) if row else None

    def settlement(self, candidate_hash: str, settlement_date: str) -> dict[str, Any] | None:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM portfolio_forward_performance_settlements "
                "WHERE candidate_hash = ? AND settlement_date = ?",
                (str(candidate_hash or ""), str(settlement_date or "")),
            ).fetchone()
        return self._decode(row)

    def latest(self, candidate_hash: str) -> dict[str, Any] | None:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM portfolio_forward_performance_settlements "
                "WHERE candidate_hash = ? ORDER BY settlement_date DESC LIMIT 1",
                (str(candidate_hash or ""),),
            ).fetchone()
        return self._decode(row)

    def settlements(self, candidate_hash: str) -> list[dict[str, Any]]:
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT payload_json FROM portfolio_forward_performance_settlements "
                "WHERE candidate_hash = ? ORDER BY settlement_date",
                (str(candidate_hash or ""),),
            ).fetchall()
        return [json.loads(str(row["payload_json"])) for row in rows]

    def settlement_dates(self, candidate_hash: str) -> list[str]:
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT settlement_date FROM portfolio_forward_performance_settlements "
                "WHERE candidate_hash = ? ORDER BY settlement_date",
                (str(candidate_hash or ""),),
            ).fetchall()
        return [str(row["settlement_date"] or "") for row in rows]

    def record(self, settlement: dict[str, Any]) -> dict[str, Any]:
        candidate_hash = str(settlement.get("candidate_hash") or "")
        settlement_date = str(settlement.get("settlement_date") or "")
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT settlement_hash, payload_json FROM portfolio_forward_performance_settlements "
                "WHERE candidate_hash = ? AND settlement_date = ?",
                (candidate_hash, settlement_date),
            ).fetchone()
            if existing:
                existing_payload = json.loads(str(existing["payload_json"]))
                if str(existing["settlement_hash"] or "") == str(settlement.get("settlement_hash") or ""):
                    return {"ok": True, "status": "IDEMPOTENT_REPLAY", "settlement": existing_payload}
                return {
                    "ok": False,
                    "status": "CONFLICT",
                    "reason": "same_candidate_and_date_has_different_settlement_hash",
                    "existing_hash": str(existing["settlement_hash"] or ""),
                    "incoming_hash": str(settlement.get("settlement_hash") or ""),
                }
            latest_row = connection.execute(
                "SELECT payload_json FROM portfolio_forward_performance_settlements "
                "WHERE candidate_hash = ? ORDER BY settlement_date DESC LIMIT 1",
                (candidate_hash,),
            ).fetchone()
            previous = self._decode(latest_row)
            chain_rows = connection.execute(
                "SELECT payload_json FROM portfolio_forward_performance_settlements "
                "WHERE candidate_hash = ? ORDER BY settlement_date",
                (candidate_hash,),
            ).fetchall()
            chain_previous: dict[str, Any] | None = None
            chain_blockers: list[str] = []
            for row in chain_rows:
                chain_payload = json.loads(str(row["payload_json"]))
                chain_verification = verify_forward_performance_settlement(chain_payload, chain_previous)
                if chain_verification.get("status") != "PASS":
                    chain_blockers.extend(chain_verification.get("blockers") or [])
                chain_previous = chain_payload
            if chain_blockers:
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "reason": "existing_forward_performance_chain_invalid",
                    "blockers": list(dict.fromkeys(chain_blockers)),
                }
            verification = verify_forward_performance_settlement(settlement, previous)
            if verification.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "reason": "forward_performance_settlement_invalid",
                    "verification": verification,
                }
            current_evidence = dict(dict(settlement.get("observation_evidence") or {}).get("current") or {})
            source = dict(dict(settlement.get("observation_evidence") or {}).get("source") or {})
            binding = dict(dict(settlement.get("market_snapshot") or {}).get("dataset_binding") or {})
            payload_json = json.dumps(
                settlement,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            connection.execute(
                """
                INSERT INTO portfolio_forward_performance_settlements(
                    candidate_hash, settlement_date, settlement_hash,
                    previous_settlement_hash, current_observation_hash,
                    source_decision_hash, dataset_hash, recorded_at, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_hash,
                    settlement_date,
                    str(settlement.get("settlement_hash") or ""),
                    str(settlement.get("previous_settlement_hash") or ""),
                    str(current_evidence.get("observation_hash") or ""),
                    str(source.get("decision_hash") or ""),
                    str(binding.get("data_hash") or ""),
                    int(settlement.get("recorded_at") or 0),
                    payload_json,
                ),
            )
        return {"ok": True, "status": "RECORDED", "settlement": settlement}

    def audit(
        self,
        candidate_hash: str,
        *,
        observations: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        clean_hash = str(candidate_hash or "")
        integrity_violations: list[str] = []
        settlements: list[dict[str, Any]] = []
        with self._lock, closing(self._connect()) as connection:
            database_rows = connection.execute(
                "SELECT * FROM portfolio_forward_performance_settlements "
                "WHERE candidate_hash = ? ORDER BY settlement_date",
                (clean_hash,),
            ).fetchall()
        for row in database_rows:
            row_date = str(row["settlement_date"] or "")
            try:
                settlement = json.loads(str(row["payload_json"]))
            except json.JSONDecodeError:
                integrity_violations.append(f"{row_date}:settlement_json_invalid")
                continue
            settlements.append(settlement)
            current_evidence = dict(dict(settlement.get("observation_evidence") or {}).get("current") or {})
            source_evidence = dict(dict(settlement.get("observation_evidence") or {}).get("source") or {})
            binding = dict(dict(settlement.get("market_snapshot") or {}).get("dataset_binding") or {})
            metadata_checks = {
                "candidate_hash": str(settlement.get("candidate_hash") or "") == str(row["candidate_hash"] or ""),
                "settlement_date": str(settlement.get("settlement_date") or "") == row_date,
                "settlement_hash": str(settlement.get("settlement_hash") or "") == str(row["settlement_hash"] or ""),
                "previous_settlement_hash": str(settlement.get("previous_settlement_hash") or "")
                == str(row["previous_settlement_hash"] or ""),
                "current_observation_hash": str(current_evidence.get("observation_hash") or "")
                == str(row["current_observation_hash"] or ""),
                "source_decision_hash": str(source_evidence.get("decision_hash") or "")
                == str(row["source_decision_hash"] or ""),
                "dataset_hash": str(binding.get("data_hash") or "") == str(row["dataset_hash"] or ""),
                "recorded_at": int(settlement.get("recorded_at") or 0) == int(row["recorded_at"] or 0),
            }
            integrity_violations.extend(
                f"{row_date}:database_{name}_mismatch"
                for name, passed in metadata_checks.items()
                if not passed
            )
        previous: dict[str, Any] | None = None
        for settlement in settlements:
            verification = verify_forward_performance_settlement(settlement, previous)
            if verification.get("status") != "PASS":
                date = str(settlement.get("settlement_date") or "")
                integrity_violations.extend(
                    f"{date}:{blocker}" for blocker in verification.get("blockers") or []
                )
            previous = settlement

        expected = {str(key): dict(value) for key, value in dict(observations or {}).items()}
        settlement_dates = [str(item.get("settlement_date") or "") for item in settlements]
        unexpected_dates: list[str] = []
        observation_hash_mismatches: list[str] = []
        if observations is not None:
            for date, observation in expected.items():
                observation_verification = verify_shadow_observation(
                    observation,
                    candidate_hash=clean_hash,
                    signal_date=date,
                )
                if observation_verification.get("status") != "PASS":
                    integrity_violations.extend(
                        f"{date}:source_observation_{blocker}"
                        for blocker in observation_verification.get("blockers") or []
                    )
            for settlement in settlements:
                date = str(settlement.get("settlement_date") or "")
                observation = expected.get(date)
                if not observation:
                    unexpected_dates.append(date)
                    continue
                evidence = dict(dict(settlement.get("observation_evidence") or {}).get("current") or {})
                evidence_matches = (
                    str(evidence.get("observation_hash") or "") == str(observation.get("observation_hash") or "")
                    and str(evidence.get("decision_hash") or "") == str(observation.get("decision_hash") or "")
                    and str(evidence.get("dataset_hash") or "") == str(observation.get("dataset_hash") or "")
                    and str(evidence.get("capture_contract_hash") or "")
                    == str(observation.get("capture_contract_hash") or "")
                    and str(evidence.get("risk_snapshot_hash") or "")
                    == str(observation.get("risk_snapshot_hash") or "")
                    and str(evidence.get("forward_state_contract_hash") or "")
                    == str(observation.get("forward_state_contract_hash") or "")
                )
                if not evidence_matches:
                    observation_hash_mismatches.append(date)
            integrity_violations.extend(f"{date}:settlement_without_observation" for date in unexpected_dates)
            integrity_violations.extend(f"{date}:observation_hash_mismatch" for date in observation_hash_mismatches)
        unsettled_dates = sorted(set(expected) - set(settlement_dates)) if observations is not None else []
        authority_violations = sum(
            int(
                item.get("observation_only") is not True
                or item.get("simulation_only") is not True
                or item.get("paper_authorized") is not False
                or item.get("live_order_allowed") is not False
            )
            for item in settlements
        )
        if authority_violations:
            integrity_violations.append("settlement_execution_authority_violation")
        return {
            "schema_version": PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION,
            "status": "PASS" if not integrity_violations else "BLOCK",
            "candidate_hash": clean_hash,
            "settlement_count": len(settlements),
            "outcome_period_count": max(len(settlements) - 1, 0),
            "first_settlement_date": settlement_dates[0] if settlement_dates else "",
            "last_settlement_date": settlement_dates[-1] if settlement_dates else "",
            "unsettled_observation_dates": unsettled_dates,
            "unexpected_settlement_dates": unexpected_dates,
            "observation_hash_mismatch_dates": observation_hash_mismatches,
            "execution_authority_violation_count": authority_violations,
            "integrity_violations": list(dict.fromkeys(integrity_violations)),
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def summary(
        self,
        candidate_hash: str,
        *,
        observations: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        settlements = self.settlements(candidate_hash)
        audit = self.audit(candidate_hash, observations=observations)
        if not settlements:
            return {
                **audit,
                "strategy": {},
                "benchmark": {},
                "cumulative_excess_return_pct": 0.0,
                "order_count": 0,
                "rebalance_execution_count": 0,
            }
        latest = settlements[-1]
        outcome_rows = settlements[1:]
        strategy_returns = [_number(dict(item.get("strategy") or {}).get("daily_return_pct")) / 100.0 for item in outcome_rows]
        benchmark_returns = [_number(dict(item.get("benchmark") or {}).get("daily_return_pct")) / 100.0 for item in outcome_rows]
        active_returns = [left - right for left, right in zip(strategy_returns, benchmark_returns)]

        def annualized_return(account: dict[str, Any]) -> float:
            count = len(outcome_rows)
            cumulative = _number(account.get("cumulative_return_pct")) / 100.0
            if count <= 0 or cumulative <= -1.0:
                return 0.0
            return ((1.0 + cumulative) ** (252.0 / count) - 1.0) * 100.0

        def annualized_ratio(returns: list[float]) -> float:
            if len(returns) < 2:
                return 0.0
            mean = sum(returns) / len(returns)
            variance = sum((item - mean) ** 2 for item in returns) / len(returns)
            deviation = math.sqrt(max(variance, 0.0))
            return mean / deviation * math.sqrt(252.0) if deviation > 0 else 0.0

        strategy = dict(latest.get("strategy") or {})
        benchmark = dict(latest.get("benchmark") or {})
        return {
            **audit,
            "strategy": {
                "equity": strategy.get("equity"),
                "cumulative_return_pct": strategy.get("cumulative_return_pct"),
                "annualized_return_pct": _rounded(annualized_return(strategy), 8),
                "max_drawdown_pct": dict(strategy.get("state") or {}).get("max_drawdown_pct"),
                "sharpe": _rounded(annualized_ratio(strategy_returns), 8),
                "gross_exposure_pct": strategy.get("gross_exposure_pct"),
                "total_fees": dict(strategy.get("state") or {}).get("total_fees"),
                "turnover": dict(strategy.get("state") or {}).get("turnover"),
            },
            "benchmark": {
                "equity": benchmark.get("equity"),
                "cumulative_return_pct": benchmark.get("cumulative_return_pct"),
                "annualized_return_pct": _rounded(annualized_return(benchmark), 8),
                "max_drawdown_pct": dict(benchmark.get("state") or {}).get("max_drawdown_pct"),
                "sharpe": _rounded(annualized_ratio(benchmark_returns), 8),
                "gross_exposure_pct": benchmark.get("gross_exposure_pct"),
                "total_fees": dict(benchmark.get("state") or {}).get("total_fees"),
                "turnover": dict(benchmark.get("state") or {}).get("turnover"),
            },
            "information_ratio": _rounded(annualized_ratio(active_returns), 8),
            "cumulative_excess_return_pct": latest.get("cumulative_excess_return_pct"),
            "order_count": sum(len(dict(item.get("strategy") or {}).get("orders") or []) for item in settlements),
            "rebalance_execution_count": sum(
                int(
                    dict(item.get("decision_execution") or {}).get("execute")
                    and str(dict(item.get("decision_execution") or {}).get("reason") or "")
                    == "relative_strength_rebalance"
                    and str(dict(item.get("decision_execution") or {}).get("status") or "")
                    in {"EXECUTED", "EXECUTED_NO_FILL"}
                )
                for item in settlements
            ),
            "latest_settlement_hash": str(latest.get("settlement_hash") or ""),
        }


def _build_legacy_forward_performance_readiness(
    *,
    candidate: dict[str, Any],
    shadow_audit: dict[str, Any],
    performance_summary: dict[str, Any],
    historical_statistical_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = dict(candidate.get("spec") or {})
    threshold_contract = forward_evidence_thresholds_from_spec(spec)
    required_outcomes = int(threshold_contract["minimum_forward_performance_outcomes"])
    required_rebalances = int(threshold_contract["minimum_planned_rebalances"])
    drawdown_limit = _number(
        dict(spec.get("acceptance_contract") or {}).get("validation_and_test_max_drawdown_below_pct"),
        15.0,
    )
    outcome_value = _nonnegative_integer(performance_summary.get("outcome_period_count"))
    rebalance_value = _nonnegative_integer(performance_summary.get("rebalance_execution_count"))
    authority_violation_value = _nonnegative_integer(
        performance_summary.get("execution_authority_violation_count")
    )
    settlement_value = _nonnegative_integer(performance_summary.get("settlement_count"))
    captured_value = _nonnegative_integer(shadow_audit.get("valid_observation_count"))
    progress_types_valid = all(
        value is not None
        for value in (
            outcome_value,
            rebalance_value,
            authority_violation_value,
            settlement_value,
            captured_value,
        )
    )
    outcome_count = outcome_value or 0
    rebalance_count = rebalance_value or 0
    strategy = dict(performance_summary.get("strategy") or {})
    statistical = dict(historical_statistical_audit or {})
    integrity_checks = {
        "candidate_forward_threshold_contract_pass": threshold_contract["status"] == "PASS",
        "shadow_ledger_integrity_pass": shadow_audit.get("status") == "PASS",
        "performance_ledger_integrity_pass": performance_summary.get("status") == "PASS",
        "forward_progress_types_valid": progress_types_valid,
        "all_captured_observations_settled": not list(performance_summary.get("unsettled_observation_dates") or []),
        "zero_execution_authority": (
            authority_violation_value == 0
            and candidate.get("research_only") is True
            and candidate.get("paper_authorized") is False
            and candidate.get("live_order_allowed") is False
        ),
        "historical_statistical_audit_integrity_pass": (
            statistical.get("verification_status") == "PASS"
        ),
    }
    evidence_checks = {
        "minimum_forward_outcomes": outcome_count >= required_outcomes,
        "minimum_forward_rebalances": rebalance_count >= required_rebalances,
        "forward_excess_return_positive": _number(performance_summary.get("cumulative_excess_return_pct")) > 0,
        "forward_drawdown_below_limit": bool(strategy) and _number(strategy.get("max_drawdown_pct"), 100.0) < drawdown_limit,
        "historical_statistical_audit_pass": statistical.get("status") == "PASS",
    }
    integrity_blockers = [name for name, passed in integrity_checks.items() if not passed]
    evidence_blockers = [name for name, passed in evidence_checks.items() if not passed]
    if integrity_blockers:
        status = "BLOCK"
    elif outcome_count < required_outcomes or rebalance_count < required_rebalances:
        status = "COLLECTING"
    elif evidence_blockers:
        status = "RESEARCH_REVIEW_BLOCKED"
    else:
        status = "RESEARCH_REVIEW_READY"
    return {
        "schema_version": PORTFOLIO_FORWARD_PERFORMANCE_SCHEMA_VERSION,
        "status": status,
        "promotion_status": "BLOCK" if integrity_blockers or evidence_blockers else "REVIEW_REQUIRED",
        "blockers": list(dict.fromkeys([*integrity_blockers, *evidence_blockers])),
        "integrity_checks": integrity_checks,
        "evidence_checks": evidence_checks,
        "progress": {
            "forward_outcomes": outcome_count,
            "required_forward_outcomes": required_outcomes,
            "remaining_forward_outcomes": max(required_outcomes - outcome_count, 0),
            "settlements": settlement_value or 0,
            "captured_observations": captured_value or 0,
            "executed_rebalances": rebalance_count,
            "required_executed_rebalances": required_rebalances,
            "remaining_executed_rebalances": max(required_rebalances - rebalance_count, 0),
        },
        "historical_statistical_audit": {
            "status": str(statistical.get("status") or "MISSING"),
            "conclusion": str(statistical.get("conclusion") or ""),
            "audit_hash": str(statistical.get("audit_hash") or ""),
            "artifact_hash": str(statistical.get("artifact_hash") or ""),
            "verification_status": str(statistical.get("verification_status") or "BLOCK"),
            "verification_blockers": list(statistical.get("verification_blockers") or []),
        },
        "forward_threshold_contract": threshold_contract,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_forward_performance_readiness(
    *,
    candidate: dict[str, Any],
    shadow_audit: dict[str, Any],
    performance_summary: dict[str, Any],
    historical_statistical_audit: dict[str, Any] | None = None,
    forward_statistical_audit: dict[str, Any] | None = None,
    readiness_schema_version: str = LEGACY_PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Build versioned research readiness without granting execution authority.

    The legacy schema preserves the pre-forward-statistical-audit contract.
    v2 preserves the historical full-series audit contract; v3 is the current
    first-joint-maturity single-look contract.
    """
    legacy = _build_legacy_forward_performance_readiness(
        candidate=candidate,
        shadow_audit=shadow_audit,
        performance_summary=performance_summary,
        historical_statistical_audit=historical_statistical_audit,
    )
    if readiness_schema_version == LEGACY_PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION:
        return legacy
    if readiness_schema_version == PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION:
        try:
            return _build_forward_performance_readiness_v3(
                legacy=legacy,
                candidate=candidate,
                shadow_audit=shadow_audit,
                performance_summary=performance_summary,
                historical_statistical_audit=historical_statistical_audit,
                forward_statistical_audit=forward_statistical_audit,
            )
        except RecursionError:
            return {
                **legacy,
                "schema_version": PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
                "status": "BLOCK",
                "promotion_status": "BLOCK",
                "blockers": list(dict.fromkeys([
                    *list(legacy.get("blockers") or []),
                    "forward_readiness_v3_recursion_invalid",
                ])),
                "decision_policy": EXPECTED_FORWARD_DECISION_POLICY,
                "decision_status": "BLOCK",
                "research_action": "BLOCK",
                "research_only": True,
                "observation_only": True,
                "simulation_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
    if readiness_schema_version != PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION:
        return {
            **legacy,
            "schema_version": str(readiness_schema_version or ""),
            "status": "BLOCK",
            "promotion_status": "BLOCK",
            "blockers": list(dict.fromkeys([
                *list(legacy.get("blockers") or []),
                "forward_readiness_schema_unsupported",
            ])),
            "research_only": True,
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    progress = dict(legacy.get("progress") or {})
    outcome_count = int(progress.get("forward_outcomes") or 0)
    required_outcomes = int(progress.get("required_forward_outcomes") or 0)
    rebalance_count = int(progress.get("executed_rebalances") or 0)
    required_rebalances = int(progress.get("required_executed_rebalances") or 0)
    due = outcome_count >= required_outcomes and rebalance_count >= required_rebalances
    forward_audit = dict(forward_statistical_audit or {})
    audit_present = bool(forward_audit)
    audit_binding = dict(forward_audit.get("input_binding") or {})
    audit_maturity = dict(forward_audit.get("maturity") or {})
    expected_maturity_status = "DUE" if due else "NOT_DUE"
    expected_spec_hash = _canonical_hash(dict(candidate.get("spec") or {}))
    audit_outcomes = _nonnegative_integer(audit_binding.get("outcome_period_count"))
    audit_rebalances = _nonnegative_integer(audit_binding.get("rebalance_execution_count"))
    audit_settlements = _nonnegative_integer(audit_binding.get("settlement_count"))
    maturity_outcomes = _nonnegative_integer(audit_maturity.get("forward_outcomes"))
    maturity_required_outcomes = _nonnegative_integer(audit_maturity.get("required_forward_outcomes"))
    maturity_rebalances = _nonnegative_integer(audit_maturity.get("executed_rebalances"))
    maturity_required_rebalances = _nonnegative_integer(
        audit_maturity.get("required_executed_rebalances")
    )

    audit_binding_matches = bool(audit_present) and (
        str(audit_binding.get("candidate_hash") or "") == str(candidate.get("candidate_hash") or "")
        and str(audit_binding.get("candidate_spec_hash") or "") == expected_spec_hash
        and audit_outcomes == outcome_count
        and audit_rebalances == rebalance_count
        and audit_settlements == _nonnegative_integer(performance_summary.get("settlement_count"))
        and str(audit_binding.get("latest_settlement_hash") or "")
        == str(performance_summary.get("latest_settlement_hash") or "")
        and str(audit_binding.get("historical_statistical_audit_hash") or "")
        == str(dict(historical_statistical_audit or {}).get("audit_hash") or "")
    )
    audit_maturity_matches = bool(audit_present) and (
        str(audit_maturity.get("status") or "") == expected_maturity_status
        and maturity_outcomes == outcome_count
        and maturity_required_outcomes == required_outcomes
        and maturity_rebalances == rebalance_count
        and maturity_required_rebalances == required_rebalances
    )
    audit_integrity_pass = (
        not audit_present
    ) or (
        audit_present
        and forward_audit.get("schema_version") == EXPECTED_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION
        and bool(str(forward_audit.get("audit_hash") or ""))
        and forward_audit.get("verification_status") == "PASS"
        and audit_binding_matches
        and audit_maturity_matches
        and dict(forward_audit.get("contract_comparison") or {}).get("status") == "PASS"
        and forward_audit.get("research_only") is True
        and forward_audit.get("observation_only") is True
        and forward_audit.get("simulation_only") is True
        and forward_audit.get("profitability_proven") is False
        and forward_audit.get("paper_authorized") is False
        and forward_audit.get("live_order_allowed") is False
    )

    integrity_checks = dict(legacy.get("integrity_checks") or {})
    integrity_checks.update({
        "forward_statistical_audit_integrity_pass": audit_integrity_pass,
        "forward_statistical_audit_binding_pass": (audit_binding_matches if audit_present else True),
        "forward_statistical_audit_maturity_pass": (audit_maturity_matches if audit_present else True),
        "forward_statistical_audit_zero_execution_authority": (
            not audit_present
            or (
                forward_audit.get("research_only") is True
                and forward_audit.get("observation_only") is True
                and forward_audit.get("simulation_only") is True
                and forward_audit.get("profitability_proven") is False
                and forward_audit.get("paper_authorized") is False
                and forward_audit.get("live_order_allowed") is False
            )
        ),
    })
    evidence_checks = {
        name: passed
        for name, passed in dict(legacy.get("evidence_checks") or {}).items()
        if name != "historical_statistical_audit_pass"
    }
    evidence_checks.update({
        "forward_statistical_audit_due": due,
        "forward_statistical_audit_present": audit_present if due else True,
        "forward_statistical_audit_pass": forward_audit.get("status") == "PASS" if due else True,
        "forward_statistical_evidence_is_not_profit_or_authorization": (
            not audit_present
            or (
                forward_audit.get("profitability_proven") is False
                and forward_audit.get("paper_authorized") is False
                and forward_audit.get("live_order_allowed") is False
            )
        ),
    })
    integrity_blockers = [name for name, passed in integrity_checks.items() if not passed]
    evidence_blockers = [name for name, passed in evidence_checks.items() if not passed]
    if integrity_blockers:
        status = "BLOCK"
    elif not due:
        status = "COLLECTING"
    elif evidence_blockers:
        status = "RESEARCH_REVIEW_BLOCKED"
    else:
        status = "RESEARCH_REVIEW_READY"

    return {
        **legacy,
        "schema_version": PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
        "status": status,
        "promotion_status": "REVIEW_REQUIRED" if status == "RESEARCH_REVIEW_READY" else "BLOCK",
        "blockers": list(dict.fromkeys([*integrity_blockers, *evidence_blockers])),
        "integrity_checks": integrity_checks,
        "evidence_checks": evidence_checks,
        "forward_statistical_audit_due_status": expected_maturity_status,
        "historical_statistical_claim_status": str(
            dict(historical_statistical_audit or {}).get("status") or "MISSING"
        ),
        "forward_statistical_audit": {
            "schema_version": str(forward_audit.get("schema_version") or ""),
            "status": str(forward_audit.get("status") or "MISSING"),
            "conclusion": str(forward_audit.get("conclusion") or ""),
            "audit_hash": str(forward_audit.get("audit_hash") or ""),
            "verification_status": str(forward_audit.get("verification_status") or "NOT_RUN"),
            "verification_blockers": list(forward_audit.get("verification_blockers") or []),
            "maturity": audit_maturity,
            "input_binding": audit_binding,
            "contract_comparison": dict(forward_audit.get("contract_comparison") or {}),
            "evidence_scope": str(forward_audit.get("evidence_scope") or ""),
            "profitability_proven": False,
            "research_only": True,
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _build_forward_performance_readiness_v3(
    *,
    legacy: dict[str, Any],
    candidate: dict[str, Any],
    shadow_audit: dict[str, Any],
    performance_summary: dict[str, Any],
    historical_statistical_audit: dict[str, Any] | None,
    forward_statistical_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    """Consume the explicit audit-v2 frozen single-look decision."""

    named_inputs = {
        "legacy": legacy,
        "candidate": candidate,
        "shadow_audit": shadow_audit,
        "performance_summary": performance_summary,
        "historical_statistical_audit": historical_statistical_audit,
        "forward_statistical_audit": forward_statistical_audit,
    }
    cyclic_inputs = [
        name for name, value in named_inputs.items() if _v3_container_cycle_detected(value)
    ]

    def acyclic_mapping(name: str, value: Any) -> dict[str, Any]:
        if name in cyclic_inputs or not isinstance(value, dict):
            return {}
        return dict(value)

    legacy_source = acyclic_mapping("legacy", legacy)
    candidate_source = acyclic_mapping("candidate", candidate)
    shadow_source = acyclic_mapping("shadow_audit", shadow_audit)
    performance_source = acyclic_mapping("performance_summary", performance_summary)
    historical_source = acyclic_mapping(
        "historical_statistical_audit",
        historical_statistical_audit,
    )
    forward_audit = acyclic_mapping("forward_statistical_audit", forward_statistical_audit)
    spec = dict(candidate_source.get("spec") or {}) if isinstance(candidate_source.get("spec"), dict) else {}
    threshold_contract = forward_evidence_thresholds_v3_from_spec(spec)

    outcome_value = _v3_safe_integer(performance_source.get("outcome_period_count"))
    rebalance_value = _v3_safe_integer(performance_source.get("rebalance_execution_count"))
    settlement_value = _v3_safe_integer(performance_source.get("settlement_count"))
    authority_violation_value = _v3_safe_integer(
        performance_source.get("execution_authority_violation_count")
    )
    captured_value = _v3_safe_integer(shadow_source.get("valid_observation_count"))
    progress_values_valid = all(
        value is not None
        for value in (
            outcome_value,
            rebalance_value,
            settlement_value,
            authority_violation_value,
            captured_value,
        )
    )
    outcome_count = outcome_value or 0
    required_outcomes = int(threshold_contract["minimum_forward_performance_outcomes"])
    rebalance_count = rebalance_value or 0
    required_rebalances = int(threshold_contract["minimum_planned_rebalances"])
    due = (
        progress_values_valid
        and threshold_contract.get("status") == "PASS"
        and outcome_count >= required_outcomes
        and rebalance_count >= required_rebalances
    )
    expected_maturity_status = "DUE" if due else "NOT_DUE"
    expected_spec_hash = _canonical_hash(spec)
    expected_threshold_hash = _canonical_hash(threshold_contract)

    audit_binding = dict(forward_audit.get("input_binding") or {}) if isinstance(forward_audit.get("input_binding"), dict) else {}
    audit_maturity = dict(forward_audit.get("maturity") or {}) if isinstance(forward_audit.get("maturity"), dict) else {}
    audit_checks = dict(forward_audit.get("checks") or {}) if isinstance(forward_audit.get("checks"), dict) else {}
    decision_window = dict(forward_audit.get("decision_window") or {}) if isinstance(forward_audit.get("decision_window"), dict) else {}
    prefix = dict(decision_window.get("first_joint_maturity_prefix") or {}) if isinstance(decision_window.get("first_joint_maturity_prefix"), dict) else {}
    stage = dict(forward_audit.get("stage") or {}) if isinstance(forward_audit.get("stage"), dict) else {}
    statistical_contract = dict(forward_audit.get("statistical_contract") or {}) if isinstance(forward_audit.get("statistical_contract"), dict) else {}
    risk_acceptance = (
        dict(decision_window.get("risk_acceptance") or {})
        if isinstance(decision_window.get("risk_acceptance"), dict)
        else {}
    )

    audit_outcomes = _v3_safe_integer(audit_binding.get("outcome_period_count"))
    audit_rebalances = _v3_safe_integer(audit_binding.get("rebalance_execution_count"))
    audit_settlements = _v3_safe_integer(audit_binding.get("settlement_count"))
    maturity_outcomes = _v3_safe_integer(audit_maturity.get("forward_outcomes"))
    maturity_required_outcomes = _v3_safe_integer(audit_maturity.get("required_forward_outcomes"))
    maturity_rebalances = _v3_safe_integer(audit_maturity.get("executed_rebalances"))
    maturity_required_rebalances = _v3_safe_integer(
        audit_maturity.get("required_executed_rebalances")
    )
    first_due_index = _v3_safe_integer(prefix.get("first_due_settlement_index"))
    prefix_settlements = _v3_safe_integer(prefix.get("settlement_count"))
    prefix_outcomes = _v3_safe_integer(prefix.get("outcome_period_count"))
    prefix_rebalances = _v3_safe_integer(prefix.get("rebalance_execution_count"))

    decision_hash = str(decision_window.get("decision_hash") or "")
    decision_content = dict(decision_window)
    decision_content.pop("decision_hash", None)
    decision_hash_valid = bool(decision_hash) and decision_hash == _canonical_hash(decision_content)
    risk_hash = str(risk_acceptance.get("risk_hash") or "")
    risk_content = dict(risk_acceptance)
    risk_content.pop("risk_hash", None)
    risk_hash_valid = bool(risk_hash) and risk_hash == _canonical_hash(risk_content)
    acceptance = spec.get("acceptance_contract")
    acceptance_contract = dict(acceptance) if isinstance(acceptance, dict) else {}
    expected_risk_limit = _v3_finite_native_number(
        acceptance_contract.get("validation_and_test_max_drawdown_below_pct")
    )
    if expected_risk_limit is not None and expected_risk_limit <= 0.0:
        expected_risk_limit = None
    supplied_risk_limit = _v3_finite_native_number(
        risk_acceptance.get("required_max_drawdown_below_pct")
    )
    supplied_risk_drawdown = _v3_finite_native_number(
        risk_acceptance.get("prefix_max_drawdown_pct")
    )
    risk_prefix_settlements = _v3_safe_integer(
        risk_acceptance.get("prefix_settlement_count")
    )
    risk_prefix_outcomes = _v3_safe_integer(
        risk_acceptance.get("prefix_outcome_period_count")
    )
    audit_binding_matches = bool(forward_audit) and (
        str(audit_binding.get("candidate_hash") or "")
        == str(candidate_source.get("candidate_hash") or "")
        and str(audit_binding.get("candidate_spec_hash") or "") == expected_spec_hash
        and audit_outcomes == outcome_count
        and audit_rebalances == rebalance_count
        and audit_settlements == settlement_value
        and str(audit_binding.get("latest_settlement_hash") or "")
        == str(performance_source.get("latest_settlement_hash") or "")
        and str(audit_binding.get("historical_statistical_audit_hash") or "")
        == str(historical_source.get("audit_hash") or "")
        and str(audit_binding.get("decision_policy") or "") == EXPECTED_FORWARD_DECISION_POLICY
        and str(audit_binding.get("decision_hash") or "") == decision_hash
        and str(audit_binding.get("decision_series_hash") or "")
        == str(decision_window.get("decision_series_hash") or "")
        and str(audit_binding.get("risk_acceptance_hash") or "") == risk_hash
    )
    audit_maturity_matches = bool(forward_audit) and (
        str(audit_maturity.get("status") or "") == expected_maturity_status
        and maturity_outcomes == outcome_count
        and maturity_required_outcomes == required_outcomes
        and maturity_rebalances == rebalance_count
        and maturity_required_rebalances == required_rebalances
        and audit_maturity.get("both_thresholds_required") is True
        and str(audit_maturity.get("decision_policy") or "") == EXPECTED_FORWARD_DECISION_POLICY
        and str(audit_maturity.get("first_joint_maturity_status") or "")
        == ("DUE" if due else "NOT_DUE")
    )

    if due:
        prefix_matches = (
            prefix.get("status") == "DUE"
            and prefix.get("policy") == EXPECTED_FORWARD_DECISION_POLICY
            and prefix.get("required_forward_outcomes") == required_outcomes
            and prefix.get("required_executed_rebalances") == required_rebalances
            and first_due_index is not None
            and prefix_settlements == first_due_index + 1
            and prefix_outcomes == first_due_index
            and prefix_outcomes is not None
            and prefix_outcomes >= required_outcomes
            and prefix_rebalances is not None
            and prefix_rebalances >= required_rebalances
            and bool(str(prefix.get("first_due_settlement_date") or ""))
            and bool(str(prefix.get("first_due_settlement_hash") or ""))
            and not list(prefix.get("blockers") or [])
            and audit_binding.get("first_due_settlement_index") == first_due_index
            and str(audit_binding.get("first_due_settlement_date") or "")
            == str(prefix.get("first_due_settlement_date") or "")
            and str(audit_binding.get("first_due_settlement_hash") or "")
            == str(prefix.get("first_due_settlement_hash") or "")
            and audit_maturity.get("first_due_settlement_index") == first_due_index
            and str(audit_maturity.get("first_due_settlement_date") or "")
            == str(prefix.get("first_due_settlement_date") or "")
            and str(audit_maturity.get("first_due_settlement_hash") or "")
            == str(prefix.get("first_due_settlement_hash") or "")
        )
    else:
        prefix_matches = (
            prefix.get("status") == "NOT_DUE"
            and prefix.get("policy") == EXPECTED_FORWARD_DECISION_POLICY
            and prefix.get("required_forward_outcomes") == required_outcomes
            and prefix.get("required_executed_rebalances") == required_rebalances
            and prefix.get("first_due_settlement_index") is None
            and prefix_settlements == 0
            and prefix_outcomes == 0
            and prefix_rebalances == 0
            and not list(prefix.get("blockers") or [])
        )

    risk_checks = (
        dict(risk_acceptance.get("checks") or {})
        if isinstance(risk_acceptance.get("checks"), dict)
        else {}
    )
    risk_binding_matches = (
        risk_acceptance.get("schema_version")
        == EXPECTED_FORWARD_RISK_ACCEPTANCE_SCHEMA_VERSION
        and risk_acceptance.get("method")
        == "PREFIX_STRATEGY_EQUITY_PEAK_TO_TROUGH_MAX_DRAWDOWN"
        and risk_acceptance.get("comparison") == "STRICTLY_BELOW"
        and risk_acceptance.get("threshold_field")
        == "validation_and_test_max_drawdown_below_pct"
        and expected_risk_limit is not None
        and supplied_risk_limit == expected_risk_limit
        and str(risk_acceptance.get("decision_series_hash") or "")
        == str(decision_window.get("decision_series_hash") or "")
        and str(decision_window.get("risk_acceptance_hash") or "") == risk_hash
        and str(audit_binding.get("risk_acceptance_hash") or "") == risk_hash
        and risk_hash_valid
    )
    if due:
        risk_binding_matches = risk_binding_matches and (
            risk_prefix_settlements == prefix_settlements
            and risk_prefix_outcomes == prefix_outcomes
            and str(risk_acceptance.get("prefix_first_due_settlement_hash") or "")
            == str(prefix.get("first_due_settlement_hash") or "")
        )
        risk_numeric_pass = (
            supplied_risk_drawdown is not None
            and supplied_risk_drawdown >= 0.0
            and supplied_risk_limit is not None
            and supplied_risk_drawdown < supplied_risk_limit
        )
        if risk_acceptance.get("status") == "PASS":
            risk_semantics_match = (
                risk_numeric_pass
                and not list(risk_acceptance.get("blockers") or [])
                and risk_checks.get("frozen_drawdown_limit_valid") is True
                and risk_checks.get("prefix_strategy_equity_valid") is True
                and risk_checks.get("prefix_max_drawdown_strictly_below_limit") is True
            )
        else:
            risk_semantics_match = (
                risk_acceptance.get("status") == "BLOCK"
                and supplied_risk_drawdown is not None
                and supplied_risk_limit is not None
                and not risk_numeric_pass
                and list(risk_acceptance.get("blockers") or [])
                == ["risk_acceptance_max_drawdown_not_below_limit"]
                and risk_checks.get("frozen_drawdown_limit_valid") is True
                and risk_checks.get("prefix_strategy_equity_valid") is True
                and risk_checks.get("prefix_max_drawdown_strictly_below_limit") is False
            )
    else:
        risk_binding_matches = risk_binding_matches and (
            risk_prefix_settlements == 0
            and risk_prefix_outcomes == 0
            and str(risk_acceptance.get("prefix_first_due_settlement_hash") or "") == ""
        )
        risk_semantics_match = (
            risk_acceptance.get("status") == "NOT_DUE"
            and supplied_risk_drawdown is None
            and not list(risk_acceptance.get("blockers") or [])
            and risk_checks.get("frozen_drawdown_limit_valid") is True
            and risk_checks.get("prefix_strategy_equity_valid") is False
            and risk_checks.get("prefix_max_drawdown_strictly_below_limit") is False
        )

    decision_status = str(decision_window.get("decision_status") or "")
    research_action = str(decision_window.get("research_action") or "")
    expected_audit_statuses: set[str]
    if not due:
        decision_semantics_match = (
            decision_window.get("status") == "NOT_DUE"
            and decision_status == "NOT_DUE"
            and research_action == "COLLECT_MORE"
            and not stage
            and risk_semantics_match
        )
        expected_audit_statuses = {"NOT_DUE"}
    elif decision_status == "PASS":
        decision_semantics_match = (
            decision_window.get("status") == "FROZEN"
            and research_action == "REVIEW_REQUIRED"
            and stage.get("status") == "PASS"
            and risk_acceptance.get("status") == "PASS"
            and risk_semantics_match
            and not list(decision_window.get("blockers") or [])
        )
        expected_audit_statuses = {"PASS"}
    else:
        decision_semantics_match = (
            decision_window.get("status") == "FROZEN"
            and decision_status == "BLOCK"
            and research_action == "STOP_RESEARCH"
            and (
                stage.get("status") == "BLOCK"
                or risk_acceptance.get("status") == "BLOCK"
            )
            and risk_semantics_match
            and bool(list(decision_window.get("blockers") or []))
        )
        expected_audit_statuses = {"BLOCK"}

    decision_binding_matches = (
        decision_window.get("schema_version") == EXPECTED_FORWARD_DECISION_WINDOW_SCHEMA_VERSION
        and decision_window.get("policy") == EXPECTED_FORWARD_DECISION_POLICY
        and str(decision_window.get("candidate_hash") or "")
        == str(candidate_source.get("candidate_hash") or "")
        and str(decision_window.get("candidate_spec_hash") or "") == expected_spec_hash
        and str(decision_window.get("forward_threshold_contract_hash") or "")
        == expected_threshold_hash
        and str(decision_window.get("statistical_contract_hash") or "")
        == str(audit_binding.get("statistical_contract_hash") or "")
        and str(decision_window.get("stage_hash") or "") == str(stage.get("stage_hash") or "")
        and decision_window.get("later_settlements_used") is False
        and prefix_matches
        and risk_binding_matches
    )
    try:
        authority_scan_clear = not authority_violations(
            forward_audit,
            path="$.forward_statistical_audit",
        )
    except RecursionError:
        authority_scan_clear = False
    zero_authority = (
        authority_scan_clear
        and forward_audit.get("research_only") is True
        and forward_audit.get("observation_only") is True
        and forward_audit.get("simulation_only") is True
        and forward_audit.get("profitability_proven") is False
        and forward_audit.get("paper_authorized") is False
        and forward_audit.get("live_order_allowed") is False
        and decision_window.get("research_only") is True
        and decision_window.get("observation_only") is True
        and decision_window.get("simulation_only") is True
        and decision_window.get("profitability_proven") is False
        and decision_window.get("paper_authorized") is False
        and decision_window.get("live_order_allowed") is False
    )
    statistical_contract_safe_integers = all(
        _v3_safe_integer(statistical_contract.get(name), minimum=1) is not None
        for name in (
            "periods_per_year",
            "resample_count",
            "block_length",
            "minimum_observations",
            "selection_trial_count",
        )
    )
    stage_observation_count = _v3_safe_integer(stage.get("observation_count"))
    stage_count_matches = (
        not due
        or (
            stage_observation_count is not None
            and stage_observation_count == prefix_outcomes
        )
    )
    audit_core_checks_pass = all(
        audit_checks.get(name) is True
        for name in (
            "candidate_authority_is_research_only",
            "forward_threshold_contract_pass",
            "settlement_series_integrity_pass",
            "historical_statistical_contract_verified",
            "same_statistical_contract_except_forward_maturity_floor",
            "first_joint_maturity_prefix_integrity_pass",
            "single_statistical_look_uses_frozen_prefix_only",
            "first_joint_maturity_risk_acceptance_integrity_pass",
            "zero_execution_authority",
        )
    )
    audit_integrity_pass = (
        bool(forward_audit)
        and forward_audit.get("schema_version")
        == EXPECTED_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION
        and bool(str(forward_audit.get("audit_hash") or ""))
        and forward_audit.get("verification_status") == "PASS"
        and forward_audit.get("semantic_recomputed") is True
        and audit_binding_matches
        and audit_maturity_matches
        and decision_hash_valid
        and decision_binding_matches
        and decision_semantics_match
        and risk_semantics_match
        and forward_audit.get("status") in expected_audit_statuses
        and dict(forward_audit.get("contract_comparison") or {}).get("status") == "PASS"
        and audit_core_checks_pass
        and zero_authority
    )

    integrity_checks = dict(legacy_source.get("integrity_checks") or {})
    integrity_checks.update({
        "forward_readiness_v3_inputs_acyclic": not cyclic_inputs,
        "candidate_forward_threshold_contract_v3_pass": (
            threshold_contract.get("status") == "PASS"
        ),
        "forward_progress_safe_integers": progress_values_valid,
        "forward_statistical_audit_v2_present": bool(forward_audit),
        "forward_statistical_audit_v2_integrity_pass": audit_integrity_pass,
        "forward_statistical_audit_v2_binding_pass": audit_binding_matches,
        "forward_statistical_audit_v2_maturity_pass": audit_maturity_matches,
        "first_joint_maturity_prefix_pass": prefix_matches,
        "first_joint_maturity_decision_hash_pass": decision_hash_valid,
        "first_joint_maturity_decision_binding_pass": decision_binding_matches,
        "first_joint_maturity_decision_semantics_pass": decision_semantics_match,
        "first_joint_maturity_risk_hash_pass": risk_hash_valid,
        "first_joint_maturity_risk_binding_pass": risk_binding_matches,
        "first_joint_maturity_risk_semantics_pass": risk_semantics_match,
        "forward_statistical_contract_safe_integers": statistical_contract_safe_integers,
        "forward_statistical_stage_count_safe": stage_count_matches,
        "forward_statistical_audit_v2_zero_execution_authority": zero_authority,
    })
    evidence_checks = {
        "first_joint_maturity_decision_pass": (decision_status == "PASS" if due else True),
        "first_joint_maturity_review_action_required": (
            research_action == "REVIEW_REQUIRED" if due else True
        ),
        "forward_statistical_evidence_is_not_profit_or_authorization": zero_authority,
    }
    integrity_blockers = [name for name, passed in integrity_checks.items() if not passed]
    evidence_blockers = [name for name, passed in evidence_checks.items() if not passed]
    if integrity_blockers:
        status = "BLOCK"
    elif not due:
        status = "COLLECTING"
    elif evidence_blockers:
        status = "RESEARCH_REVIEW_BLOCKED"
    else:
        status = "RESEARCH_REVIEW_READY"

    safe_progress = {
        "forward_outcomes": outcome_count,
        "required_forward_outcomes": required_outcomes,
        "remaining_forward_outcomes": max(required_outcomes - outcome_count, 0),
        "settlements": settlement_value or 0,
        "captured_observations": captured_value or 0,
        "executed_rebalances": rebalance_count,
        "required_executed_rebalances": required_rebalances,
        "remaining_executed_rebalances": max(required_rebalances - rebalance_count, 0),
    }
    return {
        **legacy_source,
        "schema_version": PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        "status": status,
        "promotion_status": "REVIEW_REQUIRED" if status == "RESEARCH_REVIEW_READY" else "BLOCK",
        "blockers": list(dict.fromkeys([*integrity_blockers, *evidence_blockers])),
        "integrity_checks": integrity_checks,
        "evidence_checks": evidence_checks,
        "progress": safe_progress,
        "forward_threshold_contract": threshold_contract,
        "forward_statistical_audit_due_status": expected_maturity_status,
        "decision_policy": EXPECTED_FORWARD_DECISION_POLICY,
        "decision_status": decision_status or "MISSING",
        "research_action": research_action or "BLOCK",
        "historical_statistical_claim_status": str(
            historical_source.get("status") or "MISSING"
        ),
        "forward_statistical_audit": {
            "schema_version": str(forward_audit.get("schema_version") or ""),
            "status": str(forward_audit.get("status") or "MISSING"),
            "conclusion": str(forward_audit.get("conclusion") or ""),
            "audit_hash": str(forward_audit.get("audit_hash") or ""),
            "verification_status": str(forward_audit.get("verification_status") or "NOT_RUN"),
            "verification_blockers": list(forward_audit.get("verification_blockers") or []),
            "maturity": audit_maturity,
            "input_binding": audit_binding,
            "decision_window": decision_window,
            "contract_comparison": dict(forward_audit.get("contract_comparison") or {}),
            "evidence_scope": str(forward_audit.get("evidence_scope") or ""),
            "profitability_proven": False,
            "research_only": True,
            "observation_only": True,
            "simulation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
