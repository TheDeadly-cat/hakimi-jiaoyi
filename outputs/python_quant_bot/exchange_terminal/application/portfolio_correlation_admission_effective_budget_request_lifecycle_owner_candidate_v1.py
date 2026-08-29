"""Single-attempt, always-closing synthetic request lifecycle owner."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from collections.abc import Mapping
from threading import Lock
from typing import Any

from exchange_terminal.application.portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1 import (
    ADAPTER_CONTRACT_HASH,
    build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1,
    verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_consistency_candidate_v1,
)
from exchange_terminal.application.portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1 import (
    REQUEST_EVIDENCE_CONTRACT_HASH,
    verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_python_provider_binding_v1 import (
    EXPECTED_PROVIDER_BINDING_HASH,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_request_scope_source_resolver_candidate_v1 import (
    CANDIDATE_CONTRACT_HASH as REQUEST_SCOPE_SOURCE_RESOLVER_CONTRACT_HASH,
    RequestLocalSourceContextCandidateV1,
    verify_request_scope_evidence_candidate_v1,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-lifecycle-owner-"
    "candidate-contract-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-request-lifecycle-"
    "owner-candidate-v1-synthetic-unregistered-lock-2"
)
CREATION_RECEIPT_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-lifecycle-owner-"
    "creation-receipt-v1"
)
EXECUTION_RECEIPT_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-lifecycle-owner-"
    "execution-receipt-v1"
)
EXECUTION_RESULT_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-lifecycle-owner-"
    "execution-result-v1"
)
PRIOR_LIFECYCLE_OWNER_CONTRACT_HASH = (
    "5b4873fc01d928195283e4f31846a74336dd0a027876e55ac62b28032a791c03"
)
LIFECYCLE_OWNER_CONTRACT_HASH = (
    "f9e349c876a243a966429b98645a23e6d41e093ab58102980e760748c16cf42d"
)
MAXIMUM_ADAPTER_ATTEMPT_COUNT = 1

_CONSTRUCTION_TOKEN = object()
_BLOCKERS = (
    "UNREGISTERED_CANDIDATE",
    "SYNTHETIC_ONLY",
    "SECURITY_RECEIPT_SEMANTICS_UNVERIFIED",
    "AUTHENTICATED_REQUEST_OWNER_NOT_REGISTERED",
    "HTTP_MOUNT_NOT_IMPLEMENTED",
    "PAPER_LIVE_UNAUTHORIZED",
)
_AUTHORITY = {
    "descriptive_research_only": True,
    "authenticated_request_claimed": False,
    "http_registration_authorized": False,
    "runtime_activation_authorized": False,
    "paper_authorized": False,
    "live_authorized": False,
    "profitability_claimed": False,
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _safe_snapshot(value: Any) -> Any:
    return json.loads(
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=False,
        )
    )


def _seal(document: Mapping[str, Any], field: str) -> dict[str, Any]:
    sealed = dict(document)
    sealed[field] = _canonical_hash(document)
    return sealed


def _documents_are_bound(
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
) -> bool:
    return (
        verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            request_contract_evidence_candidate
        )
        and verify_request_scope_evidence_candidate_v1(
            request_scope_evidence_candidate
        )
        and request_scope_evidence_candidate["evidence"]["request_contract_hash"]
        == request_contract_evidence_candidate["request_contract_hash"]
    )


def _build_creation_receipt(
    request_contract_evidence_candidate: Mapping[str, Any],
    request_scope_evidence_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    evidence = request_scope_evidence_candidate["evidence"]
    receipt = {
        "schema_version": CREATION_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "owner_state": "CREATED_NOT_ATTEMPTED",
        "synthetic_only": True,
        "registered": False,
        "lifecycle_owner_contract_hash": LIFECYCLE_OWNER_CONTRACT_HASH,
        "prior_lifecycle_owner_contract_hash": (
            PRIOR_LIFECYCLE_OWNER_CONTRACT_HASH
        ),
        "request_evidence_contract_hash": REQUEST_EVIDENCE_CONTRACT_HASH,
        "request_scope_source_resolver_contract_hash": (
            REQUEST_SCOPE_SOURCE_RESOLVER_CONTRACT_HASH
        ),
        "projection_adapter_contract_hash": ADAPTER_CONTRACT_HASH,
        "request_candidate_hash": request_contract_evidence_candidate[
            "candidate_hash"
        ],
        "request_payload_hash": request_contract_evidence_candidate[
            "request_payload_hash"
        ],
        "request_contract_hash": request_contract_evidence_candidate[
            "request_contract_hash"
        ],
        "request_scope_candidate_hash": request_scope_evidence_candidate[
            "candidate_hash"
        ],
        "request_scope_evidence_hash": request_scope_evidence_candidate[
            "evidence_hash"
        ],
        "request_scope_id": evidence["request_scope_id"],
        "context_generation_id": evidence["context_generation_id"],
        "authentication_receipt_hash": evidence[
            "authentication_receipt_hash"
        ],
        "csrf_receipt_hash": evidence["csrf_receipt_hash"],
        "origin_receipt_hash": evidence["origin_receipt_hash"],
        "maximum_adapter_attempt_count": MAXIMUM_ADAPTER_ATTEMPT_COUNT,
        "close_after_any_attempt": True,
        "facts": {
            "request_and_scope_exactly_bound": True,
            "request_lifecycle_owned_in_memory": True,
            "atomic_in_process_attempt_claim": True,
            "context_consumption_observation_type_guarded": True,
            "security_receipts_hash_bound": True,
            "security_receipt_semantics_verified": False,
            "source_documents_embedded": False,
            "clockless": True,
        },
        "blockers": list(_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(receipt, "creation_receipt_hash")


def verify_portfolio_correlation_admission_effective_budget_request_lifecycle_creation_receipt_v1(
    document: Any,
    *,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
) -> bool:
    if not isinstance(document, Mapping) or not _documents_are_bound(
        request_contract_evidence_candidate,
        request_scope_evidence_candidate,
    ):
        return False
    expected = _build_creation_receipt(
        request_contract_evidence_candidate,
        request_scope_evidence_candidate,
    )
    return document == expected


def _build_execution_receipt(
    creation_receipt: Mapping[str, Any],
    *,
    provider_input_hash: str | None,
    adapter_candidate: Mapping[str, Any] | None,
    context_consumed: bool,
) -> dict[str, Any]:
    adapter_accepted = adapter_candidate is not None
    receipt = {
        "schema_version": EXECUTION_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "owner_state": "CLOSED_AFTER_SINGLE_ADAPTER_ATTEMPT",
        "execution_outcome": (
            "ADAPTER_ACCEPTED" if adapter_accepted else "ADAPTER_REJECTED"
        ),
        "synthetic_only": True,
        "registered": False,
        "lifecycle_owner_contract_hash": LIFECYCLE_OWNER_CONTRACT_HASH,
        "prior_lifecycle_owner_contract_hash": (
            PRIOR_LIFECYCLE_OWNER_CONTRACT_HASH
        ),
        "creation_receipt_hash": creation_receipt["creation_receipt_hash"],
        "provider_input_hash": provider_input_hash,
        "expected_provider_binding_hash": EXPECTED_PROVIDER_BINDING_HASH,
        "adapter_hash": (
            adapter_candidate["adapter_hash"] if adapter_accepted else None
        ),
        "projection_response_hash": (
            adapter_candidate["projection_response_hash"]
            if adapter_accepted
            else None
        ),
        "adapter_attempt_count": 1,
        "maximum_adapter_attempt_count": MAXIMUM_ADAPTER_ATTEMPT_COUNT,
        "closed": True,
        "context_consumed_observed": context_consumed,
        "source_documents_embedded": False,
        "facts": {
            "retry_possible": False,
            "closed_after_any_attempt": True,
            "atomic_in_process_attempt_claim": True,
            "context_consumption_observation_type_guarded": True,
            "adapter_evidence_consistency_verified": adapter_accepted,
            "adapter_semantic_provenance_verified_here": False,
            "failure_reason_semantically_reexecuted": False,
            "security_receipt_semantics_verified": False,
        },
        "blockers": list(_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(receipt, "execution_receipt_hash")


def _build_execution_result(
    creation_receipt: Mapping[str, Any],
    execution_receipt: Mapping[str, Any],
    adapter_candidate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    result = {
        "schema_version": EXECUTION_RESULT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "synthetic_only": True,
        "registered": False,
        "creation_receipt": deepcopy(creation_receipt),
        "adapter_candidate": deepcopy(adapter_candidate),
        "execution_receipt": deepcopy(execution_receipt),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(result, "result_hash")


def verify_portfolio_correlation_admission_effective_budget_request_lifecycle_execution_result_candidate_v1(
    document: Any,
    *,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
    provider_binding_document: Any,
    context_consumed_observed: bool,
) -> bool:
    if not isinstance(document, Mapping) or not isinstance(
        context_consumed_observed, bool
    ):
        return False
    creation_receipt = document.get("creation_receipt")
    if not verify_portfolio_correlation_admission_effective_budget_request_lifecycle_creation_receipt_v1(
        creation_receipt,
        request_contract_evidence_candidate=request_contract_evidence_candidate,
        request_scope_evidence_candidate=request_scope_evidence_candidate,
    ):
        return False
    try:
        provider_snapshot = _safe_snapshot(provider_binding_document)
        provider_input_hash = _canonical_hash(provider_snapshot)
    except (TypeError, ValueError, OverflowError):
        provider_snapshot = None
        provider_input_hash = None
    adapter_candidate = document.get("adapter_candidate")
    if adapter_candidate is not None and (
        provider_snapshot is None
        or not verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_consistency_candidate_v1(
            adapter_candidate,
            request_contract_evidence_candidate,
            provider_binding_document=provider_snapshot,
            request_scope_evidence_candidate=request_scope_evidence_candidate,
        )
    ):
        return False
    execution_receipt = _build_execution_receipt(
        creation_receipt,
        provider_input_hash=provider_input_hash,
        adapter_candidate=adapter_candidate,
        context_consumed=context_consumed_observed,
    )
    expected = _build_execution_result(
        creation_receipt,
        execution_receipt,
        adapter_candidate,
    )
    return document == expected


class RequestLifecycleOwnerCandidateV1:
    """Own one request/scope pair and close after one adapter attempt."""

    __slots__ = (
        "_request_evidence",
        "_request_scope",
        "_creation_receipt",
        "_execution_receipt",
        "_attempt_lock",
        "_attempted",
        "_closed",
    )

    def __init__(
        self,
        request_evidence: Mapping[str, Any],
        request_scope: Mapping[str, Any],
        creation_receipt: Mapping[str, Any],
        *,
        _construction_token: object | None = None,
    ) -> None:
        if _construction_token is not _CONSTRUCTION_TOKEN:
            raise TypeError(
                "use build_portfolio_correlation_admission_effective_budget_"
                "request_lifecycle_owner_candidate_v1"
            )
        self._request_evidence = dict(request_evidence)
        self._request_scope = dict(request_scope)
        self._creation_receipt = dict(creation_receipt)
        self._execution_receipt: dict[str, Any] | None = None
        self._attempt_lock = Lock()
        self._attempted = False
        self._closed = False

    def __repr__(self) -> str:
        with self._attempt_lock:
            attempted = self._attempted
            closed = self._closed
        return (
            "<RequestLifecycleOwnerCandidateV1 "
            f"attempted={attempted} closed={closed} "
            "request_and_sources=REDACTED>"
        )

    @property
    def attempted(self) -> bool:
        with self._attempt_lock:
            return self._attempted

    @property
    def closed(self) -> bool:
        with self._attempt_lock:
            return self._closed

    @property
    def creation_receipt(self) -> dict[str, Any]:
        return deepcopy(self._creation_receipt)

    @property
    def execution_receipt(self) -> dict[str, Any] | None:
        return deepcopy(self._execution_receipt)

    def execute_once(
        self,
        *,
        provider_binding_document: Any,
        request_local_source_context_candidate: Any,
    ) -> dict[str, Any] | None:
        with self._attempt_lock:
            if self._attempted or self._closed:
                return None
            self._attempted = True
        try:
            provider_snapshot = _safe_snapshot(provider_binding_document)
            provider_input_hash = _canonical_hash(provider_snapshot)
        except (TypeError, ValueError, OverflowError):
            provider_snapshot = None
            provider_input_hash = None
        adapter_candidate = None
        if provider_snapshot is not None:
            try:
                candidate = build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1(
                    self._request_evidence,
                    provider_binding_document=provider_snapshot,
                    request_scope_evidence_candidate=self._request_scope,
                    request_local_source_context_candidate=(
                        request_local_source_context_candidate
                    ),
                )
            except Exception:
                candidate = None
            if candidate is not None and verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_consistency_candidate_v1(
                candidate,
                self._request_evidence,
                provider_binding_document=provider_snapshot,
                request_scope_evidence_candidate=self._request_scope,
            ):
                adapter_candidate = candidate
        with self._attempt_lock:
            self._closed = True
        context_consumed = (
            type(request_local_source_context_candidate)
            is RequestLocalSourceContextCandidateV1
            and request_local_source_context_candidate.consumed
        )
        self._execution_receipt = _build_execution_receipt(
            self._creation_receipt,
            provider_input_hash=provider_input_hash,
            adapter_candidate=adapter_candidate,
            context_consumed=context_consumed,
        )
        result = _build_execution_result(
            self._creation_receipt,
            self._execution_receipt,
            adapter_candidate,
        )
        self._request_evidence = {}
        self._request_scope = {}
        return result


def build_portfolio_correlation_admission_effective_budget_request_lifecycle_owner_candidate_v1(
    *,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
) -> RequestLifecycleOwnerCandidateV1 | None:
    try:
        request_snapshot = _safe_snapshot(request_contract_evidence_candidate)
        scope_snapshot = _safe_snapshot(request_scope_evidence_candidate)
    except (TypeError, ValueError, OverflowError):
        return None
    if not _documents_are_bound(request_snapshot, scope_snapshot):
        return None
    creation_receipt = _build_creation_receipt(
        request_snapshot,
        scope_snapshot,
    )
    return RequestLifecycleOwnerCandidateV1(
        request_snapshot,
        scope_snapshot,
        creation_receipt,
        _construction_token=_CONSTRUCTION_TOKEN,
    )


__all__ = [
    "CREATION_RECEIPT_SCHEMA_VERSION",
    "EXECUTION_RECEIPT_SCHEMA_VERSION",
    "EXECUTION_RESULT_SCHEMA_VERSION",
    "LIFECYCLE_OWNER_CONTRACT_HASH",
    "MAXIMUM_ADAPTER_ATTEMPT_COUNT",
    "PRIOR_LIFECYCLE_OWNER_CONTRACT_HASH",
    "RequestLifecycleOwnerCandidateV1",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_portfolio_correlation_admission_effective_budget_request_lifecycle_owner_candidate_v1",
    "verify_portfolio_correlation_admission_effective_budget_request_lifecycle_creation_receipt_v1",
    "verify_portfolio_correlation_admission_effective_budget_request_lifecycle_execution_result_candidate_v1",
]
