from __future__ import annotations

from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3 import (
    GATE_SCHEMA as PRECOMMIT_GATE_V3_SCHEMA,
    STATIC_FINGERPRINT as PRECOMMIT_GATE_V3_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate import (
    GATE_SCHEMA as RESIDUAL_ORDER_GATE_SCHEMA,
    STATIC_FINGERPRINT as RESIDUAL_ORDER_GATE_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)


GATE_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v4"
)
STATIC_FINGERPRINT = "20260831-cross-lag-factor-calibration-precommit-gate-4"


def _authority() -> dict[str, bool]:
    return {
        "beta_temporal_stability_proven": False,
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_precommit_timing_attested": False,
        "formal_residualization_registration_v2_issued": False,
        "future_evaluation_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "residual_energy_temporal_stability_proven": False,
        "residual_order_independence_proven": False,
    }


def _unknown_facts() -> dict[str, bool]:
    return {
        "beta_stability_threshold_passed": False,
        "beta_temporal_stability_proven": False,
        "cross_gate_source_hashes_bound": False,
        "external_time_anchor_verified": False,
        "future_evaluation_activated": False,
        "local_precommit_binding_complete": False,
        "precommit_gate_v3_verified": False,
        "residual_energy_temporal_stability_proven": False,
        "residual_energy_threshold_passed": False,
        "residual_order_gate_verified": False,
        "residual_order_independence_proven": False,
        "residual_order_threshold_passed": False,
        "source_gate_block_relaxed": False,
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "gate_hash")


def _unknown(reason: str, source_state: str) -> dict[str, Any]:
    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": source_state,
            "gate_decision": "UNKNOWN",
            "gate_reason": reason,
            "source_precommit_gate_v3_decision": None,
            "source_residual_order_gate_decision": None,
            "protocol_id": None,
            "future_evaluation_id": None,
            "precommit_declared_at_utc": None,
            "evaluation_not_before_date": None,
            "external_time_anchor_reference_hash": None,
            "fold_count": None,
            "maximum_allowed_absolute_lag_one_residual_energy_coupling": None,
            "maximum_observed_absolute_lag_one_residual_energy_coupling": None,
            "residual_order_unstable_identity_count": None,
            "zero_lag_energy_identity_fold_count": None,
            "source_precommit_gate_v3_hash": None,
            "source_residual_order_gate_hash": None,
            "source_residual_energy_gate_hash": None,
            "source_beta_stability_gate_hash": None,
            "source_replay_hash": None,
            "source_registration_hash": None,
            "source_calibration_observations_hash": None,
            "facts": _unknown_facts(),
            "blockers": [reason],
            "authority": _authority(),
        }
    )


def _combined_blockers(*groups: list[str]) -> list[str]:
    output: list[str] = []
    for group in groups:
        for blocker in group:
            if blocker not in output:
                output.append(blocker)
    return output


