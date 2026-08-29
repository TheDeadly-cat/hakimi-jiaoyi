from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from threading import Lock
from typing import Any

from exchange_terminal.application.strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1 import (
    REQUEST_EVIDENCE_CONTRACT_HASH,
)
from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_candidate_v1 import (
    CANDIDATE_CONTRACT_HASH as SOURCE_RESOLVER_CONTRACT_HASH,
)
from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_candidate_v1 import (
    EXPECTED_PREREGISTRATION_HASH as SECURITY_GATE_PREREGISTRATION_HASH,
    GATE_CONTRACT_HASH as SECURITY_GATE_CONTRACT_HASH,
    verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1,
    verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1,
)
from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_adr0334_source_producer_candidate_v1 import (
    CANDIDATE_CONTRACT_HASH as SOURCE_PRODUCER_CONTRACT_HASH,
)


SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-lifecycle-owner-candidate-contract-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-"
    "presentation-request-lifecycle-owner-candidate-v1-synthetic-"
    "unregistered-atomic-lock-1"
)
CREATION_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-lifecycle-owner-creation-receipt-v1"
)
CLAIM_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-lifecycle-owner-claim-receipt-v1"
)
CLAIM_RESULT_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-lifecycle-owner-claim-result-v1"
)
LIFECYCLE_OWNER_CONTRACT_HASH = (
    "73833a5ada7b94b52bbf7ec86130f033dab0ca582288b946a4d7a67498efd202"
)
MAXIMUM_CLAIM_ATTEMPT_COUNT = 1

_CONSTRUCTION_TOKEN = object()
_BLOCKERS = (
    "ADR0343_SYNTHETIC_OWNER_ONLY",
    "SECURITY_GATE_UNKNOWN",
    "SECURITY_SEMANTICS_UNAVAILABLE",
    "AUTHENTICATED_REQUEST_CLAIM_UNAVAILABLE",
    "DURABLE_IDEMPOTENCY_STORE_UNAVAILABLE",
    "CROSS_PROCESS_EXCLUSION_UNAVAILABLE",
    "TRUSTED_INTERNAL_PROVIDER_IMPLEMENTATION_MISSING",
    "HANDLER_BINDING_UNAUTHORIZED",
    "ROUTE_NOT_REGISTERED",
    "CURRENT_ACTIVATION_NOT_AUTHORIZED",
    "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
)
_AUTHORITY_FIELDS = (
    "descriptive_research_only",
    "authenticated_request_claimed",
    "lifecycle_activation_authorized",
    "provider_binding_authorized",
    "handler_binding_authorized",
    "http_registration_authorized",
    "runtime_activation_authorized",
    "current_admission_allowed",
    "paper_authorized",
    "live_authorized",
    "writer_allowed",
    "profitability_claimed",
)
_CREATION_FACT_FIELDS = (
    "security_gate_exactly_verified",
    "all_nonsecurity_cross_bindings_verified",
    "security_semantics_available",
    "authenticated_claim_possible",
    "request_lifecycle_owned_in_memory",
    "atomic_in_process_claim",
    "durable_idempotency_provided",
    "cross_process_exclusion_provided",
    "request_or_source_documents_embedded",
    "clockless",
)
_CLAIM_FACT_FIELDS = (
    "retry_possible",
    "closed_after_any_attempt",
    "atomic_in_process_claim",
    "security_gate_reexecuted_during_claim",
    "authenticated_claim_created",
    "context_consumption_attempted",
    "provider_invocation_attempted",
    "handler_invocation_attempted",
    "durable_idempotency_provided",
    "cross_process_exclusion_provided",
)
_CREATION_RECEIPT_FIELDS = (
    "schema_version",
    "static_fingerprint",
    "interface_status",
    "status",
    "owner_state",
    "synthetic_only",
    "registered",
    "lifecycle_owner_contract_hash",
    "security_gate_contract_hash",
    "security_gate_preregistration_hash",
    "request_evidence_contract_hash",
    "source_producer_contract_hash",
    "source_resolver_contract_hash",
    "security_gate_evaluation_hash",
    "security_gate_status",
    "security_gate_state",
    "permission_state",
    "request_evidence_candidate_hash",
    "request_contract_hash",
    "request_scope_candidate_hash",
    "request_scope_id",
    "context_generation_id",
    "adr0334_evaluation_hash",
    "source_production_receipt_hash",
    "context_creation_receipt_hash",
    "receipt_document_hashes",
    "maximum_claim_attempt_count",
    "close_after_any_attempt",
    "facts",
    "blockers",
    "authority",
    "creation_receipt_hash",
)
_CLAIM_RECEIPT_FIELDS = (
    "schema_version",
    "static_fingerprint",
    "interface_status",
    "status",
    "owner_state",
    "claim_outcome",
    "synthetic_only",
    "registered",
    "lifecycle_owner_contract_hash",
    "creation_receipt_hash",
    "security_gate_evaluation_hash",
    "claim_attempt_count",
    "maximum_claim_attempt_count",
    "closed",
    "authenticated_claim_created",
    "context_consumption_attempted",
    "provider_invocation_attempted",
    "handler_invocation_attempted",
    "facts",
    "blockers",
    "authority",
    "claim_receipt_hash",
)
_CLAIM_RESULT_FIELDS = (
    "schema_version",
    "static_fingerprint",
    "interface_status",
    "status",
    "synthetic_only",
    "registered",
    "creation_receipt",
    "claim_receipt",
    "authority",
    "result_hash",
)


