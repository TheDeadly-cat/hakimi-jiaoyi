from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..services.strict_canonical_json_hash import strict_json_contract_equal
from ..services.strict_governance_primitives import strict_native_true, strict_sha256
from ..services.strategy_correlation_cross_lag_public_projection import (
    PUBLIC_SUMMARY_SCHEMA,
    PUBLIC_SUMMARY_VERIFICATION_SCHEMA,
    STATIC_FINGERPRINT as PUBLIC_SUMMARY_STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_public_summary,
    verify_strategy_correlation_cross_lag_public_summary,
)


ENVELOPE_SCHEMA_VERSION = "strategy-correlation-cross-lag-presentation-envelope-v1"
ADAPTER_STATIC_FINGERPRINT = "20260821-cross-lag-c5-presentation-envelope-adapter-1"


def _context(
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
    return {
        "protocol_registration": protocol_registration,
        "preregistration_adapter_binding": preregistration_adapter_binding,
        "evaluation": evaluation,
        "consumer_receipt": consumer_receipt,
        "strata_protocol_registration": strata_protocol_registration,
        "registry_assignment_adapter": registry_assignment_adapter,
        "direction_contract": direction_contract,
        "source_preregistration": source_preregistration,
        "strata_registration": strata_registration,
        "registry_asset": registry_asset,
        "registry_binding_assessment": registry_binding_assessment,
        "dimension_id": dimension_id,
        "selection_cutoff_date": selection_cutoff_date,
        "first_observation_timestamp": first_observation_timestamp,
        "aligned_observations": aligned_observations,
        "expected_binding_assessment_hash": expected_binding_assessment_hash,
        "expected_protocol_registration_hash": expected_protocol_registration_hash,
        "expected_preregistration_adapter_binding_hash": expected_preregistration_adapter_binding_hash,
        "expected_evaluation_hash": expected_evaluation_hash,
        "expected_consumer_receipt_hash": expected_consumer_receipt_hash,
        "expected_strata_protocol_registration_hash": expected_strata_protocol_registration_hash,
        "expected_registry_assignment_adapter_hash": expected_registry_assignment_adapter_hash,
        "expected_direction_contract_hash": expected_direction_contract_hash,
        "expected_registry_asset_hash": expected_registry_asset_hash,
        "expected_classification_source_hash": expected_classification_source_hash,
        "expected_stratum_assignment_hash": expected_stratum_assignment_hash,
    }


def build_strategy_correlation_cross_lag_presentation_envelope(
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
) -> dict[str, Any] | None:
    try:
        context = _context(
            protocol_registration=protocol_registration,
            preregistration_adapter_binding=preregistration_adapter_binding,
            evaluation=evaluation,
            consumer_receipt=consumer_receipt,
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
            expected_binding_assessment_hash=expected_binding_assessment_hash,
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
        summary = build_strategy_correlation_cross_lag_public_summary(
            binding_assessment,
            **context,
        )
        if type(summary) is not dict:
            return None
        if (
            summary.get("schema_version") != PUBLIC_SUMMARY_SCHEMA
            or summary.get("verification_schema_version")
            != PUBLIC_SUMMARY_VERIFICATION_SCHEMA
            or summary.get("static_fingerprint")
            != PUBLIC_SUMMARY_STATIC_FINGERPRINT
        ):
            return None
        verified = verify_strategy_correlation_cross_lag_public_summary(
            summary,
            binding_assessment,
            **context,
        )
        if not strict_native_true(verified):
            return None
        public_summary_hash = summary.get("public_summary_hash")
        if not strict_sha256(public_summary_hash):
            return None
        summary_copy = deepcopy(summary)
        if type(summary_copy) is not dict:
            return None
        if not strict_json_contract_equal(summary_copy, summary):
            return None
        return {
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "summary": summary_copy,
            "verification": {
                "schema_version": PUBLIC_SUMMARY_VERIFICATION_SCHEMA,
                "valid": True,
                "supplied_public_summary_hash": public_summary_hash,
                "rebuilt_public_summary_hash": public_summary_hash,
            },
        }
    except Exception:
        return None


def verify_strategy_correlation_cross_lag_presentation_envelope(
    document: Any,
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
) -> bool:
    try:
        expected = build_strategy_correlation_cross_lag_presentation_envelope(
            binding_assessment,
            protocol_registration=protocol_registration,
            preregistration_adapter_binding=preregistration_adapter_binding,
            evaluation=evaluation,
            consumer_receipt=consumer_receipt,
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
            expected_binding_assessment_hash=expected_binding_assessment_hash,
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
        if expected is None:
            return False
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
