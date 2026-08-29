from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_report_consumer import (
    STATIC_FINGERPRINT as REPORT_STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA as REPORT_SCHEMA,
    verify_strategy_correlation_cross_lag_factor_calibration_consumer_receipt,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)


ENVELOPE_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-presentation-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20260823-cross-lag-factor-calibration-presentation-envelope-1"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_calibration_timing_attested": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mounted": False,
        "profitability_claim_allowed": False,
        "report_consumer_activated": False,
        "source_semantics_replayed_in_browser": False,
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "envelope_hash")


def _closed(source_state: str, reason: str) -> dict[str, Any]:
    return _seal(
        {
            "schema_version": ENVELOPE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "presentation_status": PRESENTATION_STATUS,
            "verification_state": "UNKNOWN",
            "envelope_reason": reason,
            "source_state": source_state,
            "source_schema_version": None,
            "source_static_fingerprint": None,
            "source_report_hash": None,
            "source_replay_hash": None,
            "source_registration_hash": None,
            "source_calibration_observations_hash": None,
            "report": None,
            "authority": _authority(),
        }
    )


def _verified(report: dict[str, Any]) -> dict[str, Any]:
    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _closed("INVALID", "G1_REPORT_INVALID")
    return _seal(
        {
            "schema_version": ENVELOPE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "presentation_status": PRESENTATION_STATUS,
            "verification_state": "VERIFIED",
            "envelope_reason": "G1_REPORT_VERIFIED",
            "source_state": report["source_state"],
            "source_schema_version": report["schema_version"],
            "source_static_fingerprint": report["static_fingerprint"],
            "source_report_hash": report["verification_hash"],
            "source_replay_hash": report["source_replay_hash"],
            "source_registration_hash": report["source_registration_hash"],
            "source_calibration_observations_hash": report[
                "source_calibration_observations_hash"
            ],
            "report": deepcopy(report),
            "authority": authority,
        }
    )


def build_strategy_correlation_cross_lag_factor_calibration_presentation_envelope(
    report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
    expected_replay_hash: Any,
    expected_report_hash: Any,
) -> dict[str, Any]:
    try:
        if report is None:
            if type(expected_report_hash) is not str or expected_report_hash != "":
                return _closed("INVALID", "G1_REPORT_INVALID")
            return _closed("NOT_SUPPLIED", "G1_REPORT_NOT_SUPPLIED")

        if type(report) is not dict or not strict_sha256(expected_report_hash):
            return _closed("INVALID", "G1_REPORT_INVALID")

        if (
            report.get("schema_version") != REPORT_SCHEMA
            or report.get("static_fingerprint") != REPORT_STATIC_FINGERPRINT
        ):
            return _closed("UNSUPPORTED", "G1_REPORT_UNSUPPORTED")

        if report.get("verification_hash") != expected_report_hash:
            return _closed("INVALID", "G1_REPORT_INVALID")

        verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_consumer_receipt(
                report,
                replay,
                residualization_registration=residualization_registration,
                calibration_observations=calibration_observations,
                expected_registration_hash=expected_registration_hash,
                expected_calibration_observations_hash=(
                    expected_calibration_observations_hash
                ),
                expected_replay_hash=expected_replay_hash,
            )
        )
        if verified is not True:
            return _closed("INVALID", "G1_REPORT_INVALID")
        return _verified(report)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return _closed("INVALID", "G1_REPORT_INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_presentation_envelope(
    document: Any,
    report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_registration_hash: Any,
    expected_calibration_observations_hash: Any,
    expected_replay_hash: Any,
    expected_report_hash: Any,
) -> bool:
    try:
        rebuilt = build_strategy_correlation_cross_lag_factor_calibration_presentation_envelope(
            report,
            replay,
            residualization_registration,
            calibration_observations,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=(
                expected_calibration_observations_hash
            ),
            expected_replay_hash=expected_replay_hash,
            expected_report_hash=expected_report_hash,
        )
        return strict_json_contract_equal(document, rebuilt)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return False
