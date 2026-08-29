from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any

from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from .strict_governance_primitives import (
    strict_iso_date,
    strict_native_true,
    strict_nonempty_string,
    strict_sha256,
)
from .strategy_correlation_cross_lag_gate import (
    EVALUATION_SCHEMA as C0_EVALUATION_SCHEMA,
    STATIC_FINGERPRINT as C0_STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_gate,
    verify_strategy_correlation_cross_lag_evaluation,
)


DIAGNOSTIC_SCHEMA = (
    "strategy-correlation-cross-lag-factor-conditional-diagnostic-candidate-v1"
)
STATIC_FINGERPRINT = "20260822-cross-lag-factor-conditional-diagnostic-1"
REGISTRATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-residualization-registration-candidate-v1"
)
REGISTRATION_STATIC_FINGERPRINT = (
    "20260822-cross-lag-factor-residualization-registration-1"
)
FACTOR_OBSERVATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-observations-candidate-v1"
)

_DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_REGISTRATION_FIELDS = {
    "schema_version",
    "static_fingerprint",
    "factor_id",
    "factor_source_hash",
    "calibration_receipt_hash",
    "identity_order_hash",
    "identity_order",
    "beta_by_identity",
    "calibration_cutoff_date",
    "selection_cutoff_date",
    "exposure_estimator",
    "intercept_policy",
    "factor_policy",
    "missing_policy",
    "registration_hash",
}
_FACTOR_DOCUMENT_FIELDS = {
    "schema_version",
    "factor_id",
    "factor_source_hash",
    "rows",
    "factor_observations_hash",
}
_FACTOR_ROW_FIELDS = {"sequence_number", "observation_id", "factor_return"}
_RAW_ROW_FIELDS = {"sequence_number", "observation_id", "returns"}
_C0_PROJECTION_FIELDS = (
    "schema_version",
    "static_fingerprint",
    "evaluation_hash",
    "gate_decision",
    "gate_reason",
    "observation_count",
    "cross_stratum_pair_count",
    "lag_test_count",
    "dependent_test_count",
    "max_adjusted_absolute_lower",
)


def _native_mapping(value: Any) -> bool:
    return type(value) is dict


def _native_list(value: Any) -> bool:
    return type(value) is list


def _native_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _ascii_nonempty(value: Any) -> bool:
    if not strict_nonempty_string(value):
        return False
    try:
        value.encode("ascii")
    except (AttributeError, UnicodeEncodeError):
        return False
    return value == value.strip()


def _strict_sealed(document: Any, hash_field: str) -> bool:
    if not _native_mapping(document) or hash_field not in document:
        return False
    supplied_hash = document.get(hash_field)
    if not strict_sha256(supplied_hash):
        return False
    payload = dict(document)
    payload.pop(hash_field)
    expected = seal_strict_canonical_document(payload, hash_field)
    return strict_json_contract_equal(document, expected)


def _canonical_beta(value: Any) -> Decimal | None:
    if type(value) is not str or not _DECIMAL_PATTERN.fullmatch(value):
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    if not parsed.is_finite() or parsed < Decimal("-10") or parsed > Decimal("10"):
        return None
    if parsed == 0:
        canonical = "0"
    elif parsed == parsed.to_integral_value():
        canonical = format(parsed.quantize(Decimal("1")), "f")
    else:
        canonical = format(parsed.normalize(), "f")
    if value != canonical:
        return None
    return parsed


