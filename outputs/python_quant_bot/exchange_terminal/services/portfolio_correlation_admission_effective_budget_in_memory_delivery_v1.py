"""Summary-only in-memory delivery for the admission-budget binding v1."""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_binding_v1 as binding_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-"
    "in-memory-delivery-envelope-v1"
)
PAYLOAD_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-"
    "presentation-payload-v1"
)
RECEIPT_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-"
    "payload-extraction-receipt-v1"
)
STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-effective-budget-"
    "in-memory-delivery-v1-lock-1"
)
BINDING_IMPLEMENTATION_SHA256 = (
    "7263b07df309ad3c2a4c79313e62ff8912c567ee0cf6a2ee9abdc336ce6bd9e9"
)
JAVASCRIPT_GLOBAL = (
    "HakimiPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1"
)
FUNCTION_EXPORTS = (
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1",
    "extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1",
    "buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1",
    "verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1",
)

_HEX_CHARS = frozenset("0123456789abcdef")
_PAYLOAD_SOURCE_FIELDS = (
    "binding_hash",
    "report_universe_contract_hash",
    "correlation_preregistration_hash",
    "correlation_matrix_hash",
    "complete_link_audit_hash",
    "complete_link_gate_hash",
    "strata_registration_hash",
    "strata_gate_hash",
    "admission_v2_hash",
    "effective_budget_v3_hash",
    "strategy_identity_hash",
    "proposal_scope_hash",
)


class _InvalidJsonDocument(ValueError):
    pass


