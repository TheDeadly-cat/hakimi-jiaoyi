from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .portfolio_risk import evaluate_portfolio_risk


PORTFOLIO_SHADOW_RISK_SCHEMA_VERSION = "portfolio-shadow-risk-v1"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if math.isfinite(parsed) else default


def build_shadow_portfolio_risk(
    *,
    candidate: dict[str, Any],
    backtest_report: dict[str, Any],
    correlation_matrix: dict[str, Any],
    hypothetical_equity: float = 100_000.0,
) -> dict[str, Any]:
    decision = dict(backtest_report.get("pending_decision_at_end") or {})
    manifest = dict(backtest_report.get("dataset_manifest") or {})
    spec = dict(candidate.get("spec") or {})
    target_symbols = [str(symbol).upper() for symbol in decision.get("target_symbols") or []]
    target_weights = {str(symbol).upper(): max(_number(weight), 0.0) for symbol, weight in dict(decision.get("target_weights") or {}).items()}
    hold_observation = not bool(decision.get("execute", True))
    weights_recovered = False
    final_positions = dict(backtest_report.get("final_positions") or {})
    if target_symbols and any(target_weights.get(symbol, 0.0) <= 0 for symbol in target_symbols):
        market_values = {
            symbol: max(_number((final_positions.get(symbol) or {}).get("market_value")), 0.0)
            for symbol in target_symbols
        }
        total_market_value = sum(market_values.values())
        if total_market_value > 0:
            target_weights = {symbol: market_values[symbol] / total_market_value for symbol in target_symbols}
            weights_recovered = True
    allocation = max(0.0, min(_number(decision.get("target_allocation_pct")) / 100.0, 1.0))
    equity = max(_number(hypothetical_equity), 0.0)
    clusters = {str(symbol).upper(): str(cluster or symbol).upper() for symbol, cluster in dict(spec.get("clusters") or {}).items()}
    liquidity = dict(decision.get("liquidity") or {})
    inherited_decision: dict[str, Any] = {}
    if target_symbols and not all(symbol in liquidity for symbol in target_symbols):
        for historical in reversed(list(backtest_report.get("decisions") or [])):
            historical_symbols = {str(symbol).upper() for symbol in historical.get("target_symbols") or []}
            if set(target_symbols).issubset(historical_symbols) and historical.get("liquidity"):
                inherited_decision = dict(historical)
                liquidity = dict(historical.get("liquidity") or {})
                break
    adjustment = dict(manifest.get("adjustment_evidence") or {})
    data_revisions = dict(manifest.get("data_revision_evidence") or {})
    effective_regime = dict(decision.get("regime") or inherited_decision.get("regime") or {})
    blockers: list[str] = []
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(passed), "detail": detail})
        if not passed:
            blockers.append(f"{name}:{detail}")

    add("candidate_hash", bool(candidate.get("candidate_hash")), str(candidate.get("candidate_hash") or "missing"))
    add("backtest_status", bool(backtest_report.get("ok")), "PASS" if backtest_report.get("ok") else "backtest_failed")
    add("hypothetical_equity", equity > 0, f"{equity:.2f}")
    add("target_count", len(target_symbols) == len(set(target_symbols)), f"{len(target_symbols)} unique targets")
    missing_weights = sorted(symbol for symbol in target_symbols if target_weights.get(symbol, 0.0) <= 0)
    add("target_weights", not missing_weights, "complete" if not missing_weights else f"missing:{','.join(missing_weights)}")
    if target_symbols:
        weight_sum = sum(target_weights.get(symbol, 0.0) for symbol in target_symbols)
        add("weight_sum", 0 < weight_sum <= 1.0 + 1e-5, f"{weight_sum:.8f}")
        add(
            "correlation_matrix",
            correlation_matrix.get("status") == "PASS",
            str(correlation_matrix.get("status") or "missing"),
        )
    else:
        add("risk_off_cash_state", allocation <= 1e-12, f"allocation={allocation:.8f}")

    positions: list[dict[str, Any]] = []
    per_symbol: list[dict[str, Any]] = []
    for symbol in target_symbols:
        liquidity_row = dict(liquidity.get(symbol) or {})
        adjustment_row = dict(adjustment.get(symbol) or {})
        revision_row = dict(data_revisions.get(symbol) or {})
        liquidity_ok = hold_observation or bool(liquidity_row.get("eligible"))
        adjustment_ok = bool(adjustment_row.get("backtest_eligible"))
        revision_ok = not revision_row or str(revision_row.get("status") or "REVIEW").upper() != "BLOCK"
        if not liquidity_ok:
            blockers.append(f"{symbol}:liquidity_not_eligible")
        if not adjustment_ok:
            blockers.append(f"{symbol}:adjustment_not_eligible")
        if not revision_ok:
            blockers.append(f"{symbol}:data_revision_not_eligible")
        notional = equity * allocation * target_weights.get(symbol, 0.0)
        result = evaluate_portfolio_risk(
            equity=equity,
            positions=positions,
            proposed_symbol=symbol,
            proposed_notional=notional,
            proposed_direction="LONG",
            proposed_cluster=clusters.get(symbol, symbol),
            risk_increasing=True,
            correlations=correlation_matrix,
            regime=effective_regime,
        )
        per_symbol.append({
            "symbol": symbol,
            "target_notional": round(notional, 2),
            "liquidity": liquidity_row,
            "adjustment_evidence_hash": adjustment_row.get("evidence_hash", ""),
            "data_revision_evidence_hash": revision_row.get("evidence_hash", ""),
            "portfolio_risk": result,
        })
        if result.get("status") != "PASS":
            blockers.extend(f"{symbol}:portfolio:{reason}" for reason in result.get("reject_reasons") or ["risk_gate_blocked"])
        else:
            positions.append({
                "symbol": symbol,
                "notional": notional,
                "direction": "LONG",
                "cluster": clusters.get(symbol, symbol),
            })

    payload = {
        "schema_version": PORTFOLIO_SHADOW_RISK_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "checks": checks,
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "signal_date": str(decision.get("signal_date") or manifest.get("last") or ""),
        "dataset_hash": str(manifest.get("data_hash") or ""),
        "correlation_matrix_hash": str(correlation_matrix.get("matrix_hash") or ""),
        "hypothetical_equity": round(equity, 2),
        "target_allocation_pct": round(allocation * 100.0, 6),
        "target_symbols": target_symbols,
        "hold_observation": hold_observation,
        "weight_source": "FINAL_POSITION_MARKET_VALUES" if weights_recovered else "DECISION_TARGET_WEIGHTS",
        "liquidity_source_date": str(inherited_decision.get("signal_date") or decision.get("signal_date") or ""),
        "regime_id": str(effective_regime.get("regime_id") or ""),
        "per_symbol": per_symbol,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["risk_snapshot_hash"] = _canonical_hash(payload)
    return payload
