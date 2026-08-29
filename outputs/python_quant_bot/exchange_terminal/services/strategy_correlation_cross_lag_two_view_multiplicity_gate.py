from __future__ import annotations

import math
import re
from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
    strict_sha256,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 import (
    verify_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2,
)
from exchange_terminal.services.strategy_correlation_cross_lag_gate import (
    _adjusted_absolute_lower as _c0_adjusted_absolute_lower,
    _decimal_text as _c0_decimal_text,
    _effective_sample_size as _c0_effective_sample_size,
    _pearson as _c0_pearson,
    _shifted_pair as _c0_shifted_pair,
)
from exchange_terminal.services.strategy_correlation_cross_lag_gate import (
    evaluate_strategy_correlation_cross_lag_gate,
    verify_strategy_correlation_cross_lag_evaluation,
)
from exchange_terminal.services.strategy_correlation_cross_lag_two_view_multiplicity_registration import (
    CORRECTION_METHOD,
    DEPENDENCE_THRESHOLD,
    FAMILY_ALPHA,
    LAGS,
    VIEWS,
    verify_strategy_correlation_cross_lag_two_view_multiplicity_registration,
)


GATE_SCHEMA = "strategy-correlation-cross-lag-two-view-multiplicity-gate-candidate-v1"
STATIC_FINGERPRINT = "20260822-cross-lag-two-view-multiplicity-gate-1"
MIN_EFFECTIVE_SAMPLE = 20.0
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "factor_calibration_attested": False,
        "global_independence_proven": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "raw_independence_proven": False,
        "registration_timing_attested": False,
        "residual_independence_proven": False,
        "sequence_timing_attested": False,
        "strata_timing_attested": False,
    }


def _facts(*, observed: bool, source_block_preserved: bool = False) -> dict[str, bool]:
    return {
        "formula_parity_verified": observed is True,
        "global_two_view_multiplicity_registered": observed is True,
        "raw_c0_verified": observed is True,
        "registration_timing_attested": False,
        "residual_c0_verified": observed is True,
        "residual_input_hash_verified": observed is True,
        "source_block_preserved": source_block_preserved is True,
    }


def _unknown() -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "blockers": ["TWO_VIEW_MULTIPLICITY_INPUT_INVALID"],
            "correction_method": CORRECTION_METHOD,
            "cross_stratum_pair_count": None,
            "dependence_threshold": DEPENDENCE_THRESHOLD,
            "facts": _facts(observed=False),
            "family_alpha": FAMILY_ALPHA,
            "family_registration_hash": None,
            "f0_diagnostic_hash": None,
            "gate_decision": "UNKNOWN",
            "gate_reason": "TWO_VIEW_MULTIPLICITY_INPUT_INVALID",
            "global_dependent_test_count": None,
            "global_recalibrated_decision": "UNKNOWN",
            "global_test_count": None,
            "lags": list(LAGS),
            "maturity_state": "UNKNOWN",
            "per_view_test_count": None,
            "private_recalculated_test_ledger_hash": None,
            "raw_evaluation_hash": None,
            "residual_evaluation_hash": None,
            "residual_input_hash": None,
            "schema_version": GATE_SCHEMA,
            "source_state": "UNKNOWN",
            "static_fingerprint": STATIC_FINGERPRINT,
            "stratum_assignment_hash": None,
            "view_count": len(VIEWS),
            "view_summaries": None,
            "views": list(VIEWS),
        },
        "evaluation_hash",
    )


_decimal_text = _c0_decimal_text


def _decimal_number(value: Any) -> float | None:
    if type(value) is not str or _DECIMAL.fullmatch(value) is None:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


_adjusted_absolute_lower = _c0_adjusted_absolute_lower


def _gate_decision(
    raw_source_decision: str,
    residual_source_decision: str,
    global_dependent_test_count: int,
) -> tuple[str, str, bool]:
    source_block = raw_source_decision == "BLOCK" or residual_source_decision == "BLOCK"
    global_block = global_dependent_test_count > 0
    if source_block and not global_block:
        return (
            "BLOCK",
            "SOURCE_C0_BLOCK_PRESERVED_AFTER_GLOBAL_RECALIBRATION",
            True,
        )
    if source_block and global_block:
        return "BLOCK", "SOURCE_AND_GLOBAL_TWO_VIEW_DEPENDENCE_DETECTED", True
    if global_block:
        return "BLOCK", "GLOBAL_TWO_VIEW_DEPENDENCE_DETECTED", False
    return "PASS", "NO_GLOBAL_TWO_VIEW_DEPENDENCE_DETECTED", False


