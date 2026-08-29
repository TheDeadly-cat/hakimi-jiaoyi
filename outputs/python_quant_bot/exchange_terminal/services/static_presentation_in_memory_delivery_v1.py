"""In-memory delivery envelope for the registered correlation admission rail."""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services.portfolio_correlation_admission_v1 import (
    verify_portfolio_correlation_admission_v1,
)
from exchange_terminal.services.static_presentation_asset_registration_v1 import (
    PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID,
    verify_portfolio_correlation_admission_rail_asset_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "static-presentation-in-memory-delivery-envelope-v1"
STATIC_FINGERPRINT = (
    "20260823-static-presentation-in-memory-delivery-v1-host-unbound-lock-1"
)
REGISTRATION_HASH = (
    "e5512d1d84ce9a2d3e3a23955b9d089c8c454d3cad93ac49f2c78bbf288459a1"
)
SOURCE_SCHEMA_VERSION = "portfolio-correlation-admission-v1"
CONSUMER_SCHEMA_VERSION = "portfolio-correlation-admission-rail-v1"
CONSUMER_STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-rail-v1-unmounted-lock-1"
)
JAVASCRIPT_GLOBAL = "HakimiPortfolioCorrelationAdmissionRailV1"

_AUTHORITY_KEYS = (
    "browser_execution_allowed",
    "current_admission_allowed",
    "dom_mount_allowed",
    "endpoint_registration_allowed",
    "live_order_allowed",
    "paper_authorized",
    "runtime_delivery_allowed",
    "writer_allowed",
)


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite delivery evidence is not permitted")
        return value
    if type(value) not in {dict, list}:
        raise TypeError("delivery evidence requires native JSON values")
    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic delivery evidence is not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("delivery evidence keys must be strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _consumer_contract() -> dict[str, Any]:
    return {
        "schema_version": CONSUMER_SCHEMA_VERSION,
        "static_fingerprint": CONSUMER_STATIC_FINGERPRINT,
        "browser_global": JAVASCRIPT_GLOBAL,
        "verify_function": "verifyPortfolioCorrelationAdmissionV1",
        "view_model_function": (
            "buildPortfolioCorrelationAdmissionRailViewModelV1"
        ),
        "render_function": "renderPortfolioCorrelationAdmissionRailV1",
    }


def _transport() -> dict[str, Any]:
    return {
        "mode": "IN_MEMORY_ARGUMENT_ONLY",
        "content_type": "application/json",
        "endpoint": None,
        "route": None,
        "host_slot": None,
    }


def _build_unknown(reason_code: str) -> dict[str, Any]:
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNKNOWN",
        "delivery_state": "UNKNOWN",
        "reason_code": reason_code,
        "registration_id": PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID,
        "registration_hash": None,
        "source_schema_version": SOURCE_SCHEMA_VERSION,
        "source_status": "UNKNOWN",
        "source_hash": None,
        "consumer_contract": _consumer_contract(),
        "transport": _transport(),
        "payload": None,
        "facts": {
            "registration_exactly_verified": False,
            "source_candidate_exactly_verified": False,
            "admission_candidate_embedded": False,
            "raw_source_report_embedded": False,
            "raw_correlation_evidence_embedded": False,
            "delivery_attempted": False,
            "javascript_adapter_executed": False,
            "view_model_derived": False,
            "markup_derived": False,
            "markup_embedded": False,
            "browser_executed": False,
            "dom_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "envelope_hash")


def _build_exact(
    registration: dict[str, Any],
    admission: dict[str, Any],
) -> dict[str, Any]:
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "delivery_state": (
            "EXACT_CANDIDATE_ENVELOPED_IN_MEMORY_HOST_UNBOUND"
        ),
        "reason_code": (
            "EXACT_REGISTRATION_AND_ADMISSION_CANDIDATE_ENVELOPED_"
            "IN_MEMORY_HOST_UNBOUND"
        ),
        "registration_id": PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID,
        "registration_hash": registration["registration_hash"],
        "source_schema_version": SOURCE_SCHEMA_VERSION,
        "source_status": admission["status"],
        "source_hash": admission["correlation_admission_hash"],
        "consumer_contract": _consumer_contract(),
        "transport": _transport(),
        "payload": admission,
        "facts": {
            "registration_exactly_verified": True,
            "source_candidate_exactly_verified": True,
            "admission_candidate_embedded": True,
            "raw_source_report_embedded": False,
            "raw_correlation_evidence_embedded": False,
            "delivery_attempted": False,
            "javascript_adapter_executed": False,
            "view_model_derived": False,
            "markup_derived": False,
            "markup_embedded": False,
            "browser_executed": False,
            "dom_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "envelope_hash")


def build_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1(
    registration_document: Any,
    admission_document: Any,
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
            "registration": registration_document,
            "admission": admission_document,
            "report": report_document,
            "correlation_preregistration": correlation_preregistration_document,
            "correlation_matrix": correlation_matrix_document,
            "selection_cells": selection_cells_document,
            "complete_link_gate": complete_link_gate_document,
            "strata_preregistration": strata_preregistration_document,
            "strata_gate": strata_gate_document,
        })
    except Exception:
        return _build_unknown("DELIVERY_INPUT_SNAPSHOT_FAILED")

    registration = snapshot["registration"]
    if not verify_portfolio_correlation_admission_rail_asset_registration_v1(
        registration
    ):
        return _build_unknown("ASSET_REGISTRATION_NOT_EXACT")
    if registration.get("registration_hash") != REGISTRATION_HASH:
        return _build_unknown("ASSET_REGISTRATION_HASH_DRIFT")

    admission = snapshot["admission"]
    verification = verify_portfolio_correlation_admission_v1(
        admission,
        snapshot["report"],
        snapshot["correlation_preregistration"],
        snapshot["correlation_matrix"],
        snapshot["selection_cells"],
        snapshot["complete_link_gate"],
        snapshot["strata_preregistration"],
        snapshot["strata_gate"],
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
    )
    if verification.get("status") != "PASS":
        return _build_unknown("ADMISSION_CANDIDATE_NOT_EXACT")
    if (
        type(admission) is not dict
        or admission.get("schema_version") != SOURCE_SCHEMA_VERSION
        or admission.get("status") not in {"PASS", "BLOCK"}
    ):
        return _build_unknown("ADMISSION_CANDIDATE_STATE_INVALID")
    return _build_exact(registration, admission)


def verify_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1(
    document: Any,
    registration_document: Any,
    admission_document: Any,
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
    expected = (
        build_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1(
            registration_document,
            admission_document,
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
    )
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "CONSUMER_SCHEMA_VERSION",
    "REGISTRATION_HASH",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1",
    "verify_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1",
]
