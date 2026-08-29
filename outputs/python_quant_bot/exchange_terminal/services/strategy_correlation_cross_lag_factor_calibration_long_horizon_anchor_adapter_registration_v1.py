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
    PROTOCOL_ID as SOURCE_PROTOCOL_ID,
    SCHEMA_VERSION as SOURCE_SCHEMA_VERSION,
    STATIC_FINGERPRINT as SOURCE_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "anchor-adapter-registration-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260918-cross-lag-factor-calibration-long-horizon-"
    "anchor-adapter-registration-1"
)
REGISTRATION_PROTOCOL_ID = (
    "FUTURE_FACTOR_RESIDUAL_ORDER_EXTERNAL_ANCHOR_ADAPTER_REGISTRATION_V1"
)
SIGNATURE_ALGORITHMS = (
    "ED25519",
    "ECDSA_P256_SHA256",
    "RSA_PSS_SHA256",
)
RECEIPT_ENCODINGS = (
    "PROVIDER_OPAQUE_BYTES",
    "RFC8785_JCS_UTF8",
)

_ASCII_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UTC_SECOND = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _authority() -> dict[str, bool]:
    return {
        "adapter_use_allowed": False,
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_registration_time_verified": False,
        "external_time_anchor_verified": False,
        "future_evaluation_allowed": False,
        "future_observation_collection_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _facts(
    *,
    source_verified: bool = False,
    values_pinned: bool = False,
    chronology_claim_valid: bool = False,
) -> dict[str, bool]:
    return {
        "adapter_implementation_verified": False,
        "adapter_values_pinned": values_pinned,
        "evaluation_activated": False,
        "external_authenticity_proven": False,
        "external_registration_time_verified": False,
        "observation_batch_present": False,
        "observations_collected": False,
        "registration_chronology_claim_valid": chronology_claim_valid,
        "result_available": False,
        "source_observation_protocol_verified": source_verified,
        "trust_root_value_pinned": values_pinned,
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


def _ascii_id(value: Any) -> bool:
    return type(value) is str and _ASCII_ID.fullmatch(value) is not None


def _source_state(document: Any) -> str:
    if type(document) is not dict:
        return "UNKNOWN"
    value = document.get("source_state")
    return value if value in {"VERIFIED", "BLOCKED", "UNKNOWN"} else "UNKNOWN"


def _source_text(document: Any, key: str) -> str | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is str else None


def _unknown(
    reason: str,
    source_protocol: Any,
    *,
    expected_source_protocol_hash: Any = None,
    expected_preregistration_hash: Any = None,
    source_verified: bool = False,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "adapter_id": None,
        "adapter_implementation_sha256": None,
        "adapter_static_fingerprint": None,
        "adapter_value_binding_hash": None,
        "authority": _authority(),
        "blockers": [reason],
        "declared_at_utc": None,
        "evaluation_not_before_date": _source_text(
            source_protocol, "evaluation_not_before_date"
        ),
        "facts": _facts(source_verified=source_verified),
        "future_evaluation_id": _source_text(source_protocol, "future_evaluation_id"),
        "provider_id": None,
        "receipt_encoding": None,
        "registration_protocol_id": REGISTRATION_PROTOCOL_ID,
        "registration_reason": reason,
        "registration_state": "UNKNOWN",
        "schema_version": SCHEMA_VERSION,
        "signature_algorithm": None,
        "source_external_time_anchor_reference_hash": _source_text(
            source_protocol, "source_external_time_anchor_reference_hash"
        ),
        "source_observation_protocol_hash": (
            expected_source_protocol_hash
            if strict_sha256(expected_source_protocol_hash)
            else None
        ),
        "source_observation_protocol_schema": _source_text(
            source_protocol, "schema_version"
        ),
        "source_preregistered_at_utc": None,
        "source_preregistration_hash": (
            expected_preregistration_hash
            if strict_sha256(expected_preregistration_hash)
            else None
        ),
        "source_state": _source_state(source_protocol),
        "static_fingerprint": STATIC_FINGERPRINT,
        "trust_root_sha256": None,
    }
    return seal_strict_canonical_document(document, "registration_hash")


def build_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1(
    observation_protocol_v1: Any,
    long_horizon_preregistration_v1: Any,
    source_verification_context: Any,
    *,
    expected_observation_protocol_hash: Any,
    expected_preregistration_hash: Any,
    adapter_id: Any,
    adapter_static_fingerprint: Any,
    adapter_implementation_sha256: Any,
    provider_id: Any,
    trust_root_sha256: Any,
    signature_algorithm: Any,
    receipt_encoding: Any,
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
    ):
        return _unknown(
            "SOURCE_OBSERVATION_PROTOCOL_IDENTITY_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if (
        source_protocol.get("source_state") != "VERIFIED"
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
    if type(long_horizon_preregistration_v1) is not dict:
        return _unknown(
            "SOURCE_PREREGISTRATION_NOT_OBJECT",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )

    if not _ascii_id(adapter_id) or not _ascii_id(adapter_static_fingerprint):
        return _unknown(
            "ADAPTER_IDENTITY_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if not _ascii_id(provider_id):
        return _unknown(
            "PROVIDER_ID_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if not strict_sha256(adapter_implementation_sha256) or not strict_sha256(
        trust_root_sha256
    ):
        return _unknown(
            "ADAPTER_HASH_BINDINGS_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if signature_algorithm not in SIGNATURE_ALGORITHMS:
        return _unknown(
            "SIGNATURE_ALGORITHM_UNSUPPORTED",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if receipt_encoding not in RECEIPT_ENCODINGS:
        return _unknown(
            "RECEIPT_ENCODING_UNSUPPORTED",
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
            "ADAPTER_DECLARATION_TIME_INVALID",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if declared_at < preregistered_at:
        return _unknown(
            "ADAPTER_DECLARATION_BEFORE_PREREGISTRATION",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )
    if declared_at.date() >= evaluation_not_before:
        return _unknown(
            "ADAPTER_DECLARATION_NOT_BEFORE_EVALUATION",
            source_protocol,
            expected_source_protocol_hash=expected_observation_protocol_hash,
            expected_preregistration_hash=expected_preregistration_hash,
            source_verified=True,
        )

    binding = {
        "adapter_id": adapter_id,
        "adapter_implementation_sha256": adapter_implementation_sha256,
        "adapter_static_fingerprint": adapter_static_fingerprint,
        "declared_at_utc": declared_at_utc,
        "provider_id": provider_id,
        "receipt_encoding": receipt_encoding,
        "signature_algorithm": signature_algorithm,
        "source_observation_protocol_hash": expected_observation_protocol_hash,
        "source_preregistration_hash": expected_preregistration_hash,
        "trust_root_sha256": trust_root_sha256,
    }
    document: dict[str, Any] = {
        "adapter_id": adapter_id,
        "adapter_implementation_sha256": adapter_implementation_sha256,
        "adapter_static_fingerprint": adapter_static_fingerprint,
        "adapter_value_binding_hash": strict_canonical_hash(binding),
        "authority": _authority(),
        "blockers": [
            "ADAPTER_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
            "ADAPTER_IMPLEMENTATION_NOT_VERIFIED",
            "FUTURE_OBSERVATION_BATCH_NOT_OBSERVED",
            "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
        ],
        "declared_at_utc": declared_at_utc,
        "evaluation_not_before_date": source_protocol.get(
            "evaluation_not_before_date"
        ),
        "facts": _facts(
            source_verified=True,
            values_pinned=True,
            chronology_claim_valid=True,
        ),
        "future_evaluation_id": source_protocol.get("future_evaluation_id"),
        "provider_id": provider_id,
        "receipt_encoding": receipt_encoding,
        "registration_protocol_id": REGISTRATION_PROTOCOL_ID,
        "registration_reason": (
            "ADAPTER_VALUES_PINNED_EXTERNAL_REGISTRATION_TIME_UNVERIFIED"
        ),
        "registration_state": "DECLARED_NOT_EXTERNALLY_TIME_ATTESTED",
        "schema_version": SCHEMA_VERSION,
        "signature_algorithm": signature_algorithm,
        "source_external_time_anchor_reference_hash": source_protocol.get(
            "source_external_time_anchor_reference_hash"
        ),
        "source_observation_protocol_hash": expected_observation_protocol_hash,
        "source_observation_protocol_schema": SOURCE_SCHEMA_VERSION,
        "source_preregistered_at_utc": long_horizon_preregistration_v1.get(
            "preregistered_at_utc"
        ),
        "source_preregistration_hash": expected_preregistration_hash,
        "source_state": "VERIFIED",
        "static_fingerprint": STATIC_FINGERPRINT,
        "trust_root_sha256": trust_root_sha256,
    }
    return seal_strict_canonical_document(document, "registration_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1(
    document: Any,
    observation_protocol_v1: Any,
    long_horizon_preregistration_v1: Any,
    source_verification_context: Any,
    **expected: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        rebuilt = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1(
            observation_protocol_v1,
            long_horizon_preregistration_v1,
            source_verification_context,
            **expected,
        )
        return strict_json_contract_equal(document, rebuilt)
    except Exception:
        return False
