from __future__ import annotations

import hmac
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_downside_tail_gate import (
    verify_strategy_correlation_downside_tail_evaluation,
    verify_strategy_correlation_downside_tail_registration,
)


VERIFICATION_SCHEMA = "strategy-correlation-downside-tail-report-consumer-verification-v1"
STATIC_FINGERPRINT = "20260821-downside-tail-report-consumer-1"

_AUTHORITY = {
    "descriptive_only": True,
    "independence_proven": False,
    "count_as_independent_allowed": False,
    "candidate_report_binding_activation_allowed": False,
    "formal_report_binding_allowed": False,
    "formal_registry_activation_allowed": False,
    "profitability_claim_allowed": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _sealed_receipt(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "verification_hash")


def _unknown_receipt(
    *,
    registration_hash_verified: bool,
    evaluation_hash_verified: bool,
) -> dict[str, Any]:
    return _sealed_receipt(
        {
            "schema_version": VERIFICATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "verification_status": "BLOCK",
            "source_state": "UNKNOWN",
            "gate_decision": "UNKNOWN",
            "gate_reason": "EVALUATION_CONTRACT_UNKNOWN",
            "candidate_binding_status": "UNKNOWN",
            "registration_hash": None,
            "evaluation_hash": None,
            "registration_hash_verified": registration_hash_verified,
            "evaluation_hash_verified": evaluation_hash_verified,
            "semantic_contract_verified": False,
            "observation_count": None,
            "tail_event_count": None,
            "cross_stratum_pair_count": None,
            "tested_pair_count": None,
            "coupled_pair_count": None,
            "verification_blockers": ["EVALUATION_CONTRACT_UNKNOWN"],
            "source_blockers": [],
            "authority": dict(_AUTHORITY),
        }
    )


def consume_strategy_correlation_downside_tail_evaluation(
    evaluation: Any,
    *,
    registration: Any,
    expected_registration_hash: Any,
    expected_evaluation_hash: Any,
) -> dict[str, Any]:
    registration_contract_verified = verify_strategy_correlation_downside_tail_registration(
        registration
    )
    registration_hash_verified = bool(
        registration_contract_verified
        and strict_sha256(expected_registration_hash)
        and hmac.compare_digest(
            registration["registration_hash"],
            expected_registration_hash,
        )
    )
    evaluation_hash_verified = bool(
        type(evaluation) is dict
        and strict_sha256(evaluation.get("evaluation_hash"))
        and strict_sha256(expected_evaluation_hash)
        and hmac.compare_digest(
            evaluation["evaluation_hash"],
            expected_evaluation_hash,
        )
    )
    semantic_contract_verified = verify_strategy_correlation_downside_tail_evaluation(
        evaluation,
        registration,
        expected_registration_hash=expected_registration_hash,
        expected_evaluation_hash=expected_evaluation_hash,
    )
    if not semantic_contract_verified:
        return _unknown_receipt(
            registration_hash_verified=registration_hash_verified,
            evaluation_hash_verified=evaluation_hash_verified,
        )

    source_state = evaluation["source_state"]
    source_observed = source_state == "OBSERVED"
    return _sealed_receipt(
        {
            "schema_version": VERIFICATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "verification_status": "PASS" if source_observed else "BLOCK",
            "source_state": source_state,
            "gate_decision": evaluation["gate_decision"],
            "gate_reason": evaluation["gate_reason"],
            "candidate_binding_status": "CANDIDATE_HASH_BOUND_NOT_FORMAL",
            "registration_hash": registration["registration_hash"],
            "evaluation_hash": evaluation["evaluation_hash"],
            "registration_hash_verified": True,
            "evaluation_hash_verified": True,
            "semantic_contract_verified": True,
            "observation_count": evaluation["observation_count"],
            "tail_event_count": evaluation["tail_event_count"],
            "cross_stratum_pair_count": evaluation["cross_stratum_pair_count"],
            "tested_pair_count": evaluation["tested_pair_count"],
            "coupled_pair_count": evaluation["coupled_pair_count"],
            "verification_blockers": [] if source_observed else ["SOURCE_EVALUATION_UNKNOWN"],
            "source_blockers": list(evaluation["blockers"]),
            "authority": dict(_AUTHORITY),
        }
    )


def verify_strategy_correlation_downside_tail_consumer_receipt(
    document: Any,
    evaluation: Any,
    *,
    registration: Any,
    expected_registration_hash: Any,
    expected_evaluation_hash: Any,
) -> bool:
    if type(document) is not dict:
        return False
    expected = consume_strategy_correlation_downside_tail_evaluation(
        evaluation,
        registration=registration,
        expected_registration_hash=expected_registration_hash,
        expected_evaluation_hash=expected_evaluation_hash,
    )
    return strict_json_contract_equal(document, expected)
