"""Preregister an unmounted external identity/source adapter boundary.

The record binds existing witness-ownership governance artifacts to declared
external identity-registry and revocation-authority sources.  It performs no
external observation and grants no publication or trading authority.
"""

from __future__ import annotations

import re
from typing import Any

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_publication_consumer_v1 as publication,
)
from exchange_terminal.application import (
    witness_ownership_state_provider_key_continuity_v1 as key_continuity,
)
from exchange_terminal.application import (
    witness_ownership_state_provider_key_revocation_source_v1 as revocation_source,
)
from exchange_terminal.application import (
    witness_ownership_state_provider_preregistration_v1 as provider_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "witness-ownership-provider-identity-source-adapter-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-provider-identity-source-adapter-"
    "preregistration-v1-lock-1"
)
CONSUMER_STATUS = "UNMOUNTED_IDENTITY_SOURCE_ADAPTER_CANDIDATE"
REGISTRATION_STATE = "DECLARED_EXTERNAL_SOURCES_UNOBSERVED"
PERMISSION_STATE = "RESEARCH_ONLY"

IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM = "ED25519"
IDENTITY_ATTESTATION_RECEIPT_ENCODING = "RFC8785_JCS_UTF8"

PROVIDER_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "081cf9dfae66918f6e5e1cf4fd8f9d7e7c438aff01e1b465726a86d8aee47b2d"
)
KEY_CONTINUITY_IMPLEMENTATION_SHA256 = (
    "06404d081bdde55f619b78089024f13886d00224ff896f955fe8418fc9edde16"
)
REVOCATION_SOURCE_IMPLEMENTATION_SHA256 = (
    "44638fe992d1e204c6cf39d11f8bee81b5bb4bef36c6adb7116d3e9e14300a08"
)
PUBLICATION_PORT_IMPLEMENTATION_SHA256 = (
    "433404433d04a7c5733084a253eaf1394433618e13eaf51fff2914c86e9617dd"
)
PUBLICATION_CONSUMER_IMPLEMENTATION_SHA256 = (
    "b94371a927983588aecd678ba40ee5ca4c2d5e9678ea8f5f6c4420808dd77d13"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")

_EVIDENCE_REQUIREMENTS = (
    ("ADAPTER_IMPLEMENTATION_REPRODUCIBILITY", True),
    ("IDENTITY_REGISTRY_SNAPSHOT_AUTHENTICITY", True),
    ("PROVIDER_SUBJECT_UNIQUENESS", True),
    ("PROVIDER_IDENTITY_DOCUMENT_BINDING", True),
    ("ACTIVE_KEY_MEMBERSHIP_AND_CURRENTNESS", True),
    ("REVOCATION_SOURCE_SNAPSHOT_AUTHENTICITY", True),
    ("REVOCATION_AUTHORITY_SOURCE_INDEPENDENCE", True),
    ("SOURCE_FRESHNESS_AND_REPLAY_RESISTANCE", True),
    ("SIGNED_OBSERVATION_RECEIPT", True),
)


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _is_token(value: Any) -> bool:
    return type(value) is str and _TOKEN_RE.fullmatch(value) is not None


def expected_witness_ownership_provider_identity_source_evidence_requirements_v1(
) -> list[dict[str, Any]]:
    return [
        {
            "requirement_id": requirement_id,
            "required_before_identity_or_source_verification": required,
            "evidence_status": "UNOBSERVED",
        }
        for requirement_id, required in _EVIDENCE_REQUIREMENTS
    ]


def build_witness_ownership_provider_identity_source_adapter_preregistration_v1(
    *,
    target_stream_id: Any,
    provider_preregistration_hash: Any,
    active_key_state_hash: Any,
    revocation_quorum_evidence_hash: Any,
    identity_source_adapter_id: Any,
    identity_source_adapter_static_fingerprint: Any,
    identity_source_adapter_implementation_sha256: Any,
    identity_registry_id: Any,
    identity_registry_snapshot_id: Any,
    identity_registry_snapshot_sha256: Any,
    identity_registry_trust_root_sha256: Any,
    provider_subject_id_hash: Any,
    provider_identity_document_sha256: Any,
    revocation_authority_source_id: Any,
    revocation_authority_source_snapshot_id: Any,
    revocation_authority_source_snapshot_sha256: Any,
    revocation_authority_source_trust_root_sha256: Any,
    observation_receipt_protocol_version: Any,
) -> dict[str, Any]:
    tokens = (
        target_stream_id,
        identity_source_adapter_id,
        identity_source_adapter_static_fingerprint,
        identity_registry_id,
        identity_registry_snapshot_id,
        revocation_authority_source_id,
        revocation_authority_source_snapshot_id,
        observation_receipt_protocol_version,
    )
    hashes = (
        provider_preregistration_hash,
        active_key_state_hash,
        revocation_quorum_evidence_hash,
        identity_source_adapter_implementation_sha256,
        identity_registry_snapshot_sha256,
        identity_registry_trust_root_sha256,
        provider_subject_id_hash,
        provider_identity_document_sha256,
        revocation_authority_source_snapshot_sha256,
        revocation_authority_source_trust_root_sha256,
    )
    if not all(_is_token(value) for value in tokens):
        return {}
    if not all(_is_sha256(value) for value in hashes):
        return {}
    if len(set(hashes)) != len(hashes):
        return {}
    if len(
        {
            identity_source_adapter_id,
            identity_registry_id,
            revocation_authority_source_id,
        }
    ) != 3:
        return {}
    if identity_registry_snapshot_id == revocation_authority_source_snapshot_id:
        return {}

    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registration_state": REGISTRATION_STATE,
        "target_contract": {
            "target_stream_id": target_stream_id,
            "provider_preregistration_schema_version": (
                provider_preregistration.PREREGISTRATION_SCHEMA_VERSION
            ),
            "provider_preregistration_implementation_sha256": (
                PROVIDER_PREREGISTRATION_IMPLEMENTATION_SHA256
            ),
            "key_continuity_state_schema_version": (
                key_continuity.KEY_STATE_SCHEMA_VERSION
            ),
            "key_continuity_implementation_sha256": (
                KEY_CONTINUITY_IMPLEMENTATION_SHA256
            ),
            "revocation_quorum_evidence_schema_version": (
                revocation_source.QUORUM_EVIDENCE_SCHEMA_VERSION
            ),
            "revocation_source_implementation_sha256": (
                REVOCATION_SOURCE_IMPLEMENTATION_SHA256
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
            "provider_preregistration_hash": provider_preregistration_hash,
            "active_key_state_hash": active_key_state_hash,
            "revocation_quorum_evidence_hash": revocation_quorum_evidence_hash,
        },
        "identity_source_adapter": {
            "adapter_id": identity_source_adapter_id,
            "adapter_static_fingerprint": identity_source_adapter_static_fingerprint,
            "adapter_implementation_sha256": (
                identity_source_adapter_implementation_sha256
            ),
            "runtime_observed": False,
            "implementation_reproduced": False,
        },
        "identity_registry_source": {
            "registry_id": identity_registry_id,
            "registry_snapshot_id": identity_registry_snapshot_id,
            "registry_snapshot_sha256": identity_registry_snapshot_sha256,
            "registry_trust_root_sha256": identity_registry_trust_root_sha256,
            "provider_subject_id_hash": provider_subject_id_hash,
            "provider_identity_document_sha256": provider_identity_document_sha256,
            "snapshot_observed": False,
            "snapshot_authenticity_verified": False,
            "provider_subject_uniqueness_verified": False,
            "provider_identity_binding_verified": False,
        },
        "revocation_authority_source": {
            "source_id": revocation_authority_source_id,
            "source_snapshot_id": revocation_authority_source_snapshot_id,
            "source_snapshot_sha256": (
                revocation_authority_source_snapshot_sha256
            ),
            "source_trust_root_sha256": (
                revocation_authority_source_trust_root_sha256
            ),
            "snapshot_observed": False,
            "snapshot_authenticity_verified": False,
            "source_independence_verified": False,
            "freshness_and_replay_resistance_verified": False,
        },
        "observation_receipt_contract": {
            "protocol_version": observation_receipt_protocol_version,
            "signature_algorithm": IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM,
            "receipt_encoding": IDENTITY_ATTESTATION_RECEIPT_ENCODING,
            "signed_receipt_observed": False,
            "signed_receipt_verified": False,
        },
        "required_evidence": (
            expected_witness_ownership_provider_identity_source_evidence_requirements_v1()
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
    return seal_strict_canonical_document(document, "adapter_preregistration_hash")


def verify_witness_ownership_provider_identity_source_adapter_preregistration_v1(
    document: Any,
    **build_kwargs: Any,
) -> bool:
    expected = (
        build_witness_ownership_provider_identity_source_adapter_preregistration_v1(
            **build_kwargs
        )
    )
    return bool(expected) and strict_json_contract_equal(document, expected)


__all__ = [
    "CONSUMER_STATUS",
    "IDENTITY_ATTESTATION_RECEIPT_ENCODING",
    "IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM",
    "KEY_CONTINUITY_IMPLEMENTATION_SHA256",
    "PERMISSION_STATE",
    "PROVIDER_PREREGISTRATION_IMPLEMENTATION_SHA256",
    "PUBLICATION_CONSUMER_IMPLEMENTATION_SHA256",
    "PUBLICATION_PORT_IMPLEMENTATION_SHA256",
    "REGISTRATION_STATE",
    "REVOCATION_SOURCE_IMPLEMENTATION_SHA256",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_witness_ownership_provider_identity_source_adapter_preregistration_v1",
    "expected_witness_ownership_provider_identity_source_evidence_requirements_v1",
    "verify_witness_ownership_provider_identity_source_adapter_preregistration_v1",
]
