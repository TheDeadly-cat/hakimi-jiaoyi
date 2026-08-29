"""Unmounted HTTP candidate for the exact stratified portfolio-risk presentation-v7.

This module deliberately defines no route, transport, registry, or runtime binding.
It reduces an exactly rebuilt presentation-v7 document to a bounded display payload.
Unknown or substituted sources return no payload and no partial risk summary.
"""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7
    as presentation_v7,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-presentation-"
    "http-candidate-request-v7"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-presentation-"
    "http-candidate-response-v7"
)
PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-presentation-"
    "http-payload-v7"
)
STATIC_FINGERPRINT = "20260823-stratified-budget-http-candidate-v7-unmounted-lock-1"
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
KNOWN_BLOCKED_STATE = "KNOWN_BLOCKED"
UNKNOWN_STATE = "UNKNOWN"
PRESENTATION_V7_IMPLEMENTATION_SHA256 = (
    "27bfeacbdcbdfb03009c0dec007274e3c143af1045a8bfe7587ca4629ada8b38"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
HTTP_CANDIDATE_BLOCKERS = (
    "HTTP_CANDIDATE_V7_UNREGISTERED",
    "PRESENTATION_CONSUMER_NOT_REGISTERED",
    "CURRENT_ADMISSION_LOCKED",
    "UI_NOT_MOUNTED",
)

_VERIFY_PRESENTATION = (
    presentation_v7.verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7
)
_REQUEST_KEYS = {
    "schema_version",
    "stratified_presentation_v7_document",
    "expected_presentation_v7_hash",
}
_CONTEXT_KEYS = {
    "envelope_v6_document",
    "budget_v3_document",
    "envelope_v6_verification_context",
    "budget_v3_verification_context",
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
_LOCAL_KEYS = {
    "joint_decision",
    "joint_status",
    "portfolio_risk_v6_decision",
    "portfolio_risk_v6_status",
    "stratified_budget_decision",
    "stratified_budget_status",
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
_RECEIPT_KEYS = {
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


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return type(value) is dict and set(value) == expected


def _is_hash(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _number_text(value: Any) -> str | None:
    """Project a verified non-negative number without cross-runtime float sealing."""
    if value is None:
        return None
    if isinstance(value, bool) or type(value) not in {int, float}:
        raise ValueError("risk summary number invalid")
    if type(value) is float and not math.isfinite(value):
        raise ValueError("risk summary number must be finite")
    if value < 0:
        raise ValueError("risk summary number must be non-negative")
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
    document = value["stratified_presentation_v7_document"]
    expected_hash = value["expected_presentation_v7_hash"]
    return (
        value["schema_version"] == REQUEST_SCHEMA_VERSION
        and type(document) is dict
        and _is_hash(expected_hash)
        and document.get("presentation_v7_hash") == expected_hash
    )


def _context_valid(value: Any) -> bool:
    return _exact_keys(value, _CONTEXT_KEYS)


def _receipt_valid(value: Any, expected_hash: str) -> bool:
    if not _exact_keys(value, _RECEIPT_KEYS):
        return False
    return (
        value["schema_version"] == presentation_v7.VERIFICATION_SCHEMA_VERSION
        and value["status"] == "PASS"
        and value["blockers"] == []
        and value["presentation_status"] == "BLOCK"
        and value["presentation_v7_hash"] == expected_hash
        and value["current_admission_allowed"] is False
        and value["live_order_allowed"] is False
        and value["paper_authorized"] is False
        and value["presentation_consumer_activation_allowed"] is False
        and value["runtime_gate_activation_allowed"] is False
        and value["writer_allowed"] is False
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
    )


def _known_presentation(value: Any) -> bool:
    if not _exact_keys(value, _PRESENTATION_KEYS):
        return False
    local = value["local_decision"]
    risk = value["risk_summary"]
    facts = value["facts"]
    source = value["source"]
    stages = value["stages"]
    return (
        value["schema_version"] == presentation_v7.SCHEMA_VERSION
        and value["static_fingerprint"] == presentation_v7.STATIC_FINGERPRINT
        and value["status"] == "BLOCK"
        and _is_hash(value["presentation_v7_hash"])
        and value["axis_order"] == list(AXIS_ORDER)
        and _exact_keys(local, _LOCAL_KEYS)
        and local["joint_status"] in {"PASS", "BLOCK"}
        and local["portfolio_risk_v6_status"] in {"PASS", "BLOCK"}
        and local["stratified_budget_status"] in {"PASS", "BLOCK"}
        and _exact_keys(risk, _RISK_KEYS)
        and type(risk["dimension_results"]) is list
        and all(_dimension_valid(row) for row in risk["dimension_results"])
        and type(facts) is dict
        and facts.get("v6_envelope_exactly_verified") is True
        and facts.get("budget_v3_exactly_verified") is True
        and facts.get("joint_local_research_decision_made") is True
        and facts.get("source_documents_embedded") is False
        and facts.get("verification_contexts_embedded") is False
        and type(source) is dict
        and source.get("state") == "EXACT_V6_AND_BUDGET_V3"
        and type(stages) is list
        and len(stages) == len(AXIS_ORDER)
        and all(
            _exact_keys(stage, {"axis", "detail", "state"})
            and stage["axis"] == AXIS_ORDER[index]
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
        "maximum_stratum_gross_pct": _number_text(
            value["maximum_stratum_gross_pct"]
        ),
        "over_limit_stratum_count": value["over_limit_stratum_count"],
        "status": value["status"],
        "weighted_effective_strata_count": _number_text(
            value["weighted_effective_strata_count"]
        ),
    }


def _payload(presentation: dict[str, Any]) -> dict[str, Any]:
    risk = presentation["risk_summary"]
    document = {
        "authority": _authority(),
        "decision": "EXACT_PRESENTATION_V7_PROJECTED_AUTHORITY_UNCHANGED",
        "facts": {
            "budget_v3_exactly_verified": True,
            "dimension_summaries_projected": bool(risk["dimension_results"]),
            "matrices_embedded": False,
            "positions_embedded": False,
            "profitability_proven": False,
            "runtime_consumer_bound": False,
            "source_document_embedded": False,
            "ui_mounted": False,
            "v6_envelope_exactly_verified": True,
            "verification_context_embedded": False,
        },
        "gaps": {
            "http_candidate_blocker_count": len(HTTP_CANDIDATE_BLOCKERS),
            "http_candidate_blockers": list(HTTP_CANDIDATE_BLOCKERS),
            "local_blocker_count": presentation["gaps"]["local_blocker_count"],
            "stratified_budget_blocker_count": presentation["gaps"][
                "stratified_budget_blocker_count"
            ],
        },
        "local_decision": deepcopy(presentation["local_decision"]),
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
            "presentation_v7_hash": presentation["presentation_v7_hash"],
            "state": presentation["source"]["state"],
        },
        "stages": [
            deepcopy(presentation["stages"][0]),
            deepcopy(presentation["stages"][1]),
            {
                "axis": "MATURITY",
                "detail": "UNMOUNTED_HTTP_CANDIDATE_V7",
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
            "presentation_v7_exactly_verified": known,
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
            "presentation_v7_hash": source_hash if known else None,
            "presentation_v7_implementation_sha256": (
                PRESENTATION_V7_IMPLEMENTATION_SHA256
            ),
            "presentation_v7_schema_version": presentation_v7.SCHEMA_VERSION,
            "presentation_v7_static_fingerprint": presentation_v7.STATIC_FINGERPRINT,
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


def build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
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

    presentation = request_payload["stratified_presentation_v7_document"]
    expected_hash = request_payload["expected_presentation_v7_hash"]
    try:
        receipt = _VERIFY_PRESENTATION(
            presentation,
            presentation_verification_context["envelope_v6_document"],
            presentation_verification_context["budget_v3_document"],
            envelope_v6_verification_context=presentation_verification_context[
                "envelope_v6_verification_context"
            ],
            budget_v3_verification_context=presentation_verification_context[
                "budget_v3_verification_context"
            ],
        )
    except (KeyError, TypeError, ValueError):
        receipt = None
    if not _receipt_valid(receipt, expected_hash):
        return _unknown(
            "PRESENTATION_V7_EXACT_REBUILD_FAILED",
            request_valid=True,
            context_valid=True,
        )
    if not _known_presentation(presentation):
        return _unknown(
            "PRESENTATION_V7_SOURCE_UNKNOWN",
            request_valid=True,
            context_valid=True,
        )
    try:
        payload = _payload(presentation)
    except (KeyError, TypeError, ValueError):
        return _unknown(
            "PRESENTATION_V7_PROJECTION_FAILED",
            request_valid=True,
            context_valid=True,
        )
    blockers = list(HTTP_CANDIDATE_BLOCKERS)
    if presentation["local_decision"]["joint_status"] == "BLOCK":
        blockers.append("LOCAL_RESEARCH_GATE_BLOCKED")
    return _response(
        state=KNOWN_BLOCKED_STATE,
        payload=payload,
        blockers=blockers,
        request_valid=True,
        context_valid=True,
        source_hash=expected_hash,
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
    response: Any,
    request_payload: Any,
    *,
    presentation_verification_context: Any,
) -> bool:
    """Verify an exact rebuild; this never grants transport or mount authority."""
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
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
    "PRESENTATION_V7_IMPLEMENTATION_SHA256",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATE",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7",
]
