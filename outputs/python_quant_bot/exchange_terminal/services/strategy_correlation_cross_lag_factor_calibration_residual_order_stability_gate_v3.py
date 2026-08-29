from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2 import (
    _folds as _source_folds,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-residual-order-stability-gate-candidate-v3"
)
STATIC_FINGERPRINT = (
    "20260906-cross-lag-factor-calibration-residual-order-stability-gate-3"
)
SOURCE_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-residual-order-stability-gate-candidate-v2"
)
SOURCE_POSITIVE_DECISION = "RESIDUAL_MULTI_LAG_ORDER_STABLE_CANDIDATE"
POSITIVE_DECISION = "RESIDUAL_THREE_LAG_ORDER_STABLE_CANDIDATE"
BLOCK_DECISION = "RESIDUAL_THREE_LAG_ORDER_BLOCK"
EVALUATED_LAGS = (1, 2, 3)
NEWLY_EVALUATED_LAGS = (3,)
RESIDUAL_ORDER_CEILING = Decimal("0.8")
DECIMAL_PRECISION = 50


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean is not a decimal")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid decimal") from exc
    if not result.is_finite():
        raise ValueError("decimal must be finite")
    return result


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _deduplicate(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_calibration_timing_attested": False,
        "future_evaluation_allowed": True,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "residual_order_independence_proven": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "lag_three_protocol_pinned": True,
        "residual_order_independence_proven": False,
        "residual_order_threshold_passed": False,
        "source_gate_block_relaxed": False,
        "source_hashes_cross_bound": False,
        "source_v2_verified": False,
    }


def _base_projection() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source_state": "UNKNOWN",
        "source_residual_order_gate_v2_decision": None,
        "source_residual_order_gate_v2_hash": None,
        "source_residual_order_gate_v1_hash": None,
        "source_beta_stability_gate_hash": None,
        "source_replay_hash": None,
        "source_registration_hash": None,
        "source_calibration_observations_hash": None,
        "gate_decision": "UNKNOWN",
        "gate_reason": "SOURCE_NOT_EVALUATED",
        "blockers": ["SOURCE_NOT_EVALUATED"],
        "evaluated_lags": list(EVALUATED_LAGS),
        "newly_evaluated_lags": list(NEWLY_EVALUATED_LAGS),
        "maximum_allowed_absolute_residual_energy_coupling": _canonical_decimal(
            RESIDUAL_ORDER_CEILING
        ),
        "maximum_observed_absolute_three_lag_residual_energy_coupling": None,
        "maximum_observed_absolute_lag_three_residual_energy_coupling": None,
        "minimum_observed_fold_rows": None,
        "maximum_observed_fold_rows": None,
        "fold_count": None,
        "unstable_identity_count": None,
        "zero_lag_energy_identity_fold_count": None,
        "private_fold_lag_three_residual_order_ledger_hash": None,
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
    return (
        isinstance(expected, str)
        and isinstance(actual, str)
        and expected == actual
    )


def _lag_three_coupling(values: list[Decimal]) -> tuple[Decimal, bool]:
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        lag = 3
        numerator = Decimal(2) * abs(
            sum(
                values[index] * values[index - lag]
                for index in range(lag, len(values))
            )
        )
        denominator = sum(
            values[index] ** 2 + values[index - lag] ** 2
            for index in range(lag, len(values))
        )
        if denominator == 0:
            return Decimal(0), True
        return numerator / denominator, False


