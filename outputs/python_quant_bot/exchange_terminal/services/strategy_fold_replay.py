from __future__ import annotations

import hashlib
import json
from typing import Any

from .backtest_engine import (
    EXECUTION_MODEL_VERSION,
    prepare_backtest_dataset,
    run_causal_long_only_backtest,
)
from .strategy_signals import (
    build_strategy_signal_fn,
    SIGNAL_ENGINE_VERSION,
    strategy_signal_input,
    strategy_startup_candles_for_params,
    strategy_validation_capability,
)


STRATEGY_FIXED_SLICE_BACKTEST_INPUT_SCHEMA_VERSION = (
    "strategy-fixed-slice-backtest-input-v1"
)
STRATEGY_FIXED_SLICE_BACKTEST_RESULT_SCHEMA_VERSION = (
    "strategy-fixed-slice-backtest-result-v1"
)


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _canonical_mapping(value: dict[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("fixed_slice_mapping_invalid")
    return json.loads(json.dumps(value, ensure_ascii=True, sort_keys=True, default=str))


def _dataset_identity(manifest: dict[str, Any] | Any) -> dict[str, Any]:
    source = manifest if isinstance(manifest, dict) else {}
    return {
        "symbol": str(source.get("symbol") or ""),
        "source": str(source.get("source") or ""),
        "market": str(source.get("market") or ""),
        "timeframe": str(source.get("timeframe") or ""),
        "hash_scope": str(source.get("hash_scope") or ""),
        "data_hash": str(source.get("data_hash") or ""),
        "row_count": source.get("row_count"),
        "first": str(source.get("first") or ""),
        "last": str(source.get("last") or ""),
        "first_ts_ms": source.get("first_ts_ms"),
        "last_ts_ms": source.get("last_ts_ms"),
    }


def stable_causal_backtest_result_projection(
    report: dict[str, Any] | Any,
) -> dict[str, Any]:
    """Project the complete stable result surface used by replay evidence.

    The full trade and equity lists remain outside the evidence object, while
    their canonical digests bind every event/point.  Callers must still replay
    the causal engine; this helper is a projection, not an authenticity claim.
    """
    payload = report if isinstance(report, dict) else {}
    content = {
        "schema_version": STRATEGY_FIXED_SLICE_BACKTEST_RESULT_SCHEMA_VERSION,
        "ok": payload.get("ok") is True,
        "error": str(payload.get("error") or ""),
        "data_points": payload.get("data_points"),
        "evaluation_window": payload.get("evaluation_window")
        if isinstance(payload.get("evaluation_window"), dict)
        else {},
        "fee_rate": payload.get("fee_rate"),
        "slippage_bps": payload.get("slippage_bps"),
        "initial_cash": payload.get("initial_cash"),
        "final_equity": payload.get("final_equity"),
        "total_return_pct": payload.get("total_return_pct"),
        "annualized_pct": payload.get("annualized_pct"),
        "max_drawdown_pct": payload.get("max_drawdown_pct"),
        "win_rate_pct": payload.get("win_rate_pct"),
        "sharpe": payload.get("sharpe"),
        "trade_count": payload.get("trade_count"),
        "order_event_count": payload.get("order_event_count"),
        "total_fees": payload.get("total_fees"),
        "turnover": payload.get("turnover"),
        "exposure_pct": payload.get("exposure_pct"),
        "ambiguous_intrabar_count": payload.get("ambiguous_intrabar_count"),
        "pending_signal_at_end": str(payload.get("pending_signal_at_end") or ""),
        "trades_hash": canonical_hash(payload.get("trades") if isinstance(payload.get("trades"), list) else []),
        "equity_curve_hash": canonical_hash(
            payload.get("equity_curve") if isinstance(payload.get("equity_curve"), list) else []
        ),
        "execution_model": str(payload.get("execution_model") or ""),
        "research_only": payload.get("research_only") is True,
        "paper_authorized": payload.get("paper_authorized") is True,
        "live_order_allowed": payload.get("live_order_allowed") is True,
    }
    return {**content, "result_hash": canonical_hash(content)}


def replay_fixed_chronological_slice(
    *,
    rows: list[dict[str, Any]] | Any,
    symbol: str,
    source: str,
    market: str,
    timeframe: str,
    fold_number: int,
    strategy_id: str,
    params: dict[str, Any] | Any,
    param_hash: str,
    risk: dict[str, Any] | Any,
) -> dict[str, Any]:
    """Run and seal one deterministic fixed-parameter chronological slice."""

    if not isinstance(rows, list) or not rows or not all(isinstance(item, dict) for item in rows):
        raise ValueError("fixed_slice_rows_invalid")
    if isinstance(fold_number, bool) or not isinstance(fold_number, int) or fold_number < 1:
        raise ValueError("fixed_slice_fold_number_invalid")
    clean_strategy_id = str(strategy_id or "").strip().lower()
    capability = strategy_validation_capability(clean_strategy_id)
    if capability.get("backtest_supported") is not True:
        raise ValueError("fixed_slice_strategy_not_backtest_supported")
    frozen_params = _canonical_mapping(params)
    if not param_hash or str(param_hash) != canonical_hash(frozen_params):
        raise ValueError("fixed_slice_param_hash_mismatch")
    frozen_risk = _canonical_mapping(risk)
    required_risk = (
        "position_pct",
        "take_profit_pct",
        "stop_loss_pct",
        "fee_rate",
        "slippage_bps",
        "leverage",
    )
    if any(field not in frozen_risk for field in required_risk):
        raise ValueError("fixed_slice_risk_incomplete")

    fold_source = f"{str(source or '')}:pretest_fold_{fold_number}"
    startup = strategy_startup_candles_for_params(clean_strategy_id, frozen_params)
    manifest = prepare_backtest_dataset(
        rows,
        symbol=str(symbol or ""),
        source=fold_source,
        timeframe=str(timeframe or "1D"),
        minimum_rows=1,
        market=str(market or ""),
    )["manifest"]
    input_content = {
        "schema_version": STRATEGY_FIXED_SLICE_BACKTEST_INPUT_SCHEMA_VERSION,
        "fold": fold_number,
        "dataset_identity": _dataset_identity(manifest),
        "strategy_id": clean_strategy_id,
        "params": frozen_params,
        "param_hash": str(param_hash),
        "risk": frozen_risk,
        "execution_model": EXECUTION_MODEL_VERSION,
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
        "signal_input": strategy_signal_input(clean_strategy_id),
        "startup_candles": startup,
        "evaluation_start_index": None,
        "initial_cash": 10_000.0,
    }
    input_identity = {**input_content, "input_hash": canonical_hash(input_content)}
    report = run_causal_long_only_backtest(
        rows=[dict(item) for item in rows],
        symbol=str(symbol or ""),
        source=fold_source,
        signal_fn=build_strategy_signal_fn(clean_strategy_id, frozen_params),
        position_pct=float(frozen_risk["position_pct"]),
        take_profit_pct=float(frozen_risk["take_profit_pct"]),
        stop_loss_pct=float(frozen_risk["stop_loss_pct"]),
        startup_candles=startup,
        fee_rate=float(frozen_risk["fee_rate"]),
        slippage_bps=float(frozen_risk["slippage_bps"]),
        leverage=float(frozen_risk["leverage"]),
        initial_cash=10_000.0,
        market=str(market or ""),
        timeframe=str(timeframe or "1D"),
        evaluation_start_index=None,
        signal_input=strategy_signal_input(clean_strategy_id),
    )
    return {
        "input_identity": input_identity,
        "result_projection": stable_causal_backtest_result_projection(report),
    }


__all__ = [
    "STRATEGY_FIXED_SLICE_BACKTEST_INPUT_SCHEMA_VERSION",
    "STRATEGY_FIXED_SLICE_BACKTEST_RESULT_SCHEMA_VERSION",
    "canonical_hash",
    "replay_fixed_chronological_slice",
    "stable_causal_backtest_result_projection",
]
