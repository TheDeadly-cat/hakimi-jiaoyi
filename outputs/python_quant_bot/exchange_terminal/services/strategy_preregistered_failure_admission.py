from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .strategy_hypothesis_preregistration import (
    MECHANISM_FAILURE_EVIDENCE_STAGE_V2,
    MECHANISM_FAILURE_METRICS_V2,
    MECHANISM_FAILURE_OPERATORS_V2,
    MECHANISM_FAILURE_REQUIRED_ACTION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    verify_strategy_hypothesis_preregistration,
)
from .strategy_research import (
    aggregate_validation_variant,
    build_parameter_stability_snapshot,
    canonical_hash,
    freeze_validation_candidates,
)
from .strategy_research_search_lineage import (
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
    verify_strategy_research_registry_anchor,
    verify_strategy_research_search_lineage,
)


PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION = 12
MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION = 13
STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION = (
    "strategy-preregistered-failure-admission-v1"
)
STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V2 = (
    "strategy-preregistered-failure-admission-v2"
)
STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3 = (
    "strategy-preregistered-failure-admission-v3"
)
_DEVELOPMENT_STAGE = "DEVELOPMENT_SELECTION"
_BLOCK_ACTION = "BLOCK_RESEARCH"
_SUPPORTED_CONDITIONS = {
    "parameter_plateau_absent",
    "cost_break_even_lost",
    "fixed_parameter_time_slice_instability",
}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sequence(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _native_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _parameter_condition(
    strategy_id: str,
    parameter_stability: dict[str, Any],
) -> tuple[bool, list[str]]:
    rows = [
        row for row in _sequence(parameter_stability.get("strategies"))
        if isinstance(row, dict)
        and str(row.get("strategy_id") or "").strip().lower() == strategy_id
    ]
    if len(rows) != 1:
        return False, ["parameter_plateau_strategy_evidence_missing_or_duplicate"]
    row = rows[0]
    plateau_width = _native_nonnegative_int(row.get("plateau_width"))
    adjacent = _native_nonnegative_int(row.get("adjacent_near_best_variant_count"))
    best_score = _finite(row.get("best_adjusted_score"))
    passed = (
        parameter_stability.get("schema_version") == "strategy-parameter-plateau-v2"
        and row.get("status") == "PASS"
        and plateau_width is not None
        and plateau_width >= 2
        and adjacent is not None
        and adjacent >= 1
        and row.get("peak_only") is False
        and best_score is not None
        and best_score > 0
    )
    blockers = [str(item) for item in _sequence(row.get("blockers")) if str(item)]
    if not passed and not blockers:
        blockers.append("parameter_plateau_not_passed")
    return passed, blockers


def _cost_condition(cells: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if not cells:
        return False, ["selection_cost_evidence_missing"]
    for cell in cells:
        evidence = _mapping(cell.get("cost_sensitivity"))
        worst_return = _finite(evidence.get("worst_return_pct"))
        passed = (
            cell.get("cost_sensitivity_status") == "PASS"
            and evidence.get("status") == "PASS"
            and evidence.get("verification_status") == "PASS"
            and evidence.get("stage") == _DEVELOPMENT_STAGE
            and evidence.get("break_even_preserved") is True
            and worst_return is not None
            and worst_return > 0
        )
        if not passed:
            blockers.extend(
                str(item) for item in _sequence(evidence.get("blockers")) if str(item)
            )
            blockers.append(f"cost_break_even_not_preserved:{cell.get('symbol') or 'UNKNOWN'}")
    return not blockers, list(dict.fromkeys(blockers))


def _fixed_slice_condition(cells: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if not cells:
        return False, ["selection_fixed_slice_evidence_missing"]
    for cell in cells:
        evidence = _mapping(cell.get("fold_stability"))
        usable = _native_nonnegative_int(evidence.get("usable_folds"))
        positive = _native_nonnegative_int(evidence.get("positive_folds"))
        passed = (
            cell.get("fold_stability_status") == "PASS"
            and evidence.get("schema_version") == "strategy-fixed-chronological-slice-evidence-v2"
            and evidence.get("verification_status") == "PASS"
            and evidence.get("status") == "PASS"
            and evidence.get("parameters_refit_per_fold") is False
            and evidence.get("walk_forward_optimization_claim_allowed") is False
            and usable is not None
            and usable > 0
            and positive is not None
            and positive > 0
        )
        if not passed:
            blockers.extend(
                str(item) for item in _sequence(evidence.get("blockers")) if str(item)
            )
            blockers.append(f"fixed_parameter_slice_not_passed:{cell.get('symbol') or 'UNKNOWN'}")
    return not blockers, list(dict.fromkeys(blockers))


def _selection_cell_coverage_condition(
    cells: list[dict[str, Any]],
    required_symbols: list[str],
) -> tuple[bool, list[str]]:
    symbols = [str(cell.get("symbol") or "").strip().upper() for cell in cells]
    missing = [item for item in required_symbols if symbols.count(item) == 0]
    duplicate = [item for item in required_symbols if symbols.count(item) > 1]
    unexpected = sorted({item for item in symbols if item and item not in required_symbols})
    blockers: list[str] = []
    if not required_symbols:
        blockers.append("required_selection_symbols_missing")
    if any(not item for item in symbols):
        blockers.append("selection_cell_symbol_missing")
    if missing:
        blockers.append("selection_cell_required_symbol_missing:" + ",".join(missing))
    if duplicate:
        blockers.append("selection_cell_required_symbol_duplicate:" + ",".join(duplicate))
    if unexpected:
        blockers.append("selection_cell_symbol_unexpected:" + ",".join(unexpected))
    return not blockers, blockers


def build_strategy_preregistered_failure_admission(
    *,
    batch_spec: dict[str, Any] | Any,
    hypothesis_preregistration: dict[str, Any] | Any,
    parameter_stability: dict[str, Any] | Any,
    selection_cells: list[dict[str, Any]] | Any,
    validation_candidates: list[dict[str, Any]] | Any,
    total_variant_trials: int | None = None,
) -> dict[str, Any]:
    """Rebuild preregistered development BLOCK_RESEARCH conditions from evidence."""

    spec = _mapping(batch_spec)
    hypothesis = _mapping(hypothesis_preregistration)
    plateau = _mapping(parameter_stability)
    cells = [dict(item) for item in _sequence(selection_cells) if isinstance(item, dict)]
    candidates = [
        dict(item) for item in _sequence(validation_candidates) if isinstance(item, dict)
    ]
    frozen_variants = [
        dict(item) for item in _sequence(spec.get("variants")) if isinstance(item, dict)
    ]
    required_symbols = list(dict.fromkeys(
        str(item).strip().upper()
        for item in _sequence(spec.get("selection_symbols"))
        if isinstance(item, str) and item.strip()
    ))
    hypothesis_strategies = [
        str(item).strip().lower()
        for item in _sequence(hypothesis.get("strategy_ids"))
        if isinstance(item, str) and item.strip()
    ]
    raw_standard = _sequence(
        _mapping(hypothesis.get("failure_contract")).get("standard_conditions")
    )
    standard = [
        dict(item)
        for item in raw_standard
        if isinstance(item, dict)
        and item.get("evidence_stage") == _DEVELOPMENT_STAGE
        and item.get("required_action") == _BLOCK_ACTION
    ]
    standard_ids = [str(item.get("condition_id") or "") for item in standard]
    contract_blockers: list[str] = []
    effective_trial_count = len(frozen_variants)
    if total_variant_trials is not None:
        if (
            isinstance(total_variant_trials, bool)
            or not isinstance(total_variant_trials, int)
            or total_variant_trials < len(frozen_variants)
        ):
            contract_blockers.append("cumulative_variant_trial_count_invalid")
        else:
            effective_trial_count = total_variant_trials
    if (
        set(standard_ids) != _SUPPORTED_CONDITIONS
        or len(standard_ids) != len(_SUPPORTED_CONDITIONS)
    ):
        contract_blockers.append("preregistered_development_block_conditions_invalid")
    spec_strategies = [
        str(item).strip().lower()
        for item in _sequence(spec.get("strategies"))
        if isinstance(item, str) and item.strip()
    ]
    if hypothesis_strategies != spec_strategies:
        contract_blockers.append("hypothesis_strategy_binding_mismatch")

    recalculated_rankings = [
        aggregate_validation_variant(
            variant,
            [
                cell for cell in cells
                if str(cell.get("strategy_id") or "").strip().lower()
                == str(variant.get("strategy_id") or "").strip().lower()
                and str(cell.get("variant_id") or "") == str(variant.get("variant_id") or "")
            ],
            required_symbols=len(required_symbols),
            total_variant_trials=effective_trial_count,
        )
        for variant in frozen_variants
    ]
    recalculated_rankings.sort(
        key=lambda row: float(row.get("adjusted_score") or -1e9),
        reverse=True,
    )
    max_candidates = _native_nonnegative_int(spec.get("max_test_candidates"))
    if max_candidates is None or max_candidates < 1:
        contract_blockers.append("max_test_candidates_invalid")
        max_candidates = 0
    expected_candidates = freeze_validation_candidates(
        recalculated_rankings,
        max_candidates=max_candidates,
    )
    expected_plateau = build_parameter_stability_snapshot(
        recalculated_rankings,
        frozen_variants=frozen_variants,
    )
    if candidates != expected_candidates:
        contract_blockers.append("validation_candidates_development_recalculation_mismatch")
    if plateau != expected_plateau:
        contract_blockers.append("parameter_stability_development_recalculation_mismatch")

    candidates_by_strategy: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        strategy_id = str(candidate.get("strategy_id") or "").strip().lower()
        candidates_by_strategy.setdefault(strategy_id, []).append(candidate)
    unexpected = sorted(set(candidates_by_strategy) - set(hypothesis_strategies))
    if unexpected:
        contract_blockers.append("admission_candidate_strategy_not_hypothesis_bound")
    if not candidates:
        contract_blockers.append("validation_candidate_set_empty")
    if len(candidates) > max_candidates:
        contract_blockers.append("validation_candidate_limit_exceeded")
    if any(len(items) > 1 for items in candidates_by_strategy.values()):
        contract_blockers.append("validation_candidate_strategy_duplicate")

    strategies: list[dict[str, Any]] = []
    for strategy_id in hypothesis_strategies:
        strategy_candidates = candidates_by_strategy.get(strategy_id, [])
        candidate_variant_ids = [
            str(candidate.get("variant_id") or "") for candidate in strategy_candidates
        ]
        candidate_variant_id_set = {item for item in candidate_variant_ids if item}
        strategy_cells = [
            cell for cell in cells
            if str(cell.get("strategy_id") or "").strip().lower() == strategy_id
            and str(cell.get("variant_id") or "") in candidate_variant_id_set
        ]
        has_candidate = len(strategy_candidates) == 1 and all(candidate_variant_ids)
        coverage_passed, coverage_blockers = (
            _selection_cell_coverage_condition(strategy_cells, required_symbols)
            if has_candidate else (True, [])
        )
        checks: list[dict[str, Any]] = []
        for condition_id in standard_ids:
            if condition_id == "parameter_plateau_absent":
                passed, blockers = _parameter_condition(strategy_id, plateau)
            elif condition_id == "cost_break_even_lost":
                if not strategy_candidates:
                    checks.append({
                        "condition_id": condition_id,
                        "evidence_stage": _DEVELOPMENT_STAGE,
                        "required_action": _BLOCK_ACTION,
                        "status": "NOT_APPLICABLE",
                        "triggered": False,
                        "blockers": [],
                    })
                    continue
                passed, blockers = _cost_condition(strategy_cells)
            elif condition_id == "fixed_parameter_time_slice_instability":
                if not strategy_candidates:
                    checks.append({
                        "condition_id": condition_id,
                        "evidence_stage": _DEVELOPMENT_STAGE,
                        "required_action": _BLOCK_ACTION,
                        "status": "NOT_APPLICABLE",
                        "triggered": False,
                        "blockers": [],
                    })
                    continue
                passed, blockers = _fixed_slice_condition(strategy_cells)
            else:
                passed, blockers = False, [f"unsupported_preregistered_condition:{condition_id}"]
            checks.append({
                "condition_id": condition_id,
                "evidence_stage": _DEVELOPMENT_STAGE,
                "required_action": _BLOCK_ACTION,
                "status": "PASS" if passed else "BLOCK",
                "triggered": not passed,
                "blockers": blockers,
            })
        blockers = [
            str(blocker)
            for check in checks if check.get("status") == "BLOCK"
            for blocker in _sequence(check.get("blockers"))
        ]
        if not coverage_passed:
            blockers.extend(coverage_blockers)
        if len(strategy_candidates) > 1 or any(not item for item in candidate_variant_ids):
            blockers.append("validation_candidate_invalid_or_duplicate")
        status = "PASS" if not blockers else "BLOCK"
        strategies.append({
            "strategy_id": strategy_id,
            "status": status,
            "candidate_variant_ids": candidate_variant_ids,
            "admitted_variant_ids": [],
            "checks": checks,
            "blockers": list(dict.fromkeys(blockers)),
        })

    all_blockers = [*contract_blockers]
    all_blockers.extend(
        f"{row['strategy_id']}:{item}"
        for row in strategies
        for item in _sequence(row.get("blockers"))
    )
    batch_passed = bool(strategies) and not all_blockers
    admitted_variant_ids = [
        variant_id
        for row in strategies
        for variant_id in _sequence(row.get("candidate_variant_ids"))
        if batch_passed and isinstance(variant_id, str) and variant_id
    ]
    if batch_passed:
        for row in strategies:
            row["admitted_variant_ids"] = list(row.get("candidate_variant_ids") or [])
    content = {
        "schema_version": STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION,
        "status": "PASS" if batch_passed else "BLOCK",
        "admission_scope": "HYPOTHESIS_BATCH",
        "evidence_stage": _DEVELOPMENT_STAGE,
        "required_action": _BLOCK_ACTION,
        "hypothesis_id": str(hypothesis.get("hypothesis_id") or ""),
        "hypothesis_hash": str(hypothesis.get("hypothesis_hash") or ""),
        "development_recalculation": {
            "required_selection_symbols": required_symbols,
            "validation_rankings_hash": canonical_hash(recalculated_rankings),
            "validation_candidates_match": candidates == expected_candidates,
            "parameter_stability_match": plateau == expected_plateau,
        },
        "standard_condition_ids": standard_ids,
        "strategies": strategies,
        "admitted_variant_ids": admitted_variant_ids,
        "blockers": list(dict.fromkeys(all_blockers)),
        "descriptive_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "admission_hash": canonical_hash(content)}


def _mechanism_condition_contract(
    hypothesis: dict[str, Any],
    *,
    expected_strategy_ids: list[str],
    expected_schema_version: str = (
        STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
    ),
) -> tuple[list[dict[str, Any]], list[str]]:
    verification = verify_strategy_hypothesis_preregistration(
        hypothesis,
        expected_strategy_ids=expected_strategy_ids,
        expected_research_generation=str(
            hypothesis.get("research_generation") or ""
        ),
        expected_schema_version=(
            expected_schema_version
        ),
    )
    blockers = [
        f"mechanism_hypothesis:{item}"
        for item in verification.get("blockers") or []
    ]
    failure_contract = _mapping(hypothesis.get("failure_contract"))
    raw_conditions = _sequence(
        failure_contract.get("mechanism_specific_conditions")
    )
    if not raw_conditions:
        blockers.append("mechanism_conditions_missing")
        return [], list(dict.fromkeys(blockers))
    required_fields = {
        "condition_id",
        "evidence_stage",
        "metric",
        "operator",
        "threshold",
        "required_action",
    }
    conditions: list[dict[str, Any]] = []
    condition_ids: list[str] = []
    for raw in raw_conditions:
        if not isinstance(raw, dict) or set(raw) != required_fields:
            blockers.append("mechanism_condition_shape_invalid")
            continue
        condition_id = str(raw.get("condition_id") or "")
        metric = str(raw.get("metric") or "")
        operator = str(raw.get("operator") or "")
        threshold = _finite(raw.get("threshold"))
        if not condition_id:
            blockers.append("mechanism_condition_id_missing")
        elif condition_id in condition_ids:
            blockers.append("mechanism_condition_id_duplicate")
        if raw.get("evidence_stage") != MECHANISM_FAILURE_EVIDENCE_STAGE_V2:
            blockers.append("mechanism_condition_evidence_stage_invalid")
        if raw.get("required_action") != MECHANISM_FAILURE_REQUIRED_ACTION_V2:
            blockers.append("mechanism_condition_required_action_invalid")
        if metric not in MECHANISM_FAILURE_METRICS_V2:
            blockers.append("mechanism_condition_metric_invalid")
        if operator not in MECHANISM_FAILURE_OPERATORS_V2:
            blockers.append("mechanism_condition_operator_invalid")
        if threshold is None:
            blockers.append("mechanism_condition_threshold_invalid")
        if (
            not condition_id
            or condition_id in condition_ids
            or raw.get("evidence_stage")
            != MECHANISM_FAILURE_EVIDENCE_STAGE_V2
            or raw.get("required_action")
            != MECHANISM_FAILURE_REQUIRED_ACTION_V2
            or metric not in MECHANISM_FAILURE_METRICS_V2
            or operator not in MECHANISM_FAILURE_OPERATORS_V2
            or threshold is None
        ):
            continue
        condition_ids.append(condition_id)
        conditions.append(dict(raw))
    if len(conditions) != len(raw_conditions):
        blockers.append("mechanism_conditions_unresolved")
    return conditions, list(dict.fromkeys(blockers))


def _mechanism_metric_value(
    metric: str,
    *,
    ranking: dict[str, Any],
    cells: list[dict[str, Any]],
) -> float | None:
    ranking_fields = {
        "validation_adjusted_score": "adjusted_score",
        "median_validation_return_pct": "median_validation_return_pct",
        "median_validation_excess_return_pct": (
            "median_validation_excess_return_pct"
        ),
        "validation_worst_drawdown_pct": "validation_worst_drawdown_pct",
        "validation_trade_count": "validation_trade_count",
    }
    if metric in ranking_fields:
        return _finite(ranking.get(ranking_fields[metric]))
    if not cells:
        return None
    if metric == "minimum_stressed_return_pct":
        values = [
            _finite(_mapping(cell.get("cost_sensitivity")).get("worst_return_pct"))
            for cell in cells
        ]
    elif metric == "minimum_positive_fold_count":
        values = [
            _finite(_mapping(cell.get("fold_stability")).get("positive_folds"))
            for cell in cells
        ]
    else:
        return None
    if any(value is None for value in values):
        return None
    return min(float(value) for value in values if value is not None)


def _condition_triggered(value: float, operator: str, threshold: float) -> bool:
    if operator == "LT":
        return value < threshold
    if operator == "LTE":
        return value <= threshold
    if operator == "GT":
        return value > threshold
    if operator == "GTE":
        return value >= threshold
    raise ValueError("mechanism_condition_operator_invalid")


def build_strategy_preregistered_failure_admission_v2(
    *,
    batch_spec: dict[str, Any] | Any,
    hypothesis_preregistration: dict[str, Any] | Any,
    parameter_stability: dict[str, Any] | Any,
    selection_cells: list[dict[str, Any]] | Any,
    validation_candidates: list[dict[str, Any]] | Any,
    total_variant_trials: int | None = None,
    _expected_hypothesis_schema_version: str = (
        STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
    ),
) -> dict[str, Any]:
    """Evaluate schema-13 machine-readable mechanism conditions fail closed."""

    spec = _mapping(batch_spec)
    hypothesis = _mapping(hypothesis_preregistration)
    cells = [
        dict(item) for item in _sequence(selection_cells)
        if isinstance(item, dict)
    ]
    candidates = [
        dict(item) for item in _sequence(validation_candidates)
        if isinstance(item, dict)
    ]
    base = build_strategy_preregistered_failure_admission(
        batch_spec=spec,
        hypothesis_preregistration=hypothesis,
        parameter_stability=parameter_stability,
        selection_cells=cells,
        validation_candidates=candidates,
        total_variant_trials=total_variant_trials,
    )
    strategy_ids = [
        str(item).strip().lower()
        for item in _sequence(spec.get("strategies"))
        if isinstance(item, str) and item.strip()
    ]
    mechanism_conditions, contract_blockers = _mechanism_condition_contract(
        hypothesis,
        expected_strategy_ids=strategy_ids,
        expected_schema_version=_expected_hypothesis_schema_version,
    )
    variants = [
        dict(item) for item in _sequence(spec.get("variants"))
        if isinstance(item, dict)
    ]
    required_symbols = list(dict.fromkeys(
        str(item).strip().upper()
        for item in _sequence(spec.get("selection_symbols"))
        if isinstance(item, str) and item.strip()
    ))
    recalculated_rankings = [
        aggregate_validation_variant(
            variant,
            [
                cell for cell in cells
                if str(cell.get("strategy_id") or "").strip().lower()
                == str(variant.get("strategy_id") or "").strip().lower()
                and str(cell.get("variant_id") or "")
                == str(variant.get("variant_id") or "")
            ],
            required_symbols=len(required_symbols),
            total_variant_trials=(
                total_variant_trials
                if isinstance(total_variant_trials, int)
                and not isinstance(total_variant_trials, bool)
                and total_variant_trials >= len(variants)
                else len(variants)
            ),
        )
        for variant in variants
    ]
    ranking_by_id = {
        str(row.get("variant_id") or ""): row
        for row in recalculated_rankings
        if str(row.get("variant_id") or "")
    }
    candidates_by_strategy: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        candidates_by_strategy.setdefault(
            str(candidate.get("strategy_id") or "").strip().lower(),
            [],
        ).append(candidate)

    updated_rows: list[dict[str, Any]] = []
    mechanism_blockers: list[str] = []
    for raw_row in _sequence(base.get("strategies")):
        row = dict(raw_row) if isinstance(raw_row, dict) else {}
        strategy_id = str(row.get("strategy_id") or "").strip().lower()
        strategy_candidates = candidates_by_strategy.get(strategy_id, [])
        candidate = strategy_candidates[0] if len(strategy_candidates) == 1 else {}
        variant_id = str(candidate.get("variant_id") or "")
        ranking = _mapping(ranking_by_id.get(variant_id))
        candidate_cells = [
            cell for cell in cells
            if str(cell.get("strategy_id") or "").strip().lower() == strategy_id
            and str(cell.get("variant_id") or "") == variant_id
        ]
        checks = [
            {**dict(check), "condition_kind": "STANDARD"}
            for check in _sequence(row.get("checks"))
            if isinstance(check, dict)
        ]
        row_mechanism_blockers: list[str] = []
        for condition in mechanism_conditions:
            condition_id = str(condition.get("condition_id") or "")
            if not strategy_candidates:
                checks.append({
                    **condition,
                    "condition_kind": "MECHANISM_SPECIFIC",
                    "status": "NOT_APPLICABLE",
                    "triggered": False,
                    "metric_value": None,
                    "blockers": [],
                })
                continue
            metric_value = _mechanism_metric_value(
                str(condition.get("metric") or ""),
                ranking=ranking,
                cells=candidate_cells,
            )
            threshold = _finite(condition.get("threshold"))
            if len(strategy_candidates) != 1 or metric_value is None or threshold is None:
                blockers = [f"mechanism_condition_unresolved:{condition_id}"]
                triggered: bool | None = None
                status = "BLOCK"
            else:
                triggered = _condition_triggered(
                    metric_value,
                    str(condition.get("operator") or ""),
                    threshold,
                )
                blockers = (
                    [f"mechanism_condition_triggered:{condition_id}"]
                    if triggered else []
                )
                status = "BLOCK" if triggered else "PASS"
            checks.append({
                **condition,
                "condition_kind": "MECHANISM_SPECIFIC",
                "status": status,
                "triggered": triggered,
                "metric_value": metric_value,
                "blockers": blockers,
            })
            row_mechanism_blockers.extend(blockers)
        row_blockers = list(dict.fromkeys([
            *[str(item) for item in _sequence(row.get("blockers"))],
            *row_mechanism_blockers,
        ]))
        mechanism_blockers.extend(
            f"{strategy_id}:{item}" for item in row_mechanism_blockers
        )
        row.update({
            "status": "PASS" if not row_blockers else "BLOCK",
            "checks": checks,
            "blockers": row_blockers,
        })
        updated_rows.append(row)

    all_blockers = list(dict.fromkeys([
        *[str(item) for item in _sequence(base.get("blockers"))],
        *contract_blockers,
        *mechanism_blockers,
    ]))
    batch_passed = base.get("status") == "PASS" and not all_blockers
    admitted_variant_ids = (
        [str(item) for item in _sequence(base.get("admitted_variant_ids"))]
        if batch_passed else []
    )
    for row in updated_rows:
        row["admitted_variant_ids"] = (
            list(row.get("candidate_variant_ids") or [])
            if batch_passed else []
        )
    standard_conditions = _sequence(
        _mapping(hypothesis.get("failure_contract")).get("standard_conditions")
    )
    future_standard_checks = [
        {
            **dict(item),
            "condition_kind": "STANDARD",
            "status": "NOT_DUE",
            "triggered": False,
            "blockers": [],
        }
        for item in standard_conditions
        if isinstance(item, dict)
        and item.get("evidence_stage") in {
            "PREREGISTERED_BLIND_SINGLE_USE",
            "NATURAL_FORWARD_MATURITY",
        }
    ]
    content = {
        key: value for key, value in base.items() if key != "admission_hash"
    }
    content.update({
        "schema_version": (
            STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V2
        ),
        "status": "PASS" if batch_passed else "BLOCK",
        "strategies": updated_rows,
        "mechanism_condition_ids": [
            str(item.get("condition_id") or "")
            for item in mechanism_conditions
        ],
        "future_standard_checks": future_standard_checks,
        "admitted_variant_ids": admitted_variant_ids,
        "blockers": all_blockers,
    })
    return {**content, "admission_hash": canonical_hash(content)}


def _build_strategy_preregistered_failure_admission_v3_core(
    *,
    batch_spec: dict[str, Any] | Any,
    hypothesis_preregistration: dict[str, Any] | Any,
    parameter_stability: dict[str, Any] | Any,
    selection_cells: list[dict[str, Any]] | Any,
    validation_candidates: list[dict[str, Any]] | Any,
    registration_context: dict[str, Any] | Any = None,
    live_registry_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild schema-14 admission with the global preregistered trial count."""

    spec = _mapping(batch_spec)
    hypothesis = _mapping(hypothesis_preregistration)
    variants = [
        dict(item) for item in _sequence(spec.get("variants"))
        if isinstance(item, dict)
    ]
    lineage = _mapping(spec.get("search_lineage"))
    lineage_verification = verify_strategy_research_search_lineage(
        lineage,
        expected_search_family_id=str(hypothesis.get("search_family_id") or ""),
        expected_current_trial_count=len(variants),
    )
    context = _mapping(registration_context)
    protocol = _mapping(context.get("protocol"))
    claim = _mapping(context.get("claim"))
    registered_spec = _mapping(protocol.get("batch_spec"))
    registry_audit = _mapping(context.get("registry_audit"))
    context_blockers: list[str] = []
    if not isinstance(registration_context, dict):
        context_blockers.append("strategy_search_registration_context_missing")
    if context.get("ok") is not True or context.get("status") != "RUNNING":
        context_blockers.append("strategy_search_registration_not_running")
    if registry_audit.get("status") != "PASS":
        context_blockers.append("strategy_search_registry_audit_not_passed")
    protocol_content = {
        key: value for key, value in protocol.items() if key != "protocol_hash"
    }
    protocol_hash = str(protocol.get("protocol_hash") or "")
    if not protocol_hash or canonical_hash(protocol_content) != protocol_hash:
        context_blockers.append("strategy_search_registered_protocol_hash_invalid")
    if registered_spec != spec:
        context_blockers.append("strategy_search_registered_batch_spec_mismatch")
    if str(protocol.get("batch_spec_hash") or "") != canonical_hash(registered_spec):
        context_blockers.append("strategy_search_registered_batch_hash_invalid")
    registration_id = str(protocol.get("registration_id") or "")
    if (
        not registration_id
        or str(context.get("registration_id") or "") != registration_id
    ):
        context_blockers.append("strategy_search_registration_id_mismatch")
    claim_content = {
        key: value for key, value in claim.items() if key != "claim_hash"
    }
    claim_hash = str(claim.get("claim_hash") or "")
    if (
        claim.get("schema_version") != "strategy-matrix-single-use-claim-v2"
        or claim.get("status") != "CLAIMED_FOR_SINGLE_RUN"
        or not claim_hash
        or canonical_hash(claim_content) != claim_hash
    ):
        context_blockers.append("strategy_search_registration_claim_invalid")
    if (
        str(claim.get("registration_id") or "") != registration_id
        or str(claim.get("protocol_hash") or "") != protocol_hash
    ):
        context_blockers.append("strategy_search_registration_claim_binding_mismatch")
    anchor_verification = verify_strategy_research_registry_anchor(
        claim.get("search_lineage_registry_anchor"),
        search_lineage=lineage,
        expected_registration_id=registration_id,
        expected_protocol_hash=protocol_hash,
        expected_active_runtime_root=str(
            Path(str(protocol.get("registry_path") or "")).parent
        ),
        expected_canonical_registry_path=str(
            protocol.get("registry_path") or ""
        ),
    )
    context_blockers.extend(
        f"strategy_search_registration_anchor:{item}"
        for item in anchor_verification.get("blockers") or []
    )
    receipt_consistent = not context_blockers
    live_binding = _mapping(live_registry_binding)
    expected_anchor_hash = str(
        _mapping(claim.get("search_lineage_registry_anchor")).get("anchor_hash")
        or ""
    )
    live_registry_verified = (
        live_binding.get("schema_version")
        == "strategy-search-live-registry-verification-v1"
        and live_binding.get("status") == "LIVE_REGISTRY_VERIFIED"
        and live_binding.get("registration_id") == registration_id
        and live_binding.get("protocol_hash") == protocol_hash
        and live_binding.get("claim_hash") == claim_hash
        and live_binding.get("registry_anchor_hash") == expected_anchor_hash
        and live_binding.get("cumulative_trial_count")
        == lineage.get("cumulative_trial_count")
        and isinstance(live_binding.get("registered_event_hash"), str)
        and len(str(live_binding.get("registered_event_hash") or "")) == 64
        and isinstance(live_binding.get("claimed_event_hash"), str)
        and len(str(live_binding.get("claimed_event_hash") or "")) == 64
        and isinstance(live_binding.get("registry_audit_event_count"), int)
        and not isinstance(live_binding.get("registry_audit_event_count"), bool)
        and live_binding.get("registry_audit_event_count") >= 2
        and isinstance(live_binding.get("registry_audit_tail_event_hash"), str)
        and len(str(live_binding.get("registry_audit_tail_event_hash") or "")) == 64
        and receipt_consistent
    )
    cumulative_trial_count = lineage_verification.get("cumulative_trial_count")
    effective_trial_count = (
        cumulative_trial_count
        if lineage_verification.get("status") == "PASS"
        and live_registry_verified
        and isinstance(cumulative_trial_count, int)
        and not isinstance(cumulative_trial_count, bool)
        and cumulative_trial_count >= len(variants)
        else len(variants)
    )
    base = build_strategy_preregistered_failure_admission_v2(
        batch_spec=spec,
        hypothesis_preregistration=hypothesis,
        parameter_stability=parameter_stability,
        selection_cells=selection_cells,
        validation_candidates=validation_candidates,
        total_variant_trials=effective_trial_count,
        _expected_hypothesis_schema_version=(
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
        ),
    )
    lineage_blockers = [
        f"search_lineage:{item}"
        for item in lineage_verification.get("blockers") or []
    ]
    all_blockers = list(dict.fromkeys([
        *[str(item) for item in _sequence(base.get("blockers"))],
        *lineage_blockers,
        *context_blockers,
        *(
            []
            if live_registry_verified
            else ["strategy_search_lineage_live_registry_verification_required"]
        ),
    ]))
    batch_passed = base.get("status") == "PASS" and not all_blockers
    strategies = [
        dict(item) for item in _sequence(base.get("strategies"))
        if isinstance(item, dict)
    ]
    if not batch_passed:
        for row in strategies:
            row["admitted_variant_ids"] = []
    content = {key: value for key, value in base.items() if key != "admission_hash"}
    content.update({
        "schema_version": (
            STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3
        ),
        "status": "PASS" if batch_passed else "BLOCK",
        "strategies": strategies,
        "admitted_variant_ids": (
            list(base.get("admitted_variant_ids") or []) if batch_passed else []
        ),
        "search_lineage_binding": {
            "report_schema_version": (
                STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
            ),
            "status": (
                "PASS"
                if lineage_verification.get("status") == "PASS"
                else "BLOCK"
            ),
            "lineage_hash": str(lineage.get("lineage_hash") or ""),
            "search_family_id": str(lineage.get("search_family_id") or ""),
            "trial_count_scope": str(lineage.get("trial_count_scope") or ""),
            "current_trial_count": lineage.get("current_trial_count"),
            "cumulative_trial_count": lineage.get("cumulative_trial_count"),
            "derived_before_selection": (
                lineage.get("derived_before_selection") is True
            ),
            "blockers": list(lineage_verification.get("blockers") or []),
        },
        "registration_binding": {
            "status": (
                "LIVE_REGISTRY_VERIFIED"
                if live_registry_verified
                else "SELF_CONSISTENT_RECEIPT"
                if receipt_consistent
                else "BLOCK"
            ),
            "verification_scope": (
                "LIVE_REGISTRY_AUDIT_AND_PREREGISTRATION_RECEIPT"
                if live_registry_verified
                else "SELF_CONSISTENT_RECEIPT_ONLY"
            ),
            "registration_id": registration_id,
            "protocol_hash": protocol_hash,
            "claim_hash": claim_hash,
            "registry_anchor_hash": str(
                _mapping(claim.get("search_lineage_registry_anchor")).get(
                    "anchor_hash"
                )
                or ""
            ),
            "registry_status": str(context.get("status") or ""),
            "registry_audit_status": str(registry_audit.get("status") or ""),
            "blockers": context_blockers,
        },
        "blockers": all_blockers,
    })
    return {**content, "admission_hash": canonical_hash(content)}


def build_strategy_preregistered_failure_admission_v3(
    *,
    batch_spec: dict[str, Any] | Any,
    hypothesis_preregistration: dict[str, Any] | Any,
    parameter_stability: dict[str, Any] | Any,
    selection_cells: list[dict[str, Any]] | Any,
    validation_candidates: list[dict[str, Any]] | Any,
    registration_context: dict[str, Any] | Any = None,
) -> dict[str, Any]:
    """Build only a receipt-consistency draft; a live store owns PASS admission."""

    return _build_strategy_preregistered_failure_admission_v3_core(
        batch_spec=batch_spec,
        hypothesis_preregistration=hypothesis_preregistration,
        parameter_stability=parameter_stability,
        selection_cells=selection_cells,
        validation_candidates=validation_candidates,
        registration_context=registration_context,
        live_registry_binding=None,
    )


def _build_strategy_preregistered_failure_admission_v3_from_live_registry(
    *,
    batch_spec: dict[str, Any],
    hypothesis_preregistration: dict[str, Any],
    parameter_stability: dict[str, Any],
    selection_cells: list[dict[str, Any]],
    validation_candidates: list[dict[str, Any]],
    registration_context: dict[str, Any],
    live_registry_binding: dict[str, Any],
) -> dict[str, Any]:
    return _build_strategy_preregistered_failure_admission_v3_core(
        batch_spec=batch_spec,
        hypothesis_preregistration=hypothesis_preregistration,
        parameter_stability=parameter_stability,
        selection_cells=selection_cells,
        validation_candidates=validation_candidates,
        registration_context=registration_context,
        live_registry_binding=live_registry_binding,
    )


def verify_strategy_preregistered_failure_admission_v3_receipt(
    admission: dict[str, Any] | Any,
    *,
    batch_spec: dict[str, Any] | Any,
    hypothesis_preregistration: dict[str, Any] | Any,
    parameter_stability: dict[str, Any] | Any,
    selection_cells: list[dict[str, Any]] | Any,
    validation_candidates: list[dict[str, Any]] | Any,
    registration_context: dict[str, Any] | Any,
) -> dict[str, Any]:
    """Verify a persisted schema-14 admission without claiming a live DB check.

    The report carries the preregistration protocol and claim receipt, but not
    the live SQLite connection that originally authorized the admission.  This
    verifier therefore reconstructs the exact persisted object from those
    receipts and the cumulative lineage while explicitly reporting an offline
    receipt-consistency scope.
    """

    payload = _mapping(admission)
    spec = _mapping(batch_spec)
    hypothesis = _mapping(hypothesis_preregistration)
    variants = [
        dict(item) for item in _sequence(spec.get("variants"))
        if isinstance(item, dict)
    ]
    lineage = _mapping(spec.get("search_lineage"))
    lineage_verification = verify_strategy_research_search_lineage(
        lineage,
        expected_search_family_id=str(hypothesis.get("search_family_id") or ""),
        expected_current_trial_count=len(variants),
    )

    # Reuse the receipt-only builder to verify protocol, claim, anchor, and
    # registry-path bindings.  Its mandatory live-verification blocker is not
    # copied into the expected persisted admission.
    receipt_draft = build_strategy_preregistered_failure_admission_v3(
        batch_spec=spec,
        hypothesis_preregistration=hypothesis,
        parameter_stability=parameter_stability,
        selection_cells=selection_cells,
        validation_candidates=validation_candidates,
        registration_context=registration_context,
    )
    receipt_binding = _mapping(receipt_draft.get("registration_binding"))
    context_blockers = [
        str(item) for item in _sequence(receipt_binding.get("blockers"))
    ]
    receipt_consistent = (
        receipt_binding.get("status") == "SELF_CONSISTENT_RECEIPT"
        and receipt_binding.get("verification_scope")
        == "SELF_CONSISTENT_RECEIPT_ONLY"
        and not context_blockers
    )
    cumulative_trial_count = lineage_verification.get("cumulative_trial_count")
    effective_trial_count = (
        cumulative_trial_count
        if lineage_verification.get("status") == "PASS"
        and isinstance(cumulative_trial_count, int)
        and not isinstance(cumulative_trial_count, bool)
        and cumulative_trial_count >= len(variants)
        else len(variants)
    )
    base = build_strategy_preregistered_failure_admission_v2(
        batch_spec=spec,
        hypothesis_preregistration=hypothesis,
        parameter_stability=parameter_stability,
        selection_cells=selection_cells,
        validation_candidates=validation_candidates,
        total_variant_trials=effective_trial_count,
        _expected_hypothesis_schema_version=(
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
        ),
    )
    lineage_blockers = [
        f"search_lineage:{item}"
        for item in lineage_verification.get("blockers") or []
    ]
    expected_blockers = list(dict.fromkeys([
        *[str(item) for item in _sequence(base.get("blockers"))],
        *lineage_blockers,
        *context_blockers,
    ]))
    batch_passed = (
        base.get("status") == "PASS"
        and not expected_blockers
        and receipt_consistent
    )
    strategies = [
        dict(item) for item in _sequence(base.get("strategies"))
        if isinstance(item, dict)
    ]
    if not batch_passed:
        for row in strategies:
            row["admitted_variant_ids"] = []
    expected_content = {
        key: value for key, value in base.items() if key != "admission_hash"
    }
    expected_registration_binding = dict(receipt_binding)
    expected_registration_binding.update({
        "status": "LIVE_REGISTRY_VERIFIED",
        "verification_scope": (
            "LIVE_REGISTRY_AUDIT_AND_PREREGISTRATION_RECEIPT"
        ),
    })
    expected_content.update({
        "schema_version": (
            STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3
        ),
        "status": "PASS" if batch_passed else "BLOCK",
        "strategies": strategies,
        "admitted_variant_ids": (
            list(base.get("admitted_variant_ids") or [])
            if batch_passed else []
        ),
        "search_lineage_binding": _mapping(
            receipt_draft.get("search_lineage_binding")
        ),
        "registration_binding": expected_registration_binding,
        "blockers": expected_blockers,
    })
    expected_admission = {
        **expected_content,
        "admission_hash": canonical_hash(expected_content),
    }

    blockers: list[str] = []
    if not isinstance(admission, dict):
        blockers.append("strategy_admission_v3_type_invalid")
    if lineage_verification.get("status") != "PASS":
        blockers.extend(
            f"strategy_admission_v3_lineage:{item}"
            for item in lineage_verification.get("blockers") or []
        )
    if not receipt_consistent:
        blockers.extend(
            f"strategy_admission_v3_receipt:{item}"
            for item in (
                context_blockers
                or ["strategy_search_registration_receipt_inconsistent"]
            )
        )
    if payload != expected_admission:
        blockers.append("strategy_admission_v3_semantic_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "admission_status": str(payload.get("status") or "BLOCK"),
        "admission_hash": str(payload.get("admission_hash") or ""),
        "expected_admission": expected_admission,
        "verification_scope": (
            "OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY"
        ),
        "live_registry_verified": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION",
    "PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION",
    "STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION",
    "STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V2",
    "STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3",
    "build_strategy_preregistered_failure_admission",
    "build_strategy_preregistered_failure_admission_v2",
    "build_strategy_preregistered_failure_admission_v3",
    "verify_strategy_preregistered_failure_admission_v3_receipt",
]
