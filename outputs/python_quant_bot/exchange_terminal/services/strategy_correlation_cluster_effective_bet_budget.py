from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    AUDIT_SCHEMA_VERSION,
    TOPOLOGY_RULE,
    verify_correlation_cluster_complete_link_audit,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    PREREGISTRATION_SCHEMA_VERSION,
    verify_correlation_cluster_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v1"
BUDGET_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-effective-bet-budget-v1-verification-v1"
)
STATIC_FINGERPRINT = "20260822-all-cluster-effective-bet-budget-lock-1"
DEFAULT_MAX_CLUSTER_GROSS_PCT = 45.0


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "runtime_gate_activation_allowed": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _number(value: Any, *, positive: bool) -> float | None:
    if type(value) not in {int, float}:
        return None
    result = float(value)
    if not math.isfinite(result):
        return None
    if positive and result <= 0:
        return None
    return result


def _normalized_positions(positions: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if type(positions) is not list:
        return [], ["positions_contract_invalid"]
    normalized: list[dict[str, Any]] = []
    blockers: list[str] = []
    for index, raw in enumerate(positions):
        if type(raw) is not dict:
            blockers.append(f"position_{index}_contract_invalid")
            continue
        symbol_raw = raw.get("symbol")
        direction_raw = raw.get("direction")
        notional = _number(raw.get("notional"), positive=True)
        symbol = symbol_raw.strip().upper() if type(symbol_raw) is str else ""
        direction = (
            direction_raw.strip().upper()
            if type(direction_raw) is str
            else ""
        )
        if not symbol:
            blockers.append(f"position_{index}_symbol_invalid")
        if notional is None:
            blockers.append(f"position_{index}_notional_invalid")
        if direction not in {"LONG", "SHORT"}:
            blockers.append(f"position_{index}_direction_invalid")
        if symbol and notional is not None and direction in {"LONG", "SHORT"}:
            normalized.append(
                {
                    "symbol": symbol,
                    "notional": notional,
                    "direction": direction,
                }
            )
    return normalized, blockers


def _source_contract(
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    source = {
        "preregistration_schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "complete_link_audit_schema_version": AUDIT_SCHEMA_VERSION,
        "topology_rule": TOPOLOGY_RULE,
        "preregistration_verified": False,
        "matrix_bound_by_complete_link_audit": False,
        "complete_link_contract_verified": False,
        "complete_link_decision": "UNKNOWN",
    }
    blockers: list[str] = []
    membership: dict[str, str] = {}
    try:
        preregistration_verification = verify_correlation_cluster_preregistration(
            preregistration
        )
        audit_verification = verify_correlation_cluster_complete_link_audit(
            complete_link_audit,
            preregistration=preregistration,
            correlation_matrix=correlation_matrix,
        )
    except (KeyError, TypeError, ValueError):
        return source, membership, ["complete_link_source_verifier_error"]

    source["preregistration_verified"] = bool(
        type(preregistration_verification) is dict
        and preregistration_verification.get("status") == "PASS"
    )
    source["complete_link_contract_verified"] = bool(
        type(audit_verification) is dict
        and audit_verification.get("status") == "PASS"
        and audit_verification.get("current_admission_allowed") is False
        and audit_verification.get("current_writer_activation_allowed") is False
        and audit_verification.get("permissions")
        == {"paper_authorized": False, "live_order_allowed": False}
    )
    source["matrix_bound_by_complete_link_audit"] = source[
        "complete_link_contract_verified"
    ]
    if not source["preregistration_verified"]:
        blockers.append("preregistration_unverified")
    if not source["complete_link_contract_verified"]:
        blockers.append("complete_link_contract_unverified")
        return source, membership, blockers
    if type(complete_link_audit) is not dict:
        blockers.append("complete_link_audit_invalid")
        return source, membership, blockers

    decision = complete_link_audit.get("status")
    source["complete_link_decision"] = (
        decision if type(decision) is str else "UNKNOWN"
    )
    if decision != "PASS":
        blockers.append("complete_link_decision_block")
        return source, membership, blockers

    cluster_results = complete_link_audit.get("cluster_results")
    if type(cluster_results) is not list:
        blockers.append("cluster_results_invalid")
        return source, membership, blockers
    for cluster_index, cluster_result in enumerate(cluster_results):
        if type(cluster_result) is not dict:
            blockers.append(f"cluster_{cluster_index}_invalid")
            continue
        cluster_id_raw = cluster_result.get("cluster_id")
        cluster_id = (
            cluster_id_raw.strip().upper()
            if type(cluster_id_raw) is str
            else ""
        )
        members = cluster_result.get("members")
        if (
            not cluster_id
            or cluster_result.get("status") != "PASS"
            or type(members) is not list
            or not members
        ):
            blockers.append(f"cluster_{cluster_index}_assignment_invalid")
            continue
        for member in members:
            symbol = member.strip().upper() if type(member) is str else ""
            if not symbol:
                blockers.append(f"cluster_{cluster_index}_member_invalid")
            elif symbol in membership:
                blockers.append(f"cluster_assignment_duplicate:{symbol}")
            else:
                membership[symbol] = cluster_id
    return source, membership, blockers


def _risk_reduction_result() -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": BUDGET_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "PASS",
            "decision": "RISK_REDUCTION_PATH",
            "source": {
                "preregistration_schema_version": PREREGISTRATION_SCHEMA_VERSION,
                "complete_link_audit_schema_version": AUDIT_SCHEMA_VERSION,
                "topology_rule": TOPOLOGY_RULE,
                "preregistration_verified": False,
                "matrix_bound_by_complete_link_audit": False,
                "complete_link_contract_verified": False,
                "complete_link_decision": "NOT_EVALUATED",
            },
            "portfolio": {
                "equity": None,
                "symbol_ticket_count": None,
                "effective_independent_bet_count": None,
                "correlated_duplicate_ticket_count": None,
                "proposed_symbol": None,
                "proposed_direction": None,
                "proposed_notional": None,
            },
            "cluster_exposures": [],
            "checks": [
                {
                    "name": "risk_reduction_path",
                    "ok": True,
                    "message": "Risk-reducing actions are not blocked by research cluster budgets.",
                }
            ],
            "facts": {
                "risk_increasing": False,
                "all_active_clusters_evaluated": False,
                "proposal_centered_only": False,
                "direction_netting_used": False,
                "correlated_symbols_counted_as_one": False,
                "source_documents_embedded": False,
                "raw_correlations_embedded": False,
                "runtime_assets_accessed": False,
                "runtime_gate_integrated": False,
            },
            "authority": _authority(),
            "blockers": [],
        },
        "budget_hash",
    )


