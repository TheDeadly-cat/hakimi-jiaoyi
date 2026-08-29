from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from exchange_terminal.application import (
    witness_ownership_state_provider_identity_source_adapter_preregistration_v1 as preregistration,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class WitnessOwnershipProviderIdentitySourceAdapterPreregistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.kwargs = {
            "target_stream_id": "witness-provider-key-revocations",
            "provider_preregistration_hash": _hash("provider-preregistration"),
            "active_key_state_hash": _hash("active-key-state"),
            "revocation_quorum_evidence_hash": _hash("revocation-quorum"),
            "identity_source_adapter_id": "external-identity-source-adapter-01",
            "identity_source_adapter_static_fingerprint": (
                "synthetic-external-identity-source-adapter-v1"
            ),
            "identity_source_adapter_implementation_sha256": _hash(
                "adapter-implementation"
            ),
            "identity_registry_id": "identity-registry-01",
            "identity_registry_snapshot_id": "identity-snapshot-0001",
            "identity_registry_snapshot_sha256": _hash(
                "identity-registry-snapshot"
            ),
            "identity_registry_trust_root_sha256": _hash(
                "identity-registry-trust-root"
            ),
            "provider_subject_id_hash": _hash("provider-subject-id"),
            "provider_identity_document_sha256": _hash(
                "provider-identity-document"
            ),
            "revocation_authority_source_id": "revocation-authority-source-01",
            "revocation_authority_source_snapshot_id": "revocation-source-0001",
            "revocation_authority_source_snapshot_sha256": _hash(
                "revocation-source-snapshot"
            ),
            "revocation_authority_source_trust_root_sha256": _hash(
                "revocation-source-trust-root"
            ),
            "observation_receipt_protocol_version": (
                "witness-provider-identity-source-observation-receipt-v1"
            ),
        }

    def _build(self, **overrides):
        kwargs = dict(self.kwargs)
        kwargs.update(overrides)
        return preregistration.build_witness_ownership_provider_identity_source_adapter_preregistration_v1(
            **kwargs
        )

    def test_build_is_deterministic_and_content_addressed(self) -> None:
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertRegex(first["adapter_preregistration_hash"], r"^[0-9a-f]{64}$")

    def test_target_contract_freezes_upstream_schema_and_implementation_hashes(self) -> None:
        target = self._build()["target_contract"]
        self.assertEqual(
            target["provider_preregistration_implementation_sha256"],
            preregistration.PROVIDER_PREREGISTRATION_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            target["key_continuity_implementation_sha256"],
            preregistration.KEY_CONTINUITY_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            target["revocation_source_implementation_sha256"],
            preregistration.REVOCATION_SOURCE_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            target["publication_port_implementation_sha256"],
            preregistration.PUBLICATION_PORT_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            target["publication_consumer_implementation_sha256"],
            preregistration.PUBLICATION_CONSUMER_IMPLEMENTATION_SHA256,
        )

    def test_governance_anchor_hashes_are_exactly_bound(self) -> None:
        anchors = self._build()["governance_anchor_hashes"]
        self.assertEqual(
            anchors,
            {
                "provider_preregistration_hash": self.kwargs[
                    "provider_preregistration_hash"
                ],
                "active_key_state_hash": self.kwargs["active_key_state_hash"],
                "revocation_quorum_evidence_hash": self.kwargs[
                    "revocation_quorum_evidence_hash"
                ],
            },
        )

    def test_required_evidence_is_fixed_and_unobserved(self) -> None:
        requirements = self._build()["required_evidence"]
        self.assertEqual(len(requirements), 9)
        self.assertTrue(
            all(item["evidence_status"] == "UNOBSERVED" for item in requirements)
        )
        self.assertTrue(
            all(
                item["required_before_identity_or_source_verification"] is True
                for item in requirements
            )
        )

    def test_requirement_builder_returns_a_fresh_value(self) -> None:
        first = preregistration.expected_witness_ownership_provider_identity_source_evidence_requirements_v1()
        first[0]["evidence_status"] = "FORGED"
        second = preregistration.expected_witness_ownership_provider_identity_source_evidence_requirements_v1()
        self.assertEqual(second[0]["evidence_status"], "UNOBSERVED")

    def test_authority_is_permanently_locked(self) -> None:
        authority = self._build()["authority"]
        self.assertEqual(authority["permission_state"], "RESEARCH_ONLY")
        self.assertTrue(all(value is False for key, value in authority.items() if key != "permission_state"))

    def test_external_sources_are_declared_but_unobserved(self) -> None:
        document = self._build()
        self.assertEqual(
            document["registration_state"],
            preregistration.REGISTRATION_STATE,
        )
        self.assertFalse(document["identity_source_adapter"]["runtime_observed"])
        self.assertFalse(document["identity_registry_source"]["snapshot_observed"])
        self.assertFalse(document["revocation_authority_source"]["snapshot_observed"])

    def test_observation_receipt_algorithm_and_encoding_are_fixed(self) -> None:
        receipt = self._build()["observation_receipt_contract"]
        self.assertEqual(receipt["signature_algorithm"], "ED25519")
        self.assertEqual(receipt["receipt_encoding"], "RFC8785_JCS_UTF8")
        self.assertFalse(receipt["signed_receipt_observed"])
        self.assertFalse(receipt["signed_receipt_verified"])

    def test_exact_verifier_accepts_exact_rebuild(self) -> None:
        document = self._build()
        self.assertTrue(
            preregistration.verify_witness_ownership_provider_identity_source_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_verifier_rejects_adapter_implementation_tamper(self) -> None:
        document = deepcopy(self._build())
        document["identity_source_adapter"]["adapter_implementation_sha256"] = _hash(
            "forged-adapter"
        )
        self.assertFalse(
            preregistration.verify_witness_ownership_provider_identity_source_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_verifier_rejects_authority_escalation(self) -> None:
        document = deepcopy(self._build())
        document["authority"]["permission"] = True
        self.assertFalse(
            preregistration.verify_witness_ownership_provider_identity_source_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_verifier_rejects_extra_fields(self) -> None:
        document = deepcopy(self._build())
        document["identity_registry_source"]["display_name"] = "unbound"
        self.assertFalse(
            preregistration.verify_witness_ownership_provider_identity_source_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_verifier_rejects_requirement_reordering(self) -> None:
        document = deepcopy(self._build())
        document["required_evidence"].reverse()
        self.assertFalse(
            preregistration.verify_witness_ownership_provider_identity_source_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_uppercase_hash_is_rejected(self) -> None:
        self.assertEqual(
            self._build(
                identity_registry_snapshot_sha256=self.kwargs[
                    "identity_registry_snapshot_sha256"
                ].upper()
            ),
            {},
        )

    def test_short_hash_is_rejected(self) -> None:
        self.assertEqual(self._build(provider_subject_id_hash="0" * 63), {})

    def test_reused_semantic_hash_is_rejected(self) -> None:
        self.assertEqual(
            self._build(
                active_key_state_hash=self.kwargs["provider_preregistration_hash"]
            ),
            {},
        )

    def test_identity_registry_and_revocation_source_must_be_separate(self) -> None:
        self.assertEqual(
            self._build(
                revocation_authority_source_id=self.kwargs["identity_registry_id"]
            ),
            {},
        )

    def test_source_snapshot_identifiers_must_be_separate(self) -> None:
        self.assertEqual(
            self._build(
                revocation_authority_source_snapshot_id=self.kwargs[
                    "identity_registry_snapshot_id"
                ]
            ),
            {},
        )

    def test_non_ascii_identifier_is_rejected(self) -> None:
        self.assertEqual(self._build(identity_registry_id="registry-\u6d4b\u8bd5"), {})

    def test_whitespace_bearing_identifier_is_rejected(self) -> None:
        self.assertEqual(self._build(identity_registry_id=" identity-registry-01"), {})

    def test_stream_binding_changes_registration_hash(self) -> None:
        first = self._build()
        second = self._build(target_stream_id="witness-provider-key-revocations-alt")
        self.assertNotEqual(
            first["adapter_preregistration_hash"],
            second["adapter_preregistration_hash"],
        )

    def test_serialized_record_contains_no_raw_subject_or_key_material(self) -> None:
        serialized = json.dumps(self._build(), sort_keys=True)
        self.assertNotIn("provider@example.test", serialized)
        self.assertNotIn("BEGIN PUBLIC KEY", serialized)
        self.assertNotIn("signature_base64", serialized)
        self.assertNotIn("storage_path", serialized)


if __name__ == "__main__":
    unittest.main()
