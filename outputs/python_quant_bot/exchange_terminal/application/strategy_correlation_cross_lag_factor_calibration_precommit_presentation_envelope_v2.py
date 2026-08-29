from __future__ import annotations

from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5 import (
    REPORT_SCHEMA,
    STATIC_FINGERPRINT as REPORT_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5,
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
    "strategy-correlation-cross-lag-factor-calibration-precommit-"
    "presentation-envelope-v2"
)
STATIC_FINGERPRINT = (
    "20260904-cross-lag-factor-calibration-precommit-presentation-envelope-2"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mount_allowed": False,
        "profitability_claim_allowed": False,
    }


def _permission_axis() -> dict[str, Any]:
    return {
        "label": "PERMISSION",
        "state": "LOCKED",
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_claim_allowed": False,
    }


def _unknown_facts() -> dict[str, bool]:
    return {
        "aggregate_only": True,
        "consumer_verified": False,
        "four_axis_separation_preserved": True,
        "private_ledger_exposed": False,
        "residual_order_independence_proven": False,
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "presentation_hash")


def _unknown(reason: str, source_state: str) -> dict[str, Any]:
    return _seal(
        {
            "schema_version": ENVELOPE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "presentation_status": PRESENTATION_STATUS,
            "source_state": source_state,
            "display_state": "UNKNOWN",
            "display_reason": reason,
            "source_axis": {
                "label": "SOURCE",
                "state": "UNKNOWN",
                "consumer_verification_state": "UNKNOWN",
                "consumer_hash": None,
                "gate_hash": None,
            },
            "gap_axis": {
                "label": "GAP",
                "state": "OPEN",
                "gap_code": "VERIFIED_EVIDENCE_UNAVAILABLE",
                "arbitrary_lag_independence_unresolved": True,
                "external_timing_unresolved": True,
            },
            "maturity_axis": {
                "label": "MATURITY",
                "state": "UNKNOWN",
                "evaluated_lags": [],
                "maximum_evaluated_lag": None,
                "ceiling": None,
                "observed_maximum": None,
                "threshold_relation": "UNKNOWN",
                "unstable_identity_count": None,
            },
            "permission_axis": _permission_axis(),
            "phase_comb": {
                "status": "UNKNOWN",
                "teeth": [],
                "ceiling": None,
                "observed_maximum": None,
                "private_ledger_exposed": False,
            },
            "blocker_count": 1,
            "source_consumer_hash": None,
            "source_gate_hash": None,
            "source_residual_order_gate_v2_hash": None,
            "source_residual_order_gate_v1_hash": None,
            "source_beta_stability_gate_hash": None,
            "source_replay_hash": None,
            "source_registration_hash": None,
            "source_calibration_observations_hash": None,
            "facts": _unknown_facts(),
            "authority": _authority(),
        }
    )


def _observed(report: dict[str, Any]) -> dict[str, Any]:
    verification_state = report["verification_state"]
    if verification_state == "VERIFIED_LOCAL_BINDING":
        display_state = "LOCAL_BINDING"
        display_reason = "MULTI_LAG_LOCAL_BINDING_VERIFIED"
        maturity_state = "LOCAL_MULTI_LAG_BOUND"
        relation = "AT_OR_BELOW_CEILING"
        phase_status = "LOCAL_BINDING"
    elif verification_state == "VERIFIED_BLOCK":
        display_state = "EVIDENCE_BLOCK"
        display_reason = "MULTI_LAG_EVIDENCE_BLOCK_VERIFIED"
        maturity_state = "BLOCKED_BY_EVIDENCE"
        relation = "BLOCKED_OR_ABOVE_CEILING"
        phase_status = "EVIDENCE_BLOCK"
    else:
        return _unknown("REPORT_CONSUMER_NOT_OBSERVED_FOR_PRESENTATION", "UNKNOWN")

    authority = _authority()
    if strict_research_authority_invalid(authority):
        return _unknown("PRESENTATION_ENVELOPE_V2_INTERNAL_AUTHORITY_INVALID", "INVALID")
    lags = report["evaluated_lags"]
    teeth = [
        {"lag": lag, "coverage": "PREREGISTERED", "result_exposed": False}
        for lag in lags
    ]
    return _seal(
        {
            "schema_version": ENVELOPE_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "presentation_status": PRESENTATION_STATUS,
            "source_state": "OBSERVED",
            "display_state": display_state,
            "display_reason": display_reason,
            "source_axis": {
                "label": "SOURCE",
                "state": "VERIFIED",
                "consumer_verification_state": verification_state,
                "consumer_hash": report["verification_hash"],
                "gate_hash": report["source_gate_hash"],
            },
            "gap_axis": {
                "label": "GAP",
                "state": "OPEN",
                "gap_code": "ARBITRARY_LAG_AND_EXTERNAL_TIMING_UNRESOLVED",
                "arbitrary_lag_independence_unresolved": True,
                "external_timing_unresolved": True,
            },
            "maturity_axis": {
                "label": "MATURITY",
                "state": maturity_state,
                "evaluated_lags": lags,
                "maximum_evaluated_lag": report["maximum_evaluated_lag"],
                "ceiling": report[
                    "maximum_allowed_absolute_multi_lag_residual_energy_coupling"
                ],
                "observed_maximum": report[
                    "maximum_observed_absolute_multi_lag_residual_energy_coupling"
                ],
                "threshold_relation": relation,
                "unstable_identity_count": report[
                    "residual_multi_lag_order_unstable_identity_count"
                ],
            },
            "permission_axis": _permission_axis(),
            "phase_comb": {
                "status": phase_status,
                "teeth": teeth,
                "ceiling": report[
                    "maximum_allowed_absolute_multi_lag_residual_energy_coupling"
                ],
                "observed_maximum": report[
                    "maximum_observed_absolute_multi_lag_residual_energy_coupling"
                ],
                "private_ledger_exposed": False,
            },
            "blocker_count": len(report["blockers"]),
            "source_consumer_hash": report["verification_hash"],
            "source_gate_hash": report["source_gate_hash"],
            "source_residual_order_gate_v2_hash": report[
                "source_residual_order_gate_v2_hash"
            ],
            "source_residual_order_gate_v1_hash": report[
                "source_residual_order_gate_v1_hash"
            ],
            "source_beta_stability_gate_hash": report[
                "source_beta_stability_gate_hash"
            ],
            "source_replay_hash": report["source_replay_hash"],
            "source_registration_hash": report["source_registration_hash"],
            "source_calibration_observations_hash": report[
                "source_calibration_observations_hash"
            ],
            "facts": {
                "aggregate_only": report["facts"]["aggregate_only"],
                "consumer_verified": True,
                "four_axis_separation_preserved": True,
                "private_ledger_exposed": False,
                "residual_order_independence_proven": False,
            },
            "authority": authority,
        }
    )


