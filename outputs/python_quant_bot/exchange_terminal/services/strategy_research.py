from __future__ import annotations

import hashlib
import json
import math
from statistics import median
from typing import Any


STRATEGY_RESEARCH_SCHEMA_VERSION = "nested-strategy-research-v2"

RAW_EXCESS_LANE = "RAW_EXCESS"
RISK_ADJUSTED_LANE = "RISK_ADJUSTED"


PARAMETER_VARIANT_OVERRIDES: dict[str, list[tuple[str, dict[str, Any]]]] = {
    "dual_ma": [
        ("fast", {"fast_window": 10, "slow_window": 50}),
        ("balanced", {"fast_window": 20, "slow_window": 80}),
        ("slow", {"fast_window": 40, "slow_window": 150}),
    ],
    "bollinger": [
        ("responsive", {"window": 20, "std_mult": 1.5}),
        ("balanced", {"window": 20, "std_mult": 2.0}),
        ("wide", {"window": 30, "std_mult": 2.2}),
    ],
    "macd": [
        ("fast", {"fast": 8, "slow": 21, "signal": 5}),
        ("classic", {"fast": 12, "slow": 26, "signal": 9}),
        ("slow", {"fast": 19, "slow": 39, "signal": 9}),
    ],
    "rsi": [
        ("fast", {"window": 10, "oversold": 30, "overbought": 70}),
        ("classic", {"window": 14, "oversold": 30, "overbought": 70}),
        ("slow", {"window": 21, "oversold": 35, "overbought": 65}),
    ],
    "momentum": [
        ("short", {"window": 20, "threshold": 0.015}),
        ("medium", {"window": 60, "threshold": 0.03}),
        ("long", {"window": 120, "threshold": 0.06}),
    ],
    "livermore": [
        ("fast", {"pivot_window": 40, "confirm_pct": 0.004}),
        ("classic", {"pivot_window": 60, "confirm_pct": 0.006}),
        ("strict", {"pivot_window": 100, "confirm_pct": 0.01}),
    ],
    "turtle": [
        ("short", {"entry_window": 20, "exit_window": 10}),
        ("classic", {"entry_window": 55, "exit_window": 20}),
        ("long", {"entry_window": 100, "exit_window": 40}),
    ],
    "darvas": [
        ("fast", {"box_window": 30, "confirm_pct": 0.003}),
        ("balanced", {"box_window": 60, "confirm_pct": 0.006}),
        ("strict", {"box_window": 120, "confirm_pct": 0.01}),
    ],
    "volume_trend": [
        ("responsive", {"trend_window": 80, "fast_window": 40, "breakout_window": 20, "exit_window": 10, "volume_window": 20, "volume_ratio": 1.0}),
        ("balanced", {"trend_window": 100, "fast_window": 50, "breakout_window": 20, "exit_window": 10, "volume_window": 20, "volume_ratio": 1.1}),
        ("strict", {"trend_window": 150, "fast_window": 50, "breakout_window": 55, "exit_window": 20, "volume_window": 30, "volume_ratio": 1.25}),
    ],
    "squeeze_breakout": [
        ("responsive", {"atr_short_window": 5, "atr_long_window": 30, "volume_short_window": 5, "volume_long_window": 30, "squeeze_atr_ratio": 0.65, "volume_contraction_ratio": 0.80, "breakout_window": 15, "range_expansion_ratio": 1.30, "volume_expansion_ratio": 1.20, "trend_window": 80, "exit_window": 10, "max_breakout_atr": 2.0, "atr_stop_mult": 2.0}),
        ("balanced", {"atr_short_window": 10, "atr_long_window": 50, "volume_short_window": 10, "volume_long_window": 50, "squeeze_atr_ratio": 0.70, "volume_contraction_ratio": 0.75, "breakout_window": 20, "range_expansion_ratio": 1.40, "volume_expansion_ratio": 1.35, "trend_window": 100, "exit_window": 15, "max_breakout_atr": 1.75, "atr_stop_mult": 2.5}),
        ("strict", {"atr_short_window": 10, "atr_long_window": 60, "volume_short_window": 10, "volume_long_window": 60, "squeeze_atr_ratio": 0.60, "volume_contraction_ratio": 0.70, "breakout_window": 30, "range_expansion_ratio": 1.60, "volume_expansion_ratio": 1.50, "trend_window": 150, "exit_window": 20, "max_breakout_atr": 1.50, "atr_stop_mult": 3.0}),
    ],
}


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def _median(rows: list[dict[str, Any]], key: str, default: float = 0.0) -> float:
    values = [_number(row.get(key), default) for row in rows]
    return float(median(values)) if values else default


def _finite_metrics(cell: dict[str, Any], fields: tuple[str, ...]) -> bool:
    for field in fields:
        value = cell.get(field)
        if field.endswith("_trade_count"):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return False
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if not math.isfinite(float(value)):
            return False
    return True


