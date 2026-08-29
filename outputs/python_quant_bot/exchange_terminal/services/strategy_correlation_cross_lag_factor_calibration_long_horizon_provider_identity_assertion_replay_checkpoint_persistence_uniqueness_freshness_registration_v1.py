from __future__ import annotations

import copy
import re
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


REGISTRATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-checkpoint-persistence-uniqueness-freshness-"
    "registration-v1"
)
RECEIPT_SCHEMA = f"{REGISTRATION_SCHEMA}-receipt"
STATIC_FINGERPRINT = (
    "20261002-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "assertion-replay-checkpoint-persistence-uniqueness-freshness-registration-1"
)
REGISTERED_STATUS = (
    "UNIQUENESS_FRESHNESS_EVIDENCE_ADAPTER_REGISTERED_RECEIPTS_UNOBSERVED"
)
UNKNOWN_STATUS = "UNKNOWN"

SOURCE_LINEAGE_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-checkpoint-persistence-lineage-candidate-v1"
)
SOURCE_LINEAGE_STATIC_FINGERPRINT = (
    "20261001-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "assertion-replay-checkpoint-persistence-lineage-1"
)
OCCURRENCE_RECEIPT_SCHEMA = (
    "provider-identity-assertion-complete-occurrence-cardinality-receipt-v1"
)
TIME_RECEIPT_SCHEMA = "provider-identity-assertion-time-window-receipt-v1"
SIGNATURE_ALGORITHM = "ed25519"
SIGNATURE_ENCODING = "base64url-no-padding"
CANONICAL_HASH_ALGORITHM = "sha256"
CANONICAL_HASH_ENCODING = "lowercase-hex"
SCAN_POLICY = "complete-zero-to-checkpoint-tree-size-exclusive-v1"
CARDINALITY_POLICY = "exactly-one-index-equal-to-replay-leaf-index-v1"
TIME_WINDOW_POLICY = "checkpoint-through-scan-to-reference-time-v1"
OCCURRENCE_SIGNATURE_DOMAIN = (
    "hakimi.provider-identity-assertion.complete-occurrence-cardinality.v1"
)
TIME_SIGNATURE_DOMAIN = "hakimi.provider-identity-assertion.time-window.v1"

_MAX_WINDOW_MS = 31 * 24 * 60 * 60 * 1000
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REGISTRATION_FIELDS = frozenset(
    {
        "schema",
        "adapter_id",
        "adapter_implementation_hash",
        "source_lineage_schema",
        "source_lineage_static_fingerprint",
        "source_replay_registration_receipt_hash",
        "source_persistence_registration_receipt_hash",
        "occurrence_provider_id",
        "occurrence_namespace",
        "occurrence_provider_key_id",
        "occurrence_provider_public_key_hash",
        "time_authority_id",
        "time_namespace",
        "time_authority_key_id",
        "time_authority_public_key_hash",
        "occurrence_receipt_schema",
        "time_receipt_schema",
        "signature_algorithm",
        "signature_encoding",
        "canonical_hash_algorithm",
        "canonical_hash_encoding",
        "scan_policy",
        "cardinality_policy",
        "time_window_policy",
        "occurrence_signature_domain",
        "time_signature_domain",
        "max_checkpoint_age_ms",
        "max_occurrence_to_reference_delay_ms",
    }
)
_EXACT_FIELDS = {
    "schema": REGISTRATION_SCHEMA,
    "source_lineage_schema": SOURCE_LINEAGE_SCHEMA,
    "source_lineage_static_fingerprint": SOURCE_LINEAGE_STATIC_FINGERPRINT,
    "occurrence_receipt_schema": OCCURRENCE_RECEIPT_SCHEMA,
    "time_receipt_schema": TIME_RECEIPT_SCHEMA,
    "signature_algorithm": SIGNATURE_ALGORITHM,
    "signature_encoding": SIGNATURE_ENCODING,
    "canonical_hash_algorithm": CANONICAL_HASH_ALGORITHM,
    "canonical_hash_encoding": CANONICAL_HASH_ENCODING,
    "scan_policy": SCAN_POLICY,
    "cardinality_policy": CARDINALITY_POLICY,
    "time_window_policy": TIME_WINDOW_POLICY,
    "occurrence_signature_domain": OCCURRENCE_SIGNATURE_DOMAIN,
    "time_signature_domain": TIME_SIGNATURE_DOMAIN,
}
_IDENTIFIER_FIELDS = (
    "adapter_id",
    "occurrence_provider_id",
    "occurrence_namespace",
    "occurrence_provider_key_id",
    "time_authority_id",
    "time_namespace",
    "time_authority_key_id",
)
_HASH_FIELDS = (
    "adapter_implementation_hash",
    "source_replay_registration_receipt_hash",
    "source_persistence_registration_receipt_hash",
    "occurrence_provider_public_key_hash",
    "time_authority_public_key_hash",
)


