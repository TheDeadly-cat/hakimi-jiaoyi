from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol, runtime_checkable


EVIDENCE_REFERENCE_SCHEMA_VERSION = (
    "registry-organization-identity-evidence-reference-v1"
)
SIGNATURE_ALGORITHM = "ed25519"

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")


class RegistryOrganizationIdentityEvidenceKindV1(str, Enum):
    ORGANIZATION_REGISTRY_ATTESTATION = "ORGANIZATION_REGISTRY_ATTESTATION"
    DOMAIN_CONTROL_ATTESTATION = "DOMAIN_CONTROL_ATTESTATION"
    KEY_GOVERNANCE_EVALUATION = "KEY_GOVERNANCE_EVALUATION"
    AUDITOR_PROVENANCE_EVALUATION = "AUDITOR_PROVENANCE_EVALUATION"
    ARTIFACT_TRANSPARENCY_EVALUATION = "ARTIFACT_TRANSPARENCY_EVALUATION"
    REVOCATION_STATUS_RECEIPT = "REVOCATION_STATUS_RECEIPT"


_EXPECTED_SCHEMAS = {
    RegistryOrganizationIdentityEvidenceKindV1.ORGANIZATION_REGISTRY_ATTESTATION: (
        "registry-organization-authority-attestation-v1"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.DOMAIN_CONTROL_ATTESTATION: (
        "registry-domain-control-attestation-v1"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.KEY_GOVERNANCE_EVALUATION: (
        "provider-identity-witness-conformance-key-governance-evaluation-v1"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.AUDITOR_PROVENANCE_EVALUATION: (
        "provider-identity-auditor-provenance-suite-reproducibility-evaluation-v1"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.ARTIFACT_TRANSPARENCY_EVALUATION: (
        "provider-identity-artifact-transparency-availability-evaluation-v1"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.REVOCATION_STATUS_RECEIPT: (
        "registry-revocation-status-receipt-v1"
    ),
}
_EXPECTED_SIGNER_ROLES = {
    RegistryOrganizationIdentityEvidenceKindV1.ORGANIZATION_REGISTRY_ATTESTATION: (
        "organization_registry_authority"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.DOMAIN_CONTROL_ATTESTATION: (
        "domain_control_auditor"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.KEY_GOVERNANCE_EVALUATION: (
        "key_governance_auditor"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.AUDITOR_PROVENANCE_EVALUATION: (
        "provenance_registry_authority"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.ARTIFACT_TRANSPARENCY_EVALUATION: (
        "transparency_log_authority"
    ),
    RegistryOrganizationIdentityEvidenceKindV1.REVOCATION_STATUS_RECEIPT: (
        "revocation_authority"
    ),
}


def expected_evidence_schema_v1(
    kind: RegistryOrganizationIdentityEvidenceKindV1,
) -> str:
    if not isinstance(kind, RegistryOrganizationIdentityEvidenceKindV1):
        raise ValueError("evidence kind must be an exact v1 enum value")
    return _EXPECTED_SCHEMAS[kind]


def expected_signer_role_v1(
    kind: RegistryOrganizationIdentityEvidenceKindV1,
) -> str:
    if not isinstance(kind, RegistryOrganizationIdentityEvidenceKindV1):
        raise ValueError("evidence kind must be an exact v1 enum value")
    return _EXPECTED_SIGNER_ROLES[kind]


def _require_hash(name: str, value: str) -> None:
    if not isinstance(value, str) or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase sha256 hex digest")


def _require_identifier(name: str, value: str) -> None:
    if not isinstance(value, str) or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded lowercase identifier")


@dataclass(frozen=True, slots=True)
class RegistryOrganizationIdentityEvidenceReferenceV1:
    kind: RegistryOrganizationIdentityEvidenceKindV1
    evidence_schema_version: str
    artifact_sha256: str
    signer_role: str
    signer_public_key_spki_sha256: str
    subject_registry_id: str
    subject_public_key_spki_sha256: str
    issued_at_ms: int
    expires_at_ms: int
    signature_algorithm: str = SIGNATURE_ALGORITHM
    schema_version: str = EVIDENCE_REFERENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.kind, RegistryOrganizationIdentityEvidenceKindV1):
            raise ValueError("evidence kind must be an exact v1 enum value")
        if self.evidence_schema_version != expected_evidence_schema_v1(self.kind):
            raise ValueError("evidence schema does not match its kind")
        if self.signer_role != expected_signer_role_v1(self.kind):
            raise ValueError("signer role does not match its evidence kind")
        _require_hash("artifact_sha256", self.artifact_sha256)
        _require_hash(
            "signer_public_key_spki_sha256",
            self.signer_public_key_spki_sha256,
        )
        _require_hash(
            "subject_public_key_spki_sha256",
            self.subject_public_key_spki_sha256,
        )
        _require_identifier("subject_registry_id", self.subject_registry_id)
        if self.signature_algorithm != SIGNATURE_ALGORITHM:
            raise ValueError("evidence signature algorithm must be ed25519")
        if self.schema_version != EVIDENCE_REFERENCE_SCHEMA_VERSION:
            raise ValueError("evidence reference schema aliases are forbidden")
        for name in ("issued_at_ms", "expires_at_ms"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.expires_at_ms <= self.issued_at_ms:
            raise ValueError("evidence reference expiry must follow issuance")


@runtime_checkable
class RegistryOrganizationIdentityEvidenceSourceV1(Protocol):
    @property
    def source_id(self) -> str:
        ...

    def fetch_references(
        self, registry_id: str
    ) -> tuple[RegistryOrganizationIdentityEvidenceReferenceV1, ...]:
        ...
