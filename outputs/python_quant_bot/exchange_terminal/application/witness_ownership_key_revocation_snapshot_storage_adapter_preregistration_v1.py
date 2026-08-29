"""Preregister storage semantics for an unmounted revocation snapshot adapter.

This module defines only a strict, backend-neutral registration record.  It
does not select a path, open storage, instantiate an adapter, or grant current,
paper, live, or publication authority.
"""

from __future__ import annotations

import re
from typing import Any

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_publication_consumer_v1 as publication,
)
from exchange_terminal.application import (
    witness_ownership_state_provider_identity_source_adapter_preregistration_v1 as identity_source,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "witness-ownership-key-revocation-snapshot-storage-adapter-"
    "preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-key-revocation-snapshot-storage-adapter-"
    "preregistration-v1-lock-1"
)
CONSUMER_STATUS = "UNMOUNTED_STORAGE_ADAPTER_CANDIDATE"
REGISTRATION_STATE = "DECLARED_STORAGE_DOMAIN_EVIDENCE_UNOBSERVED"
PERMISSION_STATE = "RESEARCH_ONLY"

CONTENT_PUBLICATION_PROTOCOL = "CONTENT_ADDRESSED_NO_CLOBBER_V1"
HEAD_UPDATE_PROTOCOL = "CONDITIONAL_COMPARE_AND_SWAP_V1"
CURRENT_READ_PROTOCOL = "POST_SUCCESS_EXACT_CURRENT_HEAD_READ_V1"
CONFLICT_POLICY = "NO_AUTOMATIC_RETRY_OR_REISSUE_V1"

STORAGE_BACKEND_LOCAL_FILESYSTEM = "LOCAL_FILESYSTEM"
STORAGE_BACKEND_TRANSACTIONAL_DATABASE = "TRANSACTIONAL_DATABASE"
STORAGE_BACKEND_CONDITIONAL_OBJECT_STORE = "CONDITIONAL_OBJECT_STORE"
ALLOWED_STORAGE_BACKEND_KINDS = frozenset(
    {
        STORAGE_BACKEND_LOCAL_FILESYSTEM,
        STORAGE_BACKEND_TRANSACTIONAL_DATABASE,
        STORAGE_BACKEND_CONDITIONAL_OBJECT_STORE,
    }
)

