"""Unmounted HTTP candidate for exact edge-uncertainty presentation-v9.

This module defines no route, transport, registry, current selector, writer,
scheduler, or runtime binding. It accepts an exact presentation-v9 and the two
source documents plus verification contexts required to rebuild it, then
projects only bounded aggregate display evidence. Any malformed, substituted,
or unknown source returns no payload and no partial summary.
"""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9
    as presentation_v9,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "edge-uncertainty-presentation-http-candidate-request-v9"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "edge-uncertainty-presentation-http-candidate-response-v9"
)
PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "edge-uncertainty-presentation-http-payload-v9"
)
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-presentation-http-"
    "candidate-v9-unmounted-lock-1"
)
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
KNOWN_BLOCKED_STATE = "KNOWN_BLOCKED"
UNKNOWN_STATE = "UNKNOWN"
PRESENTATION_V9_IMPLEMENTATION_SHA256 = (
    "5fb7af67366913016c79236419f9b8df356a6b809ec876e0c312a67a4839b132"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
HTTP_CANDIDATE_BLOCKERS = (
    "HTTP_CANDIDATE_V9_UNREGISTERED",
    "PRESENTATION_V9_CONSUMER_NOT_REGISTERED",
    "CURRENT_ADMISSION_LOCKED",
    "UI_NOT_MOUNTED",
)

_VERIFY_PRESENTATION = (
    presentation_v9.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9
)
_REQUEST_KEYS = {
    "schema_version",
    "stratified_multi_window_edge_uncertainty_presentation_v9_document",
    "expected_presentation_v9_hash",
}
_CONTEXT_KEYS = {
    "presentation_v8_document",
    "adapter_v8_document",
    "presentation_v8_verification_context",
    "adapter_v8_verification_context",
}
_PRESENTATION_KEYS = {
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
_SOURCE_AUTHORITY_KEYS = {
    "current_admission_allowed",
    "current_pointer_written",
    "descriptive_only",
    "formal_registry_activation_allowed",
    "http_candidate_creation_allowed",
    "live_order_allowed",
    "paper_authorized",
    "presentation_consumer_activation_allowed",
    "presentation_only",
    "research_only",
    "runtime_gate_activation_allowed",
    "writer_allowed",
}
_FACT_KEYS = {
    "adapter_v8_exactly_verified",
    "browser_review_performed",
    "cross_bindings_verified",
    "http_candidate_registered",
    "positions_embedded",
    "presentation_v8_exactly_verified",
    "profitability_proven",
    "runtime_assets_accessed",
    "runtime_consumer_bound",
    "source_documents_embedded",
    "ui_mounted",
    "verification_contexts_embedded",
}
_GAP_KEYS = {
    "adapter_v8_blocker_count",
    "edge_uncertainty_blocker_count",
    "local_blocker_count",
    "presentation_blocker_count",
    "presentation_blockers",
    "source_failure",
}
_LOCAL_KEYS = {
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
_SOURCE_KEYS = {
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
_RECEIPT_KEYS = {
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


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return type(value) is dict and set(value) == expected


def _is_hash(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_non_negative_number(value: Any) -> bool:
    if isinstance(value, bool) or type(value) not in {int, float}:
        return False
    if type(value) is float and not math.isfinite(value):
        return False
    return value >= 0


def _is_int(value: Any, *, minimum: int | None = None, maximum: int | None = None) -> bool:
    if type(value) is not int or isinstance(value, bool):
        return False
    if minimum is not None and value < minimum:
        return False
    if maximum is not None and value > maximum:
        return False
    return True


def _number_text(value: Any) -> str:
    if not _is_non_negative_number(value):
        raise ValueError("summary number invalid")
    if value == 0:
        return "0"
    return format(value, ".15g")


def _authority() -> dict[str, bool]:
    return {
        "consumer_activation_allowed": False,
        "current_admission_allowed": False,
        "descriptive_only": True,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mount_allowed": False,
        "route_registration_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def _request_valid(value: Any) -> bool:
    if not _exact_keys(value, _REQUEST_KEYS):
        return False
    document = value[
        "stratified_multi_window_edge_uncertainty_presentation_v9_document"
    ]
    expected_hash = value["expected_presentation_v9_hash"]
    return (
        value["schema_version"] == REQUEST_SCHEMA_VERSION
        and type(document) is dict
        and _is_hash(expected_hash)
        and document.get("presentation_v9_hash") == expected_hash
    )


def _context_valid(value: Any) -> bool:
    return _exact_keys(value, _CONTEXT_KEYS)


def _receipt_valid(value: Any, expected_hash: str) -> bool:
    if not _exact_keys(value, _RECEIPT_KEYS):
        return False
    return (
        value["schema_version"] == presentation_v9.VERIFICATION_SCHEMA_VERSION
        and value["status"] == "PASS"
        and value["blockers"] == []
        and value["presentation_v9_exactly_verified"] is True
        and value["presentation_v9_hash"] == expected_hash
        and value["current_admission_allowed"] is False
        and value["live_order_allowed"] is False
        and value["paper_authorized"] is False
        and value["presentation_consumer_activation_allowed"] is False
        and value["runtime_gate_activation_allowed"] is False
        and value["writer_allowed"] is False
    )


def _source_authority_valid(value: Any) -> bool:
    if not _exact_keys(value, _SOURCE_AUTHORITY_KEYS):
        return False
    if not all(type(item) is bool for item in value.values()):
        return False
    return (
        value["descriptive_only"] is True
        and value["presentation_only"] is True
        and value["research_only"] is True
        and value["current_admission_allowed"] is False
        and value["current_pointer_written"] is False
        and value["formal_registry_activation_allowed"] is False
        and value["http_candidate_creation_allowed"] is False
        and value["live_order_allowed"] is False
        and value["paper_authorized"] is False
        and value["presentation_consumer_activation_allowed"] is False
        and value["runtime_gate_activation_allowed"] is False
        and value["writer_allowed"] is False
    )


def _facts_valid(value: Any) -> bool:
    if not _exact_keys(value, _FACT_KEYS):
        return False
    if not all(type(item) is bool for item in value.values()):
        return False
    return (
        value["adapter_v8_exactly_verified"] is True
        and value["cross_bindings_verified"] is True
        and value["presentation_v8_exactly_verified"] is True
        and value["browser_review_performed"] is False
        and value["http_candidate_registered"] is False
        and value["positions_embedded"] is False
        and value["profitability_proven"] is False
        and value["runtime_assets_accessed"] is False
        and value["runtime_consumer_bound"] is False
        and value["source_documents_embedded"] is False
        and value["ui_mounted"] is False
        and value["verification_contexts_embedded"] is False
    )


def _gaps_valid(value: Any) -> bool:
    if not _exact_keys(value, _GAP_KEYS):
        return False
    counts = (
        value["adapter_v8_blocker_count"],
        value["edge_uncertainty_blocker_count"],
        value["local_blocker_count"],
        value["presentation_blocker_count"],
    )
    blockers = value["presentation_blockers"]
    return (
        all(_is_int(item, minimum=0) for item in counts)
        and type(blockers) is list
        and all(type(item) is str and bool(item) for item in blockers)
        and value["presentation_blocker_count"] == len(blockers)
        and value["source_failure"] is None
    )


def _local_valid(value: Any) -> bool:
    if not _exact_keys(value, _LOCAL_KEYS):
        return False
    status_keys = [key for key in _LOCAL_KEYS if key.endswith("_status")]
    decision_keys = [key for key in _LOCAL_KEYS if key.endswith("_decision")]
    return (
        all(value[key] in {"PASS", "BLOCK"} for key in status_keys)
        and all(type(value[key]) is str and bool(value[key]) for key in decision_keys)
    )


def _dimension_valid(value: Any) -> bool:
    if not _exact_keys(value, _DIMENSION_KEYS):
        return False
    return (
        type(value["dimension_id"]) is str
        and bool(value["dimension_id"])
        and type(value["dominant_stratum_id"]) is str
        and bool(value["dominant_stratum_id"])
        and _is_int(value["active_stratum_count"], minimum=0)
        and _is_int(value["over_limit_stratum_count"], minimum=0)
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
    if not _exact_keys(value, _RISK_KEYS):
        return False
    rows = value["dimension_results"]
    return (
        _is_int(value["active_dimension_count"], minimum=0)
        and type(rows) is list
        and value["active_dimension_count"] == len(rows)
        and all(_dimension_valid(row) for row in rows)
        and _is_non_negative_number(
            value["conservative_weighted_effective_strata_count"]
        )
        and _is_non_negative_number(value["maximum_active_stratum_gross_pct"])
        and _is_non_negative_number(value["total_active_gross_pct"])
        and _is_non_negative_number(value["v2_weighted_effective_cluster_count"])
        and type(value["weighted_diversification_gate_applied"]) is bool
    )


def _multi_window_valid(value: Any) -> bool:
    if not _exact_keys(value, _MULTI_WINDOW_KEYS):
        return False
    registered = value["registered_window_count"]
    verified = value["verified_window_count"]
    return (
        type(value["anchor_window_id"]) is str
        and bool(value["anchor_window_id"])
        and _is_int(registered, minimum=1)
        and _is_int(verified, minimum=1)
        and verified == registered
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
    count_keys = {
        "blocked_pair_count",
        "insufficient_sample_pair_count",
        "observed_breach_pair_count",
        "uncertainty_overlap_pair_count",
        "verified_pair_count",
    }
    return (
        all(_is_int(value[key], minimum=0) for key in count_keys)
        and _is_hash(value["cluster_partition_hash"])
        and _is_int(
            value["correlation_floor_micros"], minimum=-1_000_000, maximum=1_000_000
        )
        and _is_int(value["confidence_z_micros"], minimum=1)
        and _is_int(
            value["maximum_confidence_upper_correlation_micros"],
            minimum=-1_000_000,
            maximum=1_000_000,
        )
    )


def _source_valid(value: Any) -> bool:
    if not _exact_keys(value, _SOURCE_KEYS):
        return False
    hash_keys = [key for key in _SOURCE_KEYS if key != "state"]
    return (
        all(_is_hash(value[key]) for key in hash_keys)
        and value["state"] == "EXACT_PRESENTATION_V8_AND_ADAPTER_V8"
        and value["adapter_v8_implementation_sha256"]
        == presentation_v9.ADAPTER_V8_IMPLEMENTATION_SHA256
        and value["presentation_v8_implementation_sha256"]
        == presentation_v9.PRESENTATION_V8_IMPLEMENTATION_SHA256
        and value["strict_canonical_implementation_sha256"]
        == STRICT_CANONICAL_IMPLEMENTATION_SHA256
    )


def _known_presentation(value: Any) -> bool:
    if not _exact_keys(value, _PRESENTATION_KEYS):
        return False
    stages = value["stages"]
    return (
        value["schema_version"] == presentation_v9.SCHEMA_VERSION
        and value["static_fingerprint"] == presentation_v9.STATIC_FINGERPRINT
        and value["status"] == "BLOCK"
        and _is_hash(value["presentation_v9_hash"])
        and value["axis_order"] == list(AXIS_ORDER)
        and type(value["decision"]) is str
        and bool(value["decision"])
        and type(value["policy"]) is dict
        and _source_authority_valid(value["authority"])
        and _facts_valid(value["facts"])
        and _gaps_valid(value["gaps"])
        and _local_valid(value["local_decision"])
        and _multi_window_valid(value["multi_window_summary"])
        and _risk_valid(value["risk_summary"])
        and _edge_valid(value["edge_uncertainty_summary"])
        and _source_valid(value["source"])
        and value["edge_uncertainty_summary"]["cluster_partition_hash"]
        == value["source"]["cluster_partition_hash"]
        and type(stages) is list
        and len(stages) == len(AXIS_ORDER)
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


def _project_dimension(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "active_stratum_count": value["active_stratum_count"],
        "dimension_id": value["dimension_id"],
        "diversification_status": value["diversification_status"],
        "dominant_stratum_id": value["dominant_stratum_id"],
        "dominant_stratum_share_of_active_gross_pct": _number_text(
            value["dominant_stratum_share_of_active_gross_pct"]
        ),
        "gross_limit_status": value["gross_limit_status"],
        "maximum_stratum_gross_pct": _number_text(value["maximum_stratum_gross_pct"]),
        "over_limit_stratum_count": value["over_limit_stratum_count"],
        "status": value["status"],
        "weighted_effective_strata_count": _number_text(
            value["weighted_effective_strata_count"]
        ),
    }


def _payload(presentation: dict[str, Any]) -> dict[str, Any]:
    risk = presentation["risk_summary"]
    multi = presentation["multi_window_summary"]
    edge = presentation["edge_uncertainty_summary"]
    source = presentation["source"]
    document = {
        "authority": _authority(),
        "decision": "EXACT_PRESENTATION_V9_PROJECTED_AUTHORITY_UNCHANGED",
        "edge_uncertainty_summary": deepcopy(edge),
        "facts": {
            "adapter_v8_exactly_verified": True,
            "edge_uncertainty_summary_projected": True,
            "matrices_embedded": False,
            "multi_window_summary_projected": True,
            "positions_embedded": False,
            "presentation_v8_exactly_verified": True,
            "profitability_proven": False,
            "runtime_consumer_bound": False,
            "source_documents_embedded": False,
            "ui_mounted": False,
            "verification_contexts_embedded": False,
        },
        "gaps": {
            "adapter_v8_blocker_count": presentation["gaps"][
                "adapter_v8_blocker_count"
            ],
            "edge_uncertainty_blocker_count": presentation["gaps"][
                "edge_uncertainty_blocker_count"
            ],
            "http_candidate_blocker_count": len(HTTP_CANDIDATE_BLOCKERS),
            "http_candidate_blockers": list(HTTP_CANDIDATE_BLOCKERS),
            "local_blocker_count": presentation["gaps"]["local_blocker_count"],
            "presentation_blocker_count": presentation["gaps"][
                "presentation_blocker_count"
            ],
            "presentation_blockers": deepcopy(
                presentation["gaps"]["presentation_blockers"]
            ),
        },
        "local_decision": deepcopy(presentation["local_decision"]),
        "multi_window_summary": {
            "anchor_window_id": multi["anchor_window_id"],
            "any_registered_window_blocked": multi["any_registered_window_blocked"],
            "cluster_partition_stable": multi["cluster_partition_stable"],
            "minimum_conservative_weighted_effective_strata_count": _number_text(
                multi["minimum_conservative_weighted_effective_strata_count"]
            ),
            "registered_window_count": multi["registered_window_count"],
            "strata_topology_stable": multi["strata_topology_stable"],
            "verified_window_count": multi["verified_window_count"],
            "worst_window_maximum_active_stratum_gross_pct": _number_text(
                multi["worst_window_maximum_active_stratum_gross_pct"]
            ),
        },
        "risk_summary": {
            "active_dimension_count": risk["active_dimension_count"],
            "conservative_weighted_effective_strata_count": _number_text(
                risk["conservative_weighted_effective_strata_count"]
            ),
            "dimension_results": [
                _project_dimension(row) for row in risk["dimension_results"]
            ],
            "maximum_active_stratum_gross_pct": _number_text(
                risk["maximum_active_stratum_gross_pct"]
            ),
            "total_active_gross_pct": _number_text(risk["total_active_gross_pct"]),
            "v2_weighted_effective_cluster_count": _number_text(
                risk["v2_weighted_effective_cluster_count"]
            ),
            "weighted_diversification_gate_applied": risk[
                "weighted_diversification_gate_applied"
            ],
        },
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "source": {
            "adapter_v7_hash": source["adapter_v7_hash"],
            "adapter_v8_hash": source["adapter_v8_hash"],
            "cluster_partition_hash": source["cluster_partition_hash"],
            "edge_gate_v1_hash": source["edge_gate_v1_hash"],
            "presentation_v8_hash": source["presentation_v8_hash"],
            "presentation_v9_hash": presentation["presentation_v9_hash"],
            "stability_gate_v2_hash": source["stability_gate_v2_hash"],
            "state": source["state"],
            "trade_identity_hash": source["trade_identity_hash"],
        },
        "stages": [
            deepcopy(presentation["stages"][0]),
            deepcopy(presentation["stages"][1]),
            {
                "axis": "MATURITY",
                "detail": "UNMOUNTED_HTTP_CANDIDATE_V9",
                "state": "CANDIDATE_ONLY",
            },
            {
                "axis": "PERMISSION",
                "detail": "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY",
                "state": "UNAUTHORIZED",
            },
        ],
        "status": "BLOCK",
    }
    return seal_strict_canonical_document(document, "payload_hash")


def _response(
    *,
    state: str,
    payload: dict[str, Any] | None,
    blockers: list[str],
    request_valid: bool,
    context_valid: bool,
    source_hash: str | None,
) -> dict[str, Any]:
    known = state == KNOWN_BLOCKED_STATE
    document = {
        "authority": _authority(),
        "blockers": blockers,
        "facts": {
            "context_contract_valid": context_valid,
            "presentation_v9_exactly_verified": known,
            "profitability_proven": False,
            "request_contract_valid": request_valid,
            "result_available": known,
            "route_registered": False,
            "runtime_mutations_performed": False,
            "source_contract_known": known,
            "transport_registered": False,
            "ui_mounted": False,
        },
        "interface_status": INTERFACE_STATUS,
        "lineage": {
            "presentation_v9_hash": source_hash if known else None,
            "presentation_v9_implementation_sha256": (
                PRESENTATION_V9_IMPLEMENTATION_SHA256
            ),
            "presentation_v9_schema_version": presentation_v9.SCHEMA_VERSION,
            "presentation_v9_static_fingerprint": presentation_v9.STATIC_FINGERPRINT,
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "payload": payload,
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "state": state,
        "static_fingerprint": STATIC_FINGERPRINT,
    }
    return seal_strict_canonical_document(document, "response_hash")


def _unknown(reason: str, *, request_valid: bool, context_valid: bool) -> dict[str, Any]:
    return _response(
        state=UNKNOWN_STATE,
        payload=None,
        blockers=sorted(set(HTTP_CANDIDATE_BLOCKERS + (reason,))),
        request_valid=request_valid,
        context_valid=context_valid,
        source_hash=None,
    )


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
    request_payload: Any,
    *,
    presentation_verification_context: Any,
) -> dict[str, Any]:
    """Build a sealed display candidate without registering any transport."""
    request_valid = _request_valid(request_payload)
    context_valid = _context_valid(presentation_verification_context)
    if not request_valid or not context_valid:
        return _unknown(
            "REQUEST_OR_CONTEXT_CONTRACT_INVALID",
            request_valid=request_valid,
            context_valid=context_valid,
        )

    presentation = request_payload[
        "stratified_multi_window_edge_uncertainty_presentation_v9_document"
    ]
    expected_hash = request_payload["expected_presentation_v9_hash"]
    try:
        receipt = _VERIFY_PRESENTATION(
            presentation,
            presentation_verification_context["presentation_v8_document"],
            presentation_verification_context["adapter_v8_document"],
            presentation_v8_verification_context=presentation_verification_context[
                "presentation_v8_verification_context"
            ],
            adapter_v8_verification_context=presentation_verification_context[
                "adapter_v8_verification_context"
            ],
        )
    except (KeyError, TypeError, ValueError):
        receipt = None
    if not _receipt_valid(receipt, expected_hash):
        return _unknown(
            "PRESENTATION_V9_EXACT_REBUILD_FAILED",
            request_valid=True,
            context_valid=True,
        )
    if not _known_presentation(presentation):
        return _unknown(
            "PRESENTATION_V9_SOURCE_UNKNOWN",
            request_valid=True,
            context_valid=True,
        )
    try:
        payload = _payload(presentation)
    except (KeyError, TypeError, ValueError):
        return _unknown(
            "PRESENTATION_V9_PROJECTION_FAILED",
            request_valid=True,
            context_valid=True,
        )

    blockers = list(HTTP_CANDIDATE_BLOCKERS)
    if presentation["local_decision"]["joint_status"] == "BLOCK":
        blockers.append("LOCAL_RESEARCH_GATE_BLOCKED")
    if presentation["multi_window_summary"]["any_registered_window_blocked"]:
        blockers.append("MULTI_WINDOW_STABILITY_GATE_BLOCKED")
    if (
        presentation["local_decision"]["edge_gate_v1_status"] == "BLOCK"
        or presentation["edge_uncertainty_summary"]["blocked_pair_count"] > 0
    ):
        blockers.append("CROSS_CLUSTER_EDGE_UNCERTAINTY_GATE_BLOCKED")
    return _response(
        state=KNOWN_BLOCKED_STATE,
        payload=payload,
        blockers=blockers,
        request_valid=True,
        context_valid=True,
        source_hash=expected_hash,
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
    response: Any,
    request_payload: Any,
    *,
    presentation_verification_context: Any,
) -> bool:
    """Verify an exact rebuild without granting transport or mount authority."""
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
            request_payload,
            presentation_verification_context=presentation_verification_context,
        )
        return strict_json_contract_equal(response, expected)
    except (KeyError, TypeError, ValueError):
        return False


__all__ = [
    "AXIS_ORDER",
    "HTTP_CANDIDATE_BLOCKERS",
    "INTERFACE_STATUS",
    "KNOWN_BLOCKED_STATE",
    "PAYLOAD_SCHEMA_VERSION",
    "PRESENTATION_V9_IMPLEMENTATION_SHA256",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATE",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9",
]
