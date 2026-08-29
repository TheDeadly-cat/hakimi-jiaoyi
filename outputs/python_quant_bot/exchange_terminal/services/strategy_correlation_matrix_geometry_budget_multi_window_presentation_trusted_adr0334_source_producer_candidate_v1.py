from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from typing import Any

from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9 import (
    CONTRACT_HASH as ADR0334_BINDING_CONTRACT_HASH,
    SCHEMA_VERSION as ADR0334_BINDING_SCHEMA_VERSION,
    STATIC_FINGERPRINT as ADR0334_BINDING_STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA_VERSION as ADR0334_VERIFICATION_SCHEMA_VERSION,
    evaluate_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9,
    verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9,
)
from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_candidate_v1 import (
    CANDIDATE_CONTRACT_HASH as SOURCE_RESOLVER_CANDIDATE_CONTRACT_HASH,
    SCOPE_RESOLVER_PREREGISTRATION_HASH,
    RequestLocalSourceContextCandidateV1,
    build_request_local_source_context_candidate_v1,
    verify_context_creation_receipt_v1,
    verify_request_scope_evidence_candidate_v1,
)
from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1 import (
    PROVIDER_OUTPUT_SCHEMA_VERSION,
    PROVIDER_OUTPUT_SHAPE_HASH,
    REQUEST_ROLES,
    REQUEST_ROLE_HASH,
    VERIFICATION_CONTEXT_ROLES,
    VERIFICATION_CONTEXT_ROLE_HASH,
)


SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "trusted-adr0334-source-producer-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-"
    "presentation-trusted-adr0334-source-producer-candidate-v1-unbound-lock-1"
)
PRODUCTION_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "trusted-adr0334-source-production-receipt-v1"
)
CANDIDATE_REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "http-candidate-request-v9"
)
MAX_SOURCE_INPUT_BYTES = 1_000_000
MAX_CONTEXT_HANDOFF_COUNT = 1

