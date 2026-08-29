from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from hashlib import sha256
import unittest

from exchange_terminal.interfaces.registry_organization_identity import (
    RegistryOrganizationIdentityEvidenceKindV1,
    expected_signer_role_v1,
)
from exchange_terminal.interfaces.registry_signer_source_trust import (
    SOURCE_TRUST_SOURCE_PORT_VERSION,
    RegistrySignerSourceTrustRecordV1,
    RegistrySignerSourceTrustSourceV1,
    expected_source_trust_authority_role_v1,
)


def _digest(value: str) -> str:
    return sha256(value.encode("ascii")).hexdigest()


class _SyntheticSourceTrustSource:
    source_adapter_id = "synthetic.source-trust.adapter"
    protocol_version = SOURCE_TRUST_SOURCE_PORT_VERSION

    def fetch_source_trust_records(self, registry_id: str):
        return ()


class RegistrySignerSourceTrustInterfaceV1Tests(unittest.TestCase):
    def _record_args(
        self,
        kind: RegistryOrganizationIdentityEvidenceKindV1,
    ) -> dict:
        slug = kind.value.lower()
        return {
            "evidence_kind": kind,
            "signer_role": expected_signer_role_v1(kind),
            "signer_public_key_spki_sha256": _digest(f"{slug}:signer"),
            "subject_registry_id": "synthetic.identity.registry",
            "subject_public_key_spki_sha256": _digest("subject-key"),
            "authority_registry_id": f"synthetic.{slug}.authority",
            "authority_role": expected_source_trust_authority_role_v1(kind),
            "authority_public_key_spki_sha256": _digest(f"{slug}:authority"),
            "authority_statement_sha256": _digest(f"{slug}:statement"),
            "trust_anchor_id": f"synthetic.{slug}.anchor",
            "trust_anchor_sha256": _digest(f"{slug}:anchor"),
            "source_adapter_id": f"synthetic.{slug}.adapter",
            "source_adapter_implementation_sha256": _digest(f"{slug}:adapter"),
            "policy_id": f"synthetic.{slug}.policy",
            "policy_version": "v1.0",
            "revocation_source_id": f"synthetic.{slug}.revocation",
            "revocation_snapshot_sha256": _digest(f"{slug}:revocation"),
            "issued_at_ms": 1_000,
            "expires_at_ms": 2_000,
        }

    def test_all_six_roles_build_immutable_source_trust_records(self) -> None:
        records = [
            RegistrySignerSourceTrustRecordV1(**self._record_args(kind))
            for kind in RegistryOrganizationIdentityEvidenceKindV1
        ]
        self.assertEqual(len(records), 6)
        self.assertEqual(len({record.signer_role for record in records}), 6)
        self.assertEqual(len({record.authority_role for record in records}), 6)
        with self.assertRaises(FrozenInstanceError):
            records[0].authority_role = "drift"  # type: ignore[misc]

    def test_role_schema_algorithm_hash_and_time_aliases_are_rejected(self) -> None:
        kind = RegistryOrganizationIdentityEvidenceKindV1.DOMAIN_CONTROL_ATTESTATION
        base = self._record_args(kind)
        for patch in (
            {"signer_role": "organization_registry_authority"},
            {"authority_role": "domain_control_signer_source_authority-v2"},
            {"schema_version": "registry-signer-source-trust-record-v1.0"},
            {"signature_algorithm": "Ed25519"},
            {"authority_statement_sha256": "0" * 63},
            {"issued_at_ms": True},
            {"expires_at_ms": 1_000},
        ):
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    RegistrySignerSourceTrustRecordV1(**(base | patch))

    def test_self_attestation_namespace_collisions_are_rejected(self) -> None:
        kind = RegistryOrganizationIdentityEvidenceKindV1.KEY_GOVERNANCE_EVALUATION
        base = self._record_args(kind)
        for field_name, collision_field in (
            ("authority_registry_id", "subject_registry_id"),
            ("trust_anchor_id", "authority_registry_id"),
            ("source_adapter_id", "subject_registry_id"),
            ("revocation_source_id", "source_adapter_id"),
        ):
            with self.subTest(field=field_name):
                patch = {field_name: base[collision_field]}
                with self.assertRaises(ValueError):
                    RegistrySignerSourceTrustRecordV1(**(base | patch))

    def test_subject_signer_and_authority_key_collisions_are_rejected(self) -> None:
        kind = RegistryOrganizationIdentityEvidenceKindV1.REVOCATION_STATUS_RECEIPT
        base = self._record_args(kind)
        for field_name, collision_field in (
            (
                "signer_public_key_spki_sha256",
                "subject_public_key_spki_sha256",
            ),
            (
                "authority_public_key_spki_sha256",
                "subject_public_key_spki_sha256",
            ),
            (
                "authority_public_key_spki_sha256",
                "signer_public_key_spki_sha256",
            ),
        ):
            with self.subTest(field=field_name, collision=collision_field):
                patch = {field_name: base[collision_field]}
                with self.assertRaises(ValueError):
                    RegistrySignerSourceTrustRecordV1(**(base | patch))

    def test_record_contract_has_no_caller_supplied_authority_boolean(self) -> None:
        field_names = {field.name for field in fields(RegistrySignerSourceTrustRecordV1)}
        for forbidden in ("trusted", "verified", "allowed", "authorized"):
            self.assertFalse(any(forbidden in name for name in field_names))

    def test_structural_port_match_does_not_prove_source_trust(self) -> None:
        source = _SyntheticSourceTrustSource()
        self.assertIsInstance(source, RegistrySignerSourceTrustSourceV1)
        self.assertEqual(
            source.fetch_source_trust_records("synthetic.identity.registry"),
            (),
        )
        self.assertFalse(hasattr(source, "external_source_trust_verified"))
        self.assertFalse(hasattr(source, "signer_role_identity_verified"))


if __name__ == "__main__":
    unittest.main()
