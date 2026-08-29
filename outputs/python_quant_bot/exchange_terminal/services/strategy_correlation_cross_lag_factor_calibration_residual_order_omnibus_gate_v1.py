from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2 import (
    _folds as _source_folds,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3 import (
    DECIMAL_PRECISION,
    POSITIVE_DECISION as SOURCE_POSITIVE_DECISION,
    SCHEMA_VERSION as SOURCE_SCHEMA_VERSION,
    _canonical_decimal,
    _decimal,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-residual-order-omnibus-gate-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260911-cross-lag-factor-calibration-residual-order-omnibus-gate-1"
)
POSITIVE_DECISION = "RESIDUAL_FINITE_HORIZON_OMNIBUS_STABLE_CANDIDATE"
BLOCK_DECISION = "RESIDUAL_FINITE_HORIZON_OMNIBUS_BLOCK"
EVALUATED_LAGS = (1, 2, 3, 4, 5, 6)
OMNIBUS_BAND_LAGS = (4, 5, 6)
BAND_QUADRATIC_ENERGY_CEILING = Decimal("0.64")


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
        "finite_horizon_only": True,
        "lag_band_protocol_pinned": True,
        "omnibus_quadratic_energy_threshold_passed": False,
        "residual_order_independence_proven": False,
        "source_gate_block_relaxed": False,
        "source_hashes_cross_bound": False,
        "source_v3_verified": False,
    }


def _base_projection() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source_state": "UNKNOWN",
        "source_residual_order_gate_v3_decision": None,
        "source_residual_order_gate_v3_hash": None,
        "source_residual_order_gate_v2_hash": None,
        "source_residual_order_gate_v1_hash": None,
        "source_beta_stability_gate_hash": None,
        "source_replay_hash": None,
        "source_registration_hash": None,
        "source_calibration_observations_hash": None,
        "source_maximum_observed_absolute_three_lag_residual_energy_coupling": None,
        "gate_decision": "UNKNOWN",
        "gate_reason": "SOURCE_NOT_EVALUATED",
        "blockers": ["SOURCE_NOT_EVALUATED"],
        "evaluated_lags": list(EVALUATED_LAGS),
        "omnibus_band_lags": list(OMNIBUS_BAND_LAGS),
        "maximum_evaluated_lag": max(EVALUATED_LAGS),
        "maximum_allowed_lag_band_quadratic_energy": _canonical_decimal(
            BAND_QUADRATIC_ENERGY_CEILING
        ),
        "maximum_observed_lag_band_quadratic_energy": None,
        "minimum_observed_fold_rows": None,
        "maximum_observed_fold_rows": None,
        "minimum_observed_lag_pairs": None,
        "maximum_observed_lag_pairs": None,
        "fold_count": None,
        "unstable_identity_count": None,
        "zero_energy_lag_measurement_count": None,
        "private_fold_lag_band_residual_order_ledger_hash": None,
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


def _lag_coupling(values: list[Decimal], lag: int) -> tuple[Decimal, bool]:
    if isinstance(lag, bool) or not isinstance(lag, int) or lag <= 0:
        raise ValueError("lag must be a positive integer")
    if len(values) <= lag:
        raise ValueError("lag requires at least one paired observation")
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
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


def _band_quadratic_energy(couplings: dict[int, Decimal]) -> Decimal:
    if set(couplings) != set(OMNIBUS_BAND_LAGS):
        raise ValueError("lag band is incomplete")
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        return sum(couplings[lag] ** 2 for lag in OMNIBUS_BAND_LAGS)


