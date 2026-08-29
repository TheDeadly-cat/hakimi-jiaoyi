from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6 import (
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v3"
)
STATIC_FINGERPRINT = (
    "20260909-cross-lag-factor-calibration-precommit-presentation-envelope-3"
)
SOURCE_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-report-consumer-verification-v6"
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
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "aggregate_only": True,
        "consumer_verified": False,
        "four_axis_separation_preserved": True,
        "private_ledger_exposed": False,
        "residual_order_independence_proven": False,
    }


def _base_projection() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "presentation_status": PRESENTATION_STATUS,
        "display_state": "UNKNOWN",
        "display_reason": "SOURCE_NOT_EVALUATED",
        "source_state": "UNKNOWN",
        "source_consumer_hash": None,
        "source_gate_hash": None,
        "source_report_consumer_v5_hash": None,
        "source_precommit_gate_v5_hash": None,
        "source_residual_order_gate_v3_hash": None,
        "source_residual_order_gate_v2_hash": None,
        "source_residual_order_gate_v1_hash": None,
        "source_beta_stability_gate_hash": None,
        "source_replay_hash": None,
        "source_registration_hash": None,
        "source_calibration_observations_hash": None,
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
            "gap_code": "ARBITRARY_LAG_AND_EXTERNAL_TIMING_UNRESOLVED",
            "arbitrary_lag_independence_unresolved": True,
            "external_timing_unresolved": True,
        },
        "maturity_axis": {
            "label": "MATURITY",
            "state": "UNKNOWN",
            "evaluated_lags": [1, 2, 3],
            "maximum_evaluated_lag": 3,
            "observed_maximum": None,
            "ceiling": None,
            "threshold_relation": "UNKNOWN",
            "unstable_identity_count": None,
        },
        "permission_axis": _permission_axis(),
        "phase_comb": {
            "status": "UNKNOWN",
            "teeth": [
                {"lag": 1, "coverage": "PREREGISTERED", "result_exposed": False},
                {"lag": 2, "coverage": "PREREGISTERED", "result_exposed": False},
                {"lag": 3, "coverage": "PREREGISTERED", "result_exposed": False},
            ],
            "observed_maximum": None,
            "ceiling": None,
            "private_ledger_exposed": False,
        },
        "blocker_count": 1,
        "facts": _facts(),
        "authority": _authority(),
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "presentation_hash")


def _unknown(reason: str, source_state: str = "UNKNOWN") -> dict[str, Any]:
    projection = _base_projection()
    projection["source_state"] = source_state
    projection["display_reason"] = reason
    return _seal(projection)


def _hash_matches(expected: Any, actual: Any) -> bool:
    return (
        isinstance(expected, str)
        and isinstance(actual, str)
        and expected == actual
    )