def _recalculate_view(
    view: str,
    evaluation: dict[str, Any],
    aligned_observations: list[dict[str, Any]],
    *,
    per_view_test_count: int,
    global_test_count: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    lag_results = evaluation.get("lag_results")
    if type(lag_results) is not list or len(lag_results) != per_view_test_count:
        return None
    if type(aligned_observations) is not list:
        return None
    ledger: list[dict[str, Any]] = []
    global_dependent_count = 0
    global_lowers: list[float] = []
    threshold = float(DEPENDENCE_THRESHOLD)
    series_by_identity: dict[str, list[float]] = {}

    for row in lag_results:
        if type(row) is not dict:
            return None
        left_identity = row.get("left_identity")
        right_identity = row.get("right_identity")
        lag = row.get("lag")
        if type(left_identity) is not str or type(right_identity) is not str:
            return None
        if type(lag) is not int:
            return None
        for identity in (left_identity, right_identity):
            if identity in series_by_identity:
                continue
            values: list[float] = []
            for observation in aligned_observations:
                if type(observation) is not dict:
                    return None
                returns = observation.get("returns")
                if type(returns) is not dict or identity not in returns:
                    return None
                value = returns[identity]
                if type(value) not in (int, float) or type(value) is bool:
                    return None
                values.append(float(value))
            series_by_identity[identity] = values

        shifted_left, shifted_right = _c0_shifted_pair(
            series_by_identity[left_identity],
            series_by_identity[right_identity],
            lag,
        )
        correlation = _c0_pearson(shifted_left, shifted_right)
        effective_sample_size = _c0_effective_sample_size(
            shifted_left, shifted_right
        )
        if correlation is None or effective_sample_size is None:
            return None
        if len(shifted_left) != row.get("paired_observation_count"):
            return None
        if _decimal_text(correlation) != row.get("correlation"):
            return None
        if _decimal_text(effective_sample_size) != row.get("effective_sample_size"):
            return None

        per_view_lower = _adjusted_absolute_lower(
            correlation, effective_sample_size, per_view_test_count
        )
        global_lower = _adjusted_absolute_lower(
            correlation, effective_sample_size, global_test_count
        )
        if per_view_lower is None or global_lower is None:
            return None
        per_view_text = _decimal_text(per_view_lower)
        global_text = _decimal_text(global_lower)
        if per_view_text != row.get("adjusted_absolute_lower"):
            return None
        dependent = global_lower >= threshold
        global_dependent_count += int(dependent)
        global_lowers.append(global_lower)
        ledger.append(
            {
                "effective_sample_size": row.get("effective_sample_size"),
                "global_adjusted_absolute_lower": global_text,
                "global_dependent": dependent,
                "lag": lag,
                "left_identity": left_identity,
                "left_stratum": row.get("left_stratum"),
                "right_identity": right_identity,
                "right_stratum": row.get("right_stratum"),
                "source_adjusted_absolute_lower": row.get(
                    "adjusted_absolute_lower"
                ),
                "source_correlation": row.get("correlation"),
                "view": view,
            }
        )

    summary = {
        "global_dependent_test_count": global_dependent_count,
        "max_global_adjusted_absolute_lower": _decimal_text(max(global_lowers)),
        "source_dependent_test_count": evaluation.get("dependent_test_count"),
        "source_evaluation_hash": evaluation.get("evaluation_hash"),
        "source_gate_decision": evaluation.get("gate_decision"),
        "view": view,
    }
    return summary, ledger


def evaluate_strategy_correlation_cross_lag_two_view_multiplicity_gate(
    family_registration: Any,
    f0_diagnostic: Any,
    preregistered_strata: Any,
    raw_aligned_observations: Any,
    residual_aligned_observations: Any,
    residualization_registration: Any,
    factor_observations: Any,
    *,
    expected_stratum_assignment_hash: Any,
    expected_residualization_registration_hash: Any,
    expected_factor_observations_hash: Any,
    expected_family_registration_hash: Any,
    expected_f0_diagnostic_hash: Any,
    expected_residual_input_hash: Any,
) -> dict[str, Any]:
    try:
        if not verify_strategy_correlation_cross_lag_two_view_multiplicity_registration(
            family_registration,
            preregistered_strata,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_registration_hash=expected_family_registration_hash,
        ):
            return _unknown()
        if family_registration.get("source_state") != "REGISTERED":
            return _unknown()
        if not verify_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2(
            f0_diagnostic,
            preregistered_strata,
            raw_aligned_observations,
            residualization_registration,
            factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_registration_hash=expected_residualization_registration_hash,
            expected_factor_observations_hash=expected_factor_observations_hash,
            expected_diagnostic_hash=expected_f0_diagnostic_hash,
        ):
            return _unknown()
        if type(f0_diagnostic) is not dict or f0_diagnostic.get("source_state") != "OBSERVED":
            return _unknown()
        if not strict_sha256(expected_residual_input_hash):
            return _unknown()
        if f0_diagnostic.get("residual_input_hash") != expected_residual_input_hash:
            return _unknown()
        if strict_canonical_hash(residual_aligned_observations) != expected_residual_input_hash:
            return _unknown()

        raw_evaluation = evaluate_strategy_correlation_cross_lag_gate(
            preregistered_strata,
            raw_aligned_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        residual_evaluation = evaluate_strategy_correlation_cross_lag_gate(
            preregistered_strata,
            residual_aligned_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        if not verify_strategy_correlation_cross_lag_evaluation(
            raw_evaluation,
            preregistered_strata,
            raw_aligned_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        ):
            return _unknown()
        if not verify_strategy_correlation_cross_lag_evaluation(
            residual_evaluation,
            preregistered_strata,
            residual_aligned_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        ):
            return _unknown()
        if raw_evaluation.get("source_state") != "OBSERVED" or residual_evaluation.get("source_state") != "OBSERVED":
            return _unknown()
        raw_projection = f0_diagnostic.get("raw_evaluation")
        residual_projection = f0_diagnostic.get("residual_evaluation")
        if type(raw_projection) is not dict or type(residual_projection) is not dict:
            return _unknown()
        if raw_evaluation.get("evaluation_hash") != raw_projection.get("evaluation_hash"):
            return _unknown()
        if residual_evaluation.get("evaluation_hash") != residual_projection.get("evaluation_hash"):
            return _unknown()

        pair_count = family_registration.get("cross_stratum_pair_count")
        per_view_test_count = family_registration.get("per_view_test_count")
        global_test_count = family_registration.get("global_test_count")
        if type(pair_count) is not int or type(per_view_test_count) is not int or type(global_test_count) is not int:
            return _unknown()
        if family_registration.get("views") != list(VIEWS) or family_registration.get("lags") != list(LAGS):
            return _unknown()
        if family_registration.get("view_count") != len(VIEWS):
            return _unknown()
        if family_registration.get("lag_count") != len(LAGS):
            return _unknown()
        if per_view_test_count != pair_count * len(LAGS):
            return _unknown()
        if global_test_count != per_view_test_count * len(VIEWS):
            return _unknown()
        for evaluation in (raw_evaluation, residual_evaluation):
            if evaluation.get("cross_stratum_pair_count") != pair_count:
                return _unknown()
            if evaluation.get("lag_test_count") != per_view_test_count:
                return _unknown()
            if evaluation.get("lag_family") != list(LAGS):
                return _unknown()

        raw_result = _recalculate_view(
            "RAW",
            raw_evaluation,
            raw_aligned_observations,
            per_view_test_count=per_view_test_count,
            global_test_count=global_test_count,
        )
        residual_result = _recalculate_view(
            "RESIDUAL",
            residual_evaluation,
            residual_aligned_observations,
            per_view_test_count=per_view_test_count,
            global_test_count=global_test_count,
        )
        if raw_result is None or residual_result is None:
            return _unknown()
        raw_summary, raw_ledger = raw_result
        residual_summary, residual_ledger = residual_result
        raw_keys = [
            (row.get("left_identity"), row.get("left_stratum"), row.get("right_identity"), row.get("right_stratum"), row.get("lag"))
            for row in raw_evaluation["lag_results"]
        ]
        residual_keys = [
            (row.get("left_identity"), row.get("left_stratum"), row.get("right_identity"), row.get("right_stratum"), row.get("lag"))
            for row in residual_evaluation["lag_results"]
        ]
        if raw_keys != residual_keys:
            return _unknown()
        ledger = raw_ledger + residual_ledger
        if len(ledger) != global_test_count:
            return _unknown()
        global_dependent_count = (
            raw_summary["global_dependent_test_count"]
            + residual_summary["global_dependent_test_count"]
        )
        gate_decision, gate_reason, source_block_preserved = _gate_decision(
            raw_evaluation["gate_decision"],
            residual_evaluation["gate_decision"],
            global_dependent_count,
        )
        blockers = [
            "REGISTRATION_TIMING_UNATTESTED",
            "FACTOR_CALIBRATION_RECEIPT_UNATTESTED",
            "TWO_VIEW_MULTIPLICITY_GATE_NOT_ACTIVATED",
        ]
        if raw_evaluation["gate_decision"] == "BLOCK":
            blockers.append("RAW_C0_BLOCK_PRESERVED")
        if residual_evaluation["gate_decision"] == "BLOCK":
            blockers.append("RESIDUAL_C0_BLOCK_PRESERVED")
        if global_dependent_count > 0:
            blockers.append("GLOBAL_TWO_VIEW_DEPENDENCE_DETECTED")
        if gate_reason == "SOURCE_C0_BLOCK_PRESERVED_AFTER_GLOBAL_RECALIBRATION":
            blockers.append(gate_reason)

        return seal_strict_canonical_document(
            {
                "authority": _authority(),
                "blockers": blockers,
                "correction_method": CORRECTION_METHOD,
                "cross_stratum_pair_count": pair_count,
                "dependence_threshold": DEPENDENCE_THRESHOLD,
                "facts": _facts(
                    observed=True,
                    source_block_preserved=source_block_preserved,
                ),
                "family_alpha": FAMILY_ALPHA,
                "family_registration_hash": family_registration["registration_hash"],
                "f0_diagnostic_hash": f0_diagnostic["diagnostic_hash"],
                "gate_decision": gate_decision,
                "gate_reason": gate_reason,
                "global_dependent_test_count": global_dependent_count,
                "global_recalibrated_decision": (
                    "BLOCK" if global_dependent_count > 0 else "PASS"
                ),
                "global_test_count": global_test_count,
                "lags": list(LAGS),
                "maturity_state": "CANDIDATE_GLOBAL_FAMILY_NOT_TIME_ATTESTED",
                "per_view_test_count": per_view_test_count,
                "private_recalculated_test_ledger_hash": strict_canonical_hash(ledger),
                "raw_evaluation_hash": raw_evaluation["evaluation_hash"],
                "residual_evaluation_hash": residual_evaluation["evaluation_hash"],
                "residual_input_hash": expected_residual_input_hash,
                "schema_version": GATE_SCHEMA,
                "source_state": "OBSERVED",
                "static_fingerprint": STATIC_FINGERPRINT,
                "stratum_assignment_hash": family_registration[
                    "stratum_assignment_hash"
                ],
                "view_count": len(VIEWS),
                "view_summaries": [raw_summary, residual_summary],
                "views": list(VIEWS),
            },
            "evaluation_hash",
        )
    except Exception:
        return _unknown()


def verify_strategy_correlation_cross_lag_two_view_multiplicity_gate(
    document: Any,
    family_registration: Any,
    f0_diagnostic: Any,
    preregistered_strata: Any,
    raw_aligned_observations: Any,
    residual_aligned_observations: Any,
    residualization_registration: Any,
    factor_observations: Any,
    *,
    expected_stratum_assignment_hash: Any,
    expected_residualization_registration_hash: Any,
    expected_factor_observations_hash: Any,
    expected_family_registration_hash: Any,
    expected_f0_diagnostic_hash: Any,
    expected_residual_input_hash: Any,
    expected_evaluation_hash: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        if not strict_sha256(expected_evaluation_hash):
            return False
        if document.get("evaluation_hash") != expected_evaluation_hash:
            return False
        expected = evaluate_strategy_correlation_cross_lag_two_view_multiplicity_gate(
            family_registration,
            f0_diagnostic,
            preregistered_strata,
            raw_aligned_observations,
            residual_aligned_observations,
            residualization_registration,
            factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_residualization_registration_hash=expected_residualization_registration_hash,
            expected_factor_observations_hash=expected_factor_observations_hash,
            expected_family_registration_hash=expected_family_registration_hash,
            expected_f0_diagnostic_hash=expected_f0_diagnostic_hash,
            expected_residual_input_hash=expected_residual_input_hash,
        )
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