def build_parameter_variants(strategy_id: str, base_params: dict[str, Any]) -> list[dict[str, Any]]:
    clean_id = str(strategy_id or "").strip().lower()
    variants: list[dict[str, Any]] = []
    for label, overrides in PARAMETER_VARIANT_OVERRIDES.get(clean_id, [("default", {})]):
        params = {**dict(base_params or {}), **dict(overrides)}
        param_hash = canonical_hash(params)
        variants.append({
            "strategy_id": clean_id,
            "variant_label": label,
            "variant_id": f"{clean_id}:{label}:{param_hash[:10]}",
            "params": params,
            "param_hash": param_hash,
        })
    return variants


def parameter_variant_trial_count(strategy_ids: list[str] | Any) -> int:
    """Count the frozen grid trials without using market or result data."""

    if not isinstance(strategy_ids, list) or not strategy_ids:
        raise ValueError("strategy_trial_count_strategy_ids_invalid")
    normalized: list[str] = []
    for value in strategy_ids:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("strategy_trial_count_strategy_id_invalid")
        strategy_id = value.strip().lower()
        if strategy_id in normalized:
            raise ValueError("strategy_trial_count_strategy_id_duplicate")
        normalized.append(strategy_id)
    count = sum(len(build_parameter_variants(strategy_id, {})) for strategy_id in normalized)
    if count < 1:
        raise ValueError("strategy_trial_count_empty")
    return count


def build_legacy_parameter_stability_snapshot_v1(
    rankings: list[dict[str, Any]],
    *,
    near_best_fraction: float = 0.25,
    minimum_absolute_gap: float = 1.0,
) -> dict[str, Any]:
    """Reproduce historical v1 parameter-stability evidence byte for byte.

    V1 grouped variants by score distance only.  It did not prove that the
    near-best variants were eligible or adjacent in the declared grid, so it
    must not be used for new reports.  The implementation remains available
    solely to verify already-issued v1 evidence without changing its hash.
    """
    safe_fraction = min(max(float(near_best_fraction), 0.0), 1.0)
    safe_gap = max(float(minimum_absolute_gap), 0.0)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rankings if isinstance(rankings, list) else []:
        if not isinstance(row, dict):
            continue
        strategy_id = str(row.get("strategy_id") or "").strip().lower()
        if strategy_id:
            grouped.setdefault(strategy_id, []).append(row)

    strategies: list[dict[str, Any]] = []
    for strategy_id in sorted(grouped):
        rows = grouped[strategy_id]
        scored = [
            row for row in rows
            if math.isfinite(_number(row.get("adjusted_score"), float("nan")))
        ]
        eligible = [row for row in scored if row.get("eligible_for_test") is True]
        if not scored:
            strategies.append({
                "strategy_id": strategy_id,
                "status": "BLOCK",
                "variant_count": len(rows),
                "scored_variant_count": 0,
                "eligible_variant_count": 0,
                "near_best_variant_count": 0,
                "near_best_variant_ids": [],
                "best_variant_id": "",
                "best_adjusted_score": None,
                "median_adjusted_score": None,
                "peak_only": False,
                "blockers": ["parameter_stability_no_finite_scores"],
            })
            continue
        ordered = sorted(
            scored,
            key=lambda row: _number(row.get("adjusted_score"), float("-inf")),
            reverse=True,
        )
        best = _number(ordered[0].get("adjusted_score"), float("nan"))
        threshold = max(abs(best) * safe_fraction, safe_gap)
        near_best = [
            row for row in ordered
            if best - _number(row.get("adjusted_score"), float("-inf")) <= threshold
        ]
        best_id = str(ordered[0].get("variant_id") or "")
        near_ids = [str(row.get("variant_id") or "") for row in near_best]
        status = "PASS"
        blockers: list[str] = []
        if len(scored) < 3:
            status = "NOT_ENOUGH_VARIANTS"
            blockers.append(f"parameter_stability_variants:{len(scored)}<3")
        elif len(eligible) < 2:
            status = "REVIEW"
            blockers.append(f"parameter_stability_eligible_variants:{len(eligible)}<2")
        elif len(near_best) < 2:
            status = "REVIEW"
            blockers.append("parameter_stability_peak_without_plateau")
        elif best <= 0:
            status = "REVIEW"
            blockers.append("parameter_stability_best_score_not_positive")
        strategies.append({
            "strategy_id": strategy_id,
            "status": status,
            "variant_count": len(rows),
            "scored_variant_count": len(scored),
            "eligible_variant_count": len(eligible),
            "near_best_variant_count": len(near_best),
            "near_best_variant_ids": near_ids,
            "best_variant_id": best_id,
            "best_adjusted_score": round(best, 6),
            "median_adjusted_score": round(_median(scored, "adjusted_score", 0.0), 6),
            "near_best_gap": round(threshold, 6),
            "peak_only": len(near_best) == 1,
            "blockers": blockers,
        })

    statuses = {str(row.get("status") or "BLOCK") for row in strategies}
    if not strategies:
        status = "NOT_CHECKED"
    elif "BLOCK" in statuses:
        status = "BLOCK"
    elif "REVIEW" in statuses:
        status = "REVIEW"
    elif "NOT_ENOUGH_VARIANTS" in statuses:
        status = "NOT_ENOUGH_VARIANTS"
    else:
        status = "PASS"
    return {
        "schema_version": "strategy-parameter-plateau-v1",
        "status": status,
        "basis": "VALIDATION_ADJUSTED_SCORE_PLATEAU",
        "near_best_fraction": safe_fraction,
        "minimum_absolute_gap": safe_gap,
        "strategies": strategies,
        "descriptive_only": True,
        "parameter_selection_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "blockers": [
            blocker
            for row in strategies
            for blocker in (row.get("blockers") or [])
        ],
    }


