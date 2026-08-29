from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_report_consumer import (
    verify_strategy_correlation_cross_lag_factor_conditional_consumer_receipt,
)
from exchange_terminal.services.strategy_correlation_cross_lag_two_view_multiplicity_gate import (
    verify_strategy_correlation_cross_lag_two_view_multiplicity_gate,
)


VERIFICATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-conditional-report-consumer-"
    "verification-v2"
)
STATIC_FINGERPRINT = "20260822-cross-lag-factor-conditional-report-consumer-2"
PERMISSION_STATE = "RESEARCH_ONLY_NO_EXECUTION_AUTHORITY"
SUPERSEDED_V1_BLOCKERS = {
    "FACTOR_CONDITIONAL_REPORT_NOT_ACTIVATED",
    "GLOBAL_TWO_VIEW_MULTIPLICITY_NOT_REGISTERED",
}


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "global_independence_proven": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "raw_independence_proven": False,
        "report_consumer_v2_activated": False,
        "residual_independence_proven": False,
    }


def _facts(
    *,
    f1_verified: bool,
    f3_verified: bool,
    cross_links_verified: bool,
    gate_facts: Any = None,
) -> dict[str, bool]:
    source = gate_facts if type(gate_facts) is dict else {}
    return {
        "factor_calibration_attested": (
            source.get("factor_calibration_attested") is True
        ),
        "formula_parity_verified": source.get("formula_parity_verified") is True,
        "global_two_view_multiplicity_registered": (
            source.get("global_two_view_multiplicity_registered") is True
        ),
        "registration_timing_attested": (
            source.get("registration_timing_attested") is True
        ),
        "report_consumer_v2_activated": False,
        "source_block_preserved": source.get("source_block_preserved") is True,
        "source_cross_links_verified": cross_links_verified,
        "source_f1_receipt_verified": f1_verified,
        "source_f3_gate_verified": f3_verified,
    }


def _unknown(reason: str) -> dict[str, Any]:
    document: dict[str, Any] = {
        "authority": _authority(),
        "blockers": [reason],
        "correction_method": None,
        "dependence_threshold": None,
        "family_alpha": None,
        "facts": _facts(
            f1_verified=False,
            f3_verified=False,
            cross_links_verified=False,
        ),
        "gap_state": "UNKNOWN",
        "global_dependent_test_count": None,
        "global_recalibrated_decision": "UNKNOWN",
        "global_test_count": None,
        "lags": [],
        "maturity_state": "UNKNOWN",
        "per_view_test_count": None,
        "permission_state": PERMISSION_STATE,
        "report_state": "UNKNOWN",
        "schema_version": VERIFICATION_SCHEMA,
        "source_f0_diagnostic_hash": None,
        "source_f1_gap_state": None,
        "source_f1_maturity_state": None,
        "source_f1_report_state": None,
        "source_f1_verification_hash": None,
        "source_family_registration_hash": None,
        "source_raw_evaluation_hash": None,
        "source_residual_evaluation_hash": None,
        "source_residual_input_hash": None,
        "source_state": "UNKNOWN",
        "source_two_view_gate_evaluation_hash": None,
        "static_fingerprint": STATIC_FINGERPRINT,
        "view_count": None,
        "view_summaries": [],
        "views": [],
    }
    return seal_strict_canonical_document(document, "verification_hash")


def _merged_blockers(v1_receipt: dict[str, Any], gate: dict[str, Any]) -> list[str] | None:
    v1_blockers = v1_receipt.get("blockers")
    gate_blockers = gate.get("blockers")
    if type(v1_blockers) is not list or type(gate_blockers) is not list:
        return None
    if any(type(value) is not str for value in [*v1_blockers, *gate_blockers]):
        return None
    merged: list[str] = []
    for blocker in [*v1_blockers, *gate_blockers]:
        if blocker in SUPERSEDED_V1_BLOCKERS or blocker in merged:
            continue
        merged.append(blocker)
    merged.append("FACTOR_CONDITIONAL_REPORT_V2_NOT_ACTIVATED")
    return merged


