from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from typing import Any

from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_preregistration_v1 import (
    CROSS_BINDING_CONTRACT_HASH,
    PROVIDER_PREREGISTRATION_HASH,
    REQUEST_SCOPE_CONTRACT_HASH,
    REQUEST_SCOPE_FIELD_ORDER_HASH,
    REQUEST_SCOPE_SCHEMA_VERSION,
    SOURCE_RESOLVER_CONTRACT_HASH,
    SOURCE_RESOLVER_SCHEMA_VERSION,
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
    "request-scope-source-resolver-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-"
    "presentation-request-scope-source-resolver-candidate-v1-unbound-lock-1"
)
REQUEST_SCOPE_EVIDENCE_CANDIDATE_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-scope-evidence-candidate-v1"
)
CONTEXT_CREATION_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-local-source-context-creation-receipt-v1"
)
CONTEXT_CONSUMPTION_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-local-source-context-consumption-receipt-v1"
)
SOURCE_RESOLUTION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-local-source-resolution-v1"
)

SCOPE_RESOLVER_PREREGISTRATION_HASH = (
    "6d6b20197a5341b5462716b97dc968e4e5496d10d4c752b3d5d5d86a70345586"
)
PROPOSED_METHOD = "POST"
PROPOSED_ROUTE = (
    "/api/research/strategy-correlation-clusters/"
    "geometry-budget-multi-window-presentation-v9"
)
REQUEST_SOURCE_COUNT = 3
VERIFICATION_CONTEXT_SOURCE_COUNT = 7
MAXIMUM_RESOLUTION_COUNT = 1
MAX_CANONICAL_CONTEXT_BYTES = 1_000_000

REQUEST_SCOPE_FIELD_ORDER = (
    "schema_version",
    "request_scope_id",
    "authentication_receipt_hash",
    "csrf_receipt_hash",
    "origin_receipt_hash",
    "request_contract_hash",
    "method",
    "route",
    "context_generation_id",
    "maximum_resolution_count",
    "consumed",
)

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

_SCOPE_TOP_LEVEL_FIELDS = (
    "schema_version",
    "static_fingerprint",
    "candidate_contract_hash",
    "scope_resolver_preregistration_hash",
    "request_scope_contract_hash",
    "source_resolver_contract_hash",
    "cross_binding_contract_hash",
    "status",
    "registered",
    "synthetic_only",
    "evidence",
    "facts",
    "blockers",
    "authority",
)
_CONTEXT_CREATION_RECEIPT_FIELDS = (
    "schema_version",
    "candidate_contract_hash",
    "static_fingerprint",
    "scope_resolver_preregistration_hash",
    "request_scope_id",
    "context_generation_id",
    "request_scope_evidence_hash",
    "request_role_hash",
    "verification_context_role_hash",
    "provider_output_shape_hash",
    "request_source_hashes_by_role",
    "verification_context_source_hashes_by_role",
    "context_hash",
    "maximum_resolution_count",
    "source_documents_embedded",
    "source_role_meaning_reverified",
    "receipt_authenticated",
)
_CONTEXT_CONSUMPTION_RECEIPT_FIELDS = (
    "schema_version",
    "candidate_contract_hash",
    "request_scope_id",
    "context_generation_id",
    "request_scope_evidence_hash",
    "context_creation_receipt_hash",
    "context_hash",
    "resolution_count",
    "consumed",
    "discarded_after_resolution",
    "reusable",
)
_SOURCE_RESOLUTION_FIELDS = (
    "schema_version",
    "candidate_contract_hash",
    "provider_output_schema_version",
    "provider_output_shape_hash",
    "request_role_hash",
    "verification_context_role_hash",
    "request_scope_id",
    "context_generation_id",
    "request_role_values_in_contract_order",
    "verification_context_values_in_contract_order",
    "consumption_receipt",
)

