from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1 import (
    MAXIMUM_EVALUATED_LAG,
    MINIMUM_PAIRS_AT_MAXIMUM_LAG,
    MINIMUM_ROWS_PER_FOLD,
    PROTOCOL_ID as SOURCE_PROTOCOL_ID,
    SCHEMA_VERSION as SOURCE_SCHEMA_VERSION,
    STATIC_FINGERPRINT as SOURCE_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "fold-schedule-preregistration-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260920-cross-lag-factor-calibration-long-horizon-"
    "fold-schedule-preregistration-1"
)
SCHEDULE_PROTOCOL_ID = (
    "FUTURE_FACTOR_RESIDUAL_ORDER_LONG_HORIZON_FOLD_SCHEDULE_V1"
)
FOLD_COUNT = 4
ROWS_PER_FOLD = 20
TOTAL_SCHEDULED_ROWS = FOLD_COUNT * ROWS_PER_FOLD
FOLD_ORDER = tuple(f"LH-FOLD-{index:02d}" for index in range(1, FOLD_COUNT + 1))
ASSIGNMENT_RULE = "FIRST_ELIGIBLE_COMMON_DATE_PREFIX_CONTIGUOUS_FIXED_COUNT_V1"
ELIGIBILITY_RULE = (
    "FIRST_STRICTLY_INCREASING_REGISTERED_IDENTITY_AND_FACTOR_COMMON_DATE_"
    "ON_OR_AFTER_EVALUATION_NOT_BEFORE"
)
MISSING_DATA_POLICY = "ANY_MISSING_REGISTERED_IDENTITY_OR_FACTOR_BLOCKS_SCHEDULE"
DUPLICATE_OR_OUT_OF_ORDER_POLICY = "BLOCK"
INCOMPLETE_PREFIX_POLICY = "UNKNOWN_UNTIL_ALL_80_COMMON_DATES_OBSERVED"
EXCESS_OBSERVATION_POLICY = "EXCLUDE_AFTER_POSITION_79_FROM_V1_EVALUATION"

_UTC_SECOND = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _position_ranges() -> list[dict[str, Any]]:
    return [
        {
            "end_position_inclusive": (index + 1) * ROWS_PER_FOLD - 1,
            "fold_id": fold_id,
            "start_position_inclusive": index * ROWS_PER_FOLD,
        }
        for index, fold_id in enumerate(FOLD_ORDER)
    ]


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_schedule_time_verified": False,
        "future_evaluation_allowed": False,
        "future_observation_collection_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _facts(
    *,
    source_verified: bool = False,
    schedule_pinned: bool = False,
    chronology_claim_valid: bool = False,
) -> dict[str, bool]:
    return {
        "evaluation_activated": False,
        "external_schedule_time_verified": False,
        "fold_assignment_deterministic": schedule_pinned,
        "fold_boundaries_date_observed": False,
        "fold_schedule_pinned": schedule_pinned,
        "future_observations_collected": False,
        "result_available": False,
        "schedule_chronology_claim_valid": chronology_claim_valid,
        "source_observation_protocol_verified": source_verified,
    }


def _utc_second(value: Any) -> datetime | None:
    if type(value) is not str or _UTC_SECOND.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None
    return parsed if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value else None


def _iso_date(value: Any) -> date | None:
    if type(value) is not str:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _safe_text(document: Any, key: str) -> str | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is str else None


def _source_state(document: Any) -> str:
    if type(document) is not dict:
        return "UNKNOWN"
    value = document.get("source_state")
    return value if value in {"VERIFIED", "BLOCKED", "UNKNOWN"} else "UNKNOWN"


