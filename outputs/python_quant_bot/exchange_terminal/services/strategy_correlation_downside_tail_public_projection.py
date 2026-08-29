from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from exchange_terminal.services.strategy_correlation_downside_tail_protocol import (
    verify_strategy_correlation_downside_tail_protocol_binding_assessment,
)


PUBLIC_SUMMARY_SCHEMA = "strategy-correlation-downside-tail-public-summary-v1"
PUBLIC_SUMMARY_VERIFICATION_SCHEMA = (
    "strategy-correlation-downside-tail-public-summary-v1-verification-v1"
)
STATIC_FINGERPRINT = "20260821-downside-tail-public-lockboard-1"

_NOT_SUPPLIED = object()

_PERMISSION = {
    "descriptive_only": True,
    "independence_proven": False,
    "count_as_independent_allowed": False,
    "candidate_binding_activation_allowed": False,
    "formal_report_binding_allowed": False,
    "formal_registry_activation_allowed": False,
    "profitability_claim_allowed": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}

_REDACTION = {
    "protocol_hash_exposed": False,
    "registration_hash_exposed": False,
    "evaluation_hash_exposed": False,
    "consumer_verification_hash_exposed": False,
    "assessment_hash_exposed": False,
    "identity_set_hash_exposed": False,
    "stratum_assignment_hash_exposed": False,
    "observation_ids_exposed": False,
    "returns_exposed": False,
    "pair_identities_exposed": False,
    "strata_exposed": False,
    "overlap_values_exposed": False,
    "p_values_exposed": False,
    "profitability_metrics_exposed": False,
}


def _summary(
    *,
    source_state: str,
    gate_decision: str,
    gate_reason: str,
    binding_status: str,
    protocol_status: str,
    maturity_state: str,
    observation_count: int | None = None,
    tail_event_count: int | None = None,
    cross_stratum_pair_count: int | None = None,
    coupled_pair_count: int | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": {
            "state": source_state,
            "evidence_contract": "PREREGISTERED_DOWNSIDE_TAIL_CANDIDATE_V1",
            "observation_count": observation_count,
            "tail_event_count": tail_event_count,
            "cross_stratum_pair_count": cross_stratum_pair_count,
            "coupled_pair_count": coupled_pair_count,
        },
        "gap": {
            "gate_decision": gate_decision,
            "gate_reason": gate_reason,
            "binding_status": binding_status,
            "protocol_status": protocol_status,
        },
        "maturity": {
            "state": maturity_state,
            "formal_registration_status": "NOT_ESTABLISHED",
            "current_status": "LOCKED",
        },
        "permission": dict(_PERMISSION),
        "redaction": dict(_REDACTION),
    }


def _not_supplied_summary() -> dict[str, Any]:
    return _summary(
        source_state="NOT_SUPPLIED",
        gate_decision="NOT_SUPPLIED",
        gate_reason="NOT_SUPPLIED",
        binding_status="NOT_SUPPLIED",
        protocol_status="NOT_SUPPLIED",
        maturity_state="NOT_SUPPLIED",
    )


def _unknown_summary() -> dict[str, Any]:
    return _summary(
        source_state="UNKNOWN",
        gate_decision="UNKNOWN",
        gate_reason="SOURCE_CONTRACT_UNKNOWN",
        binding_status="UNKNOWN",
        protocol_status="UNKNOWN",
        maturity_state="UNKNOWN",
    )


def build_strategy_correlation_downside_tail_public_summary(
    binding_assessment: Any = _NOT_SUPPLIED,
    *,
    protocol_registration: Any = None,
    evaluation: Any = None,
    consumer_receipt: Any = None,
    source_registration: Any = None,
    expected_protocol_hash: Any = None,
    expected_registration_hash: Any = None,
    expected_evaluation_hash: Any = None,
) -> dict[str, Any]:
    if binding_assessment is _NOT_SUPPLIED:
        return _not_supplied_summary()
    try:
        valid = verify_strategy_correlation_downside_tail_protocol_binding_assessment(
            binding_assessment,
            protocol_registration,
            evaluation,
            consumer_receipt,
            source_registration=source_registration,
            expected_protocol_hash=expected_protocol_hash,
            expected_registration_hash=expected_registration_hash,
            expected_evaluation_hash=expected_evaluation_hash,
        )
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        return _unknown_summary()

    if (
        binding_assessment["binding_status"] == "CANDIDATE_BOUND"
        and binding_assessment["source_state"] == "OBSERVED"
        and binding_assessment["gate_decision"] in {"PASS", "BLOCK"}
    ):
        decision = binding_assessment["gate_decision"]
        return _summary(
            source_state="OBSERVED",
            gate_decision=decision,
            gate_reason=(
                "DOWNSIDE_TAIL_COUPLING_DETECTED"
                if decision == "BLOCK"
                else "NO_SIGNIFICANT_HIGH_DOWNSIDE_TAIL_OVERLAP"
            ),
            binding_status="CANDIDATE_BOUND",
            protocol_status="VERIFIED_CANDIDATE",
            maturity_state="CANDIDATE_BOUND_NOT_FORMAL",
            observation_count=consumer_receipt["observation_count"],
            tail_event_count=consumer_receipt["tail_event_count"],
            cross_stratum_pair_count=consumer_receipt["cross_stratum_pair_count"],
            coupled_pair_count=consumer_receipt["coupled_pair_count"],
        )

    if (
        binding_assessment["binding_status"] == "CANDIDATE_BLOCKED"
        and binding_assessment["source_state"] == "UNKNOWN"
    ):
        return _summary(
            source_state="UNKNOWN",
            gate_decision="BLOCK",
            gate_reason="SOURCE_EVALUATION_UNKNOWN",
            binding_status="CANDIDATE_BLOCKED",
            protocol_status="VERIFIED_CANDIDATE",
            maturity_state="CANDIDATE_BLOCKED_NOT_FORMAL",
        )
    return _unknown_summary()


def verify_strategy_correlation_downside_tail_public_summary(
    document: Any,
    binding_assessment: Any = _NOT_SUPPLIED,
    *,
    protocol_registration: Any = None,
    evaluation: Any = None,
    consumer_receipt: Any = None,
    source_registration: Any = None,
    expected_protocol_hash: Any = None,
    expected_registration_hash: Any = None,
    expected_evaluation_hash: Any = None,
) -> dict[str, Any]:
    expected = build_strategy_correlation_downside_tail_public_summary(
        binding_assessment,
        protocol_registration=protocol_registration,
        evaluation=evaluation,
        consumer_receipt=consumer_receipt,
        source_registration=source_registration,
        expected_protocol_hash=expected_protocol_hash,
        expected_registration_hash=expected_registration_hash,
        expected_evaluation_hash=expected_evaluation_hash,
    )
    valid = bool(
        type(document) is dict
        and strict_json_contract_equal(document, expected)
        and not strict_research_authority_invalid(document)
    )
    return seal_strict_canonical_document(
        {
            "schema_version": PUBLIC_SUMMARY_VERIFICATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "verification_status": "PASS" if valid else "BLOCK",
            "public_state": document["source"]["state"] if valid else "UNKNOWN",
            "gate_decision": document["gap"]["gate_decision"] if valid else "UNKNOWN",
            "authority": dict(_PERMISSION),
        },
        "verification_hash",
    )
