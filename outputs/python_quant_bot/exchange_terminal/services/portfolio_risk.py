from __future__ import annotations

import hashlib
import json
import math
from statistics import fmean
from typing import Any

from hakimi_research.candle_contract import candle_is_complete


PORTFOLIO_RISK_SCHEMA_VERSION = "portfolio-risk-budget-v1"
DEFAULT_LIMITS = {
    "max_single_position_pct": 35.0,
    "max_gross_exposure_pct": 70.0,
    "max_net_exposure_pct": 60.0,
    "max_correlated_cluster_pct": 45.0,
    "max_named_cluster_pct": 45.0,
    "max_positions": 4,
    "correlation_threshold": 0.80,
    "require_correlation_for_new_symbol": True,
}


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _positive(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return number if math.isfinite(number) and number > 0 else 0.0


def _completed(row: dict[str, Any]) -> bool:
    return candle_is_complete(row, default_if_missing=False)


def _close_series(rows: list[dict[str, Any]]) -> dict[str, float]:
    closes: dict[str, float] = {}
    for raw in rows:
        if not isinstance(raw, dict) or not _completed(raw):
            continue
        key = str(raw.get("date") or "").strip()[:10]
        close = _positive(raw.get("close"))
        if key and close > 0:
            closes[key] = close
    return closes


def aligned_return_correlation(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    *,
    lookback: int = 60,
    minimum_overlap: int = 40,
) -> dict[str, Any]:
    left = _close_series(left_rows)
    right = _close_series(right_rows)
    common_dates = sorted(set(left) & set(right))
    pairs: list[tuple[float, float]] = []
    for previous_date, current_date in zip(common_dates[:-1], common_dates[1:]):
        left_previous = left[previous_date]
        right_previous = right[previous_date]
        if left_previous <= 0 or right_previous <= 0:
            continue
        pairs.append((
            left[current_date] / left_previous - 1.0,
            right[current_date] / right_previous - 1.0,
        ))
    pairs = pairs[-max(int(lookback), 2):]
    required = max(int(minimum_overlap), 2)
    if len(pairs) < required:
        return {
            "status": "BLOCK",
            "correlation": None,
            "overlap": len(pairs),
            "required_overlap": required,
            "blockers": [f"aligned_returns:{len(pairs)}<{required}"],
        }
    left_returns = [item[0] for item in pairs]
    right_returns = [item[1] for item in pairs]
    left_mean = fmean(left_returns)
    right_mean = fmean(right_returns)
    covariance = fmean([
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in pairs
    ])
    left_variance = fmean([(value - left_mean) ** 2 for value in left_returns])
    right_variance = fmean([(value - right_mean) ** 2 for value in right_returns])
    denominator = math.sqrt(left_variance * right_variance)
    if denominator <= 1e-15:
        return {
            "status": "BLOCK",
            "correlation": None,
            "overlap": len(pairs),
            "required_overlap": required,
            "blockers": ["zero_return_variance"],
        }
    correlation = max(-1.0, min(covariance / denominator, 1.0))
    return {
        "status": "PASS",
        "correlation": round(correlation, 6),
        "overlap": len(pairs),
        "required_overlap": required,
        "blockers": [],
    }


def build_correlation_matrix(
    payloads: dict[str, dict[str, Any]],
    *,
    lookback: int = 60,
    minimum_overlap: int = 40,
) -> dict[str, Any]:
    normalized_payloads = {str(symbol).upper(): dict(payload or {}) for symbol, payload in payloads.items()}
    symbols = sorted(normalized_payloads)
    pairs: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    for left_index, left_symbol in enumerate(symbols):
        left_rows = list((normalized_payloads.get(left_symbol) or {}).get("rows") or [])
        for right_symbol in symbols[left_index + 1:]:
            right_rows = list((normalized_payloads.get(right_symbol) or {}).get("rows") or [])
            result = aligned_return_correlation(
                left_rows,
                right_rows,
                lookback=lookback,
                minimum_overlap=minimum_overlap,
            )
            pair_key = f"{left_symbol}|{right_symbol}"
            pairs[pair_key] = result
            if result.get("status") != "PASS":
                blockers.append(f"{pair_key}:{'/'.join(result.get('blockers') or ['unavailable'])}")
    payload = {
        "schema_version": PORTFOLIO_RISK_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "symbols": symbols,
        "lookback": max(int(lookback), 2),
        "minimum_overlap": max(int(minimum_overlap), 2),
        "pairs": pairs,
        "blockers": blockers,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["matrix_hash"] = _canonical_hash(payload)
    return payload


def _correlation_value(correlations: dict[str, Any], left: str, right: str) -> float | None:
    if left == right:
        return 1.0
    key = "|".join(sorted((left, right)))
    raw = correlations.get(key)
    if isinstance(raw, dict):
        raw = raw.get("correlation")
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    return max(-1.0, min(value, 1.0)) if math.isfinite(value) else None


def _normalized_positions(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in positions:
        if not isinstance(raw, dict):
            continue
        symbol = str(raw.get("symbol") or "").upper()
        notional = _positive(raw.get("notional") or raw.get("position_value") or raw.get("market_value"))
        direction = str(raw.get("direction") or raw.get("side") or "LONG").upper()
        if symbol and notional > 0 and direction in {"LONG", "SHORT"}:
            normalized.append({
                "symbol": symbol,
                "notional": notional,
                "direction": direction,
                "cluster": str(raw.get("cluster") or "").upper(),
            })
    return normalized


def evaluate_portfolio_risk(
    *,
    equity: float,
    positions: list[dict[str, Any]],
    proposed_symbol: str,
    proposed_notional: float,
    proposed_direction: str = "LONG",
    proposed_cluster: str = "",
    risk_increasing: bool = True,
    correlations: dict[str, Any] | None = None,
    regime: dict[str, Any] | None = None,
    limits: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_equity = _positive(equity)
    symbol = str(proposed_symbol or "").upper()
    amount = _positive(proposed_notional)
    direction = str(proposed_direction or "LONG").upper()
    cluster = str(proposed_cluster or "").upper()
    current = _normalized_positions(list(positions or []))
    settings = {**DEFAULT_LIMITS, **dict(limits or {})}
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, message: str, *, blocking: bool = True) -> None:
        checks.append({
            "name": name,
            "ok": bool(passed),
            "blocking": bool(blocking),
            "message": message,
        })

    if not risk_increasing:
        add("risk_reduction_path", True, "Risk-reducing orders remain available.", blocking=False)
        result = {
            "schema_version": PORTFOLIO_RISK_SCHEMA_VERSION,
            "status": "PASS",
            "portfolio_gate_passed": True,
            "checks": checks,
            "reject_reasons": [],
            "risk_increasing": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        result["check_hash"] = _canonical_hash(result)
        return result

    add("equity_positive", clean_equity > 0, f"Portfolio equity {clean_equity:.2f}.")
    add("symbol_present", bool(symbol), f"Proposed symbol {symbol or '--'}.")
    add("notional_positive", amount > 0, f"Proposed notional {amount:.2f}.")
    add("direction_valid", direction in {"LONG", "SHORT"}, f"Proposed direction {direction or '--'}.")

    gross_before = sum(item["notional"] for item in current)
    net_before = sum(item["notional"] * (1.0 if item["direction"] == "LONG" else -1.0) for item in current)
    signed_proposal = amount * (1.0 if direction == "LONG" else -1.0)
    gross_after = gross_before + amount
    net_after = net_before + signed_proposal
    existing_symbols = {item["symbol"] for item in current}
    position_count_after = len(existing_symbols | ({symbol} if symbol else set()))

    regime_multiplier = 1.0
    if isinstance(regime, dict) and regime:
        if regime.get("status") != "PASS":
            add("market_regime_available", False, "Market regime evidence is unavailable.")
        else:
            regime_multiplier = max(0.0, min(float(regime.get("long_only_budget_multiplier") or 0.0), 1.0)) if direction == "LONG" else 1.0
            add("market_regime_available", True, f"Market regime {regime.get('regime_id') or '--'}.", blocking=False)
    else:
        add("market_regime_available", True, "Market regime budget was not requested for this gate.", blocking=False)

    single_limit_pct = max(float(settings["max_single_position_pct"]), 0.0) * regime_multiplier
    gross_limit_pct = max(float(settings["max_gross_exposure_pct"]), 0.0)
    net_limit_pct = max(float(settings["max_net_exposure_pct"]), 0.0)
    max_positions = max(int(settings["max_positions"]), 1)
    single_after = amount + sum(item["notional"] for item in current if item["symbol"] == symbol and item["direction"] == direction)
    single_pct = single_after / max(clean_equity, 1e-12) * 100.0
    gross_pct = gross_after / max(clean_equity, 1e-12) * 100.0
    net_pct = abs(net_after) / max(clean_equity, 1e-12) * 100.0
    add("single_position_limit", single_pct <= single_limit_pct + 1e-9, f"Single position {single_pct:.2f}% / limit {single_limit_pct:.2f}%.")
    add("gross_exposure_limit", gross_pct <= gross_limit_pct + 1e-9, f"Gross exposure {gross_pct:.2f}% / limit {gross_limit_pct:.2f}%.")
    add("net_exposure_limit", net_pct <= net_limit_pct + 1e-9, f"Net exposure {net_pct:.2f}% / limit {net_limit_pct:.2f}%.")
    add("position_count_limit", position_count_after <= max_positions, f"Position count {position_count_after} / limit {max_positions}.")

    named_cluster_notional = amount
    if cluster:
        named_cluster_notional += sum(item["notional"] for item in current if item["cluster"] == cluster)
    named_cluster_pct = named_cluster_notional / max(clean_equity, 1e-12) * 100.0 if cluster else 0.0
    named_cluster_limit = max(float(settings["max_named_cluster_pct"]), 0.0)
    add(
        "named_cluster_limit",
        not cluster or named_cluster_pct <= named_cluster_limit + 1e-9,
        f"Named cluster {cluster or '--'} exposure {named_cluster_pct:.2f}% / limit {named_cluster_limit:.2f}%.",
        blocking=bool(cluster),
    )

    matrix = dict(correlations or {})
    if isinstance(matrix.get("pairs"), dict):
        matrix = dict(matrix["pairs"])
    correlation_threshold = max(0.0, min(float(settings["correlation_threshold"]), 1.0))
    correlated_notional = amount
    missing_correlations: list[str] = []
    correlated_symbols: list[str] = []
    for item in current:
        if item["symbol"] == symbol:
            continue
        correlation = _correlation_value(matrix, symbol, item["symbol"])
        if correlation is None:
            missing_correlations.append(item["symbol"])
        elif abs(correlation) >= correlation_threshold:
            correlated_notional += item["notional"]
            correlated_symbols.append(item["symbol"])
    require_correlation = bool(settings["require_correlation_for_new_symbol"])
    add(
        "correlation_coverage",
        not (require_correlation and symbol not in existing_symbols and missing_correlations),
        "Correlation coverage complete." if not missing_correlations else f"Missing correlation for: {', '.join(sorted(set(missing_correlations)))}.",
    )
    correlated_pct = correlated_notional / max(clean_equity, 1e-12) * 100.0
    correlated_limit = max(float(settings["max_correlated_cluster_pct"]), 0.0)
    add(
        "correlated_cluster_limit",
        correlated_pct <= correlated_limit + 1e-9,
        f"Correlated cluster {correlated_pct:.2f}% / limit {correlated_limit:.2f}% ({', '.join(correlated_symbols) or 'proposal only'}).",
    )

    reject_reasons = [item["message"] for item in checks if item["blocking"] and not item["ok"]]
    result = {
        "schema_version": PORTFOLIO_RISK_SCHEMA_VERSION,
        "status": "PASS" if not reject_reasons else "BLOCK",
        "portfolio_gate_passed": not reject_reasons,
        "checks": checks,
        "reject_reasons": reject_reasons,
        "risk_increasing": True,
        "proposed_symbol": symbol,
        "proposed_direction": direction,
        "proposed_notional": round(amount, 2),
        "equity": round(clean_equity, 2),
        "exposure_after": {
            "single_position_pct": round(single_pct, 4),
            "gross_exposure_pct": round(gross_pct, 4),
            "net_exposure_pct": round(net_pct, 4),
            "named_cluster_pct": round(named_cluster_pct, 4),
            "correlated_cluster_pct": round(correlated_pct, 4),
            "position_count": position_count_after,
        },
        "limits": settings,
        "regime_budget_multiplier": round(regime_multiplier, 4),
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    result["check_hash"] = _canonical_hash(result)
    return result
