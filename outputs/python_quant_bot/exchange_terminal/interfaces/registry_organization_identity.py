"""Compatibility shim for the application-owned organization identity port."""

from __future__ import annotations

from exchange_terminal.application.ports.registry_organization_identity_v1 import (
    EVIDENCE_REFERENCE_SCHEMA_VERSION,
    SIGNATURE_ALGORITHM,
    RegistryOrganizationIdentityEvidenceKindV1,
    RegistryOrganizationIdentityEvidenceReferenceV1,
    RegistryOrganizationIdentityEvidenceSourceV1,
    expected_evidence_schema_v1,
    expected_signer_role_v1,
)


COMPATIBILITY_SHIM_SCHEMA_VERSION = (
    "registry-organization-identity-interface-compatibility-shim-v1"
)
CANONICAL_PORT_MODULE = (
    "exchange_terminal.application.ports.registry_organization_identity_v1"
)
CANONICAL_PORT_IMPLEMENTATION_SHA256 = (
    "df294b21bae439b96b86220a2be55ed5bf3305c9f32aaefb98c18e5d3b00b59f"
)

__all__ = (
    "CANONICAL_PORT_IMPLEMENTATION_SHA256",
    "CANONICAL_PORT_MODULE",
    "COMPATIBILITY_SHIM_SCHEMA_VERSION",
    "EVIDENCE_REFERENCE_SCHEMA_VERSION",
    "SIGNATURE_ALGORITHM",
    "RegistryOrganizationIdentityEvidenceKindV1",
    "RegistryOrganizationIdentityEvidenceReferenceV1",
    "RegistryOrganizationIdentityEvidenceSourceV1",
    "expected_evidence_schema_v1",
    "expected_signer_role_v1",
)