def _unknown(
    reason: str,
    source_protocol: Any,
    *,
    expected_source_protocol_hash: Any = None,
    expected_preregistration_hash: Any = None,
    source_verified: bool = False,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "assignment_rule": ASSIGNMENT_RULE,
        "authority": _authority(),
        "blockers": [reason],
        "declared_at_utc": None,
        "duplicate_or_out_of_order_policy": DUPLICATE_OR_OUT_OF_ORDER_POLICY,
        "eligibility_rule": ELIGIBILITY_RULE,
        "evaluation_not_before_date": _safe_text(
            source_protocol, "evaluation_not_before_date"
        ),
        "excess_observation_policy": EXCESS_OBSERVATION_POLICY,
        "factor_id": None,
        "factor_source_hash": None,
        "facts": _facts(source_verified=source_verified),
        "fold_count": None,
        "fold_order": [],
        "fold_position_ranges": [],
        "future_evaluation_id": _safe_text(source_protocol, "future_evaluation_id"),
        "identity_count": None,
        "identity_order_hash": None,
        "incomplete_prefix_policy": INCOMPLETE_PREFIX_POLICY,
        "maximum_evaluated_lag": None,
        "minimum_pairs_at_maximum_lag": None,
        "missing_data_policy": MISSING_DATA_POLICY,
        "rows_per_fold": None,
        "schedule_protocol_id": SCHEDULE_PROTOCOL_ID,
        "schedule_reason": reason,
        "schedule_state": "UNKNOWN",
        "schema_version": SCHEMA_VERSION,
        "source_observation_protocol_hash": (
            expected_source_protocol_hash
            if strict_sha256(expected_source_protocol_hash)
            else None
        ),
        "source_observation_protocol_schema": _safe_text(
            source_protocol, "schema_version"
        ),
        "source_preregistered_at_utc": None,
        "source_preregistration_hash": (
            expected_preregistration_hash
            if strict_sha256(expected_preregistration_hash)
            else None
        ),
        "source_report_consumer_v7_hash": _safe_text(
            source_protocol, "source_report_consumer_v7_hash"
        ),
        "source_residualization_registration_hash": None,
        "source_state": _source_state(source_protocol),
        "static_fingerprint": STATIC_FINGERPRINT,
        "total_scheduled_rows": None,
    }
    return seal_strict_canonical_document(document, "schedule_hash")


