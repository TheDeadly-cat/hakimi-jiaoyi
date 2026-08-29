from __future__ import annotations

import hmac
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_downside_tail_gate import (
    EVALUATION_SCHEMA,
    REGISTRATION_SCHEMA,
    STATIC_FINGERPRINT as GATE_STATIC_FINGERPRINT,
    verify_strategy_correlation_downside_tail_registration,
)
from exchange_terminal.services.strategy_correlation_downside_tail_report_consumer import (
    STATIC_FINGERPRINT as CONSUMER_STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA as CONSUMER_VERIFICATION_SCHEMA,
    verify_strategy_correlation_downside_tail_consumer_receipt,
)


PROTOCOL_SCHEMA = "strategy-correlation-downside-tail-protocol-registration-candidate-v1"
PROTOCOL_VERIFICATION_SCHEMA = (
    "strategy-correlation-downside-tail-protocol-registration-candidate-v1-verification-v1"
)
BINDING_ASSESSMENT_SCHEMA = (
    "strategy-correlation-downside-tail-protocol-binding-candidate-v1"
)
STATIC_FINGERPRINT = "20260821-downside-tail-protocol-binding-1"

_AUTHORITY = {
    "descriptive_only": True,
    "independence_proven": False,
    "count_as_independent_allowed": False,
    "registration_timing_attested": False,
    "formal_preregistration_bound": False,
    "candidate_binding_activation_allowed": False,
    "formal_report_binding_allowed": False,
    "formal_registry_activation_allowed": False,
    "profitability_claim_allowed": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _contract() -> dict[str, Any]:
    return {
        "registration_hash_source": "EXTERNAL_PIN_REQUIRED",
        "evaluation_hash_source": "EXTERNAL_PIN_REQUIRED_AFTER_OBSERVATION",
        "protocol_hash_source": "EXTERNAL_PIN_REQUIRED",
        "pair_scope": "CROSS_PREREGISTERED_STRATA_ONLY",
        "allowed_observed_gate_decisions": ["PASS", "BLOCK"],
        "observed_block_handling": "PRESERVE_AS_OBSERVED_BLOCK",
        "unknown_handling": "CANDIDATE_BLOCKED",
        "candidate_binding_rule": "OBSERVED_PASS_OR_BLOCK_ONLY",
        "formal_migration_rule": "SEPARATE_REVIEW_REQUIRED",
    }


def build_strategy_correlation_downside_tail_protocol_registration(
    source_registration: Any,
) -> dict[str, Any]:
    if not verify_strategy_correlation_downside_tail_registration(source_registration):
        raise ValueError("source registration does not satisfy the fixed candidate contract")
    document = {
        "schema_version": PROTOCOL_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source_registration_schema": REGISTRATION_SCHEMA,
        "source_registration_hash": source_registration["registration_hash"],
        "identity_set_hash": source_registration["identity_set_hash"],
        "stratum_assignment_hash": source_registration["stratum_assignment_hash"],
        "target_gate_schema": EVALUATION_SCHEMA,
        "target_gate_static_fingerprint": GATE_STATIC_FINGERPRINT,
        "target_consumer_schema": CONSUMER_VERIFICATION_SCHEMA,
        "target_consumer_static_fingerprint": CONSUMER_STATIC_FINGERPRINT,
        "contract": _contract(),
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(document, "protocol_hash")


def _protocol_contract_valid(
    document: Any,
    source_registration: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_downside_tail_protocol_registration(
            source_registration
        )
    except (TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def verify_strategy_correlation_downside_tail_protocol_registration(
    document: Any,
    *,
    source_registration: Any,
) -> dict[str, Any]:
    valid = _protocol_contract_valid(document, source_registration)
    receipt = {
        "schema_version": PROTOCOL_VERIFICATION_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "verification_status": "PASS" if valid else "BLOCK",
        "protocol_contract_verified": valid,
        "source_registration_verified": valid,
        "protocol_hash": document["protocol_hash"] if valid else None,
        "source_registration_hash": (
            source_registration["registration_hash"] if valid else None
        ),
        "blockers": [] if valid else ["PROTOCOL_CONTRACT_UNKNOWN"],
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(receipt, "verification_hash")


def _unknown_assessment(
    *,
    protocol_contract_verified: bool,
    protocol_hash_verified: bool,
    consumer_receipt_verified: bool,
    reason: str,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": BINDING_ASSESSMENT_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "assessment_status": "BLOCK",
            "source_state": "UNKNOWN",
            "gate_decision": "UNKNOWN",
            "gate_reason": "SOURCE_CONTRACT_UNKNOWN",
            "binding_status": "UNKNOWN",
            "protocol_hash": None,
            "registration_hash": None,
            "evaluation_hash": None,
            "consumer_verification_hash": None,
            "protocol_contract_verified": protocol_contract_verified,
            "protocol_hash_verified": protocol_hash_verified,
            "consumer_receipt_verified": consumer_receipt_verified,
            "source_semantic_verified": False,
            "binding_blockers": [reason],
            "source_blockers": [],
            "authority": dict(_AUTHORITY),
        },
        "assessment_hash",
    )


def assess_strategy_correlation_downside_tail_protocol_binding(
    protocol_registration: Any,
    evaluation: Any,
    consumer_receipt: Any,
    *,
    source_registration: Any,
    expected_protocol_hash: Any,
    expected_registration_hash: Any,
    expected_evaluation_hash: Any,
) -> dict[str, Any]:
    protocol_contract_verified = _protocol_contract_valid(
        protocol_registration,
        source_registration,
    )
    protocol_hash_verified = bool(
        protocol_contract_verified
        and strict_sha256(expected_protocol_hash)
        and hmac.compare_digest(
            protocol_registration["protocol_hash"],
            expected_protocol_hash,
        )
    )
    consumer_receipt_verified = verify_strategy_correlation_downside_tail_consumer_receipt(
        consumer_receipt,
        evaluation,
        registration=source_registration,
        expected_registration_hash=expected_registration_hash,
        expected_evaluation_hash=expected_evaluation_hash,
    )

    if not protocol_contract_verified:
        return _unknown_assessment(
            protocol_contract_verified=False,
            protocol_hash_verified=False,
            consumer_receipt_verified=consumer_receipt_verified,
            reason="PROTOCOL_CONTRACT_UNKNOWN",
        )
    if not protocol_hash_verified:
        return _unknown_assessment(
            protocol_contract_verified=True,
            protocol_hash_verified=False,
            consumer_receipt_verified=consumer_receipt_verified,
            reason="EXPECTED_PROTOCOL_HASH_MISMATCH",
        )
    if not consumer_receipt_verified:
        return _unknown_assessment(
            protocol_contract_verified=True,
            protocol_hash_verified=True,
            consumer_receipt_verified=False,
            reason="CONSUMER_RECEIPT_UNKNOWN",
        )

    source_observed = consumer_receipt["source_state"] == "OBSERVED"
    binding_status = "CANDIDATE_BOUND" if source_observed else "CANDIDATE_BLOCKED"
    return seal_strict_canonical_document(
        {
            "schema_version": BINDING_ASSESSMENT_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "assessment_status": "PASS" if source_observed else "BLOCK",
            "source_state": consumer_receipt["source_state"],
            "gate_decision": consumer_receipt["gate_decision"],
            "gate_reason": consumer_receipt["gate_reason"],
            "binding_status": binding_status,
            "protocol_hash": protocol_registration["protocol_hash"],
            "registration_hash": source_registration["registration_hash"],
            "evaluation_hash": evaluation["evaluation_hash"],
            "consumer_verification_hash": consumer_receipt["verification_hash"],
            "protocol_contract_verified": True,
            "protocol_hash_verified": True,
            "consumer_receipt_verified": True,
            "source_semantic_verified": consumer_receipt["semantic_contract_verified"],
            "binding_blockers": [] if source_observed else ["SOURCE_EVALUATION_UNKNOWN"],
            "source_blockers": list(consumer_receipt["source_blockers"]),
            "authority": dict(_AUTHORITY),
        },
        "assessment_hash",
    )


def verify_strategy_correlation_downside_tail_protocol_binding_assessment(
    document: Any,
    protocol_registration: Any,
    evaluation: Any,
    consumer_receipt: Any,
    *,
    source_registration: Any,
    expected_protocol_hash: Any,
    expected_registration_hash: Any,
    expected_evaluation_hash: Any,
) -> bool:
    if type(document) is not dict:
        return False
    expected = assess_strategy_correlation_downside_tail_protocol_binding(
        protocol_registration,
        evaluation,
        consumer_receipt,
        source_registration=source_registration,
        expected_protocol_hash=expected_protocol_hash,
        expected_registration_hash=expected_registration_hash,
        expected_evaluation_hash=expected_evaluation_hash,
    )
    return strict_json_contract_equal(document, expected)
