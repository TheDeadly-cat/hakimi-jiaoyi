from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_stability_gate import (
    FOLD_COUNT,
    GATE_SCHEMA as BETA_STABILITY_GATE_SCHEMA,
    MIN_ROWS_PER_FOLD,
    STATIC_FINGERPRINT as BETA_STABILITY_GATE_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_stability_gate,
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
    "stability-gate-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260830-cross-lag-factor-calibration-residual-order-stability-gate-1"
)
MAX_ABSOLUTE_LAG_ONE_RESIDUAL_ENERGY_COUPLING = Decimal("0.8")


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
        "beta_stability_gate_verified": False,
        "residual_order_independence_proven": False,
        "residual_order_protocol_pinned": True,
        "residual_order_threshold_passed": False,
        "source_gate_block_relaxed": False,
        "source_hashes_cross_bound": False,
    }


def _base_projection() -> dict[str, Any]:
    return {
        "fold_count": FOLD_COUNT,
        "minimum_rows_per_fold": MIN_ROWS_PER_FOLD,
        "maximum_allowed_absolute_lag_one_residual_energy_coupling": (
            _canonical_decimal(MAX_ABSOLUTE_LAG_ONE_RESIDUAL_ENERGY_COUPLING)
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
            "maximum_observed_absolute_lag_one_residual_energy_coupling": None,
            "unstable_identity_count": None,
            "zero_lag_energy_identity_fold_count": None,
            "private_fold_residual_order_ledger_hash": None,
            "source_beta_stability_gate_decision": None,
            "source_beta_stability_gate_hash": None,
            "source_replay_hash": None,
            "source_registration_hash": None,
            "source_calibration_observations_hash": None,
            "facts": _unknown_facts(),
            "blockers": [reason],
            "authority": _authority(),
        }
    )


def _source_blocked(beta_stability_gate: dict[str, Any]) -> dict[str, Any]:
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("RESIDUAL_ORDER_INTERNAL_AUTHORITY_INVALID", "INVALID")
    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": "BLOCK",
            "gate_reason": "SOURCE_BETA_STABILITY_GATE_BLOCKED",
            **_base_projection(),
            "minimum_observed_fold_rows": None,
            "maximum_observed_fold_rows": None,
            "maximum_observed_absolute_lag_one_residual_energy_coupling": None,
            "unstable_identity_count": None,
            "zero_lag_energy_identity_fold_count": None,
            "private_fold_residual_order_ledger_hash": None,
            "source_beta_stability_gate_decision": beta_stability_gate[
                "gate_decision"
            ],
            "source_beta_stability_gate_hash": beta_stability_gate["gate_hash"],
            "source_replay_hash": beta_stability_gate["source_replay_hash"],
            "source_registration_hash": beta_stability_gate[
                "source_registration_hash"
            ],
            "source_calibration_observations_hash": beta_stability_gate[
                "source_calibration_observations_hash"
            ],
            "facts": {
                **_unknown_facts(),
                "beta_stability_gate_verified": True,
                "source_hashes_cross_bound": True,
            },
            "blockers": _deduplicate(
                [
                    *beta_stability_gate["blockers"],
                    "SOURCE_BETA_STABILITY_GATE_BLOCKED",
                    "RESIDUAL_ORDER_STABILITY_CANDIDATE_NOT_ACTIVATED",
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


def _evaluate_residual_order(
    registration: dict[str, Any], calibration_observations: dict[str, Any]
) -> dict[str, Any]:
    identities = registration["identity_order"]
    registered = {
        identity: _decimal(registration["beta_by_identity"][identity])
        for identity in identities
    }
    fold_rows = _folds(calibration_observations["rows"])
    if min(map(len, fold_rows)) < MIN_ROWS_PER_FOLD:
        raise ValueError("insufficient rows per residual-order fold")

    maximum_coupling = Decimal("0")
    unstable_identities: set[str] = set()
    zero_lag_energy_identity_fold_count = 0
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
                adjacent = list(zip(residuals, residuals[1:]))
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
                    zero_lag_energy_identity_fold_count += 1
                else:
                    coupling = Decimal("2") * abs(lag_product) / lag_pair_energy
                if coupling < 0 or coupling > 1:
                    raise ArithmeticError("residual-order coupling outside unit interval")
                identity_maximum = max(identity_maximum, coupling)
                maximum_coupling = max(maximum_coupling, coupling)
                fold_ledger.append(
                    {
                        "fold_index": fold_index,
                        "row_count": len(rows),
                        "lag_pair_energy": _canonical_decimal(lag_pair_energy),
                        "absolute_lag_one_residual_energy_coupling": (
                            _canonical_decimal(coupling)
                        ),
                    }
                )
            if identity_maximum > MAX_ABSOLUTE_LAG_ONE_RESIDUAL_ENERGY_COUPLING:
                unstable_identities.add(identity)
            private_ledger.append(
                {
                    "identity": identity,
                    "maximum_absolute_lag_one_residual_energy_coupling": (
                        _canonical_decimal(identity_maximum)
                    ),
                    "folds": fold_ledger,
                }
            )

    return {
        "minimum_observed_fold_rows": min(map(len, fold_rows)),
        "maximum_observed_fold_rows": max(map(len, fold_rows)),
        "maximum_observed_absolute_lag_one_residual_energy_coupling": (
            _canonical_decimal(maximum_coupling)
        ),
        "unstable_identity_count": len(unstable_identities),
        "zero_lag_energy_identity_fold_count": (
            zero_lag_energy_identity_fold_count
        ),
        "private_fold_residual_order_ledger_hash": strict_canonical_hash(
            private_ledger
        ),
    }


def _observed(
    beta_stability_gate: dict[str, Any], metrics: dict[str, Any]
) -> dict[str, Any]:
    stable = metrics["unstable_identity_count"] == 0
    decision = "RESIDUAL_ORDER_STABLE_CANDIDATE" if stable else "BLOCK"
    reason = (
        "NO_PREREGISTERED_RESIDUAL_ORDER_INSTABILITY_DETECTED"
        if stable
        else "CALIBRATION_RESIDUAL_ORDER_INSTABILITY_DETECTED"
    )
    blockers = [*beta_stability_gate["blockers"]]
    if not stable:
        blockers.append(reason)
    blockers.append("RESIDUAL_ORDER_STABILITY_CANDIDATE_NOT_ACTIVATED")
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("RESIDUAL_ORDER_INTERNAL_AUTHORITY_INVALID", "INVALID")
    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": decision,
            "gate_reason": reason,
            **_base_projection(),
            **metrics,
            "source_beta_stability_gate_decision": beta_stability_gate[
                "gate_decision"
            ],
            "source_beta_stability_gate_hash": beta_stability_gate["gate_hash"],
            "source_replay_hash": beta_stability_gate["source_replay_hash"],
            "source_registration_hash": beta_stability_gate[
                "source_registration_hash"
            ],
            "source_calibration_observations_hash": beta_stability_gate[
                "source_calibration_observations_hash"
            ],
            "facts": {
                "beta_stability_gate_verified": True,
                "residual_order_independence_proven": False,
                "residual_order_protocol_pinned": True,
                "residual_order_threshold_passed": stable,
                "source_gate_block_relaxed": False,
                "source_hashes_cross_bound": True,
            },
            "blockers": _deduplicate(blockers),
            "authority": authority,
        }
    )


def evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate(
    beta_stability_gate: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_beta_stability_gate_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> dict[str, Any]:
    try:
        if beta_stability_gate is None:
            if (
                type(expected_beta_stability_gate_hash) is not str
                or expected_beta_stability_gate_hash != ""
            ):
                return _unknown("H0_BETA_STABILITY_GATE_INVALID", "INVALID")
            return _unknown("H0_BETA_STABILITY_GATE_MISSING", "MISSING")
        if (
            type(beta_stability_gate) is not dict
            or not strict_sha256(expected_beta_stability_gate_hash)
        ):
            return _unknown("H0_BETA_STABILITY_GATE_INVALID", "INVALID")
        if (
            beta_stability_gate.get("schema_version")
            != BETA_STABILITY_GATE_SCHEMA
            or beta_stability_gate.get("static_fingerprint")
            != BETA_STABILITY_GATE_STATIC_FINGERPRINT
        ):
            return _unknown("H0_BETA_STABILITY_GATE_UNSUPPORTED", "UNSUPPORTED")
        if beta_stability_gate.get("gate_hash") != expected_beta_stability_gate_hash:
            return _unknown("H0_BETA_STABILITY_GATE_INVALID", "INVALID")

        verified = verify_strategy_correlation_cross_lag_factor_calibration_stability_gate(
            beta_stability_gate,
            replay,
            residualization_registration,
            calibration_observations,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        if verified is not True:
            return _unknown("H0_BETA_STABILITY_GATE_INVALID", "INVALID")
        if beta_stability_gate["source_state"] != "OBSERVED":
            return _unknown("H0_BETA_STABILITY_GATE_NOT_OBSERVED", "UNKNOWN")
        if beta_stability_gate["gate_decision"] == "BLOCK":
            return _source_blocked(beta_stability_gate)
        if beta_stability_gate["gate_decision"] != "STABLE_CANDIDATE":
            return _unknown("H0_BETA_STABILITY_GATE_INVALID", "INVALID")
        metrics = _evaluate_residual_order(
            residualization_registration, calibration_observations
        )
        return _observed(beta_stability_gate, metrics)
    except (
        InvalidOperation,
        KeyError,
        TypeError,
        ValueError,
        ArithmeticError,
        OverflowError,
    ):
        return _unknown("RESIDUAL_ORDER_STABILITY_EVALUATION_INVALID", "INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate(
    document: Any,
    beta_stability_gate: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_beta_stability_gate_hash: Any,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    try:
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate(
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
