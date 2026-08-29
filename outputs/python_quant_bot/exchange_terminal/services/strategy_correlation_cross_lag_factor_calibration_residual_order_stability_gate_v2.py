from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate import (
    GATE_SCHEMA as RESIDUAL_ORDER_GATE_V1_SCHEMA,
    STATIC_FINGERPRINT as RESIDUAL_ORDER_GATE_V1_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_stability_gate import (
    FOLD_COUNT,
    MIN_ROWS_PER_FOLD,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)


GATE_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-residual-order-"
    "stability-gate-candidate-v2"
)
STATIC_FINGERPRINT = (
    "20260901-cross-lag-factor-calibration-residual-order-stability-gate-2"
)
EVALUATED_LAGS = (1, 2)
MAX_ABSOLUTE_MULTI_LAG_RESIDUAL_ENERGY_COUPLING = Decimal("0.8")


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value.normalize(), "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_calibration_timing_attested": False,
        "future_evaluation_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "residual_order_independence_proven": False,
    }


def _unknown_facts() -> dict[str, bool]:
    return {
        "residual_multi_lag_order_threshold_passed": False,
        "residual_order_gate_v1_verified": False,
        "residual_order_independence_proven": False,
        "residual_order_protocol_pinned": True,
        "source_gate_block_relaxed": False,
        "source_hashes_cross_bound": False,
    }


def _base_projection() -> dict[str, Any]:
    return {
        "fold_count": FOLD_COUNT,
        "minimum_rows_per_fold": MIN_ROWS_PER_FOLD,
        "evaluated_lags": list(EVALUATED_LAGS),
        "maximum_evaluated_lag": max(EVALUATED_LAGS),
        "maximum_allowed_absolute_multi_lag_residual_energy_coupling": (
            _canonical_decimal(
                MAX_ABSOLUTE_MULTI_LAG_RESIDUAL_ENERGY_COUPLING
            )
        ),
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "gate_hash")


def _deduplicate(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _unknown(reason: str, source_state: str) -> dict[str, Any]:
    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": source_state,
            "gate_decision": "UNKNOWN",
            "gate_reason": reason,
            **_base_projection(),
            "minimum_observed_fold_rows": None,
            "maximum_observed_fold_rows": None,
            "maximum_observed_absolute_multi_lag_residual_energy_coupling": None,
            "unstable_identity_count": None,
            "zero_lag_energy_identity_fold_lag_count": None,
            "private_fold_multi_lag_residual_order_ledger_hash": None,
            "source_residual_order_gate_v1_decision": None,
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


def _source_blocked(residual_order_gate_v1: dict[str, Any]) -> dict[str, Any]:
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("RESIDUAL_ORDER_V2_INTERNAL_AUTHORITY_INVALID", "INVALID")
    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": "BLOCK",
            "gate_reason": "SOURCE_RESIDUAL_ORDER_GATE_V1_BLOCKED",
            **_base_projection(),
            "minimum_observed_fold_rows": None,
            "maximum_observed_fold_rows": None,
            "maximum_observed_absolute_multi_lag_residual_energy_coupling": None,
            "unstable_identity_count": None,
            "zero_lag_energy_identity_fold_lag_count": None,
            "private_fold_multi_lag_residual_order_ledger_hash": None,
            "source_residual_order_gate_v1_decision": residual_order_gate_v1[
                "gate_decision"
            ],
            "source_residual_order_gate_v1_hash": residual_order_gate_v1[
                "gate_hash"
            ],
            "source_beta_stability_gate_hash": residual_order_gate_v1[
                "source_beta_stability_gate_hash"
            ],
            "source_replay_hash": residual_order_gate_v1["source_replay_hash"],
            "source_registration_hash": residual_order_gate_v1[
                "source_registration_hash"
            ],
            "source_calibration_observations_hash": residual_order_gate_v1[
                "source_calibration_observations_hash"
            ],
            "facts": {
                **_unknown_facts(),
                "residual_order_gate_v1_verified": True,
                "source_hashes_cross_bound": True,
            },
            "blockers": _deduplicate(
                [
                    *residual_order_gate_v1["blockers"],
                    "SOURCE_RESIDUAL_ORDER_GATE_V1_BLOCKED",
                    "RESIDUAL_MULTI_LAG_ORDER_STABILITY_CANDIDATE_NOT_ACTIVATED",
                ]
            ),
            "authority": authority,
        }
    )


