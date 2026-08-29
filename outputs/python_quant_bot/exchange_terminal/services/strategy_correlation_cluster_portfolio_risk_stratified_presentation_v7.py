"""Neutral, unmounted joint presentation of adapter-v6 and budget-v3.

The v6 presentation contract predates active-strata portfolio budgeting.  This
consumer exactly verifies both sources and projects a bounded summary without
embedding verification contexts, positions, matrices, or source documents.
"""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as budget_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1 as envelope_v6,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-presentation-v7"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260823-stratified-portfolio-risk-presentation-v7-lock-1"
ENVELOPE_V6_IMPLEMENTATION_SHA256 = (
    "ec8977a0b3750b17a5ac35c20c6fe1791573a0529e0d8e61a81a07010ebf02dd"
)
BUDGET_V3_IMPLEMENTATION_SHA256 = (
    "bece44fe40c02242c879d1dead5cc11d2ce00edfc91c8d78a5b29962516c002d"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
PRESENTATION_GAPS = (
    "RUNTIME_INPUT_ADMISSION_NOT_ESTABLISHED",
    "CURRENT_MIGRATION_NOT_AUTHORIZED",
    "HTTP_PRESENTATION_CANDIDATE_NOT_REGISTERED",
    "BROWSER_REVIEW_NOT_PERFORMED",
    "PAPER_LIVE_UNAUTHORIZED",
)

V6_CONTEXT_KEYS = frozenset(
    {
        "adapter_v6_document",
        "adapter_v5_document",
        "downside_tail_registration",
        "downside_tail_evaluation",
        "expected_adapter_v6_hash",
        "adapter_v5_verification_context",
        "downside_tail_verification_context",
    }
)
BUDGET_V3_CONTEXT_KEYS = frozenset(
    {
        "preregistration",
        "correlation_matrix",
        "complete_link_audit",
        "strata_registration",
        "strata_gate",
        "complete_link_gate",
        "equity",
        "positions",
        "proposed_symbol",
        "proposed_notional",
        "proposed_direction",
        "max_cluster_gross_pct",
        "risk_increasing",
    }
)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "http_candidate_creation_allowed": False,
        "presentation_consumer_activation_allowed": False,
        "formal_registry_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "migration_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _is_hash(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_number_or_none(value: Any) -> bool:
    return bool(
        value is None
        or (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(float(value))
        )
    )


def _exact_context(value: Any, expected_keys: frozenset[str]) -> bool:
    return type(value) is dict and set(value) == set(expected_keys)


def _verify_v6(document: Any, context: Any) -> bool:
    if not _exact_context(context, V6_CONTEXT_KEYS):
        return False
    try:
        receipt = envelope_v6.verify_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1(
            document,
            context["adapter_v6_document"],
            context["adapter_v5_document"],
            context["downside_tail_registration"],
            context["downside_tail_evaluation"],
            expected_adapter_v6_hash=context["expected_adapter_v6_hash"],
            adapter_v5_verification_context=context[
                "adapter_v5_verification_context"
            ],
            downside_tail_verification_context=context[
                "downside_tail_verification_context"
            ],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        type(document) is dict
        and receipt.get("status") == "PASS"
        and receipt.get("envelope_exactly_verified") is True
        and receipt.get("envelope_status") == "BLOCK"
        and _is_hash(document.get("envelope_hash"))
        and receipt.get("envelope_hash") == document.get("envelope_hash")
        and document.get("schema_version") == envelope_v6.SCHEMA_VERSION
        and document.get("axis_order") == list(AXIS_ORDER)
        and type(document.get("local_decision")) is dict
        and document["local_decision"].get("status") in {"PASS", "BLOCK"}
        and type(document.get("facts")) is dict
        and document["facts"].get("source_documents_embedded") is False
        and document["facts"].get("positions_embedded") is False
        and document["facts"].get("ui_mounted") is False
        and receipt.get("current_admission_allowed") is False
        and receipt.get("runtime_gate_activation_allowed") is False
        and receipt.get("writer_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("live_order_allowed") is False
    )


def _verify_budget_v3(document: Any, context: Any) -> bool:
    if not _exact_context(context, BUDGET_V3_CONTEXT_KEYS):
        return False
    try:
        receipt = budget_v3.verify_strategy_correlation_cluster_effective_bet_budget_v3(
            document,
            context["preregistration"],
            context["correlation_matrix"],
            context["complete_link_audit"],
            strata_registration=context["strata_registration"],
            strata_gate=context["strata_gate"],
            complete_link_gate=context["complete_link_gate"],
            equity=context["equity"],
            positions=context["positions"],
            proposed_symbol=context["proposed_symbol"],
            proposed_notional=context["proposed_notional"],
            proposed_direction=context["proposed_direction"],
            max_cluster_gross_pct=context["max_cluster_gross_pct"],
            risk_increasing=context["risk_increasing"],
        )
    except (KeyError, TypeError, ValueError):
        return False
    expected_authority = {
        "descriptive_only": True,
        "runtime_gate_activation_allowed": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return bool(
        type(document) is dict
        and receipt.get("status") == "PASS"
        and receipt.get("budget_decision") in {
            "BLOCK",
            "PASS_STRATIFIED_RESEARCH_BUDGET",
            "RISK_REDUCTION_PATH",
        }
        and receipt.get("budget_v3_hash") == document.get("budget_v3_hash")
        and _is_hash(document.get("budget_v3_hash"))
        and document.get("schema_version") == budget_v3.BUDGET_SCHEMA_VERSION
        and document.get("status") in {"PASS", "BLOCK"}
        and strict_json_contract_equal(document.get("authority"), expected_authority)
        and type(document.get("portfolio")) is dict
        and type(document.get("facts")) is dict
        and document["facts"].get("source_documents_embedded") is False
        and document["facts"].get("cluster_exposure_rows_embedded") is False
        and document["facts"].get("strata_membership_rows_embedded") is False
        and document["facts"].get("profitability_proven") is False
        and receipt.get("current_admission_allowed") is False
        and receipt.get("runtime_gate_activation_allowed") is False
        and receipt.get("writer_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("live_order_allowed") is False
    )


def _dimension_results(document: dict[str, Any]) -> list[dict[str, Any]]:
    portfolio = document["portfolio"]
    raw_results = portfolio.get("dimension_results")
    if type(raw_results) is not list:
        raise ValueError("budget-v3 dimension results invalid")
    projected = []
    expected_keys = {
        "active_stratum_count",
        "dimension_id",
        "diversification_status",
        "dominant_stratum_id",
        "dominant_stratum_share_of_active_gross_pct",
        "gross_limit_status",
        "maximum_stratum_gross_pct",
        "over_limit_stratum_count",
        "status",
        "weighted_effective_strata_count",
    }
    for row in raw_results:
        if type(row) is not dict or set(row) != expected_keys:
            raise ValueError("budget-v3 dimension result shape invalid")
        if (
            type(row["dimension_id"]) is not str
            or not row["dimension_id"]
            or type(row["dominant_stratum_id"]) is not str
            or not row["dominant_stratum_id"]
            or type(row["active_stratum_count"]) is not int
            or isinstance(row["active_stratum_count"], bool)
            or type(row["over_limit_stratum_count"]) is not int
            or isinstance(row["over_limit_stratum_count"], bool)
            or not _is_number_or_none(row["weighted_effective_strata_count"])
            or not _is_number_or_none(row["maximum_stratum_gross_pct"])
            or not _is_number_or_none(
                row["dominant_stratum_share_of_active_gross_pct"]
            )
            or row["diversification_status"]
            not in {"PASS", "BLOCK", "NOT_APPLICABLE"}
            or row["gross_limit_status"] not in {"PASS", "BLOCK"}
            or row["status"] not in {"PASS", "BLOCK"}
        ):
            raise ValueError("budget-v3 dimension result invalid")
        projected.append({key: row[key] for key in sorted(expected_keys)})
    return projected


def _unknown() -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "axis_order": list(AXIS_ORDER),
            "decision": "UNKNOWN_SOURCE_PROJECTED_UNMOUNTED",
            "facts": {
                "browser_review_performed": False,
                "budget_v3_exactly_verified": False,
                "dimension_summaries_embedded": False,
                "http_candidate_registered": False,
                "joint_local_research_decision_made": False,
                "matrices_embedded": False,
                "positions_embedded": False,
                "profitability_proven": False,
                "projection_only": True,
                "runtime_assets_accessed": False,
                "runtime_consumer_bound": False,
                "source_documents_embedded": False,
                "ui_mounted": False,
                "v6_envelope_exactly_verified": False,
                "verification_contexts_embedded": False,
            },
            "gaps": {
                "local_blocker_count": 0,
                "presentation_blocker_count": len(PRESENTATION_GAPS),
                "presentation_blockers": list(PRESENTATION_GAPS),
                "stratified_budget_blocker_count": 0,
            },
            "local_decision": {
                "joint_decision": "UNKNOWN",
                "joint_status": "UNKNOWN",
                "portfolio_risk_v6_decision": "UNKNOWN",
                "portfolio_risk_v6_status": "UNKNOWN",
                "stratified_budget_decision": "UNKNOWN",
                "stratified_budget_status": "UNKNOWN",
            },
            "policy": {
                "budget_block_overrides_v6_local_clear": True,
                "local_block_preserved": True,
                "risk_reduction_is_not_execution_authority": True,
            },
            "risk_summary": {
                "active_dimension_count": None,
                "conservative_weighted_effective_strata_count": None,
                "dimension_results": [],
                "maximum_active_stratum_gross_pct": None,
                "total_active_gross_pct": None,
                "v2_weighted_effective_cluster_count": None,
                "weighted_diversification_gate_applied": None,
            },
            "schema_version": SCHEMA_VERSION,
            "source": {
                "budget_v3_context_hash": None,
                "budget_v3_hash": None,
                "budget_v3_implementation_sha256": BUDGET_V3_IMPLEMENTATION_SHA256,
                "envelope_v6_context_hash": None,
                "envelope_v6_hash": None,
                "envelope_v6_implementation_sha256": (
                    ENVELOPE_V6_IMPLEMENTATION_SHA256
                ),
                "state": "UNKNOWN",
                "strict_canonical_implementation_sha256": (
                    STRICT_CANONICAL_IMPLEMENTATION_SHA256
                ),
            },
            "stages": [
                {"axis": "SOURCE", "detail": "SOURCE_CONTRACT_UNKNOWN", "state": "UNKNOWN"},
                {"axis": "GAP", "detail": "SOURCE_CONTRACT_UNKNOWN", "state": "OPEN"},
                {"axis": "MATURITY", "detail": "UNMOUNTED_PRESENTATION_CANDIDATE", "state": "CANDIDATE"},
                {"axis": "PERMISSION", "detail": "NO_EXECUTION_OR_ACTIVATION_PERMISSION", "state": "NONE"},
            ],
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "BLOCK",
        },
        "presentation_v7_hash",
    )


def build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7(
    envelope_v6_document: Any,
    budget_v3_document: Any,
    *,
    envelope_v6_verification_context: Any,
    budget_v3_verification_context: Any,
) -> dict[str, Any]:
    v6_exact = _verify_v6(
        envelope_v6_document,
        envelope_v6_verification_context,
    )
    budget_exact = _verify_budget_v3(
        budget_v3_document,
        budget_v3_verification_context,
    )
    if not v6_exact or not budget_exact:
        return _unknown()
    try:
        dimensions = _dimension_results(budget_v3_document)
        v6_local = envelope_v6_document["local_decision"]
        budget_portfolio = budget_v3_document["portfolio"]
        budget_blockers = budget_v3_document["blockers"]
        if (
            type(budget_blockers) is not list
            or any(type(value) is not str for value in budget_blockers)
        ):
            return _unknown()
    except (KeyError, TypeError, ValueError):
        return _unknown()

    v6_status = v6_local["status"]
    v6_decision = v6_local["decision"]
    budget_status = budget_v3_document["status"]
    budget_decision = budget_v3_document["decision"]
    if budget_status == "BLOCK":
        joint_status = "BLOCK"
        joint_decision = "BLOCK_STRATIFIED_EFFECTIVE_BET_BUDGET"
    elif v6_status == "BLOCK":
        joint_status = "BLOCK"
        joint_decision = "BLOCK_PORTFOLIO_RISK_V6"
    else:
        joint_status = "PASS"
        joint_decision = "PASS_LOCAL_RESEARCH_COMPONENTS"

    local_blockers = []
    if type(v6_local.get("blockers")) is list:
        local_blockers.extend(
            value for value in v6_local["blockers"] if type(value) is str
        )
    local_blockers.extend(budget_blockers)
    local_blockers = sorted(set(local_blockers))
    maximum_gross = (
        max(row["maximum_stratum_gross_pct"] for row in dimensions)
        if dimensions
        else None
    )
    gap_state = "OPEN" if joint_status == "BLOCK" else "CLEAR_WITH_GOVERNANCE_GAPS"
    gap_detail = (
        "LOCAL_RESEARCH_BLOCK_PRESENT"
        if joint_status == "BLOCK"
        else "LOCAL_RESEARCH_GATES_CLEAR_GOVERNANCE_GAPS_REMAIN"
    )
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "axis_order": list(AXIS_ORDER),
            "decision": (
                "EXACT_JOINT_LOCAL_BLOCK_PROJECTED_UNMOUNTED"
                if joint_status == "BLOCK"
                else "EXACT_JOINT_LOCAL_CLEAR_PROJECTED_UNMOUNTED"
            ),
            "facts": {
                "browser_review_performed": False,
                "budget_v3_exactly_verified": True,
                "dimension_summaries_embedded": bool(dimensions),
                "http_candidate_registered": False,
                "joint_local_research_decision_made": True,
                "matrices_embedded": False,
                "positions_embedded": False,
                "profitability_proven": False,
                "projection_only": True,
                "runtime_assets_accessed": False,
                "runtime_consumer_bound": False,
                "source_documents_embedded": False,
                "ui_mounted": False,
                "v6_envelope_exactly_verified": True,
                "verification_contexts_embedded": False,
            },
            "gaps": {
                "local_blocker_count": len(local_blockers),
                "presentation_blocker_count": len(PRESENTATION_GAPS),
                "presentation_blockers": list(PRESENTATION_GAPS),
                "stratified_budget_blocker_count": len(budget_blockers),
            },
            "local_decision": {
                "joint_decision": joint_decision,
                "joint_status": joint_status,
                "portfolio_risk_v6_decision": v6_decision,
                "portfolio_risk_v6_status": v6_status,
                "stratified_budget_decision": budget_decision,
                "stratified_budget_status": budget_status,
            },
            "policy": {
                "budget_block_overrides_v6_local_clear": True,
                "local_block_preserved": True,
                "risk_reduction_is_not_execution_authority": True,
            },
            "risk_summary": {
                "active_dimension_count": budget_portfolio.get(
                    "active_dimension_count"
                ),
                "conservative_weighted_effective_strata_count": (
                    budget_portfolio.get(
                        "conservative_weighted_effective_strata_count"
                    )
                ),
                "dimension_results": dimensions,
                "maximum_active_stratum_gross_pct": maximum_gross,
                "total_active_gross_pct": budget_portfolio.get(
                    "total_active_gross_pct"
                ),
                "v2_weighted_effective_cluster_count": budget_portfolio.get(
                    "v2_weighted_effective_cluster_count"
                ),
                "weighted_diversification_gate_applied": budget_portfolio.get(
                    "weighted_diversification_gate_applied"
                ),
            },
            "schema_version": SCHEMA_VERSION,
            "source": {
                "budget_v3_context_hash": strict_canonical_hash(
                    budget_v3_verification_context
                ),
                "budget_v3_hash": budget_v3_document["budget_v3_hash"],
                "budget_v3_implementation_sha256": BUDGET_V3_IMPLEMENTATION_SHA256,
                "envelope_v6_context_hash": strict_canonical_hash(
                    envelope_v6_verification_context
                ),
                "envelope_v6_hash": envelope_v6_document["envelope_hash"],
                "envelope_v6_implementation_sha256": (
                    ENVELOPE_V6_IMPLEMENTATION_SHA256
                ),
                "state": "EXACT_V6_AND_BUDGET_V3",
                "strict_canonical_implementation_sha256": (
                    STRICT_CANONICAL_IMPLEMENTATION_SHA256
                ),
            },
            "stages": [
                {"axis": "SOURCE", "detail": "EXACT_V6_AND_BUDGET_V3", "state": "KNOWN"},
                {"axis": "GAP", "detail": gap_detail, "state": gap_state},
                {"axis": "MATURITY", "detail": "UNMOUNTED_PRESENTATION_CANDIDATE", "state": "CANDIDATE"},
                {"axis": "PERMISSION", "detail": "NO_EXECUTION_OR_ACTIVATION_PERMISSION", "state": "NONE"},
            ],
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "BLOCK",
        },
        "presentation_v7_hash",
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7(
    document: Any,
    envelope_v6_document: Any,
    budget_v3_document: Any,
    *,
    envelope_v6_verification_context: Any,
    budget_v3_verification_context: Any,
) -> dict[str, Any]:
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7(
            envelope_v6_document,
            budget_v3_document,
            envelope_v6_verification_context=envelope_v6_verification_context,
            budget_v3_verification_context=budget_v3_verification_context,
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        exact = False
        expected = None
    return {
        "blockers": [] if exact else ["PRESENTATION_V7_EXACT_REBUILD"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_decision": expected["decision"] if exact else "UNKNOWN",
        "presentation_status": "BLOCK" if exact else "UNKNOWN",
        "presentation_v7_hash": expected["presentation_v7_hash"] if exact else None,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }


__all__ = [
    "AXIS_ORDER",
    "BUDGET_V3_CONTEXT_KEYS",
    "PRESENTATION_GAPS",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "V6_CONTEXT_KEYS",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7",
]
