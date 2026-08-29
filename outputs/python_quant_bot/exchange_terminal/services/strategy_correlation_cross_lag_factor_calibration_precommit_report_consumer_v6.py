from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6 import (
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5 import (
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-report-consumer-verification-v6"
)
STATIC_FINGERPRINT = (
    "20260908-cross-lag-factor-calibration-precommit-report-consumer-6"
)
SOURCE_V6_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v6"
)
SOURCE_CONSUMER_V5_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-report-consumer-verification-v5"
)
SOURCE_V6_POSITIVE = "BOUND_LOCAL_ONLY_THREE_LAG_STABILITY_GUARDED"


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
        "local_precommit_binding_complete": False,
        "precommit_gate_v6_verified": False,
        "report_consumer_v5_verified": False,
        "residual_order_gate_v3_verified": False,
        "residual_order_independence_proven": False,
        "source_gate_block_relaxed": False,
    }


def _base_projection() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source_state": "UNKNOWN",
        "source_gate_decision": None,
        "source_v5_consumer_state": None,
        "source_gate_hash": None,
        "source_report_consumer_v5_hash": None,
        "source_precommit_gate_v5_hash": None,
        "source_residual_order_gate_v3_hash": None,
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
        "evaluated_lags": [1, 2, 3],
        "maximum_evaluated_lag": 3,
        "maximum_allowed_absolute_three_lag_residual_energy_coupling": None,
        "maximum_observed_absolute_three_lag_residual_energy_coupling": None,
        "residual_three_lag_order_unstable_identity_count": None,
        "fold_count": None,
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
    precommit_gate_v6: dict[str, Any],
    report_consumer_v5: dict[str, Any],
    residual_order_gate_v3: dict[str, Any],
    *,
    expected_precommit_gate_v5_hash: Any,
    expected_residual_order_gate_v3_hash: Any,
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
            report_consumer_v5.get("source_gate_hash"),
        ),
        (
            expected_residual_order_gate_v3_hash,
            precommit_gate_v6.get("source_residual_order_gate_v3_hash"),
            residual_order_gate_v3.get("gate_hash"),
        ),
        (
            expected_residual_order_gate_v2_hash,
            precommit_gate_v6.get("source_residual_order_gate_v2_hash"),
            report_consumer_v5.get("source_residual_order_gate_v2_hash"),
            residual_order_gate_v3.get("source_residual_order_gate_v2_hash"),
        ),
        (
            expected_residual_order_gate_v1_hash,
            precommit_gate_v6.get("source_residual_order_gate_v1_hash"),
            report_consumer_v5.get("source_residual_order_gate_v1_hash"),
            residual_order_gate_v3.get("source_residual_order_gate_v1_hash"),
        ),
        (
            expected_beta_stability_gate_hash,
            precommit_gate_v6.get("source_beta_stability_gate_hash"),
            report_consumer_v5.get("source_beta_stability_gate_hash"),
            residual_order_gate_v3.get("source_beta_stability_gate_hash"),
        ),
        (
            expected_replay_hash,
            precommit_gate_v6.get("source_replay_hash"),
            report_consumer_v5.get("source_replay_hash"),
            residual_order_gate_v3.get("source_replay_hash"),
        ),
        (
            expected_registration_hash,
            precommit_gate_v6.get("source_registration_hash"),
            report_consumer_v5.get("source_registration_hash"),
            residual_order_gate_v3.get("source_registration_hash"),
        ),
        (
            expected_calibration_observations_hash,
            precommit_gate_v6.get("source_calibration_observations_hash"),
            report_consumer_v5.get("source_calibration_observations_hash"),
            residual_order_gate_v3.get("source_calibration_observations_hash"),
        ),
    )
    return all(
        isinstance(group[0], str) and all(value == group[0] for value in group[1:])
        for group in bindings
    )


def consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6(
    precommit_gate_v6: Any,
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
    source_report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_precommit_gate_v6_hash: Any,
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
    expected_source_report_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> dict[str, Any]:
    if not isinstance(precommit_gate_v6, dict) or not isinstance(
        report_consumer_v5, dict
    ):
        return _unknown("MISSING_SOURCE")
    if precommit_gate_v6.get("schema_version") != SOURCE_V6_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_PRECOMMIT_GATE_V6", "UNSUPPORTED")
    if report_consumer_v5.get("schema_version") != SOURCE_CONSUMER_V5_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_REPORT_CONSUMER_V5", "UNSUPPORTED")
    if not _hash_matches(
        expected_precommit_gate_v6_hash,
        precommit_gate_v6.get("gate_hash"),
    ):
        return _unknown("EXPECTED_PRECOMMIT_GATE_V6_HASH_MISMATCH")
    if not _hash_matches(
        expected_report_consumer_v5_hash,
        report_consumer_v5.get("verification_hash"),
    ):
        return _unknown("EXPECTED_REPORT_CONSUMER_V5_HASH_MISMATCH")

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
        source_report,
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
        expected_report_hash=expected_source_report_hash,
        expected_replay_hash=expected_replay_hash,
        expected_registration_hash=expected_registration_hash,
        expected_calibration_observations_hash=expected_calibration_observations_hash,
    )
    v5_consumer_verified = verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5(
        report_consumer_v5,
        precommit_gate_v5,
        precommit_gate_v4,
        residual_order_gate_v2,
        precommit_gate_v3,
        residual_order_gate_v1,
        precommit_gate_v2,
        residual_energy_gate,
        precommit_gate_v1,
        beta_stability_gate,
        precommit_declaration,
        source_report,
        replay,
        residualization_registration,
        calibration_observations,
        expected_precommit_gate_v5_hash=expected_precommit_gate_v5_hash,
        expected_precommit_gate_v4_hash=expected_precommit_gate_v4_hash,
        expected_residual_order_gate_v2_hash=expected_residual_order_gate_v2_hash,
        expected_precommit_gate_v3_hash=expected_precommit_gate_v3_hash,
        expected_residual_order_gate_v1_hash=expected_residual_order_gate_v1_hash,
        expected_precommit_gate_v2_hash=expected_precommit_gate_v2_hash,
        expected_residual_energy_gate_hash=expected_residual_energy_gate_hash,
        expected_precommit_gate_v1_hash=expected_precommit_gate_v1_hash,
        expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
        expected_declaration_hash=expected_declaration_hash,
        expected_source_report_hash=expected_source_report_hash,
        expected_replay_hash=expected_replay_hash,
        expected_registration_hash=expected_registration_hash,
        expected_calibration_observations_hash=expected_calibration_observations_hash,
    )
    if not v6_verified or not v5_consumer_verified:
        return _unknown("SOURCE_OR_CONTEXT_INVALID")
    if not _cross_bindings_match(
        precommit_gate_v6,
        report_consumer_v5,
        residual_order_gate_v3,
        expected_precommit_gate_v5_hash=expected_precommit_gate_v5_hash,
        expected_residual_order_gate_v3_hash=expected_residual_order_gate_v3_hash,
        expected_residual_order_gate_v2_hash=expected_residual_order_gate_v2_hash,
        expected_residual_order_gate_v1_hash=expected_residual_order_gate_v1_hash,
        expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
        expected_replay_hash=expected_replay_hash,
        expected_registration_hash=expected_registration_hash,
        expected_calibration_observations_hash=expected_calibration_observations_hash,
    ):
        return _unknown("CROSS_CONSUMER_SOURCE_HASH_MISMATCH")

    gate_decision = precommit_gate_v6.get("gate_decision")
    v5_state = report_consumer_v5.get("verification_state")
    if gate_decision == "UNKNOWN" or v5_state == "UNKNOWN":
        return _unknown("SOURCE_STATE_UNKNOWN")
    if gate_decision == SOURCE_V6_POSITIVE and v5_state != "VERIFIED_LOCAL_BINDING":
        return _unknown("SOURCE_STATE_INCOMPATIBLE")
    positive = gate_decision == SOURCE_V6_POSITIVE
    verification_state = "VERIFIED_LOCAL_BINDING" if positive else "VERIFIED_BLOCK"
    verification_reason = (
        "PRECOMMIT_V6_LOCAL_BINDING_VERIFIED"
        if positive
        else "PRECOMMIT_V6_BLOCK_VERIFIED"
    )

    projection = _base_projection()
    projection.update(
        {
            "source_state": "OBSERVED",
            "source_gate_decision": gate_decision,
            "source_v5_consumer_state": v5_state,
            "source_gate_hash": expected_precommit_gate_v6_hash,
            "source_report_consumer_v5_hash": expected_report_consumer_v5_hash,
            "source_precommit_gate_v5_hash": expected_precommit_gate_v5_hash,
            "source_residual_order_gate_v3_hash": expected_residual_order_gate_v3_hash,
            "source_residual_order_gate_v2_hash": expected_residual_order_gate_v2_hash,
            "source_residual_order_gate_v1_hash": expected_residual_order_gate_v1_hash,
            "source_beta_stability_gate_hash": expected_beta_stability_gate_hash,
            "source_replay_hash": expected_replay_hash,
            "source_registration_hash": expected_registration_hash,
            "source_calibration_observations_hash": expected_calibration_observations_hash,
            "verification_state": verification_state,
            "verification_reason": verification_reason,
            "blockers": _deduplicate(
                list(report_consumer_v5.get("blockers", []))
                + list(precommit_gate_v6.get("blockers", []))
                + ["REPORT_CONSUMER_V6_NOT_ACTIVATED"]
            ),
            "protocol_id": report_consumer_v5.get("protocol_id"),
            "future_evaluation_id": report_consumer_v5.get("future_evaluation_id"),
            "evaluation_not_before_date": report_consumer_v5.get(
                "evaluation_not_before_date"
            ),
            "precommit_declared_at_utc": report_consumer_v5.get(
                "precommit_declared_at_utc"
            ),
            "maximum_allowed_absolute_three_lag_residual_energy_coupling": residual_order_gate_v3.get(
                "maximum_allowed_absolute_residual_energy_coupling"
            ),
            "maximum_observed_absolute_three_lag_residual_energy_coupling": residual_order_gate_v3.get(
                "maximum_observed_absolute_three_lag_residual_energy_coupling"
            ),
            "residual_three_lag_order_unstable_identity_count": residual_order_gate_v3.get(
                "unstable_identity_count"
            ),
            "fold_count": residual_order_gate_v3.get("fold_count"),
            "facts": {
                **_facts(),
                "cross_consumer_source_hashes_bound": True,
                "local_precommit_binding_complete": positive,
                "precommit_gate_v6_verified": True,
                "report_consumer_v5_verified": True,
                "residual_order_gate_v3_verified": True,
            },
        }
    )
    return _seal(projection)


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    rebuilt = consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6(
        *args,
        **expected,
    )
    return strict_json_contract_equal(document, rebuilt)
