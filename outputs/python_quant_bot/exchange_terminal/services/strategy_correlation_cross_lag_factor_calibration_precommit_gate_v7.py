from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6 import (
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1 import (
    verify_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v7"
)
STATIC_FINGERPRINT = "20260912-cross-lag-factor-calibration-precommit-gate-7"
SOURCE_V6_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v6"
)
SOURCE_OMNIBUS_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-residual-order-omnibus-gate-candidate-v1"
)
SOURCE_V6_POSITIVE = "BOUND_LOCAL_ONLY_THREE_LAG_STABILITY_GUARDED"
SOURCE_OMNIBUS_POSITIVE = "RESIDUAL_FINITE_HORIZON_OMNIBUS_STABLE_CANDIDATE"
POSITIVE_DECISION = "BOUND_LOCAL_ONLY_FINITE_HORIZON_OMNIBUS_GUARDED"
EVALUATED_LAGS = (1, 2, 3, 4, 5, 6)
OMNIBUS_BAND_LAGS = (4, 5, 6)


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_precommit_timing_attested": False,
        "future_evaluation_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "residual_order_independence_proven": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "cross_gate_source_hashes_bound": False,
        "external_time_anchor_verified": False,
        "finite_horizon_omnibus_guard_bound": False,
        "future_evaluation_activated": False,
        "local_precommit_binding_complete": False,
        "omnibus_gate_v1_verified": False,
        "omnibus_quadratic_energy_threshold_passed": False,
        "precommit_gate_v6_verified": False,
        "residual_order_independence_proven": False,
        "source_gate_block_relaxed": False,
    }


def _base_projection() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source_state": "UNKNOWN",
        "source_precommit_gate_v6_decision": None,
        "source_omnibus_gate_v1_decision": None,
        "source_precommit_gate_v6_hash": None,
        "source_omnibus_gate_v1_hash": None,
        "source_precommit_gate_v5_hash": None,
        "source_residual_order_gate_v3_hash": None,
        "source_precommit_gate_v4_hash": None,
        "source_residual_order_gate_v2_hash": None,
        "source_residual_order_gate_v1_hash": None,
        "source_beta_stability_gate_hash": None,
        "source_replay_hash": None,
        "source_registration_hash": None,
        "source_calibration_observations_hash": None,
        "evaluated_lags": list(EVALUATED_LAGS),
        "omnibus_band_lags": list(OMNIBUS_BAND_LAGS),
        "maximum_evaluated_lag": max(EVALUATED_LAGS),
        "maximum_allowed_lag_band_quadratic_energy": "0.64",
        "maximum_observed_lag_band_quadratic_energy": None,
        "fold_count": None,
        "unstable_identity_count": None,
        "gate_decision": "UNKNOWN",
        "gate_reason": "SOURCE_NOT_EVALUATED",
        "blockers": ["SOURCE_NOT_EVALUATED"],
        "facts": _facts(),
        "authority": _authority(),
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "gate_hash")


def _unknown(reason: str, source_state: str = "UNKNOWN") -> dict[str, Any]:
    projection = _base_projection()
    projection["source_state"] = source_state
    projection["gate_reason"] = reason
    projection["blockers"] = [reason]
    return _seal(projection)


def _hash_matches(expected: Any, actual: Any) -> bool:
    return isinstance(expected, str) and isinstance(actual, str) and expected == actual


def _combined_blockers(*groups: list[str]) -> list[str]:
    combined: list[str] = []
    for group in groups:
        for blocker in group:
            if blocker not in combined:
                combined.append(blocker)
    return combined


