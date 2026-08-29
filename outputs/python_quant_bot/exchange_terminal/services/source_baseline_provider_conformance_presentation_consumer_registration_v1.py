"""Versioned unmounted registration for the ADR0282 neutral card candidate."""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_presentation_consumer_preregistration_v1 import (
    PAYLOAD_SCHEMA_VERSION,
    STATIC_FINGERPRINT as PAYLOAD_STATIC_FINGERPRINT,
    build_source_baseline_provider_conformance_presentation_consumer_preregistration_v1,
    verify_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "source-baseline-provider-conformance-presentation-consumer-registration-v1"
)
BINDING_SCHEMA_VERSION = (
    "source-baseline-provider-conformance-presentation-consumer-binding-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260823-source-baseline-provider-conformance-consumer-registration-v1-lock-1"
)
STATUS = "BLOCKED"

CONSUMER_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "7ff64216e70dcedd43b86210cfac68b632c1eb7bc10a390bec9d4ffb619ac572"
)
CONSUMER_PREREGISTRATION_HASH = (
    "42b4c9830844c455b05c4952a7010655534048f73cf78f9f7ab574bebbddca5d"
)
CARD_SCHEMA_VERSION = "source-baseline-provider-conformance-neutral-card-v1"
CARD_STATIC_FINGERPRINT = (
    "20260823-source-baseline-provider-conformance-neutral-card-v1-unmounted-lock-1"
)
CARD_IMPLEMENTATION_SHA256 = (
    "88a1ac27eaefd554e82129a5b2883d14af365965559d1d0e84db8dc32b1d9a5a"
)
CARD_TEST_SHA256 = (
    "e64ec0abd375c6fdda4dde9032b2a79b9535173b25a255cdd20c27e31b1d65a6"
)
ADR0282_SHA256 = (
    "7b5b280d09c616086caad4ece31a62a6e56a412001e2e710cb0d11db61664aa0"
)
STRICT_CANONICAL_JS_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
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


