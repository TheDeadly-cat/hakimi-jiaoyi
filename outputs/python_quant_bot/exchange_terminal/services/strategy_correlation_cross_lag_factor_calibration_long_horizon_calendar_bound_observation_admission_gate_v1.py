from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 import (
    POSITIVE_STATE as SESSION_POSITIVE_STATE,
    SCHEMA_VERSION as SESSION_SCHEMA_VERSION,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "calendar-bound-observation-admission-gate-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260922-cross-lag-factor-calibration-long-horizon-"
    "calendar-bound-observation-admission-gate-1"
)
PREREQUISITE_POLICY_ID = (
    "FUTURE_FACTOR_RESIDUAL_ORDER_LONG_HORIZON_"
    "CALENDAR_BOUND_OBSERVATION_ADMISSION_PREREQUISITES_V1"
)
CANDIDATE_STATE = "SESSION_VERIFIED_ADMISSION_PREREQUISITES_UNREGISTERED"

REQUIRED_EVIDENCE_KINDS = (
    "EXTERNAL_PROVIDER_IDENTITY_ATTESTATION_V1",
    "EXTERNAL_CALENDAR_REGISTRATION_TIME_ATTESTATION_V1",
    "APPEND_ONLY_REPLAY_REGISTRY_RECEIPT_V1",
    "LONG_HORIZON_EVALUATION_ACTIVATION_RECEIPT_V1",
    "OBSERVATION_ADMISSION_RECEIPT_V1",
)
REQUIRED_BLOCKERS = (
    "PROVIDER_IDENTITY_NOT_EXTERNALLY_ESTABLISHED",
    "CALENDAR_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
    "REPLAY_REGISTRY_NOT_CHECKED",
    "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
    "OBSERVATION_ADMISSION_NOT_ACTIVATED",
)

