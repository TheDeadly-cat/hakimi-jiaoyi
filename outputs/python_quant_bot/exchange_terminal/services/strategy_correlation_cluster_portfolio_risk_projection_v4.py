"""Neutral public projection for weighted portfolio-risk adapter-v4."""

from __future__ import annotations

import copy
import math
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v4 as adapter_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-projection-v4"
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-weighted-diversification-public-projection-v4-lock-1"
)
ADAPTER_V4_IMPLEMENTATION_SHA256 = (
    "d57c69f88746ac168334e37545c465f22d2d9e5453d3a814c7b64b57604c9202"
)
STAGE_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

ADAPTER_V4_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "adapter_v3_document",
        "weighted_budget_v2_document",
        "adapter_v3_verification_context",
        "weighted_budget_v2_verification_context",
    }
)

_GAP_BY_DECISION = {
    "WITHIN_WEIGHTED_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY": (
        "NONE_OBSERVED",
        "NO_LOCAL_WEIGHTED_POLICY_GAP_OBSERVED",
    ),
    "RISK_REDUCTION_PATH_WEIGHTED_DIVERSIFICATION_NOT_REQUIRED": (
        "NONE_OBSERVED",
        "VERIFIED_RISK_REDUCTION_WEIGHTED_EXEMPTION",
    ),
    "BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION": (
        "DECLARED",
        "WEIGHTED_CLUSTER_DIVERSIFICATION",
    ),
    "BLOCKED_ADAPTER_V3_COMPONENT": ("DECLARED", "ADAPTER_V3_COMPONENT"),
    "BLOCKED_WEIGHTED_BUDGET_COMPONENT": (
        "DECLARED",
        "WEIGHTED_BUDGET_COMPONENT",
    ),
    "BLOCKED_WEIGHTED_ADAPTER_COMPONENT_VERIFICATION": (
        "DECLARED",
        "ADAPTER_V4_COMPONENT_OR_LINEAGE",
    ),
}

_V4_AUTHORITY = {
    "research_only": True,
    "local_decision_only": True,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "formal_registry_activation_allowed": False,
    "live_order_allowed": False,
    "migration_allowed": False,
    "paper_authorized": False,
    "risk_service_invocation_allowed": False,
    "runtime_gate_activation_allowed": False,
    "shadow_consumer_activation_allowed": False,
    "writer_allowed": False,
}


