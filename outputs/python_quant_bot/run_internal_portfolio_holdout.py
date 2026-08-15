from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from exchange_terminal import server
from exchange_terminal.services.portfolio_backtest import (
    audit_relative_strength_causality,
    prepare_attested_portfolio_dataset,
    relative_strength_settings_from_spec,
    run_causal_relative_strength_backtest,
    slice_portfolio_payload_through_date,
)
from exchange_terminal.services.portfolio_candidate import verify_frozen_portfolio_candidate
from exchange_terminal.services.portfolio_forward import (
    DEFAULT_ACTIVE_CANDIDATE_FILE,
    load_active_portfolio_candidate,
)
from exchange_terminal.services.portfolio_risk import build_correlation_matrix
from exchange_terminal.services.research_exposure import audit_blind_holdout_symbols
from exchange_terminal.services.strategy_benchmark import buy_and_hold_report


DEFAULT_HOLDOUT_SYMBOLS = ["AMAT", "LRCX", "KLAC", "QCOM", "INTC", "STX", "NTAP", "SMCI"]
HOLDOUT_CLUSTERS = {
    "AMAT": "SEMI_EQUIPMENT",
    "LRCX": "SEMI_EQUIPMENT",
    "KLAC": "SEMI_EQUIPMENT",
    "QCOM": "SEMI_DESIGN",
    "INTC": "SEMI_FOUNDRY",
    "STX": "MEMORY_STORAGE",
    "NTAP": "MEMORY_STORAGE",
    "SMCI": "AI_SERVER",
}


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def finite_number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if math.isfinite(parsed) else default


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def benchmark_report(
    payload: dict[str, Any],
    symbol: str,
    position_pct: float,
    start_index: int,
    *,
    fee_rate: float = 0.0005,
    slippage_bps: float = 2.0,
) -> dict[str, Any]:
    return buy_and_hold_report(
        rows=list(payload.get("rows") or []),
        symbol=symbol,
        source=f"{payload.get('source') or ''}:cross_sectional_holdout_benchmark",
        position_pct=position_pct,
        startup_candles=80,
        fee_rate=fee_rate,
        slippage_bps=slippage_bps,
        market="stock",
        evaluation_start_index=start_index,
    )