def _cross_links_match(
    v1_receipt: dict[str, Any],
    gate: dict[str, Any],
    family_registration: dict[str, Any],
    *,
    expected_stratum_assignment_hash: str,
    expected_residualization_registration_hash: str,
    expected_factor_observations_hash: str,
    expected_family_registration_hash: str,
    expected_f0_diagnostic_hash: str,
    expected_residual_input_hash: str,
) -> bool:
    equalities = (
        (v1_receipt.get("source_diagnostic_hash"), expected_f0_diagnostic_hash),
        (gate.get("f0_diagnostic_hash"), expected_f0_diagnostic_hash),
        (
            v1_receipt.get("source_factor_observations_hash"),
            expected_factor_observations_hash,
        ),
        (
            v1_receipt.get("source_registration_hash"),
            expected_residualization_registration_hash,
        ),
        (gate.get("stratum_assignment_hash"), expected_stratum_assignment_hash),
        (gate.get("family_registration_hash"), expected_family_registration_hash),
        (
            family_registration.get("registration_hash"),
            expected_family_registration_hash,
        ),
        (
            v1_receipt.get("source_residual_input_hash"),
            expected_residual_input_hash,
        ),
        (gate.get("residual_input_hash"), expected_residual_input_hash),
        (
            v1_receipt.get("source_raw_evaluation_hash"),
            gate.get("raw_evaluation_hash"),
        ),
        (
            v1_receipt.get("source_residual_evaluation_hash"),
            gate.get("residual_evaluation_hash"),
        ),
        (
            v1_receipt.get("source_identity_order_hash"),
            family_registration.get("identity_order_hash"),
        ),
    )
    return all(type(left) is str and left == right for left, right in equalities)


