from __future__ import annotations

from datetime import date
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import (
    strict_iso_date,
    strict_sha256,
    strict_utc_second_timestamp,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7 import (
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-preregistration-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260916-cross-lag-factor-calibration-long-horizon-preregistration-1"
)
SOURCE_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-precommit-report-consumer-verification-v7"
)
SOURCE_POSITIVE_STATE = "VERIFIED_LOCAL_BINDING"
PROTOCOL_ID = "FUTURE_FACTOR_RESIDUAL_ORDER_LONG_HORIZON_V1"
MINIMUM_ROWS_PER_FOLD = 20
EVALUATED_LAGS = tuple(range(1, 13))
INHERITED_LAGS = tuple(range(1, 7))
EXTENSION_LAGS = tuple(range(7, 13))
MAXIMUM_EVALUATED_LAG = max(EVALUATED_LAGS)
MINIMUM_PAIRS_AT_MAXIMUM_LAG = MINIMUM_ROWS_PER_FOLD - MAXIMUM_EVALUATED_LAG
TAIL_SCORE = "SUM_SQUARED_ABSOLUTE_RESIDUAL_ENERGY_COUPLING"
TAIL_QUADRATIC_ENERGY_CEILING = "0.64"


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_time_anchor_verified": False,
        "future_evaluation_allowed": False,
        "future_observation_collection_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "evaluation_activated": False,
        "external_time_anchor_verified": False,
        "long_horizon_protocol_pinned": False,
        "minimum_pair_support_pinned": False,
        "observations_collected": False,
        "residual_order_independence_proven": False,
        "result_available": False,
        "source_consumer_v7_verified": False,
        "source_local_binding_required": True,
        "tail_score_pinned": False,
    }


def _base_projection() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source_state": "UNKNOWN",
        "preregistration_state": "UNKNOWN",
        "preregistration_reason": "SOURCE_NOT_EVALUATED",
        "protocol_id": PROTOCOL_ID,
        "future_evaluation_id": None,
        "source_protocol_id": None,
        "source_future_evaluation_id": None,
        "source_report_consumer_v7_hash": None,
        "source_precommit_gate_v7_hash": None,
        "source_precommit_declaration_hash": None,
        "source_external_time_anchor_reference_hash": None,
        "source_evaluation_not_before_date": None,
        "preregistered_at_utc": None,
        "evaluation_not_before_date": None,
        "minimum_rows_per_fold": MINIMUM_ROWS_PER_FOLD,
        "evaluated_lags": list(EVALUATED_LAGS),
        "inherited_lags": list(INHERITED_LAGS),
        "extension_lags": list(EXTENSION_LAGS),
        "maximum_evaluated_lag": MAXIMUM_EVALUATED_LAG,
        "minimum_pairs_at_maximum_lag": MINIMUM_PAIRS_AT_MAXIMUM_LAG,
        "tail_score": TAIL_SCORE,
        "maximum_allowed_tail_quadratic_energy": TAIL_QUADRATIC_ENERGY_CEILING,
        "inclusive_ceiling": True,
        "evaluation_status": "NOT_EVALUATED",
        "blockers": ["SOURCE_NOT_EVALUATED"],
        "facts": _facts(),
        "authority": _authority(),
    }


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "preregistration_hash")


def _unknown(reason: str, source_state: str = "UNKNOWN") -> dict[str, Any]:
    projection = _base_projection()
    projection["source_state"] = source_state
    projection["preregistration_reason"] = reason
    projection["blockers"] = [reason]
    return _seal(projection)


def _hash_matches(expected: Any, actual: Any) -> bool:
    return strict_sha256(expected) and expected == actual


def _future_evaluation_id(source_declaration_hash: str) -> str:
    return f"LH12-{source_declaration_hash[:20].upper()}"


