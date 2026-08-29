"""Preregister persistence evidence for an ADR0352 common replay view.

The registration is consumer-first and performs no I/O. It binds one exact
ADR0352 preregistration to domain-separated future asset, write, and reopen
receipt contracts while keeping provider trust, receipt observation,
durability, authoritative pinning, and every trading authority false.
"""

from __future__ import annotations

import base64
import binascii
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from hmac import compare_digest
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1
    as replay_binding_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-lifecycle-replay-checkpoint-persistence-"
    "registration-v1"
)
CHECKPOINT_ASSET_SCHEMA_VERSION = (
    "strategy-correlation-lifecycle-replay-common-view-checkpoint-"
    "persistence-asset-v1"
)
WRITE_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-lifecycle-replay-common-view-checkpoint-"
    "persistence-write-receipt-v1"
)
REOPEN_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-lifecycle-replay-common-view-checkpoint-"
    "persistence-reopen-receipt-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-multi-window-lifecycle-replay-checkpoint-"
    "persistence-registration-v1-synthetic-unmounted-lock-1"
)
REPLAY_BINDING_V1_IMPLEMENTATION_SHA256 = (
    "44872a353d2380a09f9d45ba3a3e229c1e54aba3c737439a6f841ab181f9bef9"
)
SIGNATURE_ALGORITHM = "ED25519"
RECEIPT_ENCODING = "STRICT_CANONICAL_JSON_UTF8"
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
CHECKPOINT_ASSET_HASH_DOMAIN = (
    "hakimi.strategy-correlation.lifecycle-replay.checkpoint-persistence."
    "asset.v1"
)
WRITE_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.lifecycle-replay.checkpoint-persistence."
    "write.v1"
)
REOPEN_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.lifecycle-replay.checkpoint-persistence."
    "reopen.v1"
)
RECORD_CARDINALITY_POLICY = "EXACTLY_ONE_CHECKPOINT_ASSET_RECORD_V1"
SESSION_SEPARATION_POLICY = "DISTINCT_WRITE_AND_REOPEN_SESSIONS_V1"
SOURCE_BINDING_POLICY = "EXACT_ADR0352_COMMON_REGISTRY_VIEW_V1"
IO_MODE = "EXTERNAL_RECEIPTS_ONLY_NO_LOCAL_IO_V1"
PERSISTENCE_PROVIDER_KEY_ROLE = (
    "LIFECYCLE_REPLAY_CHECKPOINT_PERSISTENCE_PROVIDER"
)

_MAX_DELAY_SECONDS = 366 * 24 * 60 * 60
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_CONFIGURATION_FIELDS = frozenset(
    {
        "declared_at_utc",
        "excluded_upstream_public_key_hashes_by_window",
        "max_reopen_receipt_delay_seconds",
        "max_write_receipt_delay_seconds",
        "min_reopen_separation_seconds",
        "persistence_adapter_id",
        "persistence_adapter_implementation_hash",
        "persistence_namespace",
        "persistence_provider_id",
        "persistence_provider_key_id",
        "persistence_provider_public_key_base64",
    }
)
_EXCLUDED_KEY_ROW_FIELDS = frozenset(
    {"public_key_sha256s", "window_id"}
)
_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_AUTHORITY = {
    "authoritative_future_pin_allowed": False,
    "candidate_activation_allowed": False,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "durable_checkpoint_claim_allowed": False,
    "live_order_allowed": False,
    "paper_authorized": False,
    "persistence_provider_use_allowed": False,
    "profitability_claim_allowed": False,
    "writer_allowed": False,
}


