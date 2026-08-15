from __future__ import annotations

import json
import math
from datetime import date
from typing import Any

from .backtest_engine import (
    EXECUTION_MODEL_VERSION,
    causal_prefix_invariance_check,
    prepare_backtest_dataset,
    run_causal_long_only_backtest,
)
from .strategy_benchmark import buy_and_hold_report
from .strategy_cost_stress import (
    SELECTION_COST_STRESS_STAGE,
    build_strategy_cost_stress_contract,
    build_strategy_cost_stress_evidence,
    project_cost_stress_observation,
)
from .strategy_fold_replay import (
    canonical_hash,
    stable_causal_backtest_result_projection,
)
from .strategy_quality import strategy_lookahead_check
from .research_symbol_market import (
    RESEARCH_SYMBOL_MARKET_CLASSIFIER_VERSION,
    research_market_for_symbol,
)
from .strategy_signals import (
    SIGNAL_ENGINE_VERSION,
    build_strategy_signal_fn,
    strategy_signal_input,
    strategy_startup_candles_for_params,
    strategy_validation_capability,
)


STRATEGY_SELECTION_REPLAY_SCHEMA_VERSION = "strategy-selection-cell-replay-v1"
STRATEGY_SELECTION_REPLAY_INPUT_SCHEMA_VERSION = "strategy-selection-cell-input-v1"
STRATEGY_SELECTION_RUN_INPUT_SCHEMA_VERSION = "strategy-selection-run-input-v1"
STRATEGY_SELECTION_BENCHMARK_INPUT_SCHEMA_VERSION = (
    "strategy-selection-benchmark-input-v1"
)
STRATEGY_SELECTION_LOOKAHEAD_SCHEMA_VERSION = "strategy-selection-lookahead-v1"
DEVELOPMENT_SELECTION_SPLIT_SCHEMA_VERSION = (
    "development-selection-prefix-split-v1"
)
DEVELOPMENT_SELECTION_SPLIT_POLICY = (
    "TRAIN_VALIDATION_ONLY_INDEX_SPLIT_V1"
)