_PINNED_REQUEST_ROLES = (
    "schema_version",
    "geometry_budget_multi_window_presentation_binding_evaluation",
    "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash",
)
_PINNED_VERIFICATION_CONTEXT_ROLES = (
    "presentation_binding_evaluation",
    "adapter_v7_document",
    "expected_evaluation_hash",
    "expected_presentation_binding_evaluation_hash",
    "expected_adapter_v7_hash",
    "presentation_binding_verification_context",
    "adapter_v7_verification_context",
)
_SOURCE_INPUT_FIELDS = (
    "presentation_binding_evaluation",
    "adapter_v7_document",
    "presentation_binding_verification_context",
    "adapter_v7_verification_context",
)
_ADR0334_VERIFICATION_RECEIPT_FIELDS = (
    "schema_version",
    "status",
    "evaluation_hash",
    "current_admission_allowed",
    "writer_allowed",
    "paper_authorized",
    "live_order_allowed",
)
_PRODUCTION_RECEIPT_FIELDS = (
    "schema_version",
    "candidate_contract_hash",
    "static_fingerprint",
    "status",
    "registered",
    "synthetic_only",
    "adr0334_binding_schema_version",
    "adr0334_binding_contract_hash",
    "adr0334_binding_static_fingerprint",
    "source_resolver_candidate_contract_hash",
    "scope_resolver_preregistration_hash",
    "request_scope_evidence_hash",
    "request_local_context_creation_receipt_hash",
    "adr0334_evaluation_hash",
    "adr0334_verification_receipt",
    "request_role_hash",
    "verification_context_role_hash",
    "provider_output_shape_hash",
    "source_documents_embedded",
    "facts",
    "blockers",
    "authority",
    "production_receipt_hash",
)
_BLOCKERS = (
    "ADR0340_SYNTHETIC_CANDIDATE_ONLY",
    "SECURITY_RECEIPTS_SEMANTICALLY_UNVERIFIED",
    "AUTHENTICATED_REQUEST_SCOPE_PROVIDER_UNREGISTERED",
    "TRUSTED_ADR0334_SOURCE_PRODUCER_UNREGISTERED",
    "SOURCE_PROVENANCE_NOT_CRYPTOGRAPHICALLY_AUTHENTICATED",
    "TRUSTED_INTERNAL_PROVIDER_IMPLEMENTATION_MISSING",
    "HANDLER_BINDING_UNAUTHORIZED",
    "ROUTE_NOT_REGISTERED",
    "CURRENT_ACTIVATION_NOT_AUTHORIZED",
    "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
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


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _has_exact_fields(value: Any, expected_fields: tuple[str, ...]) -> bool:
    return type(value) is dict and tuple(value) == expected_fields


def _snapshot_json_value(value: Any, active_container_ids: set[int]) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        return value
    if type(value) is list:
        identity = id(value)
        if identity in active_container_ids:
            raise ValueError("cyclic JSON list")
        active_container_ids.add(identity)
        try:
            return [
                _snapshot_json_value(item, active_container_ids) for item in value
            ]
        finally:
            active_container_ids.remove(identity)
    if type(value) is dict:
        identity = id(value)
        if identity in active_container_ids:
            raise ValueError("cyclic JSON object")
        if not all(type(key) is str for key in value):
            raise TypeError("JSON object keys must be strings")
        active_container_ids.add(identity)
        try:
            return {
                key: _snapshot_json_value(item, active_container_ids)
                for key, item in value.items()
            }
        finally:
            active_container_ids.remove(identity)
    raise TypeError("value is not an exact JSON tree")


def _snapshot_source_inputs(
    *,
    presentation_binding_evaluation: Any,
    adapter_v7_document: Any,
    presentation_binding_verification_context: Any,
    adapter_v7_verification_context: Any,
) -> dict[str, dict[str, Any]] | None:
    source_inputs = {
        "presentation_binding_evaluation": presentation_binding_evaluation,
        "adapter_v7_document": adapter_v7_document,
        "presentation_binding_verification_context": (
            presentation_binding_verification_context
        ),
        "adapter_v7_verification_context": adapter_v7_verification_context,
    }
    if not all(type(value) is dict for value in source_inputs.values()):
        return None
    try:
        snapshot = {
            name: _snapshot_json_value(value, set())
            for name, value in source_inputs.items()
        }
    except (RecursionError, TypeError, ValueError):
        return None
    canonical_source_inputs = _canonical_json_bytes(snapshot)
    if (
        canonical_source_inputs is None
        or len(canonical_source_inputs) > MAX_SOURCE_INPUT_BYTES
    ):
        return None
    return snapshot


def _candidate_contract() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "production_receipt_schema_version": PRODUCTION_RECEIPT_SCHEMA_VERSION,
        "adr0334_binding_schema_version": ADR0334_BINDING_SCHEMA_VERSION,
        "adr0334_binding_contract_hash": ADR0334_BINDING_CONTRACT_HASH,
        "adr0334_binding_static_fingerprint": ADR0334_BINDING_STATIC_FINGERPRINT,
        "adr0334_verification_schema_version": ADR0334_VERIFICATION_SCHEMA_VERSION,
        "source_resolver_candidate_contract_hash": (
            SOURCE_RESOLVER_CANDIDATE_CONTRACT_HASH
        ),
        "scope_resolver_preregistration_hash": SCOPE_RESOLVER_PREREGISTRATION_HASH,
        "provider_output_schema_version": PROVIDER_OUTPUT_SCHEMA_VERSION,
        "provider_output_shape_hash": PROVIDER_OUTPUT_SHAPE_HASH,
        "candidate_request_schema_version": CANDIDATE_REQUEST_SCHEMA_VERSION,
        "request_roles": list(REQUEST_ROLES),
        "request_role_hash": REQUEST_ROLE_HASH,
        "verification_context_roles": list(VERIFICATION_CONTEXT_ROLES),
        "verification_context_role_hash": VERIFICATION_CONTEXT_ROLE_HASH,
        "maximum_source_input_bytes": MAX_SOURCE_INPUT_BYTES,
        "maximum_context_handoff_count": MAX_CONTEXT_HANDOFF_COUNT,
        "source_mode": "EXPLICIT_INTERNAL_ADR0334_ARGUMENTS_DERIVED_HASHES_ONLY",
        "status": "BLOCKED",
        "registered": False,
    }