_SESSION_CONTEXT_KEYS = frozenset(
    {
        "batch_verification_context",
        "batch_verification_v1",
        "calendar_registration_v1",
        "calendar_registration_verification_context",
        "expected_batch_verification_hash",
        "expected_calendar_registration_hash",
        "observation_batch",
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


def _facts(*, source_verified: bool = False, policy_bound: bool = False) -> dict[str, bool]:
    return {
        "admission_policy_bound": policy_bound,
        "admission_receipt_verified": False,
        "calendar_registration_time_attestation_verified": False,
        "calendar_session_verification_verified": source_verified,
        "evaluation_activation_receipt_verified": False,
        "external_provider_identity_attestation_verified": False,
        "observation_admitted": False,
        "replay_registry_receipt_verified": False,
        "result_available": False,
        "source_batch_verified": source_verified,
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
    return value if type(value) is int and type(value) is not bool and value >= 0 else None


def _source_state(document: Any) -> str:
    value = _safe_text(document, "source_state")
    return value if value in {"VERIFIED", "BLOCKED", "UNKNOWN"} else "UNKNOWN"


def _document(
    source: Any,
    *,
    blocker: str | None,
    source_verified: bool,
    policy_hash: str | None,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "admission_decision_state": CANDIDATE_STATE if source_verified else "UNKNOWN",
        "admission_policy_hash": policy_hash,
        "authority": _authority(),
        "blockers": list(REQUIRED_BLOCKERS) if source_verified else [blocker],
        "calendar_session_evaluation_hash": _safe_text(
            source, "calendar_session_evaluation_hash"
        ),
        "evidence_requirement_count": len(REQUIRED_EVIDENCE_KINDS),
        "factor_id": _safe_text(source, "factor_id"),
        "factor_source_hash": _safe_text(source, "factor_source_hash"),
        "facts": _facts(source_verified=source_verified, policy_bound=source_verified),
        "future_evaluation_id": _safe_text(source, "future_evaluation_id"),
        "identity_calendar_assignment_hash": _safe_text(
            source, "identity_calendar_assignment_hash"
        ),
        "identity_count": _safe_count(source, "identity_count"),
        "identity_order_hash": _safe_text(source, "identity_order_hash"),
        "observation_batch_hash": _safe_text(source, "observation_batch_hash"),
        "prerequisite_policy_id": PREREQUISITE_POLICY_ID,
        "provider_id": _safe_text(source, "provider_id"),
        "provider_timestamp_utc": _safe_text(source, "provider_timestamp_utc"),
        "required_evidence_kinds": list(REQUIRED_EVIDENCE_KINDS),
        "row_count": _safe_count(source, "row_count"),
        "schema_version": SCHEMA_VERSION,
        "session_check_count": _safe_count(source, "session_check_count"),
        "source_batch_verification_hash": _safe_text(
            source, "source_batch_verification_hash"
        ),
        "source_calendar_registration_hash": _safe_text(
            source, "source_calendar_registration_hash"
        ),
        "source_calendar_session_verification_hash": _safe_text(
            source, "verification_hash"
        ),
        "source_calendar_session_verification_schema": _safe_text(
            source, "schema_version"
        ),
        "source_schedule_hash": _safe_text(source, "source_schedule_hash"),
        "source_state": _source_state(source),
        "static_fingerprint": STATIC_FINGERPRINT,
        "verification_reason": (
            "CALENDAR_BOUND_SOURCE_VERIFIED_EXTERNAL_ADMISSION_"
            "PREREQUISITES_UNREGISTERED"
            if source_verified
            else blocker
        ),
    }
    return seal_strict_canonical_document(document, "admission_gate_hash")


def _unknown(reason: str, source: Any) -> dict[str, Any]:
    return _document(
        source,
        blocker=reason,
        source_verified=False,
        policy_hash=None,
    )


def evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_bound_observation_admission_gate_v1(
    calendar_session_verification_v1: Any,
    calendar_session_verification_context: Any,
    *,
    expected_calendar_session_verification_hash: Any,
) -> dict[str, Any]:
    source = calendar_session_verification_v1
    if not strict_sha256(expected_calendar_session_verification_hash):
        return _unknown("EXPECTED_SESSION_VERIFICATION_HASH_INVALID", source)
    if (
        type(source) is not dict
        or source.get("verification_hash")
        != expected_calendar_session_verification_hash
    ):
        return _unknown("SOURCE_SESSION_VERIFICATION_HASH_MISMATCH", source)
    if source.get("schema_version") != SESSION_SCHEMA_VERSION:
        return _unknown("SOURCE_SESSION_VERIFICATION_SCHEMA_UNSUPPORTED", source)
    if (
        type(calendar_session_verification_context) is not dict
        or set(calendar_session_verification_context) != _SESSION_CONTEXT_KEYS
    ):
        return _unknown("SESSION_VERIFICATION_CONTEXT_INVALID", source)

    context = calendar_session_verification_context
    try:
        source_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1(
                source,
                context["calendar_registration_v1"],
                context["calendar_registration_verification_context"],
                context["batch_verification_v1"],
                context["batch_verification_context"],
                context["observation_batch"],
                expected_calendar_registration_hash=context[
                    "expected_calendar_registration_hash"
                ],
                expected_batch_verification_hash=context[
                    "expected_batch_verification_hash"
                ],
            )
        )
    except Exception:
        source_verified = False
    if not source_verified:
        return _unknown("SOURCE_SESSION_VERIFICATION_NOT_VERIFIED", source)
    if source.get("calendar_session_verification_state") != SESSION_POSITIVE_STATE:
        return _unknown("SOURCE_SESSION_VERIFICATION_STATE_NOT_POSITIVE", source)
    if source.get("source_state") != "VERIFIED":
        return _unknown("SOURCE_STATE_NOT_VERIFIED", source)
    if source.get("blockers") != list(REQUIRED_BLOCKERS):
        return _unknown("SOURCE_ADMISSION_GAPS_DRIFTED", source)

    source_facts = source.get("facts")
    source_authority = source.get("authority")
    if (
        type(source_facts) is not dict
        or source_facts.get("calendar_sessions_evaluated") is not True
        or source_facts.get("source_batch_verified") is not True
        or source_facts.get("observation_admission_allowed") is not False
        or type(source_authority) is not dict
        or source_authority.get("observation_admission_allowed") is not False
        or source_authority.get("current_admission_allowed") is not False
    ):
        return _unknown("SOURCE_ADMISSION_LOCK_INVALID", source)

    source_hashes = {
        key: _safe_text(source, key)
        for key in (
            "calendar_session_evaluation_hash",
            "identity_calendar_assignment_hash",
            "observation_batch_hash",
            "source_batch_verification_hash",
            "source_calendar_registration_hash",
            "source_schedule_hash",
            "verification_hash",
        )
    }
    if not all(strict_sha256(value) for value in source_hashes.values()):
        return _unknown("SOURCE_BINDING_HASH_INVALID", source)

    policy_hash = strict_canonical_hash(
        {
            "calendar_session_evaluation_hash": source_hashes[
                "calendar_session_evaluation_hash"
            ],
            "future_evaluation_id": _safe_text(source, "future_evaluation_id"),
            "identity_calendar_assignment_hash": source_hashes[
                "identity_calendar_assignment_hash"
            ],
            "observation_batch_hash": source_hashes["observation_batch_hash"],
            "prerequisite_policy_id": PREREQUISITE_POLICY_ID,
            "required_evidence_kinds": list(REQUIRED_EVIDENCE_KINDS),
            "source_batch_verification_hash": source_hashes[
                "source_batch_verification_hash"
            ],
            "source_calendar_registration_hash": source_hashes[
                "source_calendar_registration_hash"
            ],
            "source_calendar_session_verification_hash": source_hashes[
                "verification_hash"
            ],
            "source_schedule_hash": source_hashes["source_schedule_hash"],
        }
    )
    return _document(
        source,
        blocker=None,
        source_verified=True,
        policy_hash=policy_hash,
    )


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_bound_observation_admission_gate_v1(
    document: Any,
    calendar_session_verification_v1: Any,
    calendar_session_verification_context: Any,
    *,
    expected_calendar_session_verification_hash: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_bound_observation_admission_gate_v1(
            calendar_session_verification_v1,
            calendar_session_verification_context,
            expected_calendar_session_verification_hash=(
                expected_calendar_session_verification_hash
            ),
        )
    except (TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)
