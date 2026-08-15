from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .backtest_engine import prepare_backtest_dataset
from .strategy_fold_replay import replay_fixed_chronological_slice
from .strategy_research_search_lineage import (
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
)
from .strategy_validation import chronological_folds, summarize_walk_forward


LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION = 9
FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION = 10
COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS = frozenset({
    8,
    9,
    10,
    11,
    12,
    13,
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
})
CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSIONS = frozenset({
    9,
    10,
    11,
    12,
    13,
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
})
FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_V1_REPORT_SCHEMA_VERSIONS = frozenset({9})
FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_V2_REPORT_SCHEMA_VERSIONS = frozenset({
    10,
    11,
    12,
    13,
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
})
STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION = (
    "strategy-fixed-chronological-slice-evidence-v1"
)
STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION_V2 = (
    "strategy-fixed-chronological-slice-evidence-v2"
)
STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V4 = (
    "strategy-research-selection-cell-evidence-v4"
)
STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V5 = (
    "strategy-research-selection-cell-evidence-v5"
)
FIXED_CHRONOLOGICAL_SLICE_POLICY_SCHEMA_VERSION = (
    "strategy-fixed-chronological-slice-policy-v1"
)
FIXED_CHRONOLOGICAL_SLICE_FOLD_COUNT = 3
FIXED_CHRONOLOGICAL_SLICE_MINIMUM_FOLD_ROWS = 120


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _native_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _native_finite(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _dataset_identity(
    rows: list[dict[str, Any]],
    *,
    symbol: str,
    source: str,
    market: str,
    timeframe: str,
) -> dict[str, Any]:
    manifest = prepare_backtest_dataset(
        rows,
        symbol=symbol,
        source=source,
        timeframe=timeframe,
        minimum_rows=1,
        market=market,
    )["manifest"]
    return {
        "symbol": str(manifest.get("symbol") or ""),
        "source": str(manifest.get("source") or ""),
        "market": str(manifest.get("market") or ""),
        "timeframe": str(manifest.get("timeframe") or ""),
        "hash_scope": str(manifest.get("hash_scope") or ""),
        "data_hash": str(manifest.get("data_hash") or ""),
        "row_count": manifest.get("row_count"),
        "first": str(manifest.get("first") or ""),
        "last": str(manifest.get("last") or ""),
        "first_ts_ms": manifest.get("first_ts_ms"),
        "last_ts_ms": manifest.get("last_ts_ms"),
    }


def build_fixed_chronological_slice_evidence(
    *,
    selection_rows: list[dict[str, Any]] | Any,
    symbol: str,
    source: str,
    market: str,
    timeframe: str,
    fold_plans: list[dict[str, Any]] | Any,
    fold_reports: list[dict[str, Any]] | Any,
    minimum_fold_rows: int,
) -> dict[str, Any]:
    """Freeze fixed-parameter slice topology and results without claiming WFO."""

    rows = [dict(item) for item in selection_rows] if isinstance(selection_rows, list) and all(
        isinstance(item, dict) for item in selection_rows
    ) else []
    plans = [dict(item) for item in fold_plans] if isinstance(fold_plans, list) and all(
        isinstance(item, dict) for item in fold_plans
    ) else []
    reports = [dict(item) for item in fold_reports] if isinstance(fold_reports, list) and all(
        isinstance(item, dict) for item in fold_reports
    ) else []
    minimum = _native_nonnegative_int(minimum_fold_rows)
    integrity_blockers: list[str] = []
    if not rows:
        integrity_blockers.append("chronological_selection_prefix_empty_or_invalid")
    if not plans or len(plans) != len(reports):
        integrity_blockers.append("chronological_fold_plan_result_coverage_invalid")
    if minimum is None or minimum < 1:
        integrity_blockers.append("chronological_minimum_fold_rows_invalid")
        minimum = 1

    selection_identity = _dataset_identity(
        rows,
        symbol=symbol,
        source=source,
        market=market,
        timeframe=timeframe,
    )
    projected_folds: list[dict[str, Any]] = []
    cursor = 0
    topology_strict_order = True
    topology_no_overlap = True
    topology_no_gaps = True
    for index, (plan, report) in enumerate(zip(plans, reports), start=1):
        fold_number = _native_nonnegative_int(plan.get("fold"))
        start_index = _native_nonnegative_int(plan.get("start_index"))
        end_index = _native_nonnegative_int(plan.get("end_index"))
        declared_count = _native_nonnegative_int(plan.get("count"))
        if fold_number != index:
            integrity_blockers.append(f"chronological_fold_number_invalid:{index}")
            topology_strict_order = False
        if start_index is None or end_index is None or end_index <= start_index or end_index > len(rows):
            integrity_blockers.append(f"chronological_fold_bounds_invalid:{index}")
            start_index = min(start_index or 0, len(rows))
            end_index = min(max(end_index or start_index, start_index), len(rows))
        if start_index < cursor:
            integrity_blockers.append(f"chronological_fold_overlap:{index}")
            topology_no_overlap = False
        elif start_index > cursor:
            integrity_blockers.append(f"chronological_fold_gap:{index}")
            topology_no_gaps = False
        actual_rows = rows[start_index:end_index]
        actual_count = len(actual_rows)
        if declared_count != actual_count:
            integrity_blockers.append(f"chronological_fold_count_mismatch:{index}")
        if actual_count < minimum:
            integrity_blockers.append(f"chronological_fold_minimum_rows_not_met:{index}")
        actual_start = str(actual_rows[0].get("date") or "") if actual_rows else ""
        actual_end = str(actual_rows[-1].get("date") or "") if actual_rows else ""
        if str(plan.get("start") or "") != actual_start:
            integrity_blockers.append(f"chronological_fold_start_mismatch:{index}")
        if str(plan.get("end") or "") != actual_end:
            integrity_blockers.append(f"chronological_fold_end_mismatch:{index}")
        if report.get("fold") != fold_number:
            integrity_blockers.append(f"chronological_fold_result_identity_mismatch:{index}")
        if str(report.get("start") or "") != actual_start:
            integrity_blockers.append(f"chronological_fold_result_start_mismatch:{index}")
        if str(report.get("end") or "") != actual_end:
            integrity_blockers.append(f"chronological_fold_result_end_mismatch:{index}")
        if not isinstance(report.get("ok"), bool):
            integrity_blockers.append(f"chronological_fold_result_ok_type_invalid:{index}")
        if not _native_finite(report.get("total_return_pct")):
            integrity_blockers.append(f"chronological_fold_result_return_invalid:{index}")
        if (
            not _native_finite(report.get("max_drawdown_pct"))
            or float(report.get("max_drawdown_pct")) < 0
        ):
            integrity_blockers.append(f"chronological_fold_result_drawdown_invalid:{index}")
        if _native_nonnegative_int(report.get("trade_count")) is None:
            integrity_blockers.append(f"chronological_fold_result_trade_count_invalid:{index}")
        projected_folds.append({
            "fold": fold_number,
            "count": actual_count,
            "start_index": start_index,
            "end_index": end_index,
            "start": actual_start,
            "end": actual_end,
            "dataset_identity": _dataset_identity(
                actual_rows,
                symbol=symbol,
                source=source,
                market=market,
                timeframe=timeframe,
            ),
            "ok": report.get("ok") is True,
            "total_return_pct": report.get("total_return_pct"),
            "max_drawdown_pct": report.get("max_drawdown_pct"),
            "trade_count": report.get("trade_count"),
        })
        cursor = max(cursor, end_index)

    if cursor != len(rows):
        integrity_blockers.append("chronological_selection_prefix_not_fully_covered")
        topology_no_gaps = False
    summary = summarize_walk_forward(projected_folds)
    if integrity_blockers:
        summary["status"] = "BLOCK"
    summary_blockers = [str(item) for item in summary.get("blockers") or []]
    all_blockers = list(dict.fromkeys([*integrity_blockers, *summary_blockers]))
    content = {
        "schema_version": STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION,
        "verification_status": "PASS" if not integrity_blockers else "BLOCK",
        "status": "PASS" if not all_blockers else "BLOCK",
        "evaluation_mode": "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
        "parameters_refit_per_fold": False,
        "walk_forward_optimization_claim_allowed": False,
        "selection_prefix": selection_identity,
        "minimum_fold_rows": minimum,
        "coverage": {
            "start_index": 0,
            "end_index": cursor,
            "row_count": len(rows),
            "strict_order": topology_strict_order,
            "no_overlap": topology_no_overlap,
            "no_gaps": topology_no_gaps,
            "fully_covered": cursor == len(rows) and not integrity_blockers,
        },
        "fold_count": summary.get("fold_count"),
        "usable_folds": summary.get("usable_folds"),
        "positive_folds": summary.get("positive_folds"),
        "total_trades": summary.get("total_trades"),
        "worst_drawdown_pct": summary.get("worst_drawdown_pct"),
        "folds": projected_folds,
        "integrity_blockers": list(dict.fromkeys(integrity_blockers)),
        "outcome_blockers": summary_blockers,
        "blockers": all_blockers,
        "descriptive_only": True,
        "profitability_proven": False,
        "parameter_selection_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "evidence_hash": _canonical_hash(content)}


def build_fixed_chronological_slice_evidence_v2(
    *,
    selection_rows: list[dict[str, Any]] | Any,
    symbol: str,
    source: str,
    market: str,
    timeframe: str,
    strategy_id: str,
    params: dict[str, Any] | Any,
    param_hash: str,
    risk: dict[str, Any] | Any,
) -> dict[str, Any]:
    """Recompute fixed-slice results from frozen rows and fully bound inputs."""

    rows = [dict(item) for item in selection_rows] if isinstance(selection_rows, list) and all(
        isinstance(item, dict) for item in selection_rows
    ) else []
    fold_plan = chronological_folds(
        rows,
        fold_count=FIXED_CHRONOLOGICAL_SLICE_FOLD_COUNT,
        minimum_fold_rows=FIXED_CHRONOLOGICAL_SLICE_MINIMUM_FOLD_ROWS,
    )
    plans = [dict(item) for item in fold_plan.get("folds") or []]
    minimum = FIXED_CHRONOLOGICAL_SLICE_MINIMUM_FOLD_ROWS
    integrity_blockers: list[str] = []
    if not rows:
        integrity_blockers.append("chronological_selection_prefix_empty_or_invalid")
    if fold_plan.get("status") != "PASS" or not plans:
        integrity_blockers.append("chronological_fold_plan_coverage_invalid")

    selection_identity = _dataset_identity(
        rows,
        symbol=symbol,
        source=source,
        market=market,
        timeframe=timeframe,
    )
    projected_folds: list[dict[str, Any]] = []
    cursor = 0
    topology_strict_order = True
    topology_no_overlap = True
    topology_no_gaps = True
    for index, plan in enumerate(plans, start=1):
        fold_number = _native_nonnegative_int(plan.get("fold"))
        start_index = _native_nonnegative_int(plan.get("start_index"))
        end_index = _native_nonnegative_int(plan.get("end_index"))
        declared_count = _native_nonnegative_int(plan.get("count"))
        if fold_number != index:
            integrity_blockers.append(f"chronological_fold_number_invalid:{index}")
            topology_strict_order = False
        if start_index is None or end_index is None or end_index <= start_index or end_index > len(rows):
            integrity_blockers.append(f"chronological_fold_bounds_invalid:{index}")
            start_index = min(start_index or 0, len(rows))
            end_index = min(max(end_index or start_index, start_index), len(rows))
        if start_index < cursor:
            integrity_blockers.append(f"chronological_fold_overlap:{index}")
            topology_no_overlap = False
        elif start_index > cursor:
            integrity_blockers.append(f"chronological_fold_gap:{index}")
            topology_no_gaps = False
        actual_rows = rows[start_index:end_index]
        actual_count = len(actual_rows)
        if declared_count != actual_count:
            integrity_blockers.append(f"chronological_fold_count_mismatch:{index}")
        if actual_count < minimum:
            integrity_blockers.append(f"chronological_fold_minimum_rows_not_met:{index}")
        actual_start = str(actual_rows[0].get("date") or "") if actual_rows else ""
        actual_end = str(actual_rows[-1].get("date") or "") if actual_rows else ""
        if str(plan.get("start") or "") != actual_start:
            integrity_blockers.append(f"chronological_fold_start_mismatch:{index}")
        if str(plan.get("end") or "") != actual_end:
            integrity_blockers.append(f"chronological_fold_end_mismatch:{index}")
        try:
            replay = replay_fixed_chronological_slice(
                rows=actual_rows,
                symbol=symbol,
                source=source,
                market=market,
                timeframe=timeframe,
                fold_number=index,
                strategy_id=strategy_id,
                params=params,
                param_hash=param_hash,
                risk=risk,
            )
        except (TypeError, ValueError, KeyError, OverflowError):
            replay = {"input_identity": {}, "result_projection": {}}
            integrity_blockers.append(f"chronological_fold_replay_invalid:{index}")
        result = replay.get("result_projection") if isinstance(replay, dict) else {}
        result = result if isinstance(result, dict) else {}
        if not isinstance(result.get("ok"), bool):
            integrity_blockers.append(f"chronological_fold_result_ok_type_invalid:{index}")
        if result.get("ok") is True:
            if not _native_finite(result.get("total_return_pct")):
                integrity_blockers.append(f"chronological_fold_result_return_invalid:{index}")
            if (
                not _native_finite(result.get("max_drawdown_pct"))
                or float(result.get("max_drawdown_pct")) < 0
            ):
                integrity_blockers.append(f"chronological_fold_result_drawdown_invalid:{index}")
            if _native_nonnegative_int(result.get("trade_count")) is None:
                integrity_blockers.append(f"chronological_fold_result_trade_count_invalid:{index}")
        projected_folds.append({
            "fold": fold_number,
            "count": actual_count,
            "start_index": start_index,
            "end_index": end_index,
            "start": actual_start,
            "end": actual_end,
            "input_identity": replay.get("input_identity") if isinstance(replay, dict) else {},
            "result_projection": result,
            "ok": result.get("ok") is True,
            "total_return_pct": result.get("total_return_pct"),
            "max_drawdown_pct": result.get("max_drawdown_pct"),
            "trade_count": result.get("trade_count"),
        })
        cursor = max(cursor, end_index)

    if cursor != len(rows):
        integrity_blockers.append("chronological_selection_prefix_not_fully_covered")
        topology_no_gaps = False
    summary = summarize_walk_forward(projected_folds)
    if integrity_blockers:
        summary["status"] = "BLOCK"
    summary_blockers = [str(item) for item in summary.get("blockers") or []]
    all_blockers = list(dict.fromkeys([*integrity_blockers, *summary_blockers]))
    content = {
        "schema_version": STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION_V2,
        "verification_status": "PASS" if not integrity_blockers else "BLOCK",
        "status": "PASS" if not all_blockers else "BLOCK",
        "evaluation_mode": "FIXED_PARAMETER_CHRONOLOGICAL_SLICES_REPLAYED",
        "parameters_refit_per_fold": False,
        "walk_forward_optimization_claim_allowed": False,
        "selection_prefix": selection_identity,
        "minimum_fold_rows": minimum,
        "fold_policy": {
            "schema_version": FIXED_CHRONOLOGICAL_SLICE_POLICY_SCHEMA_VERSION,
            "fold_count": FIXED_CHRONOLOGICAL_SLICE_FOLD_COUNT,
            "minimum_fold_rows": FIXED_CHRONOLOGICAL_SLICE_MINIMUM_FOLD_ROWS,
        },
        "coverage": {
            "start_index": 0,
            "end_index": cursor,
            "row_count": len(rows),
            "strict_order": topology_strict_order,
            "no_overlap": topology_no_overlap,
            "no_gaps": topology_no_gaps,
            "fully_covered": cursor == len(rows) and not integrity_blockers,
        },
        "fold_count": summary.get("fold_count"),
        "usable_folds": summary.get("usable_folds"),
        "positive_folds": summary.get("positive_folds"),
        "total_trades": summary.get("total_trades"),
        "worst_drawdown_pct": summary.get("worst_drawdown_pct"),
        "folds": projected_folds,
        "integrity_blockers": list(dict.fromkeys(integrity_blockers)),
        "outcome_blockers": summary_blockers,
        "blockers": all_blockers,
        "descriptive_only": True,
        "profitability_proven": False,
        "parameter_selection_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "evidence_hash": _canonical_hash(content)}


__all__ = [
    "CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSIONS",
    "COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS",
    "FIXED_CHRONOLOGICAL_SLICE_FOLD_COUNT",
    "FIXED_CHRONOLOGICAL_SLICE_MINIMUM_FOLD_ROWS",
    "FIXED_CHRONOLOGICAL_SLICE_POLICY_SCHEMA_VERSION",
    "FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION",
    "FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_V1_REPORT_SCHEMA_VERSIONS",
    "FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_V2_REPORT_SCHEMA_VERSIONS",
    "LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION",
    "STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION",
    "STRATEGY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_SCHEMA_VERSION_V2",
    "STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V4",
    "STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V5",
    "build_fixed_chronological_slice_evidence",
    "build_fixed_chronological_slice_evidence_v2",
]
