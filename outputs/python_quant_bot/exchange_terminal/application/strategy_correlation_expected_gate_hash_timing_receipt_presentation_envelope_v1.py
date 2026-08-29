from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_expected_gate_hash_timing_receipt as receipt_contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-expected-gate-hash-timing-receipt-"
    "presentation-envelope-v1"
)
VERIFICATION_CONTEXT_SCHEMA_VERSION = (
    "strategy-correlation-expected-gate-hash-timing-receipt-"
    "presentation-verification-context-v1"
)
STATIC_FINGERPRINT = (
    "20260822-expected-gate-hash-timing-receipt-neutral-presentation-1"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"
CANDIDATE_DISPLAY_STATE = "CANDIDATE_CONTRACT_OBSERVED_AUTHORITY_UNPROVEN"
UNKNOWN_DISPLAY_STATE = "UNKNOWN"
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

SOURCE_RECEIPT_SCHEMA_VERSION = receipt_contract.RECEIPT_SCHEMA_VERSION
SOURCE_VERIFICATION_SCHEMA_VERSION = receipt_contract.VERIFICATION_SCHEMA_VERSION

_CONTEXT_ARGUMENT_FIELDS = frozenset(
    {
        "gate_stage",
        "expected_gate_bindings",
        "expected_receipt_id",
        "expected_anchor_provider",
        "expected_anchor_namespace",
        "expected_anchor_id",
        "expected_declared_at",
        "expected_anchored_at",
        "expected_evidence_not_before",
        "expected_base_artifact_hash",
        "expected_protocol_registration_hash",
        "expected_identity_set_hash",
        "expected_source_linkage_hash",
        "expected_gate_commitment_hash",
        "expected_external_anchor_receipt_hash",
        "expected_candidate_receipt_hash",
    }
)
_CONTEXT_FIELDS = frozenset(
    {"schema_version", *_CONTEXT_ARGUMENT_FIELDS}
)
_PRESENTATION_BLOCKERS = (
    *receipt_contract.AUTHORITY_GAPS,
    "TIMING_AUTHORITY_NOT_PROVEN",
    "PREREGISTRATION_AUTHORITY_NOT_PROVEN",
    "NATURAL_FORWARD_MATURITY_NOT_PROVEN",
    "CURRENT_CONSUMER_BINDING_ABSENT",
    "TRADING_AUTHORITY_NOT_GRANTED",
)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "candidate_contract_promotion_allowed": False,
        "timing_authority_promotion_allowed": False,
        "maturity_promotion_allowed": False,
        "profitability_claim_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "result_available": False,
        "candidate_receipt_contract_verified": False,
        "source_linkage_bound": False,
        "expected_gate_commitment_bound": False,
        "chronology_contract_verified": False,
        "external_anchor_authenticity_verified": False,
        "timing_authority_verified": False,
        "preregistration_authority_verified": False,
        "natural_forward_maturity_proven": False,
        "market_outcome_evidence_present": False,
        "profitability_proven": False,
    }


def _summary() -> dict[str, Any]:
    return {
        "candidate_receipt_contract": None,
        "gate_stage": None,
        "identity_count": None,
        "timing_authority": None,
        "preregistration_authority": None,
        "natural_forward_maturity": None,
        "current_reference_present": False,
    }


def _lineage(*, source_bound: bool) -> dict[str, Any]:
    return {
        "source_receipt_schema_version": (
            SOURCE_RECEIPT_SCHEMA_VERSION if source_bound else None
        ),
        "source_verification_schema_version": (
            SOURCE_VERIFICATION_SCHEMA_VERSION if source_bound else None
        ),
        "source_receipt_embedded": False,
        "gate_bindings_embedded": False,
        "verification_context_embedded": False,
    }


def _unknown_axes(detail: str) -> list[dict[str, str]]:
    return [
        {
            "axis": axis,
            "state": "UNKNOWN",
            "signal": "UNKNOWN",
            "headline": "Evidence unavailable",
            "detail": detail,
        }
        for axis in AXIS_ORDER
    ]


def _candidate_axes() -> list[dict[str, str]]:
    return [
        {
            "axis": "SOURCE",
            "state": "CANDIDATE CONTRACT VERIFIED",
            "signal": "OBSERVED",
            "headline": "Expected-gate commitment contract verified",
            "detail": "Identity, source-linkage, gate-commitment and chronology fields passed the candidate consumer; this is structural evidence only.",
        },
        {
            "axis": "GAP",
            "state": "EXTERNAL AUTHORITY UNPROVEN",
            "signal": "BLOCKED",
            "headline": "External timing authority remains absent",
            "detail": "Anchor authenticity, immutable persistence, uniqueness, freshness and rollback resistance are not verified.",
        },
        {
            "axis": "MATURITY",
            "state": "NOT PROVEN",
            "signal": "UNKNOWN",
            "headline": "No maturity promotion",
            "detail": "A candidate receipt contract does not establish preregistration authority, natural-forward maturity, market outcomes or profitability.",
        },
        {
            "axis": "PERMISSION",
            "state": "RESEARCH ONLY",
            "signal": "LOCKED",
            "headline": "No admission or trading authority",
            "detail": "The envelope is descriptive and unmounted. Current writes, paper authorization and live orders remain disabled.",
        },
    ]


