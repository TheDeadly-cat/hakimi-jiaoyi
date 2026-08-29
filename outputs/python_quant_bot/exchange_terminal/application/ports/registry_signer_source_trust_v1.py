from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol, runtime_checkable

from exchange_terminal.application.ports.registry_organization_identity_v1 import (
    RegistryOrganizationIdentityEvidenceKindV1,
    expected_signer_role_v1,
)


SOURCE_TRUST_RECORD_SCHEMA_VERSION = "registry-signer-source-trust-record-v1"
SOURCE_TRUST_SOURCE_PORT_VERSION = "registry-signer-source-trust-source-port-v1"
SIGNATURE_ALGORITHM = "ed25519"

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_EXPECTED_AUTHORITY_ROLES = {
    RegistryOrganizationIdentityEvidenceKindV1.ORGANIZATION_REGISTRY_ATTESTATION: (
        "organization_registry_signer_source_authority"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.DOMAIN_CONTROL_ATTESTATION: (
        "domain_control_signer_source_authority"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.KEY_GOVERNANCE_EVALUATION: (
        "key_governance_signer_source_authority"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.AUDITOR_PROVENANCE_EVALUATION: (
        "auditor_provenance_signer_source_authority"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.ARTIFACT_TRANSPARENCY_EVALUATION: (
        "artifact_transparency_signer_source_authority"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.REVOCATION_STATUS_RECEIPT: (
        "revocation_signer_source_authority"
    ),
}


def expected_source_trust_authority_role_v1(
    kind: RegistryOrganizationIdentityEvidenceKindV1,
) -> str:
    if not isinstance(kind, RegistryOrganizationIdentityEvidenceKindV1):
        raise ValueError("evidence kind must be an exact v1 enum value")
    return _EXPECTED_AUTHORITY_ROLES[kind]


def _require_hash(name: str, value: str) -> None:
    if not isinstance(value, str) or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase sha256 hex digest")


def _require_identifier(name: str, value: str) -> None:
    if not isinstance(value, str) or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded lowercase identifier")


@dataclass(frozen=True, slots=True)
class RegistrySignerSourceTrustRecordV1:
    evidence_kind: RegistryOrganizationIdentityEvidenceKindV1
    signer_role: str
    signer_public_key_spki_sha256: str
    subject_registry_id: str
    subject_public_key_spki_sha256: str
    authority_registry_id: str
    authority_role: str
    authority_public_key_spki_sha256: str
    authority_statement_sha256: str
    trust_anchor_id: str
    trust_anchor_sha256: str
    source_adapter_id: str
    source_adapter_implementation_sha256: str
    policy_id: str
    policy_version: str
    revocation_source_id: str
    revocation_snapshot_sha256: str
    issued_at_ms: int
    expires_at_ms: int
    signature_algorithm: str = SIGNATURE_ALGORITHM
    schema_version: str = SOURCE_TRUST_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(
            self.evidence_kind,
            RegistryOrganizationIdentityEvidenceKindV1,
        ):
            raise ValueError("evidence kind must be an exact v1 enum value")
        if self.signer_role != expected_signer_role_v1(self.evidence_kind):
            raise ValueError("signer role does not match its evidence kind")
        if self.authority_role != expected_source_trust_authority_role_v1(
            self.evidence_kind
        ):
            raise ValueError("authority role does not match its evidence kind")

        for name in (
            "signer_public_key_spki_sha256",
            "subject_public_key_spki_sha256",
            "authority_public_key_spki_sha256",
            "authority_statement_sha256",
            "trust_anchor_sha256",
            "source_adapter_implementation_sha256",
            "revocation_snapshot_sha256",
        ):
            _require_hash(name, getattr(self, name))
        for name in (
            "subject_registry_id",
            "authority_registry_id",
            "authority_role",
            "trust_anchor_id",
            "source_adapter_id",
            "policy_id",
            "policy_version",
            "revocation_source_id",
        ):
            _require_identifier(name, getattr(self, name))

        namespace_ids = (
            self.subject_registry_id,
            self.authority_registry_id,
            self.trust_anchor_id,
            self.source_adapter_id,
            self.revocation_source_id,
        )
        if len(set(namespace_ids)) != len(namespace_ids):
            raise ValueError(
                "subject, authority, anchor, adapter, and revocation namespaces "
                "must be distinct"
            )
        key_hashes = (
            self.subject_public_key_spki_sha256,
            self.signer_public_key_spki_sha256,
            self.authority_public_key_spki_sha256,
        )
        if len(set(key_hashes)) != len(key_hashes):
            raise ValueError(
                "subject, evidence signer, and source authority keys must be distinct"
            )
        if self.signature_algorithm != SIGNATURE_ALGORITHM:
            raise ValueError("source trust signature algorithm must be ed25519")
        if self.schema_version != SOURCE_TRUST_RECORD_SCHEMA_VERSION:
            raise ValueError("source trust record schema aliases are forbidden")
        for name in ("issued_at_ms", "expires_at_ms"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.expires_at_ms <= self.issued_at_ms:
            raise ValueError("source trust record expiry must follow issuance")


@runtime_checkable
class RegistrySignerSourceTrustSourceV1(Protocol):
    @property
    def source_adapter_id(self) -> str:
        ...

    @property
    def protocol_version(self) -> str:
        ...

    def fetch_source_trust_records(
        self,
        registry_id: str,
    ) -> tuple[RegistrySignerSourceTrustRecordV1, ...]:
        ...
