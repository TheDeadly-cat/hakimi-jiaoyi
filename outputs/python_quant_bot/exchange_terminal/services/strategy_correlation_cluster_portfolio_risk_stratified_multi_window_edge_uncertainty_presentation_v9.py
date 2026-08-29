"""Unmounted presentation-v9 joining presentation-v8 with adapter-v8.

The presentation exact-verifies both sources, cross-binds their shared
adapter-v7, stability-gate-v2, trade identity, and window counts, then projects
only bounded anchor, multi-window, and edge-uncertainty summaries. It defines no
HTTP route, UI mount, current selector, paper path, or live path.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_adapter_v8
    as adapter_v8,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8
    as presentation_v8,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "edge-uncertainty-presentation-v9"
)
VERIFICATION_SCHEMA_VERSION = SCHEMA_VERSION + "-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-presentation-v9-"
    "unmounted-lock-1"
)
PRESENTATION_V8_IMPLEMENTATION_SHA256 = (
    "f2720ff7b2b32e7ffdf4c83502b1fa65f83ceb3ee8806dae94b0aaf71fd8ba6b"
)
ADAPTER_V8_IMPLEMENTATION_SHA256 = (
    "430b808a1ed0b0eed771e8b2a6b81efe3d443f88599cf3bd1c75df4d025c5ebf"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
PRESENTATION_BLOCKERS = (
    "PRESENTATION_V9_CONSUMER_NOT_REGISTERED",
    "HTTP_CANDIDATE_V9_NOT_DEFINED",
    "UI_NOT_MOUNTED",
    "CURRENT_ADMISSION_LOCKED",
)

_VERIFY_PRESENTATION_V8 = (
    presentation_v8.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8
)
_VERIFY_ADAPTER_V8 = (
    adapter_v8.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_adapter_v8
)
_PRESENTATION_CONTEXT_KEYS = {
    "adapter_v7_document",
    "adapter_v7_verification_context",
    "presentation_v7_document",
    "presentation_v7_verification_context",
}
_ADAPTER_CONTEXT_KEYS = {
    "adapter_v7_document",
    "adapter_v7_verification_context",
    "edge_gate_v1_document",
    "edge_gate_v1_verification_context",
}
_PRESENTATION_V8_KEYS = {
    "authority",
    "axis_order",
    "decision",
    "facts",
    "gaps",
    "local_decision",
    "multi_window_summary",
    "policy",
    "presentation_v8_hash",
    "risk_summary",
    "schema_version",
    "source",
    "stages",
    "static_fingerprint",
    "status",
}
_PRESENTATION_V8_SOURCE_KEYS = {
    "adapter_v7_context_hash",
    "adapter_v7_hash",
    "adapter_v7_implementation_sha256",
    "presentation_v7_context_hash",
    "presentation_v7_hash",
    "presentation_v7_implementation_sha256",
    "stability_gate_v2_hash",
    "stability_gate_v2_implementation_sha256",
    "state",
    "strict_canonical_implementation_sha256",
    "trade_identity_hash",
}
_PRESENTATION_V8_LOCAL_KEYS = {
    "adapter_v7_decision",
    "adapter_v7_status",
    "anchor_budget_v3_decision",
    "anchor_budget_v3_status",
    "joint_decision",
    "joint_status",
    "presentation_v7_joint_decision",
    "presentation_v7_joint_status",
    "stability_gate_v2_decision",
    "stability_gate_v2_status",
}
_MULTI_WINDOW_KEYS = {
    "anchor_window_id",
    "any_registered_window_blocked",
    "cluster_partition_stable",
    "minimum_conservative_weighted_effective_strata_count",
    "registered_window_count",
    "strata_topology_stable",
    "verified_window_count",
    "worst_window_maximum_active_stratum_gross_pct",
}
_PRESENTATION_V8_RECEIPT_KEYS = {
    "blockers",
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "presentation_consumer_activation_allowed",
    "presentation_v8_exactly_verified",
    "presentation_v8_hash",
    "runtime_gate_activation_allowed",
    "schema_version",
    "status",
    "writer_allowed",
}
_ADAPTER_V8_KEYS = {
    "adapter_v8_hash",
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
    "summary",
}
_ADAPTER_V8_SOURCE_KEYS = {
    "adapter_v7_hash",
    "adapter_v7_implementation_sha256",
    "cluster_partition_hash",
    "edge_evidence_hash",
    "edge_gate_v1_hash",
    "edge_gate_v1_implementation_sha256",
    "edge_preregistration_hash",
    "source_documents_embedded",
    "stability_gate_v2_hash",
    "stability_gate_v2_implementation_sha256",
    "strict_canonical_implementation_sha256",
    "trade_identity_hash",
    "verification_contexts_embedded",
}
_ADAPTER_V8_COMPONENT_KEYS = {
    "adapter_v7_decision",
    "adapter_v7_status",
    "edge_gate_v1_decision",
    "edge_gate_v1_status",
    "stability_gate_v2_decision",
    "stability_gate_v2_status",
}
_ADAPTER_V8_SUMMARY_KEYS = {
    "blocked_pair_count",
    "confidence_z_micros",
    "correlation_floor_micros",
    "edge_verified_pair_count",
    "insufficient_sample_pair_count",
    "maximum_confidence_upper_correlation_micros",
    "observed_breach_pair_count",
    "registered_window_count",
    "uncertainty_overlap_pair_count",
    "verified_window_count",
}
_ADAPTER_V8_RECEIPT_KEYS = {
    "adapter_v8_exactly_verified",
    "adapter_v8_hash",
    "adapter_v8_status",
    "blockers",
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "runtime_gate_activation_allowed",
    "schema_version",
    "source_known",
    "status",
    "writer_allowed",
}


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return type(value) is dict and set(value) == expected


def _is_hash(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool)


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


def _presentation_context_valid(value: Any) -> bool:
    return (
        _exact_keys(value, _PRESENTATION_CONTEXT_KEYS)
        and all(type(value[key]) is dict for key in _PRESENTATION_CONTEXT_KEYS)
    )


def _adapter_context_valid(value: Any) -> bool:
    return (
        _exact_keys(value, _ADAPTER_CONTEXT_KEYS)
        and all(type(value[key]) is dict for key in _ADAPTER_CONTEXT_KEYS)
    )


def _presentation_receipt_valid(value: Any, document: dict[str, Any]) -> bool:
    return (
        _exact_keys(value, _PRESENTATION_V8_RECEIPT_KEYS)
        and value["schema_version"] == presentation_v8.VERIFICATION_SCHEMA_VERSION
        and value["status"] == "PASS"
        and value["blockers"] == []
        and value["presentation_v8_exactly_verified"] is True
        and value["presentation_v8_hash"] == document["presentation_v8_hash"]
        and value["current_admission_allowed"] is False
        and value["live_order_allowed"] is False
        and value["paper_authorized"] is False
        and value["presentation_consumer_activation_allowed"] is False
        and value["runtime_gate_activation_allowed"] is False
        and value["writer_allowed"] is False
    )


def _adapter_receipt_valid(value: Any, document: dict[str, Any]) -> bool:
    return (
        _exact_keys(value, _ADAPTER_V8_RECEIPT_KEYS)
        and value["schema_version"] == adapter_v8.VERIFICATION_SCHEMA_VERSION
        and value["status"] == "PASS"
        and value["blockers"] == []
        and value["adapter_v8_exactly_verified"] is True
        and value["adapter_v8_hash"] == document["adapter_v8_hash"]
        and value["adapter_v8_status"] == document["status"]
        and document["status"] in {"PASS", "BLOCK"}
        and value["source_known"] is True
        and value["current_admission_allowed"] is False
        and value["live_order_allowed"] is False
        and value["paper_authorized"] is False
        and value["runtime_gate_activation_allowed"] is False
        and value["writer_allowed"] is False
    )


def _presentation_document_valid(value: Any) -> bool:
    if not _exact_keys(value, _PRESENTATION_V8_KEYS):
        return False
    source = value["source"]
    local = value["local_decision"]
    multi = value["multi_window_summary"]
    facts = value["facts"]
    return (
        value["schema_version"] == presentation_v8.SCHEMA_VERSION
        and value["static_fingerprint"] == presentation_v8.STATIC_FINGERPRINT
        and value["status"] == "BLOCK"
        and _is_hash(value["presentation_v8_hash"])
        and value["axis_order"] == list(AXIS_ORDER)
        and type(value["risk_summary"]) is dict
        and _exact_keys(source, _PRESENTATION_V8_SOURCE_KEYS)
        and source["state"] == "EXACT_PRESENTATION_V7_AND_ADAPTER_V7"
        and all(
            _is_hash(source[key])
            for key in _PRESENTATION_V8_SOURCE_KEYS
            if key != "state"
        )
        and _exact_keys(local, _PRESENTATION_V8_LOCAL_KEYS)
        and all(
            local[key] in {"PASS", "BLOCK"}
            for key in _PRESENTATION_V8_LOCAL_KEYS
            if key.endswith("_status")
        )
        and _exact_keys(multi, _MULTI_WINDOW_KEYS)
        and _is_int(multi["registered_window_count"])
        and _is_int(multi["verified_window_count"])
        and multi["registered_window_count"] > 0
        and multi["verified_window_count"] == multi["registered_window_count"]
        and type(facts) is dict
        and facts.get("presentation_v7_exactly_verified") is True
        and facts.get("adapter_v7_exactly_verified") is True
        and facts.get("source_documents_embedded") is False
        and facts.get("verification_contexts_embedded") is False
        and facts.get("runtime_consumer_bound") is False
        and facts.get("ui_mounted") is False
        and value["authority"].get("paper_authorized") is False
        and value["authority"].get("live_order_allowed") is False
    )


def _adapter_document_valid(value: Any) -> bool:
    if not _exact_keys(value, _ADAPTER_V8_KEYS):
        return False
    source = value["source"]
    components = value["component_states"]
    summary = value["summary"]
    return (
        value["schema_version"] == adapter_v8.SCHEMA_VERSION
        and value["static_fingerprint"] == adapter_v8.STATIC_FINGERPRINT
        and value["status"] in {"PASS", "BLOCK"}
        and _is_hash(value["adapter_v8_hash"])
        and type(value["decision"]) is str
        and bool(value["decision"])
        and _exact_keys(source, _ADAPTER_V8_SOURCE_KEYS)
        and all(
            _is_hash(source[key])
            for key in _ADAPTER_V8_SOURCE_KEYS
            if key not in {
                "source_documents_embedded",
                "verification_contexts_embedded",
            }
        )
        and source["source_documents_embedded"] is False
        and source["verification_contexts_embedded"] is False
        and _exact_keys(components, _ADAPTER_V8_COMPONENT_KEYS)
        and all(
            components[key] in {"PASS", "BLOCK"}
            for key in _ADAPTER_V8_COMPONENT_KEYS
            if key.endswith("_status")
        )
        and _exact_keys(summary, _ADAPTER_V8_SUMMARY_KEYS)
        and all(_is_int(summary[key]) and summary[key] >= 0 for key in summary)
        and value["facts"].get("source_statuses_known") is True
        and value["facts"].get("source_documents_embedded") is False
        and value["facts"].get("verification_contexts_embedded") is False
        and value["authority"].get("paper_authorized") is False
        and value["authority"].get("live_order_allowed") is False
    )


def _unknown(reason: str) -> dict[str, Any]:
    document = {
        "authority": _authority(),
        "axis_order": list(AXIS_ORDER),
        "decision": "UNKNOWN_EDGE_UNCERTAINTY_PRESENTATION_SOURCE",
        "edge_uncertainty_summary": None,
        "facts": {
            "adapter_v8_exactly_verified": False,
            "browser_review_performed": False,
            "cross_bindings_verified": False,
            "http_candidate_registered": False,
            "positions_embedded": False,
            "presentation_v8_exactly_verified": False,
            "profitability_proven": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "source_documents_embedded": False,
            "ui_mounted": False,
            "verification_contexts_embedded": False,
        },
        "gaps": {
            "adapter_v8_blocker_count": None,
            "edge_uncertainty_blocker_count": None,
            "local_blocker_count": None,
            "presentation_blocker_count": len(PRESENTATION_BLOCKERS),
            "presentation_blockers": list(PRESENTATION_BLOCKERS),
            "source_failure": reason,
        },
        "local_decision": {
            "adapter_v7_decision": "UNKNOWN",
            "adapter_v7_status": "UNKNOWN",
            "adapter_v8_decision": "UNKNOWN",
            "adapter_v8_status": "UNKNOWN",
            "edge_gate_v1_decision": "UNKNOWN",
            "edge_gate_v1_status": "UNKNOWN",
            "joint_decision": "UNKNOWN",
            "joint_status": "UNKNOWN",
            "presentation_v8_joint_decision": "UNKNOWN",
            "presentation_v8_joint_status": "UNKNOWN",
            "stability_gate_v2_decision": "UNKNOWN",
            "stability_gate_v2_status": "UNKNOWN",
        },
        "multi_window_summary": None,
        "policy": {
            "adapter_v8_block_overrides_presentation_v8_local_pass": True,
            "outer_status_is_not_execution_authority": True,
            "source_documents_must_remain_unembedded": True,
        },
        "risk_summary": None,
        "schema_version": SCHEMA_VERSION,
        "source": {
            "adapter_v7_hash": None,
            "adapter_v8_hash": None,
            "adapter_v8_implementation_sha256": ADAPTER_V8_IMPLEMENTATION_SHA256,
            "cluster_partition_hash": None,
            "edge_gate_v1_hash": None,
            "presentation_v8_hash": None,
            "presentation_v8_implementation_sha256": (
                PRESENTATION_V8_IMPLEMENTATION_SHA256
            ),
            "stability_gate_v2_hash": None,
            "state": "UNKNOWN",
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "trade_identity_hash": None,
        },
        "stages": [
            {"axis": "SOURCE", "detail": "UNKNOWN", "state": "UNKNOWN"},
            {"axis": "GAP", "detail": reason, "state": "OPEN"},
            {
                "axis": "MATURITY",
                "detail": "UNMOUNTED_PRESENTATION_CANDIDATE_V9",
                "state": "CANDIDATE",
            },
            {
                "axis": "PERMISSION",
                "detail": "NO_EXECUTION_OR_ACTIVATION_PERMISSION",
                "state": "NONE",
            },
        ],
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCK",
    }
    return seal_strict_canonical_document(document, "presentation_v9_hash")


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9(
    presentation_v8_document: Any,
    adapter_v8_document: Any,
    *,
    presentation_v8_verification_context: Any,
    adapter_v8_verification_context: Any,
) -> dict[str, Any]:
    """Build a bounded unmounted presentation and fail closed on every splice."""
    if not _presentation_context_valid(presentation_v8_verification_context):
        return _unknown("PRESENTATION_V8_VERIFICATION_CONTEXT_INVALID")
    if not _adapter_context_valid(adapter_v8_verification_context):
        return _unknown("ADAPTER_V8_VERIFICATION_CONTEXT_INVALID")
    if not _presentation_document_valid(presentation_v8_document):
        return _unknown("PRESENTATION_V8_DOCUMENT_INVALID")
    if not _adapter_document_valid(adapter_v8_document):
        return _unknown("ADAPTER_V8_DOCUMENT_INVALID")
    try:
        presentation_receipt = _VERIFY_PRESENTATION_V8(
            presentation_v8_document,
            presentation_v8_verification_context["presentation_v7_document"],
            presentation_v8_verification_context["adapter_v7_document"],
            presentation_v7_verification_context=presentation_v8_verification_context[
                "presentation_v7_verification_context"
            ],
            adapter_v7_verification_context=presentation_v8_verification_context[
                "adapter_v7_verification_context"
            ],
        )
    except (KeyError, TypeError, ValueError):
        presentation_receipt = None
    if not _presentation_receipt_valid(
        presentation_receipt,
        presentation_v8_document,
    ):
        return _unknown("PRESENTATION_V8_EXACT_REBUILD_FAILED")
    try:
        adapter_receipt = _VERIFY_ADAPTER_V8(
            adapter_v8_document,
            adapter_v8_verification_context["adapter_v7_document"],
            adapter_v8_verification_context["edge_gate_v1_document"],
            adapter_v7_verification_context=adapter_v8_verification_context[
                "adapter_v7_verification_context"
            ],
            edge_gate_v1_verification_context=adapter_v8_verification_context[
                "edge_gate_v1_verification_context"
            ],
        )
    except (KeyError, TypeError, ValueError):
        adapter_receipt = None
    if not _adapter_receipt_valid(adapter_receipt, adapter_v8_document):
        return _unknown("ADAPTER_V8_EXACT_REBUILD_FAILED")

    presentation_adapter = presentation_v8_verification_context[
        "adapter_v7_document"
    ]
    joint_adapter = adapter_v8_verification_context["adapter_v7_document"]
    if not strict_json_contract_equal(presentation_adapter, joint_adapter):
        return _unknown("ADAPTER_V7_DOCUMENT_CONTEXT_SPLICE")
    p8_source = presentation_v8_document["source"]
    a8_source = adapter_v8_document["source"]
    p8_local = presentation_v8_document["local_decision"]
    a8_components = adapter_v8_document["component_states"]
    if (
        p8_source["adapter_v7_hash"] != a8_source["adapter_v7_hash"]
        or p8_source["adapter_v7_hash"] != presentation_adapter.get("adapter_v7_hash")
    ):
        return _unknown("ADAPTER_V7_HASH_SPLICE")
    if p8_source["stability_gate_v2_hash"] != a8_source["stability_gate_v2_hash"]:
        return _unknown("STABILITY_GATE_V2_HASH_SPLICE")
    if p8_source["trade_identity_hash"] != a8_source["trade_identity_hash"]:
        return _unknown("TRADE_IDENTITY_SPLICE")
    if (
        p8_local["adapter_v7_status"] != a8_components["adapter_v7_status"]
        or p8_local["adapter_v7_decision"] != a8_components["adapter_v7_decision"]
    ):
        return _unknown("ADAPTER_V7_STATUS_DECISION_SPLICE")
    if (
        p8_local["stability_gate_v2_status"]
        != a8_components["stability_gate_v2_status"]
        or p8_local["stability_gate_v2_decision"]
        != a8_components["stability_gate_v2_decision"]
    ):
        return _unknown("STABILITY_GATE_V2_STATUS_DECISION_SPLICE")
    p8_multi = presentation_v8_document["multi_window_summary"]
    a8_summary = adapter_v8_document["summary"]
    if (
        p8_multi["registered_window_count"] != a8_summary["registered_window_count"]
        or p8_multi["verified_window_count"] != a8_summary["verified_window_count"]
    ):
        return _unknown("WINDOW_COUNT_SPLICE")

    presentation_blocked = p8_local["joint_status"] == "BLOCK"
    adapter_blocked = adapter_v8_document["status"] == "BLOCK"
    local_blocked = presentation_blocked or adapter_blocked
    joint_status = "BLOCK" if local_blocked else "PASS"
    joint_decision = (
        "BLOCK_STRATIFIED_MULTI_WINDOW_EDGE_UNCERTAINTY_LOCAL_RESEARCH"
        if local_blocked
        else "PASS_STRATIFIED_MULTI_WINDOW_EDGE_UNCERTAINTY_LOCAL_RESEARCH"
    )
    edge_blockers = a8_summary["blocked_pair_count"]
    document = {
        "authority": _authority(),
        "axis_order": list(AXIS_ORDER),
        "decision": (
            "EXACT_EDGE_UNCERTAINTY_LOCAL_BLOCK_PROJECTED_UNMOUNTED"
            if local_blocked
            else "EXACT_EDGE_UNCERTAINTY_LOCAL_CLEAR_PROJECTED_UNMOUNTED"
        ),
        "edge_uncertainty_summary": {
            "blocked_pair_count": a8_summary["blocked_pair_count"],
            "cluster_partition_hash": a8_source["cluster_partition_hash"],
            "confidence_z_micros": a8_summary["confidence_z_micros"],
            "correlation_floor_micros": a8_summary["correlation_floor_micros"],
            "insufficient_sample_pair_count": a8_summary[
                "insufficient_sample_pair_count"
            ],
            "maximum_confidence_upper_correlation_micros": a8_summary[
                "maximum_confidence_upper_correlation_micros"
            ],
            "observed_breach_pair_count": a8_summary[
                "observed_breach_pair_count"
            ],
            "uncertainty_overlap_pair_count": a8_summary[
                "uncertainty_overlap_pair_count"
            ],
            "verified_pair_count": a8_summary["edge_verified_pair_count"],
        },
        "facts": {
            "adapter_v8_exactly_verified": True,
            "browser_review_performed": False,
            "cross_bindings_verified": True,
            "http_candidate_registered": False,
            "positions_embedded": False,
            "presentation_v8_exactly_verified": True,
            "profitability_proven": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "source_documents_embedded": False,
            "ui_mounted": False,
            "verification_contexts_embedded": False,
        },
        "gaps": {
            "adapter_v8_blocker_count": len(adapter_v8_document["blockers"]),
            "edge_uncertainty_blocker_count": edge_blockers,
            "local_blocker_count": 1 if local_blocked else 0,
            "presentation_blocker_count": len(PRESENTATION_BLOCKERS),
            "presentation_blockers": list(PRESENTATION_BLOCKERS),
            "source_failure": None,
        },
        "local_decision": {
            "adapter_v7_decision": a8_components["adapter_v7_decision"],
            "adapter_v7_status": a8_components["adapter_v7_status"],
            "adapter_v8_decision": adapter_v8_document["decision"],
            "adapter_v8_status": adapter_v8_document["status"],
            "edge_gate_v1_decision": a8_components["edge_gate_v1_decision"],
            "edge_gate_v1_status": a8_components["edge_gate_v1_status"],
            "joint_decision": joint_decision,
            "joint_status": joint_status,
            "presentation_v8_joint_decision": p8_local["joint_decision"],
            "presentation_v8_joint_status": p8_local["joint_status"],
            "stability_gate_v2_decision": a8_components[
                "stability_gate_v2_decision"
            ],
            "stability_gate_v2_status": a8_components["stability_gate_v2_status"],
        },
        "multi_window_summary": deepcopy(p8_multi),
        "policy": {
            "adapter_v8_block_overrides_presentation_v8_local_pass": True,
            "outer_status_is_not_execution_authority": True,
            "source_documents_must_remain_unembedded": True,
        },
        "risk_summary": deepcopy(presentation_v8_document["risk_summary"]),
        "schema_version": SCHEMA_VERSION,
        "source": {
            "adapter_v7_hash": a8_source["adapter_v7_hash"],
            "adapter_v8_hash": adapter_v8_document["adapter_v8_hash"],
            "adapter_v8_implementation_sha256": ADAPTER_V8_IMPLEMENTATION_SHA256,
            "cluster_partition_hash": a8_source["cluster_partition_hash"],
            "edge_gate_v1_hash": a8_source["edge_gate_v1_hash"],
            "presentation_v8_hash": presentation_v8_document["presentation_v8_hash"],
            "presentation_v8_implementation_sha256": (
                PRESENTATION_V8_IMPLEMENTATION_SHA256
            ),
            "stability_gate_v2_hash": a8_source["stability_gate_v2_hash"],
            "state": "EXACT_PRESENTATION_V8_AND_ADAPTER_V8",
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "trade_identity_hash": a8_source["trade_identity_hash"],
        },
        "stages": [
            {
                "axis": "SOURCE",
                "detail": "EXACT_PRESENTATION_V8_AND_ADAPTER_V8",
                "state": "KNOWN",
            },
            {
                "axis": "GAP",
                "detail": (
                    "LOCAL_RESEARCH_BLOCK_PRESENT"
                    if local_blocked
                    else "LOCAL_RESEARCH_GATES_CLEAR_GOVERNANCE_GAPS_REMAIN"
                ),
                "state": "OPEN" if local_blocked else "CLEAR_WITH_GOVERNANCE_GAPS",
            },
            {
                "axis": "MATURITY",
                "detail": "UNMOUNTED_PRESENTATION_CANDIDATE_V9",
                "state": "CANDIDATE",
            },
            {
                "axis": "PERMISSION",
                "detail": "NO_EXECUTION_OR_ACTIVATION_PERMISSION",
                "state": "NONE",
            },
        ],
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCK",
    }
    return seal_strict_canonical_document(document, "presentation_v9_hash")


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9(
    document: Any,
    presentation_v8_document: Any,
    adapter_v8_document: Any,
    *,
    presentation_v8_verification_context: Any,
    adapter_v8_verification_context: Any,
) -> dict[str, Any]:
    """Return an authority-locked exact-rebuild receipt."""
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9(
            presentation_v8_document,
            adapter_v8_document,
            presentation_v8_verification_context=presentation_v8_verification_context,
            adapter_v8_verification_context=adapter_v8_verification_context,
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        expected = None
        exact = False
    return {
        "blockers": [] if exact else ["PRESENTATION_V9_EXACT_REBUILD_FAILED"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_v9_exactly_verified": exact,
        "presentation_v9_hash": expected.get("presentation_v9_hash") if exact else None,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }


__all__ = [
    "ADAPTER_V8_IMPLEMENTATION_SHA256",
    "AXIS_ORDER",
    "PRESENTATION_BLOCKERS",
    "PRESENTATION_V8_IMPLEMENTATION_SHA256",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9",
]
