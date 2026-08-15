from __future__ import annotations

import json
import math
from typing import Any

from .backtest_engine import (
    EXECUTION_MODEL_VERSION,
    causal_prefix_invariance_check,
    prepare_backtest_dataset,
    run_causal_long_only_backtest,
)
from .research_symbol_market import (
    RESEARCH_SYMBOL_MARKET_CLASSIFIER_VERSION,
    research_market_for_symbol,
)
from .strategy_benchmark import (
    align_completed_daily_payloads,
    build_calendar_split_schedule,
    buy_and_hold_report,
)
from .strategy_chronological_slice import (
    build_fixed_chronological_slice_evidence_v2,
)
from .strategy_cost_stress import (
    FROZEN_TEST_COST_STRESS_STAGE,
    build_strategy_cost_stress_contract,
    build_strategy_cost_stress_evidence,
    project_cost_stress_observation,
)
from .strategy_fold_replay import (
    canonical_hash,
    stable_causal_backtest_result_projection,
)
from .strategy_quality import strategy_lookahead_check
from .strategy_signals import (
    SIGNAL_ENGINE_VERSION,
    build_strategy_signal_fn,
    strategy_signal_input,
    strategy_startup_candles_for_params,
    strategy_validation_capability,
)


FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION = 11
STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION = (
    "strategy-frozen-evaluation-replay-v1"
)
STRATEGY_FROZEN_EVALUATION_INPUT_SCHEMA_VERSION = (
    "strategy-frozen-evaluation-input-v1"
)
STRATEGY_FROZEN_EVALUATION_RUN_INPUT_SCHEMA_VERSION = (
    "strategy-frozen-evaluation-run-input-v1"
)
STRATEGY_FROZEN_EVALUATION_BENCHMARK_INPUT_SCHEMA_VERSION = (
    "strategy-frozen-evaluation-benchmark-input-v1"
)
STRATEGY_FROZEN_EVALUATION_LOOKAHEAD_SCHEMA_VERSION = (
    "strategy-frozen-evaluation-lookahead-v1"
)
STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION_V2 = (
    "strategy-research-test-cell-evidence-v2"
)
STRATEGY_RESEARCH_HOLDOUT_CELL_EVIDENCE_SCHEMA_VERSION_V1 = (
    "strategy-research-holdout-cell-evidence-v1"
)

FROZEN_TEST_ROLE = "FROZEN_TEST_ONCE"
HOLDOUT_CONFIRMATION_ROLE = "HOLDOUT_CONFIRMATION"
SUPPORTED_FROZEN_EVALUATION_ROLES = frozenset({
    FROZEN_TEST_ROLE,
    HOLDOUT_CONFIRMATION_ROLE,
})


