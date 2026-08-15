from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .execution_authority import authority_violations
from .portfolio_forward_performance import (
    forward_evidence_thresholds_from_spec,
    forward_evidence_thresholds_v3_from_spec,
    verify_forward_performance_settlement,
)
from .portfolio_statistical_audit import (
    PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION,
    audit_paired_equity_curve_stage,
    statistical_bootstrap_budget_blockers,
)


PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION = "portfolio-forward-statistical-audit-v1"
PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION = "portfolio-forward-statistical-audit-v2"
PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION = "portfolio-forward-series-evidence-v1"
PORTFOLIO_FORWARD_STATISTICAL_CONTRACT_SCHEMA_VERSION = "portfolio-forward-statistical-contract-v1"
PORTFOLIO_FORWARD_DECISION_WINDOW_SCHEMA_VERSION = (
    "portfolio-forward-first-joint-maturity-decision-v1"
)
PORTFOLIO_FORWARD_RISK_ACCEPTANCE_SCHEMA_VERSION = (
    "portfolio-forward-first-joint-maturity-risk-acceptance-v1"
)
PORTFOLIO_FORWARD_DECISION_POLICY = "FIRST_JOINT_MATURITY_SINGLE_LOOK"
_MAX_SAFE_INTEGER = 9_007_199_254_740_991

FORWARD_STATISTICAL_AUDIT_CONTENT_FIELDS = (
    "schema_version",
    "status",
    "conclusion",
    "blockers",
    "input_binding",
    "maturity",
    "contract_comparison",
    "statistical_contract",
    "series_evidence",
    "stage",
    "checks",
    "evidence_scope",
    "profitability_proven",
    "research_only",
    "observation_only",
    "simulation_only",
    "paper_authorized",
    "live_order_allowed",
)

FORWARD_STATISTICAL_AUDIT_V2_CONTENT_FIELDS = (
    *FORWARD_STATISTICAL_AUDIT_CONTENT_FIELDS,
    "decision_window",
)

_COPIED_STATISTICAL_CONTRACT_FIELDS = (
    "method",
    "periods_per_year",
    "resample_count",
    "block_length",
    "confidence_level",
    "required_positive_probability",
    "required_selection_adjusted_probability",
    "selection_adjustment",
    "selection_trial_count",
)


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def forward_statistical_audit_content(report: dict[str, Any]) -> dict[str, Any]:
    return {key: report.get(key) for key in FORWARD_STATISTICAL_AUDIT_CONTENT_FIELDS}


def forward_statistical_audit_v2_content(report: dict[str, Any]) -> dict[str, Any]:
    return {key: report.get(key) for key in FORWARD_STATISTICAL_AUDIT_V2_CONTENT_FIELDS}


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _strict_positive_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _v2_safe_integer(value: Any, *, minimum: int = 0) -> int | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > _MAX_SAFE_INTEGER
    ):
        return None
    return value


def _v2_container_cycle_detected(payload: Any) -> bool:
    """Detect built-in container cycles without recursive traversal."""

    if not isinstance(payload, (dict, list, tuple)):
        return False
    active: set[int] = set()
    complete: set[int] = set()
    stack: list[tuple[Any, bool]] = [(payload, False)]
    while stack:
        value, exiting = stack.pop()
        if not isinstance(value, (dict, list, tuple)):
            continue
        identity = id(value)
        if exiting:
            active.discard(identity)
            complete.add(identity)
            continue
        if identity in active:
            return True
        if identity in complete:
            continue
        active.add(identity)
        stack.append((value, True))
        children = value.values() if isinstance(value, dict) else value
        stack.extend((child, False) for child in children)
    return False