CANDIDATE_CONTRACT_HASH = (
    "f6148d309a3343324347019811055f449d7621046afd460e5a79d3b622da9389"
)


def _facts() -> dict[str, bool]:
    return {
        "adr0334_evaluation_constructed_inside_candidate": True,
        "adr0334_exact_verifier_passed": True,
        "expected_hashes_derived_from_source_documents": True,
        "request_and_context_role_order_frozen": True,
        "request_local_context_created": True,
        "source_documents_retained_by_producer": False,
        "security_receipts_semantically_verified": False,
        "request_scope_semantically_authenticated": False,
        "client_source_provenance_verified": False,
        "source_provenance_cryptographically_authenticated": False,
        "trusted_source_producer_registered": False,
        "trusted_internal_provider_bound": False,
        "handler_bound": False,
        "route_registered": False,
        "externally_callable": False,
        "runtime_assets_accessed": False,
        "runtime_mutations_performed": False,
        "profitability_proven": False,
    }


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "request_scope_trust_granted": False,
        "source_producer_registration_allowed": False,
        "provider_binding_allowed": False,
        "handler_binding_allowed": False,
        "route_registration_allowed": False,
        "external_call_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def _valid_adr0334_verification_receipt(
    receipt: Any,
    expected_evaluation_hash: str,
) -> bool:
    return (
        _has_exact_fields(receipt, _ADR0334_VERIFICATION_RECEIPT_FIELDS)
        and receipt["schema_version"] == ADR0334_VERIFICATION_SCHEMA_VERSION
        and receipt["status"] == "PASS"
        and receipt["evaluation_hash"] == expected_evaluation_hash
        and receipt["current_admission_allowed"] is False
        and receipt["writer_allowed"] is False
        and receipt["paper_authorized"] is False
        and receipt["live_order_allowed"] is False
    )


def _build_production_receipt_v1(
    *,
    request_scope_evidence_candidate: dict[str, Any],
    request_local_context_creation_receipt: dict[str, Any],
    adr0334_evaluation_hash: str,
    adr0334_verification_receipt: dict[str, Any],
) -> dict[str, Any]:
    request_scope_evidence_hash = _canonical_hash(
        request_scope_evidence_candidate
    )
    context_creation_receipt_hash = _canonical_hash(
        request_local_context_creation_receipt
    )
    if request_scope_evidence_hash is None or context_creation_receipt_hash is None:
        raise RuntimeError("verified candidate receipts must be hashable")
    receipt_without_hash = {
        "schema_version": PRODUCTION_RECEIPT_SCHEMA_VERSION,
        "candidate_contract_hash": CANDIDATE_CONTRACT_HASH,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "registered": False,
        "synthetic_only": True,
        "adr0334_binding_schema_version": ADR0334_BINDING_SCHEMA_VERSION,
        "adr0334_binding_contract_hash": ADR0334_BINDING_CONTRACT_HASH,
        "adr0334_binding_static_fingerprint": ADR0334_BINDING_STATIC_FINGERPRINT,
        "source_resolver_candidate_contract_hash": (
            SOURCE_RESOLVER_CANDIDATE_CONTRACT_HASH
        ),
        "scope_resolver_preregistration_hash": SCOPE_RESOLVER_PREREGISTRATION_HASH,
        "request_scope_evidence_hash": request_scope_evidence_hash,
        "request_local_context_creation_receipt_hash": (
            context_creation_receipt_hash
        ),
        "adr0334_evaluation_hash": adr0334_evaluation_hash,
        "adr0334_verification_receipt": deepcopy(adr0334_verification_receipt),
        "request_role_hash": REQUEST_ROLE_HASH,
        "verification_context_role_hash": VERIFICATION_CONTEXT_ROLE_HASH,
        "provider_output_shape_hash": PROVIDER_OUTPUT_SHAPE_HASH,
        "source_documents_embedded": False,
        "facts": _facts(),
        "blockers": list(_BLOCKERS),
        "authority": _authority(),
    }
    production_receipt_hash = _canonical_hash(receipt_without_hash)
    if production_receipt_hash is None:
        raise RuntimeError("production receipt must be hashable")
    return {
        **receipt_without_hash,
        "production_receipt_hash": production_receipt_hash,
    }


