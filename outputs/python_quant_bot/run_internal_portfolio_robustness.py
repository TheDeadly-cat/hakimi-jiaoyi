from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from exchange_terminal import server
from exchange_terminal.services.portfolio_backtest import (
    prepare_attested_portfolio_dataset,
    relative_strength_settings_from_spec,
    run_causal_relative_strength_backtest,
    slice_portfolio_payload_through_date,
)
from exchange_terminal.services.portfolio_candidate import verify_frozen_portfolio_candidate
from exchange_terminal.services.portfolio_forward import DEFAULT_ACTIVE_CANDIDATE_FILE, load_active_portfolio_candidate
from exchange_terminal.services.portfolio_robustness import (
    build_robustness_assessment,
    compact_backtest_result,
    fixed_parameter_stress_cases,
)
from exchange_terminal.services.portfolio_universe import derive_universe_subset_contract


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def through_cutoff(payload: dict[str, Any], cutoff: str, dataset_lineage_id: str) -> dict[str, Any]:
    return slice_portfolio_payload_through_date(
        payload,
        cutoff,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
    )


def engine_settings(spec: dict[str, Any]) -> dict[str, Any]:
    return relative_strength_settings_from_spec(spec)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fixed diagnostics against one frozen portfolio candidate without tuning it.")
    parser.add_argument("--candidate", default="")
    parser.add_argument("--registry", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    report_dir = Path(server.RUNTIME_DIR) / "reports"
    if args.candidate:
        candidate_path = Path(args.candidate).resolve()
        candidate = read_json(candidate_path)
        verification = verify_frozen_portfolio_candidate(candidate)
    else:
        registry_path = Path(args.registry).resolve() if args.registry else report_dir / DEFAULT_ACTIVE_CANDIDATE_FILE
        active = load_active_portfolio_candidate(report_dir, registry_path=registry_path)
        if active["status"] != "PASS":
            print(json.dumps({"ok": False, "status": "BLOCK", "active_candidate": active}, ensure_ascii=False, indent=2))
            return 2
        candidate_path = Path(str(active["candidate_path"]))
        candidate = dict(active["candidate"])
        verification = dict(active["candidate_verification"])
    if verification.get("status") != "PASS":
        print(json.dumps({"ok": False, "status": "BLOCK", "candidate_verification": verification}, ensure_ascii=False, indent=2))
        return 2

    spec = dict(candidate.get("spec") or {})
    dataset_lineage_id = str(spec.get("experiment_id") or candidate.get("candidate_hash") or "").strip()
    settings = engine_settings(spec)
    settings["universe_contract"] = dict(
        (candidate.get("research_governance") or {}).get("universe_contract") or {}
    )
    benchmark = settings["benchmark_symbol"]
    symbols = [benchmark, *settings["tradable_symbols"]]
    limit = int(args.limit) if int(args.limit) > 0 else max(int(candidate.get("dataset_row_count") or 0) + 30, 180)
    cutoff = str(candidate.get("dataset_last") or "")
    raw = {
        symbol: through_cutoff(
            server.backtest_market_rows(symbol, limit, dataset_lineage_id=dataset_lineage_id),
            cutoff,
            dataset_lineage_id,
        )
        for symbol in symbols
    }
    prepared = prepare_attested_portfolio_dataset(
        raw,
        benchmark_symbol=benchmark,
        minimum_rows=180,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
        universe_contract=settings["universe_contract"],
    )
    if prepared["status"] != "PASS" or str(prepared["manifest"].get("data_hash") or "") != str(candidate.get("dataset_hash") or ""):
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "reason": "frozen_dataset_hash_mismatch",
            "candidate_dataset_hash": candidate.get("dataset_hash"),
            "current_dataset_manifest": prepared["manifest"],
        }, ensure_ascii=False, indent=2))
        return 3
    payloads = dict(prepared["payloads"])
    evaluation_start_value = (
        spec["validation_end_index"]
        if "validation_end_index" in spec and spec["validation_end_index"] is not None
        else int(prepared["manifest"]["row_count"] * 0.75)
    )
    evaluation_start = int(evaluation_start_value)

    parameter_results: list[dict[str, Any]] = []
    for case in fixed_parameter_stress_cases(spec):
        case_settings = {**settings, **dict(case.get("overrides") or {})}
        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            evaluation_start_index=evaluation_start,
            **case_settings,
        )
        parameter_results.append(compact_backtest_result(
            str(case["label"]),
            report,
            overrides=dict(case.get("overrides") or {}),
        ))

    ablation_results: list[dict[str, Any]] = []
    for removed_symbol in settings["tradable_symbols"]:
        remaining = [symbol for symbol in settings["tradable_symbols"] if symbol != removed_symbol]
        case_payloads = {symbol: payload for symbol, payload in payloads.items() if symbol == benchmark or symbol in remaining}
        subset_contract = derive_universe_subset_contract(
            settings["universe_contract"],
            tradable_symbols=remaining,
            derivation_purpose=f"ROBUSTNESS_ABLATION_WITHOUT_{removed_symbol}",
        )
        report = run_causal_relative_strength_backtest(
            payloads=case_payloads,
            evaluation_start_index=evaluation_start,
            **{
                **settings,
                "tradable_symbols": remaining,
                "clusters": {symbol: settings["clusters"].get(symbol, symbol) for symbol in remaining},
                "universe_contract": subset_contract,
            },
        )
        ablation_results.append(compact_backtest_result(
            f"WITHOUT_{removed_symbol}",
            report,
            removed_symbol=removed_symbol,
        ))

    capital_results: list[dict[str, Any]] = []
    for label, capital in (("CAPITAL_100K", 100_000.0), ("CAPITAL_1M", 1_000_000.0), ("CAPITAL_10M", 10_000_000.0)):
        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            evaluation_start_index=evaluation_start,
            initial_cash=capital,
            **settings,
        )
        capital_results.append(compact_backtest_result(label, report, initial_cash=capital))

    assessment = build_robustness_assessment(
        candidate_hash=str(candidate.get("candidate_hash") or ""),
        dataset_hash=str(prepared["manifest"].get("data_hash") or ""),
        parameter_results=parameter_results,
        ablation_results=ablation_results,
        capital_results=capital_results,
        created_at=datetime.now(timezone.utc).isoformat(),
        candidate_verification=verification,
    )
    output = Path(args.output).resolve() if args.output else report_dir / f"portfolio_robustness_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    output.write_text(json.dumps(assessment, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ok": assessment["status"] == "ROBUSTNESS_PASS",
        "status": assessment["status"],
        "candidate_hash": assessment["candidate_hash"],
        "checks": assessment["checks"],
        "parameter_summary": assessment["parameter_summary"],
        "ablation_summary": assessment["ablation_summary"],
        "capital_results": assessment["capital_results"],
        "robustness_hash": assessment["robustness_hash"],
        "report": str(output.resolve()),
        "paper_authorized": False,
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if assessment["status"] == "ROBUSTNESS_PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
