from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 import (
    POSITIVE_STATE as SOURCE_POSITIVE_STATE,
    SCHEMA_VERSION as SOURCE_SCHEMA_VERSION,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "calendar-session-presentation-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20260922-cross-lag-factor-calibration-long-horizon-"
    "calendar-session-presentation-envelope-1"
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


def _facts(*, observed: bool = False, locally_bound: bool = False) -> dict[str, bool]:
    return {
        "aggregate_only": True,
        "canonical_calendar_ids_bound": locally_bound,
        "common_session_intersection_verified": locally_bound,
        "external_calendar_registration_time_verified": False,
        "external_provider_identity_verified": False,
        "four_axis_separation_preserved": True,
        "observation_admission_allowed": False,
        "private_session_details_exposed": False,
        "provider_time_close_bound": locally_bound,
        "replay_registry_checked": False,
        "source_verifier_replayed": observed,
    }


def _stops(state: str) -> list[dict[str, Any]]:
    states = {
        "LOCAL_SESSION_BOUND": (
            "BOUND",
            "BOUND",
            "PROVIDER_TIME_BOUND",
            "LOCKED",
        ),
        "EVIDENCE_BLOCK": ("BLOCKED", "BLOCKED", "UNKNOWN", "LOCKED"),
        "UNKNOWN": ("UNKNOWN", "UNKNOWN", "UNKNOWN", "LOCKED"),
    }[state]
    definitions = (
        ("CAL", "CANONICAL CALENDAR"),
        ("LBL", "COMMON SESSION LABELS"),
        ("CLS", "SESSION CLOSE"),
        ("ADM", "OBSERVATION ADMISSION"),
    )
    return [
        {
            "code": code,
            "label": label,
            "state": stop_state,
            "result_exposed": False,
        }
        for (code, label), stop_state in zip(definitions, states)
    ]


def _base_projection() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "presentation_status": PRESENTATION_STATUS,
        "display_state": "UNKNOWN",
        "display_reason": "SOURCE_NOT_EVALUATED",
        "source_state": "UNKNOWN",
        "source_session_verification_hash": None,
        "source_calendar_registration_hash": None,
        "source_batch_verification_hash": None,
        "source_schedule_hash": None,
        "source_observation_batch_hash": None,
        "source_axis": {
            "label": "SOURCE",
            "state": "UNKNOWN",
            "session_verification_state": "UNKNOWN",
            "verification_hash": None,
            "calendar_registration_hash": None,
            "batch_verification_hash": None,
        },
        "gap_axis": {
            "label": "GAP",
            "state": "OPEN",
            "gap_code": "PROVIDER_IDENTITY_TIME_AND_REPLAY_UNRESOLVED",
            "external_timing_unresolved": True,
            "provider_identity_unresolved": True,
            "replay_registry_unresolved": True,
        },
        "maturity_axis": {
            "label": "MATURITY",
            "state": "UNKNOWN",
            "metric": "COMMON_COMPLETED_SESSION_LABELS",
            "row_count": None,
            "completed_common_session_count": None,
            "distinct_calendar_count": None,
            "session_check_count": None,
            "batch_admitted": False,
        },
        "permission_axis": _permission_axis(),
        "timetable": {
            "status": "UNKNOWN",
            "stops": _stops("UNKNOWN"),
            "aggregate_only": True,
            "private_session_details_exposed": False,
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


def _safe_count(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _source_hashes(source: dict[str, Any]) -> dict[str, str] | None:
    fields = {
        "source_session_verification_hash": source.get("verification_hash"),
        "source_calendar_registration_hash": source.get(
            "source_calendar_registration_hash"
        ),
        "source_batch_verification_hash": source.get(
            "source_batch_verification_hash"
        ),
        "source_schedule_hash": source.get("source_schedule_hash"),
        "source_observation_batch_hash": source.get("observation_batch_hash"),
    }
    return fields if all(strict_sha256(value) for value in fields.values()) else None


def _observed(source: dict[str, Any], hashes: dict[str, str]) -> dict[str, Any]:
    locally_bound = (
        source.get("source_state") == "VERIFIED"
        and source.get("calendar_session_verification_state")
        == SOURCE_POSITIVE_STATE
    )
    display_state = "LOCAL_SESSION_BOUND" if locally_bound else "EVIDENCE_BLOCK"
    display_reason = (
        "LOCAL_CALENDAR_SESSION_BINDING_VERIFIED"
        if locally_bound
        else "CALENDAR_SESSION_EVIDENCE_BLOCK_VERIFIED"
    )
    maturity_state = "LOCAL_SESSION_SEQUENCE_BOUND" if locally_bound else "EVIDENCE_BLOCK"
    row_count = _safe_count(source.get("row_count")) if locally_bound else None
    completed_count = (
        _safe_count(source.get("completed_common_session_count"))
        if locally_bound
        else None
    )
    calendar_count = (
        _safe_count(source.get("distinct_calendar_count"))
        if locally_bound
        else None
    )
    check_count = (
        _safe_count(source.get("session_check_count"))
        if locally_bound
        else None
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "presentation_status": PRESENTATION_STATUS,
        "display_state": display_state,
        "display_reason": display_reason,
        "source_state": "OBSERVED",
        **hashes,
        "source_axis": {
            "label": "SOURCE",
            "state": "VERIFIED" if locally_bound else "VERIFIED_BLOCK",
            "session_verification_state": source.get(
                "calendar_session_verification_state"
            ),
            "verification_hash": hashes["source_session_verification_hash"],
            "calendar_registration_hash": hashes[
                "source_calendar_registration_hash"
            ],
            "batch_verification_hash": hashes["source_batch_verification_hash"],
        },
        "gap_axis": {
            "label": "GAP",
            "state": "OPEN",
            "gap_code": "PROVIDER_IDENTITY_TIME_AND_REPLAY_UNRESOLVED",
            "external_timing_unresolved": True,
            "provider_identity_unresolved": True,
            "replay_registry_unresolved": True,
        },
        "maturity_axis": {
            "label": "MATURITY",
            "state": maturity_state,
            "metric": "COMMON_COMPLETED_SESSION_LABELS",
            "row_count": row_count,
            "completed_common_session_count": completed_count,
            "distinct_calendar_count": calendar_count,
            "session_check_count": check_count,
            "batch_admitted": False,
        },
        "permission_axis": _permission_axis(),
        "timetable": {
            "status": display_state,
            "stops": _stops(display_state),
            "aggregate_only": True,
            "private_session_details_exposed": False,
        },
        "blocker_count": len(source.get("blockers", [])),
        "facts": _facts(observed=True, locally_bound=locally_bound),
        "authority": _authority(),
    }


def build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_presentation_envelope_v1(
    session_verification_v1: Any,
    calendar_registration_v1: Any,
    calendar_registration_verification_context: Any,
    batch_verification_v1: Any,
    batch_verification_context: Any,
    observation_batch: Any,
    *,
    expected_session_verification_hash: Any,
    expected_calendar_registration_hash: Any,
    expected_batch_verification_hash: Any,
) -> dict[str, Any]:
    source = session_verification_v1
    if type(source) is not dict:
        return _unknown("MISSING_SESSION_VERIFICATION")
    if source.get("schema_version") != SOURCE_SCHEMA_VERSION:
        return _unknown("UNSUPPORTED_SESSION_VERIFICATION", "UNSUPPORTED")
    if (
        not strict_sha256(expected_session_verification_hash)
        or source.get("verification_hash") != expected_session_verification_hash
    ):
        return _unknown("EXPECTED_SESSION_VERIFICATION_HASH_MISMATCH")
    try:
        source_verified = verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1(
            source,
            calendar_registration_v1,
            calendar_registration_verification_context,
            batch_verification_v1,
            batch_verification_context,
            observation_batch,
            expected_calendar_registration_hash=expected_calendar_registration_hash,
            expected_batch_verification_hash=expected_batch_verification_hash,
        )
    except Exception:
        source_verified = False
    if not source_verified:
        return _unknown("SESSION_VERIFICATION_OR_CONTEXT_INVALID")
    if (
        source.get("source_calendar_registration_hash")
        != expected_calendar_registration_hash
        or source.get("source_batch_verification_hash")
        != expected_batch_verification_hash
    ):
        return _unknown("SESSION_SOURCE_HASH_CROSS_BIND_INVALID")
    source_state = source.get("calendar_session_verification_state")
    if source_state not in {SOURCE_POSITIVE_STATE, "UNKNOWN"}:
        return _unknown("SESSION_VERIFICATION_STATE_UNKNOWN")
    hashes = _source_hashes(source)
    if hashes is None:
        return _unknown("SESSION_SOURCE_BINDINGS_INCOMPLETE")
    return _seal(_observed(source, hashes))


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_presentation_envelope_v1(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    if type(document) is not dict:
        return False
    rebuilt = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_presentation_envelope_v1(
        *args,
        **expected,
    )
    return strict_json_contract_equal(document, rebuilt)