def verify_trusted_adr0334_source_production_receipt_v1(
    receipt: Any,
    request_scope_evidence_candidate: Any,
    request_local_context_creation_receipt: Any,
) -> bool:
    if not _has_exact_fields(receipt, _PRODUCTION_RECEIPT_FIELDS):
        return False
    if not verify_request_scope_evidence_candidate_v1(
        request_scope_evidence_candidate
    ):
        return False
    if not verify_context_creation_receipt_v1(
        request_local_context_creation_receipt,
        request_scope_evidence_candidate,
    ):
        return False
    evaluation_hash = receipt.get("adr0334_evaluation_hash")
    verification_receipt = receipt.get("adr0334_verification_receipt")
    if not _is_sha256(evaluation_hash):
        return False
    if not _valid_adr0334_verification_receipt(
        verification_receipt,
        evaluation_hash,
    ):
        return False
    rebuilt = _build_production_receipt_v1(
        request_scope_evidence_candidate=request_scope_evidence_candidate,
        request_local_context_creation_receipt=(
            request_local_context_creation_receipt
        ),
        adr0334_evaluation_hash=evaluation_hash,
        adr0334_verification_receipt=verification_receipt,
    )
    return receipt == rebuilt


_CONSTRUCTION_TOKEN = object()


class TrustedAdr0334SourceProducerCandidateV1:
    __slots__ = ("_request_local_context", "_receipt", "_consumed")

    def __init__(
        self,
        request_local_context: RequestLocalSourceContextCandidateV1,
        receipt: dict[str, Any],
        *,
        _construction_token: object | None = None,
    ) -> None:
        if _construction_token is not _CONSTRUCTION_TOKEN:
            raise TypeError(
                "use build_trusted_adr0334_source_producer_candidate_v1"
            )
        self._request_local_context = request_local_context
        self._receipt = receipt
        self._consumed = False

    @property
    def receipt(self) -> dict[str, Any]:
        return deepcopy(self._receipt)

    @property
    def consumed(self) -> bool:
        return self._consumed

    def __repr__(self) -> str:
        return (
            "TrustedAdr0334SourceProducerCandidateV1("
            f"consumed={self._consumed}, source_documents=REDACTED)"
        )

    def take_request_local_context_once(
        self,
    ) -> RequestLocalSourceContextCandidateV1 | None:
        if self._consumed:
            return None
        request_local_context = self._request_local_context
        self._request_local_context = None  # type: ignore[assignment]
        self._consumed = True
        return request_local_context


