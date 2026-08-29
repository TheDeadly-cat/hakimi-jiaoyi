"""Style-aware unmounted registration for the source-baseline card."""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.services.source_baseline_provider_conformance_presentation_consumer_registration_v1 import (
    BINDING_SCHEMA_VERSION as PREDECESSOR_BINDING_SCHEMA_VERSION,
    CARD_IMPLEMENTATION_SHA256,
    SCHEMA_VERSION as PREDECESSOR_REGISTRATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT as PREDECESSOR_STATIC_FINGERPRINT,
    STRICT_CANONICAL_JS_SHA256,
    build_source_baseline_provider_conformance_presentation_consumer_registration_v1,
    verify_source_baseline_provider_conformance_presentation_consumer_binding_candidate_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "source-baseline-provider-conformance-presentation-consumer-registration-v2"
)
BINDING_SCHEMA_VERSION = (
    "source-baseline-provider-conformance-presentation-consumer-binding-candidate-v2"
)
STATIC_FINGERPRINT = (
    "20260823-source-baseline-provider-conformance-consumer-registration-v2-lock-1"
)
STATUS = "BLOCKED"

PREDECESSOR_REGISTRATION_IMPLEMENTATION_SHA256 = (
    "948aaa77ea86658732226d2ed4d4c585a625ba409b946ef1f79fac58f0a883fe"
)
PREDECESSOR_REGISTRATION_HASH = (
    "217e4b759b993f3f513b989b79c380f7e192c799872e3f6959116171cc83d036"
)
STYLE_PREREGISTRATION_SCHEMA_VERSION = (
    "source-baseline-provider-conformance-style-preregistration-v1"
)
STYLE_PREREGISTRATION_STATIC_FINGERPRINT = (
    "20260823-source-baseline-provider-conformance-style-preregistration-v1-lock-1"
)
STYLE_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "ff06b47a7832a46a7092f5dba4b64401e56b0e6f7562420d2a505bf79bda6ff0"
)
STYLE_PREREGISTRATION_HASH = (
    "c8a882d9960d3c37f86d398304f827cf92bb741a229f33eed6abb96f4b8dccb5"
)
ISOLATED_STYLESHEET_SHA256 = (
    "fc41356f8fead588a3e2a4df24ba742cfd66646df38fd9ceec512a97db1da31f"
)
STYLE_CONTRACT_TEST_SHA256 = (
    "7216175fc3dbbc5efde9767df7ffc43ad3a9f991598ae4bc4101b89bf8704d8b"
)
ADR0284_SHA256 = (
    "5a928a0bf7c2e4f89c9a095c64e610d5f8a054b4546d10c147de5854c7e93254"
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


def build_source_baseline_provider_conformance_presentation_consumer_registration_v2() -> dict[str, Any]:
    predecessor = (
        build_source_baseline_provider_conformance_presentation_consumer_registration_v1()
    )
    if predecessor.get("consumer_registration_hash") != PREDECESSOR_REGISTRATION_HASH:
        raise RuntimeError("ADR0283 predecessor registration hash drifted")
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "registration_state": "CARD_AND_ISOLATED_STYLESHEET_REGISTERED_UNMOUNTED",
        "decision": "PAYLOAD_CARD_CANONICAL_STYLE_CONTRACT_AND_ISOLATED_STYLESHEET_PINNED_APP_HTML_ROUTE_BROWSER_AND_MOUNT_ABSENT",
        "predecessor_contract": {
            "schema_version": PREDECESSOR_REGISTRATION_SCHEMA_VERSION,
            "binding_schema_version": PREDECESSOR_BINDING_SCHEMA_VERSION,
            "static_fingerprint": PREDECESSOR_STATIC_FINGERPRINT,
            "consumer_registration_hash": PREDECESSOR_REGISTRATION_HASH,
            "implementation_sha256": PREDECESSOR_REGISTRATION_IMPLEMENTATION_SHA256,
        },
        "style_contract": {
            "schema_version": STYLE_PREREGISTRATION_SCHEMA_VERSION,
            "static_fingerprint": STYLE_PREREGISTRATION_STATIC_FINGERPRINT,
            "style_preregistration_hash": STYLE_PREREGISTRATION_HASH,
            "implementation_sha256": STYLE_PREREGISTRATION_IMPLEMENTATION_SHA256,
            "namespace": ".sb-conformance-card",
            "visual_direction": "COLD_AUDIT_FILM",
            "signature_element": "FOUR_STAGE_CALIBRATION_SPINE",
            "palette_color_count": 6,
            "typography_role_count": 3,
            "compact_breakpoint_max_width_px": 780,
            "narrow_breakpoint_max_width_px": 520,
            "motion_mounted_state_only": True,
            "reduced_motion_override_required": True,
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
            "style_preregistration_javascript": {
                "path": "exchange_terminal/static/evidence_source_baseline_provider_conformance_style_preregistration_v1.js",
                "sha256": STYLE_PREREGISTRATION_IMPLEMENTATION_SHA256,
            },
            "isolated_stylesheet": {
                "path": "exchange_terminal/static/evidence_source_baseline_provider_conformance_card_v1.css",
                "sha256": ISOLATED_STYLESHEET_SHA256,
            },
            "app_importer": None,
            "html_template": None,
        },
        "conformance_reference": {
            "test_path": "exchange_terminal/static/evidence_source_baseline_provider_conformance_style_preregistration_v1.test.js",
            "test_sha256": STYLE_CONTRACT_TEST_SHA256,
            "adr_path": "docs/adr/0284-source-baseline-provider-conformance-style-preregistration-v1.md",
            "adr_sha256": ADR0284_SHA256,
            "browser_evidence_embedded": False,
            "visual_review_embedded": False,
        },
        "protected_asset_guard": {
            "path": "exchange_terminal/static/styles.css",
            "observed_sha256": PROTECTED_STYLESHEET_SHA256,
            "imported": False,
            "modified": False,
            "reuse_authorized": False,
        },
        "facts": {
            "predecessor_registration_pinned": True,
            "style_contract_pinned": True,
            "isolated_stylesheet_registered": True,
            "asset_manifest_complete_for_unmounted_candidate": True,
            "stylesheet_runtime_loaded": False,
            "protected_stylesheet_modified": False,
            "app_imported": False,
            "html_bound": False,
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
            "stylesheet_runtime_binding_allowed": False,
            "protected_stylesheet_write_allowed": False,
            "app_import_allowed": False,
            "html_binding_allowed": False,
            "route_registration_allowed": False,
            "browser_execution_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "consumer_registration_hash")


def verify_source_baseline_provider_conformance_presentation_consumer_registration_v2(
    document: Any,
) -> bool:
    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    return strict_json_contract_equal(
        snapshot,
        build_source_baseline_provider_conformance_presentation_consumer_registration_v2(),
    )


def _build_style_binding(
    *,
    status: str,
    binding_state: str,
    reason_code: str,
    consumer_registration_v2_hash: str | None,
    predecessor_consumer_binding_hash: str | None,
    payload_candidate_hash: str | None,
    source_envelope_hash: str | None,
    registration_v2_exact: bool,
    predecessor_binding_exact: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "binding_state": binding_state,
        "reason_code": reason_code,
        "consumer_registration_v2_hash": consumer_registration_v2_hash,
        "predecessor_consumer_binding_hash": predecessor_consumer_binding_hash,
        "payload_candidate_hash": payload_candidate_hash,
        "source_envelope_hash": source_envelope_hash,
        "card_implementation_sha256": CARD_IMPLEMENTATION_SHA256,
        "style_preregistration_hash": STYLE_PREREGISTRATION_HASH,
        "isolated_stylesheet_sha256": ISOLATED_STYLESHEET_SHA256,
        "facts": {
            "registration_v2_exactly_verified": registration_v2_exact,
            "predecessor_binding_exactly_verified": predecessor_binding_exact,
            "payload_hash_bound": predecessor_binding_exact,
            "card_hash_bound": registration_v2_exact,
            "style_contract_hash_bound": registration_v2_exact,
            "isolated_stylesheet_hash_bound": registration_v2_exact,
            "raw_payload_embedded": False,
            "raw_style_document_embedded": False,
            "raw_source_documents_embedded": False,
            "raw_identity_material_embedded": False,
            "stylesheet_runtime_loaded": False,
            "app_imported": False,
            "html_bound": False,
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
            "stylesheet_runtime_binding_allowed": False,
            "app_import_allowed": False,
            "html_binding_allowed": False,
            "route_registration_allowed": False,
            "browser_execution_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "style_binding_hash")


def _unknown_style_binding(reason_code: str) -> dict[str, Any]:
    return _build_style_binding(
        status="UNKNOWN",
        binding_state="UNKNOWN",
        reason_code=reason_code,
        consumer_registration_v2_hash=None,
        predecessor_consumer_binding_hash=None,
        payload_candidate_hash=None,
        source_envelope_hash=None,
        registration_v2_exact=False,
        predecessor_binding_exact=False,
    )


def build_source_baseline_provider_conformance_presentation_consumer_style_binding_candidate_v2(
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
    registration_snapshot = _snapshot_json_mapping(consumer_registration_v2_document)
    if registration_snapshot is None:
        return _unknown_style_binding("CONSUMER_REGISTRATION_V2_SNAPSHOT_FAILED")
    if not verify_source_baseline_provider_conformance_presentation_consumer_registration_v2(
        registration_snapshot
    ):
        return _unknown_style_binding("CONSUMER_REGISTRATION_V2_NOT_EXACT")

    predecessor_binding_snapshot = _snapshot_json_mapping(
        predecessor_consumer_binding_document
    )
    if predecessor_binding_snapshot is None:
        return _unknown_style_binding("PREDECESSOR_BINDING_SNAPSHOT_FAILED")
    predecessor_exact = verify_source_baseline_provider_conformance_presentation_consumer_binding_candidate_v1(
        predecessor_binding_snapshot,
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
    if not predecessor_exact:
        return _unknown_style_binding("PREDECESSOR_BINDING_NOT_EXACT")

    return _build_style_binding(
        status="BLOCKED",
        binding_state="PAYLOAD_CARD_AND_ISOLATED_STYLESHEET_HASH_BOUND_UNMOUNTED",
        reason_code="EXACT_PREDECESSOR_BINDING_CARD_STYLE_CONTRACT_AND_ISOLATED_STYLESHEET_HASH_BOUND_APP_HTML_ROUTE_BROWSER_AND_MOUNT_ABSENT",
        consumer_registration_v2_hash=registration_snapshot[
            "consumer_registration_hash"
        ],
        predecessor_consumer_binding_hash=predecessor_binding_snapshot[
            "consumer_binding_hash"
        ],
        payload_candidate_hash=predecessor_binding_snapshot[
            "payload_candidate_hash"
        ],
        source_envelope_hash=predecessor_binding_snapshot["source_envelope_hash"],
        registration_v2_exact=True,
        predecessor_binding_exact=True,
    )


def verify_source_baseline_provider_conformance_presentation_consumer_style_binding_candidate_v2(
    document: Any,
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
    rebuilt = build_source_baseline_provider_conformance_presentation_consumer_style_binding_candidate_v2(
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
