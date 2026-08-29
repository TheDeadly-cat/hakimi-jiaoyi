"""Unregistered ADR0334-bound multi-window HTTP candidate v9.

This wrapper registers no route or transport. It exact-verifies the
geometry-bound multi-window evaluation, derives the legacy HTTP-v8 request and
verification context, and accepts only a pinned, exactly rebuilt KNOWN_BLOCKED
response with all authority fields locked.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from hmac import compare_digest
import json
from typing import Any

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_candidate_v8
    as _http_v8,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9
    as _multi_window_binding,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "http-candidate-request-v9"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "http-candidate-response-v9"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-"
    "presentation-http-v9-unregistered-lock-1"
)
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
UNKNOWN_STATE = "UNKNOWN"
KNOWN_BLOCKED_STATE = "KNOWN_BLOCKED"

MULTI_WINDOW_BINDING_MODULE = (
    "exchange_terminal.services.strategy_correlation_matrix_geometry_budget_"
    "multi_window_presentation_binding_v9"
)
MULTI_WINDOW_BINDING_IMPLEMENTATION_SHA256 = (
    "17f43a0bfa4b9c1912e8f167efa9be4bd5f4c9e56d0d818fda88abe5f6705295"
)
HTTP_V8_MODULE = (
    "exchange_terminal.interfaces.http.strategy_correlation_cluster_portfolio_"
    "risk_stratified_multi_window_presentation_candidate_v8"
)
HTTP_V8_IMPLEMENTATION_SHA256 = (
    "70e2cabb54d0a9bf51973756fbe40173b142745d3a3f9d0f6f816ca759eb2770"
)

_REQUEST_KEYS = frozenset(
    {
        "schema_version",
        "geometry_budget_multi_window_presentation_binding_evaluation",
        "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash",
    }
)
_BINDING_CONTEXT_KEYS = frozenset(
    {
        "presentation_binding_evaluation",
        "adapter_v7_document",
        "expected_evaluation_hash",
        "expected_presentation_binding_evaluation_hash",
        "expected_adapter_v7_hash",
        "presentation_binding_verification_context",
        "adapter_v7_verification_context",
    }
)
_BINDING_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "evaluation_hash",
        "current_admission_allowed",
        "writer_allowed",
        "paper_authorized",
        "live_order_allowed",
    }
)

_PINNED_HTTP_V8_BUILDER = (
    _http_v8.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8
)


def _canonical_hash(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


def _canonical_external_hash(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


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
    stored = _safe_hash(document, field)
    if stored is None:
        return False
    unsigned = deepcopy(document)
    unsigned.pop(field, None)
    return compare_digest(_canonical_external_hash(unsigned), stored)


_CONTRACT_MANIFEST = {
    "request_schema_version": REQUEST_SCHEMA_VERSION,
    "response_schema_version": RESPONSE_SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "interface_status": INTERFACE_STATUS,
    "accepted_state": KNOWN_BLOCKED_STATE,
    "multi_window_binding": {
        "module": MULTI_WINDOW_BINDING_MODULE,
        "source_sha256": MULTI_WINDOW_BINDING_IMPLEMENTATION_SHA256,
        "contract_hash": _multi_window_binding.CONTRACT_HASH,
        "static_fingerprint": _multi_window_binding.STATIC_FINGERPRINT,
        "schema_version": _multi_window_binding.SCHEMA_VERSION,
        "verification_schema_version": (
            _multi_window_binding.VERIFICATION_SCHEMA_VERSION
        ),
    },
    "http_v8": {
        "module": HTTP_V8_MODULE,
        "source_sha256": HTTP_V8_IMPLEMENTATION_SHA256,
        "request_schema_version": _http_v8.REQUEST_SCHEMA_VERSION,
        "response_schema_version": _http_v8.RESPONSE_SCHEMA_VERSION,
        "candidate_builder": (
            "build_strategy_correlation_cluster_portfolio_risk_stratified_"
            "multi_window_presentation_http_candidate_response_v8"
        ),
        "exact_rebuilder": "http_v8_builder@v9_import",
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
    binding_evaluation: Any,
    http_v8_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    multi_window_document = (
        binding_evaluation.get("multi_window_document")
        if isinstance(binding_evaluation, dict)
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
            "geometry_bound_multi_window_exactly_verified": (
                http_v8_response is not None
            ),
            "http_v8_exactly_rebuilt": http_v8_response is not None,
            "route_registered": False,
            "request_context_embedded": False,
            "source_documents_embedded": False,
        },
        "lineage": {
            "multi_window_binding_evaluation_hash": _safe_hash(
                binding_evaluation, "evaluation_hash"
            ),
            "multi_window_v8_hash": _safe_hash(
                multi_window_document, "presentation_v8_hash"
            ),
            "http_v8_response_hash": _safe_hash(
                http_v8_response, "response_hash"
            ),
        },
        "payload": (
            deepcopy(http_v8_response.get("payload"))
            if http_v8_response
            else None
        ),
        "authority": _authority(),
    }
    document["response_hash"] = _canonical_external_hash(document)
    return document


def _binding_receipt_valid(receipt: Any, expected_hash: str) -> bool:
    return bool(
        isinstance(receipt, dict)
        and frozenset(receipt) == _BINDING_RECEIPT_KEYS
        and receipt.get("schema_version")
        == _multi_window_binding.VERIFICATION_SCHEMA_VERSION
        and receipt.get("status") == "PASS"
        and receipt.get("evaluation_hash") == expected_hash
        and receipt.get("current_admission_allowed") is False
        and receipt.get("writer_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("live_order_allowed") is False
    )


def _verify_binding_evaluation(document: Any, context: Any) -> bool:
    if not isinstance(context, dict) or frozenset(context) != _BINDING_CONTEXT_KEYS:
        return False
    try:
        receipt = _multi_window_binding.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9(
            document,
            context["presentation_binding_evaluation"],
            context["adapter_v7_document"],
            expected_evaluation_hash=context["expected_evaluation_hash"],
            expected_presentation_binding_evaluation_hash=context[
                "expected_presentation_binding_evaluation_hash"
            ],
            expected_adapter_v7_hash=context["expected_adapter_v7_hash"],
            presentation_binding_verification_context=context[
                "presentation_binding_verification_context"
            ],
            adapter_v7_verification_context=context[
                "adapter_v7_verification_context"
            ],
        )
    except Exception:
        return False
    return _binding_receipt_valid(receipt, context["expected_evaluation_hash"])


def _derived_http_v8_verification_context(
    context: dict[str, Any],
) -> dict[str, Any] | None:
    presentation_binding_evaluation = context.get(
        "presentation_binding_evaluation"
    )
    presentation_context = context.get("presentation_binding_verification_context")
    adapter_context = context.get("adapter_v7_verification_context")
    adapter_document = context.get("adapter_v7_document")
    if (
        not isinstance(presentation_binding_evaluation, dict)
        or not isinstance(presentation_context, dict)
        or not isinstance(adapter_context, dict)
        or not isinstance(adapter_document, dict)
    ):
        return None
    presentation = presentation_binding_evaluation.get("presentation_document")
    budget_pair = _multi_window_binding._budget_document_and_context(
        presentation_context
    )
    if not isinstance(presentation, dict) or budget_pair is None:
        return None
    budget, budget_context = budget_pair
    return {
        "presentation_v7_document": presentation,
        "adapter_v7_document": adapter_document,
        "presentation_v7_verification_context": (
            _multi_window_binding._presentation_v7_context(
                presentation_context,
                budget,
                budget_context,
            )
        ),
        "adapter_v7_verification_context": (
            _multi_window_binding._adapter_v7_context(
                adapter_context,
                budget,
                budget_context,
            )
        ),
    }


def _v8_request(multi_window_document: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": _http_v8.REQUEST_SCHEMA_VERSION,
        "stratified_multi_window_presentation_v8_document": (
            multi_window_document
        ),
        "expected_presentation_v8_hash": multi_window_document[
            "presentation_v8_hash"
        ],
    }


def _http_v8_authority_is_locked(response: Any) -> bool:
    if (
        not isinstance(response, dict)
        or response.get("interface_status") != _http_v8.INTERFACE_STATUS
        or response.get("state") != _http_v8.KNOWN_BLOCKED_STATE
        or not isinstance(response.get("payload"), dict)
    ):
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
    authorities = (response.get("authority"), response["payload"].get("authority"))
    return all(
        isinstance(authority, dict)
        and all(authority.get(field) is False for field in false_fields)
        for authority in authorities
    )


def build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_response_v9(
    request_payload: Any,
    *,
    multi_window_binding_verification_context: Any,
) -> dict[str, Any]:
    """Build a sealed display candidate without registering a transport."""
    if not isinstance(request_payload, dict) or frozenset(request_payload) != _REQUEST_KEYS:
        return _response(
            state=UNKNOWN_STATE,
            blocker="REQUEST_SHAPE_INVALID",
            binding_evaluation=None,
        )
    evaluation = request_payload.get(
        "geometry_budget_multi_window_presentation_binding_evaluation"
    )
    expected_hash = request_payload.get(
        "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash"
    )
    if (
        request_payload.get("schema_version") != REQUEST_SCHEMA_VERSION
        or not _is_exact_hash(expected_hash)
        or _safe_hash(evaluation, "evaluation_hash") != expected_hash
        or not isinstance(multi_window_binding_verification_context, dict)
        or multi_window_binding_verification_context.get("expected_evaluation_hash")
        != expected_hash
    ):
        return _response(
            state=UNKNOWN_STATE,
            blocker="REQUEST_CONTRACT_INVALID",
            binding_evaluation=evaluation,
        )
    if not _verify_binding_evaluation(
        evaluation,
        multi_window_binding_verification_context,
    ):
        return _response(
            state=UNKNOWN_STATE,
            blocker="MULTI_WINDOW_BINDING_EVALUATION_INVALID",
            binding_evaluation=evaluation,
        )
    multi_window_document = evaluation.get("multi_window_document")
    if (
        evaluation.get("status") != "PASS"
        or evaluation.get("multi_window_verified") is not True
        or not isinstance(multi_window_document, dict)
        or _safe_hash(multi_window_document, "presentation_v8_hash")
        != evaluation.get("multi_window_v8_hash")
    ):
        return _response(
            state=UNKNOWN_STATE,
            blocker="MULTI_WINDOW_BINDING_EVALUATION_NOT_PASS",
            binding_evaluation=evaluation,
        )

    http_v8_context = _derived_http_v8_verification_context(
        multi_window_binding_verification_context
    )
    if http_v8_context is None:
        return _response(
            state=UNKNOWN_STATE,
            blocker="HTTP_V8_CONTEXT_INVALID",
            binding_evaluation=evaluation,
        )
    http_v8_request = _v8_request(multi_window_document)
    try:
        http_v8_response = _http_v8.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
            http_v8_request,
            presentation_verification_context=http_v8_context,
        )
    except Exception:
        return _response(
            state=UNKNOWN_STATE,
            blocker="HTTP_V8_CONSUMER_EXCEPTION",
            binding_evaluation=evaluation,
        )
    try:
        expected_http_v8_response = _PINNED_HTTP_V8_BUILDER(
            http_v8_request,
            presentation_verification_context=http_v8_context,
        )
    except Exception:
        return _response(
            state=UNKNOWN_STATE,
            blocker="HTTP_V8_EXACT_REBUILD_EXCEPTION",
            binding_evaluation=evaluation,
        )
    if (
        not _self_hash_is_exact(http_v8_response, "response_hash")
        or http_v8_response != expected_http_v8_response
    ):
        return _response(
            state=UNKNOWN_STATE,
            blocker="HTTP_V8_RESPONSE_INVALID",
            binding_evaluation=evaluation,
        )
    try:
        http_v8_verified = _http_v8.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
            http_v8_response,
            http_v8_request,
            presentation_verification_context=http_v8_context,
        )
    except Exception:
        http_v8_verified = False
    if not http_v8_verified or not _http_v8_authority_is_locked(http_v8_response):
        return _response(
            state=UNKNOWN_STATE,
            blocker="HTTP_V8_VERIFICATION_OR_AUTHORITY_INVALID",
            binding_evaluation=evaluation,
        )
    return _response(
        state=KNOWN_BLOCKED_STATE,
        blocker=None,
        binding_evaluation=evaluation,
        http_v8_response=http_v8_response,
    )


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_response_v9(
    response: Any,
    request_payload: Any,
    *,
    multi_window_binding_verification_context: Any,
) -> bool:
    """Verify an exact rebuild without granting route or mount authority."""
    try:
        expected = build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_response_v9(
            request_payload,
            multi_window_binding_verification_context=(
                multi_window_binding_verification_context
            ),
        )
    except Exception:
        return False
    return bool(
        isinstance(response, dict)
        and _self_hash_is_exact(response, "response_hash")
        and response == expected
    )


__all__ = [
    "CONTRACT_HASH",
    "HTTP_V8_IMPLEMENTATION_SHA256",
    "INTERFACE_STATUS",
    "KNOWN_BLOCKED_STATE",
    "MULTI_WINDOW_BINDING_IMPLEMENTATION_SHA256",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATE",
    "build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_response_v9",
    "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_response_v9",
]
