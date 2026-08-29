from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7 import (
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6 import (
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-report-consumer-verification-v7"
)
STATIC_FINGERPRINT = (
    "20260913-cross-lag-factor-calibration-precommit-report-consumer-7"
)
SOURCE_V7_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v7"
)
SOURCE_CONSUMER_V6_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-report-consumer-verification-v6"
)
SOURCE_V7_POSITIVE = "BOUND_LOCAL_ONLY_FINITE_HORIZON_OMNIBUS_GUARDED"
SOURCE_CONSUMER_V6_POSITIVE = "VERIFIED_LOCAL_BINDING"
EVALUATED_LAGS = (1, 2, 3, 4, 5, 6)
OMNIBUS_BAND_LAGS = (4, 5, 6)


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mount_allowed": False,
        "profitability_claim_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "aggregate_only": True,
        "cross_consumer_source_hashes_bound": False,
        "finite_horizon_omnibus_guard_bound": False,
        "local_precommit_binding_complete": False,
        "omnibus_gate_v1_verified": False,
        "omnibus_quadratic_energy_threshold_passed": False,
        "precommit_gate_v7_verified": False,
        "report_consumer_v6_verified": False,
        "residual_order_gate_v3_verified": False,
        "residual_order_independence_proven": False,
        "source_gate_block_relaxed": False,
    }


def _base_projection() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source_state": "UNKNOWN",
        "source_precommit_gate_v7_decision": None,
        "source_report_consumer_v6_state": None,
        "source_precommit_gate_v7_hash": None,
        "source_report_consumer_v6_hash": None,
        "source_precommit_gate_v6_hash": None,
        "source_omnibus_gate_v1_hash": None,
        "source_report_consumer_v5_hash": None,
        "source_precommit_gate_v5_hash": None,
        "source_residual_order_gate_v3_hash": None,
        "source_precommit_gate_v4_hash": None,
        "source_residual_order_gate_v2_hash": None,
        "source_residual_order_gate_v1_hash": None,
        "source_beta_stability_gate_hash": None,
        "source_replay_hash": None,
        "source_registration_hash": None,
        "source_calibration_observations_hash": None,
        "verification_state": "UNKNOWN",
        "verification_reason": "SOURCE_NOT_EVALUATED",
        "blockers": ["SOURCE_NOT_EVALUATED"],
        "protocol_id": None,
        "future_evaluation_id": None,
        "evaluation_not_before_date": None,
        "precommit_declared_at_utc": None,
        "evaluated_lags": list(EVALUATED_LAGS),
        "omnibus_band_lags": list(OMNIBUS_BAND_LAGS),
        "maximum_evaluated_lag": max(EVALUATED_LAGS),
        "maximum_allowed_lag_band_quadratic_energy": "0.64",
        "maximum_observed_lag_band_quadratic_energy": None,
        "fold_count": None,
        "unstable_identity_count": None,
        "facts": _facts(),
        "authority": _authority(),
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "verification_hash")


def _unknown(reason: str, source_state: str = "UNKNOWN") -> dict[str, Any]:
    projection = _base_projection()
    projection["source_state"] = source_state
    projection["verification_reason"] = reason
    projection["blockers"] = [reason]
    return _seal(projection)


def _hash_matches(expected: Any, actual: Any) -> bool:
    return (
        isinstance(expected, str)
        and isinstance(actual, str)
        and expected == actual
    )


