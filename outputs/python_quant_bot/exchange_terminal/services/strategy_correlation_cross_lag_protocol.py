from __future__ import annotations

from typing import Any

from .strategy_correlation_cross_lag_direction_contract import (
    CONTRACT_SCHEMA as DIRECTION_CONTRACT_SCHEMA,
    LAG_DIRECTION_CONVENTION,
)
from .strategy_correlation_cross_lag_gate import (
    EVALUATION_SCHEMA,
    FAMILY_ALPHA,
    LAGS,
    MIN_ADJUSTED_ABSOLUTE_LOWER,
    MIN_EFFECTIVE_SAMPLE,
    MIN_OBSERVATION_COUNT,
    STATIC_FINGERPRINT as GATE_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_evaluation,
)
from .strategy_correlation_cross_lag_preregistration_adapter_binding import (
    BINDING_SCHEMA as PREREGISTRATION_BINDING_SCHEMA,
    STATIC_FINGERPRINT as PREREGISTRATION_BINDING_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_preregistration_adapter_binding,
)
from .strategy_correlation_cross_lag_registry_assignment_adapter import (
    ADAPTER_SCHEMA as REGISTRY_ASSIGNMENT_ADAPTER_SCHEMA,
    MULTIPLICITY_POLICY,
    STATIC_FINGERPRINT as REGISTRY_ASSIGNMENT_ADAPTER_STATIC_FINGERPRINT,
)
from .strategy_correlation_cross_lag_report_consumer import (
    STATIC_FINGERPRINT as CONSUMER_STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA as CONSUMER_VERIFICATION_SCHEMA,
    verify_strategy_correlation_cross_lag_consumer_receipt,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


PROTOCOL_SCHEMA = "strategy-correlation-cross-lag-protocol-registration-candidate-v1"
PROTOCOL_VERIFICATION_SCHEMA = f"{PROTOCOL_SCHEMA}-verification-v1"
STATIC_FINGERPRINT = "20260821-cross-lag-protocol-registration-1"

_VALID_BLOCKERS = [
    "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED",
    "CROSS_LAG_EVALUATION_NOT_BOUND",
]

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


def _facts(value: bool) -> dict[str, bool]:
    return {
        "preregistration_adapter_binding_verified": value,
        "protocol_v5_source_bound": value,
        "registry_assignment_bound": value,
        "direction_contract_bound": value,
        "analytic_policy_bound": value,
    }


def _sealed_registration(
    *,
    registration_state: str,
    source_state: str,
    gap_state: str,
    maturity_state: str,
    facts: dict[str, bool],
    blockers: list[str],
    preregistration_adapter_binding_hash: str = "",
    cluster_preregistration_hash: str = "",
    strata_protocol_registration_hash: str = "",
    registry_assignment_adapter_hash: str = "",
    registry_asset_hash: str = "",
    registry_binding_assessment_hash: str = "",
    stratum_assignment_hash: str = "",
    direction_contract_hash: str = "",
    analytic_policy_hash: str = "",
    classification_effective_date: str = "",
    selection_cutoff_date: str = "",
    frozen_at: str = "",
    first_observation_timestamp: str = "",
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": PROTOCOL_SCHEMA,
            "verification_schema_version": PROTOCOL_VERIFICATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "registration_state": registration_state,
            "source_state": source_state,
            "gap_state": gap_state,
            "maturity_state": maturity_state,
            "permission_state": "LOCKED",
            "preregistration_binding_schema": PREREGISTRATION_BINDING_SCHEMA,
            "preregistration_binding_static_fingerprint": PREREGISTRATION_BINDING_STATIC_FINGERPRINT,
            "preregistration_adapter_binding_hash": preregistration_adapter_binding_hash,
            "cluster_preregistration_hash": cluster_preregistration_hash,
            "strata_protocol_registration_hash": strata_protocol_registration_hash,
            "registry_assignment_adapter_schema": REGISTRY_ASSIGNMENT_ADAPTER_SCHEMA,
            "registry_assignment_adapter_static_fingerprint": REGISTRY_ASSIGNMENT_ADAPTER_STATIC_FINGERPRINT,
            "registry_assignment_adapter_hash": registry_assignment_adapter_hash,
            "registry_asset_hash": registry_asset_hash,
            "registry_binding_assessment_hash": registry_binding_assessment_hash,
            "stratum_assignment_hash": stratum_assignment_hash,
            "direction_contract_schema": DIRECTION_CONTRACT_SCHEMA,
            "direction_contract_hash": direction_contract_hash,
            "lag_direction_convention": LAG_DIRECTION_CONVENTION,
            "source_gate_schema": EVALUATION_SCHEMA,
            "source_gate_static_fingerprint": GATE_STATIC_FINGERPRINT,
            "consumer_schema": CONSUMER_VERIFICATION_SCHEMA,
            "consumer_static_fingerprint": CONSUMER_STATIC_FINGERPRINT,
            "lag_family": list(LAGS),
            "multiplicity_policy": MULTIPLICITY_POLICY,
            "family_alpha": str(FAMILY_ALPHA),
            "minimum_observation_count": MIN_OBSERVATION_COUNT,
            "minimum_effective_sample_size": str(MIN_EFFECTIVE_SAMPLE),
            "minimum_adjusted_absolute_lower": str(MIN_ADJUSTED_ABSOLUTE_LOWER),
            "analytic_policy_hash": analytic_policy_hash,
            "classification_effective_date": classification_effective_date,
            "selection_cutoff_date": selection_cutoff_date,
            "frozen_at": frozen_at,
            "first_observation_timestamp": first_observation_timestamp,
            "facts": dict(facts),
            "blockers": list(blockers),
            "authority": dict(_LOCKED_AUTHORITY),
        },
        "protocol_registration_hash",
    )


