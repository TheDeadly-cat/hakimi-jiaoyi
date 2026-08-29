from __future__ import annotations

from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4 import (
    GATE_SCHEMA as PRECOMMIT_GATE_V4_SCHEMA,
    STATIC_FINGERPRINT as PRECOMMIT_GATE_V4_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2 import (
    GATE_SCHEMA as RESIDUAL_ORDER_GATE_V2_SCHEMA,
    STATIC_FINGERPRINT as RESIDUAL_ORDER_GATE_V2_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2,
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
    "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v5"
)
STATIC_FINGERPRINT = "20260902-cross-lag-factor-calibration-precommit-gate-5"


def _authority() -> dict[str, bool]:
    return {
        "beta_temporal_stability_proven": False,
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_precommit_timing_attested": False,
        "future_evaluation_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "residual_energy_temporal_stability_proven": False,
        "residual_order_independence_proven": False,
    }


def _unknown_facts() -> dict[str, bool]:
    return {
        "cross_gate_source_hashes_bound": False,
        "external_time_anchor_verified": False,
        "future_evaluation_activated": False,
        "local_precommit_binding_complete": False,
        "precommit_gate_v4_verified": False,
        "residual_multi_lag_order_threshold_passed": False,
        "residual_order_gate_v2_verified": False,
        "residual_order_independence_proven": False,
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
            "source_precommit_gate_v4_decision": None,
            "source_residual_order_gate_v2_decision": None,
            "protocol_id": None,
            "future_evaluation_id": None,
            "precommit_declared_at_utc": None,
            "evaluation_not_before_date": None,
            "external_time_anchor_reference_hash": None,
            "fold_count": None,
            "evaluated_lags": None,
            "maximum_evaluated_lag": None,
            "maximum_allowed_absolute_multi_lag_residual_energy_coupling": None,
            "maximum_observed_absolute_multi_lag_residual_energy_coupling": None,
            "residual_multi_lag_order_unstable_identity_count": None,
            "source_precommit_gate_v4_hash": None,
            "source_residual_order_gate_v2_hash": None,
            "source_residual_order_gate_v1_hash": None,
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
    precommit_gate_v4: dict[str, Any], residual_order_gate_v2: dict[str, Any]
) -> dict[str, Any]:
    precommit_decision = precommit_gate_v4["gate_decision"]
    order_decision = residual_order_gate_v2["gate_decision"]
    if precommit_decision == "BLOCK":
        decision = "BLOCK"
        reason = "SOURCE_PRECOMMIT_GATE_V4_BLOCKED"
    elif order_decision == "BLOCK":
        decision = "BLOCK"
        reason = "RESIDUAL_MULTI_LAG_ORDER_STABILITY_GATE_BLOCKED"
    elif (
        precommit_decision == "BOUND_LOCAL_ONLY_TRIPLE_STABILITY_GUARDED"
        and order_decision == "RESIDUAL_MULTI_LAG_ORDER_STABLE_CANDIDATE"
    ):
        decision = "BOUND_LOCAL_ONLY_MULTI_LAG_STABILITY_GUARDED"
        reason = "LOCAL_PRECOMMIT_MULTI_LAG_RESIDUAL_ORDER_GUARD_BOUND"
    else:
        return _unknown("SOURCE_GATE_NOT_OBSERVED_FOR_V5", "UNKNOWN")

    blockers = _combined_blockers(
        precommit_gate_v4["blockers"], residual_order_gate_v2["blockers"]
    )
    if decision == "BLOCK" and reason not in blockers:
        blockers.append(reason)
    if "PRECOMMIT_GATE_V5_NOT_ACTIVATED" not in blockers:
        blockers.append("PRECOMMIT_GATE_V5_NOT_ACTIVATED")
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("PRECOMMIT_GATE_V5_INTERNAL_AUTHORITY_INVALID", "INVALID")

    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": decision,
            "gate_reason": reason,
            "source_precommit_gate_v4_decision": precommit_decision,
            "source_residual_order_gate_v2_decision": order_decision,
            "protocol_id": precommit_gate_v4["protocol_id"],
            "future_evaluation_id": precommit_gate_v4["future_evaluation_id"],
            "precommit_declared_at_utc": precommit_gate_v4[
                "precommit_declared_at_utc"
            ],
            "evaluation_not_before_date": precommit_gate_v4[
                "evaluation_not_before_date"
            ],
            "external_time_anchor_reference_hash": precommit_gate_v4[
                "external_time_anchor_reference_hash"
            ],
            "fold_count": precommit_gate_v4["fold_count"],
            "evaluated_lags": residual_order_gate_v2["evaluated_lags"],
            "maximum_evaluated_lag": residual_order_gate_v2[
                "maximum_evaluated_lag"
            ],
            "maximum_allowed_absolute_multi_lag_residual_energy_coupling": residual_order_gate_v2[
                "maximum_allowed_absolute_multi_lag_residual_energy_coupling"
            ],
            "maximum_observed_absolute_multi_lag_residual_energy_coupling": residual_order_gate_v2[
                "maximum_observed_absolute_multi_lag_residual_energy_coupling"
            ],
            "residual_multi_lag_order_unstable_identity_count": residual_order_gate_v2[
                "unstable_identity_count"
            ],
            "source_precommit_gate_v4_hash": precommit_gate_v4["gate_hash"],
            "source_residual_order_gate_v2_hash": residual_order_gate_v2[
                "gate_hash"
            ],
            "source_residual_order_gate_v1_hash": precommit_gate_v4[
                "source_residual_order_gate_hash"
            ],
            "source_beta_stability_gate_hash": precommit_gate_v4[
                "source_beta_stability_gate_hash"
            ],
            "source_replay_hash": precommit_gate_v4["source_replay_hash"],
            "source_registration_hash": precommit_gate_v4[
                "source_registration_hash"
            ],
            "source_calibration_observations_hash": precommit_gate_v4[
                "source_calibration_observations_hash"
            ],
            "facts": {
                "cross_gate_source_hashes_bound": True,
                "external_time_anchor_verified": False,
                "future_evaluation_activated": False,
                "local_precommit_binding_complete": precommit_gate_v4["facts"][
                    "local_precommit_binding_complete"
                ],
                "precommit_gate_v4_verified": True,
                "residual_multi_lag_order_threshold_passed": residual_order_gate_v2[
                    "facts"
                ]["residual_multi_lag_order_threshold_passed"],
                "residual_order_gate_v2_verified": True,
                "residual_order_independence_proven": False,
                "source_gate_block_relaxed": False,
            },
            "blockers": blockers,
            "authority": authority,
        }
    )


def evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5(
    precommit_gate_v4: Any,
    residual_order_gate_v2: Any,
    precommit_gate_v3: Any,
    residual_order_gate_v1: Any,
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
    expected_precommit_gate_v4_hash: Any,
    expected_residual_order_gate_v2_hash: Any,
    expected_precommit_gate_v3_hash: Any,
    expected_residual_order_gate_v1_hash: Any,
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
        if precommit_gate_v4 is None or residual_order_gate_v2 is None:
            missing = (
                "PRECOMMIT_GATE_V4_MISSING"
                if precommit_gate_v4 is None
                else "RESIDUAL_ORDER_GATE_V2_MISSING"
            )
            expected = (
                expected_precommit_gate_v4_hash
                if precommit_gate_v4 is None
                else expected_residual_order_gate_v2_hash
            )
            if type(expected) is not str or expected != "":
                return _unknown("SOURCE_GATE_INVALID_FOR_V5", "INVALID")
            return _unknown(missing, "MISSING")
        if type(precommit_gate_v4) is not dict or type(residual_order_gate_v2) is not dict:
            return _unknown("SOURCE_GATE_INVALID_FOR_V5", "INVALID")
        if (
            precommit_gate_v4.get("schema_version") != PRECOMMIT_GATE_V4_SCHEMA
            or precommit_gate_v4.get("static_fingerprint")
            != PRECOMMIT_GATE_V4_STATIC_FINGERPRINT
        ):
            return _unknown("PRECOMMIT_GATE_V4_UNSUPPORTED", "UNSUPPORTED")
        if (
            residual_order_gate_v2.get("schema_version")
            != RESIDUAL_ORDER_GATE_V2_SCHEMA
            or residual_order_gate_v2.get("static_fingerprint")
            != RESIDUAL_ORDER_GATE_V2_STATIC_FINGERPRINT
        ):
            return _unknown("RESIDUAL_ORDER_GATE_V2_UNSUPPORTED", "UNSUPPORTED")
        if (
            not strict_sha256(expected_precommit_gate_v4_hash)
            or not strict_sha256(expected_residual_order_gate_v2_hash)
            or precommit_gate_v4.get("gate_hash") != expected_precommit_gate_v4_hash
            or residual_order_gate_v2.get("gate_hash")
            != expected_residual_order_gate_v2_hash
        ):
            return _unknown("SOURCE_GATE_INVALID_FOR_V5", "INVALID")

        precommit_verified = verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4(
            precommit_gate_v4,
            precommit_gate_v3,
            residual_order_gate_v1,
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
            expected_residual_order_gate_hash=expected_residual_order_gate_v1_hash,
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
        order_verified = verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2(
            residual_order_gate_v2,
            residual_order_gate_v1,
            beta_stability_gate,
            replay,
            residualization_registration,
            calibration_observations,
            expected_residual_order_gate_v1_hash=(
                expected_residual_order_gate_v1_hash
            ),
            expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        if precommit_verified is not True or order_verified is not True:
            return _unknown("SOURCE_GATE_INVALID_FOR_V5", "INVALID")
        if (
            precommit_gate_v4["source_residual_order_gate_hash"]
            != residual_order_gate_v2["source_residual_order_gate_v1_hash"]
            or precommit_gate_v4["source_beta_stability_gate_hash"]
            != residual_order_gate_v2["source_beta_stability_gate_hash"]
            or precommit_gate_v4["source_replay_hash"]
            != residual_order_gate_v2["source_replay_hash"]
            or precommit_gate_v4["source_registration_hash"]
            != residual_order_gate_v2["source_registration_hash"]
            or precommit_gate_v4["source_calibration_observations_hash"]
            != residual_order_gate_v2["source_calibration_observations_hash"]
            or precommit_gate_v4["fold_count"] != residual_order_gate_v2["fold_count"]
        ):
            return _unknown("CROSS_GATE_SOURCE_HASH_MISMATCH", "INVALID")
        return _observed(precommit_gate_v4, residual_order_gate_v2)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return _unknown("SOURCE_GATE_INVALID_FOR_V5", "INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5(
    document: Any,
    precommit_gate_v4: Any,
    residual_order_gate_v2: Any,
    precommit_gate_v3: Any,
    residual_order_gate_v1: Any,
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
    expected_precommit_gate_v4_hash: Any,
    expected_residual_order_gate_v2_hash: Any,
    expected_precommit_gate_v3_hash: Any,
    expected_residual_order_gate_v1_hash: Any,
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
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5(
            precommit_gate_v4,
            residual_order_gate_v2,
            precommit_gate_v3,
            residual_order_gate_v1,
            precommit_gate_v2,
            residual_energy_gate,
            precommit_gate_v1,
            beta_stability_gate,
            precommit_declaration,
            report,
            replay,
            residualization_registration,
            calibration_observations,
            expected_precommit_gate_v4_hash=expected_precommit_gate_v4_hash,
            expected_residual_order_gate_v2_hash=expected_residual_order_gate_v2_hash,
            expected_precommit_gate_v3_hash=expected_precommit_gate_v3_hash,
            expected_residual_order_gate_v1_hash=(
                expected_residual_order_gate_v1_hash
            ),
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
