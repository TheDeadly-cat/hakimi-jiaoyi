"""Neutral public projection for the detached portfolio-risk adapter v3."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v3 as adapter_v3,
)


SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-projection-v3"
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-freshness-public-projection-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STAGE_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_AUTHORITY_FALSE_KEYS = frozenset(
    {
        "current_admission_allowed",
        "current_pointer_written",
        "formal_registry_activation_allowed",
        "live_order_allowed",
        "migration_allowed",
        "paper_authorized",
        "risk_service_invocation_allowed",
        "runtime_gate_activation_allowed",
        "shadow_consumer_activation_allowed",
        "writer_allowed",
    }
)

_GAP_BY_DECISION = {
    "WITHIN_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY": (
        "NONE_OBSERVED",
        "NO_LOCAL_POLICY_GAP_OBSERVED",
    ),
    "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_NOT_REQUIRED": (
        "NONE_OBSERVED",
        "VERIFIED_RISK_REDUCTION_FRESHNESS_EXEMPTION",
    ),
    "BLOCKED_SESSION_FRESHNESS": ("DECLARED", "SESSION_FRESHNESS"),
    "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET": (
        "DECLARED",
        "BASE_PORTFOLIO_RISK_BUDGET",
    ),
    "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY": (
        "DECLARED",
        "TEMPORAL_CORRELATION_STABILITY",
    ),
    "BLOCKED_ADAPTER_FRESHNESS_LINEAGE": (
        "DECLARED",
        "ADAPTER_FRESHNESS_LINEAGE",
    ),
    "BLOCKED_ADAPTER_V2_COMPONENT": (
        "DECLARED",
        "ADAPTER_V2_COMPONENT",
    ),
}


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _text(value: Any, default: str = "UNKNOWN") -> str:
    return value if type(value) is str and value else default


def _strict_sha256(value: Any) -> str | None:
    if type(value) is not str or len(value) != 64:
        return None
    if any(char not in "0123456789abcdef" for char in value):
        return None
    return value


def _string_list(value: Any) -> list[str]:
    if type(value) is not list or any(type(item) is not str for item in value):
        return []
    return list(value)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _adapter_authority_locked(value: Any) -> bool:
    authority = _dict(value)
    return bool(authority) and all(
        authority.get(key) is False for key in _AUTHORITY_FALSE_KEYS
    )


def _verify_adapter(
    document: Any,
    lineage_binding_v2: Any,
    lineage_binding_verification_context: Any,
) -> dict[str, Any]:
    try:
        return adapter_v3.verify_strategy_correlation_cluster_portfolio_risk_adapter_v3(
            document,
            lineage_binding_v2,
            lineage_binding_verification_context=(
                lineage_binding_verification_context
            ),
        )
    except Exception:
        return {}


def project_strategy_correlation_cluster_portfolio_risk_projection_v3(
    adapter_v3_document: Any,
    lineage_binding_v2: Any,
    *,
    lineage_binding_verification_context: Any,
) -> dict[str, Any]:
    """Project exact adapter-v3 state without granting or implying permission."""

    source_document = _dict(adapter_v3_document)
    source = _dict(source_document.get("source"))
    facts = _dict(source_document.get("facts"))
    authority = _dict(source_document.get("authority"))
    receipt = _verify_adapter(
        adapter_v3_document,
        lineage_binding_v2,
        lineage_binding_verification_context,
    )
    local_status = _text(source_document.get("status"))
    local_decision = _text(source_document.get("decision"))
    risk_increasing = _dict(source_document.get("policy")).get("risk_increasing")

    exact = bool(
        receipt.get("status") == "PASS"
        and receipt.get("adapter_v3_exactly_verified") is True
        and receipt.get("adapter_v3_status") == local_status
        and source_document.get("schema_version") == adapter_v3.SCHEMA_VERSION
        and source_document.get("static_fingerprint")
        == adapter_v3.STATIC_FINGERPRINT
        and _strict_sha256(source_document.get("adapter_hash"))
        and source.get("lineage_binding_exactly_verified") is True
        and facts.get("shared_native_lineage_verified") is True
        and facts.get("joint_admission_decision_made") is False
        and risk_increasing in (True, False)
        and local_status in ("PASS", "BLOCK")
        and _adapter_authority_locked(authority)
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
    )

    if exact:
        gap_state, gap_detail = _GAP_BY_DECISION.get(
            local_decision,
            ("DECLARED", "UNCLASSIFIED_LOCAL_POLICY_GAP"),
        )
        maturity_state = (
            "LOCAL_POLICY_SATISFIED"
            if local_status == "PASS"
            else "LOCAL_POLICY_BLOCKED"
        )
        projection_status = "PASS"
        projection_decision = (
            "EXACT_LOCAL_RESEARCH_DECISION_PROJECTED_AUTHORITY_UNCHANGED"
        )
        stages = [
            {
                "key": "SOURCE",
                "state": "VERIFIED",
                "detail": "ADAPTER_V3_EXACT_REBUILD",
            },
            {"key": "GAP", "state": gap_state, "detail": gap_detail},
            {
                "key": "MATURITY",
                "state": maturity_state,
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
            "adapter_v3_schema_version": _text(
                source_document.get("schema_version")
            ),
            "adapter_v3_hash": _strict_sha256(
                source_document.get("adapter_hash")
            ),
            "adapter_v3_exactly_verified": exact,
            "lineage_binding_schema_version": _text(
                source.get("lineage_binding_schema_version")
            ),
            "lineage_binding_hash": _strict_sha256(
                source.get("lineage_binding_hash")
            ),
            "freshness_evaluation_hash": _strict_sha256(
                source.get("freshness_evaluation_hash")
            ),
        },
        "local_decision": {
            "status": local_status,
            "decision": local_decision,
            "risk_increasing": risk_increasing,
            "session_freshness_required": (
                risk_increasing if type(risk_increasing) is bool else None
            ),
            "blockers": (
                _string_list(source_document.get("blockers")) if exact else []
            ),
            "warnings": (
                _string_list(source_document.get("warnings")) if exact else []
            ),
        },
        "stages": stages,
        "facts": {
            "projection_only": True,
            "source_document_embedded": False,
            "positions_embedded": False,
            "completed_price_rows_embedded": False,
            "return_series_embedded": False,
            "correlation_matrices_embedded": False,
            "profitability_proven": False,
            "runtime_consumer_bound": False,
        },
        "authority": {
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
        },
    }
    projection["projection_hash"] = _canonical_hash(projection)
    return projection


def verify_strategy_correlation_cluster_portfolio_risk_projection_v3(
    document: Any,
    adapter_v3_document: Any,
    lineage_binding_v2: Any,
    *,
    lineage_binding_verification_context: Any,
) -> dict[str, Any]:
    expected = project_strategy_correlation_cluster_portfolio_risk_projection_v3(
        adapter_v3_document,
        lineage_binding_v2,
        lineage_binding_verification_context=(
            lineage_binding_verification_context
        ),
    )
    exact = bool(type(document) is dict and document == expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "projection_exactly_verified": exact,
        "projection_status": expected.get("status") if exact else "UNKNOWN",
        "projection_hash": expected.get("projection_hash") if exact else None,
        "blockers": [] if exact else ["projection_v3_exact_rebuild"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


__all__ = [
    "SCHEMA_VERSION",
    "STAGE_ORDER",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "project_strategy_correlation_cluster_portfolio_risk_projection_v3",
    "verify_strategy_correlation_cluster_portfolio_risk_projection_v3",
]
