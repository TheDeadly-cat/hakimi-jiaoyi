"""Preregistered-strata successor for effective correlation-cluster budgets.

V2 weights active complete-link clusters but cannot consume the existing
preregistered strata contract.  This unmounted research consumer preserves the
exact v1/v2 decisions, then collapses active cluster gross into every frozen
strata dimension.  It grants no runtime, current, paper, live, or writer
authority.
"""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget as budget_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v2 as budget_v2,
)
from exchange_terminal.services import (
    strategy_correlation_preregistered_strata as strata_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v3"
BUDGET_VERIFICATION_SCHEMA_VERSION = f"{BUDGET_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260823-preregistered-strata-effective-budget-v3-lock-1"
V1_IMPLEMENTATION_SHA256 = (
    "b3a1fc720f9a54776279431abaef23155b6ab313868603e3a061919f698669b8"
)
V2_IMPLEMENTATION_SHA256 = (
    "1832e4dede892c8d5748a829cd39562773c425e0ce7c970b584538ade7c3adfe"
)
STRATA_IMPLEMENTATION_SHA256 = (
    "0758bd054adc2c98b51bf027cb5deea25e3620f555fd3369cdaf799c964adbb8"
)
COMPLETE_LINK_IMPLEMENTATION_SHA256 = (
    "a44851d07ce6757f11763f8f76f5036129ab0a718094a9cb1b46886781885be8"
)
MINIMUM_WEIGHTED_EFFECTIVE_STRATA_COUNT = 1.5
WEIGHTING_RULE = "INVERSE_HERFINDAHL_ON_ACTIVE_STRATUM_GROSS_NOTIONAL"
STRATUM_GROSS_RULE = "SUM_ACTIVE_MEMBER_CLUSTER_GROSS_NOTIONAL"
CONSERVATIVE_DIMENSION_RULE = "MINIMUM_ACROSS_ALL_PREREGISTERED_DIMENSIONS"


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


def _is_number(value: Any, *, positive: bool = False) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    clean = float(value)
    return math.isfinite(clean) and (clean > 0.0 if positive else clean >= 0.0)


def _hash_or_none(value: Any) -> str | None:
    if (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    ):
        return value
    return None


def _check(
    name: str,
    ok: bool,
    pass_message: str,
    block_message: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "message": pass_message if ok else block_message,
    }


def _call_v1(
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any,
    max_cluster_gross_pct: Any,
    risk_increasing: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    document = budget_v1.evaluate_strategy_correlation_cluster_effective_bet_budget(
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
    receipt = budget_v1.verify_strategy_correlation_cluster_effective_bet_budget(
        document,
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
    return document, receipt


def _call_v2(
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any,
    max_cluster_gross_pct: Any,
    risk_increasing: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    document = budget_v2.evaluate_strategy_correlation_cluster_effective_bet_budget_v2(
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
    receipt = budget_v2.verify_strategy_correlation_cluster_effective_bet_budget_v2(
        document,
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
    return document, receipt


def _derive_dimension_metrics(
    registration: Any,
    v1_document: Any,
    v2_document: Any,
    *,
    max_cluster_gross_pct: Any,
) -> list[dict[str, Any]]:
    if type(registration) is not dict or type(v1_document) is not dict:
        raise ValueError("stratified source documents invalid")
    if type(v2_document) is not dict or not _is_number(
        max_cluster_gross_pct,
        positive=True,
    ):
        raise ValueError("stratified policy invalid")
    dimensions = registration.get("dimensions")
    exposures = v1_document.get("cluster_exposures")
    portfolio = v1_document.get("portfolio")
    v2_portfolio = v2_document.get("portfolio")
    if (
        type(dimensions) is not list
        or not dimensions
        or type(exposures) is not list
        or type(portfolio) is not dict
        or type(v2_portfolio) is not dict
        or not _is_number(portfolio.get("equity"), positive=True)
    ):
        raise ValueError("stratified source shape invalid")

    equity = float(portfolio["equity"])
    gross_by_cluster: dict[str, float] = {}
    for row in exposures:
        if type(row) is not dict:
            raise ValueError("cluster exposure row invalid")
        cluster_id = row.get("cluster_id")
        gross_notional = row.get("gross_notional")
        if (
            type(cluster_id) is not str
            or not cluster_id.strip()
            or not _is_number(gross_notional, positive=True)
            or row.get("status") not in {"PASS", "BLOCK"}
        ):
            raise ValueError("cluster exposure row invalid")
        normalized_cluster_id = cluster_id.strip().upper()
        if normalized_cluster_id in gross_by_cluster:
            raise ValueError("cluster exposure duplicated")
        gross_by_cluster[normalized_cluster_id] = float(gross_notional)
    if not gross_by_cluster:
        raise ValueError("active cluster exposure missing")

    total_gross = sum(gross_by_cluster.values())
    total_gross_pct = total_gross / equity * 100.0
    v2_total_gross_pct = v2_portfolio.get("total_active_gross_pct")
    trigger_applied = v2_portfolio.get("weighted_diversification_gate_applied")
    if (
        not _is_number(v2_total_gross_pct)
        or abs(float(v2_total_gross_pct) - total_gross_pct) > 1e-6
        or type(trigger_applied) is not bool
    ):
        raise ValueError("v1/v2 active gross binding invalid")

    limit = float(max_cluster_gross_pct)
    results: list[dict[str, Any]] = []
    for dimension in dimensions:
        if type(dimension) is not dict:
            raise ValueError("strata dimension invalid")
        dimension_id = dimension.get("dimension_id")
        strata = dimension.get("strata")
        if type(dimension_id) is not str or not dimension_id or type(strata) is not list:
            raise ValueError("strata dimension invalid")
        cluster_to_stratum: dict[str, str] = {}
        for stratum in strata:
            if type(stratum) is not dict:
                raise ValueError("stratum invalid")
            stratum_id = stratum.get("stratum_id")
            cluster_ids = stratum.get("cluster_ids")
            if (
                type(stratum_id) is not str
                or not stratum_id
                or type(cluster_ids) is not list
                or not cluster_ids
            ):
                raise ValueError("stratum invalid")
            for cluster_id in cluster_ids:
                if type(cluster_id) is not str or not cluster_id.strip():
                    raise ValueError("stratum cluster invalid")
                normalized_cluster_id = cluster_id.strip().upper()
                if normalized_cluster_id in cluster_to_stratum:
                    raise ValueError("stratum cluster duplicated")
                cluster_to_stratum[normalized_cluster_id] = stratum_id
        if not set(gross_by_cluster).issubset(cluster_to_stratum):
            raise ValueError("active cluster lacks preregistered stratum")

        gross_by_stratum: dict[str, float] = {}
        for cluster_id, gross_notional in gross_by_cluster.items():
            stratum_id = cluster_to_stratum[cluster_id]
            gross_by_stratum[stratum_id] = (
                gross_by_stratum.get(stratum_id, 0.0) + gross_notional
            )
        squared_gross = sum(value * value for value in gross_by_stratum.values())
        if squared_gross <= 0.0:
            raise ValueError("active stratum gross invalid")
        weighted_count = total_gross * total_gross / squared_gross
        dominant_stratum_id, dominant_gross = min(
            gross_by_stratum.items(),
            key=lambda item: (-item[1], item[0]),
        )
        maximum_stratum_gross_pct = max(gross_by_stratum.values()) / equity * 100.0
        over_limit_count = sum(
            gross_notional / equity * 100.0 > limit + 1e-9
            for gross_notional in gross_by_stratum.values()
        )
        diversification_ok = bool(
            not trigger_applied
            or weighted_count + 1e-12
            >= MINIMUM_WEIGHTED_EFFECTIVE_STRATA_COUNT
        )
        gross_limit_ok = over_limit_count == 0
        results.append(
            {
                "active_stratum_count": len(gross_by_stratum),
                "dimension_id": dimension_id,
                "diversification_status": (
                    "NOT_APPLICABLE"
                    if not trigger_applied
                    else "PASS"
                    if diversification_ok
                    else "BLOCK"
                ),
                "dominant_stratum_id": dominant_stratum_id,
                "dominant_stratum_share_of_active_gross_pct": round(
                    dominant_gross / total_gross * 100.0,
                    6,
                ),
                "gross_limit_status": "PASS" if gross_limit_ok else "BLOCK",
                "maximum_stratum_gross_pct": round(
                    maximum_stratum_gross_pct,
                    6,
                ),
                "over_limit_stratum_count": over_limit_count,
                "status": (
                    "PASS" if gross_limit_ok and diversification_ok else "BLOCK"
                ),
                "weighted_effective_strata_count": round(weighted_count, 6),
            }
        )
    return sorted(results, key=lambda row: row["dimension_id"])


def evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    strata_registration: Any = None,
    strata_gate: Any = None,
    complete_link_gate: Any = None,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = budget_v1.DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    try:
        v1_document, v1_receipt = _call_v1(
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
    except (KeyError, TypeError, ValueError):
        v1_document, v1_receipt = {}, {}
    try:
        v2_document, v2_receipt = _call_v2(
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
    except (KeyError, TypeError, ValueError):
        v2_document, v2_receipt = {}, {}

    v1_exact = v1_receipt.get("status") == "PASS"
    v2_exact = v2_receipt.get("status") == "PASS"
    v1_status = v1_document.get("status") if v1_exact else "UNKNOWN"
    v2_status = v2_document.get("status") if v2_exact else "UNKNOWN"
    v1_hash = _hash_or_none(v1_document.get("budget_hash"))
    v2_hash = _hash_or_none(v2_document.get("budget_v2_hash"))
    v1_v2_hash_bound = bool(
        v1_exact
        and v2_exact
        and v1_hash is not None
        and type(v2_document.get("source")) is dict
        and v2_document["source"].get("v1_budget_hash") == v1_hash
        and v2_document["source"].get("v1_exactly_verified") is True
    )
    risk_reduction = bool(
        type(risk_increasing) is bool
        and risk_increasing is False
        and v2_exact
        and v2_status == "PASS"
        and v2_document.get("decision") == "RISK_REDUCTION_PATH"
    )
    strata_required = not risk_reduction

    registration_exact = False
    gate_exact = False
    gate_status = "NOT_APPLICABLE" if not strata_required else "UNKNOWN"
    same_source = False
    registration_hash = None
    gate_hash = None
    complete_link_gate_hash = None
    if strata_required:
        try:
            registration_receipt = (
                strata_v1.verify_strategy_correlation_strata_preregistration(
                    strata_registration,
                    source_preregistration=preregistration,
                )
            )
            registration_exact = registration_receipt.get("status") == "PASS"
            gate_receipt = strata_v1.verify_strategy_correlation_strata_gate(
                strata_gate,
                registration=strata_registration,
                complete_link_gate=complete_link_gate,
                source_preregistration=preregistration,
            )
            gate_exact = gate_receipt.get("status") == "PASS"
        except (KeyError, TypeError, ValueError):
            registration_exact = False
            gate_exact = False
        if type(strata_gate) is dict and gate_exact:
            gate_status = strata_gate.get("status", "UNKNOWN")
            gate_hash = _hash_or_none(strata_gate.get("gate_hash"))
        if type(strata_registration) is dict and registration_exact:
            registration_hash = _hash_or_none(
                strata_registration.get("registration_hash")
            )
        if type(complete_link_gate) is dict:
            complete_link_gate_hash = _hash_or_none(
                complete_link_gate.get("gate_hash")
            )
        preregistration_hash = (
            preregistration.get("preregistration_hash")
            if type(preregistration) is dict
            else None
        )
        same_source = bool(
            registration_exact
            and gate_exact
            and registration_hash is not None
            and gate_hash is not None
            and complete_link_gate_hash is not None
            and strata_registration.get("source_preregistration_hash")
            == preregistration_hash
            and strata_gate.get("source_preregistration_hash")
            == preregistration_hash
            and strata_gate.get("strata_registration_hash") == registration_hash
            and strata_gate.get("base_complete_link_gate_hash")
            == complete_link_gate_hash
        )

    dimension_results: list[dict[str, Any]] = []
    metrics_exact = risk_reduction
    if (
        strata_required
        and registration_exact
        and v1_exact
        and v2_exact
        and v1_status == "PASS"
    ):
        try:
            dimension_results = _derive_dimension_metrics(
                strata_registration,
                v1_document,
                v2_document,
                max_cluster_gross_pct=max_cluster_gross_pct,
            )
            metrics_exact = bool(dimension_results)
        except (KeyError, TypeError, ValueError):
            metrics_exact = False

    blockers: list[str] = []
    if not v1_exact:
        blockers.append("v1_exact_verification")
    if not v2_exact:
        blockers.append("v2_exact_verification")
    if not v1_v2_hash_bound:
        blockers.append("v1_v2_hash_binding")
    if v1_status != "PASS":
        blockers.append("v1_budget_gate")
    if v2_status != "PASS":
        blockers.append("v2_budget_gate")
    if strata_required:
        if not registration_exact:
            blockers.append("strata_registration_exact_verification")
        if not gate_exact:
            blockers.append("strata_gate_exact_verification")
        if gate_status != "PASS":
            blockers.append("strata_gate_decision")
        if not same_source:
            blockers.append("strata_source_hash_binding")
        if not metrics_exact:
            blockers.append("stratified_metrics")

    over_limit_dimensions = [
        row["dimension_id"]
        for row in dimension_results
        if row["gross_limit_status"] == "BLOCK"
    ]
    low_effective_dimensions = [
        row["dimension_id"]
        for row in dimension_results
        if row["diversification_status"] == "BLOCK"
    ]
    if over_limit_dimensions:
        blockers.append(
            "stratum_gross_limit_exceeded:" + ",".join(over_limit_dimensions)
        )
    if low_effective_dimensions:
        blockers.append(
            "weighted_effective_strata_gate:" + ",".join(low_effective_dimensions)
        )

    blockers = sorted(set(blockers))
    status = "PASS" if not blockers else "BLOCK"
    conservative_count = (
        min(row["weighted_effective_strata_count"] for row in dimension_results)
        if dimension_results
        else None
    )
    v2_portfolio = (
        v2_document.get("portfolio")
        if type(v2_document.get("portfolio")) is dict
        else {}
    )
    checks = [
        _check(
            "v1_v2_exact_chain",
            v1_exact and v2_exact and v1_v2_hash_bound,
            "V1 and v2 are exactly rebuilt and hash-bound.",
            "V1 or v2 cannot be exactly rebuilt and hash-bound.",
        ),
        _check(
            "v2_budget_gate",
            v2_status == "PASS",
            "The weighted cluster budget passes.",
            "The weighted cluster budget blocks or is unknown.",
        ),
        _check(
            "preregistered_strata_chain",
            risk_reduction
            or (
                registration_exact
                and gate_exact
                and gate_status == "PASS"
                and same_source
            ),
            "The preregistered strata chain passes or is not applicable.",
            "The preregistered strata chain is blocked, inexact, or misbound.",
        ),
        _check(
            "active_strata_metrics",
            metrics_exact,
            "Active cluster gross is exactly collapsed by preregistered strata.",
            "Active strata metrics cannot be exactly derived.",
        ),
        _check(
            "all_stratum_gross_limits",
            not over_limit_dimensions,
            "Every active stratum is within the gross limit.",
            "At least one active stratum exceeds the gross limit.",
        ),
        _check(
            "weighted_effective_strata_gate",
            not low_effective_dimensions,
            "Every dimension has sufficient active weighted strata or is below trigger.",
            "At least one dimension has insufficient active weighted strata.",
        ),
    ]
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "blockers": blockers,
            "checks": checks,
            "decision": (
                "RISK_REDUCTION_PATH"
                if status == "PASS" and risk_reduction
                else "PASS_STRATIFIED_RESEARCH_BUDGET"
                if status == "PASS"
                else "BLOCK"
            ),
            "facts": {
                "cluster_exposure_rows_embedded": False,
                "cluster_labels_treated_as_independent_bets": False,
                "direction_netting_used": False,
                "profitability_proven": False,
                "risk_increasing": risk_increasing
                if type(risk_increasing) is bool
                else None,
                "runtime_assets_accessed": False,
                "runtime_gate_integrated": False,
                "same_stratum_active_clusters_collapsed": bool(dimension_results),
                "source_documents_embedded": False,
                "strata_membership_rows_embedded": False,
                "strata_required": strata_required,
                "stratified_metrics_exactly_derived": metrics_exact,
            },
            "policy": {
                "conservative_dimension_rule": CONSERVATIVE_DIMENSION_RULE,
                "minimum_weighted_effective_strata_count": (
                    MINIMUM_WEIGHTED_EFFECTIVE_STRATA_COUNT
                ),
                "stratum_gross_limit_pct": (
                    float(max_cluster_gross_pct)
                    if _is_number(max_cluster_gross_pct, positive=True)
                    else None
                ),
                "stratum_gross_rule": STRATUM_GROSS_RULE,
                "weighting_rule": WEIGHTING_RULE,
            },
            "portfolio": {
                "active_cluster_count": v2_portfolio.get("active_cluster_count"),
                "active_dimension_count": len(dimension_results),
                "conservative_weighted_effective_strata_count": conservative_count,
                "dimension_results": dimension_results,
                "symbol_ticket_count": v2_portfolio.get("symbol_ticket_count"),
                "total_active_gross_pct": v2_portfolio.get(
                    "total_active_gross_pct"
                ),
                "v2_weighted_effective_cluster_count": v2_portfolio.get(
                    "weighted_effective_cluster_count"
                ),
                "weighted_diversification_gate_applied": v2_portfolio.get(
                    "weighted_diversification_gate_applied"
                ),
            },
            "schema_version": BUDGET_SCHEMA_VERSION,
            "source": {
                "complete_link_gate_hash": complete_link_gate_hash,
                "complete_link_implementation_sha256": (
                    COMPLETE_LINK_IMPLEMENTATION_SHA256
                ),
                "precomputed_predecessor_result_accepted": False,
                "same_source_preregistration_verified": same_source,
                "strata_gate_hash": gate_hash,
                "strata_gate_status": gate_status,
                "strata_implementation_sha256": STRATA_IMPLEMENTATION_SHA256,
                "strata_registration_hash": registration_hash,
                "strata_registration_schema_version": (
                    strata_registration.get("schema_version")
                    if registration_exact and type(strata_registration) is dict
                    else None
                ),
                "v1_budget_hash": v1_hash,
                "v1_implementation_sha256": V1_IMPLEMENTATION_SHA256,
                "v1_status": v1_status,
                "v2_budget_hash": v2_hash,
                "v2_implementation_sha256": V2_IMPLEMENTATION_SHA256,
                "v2_status": v2_status,
            },
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
        },
        "budget_v3_hash",
    )


def verify_strategy_correlation_cluster_effective_bet_budget_v3(
    document: Any,
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    strata_registration: Any = None,
    strata_gate: Any = None,
    complete_link_gate: Any = None,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = budget_v1.DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    try:
        expected = evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
            preregistration,
            correlation_matrix,
            complete_link_audit,
            strata_registration=strata_registration,
            strata_gate=strata_gate,
            complete_link_gate=complete_link_gate,
            equity=equity,
            positions=positions,
            proposed_symbol=proposed_symbol,
            proposed_notional=proposed_notional,
            proposed_direction=proposed_direction,
            max_cluster_gross_pct=max_cluster_gross_pct,
            risk_increasing=risk_increasing,
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        exact = False
        expected = None
    return {
        "budget_decision": expected["decision"] if exact else "UNKNOWN",
        "budget_v3_hash": expected["budget_v3_hash"] if exact else None,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": BUDGET_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }


__all__ = [
    "BUDGET_SCHEMA_VERSION",
    "BUDGET_VERIFICATION_SCHEMA_VERSION",
    "CONSERVATIVE_DIMENSION_RULE",
    "MINIMUM_WEIGHTED_EFFECTIVE_STRATA_COUNT",
    "STATIC_FINGERPRINT",
    "STRATUM_GROSS_RULE",
    "WEIGHTING_RULE",
    "evaluate_strategy_correlation_cluster_effective_bet_budget_v3",
    "verify_strategy_correlation_cluster_effective_bet_budget_v3",
]
