"""Unregistered ADR0332-bound HTTP candidate v8.

This wrapper does not register a route.  It exact-verifies the geometry-bound
presentation evaluation, derives the legacy v7 request and verification context,
and accepts only a pinned, exactly rebuilt KNOWN_BLOCKED v7 response.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from hmac import compare_digest
import json
from typing import Any

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_stratified_presentation_candidate_v7 as _http_v7,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_presentation_binding_v1 as _presentation_binding,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-presentation-http-candidate-request-v8"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-presentation-http-candidate-response-v8"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-presentation-http-v8-unregistered-lock-1"
)
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
UNKNOWN_STATE = "UNKNOWN"
KNOWN_BLOCKED_STATE = "KNOWN_BLOCKED"

PRESENTATION_BINDING_MODULE = (
    "exchange_terminal.services.strategy_correlation_matrix_geometry_budget_presentation_binding_v1"
)
PRESENTATION_BINDING_IMPLEMENTATION_SHA256 = (
    "e482206ff0e4a6e805e6f7318305135c8a291c4f9a1065ca2975b9ddb6093113"
)
HTTP_V7_MODULE = (
    "exchange_terminal.interfaces.http.strategy_correlation_cluster_portfolio_risk_stratified_presentation_candidate_v7"
)
HTTP_V7_IMPLEMENTATION_SHA256 = (
    "fdb2d0ff4abe5df9d7e83dae901e6bb11ae3e5b1fa3c4190b7d5123d3e058f23"
)

_REQUEST_KEYS = frozenset(
    {
        "schema_version",
        "geometry_budget_presentation_binding_evaluation",
        "expected_geometry_budget_presentation_binding_evaluation_hash",
    }
)
_PRESENTATION_BINDING_CONTEXT_KEYS = frozenset(
    {
        "presentation_binding_preregistration",
        "budget_binding_preregistration",
        "budget_binding_evaluation",
        "envelope_v6_document",
        "expected_evaluation_hash",
        "expected_presentation_binding_preregistration_hash",
        "expected_budget_binding_preregistration_hash",
        "expected_budget_binding_evaluation_hash",
        "budget_binding_verification_context",
        "envelope_v6_verification_context",
    }
)

_PINNED_HTTP_V7_BUILDER = (
    _http_v7.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7
)


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return sha256(payload).hexdigest()


def _canonical_external_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _is_exact_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_hash(document: Any, field: str) -> str | None:
    if not isinstance(document, dict):
        return None
    value = document.get(field)
    return value if _is_exact_hash(value) else None


def _self_hash_is_exact(document: Any, field: str) -> bool:
    stored_hash = _safe_hash(document, field)
    if stored_hash is None:
        return False
    unsigned = deepcopy(document)
    unsigned.pop(field, None)
    return compare_digest(_canonical_external_hash(unsigned), stored_hash)


_CONTRACT_MANIFEST = {
    "request_schema_version": REQUEST_SCHEMA_VERSION,
    "response_schema_version": RESPONSE_SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "interface_status": INTERFACE_STATUS,
    "accepted_state": KNOWN_BLOCKED_STATE,
    "presentation_binding": {
        "module": PRESENTATION_BINDING_MODULE,
        "source_sha256": PRESENTATION_BINDING_IMPLEMENTATION_SHA256,
        "contract_hash": _presentation_binding.BINDING_CONTRACT_HASH,
        "static_fingerprint": _presentation_binding.STATIC_FINGERPRINT,
        "evaluation_schema_version": _presentation_binding.EVALUATION_SCHEMA_VERSION,
    },
    "http_v7": {
        "module": HTTP_V7_MODULE,
        "source_sha256": HTTP_V7_IMPLEMENTATION_SHA256,
        "request_schema_version": _http_v7.REQUEST_SCHEMA_VERSION,
        "response_schema_version": _http_v7.RESPONSE_SCHEMA_VERSION,
        "candidate_builder": (
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7"
        ),
        "exact_rebuilder": (
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7@v8_import"
        ),
    },
    "authority": {
        "route_registration_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "writer_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    },
}
CONTRACT_HASH = _canonical_hash(_CONTRACT_MANIFEST)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "consumer_activation_allowed": False,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mount_allowed": False,
        "route_registration_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def _response(
    *,
    state: str,
    blocker: str | None,
    presentation_binding_evaluation: Any,
    v7_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    presentation = (
        presentation_binding_evaluation.get("presentation_document")
        if isinstance(presentation_binding_evaluation, dict)
        else None
    )
    document: dict[str, Any] = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "contract_hash": CONTRACT_HASH,
        "interface_status": INTERFACE_STATUS,
        "state": state,
        "blockers": [blocker] if blocker is not None else [],
        "facts": {
            "geometry_bound_presentation_exactly_verified": (
                v7_response is not None
            ),
            "http_v7_exactly_rebuilt": v7_response is not None,
            "route_registered": False,
            "request_context_embedded": False,
            "source_documents_embedded": False,
        },
        "lineage": {
            "presentation_binding_evaluation_hash": _safe_hash(
                presentation_binding_evaluation, "evaluation_hash"
            ),
            "presentation_v7_hash": _safe_hash(
                presentation, "presentation_v7_hash"
            ),
            "http_v7_response_hash": _safe_hash(v7_response, "response_hash"),
        },
        "payload": deepcopy(v7_response.get("payload")) if v7_response else None,
        "authority": _authority(),
    }
    document["response_hash"] = _canonical_external_hash(document)
    return document


def _verify_presentation_binding_evaluation(document: Any, context: Any) -> bool:
    if (
        not isinstance(context, dict)
        or frozenset(context) != _PRESENTATION_BINDING_CONTEXT_KEYS
    ):
        return False
    try:
        return _presentation_binding.verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1(
            document,
            context["presentation_binding_preregistration"],
            context["budget_binding_preregistration"],
            context["budget_binding_evaluation"],
            context["envelope_v6_document"],
            expected_evaluation_hash=context["expected_evaluation_hash"],
            expected_presentation_binding_preregistration_hash=context[
                "expected_presentation_binding_preregistration_hash"
            ],
            expected_budget_binding_preregistration_hash=context[
                "expected_budget_binding_preregistration_hash"
            ],
            expected_budget_binding_evaluation_hash=context[
                "expected_budget_binding_evaluation_hash"
            ],
            budget_binding_verification_context=context[
                "budget_binding_verification_context"
            ],
            envelope_v6_verification_context=context[
                "envelope_v6_verification_context"
            ],
        )
    except Exception:
        return False


def _derived_presentation_verification_context(
    context: dict[str, Any],
) -> dict[str, Any] | None:
    budget_context = context.get("budget_binding_verification_context")
    budget_binding_evaluation = context.get("budget_binding_evaluation")
    if not isinstance(budget_context, dict) or not isinstance(
        budget_binding_evaluation, dict
    ):
        return None
    budget_v3_context = _presentation_binding._derived_budget_v3_context(
        budget_context
    )
    budget_document = budget_binding_evaluation.get("effective_budget_document")
    if budget_v3_context is None or not isinstance(budget_document, dict):
        return None
    return {
        "envelope_v6_document": context["envelope_v6_document"],
        "budget_v3_document": budget_document,
        "envelope_v6_verification_context": context[
            "envelope_v6_verification_context"
        ],
        "budget_v3_verification_context": budget_v3_context,
    }


def _v7_request(presentation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": _http_v7.REQUEST_SCHEMA_VERSION,
        "stratified_presentation_v7_document": presentation,
        "expected_presentation_v7_hash": presentation["presentation_v7_hash"],
    }


def _v7_authority_is_locked(response: Any) -> bool:
    if (
        not isinstance(response, dict)
        or response.get("interface_status") != _http_v7.INTERFACE_STATUS
        or response.get("state") != _http_v7.KNOWN_BLOCKED_STATE
        or not isinstance(response.get("payload"), dict)
    ):
        return False
    authority = response.get("authority")
    if not isinstance(authority, dict):
        return False
    false_fields = (
        "consumer_activation_allowed",
        "current_admission_allowed",
        "live_order_allowed",
        "paper_authorized",
        "presentation_mount_allowed",
        "route_registration_allowed",
        "runtime_gate_activation_allowed",
        "writer_allowed",
    )
    return all(authority.get(field) is False for field in false_fields)


def build_strategy_correlation_matrix_geometry_budget_presentation_http_candidate_response_v8(
    request_payload: Any,
    *,
    presentation_binding_verification_context: Any,
) -> dict[str, Any]:
    if not isinstance(request_payload, dict) or frozenset(request_payload) != _REQUEST_KEYS:
        return _response(
            state=UNKNOWN_STATE,
            blocker="REQUEST_SHAPE_INVALID",
            presentation_binding_evaluation=None,
        )
    evaluation = request_payload.get(
        "geometry_budget_presentation_binding_evaluation"
    )
    expected_hash = request_payload.get(
        "expected_geometry_budget_presentation_binding_evaluation_hash"
    )
    if (
        request_payload.get("schema_version") != REQUEST_SCHEMA_VERSION
        or not _is_exact_hash(expected_hash)
        or _safe_hash(evaluation, "evaluation_hash") != expected_hash
        or not isinstance(presentation_binding_verification_context, dict)
        or presentation_binding_verification_context.get("expected_evaluation_hash")
        != expected_hash
    ):
        return _response(
            state=UNKNOWN_STATE,
            blocker="REQUEST_CONTRACT_INVALID",
            presentation_binding_evaluation=evaluation,
        )
    if not _verify_presentation_binding_evaluation(
        evaluation,
        presentation_binding_verification_context,
    ):
        return _response(
            state=UNKNOWN_STATE,
            blocker="PRESENTATION_BINDING_EVALUATION_INVALID",
            presentation_binding_evaluation=evaluation,
        )
    if (
        evaluation.get("status") != "PASS"
        or evaluation.get("presentation_verified") is not True
        or not isinstance(evaluation.get("presentation_document"), dict)
    ):
        return _response(
            state=UNKNOWN_STATE,
            blocker="PRESENTATION_BINDING_EVALUATION_NOT_PASS",
            presentation_binding_evaluation=evaluation,
        )

    presentation = evaluation["presentation_document"]
    v7_context = _derived_presentation_verification_context(
        presentation_binding_verification_context
    )
    if v7_context is None:
        return _response(
            state=UNKNOWN_STATE,
            blocker="PRESENTATION_V7_CONTEXT_INVALID",
            presentation_binding_evaluation=evaluation,
        )
    v7_request = _v7_request(presentation)
    try:
        v7_response = _http_v7.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
            v7_request,
            presentation_verification_context=v7_context,
        )
    except Exception:
        return _response(
            state=UNKNOWN_STATE,
            blocker="HTTP_V7_CONSUMER_EXCEPTION",
            presentation_binding_evaluation=evaluation,
        )
    try:
        expected_v7_response = _PINNED_HTTP_V7_BUILDER(
            v7_request,
            presentation_verification_context=v7_context,
        )
    except Exception:
        return _response(
            state=UNKNOWN_STATE,
            blocker="HTTP_V7_EXACT_REBUILD_EXCEPTION",
            presentation_binding_evaluation=evaluation,
        )
    if (
        not _self_hash_is_exact(v7_response, "response_hash")
        or v7_response != expected_v7_response
    ):
        return _response(
            state=UNKNOWN_STATE,
            blocker="HTTP_V7_RESPONSE_INVALID",
            presentation_binding_evaluation=evaluation,
        )
    try:
        v7_verified = _http_v7.verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
            v7_response,
            v7_request,
            presentation_verification_context=v7_context,
        )
    except Exception:
        v7_verified = False
    if not v7_verified or not _v7_authority_is_locked(v7_response):
        return _response(
            state=UNKNOWN_STATE,
            blocker="HTTP_V7_VERIFICATION_OR_AUTHORITY_INVALID",
            presentation_binding_evaluation=evaluation,
        )
    return _response(
        state=KNOWN_BLOCKED_STATE,
        blocker=None,
        presentation_binding_evaluation=evaluation,
        v7_response=v7_response,
    )


def verify_strategy_correlation_matrix_geometry_budget_presentation_http_candidate_response_v8(
    response: Any,
    request_payload: Any,
    *,
    presentation_binding_verification_context: Any,
) -> bool:
    try:
        expected = build_strategy_correlation_matrix_geometry_budget_presentation_http_candidate_response_v8(
            request_payload,
            presentation_binding_verification_context=(
                presentation_binding_verification_context
            ),
        )
    except Exception:
        return False
    return bool(
        isinstance(response, dict)
        and _self_hash_is_exact(response, "response_hash")
        and response == expected
    )