def build_trusted_adr0334_source_producer_candidate_v1(
    *,
    request_scope_evidence_candidate: Any,
    presentation_binding_evaluation: Any,
    adapter_v7_document: Any,
    presentation_binding_verification_context: Any,
    adapter_v7_verification_context: Any,
) -> TrustedAdr0334SourceProducerCandidateV1 | None:
    if not verify_request_scope_evidence_candidate_v1(
        request_scope_evidence_candidate
    ):
        return None
    source_inputs = _snapshot_source_inputs(
        presentation_binding_evaluation=presentation_binding_evaluation,
        adapter_v7_document=adapter_v7_document,
        presentation_binding_verification_context=(
            presentation_binding_verification_context
        ),
        adapter_v7_verification_context=adapter_v7_verification_context,
    )
    if source_inputs is None:
        return None
    expected_presentation_hash = source_inputs[
        "presentation_binding_evaluation"
    ].get("evaluation_hash")
    expected_adapter_hash = source_inputs["adapter_v7_document"].get(
        "adapter_v7_hash"
    )
    if not _is_sha256(expected_presentation_hash) or not _is_sha256(
        expected_adapter_hash
    ):
        return None
    try:
        evaluation = evaluate_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9(
            deepcopy(source_inputs["presentation_binding_evaluation"]),
            deepcopy(source_inputs["adapter_v7_document"]),
            expected_presentation_binding_evaluation_hash=(
                expected_presentation_hash
            ),
            expected_adapter_v7_hash=expected_adapter_hash,
            presentation_binding_verification_context=deepcopy(
                source_inputs["presentation_binding_verification_context"]
            ),
            adapter_v7_verification_context=deepcopy(
                source_inputs["adapter_v7_verification_context"]
            ),
        )
    except Exception:
        return None
    try:
        evaluation_snapshot = _snapshot_json_value(evaluation, set())
    except (RecursionError, TypeError, ValueError):
        return None
    if type(evaluation_snapshot) is not dict:
        return None
    evaluation_hash = evaluation_snapshot.get("evaluation_hash")
    if not _is_sha256(evaluation_hash):
        return None
    try:
        verification_receipt = verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9(
            deepcopy(evaluation_snapshot),
            deepcopy(source_inputs["presentation_binding_evaluation"]),
            deepcopy(source_inputs["adapter_v7_document"]),
            expected_evaluation_hash=evaluation_hash,
            expected_presentation_binding_evaluation_hash=(
                expected_presentation_hash
            ),
            expected_adapter_v7_hash=expected_adapter_hash,
            presentation_binding_verification_context=deepcopy(
                source_inputs["presentation_binding_verification_context"]
            ),
            adapter_v7_verification_context=deepcopy(
                source_inputs["adapter_v7_verification_context"]
            ),
        )
    except Exception:
        return None
    try:
        verification_receipt_snapshot = _snapshot_json_value(
            verification_receipt,
            set(),
        )
    except (RecursionError, TypeError, ValueError):
        return None
    if not _valid_adr0334_verification_receipt(
        verification_receipt_snapshot,
        evaluation_hash,
    ):
        return None
    request_role_values = {
        "schema_version": CANDIDATE_REQUEST_SCHEMA_VERSION,
        "geometry_budget_multi_window_presentation_binding_evaluation": (
            evaluation_snapshot
        ),
        "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash": (
            evaluation_hash
        ),
    }
    verification_context_values = {
        "presentation_binding_evaluation": source_inputs[
            "presentation_binding_evaluation"
        ],
        "adapter_v7_document": source_inputs["adapter_v7_document"],
        "expected_evaluation_hash": evaluation_hash,
        "expected_presentation_binding_evaluation_hash": (
            expected_presentation_hash
        ),
        "expected_adapter_v7_hash": expected_adapter_hash,
        "presentation_binding_verification_context": source_inputs[
            "presentation_binding_verification_context"
        ],
        "adapter_v7_verification_context": source_inputs[
            "adapter_v7_verification_context"
        ],
    }
    request_local_context = build_request_local_source_context_candidate_v1(
        request_scope_evidence_candidate=request_scope_evidence_candidate,
        request_role_values_in_contract_order=request_role_values,
        verification_context_values_in_contract_order=(
            verification_context_values
        ),
    )
    if request_local_context is None:
        return None
    production_receipt = _build_production_receipt_v1(
        request_scope_evidence_candidate=request_scope_evidence_candidate,
        request_local_context_creation_receipt=request_local_context.receipt,
        adr0334_evaluation_hash=evaluation_hash,
        adr0334_verification_receipt=verification_receipt_snapshot,
    )
    return TrustedAdr0334SourceProducerCandidateV1(
        request_local_context,
        production_receipt,
        _construction_token=_CONSTRUCTION_TOKEN,
    )


if tuple(REQUEST_ROLES) != _PINNED_REQUEST_ROLES:
    raise RuntimeError("ADR0337 request role order drifted")
if tuple(VERIFICATION_CONTEXT_ROLES) != _PINNED_VERIFICATION_CONTEXT_ROLES:
    raise RuntimeError("ADR0337 verification-context role order drifted")
if SOURCE_RESOLVER_CANDIDATE_CONTRACT_HASH != (
    "dcc7b3f75e89dc676594c3ab5370270eb7eec60e62f8ee542c38dc0c60d2df9f"
):
    raise RuntimeError("ADR0339 source-resolver candidate contract drifted")
if _canonical_hash(_candidate_contract()) != CANDIDATE_CONTRACT_HASH:
    raise RuntimeError("ADR0340 source-producer candidate contract drifted")
