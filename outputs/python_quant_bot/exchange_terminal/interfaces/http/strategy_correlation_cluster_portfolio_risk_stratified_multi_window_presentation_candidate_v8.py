"""Unmounted HTTP candidate for exact stratified multi-window presentation-v8.

This module defines no route, transport, registry, current selector, or runtime
binding. It accepts an exact presentation-v8 plus the two source documents and
verification contexts required to rebuild that presentation, then projects only
bounded display aggregates. Unknown, malformed, or substituted sources return
no payload and no partial risk or multi-window summary.
"""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8
    as presentation_v8,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "presentation-http-candidate-request-v8"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "presentation-http-candidate-response-v8"
)
PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
    "presentation-http-payload-v8"
)
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-presentation-http-candidate-v8-"
    "unmounted-lock-1"
)
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
KNOWN_BLOCKED_STATE = "KNOWN_BLOCKED"
UNKNOWN_STATE = "UNKNOWN"
PRESENTATION_V8_IMPLEMENTATION_SHA256 = (
    "f2720ff7b2b32e7ffdf4c83502b1fa65f83ceb3ee8806dae94b0aaf71fd8ba6b"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
HTTP_CANDIDATE_BLOCKERS = (
    "HTTP_CANDIDATE_V8_UNREGISTERED",
    "PRESENTATION_V8_CONSUMER_NOT_REGISTERED",
    "CURRENT_ADMISSION_LOCKED",
    "UI_NOT_MOUNTED",
)

_VERIFY_PRESENTATION = (
    presentation_v8.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8
)
_REQUEST_KEYS = {
    "schema_version",
    "stratified_multi_window_presentation_v8_document",
    "expected_presentation_v8_hash",
}
_CONTEXT_KEYS = {
    "presentation_v7_document",
    "adapter_v7_document",
    "presentation_v7_verification_context",
    "adapter_v7_verification_context",
}
_PRESENTATION_KEYS = {
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
    "adapter_v7_exactly_verified",
    "anchor_budget_cross_bound",
    "browser_review_performed",
    "http_candidate_registered",
    "multi_window_summary_projected",
    "positions_embedded",
    "presentation_v7_exactly_verified",
    "profitability_proven",
    "runtime_assets_accessed",
    "runtime_consumer_bound",
    "source_documents_embedded",
    "ui_mounted",
    "verification_contexts_embedded",
}
_GAP_KEYS = {
    "local_blocker_count",
    "multi_window_blocker_count",
    "presentation_blocker_count",
    "presentation_blockers",
}
_LOCAL_KEYS = {
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
_RECEIPT_KEYS = {
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


def _number_text(value: Any) -> str:
    """Project verified non-negative numbers without cross-runtime floats."""
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
    document = value["stratified_multi_window_presentation_v8_document"]
    expected_hash = value["expected_presentation_v8_hash"]
    return (
        value["schema_version"] == REQUEST_SCHEMA_VERSION
        and type(document) is dict
        and _is_hash(expected_hash)
        and document.get("presentation_v8_hash") == expected_hash
    )


def _context_valid(value: Any) -> bool:
    return _exact_keys(value, _CONTEXT_KEYS)


def _receipt_valid(value: Any, expected_hash: str) -> bool:
    if not _exact_keys(value, _RECEIPT_KEYS):
        return False
    return (
        value["schema_version"] == presentation_v8.VERIFICATION_SCHEMA_VERSION
        and value["status"] == "PASS"
        and value["blockers"] == []
        and value["presentation_v8_exactly_verified"] is True
        and value["presentation_v8_hash"] == expected_hash
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
        value["adapter_v7_exactly_verified"] is True
        and value["anchor_budget_cross_bound"] is True
        and value["multi_window_summary_projected"] is True
        and value["presentation_v7_exactly_verified"] is True
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
        value["local_blocker_count"],
        value["multi_window_blocker_count"],
        value["presentation_blocker_count"],
    )
    return (
        all(type(item) is int and not isinstance(item, bool) and item >= 0 for item in counts)
        and type(value["presentation_blockers"]) is list
        and all(type(item) is str and bool(item) for item in value["presentation_blockers"])
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
        and type(value["active_stratum_count"]) is int
        and not isinstance(value["active_stratum_count"], bool)
        and value["active_stratum_count"] >= 0
        and type(value["over_limit_stratum_count"]) is int
        and not isinstance(value["over_limit_stratum_count"], bool)
        and value["over_limit_stratum_count"] >= 0
        and value["diversification_status"] in {"PASS", "BLOCK", "NOT_APPLICABLE"}
        and value["gross_limit_status"] in {"PASS", "BLOCK"}
        and value["status"] in {"PASS", "BLOCK"}
        and _is_non_negative_number(value["dominant_stratum_share_of_active_gross_pct"])
        and _is_non_negative_number(value["maximum_stratum_gross_pct"])
        and _is_non_negative_number(value["weighted_effective_strata_count"])
    )


def _risk_valid(value: Any) -> bool:
    if not _exact_keys(value, _RISK_KEYS):
        return False
    rows = value["dimension_results"]
    return (
        type(value["active_dimension_count"]) is int
        and not isinstance(value["active_dimension_count"], bool)
        and value["active_dimension_count"] >= 0
        and type(rows) is list
        and value["active_dimension_count"] == len(rows)
        and all(_dimension_valid(row) for row in rows)
        and _is_non_negative_number(value["conservative_weighted_effective_strata_count"])
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
        and type(registered) is int
        and not isinstance(registered, bool)
        and registered > 0
        and type(verified) is int
        and not isinstance(verified, bool)
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


def _source_valid(value: Any) -> bool:
    if not _exact_keys(value, _SOURCE_KEYS):
        return False
    hash_keys = [key for key in _SOURCE_KEYS if key.endswith("_hash")]
    implementation_keys = [
        key for key in _SOURCE_KEYS if key.endswith("_implementation_sha256")
    ]
    return (
        all(_is_hash(value[key]) for key in hash_keys + implementation_keys)
        and type(value["state"]) is str
        and value["state"].startswith("EXACT_")
    )


def _known_presentation(value: Any) -> bool:
    if not _exact_keys(value, _PRESENTATION_KEYS):
        return False
    stages = value["stages"]
    return (
        value["schema_version"] == presentation_v8.SCHEMA_VERSION
        and value["static_fingerprint"] == presentation_v8.STATIC_FINGERPRINT
        and value["status"] == "BLOCK"
        and _is_hash(value["presentation_v8_hash"])
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
        and _source_valid(value["source"])
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
    source = presentation["source"]
    document = {
        "authority": _authority(),
        "decision": "EXACT_PRESENTATION_V8_PROJECTED_AUTHORITY_UNCHANGED",
        "facts": {
            "adapter_v7_exactly_verified": True,
            "matrices_embedded": False,
            "multi_window_summary_projected": True,
            "positions_embedded": False,
            "presentation_v7_exactly_verified": True,
            "profitability_proven": False,
            "runtime_consumer_bound": False,
            "source_documents_embedded": False,
            "ui_mounted": False,
            "verification_contexts_embedded": False,
        },
        "gaps": {
            "http_candidate_blocker_count": len(HTTP_CANDIDATE_BLOCKERS),
            "http_candidate_blockers": list(HTTP_CANDIDATE_BLOCKERS),
            "local_blocker_count": presentation["gaps"]["local_blocker_count"],
            "multi_window_blocker_count": presentation["gaps"][
                "multi_window_blocker_count"
            ],
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
            "presentation_v7_hash": source["presentation_v7_hash"],
            "presentation_v8_hash": presentation["presentation_v8_hash"],
            "stability_gate_v2_hash": source["stability_gate_v2_hash"],
            "state": source["state"],
            "trade_identity_hash": source["trade_identity_hash"],
        },
        "stages": [
            deepcopy(presentation["stages"][0]),
            deepcopy(presentation["stages"][1]),
            {
                "axis": "MATURITY",
                "detail": "UNMOUNTED_HTTP_CANDIDATE_V8",
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
            "presentation_v8_exactly_verified": known,
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
            "presentation_v8_hash": source_hash if known else None,
            "presentation_v8_implementation_sha256": (
                PRESENTATION_V8_IMPLEMENTATION_SHA256
            ),
            "presentation_v8_schema_version": presentation_v8.SCHEMA_VERSION,
            "presentation_v8_static_fingerprint": presentation_v8.STATIC_FINGERPRINT,
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


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
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
        "stratified_multi_window_presentation_v8_document"
    ]
    expected_hash = request_payload["expected_presentation_v8_hash"]
    try:
        receipt = _VERIFY_PRESENTATION(
            presentation,
            presentation_verification_context["presentation_v7_document"],
            presentation_verification_context["adapter_v7_document"],
            presentation_v7_verification_context=presentation_verification_context[
                "presentation_v7_verification_context"
            ],
            adapter_v7_verification_context=presentation_verification_context[
                "adapter_v7_verification_context"
            ],
        )
    except (KeyError, TypeError, ValueError):
        receipt = None
    if not _receipt_valid(receipt, expected_hash):
        return _unknown(
            "PRESENTATION_V8_EXACT_REBUILD_FAILED",
            request_valid=True,
            context_valid=True,
        )
    if not _known_presentation(presentation):
        return _unknown(
            "PRESENTATION_V8_SOURCE_UNKNOWN",
            request_valid=True,
            context_valid=True,
        )
    try:
        payload = _payload(presentation)
    except (KeyError, TypeError, ValueError):
        return _unknown(
            "PRESENTATION_V8_PROJECTION_FAILED",
            request_valid=True,
            context_valid=True,
        )
    blockers = list(HTTP_CANDIDATE_BLOCKERS)
    if presentation["local_decision"]["joint_status"] == "BLOCK":
        blockers.append("LOCAL_RESEARCH_GATE_BLOCKED")
    if presentation["multi_window_summary"]["any_registered_window_blocked"]:
        blockers.append("MULTI_WINDOW_STABILITY_GATE_BLOCKED")
    return _response(
        state=KNOWN_BLOCKED_STATE,
        payload=payload,
        blockers=blockers,
        request_valid=True,
        context_valid=True,
        source_hash=expected_hash,
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
    response: Any,
    request_payload: Any,
    *,
    presentation_verification_context: Any,
) -> bool:
    """Verify an exact rebuild without granting transport or mount authority."""
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
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
    "PRESENTATION_V8_IMPLEMENTATION_SHA256",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATE",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8",
]