IDENTITY_SOURCE_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "d087684a6a7e64bd2acf6e213144083ad30e5b88bf091f9f56edb942465f4374"
)
PUBLICATION_PORT_IMPLEMENTATION_SHA256 = (
    "433404433d04a7c5733084a253eaf1394433618e13eaf51fff2914c86e9617dd"
)
PUBLICATION_CONSUMER_IMPLEMENTATION_SHA256 = (
    "b94371a927983588aecd678ba40ee5ca4c2d5e9678ea8f5f6c4420808dd77d13"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")

_COMMON_EVIDENCE_REQUIREMENTS = (
    "ADAPTER_IMPLEMENTATION_REPRODUCIBILITY",
    "STORAGE_DOMAIN_OWNERSHIP",
    "CONTENT_AND_HEAD_NAMESPACE_CONFINEMENT",
    "CONTENT_NO_CLOBBER_COLLISION_BEHAVIOR",
    "STRICT_BOUNDED_ARTIFACT_READ",
    "CAS_SINGLE_WINNER_CONCURRENCY",
    "CAS_CONFLICT_WITHOUT_RETRY_OR_REISSUE",
    "CRASH_BEFORE_CONTENT_PUBLICATION",
    "CRASH_AFTER_CONTENT_BEFORE_HEAD",
    "CRASH_AFTER_HEAD_BEFORE_RECEIPT",
    "RESTART_EXACT_CURRENT_HEAD_READ",
    "ROLLBACK_AND_EQUIVOCATION_DETECTION",
    "INDEPENDENT_DURABILITY_AND_READ_OBSERVER",
)

_BACKEND_EVIDENCE_REQUIREMENT = {
    STORAGE_BACKEND_LOCAL_FILESYSTEM: (
        "FILESYSTEM_REPARSE_CONFINEMENT_AND_SAME_VOLUME_ATOMICITY"
    ),
    STORAGE_BACKEND_TRANSACTIONAL_DATABASE: (
        "DATABASE_TRANSACTION_ISOLATION_AND_UNIQUE_CONSTRAINT"
    ),
    STORAGE_BACKEND_CONDITIONAL_OBJECT_STORE: (
        "OBJECT_STORE_CONDITIONAL_GENERATION_AND_READ_CONSISTENCY"
    ),
}


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _is_token(value: Any) -> bool:
    return type(value) is str and _TOKEN_RE.fullmatch(value) is not None


def expected_witness_ownership_snapshot_storage_evidence_requirements_v1(
    storage_backend_kind: Any,
) -> list[dict[str, Any]]:
    if storage_backend_kind not in ALLOWED_STORAGE_BACKEND_KINDS:
        return []
    requirements = [
        {
            "requirement_id": requirement_id,
            "requirement_scope": "COMMON",
            "required_before_persistence_verification": True,
            "evidence_status": "UNOBSERVED",
        }
        for requirement_id in _COMMON_EVIDENCE_REQUIREMENTS
    ]
    requirements.append(
        {
            "requirement_id": _BACKEND_EVIDENCE_REQUIREMENT[
                storage_backend_kind
            ],
            "requirement_scope": storage_backend_kind,
            "required_before_persistence_verification": True,
            "evidence_status": "UNOBSERVED",
        }
    )
    return requirements


def build_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
    *,
    identity_source_adapter_preregistration_hash: Any,
    target_stream_id: Any,
    storage_adapter_id: Any,
    storage_adapter_static_fingerprint: Any,
    storage_adapter_implementation_sha256: Any,
    storage_backend_kind: Any,
    storage_domain_id_hash: Any,
    content_namespace_id_hash: Any,
    head_namespace_id_hash: Any,
    durability_protocol_version: Any,
    crash_recovery_protocol_version: Any,
    concurrency_control_protocol_version: Any,
) -> dict[str, Any]:
    tokens = (
        target_stream_id,
        storage_adapter_id,
        storage_adapter_static_fingerprint,
        durability_protocol_version,
        crash_recovery_protocol_version,
        concurrency_control_protocol_version,
    )
    hashes = (
        identity_source_adapter_preregistration_hash,
        storage_adapter_implementation_sha256,
        storage_domain_id_hash,
        content_namespace_id_hash,
        head_namespace_id_hash,
    )
    if not all(_is_token(value) for value in tokens):
        return {}
    if storage_backend_kind not in ALLOWED_STORAGE_BACKEND_KINDS:
        return {}
    if not all(_is_sha256(value) for value in hashes):
        return {}
    if len(set(hashes)) != len(hashes):
        return {}
    if len(
        {
            durability_protocol_version,
            crash_recovery_protocol_version,
            concurrency_control_protocol_version,
        }
    ) != 3:
        return {}

    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registration_state": REGISTRATION_STATE,
        "target_contract": {
            "target_stream_id": target_stream_id,
            "identity_source_preregistration_schema_version": (
                identity_source.SCHEMA_VERSION
            ),
            "identity_source_preregistration_implementation_sha256": (
                IDENTITY_SOURCE_PREREGISTRATION_IMPLEMENTATION_SHA256
            ),
            "publication_consumer_contract_version": publication.CONTRACT_VERSION,
            "publication_port_implementation_sha256": (
                PUBLICATION_PORT_IMPLEMENTATION_SHA256
            ),
            "publication_consumer_implementation_sha256": (
                PUBLICATION_CONSUMER_IMPLEMENTATION_SHA256
            ),
        },
        "governance_anchor_hashes": {
            "identity_source_adapter_preregistration_hash": (
                identity_source_adapter_preregistration_hash
            ),
        },
        "storage_adapter": {
            "adapter_id": storage_adapter_id,
            "adapter_static_fingerprint": storage_adapter_static_fingerprint,
            "adapter_implementation_sha256": storage_adapter_implementation_sha256,
            "runtime_observed": False,
            "implementation_reproduced": False,
        },
        "storage_domain": {
            "storage_backend_kind": storage_backend_kind,
            "storage_domain_id_hash": storage_domain_id_hash,
            "content_namespace_id_hash": content_namespace_id_hash,
            "head_namespace_id_hash": head_namespace_id_hash,
            "content_publication_protocol": CONTENT_PUBLICATION_PROTOCOL,
            "head_update_protocol": HEAD_UPDATE_PROTOCOL,
            "current_read_protocol": CURRENT_READ_PROTOCOL,
            "conflict_policy": CONFLICT_POLICY,
            "durability_protocol_version": durability_protocol_version,
            "crash_recovery_protocol_version": crash_recovery_protocol_version,
            "concurrency_control_protocol_version": (
                concurrency_control_protocol_version
            ),
            "storage_domain_observed": False,
            "namespace_confinement_verified": False,
            "content_immutability_verified": False,
            "atomic_head_compare_and_swap_verified": False,
            "durability_verified": False,
            "restart_read_verified": False,
            "rollback_and_equivocation_detection_verified": False,
        },
        "required_evidence": (
            expected_witness_ownership_snapshot_storage_evidence_requirements_v1(
                storage_backend_kind
            )
        ),
        "authority": {
            "permission_state": PERMISSION_STATE,
            "permission": False,
            "paper_authorized": False,
            "live_authorized": False,
            "provider_identity_verified": False,
            "external_source_truth_verified": False,
            "external_persistence_independently_verified": False,
            "snapshot_publication_authorized": False,
            "current_chain_activated": False,
        },
    }
    return seal_strict_canonical_document(
        document,
        "storage_adapter_preregistration_hash",
    )


def verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
    document: Any,
    **build_kwargs: Any,
) -> bool:
    expected = build_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
        **build_kwargs
    )
    return bool(expected) and strict_json_contract_equal(document, expected)


__all__ = [
    "ALLOWED_STORAGE_BACKEND_KINDS",
    "CONFLICT_POLICY",
    "CONSUMER_STATUS",
    "CONTENT_PUBLICATION_PROTOCOL",
    "CURRENT_READ_PROTOCOL",
    "HEAD_UPDATE_PROTOCOL",
    "IDENTITY_SOURCE_PREREGISTRATION_IMPLEMENTATION_SHA256",
    "PERMISSION_STATE",
    "PUBLICATION_CONSUMER_IMPLEMENTATION_SHA256",
    "PUBLICATION_PORT_IMPLEMENTATION_SHA256",
    "REGISTRATION_STATE",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STORAGE_BACKEND_CONDITIONAL_OBJECT_STORE",
    "STORAGE_BACKEND_LOCAL_FILESYSTEM",
    "STORAGE_BACKEND_TRANSACTIONAL_DATABASE",
    "build_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1",
    "expected_witness_ownership_snapshot_storage_evidence_requirements_v1",
    "verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1",
]
