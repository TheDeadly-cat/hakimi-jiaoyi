from __future__ import annotations

import hashlib
import json
from typing import Any


STRATEGY_RISK_PROFILE_VERSION = "strategy-risk-profile-v1"

TREND_STRATEGIES = {
    "dual_ma",
    "macd",
    "momentum",
    "livermore",
    "turtle",
    "darvas",
    "volume_trend",
    "trend_pullback",
    "squeeze_breakout",
}
MEAN_REVERSION_STRATEGIES = {"bollinger", "rsi"}


def _hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def strategy_research_risk_profile(
    strategy_id: str,
    base_risk: dict[str, Any],
    *,
    preserve_explicit_transaction_costs: bool = False,
) -> dict[str, Any]:
    clean_id = str(strategy_id or "").strip().lower()
    fee_rate = (
        float(base_risk["fee_rate"])
        if preserve_explicit_transaction_costs and "fee_rate" in base_risk
        else float(base_risk.get("fee_rate") or 0.0005)
    )
    slippage_bps = (
        float(base_risk["slippage_bps"])
        if preserve_explicit_transaction_costs and "slippage_bps" in base_risk
        else float(base_risk.get("slippage_bps") or 2.0)
    )
    risk = {
        "position_pct": float(base_risk.get("position_pct") or 35.0),
        "take_profit_pct": float(base_risk.get("take_profit_pct") or 0.0),
        "stop_loss_pct": float(base_risk.get("stop_loss_pct") or 0.0),
        "fee_rate": fee_rate,
        "slippage_bps": slippage_bps,
        "leverage": 1.0,
    }
    if clean_id in TREND_STRATEGIES:
        profile_id = "TREND_STRUCTURE_EXIT"
        risk.update({"take_profit_pct": 0.0, "stop_loss_pct": 8.0})
        rationale = "Trend systems keep the right tail open, exit on structure, and use an 8% emergency stop."
    elif clean_id in MEAN_REVERSION_STRATEGIES:
        profile_id = "MEAN_REVERSION_BOUNDED_EXIT"
        risk.update({"take_profit_pct": 6.0, "stop_loss_pct": 4.0})
        rationale = "Mean-reversion systems use bounded profit and loss exits in addition to signal exits."
    else:
        profile_id = "BASE_RESEARCH_RISK"
        rationale = "No strategy-class override is available; the explicit batch risk is preserved."
    payload = {
        "version": STRATEGY_RISK_PROFILE_VERSION,
        "profile_id": profile_id,
        "strategy_id": clean_id,
        "risk": risk,
        "rationale": rationale,
    }
    return {**payload, "risk_hash": _hash(payload)}
