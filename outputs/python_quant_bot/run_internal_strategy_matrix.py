from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

from exchange_terminal import server
from exchange_terminal.application.market_data_envelope import consume_market_data_payloads
from exchange_terminal.market_data.candle_contract import candle_is_complete
from exchange_terminal.services.backtest_engine import EXECUTION_MODEL_VERSION, causal_prefix_invariance_check, prepare_backtest_dataset
from exchange_terminal.services.market_regime import (
    MARKET_REGIME_SCHEMA_VERSION,
    audit_market_regime_causality,
    summarize_market_regimes,
)
from exchange_terminal.services.portfolio_risk import PORTFOLIO_RISK_SCHEMA_VERSION, build_correlation_matrix
from exchange_terminal.services.strategy_benchmark import (
    BENCHMARK_SCHEMA_VERSION,
    aggregate_strategy_selection,
    align_completed_daily_payloads,
    build_calendar_split_schedule,
    buy_and_hold_report,
    confirmation_summary,
)
from exchange_terminal.services.strategy_quality import strategy_lookahead_check
from exchange_terminal.services.strategy_selection_alignment import (
    build_strategy_selection_alignment_input_snapshot,
)
from exchange_terminal.services.strategy_matrix_evidence import (
    MATRIX_REPORT_SCHEMA_VERSION,
    MATRIX_RESEARCH_GOVERNANCE_VERSION,
    strategy_matrix_result_hash,
    strategy_matrix_run_hash,
    verify_strategy_matrix_report,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION,
    StrategyMatrixRegistrationStore,
    audit_strategy_matrix_holdout_exposure,
    build_strategy_matrix_completion,
    canonical_hash as protocol_canonical_hash,
    verify_strategy_matrix_completion,
)
from exchange_terminal.services.prepared_research_result import (
    build_prepared_research_result,
    load_prepared_research_result,
    prepared_research_result_path,
    publish_json_no_clobber,
    publish_prepared_research_result_no_clobber,
    verify_prepared_research_result,
)
from exchange_terminal.services.strategy_risk_profiles import strategy_research_risk_profile
from exchange_terminal.services.strategy_signals import (
    assert_new_research_allowed,
    build_strategy_signal_fn,
    strategy_signal_input,
    validated_strategy_ids,
)
from exchange_terminal.services.trusted_clock import attest_utc_clock


