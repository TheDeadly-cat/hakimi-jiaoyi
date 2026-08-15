from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any

from .execution_authority import authority_violations


BACKTEST_RETURN_QUALITY_SCHEMA_VERSION = "backtest-return-quality-v1"
BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION = "backtest-return-quality-v2"
BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION = "backtest-return-quality-v3"
CURRENT_BACKTEST_RETURN_QUALITY_SCHEMA_VERSION = BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION
SUPPORTED_BACKTEST_RETURN_QUALITY_SCHEMA_VERSIONS = {
    BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
    BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
    BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION,
}
PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_SCHEMA_VERSION = (
    "portfolio-return-quality-source-identity-v1"
)
PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_V2_SCHEMA_VERSION = (
    "portfolio-return-quality-source-identity-v2"
)
PORTFOLIO_RESEARCH_SOURCE_ARTIFACT_FAMILY = "PORTFOLIO_RESEARCH_PROTOCOL_V1"
def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _count(value: Any) -> int | None:
    number = _number(value)
    if number is None or number < 0 or not number.is_integer():
        return None
    return int(number)


def _rounded(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None else None


def _strings(value: Any) -> list[str]:
    return [str(item) for item in _items(value) if isinstance(item, str) and item]


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _authority_violations(value: Any, path: str = "source") -> list[str]:
    return [
        f"authority_not_false:{violation}"
        for violation in authority_violations(value, path=path)
    ]


def _evidence_stage(research: dict[str, Any]) -> str:
    if research.get("fresh_holdout_required") is True:
        return "DEVELOPMENT_HISTORICAL"
    mechanism = str(research.get("mechanism_status") or "").upper()
    if "FRESH_HOLDOUT" in mechanism or "DEVELOPMENT" in mechanism:
        return "DEVELOPMENT_HISTORICAL"
    return "HISTORICAL_RESEARCH"


def _stage_projection(
    name: str,
    research: dict[str, Any],
    statistical: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    strategy = _object(research.get(name))
    benchmark = _object(research.get(f"{name}_benchmark"))
    comparison = _object(research.get(f"{name}_comparison"))
    statistical_stage = _object(_object(statistical.get("stages")).get(name))
    observed = _object(statistical_stage.get("observed"))

    strategy_return = _number(strategy.get("total_return_pct"))
    benchmark_return = _number(benchmark.get("total_return_pct"))
    computed_excess = (
        strategy_return - benchmark_return
        if strategy_return is not None and benchmark_return is not None
        else None
    )
    reported_excess = _number(comparison.get("excess_return_pct"))
    point_excess = computed_excess
    strategy_drawdown = _number(strategy.get("max_drawdown_pct"))
    benchmark_drawdown = _number(benchmark.get("max_drawdown_pct"))
    evaluated_rows = _count(_object(strategy.get("evaluation_window")).get("evaluated_rows"))
    order_events = _count(strategy.get("order_event_count"))
    decision_events = _count(strategy.get("decision_event_count"))
    observation_count = _count(statistical_stage.get("observation_count"))

    gaps: list[str] = []
    for field, value in (
        ("strategy_return", strategy_return),
        ("benchmark_return", benchmark_return),
        ("benchmark_excess", point_excess),
        ("max_drawdown", strategy_drawdown),
        ("evaluated_rows", evaluated_rows),
        ("statistical_observation_count", observation_count),
    ):
        if value is None:
            gaps.append(f"{name}_{field}_unknown")

    failures: list[str] = []
    if strategy_return is not None and strategy_return <= 0:
        failures.append(f"{name}_return_not_positive")
    if point_excess is not None and point_excess <= 0:
        failures.append(f"{name}_benchmark_excess_not_positive")
    statistical_status = str(statistical_stage.get("status") or "UNKNOWN").upper()
    if statistical_status == "BLOCK":
        failures.append(f"{name}_statistical_claim_block")
    if (
        computed_excess is not None
        and reported_excess is not None
        and abs(computed_excess - reported_excess) > 0.00011
    ):
        failures.append(f"{name}_reported_excess_mismatch")

    projection = {
        "stage": name.upper(),
        "evidence_status": "AVAILABLE" if not gaps else "PARTIAL",
        "benchmark_excess_status": "AVAILABLE" if point_excess is not None else "UNKNOWN",
        "benchmark_excess_basis": (
            "RECOMPUTED_FROM_STRATEGY_AND_BENCHMARK_RETURNS"
            if point_excess is not None
            else "REPORTED_ONLY_NOT_USED"
            if reported_excess is not None
            else "NOT_PROVIDED"
        ),
        "strategy_return_pct": _rounded(strategy_return),
        "benchmark_return_pct": _rounded(benchmark_return),
        "benchmark_excess_return_pct": _rounded(point_excess),
        "reported_benchmark_excess_return_pct": _rounded(reported_excess),
        "strategy_max_drawdown_pct": _rounded(strategy_drawdown),
        "benchmark_max_drawdown_pct": _rounded(benchmark_drawdown),
        "drawdown_improvement_pct": _rounded(
            benchmark_drawdown - strategy_drawdown
            if benchmark_drawdown is not None and strategy_drawdown is not None
            else None
        ),
        "sample": {
            "evaluated_rows": evaluated_rows,
            "order_event_count": order_events,
            "decision_event_count": decision_events,
            "paired_return_observation_count": observation_count,
        },
        "statistical_claim": {
            "status": statistical_status,
            "observed_strategy_compound_return_pct": _rounded(
                _number(observed.get("strategy_compound_return_pct"))
            ),
            "observed_benchmark_compound_return_pct": _rounded(
                _number(observed.get("benchmark_compound_return_pct"))
            ),
            "observed_compound_excess_return_pct": _rounded(
                _number(observed.get("compound_excess_return_pct"))
            ),
            "blockers": _strings(statistical_stage.get("blockers")),
        },
        "quality_flags": {
            "strategy_return_positive": strategy_return > 0 if strategy_return is not None else None,
            "benchmark_excess_positive": point_excess > 0 if point_excess is not None else None,
        },
    }
    return projection, gaps, failures


def _cost_projection(
    research: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    spec = _object(research.get("spec"))
    test = _object(research.get("test"))
    test_run_spec = _object(test.get("run_spec"))
    baseline_return = _number(test.get("total_return_pct"))
    fee_rate = _number(spec.get("fee_rate"))
    slippage_bps = _number(spec.get("slippage_bps"))
    run_fee_rate = _number(test_run_spec.get("fee_rate"))
    run_slippage_bps = _number(test_run_spec.get("slippage_bps"))
    configured_cost_binding_known = all(
        value is not None
        for value in (fee_rate, slippage_bps, run_fee_rate, run_slippage_bps)
    )
    configured_cost_binding_pass = bool(
        configured_cost_binding_known
        and abs(float(fee_rate) - float(run_fee_rate)) <= 1e-12
        and abs(float(slippage_bps) - float(run_slippage_bps)) <= 1e-9
    )
    raw_contract = _items(spec.get("cost_stress_contract"))
    contract_by_label: dict[str, dict[str, float | None]] = {}
    contract_duplicates: list[str] = []
    contract_invalid: list[str] = []
    for index, raw in enumerate(raw_contract):
        contract = _object(raw)
        label = str(contract.get("label") or f"SCENARIO_{index + 1}").upper()
        if label in contract_by_label:
            contract_duplicates.append(label)
        contract_fee = _number(contract.get("fee_rate"))
        contract_slippage = _number(contract.get("slippage_bps"))
        if contract_fee is None or contract_slippage is None:
            contract_invalid.append(label)
        contract_by_label[label] = {
            "fee_rate": contract_fee,
            "slippage_bps": contract_slippage,
        }
    raw_scenarios = _items(research.get("cost_stress"))
    scenarios: list[dict[str, Any]] = []
    failures: list[str] = []
    seen_scenario_labels: set[str] = set()

    if contract_duplicates:
        failures.extend(
            f"cost_stress_contract_duplicate:{label}"
            for label in _unique(contract_duplicates)
        )
    if contract_invalid:
        failures.extend(
            f"cost_stress_contract_invalid:{label}"
            for label in _unique(contract_invalid)
        )

    for index, raw in enumerate(raw_scenarios):
        scenario = _object(raw)
        label = str(scenario.get("label") or f"SCENARIO_{index + 1}").upper()
        duplicate_scenario = label in seen_scenario_labels
        seen_scenario_labels.add(label)
        scenario_return = _number(scenario.get("total_return_pct"))
        scenario_drawdown = _number(scenario.get("max_drawdown_pct"))
        scenario_fee = _number(scenario.get("fee_rate"))
        scenario_slippage = _number(scenario.get("slippage_bps"))
        scenario_ok = scenario.get("ok") is True
        contract = contract_by_label.get(label)
        contract_known = contract is not None
        contract_match = bool(
            contract_known
            and contract.get("fee_rate") is not None
            and contract.get("slippage_bps") is not None
            and scenario_fee is not None
            and scenario_slippage is not None
            and abs(float(contract["fee_rate"]) - float(scenario_fee)) <= 1e-12
            and abs(float(contract["slippage_bps"]) - float(scenario_slippage)) <= 1e-9
        )
        scenario_available = bool(
            not duplicate_scenario
            and scenario_ok
            and scenario_return is not None
            and contract_match
        )
        if duplicate_scenario:
            failures.append(f"cost_stress_scenario_duplicate:{label}")
        if raw_contract and not contract_match:
            failures.append(f"cost_stress_contract_mismatch:{label}")
        if not scenario_ok or scenario_return is None:
            failures.append(f"cost_stress_invalid:{label}")
        elif scenario_available and scenario_return <= 0:
            failures.append(f"cost_stress_return_not_positive:{label}")
        scenarios.append(
            {
                "label": label,
                "status": (
                    "AVAILABLE"
                    if scenario_available
                    else "BLOCK"
                    if duplicate_scenario or (raw_contract and not contract_match) or not scenario_ok
                    else "UNKNOWN"
                ),
                "contract_match": contract_match if raw_contract else None,
                "fee_rate": _rounded(scenario_fee, 8),
                "slippage_bps": _rounded(scenario_slippage, 4),
                "contract_fee_rate": _rounded(
                    _number(contract.get("fee_rate")) if contract else None,
                    8,
                ),
                "contract_slippage_bps": _rounded(
                    _number(contract.get("slippage_bps")) if contract else None,
                    4,
                ),
                "declared_return_pct": _rounded(scenario_return),
                "declared_max_drawdown_pct": _rounded(scenario_drawdown),
                "return_pct": _rounded(scenario_return) if scenario_available else None,
                "max_drawdown_pct": _rounded(scenario_drawdown) if scenario_available else None,
            }
        )

    usable_returns = [
        value
        for value in (_number(item.get("return_pct")) for item in scenarios)
        if value is not None
    ]
    usable_drawdowns = [
        value
        for value in (_number(item.get("max_drawdown_pct")) for item in scenarios)
        if value is not None
    ]
    gaps: list[str] = []
    if baseline_return is None:
        gaps.append("cost_after_baseline_return_unknown")
    if fee_rate is None:
        gaps.append("cost_model_fee_rate_unknown")
    if slippage_bps is None:
        gaps.append("cost_model_slippage_unknown")
    if not configured_cost_binding_known:
        gaps.append("configured_cost_test_run_binding_unknown")
    elif not configured_cost_binding_pass:
        failures.append("configured_cost_test_run_binding_mismatch")
    if not scenarios:
        gaps.append("cost_stress_scenarios_unknown")
    if not raw_contract:
        gaps.append("cost_stress_contract_unknown")
    else:
        for label in contract_by_label:
            if label not in seen_scenario_labels:
                gaps.append(f"cost_stress_scenario_missing:{label}")

    complete_stress_contract = bool(
        raw_contract
        and not contract_duplicates
        and not contract_invalid
        and len(contract_by_label) == len(scenarios)
        and set(contract_by_label) == seen_scenario_labels
        and all(item.get("status") == "AVAILABLE" for item in scenarios)
    )

    projection = {
        "status": "BLOCK" if failures else "PARTIAL" if gaps else "AVAILABLE",
        "baseline_model": {
            "status": (
                "AVAILABLE"
                if baseline_return is not None and configured_cost_binding_pass
                else "BLOCK"
                if configured_cost_binding_known and not configured_cost_binding_pass
                else "UNKNOWN"
            ),
            "fee_rate": _rounded(fee_rate, 8),
            "slippage_bps": _rounded(slippage_bps, 4),
            "test_run_fee_rate": _rounded(run_fee_rate, 8),
            "test_run_slippage_bps": _rounded(run_slippage_bps, 4),
            "cost_binding_basis": (
                "TEST_RUN_SPEC_MATCHES_FROZEN_RESEARCH_SPEC"
                if configured_cost_binding_pass
                else "TEST_RUN_SPEC_MISMATCH"
                if configured_cost_binding_known
                else "TEST_RUN_SPEC_NOT_VERIFIABLE"
            ),
            "configured_costs_declared_in_test_run": (
                configured_cost_binding_pass if configured_cost_binding_known else None
            ),
            "declared_test_return_pct": _rounded(baseline_return),
            "test_return_after_configured_costs_pct": (
                _rounded(baseline_return) if configured_cost_binding_pass else None
            ),
        },
        "stress_scenarios": scenarios,
        "stress_contract": {
            "status": (
                "AVAILABLE"
                if raw_contract and not contract_duplicates and not contract_invalid
                else "BLOCK"
                if contract_duplicates or contract_invalid
                else "UNKNOWN"
            ),
            "expected_labels": list(contract_by_label),
            "reported_labels": [str(item.get("label") or "") for item in scenarios],
        },
        "worst_stress_return_pct": _rounded(
            min(usable_returns) if complete_stress_contract and usable_returns else None
        ),
        "worst_stress_max_drawdown_pct": _rounded(
            max(usable_drawdowns) if complete_stress_contract and usable_drawdowns else None
        ),
        "all_stress_returns_positive": (
            all(value > 0 for value in usable_returns)
            if complete_stress_contract and usable_returns
            else None
        ),
    }
    return projection, gaps, failures


def _source_integrity_blocked_projection(
    result: dict[str, Any],
    source_blockers: list[str],
) -> dict[str, Any]:
    """Remove every descriptive numeric claim when its source cannot be verified."""

    blocked_stage = lambda name: {
        "stage": name.upper(),
        "evidence_status": "BLOCK",
        "benchmark_excess_status": "UNKNOWN",
        "benchmark_excess_basis": "SOURCE_INTEGRITY_BLOCKED",
        "strategy_return_pct": None,
        "benchmark_return_pct": None,
        "benchmark_excess_return_pct": None,
        "reported_benchmark_excess_return_pct": None,
        "strategy_max_drawdown_pct": None,
        "benchmark_max_drawdown_pct": None,
        "drawdown_improvement_pct": None,
        "sample": {
            "evaluated_rows": None,
            "order_event_count": None,
            "decision_event_count": None,
            "paired_return_observation_count": None,
        },
        "statistical_claim": {
            "status": "UNKNOWN",
            "observed_strategy_compound_return_pct": None,
            "observed_benchmark_compound_return_pct": None,
            "observed_compound_excess_return_pct": None,
            "blockers": [],
        },
        "quality_flags": {
            "strategy_return_positive": None,
            "benchmark_excess_positive": None,
        },
    }
    result["status"] = "BLOCK"
    result["interpretation"] = "SOURCE_INTEGRITY_BLOCKED_NO_NUMERIC_CLAIMS"
    result["summary"] = {
        "strategy_return_pct": None,
        "benchmark_return_pct": None,
        "benchmark_excess_return_pct": None,
        "benchmark_excess_status": "UNKNOWN",
        "cost_after_return_pct": None,
        "cost_after_status": "UNKNOWN",
        "worst_stress_return_pct": None,
        "max_drawdown_pct": None,
        "sample_size": None,
        "sample_unit": "UNKNOWN",
        "evidence_stage": "UNKNOWN",
    }
    result["stages"] = {
        "validation": blocked_stage("validation"),
        "test": blocked_stage("test"),
    }
    result["cost_after"] = {
        "status": "BLOCK",
        "baseline_model": {
            "status": "UNKNOWN",
            "fee_rate": None,
            "slippage_bps": None,
            "test_run_fee_rate": None,
            "test_run_slippage_bps": None,
            "cost_binding_basis": "SOURCE_INTEGRITY_BLOCKED",
            "configured_costs_declared_in_test_run": None,
            "declared_test_return_pct": None,
            "test_return_after_configured_costs_pct": None,
        },
        "stress_scenarios": [],
        "stress_contract": {
            "status": "UNKNOWN",
            "expected_labels": [],
            "reported_labels": [],
        },
        "worst_stress_return_pct": None,
        "worst_stress_max_drawdown_pct": None,
        "all_stress_returns_positive": None,
    }
    result["statistical_claim_status"] = "UNKNOWN"
    result["failure_conditions"] = {
        "source_integrity": _unique(source_blockers),
        "observed": [],
        "evidence_gaps": [],
        "promotion_gaps": [],
    }
    result["source_integrity_status"] = "BLOCK"
    result["numeric_claims_available"] = False
    return result


def build_backtest_return_quality_projection(
    research_report: dict[str, Any] | None,
    statistical_audit: dict[str, Any] | None = None,
    *,
    schema_version: str = BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
    source_identity: dict[str, Any] | None = None,
    source_evidence_hash: str = "",
    source_manifest_hash: str = "",
    detached_source_binding_hash: str = "",
    verified_source_integrity_status: str = "PASS",
    verified_source_integrity_blockers: list[str] | None = None,
) -> dict[str, Any]:
    """Project already-loaded historical reports into a fail-closed return-quality view."""

    if schema_version not in SUPPORTED_BACKTEST_RETURN_QUALITY_SCHEMA_VERSIONS:
        raise ValueError(f"unsupported backtest return-quality schema: {schema_version}")

    research = _object(research_report)
    statistical = _object(statistical_audit)
    source_integrity: list[str] = []
    if research.get("research_only") is not True:
        source_integrity.append("research_source_not_research_only")
    for field in ("paper_authorized", "live_order_allowed"):
        if research.get(field) is not False:
            source_integrity.append(f"research_source_{field}_not_false")
    if statistical and statistical.get("research_only") is not True:
        source_integrity.append("statistical_source_not_research_only")
    if statistical:
        for field in ("paper_authorized", "live_order_allowed"):
            if statistical.get(field) is not False:
                source_integrity.append(f"statistical_source_{field}_not_false")
    source_integrity.extend(_authority_violations(research, "research"))
    source_integrity.extend(_authority_violations(statistical, "statistical"))

    validation, validation_gaps, validation_failures = _stage_projection(
        "validation", research, statistical
    )
    test, test_gaps, test_failures = _stage_projection("test", research, statistical)
    costs, cost_gaps, cost_failures = _cost_projection(research)
    evidence_gaps = [*validation_gaps, *test_gaps, *cost_gaps]

    statistical_status = str(statistical.get("status") or "UNKNOWN").upper()
    observed_failures = [*validation_failures, *test_failures, *cost_failures]
    if statistical_status == "BLOCK":
        observed_failures.append("historical_statistical_claim_block")
    elif statistical_status == "UNKNOWN":
        evidence_gaps.append("historical_statistical_claim_unknown")
    for name, passed in _object(research.get("development_checks")).items():
        if passed is False:
            observed_failures.append(f"development_check_failed:{name}")

    promotion_gaps: list[str] = []
    if research.get("fresh_holdout_required") is True:
        promotion_gaps.append("fresh_untouched_holdout_required")
    if research.get("forward_observation_required") is True:
        promotion_gaps.append("natural_forward_observation_required")

    evidence_gaps = _unique(evidence_gaps)
    source_integrity = _unique(source_integrity)
    observed_failures = _unique(observed_failures)
    promotion_gaps = _unique(promotion_gaps)
    status = (
        "BLOCK"
        if source_integrity or observed_failures
        else "PARTIAL"
        if evidence_gaps
        else "AVAILABLE"
    )

    test_sample = _object(test.get("sample"))
    paired_observations = _count(test_sample.get("paired_return_observation_count"))
    evaluated_rows = _count(test_sample.get("evaluated_rows"))
    sample_size = paired_observations if paired_observations is not None else evaluated_rows
    sample_unit = (
        "PAIRED_RETURN_OBSERVATIONS"
        if paired_observations is not None
        else "EVALUATED_ROWS"
        if evaluated_rows is not None
        else "UNKNOWN"
    )
    summary = {
        "strategy_return_pct": test.get("strategy_return_pct"),
        "benchmark_return_pct": test.get("benchmark_return_pct"),
        "benchmark_excess_return_pct": test.get("benchmark_excess_return_pct"),
        "benchmark_excess_status": test.get("benchmark_excess_status"),
        "cost_after_return_pct": _object(costs.get("baseline_model")).get(
            "test_return_after_configured_costs_pct"
        ),
        "cost_after_status": _object(costs.get("baseline_model")).get("status"),
        "worst_stress_return_pct": costs.get("worst_stress_return_pct"),
        "max_drawdown_pct": test.get("strategy_max_drawdown_pct"),
        "sample_size": sample_size,
        "sample_unit": sample_unit,
        "evidence_stage": _evidence_stage(research),
    }
    result = {
        "schema_version": BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
        "status": status,
        "interpretation": "DESCRIPTIVE_HISTORICAL_EVIDENCE_ONLY",
        "summary": summary,
        "stages": {
            "validation": validation,
            "test": test,
        },
        "cost_after": costs,
        "statistical_claim_status": statistical_status,
        "failure_conditions": {
            "source_integrity": source_integrity,
            "observed": observed_failures,
            "evidence_gaps": evidence_gaps,
            "promotion_gaps": promotion_gaps,
        },
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if schema_version == BACKTEST_RETURN_QUALITY_SCHEMA_VERSION:
        return result

    identity = deepcopy(_object(source_identity))
    identity_content = dict(identity)
    declared_identity_hash = str(identity_content.pop("identity_hash", "") or "")
    v2_integrity: list[str] = []
    expected_identity_schema = (
        PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_V2_SCHEMA_VERSION
        if schema_version == BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION
        else PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_SCHEMA_VERSION
    )
    if identity.get("schema_version") != expected_identity_schema:
        v2_integrity.append("return_quality_source_identity_schema_invalid")
    if identity.get("source_artifact_family") != PORTFOLIO_RESEARCH_SOURCE_ARTIFACT_FAMILY:
        v2_integrity.append("return_quality_source_artifact_family_invalid")
    if identity.get("strategy_schema7_preregistration_status") != "NOT_APPLICABLE":
        v2_integrity.append("return_quality_strategy_schema7_scope_invalid")
    required_identity_fields = [
        "candidate_hash",
        "candidate_research_report_hash",
        "candidate_spec_hash",
        "research_batch_run_hash",
        "research_spec_hash",
        "research_generation",
        "research_protocol_hash",
        "research_file_sha256",
        "statistical_audit_schema_version",
        "statistical_audit_hash",
        "statistical_input_binding_hash",
        "experiment_completion_receipt_hash",
        "active_candidate_registry_hash",
    ]
    required_identity_hashes = [
        "candidate_hash",
        "candidate_research_report_hash",
        "candidate_spec_hash",
        "research_batch_run_hash",
        "research_spec_hash",
        "research_protocol_hash",
        "research_file_sha256",
        "statistical_audit_hash",
        "statistical_input_binding_hash",
        "experiment_completion_receipt_hash",
        "active_candidate_registry_hash",
    ]
    if schema_version == BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION:
        required_identity_fields.extend(
            (
                "research_file_byte_length",
                "research_canonical_object_hash",
                "candidate_canonical_object_hash",
                "statistical_canonical_object_hash",
                "backtest_result_digest_collection_hash",
                "detached_source_binding_hash",
            )
        )
        required_identity_hashes.extend(
            (
                "research_canonical_object_hash",
                "candidate_canonical_object_hash",
                "statistical_canonical_object_hash",
                "backtest_result_digest_collection_hash",
                "detached_source_binding_hash",
            )
        )
    else:
        required_identity_fields.extend(
            ("research_source_document_sha256", "backtest_result_evidence_hash")
        )
        required_identity_hashes.extend(
            ("research_source_document_sha256", "backtest_result_evidence_hash")
        )
    for field in required_identity_fields:
        if not str(identity.get(field) or ""):
            v2_integrity.append(f"return_quality_source_identity_missing:{field}")
    for field in required_identity_hashes:
        if str(identity.get(field) or "") and not _is_sha256(identity.get(field)):
            v2_integrity.append(f"return_quality_source_identity_hash_invalid:{field}")
    if not declared_identity_hash or _canonical_hash(identity_content) != declared_identity_hash:
        v2_integrity.append("return_quality_source_identity_hash_invalid")
    if schema_version == BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION:
        if not _is_sha256(source_manifest_hash):
            v2_integrity.append("return_quality_source_manifest_hash_invalid")
        if not _is_sha256(detached_source_binding_hash):
            v2_integrity.append("return_quality_detached_source_binding_hash_invalid")
        if str(identity.get("detached_source_binding_hash") or "") != str(
            detached_source_binding_hash or ""
        ):
            v2_integrity.append("return_quality_detached_source_binding_mismatch")
    elif not _is_sha256(source_evidence_hash):
        v2_integrity.append("return_quality_source_evidence_hash_invalid")
    if identity.get("external_anchor_verified") is not False:
        v2_integrity.append("return_quality_external_anchor_scope_invalid")
    if identity.get("cryptographic_authenticity_proven") is not False:
        v2_integrity.append("return_quality_cryptographic_authenticity_scope_invalid")
    v2_integrity.extend(_authority_violations(identity, "source_identity"))

    declared_source_status = str(verified_source_integrity_status or "").upper()
    verified_blockers = _unique(
        [str(item) for item in verified_source_integrity_blockers or [] if str(item)]
    )
    if declared_source_status != "PASS":
        v2_integrity.extend(
            verified_blockers or ["return_quality_source_evidence_not_semantically_verified"]
        )

    combined_integrity = _unique(
        [
            *result["failure_conditions"]["source_integrity"],
            *v2_integrity,
        ]
    )
    result["schema_version"] = schema_version
    result["source_identity"] = identity
    if schema_version == BACKTEST_RETURN_QUALITY_V3_SCHEMA_VERSION:
        result["source_manifest_hash"] = str(source_manifest_hash or "")
        result["detached_source_binding_hash"] = str(
            detached_source_binding_hash or ""
        )
    else:
        result["source_evidence_hash"] = str(source_evidence_hash or "")
    result["failure_conditions"]["source_integrity"] = combined_integrity
    if combined_integrity:
        return _source_integrity_blocked_projection(result, combined_integrity)
    result["source_integrity_status"] = "PASS"
    result["numeric_claims_available"] = True
    return result