def _sealed(
    *,
    display_state: str,
    axes: list[dict[str, str]],
    summary: dict[str, Any],
    lineage: dict[str, Any],
    facts: dict[str, bool],
    blockers: list[str],
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "presentation_status": PRESENTATION_STATUS,
            "display_state": display_state,
            "axis_order": list(AXIS_ORDER),
            "axes": axes,
            "summary": summary,
            "lineage": lineage,
            "facts": facts,
            "authority": _authority(),
            "blockers": blockers,
        },
        "presentation_hash",
    )


def _unknown(reason: str) -> dict[str, Any]:
    return _sealed(
        display_state=UNKNOWN_DISPLAY_STATE,
        axes=_unknown_axes(
            "The timing-receipt candidate did not verify for presentation."
        ),
        summary=_summary(),
        lineage=_lineage(source_bound=False),
        facts=_facts(),
        blockers=[reason],
    )


def _context_valid(value: Any) -> bool:
    return (
        type(value) is dict
        and frozenset(value) == _CONTEXT_FIELDS
        and value.get("schema_version") == VERIFICATION_CONTEXT_SCHEMA_VERSION
    )


def _verification_presentable(verification: Any) -> bool:
    if type(verification) is not dict:
        return False
    if (
        verification.get("schema_version") != SOURCE_VERIFICATION_SCHEMA_VERSION
        or verification.get("status") != "PASS"
        or verification.get("decision") != "BLOCK"
        or verification.get("authority_gaps")
        != list(receipt_contract.AUTHORITY_GAPS)
        or verification.get("gate_stage")
        not in receipt_contract.SUPPORTED_GATE_STAGES
        or type(verification.get("identity_count")) is not int
        or verification.get("identity_count", 0) <= 0
        or verification.get("candidate_receipt_verified") is not True
        or verification.get("source_linkage_bound") is not True
        or verification.get("expected_gate_commitment_bound") is not True
        or verification.get("chronology_contract_verified") is not True
        or verification.get("external_anchor_receipt_hash_bound") is not True
        or verification.get("candidate_only") is not True
        or verification.get("consumer_only") is not True
    ):
        return False
    for field in (
        "receipt_producer_implemented",
        "anchor_receipt_verifier_implemented",
        "external_anchor_authenticity_verified",
        "immutable_persistence_verified",
        "anchor_uniqueness_verified",
        "anchor_freshness_verified",
        "rollback_resistance_verified",
        "timing_authority_verified",
        "preregistration_authority_verified",
        "formal_registry_bound",
        "formal_registry_activation_allowed",
        "writer_implemented",
        "current_writer_activation_allowed",
        "current_admission_allowed",
    ):
        if verification.get(field) is not False:
            return False
    permissions = verification.get("permissions")
    return (
        type(permissions) is dict
        and permissions.get("research_only") is True
        and permissions.get("paper_authorized") is False
        and permissions.get("live_order_allowed") is False
    )


def build_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1(
    candidate_receipt: Any,
    *,
    verification_context: Any,
) -> dict[str, Any]:
    if type(candidate_receipt) is not dict:
        return _unknown("SOURCE_RECEIPT_INVALID")
    if not _context_valid(verification_context):
        return _unknown("VERIFICATION_CONTEXT_INVALID")
    arguments = {
        field: verification_context[field]
        for field in _CONTEXT_ARGUMENT_FIELDS
    }
    try:
        verification = receipt_contract.verify_strategy_correlation_expected_gate_hash_timing_receipt_candidate(
            candidate_receipt,
            **arguments,
        )
    except Exception:
        return _unknown("SOURCE_RECEIPT_VERIFIER_ERROR")
    if not _verification_presentable(verification):
        return _unknown("SOURCE_RECEIPT_UNVERIFIED")

    facts = _facts()
    facts.update(
        {
            "result_available": True,
            "candidate_receipt_contract_verified": True,
            "source_linkage_bound": True,
            "expected_gate_commitment_bound": True,
            "chronology_contract_verified": True,
        }
    )
    summary = _summary()
    summary.update(
        {
            "candidate_receipt_contract": "VERIFIED_CANDIDATE_ONLY",
            "gate_stage": verification["gate_stage"],
            "identity_count": verification["identity_count"],
            "timing_authority": "NOT_PROVEN",
            "preregistration_authority": "NOT_PROVEN",
            "natural_forward_maturity": "NOT_PROVEN",
        }
    )
    return _sealed(
        display_state=CANDIDATE_DISPLAY_STATE,
        axes=_candidate_axes(),
        summary=summary,
        lineage=_lineage(source_bound=True),
        facts=facts,
        blockers=list(_PRESENTATION_BLOCKERS),
    )


def verify_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1(
    document: Any,
    candidate_receipt: Any,
    *,
    verification_context: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1(
            candidate_receipt,
            verification_context=verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "AXIS_ORDER",
    "CANDIDATE_DISPLAY_STATE",
    "PRESENTATION_STATUS",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNKNOWN_DISPLAY_STATE",
    "VERIFICATION_CONTEXT_SCHEMA_VERSION",
    "build_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1",
    "verify_strategy_correlation_expected_gate_hash_timing_receipt_presentation_envelope_v1",
]
