"""Unregistered route contract consuming the exact membership candidate-v11.

The proposed method and path are descriptive contract data only.  This module
does not register a server route, bind a handler, mount a UI consumer, read
runtime state, or grant current, paper, or live authority.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Mapping

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_candidate_v11
    as _candidate_v11,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-route-contract-request-v1"
)
PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-route-contract-payload-v1"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-route-contract-response-v1"
)
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "membership-http-route-contract-v1-unregistered-lock-1"
)
CANDIDATE_V11_IMPLEMENTATION_HASH = (
    "edb4deca22e9dfee22627626ac6982af09199ec6052fb9e6658df371566415d1"
)
STRICT_CANONICAL_IMPLEMENTATION_HASH = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

PROPOSED_HTTP_METHOD = "POST"
PROPOSED_ROUTE_PATH = (
    "/api/research/strategy-correlation-clusters/"
    "common-observation-membership-presentation-v11"
)
JSON_MEDIA_TYPE = "application/json"
INTERFACE_STATE = "UNREGISTERED_ROUTE_CONTRACT"
KNOWN_STATE = "KNOWN_UNREGISTERED"
UNKNOWN_STATE = "UNKNOWN"

LOCKED_AUTHORITY = {
    "route_registration_allowed": False,
    "handler_binding_allowed": False,
    "external_call_allowed": False,
    "ui_consumer_mount_allowed": False,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "paper_authorized": False,
    "live_order_allowed": False,
    "runtime_gate_activation_allowed": False,
    "writer_allowed": False,
}
BASE_BLOCKERS = (
    "ROUTE_CONTRACT_V1_UNREGISTERED",
    "REGISTRATION_EVIDENCE_ABSENT",
    "HTTP_HANDLER_NOT_BOUND",
    "SERVER_CONTRACT_NOT_BOUND",
    "UI_CONSUMER_NOT_BOUND",
    "CURRENT_ADMISSION_LOCKED",
)
UNKNOWN_BLOCKER = "CANDIDATE_V11_UNKNOWN"

_REQUEST_KEYS = {
    "schema_version",
    "expected_candidate_v11_hash",
    "candidate_v11_response",
}
_CONTEXT_KEYS = {
    "candidate_v11_request_payload",
    "candidate_v11_presentation_verification_context",
}
_CANDIDATE_RESPONSE_KEYS = {
    "schema_version",
    "static_contract_version",
    "status",
    "state",
    "interface",
    "authority",
    "blockers",
    "lineage",
    "payload",
    "source_hash",
}
_CANDIDATE_PAYLOAD_KEYS = {
    "schema_version",
    "decision",
    "status",
    "authority",
    "aggregate_summaries",
    "local_decision",
    "source_hashes",
    "facts",
    "gaps",
    "stages",
    "source_hash",
}
_OPTIONAL_CANDIDATE_BLOCKERS = {
    "PRESENTATION_V11_LOCAL_BLOCK",
    "ADAPTER_V10_BLOCK",
    "COMMON_OBSERVATION_MEMBERSHIP_BLOCK",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_VERIFY_CANDIDATE = getattr(
    _candidate_v11,
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_"
    "edge_uncertainty_common_observation_membership_presentation_http_candidate_"
    "response_v11",
)


def _plain_mapping(value: Any) -> bool:
    return type(value) is dict


def _hash(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _sealed(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(copy.deepcopy(document), "source_hash")


def _valid_request(request_payload: Any) -> bool:
    return (
        _plain_mapping(request_payload)
        and set(request_payload) == _REQUEST_KEYS
        and request_payload.get("schema_version") == REQUEST_SCHEMA_VERSION
        and _hash(request_payload.get("expected_candidate_v11_hash"))
        and _plain_mapping(request_payload.get("candidate_v11_response"))
    )


def _valid_context(context: Any) -> bool:
    return (
        _plain_mapping(context)
        and set(context) == _CONTEXT_KEYS
        and all(_plain_mapping(context[key]) for key in _CONTEXT_KEYS)
    )


def _candidate_authority_locked(value: Any) -> bool:
    return _plain_mapping(value) and strict_json_contract_equal(
        value, _candidate_v11.LOCKED_AUTHORITY
    )


def _valid_candidate_response(response: Any, expected_hash: Any) -> bool:
    if not _plain_mapping(response) or set(response) != _CANDIDATE_RESPONSE_KEYS:
        return False
    if response.get("schema_version") != _candidate_v11.RESPONSE_SCHEMA_VERSION:
        return False
    if response.get("static_contract_version") != _candidate_v11.STATIC_CONTRACT_VERSION:
        return False
    if response.get("source_hash") != expected_hash or not _hash(expected_hash):
        return False
    if response.get("status") != "BLOCK" or response.get("state") != _candidate_v11.KNOWN_STATE:
        return False
    if response.get("interface") != _candidate_v11.INTERFACE_STATE:
        return False
    if not _candidate_authority_locked(response.get("authority")):
        return False
    blockers = response.get("blockers")
    if not isinstance(blockers, list) or blockers[: len(_candidate_v11.BASE_BLOCKERS)] != list(
        _candidate_v11.BASE_BLOCKERS
    ):
        return False
    if any(blocker not in _OPTIONAL_CANDIDATE_BLOCKERS for blocker in blockers[len(_candidate_v11.BASE_BLOCKERS) :]):
        return False
    payload = response.get("payload")
    if not _plain_mapping(payload) or set(payload) != _CANDIDATE_PAYLOAD_KEYS:
        return False
    if payload.get("schema_version") != _candidate_v11.PAYLOAD_SCHEMA_VERSION:
        return False
    if payload.get("status") != "BLOCK" or not _candidate_authority_locked(
        payload.get("authority")
    ):
        return False
    facts = payload.get("facts")
    gaps = payload.get("gaps")
    if not _plain_mapping(facts) or not _plain_mapping(gaps):
        return False
    if facts.get("gap_scopes_explicit") is not True:
        return False
    if facts.get("source_gap_snapshot_current") is not False:
        return False
    source_snapshot = gaps.get("source_snapshot")
    candidate_current = gaps.get("candidate_current")
    if not _plain_mapping(source_snapshot) or not _plain_mapping(candidate_current):
        return False
    if source_snapshot.get("schema_version") != _candidate_v11.PRESENTATION_SCHEMA_VERSION:
        return False
    if source_snapshot.get("static_fingerprint") != _candidate_v11.PRESENTATION_STATIC_FINGERPRINT:
        return False
    if candidate_current.get("static_contract_version") != _candidate_v11.STATIC_CONTRACT_VERSION:
        return False
    if candidate_current.get("interface") != _candidate_v11.INTERFACE_STATE:
        return False
    if candidate_current.get("blockers") != blockers:
        return False
    if candidate_current.get("blocker_count") != len(blockers):
        return False
    return True


def _candidate_additive_blockers(candidate_response: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    source_blockers = candidate_response.get("blockers", [])
    mapping = (
        ("PRESENTATION_V11_LOCAL_BLOCK", "CANDIDATE_V11_LOCAL_BLOCK"),
        ("ADAPTER_V10_BLOCK", "CANDIDATE_V11_ADAPTER_BLOCK"),
        (
            "COMMON_OBSERVATION_MEMBERSHIP_BLOCK",
            "CANDIDATE_V11_MEMBERSHIP_BLOCK",
        ),
    )
    for source, projected in mapping:
        if source in source_blockers:
            blockers.append(projected)
    return blockers


def _known_payload(
    candidate_response: Mapping[str, Any], current_blockers: list[str]
) -> dict[str, Any]:
    payload = {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "decision": "EXACT_CANDIDATE_V11_BOUND_ROUTE_REGISTRATION_ABSENT",
        "status": "BLOCK",
        "transport": {
            "proposed_only": True,
            "registered": False,
            "externally_callable": False,
            "http_method": PROPOSED_HTTP_METHOD,
            "proposed_route_path": PROPOSED_ROUTE_PATH,
            "request_media_type": JSON_MEDIA_TYPE,
            "response_media_type": JSON_MEDIA_TYPE,
            "handler_bound": False,
            "server_contract_bound": False,
            "ui_consumer_bound": False,
            "runtime_probe_performed": False,
        },
        "registration_evidence": {
            "status": "ABSENT",
            "registration_document_present": False,
            "registration_receipt_present": False,
            "source_audit_required": True,
        },
        "contract": {
            "candidate_request_schema_version": _candidate_v11.REQUEST_SCHEMA_VERSION,
            "candidate_response_schema_version": _candidate_v11.RESPONSE_SCHEMA_VERSION,
            "candidate_static_contract_version": _candidate_v11.STATIC_CONTRACT_VERSION,
            "route_contract_schema_version": RESPONSE_SCHEMA_VERSION,
        },
        "lineage": {
            "candidate_v11_hash": candidate_response["source_hash"],
            "candidate_v11_implementation_hash": CANDIDATE_V11_IMPLEMENTATION_HASH,
            "strict_canonical_implementation_hash": STRICT_CANONICAL_IMPLEMENTATION_HASH,
        },
        "facts": {
            "candidate_v11_exact": True,
            "candidate_v11_known_blocked": True,
            "candidate_payload_embedded": False,
            "candidate_request_embedded": False,
            "verification_context_embedded": False,
            "route_contract_versioned": True,
            "route_registered": False,
            "handler_bound": False,
            "server_contract_bound": False,
            "ui_consumer_bound": False,
            "runtime_assets_accessed": False,
            "profitability_proven": False,
        },
        "blockers": list(current_blockers),
        "authority": copy.deepcopy(LOCKED_AUTHORITY),
        "stages": [
            {
                "axis": "SOURCE",
                "state": "KNOWN",
                "detail": "EXACT_CANDIDATE_V11_LOCK4",
            },
            {
                "axis": "GAP",
                "state": "BLOCKED",
                "detail": "REGISTRATION_HANDLER_SERVER_AND_UI_BINDINGS_ABSENT",
            },
            {
                "axis": "MATURITY",
                "state": "CONTRACT_ONLY",
                "detail": "UNREGISTERED_ROUTE_CONTRACT_V1",
            },
            {
                "axis": "PERMISSION",
                "state": "NONE",
                "detail": "NO_CURRENT_PAPER_OR_LIVE_AUTHORITY",
            },
        ],
    }
    return _sealed(payload)


def _response(
    *,
    state: str,
    expected_candidate_hash: str | None,
    payload: Mapping[str, Any] | None,
    blockers: list[str],
) -> dict[str, Any]:
    response = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCK" if state == KNOWN_STATE else "UNKNOWN",
        "state": state,
        "interface": INTERFACE_STATE,
        "authority": copy.deepcopy(LOCKED_AUTHORITY),
        "blockers": blockers,
        "lineage": {
            "candidate_v11_schema_version": _candidate_v11.RESPONSE_SCHEMA_VERSION,
            "candidate_v11_static_contract_version": _candidate_v11.STATIC_CONTRACT_VERSION,
            "candidate_v11_hash": expected_candidate_hash,
            "candidate_v11_implementation_hash": CANDIDATE_V11_IMPLEMENTATION_HASH,
            "strict_canonical_implementation_hash": STRICT_CANONICAL_IMPLEMENTATION_HASH,
        },
        "payload": copy.deepcopy(payload),
    }
    return _sealed(response)


def _unknown_response(expected_hash: Any = None) -> dict[str, Any]:
    safe_hash = expected_hash if _hash(expected_hash) else None
    return _response(
        state=UNKNOWN_STATE,
        expected_candidate_hash=safe_hash,
        payload=None,
        blockers=[*BASE_BLOCKERS, UNKNOWN_BLOCKER],
    )


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
    request_payload: Mapping[str, Any],
    *,
    candidate_verification_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a route contract document without registering the proposed route."""
    request_copy = copy.deepcopy(request_payload)
    context_copy = copy.deepcopy(candidate_verification_context)
    expected_hash = request_copy.get("expected_candidate_v11_hash") if _plain_mapping(request_copy) else None
    if not _valid_request(request_copy) or not _valid_context(context_copy):
        return _unknown_response(expected_hash)
    candidate_response = request_copy["candidate_v11_response"]
    if not _valid_candidate_response(candidate_response, expected_hash):
        return _unknown_response(expected_hash)
    try:
        exact = _VERIFY_CANDIDATE(
            candidate_response,
            context_copy["candidate_v11_request_payload"],
            presentation_verification_context=context_copy[
                "candidate_v11_presentation_verification_context"
            ],
        )
    except Exception:
        return _unknown_response(expected_hash)
    if exact is not True:
        return _unknown_response(expected_hash)
    blockers = [*BASE_BLOCKERS, *_candidate_additive_blockers(candidate_response)]
    payload = _known_payload(candidate_response, blockers)
    return _response(
        state=KNOWN_STATE,
        expected_candidate_hash=expected_hash,
        payload=payload,
        blockers=blockers,
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
    document: Mapping[str, Any],
    request_payload: Mapping[str, Any],
    *,
    candidate_verification_context: Mapping[str, Any],
) -> bool:
    """Verify the route contract by exact deterministic rebuild."""
    if not _plain_mapping(document):
        return False
    try:
        rebuilt = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
            request_payload,
            candidate_verification_context=candidate_verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, rebuilt)


__all__ = [
    "BASE_BLOCKERS",
    "CANDIDATE_V11_IMPLEMENTATION_HASH",
    "INTERFACE_STATE",
    "JSON_MEDIA_TYPE",
    "KNOWN_STATE",
    "LOCKED_AUTHORITY",
    "PAYLOAD_SCHEMA_VERSION",
    "PROPOSED_HTTP_METHOD",
    "PROPOSED_ROUTE_PATH",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATE",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1",
]
