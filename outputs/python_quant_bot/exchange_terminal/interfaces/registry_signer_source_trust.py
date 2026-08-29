"""Compatibility shim for the application-owned signer source-trust port."""

from __future__ import annotations

from exchange_terminal.application.ports.registry_signer_source_trust_v1 import (
    SIGNATURE_ALGORITHM,
    SOURCE_TRUST_RECORD_SCHEMA_VERSION,
    SOURCE_TRUST_SOURCE_PORT_VERSION,
    RegistryOrganizationIdentityEvidenceKindV1,
    RegistrySignerSourceTrustRecordV1,
    RegistrySignerSourceTrustSourceV1,
    expected_signer_role_v1,
    expected_source_trust_authority_role_v1,
)


COMPATIBILITY_SHIM_SCHEMA_VERSION = (
    "registry-signer-source-trust-interface-compatibility-shim-v1"
)
CANONICAL_PORT_MODULE = (
    "exchange_terminal.application.ports.registry_signer_source_trust_v1"
)
CANONICAL_PORT_IMPLEMENTATION_SHA256 = (
    "04e288bc11db85e21a775602d54a453d514474b9bf82133716ec4e63f72775ff"
)

__all__ = (
    "CANONICAL_PORT_IMPLEMENTATION_SHA256",
    "CANONICAL_PORT_MODULE",
    "COMPATIBILITY_SHIM_SCHEMA_VERSION",
    "SIGNATURE_ALGORITHM",
    "SOURCE_TRUST_RECORD_SCHEMA_VERSION",
    "SOURCE_TRUST_SOURCE_PORT_VERSION",
    "RegistryOrganizationIdentityEvidenceKindV1",
    "RegistrySignerSourceTrustRecordV1",
    "RegistrySignerSourceTrustSourceV1",
    "expected_signer_role_v1",
    "expected_source_trust_authority_role_v1",
)