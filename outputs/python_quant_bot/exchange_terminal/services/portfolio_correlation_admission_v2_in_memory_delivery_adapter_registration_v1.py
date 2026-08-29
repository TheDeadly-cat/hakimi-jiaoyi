from __future__ import annotations

import math
from typing import Any

from .portfolio_correlation_admission_v2_in_memory_delivery_v1 import (
    CONSUMER_PREREGISTRATION_HASH,
    PAYLOAD_SCHEMA_VERSION,
    SCHEMA_VERSION as DELIVERY_ENVELOPE_SCHEMA_VERSION,
    STATIC_FINGERPRINT as DELIVERY_STATIC_FINGERPRINT,
    verify_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-v2-in-memory-delivery-adapter-registration-v1"
)
BINDING_SCHEMA_VERSION = (
    "portfolio-correlation-admission-v2-in-memory-delivery-adapter-binding-v1"
)
STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-v2-delivery-adapter-registration-v1-lock-1"
)
STATUS = "BLOCKED"

PYTHON_ADAPTER_IMPLEMENTATION_SHA256 = (
    "0d725596a5019a1910f86ba2589ec305229d9bd79cb5bd78b71d17344f6af99b"
)
PYTHON_ADAPTER_TEST_SHA256 = (
    "48a2413177a13bba3a3c91584d80f2fbc029a2bd9f7a5a1c2c02106100d9fc1e"
)
JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256 = (
    "cedb6331ec8d922d60ef8a76e2aafcc0fd28d7c1a3ab850725fc4a0e7f02a083"
)
JAVASCRIPT_ADAPTER_TEST_SHA256 = (
    "9886a2da5103615fac7e98849772aa93bf3ada61d97388f01f3955d871d91a1d"
)
ADR0301_SHA256 = (
    "18d244a89fab8278458b680d3b0742ef34fc41da11478cbb78f05df15c32600d"
)
STRICT_CANONICAL_JS_SHA256 = (
    "6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39"
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


def build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1(
) -> dict[str, Any]:
    if DELIVERY_ENVELOPE_SCHEMA_VERSION != (
        "portfolio-correlation-admission-v2-in-memory-delivery-envelope-v1"
    ):
        raise RuntimeError("ADR0301 envelope schema drifted")
    if DELIVERY_STATIC_FINGERPRINT != (
        "20260823-portfolio-correlation-admission-v2-in-memory-delivery-v1-lock-1"
    ):
        raise RuntimeError("ADR0301 static fingerprint drifted")

    document = {
        "schema_version": SCHEMA_VERSION,
        "binding_schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "registration_state": "PYTHON_AND_JAVASCRIPT_DELIVERY_ADAPTERS_REGISTERED_UNBOUND",
        "decision": "DUAL_RUNTIME_ADAPTERS_TESTS_DEPENDENCIES_AND_EXACT_ENVELOPE_BINDING_PINNED_RAIL_SOURCE_HOST_EXECUTION_AND_MOUNT_ABSENT",
        "source_contract": {
            "consumer_preregistration_hash": CONSUMER_PREREGISTRATION_HASH,
            "delivery_envelope_schema_version": DELIVERY_ENVELOPE_SCHEMA_VERSION,
            "presentation_payload_schema_version": PAYLOAD_SCHEMA_VERSION,
            "delivery_static_fingerprint": DELIVERY_STATIC_FINGERPRINT,
            "transport_mode": "IN_MEMORY_JSON_DOCUMENT",
            "endpoint": None,
            "route": None,
        },
        "python_contract": {
            "builder": "build_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1",
            "verifier": "verify_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1",
            "implementation_path": "exchange_terminal/services/portfolio_correlation_admission_v2_in_memory_delivery_v1.py",
            "implementation_sha256": PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
            "test_path": "tests/test_portfolio_correlation_admission_v2_in_memory_delivery_v1.py",
            "test_sha256": PYTHON_ADAPTER_TEST_SHA256,
        },
        "javascript_contract": {
            "module_format": "UMD_COMMONJS",
            "browser_global": "HakimiPortfolioCorrelationAdmissionV2InMemoryDeliveryV1",
            "receipt_schema_version": "portfolio-correlation-admission-v2-payload-extraction-receipt-v1",
            "function_exports": [
                "verifyPortfolioCorrelationAdmissionV2PresentationPayloadV1",
                "verifyPortfolioCorrelationAdmissionV2InMemoryDeliveryEnvelopeV1",
                "extractPortfolioCorrelationAdmissionV2PresentationPayloadV1",
                "buildPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1",
                "verifyPortfolioCorrelationAdmissionV2PayloadExtractionReceiptV1",
            ],
            "relative_load_order": [
                "strict_canonical_json_v1.js",
                "evidence_portfolio_correlation_admission_v2_in_memory_delivery_v1.js",
            ],
            "implementation_path": "exchange_terminal/static/evidence_portfolio_correlation_admission_v2_in_memory_delivery_v1.js",
            "implementation_sha256": JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
            "test_path": "exchange_terminal/static/evidence_portfolio_correlation_admission_v2_in_memory_delivery_v1.test.js",
            "test_sha256": JAVASCRIPT_ADAPTER_TEST_SHA256,
        },
        "dependency_manifest": {
            "strict_canonical_javascript_sha256": STRICT_CANONICAL_JS_SHA256,
            "adr0301_sha256": ADR0301_SHA256,
        },
        "host_plan": {
            "payload_source_provider": None,
            "presentation_rail": None,
            "isolated_stylesheet": None,
            "app_importer": None,
            "html_script_tag": None,
            "host_slot": None,
            "endpoint": None,
            "route": None,
        },
        "facts": {
            "consumer_preregistration_pinned": True,
            "python_adapter_registered": True,
            "javascript_adapter_registered": True,
            "adapter_tests_pinned": True,
            "cross_runtime_schema_pinned": True,
            "strict_canonical_dependency_pinned": True,
            "registration_invoked_python_adapter": False,
            "registration_loaded_javascript_adapter": False,
            "payload_source_provider_present": False,
            "presentation_rail_registered": False,
            "stylesheet_registered": False,
            "endpoint_present": False,
            "route_registered": False,
            "adapter_execution_observed": False,
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
            "payload_source_registration_allowed": False,
            "presentation_registration_allowed": False,
            "stylesheet_registration_allowed": False,
            "endpoint_registration_allowed": False,
            "route_registration_allowed": False,
            "host_asset_write_allowed": False,
            "adapter_execution_allowed": False,
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
    return seal_strict_canonical_document(document, "adapter_registration_hash")


def verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
    except Exception:
        return False
    return type(snapshot) is dict and strict_json_contract_equal(
        snapshot,
        build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1(),
    )


def _build_binding(
    *,
    status: str,
    binding_state: str,
    reason_code: str,
    adapter_registration_hash: str | None,
    delivery_envelope_hash: str | None,
    presentation_payload_hash: str | None,
    candidate_hash: str | None,
    consumer_preregistration_hash: str | None,
    consumer_binding_hash: str | None,
    registration_exact: bool,
    envelope_exact: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "binding_state": binding_state,
        "reason_code": reason_code,
        "source": {
            "adapter_registration_hash": adapter_registration_hash,
            "delivery_envelope_hash": delivery_envelope_hash,
            "presentation_payload_hash": presentation_payload_hash,
            "candidate_hash": candidate_hash,
            "consumer_preregistration_hash": consumer_preregistration_hash,
            "consumer_binding_hash": consumer_binding_hash,
            "python_adapter_implementation_sha256": PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
            "javascript_adapter_implementation_sha256": JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
        },
        "facts": {
            "adapter_registration_exactly_verified": registration_exact,
            "delivery_envelope_exactly_verified": envelope_exact,
            "dual_runtime_asset_hashes_bound": registration_exact,
            "delivery_envelope_hash_bound": envelope_exact,
            "raw_delivery_envelope_embedded": False,
            "raw_presentation_payload_embedded": False,
            "raw_source_documents_embedded": False,
            "raw_symbol_lists_embedded": False,
            "payload_source_provider_present": False,
            "presentation_rail_registered": False,
            "stylesheet_registered": False,
            "endpoint_present": False,
            "route_registered": False,
            "adapter_execution_observed": False,
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
            "payload_source_registration_allowed": False,
            "presentation_registration_allowed": False,
            "stylesheet_registration_allowed": False,
            "endpoint_registration_allowed": False,
            "route_registration_allowed": False,
            "host_asset_write_allowed": False,
            "adapter_execution_allowed": False,
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
    return seal_strict_canonical_document(document, "adapter_binding_hash")


def _unknown_binding(reason_code: str) -> dict[str, Any]:
    return _build_binding(
        status="UNKNOWN",
        binding_state="UNKNOWN",
        reason_code=reason_code,
        adapter_registration_hash=None,
        delivery_envelope_hash=None,
        presentation_payload_hash=None,
        candidate_hash=None,
        consumer_preregistration_hash=None,
        consumer_binding_hash=None,
        registration_exact=False,
        envelope_exact=False,
    )


def build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_binding_v1(
    adapter_registration_document: Any,
    delivery_envelope_document: Any,
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
            "adapter_registration": adapter_registration_document,
            "delivery_envelope": delivery_envelope_document,
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
        return _unknown_binding("INPUT_SNAPSHOT_FAILED")

    registration = snapshot["adapter_registration"]
    if not verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1(
        registration
    ):
        return _unknown_binding("ADAPTER_REGISTRATION_NOT_EXACT")

    envelope = snapshot["delivery_envelope"]
    try:
        envelope_exact = verify_portfolio_correlation_admission_v2_in_memory_delivery_envelope_v1(
            envelope,
            snapshot["consumer_preregistration"],
            snapshot["consumer_binding"],
            snapshot["candidate"],
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
        return _unknown_binding("DELIVERY_ENVELOPE_VERIFICATION_EXCEPTION")
    if not envelope_exact:
        return _unknown_binding("DELIVERY_ENVELOPE_NOT_EXACT")

    provenance = envelope["provenance"]
    payload = envelope["presentation_payload"]
    return _build_binding(
        status="BLOCKED",
        binding_state="REGISTERED_DUAL_RUNTIME_ADAPTERS_AND_EXACT_ENVELOPE_HASH_BOUND_EXECUTION_UNAUTHORIZED",
        reason_code="DUAL_RUNTIME_ADAPTER_ASSETS_AND_EXACT_ENVELOPE_HASH_BOUND_RAIL_SOURCE_HOST_EXECUTION_BROWSER_AND_MOUNT_ABSENT",
        adapter_registration_hash=registration["adapter_registration_hash"],
        delivery_envelope_hash=envelope["delivery_envelope_hash"],
        presentation_payload_hash=payload["presentation_payload_hash"],
        candidate_hash=provenance["candidate_hash"],
        consumer_preregistration_hash=provenance[
            "consumer_preregistration_hash"
        ],
        consumer_binding_hash=provenance["consumer_binding_hash"],
        registration_exact=True,
        envelope_exact=True,
    )


def verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_binding_v1(
    document: Any,
    adapter_registration_document: Any,
    delivery_envelope_document: Any,
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
    rebuilt = build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_binding_v1(
        adapter_registration_document,
        delivery_envelope_document,
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
    "ADR0301_SHA256",
    "BINDING_SCHEMA_VERSION",
    "JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256",
    "JAVASCRIPT_ADAPTER_TEST_SHA256",
    "PYTHON_ADAPTER_IMPLEMENTATION_SHA256",
    "PYTHON_ADAPTER_TEST_SHA256",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_JS_SHA256",
    "build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_binding_v1",
    "build_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1",
    "verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_binding_v1",
    "verify_portfolio_correlation_admission_v2_in_memory_delivery_adapter_registration_v1",
]
