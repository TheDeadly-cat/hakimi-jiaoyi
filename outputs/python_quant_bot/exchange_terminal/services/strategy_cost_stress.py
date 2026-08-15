from __future__ import annotations

import hashlib
import json
import math
from typing import Any


COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION = 8
STRATEGY_COST_STRESS_CONTRACT_SCHEMA_VERSION = "strategy-cost-stress-contract-v1"
STRATEGY_COST_STRESS_EVIDENCE_SCHEMA_VERSION = "strategy-cost-stress-evidence-v1"
STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V3 = (
    "strategy-research-selection-cell-evidence-v3"
)
STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION = (
    "strategy-research-test-cell-evidence-v1"
)

SELECTION_COST_STRESS_STAGE = "DEVELOPMENT_SELECTION"
FROZEN_TEST_COST_STRESS_STAGE = "FROZEN_TEST_ONCE"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _nonnegative_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _fee(value: Any) -> float:
    number = _finite_number(value)
    if number is None or not 0 <= number <= 0.10:
        raise ValueError("strategy_cost_stress_risk_fee_invalid")
    return round(number, 8)


def _slippage(value: Any) -> float:
    number = _finite_number(value)
    if number is None or not 0 <= number <= 10_000:
        raise ValueError("strategy_cost_stress_risk_slippage_invalid")
    return round(number, 4)


def normalize_strategy_cost_risk(risk: dict[str, Any] | Any) -> dict[str, Any]:
    """Match the transaction-cost precision emitted by the backtest report."""

    if not isinstance(risk, dict):
        raise ValueError("strategy_cost_stress_risk_type_invalid")
    return {
        **risk,
        "fee_rate": _fee(risk.get("fee_rate")),
        "slippage_bps": _slippage(risk.get("slippage_bps")),
    }


def build_strategy_cost_stress_contract(risk: dict[str, Any] | Any) -> dict[str, Any]:
    """Freeze the exact configured/stress/severe transaction-cost recipe."""

    normalized_risk = normalize_strategy_cost_risk(risk)
    configured_fee = normalized_risk["fee_rate"]
    configured_slippage = normalized_risk["slippage_bps"]
    content = {
        "schema_version": STRATEGY_COST_STRESS_CONTRACT_SCHEMA_VERSION,
        "configured": {
            "name": "configured",
            "fee_rate": configured_fee,
            "slippage_bps": configured_slippage,
        },
        "selection_scenarios": [
            {
                "name": "stress",
                "fee_rate": _fee(max(configured_fee * 1.6, 0.0008)),
                "slippage_bps": _slippage(max(configured_slippage * 2.5, 5.0)),
            },
            {
                "name": "severe",
                "fee_rate": _fee(max(configured_fee * 2.4, 0.0012)),
                "slippage_bps": _slippage(max(configured_slippage * 5.0, 10.0)),
            },
        ],
        "frozen_test_scenarios": [
            {
                "name": "severe",
                "fee_rate": _fee(max(configured_fee * 2.4, 0.0012)),
                "slippage_bps": _slippage(max(configured_slippage * 5.0, 10.0)),
            },
        ],
        "selection_decision_policy": (
            "POSITIVE_STRESSED_RETURN_WITH_DEGRADATION_AND_DRAWDOWN_V1"
        ),
        "frozen_test_decision_policy": "SEVERE_RETURN_MUST_REMAIN_POSITIVE_V1",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "contract_hash": _canonical_hash(content)}


def project_cost_stress_observation(
    name: str,
    report: dict[str, Any] | Any,
) -> dict[str, Any]:
    payload = report if isinstance(report, dict) else {}
    return {
        "name": str(name or ""),
        "ok": payload.get("ok") is True,
        "fee_rate": payload.get("fee_rate"),
        "slippage_bps": payload.get("slippage_bps"),
        "total_return_pct": payload.get("total_return_pct"),
        "max_drawdown_pct": payload.get("max_drawdown_pct"),
        "trade_count": payload.get("trade_count"),
    }


