"""Detached local research decision over portfolio-risk and session freshness.

This adapter consumes the exact ADR0188 lineage binding.  It does not grant
runtime, paper, live, registry, writer, or migration authority.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2
    as lineage_v2,
)


SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-adapter-v3"
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-temporal-session-freshness-adapter-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"

LINEAGE_CONTEXT_KEYS = frozenset(
    {
        "adapter_v2_document",
        "freshness_evaluation",
        "legacy_matrix_binding",
        "adapter_v2_verification_context",
        "freshness_verification_context",
        "legacy_matrix_binding_verification_context",
    }
)

_LINEAGE_AUTHORITY_FALSE_KEYS = frozenset(
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

_PRESERVED_ADAPTER_BLOCK_DECISIONS = frozenset(
    {
        "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET",
        "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY",
    }
)


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _exact_context(value: Any) -> dict[str, Any] | None:
    if type(value) is not dict or set(value) != LINEAGE_CONTEXT_KEYS:
        return None
    return value


def _text(value: Any, default: str = "UNKNOWN") -> str:
    return value if type(value) is str and value else default


def _strict_sha256(value: Any) -> str | None:
    if type(value) is not str or len(value) != 64:
        return None
    if any(char not in "0123456789abcdef" for char in value):
        return None
    return value


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _authority_is_locked(value: Any) -> bool:
    authority = _dict(value)
    return bool(authority) and all(
        authority.get(key) is False for key in _LINEAGE_AUTHORITY_FALSE_KEYS
    )


def _verify_lineage(
    document: Any,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    if context is None:
        return {}
    try:
        return lineage_v2.verify_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2(
            document,
            context["adapter_v2_document"],
            context["freshness_evaluation"],
            context["legacy_matrix_binding"],
            adapter_v2_verification_context=(
                context["adapter_v2_verification_context"]
            ),
            freshness_verification_context=(
                context["freshness_verification_context"]
            ),
            legacy_matrix_binding_verification_context=(
                context["legacy_matrix_binding_verification_context"]
            ),
        )
    except Exception:
        return {}


def evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v3(
    lineage_binding_v2: Any,
    *,
    lineage_binding_verification_context: Any,
) -> dict[str, Any]:
    """Make a detached, local-only research decision from exact bound inputs."""

    context = _exact_context(lineage_binding_verification_context)
    lineage_document = _dict(lineage_binding_v2)
    receipt = _verify_lineage(lineage_binding_v2, context)

    adapter_document = _dict(
        context.get("adapter_v2_document") if context is not None else None
    )
    freshness_document = _dict(
        context.get("freshness_evaluation") if context is not None else None
    )
    legacy_document = _dict(
        context.get("legacy_matrix_binding") if context is not None else None
    )

    component_states = _dict(lineage_document.get("component_states"))
    lineage_facts = _dict(lineage_document.get("facts"))
    adapter_facts = _dict(adapter_document.get("facts"))

    adapter_status = _text(adapter_document.get("status"))
    adapter_decision = _text(adapter_document.get("decision"))
    freshness_status = _text(freshness_document.get("status"))
    freshness_decision = _text(freshness_document.get("decision"))
    legacy_status = _text(legacy_document.get("status"))
    legacy_decision = _text(legacy_document.get("decision"))
    risk_increasing = adapter_facts.get("risk_increasing")

    component_identity = bool(
        type(component_states) is dict
        and component_states.get("adapter_v2_status") == adapter_status
        and component_states.get("adapter_v2_decision") == adapter_decision
        and component_states.get("session_freshness_status") == freshness_status
        and component_states.get("session_freshness_decision")
        == freshness_decision
        and component_states.get("legacy_matrix_binding_status") == legacy_status
        and component_states.get("legacy_matrix_binding_decision")
        == legacy_decision
    )
    receipt_authority_locked = all(
        receipt.get(key) is False
        for key in (
            "current_admission_allowed",
            "joint_admission_decision_allowed",
            "live_order_allowed",
            "paper_authorized",
            "runtime_gate_activation_allowed",
            "shadow_consumer_activation_allowed",
        )
    )
    lineage_exact = bool(
        context is not None
        and receipt.get("status") == "PASS"
        and receipt.get("lineage_binding_exactly_verified") is True
        and receipt.get("lineage_binding_status") == "PASS"
        and lineage_document.get("status") == "PASS"
        and lineage_facts.get("shared_native_lineage_verified") is True
        and lineage_facts.get("lineage_binding_only") is True
        and lineage_facts.get("joint_admission_decision_made") is False
        and lineage_facts.get("external_provider_trust_verified") is False
        and lineage_facts.get("external_time_authority_verified") is False
        and component_identity
        and _authority_is_locked(lineage_document.get("authority"))
        and receipt_authority_locked
        and risk_increasing in (True, False)
    )

    status = "BLOCK"
    decision = "BLOCKED_ADAPTER_FRESHNESS_LINEAGE"
    blockers = ["ADAPTER_FRESHNESS_LINEAGE_V2_INVALID"]
    warnings: list[str] = []

    if lineage_exact:
        blockers = []
        if risk_increasing is False:
            if (
                adapter_status == "PASS"
                and adapter_decision
                == "RISK_REDUCTION_PATH_TEMPORAL_STABILITY_NOT_REQUIRED"
            ):
                status = "PASS"
                decision = (
                    "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_"
                    "NOT_REQUIRED"
                )
                if freshness_status == "BLOCK":
                    warnings.append(
                        "SESSION_FRESHNESS_BLOCK_OBSERVED_RISK_REDUCTION_ONLY"
                    )
            else:
                decision = "BLOCKED_ADAPTER_V2_COMPONENT"
                blockers = ["ADAPTER_V2_REDUCTION_CONTRACT_INVALID"]
        elif adapter_status == "BLOCK":
            decision = (
                adapter_decision
                if adapter_decision in _PRESERVED_ADAPTER_BLOCK_DECISIONS
                else "BLOCKED_ADAPTER_V2_COMPONENT"
            )
            blockers = [
                (
                    "BASE_ADAPTER_V2_BLOCKED"
                    if decision == "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET"
                    else "TEMPORAL_STABILITY_BLOCKED"
                    if decision == "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY"
                    else "ADAPTER_V2_COMPONENT_INVALID"
                )
            ]
        elif (
            adapter_status != "PASS"
            or adapter_decision
            != "WITHIN_RESEARCH_RISK_BUDGET_AND_TEMPORAL_STABILITY"
        ):
            decision = "BLOCKED_ADAPTER_V2_COMPONENT"
            blockers = ["ADAPTER_V2_COMPONENT_INVALID"]
        elif freshness_status == "BLOCK":
            decision = "BLOCKED_SESSION_FRESHNESS"
            blockers = ["SESSION_FRESHNESS_BLOCKED"]
        elif freshness_status != "PASS":
            decision = "BLOCKED_SESSION_FRESHNESS"
            blockers = ["SESSION_FRESHNESS_COMPONENT_INVALID"]
        else:
            status = "PASS"
            decision = (
                "WITHIN_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_"
                "SESSION_FRESHNESS_LOCAL_ONLY"
            )

    adapter_passed = bool(lineage_exact and adapter_status == "PASS")
    freshness_satisfied = bool(
        lineage_exact
        and (risk_increasing is False or freshness_status == "PASS")
    )
    checks = [
        {
            "name": "lineage_binding_v2_exact_verification",
            "ok": lineage_exact,
            "blocking": True,
        },
        {
            "name": "adapter_v2_component_pass",
            "ok": adapter_passed,
            "blocking": True,
        },
        {
            "name": "session_freshness_pass_or_risk_reduction_exemption",
            "ok": freshness_satisfied,
            "blocking": True,
        },
        {
            "name": "external_authority_not_promoted",
            "ok": True,
            "blocking": True,
        },
    ]

    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": decision,
        "source": {
            "lineage_binding_schema_version": _text(
                lineage_document.get("schema_version")
            ),
            "lineage_binding_hash": _strict_sha256(
                lineage_document.get("lineage_binding_hash")
            ),
            "lineage_binding_exactly_verified": lineage_exact,
            "adapter_v2_schema_version": _text(
                adapter_document.get("schema_version")
            ),
            "adapter_v2_hash": _strict_sha256(
                adapter_document.get("adapter_hash")
            ),
            "freshness_schema_version": _text(
                freshness_document.get("schema_version")
            ),
            "freshness_evaluation_hash": _strict_sha256(
                freshness_document.get("evaluation_hash")
            ),
            "legacy_matrix_binding_schema_version": _text(
                legacy_document.get("schema_version")
            ),
            "legacy_matrix_binding_hash": _strict_sha256(
                legacy_document.get("binding_hash")
            ),
        },
        "component_states": {
            "adapter_v2_status": adapter_status if lineage_exact else "UNKNOWN",
            "adapter_v2_decision": (
                adapter_decision if lineage_exact else "UNKNOWN"
            ),
            "session_freshness_status": (
                freshness_status if lineage_exact else "UNKNOWN"
            ),
            "session_freshness_decision": (
                freshness_decision if lineage_exact else "UNKNOWN"
            ),
            "legacy_matrix_binding_status": (
                legacy_status if lineage_exact else "UNKNOWN"
            ),
            "legacy_matrix_binding_decision": (
                legacy_decision if lineage_exact else "UNKNOWN"
            ),
        },
        "policy": {
            "risk_increasing": risk_increasing if lineage_exact else None,
            "adapter_v2_required": True,
            "temporal_stability_required_for_risk_increase": True,
            "session_freshness_required_for_risk_increase": True,
            "session_freshness_required_for_risk_reduction": False,
        },
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "facts": {
            "joint_local_research_decision_made": lineage_exact,
            "joint_admission_decision_made": False,
            "lineage_binding_only_input": True,
            "shared_native_lineage_verified": bool(
                lineage_exact
                and lineage_facts.get("shared_native_lineage_verified") is True
            ),
            "external_provider_trust_verified": False,
            "external_time_authority_verified": False,
            "profitability_proven": False,
            "risk_service_invoked": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "source_documents_embedded": False,
            "positions_embedded": False,
            "completed_price_rows_embedded": False,
            "return_series_embedded": False,
            "correlation_matrices_embedded": False,
        },
        "authority": {
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
        },
    }
    document["adapter_hash"] = _canonical_hash(document)
    return document


def verify_strategy_correlation_cluster_portfolio_risk_adapter_v3(
    document: Any,
    lineage_binding_v2: Any,
    *,
    lineage_binding_verification_context: Any,
) -> dict[str, Any]:
    """Rebuild adapter-v3 and require byte-semantic document equality."""

    expected = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v3(
        lineage_binding_v2,
        lineage_binding_verification_context=(
            lineage_binding_verification_context
        ),
    )
    exact = bool(type(document) is dict and document == expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "adapter_v3_exactly_verified": exact,
        "adapter_v3_status": (
            expected.get("status") if exact else "UNKNOWN"
        ),
        "adapter_v3_hash": (
            expected.get("adapter_hash") if exact else None
        ),
        "blockers": [] if exact else ["adapter_v3_exact_rebuild"],
        "current_admission_allowed": False,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


__all__ = [
    "LINEAGE_CONTEXT_KEYS",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v3",
    "verify_strategy_correlation_cluster_portfolio_risk_adapter_v3",
]