def build_parameter_stability_snapshot(
    rankings: list[dict[str, Any]],
    *,
    frozen_variants: list[dict[str, Any]] | None = None,
    near_best_fraction: float = 0.25,
    minimum_absolute_gap: float = 1.0,
) -> dict[str, Any]:
    """Project rankings onto the variant sequence frozen in the batch spec.

    The sequence, rather than today's global strategy defaults, defines the
    topology so historical evidence cannot drift when code changes later.  The
    best scored point must itself be eligible and must have a directly adjacent
    eligible near-best point.  Non-adjacent endpoints and ineligible points do
    not form a plateau.  This remains descriptive only and never reruns data,
    selects parameters, or grants execution authority.
    """
    safe_fraction = min(max(float(near_best_fraction), 0.0), 1.0)
    safe_gap = max(float(minimum_absolute_gap), 0.0)
    ranking_rows = [dict(row) for row in rankings if isinstance(row, dict)] if isinstance(rankings, list) else []
    frozen_rows = [dict(row) for row in frozen_variants if isinstance(row, dict)] if isinstance(frozen_variants, list) else []
    if not frozen_rows:
        return {
            "schema_version": "strategy-parameter-plateau-v2",
            "status": "BLOCK",
            "basis": "ELIGIBLE_VALIDATION_ADJUSTED_SCORE_ADJACENCY_PLATEAU",
            "topology_basis": "FROZEN_VARIANT_SEQUENCE_ADJACENCY",
            "numeric_parameter_distance_checked": False,
            "near_best_fraction": safe_fraction,
            "minimum_absolute_gap": safe_gap,
            "strategies": [],
            "descriptive_only": True,
            "parameter_selection_allowed": False,
            "historical_rerun_recommended": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
            "blockers": ["parameter_stability_frozen_topology_missing"],
        }

    frozen_strategy_order = list(dict.fromkeys(
        str(row.get("strategy_id") or "").strip().lower()
        for row in frozen_rows
        if str(row.get("strategy_id") or "").strip()
    ))
    ranking_strategy_ids = {
        str(row.get("strategy_id") or "").strip().lower()
        for row in ranking_rows
        if str(row.get("strategy_id") or "").strip()
    }
    strategy_order = [
        *frozen_strategy_order,
        *sorted(ranking_strategy_ids - set(frozen_strategy_order)),
    ]

    strategies: list[dict[str, Any]] = []
    for strategy_id in strategy_order:
        rows = [
            row for row in ranking_rows
            if str(row.get("strategy_id") or "").strip().lower() == strategy_id
        ]
        frozen = [
            row for row in frozen_rows
            if str(row.get("strategy_id") or "").strip().lower() == strategy_id
        ]
        topology_ids = [str(row.get("variant_id") or "").strip() for row in frozen]
        topology_index = {variant_id: index for index, variant_id in enumerate(topology_ids) if variant_id}
        topology_edges = [
            {
                "left_variant_id": topology_ids[index],
                "right_variant_id": topology_ids[index + 1],
            }
            for index in range(max(len(topology_ids) - 1, 0))
        ]
        ranking_ids = [str(row.get("variant_id") or "").strip() for row in rows]
        frozen_duplicates = sorted({item for item in topology_ids if item and topology_ids.count(item) > 1})
        ranking_duplicates = sorted({item for item in ranking_ids if item and ranking_ids.count(item) > 1})
        missing_ranking_ids = [item for item in topology_ids if item and item not in set(ranking_ids)]
        unexpected_ranking_ids = [item for item in ranking_ids if item and item not in set(topology_ids)]
        identity_mismatches: list[str] = []
        frozen_by_id = {str(row.get("variant_id") or ""): row for row in frozen}
        ranking_by_id = {str(row.get("variant_id") or ""): row for row in rows}
        for variant_id in sorted(set(frozen_by_id) & set(ranking_by_id)):
            frozen_row = frozen_by_id[variant_id]
            ranking_row = ranking_by_id[variant_id]
            if str(ranking_row.get("strategy_id") or "").strip().lower() != strategy_id:
                identity_mismatches.append(f"{variant_id}:strategy_id")
            if str(ranking_row.get("param_hash") or "") != str(frozen_row.get("param_hash") or ""):
                identity_mismatches.append(f"{variant_id}:param_hash")
            if ranking_row.get("params") != frozen_row.get("params"):
                identity_mismatches.append(f"{variant_id}:params")
            if str(ranking_row.get("variant_label") or "") != str(frozen_row.get("variant_label") or ""):
                identity_mismatches.append(f"{variant_id}:variant_label")
        scored = [
            row for row in rows
            if math.isfinite(_number(row.get("adjusted_score"), float("nan")))
        ]
        eligible = [
            row for row in scored
            if str(row.get("status") or "").upper() == "PASS"
            and row.get("eligible_for_test") is True
        ]
        ordered = sorted(
            scored,
            key=lambda row: (
                -_number(row.get("adjusted_score"), float("-inf")),
                topology_index.get(str(row.get("variant_id") or ""), len(topology_ids)),
            ),
        )
        best = _number(ordered[0].get("adjusted_score"), float("nan")) if ordered else float("nan")
        threshold = max(abs(best) * safe_fraction, safe_gap) if math.isfinite(best) else safe_gap
        near_best_scored = [
            row for row in ordered
            if best - _number(row.get("adjusted_score"), float("-inf")) <= threshold
        ] if ordered else []
        best_row = ordered[0] if ordered else {}
        best_id = str(best_row.get("variant_id") or "")
        best_eligible = best_row in eligible
        near_best_eligible = [row for row in near_best_scored if row in eligible]
        best_position = topology_index.get(best_id, -1)
        adjacent_ids = {
            topology_ids[index]
            for index in (best_position - 1, best_position + 1)
            if 0 <= index < len(topology_ids)
        }
        adjacent_near_best = [
            row for row in near_best_eligible
            if row is not best_row and str(row.get("variant_id") or "") in adjacent_ids
        ]
        blockers: list[str] = []
        status = "PASS"
        topology_invalid = (
            not frozen
            or any(not item for item in topology_ids)
            or any(not item for item in ranking_ids)
            or bool(frozen_duplicates)
            or bool(ranking_duplicates)
            or bool(missing_ranking_ids)
            or bool(unexpected_ranking_ids)
            or bool(identity_mismatches)
        )
        if topology_invalid:
            status = "BLOCK"
            if not frozen:
                blockers.append("parameter_stability_strategy_topology_missing")
            if any(not item for item in topology_ids + ranking_ids):
                blockers.append("parameter_stability_variant_id_missing")
            if frozen_duplicates:
                blockers.append("parameter_stability_frozen_variant_duplicate")
            if ranking_duplicates:
                blockers.append("parameter_stability_ranking_variant_duplicate")
            if missing_ranking_ids:
                blockers.append("parameter_stability_ranking_coverage_missing")
            if unexpected_ranking_ids:
                blockers.append("parameter_stability_ranking_variant_unknown")
            if identity_mismatches:
                blockers.append("parameter_stability_ranking_identity_mismatch")
        elif len(frozen) < 3 or len(scored) < 3:
            status = "NOT_ENOUGH_VARIANTS"
            blockers.append(f"parameter_stability_scored_topology_variants:{len(scored)}<3")
        elif not best_eligible:
            status = "REVIEW"
            blockers.append("parameter_stability_best_variant_ineligible")
        elif not adjacent_near_best:
            status = "REVIEW"
            blockers.append("parameter_stability_peak_without_adjacent_plateau")
        elif best <= 0:
            status = "REVIEW"
            blockers.append("parameter_stability_best_score_not_positive")

        near_scored_ids = [str(row.get("variant_id") or "") for row in near_best_scored]
        near_eligible_ids = [str(row.get("variant_id") or "") for row in near_best_eligible]
        adjacent_eligible_ids = [str(row.get("variant_id") or "") for row in adjacent_near_best]
        connected_plateau_ids: list[str] = []
        if best_eligible and best_position >= 0:
            near_eligible_id_set = set(near_eligible_ids)
            left = best_position
            right = best_position
            while left - 1 >= 0 and topology_ids[left - 1] in near_eligible_id_set:
                left -= 1
            while right + 1 < len(topology_ids) and topology_ids[right + 1] in near_eligible_id_set:
                right += 1
            connected_plateau_ids = topology_ids[left:right + 1]
        strategies.append({
            "strategy_id": strategy_id,
            "status": status,
            "variant_count": len(rows),
            "frozen_variant_count": len(frozen),
            "scored_variant_count": len(scored),
            "eligible_variant_count": len(eligible),
            "topology_complete": not topology_invalid,
            "topology_variant_ids": topology_ids,
            "topology_edges": topology_edges,
            "missing_ranking_variant_ids": missing_ranking_ids,
            "unexpected_ranking_variant_ids": unexpected_ranking_ids,
            "identity_mismatches": identity_mismatches,
            "near_best_scored_variant_count": len(near_best_scored),
            "near_best_scored_variant_ids": near_scored_ids,
            "near_best_eligible_variant_count": len(near_best_eligible),
            "near_best_eligible_variant_ids": near_eligible_ids,
            "adjacent_near_best_variant_count": len(adjacent_near_best),
            "adjacent_near_best_variant_ids": adjacent_eligible_ids,
            "connected_plateau_ids": connected_plateau_ids,
            "plateau_width": len(connected_plateau_ids),
            "best_variant_id": best_id,
            "best_variant_eligible": best_eligible,
            "best_adjusted_score": round(best, 6) if math.isfinite(best) else None,
            "median_adjusted_score": round(_median(eligible, "adjusted_score", 0.0), 6) if eligible else None,
            "near_best_gap": round(threshold, 6),
            "peak_only": not adjacent_near_best,
            "blockers": blockers,
        })

    statuses = {str(row.get("status") or "BLOCK") for row in strategies}
    if not strategies:
        status = "NOT_CHECKED"
    elif "BLOCK" in statuses:
        status = "BLOCK"
    elif "REVIEW" in statuses:
        status = "REVIEW"
    elif "NOT_ENOUGH_VARIANTS" in statuses:
        status = "NOT_ENOUGH_VARIANTS"
    else:
        status = "PASS"
    return {
        "schema_version": "strategy-parameter-plateau-v2",
        "status": status,
        "basis": "ELIGIBLE_VALIDATION_ADJUSTED_SCORE_ADJACENCY_PLATEAU",
        "topology_basis": "FROZEN_VARIANT_SEQUENCE_ADJACENCY",
        "numeric_parameter_distance_checked": False,
        "near_best_fraction": safe_fraction,
        "minimum_absolute_gap": safe_gap,
        "strategies": strategies,
        "descriptive_only": True,
        "parameter_selection_allowed": False,
        "historical_rerun_recommended": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "blockers": [
            blocker
            for row in strategies
            for blocker in (row.get("blockers") or [])
        ],
    }


