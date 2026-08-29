"""Joint adapter for weighted portfolio risk and multi-window stability.

Adapter-v5 keeps adapter-v4 and the stability gate immutable.  It requires one
registered stability window to be the exact weighted-budget source consumed by
adapter-v4, cross-binds the canonical trade identity, and preserves any source
block.  It remains a local, summary-only research decision with no runtime or
trading authority.
"""

from __future__ import annotations

import copy
import hmac
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_stability_gate_v1 as stability_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v4 as adapter_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-adapter-v5"
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-portfolio-risk-adapter-v5-multi-window-joint-lock-1"
)
ADAPTER_V4_IMPLEMENTATION_SHA256 = (
    "d57c69f88746ac168334e37545c465f22d2d9e5453d3a814c7b64b57604c9202"
)
STABILITY_GATE_V1_IMPLEMENTATION_SHA256 = (
    "64aeac49b3ea432ce8307c66204056741e83ef2111d809401c2c98d294bf8c8d"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

ADAPTER_V4_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "adapter_v3_document",
        "weighted_budget_v2_document",
        "adapter_v3_verification_context",
        "weighted_budget_v2_verification_context",
    }
)
STABILITY_GATE_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "preregistration",
        "window_budget_documents",
        "window_verification_contexts",
        "expected_preregistration_hash",
        "anchor_window_id",
    }
)