def comparison(strategy: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    strategy_return = finite_number(strategy.get("total_return_pct"))
    benchmark_return = finite_number(benchmark.get("total_return_pct"))
    strategy_drawdown = finite_number(strategy.get("max_drawdown_pct"))
    benchmark_drawdown = finite_number(benchmark.get("max_drawdown_pct"))
    strategy_sharpe = finite_number(strategy.get("sharpe"))
    benchmark_sharpe = finite_number(benchmark.get("sharpe"))
    return {
        "strategy_return_pct": round(strategy_return, 4),
        "benchmark_return_pct": round(benchmark_return, 4),
        "excess_return_pct": round(strategy_return - benchmark_return, 4),
        "strategy_max_drawdown_pct": round(strategy_drawdown, 4),
        "benchmark_max_drawdown_pct": round(benchmark_drawdown, 4),
        "drawdown_improvement_pct": round(benchmark_drawdown - strategy_drawdown, 4),
        "strategy_sharpe": round(strategy_sharpe, 4),
        "benchmark_sharpe": round(benchmark_sharpe, 4),
        "sharpe_excess": round(strategy_sharpe - benchmark_sharpe, 4),
        "risk_efficiency_excess": round(
            strategy_return / max(strategy_drawdown, 1.0)
            - benchmark_return / max(benchmark_drawdown, 1.0),
            6,
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one cross-sectional holdout against a frozen portfolio candidate.")
    parser.add_argument("--candidate", default="")
    parser.add_argument("--registry", default="")
    parser.add_argument("--holdout-symbols", nargs="+", default=DEFAULT_HOLDOUT_SYMBOLS)
    parser.add_argument("--limit", type=int, default=780)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    report_dir = Path(server.RUNTIME_DIR) / "reports"
    if args.candidate:
        candidate_path = Path(args.candidate).resolve()
        candidate = read_json(candidate_path)
        candidate_verification = verify_frozen_portfolio_candidate(candidate)
    else:
        registry_path = Path(args.registry).resolve() if args.registry else report_dir / DEFAULT_ACTIVE_CANDIDATE_FILE
        active = load_active_portfolio_candidate(report_dir, registry_path=registry_path)
        if active["status"] != "PASS":
            print(json.dumps({"ok": False, "status": "BLOCK", "active_candidate": active}, ensure_ascii=False, indent=2))
            return 2
        candidate_path = Path(str(active["candidate_path"]))
        candidate = dict(active["candidate"])
        candidate_verification = dict(active["candidate_verification"])
    if candidate_verification["status"] != "PASS":
        print(json.dumps({"ok": False, "candidate_verification": candidate_verification}, ensure_ascii=False, indent=2))
        return 2

    holdout_symbols = list(dict.fromkeys(str(symbol).upper() for symbol in args.holdout_symbols))
    exposure_audit = audit_blind_holdout_symbols(report_dir, holdout_symbols)
    if exposure_audit["status"] != "PASS":
        print(json.dumps({"ok": False, "exposure_audit": exposure_audit}, ensure_ascii=False, indent=2))
        return 3

    frozen_spec = dict(candidate.get("spec") or {})
    dataset_lineage_id = str(frozen_spec.get("experiment_id") or candidate.get("candidate_hash") or "").strip()
    settings = relative_strength_settings_from_spec(frozen_spec)
    benchmark = settings["benchmark_symbol"]
    cutoff = str(candidate.get("dataset_last") or "")
    if not cutoff:
        print(json.dumps({"ok": False, "status": "BLOCK", "reason": "candidate_dataset_cutoff_missing"}, ensure_ascii=False, indent=2))
        return 4
    raw_payloads = {
        symbol: slice_portfolio_payload_through_date(
            server.backtest_market_rows(
                symbol,
                max(int(args.limit), 180),
                dataset_lineage_id=dataset_lineage_id,
            ),
            cutoff,
            attest_backtest_rows=server.attest_stock_backtest_rows,
            dataset_lineage_id=dataset_lineage_id,
        )
        for symbol in [benchmark, *holdout_symbols]
    }
    prepared = prepare_attested_portfolio_dataset(
        raw_payloads,
        benchmark_symbol=benchmark,
        minimum_rows=180,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
    )
    if prepared["status"] != "PASS":
        print(json.dumps({"ok": False, "dataset_manifest": prepared["manifest"]}, ensure_ascii=False, indent=2))
        return 4
    payloads = dict(prepared["payloads"])
    row_count = int(prepared["manifest"].get("row_count") or 0)
    test_start = int(row_count * 0.75)
    settings.update({
        "tradable_symbols": holdout_symbols,
        "clusters": {symbol: HOLDOUT_CLUSTERS.get(symbol, symbol) for symbol in holdout_symbols},
    })
    holdout = run_causal_relative_strength_backtest(
        payloads=payloads,
        evaluation_start_index=test_start,
        **settings,
    )
    benchmark_result = benchmark_report(
        payloads[benchmark],
        benchmark,
        settings["gross_target_pct"],
        test_start,
        fee_rate=settings["fee_rate"],
        slippage_bps=settings["slippage_bps"],
    )
    result_comparison = comparison(holdout, benchmark_result)
    causal_audit = audit_relative_strength_causality(payloads=payloads, **settings)
    correlations = build_correlation_matrix(payloads)
    severe_settings = {**settings, "fee_rate": 0.0020, "slippage_bps": 10.0}
    severe_cost = run_causal_relative_strength_backtest(
        payloads=payloads,
        evaluation_start_index=test_start,
        **severe_settings,
    )
    checks = {
        "holdout_positive": finite_number(holdout.get("total_return_pct")) > 0,
        "holdout_drawdown_below_15": finite_number(holdout.get("max_drawdown_pct"), 100.0) < 15.0,
        "holdout_risk_efficiency_positive": finite_number(result_comparison.get("risk_efficiency_excess")) > 0,
        "holdout_annualized_turnover_below_12": finite_number(holdout.get("annualized_turnover_multiple"), 100.0) < 12.0,
        "holdout_order_events_at_least_10": int(holdout.get("order_event_count") or 0) >= 10,
        "severe_cost_positive": bool(severe_cost.get("ok")) and finite_number(severe_cost.get("total_return_pct")) > 0,
        "causal_audit_pass": causal_audit.get("status") == "PASS",
        "correlation_coverage_pass": correlations.get("status") == "PASS",
    }
    status = "CROSS_SECTIONAL_PASS" if all(checks.values()) else "CROSS_SECTIONAL_BLOCK"
    spec = {
        "candidate_path": str(candidate_path.resolve()),
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "benchmark_symbol": benchmark,
        "holdout_symbols": holdout_symbols,
        "holdout_clusters": settings["clusters"],
        "test_start_index": test_start,
        "dataset_cutoff": cutoff,
        "cross_sectional_independence": True,
        "temporal_independence": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report = {
        "schema_version": "portfolio-cross-sectional-holdout-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "spec": spec,
        "spec_hash": canonical_hash(spec),
        "candidate_verification": candidate_verification,
        "exposure_audit_before_load": exposure_audit,
        "dataset_manifest": prepared["manifest"],
        "holdout": holdout,
        "benchmark": benchmark_result,
        "comparison": result_comparison,
        "severe_cost": {
            "total_return_pct": severe_cost.get("total_return_pct"),
            "max_drawdown_pct": severe_cost.get("max_drawdown_pct"),
            "sharpe": severe_cost.get("sharpe"),
            "annualized_turnover_multiple": severe_cost.get("annualized_turnover_multiple"),
            "run_hash": severe_cost.get("run_hash", ""),
        },
        "causal_audit": causal_audit,
        "correlation_matrix": correlations,
        "checks": checks,
        "fresh_temporal_holdout_required": True,
        "forward_observation_required": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report["batch_run_hash"] = canonical_hash({
        "spec_hash": report["spec_hash"],
        "dataset_hash": prepared["manifest"].get("data_hash", ""),
        "holdout_run_hash": holdout.get("run_hash", ""),
        "benchmark_data_hash": (benchmark_result.get("dataset_manifest") or {}).get("data_hash", ""),
        "severe_cost_run_hash": severe_cost.get("run_hash", ""),
        "candidate_hash": candidate.get("candidate_hash", ""),
        "checks": checks,
        "status": status,
    })
    output = Path(args.output) if args.output else report_dir / f"portfolio_holdout_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": status,
        "comparison": result_comparison,
        "annualized_turnover_multiple": holdout.get("annualized_turnover_multiple"),
        "order_event_count": holdout.get("order_event_count"),
        "severe_cost_return_pct": severe_cost.get("total_return_pct"),
        "checks": checks,
        "fresh_temporal_holdout_required": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "batch_run_hash": report["batch_run_hash"],
        "report": str(output.resolve()),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
