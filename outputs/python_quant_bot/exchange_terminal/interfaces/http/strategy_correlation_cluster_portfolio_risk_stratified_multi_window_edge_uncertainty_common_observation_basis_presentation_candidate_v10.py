"""Unmounted HTTP candidate for exact common-observation presentation-v10."""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10
    as presentation_v10,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "edge-uncertainty-common-observation-basis-presentation-http-candidate-"
    "request-v10"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "edge-uncertainty-common-observation-basis-presentation-http-candidate-"
    "response-v10"
)
PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "edge-uncertainty-common-observation-basis-presentation-http-payload-v10"
)
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "basis-presentation-http-candidate-v10-unmounted-lock-1"
)
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
KNOWN_BLOCKED_STATE = "KNOWN_BLOCKED"
UNKNOWN_STATE = "UNKNOWN"
PRESENTATION_V10_IMPLEMENTATION_SHA256 = (
    "85a317babc16b310b9c62639879a241b0bf206d33a4be460a8d98400fb71c22e"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
HTTP_CANDIDATE_BLOCKERS = (
    "HTTP_CANDIDATE_V10_UNREGISTERED",
    "PRESENTATION_V10_CONSUMER_NOT_REGISTERED",
    "CURRENT_ADMISSION_LOCKED",
    "UI_NOT_MOUNTED",
)

_VERIFY_PRESENTATION = (
    presentation_v10.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10
)
_REQUEST_KEYS = {
    "expected_presentation_v10_hash",
    "schema_version",
    "stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10_document",
}
_CONTEXT_KEYS = {
    "adapter_v9_document",
    "adapter_v9_verification_context",
    "presentation_v9_document",
    "presentation_v9_verification_context",
}
_RECEIPT_KEYS = {
    "blockers",
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "presentation_consumer_activation_allowed",
    "presentation_v10_exactly_verified",
    "presentation_v10_hash",
    "runtime_gate_activation_allowed",
    "schema_version",
    "status",
    "writer_allowed",
}
_PRESENTATION_KEYS = {
    "authority",
    "axis_order",
    "common_observation_summary",
    "decision",
    "edge_uncertainty_summary",
    "facts",
    "gaps",
    "local_decision",
    "multi_window_summary",
    "policy",
    "presentation_v10_hash",
    "risk_summary",
    "schema_version",
    "source",
    "stages",
    "static_fingerprint",
    "status",
}
_AUTHORITY_KEYS = {
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
    "adapter_v9_exactly_verified",
    "browser_review_performed",
    "common_observation_basis_projected",
    "cross_bindings_verified",
    "http_candidate_registered",
    "positions_embedded",
    "presentation_v9_exactly_verified",
    "profitability_proven",
    "provenance_declaration_only",
    "raw_samples_recomputed",
    "runtime_assets_accessed",
    "runtime_consumer_bound",
    "source_documents_embedded",
    "ui_mounted",
    "verification_contexts_embedded",
}
_GAP_KEYS = {
    "adapter_v9_blocker_count",
    "common_observation_basis_blocker_count",
    "local_blocker_count",
    "presentation_blocker_count",
    "presentation_blockers",
    "source_failure",
}
_LOCAL_KEYS = {
    "adapter_v8_decision",
    "adapter_v8_status",
    "adapter_v9_decision",
    "adapter_v9_status",
    "common_observation_basis_gate_v1_decision",
    "common_observation_basis_gate_v1_status",
    "edge_gate_v1_decision",
    "edge_gate_v1_status",
    "joint_decision",
    "joint_status",
    "presentation_v9_joint_decision",
    "presentation_v9_joint_status",
}
_COMMON_KEYS = {
    "all_pair_sample_counts_match",
    "common_sample_count",
    "edge_pair_count",
    "minimum_common_sample_count",
    "pair_count_matching_common_sample_count",
    "provenance_declaration_only",
    "raw_samples_recomputed",
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
_SOURCE_KEYS = {
    "adapter_v8_hash",
    "adapter_v9_hash",
    "adapter_v9_implementation_sha256",
    "basis_evidence_hash",
    "basis_preregistration_hash",
    "cluster_partition_hash",
    "common_observation_basis_gate_v1_hash",
    "common_sample_set_hash",
    "edge_gate_v1_hash",
    "observation_policy_hash",
    "presentation_v9_hash",
    "presentation_v9_implementation_sha256",
    "state",
    "strict_canonical_implementation_sha256",
    "trade_identity_hash",
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


def _number_text(value: Any) -> str:
    if not _is_non_negative_number(value):
        raise ValueError("summary number invalid")
    return "0" if value == 0 else format(value, ".15g")


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


def _source_authority_valid(value: Any) -> bool:
    if not _exact_keys(value, _AUTHORITY_KEYS):
        return False
    return (
        all(type(item) is bool for item in value.values())
        and value["descriptive_only"] is True
        and value["presentation_only"] is True
        and value["research_only"] is True
        and all(
            value[key] is False
            for key in _AUTHORITY_KEYS
            - {"descriptive_only", "presentation_only", "research_only"}
        )
    )


def _facts_valid(value: Any) -> bool:
    return (
        _exact_keys(value, _FACT_KEYS)
        and all(type(item) is bool for item in value.values())
        and value["adapter_v9_exactly_verified"] is True
        and value["common_observation_basis_projected"] is True
        and value["cross_bindings_verified"] is True
        and value["presentation_v9_exactly_verified"] is True
        and value["provenance_declaration_only"] is True
        and value["raw_samples_recomputed"] is False
        and all(
            value[key] is False
            for key in {
                "browser_review_performed",
                "http_candidate_registered",
                "positions_embedded",
                "profitability_proven",
                "runtime_assets_accessed",
                "runtime_consumer_bound",
                "source_documents_embedded",
                "ui_mounted",
                "verification_contexts_embedded",
            }
        )
    )


def _gaps_valid(value: Any) -> bool:
    if not _exact_keys(value, _GAP_KEYS):
        return False
    counts = [
        value["adapter_v9_blocker_count"],
        value["common_observation_basis_blocker_count"],
        value["local_blocker_count"],
        value["presentation_blocker_count"],
    ]
    return (
        all(_is_int(item, 0) for item in counts)
        and type(value["presentation_blockers"]) is list
        and all(
            type(item) is str and bool(item)
            for item in value["presentation_blockers"]
        )
        and value["presentation_blocker_count"]
        == len(value["presentation_blockers"])
        and value["source_failure"] is None
    )


def _local_valid(value: Any) -> bool:
    if not _exact_keys(value, _LOCAL_KEYS):
        return False
    return all(
        value[key] in {"PASS", "BLOCK"}
        for key in _LOCAL_KEYS
        if key.endswith("_status")
    ) and all(
        type(value[key]) is str and bool(value[key])
        for key in _LOCAL_KEYS
        if key.endswith("_decision")
    )


def _common_valid(value: Any) -> bool:
    return (
        _exact_keys(value, _COMMON_KEYS)
        and type(value["all_pair_sample_counts_match"]) is bool
        and _is_int(value["common_sample_count"], 1)
        and _is_int(value["edge_pair_count"], 1)
        and _is_int(value["minimum_common_sample_count"], 1)
        and _is_int(value["pair_count_matching_common_sample_count"], 0)
        and value["provenance_declaration_only"] is True
        and value["raw_samples_recomputed"] is False
        and value["all_pair_sample_counts_match"]
        == (
            value["pair_count_matching_common_sample_count"]
            == value["edge_pair_count"]
        )
    )


def _edge_valid(value: Any) -> bool:
    if not _exact_keys(value, _EDGE_KEYS):
        return False
    return (
        _is_hash(value["cluster_partition_hash"])
        and all(
            _is_int(value[key], 0)
            for key in {
                "blocked_pair_count",
                "insufficient_sample_pair_count",
                "observed_breach_pair_count",
                "uncertainty_overlap_pair_count",
                "verified_pair_count",
            }
        )
        and _is_int(value["confidence_z_micros"], 1)
        and _is_int(value["correlation_floor_micros"])
        and _is_int(value["maximum_confidence_upper_correlation_micros"])
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


def _source_valid(value: Any) -> bool:
    return (
        _exact_keys(value, _SOURCE_KEYS)
        and all(_is_hash(value[key]) for key in _SOURCE_KEYS - {"state"})
        and value["state"] == "EXACT_PRESENTATION_V9_AND_ADAPTER_V9"
        and value["adapter_v9_implementation_sha256"]
        == presentation_v10.ADAPTER_V9_IMPLEMENTATION_SHA256
        and value["presentation_v9_implementation_sha256"]
        == presentation_v10.PRESENTATION_V9_IMPLEMENTATION_SHA256
        and value["strict_canonical_implementation_sha256"]
        == STRICT_CANONICAL_IMPLEMENTATION_SHA256
    )


def _known_presentation(value: Any) -> bool:
    if not _exact_keys(value, _PRESENTATION_KEYS):
        return False
    stages = value["stages"]
    return (
        value["schema_version"] == presentation_v10.SCHEMA_VERSION
        and value["static_fingerprint"] == presentation_v10.STATIC_FINGERPRINT
        and value["status"] == "BLOCK"
        and _is_hash(value["presentation_v10_hash"])
        and value["axis_order"] == list(AXIS_ORDER)
        and _source_authority_valid(value["authority"])
        and _facts_valid(value["facts"])
        and _gaps_valid(value["gaps"])
        and _local_valid(value["local_decision"])
        and _common_valid(value["common_observation_summary"])
        and _edge_valid(value["edge_uncertainty_summary"])
        and _multi_valid(value["multi_window_summary"])
        and _risk_valid(value["risk_summary"])
        and _source_valid(value["source"])
        and value["edge_uncertainty_summary"]["cluster_partition_hash"]
        == value["source"]["cluster_partition_hash"]
        and type(value["policy"]) is dict
        and type(value["decision"]) is str
        and bool(value["decision"])
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


def _request_valid(value: Any) -> bool:
    if not _exact_keys(value, _REQUEST_KEYS):
        return False
    document = value[
        "stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10_document"
    ]
    expected_hash = value["expected_presentation_v10_hash"]
    return (
        value["schema_version"] == REQUEST_SCHEMA_VERSION
        and type(document) is dict
        and _is_hash(expected_hash)
        and document.get("presentation_v10_hash") == expected_hash
    )


def _receipt_valid(value: Any, expected_hash: str) -> bool:
    return (
        _exact_keys(value, _RECEIPT_KEYS)
        and value["schema_version"] == presentation_v10.VERIFICATION_SCHEMA_VERSION
        and value["status"] == "PASS"
        and value["blockers"] == []
        and value["presentation_v10_exactly_verified"] is True
        and value["presentation_v10_hash"] == expected_hash
        and value["current_admission_allowed"] is False
        and value["live_order_allowed"] is False
        and value["paper_authorized"] is False
        and value["presentation_consumer_activation_allowed"] is False
        and value["runtime_gate_activation_allowed"] is False
        and value["writer_allowed"] is False
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
    source = presentation["source"]
    document = {
        "authority": _authority(),
        "common_observation_summary": deepcopy(
            presentation["common_observation_summary"]
        ),
        "decision": "EXACT_PRESENTATION_V10_PROJECTED_AUTHORITY_UNCHANGED",
        "edge_uncertainty_summary": deepcopy(
            presentation["edge_uncertainty_summary"]
        ),
        "facts": {
            "adapter_v9_exactly_verified": True,
            "common_observation_basis_projected": True,
            "edge_uncertainty_summary_projected": True,
            "matrices_embedded": False,
            "multi_window_summary_projected": True,
            "positions_embedded": False,
            "presentation_v9_exactly_verified": True,
            "profitability_proven": False,
            "provenance_declaration_only": True,
            "raw_samples_recomputed": False,
            "runtime_consumer_bound": False,
            "source_documents_embedded": False,
            "ui_mounted": False,
            "verification_contexts_embedded": False,
        },
        "gaps": {
            "adapter_v9_blocker_count": presentation["gaps"][
                "adapter_v9_blocker_count"
            ],
            "common_observation_basis_blocker_count": presentation["gaps"][
                "common_observation_basis_blocker_count"
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
            "adapter_v9_hash": source["adapter_v9_hash"],
            "basis_evidence_hash": source["basis_evidence_hash"],
            "basis_preregistration_hash": source["basis_preregistration_hash"],
            "cluster_partition_hash": source["cluster_partition_hash"],
            "common_observation_basis_gate_v1_hash": source[
                "common_observation_basis_gate_v1_hash"
            ],
            "common_sample_set_hash": source["common_sample_set_hash"],
            "edge_gate_v1_hash": source["edge_gate_v1_hash"],
            "observation_policy_hash": source["observation_policy_hash"],
            "presentation_v10_hash": presentation["presentation_v10_hash"],
            "presentation_v9_hash": source["presentation_v9_hash"],
            "state": source["state"],
            "trade_identity_hash": source["trade_identity_hash"],
        },
        "stages": [
            deepcopy(presentation["stages"][0]),
            deepcopy(presentation["stages"][1]),
            {
                "axis": "MATURITY",
                "detail": "UNMOUNTED_HTTP_CANDIDATE_V10",
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
            "presentation_v10_exactly_verified": known,
            "profitability_proven": False,
            "provenance_declaration_only": True,
            "raw_samples_recomputed": False,
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
            "presentation_v10_hash": source_hash if known else None,
            "presentation_v10_implementation_sha256": PRESENTATION_V10_IMPLEMENTATION_SHA256,
            "presentation_v10_schema_version": presentation_v10.SCHEMA_VERSION,
            "presentation_v10_static_fingerprint": presentation_v10.STATIC_FINGERPRINT,
            "strict_canonical_implementation_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
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


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
    request_payload: Any,
    *,
    presentation_verification_context: Any,
) -> dict[str, Any]:
    """Build a sealed display candidate without registering transport."""
    request_valid = _request_valid(request_payload)
    context_valid = _exact_keys(presentation_verification_context, _CONTEXT_KEYS)
    if not request_valid or not context_valid:
        return _unknown(
            "REQUEST_OR_CONTEXT_CONTRACT_INVALID",
            request_valid=request_valid,
            context_valid=context_valid,
        )
    presentation = request_payload[
        "stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10_document"
    ]
    expected_hash = request_payload["expected_presentation_v10_hash"]
    context = presentation_verification_context
    try:
        receipt = _VERIFY_PRESENTATION(
            presentation,
            context["presentation_v9_document"],
            context["adapter_v9_document"],
            presentation_v9_verification_context=context[
                "presentation_v9_verification_context"
            ],
            adapter_v9_verification_context=context[
                "adapter_v9_verification_context"
            ],
        )
    except (KeyError, TypeError, ValueError):
        receipt = None
    if not _receipt_valid(receipt, expected_hash):
        return _unknown(
            "PRESENTATION_V10_EXACT_REBUILD_FAILED",
            request_valid=True,
            context_valid=True,
        )
    if not _known_presentation(presentation):
        return _unknown(
            "PRESENTATION_V10_SOURCE_UNKNOWN",
            request_valid=True,
            context_valid=True,
        )
    try:
        payload = _payload(presentation)
    except (KeyError, TypeError, ValueError):
        return _unknown(
            "PRESENTATION_V10_PROJECTION_FAILED",
            request_valid=True,
            context_valid=True,
        )
    blockers = list(HTTP_CANDIDATE_BLOCKERS)
    local = presentation["local_decision"]
    common = presentation["common_observation_summary"]
    edge = presentation["edge_uncertainty_summary"]
    if local["joint_status"] == "BLOCK":
        blockers.append("LOCAL_RESEARCH_GATE_BLOCKED")
    if presentation["multi_window_summary"]["any_registered_window_blocked"]:
        blockers.append("MULTI_WINDOW_STABILITY_GATE_BLOCKED")
    if edge["blocked_pair_count"] > 0 or local["edge_gate_v1_status"] == "BLOCK":
        blockers.append("CROSS_CLUSTER_EDGE_UNCERTAINTY_GATE_BLOCKED")
    if (
        local["common_observation_basis_gate_v1_status"] == "BLOCK"
        or not common["all_pair_sample_counts_match"]
    ):
        blockers.append("COMMON_OBSERVATION_BASIS_GATE_BLOCKED")
    return _response(
        state=KNOWN_BLOCKED_STATE,
        payload=payload,
        blockers=blockers,
        request_valid=True,
        context_valid=True,
        source_hash=expected_hash,
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
    response: Any,
    request_payload: Any,
    *,
    presentation_verification_context: Any,
) -> bool:
    """Verify exact rebuild without granting route or mount authority."""
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
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
    "PRESENTATION_V10_IMPLEMENTATION_SHA256",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATE",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10",
]
