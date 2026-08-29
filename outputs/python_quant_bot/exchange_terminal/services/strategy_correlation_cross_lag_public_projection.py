from __future__ import annotations

from typing import Any

from .strategy_correlation_cross_lag_protocol import (
    BINDING_ASSESSMENT_SCHEMA,
    BINDING_ASSESSMENT_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_protocol_binding_assessment,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


PUBLIC_SUMMARY_SCHEMA = "strategy-correlation-cross-lag-public-summary-v1"
PUBLIC_SUMMARY_VERIFICATION_SCHEMA = f"{PUBLIC_SUMMARY_SCHEMA}-verification-v1"
STATIC_FINGERPRINT = "20260821-cross-lag-public-summary-1"

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


def _facts(source_verified: bool) -> dict[str, bool]:
    return {
        "c2_assessment_verified": source_verified,
        "aggregate_projection_only": True,
        "sequence_order_attested": False,
        "formal_preregistration_bound": False,
    }


def _sealed_summary(
    *,
    public_state: str,
    source_axis: str,
    gap_axis: str,
    maturity_axis: str,
    blockers: list[str],
    source_verified: bool,
    c2_assessment_hash: str = "",
    protocol_registration_hash: str = "",
    preregistration_adapter_binding_hash: str = "",
    evaluation_hash: str = "",
    consumer_receipt_hash: str = "",
    stratum_assignment_hash: str = "",
    direction_contract_hash: str = "",
    analytic_policy_hash: str = "",
    gate_decision: str = "UNKNOWN",
    gate_reason: str = "UNKNOWN",
    cross_stratum_pair_count: int = 0,
    lag_test_count: int = 0,
    dependent_test_count: int = 0,
    max_adjusted_absolute_lower: str = "0",
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": PUBLIC_SUMMARY_SCHEMA,
            "verification_schema_version": PUBLIC_SUMMARY_VERIFICATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "public_state": public_state,
            "source_axis": source_axis,
            "gap_axis": gap_axis,
            "maturity_axis": maturity_axis,
            "permission_axis": "LOCKED",
            "c2_assessment_schema": BINDING_ASSESSMENT_SCHEMA,
            "c2_assessment_static_fingerprint": BINDING_ASSESSMENT_STATIC_FINGERPRINT,
            "c2_assessment_hash": c2_assessment_hash,
            "protocol_registration_hash": protocol_registration_hash,
            "preregistration_adapter_binding_hash": preregistration_adapter_binding_hash,
            "evaluation_hash": evaluation_hash,
            "consumer_receipt_hash": consumer_receipt_hash,
            "stratum_assignment_hash": stratum_assignment_hash,
            "direction_contract_hash": direction_contract_hash,
            "analytic_policy_hash": analytic_policy_hash,
            "gate_decision": gate_decision,
            "gate_reason": gate_reason,
            "cross_stratum_pair_count": cross_stratum_pair_count,
            "lag_test_count": lag_test_count,
            "dependent_test_count": dependent_test_count,
            "max_adjusted_absolute_lower": max_adjusted_absolute_lower,
            "facts": _facts(source_verified),
            "blockers": list(blockers),
            "authority": dict(_LOCKED_AUTHORITY),
        },
        "public_summary_hash",
    )


def _not_supplied_summary() -> dict[str, Any]:
    return _sealed_summary(
        public_state="NOT_SUPPLIED",
        source_axis="NOT_SUPPLIED",
        gap_axis="SOURCE_NOT_SUPPLIED",
        maturity_axis="NOT_EVALUATED",
        blockers=["CROSS_LAG_PROTOCOL_EVIDENCE_NOT_SUPPLIED"],
        source_verified=False,
    )


def _unknown_summary() -> dict[str, Any]:
    return _sealed_summary(
        public_state="UNKNOWN",
        source_axis="UNKNOWN",
        gap_axis="SOURCE_INVALID",
        maturity_axis="UNKNOWN",
        blockers=["CROSS_LAG_PROTOCOL_EVIDENCE_INVALID"],
        source_verified=False,
    )


