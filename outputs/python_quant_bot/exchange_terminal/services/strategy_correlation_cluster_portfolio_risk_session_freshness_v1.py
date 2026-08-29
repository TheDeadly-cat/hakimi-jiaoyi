from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from . import (
    strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1
    as calendar_registration_contract,
)
from .strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1 import (
    MANIFEST_SCHEMA_VERSION as NATIVE_CUTOFF_MANIFEST_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256
from .trusted_clock import (
    TRUSTED_CLOCK_SCHEMA_VERSION,
    verify_trusted_clock_attestation,
)


REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-session-freshness-policy-registration-v1"
)
EVALUATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-session-freshness-evaluation-v1"
)
STATIC_FINGERPRINT = "20260822-completed-session-lag-freshness-1"
POLICY_ID = "PORTFOLIO_RISK_CORRELATION_COMPLETED_SESSION_LAG_V1"
LAG_RULE = "MAX_COMPLETED_REGISTERED_SESSION_LAG_ACROSS_CALENDARS"
REFERENCE_TIME_RULE = "TRUSTED_CLOCK_V2_EXTERNAL_QUORUM_ATTESTED_NOW"
REQUIRED_CLOCK_QUALITY = "EXTERNAL_QUORUM"
MINIMUM_CLOCK_SOURCES = 2
MAX_REGISTERED_COMPLETED_SESSION_LAG = 3
MAX_REFERENCE_HORIZON_CALENDAR_DAYS = 31

_NATIVE_CONTEXT_KEYS = frozenset(
    {
        "completed_price_input",
        "matrix_replay",
        "derivation_receipt",
        "composition_document",
        "composition_context",
        "expected_observation_cutoff_utc",
    }
)
_REGISTRATION_INPUT_KEYS = frozenset(
    {
        "native_cutoff_manifest",
        "native_cutoff_context",
        "expected_native_cutoff_manifest_hash",
        "max_completed_session_lag",
        "declared_at_utc",
    }
)


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _native_int(value: Any, *, minimum: int, maximum: int) -> int | None:
    if type(value) is not int or value < minimum or value > maximum:
        return None
    return value


def _iso_date(value: Any) -> date | None:
    if type(value) is not str or len(value) != 10:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _utc_second(value: Any) -> datetime | None:
    if type(value) is not str:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def _utc_from_ms(value: Any) -> datetime | None:
    if type(value) is not int or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


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


def _session_label(value: Any) -> str | None:
    session = value
    if hasattr(session, "to_pydatetime"):
        try:
            session = session.to_pydatetime()
        except Exception:
            return None
    if isinstance(session, datetime):
        return session.date().isoformat()
    if isinstance(session, date):
        return session.isoformat()
    return None


def _authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


def _check(name: str, ok: bool, passed: str, failed: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "detail": passed if ok else failed,
    }


def _verify_native_cutoff(
    manifest: Any,
    context: Any,
    expected_hash: Any,
) -> bool:
    if (
        type(manifest) is not dict
        or type(context) is not dict
        or set(context) != _NATIVE_CONTEXT_KEYS
        or not strict_sha256(expected_hash)
        or manifest.get("manifest_hash") != expected_hash
        or manifest.get("schema_version") != NATIVE_CUTOFF_MANIFEST_SCHEMA_VERSION
        or manifest.get("status") != "PASS"
    ):
        return False
    try:
        verification = (
            verify_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1(
                manifest,
                **context,
            )
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        type(verification) is dict
        and verification.get("status") == "PASS"
        and verification.get("manifest_exactly_verified") is True
        and not _list(verification.get("blockers"))
    )


