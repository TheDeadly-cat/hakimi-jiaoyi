from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import unittest

from exchange_terminal.application import (
    anti_replay_registry_identity_preregistration_v1 as identity_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_evidence_bundle_evaluation_v1 as evaluation_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_intake_preregistration_v1 as intake_v1,
)
from exchange_terminal.interfaces.registry_organization_identity import (
    RegistryOrganizationIdentityEvidenceKindV1,
    RegistryOrganizationIdentityEvidenceReferenceV1,
    expected_evidence_schema_v1,
    expected_signer_role_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class RegistryOrganizationIdentityEvidenceBundleEvaluationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reference_time_ms = 10_000_000
        cls.kwargs = {
            "registry_id": "synthetic.bundle.registry",
            "operator_identity_claim": "synthetic-bundle-operator-claim",
            "public_key_spki_sha256": sha256(b"synthetic-bundle-subject-key").hexdigest(),
            "trust_domain": "synthetic.bundle.test",
            "adapter_protocol_version": identity_v1.ADAPTER_PROTOCOL_VERSION,
        }
        identity_kwargs = dict(cls.kwargs)
        identity_kwargs.pop("adapter_protocol_version")
        cls.identity = identity_v1.build_anti_replay_registry_identity_preregistration_v1(
            **identity_kwargs
        )
        cls.intake = intake_v1.build_anti_replay_registry_organization_identity_intake_preregistration_v1(
            cls.identity,
            **cls.kwargs,
        )
        cls.references = cls._references()

    @classmethod
    def _references(cls) -> tuple[RegistryOrganizationIdentityEvidenceReferenceV1, ...]:
        return tuple(
            RegistryOrganizationIdentityEvidenceReferenceV1(
                kind=kind,
                evidence_schema_version=expected_evidence_schema_v1(kind),
                artifact_sha256=sha256(f"{kind.value}:artifact".encode("ascii")).hexdigest(),
                signer_role=expected_signer_role_v1(kind),
                signer_public_key_spki_sha256=sha256(
                    f"{kind.value}:signer-key".encode("ascii")
                ).hexdigest(),
                subject_registry_id=cls.kwargs["registry_id"],
                subject_public_key_spki_sha256=cls.kwargs[
                    "public_key_spki_sha256"
                ],
                issued_at_ms=cls.reference_time_ms - 1_000,
                expires_at_ms=cls.reference_time_ms + 1_000,
            )
            for kind in RegistryOrganizationIdentityEvidenceKindV1
        )

    def _evaluate(
        self,
        references: tuple[RegistryOrganizationIdentityEvidenceReferenceV1, ...]
        | None = None,
        reference_time_ms: int | None = None,
    ) -> dict:
        return evaluation_v1.evaluate_anti_replay_registry_organization_identity_evidence_bundle_v1(
            self.intake,
            self.identity,
            references or self.references,
            self.reference_time_ms
            if reference_time_ms is None
            else reference_time_ms,
            **self.kwargs,
        )

    def _replace(self, index: int, **changes) -> tuple:
        values = list(self.references)
        original = values[index]
        fields = {
            name: getattr(original, name)
            for name in original.__dataclass_fields__
        }
        fields.update(changes)
        values[index] = RegistryOrganizationIdentityEvidenceReferenceV1(**fields)
        return tuple(values)

    def test_exact_synthetic_bundle_passes_local_checks_but_identity_stays_false(self) -> None:
        document = self._evaluate()
        self.assertEqual(document["status"], "BLOCKED")
        self.assertEqual(
            document["local_bundle_status"],
            evaluation_v1.LOCAL_PASS_STATUS,
        )
        self.assertTrue(document["facts"]["all_references_fresh"])
        self.assertTrue(document["facts"]["signer_public_keys_distinct"])
        self.assertFalse(document["facts"]["evidence_signatures_verified"])
        self.assertFalse(document["facts"]["external_source_trust_verified"])
        self.assertFalse(
            document["facts"]["registry_organization_identity_verified"]
        )

    def test_bundle_binds_six_unique_roles_keys_artifacts_and_subjects(self) -> None:
        document = self._evaluate()
        references = document["references"]
        self.assertEqual(len(references), 6)
        self.assertEqual(len({row["signer_role"] for row in references}), 6)
        self.assertEqual(
            len({row["signer_public_key_spki_sha256"] for row in references}), 6
        )
        self.assertEqual(len({row["artifact_sha256"] for row in references}), 6)
        self.assertTrue(
            all(row["subject_registry_id"] == self.kwargs["registry_id"] for row in references)
        )

    def test_duplicate_signer_key_blocks_local_bundle(self) -> None:
        references = self._replace(
            1,
            signer_public_key_spki_sha256=self.references[0].signer_public_key_spki_sha256,
        )
        document = self._evaluate(references)
        self.assertEqual(document["local_bundle_status"], "BLOCK")
        self.assertFalse(document["facts"]["signer_public_keys_distinct"])

    def test_duplicate_artifact_hash_blocks_local_bundle(self) -> None:
        references = self._replace(
            1,
            artifact_sha256=self.references[0].artifact_sha256,
        )
        document = self._evaluate(references)
        self.assertEqual(document["local_bundle_status"], "BLOCK")
        self.assertFalse(document["facts"]["artifact_hashes_distinct"])

    def test_subject_binding_substitution_blocks_local_bundle(self) -> None:
        references = self._replace(
            0,
            subject_registry_id="synthetic.substituted.registry",
        )
        document = self._evaluate(references)
        self.assertEqual(document["local_bundle_status"], "BLOCK")
        self.assertFalse(document["facts"]["subject_registry_id_bound"])

    def test_stale_and_future_references_block_local_bundle(self) -> None:
        stale = self._replace(
            0,
            issued_at_ms=1,
            expires_at_ms=2,
        )
        future = self._replace(
            0,
            issued_at_ms=self.reference_time_ms + 1,
            expires_at_ms=self.reference_time_ms + 2,
        )
        for references in (stale, future):
            with self.subTest(first=references[0].issued_at_ms):
                document = self._evaluate(references)
                self.assertEqual(document["local_bundle_status"], "BLOCK")
                self.assertFalse(document["facts"]["all_references_fresh"])

    def test_missing_or_duplicate_kind_is_rejected_before_evaluation(self) -> None:
        with self.assertRaises(ValueError):
            self._evaluate(self.references[:-1])
        duplicated = self.references[:-1] + (self.references[0],)
        with self.assertRaises(ValueError):
            self._evaluate(duplicated)

    def test_public_exact_verifier_separates_local_pass_and_identity(self) -> None:
        document = self._evaluate()
        exact = evaluation_v1.verify_anti_replay_registry_organization_identity_evidence_bundle_evaluation_v1(
            document,
            self.intake,
            self.identity,
            self.references,
            self.reference_time_ms,
            **self.kwargs,
        )
        self.assertEqual(exact["status"], "PASS")
        self.assertEqual(exact["evaluation_status"], "BLOCKED")
        self.assertEqual(exact["local_bundle_status"], evaluation_v1.LOCAL_PASS_STATUS)
        self.assertFalse(exact["evidence_signatures_verified"])
        self.assertFalse(exact["external_source_trust_verified"])
        self.assertFalse(exact["registry_organization_identity_verified"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])
        self.assertFalse(exact["writer_allowed"])

    def test_exact_local_freshness_failure_remains_verifier_block(self) -> None:
        stale = self._replace(0, issued_at_ms=1, expires_at_ms=2)
        document = self._evaluate(stale)
        exact = evaluation_v1.verify_anti_replay_registry_organization_identity_evidence_bundle_evaluation_v1(
            document,
            self.intake,
            self.identity,
            stale,
            self.reference_time_ms,
            **self.kwargs,
        )
        self.assertEqual(exact["status"], "BLOCK")
        self.assertTrue(exact["evaluation_document_exactly_rebuilt"])
        self.assertEqual(exact["evaluation_status"], "BLOCKED")
        self.assertEqual(exact["local_bundle_status"], "BLOCK")

    def test_tampered_evaluation_becomes_block_unknown(self) -> None:
        document = self._evaluate()
        body = deepcopy(document)
        body.pop("evaluation_hash")
        body["facts"]["evidence_signatures_verified"] = True
        tampered = seal_strict_canonical_document(body, "evaluation_hash")
        exact = evaluation_v1.verify_anti_replay_registry_organization_identity_evidence_bundle_evaluation_v1(
            tampered,
            self.intake,
            self.identity,
            self.references,
            self.reference_time_ms,
            **self.kwargs,
        )
        self.assertEqual(exact["status"], "BLOCK")
        self.assertFalse(exact["evaluation_document_exactly_rebuilt"])
        self.assertEqual(exact["evaluation_status"], "UNKNOWN")
        self.assertFalse(exact["registry_organization_identity_verified"])

    def test_evaluation_contains_no_payload_or_signature_material(self) -> None:
        serialized = repr(self._evaluate()).lower()
        self.assertNotIn("artifact_payload", serialized)
        self.assertNotIn("signature_material", serialized)
        self.assertNotIn("private_key", serialized)
        self.assertNotIn(self.kwargs["operator_identity_claim"], serialized)


if __name__ == "__main__":
    unittest.main()