def _projection_authority() -> dict[str, bool]:
    return {
        "research_only": True,
        "presentation_only": True,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _exact_context(value: Any) -> dict[str, Any] | None:
    return (
        value
        if type(value) is dict
        and frozenset(value) == ADAPTER_V4_VERIFICATION_CONTEXT_KEYS
        else None
    )


def _hash(value: Any) -> str | None:
    if (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    ):
        return value
    return None


def _number(value: Any) -> int | float | None:
    return (
        value
        if type(value) in {int, float} and math.isfinite(float(value))
        else None
    )


def _string_list(value: Any) -> list[str]:
    return (
        list(value)
        if type(value) is list and all(type(item) is str for item in value)
        else []
    )


def _verify_adapter(document: Any, context: Any) -> dict[str, Any]:
    exact_context = _exact_context(context)
    if exact_context is None:
        return {}
    try:
        receipt = adapter_v4.verify_strategy_correlation_cluster_portfolio_risk_adapter_v4(
            copy.deepcopy(document),
            copy.deepcopy(exact_context["adapter_v3_document"]),
            copy.deepcopy(exact_context["weighted_budget_v2_document"]),
            adapter_v3_verification_context=copy.deepcopy(
                exact_context["adapter_v3_verification_context"]
            ),
            weighted_budget_v2_verification_context=copy.deepcopy(
                exact_context["weighted_budget_v2_verification_context"]
            ),
        )
    except Exception:
        return {}
    return receipt if type(receipt) is dict else {}


def _weighted_summary(
    document: dict[str, Any], *, risk_increasing: bool
) -> dict[str, Any] | None:
    portfolio = _dict(document.get("portfolio"))
    unweighted = portfolio.get("unweighted_effective_cluster_count")
    weighted = _number(portfolio.get("weighted_effective_cluster_count"))
    dominant = _number(
        portfolio.get("dominant_cluster_share_of_active_gross_pct")
    )
    gate_applied = portfolio.get("weighted_diversification_gate_applied")
    if risk_increasing is False:
        if (
            unweighted is not None
            or weighted is not None
            or dominant is not None
            or gate_applied is not False
        ):
            return None
        assessment = "NOT_APPLICABLE"
    else:
        if (
            type(unweighted) is not int
            or unweighted <= 0
            or weighted is None
            or float(weighted) <= 0.0
            or dominant is None
            or not 0.0 <= float(dominant) <= 100.0
            or type(gate_applied) is not bool
        ):
            return None
        decision = document.get("decision")
        assessment = (
            "CONCENTRATED"
            if decision == "BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION"
            else "SUFFICIENT"
            if document.get("status") == "PASS"
            else "UPSTREAM_BLOCKED"
        )
    return {
        "assessment": assessment,
        "unweighted_effective_cluster_count": unweighted,
        "weighted_effective_cluster_count": weighted,
        "dominant_cluster_share_of_active_gross_pct": dominant,
        "minimum_weighted_effective_cluster_count": 1.5,
        "gate_applied": gate_applied,
    }


def project_strategy_correlation_cluster_portfolio_risk_projection_v4(
    adapter_v4_document: Any,
    *,
    adapter_v4_verification_context: Any,
) -> dict[str, Any]:
    source_document = _dict(adapter_v4_document)
    source = _dict(source_document.get("source"))
    facts = _dict(source_document.get("facts"))
    policy = _dict(source_document.get("policy"))
    receipt = _verify_adapter(
        adapter_v4_document, adapter_v4_verification_context
    )
    local_status = source_document.get("status")
    local_decision = source_document.get("decision")
    risk_increasing = policy.get("risk_increasing")
    weighted = (
        _weighted_summary(source_document, risk_increasing=risk_increasing)
        if type(risk_increasing) is bool
        else None
    )
    exact = bool(
        _exact_context(adapter_v4_verification_context) is not None
        and receipt.get("status") == "PASS"
        and receipt.get("adapter_v4_exactly_verified") is True
        and receipt.get("adapter_v4_status") == local_status
        and receipt.get("adapter_v4_hash") == source_document.get("adapter_hash")
        and receipt.get("blockers") == []
        and all(
            receipt.get(key) is False
            for key in (
                "current_admission_allowed",
                "formal_registry_activation_allowed",
                "live_order_allowed",
                "paper_authorized",
                "runtime_gate_activation_allowed",
                "shadow_consumer_activation_allowed",
                "writer_allowed",
            )
        )
        and source_document.get("schema_version") == adapter_v4.SCHEMA_VERSION
        and source_document.get("static_fingerprint")
        == adapter_v4.STATIC_FINGERPRINT
        and local_status in {"PASS", "BLOCK"}
        and local_decision in _GAP_BY_DECISION
        and _hash(source_document.get("adapter_hash")) is not None
        and _hash(source.get("adapter_v3_hash")) is not None
        and _hash(source.get("weighted_budget_v2_hash")) is not None
        and _hash(source.get("v1_budget_hash")) is not None
        and type(risk_increasing) is bool
        and weighted is not None
        and facts.get("profitability_proven") is False
        and facts.get("runtime_consumer_bound") is False
        and source_document.get("authority") == _V4_AUTHORITY
    )

    if exact:
        gap_state, gap_detail = _GAP_BY_DECISION[local_decision]
        projection_status = "PASS"
        projection_decision = (
            "EXACT_WEIGHTED_LOCAL_RESEARCH_DECISION_PROJECTED_AUTHORITY_UNCHANGED"
        )
        stages = [
            {
                "key": "SOURCE",
                "state": "VERIFIED",
                "detail": "ADAPTER_V4_EXACT_REBUILD",
            },
            {"key": "GAP", "state": gap_state, "detail": gap_detail},
            {
                "key": "MATURITY",
                "state": (
                    "LOCAL_POLICY_SATISFIED"
                    if local_status == "PASS"
                    else "LOCAL_POLICY_BLOCKED"
                ),
                "detail": local_decision,
            },
            {
                "key": "PERMISSION",
                "state": "UNAUTHORIZED",
                "detail": "NO_RUNTIME_PAPER_OR_LIVE_AUTHORITY",
            },
        ]
    else:
        projection_status = "BLOCK"
        projection_decision = "UNKNOWN_SOURCE"
        local_status = "UNKNOWN"
        local_decision = "UNKNOWN"
        risk_increasing = None
        weighted = {
            "assessment": "UNKNOWN",
            "unweighted_effective_cluster_count": None,
            "weighted_effective_cluster_count": None,
            "dominant_cluster_share_of_active_gross_pct": None,
            "minimum_weighted_effective_cluster_count": 1.5,
            "gate_applied": None,
        }
        stages = [
            {"key": "SOURCE", "state": "UNKNOWN", "detail": "UNKNOWN"},
            {"key": "GAP", "state": "UNKNOWN", "detail": "UNKNOWN"},
            {"key": "MATURITY", "state": "UNKNOWN", "detail": "UNKNOWN"},
            {
                "key": "PERMISSION",
                "state": "UNAUTHORIZED",
                "detail": "NO_PERMISSION_CAN_BE_INFERRED",
            },
        ]

    projection: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": projection_status,
        "decision": projection_decision,
        "source": {
            "adapter_v4_schema_version": (
                source_document.get("schema_version") if exact else "UNKNOWN"
            ),
            "adapter_v4_hash": (
                _hash(source_document.get("adapter_hash")) if exact else None
            ),
            "adapter_v4_exactly_verified": exact,
            "adapter_v4_implementation_sha256": ADAPTER_V4_IMPLEMENTATION_SHA256,
            "adapter_v3_hash": _hash(source.get("adapter_v3_hash")) if exact else None,
            "weighted_budget_v2_hash": (
                _hash(source.get("weighted_budget_v2_hash")) if exact else None
            ),
            "v1_budget_hash": _hash(source.get("v1_budget_hash")) if exact else None,
        },
        "local_decision": {
            "status": local_status,
            "decision": local_decision,
            "risk_increasing": risk_increasing,
            "blockers": (
                _string_list(source_document.get("blockers")) if exact else []
            ),
            "warnings": (
                _string_list(source_document.get("warnings")) if exact else []
            ),
        },
        "weighted_diversification": weighted,
        "stages": stages,
        "facts": {
            "projection_only": True,
            "source_document_embedded": False,
            "component_documents_embedded": False,
            "positions_embedded": False,
            "cluster_exposure_rows_embedded": False,
            "correlation_matrices_embedded": False,
            "profitability_proven": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
        },
        "authority": _projection_authority(),
    }
    return seal_strict_canonical_document(projection, "projection_hash")


def verify_strategy_correlation_cluster_portfolio_risk_projection_v4(
    document: Any,
    adapter_v4_document: Any,
    *,
    adapter_v4_verification_context: Any,
) -> dict[str, Any]:
    expected = project_strategy_correlation_cluster_portfolio_risk_projection_v4(
        adapter_v4_document,
        adapter_v4_verification_context=adapter_v4_verification_context,
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "projection_exactly_verified": exact,
        "projection_status": expected.get("status") if exact else "UNKNOWN",
        "projection_hash": expected.get("projection_hash") if exact else None,
        "blockers": [] if exact else ["projection_v4_exact_rebuild"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


__all__ = [
    "SCHEMA_VERSION",
    "VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "ADAPTER_V4_IMPLEMENTATION_SHA256",
    "ADAPTER_V4_VERIFICATION_CONTEXT_KEYS",
    "STAGE_ORDER",
    "project_strategy_correlation_cluster_portfolio_risk_projection_v4",
    "verify_strategy_correlation_cluster_portfolio_risk_projection_v4",
]
