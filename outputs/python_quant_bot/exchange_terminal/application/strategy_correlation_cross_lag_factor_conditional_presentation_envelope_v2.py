from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_report_consumer_v2 import (
    STATIC_FINGERPRINT as REPORT_STATIC_FINGERPRINT,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_report_consumer_v2 import (
    VERIFICATION_SCHEMA as REPORT_SCHEMA,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_report_consumer_v2 import (
    verify_strategy_correlation_cross_lag_factor_conditional_report_v2,
)


ENVELOPE_SCHEMA = (
    "strategy-correlation-cross-lag-factor-conditional-presentation-envelope-v2"
)
STATIC_FINGERPRINT = "20260822-cross-lag-factor-conditional-presentation-envelope-2"
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"


def _authority(*, global_family_registered: bool = False) -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "global_two_view_multiplicity_registered": global_family_registered,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mounted": False,
        "profitability_claim_allowed": False,
        "report_consumer_v2_activated": False,
        "source_semantics_replayed_in_browser": False,
    }


def _closed(
    verification_state: str,
    reason: str,
    *,
    source_schema_version: str | None = None,
    source_static_fingerprint: str | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "authority": _authority(),
        "envelope_reason": reason,
        "presentation_status": PRESENTATION_STATUS,
        "report": None,
        "schema_version": ENVELOPE_SCHEMA,
        "source_f1_verification_hash": None,
        "source_report_hash": None,
        "source_schema_version": source_schema_version,
        "source_state": "UNKNOWN",
        "source_static_fingerprint": source_static_fingerprint,
        "source_two_view_gate_evaluation_hash": None,
        "static_fingerprint": STATIC_FINGERPRINT,
        "verification_state": verification_state,
    }
    return seal_strict_canonical_document(document, "envelope_hash")


def _verified(report: dict[str, Any]) -> dict[str, Any]:
    facts = report.get("facts")
    registered = (
        type(facts) is dict
        and facts.get("global_two_view_multiplicity_registered") is True
    )
    document: dict[str, Any] = {
        "authority": _authority(global_family_registered=registered),
        "envelope_reason": "F4_REPORT_VERIFIED",
        "presentation_status": PRESENTATION_STATUS,
        "report": deepcopy(report),
        "schema_version": ENVELOPE_SCHEMA,
        "source_f1_verification_hash": report.get(
            "source_f1_verification_hash"
        ),
        "source_report_hash": report.get("verification_hash"),
        "source_schema_version": report.get("schema_version"),
        "source_state": report.get("source_state"),
        "source_static_fingerprint": report.get("static_fingerprint"),
        "source_two_view_gate_evaluation_hash": report.get(
            "source_two_view_gate_evaluation_hash"
        ),
        "static_fingerprint": STATIC_FINGERPRINT,
        "verification_state": "VERIFIED",
    }
    return seal_strict_canonical_document(document, "envelope_hash")


def build_strategy_correlation_cross_lag_factor_conditional_presentation_envelope_v2(
    report: Any,
    v1_receipt: Any,
    two_view_gate: Any,
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
    expected_v1_receipt_hash: Any,
    expected_two_view_gate_hash: Any,
    expected_report_hash: Any,
) -> dict[str, Any]:
    if report is None:
        return _closed("NOT_SUPPLIED", "F4_REPORT_NOT_SUPPLIED")
    if type(report) is not dict:
        return _closed("INVALID", "F4_REPORT_SHAPE_INVALID")
    schema_version = report.get("schema_version")
    static_fingerprint = report.get("static_fingerprint")
    if schema_version != REPORT_SCHEMA or static_fingerprint != REPORT_STATIC_FINGERPRINT:
        return _closed(
            "UNSUPPORTED",
            "F4_REPORT_CONTRACT_UNSUPPORTED",
            source_schema_version=(
                schema_version if type(schema_version) is str else None
            ),
            source_static_fingerprint=(
                static_fingerprint if type(static_fingerprint) is str else None
            ),
        )
    if not strict_sha256(expected_report_hash):
        return _closed("INVALID", "EXPECTED_REPORT_HASH_INVALID")
    if report.get("verification_hash") != expected_report_hash:
        return _closed("INVALID", "F4_REPORT_HASH_MISMATCH")
    try:
        verified = verify_strategy_correlation_cross_lag_factor_conditional_report_v2(
            report,
            v1_receipt,
            two_view_gate,
            family_registration,
            f0_diagnostic,
            preregistered_strata,
            raw_aligned_observations,
            residual_aligned_observations,
            residualization_registration,
            factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_residualization_registration_hash=(
                expected_residualization_registration_hash
            ),
            expected_factor_observations_hash=expected_factor_observations_hash,
            expected_family_registration_hash=expected_family_registration_hash,
            expected_f0_diagnostic_hash=expected_f0_diagnostic_hash,
            expected_residual_input_hash=expected_residual_input_hash,
            expected_v1_receipt_hash=expected_v1_receipt_hash,
            expected_two_view_gate_hash=expected_two_view_gate_hash,
            expected_verification_hash=expected_report_hash,
        )
    except Exception:
        verified = False
    if not verified:
        return _closed(
            "INVALID",
            "F4_REPORT_NOT_VERIFIED",
            source_schema_version=REPORT_SCHEMA,
            source_static_fingerprint=REPORT_STATIC_FINGERPRINT,
        )
    return _verified(report)


def verify_strategy_correlation_cross_lag_factor_conditional_presentation_envelope_v2(
    document: Any,
    report: Any,
    v1_receipt: Any,
    two_view_gate: Any,
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
    expected_v1_receipt_hash: Any,
    expected_two_view_gate_hash: Any,
    expected_report_hash: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        expected = build_strategy_correlation_cross_lag_factor_conditional_presentation_envelope_v2(
            report,
            v1_receipt,
            two_view_gate,
            family_registration,
            f0_diagnostic,
            preregistered_strata,
            raw_aligned_observations,
            residual_aligned_observations,
            residualization_registration,
            factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_residualization_registration_hash=(
                expected_residualization_registration_hash
            ),
            expected_factor_observations_hash=expected_factor_observations_hash,
            expected_family_registration_hash=expected_family_registration_hash,
            expected_f0_diagnostic_hash=expected_f0_diagnostic_hash,
            expected_residual_input_hash=expected_residual_input_hash,
            expected_v1_receipt_hash=expected_v1_receipt_hash,
            expected_two_view_gate_hash=expected_two_view_gate_hash,
            expected_report_hash=expected_report_hash,
        )
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
