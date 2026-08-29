from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_replay import (
    REPLAY_SCHEMA,
    STATIC_FINGERPRINT as REPLAY_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_replay,
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
    "strategy-correlation-cross-lag-factor-calibration-stability-gate-candidate-v1"
)
STATIC_FINGERPRINT = "20260825-cross-lag-factor-calibration-stability-gate-1"
FOLD_COUNT = 4
MIN_ROWS_PER_FOLD = 5
NORMALIZATION_FLOOR = Decimal("0.25")
MAX_NORMALIZED_BETA_DRIFT = Decimal("0.5")


def _canonical_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value.normalize(), "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _authority() -> dict[str, bool]:
    return {
        "beta_temporal_stability_proven": False,
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_calibration_timing_attested": False,
        "future_evaluation_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _unknown_facts() -> dict[str, bool]:
    return {
        "beta_stability_threshold_passed": False,
        "beta_temporal_stability_proven": False,
        "external_calibration_timing_attested": False,
        "fold_protocol_pinned": True,
        "source_calibration_replay_verified": False,
        "source_gate_block_relaxed": False,
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "gate_hash")


def _base_projection() -> dict[str, Any]:
    return {
        "fold_count": FOLD_COUNT,
        "minimum_rows_per_fold": MIN_ROWS_PER_FOLD,
        "normalization_floor": _canonical_decimal(NORMALIZATION_FLOOR),
        "maximum_allowed_normalized_beta_drift": _canonical_decimal(
            MAX_NORMALIZED_BETA_DRIFT
        ),
    }


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
            "maximum_observed_normalized_beta_drift": None,
            "unstable_identity_count": None,
            "sign_reversal_count": None,
            "unidentified_fold_count": None,
            "private_fold_beta_ledger_hash": None,
            "source_replay_hash": None,
            "source_registration_hash": None,
            "source_calibration_observations_hash": None,
            "facts": _unknown_facts(),
            "blockers": [reason],
            "authority": _authority(),
        }
    )


def _source_blocked(replay: dict[str, Any]) -> dict[str, Any]:
    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": "BLOCK",
            "gate_reason": "SOURCE_CALIBRATION_REPLAY_BLOCKED",
            **_base_projection(),
            "minimum_observed_fold_rows": None,
            "maximum_observed_fold_rows": None,
            "maximum_observed_normalized_beta_drift": None,
            "unstable_identity_count": None,
            "sign_reversal_count": None,
            "unidentified_fold_count": None,
            "private_fold_beta_ledger_hash": None,
            "source_replay_hash": replay["receipt_hash"],
            "source_registration_hash": replay["registration_hash"],
            "source_calibration_observations_hash": replay[
                "calibration_observations_hash"
            ],
            "facts": {
                **_unknown_facts(),
                "source_calibration_replay_verified": True,
            },
            "blockers": [
                *replay["blockers"],
                "SOURCE_CALIBRATION_REPLAY_BLOCKED",
                "BETA_STABILITY_CANDIDATE_NOT_ACTIVATED",
            ],
            "authority": _authority(),
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


def _evaluate_folds(
    registration: dict[str, Any], calibration_observations: dict[str, Any]
) -> dict[str, Any]:
    identities = registration["identity_order"]
    registered = {
        identity: _decimal(registration["beta_by_identity"][identity])
        for identity in identities
    }
    fold_rows = _folds(calibration_observations["rows"])
    if min(map(len, fold_rows)) < MIN_ROWS_PER_FOLD:
        raise ValueError("insufficient rows per stability fold")

    unstable_identities: set[str] = set()
    sign_reversals = 0
    unidentified = 0
    maximum_drift = Decimal("0")
    private_ledger: list[dict[str, Any]] = []

    with localcontext() as context:
        context.prec = 50
        for fold_index, rows in enumerate(fold_rows):
            factors = [_decimal(row["factor_return"]) for row in rows]
            energy = sum((factor * factor for factor in factors), Decimal("0"))
            mean = sum(factors, Decimal("0")) / Decimal(len(factors))
            centered_energy = sum(
                ((factor - mean) * (factor - mean) for factor in factors),
                Decimal("0"),
            )
            if energy == 0 or centered_energy == 0:
                unidentified += 1
                private_ledger.append(
                    {
                        "fold_index": fold_index,
                        "row_count": len(rows),
                        "identified": False,
                        "beta_by_identity": None,
                    }
                )
                continue

            fold_betas: dict[str, str] = {}
            for identity in identities:
                numerator = sum(
                    (
                        factor * _decimal(row["returns"][identity])
                        for factor, row in zip(factors, rows, strict=True)
                    ),
                    Decimal("0"),
                )
                beta = numerator / energy
                fold_betas[identity] = _canonical_decimal(beta)
                scale = max(abs(registered[identity]), NORMALIZATION_FLOOR)
                drift = abs(beta - registered[identity]) / scale
                maximum_drift = max(maximum_drift, drift)
                if drift > MAX_NORMALIZED_BETA_DRIFT:
                    unstable_identities.add(identity)
                if registered[identity] * beta < 0:
                    sign_reversals += 1
                    unstable_identities.add(identity)
            private_ledger.append(
                {
                    "fold_index": fold_index,
                    "row_count": len(rows),
                    "identified": True,
                    "beta_by_identity": fold_betas,
                }
            )

    return {
        "minimum_observed_fold_rows": min(map(len, fold_rows)),
        "maximum_observed_fold_rows": max(map(len, fold_rows)),
        "maximum_observed_normalized_beta_drift": _canonical_decimal(maximum_drift),
        "unstable_identity_count": len(unstable_identities),
        "sign_reversal_count": sign_reversals,
        "unidentified_fold_count": unidentified,
        "private_fold_beta_ledger_hash": strict_canonical_hash(private_ledger),
    }