def rebuild_strategy_frozen_confirmation_context(
    *,
    datasets: dict[str, dict[str, Any]] | Any,
    expected_symbols: set[str],
    manifests: list[dict[str, Any]] | Any,
    split_policy: dict[str, Any] | Any,
    data_policy: dict[str, Any] | Any,
    required_start: str,
    required_as_of: str,
    reported_alignment: dict[str, Any] | Any = None,
    reported_schedule: dict[str, Any] | Any = None,
) -> dict[str, Any]:
    """Rebuild confirmation alignment and schedule from frozen snapshot rows."""

    blockers: list[str] = []
    if not isinstance(datasets, dict) or not all(
        isinstance(item, dict) for item in datasets.values()
    ):
        datasets = {}
        blockers.append("holdout_confirmation_datasets_invalid")
    normalized_expected = {
        str(symbol or "").strip().upper() for symbol in expected_symbols
    }
    normalized_datasets = {
        str(symbol or "").strip().upper(): dict(dataset)
        for symbol, dataset in datasets.items()
        if str(symbol or "").strip()
    }
    if set(normalized_datasets) != normalized_expected:
        blockers.append("holdout_confirmation_dataset_role_coverage_mismatch")
    raw_payloads: dict[str, dict[str, Any]] = {}
    for symbol, dataset in normalized_datasets.items():
        rows = dataset.get("rows")
        source = str(dataset.get("source") or "")
        try:
            expected_market = research_market_for_symbol(symbol)
        except ValueError:
            expected_market = ""
        if (
            dataset.get("role") != "CONFIRMATION"
            or dataset.get("timeframe") != "1D"
            or dataset.get("market") != expected_market
            or not source
            or not isinstance(rows, list)
            or not all(isinstance(row, dict) for row in rows)
        ):
            blockers.append(f"holdout_confirmation_dataset_invalid:{symbol}")
            continue
        raw_payloads[symbol] = {
            "source": source,
            "rows": [dict(row) for row in rows],
        }

    manifest_rows = (
        [dict(item) for item in manifests]
        if isinstance(manifests, list)
        and all(isinstance(item, dict) for item in manifests)
        else []
    )
    manifest_by_symbol = {
        str(item.get("symbol") or "").strip().upper(): item
        for item in manifest_rows
        if item.get("role") == "CONFIRMATION"
        and str(item.get("symbol") or "").strip()
    }
    if set(manifest_by_symbol) != normalized_expected or len(
        manifest_by_symbol
    ) != len(manifest_rows):
        blockers.append("holdout_confirmation_manifest_coverage_mismatch")
    for symbol, manifest in manifest_by_symbol.items():
        dataset = normalized_datasets.get(symbol, {})
        if str(manifest.get("source") or "") != str(
            dataset.get("source") or ""
        ):
            blockers.append(f"holdout_confirmation_manifest_source_mismatch:{symbol}")
        if manifest.get("status") != "PASS":
            blockers.extend(
                f"{symbol}:confirmation_manifest:{item}"
                for item in manifest.get("blockers") or ["status_not_pass"]
            )

    safe_data_policy = _canonical_mapping(data_policy)
    safe_split_policy = _canonical_mapping(split_policy)
    try:
        aligned_payloads, alignment = align_completed_daily_payloads(
            raw_payloads,
            max_endpoint_skew_days=safe_data_policy.get(
                "max_endpoint_skew_days"
            ),
            max_boundary_skew_days=safe_data_policy.get(
                "max_boundary_skew_days"
            ),
            required_start=str(required_start or ""),
            required_as_of=str(required_as_of or ""),
        )
    except (TypeError, ValueError, KeyError, OverflowError):
        aligned_payloads = {}
        alignment = {
            "status": "BLOCK",
            "blockers": ["holdout_alignment_rebuild_failed"],
        }
    if alignment.get("status") != "PASS":
        blockers.extend(
            str(item)
            for item in alignment.get("blockers")
            or ["holdout_alignment_rebuild_blocked"]
        )
    else:
        for symbol in sorted(set(raw_payloads) & set(aligned_payloads)):
            if list(aligned_payloads[symbol].get("rows") or []) != list(
                raw_payloads[symbol].get("rows") or []
            ):
                blockers.append(f"holdout_aligned_rows_mismatch:{symbol}")
    try:
        schedule = build_calendar_split_schedule(
            aligned_payloads,
            train_ratio=safe_split_policy.get("train_ratio"),
            validation_ratio=safe_split_policy.get("validation_ratio"),
            minimum_segment_rows=safe_split_policy.get(
                "minimum_segment_rows"
            ),
        )
    except (TypeError, ValueError, KeyError, OverflowError):
        schedule = {
            "status": "BLOCK",
            "symbol_boundaries": {},
            "blockers": ["holdout_calendar_split_rebuild_failed"],
        }
    if schedule.get("status") != "PASS":
        blockers.extend(
            str(item)
            for item in schedule.get("blockers")
            or ["holdout_calendar_split_rebuild_blocked"]
        )
    if reported_alignment is not None and (
        not isinstance(reported_alignment, dict)
        or reported_alignment != alignment
    ):
        blockers.append("holdout_alignment_semantic_mismatch")
    if reported_schedule is not None and (
        not isinstance(reported_schedule, dict)
        or reported_schedule != schedule
    ):
        blockers.append("holdout_calendar_schedule_semantic_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "payloads": aligned_payloads if not blockers else {},
        "alignment": alignment,
        "schedule": schedule,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _canonical_mapping(value: dict[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("strategy_frozen_evaluation_mapping_invalid")
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
        "duplicate_trading_date_count": source.get(
            "duplicate_trading_date_count"
        ),
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


def _stable_prefix_projection(payload: dict[str, Any] | Any) -> dict[str, Any]:
    source = _canonical_mapping(payload) if isinstance(payload, dict) else {}
    content = {
        "version": str(source.get("version") or ""),
        "status": str(source.get("status") or "BLOCK"),
        "checkpoint_count": source.get("checkpoint_count"),
        "checks": source.get("checks")
        if isinstance(source.get("checks"), list)
        else [],
        "issues": source.get("issues")
        if isinstance(source.get("issues"), list)
        else [],
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
        "schema_version": STRATEGY_FROZEN_EVALUATION_LOOKAHEAD_SCHEMA_VERSION,
        "status": str(source.get("status") or "BLOCK"),
        "score": source.get("score"),
        "issues": list(source.get("issues") or []),
        "checks": _canonical_mapping({"rows": source.get("checks") or []})[
            "rows"
        ],
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
            issues.append(f"frozen_evaluation_{role}_{field}_invalid")
    if (
        _finite(result.get("max_drawdown_pct")) is not None
        and float(result["max_drawdown_pct"]) < 0
    ):
        issues.append(f"frozen_evaluation_{role}_drawdown_negative")
    if _native_nonnegative_int(result.get("trade_count")) is None:
        issues.append(f"frozen_evaluation_{role}_trade_count_invalid")
    if _native_nonnegative_int(result.get("order_event_count")) is None:
        issues.append(f"frozen_evaluation_{role}_order_event_count_invalid")
    if result.get("execution_model") != EXECUTION_MODEL_VERSION:
        issues.append(f"frozen_evaluation_{role}_execution_model_mismatch")
    if (
        result.get("research_only") is not True
        or result.get("paper_authorized") is not False
        or result.get("live_order_allowed") is not False
    ):
        issues.append(f"frozen_evaluation_{role}_execution_authority_invalid")
    return issues


def _run_strategy(
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
        "schema_version": STRATEGY_FROZEN_EVALUATION_RUN_INPUT_SCHEMA_VERSION,
        "run_role": run_role,
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


def _run_benchmark(
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
        "schema_version": (
            STRATEGY_FROZEN_EVALUATION_BENCHMARK_INPUT_SCHEMA_VERSION
        ),
        "run_role": "FROZEN_EVALUATION_BUY_AND_HOLD",
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


def _temporal_projection(
    validation_result: dict[str, Any],
    test_result: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    for name, result in (("validation", validation_result), ("test", test_result)):
        if result.get("ok") is not True:
            blockers.append(f"{name}_segment_backtest_failed")
        if _native_nonnegative_int(result.get("trade_count")) is None:
            blockers.append(f"{name}_segment_trade_count_invalid")
        elif int(result["trade_count"]) < 2:
            blockers.append(f"{name}_segment_has_fewer_than_2_closed_trades")
        value = _finite(result.get("total_return_pct"))
        if value is None or value <= 0:
            blockers.append(f"{name}_segment_return_not_positive")
        drawdown = _finite(result.get("max_drawdown_pct"))
        if drawdown is None or drawdown < 0 or drawdown >= 25:
            blockers.append(f"{name}_segment_drawdown_invalid_or_exceeds_25pct")
    content = {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "temporal_hash": canonical_hash(content)}


def build_strategy_frozen_evaluation_replay_evidence(
    *,
    role: str,
    rows: list[dict[str, Any]] | Any,
    train_end_index: int,
    validation_end_index: int,
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
    """Replay schema-11 TEST/holdout evidence from frozen causal inputs."""

    clean_role = str(role or "").strip().upper()
    if clean_role not in SUPPORTED_FROZEN_EVALUATION_ROLES:
        raise ValueError("strategy_frozen_evaluation_role_invalid")
    if (
        not isinstance(rows, list)
        or not rows
        or not all(isinstance(item, dict) for item in rows)
    ):
        raise ValueError("strategy_frozen_evaluation_rows_invalid")
    clean_symbol = str(symbol or "").strip().upper()
    clean_source = str(source or "").strip()
    clean_market = str(market or "").strip().lower()
    clean_timeframe = str(timeframe or "").strip().upper()
    if not clean_symbol or not clean_source:
        raise ValueError("strategy_frozen_evaluation_dataset_identity_invalid")
    if clean_market != research_market_for_symbol(clean_symbol):
        raise ValueError("strategy_frozen_evaluation_market_identity_mismatch")
    if clean_timeframe != "1D":
        raise ValueError("strategy_frozen_evaluation_timeframe_not_daily")
    clean_strategy_id = str(strategy_id or "").strip().lower()
    clean_variant_id = str(variant_id or "").strip()
    clean_implementation_fingerprint = str(
        implementation_fingerprint or ""
    ).strip()
    if not clean_variant_id or not clean_implementation_fingerprint:
        raise ValueError("strategy_frozen_evaluation_variant_identity_invalid")
    if strategy_validation_capability(clean_strategy_id).get(
        "backtest_supported"
    ) is not True:
        raise ValueError("strategy_frozen_evaluation_strategy_unsupported")
    frozen_params = _canonical_mapping(params)
    if not param_hash or str(param_hash) != canonical_hash(frozen_params):
        raise ValueError("strategy_frozen_evaluation_param_hash_mismatch")
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
            raise ValueError(f"strategy_frozen_evaluation_risk_invalid:{field}")
    if abs(float(frozen_risk["leverage"]) - 1.0) > 1e-9:
        raise ValueError("strategy_frozen_evaluation_leverage_not_supported")

    train_end = _native_nonnegative_int(train_end_index)
    validation_end = _native_nonnegative_int(validation_end_index)
    if (
        train_end is None
        or validation_end is None
        or train_end < 1
        or train_end >= validation_end
        or validation_end >= len(rows)
    ):
        raise ValueError("strategy_frozen_evaluation_boundary_invalid")

    startup = strategy_startup_candles_for_params(
        clean_strategy_id, frozen_params
    )
    prepared = prepare_backtest_dataset(
        [dict(item) for item in rows],
        symbol=clean_symbol,
        source=clean_source,
        timeframe=clean_timeframe,
        minimum_rows=startup + 2,
        market=clean_market,
    )
    manifest = prepared["manifest"]
    clean_rows = [dict(item) for item in prepared.get("rows") or []]
    if len(clean_rows) != len(rows):
        raise ValueError("strategy_frozen_evaluation_dataset_row_drift")
    if (
        manifest.get("input_row_count") != len(rows)
        or manifest.get("row_count") != len(rows)
        or manifest.get("excluded_incomplete_count") != 0
        or manifest.get("invalid_row_count") != 0
        or manifest.get("duplicate_count") != 0
        or manifest.get("duplicate_trading_date_count") != 0
        or manifest.get("ordered") is not True
    ):
        raise ValueError("strategy_frozen_evaluation_dataset_not_canonical")

    cost_contract = build_strategy_cost_stress_contract(frozen_risk)
    input_content = {
        "schema_version": STRATEGY_FROZEN_EVALUATION_INPUT_SCHEMA_VERSION,
        "role": clean_role,
        "dataset_identity": _dataset_identity(manifest),
        "train_end_index": train_end,
        "validation_end_index": validation_end,
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
        "initial_cash": 10_000.0,
    }
    input_identity = {**input_content, "input_hash": canonical_hash(input_content)}

    configured_run = _run_strategy(
        rows=clean_rows,
        symbol=clean_symbol,
        source=f"{clean_source}:frozen_evaluation_configured",
        market=clean_market,
        timeframe=clean_timeframe,
        run_role=f"{clean_role}_CONFIGURED",
        strategy_id=clean_strategy_id,
        params=frozen_params,
        param_hash=str(param_hash),
        risk=frozen_risk,
        startup_candles=startup,
        evaluation_start_index=validation_end,
        fee_rate=float(frozen_risk["fee_rate"]),
        slippage_bps=float(frozen_risk["slippage_bps"]),
    )
    benchmark_run = _run_benchmark(
        rows=clean_rows,
        symbol=clean_symbol,
        source=f"{clean_source}:frozen_evaluation_buy_hold",
        market=clean_market,
        timeframe=clean_timeframe,
        risk=frozen_risk,
        evaluation_start_index=validation_end,
    )
    severe_contract = dict(cost_contract["frozen_test_scenarios"][0])
    severe_run = _run_strategy(
        rows=clean_rows,
        symbol=clean_symbol,
        source=f"{clean_source}:frozen_evaluation_severe_cost",
        market=clean_market,
        timeframe=clean_timeframe,
        run_role=f"{clean_role}_SEVERE_COST",
        strategy_id=clean_strategy_id,
        params=frozen_params,
        param_hash=str(param_hash),
        risk=frozen_risk,
        startup_candles=startup,
        evaluation_start_index=validation_end,
        fee_rate=float(severe_contract["fee_rate"]),
        slippage_bps=float(severe_contract["slippage_bps"]),
    )
    configured_result = configured_run["result_projection"]
    benchmark_result = benchmark_run["result_projection"]
    severe_result = severe_run["result_projection"]
    cost_evidence = build_strategy_cost_stress_evidence(
        stage=FROZEN_TEST_COST_STRESS_STAGE,
        risk=frozen_risk,
        baseline=project_cost_stress_observation(
            "configured", configured_result
        ),
        scenarios=[project_cost_stress_observation("severe", severe_result)],
    )

    configured_return = _number_or_zero(
        configured_result.get("total_return_pct")
    )
    benchmark_return = _number_or_zero(
        benchmark_result.get("total_return_pct")
    )
    configured_drawdown = _number_or_zero(
        configured_result.get("max_drawdown_pct")
    )
    benchmark_drawdown = _number_or_zero(
        benchmark_result.get("max_drawdown_pct")
    )
    configured_sharpe = _number_or_zero(configured_result.get("sharpe"))
    benchmark_sharpe = _number_or_zero(benchmark_result.get("sharpe"))
    configured_efficiency = configured_return / max(configured_drawdown, 1.0)
    benchmark_efficiency = benchmark_return / max(benchmark_drawdown, 1.0)

    validation_run: dict[str, Any] | None = None
    temporal: dict[str, Any] | None = None
    fixed_slice: dict[str, Any] | None = None
    prefix_invariance: dict[str, Any] | None = None
    lookahead: dict[str, Any] | None = None
    if clean_role == HOLDOUT_CONFIRMATION_ROLE:
        validation_run = _run_strategy(
            rows=clean_rows[:validation_end],
            symbol=clean_symbol,
            source=f"{clean_source}:holdout_validation",
            market=clean_market,
            timeframe=clean_timeframe,
            run_role="HOLDOUT_VALIDATION_CONFIGURED",
            strategy_id=clean_strategy_id,
            params=frozen_params,
            param_hash=str(param_hash),
            risk=frozen_risk,
            startup_candles=startup,
            evaluation_start_index=train_end,
            fee_rate=float(frozen_risk["fee_rate"]),
            slippage_bps=float(frozen_risk["slippage_bps"]),
        )
        temporal = _temporal_projection(
            validation_run["result_projection"], configured_result
        )
        fixed_slice = build_fixed_chronological_slice_evidence_v2(
            selection_rows=clean_rows,
            symbol=clean_symbol,
            source=f"{clean_source}:holdout_fixed_slices",
            market=clean_market,
            timeframe=clean_timeframe,
            strategy_id=clean_strategy_id,
            params=frozen_params,
            param_hash=str(param_hash),
            risk=frozen_risk,
        )
        prefix_raw = causal_prefix_invariance_check(
            rows=clean_rows,
            symbol=clean_symbol,
            source=f"{clean_source}:holdout_causal_audit",
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
            prefix_invariance_hash=str(
                prefix_invariance.get("audit_hash") or ""
            ),
        )

    common_flat = {
        "dataset_status": manifest.get("status", "BLOCK"),
        "dataset_hash": manifest.get("data_hash", ""),
        "test_ok": configured_result.get("ok") is True,
        "test_return_pct": configured_result.get("total_return_pct"),
        "test_excess_return_pct": round(
            configured_return - benchmark_return, 4
        ),
        "test_trade_count": configured_result.get("trade_count"),
        "test_max_drawdown_pct": configured_result.get("max_drawdown_pct"),
        "test_sharpe": configured_result.get("sharpe"),
        "test_drawdown_improvement_pct": round(
            benchmark_drawdown - configured_drawdown, 4
        ),
        "test_sharpe_excess": round(
            configured_sharpe - benchmark_sharpe, 4
        ),
        "test_return_drawdown_efficiency": round(
            configured_efficiency, 6
        ),
        "test_risk_efficiency_excess": round(
            configured_efficiency - benchmark_efficiency, 6
        ),
    }
    if clean_role == FROZEN_TEST_ROLE:
        flat_metric_projection = {
            **common_flat,
            "test_start_index": validation_end,
            "test_start": str(clean_rows[validation_end].get("date") or ""),
            "test_end": str(clean_rows[-1].get("date") or ""),
            "test_buy_hold_return_pct": benchmark_result.get(
                "total_return_pct"
            ),
            "test_buy_hold_max_drawdown_pct": benchmark_result.get(
                "max_drawdown_pct"
            ),
            "test_buy_hold_sharpe": benchmark_result.get("sharpe"),
            "test_buy_hold_return_drawdown_efficiency": round(
                benchmark_efficiency, 6
            ),
            "test_severe_cost_return_pct": severe_result.get(
                "total_return_pct"
            ),
            "test_cost_status": cost_evidence.get("status", "BLOCK"),
        }
    else:
        validation_result = (
            validation_run["result_projection"] if validation_run else {}
        )
        flat_metric_projection = {
            **common_flat,
            "source": clean_source,
            "dataset_rows": manifest.get("row_count", 0),
            "dataset_blockers": list(manifest.get("blockers") or []),
            "baseline_ok": configured_result.get("ok") is True,
            "baseline_return_pct": configured_result.get("total_return_pct"),
            "baseline_max_drawdown_pct": configured_result.get(
                "max_drawdown_pct"
            ),
            "baseline_trade_count": configured_result.get("trade_count"),
            "baseline_sharpe": configured_result.get("sharpe"),
            "validation_return_pct": validation_result.get(
                "total_return_pct"
            ),
            "validation_trade_count": validation_result.get("trade_count"),
            "buy_hold_test_return_pct": benchmark_result.get(
                "total_return_pct"
            ),
            "buy_hold_test_max_drawdown_pct": benchmark_result.get(
                "max_drawdown_pct"
            ),
            "buy_hold_test_sharpe": benchmark_result.get("sharpe"),
            "buy_hold_test_return_drawdown_efficiency": round(
                benchmark_efficiency, 6
            ),
            "cost_sensitivity_status": cost_evidence.get("status", "BLOCK"),
            "cost_sensitivity_blockers": list(
                cost_evidence.get("blockers") or []
            ),
            "temporal_status": (temporal or {}).get("status", "BLOCK"),
            "temporal_blockers": list((temporal or {}).get("blockers") or []),
            "walk_forward_status": (fixed_slice or {}).get(
                "status", "BLOCK"
            ),
            "lookahead_status": (lookahead or {}).get("status", "BLOCK"),
            "lookahead_issues": list((lookahead or {}).get("issues") or []),
        }

    integrity_blockers: list[str] = []
    if manifest.get("status") != "PASS":
        integrity_blockers.append("frozen_evaluation_dataset_integrity_blocked")
    runs = [
        ("configured", configured_run),
        ("benchmark", benchmark_run),
        ("severe", severe_run),
    ]
    if validation_run is not None:
        runs.append(("validation", validation_run))
    for name, replay in runs:
        integrity_blockers.extend(
            _result_integrity_issues(name, replay["result_projection"])
        )
    if cost_evidence.get("verification_status") != "PASS":
        integrity_blockers.append(
            "frozen_evaluation_cost_evidence_integrity_blocked"
        )
    if fixed_slice is not None and fixed_slice.get("verification_status") != "PASS":
        integrity_blockers.append(
            "frozen_evaluation_fixed_slice_integrity_blocked"
        )

    outcome_blockers: list[str] = []
    for name, replay in runs:
        if replay["result_projection"].get("ok") is not True:
            outcome_blockers.append(f"frozen_evaluation_{name}_not_runnable")
    if cost_evidence.get("status") != "PASS":
        outcome_blockers.extend(
            str(item) for item in cost_evidence.get("blockers") or []
        )
    if temporal is not None and temporal.get("status") != "PASS":
        outcome_blockers.extend(
            f"temporal:{item}" for item in temporal.get("blockers") or []
        )
    if fixed_slice is not None and fixed_slice.get("status") != "PASS":
        outcome_blockers.append("frozen_evaluation_fixed_slice_blocked")
    if prefix_invariance is not None and prefix_invariance.get("status") != "PASS":
        outcome_blockers.append("frozen_evaluation_prefix_invariance_blocked")
    if lookahead is not None and lookahead.get("status") != "PASS":
        outcome_blockers.append("frozen_evaluation_lookahead_blocked")

    all_blockers = list(dict.fromkeys([*integrity_blockers, *outcome_blockers]))
    content = {
        "schema_version": STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION,
        "role": clean_role,
        "verification_status": "PASS" if not integrity_blockers else "BLOCK",
        "status": "PASS" if not all_blockers else "BLOCK",
        "input_identity": input_identity,
        "configured_run": configured_run,
        "benchmark_run": benchmark_run,
        "severe_cost_run": severe_run,
        "cost_stress_evidence": cost_evidence,
        "validation_run": validation_run,
        "temporal_evidence": temporal,
        "fixed_slice_evidence": fixed_slice,
        "fixed_slice_scope": (
            "FULL_FROZEN_CONFIRMATION_DATASET"
            if clean_role == HOLDOUT_CONFIRMATION_ROLE
            else None
        ),
        "prefix_invariance": prefix_invariance,
        "lookahead": lookahead,
        "flat_metric_projection": flat_metric_projection,
        "integrity_blockers": list(dict.fromkeys(integrity_blockers)),
        "outcome_blockers": list(dict.fromkeys(outcome_blockers)),
        "blockers": all_blockers,
        "evaluation_mode": "CAUSAL_FROZEN_POST_SELECTION_REPLAY",
        "historical_backtest_only": True,
        "profitability_proven": False,
        "parameter_selection_authority": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "evidence_hash": canonical_hash(content)}


__all__ = [
    "FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION",
    "FROZEN_TEST_ROLE",
    "HOLDOUT_CONFIRMATION_ROLE",
    "STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_HOLDOUT_CELL_EVIDENCE_SCHEMA_VERSION_V1",
    "STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION_V2",
    "build_strategy_frozen_evaluation_replay_evidence",
    "rebuild_strategy_frozen_confirmation_context",
]