def aggregate_validation_variant(
    variant: dict[str, Any],
    cells: list[dict[str, Any]],
    *,
    required_symbols: int,
    total_variant_trials: int,
) -> dict[str, Any]:
    usable = [
        cell for cell in cells
        if cell.get("dataset_status") == "PASS"
        and cell.get("train_ok") is True
        and cell.get("validation_ok") is True
        and _finite_metrics(cell, (
            "train_return_pct",
            "validation_return_pct",
            "validation_excess_return_pct",
            "validation_trade_count",
            "validation_max_drawdown_pct",
            "validation_sharpe",
            "validation_drawdown_improvement_pct",
            "validation_sharpe_excess",
            "validation_risk_efficiency_excess",
        ))
    ]
    minimum_positive = max(1, math.ceil(required_symbols * 0.60))
    train_positive = [cell for cell in usable if _number(cell.get("train_return_pct")) > 0]
    validation_positive = [cell for cell in usable if _number(cell.get("validation_return_pct")) > 0]
    excess_positive = [cell for cell in usable if _number(cell.get("validation_excess_return_pct")) > 0]
    drawdown_improved = [cell for cell in usable if _number(cell.get("validation_drawdown_improvement_pct")) > 0]
    sharpe_excess_positive = [cell for cell in usable if _number(cell.get("validation_sharpe_excess")) > 0]
    risk_efficiency_positive = [cell for cell in usable if _number(cell.get("validation_risk_efficiency_excess")) > 0]
    fold_pass = [cell for cell in usable if cell.get("fold_stability_status") == "PASS"]
    cost_pass = [cell for cell in usable if cell.get("cost_sensitivity_status") == "PASS"]
    lookahead_pass = [cell for cell in usable if cell.get("lookahead_status") == "PASS"]
    total_trades = sum(int(cell.get("validation_trade_count") or 0) for cell in usable)
    worst_drawdown = max((_number(cell.get("validation_max_drawdown_pct"), 100.0) for cell in usable), default=100.0)
    median_train_return = _median(usable, "train_return_pct")
    median_validation_return = _median(usable, "validation_return_pct")
    median_excess = _median(usable, "validation_excess_return_pct")
    median_sharpe = _median(usable, "validation_sharpe")
    median_drawdown_improvement = _median(usable, "validation_drawdown_improvement_pct")
    median_sharpe_excess = _median(usable, "validation_sharpe_excess")
    median_risk_efficiency_excess = _median(usable, "validation_risk_efficiency_excess")
    raw_score = median_excess + median_validation_return * 0.15 + median_sharpe * 0.5 - worst_drawdown * 0.12
    raw_trial_penalty = 0.75 * math.sqrt(2.0 * math.log(max(int(total_variant_trials), 2)))
    raw_adjusted_score = raw_score - raw_trial_penalty
    risk_score = (
        median_validation_return * 0.25
        + median_sharpe_excess * 2.0
        + median_risk_efficiency_excess
        + median_drawdown_improvement * 0.15
        - worst_drawdown * 0.10
        - abs(min(median_excess, 0.0)) * 0.25
    )
    risk_trial_penalty = 0.75 * math.sqrt(2.0 * math.log(max(int(total_variant_trials) * 2, 2)))
    risk_adjusted_score = risk_score - risk_trial_penalty
    common_blockers: list[str] = []
    if len(usable) < required_symbols:
        common_blockers.append(f"usable_symbols:{len(usable)}<{required_symbols}")
    if len(train_positive) < minimum_positive:
        common_blockers.append(f"train_positive_symbols:{len(train_positive)}<{minimum_positive}")
    if len(validation_positive) < minimum_positive:
        common_blockers.append(f"validation_positive_symbols:{len(validation_positive)}<{minimum_positive}")
    if len(fold_pass) < minimum_positive:
        common_blockers.append(f"fold_stability_pass_symbols:{len(fold_pass)}<{minimum_positive}")
    if len(cost_pass) < max(1, math.ceil(required_symbols * 0.75)):
        common_blockers.append("cost_sensitivity_cross_symbol_block")
    if len(lookahead_pass) < required_symbols:
        common_blockers.append(f"lookahead_pass_symbols:{len(lookahead_pass)}<{required_symbols}")
    if total_trades < required_symbols * 2:
        common_blockers.append(f"validation_trades:{total_trades}<{required_symbols * 2}")
    if worst_drawdown >= 25:
        common_blockers.append(f"validation_worst_drawdown:{worst_drawdown:.2f}>=25")
    if median_train_return <= 0:
        common_blockers.append("median_train_return_not_positive")

    raw_blockers: list[str] = []
    if len(excess_positive) < minimum_positive:
        raw_blockers.append(f"validation_excess_positive_symbols:{len(excess_positive)}<{minimum_positive}")
    if median_excess <= 0:
        raw_blockers.append("median_validation_excess_not_positive")
    if raw_adjusted_score <= 0:
        raw_blockers.append("multiple_trial_adjusted_score_not_positive")

    minimum_risk = max(1, math.ceil(required_symbols * 0.80))
    risk_blockers: list[str] = []
    if len(drawdown_improved) < minimum_risk:
        risk_blockers.append(f"drawdown_improved_symbols:{len(drawdown_improved)}<{minimum_risk}")
    if len(risk_efficiency_positive) < minimum_risk:
        risk_blockers.append(f"risk_efficiency_positive_symbols:{len(risk_efficiency_positive)}<{minimum_risk}")
    if len(sharpe_excess_positive) < minimum_positive:
        risk_blockers.append(f"sharpe_excess_positive_symbols:{len(sharpe_excess_positive)}<{minimum_positive}")
    if worst_drawdown >= 15:
        risk_blockers.append(f"risk_lane_worst_drawdown:{worst_drawdown:.2f}>=15")
    if median_validation_return < 2.0:
        risk_blockers.append(f"risk_lane_median_return:{median_validation_return:.2f}<2")
    if median_excess < -3.0:
        risk_blockers.append(f"risk_lane_median_raw_lag:{median_excess:.2f}<-3")
    if median_drawdown_improvement < 3.0:
        risk_blockers.append(f"median_drawdown_improvement:{median_drawdown_improvement:.2f}<3")
    if median_sharpe_excess <= 0:
        risk_blockers.append("median_sharpe_excess_not_positive")
    if median_risk_efficiency_excess <= 0:
        risk_blockers.append("median_risk_efficiency_excess_not_positive")
    if risk_adjusted_score <= 0:
        risk_blockers.append("multiple_trial_risk_adjusted_score_not_positive")

    raw_pass = not common_blockers and not raw_blockers
    risk_pass = not common_blockers and not risk_blockers
    selection_lane = RAW_EXCESS_LANE if raw_pass else RISK_ADJUSTED_LANE if risk_pass else "NONE"
    adjusted_score = raw_adjusted_score if raw_pass else risk_adjusted_score if risk_pass else max(raw_adjusted_score, risk_adjusted_score)
    blockers = [] if selection_lane != "NONE" else [
        *common_blockers,
        *[f"{RAW_EXCESS_LANE}:{item}" for item in raw_blockers],
        *[f"{RISK_ADJUSTED_LANE}:{item}" for item in risk_blockers],
    ]
    return {
        **variant,
        "status": "PASS" if not blockers else "BLOCK",
        "eligible_for_test": not blockers,
        "selection_lane": selection_lane,
        "required_symbols": required_symbols,
        "usable_symbols": len(usable),
        "train_positive_symbols": len(train_positive),
        "validation_positive_symbols": len(validation_positive),
        "validation_excess_positive_symbols": len(excess_positive),
        "validation_drawdown_improved_symbols": len(drawdown_improved),
        "validation_sharpe_excess_positive_symbols": len(sharpe_excess_positive),
        "validation_risk_efficiency_positive_symbols": len(risk_efficiency_positive),
        "fold_stability_pass_symbols": len(fold_pass),
        "cost_pass_symbols": len(cost_pass),
        "lookahead_pass_symbols": len(lookahead_pass),
        "validation_trade_count": total_trades,
        "validation_worst_drawdown_pct": round(worst_drawdown, 4),
        "median_train_return_pct": round(median_train_return, 4),
        "median_validation_return_pct": round(median_validation_return, 4),
        "median_validation_excess_return_pct": round(median_excess, 4),
        "median_validation_sharpe": round(median_sharpe, 4),
        "median_validation_drawdown_improvement_pct": round(median_drawdown_improvement, 4),
        "median_validation_sharpe_excess": round(median_sharpe_excess, 4),
        "median_validation_risk_efficiency_excess": round(median_risk_efficiency_excess, 6),
        "raw_score": round(raw_score, 4),
        "raw_multiple_trial_penalty": round(raw_trial_penalty, 4),
        "raw_adjusted_score": round(raw_adjusted_score, 4),
        "risk_adjusted_raw_score": round(risk_score, 4),
        "risk_adjusted_trial_penalty": round(risk_trial_penalty, 4),
        "risk_adjusted_score": round(risk_adjusted_score, 4),
        "multiple_trial_penalty": round(raw_trial_penalty if selection_lane == RAW_EXCESS_LANE else risk_trial_penalty, 4),
        "adjusted_score": round(adjusted_score, 4),
        "lane_blockers": {
            RAW_EXCESS_LANE: raw_blockers,
            RISK_ADJUSTED_LANE: risk_blockers,
        },
        "blockers": blockers,
    }


