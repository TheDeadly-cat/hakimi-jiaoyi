from __future__ import annotations

from typing import Any

from .execution_authority import authority_violations
from .strict_canonical_json_hash import (
    strict_canonical_hash,
    strict_json_contract_equal,
)
from .strategy_correlation_cluster_gate import (
    verify_correlation_cluster_preregistration,
)
from .strategy_correlation_cluster_temporal_stability import (
    GATE_SCHEMA_VERSION as SOURCE_TEMPORAL_GATE_SCHEMA_VERSION,
    LOOKBACK_OBSERVATIONS,
    verify_strategy_correlation_cluster_temporal_stability_gate,
)


POLICY_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-policy-v1"
)
POLICY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-policy-v1-verification-v1"
)
AUDIT_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-audit-v1"
)
GATE_SCHEMA_VERSION = "strategy-correlation-cluster-temporal-date-grid-gate-v1"
GATE_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-gate-v1-verification-v1"
)
DATE_GRID_RULE = "ALL_SYMBOL_PRICE_DATE_GRIDS_EXACTLY_EQUAL_BEFORE_WINDOW_SPLIT"
REQUIRED_PRICE_ROWS = LOOKBACK_OBSERVATIONS + 1

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    return {**payload, field: strict_canonical_hash(payload)}


def _authority_invalid(value: Any) -> bool:
    try:
        return bool(authority_violations(value))
    except (MemoryError, RecursionError, TypeError, ValueError):
        return True