def _expected_scenarios(contract: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    if stage == SELECTION_COST_STRESS_STAGE:
        raw = contract.get("selection_scenarios")
    elif stage == FROZEN_TEST_COST_STRESS_STAGE:
        raw = contract.get("frozen_test_scenarios")
    else:
        raise ValueError("strategy_cost_stress_stage_invalid")
    return [dict(item) for item in raw or [] if isinstance(item, dict)]


def build_strategy_cost_stress_evidence(
    *,
    stage: str,
    risk: dict[str, Any],
    baseline: dict[str, Any] | Any,
    scenarios: list[dict[str, Any]] | Any,
) -> dict[str, Any]:
    """Build self-contained evidence while separating integrity from outcome."""

    contract = build_strategy_cost_stress_contract(risk)
    expected_scenarios = _expected_scenarios(contract, stage)
    baseline_row = dict(baseline) if isinstance(baseline, dict) else {}
    scenario_rows = [dict(item) for item in scenarios] if isinstance(scenarios, list) and all(
        isinstance(item, dict) for item in scenarios
    ) else []

    integrity_blockers: list[str] = []
    configured = contract["configured"]
    if baseline_row.get("name") != "configured":
        integrity_blockers.append("cost_stress_baseline_name_invalid")
    for field in ("fee_rate", "slippage_bps"):
        actual = _finite_number(baseline_row.get(field))
        if actual is None or actual != float(configured[field]):
            integrity_blockers.append(f"cost_stress_baseline_config_mismatch:{field}")
    baseline_return = _finite_number(baseline_row.get("total_return_pct"))
    baseline_drawdown = _finite_number(baseline_row.get("max_drawdown_pct"))
    baseline_trades = _nonnegative_integer(baseline_row.get("trade_count"))
    if (
        baseline_row.get("ok") is not True
        or baseline_return is None
        or baseline_drawdown is None
        or baseline_drawdown < 0
        or baseline_trades is None
    ):
        integrity_blockers.append("cost_stress_baseline_metrics_invalid")

    expected_names = [str(item.get("name") or "") for item in expected_scenarios]
    actual_names = [str(item.get("name") or "") for item in scenario_rows]
    if actual_names != expected_names or len(actual_names) != len(set(actual_names)):
        integrity_blockers.append("cost_stress_scenario_identity_invalid")

    expected_by_name = {
        str(item.get("name") or ""): item for item in expected_scenarios
    }
    valid_scenarios: list[dict[str, Any]] = []
    for item in scenario_rows:
        name = str(item.get("name") or "")
        expected = expected_by_name.get(name)
        if expected is None:
            continue
        for field in ("fee_rate", "slippage_bps"):
            actual = _finite_number(item.get(field))
            if actual is None or actual != float(expected[field]):
                integrity_blockers.append(
                    f"cost_stress_scenario_config_mismatch:{name}:{field}"
                )
        scenario_return = _finite_number(item.get("total_return_pct"))
        scenario_drawdown = _finite_number(item.get("max_drawdown_pct"))
        scenario_trades = _nonnegative_integer(item.get("trade_count"))
        if (
            item.get("ok") is not True
            or scenario_return is None
            or scenario_drawdown is None
            or scenario_drawdown < 0
            or scenario_trades is None
        ):
            integrity_blockers.append(f"cost_stress_scenario_metrics_invalid:{name}")
            continue
        valid_scenarios.append(item)

    complete = (
        not integrity_blockers
        and len(valid_scenarios) == len(expected_scenarios)
        and bool(valid_scenarios)
    )
    worst_return = min(
        (_finite_number(item.get("total_return_pct")) for item in valid_scenarios),
        default=None,
    ) if complete else None
    worst_drawdown = max(
        (_finite_number(item.get("max_drawdown_pct")) for item in valid_scenarios),
        default=None,
    ) if complete else None
    stressed_trade_count = sum(
        int(item["trade_count"]) for item in valid_scenarios
    ) if complete else None
    degradation = (
        baseline_return - worst_return
        if baseline_return is not None and worst_return is not None
        else None
    )
    allowed_degradation = (
        max(5.0, abs(baseline_return) * 0.75)
        if baseline_return is not None
        else None
    )

    outcome_blockers: list[str] = []
    if complete and worst_return is not None and worst_return <= 0:
        outcome_blockers.append("cost_stress_break_even_lost")
    if stage == SELECTION_COST_STRESS_STAGE and complete:
        if (
            degradation is not None
            and allowed_degradation is not None
            and degradation > allowed_degradation
        ):
            outcome_blockers.append("cost_stress_return_degradation_exceeded")
        if worst_drawdown is not None and worst_drawdown >= 30:
            outcome_blockers.append("cost_stress_drawdown_limit_exceeded")

    all_blockers = list(dict.fromkeys([*integrity_blockers, *outcome_blockers]))
    content = {
        "schema_version": STRATEGY_COST_STRESS_EVIDENCE_SCHEMA_VERSION,
        "stage": stage,
        "verification_status": "PASS" if not integrity_blockers else "BLOCK",
        "status": "PASS" if complete and not outcome_blockers else "BLOCK",
        "decision_policy": (
            contract["selection_decision_policy"]
            if stage == SELECTION_COST_STRESS_STAGE
            else contract["frozen_test_decision_policy"]
        ),
        "contract": contract,
        "baseline": baseline_row,
        "scenarios": scenario_rows,
        "baseline_return_pct": round(baseline_return, 2) if baseline_return is not None else None,
        "worst_return_pct": round(worst_return, 2) if worst_return is not None else None,
        "break_even_preserved": worst_return > 0 if worst_return is not None else None,
        "minimum_stressed_return_pct": 0.0,
        "return_degradation_pct": round(degradation, 2) if degradation is not None else None,
        "allowed_degradation_pct": (
            round(allowed_degradation, 2) if allowed_degradation is not None else None
        ),
        "worst_drawdown_pct": round(worst_drawdown, 2) if worst_drawdown is not None else None,
        "stressed_trade_count": stressed_trade_count,
        "integrity_blockers": list(dict.fromkeys(integrity_blockers)),
        "outcome_blockers": list(dict.fromkeys(outcome_blockers)),
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
    "COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION",
    "FROZEN_TEST_COST_STRESS_STAGE",
    "SELECTION_COST_STRESS_STAGE",
    "STRATEGY_COST_STRESS_CONTRACT_SCHEMA_VERSION",
    "STRATEGY_COST_STRESS_EVIDENCE_SCHEMA_VERSION",
    "STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V3",
    "STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION",
    "build_strategy_cost_stress_contract",
    "build_strategy_cost_stress_evidence",
    "normalize_strategy_cost_risk",
    "project_cost_stress_observation",
]
