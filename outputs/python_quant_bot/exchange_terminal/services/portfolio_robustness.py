from __future__ import annotations

import hashlib
import json
import math
from typing import Any


PORTFOLIO_ROBUSTNESS_SCHEMA_VERSION = "portfolio-robustness-diagnostic-v2"


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


def _nonnegative_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0 or not parsed.is_integer():
        return None
    return int(parsed)


def fixed_parameter_stress_cases(spec: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"label": "BASELINE", "overrides": {}},
        {"label": "LOOKBACK_105", "overrides": {"lookback": 105}},
        {"label": "LOOKBACK_147", "overrides": {"lookback": 147}},
        {"label": "SKIP_RECENT_3", "overrides": {"skip_recent": 3}},
        {"label": "SKIP_RECENT_10", "overrides": {"skip_recent": 10}},
        {"label": "TARGET_VOL_12", "overrides": {"target_portfolio_volatility_pct": 12.0}},
        {"label": "TARGET_VOL_18", "overrides": {"target_portfolio_volatility_pct": 18.0}},
    ]


def compact_backtest_result(label: str, report: dict[str, Any], **metadata: Any) -> dict[str, Any]:
    return {
        "label": str(label),
        **metadata,
        "ok": report.get("ok") is True,
        "total_return_pct": report.get("total_return_pct"),
        "max_drawdown_pct": report.get("max_drawdown_pct"),
        "sharpe": report.get("sharpe"),
        "annualized_turnover_multiple": report.get("annualized_turnover_multiple"),
        "order_event_count": report.get("order_event_count"),
        "partial_fill_count": report.get("partial_fill_count"),
        "liquidity_block_count": report.get("liquidity_block_count"),
        "gap_block_count": report.get("gap_block_count"),
        "schedule_status": str((report.get("schedule_contract") or {}).get("status") or "BLOCK"),
        "run_hash": str(report.get("run_hash") or ""),
    }


def build_robustness_assessment(
    *,
    candidate_hash: str,
    dataset_hash: str,
    parameter_results: list[dict[str, Any]],
    ablation_results: list[dict[str, Any]],
    capital_results: list[dict[str, Any]],
    created_at: str = "",
    candidate_verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parameter_ok = [
        item for item in parameter_results
        if item.get("ok") is True
        and item.get("schedule_status") == "PASS"
        and _number(item.get("total_return_pct")) > 0
        and _number(item.get("max_drawdown_pct"), 100.0) < 15.0
    ]
    ablation_ok = [
        item for item in ablation_results
        if item.get("ok") is True
        and item.get("schedule_status") == "PASS"
        and _number(item.get("total_return_pct")) > 0
    ]
    capital_by_label = {str(item.get("label") or ""): item for item in capital_results}
    negative_ablation_symbols = [
        str(item.get("removed_symbol") or item.get("label") or "")
        for item in ablation_results
        if item.get("ok") is not True or _number(item.get("total_return_pct")) <= 0
    ]
    checks = {
        "candidate_hash_present": bool(candidate_hash),
        "dataset_hash_present": bool(dataset_hash),
        "candidate_verification_pass": (candidate_verification or {}).get("status") == "PASS",
        "parameter_neighborhood_positive_at_least_5_of_7": len(parameter_ok) >= 5 and len(parameter_results) == 7,
        "universe_ablation_positive_at_least_75_pct": bool(ablation_results) and len(ablation_ok) / len(ablation_results) >= 0.75,
        "baseline_capital_positive": _number((capital_by_label.get("CAPITAL_100K") or {}).get("total_return_pct")) > 0,
        "million_capital_positive_without_partial_fills": (
            _number((capital_by_label.get("CAPITAL_1M") or {}).get("total_return_pct")) > 0
            and _nonnegative_integer((capital_by_label.get("CAPITAL_1M") or {}).get("partial_fill_count")) == 0
        ),
        "all_diagnostics_follow_schedule": all(
            item.get("schedule_status") == "PASS"
            for item in [*parameter_results, *ablation_results, *capital_results]
        ),
    }
    payload = {
        "schema_version": PORTFOLIO_ROBUSTNESS_SCHEMA_VERSION,
        "status": "ROBUSTNESS_PASS" if all(checks.values()) else "ROBUSTNESS_BLOCK",
        "candidate_hash": str(candidate_hash or ""),
        "dataset_hash": str(dataset_hash or ""),
        "created_at": str(created_at or ""),
        "candidate_verification": dict(candidate_verification or {}),
        "checks": checks,
        "warnings": [
            f"single_symbol_ablation_non_positive:{symbol}"
            for symbol in negative_ablation_symbols
        ],
        "parameter_summary": {
            "case_count": len(parameter_results),
            "positive_bounded_count": len(parameter_ok),
        },
        "ablation_summary": {
            "case_count": len(ablation_results),
            "positive_count": len(ablation_ok),
            "positive_ratio": round(len(ablation_ok) / len(ablation_results), 6) if ablation_results else 0.0,
        },
        "parameter_results": parameter_results,
        "ablation_results": ablation_results,
        "capital_results": capital_results,
        "diagnostic_only": True,
        "parameter_selection_allowed": False,
        "manual_review_required": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["robustness_hash"] = _canonical_hash(payload)
    return payload


def verify_robustness_report(report: dict[str, Any], *, candidate_hash: str) -> dict[str, Any]:
    payload = dict(report or {})
    expected_hash = str(payload.pop("robustness_hash", "") or "")
    blockers: list[str] = []
    if str(report.get("schema_version") or "") != PORTFOLIO_ROBUSTNESS_SCHEMA_VERSION:
        blockers.append("robustness_schema_invalid")
    if str(report.get("status") or "") != "ROBUSTNESS_PASS":
        blockers.append("robustness_status_not_passed")
    if str(report.get("candidate_hash") or "") != str(candidate_hash or ""):
        blockers.append("robustness_candidate_hash_mismatch")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("robustness_hash_mismatch")
    if report.get("paper_authorized") is not False or report.get("live_order_allowed") is not False:
        blockers.append("robustness_report_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "expected_hash": expected_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
