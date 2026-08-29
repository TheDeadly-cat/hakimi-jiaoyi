from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7 import (
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v4"
)
STATIC_FINGERPRINT = (
    "20260914-cross-lag-factor-calibration-precommit-presentation-envelope-4"
)
SOURCE_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-report-consumer-verification-v7"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"
EVALUATED_LAGS = (1, 2, 3, 4, 5, 6)
OMNIBUS_BAND_LAGS = (4, 5, 6)


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
        "finite_horizon_omnibus_guard_bound": False,
        "four_axis_separation_preserved": True,
        "lags_above_six_unresolved": True,
        "omnibus_quadratic_energy_threshold_passed": False,
        "private_ledger_exposed": False,
        "residual_order_independence_proven": False,
    }


def _teeth() -> list[dict[str, Any]]:
    return [
        {
            "lag": lag,
            "coverage": (
                "BASELINE_PREREGISTERED"
                if lag < min(OMNIBUS_BAND_LAGS)
                else "OMNIBUS_PREREGISTERED"
            ),
            "result_exposed": False,
        }
        for lag in EVALUATED_LAGS
    ]


def _base_projection() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "presentation_status": PRESENTATION_STATUS,
        "display_state": "UNKNOWN",
        "display_reason": "SOURCE_NOT_EVALUATED",
        "source_state": "UNKNOWN",
        "source_consumer_hash": None,
        "source_precommit_gate_v7_hash": None,
        "source_report_consumer_v6_hash": None,
        "source_precommit_gate_v6_hash": None,
        "source_omnibus_gate_v1_hash": None,
        "source_report_consumer_v5_hash": None,
        "source_precommit_gate_v5_hash": None,
        "source_residual_order_gate_v3_hash": None,
        "source_precommit_gate_v4_hash": None,
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
            "precommit_gate_v7_hash": None,
            "omnibus_gate_v1_hash": None,
        },
        "gap_axis": {
            "label": "GAP",
            "state": "OPEN",
            "gap_code": "LAGS_ABOVE_SIX_AND_EXTERNAL_TIMING_UNRESOLVED",
            "arbitrary_lag_independence_unresolved": True,
            "external_timing_unresolved": True,
            "lags_above_six_unresolved": True,
        },
        "maturity_axis": {
            "label": "MATURITY",
            "state": "UNKNOWN",
            "evaluated_lags": list(EVALUATED_LAGS),
            "omnibus_band_lags": list(OMNIBUS_BAND_LAGS),
            "maximum_evaluated_lag": max(EVALUATED_LAGS),
            "metric": "LAG_BAND_QUADRATIC_ENERGY",
            "observed_maximum": None,
            "ceiling": "0.64",
            "threshold_relation": "UNKNOWN",
            "fold_count": None,
            "unstable_identity_count": None,
        },
        "permission_axis": _permission_axis(),
        "phase_comb": {
            "status": "UNKNOWN",
            "teeth": _teeth(),
            "omnibus_band_lags": list(OMNIBUS_BAND_LAGS),
            "observed_maximum": None,
            "ceiling": "0.64",
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
        display_reason = "FINITE_HORIZON_LOCAL_BINDING_VERIFIED"
        maturity_state = "LOCAL_FINITE_HORIZON_BOUND"
        threshold_relation = "AT_OR_BELOW_CEILING"
    else:
        display_state = "EVIDENCE_BLOCK"
        display_reason = "FINITE_HORIZON_EVIDENCE_BLOCK_VERIFIED"
        maturity_state = "EVIDENCE_BLOCK"
        threshold_relation = "SOURCE_BLOCK_VERIFIED"

    observed_maximum = report.get(
        "maximum_observed_lag_band_quadratic_energy"
    )
    ceiling = report.get("maximum_allowed_lag_band_quadratic_energy")
    consumer_hash = report["verification_hash"]
    precommit_gate_v7_hash = report["source_precommit_gate_v7_hash"]
    omnibus_gate_v1_hash = report["source_omnibus_gate_v1_hash"]
    source_facts = report.get("facts", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "presentation_status": PRESENTATION_STATUS,
        "display_state": display_state,
        "display_reason": display_reason,
        "source_state": "OBSERVED",
        "source_consumer_hash": consumer_hash,
        "source_precommit_gate_v7_hash": precommit_gate_v7_hash,
        "source_report_consumer_v6_hash": report.get(
            "source_report_consumer_v6_hash"
        ),
        "source_precommit_gate_v6_hash": report.get(
            "source_precommit_gate_v6_hash"
        ),
        "source_omnibus_gate_v1_hash": omnibus_gate_v1_hash,
        "source_report_consumer_v5_hash": report.get(
            "source_report_consumer_v5_hash"
        ),
        "source_precommit_gate_v5_hash": report.get(
            "source_precommit_gate_v5_hash"
        ),
        "source_residual_order_gate_v3_hash": report.get(
            "source_residual_order_gate_v3_hash"
        ),
        "source_precommit_gate_v4_hash": report.get(
            "source_precommit_gate_v4_hash"
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
            "precommit_gate_v7_hash": precommit_gate_v7_hash,
            "omnibus_gate_v1_hash": omnibus_gate_v1_hash,
        },
        "gap_axis": {
            "label": "GAP",
            "state": "OPEN",
            "gap_code": "LAGS_ABOVE_SIX_AND_EXTERNAL_TIMING_UNRESOLVED",
            "arbitrary_lag_independence_unresolved": True,
            "external_timing_unresolved": True,
            "lags_above_six_unresolved": True,
        },
        "maturity_axis": {
            "label": "MATURITY",
            "state": maturity_state,
            "evaluated_lags": list(report.get("evaluated_lags", [])),
            "omnibus_band_lags": list(report.get("omnibus_band_lags", [])),
            "maximum_evaluated_lag": report.get("maximum_evaluated_lag"),
            "metric": "LAG_BAND_QUADRATIC_ENERGY",
            "observed_maximum": observed_maximum,
            "ceiling": ceiling,
            "threshold_relation": threshold_relation,
            "fold_count": report.get("fold_count"),
            "unstable_identity_count": report.get("unstable_identity_count"),
        },
        "permission_axis": _permission_axis(),
        "phase_comb": {
            "status": display_state,
            "teeth": _teeth(),
            "omnibus_band_lags": list(report.get("omnibus_band_lags", [])),
            "observed_maximum": observed_maximum,
            "ceiling": ceiling,
            "private_ledger_exposed": False,
        },
        "blocker_count": len(report.get("blockers", [])),
        "facts": {
            **_facts(),
            "consumer_verified": True,
            "finite_horizon_omnibus_guard_bound": bool(
                source_facts.get("finite_horizon_omnibus_guard_bound")
            ),
            "omnibus_quadratic_energy_threshold_passed": bool(
                source_facts.get("omnibus_quadratic_energy_threshold_passed")
            ),
        },
        "authority": _authority(),
    }


def build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v4(
    report_consumer_v7: Any,
    precommit_gate_v7: Any,
    report_consumer_v6: Any,
    precommit_gate_v6: Any,
    omnibus_gate_v1: Any,
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
    report: Any,
    replay: Any,
    residualization_registration: Any,
    calibration_observations: Any,
    *,
    expected_report_consumer_v7_hash: Any,
    **expected: Any,
) -> dict[str, Any]:
    if not isinstance(report_consumer_v7, dict):
        return _unknown("MISSING_REPORT_CONSUMER_V7")
    if report_consumer_v7.get("schema_version") != SOURCE_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_REPORT_CONSUMER_V7", "UNSUPPORTED")
    if not _hash_matches(
        expected_report_consumer_v7_hash,
        report_consumer_v7.get("verification_hash"),
    ):
        return _unknown("EXPECTED_REPORT_CONSUMER_V7_HASH_MISMATCH")
    source_args = (
        precommit_gate_v7,
        report_consumer_v6,
        precommit_gate_v6,
        omnibus_gate_v1,
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
        report,
        replay,
        residualization_registration,
        calibration_observations,
    )
    if not verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7(
        report_consumer_v7,
        *source_args,
        **expected,
    ):
        return _unknown("REPORT_CONSUMER_V7_OR_CONTEXT_INVALID")
    if not _hash_matches(
        expected.get("expected_precommit_gate_v7_hash"),
        report_consumer_v7.get("source_precommit_gate_v7_hash"),
    ):
        return _unknown("REPORT_CONSUMER_V7_GATE_HASH_MISMATCH")
    if not _hash_matches(
        expected.get("expected_omnibus_gate_v1_hash"),
        report_consumer_v7.get("source_omnibus_gate_v1_hash"),
    ):
        return _unknown("REPORT_CONSUMER_V7_OMNIBUS_HASH_MISMATCH")
    if report_consumer_v7.get("verification_state") not in (
        "VERIFIED_LOCAL_BINDING",
        "VERIFIED_BLOCK",
    ):
        return _unknown("REPORT_CONSUMER_V7_STATE_UNKNOWN")
    return _seal(_observed(report_consumer_v7))


def verify_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v4(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    rebuilt = build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v4(
        *args,
        **expected,
    )
    return strict_json_contract_equal(document, rebuilt)
