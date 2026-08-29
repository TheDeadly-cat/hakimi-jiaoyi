from __future__ import annotations

from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2 import (
    GATE_SCHEMA as PRECOMMIT_GATE_V2_SCHEMA,
    STATIC_FINGERPRINT as PRECOMMIT_GATE_V2_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate import (
    GATE_SCHEMA as RESIDUAL_ENERGY_GATE_SCHEMA,
    STATIC_FINGERPRINT as RESIDUAL_ENERGY_GATE_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate,
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
    "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v3"
)
STATIC_FINGERPRINT = "20260829-cross-lag-factor-calibration-precommit-gate-3"


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
    }


def _unknown_facts() -> dict[str, bool]:
    return {
        "beta_stability_threshold_passed": False,
        "beta_temporal_stability_proven": False,
        "cross_gate_source_hashes_bound": False,
        "external_time_anchor_verified": False,
        "formal_residualization_registration_v2_issued": False,
        "future_evaluation_activated": False,
        "local_precommit_binding_complete": False,
        "precommit_gate_v2_verified": False,
        "residual_energy_gate_verified": False,
        "residual_energy_temporal_stability_proven": False,
        "residual_energy_threshold_passed": False,
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
            "source_precommit_gate_v2_decision": None,
            "source_residual_energy_gate_decision": None,
            "protocol_id": None,
            "future_evaluation_id": None,
            "precommit_declared_at_utc": None,
            "evaluation_not_before_date": None,
            "external_time_anchor_reference_hash": None,
            "fold_count": None,
            "maximum_allowed_normalized_beta_drift": None,
            "maximum_observed_normalized_beta_drift": None,
            "beta_unstable_identity_count": None,
            "sign_reversal_count": None,
            "unidentified_fold_count": None,
            "maximum_allowed_normalized_residual_energy_dispersion": None,
            "maximum_observed_normalized_residual_energy_dispersion": None,
            "residual_energy_unstable_identity_count": None,
            "zero_residual_identity_count": None,
            "source_precommit_gate_v2_hash": None,
            "source_residual_energy_gate_hash": None,
            "source_precommit_gate_v1_hash": None,
            "source_beta_stability_gate_hash": None,
            "source_declaration_hash": None,
            "source_report_hash": None,
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
    precommit_gate_v2: dict[str, Any],
    residual_energy_gate: dict[str, Any],
) -> dict[str, Any]:
    precommit_decision = precommit_gate_v2["gate_decision"]
    residual_decision = residual_energy_gate["gate_decision"]
    if (
        precommit_decision == "BOUND_LOCAL_ONLY_STABILITY_GUARDED"
        and residual_decision == "RESIDUAL_ENERGY_STABLE_CANDIDATE"
    ):
        decision = "BOUND_LOCAL_ONLY_DUAL_STABILITY_GUARDED"
        reason = "LOCAL_PRECOMMIT_BETA_AND_RESIDUAL_ENERGY_GUARDS_BOUND"
    elif precommit_decision == "BLOCK":
        decision = "BLOCK"
        reason = "SOURCE_PRECOMMIT_GATE_V2_BLOCKED"
    elif residual_decision == "BLOCK":
        decision = "BLOCK"
        reason = "RESIDUAL_ENERGY_STABILITY_GATE_BLOCKED"
    else:
        return _unknown("SOURCE_GATE_NOT_OBSERVED_FOR_V3", "UNKNOWN")

    blockers = _combined_blockers(
        precommit_gate_v2["blockers"], residual_energy_gate["blockers"]
    )
    if decision == "BLOCK" and reason not in blockers:
        blockers.append(reason)
    if "PRECOMMIT_GATE_V3_NOT_ACTIVATED" not in blockers:
        blockers.append("PRECOMMIT_GATE_V3_NOT_ACTIVATED")
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("PRECOMMIT_GATE_V3_INTERNAL_AUTHORITY_INVALID", "INVALID")

    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": decision,
            "gate_reason": reason,
            "source_precommit_gate_v2_decision": precommit_decision,
            "source_residual_energy_gate_decision": residual_decision,
            "protocol_id": precommit_gate_v2["protocol_id"],
            "future_evaluation_id": precommit_gate_v2["future_evaluation_id"],
            "precommit_declared_at_utc": precommit_gate_v2[
                "precommit_declared_at_utc"
            ],
            "evaluation_not_before_date": precommit_gate_v2[
                "evaluation_not_before_date"
            ],
            "external_time_anchor_reference_hash": precommit_gate_v2[
                "external_time_anchor_reference_hash"
            ],
            "fold_count": precommit_gate_v2["fold_count"],
            "maximum_allowed_normalized_beta_drift": precommit_gate_v2[
                "maximum_allowed_normalized_beta_drift"
            ],
            "maximum_observed_normalized_beta_drift": precommit_gate_v2[
                "maximum_observed_normalized_beta_drift"
            ],
            "beta_unstable_identity_count": precommit_gate_v2[
                "unstable_identity_count"
            ],
            "sign_reversal_count": precommit_gate_v2["sign_reversal_count"],
            "unidentified_fold_count": precommit_gate_v2[
                "unidentified_fold_count"
            ],
            "maximum_allowed_normalized_residual_energy_dispersion": residual_energy_gate[
                "maximum_allowed_normalized_residual_energy_dispersion"
            ],
            "maximum_observed_normalized_residual_energy_dispersion": residual_energy_gate[
                "maximum_observed_normalized_residual_energy_dispersion"
            ],
            "residual_energy_unstable_identity_count": residual_energy_gate[
                "unstable_identity_count"
            ],
            "zero_residual_identity_count": residual_energy_gate[
                "zero_residual_identity_count"
            ],
            "source_precommit_gate_v2_hash": precommit_gate_v2["gate_hash"],
            "source_residual_energy_gate_hash": residual_energy_gate["gate_hash"],
            "source_precommit_gate_v1_hash": precommit_gate_v2[
                "source_precommit_gate_v1_hash"
            ],
            "source_beta_stability_gate_hash": precommit_gate_v2[
                "source_stability_gate_hash"
            ],
            "source_declaration_hash": precommit_gate_v2[
                "source_declaration_hash"
            ],
            "source_report_hash": precommit_gate_v2["source_report_hash"],
            "source_replay_hash": precommit_gate_v2["source_replay_hash"],
            "source_registration_hash": precommit_gate_v2[
                "source_registration_hash"
            ],
            "source_calibration_observations_hash": precommit_gate_v2[
                "source_calibration_observations_hash"
            ],
            "facts": {
                "beta_stability_threshold_passed": precommit_gate_v2["facts"][
                    "beta_stability_threshold_passed"
                ],
                "beta_temporal_stability_proven": False,
                "cross_gate_source_hashes_bound": True,
                "external_time_anchor_verified": False,
                "formal_residualization_registration_v2_issued": False,
                "future_evaluation_activated": False,
                "local_precommit_binding_complete": precommit_gate_v2["facts"][
                    "local_precommit_binding_complete"
                ],
                "precommit_gate_v2_verified": True,
                "residual_energy_gate_verified": True,
                "residual_energy_temporal_stability_proven": False,
                "residual_energy_threshold_passed": residual_energy_gate["facts"][
                    "residual_energy_threshold_passed"
                ],
                "source_gate_block_relaxed": False,
            },
            "blockers": blockers,
            "authority": authority,
        }
    )


def evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3(
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
        if precommit_gate_v2 is None or residual_energy_gate is None:
            missing = (
                "PRECOMMIT_GATE_V2_MISSING"
                if precommit_gate_v2 is None
                else "RESIDUAL_ENERGY_STABILITY_GATE_MISSING"
            )
            expected = (
                expected_precommit_gate_v2_hash
                if precommit_gate_v2 is None
                else expected_residual_energy_gate_hash
            )
            if type(expected) is not str or expected != "":
                return _unknown("SOURCE_GATE_INVALID_FOR_V3", "INVALID")
            return _unknown(missing, "MISSING")
        if type(precommit_gate_v2) is not dict or type(residual_energy_gate) is not dict:
            return _unknown("SOURCE_GATE_INVALID_FOR_V3", "INVALID")
        if (
            precommit_gate_v2.get("schema_version") != PRECOMMIT_GATE_V2_SCHEMA
            or precommit_gate_v2.get("static_fingerprint")
            != PRECOMMIT_GATE_V2_STATIC_FINGERPRINT
        ):
            return _unknown("PRECOMMIT_GATE_V2_UNSUPPORTED", "UNSUPPORTED")
        if (
            residual_energy_gate.get("schema_version")
            != RESIDUAL_ENERGY_GATE_SCHEMA
            or residual_energy_gate.get("static_fingerprint")
            != RESIDUAL_ENERGY_GATE_STATIC_FINGERPRINT
        ):
            return _unknown("RESIDUAL_ENERGY_GATE_UNSUPPORTED", "UNSUPPORTED")
        if (
            not strict_sha256(expected_precommit_gate_v2_hash)
            or not strict_sha256(expected_residual_energy_gate_hash)
            or precommit_gate_v2.get("gate_hash") != expected_precommit_gate_v2_hash
            or residual_energy_gate.get("gate_hash")
            != expected_residual_energy_gate_hash
        ):
            return _unknown("SOURCE_GATE_INVALID_FOR_V3", "INVALID")

        precommit_verified = verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2(
            precommit_gate_v2,
            precommit_gate_v1,
            beta_stability_gate,
            precommit_declaration,
            report,
            replay,
            residualization_registration,
            calibration_observations,
            expected_precommit_gate_v1_hash=expected_precommit_gate_v1_hash,
            expected_stability_gate_hash=expected_beta_stability_gate_hash,
            expected_declaration_hash=expected_declaration_hash,
            expected_report_hash=expected_report_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        residual_verified = verify_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate(
            residual_energy_gate,
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
        if precommit_verified is not True or residual_verified is not True:
            return _unknown("SOURCE_GATE_INVALID_FOR_V3", "INVALID")
        if (
            precommit_gate_v2["source_stability_gate_hash"]
            != residual_energy_gate["source_beta_stability_gate_hash"]
            or precommit_gate_v2["source_replay_hash"]
            != residual_energy_gate["source_replay_hash"]
            or precommit_gate_v2["source_registration_hash"]
            != residual_energy_gate["source_registration_hash"]
            or precommit_gate_v2["source_calibration_observations_hash"]
            != residual_energy_gate["source_calibration_observations_hash"]
            or precommit_gate_v2["fold_count"] != residual_energy_gate["fold_count"]
        ):
            return _unknown("CROSS_GATE_SOURCE_HASH_MISMATCH", "INVALID")
        return _observed(precommit_gate_v2, residual_energy_gate)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return _unknown("SOURCE_GATE_INVALID_FOR_V3", "INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3(
    document: Any,
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
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3(
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
        return strict_json_contract_equal(document, rebuilt)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return False