def _canonical_mapping(value: dict[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("strategy_selection_replay_mapping_invalid")
    return json.loads(
        json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    )


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
        "input_row_count": source.get("input_row_count"),
        "excluded_incomplete_count": source.get("excluded_incomplete_count"),
        "invalid_row_count": source.get("invalid_row_count"),
        "duplicate_count": source.get("duplicate_count"),
        "duplicate_trading_date_count": source.get("duplicate_trading_date_count"),
        "ordered": source.get("ordered") is True,
        "first": str(source.get("first") or ""),
        "last": str(source.get("last") or ""),
        "first_ts_ms": source.get("first_ts_ms"),
        "last_ts_ms": source.get("last_ts_ms"),
        "status": str(source.get("status") or "BLOCK"),
        "blockers": list(source.get("blockers") or []),
    }


def _native_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _number_or_zero(value: Any) -> float:
    number = _finite(value)
    return number if number is not None else 0.0


def build_development_selection_prefix_schedule(
    payloads: dict[str, dict[str, Any]] | Any,
    *,
    train_ratio: float,
    validation_ratio: float,
    minimum_segment_rows: int,
) -> dict[str, Any]:
    """Derive a development-only split from the physically truncated prefix.

    A development snapshot cannot reconstruct the original full-span calendar
    boundary after the protected test suffix has been removed.  This explicit
    index policy is therefore the only admissible train cutoff for schema 10
    development reports; formal reports continue to rebuild the calendar split
    from the complete frozen snapshot.
    """

    blockers: list[str] = []
    if not isinstance(payloads, dict) or not payloads:
        blockers.append("development_selection_payloads_invalid")
        clean_payloads: dict[str, dict[str, Any]] = {}
    else:
        clean_payloads = {
            str(symbol or "").strip().upper(): value
            for symbol, value in payloads.items()
            if str(symbol or "").strip() and isinstance(value, dict)
        }
        if len(clean_payloads) != len(payloads):
            blockers.append("development_selection_payload_identity_invalid")
    safe_train = _finite(train_ratio)
    safe_validation = _finite(validation_ratio)
    minimum = _native_nonnegative_int(minimum_segment_rows)
    if (
        safe_train is None
        or safe_validation is None
        or safe_train <= 0
        or safe_validation <= 0
        or safe_train + safe_validation > 1
    ):
        blockers.append("development_selection_ratio_invalid")
        projected_train_fraction = 0.0
    else:
        projected_train_fraction = safe_train / (safe_train + safe_validation)
    if minimum is None or minimum < 1:
        blockers.append("development_selection_minimum_rows_invalid")
        minimum = 1

    boundaries: dict[str, dict[str, Any]] = {}
    starts: list[str] = []
    ends: list[str] = []
    for symbol, payload in sorted(clean_payloads.items()):
        raw_rows = payload.get("rows")
        if (
            not isinstance(raw_rows, list)
            or not raw_rows
            or not all(isinstance(item, dict) for item in raw_rows)
        ):
            blockers.append(f"{symbol}:development_selection_rows_invalid")
            continue
        rows = [dict(item) for item in raw_rows]
        first = str(rows[0].get("date") or "")[:10]
        last = str(rows[-1].get("date") or "")[:10]
        try:
            date.fromisoformat(first)
            date.fromisoformat(last)
        except ValueError:
            blockers.append(f"{symbol}:development_selection_dates_invalid")
            continue
        train_end = int(math.floor(len(rows) * projected_train_fraction))
        validation_count = len(rows) - train_end
        if train_end < minimum:
            blockers.append(
                f"{symbol}:development_train_rows:{train_end}<{minimum}"
            )
        if validation_count < minimum:
            blockers.append(
                f"{symbol}:development_validation_rows:{validation_count}<{minimum}"
            )
        if not 0 < train_end < len(rows):
            blockers.append(f"{symbol}:development_selection_boundary_invalid")
            continue
        starts.append(first)
        ends.append(last)
        boundaries[symbol] = {
            "train_end_index": train_end,
            "validation_end_index": len(rows),
            "train_end_date": str(rows[train_end - 1].get("date") or "")[:10],
            "validation_end_date": last,
            "counts": {
                "train": train_end,
                "validation": validation_count,
                "test": 0,
            },
            "row_count": len(rows),
        }
    if len(boundaries) != len(clean_payloads) or not boundaries:
        blockers.append("development_selection_boundary_coverage_invalid")
    common_start = max(starts) if starts else ""
    common_end = min(ends) if ends else ""
    span_days = 0
    if common_start and common_end:
        try:
            span_days = (date.fromisoformat(common_end) - date.fromisoformat(common_start)).days
        except ValueError:
            blockers.append("development_selection_common_dates_invalid")
    return {
        "schema_version": DEVELOPMENT_SELECTION_SPLIT_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "common_start": common_start,
        "common_end": common_end,
        "train_end": "",
        "validation_end": common_end,
        "train_ratio": safe_train,
        "validation_ratio": safe_validation,
        "projected_train_fraction": round(projected_train_fraction, 12),
        "minimum_segment_rows": minimum,
        "span_days": span_days,
        "symbol_boundaries": boundaries,
        "blockers": list(dict.fromkeys(blockers)),
        "projection_policy": DEVELOPMENT_SELECTION_SPLIT_POLICY,
        "protected_test_rows_persisted": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _stable_prefix_projection(payload: dict[str, Any] | Any) -> dict[str, Any]:
    source = _canonical_mapping(payload) if isinstance(payload, dict) else {}
    content = {
        "version": str(source.get("version") or ""),
        "status": str(source.get("status") or "BLOCK"),
        "checkpoint_count": source.get("checkpoint_count"),
        "checks": source.get("checks") if isinstance(source.get("checks"), list) else [],
        "issues": source.get("issues") if isinstance(source.get("issues"), list) else [],
        "dataset_hash": str(source.get("dataset_hash") or ""),
        "dataset_rows": source.get("dataset_rows"),
        "signal_input": str(source.get("signal_input") or ""),
    }
    return {**content, "audit_hash": canonical_hash(content)}


def _stable_lookahead_projection(
    payload: dict[str, Any] | Any,
    *,
    prefix_invariance_hash: str,
) -> dict[str, Any]:
    source = payload if isinstance(payload, dict) else {}
    content = {
        "schema_version": STRATEGY_SELECTION_LOOKAHEAD_SCHEMA_VERSION,
        "status": str(source.get("status") or "BLOCK"),
        "score": source.get("score"),
        "issues": list(source.get("issues") or []),
        "checks": _canonical_mapping({"rows": source.get("checks") or []})["rows"],
        "sample_size": source.get("sample_size"),
        "startup_candles": source.get("startup_candles"),
        "max_window": source.get("max_window"),
        "prefix_invariance_hash": str(prefix_invariance_hash or ""),
    }
    return {**content, "lookahead_hash": canonical_hash(content)}


def _result_integrity_issues(role: str, result: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if result.get("ok") is not True:
        return issues
    for field in (
        "total_return_pct",
        "max_drawdown_pct",
        "sharpe",
        "final_equity",
    ):
        if _finite(result.get(field)) is None:
            issues.append(f"selection_replay_{role}_{field}_invalid")
    if (
        _finite(result.get("max_drawdown_pct")) is not None
        and float(result["max_drawdown_pct"]) < 0
    ):
        issues.append(f"selection_replay_{role}_drawdown_negative")
    if _native_nonnegative_int(result.get("trade_count")) is None:
        issues.append(f"selection_replay_{role}_trade_count_invalid")
    if _native_nonnegative_int(result.get("order_event_count")) is None:
        issues.append(f"selection_replay_{role}_order_event_count_invalid")
    if result.get("execution_model") != EXECUTION_MODEL_VERSION:
        issues.append(f"selection_replay_{role}_execution_model_mismatch")
    if (
        result.get("research_only") is not True
        or result.get("paper_authorized") is not False
        or result.get("live_order_allowed") is not False
    ):
        issues.append(f"selection_replay_{role}_execution_authority_invalid")
    return issues


def _run_strategy_replay(
    *,
    rows: list[dict[str, Any]],
    symbol: str,
    source: str,
    market: str,
    timeframe: str,
    run_role: str,
    strategy_id: str,
    params: dict[str, Any],
    param_hash: str,
    risk: dict[str, Any],
    startup_candles: int,
    evaluation_start_index: int | None,
    fee_rate: float,
    slippage_bps: float,
) -> dict[str, Any]:
    manifest = prepare_backtest_dataset(
        rows,
        symbol=symbol,
        source=source,
        timeframe=timeframe,
        minimum_rows=1,
        market=market,
    )["manifest"]
    input_content = {
        "schema_version": STRATEGY_SELECTION_RUN_INPUT_SCHEMA_VERSION,
        "run_role": str(run_role or ""),
        "dataset_identity": _dataset_identity(manifest),
        "strategy_id": strategy_id,
        "params": params,
        "param_hash": param_hash,
        "base_risk": risk,
        "effective_fee_rate": fee_rate,
        "effective_slippage_bps": slippage_bps,
        "execution_model": EXECUTION_MODEL_VERSION,
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
        "signal_input": strategy_signal_input(strategy_id),
        "startup_candles": startup_candles,
        "evaluation_start_index": evaluation_start_index,
        "initial_cash": 10_000.0,
    }
    report = run_causal_long_only_backtest(
        rows=[dict(item) for item in rows],
        symbol=symbol,
        source=source,
        signal_fn=build_strategy_signal_fn(strategy_id, params),
        position_pct=float(risk["position_pct"]),
        take_profit_pct=float(risk["take_profit_pct"]),
        stop_loss_pct=float(risk["stop_loss_pct"]),
        startup_candles=startup_candles,
        fee_rate=float(fee_rate),
        slippage_bps=float(slippage_bps),
        leverage=1.0,
        initial_cash=10_000.0,
        market=market,
        timeframe=timeframe,
        evaluation_start_index=evaluation_start_index,
        signal_input=strategy_signal_input(strategy_id),
    )
    return {
        "input_identity": {
            **input_content,
            "input_hash": canonical_hash(input_content),
        },
        "result_projection": stable_causal_backtest_result_projection(report),
    }


def _run_benchmark_replay(
    *,
    rows: list[dict[str, Any]],
    symbol: str,
    source: str,
    market: str,
    timeframe: str,
    risk: dict[str, Any],
    evaluation_start_index: int,
) -> dict[str, Any]:
    manifest = prepare_backtest_dataset(
        rows,
        symbol=symbol,
        source=source,
        timeframe=timeframe,
        minimum_rows=1,
        market=market,
    )["manifest"]
    input_content = {
        "schema_version": STRATEGY_SELECTION_BENCHMARK_INPUT_SCHEMA_VERSION,
        "run_role": "VALIDATION_BUY_AND_HOLD",
        "dataset_identity": _dataset_identity(manifest),
        "benchmark_policy": "BUY_AND_HOLD_NEXT_BAR_OPEN_V1",
        "position_pct": risk["position_pct"],
        "fee_rate": risk["fee_rate"],
        "slippage_bps": risk["slippage_bps"],
        "startup_candles": 80,
        "evaluation_start_index": evaluation_start_index,
        "execution_model": EXECUTION_MODEL_VERSION,
        "initial_cash": 10_000.0,
    }
    report = buy_and_hold_report(
        rows=[dict(item) for item in rows],
        symbol=symbol,
        source=source,
        position_pct=float(risk["position_pct"]),
        startup_candles=80,
        fee_rate=float(risk["fee_rate"]),
        slippage_bps=float(risk["slippage_bps"]),
        market=market,
        evaluation_start_index=evaluation_start_index,
    )
    return {
        "input_identity": {
            **input_content,
            "input_hash": canonical_hash(input_content),
        },
        "result_projection": stable_causal_backtest_result_projection(report),
    }


def build_strategy_selection_replay_evidence(
    *,
    selection_rows: list[dict[str, Any]] | Any,
    train_end_index: int,
    symbol: str,
    source: str,
    market: str,
    timeframe: str,
    variant_id: str,
    strategy_id: str,
    params: dict[str, Any] | Any,
    param_hash: str,
    implementation_fingerprint: str,
    risk: dict[str, Any] | Any,
) -> dict[str, Any]:
    """Replay every schema-10 selection metric from frozen causal inputs."""

    if (
        not isinstance(selection_rows, list)
        or not selection_rows
        or not all(isinstance(item, dict) for item in selection_rows)
    ):
        raise ValueError("strategy_selection_replay_rows_invalid")
    train_end = _native_nonnegative_int(train_end_index)
    if train_end is None or train_end < 1 or train_end >= len(selection_rows):
        raise ValueError("strategy_selection_replay_train_boundary_invalid")
    rows = [dict(item) for item in selection_rows]
    clean_symbol = str(symbol or "").strip().upper()
    clean_source = str(source or "").strip()
    clean_market = str(market or "").strip().lower()
    clean_timeframe = str(timeframe or "").strip().upper()
    if not clean_symbol or not clean_source:
        raise ValueError("strategy_selection_replay_dataset_identity_invalid")
    expected_market = research_market_for_symbol(clean_symbol)
    if clean_market != expected_market:
        raise ValueError("strategy_selection_replay_market_identity_mismatch")
    if clean_timeframe != "1D":
        raise ValueError("strategy_selection_replay_timeframe_not_daily")
    clean_strategy_id = str(strategy_id or "").strip().lower()
    clean_variant_id = str(variant_id or "").strip()
    clean_implementation_fingerprint = str(
        implementation_fingerprint or ""
    ).strip()
    if not clean_variant_id or not clean_implementation_fingerprint:
        raise ValueError("strategy_selection_replay_variant_identity_invalid")
    capability = strategy_validation_capability(clean_strategy_id)
    if capability.get("backtest_supported") is not True:
        raise ValueError("strategy_selection_replay_strategy_unsupported")
    frozen_params = _canonical_mapping(params)
    if not param_hash or str(param_hash) != canonical_hash(frozen_params):
        raise ValueError("strategy_selection_replay_param_hash_mismatch")
    frozen_risk = _canonical_mapping(risk)
    for field in (
        "position_pct",
        "take_profit_pct",
        "stop_loss_pct",
        "fee_rate",
        "slippage_bps",
        "leverage",
    ):
        if _finite(frozen_risk.get(field)) is None:
            raise ValueError(f"strategy_selection_replay_risk_invalid:{field}")
    if abs(float(frozen_risk["leverage"]) - 1.0) > 1e-9:
        raise ValueError("strategy_selection_replay_leverage_not_supported")

    startup = strategy_startup_candles_for_params(clean_strategy_id, frozen_params)
    prepared = prepare_backtest_dataset(
        rows,
        symbol=clean_symbol,
        source=clean_source,
        timeframe=clean_timeframe,
        minimum_rows=startup + 2,
        market=clean_market,
    )
    manifest = prepared["manifest"]
    clean_rows = [dict(item) for item in prepared.get("rows") or []]
    if len(clean_rows) != len(rows):
        raise ValueError("strategy_selection_replay_dataset_row_drift")
    if (
        manifest.get("input_row_count") != len(rows)
        or manifest.get("row_count") != len(rows)
        or manifest.get("excluded_incomplete_count") != 0
        or manifest.get("invalid_row_count") != 0
        or manifest.get("duplicate_count") != 0
        or manifest.get("duplicate_trading_date_count") != 0
        or manifest.get("ordered") is not True
    ):
        raise ValueError("strategy_selection_replay_dataset_not_canonical")
    cost_contract = build_strategy_cost_stress_contract(frozen_risk)
    input_content = {
        "schema_version": STRATEGY_SELECTION_REPLAY_INPUT_SCHEMA_VERSION,
        "dataset_identity": _dataset_identity(manifest),
        "train_end_index": train_end,
        "validation_end_index": len(clean_rows),
        "variant_id": clean_variant_id,
        "strategy_id": clean_strategy_id,
        "params": frozen_params,
        "param_hash": str(param_hash),
        "implementation_fingerprint": clean_implementation_fingerprint,
        "risk": frozen_risk,
        "cost_stress_contract": cost_contract,
        "symbol_market_classifier_version": (
            RESEARCH_SYMBOL_MARKET_CLASSIFIER_VERSION
        ),
        "execution_model": EXECUTION_MODEL_VERSION,
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
        "signal_input": strategy_signal_input(clean_strategy_id),
        "startup_candles": startup,
        "benchmark_policy": "BUY_AND_HOLD_NEXT_BAR_OPEN_V1",
        "lookahead_policy": "CAUSAL_PREFIX_INVARIANCE_AND_STATIC_SCAN_V1",
        "initial_cash": 10_000.0,
    }
    input_identity = {**input_content, "input_hash": canonical_hash(input_content)}

    train_run = _run_strategy_replay(
        rows=clean_rows[:train_end],
        symbol=clean_symbol,
        source=f"{clean_source}:research_train",
        market=clean_market,
        timeframe=clean_timeframe,
        run_role="TRAIN_CONFIGURED",
        strategy_id=clean_strategy_id,
        params=frozen_params,
        param_hash=str(param_hash),
        risk=frozen_risk,
        startup_candles=startup,
        evaluation_start_index=None,
        fee_rate=float(frozen_risk["fee_rate"]),
        slippage_bps=float(frozen_risk["slippage_bps"]),
    )
    validation_run = _run_strategy_replay(
        rows=clean_rows,
        symbol=clean_symbol,
        source=f"{clean_source}:research_validation",
        market=clean_market,
        timeframe=clean_timeframe,
        run_role="VALIDATION_CONFIGURED",
        strategy_id=clean_strategy_id,
        params=frozen_params,
        param_hash=str(param_hash),
        risk=frozen_risk,
        startup_candles=startup,
        evaluation_start_index=train_end,
        fee_rate=float(frozen_risk["fee_rate"]),
        slippage_bps=float(frozen_risk["slippage_bps"]),
    )
    benchmark_run = _run_benchmark_replay(
        rows=clean_rows,
        symbol=clean_symbol,
        source=f"{clean_source}:validation_buy_hold",
        market=clean_market,
        timeframe=clean_timeframe,
        risk=frozen_risk,
        evaluation_start_index=train_end,
    )
    cost_runs: list[dict[str, Any]] = []
    cost_observations: list[dict[str, Any]] = []
    for scenario in cost_contract.get("selection_scenarios") or []:
        name = str(scenario.get("name") or "")
        replay = _run_strategy_replay(
            rows=clean_rows,
            symbol=clean_symbol,
            source=f"{clean_source}:validation_cost_{name}",
            market=clean_market,
            timeframe=clean_timeframe,
            run_role=f"VALIDATION_COST_{name.upper()}",
            strategy_id=clean_strategy_id,
            params=frozen_params,
            param_hash=str(param_hash),
            risk=frozen_risk,
            startup_candles=startup,
            evaluation_start_index=train_end,
            fee_rate=float(scenario["fee_rate"]),
            slippage_bps=float(scenario["slippage_bps"]),
        )
        cost_runs.append({"name": name, **replay})
        cost_observations.append(
            project_cost_stress_observation(name, replay["result_projection"])
        )
    cost_sensitivity = build_strategy_cost_stress_evidence(
        stage=SELECTION_COST_STRESS_STAGE,
        risk=frozen_risk,
        baseline=project_cost_stress_observation(
            "configured", validation_run["result_projection"]
        ),
        scenarios=cost_observations,
    )

    prefix_raw = causal_prefix_invariance_check(
        rows=clean_rows,
        symbol=clean_symbol,
        source=f"{clean_source}:pretest_causal_audit",
        signal_factory=lambda _rows: build_strategy_signal_fn(
            clean_strategy_id, frozen_params
        ),
        position_pct=float(frozen_risk["position_pct"]),
        take_profit_pct=float(frozen_risk["take_profit_pct"]),
        stop_loss_pct=float(frozen_risk["stop_loss_pct"]),
        startup_candles=startup,
        fee_rate=float(frozen_risk["fee_rate"]),
        slippage_bps=float(frozen_risk["slippage_bps"]),
        leverage=1.0,
        initial_cash=10_000.0,
        market=clean_market,
        timeframe=clean_timeframe,
        signal_input=strategy_signal_input(clean_strategy_id),
    )
    prefix_invariance = _stable_prefix_projection(prefix_raw)
    lookahead_raw = strategy_lookahead_check(
        {"id": clean_strategy_id, "params": frozen_params},
        candle_count=len(clean_rows),
        startup_candles=startup,
        rows=clean_rows,
        prefix_invariance=prefix_raw,
    )
    lookahead = _stable_lookahead_projection(
        lookahead_raw,
        prefix_invariance_hash=str(prefix_invariance.get("audit_hash") or ""),
    )

    train_result = train_run["result_projection"]
    validation_result = validation_run["result_projection"]
    benchmark_result = benchmark_run["result_projection"]
    validation_return = _number_or_zero(validation_result.get("total_return_pct"))
    benchmark_return = _number_or_zero(benchmark_result.get("total_return_pct"))
    validation_drawdown = _number_or_zero(validation_result.get("max_drawdown_pct"))
    benchmark_drawdown = _number_or_zero(benchmark_result.get("max_drawdown_pct"))
    validation_sharpe = _number_or_zero(validation_result.get("sharpe"))
    benchmark_sharpe = _number_or_zero(benchmark_result.get("sharpe"))
    validation_efficiency = validation_return / max(validation_drawdown, 1.0)
    benchmark_efficiency = benchmark_return / max(benchmark_drawdown, 1.0)
    flat_metric_projection = {
        "dataset_status": manifest.get("status", "BLOCK"),
        "dataset_hash": manifest.get("data_hash", ""),
        "dataset_blockers": list(manifest.get("blockers") or []),
        "selection_input_rows": len(clean_rows),
        "selection_input_end": str(clean_rows[-1].get("date") or ""),
        "test_rows_evaluated": False,
        "train_ok": train_result.get("ok") is True,
        "train_return_pct": train_result.get("total_return_pct"),
        "train_trade_count": train_result.get("trade_count"),
        "validation_ok": validation_result.get("ok") is True,
        "validation_return_pct": validation_result.get("total_return_pct"),
        "validation_excess_return_pct": round(
            validation_return - benchmark_return, 4
        ),
        "validation_trade_count": validation_result.get("trade_count"),
        "validation_max_drawdown_pct": validation_result.get("max_drawdown_pct"),
        "validation_sharpe": validation_result.get("sharpe"),
        "validation_buy_hold_return_pct": benchmark_result.get("total_return_pct"),
        "validation_buy_hold_max_drawdown_pct": benchmark_result.get(
            "max_drawdown_pct"
        ),
        "validation_buy_hold_sharpe": benchmark_result.get("sharpe"),
        "validation_drawdown_improvement_pct": round(
            benchmark_drawdown - validation_drawdown, 4
        ),
        "validation_sharpe_excess": round(
            validation_sharpe - benchmark_sharpe, 4
        ),
        "validation_return_drawdown_efficiency": round(
            validation_efficiency, 6
        ),
        "validation_buy_hold_return_drawdown_efficiency": round(
            benchmark_efficiency, 6
        ),
        "validation_risk_efficiency_excess": round(
            validation_efficiency - benchmark_efficiency, 6
        ),
        "cost_sensitivity_status": cost_sensitivity.get("status", "BLOCK"),
        "cost_sensitivity": cost_sensitivity,
        "lookahead_status": lookahead.get("status", "BLOCK"),
        "lookahead_issues": list(lookahead.get("issues") or []),
    }

    integrity_blockers: list[str] = []
    if manifest.get("status") != "PASS":
        integrity_blockers.append("selection_replay_dataset_integrity_blocked")
    for role, replay in (
        ("train", train_run),
        ("validation", validation_run),
        ("benchmark", benchmark_run),
    ):
        integrity_blockers.extend(
            _result_integrity_issues(role, replay["result_projection"])
        )
    for replay in cost_runs:
        integrity_blockers.extend(
            _result_integrity_issues(
                f"cost_{replay.get('name') or 'unknown'}",
                replay["result_projection"],
            )
        )
    if cost_sensitivity.get("verification_status") != "PASS":
        integrity_blockers.append("selection_replay_cost_evidence_integrity_blocked")
    if prefix_invariance.get("status") not in {"PASS", "BLOCK"}:
        integrity_blockers.append("selection_replay_prefix_status_invalid")
    if lookahead.get("status") not in {"PASS", "WATCH", "BLOCK"}:
        integrity_blockers.append("selection_replay_lookahead_status_invalid")

    outcome_blockers: list[str] = []
    for role, replay in (
        ("train", train_run),
        ("validation", validation_run),
        ("benchmark", benchmark_run),
    ):
        if replay["result_projection"].get("ok") is not True:
            outcome_blockers.append(f"selection_replay_{role}_not_runnable")
    for replay in cost_runs:
        if replay["result_projection"].get("ok") is not True:
            outcome_blockers.append(
                f"selection_replay_cost_{replay.get('name') or 'unknown'}_not_runnable"
            )
    if cost_sensitivity.get("status") != "PASS":
        outcome_blockers.extend(
            str(item) for item in cost_sensitivity.get("blockers") or []
        )
    if prefix_invariance.get("status") != "PASS":
        outcome_blockers.append("selection_replay_prefix_invariance_blocked")
    if lookahead.get("status") != "PASS":
        outcome_blockers.append("selection_replay_lookahead_blocked")

    all_blockers = list(dict.fromkeys([*integrity_blockers, *outcome_blockers]))
    content = {
        "schema_version": STRATEGY_SELECTION_REPLAY_SCHEMA_VERSION,
        "verification_status": "PASS" if not integrity_blockers else "BLOCK",
        "status": "PASS" if not all_blockers else "BLOCK",
        "input_identity": input_identity,
        "train_run": train_run,
        "validation_run": validation_run,
        "benchmark_run": benchmark_run,
        "cost_runs": cost_runs,
        "cost_sensitivity": cost_sensitivity,
        "prefix_invariance": prefix_invariance,
        "lookahead": lookahead,
        "flat_metric_projection": flat_metric_projection,
        "integrity_blockers": list(dict.fromkeys(integrity_blockers)),
        "outcome_blockers": list(dict.fromkeys(outcome_blockers)),
        "blockers": all_blockers,
        "evaluation_mode": "CAUSAL_SELECTION_AND_COST_REPLAY",
        "historical_backtest_only": True,
        "profitability_proven": False,
        "parameter_selection_authority": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "evidence_hash": canonical_hash(content)}


__all__ = [
    "DEVELOPMENT_SELECTION_SPLIT_POLICY",
    "DEVELOPMENT_SELECTION_SPLIT_SCHEMA_VERSION",
    "STRATEGY_SELECTION_REPLAY_INPUT_SCHEMA_VERSION",
    "STRATEGY_SELECTION_REPLAY_SCHEMA_VERSION",
    "build_development_selection_prefix_schedule",
    "build_strategy_selection_replay_evidence",
]
