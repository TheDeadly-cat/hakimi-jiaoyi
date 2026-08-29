"""Bounded presentation joining presentation-v9 and adapter-v9.

The presentation exposes aggregate portfolio-risk, multi-window, edge
uncertainty, and common-observation provenance evidence. It remains unmounted,
outer blocked, research-only, and grants no consumer, writer, paper, live, or
current authority.
"""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_adapter_v9
    as adapter_v9,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9
    as presentation_v9,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "edge-uncertainty-common-observation-basis-presentation-v10"
)
VERIFICATION_SCHEMA_VERSION = SCHEMA_VERSION + "-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "basis-presentation-v10-unmounted-lock-1"
)
PRESENTATION_V9_IMPLEMENTATION_SHA256 = (
    "5fb7af67366913016c79236419f9b8df356a6b809ec876e0c312a67a4839b132"
)
ADAPTER_V9_IMPLEMENTATION_SHA256 = (
    "9bad81d8b719ab20402a5970498848660a343dd9f386b32294c5da50da3cf517"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
PRESENTATION_BLOCKERS = (
    "PRESENTATION_V10_CONSUMER_NOT_REGISTERED",
    "HTTP_CANDIDATE_V10_NOT_DEFINED",
    "UI_NOT_MOUNTED",
    "CURRENT_ADMISSION_LOCKED",
)

_VERIFY_PRESENTATION_V9 = (
    presentation_v9.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9
)
_VERIFY_ADAPTER_V9 = (
    adapter_v9.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_adapter_v9
)
_PRESENTATION_CONTEXT_KEYS = {
    "adapter_v8_document",
    "adapter_v8_verification_context",
    "presentation_v8_document",
    "presentation_v8_verification_context",
}
_ADAPTER_CONTEXT_KEYS = {
    "adapter_v8_document",
    "adapter_v8_verification_context",
    "common_observation_basis_gate_v1_document",
    "common_observation_basis_gate_v1_verification_context",
}
_PRESENTATION_RECEIPT_KEYS = {
    "blockers",
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "presentation_consumer_activation_allowed",
    "presentation_v9_exactly_verified",
    "presentation_v9_hash",
    "runtime_gate_activation_allowed",
    "schema_version",
    "status",
    "writer_allowed",
}
_ADAPTER_RECEIPT_KEYS = {
    "adapter_v9_exactly_verified",
    "adapter_v9_hash",
    "adapter_v9_status",
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
_PRESENTATION_TOP_KEYS = {
    "authority",
    "axis_order",
    "decision",
    "edge_uncertainty_summary",
    "facts",
    "gaps",
    "local_decision",
    "multi_window_summary",
    "policy",
    "presentation_v9_hash",
    "risk_summary",
    "schema_version",
    "source",
    "stages",
    "static_fingerprint",
    "status",
}
_PRESENTATION_SOURCE_KEYS = {
    "adapter_v7_hash",
    "adapter_v8_hash",
    "adapter_v8_implementation_sha256",
    "cluster_partition_hash",
    "edge_gate_v1_hash",
    "presentation_v8_hash",
    "presentation_v8_implementation_sha256",
    "stability_gate_v2_hash",
    "state",
    "strict_canonical_implementation_sha256",
    "trade_identity_hash",
}
_EDGE_KEYS = {
    "blocked_pair_count",
    "cluster_partition_hash",
    "confidence_z_micros",
    "correlation_floor_micros",
    "insufficient_sample_pair_count",
    "maximum_confidence_upper_correlation_micros",
    "observed_breach_pair_count",
    "uncertainty_overlap_pair_count",
    "verified_pair_count",
}
_MULTI_KEYS = {
    "anchor_window_id",
    "any_registered_window_blocked",
    "cluster_partition_stable",
    "minimum_conservative_weighted_effective_strata_count",
    "registered_window_count",
    "strata_topology_stable",
    "verified_window_count",
    "worst_window_maximum_active_stratum_gross_pct",
}
_RISK_KEYS = {
    "active_dimension_count",
    "conservative_weighted_effective_strata_count",
    "dimension_results",
    "maximum_active_stratum_gross_pct",
    "total_active_gross_pct",
    "v2_weighted_effective_cluster_count",
    "weighted_diversification_gate_applied",
}
_DIMENSION_KEYS = {
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
_PRESENTATION_LOCAL_KEYS = {
    "adapter_v7_decision",
    "adapter_v7_status",
    "adapter_v8_decision",
    "adapter_v8_status",
    "edge_gate_v1_decision",
    "edge_gate_v1_status",
    "joint_decision",
    "joint_status",
    "presentation_v8_joint_decision",
    "presentation_v8_joint_status",
    "stability_gate_v2_decision",
    "stability_gate_v2_status",
}
_ADAPTER_TOP_KEYS = {
    "adapter_v9_hash",
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
_ADAPTER_SOURCE_KEYS = {
    "adapter_v8_hash",
    "adapter_v8_implementation_sha256",
    "basis_evidence_hash",
    "basis_preregistration_hash",
    "cluster_partition_hash",
    "common_observation_basis_gate_v1_hash",
    "common_observation_basis_gate_v1_implementation_sha256",
    "common_sample_set_hash",
    "edge_evidence_hash",
    "edge_gate_v1_hash",
    "edge_preregistration_hash",
    "observation_policy_hash",
    "source_documents_embedded",
    "strict_canonical_implementation_sha256",
    "trade_identity_hash",
    "verification_contexts_embedded",
}
_ADAPTER_SUMMARY_KEYS = {
    "blocked_pair_count",
    "common_sample_count",
    "confidence_z_micros",
    "correlation_floor_micros",
    "edge_pair_count",
    "edge_verified_pair_count",
    "insufficient_sample_pair_count",
    "maximum_confidence_upper_correlation_micros",
    "minimum_common_sample_count",
    "observed_breach_pair_count",
    "pair_count_matching_common_sample_count",
    "registered_window_count",
    "uncertainty_overlap_pair_count",
    "verified_window_count",
}
_ADAPTER_COMPONENT_KEYS = {
    "adapter_v8_decision",
    "adapter_v8_status",
    "common_observation_basis_gate_v1_decision",
    "common_observation_basis_gate_v1_status",
    "edge_gate_v1_decision",
    "edge_gate_v1_status",
}


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return type(value) is dict and set(value) == expected


def _is_hash(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_int(value: Any, minimum: int | None = None) -> bool:
    return (
        type(value) is int
        and not isinstance(value, bool)
        and (minimum is None or value >= minimum)
    )


def _is_non_negative_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and type(value) in {int, float}
        and (type(value) is not float or math.isfinite(value))
        and value >= 0
    )


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


def _dimension_valid(value: Any) -> bool:
    return (
        _exact_keys(value, _DIMENSION_KEYS)
        and _is_int(value["active_stratum_count"], 0)
        and _is_int(value["over_limit_stratum_count"], 0)
        and type(value["dimension_id"]) is str
        and bool(value["dimension_id"])
        and type(value["dominant_stratum_id"]) is str
        and bool(value["dominant_stratum_id"])
        and value["diversification_status"] in {"PASS", "BLOCK", "NOT_APPLICABLE"}
        and value["gross_limit_status"] in {"PASS", "BLOCK"}
        and value["status"] in {"PASS", "BLOCK"}
        and _is_non_negative_number(
            value["dominant_stratum_share_of_active_gross_pct"]
        )
        and _is_non_negative_number(value["maximum_stratum_gross_pct"])
        and _is_non_negative_number(value["weighted_effective_strata_count"])
    )


def _risk_valid(value: Any) -> bool:
    if not _exact_keys(value, _RISK_KEYS) or type(value["dimension_results"]) is not list:
        return False
    return (
        _is_int(value["active_dimension_count"], 0)
        and value["active_dimension_count"] == len(value["dimension_results"])
        and all(_dimension_valid(row) for row in value["dimension_results"])
        and _is_non_negative_number(
            value["conservative_weighted_effective_strata_count"]
        )
        and _is_non_negative_number(value["maximum_active_stratum_gross_pct"])
        and _is_non_negative_number(value["total_active_gross_pct"])
        and _is_non_negative_number(value["v2_weighted_effective_cluster_count"])
        and type(value["weighted_diversification_gate_applied"]) is bool
    )


def _multi_valid(value: Any) -> bool:
    return (
        _exact_keys(value, _MULTI_KEYS)
        and type(value["anchor_window_id"]) is str
        and bool(value["anchor_window_id"])
        and _is_int(value["registered_window_count"], 1)
        and value["verified_window_count"] == value["registered_window_count"]
        and type(value["any_registered_window_blocked"]) is bool
        and type(value["cluster_partition_stable"]) is bool
        and type(value["strata_topology_stable"]) is bool
        and _is_non_negative_number(
            value["minimum_conservative_weighted_effective_strata_count"]
        )
        and _is_non_negative_number(
            value["worst_window_maximum_active_stratum_gross_pct"]
        )
    )


def _edge_valid(value: Any) -> bool:
    if not _exact_keys(value, _EDGE_KEYS):
        return False
    count_keys = _EDGE_KEYS - {
        "cluster_partition_hash",
        "confidence_z_micros",
        "correlation_floor_micros",
        "maximum_confidence_upper_correlation_micros",
    }
    return (
        all(_is_int(value[key], 0) for key in count_keys)
        and _is_hash(value["cluster_partition_hash"])
        and _is_int(value["confidence_z_micros"], 1)
        and _is_int(value["correlation_floor_micros"])
        and _is_int(value["maximum_confidence_upper_correlation_micros"])
    )


def _presentation_document_valid(value: Any) -> bool:
    if not _exact_keys(value, _PRESENTATION_TOP_KEYS):
        return False
    source = value["source"]
    local = value["local_decision"]
    stages = value["stages"]
    if not _exact_keys(source, _PRESENTATION_SOURCE_KEYS) or not _exact_keys(
        local, _PRESENTATION_LOCAL_KEYS
    ):
        return False
    status_keys = [key for key in _PRESENTATION_LOCAL_KEYS if key.endswith("_status")]
    decision_keys = [
        key for key in _PRESENTATION_LOCAL_KEYS if key.endswith("_decision")
    ]
    return (
        value["schema_version"] == presentation_v9.SCHEMA_VERSION
        and value["static_fingerprint"] == presentation_v9.STATIC_FINGERPRINT
        and value["status"] == "BLOCK"
        and _is_hash(value["presentation_v9_hash"])
        and value["axis_order"] == list(AXIS_ORDER)
        and value["authority"] == _authority()
        and type(value["decision"]) is str
        and bool(value["decision"])
        and type(value["policy"]) is dict
        and all(_is_hash(source[key]) for key in _PRESENTATION_SOURCE_KEYS - {"state"})
        and source["state"] == "EXACT_PRESENTATION_V8_AND_ADAPTER_V8"
        and source["strict_canonical_implementation_sha256"]
        == STRICT_CANONICAL_IMPLEMENTATION_SHA256
        and all(local[key] in {"PASS", "BLOCK"} for key in status_keys)
        and all(type(local[key]) is str and bool(local[key]) for key in decision_keys)
        and _risk_valid(value["risk_summary"])
        and _multi_valid(value["multi_window_summary"])
        and _edge_valid(value["edge_uncertainty_summary"])
        and value["edge_uncertainty_summary"]["cluster_partition_hash"]
        == source["cluster_partition_hash"]
        and type(stages) is list
        and len(stages) == 4
        and all(
            _exact_keys(stage, {"axis", "detail", "state"})
            and stage["axis"] == AXIS_ORDER[index]
            and type(stage["detail"]) is str
            and bool(stage["detail"])
            and type(stage["state"]) is str
            and bool(stage["state"])
            for index, stage in enumerate(stages)
        )
    )


def _adapter_document_valid(value: Any) -> bool:
    if not _exact_keys(value, _ADAPTER_TOP_KEYS):
        return False
    source = value["source"]
    summary = value["summary"]
    components = value["component_states"]
    if (
        not _exact_keys(source, _ADAPTER_SOURCE_KEYS)
        or not _exact_keys(summary, _ADAPTER_SUMMARY_KEYS)
        or not _exact_keys(components, _ADAPTER_COMPONENT_KEYS)
    ):
        return False
    hash_keys = _ADAPTER_SOURCE_KEYS - {
        "source_documents_embedded",
        "verification_contexts_embedded",
    }
    status_keys = [key for key in _ADAPTER_COMPONENT_KEYS if key.endswith("_status")]
    decision_keys = [
        key for key in _ADAPTER_COMPONENT_KEYS if key.endswith("_decision")
    ]
    return (
        value["schema_version"] == adapter_v9.SCHEMA_VERSION
        and value["static_fingerprint"] == adapter_v9.STATIC_FINGERPRINT
        and value["status"] in {"PASS", "BLOCK"}
        and _is_hash(value["adapter_v9_hash"])
        and type(value["decision"]) is str
        and bool(value["decision"])
        and type(value["blockers"]) is list
        and all(type(item) is str and bool(item) for item in value["blockers"])
        and all(_is_hash(source[key]) for key in hash_keys)
        and source["source_documents_embedded"] is False
        and source["verification_contexts_embedded"] is False
        and source["strict_canonical_implementation_sha256"]
        == STRICT_CANONICAL_IMPLEMENTATION_SHA256
        and all(_is_int(summary[key], 0) for key in summary)
        and all(components[key] in {"PASS", "BLOCK"} for key in status_keys)
        and all(
            type(components[key]) is str and bool(components[key])
            for key in decision_keys
        )
        and value["facts"].get("provenance_declaration_only") is True
        and value["facts"].get("raw_samples_recomputed") is False
    )


def _presentation_receipt_valid(value: Any, document: dict[str, Any]) -> bool:
    return (
        _exact_keys(value, _PRESENTATION_RECEIPT_KEYS)
        and value["schema_version"] == presentation_v9.VERIFICATION_SCHEMA_VERSION
        and value["status"] == "PASS"
        and value["blockers"] == []
        and value["presentation_v9_exactly_verified"] is True
        and value["presentation_v9_hash"] == document["presentation_v9_hash"]
        and value["current_admission_allowed"] is False
        and value["live_order_allowed"] is False
        and value["paper_authorized"] is False
        and value["presentation_consumer_activation_allowed"] is False
        and value["runtime_gate_activation_allowed"] is False
        and value["writer_allowed"] is False
    )


def _adapter_receipt_valid(value: Any, document: dict[str, Any]) -> bool:
    return (
        _exact_keys(value, _ADAPTER_RECEIPT_KEYS)
        and value["schema_version"] == adapter_v9.VERIFICATION_SCHEMA_VERSION
        and value["status"] == "PASS"
        and value["blockers"] == []
        and value["adapter_v9_exactly_verified"] is True
        and value["adapter_v9_hash"] == document["adapter_v9_hash"]
        and value["adapter_v9_status"] == document["status"]
        and value["source_known"] is True
        and value["current_admission_allowed"] is False
        and value["live_order_allowed"] is False
        and value["paper_authorized"] is False
        and value["runtime_gate_activation_allowed"] is False
        and value["writer_allowed"] is False
    )


def _unknown(reason: str) -> dict[str, Any]:
    document = {
        "authority": _authority(),
        "axis_order": list(AXIS_ORDER),
        "common_observation_summary": None,
        "decision": "UNKNOWN_COMMON_OBSERVATION_BASIS_PRESENTATION_V10",
        "edge_uncertainty_summary": None,
        "facts": {
            "adapter_v9_exactly_verified": False,
            "browser_review_performed": False,
            "common_observation_basis_projected": False,
            "cross_bindings_verified": False,
            "http_candidate_registered": False,
            "positions_embedded": False,
            "presentation_v9_exactly_verified": False,
            "profitability_proven": False,
            "provenance_declaration_only": True,
            "raw_samples_recomputed": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "source_documents_embedded": False,
            "ui_mounted": False,
            "verification_contexts_embedded": False,
        },
        "gaps": {
            "adapter_v9_blocker_count": 0,
            "common_observation_basis_blocker_count": 0,
            "local_blocker_count": 0,
            "presentation_blocker_count": len(PRESENTATION_BLOCKERS),
            "presentation_blockers": list(PRESENTATION_BLOCKERS),
            "source_failure": reason,
        },
        "local_decision": {
            "adapter_v8_decision": "UNKNOWN",
            "adapter_v8_status": "UNKNOWN",
            "adapter_v9_decision": "UNKNOWN",
            "adapter_v9_status": "UNKNOWN",
            "common_observation_basis_gate_v1_decision": "UNKNOWN",
            "common_observation_basis_gate_v1_status": "UNKNOWN",
            "edge_gate_v1_decision": "UNKNOWN",
            "edge_gate_v1_status": "UNKNOWN",
            "joint_decision": "UNKNOWN",
            "joint_status": "UNKNOWN",
            "presentation_v9_joint_decision": "UNKNOWN",
            "presentation_v9_joint_status": "UNKNOWN",
        },
        "multi_window_summary": None,
        "policy": {
            "outer_status_always_block": True,
            "provenance_is_not_raw_sample_recomputation": True,
            "risk_reduction_is_not_execution_authority": True,
        },
        "risk_summary": None,
        "schema_version": SCHEMA_VERSION,
        "source": {
            "adapter_v8_hash": None,
            "adapter_v9_hash": None,
            "adapter_v9_implementation_sha256": ADAPTER_V9_IMPLEMENTATION_SHA256,
            "basis_evidence_hash": None,
            "basis_preregistration_hash": None,
            "cluster_partition_hash": None,
            "common_observation_basis_gate_v1_hash": None,
            "common_sample_set_hash": None,
            "edge_gate_v1_hash": None,
            "observation_policy_hash": None,
            "presentation_v9_hash": None,
            "presentation_v9_implementation_sha256": PRESENTATION_V9_IMPLEMENTATION_SHA256,
            "state": "UNKNOWN",
            "strict_canonical_implementation_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
            "trade_identity_hash": None,
        },
        "stages": [
            {
                "axis": axis,
                "detail": "NO_PERMISSION_CAN_BE_INFERRED" if axis == "PERMISSION" else "UNKNOWN",
                "state": "NONE" if axis == "PERMISSION" else "UNKNOWN",
            }
            for axis in AXIS_ORDER
        ],
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCK",
    }
    return seal_strict_canonical_document(document, "presentation_v10_hash")


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10(
    presentation_v9_document: Any,
    adapter_v9_document: Any,
    *,
    presentation_v9_verification_context: Any,
    adapter_v9_verification_context: Any,
) -> dict[str, Any]:
    """Build a bounded, outer-blocked presentation from exact predecessors."""
    if (
        not _presentation_document_valid(presentation_v9_document)
        or not _adapter_document_valid(adapter_v9_document)
        or not _exact_keys(
            presentation_v9_verification_context, _PRESENTATION_CONTEXT_KEYS
        )
        or not _exact_keys(adapter_v9_verification_context, _ADAPTER_CONTEXT_KEYS)
    ):
        return _unknown("SOURCE_OR_CONTEXT_CONTRACT_INVALID")
    presentation_context = presentation_v9_verification_context
    adapter_context = adapter_v9_verification_context
    try:
        presentation_receipt = _VERIFY_PRESENTATION_V9(
            presentation_v9_document,
            presentation_context["presentation_v8_document"],
            presentation_context["adapter_v8_document"],
            presentation_v8_verification_context=presentation_context[
                "presentation_v8_verification_context"
            ],
            adapter_v8_verification_context=presentation_context[
                "adapter_v8_verification_context"
            ],
        )
        adapter_receipt = _VERIFY_ADAPTER_V9(
            adapter_v9_document,
            adapter_context["adapter_v8_document"],
            adapter_context["common_observation_basis_gate_v1_document"],
            adapter_v8_verification_context=adapter_context[
                "adapter_v8_verification_context"
            ],
            common_observation_basis_gate_v1_verification_context=adapter_context[
                "common_observation_basis_gate_v1_verification_context"
            ],
        )
    except (KeyError, TypeError, ValueError):
        return _unknown("PREDECESSOR_VERIFIER_EXCEPTION")
    if not _presentation_receipt_valid(presentation_receipt, presentation_v9_document):
        return _unknown("PRESENTATION_V9_EXACT_REBUILD_FAILED")
    if not _adapter_receipt_valid(adapter_receipt, adapter_v9_document):
        return _unknown("ADAPTER_V9_EXACT_REBUILD_FAILED")
    if not strict_json_contract_equal(
        presentation_context["adapter_v8_document"],
        adapter_context["adapter_v8_document"],
    ):
        return _unknown("ADAPTER_V8_DOCUMENT_CONTEXT_SPLICE")

    presentation_source = presentation_v9_document["source"]
    adapter_source = adapter_v9_document["source"]
    presentation_local = presentation_v9_document["local_decision"]
    adapter_components = adapter_v9_document["component_states"]
    presentation_edge = presentation_v9_document["edge_uncertainty_summary"]
    presentation_multi = presentation_v9_document["multi_window_summary"]
    adapter_summary = adapter_v9_document["summary"]
    bindings = {
        "adapter_v8": (
            presentation_source["adapter_v8_hash"]
            == adapter_source["adapter_v8_hash"]
            == presentation_context["adapter_v8_document"].get("adapter_v8_hash")
        ),
        "edge_gate": (
            presentation_source["edge_gate_v1_hash"]
            == adapter_source["edge_gate_v1_hash"]
        ),
        "partition": (
            presentation_source["cluster_partition_hash"]
            == adapter_source["cluster_partition_hash"]
        ),
        "trade": (
            presentation_source["trade_identity_hash"]
            == adapter_source["trade_identity_hash"]
        ),
        "adapter_component": (
            presentation_local["adapter_v8_status"]
            == adapter_components["adapter_v8_status"]
            and presentation_local["adapter_v8_decision"]
            == adapter_components["adapter_v8_decision"]
        ),
        "edge_component": (
            presentation_local["edge_gate_v1_status"]
            == adapter_components["edge_gate_v1_status"]
            and presentation_local["edge_gate_v1_decision"]
            == adapter_components["edge_gate_v1_decision"]
        ),
        "edge_summary": (
            presentation_edge["blocked_pair_count"]
            == adapter_summary["blocked_pair_count"]
            and presentation_edge["confidence_z_micros"]
            == adapter_summary["confidence_z_micros"]
            and presentation_edge["correlation_floor_micros"]
            == adapter_summary["correlation_floor_micros"]
            and presentation_edge["insufficient_sample_pair_count"]
            == adapter_summary["insufficient_sample_pair_count"]
            and presentation_edge[
                "maximum_confidence_upper_correlation_micros"
            ]
            == adapter_summary["maximum_confidence_upper_correlation_micros"]
            and presentation_edge["observed_breach_pair_count"]
            == adapter_summary["observed_breach_pair_count"]
            and presentation_edge["uncertainty_overlap_pair_count"]
            == adapter_summary["uncertainty_overlap_pair_count"]
            and presentation_edge["verified_pair_count"]
            == adapter_summary["edge_verified_pair_count"]
        ),
        "window_counts": (
            presentation_multi["registered_window_count"]
            == adapter_summary["registered_window_count"]
            and presentation_multi["verified_window_count"]
            == adapter_summary["verified_window_count"]
        ),
    }
    failed = [name for name, passed in bindings.items() if not passed]
    if failed:
        return _unknown("CROSS_BINDING_SPLICE_" + "_".join(sorted(failed)).upper())

    p9_blocked = presentation_local["joint_status"] == "BLOCK"
    adapter_blocked = adapter_v9_document["status"] == "BLOCK"
    local_blocked = p9_blocked or adapter_blocked
    local_decision = {
        "adapter_v8_decision": presentation_local["adapter_v8_decision"],
        "adapter_v8_status": presentation_local["adapter_v8_status"],
        "adapter_v9_decision": adapter_v9_document["decision"],
        "adapter_v9_status": adapter_v9_document["status"],
        "common_observation_basis_gate_v1_decision": adapter_components[
            "common_observation_basis_gate_v1_decision"
        ],
        "common_observation_basis_gate_v1_status": adapter_components[
            "common_observation_basis_gate_v1_status"
        ],
        "edge_gate_v1_decision": presentation_local["edge_gate_v1_decision"],
        "edge_gate_v1_status": presentation_local["edge_gate_v1_status"],
        "joint_decision": (
            "BLOCK_COMMON_OBSERVATION_BASIS_PRESENTATION_V10"
            if local_blocked
            else "PASS_COMMON_OBSERVATION_BASIS_LOCAL_RESEARCH_PRESENTATION_V10"
        ),
        "joint_status": "BLOCK" if local_blocked else "PASS",
        "presentation_v9_joint_decision": presentation_local["joint_decision"],
        "presentation_v9_joint_status": presentation_local["joint_status"],
    }
    document = {
        "authority": _authority(),
        "axis_order": list(AXIS_ORDER),
        "common_observation_summary": {
            "all_pair_sample_counts_match": (
                adapter_summary["pair_count_matching_common_sample_count"]
                == adapter_summary["edge_pair_count"]
            ),
            "common_sample_count": adapter_summary["common_sample_count"],
            "edge_pair_count": adapter_summary["edge_pair_count"],
            "minimum_common_sample_count": adapter_summary[
                "minimum_common_sample_count"
            ],
            "pair_count_matching_common_sample_count": adapter_summary[
                "pair_count_matching_common_sample_count"
            ],
            "provenance_declaration_only": True,
            "raw_samples_recomputed": False,
        },
        "decision": "BLOCK_OUTER_PRESENTATION_V10_AUTHORITY_UNCHANGED",
        "edge_uncertainty_summary": deepcopy(presentation_edge),
        "facts": {
            "adapter_v9_exactly_verified": True,
            "browser_review_performed": False,
            "common_observation_basis_projected": True,
            "cross_bindings_verified": True,
            "http_candidate_registered": False,
            "positions_embedded": False,
            "presentation_v9_exactly_verified": True,
            "profitability_proven": False,
            "provenance_declaration_only": True,
            "raw_samples_recomputed": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "source_documents_embedded": False,
            "ui_mounted": False,
            "verification_contexts_embedded": False,
        },
        "gaps": {
            "adapter_v9_blocker_count": len(adapter_v9_document["blockers"]),
            "common_observation_basis_blocker_count": (
                1
                if adapter_components[
                    "common_observation_basis_gate_v1_status"
                ]
                == "BLOCK"
                else 0
            ),
            "local_blocker_count": 1 if local_blocked else 0,
            "presentation_blocker_count": len(PRESENTATION_BLOCKERS),
            "presentation_blockers": list(PRESENTATION_BLOCKERS),
            "source_failure": None,
        },
        "local_decision": local_decision,
        "multi_window_summary": deepcopy(presentation_multi),
        "policy": {
            "adapter_v9_block_overrides_presentation_v9_pass": True,
            "outer_status_always_block": True,
            "provenance_is_not_raw_sample_recomputation": True,
            "risk_reduction_is_not_execution_authority": True,
        },
        "risk_summary": deepcopy(presentation_v9_document["risk_summary"]),
        "schema_version": SCHEMA_VERSION,
        "source": {
            "adapter_v8_hash": presentation_source["adapter_v8_hash"],
            "adapter_v9_hash": adapter_v9_document["adapter_v9_hash"],
            "adapter_v9_implementation_sha256": ADAPTER_V9_IMPLEMENTATION_SHA256,
            "basis_evidence_hash": adapter_source["basis_evidence_hash"],
            "basis_preregistration_hash": adapter_source[
                "basis_preregistration_hash"
            ],
            "cluster_partition_hash": presentation_source[
                "cluster_partition_hash"
            ],
            "common_observation_basis_gate_v1_hash": adapter_source[
                "common_observation_basis_gate_v1_hash"
            ],
            "common_sample_set_hash": adapter_source["common_sample_set_hash"],
            "edge_gate_v1_hash": presentation_source["edge_gate_v1_hash"],
            "observation_policy_hash": adapter_source["observation_policy_hash"],
            "presentation_v9_hash": presentation_v9_document[
                "presentation_v9_hash"
            ],
            "presentation_v9_implementation_sha256": PRESENTATION_V9_IMPLEMENTATION_SHA256,
            "state": "EXACT_PRESENTATION_V9_AND_ADAPTER_V9",
            "strict_canonical_implementation_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
            "trade_identity_hash": presentation_source["trade_identity_hash"],
        },
        "stages": [
            {
                "axis": "SOURCE",
                "detail": "EXACT_PRESENTATION_V9_AND_ADAPTER_V9",
                "state": "KNOWN",
            },
            {
                "axis": "GAP",
                "detail": (
                    "LOCAL_RESEARCH_BLOCK_PRESENT"
                    if local_blocked
                    else "LOCAL_RESEARCH_CLEAR_GOVERNANCE_GAPS_REMAIN"
                ),
                "state": "OPEN" if local_blocked else "CLEAR_WITH_GOVERNANCE_GAPS",
            },
            {
                "axis": "MATURITY",
                "detail": "UNMOUNTED_PRESENTATION_CANDIDATE_V10",
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
    return seal_strict_canonical_document(document, "presentation_v10_hash")


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10(
    document: Any,
    presentation_v9_document: Any,
    adapter_v9_document: Any,
    *,
    presentation_v9_verification_context: Any,
    adapter_v9_verification_context: Any,
) -> dict[str, Any]:
    """Return a locked exact-rebuild receipt."""
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10(
            presentation_v9_document,
            adapter_v9_document,
            presentation_v9_verification_context=presentation_v9_verification_context,
            adapter_v9_verification_context=adapter_v9_verification_context,
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        expected = None
        exact = False
    return {
        "blockers": [] if exact else ["PRESENTATION_V10_EXACT_REBUILD_FAILED"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_v10_exactly_verified": exact,
        "presentation_v10_hash": expected["presentation_v10_hash"] if exact else None,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }


__all__ = [
    "ADAPTER_V9_IMPLEMENTATION_SHA256",
    "AXIS_ORDER",
    "PRESENTATION_BLOCKERS",
    "PRESENTATION_V9_IMPLEMENTATION_SHA256",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10",
]