def _observed(report: dict[str, Any]) -> dict[str, Any]:
    verification_state = report["verification_state"]
    if verification_state == "VERIFIED_LOCAL_BINDING":
        display_state = "LOCAL_BINDING"
        display_reason = "THREE_LAG_LOCAL_BINDING_VERIFIED"
        maturity_state = "LOCAL_THREE_LAG_BOUND"
        threshold_relation = "AT_OR_BELOW_CEILING"
    else:
        display_state = "EVIDENCE_BLOCK"
        display_reason = "THREE_LAG_EVIDENCE_BLOCK_VERIFIED"
        maturity_state = "EVIDENCE_BLOCK"
        threshold_relation = "SOURCE_BLOCK_VERIFIED"

    observed_maximum = report.get(
        "maximum_observed_absolute_three_lag_residual_energy_coupling"
    )
    ceiling = report.get(
        "maximum_allowed_absolute_three_lag_residual_energy_coupling"
    )
    consumer_hash = report["verification_hash"]
    gate_hash = report["source_gate_hash"]
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "presentation_status": PRESENTATION_STATUS,
        "display_state": display_state,
        "display_reason": display_reason,
        "source_state": "OBSERVED",
        "source_consumer_hash": consumer_hash,
        "source_gate_hash": gate_hash,
        "source_report_consumer_v5_hash": report.get(
            "source_report_consumer_v5_hash"
        ),
        "source_precommit_gate_v5_hash": report.get(
            "source_precommit_gate_v5_hash"
        ),
        "source_residual_order_gate_v3_hash": report.get(
            "source_residual_order_gate_v3_hash"
        ),
        "source_residual_order_gate_v2_hash": report.get(
            "source_residual_order_gate_v2_hash"
        ),
        "source_residual_order_gate_v1_hash": report.get(
            "source_residual_order_gate_v1_hash"
        ),
        "source_beta_stability_gate_hash": report.get(
            "source_beta_stability_gate_hash"
        ),
        "source_replay_hash": report.get("source_replay_hash"),
        "source_registration_hash": report.get("source_registration_hash"),
        "source_calibration_observations_hash": report.get(
            "source_calibration_observations_hash"
        ),
        "source_axis": {
            "label": "SOURCE",
            "state": "VERIFIED",
            "consumer_verification_state": verification_state,
            "consumer_hash": consumer_hash,
            "gate_hash": gate_hash,
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
            "evaluated_lags": [1, 2, 3],
            "maximum_evaluated_lag": 3,
            "observed_maximum": observed_maximum,
            "ceiling": ceiling,
            "threshold_relation": threshold_relation,
            "unstable_identity_count": report.get(
                "residual_three_lag_order_unstable_identity_count"
            ),
        },
        "permission_axis": _permission_axis(),
        "phase_comb": {
            "status": display_state,
            "teeth": [
                {"lag": 1, "coverage": "PREREGISTERED", "result_exposed": False},
                {"lag": 2, "coverage": "PREREGISTERED", "result_exposed": False},
                {"lag": 3, "coverage": "PREREGISTERED", "result_exposed": False},
            ],
            "observed_maximum": observed_maximum,
            "ceiling": ceiling,
            "private_ledger_exposed": False,
        },
        "blocker_count": len(report.get("blockers", [])),
        "facts": {
            **_facts(),
            "consumer_verified": True,
        },
        "authority": _authority(),
    }


def build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3(
    report_consumer_v6: Any,
    precommit_gate_v6: Any,
    report_consumer_v5: Any,
    precommit_gate_v5: Any,
    residual_order_gate_v3: Any,
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
    expected_report_consumer_v6_hash: Any,
    **expected: Any,
) -> dict[str, Any]:
    if not isinstance(report_consumer_v6, dict):
        return _unknown("MISSING_REPORT_CONSUMER_V6")
    if report_consumer_v6.get("schema_version") != SOURCE_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_REPORT_CONSUMER_V6", "UNSUPPORTED")
    if not _hash_matches(
        expected_report_consumer_v6_hash,
        report_consumer_v6.get("verification_hash"),
    ):
        return _unknown("EXPECTED_REPORT_CONSUMER_V6_HASH_MISMATCH")
    source_args = (
        precommit_gate_v6,
        report_consumer_v5,
        precommit_gate_v5,
        residual_order_gate_v3,
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
    )
    if not verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6(
        report_consumer_v6,
        *source_args,
        **expected,
    ):
        return _unknown("REPORT_CONSUMER_V6_OR_CONTEXT_INVALID")
    if not _hash_matches(
        expected.get("expected_precommit_gate_v6_hash"),
        report_consumer_v6.get("source_gate_hash"),
    ):
        return _unknown("REPORT_CONSUMER_V6_GATE_HASH_MISMATCH")
    if report_consumer_v6.get("verification_state") not in (
        "VERIFIED_LOCAL_BINDING",
        "VERIFIED_BLOCK",
    ):
        return _unknown("REPORT_CONSUMER_V6_STATE_UNKNOWN")
    return _seal(_observed(report_consumer_v6))


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    rebuilt = build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3(
        *args,
        **expected,
    )
    return strict_json_contract_equal(document, rebuilt)