def _folds(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    base, remainder = divmod(len(rows), FOLD_COUNT)
    sizes = [base + (1 if index < remainder else 0) for index in range(FOLD_COUNT)]
    output: list[list[dict[str, Any]]] = []
    cursor = 0
    for size in sizes:
        output.append(rows[cursor : cursor + size])
        cursor += size
    return output


def _decimal(value: Any) -> Decimal:
    if type(value) not in (int, float, str) or type(value) is bool:
        raise ValueError("non-native calibration number")
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise ValueError("non-finite calibration number")
    return parsed


def _evaluate_multi_lag_order(
    registration: dict[str, Any], calibration_observations: dict[str, Any]
) -> dict[str, Any]:
    identities = registration["identity_order"]
    registered = {
        identity: _decimal(registration["beta_by_identity"][identity])
        for identity in identities
    }
    fold_rows = _folds(calibration_observations["rows"])
    if min(map(len, fold_rows)) < MIN_ROWS_PER_FOLD:
        raise ValueError("insufficient rows per multi-lag residual-order fold")

    maximum_coupling = Decimal("0")
    unstable_identities: set[str] = set()
    zero_count = 0
    private_ledger: list[dict[str, Any]] = []

    with localcontext() as context:
        context.prec = 50
        for identity in identities:
            identity_maximum = Decimal("0")
            fold_ledger: list[dict[str, Any]] = []
            for fold_index, rows in enumerate(fold_rows):
                residuals = [
                    _decimal(row["returns"][identity])
                    - registered[identity] * _decimal(row["factor_return"])
                    for row in rows
                ]
                lag_ledger: list[dict[str, Any]] = []
                for lag in EVALUATED_LAGS:
                    adjacent = list(zip(residuals, residuals[lag:]))
                    lag_product = sum(
                        (left * right for left, right in adjacent), Decimal("0")
                    )
                    lag_pair_energy = sum(
                        (
                            left * left + right * right
                            for left, right in adjacent
                        ),
                        Decimal("0"),
                    )
                    if lag_pair_energy == 0:
                        coupling = Decimal("0")
                        zero_count += 1
                    else:
                        coupling = (
                            Decimal("2") * abs(lag_product) / lag_pair_energy
                        )
                    if coupling < 0 or coupling > 1:
                        raise ArithmeticError("multi-lag coupling outside unit interval")
                    identity_maximum = max(identity_maximum, coupling)
                    maximum_coupling = max(maximum_coupling, coupling)
                    lag_ledger.append(
                        {
                            "lag": lag,
                            "lag_pair_count": len(adjacent),
                            "lag_pair_energy": _canonical_decimal(lag_pair_energy),
                            "absolute_residual_energy_coupling": (
                                _canonical_decimal(coupling)
                            ),
                        }
                    )
                fold_ledger.append(
                    {
                        "fold_index": fold_index,
                        "row_count": len(rows),
                        "lags": lag_ledger,
                    }
                )
            if (
                identity_maximum
                > MAX_ABSOLUTE_MULTI_LAG_RESIDUAL_ENERGY_COUPLING
            ):
                unstable_identities.add(identity)
            private_ledger.append(
                {
                    "identity": identity,
                    "maximum_absolute_multi_lag_residual_energy_coupling": (
                        _canonical_decimal(identity_maximum)
                    ),
                    "folds": fold_ledger,
                }
            )

    return {
        "minimum_observed_fold_rows": min(map(len, fold_rows)),
        "maximum_observed_fold_rows": max(map(len, fold_rows)),
        "maximum_observed_absolute_multi_lag_residual_energy_coupling": (
            _canonical_decimal(maximum_coupling)
        ),
        "unstable_identity_count": len(unstable_identities),
        "zero_lag_energy_identity_fold_lag_count": zero_count,
        "private_fold_multi_lag_residual_order_ledger_hash": (
            strict_canonical_hash(private_ledger)
        ),
    }


def _observed(
    residual_order_gate_v1: dict[str, Any], metrics: dict[str, Any]
) -> dict[str, Any]:
    stable = metrics["unstable_identity_count"] == 0
    decision = (
        "RESIDUAL_MULTI_LAG_ORDER_STABLE_CANDIDATE" if stable else "BLOCK"
    )
    reason = (
        "NO_PREREGISTERED_MULTI_LAG_RESIDUAL_ORDER_INSTABILITY_DETECTED"
        if stable
        else "CALIBRATION_MULTI_LAG_RESIDUAL_ORDER_INSTABILITY_DETECTED"
    )
    blockers = [*residual_order_gate_v1["blockers"]]
    if not stable:
        blockers.append(reason)
    blockers.append("RESIDUAL_MULTI_LAG_ORDER_STABILITY_CANDIDATE_NOT_ACTIVATED")
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("RESIDUAL_ORDER_V2_INTERNAL_AUTHORITY_INVALID", "INVALID")
    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": decision,
            "gate_reason": reason,
            **_base_projection(),
            **metrics,
            "source_residual_order_gate_v1_decision": residual_order_gate_v1[
                "gate_decision"
            ],
            "source_residual_order_gate_v1_hash": residual_order_gate_v1[
                "gate_hash"
            ],
            "source_beta_stability_gate_hash": residual_order_gate_v1[
                "source_beta_stability_gate_hash"
            ],
            "source_replay_hash": residual_order_gate_v1["source_replay_hash"],
            "source_registration_hash": residual_order_gate_v1[
                "source_registration_hash"
            ],
            "source_calibration_observations_hash": residual_order_gate_v1[
                "source_calibration_observations_hash"
            ],
            "facts": {
                "residual_multi_lag_order_threshold_passed": stable,
                "residual_order_gate_v1_verified": True,
                "residual_order_independence_proven": False,
                "residual_order_protocol_pinned": True,
                "source_gate_block_relaxed": False,
                "source_hashes_cross_bound": True,
            },
            "blockers": _deduplicate(blockers),
            "authority": authority,
        }
    )


def evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2(
    residual_order_gate_v1: Any,
    beta_stability_gate: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_residual_order_gate_v1_hash: Any,
    expected_beta_stability_gate_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> dict[str, Any]:
    try:
        if residual_order_gate_v1 is None:
            if (
                type(expected_residual_order_gate_v1_hash) is not str
                or expected_residual_order_gate_v1_hash != ""
            ):
                return _unknown("RESIDUAL_ORDER_GATE_V1_INVALID", "INVALID")
            return _unknown("RESIDUAL_ORDER_GATE_V1_MISSING", "MISSING")
        if (
            type(residual_order_gate_v1) is not dict
            or not strict_sha256(expected_residual_order_gate_v1_hash)
        ):
            return _unknown("RESIDUAL_ORDER_GATE_V1_INVALID", "INVALID")
        if (
            residual_order_gate_v1.get("schema_version")
            != RESIDUAL_ORDER_GATE_V1_SCHEMA
            or residual_order_gate_v1.get("static_fingerprint")
            != RESIDUAL_ORDER_GATE_V1_STATIC_FINGERPRINT
        ):
            return _unknown("RESIDUAL_ORDER_GATE_V1_UNSUPPORTED", "UNSUPPORTED")
        if residual_order_gate_v1.get("gate_hash") != expected_residual_order_gate_v1_hash:
            return _unknown("RESIDUAL_ORDER_GATE_V1_INVALID", "INVALID")

        verified = verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate(
            residual_order_gate_v1,
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
        if verified is not True:
            return _unknown("RESIDUAL_ORDER_GATE_V1_INVALID", "INVALID")
        if residual_order_gate_v1["source_state"] != "OBSERVED":
            return _unknown("RESIDUAL_ORDER_GATE_V1_NOT_OBSERVED", "UNKNOWN")
        if residual_order_gate_v1["gate_decision"] == "BLOCK":
            return _source_blocked(residual_order_gate_v1)
        if (
            residual_order_gate_v1["gate_decision"]
            != "RESIDUAL_ORDER_STABLE_CANDIDATE"
        ):
            return _unknown("RESIDUAL_ORDER_GATE_V1_INVALID", "INVALID")
        metrics = _evaluate_multi_lag_order(
            residualization_registration, calibration_observations
        )
        return _observed(residual_order_gate_v1, metrics)
    except (
        InvalidOperation,
        KeyError,
        TypeError,
        ValueError,
        ArithmeticError,
        OverflowError,
    ):
        return _unknown("RESIDUAL_ORDER_V2_EVALUATION_INVALID", "INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2(
    document: Any,
    residual_order_gate_v1: Any,
    beta_stability_gate: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_residual_order_gate_v1_hash: Any,
    expected_beta_stability_gate_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    try:
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2(
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
        return strict_json_contract_equal(document, rebuilt)
    except (
        InvalidOperation,
        KeyError,
        TypeError,
        ValueError,
        ArithmeticError,
        OverflowError,
    ):
        return False