def _observed(
    precommit_gate_v3: dict[str, Any], residual_order_gate: dict[str, Any]
) -> dict[str, Any]:
    precommit_decision = precommit_gate_v3["gate_decision"]
    residual_order_decision = residual_order_gate["gate_decision"]
    if precommit_decision == "BLOCK":
        decision = "BLOCK"
        reason = "SOURCE_PRECOMMIT_GATE_V3_BLOCKED"
    elif residual_order_decision == "BLOCK":
        decision = "BLOCK"
        reason = "RESIDUAL_ORDER_STABILITY_GATE_BLOCKED"
    elif (
        precommit_decision == "BOUND_LOCAL_ONLY_DUAL_STABILITY_GUARDED"
        and residual_order_decision == "RESIDUAL_ORDER_STABLE_CANDIDATE"
    ):
        decision = "BOUND_LOCAL_ONLY_TRIPLE_STABILITY_GUARDED"
        reason = "LOCAL_PRECOMMIT_BETA_RESIDUAL_ENERGY_AND_ORDER_GUARDS_BOUND"
    else:
        return _unknown("SOURCE_GATE_NOT_OBSERVED_FOR_V4", "UNKNOWN")

    blockers = _combined_blockers(
        precommit_gate_v3["blockers"], residual_order_gate["blockers"]
    )
    if decision == "BLOCK" and reason not in blockers:
        blockers.append(reason)
    if "PRECOMMIT_GATE_V4_NOT_ACTIVATED" not in blockers:
        blockers.append("PRECOMMIT_GATE_V4_NOT_ACTIVATED")
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("PRECOMMIT_GATE_V4_INTERNAL_AUTHORITY_INVALID", "INVALID")

    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": decision,
            "gate_reason": reason,
            "source_precommit_gate_v3_decision": precommit_decision,
            "source_residual_order_gate_decision": residual_order_decision,
            "protocol_id": precommit_gate_v3["protocol_id"],
            "future_evaluation_id": precommit_gate_v3["future_evaluation_id"],
            "precommit_declared_at_utc": precommit_gate_v3[
                "precommit_declared_at_utc"
            ],
            "evaluation_not_before_date": precommit_gate_v3[
                "evaluation_not_before_date"
            ],
            "external_time_anchor_reference_hash": precommit_gate_v3[
                "external_time_anchor_reference_hash"
            ],
            "fold_count": precommit_gate_v3["fold_count"],
            "maximum_allowed_absolute_lag_one_residual_energy_coupling": residual_order_gate[
                "maximum_allowed_absolute_lag_one_residual_energy_coupling"
            ],
            "maximum_observed_absolute_lag_one_residual_energy_coupling": residual_order_gate[
                "maximum_observed_absolute_lag_one_residual_energy_coupling"
            ],
            "residual_order_unstable_identity_count": residual_order_gate[
                "unstable_identity_count"
            ],
            "zero_lag_energy_identity_fold_count": residual_order_gate[
                "zero_lag_energy_identity_fold_count"
            ],
            "source_precommit_gate_v3_hash": precommit_gate_v3["gate_hash"],
            "source_residual_order_gate_hash": residual_order_gate["gate_hash"],
            "source_residual_energy_gate_hash": precommit_gate_v3[
                "source_residual_energy_gate_hash"
            ],
            "source_beta_stability_gate_hash": precommit_gate_v3[
                "source_beta_stability_gate_hash"
            ],
            "source_replay_hash": precommit_gate_v3["source_replay_hash"],
            "source_registration_hash": precommit_gate_v3[
                "source_registration_hash"
            ],
            "source_calibration_observations_hash": precommit_gate_v3[
                "source_calibration_observations_hash"
            ],
            "facts": {
                "beta_stability_threshold_passed": precommit_gate_v3["facts"][
                    "beta_stability_threshold_passed"
                ],
                "beta_temporal_stability_proven": False,
                "cross_gate_source_hashes_bound": True,
                "external_time_anchor_verified": False,
                "future_evaluation_activated": False,
                "local_precommit_binding_complete": precommit_gate_v3["facts"][
                    "local_precommit_binding_complete"
                ],
                "precommit_gate_v3_verified": True,
                "residual_energy_temporal_stability_proven": False,
                "residual_energy_threshold_passed": precommit_gate_v3["facts"][
                    "residual_energy_threshold_passed"
                ],
                "residual_order_gate_verified": True,
                "residual_order_independence_proven": False,
                "residual_order_threshold_passed": residual_order_gate["facts"][
                    "residual_order_threshold_passed"
                ],
                "source_gate_block_relaxed": False,
            },
            "blockers": blockers,
            "authority": authority,
        }
    )


def evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4(
    precommit_gate_v3: Any,
    residual_order_gate: Any,
    precommit_gate_v2: Any,
    residual_energy_gate: Any,
    precommit_gate_v1: Any,
    beta_stability_gate: Any,
    precommit_declaration: Any,
    report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_precommit_gate_v3_hash: Any,
    expected_residual_order_gate_hash: Any,
    expected_precommit_gate_v2_hash: Any,
    expected_residual_energy_gate_hash: Any,
    expected_precommit_gate_v1_hash: Any,
    expected_beta_stability_gate_hash: Any,
    expected_declaration_hash: Any,
    expected_report_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> dict[str, Any]:
    try:
        if precommit_gate_v3 is None or residual_order_gate is None:
            missing = (
                "PRECOMMIT_GATE_V3_MISSING"
                if precommit_gate_v3 is None
                else "RESIDUAL_ORDER_STABILITY_GATE_MISSING"
            )
            expected = (
                expected_precommit_gate_v3_hash
                if precommit_gate_v3 is None
                else expected_residual_order_gate_hash
            )
            if type(expected) is not str or expected != "":
                return _unknown("SOURCE_GATE_INVALID_FOR_V4", "INVALID")
            return _unknown(missing, "MISSING")
        if type(precommit_gate_v3) is not dict or type(residual_order_gate) is not dict:
            return _unknown("SOURCE_GATE_INVALID_FOR_V4", "INVALID")
        if (
            precommit_gate_v3.get("schema_version") != PRECOMMIT_GATE_V3_SCHEMA
            or precommit_gate_v3.get("static_fingerprint")
            != PRECOMMIT_GATE_V3_STATIC_FINGERPRINT
        ):
            return _unknown("PRECOMMIT_GATE_V3_UNSUPPORTED", "UNSUPPORTED")
        if (
            residual_order_gate.get("schema_version") != RESIDUAL_ORDER_GATE_SCHEMA
            or residual_order_gate.get("static_fingerprint")
            != RESIDUAL_ORDER_GATE_STATIC_FINGERPRINT
        ):
            return _unknown("RESIDUAL_ORDER_GATE_UNSUPPORTED", "UNSUPPORTED")
        if (
            not strict_sha256(expected_precommit_gate_v3_hash)
            or not strict_sha256(expected_residual_order_gate_hash)
            or precommit_gate_v3.get("gate_hash") != expected_precommit_gate_v3_hash
            or residual_order_gate.get("gate_hash")
            != expected_residual_order_gate_hash
        ):
            return _unknown("SOURCE_GATE_INVALID_FOR_V4", "INVALID")

        precommit_verified = verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3(
            precommit_gate_v3,
            precommit_gate_v2,
            residual_energy_gate,
            precommit_gate_v1,
            beta_stability_gate,
            precommit_declaration,
            report,
            replay,
            residualization_registration,
            calibration_observations,
            expected_precommit_gate_v2_hash=expected_precommit_gate_v2_hash,
            expected_residual_energy_gate_hash=expected_residual_energy_gate_hash,
            expected_precommit_gate_v1_hash=expected_precommit_gate_v1_hash,
            expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
            expected_declaration_hash=expected_declaration_hash,
            expected_report_hash=expected_report_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        residual_order_verified = verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate(
            residual_order_gate,
            beta_stability_gate,
            replay,
            residualization_registration,
            calibration_observations,
            expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        if precommit_verified is not True or residual_order_verified is not True:
            return _unknown("SOURCE_GATE_INVALID_FOR_V4", "INVALID")
        if (
            precommit_gate_v3["source_beta_stability_gate_hash"]
            != residual_order_gate["source_beta_stability_gate_hash"]
            or precommit_gate_v3["source_replay_hash"]
            != residual_order_gate["source_replay_hash"]
            or precommit_gate_v3["source_registration_hash"]
            != residual_order_gate["source_registration_hash"]
            or precommit_gate_v3["source_calibration_observations_hash"]
            != residual_order_gate["source_calibration_observations_hash"]
            or precommit_gate_v3["fold_count"] != residual_order_gate["fold_count"]
        ):
            return _unknown("CROSS_GATE_SOURCE_HASH_MISMATCH", "INVALID")
        return _observed(precommit_gate_v3, residual_order_gate)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return _unknown("SOURCE_GATE_INVALID_FOR_V4", "INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4(
    document: Any,
    precommit_gate_v3: Any,
    residual_order_gate: Any,
    precommit_gate_v2: Any,
    residual_energy_gate: Any,
    precommit_gate_v1: Any,
    beta_stability_gate: Any,
    precommit_declaration: Any,
    report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_precommit_gate_v3_hash: Any,
    expected_residual_order_gate_hash: Any,
    expected_precommit_gate_v2_hash: Any,
    expected_residual_energy_gate_hash: Any,
    expected_precommit_gate_v1_hash: Any,
    expected_beta_stability_gate_hash: Any,
    expected_declaration_hash: Any,
    expected_report_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    try:
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4(
            precommit_gate_v3,
            residual_order_gate,
            precommit_gate_v2,
            residual_energy_gate,
            precommit_gate_v1,
            beta_stability_gate,
            precommit_declaration,
            report,
            replay,
            residualization_registration,
            calibration_observations,
            expected_precommit_gate_v3_hash=expected_precommit_gate_v3_hash,
            expected_residual_order_gate_hash=expected_residual_order_gate_hash,
            expected_precommit_gate_v2_hash=expected_precommit_gate_v2_hash,
            expected_residual_energy_gate_hash=expected_residual_energy_gate_hash,
            expected_precommit_gate_v1_hash=expected_precommit_gate_v1_hash,
            expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
            expected_declaration_hash=expected_declaration_hash,
            expected_report_hash=expected_report_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        return strict_json_contract_equal(document, rebuilt)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return False