def _plain_json_snapshot(
    value: Any,
    active: set[int] | None = None,
) -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise _InvalidJsonDocument("non-finite numbers are not supported")
        return value
    if type(value) not in (dict, list):
        raise _InvalidJsonDocument("document must contain exact JSON types")

    if active is None:
        active = set()
    identity = id(value)
    if identity in active:
        raise _InvalidJsonDocument("cyclic documents are not supported")
    active.add(identity)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise _InvalidJsonDocument("object keys must be exact strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(identity)


def _hash_or_none(value: Any) -> str | None:
    if (
        type(value) is str
        and len(value) == 64
        and all(character in _HEX_CHARS for character in value)
    ):
        return value
    return None


def _locked_authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "runtime_delivery_allowed": False,
        "browser_execution_allowed": False,
        "dom_access_allowed": False,
        "render_allowed": False,
        "ui_mount_allowed": False,
        "route_registration_allowed": False,
        "endpoint_registration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _transport() -> dict[str, Any]:
    return {
        "mode": "IN_MEMORY_JSON_DOCUMENT",
        "network_used": False,
        "storage_used": False,
        "persisted": False,
        "endpoint": None,
        "route": None,
    }


def _consumer_contract() -> dict[str, Any]:
    return {
        "javascript_global": JAVASCRIPT_GLOBAL,
        "module_format": "UMD_COMMONJS",
        "function_exports": list(FUNCTION_EXPORTS),
        "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
        "envelope_schema_version": SCHEMA_VERSION,
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "tier_order": list(binding_v1.TIER_ORDER),
        "host_script": None,
        "host_stylesheet": None,
        "host_slot": None,
        "payload_source_provider": None,
    }


def _provenance(
    *,
    binding_hash: str | None,
    admission_v2_hash: str | None,
    effective_budget_v3_hash: str | None,
    presentation_payload_hash: str | None,
) -> dict[str, str | None]:
    return {
        "binding_schema_version": binding_v1.SCHEMA_VERSION,
        "binding_static_fingerprint": binding_v1.STATIC_FINGERPRINT,
        "binding_hash": binding_hash,
        "admission_v2_hash": admission_v2_hash,
        "effective_budget_v3_hash": effective_budget_v3_hash,
        "presentation_payload_hash": presentation_payload_hash,
    }


def _build_unknown(reason_code: str) -> dict[str, Any]:
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNKNOWN",
        "delivery_state": "UNKNOWN",
        "reason_code": reason_code,
        "transport": _transport(),
        "consumer_contract": _consumer_contract(),
        "provenance": _provenance(
            binding_hash=None,
            admission_v2_hash=None,
            effective_budget_v3_hash=None,
            presentation_payload_hash=None,
        ),
        "presentation_payload": None,
        "facts": {
            "binding_exactly_verified": False,
            "payload_projected": False,
            "runtime_mutations_performed": False,
            "source_documents_embedded": False,
            "browser_executed": False,
            "dom_accessed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(envelope, "delivery_envelope_hash")


def _build_payload(binding: dict[str, Any]) -> dict[str, Any]:
    binding_source = binding["source"]
    payload_source = {
        "binding_hash": binding["binding_hash"],
        **{
            field: binding_source[field]
            for field in _PAYLOAD_SOURCE_FIELDS
            if field != "binding_hash"
        },
    }
    payload = {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "KNOWN",
        "binding_status": binding["status"],
        "first_blocking_tier": binding["first_blocking_tier"],
        "admission_v2_status": binding["admission_v2_status"],
        "effective_budget_v3_status": binding[
            "effective_budget_v3_status"
        ],
        "source": payload_source,
        "checks": binding["checks"],
        "tiers": binding["tiers"],
        "blockers": binding["blockers"],
        "facts": {
            "binding_exactly_verified": True,
            "hash_only_projection": True,
            "source_documents_embedded": False,
            "positions_embedded": False,
            "strategy_identity_embedded": False,
            "raw_symbol_lists_embedded": False,
            "profitability_proven": False,
        },
        "permissions": {
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "render_allowed": False,
            "dom_access_allowed": False,
            "browser_execution_allowed": False,
        },
    }
    return seal_strict_canonical_document(
        payload,
        "presentation_payload_hash",
    )


def _build_exact(binding: dict[str, Any]) -> dict[str, Any]:
    payload = _build_payload(binding)
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "KNOWN",
        "delivery_state": "EXACT_IN_MEMORY",
        "reason_code": "EXACT_BINDING_PROJECTED",
        "transport": _transport(),
        "consumer_contract": _consumer_contract(),
        "provenance": _provenance(
            binding_hash=binding["binding_hash"],
            admission_v2_hash=binding["source"]["admission_v2_hash"],
            effective_budget_v3_hash=binding["source"][
                "effective_budget_v3_hash"
            ],
            presentation_payload_hash=payload[
                "presentation_payload_hash"
            ],
        ),
        "presentation_payload": payload,
        "facts": {
            "binding_exactly_verified": True,
            "payload_projected": True,
            "runtime_mutations_performed": False,
            "source_documents_embedded": False,
            "browser_executed": False,
            "dom_accessed": False,
            "profitability_proven": False,
        },
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(envelope, "delivery_envelope_hash")


def build_portfolio_correlation_admission_effective_budget_in_memory_delivery_envelope_v1(
    binding_document: Any,
    admission_v2_document: Any,
    effective_budget_v3_document: Any,
    report_document: Any,
    correlation_preregistration_document: Any,
    correlation_matrix_document: Any,
    selection_cells_document: Any,
    complete_link_audit_document: Any,
    complete_link_gate_document: Any,
    strata_preregistration_document: Any,
    strata_gate_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = binding_v1.DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    try:
        binding = _plain_json_snapshot(binding_document)
    except (TypeError, ValueError):
        return _build_unknown("BINDING_UNKNOWN")

    try:
        receipt = (
            binding_v1.verify_portfolio_correlation_admission_effective_budget_binding_v1(
                binding,
                admission_v2_document,
                effective_budget_v3_document,
                report_document,
                correlation_preregistration_document,
                correlation_matrix_document,
                selection_cells_document,
                complete_link_audit_document,
                complete_link_gate_document,
                strata_preregistration_document,
                strata_gate_document,
                strategy_id=strategy_id,
                variant_id=variant_id,
                lane=lane,
                equity=equity,
                positions=positions,
                proposed_symbol=proposed_symbol,
                proposed_notional=proposed_notional,
                proposed_direction=proposed_direction,
                max_cluster_gross_pct=max_cluster_gross_pct,
                risk_increasing=risk_increasing,
            )
        )
    except (KeyError, TypeError, ValueError):
        return _build_unknown("BINDING_UNKNOWN")

    if type(receipt) is not dict or receipt.get("status") != "PASS":
        return _build_unknown("BINDING_UNKNOWN")
    if (
        type(binding) is not dict
        or binding.get("checks", {}).get("input_snapshot_exact") is not True
        or _hash_or_none(binding.get("binding_hash")) is None
        or type(binding.get("source")) is not dict
        or any(
            _hash_or_none(binding["source"].get(field)) is None
            for field in binding_v1._SOURCE_FIELDS
        )
    ):
        return _build_unknown("BINDING_SOURCE_UNKNOWN")

    try:
        return _build_exact(binding)
    except (KeyError, TypeError, ValueError):
        return _build_unknown("DELIVERY_BUILD_FAILED")


def verify_portfolio_correlation_admission_effective_budget_in_memory_delivery_envelope_v1(
    document: Any,
    binding_document: Any,
    admission_v2_document: Any,
    effective_budget_v3_document: Any,
    report_document: Any,
    correlation_preregistration_document: Any,
    correlation_matrix_document: Any,
    selection_cells_document: Any,
    complete_link_audit_document: Any,
    complete_link_gate_document: Any,
    strata_preregistration_document: Any,
    strata_gate_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = binding_v1.DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
) -> bool:
    expected = build_portfolio_correlation_admission_effective_budget_in_memory_delivery_envelope_v1(
        binding_document,
        admission_v2_document,
        effective_budget_v3_document,
        report_document,
        correlation_preregistration_document,
        correlation_matrix_document,
        selection_cells_document,
        complete_link_audit_document,
        complete_link_gate_document,
        strata_preregistration_document,
        strata_gate_document,
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
        equity=equity,
        positions=positions,
        proposed_symbol=proposed_symbol,
        proposed_notional=proposed_notional,
        proposed_direction=proposed_direction,
        max_cluster_gross_pct=max_cluster_gross_pct,
        risk_increasing=risk_increasing,
    )
    return strict_json_contract_equal(document, expected)
