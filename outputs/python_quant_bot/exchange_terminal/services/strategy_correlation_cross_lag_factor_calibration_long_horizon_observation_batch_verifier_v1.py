from __future__ import annotations

import math
import re
from datetime import date
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1 import (
    POSITIVE_STATE as SIGNATURE_POSITIVE_STATE,
    SCHEMA_VERSION as SIGNATURE_SCHEMA_VERSION,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1 import (
    FOLD_COUNT,
    FOLD_ORDER,
    MAXIMUM_EVALUATED_LAG,
    MINIMUM_PAIRS_AT_MAXIMUM_LAG,
    ROWS_PER_FOLD,
    SCHEMA_VERSION as SCHEDULE_SCHEMA_VERSION,
    TOTAL_SCHEDULED_ROWS,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1 import (
    OBSERVATION_BATCH_SCHEMA,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "observation-batch-verification-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260921-cross-lag-factor-calibration-long-horizon-"
    "observation-batch-verifier-1"
)
BATCH_STATIC_FINGERPRINT = (
    "20260921-cross-lag-factor-calibration-long-horizon-observation-batch-1"
)
POSITIVE_STATE = "BATCH_CONTENT_VERIFIED_SIGNATURE_LIMITED"

_ASCII_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_BATCH_KEYS = frozenset(
    {
        "factor_id",
        "factor_source_hash",
        "first_observation_date",
        "fold_order",
        "fold_order_hash",
        "future_evaluation_id",
        "identity_order_hash",
        "last_observation_date",
        "observation_batch_hash",
        "rows",
        "schedule_hash",
        "schema_version",
        "source_report_consumer_v7_hash",
        "static_fingerprint",
    }
)
_ROW_KEYS = frozenset(
    {
        "factor_return",
        "fold_id",
        "fold_position",
        "observation_date",
        "observation_id",
        "position",
        "returns",
    }
)
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
_SIGNATURE_CONTEXT_KEYS = frozenset(
    {
        "attestation_receipt",
        "expected_attestation_hash",
        "expected_registration_hash",
        "long_horizon_preregistration_v1",
        "observation_protocol_v1",
        "registration_v1",
        "registration_verification_context",
        "source_verification_context",
    }
)


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_authenticity_proven": False,
        "future_evaluation_allowed": False,
        "live_order_allowed": False,
        "observation_admission_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _facts(
    *,
    schedule_verified: bool = False,
    signature_verified: bool = False,
    batch_seal_verified: bool = False,
    batch_content_verified: bool = False,
) -> dict[str, bool]:
    return {
        "batch_content_verified": batch_content_verified,
        "batch_hash_signed": batch_content_verified and signature_verified,
        "batch_seal_verified": batch_seal_verified,
        "date_window_verified": batch_content_verified,
        "evaluation_activated": False,
        "external_authenticity_proven": False,
        "external_registration_time_verified": False,
        "fold_assignment_verified": batch_content_verified,
        "identity_factor_content_complete": batch_content_verified,
        "observation_admitted": False,
        "provider_identity_verified": False,
        "replay_registry_checked": False,
        "result_available": False,
        "schedule_verified": schedule_verified,
        "signature_verification_verified": signature_verified,
    }


def _iso_date(value: Any) -> date | None:
    if type(value) is not str:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _finite_number(value: Any) -> bool:
    return (
        type(value) in (int, float)
        and type(value) is not bool
        and math.isfinite(float(value))
    )


def _safe_text(document: Any, key: str) -> str | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is str else None


def _source_state(schedule: Any, signature_verification: Any) -> str:
    values = []
    for document in (schedule, signature_verification):
        if type(document) is dict:
            value = document.get("source_state")
            if value in {"VERIFIED", "BLOCKED", "UNKNOWN"}:
                values.append(value)
    if "BLOCKED" in values:
        return "BLOCKED"
    return "VERIFIED" if values and all(value == "VERIFIED" for value in values) else "UNKNOWN"


def _unknown(
    reason: str,
    schedule: Any,
    signature_verification: Any,
    batch: Any,
    *,
    expected_schedule_hash: Any = None,
    expected_signature_verification_hash: Any = None,
    expected_batch_hash: Any = None,
    schedule_verified: bool = False,
    signature_verified: bool = False,
    batch_seal_verified: bool = False,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "attestation_hash": _safe_text(signature_verification, "attestation_hash"),
        "authority": _authority(),
        "blockers": [reason],
        "factor_id": _safe_text(batch, "factor_id"),
        "factor_source_hash": _safe_text(batch, "factor_source_hash"),
        "facts": _facts(
            schedule_verified=schedule_verified,
            signature_verified=signature_verified,
            batch_seal_verified=batch_seal_verified,
        ),
        "first_observation_date": _safe_text(batch, "first_observation_date"),
        "fold_count": None,
        "fold_order_hash": _safe_text(batch, "fold_order_hash"),
        "future_evaluation_id": _safe_text(batch, "future_evaluation_id"),
        "identity_count": None,
        "identity_order_hash": _safe_text(batch, "identity_order_hash"),
        "last_observation_date": _safe_text(batch, "last_observation_date"),
        "maximum_evaluated_lag": None,
        "minimum_pairs_at_maximum_lag": None,
        "observation_batch_hash": (
            expected_batch_hash if strict_sha256(expected_batch_hash) else None
        ),
        "private_observation_ledger_hash": None,
        "provider_id": _safe_text(signature_verification, "provider_id"),
        "provider_timestamp_utc": _safe_text(
            signature_verification, "provider_timestamp_utc"
        ),
        "row_count": None,
        "rows_per_fold": None,
        "schedule_hash": (
            expected_schedule_hash if strict_sha256(expected_schedule_hash) else None
        ),
        "schema_version": SCHEMA_VERSION,
        "signature_verification_hash": (
            expected_signature_verification_hash
            if strict_sha256(expected_signature_verification_hash)
            else None
        ),
        "source_report_consumer_v7_hash": _safe_text(
            batch, "source_report_consumer_v7_hash"
        ),
        "source_state": _source_state(schedule, signature_verification),
        "static_fingerprint": STATIC_FINGERPRINT,
        "verification_reason": reason,
        "verification_state": "UNKNOWN",
    }
    return seal_strict_canonical_document(document, "verification_hash")


def evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1(
    fold_schedule_v1: Any,
    schedule_verification_context: Any,
    signature_verification_v1: Any,
    signature_verification_context: Any,
    observation_batch: Any,
    *,
    expected_schedule_hash: Any,
    expected_signature_verification_hash: Any,
    expected_batch_hash: Any,
) -> dict[str, Any]:
    schedule = fold_schedule_v1
    signature_verification = signature_verification_v1
    batch = observation_batch
    for value, reason in (
        (expected_schedule_hash, "EXPECTED_SCHEDULE_HASH_INVALID"),
        (
            expected_signature_verification_hash,
            "EXPECTED_SIGNATURE_VERIFICATION_HASH_INVALID",
        ),
        (expected_batch_hash, "EXPECTED_BATCH_HASH_INVALID"),
    ):
        if not strict_sha256(value):
            return _unknown(
                reason,
                schedule,
                signature_verification,
                batch,
                expected_schedule_hash=expected_schedule_hash,
                expected_signature_verification_hash=(
                    expected_signature_verification_hash
                ),
                expected_batch_hash=expected_batch_hash,
            )
    if type(schedule) is not dict or schedule.get("schedule_hash") != expected_schedule_hash:
        return _unknown(
            "SOURCE_SCHEDULE_HASH_MISMATCH",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
        )
    if schedule.get("schema_version") != SCHEDULE_SCHEMA_VERSION:
        return _unknown(
            "SOURCE_SCHEDULE_SCHEMA_UNSUPPORTED",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
        )
    if (
        type(schedule_verification_context) is not dict
        or set(schedule_verification_context) != _SCHEDULE_CONTEXT_KEYS
    ):
        return _unknown(
            "SCHEDULE_VERIFICATION_CONTEXT_INVALID",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
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
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
        )
    if schedule.get("schedule_state") != "SCHEDULE_DECLARED_NOT_EXTERNALLY_TIME_ATTESTED":
        return _unknown(
            "SOURCE_SCHEDULE_NOT_DECLARED",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
        )
    if (
        type(signature_verification) is not dict
        or signature_verification.get("verification_hash")
        != expected_signature_verification_hash
    ):
        return _unknown(
            "SOURCE_SIGNATURE_VERIFICATION_HASH_MISMATCH",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
        )
    if signature_verification.get("schema_version") != SIGNATURE_SCHEMA_VERSION:
        return _unknown(
            "SOURCE_SIGNATURE_VERIFICATION_SCHEMA_UNSUPPORTED",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
        )
    if (
        type(signature_verification_context) is not dict
        or set(signature_verification_context) != _SIGNATURE_CONTEXT_KEYS
    ):
        return _unknown(
            "SIGNATURE_VERIFICATION_CONTEXT_INVALID",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
        )
    try:
        signature_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1(
                signature_verification,
                signature_verification_context["registration_v1"],
                signature_verification_context["observation_protocol_v1"],
                signature_verification_context["long_horizon_preregistration_v1"],
                signature_verification_context["source_verification_context"],
                signature_verification_context["registration_verification_context"],
                signature_verification_context["attestation_receipt"],
                expected_registration_hash=signature_verification_context[
                    "expected_registration_hash"
                ],
                expected_attestation_hash=signature_verification_context[
                    "expected_attestation_hash"
                ],
            )
        )
    except Exception:
        signature_verified = False
    if not signature_verified:
        return _unknown(
            "SOURCE_SIGNATURE_VERIFICATION_NOT_VERIFIED",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
        )
    if signature_verification.get("verification_state") != SIGNATURE_POSITIVE_STATE:
        return _unknown(
            "SOURCE_SIGNATURE_STATE_NOT_POSITIVE",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
        )
    if signature_verification.get("observation_batch_hash") != expected_batch_hash:
        return _unknown(
            "SIGNED_BATCH_HASH_MISMATCH",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
        )
    if type(batch) is not dict or set(batch) != _BATCH_KEYS:
        return _unknown(
            "OBSERVATION_BATCH_FIELDS_INVALID",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
        )
    if batch.get("observation_batch_hash") != expected_batch_hash:
        return _unknown(
            "OBSERVATION_BATCH_HASH_MISMATCH",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
        )
    try:
        sealed = seal_strict_canonical_document(
            {
                key: value
                for key, value in batch.items()
                if key != "observation_batch_hash"
            },
            "observation_batch_hash",
        )
    except (TypeError, ValueError):
        sealed = None
    if sealed is None or not strict_json_contract_equal(batch, sealed):
        return _unknown(
            "OBSERVATION_BATCH_SEAL_INVALID",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
        )
    if (
        batch.get("schema_version") != OBSERVATION_BATCH_SCHEMA
        or batch.get("static_fingerprint") != BATCH_STATIC_FINGERPRINT
    ):
        return _unknown(
            "OBSERVATION_BATCH_IDENTITY_INVALID",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
            batch_seal_verified=True,
        )

    source_context = schedule_verification_context["source_verification_context"]
    registration = (
        source_context.get("residualization_registration")
        if type(source_context) is dict
        else None
    )
    identities = registration.get("identity_order") if type(registration) is dict else None
    if type(identities) is not list or not identities:
        return _unknown(
            "SOURCE_IDENTITY_ORDER_UNAVAILABLE",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
            batch_seal_verified=True,
        )
    if (
        batch.get("schedule_hash") != expected_schedule_hash
        or batch.get("future_evaluation_id") != schedule.get("future_evaluation_id")
        or batch.get("source_report_consumer_v7_hash")
        != schedule.get("source_report_consumer_v7_hash")
        or batch.get("identity_order_hash") != schedule.get("identity_order_hash")
        or batch.get("factor_id") != schedule.get("factor_id")
        or batch.get("factor_source_hash") != schedule.get("factor_source_hash")
        or batch.get("fold_order") != list(FOLD_ORDER)
        or batch.get("fold_order_hash") != strict_canonical_hash(list(FOLD_ORDER))
    ):
        return _unknown(
            "OBSERVATION_BATCH_SOURCE_BINDINGS_INVALID",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
            batch_seal_verified=True,
        )
    rows = batch.get("rows")
    if type(rows) is not list or len(rows) != TOTAL_SCHEDULED_ROWS:
        return _unknown(
            "OBSERVATION_BATCH_ROW_COUNT_INVALID",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
            batch_seal_verified=True,
        )
    evaluation_not_before = _iso_date(schedule.get("evaluation_not_before_date"))
    previous_date: date | None = None
    observation_ids: set[str] = set()
    parsed_dates: list[str] = []
    for index, row in enumerate(rows):
        if type(row) is not dict or set(row) != _ROW_KEYS:
            reason = "OBSERVATION_ROW_FIELDS_INVALID"
            break
        fold_index = index // ROWS_PER_FOLD
        if (
            row.get("position") != index
            or row.get("fold_id") != FOLD_ORDER[fold_index]
            or row.get("fold_position") != index % ROWS_PER_FOLD
        ):
            reason = "OBSERVATION_FOLD_ASSIGNMENT_INVALID"
            break
        observation_id = row.get("observation_id")
        if (
            type(observation_id) is not str
            or _ASCII_ID.fullmatch(observation_id) is None
            or observation_id in observation_ids
        ):
            reason = "OBSERVATION_ID_INVALID_OR_DUPLICATE"
            break
        observation_ids.add(observation_id)
        observation_date = _iso_date(row.get("observation_date"))
        if (
            observation_date is None
            or evaluation_not_before is None
            or observation_date < evaluation_not_before
            or (previous_date is not None and observation_date <= previous_date)
        ):
            reason = "OBSERVATION_DATE_ORDER_OR_WINDOW_INVALID"
            break
        previous_date = observation_date
        parsed_dates.append(observation_date.isoformat())
        if not _finite_number(row.get("factor_return")):
            reason = "OBSERVATION_FACTOR_RETURN_INVALID"
            break
        returns = row.get("returns")
        if type(returns) is not dict or set(returns) != set(identities):
            reason = "OBSERVATION_IDENTITY_RETURNS_INVALID"
            break
        if any(not _finite_number(returns.get(identity)) for identity in identities):
            reason = "OBSERVATION_IDENTITY_RETURN_VALUE_INVALID"
            break
    else:
        reason = ""
    if reason:
        return _unknown(
            reason,
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
            batch_seal_verified=True,
        )
    if (
        batch.get("first_observation_date") != parsed_dates[0]
        or batch.get("last_observation_date") != parsed_dates[-1]
        or signature_verification.get("batch_first_observation_date")
        != parsed_dates[0]
        or signature_verification.get("batch_last_observation_date")
        != parsed_dates[-1]
    ):
        return _unknown(
            "OBSERVATION_BATCH_DATE_BINDINGS_INVALID",
            schedule,
            signature_verification,
            batch,
            expected_schedule_hash=expected_schedule_hash,
            expected_signature_verification_hash=expected_signature_verification_hash,
            expected_batch_hash=expected_batch_hash,
            schedule_verified=True,
            signature_verified=True,
            batch_seal_verified=True,
        )

    document: dict[str, Any] = {
        "attestation_hash": signature_verification.get("attestation_hash"),
        "authority": _authority(),
        "blockers": [
            "PROVIDER_IDENTITY_NOT_EXTERNALLY_ESTABLISHED",
            "REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
            "REPLAY_REGISTRY_NOT_CHECKED",
            "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
        ],
        "factor_id": batch.get("factor_id"),
        "factor_source_hash": batch.get("factor_source_hash"),
        "facts": _facts(
            schedule_verified=True,
            signature_verified=True,
            batch_seal_verified=True,
            batch_content_verified=True,
        ),
        "first_observation_date": parsed_dates[0],
        "fold_count": FOLD_COUNT,
        "fold_order_hash": batch.get("fold_order_hash"),
        "future_evaluation_id": batch.get("future_evaluation_id"),
        "identity_count": len(identities),
        "identity_order_hash": batch.get("identity_order_hash"),
        "last_observation_date": parsed_dates[-1],
        "maximum_evaluated_lag": MAXIMUM_EVALUATED_LAG,
        "minimum_pairs_at_maximum_lag": MINIMUM_PAIRS_AT_MAXIMUM_LAG,
        "observation_batch_hash": expected_batch_hash,
        "private_observation_ledger_hash": strict_canonical_hash(rows),
        "provider_id": signature_verification.get("provider_id"),
        "provider_timestamp_utc": signature_verification.get(
            "provider_timestamp_utc"
        ),
        "row_count": len(rows),
        "rows_per_fold": ROWS_PER_FOLD,
        "schedule_hash": expected_schedule_hash,
        "schema_version": SCHEMA_VERSION,
        "signature_verification_hash": expected_signature_verification_hash,
        "source_report_consumer_v7_hash": batch.get(
            "source_report_consumer_v7_hash"
        ),
        "source_state": "VERIFIED",
        "static_fingerprint": STATIC_FINGERPRINT,
        "verification_reason": (
            "BATCH_CONTENT_AND_SIGNED_HASH_VERIFIED_EXTERNAL_PROVENANCE_INCOMPLETE"
        ),
        "verification_state": POSITIVE_STATE,
    }
    return seal_strict_canonical_document(document, "verification_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1(
            *args,
            **expected,
        )
        return strict_json_contract_equal(document, rebuilt)
    except Exception:
        return False
