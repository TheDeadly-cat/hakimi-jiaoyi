from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1 as preregistration,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class WitnessOwnershipSnapshotStorageAdapterPreregistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.kwargs = {
            "identity_source_adapter_preregistration_hash": _hash(
                "identity-source-preregistration"
            ),
            "target_stream_id": "witness-provider-key-revocations",
            "storage_adapter_id": "snapshot-storage-adapter-01",
            "storage_adapter_static_fingerprint": (
                "synthetic-snapshot-storage-adapter-v1"
            ),
            "storage_adapter_implementation_sha256": _hash(
                "storage-adapter-implementation"
            ),
            "storage_backend_kind": preregistration.STORAGE_BACKEND_LOCAL_FILESYSTEM,
            "storage_domain_id_hash": _hash("storage-domain-id"),
            "content_namespace_id_hash": _hash("content-namespace-id"),
            "head_namespace_id_hash": _hash("head-namespace-id"),
            "durability_protocol_version": "synthetic-durability-protocol-v1",
            "crash_recovery_protocol_version": (
                "synthetic-crash-recovery-protocol-v1"
            ),
            "concurrency_control_protocol_version": (
                "synthetic-concurrency-control-protocol-v1"
            ),
        }

    def _build(self, **overrides):
        kwargs = dict(self.kwargs)
        kwargs.update(overrides)
        return preregistration.build_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
            **kwargs
        )

    def test_build_is_deterministic_and_content_addressed(self) -> None:
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertRegex(
            first["storage_adapter_preregistration_hash"],
            r"^[0-9a-f]{64}$",
        )

    def test_target_contract_binds_identity_source_and_publication_versions(self) -> None:
        target = self._build()["target_contract"]
        self.assertEqual(
            target["identity_source_preregistration_implementation_sha256"],
            preregistration.IDENTITY_SOURCE_PREREGISTRATION_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            target["publication_port_implementation_sha256"],
            preregistration.PUBLICATION_PORT_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            target["publication_consumer_implementation_sha256"],
            preregistration.PUBLICATION_CONSUMER_IMPLEMENTATION_SHA256,
        )

    def test_identity_source_registration_hash_is_exactly_bound(self) -> None:
        anchors = self._build()["governance_anchor_hashes"]
        self.assertEqual(
            anchors["identity_source_adapter_preregistration_hash"],
            self.kwargs["identity_source_adapter_preregistration_hash"],
        )

    def test_backend_neutral_publication_protocols_are_fixed(self) -> None:
        domain = self._build()["storage_domain"]
        self.assertEqual(
            domain["content_publication_protocol"],
            preregistration.CONTENT_PUBLICATION_PROTOCOL,
        )
        self.assertEqual(
            domain["head_update_protocol"],
            preregistration.HEAD_UPDATE_PROTOCOL,
        )
        self.assertEqual(
            domain["current_read_protocol"],
            preregistration.CURRENT_READ_PROTOCOL,
        )
        self.assertEqual(domain["conflict_policy"], preregistration.CONFLICT_POLICY)

    def test_common_and_backend_specific_evidence_stay_unobserved(self) -> None:
        requirements = self._build()["required_evidence"]
        self.assertEqual(len(requirements), 14)
        self.assertEqual(requirements[-1]["requirement_scope"], "LOCAL_FILESYSTEM")
        self.assertTrue(
            all(item["evidence_status"] == "UNOBSERVED" for item in requirements)
        )

    def test_each_backend_has_one_distinct_specific_requirement(self) -> None:
        tails = set()
        for backend in preregistration.ALLOWED_STORAGE_BACKEND_KINDS:
            requirements = preregistration.expected_witness_ownership_snapshot_storage_evidence_requirements_v1(
                backend
            )
            self.assertEqual(len(requirements), 14)
            self.assertEqual(requirements[-1]["requirement_scope"], backend)
            tails.add(requirements[-1]["requirement_id"])
        self.assertEqual(len(tails), 3)

    def test_requirement_builder_returns_fresh_values(self) -> None:
        first = preregistration.expected_witness_ownership_snapshot_storage_evidence_requirements_v1(
            preregistration.STORAGE_BACKEND_LOCAL_FILESYSTEM
        )
        first[0]["evidence_status"] = "FORGED"
        second = preregistration.expected_witness_ownership_snapshot_storage_evidence_requirements_v1(
            preregistration.STORAGE_BACKEND_LOCAL_FILESYSTEM
        )
        self.assertEqual(second[0]["evidence_status"], "UNOBSERVED")

    def test_storage_observation_and_authority_are_locked(self) -> None:
        document = self._build()
        domain = document["storage_domain"]
        self.assertTrue(
            all(
                value is False
                for key, value in domain.items()
                if key.endswith("_verified") or key == "storage_domain_observed"
            )
        )
        authority = document["authority"]
        self.assertEqual(authority["permission_state"], "RESEARCH_ONLY")
        self.assertTrue(
            all(value is False for key, value in authority.items() if key != "permission_state")
        )

    def test_exact_verifier_accepts_exact_rebuild(self) -> None:
        document = self._build()
        self.assertTrue(
            preregistration.verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_verifier_rejects_adapter_implementation_tamper(self) -> None:
        document = deepcopy(self._build())
        document["storage_adapter"]["adapter_implementation_sha256"] = _hash(
            "forged-adapter"
        )
        self.assertFalse(
            preregistration.verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_verifier_rejects_backend_tamper(self) -> None:
        document = deepcopy(self._build())
        document["storage_domain"]["storage_backend_kind"] = (
            preregistration.STORAGE_BACKEND_TRANSACTIONAL_DATABASE
        )
        self.assertFalse(
            preregistration.verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_verifier_rejects_authority_escalation(self) -> None:
        document = deepcopy(self._build())
        document["authority"]["snapshot_publication_authorized"] = True
        self.assertFalse(
            preregistration.verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_verifier_rejects_extra_fields(self) -> None:
        document = deepcopy(self._build())
        document["storage_domain"]["path"] = "forbidden"
        self.assertFalse(
            preregistration.verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_verifier_rejects_requirement_reordering(self) -> None:
        document = deepcopy(self._build())
        document["required_evidence"].reverse()
        self.assertFalse(
            preregistration.verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
                document,
                **self.kwargs,
            )
        )

    def test_unknown_backend_is_rejected(self) -> None:
        self.assertEqual(self._build(storage_backend_kind="UNBOUNDED_STORAGE"), {})
        self.assertEqual(
            preregistration.expected_witness_ownership_snapshot_storage_evidence_requirements_v1(
                "UNBOUNDED_STORAGE"
            ),
            [],
        )

    def test_uppercase_hash_is_rejected(self) -> None:
        self.assertEqual(
            self._build(
                storage_domain_id_hash=self.kwargs["storage_domain_id_hash"].upper()
            ),
            {},
        )

    def test_reused_semantic_hash_is_rejected(self) -> None:
        self.assertEqual(
            self._build(
                head_namespace_id_hash=self.kwargs["content_namespace_id_hash"]
            ),
            {},
        )

    def test_non_ascii_adapter_identifier_is_rejected(self) -> None:
        self.assertEqual(self._build(storage_adapter_id="adapter-\u6d4b\u8bd5"), {})

    def test_whitespace_bearing_protocol_is_rejected(self) -> None:
        self.assertEqual(
            self._build(durability_protocol_version=" durability-v1"),
            {},
        )

    def test_protocol_roles_must_not_reuse_one_identifier(self) -> None:
        self.assertEqual(
            self._build(
                crash_recovery_protocol_version=self.kwargs[
                    "durability_protocol_version"
                ]
            ),
            {},
        )

    def test_stream_binding_changes_registration_hash(self) -> None:
        first = self._build()
        second = self._build(target_stream_id="witness-provider-key-revocations-alt")
        self.assertNotEqual(
            first["storage_adapter_preregistration_hash"],
            second["storage_adapter_preregistration_hash"],
        )

    def test_serialized_record_excludes_paths_connections_and_credentials(self) -> None:
        serialized = json.dumps(self._build(), sort_keys=True)
        self.assertNotIn("storage_path", serialized)
        self.assertNotIn("connection_string", serialized)
        self.assertNotIn("bucket_name", serialized)
        self.assertNotIn("table_name", serialized)
        self.assertNotIn("credential", serialized)
        self.assertNotIn("secret", serialized)


if __name__ == "__main__":
    unittest.main()