_SCOPE_BLOCKERS = (
    "ADR0339_SYNTHETIC_CANDIDATE_ONLY",
    "SECURITY_RECEIPTS_SEMANTICALLY_UNVERIFIED",
    "AUTHENTICATED_REQUEST_SCOPE_PROVIDER_UNREGISTERED",
    "TRUSTED_ADR0334_SOURCE_PRODUCTION_UNBOUND",
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


def _snapshot_role_mapping(
    source_values: Any,
    expected_roles: tuple[str, ...],
) -> dict[str, Any] | None:
    if not _has_exact_fields(source_values, expected_roles):
        return None
    try:
        return {
            role: _snapshot_json_value(source_values[role], set())
            for role in expected_roles
        }
    except (RecursionError, TypeError, ValueError):
        return None


def _candidate_contract() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "scope_resolver_preregistration_hash": SCOPE_RESOLVER_PREREGISTRATION_HASH,
        "request_scope_contract_hash": REQUEST_SCOPE_CONTRACT_HASH,
        "source_resolver_contract_hash": SOURCE_RESOLVER_CONTRACT_HASH,
        "cross_binding_contract_hash": CROSS_BINDING_CONTRACT_HASH,
        "provider_preregistration_hash": PROVIDER_PREREGISTRATION_HASH,
        "provider_output_schema_version": PROVIDER_OUTPUT_SCHEMA_VERSION,
        "provider_output_shape_hash": PROVIDER_OUTPUT_SHAPE_HASH,
        "request_scope_evidence_schema_version": (
            REQUEST_SCOPE_EVIDENCE_CANDIDATE_SCHEMA_VERSION
        ),
        "context_creation_receipt_schema_version": (
            CONTEXT_CREATION_RECEIPT_SCHEMA_VERSION
        ),
        "context_consumption_receipt_schema_version": (
            CONTEXT_CONSUMPTION_RECEIPT_SCHEMA_VERSION
        ),
        "source_resolution_schema_version": SOURCE_RESOLUTION_SCHEMA_VERSION,
        "request_roles": list(REQUEST_ROLES),
        "request_role_hash": REQUEST_ROLE_HASH,
        "verification_context_roles": list(VERIFICATION_CONTEXT_ROLES),
        "verification_context_role_hash": VERIFICATION_CONTEXT_ROLE_HASH,
        "method": PROPOSED_METHOD,
        "route": PROPOSED_ROUTE,
        "maximum_resolution_count": MAXIMUM_RESOLUTION_COUNT,
        "maximum_canonical_context_bytes": MAX_CANONICAL_CONTEXT_BYTES,
        "construction_mode": "PURE_IN_MEMORY_EXPLICIT_SYNTHETIC_CALL_ONLY",
        "status": "BLOCKED",
        "registered": False,
    }


CANDIDATE_CONTRACT_HASH = (
    "dcc7b3f75e89dc676594c3ab5370270eb7eec60e62f8ee542c38dc0c60d2df9f"
)


def _scope_facts() -> dict[str, bool]:
    return {
        "request_local": True,
        "single_use": True,
        "clockless": True,
        "hash_shape_verified": True,
        "security_receipts_semantically_verified": False,
        "authentication_performed": False,
        "source_role_meaning_reverified": False,
        "request_scope_provider_registered": False,
        "trusted_source_producer_bound": False,
        "trusted_internal_provider_bound": False,
        "handler_bound": False,
        "route_registered": False,
        "externally_callable": False,
        "runtime_assets_accessed": False,
        "runtime_mutations_performed": False,
        "profitability_proven": False,
    }


def _scope_authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "security_receipt_trust_granted": False,
        "request_scope_registration_allowed": False,
        "source_production_binding_allowed": False,
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


def build_request_scope_evidence_candidate_v1(
    *,
    scope_resolver_preregistration_hash: Any,
    request_scope_id: Any,
    authentication_receipt_hash: Any,
    csrf_receipt_hash: Any,
    origin_receipt_hash: Any,
    request_contract_hash: Any,
    context_generation_id: Any,
) -> dict[str, Any] | None:
    if scope_resolver_preregistration_hash != SCOPE_RESOLVER_PREREGISTRATION_HASH:
        return None
    opaque_hashes = (
        request_scope_id,
        authentication_receipt_hash,
        csrf_receipt_hash,
        origin_receipt_hash,
        request_contract_hash,
        context_generation_id,
    )
    if not all(_is_sha256(value) for value in opaque_hashes):
        return None
    evidence = {
        "schema_version": REQUEST_SCOPE_SCHEMA_VERSION,
        "request_scope_id": request_scope_id,
        "authentication_receipt_hash": authentication_receipt_hash,
        "csrf_receipt_hash": csrf_receipt_hash,
        "origin_receipt_hash": origin_receipt_hash,
        "request_contract_hash": request_contract_hash,
        "method": PROPOSED_METHOD,
        "route": PROPOSED_ROUTE,
        "context_generation_id": context_generation_id,
        "maximum_resolution_count": MAXIMUM_RESOLUTION_COUNT,
        "consumed": False,
    }
    return {
        "schema_version": REQUEST_SCOPE_EVIDENCE_CANDIDATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "candidate_contract_hash": CANDIDATE_CONTRACT_HASH,
        "scope_resolver_preregistration_hash": SCOPE_RESOLVER_PREREGISTRATION_HASH,
        "request_scope_contract_hash": REQUEST_SCOPE_CONTRACT_HASH,
        "source_resolver_contract_hash": SOURCE_RESOLVER_CONTRACT_HASH,
        "cross_binding_contract_hash": CROSS_BINDING_CONTRACT_HASH,
        "status": "BLOCKED",
        "registered": False,
        "synthetic_only": True,
        "evidence": evidence,
        "facts": _scope_facts(),
        "blockers": list(_SCOPE_BLOCKERS),
        "authority": _scope_authority(),
    }