def _authority() -> dict[str, bool]:
    return {
        "assertion_uniqueness_verified": False,
        "freshness_verified": False,
        "replay_absence_verified": False,
        "complete_history_verified": False,
        "replay_registry_checked": False,
        "provider_identity_verified": False,
        "observation_admitted": False,
        "parameter_selection_authority": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "registration_shape_verified": False,
        "source_lineage_contract_pinned": False,
        "occurrence_and_time_roles_separated": False,
        "source_lineage_observed": False,
        "occurrence_receipt_observed": False,
        "time_receipt_observed": False,
        "external_occurrence_provider_trust_attested": False,
        "external_time_authority_trust_attested": False,
    }


def _evidence() -> dict[str, Any]:
    return {
        "adapter_id": None,
        "source_replay_registration_receipt_hash": None,
        "source_persistence_registration_receipt_hash": None,
        "occurrence_provider_id": None,
        "occurrence_provider_key_id": None,
        "time_authority_id": None,
        "time_authority_key_id": None,
        "max_checkpoint_age_ms": None,
        "max_occurrence_to_reference_delay_ms": None,
    }


def _sealed(
    *,
    status: str,
    reason: str | None,
    facts: dict[str, bool] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema": RECEIPT_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "reason": reason,
            "facts": facts or _facts(),
            "evidence": evidence or _evidence(),
            "authority": _authority(),
        },
        "receipt_hash",
    )


def _strict_identifier(value: Any) -> bool:
    return type(value) is str and _IDENTIFIER.fullmatch(value) is not None


def _strict_hash(value: Any) -> bool:
    return type(value) is str and _LOWER_SHA256.fullmatch(value) is not None


def _normalize_registration(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict:
        return None, "registration_shape_invalid"
    if set(value) != _REGISTRATION_FIELDS:
        return None, "registration_fields_invalid"
    for field, expected in _EXACT_FIELDS.items():
        if value.get(field) != expected:
            return None, f"registration_{field}_invalid"
    for field in _IDENTIFIER_FIELDS:
        if not _strict_identifier(value.get(field)):
            return None, f"registration_{field}_invalid"
    for field in _HASH_FIELDS:
        if not _strict_hash(value.get(field)):
            return None, f"registration_{field}_invalid"
    max_age = value.get("max_checkpoint_age_ms")
    if type(max_age) is not int or not 1 <= max_age <= _MAX_WINDOW_MS:
        return None, "registration_max_checkpoint_age_ms_invalid"
    max_delay = value.get("max_occurrence_to_reference_delay_ms")
    if type(max_delay) is not int or not 1 <= max_delay <= max_age:
        return None, "registration_max_occurrence_to_reference_delay_ms_invalid"
    if value["occurrence_provider_key_id"] == value["time_authority_key_id"]:
        return None, "registration_role_key_ids_not_distinct"
    if (
        value["occurrence_provider_public_key_hash"]
        == value["time_authority_public_key_hash"]
    ):
        return None, "registration_role_key_hashes_not_distinct"
    if value["occurrence_provider_id"] == value["time_authority_id"]:
        return None, "registration_role_provider_ids_not_distinct"
    return copy.deepcopy(value), None


def build_provider_identity_assertion_uniqueness_freshness_registration_v1(
    registration: Any,
) -> dict[str, Any]:
    clean, reason = _normalize_registration(registration)
    if clean is None:
        return _sealed(status=UNKNOWN_STATUS, reason=reason)
    facts = _facts()
    facts.update(
        {
            "registration_shape_verified": True,
            "source_lineage_contract_pinned": True,
            "occurrence_and_time_roles_separated": True,
        }
    )
    evidence = _evidence()
    for field in evidence:
        evidence[field] = clean[field]
    return _sealed(
        status=REGISTERED_STATUS,
        reason=None,
        facts=facts,
        evidence=evidence,
    )


def verify_provider_identity_assertion_uniqueness_freshness_registration_v1(
    receipt: Any,
    *,
    registration: Any,
) -> bool:
    if type(receipt) is not dict:
        return False
    return receipt == build_provider_identity_assertion_uniqueness_freshness_registration_v1(
        registration
    )
