from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from typing import Any


SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-contract-evidence-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-"
    "presentation-request-contract-evidence-candidate-v1-synthetic-"
    "unregistered-lock-1"
)
REQUEST_CONTRACT_PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-contract-payload-v1"
)
CANDIDATE_REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "http-candidate-request-v9"
)
ADR0334_BINDING_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "binding-v9"
)
ADR0334_BINDING_CONTRACT_HASH = (
    "32edce4777fa90cdc1c79536ea3187133775a368e0e1e401db9f82c165122e47"
)
ADR0334_BINDING_STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-"
    "presentation-v9-unmounted-lock-1"
)
METHOD = "POST"
ROUTE = (
    "/api/research/strategy-correlation-clusters/"
    "geometry-budget-multi-window-presentation-v9"
)
MAXIMUM_REQUEST_BYTES = 1_000_000

REQUEST_FIELDS = (
    "schema_version",
    "geometry_budget_multi_window_presentation_binding_evaluation",
    "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash",
)
REQUEST_ROLE_HASH = (
    "2d6ad49ff964471733c26c428a8450757d4e00c3f1f268510fd950d31a8d1928"
)
ADR0334_EVALUATION_FIELDS = (
    "schema_version",
    "status",
    "reason_code",
    "static_fingerprint",
    "contract_hash",
    "axis_order",
    "presentation_binding_evaluation_hash",
    "adapter_v7_hash",
    "multi_window_v8_hash",
    "multi_window_invocation_attempted",
    "multi_window_verified",
    "multi_window_status",
    "multi_window_decision",
    "multi_window_document",
    "mounted",
    "synthetic_only",
    "facts",
    "authority",
    "evaluation_hash",
)
ADR0334_EVALUATION_FIELD_ORDER_HASH = (
    "104f7e26f5ca98f8a3a8c6bd6a25e568dee4dcb3c37c743494664e7c7b68a793"
)
ADR0334_AUTHORITY_FIELDS = (
    "current_admission_allowed",
    "writer_allowed",
    "paper_authorized",
    "live_order_allowed",
)
ADR0334_FACT_FIELDS = (
    "ui_mounted",
    "http_candidate_registered",
    "runtime_consumer_bound",
)
REQUEST_CONTRACT_PAYLOAD_FIELDS = (
    "schema_version",
    "method",
    "route",
    "request_schema_version",
    "request_payload_hash",
    "adr0334_evaluation_hash",
)
REQUEST_CONTRACT_PAYLOAD_FIELD_ORDER_HASH = (
    "6845f7bfb8bfd07f21dad53d3f2d0580c4303a2920aed0d4462fd2cb27799a7e"
)
REQUEST_EVIDENCE_CONTRACT_HASH = (
    "0d0046487ff4fab91d2be6e7dc1e2da0d352560aabc16250009809164341725a"
)

_CANDIDATE_FIELDS = (
    "schema_version",
    "static_fingerprint",
    "interface_status",
    "status",
    "candidate_state",
    "synthetic_only",
    "registered",
    "request_evidence_contract_hash",
    "method",
    "route",
    "request_snapshot",
    "request_payload_hash",
    "request_contract_payload",
    "request_contract_hash",
    "adr0334_evaluation_hash",
    "facts",
    "blockers",
    "authority",
    "candidate_hash",
)
_BLOCKERS = (
    "UNREGISTERED_CANDIDATE",
    "SYNTHETIC_ONLY",
    "ADR0334_SOURCE_SEMANTICS_NOT_REVERIFIED",
    "EXTERNAL_HTTP_BODY_BINDING_UNVERIFIED",
    "TRANSPORT_PARSER_NOT_REGISTERED",
    "AUTHENTICATION_NOT_PERFORMED",
    "SECURITY_RECEIPT_SEMANTICS_UNVERIFIED",
    "REQUEST_LIFECYCLE_OWNER_UNREGISTERED",
    "HTTP_MOUNT_NOT_IMPLEMENTED",
    "CURRENT_ACTIVATION_NOT_AUTHORIZED",
    "PAPER_LIVE_UNAUTHORIZED",
)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_research_only": True,
        "request_content_integrity_verified": True,
        "adr0334_semantic_authority_granted": False,
        "external_http_body_authorized": False,
        "authenticated_request_authorized": False,
        "http_registration_authorized": False,
        "runtime_activation_authorized": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_authorized": False,
        "writer_allowed": False,
        "profitability_claimed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "request_snapshotted_once": True,
        "request_fields_exact_and_ordered": True,
        "request_payload_hash_derived_not_supplied": True,
        "request_contract_hash_derived_not_supplied": True,
        "adr0334_evaluation_hash_integrity_verified": True,
        "adr0334_evaluation_status_preserved": True,
        "adr0334_semantics_reverified": False,
        "adr0334_source_provenance_verified": False,
        "external_http_body_binding_verified": False,
        "transport_parser_authoritative": False,
        "authentication_performed": False,
        "request_snapshot_embedded": True,
        "request_snapshot_logging_allowed": False,
        "request_snapshot_response_embedding_allowed": False,
        "clockless": True,
    }


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