def consume_strategy_correlation_cross_lag_factor_conditional_report_v2(
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
) -> dict[str, Any]:
    expected_hashes = (
        expected_stratum_assignment_hash,
        expected_residualization_registration_hash,
        expected_factor_observations_hash,
        expected_family_registration_hash,
        expected_f0_diagnostic_hash,
        expected_residual_input_hash,
        expected_v1_receipt_hash,
        expected_two_view_gate_hash,
    )
    if not all(strict_sha256(value) for value in expected_hashes):
        return _unknown("EXPECTED_HASH_INVALID")
    if any(
        type(value) is not dict
        for value in (v1_receipt, two_view_gate, family_registration, f0_diagnostic)
    ):
        return _unknown("SOURCE_SHAPE_INVALID")
    if v1_receipt.get("verification_hash") != expected_v1_receipt_hash:
        return _unknown("F1_RECEIPT_HASH_MISMATCH")
    if two_view_gate.get("evaluation_hash") != expected_two_view_gate_hash:
        return _unknown("F3_GATE_HASH_MISMATCH")

    try:
        f1_verified = (
            verify_strategy_correlation_cross_lag_factor_conditional_consumer_receipt(
                v1_receipt,
                f0_diagnostic,
                preregistered_strata=preregistered_strata,
                aligned_observations=raw_aligned_observations,
                residualization_registration=residualization_registration,
                factor_observations=factor_observations,
                expected_stratum_assignment_hash=expected_stratum_assignment_hash,
                expected_registration_hash=(
                    expected_residualization_registration_hash
                ),
                expected_factor_observations_hash=(
                    expected_factor_observations_hash
                ),
                expected_diagnostic_hash=expected_f0_diagnostic_hash,
            )
        )
        if not f1_verified:
            return _unknown("F1_RECEIPT_NOT_VERIFIED")
        f3_verified = verify_strategy_correlation_cross_lag_two_view_multiplicity_gate(
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
            expected_evaluation_hash=expected_two_view_gate_hash,
        )
        if not f3_verified:
            return _unknown("F3_GATE_NOT_VERIFIED")
        if v1_receipt.get("source_state") != "OBSERVED":
            return _unknown("F1_RECEIPT_NOT_OBSERVED")
        if two_view_gate.get("source_state") != "OBSERVED":
            return _unknown("F3_GATE_NOT_OBSERVED")
        if not _cross_links_match(
            v1_receipt,
            two_view_gate,
            family_registration,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_residualization_registration_hash=(
                expected_residualization_registration_hash
            ),
            expected_factor_observations_hash=expected_factor_observations_hash,
            expected_family_registration_hash=expected_family_registration_hash,
            expected_f0_diagnostic_hash=expected_f0_diagnostic_hash,
            expected_residual_input_hash=expected_residual_input_hash,
        ):
            return _unknown("SOURCE_CROSS_LINK_MISMATCH")
        blockers = _merged_blockers(v1_receipt, two_view_gate)
        if blockers is None:
            return _unknown("SOURCE_BLOCKERS_INVALID")
        decision = two_view_gate.get("gate_decision")
        if decision not in ("PASS", "BLOCK"):
            return _unknown("F3_GATE_DECISION_INVALID")
        view_summaries = two_view_gate.get("view_summaries")
        views = two_view_gate.get("views")
        lags = two_view_gate.get("lags")
        if any(type(value) is not list for value in (view_summaries, views, lags)):
            return _unknown("F3_AGGREGATE_SHAPE_INVALID")

        blocked = decision == "BLOCK"
        document: dict[str, Any] = {
            "authority": _authority(),
            "blockers": blockers,
            "correction_method": two_view_gate.get("correction_method"),
            "dependence_threshold": two_view_gate.get("dependence_threshold"),
            "family_alpha": two_view_gate.get("family_alpha"),
            "facts": _facts(
                f1_verified=True,
                f3_verified=True,
                cross_links_verified=True,
                gate_facts=two_view_gate.get("facts"),
            ),
            "gap_state": (
                "GLOBAL_TWO_VIEW_DEPENDENCE_OBSERVED"
                if blocked
                else "NO_GLOBAL_TWO_VIEW_DEPENDENCE_OBSERVED"
            ),
            "global_dependent_test_count": two_view_gate.get(
                "global_dependent_test_count"
            ),
            "global_recalibrated_decision": two_view_gate.get(
                "global_recalibrated_decision"
            ),
            "global_test_count": two_view_gate.get("global_test_count"),
            "lags": deepcopy(lags),
            "maturity_state": two_view_gate.get("maturity_state"),
            "per_view_test_count": two_view_gate.get("per_view_test_count"),
            "permission_state": PERMISSION_STATE,
            "report_state": (
                "GLOBAL_TWO_VIEW_FAMILY_BLOCKED"
                if blocked
                else "GLOBAL_TWO_VIEW_FAMILY_OBSERVED_NOT_ACTIVATED"
            ),
            "schema_version": VERIFICATION_SCHEMA,
            "source_f0_diagnostic_hash": expected_f0_diagnostic_hash,
            "source_f1_gap_state": v1_receipt.get("gap_state"),
            "source_f1_maturity_state": v1_receipt.get("maturity_state"),
            "source_f1_report_state": v1_receipt.get("report_state"),
            "source_f1_verification_hash": expected_v1_receipt_hash,
            "source_family_registration_hash": expected_family_registration_hash,
            "source_raw_evaluation_hash": two_view_gate.get("raw_evaluation_hash"),
            "source_residual_evaluation_hash": two_view_gate.get(
                "residual_evaluation_hash"
            ),
            "source_residual_input_hash": expected_residual_input_hash,
            "source_state": "OBSERVED",
            "source_two_view_gate_evaluation_hash": expected_two_view_gate_hash,
            "static_fingerprint": STATIC_FINGERPRINT,
            "view_count": two_view_gate.get("view_count"),
            "view_summaries": deepcopy(view_summaries),
            "views": deepcopy(views),
        }
        return seal_strict_canonical_document(document, "verification_hash")
    except Exception:
        return _unknown("UNEXPECTED_CONSUMER_ERROR")


def verify_strategy_correlation_cross_lag_factor_conditional_report_v2(
    document: Any,
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
    expected_verification_hash: Any,
) -> bool:
    try:
        if type(document) is not dict or not strict_sha256(expected_verification_hash):
            return False
        if document.get("verification_hash") != expected_verification_hash:
            return False
        expected = consume_strategy_correlation_cross_lag_factor_conditional_report_v2(
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
        )
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