def _observed(
    replay: dict[str, Any], metrics: dict[str, Any]
) -> dict[str, Any]:
    stable = (
        metrics["unstable_identity_count"] == 0
        and metrics["sign_reversal_count"] == 0
        and metrics["unidentified_fold_count"] == 0
    )
    decision = "STABLE_CANDIDATE" if stable else "BLOCK"
    if metrics["unidentified_fold_count"]:
        reason = "FOLD_FACTOR_IDENTIFICATION_INSUFFICIENT"
    elif stable:
        reason = "NO_PREREGISTERED_BETA_INSTABILITY_DETECTED"
    else:
        reason = "CALIBRATION_BETA_TEMPORAL_INSTABILITY_DETECTED"
    blockers = [*replay["blockers"]]
    if not stable:
        blockers.append(reason)
    blockers.append("BETA_STABILITY_CANDIDATE_NOT_ACTIVATED")
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("BETA_STABILITY_INTERNAL_AUTHORITY_INVALID", "INVALID")
    return _seal(
        {
            "schema_version": GATE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": decision,
            "gate_reason": reason,
            **_base_projection(),
            **metrics,
            "source_replay_hash": replay["receipt_hash"],
            "source_registration_hash": replay["registration_hash"],
            "source_calibration_observations_hash": replay[
                "calibration_observations_hash"
            ],
            "facts": {
                "beta_stability_threshold_passed": stable,
                "beta_temporal_stability_proven": False,
                "external_calibration_timing_attested": False,
                "fold_protocol_pinned": True,
                "source_calibration_replay_verified": True,
                "source_gate_block_relaxed": False,
            },
            "blockers": blockers,
            "authority": authority,
        }
    )


def evaluate_strategy_correlation_cross_lag_factor_calibration_stability_gate(
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> dict[str, Any]:
    try:
        if replay is None:
            if type(expected_replay_hash) is not str or expected_replay_hash != "":
                return _unknown("G0_CALIBRATION_REPLAY_INVALID", "INVALID")
            return _unknown("G0_CALIBRATION_REPLAY_MISSING", "MISSING")
        if type(replay) is not dict or not strict_sha256(expected_replay_hash):
            return _unknown("G0_CALIBRATION_REPLAY_INVALID", "INVALID")
        if (
            replay.get("schema_version") != REPLAY_SCHEMA
            or replay.get("static_fingerprint") != REPLAY_STATIC_FINGERPRINT
        ):
            return _unknown("G0_CALIBRATION_REPLAY_UNSUPPORTED", "UNSUPPORTED")
        if replay.get("receipt_hash") != expected_replay_hash:
            return _unknown("G0_CALIBRATION_REPLAY_INVALID", "INVALID")
        verified = verify_strategy_correlation_cross_lag_factor_calibration_replay(
            replay,
            residualization_registration,
            calibration_observations,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        if verified is not True:
            return _unknown("G0_CALIBRATION_REPLAY_INVALID", "INVALID")
        if replay["source_state"] != "OBSERVED":
            return _unknown("G0_CALIBRATION_REPLAY_NOT_OBSERVED", "UNKNOWN")
        if replay["replay_decision"] == "BLOCK":
            return _source_blocked(replay)
        if replay["replay_decision"] != "MATCH":
            return _unknown("G0_CALIBRATION_REPLAY_INVALID", "INVALID")
        metrics = _evaluate_folds(
            residualization_registration, calibration_observations
        )
        return _observed(replay, metrics)
    except (
        InvalidOperation,
        KeyError,
        TypeError,
        ValueError,
        ArithmeticError,
        OverflowError,
    ):
        return _unknown("BETA_STABILITY_EVALUATION_INVALID", "INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_stability_gate(
    document: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_replay_hash: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    try:
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_stability_gate(
            replay,
            residualization_registration,
            calibration_observations,
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