def _canonical_json_bytes(value: Any) -> bytes | None:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (OverflowError, RecursionError, TypeError, ValueError):
        return None


def _canonical_hash(value: Any) -> str | None:
    payload = _canonical_json_bytes(value)
    if payload is None:
        return None
    return sha256(payload).hexdigest()


def _has_exact_fields(value: Any, fields: tuple[str, ...]) -> bool:
    return type(value) is dict and tuple(value) == fields


def _authority() -> dict[str, bool]:
    return {
        "descriptive_research_only": True,
        "authenticated_request_claimed": False,
        "lifecycle_activation_authorized": False,
        "provider_binding_authorized": False,
        "handler_binding_authorized": False,
        "http_registration_authorized": False,
        "runtime_activation_authorized": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_authorized": False,
        "writer_allowed": False,
        "profitability_claimed": False,
    }


def _candidate_contract() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "creation_receipt_schema_version": CREATION_RECEIPT_SCHEMA_VERSION,
        "claim_receipt_schema_version": CLAIM_RECEIPT_SCHEMA_VERSION,
        "claim_result_schema_version": CLAIM_RESULT_SCHEMA_VERSION,
        "security_gate_contract_hash": SECURITY_GATE_CONTRACT_HASH,
        "security_gate_preregistration_hash": SECURITY_GATE_PREREGISTRATION_HASH,
        "request_evidence_contract_hash": REQUEST_EVIDENCE_CONTRACT_HASH,
        "source_producer_contract_hash": SOURCE_PRODUCER_CONTRACT_HASH,
        "source_resolver_contract_hash": SOURCE_RESOLVER_CONTRACT_HASH,
        "maximum_claim_attempt_count": MAXIMUM_CLAIM_ATTEMPT_COUNT,
        "claim_mode": "ATOMIC_IN_PROCESS_ALWAYS_REJECT_UNKNOWN_GATE",
        "semantic_success_state_enabled": False,
        "status": "BLOCKED",
        "registered": False,
    }


def _inputs_exactly_verify(
    *,
    security_gate_preregistration_document: Any,
    security_gate_evaluation: Any,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
    source_production_receipt: Any,
    request_local_context_creation_receipt: Any,
    authentication_receipt_document: Any,
    csrf_receipt_document: Any,
    origin_receipt_document: Any,
) -> bool:
    return (
        verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1(
            security_gate_preregistration_document
        )
        and verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1(
            security_gate_evaluation,
            security_gate_preregistration_document,
            request_contract_evidence_candidate,
            request_scope_evidence_candidate,
            source_production_receipt,
            request_local_context_creation_receipt,
            authentication_receipt_document=authentication_receipt_document,
            csrf_receipt_document=csrf_receipt_document,
            origin_receipt_document=origin_receipt_document,
        )
        and security_gate_evaluation["status"] == "UNKNOWN"
        and security_gate_evaluation["gate_state"]
        == "SECURITY_SEMANTICS_UNAVAILABLE"
        and security_gate_evaluation["permission_state"] == "UNAUTHORIZED"
        and security_gate_evaluation["facts"]["security_semantics_verified"]
        is False
        and security_gate_evaluation["facts"][
            "authenticated_request_authorized"
        ]
        is False
    )


