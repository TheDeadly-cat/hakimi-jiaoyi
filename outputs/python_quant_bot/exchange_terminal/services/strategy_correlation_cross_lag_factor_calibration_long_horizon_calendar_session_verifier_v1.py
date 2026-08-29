from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1 as calendar_registration_module,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1 import (
    CALENDAR_LIBRARY_DISTRIBUTION,
    CALENDAR_LIBRARY_VERSION,
    COMMON_DATE_RULE,
    SCHEMA_VERSION as CALENDAR_REGISTRATION_SCHEMA_VERSION,
    SESSION_COMPLETION_POLICY,
    SESSION_LABEL_POLICY,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1 import (
    SCHEMA_VERSION as BATCH_VERIFICATION_SCHEMA_VERSION,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "calendar-session-verifier-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260922-cross-lag-factor-calibration-long-horizon-"
    "calendar-session-verifier-2"
)
CALENDAR_SESSION_PROTOCOL_ID = (
    "FUTURE_FACTOR_RESIDUAL_ORDER_LONG_HORIZON_CALENDAR_SESSION_VERIFIER_V1"
)
POSITIVE_STATE = "CALENDAR_SESSIONS_VERIFIED_BATCH_NOT_ADMITTED"

_CALENDAR_CONTEXT_KEYS = frozenset(
    {
        "declared_at_utc",
        "expected_schedule_hash",
        "factor_calendar_id",
        "fold_schedule_v1",
        "identity_calendar_ids",
        "schedule_verification_context",
    }
)
_BATCH_CONTEXT_KEYS = frozenset(
    {
        "expected_batch_hash",
        "expected_schedule_hash",
        "expected_signature_verification_hash",
        "fold_schedule_v1",
        "schedule_verification_context",
        "signature_verification_context",
        "signature_verification_v1",
    }
)


def _authority() -> dict[str, bool]:
    return {
        "calendar_enforcement_activated": False,
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "future_evaluation_allowed": False,
        "live_order_allowed": False,
        "observation_admission_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _facts(
    *,
    calendar_registration_verified: bool = False,
    source_batch_verified: bool = False,
    schedule_cross_binding_verified: bool = False,
    sessions_verified: bool = False,
) -> dict[str, bool]:
    return {
        "all_registered_sessions_completed": sessions_verified,
        "calendar_registration_verified": calendar_registration_verified,
        "calendar_sessions_evaluated": sessions_verified,
        "common_session_intersection_verified": sessions_verified,
        "external_calendar_registration_time_verified": False,
        "external_provider_identity_verified": False,
        "observation_admission_allowed": False,
        "replay_registry_checked": False,
        "result_available": False,
        "schedule_cross_binding_verified": schedule_cross_binding_verified,
        "source_batch_verified": source_batch_verified,
    }


def _safe_text(document: Any, key: str) -> str | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is str else None


def _safe_count(document: Any, key: str) -> int | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is int and value >= 0 else None


def _utc_second(value: Any) -> datetime | None:
    if type(value) is not str:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None
    return parsed if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value else None


def _unknown(
    reason: str,
    calendar_registration_v1: Any,
    batch_verification_v1: Any,
    *,
    expected_calendar_registration_hash: Any = None,
    expected_batch_verification_hash: Any = None,
    calendar_registration_verified: bool = False,
    source_batch_verified: bool = False,
    schedule_cross_binding_verified: bool = False,
) -> dict[str, Any]:
    calendar = calendar_registration_v1
    batch = batch_verification_v1
    document: dict[str, Any] = {
        "authority": _authority(),
        "blockers": [reason],
        "calendar_library_distribution": CALENDAR_LIBRARY_DISTRIBUTION,
        "calendar_library_version": CALENDAR_LIBRARY_VERSION,
        "calendar_session_evaluation_hash": None,
        "calendar_session_protocol_id": CALENDAR_SESSION_PROTOCOL_ID,
        "calendar_session_verification_state": "UNKNOWN",
        "common_date_rule": COMMON_DATE_RULE,
        "completed_common_session_count": None,
        "distinct_calendar_count": None,
        "evaluation_not_before_date": _safe_text(
            calendar, "evaluation_not_before_date"
        ),
        "factor_id": _safe_text(batch, "factor_id"),
        "factor_source_hash": _safe_text(batch, "factor_source_hash"),
        "facts": _facts(
            calendar_registration_verified=calendar_registration_verified,
            source_batch_verified=source_batch_verified,
            schedule_cross_binding_verified=schedule_cross_binding_verified,
        ),
        "first_observation_date": _safe_text(batch, "first_observation_date"),
        "future_evaluation_id": _safe_text(batch, "future_evaluation_id"),
        "identity_calendar_assignment_hash": _safe_text(
            calendar, "identity_calendar_assignment_hash"
        ),
        "identity_count": _safe_count(batch, "identity_count"),
        "identity_order_hash": _safe_text(batch, "identity_order_hash"),
        "last_observation_date": _safe_text(batch, "last_observation_date"),
        "observation_batch_hash": _safe_text(batch, "observation_batch_hash"),
        "provider_id": _safe_text(batch, "provider_id"),
        "provider_timestamp_utc": _safe_text(batch, "provider_timestamp_utc"),
        "row_count": _safe_count(batch, "row_count"),
        "schema_version": SCHEMA_VERSION,
        "session_check_count": None,
        "session_completion_policy": SESSION_COMPLETION_POLICY,
        "session_label_policy": SESSION_LABEL_POLICY,
        "source_batch_verification_hash": (
            expected_batch_verification_hash
            if strict_sha256(expected_batch_verification_hash)
            else None
        ),
        "source_batch_verification_schema": _safe_text(batch, "schema_version"),
        "source_calendar_registration_hash": (
            expected_calendar_registration_hash
            if strict_sha256(expected_calendar_registration_hash)
            else None
        ),
        "source_calendar_registration_schema": _safe_text(
            calendar, "schema_version"
        ),
        "source_schedule_hash": _safe_text(calendar, "source_schedule_hash"),
        "source_state": "UNKNOWN",
        "static_fingerprint": STATIC_FINGERPRINT,
        "verification_reason": reason,
    }
    return seal_strict_canonical_document(document, "verification_hash")


def _session_close_utc(value: Any) -> datetime | None:
    close = value
    if not isinstance(close, datetime) and hasattr(close, "to_pydatetime"):
        try:
            close = close.to_pydatetime()
        except Exception:
            return None
    if not isinstance(close, datetime) or close.tzinfo is None:
        return None
    try:
        return close.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        return None


def _evaluate_sessions(
    calendar_registration_v1: dict[str, Any],
    rows: list[Any],
    provider_timestamp: datetime,
) -> tuple[str | None, int | None, int | None]:
    assignments = calendar_registration_v1.get("identity_calendar_assignments")
    factor_calendar_id = calendar_registration_v1.get("factor_calendar_id")
    if type(assignments) is not list or type(factor_calendar_id) is not str:
        return "CALENDAR_ASSIGNMENTS_INVALID", None, None
    calendar_ids: list[str] = []
    for expected_index, assignment in enumerate(assignments):
        if (
            type(assignment) is not dict
            or set(assignment) != {"calendar_id", "identity_index"}
            or assignment.get("identity_index") != expected_index
            or type(assignment.get("calendar_id")) is not str
        ):
            return "CALENDAR_ASSIGNMENTS_INVALID", None, None
        calendar_ids.append(assignment["calendar_id"])
    calendar_ids.append(factor_calendar_id)
    distinct_ids = sorted(set(calendar_ids))
    runtime = calendar_registration_module.exchange_calendars
    if runtime is None:
        return "CALENDAR_RUNTIME_UNAVAILABLE", None, None
    calendars: dict[str, Any] = {}
    try:
        for calendar_id in distinct_ids:
            calendars[calendar_id] = runtime.get_calendar(calendar_id)
    except Exception:
        return "CALENDAR_RUNTIME_UNAVAILABLE", None, None

    check_count = 0
    for row in rows:
        if type(row) is not dict or type(row.get("observation_date")) is not str:
            return "OBSERVATION_ROWS_INVALID", None, None
        observation_date = row["observation_date"]
        for calendar_id in distinct_ids:
            calendar = calendars[calendar_id]
            try:
                is_session = bool(calendar.is_session(observation_date))
            except Exception:
                return "CALENDAR_SESSION_LOOKUP_FAILED", None, None
            if not is_session:
                return "OBSERVATION_DATE_NOT_COMMON_REGISTERED_SESSION", None, None
            try:
                close_utc = _session_close_utc(
                    calendar.session_close(observation_date)
                )
            except Exception:
                return "CALENDAR_SESSION_LOOKUP_FAILED", None, None
            if close_utc is None:
                return "CALENDAR_SESSION_CLOSE_INVALID", None, None
            if close_utc > provider_timestamp:
                return (
                    "CALENDAR_SESSION_NOT_COMPLETED_AT_PROVIDER_TIMESTAMP",
                    None,
                    None,
                )
            check_count += 1
    return None, len(distinct_ids), check_count


def evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1(
    calendar_registration_v1: Any,
    calendar_registration_verification_context: Any,
    batch_verification_v1: Any,
    batch_verification_context: Any,
    observation_batch: Any,
    *,
    expected_calendar_registration_hash: Any,
    expected_batch_verification_hash: Any,
) -> dict[str, Any]:
    calendar = calendar_registration_v1
    batch = batch_verification_v1
    if not strict_sha256(expected_calendar_registration_hash):
        return _unknown(
            "EXPECTED_CALENDAR_REGISTRATION_HASH_INVALID",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
        )
    if not strict_sha256(expected_batch_verification_hash):
        return _unknown(
            "EXPECTED_BATCH_VERIFICATION_HASH_INVALID",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
        )
    if type(calendar) is not dict:
        return _unknown(
            "SOURCE_CALENDAR_REGISTRATION_NOT_OBJECT",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
        )
    if calendar.get("calendar_registration_hash") != expected_calendar_registration_hash:
        return _unknown(
            "SOURCE_CALENDAR_REGISTRATION_HASH_MISMATCH",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
        )
    if calendar.get("schema_version") != CALENDAR_REGISTRATION_SCHEMA_VERSION:
        return _unknown(
            "SOURCE_CALENDAR_REGISTRATION_SCHEMA_UNSUPPORTED",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
        )
    if (
        type(calendar_registration_verification_context) is not dict
        or set(calendar_registration_verification_context) != _CALENDAR_CONTEXT_KEYS
    ):
        return _unknown(
            "CALENDAR_REGISTRATION_VERIFICATION_CONTEXT_INVALID",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
        )
    calendar_context = calendar_registration_verification_context
    try:
        calendar_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1(
                calendar,
                calendar_context["fold_schedule_v1"],
                calendar_context["schedule_verification_context"],
                expected_schedule_hash=calendar_context["expected_schedule_hash"],
                identity_calendar_ids=calendar_context["identity_calendar_ids"],
                factor_calendar_id=calendar_context["factor_calendar_id"],
                declared_at_utc=calendar_context["declared_at_utc"],
            )
        )
    except Exception:
        calendar_verified = False
    if not calendar_verified:
        return _unknown(
            "SOURCE_CALENDAR_REGISTRATION_NOT_VERIFIED",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
        )
    if (
        calendar.get("source_state") != "VERIFIED"
        or calendar.get("calendar_registration_state")
        != "CALENDAR_ASSIGNMENT_DECLARED_NOT_EXTERNALLY_TIME_ATTESTED"
    ):
        return _unknown(
            "SOURCE_CALENDAR_REGISTRATION_STATE_NOT_POSITIVE",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
        )
    if type(batch) is not dict:
        return _unknown(
            "SOURCE_BATCH_VERIFICATION_NOT_OBJECT",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
        )
    if batch.get("verification_hash") != expected_batch_verification_hash:
        return _unknown(
            "SOURCE_BATCH_VERIFICATION_HASH_MISMATCH",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
        )
    if batch.get("schema_version") != BATCH_VERIFICATION_SCHEMA_VERSION:
        return _unknown(
            "SOURCE_BATCH_VERIFICATION_SCHEMA_UNSUPPORTED",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
        )
    if (
        type(batch_verification_context) is not dict
        or set(batch_verification_context) != _BATCH_CONTEXT_KEYS
    ):
        return _unknown(
            "BATCH_VERIFICATION_CONTEXT_INVALID",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
        )
    batch_context = batch_verification_context
    try:
        batch_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1(
                batch,
                batch_context["fold_schedule_v1"],
                batch_context["schedule_verification_context"],
                batch_context["signature_verification_v1"],
                batch_context["signature_verification_context"],
                observation_batch,
                expected_schedule_hash=batch_context["expected_schedule_hash"],
                expected_signature_verification_hash=batch_context[
                    "expected_signature_verification_hash"
                ],
                expected_batch_hash=batch_context["expected_batch_hash"],
            )
        )
    except Exception:
        batch_verified = False
    if not batch_verified:
        return _unknown(
            "SOURCE_BATCH_VERIFICATION_NOT_VERIFIED",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
        )
    if (
        batch.get("source_state") != "VERIFIED"
        or batch.get("verification_state")
        != "BATCH_CONTENT_VERIFIED_SIGNATURE_LIMITED"
    ):
        return _unknown(
            "SOURCE_BATCH_VERIFICATION_STATE_NOT_POSITIVE",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
            source_batch_verified=True,
        )
    if type(observation_batch) is not dict or type(observation_batch.get("rows")) is not list:
        return _unknown(
            "OBSERVATION_ROWS_INVALID",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
            source_batch_verified=True,
        )
    rows = observation_batch["rows"]
    schedule_hashes = {
        calendar.get("source_schedule_hash"),
        batch.get("schedule_hash"),
        observation_batch.get("schedule_hash"),
        calendar_context.get("expected_schedule_hash"),
        batch_context.get("expected_schedule_hash"),
    }
    cross_binding_valid = (
        len(schedule_hashes) == 1
        and all(strict_sha256(value) for value in schedule_hashes)
        and calendar.get("identity_count") == batch.get("identity_count")
        and calendar.get("identity_order_hash") == batch.get("identity_order_hash")
        == observation_batch.get("identity_order_hash")
        and calendar.get("factor_id") == batch.get("factor_id")
        == observation_batch.get("factor_id")
        and calendar.get("factor_source_hash") == batch.get("factor_source_hash")
        == observation_batch.get("factor_source_hash")
        and calendar.get("future_evaluation_id") == batch.get("future_evaluation_id")
        == observation_batch.get("future_evaluation_id")
        and batch.get("observation_batch_hash")
        == observation_batch.get("observation_batch_hash")
        == batch_context.get("expected_batch_hash")
        and batch.get("row_count") == len(rows)
        and batch.get("first_observation_date")
        == observation_batch.get("first_observation_date")
        and batch.get("last_observation_date")
        == observation_batch.get("last_observation_date")
    )
    if not cross_binding_valid:
        return _unknown(
            "SOURCE_CROSS_BINDING_INVALID",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
            source_batch_verified=True,
        )
    provider_timestamp = _utc_second(batch.get("provider_timestamp_utc"))
    if provider_timestamp is None:
        return _unknown(
            "PROVIDER_TIMESTAMP_INVALID",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
            source_batch_verified=True,
            schedule_cross_binding_verified=True,
        )
    session_reason, distinct_calendar_count, session_check_count = _evaluate_sessions(
        calendar,
        rows,
        provider_timestamp,
    )
    if session_reason is not None:
        return _unknown(
            session_reason,
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
            source_batch_verified=True,
            schedule_cross_binding_verified=True,
        )
    if distinct_calendar_count is None or session_check_count is None:
        return _unknown(
            "CALENDAR_SESSION_EVALUATION_INCOMPLETE",
            calendar,
            batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
            calendar_registration_verified=True,
            source_batch_verified=True,
            schedule_cross_binding_verified=True,
        )

    evaluation_binding = {
        "calendar_library_distribution": CALENDAR_LIBRARY_DISTRIBUTION,
        "calendar_library_version": CALENDAR_LIBRARY_VERSION,
        "calendar_session_protocol_id": CALENDAR_SESSION_PROTOCOL_ID,
        "common_date_rule": COMMON_DATE_RULE,
        "completed_common_session_count": len(rows),
        "distinct_calendar_count": distinct_calendar_count,
        "first_observation_date": batch.get("first_observation_date"),
        "identity_calendar_assignment_hash": calendar.get(
            "identity_calendar_assignment_hash"
        ),
        "last_observation_date": batch.get("last_observation_date"),
        "observation_batch_hash": batch.get("observation_batch_hash"),
        "provider_timestamp_utc": batch.get("provider_timestamp_utc"),
        "row_count": len(rows),
        "session_check_count": session_check_count,
        "session_completion_policy": SESSION_COMPLETION_POLICY,
        "session_label_policy": SESSION_LABEL_POLICY,
        "source_batch_verification_hash": expected_batch_verification_hash,
        "source_calendar_registration_hash": expected_calendar_registration_hash,
        "source_schedule_hash": calendar.get("source_schedule_hash"),
    }
    document: dict[str, Any] = {
        "authority": _authority(),
        "blockers": [
            "PROVIDER_IDENTITY_NOT_EXTERNALLY_ESTABLISHED",
            "CALENDAR_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
            "REPLAY_REGISTRY_NOT_CHECKED",
            "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
            "OBSERVATION_ADMISSION_NOT_ACTIVATED",
        ],
        "calendar_library_distribution": CALENDAR_LIBRARY_DISTRIBUTION,
        "calendar_library_version": CALENDAR_LIBRARY_VERSION,
        "calendar_session_evaluation_hash": strict_canonical_hash(
            evaluation_binding
        ),
        "calendar_session_protocol_id": CALENDAR_SESSION_PROTOCOL_ID,
        "calendar_session_verification_state": POSITIVE_STATE,
        "common_date_rule": COMMON_DATE_RULE,
        "completed_common_session_count": len(rows),
        "distinct_calendar_count": distinct_calendar_count,
        "evaluation_not_before_date": calendar.get("evaluation_not_before_date"),
        "factor_id": batch.get("factor_id"),
        "factor_source_hash": batch.get("factor_source_hash"),
        "facts": _facts(
            calendar_registration_verified=True,
            source_batch_verified=True,
            schedule_cross_binding_verified=True,
            sessions_verified=True,
        ),
        "first_observation_date": batch.get("first_observation_date"),
        "future_evaluation_id": batch.get("future_evaluation_id"),
        "identity_calendar_assignment_hash": calendar.get(
            "identity_calendar_assignment_hash"
        ),
        "identity_count": batch.get("identity_count"),
        "identity_order_hash": batch.get("identity_order_hash"),
        "last_observation_date": batch.get("last_observation_date"),
        "observation_batch_hash": batch.get("observation_batch_hash"),
        "provider_id": batch.get("provider_id"),
        "provider_timestamp_utc": batch.get("provider_timestamp_utc"),
        "row_count": len(rows),
        "schema_version": SCHEMA_VERSION,
        "session_check_count": session_check_count,
        "session_completion_policy": SESSION_COMPLETION_POLICY,
        "session_label_policy": SESSION_LABEL_POLICY,
        "source_batch_verification_hash": expected_batch_verification_hash,
        "source_batch_verification_schema": BATCH_VERIFICATION_SCHEMA_VERSION,
        "source_calendar_registration_hash": expected_calendar_registration_hash,
        "source_calendar_registration_schema": CALENDAR_REGISTRATION_SCHEMA_VERSION,
        "source_schedule_hash": calendar.get("source_schedule_hash"),
        "source_state": "VERIFIED",
        "static_fingerprint": STATIC_FINGERPRINT,
        "verification_reason": (
            "REGISTERED_COMMON_SESSIONS_COMPLETED_BATCH_NOT_ADMITTED"
        ),
    }
    return seal_strict_canonical_document(document, "verification_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1(
            *args,
            **expected,
        )
        return strict_json_contract_equal(document, rebuilt)
    except Exception:
        return False
