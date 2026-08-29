from __future__ import annotations

from typing import Any

from .strategy_correlation_cross_lag_direction_contract import (
    CONTRACT_SCHEMA as DIRECTION_CONTRACT_SCHEMA,
    LAG_DIRECTION_CONVENTION,
    verify_strategy_correlation_cross_lag_direction_contract,
)
from .strategy_correlation_cross_lag_registry_assignment_adapter import (
    ADAPTER_SCHEMA as REGISTRY_ASSIGNMENT_ADAPTER_SCHEMA,
    STATIC_FINGERPRINT as REGISTRY_ASSIGNMENT_ADAPTER_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_registry_assignment_adapter,
)
from .strategy_correlation_strata_protocol import (
    REGISTRATION_SCHEMA_VERSION as STRATA_PROTOCOL_SCHEMA,
    REGISTRATION_VERIFICATION_SCHEMA_VERSION as STRATA_PROTOCOL_VERIFICATION_SCHEMA,
    verify_strategy_correlation_strata_protocol_registration,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


BINDING_SCHEMA = "strategy-correlation-cross-lag-preregistration-adapter-binding-candidate-v1"
STATIC_FINGERPRINT = "20260821-cross-lag-preregistration-adapter-binding-1"

_VALID_BLOCKERS = ["CROSS_LAG_C2_PROTOCOL_NOT_IMPLEMENTED"]

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


def _sealed_binding(
    *,
    binding_state: str,
    source_state: str,
    gap_state: str,
    maturity_state: str,
    facts: dict[str, bool],
    blockers: list[str],
    cluster_preregistration_hash: str = "",
    strata_protocol_registration_hash: str = "",
    strata_protocol_source_registration_hash: str = "",
    registry_assignment_adapter_hash: str = "",
    direction_contract_hash: str = "",
    registry_asset_hash: str = "",
    registry_binding_assessment_hash: str = "",
    stratum_assignment_hash: str = "",
    identity_set_hash: str = "",
    identity_count: int = 0,
    stratum_count: int = 0,
    analytic_policy_hash: str = "",
    classification_effective_date: str = "",
    selection_cutoff_date: str = "",
    frozen_at: str = "",
    first_observation_timestamp: str = "",
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": BINDING_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "binding_state": binding_state,
            "source_state": source_state,
            "gap_state": gap_state,
            "maturity_state": maturity_state,
            "permission_state": "LOCKED",
            "strata_protocol_schema": STRATA_PROTOCOL_SCHEMA,
            "strata_protocol_verification_schema": STRATA_PROTOCOL_VERIFICATION_SCHEMA,
            "registry_assignment_adapter_schema": REGISTRY_ASSIGNMENT_ADAPTER_SCHEMA,
            "registry_assignment_adapter_static_fingerprint": REGISTRY_ASSIGNMENT_ADAPTER_STATIC_FINGERPRINT,
            "direction_contract_schema": DIRECTION_CONTRACT_SCHEMA,
            "lag_direction_convention": LAG_DIRECTION_CONVENTION,
            "cluster_preregistration_hash": cluster_preregistration_hash,
            "strata_protocol_registration_hash": strata_protocol_registration_hash,
            "strata_protocol_source_registration_hash": strata_protocol_source_registration_hash,
            "registry_assignment_adapter_hash": registry_assignment_adapter_hash,
            "direction_contract_hash": direction_contract_hash,
            "registry_asset_hash": registry_asset_hash,
            "registry_binding_assessment_hash": registry_binding_assessment_hash,
            "stratum_assignment_hash": stratum_assignment_hash,
            "identity_set_hash": identity_set_hash,
            "identity_count": identity_count,
            "stratum_count": stratum_count,
            "analytic_policy_hash": analytic_policy_hash,
            "classification_effective_date": classification_effective_date,
            "selection_cutoff_date": selection_cutoff_date,
            "frozen_at": frozen_at,
            "first_observation_timestamp": first_observation_timestamp,
            "facts": dict(facts),
            "blockers": list(blockers),
            "authority": dict(_LOCKED_AUTHORITY),
        },
        "binding_hash",
    )