def build_strategy_correlation_cross_lag_public_summary(
    binding_assessment: Any,
    *,
    protocol_registration: Any,
    preregistration_adapter_binding: Any,
    evaluation: Any,
    consumer_receipt: Any,
    strata_protocol_registration: Any,
    registry_assignment_adapter: Any,
    direction_contract: Any,
    source_preregistration: Any,
    strata_registration: Any,
    registry_asset: Any,
    registry_binding_assessment: Any,
    dimension_id: Any,
    selection_cutoff_date: Any,
    first_observation_timestamp: Any,
    aligned_observations: Any,
    expected_binding_assessment_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_preregistration_adapter_binding_hash: Any,
    expected_evaluation_hash: Any,
    expected_consumer_receipt_hash: Any,
    expected_strata_protocol_registration_hash: Any,
    expected_registry_assignment_adapter_hash: Any,
    expected_direction_contract_hash: Any,
    expected_registry_asset_hash: Any,
    expected_classification_source_hash: Any,
    expected_stratum_assignment_hash: Any,
) -> dict[str, Any]:
    """Verify the complete C2 context and emit one aggregate-only summary."""

    if binding_assessment is None:
        return _not_supplied_summary()
    if not isinstance(binding_assessment, dict):
        return _unknown_summary()
    if not strict_sha256(expected_binding_assessment_hash):
        return _unknown_summary()
    if binding_assessment.get("binding_assessment_hash") != expected_binding_assessment_hash:
        return _unknown_summary()

    try:
        verified = verify_strategy_correlation_cross_lag_protocol_binding_assessment(
            binding_assessment,
            protocol_registration,
            preregistration_adapter_binding,
            evaluation,
            consumer_receipt,
            strata_protocol_registration=strata_protocol_registration,
            registry_assignment_adapter=registry_assignment_adapter,
            direction_contract=direction_contract,
            source_preregistration=source_preregistration,
            strata_registration=strata_registration,
            registry_asset=registry_asset,
            registry_binding_assessment=registry_binding_assessment,
            dimension_id=dimension_id,
            selection_cutoff_date=selection_cutoff_date,
            first_observation_timestamp=first_observation_timestamp,
            aligned_observations=aligned_observations,
            expected_protocol_registration_hash=expected_protocol_registration_hash,
            expected_preregistration_adapter_binding_hash=expected_preregistration_adapter_binding_hash,
            expected_evaluation_hash=expected_evaluation_hash,
            expected_consumer_receipt_hash=expected_consumer_receipt_hash,
            expected_strata_protocol_registration_hash=expected_strata_protocol_registration_hash,
            expected_registry_assignment_adapter_hash=expected_registry_assignment_adapter_hash,
            expected_direction_contract_hash=expected_direction_contract_hash,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_classification_source_hash=expected_classification_source_hash,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
    except Exception:
        verified = False
    if not verified:
        return _unknown_summary()

    state = binding_assessment.get("assessment_state")
    if state == "OBSERVED_PASS_CANDIDATE_PROTOCOL":
        public_state = "OBSERVED_PASS"
        gap_axis = "SEQUENCE_ORDER_UNATTESTED"
        blockers = [
            "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED",
            "CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED",
        ]
    elif state == "OBSERVED_BLOCK_CANDIDATE_PROTOCOL":
        public_state = "OBSERVED_BLOCK"
        gap_axis = "CROSS_LAG_DEPENDENCE_OBSERVED"
        blockers = [
            "CROSS_LAG_DEPENDENCE_DETECTED",
            "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED",
            "CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED",
        ]
    else:
        return _unknown_summary()

    return _sealed_summary(
        public_state=public_state,
        source_axis="VERIFIED_C2",
        gap_axis=gap_axis,
        maturity_axis="CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL",
        blockers=blockers,
        source_verified=True,
        c2_assessment_hash=binding_assessment["binding_assessment_hash"],
        protocol_registration_hash=binding_assessment["protocol_registration_hash"],
        preregistration_adapter_binding_hash=binding_assessment["preregistration_adapter_binding_hash"],
        evaluation_hash=binding_assessment["evaluation_hash"],
        consumer_receipt_hash=binding_assessment["consumer_receipt_hash"],
        stratum_assignment_hash=binding_assessment["stratum_assignment_hash"],
        direction_contract_hash=binding_assessment["direction_contract_hash"],
        analytic_policy_hash=binding_assessment["analytic_policy_hash"],
        gate_decision=binding_assessment["gate_decision"],
        gate_reason=binding_assessment["gate_reason"],
        cross_stratum_pair_count=binding_assessment["cross_stratum_pair_count"],
        lag_test_count=binding_assessment["lag_test_count"],
        dependent_test_count=binding_assessment["dependent_test_count"],
        max_adjusted_absolute_lower=binding_assessment["max_adjusted_absolute_lower"],
    )


def verify_strategy_correlation_cross_lag_public_summary(
    document: Any,
    binding_assessment: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected = build_strategy_correlation_cross_lag_public_summary(
            binding_assessment,
            **kwargs,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)