def _registration_values(
    registration: Any,
    *,
    expected_registration_hash: Any,
) -> tuple[list[str], dict[str, Decimal]] | None:
    if not _native_mapping(registration) or set(registration) != _REGISTRATION_FIELDS:
        return None
    if not _strict_sealed(registration, "registration_hash"):
        return None
    if (
        not strict_sha256(expected_registration_hash)
        or registration["registration_hash"] != expected_registration_hash
        or registration["schema_version"] != REGISTRATION_SCHEMA
        or registration["static_fingerprint"] != REGISTRATION_STATIC_FINGERPRINT
        or not _ascii_nonempty(registration["factor_id"])
        or not strict_sha256(registration["factor_source_hash"])
        or not strict_sha256(registration["calibration_receipt_hash"])
        or not strict_sha256(registration["identity_order_hash"])
        or registration["exposure_estimator"] != "FROZEN_PRE_EVALUATION_OLS_V1"
        or registration["intercept_policy"] != "NO_INTERCEPT_RETURN_RESIDUAL_V1"
        or registration["factor_policy"] != "CONTEMPORANEOUS_SINGLE_FACTOR_V1"
        or registration["missing_policy"] != "FAIL_CLOSED"
    ):
        return None
    identities = registration["identity_order"]
    betas = registration["beta_by_identity"]
    if (
        not _native_list(identities)
        or len(identities) < 2
        or len(identities) > 64
        or not all(_ascii_nonempty(identity) for identity in identities)
        or len(set(identities)) != len(identities)
        or strict_canonical_hash(identities) != registration["identity_order_hash"]
        or not _native_mapping(betas)
        or list(betas) != identities
    ):
        return None
    parsed_betas: dict[str, Decimal] = {}
    for identity in identities:
        parsed = _canonical_beta(betas[identity])
        if parsed is None:
            return None
        parsed_betas[identity] = parsed
    calibration_cutoff = registration["calibration_cutoff_date"]
    selection_cutoff = registration["selection_cutoff_date"]
    if not strict_iso_date(calibration_cutoff) or not strict_iso_date(selection_cutoff):
        return None
    if date.fromisoformat(calibration_cutoff) >= date.fromisoformat(selection_cutoff):
        return None
    return list(identities), parsed_betas


def _factor_values(
    factor_observations: Any,
    registration: dict[str, Any],
    *,
    expected_factor_observations_hash: Any,
) -> tuple[list[dict[str, Any]], list[float]] | None:
    if (
        not _native_mapping(factor_observations)
        or set(factor_observations) != _FACTOR_DOCUMENT_FIELDS
        or not _strict_sealed(factor_observations, "factor_observations_hash")
        or not strict_sha256(expected_factor_observations_hash)
        or factor_observations["factor_observations_hash"]
        != expected_factor_observations_hash
        or factor_observations["schema_version"] != FACTOR_OBSERVATION_SCHEMA
        or factor_observations["factor_id"] != registration["factor_id"]
        or factor_observations["factor_source_hash"]
        != registration["factor_source_hash"]
    ):
        return None
    rows = factor_observations["rows"]
    if not _native_list(rows) or len(rows) < 64 or len(rows) > 2000:
        return None
    values: list[float] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if (
            not _native_mapping(row)
            or set(row) != _FACTOR_ROW_FIELDS
            or type(row["sequence_number"]) is not int
            or row["sequence_number"] != index
            or not _ascii_nonempty(row["observation_id"])
            or row["observation_id"] in seen_ids
            or not _native_number(row["factor_return"])
        ):
            return None
        seen_ids.add(row["observation_id"])
        values.append(float(row["factor_return"]))
    mean = sum(values) / len(values)
    if sum((value - mean) ** 2 for value in values) <= 0.0:
        return None
    return rows, values


def _residual_rows(
    aligned_observations: Any,
    factor_rows: list[dict[str, Any]],
    factor_values: list[float],
    identities: list[str],
    betas: dict[str, Decimal],
) -> list[dict[str, Any]] | None:
    if not _native_list(aligned_observations) or len(aligned_observations) != len(
        factor_rows
    ):
        return None
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_row in enumerate(aligned_observations):
        factor_row = factor_rows[index]
        if (
            not _native_mapping(raw_row)
            or set(raw_row) != _RAW_ROW_FIELDS
            or type(raw_row["sequence_number"]) is not int
            or raw_row["sequence_number"] != index
            or not _ascii_nonempty(raw_row["observation_id"])
            or raw_row["observation_id"] in seen_ids
            or factor_row["sequence_number"] != index
            or factor_row["observation_id"] != raw_row["observation_id"]
            or not _native_mapping(raw_row["returns"])
            or list(raw_row["returns"]) != identities
        ):
            return None
        seen_ids.add(raw_row["observation_id"])
        residual_returns: dict[str, float] = {}
        for identity in identities:
            raw_value = raw_row["returns"][identity]
            if not _native_number(raw_value):
                return None
            residual = float(raw_value) - float(betas[identity]) * factor_values[index]
            if not math.isfinite(residual):
                return None
            residual_returns[identity] = residual
        result.append(
            {
                "sequence_number": index,
                "observation_id": raw_row["observation_id"],
                "returns": residual_returns,
            }
        )
    return result


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "raw_independence_proven": False,
        "residual_independence_proven": False,
        "common_factor_causality_proven": False,
        "calibration_receipt_attested": False,
        "factor_registration_formal": False,
        "sequence_timing_attested": False,
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_claim_allowed": False,
    }


