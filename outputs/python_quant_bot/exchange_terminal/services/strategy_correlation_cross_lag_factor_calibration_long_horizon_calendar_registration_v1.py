from __future__ import annotations

from datetime import date, datetime, timezone
from importlib.metadata import PackageNotFoundError, version as distribution_version
from typing import Any

try:
    import exchange_calendars as exchange_calendars
except ImportError:  # pragma: no cover - exercised through dependency patching
    exchange_calendars = None

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1 import (
    SCHEMA_VERSION as SCHEDULE_SCHEMA_VERSION,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "calendar-registration-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260922-cross-lag-factor-calibration-long-horizon-calendar-registration-2"
)
CALENDAR_PROTOCOL_ID = (
    "FUTURE_FACTOR_RESIDUAL_ORDER_LONG_HORIZON_CALENDAR_REGISTRATION_V1"
)
CALENDAR_LIBRARY_DISTRIBUTION = "exchange-calendars"
CALENDAR_LIBRARY_VERSION = "4.13.2"
COMMON_DATE_RULE = "INTERSECTION_OF_COMPLETED_REGISTERED_SESSIONS_V1"
SESSION_COMPLETION_POLICY = "SESSION_CLOSE_NOT_AFTER_PROVIDER_TIMESTAMP_UTC"
SESSION_LABEL_POLICY = "EXCHANGE_CALENDAR_SESSION_LABEL_DATE_V1"
MISSING_CALENDAR_POLICY = "BLOCK"
UNSUPPORTED_CALENDAR_POLICY = "BLOCK"

_SCHEDULE_CONTEXT_KEYS = frozenset(
    {
        "declared_at_utc",
        "expected_observation_protocol_hash",
        "expected_preregistration_hash",
        "long_horizon_preregistration_v1",
        "observation_protocol_v1",
        "source_verification_context",
    }
)


def _authority() -> dict[str, bool]:
    return {
        "calendar_enforcement_activated": False,
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_calendar_registration_time_verified": False,
        "future_evaluation_allowed": False,
        "live_order_allowed": False,
        "observation_admission_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _facts(
    *,
    schedule_verified: bool = False,
    assignments_pinned: bool = False,
    chronology_claim_valid: bool = False,
) -> dict[str, bool]:
    return {
        "calendar_assignments_pinned": assignments_pinned,
        "calendar_library_version_pinned": assignments_pinned,
        "calendar_sessions_evaluated": False,
        "common_date_rule_pinned": assignments_pinned,
        "evaluation_activated": False,
        "external_calendar_registration_time_verified": False,
        "future_observations_collected": False,
        "result_available": False,
        "schedule_verified": schedule_verified,
        "session_completion_policy_pinned": assignments_pinned,
        "registration_chronology_claim_valid": chronology_claim_valid,
    }


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


def _calendar_runtime() -> tuple[
    str | None,
    str | None,
    set[str] | None,
    set[str] | None,
]:
    if exchange_calendars is None:
        return None, None, None, None
    try:
        library_version = distribution_version(CALENDAR_LIBRARY_DISTRIBUTION)
        module_version = getattr(exchange_calendars, "__version__", None)
        names = set(exchange_calendars.get_calendar_names(include_aliases=True))
        canonical_names = set(
            exchange_calendars.get_calendar_names(include_aliases=False)
        )
    except Exception:
        return None, None, None, None
    if (
        any(type(name) is not str for name in names)
        or any(type(name) is not str for name in canonical_names)
        or not canonical_names.issubset(names)
    ):
        return None, None, None, None
    return library_version, module_version, names, canonical_names


def _unknown(
    reason: str,
    schedule: Any,
    *,
    expected_schedule_hash: Any = None,
    schedule_verified: bool = False,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "authority": _authority(),
        "blockers": [reason],
        "calendar_library_distribution": CALENDAR_LIBRARY_DISTRIBUTION,
        "calendar_library_version": CALENDAR_LIBRARY_VERSION,
        "calendar_protocol_id": CALENDAR_PROTOCOL_ID,
        "calendar_registration_state": "UNKNOWN",
        "common_date_rule": COMMON_DATE_RULE,
        "declared_at_utc": None,
        "distinct_calendar_ids": [],
        "evaluation_not_before_date": _safe_text(
            schedule, "evaluation_not_before_date"
        ),
        "factor_calendar_id": None,
        "factor_id": _safe_text(schedule, "factor_id"),
        "factor_source_hash": _safe_text(schedule, "factor_source_hash"),
        "facts": _facts(schedule_verified=schedule_verified),
        "future_evaluation_id": _safe_text(schedule, "future_evaluation_id"),
        "identity_calendar_assignment_hash": None,
        "identity_calendar_assignments": [],
        "identity_count": None,
        "identity_order_hash": _safe_text(schedule, "identity_order_hash"),
        "missing_calendar_policy": MISSING_CALENDAR_POLICY,
        "registration_reason": reason,
        "schema_version": SCHEMA_VERSION,
        "session_completion_policy": SESSION_COMPLETION_POLICY,
        "session_label_policy": SESSION_LABEL_POLICY,
        "source_schedule_hash": (
            expected_schedule_hash if strict_sha256(expected_schedule_hash) else None
        ),
        "source_schedule_schema": _safe_text(schedule, "schema_version"),
        "source_state": _source_state(schedule),
        "static_fingerprint": STATIC_FINGERPRINT,
        "unsupported_calendar_policy": UNSUPPORTED_CALENDAR_POLICY,
    }
    return seal_strict_canonical_document(document, "calendar_registration_hash")


