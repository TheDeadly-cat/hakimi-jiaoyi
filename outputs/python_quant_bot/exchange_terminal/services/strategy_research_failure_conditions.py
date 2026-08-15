from __future__ import annotations

from copy import deepcopy
import math
from typing import Any


STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION = (
    "strategy-research-failure-conditions-v1"
)
STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V2 = (
    "strategy-research-failure-conditions-v2"
)
STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V3 = (
    "strategy-research-failure-conditions-v3"
)
STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V4 = (
    "strategy-research-failure-conditions-v4"
)


def _native_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _strings(value: Any, *, limit: int = 24) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:240] for item in value if isinstance(item, str) and item][:limit]


def build_strategy_research_failure_conditions(
    *,
    strategy_id: str,
    parameter_stability: dict[str, Any] | None,
    cost_sensitivity: dict[str, Any] | None,
    chronological_slices: dict[str, Any] | None,
    implementation_currentness: dict[str, Any] | None,
    full_implementation_currentness: dict[str, Any] | None,
) -> dict[str, Any]:
    """Describe checked invalidation conditions without creating a new strategy gate."""

    plateau = deepcopy(parameter_stability) if isinstance(parameter_stability, dict) else {}
    cost = deepcopy(cost_sensitivity) if isinstance(cost_sensitivity, dict) else {}
    chronological = deepcopy(chronological_slices) if isinstance(chronological_slices, dict) else {}
    implementation = (
        deepcopy(implementation_currentness)
        if isinstance(implementation_currentness, dict)
        else {}
    )
    full_implementation = (
        deepcopy(full_implementation_currentness)
        if isinstance(full_implementation_currentness, dict)
        else {}
    )
    if not str(strategy_id or "").strip():
        return {
            "schema_version": STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION,
            "status": "NOT_IN_REPORT",
            "observed": ["strategy_not_in_frozen_research_report"],
            "evidence_gaps": [
                "strategy_specific_parameter_cost_and_time_evidence_missing",
                "dataset_currentness_not_checked",
                "report_age_policy_not_checked",
                "natural_forward_performance_not_proven_by_strategy_report",
            ],
            "conditions": [],
            "descriptive_only": True,
            "profitability_proven": False,
            "parameter_selection_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    observed: list[str] = []
    evidence_gaps: list[str] = [
        "dataset_currentness_not_checked",
        "report_age_policy_not_checked",
        "natural_forward_performance_not_proven_by_strategy_report",
    ]
    conditions: list[dict[str, Any]] = []

    def add_condition(
        condition_id: str,
        evidence_status: Any,
        triggered: bool | None,
        blockers: Any,
    ) -> None:
        conditions.append({
            "condition_id": condition_id,
            "evidence_status": str(evidence_status or "UNKNOWN")[:32],
            "triggered": triggered,
            "blockers": _strings(blockers),
        })
        if triggered is True:
            observed.append(condition_id)
        elif triggered is None:
            evidence_gaps.append(f"{condition_id}_not_checked")

    parameter_status = str(plateau.get("status") or "UNKNOWN").upper()
    plateau_width = _native_nonnegative_int(plateau.get("plateau_width"))
    adjacent_count = _native_nonnegative_int(plateau.get("adjacent_near_best_variant_count"))
    best_score = _number(plateau.get("best_adjusted_score"))
    parameter_pass_claim_valid = (
        parameter_status == "PASS"
        and plateau_width is not None
        and plateau_width >= 2
        and adjacent_count is not None
        and adjacent_count >= 1
        and plateau.get("peak_only") is False
        and best_score is not None
        and best_score > 0
    )
    parameter_triggered = (
        False if parameter_pass_claim_valid
        else True if parameter_status in {"PASS", "REVIEW", "NOT_ENOUGH_VARIANTS", "BLOCK"}
        else None
    )
    add_condition(
        "parameter_plateau_not_preserved",
        parameter_status,
        parameter_triggered,
        plateau.get("blockers"),
    )

    cost_status = str(cost.get("status") or "UNKNOWN").upper()
    break_even = cost.get("break_even_preserved")
    worst_return = _number(cost.get("worst_stressed_return_pct"))
    cost_pass_claim_valid = (
        cost_status == "PASS"
        and break_even is True
        and worst_return is not None
        and worst_return > 0
    )
    cost_triggered = (
        False if cost_pass_claim_valid
        else True if cost_status in {"PASS", "REVIEW", "BLOCK"}
        or break_even is False
        or (worst_return is not None and worst_return <= 0)
        else None
    )
    add_condition(
        "cost_stress_break_even_not_preserved",
        cost_status,
        cost_triggered,
        cost.get("blockers"),
    )

    temporal_status = str(chronological.get("status") or "UNKNOWN").upper()
    usable_folds = _native_nonnegative_int(chronological.get("usable_fold_count"))
    positive_folds = _native_nonnegative_int(chronological.get("positive_fold_count"))
    temporal_pass_claim_valid = (
        temporal_status == "PASS"
        and usable_folds is not None
        and usable_folds > 0
        and positive_folds is not None
        and positive_folds > 0
    )
    temporal_triggered = (
        False if temporal_pass_claim_valid
        else True if temporal_status in {"PASS", "REVIEW", "BLOCK"}
        else None
    )
    add_condition(
        "fixed_parameter_time_slice_robustness_not_preserved",
        temporal_status,
        temporal_triggered,
        chronological.get("blockers"),
    )

    signal_status = str(implementation.get("status") or "UNKNOWN").upper()
    signal_triggered = False if signal_status == "MATCH" else True if signal_status == "MISMATCH" else None
    add_condition(
        "strategy_signal_implementation_changed",
        signal_status,
        signal_triggered,
        implementation.get("blockers"),
    )

    full_status = str(full_implementation.get("status") or "UNKNOWN").upper()
    full_triggered = False if full_status == "MATCH" else True if full_status == "MISMATCH" else None
    add_condition(
        "research_implementation_closure_changed",
        full_status,
        full_triggered,
        full_implementation.get("blockers"),
    )

    observed = list(dict.fromkeys(observed))[:24]
    evidence_gaps = list(dict.fromkeys(evidence_gaps))[:24]
    return {
        "schema_version": STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION,
        "status": "TRIGGERED" if observed else "GAPS",
        "observed": observed,
        "evidence_gaps": evidence_gaps,
        "conditions": conditions,
        "descriptive_only": True,
        "profitability_proven": False,
        "parameter_selection_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_strategy_research_failure_conditions_v2(
    *,
    strategy_id: str,
    parameter_stability: dict[str, Any] | None,
    cost_sensitivity: dict[str, Any] | None,
    chronological_slices: dict[str, Any] | None,
    implementation_currentness: dict[str, Any] | None,
    full_implementation_currentness: dict[str, Any] | None,
    post_selection_replay_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extend the unchanged v1 contract with schema-11/12 replay preservation.

    ``NOT_RUN`` is an evidence gap, never a claimed failure or success.  A replay
    ``BLOCK`` is descriptive historical evidence and grants no selection or
    execution authority.
    """

    result = build_strategy_research_failure_conditions(
        strategy_id=strategy_id,
        parameter_stability=parameter_stability,
        cost_sensitivity=cost_sensitivity,
        chronological_slices=chronological_slices,
        implementation_currentness=implementation_currentness,
        full_implementation_currentness=full_implementation_currentness,
    )
    result["schema_version"] = STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V2
    if not str(strategy_id or "").strip():
        return result

    replay = (
        deepcopy(post_selection_replay_summary)
        if isinstance(post_selection_replay_summary, dict)
        else {}
    )
    stage_pairs = (
        ("frozen_test_replay_not_preserved", replay.get("frozen_test")),
        (
            "holdout_confirmation_replay_not_preserved",
            replay.get("holdout_confirmation"),
        ),
    )
    observed = list(result.get("observed") or [])
    evidence_gaps = list(result.get("evidence_gaps") or [])
    conditions = list(result.get("conditions") or [])
    for condition_id, raw_stage in stage_pairs:
        stage = raw_stage if isinstance(raw_stage, dict) else {}
        stage_status = str(stage.get("status") or "UNKNOWN").upper()
        if stage_status == "PASS":
            triggered: bool | None = False
        elif stage_status == "BLOCK":
            triggered = True
            observed.append(condition_id)
        else:
            triggered = None
            evidence_gaps.append(f"{condition_id}_not_checked")
        conditions.append({
            "condition_id": condition_id,
            "evidence_status": stage_status[:32],
            "triggered": triggered,
            "blockers": _strings(stage.get("blockers")),
        })

    result["observed"] = list(dict.fromkeys(observed))[:24]
    result["evidence_gaps"] = list(dict.fromkeys(evidence_gaps))[:24]
    result["conditions"] = conditions
    result["status"] = "TRIGGERED" if result["observed"] else "GAPS"
    return result


def build_strategy_research_failure_conditions_v3(
    *,
    strategy_id: str,
    parameter_stability: dict[str, Any] | None,
    cost_sensitivity: dict[str, Any] | None,
    chronological_slices: dict[str, Any] | None,
    implementation_currentness: dict[str, Any] | None,
    full_implementation_currentness: dict[str, Any] | None,
    post_selection_replay_summary: dict[str, Any] | None,
    preregistered_failure_admission: dict[str, Any] | None,
) -> dict[str, Any]:
    """Add schema-13 mechanism admission without treating NOT_DUE as success."""

    result = build_strategy_research_failure_conditions_v2(
        strategy_id=strategy_id,
        parameter_stability=parameter_stability,
        cost_sensitivity=cost_sensitivity,
        chronological_slices=chronological_slices,
        implementation_currentness=implementation_currentness,
        full_implementation_currentness=full_implementation_currentness,
        post_selection_replay_summary=post_selection_replay_summary,
    )
    result["schema_version"] = STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V3
    admission = (
        deepcopy(preregistered_failure_admission)
        if isinstance(preregistered_failure_admission, dict)
        else {}
    )
    admission_status = str(admission.get("status") or "UNKNOWN").upper()
    result["preregistered_failure_admission_status"] = admission_status[:32]
    if not str(strategy_id or "").strip():
        return result

    observed = list(result.get("observed") or [])
    evidence_gaps = list(result.get("evidence_gaps") or [])
    conditions = list(result.get("conditions") or [])

    def append_condition(
        *,
        condition_id: str,
        evidence_status: str,
        triggered: bool | None,
        blockers: Any,
    ) -> None:
        conditions.append({
            "condition_id": condition_id,
            "evidence_status": evidence_status[:32],
            "triggered": triggered,
            "blockers": _strings(blockers),
        })
        if triggered is True:
            observed.append(condition_id)
        elif triggered is None:
            evidence_gaps.append(f"{condition_id}_not_checked")

    admission_triggered = (
        False
        if admission_status == "PASS"
        else True
        if admission_status == "BLOCK"
        else None
    )
    append_condition(
        condition_id="preregistered_failure_admission_blocked",
        evidence_status=admission_status,
        triggered=admission_triggered,
        blockers=admission.get("blockers"),
    )

    checks = admission.get("checks")
    checks = checks if isinstance(checks, list) else []
    for raw in checks:
        check = raw if isinstance(raw, dict) else {}
        if check.get("condition_kind") != "MECHANISM_SPECIFIC":
            continue
        source_id = str(check.get("condition_id") or "unknown")[:64]
        condition_id = f"mechanism_failure:{source_id}"
        status = str(check.get("status") or "UNKNOWN").upper()
        raw_triggered = check.get("triggered")
        triggered = (
            False
            if status == "PASS" and raw_triggered is False
            else True
            if status == "BLOCK" and raw_triggered is True
            else None
        )
        append_condition(
            condition_id=condition_id,
            evidence_status=status,
            triggered=triggered,
            blockers=check.get("blockers"),
        )

    future_checks = admission.get("future_standard_checks")
    future_checks = future_checks if isinstance(future_checks, list) else []
    for raw in future_checks:
        check = raw if isinstance(raw, dict) else {}
        source_id = str(check.get("condition_id") or "unknown")[:64]
        condition_id = f"future_standard_failure:{source_id}"
        status = str(check.get("status") or "UNKNOWN").upper()
        raw_triggered = check.get("triggered")
        triggered = (
            False
            if status == "PASS" and raw_triggered is False
            else True
            if status == "BLOCK" and raw_triggered is True
            else None
        )
        append_condition(
            condition_id=condition_id,
            evidence_status=status,
            triggered=triggered,
            blockers=check.get("blockers"),
        )

    result["observed"] = list(dict.fromkeys(observed))[:24]
    result["evidence_gaps"] = list(dict.fromkeys(evidence_gaps))[:24]
    result["conditions"] = conditions
    result["status"] = "TRIGGERED" if result["observed"] else "GAPS"
    return result


def build_strategy_research_failure_conditions_v4(
    *,
    strategy_id: str,
    parameter_stability: dict[str, Any] | None,
    cost_sensitivity: dict[str, Any] | None,
    chronological_slices: dict[str, Any] | None,
    implementation_currentness: dict[str, Any] | None,
    full_implementation_currentness: dict[str, Any] | None,
    post_selection_replay_summary: dict[str, Any] | None,
    preregistered_failure_admission: dict[str, Any] | None,
    search_lineage: dict[str, Any] | None,
) -> dict[str, Any]:
    """Add schema-14 search-lineage scope without claiming a current registry.

    ``BOUND`` means the persisted report records a live registry verification at
    selection time.  ``BLOCK`` means only the preregistration receipt is
    self-consistent, so the missing live-at-selection verification is an
    observed research failure rather than a current-database claim.
    """

    result = build_strategy_research_failure_conditions_v3(
        strategy_id=strategy_id,
        parameter_stability=parameter_stability,
        cost_sensitivity=cost_sensitivity,
        chronological_slices=chronological_slices,
        implementation_currentness=implementation_currentness,
        full_implementation_currentness=full_implementation_currentness,
        post_selection_replay_summary=post_selection_replay_summary,
        preregistered_failure_admission=preregistered_failure_admission,
    )
    result["schema_version"] = STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V4
    lineage = deepcopy(search_lineage) if isinstance(search_lineage, dict) else {}
    lineage_status = str(lineage.get("status") or "UNKNOWN").upper()
    result["search_lineage_status"] = lineage_status[:32]
    if not str(strategy_id or "").strip():
        return result

    if lineage_status == "BOUND":
        triggered: bool | None = False
    elif lineage_status == "BLOCK":
        triggered = True
    else:
        triggered = None
    condition_id = "search_lineage_live_at_selection_not_verified"
    conditions = list(result.get("conditions") or [])
    conditions.append({
        "condition_id": condition_id,
        "evidence_status": lineage_status[:32],
        "triggered": triggered,
        "blockers": _strings(lineage.get("blockers")),
    })
    observed = list(result.get("observed") or [])
    evidence_gaps = list(result.get("evidence_gaps") or [])
    if triggered is True:
        observed.append(condition_id)
    elif triggered is None:
        evidence_gaps.append(f"{condition_id}_not_checked")
    result["observed"] = list(dict.fromkeys(observed))[:24]
    result["evidence_gaps"] = list(dict.fromkeys(evidence_gaps))[:24]
    result["conditions"] = conditions
    result["status"] = "TRIGGERED" if result["observed"] else "GAPS"
    return result


__all__ = [
    "STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V2",
    "STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V3",
    "STRATEGY_RESEARCH_FAILURE_CONDITIONS_SCHEMA_VERSION_V4",
    "build_strategy_research_failure_conditions",
    "build_strategy_research_failure_conditions_v2",
    "build_strategy_research_failure_conditions_v3",
    "build_strategy_research_failure_conditions_v4",
]