def _evaluate_lag_three(
    registration: dict[str, Any],
    calibration_observations: dict[str, Any],
) -> dict[str, Any]:
    identities = registration["identity_order"]
    beta_by_identity = registration["beta_by_identity"]
    folds = _source_folds(calibration_observations["rows"])
    ledger: list[dict[str, Any]] = []
    maximum = Decimal(0)
    unstable_identities: set[str] = set()
    zero_energy_count = 0
    fold_sizes: list[int] = []

    for fold_number, fold in enumerate(folds, start=1):
        fold_sizes.append(len(fold))
        for identity in identities:
            with localcontext() as context:
                context.prec = DECIMAL_PRECISION
                beta = _decimal(beta_by_identity[identity])
                residuals = [
                    _decimal(row["returns"][identity])
                    - beta * _decimal(row["factor_return"])
                    for row in fold
                ]
                coupling, zero_energy = _lag_three_coupling(residuals)
            maximum = max(maximum, coupling)
            if coupling > RESIDUAL_ORDER_CEILING:
                unstable_identities.add(identity)
            if zero_energy:
                zero_energy_count += 1
            ledger.append(
                {
                    "absolute_lag_three_residual_energy_coupling": _canonical_decimal(
                        coupling
                    ),
                    "fold_number": fold_number,
                    "identity": identity,
                    "lag": 3,
                    "row_count": len(fold),
                    "zero_lag_energy": zero_energy,
                }
            )

    return {
        "fold_count": len(folds),
        "maximum_observed_absolute_lag_three_residual_energy_coupling": _canonical_decimal(
            maximum
        ),
        "maximum_observed_fold_rows": max(fold_sizes),
        "minimum_observed_fold_rows": min(fold_sizes),
        "private_fold_lag_three_residual_order_ledger_hash": strict_canonical_hash(
            ledger
        ),
        "unstable_identity_count": len(unstable_identities),
        "zero_lag_energy_identity_fold_count": zero_energy_count,
    }


def _source_blocked(source: dict[str, Any]) -> dict[str, Any]:
    projection = _base_projection()
    projection.update(
        {
            "source_state": "VERIFIED",
            "source_residual_order_gate_v2_decision": source.get("gate_decision"),
            "source_residual_order_gate_v2_hash": source.get("gate_hash"),
            "source_residual_order_gate_v1_hash": source.get(
                "source_residual_order_gate_v1_hash"
            ),
            "source_beta_stability_gate_hash": source.get(
                "source_beta_stability_gate_hash"
            ),
            "source_replay_hash": source.get("source_replay_hash"),
            "source_registration_hash": source.get("source_registration_hash"),
            "source_calibration_observations_hash": source.get(
                "source_calibration_observations_hash"
            ),
            "gate_decision": BLOCK_DECISION,
            "gate_reason": "SOURCE_V2_BLOCKED",
            "blockers": _deduplicate(
                list(source.get("blockers", [])) + ["SOURCE_V2_BLOCKED"]
            ),
            "maximum_observed_absolute_three_lag_residual_energy_coupling": source.get(
                "maximum_observed_absolute_multi_lag_residual_energy_coupling"
            ),
            "minimum_observed_fold_rows": source.get(
                "minimum_observed_fold_rows"
            ),
            "maximum_observed_fold_rows": source.get(
                "maximum_observed_fold_rows"
            ),
            "fold_count": source.get("fold_count"),
            "unstable_identity_count": source.get("unstable_identity_count"),
            "facts": {
                **_facts(),
                "source_hashes_cross_bound": True,
                "source_v2_verified": True,
            },
        }
    )
    return _seal(projection)


def evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3(
    residual_order_gate_v2: Any,
    residual_order_gate_v1: Any,
    beta_stability_gate: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_residual_order_gate_v2_hash: Any,
    expected_residual_order_gate_v1_hash: Any,
    expected_beta_stability_gate_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> dict[str, Any]:
    if not isinstance(residual_order_gate_v2, dict):
        return _unknown("MISSING_SOURCE_V2")
    if residual_order_gate_v2.get("schema_version") != SOURCE_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_SOURCE_V2", "UNSUPPORTED")
    if not _hash_matches(
        expected_residual_order_gate_v2_hash,
        residual_order_gate_v2.get("gate_hash"),
    ):
        return _unknown("EXPECTED_SOURCE_V2_HASH_MISMATCH")
    if not isinstance(residual_order_gate_v1, dict) or not _hash_matches(
        expected_residual_order_gate_v1_hash,
        residual_order_gate_v1.get("gate_hash"),
    ):
        return _unknown("SOURCE_V1_OR_HASH_INVALID")
    if not _hash_matches(
        expected_residual_order_gate_v1_hash,
        residual_order_gate_v2.get("source_residual_order_gate_v1_hash"),
    ):
        return _unknown("SOURCE_V1_V2_HASH_MISMATCH")

    source_verified = (
        verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2(
            residual_order_gate_v2,
            residual_order_gate_v1,
            beta_stability_gate,
            replay,
            residualization_registration,
            calibration_observations,
            expected_residual_order_gate_v1_hash=expected_residual_order_gate_v1_hash,
            expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_calibration_observations_hash,
        )
    )
    if not source_verified:
        return _unknown("SOURCE_V2_OR_CONTEXT_INVALID")

    source_decision = residual_order_gate_v2.get("gate_decision")
    if source_decision == "UNKNOWN":
        return _unknown("SOURCE_V2_UNKNOWN")
    if source_decision != SOURCE_POSITIVE_DECISION:
        return _source_blocked(residual_order_gate_v2)

    try:
        metrics = _evaluate_lag_three(
            residualization_registration,
            calibration_observations,
        )
        source_maximum = _decimal(
            residual_order_gate_v2[
                "maximum_observed_absolute_multi_lag_residual_energy_coupling"
            ]
        )
        lag_three_maximum = _decimal(
            metrics[
                "maximum_observed_absolute_lag_three_residual_energy_coupling"
            ]
        )
    except (KeyError, TypeError, ValueError):
        return _unknown("LAG_THREE_EVALUATION_INVALID")

    combined_maximum = max(source_maximum, lag_three_maximum)
    threshold_passed = combined_maximum <= RESIDUAL_ORDER_CEILING
    blockers = list(residual_order_gate_v2.get("blockers", []))
    blockers.extend(
        [
            "LAGS_ABOVE_THREE_UNRESOLVED",
            "RESIDUAL_ORDER_V3_NOT_ACTIVATED",
        ]
    )
    if not threshold_passed:
        blockers.append("LAG_THREE_RESIDUAL_ORDER_THRESHOLD_EXCEEDED")

    projection = _base_projection()
    projection.update(
        {
            "source_state": "VERIFIED",
            "source_residual_order_gate_v2_decision": source_decision,
            "source_residual_order_gate_v2_hash": residual_order_gate_v2["gate_hash"],
            "source_residual_order_gate_v1_hash": expected_residual_order_gate_v1_hash,
            "source_beta_stability_gate_hash": expected_beta_stability_gate_hash,
            "source_replay_hash": expected_replay_hash,
            "source_registration_hash": expected_registration_hash,
            "source_calibration_observations_hash": expected_calibration_observations_hash,
            "gate_decision": POSITIVE_DECISION if threshold_passed else BLOCK_DECISION,
            "gate_reason": (
                "LAGS_ONE_TO_THREE_AT_OR_BELOW_CEILING"
                if threshold_passed
                else "LAG_THREE_RESIDUAL_ORDER_ABOVE_CEILING"
            ),
            "blockers": _deduplicate(blockers),
            "maximum_observed_absolute_three_lag_residual_energy_coupling": _canonical_decimal(
                combined_maximum
            ),
            **metrics,
            "facts": {
                **_facts(),
                "residual_order_threshold_passed": threshold_passed,
                "source_hashes_cross_bound": True,
                "source_v2_verified": True,
            },
        }
    )
    return _seal(projection)


def verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3(
    document: Any,
    residual_order_gate_v2: Any,
    residual_order_gate_v1: Any,
    beta_stability_gate: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_residual_order_gate_v2_hash: Any,
    expected_residual_order_gate_v1_hash: Any,
    expected_beta_stability_gate_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3(
        residual_order_gate_v2,
        residual_order_gate_v1,
        beta_stability_gate,
        replay,
        residualization_registration,
        calibration_observations,
        expected_residual_order_gate_v2_hash=expected_residual_order_gate_v2_hash,
        expected_residual_order_gate_v1_hash=expected_residual_order_gate_v1_hash,
        expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
        expected_replay_hash=expected_replay_hash,
        expected_registration_hash=expected_registration_hash,
        expected_calibration_observations_hash=expected_calibration_observations_hash,
    )
    return strict_json_contract_equal(document, rebuilt)