def build_source_baseline_provider_conformance_presentation_consumer_registration_v1() -> dict[str, Any]:
    preregistration = (
        build_source_baseline_provider_conformance_presentation_consumer_preregistration_v1()
    )
    if (
        preregistration.get("consumer_preregistration_hash")
        != CONSUMER_PREREGISTRATION_HASH
    ):
        raise RuntimeError("ADR0281 preregistration hash drifted")
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "registration_state": "ASSET_MANIFEST_REGISTERED_UNMOUNTED",
        "decision": "PAYLOAD_CARD_AND_CANONICAL_ASSETS_PINNED_STYLESHEET_APP_ROUTE_BROWSER_AND_MOUNT_ABSENT",
        "source_contract": {
            "consumer_preregistration_schema_version": preregistration[
                "schema_version"
            ],
            "consumer_preregistration_static_fingerprint": preregistration[
                "static_fingerprint"
            ],
            "consumer_preregistration_hash": CONSUMER_PREREGISTRATION_HASH,
            "consumer_preregistration_implementation_sha256": CONSUMER_PREREGISTRATION_IMPLEMENTATION_SHA256,
            "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
            "payload_static_fingerprint": PAYLOAD_STATIC_FINGERPRINT,
        },
        "consumer_contract": {
            "card_schema_version": CARD_SCHEMA_VERSION,
            "card_static_fingerprint": CARD_STATIC_FINGERPRINT,
            "module_format": "UMD_COMMONJS",
            "browser_global": "HakimiSourceBaselineProviderConformanceCardV1",
            "load_order": [
                "strict_canonical_json_v1.js",
                "evidence_source_baseline_provider_conformance_card_v1.js",
            ],
            "exported_functions": [
                "verifySourceBaselineProviderConformancePayloadCandidateV1",
                "buildSourceBaselineProviderConformanceViewModelV1",
                "renderSourceBaselineProviderConformanceCardV1",
            ],
            "ordered_stage_contract": [
                "SOURCE",
                "GAP",
                "MATURITY",
                "PERMISSION",
            ],
            "display_tone": "NEUTRAL",
            "accepted_status": "BLOCKED",
        },
        "asset_manifest": {
            "strict_canonical_javascript": {
                "path": "exchange_terminal/static/strict_canonical_json_v1.js",
                "sha256": STRICT_CANONICAL_JS_SHA256,
            },
            "card_javascript": {
                "path": "exchange_terminal/static/evidence_source_baseline_provider_conformance_card_v1.js",
                "sha256": CARD_IMPLEMENTATION_SHA256,
            },
            "stylesheet": None,
            "app_importer": None,
            "html_template": None,
        },
        "conformance_reference": {
            "test_path": "exchange_terminal/static/evidence_source_baseline_provider_conformance_card_v1.test.js",
            "test_sha256": CARD_TEST_SHA256,
            "adr_path": "docs/adr/0282-source-baseline-provider-conformance-neutral-card-v1.md",
            "adr_sha256": ADR0282_SHA256,
            "test_result_embedded": False,
        },
        "protected_asset_guard": {
            "path": "exchange_terminal/static/styles.css",
            "observed_sha256": PROTECTED_STYLESHEET_SHA256,
            "bound_to_consumer": False,
            "reuse_authorized": False,
            "modification_authorized": False,
        },
        "facts": {
            "consumer_preregistration_pinned": True,
            "consumer_registration_present": True,
            "card_implementation_present": True,
            "canonical_dependency_present": True,
            "candidate_test_asset_pinned": True,
            "test_result_embedded": False,
            "asset_manifest_complete_for_unmounted_candidate": True,
            "stylesheet_bound": False,
            "app_imported": False,
            "route_registered": False,
            "browser_executed": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "asset_write_allowed": False,
            "consumer_execution_allowed": False,
            "browser_execution_allowed": False,
            "stylesheet_binding_allowed": False,
            "app_import_allowed": False,
            "route_registration_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "consumer_registration_hash")


def verify_source_baseline_provider_conformance_presentation_consumer_registration_v1(
    document: Any,
) -> bool:
    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    return strict_json_contract_equal(
        snapshot,
        build_source_baseline_provider_conformance_presentation_consumer_registration_v1(),
    )


def _build_binding_candidate(
    *,
    status: str,
    binding_state: str,
    reason_code: str,
    consumer_registration_hash: str | None,
    payload_candidate_hash: str | None,
    source_envelope_hash: str | None,
    registration_exact: bool,
    payload_exact: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "binding_state": binding_state,
        "reason_code": reason_code,
        "consumer_registration_hash": consumer_registration_hash,
        "payload_candidate_hash": payload_candidate_hash,
        "source_envelope_hash": source_envelope_hash,
        "card_implementation_sha256": CARD_IMPLEMENTATION_SHA256,
        "facts": {
            "registration_exactly_verified": registration_exact,
            "payload_exactly_verified": payload_exact,
            "payload_hash_bound": payload_exact,
            "card_hash_bound": registration_exact,
            "raw_payload_embedded": False,
            "raw_source_documents_embedded": False,
            "raw_identity_material_embedded": False,
            "stylesheet_bound": False,
            "consumer_executed": False,
            "browser_executed": False,
            "route_registered": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "consumer_execution_allowed": False,
            "browser_execution_allowed": False,
            "stylesheet_binding_allowed": False,
            "route_registration_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "consumer_binding_hash")


def _unknown_binding(reason_code: str) -> dict[str, Any]:
    return _build_binding_candidate(
        status="UNKNOWN",
        binding_state="UNKNOWN",
        reason_code=reason_code,
        consumer_registration_hash=None,
        payload_candidate_hash=None,
        source_envelope_hash=None,
        registration_exact=False,
        payload_exact=False,
    )


def build_source_baseline_provider_conformance_presentation_consumer_binding_candidate_v1(
    consumer_registration_document: Any,
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
    registration_snapshot = _snapshot_json_mapping(consumer_registration_document)
    if registration_snapshot is None:
        return _unknown_binding("CONSUMER_REGISTRATION_SNAPSHOT_FAILED")
    if not verify_source_baseline_provider_conformance_presentation_consumer_registration_v1(
        registration_snapshot
    ):
        return _unknown_binding("CONSUMER_REGISTRATION_NOT_EXACT")

    payload_snapshot = _snapshot_json_mapping(payload_candidate_document)
    if payload_snapshot is None:
        return _unknown_binding("PAYLOAD_CANDIDATE_SNAPSHOT_FAILED")
    payload_exact = verify_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1(
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
    if not payload_exact:
        return _unknown_binding("PAYLOAD_CANDIDATE_NOT_EXACT")

    return _build_binding_candidate(
        status="BLOCKED",
        binding_state="PAYLOAD_AND_CARD_HASH_BOUND_UNMOUNTED",
        reason_code="EXACT_PAYLOAD_AND_REGISTERED_CARD_BOUND_STYLESHEET_APP_ROUTE_BROWSER_AND_MOUNT_ABSENT",
        consumer_registration_hash=registration_snapshot[
            "consumer_registration_hash"
        ],
        payload_candidate_hash=payload_snapshot["payload_candidate_hash"],
        source_envelope_hash=payload_snapshot["source_envelope_hash"],
        registration_exact=True,
        payload_exact=True,
    )


def verify_source_baseline_provider_conformance_presentation_consumer_binding_candidate_v1(
    document: Any,
    consumer_registration_document: Any,
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
    rebuilt = build_source_baseline_provider_conformance_presentation_consumer_binding_candidate_v1(
        consumer_registration_document,
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
