from __future__ import annotations

from typing import Any

from .strategy_correlation_cross_lag_gate import (
    EVALUATION_SCHEMA,
    LAGS,
    STATIC_FINGERPRINT as GATE_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_evaluation,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


VERIFICATION_SCHEMA = "strategy-correlation-cross-lag-report-consumer-verification-v1"
STATIC_FINGERPRINT = "20260821-cross-lag-report-consumer-1"

_LOCKED_AUTHORITY = {
    "descriptive_only": True,
    "formal_preregistration_bound": False,
    "sequence_order_attested": False,
    "strata_timing_attested": False,
    "independence_proven": False,
    "count_as_independent_allowed": False,
    "candidate_binding_activation_allowed": False,
    "formal_registry_activation_allowed": False,
    "formal_registry_written": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
    "current_pointer_written": False,
    "paper_authorized": False,
    "live_order_allowed": False,
    "profitability_claim_allowed": False,
}


def _sealed_receipt(
    *,
    report_state: str,
    source_state: str,
    gap_state: str,
    maturity_state: str,
    gate_decision: str,
    gate_reason: str,
    blockers: list[str],
    source_evaluation_hash: str = "",
    stratum_assignment_hash: str = "",
    cross_stratum_pair_count: int = 0,
    lag_test_count: int = 0,
    dependent_test_count: int = 0,
    max_adjusted_absolute_lower: str = "0",
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": VERIFICATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "report_state": report_state,
            "source_state": source_state,
            "gap_state": gap_state,
            "maturity_state": maturity_state,
            "permission_state": "LOCKED",
            "source_schema_version": EVALUATION_SCHEMA,
            "source_static_fingerprint": GATE_STATIC_FINGERPRINT,
            "source_evaluation_hash": source_evaluation_hash,
            "stratum_assignment_hash": stratum_assignment_hash,
            "lag_family": list(LAGS),
            "cross_stratum_pair_count": cross_stratum_pair_count,
            "lag_test_count": lag_test_count,
            "dependent_test_count": dependent_test_count,
            "max_adjusted_absolute_lower": max_adjusted_absolute_lower,
            "gate_decision": gate_decision,
            "gate_reason": gate_reason,
            "blockers": list(blockers),
            "authority": dict(_LOCKED_AUTHORITY),
        },
        "verification_hash",
    )


def _not_supplied_receipt() -> dict[str, Any]:
    return _sealed_receipt(
        report_state="NOT_SUPPLIED",
        source_state="NOT_SUPPLIED",
        gap_state="SOURCE_NOT_SUPPLIED",
        maturity_state="NOT_EVALUATED",
        gate_decision="UNKNOWN",
        gate_reason="EVALUATION_NOT_SUPPLIED",
        blockers=["EVALUATION_NOT_SUPPLIED"],
    )


def _unknown_receipt() -> dict[str, Any]:
    return _sealed_receipt(
        report_state="UNKNOWN",
        source_state="UNKNOWN",
        gap_state="SOURCE_INVALID",
        maturity_state="UNKNOWN",
        gate_decision="UNKNOWN",
        gate_reason="EVALUATION_INVALID",
        blockers=["EVALUATION_INVALID"],
    )


def consume_strategy_correlation_cross_lag_evaluation(
    evaluation: Any,
    *,
    preregistered_strata: Any,
    aligned_observations: Any,
    expected_stratum_assignment_hash: Any,
    expected_evaluation_hash: Any,
) -> dict[str, Any]:
    """Replay and redact one candidate evaluation without performing I/O."""

    if evaluation is None:
        return _not_supplied_receipt()
    if not isinstance(evaluation, dict):
        return _unknown_receipt()
    if not strict_sha256(expected_stratum_assignment_hash):
        return _unknown_receipt()
    if not strict_sha256(expected_evaluation_hash):
        return _unknown_receipt()
    if evaluation.get("evaluation_hash") != expected_evaluation_hash:
        return _unknown_receipt()

    try:
        verified = verify_strategy_correlation_cross_lag_evaluation(
            evaluation,
            preregistered_strata,
            aligned_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
    except Exception:
        verified = False
    if not verified:
        return _unknown_receipt()

    decision = evaluation["gate_decision"]
    if decision == "PASS":
        report_state = "OBSERVED_PASS"
        gap_state = "NO_PREREGISTERED_CROSS_LAG_DEPENDENCE_OBSERVED"
        blockers: list[str] = []
    elif decision == "BLOCK":
        report_state = "OBSERVED_BLOCK"
        gap_state = "PREREGISTERED_CROSS_LAG_DEPENDENCE_OBSERVED"
        blockers = ["CROSS_LAG_DEPENDENCE_DETECTED"]
    else:
        return _unknown_receipt()

    return _sealed_receipt(
        report_state=report_state,
        source_state="OBSERVED",
        gap_state=gap_state,
        maturity_state="CANDIDATE_EVALUATED_NOT_FORMAL",
        gate_decision=decision,
        gate_reason=evaluation["gate_reason"],
        blockers=blockers,
        source_evaluation_hash=evaluation["evaluation_hash"],
        stratum_assignment_hash=evaluation["stratum_assignment_hash"],
        cross_stratum_pair_count=evaluation["cross_stratum_pair_count"],
        lag_test_count=evaluation["lag_test_count"],
        dependent_test_count=evaluation["dependent_test_count"],
        max_adjusted_absolute_lower=evaluation["max_adjusted_absolute_lower"],
    )


def verify_strategy_correlation_cross_lag_consumer_receipt(
    document: Any,
    evaluation: Any,
    *,
    preregistered_strata: Any,
    aligned_observations: Any,
    expected_stratum_assignment_hash: Any,
    expected_evaluation_hash: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected = consume_strategy_correlation_cross_lag_evaluation(
            evaluation,
            preregistered_strata=preregistered_strata,
            aligned_observations=aligned_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_evaluation_hash=expected_evaluation_hash,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)
