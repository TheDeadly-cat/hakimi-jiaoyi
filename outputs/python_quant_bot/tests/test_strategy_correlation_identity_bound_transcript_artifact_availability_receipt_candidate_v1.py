from __future__ import annotations

import base64
import copy
import hashlib
import json
from types import SimpleNamespace
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from exchange_terminal.application import (
    strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1
    as availability,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_identity_bound_signed_replay_cursor_provider_transcript_content_bridge_candidate_v1 as upstream_fixture_module


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _spki(private_key: Ed25519PrivateKey) -> tuple[str, str]:
    spki = private_key.public_key().public_bytes(
        Encoding.DER,
        PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(spki).decode("ascii"), hashlib.sha256(spki).hexdigest()


def _sign(private_key: Ed25519PrivateKey, claim_hash: str) -> str:
    return base64.b64encode(private_key.sign(bytes.fromhex(claim_hash))).decode(
        "ascii"
    )


def _nested_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _nested_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _nested_keys(item)


class StrategyCorrelationIdentityBoundTranscriptArtifactAvailabilityReceiptCandidateV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        Upstream = upstream_fixture_module.StrategyCorrelationIdentityBoundSignedReplayCursorProviderTranscriptContentBridgeCandidateV1Tests
        Upstream.setUpClass()
        cls.upstream_fixture = Upstream
        cls.upstream_document = Upstream.result
        cls.upstream_context = {
            "identity_bound_conformance_bridge_document": Upstream.identity_conformance_document,
            "identity_bound_conformance_bridge_verification_context": Upstream.identity_conformance_context,
            "transcript_content_evidence_document": Upstream.content_evidence,
            "transcript_content_verification_context": Upstream.content_context,
            "expected_identity_bound_conformance_bridge_hash": Upstream.identity_conformance_document[
                "identity_bound_signed_provider_conformance_bridge_hash"
            ],
            "expected_content_verification_hash": Upstream.content_evidence[
                "content_verification_hash"
            ],
            "expected_transcript_binding_hash": Upstream.binding_document[
                "transcript_binding_hash"
            ],
            "expected_conformance_quorum_evidence_hash": Upstream.quorum_evidence[
                "quorum_evidence_hash"
            ],
            "expected_signed_receipt_evidence_hash": Upstream.receipt_evidence[
                "verification_evidence_hash"
            ],
            "expected_conformance_plan_hash": Upstream.binding_fixture.plan_document[
                "conformance_plan_hash"
            ],
            "expected_provider_preregistration_hash": Upstream.binding_fixture.provider_preregistration_document[
                "preregistration_hash"
            ],
        }
        cls.upstream_hash = cls.upstream_document[
            "identity_bound_provider_transcript_content_bridge_hash"
        ]

        cls.publisher_key = Ed25519PrivateKey.generate()
        cls.retriever_keys = [Ed25519PrivateKey.generate() for _ in range(2)]
        cls.publisher_spki, publisher_key_hash = _spki(cls.publisher_key)
        retriever_spki = [_spki(key) for key in cls.retriever_keys]
        cls.retriever_spki = [item[0] for item in retriever_spki]
        cls.publisher_registration = {
            "publisher_id": "synthetic-transcript-publisher-1",
            "organization_claim_hash": _hash("synthetic-publisher-organization"),
            "trust_domain": "synthetic-publisher-domain",
            "public_key_spki_sha256": publisher_key_hash,
        }
        cls.retriever_registrations = [
            {
                "retriever_id": f"synthetic-transcript-retriever-{index + 1}",
                "organization_claim_hash": _hash(
                    f"synthetic-retriever-organization-{index + 1}"
                ),
                "trust_domain": f"synthetic-retriever-domain-{index + 1}",
                "public_key_spki_sha256": retriever_spki[index][1],
            }
            for index in range(2)
        ]
        cls.locator_rows = [
            {
                "observer_id": bundle["observer_id"],
                "locator_commitment_hash": _hash(
                    f"synthetic-immutable-locator-{index + 1}"
                ),
                "immutable_version_hash": _hash(
                    f"synthetic-immutable-version-{index + 1}"
                ),
            }
            for index, bundle in enumerate(Upstream.content_bundles)
        ]
        cls.registration = availability.build_strategy_correlation_transcript_artifact_availability_registration_v1(
            cls.upstream_document,
            cls.upstream_context,
            expected_identity_bound_transcript_content_bridge_hash=cls.upstream_hash,
            artifact_locator_rows=cls.locator_rows,
            publisher_registration=cls.publisher_registration,
            retriever_registrations=cls.retriever_registrations,
        )
        cls.publication_claim = availability.build_strategy_correlation_transcript_artifact_publication_claim_v1(
            cls.registration,
            expected_availability_registration_hash=cls.registration[
                "availability_registration_hash"
            ],
            publication_nonce_hash=_hash("synthetic-publication-nonce"),
        )
        cls.publication_signature = _sign(
            cls.publisher_key,
            cls.publication_claim["publication_claim_hash"],
        )
        cls.signed_publication_receipt = availability.build_signed_strategy_correlation_transcript_artifact_publication_receipt_v1(
            cls.publication_claim,
            cls.registration,
            public_key_spki_base64=cls.publisher_spki,
            signature_base64=cls.publication_signature,
            expected_publication_claim_hash=cls.publication_claim[
                "publication_claim_hash"
            ],
            expected_availability_registration_hash=cls.registration[
                "availability_registration_hash"
            ],
        )
        cls.signed_retrieval_receipts = []
        for artifact_index, artifact in enumerate(cls.registration["artifacts"]):
            for retriever_index in range(2):
                cls.signed_retrieval_receipts.append(
                    cls._build_retrieval_receipt(
                        artifact_index,
                        retriever_index,
                        challenge_label=(
                            f"synthetic-retrieval-challenge-{artifact_index + 1}-"
                            f"{retriever_index + 1}"
                        ),
                    )
                )
        cls.receipt_set_hash = availability.build_strategy_correlation_transcript_artifact_retrieval_receipt_set_hash_v1(
            cls.signed_retrieval_receipts
        )
        cls.result = cls._evaluate_static()

    @classmethod
    def _build_retrieval_receipt(
        cls,
        artifact_index: int,
        retriever_index: int,
        *,
        challenge_label: str,
    ):
        artifact = cls.registration["artifacts"][artifact_index]
        retriever = cls.retriever_registrations[retriever_index]
        claim = availability.build_strategy_correlation_transcript_artifact_retrieval_claim_v1(
            cls.registration,
            cls.signed_publication_receipt,
            retriever_id=retriever["retriever_id"],
            artifact_id=artifact["artifact_id"],
            challenge_nonce_hash=_hash(challenge_label),
            retrieved_content_bundle_hash=artifact["content_bundle_hash"],
            retrieved_total_payload_bytes=artifact["total_payload_bytes"],
            expected_availability_registration_hash=cls.registration[
                "availability_registration_hash"
            ],
            expected_signed_publication_receipt_hash=cls.signed_publication_receipt[
                "signed_publication_receipt_hash"
            ],
        )
        return availability.build_signed_strategy_correlation_transcript_artifact_retrieval_receipt_v1(
            claim,
            cls.registration,
            cls.signed_publication_receipt,
            public_key_spki_base64=cls.retriever_spki[retriever_index],
            signature_base64=_sign(
                cls.retriever_keys[retriever_index], claim["retrieval_claim_hash"]
            ),
            expected_retrieval_claim_hash=claim["retrieval_claim_hash"],
            expected_availability_registration_hash=cls.registration[
                "availability_registration_hash"
            ],
            expected_signed_publication_receipt_hash=cls.signed_publication_receipt[
                "signed_publication_receipt_hash"
            ],
        )

    @classmethod
    def _evaluate_static(cls, **overrides):
        arguments = {
            "identity_bound_transcript_content_bridge_document": cls.upstream_document,
            "identity_bound_transcript_content_bridge_verification_context": cls.upstream_context,
            "availability_registration_document": cls.registration,
            "signed_publication_receipt_document": cls.signed_publication_receipt,
            "signed_retrieval_receipt_documents": cls.signed_retrieval_receipts,
            "expected_identity_bound_transcript_content_bridge_hash": cls.upstream_hash,
            "expected_availability_registration_hash": cls.registration[
                "availability_registration_hash"
            ],
            "expected_signed_publication_receipt_hash": cls.signed_publication_receipt[
                "signed_publication_receipt_hash"
            ],
            "expected_retrieval_receipt_set_hash": cls.receipt_set_hash,
        }
        arguments.update(overrides)
        return availability.evaluate_strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1(
            **arguments
        )

    def test_exact_signed_claim_candidate_remains_blocked(self):
        self.assertIsNotNone(self.result)
        self.assertEqual(self.result["status"], availability.STATUS)
        self.assertEqual(self.result["decision"], availability.DECISION)
        self.assertEqual(self.result["permission_state"], "BLOCKED")
        self.assertEqual(self.result["consumer_status"], "UNMOUNTED_CANDIDATE")
        self.assertTrue(all(value is False for value in self.result["authority"].values()))

    def test_exact_verifier_reconstructs_evidence(self):
        self.assertTrue(
            availability.verify_strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1(
                self.result,
                self.upstream_document,
                self.upstream_context,
                self.registration,
                self.signed_publication_receipt,
                self.signed_retrieval_receipts,
                expected_availability_receipt_evidence_hash=self.result[
                    "availability_receipt_evidence_hash"
                ],
                expected_identity_bound_transcript_content_bridge_hash=self.upstream_hash,
                expected_availability_registration_hash=self.registration[
                    "availability_registration_hash"
                ],
                expected_signed_publication_receipt_hash=self.signed_publication_receipt[
                    "signed_publication_receipt_hash"
                ],
                expected_retrieval_receipt_set_hash=self.receipt_set_hash,
            )
        )

    def test_registration_verifier_reconstructs_exact_catalog(self):
        self.assertTrue(
            availability.verify_strategy_correlation_transcript_artifact_availability_registration_v1(
                self.registration,
                self.upstream_document,
                self.upstream_context,
                expected_availability_registration_hash=self.registration[
                    "availability_registration_hash"
                ],
                expected_identity_bound_transcript_content_bridge_hash=self.upstream_hash,
            )
        )

    def test_evaluation_is_deterministic(self):
        self.assertEqual(self._evaluate_static(), self.result)

    def test_missing_or_duplicate_retrieval_receipt_is_rejected(self):
        missing = self.signed_retrieval_receipts[:-1]
        duplicate = [
            *self.signed_retrieval_receipts[:-1],
            self.signed_retrieval_receipts[0],
        ]
        self.assertIsNone(
            self._evaluate_static(signed_retrieval_receipt_documents=missing)
        )
        self.assertIsNone(
            self._evaluate_static(signed_retrieval_receipt_documents=duplicate)
        )

    def test_wrong_publisher_signature_is_rejected(self):
        document = copy.deepcopy(self.signed_publication_receipt)
        document["signature_base64"] = _sign(
            self.retriever_keys[0], self.publication_claim["publication_claim_hash"]
        )
        document.pop("signed_publication_receipt_hash")
        document = seal_strict_canonical_document(
            document, "signed_publication_receipt_hash"
        )
        self.assertIsNone(
            self._evaluate_static(
                signed_publication_receipt_document=document,
                expected_signed_publication_receipt_hash=document[
                    "signed_publication_receipt_hash"
                ],
            )
        )

    def test_wrong_retriever_signature_is_rejected(self):
        receipts = copy.deepcopy(self.signed_retrieval_receipts)
        claim_hash = receipts[0]["retrieval_claim"]["retrieval_claim_hash"]
        receipts[0]["signature_base64"] = _sign(self.retriever_keys[1], claim_hash)
        receipts[0].pop("signed_retrieval_receipt_hash")
        receipts[0] = seal_strict_canonical_document(
            receipts[0], "signed_retrieval_receipt_hash"
        )
        set_hash = availability.build_strategy_correlation_transcript_artifact_retrieval_receipt_set_hash_v1(
            receipts
        )
        self.assertIsNone(
            self._evaluate_static(
                signed_retrieval_receipt_documents=receipts,
                expected_retrieval_receipt_set_hash=set_hash,
            )
        )

    def test_duplicate_challenge_nonce_is_rejected(self):
        receipts = list(self.signed_retrieval_receipts)
        receipts[1] = self._build_retrieval_receipt(
            0,
            1,
            challenge_label="synthetic-retrieval-challenge-1-1",
        )
        set_hash = availability.build_strategy_correlation_transcript_artifact_retrieval_receipt_set_hash_v1(
            receipts
        )
        self.assertIsNone(
            self._evaluate_static(
                signed_retrieval_receipt_documents=receipts,
                expected_retrieval_receipt_set_hash=set_hash,
            )
        )

    def test_provider_or_observer_key_collision_is_rejected(self):
        provider_hash = self.upstream_fixture.binding_fixture.provider_preregistration_document[
            "identity"
        ]["public_key_spki_sha256"]
        publisher = {
            **self.publisher_registration,
            "public_key_spki_sha256": provider_hash,
        }
        with self.assertRaises(ValueError):
            availability.build_strategy_correlation_transcript_artifact_availability_registration_v1(
                self.upstream_document,
                self.upstream_context,
                expected_identity_bound_transcript_content_bridge_hash=self.upstream_hash,
                artifact_locator_rows=self.locator_rows,
                publisher_registration=publisher,
                retriever_registrations=self.retriever_registrations,
            )

    def test_role_organization_or_trust_domain_collision_is_rejected(self):
        retrievers = copy.deepcopy(self.retriever_registrations)
        retrievers[1]["organization_claim_hash"] = retrievers[0][
            "organization_claim_hash"
        ]
        with self.assertRaises(ValueError):
            availability.build_strategy_correlation_transcript_artifact_availability_registration_v1(
                self.upstream_document,
                self.upstream_context,
                expected_identity_bound_transcript_content_bridge_hash=self.upstream_hash,
                artifact_locator_rows=self.locator_rows,
                publisher_registration=self.publisher_registration,
                retriever_registrations=retrievers,
            )

    def test_locator_commitment_drift_is_rejected(self):
        document = copy.deepcopy(self.registration)
        document["artifacts"][0]["locator_commitment_hash"] = "a" * 64
        document.pop("availability_registration_hash")
        document = seal_strict_canonical_document(
            document, "availability_registration_hash"
        )
        self.assertIsNone(
            self._evaluate_static(
                availability_registration_document=document,
                expected_availability_registration_hash=document[
                    "availability_registration_hash"
                ],
            )
        )

    def test_expected_hash_drift_is_rejected(self):
        for field in (
            "expected_identity_bound_transcript_content_bridge_hash",
            "expected_availability_registration_hash",
            "expected_signed_publication_receipt_hash",
            "expected_retrieval_receipt_set_hash",
        ):
            with self.subTest(field=field):
                self.assertIsNone(self._evaluate_static(**{field: "a" * 64}))

    def test_upstream_context_alias_is_rejected(self):
        context = dict(self.upstream_context)
        context["compatibility_alias"] = True
        self.assertIsNone(
            self._evaluate_static(
                identity_bound_transcript_content_bridge_verification_context=context
            )
        )

    def test_shape_compatible_alias_is_rejected(self):
        alias = SimpleNamespace(**self.registration)
        self.assertIsNone(
            self._evaluate_static(availability_registration_document=alias)
        )

    def test_local_signatures_never_promote_external_availability(self):
        facts = self.result["facts"]
        self.assertTrue(facts["publisher_signature_exactly_verified"])
        self.assertTrue(
            facts["dual_retriever_signatures_per_artifact_exactly_verified"]
        )
        self.assertFalse(facts["publisher_identity_verified"])
        self.assertFalse(facts["retriever_identities_verified"])
        self.assertFalse(facts["retriever_independence_verified"])
        self.assertFalse(facts["publisher_external_operation_verified"])
        self.assertFalse(facts["actual_network_retrieval_verified"])
        self.assertFalse(facts["public_artifact_availability_verified"])
        self.assertFalse(facts["external_persistence_verified"])

    def test_output_redacts_locators_keys_signatures_claims_and_artifacts(self):
        forbidden_keys = {
            "locator_commitment_hash",
            "immutable_version_hash",
            "public_key_spki_base64",
            "signature_base64",
            "publication_claim",
            "retrieval_claim",
            "artifacts",
            "content_bundle_documents",
            "case_payloads",
        }
        self.assertTrue(forbidden_keys.isdisjoint(set(_nested_keys(self.result))))
        serialized = json.dumps(self.result, sort_keys=True)
        self.assertNotIn(self.publisher_spki, serialized)
        self.assertNotIn(self.publication_signature, serialized)
        for receipt in self.signed_retrieval_receipts:
            self.assertNotIn(receipt["public_key_spki_base64"], serialized)
            self.assertNotIn(receipt["signature_base64"], serialized)


if __name__ == "__main__":
    unittest.main()