def verify_request_scope_evidence_candidate_v1(document: Any) -> bool:
    if not _has_exact_fields(document, _SCOPE_TOP_LEVEL_FIELDS):
        return False
    evidence = document.get("evidence")
    if not _has_exact_fields(evidence, REQUEST_SCOPE_FIELD_ORDER):
        return False
    rebuilt = build_request_scope_evidence_candidate_v1(
        scope_resolver_preregistration_hash=document.get(
            "scope_resolver_preregistration_hash"
        ),
        request_scope_id=evidence.get("request_scope_id"),
        authentication_receipt_hash=evidence.get("authentication_receipt_hash"),
        csrf_receipt_hash=evidence.get("csrf_receipt_hash"),
        origin_receipt_hash=evidence.get("origin_receipt_hash"),
        request_contract_hash=evidence.get("request_contract_hash"),
        context_generation_id=evidence.get("context_generation_id"),
    )
    return rebuilt is not None and document == rebuilt


def _role_hashes(
    source_values: dict[str, Any],
    expected_roles: tuple[str, ...],
) -> dict[str, str] | None:
    hashes: dict[str, str] = {}
    for role in expected_roles:
        source_hash = _canonical_hash(source_values[role])
        if source_hash is None:
            return None
        hashes[role] = source_hash
    return hashes


def _context_binding_hash(
    *,
    request_scope_id: str,
    context_generation_id: str,
    request_scope_evidence_hash: str,
    request_source_hashes_by_role: dict[str, str],
    verification_context_source_hashes_by_role: dict[str, str],
) -> str:
    binding = {
        "candidate_contract_hash": CANDIDATE_CONTRACT_HASH,
        "request_scope_id": request_scope_id,
        "context_generation_id": context_generation_id,
        "request_scope_evidence_hash": request_scope_evidence_hash,
        "request_role_hash": REQUEST_ROLE_HASH,
        "verification_context_role_hash": VERIFICATION_CONTEXT_ROLE_HASH,
        "request_source_hashes_by_role": request_source_hashes_by_role,
        "verification_context_source_hashes_by_role": (
            verification_context_source_hashes_by_role
        ),
    }
    context_hash = _canonical_hash(binding)
    if context_hash is None:
        raise RuntimeError("canonical context binding must be hashable")
    return context_hash


def _build_context_creation_receipt_v1(
    request_scope_evidence_candidate: dict[str, Any],
    request_source_hashes_by_role: dict[str, str],
    verification_context_source_hashes_by_role: dict[str, str],
) -> dict[str, Any]:
    evidence = request_scope_evidence_candidate["evidence"]
    scope_evidence_hash = _canonical_hash(request_scope_evidence_candidate)
    if scope_evidence_hash is None:
        raise RuntimeError("verified request scope evidence must be hashable")
    context_hash = _context_binding_hash(
        request_scope_id=evidence["request_scope_id"],
        context_generation_id=evidence["context_generation_id"],
        request_scope_evidence_hash=scope_evidence_hash,
        request_source_hashes_by_role=request_source_hashes_by_role,
        verification_context_source_hashes_by_role=(
            verification_context_source_hashes_by_role
        ),
    )
    return {
        "schema_version": CONTEXT_CREATION_RECEIPT_SCHEMA_VERSION,
        "candidate_contract_hash": CANDIDATE_CONTRACT_HASH,
        "static_fingerprint": STATIC_FINGERPRINT,
        "scope_resolver_preregistration_hash": SCOPE_RESOLVER_PREREGISTRATION_HASH,
        "request_scope_id": evidence["request_scope_id"],
        "context_generation_id": evidence["context_generation_id"],
        "request_scope_evidence_hash": scope_evidence_hash,
        "request_role_hash": REQUEST_ROLE_HASH,
        "verification_context_role_hash": VERIFICATION_CONTEXT_ROLE_HASH,
        "provider_output_shape_hash": PROVIDER_OUTPUT_SHAPE_HASH,
        "request_source_hashes_by_role": deepcopy(request_source_hashes_by_role),
        "verification_context_source_hashes_by_role": deepcopy(
            verification_context_source_hashes_by_role
        ),
        "context_hash": context_hash,
        "maximum_resolution_count": MAXIMUM_RESOLUTION_COUNT,
        "source_documents_embedded": False,
        "source_role_meaning_reverified": False,
        "receipt_authenticated": False,
    }


