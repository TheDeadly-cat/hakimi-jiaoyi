"""Register the dual-runtime in-memory delivery adapters without executing them."""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.services.source_baseline_provider_conformance_in_memory_payload_delivery_adapter_v1 import (
    LOAD_DESCRIPTOR_HASH,
    LOAD_DESCRIPTOR_IMPLEMENTATION_SHA256,
    SCHEMA_VERSION as DELIVERY_ENVELOPE_SCHEMA_VERSION,
    STATIC_FINGERPRINT as DELIVERY_ENVELOPE_STATIC_FINGERPRINT,
    verify_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "source-baseline-provider-conformance-in-memory-delivery-adapter-registration-v1"
)
BINDING_SCHEMA_VERSION = (
    "source-baseline-provider-conformance-in-memory-delivery-adapter-binding-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260823-source-baseline-provider-conformance-delivery-adapter-registration-v1-lock-1"
)
STATUS = "BLOCKED"

PYTHON_ADAPTER_IMPLEMENTATION_SHA256 = (
    "b6251351e821a455fa781c55d12a41db2ce03e576cbfca6dc78c4a4b767a0ee7"
)
PYTHON_ADAPTER_TEST_SHA256 = (
    "539cb33d229e8078c5d24c21c8c1bee254850399ccbe824de3b3a9fe79dcb0b6"
)
JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256 = (
    "46679b99d3c9c93529d6917960d4dbebc6caffe4b9053826f061cdd7877ab8ed"
)
JAVASCRIPT_ADAPTER_TEST_SHA256 = (
    "1e252e35ad490175423397aca6512640a90b3568ac93b0a6b1686b527ceda553"
)
ADR0287_SHA256 = (
    "b06cd1f4fd942d038d779923a0611d4ba46268e2840e85ea6b5b9df20560185c"
)
STRICT_CANONICAL_JS_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
)
CARD_IMPLEMENTATION_SHA256 = (
    "88a1ac27eaefd554e82129a5b2883d14af365965559d1d0e84db8dc32b1d9a5a"
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


def build_source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1() -> dict[str, Any]:
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "registration_state": "PYTHON_AND_JAVASCRIPT_ADAPTERS_REGISTERED_UNBOUND",
        "decision": "DUAL_RUNTIME_ADAPTERS_TESTS_AND_DEPENDENCIES_PINNED_PAYLOAD_SOURCE_ENDPOINT_HOST_LOAD_CONSUMER_EXECUTION_AND_MOUNT_ABSENT",
        "source_contract": {
            "load_descriptor_hash": LOAD_DESCRIPTOR_HASH,
            "load_descriptor_implementation_sha256": LOAD_DESCRIPTOR_IMPLEMENTATION_SHA256,
            "delivery_envelope_schema_version": DELIVERY_ENVELOPE_SCHEMA_VERSION,
            "delivery_envelope_static_fingerprint": DELIVERY_ENVELOPE_STATIC_FINGERPRINT,
            "transport_mode": "IN_MEMORY_JSON_DOCUMENT",
            "endpoint": None,
            "route": None,
        },
        "python_contract": {
            "builder": "build_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1",
            "verifier": "verify_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1",
            "implementation_path": "exchange_terminal/services/source_baseline_provider_conformance_in_memory_payload_delivery_adapter_v1.py",
            "implementation_sha256": PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
        },
        "javascript_contract": {
            "module_format": "UMD_COMMONJS",
            "browser_global": "HakimiSourceBaselineProviderConformanceInMemoryDeliveryAdapterV1",
            "receipt_schema_version": "source-baseline-provider-conformance-in-memory-payload-consumption-receipt-candidate-v1",
            "exports": [
                "verifyInMemoryPayloadDeliveryEnvelopeV1",
                "extractPayloadCandidateFromInMemoryEnvelopeV1",
                "buildInMemoryPayloadConsumptionReceiptCandidateV1",
                "verifyInMemoryPayloadConsumptionReceiptCandidateV1",
            ],
            "relative_load_order": [
                "strict_canonical_json_v1.js",
                "evidence_source_baseline_provider_conformance_card_v1.js",
                "evidence_source_baseline_provider_conformance_in_memory_delivery_adapter_v1.js",
            ],
            "implementation_path": "exchange_terminal/static/evidence_source_baseline_provider_conformance_in_memory_delivery_adapter_v1.js",
            "implementation_sha256": JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
        },
        "dependency_manifest": {
            "strict_canonical_javascript_sha256": STRICT_CANONICAL_JS_SHA256,
            "card_javascript_sha256": CARD_IMPLEMENTATION_SHA256,
            "python_adapter_test_sha256": PYTHON_ADAPTER_TEST_SHA256,
            "javascript_adapter_test_sha256": JAVASCRIPT_ADAPTER_TEST_SHA256,
            "adr0287_sha256": ADR0287_SHA256,
        },
        "host_plan": {
            "payload_source_provider": None,
            "payload_endpoint": None,
            "app_importer": None,
            "html_script_tag": None,
            "host_slot": None,
        },
        "facts": {
            "load_descriptor_pinned": True,
            "python_adapter_registered": True,
            "javascript_adapter_registered": True,
            "adapter_tests_pinned": True,
            "cross_runtime_schema_pinned": True,
            "payload_source_provider_present": False,
            "endpoint_present": False,
            "route_registered": False,
            "python_adapter_invoked_by_registration": False,
            "javascript_adapter_runtime_loaded": False,
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
            "payload_source_registration_allowed": False,
            "endpoint_registration_allowed": False,
            "route_registration_allowed": False,
            "host_asset_write_allowed": False,
            "adapter_execution_allowed": False,
            "card_render_allowed": False,
            "dom_access_allowed": False,
            "browser_execution_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "adapter_registration_hash")


def verify_source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1(
    document: Any,
) -> bool:
    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    return strict_json_contract_equal(
        snapshot,
        build_source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1(),
    )


def _build_registration_binding(
    *,
    status: str,
    binding_state: str,
    reason_code: str,
    adapter_registration_hash: str | None,
    delivery_envelope_hash: str | None,
    load_descriptor_binding_hash: str | None,
    payload_candidate_hash: str | None,
    registration_exact: bool,
    envelope_exact: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "binding_state": binding_state,
        "reason_code": reason_code,
        "adapter_registration_hash": adapter_registration_hash,
        "delivery_envelope_hash": delivery_envelope_hash,
        "load_descriptor_binding_hash": load_descriptor_binding_hash,
        "payload_candidate_hash": payload_candidate_hash,
        "python_adapter_implementation_sha256": PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
        "javascript_adapter_implementation_sha256": JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
        "facts": {
            "adapter_registration_exactly_verified": registration_exact,
            "delivery_envelope_exactly_verified": envelope_exact,
            "dual_runtime_asset_hashes_bound": registration_exact,
            "delivery_envelope_hash_bound": envelope_exact,
            "raw_delivery_envelope_embedded": False,
            "raw_payload_embedded": False,
            "raw_source_documents_embedded": False,
            "raw_identity_material_embedded": False,
            "payload_source_provider_present": False,
            "endpoint_present": False,
            "route_registered": False,
            "adapter_execution_observed": False,
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
            "payload_source_registration_allowed": False,
            "endpoint_registration_allowed": False,
            "route_registration_allowed": False,
            "host_asset_write_allowed": False,
            "adapter_execution_allowed": False,
            "card_render_allowed": False,
            "dom_access_allowed": False,
            "browser_execution_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "adapter_binding_hash")


def _unknown_binding(reason_code: str) -> dict[str, Any]:
    return _build_registration_binding(
        status="UNKNOWN",
        binding_state="UNKNOWN",
        reason_code=reason_code,
        adapter_registration_hash=None,
        delivery_envelope_hash=None,
        load_descriptor_binding_hash=None,
        payload_candidate_hash=None,
        registration_exact=False,
        envelope_exact=False,
    )


def build_source_baseline_provider_conformance_in_memory_delivery_adapter_binding_candidate_v1(
    adapter_registration_document: Any,
    delivery_envelope_document: Any,
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
    registration_snapshot = _snapshot_json_mapping(adapter_registration_document)
    if registration_snapshot is None:
        return _unknown_binding("ADAPTER_REGISTRATION_SNAPSHOT_FAILED")
    if not verify_source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1(
        registration_snapshot
    ):
        return _unknown_binding("ADAPTER_REGISTRATION_NOT_EXACT")

    envelope_snapshot = _snapshot_json_mapping(delivery_envelope_document)
    if envelope_snapshot is None:
        return _unknown_binding("DELIVERY_ENVELOPE_SNAPSHOT_FAILED")
    envelope_exact = verify_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1(
        envelope_snapshot,
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
    if not envelope_exact:
        return _unknown_binding("DELIVERY_ENVELOPE_NOT_EXACT")

    return _build_registration_binding(
        status="BLOCKED",
        binding_state="REGISTERED_ADAPTERS_AND_EXACT_ENVELOPE_HASH_BOUND_EXECUTION_UNAUTHORIZED",
        reason_code="DUAL_RUNTIME_ADAPTER_ASSETS_AND_EXACT_ENVELOPE_HASH_BOUND_PAYLOAD_SOURCE_ENDPOINT_HOST_LOAD_EXECUTION_BROWSER_AND_MOUNT_ABSENT",
        adapter_registration_hash=registration_snapshot[
            "adapter_registration_hash"
        ],
        delivery_envelope_hash=envelope_snapshot["delivery_envelope_hash"],
        load_descriptor_binding_hash=envelope_snapshot["provenance"][
            "load_descriptor_binding_hash"
        ],
        payload_candidate_hash=envelope_snapshot["provenance"][
            "payload_candidate_hash"
        ],
        registration_exact=True,
        envelope_exact=True,
    )


def verify_source_baseline_provider_conformance_in_memory_delivery_adapter_binding_candidate_v1(
    document: Any,
    adapter_registration_document: Any,
    delivery_envelope_document: Any,
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
    rebuilt = build_source_baseline_provider_conformance_in_memory_delivery_adapter_binding_candidate_v1(
        adapter_registration_document,
        delivery_envelope_document,
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