def _evaluate_band(
    registration: dict[str, Any],
    calibration_observations: dict[str, Any],
) -> dict[str, Any]:
    identities = registration["identity_order"]
    beta_by_identity = registration["beta_by_identity"]
    folds = _source_folds(calibration_observations["rows"])
    if not folds:
        raise ValueError("at least one fold is required")

    ledger: list[dict[str, Any]] = []
    maximum_energy = Decimal(0)
    unstable_identities: set[str] = set()
    zero_energy_count = 0
    fold_sizes: list[int] = []
    pair_counts: list[int] = []

    for fold_number, fold in enumerate(folds, start=1):
        if len(fold) <= max(OMNIBUS_BAND_LAGS):
            raise ValueError("fold is too short for the preregistered lag band")
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
                couplings: dict[int, Decimal] = {}
                zero_energy_by_lag: dict[str, bool] = {}
                for lag in OMNIBUS_BAND_LAGS:
                    coupling, zero_energy = _lag_coupling(residuals, lag)
                    couplings[lag] = coupling
                    zero_energy_by_lag[str(lag)] = zero_energy
                    pair_counts.append(len(residuals) - lag)
                    if zero_energy:
                        zero_energy_count += 1
                band_energy = _band_quadratic_energy(couplings)

            maximum_energy = max(maximum_energy, band_energy)
            if band_energy > BAND_QUADRATIC_ENERGY_CEILING:
                unstable_identities.add(identity)
            ledger.append(
                {
                    "absolute_residual_energy_coupling_by_lag": {
                        str(lag): _canonical_decimal(couplings[lag])
                        for lag in OMNIBUS_BAND_LAGS
                    },
                    "fold_number": fold_number,
                    "identity": identity,
                    "lag_band_quadratic_energy": _canonical_decimal(band_energy),
                    "lag_pair_count_by_lag": {
                        str(lag): len(residuals) - lag
                        for lag in OMNIBUS_BAND_LAGS
                    },
                    "row_count": len(fold),
                    "zero_energy_by_lag": zero_energy_by_lag,
                }
            )

    return {
        "fold_count": len(folds),
        "maximum_observed_lag_band_quadratic_energy": _canonical_decimal(
            maximum_energy
        ),
        "maximum_observed_fold_rows": max(fold_sizes),
        "minimum_observed_fold_rows": min(fold_sizes),
        "maximum_observed_lag_pairs": max(pair_counts),
        "minimum_observed_lag_pairs": min(pair_counts),
        "private_fold_lag_band_residual_order_ledger_hash": strict_canonical_hash(
            ledger
        ),
        "unstable_identity_count": len(unstable_identities),
        "zero_energy_lag_measurement_count": zero_energy_count,
    }


