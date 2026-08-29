from __future__ import annotations

import math
from typing import Any

from .portfolio_correlation_admission_v2 import (
    SCHEMA_VERSION as PRODUCER_SCHEMA_VERSION,
    STATIC_FINGERPRINT as PRODUCER_STATIC_FINGERPRINT,
    verify_portfolio_correlation_admission_v2,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "portfolio-correlation-admission-v2-consumer-preregistration-v1"
BINDING_SCHEMA_VERSION = "portfolio-correlation-admission-v2-consumer-binding-v1"
STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-v2-consumer-preregistration-v1-lock-1"
)
STATUS = "BLOCKED"

V1_SCHEMA_VERSION = "portfolio-correlation-admission-v1"
V1_IMPLEMENTATION_SHA256 = (
    "d279356f1d2d55e3a8ccd02524faa4245afc357ffe91b5820ae1cc772fa75002"
)
V2_IMPLEMENTATION_SHA256 = (
    "a691435ceb366ba723ab1235467e4333da8bb622f10d826460ca104423b7a67f"
)
V2_CONTRACT_TEST_SHA256 = (
    "320613fd3903a57fe349dcbafb5400b7101afd4c9f53b6689bcdcd79c472ecea"
)
ADR0299_SHA256 = (
    "374fb0dcd25c57196b97e282b70e96a4b38c602ecac4ba2b507970e287b67521"
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


def build_portfolio_correlation_admission_v2_consumer_preregistration_v1(
) -> dict[str, Any]:
    if PRODUCER_SCHEMA_VERSION != "portfolio-correlation-admission-v2":
        raise RuntimeError("ADR0299 producer schema drifted")
    if PRODUCER_STATIC_FINGERPRINT != (
        "20260823-portfolio-correlation-common-universe-v2-unbound-lock-1"
    ):
        raise RuntimeError("ADR0299 producer fingerprint drifted")

    document = {
        "schema_version": SCHEMA_VERSION,
        "binding_schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "registration_state": "V2_CONSUMER_PREREGISTERED_UNBOUND",
        "decision": "EXACT_V2_PRODUCER_AND_VERIFIER_PINNED_HASH_ONLY_BINDING_AVAILABLE_DELIVERY_PRESENTATION_HOST_AND_CURRENT_ABSENT",
        "producer_contract": {
            "schema_version": PRODUCER_SCHEMA_VERSION,
            "static_fingerprint": PRODUCER_STATIC_FINGERPRINT,
            "implementation_sha256": V2_IMPLEMENTATION_SHA256,
            "test_sha256": V2_CONTRACT_TEST_SHA256,
            "adr_sha256": ADR0299_SHA256,
            "candidate_hash_field": "correlation_admission_v2_hash",
            "exact_verifier": "verify_portfolio_correlation_admission_v2",
            "accepted_candidate_statuses": ["PASS", "BLOCK"],
        },
        "predecessor_contract": {
            "schema_version": V1_SCHEMA_VERSION,
            "implementation_sha256": V1_IMPLEMENTATION_SHA256,
            "compatibility_unchanged": True,
        },
        "consumer_contract": {
            "binding_mode": "EXPLICIT_PURE_IN_MEMORY_EXACT_REBUILD",
            "raw_candidate_embedded": False,
            "raw_source_documents_embedded": False,
            "raw_symbol_lists_embedded": False,
            "delivery_adapter": None,
            "presentation_consumer": None,
            "application_importer": None,
            "html_mount": None,
            "route": None,
        },
        "facts": {
            "producer_schema_pinned": True,
            "producer_implementation_pinned": True,
            "producer_test_pinned": True,
            "producer_adr_pinned": True,
            "predecessor_implementation_pinned": True,
            "exact_candidate_binding_builder_present": True,
            "delivery_adapter_registered": False,
            "presentation_consumer_registered": False,
            "app_imported": False,
            "html_bound": False,
            "route_registered": False,
            "browser_executed": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "delivery_registration_allowed": False,
            "presentation_registration_allowed": False,
            "app_import_allowed": False,
            "html_binding_allowed": False,
            "route_registration_allowed": False,
            "browser_execution_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "consumer_preregistration_hash")


def verify_portfolio_correlation_admission_v2_consumer_preregistration_v1(
    document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
    except Exception:
        return False
    return type(snapshot) is dict and strict_json_contract_equal(
        snapshot,
        build_portfolio_correlation_admission_v2_consumer_preregistration_v1(),
    )


def _build_binding(
    *,
    status: str,
    binding_state: str,
    reason_code: str,
    consumer_preregistration_hash: str | None,
    candidate_hash: str | None,
    candidate_status: str | None,
    common_universe_status: str | None,
    common_universe_binding_hash: str | None,
    v1_candidate_hash: str | None,
    source_report_hash: str | None,
    preregistration_exact: bool,
    candidate_exact: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "binding_state": binding_state,
        "reason_code": reason_code,
        "source": {
            "consumer_preregistration_hash": consumer_preregistration_hash,
            "candidate_hash": candidate_hash,
            "candidate_status": candidate_status,
            "common_universe_status": common_universe_status,
            "common_universe_binding_hash": common_universe_binding_hash,
            "v1_candidate_hash": v1_candidate_hash,
            "source_report_hash": source_report_hash,
        },
        "facts": {
            "consumer_preregistration_exactly_verified": preregistration_exact,
            "v2_candidate_exactly_verified": candidate_exact,
            "v2_candidate_research_pass": (
                candidate_exact and candidate_status == "PASS"
            ),
            "v2_block_candidate_bound": (
                candidate_exact and candidate_status == "BLOCK"
            ),
            "raw_candidate_embedded": False,
            "raw_source_documents_embedded": False,
            "raw_symbol_lists_embedded": False,
            "delivery_adapter_registered": False,
            "presentation_consumer_registered": False,
            "consumer_executed": False,
            "app_imported": False,
            "html_bound": False,
            "route_registered": False,
            "browser_executed": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "delivery_registration_allowed": False,
            "presentation_registration_allowed": False,
            "consumer_execution_allowed": False,
            "app_import_allowed": False,
            "html_binding_allowed": False,
            "route_registration_allowed": False,
            "browser_execution_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "consumer_binding_hash")


def _unknown_binding(reason_code: str) -> dict[str, Any]:
    return _build_binding(
        status="UNKNOWN",
        binding_state="UNKNOWN",
        reason_code=reason_code,
        consumer_preregistration_hash=None,
        candidate_hash=None,
        candidate_status=None,
        common_universe_status=None,
        common_universe_binding_hash=None,
        v1_candidate_hash=None,
        source_report_hash=None,
        preregistration_exact=False,
        candidate_exact=False,
    )


def build_portfolio_correlation_admission_v2_consumer_binding_v1(
    consumer_preregistration_document: Any,
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

    registration = snapshot["consumer_preregistration"]
    if not verify_portfolio_correlation_admission_v2_consumer_preregistration_v1(
        registration
    ):
        return _unknown_binding("CONSUMER_PREREGISTRATION_NOT_EXACT")

    candidate = snapshot["candidate"]
    try:
        verification = verify_portfolio_correlation_admission_v2(
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
        return _unknown_binding("V2_CANDIDATE_VERIFICATION_EXCEPTION")
    if type(verification) is not dict or verification.get("status") != "PASS":
        return _unknown_binding("V2_CANDIDATE_NOT_EXACT")
    if type(candidate) is not dict or candidate.get("status") not in {"PASS", "BLOCK"}:
        return _unknown_binding("V2_CANDIDATE_STATUS_INVALID")

    candidate_status = candidate["status"]
    evidence_hashes = candidate["evidence_hashes"]
    return _build_binding(
        status="BLOCKED",
        binding_state=(
            "EXACT_V2_RESEARCH_PASS_BOUND_CONSUMER_UNACTIVATED"
            if candidate_status == "PASS"
            else "EXACT_V2_BLOCK_BOUND_CONSUMER_UNACTIVATED"
        ),
        reason_code=(
            "EXACT_V2_RESEARCH_PASS_HASH_BOUND_DELIVERY_PRESENTATION_HOST_AND_CURRENT_ABSENT"
            if candidate_status == "PASS"
            else "EXACT_V2_BLOCK_HASH_BOUND_DELIVERY_PRESENTATION_HOST_AND_CURRENT_ABSENT"
        ),
        consumer_preregistration_hash=registration[
            "consumer_preregistration_hash"
        ],
        candidate_hash=candidate["correlation_admission_v2_hash"],
        candidate_status=candidate_status,
        common_universe_status=candidate["common_universe_status"],
        common_universe_binding_hash=evidence_hashes[
            "common_universe_binding_hash"
        ],
        v1_candidate_hash=evidence_hashes["v1_correlation_admission_hash"],
        source_report_hash=evidence_hashes["source_report_hash"],
        preregistration_exact=True,
        candidate_exact=True,
    )


def verify_portfolio_correlation_admission_v2_consumer_binding_v1(
    document: Any,
    consumer_preregistration_document: Any,
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
    rebuilt = build_portfolio_correlation_admission_v2_consumer_binding_v1(
        consumer_preregistration_document,
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
    "ADR0299_SHA256",
    "BINDING_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "V1_IMPLEMENTATION_SHA256",
    "V2_CONTRACT_TEST_SHA256",
    "V2_IMPLEMENTATION_SHA256",
    "build_portfolio_correlation_admission_v2_consumer_binding_v1",
    "build_portfolio_correlation_admission_v2_consumer_preregistration_v1",
    "verify_portfolio_correlation_admission_v2_consumer_binding_v1",
    "verify_portfolio_correlation_admission_v2_consumer_preregistration_v1",
]