def freeze_validation_candidates(
    rankings: list[dict[str, Any]],
    *,
    max_candidates: int = 2,
) -> list[dict[str, Any]]:
    best_by_strategy: dict[str, dict[str, Any]] = {}
    for row in rankings:
        if not row.get("eligible_for_test"):
            continue
        strategy_id = str(row.get("strategy_id") or "")
        current = best_by_strategy.get(strategy_id)
        if current is None or _number(row.get("adjusted_score"), -1e9) > _number(current.get("adjusted_score"), -1e9):
            best_by_strategy[strategy_id] = row
    ordered = sorted(best_by_strategy.values(), key=lambda row: _number(row.get("adjusted_score"), -1e9), reverse=True)
    return [
        {
            "strategy_id": row["strategy_id"],
            "variant_id": row["variant_id"],
            "params": row["params"],
            "param_hash": row["param_hash"],
            "implementation_fingerprint": row.get("implementation_fingerprint", ""),
            "risk_profile": row.get("risk_profile", {}),
            "risk": row.get("risk", {}),
            "risk_hash": row.get("risk_hash", ""),
            "validation_adjusted_score": row.get("adjusted_score"),
            "selection_lane": row.get("selection_lane", RAW_EXCESS_LANE),
            "frozen_before_test": True,
        }
        for row in ordered[:max(0, int(max_candidates))]
    ]