def _source_hashes_match(
    source: dict[str, Any],
    *,
    expected_residual_order_gate_v2_hash: Any,
    expected_residual_order_gate_v1_hash: Any,
    expected_beta_stability_gate_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    pairs = (
        (
            expected_residual_order_gate_v2_hash,
            source.get("source_residual_order_gate_v2_hash"),
        ),
        (
            expected_residual_order_gate_v1_hash,
            source.get("source_residual_order_gate_v1_hash"),
        ),
        (
            expected_beta_stability_gate_hash,
            source.get("source_beta_stability_gate_hash"),
        ),
        (expected_replay_hash, source.get("source_replay_hash")),
        (expected_registration_hash, source.get("source_registration_hash")),
        (
            expected_calibration_observations_hash,
            source.get("source_calibration_observations_hash"),
        ),
    )
    return all(_hash_matches(expected, actual) for expected, actual in pairs)


def _source_blocked(source: dict[str, Any]) -> dict[str, Any]:
    projection = _base_projection()
    projection.update(
        {
            "source_state": "VERIFIED",
            "source_residual_order_gate_v3_decision": source.get("gate_decision"),
            "source_residual_order_gate_v3_hash": source.get("gate_hash"),
            "source_residual_order_gate_v2_hash": source.get(
                "source_residual_order_gate_v2_hash"
            ),
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
            "source_maximum_observed_absolute_three_lag_residual_energy_coupling": source.get(
                "maximum_observed_absolute_three_lag_residual_energy_coupling"
            ),
            "gate_decision": BLOCK_DECISION,
            "gate_reason": "SOURCE_V3_BLOCKED",
            "blockers": _deduplicate(
                list(source.get("blockers", []))
                + [
                    "SOURCE_V3_BLOCKED",
                    "LAGS_ABOVE_SIX_UNRESOLVED",
                    "EXTERNAL_TIMING_UNRESOLVED",
                ]
            ),
            "facts": {
                **_facts(),
                "source_hashes_cross_bound": True,
                "source_v3_verified": True,
            },
        }
    )
    return _seal(projection)


def evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1(
    residual_order_gate_v3: Any,
    residual_order_gate_v2: Any,
    residual_order_gate_v1: Any,
    beta_stability_gate: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_residual_order_gate_v3_hash: Any,
    expected_residual_order_gate_v2_hash: Any,
    expected_residual_order_gate_v1_hash: Any,
    expected_beta_stability_gate_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> dict[str, Any]:
    if not isinstance(residual_order_gate_v3, dict):
        return _unknown("MISSING_SOURCE_V3")
    if residual_order_gate_v3.get("schema_version") != SOURCE_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_SOURCE_V3", "UNSUPPORTED")
    if not _hash_matches(
        expected_residual_order_gate_v3_hash,
        residual_order_gate_v3.get("gate_hash"),
    ):
        return _unknown("EXPECTED_SOURCE_V3_HASH_MISMATCH")
    if not isinstance(residual_order_gate_v2, dict) or not _hash_matches(
        expected_residual_order_gate_v2_hash,
        residual_order_gate_v2.get("gate_hash"),
    ):
        return _unknown("SOURCE_V2_OR_HASH_INVALID")
    if not isinstance(residual_order_gate_v1, dict) or not _hash_matches(
        expected_residual_order_gate_v1_hash,
        residual_order_gate_v1.get("gate_hash"),
    ):
        return _unknown("SOURCE_V1_OR_HASH_INVALID")

    source_verified = verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3(
        residual_order_gate_v3,
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
    if not source_verified:
        return _unknown("SOURCE_V3_OR_CONTEXT_INVALID")
    if not _source_hashes_match(
        residual_order_gate_v3,
        expected_residual_order_gate_v2_hash=expected_residual_order_gate_v2_hash,
        expected_residual_order_gate_v1_hash=expected_residual_order_gate_v1_hash,
        expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
        expected_replay_hash=expected_replay_hash,
        expected_registration_hash=expected_registration_hash,
        expected_calibration_observations_hash=expected_calibration_observations_hash,
    ):
        return _unknown("SOURCE_V3_HASH_CROSS_BIND_INVALID")

    source_decision = residual_order_gate_v3.get("gate_decision")
    if source_decision == "UNKNOWN":
        return _unknown("SOURCE_V3_UNKNOWN")
    if source_decision != SOURCE_POSITIVE_DECISION:
        return _source_blocked(residual_order_gate_v3)

    try:
        metrics = _evaluate_band(
            residualization_registration,
            calibration_observations,
        )
        maximum_energy = _decimal(
            metrics["maximum_observed_lag_band_quadratic_energy"]
        )
    except (KeyError, TypeError, ValueError):
        return _unknown("LAG_BAND_EVALUATION_INVALID")

    threshold_passed = maximum_energy <= BAND_QUADRATIC_ENERGY_CEILING
    blockers = list(residual_order_gate_v3.get("blockers", []))
    blockers.extend(
        [
            "LAGS_ABOVE_SIX_UNRESOLVED",
            "EXTERNAL_TIMING_UNRESOLVED",
            "RESIDUAL_ORDER_OMNIBUS_V1_NOT_ACTIVATED",
        ]
    )
    if not threshold_passed:
        blockers.append("LAG_BAND_QUADRATIC_ENERGY_EXCEEDED")

    projection = _base_projection()
    projection.update(
        {
            "source_state": "VERIFIED",
            "source_residual_order_gate_v3_decision": source_decision,
            "source_residual_order_gate_v3_hash": residual_order_gate_v3["gate_hash"],
            "source_residual_order_gate_v2_hash": expected_residual_order_gate_v2_hash,
            "source_residual_order_gate_v1_hash": expected_residual_order_gate_v1_hash,
            "source_beta_stability_gate_hash": expected_beta_stability_gate_hash,
            "source_replay_hash": expected_replay_hash,
            "source_registration_hash": expected_registration_hash,
            "source_calibration_observations_hash": expected_calibration_observations_hash,
            "source_maximum_observed_absolute_three_lag_residual_energy_coupling": residual_order_gate_v3.get(
                "maximum_observed_absolute_three_lag_residual_energy_coupling"
            ),
            "gate_decision": POSITIVE_DECISION if threshold_passed else BLOCK_DECISION,
            "gate_reason": (
                "LAG_BAND_FOUR_TO_SIX_AT_OR_BELOW_QUADRATIC_ENERGY_CEILING"
                if threshold_passed
                else "LAG_BAND_FOUR_TO_SIX_QUADRATIC_ENERGY_ABOVE_CEILING"
            ),
            "blockers": _deduplicate(blockers),
            **metrics,
            "facts": {
                **_facts(),
                "omnibus_quadratic_energy_threshold_passed": threshold_passed,
                "source_hashes_cross_bound": True,
                "source_v3_verified": True,
            },
        }
    )
    return _seal(projection)


def verify_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1(
    document: Any,
    residual_order_gate_v3: Any,
    residual_order_gate_v2: Any,
    residual_order_gate_v1: Any,
    beta_stability_gate: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_residual_order_gate_v3_hash: Any,
    expected_residual_order_gate_v2_hash: Any,
    expected_residual_order_gate_v1_hash: Any,
    expected_beta_stability_gate_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1(
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
    return strict_json_contract_equal(document, rebuilt)
