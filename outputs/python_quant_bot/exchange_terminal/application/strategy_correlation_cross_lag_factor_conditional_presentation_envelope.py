from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
    strict_sha256,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_report_consumer import (
    STATIC_FINGERPRINT as RECEIPT_STATIC_FINGERPRINT,
    VERIFICATION_SCHEMA as RECEIPT_SCHEMA,
    verify_strategy_correlation_cross_lag_factor_conditional_consumer_receipt,
)


ENVELOPE_SCHEMA = (
    "strategy-correlation-cross-lag-factor-conditional-presentation-envelope-v1"
)
STATIC_FINGERPRINT = "20260822-cross-lag-factor-conditional-presentation-envelope-1"
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "common_factor_causality_proven": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "factor_calibration_attested": False,
        "global_two_view_multiplicity_registered": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mounted": False,
        "profitability_claim_allowed": False,
        "raw_independence_proven": False,
        "residual_independence_proven": False,
        "source_semantics_replayed_in_browser": False,
    }


def _closed(verification_state: str, reason: str) -> dict[str, Any]:
    source_state = "NOT_SUPPLIED" if verification_state == "NOT_SUPPLIED" else "INVALID"
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "blockers": [reason],
            "envelope_reason": reason,
            "presentation_status": PRESENTATION_STATUS,
            "report": None,
            "schema_version": ENVELOPE_SCHEMA,
            "source_diagnostic_hash": None,
            "source_receipt_hash": None,
            "source_schema_version": None,
            "source_state": source_state,
            "source_static_fingerprint": None,
            "source_v1_diagnostic_hash": None,
            "static_fingerprint": STATIC_FINGERPRINT,
            "verification_state": verification_state,
        },
        "envelope_hash",
    )


def _verified(receipt: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "blockers": [],
            "envelope_reason": "F1_RECEIPT_VERIFIED",
            "presentation_status": PRESENTATION_STATUS,
            "report": deepcopy(receipt),
            "schema_version": ENVELOPE_SCHEMA,
            "source_diagnostic_hash": receipt.get("source_diagnostic_hash"),
            "source_receipt_hash": receipt.get("verification_hash"),
            "source_schema_version": RECEIPT_SCHEMA,
            "source_state": receipt.get("source_state"),
            "source_static_fingerprint": RECEIPT_STATIC_FINGERPRINT,
            "source_v1_diagnostic_hash": receipt.get("source_v1_diagnostic_hash"),
            "static_fingerprint": STATIC_FINGERPRINT,
            "verification_state": "VERIFIED",
        },
        "envelope_hash",
    )


def build_strategy_correlation_cross_lag_factor_conditional_presentation_envelope(
    receipt: Any,
    diagnostic: Any,
    *,
    preregistered_strata: Any,
    aligned_observations: Any,
    residualization_registration: Any,
    factor_observations: Any,
    expected_stratum_assignment_hash: Any,
    expected_registration_hash: Any,
    expected_factor_observations_hash: Any,
    expected_diagnostic_hash: Any,
    expected_receipt_hash: Any,
) -> dict[str, Any]:
    try:
        if receipt is None:
            return _closed("NOT_SUPPLIED", "F1_RECEIPT_NOT_SUPPLIED")
        if type(receipt) is not dict:
            return _closed("INVALID", "F1_RECEIPT_INVALID")
        if receipt.get("schema_version") != RECEIPT_SCHEMA:
            return _closed("INVALID", "F1_RECEIPT_INVALID")
        if receipt.get("static_fingerprint") != RECEIPT_STATIC_FINGERPRINT:
            return _closed("INVALID", "F1_RECEIPT_INVALID")
        if not strict_sha256(expected_receipt_hash):
            return _closed("INVALID", "F1_RECEIPT_INVALID")
        if receipt.get("verification_hash") != expected_receipt_hash:
            return _closed("INVALID", "F1_RECEIPT_INVALID")
        if not verify_strategy_correlation_cross_lag_factor_conditional_consumer_receipt(
            receipt,
            diagnostic,
            preregistered_strata=preregistered_strata,
            aligned_observations=aligned_observations,
            residualization_registration=residualization_registration,
            factor_observations=factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_registration_hash=expected_registration_hash,
            expected_factor_observations_hash=expected_factor_observations_hash,
            expected_diagnostic_hash=expected_diagnostic_hash,
        ):
            return _closed("INVALID", "F1_RECEIPT_INVALID")
        return _verified(receipt)
    except Exception:
        return _closed("INVALID", "F1_RECEIPT_INVALID")


def verify_strategy_correlation_cross_lag_factor_conditional_presentation_envelope(
    document: Any,
    receipt: Any,
    diagnostic: Any,
    *,
    preregistered_strata: Any,
    aligned_observations: Any,
    residualization_registration: Any,
    factor_observations: Any,
    expected_stratum_assignment_hash: Any,
    expected_registration_hash: Any,
    expected_factor_observations_hash: Any,
    expected_diagnostic_hash: Any,
    expected_receipt_hash: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        if not strict_sha256(document.get("envelope_hash")):
            return False
        expected = build_strategy_correlation_cross_lag_factor_conditional_presentation_envelope(
            receipt,
            diagnostic,
            preregistered_strata=preregistered_strata,
            aligned_observations=aligned_observations,
            residualization_registration=residualization_registration,
            factor_observations=factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_registration_hash=expected_registration_hash,
            expected_factor_observations_hash=expected_factor_observations_hash,
            expected_diagnostic_hash=expected_diagnostic_hash,
            expected_receipt_hash=expected_receipt_hash,
        )
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