def build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v2(
    report_consumer: Any,
    precommit_gate_v5: Any,
    precommit_gate_v4: Any,
    residual_order_gate_v2: Any,
    precommit_gate_v3: Any,
    residual_order_gate_v1: Any,
    precommit_gate_v2: Any,
    residual_energy_gate: Any,
    precommit_gate_v1: Any,
    beta_stability_gate: Any,
    precommit_declaration: Any,
    source_report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_report_consumer_hash: Any,
    **expected: Any,
) -> dict[str, Any]:
    try:
        if report_consumer is None:
            if (
                type(expected_report_consumer_hash) is not str
                or expected_report_consumer_hash != ""
            ):
                return _unknown("REPORT_CONSUMER_V5_INVALID", "INVALID")
            return _unknown("REPORT_CONSUMER_V5_MISSING", "MISSING")
        if (
            type(report_consumer) is not dict
            or not strict_sha256(expected_report_consumer_hash)
        ):
            return _unknown("REPORT_CONSUMER_V5_INVALID", "INVALID")
        if (
            report_consumer.get("schema_version") != REPORT_SCHEMA
            or report_consumer.get("static_fingerprint")
            != REPORT_STATIC_FINGERPRINT
        ):
            return _unknown("REPORT_CONSUMER_V5_UNSUPPORTED", "UNSUPPORTED")
        if report_consumer.get("verification_hash") != expected_report_consumer_hash:
            return _unknown("REPORT_CONSUMER_V5_INVALID", "INVALID")

        verified = verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5(
            report_consumer,
            precommit_gate_v5,
            precommit_gate_v4,
            residual_order_gate_v2,
            precommit_gate_v3,
            residual_order_gate_v1,
            precommit_gate_v2,
            residual_energy_gate,
            precommit_gate_v1,
            beta_stability_gate,
            precommit_declaration,
            source_report,
            replay,
            residualization_registration,
            calibration_observations,
            **expected,
        )
        if verified is not True:
            return _unknown("REPORT_CONSUMER_V5_INVALID", "INVALID")
        if report_consumer["source_state"] != "OBSERVED":
            return _unknown("REPORT_CONSUMER_V5_NOT_OBSERVED", "UNKNOWN")
        return _observed(report_consumer)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return _unknown("REPORT_CONSUMER_V5_INVALID", "INVALID")


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v2(
    document: Any,
    report_consumer: Any,
    precommit_gate_v5: Any,
    precommit_gate_v4: Any,
    residual_order_gate_v2: Any,
    precommit_gate_v3: Any,
    residual_order_gate_v1: Any,
    precommit_gate_v2: Any,
    residual_energy_gate: Any,
    precommit_gate_v1: Any,
    beta_stability_gate: Any,
    precommit_declaration: Any,
    source_report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    **expected: Any,
) -> bool:
    try:
        rebuilt = build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v2(
            report_consumer,
            precommit_gate_v5,
            precommit_gate_v4,
            residual_order_gate_v2,
            precommit_gate_v3,
            residual_order_gate_v1,
            precommit_gate_v2,
            residual_energy_gate,
            precommit_gate_v1,
            beta_stability_gate,
            precommit_declaration,
            source_report,
            replay,
            residualization_registration,
            calibration_observations,
            **expected,
        )
        return strict_json_contract_equal(document, rebuilt)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError):
        return False
