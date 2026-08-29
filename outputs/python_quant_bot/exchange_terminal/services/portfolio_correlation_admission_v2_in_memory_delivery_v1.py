from __future__ import annotations

import math
from typing import Any

from .portfolio_correlation_admission_v2_consumer_preregistration_v1 import (
    build_portfolio_correlation_admission_v2_consumer_preregistration_v1,
    verify_portfolio_correlation_admission_v2_consumer_binding_v1,
    verify_portfolio_correlation_admission_v2_consumer_preregistration_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "portfolio-correlation-admission-v2-in-memory-delivery-envelope-v1"
PAYLOAD_SCHEMA_VERSION = "portfolio-correlation-admission-v2-presentation-payload-v1"
STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-v2-in-memory-delivery-v1-lock-1"
)
STATUS = "BLOCKED"

CONSUMER_PREREGISTRATION_HASH = (
    "6e750c92f129edea5c18445a563ea34a027df4f47281d0b9f3e1209ac35f2b90"
)
CONSUMER_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "4320d27377f5982331ca5b39113d2fee9f252edb3d968dee04797adf17690cfa"
)
CONSUMER_PREREGISTRATION_TEST_SHA256 = (
    "634516fb23cdd369abc9da6fa7c856e9020a569dbdcbc7842d6827c2fde7aa09"
)
ADR0300_SHA256 = (
    "648d02670b3687af7043e57135cbd4d0aad8c345df337ee7f7f1a410205d3cff"
)


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite numbers are not permitted")
        return value
    if type(value) not in {dict, list}:
        raise TypeError("input must contain native JSON values")

    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic input is not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("object keys must be native strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _build_presentation_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    document = {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": candidate["status"],
        "first_blocking_tier": candidate["first_blocking_tier"],
        "common_universe_status": candidate["common_universe_status"],
        "v1_admission_status": candidate["v1_admission_status"],
        "v1_first_blocking_tier": candidate["v1_first_blocking_tier"],
        "candidate_hash": candidate["correlation_admission_v2_hash"],
        "common_universe_binding_hash": candidate["evidence_hashes"][
            "common_universe_binding_hash"
        ],
        "source_report_hash": candidate["evidence_hashes"]["source_report_hash"],
        "checks": dict(candidate["checks"]),
        "blockers": list(candidate["blockers"]),
        "facts": {
            "consumer_only": True,
            "raw_v2_candidate_embedded": False,
            "raw_source_documents_embedded": False,
            "raw_symbol_lists_embedded": False,
            "profitability_proven": False,
        },
        "permissions": {
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "presentation_payload_hash")


def _build_delivery_envelope(
    *,
    status: str,
    delivery_state: str,
    reason_code: str,
    consumer_preregistration_hash: str | None,
    consumer_binding_hash: str | None,
    candidate_hash: str | None,
    candidate_status: str | None,
    common_universe_binding_hash: str | None,
    source_report_hash: str | None,
    presentation_payload: dict[str, Any] | None,
    preregistration_exact: bool,
    binding_exact: bool,
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
            "javascript_adapter_global": "HakimiPortfolioCorrelationAdmissionV2InMemoryDeliveryV1",
            "javascript_verify_function": "verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1",
            "javascript_extract_function": "extractPortfolioCorrelationAdmissionV2PresentationPayloadV1",
            "javascript_receipt_function": "buildPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1",
            "presentation_consumer": None,
            "render_function": None,
        },
        "provenance": {
            "consumer_preregistration_hash": consumer_preregistration_hash,
            "consumer_preregistration_implementation_sha256": CONSUMER_PREREGISTRATION_IMPLEMENTATION_SHA256,
            "consumer_preregistration_test_sha256": CONSUMER_PREREGISTRATION_TEST_SHA256,
            "consumer_preregistration_adr_sha256": ADR0300_SHA256,
            "consumer_binding_hash": consumer_binding_hash,
            "candidate_hash": candidate_hash,
            "candidate_status": candidate_status,
            "common_universe_binding_hash": common_universe_binding_hash,
            "source_report_hash": source_report_hash,
        },
        "presentation_payload": presentation_payload,
        "facts": {
            "consumer_preregistration_exactly_verified": preregistration_exact,
            "consumer_binding_exactly_verified": binding_exact,
            "bounded_presentation_payload_embedded": presentation_payload is not None,
            "raw_v2_candidate_embedded": False,
            "raw_source_documents_embedded": False,
            "raw_symbol_lists_embedded": False,
            "wire_bytes_built": False,
            "delivery_attempted": False,
            "network_accessed": False,
            "endpoint_present": False,
            "route_registered": False,
            "persistent_storage_used": False,
            "payload_extracted": False,
            "presentation_consumer_executed": False,
            "render_called": False,
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
            "payload_extraction_runtime_allowed": False,
            "presentation_consumer_execution_allowed": False,
            "render_allowed": False,
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
        consumer_preregistration_hash=None,
        consumer_binding_hash=None,
        candidate_hash=None,
        candidate_status=None,
        common_universe_binding_hash=None,
        source_report_hash=None,
        presentation_payload=None,
        preregistration_exact=False,
        binding_exact=False,
    )


def build_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1(
    consumer_preregistration_document: Any,
    consumer_binding_document: Any,
    candidate_document: Any,
    report_document: Any,
    correlation_preregistration_document: Any,
    correlation_matrix_document: Any,
    selection_cells_document: Any,
    complete_link_gate_document: Any,
    strata_preregistration_document: Any,
    strata_gate_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    try:
        snapshot = _plain_json_snapshot({
            "consumer_preregistration": consumer_preregistration_document,
            "consumer_binding": consumer_binding_document,
            "candidate": candidate_document,
            "report": report_document,
            "correlation_preregistration": correlation_preregistration_document,
            "correlation_matrix": correlation_matrix_document,
            "selection_cells": selection_cells_document,
            "complete_link_gate": complete_link_gate_document,
            "strata_preregistration": strata_preregistration_document,
            "strata_gate": strata_gate_document,
            "strategy_id": strategy_id,
            "variant_id": variant_id,
            "lane": lane,
        })
    except Exception:
        return _unknown_delivery("INPUT_SNAPSHOT_FAILED")

    registration = snapshot["consumer_preregistration"]
    if not verify_portfolio_correlation_admission_v2_consumer_preregistration_v1(
        registration
    ):
        return _unknown_delivery("CONSUMER_PREREGISTRATION_NOT_EXACT")
    if registration.get("consumer_preregistration_hash") != CONSUMER_PREREGISTRATION_HASH:
        return _unknown_delivery("CONSUMER_PREREGISTRATION_HASH_DRIFT")

    binding = snapshot["consumer_binding"]
    candidate = snapshot["candidate"]
    try:
        binding_exact = verify_portfolio_correlation_admission_v2_consumer_binding_v1(
            binding,
            registration,
            candidate,
            snapshot["report"],
            snapshot["correlation_preregistration"],
            snapshot["correlation_matrix"],
            snapshot["selection_cells"],
            snapshot["complete_link_gate"],
            snapshot["strata_preregistration"],
            snapshot["strata_gate"],
            strategy_id=snapshot["strategy_id"],
            variant_id=snapshot["variant_id"],
            lane=snapshot["lane"],
        )
    except Exception:
        return _unknown_delivery("CONSUMER_BINDING_VERIFICATION_EXCEPTION")
    if not binding_exact:
        return _unknown_delivery("CONSUMER_BINDING_NOT_EXACT")
    if (
        type(candidate) is not dict
        or type(binding) is not dict
        or binding.get("source", {}).get("candidate_hash")
        != candidate.get("correlation_admission_v2_hash")
    ):
        return _unknown_delivery("CANDIDATE_HASH_DOES_NOT_MATCH_BINDING")

    payload = _build_presentation_payload(candidate)
    return _build_delivery_envelope(
        status="BLOCKED",
        delivery_state="EXACT_V2_PRESENTATION_PAYLOAD_ENVELOPED_IN_MEMORY_CONSUMER_UNBOUND",
        reason_code="EXACT_BOUNDED_V2_PRESENTATION_PAYLOAD_EMBEDDED_IN_MEMORY_WIRE_ENDPOINT_ROUTE_PRESENTATION_RENDER_BROWSER_AND_MOUNT_ABSENT",
        consumer_preregistration_hash=registration[
            "consumer_preregistration_hash"
        ],
        consumer_binding_hash=binding["consumer_binding_hash"],
        candidate_hash=candidate["correlation_admission_v2_hash"],
        candidate_status=candidate["status"],
        common_universe_binding_hash=candidate["evidence_hashes"][
            "common_universe_binding_hash"
        ],
        source_report_hash=candidate["evidence_hashes"]["source_report_hash"],
        presentation_payload=payload,
        preregistration_exact=True,
        binding_exact=True,
    )


def verify_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1(
    document: Any,
    consumer_preregistration_document: Any,
    consumer_binding_document: Any,
    candidate_document: Any,
    report_document: Any,
    correlation_preregistration_document: Any,
    correlation_matrix_document: Any,
    selection_cells_document: Any,
    complete_link_gate_document: Any,
    strata_preregistration_document: Any,
    strata_gate_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
    except Exception:
        return False
    if type(snapshot) is not dict:
        return False
    rebuilt = build_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1(
        consumer_preregistration_document,
        consumer_binding_document,
        candidate_document,
        report_document,
        correlation_preregistration_document,
        correlation_matrix_document,
        selection_cells_document,
        complete_link_gate_document,
        strata_preregistration_document,
        strata_gate_document,
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
    )
    return strict_json_contract_equal(snapshot, rebuilt)


__all__ = [
    "ADR0300_SHA256",
    "CONSUMER_PREREGISTRATION_HASH",
    "CONSUMER_PREREGISTRATION_IMPLEMENTATION_SHA256",
    "CONSUMER_PREREGISTRATION_TEST_SHA256",
    "PAYLOAD_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1",
    "verify_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1",
]
