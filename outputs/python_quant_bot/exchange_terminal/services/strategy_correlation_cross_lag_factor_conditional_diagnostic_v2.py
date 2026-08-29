from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic as _evaluate_v1,
    seal_strict_canonical_document,
    strict_json_contract_equal,
    strict_sha256,
    verify_strategy_correlation_cross_lag_factor_conditional_diagnostic as _verify_v1,
)


V1_SCHEMA = "strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v1"
V1_STATIC_FINGERPRINT = "20260822-cross-lag-factor-conditional-diagnostic-1"
DIAGNOSTIC_SCHEMA = "strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v2"
STATIC_FINGERPRINT = "20260822-cross-lag-factor-conditional-diagnostic-2"
REPORT_CONSUMER_SCHEMA = (
    "strategy-correlation-cross-lag-factor-conditional-report-consumer-verification-v1"
)
V1_DYNAMIC_BLOCKER = "F1_REPORT_CONSUMER_NOT_IMPLEMENTED"
STABLE_REPORT_BLOCKER = "FACTOR_CONDITIONAL_REPORT_NOT_ACTIVATED"


def _authority() -> dict[str, bool]:
    return {
        "calibration_receipt_attested": False,
        "candidate_activation_allowed": False,
        "common_factor_causality_proven": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "factor_registration_formal": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "raw_independence_proven": False,
        "residual_independence_proven": False,
        "sequence_timing_attested": False,
    }


def _report_contract() -> dict[str, str]:
    return {
        "activation_state": "UNMOUNTED",
        "schema_version": REPORT_CONSUMER_SCHEMA,
    }


def _unknown() -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "blockers": [
                "F0_V1_SOURCE_INVALID",
                STABLE_REPORT_BLOCKER,
            ],
            "calibration_receipt_hash": None,
            "diagnostic_reason": "F0_V1_SOURCE_INVALID",
            "diagnostic_state": "UNKNOWN",
            "factor_id": None,
            "factor_observations_hash": None,
            "factor_source_hash": None,
            "facts": {
                "calibration_receipt_attested": False,
                "global_two_view_multiplicity_registered": False,
                "raw_block_relaxed": False,
                "raw_c0_verified": False,
                "residual_c0_verified": False,
            },
            "identity_order_hash": None,
            "maturity_state": "UNKNOWN",
            "raw_evaluation": None,
            "registration_hash": None,
            "report_contract": _report_contract(),
            "residual_evaluation": None,
            "residual_input_hash": None,
            "schema_version": DIAGNOSTIC_SCHEMA,
            "source_state": "UNKNOWN",
            "source_v1_diagnostic_hash": None,
            "static_fingerprint": STATIC_FINGERPRINT,
        },
        "diagnostic_hash",
    )


def _project_v1(v1: Any) -> dict[str, Any] | None:
    if type(v1) is not dict:
        return None
    if v1.get("schema_version") != V1_SCHEMA:
        return None
    if v1.get("static_fingerprint") != V1_STATIC_FINGERPRINT:
        return None
    if v1.get("source_state") != "OBSERVED":
        return None
    source_hash = v1.get("diagnostic_hash")
    if not strict_sha256(source_hash):
        return None
    blockers = v1.get("blockers")
    if type(blockers) is not list or any(type(item) is not str for item in blockers):
        return None
    if blockers.count(V1_DYNAMIC_BLOCKER) != 1:
        return None
    if STABLE_REPORT_BLOCKER in blockers:
        return None

    projected = deepcopy(v1)
    projected.pop("diagnostic_hash", None)
    projected["blockers"] = [
        STABLE_REPORT_BLOCKER if item == V1_DYNAMIC_BLOCKER else item
        for item in blockers
    ]
    projected["report_contract"] = _report_contract()
    projected["schema_version"] = DIAGNOSTIC_SCHEMA
    projected["source_v1_diagnostic_hash"] = source_hash
    projected["static_fingerprint"] = STATIC_FINGERPRINT
    return seal_strict_canonical_document(projected, "diagnostic_hash")


def evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2(
    preregistered_strata: Any,
    aligned_observations: Any,
    residualization_registration: Any,
    factor_observations: Any,
    *,
    expected_stratum_assignment_hash: Any,
    expected_registration_hash: Any,
    expected_factor_observations_hash: Any,
) -> dict[str, Any]:
    try:
        v1 = _evaluate_v1(
            preregistered_strata,
            aligned_observations,
            residualization_registration,
            factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_registration_hash=expected_registration_hash,
            expected_factor_observations_hash=expected_factor_observations_hash,
        )
        if not _verify_v1(
            v1,
            preregistered_strata,
            aligned_observations,
            residualization_registration,
            factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_registration_hash=expected_registration_hash,
            expected_factor_observations_hash=expected_factor_observations_hash,
        ):
            return _unknown()
        projected = _project_v1(v1)
        return projected if projected is not None else _unknown()
    except Exception:
        return _unknown()


def verify_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2(
    document: Any,
    preregistered_strata: Any,
    aligned_observations: Any,
    residualization_registration: Any,
    factor_observations: Any,
    *,
    expected_stratum_assignment_hash: Any,
    expected_registration_hash: Any,
    expected_factor_observations_hash: Any,
    expected_diagnostic_hash: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        if not strict_sha256(expected_diagnostic_hash):
            return False
        if document.get("diagnostic_hash") != expected_diagnostic_hash:
            return False
        expected = evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2(
            preregistered_strata,
            aligned_observations,
            residualization_registration,
            factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_registration_hash=expected_registration_hash,
            expected_factor_observations_hash=expected_factor_observations_hash,
        )
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