def aggregate_frozen_test(
    candidate: dict[str, Any],
    cells: list[dict[str, Any]],
    *,
    required_symbols: int,
) -> dict[str, Any]:
    selected_lane = str(candidate.get("selection_lane") or RAW_EXCESS_LANE).upper()
    required_metrics = [
        "test_return_pct",
        "test_excess_return_pct",
        "test_trade_count",
        "test_max_drawdown_pct",
    ]
    if selected_lane == RISK_ADJUSTED_LANE:
        required_metrics.extend([
            "test_drawdown_improvement_pct",
            "test_sharpe_excess",
            "test_risk_efficiency_excess",
        ])
    usable = [
        cell for cell in cells
        if cell.get("dataset_status") == "PASS"
        and cell.get("test_ok") is True
        and _finite_metrics(cell, tuple(required_metrics))
    ]
    minimum_positive = max(1, math.ceil(required_symbols * 0.60))
    positive = [cell for cell in usable if _number(cell.get("test_return_pct")) > 0]
    excess_positive = [cell for cell in usable if _number(cell.get("test_excess_return_pct")) > 0]
    drawdown_improved = [cell for cell in usable if _number(cell.get("test_drawdown_improvement_pct")) > 0]
    sharpe_excess_positive = [cell for cell in usable if _number(cell.get("test_sharpe_excess")) > 0]
    risk_efficiency_positive = [cell for cell in usable if _number(cell.get("test_risk_efficiency_excess")) > 0]
    cost_pass = [cell for cell in usable if cell.get("test_cost_status") == "PASS"]
    total_trades = sum(int(cell.get("test_trade_count") or 0) for cell in usable)
    worst_drawdown = max((_number(cell.get("test_max_drawdown_pct"), 100.0) for cell in usable), default=100.0)
    median_return = _median(usable, "test_return_pct")
    median_excess = _median(usable, "test_excess_return_pct")
    median_drawdown_improvement = _median(usable, "test_drawdown_improvement_pct")
    median_sharpe_excess = _median(usable, "test_sharpe_excess")
    median_risk_efficiency_excess = _median(usable, "test_risk_efficiency_excess")
    common_blockers: list[str] = []
    if len(usable) < required_symbols:
        common_blockers.append(f"usable_test_symbols:{len(usable)}<{required_symbols}")
    if len(positive) < minimum_positive:
        common_blockers.append(f"test_positive_symbols:{len(positive)}<{minimum_positive}")
    if len(cost_pass) < max(1, math.ceil(required_symbols * 0.75)):
        common_blockers.append("test_cost_sensitivity_cross_symbol_block")
    if total_trades < required_symbols * 2:
        common_blockers.append(f"test_trades:{total_trades}<{required_symbols * 2}")
    if worst_drawdown >= 25:
        common_blockers.append(f"test_worst_drawdown:{worst_drawdown:.2f}>=25")

    lane_blockers: list[str] = []
    if selected_lane == RAW_EXCESS_LANE:
        if len(excess_positive) < minimum_positive:
            lane_blockers.append(f"test_excess_positive_symbols:{len(excess_positive)}<{minimum_positive}")
        if median_excess <= 0:
            lane_blockers.append("median_test_excess_not_positive")
    elif selected_lane == RISK_ADJUSTED_LANE:
        minimum_risk = max(1, math.ceil(required_symbols * 0.80))
        if len(drawdown_improved) < minimum_risk:
            lane_blockers.append(f"test_drawdown_improved_symbols:{len(drawdown_improved)}<{minimum_risk}")
        if len(risk_efficiency_positive) < minimum_risk:
            lane_blockers.append(f"test_risk_efficiency_positive_symbols:{len(risk_efficiency_positive)}<{minimum_risk}")
        if len(sharpe_excess_positive) < minimum_positive:
            lane_blockers.append(f"test_sharpe_excess_positive_symbols:{len(sharpe_excess_positive)}<{minimum_positive}")
        if worst_drawdown >= 15:
            lane_blockers.append(f"risk_lane_test_worst_drawdown:{worst_drawdown:.2f}>=15")
        if median_return < 2.0:
            lane_blockers.append(f"risk_lane_median_test_return:{median_return:.2f}<2")
        if median_excess < -3.0:
            lane_blockers.append(f"risk_lane_median_test_raw_lag:{median_excess:.2f}<-3")
        if median_drawdown_improvement < 3.0:
            lane_blockers.append(f"median_test_drawdown_improvement:{median_drawdown_improvement:.2f}<3")
        if median_sharpe_excess <= 0:
            lane_blockers.append("median_test_sharpe_excess_not_positive")
        if median_risk_efficiency_excess <= 0:
            lane_blockers.append("median_test_risk_efficiency_excess_not_positive")
    else:
        lane_blockers.append(f"unknown_selection_lane:{selected_lane}")
    blockers = [*common_blockers, *lane_blockers]
    return {
        **candidate,
        "status": "PASS" if not blockers else "BLOCK",
        "eligible_for_holdout": not blockers,
        "test_lane": selected_lane,
        "usable_test_symbols": len(usable),
        "test_positive_symbols": len(positive),
        "test_excess_positive_symbols": len(excess_positive),
        "test_drawdown_improved_symbols": len(drawdown_improved),
        "test_sharpe_excess_positive_symbols": len(sharpe_excess_positive),
        "test_risk_efficiency_positive_symbols": len(risk_efficiency_positive),
        "test_cost_pass_symbols": len(cost_pass),
        "test_trade_count": total_trades,
        "test_worst_drawdown_pct": round(worst_drawdown, 4),
        "median_test_return_pct": round(median_return, 4),
        "median_test_excess_return_pct": round(median_excess, 4),
        "median_test_drawdown_improvement_pct": round(median_drawdown_improvement, 4),
        "median_test_sharpe_excess": round(median_sharpe_excess, 4),
        "median_test_risk_efficiency_excess": round(median_risk_efficiency_excess, 6),
        "blockers": blockers,
    }