def _deduplicate(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _cross_bindings_match(
    precommit_gate_v7: dict[str, Any],
    report_consumer_v6: dict[str, Any],
    precommit_gate_v6: dict[str, Any],
    omnibus_gate_v1: dict[str, Any],
    report_consumer_v5: dict[str, Any],
    *,
    expected_precommit_gate_v6_hash: Any,
    expected_omnibus_gate_v1_hash: Any,
    expected_report_consumer_v5_hash: Any,
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
            expected_precommit_gate_v6_hash,
            precommit_gate_v7.get("source_precommit_gate_v6_hash"),
            report_consumer_v6.get("source_gate_hash"),
            precommit_gate_v6.get("gate_hash"),
        ),
        (
            expected_omnibus_gate_v1_hash,
            precommit_gate_v7.get("source_omnibus_gate_v1_hash"),
            omnibus_gate_v1.get("gate_hash"),
        ),
        (
            expected_report_consumer_v5_hash,
            report_consumer_v6.get("source_report_consumer_v5_hash"),
            report_consumer_v5.get("verification_hash"),
        ),
        (
            expected_precommit_gate_v5_hash,
            precommit_gate_v7.get("source_precommit_gate_v5_hash"),
            report_consumer_v6.get("source_precommit_gate_v5_hash"),
            precommit_gate_v6.get("source_precommit_gate_v5_hash"),
        ),
        (
            expected_residual_order_gate_v3_hash,
            precommit_gate_v7.get("source_residual_order_gate_v3_hash"),
            report_consumer_v6.get("source_residual_order_gate_v3_hash"),
            precommit_gate_v6.get("source_residual_order_gate_v3_hash"),
            omnibus_gate_v1.get("source_residual_order_gate_v3_hash"),
        ),
        (
            expected_precommit_gate_v4_hash,
            precommit_gate_v7.get("source_precommit_gate_v4_hash"),
            precommit_gate_v6.get("source_precommit_gate_v4_hash"),
        ),
        (
            expected_residual_order_gate_v2_hash,
            precommit_gate_v7.get("source_residual_order_gate_v2_hash"),
            report_consumer_v6.get("source_residual_order_gate_v2_hash"),
            precommit_gate_v6.get("source_residual_order_gate_v2_hash"),
            omnibus_gate_v1.get("source_residual_order_gate_v2_hash"),
        ),
        (
            expected_residual_order_gate_v1_hash,
            precommit_gate_v7.get("source_residual_order_gate_v1_hash"),
            report_consumer_v6.get("source_residual_order_gate_v1_hash"),
            precommit_gate_v6.get("source_residual_order_gate_v1_hash"),
            omnibus_gate_v1.get("source_residual_order_gate_v1_hash"),
        ),
        (
            expected_beta_stability_gate_hash,
            precommit_gate_v7.get("source_beta_stability_gate_hash"),
            report_consumer_v6.get("source_beta_stability_gate_hash"),
            precommit_gate_v6.get("source_beta_stability_gate_hash"),
            omnibus_gate_v1.get("source_beta_stability_gate_hash"),
        ),
        (
            expected_replay_hash,
            precommit_gate_v7.get("source_replay_hash"),
            report_consumer_v6.get("source_replay_hash"),
            precommit_gate_v6.get("source_replay_hash"),
            omnibus_gate_v1.get("source_replay_hash"),
        ),
        (
            expected_registration_hash,
            precommit_gate_v7.get("source_registration_hash"),
            report_consumer_v6.get("source_registration_hash"),
            precommit_gate_v6.get("source_registration_hash"),
            omnibus_gate_v1.get("source_registration_hash"),
        ),
        (
            expected_calibration_observations_hash,
            precommit_gate_v7.get("source_calibration_observations_hash"),
            report_consumer_v6.get("source_calibration_observations_hash"),
            precommit_gate_v6.get("source_calibration_observations_hash"),
            omnibus_gate_v1.get("source_calibration_observations_hash"),
        ),
    )
    return all(
        isinstance(group[0], str) and all(value == group[0] for value in group[1:])
        for group in bindings
    )


def consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7(
    precommit_gate_v7: Any,
    report_consumer_v6: Any,
    precommit_gate_v6: Any,
    omnibus_gate_v1: Any,
    report_consumer_v5: Any,
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
    expected_precommit_gate_v7_hash: Any,
    expected_report_consumer_v6_hash: Any,
    expected_precommit_gate_v6_hash: Any,
    expected_omnibus_gate_v1_hash: Any,
    expected_report_consumer_v5_hash: Any,
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
    if not isinstance(precommit_gate_v7, dict) or not isinstance(
        report_consumer_v6, dict
    ):
        return _unknown("MISSING_SOURCE")
    if precommit_gate_v7.get("schema_version") != SOURCE_V7_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_PRECOMMIT_GATE_V7", "UNSUPPORTED")
    if (
        report_consumer_v6.get("schema_version")
        != SOURCE_CONSUMER_V6_SCHEMA_VERSION
    ):
        return _unknown("UNSUPPORTED_REPORT_CONSUMER_V6", "UNSUPPORTED")
    if not _hash_matches(
        expected_precommit_gate_v7_hash,
        precommit_gate_v7.get("gate_hash"),
    ):
        return _unknown("EXPECTED_PRECOMMIT_GATE_V7_HASH_MISMATCH")
    if not _hash_matches(
        expected_report_consumer_v6_hash,
        report_consumer_v6.get("verification_hash"),
    ):
        return _unknown("EXPECTED_REPORT_CONSUMER_V6_HASH_MISMATCH")

    v7_verified = verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7(
        precommit_gate_v7,
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
    v6_consumer_verified = verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6(
        report_consumer_v6,
        precommit_gate_v6,
        report_consumer_v5,
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
        expected_report_consumer_v5_hash=expected_report_consumer_v5_hash,
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
        expected_source_report_hash=expected_report_hash,
        expected_replay_hash=expected_replay_hash,
        expected_registration_hash=expected_registration_hash,
        expected_calibration_observations_hash=expected_calibration_observations_hash,
    )
    if not v7_verified or not v6_consumer_verified:
        return _unknown("SOURCE_OR_CONTEXT_INVALID")
    if not _cross_bindings_match(
        precommit_gate_v7,
        report_consumer_v6,
        precommit_gate_v6,
        omnibus_gate_v1,
        report_consumer_v5,
        expected_precommit_gate_v6_hash=expected_precommit_gate_v6_hash,
        expected_omnibus_gate_v1_hash=expected_omnibus_gate_v1_hash,
        expected_report_consumer_v5_hash=expected_report_consumer_v5_hash,
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
        return _unknown("CROSS_CONSUMER_SOURCE_HASH_MISMATCH")

    gate_decision = precommit_gate_v7.get("gate_decision")
    consumer_state = report_consumer_v6.get("verification_state")
    if gate_decision == "UNKNOWN" or consumer_state == "UNKNOWN":
        return _unknown("SOURCE_STATE_UNKNOWN")
    if gate_decision not in (SOURCE_V7_POSITIVE, "BLOCK") or consumer_state not in (
        SOURCE_CONSUMER_V6_POSITIVE,
        "VERIFIED_BLOCK",
    ):
        return _unknown("SOURCE_STATE_INVALID")
    if gate_decision == SOURCE_V7_POSITIVE and consumer_state != (
        SOURCE_CONSUMER_V6_POSITIVE
    ):
        return _unknown("SOURCE_STATE_INCOMPATIBLE")

    positive = (
        gate_decision == SOURCE_V7_POSITIVE
        and consumer_state == SOURCE_CONSUMER_V6_POSITIVE
    )
    verification_state = "VERIFIED_LOCAL_BINDING" if positive else "VERIFIED_BLOCK"
    verification_reason = (
        "PRECOMMIT_V7_LOCAL_BINDING_VERIFIED"
        if positive
        else "PRECOMMIT_V7_BLOCK_VERIFIED"
    )

    source_facts = precommit_gate_v7.get("facts", {})
    projection = _base_projection()
    projection.update(
        {
            "source_state": "OBSERVED",
            "source_precommit_gate_v7_decision": gate_decision,
            "source_report_consumer_v6_state": consumer_state,
            "source_precommit_gate_v7_hash": expected_precommit_gate_v7_hash,
            "source_report_consumer_v6_hash": expected_report_consumer_v6_hash,
            "source_precommit_gate_v6_hash": expected_precommit_gate_v6_hash,
            "source_omnibus_gate_v1_hash": expected_omnibus_gate_v1_hash,
            "source_report_consumer_v5_hash": expected_report_consumer_v5_hash,
            "source_precommit_gate_v5_hash": expected_precommit_gate_v5_hash,
            "source_residual_order_gate_v3_hash": expected_residual_order_gate_v3_hash,
            "source_precommit_gate_v4_hash": expected_precommit_gate_v4_hash,
            "source_residual_order_gate_v2_hash": expected_residual_order_gate_v2_hash,
            "source_residual_order_gate_v1_hash": expected_residual_order_gate_v1_hash,
            "source_beta_stability_gate_hash": expected_beta_stability_gate_hash,
            "source_replay_hash": expected_replay_hash,
            "source_registration_hash": expected_registration_hash,
            "source_calibration_observations_hash": expected_calibration_observations_hash,
            "verification_state": verification_state,
            "verification_reason": verification_reason,
            "blockers": _deduplicate(
                list(report_consumer_v6.get("blockers", []))
                + list(precommit_gate_v7.get("blockers", []))
                + ["REPORT_CONSUMER_V7_NOT_ACTIVATED"]
            ),
            "protocol_id": report_consumer_v6.get("protocol_id"),
            "future_evaluation_id": report_consumer_v6.get(
                "future_evaluation_id"
            ),
            "evaluation_not_before_date": report_consumer_v6.get(
                "evaluation_not_before_date"
            ),
            "precommit_declared_at_utc": report_consumer_v6.get(
                "precommit_declared_at_utc"
            ),
            "evaluated_lags": list(precommit_gate_v7.get("evaluated_lags", [])),
            "omnibus_band_lags": list(
                precommit_gate_v7.get("omnibus_band_lags", [])
            ),
            "maximum_evaluated_lag": precommit_gate_v7.get(
                "maximum_evaluated_lag"
            ),
            "maximum_allowed_lag_band_quadratic_energy": precommit_gate_v7.get(
                "maximum_allowed_lag_band_quadratic_energy"
            ),
            "maximum_observed_lag_band_quadratic_energy": precommit_gate_v7.get(
                "maximum_observed_lag_band_quadratic_energy"
            ),
            "fold_count": precommit_gate_v7.get("fold_count"),
            "unstable_identity_count": precommit_gate_v7.get(
                "unstable_identity_count"
            ),
            "facts": {
                **_facts(),
                "cross_consumer_source_hashes_bound": True,
                "finite_horizon_omnibus_guard_bound": positive,
                "local_precommit_binding_complete": positive,
                "omnibus_gate_v1_verified": True,
                "omnibus_quadratic_energy_threshold_passed": bool(
                    source_facts.get("omnibus_quadratic_energy_threshold_passed")
                ),
                "precommit_gate_v7_verified": True,
                "report_consumer_v6_verified": True,
                "residual_order_gate_v3_verified": True,
            },
        }
    )
    return _seal(projection)


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    rebuilt = consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7(
        *args,
        **expected,
    )
    return strict_json_contract_equal(document, rebuilt)
