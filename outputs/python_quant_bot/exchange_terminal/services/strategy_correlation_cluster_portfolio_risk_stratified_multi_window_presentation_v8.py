"""Neutral joint presentation of presentation-v7 and anchor adapter-v7.

This candidate projects bounded single-window and multi-window summaries only
after both immutable sources are exactly verified and cross-bound to the same
budget-v3 anchor. It defines no HTTP route, UI mount, current admission, paper,
live, or order authority.
"""

from __future__ import annotations

import copy
import hmac
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7
    as adapter_v7,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7
    as presentation_v7,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_stratified_stability_gate_v2
    as stability_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-"
    "multi-window-presentation-v8"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-presentation-v8-unmounted-lock-1"
)
PRESENTATION_V7_IMPLEMENTATION_SHA256 = (
    "27bfeacbdcbdfb03009c0dec007274e3c143af1045a8bfe7587ca4629ada8b38"
)
ADAPTER_V7_IMPLEMENTATION_SHA256 = (
    "09ecd921823260df4e8fda708f3c276d40fccd22c390b0ef7f920f9d9fc52f3e"
)
STABILITY_GATE_V2_IMPLEMENTATION_SHA256 = (
    "0756cc0d0338170e80bd2b3672ecd6a65542953e2c0dc92a48c05229e0f7902f"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
PRESENTATION_GAPS = (
    "PRESENTATION_V8_CONSUMER_NOT_REGISTERED",
    "HTTP_CANDIDATE_V8_NOT_DEFINED",
    "UI_NOT_MOUNTED",
    "CURRENT_ADMISSION_LOCKED",
)
PRESENTATION_V7_CONTEXT_KEYS = frozenset(
    {
        "budget_v3_document",
        "budget_v3_verification_context",
        "envelope_v6_document",
        "envelope_v6_verification_context",
    }
)
ADAPTER_V7_CONTEXT_KEYS = frozenset(
    {
        "anchor_budget_v3_document",
        "anchor_budget_v3_verification_context",
        "risk_increasing",
        "stability_gate_v2_document",
        "stability_gate_v2_verification_context",
    }
)

_VERIFY_PRESENTATION_V7 = (
    presentation_v7.verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7
)
_VERIFY_ADAPTER_V7 = (
    adapter_v7.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_PRESENTATION_RECEIPT_KEYS = {
    "blockers",
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "presentation_consumer_activation_allowed",
    "presentation_decision",
    "presentation_status",
    "presentation_v7_hash",
    "runtime_gate_activation_allowed",
    "schema_version",
    "status",
    "writer_allowed",
}
_ADAPTER_RECEIPT_KEYS = {
    "adapter_v7_exactly_verified",
    "adapter_v7_hash",
    "adapter_v7_status",
    "blockers",
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "risk_service_invocation_allowed",
    "runtime_gate_activation_allowed",
    "schema_version",
    "status",
    "writer_allowed",
}
_PRESENTATION_KEYS = {
    "authority",
    "axis_order",
    "decision",
    "facts",
    "gaps",
    "local_decision",
    "policy",
    "presentation_v7_hash",
    "risk_summary",
    "schema_version",
    "source",
    "stages",
    "static_fingerprint",
    "status",
}
_ADAPTER_KEYS = {
    "adapter_v7_hash",
    "authority",
    "blockers",
    "checks",
    "component_states",
    "decision",
    "facts",
    "schema_version",
    "source",
    "static_fingerprint",
    "status",
}


def _exact_keys(value: Any, expected: set[str] | frozenset[str]) -> bool:
    return type(value) is dict and set(value) == set(expected)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _same_hash(left: Any, right: Any) -> bool:
    return _is_hash(left) and _is_hash(right) and hmac.compare_digest(left, right)


def _sealed_hash_exact(document: Any, field: str) -> bool:
    if type(document) is not dict or not _is_hash(document.get(field)):
        return False
    body = copy.deepcopy(document)
    supplied = body.pop(field)
    try:
        expected = strict_canonical_hash(body)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(supplied, expected)


def _source_authority_locked(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    if type(authority) is not dict or not authority:
        return False
    for key, value in authority.items():
        if type(key) is not str or type(value) is not bool:
            return False
        if key in {"descriptive_only", "local_decision_only", "presentation_only", "research_only"}:
            if value is not True:
                return False
        elif value is not False:
            return False
    return True


def _authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "formal_registry_activation_allowed": False,
        "http_candidate_creation_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_only": True,
        "research_only": True,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def _presentation_context_valid(context: Any) -> bool:
    return (
        _exact_keys(context, PRESENTATION_V7_CONTEXT_KEYS)
        and all(type(context[key]) is dict for key in PRESENTATION_V7_CONTEXT_KEYS)
    )


def _adapter_context_valid(context: Any) -> bool:
    return (
        _exact_keys(context, ADAPTER_V7_CONTEXT_KEYS)
        and type(context["anchor_budget_v3_document"]) is dict
        and type(context["anchor_budget_v3_verification_context"]) is dict
        and type(context["stability_gate_v2_document"]) is dict
        and type(context["stability_gate_v2_verification_context"]) is dict
        and context["risk_increasing"] is True
    )


def _presentation_receipt_valid(receipt: Any, document: Any) -> bool:
    return (
        _exact_keys(receipt, _PRESENTATION_RECEIPT_KEYS)
        and receipt["schema_version"] == presentation_v7.VERIFICATION_SCHEMA_VERSION
        and receipt["status"] == "PASS"
        and receipt["blockers"] == []
        and receipt["presentation_status"] == "BLOCK"
        and receipt["presentation_decision"] == document.get("decision")
        and receipt["presentation_v7_hash"] == document.get("presentation_v7_hash")
        and receipt["presentation_consumer_activation_allowed"] is False
        and receipt["runtime_gate_activation_allowed"] is False
        and receipt["current_admission_allowed"] is False
        and receipt["writer_allowed"] is False
        and receipt["paper_authorized"] is False
        and receipt["live_order_allowed"] is False
    )


def _adapter_receipt_valid(receipt: Any, document: Any) -> bool:
    return (
        _exact_keys(receipt, _ADAPTER_RECEIPT_KEYS)
        and receipt["schema_version"] == adapter_v7.VERIFICATION_SCHEMA_VERSION
        and receipt["status"] == "PASS"
        and receipt["blockers"] == []
        and receipt["adapter_v7_exactly_verified"] is True
        and receipt["adapter_v7_status"] == document.get("status")
        and receipt["adapter_v7_hash"] == document.get("adapter_v7_hash")
        and receipt["risk_service_invocation_allowed"] is False
        and receipt["runtime_gate_activation_allowed"] is False
        and receipt["current_admission_allowed"] is False
        and receipt["writer_allowed"] is False
        and receipt["paper_authorized"] is False
        and receipt["live_order_allowed"] is False
    )


def _call_presentation_verifier(document: Any, context: Any) -> bool:
    if not _presentation_context_valid(context):
        return False
    try:
        receipt = _VERIFY_PRESENTATION_V7(
            copy.deepcopy(document),
            copy.deepcopy(context["envelope_v6_document"]),
            copy.deepcopy(context["budget_v3_document"]),
            envelope_v6_verification_context=copy.deepcopy(
                context["envelope_v6_verification_context"]
            ),
            budget_v3_verification_context=copy.deepcopy(
                context["budget_v3_verification_context"]
            ),
        )
    except Exception:
        return False
    return _presentation_receipt_valid(receipt, document)


def _call_adapter_verifier(document: Any, context: Any) -> bool:
    if not _adapter_context_valid(context):
        return False
    try:
        receipt = _VERIFY_ADAPTER_V7(
            copy.deepcopy(document),
            copy.deepcopy(context["anchor_budget_v3_document"]),
            copy.deepcopy(context["stability_gate_v2_document"]),
            anchor_budget_v3_verification_context=copy.deepcopy(
                context["anchor_budget_v3_verification_context"]
            ),
            stability_gate_v2_verification_context=copy.deepcopy(
                context["stability_gate_v2_verification_context"]
            ),
            risk_increasing=True,
        )
    except Exception:
        return False
    return _adapter_receipt_valid(receipt, document)


def _presentation_presentable(document: Any) -> bool:
    if (
        not _exact_keys(document, _PRESENTATION_KEYS)
        or document.get("schema_version") != presentation_v7.SCHEMA_VERSION
        or document.get("static_fingerprint") != presentation_v7.STATIC_FINGERPRINT
        or document.get("status") != "BLOCK"
        or document.get("axis_order") != list(AXIS_ORDER)
        or not _sealed_hash_exact(document, "presentation_v7_hash")
        or not _source_authority_locked(document)
    ):
        return False
    source = document["source"]
    local = document["local_decision"]
    facts = document["facts"]
    return (
        type(source) is dict
        and source.get("state") == "EXACT_V6_AND_BUDGET_V3"
        and _is_hash(source.get("budget_v3_hash"))
        and type(local) is dict
        and local.get("joint_status") in {"PASS", "BLOCK"}
        and local.get("portfolio_risk_v6_status") in {"PASS", "BLOCK"}
        and local.get("stratified_budget_status") in {"PASS", "BLOCK"}
        and type(local.get("joint_decision")) is str
        and type(local.get("stratified_budget_decision")) is str
        and type(facts) is dict
        and facts.get("v6_envelope_exactly_verified") is True
        and facts.get("budget_v3_exactly_verified") is True
        and facts.get("joint_local_research_decision_made") is True
        and facts.get("source_documents_embedded") is False
        and facts.get("verification_contexts_embedded") is False
        and type(document["risk_summary"]) is dict
        and type(document["stages"]) is list
        and len(document["stages"]) == len(AXIS_ORDER)
    )


def _adapter_presentable(document: Any) -> bool:
    if (
        not _exact_keys(document, _ADAPTER_KEYS)
        or document.get("schema_version") != adapter_v7.SCHEMA_VERSION
        or document.get("static_fingerprint") != adapter_v7.STATIC_FINGERPRINT
        or document.get("status") not in {"PASS", "BLOCK"}
        or not _sealed_hash_exact(document, "adapter_v7_hash")
        or not _source_authority_locked(document)
    ):
        return False
    source = document["source"]
    states = document["component_states"]
    facts = document["facts"]
    blockers = document["blockers"]
    return (
        type(source) is dict
        and _is_hash(source.get("anchor_budget_v3_hash"))
        and _is_hash(source.get("stability_gate_v2_hash"))
        and _is_hash(source.get("trade_identity_hash"))
        and type(source.get("anchor_window_id")) is str
        and bool(source["anchor_window_id"])
        and source.get("source_documents_embedded") is False
        and source.get("verification_contexts_embedded") is False
        and type(states) is dict
        and states.get("anchor_budget_v3_status") in {"PASS", "BLOCK"}
        and states.get("stability_gate_v2_status") in {"PASS", "BLOCK"}
        and type(states.get("anchor_budget_v3_decision")) is str
        and type(states.get("stability_gate_v2_decision")) is str
        and type(facts) is dict
        and facts.get("anchor_budget_and_context_cross_bound") is True
        and facts.get("anchor_budget_v3_exactly_verified") is True
        and facts.get("stability_gate_v2_exactly_verified") is True
        and facts.get("trade_identity_cross_bound") is True
        and facts.get("joint_local_research_decision_made") is True
        and facts.get("source_documents_embedded") is False
        and facts.get("verification_contexts_embedded") is False
        and type(blockers) is list
        and (
            (document["status"] == "PASS" and blockers == [])
            or (document["status"] == "BLOCK" and bool(blockers))
        )
    )


def _gate_summary_presentable(document: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != stability_v2.GATE_SCHEMA_VERSION
        or document.get("static_fingerprint") != stability_v2.STATIC_FINGERPRINT
        or document.get("status") not in {"PASS", "BLOCK"}
        or not _sealed_hash_exact(document, "stability_gate_v2_hash")
        or not _source_authority_locked(document)
    ):
        return False
    summary = document.get("summary")
    source = document.get("source")
    return (
        type(summary) is dict
        and type(source) is dict
        and _is_hash(source.get("trade_identity_hash"))
        and type(summary.get("registered_window_count")) is int
        and summary["registered_window_count"] == stability_v2.REQUIRED_WINDOW_COUNT
        and type(summary.get("verified_window_count")) is int
        and summary["verified_window_count"] == stability_v2.REQUIRED_WINDOW_COUNT
        and type(summary.get("any_registered_window_blocked")) is bool
        and type(summary.get("cluster_partition_stable")) is bool
        and type(summary.get("strata_topology_stable")) is bool
    )


def _cross_bindings(
    presentation_document: Any,
    adapter_document: Any,
    presentation_context: Any,
    adapter_context: Any,
) -> dict[str, bool]:
    presentation_budget = (
        presentation_context.get("budget_v3_document")
        if type(presentation_context) is dict
        else None
    )
    presentation_budget_context = (
        presentation_context.get("budget_v3_verification_context")
        if type(presentation_context) is dict
        else None
    )
    adapter_budget = (
        adapter_context.get("anchor_budget_v3_document")
        if type(adapter_context) is dict
        else None
    )
    adapter_budget_context = (
        adapter_context.get("anchor_budget_v3_verification_context")
        if type(adapter_context) is dict
        else None
    )
    presentation_source = (
        presentation_document.get("source")
        if type(presentation_document) is dict
        else None
    )
    presentation_local = (
        presentation_document.get("local_decision")
        if type(presentation_document) is dict
        else None
    )
    adapter_source = (
        adapter_document.get("source") if type(adapter_document) is dict else None
    )
    adapter_states = (
        adapter_document.get("component_states")
        if type(adapter_document) is dict
        else None
    )
    gate_document = (
        adapter_context.get("stability_gate_v2_document")
        if type(adapter_context) is dict
        else None
    )
    gate_source = gate_document.get("source") if type(gate_document) is dict else None
    return {
        "anchor_budget_document_exact_identity": (
            type(presentation_budget) is dict
            and type(adapter_budget) is dict
            and strict_json_contract_equal(presentation_budget, adapter_budget)
        ),
        "anchor_budget_context_exact_identity": (
            type(presentation_budget_context) is dict
            and type(adapter_budget_context) is dict
            and strict_json_contract_equal(
                presentation_budget_context, adapter_budget_context
            )
        ),
        "anchor_budget_hash_identity": (
            type(presentation_source) is dict
            and type(adapter_source) is dict
            and _same_hash(
                presentation_source.get("budget_v3_hash"),
                adapter_source.get("anchor_budget_v3_hash"),
            )
        ),
        "anchor_budget_status_identity": (
            type(presentation_local) is dict
            and type(adapter_states) is dict
            and presentation_local.get("stratified_budget_status")
            == adapter_states.get("anchor_budget_v3_status")
        ),
        "anchor_budget_decision_identity": (
            type(presentation_local) is dict
            and type(adapter_states) is dict
            and presentation_local.get("stratified_budget_decision")
            == adapter_states.get("anchor_budget_v3_decision")
        ),
        "stability_gate_hash_identity": (
            type(adapter_source) is dict
            and type(gate_document) is dict
            and _same_hash(
                adapter_source.get("stability_gate_v2_hash"),
                gate_document.get("stability_gate_v2_hash"),
            )
        ),
        "trade_identity_hash_identity": (
            type(adapter_source) is dict
            and type(gate_source) is dict
            and _same_hash(
                adapter_source.get("trade_identity_hash"),
                gate_source.get("trade_identity_hash"),
            )
        ),
    }


def _unknown() -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "axis_order": list(AXIS_ORDER),
            "decision": "UNKNOWN_SOURCE_PROJECTED_UNMOUNTED",
            "facts": {
                "adapter_v7_exactly_verified": False,
                "anchor_budget_cross_bound": False,
                "browser_review_performed": False,
                "http_candidate_registered": False,
                "multi_window_summary_projected": False,
                "positions_embedded": False,
                "presentation_v7_exactly_verified": False,
                "profitability_proven": False,
                "runtime_assets_accessed": False,
                "runtime_consumer_bound": False,
                "source_documents_embedded": False,
                "ui_mounted": False,
                "verification_contexts_embedded": False,
            },
            "gaps": {
                "local_blocker_count": 0,
                "multi_window_blocker_count": 0,
                "presentation_blocker_count": len(PRESENTATION_GAPS),
                "presentation_blockers": list(PRESENTATION_GAPS),
            },
            "local_decision": {
                "adapter_v7_decision": "UNKNOWN",
                "adapter_v7_status": "UNKNOWN",
                "anchor_budget_v3_decision": "UNKNOWN",
                "anchor_budget_v3_status": "UNKNOWN",
                "joint_decision": "UNKNOWN",
                "joint_status": "UNKNOWN",
                "presentation_v7_joint_decision": "UNKNOWN",
                "presentation_v7_joint_status": "UNKNOWN",
                "stability_gate_v2_decision": "UNKNOWN",
                "stability_gate_v2_status": "UNKNOWN",
            },
            "multi_window_summary": {
                "anchor_window_id": None,
                "any_registered_window_blocked": None,
                "cluster_partition_stable": None,
                "minimum_conservative_weighted_effective_strata_count": None,
                "registered_window_count": None,
                "strata_topology_stable": None,
                "verified_window_count": None,
                "worst_window_maximum_active_stratum_gross_pct": None,
            },
            "policy": {
                "local_block_preserved": True,
                "multi_window_block_overrides_anchor_clear": True,
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
                "adapter_v7_context_hash": None,
                "adapter_v7_hash": None,
                "adapter_v7_implementation_sha256": ADAPTER_V7_IMPLEMENTATION_SHA256,
                "presentation_v7_context_hash": None,
                "presentation_v7_hash": None,
                "presentation_v7_implementation_sha256": PRESENTATION_V7_IMPLEMENTATION_SHA256,
                "stability_gate_v2_hash": None,
                "stability_gate_v2_implementation_sha256": STABILITY_GATE_V2_IMPLEMENTATION_SHA256,
                "state": "UNKNOWN",
                "strict_canonical_implementation_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
                "trade_identity_hash": None,
            },
            "stages": [
                {"axis": "SOURCE", "detail": "SOURCE_CONTRACT_UNKNOWN", "state": "UNKNOWN"},
                {"axis": "GAP", "detail": "SOURCE_CONTRACT_UNKNOWN", "state": "OPEN"},
                {"axis": "MATURITY", "detail": "UNMOUNTED_PRESENTATION_V8_CANDIDATE", "state": "CANDIDATE"},
                {"axis": "PERMISSION", "detail": "NO_EXECUTION_OR_ACTIVATION_PERMISSION", "state": "NONE"},
            ],
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "BLOCK",
        },
        "presentation_v8_hash",
    )


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8(
    presentation_v7_document: Any,
    adapter_v7_document: Any,
    *,
    presentation_v7_verification_context: Any,
    adapter_v7_verification_context: Any,
) -> dict[str, Any]:
    checks = {
        "presentation_v7_context_exact": _presentation_context_valid(
            presentation_v7_verification_context
        ),
        "adapter_v7_context_exact": _adapter_context_valid(
            adapter_v7_verification_context
        ),
        "presentation_v7_exactly_verified": _call_presentation_verifier(
            presentation_v7_document, presentation_v7_verification_context
        ),
        "adapter_v7_exactly_verified": _call_adapter_verifier(
            adapter_v7_document, adapter_v7_verification_context
        ),
        "presentation_v7_presentable": _presentation_presentable(
            presentation_v7_document
        ),
        "adapter_v7_presentable": _adapter_presentable(adapter_v7_document),
        "stability_gate_v2_summary_presentable": _gate_summary_presentable(
            adapter_v7_verification_context.get("stability_gate_v2_document")
            if type(adapter_v7_verification_context) is dict
            else None
        ),
    }
    checks.update(
        _cross_bindings(
            presentation_v7_document,
            adapter_v7_document,
            presentation_v7_verification_context,
            adapter_v7_verification_context,
        )
    )
    if not checks or not all(checks.values()):
        return _unknown()

    presentation_local = presentation_v7_document["local_decision"]
    adapter_states = adapter_v7_document["component_states"]
    adapter_status = adapter_v7_document["status"]
    presentation_status = presentation_local["joint_status"]
    if adapter_status == "BLOCK":
        joint_status = "BLOCK"
        joint_decision = "BLOCK_STRATIFIED_MULTI_WINDOW_ADAPTER_V7"
    elif presentation_status == "BLOCK":
        joint_status = "BLOCK"
        joint_decision = "BLOCK_PRESENTATION_V7_LOCAL_COMPONENT"
    else:
        joint_status = "PASS"
        joint_decision = "PASS_STRATIFIED_MULTI_WINDOW_LOCAL_RESEARCH_COMPONENTS"
    local_blockers = copy.deepcopy(adapter_v7_document["blockers"])
    if presentation_status == "BLOCK":
        local_blockers.append("presentation_v7_local_component_block")
    local_blockers = sorted(set(local_blockers))
    gap_state = "OPEN" if joint_status == "BLOCK" else "CLEAR_WITH_GOVERNANCE_GAPS"
    gap_detail = (
        "LOCAL_RESEARCH_BLOCK_PRESENT"
        if joint_status == "BLOCK"
        else "LOCAL_RESEARCH_GATES_CLEAR_GOVERNANCE_GAPS_REMAIN"
    )
    gate_document = adapter_v7_verification_context["stability_gate_v2_document"]
    gate_summary = gate_document["summary"]
    adapter_source = adapter_v7_document["source"]
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "axis_order": list(AXIS_ORDER),
            "decision": (
                "EXACT_STRATIFIED_MULTI_WINDOW_LOCAL_BLOCK_PROJECTED_UNMOUNTED"
                if joint_status == "BLOCK"
                else "EXACT_STRATIFIED_MULTI_WINDOW_LOCAL_CLEAR_PROJECTED_UNMOUNTED"
            ),
            "facts": {
                "adapter_v7_exactly_verified": True,
                "anchor_budget_cross_bound": True,
                "browser_review_performed": False,
                "http_candidate_registered": False,
                "multi_window_summary_projected": True,
                "positions_embedded": False,
                "presentation_v7_exactly_verified": True,
                "profitability_proven": False,
                "runtime_assets_accessed": False,
                "runtime_consumer_bound": False,
                "source_documents_embedded": False,
                "ui_mounted": False,
                "verification_contexts_embedded": False,
            },
            "gaps": {
                "local_blocker_count": len(local_blockers),
                "multi_window_blocker_count": len(adapter_v7_document["blockers"]),
                "presentation_blocker_count": len(PRESENTATION_GAPS),
                "presentation_blockers": list(PRESENTATION_GAPS),
            },
            "local_decision": {
                "adapter_v7_decision": adapter_v7_document["decision"],
                "adapter_v7_status": adapter_status,
                "anchor_budget_v3_decision": adapter_states[
                    "anchor_budget_v3_decision"
                ],
                "anchor_budget_v3_status": adapter_states[
                    "anchor_budget_v3_status"
                ],
                "joint_decision": joint_decision,
                "joint_status": joint_status,
                "presentation_v7_joint_decision": presentation_local[
                    "joint_decision"
                ],
                "presentation_v7_joint_status": presentation_status,
                "stability_gate_v2_decision": adapter_states[
                    "stability_gate_v2_decision"
                ],
                "stability_gate_v2_status": adapter_states[
                    "stability_gate_v2_status"
                ],
            },
            "multi_window_summary": {
                "anchor_window_id": adapter_source["anchor_window_id"],
                "any_registered_window_blocked": gate_summary[
                    "any_registered_window_blocked"
                ],
                "cluster_partition_stable": gate_summary[
                    "cluster_partition_stable"
                ],
                "minimum_conservative_weighted_effective_strata_count": gate_summary[
                    "minimum_conservative_weighted_effective_strata_count"
                ],
                "registered_window_count": gate_summary["registered_window_count"],
                "strata_topology_stable": gate_summary["strata_topology_stable"],
                "verified_window_count": gate_summary["verified_window_count"],
                "worst_window_maximum_active_stratum_gross_pct": gate_summary[
                    "worst_window_maximum_active_stratum_gross_pct"
                ],
            },
            "policy": {
                "local_block_preserved": True,
                "multi_window_block_overrides_anchor_clear": True,
                "risk_reduction_is_not_execution_authority": True,
            },
            "risk_summary": copy.deepcopy(presentation_v7_document["risk_summary"]),
            "schema_version": SCHEMA_VERSION,
            "source": {
                "adapter_v7_context_hash": strict_canonical_hash(
                    adapter_v7_verification_context
                ),
                "adapter_v7_hash": adapter_v7_document["adapter_v7_hash"],
                "adapter_v7_implementation_sha256": ADAPTER_V7_IMPLEMENTATION_SHA256,
                "presentation_v7_context_hash": strict_canonical_hash(
                    presentation_v7_verification_context
                ),
                "presentation_v7_hash": presentation_v7_document[
                    "presentation_v7_hash"
                ],
                "presentation_v7_implementation_sha256": PRESENTATION_V7_IMPLEMENTATION_SHA256,
                "stability_gate_v2_hash": gate_document["stability_gate_v2_hash"],
                "stability_gate_v2_implementation_sha256": STABILITY_GATE_V2_IMPLEMENTATION_SHA256,
                "state": "EXACT_PRESENTATION_V7_AND_ADAPTER_V7",
                "strict_canonical_implementation_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
                "trade_identity_hash": adapter_source["trade_identity_hash"],
            },
            "stages": [
                {"axis": "SOURCE", "detail": "EXACT_PRESENTATION_V7_AND_ADAPTER_V7", "state": "KNOWN"},
                {"axis": "GAP", "detail": gap_detail, "state": gap_state},
                {"axis": "MATURITY", "detail": "UNMOUNTED_PRESENTATION_V8_CANDIDATE", "state": "CANDIDATE"},
                {"axis": "PERMISSION", "detail": "NO_EXECUTION_OR_ACTIVATION_PERMISSION", "state": "NONE"},
            ],
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "BLOCK",
        },
        "presentation_v8_hash",
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8(
    document: Any,
    presentation_v7_document: Any,
    adapter_v7_document: Any,
    *,
    presentation_v7_verification_context: Any,
    adapter_v7_verification_context: Any,
) -> dict[str, Any]:
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8(
            presentation_v7_document,
            adapter_v7_document,
            presentation_v7_verification_context=presentation_v7_verification_context,
            adapter_v7_verification_context=adapter_v7_verification_context,
        )
        exact = (
            type(document) is dict
            and strict_json_contract_equal(document, expected)
            and document.get("schema_version") == SCHEMA_VERSION
            and document.get("status") == "BLOCK"
            and _sealed_hash_exact(document, "presentation_v8_hash")
            and _source_authority_locked(document)
        )
    except Exception:
        exact = False
    return {
        "blockers": [] if exact else ["stratified_multi_window_presentation_v8_exact_rebuild"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_v8_exactly_verified": exact,
        "presentation_v8_hash": (
            document.get("presentation_v8_hash")
            if exact and type(document) is dict
            else None
        ),
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }


__all__ = [
    "ADAPTER_V7_CONTEXT_KEYS",
    "ADAPTER_V7_IMPLEMENTATION_SHA256",
    "AXIS_ORDER",
    "PRESENTATION_GAPS",
    "PRESENTATION_V7_CONTEXT_KEYS",
    "PRESENTATION_V7_IMPLEMENTATION_SHA256",
    "SCHEMA_VERSION",
    "STABILITY_GATE_V2_IMPLEMENTATION_SHA256",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8",
]