def _candidate_contract() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "request_contract_payload_schema_version": (
            REQUEST_CONTRACT_PAYLOAD_SCHEMA_VERSION
        ),
        "candidate_request_schema_version": CANDIDATE_REQUEST_SCHEMA_VERSION,
        "adr0334_binding_schema_version": ADR0334_BINDING_SCHEMA_VERSION,
        "adr0334_binding_contract_hash": ADR0334_BINDING_CONTRACT_HASH,
        "adr0334_binding_static_fingerprint": (
            ADR0334_BINDING_STATIC_FINGERPRINT
        ),
        "adr0334_evaluation_fields": list(ADR0334_EVALUATION_FIELDS),
        "adr0334_evaluation_field_order_hash": (
            ADR0334_EVALUATION_FIELD_ORDER_HASH
        ),
        "request_fields": list(REQUEST_FIELDS),
        "request_role_hash": REQUEST_ROLE_HASH,
        "request_contract_payload_fields": list(REQUEST_CONTRACT_PAYLOAD_FIELDS),
        "request_contract_payload_field_order_hash": (
            REQUEST_CONTRACT_PAYLOAD_FIELD_ORDER_HASH
        ),
        "method": METHOD,
        "route": ROUTE,
        "maximum_request_bytes": MAXIMUM_REQUEST_BYTES,
        "snapshot_mode": "EXACT_ORDERED_JSON_ADR0334_EVALUATION_HASH_BOUND",
        "status": "BLOCKED",
        "registered": False,
    }


def _adr0334_evaluation_integrity_verified(
    evaluation: Any,
    expected_evaluation_hash: Any,
) -> bool:
    if not _has_exact_fields(evaluation, ADR0334_EVALUATION_FIELDS):
        return False
    if not _is_sha256(expected_evaluation_hash):
        return False
    if evaluation["evaluation_hash"] != expected_evaluation_hash:
        return False
    if evaluation["schema_version"] != ADR0334_BINDING_SCHEMA_VERSION:
        return False
    if evaluation["contract_hash"] != ADR0334_BINDING_CONTRACT_HASH:
        return False
    if evaluation["static_fingerprint"] != ADR0334_BINDING_STATIC_FINGERPRINT:
        return False
    if evaluation["status"] not in ("PASS", "BLOCK", "UNKNOWN"):
        return False
    if evaluation["mounted"] is not False or evaluation["synthetic_only"] is not True:
        return False
    authority = evaluation["authority"]
    facts = evaluation["facts"]
    if not _has_exact_fields(authority, ADR0334_AUTHORITY_FIELDS):
        return False
    if not _has_exact_fields(facts, ADR0334_FACT_FIELDS):
        return False
    if not all(authority[field] is False for field in ADR0334_AUTHORITY_FIELDS):
        return False
    if not all(facts[field] is False for field in ADR0334_FACT_FIELDS):
        return False
    evaluation_without_hash = {
        field: evaluation[field]
        for field in ADR0334_EVALUATION_FIELDS
        if field != "evaluation_hash"
    }
    return _canonical_hash(evaluation_without_hash) == expected_evaluation_hash