def _verification(schema_version: str, blockers: list[str]) -> dict[str, Any]:
    unique = list(dict.fromkeys(blockers))
    return {
        "schema_version": schema_version,
        "status": "BLOCK" if unique else "PASS",
        "blockers": unique,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def build_strategy_correlation_cluster_temporal_date_grid_policy() -> dict[str, Any]:
    payload = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_temporal_gate_schema_version": SOURCE_TEMPORAL_GATE_SCHEMA_VERSION,
        "date_grid_rule": DATE_GRID_RULE,
        "required_price_rows": REQUIRED_PRICE_ROWS,
        "required_return_observations": LOOKBACK_OBSERVATIONS,
        "all_preregistered_symbols_required": True,
        "exact_date_order_required": True,
        "date_intersection_substitution_allowed": False,
        "positional_alignment_without_date_equality_allowed": False,
        "descriptive_only": True,
        "consumer_only": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return _seal(payload, "policy_hash")


def verify_strategy_correlation_cluster_temporal_date_grid_policy(
    document: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    expected = build_strategy_correlation_cluster_temporal_date_grid_policy()
    if type(document) is not dict or not strict_json_contract_equal(
        document,
        expected,
    ):
        blockers.append("temporal_date_grid_policy_contract_invalid")
    if _authority_invalid(document):
        blockers.append("execution_authority_invalid")
    result = _verification(POLICY_VERIFICATION_SCHEMA_VERSION, blockers)
    result["policy_hash"] = expected["policy_hash"] if not blockers else ""
    return result


def build_strategy_correlation_cluster_temporal_date_grid_audit(
    source_uncertainty_audit: Any,
    preregistration: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if _authority_invalid(source_uncertainty_audit) or _authority_invalid(
        preregistration
    ):
        blockers.append("execution_authority_invalid")

    preregistration_verification = verify_correlation_cluster_preregistration(
        preregistration
    )
    if preregistration_verification.get("status") != "PASS":
        blockers.append("correlation_cluster_preregistration_invalid")
        expected_symbols: list[str] = []
    else:
        expected_symbols = list(preregistration["symbols"])

    source = source_uncertainty_audit if type(source_uncertainty_audit) is dict else {}
    matrix_replay = source.get("matrix_replay")
    matrix_replay = matrix_replay if type(matrix_replay) is dict else {}
    completed_input = matrix_replay.get("completed_price_input")
    completed_input = completed_input if type(completed_input) is dict else {}
    datasets = completed_input.get("datasets")

    observed_symbols: list[str] = []
    grids: dict[str, tuple[str, ...]] = {}
    grid_results: list[dict[str, Any]] = []
    if type(datasets) is not list:
        blockers.append("completed_price_datasets_invalid")
        datasets = []
    for dataset in datasets:
        if type(dataset) is not dict:
            blockers.append("completed_price_dataset_invalid")
            continue
        symbol = dataset.get("symbol")
        rows = dataset.get("price_rows")
        if type(symbol) is not str or not symbol or type(rows) is not list:
            blockers.append("completed_price_dataset_invalid")
            continue
        if symbol in grids:
            blockers.append("completed_price_dataset_symbol_duplicate")
            continue
        observed_symbols.append(symbol)
        dates: list[str] = []
        dates_valid = len(rows) == REQUIRED_PRICE_ROWS
        for row in rows:
            if type(row) is not dict or type(row.get("date")) is not str:
                dates_valid = False
                continue
            dates.append(row["date"])
        if len(dates) != REQUIRED_PRICE_ROWS or len(set(dates)) != len(dates):
            dates_valid = False
        if not dates_valid:
            blockers.append(f"price_date_grid_invalid:{symbol}")
            grid_hash = ""
        else:
            grid_hash = strict_canonical_hash(dates)
            grids[symbol] = tuple(dates)
        grid_results.append(
            {
                "symbol": symbol,
                "price_date_count": len(dates),
                "return_observation_count": max(0, len(dates) - 1),
                "price_date_grid_hash": grid_hash,
                "status": "PASS" if dates_valid else "BLOCK",
            }
        )

    coverage_exact = (
        observed_symbols == expected_symbols
        and len(set(observed_symbols)) == len(observed_symbols)
    )
    if not coverage_exact:
        blockers.append("price_date_grid_symbol_coverage_mismatch")
    exact_grid = (
        coverage_exact
        and len(grids) == len(expected_symbols)
        and bool(grids)
        and len(set(grids.values())) == 1
    )
    if not exact_grid:
        blockers.append("price_date_grids_not_exactly_equal")

    policy = build_strategy_correlation_cluster_temporal_date_grid_policy()
    common_grid = next(iter(grids.values()), ()) if exact_grid else ()
    payload = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "status": "BLOCK" if blockers else "PASS",
        "date_grid_rule": DATE_GRID_RULE,
        "policy": policy,
        "policy_hash": policy["policy_hash"],
        "source_uncertainty_audit_hash": source.get("audit_hash", ""),
        "preregistration_hash": (
            preregistration.get("preregistration_hash", "")
            if type(preregistration) is dict
            else ""
        ),
        "completed_price_input_hash": completed_input.get("input_hash", ""),
        "expected_symbols": expected_symbols,
        "grid_results": sorted(grid_results, key=lambda item: item["symbol"]),
        "exact_symbol_coverage_proven": coverage_exact,
        "exact_common_price_date_grid_proven": exact_grid,
        "common_price_date_count": len(common_grid),
        "common_return_observation_count": max(0, len(common_grid) - 1),
        "common_price_date_grid_hash": (
            strict_canonical_hash(list(common_grid)) if common_grid else ""
        ),
        "blockers": list(dict.fromkeys(blockers)),
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "consumer_only": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return _seal(payload, "audit_hash")


def evaluate_strategy_correlation_cluster_temporal_date_grid_gate(
    source_uncertainty_audit: Any,
    source_temporal_stability_gate: Any,
    *,
    full_window_stability_gate: Any,
    complete_link_gate: Any,
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    source_verification = (
        verify_strategy_correlation_cluster_temporal_stability_gate(
            source_temporal_stability_gate,
            source_uncertainty_audit=source_uncertainty_audit,
            full_window_stability_gate=full_window_stability_gate,
            complete_link_gate=complete_link_gate,
            preregistration=preregistration,
            correlation_matrix=correlation_matrix,
            selection_cells=selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    )
    audit = build_strategy_correlation_cluster_temporal_date_grid_audit(
        source_uncertainty_audit,
        preregistration,
    )
    blockers: list[str] = []
    if source_verification.get("status") != "PASS":
        blockers.append("source_temporal_stability_gate_not_verified")
    source_decision_status = source_verification.get("decision_status", "BLOCK")
    if source_decision_status != "PASS":
        blockers.append("source_temporal_stability_gate_blocked")
    if audit["status"] != "PASS":
        blockers.append("exact_common_price_date_grid_not_proven")

    if source_verification.get("status") != "PASS":
        first_blocking_tier = "SOURCE_TEMPORAL_CONTRACT"
    elif source_decision_status != "PASS":
        first_blocking_tier = "SOURCE_TEMPORAL_DECISION"
    elif audit["status"] != "PASS":
        first_blocking_tier = "DATE_GRID_BINDING"
    else:
        first_blocking_tier = None
    policy = build_strategy_correlation_cluster_temporal_date_grid_policy()
    source_gate = (
        source_temporal_stability_gate
        if type(source_temporal_stability_gate) is dict
        else {}
    )
    payload = {
        "schema_version": GATE_SCHEMA_VERSION,
        "status": "BLOCK" if blockers else "PASS",
        "strategy_id": strategy_id,
        "variant_id": variant_id,
        "lane": lane,
        "first_blocking_tier": first_blocking_tier,
        "source_temporal_gate_schema_version": SOURCE_TEMPORAL_GATE_SCHEMA_VERSION,
        "source_temporal_gate_hash": source_gate.get("gate_hash", ""),
        "source_temporal_contract_status": source_verification.get(
            "status", "BLOCK"
        ),
        "source_temporal_decision_status": source_decision_status,
        "policy": policy,
        "policy_hash": policy["policy_hash"],
        "date_grid_audit": audit,
        "date_grid_audit_hash": audit["audit_hash"],
        "blockers": blockers,
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "consumer_only": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return _seal(payload, "gate_hash")


def verify_strategy_correlation_cluster_temporal_date_grid_gate(
    document: Any,
    *,
    source_uncertainty_audit: Any,
    source_temporal_stability_gate: Any,
    full_window_stability_gate: Any,
    complete_link_gate: Any,
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        expected = evaluate_strategy_correlation_cluster_temporal_date_grid_gate(
            source_uncertainty_audit,
            source_temporal_stability_gate,
            full_window_stability_gate=full_window_stability_gate,
            complete_link_gate=complete_link_gate,
            preregistration=preregistration,
            correlation_matrix=correlation_matrix,
            selection_cells=selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except (
        ArithmeticError,
        KeyError,
        MemoryError,
        RecursionError,
        TypeError,
        ValueError,
    ):
        expected = None
        blockers.append("temporal_date_grid_gate_source_invalid")
    if expected is not None and (
        type(document) is not dict
        or not strict_json_contract_equal(document, expected)
    ):
        blockers.append("temporal_date_grid_gate_contract_invalid")
    if _authority_invalid(document):
        blockers.append("execution_authority_invalid")
    result = _verification(GATE_VERIFICATION_SCHEMA_VERSION, blockers)
    result["decision_status"] = (
        expected["status"] if expected is not None and not blockers else "BLOCK"
    )
    result["gate_hash"] = (
        expected["gate_hash"] if expected is not None and not blockers else ""
    )
    return result


__all__ = [
    "AUDIT_SCHEMA_VERSION",
    "DATE_GRID_RULE",
    "GATE_SCHEMA_VERSION",
    "GATE_VERIFICATION_SCHEMA_VERSION",
    "POLICY_SCHEMA_VERSION",
    "POLICY_VERIFICATION_SCHEMA_VERSION",
    "REQUIRED_PRICE_ROWS",
    "build_strategy_correlation_cluster_temporal_date_grid_audit",
    "build_strategy_correlation_cluster_temporal_date_grid_policy",
    "evaluate_strategy_correlation_cluster_temporal_date_grid_gate",
    "verify_strategy_correlation_cluster_temporal_date_grid_gate",
    "verify_strategy_correlation_cluster_temporal_date_grid_policy",
]