def build_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1(
    observation_protocol_v1: Any,
    long_horizon_preregistration_v1: Any,
    source_verification_context: Any,
    *,
    expected_observation_protocol_hash: Any,
    expected_preregistration_hash: Any,
    declared_at_utc: Any,
) -> dict[str, Any]:
    source_protocol = observation_protocol_v1
    if not strict_sha256(expected_observation_protocol_hash):
        return _unknown(
            "EXPECTED_OBSERVATION_PROTOCOL_HASH_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if not strict_sha256(expected_preregistration_hash):
        return _unknown(
            "EXPECTED_PREREGISTRATION_HASH_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if type(source_protocol) is not dict:
        return _unknown(
            "SOURCE_OBSERVATION_PROTOCOL_NOT_OBJECT",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if source_protocol.get("protocol_hash") != expected_observation_protocol_hash:
        return _unknown(
            "SOURCE_OBSERVATION_PROTOCOL_HASH_MISMATCH",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if source_protocol.get("schema_version") != SOURCE_SCHEMA_VERSION:
        return _unknown(
            "SOURCE_OBSERVATION_PROTOCOL_SCHEMA_UNSUPPORTED",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    try:
        source_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1(
                source_protocol,
                long_horizon_preregistration_v1,
                source_verification_context,
                expected_preregistration_hash=expected_preregistration_hash,
            )
        )
    except Exception:
        source_verified = False
    if not source_verified:
        return _unknown(
            "SOURCE_OBSERVATION_PROTOCOL_NOT_VERIFIED",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
        )
    if (
        source_protocol.get("static_fingerprint") != SOURCE_STATIC_FINGERPRINT
        or source_protocol.get("protocol_id") != SOURCE_PROTOCOL_ID
        or source_protocol.get("source_state") != "VERIFIED"
        or source_protocol.get("protocol_state")
        != "PROTOCOL_DECLARED_NO_OBSERVATIONS"
        or source_protocol.get("source_preregistration_hash")
        != expected_preregistration_hash
    ):
        return _unknown(
            "SOURCE_OBSERVATION_PROTOCOL_NOT_DECLARED",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if type(source_verification_context) is not dict:
        return _unknown(
            "SOURCE_VERIFICATION_CONTEXT_NOT_OBJECT",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    report_consumer = source_verification_context.get("report_consumer_v7")
    registration = source_verification_context.get("residualization_registration")
    if type(report_consumer) is not dict or type(registration) is not dict:
        return _unknown(
            "SOURCE_FOLD_CONTEXT_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if (
        report_consumer.get("fold_count") != FOLD_COUNT
        or report_consumer.get("verification_hash")
        != source_protocol.get("source_report_consumer_v7_hash")
    ):
        return _unknown(
            "SOURCE_FOLD_COUNT_OR_CONSUMER_HASH_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    identities = registration.get("identity_order")
    if (
        type(identities) is not list
        or not identities
        or any(type(identity) is not str or not identity for identity in identities)
        or len(identities) != len(set(identities))
        or registration.get("identity_order_hash") != strict_canonical_hash(identities)
        or not strict_sha256(registration.get("factor_source_hash"))
        or not strict_sha256(registration.get("registration_hash"))
        or type(registration.get("factor_id")) is not str
        or not registration.get("factor_id")
    ):
        return _unknown(
            "SOURCE_IDENTITY_OR_FACTOR_BINDINGS_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if (
        source_protocol.get("minimum_rows_per_fold") != ROWS_PER_FOLD
        or source_protocol.get("maximum_evaluated_lag") != MAXIMUM_EVALUATED_LAG
        or source_protocol.get("minimum_pairs_at_maximum_lag")
        != MINIMUM_PAIRS_AT_MAXIMUM_LAG
    ):
        return _unknown(
            "SOURCE_LONG_HORIZON_SUPPORT_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if type(long_horizon_preregistration_v1) is not dict:
        return _unknown(
            "SOURCE_PREREGISTRATION_NOT_OBJECT",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    declared_at = _utc_second(declared_at_utc)
    preregistered_at = _utc_second(
        long_horizon_preregistration_v1.get("preregistered_at_utc")
    )
    evaluation_not_before = _iso_date(
        source_protocol.get("evaluation_not_before_date")
    )
    if declared_at is None or preregistered_at is None or evaluation_not_before is None:
        return _unknown(
            "SCHEDULE_DECLARATION_TIME_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if declared_at < preregistered_at:
        return _unknown(
            "SCHEDULE_DECLARATION_BEFORE_PREREGISTRATION",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if declared_at.date() >= evaluation_not_before:
        return _unknown(
            "SCHEDULE_DECLARATION_NOT_BEFORE_EVALUATION",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )

    schedule_binding = {
        "assignment_rule": ASSIGNMENT_RULE,
        "declared_at_utc": declared_at_utc,
        "duplicate_or_out_of_order_policy": DUPLICATE_OR_OUT_OF_ORDER_POLICY,
        "eligibility_rule": ELIGIBILITY_RULE,
        "evaluation_not_before_date": source_protocol.get(
            "evaluation_not_before_date"
        ),
        "excess_observation_policy": EXCESS_OBSERVATION_POLICY,
        "factor_id": registration.get("factor_id"),
        "factor_source_hash": registration.get("factor_source_hash"),
        "fold_count": FOLD_COUNT,
        "fold_order": list(FOLD_ORDER),
        "fold_position_ranges": _position_ranges(),
        "future_evaluation_id": source_protocol.get("future_evaluation_id"),
        "identity_order_hash": registration.get("identity_order_hash"),
        "incomplete_prefix_policy": INCOMPLETE_PREFIX_POLICY,
        "maximum_evaluated_lag": MAXIMUM_EVALUATED_LAG,
        "minimum_pairs_at_maximum_lag": MINIMUM_PAIRS_AT_MAXIMUM_LAG,
        "missing_data_policy": MISSING_DATA_POLICY,
        "rows_per_fold": ROWS_PER_FOLD,
        "source_observation_protocol_hash": expected_observation_protocol_hash,
        "source_preregistration_hash": expected_preregistration_hash,
        "source_report_consumer_v7_hash": report_consumer.get("verification_hash"),
        "source_residualization_registration_hash": registration.get(
            "registration_hash"
        ),
        "total_scheduled_rows": TOTAL_SCHEDULED_ROWS,
    }
    document: dict[str, Any] = {
        **schedule_binding,
        "authority": _authority(),
        "blockers": [
            "SCHEDULE_DECLARATION_TIME_NOT_EXTERNALLY_ATTESTED",
            "FUTURE_OBSERVATIONS_NOT_COLLECTED",
            "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
        ],
        "facts": _facts(
            source_verified=True,
            schedule_pinned=True,
            chronology_claim_valid=True,
        ),
        "identity_count": len(identities),
        "schedule_binding_hash": strict_canonical_hash(schedule_binding),
        "schedule_protocol_id": SCHEDULE_PROTOCOL_ID,
        "schedule_reason": (
            "FIXED_COUNT_PREFIX_PINNED_EXTERNAL_SCHEDULE_TIME_UNVERIFIED"
        ),
        "schedule_state": "SCHEDULE_DECLARED_NOT_EXTERNALLY_TIME_ATTESTED",
        "schema_version": SCHEMA_VERSION,
        "source_observation_protocol_schema": SOURCE_SCHEMA_VERSION,
        "source_preregistered_at_utc": long_horizon_preregistration_v1.get(
            "preregistered_at_utc"
        ),
        "source_state": "VERIFIED",
        "static_fingerprint": STATIC_FINGERPRINT,
    }
    return seal_strict_canonical_document(document, "schedule_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        rebuilt = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1(
            *args,
            **expected,
        )
        return strict_json_contract_equal(document, rebuilt)
    except Exception:
        return False