def aggregate_holdout_confirmation(
    candidate: dict[str, Any],
    cells: list[dict[str, Any]],
    *,
    required_symbols: int,
) -> dict[str, Any]:
    normalized = [{
        **cell,
        "test_ok": cell.get("test_ok") is True or cell.get("baseline_ok") is True,
        "test_cost_status": cell.get("cost_sensitivity_status", "BLOCK"),
    } for cell in cells]
    result = aggregate_frozen_test(candidate, normalized, required_symbols=required_symbols)
    temporal_pass = sum(cell.get("temporal_status") == "PASS" for cell in normalized)
    walk_forward_pass = sum(cell.get("walk_forward_status") == "PASS" for cell in normalized)
    lookahead_pass = sum(cell.get("lookahead_status") == "PASS" for cell in normalized)
    blockers = list(result.get("blockers") or [])
    if temporal_pass < required_symbols:
        blockers.append(f"holdout_temporal_pass:{temporal_pass}<{required_symbols}")
    if walk_forward_pass < required_symbols:
        blockers.append(f"holdout_walk_forward_pass:{walk_forward_pass}<{required_symbols}")
    if lookahead_pass < required_symbols:
        blockers.append(f"holdout_lookahead_pass:{lookahead_pass}<{required_symbols}")
    return {
        **result,
        "status": "PASS" if not blockers else "BLOCK",
        "forward_candidate": not blockers,
        "holdout_lane": result.get("test_lane"),
        "holdout_symbols": len(normalized),
        "holdout_temporal_pass_symbols": temporal_pass,
        "holdout_walk_forward_pass_symbols": walk_forward_pass,
        "holdout_lookahead_pass_symbols": lookahead_pass,
        "blockers": list(dict.fromkeys(blockers)),
        "paper_authorized": False,
        "live_order_allowed": False,
    }
