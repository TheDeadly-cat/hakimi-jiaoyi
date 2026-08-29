from __future__ import annotations

import base64
import copy
import json
import unittest

from exchange_terminal.application.strategy_correlation_identity_bound_transcript_artifact_availability_continuity_candidate_v1 import (
    build_signed_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1,
    build_strategy_correlation_transcript_artifact_availability_continuity_genesis_hash_v1,
    build_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1,
    build_strategy_correlation_transcript_artifact_availability_epoch_observation_v1,
    evaluate_strategy_correlation_identity_bound_transcript_artifact_availability_continuity_candidate_v1,
    verify_signed_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1,
    verify_strategy_correlation_identity_bound_transcript_artifact_availability_continuity_candidate_v1,
)
from exchange_terminal.application.strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1 import (
    build_strategy_correlation_transcript_artifact_retrieval_receipt_set_hash_v1,
    evaluate_strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from tests import (
    test_strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1 as availability_fixture_module,
)


class StrategyCorrelationIdentityBoundTranscriptArtifactAvailabilityContinuityCandidateV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = (
            availability_fixture_module.StrategyCorrelationIdentityBoundTranscriptArtifactAvailabilityReceiptCandidateV1Tests
        )
        fixture.setUpClass()
        cls.availability_fixture = fixture
        cls.registration = fixture.registration
        cls.publication = fixture.signed_publication_receipt
        cls.registration_hash = cls.registration["availability_registration_hash"]
        cls.publication_hash = cls.publication["signed_publication_receipt_hash"]

        cls.epoch_inputs = []
        cls.epoch_availability = []
        for ordinal in range(1, 4):
            receipts = []
            for artifact_index in range(2):
                for retriever_index in range(2):
                    receipts.append(
                        fixture._build_retrieval_receipt(
                            artifact_index,
                            retriever_index,
                            challenge_label=(
                                f"continuity-epoch-{ordinal}-artifact-{artifact_index}-retriever-{retriever_index}"
                            ),
                        )
                    )
            receipt_set_hash = build_strategy_correlation_transcript_artifact_retrieval_receipt_set_hash_v1(
                receipts
            )
            evidence = evaluate_strategy_correlation_identity_bound_transcript_artifact_availability_receipt_candidate_v1(
                fixture.upstream_document,
                fixture.upstream_context,
                cls.registration,
                cls.publication,
                receipts,
                expected_identity_bound_transcript_content_bridge_hash=fixture.upstream_hash,
                expected_availability_registration_hash=cls.registration_hash,
                expected_signed_publication_receipt_hash=cls.publication_hash,
                expected_retrieval_receipt_set_hash=receipt_set_hash,
            )
            if evidence is None:
                raise AssertionError("failed to build synthetic epoch availability evidence")
            context = {
                "identity_bound_transcript_content_bridge_document": fixture.upstream_document,
                "identity_bound_transcript_content_bridge_verification_context": fixture.upstream_context,
                "availability_registration_document": cls.registration,
                "signed_publication_receipt_document": cls.publication,
                "signed_retrieval_receipt_documents": receipts,
                "expected_identity_bound_transcript_content_bridge_hash": fixture.upstream_hash,
                "expected_availability_registration_hash": cls.registration_hash,
                "expected_signed_publication_receipt_hash": cls.publication_hash,
                "expected_retrieval_receipt_set_hash": receipt_set_hash,
            }
            challenge_rows = []
            for receipt in receipts:
                claim = receipt["retrieval_claim"]
                challenge_rows.append(
                    {
                        "artifact_id": claim["artifact"]["artifact_id"],
                        "retriever_id": claim["retriever"]["retriever_id"],
                        "challenge_nonce_hash": claim["source"]["challenge_nonce_hash"],
                    }
                )
            cls.epoch_inputs.append(
                {
                    "epoch_id": f"synthetic-epoch-{ordinal:04d}",
                    "ordinal": ordinal,
                    "slot_commitment_hash": strict_canonical_hash(
                        {
                            "domain": "synthetic-logical-slot-no-external-time",
                            "ordinal": ordinal,
                        }
                    ),
                    "challenge_rows": challenge_rows,
                }
            )
            cls.epoch_availability.append(
                {
                    "evidence": evidence,
                    "context": context,
                    "evidence_hash": evidence["availability_receipt_evidence_hash"],
                }
            )

        cls.schedule = build_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
            cls.registration,
            cls.publication,
            expected_availability_registration_hash=cls.registration_hash,
            expected_signed_publication_receipt_hash=cls.publication_hash,
            epoch_rows=cls.epoch_inputs,
        )
        cls.schedule_hash = cls.schedule["continuity_schedule_hash"]
        cls.schedule_signature = base64.b64encode(
            fixture.publisher_key.sign(bytes.fromhex(cls.schedule_hash))
        ).decode("ascii")
        cls.signed_schedule = build_signed_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
            cls.schedule,
            cls.registration,
            cls.publication,
            public_key_spki_base64=fixture.publisher_spki,
            signature_base64=cls.schedule_signature,
            expected_continuity_schedule_hash=cls.schedule_hash,
        )
        cls.signed_schedule_hash = cls.signed_schedule["signed_continuity_schedule_hash"]

        previous_hash = build_strategy_correlation_transcript_artifact_availability_continuity_genesis_hash_v1(
            cls.signed_schedule_hash
        )
        cls.observations = []
        cls.epoch_rows = []
        for epoch_input, availability in zip(cls.epoch_inputs, cls.epoch_availability):
            observation = build_strategy_correlation_transcript_artifact_availability_epoch_observation_v1(
                cls.signed_schedule,
                availability["evidence"],
                availability["context"],
                epoch_id=epoch_input["epoch_id"],
                previous_epoch_observation_hash=previous_hash,
                expected_signed_continuity_schedule_hash=cls.signed_schedule_hash,
                expected_continuity_schedule_hash=cls.schedule_hash,
                expected_availability_receipt_evidence_hash=availability["evidence_hash"],
            )
            cls.observations.append(observation)
            cls.epoch_rows.append(
                {
                    "epoch_observation_document": observation,
                    "availability_receipt_evidence_document": availability["evidence"],
                    "availability_receipt_verification_context": availability["context"],
                    "expected_availability_receipt_evidence_hash": availability["evidence_hash"],
                }
            )
            previous_hash = observation["epoch_observation_hash"]
        cls.final_observation_hash = previous_hash
        cls.result = evaluate_strategy_correlation_identity_bound_transcript_artifact_availability_continuity_candidate_v1(
            cls.signed_schedule,
            cls.epoch_rows,
            expected_signed_continuity_schedule_hash=cls.signed_schedule_hash,
            expected_continuity_schedule_hash=cls.schedule_hash,
            expected_final_epoch_observation_hash=cls.final_observation_hash,
        )
        if cls.result is None:
            raise AssertionError("failed to build synthetic continuity evidence")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.availability_fixture.tearDownClass()

    def _evaluate(self, rows=None, signed_schedule=None):
        return evaluate_strategy_correlation_identity_bound_transcript_artifact_availability_continuity_candidate_v1(
            self.signed_schedule if signed_schedule is None else signed_schedule,
            self.epoch_rows if rows is None else rows,
            expected_signed_continuity_schedule_hash=self.signed_schedule_hash,
            expected_continuity_schedule_hash=self.schedule_hash,
            expected_final_epoch_observation_hash=self.final_observation_hash,
        )

    def _clone_epoch_rows(self):
        rows = []
        for row in self.epoch_rows:
            context = dict(row["availability_receipt_verification_context"])
            context["signed_retrieval_receipt_documents"] = copy.deepcopy(
                context["signed_retrieval_receipt_documents"]
            )
            rows.append(
                {
                    "epoch_observation_document": copy.deepcopy(
                        row["epoch_observation_document"]
                    ),
                    "availability_receipt_evidence_document": copy.deepcopy(
                        row["availability_receipt_evidence_document"]
                    ),
                    "availability_receipt_verification_context": context,
                    "expected_availability_receipt_evidence_hash": row[
                        "expected_availability_receipt_evidence_hash"
                    ],
                }
            )
        return rows

    def test_exact_three_epoch_candidate_remains_blocked(self) -> None:
        self.assertEqual(
            self.result["status"],
            "OBSERVED_PREREGISTERED_THREE_EPOCH_LOCAL_RETRIEVAL_CONTINUITY_CANDIDATE",
        )
        self.assertEqual(self.result["consumer_status"], "UNMOUNTED_CANDIDATE")
        self.assertEqual(self.result["permission_state"], "BLOCKED")
        self.assertEqual(self.result["continuity"]["epoch_count"], 3)
        self.assertEqual(self.result["continuity"]["signed_retrieval_claim_count"], 12)

    def test_exact_verifier_reconstructs_continuity(self) -> None:
        self.assertTrue(
            verify_strategy_correlation_identity_bound_transcript_artifact_availability_continuity_candidate_v1(
                self.result,
                self.signed_schedule,
                self.epoch_rows,
                expected_continuity_evidence_hash=self.result["continuity_evidence_hash"],
                expected_signed_continuity_schedule_hash=self.signed_schedule_hash,
                expected_continuity_schedule_hash=self.schedule_hash,
                expected_final_epoch_observation_hash=self.final_observation_hash,
            )
        )

    def test_signed_schedule_verifier(self) -> None:
        self.assertTrue(
            verify_signed_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
                self.signed_schedule,
                self.registration,
                self.publication,
                expected_signed_continuity_schedule_hash=self.signed_schedule_hash,
                expected_continuity_schedule_hash=self.schedule_hash,
            )
        )

    def test_missing_or_reordered_epoch_is_rejected(self) -> None:
        self.assertIsNone(self._evaluate(rows=self.epoch_rows[:-1]))
        reordered = self._clone_epoch_rows()
        reordered[0], reordered[1] = reordered[1], reordered[0]
        self.assertIsNone(self._evaluate(rows=reordered))

    def test_replayed_epoch_evidence_is_rejected(self) -> None:
        rows = self._clone_epoch_rows()
        rows[1]["availability_receipt_evidence_document"] = copy.deepcopy(
            rows[0]["availability_receipt_evidence_document"]
        )
        rows[1]["availability_receipt_verification_context"] = dict(
            rows[0]["availability_receipt_verification_context"]
        )
        rows[1]["expected_availability_receipt_evidence_hash"] = rows[0][
            "expected_availability_receipt_evidence_hash"
        ]
        self.assertIsNone(self._evaluate(rows=rows))

    def test_duplicate_schedule_challenge_is_rejected(self) -> None:
        epoch_inputs = copy.deepcopy(self.epoch_inputs)
        epoch_inputs[1]["challenge_rows"][0]["challenge_nonce_hash"] = epoch_inputs[0][
            "challenge_rows"
        ][0]["challenge_nonce_hash"]
        with self.assertRaises(ValueError):
            build_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
                self.registration,
                self.publication,
                expected_availability_registration_hash=self.registration_hash,
                expected_signed_publication_receipt_hash=self.publication_hash,
                epoch_rows=epoch_inputs,
            )

    def test_wrong_schedule_signature_is_rejected(self) -> None:
        document = copy.deepcopy(self.signed_schedule)
        signature = bytearray(base64.b64decode(document["signature_base64"]))
        signature[0] ^= 1
        document.pop("signed_continuity_schedule_hash")
        document["signature_base64"] = base64.b64encode(bytes(signature)).decode("ascii")
        document = seal_strict_canonical_document(
            document, "signed_continuity_schedule_hash"
        )
        self.assertFalse(
            verify_signed_strategy_correlation_transcript_artifact_availability_continuity_schedule_v1(
                document,
                self.registration,
                self.publication,
                expected_signed_continuity_schedule_hash=document[
                    "signed_continuity_schedule_hash"
                ],
                expected_continuity_schedule_hash=self.schedule_hash,
            )
        )

    def test_previous_observation_hash_drift_is_rejected(self) -> None:
        rows = self._clone_epoch_rows()
        observation = rows[1]["epoch_observation_document"]
        observation.pop("epoch_observation_hash")
        observation["source"]["previous_epoch_observation_hash"] = "f" * 64
        rows[1]["epoch_observation_document"] = seal_strict_canonical_document(
            observation, "epoch_observation_hash"
        )
        self.assertIsNone(self._evaluate(rows=rows))

    def test_epoch_receipt_replay_is_rejected(self) -> None:
        rows = self._clone_epoch_rows()
        rows[1]["availability_receipt_verification_context"][
            "signed_retrieval_receipt_documents"
        ][0] = copy.deepcopy(
            rows[0]["availability_receipt_verification_context"][
                "signed_retrieval_receipt_documents"
            ][0]
        )
        self.assertIsNone(self._evaluate(rows=rows))

    def test_context_alias_is_rejected(self) -> None:
        rows = self._clone_epoch_rows()
        rows[0]["availability_receipt_verification_context"][
            "availability_evidence_alias"
        ] = rows[0]["availability_receipt_evidence_document"]
        self.assertIsNone(self._evaluate(rows=rows))

    def test_output_redacts_keys_signatures_receipts_and_raw_challenges(self) -> None:
        encoded = json.dumps(self.result, sort_keys=True)
        self.assertNotIn(self.availability_fixture.publisher_spki, encoded)
        self.assertNotIn(self.schedule_signature, encoded)
        first_receipt = self.epoch_availability[0]["context"][
            "signed_retrieval_receipt_documents"
        ][0]
        self.assertNotIn(first_receipt["signature_base64"], encoded)
        first_challenge = self.epoch_inputs[0]["challenge_rows"][0][
            "challenge_nonce_hash"
        ]
        self.assertNotIn(first_challenge, encoded)

    def test_local_epochs_never_promote_external_time_or_durability(self) -> None:
        facts = self.result["facts"]
        authority = self.result["authority"]
        self.assertTrue(facts["local_multi_epoch_retrieval_continuity_claim_verified"])
        for field in (
            "external_time_truth_verified",
            "external_artifact_durability_verified",
            "external_persistence_verified",
            "network_retrieval_verified",
            "public_artifact_availability_verified",
            "publisher_identity_verified",
            "retriever_identities_verified",
            "retriever_independence_verified",
        ):
            self.assertFalse(facts[field])
        self.assertTrue(all(value is False for value in authority.values()))
        self.assertEqual(self.result["permission"], {"paper": "UNAUTHORIZED", "live": "UNAUTHORIZED"})


if __name__ == "__main__":
    unittest.main()
