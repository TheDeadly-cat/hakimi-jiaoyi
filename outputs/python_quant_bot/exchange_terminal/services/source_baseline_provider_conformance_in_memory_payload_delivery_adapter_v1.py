"""Build a bounded in-memory payload delivery envelope without an endpoint."""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_presentation_consumer_preregistration_v1 import (
    PAYLOAD_SCHEMA_VERSION,
    STATIC_FINGERPRINT as PAYLOAD_STATIC_FINGERPRINT,
)
from exchange_terminal.services.source_baseline_provider_conformance_application_load_descriptor_preregistration_v1 import (
    BINDING_SCHEMA_VERSION as LOAD_DESCRIPTOR_BINDING_SCHEMA_VERSION,
    SCHEMA_VERSION as LOAD_DESCRIPTOR_SCHEMA_VERSION,
    STATIC_FINGERPRINT as LOAD_DESCRIPTOR_STATIC_FINGERPRINT,
    verify_source_baseline_provider_conformance_application_load_descriptor_binding_candidate_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "source-baseline-provider-conformance-in-memory-payload-delivery-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20260823-source-baseline-provider-conformance-in-memory-delivery-v1-lock-1"
)
STATUS = "BLOCKED"

LOAD_DESCRIPTOR_IMPLEMENTATION_SHA256 = (
    "9bcd1f37f8c0ef85ddcfffed65dd1104b7317567e69972ad1469cf55886e7ae5"
)
LOAD_DESCRIPTOR_HASH = (
    "a842fe43de8b8c2b7bdd2c2978dfb4d09f03ca49aa8555d2ab3edcbe7cdbd7b2"
)


def _snapshot_json_value(value: Any, active_ids: set[int]) -> Any:
    if isinstance(value, Mapping):
        value_id = id(value)
        if value_id in active_ids:
            raise ValueError("cyclic mapping is not a JSON document")
        active_ids.add(value_id)
        try:
            snapshot: dict[str, Any] = {}
            for key in value:
                if type(key) is not str or key in snapshot:
                    raise TypeError("JSON object keys must be unique strings")
                snapshot[key] = _snapshot_json_value(value[key], active_ids)
            return snapshot
        finally:
            active_ids.remove(value_id)
    if type(value) is list:
        value_id = id(value)
        if value_id in active_ids:
            raise ValueError("cyclic list is not a JSON document")
        active_ids.add(value_id)
        try:
            return [_snapshot_json_value(item, active_ids) for item in value]
        finally:
            active_ids.remove(value_id)
    if value is None or type(value) in (bool, int, float, str):
        return value
    raise TypeError("input must contain only JSON-compatible values")


def _snapshot_json_mapping(document: Any) -> dict[str, Any] | None:
    if not isinstance(document, Mapping):
        return None
    try:
        snapshot = _snapshot_json_value(document, set())
    except Exception:
        return None
    return snapshot if type(snapshot) is dict else None