def build_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1(
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
    preregistered_at_utc: Any,
    evaluation_not_before_date: Any,
    *,
    expected_report_consumer_v7_hash: Any,
    **expected: Any,
) -> dict[str, Any]:
    if not isinstance(report_consumer_v7, dict):
        return _unknown("MISSING_REPORT_CONSUMER_V7", "MISSING")
    if report_consumer_v7.get("schema_version") != SOURCE_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_REPORT_CONSUMER_V7", "UNSUPPORTED")
    if not _hash_matches(
        expected_report_consumer_v7_hash,
        report_consumer_v7.get("verification_hash"),
    ):
        return _unknown("EXPECTED_REPORT_CONSUMER_V7_HASH_MISMATCH", "INVALID")

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
        return _unknown("REPORT_CONSUMER_V7_OR_CONTEXT_INVALID", "INVALID")
    if report_consumer_v7.get("verification_state") != SOURCE_POSITIVE_STATE:
        return _unknown("SOURCE_REPORT_CONSUMER_V7_BLOCKED", "BLOCKED")

    expected_precommit_gate_v7_hash = expected.get(
        "expected_precommit_gate_v7_hash"
    )
    expected_declaration_hash = expected.get("expected_declaration_hash")
    if not _hash_matches(
        expected_precommit_gate_v7_hash,
        report_consumer_v7.get("source_precommit_gate_v7_hash"),
    ):
        return _unknown("SOURCE_PRECOMMIT_GATE_V7_HASH_MISMATCH", "INVALID")
    if not isinstance(precommit_declaration, dict) or not _hash_matches(
        expected_declaration_hash,
        precommit_declaration.get("declaration_hash"),
    ):
        return _unknown("SOURCE_PRECOMMIT_DECLARATION_HASH_MISMATCH", "INVALID")
    if (
        report_consumer_v7.get("protocol_id")
        != precommit_declaration.get("protocol_id")
        or report_consumer_v7.get("future_evaluation_id")
        != precommit_declaration.get("future_evaluation_id")
        or report_consumer_v7.get("evaluation_not_before_date")
        != precommit_declaration.get("evaluation_not_before_date")
        or report_consumer_v7.get("precommit_declared_at_utc")
        != precommit_declaration.get("precommit_declared_at_utc")
    ):
        return _unknown("SOURCE_PRECOMMIT_METADATA_MISMATCH", "INVALID")
    if not strict_sha256(
        precommit_declaration.get("external_time_anchor_reference_hash")
    ):
        return _unknown("SOURCE_EXTERNAL_TIME_ANCHOR_HASH_INVALID", "INVALID")
    if not strict_utc_second_timestamp(preregistered_at_utc) or not strict_iso_date(
        evaluation_not_before_date
    ):
        return _unknown("LONG_HORIZON_TIMING_INVALID", "INVALID")

    try:
        source_not_before = date.fromisoformat(
            precommit_declaration["evaluation_not_before_date"]
        )
        preregistered_date = date.fromisoformat(preregistered_at_utc[:10])
        long_horizon_not_before = date.fromisoformat(evaluation_not_before_date)
    except (KeyError, TypeError, ValueError):
        return _unknown("LONG_HORIZON_TIMING_INVALID", "INVALID")
    if not source_not_before <= preregistered_date < long_horizon_not_before:
        return _unknown("LONG_HORIZON_TIMING_ORDER_INVALID", "INVALID")

    blockers = [
        "EXTERNAL_TIME_ANCHOR_UNVERIFIED",
        "LONG_HORIZON_OBSERVATIONS_NOT_COLLECTED",
        "LONG_HORIZON_EVALUATION_NOT_RUN",
        "LONG_HORIZON_PREREGISTRATION_NOT_ACTIVATED",
        "LAGS_ABOVE_TWELVE_UNRESOLVED",
    ]
    projection = _base_projection()
    projection.update(
        {
            "source_state": "VERIFIED",
            "preregistration_state": "DECLARED_NOT_EVALUATED",
            "preregistration_reason": "LONG_HORIZON_PROTOCOL_PINNED_EXTERNAL_TIME_UNVERIFIED",
            "future_evaluation_id": _future_evaluation_id(
                expected_declaration_hash
            ),
            "source_protocol_id": precommit_declaration["protocol_id"],
            "source_future_evaluation_id": precommit_declaration[
                "future_evaluation_id"
            ],
            "source_report_consumer_v7_hash": expected_report_consumer_v7_hash,
            "source_precommit_gate_v7_hash": expected_precommit_gate_v7_hash,
            "source_precommit_declaration_hash": expected_declaration_hash,
            "source_external_time_anchor_reference_hash": precommit_declaration[
                "external_time_anchor_reference_hash"
            ],
            "source_evaluation_not_before_date": precommit_declaration[
                "evaluation_not_before_date"
            ],
            "preregistered_at_utc": preregistered_at_utc,
            "evaluation_not_before_date": evaluation_not_before_date,
            "blockers": blockers,
            "facts": {
                **_facts(),
                "long_horizon_protocol_pinned": True,
                "minimum_pair_support_pinned": True,
                "source_consumer_v7_verified": True,
                "tail_score_pinned": True,
            },
        }
    )
    return _seal(projection)


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    rebuilt = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1(
        *args,
        **expected,
    )
    return strict_json_contract_equal(document, rebuilt)
