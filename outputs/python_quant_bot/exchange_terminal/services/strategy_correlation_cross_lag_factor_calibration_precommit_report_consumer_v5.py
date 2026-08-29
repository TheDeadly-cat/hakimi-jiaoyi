from __future__ import annotations

from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5 import (
    GATE_SCHEMA as PRECOMMIT_GATE_V5_SCHEMA,
    STATIC_FINGERPRINT as PRECOMMIT_GATE_V5_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)


REPORT_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-report-"
    "consumer-verification-v5"
)
STATIC_FINGERPRINT = (
    "20260903-cross-lag-factor-calibration-precommit-report-consumer-5"
)


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


def _unknown_facts() -> dict[str, bool]:
    return {
        "aggregate_only": True,
        "cross_gate_source_hashes_bound": False,
        "local_precommit_binding_complete": False,
        "precommit_gate_v5_verified": False,
        "residual_order_independence_proven": False,
        "source_gate_block_relaxed": False,
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "verification_hash")


def _unknown(reason: str, source_state: str) -> dict[str, Any]:
    return _seal(
        {
            "schema_version": REPORT_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": source_state,
            "verification_state": "UNKNOWN",
            "verification_reason": reason,
            "source_gate_decision": None,
            "protocol_id": None,
            "future_evaluation_id": None,
            "precommit_declared_at_utc": None,
            "evaluation_not_before_date": None,
            "fold_count": None,
            "evaluated_lags": None,
            "maximum_evaluated_lag": None,
            "maximum_allowed_absolute_multi_lag_residual_energy_coupling": None,
            "maximum_observed_absolute_multi_lag_residual_energy_coupling": None,
            "residual_multi_lag_order_unstable_identity_count": None,
            "source_gate_hash": None,
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


def _deduplicate(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _observed(source_gate: dict[str, Any]) -> dict[str, Any]:
    decision = source_gate["gate_decision"]
    if decision == "BOUND_LOCAL_ONLY_MULTI_LAG_STABILITY_GUARDED":
        verification_state = "VERIFIED_LOCAL_BINDING"
        reason = "PRECOMMIT_V5_LOCAL_BINDING_VERIFIED"
    elif decision == "BLOCK":
        verification_state = "VERIFIED_BLOCK"
        reason = "PRECOMMIT_V5_BLOCK_VERIFIED"
    else:
        return _unknown("PRECOMMIT_GATE_V5_NOT_OBSERVED_FOR_REPORT", "UNKNOWN")

    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("REPORT_CONSUMER_V5_INTERNAL_AUTHORITY_INVALID", "INVALID")
    blockers = _deduplicate(
        [*source_gate["blockers"], "REPORT_CONSUMER_V5_NOT_ACTIVATED"]
    )
    return _seal(
        {
            "schema_version": REPORT_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "verification_state": verification_state,
            "verification_reason": reason,
            "source_gate_decision": decision,
            "protocol_id": source_gate["protocol_id"],
            "future_evaluation_id": source_gate["future_evaluation_id"],
            "precommit_declared_at_utc": source_gate[
                "precommit_declared_at_utc"
            ],
            "evaluation_not_before_date": source_gate[
                "evaluation_not_before_date"
            ],
            "fold_count": source_gate["fold_count"],
            "evaluated_lags": source_gate["evaluated_lags"],
            "maximum_evaluated_lag": source_gate["maximum_evaluated_lag"],
            "maximum_allowed_absolute_multi_lag_residual_energy_coupling": source_gate[
                "maximum_allowed_absolute_multi_lag_residual_energy_coupling"
            ],
            "maximum_observed_absolute_multi_lag_residual_energy_coupling": source_gate[
                "maximum_observed_absolute_multi_lag_residual_energy_coupling"
            ],
            "residual_multi_lag_order_unstable_identity_count": source_gate[
                "residual_multi_lag_order_unstable_identity_count"
            ],
            "source_gate_hash": source_gate["gate_hash"],
            "source_residual_order_gate_v2_hash": source_gate[
                "source_residual_order_gate_v2_hash"
            ],
            "source_residual_order_gate_v1_hash": source_gate[
                "source_residual_order_gate_v1_hash"
            ],
            "source_beta_stability_gate_hash": source_gate[
                "source_beta_stability_gate_hash"
            ],
            "source_replay_hash": source_gate["source_replay_hash"],
            "source_registration_hash": source_gate[
                "source_registration_hash"
            ],
            "source_calibration_observations_hash": source_gate[
                "source_calibration_observations_hash"
            ],
            "facts": {
                "aggregate_only": True,
                "cross_gate_source_hashes_bound": source_gate["facts"][
                    "cross_gate_source_hashes_bound"
                ],
                "local_precommit_binding_complete": source_gate["facts"][
                    "local_precommit_binding_complete"
                ],
                "precommit_gate_v5_verified": True,
                "residual_order_independence_proven": False,
                "source_gate_block_relaxed": False,
            },
            "blockers": blockers,
            "authority": authority,
        }
    )


def consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5(
    precommit_gate_v5: Any,
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
    expected_precommit_gate_v5_hash: Any,
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
    try:
        if precommit_gate_v5 is None:
            if (
                type(expected_precommit_gate_v5_hash) is not str
                or expected_precommit_gate_v5_hash != ""
            ):
                return _unknown("PRECOMMIT_GATE_V5_INVALID", "INVALID")
            return _unknown("PRECOMMIT_GATE_V5_MISSING", "MISSING")
        if (
            type(precommit_gate_v5) is not dict
            or not strict_sha256(expected_precommit_gate_v5_hash)
        ):
            return _unknown("PRECOMMIT_GATE_V5_INVALID", "INVALID")
        if (
            precommit_gate_v5.get("schema_version") != PRECOMMIT_GATE_V5_SCHEMA
            or precommit_gate_v5.get("static_fingerprint")
            != PRECOMMIT_GATE_V5_STATIC_FINGERPRINT
        ):
            return _unknown("PRECOMMIT_GATE_V5_UNSUPPORTED", "UNSUPPORTED")
        if precommit_gate_v5.get("gate_hash") != expected_precommit_gate_v5_hash:
            return _unknown("PRECOMMIT_GATE_V5_INVALID", "INVALID")

        verified = verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5(
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
            expected_report_hash=expected_source_report_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        if verified is not True:
            return _unknown("PRECOMMIT_GATE_V5_INVALID", "INVALID")
        if precommit_gate_v5["source_state"] != "OBSERVED":
            return _unknown("PRECOMMIT_GATE_V5_NOT_OBSERVED", "UNKNOWN")
        return _observed(precommit_gate_v5)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return _unknown("PRECOMMIT_GATE_V5_INVALID", "INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5(
    document: Any,
    precommit_gate_v5: Any,
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
    **expected: Any,
) -> bool:
    try:
        rebuilt = consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5(
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
            **expected,
        )
        return strict_json_contract_equal(document, rebuilt)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return False