def evaluate_strategy_correlation_cluster_effective_bet_budget(
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    if type(risk_increasing) is not bool:
        risk_increasing = True
        risk_flag_blocker = ["risk_increasing_type_invalid"]
    else:
        risk_flag_blocker = []
    if risk_increasing is False:
        return _risk_reduction_result()

    clean_equity = _number(equity, positive=True)
    amount = _number(proposed_notional, positive=True)
    limit = _number(max_cluster_gross_pct, positive=False)
    symbol = (
        proposed_symbol.strip().upper()
        if type(proposed_symbol) is str
        else ""
    )
    direction = (
        proposed_direction.strip().upper()
        if type(proposed_direction) is str
        else ""
    )
    normalized_positions, input_blockers = _normalized_positions(positions)
    blockers = list(risk_flag_blocker) + input_blockers
    if clean_equity is None:
        blockers.append("equity_invalid")
    if amount is None:
        blockers.append("proposed_notional_invalid")
    if not symbol:
        blockers.append("proposed_symbol_invalid")
    if direction not in {"LONG", "SHORT"}:
        blockers.append("proposed_direction_invalid")
    if limit is None or limit < 0 or limit > 100:
        blockers.append("max_cluster_gross_pct_invalid")

    source, membership, source_blockers = _source_contract(
        preregistration,
        correlation_matrix,
        complete_link_audit,
    )
    blockers.extend(source_blockers)

    gross_by_symbol: dict[str, float] = {}
    for position in normalized_positions:
        gross_by_symbol[position["symbol"]] = (
            gross_by_symbol.get(position["symbol"], 0.0)
            + position["notional"]
        )
    if symbol and amount is not None:
        gross_by_symbol[symbol] = gross_by_symbol.get(symbol, 0.0) + amount

    active_symbols = sorted(gross_by_symbol)
    missing_assignments = sorted(
        active_symbol
        for active_symbol in active_symbols
        if active_symbol not in membership
    )
    if missing_assignments:
        blockers.append(
            "cluster_assignment_missing:" + ",".join(missing_assignments)
        )

    cluster_totals: dict[str, float] = {}
    cluster_symbols: dict[str, list[str]] = {}
    for active_symbol in active_symbols:
        cluster_id = membership.get(active_symbol)
        if cluster_id is None:
            continue
        cluster_totals[cluster_id] = (
            cluster_totals.get(cluster_id, 0.0) + gross_by_symbol[active_symbol]
        )
        cluster_symbols.setdefault(cluster_id, []).append(active_symbol)

    clean_limit = limit if limit is not None and 0 <= limit <= 100 else 0.0
    denominator = clean_equity if clean_equity is not None else 1e-12
    cluster_exposures: list[dict[str, Any]] = []
    over_limit_clusters: list[str] = []
    for cluster_id in sorted(cluster_totals):
        gross_notional = cluster_totals[cluster_id]
        gross_pct = gross_notional / denominator * 100.0
        status = "PASS" if gross_pct <= clean_limit + 1e-9 else "BLOCK"
        if status == "BLOCK":
            over_limit_clusters.append(cluster_id)
        cluster_exposures.append(
            {
                "cluster_id": cluster_id,
                "symbols": sorted(cluster_symbols[cluster_id]),
                "symbol_ticket_count": len(cluster_symbols[cluster_id]),
                "gross_notional": round(gross_notional, 2),
                "gross_exposure_pct": round(gross_pct, 4),
                "limit_pct": round(clean_limit, 4),
                "status": status,
            }
        )
    if over_limit_clusters:
        blockers.append("cluster_gross_limit_exceeded:" + ",".join(over_limit_clusters))

    effective_bets = len(cluster_totals) if not missing_assignments else None
    symbol_ticket_count = len(active_symbols)
    duplicate_tickets = (
        symbol_ticket_count - effective_bets
        if effective_bets is not None
        else None
    )
    source_ok = not source_blockers
    inputs_ok = not input_blockers and not risk_flag_blocker and all(
        blocker not in blockers
        for blocker in (
            "equity_invalid",
            "proposed_notional_invalid",
            "proposed_symbol_invalid",
            "proposed_direction_invalid",
            "max_cluster_gross_pct_invalid",
        )
    )
    coverage_ok = not missing_assignments and source_ok
    limits_ok = not over_limit_clusters and coverage_ok and inputs_ok
    checks = [
        {
            "name": "verified_complete_link_source",
            "ok": source_ok,
            "message": "Complete-link cluster source verified." if source_ok else "Complete-link cluster source unavailable or blocked.",
        },
        {
            "name": "portfolio_input_contract",
            "ok": inputs_ok,
            "message": "Portfolio inputs are strict and complete." if inputs_ok else "Portfolio input contract is invalid.",
        },
        {
            "name": "cluster_assignment_coverage",
            "ok": coverage_ok,
            "message": "Every active symbol has one verified cluster assignment." if coverage_ok else "At least one active symbol lacks a verified cluster assignment.",
        },
        {
            "name": "all_cluster_gross_limits",
            "ok": limits_ok,
            "message": "Every active cluster is within gross budget." if limits_ok else "At least one active cluster exceeds gross budget or could not be evaluated.",
        },
    ]
    status = "PASS" if all(check["ok"] for check in checks) else "BLOCK"
    return seal_strict_canonical_document(
        {
            "schema_version": BUDGET_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "decision": (
                "PASS_RESEARCH_BUDGET" if status == "PASS" else "BLOCK"
            ),
            "source": source,
            "portfolio": {
                "equity": round(clean_equity, 2) if clean_equity is not None else None,
                "symbol_ticket_count": symbol_ticket_count,
                "effective_independent_bet_count": effective_bets,
                "correlated_duplicate_ticket_count": duplicate_tickets,
                "proposed_symbol": symbol or None,
                "proposed_direction": direction or None,
                "proposed_notional": round(amount, 2) if amount is not None else None,
            },
            "cluster_exposures": cluster_exposures,
            "checks": checks,
            "facts": {
                "risk_increasing": True,
                "all_active_clusters_evaluated": coverage_ok,
                "proposal_centered_only": False,
                "direction_netting_used": False,
                "correlated_symbols_counted_as_one": bool(
                    duplicate_tickets is not None and duplicate_tickets > 0
                ),
                "source_documents_embedded": False,
                "raw_correlations_embedded": False,
                "runtime_assets_accessed": False,
                "runtime_gate_integrated": False,
            },
            "authority": _authority(),
            "blockers": sorted(set(blockers)),
        },
        "budget_hash",
    )


def verify_strategy_correlation_cluster_effective_bet_budget(
    document: Any,
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    expected = evaluate_strategy_correlation_cluster_effective_bet_budget(
        preregistration,
        correlation_matrix,
        complete_link_audit,
        equity=equity,
        positions=positions,
        proposed_symbol=proposed_symbol,
        proposed_notional=proposed_notional,
        proposed_direction=proposed_direction,
        max_cluster_gross_pct=max_cluster_gross_pct,
        risk_increasing=risk_increasing,
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": BUDGET_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["budget_exact_reconstruction"],
        "budget_decision": expected["decision"],
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "BUDGET_SCHEMA_VERSION",
    "BUDGET_VERIFICATION_SCHEMA_VERSION",
    "DEFAULT_MAX_CLUSTER_GROSS_PCT",
    "STATIC_FINGERPRINT",
    "evaluate_strategy_correlation_cluster_effective_bet_budget",
    "verify_strategy_correlation_cluster_effective_bet_budget",
]
