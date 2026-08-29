from __future__ import annotations

from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_replay import (
    REPLAY_SCHEMA,
    STATIC_FINGERPRINT as REPLAY_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_replay,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)


SOURCE_SCHEMA = REPLAY_SCHEMA
SOURCE_STATIC_FINGERPRINT = REPLAY_STATIC_FINGERPRINT
VERIFICATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-report-consumer-verification-v1"
)
STATIC_FINGERPRINT = "20260823-cross-lag-factor-calibration-report-consumer-1"
REPORT_BLOCKER = "FACTOR_CALIBRATION_REPORT_NOT_ACTIVATED"
MISSING_REASON = "G0_CALIBRATION_REPLAY_MISSING"
UNSUPPORTED_REASON = "G0_CALIBRATION_REPLAY_UNSUPPORTED"
INVALID_REASON = "G0_CALIBRATION_REPLAY_INVALID"


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
        "report_consumer_activated": False,
        "report_mounted": False,
    }


def _unknown_facts() -> dict[str, bool]:
    return {
        "all_rows_at_or_before_calibration_cutoff": False,
        "beta_replay_matches_registration": False,
        "calibration_input_verified": False,
        "estimator_replayed": False,
        "external_calibration_timing_attested": False,
        "registration_calibration_receipt_g0_bound": False,
        "registration_v1_verified": False,
        "selection_after_calibration": False,
        "source_replay_verified": False,
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "verification_hash")


def _unknown(reason: str, source_state: str) -> dict[str, Any]:
    return _seal(
        {
            "schema_version": VERIFICATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": source_state,
            "source_schema_version": None,
            "source_static_fingerprint": None,
            "source_replay_hash": None,
            "source_registration_hash": None,
            "source_calibration_observations_hash": None,
            "source_declared_calibration_receipt_hash": None,
            "source_registered_beta_ledger_hash": None,
            "source_replayed_beta_ledger_hash": None,
            "source_report_contract": None,
            "report_state": "UNKNOWN",
            "diagnostic_state": "UNKNOWN",
            "diagnostic_reason": reason,
            "gap_state": reason,
            "maturity_state": "UNKNOWN",
            "permission_state": "LOCKED",
            "calibration_summary": None,
            "facts": _unknown_facts(),
            "blockers": [reason],
            "authority": _authority(),
        }
    )


def _observed(replay: dict[str, Any]) -> dict[str, Any]:
    decision = replay["replay_decision"]
    if decision == "MATCH":
        report_state = "OBSERVED_CALIBRATION_MATCH"
        diagnostic_state = "CALIBRATION_REPLAY_MATCH"
        diagnostic_reason = "REGISTERED_BETAS_REPLAYED_WITHIN_TOLERANCE"
        gap_state = "MATHEMATICAL_REPLAY_MATCHED_TIMING_UNATTESTED"
    elif decision == "BLOCK":
        report_state = "OBSERVED_CALIBRATION_BLOCK"
        diagnostic_state = "CALIBRATION_REPLAY_BLOCK"
        diagnostic_reason = "REGISTERED_BETAS_FAILED_CALIBRATION_REPLAY"
        gap_state = "CALIBRATION_REPLAY_MISMATCH"
    else:
        return _unknown(INVALID_REASON, "INVALID")

    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown(INVALID_REASON, "INVALID")

    source_facts = replay["facts"]
    facts = {
        "all_rows_at_or_before_calibration_cutoff": source_facts[
            "all_rows_at_or_before_calibration_cutoff"
        ],
        "beta_replay_matches_registration": source_facts[
            "beta_replay_matches_registration"
        ],
        "calibration_input_verified": source_facts["calibration_input_verified"],
        "estimator_replayed": source_facts["estimator_replayed"],
        "external_calibration_timing_attested": False,
        "registration_calibration_receipt_g0_bound": False,
        "registration_v1_verified": source_facts["registration_v1_verified"],
        "selection_after_calibration": source_facts["selection_after_calibration"],
        "source_replay_verified": True,
    }

    return _seal(
        {
            "schema_version": VERIFICATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "source_schema_version": replay["schema_version"],
            "source_static_fingerprint": replay["static_fingerprint"],
            "source_replay_hash": replay["receipt_hash"],
            "source_registration_hash": replay["registration_hash"],
            "source_calibration_observations_hash": replay[
                "calibration_observations_hash"
            ],
            "source_declared_calibration_receipt_hash": replay[
                "declared_calibration_receipt_hash"
            ],
            "source_registered_beta_ledger_hash": replay[
                "registered_beta_ledger_hash"
            ],
            "source_replayed_beta_ledger_hash": replay[
                "replayed_beta_ledger_hash"
            ],
            "source_report_contract": {
                "schema_version": VERIFICATION_SCHEMA,
                "activation_state": "UNMOUNTED",
            },
            "report_state": report_state,
            "diagnostic_state": diagnostic_state,
            "diagnostic_reason": diagnostic_reason,
            "gap_state": gap_state,
            "maturity_state": replay["maturity_state"],
            "permission_state": "LOCKED",
            "calibration_summary": {
                "replay_decision": decision,
                "observation_count": replay["observation_count"],
                "first_observation_date": replay["first_observation_date"],
                "last_observation_date": replay["last_observation_date"],
                "calibration_cutoff_date": replay["calibration_cutoff_date"],
                "selection_cutoff_date": replay["selection_cutoff_date"],
                "identity_count": replay["identity_count"],
                "estimator": replay["estimator"],
                "intercept_policy": replay["intercept_policy"],
                "beta_abs_tolerance": replay["beta_abs_tolerance"],
                "max_abs_beta_error": replay["max_abs_beta_error"],
            },
            "facts": facts,
            "blockers": [*replay["blockers"], REPORT_BLOCKER],
            "authority": authority,
        }
    )


def consume_strategy_correlation_cross_lag_factor_calibration_replay(
    replay: Any,
    *,
    residualization_registration: Any,
    calibration_observations: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
    expected_replay_hash: Any,
) -> dict[str, Any]:
    try:
        if replay is None:
            if type(expected_replay_hash) is not str or expected_replay_hash != "":
                return _unknown(INVALID_REASON, "INVALID")
            return _unknown(MISSING_REASON, "MISSING")

        if type(replay) is not dict or not strict_sha256(expected_replay_hash):
            return _unknown(INVALID_REASON, "INVALID")

        if (
            replay.get("schema_version") != SOURCE_SCHEMA
            or replay.get("static_fingerprint") != SOURCE_STATIC_FINGERPRINT
        ):
            return _unknown(UNSUPPORTED_REASON, "UNSUPPORTED")

        if replay.get("receipt_hash") != expected_replay_hash:
            return _unknown(INVALID_REASON, "INVALID")

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
            return _unknown(INVALID_REASON, "INVALID")
        return _observed(replay)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return _unknown(INVALID_REASON, "INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_consumer_receipt(
    document: Any,
    replay: Any,
    *,
    residualization_registration: Any,
    calibration_observations: Any,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
    expected_replay_hash: Any,
) -> bool:
    try:
        rebuilt = consume_strategy_correlation_cross_lag_factor_calibration_replay(
            replay,
            residualization_registration=residualization_registration,
            calibration_observations=calibration_observations,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
            expected_replay_hash=expected_replay_hash,
        )
        return strict_json_contract_equal(document, rebuilt)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return False