def _cross_bindings_match(
    precommit_gate_v6: dict[str, Any],
    omnibus_gate_v1: dict[str, Any],
    *,
    expected_precommit_gate_v5_hash: Any,
    expected_residual_order_gate_v3_hash: Any,
    expected_precommit_gate_v4_hash: Any,
    expected_residual_order_gate_v2_hash: Any,
    expected_residual_order_gate_v1_hash: Any,
    expected_beta_stability_gate_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    bindings = (
        (
            expected_precommit_gate_v5_hash,
            precommit_gate_v6.get("source_precommit_gate_v5_hash"),
        ),
        (
            expected_residual_order_gate_v3_hash,
            precommit_gate_v6.get("source_residual_order_gate_v3_hash"),
            omnibus_gate_v1.get("source_residual_order_gate_v3_hash"),
        ),
        (
            expected_precommit_gate_v4_hash,
            precommit_gate_v6.get("source_precommit_gate_v4_hash"),
        ),
        (
            expected_residual_order_gate_v2_hash,
            precommit_gate_v6.get("source_residual_order_gate_v2_hash"),
            omnibus_gate_v1.get("source_residual_order_gate_v2_hash"),
        ),
        (
            expected_residual_order_gate_v1_hash,
            precommit_gate_v6.get("source_residual_order_gate_v1_hash"),
            omnibus_gate_v1.get("source_residual_order_gate_v1_hash"),
        ),
        (
            expected_beta_stability_gate_hash,
            precommit_gate_v6.get("source_beta_stability_gate_hash"),
            omnibus_gate_v1.get("source_beta_stability_gate_hash"),
        ),
        (
            expected_replay_hash,
            precommit_gate_v6.get("source_replay_hash"),
            omnibus_gate_v1.get("source_replay_hash"),
        ),
        (
            expected_registration_hash,
            precommit_gate_v6.get("source_registration_hash"),
            omnibus_gate_v1.get("source_registration_hash"),
        ),
        (
            expected_calibration_observations_hash,
            precommit_gate_v6.get("source_calibration_observations_hash"),
            omnibus_gate_v1.get("source_calibration_observations_hash"),
        ),
    )
    return all(
        isinstance(group[0], str) and all(value == group[0] for value in group[1:])
        for group in bindings
    )


def evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7(
    precommit_gate_v6: Any,
    omnibus_gate_v1: Any,
    precommit_gate_v5: Any,
    residual_order_gate_v3: Any,
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
    expected_precommit_gate_v6_hash: Any,
    expected_omnibus_gate_v1_hash: Any,
    expected_precommit_gate_v5_hash: Any,
    expected_residual_order_gate_v3_hash: Any,
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
    if not isinstance(precommit_gate_v6, dict) or not isinstance(
        omnibus_gate_v1, dict
    ):
        return _unknown("MISSING_SOURCE_GATE")
    if precommit_gate_v6.get("schema_version") != SOURCE_V6_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_PRECOMMIT_GATE_V6", "UNSUPPORTED")
    if omnibus_gate_v1.get("schema_version") != SOURCE_OMNIBUS_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_OMNIBUS_GATE_V1", "UNSUPPORTED")
    if not _hash_matches(
        expected_precommit_gate_v6_hash,
        precommit_gate_v6.get("gate_hash"),
    ):
        return _unknown("EXPECTED_PRECOMMIT_GATE_V6_HASH_MISMATCH")
    if not _hash_matches(
        expected_omnibus_gate_v1_hash,
        omnibus_gate_v1.get("gate_hash"),
    ):
        return _unknown("EXPECTED_OMNIBUS_GATE_V1_HASH_MISMATCH")

    v6_verified = verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6(
        precommit_gate_v6,
        precommit_gate_v5,
        residual_order_gate_v3,
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
        expected_precommit_gate_v5_hash=expected_precommit_gate_v5_hash,
        expected_residual_order_gate_v3_hash=expected_residual_order_gate_v3_hash,
        expected_precommit_gate_v4_hash=expected_precommit_gate_v4_hash,
        expected_residual_order_gate_v2_hash=expected_residual_order_gate_v2_hash,
        expected_precommit_gate_v3_hash=expected_precommit_gate_v3_hash,
        expected_residual_order_gate_v1_hash=expected_residual_order_gate_v1_hash,
        expected_precommit_gate_v2_hash=expected_precommit_gate_v2_hash,
        expected_residual_energy_gate_hash=expected_residual_energy_gate_hash,
        expected_precommit_gate_v1_hash=expected_precommit_gate_v1_hash,
        expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
        expected_declaration_hash=expected_declaration_hash,
        expected_report_hash=expected_report_hash,
        expected_replay_hash=expected_replay_hash,
        expected_registration_hash=expected_registration_hash,
        expected_calibration_observations_hash=expected_calibration_observations_hash,
    )
    omnibus_verified = verify_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1(
        omnibus_gate_v1,
        residual_order_gate_v3,
        residual_order_gate_v2,
        residual_order_gate_v1,
        beta_stability_gate,
        replay,
        residualization_registration,
        calibration_observations,
        expected_residual_order_gate_v3_hash=expected_residual_order_gate_v3_hash,
        expected_residual_order_gate_v2_hash=expected_residual_order_gate_v2_hash,
        expected_residual_order_gate_v1_hash=expected_residual_order_gate_v1_hash,
        expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
        expected_replay_hash=expected_replay_hash,
        expected_registration_hash=expected_registration_hash,
        expected_calibration_observations_hash=expected_calibration_observations_hash,
    )
    if not v6_verified or not omnibus_verified:
        return _unknown("SOURCE_GATE_OR_CONTEXT_INVALID")
    if not _cross_bindings_match(
        precommit_gate_v6,
        omnibus_gate_v1,
        expected_precommit_gate_v5_hash=expected_precommit_gate_v5_hash,
        expected_residual_order_gate_v3_hash=expected_residual_order_gate_v3_hash,
        expected_precommit_gate_v4_hash=expected_precommit_gate_v4_hash,
        expected_residual_order_gate_v2_hash=expected_residual_order_gate_v2_hash,
        expected_residual_order_gate_v1_hash=expected_residual_order_gate_v1_hash,
        expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
        expected_replay_hash=expected_replay_hash,
        expected_registration_hash=expected_registration_hash,
        expected_calibration_observations_hash=expected_calibration_observations_hash,
    ):
        return _unknown("CROSS_GATE_SOURCE_HASH_MISMATCH")

    v6_decision = precommit_gate_v6.get("gate_decision")
    omnibus_decision = omnibus_gate_v1.get("gate_decision")
    if "UNKNOWN" in (v6_decision, omnibus_decision):
        return _unknown("SOURCE_GATE_UNKNOWN")
    positive = (
        v6_decision == SOURCE_V6_POSITIVE
        and omnibus_decision == SOURCE_OMNIBUS_POSITIVE
    )
    if v6_decision != SOURCE_V6_POSITIVE:
        reason = "PRECOMMIT_GATE_V6_BLOCKED"
    elif omnibus_decision != SOURCE_OMNIBUS_POSITIVE:
        reason = "RESIDUAL_FINITE_HORIZON_OMNIBUS_GATE_BLOCKED"
    else:
        reason = "LOCAL_PRECOMMIT_FINITE_HORIZON_OMNIBUS_GUARD_BOUND"

    blockers = _combined_blockers(
        list(precommit_gate_v6.get("blockers", [])),
        list(omnibus_gate_v1.get("blockers", [])),
        ["PRECOMMIT_GATE_V7_NOT_ACTIVATED"],
        [] if positive else [reason],
    )
    projection = _base_projection()
    projection.update(
        {
            "source_state": "OBSERVED",
            "source_precommit_gate_v6_decision": v6_decision,
            "source_omnibus_gate_v1_decision": omnibus_decision,
            "source_precommit_gate_v6_hash": expected_precommit_gate_v6_hash,
            "source_omnibus_gate_v1_hash": expected_omnibus_gate_v1_hash,
            "source_precommit_gate_v5_hash": expected_precommit_gate_v5_hash,
            "source_residual_order_gate_v3_hash": expected_residual_order_gate_v3_hash,
            "source_precommit_gate_v4_hash": expected_precommit_gate_v4_hash,
            "source_residual_order_gate_v2_hash": expected_residual_order_gate_v2_hash,
            "source_residual_order_gate_v1_hash": expected_residual_order_gate_v1_hash,
            "source_beta_stability_gate_hash": expected_beta_stability_gate_hash,
            "source_replay_hash": expected_replay_hash,
            "source_registration_hash": expected_registration_hash,
            "source_calibration_observations_hash": expected_calibration_observations_hash,
            "evaluated_lags": list(omnibus_gate_v1.get("evaluated_lags", [])),
            "omnibus_band_lags": list(
                omnibus_gate_v1.get("omnibus_band_lags", [])
            ),
            "maximum_evaluated_lag": omnibus_gate_v1.get(
                "maximum_evaluated_lag"
            ),
            "maximum_allowed_lag_band_quadratic_energy": omnibus_gate_v1.get(
                "maximum_allowed_lag_band_quadratic_energy"
            ),
            "maximum_observed_lag_band_quadratic_energy": omnibus_gate_v1.get(
                "maximum_observed_lag_band_quadratic_energy"
            ),
            "fold_count": omnibus_gate_v1.get("fold_count"),
            "unstable_identity_count": omnibus_gate_v1.get(
                "unstable_identity_count"
            ),
            "gate_decision": POSITIVE_DECISION if positive else "BLOCK",
            "gate_reason": reason,
            "blockers": blockers,
            "facts": {
                **_facts(),
                "cross_gate_source_hashes_bound": True,
                "finite_horizon_omnibus_guard_bound": positive,
                "local_precommit_binding_complete": positive,
                "omnibus_gate_v1_verified": True,
                "omnibus_quadratic_energy_threshold_passed": omnibus_decision
                == SOURCE_OMNIBUS_POSITIVE,
                "precommit_gate_v6_verified": True,
            },
        }
    )
    return _seal(projection)


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7(
    document: Any,
    precommit_gate_v6: Any,
    omnibus_gate_v1: Any,
    precommit_gate_v5: Any,
    residual_order_gate_v3: Any,
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
    expected_precommit_gate_v6_hash: Any,
    expected_omnibus_gate_v1_hash: Any,
    expected_precommit_gate_v5_hash: Any,
    expected_residual_order_gate_v3_hash: Any,
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
    if not isinstance(document, dict):
        return False
    rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7(
        precommit_gate_v6,
        omnibus_gate_v1,
        precommit_gate_v5,
        residual_order_gate_v3,
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
        expected_precommit_gate_v6_hash=expected_precommit_gate_v6_hash,
        expected_omnibus_gate_v1_hash=expected_omnibus_gate_v1_hash,
        expected_precommit_gate_v5_hash=expected_precommit_gate_v5_hash,
        expected_residual_order_gate_v3_hash=expected_residual_order_gate_v3_hash,
        expected_precommit_gate_v4_hash=expected_precommit_gate_v4_hash,
        expected_residual_order_gate_v2_hash=expected_residual_order_gate_v2_hash,
        expected_precommit_gate_v3_hash=expected_precommit_gate_v3_hash,
        expected_residual_order_gate_v1_hash=expected_residual_order_gate_v1_hash,
        expected_precommit_gate_v2_hash=expected_precommit_gate_v2_hash,
        expected_residual_energy_gate_hash=expected_residual_energy_gate_hash,
        expected_precommit_gate_v1_hash=expected_precommit_gate_v1_hash,
        expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
        expected_declaration_hash=expected_declaration_hash,
        expected_report_hash=expected_report_hash,
        expected_replay_hash=expected_replay_hash,
        expected_registration_hash=expected_registration_hash,
        expected_calibration_observations_hash=expected_calibration_observations_hash,
    )
    return strict_json_contract_equal(document, rebuilt)
