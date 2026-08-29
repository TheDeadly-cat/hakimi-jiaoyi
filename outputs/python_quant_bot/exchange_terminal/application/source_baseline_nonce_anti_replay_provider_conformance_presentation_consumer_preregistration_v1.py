"""Preregistered read-only consumer contract for the ADR0280 envelope."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1 import (
    ORDERED_STAGES,
    SCHEMA_VERSION as SOURCE_ENVELOPE_SCHEMA_VERSION,
    STATIC_FINGERPRINT as SOURCE_ENVELOPE_STATIC_FINGERPRINT,
    verify_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "source-baseline-provider-conformance-presentation-consumer-preregistration-v1"
)
PAYLOAD_SCHEMA_VERSION = (
    "source-baseline-provider-conformance-presentation-consumer-payload-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260823-source-baseline-presentation-consumer-preregistration-v1-lock-2"
)
STATUS = "BLOCKED"

SOURCE_ENVELOPE_IMPLEMENTATION_SHA256 = (
    "042457daf61f2d7872b7d566ed6cab58f7620260478a2d02cc3b3fba5996e8c4"
)
CONSUMER_REGISTRATION_V9_IMPLEMENTATION_SHA256 = (
    "e59e2d88f18d104ea08609b90d775e2d1e4c981040a6de326ed068755f865ab5"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
PROTECTED_STYLESHEET_SHA256 = (
    "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a"
)


def expected_source_envelope_top_level_fields_v1() -> list[str]:
    return [
        "schema_version",
        "static_fingerprint",
        "presentation_status",
        "display_tone",
        "display_state",
        "ordered_stage_contract",
        "axes",
        "summary",
        "lineage",
        "facts",
        "blockers",
        "authority",
        "presentation_envelope_hash",
    ]


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


def build_source_baseline_provider_conformance_presentation_consumer_preregistration_v1() -> dict[str, Any]:
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": "SOURCE_SCHEMA_PINNED_PAYLOAD_CANDIDATE_ALLOWED_CONSUMER_ASSETS_ROUTE_BROWSER_AND_MOUNT_ABSENT",
        "source_pin": {
            "schema_version": SOURCE_ENVELOPE_SCHEMA_VERSION,
            "static_fingerprint": SOURCE_ENVELOPE_STATIC_FINGERPRINT,
            "implementation_sha256": SOURCE_ENVELOPE_IMPLEMENTATION_SHA256,
            "document_hash_field": "presentation_envelope_hash",
        },
        "consumer_contract": {
            "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
            "allowed_source_top_level_fields": expected_source_envelope_top_level_fields_v1(),
            "ordered_stage_contract": list(ORDERED_STAGES),
            "axis_fields": ["stage", "state", "detail"],
            "summary_fields": [
                "source_document_count",
                "required_case_count",
                "executed_case_count",
                "passed_case_count",
                "open_gap_count",
            ],
            "payload_fields": [
                "display_tone",
                "display_state",
                "ordered_stage_contract",
                "axes",
                "summary",
                "blockers",
                "permission",
            ],
            "lineage_projection": "SOURCE_ENVELOPE_HASH_ONLY",
            "raw_source_documents_allowed": False,
            "raw_identity_material_allowed": False,
            "executable_assets_allowed": False,
        },
        "existing_consumer_boundary": {
            "registration_v9_implementation_sha256": CONSUMER_REGISTRATION_V9_IMPLEMENTATION_SHA256,
            "registration_v9_semantically_compatible": False,
            "reason": "PORTFOLIO_RISK_ASSET_AND_RECEIPT_CHAIN_DIFFERS_FROM_ADR0280",
        },
        "implementation_bindings": {
            "strict_canonical_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
            "protected_stylesheet_sha256": PROTECTED_STYLESHEET_SHA256,
        },
        "asset_manifest": {
            "consumer_javascript_sha256": None,
            "card_javascript_sha256": None,
            "stylesheet_sha256": None,
            "consumer_implementation_sha256": None,
        },
        "facts": {
            "source_schema_pinned": True,
            "source_implementation_pinned": True,
            "payload_contract_preregistered": True,
            "consumer_implementation_present": False,
            "asset_manifest_complete": False,
            "browser_execution_observed": False,
            "route_registered": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "asset_write_allowed": False,
            "browser_execution_allowed": False,
            "route_registration_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "consumer_preregistration_hash")


def verify_source_baseline_provider_conformance_presentation_consumer_preregistration_v1(
    document: Any,
) -> bool:
    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    return strict_json_contract_equal(
        snapshot,
        build_source_baseline_provider_conformance_presentation_consumer_preregistration_v1(),
    )


def _permission_payload() -> dict[str, bool | str]:
    return {
        "state": "BLOCKED",
        "provider_call_allowed": False,
        "writer_allowed": False,
        "route_registration_allowed": False,
        "ui_consumer_mount_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _build_payload_candidate(
    *,
    status: str,
    consumer_status: str,
    reason_code: str,
    source_envelope_hash: str | None,
    consumer_preregistration_hash: str | None,
    payload: dict[str, Any] | None,
    source_envelope_exactly_verified: bool,
    preregistration_exactly_verified: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "consumer_status": consumer_status,
        "reason_code": reason_code,
        "source_envelope_hash": source_envelope_hash,
        "consumer_preregistration_hash": consumer_preregistration_hash,
        "payload": payload,
        "facts": {
            "source_envelope_exactly_verified": source_envelope_exactly_verified,
            "preregistration_exactly_verified": preregistration_exactly_verified,
            "bounded_payload_built": payload is not None,
            "source_lineage_details_embedded": False,
            "raw_source_documents_embedded": False,
            "raw_identity_material_embedded": False,
            "consumer_implementation_present": False,
            "asset_manifest_complete": False,
            "browser_executed": False,
            "route_registered": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "asset_write_allowed": False,
            "browser_execution_allowed": False,
            "route_registration_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "payload_candidate_hash")


def _unknown_payload(reason_code: str, *, preregistration_exact: bool) -> dict[str, Any]:
    return _build_payload_candidate(
        status="UNKNOWN",
        consumer_status="UNKNOWN",
        reason_code=reason_code,
        source_envelope_hash=None,
        consumer_preregistration_hash=None,
        payload=None,
        source_envelope_exactly_verified=False,
        preregistration_exactly_verified=preregistration_exact,
    )


def build_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1(
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
    consumer_preregistration_snapshot = _snapshot_json_mapping(
        consumer_preregistration_document
    )
    if consumer_preregistration_snapshot is None:
        return _unknown_payload(
            "CONSUMER_PREREGISTRATION_SNAPSHOT_FAILED",
            preregistration_exact=False,
        )
    preregistration_exact = verify_source_baseline_provider_conformance_presentation_consumer_preregistration_v1(
        consumer_preregistration_snapshot
    )
    if not preregistration_exact:
        return _unknown_payload(
            "CONSUMER_PREREGISTRATION_NOT_EXACT", preregistration_exact=False
        )

    source_envelope_snapshot = _snapshot_json_mapping(source_envelope_document)
    conformance_plan_snapshot = _snapshot_json_mapping(conformance_plan_document)
    provider_identity_binding_snapshot = _snapshot_json_mapping(
        provider_identity_binding_document
    )
    namespace_preregistration_snapshot = _snapshot_json_mapping(
        namespace_preregistration_document
    )
    identity_preregistration_snapshot = _snapshot_json_mapping(
        identity_preregistration_document
    )
    organization_identity_intake_snapshot = _snapshot_json_mapping(
        organization_identity_intake_document
    )
    signer_source_trust_preregistration_snapshot = _snapshot_json_mapping(
        signer_source_trust_preregistration_document
    )
    source_chain_snapshots = (
        source_envelope_snapshot,
        conformance_plan_snapshot,
        provider_identity_binding_snapshot,
        namespace_preregistration_snapshot,
        identity_preregistration_snapshot,
        organization_identity_intake_snapshot,
        signer_source_trust_preregistration_snapshot,
    )
    if any(snapshot is None for snapshot in source_chain_snapshots):
        return _unknown_payload(
            "SOURCE_CHAIN_SNAPSHOT_FAILED", preregistration_exact=True
        )

    envelope_exact = verify_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1(
        source_envelope_snapshot,
        conformance_plan_snapshot,
        provider_identity_binding_snapshot,
        namespace_preregistration_snapshot,
        identity_preregistration_snapshot,
        organization_identity_intake_snapshot,
        signer_source_trust_preregistration_snapshot,
        registry_id=registry_id,
        operator_identity_claim=operator_identity_claim,
        public_key_spki_sha256=public_key_spki_sha256,
        trust_domain=trust_domain,
    )
    if not envelope_exact:
        return _unknown_payload(
            "SOURCE_ENVELOPE_NOT_EXACT", preregistration_exact=True
        )
    if source_envelope_snapshot.get("presentation_status") != "UNMOUNTED_CANDIDATE":
        return _unknown_payload(
            "SOURCE_PRESENTATION_STATUS_NOT_ALLOWED", preregistration_exact=True
        )

    payload = {
        "display_tone": source_envelope_snapshot["display_tone"],
        "display_state": source_envelope_snapshot["display_state"],
        "ordered_stage_contract": deepcopy(
            source_envelope_snapshot["ordered_stage_contract"]
        ),
        "axes": deepcopy(source_envelope_snapshot["axes"]),
        "summary": deepcopy(source_envelope_snapshot["summary"]),
        "blockers": deepcopy(source_envelope_snapshot["blockers"]),
        "permission": _permission_payload(),
    }
    return _build_payload_candidate(
        status="BLOCKED",
        consumer_status="PAYLOAD_BUILT_CONSUMER_UNREGISTERED",
        reason_code="BOUNDED_PAYLOAD_BUILT_ASSETS_ROUTE_BROWSER_AND_MOUNT_ABSENT",
        source_envelope_hash=source_envelope_snapshot["presentation_envelope_hash"],
        consumer_preregistration_hash=consumer_preregistration_snapshot[
            "consumer_preregistration_hash"
        ],
        payload=payload,
        source_envelope_exactly_verified=True,
        preregistration_exactly_verified=True,
    )


def verify_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1(
    document: Any,
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
    rebuilt = build_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1(
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
