"""Preregister an application load descriptor without mutating host assets."""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.services.source_baseline_provider_conformance_presentation_consumer_registration_v2 import (
    CARD_IMPLEMENTATION_SHA256,
    ISOLATED_STYLESHEET_SHA256,
    SCHEMA_VERSION as CONSUMER_REGISTRATION_V2_SCHEMA_VERSION,
    STATIC_FINGERPRINT as CONSUMER_REGISTRATION_V2_STATIC_FINGERPRINT,
    STRICT_CANONICAL_JS_SHA256,
    STYLE_PREREGISTRATION_IMPLEMENTATION_SHA256,
    build_source_baseline_provider_conformance_presentation_consumer_registration_v2,
    verify_source_baseline_provider_conformance_presentation_consumer_style_binding_candidate_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "source-baseline-provider-conformance-application-load-descriptor-preregistration-v1"
)
BINDING_SCHEMA_VERSION = (
    "source-baseline-provider-conformance-application-load-descriptor-binding-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260823-source-baseline-provider-conformance-load-descriptor-v1-lock-1"
)
STATUS = "BLOCKED"

CONSUMER_REGISTRATION_V2_IMPLEMENTATION_SHA256 = (
    "160e680e2ad94e281ee4bbe5c22e610c24837c6ec382b93a40408eb15d2d772a"
)
CONSUMER_REGISTRATION_V2_HASH = (
    "ab663f22c980f850b8440b8844909930d7a1a72f27245b26826c45c2000e7c64"
)
HOST_INDEX_HTML_SHA256 = (
    "553b33b0c4ef4ffb3e2f49d6671fe011f687696b95a7f5ff069f51f57bd5cd13"
)
HOST_APP_JS_SHA256 = (
    "9bf55162aff8d7a233804557c91605c801b92f515b2835978c05e2d1f3ef9210"
)
PROTECTED_STYLESHEET_SHA256 = (
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
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


def build_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1() -> dict[str, Any]:
    registration_v2 = (
        build_source_baseline_provider_conformance_presentation_consumer_registration_v2()
    )
    if (
        registration_v2.get("consumer_registration_hash")
        != CONSUMER_REGISTRATION_V2_HASH
    ):
        raise RuntimeError("ADR0285 registration-v2 hash drifted")
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "descriptor_state": "HOST_PINNED_LOAD_AND_MOUNT_CHANGES_NOT_APPLIED",
        "decision": "CURRENT_HOST_ASSETS_AND_FUTURE_RELATIVE_LOAD_ORDER_PINNED_SLOT_APP_BINDING_PAYLOAD_ADAPTER_BROWSER_AND_MOUNT_ABSENT",
        "source_contract": {
            "consumer_registration_v2_schema_version": CONSUMER_REGISTRATION_V2_SCHEMA_VERSION,
            "consumer_registration_v2_static_fingerprint": CONSUMER_REGISTRATION_V2_STATIC_FINGERPRINT,
            "consumer_registration_v2_hash": CONSUMER_REGISTRATION_V2_HASH,
            "consumer_registration_v2_implementation_sha256": CONSUMER_REGISTRATION_V2_IMPLEMENTATION_SHA256,
        },
        "host_contract": {
            "index_html": {
                "path": "exchange_terminal/static/index.html",
                "observed_sha256": HOST_INDEX_HTML_SHA256,
                "modified_by_descriptor": False,
            },
            "app_javascript": {
                "path": "exchange_terminal/static/app.js",
                "observed_sha256": HOST_APP_JS_SHA256,
                "modified_by_descriptor": False,
            },
            "protected_stylesheet": {
                "path": "exchange_terminal/static/styles.css",
                "observed_sha256": PROTECTED_STYLESHEET_SHA256,
                "modified_by_descriptor": False,
            },
            "interface_view": "research",
        },
        "relative_load_order": {
            "relative_subset_only": True,
            "existing_unlisted_assets_preserved": True,
            "stylesheets": [
                {
                    "path": "exchange_terminal/static/styles.css",
                    "sha256": PROTECTED_STYLESHEET_SHA256,
                    "state": "OBSERVED_UNCHANGED",
                    "relation": "EXISTING_BASE",
                },
                {
                    "path": "exchange_terminal/static/evidence_source_baseline_provider_conformance_card_v1.css",
                    "sha256": ISOLATED_STYLESHEET_SHA256,
                    "state": "PREREGISTERED_NOT_LOADED",
                    "relation": "AFTER_PROTECTED_STYLESHEET",
                },
            ],
            "scripts": [
                {
                    "path": "exchange_terminal/static/strict_canonical_json_v1.js",
                    "sha256": STRICT_CANONICAL_JS_SHA256,
                    "state": "PREREGISTERED_NOT_LOADED",
                    "relation": "BEFORE_CARD",
                },
                {
                    "path": "exchange_terminal/static/evidence_source_baseline_provider_conformance_card_v1.js",
                    "sha256": CARD_IMPLEMENTATION_SHA256,
                    "state": "PREREGISTERED_NOT_LOADED",
                    "relation": "AFTER_CANONICAL_BEFORE_APP",
                },
                {
                    "path": "exchange_terminal/static/app.js",
                    "sha256": HOST_APP_JS_SHA256,
                    "state": "OBSERVED_UNCHANGED",
                    "relation": "EXISTING_HOST_AFTER_CARD_CANDIDATE",
                },
            ],
            "style_preregistration_runtime_load_required": False,
            "style_preregistration_implementation_sha256": STYLE_PREREGISTRATION_IMPLEMENTATION_SHA256,
        },
        "mount_contract": {
            "host_anchor_id": "researchDataQualityCards",
            "host_anchor_observed": True,
            "future_slot_id": "sourceBaselineProviderConformanceCardHost",
            "future_slot_observed": False,
            "insertion_relation": "AFTER_HOST_ANCHOR",
            "card_browser_global": "HakimiSourceBaselineProviderConformanceCardV1",
            "render_function": "renderSourceBaselineProviderConformanceCardV1",
            "render_output_type": "ESCAPED_STATIC_HTML_STRING",
            "payload_delivery_adapter": None,
            "payload_endpoint": None,
            "new_route_required": False,
            "existing_research_view_reused": True,
        },
        "planned_mutations": [
            {
                "id": "HTML_STYLESHEET_TAG_INSERTION",
                "performed": False,
            },
            {
                "id": "HTML_SCRIPT_TAG_INSERTION",
                "performed": False,
            },
            {
                "id": "HTML_HOST_SLOT_INSERTION",
                "performed": False,
            },
            {
                "id": "APP_PAYLOAD_AND_RENDER_BINDING",
                "performed": False,
            },
        ],
        "blockers": [
            "HTML_ASSET_TAGS_ABSENT",
            "FUTURE_HOST_SLOT_ABSENT",
            "APP_PAYLOAD_AND_RENDER_BINDING_ABSENT",
            "PAYLOAD_DELIVERY_ADAPTER_NOT_PREREGISTERED",
            "PAYLOAD_ENDPOINT_ABSENT",
            "BROWSER_EXECUTION_NOT_AUTHORIZED",
            "VISUAL_REVIEW_NOT_PERFORMED",
        ],
        "facts": {
            "registration_v2_pinned": True,
            "host_index_pinned": True,
            "host_app_pinned": True,
            "relative_load_order_preregistered": True,
            "future_host_slot_preregistered": True,
            "html_assets_inserted": False,
            "host_slot_inserted": False,
            "app_binding_present": False,
            "payload_delivery_adapter_present": False,
            "payload_endpoint_present": False,
            "route_registered": False,
            "browser_executed": False,
            "visually_reviewed": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "host_asset_write_allowed": False,
            "stylesheet_runtime_binding_allowed": False,
            "script_runtime_loading_allowed": False,
            "app_binding_allowed": False,
            "payload_delivery_allowed": False,
            "route_registration_allowed": False,
            "browser_execution_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "load_descriptor_hash")


def verify_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1(
    document: Any,
) -> bool:
    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    return strict_json_contract_equal(
        snapshot,
        build_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1(),
    )


def _build_descriptor_binding(
    *,
    status: str,
    binding_state: str,
    reason_code: str,
    load_descriptor_hash: str | None,
    style_binding_hash: str | None,
    payload_candidate_hash: str | None,
    source_envelope_hash: str | None,
    descriptor_exact: bool,
    style_binding_exact: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "binding_state": binding_state,
        "reason_code": reason_code,
        "load_descriptor_hash": load_descriptor_hash,
        "style_binding_hash": style_binding_hash,
        "payload_candidate_hash": payload_candidate_hash,
        "source_envelope_hash": source_envelope_hash,
        "host_index_html_sha256": HOST_INDEX_HTML_SHA256,
        "host_app_javascript_sha256": HOST_APP_JS_SHA256,
        "facts": {
            "load_descriptor_exactly_verified": descriptor_exact,
            "style_binding_exactly_verified": style_binding_exact,
            "host_hashes_bound": descriptor_exact,
            "asset_order_hash_bound": descriptor_exact,
            "raw_payload_embedded": False,
            "raw_host_document_embedded": False,
            "raw_source_documents_embedded": False,
            "raw_identity_material_embedded": False,
            "html_assets_inserted": False,
            "host_slot_inserted": False,
            "app_binding_present": False,
            "payload_delivery_adapter_present": False,
            "payload_endpoint_present": False,
            "route_registered": False,
            "browser_executed": False,
            "visually_reviewed": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "host_asset_write_allowed": False,
            "script_runtime_loading_allowed": False,
            "app_binding_allowed": False,
            "payload_delivery_allowed": False,
            "route_registration_allowed": False,
            "browser_execution_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "load_descriptor_binding_hash")


def _unknown_descriptor_binding(reason_code: str) -> dict[str, Any]:
    return _build_descriptor_binding(
        status="UNKNOWN",
        binding_state="UNKNOWN",
        reason_code=reason_code,
        load_descriptor_hash=None,
        style_binding_hash=None,
        payload_candidate_hash=None,
        source_envelope_hash=None,
        descriptor_exact=False,
        style_binding_exact=False,
    )


def build_source_baseline_provider_conformance_application_load_descriptor_binding_candidate_v1(
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
    descriptor_snapshot = _snapshot_json_mapping(load_descriptor_document)
    if descriptor_snapshot is None:
        return _unknown_descriptor_binding("LOAD_DESCRIPTOR_SNAPSHOT_FAILED")
    if not verify_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1(
        descriptor_snapshot
    ):
        return _unknown_descriptor_binding("LOAD_DESCRIPTOR_NOT_EXACT")

    style_binding_snapshot = _snapshot_json_mapping(style_binding_document)
    if style_binding_snapshot is None:
        return _unknown_descriptor_binding("STYLE_BINDING_SNAPSHOT_FAILED")
    style_binding_exact = verify_source_baseline_provider_conformance_presentation_consumer_style_binding_candidate_v2(
        style_binding_snapshot,
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
    if not style_binding_exact:
        return _unknown_descriptor_binding("STYLE_BINDING_NOT_EXACT")

    return _build_descriptor_binding(
        status="BLOCKED",
        binding_state="LOAD_DESCRIPTOR_AND_STYLE_BINDING_HASH_BOUND_HOST_UNMODIFIED",
        reason_code="EXACT_LOAD_DESCRIPTOR_AND_STYLE_BINDING_HASH_BOUND_HTML_APP_PAYLOAD_ADAPTER_BROWSER_AND_MOUNT_ABSENT",
        load_descriptor_hash=descriptor_snapshot["load_descriptor_hash"],
        style_binding_hash=style_binding_snapshot["style_binding_hash"],
        payload_candidate_hash=style_binding_snapshot["payload_candidate_hash"],
        source_envelope_hash=style_binding_snapshot["source_envelope_hash"],
        descriptor_exact=True,
        style_binding_exact=True,
    )


def verify_source_baseline_provider_conformance_application_load_descriptor_binding_candidate_v1(
    document: Any,
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
    rebuilt = build_source_baseline_provider_conformance_application_load_descriptor_binding_candidate_v1(
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