def _unknown() -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": DIAGNOSTIC_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "UNKNOWN",
            "maturity_state": "UNKNOWN",
            "diagnostic_state": "UNKNOWN",
            "diagnostic_reason": "FACTOR_CONDITIONAL_EVIDENCE_INVALID",
            "raw_evaluation": None,
            "residual_evaluation": None,
            "factor_id": "",
            "factor_source_hash": "",
            "calibration_receipt_hash": "",
            "registration_hash": "",
            "factor_observations_hash": "",
            "identity_order_hash": "",
            "residual_input_hash": "",
            "facts": {
                "raw_c0_verified": False,
                "residual_c0_verified": False,
                "raw_block_relaxed": False,
                "calibration_receipt_attested": False,
                "global_two_view_multiplicity_registered": False,
            },
            "blockers": [
                "FACTOR_CONDITIONAL_EVIDENCE_INVALID",
                "F1_REPORT_CONSUMER_NOT_IMPLEMENTED",
            ],
            "authority": _authority(),
        },
        "diagnostic_hash",
    )


def _projection(evaluation: dict[str, Any]) -> dict[str, Any]:
    return {field: evaluation[field] for field in _C0_PROJECTION_FIELDS}


def _classification(raw_decision: str, residual_decision: str) -> tuple[str, str]:
    if raw_decision == "PASS" and residual_decision == "PASS":
        return (
            "NO_CONDITIONAL_DEPENDENCE_DETECTED",
            "RAW_AND_RESIDUAL_C0_CANDIDATE_PASS",
        )
    if raw_decision == "BLOCK" and residual_decision == "PASS":
        return (
            "COMMON_FACTOR_MEDIATED_CANDIDATE",
            "RAW_BLOCK_RESIDUAL_CANDIDATE_PASS",
        )
    if raw_decision == "BLOCK" and residual_decision == "BLOCK":
        return (
            "RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED",
            "RAW_AND_RESIDUAL_C0_BLOCK",
        )
    return (
        "SUPPRESSION_OR_FACTOR_MODEL_INSTABILITY",
        "RAW_PASS_RESIDUAL_C0_BLOCK",
    )


def _blockers(raw_decision: str, residual_decision: str) -> list[str]:
    blockers: list[str] = []
    if raw_decision == "BLOCK":
        blockers.append("RAW_C0_BLOCK_PRESERVED")
    if residual_decision == "BLOCK":
        blockers.append("RESIDUAL_CROSS_LAG_DEPENDENCE_DETECTED")
    if raw_decision == "PASS" and residual_decision == "BLOCK":
        blockers.append("SUPPRESSION_OR_FACTOR_MODEL_INSTABILITY")
    blockers.extend(
        [
            "FACTOR_CALIBRATION_RECEIPT_UNATTESTED",
            "GLOBAL_TWO_VIEW_MULTIPLICITY_NOT_REGISTERED",
            "F1_REPORT_CONSUMER_NOT_IMPLEMENTED",
        ]
    )
    return blockers


def evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic(
    preregistered_strata: Any,
    aligned_observations: Any,
    residualization_registration: Any,
    factor_observations: Any,
    *,
    expected_stratum_assignment_hash: Any,
    expected_registration_hash: Any,
    expected_factor_observations_hash: Any,
) -> dict[str, Any]:
    try:
        if not _native_mapping(residualization_registration):
            return _unknown()
        registration_values = _registration_values(
            residualization_registration,
            expected_registration_hash=expected_registration_hash,
        )
        if registration_values is None:
            return _unknown()
        identities, betas = registration_values
        if (
            not _native_mapping(preregistered_strata)
            or list(preregistered_strata) != identities
            or not strict_sha256(expected_stratum_assignment_hash)
        ):
            return _unknown()
        factor_values = _factor_values(
            factor_observations,
            residualization_registration,
            expected_factor_observations_hash=expected_factor_observations_hash,
        )
        if factor_values is None:
            return _unknown()
        factor_rows, factor_returns = factor_values
        residual_rows = _residual_rows(
            aligned_observations,
            factor_rows,
            factor_returns,
            identities,
            betas,
        )
        if residual_rows is None:
            return _unknown()
        raw_evaluation = evaluate_strategy_correlation_cross_lag_gate(
            preregistered_strata,
            aligned_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        raw_verified = verify_strategy_correlation_cross_lag_evaluation(
            raw_evaluation,
            preregistered_strata,
            aligned_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        residual_evaluation = evaluate_strategy_correlation_cross_lag_gate(
            preregistered_strata,
            residual_rows,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        residual_verified = verify_strategy_correlation_cross_lag_evaluation(
            residual_evaluation,
            preregistered_strata,
            residual_rows,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        if not strict_native_true(raw_verified) or not strict_native_true(
            residual_verified
        ):
            return _unknown()
        raw_decision = raw_evaluation.get("gate_decision")
        residual_decision = residual_evaluation.get("gate_decision")
        if raw_decision not in {"PASS", "BLOCK"} or residual_decision not in {
            "PASS",
            "BLOCK",
        }:
            return _unknown()
        if (
            raw_evaluation.get("schema_version") != C0_EVALUATION_SCHEMA
            or raw_evaluation.get("static_fingerprint") != C0_STATIC_FINGERPRINT
            or residual_evaluation.get("schema_version") != C0_EVALUATION_SCHEMA
            or residual_evaluation.get("static_fingerprint")
            != C0_STATIC_FINGERPRINT
        ):
            return _unknown()
        diagnostic_state, diagnostic_reason = _classification(
            raw_decision,
            residual_decision,
        )
        return seal_strict_canonical_document(
            {
                "schema_version": DIAGNOSTIC_SCHEMA,
                "static_fingerprint": STATIC_FINGERPRINT,
                "source_state": "OBSERVED",
                "maturity_state": "CANDIDATE_RESIDUALIZED_NOT_FORMAL",
                "diagnostic_state": diagnostic_state,
                "diagnostic_reason": diagnostic_reason,
                "raw_evaluation": _projection(raw_evaluation),
                "residual_evaluation": _projection(residual_evaluation),
                "factor_id": residualization_registration["factor_id"],
                "factor_source_hash": residualization_registration[
                    "factor_source_hash"
                ],
                "calibration_receipt_hash": residualization_registration[
                    "calibration_receipt_hash"
                ],
                "registration_hash": residualization_registration[
                    "registration_hash"
                ],
                "factor_observations_hash": factor_observations[
                    "factor_observations_hash"
                ],
                "identity_order_hash": residualization_registration[
                    "identity_order_hash"
                ],
                "residual_input_hash": strict_canonical_hash(residual_rows),
                "facts": {
                    "raw_c0_verified": True,
                    "residual_c0_verified": True,
                    "raw_block_relaxed": False,
                    "calibration_receipt_attested": False,
                    "global_two_view_multiplicity_registered": False,
                },
                "blockers": _blockers(raw_decision, residual_decision),
                "authority": _authority(),
            },
            "diagnostic_hash",
        )
    except Exception:
        return _unknown()


def verify_strategy_correlation_cross_lag_factor_conditional_diagnostic(
    document: Any,
    preregistered_strata: Any,
    aligned_observations: Any,
    residualization_registration: Any,
    factor_observations: Any,
    *,
    expected_stratum_assignment_hash: Any,
    expected_registration_hash: Any,
    expected_factor_observations_hash: Any,
) -> bool:
    try:
        expected = (
            evaluate_strategy_correlation_cross_lag_factor_conditional_diagnostic(
                preregistered_strata,
                aligned_observations,
                residualization_registration,
                factor_observations,
                expected_stratum_assignment_hash=expected_stratum_assignment_hash,
                expected_registration_hash=expected_registration_hash,
                expected_factor_observations_hash=expected_factor_observations_hash,
            )
        )
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