def _historical_contract(
    *,
    candidate: dict[str, Any],
    historical_statistical_audit: dict[str, Any],
    forward_minimum_observations: int,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    source = dict(historical_statistical_audit or {})
    source_config = dict(source.get("config") or {})
    spec = dict(candidate.get("spec") or {})
    blockers: list[str] = []

    if source.get("schema_version") != PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION:
        blockers.append("historical_statistical_audit_schema_invalid")
    if source.get("verification_status") != "PASS":
        blockers.append("historical_statistical_audit_not_verified")
    if source.get("semantic_recomputed") is not True:
        blockers.append("historical_statistical_audit_not_semantically_recomputed")
    if source.get("status") not in {"PASS", "BLOCK"}:
        blockers.append("historical_statistical_audit_claim_status_invalid")
    if source.get("research_only") is not True:
        blockers.append("historical_statistical_audit_research_only_invalid")
    if source.get("paper_authorized") is not False:
        blockers.append("historical_statistical_audit_paper_authority_invalid")
    if source.get("live_order_allowed") is not False:
        blockers.append("historical_statistical_audit_live_authority_invalid")
    for field in ("audit_hash", "artifact_hash"):
        if not str(source.get(field) or ""):
            blockers.append(f"historical_statistical_audit_identity_missing:{field}")

    input_binding = dict(source.get("input_binding") or {})
    supplied_historical_binding_hash = str(input_binding.get("binding_hash") or "")
    historical_binding_content = dict(input_binding)
    historical_binding_content.pop("binding_hash", None)
    if not supplied_historical_binding_hash or supplied_historical_binding_hash != _canonical_hash(
        historical_binding_content
    ):
        blockers.append("historical_statistical_audit_input_binding_hash_invalid")
    candidate_hash = str(candidate.get("candidate_hash") or "")
    candidate_spec_hash = str(candidate.get("spec_hash") or _canonical_hash(spec))
    if str(input_binding.get("candidate_hash") or "") != candidate_hash:
        blockers.append("historical_statistical_audit_candidate_mismatch")
    if str(input_binding.get("spec_hash") or "") != candidate_spec_hash:
        blockers.append("historical_statistical_audit_spec_mismatch")

    integer_contract = {
        "periods_per_year": 2,
        "resample_count": 100,
        "block_length": 1,
        "minimum_observations": 2,
        "selection_trial_count": 1,
    }
    for field, floor in integer_contract.items():
        value = _strict_positive_integer(source_config.get(field))
        if value is None or value < floor:
            blockers.append(f"historical_statistical_config_invalid:{field}")

    probability_fields = (
        "confidence_level",
        "required_positive_probability",
        "required_selection_adjusted_probability",
    )
    for field in probability_fields:
        value = _finite_number(source_config.get(field))
        if value is None or value < 0.50 or value > 1.0:
            blockers.append(f"historical_statistical_config_invalid:{field}")
    if source_config.get("method") != "PAIRED_CIRCULAR_MOVING_BLOCK":
        blockers.append("historical_statistical_config_invalid:method")
    if source_config.get("periods_per_year") != 252:
        blockers.append("historical_statistical_config_invalid:periods_per_year")
    if source_config.get("selection_adjustment") != "BONFERRONI_ONE_SIDED":
        blockers.append("historical_statistical_config_invalid:selection_adjustment")

    frozen_trial_count = spec.get("trial_count")
    if frozen_trial_count is None:
        frozen_trial_count = candidate.get("development_trial_count")
    if _strict_positive_integer(frozen_trial_count) is None:
        blockers.append("candidate_development_trial_count_invalid")
    elif source_config.get("selection_trial_count") != frozen_trial_count:
        blockers.append("historical_statistical_trial_count_mismatch")

    copied_contract = {
        field: source_config.get(field)
        for field in _COPIED_STATISTICAL_CONTRACT_FIELDS
    }
    statistical_contract = {
        "schema_version": PORTFOLIO_FORWARD_STATISTICAL_CONTRACT_SCHEMA_VERSION,
        **copied_contract,
        "minimum_observations": int(forward_minimum_observations),
        "minimum_observations_policy": "FROZEN_CANDIDATE_FORWARD_MATURITY_FLOOR",
        "source_historical_minimum_observations": source_config.get("minimum_observations"),
        "source_historical_audit_schema_version": str(source.get("schema_version") or ""),
        "source_historical_audit_hash": str(source.get("audit_hash") or ""),
        "source_historical_artifact_hash": str(source.get("artifact_hash") or ""),
        "source_historical_claim_status": str(source.get("status") or ""),
        "source_historical_config_hash": _canonical_hash(source_config),
        "source_historical_input_binding_hash": supplied_historical_binding_hash,
    }
    statistical_contract["contract_hash"] = _canonical_hash(statistical_contract)

    field_comparison = {
        field: {
            "historical": source_config.get(field),
            "forward": statistical_contract.get(field),
            "matches": source_config.get(field) == statistical_contract.get(field),
        }
        for field in _COPIED_STATISTICAL_CONTRACT_FIELDS
    }
    contract_comparison = {
        "status": (
            "PASS"
            if not blockers and all(item["matches"] for item in field_comparison.values())
            else "BLOCK"
        ),
        "copied_fields": field_comparison,
        "allowed_difference": {
            "field": "minimum_observations",
            "historical": source_config.get("minimum_observations"),
            "forward": int(forward_minimum_observations),
            "reason": "FROZEN_CANDIDATE_FORWARD_MATURITY_FLOOR",
        },
        "other_differences_allowed": False,
    }
    return statistical_contract, contract_comparison, list(dict.fromkeys(blockers))


def _forward_series_evidence(
    *,
    candidate: dict[str, Any],
    settlements: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    candidate_hash = str(candidate.get("candidate_hash") or "")
    blockers: list[str] = []
    rows: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None

    if not candidate_hash:
        blockers.append("candidate_hash_missing")

    for index, raw_settlement in enumerate(settlements):
        settlement = dict(raw_settlement or {})
        verification = verify_forward_performance_settlement(settlement, previous)
        if verification.get("status") != "PASS":
            blockers.extend(
                f"settlement:{index}:{item}"
                for item in verification.get("blockers") or ["verification_blocked"]
            )
        if str(settlement.get("candidate_hash") or "") != candidate_hash:
            blockers.append(f"settlement:{index}:candidate_mismatch")
        strategy = dict(settlement.get("strategy") or {})
        benchmark = dict(settlement.get("benchmark") or {})
        strategy_equity = _finite_number(strategy.get("equity"))
        benchmark_equity = _finite_number(benchmark.get("equity"))
        strategy_return = _finite_number(strategy.get("daily_return_pct"))
        benchmark_return = _finite_number(benchmark.get("daily_return_pct"))
        if strategy_equity is None or strategy_equity <= 0:
            blockers.append(f"settlement:{index}:strategy_equity_invalid")
        if benchmark_equity is None or benchmark_equity <= 0:
            blockers.append(f"settlement:{index}:benchmark_equity_invalid")
        if strategy_return is None:
            blockers.append(f"settlement:{index}:strategy_daily_return_invalid")
        if benchmark_return is None:
            blockers.append(f"settlement:{index}:benchmark_daily_return_invalid")
        decision = dict(settlement.get("decision_execution") or {})
        rows.append({
            "date": str(settlement.get("settlement_date") or ""),
            "settlement_type": str(settlement.get("settlement_type") or ""),
            "settlement_hash": str(settlement.get("settlement_hash") or ""),
            "previous_settlement_hash": str(settlement.get("previous_settlement_hash") or ""),
            "strategy_equity": strategy_equity,
            "benchmark_equity": benchmark_equity,
            "strategy_daily_return_pct": strategy_return,
            "benchmark_daily_return_pct": benchmark_return,
            "rebalance_executed": bool(
                decision.get("execute") is True
                and str(decision.get("reason") or "") == "relative_strength_rebalance"
                and str(decision.get("status") or "") in {"EXECUTED", "EXECUTED_NO_FILL"}
            ),
        })
        previous = settlement

    dates = [str(item.get("date") or "") for item in rows]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        blockers.append("forward_settlement_dates_invalid")
    if rows and rows[0].get("settlement_type") != "BASELINE":
        blockers.append("forward_series_baseline_missing")
    if sum(item.get("settlement_type") == "BASELINE" for item in rows) != (1 if rows else 0):
        blockers.append("forward_series_baseline_count_invalid")

    content = {
        "schema_version": PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION,
        "candidate_hash": candidate_hash,
        "settlement_count": len(rows),
        "outcome_period_count": max(len(rows) - 1, 0),
        "rebalance_execution_count": sum(bool(item.get("rebalance_executed")) for item in rows),
        "first_settlement_date": dates[0] if dates else "",
        "last_settlement_date": dates[-1] if dates else "",
        "first_settlement_hash": str(rows[0].get("settlement_hash") or "") if rows else "",
        "latest_settlement_hash": str(rows[-1].get("settlement_hash") or "") if rows else "",
        "ordered_settlement_hashes": [str(item.get("settlement_hash") or "") for item in rows],
        "rows": rows,
        "source_validation": "FULL_SETTLEMENT_SEMANTIC_CHAIN_RECOMPUTED",
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "series_hash": _canonical_hash(content)}, list(dict.fromkeys(blockers))


def first_joint_maturity_prefix(
    series_evidence: dict[str, Any],
    *,
    required_forward_outcomes: int,
    required_executed_rebalances: int,
) -> dict[str, Any]:
    """Locate the immutable first prefix where both forward thresholds are met."""

    blockers: list[str] = []
    required_outcomes = _v2_safe_integer(required_forward_outcomes, minimum=1)
    required_rebalances = _v2_safe_integer(required_executed_rebalances, minimum=1)
    if required_outcomes is None:
        blockers.append("required_forward_outcomes_invalid")
    if required_rebalances is None:
        blockers.append("required_executed_rebalances_invalid")

    evidence = dict(series_evidence or {})
    rows_value = evidence.get("rows")
    rows = list(rows_value) if isinstance(rows_value, list) else []
    if not isinstance(rows_value, list):
        blockers.append("series_rows_invalid")
    if evidence.get("schema_version") != PORTFOLIO_FORWARD_SERIES_EVIDENCE_SCHEMA_VERSION:
        blockers.append("series_schema_invalid")
    settlement_count = evidence.get("settlement_count")
    if (
        _v2_safe_integer(settlement_count) is None
        or settlement_count != len(rows)
    ):
        blockers.append("series_settlement_count_invalid")
    expected_outcomes = max(len(rows) - 1, 0)
    supplied_outcomes = evidence.get("outcome_period_count")
    if (
        _v2_safe_integer(supplied_outcomes) is None
        or supplied_outcomes != expected_outcomes
    ):
        blockers.append("series_outcome_count_invalid")

    rebalance_count = 0
    first_due_index: int | None = None
    for index, raw_row in enumerate(rows):
        if not isinstance(raw_row, dict):
            blockers.append(f"series_row_invalid:{index}")
            continue
        executed = raw_row.get("rebalance_executed")
        if not isinstance(executed, bool):
            blockers.append(f"series_rebalance_flag_invalid:{index}")
            continue
        rebalance_count += int(executed)
        outcome_count = max(index, 0)
        if (
            first_due_index is None
            and required_outcomes is not None
            and required_rebalances is not None
            and outcome_count >= required_outcomes
            and rebalance_count >= required_rebalances
        ):
            first_due_index = index

    supplied_rebalances = evidence.get("rebalance_execution_count")
    if (
        _v2_safe_integer(supplied_rebalances) is None
        or supplied_rebalances != rebalance_count
    ):
        blockers.append("series_rebalance_count_invalid")

    status = "BLOCK" if blockers else ("DUE" if first_due_index is not None else "NOT_DUE")
    if first_due_index is None:
        return {
            "status": status,
            "policy": PORTFOLIO_FORWARD_DECISION_POLICY,
            "required_forward_outcomes": required_outcomes or 0,
            "required_executed_rebalances": required_rebalances or 0,
            "first_due_settlement_index": None,
            "settlement_count": 0,
            "outcome_period_count": 0,
            "rebalance_execution_count": 0,
            "first_due_settlement_date": "",
            "first_due_settlement_hash": "",
            "blockers": list(dict.fromkeys(blockers)),
        }

    due_row = dict(rows[first_due_index])
    prefix_rows = [dict(item) for item in rows[: first_due_index + 1]]
    return {
        "status": status,
        "policy": PORTFOLIO_FORWARD_DECISION_POLICY,
        "required_forward_outcomes": int(required_outcomes or 0),
        "required_executed_rebalances": int(required_rebalances or 0),
        "first_due_settlement_index": first_due_index,
        "settlement_count": len(prefix_rows),
        "outcome_period_count": max(len(prefix_rows) - 1, 0),
        "rebalance_execution_count": sum(
            int(item.get("rebalance_executed") is True) for item in prefix_rows
        ),
        "first_due_settlement_date": str(due_row.get("date") or ""),
        "first_due_settlement_hash": str(due_row.get("settlement_hash") or ""),
        "blockers": list(dict.fromkeys(blockers)),
    }


def audit_forward_portfolio_statistics(
    *,
    candidate: dict[str, Any],
    settlements: list[dict[str, Any]],
    historical_statistical_audit: dict[str, Any],
    generated_at: int = 0,
) -> dict[str, Any]:
    frozen_candidate = dict(candidate or {})
    spec = dict(frozen_candidate.get("spec") or {})
    threshold_contract = forward_evidence_thresholds_from_spec(spec)
    required_outcomes = int(threshold_contract["minimum_forward_performance_outcomes"])
    required_rebalances = int(threshold_contract["minimum_planned_rebalances"])
    series_evidence, series_blockers = _forward_series_evidence(
        candidate=frozen_candidate,
        settlements=[dict(item or {}) for item in settlements or []],
    )
    statistical_contract, contract_comparison, contract_blockers = _historical_contract(
        candidate=frozen_candidate,
        historical_statistical_audit=dict(historical_statistical_audit or {}),
        forward_minimum_observations=required_outcomes,
    )
    authority_blockers: list[str] = []
    if frozen_candidate.get("research_only") is not True:
        authority_blockers.append("candidate_not_research_only")
    if frozen_candidate.get("paper_authorized") is not False:
        authority_blockers.append("candidate_contains_paper_authority")
    if frozen_candidate.get("live_order_allowed") is not False:
        authority_blockers.append("candidate_contains_live_authority")
    threshold_blockers: list[str] = []
    if threshold_contract.get("status") != "PASS":
        threshold_blockers.extend(
            f"forward_threshold:{item}"
            for item in threshold_contract.get("issues") or ["invalid"]
        )

    outcome_count = int(series_evidence.get("outcome_period_count") or 0)
    rebalance_count = int(series_evidence.get("rebalance_execution_count") or 0)
    due = outcome_count >= required_outcomes and rebalance_count >= required_rebalances
    maturity = {
        "status": "DUE" if due else "NOT_DUE",
        "forward_outcomes": outcome_count,
        "required_forward_outcomes": required_outcomes,
        "remaining_forward_outcomes": max(required_outcomes - outcome_count, 0),
        "executed_rebalances": rebalance_count,
        "required_executed_rebalances": required_rebalances,
        "remaining_executed_rebalances": max(required_rebalances - rebalance_count, 0),
        "both_thresholds_required": True,
    }

    historical = dict(historical_statistical_audit or {})
    input_binding = {
        "candidate_hash": str(frozen_candidate.get("candidate_hash") or ""),
        "candidate_spec_hash": _canonical_hash(spec),
        "candidate_declared_spec_hash": str(frozen_candidate.get("spec_hash") or ""),
        "historical_statistical_audit_schema_version": str(historical.get("schema_version") or ""),
        "historical_statistical_audit_hash": str(historical.get("audit_hash") or ""),
        "historical_statistical_artifact_hash": str(historical.get("artifact_hash") or ""),
        "historical_statistical_config_hash": _canonical_hash(dict(historical.get("config") or {})),
        "historical_statistical_input_binding_hash": str(
            dict(historical.get("input_binding") or {}).get("binding_hash") or ""
        ),
        "statistical_contract_hash": str(statistical_contract.get("contract_hash") or ""),
        "forward_threshold_contract_hash": _canonical_hash(threshold_contract),
        "forward_series_hash": str(series_evidence.get("series_hash") or ""),
        "ordered_settlement_hashes_hash": _canonical_hash(
            list(series_evidence.get("ordered_settlement_hashes") or [])
        ),
        "first_settlement_date": str(series_evidence.get("first_settlement_date") or ""),
        "last_settlement_date": str(series_evidence.get("last_settlement_date") or ""),
        "first_settlement_hash": str(series_evidence.get("first_settlement_hash") or ""),
        "latest_settlement_hash": str(series_evidence.get("latest_settlement_hash") or ""),
        "settlement_count": int(series_evidence.get("settlement_count") or 0),
        "outcome_period_count": outcome_count,
        "rebalance_execution_count": rebalance_count,
    }
    input_binding["binding_hash"] = _canonical_hash(input_binding)

    blockers = list(dict.fromkeys([
        *series_blockers,
        *contract_blockers,
        *threshold_blockers,
        *authority_blockers,
    ]))
    pre_stage_blockers = list(blockers)
    stage: dict[str, Any] = {}
    if due and not blockers:
        rows = list(series_evidence.get("rows") or [])
        baseline = dict(rows[0])
        outcomes = [dict(item) for item in rows[1:]]
        seed = int(_canonical_hash({
            "schema_version": PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
            "input_binding": input_binding,
            "statistical_contract": statistical_contract,
            "stage": "natural_forward",
        })[:16], 16)
        stage = audit_paired_equity_curve_stage(
            stage="natural_forward",
            strategy_report={
                "initial_cash": baseline.get("strategy_equity"),
                "equity_curve": [
                    {"date": item.get("date"), "equity": item.get("strategy_equity")}
                    for item in outcomes
                ],
            },
            benchmark_report={
                "initial_cash": baseline.get("benchmark_equity"),
                "equity_curve": [
                    {"date": item.get("date"), "equity": item.get("benchmark_equity")}
                    for item in outcomes
                ],
            },
            resample_count=int(statistical_contract["resample_count"]),
            block_length=int(statistical_contract["block_length"]),
            minimum_observations=int(statistical_contract["minimum_observations"]),
            confidence_level=float(statistical_contract["confidence_level"]),
            required_positive_probability=float(statistical_contract["required_positive_probability"]),
            required_adjusted_probability=float(
                statistical_contract["required_selection_adjusted_probability"]
            ),
            selection_trial_count=int(statistical_contract["selection_trial_count"]),
            seed=seed,
        )

    if due and stage.get("status") != "PASS":
        blockers.extend(
            f"natural_forward:{item}"
            for item in stage.get("blockers") or ["statistical_stage_not_passed"]
        )
    blockers = list(dict.fromkeys(blockers))
    checks = {
        "candidate_authority_is_research_only": not authority_blockers,
        "forward_threshold_contract_pass": threshold_contract.get("status") == "PASS",
        "settlement_series_integrity_pass": not series_blockers,
        "historical_statistical_contract_verified": not contract_blockers,
        "same_statistical_contract_except_forward_maturity_floor": contract_comparison.get("status") == "PASS",
        "maturity_requires_outcomes_and_rebalances": due,
        "natural_forward_statistical_stage_pass": stage.get("status") == "PASS" if due else False,
        "zero_execution_authority": True,
    }
    if pre_stage_blockers:
        status = "BLOCK"
        conclusion = "FORWARD_STATISTICAL_AUDIT_BLOCKED"
    elif not due:
        status = "NOT_DUE"
        conclusion = "FORWARD_STATISTICAL_AUDIT_NOT_DUE"
    elif stage.get("status") == "PASS":
        status = "PASS"
        conclusion = "FORWARD_STATISTICAL_CONTRACT_PASS"
    else:
        status = "BLOCK"
        conclusion = "FORWARD_STATISTICAL_CONTRACT_FAILED"

    content = {
        "schema_version": PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
        "status": status,
        "conclusion": conclusion,
        "blockers": blockers,
        "input_binding": input_binding,
        "maturity": maturity,
        "contract_comparison": contract_comparison,
        "statistical_contract": statistical_contract,
        "series_evidence": series_evidence,
        "stage": stage,
        "checks": checks,
        "evidence_scope": "NATURAL_FORWARD_PAIRED_PORTFOLIO_STATISTICS_ONLY",
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {
        **content,
        "generated_at": int(generated_at),
        "audit_hash": _canonical_hash(content),
    }


def verify_forward_portfolio_statistical_audit_semantics(
    audit: dict[str, Any],
    *,
    candidate: dict[str, Any],
    settlements: list[dict[str, Any]],
    historical_statistical_audit: dict[str, Any],
) -> dict[str, Any]:
    report = dict(audit or {})
    blockers: list[str] = []
    generated_at = report.get("generated_at")
    if isinstance(generated_at, bool) or not isinstance(generated_at, int) or generated_at <= 0:
        blockers.append("forward_statistical_audit_generated_at_invalid")
        generated_at = 0
    try:
        expected = audit_forward_portfolio_statistics(
            candidate=dict(candidate or {}),
            settlements=[dict(item or {}) for item in settlements or []],
            historical_statistical_audit=dict(historical_statistical_audit or {}),
            generated_at=generated_at,
        )
    except (TypeError, ValueError, OverflowError, KeyError) as exc:
        expected = {}
        blockers.append(f"forward_statistical_audit_recomputation_failed:{type(exc).__name__}")

    for field in FORWARD_STATISTICAL_AUDIT_CONTENT_FIELDS:
        if _canonical_hash(report.get(field)) != _canonical_hash(expected.get(field)):
            blockers.append(f"forward_statistical_audit_semantic_mismatch:{field}")
    if str(report.get("audit_hash") or "") != str(expected.get("audit_hash") or ""):
        blockers.append("forward_statistical_audit_semantic_hash_mismatch")
    if report.get("profitability_proven") is not False:
        blockers.append("forward_statistical_audit_profitability_claim_invalid")
    if report.get("research_only") is not True:
        blockers.append("forward_statistical_audit_research_only_invalid")
    if report.get("paper_authorized") is not False:
        blockers.append("forward_statistical_audit_paper_authority_invalid")
    if report.get("live_order_allowed") is not False:
        blockers.append("forward_statistical_audit_live_authority_invalid")

    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "claim_status": str(report.get("status") or "BLOCK"),
        "expected_status": str(expected.get("status") or "BLOCK"),
        "expected_conclusion": str(expected.get("conclusion") or ""),
        "expected_audit_hash": str(expected.get("audit_hash") or ""),
        "recomputed_from_verified_forward_settlements": bool(expected),
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _execution_authority_blockers(payload: Any, *, path: str) -> list[str]:
    try:
        return [
            f"execution_authority_violation:{item}"
            for item in authority_violations(payload, path=path)
        ]
    except RecursionError:
        return [f"execution_authority_scan_recursion_invalid:{path}"]


def _v2_historical_safe_integer_blockers(
    *,
    candidate: dict[str, Any],
    historical_statistical_audit: dict[str, Any],
) -> list[str]:
    config = dict(historical_statistical_audit.get("config") or {})
    blockers = [
        f"historical_statistical_config_unsafe_integer:{field}"
        for field in (
            "periods_per_year",
            "resample_count",
            "block_length",
            "minimum_observations",
            "selection_trial_count",
        )
        if _v2_safe_integer(config.get(field), minimum=1) is None
    ]
    spec = dict(candidate.get("spec") or {})
    trial_count = spec.get("trial_count")
    if trial_count is None:
        trial_count = candidate.get("development_trial_count")
    if _v2_safe_integer(trial_count, minimum=1) is None:
        blockers.append("candidate_development_trial_count_unsafe_integer")
    blockers.extend(
        f"historical_statistical_compute_budget:{item}"
        for item in statistical_bootstrap_budget_blockers(
            resample_count=config.get("resample_count"),
            block_length=config.get("block_length"),
        )
    )
    return blockers


def _v2_prefix_risk_acceptance(
    *,
    spec: dict[str, Any],
    prefix: dict[str, Any],
    decision_series_evidence: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    acceptance = spec.get("acceptance_contract")
    acceptance_contract = dict(acceptance) if isinstance(acceptance, dict) else {}
    raw_limit = acceptance_contract.get("validation_and_test_max_drawdown_below_pct")
    limit = (
        float(raw_limit)
        if isinstance(raw_limit, (int, float))
        and not isinstance(raw_limit, bool)
        and math.isfinite(float(raw_limit))
        and float(raw_limit) > 0.0
        else None
    )
    integrity_blockers: list[str] = []
    evidence_blockers: list[str] = []
    if not isinstance(acceptance, dict):
        integrity_blockers.append("risk_acceptance_contract_invalid")
    if limit is None:
        integrity_blockers.append("risk_acceptance_drawdown_limit_invalid")

    prefix_due = prefix.get("status") == "DUE"
    max_drawdown_pct: float | None = None
    if prefix_due:
        rows_value = decision_series_evidence.get("rows")
        rows = list(rows_value) if isinstance(rows_value, list) else []
        if not rows:
            integrity_blockers.append("risk_acceptance_prefix_rows_missing")
        peak: float | None = None
        max_drawdown = 0.0
        for index, raw_row in enumerate(rows):
            row = dict(raw_row) if isinstance(raw_row, dict) else {}
            equity = _finite_number(row.get("strategy_equity"))
            if equity is None or equity <= 0.0:
                integrity_blockers.append(
                    f"risk_acceptance_strategy_equity_invalid:{index}"
                )
                continue
            peak = equity if peak is None else max(peak, equity)
            drawdown = ((peak - equity) / peak) * 100.0
            max_drawdown = max(max_drawdown, drawdown)
        if not integrity_blockers:
            max_drawdown_pct = round(max_drawdown, 10)
            if limit is not None and not max_drawdown_pct < limit:
                evidence_blockers.append("risk_acceptance_max_drawdown_not_below_limit")

    if integrity_blockers:
        status = "BLOCK"
    elif not prefix_due:
        status = "NOT_DUE"
    elif evidence_blockers:
        status = "BLOCK"
    else:
        status = "PASS"
    content = {
        "schema_version": PORTFOLIO_FORWARD_RISK_ACCEPTANCE_SCHEMA_VERSION,
        "status": status,
        "method": "PREFIX_STRATEGY_EQUITY_PEAK_TO_TROUGH_MAX_DRAWDOWN",
        "comparison": "STRICTLY_BELOW",
        "threshold_field": "validation_and_test_max_drawdown_below_pct",
        "required_max_drawdown_below_pct": limit,
        "prefix_max_drawdown_pct": max_drawdown_pct,
        "prefix_settlement_count": prefix.get("settlement_count") if prefix_due else 0,
        "prefix_outcome_period_count": prefix.get("outcome_period_count") if prefix_due else 0,
        "prefix_first_due_settlement_hash": (
            str(prefix.get("first_due_settlement_hash") or "") if prefix_due else ""
        ),
        "decision_series_hash": str(decision_series_evidence.get("series_hash") or ""),
        "checks": {
            "frozen_drawdown_limit_valid": limit is not None,
            "prefix_strategy_equity_valid": prefix_due and not integrity_blockers,
            "prefix_max_drawdown_strictly_below_limit": (
                prefix_due and not integrity_blockers and not evidence_blockers
            ),
        },
        "blockers": list(dict.fromkeys([*integrity_blockers, *evidence_blockers])),
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return (
        {**content, "risk_hash": _canonical_hash(content)},
        list(dict.fromkeys(integrity_blockers)),
        list(dict.fromkeys(evidence_blockers)),
    )


def _audit_forward_portfolio_statistics_v2_core(
    *,
    candidate: dict[str, Any],
    settlements: list[dict[str, Any]],
    historical_statistical_audit: dict[str, Any],
    generated_at: int = 0,
) -> dict[str, Any]:
    """Audit exactly once at the first joint maturity prefix.

    The complete chain remains part of current artifact integrity, while the
    statistical decision and its hash bind only the first prefix where both
    frozen maturity thresholds were satisfied.
    """

    frozen_candidate = dict(candidate or {})
    frozen_settlements = [dict(item or {}) for item in settlements or []]
    historical = dict(historical_statistical_audit or {})
    spec = dict(frozen_candidate.get("spec") or {})
    threshold_contract = forward_evidence_thresholds_v3_from_spec(spec)
    required_outcomes = int(threshold_contract["minimum_forward_performance_outcomes"])
    required_rebalances = int(threshold_contract["minimum_planned_rebalances"])
    series_evidence, series_blockers = _forward_series_evidence(
        candidate=frozen_candidate,
        settlements=frozen_settlements,
    )
    statistical_contract, contract_comparison, contract_blockers = _historical_contract(
        candidate=frozen_candidate,
        historical_statistical_audit=historical,
        forward_minimum_observations=required_outcomes,
    )
    contract_blockers = list(dict.fromkeys([
        *contract_blockers,
        *_v2_historical_safe_integer_blockers(
            candidate=frozen_candidate,
            historical_statistical_audit=historical,
        ),
    ]))

    threshold_blockers = [
        f"forward_threshold:{item}"
        for item in threshold_contract.get("issues") or []
    ]
    candidate_authority_blockers: list[str] = []
    if frozen_candidate.get("research_only") is not True:
        candidate_authority_blockers.append("candidate_not_research_only")
    if frozen_candidate.get("paper_authorized") is not False:
        candidate_authority_blockers.append("candidate_contains_paper_authority")
    if frozen_candidate.get("live_order_allowed") is not False:
        candidate_authority_blockers.append("candidate_contains_live_authority")
    candidate_authority_blockers.extend(
        _execution_authority_blockers(frozen_candidate, path="$.candidate")
    )
    historical_authority_blockers = _execution_authority_blockers(
        historical,
        path="$.historical_statistical_audit",
    )
    settlement_authority_blockers = _execution_authority_blockers(
        frozen_settlements,
        path="$.settlements",
    )

    outcome_count = int(series_evidence.get("outcome_period_count") or 0)
    rebalance_count = int(series_evidence.get("rebalance_execution_count") or 0)
    due = outcome_count >= required_outcomes and rebalance_count >= required_rebalances
    prefix = first_joint_maturity_prefix(
        series_evidence,
        required_forward_outcomes=required_outcomes,
        required_executed_rebalances=required_rebalances,
    )
    prefix_blockers = [
        f"first_joint_maturity_prefix:{item}"
        for item in prefix.get("blockers") or []
    ]
    maturity = {
        "status": "DUE" if due else "NOT_DUE",
        "forward_outcomes": outcome_count,
        "required_forward_outcomes": required_outcomes,
        "remaining_forward_outcomes": max(required_outcomes - outcome_count, 0),
        "executed_rebalances": rebalance_count,
        "required_executed_rebalances": required_rebalances,
        "remaining_executed_rebalances": max(required_rebalances - rebalance_count, 0),
        "both_thresholds_required": True,
        "decision_policy": PORTFOLIO_FORWARD_DECISION_POLICY,
        "first_joint_maturity_status": str(prefix.get("status") or "BLOCK"),
        "first_due_settlement_index": prefix.get("first_due_settlement_index"),
        "first_due_settlement_date": str(prefix.get("first_due_settlement_date") or ""),
        "first_due_settlement_hash": str(prefix.get("first_due_settlement_hash") or ""),
    }

    decision_settlements: list[dict[str, Any]] = []
    decision_series_evidence: dict[str, Any] = {}
    decision_series_blockers: list[str] = []
    first_due_index = prefix.get("first_due_settlement_index")
    if prefix.get("status") == "DUE" and isinstance(first_due_index, int):
        decision_settlements = frozen_settlements[: first_due_index + 1]
        decision_series_evidence, raw_decision_series_blockers = _forward_series_evidence(
            candidate=frozen_candidate,
            settlements=decision_settlements,
        )
        decision_series_blockers = [
            f"decision_prefix:{item}" for item in raw_decision_series_blockers
        ]
    decision_compute_budget_blockers = (
        [
            f"decision_prefix_compute_budget:{item}"
            for item in statistical_bootstrap_budget_blockers(
                resample_count=statistical_contract.get("resample_count"),
                block_length=statistical_contract.get("block_length"),
                sample_size=decision_series_evidence.get("outcome_period_count"),
            )
        ]
        if prefix.get("status") == "DUE"
        else []
    )

    risk_acceptance, raw_risk_integrity_blockers, raw_risk_evidence_blockers = (
        _v2_prefix_risk_acceptance(
            spec=spec,
            prefix=prefix,
            decision_series_evidence=decision_series_evidence,
        )
    )
    risk_integrity_blockers = [
        f"first_joint_maturity_risk:{item}"
        for item in raw_risk_integrity_blockers
    ]
    risk_evidence_blockers = [
        f"first_joint_maturity_risk:{item}"
        for item in raw_risk_evidence_blockers
    ]

    decision_authority_blockers = [
        *candidate_authority_blockers,
        *historical_authority_blockers,
        *_execution_authority_blockers(
            decision_settlements,
            path="$.decision_settlements",
        ),
    ]
    decision_pre_stage_blockers = list(dict.fromkeys([
        *contract_blockers,
        *threshold_blockers,
        *prefix_blockers,
        *decision_series_blockers,
        *decision_compute_budget_blockers,
        *decision_authority_blockers,
        *risk_integrity_blockers,
    ]))

    stage: dict[str, Any] = {}
    if prefix.get("status") == "DUE" and not decision_pre_stage_blockers:
        decision_rows = [dict(item) for item in decision_series_evidence.get("rows") or []]
        baseline = dict(decision_rows[0])
        outcomes = [dict(item) for item in decision_rows[1:]]
        seed = int(_canonical_hash({
            "schema_version": PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
            "decision_policy": PORTFOLIO_FORWARD_DECISION_POLICY,
            "candidate_hash": str(frozen_candidate.get("candidate_hash") or ""),
            "candidate_spec_hash": _canonical_hash(spec),
            "statistical_contract_hash": str(statistical_contract.get("contract_hash") or ""),
            "forward_threshold_contract_hash": _canonical_hash(threshold_contract),
            "decision_series_hash": str(decision_series_evidence.get("series_hash") or ""),
            "first_joint_maturity_prefix": prefix,
        })[:16], 16)
        stage = audit_paired_equity_curve_stage(
            stage="natural_forward_first_joint_maturity",
            strategy_report={
                "initial_cash": baseline.get("strategy_equity"),
                "equity_curve": [
                    {"date": item.get("date"), "equity": item.get("strategy_equity")}
                    for item in outcomes
                ],
            },
            benchmark_report={
                "initial_cash": baseline.get("benchmark_equity"),
                "equity_curve": [
                    {"date": item.get("date"), "equity": item.get("benchmark_equity")}
                    for item in outcomes
                ],
            },
            resample_count=int(statistical_contract["resample_count"]),
            block_length=int(statistical_contract["block_length"]),
            minimum_observations=int(statistical_contract["minimum_observations"]),
            confidence_level=float(statistical_contract["confidence_level"]),
            required_positive_probability=float(
                statistical_contract["required_positive_probability"]
            ),
            required_adjusted_probability=float(
                statistical_contract["required_selection_adjusted_probability"]
            ),
            selection_trial_count=int(statistical_contract["selection_trial_count"]),
            seed=seed,
        )

    decision_stage_blockers = (
        [
            f"natural_forward_first_joint_maturity:{item}"
            for item in stage.get("blockers") or ["statistical_stage_not_passed"]
        ]
        if prefix.get("status") == "DUE"
        and not decision_pre_stage_blockers
        and stage.get("status") != "PASS"
        else []
    )
    if decision_pre_stage_blockers:
        decision_window_status = "BLOCK"
        decision_status = "BLOCK"
        research_action = "BLOCK"
    elif prefix.get("status") != "DUE":
        decision_window_status = "NOT_DUE"
        decision_status = "NOT_DUE"
        research_action = "COLLECT_MORE"
    elif stage.get("status") == "PASS" and risk_acceptance.get("status") == "PASS":
        decision_window_status = "FROZEN"
        decision_status = "PASS"
        research_action = "REVIEW_REQUIRED"
    else:
        decision_window_status = "FROZEN"
        decision_status = "BLOCK"
        research_action = "STOP_RESEARCH"

    decision_window_content = {
        "schema_version": PORTFOLIO_FORWARD_DECISION_WINDOW_SCHEMA_VERSION,
        "policy": PORTFOLIO_FORWARD_DECISION_POLICY,
        "status": decision_window_status,
        "decision_status": decision_status,
        "research_action": research_action,
        "candidate_hash": str(frozen_candidate.get("candidate_hash") or ""),
        "candidate_spec_hash": _canonical_hash(spec),
        "candidate_declared_spec_hash": str(frozen_candidate.get("spec_hash") or ""),
        "forward_threshold_contract_hash": _canonical_hash(threshold_contract),
        "statistical_contract_hash": str(statistical_contract.get("contract_hash") or ""),
        "first_joint_maturity_prefix": prefix,
        "decision_series_hash": str(decision_series_evidence.get("series_hash") or ""),
        "stage_hash": str(stage.get("stage_hash") or ""),
        "risk_acceptance": risk_acceptance,
        "risk_acceptance_hash": str(risk_acceptance.get("risk_hash") or ""),
        "blockers": list(dict.fromkeys([
            *decision_pre_stage_blockers,
            *decision_stage_blockers,
            *risk_evidence_blockers,
        ])),
        "later_settlements_used": False,
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    decision_window = {
        **decision_window_content,
        "decision_hash": _canonical_hash(decision_window_content),
    }

    input_binding = {
        "candidate_hash": str(frozen_candidate.get("candidate_hash") or ""),
        "candidate_spec_hash": _canonical_hash(spec),
        "candidate_declared_spec_hash": str(frozen_candidate.get("spec_hash") or ""),
        "historical_statistical_audit_schema_version": str(historical.get("schema_version") or ""),
        "historical_statistical_audit_hash": str(historical.get("audit_hash") or ""),
        "historical_statistical_artifact_hash": str(historical.get("artifact_hash") or ""),
        "historical_statistical_config_hash": _canonical_hash(dict(historical.get("config") or {})),
        "historical_statistical_input_binding_hash": str(
            dict(historical.get("input_binding") or {}).get("binding_hash") or ""
        ),
        "statistical_contract_hash": str(statistical_contract.get("contract_hash") or ""),
        "forward_threshold_contract_hash": _canonical_hash(threshold_contract),
        "forward_series_hash": str(series_evidence.get("series_hash") or ""),
        "ordered_settlement_hashes_hash": _canonical_hash(
            list(series_evidence.get("ordered_settlement_hashes") or [])
        ),
        "first_settlement_date": str(series_evidence.get("first_settlement_date") or ""),
        "last_settlement_date": str(series_evidence.get("last_settlement_date") or ""),
        "first_settlement_hash": str(series_evidence.get("first_settlement_hash") or ""),
        "latest_settlement_hash": str(series_evidence.get("latest_settlement_hash") or ""),
        "settlement_count": int(series_evidence.get("settlement_count") or 0),
        "outcome_period_count": outcome_count,
        "rebalance_execution_count": rebalance_count,
        "decision_policy": PORTFOLIO_FORWARD_DECISION_POLICY,
        "decision_hash": str(decision_window.get("decision_hash") or ""),
        "decision_series_hash": str(decision_series_evidence.get("series_hash") or ""),
        "risk_acceptance_hash": str(risk_acceptance.get("risk_hash") or ""),
        "first_due_settlement_index": prefix.get("first_due_settlement_index"),
        "first_due_settlement_date": str(prefix.get("first_due_settlement_date") or ""),
        "first_due_settlement_hash": str(prefix.get("first_due_settlement_hash") or ""),
    }
    input_binding["binding_hash"] = _canonical_hash(input_binding)

    full_pre_stage_blockers = list(dict.fromkeys([
        *series_blockers,
        *contract_blockers,
        *threshold_blockers,
        *candidate_authority_blockers,
        *historical_authority_blockers,
        *settlement_authority_blockers,
        *prefix_blockers,
        *decision_series_blockers,
        *decision_compute_budget_blockers,
        *risk_integrity_blockers,
    ]))
    blockers = list(dict.fromkeys([
        *full_pre_stage_blockers,
        *decision_stage_blockers,
        *risk_evidence_blockers,
    ]))
    checks = {
        "candidate_authority_is_research_only": not candidate_authority_blockers,
        "forward_threshold_contract_pass": threshold_contract.get("status") == "PASS",
        "settlement_series_integrity_pass": not series_blockers,
        "historical_statistical_contract_verified": not contract_blockers,
        "same_statistical_contract_except_forward_maturity_floor": (
            contract_comparison.get("status") == "PASS"
        ),
        "maturity_requires_outcomes_and_rebalances": due,
        "first_joint_maturity_prefix_integrity_pass": not (
            prefix_blockers
            or decision_series_blockers
            or decision_compute_budget_blockers
        ),
        "single_statistical_look_uses_frozen_prefix_only": (
            decision_window.get("later_settlements_used") is False
        ),
        "natural_forward_statistical_stage_pass": (
            stage.get("status") == "PASS" if prefix.get("status") == "DUE" else False
        ),
        "first_joint_maturity_risk_acceptance_pass": (
            risk_acceptance.get("status") == "PASS"
            if prefix.get("status") == "DUE"
            else False
        ),
        "first_joint_maturity_risk_acceptance_integrity_pass": not risk_integrity_blockers,
        "zero_execution_authority": not (
            candidate_authority_blockers
            or historical_authority_blockers
            or settlement_authority_blockers
        ),
    }
    if full_pre_stage_blockers:
        status = "BLOCK"
        conclusion = "FORWARD_STATISTICAL_AUDIT_BLOCKED"
    elif prefix.get("status") != "DUE":
        status = "NOT_DUE"
        conclusion = "FORWARD_STATISTICAL_AUDIT_NOT_DUE"
    elif stage.get("status") == "PASS" and risk_acceptance.get("status") == "PASS":
        status = "PASS"
        conclusion = "FORWARD_FIRST_JOINT_MATURITY_RESEARCH_ACCEPTANCE_PASS"
    else:
        status = "BLOCK"
        conclusion = "FORWARD_FIRST_JOINT_MATURITY_RESEARCH_ACCEPTANCE_FAILED"

    content = {
        "schema_version": PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
        "status": status,
        "conclusion": conclusion,
        "blockers": blockers,
        "input_binding": input_binding,
        "maturity": maturity,
        "contract_comparison": contract_comparison,
        "statistical_contract": statistical_contract,
        "series_evidence": series_evidence,
        "stage": stage,
        "checks": checks,
        "evidence_scope": (
            "NATURAL_FORWARD_FIRST_JOINT_MATURITY_SINGLE_LOOK_"
            "PAIRED_PORTFOLIO_STATISTICS_AND_PREFIX_DRAWDOWN_ONLY"
        ),
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "decision_window": decision_window,
    }
    return {
        **content,
        "generated_at": int(generated_at),
        "audit_hash": _canonical_hash(content),
    }


def _blocked_v2_input_report(*, generated_at: int, blocker: str) -> dict[str, Any]:
    report = _audit_forward_portfolio_statistics_v2_core(
        candidate={},
        settlements=[],
        historical_statistical_audit={},
        generated_at=generated_at,
    )
    report["status"] = "BLOCK"
    report["conclusion"] = "FORWARD_STATISTICAL_AUDIT_BLOCKED"
    report["blockers"] = list(dict.fromkeys([blocker, *list(report.get("blockers") or [])]))
    checks = dict(report.get("checks") or {})
    checks["v2_input_integrity_pass"] = False
    report["checks"] = checks

    decision_window = dict(report.get("decision_window") or {})
    decision_window.update({
        "status": "BLOCK",
        "decision_status": "BLOCK",
        "research_action": "BLOCK",
        "blockers": list(dict.fromkeys([
            blocker,
            *list(decision_window.get("blockers") or []),
        ])),
    })
    decision_content = dict(decision_window)
    decision_content.pop("decision_hash", None)
    decision_window = {
        **decision_content,
        "decision_hash": _canonical_hash(decision_content),
    }
    report["decision_window"] = decision_window

    input_binding = dict(report.get("input_binding") or {})
    input_binding["decision_hash"] = decision_window["decision_hash"]
    input_binding.pop("binding_hash", None)
    input_binding["binding_hash"] = _canonical_hash(input_binding)
    report["input_binding"] = input_binding
    report["audit_hash"] = _canonical_hash(forward_statistical_audit_v2_content(report))
    return report


def audit_forward_portfolio_statistics_v2(
    *,
    candidate: dict[str, Any],
    settlements: list[dict[str, Any]],
    historical_statistical_audit: dict[str, Any],
    generated_at: int = 0,
) -> dict[str, Any]:
    """Audit the first joint maturity prefix and fail closed on recursive inputs."""

    named_inputs = {
        "candidate": candidate,
        "settlements": settlements,
        "historical_statistical_audit": historical_statistical_audit,
    }
    cyclic_inputs = [
        name for name, value in named_inputs.items() if _v2_container_cycle_detected(value)
    ]
    safe_generated_at = _v2_safe_integer(generated_at)
    if safe_generated_at is None:
        return _blocked_v2_input_report(
            generated_at=0,
            blocker="forward_statistical_audit_v2_generated_at_unsafe_integer",
        )
    if cyclic_inputs:
        return _blocked_v2_input_report(
            generated_at=safe_generated_at,
            blocker=(
                "forward_statistical_audit_v2_input_cycle_invalid:"
                + ",".join(cyclic_inputs)
            ),
        )
    try:
        return _audit_forward_portfolio_statistics_v2_core(
            candidate=candidate,
            settlements=settlements,
            historical_statistical_audit=historical_statistical_audit,
            generated_at=safe_generated_at,
        )
    except RecursionError:
        return _blocked_v2_input_report(
            generated_at=safe_generated_at,
            blocker="forward_statistical_audit_v2_input_recursion_invalid",
        )
    except ValueError as exc:
        if "circular reference" not in str(exc).casefold():
            raise
        return _blocked_v2_input_report(
            generated_at=safe_generated_at,
            blocker="forward_statistical_audit_v2_input_cycle_invalid",
        )


def verify_forward_portfolio_statistical_audit_v2_semantics(
    audit: dict[str, Any],
    *,
    candidate: dict[str, Any],
    settlements: list[dict[str, Any]],
    historical_statistical_audit: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if _v2_container_cycle_detected(audit):
        blockers.append("forward_statistical_audit_cycle_invalid")
        report: dict[str, Any] = {}
    else:
        report = dict(audit or {})
    generated_at = report.get("generated_at")
    if _v2_safe_integer(generated_at, minimum=1) is None:
        blockers.append("forward_statistical_audit_generated_at_invalid")
        generated_at = 0
    try:
        expected = audit_forward_portfolio_statistics_v2(
            candidate=dict(candidate or {}),
            settlements=[dict(item or {}) for item in settlements or []],
            historical_statistical_audit=dict(historical_statistical_audit or {}),
            generated_at=generated_at,
        )
    except (TypeError, ValueError, OverflowError, KeyError, IndexError) as exc:
        expected = {}
        blockers.append(f"forward_statistical_audit_recomputation_failed:{type(exc).__name__}")

    for field in FORWARD_STATISTICAL_AUDIT_V2_CONTENT_FIELDS:
        try:
            matches = _canonical_hash(report.get(field)) == _canonical_hash(expected.get(field))
        except (RecursionError, ValueError):
            matches = False
        if not matches:
            blockers.append(f"forward_statistical_audit_semantic_mismatch:{field}")
    if str(report.get("audit_hash") or "") != str(expected.get("audit_hash") or ""):
        blockers.append("forward_statistical_audit_semantic_hash_mismatch")

    decision_window = (
        dict(report.get("decision_window") or {})
        if isinstance(report.get("decision_window"), dict)
        else {}
    )
    supplied_decision_hash = str(decision_window.pop("decision_hash", "") or "")
    try:
        decision_hash_valid = (
            bool(supplied_decision_hash)
            and supplied_decision_hash == _canonical_hash(decision_window)
        )
    except (RecursionError, ValueError):
        decision_hash_valid = False
    if not decision_hash_valid:
        blockers.append("forward_statistical_decision_hash_invalid")
    blockers.extend(
        f"forward_statistical_audit_{item}"
        for item in _execution_authority_blockers(report, path="$.forward_statistical_audit")
    )
    if report.get("profitability_proven") is not False:
        blockers.append("forward_statistical_audit_profitability_claim_invalid")
    if report.get("research_only") is not True:
        blockers.append("forward_statistical_audit_research_only_invalid")
    if report.get("paper_authorized") is not False:
        blockers.append("forward_statistical_audit_paper_authority_invalid")
    if report.get("live_order_allowed") is not False:
        blockers.append("forward_statistical_audit_live_authority_invalid")

    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "claim_status": str(report.get("status") or "BLOCK"),
        "expected_status": str(expected.get("status") or "BLOCK"),
        "expected_conclusion": str(expected.get("conclusion") or ""),
        "expected_audit_hash": str(expected.get("audit_hash") or ""),
        "expected_decision_hash": str(
            dict(expected.get("decision_window") or {}).get("decision_hash") or ""
        ),
        "recomputed_from_verified_forward_settlements": bool(expected),
        "profitability_proven": False,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