def _valid_role_hash_mapping(
    value: Any,
    expected_roles: tuple[str, ...],
) -> bool:
    return _has_exact_fields(value, expected_roles) and all(
        _is_sha256(value[role]) for role in expected_roles
    )


def verify_context_creation_receipt_v1(
    receipt: Any,
    request_scope_evidence_candidate: Any,
) -> bool:
    if not verify_request_scope_evidence_candidate_v1(
        request_scope_evidence_candidate
    ):
        return False
    if not _has_exact_fields(receipt, _CONTEXT_CREATION_RECEIPT_FIELDS):
        return False
    request_hashes = receipt.get("request_source_hashes_by_role")
    context_hashes = receipt.get("verification_context_source_hashes_by_role")
    if not _valid_role_hash_mapping(request_hashes, REQUEST_ROLES):
        return False
    if not _valid_role_hash_mapping(context_hashes, VERIFICATION_CONTEXT_ROLES):
        return False
    rebuilt = _build_context_creation_receipt_v1(
        request_scope_evidence_candidate,
        request_hashes,
        context_hashes,
    )
    return receipt == rebuilt


def _build_context_consumption_receipt_v1(
    creation_receipt: dict[str, Any],
) -> dict[str, Any]:
    creation_receipt_hash = _canonical_hash(creation_receipt)
    if creation_receipt_hash is None:
        raise RuntimeError("verified creation receipt must be hashable")
    return {
        "schema_version": CONTEXT_CONSUMPTION_RECEIPT_SCHEMA_VERSION,
        "candidate_contract_hash": CANDIDATE_CONTRACT_HASH,
        "request_scope_id": creation_receipt["request_scope_id"],
        "context_generation_id": creation_receipt["context_generation_id"],
        "request_scope_evidence_hash": creation_receipt[
            "request_scope_evidence_hash"
        ],
        "context_creation_receipt_hash": creation_receipt_hash,
        "context_hash": creation_receipt["context_hash"],
        "resolution_count": MAXIMUM_RESOLUTION_COUNT,
        "consumed": True,
        "discarded_after_resolution": True,
        "reusable": False,
    }


def verify_context_consumption_receipt_v1(
    receipt: Any,
    creation_receipt: Any,
    request_scope_evidence_candidate: Any,
) -> bool:
    if not verify_context_creation_receipt_v1(
        creation_receipt,
        request_scope_evidence_candidate,
    ):
        return False
    if not _has_exact_fields(receipt, _CONTEXT_CONSUMPTION_RECEIPT_FIELDS):
        return False
    return receipt == _build_context_consumption_receipt_v1(creation_receipt)


_CONSTRUCTION_TOKEN = object()