def build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
    request_payload: Any,
) -> dict[str, Any] | None:
    if not _has_exact_fields(request_payload, REQUEST_FIELDS):
        return None
    try:
        request_snapshot = _snapshot_json_value(request_payload, set())
    except (RecursionError, TypeError, ValueError):
        return None
    if not _has_exact_fields(request_snapshot, REQUEST_FIELDS):
        return None
    if request_snapshot["schema_version"] != CANDIDATE_REQUEST_SCHEMA_VERSION:
        return None
    evaluation = request_snapshot[
        "geometry_budget_multi_window_presentation_binding_evaluation"
    ]
    expected_evaluation_hash = request_snapshot[
        "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash"
    ]
    if not _adr0334_evaluation_integrity_verified(
        evaluation,
        expected_evaluation_hash,
    ):
        return None
    canonical_request = _canonical_json_bytes(request_snapshot)
    if canonical_request is None or len(canonical_request) > MAXIMUM_REQUEST_BYTES:
        return None
    request_payload_hash = sha256(canonical_request).hexdigest()
    request_contract_payload = {
        "schema_version": REQUEST_CONTRACT_PAYLOAD_SCHEMA_VERSION,
        "method": METHOD,
        "route": ROUTE,
        "request_schema_version": CANDIDATE_REQUEST_SCHEMA_VERSION,
        "request_payload_hash": request_payload_hash,
        "adr0334_evaluation_hash": expected_evaluation_hash,
    }
    request_contract_hash = _canonical_hash(request_contract_payload)
    if request_contract_hash is None:
        raise RuntimeError("request contract payload must be hashable")
    candidate_without_hash = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "candidate_state": "REQUEST_CONTRACT_DERIVED_FROM_EXACT_ADR0334_SNAPSHOT",
        "synthetic_only": True,
        "registered": False,
        "request_evidence_contract_hash": REQUEST_EVIDENCE_CONTRACT_HASH,
        "method": METHOD,
        "route": ROUTE,
        "request_snapshot": request_snapshot,
        "request_payload_hash": request_payload_hash,
        "request_contract_payload": request_contract_payload,
        "request_contract_hash": request_contract_hash,
        "adr0334_evaluation_hash": expected_evaluation_hash,
        "facts": _facts(),
        "blockers": list(_BLOCKERS),
        "authority": _authority(),
    }
    candidate_hash = _canonical_hash(candidate_without_hash)
    if candidate_hash is None:
        raise RuntimeError("request evidence candidate must be hashable")
    return {**candidate_without_hash, "candidate_hash": candidate_hash}


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
    document: Any,
) -> bool:
    if not _has_exact_fields(document, _CANDIDATE_FIELDS):
        return False
    if not _has_exact_fields(document.get("request_snapshot"), REQUEST_FIELDS):
        return False
    if not _has_exact_fields(
        document.get("request_contract_payload"),
        REQUEST_CONTRACT_PAYLOAD_FIELDS,
    ):
        return False
    rebuilt = build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
        document["request_snapshot"]
    )
    return rebuilt is not None and document == rebuilt


if _canonical_hash(list(ADR0334_EVALUATION_FIELDS)) != (
    ADR0334_EVALUATION_FIELD_ORDER_HASH
):
    raise RuntimeError("ADR0334 evaluation field-order hash drifted")
if _canonical_hash(list(REQUEST_CONTRACT_PAYLOAD_FIELDS)) != (
    REQUEST_CONTRACT_PAYLOAD_FIELD_ORDER_HASH
):
    raise RuntimeError("request contract payload field-order hash drifted")
if _canonical_hash(_candidate_contract()) != REQUEST_EVIDENCE_CONTRACT_HASH:
    raise RuntimeError("ADR0341 request-evidence contract hash drifted")


__all__ = [
    "ADR0334_EVALUATION_FIELD_ORDER_HASH",
    "CANDIDATE_REQUEST_SCHEMA_VERSION",
    "MAXIMUM_REQUEST_BYTES",
    "METHOD",
    "REQUEST_CONTRACT_PAYLOAD_FIELD_ORDER_HASH",
    "REQUEST_EVIDENCE_CONTRACT_HASH",
    "REQUEST_FIELDS",
    "ROUTE",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1",
    "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1",
]
