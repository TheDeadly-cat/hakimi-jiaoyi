from __future__ import annotations

from dataclasses import FrozenInstanceError
from hashlib import sha256
import unittest

from exchange_terminal.interfaces.registry_organization_identity import (
    RegistryOrganizationIdentityEvidenceKindV1,
    RegistryOrganizationIdentityEvidenceReferenceV1,
    RegistryOrganizationIdentityEvidenceSourceV1,
    expected_evidence_schema_v1,
    expected_signer_role_v1,
)


class _SyntheticStructuralSource:
    source_id = "synthetic.identity.source"

    def fetch_references(self, registry_id: str):
        return ()


class RegistryOrganizationIdentityInterfaceV1Tests(unittest.TestCase):
    def _reference(
        self, kind: RegistryOrganizationIdentityEvidenceKindV1
    ) -> RegistryOrganizationIdentityEvidenceReferenceV1:
        return RegistryOrganizationIdentityEvidenceReferenceV1(
            kind=kind,
            evidence_schema_version=expected_evidence_schema_v1(kind),
            artifact_sha256=sha256(kind.value.encode("ascii")).hexdigest(),
            signer_role=expected_signer_role_v1(kind),
            signer_public_key_spki_sha256=sha256(
                f"{kind.value}:signer-key".encode("ascii")
            ).hexdigest(),
            subject_registry_id="synthetic.identity.registry",
            subject_public_key_spki_sha256=sha256(b"synthetic-key").hexdigest(),
            issued_at_ms=1_000,
            expires_at_ms=2_000,
        )

    def test_all_six_evidence_kinds_build_immutable_references(self) -> None:
        references = [self._reference(kind) for kind in RegistryOrganizationIdentityEvidenceKindV1]
        self.assertEqual(len(references), 6)
        self.assertEqual(len({reference.signer_role for reference in references}), 6)
        with self.assertRaises(FrozenInstanceError):
            references[0].artifact_sha256 = "0" * 64  # type: ignore[misc]

    def test_schema_and_signer_role_aliases_are_rejected(self) -> None:
        kind = RegistryOrganizationIdentityEvidenceKindV1.DOMAIN_CONTROL_ATTESTATION
        base = {
            "kind": kind,
            "evidence_schema_version": expected_evidence_schema_v1(kind),
            "artifact_sha256": sha256(b"artifact").hexdigest(),
            "signer_role": expected_signer_role_v1(kind),
            "signer_public_key_spki_sha256": sha256(b"signer-key").hexdigest(),
            "subject_registry_id": "synthetic.identity.registry",
            "subject_public_key_spki_sha256": sha256(b"key").hexdigest(),
            "issued_at_ms": 1,
            "expires_at_ms": 2,
        }
        for patch in (
            {"evidence_schema_version": f"{base['evidence_schema_version']}.0"},
            {"signer_role": "organization_registry_authority"},
            {"signature_algorithm": "Ed25519"},
        ):
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    RegistryOrganizationIdentityEvidenceReferenceV1(**(base | patch))

    def test_invalid_hash_and_time_ranges_are_rejected(self) -> None:
        kind = RegistryOrganizationIdentityEvidenceKindV1.REVOCATION_STATUS_RECEIPT
        base = {
            "kind": kind,
            "evidence_schema_version": expected_evidence_schema_v1(kind),
            "artifact_sha256": sha256(b"artifact").hexdigest(),
            "signer_role": expected_signer_role_v1(kind),
            "signer_public_key_spki_sha256": sha256(b"signer-key").hexdigest(),
            "subject_registry_id": "synthetic.identity.registry",
            "subject_public_key_spki_sha256": sha256(b"key").hexdigest(),
            "issued_at_ms": 1,
            "expires_at_ms": 2,
        }
        for patch in (
            {"artifact_sha256": "0" * 63},
            {"issued_at_ms": True},
            {"expires_at_ms": 1},
        ):
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    RegistryOrganizationIdentityEvidenceReferenceV1(**(base | patch))

    def test_structural_source_match_is_not_identity_evidence(self) -> None:
        source = _SyntheticStructuralSource()
        self.assertIsInstance(source, RegistryOrganizationIdentityEvidenceSourceV1)
        self.assertEqual(source.fetch_references("synthetic.identity.registry"), ())
        self.assertFalse(hasattr(source, "organization_identity_verified"))
        self.assertFalse(hasattr(source, "external_trust_verified"))


if __name__ == "__main__":
    unittest.main()
