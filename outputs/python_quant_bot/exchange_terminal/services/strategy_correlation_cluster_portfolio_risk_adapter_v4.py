"""Shadow adapter joining adapter-v3 with weighted cluster diversification v2.

The adapter requires exact public verification and shared original-input lineage
for both components.  It is a local research candidate only and cannot register
itself, invoke runtime risk services, write current, or authorize trading.
"""

from __future__ import annotations

import copy
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v2 as weighted_v2,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v3 as adapter_v3,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-adapter-v4"
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260823-weighted-diversification-adapter-v4-shadow-lock-1"
ADAPTER_V3_IMPLEMENTATION_SHA256 = (
    "fc9faaf1c4366593e004b4c8e798f5cefafaaf985687c3f7bf7a44fd6e663fe7"
)
WEIGHTED_V2_IMPLEMENTATION_SHA256 = (
    "1832e4dede892c8d5748a829cd39562773c425e0ce7c970b584538ade7c3adfe"
)

ADAPTER_V3_VERIFICATION_CONTEXT_KEYS = frozenset(
    {"lineage_binding_v2", "lineage_binding_verification_context"}
)
WEIGHTED_V2_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "preregistration",
        "correlation_matrix",
        "complete_link_audit",
        "equity",
        "positions",
        "proposed_symbol",
        "proposed_notional",
        "proposed_direction",
        "max_cluster_gross_pct",
        "risk_increasing",
    }
)
_ADAPTER_V1_CONTEXT_KEYS = frozenset(
    {
        "preregistration",
        "cluster_correlation_matrix",
        "complete_link_audit",
        "equity",
        "positions",
        "proposed_symbol",
        "proposed_notional",
        "proposed_direction",
        "proposed_cluster",
        "risk_increasing",
        "legacy_correlations",
        "regime",
        "legacy_limits",
        "max_cluster_gross_pct",
    }
)
_ADAPTER_V2_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "adapter_v1_document",
        "temporal_stability_gate",
        "adapter_v1_verification_context",
        "temporal_stability_verification_context",
    }
)

_VERIFY_ADAPTER_V3 = (
    adapter_v3.verify_strategy_correlation_cluster_portfolio_risk_adapter_v3
)
_VERIFY_WEIGHTED_V2 = (
    weighted_v2.verify_strategy_correlation_cluster_effective_bet_budget_v2
)