def _not_supplied_registration() -> dict[str, Any]:
    return _sealed_registration(
        registration_state="NOT_SUPPLIED",
        source_state="NOT_SUPPLIED",
        gap_state="PREREGISTRATION_ADAPTER_BINDING_NOT_SUPPLIED",
        maturity_state="NOT_EVALUATED",
        facts=_facts(False),
        blockers=["PREREGISTRATION_ADAPTER_BINDING_NOT_SUPPLIED"],
    )


def _unknown_registration() -> dict[str, Any]:
    return _sealed_registration(
        registration_state="UNKNOWN",
        source_state="UNKNOWN",
        gap_state="PREREGISTRATION_ADAPTER_BINDING_INVALID",
        maturity_state="UNKNOWN",
        facts=_facts(False),
        blockers=["PREREGISTRATION_ADAPTER_BINDING_INVALID"],
    )


def build_strategy_correlation_cross_lag_protocol_registration(
    preregistration_adapter_binding: Any,
    *,
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
    expected_preregistration_adapter_binding_hash: Any,
    expected_strata_protocol_registration_hash: Any,
    expected_registry_assignment_adapter_hash: Any,
    expected_direction_contract_hash: Any,
    expected_registry_asset_hash: Any,
    expected_classification_source_hash: Any,
    expected_stratum_assignment_hash: Any,
) -> dict[str, Any]:
    """Build a result-free candidate registration from one replayed P1b chain."""

    if preregistration_adapter_binding is None:
        return _not_supplied_registration()
    if not all(
        isinstance(value, dict)
        for value in (
            preregistration_adapter_binding,
            strata_protocol_registration,
            registry_assignment_adapter,
            direction_contract,
            source_preregistration,
            strata_registration,
            registry_asset,
            registry_binding_assessment,
        )
    ):
        return _unknown_registration()
    if not all(
        strict_sha256(value)
        for value in (
            expected_preregistration_adapter_binding_hash,
            expected_strata_protocol_registration_hash,
            expected_registry_assignment_adapter_hash,
            expected_direction_contract_hash,
            expected_registry_asset_hash,
            expected_classification_source_hash,
            expected_stratum_assignment_hash,
        )
    ):
        return _unknown_registration()
    if preregistration_adapter_binding.get("binding_hash") != expected_preregistration_adapter_binding_hash:
        return _unknown_registration()

    try:
        verified = verify_strategy_correlation_cross_lag_preregistration_adapter_binding(
            preregistration_adapter_binding,
            strata_protocol_registration,
            registry_assignment_adapter,
            direction_contract,
            source_preregistration=source_preregistration,
            strata_registration=strata_registration,
            registry_asset=registry_asset,
            registry_binding_assessment=registry_binding_assessment,
            dimension_id=dimension_id,
            selection_cutoff_date=selection_cutoff_date,
            first_observation_timestamp=first_observation_timestamp,
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
        return _unknown_registration()
    if preregistration_adapter_binding.get("binding_state") != "PREREGISTRATION_ADAPTER_VERIFIED_CANDIDATE":
        return _unknown_registration()
    if preregistration_adapter_binding.get("blockers") != ["CROSS_LAG_C2_PROTOCOL_NOT_IMPLEMENTED"]:
        return _unknown_registration()

    analytic_policy = registry_assignment_adapter.get("analytic_policy")
    if not isinstance(analytic_policy, dict) or not strict_sha256(analytic_policy.get("policy_hash")):
        return _unknown_registration()

    return _sealed_registration(
        registration_state="REGISTERED_CANDIDATE_NOT_SEQUENCE_ATTESTED",
        source_state="OBSERVED",
        gap_state="SEQUENCE_ORDER_NOT_ATTESTED",
        maturity_state="CANDIDATE_PROTOCOL_REGISTERED_NOT_FORMAL",
        facts=_facts(True),
        blockers=_VALID_BLOCKERS,
        preregistration_adapter_binding_hash=preregistration_adapter_binding["binding_hash"],
        cluster_preregistration_hash=preregistration_adapter_binding["cluster_preregistration_hash"],
        strata_protocol_registration_hash=preregistration_adapter_binding["strata_protocol_registration_hash"],
        registry_assignment_adapter_hash=preregistration_adapter_binding["registry_assignment_adapter_hash"],
        registry_asset_hash=preregistration_adapter_binding["registry_asset_hash"],
        registry_binding_assessment_hash=preregistration_adapter_binding["registry_binding_assessment_hash"],
        stratum_assignment_hash=preregistration_adapter_binding["stratum_assignment_hash"],
        direction_contract_hash=preregistration_adapter_binding["direction_contract_hash"],
        analytic_policy_hash=analytic_policy["policy_hash"],
        classification_effective_date=preregistration_adapter_binding["classification_effective_date"],
        selection_cutoff_date=preregistration_adapter_binding["selection_cutoff_date"],
        frozen_at=preregistration_adapter_binding["frozen_at"],
        first_observation_timestamp=preregistration_adapter_binding["first_observation_timestamp"],
    )


def verify_strategy_correlation_cross_lag_protocol_registration(
    document: Any,
    preregistration_adapter_binding: Any,
    *,
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
    expected_preregistration_adapter_binding_hash: Any,
    expected_strata_protocol_registration_hash: Any,
    expected_registry_assignment_adapter_hash: Any,
    expected_direction_contract_hash: Any,
    expected_registry_asset_hash: Any,
    expected_classification_source_hash: Any,
    expected_stratum_assignment_hash: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected = build_strategy_correlation_cross_lag_protocol_registration(
            preregistration_adapter_binding,
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
            expected_preregistration_adapter_binding_hash=expected_preregistration_adapter_binding_hash,
            expected_strata_protocol_registration_hash=expected_strata_protocol_registration_hash,
            expected_registry_assignment_adapter_hash=expected_registry_assignment_adapter_hash,
            expected_direction_contract_hash=expected_direction_contract_hash,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_classification_source_hash=expected_classification_source_hash,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


BINDING_ASSESSMENT_SCHEMA = "strategy-correlation-cross-lag-protocol-binding-candidate-v1"
BINDING_ASSESSMENT_STATIC_FINGERPRINT = "20260821-cross-lag-protocol-binding-1"


def _assessment_facts(value: bool) -> dict[str, bool]:
    return {
        "protocol_registration_verified": value,
        "preregistration_adapter_binding_verified": value,
        "evaluation_verified": value,
        "consumer_receipt_verified": value,
        "assignment_hashes_match": value,
        "evaluation_receipt_hashes_match": value,
        "decision_and_counts_match": value,
        "direction_and_policy_match": value,
    }


def _sealed_assessment(
    *,
    assessment_state: str,
    source_state: str,
    gap_state: str,
    maturity_state: str,
    facts: dict[str, bool],
    blockers: list[str],
    protocol_registration_hash: str = "",
    preregistration_adapter_binding_hash: str = "",
    evaluation_hash: str = "",
    consumer_receipt_hash: str = "",
    cluster_preregistration_hash: str = "",
    strata_protocol_registration_hash: str = "",
    registry_assignment_adapter_hash: str = "",
    registry_asset_hash: str = "",
    registry_binding_assessment_hash: str = "",
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
            "schema_version": BINDING_ASSESSMENT_SCHEMA,
            "static_fingerprint": BINDING_ASSESSMENT_STATIC_FINGERPRINT,
            "assessment_state": assessment_state,
            "source_state": source_state,
            "gap_state": gap_state,
            "maturity_state": maturity_state,
            "permission_state": "LOCKED",
            "protocol_registration_schema": PROTOCOL_SCHEMA,
            "protocol_registration_static_fingerprint": STATIC_FINGERPRINT,
            "protocol_registration_hash": protocol_registration_hash,
            "preregistration_binding_schema": PREREGISTRATION_BINDING_SCHEMA,
            "preregistration_adapter_binding_hash": preregistration_adapter_binding_hash,
            "evaluation_schema": EVALUATION_SCHEMA,
            "evaluation_hash": evaluation_hash,
            "consumer_schema": CONSUMER_VERIFICATION_SCHEMA,
            "consumer_receipt_hash": consumer_receipt_hash,
            "cluster_preregistration_hash": cluster_preregistration_hash,
            "strata_protocol_registration_hash": strata_protocol_registration_hash,
            "registry_assignment_adapter_hash": registry_assignment_adapter_hash,
            "registry_asset_hash": registry_asset_hash,
            "registry_binding_assessment_hash": registry_binding_assessment_hash,
            "stratum_assignment_hash": stratum_assignment_hash,
            "direction_contract_hash": direction_contract_hash,
            "analytic_policy_hash": analytic_policy_hash,
            "gate_decision": gate_decision,
            "gate_reason": gate_reason,
            "cross_stratum_pair_count": cross_stratum_pair_count,
            "lag_test_count": lag_test_count,
            "dependent_test_count": dependent_test_count,
            "max_adjusted_absolute_lower": max_adjusted_absolute_lower,
            "facts": dict(facts),
            "blockers": list(blockers),
            "authority": dict(_LOCKED_AUTHORITY),
        },
        "binding_assessment_hash",
    )


def _not_supplied_assessment() -> dict[str, Any]:
    return _sealed_assessment(
        assessment_state="NOT_SUPPLIED",
        source_state="NOT_SUPPLIED",
        gap_state="CROSS_LAG_PROTOCOL_EVIDENCE_NOT_SUPPLIED",
        maturity_state="NOT_EVALUATED",
        facts=_assessment_facts(False),
        blockers=["CROSS_LAG_PROTOCOL_EVIDENCE_NOT_SUPPLIED"],
    )


def _unknown_assessment() -> dict[str, Any]:
    return _sealed_assessment(
        assessment_state="UNKNOWN",
        source_state="UNKNOWN",
        gap_state="CROSS_LAG_PROTOCOL_EVIDENCE_INVALID",
        maturity_state="UNKNOWN",
        facts=_assessment_facts(False),
        blockers=["CROSS_LAG_PROTOCOL_EVIDENCE_INVALID"],
    )


def assess_strategy_correlation_cross_lag_protocol_binding(
    protocol_registration: Any,
    preregistration_adapter_binding: Any,
    evaluation: Any,
    consumer_receipt: Any,
    *,
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
    """Replay and bind C2 registration, P1b, C0, and C1 without I/O."""

    if all(
        value is None
        for value in (
            protocol_registration,
            preregistration_adapter_binding,
            evaluation,
            consumer_receipt,
        )
    ):
        return _not_supplied_assessment()
    if not all(
        isinstance(value, dict)
        for value in (
            protocol_registration,
            preregistration_adapter_binding,
            evaluation,
            consumer_receipt,
            strata_protocol_registration,
            registry_assignment_adapter,
            direction_contract,
            source_preregistration,
            strata_registration,
            registry_asset,
            registry_binding_assessment,
        )
    ):
        return _unknown_assessment()
    if not all(
        strict_sha256(value)
        for value in (
            expected_protocol_registration_hash,
            expected_preregistration_adapter_binding_hash,
            expected_evaluation_hash,
            expected_consumer_receipt_hash,
            expected_strata_protocol_registration_hash,
            expected_registry_assignment_adapter_hash,
            expected_direction_contract_hash,
            expected_registry_asset_hash,
            expected_classification_source_hash,
            expected_stratum_assignment_hash,
        )
    ):
        return _unknown_assessment()
    if protocol_registration.get("protocol_registration_hash") != expected_protocol_registration_hash:
        return _unknown_assessment()
    if preregistration_adapter_binding.get("binding_hash") != expected_preregistration_adapter_binding_hash:
        return _unknown_assessment()
    if evaluation.get("evaluation_hash") != expected_evaluation_hash:
        return _unknown_assessment()
    if consumer_receipt.get("verification_hash") != expected_consumer_receipt_hash:
        return _unknown_assessment()

    assignment = registry_assignment_adapter.get("stratum_assignment")
    if not isinstance(assignment, dict):
        return _unknown_assessment()
    try:
        registration_verified = verify_strategy_correlation_cross_lag_protocol_registration(
            protocol_registration,
            preregistration_adapter_binding,
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
            expected_preregistration_adapter_binding_hash=expected_preregistration_adapter_binding_hash,
            expected_strata_protocol_registration_hash=expected_strata_protocol_registration_hash,
            expected_registry_assignment_adapter_hash=expected_registry_assignment_adapter_hash,
            expected_direction_contract_hash=expected_direction_contract_hash,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_classification_source_hash=expected_classification_source_hash,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        p1b_verified = verify_strategy_correlation_cross_lag_preregistration_adapter_binding(
            preregistration_adapter_binding,
            strata_protocol_registration,
            registry_assignment_adapter,
            direction_contract,
            source_preregistration=source_preregistration,
            strata_registration=strata_registration,
            registry_asset=registry_asset,
            registry_binding_assessment=registry_binding_assessment,
            dimension_id=dimension_id,
            selection_cutoff_date=selection_cutoff_date,
            first_observation_timestamp=first_observation_timestamp,
            expected_strata_protocol_registration_hash=expected_strata_protocol_registration_hash,
            expected_registry_assignment_adapter_hash=expected_registry_assignment_adapter_hash,
            expected_direction_contract_hash=expected_direction_contract_hash,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_classification_source_hash=expected_classification_source_hash,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        evaluation_verified = verify_strategy_correlation_cross_lag_evaluation(
            evaluation,
            assignment,
            aligned_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        receipt_verified = verify_strategy_correlation_cross_lag_consumer_receipt(
            consumer_receipt,
            evaluation,
            preregistered_strata=assignment,
            aligned_observations=aligned_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_evaluation_hash=expected_evaluation_hash,
        )
    except Exception:
        return _unknown_assessment()
    if not all((registration_verified, p1b_verified, evaluation_verified, receipt_verified)):
        return _unknown_assessment()

    if protocol_registration.get("preregistration_adapter_binding_hash") != preregistration_adapter_binding["binding_hash"]:
        return _unknown_assessment()
    if protocol_registration.get("stratum_assignment_hash") != expected_stratum_assignment_hash:
        return _unknown_assessment()
    if registry_assignment_adapter.get("stratum_assignment_hash") != expected_stratum_assignment_hash:
        return _unknown_assessment()
    if evaluation.get("stratum_assignment_hash") != expected_stratum_assignment_hash:
        return _unknown_assessment()
    if consumer_receipt.get("stratum_assignment_hash") != expected_stratum_assignment_hash:
        return _unknown_assessment()
    if consumer_receipt.get("source_evaluation_hash") != evaluation["evaluation_hash"]:
        return _unknown_assessment()
    if protocol_registration.get("direction_contract_hash") != preregistration_adapter_binding["direction_contract_hash"]:
        return _unknown_assessment()
    if protocol_registration.get("analytic_policy_hash") != preregistration_adapter_binding["analytic_policy_hash"]:
        return _unknown_assessment()

    matched_fields = (
        "gate_decision",
        "gate_reason",
        "cross_stratum_pair_count",
        "lag_test_count",
        "dependent_test_count",
        "max_adjusted_absolute_lower",
    )
    if any(consumer_receipt.get(field) != evaluation.get(field) for field in matched_fields):
        return _unknown_assessment()

    decision = evaluation["gate_decision"]
    if decision == "PASS" and consumer_receipt.get("report_state") == "OBSERVED_PASS":
        assessment_state = "OBSERVED_PASS_CANDIDATE_PROTOCOL"
        gap_state = "C3_PUBLIC_PROJECTION_NOT_IMPLEMENTED"
        blockers = [
            "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED",
            "CROSS_LAG_C3_PUBLIC_PROJECTION_NOT_IMPLEMENTED",
        ]
    elif decision == "BLOCK" and consumer_receipt.get("report_state") == "OBSERVED_BLOCK":
        assessment_state = "OBSERVED_BLOCK_CANDIDATE_PROTOCOL"
        gap_state = "CROSS_LAG_DEPENDENCE_OBSERVED"
        blockers = [
            "CROSS_LAG_DEPENDENCE_DETECTED",
            "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED",
            "CROSS_LAG_C3_PUBLIC_PROJECTION_NOT_IMPLEMENTED",
        ]
    else:
        return _unknown_assessment()

    return _sealed_assessment(
        assessment_state=assessment_state,
        source_state="OBSERVED",
        gap_state=gap_state,
        maturity_state="CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL",
        facts=_assessment_facts(True),
        blockers=blockers,
        protocol_registration_hash=protocol_registration["protocol_registration_hash"],
        preregistration_adapter_binding_hash=preregistration_adapter_binding["binding_hash"],
        evaluation_hash=evaluation["evaluation_hash"],
        consumer_receipt_hash=consumer_receipt["verification_hash"],
        cluster_preregistration_hash=preregistration_adapter_binding["cluster_preregistration_hash"],
        strata_protocol_registration_hash=preregistration_adapter_binding["strata_protocol_registration_hash"],
        registry_assignment_adapter_hash=preregistration_adapter_binding["registry_assignment_adapter_hash"],
        registry_asset_hash=preregistration_adapter_binding["registry_asset_hash"],
        registry_binding_assessment_hash=preregistration_adapter_binding["registry_binding_assessment_hash"],
        stratum_assignment_hash=expected_stratum_assignment_hash,
        direction_contract_hash=preregistration_adapter_binding["direction_contract_hash"],
        analytic_policy_hash=preregistration_adapter_binding["analytic_policy_hash"],
        gate_decision=evaluation["gate_decision"],
        gate_reason=evaluation["gate_reason"],
        cross_stratum_pair_count=evaluation["cross_stratum_pair_count"],
        lag_test_count=evaluation["lag_test_count"],
        dependent_test_count=evaluation["dependent_test_count"],
        max_adjusted_absolute_lower=evaluation["max_adjusted_absolute_lower"],
    )


def verify_strategy_correlation_cross_lag_protocol_binding_assessment(
    document: Any,
    protocol_registration: Any,
    preregistration_adapter_binding: Any,
    evaluation: Any,
    consumer_receipt: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected = assess_strategy_correlation_cross_lag_protocol_binding(
            protocol_registration,
            preregistration_adapter_binding,
            evaluation,
            consumer_receipt,
            **kwargs,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)