def _build_creation_receipt(
    security_gate_evaluation: dict[str, Any],
) -> dict[str, Any]:
    receipt_without_hash = {
        "schema_version": CREATION_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "owner_state": "CREATED_NOT_CLAIMED",
        "synthetic_only": True,
        "registered": False,
        "lifecycle_owner_contract_hash": LIFECYCLE_OWNER_CONTRACT_HASH,
        "security_gate_contract_hash": SECURITY_GATE_CONTRACT_HASH,
        "security_gate_preregistration_hash": SECURITY_GATE_PREREGISTRATION_HASH,
        "request_evidence_contract_hash": REQUEST_EVIDENCE_CONTRACT_HASH,
        "source_producer_contract_hash": SOURCE_PRODUCER_CONTRACT_HASH,
        "source_resolver_contract_hash": SOURCE_RESOLVER_CONTRACT_HASH,
        "security_gate_evaluation_hash": security_gate_evaluation[
            "evaluation_hash"
        ],
        "security_gate_status": security_gate_evaluation["status"],
        "security_gate_state": security_gate_evaluation["gate_state"],
        "permission_state": security_gate_evaluation["permission_state"],
        "request_evidence_candidate_hash": security_gate_evaluation[
            "request_evidence_candidate_hash"
        ],
        "request_contract_hash": security_gate_evaluation[
            "request_contract_hash"
        ],
        "request_scope_candidate_hash": security_gate_evaluation[
            "request_scope_candidate_hash"
        ],
        "request_scope_id": security_gate_evaluation["request_scope_id"],
        "context_generation_id": security_gate_evaluation[
            "context_generation_id"
        ],
        "adr0334_evaluation_hash": security_gate_evaluation[
            "adr0334_evaluation_hash"
        ],
        "source_production_receipt_hash": security_gate_evaluation[
            "source_production_receipt_hash"
        ],
        "context_creation_receipt_hash": security_gate_evaluation[
            "context_creation_receipt_hash"
        ],
        "receipt_document_hashes": deepcopy(
            security_gate_evaluation["receipt_document_hashes"]
        ),
        "maximum_claim_attempt_count": MAXIMUM_CLAIM_ATTEMPT_COUNT,
        "close_after_any_attempt": True,
        "facts": {
            "security_gate_exactly_verified": True,
            "all_nonsecurity_cross_bindings_verified": True,
            "security_semantics_available": False,
            "authenticated_claim_possible": False,
            "request_lifecycle_owned_in_memory": True,
            "atomic_in_process_claim": True,
            "durable_idempotency_provided": False,
            "cross_process_exclusion_provided": False,
            "request_or_source_documents_embedded": False,
            "clockless": True,
        },
        "blockers": list(_BLOCKERS),
        "authority": _authority(),
    }
    creation_receipt_hash = _canonical_hash(receipt_without_hash)
    if creation_receipt_hash is None:
        raise RuntimeError("creation receipt must be hashable")
    return {**receipt_without_hash, "creation_receipt_hash": creation_receipt_hash}


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_creation_receipt_v1(
    document: Any,
    *,
    security_gate_preregistration_document: Any,
    security_gate_evaluation: Any,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
    source_production_receipt: Any,
    request_local_context_creation_receipt: Any,
    authentication_receipt_document: Any = None,
    csrf_receipt_document: Any = None,
    origin_receipt_document: Any = None,
) -> bool:
    if not _has_exact_fields(document, _CREATION_RECEIPT_FIELDS):
        return False
    if not _has_exact_fields(document.get("facts"), _CREATION_FACT_FIELDS):
        return False
    if not _has_exact_fields(document.get("authority"), _AUTHORITY_FIELDS):
        return False
    if not _inputs_exactly_verify(
        security_gate_preregistration_document=(
            security_gate_preregistration_document
        ),
        security_gate_evaluation=security_gate_evaluation,
        request_contract_evidence_candidate=request_contract_evidence_candidate,
        request_scope_evidence_candidate=request_scope_evidence_candidate,
        source_production_receipt=source_production_receipt,
        request_local_context_creation_receipt=(
            request_local_context_creation_receipt
        ),
        authentication_receipt_document=authentication_receipt_document,
        csrf_receipt_document=csrf_receipt_document,
        origin_receipt_document=origin_receipt_document,
    ):
        return False
    return document == _build_creation_receipt(security_gate_evaluation)