_VERIFY_ADAPTER_V4 = (
    adapter_v4.verify_strategy_correlation_cluster_portfolio_risk_adapter_v4
)
_VERIFY_STABILITY_GATE = (
    stability_v1.verify_strategy_correlation_cluster_multi_window_stability_gate_v1
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _same_hash(left: Any, right: Any) -> bool:
    return _is_hash(left) and _is_hash(right) and hmac.compare_digest(left, right)


def _sealed_hash_exact(document: Any, field: str) -> bool:
    if type(document) is not dict or not _is_hash(document.get(field)):
        return False
    unhashed = copy.deepcopy(document)
    supplied = unhashed.pop(field)
    try:
        expected = strict_canonical_hash(unhashed)
    except ValueError:
        return False
    return hmac.compare_digest(supplied, expected)


def _adapter_authority_locked(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    if type(authority) is not dict or not authority:
        return False
    for key, value in authority.items():
        if type(key) is not str or type(value) is not bool:
            return False
        if key in {"local_decision_only", "research_only"}:
            if value is not True:
                return False
        elif value is not False:
            return False
    return True


def _descriptive_authority_locked(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    return (
        type(authority) is dict
        and bool(authority)
        and authority.get("descriptive_only") is True
        and all(type(value) is bool for value in authority.values())
        and all(
            value is False
            for key, value in authority.items()
            if key != "descriptive_only"
        )
    )


def _authority() -> dict[str, bool]:
    return {
        "local_decision_only": True,
        "research_only": True,
        "writer_allowed": False,
        "risk_service_invocation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "formal_registry_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _adapter_context_valid(context: Any) -> bool:
    return (
        type(context) is dict
        and frozenset(context) == ADAPTER_V4_VERIFICATION_CONTEXT_KEYS
        and all(
            type(context[key]) is dict
            for key in ADAPTER_V4_VERIFICATION_CONTEXT_KEYS
        )
    )


def _stability_context_valid(context: Any) -> bool:
    if (
        type(context) is not dict
        or frozenset(context) != STABILITY_GATE_VERIFICATION_CONTEXT_KEYS
        or type(context.get("anchor_window_id")) is not str
        or not context["anchor_window_id"]
        or not _is_hash(context.get("expected_preregistration_hash"))
    ):
        return False
    return all(
        type(context[key]) is dict
        for key in {
            "preregistration",
            "window_budget_documents",
            "window_verification_contexts",
        }
    )


def _adapter_receipt_passed(receipt: Any, document: Any) -> bool:
    if (
        type(receipt) is not dict
        or type(document) is not dict
        or receipt.get("status") != "PASS"
        or receipt.get("adapter_v4_exactly_verified") is not True
        or receipt.get("adapter_v4_status") != document.get("status")
        or not _same_hash(receipt.get("adapter_v4_hash"), document.get("adapter_hash"))
        or receipt.get("blockers") != []
    ):
        return False
    locked = {
        "writer_allowed",
        "runtime_gate_activation_allowed",
        "shadow_consumer_activation_allowed",
        "formal_registry_activation_allowed",
        "current_admission_allowed",
        "paper_authorized",
        "live_order_allowed",
    }
    return all(receipt.get(key) is False for key in locked)


def _stability_receipt_passed(receipt: Any, document: Any) -> bool:
    return (
        type(receipt) is dict
        and type(document) is dict
        and receipt.get("status") == "PASS"
        and receipt.get("stability_gate_exactly_verified") is True
        and receipt.get("stability_gate_decision") == document.get("decision")
        and receipt.get("blockers") == []
        and receipt.get("runtime_gate_activation_allowed") is False
        and receipt.get("current_admission_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("live_order_allowed") is False
    )


def _call_adapter_verifier(document: Any, context: Any) -> bool:
    if not _adapter_context_valid(context):
        return False
    try:
        receipt = _VERIFY_ADAPTER_V4(
            copy.deepcopy(document),
            copy.deepcopy(context["adapter_v3_document"]),
            copy.deepcopy(context["weighted_budget_v2_document"]),
            adapter_v3_verification_context=copy.deepcopy(
                context["adapter_v3_verification_context"]
            ),
            weighted_budget_v2_verification_context=copy.deepcopy(
                context["weighted_budget_v2_verification_context"]
            ),
        )
    except Exception:
        return False
    return _adapter_receipt_passed(receipt, document)


def _call_stability_verifier(document: Any, context: Any) -> bool:
    if not _stability_context_valid(context):
        return False
    try:
        receipt = _VERIFY_STABILITY_GATE(
            copy.deepcopy(document),
            copy.deepcopy(context["preregistration"]),
            copy.deepcopy(context["window_budget_documents"]),
            window_verification_contexts=copy.deepcopy(
                context["window_verification_contexts"]
            ),
            expected_preregistration_hash=context[
                "expected_preregistration_hash"
            ],
        )
    except Exception:
        return False
    return _stability_receipt_passed(receipt, document)


def _adapter_presentable(document: Any, context: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != adapter_v4.SCHEMA_VERSION
        or document.get("static_fingerprint") != adapter_v4.STATIC_FINGERPRINT
        or document.get("status") not in {"PASS", "BLOCK"}
        or not _sealed_hash_exact(document, "adapter_hash")
        or not _adapter_authority_locked(document)
    ):
        return False
    source = document.get("source")
    facts = document.get("facts")
    blockers = document.get("blockers")
    weighted_document = (
        context.get("weighted_budget_v2_document")
        if type(context) is dict
        else None
    )
    status_consistent = (
        document["status"] == "PASS" and blockers == []
    ) or (
        document["status"] == "BLOCK"
        and type(blockers) is list
        and bool(blockers)
    )
    return (
        status_consistent
        and type(source) is dict
        and type(facts) is dict
        and type(weighted_document) is dict
        and _same_hash(
            source.get("weighted_budget_v2_hash"),
            weighted_document.get("budget_v2_hash"),
        )
        and facts.get("temporal_and_session_freshness_preserved") is True
        and facts.get("weighted_diversification_consumed") is True
        and facts.get("joint_local_research_decision_made") is True
        and facts.get("source_documents_embedded") is False
        and facts.get("component_documents_embedded") is False
        and facts.get("correlation_matrices_embedded") is False
        and facts.get("positions_embedded") is False
        and facts.get("runtime_assets_accessed") is False
        and facts.get("runtime_consumer_bound") is False
        and facts.get("profitability_proven") is False
    )


def _stability_presentable(document: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != stability_v1.GATE_SCHEMA_VERSION
        or document.get("static_fingerprint") != stability_v1.STATIC_FINGERPRINT
        or document.get("status") not in {"PASS", "BLOCK"}
        or not _sealed_hash_exact(document, "stability_gate_hash")
        or not _descriptive_authority_locked(document)
    ):
        return False
    source = document.get("source")
    facts = document.get("facts")
    summaries = document.get("window_summaries")
    blockers = document.get("blockers")
    status_consistent = (
        document["status"] == "PASS" and blockers == []
    ) or (
        document["status"] == "BLOCK"
        and type(blockers) is list
        and bool(blockers)
    )
    return (
        status_consistent
        and type(source) is dict
        and _is_hash(source.get("preregistration_hash"))
        and _is_hash(source.get("trade_identity_hash"))
        and source.get("source_documents_embedded") is False
        and source.get("verification_contexts_embedded") is False
        and type(facts) is dict
        and facts.get("preregistration_exactly_verified") is True
        and facts.get("all_registered_windows_exactly_verified") is True
        and facts.get("trade_identity_consistent_across_windows") is True
        and facts.get("matrix_hashes_unique_across_windows") is True
        and facts.get("single_window_independence_assumption_used") is False
        and facts.get("correlation_matrices_embedded") is False
        and facts.get("complete_link_audits_embedded") is False
        and facts.get("positions_embedded") is False
        and facts.get("runtime_assets_accessed") is False
        and facts.get("runtime_gate_integrated") is False
        and facts.get("profitability_proven") is False
        and type(summaries) is list
        and len(summaries) == stability_v1.REQUIRED_WINDOW_COUNT
    )


def _trade_identity_hash(weighted_context: Any) -> str | None:
    if type(weighted_context) is not dict:
        return None
    matrix = weighted_context.get("correlation_matrix")
    preregistration = weighted_context.get("preregistration")
    audit = weighted_context.get("complete_link_audit")
    if not all(type(value) is dict for value in (matrix, preregistration, audit)):
        return None
    try:
        return strict_canonical_hash(
            {
                "equity": copy.deepcopy(weighted_context.get("equity")),
                "positions": copy.deepcopy(weighted_context.get("positions")),
                "proposed_symbol": weighted_context.get("proposed_symbol"),
                "proposed_notional": copy.deepcopy(
                    weighted_context.get("proposed_notional")
                ),
                "proposed_direction": weighted_context.get("proposed_direction"),
                "max_cluster_gross_pct": copy.deepcopy(
                    weighted_context.get("max_cluster_gross_pct")
                ),
                "risk_increasing": weighted_context.get("risk_increasing"),
                "matrix_symbols": copy.deepcopy(matrix.get("symbols")),
                "preregistration_symbols": copy.deepcopy(
                    preregistration.get("symbols")
                ),
                "return_series": matrix.get("return_series"),
                "absolute_pearson_threshold": audit.get(
                    "absolute_pearson_threshold"
                ),
            }
        )
    except ValueError:
        return None


def _cross_bindings(
    adapter_document: Any,
    stability_document: Any,
    adapter_context: Any,
    stability_context: Any,
) -> dict[str, bool]:
    anchor = (
        stability_context.get("anchor_window_id")
        if type(stability_context) is dict
        else None
    )
    window_documents = (
        stability_context.get("window_budget_documents")
        if type(stability_context) is dict
        else None
    )
    window_contexts = (
        stability_context.get("window_verification_contexts")
        if type(stability_context) is dict
        else None
    )
    summaries = (
        stability_document.get("window_summaries")
        if type(stability_document) is dict
        else None
    )
    anchor_summary = None
    if type(summaries) is list:
        matches = [
            item
            for item in summaries
            if type(item) is dict and item.get("window_id") == anchor
        ]
        if len(matches) == 1:
            anchor_summary = matches[0]
    adapter_weighted_document = (
        adapter_context.get("weighted_budget_v2_document")
        if type(adapter_context) is dict
        else None
    )
    adapter_weighted_context = (
        adapter_context.get("weighted_budget_v2_verification_context")
        if type(adapter_context) is dict
        else None
    )
    anchor_document = (
        window_documents.get(anchor)
        if type(window_documents) is dict and type(anchor) is str
        else None
    )
    anchor_context = (
        window_contexts.get(anchor)
        if type(window_contexts) is dict and type(anchor) is str
        else None
    )
    adapter_source = (
        adapter_document.get("source") if type(adapter_document) is dict else None
    )
    stability_source = (
        stability_document.get("source")
        if type(stability_document) is dict
        else None
    )
    derived_identity = _trade_identity_hash(adapter_weighted_context)
    return {
        "anchor_window_present_once": type(anchor_summary) is dict,
        "anchor_weighted_document_exact_identity": (
            type(adapter_weighted_document) is dict
            and type(anchor_document) is dict
            and strict_json_contract_equal(
                adapter_weighted_document, anchor_document
            )
        ),
        "anchor_weighted_context_exact_identity": (
            type(adapter_weighted_context) is dict
            and type(anchor_context) is dict
            and strict_json_contract_equal(adapter_weighted_context, anchor_context)
        ),
        "adapter_anchor_budget_hash_identity": (
            type(adapter_source) is dict
            and type(anchor_summary) is dict
            and _same_hash(
                adapter_source.get("weighted_budget_v2_hash"),
                anchor_summary.get("budget_v2_hash"),
            )
        ),
        "trade_identity_hash_identity": (
            type(stability_source) is dict
            and _same_hash(
                derived_identity, stability_source.get("trade_identity_hash")
            )
        ),
        "preregistration_hash_identity": (
            type(stability_source) is dict
            and type(stability_context) is dict
            and _same_hash(
                stability_source.get("preregistration_hash"),
                stability_context.get("expected_preregistration_hash"),
            )
        ),
    }


def _checks(
    adapter_v4_document: Any,
    stability_gate_document: Any,
    *,
    adapter_v4_verification_context: Any,
    stability_gate_verification_context: Any,
) -> dict[str, bool]:
    bindings = _cross_bindings(
        adapter_v4_document,
        stability_gate_document,
        adapter_v4_verification_context,
        stability_gate_verification_context,
    )
    return {
        "adapter_v4_verification_context_exact": _adapter_context_valid(
            adapter_v4_verification_context
        ),
        "stability_gate_verification_context_exact": _stability_context_valid(
            stability_gate_verification_context
        ),
        "adapter_v4_exactly_verified": _call_adapter_verifier(
            adapter_v4_document, adapter_v4_verification_context
        ),
        "stability_gate_exactly_verified": _call_stability_verifier(
            stability_gate_document, stability_gate_verification_context
        ),
        "adapter_v4_presentable": _adapter_presentable(
            adapter_v4_document, adapter_v4_verification_context
        ),
        "stability_gate_presentable": _stability_presentable(
            stability_gate_document
        ),
        **bindings,
    }


def evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v5(
    adapter_v4_document: Any,
    stability_gate_document: Any,
    *,
    adapter_v4_verification_context: Any,
    stability_gate_verification_context: Any,
) -> dict[str, Any]:
    """Build the exact joint local decision from two immutable components."""

    checks = _checks(
        adapter_v4_document,
        stability_gate_document,
        adapter_v4_verification_context=adapter_v4_verification_context,
        stability_gate_verification_context=stability_gate_verification_context,
    )
    known = all(checks.values())
    adapter_status = (
        adapter_v4_document.get("status")
        if known and type(adapter_v4_document) is dict
        else "UNKNOWN"
    )
    stability_status = (
        stability_gate_document.get("status")
        if known and type(stability_gate_document) is dict
        else "UNKNOWN"
    )
    if not known:
        status = "UNKNOWN"
        decision = "BLOCK_JOINT_SOURCE_UNVERIFIED"
        blockers = ["adapter_v5_exact_joint_source_closure"]
    elif adapter_status == "BLOCK":
        status = "BLOCK"
        decision = "BLOCK_ADAPTER_V4_COMPONENT"
        blockers = ["adapter_v4_component_block"]
    elif stability_status == "BLOCK":
        status = "BLOCK"
        decision = "BLOCK_MULTI_WINDOW_STABILITY_COMPONENT"
        blockers = ["multi_window_stability_component_block"]
    else:
        status = "PASS"
        decision = "PASS_WEIGHTED_AND_MULTI_WINDOW_STABLE_RESEARCH_GATE"
        blockers = []
    anchor = (
        stability_gate_verification_context.get("anchor_window_id")
        if known
        else None
    )
    stability_source = (
        stability_gate_document.get("source")
        if known and type(stability_gate_document) is dict
        else None
    )
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": decision,
        "source": {
            "adapter_v4_schema_version": adapter_v4.SCHEMA_VERSION,
            "adapter_v4_static_fingerprint": adapter_v4.STATIC_FINGERPRINT,
            "adapter_v4_implementation_sha256": ADAPTER_V4_IMPLEMENTATION_SHA256,
            "adapter_v4_hash": (
                adapter_v4_document.get("adapter_hash")
                if known and type(adapter_v4_document) is dict
                else None
            ),
            "stability_gate_schema_version": stability_v1.GATE_SCHEMA_VERSION,
            "stability_gate_static_fingerprint": stability_v1.STATIC_FINGERPRINT,
            "stability_gate_implementation_sha256": (
                STABILITY_GATE_V1_IMPLEMENTATION_SHA256
            ),
            "stability_gate_hash": (
                stability_gate_document.get("stability_gate_hash")
                if known and type(stability_gate_document) is dict
                else None
            ),
            "anchor_window_id": anchor,
            "trade_identity_hash": (
                stability_source.get("trade_identity_hash")
                if type(stability_source) is dict
                else None
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "source_documents_embedded": False,
            "verification_contexts_embedded": False,
        },
        "component_states": {
            "adapter_v4_status": adapter_status,
            "adapter_v4_decision": (
                adapter_v4_document.get("decision")
                if known and type(adapter_v4_document) is dict
                else "UNKNOWN"
            ),
            "stability_gate_status": stability_status,
            "stability_gate_decision": (
                stability_gate_document.get("decision")
                if known and type(stability_gate_document) is dict
                else "UNKNOWN"
            ),
        },
        "checks": checks,
        "facts": {
            "adapter_v4_exactly_verified": known,
            "multi_window_stability_gate_exactly_verified": known,
            "anchor_window_budget_and_context_bound": known,
            "trade_identity_cross_bound": known,
            "single_window_pass_can_be_overridden_by_multi_window_block": True,
            "joint_local_research_decision_made": known,
            "source_documents_embedded": False,
            "verification_contexts_embedded": False,
            "correlation_matrices_embedded": False,
            "positions_embedded": False,
            "runtime_assets_accessed": False,
            "risk_service_invoked": False,
            "runtime_consumer_bound": False,
            "profitability_proven": False,
        },
        "blockers": blockers,
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "adapter_v5_hash")


def verify_strategy_correlation_cluster_portfolio_risk_adapter_v5(
    document: Any,
    adapter_v4_document: Any,
    stability_gate_document: Any,
    *,
    adapter_v4_verification_context: Any,
    stability_gate_verification_context: Any,
) -> dict[str, Any]:
    """Rebuild exactly and return a non-authorizing verification receipt."""

    try:
        rebuilt = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v5(
            adapter_v4_document,
            stability_gate_document,
            adapter_v4_verification_context=adapter_v4_verification_context,
            stability_gate_verification_context=(
                stability_gate_verification_context
            ),
        )
        exact = (
            type(document) is dict
            and strict_json_contract_equal(document, rebuilt)
            and document.get("schema_version") == SCHEMA_VERSION
            and document.get("status") in {"PASS", "BLOCK"}
            and _sealed_hash_exact(document, "adapter_v5_hash")
            and _adapter_authority_locked(document)
        )
    except Exception:
        exact = False
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "adapter_v5_exactly_verified": exact,
        "adapter_v5_status": (
            document.get("status") if exact and type(document) is dict else "UNKNOWN"
        ),
        "adapter_v5_hash": (
            document.get("adapter_v5_hash") if exact and type(document) is dict else None
        ),
        "blockers": [] if exact else ["adapter_v5_exact_rebuild"],
        "writer_allowed": False,
        "risk_service_invocation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "ADAPTER_V4_IMPLEMENTATION_SHA256",
    "ADAPTER_V4_VERIFICATION_CONTEXT_KEYS",
    "SCHEMA_VERSION",
    "STABILITY_GATE_V1_IMPLEMENTATION_SHA256",
    "STABILITY_GATE_VERIFICATION_CONTEXT_KEYS",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "VERIFICATION_SCHEMA_VERSION",
    "evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v5",
    "verify_strategy_correlation_cluster_portfolio_risk_adapter_v5",
]