DEFAULT_SELECTION_SYMBOLS = ["AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT"]
DEFAULT_CONFIRMATION_SYMBOLS = ["QQQ", "ETH-USDT"]
MATRIX_SPLIT_POLICY = {
    "schema_version": "calendar-split-v1",
    "train_ratio": 0.50,
    "validation_ratio": 0.25,
    "minimum_segment_rows": 120,
}
MATRIX_WORKFLOW = "STRATEGY_MATRIX"


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def unavailable_regime_evidence(*, status: str, blocker: str) -> dict[str, Any]:
    payload = {
        "schema_version": MARKET_REGIME_SCHEMA_VERSION,
        "status": status,
        "symbols": [],
        "blockers": [blocker],
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["evidence_hash"] = canonical_hash(payload)
    return payload


def unavailable_correlation_matrix(*, blocker: str) -> dict[str, Any]:
    payload = {
        "schema_version": PORTFOLIO_RISK_SCHEMA_VERSION,
        "status": "BLOCK",
        "symbols": [],
        "pairs": {},
        "blockers": [blocker],
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["matrix_hash"] = canonical_hash(payload)
    return payload


def completed_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(row) for row in rows
        if candle_is_complete(row, default_if_missing=False)
    ]


def run_cell(
    *,
    symbol: str,
    strategy_id: str,
    payload: dict[str, Any],
    risk: dict[str, float],
    limit: int,
    temporal_boundaries: dict[str, Any],
    strategy_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    source = str(payload.get("source") or "")
    rows = list(payload.get("rows") or [])
    clean_rows = completed_rows(rows)
    market = "stock" if server.is_stock_symbol(symbol) else "crypto"
    strategy = server.choose_strategy(strategy_id)
    strategy_params = dict(strategy_params) if isinstance(strategy_params, dict) else dict(strategy.get("params") or {})
    strategy = {**strategy, "params": strategy_params}
    manifest = prepare_backtest_dataset(
        clean_rows,
        symbol=symbol,
        source=source,
        timeframe="1D",
        minimum_rows=server.strategy_startup_candles(strategy_id, strategy_params) + 2,
        market=market,
    )["manifest"]
    baseline = server.run_strategy_backtest(
        strategy_id,
        risk["position_pct"],
        risk["take_profit_pct"],
        risk["stop_loss_pct"],
        1.0,
        limit,
        symbol,
        {"rows": rows, "source": source, "bar": "1D"},
        fee_rate=risk["fee_rate"],
        slippage_bps=risk["slippage_bps"],
        strategy_params=strategy_params,
    )
    temporal = server.strategy_temporal_validation_report(
        strategy_id=strategy_id,
        symbol=symbol,
        rows=rows,
        source=source,
        position_pct=risk["position_pct"],
        take_profit_pct=risk["take_profit_pct"],
        stop_loss_pct=risk["stop_loss_pct"],
        leverage=1.0,
        baseline=baseline,
        strategy_params=strategy_params,
        train_end_index=int(temporal_boundaries.get("train_end_index") or 0),
        validation_end_index=int(temporal_boundaries.get("validation_end_index") or 0),
    )
    test_start = int(temporal_boundaries.get("validation_end_index") or 0)
    benchmark = buy_and_hold_report(
        rows=clean_rows,
        symbol=symbol,
        source=f"{source}:buy_hold",
        position_pct=risk["position_pct"],
        startup_candles=80,
        fee_rate=risk["fee_rate"],
        slippage_bps=risk["slippage_bps"],
        market=market,
    )
    benchmark_test = buy_and_hold_report(
        rows=clean_rows,
        symbol=symbol,
        source=f"{source}:buy_hold_test",
        position_pct=risk["position_pct"],
        startup_candles=80,
        fee_rate=risk["fee_rate"],
        slippage_bps=risk["slippage_bps"],
        market=market,
        evaluation_start_index=test_start,
    )
    segment_reports = temporal.get("temporal_segments") or {}
    validation = segment_reports.get("validation") or {}
    test = segment_reports.get("test") or {}
    startup_candles = server.strategy_startup_candles(strategy_id, strategy_params)
    prefix_invariance = causal_prefix_invariance_check(
        rows=clean_rows,
        symbol=symbol,
        source=source,
        signal_factory=lambda _rows: build_strategy_signal_fn(strategy_id, strategy_params),
        position_pct=risk["position_pct"],
        take_profit_pct=risk["take_profit_pct"],
        stop_loss_pct=risk["stop_loss_pct"],
        startup_candles=startup_candles,
        fee_rate=risk["fee_rate"],
        slippage_bps=risk["slippage_bps"],
        leverage=1.0,
        market=market,
        timeframe="1D",
        signal_input=strategy_signal_input(strategy_id),
    )
    lookahead = strategy_lookahead_check(
        strategy,
        candle_count=len(clean_rows),
        startup_candles=startup_candles,
        rows=clean_rows,
        prefix_invariance=prefix_invariance,
    )
    test_return = float(test.get("total_return_pct") or 0.0)
    benchmark_test_return = float(benchmark_test.get("total_return_pct") or 0.0)
    test_drawdown = float(test.get("max_drawdown_pct") or 0.0)
    benchmark_test_drawdown = float(benchmark_test.get("max_drawdown_pct") or 0.0)
    test_sharpe = float(test.get("sharpe") or 0.0)
    benchmark_test_sharpe = float(benchmark_test.get("sharpe") or 0.0)
    test_efficiency = test_return / max(test_drawdown, 1.0)
    benchmark_test_efficiency = benchmark_test_return / max(benchmark_test_drawdown, 1.0)
    implementation_fingerprint = server.strategy_implementation_fingerprint(strategy_id, strategy_params)
    strategy_param_hash = canonical_hash(strategy_params)
    run_spec = {
        "symbol": symbol,
        "strategy_id": strategy_id,
        "strategy_params": strategy.get("params") or {},
        "risk": risk,
        "dataset_hash": manifest.get("data_hash"),
        "implementation_fingerprint": implementation_fingerprint,
        "strategy_param_hash": strategy_param_hash,
        "execution_model": EXECUTION_MODEL_VERSION,
    }
    return {
        "symbol": symbol,
        "strategy_id": strategy_id,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "source": source,
        "dataset_status": manifest.get("status", "BLOCK"),
        "dataset_hash": manifest.get("data_hash", ""),
        "dataset_rows": manifest.get("row_count", 0),
        "dataset_blockers": manifest.get("blockers") or [],
        "implementation_fingerprint": implementation_fingerprint,
        "strategy_params": strategy_params,
        "strategy_param_hash": strategy_param_hash,
        "run_hash": canonical_hash(run_spec),
        "baseline_ok": bool(baseline.get("ok")),
        "baseline_return_pct": baseline.get("total_return_pct"),
        "baseline_max_drawdown_pct": baseline.get("max_drawdown_pct"),
        "baseline_trade_count": baseline.get("trade_count"),
        "baseline_sharpe": baseline.get("sharpe"),
        "buy_hold_return_pct": benchmark.get("total_return_pct"),
        "validation_return_pct": validation.get("total_return_pct"),
        "validation_trade_count": validation.get("trade_count"),
        "test_return_pct": test.get("total_return_pct"),
        "test_ok": bool(test.get("ok")),
        "test_max_drawdown_pct": test.get("max_drawdown_pct"),
        "test_trade_count": test.get("trade_count"),
        "test_sharpe": test.get("sharpe"),
        "buy_hold_test_return_pct": benchmark_test.get("total_return_pct"),
        "buy_hold_test_max_drawdown_pct": benchmark_test.get("max_drawdown_pct"),
        "buy_hold_test_sharpe": benchmark_test.get("sharpe"),
        "test_excess_return_pct": round(test_return - benchmark_test_return, 4),
        "test_drawdown_improvement_pct": round(benchmark_test_drawdown - test_drawdown, 4),
        "test_sharpe_excess": round(test_sharpe - benchmark_test_sharpe, 4),
        "test_return_drawdown_efficiency": round(test_efficiency, 6),
        "buy_hold_test_return_drawdown_efficiency": round(benchmark_test_efficiency, 6),
        "test_risk_efficiency_excess": round(test_efficiency - benchmark_test_efficiency, 6),
        "temporal_status": temporal.get("temporal_status", "BLOCK"),
        "temporal_blockers": temporal.get("temporal_blockers") or [],
        "walk_forward_status": (temporal.get("walk_forward") or {}).get("status", "BLOCK"),
        "cost_sensitivity_status": (temporal.get("cost_sensitivity") or {}).get("status", "BLOCK"),
        "cost_sensitivity_blockers": (temporal.get("cost_sensitivity") or {}).get("blockers") or [],
        "lookahead_status": lookahead.get("status", "BLOCK"),
        "lookahead_issues": lookahead.get("issues") or [],
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def dataset_manifests(
    payloads: dict[str, dict[str, Any]],
    *,
    require_frozen_revision: bool = False,
) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for symbol, payload in payloads.items():
        market = "stock" if server.is_stock_symbol(symbol) else "crypto"
        manifest = prepare_backtest_dataset(
            list(payload.get("rows") or []),
            symbol=symbol,
            source=str(payload.get("source") or ""),
            timeframe="1D",
            minimum_rows=120,
            market=market,
        )["manifest"]
        revision_evidence = (
            dict(payload.get("data_revision_evidence") or {})
            if isinstance(payload.get("data_revision_evidence"), dict)
            else {}
        )
        market_history_evidence = (
            dict(payload.get("market_history_evidence") or {})
            if isinstance(payload.get("market_history_evidence"), dict)
            else {}
        )
        blockers = list(manifest.get("blockers") or [])
        status = str(manifest.get("status") or "BLOCK")
        if (
            require_frozen_revision
            and market == "stock"
            and revision_evidence.get("status") != "PASS"
        ):
            status = "BLOCK"
            blockers.append("frozen_stock_revision_evidence_not_passed")
        if (
            require_frozen_revision
            and market == "crypto"
            and market_history_evidence.get("status") != "PASS"
        ):
            status = "BLOCK"
            blockers.append("frozen_crypto_history_evidence_not_passed")
        manifests.append({
            "symbol": symbol,
            "source": payload.get("source", ""),
            "status": status,
            "row_count": manifest.get("row_count"),
            "first": manifest.get("first"),
            "last": manifest.get("last"),
            "data_hash": manifest.get("data_hash"),
            "data_revision_evidence": revision_evidence,
            "market_history_evidence": market_history_evidence,
            "blockers": list(dict.fromkeys(blockers)),
        })
    return manifests


def load_payloads(
    symbols: list[str],
    limit: int,
    *,
    required_start: str = "",
    required_as_of: str = "",
    dataset_lineage_prefix: str = "",
    require_frozen_revision: bool = False,
    manifest_role: str = "",
    manifest_timeframe: str = "",
    capture_alignment_input: bool = False,
    require_market_data_envelope: bool = False,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    raw_payloads = {
        symbol: server.backtest_market_rows(
            symbol,
            limit,
            f"{dataset_lineage_prefix}:{symbol}" if dataset_lineage_prefix else "",
        )
        for symbol in symbols
    }
    raw_payloads = consume_market_data_payloads(
        raw_payloads,
        expected_timeframe=manifest_timeframe or "1D",
        required=require_market_data_envelope,
        require_complete=require_market_data_envelope,
    )
    aligned, alignment = align_completed_daily_payloads(
        raw_payloads,
        max_endpoint_skew_days=3,
        max_boundary_skew_days=7,
        required_start=required_start,
        required_as_of=required_as_of,
    )
    if alignment["status"] == "PASS":
        for symbol, payload in aligned.items():
            if server.is_stock_symbol(symbol):
                continue
            previous = (
                dict(payload.get("market_history_evidence") or {})
                if isinstance(payload.get("market_history_evidence"), dict)
                else {}
            )
            payload["market_history_evidence"] = server.build_history_dataset_evidence(
                symbol=symbol,
                rows=list(payload.get("rows") or []),
                source=str(payload.get("source") or ""),
                dataset_lineage_id=(
                    f"{dataset_lineage_prefix}:{symbol}"
                    if dataset_lineage_prefix
                    else ""
                ),
                cache_manifest=dict(previous.get("cache_manifest") or {}),
                cache_admitted=previous.get("cache_admitted") is True,
            )
    manifests = dataset_manifests(
        aligned if alignment["status"] == "PASS" else raw_payloads,
        require_frozen_revision=require_frozen_revision,
    )
    if manifest_timeframe and manifest_timeframe != "1D":
        raise ValueError("strategy_matrix_manifest_timeframe_invalid")
    if manifest_role or manifest_timeframe:
        manifests = [{
            **item,
            **({"role": manifest_role} if manifest_role else {}),
            **({"timeframe": manifest_timeframe} if manifest_timeframe else {}),
        } for item in manifests]
    if alignment["status"] == "BLOCK":
        alignment_blockers = [f"batch_alignment:{item}" for item in alignment.get("blockers") or []]
        for manifest in manifests:
            manifest["status"] = "BLOCK"
            manifest["blockers"] = list(dict.fromkeys([*(manifest.get("blockers") or []), *alignment_blockers]))
    if capture_alignment_input:
        alignment["input_snapshot"] = (
            build_strategy_selection_alignment_input_snapshot(
                raw_payloads,
                manifests,
            )
        )
    return aligned, manifests, alignment


def build_regime_evidence(
    payloads: dict[str, dict[str, Any]],
    schedule: dict[str, Any],
) -> dict[str, Any]:
    symbols: list[dict[str, Any]] = []
    boundaries = schedule.get("symbol_boundaries") if isinstance(schedule.get("symbol_boundaries"), dict) else {}
    for symbol, payload in payloads.items():
        rows = completed_rows(list(payload.get("rows") or []))
        boundary = boundaries.get(symbol) if isinstance(boundaries.get(symbol), dict) else {}
        test_start = int(boundary.get("validation_end_index") or 0)
        market = "stock" if server.is_stock_symbol(symbol) else "crypto"
        audit = audit_market_regime_causality(rows, market=market)
        test_window = summarize_market_regimes(rows, start_index=test_start, market=market)
        status = "PASS" if audit.get("status") == "PASS" and test_window.get("status") == "PASS" else "BLOCK"
        symbols.append({
            "symbol": symbol,
            "market": market,
            "status": status,
            "causal_audit": audit,
            "test_window": test_window,
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        })
    blockers = [f"{item['symbol']}:regime_evidence_{str(item['status']).lower()}" for item in symbols if item["status"] != "PASS"]
    payload = {
        "schema_version": MARKET_REGIME_SCHEMA_VERSION,
        "status": "PASS" if symbols and not blockers else "BLOCK",
        "symbols": symbols,
        "blockers": blockers or ([] if symbols else ["no_regime_symbols"]),
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["evidence_hash"] = canonical_hash(payload)
    return payload


def build_matrix_batch_spec(
    *,
    selection_symbols: list[str],
    confirmation_symbols: list[str],
    strategies: list[str],
    position_pct: float,
    take_profit_pct: float,
    stop_loss_pct: float,
    fee_rate: float,
    slippage_bps: float,
    limit: int,
    max_confirmation_candidates: int,
) -> dict[str, Any]:
    normalized_selection = list(dict.fromkeys(
        str(symbol or "").strip().upper() for symbol in selection_symbols if str(symbol or "").strip()
    ))
    normalized_confirmation = list(dict.fromkeys(
        str(symbol or "").strip().upper() for symbol in confirmation_symbols if str(symbol or "").strip()
    ))
    normalized_strategies = list(dict.fromkeys(
        str(strategy or "").strip().lower() for strategy in strategies if str(strategy or "").strip()
    ))
    if not normalized_selection or not normalized_confirmation or not normalized_strategies:
        raise ValueError("selection symbols, confirmation symbols, and strategies are required")
    overlap = sorted(set(normalized_selection) & set(normalized_confirmation))
    if overlap:
        raise ValueError(f"selection and confirmation symbols overlap: {', '.join(overlap)}")
    validated = set(validated_strategy_ids())
    unsupported = [strategy for strategy in normalized_strategies if strategy not in validated]
    if unsupported:
        raise ValueError(f"unsupported benchmark strategies: {', '.join(unsupported)}")
    assert_new_research_allowed(normalized_strategies)
    numeric = {
        "position_pct": float(position_pct),
        "take_profit_pct": float(take_profit_pct),
        "stop_loss_pct": float(stop_loss_pct),
        "fee_rate": float(fee_rate),
        "slippage_bps": float(slippage_bps),
    }
    if not all(math.isfinite(value) for value in numeric.values()):
        raise ValueError("matrix risk parameters must be finite")
    if not 0 < numeric["position_pct"] <= 100:
        raise ValueError("position_pct must be in (0, 100]")
    if not 0 <= numeric["take_profit_pct"] <= 1_000:
        raise ValueError("take_profit_pct must be in [0, 1000]")
    if not 0 < numeric["stop_loss_pct"] <= 100:
        raise ValueError("stop_loss_pct must be in (0, 100]")
    if not 0 <= numeric["fee_rate"] <= 0.10:
        raise ValueError("fee_rate must be in [0, 0.10]")
    if not 0 <= numeric["slippage_bps"] <= 10_000:
        raise ValueError("slippage_bps must be in [0, 10000]")
    if isinstance(limit, bool) or int(limit) < 360:
        raise ValueError("limit must be at least 360 daily rows")
    if (
        isinstance(max_confirmation_candidates, bool)
        or not 1 <= int(max_confirmation_candidates) <= len(normalized_strategies)
    ):
        raise ValueError("max_confirmation_candidates must be within the strategy count")

    risk = {**numeric, "leverage": 1.0}
    strategy_specs: dict[str, dict[str, Any]] = {}
    for strategy_id in normalized_strategies:
        strategy_params = dict(server.choose_strategy(strategy_id).get("params") or {})
        risk_profile = strategy_research_risk_profile(strategy_id, risk)
        strategy_specs[strategy_id] = {
            "params": strategy_params,
            "implementation_fingerprint": server.strategy_implementation_fingerprint(
                strategy_id,
                strategy_params,
            ),
            "signal_input": strategy_signal_input(strategy_id),
            "risk_profile": risk_profile,
            "risk": dict(risk_profile["risk"]),
        }
    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "selection_symbols": normalized_selection,
        "confirmation_symbols": normalized_confirmation,
        "strategies": normalized_strategies,
        "strategy_specs": strategy_specs,
        "risk": risk,
        "limit": int(limit),
        "max_confirmation_candidates": int(max_confirmation_candidates),
        "selection_rule": "fixed_params_common_calendar_cross_symbol_oos_then_top_n_holdout",
        "optimizer_used": False,
        "split_policy": dict(MATRIX_SPLIT_POLICY),
        "data_policy": {
            "timeframe": "1D",
            "completed_candles_only": True,
            "alignment_schema_version": "daily-batch-alignment-v2",
            "max_endpoint_skew_days": 3,
            "max_boundary_skew_days": 7,
            "frozen_stock_revision_evidence_required": True,
            "frozen_crypto_history_evidence_required": True,
            "exact_dataset_snapshot_required": True,
        },
        "execution_model_version": EXECUTION_MODEL_VERSION,
        "market_regime_schema_version": MARKET_REGIME_SCHEMA_VERSION,
        "portfolio_risk_schema_version": PORTFOLIO_RISK_SCHEMA_VERSION,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_matrix_split_schedule(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return build_calendar_split_schedule(
        payloads,
        train_ratio=float(MATRIX_SPLIT_POLICY["train_ratio"]),
        validation_ratio=float(MATRIX_SPLIT_POLICY["validation_ratio"]),
        minimum_segment_rows=int(MATRIX_SPLIT_POLICY["minimum_segment_rows"]),
    )


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def build_matrix_dataset_snapshot(
    *,
    registration_id: str,
    batch_spec_hash: str,
    dataset_manifest: list[dict[str, Any]],
    selection_payloads: dict[str, dict[str, Any]],
    confirmation_payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    datasets: list[dict[str, Any]] = []
    for role, payloads in (
        ("SELECTION", selection_payloads),
        ("CONFIRMATION", confirmation_payloads),
    ):
        for symbol in sorted(payloads):
            payload = dict(payloads[symbol] or {})
            datasets.append({
                "role": role,
                "symbol": symbol,
                "market": "stock" if server.is_stock_symbol(symbol) else "crypto",
                "timeframe": "1D",
                "source": str(payload.get("source") or ""),
                "retrieval_source": str(payload.get("retrieval_source") or ""),
                "origin_sources": list(payload.get("origin_sources") or []),
                "adjustment_basis": str(payload.get("adjustment_basis") or ""),
                "corporate_action_coverage": str(payload.get("corporate_action_coverage") or ""),
                "data_revision_evidence": dict(payload.get("data_revision_evidence") or {}),
                "market_history_evidence": dict(payload.get("market_history_evidence") or {}),
                "rows": completed_rows(list(payload.get("rows") or [])),
            })
    snapshot = {
        "schema_version": "strategy-matrix-dataset-snapshot-v1",
        "registration_id": str(registration_id or ""),
        "batch_spec_hash": batch_spec_hash,
        "dataset_manifest": dataset_manifest,
        "dataset_manifest_hash": canonical_hash(dataset_manifest),
        "datasets": datasets,
        "dataset_count": len(datasets),
        "row_count": sum(len(item["rows"]) for item in datasets),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    snapshot["snapshot_hash"] = canonical_hash(snapshot)
    return snapshot


def _legacy_matrix_runner_protocol_ownership_blockers(
    protocol: dict[str, Any],
) -> list[str]:
    if protocol.get("schema_version") == STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION:
        return ["strategy_matrix_legacy_runner_protocol_v5_not_owned"]
    return []


def build_formal_strategy_matrix_report(
    payload: dict[str, Any],
    *,
    protocol: dict[str, Any],
    claim: dict[str, Any],
    completion: dict[str, Any],
) -> dict[str, Any]:
    ownership_blockers = _legacy_matrix_runner_protocol_ownership_blockers(protocol)
    if ownership_blockers:
        raise ValueError(ownership_blockers[0])
    report = dict(payload)
    holdout_exposure_audit = dict(claim.get("holdout_exposure_audit") or {})
    governance = {
        "schema_version": MATRIX_RESEARCH_GOVERNANCE_VERSION,
        "status": "PREREGISTERED_BLIND_SINGLE_USE_COMPLETE",
        "selection_test_policy": "BLIND_ONCE",
        "development_only": False,
        "single_use_claim": True,
        "registration_id": str(protocol.get("registration_id") or ""),
        "protocol_hash": str(protocol.get("protocol_hash") or ""),
        "claim_hash": str(claim.get("claim_hash") or ""),
        "completion_hash": str(completion.get("completion_hash") or ""),
        "registered_at_ms": int(protocol.get("registered_at_ms") or 0),
        "started_at_ms": int(claim.get("started_at_ms") or 0),
        "completed_at_ms": int(completion.get("completed_at_ms") or 0),
        "holdout_exposure_audit": holdout_exposure_audit,
        "protocol": dict(protocol),
        "single_use_claim_receipt": dict(claim),
        "completion_receipt": dict(completion),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    governance["governance_hash"] = canonical_hash(governance)
    report["research_governance"] = governance
    report["batch_run_hash"] = strategy_matrix_run_hash(report)
    return report


def _verify_formal_strategy_matrix_report(report: dict[str, Any]) -> dict[str, Any]:
    return verify_strategy_matrix_report(report)


def _formal_matrix_report_bytes(report: dict[str, Any]) -> bytes:
    return json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")


def _formal_matrix_output_conflict(output: Path, report: dict[str, Any]) -> dict[str, Any]:
    if not output.exists():
        return {"status": "PASS", "blockers": []}
    try:
        existing = output.read_bytes()
    except OSError:
        existing = b""
    expected = _formal_matrix_report_bytes(report)
    return {
        "status": "PASS" if existing == expected else "BLOCK",
        "blockers": [] if existing == expected else ["strategy_matrix_final_output_conflict"],
    }


def _prepared_matrix_verification(
    prepared: dict[str, Any],
    *,
    report_dir: Path,
    protocol: dict[str, Any],
    claim: dict[str, Any],
) -> dict[str, Any]:
    try:
        prepared_file = prepared_research_result_path(
            report_dir,
            protocol_hash=str(protocol.get("protocol_hash") or ""),
        ).name
    except ValueError:
        prepared_file = ""
    return verify_prepared_research_result(
        prepared,
        expected_workflow=MATRIX_WORKFLOW,
        expected_protocol=protocol,
        expected_claim=claim,
        report_verifier=_verify_formal_strategy_matrix_report,
        reserved_output_files={prepared_file},
    )


def finalize_formal_strategy_matrix_result(
    *,
    registration_store: StrategyMatrixRegistrationStore,
    registration_id: str,
    report_dir: Path,
    output: Path,
    protocol: dict[str, Any],
    claim: dict[str, Any],
    payload: dict[str, Any],
    completion_clock: dict[str, Any],
) -> dict[str, Any]:
    ownership_blockers = _legacy_matrix_runner_protocol_ownership_blockers(protocol)
    if ownership_blockers:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ownership_blockers,
            "required_runner": "NESTED_VARIANT_RESEARCH",
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    anticipated_completion = build_strategy_matrix_completion(
        protocol=protocol,
        claim=claim,
        result_hash=str(payload.get("matrix_result_hash") or ""),
        dataset_manifest_hash=str(payload.get("dataset_manifest_hash") or ""),
        clock_attestation=completion_clock,
    )
    completion_verification = verify_strategy_matrix_completion(
        anticipated_completion,
        protocol=protocol,
        claim=claim,
    )
    if completion_verification.get("status") != "PASS":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": [
                f"strategy_matrix_completion_preview:{item}"
                for item in completion_verification.get("blockers") or []
            ],
        }

    report = build_formal_strategy_matrix_report(
        payload,
        protocol=protocol,
        claim=claim,
        completion=anticipated_completion,
    )
    report_verification = _verify_formal_strategy_matrix_report(report)
    if report_verification.get("status") != "PASS":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": [
                f"strategy_matrix_precommit_report:{item}"
                for item in report_verification.get("blockers") or []
            ],
            "report_verification": report_verification,
        }
    prepared = build_prepared_research_result(
        workflow=MATRIX_WORKFLOW,
        registration_id=str(protocol.get("registration_id") or ""),
        protocol_hash=str(protocol.get("protocol_hash") or ""),
        claim_hash=str(claim.get("claim_hash") or ""),
        batch_spec_hash=str(report.get("batch_spec_hash") or ""),
        result_hash=str(report.get("matrix_result_hash") or ""),
        dataset_manifest_hash=str(report.get("dataset_manifest_hash") or ""),
        output_file=output.name,
        report=report,
    )
    prepared_verification = _prepared_matrix_verification(
        prepared,
        report_dir=report_dir,
        protocol=protocol,
        claim=claim,
    )
    if prepared_verification.get("status") != "PASS":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(prepared_verification.get("blockers") or []),
            "prepared_verification": prepared_verification,
        }
    conflict = _formal_matrix_output_conflict(output, report)
    if conflict.get("status") != "PASS":
        return {"ok": False, "status": "BLOCK", "blockers": conflict["blockers"]}
    prepared_publication = publish_prepared_research_result_no_clobber(
        report_dir,
        prepared,
    )
    if prepared_publication.get("status") not in {"PUBLISHED", "EXISTING_IDENTICAL"}:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(prepared_publication.get("blockers") or []),
            "prepared_publication": prepared_publication,
        }

    completion_result = registration_store.complete(
        registration_id,
        result_hash=str(report.get("matrix_result_hash") or ""),
        dataset_manifest_hash=str(report.get("dataset_manifest_hash") or ""),
        clock_attestation=completion_clock,
    )
    if not completion_result.get("ok") or completion_result.get("status") != "COMPLETED":
        return {
            "ok": False,
            "status": "PREPARED_RECOVERY_REQUIRED",
            "blockers": list(
                completion_result.get("blockers")
                or ["strategy_matrix_registry_completion_blocked"]
            ),
            "completion": completion_result,
            "prepared_publication": prepared_publication,
        }
    if dict(completion_result.get("completion") or {}) != anticipated_completion:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_matrix_completion_receipt_drift"],
            "completion": completion_result,
        }

    final_publication = publish_json_no_clobber(
        output,
        report,
        failure_blocker="strategy_matrix_final_atomic_publish_failed",
    )
    if final_publication.get("status") not in {"PUBLISHED", "EXISTING_IDENTICAL"}:
        return {
            "ok": False,
            "status": "FINAL_RECOVERY_REQUIRED",
            "blockers": list(final_publication.get("blockers") or []),
            "final_publication": final_publication,
        }
    return {
        "ok": True,
        "status": "COMPLETED",
        "report": report,
        "completion": anticipated_completion,
        "prepared_publication": prepared_publication,
        "final_publication": final_publication,
    }


def recover_formal_strategy_matrix_result(
    *,
    registration_store: StrategyMatrixRegistrationStore,
    registration: dict[str, Any],
    registration_id: str,
    report_dir: Path,
    requested_output: Path | None,
) -> dict[str, Any] | None:
    registry_status = str(registration.get("status") or "")
    if registry_status not in {"RUNNING", "COMPLETED"}:
        return None
    if server.RUNTIME_READ_ONLY:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_matrix_recovery_runtime_read_only"],
        }
    protocol = dict(registration.get("protocol") or {})
    claim = dict(registration.get("claim") or {})
    ownership_blockers = _legacy_matrix_runner_protocol_ownership_blockers(protocol)
    if ownership_blockers:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ownership_blockers,
            "required_runner": "NESTED_VARIANT_RESEARCH",
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if str(protocol.get("registration_id") or "") != str(registration_id or ""):
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_matrix_recovery_registration_mismatch"],
        }
    loaded = load_prepared_research_result(
        report_dir,
        protocol_hash=str(protocol.get("protocol_hash") or ""),
    )
    if loaded.get("status") != "LOADED":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(loaded.get("blockers") or []),
        }
    prepared = dict(loaded.get("prepared") or {})
    prepared_verification = _prepared_matrix_verification(
        prepared,
        report_dir=report_dir,
        protocol=protocol,
        claim=claim,
    )
    if prepared_verification.get("status") != "PASS":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(prepared_verification.get("blockers") or []),
            "prepared_verification": prepared_verification,
        }
    report = dict(prepared_verification.get("report") or {})
    completion = dict(prepared_verification.get("completion") or {})
    output_file = str(prepared_verification.get("output_file") or "")
    output = (report_dir / output_file).resolve()
    if output.parent != report_dir or output.name != output_file:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_matrix_recovery_output_parent_invalid"],
        }
    if requested_output is not None and requested_output.resolve() != output:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_matrix_recovery_output_binding_mismatch"],
        }
    conflict = _formal_matrix_output_conflict(output, report)
    if conflict.get("status") != "PASS":
        return {"ok": False, "status": "BLOCK", "blockers": conflict["blockers"]}

    if registry_status == "RUNNING":
        completion_result = registration_store.complete(
            registration_id,
            result_hash=str(prepared.get("result_hash") or ""),
            dataset_manifest_hash=str(prepared.get("dataset_manifest_hash") or ""),
            clock_attestation=dict(completion.get("clock_attestation") or {}),
        )
        if not completion_result.get("ok") or completion_result.get("status") != "COMPLETED":
            return {
                "ok": False,
                "status": "PREPARED_RECOVERY_REQUIRED",
                "blockers": list(
                    completion_result.get("blockers")
                    or ["strategy_matrix_registry_completion_blocked"]
                ),
                "completion": completion_result,
            }
        registry_completion = dict(completion_result.get("completion") or {})
    else:
        registry_completion = dict(registration.get("completion") or {})
    if registry_completion != completion:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_matrix_recovery_completion_receipt_mismatch"],
        }

    final_publication = publish_json_no_clobber(
        output,
        report,
        failure_blocker="strategy_matrix_final_atomic_publish_failed",
    )
    if final_publication.get("status") not in {"PUBLISHED", "EXISTING_IDENTICAL"}:
        return {
            "ok": False,
            "status": "FINAL_RECOVERY_REQUIRED",
            "blockers": list(final_publication.get("blockers") or []),
            "final_publication": final_publication,
        }
    return {
        "ok": True,
        "status": "RECOVERED",
        "report": report,
        "output": output,
        "completion": completion,
        "final_publication": final_publication,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a fixed, multi-strategy, paper-only benchmark matrix.")
    parser.add_argument("--selection-symbols", nargs="+", default=DEFAULT_SELECTION_SYMBOLS)
    parser.add_argument("--confirmation-symbols", nargs="+", default=DEFAULT_CONFIRMATION_SYMBOLS)
    parser.add_argument("--strategies", nargs="+", default=None)
    parser.add_argument("--position-pct", type=float, default=20.0)
    parser.add_argument("--take-profit-pct", type=float, default=8.0)
    parser.add_argument("--stop-loss-pct", type=float, default=4.0)
    parser.add_argument("--fee-rate", type=float, default=0.0005)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=780)
    parser.add_argument("--max-confirmation-candidates", type=int, default=2)
    parser.add_argument("--output", default="")
    parser.add_argument("--registration-id", default="")
    parser.add_argument("--registry", default="")
    args = parser.parse_args()

    formal_mode = bool(args.registration_id or args.registry)
    if formal_mode and not (args.registration_id and args.registry):
        raise SystemExit("--registration-id and --registry must be supplied together")
    if not formal_mode and not args.strategies:
        raise SystemExit("--strategies is required for a new development matrix run")
    runtime_dir = Path(server.RUNTIME_DIR).resolve()
    reports_dir = (runtime_dir / "reports").resolve()
    registry_path = Path(args.registry).resolve() if args.registry else Path()
    output = (
        Path(args.output).resolve()
        if args.output
        else reports_dir / f"strategy_matrix_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    )
    registration_store: StrategyMatrixRegistrationStore | None = None
    protocol: dict[str, Any] = {}
    claim: dict[str, Any] = {}
    if formal_mode:
        try:
            output.relative_to(reports_dir)
            registry_path.relative_to(runtime_dir)
        except ValueError as exc:
            raise SystemExit("formal matrix registry and output must remain inside the active runtime") from exc
        frozen_option_names = {
            "--selection-symbols",
            "--confirmation-symbols",
            "--strategies",
            "--position-pct",
            "--take-profit-pct",
            "--stop-loss-pct",
            "--fee-rate",
            "--slippage-bps",
            "--limit",
            "--max-confirmation-candidates",
        }
        supplied_frozen_options = sorted({
            argument.split("=", 1)[0]
            for argument in sys.argv[1:]
            if argument.split("=", 1)[0] in frozen_option_names
        })
        if supplied_frozen_options:
            raise SystemExit(
                "formal matrix parameters come only from the registered protocol; remove: "
                + ", ".join(supplied_frozen_options)
            )
        registration_store = StrategyMatrixRegistrationStore(
            db_path=registry_path,
            read_only=server.RUNTIME_READ_ONLY,
        )
        registration = registration_store.get(args.registration_id)
        if not registration.get("ok"):
            raise SystemExit(json.dumps({
                "error": "matrix_registration_not_claimable",
                "registration": registration,
            }, ensure_ascii=False))
        recovery = recover_formal_strategy_matrix_result(
            registration_store=registration_store,
            registration=registration,
            registration_id=args.registration_id,
            report_dir=reports_dir,
            requested_output=(Path(args.output).resolve() if args.output else None),
        )
        if recovery is not None:
            if not recovery.get("ok"):
                raise SystemExit(json.dumps({
                    "error": "matrix_prepared_result_recovery_blocked",
                    "recovery": recovery,
                }, ensure_ascii=False))
            recovered_report = dict(recovery.get("report") or {})
            print(json.dumps({
                **dict(recovered_report.get("summary") or {}),
                "batch_run_hash": str(recovered_report.get("batch_run_hash") or ""),
                "report": str(recovery.get("output") or ""),
                "recovered_from_prepared_result": True,
            }, ensure_ascii=False, indent=2))
            return 0
        if registration.get("status") != "REGISTERED":
            raise SystemExit(json.dumps({
                "error": "matrix_registration_not_claimable",
                "registration": registration,
            }, ensure_ascii=False))
        if output.exists():
            raise SystemExit(f"formal matrix output already exists: {output}")
        protocol = dict(registration.get("protocol") or {})
        ownership_blockers = _legacy_matrix_runner_protocol_ownership_blockers(protocol)
        if ownership_blockers:
            raise SystemExit(json.dumps({
                "error": "matrix_runner_protocol_not_owned",
                "status": "BLOCK",
                "blockers": ownership_blockers,
                "required_runner": "NESTED_VARIANT_RESEARCH",
                "data_loaded": False,
                "registration_claimed": False,
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }, ensure_ascii=False))
        frozen_spec = dict(protocol.get("batch_spec") or {})
        frozen_risk = dict(frozen_spec.get("risk") or {})
        build_arguments = {
            "selection_symbols": list(frozen_spec.get("selection_symbols") or []),
            "confirmation_symbols": list(frozen_spec.get("confirmation_symbols") or []),
            "strategies": list(frozen_spec.get("strategies") or []),
            "position_pct": frozen_risk.get("position_pct"),
            "take_profit_pct": frozen_risk.get("take_profit_pct"),
            "stop_loss_pct": frozen_risk.get("stop_loss_pct"),
            "fee_rate": frozen_risk.get("fee_rate"),
            "slippage_bps": frozen_risk.get("slippage_bps"),
            "limit": frozen_spec.get("limit"),
            "max_confirmation_candidates": frozen_spec.get("max_confirmation_candidates"),
        }
    else:
        build_arguments = {
            "selection_symbols": args.selection_symbols,
            "confirmation_symbols": args.confirmation_symbols,
            "strategies": args.strategies,
            "position_pct": args.position_pct,
            "take_profit_pct": args.take_profit_pct,
            "stop_loss_pct": args.stop_loss_pct,
            "fee_rate": args.fee_rate,
            "slippage_bps": args.slippage_bps,
            "limit": args.limit,
            "max_confirmation_candidates": args.max_confirmation_candidates,
        }
    try:
        batch_spec = build_matrix_batch_spec(**build_arguments)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    selection_symbols = list(batch_spec["selection_symbols"])
    confirmation_symbols = list(batch_spec["confirmation_symbols"])
    strategies = list(batch_spec["strategies"])
    strategy_specs = dict(batch_spec["strategy_specs"])
    matrix_limit = int(batch_spec["limit"])
    started_at_ms = time.time_ns() // 1_000_000
    if formal_mode:
        if (
            str(protocol.get("batch_spec_hash") or "") != canonical_hash(batch_spec)
            or protocol_canonical_hash(protocol.get("batch_spec") or {}) != protocol_canonical_hash(batch_spec)
        ):
            raise SystemExit("registered matrix batch does not match the requested run")
        claim_exposure = audit_strategy_matrix_holdout_exposure(
            reports_dir,
            runtime_dir,
            confirmation_symbols,
        )
        claim_result = registration_store.claim(
            args.registration_id,
            clock_attestation=attest_utc_clock(),
            exposure_audit=claim_exposure,
        )
        if not claim_result.get("ok") or claim_result.get("status") != "CLAIMED":
            raise SystemExit(json.dumps({
                "error": "matrix_registration_claim_blocked",
                "claim": claim_result,
            }, ensure_ascii=False))
        protocol = dict(claim_result.get("protocol") or {})
        claim = dict(claim_result.get("claim") or {})
        started_at_ms = int(claim.get("started_at_ms") or 0)

    lineage_prefix = (
        f"strategy-matrix:{args.registration_id}:{batch_spec['schema_version']}"
        if formal_mode
        else f"strategy-matrix-development:{started_at_ms}:{canonical_hash(batch_spec)[:12]}"
    )
    selection_payloads, selection_manifests, selection_alignment = load_payloads(
        selection_symbols,
        matrix_limit,
        dataset_lineage_prefix=f"{lineage_prefix}:selection",
        require_frozen_revision=True,
    )
    selection_schedule = build_matrix_split_schedule(selection_payloads)
    if selection_alignment["status"] == "PASS" and selection_schedule["status"] != "PASS":
        selection_alignment["status"] = "BLOCK"
        selection_alignment["blockers"] = list(dict.fromkeys([
            *(selection_alignment.get("blockers") or []),
            *[f"calendar_split:{item}" for item in selection_schedule.get("blockers") or []],
        ]))
        for manifest in selection_manifests:
            manifest["status"] = "BLOCK"
            manifest["blockers"] = list(dict.fromkeys([
                *(manifest.get("blockers") or []),
                *[f"calendar_split:{item}" for item in selection_schedule.get("blockers") or []],
            ]))
    selection_regime_evidence = (
        build_regime_evidence(selection_payloads, selection_schedule)
        if selection_alignment["status"] == "PASS" and selection_schedule["status"] == "PASS"
        else unavailable_regime_evidence(
            status="BLOCK",
            blocker="selection_alignment_or_schedule_blocked",
        )
    )
    selection_correlation_matrix = (
        build_correlation_matrix(selection_payloads)
        if selection_alignment["status"] == "PASS"
        else unavailable_correlation_matrix(blocker="selection_alignment_blocked")
    )
    selection_cells: list[dict[str, Any]] = []
    selection_gate_status = "PASS" if (
        selection_alignment.get("status") == "PASS"
        and selection_schedule.get("status") == "PASS"
        and selection_regime_evidence.get("status") == "PASS"
        and selection_correlation_matrix.get("status") == "PASS"
    ) else "BLOCK"
    if selection_gate_status == "PASS":
        for strategy_id in strategies:
            for symbol in selection_symbols:
                selection_cells.append(run_cell(
                    symbol=symbol,
                    strategy_id=strategy_id,
                    payload=selection_payloads[symbol],
                    risk=dict(strategy_specs[strategy_id]["risk"]),
                    limit=matrix_limit,
                    temporal_boundaries=(selection_schedule.get("symbol_boundaries") or {}).get(symbol, {}),
                ))

    rankings = [] if selection_gate_status != "PASS" else [
            aggregate_strategy_selection(
                strategy_id,
                [cell for cell in selection_cells if cell["strategy_id"] == strategy_id],
                strategy_trials=len(strategies),
                required_symbols=len(selection_symbols),
            )
            for strategy_id in strategies
        ]
    rankings.sort(key=lambda item: item["adjusted_score"], reverse=True)
    confirmation_candidates = [
        item["strategy_id"] for item in rankings if item.get("eligible_for_confirmation")
    ][:int(batch_spec["max_confirmation_candidates"])]

    confirmation_cells: list[dict[str, Any]] = []
    confirmation_payloads: dict[str, dict[str, Any]] = {}
    confirmation_manifests: list[dict[str, Any]] = []
    confirmation_alignment: dict[str, Any] = {
        "status": "NOT_RUN",
        "common_as_of": selection_alignment.get("common_as_of", ""),
        "blockers": ["no_selection_candidate"],
    }
    confirmation_schedule: dict[str, Any] = {
        "status": "NOT_RUN",
        "blockers": ["no_selection_candidate"],
        "symbol_boundaries": {},
    }
    confirmation_regime_evidence = unavailable_regime_evidence(
        status="NOT_RUN",
        blocker="no_selection_candidate",
    )
    if confirmation_candidates:
        confirmation_payloads, confirmation_manifests, confirmation_alignment = load_payloads(
            confirmation_symbols,
            matrix_limit,
            required_start=str(selection_alignment.get("common_start") or ""),
            required_as_of=str(selection_alignment.get("common_as_of") or ""),
            dataset_lineage_prefix=f"{lineage_prefix}:confirmation",
            require_frozen_revision=True,
        )
        confirmation_schedule = build_matrix_split_schedule(confirmation_payloads)
        if confirmation_alignment["status"] == "PASS" and confirmation_schedule["status"] != "PASS":
            confirmation_alignment["status"] = "BLOCK"
            confirmation_alignment["blockers"] = list(dict.fromkeys([
                *(confirmation_alignment.get("blockers") or []),
                *[f"calendar_split:{item}" for item in confirmation_schedule.get("blockers") or []],
            ]))
            for manifest in confirmation_manifests:
                manifest["status"] = "BLOCK"
                manifest["blockers"] = list(dict.fromkeys([
                    *(manifest.get("blockers") or []),
                    *[f"calendar_split:{item}" for item in confirmation_schedule.get("blockers") or []],
                ]))
        if confirmation_alignment["status"] == "PASS":
            confirmation_regime_evidence = build_regime_evidence(confirmation_payloads, confirmation_schedule)
        if (
            confirmation_alignment.get("status") == "PASS"
            and confirmation_schedule.get("status") == "PASS"
            and confirmation_regime_evidence.get("status") == "PASS"
        ):
            for strategy_id in confirmation_candidates:
                for symbol in confirmation_symbols:
                    confirmation_cells.append(run_cell(
                        symbol=symbol,
                        strategy_id=strategy_id,
                        payload=confirmation_payloads[symbol],
                        risk=dict(strategy_specs[strategy_id]["risk"]),
                        limit=matrix_limit,
                        temporal_boundaries=(confirmation_schedule.get("symbol_boundaries") or {}).get(symbol, {}),
                    ))
    confirmations = [
        confirmation_summary(
            strategy_id,
            [cell for cell in confirmation_cells if cell["strategy_id"] == strategy_id],
            len(confirmation_symbols),
        )
        for strategy_id in confirmation_candidates
    ]
    if confirmation_alignment.get("status") == "BLOCK":
        alignment_blockers = [
            f"confirmation_alignment:{item}" for item in confirmation_alignment.get("blockers") or []
        ]
        for item in confirmations:
            item["status"] = "BLOCK"
            item["forward_candidate"] = False
            item["blockers"] = list(dict.fromkeys([*(item.get("blockers") or []), *alignment_blockers]))
    forward_candidates = [item["strategy_id"] for item in confirmations if item.get("forward_candidate")]

    dataset_manifest = [*selection_manifests, *confirmation_manifests]
    dataset_manifest_hash = canonical_hash(dataset_manifest)
    batch_spec_hash = canonical_hash(batch_spec)
    dataset_snapshot = build_matrix_dataset_snapshot(
        registration_id=str(protocol.get("registration_id") or "DEVELOPMENT_ONLY"),
        batch_spec_hash=batch_spec_hash,
        dataset_manifest=dataset_manifest,
        selection_payloads=selection_payloads,
        confirmation_payloads=confirmation_payloads,
    )
    completion_clock: dict[str, Any] = {}
    if formal_mode:
        completion_clock = attest_utc_clock()
        completed_at_ms = int(completion_clock.get("attested_now_ms") or 0)
        if completed_at_ms <= 0:
            raise SystemExit(json.dumps({
                "error": "matrix_completion_clock_blocked",
                "clock": completion_clock,
            }, ensure_ascii=False))
        created_at = datetime.fromtimestamp(completed_at_ms / 1000, tz=timezone.utc).isoformat()
    else:
        completed_at_ms = time.time_ns() // 1_000_000
        created_at = datetime.fromtimestamp(completed_at_ms / 1000, tz=timezone.utc).isoformat()
    payload = {
        "schema_version": MATRIX_REPORT_SCHEMA_VERSION,
        "created_at": created_at,
        "batch_spec": batch_spec,
        "batch_spec_hash": batch_spec_hash,
        "dataset_manifest": dataset_manifest,
        "dataset_manifest_hash": dataset_manifest_hash,
        "dataset_snapshot": dataset_snapshot,
        "selection_alignment": selection_alignment,
        "selection_calendar_schedule": selection_schedule,
        "selection_regime_evidence": selection_regime_evidence,
        "selection_correlation_matrix": selection_correlation_matrix,
        "selection_cells": selection_cells,
        "selection_rankings": rankings,
        "confirmation_candidates": confirmation_candidates,
        "confirmation_cells": confirmation_cells,
        "confirmations": confirmations,
        "confirmation_alignment": confirmation_alignment,
        "confirmation_calendar_schedule": confirmation_schedule,
        "confirmation_regime_evidence": confirmation_regime_evidence,
        "forward_candidates": forward_candidates,
        "summary": {
            "strategies": len(strategies),
            "selection_symbols": len(selection_symbols),
            "selection_cells": len(selection_cells),
            "selection_passed": sum(bool(item.get("eligible_for_confirmation")) for item in rankings),
            "confirmation_candidates": len(confirmation_candidates),
            "confirmation_cells": len(confirmation_cells),
            "forward_candidates": len(forward_candidates),
            "data_status": selection_alignment.get("status", "BLOCK"),
            "selection_gate_status": selection_gate_status,
            "market_regime_status": selection_regime_evidence.get("status", "BLOCK"),
            "portfolio_correlation_status": selection_correlation_matrix.get("status", "BLOCK"),
            "common_as_of": selection_alignment.get("common_as_of", ""),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    payload["matrix_result_hash"] = strategy_matrix_result_hash(payload)

    if formal_mode:
        assert registration_store is not None
        finalization = finalize_formal_strategy_matrix_result(
            registration_store=registration_store,
            registration_id=args.registration_id,
            report_dir=reports_dir,
            output=output,
            protocol=protocol,
            claim=claim,
            payload=payload,
            completion_clock=completion_clock,
        )
        if not finalization.get("ok"):
            raise SystemExit(json.dumps({
                "error": "matrix_formal_finalization_blocked",
                "finalization": finalization,
            }, ensure_ascii=False))
        payload = dict(finalization.get("report") or {})
    else:
        exposure_audit = {
            "schema_version": "strategy-matrix-exposure-audit-v1",
            "status": "BLOCK",
            "evaluated_before_data_load": False,
            "symbols": confirmation_symbols,
            "exposed_symbols": confirmation_symbols,
            "evidence": {},
            "blockers": ["development_matrix_does_not_preserve_blind_holdout"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        exposure_audit["audit_hash"] = canonical_hash(exposure_audit)
        research_governance = {
            "schema_version": MATRIX_RESEARCH_GOVERNANCE_VERSION,
            "status": "DEVELOPMENT_ONLY",
            "selection_test_policy": "DEVELOPMENT_ONLY",
            "development_only": True,
            "single_use_claim": False,
            "registration_id": "",
            "protocol_hash": "",
            "claim_hash": "",
            "completion_hash": "",
            "registered_at_ms": 0,
            "started_at_ms": started_at_ms,
            "completed_at_ms": completed_at_ms,
            "holdout_exposure_audit": exposure_audit,
            "protocol": {},
            "single_use_claim_receipt": {},
            "completion_receipt": {},
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        research_governance["governance_hash"] = canonical_hash(research_governance)
        payload["research_governance"] = research_governance
        payload["batch_run_hash"] = strategy_matrix_run_hash(payload)
        write_json_atomic(output, payload)
    print(json.dumps({
        **payload["summary"],
        "batch_run_hash": payload["batch_run_hash"],
        "report": str(output),
        "top_rankings": [
            {
                "strategy_id": item["strategy_id"],
                "status": item["status"],
                "adjusted_score": item["adjusted_score"],
                "blockers": item["blockers"],
            }
            for item in rankings[:4]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