def _build_claim_receipt(
    creation_receipt: dict[str, Any],
) -> dict[str, Any]:
    receipt_without_hash = {
        "schema_version": CLAIM_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "owner_state": "CLOSED_AFTER_SINGLE_CLAIM_ATTEMPT",
        "claim_outcome": "CLAIM_REJECTED_SECURITY_SEMANTICS_UNAVAILABLE",
        "synthetic_only": True,
        "registered": False,
        "lifecycle_owner_contract_hash": LIFECYCLE_OWNER_CONTRACT_HASH,
        "creation_receipt_hash": creation_receipt["creation_receipt_hash"],
        "security_gate_evaluation_hash": creation_receipt[
            "security_gate_evaluation_hash"
        ],
        "claim_attempt_count": MAXIMUM_CLAIM_ATTEMPT_COUNT,
        "maximum_claim_attempt_count": MAXIMUM_CLAIM_ATTEMPT_COUNT,
        "closed": True,
        "authenticated_claim_created": False,
        "context_consumption_attempted": False,
        "provider_invocation_attempted": False,
        "handler_invocation_attempted": False,
        "facts": {
            "retry_possible": False,
            "closed_after_any_attempt": True,
            "atomic_in_process_claim": True,
            "security_gate_reexecuted_during_claim": False,
            "authenticated_claim_created": False,
            "context_consumption_attempted": False,
            "provider_invocation_attempted": False,
            "handler_invocation_attempted": False,
            "durable_idempotency_provided": False,
            "cross_process_exclusion_provided": False,
        },
        "blockers": list(_BLOCKERS),
        "authority": _authority(),
    }
    claim_receipt_hash = _canonical_hash(receipt_without_hash)
    if claim_receipt_hash is None:
        raise RuntimeError("claim receipt must be hashable")
    return {**receipt_without_hash, "claim_receipt_hash": claim_receipt_hash}


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_claim_receipt_v1(
    document: Any,
    creation_receipt: Any,
) -> bool:
    if not _has_exact_fields(creation_receipt, _CREATION_RECEIPT_FIELDS):
        return False
    if not _has_exact_fields(document, _CLAIM_RECEIPT_FIELDS):
        return False
    if not _has_exact_fields(document.get("facts"), _CLAIM_FACT_FIELDS):
        return False
    if not _has_exact_fields(document.get("authority"), _AUTHORITY_FIELDS):
        return False
    return document == _build_claim_receipt(creation_receipt)


def _build_claim_result(
    creation_receipt: dict[str, Any],
    claim_receipt: dict[str, Any],
) -> dict[str, Any]:
    result_without_hash = {
        "schema_version": CLAIM_RESULT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "synthetic_only": True,
        "registered": False,
        "creation_receipt": deepcopy(creation_receipt),
        "claim_receipt": deepcopy(claim_receipt),
        "authority": _authority(),
    }
    result_hash = _canonical_hash(result_without_hash)
    if result_hash is None:
        raise RuntimeError("claim result must be hashable")
    return {**result_without_hash, "result_hash": result_hash}


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_claim_result_candidate_v1(
    document: Any,
    *,
    security_gate_preregistration_document: Any,
    security_gate_evaluation: Any,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
    source_production_receipt: Any,
    request_local_context_creation_receipt: Any,
    authentication_receipt_document: Any = None,
    csrf_receipt_document: Any = None,
    origin_receipt_document: Any = None,
) -> bool:
    if not _has_exact_fields(document, _CLAIM_RESULT_FIELDS):
        return False
    if not _has_exact_fields(document.get("authority"), _AUTHORITY_FIELDS):
        return False
    creation_receipt = document.get("creation_receipt")
    if not verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_creation_receipt_v1(
        creation_receipt,
        security_gate_preregistration_document=(
            security_gate_preregistration_document
        ),
        security_gate_evaluation=security_gate_evaluation,
        request_contract_evidence_candidate=request_contract_evidence_candidate,
        request_scope_evidence_candidate=request_scope_evidence_candidate,
        source_production_receipt=source_production_receipt,
        request_local_context_creation_receipt=(
            request_local_context_creation_receipt
        ),
        authentication_receipt_document=authentication_receipt_document,
        csrf_receipt_document=csrf_receipt_document,
        origin_receipt_document=origin_receipt_document,
    ):
        return False
    claim_receipt = document.get("claim_receipt")
    if not verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_claim_receipt_v1(
        claim_receipt,
        creation_receipt,
    ):
        return False
    return document == _build_claim_result(creation_receipt, claim_receipt)