def _build_delivery_envelope(
    *,
    status: str,
    delivery_state: str,
    reason_code: str,
    load_descriptor_binding_hash: str | None,
    load_descriptor_hash: str | None,
    style_binding_hash: str | None,
    payload_candidate_hash: str | None,
    source_envelope_hash: str | None,
    payload_candidate: dict[str, Any] | None,
    descriptor_binding_exact: bool,
    payload_hash_matches_binding: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "delivery_state": delivery_state,
        "reason_code": reason_code,
        "transport": {
            "mode": "IN_MEMORY_JSON_DOCUMENT",
            "media_type": "application/json",
            "encoding": "UTF-8",
            "cache_policy": "NO_STORE",
            "endpoint": None,
            "route": None,
            "wire_bytes_built": False,
            "network_transport_used": False,
            "persistent_storage_used": False,
        },
        "consumer_contract": {
            "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
            "payload_static_fingerprint": PAYLOAD_STATIC_FINGERPRINT,
            "javascript_adapter_global": "HakimiSourceBaselineProviderConformanceInMemoryDeliveryAdapterV1",
            "javascript_verify_function": "verifyInMemoryPayloadDeliveryEnvelopeV1",
            "javascript_extract_function": "extractPayloadCandidateFromInMemoryEnvelopeV1",
            "javascript_receipt_function": "buildInMemoryPayloadConsumptionReceiptCandidateV1",
        },
        "provenance": {
            "load_descriptor_schema_version": LOAD_DESCRIPTOR_SCHEMA_VERSION,
            "load_descriptor_binding_schema_version": LOAD_DESCRIPTOR_BINDING_SCHEMA_VERSION,
            "load_descriptor_static_fingerprint": LOAD_DESCRIPTOR_STATIC_FINGERPRINT,
            "load_descriptor_implementation_sha256": LOAD_DESCRIPTOR_IMPLEMENTATION_SHA256,
            "load_descriptor_binding_hash": load_descriptor_binding_hash,
            "load_descriptor_hash": load_descriptor_hash,
            "style_binding_hash": style_binding_hash,
            "payload_candidate_hash": payload_candidate_hash,
            "source_envelope_hash": source_envelope_hash,
        },
        "payload_candidate": payload_candidate,
        "facts": {
            "descriptor_binding_exactly_verified": descriptor_binding_exact,
            "payload_hash_matches_descriptor_binding": payload_hash_matches_binding,
            "bounded_payload_embedded": payload_candidate is not None,
            "raw_source_documents_embedded": False,
            "raw_identity_material_embedded": False,
            "wire_bytes_built": False,
            "delivery_attempted": False,
            "network_accessed": False,
            "endpoint_present": False,
            "route_registered": False,
            "persistent_storage_used": False,
            "consumer_executed": False,
            "card_render_called": False,
            "dom_accessed": False,
            "browser_executed": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "wire_transport_allowed": False,
            "endpoint_registration_allowed": False,
            "route_registration_allowed": False,
            "persistent_storage_allowed": False,
            "consumer_execution_allowed": False,
            "card_render_allowed": False,
            "dom_access_allowed": False,
            "browser_execution_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "delivery_envelope_hash")


def _unknown_delivery(reason_code: str) -> dict[str, Any]:
    return _build_delivery_envelope(
        status="UNKNOWN",
        delivery_state="UNKNOWN",
        reason_code=reason_code,
        load_descriptor_binding_hash=None,
        load_descriptor_hash=None,
        style_binding_hash=None,
        payload_candidate_hash=None,
        source_envelope_hash=None,
        payload_candidate=None,
        descriptor_binding_exact=False,
        payload_hash_matches_binding=False,
    )


def build_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1(
    load_descriptor_binding_document: Any,
    load_descriptor_document: Any,
    style_binding_document: Any,
    consumer_registration_v2_document: Any,
    predecessor_consumer_binding_document: Any,
    predecessor_consumer_registration_document: Any,
    payload_candidate_document: Any,
    consumer_preregistration_document: Any,
    source_envelope_document: Any,
    conformance_plan_document: Any,
    provider_identity_binding_document: Any,
    namespace_preregistration_document: Any,
    identity_preregistration_document: Any,
    organization_identity_intake_document: Any,
    signer_source_trust_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
) -> dict[str, Any]:
    descriptor_binding_snapshot = _snapshot_json_mapping(
        load_descriptor_binding_document
    )
    if descriptor_binding_snapshot is None:
        return _unknown_delivery("LOAD_DESCRIPTOR_BINDING_SNAPSHOT_FAILED")
    payload_snapshot = _snapshot_json_mapping(payload_candidate_document)
    if payload_snapshot is None:
        return _unknown_delivery("PAYLOAD_CANDIDATE_SNAPSHOT_FAILED")

    descriptor_exact = verify_source_baseline_provider_conformance_application_load_descriptor_binding_candidate_v1(
        descriptor_binding_snapshot,
        load_descriptor_document,
        style_binding_document,
        consumer_registration_v2_document,
        predecessor_consumer_binding_document,
        predecessor_consumer_registration_document,
        payload_snapshot,
        consumer_preregistration_document,
        source_envelope_document,
        conformance_plan_document,
        provider_identity_binding_document,
        namespace_preregistration_document,
        identity_preregistration_document,
        organization_identity_intake_document,
        signer_source_trust_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
    )
    if not descriptor_exact:
        return _unknown_delivery("LOAD_DESCRIPTOR_BINDING_NOT_EXACT")
    if (
        payload_snapshot.get("payload_candidate_hash")
        != descriptor_binding_snapshot.get("payload_candidate_hash")
    ):
        return _unknown_delivery("PAYLOAD_HASH_DOES_NOT_MATCH_DESCRIPTOR_BINDING")

    return _build_delivery_envelope(
        status="BLOCKED",
        delivery_state="IN_MEMORY_DOCUMENT_BUILT_ENDPOINT_UNBOUND",
        reason_code="EXACT_BOUNDED_PAYLOAD_EMBEDDED_IN_MEMORY_WIRE_ENDPOINT_ROUTE_CONSUMER_RENDER_BROWSER_AND_MOUNT_ABSENT",
        load_descriptor_binding_hash=descriptor_binding_snapshot[
            "load_descriptor_binding_hash"
        ],
        load_descriptor_hash=descriptor_binding_snapshot["load_descriptor_hash"],
        style_binding_hash=descriptor_binding_snapshot["style_binding_hash"],
        payload_candidate_hash=payload_snapshot["payload_candidate_hash"],
        source_envelope_hash=payload_snapshot["source_envelope_hash"],
        payload_candidate=payload_snapshot,
        descriptor_binding_exact=True,
        payload_hash_matches_binding=True,
    )


def verify_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1(
    document: Any,
    load_descriptor_binding_document: Any,
    load_descriptor_document: Any,
    style_binding_document: Any,
    consumer_registration_v2_document: Any,
    predecessor_consumer_binding_document: Any,
    predecessor_consumer_registration_document: Any,
    payload_candidate_document: Any,
    consumer_preregistration_document: Any,
    source_envelope_document: Any,
    conformance_plan_document: Any,
    provider_identity_binding_document: Any,
    namespace_preregistration_document: Any,
    identity_preregistration_document: Any,
    organization_identity_intake_document: Any,
    signer_source_trust_preregistration_document: Any,
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
) -> bool:
    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    rebuilt = build_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1(
        load_descriptor_binding_document,
        load_descriptor_document,
        style_binding_document,
        consumer_registration_v2_document,
        predecessor_consumer_binding_document,
        predecessor_consumer_registration_document,
        payload_candidate_document,
        consumer_preregistration_document,
        source_envelope_document,
        conformance_plan_document,
        provider_identity_binding_document,
        namespace_preregistration_document,
        identity_preregistration_document,
        organization_identity_intake_document,
        signer_source_trust_preregistration_document,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
    )
    return strict_json_contract_equal(snapshot, rebuilt)