class RequestLocalSourceContextCandidateV1:
    __slots__ = (
        "_request_role_values",
        "_verification_context_values",
        "_creation_receipt",
        "_request_scope_evidence_candidate",
        "_consumed",
    )

    def __init__(
        self,
        request_role_values: dict[str, Any],
        verification_context_values: dict[str, Any],
        creation_receipt: dict[str, Any],
        request_scope_evidence_candidate: dict[str, Any],
        *,
        _construction_token: object | None = None,
    ) -> None:
        if _construction_token is not _CONSTRUCTION_TOKEN:
            raise TypeError("use build_request_local_source_context_candidate_v1")
        self._request_role_values = request_role_values
        self._verification_context_values = verification_context_values
        self._creation_receipt = creation_receipt
        self._request_scope_evidence_candidate = request_scope_evidence_candidate
        self._consumed = False

    @property
    def receipt(self) -> dict[str, Any]:
        return deepcopy(self._creation_receipt)

    @property
    def consumed(self) -> bool:
        return self._consumed

    def __repr__(self) -> str:
        return (
            "RequestLocalSourceContextCandidateV1("
            f"consumed={self._consumed}, source_documents=REDACTED)"
        )

    def resolve_once(self) -> dict[str, Any] | None:
        if self._consumed:
            return None
        evidence = self._request_scope_evidence_candidate["evidence"]
        consumption_receipt = _build_context_consumption_receipt_v1(
            self._creation_receipt
        )
        resolved = {
            "schema_version": SOURCE_RESOLUTION_SCHEMA_VERSION,
            "candidate_contract_hash": CANDIDATE_CONTRACT_HASH,
            "provider_output_schema_version": PROVIDER_OUTPUT_SCHEMA_VERSION,
            "provider_output_shape_hash": PROVIDER_OUTPUT_SHAPE_HASH,
            "request_role_hash": REQUEST_ROLE_HASH,
            "verification_context_role_hash": VERIFICATION_CONTEXT_ROLE_HASH,
            "request_scope_id": evidence["request_scope_id"],
            "context_generation_id": evidence["context_generation_id"],
            "request_role_values_in_contract_order": deepcopy(
                self._request_role_values
            ),
            "verification_context_values_in_contract_order": deepcopy(
                self._verification_context_values
            ),
            "consumption_receipt": consumption_receipt,
        }
        self._consumed = True
        self._request_role_values = {}
        self._verification_context_values = {}
        self._request_scope_evidence_candidate = {}
        return resolved


def build_request_local_source_context_candidate_v1(
    *,
    request_scope_evidence_candidate: Any,
    request_role_values_in_contract_order: Any,
    verification_context_values_in_contract_order: Any,
) -> RequestLocalSourceContextCandidateV1 | None:
    if not verify_request_scope_evidence_candidate_v1(
        request_scope_evidence_candidate
    ):
        return None
    if request_scope_evidence_candidate["evidence"]["consumed"] is not False:
        return None
    request_snapshot = _snapshot_role_mapping(
        request_role_values_in_contract_order,
        REQUEST_ROLES,
    )
    context_snapshot = _snapshot_role_mapping(
        verification_context_values_in_contract_order,
        VERIFICATION_CONTEXT_ROLES,
    )
    if request_snapshot is None or context_snapshot is None:
        return None
    canonical_context = _canonical_json_bytes(
        {
            "request_role_values_in_contract_order": request_snapshot,
            "verification_context_values_in_contract_order": context_snapshot,
        }
    )
    if (
        canonical_context is None
        or len(canonical_context) > MAX_CANONICAL_CONTEXT_BYTES
    ):
        return None
    request_hashes = _role_hashes(request_snapshot, REQUEST_ROLES)
    context_hashes = _role_hashes(context_snapshot, VERIFICATION_CONTEXT_ROLES)
    if request_hashes is None or context_hashes is None:
        return None
    scope_snapshot = deepcopy(request_scope_evidence_candidate)
    creation_receipt = _build_context_creation_receipt_v1(
        scope_snapshot,
        request_hashes,
        context_hashes,
    )
    return RequestLocalSourceContextCandidateV1(
        request_snapshot,
        context_snapshot,
        creation_receipt,
        scope_snapshot,
        _construction_token=_CONSTRUCTION_TOKEN,
    )


if tuple(REQUEST_ROLES) != _PINNED_REQUEST_ROLES:
    raise RuntimeError("ADR0337 request role order drifted")
if tuple(VERIFICATION_CONTEXT_ROLES) != _PINNED_VERIFICATION_CONTEXT_ROLES:
    raise RuntimeError("ADR0337 verification-context role order drifted")
if len(REQUEST_ROLES) != REQUEST_SOURCE_COUNT:
    raise RuntimeError("ADR0337 request role count drifted")
if len(VERIFICATION_CONTEXT_ROLES) != VERIFICATION_CONTEXT_SOURCE_COUNT:
    raise RuntimeError("ADR0337 verification-context role count drifted")
if REQUEST_SCOPE_FIELD_ORDER_HASH != (
    "d1ba8add3e26442d8f691f1b13e5a4c03c7107d52c277b63d90fb7f136524000"
):
    raise RuntimeError("ADR0338 request scope field order drifted")
if _canonical_hash(_candidate_contract()) != CANDIDATE_CONTRACT_HASH:
    raise RuntimeError("ADR0339 candidate contract hash drifted")