class RequestLifecycleOwnerCandidateV1:
    __slots__ = (
        "_creation_receipt",
        "_claim_receipt",
        "_claim_lock",
        "_attempted",
        "_closed",
    )

    def __init__(
        self,
        creation_receipt: dict[str, Any],
        *,
        _construction_token: object | None = None,
    ) -> None:
        if _construction_token is not _CONSTRUCTION_TOKEN:
            raise TypeError(
                "use build_strategy_correlation_matrix_geometry_budget_multi_"
                "window_presentation_request_lifecycle_owner_candidate_v1"
            )
        self._creation_receipt = creation_receipt
        self._claim_receipt: dict[str, Any] | None = None
        self._claim_lock = Lock()
        self._attempted = False
        self._closed = False

    def __repr__(self) -> str:
        with self._claim_lock:
            attempted = self._attempted
            closed = self._closed
        return (
            "RequestLifecycleOwnerCandidateV1("
            f"attempted={attempted}, closed={closed}, "
            "request_receipts_and_sources=REDACTED)"
        )

    @property
    def attempted(self) -> bool:
        with self._claim_lock:
            return self._attempted

    @property
    def closed(self) -> bool:
        with self._claim_lock:
            return self._closed

    @property
    def creation_receipt(self) -> dict[str, Any]:
        return deepcopy(self._creation_receipt)

    @property
    def claim_receipt(self) -> dict[str, Any] | None:
        with self._claim_lock:
            return deepcopy(self._claim_receipt)

    def claim_once(self) -> dict[str, Any] | None:
        with self._claim_lock:
            if self._attempted or self._closed:
                return None
            self._attempted = True
            claim_receipt = _build_claim_receipt(self._creation_receipt)
            result = _build_claim_result(self._creation_receipt, claim_receipt)
            self._claim_receipt = claim_receipt
            self._closed = True
            return result


def build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_owner_candidate_v1(
    *,
    security_gate_preregistration_document: Any,
    security_gate_evaluation: Any,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
    source_production_receipt: Any,
    request_local_context_creation_receipt: Any,
    authentication_receipt_document: Any = None,
    csrf_receipt_document: Any = None,
    origin_receipt_document: Any = None,
) -> RequestLifecycleOwnerCandidateV1 | None:
    if not _inputs_exactly_verify(
        security_gate_preregistration_document=(
            security_gate_preregistration_document
        ),
        security_gate_evaluation=security_gate_evaluation,
        request_contract_evidence_candidate=request_contract_evidence_candidate,
        request_scope_evidence_candidate=request_scope_evidence_candidate,
        source_production_receipt=source_production_receipt,
        request_local_context_creation_receipt=(
            request_local_context_creation_receipt
        ),
        authentication_receipt_document=authentication_receipt_document,
        csrf_receipt_document=csrf_receipt_document,
        origin_receipt_document=origin_receipt_document,
    ):
        return None
    creation_receipt = _build_creation_receipt(security_gate_evaluation)
    return RequestLifecycleOwnerCandidateV1(
        creation_receipt,
        _construction_token=_CONSTRUCTION_TOKEN,
    )


if _canonical_hash(_candidate_contract()) != LIFECYCLE_OWNER_CONTRACT_HASH:
    raise RuntimeError("ADR0343 lifecycle-owner contract hash drifted")


__all__ = [
    "CLAIM_RECEIPT_SCHEMA_VERSION",
    "CLAIM_RESULT_SCHEMA_VERSION",
    "CREATION_RECEIPT_SCHEMA_VERSION",
    "LIFECYCLE_OWNER_CONTRACT_HASH",
    "MAXIMUM_CLAIM_ATTEMPT_COUNT",
    "RequestLifecycleOwnerCandidateV1",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_owner_candidate_v1",
    "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_claim_receipt_v1",
    "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_claim_result_candidate_v1",
    "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_lifecycle_creation_receipt_v1",
]