def build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1(
    fold_schedule_v1: Any,
    schedule_verification_context: Any,
    *,
    expected_schedule_hash: Any,
    identity_calendar_ids: Any,
    factor_calendar_id: Any,
    declared_at_utc: Any,
) -> dict[str, Any]:
    schedule = fold_schedule_v1
    if not strict_sha256(expected_schedule_hash):
        return _unknown(
            "EXPECTED_SCHEDULE_HASH_INVALID",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
        )
    if type(schedule) is not dict:
        return _unknown(
            "SOURCE_SCHEDULE_NOT_OBJECT",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
        )
    if schedule.get("schedule_hash") != expected_schedule_hash:
        return _unknown(
            "SOURCE_SCHEDULE_HASH_MISMATCH",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
        )
    if schedule.get("schema_version") != SCHEDULE_SCHEMA_VERSION:
        return _unknown(
            "SOURCE_SCHEDULE_SCHEMA_UNSUPPORTED",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
        )
    if (
        type(schedule_verification_context) is not dict
        or set(schedule_verification_context) != _SCHEDULE_CONTEXT_KEYS
    ):
        return _unknown(
            "SCHEDULE_VERIFICATION_CONTEXT_INVALID",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
        )
    try:
        schedule_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1(
                schedule,
                schedule_verification_context["observation_protocol_v1"],
                schedule_verification_context["long_horizon_preregistration_v1"],
                schedule_verification_context["source_verification_context"],
                expected_observation_protocol_hash=schedule_verification_context[
                    "expected_observation_protocol_hash"
                ],
                expected_preregistration_hash=schedule_verification_context[
                    "expected_preregistration_hash"
                ],
                declared_at_utc=schedule_verification_context["declared_at_utc"],
            )
        )
    except Exception:
        schedule_verified = False
    if not schedule_verified:
        return _unknown(
            "SOURCE_SCHEDULE_NOT_VERIFIED",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
        )
    if (
        schedule.get("source_state") != "VERIFIED"
        or schedule.get("schedule_state")
        != "SCHEDULE_DECLARED_NOT_EXTERNALLY_TIME_ATTESTED"
    ):
        return _unknown(
            "SOURCE_SCHEDULE_NOT_DECLARED",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    source_context = schedule_verification_context["source_verification_context"]
    registration = (
        source_context.get("residualization_registration")
        if type(source_context) is dict
        else None
    )
    identities = registration.get("identity_order") if type(registration) is dict else None
    if (
        type(identities) is not list
        or not identities
        or schedule.get("identity_count") != len(identities)
        or schedule.get("identity_order_hash") != strict_canonical_hash(identities)
    ):
        return _unknown(
            "SOURCE_IDENTITY_BINDINGS_INVALID",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )

    (
        library_version,
        module_version,
        available_names,
        canonical_names,
    ) = _calendar_runtime()
    if (
        library_version is None
        or module_version is None
        or available_names is None
        or canonical_names is None
    ):
        return _unknown(
            "CALENDAR_LIBRARY_UNAVAILABLE",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    if library_version != CALENDAR_LIBRARY_VERSION:
        return _unknown(
            "CALENDAR_LIBRARY_VERSION_MISMATCH",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    if module_version != CALENDAR_LIBRARY_VERSION:
        return _unknown(
            "CALENDAR_LIBRARY_MODULE_VERSION_MISMATCH",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    if (
        type(identity_calendar_ids) is not list
        or len(identity_calendar_ids) != len(identities)
        or any(type(calendar_id) is not str or not calendar_id for calendar_id in identity_calendar_ids)
    ):
        return _unknown(
            "IDENTITY_CALENDAR_ASSIGNMENTS_INVALID",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    if type(factor_calendar_id) is not str or not factor_calendar_id:
        return _unknown(
            "FACTOR_CALENDAR_ASSIGNMENT_INVALID",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    if any(calendar_id not in available_names for calendar_id in identity_calendar_ids):
        return _unknown(
            "IDENTITY_CALENDAR_UNSUPPORTED",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    if any(calendar_id not in canonical_names for calendar_id in identity_calendar_ids):
        return _unknown(
            "IDENTITY_CALENDAR_NONCANONICAL",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    if factor_calendar_id not in available_names:
        return _unknown(
            "FACTOR_CALENDAR_UNSUPPORTED",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    if factor_calendar_id not in canonical_names:
        return _unknown(
            "FACTOR_CALENDAR_NONCANONICAL",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    declared_at = _utc_second(declared_at_utc)
    schedule_declared_at = _utc_second(schedule.get("declared_at_utc"))
    evaluation_not_before = _iso_date(schedule.get("evaluation_not_before_date"))
    if declared_at is None or schedule_declared_at is None or evaluation_not_before is None:
        return _unknown(
            "CALENDAR_DECLARATION_TIME_INVALID",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    if declared_at < schedule_declared_at:
        return _unknown(
            "CALENDAR_DECLARATION_BEFORE_SCHEDULE",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )
    if declared_at.date() >= evaluation_not_before:
        return _unknown(
            "CALENDAR_DECLARATION_NOT_BEFORE_EVALUATION",
            schedule,
            expected_schedule_hash=expected_schedule_hash,
            schedule_verified=True,
        )

    assignments = [
        {"calendar_id": calendar_id, "identity_index": index}
        for index, calendar_id in enumerate(identity_calendar_ids)
    ]
    assignment_binding = {
        "calendar_library_distribution": CALENDAR_LIBRARY_DISTRIBUTION,
        "calendar_library_version": CALENDAR_LIBRARY_VERSION,
        "common_date_rule": COMMON_DATE_RULE,
        "factor_calendar_id": factor_calendar_id,
        "identity_calendar_assignments": assignments,
        "identity_order_hash": schedule.get("identity_order_hash"),
        "session_completion_policy": SESSION_COMPLETION_POLICY,
        "session_label_policy": SESSION_LABEL_POLICY,
        "source_schedule_hash": expected_schedule_hash,
    }
    document: dict[str, Any] = {
        "authority": _authority(),
        "blockers": [
            "CALENDAR_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
            "CALENDAR_SESSIONS_NOT_EVALUATED",
            "FUTURE_OBSERVATIONS_NOT_ADMITTED",
        ],
        "calendar_library_distribution": CALENDAR_LIBRARY_DISTRIBUTION,
        "calendar_library_version": CALENDAR_LIBRARY_VERSION,
        "calendar_protocol_id": CALENDAR_PROTOCOL_ID,
        "calendar_registration_state": (
            "CALENDAR_ASSIGNMENT_DECLARED_NOT_EXTERNALLY_TIME_ATTESTED"
        ),
        "common_date_rule": COMMON_DATE_RULE,
        "declared_at_utc": declared_at_utc,
        "distinct_calendar_ids": sorted(
            set(identity_calendar_ids) | {factor_calendar_id}
        ),
        "evaluation_not_before_date": schedule.get("evaluation_not_before_date"),
        "factor_calendar_id": factor_calendar_id,
        "factor_id": schedule.get("factor_id"),
        "factor_source_hash": schedule.get("factor_source_hash"),
        "facts": _facts(
            schedule_verified=True,
            assignments_pinned=True,
            chronology_claim_valid=True,
        ),
        "future_evaluation_id": schedule.get("future_evaluation_id"),
        "identity_calendar_assignment_hash": strict_canonical_hash(
            assignment_binding
        ),
        "identity_calendar_assignments": assignments,
        "identity_count": len(identities),
        "identity_order_hash": schedule.get("identity_order_hash"),
        "missing_calendar_policy": MISSING_CALENDAR_POLICY,
        "registration_reason": (
            "CANONICAL_CALENDAR_VALUES_PINNED_EXTERNAL_DECLARATION_TIME_UNVERIFIED"
        ),
        "schema_version": SCHEMA_VERSION,
        "session_completion_policy": SESSION_COMPLETION_POLICY,
        "session_label_policy": SESSION_LABEL_POLICY,
        "source_schedule_hash": expected_schedule_hash,
        "source_schedule_schema": SCHEDULE_SCHEMA_VERSION,
        "source_state": "VERIFIED",
        "static_fingerprint": STATIC_FINGERPRINT,
        "unsupported_calendar_policy": UNSUPPORTED_CALENDAR_POLICY,
    }
    return seal_strict_canonical_document(document, "calendar_registration_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        rebuilt = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1(
            *args,
            **expected,
        )
        return strict_json_contract_equal(document, rebuilt)
    except Exception:
        return False