def _authority() -> dict[str, bool]:
    return {
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


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _exact_dict(value: Any, keys: frozenset[str]) -> dict[str, Any] | None:
    return value if type(value) is dict and frozenset(value) == keys else None


def _hash(value: Any) -> str | None:
    if (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    ):
        return value
    return None


def _v3_authority_locked(document: Any) -> bool:
    return type(document) is dict and document == adapter_v3.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v3.__globals__.get("_authority", lambda: {})()


def _v3_authority_shape_locked(value: Any) -> bool:
    expected = _authority()
    return type(value) is dict and value == expected


def _weighted_authority_locked(value: Any) -> bool:
    authority = _dict(value)
    return bool(
        authority
        and authority.get("descriptive_only") is True
        and all(
            item is False
            for key, item in authority.items()
            if key != "descriptive_only"
        )
    )


def _call_adapter_v3_verifier(document: Any, context: Any) -> dict[str, Any]:
    exact_context = _exact_dict(context, ADAPTER_V3_VERIFICATION_CONTEXT_KEYS)
    if exact_context is None:
        return {}
    try:
        receipt = _VERIFY_ADAPTER_V3(
            copy.deepcopy(document),
            copy.deepcopy(exact_context["lineage_binding_v2"]),
            lineage_binding_verification_context=copy.deepcopy(
                exact_context["lineage_binding_verification_context"]
            ),
        )
    except Exception:
        return {}
    return receipt if type(receipt) is dict else {}


def _adapter_v3_exact(document: Any, context: Any) -> bool:
    receipt = _call_adapter_v3_verifier(document, context)
    value = _dict(document)
    policy = _dict(value.get("policy"))
    return bool(
        receipt.get("status") == "PASS"
        and receipt.get("adapter_v3_exactly_verified") is True
        and receipt.get("adapter_v3_status") in {"PASS", "BLOCK"}
        and receipt.get("adapter_v3_status") == value.get("status")
        and receipt.get("adapter_v3_hash") == value.get("adapter_hash")
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
        and value.get("schema_version") == adapter_v3.SCHEMA_VERSION
        and value.get("static_fingerprint") == adapter_v3.STATIC_FINGERPRINT
        and value.get("status") in {"PASS", "BLOCK"}
        and type(value.get("decision")) is str
        and _hash(value.get("adapter_hash")) is not None
        and type(policy.get("risk_increasing")) is bool
        and _v3_authority_shape_locked(value.get("authority"))
    )


def _call_weighted_v2_verifier(document: Any, context: Any) -> dict[str, Any]:
    exact_context = _exact_dict(context, WEIGHTED_V2_VERIFICATION_CONTEXT_KEYS)
    if exact_context is None:
        return {}
    try:
        receipt = _VERIFY_WEIGHTED_V2(
            copy.deepcopy(document),
            copy.deepcopy(exact_context["preregistration"]),
            copy.deepcopy(exact_context["correlation_matrix"]),
            copy.deepcopy(exact_context["complete_link_audit"]),
            equity=copy.deepcopy(exact_context["equity"]),
            positions=copy.deepcopy(exact_context["positions"]),
            proposed_symbol=copy.deepcopy(exact_context["proposed_symbol"]),
            proposed_notional=copy.deepcopy(exact_context["proposed_notional"]),
            proposed_direction=copy.deepcopy(exact_context["proposed_direction"]),
            max_cluster_gross_pct=copy.deepcopy(
                exact_context["max_cluster_gross_pct"]
            ),
            risk_increasing=copy.deepcopy(exact_context["risk_increasing"]),
        )
    except Exception:
        return {}
    return receipt if type(receipt) is dict else {}


def _weighted_v2_exact(document: Any, context: Any) -> bool:
    receipt = _call_weighted_v2_verifier(document, context)
    value = _dict(document)
    source = _dict(value.get("source"))
    policy = _dict(value.get("policy"))
    facts = _dict(value.get("facts"))
    return bool(
        receipt.get("status") == "PASS"
        and receipt.get("blockers") == []
        and receipt.get("budget_decision") == value.get("decision")
        and all(
            receipt.get(key) is False
            for key in (
                "runtime_gate_activation_allowed",
                "current_admission_allowed",
                "paper_authorized",
                "live_order_allowed",
            )
        )
        and value.get("schema_version") == weighted_v2.BUDGET_SCHEMA_VERSION
        and value.get("static_fingerprint") == weighted_v2.STATIC_FINGERPRINT
        and value.get("status") in {"PASS", "BLOCK"}
        and value.get("decision")
        in {"PASS_WEIGHTED_RESEARCH_BUDGET", "RISK_REDUCTION_PATH", "BLOCK"}
        and _hash(value.get("budget_v2_hash")) is not None
        and source.get("v1_exactly_verified") is True
        and _hash(source.get("v1_budget_hash")) is not None
        and source.get("v1_implementation_sha256")
        == weighted_v2.V1_IMPLEMENTATION_SHA256
        and policy.get("weighting_rule") == weighted_v2.WEIGHTING_RULE
        and policy.get("diversification_trigger_rule")
        == weighted_v2.DIVERSIFICATION_TRIGGER_RULE
        and policy.get("minimum_weighted_effective_cluster_count")
        == weighted_v2.MINIMUM_WEIGHTED_EFFECTIVE_CLUSTER_COUNT
        and type(facts.get("risk_increasing")) is bool
        and _weighted_authority_locked(value.get("authority"))
    )


def _shared_lineage(
    adapter_v3_document: Any,
    adapter_v3_context: Any,
    weighted_document: Any,
    weighted_context: Any,
) -> dict[str, str] | None:
    v3_context = _exact_dict(
        adapter_v3_context, ADAPTER_V3_VERIFICATION_CONTEXT_KEYS
    )
    weighted = _exact_dict(
        weighted_context, WEIGHTED_V2_VERIFICATION_CONTEXT_KEYS
    )
    if v3_context is None or weighted is None:
        return None
    lineage_context = _exact_dict(
        v3_context.get("lineage_binding_verification_context"),
        adapter_v3.LINEAGE_CONTEXT_KEYS,
    )
    if lineage_context is None:
        return None
    adapter_v2_context = _exact_dict(
        lineage_context.get("adapter_v2_verification_context"),
        _ADAPTER_V2_VERIFICATION_CONTEXT_KEYS,
    )
    if adapter_v2_context is None:
        return None
    adapter_v1_context = _exact_dict(
        adapter_v2_context.get("adapter_v1_verification_context"),
        _ADAPTER_V1_CONTEXT_KEYS,
    )
    adapter_v1_document = _dict(adapter_v2_context.get("adapter_v1_document"))
    adapter_v1_source = _dict(adapter_v1_document.get("source"))
    weighted_source = _dict(_dict(weighted_document).get("source"))
    adapter_v2_document = _dict(lineage_context.get("adapter_v2_document"))
    v3_source = _dict(_dict(adapter_v3_document).get("source"))
    if adapter_v1_context is None:
        return None
    identities = (
        weighted["preregistration"] == adapter_v1_context["preregistration"],
        weighted["correlation_matrix"]
        == adapter_v1_context["cluster_correlation_matrix"],
        weighted["complete_link_audit"]
        == adapter_v1_context["complete_link_audit"],
        weighted["equity"] == adapter_v1_context["equity"],
        weighted["positions"] == adapter_v1_context["positions"],
        weighted["proposed_symbol"] == adapter_v1_context["proposed_symbol"],
        weighted["proposed_notional"]
        == adapter_v1_context["proposed_notional"],
        weighted["proposed_direction"]
        == adapter_v1_context["proposed_direction"],
        weighted["max_cluster_gross_pct"]
        == adapter_v1_context["max_cluster_gross_pct"],
        weighted["risk_increasing"] == adapter_v1_context["risk_increasing"],
    )
    adapter_v1_hash = _hash(adapter_v1_document.get("adapter_hash"))
    v1_budget_hash = _hash(adapter_v1_source.get("effective_bet_budget_hash"))
    adapter_v2_hash = _hash(adapter_v2_document.get("adapter_hash"))
    if (
        not all(identities)
        or adapter_v1_hash is None
        or v1_budget_hash is None
        or adapter_v2_hash is None
        or weighted_source.get("v1_budget_hash") != v1_budget_hash
        or v3_source.get("adapter_v2_hash") != adapter_v2_hash
    ):
        return None
    return {
        "adapter_v1_hash": adapter_v1_hash,
        "adapter_v2_hash": adapter_v2_hash,
        "v1_budget_hash": v1_budget_hash,
    }


def _check(name: str, ok: bool) -> dict[str, Any]:
    return {"name": name, "ok": ok, "blocking": True}


def evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v4(
    adapter_v3_document: Any,
    weighted_budget_v2_document: Any,
    *,
    adapter_v3_verification_context: Any,
    weighted_budget_v2_verification_context: Any,
) -> dict[str, Any]:
    v3_exact = _adapter_v3_exact(
        adapter_v3_document, adapter_v3_verification_context
    )
    weighted_exact = _weighted_v2_exact(
        weighted_budget_v2_document, weighted_budget_v2_verification_context
    )
    lineage = (
        _shared_lineage(
            adapter_v3_document,
            adapter_v3_verification_context,
            weighted_budget_v2_document,
            weighted_budget_v2_verification_context,
        )
        if v3_exact and weighted_exact
        else None
    )
    lineage_exact = lineage is not None
    v3 = _dict(adapter_v3_document)
    weighted = _dict(weighted_budget_v2_document)
    v3_policy = _dict(v3.get("policy"))
    weighted_facts = _dict(weighted.get("facts"))
    risk_increasing = (
        v3_policy.get("risk_increasing")
        if lineage_exact
        and type(v3_policy.get("risk_increasing")) is bool
        and v3_policy.get("risk_increasing")
        == weighted_facts.get("risk_increasing")
        else None
    )
    component_contracts_exact = bool(v3_exact and weighted_exact and lineage_exact)
    v3_pass = bool(component_contracts_exact and v3.get("status") == "PASS")
    weighted_pass = bool(
        component_contracts_exact and weighted.get("status") == "PASS"
    )

    status = "BLOCK"
    decision = "BLOCKED_WEIGHTED_ADAPTER_COMPONENT_VERIFICATION"
    blockers = ["ADAPTER_V4_COMPONENT_OR_LINEAGE_INVALID"]
    warnings: list[str] = []
    if component_contracts_exact:
        blockers = []
        if risk_increasing is False:
            if (
                v3_pass
                and v3.get("decision")
                == "RISK_REDUCTION_PATH_TEMPORAL_AND_SESSION_FRESHNESS_NOT_REQUIRED"
                and weighted_pass
                and weighted.get("decision") == "RISK_REDUCTION_PATH"
            ):
                status = "PASS"
                decision = "RISK_REDUCTION_PATH_WEIGHTED_DIVERSIFICATION_NOT_REQUIRED"
            else:
                blockers = ["RISK_REDUCTION_COMPONENT_CONTRACT_INVALID"]
        elif risk_increasing is not True:
            blockers = ["RISK_DIRECTION_LINEAGE_INVALID"]
        elif not v3_pass:
            decision = "BLOCKED_ADAPTER_V3_COMPONENT"
            blockers = ["ADAPTER_V3_BLOCKED"]
        elif not weighted_pass:
            if "weighted_effective_cluster_gate" in weighted.get("blockers", []):
                decision = "BLOCKED_WEIGHTED_CLUSTER_DIVERSIFICATION"
                blockers = ["WEIGHTED_EFFECTIVE_CLUSTER_GATE_BLOCKED"]
            else:
                decision = "BLOCKED_WEIGHTED_BUDGET_COMPONENT"
                blockers = ["WEIGHTED_BUDGET_V2_BLOCKED"]
        elif (
            v3.get("decision")
            != "WITHIN_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_AND_SESSION_FRESHNESS_LOCAL_ONLY"
            or weighted.get("decision") != "PASS_WEIGHTED_RESEARCH_BUDGET"
        ):
            blockers = ["COMPONENT_DECISION_CONTRACT_INVALID"]
        else:
            status = "PASS"
            decision = (
                "WITHIN_WEIGHTED_RESEARCH_RISK_BUDGET_TEMPORAL_STABILITY_"
                "AND_SESSION_FRESHNESS_LOCAL_ONLY"
            )

    weighted_portfolio = _dict(weighted.get("portfolio")) if weighted_exact else {}
    checks = [
        _check("adapter_v3_exact_public_verification", v3_exact),
        _check("weighted_budget_v2_exact_public_verification", weighted_exact),
        _check("shared_original_input_and_v1_budget_lineage", lineage_exact),
        _check("adapter_v3_component_pass", v3_pass),
        _check(
            "weighted_budget_pass_or_risk_reduction_exemption",
            weighted_pass,
        ),
        _check("external_authority_not_promoted", True),
    ]
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": decision,
        "source": {
            "adapter_v3_schema_version": (
                v3.get("schema_version") if v3_exact else None
            ),
            "adapter_v3_hash": _hash(v3.get("adapter_hash")) if v3_exact else None,
            "adapter_v3_implementation_sha256": ADAPTER_V3_IMPLEMENTATION_SHA256,
            "weighted_budget_v2_schema_version": (
                weighted.get("schema_version") if weighted_exact else None
            ),
            "weighted_budget_v2_hash": (
                _hash(weighted.get("budget_v2_hash")) if weighted_exact else None
            ),
            "weighted_budget_v2_implementation_sha256": (
                WEIGHTED_V2_IMPLEMENTATION_SHA256
            ),
            "adapter_v1_hash": lineage.get("adapter_v1_hash") if lineage else None,
            "adapter_v2_hash": lineage.get("adapter_v2_hash") if lineage else None,
            "v1_budget_hash": lineage.get("v1_budget_hash") if lineage else None,
            "component_documents_embedded": False,
            "verification_contexts_embedded": False,
        },
        "component_states": {
            "adapter_v3_status": v3.get("status") if v3_exact else "UNKNOWN",
            "adapter_v3_decision": v3.get("decision") if v3_exact else "UNKNOWN",
            "weighted_budget_v2_status": (
                weighted.get("status") if weighted_exact else "UNKNOWN"
            ),
            "weighted_budget_v2_decision": (
                weighted.get("decision") if weighted_exact else "UNKNOWN"
            ),
        },
        "portfolio": {
            "unweighted_effective_cluster_count": weighted_portfolio.get(
                "unweighted_effective_cluster_count"
            ),
            "weighted_effective_cluster_count": weighted_portfolio.get(
                "weighted_effective_cluster_count"
            ),
            "dominant_cluster_share_of_active_gross_pct": weighted_portfolio.get(
                "dominant_cluster_share_of_active_gross_pct"
            ),
            "weighted_diversification_gate_applied": weighted_portfolio.get(
                "weighted_diversification_gate_applied"
            ),
        },
        "policy": {
            "risk_increasing": risk_increasing,
            "adapter_v3_required": True,
            "weighted_budget_v2_required": True,
            "shared_original_inputs_required": True,
            "shared_v1_budget_hash_required": True,
            "minimum_weighted_effective_cluster_count": (
                weighted_v2.MINIMUM_WEIGHTED_EFFECTIVE_CLUSTER_COUNT
            ),
        },
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "facts": {
            "joint_local_research_decision_made": component_contracts_exact,
            "component_decisions_jointly_required_for_risk_increase": True,
            "weighted_diversification_consumed": weighted_exact,
            "temporal_and_session_freshness_preserved": v3_exact,
            "component_documents_embedded": False,
            "source_documents_embedded": False,
            "positions_embedded": False,
            "correlation_matrices_embedded": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "risk_service_invoked": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "adapter_hash")


def verify_strategy_correlation_cluster_portfolio_risk_adapter_v4(
    document: Any,
    adapter_v3_document: Any,
    weighted_budget_v2_document: Any,
    *,
    adapter_v3_verification_context: Any,
    weighted_budget_v2_verification_context: Any,
) -> dict[str, Any]:
    try:
        expected = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v4(
            adapter_v3_document,
            weighted_budget_v2_document,
            adapter_v3_verification_context=adapter_v3_verification_context,
            weighted_budget_v2_verification_context=(
                weighted_budget_v2_verification_context
            ),
        )
    except Exception:
        exact = False
        expected = {}
    else:
        exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "adapter_v4_exactly_verified": exact,
        "adapter_v4_status": expected.get("status") if exact else "UNKNOWN",
        "adapter_v4_hash": expected.get("adapter_hash") if exact else None,
        "blockers": [] if exact else ["adapter_v4_exact_rebuild"],
        "current_admission_allowed": False,
        "formal_registry_activation_allowed": False,
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
    "ADAPTER_V3_IMPLEMENTATION_SHA256",
    "WEIGHTED_V2_IMPLEMENTATION_SHA256",
    "ADAPTER_V3_VERIFICATION_CONTEXT_KEYS",
    "WEIGHTED_V2_VERIFICATION_CONTEXT_KEYS",
    "evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v4",
    "verify_strategy_correlation_cluster_portfolio_risk_adapter_v4",
]
