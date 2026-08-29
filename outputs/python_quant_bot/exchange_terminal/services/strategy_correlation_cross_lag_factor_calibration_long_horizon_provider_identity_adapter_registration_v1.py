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
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1 import (
    SCHEMA_VERSION as ANCHOR_REGISTRATION_SCHEMA_VERSION,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "provider-identity-adapter-registration-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260923-cross-lag-factor-calibration-long-horizon-"
    "provider-identity-adapter-registration-1"
)
REGISTRATION_PROTOCOL_ID = (
    "FUTURE_FACTOR_RESIDUAL_ORDER_PROVIDER_IDENTITY_ADAPTER_REGISTRATION_V1"
)
REGISTRATION_STATE = "IDENTITY_ADAPTER_DECLARED_ASSERTION_NOT_OBSERVED"
IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM = "ED25519"
IDENTITY_ATTESTATION_RECEIPT_ENCODING = "RFC8785_JCS_UTF8"

SOURCE_BLOCKERS = (
    "ADAPTER_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
    "ADAPTER_IMPLEMENTATION_NOT_VERIFIED",
    "FUTURE_OBSERVATION_BATCH_NOT_OBSERVED",
    "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
)
REGISTRATION_BLOCKERS = (
    "PROVIDER_IDENTITY_ASSERTION_NOT_OBSERVED",
    "PROVIDER_IDENTITY_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
    "ANCHOR_ADAPTER_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
    "IDENTITY_ADAPTER_IMPLEMENTATION_NOT_VERIFIED",
    "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
)

_ASCII_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UTC_SECOND = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_ANCHOR_CONTEXT_KEYS = frozenset(
    {
        "adapter_id",
        "adapter_implementation_sha256",
        "adapter_static_fingerprint",
        "declared_at_utc",
        "expected_observation_protocol_hash",
        "expected_preregistration_hash",
        "provider_id",
        "receipt_encoding",
        "signature_algorithm",
        "trust_root_sha256",
    }
)


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_provider_identity_verified": False,
        "future_evaluation_allowed": False,
        "identity_adapter_use_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "provider_identity_admission_allowed": False,
    }


def _facts(
    *,
    source_verified: bool = False,
    values_pinned: bool = False,
    chronology_claim_valid: bool = False,
    trust_root_separated: bool = False,
) -> dict[str, bool]:
    return {
        "evaluation_activated": False,
        "external_identity_assertion_observed": False,
        "external_identity_signature_verified": False,
        "external_registration_time_verified": False,
        "identity_adapter_implementation_verified": False,
        "identity_adapter_values_pinned": values_pinned,
        "identity_trust_root_role_separated": trust_root_separated,
        "provider_identity_verified": False,
        "registration_chronology_claim_valid": chronology_claim_valid,
        "result_available": False,
        "source_anchor_registration_verified": source_verified,
        "source_provider_key_binding_inherited": source_verified,
    }


def _ascii_id(value: Any) -> bool:
    return type(value) is str and _ASCII_ID.fullmatch(value) is not None


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
    value = _safe_text(document, "source_state")
    return value if value in {"VERIFIED", "BLOCKED", "UNKNOWN"} else "UNKNOWN"


def _unknown(
    reason: str,
    source: Any,
    *,
    expected_anchor_registration_hash: Any = None,
    source_verified: bool = False,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "authority": _authority(),
        "blockers": [reason],
        "declared_at_utc": None,
        "evaluation_not_before_date": _safe_text(
            source, "evaluation_not_before_date"
        ),
        "facts": _facts(source_verified=source_verified),
        "future_evaluation_id": _safe_text(source, "future_evaluation_id"),
        "identity_adapter_id": None,
        "identity_adapter_implementation_sha256": None,
        "identity_adapter_static_fingerprint": None,
        "identity_adapter_value_binding_hash": None,
        "identity_attestation_receipt_encoding": None,
        "identity_attestation_signature_algorithm": None,
        "identity_registry_id": None,
        "identity_registry_snapshot_id": None,
        "identity_registry_snapshot_sha256": None,
        "identity_registry_trust_root_sha256": None,
        "provider_id": _safe_text(source, "provider_id"),
        "provider_identity_document_sha256": None,
        "provider_receipt_trust_root_sha256": _safe_text(
            source, "trust_root_sha256"
        ),
        "provider_subject_id": None,
        "registration_protocol_id": REGISTRATION_PROTOCOL_ID,
        "registration_reason": reason,
        "registration_state": "UNKNOWN",
        "schema_version": SCHEMA_VERSION,
        "source_anchor_adapter_id": _safe_text(source, "adapter_id"),
        "source_anchor_adapter_registration_hash": (
            expected_anchor_registration_hash
            if strict_sha256(expected_anchor_registration_hash)
            else None
        ),
        "source_anchor_adapter_registration_schema": _safe_text(
            source, "schema_version"
        ),
        "source_observation_protocol_hash": _safe_text(
            source, "source_observation_protocol_hash"
        ),
        "source_preregistration_hash": _safe_text(
            source, "source_preregistration_hash"
        ),
        "source_state": _source_state(source),
        "static_fingerprint": STATIC_FINGERPRINT,
    }
    return seal_strict_canonical_document(document, "registration_hash")


