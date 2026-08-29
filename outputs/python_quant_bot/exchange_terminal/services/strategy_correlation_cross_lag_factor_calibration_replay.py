from __future__ import annotations

import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    _registration_values,
)


CALIBRATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-observations-candidate-v1"
)
CALIBRATION_STATIC_FINGERPRINT = (
    "20260823-cross-lag-factor-calibration-observations-1"
)
REPLAY_SCHEMA = "strategy-correlation-cross-lag-factor-calibration-replay-candidate-v1"
STATIC_FINGERPRINT = "20260823-cross-lag-factor-calibration-replay-1"
MIN_CALIBRATION_OBSERVATIONS = 20
BETA_ABS_TOLERANCE = Decimal("0.000000000001")
_ASCII_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CALIBRATION_KEYS = {
    "calibration_observations_hash",
    "factor_id",
    "factor_source_hash",
    "identity_order",
    "rows",
    "schema_version",
    "static_fingerprint",
}
_ROW_KEYS = {
    "factor_return",
    "observation_date",
    "observation_id",
    "returns",
    "sequence_number",
}


def _authority() -> dict[str, bool]:
    return {
        "calibration_receipt_attested": False,
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_calibration_timing_attested": False,
        "factor_registration_formal": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _facts(*, matched: bool = False) -> dict[str, bool]:
    return {
        "all_rows_at_or_before_calibration_cutoff": matched,
        "beta_replay_matches_registration": matched,
        "calibration_input_verified": matched,
        "estimator_replayed": matched,
        "external_calibration_timing_attested": False,
        "registration_calibration_receipt_g0_bound": False,
        "registration_v1_verified": matched,
        "selection_after_calibration": matched,
    }


def _unknown(reason: str) -> dict[str, Any]:
    document: dict[str, Any] = {
        "authority": _authority(),
        "beta_abs_tolerance": str(BETA_ABS_TOLERANCE),
        "blockers": [reason],
        "calibration_cutoff_date": None,
        "calibration_observations_hash": None,
        "declared_calibration_receipt_hash": None,
        "estimator": None,
        "facts": _facts(),
        "factor_id": None,
        "first_observation_date": None,
        "identity_count": None,
        "intercept_policy": None,
        "last_observation_date": None,
        "maturity_state": "UNKNOWN",
        "max_abs_beta_error": None,
        "observation_count": None,
        "registered_beta_ledger_hash": None,
        "registration_hash": None,
        "replay_decision": "UNKNOWN",
        "replayed_beta_ledger_hash": None,
        "schema_version": REPLAY_SCHEMA,
        "selection_cutoff_date": None,
        "source_state": "UNKNOWN",
        "static_fingerprint": STATIC_FINGERPRINT,
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def _date(value: Any) -> date | None:
    if type(value) is not str:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _decimal(value: Any) -> Decimal | None:
    if type(value) not in (int, float) or type(value) is bool:
        return None
    if not math.isfinite(float(value)):
        return None
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _decimal_full(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value.normalize(), "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _decimal_12(value: Decimal) -> str:
    quantized = value.quantize(BETA_ABS_TOLERANCE, rounding=ROUND_HALF_EVEN)
    return _decimal_full(quantized)


def _calibration_values(
    document: Any,
    identities: list[str],
    registration: dict[str, Any],
    *,
    expected_calibration_observations_hash: Any,
) -> tuple[list[Decimal], dict[str, list[Decimal]], list[str]] | None:
    if type(document) is not dict or set(document) != _CALIBRATION_KEYS:
        return None
    if not strict_sha256(expected_calibration_observations_hash):
        return None
    if document.get("calibration_observations_hash") != expected_calibration_observations_hash:
        return None
    try:
        sealed = seal_strict_canonical_document(
            {
                key: value
                for key, value in document.items()
                if key != "calibration_observations_hash"
            },
            "calibration_observations_hash",
        )
    except (TypeError, ValueError):
        return None
    if not strict_json_contract_equal(document, sealed):
        return None
    if document.get("schema_version") != CALIBRATION_SCHEMA:
        return None
    if document.get("static_fingerprint") != CALIBRATION_STATIC_FINGERPRINT:
        return None
    if document.get("factor_id") != registration.get("factor_id"):
        return None
    if document.get("factor_source_hash") != registration.get("factor_source_hash"):
        return None
    if type(document.get("identity_order")) is not list:
        return None
    if document.get("identity_order") != identities:
        return None
    rows = document.get("rows")
    if type(rows) is not list or len(rows) < MIN_CALIBRATION_OBSERVATIONS:
        return None
    calibration_cutoff = _date(registration.get("calibration_cutoff_date"))
    selection_cutoff = _date(registration.get("selection_cutoff_date"))
    if calibration_cutoff is None or selection_cutoff is None:
        return None
    if calibration_cutoff >= selection_cutoff:
        return None

    factor_values: list[Decimal] = []
    returns_by_identity = {identity: [] for identity in identities}
    dates: list[str] = []
    observation_ids: set[str] = set()
    previous_date: date | None = None
    for index, row in enumerate(rows):
        if type(row) is not dict or set(row) != _ROW_KEYS:
            return None
        if type(row.get("sequence_number")) is not int:
            return None
        if row.get("sequence_number") != index:
            return None
        observation_id = row.get("observation_id")
        if type(observation_id) is not str or _ASCII_ID.fullmatch(observation_id) is None:
            return None
        if observation_id in observation_ids:
            return None
        observation_ids.add(observation_id)
        observation_date = _date(row.get("observation_date"))
        if observation_date is None or observation_date > calibration_cutoff:
            return None
        if previous_date is not None and observation_date <= previous_date:
            return None
        previous_date = observation_date
        dates.append(observation_date.isoformat())
        factor_return = _decimal(row.get("factor_return"))
        if factor_return is None:
            return None
        factor_values.append(factor_return)
        returns = row.get("returns")
        if type(returns) is not dict or set(returns) != set(identities):
            return None
        for identity in identities:
            value = _decimal(returns.get(identity))
            if value is None:
                return None
            returns_by_identity[identity].append(value)

    with localcontext() as context:
        context.prec = 50
        energy = sum((value * value for value in factor_values), Decimal(0))
        mean = sum(factor_values, Decimal(0)) / Decimal(len(factor_values))
        centered = sum(
            ((value - mean) * (value - mean) for value in factor_values),
            Decimal(0),
        )
    if energy <= 0 or centered <= 0:
        return None
    return factor_values, returns_by_identity, dates


def evaluate_strategy_correlation_cross_lag_factor_calibration_replay(
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> dict[str, Any]:
    if type(residualization_registration) is not dict:
        return _unknown("REGISTRATION_SHAPE_INVALID")
    try:
        parsed = _registration_values(
            residualization_registration,
            expected_registration_hash=expected_registration_hash,
        )
    except Exception:
        parsed = None
    if parsed is None:
        return _unknown("REGISTRATION_NOT_VERIFIED")
    identities, registered_betas = parsed
    values = _calibration_values(
        calibration_observations,
        identities,
        residualization_registration,
        expected_calibration_observations_hash=(
            expected_calibration_observations_hash
        ),
    )
    if values is None:
        return _unknown("CALIBRATION_OBSERVATIONS_NOT_VERIFIED")
    factor_values, returns_by_identity, dates = values

    replayed: dict[str, Decimal] = {}
    errors: list[Decimal] = []
    with localcontext() as context:
        context.prec = 50
        denominator = sum(
            (value * value for value in factor_values), Decimal(0)
        )
        for identity in identities:
            numerator = sum(
                (
                    factor * identity_return
                    for factor, identity_return in zip(
                        factor_values, returns_by_identity[identity], strict=True
                    )
                ),
                Decimal(0),
            )
            beta = numerator / denominator
            replayed[identity] = beta
            errors.append(abs(beta - registered_betas[identity]))
    max_error = max(errors)
    matched = max_error <= BETA_ABS_TOLERANCE
    registered_ledger = [
        {"beta": _decimal_full(registered_betas[identity]), "identity": identity}
        for identity in identities
    ]
    replayed_ledger = [
        {"beta": _decimal_full(replayed[identity]), "identity": identity}
        for identity in identities
    ]
    blockers = [
        "EXTERNAL_CALIBRATION_TIMING_UNATTESTED",
        "REGISTRATION_CALIBRATION_RECEIPT_NOT_G0_BOUND",
        "CALIBRATION_REPLAY_NOT_ACTIVATED",
    ]
    if not matched:
        blockers.insert(0, "REGISTERED_BETA_REPLAY_MISMATCH")
    facts = _facts(matched=True)
    facts["beta_replay_matches_registration"] = matched
    document: dict[str, Any] = {
        "authority": _authority(),
        "beta_abs_tolerance": str(BETA_ABS_TOLERANCE),
        "blockers": blockers,
        "calibration_cutoff_date": residualization_registration.get(
            "calibration_cutoff_date"
        ),
        "calibration_observations_hash": expected_calibration_observations_hash,
        "declared_calibration_receipt_hash": residualization_registration.get(
            "calibration_receipt_hash"
        ),
        "estimator": residualization_registration.get("exposure_estimator"),
        "facts": facts,
        "factor_id": residualization_registration.get("factor_id"),
        "first_observation_date": dates[0],
        "identity_count": len(identities),
        "intercept_policy": residualization_registration.get("intercept_policy"),
        "last_observation_date": dates[-1],
        "maturity_state": "CANDIDATE_CALIBRATION_REPLAY_NOT_TIME_ATTESTED",
        "max_abs_beta_error": _decimal_12(max_error),
        "observation_count": len(factor_values),
        "registered_beta_ledger_hash": strict_canonical_hash(registered_ledger),
        "registration_hash": expected_registration_hash,
        "replay_decision": "MATCH" if matched else "BLOCK",
        "replayed_beta_ledger_hash": strict_canonical_hash(replayed_ledger),
        "schema_version": REPLAY_SCHEMA,
        "selection_cutoff_date": residualization_registration.get(
            "selection_cutoff_date"
        ),
        "source_state": "OBSERVED",
        "static_fingerprint": STATIC_FINGERPRINT,
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_replay(
    document: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        expected = evaluate_strategy_correlation_cross_lag_factor_calibration_replay(
            residualization_registration,
            calibration_observations,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
        )
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