def _empty_facts() -> dict[str, bool]:
    return {
        "strata_protocol_verified": False,
        "protocol_source_matches_registry_source": False,
        "registry_assignment_verified": False,
        "direction_contract_verified": False,
        "direction_contract_bound_to_adapter": False,
        "temporal_order_verified": False,
    }


def _not_supplied_binding() -> dict[str, Any]:
    return _sealed_binding(
        binding_state="NOT_SUPPLIED",
        source_state="NOT_SUPPLIED",
        gap_state="PREREGISTRATION_EVIDENCE_NOT_SUPPLIED",
        maturity_state="NOT_EVALUATED",
        facts=_empty_facts(),
        blockers=["PREREGISTRATION_EVIDENCE_NOT_SUPPLIED"],
    )


def _unknown_binding() -> dict[str, Any]:
    return _sealed_binding(
        binding_state="UNKNOWN",
        source_state="UNKNOWN",
        gap_state="PREREGISTRATION_EVIDENCE_INVALID",
        maturity_state="UNKNOWN",
        facts=_empty_facts(),
        blockers=["PREREGISTRATION_EVIDENCE_INVALID"],
    )


def build_strategy_correlation_cross_lag_preregistration_adapter_binding(
    strata_protocol_registration: Any,
    registry_assignment_adapter: Any,
    direction_contract: Any,
    *,
    source_preregistration: Any,
    strata_registration: Any,
    registry_asset: Any,
    registry_binding_assessment: Any,
    dimension_id: Any,
    selection_cutoff_date: Any,
    first_observation_timestamp: Any,
    expected_strata_protocol_registration_hash: Any,
    expected_registry_assignment_adapter_hash: Any,
    expected_direction_contract_hash: Any,
    expected_registry_asset_hash: Any,
    expected_classification_source_hash: Any,
    expected_stratum_assignment_hash: Any,
) -> dict[str, Any]:
    """Bind one verified protocol-v5 source to one replayed P1a candidate."""

    if all(
        value is None
        for value in (
            strata_protocol_registration,
            registry_assignment_adapter,
            direction_contract,
        )
    ):
        return _not_supplied_binding()
    if not all(
        isinstance(value, dict)
        for value in (
            strata_protocol_registration,
            registry_assignment_adapter,
            direction_contract,
            source_preregistration,
            strata_registration,
            registry_asset,
            registry_binding_assessment,
        )
    ):
        return _unknown_binding()
    if not all(
        strict_sha256(value)
        for value in (
            expected_strata_protocol_registration_hash,
            expected_registry_assignment_adapter_hash,
            expected_direction_contract_hash,
            expected_registry_asset_hash,
            expected_classification_source_hash,
            expected_stratum_assignment_hash,
        )
    ):
        return _unknown_binding()
    if strata_protocol_registration.get("registration_hash") != expected_strata_protocol_registration_hash:
        return _unknown_binding()
    if registry_assignment_adapter.get("adapter_hash") != expected_registry_assignment_adapter_hash:
        return _unknown_binding()
    if direction_contract.get("contract_hash") != expected_direction_contract_hash:
        return _unknown_binding()

    try:
        protocol_verification = verify_strategy_correlation_strata_protocol_registration(
            strata_protocol_registration
        )
        adapter_verified = verify_strategy_correlation_cross_lag_registry_assignment_adapter(
            registry_assignment_adapter,
            registry_asset,
            registry_binding_assessment,
            source_preregistration=source_preregistration,
            strata_registration=strata_registration,
            dimension_id=dimension_id,
            selection_cutoff_date=selection_cutoff_date,
            first_observation_timestamp=first_observation_timestamp,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_classification_source_hash=expected_classification_source_hash,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        direction_verified = verify_strategy_correlation_cross_lag_direction_contract(
            direction_contract
        )
    except Exception:
        return _unknown_binding()
    if protocol_verification.get("status") != "PASS" or not adapter_verified or not direction_verified:
        return _unknown_binding()

    source_hash = source_preregistration.get("preregistration_hash")
    if not strict_sha256(source_hash):
        return _unknown_binding()
    if strata_protocol_registration.get("cluster_preregistration_hash") != source_hash:
        return _unknown_binding()
    if registry_assignment_adapter.get("source_preregistration_hash") != source_hash:
        return _unknown_binding()
    analytic_policy = registry_assignment_adapter.get("analytic_policy")
    if not isinstance(analytic_policy, dict):
        return _unknown_binding()
    if analytic_policy.get("lag_direction_contract_hash") != direction_contract["contract_hash"]:
        return _unknown_binding()
    if analytic_policy.get("lag_direction_convention") != direction_contract["lag_direction_convention"]:
        return _unknown_binding()
    if registry_assignment_adapter.get("adapter_state") != "REGISTRY_ASSIGNMENT_VERIFIED_CANDIDATE":
        return _unknown_binding()
    if registry_assignment_adapter.get("blockers") != ["CROSS_LAG_PROTOCOL_REGISTRATION_UNBOUND"]:
        return _unknown_binding()

    facts = {
        "strata_protocol_verified": True,
        "protocol_source_matches_registry_source": True,
        "registry_assignment_verified": True,
        "direction_contract_verified": True,
        "direction_contract_bound_to_adapter": True,
        "temporal_order_verified": True,
    }
    return _sealed_binding(
        binding_state="PREREGISTRATION_ADAPTER_VERIFIED_CANDIDATE",
        source_state="OBSERVED",
        gap_state="C2_PROTOCOL_NOT_IMPLEMENTED",
        maturity_state="CANDIDATE_PROTOCOL_AND_REGISTRY_BOUND_NOT_FORMAL",
        facts=facts,
        blockers=_VALID_BLOCKERS,
        cluster_preregistration_hash=source_hash,
        strata_protocol_registration_hash=strata_protocol_registration["registration_hash"],
        strata_protocol_source_registration_hash=strata_protocol_registration["source_registration_hash"],
        registry_assignment_adapter_hash=registry_assignment_adapter["adapter_hash"],
        direction_contract_hash=direction_contract["contract_hash"],
        registry_asset_hash=registry_assignment_adapter["registry_asset_hash"],
        registry_binding_assessment_hash=registry_assignment_adapter["registry_binding_assessment_hash"],
        stratum_assignment_hash=registry_assignment_adapter["stratum_assignment_hash"],
        identity_set_hash=registry_assignment_adapter["identity_set_hash"],
        identity_count=registry_assignment_adapter["identity_count"],
        stratum_count=registry_assignment_adapter["stratum_count"],
        analytic_policy_hash=analytic_policy["policy_hash"],
        classification_effective_date=registry_assignment_adapter["classification_effective_date"],
        selection_cutoff_date=registry_assignment_adapter["selection_cutoff_date"],
        frozen_at=registry_assignment_adapter["frozen_at"],
        first_observation_timestamp=registry_assignment_adapter["first_observation_timestamp"],
    )


def verify_strategy_correlation_cross_lag_preregistration_adapter_binding(
    document: Any,
    strata_protocol_registration: Any,
    registry_assignment_adapter: Any,
    direction_contract: Any,
    *,
    source_preregistration: Any,
    strata_registration: Any,
    registry_asset: Any,
    registry_binding_assessment: Any,
    dimension_id: Any,
    selection_cutoff_date: Any,
    first_observation_timestamp: Any,
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
        expected = build_strategy_correlation_cross_lag_preregistration_adapter_binding(
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
        return False
    return strict_json_contract_equal(document, expected)