def _exact_hash(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _strict_id(value: Any) -> bool:
    return type(value) is str and bool(_ID_RE.fullmatch(value))


def _strict_delay(value: Any) -> bool:
    return bool(
        type(value) is int
        and not isinstance(value, bool)
        and 1 <= value <= _MAX_DELAY_SECONDS
    )


def _utc(value: Any) -> datetime | None:
    if type(value) is not str or value != value.strip():
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        return None
    return parsed


def _decode_public_key(value: Any) -> bytes | None:
    if type(value) is not str or not value or value != value.strip():
        return None
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return None
    if (
        len(decoded) != 32
        or base64.b64encode(decoded).decode("ascii") != value
    ):
        return None
    return decoded


def _source_preregistration_exact(
    document: Any,
    lifecycle_binding_preregistration: Any,
    provider_binding_preregistration: Any,
    overlap_preregistration: Any,
    multi_window_preregistration: Any,
) -> bool:
    if not all(
        type(value) is dict
        for value in (
            document,
            lifecycle_binding_preregistration,
            provider_binding_preregistration,
            overlap_preregistration,
            multi_window_preregistration,
        )
    ):
        return False
    try:
        expected = replay_binding_v1.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_preregistration_v1(
            lifecycle_binding_preregistration,
            provider_binding_preregistration,
            overlap_preregistration,
            multi_window_preregistration,
            document.get("expected_replay_bindings"),
            registration_sequence=document.get("registration_sequence"),
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        type(expected) is dict
        and strict_json_contract_equal(document, expected)
    )


def _configuration_evidence(
    configuration: Any,
    source_preregistration: dict[str, Any],
) -> tuple[str, list[dict[str, str]], int] | None:
    if (
        type(configuration) is not dict
        or frozenset(configuration) != _CONFIGURATION_FIELDS
    ):
        return None
    identifiers = (
        configuration.get("persistence_provider_id"),
        configuration.get("persistence_namespace"),
        configuration.get("persistence_adapter_id"),
        configuration.get("persistence_provider_key_id"),
    )
    if not all(_strict_id(value) for value in identifiers):
        return None
    implementation_hash = configuration.get(
        "persistence_adapter_implementation_hash"
    )
    if not _exact_hash(implementation_hash):
        return None
    public_key = _decode_public_key(
        configuration.get("persistence_provider_public_key_base64")
    )
    if public_key is None:
        return None
    public_key_hash = hashlib.sha256(public_key).hexdigest()
    source_rows = source_preregistration.get("expected_replay_bindings")
    windows = source_preregistration.get("expected_windows")
    excluded_rows = configuration.get(
        "excluded_upstream_public_key_hashes_by_window"
    )
    if (
        type(source_rows) is not list
        or type(windows) is not list
        or type(excluded_rows) is not list
        or len(excluded_rows) != len(windows)
        or len(source_rows) != len(windows)
        or not windows
    ):
        return None
    normalized_rows: list[dict[str, str]] = []
    all_upstream_hashes: set[str] = set()
    for window_id, source_row, excluded_row in zip(
        windows,
        source_rows,
        excluded_rows,
        strict=True,
    ):
        if (
            type(source_row) is not dict
            or type(excluded_row) is not dict
            or frozenset(excluded_row) != _EXCLUDED_KEY_ROW_FIELDS
            or excluded_row.get("window_id") != window_id
            or type(excluded_row.get("public_key_sha256s")) is not list
        ):
            return None
        hashes = excluded_row["public_key_sha256s"]
        if (
            len(hashes) != 4
            or hashes != sorted(set(hashes))
            or not all(_exact_hash(value) for value in hashes)
            or strict_canonical_hash(hashes)
            != source_row.get("excluded_upstream_public_key_set_hash")
        ):
            return None
        all_upstream_hashes.update(hashes)
        normalized_rows.append(
            {
                "public_key_set_hash": strict_canonical_hash(hashes),
                "window_id": window_id,
            }
        )
    common = source_rows[0]
    source_role_hashes = {
        common.get("replay_registry_public_key_sha256"),
        common.get("occurrence_auditor_public_key_sha256"),
    }
    if (
        len(source_role_hashes) != 2
        or not all(_exact_hash(value) for value in source_role_hashes)
        or public_key_hash in all_upstream_hashes
        or public_key_hash in source_role_hashes
    ):
        return None
    role_ids = {
        configuration["persistence_provider_id"],
        configuration["persistence_adapter_id"],
        configuration["persistence_provider_key_id"],
        common.get("replay_registry_id"),
        common.get("replay_registry_key_id"),
        common.get("occurrence_auditor_id"),
        common.get("occurrence_auditor_key_id"),
    }
    if None in role_ids or len(role_ids) != 7:
        return None
    max_write = configuration.get("max_write_receipt_delay_seconds")
    max_reopen = configuration.get("max_reopen_receipt_delay_seconds")
    min_reopen = configuration.get("min_reopen_separation_seconds")
    if (
        not _strict_delay(max_write)
        or not _strict_delay(max_reopen)
        or not _strict_delay(min_reopen)
        or min_reopen > max_reopen
    ):
        return None
    declared = _utc(configuration.get("declared_at_utc"))
    checkpoint_issued = _utc(common.get("checkpoint_issued_at_utc"))
    if declared is None or checkpoint_issued is None or declared > checkpoint_issued:
        return None
    return public_key_hash, normalized_rows, len(all_upstream_hashes)


_CONTRACT_MANIFEST = {
    "schema_version": REGISTRATION_SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "source_contract": {
        "schema_version": replay_binding_v1.PREREGISTRATION_SCHEMA_VERSION,
        "implementation_sha256": REPLAY_BINDING_V1_IMPLEMENTATION_SHA256,
        "exact_rebuild_required": True,
    },
    "future_receipt_contracts": {
        "asset_schema_version": CHECKPOINT_ASSET_SCHEMA_VERSION,
        "write_receipt_schema_version": WRITE_RECEIPT_SCHEMA_VERSION,
        "reopen_receipt_schema_version": REOPEN_RECEIPT_SCHEMA_VERSION,
        "asset_hash_domain": CHECKPOINT_ASSET_HASH_DOMAIN,
        "write_signature_domain": WRITE_SIGNATURE_DOMAIN,
        "reopen_signature_domain": REOPEN_SIGNATURE_DOMAIN,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "receipt_encoding": RECEIPT_ENCODING,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "record_cardinality_policy": RECORD_CARDINALITY_POLICY,
        "session_separation_policy": SESSION_SEPARATION_POLICY,
        "source_binding_policy": SOURCE_BINDING_POLICY,
        "io_mode": IO_MODE,
    },
    "external_persistence_provider_claimed": False,
    "write_receipt_observed": False,
    "reopen_receipt_observed": False,
    "durability_claimed": False,
    "authoritative_future_pin_claimed": False,
}
PERSISTENCE_CONTRACT_HASH = strict_canonical_hash(_CONTRACT_MANIFEST)


def build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1(
    source_preregistration: Any,
    lifecycle_binding_preregistration: Any,
    provider_binding_preregistration: Any,
    overlap_preregistration: Any,
    multi_window_preregistration: Any,
    persistence_configuration: Any,
) -> dict[str, Any] | None:
    """Seal a no-I/O persistence consumer registration for ADR0352."""
    if not _source_preregistration_exact(
        source_preregistration,
        lifecycle_binding_preregistration,
        provider_binding_preregistration,
        overlap_preregistration,
        multi_window_preregistration,
    ):
        return None
    evidence = _configuration_evidence(
        persistence_configuration,
        source_preregistration,
    )
    if evidence is None:
        return None
    public_key_hash, excluded_rows, excluded_key_count = evidence
    common = source_preregistration["expected_replay_bindings"][0]
    facts = {
        "checkpoint_asset_schema_preregistered": True,
        "external_persistence_provider_authority_verified": False,
        "external_receipt_only_mode_verified": True,
        "local_io_performed": False,
        "persistence_provider_key_role_separation_verified": True,
        "reopen_receipt_observed": False,
        "source_common_registry_view_bound": True,
        "source_preregistration_exactly_rebuilt": True,
        "write_receipt_observed": False,
    }
    body = {
        "asset_hash_domain": CHECKPOINT_ASSET_HASH_DOMAIN,
        "asset_schema_version": CHECKPOINT_ASSET_SCHEMA_VERSION,
        "authority": deepcopy(_AUTHORITY),
        "declared_at_utc": persistence_configuration["declared_at_utc"],
        "excluded_upstream_distinct_public_key_count": excluded_key_count,
        "excluded_upstream_public_key_set_hashes": excluded_rows,
        "facts": facts,
        "io_mode": IO_MODE,
        "max_reopen_receipt_delay_seconds": persistence_configuration[
            "max_reopen_receipt_delay_seconds"
        ],
        "max_write_receipt_delay_seconds": persistence_configuration[
            "max_write_receipt_delay_seconds"
        ],
        "min_reopen_separation_seconds": persistence_configuration[
            "min_reopen_separation_seconds"
        ],
        "permissions": dict(_PERMISSIONS),
        "persistence_adapter_id": persistence_configuration[
            "persistence_adapter_id"
        ],
        "persistence_adapter_implementation_hash": persistence_configuration[
            "persistence_adapter_implementation_hash"
        ],
        "persistence_contract_hash": PERSISTENCE_CONTRACT_HASH,
        "persistence_namespace": persistence_configuration[
            "persistence_namespace"
        ],
        "persistence_provider_id": persistence_configuration[
            "persistence_provider_id"
        ],
        "persistence_provider_key_id": persistence_configuration[
            "persistence_provider_key_id"
        ],
        "persistence_provider_key_role": PERSISTENCE_PROVIDER_KEY_ROLE,
        "persistence_provider_public_key_sha256": public_key_hash,
        "receipt_encoding": RECEIPT_ENCODING,
        "record_cardinality_policy": RECORD_CARDINALITY_POLICY,
        "registration_state": (
            "PERSISTENCE_CONSUMER_REGISTERED_RECEIPTS_UNOBSERVED"
        ),
        "reopen_receipt_schema_version": REOPEN_RECEIPT_SCHEMA_VERSION,
        "reopen_signature_domain": REOPEN_SIGNATURE_DOMAIN,
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "session_separation_policy": SESSION_SEPARATION_POLICY,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "source_binding_policy": SOURCE_BINDING_POLICY,
        "source_checkpoint_issued_at_utc": common[
            "checkpoint_issued_at_utc"
        ],
        "source_checkpoint_root_hash": common["checkpoint_root_hash"],
        "source_checkpoint_tree_size": common["checkpoint_tree_size"],
        "source_common_registry_view_hash": source_preregistration[
            "common_registry_view_hash"
        ],
        "source_occurrence_auditor_key_id": common[
            "occurrence_auditor_key_id"
        ],
        "source_occurrence_auditor_public_key_sha256": common[
            "occurrence_auditor_public_key_sha256"
        ],
        "source_preregistration_hash": source_preregistration[
            "preregistration_hash"
        ],
        "source_reference_time_utc": common["reference_time_utc"],
        "source_replay_registry_id": common["replay_registry_id"],
        "source_replay_registry_key_id": common["replay_registry_key_id"],
        "source_replay_registry_namespace": common[
            "replay_registry_namespace"
        ],
        "source_replay_registry_public_key_sha256": common[
            "replay_registry_public_key_sha256"
        ],
        "source_schema_version": replay_binding_v1.PREREGISTRATION_SCHEMA_VERSION,
        "source_static_fingerprint": replay_binding_v1.STATIC_FINGERPRINT,
        "source_study_identity_hash": source_preregistration[
            "study_identity_hash"
        ],
        "source_window_count": source_preregistration[
            "expected_window_count"
        ],
        "source_window_order_hash": source_preregistration[
            "window_order_hash"
        ],
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_UNMOUNTED",
        "write_receipt_schema_version": WRITE_RECEIPT_SCHEMA_VERSION,
        "write_signature_domain": WRITE_SIGNATURE_DOMAIN,
    }
    return seal_strict_canonical_document(body, "registration_hash")


def verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1(
    document: Any,
    source_preregistration: Any,
    lifecycle_binding_preregistration: Any,
    provider_binding_preregistration: Any,
    overlap_preregistration: Any,
    multi_window_preregistration: Any,
    persistence_configuration: Any,
    *,
    expected_registration_hash: Any,
) -> bool:
    if (
        type(document) is not dict
        or not _exact_hash(expected_registration_hash)
        or document.get("registration_hash") != expected_registration_hash
    ):
        return False
    try:
        rebuilt = build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1(
            source_preregistration,
            lifecycle_binding_preregistration,
            provider_binding_preregistration,
            overlap_preregistration,
            multi_window_preregistration,
            persistence_configuration,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        type(rebuilt) is dict
        and strict_json_contract_equal(document, rebuilt)
        and compare_digest(document["registration_hash"], rebuilt["registration_hash"])
    )


__all__ = [
    "CHECKPOINT_ASSET_HASH_DOMAIN",
    "CHECKPOINT_ASSET_SCHEMA_VERSION",
    "IO_MODE",
    "PERSISTENCE_CONTRACT_HASH",
    "PERSISTENCE_PROVIDER_KEY_ROLE",
    "RECEIPT_ENCODING",
    "RECORD_CARDINALITY_POLICY",
    "REGISTRATION_SCHEMA_VERSION",
    "REOPEN_RECEIPT_SCHEMA_VERSION",
    "REOPEN_SIGNATURE_DOMAIN",
    "REPLAY_BINDING_V1_IMPLEMENTATION_SHA256",
    "SESSION_SEPARATION_POLICY",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_MESSAGE_FORMAT",
    "SOURCE_BINDING_POLICY",
    "STATIC_FINGERPRINT",
    "WRITE_RECEIPT_SCHEMA_VERSION",
    "WRITE_SIGNATURE_DOMAIN",
    "build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1",
    "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1",
]