def build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1(
    anchor_adapter_registration_v1: Any,
    observation_protocol_v1: Any,
    long_horizon_preregistration_v1: Any,
    source_verification_context: Any,
    anchor_registration_verification_context: Any,
    *,
    expected_anchor_registration_hash: Any,
    identity_adapter_id: Any,
    identity_adapter_static_fingerprint: Any,
    identity_adapter_implementation_sha256: Any,
    identity_registry_id: Any,
    identity_registry_snapshot_id: Any,
    identity_registry_snapshot_sha256: Any,
    identity_registry_trust_root_sha256: Any,
    provider_subject_id: Any,
    provider_identity_document_sha256: Any,
    identity_attestation_signature_algorithm: Any,
    identity_attestation_receipt_encoding: Any,
    declared_at_utc: Any,
) -> dict[str, Any]:
    source = anchor_adapter_registration_v1
    if not strict_sha256(expected_anchor_registration_hash):
        return _unknown(
            "EXPECTED_ANCHOR_REGISTRATION_HASH_INVALID",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
        )
    if (
        type(source) is not dict
        or source.get("registration_hash") != expected_anchor_registration_hash
    ):
        return _unknown(
            "SOURCE_ANCHOR_REGISTRATION_HASH_MISMATCH",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
        )
    if source.get("schema_version") != ANCHOR_REGISTRATION_SCHEMA_VERSION:
        return _unknown(
            "SOURCE_ANCHOR_REGISTRATION_SCHEMA_UNSUPPORTED",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
        )
    if (
        type(anchor_registration_verification_context) is not dict
        or set(anchor_registration_verification_context) != _ANCHOR_CONTEXT_KEYS
    ):
        return _unknown(
            "ANCHOR_REGISTRATION_VERIFICATION_CONTEXT_INVALID",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
        )
    try:
        source_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1(
                source,
                observation_protocol_v1,
                long_horizon_preregistration_v1,
                source_verification_context,
                **anchor_registration_verification_context,
            )
        )
    except Exception:
        source_verified = False
    if not source_verified:
        return _unknown(
            "SOURCE_ANCHOR_REGISTRATION_NOT_VERIFIED",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
        )
    if (
        source.get("source_state") != "VERIFIED"
        or source.get("registration_state")
        != "DECLARED_NOT_EXTERNALLY_TIME_ATTESTED"
        or source.get("blockers") != list(SOURCE_BLOCKERS)
    ):
        return _unknown(
            "SOURCE_ANCHOR_REGISTRATION_STATE_INVALID",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )
    source_facts = source.get("facts")
    source_authority = source.get("authority")
    if (
        type(source_facts) is not dict
        or source_facts.get("adapter_values_pinned") is not True
        or source_facts.get("trust_root_value_pinned") is not True
        or source_facts.get("external_authenticity_proven") is not False
        or type(source_authority) is not dict
        or source_authority.get("adapter_use_allowed") is not False
        or source_authority.get("current_admission_allowed") is not False
    ):
        return _unknown(
            "SOURCE_ANCHOR_AUTHORITY_INVALID",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )

    identifiers = (
        identity_adapter_id,
        identity_adapter_static_fingerprint,
        identity_registry_id,
        identity_registry_snapshot_id,
        provider_subject_id,
    )
    if not all(_ascii_id(value) for value in identifiers):
        return _unknown(
            "IDENTITY_REGISTRATION_IDENTIFIER_INVALID",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )
    hashes = (
        identity_adapter_implementation_sha256,
        identity_registry_snapshot_sha256,
        identity_registry_trust_root_sha256,
        provider_identity_document_sha256,
    )
    if not all(strict_sha256(value) for value in hashes):
        return _unknown(
            "IDENTITY_REGISTRATION_HASH_BINDING_INVALID",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )
    provider_id = _safe_text(source, "provider_id")
    provider_receipt_trust_root = _safe_text(source, "trust_root_sha256")
    if not _ascii_id(provider_id) or not strict_sha256(provider_receipt_trust_root):
        return _unknown(
            "SOURCE_PROVIDER_KEY_BINDING_INVALID",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )
    if identity_registry_trust_root_sha256 == provider_receipt_trust_root:
        return _unknown(
            "IDENTITY_TRUST_ROOT_ROLE_COLLISION",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )
    if (
        identity_attestation_signature_algorithm
        != IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM
    ):
        return _unknown(
            "IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM_UNSUPPORTED",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )
    if (
        identity_attestation_receipt_encoding
        != IDENTITY_ATTESTATION_RECEIPT_ENCODING
    ):
        return _unknown(
            "IDENTITY_ATTESTATION_RECEIPT_ENCODING_UNSUPPORTED",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )

    declared_at = _utc_second(declared_at_utc)
    source_declared_at = _utc_second(source.get("declared_at_utc"))
    evaluation_not_before = _iso_date(source.get("evaluation_not_before_date"))
    if (
        declared_at is None
        or source_declared_at is None
        or evaluation_not_before is None
    ):
        return _unknown(
            "IDENTITY_ADAPTER_DECLARATION_TIME_INVALID",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )
    if declared_at < source_declared_at:
        return _unknown(
            "IDENTITY_ADAPTER_DECLARATION_BEFORE_ANCHOR_REGISTRATION",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )
    if declared_at.date() >= evaluation_not_before:
        return _unknown(
            "IDENTITY_ADAPTER_DECLARATION_NOT_BEFORE_EVALUATION",
            source,
            expected_anchor_registration_hash=expected_anchor_registration_hash,
            source_verified=True,
        )

    binding = {
        "declared_at_utc": declared_at_utc,
        "future_evaluation_id": source.get("future_evaluation_id"),
        "identity_adapter_id": identity_adapter_id,
        "identity_adapter_implementation_sha256": (
            identity_adapter_implementation_sha256
        ),
        "identity_adapter_static_fingerprint": identity_adapter_static_fingerprint,
        "identity_attestation_receipt_encoding": (
            identity_attestation_receipt_encoding
        ),
        "identity_attestation_signature_algorithm": (
            identity_attestation_signature_algorithm
        ),
        "identity_registry_id": identity_registry_id,
        "identity_registry_snapshot_id": identity_registry_snapshot_id,
        "identity_registry_snapshot_sha256": identity_registry_snapshot_sha256,
        "identity_registry_trust_root_sha256": (
            identity_registry_trust_root_sha256
        ),
        "provider_id": provider_id,
        "provider_identity_document_sha256": provider_identity_document_sha256,
        "provider_receipt_trust_root_sha256": provider_receipt_trust_root,
        "provider_subject_id": provider_subject_id,
        "registration_protocol_id": REGISTRATION_PROTOCOL_ID,
        "source_anchor_adapter_registration_hash": (
            expected_anchor_registration_hash
        ),
        "source_observation_protocol_hash": source.get(
            "source_observation_protocol_hash"
        ),
        "source_preregistration_hash": source.get("source_preregistration_hash"),
    }
    document: dict[str, Any] = {
        "authority": _authority(),
        "blockers": list(REGISTRATION_BLOCKERS),
        "declared_at_utc": declared_at_utc,
        "evaluation_not_before_date": source.get("evaluation_not_before_date"),
        "facts": _facts(
            source_verified=True,
            values_pinned=True,
            chronology_claim_valid=True,
            trust_root_separated=True,
        ),
        "future_evaluation_id": source.get("future_evaluation_id"),
        "identity_adapter_id": identity_adapter_id,
        "identity_adapter_implementation_sha256": (
            identity_adapter_implementation_sha256
        ),
        "identity_adapter_static_fingerprint": identity_adapter_static_fingerprint,
        "identity_adapter_value_binding_hash": strict_canonical_hash(binding),
        "identity_attestation_receipt_encoding": (
            identity_attestation_receipt_encoding
        ),
        "identity_attestation_signature_algorithm": (
            identity_attestation_signature_algorithm
        ),
        "identity_registry_id": identity_registry_id,
        "identity_registry_snapshot_id": identity_registry_snapshot_id,
        "identity_registry_snapshot_sha256": identity_registry_snapshot_sha256,
        "identity_registry_trust_root_sha256": (
            identity_registry_trust_root_sha256
        ),
        "provider_id": provider_id,
        "provider_identity_document_sha256": provider_identity_document_sha256,
        "provider_receipt_trust_root_sha256": provider_receipt_trust_root,
        "provider_subject_id": provider_subject_id,
        "registration_protocol_id": REGISTRATION_PROTOCOL_ID,
        "registration_reason": (
            "IDENTITY_ADAPTER_VALUES_PINNED_EXTERNAL_ASSERTION_NOT_OBSERVED"
        ),
        "registration_state": REGISTRATION_STATE,
        "schema_version": SCHEMA_VERSION,
        "source_anchor_adapter_id": source.get("adapter_id"),
        "source_anchor_adapter_registration_hash": (
            expected_anchor_registration_hash
        ),
        "source_anchor_adapter_registration_schema": (
            ANCHOR_REGISTRATION_SCHEMA_VERSION
        ),
        "source_observation_protocol_hash": source.get(
            "source_observation_protocol_hash"
        ),
        "source_preregistration_hash": source.get("source_preregistration_hash"),
        "source_state": "VERIFIED",
        "static_fingerprint": STATIC_FINGERPRINT,
    }
    return seal_strict_canonical_document(document, "registration_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1(
    document: Any,
    anchor_adapter_registration_v1: Any,
    observation_protocol_v1: Any,
    long_horizon_preregistration_v1: Any,
    source_verification_context: Any,
    anchor_registration_verification_context: Any,
    **expected: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        rebuilt = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1(
            anchor_adapter_registration_v1,
            observation_protocol_v1,
            long_horizon_preregistration_v1,
            source_verification_context,
            anchor_registration_verification_context,
            **expected,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, rebuilt)