def _calendar_binding(
    manifest: Any,
    native_context: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    context = _dict(native_context)
    composition_context = _dict(context.get("composition_context"))
    bundle = _dict(composition_context.get("calendar_verification_bundle"))
    projection = _dict(bundle.get("calendar_registration_v1"))
    calendar_verification = _dict(
        composition_context.get("calendar_session_verification")
    )
    expected_registration_hash = bundle.get("expected_calendar_registration_hash")
    manifest_registration_hash = _dict(_dict(manifest).get("source")).get(
        "calendar_registration_hash"
    )
    ids = projection.get("distinct_calendar_ids")
    assignments = projection.get("identity_calendar_assignments")
    if (
        not strict_sha256(expected_registration_hash)
        or not strict_sha256(manifest_registration_hash)
        or manifest_registration_hash != expected_registration_hash
        or type(ids) is not list
        or not ids
        or any(type(item) is not str or not item for item in ids)
        or ids != sorted(set(ids))
        or type(assignments) is not list
        or not assignments
    ):
        return None, "calendar_registration_projection_invalid"
    assignment_ids: list[str] = []
    for expected_index, assignment in enumerate(assignments):
        if (
            type(assignment) is not dict
            or set(assignment) != {"calendar_id", "identity_index"}
            or assignment.get("identity_index") != expected_index
            or type(assignment.get("calendar_id")) is not str
            or assignment.get("calendar_id") not in ids
        ):
            return None, "calendar_assignment_projection_invalid"
        assignment_ids.append(assignment["calendar_id"])
    verification_hash = calendar_verification.get("verification_hash")
    if (
        not strict_sha256(verification_hash)
        or _dict(manifest).get("source", {}).get(
            "calendar_session_verification_hash"
        )
        != verification_hash
    ):
        return None, "calendar_session_verification_hash_mismatch"
    runtime = calendar_registration_contract.exchange_calendars
    runtime_version = getattr(runtime, "__version__", None) if runtime is not None else None
    if runtime_version != calendar_registration_contract.CALENDAR_LIBRARY_VERSION:
        return None, "calendar_runtime_version_mismatch"
    return (
        {
            "calendar_ids": list(ids),
            "calendar_id_set_hash": strict_canonical_hash(ids),
            "calendar_registration_hash": expected_registration_hash,
            "calendar_session_verification_hash": verification_hash,
            "identity_calendar_assignment_hash": strict_canonical_hash(assignments),
            "identity_count": len(assignments),
            "runtime_version": runtime_version,
        },
        None,
    )


def build_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1(
    native_cutoff_manifest: Any,
    native_cutoff_context: Any,
    *,
    expected_native_cutoff_manifest_hash: Any,
    max_completed_session_lag: Any,
    declared_at_utc: Any,
) -> dict[str, Any]:
    native_ok = _verify_native_cutoff(
        native_cutoff_manifest,
        native_cutoff_context,
        expected_native_cutoff_manifest_hash,
    )
    binding, binding_reason = (
        _calendar_binding(native_cutoff_manifest, native_cutoff_context)
        if native_ok
        else (None, "native_cutoff_manifest_unverified")
    )
    threshold = _native_int(
        max_completed_session_lag,
        minimum=0,
        maximum=MAX_REGISTERED_COMPLETED_SESSION_LAG,
    )
    declared_at = _utc_second(declared_at_utc)
    cutoff_text = _dict(_dict(native_cutoff_manifest).get("cutoff")).get(
        "session_label_date"
    )
    cutoff_date = _iso_date(cutoff_text)
    chronology_ok = bool(
        declared_at is not None
        and cutoff_date is not None
        and declared_at.date() < cutoff_date
    )
    checks = [
        _check(
            "native_cutoff_manifest_exact",
            native_ok,
            "Native cutoff manifest exactly rebuilds.",
            "Native cutoff manifest is invalid or mismatched.",
        ),
        _check(
            "calendar_projection_inherited",
            binding is not None,
            "Calendar projection is inherited from the exact cutoff chain.",
            binding_reason or "Calendar projection is unavailable.",
        ),
        _check(
            "completed_session_lag_threshold_native",
            threshold is not None,
            "Completed-session lag threshold is a bounded native integer.",
            "Completed-session lag threshold is invalid or too permissive.",
        ),
        _check(
            "policy_declared_before_cutoff",
            chronology_ok,
            "Freshness policy was declared before the frozen cutoff date.",
            "Freshness policy chronology is invalid or retrospective.",
        ),
    ]
    blockers = [item["name"] for item in checks if not item["ok"]]
    registered = not blockers
    document = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "status": "REGISTERED" if registered else "BLOCK",
        "registration_state": (
            "COMPLETED_SESSION_LAG_POLICY_REGISTERED_NOT_EVALUATED"
            if registered
            else "BLOCKED_INVALID_FRESHNESS_POLICY_REGISTRATION"
        ),
        "static_fingerprint": STATIC_FINGERPRINT,
        "declared_at_utc": declared_at_utc if declared_at is not None else None,
        "source": {
            "native_cutoff_manifest_hash": (
                expected_native_cutoff_manifest_hash if native_ok else None
            ),
            "calendar_registration_hash": (
                binding["calendar_registration_hash"] if binding else None
            ),
            "calendar_session_verification_hash": (
                binding["calendar_session_verification_hash"] if binding else None
            ),
            "calendar_id_set_hash": (
                binding["calendar_id_set_hash"] if binding else None
            ),
            "identity_calendar_assignment_hash": (
                binding["identity_calendar_assignment_hash"] if binding else None
            ),
        },
        "policy": {
            "policy_id": POLICY_ID,
            "lag_rule": LAG_RULE,
            "reference_time_rule": REFERENCE_TIME_RULE,
            "max_completed_session_lag": threshold,
            "max_reference_horizon_calendar_days": (
                MAX_REFERENCE_HORIZON_CALENDAR_DAYS
            ),
            "required_clock_schema": TRUSTED_CLOCK_SCHEMA_VERSION,
            "required_clock_quality": REQUIRED_CLOCK_QUALITY,
            "minimum_external_clock_sources": MINIMUM_CLOCK_SOURCES,
            "calendar_library_version": (
                binding["runtime_version"] if binding else None
            ),
            "calendar_count": len(binding["calendar_ids"]) if binding else None,
            "identity_count": binding["identity_count"] if binding else None,
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "calendar_projection_inherited": binding is not None,
            "freshness_policy_defined": registered,
            "freshness_policy_evaluated": False,
            "native_cutoff_exactly_verified": native_ok,
            "external_clock_authority_authenticated": False,
            "freshness_externally_proven": False,
            "runtime_consumer_bound": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "registration_hash")


def verify_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1(
    document: Any,
    *args: Any,
    **kwargs: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1(
            *args,
            **kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def _completed_session_lag(
    calendar_ids: list[str],
    cutoff_date: date,
    reference_time: datetime,
) -> tuple[list[dict[str, Any]], str | None]:
    runtime = calendar_registration_contract.exchange_calendars
    if runtime is None or getattr(runtime, "__version__", None) != (
        calendar_registration_contract.CALENDAR_LIBRARY_VERSION
    ):
        return [], "calendar_runtime_version_mismatch"
    evidence: list[dict[str, Any]] = []
    try:
        for calendar_id in calendar_ids:
            calendar = runtime.get_calendar(calendar_id)
            cutoff_text = cutoff_date.isoformat()
            if not bool(calendar.is_session(cutoff_text)):
                return [], "native_cutoff_not_registered_session"
            cutoff_close = _session_close_utc(calendar.session_close(cutoff_text))
            if cutoff_close is None:
                return [], "native_cutoff_session_close_invalid"
            if cutoff_close > reference_time:
                return [], "native_cutoff_not_completed_at_reference_time"
            sessions = calendar.sessions_in_range(
                cutoff_text,
                reference_time.date().isoformat(),
            )
            lag = 0
            latest_completed = cutoff_text
            for session in sessions:
                label = _session_label(session)
                close = _session_close_utc(calendar.session_close(session))
                if label is None or close is None:
                    return [], "calendar_session_projection_invalid"
                if close <= reference_time:
                    latest_completed = label
                    if label > cutoff_text:
                        lag += 1
            evidence.append(
                {
                    "calendar_id_hash": strict_canonical_hash(calendar_id),
                    "latest_completed_session_label": latest_completed,
                    "completed_session_lag": lag,
                }
            )
    except Exception:
        return [], "calendar_session_lookup_failed"
    return evidence, None


def evaluate_strategy_correlation_cluster_portfolio_risk_session_freshness_v1(
    registration: Any,
    *,
    registration_inputs: Any,
    trusted_clock_attestation: Any,
    expected_trusted_clock_attestation_hash: Any,
) -> dict[str, Any]:
    inputs_ok = bool(
        type(registration_inputs) is dict
        and set(registration_inputs) == _REGISTRATION_INPUT_KEYS
    )
    registration_ok = False
    if inputs_ok:
        try:
            registration_ok = bool(
                verify_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1(
                    registration,
                    **registration_inputs,
                )
                and _dict(registration).get("status") == "REGISTERED"
            )
        except (KeyError, TypeError, ValueError):
            registration_ok = False

    clock_verification = (
        verify_trusted_clock_attestation(trusted_clock_attestation)
        if type(trusted_clock_attestation) is dict
        else {"status": "BLOCK", "blockers": ["clock_attestation_not_an_object"]}
    )
    clock = _dict(trusted_clock_attestation)
    clock_sources = clock.get("external_source_count")
    required_sources = clock.get("required_external_source_count")
    reference_time = _utc_from_ms(clock.get("attested_now_ms"))
    clock_ok = bool(
        strict_sha256(expected_trusted_clock_attestation_hash)
        and clock.get("attestation_hash") == expected_trusted_clock_attestation_hash
        and clock.get("schema_version") == TRUSTED_CLOCK_SCHEMA_VERSION
        and clock.get("status") == "PASS"
        and clock.get("quality") == REQUIRED_CLOCK_QUALITY
        and type(clock_sources) is int
        and clock_sources >= MINIMUM_CLOCK_SOURCES
        and type(required_sources) is int
        and required_sources >= MINIMUM_CLOCK_SOURCES
        and reference_time is not None
        and clock_verification.get("status") == "PASS"
        and not _list(clock_verification.get("blockers"))
    )

    binding: dict[str, Any] | None = None
    cutoff_date: date | None = None
    horizon_days: int | None = None
    lag_evidence: list[dict[str, Any]] = []
    lag_reason: str | None = None
    lag_evaluated = False
    if registration_ok and clock_ok:
        manifest = registration_inputs["native_cutoff_manifest"]
        binding, lag_reason = _calendar_binding(
            manifest,
            registration_inputs["native_cutoff_context"],
        )
        cutoff_date = _iso_date(
            _dict(_dict(manifest).get("cutoff")).get("session_label_date")
        )
        if binding is not None and cutoff_date is not None and reference_time is not None:
            horizon_days = (reference_time.date() - cutoff_date).days
            if horizon_days < 0:
                lag_reason = "reference_time_before_native_cutoff"
            elif horizon_days > MAX_REFERENCE_HORIZON_CALENDAR_DAYS:
                lag_reason = "reference_horizon_exceeds_policy_limit"
            else:
                lag_evidence, lag_reason = _completed_session_lag(
                    binding["calendar_ids"],
                    cutoff_date,
                    reference_time,
                )
                lag_evaluated = lag_reason is None

    maximum_lag = (
        max(item["completed_session_lag"] for item in lag_evidence)
        if lag_evidence
        else None
    )
    threshold = _dict(_dict(registration).get("policy")).get(
        "max_completed_session_lag"
    )
    within_policy = bool(
        lag_evaluated
        and type(maximum_lag) is int
        and type(threshold) is int
        and maximum_lag <= threshold
    )
    checks = [
        _check(
            "freshness_registration_exact",
            registration_ok,
            "Freshness policy registration exactly rebuilds.",
            "Freshness policy registration is invalid or mismatched.",
        ),
        _check(
            "trusted_clock_quorum_exact",
            clock_ok,
            "Trusted-clock v2 quorum attestation exactly verifies.",
            "Trusted-clock evidence is invalid, non-quorum, legacy, or mismatched.",
        ),
        _check(
            "completed_session_lag_evaluated",
            lag_evaluated,
            "Completed-session lag was evaluated across every registered calendar.",
            lag_reason or "Completed-session lag was not evaluated.",
        ),
        _check(
            "completed_session_lag_within_policy",
            within_policy,
            "Maximum completed-session lag is within the preregistered threshold.",
            "Maximum completed-session lag exceeds or cannot satisfy policy.",
        ),
    ]
    blockers = [item["name"] for item in checks if not item["ok"]]
    if lag_reason and "completed_session_lag_evaluated" in blockers:
        blockers.append(lag_reason)
    status = "PASS" if not blockers else "BLOCK"
    if status == "PASS":
        decision = (
            "SESSION_LAG_WITHIN_PREREGISTERED_POLICY_EXTERNAL_TIME_AUTHORITY_UNPROVEN"
        )
    elif lag_evaluated and not within_policy:
        decision = "SESSION_LAG_EXCEEDS_PREREGISTERED_POLICY"
    else:
        decision = "BLOCKED_INVALID_OR_UNVERIFIED_FRESHNESS_EVIDENCE"
    document = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "status": status,
        "decision": decision,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": {
            "registration_hash": (
                _dict(registration).get("registration_hash")
                if registration_ok
                else None
            ),
            "native_cutoff_manifest_hash": (
                registration_inputs.get("expected_native_cutoff_manifest_hash")
                if registration_ok
                else None
            ),
            "calendar_registration_hash": (
                binding["calendar_registration_hash"] if binding else None
            ),
            "calendar_session_verification_hash": (
                binding["calendar_session_verification_hash"] if binding else None
            ),
            "trusted_clock_attestation_hash": (
                expected_trusted_clock_attestation_hash if clock_ok else None
            ),
        },
        "reference": {
            "attested_now_ms": clock.get("attested_now_ms") if clock_ok else None,
            "attested_now_utc": (
                reference_time.isoformat(timespec="seconds").replace("+00:00", "Z")
                if clock_ok and reference_time is not None
                else None
            ),
            "clock_quality": clock.get("quality") if clock_ok else None,
            "external_clock_source_count": clock_sources if clock_ok else None,
            "external_clock_authority_authenticated": False,
        },
        "cutoff": {
            "session_label_date": cutoff_date.isoformat() if cutoff_date else None,
            "calendar_days_to_reference": horizon_days,
        },
        "lag": {
            "lag_rule": LAG_RULE,
            "max_completed_session_lag": maximum_lag,
            "preregistered_max_completed_session_lag": threshold,
            "calendar_count": len(lag_evidence) if lag_evaluated else None,
            "by_calendar": lag_evidence if lag_evaluated else [],
        },
        "checks": checks,
        "blockers": list(dict.fromkeys(blockers)),
        "facts": {
            "calendar_sessions_evaluated": lag_evaluated,
            "freshness_policy_defined": registration_ok,
            "freshness_policy_evaluated": lag_evaluated,
            "session_lag_within_policy": within_policy,
            "shadow_policy_condition_satisfied": status == "PASS",
            "external_clock_authority_authenticated": False,
            "freshness_externally_proven": False,
            "provider_identity_authenticated": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "evaluation_hash")


def verify_strategy_correlation_cluster_portfolio_risk_session_freshness_evaluation_v1(
    document: Any,
    *args: Any,
    **kwargs: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = evaluate_strategy_correlation_cluster_portfolio_risk_session_freshness_v1(
            *args,
            **kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "EVALUATION_SCHEMA_VERSION",
    "LAG_RULE",
    "MAX_REFERENCE_HORIZON_CALENDAR_DAYS",
    "MAX_REGISTERED_COMPLETED_SESSION_LAG",
    "POLICY_ID",
    "REGISTRATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1",
    "evaluate_strategy_correlation_cluster_portfolio_risk_session_freshness_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_session_freshness_evaluation_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1",
]
