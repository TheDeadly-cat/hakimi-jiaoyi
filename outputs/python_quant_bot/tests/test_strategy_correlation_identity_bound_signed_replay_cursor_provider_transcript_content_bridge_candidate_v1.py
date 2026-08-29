from __future__ import annotations

import base64
import copy
import dataclasses
import json
from types import SimpleNamespace
import unittest

from exchange_terminal.application import (
    strategy_correlation_identity_bound_signed_replay_cursor_provider_conformance_bridge_candidate_v1
    as identity_conformance_bridge,
)
from exchange_terminal.application import (
    strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1
    as identity_receipt_bridge,
)
from exchange_terminal.application import (
    strategy_correlation_identity_bound_signed_replay_cursor_provider_transcript_content_bridge_candidate_v1
    as bridge,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_evidence_v1
    as conformance,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_transcript_binding_v1
    as transcript_binding,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_transcript_content_verifier_v1
    as transcript_content,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_receipt_v1
    as signed_receipt,
)
from exchange_terminal.application.ports import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1
    as replay_cursor_provider,
)
import tests.test_strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1 as identity_fixture_module
import tests.test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_transcript_content_verifier_v1 as content_fixture_module
import tests.test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_receipt_v1 as signed_fixture_module


def _replace_strings(value, replacements):
    if isinstance(value, str):
        return replacements.get(value, value)
    if isinstance(value, list):
        return [_replace_strings(item, replacements) for item in value]
    if isinstance(value, tuple):
        return tuple(_replace_strings(item, replacements) for item in value)
    if isinstance(value, dict):
        return {
            key: _replace_strings(item, replacements)
            for key, item in value.items()
        }
    return value


def _nested_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _nested_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _nested_keys(item)


class StrategyCorrelationIdentityBoundSignedReplayCursorProviderTranscriptContentBridgeCandidateV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        Content = content_fixture_module.ReplayCursorProviderConformanceTranscriptContentVerifierV1Tests
        Identity = identity_fixture_module.StrategyCorrelationIdentityBoundPositionDerivedReplayCursorCasBridgeCandidateV1Tests
        Signed = signed_fixture_module.ReplayCursorProviderSignedReceiptV1Tests
        Content.setUpClass()
        Binding = Content.fixture_class
        Conformance = Binding.fixture_class
        Identity.setUpClass()
        cls.content_fixture = Content
        cls.binding_fixture = Binding
        cls.conformance_fixture = Conformance
        cls.identity_fixture = Identity

        old_args = Conformance.signed_receipt_verify_args
        old_kwargs = Conformance.signed_receipt_verify_kwargs
        old_command = old_args[2]
        old_result = old_args[3]
        registration_evidence, signed_registration, registration_claim, preregistration = old_args[4:]
        cas_result = Identity.cas_result

        command_payload = replay_cursor_provider._command_payload(
            stream_id=cas_result.stream_id,
            projection_preregistration_hash=cas_result.projection_preregistration_hash,
            intent_hash=cas_result.intent_hash,
            freshness_result_fingerprint_sha256=cas_result.freshness_result_fingerprint_sha256,
            candidate_attestation_hash=cas_result.attestation_hash,
            candidate_sequence=cas_result.candidate_sequence,
            request_nonce_hash=cas_result.request_nonce_hash,
            transition_receipt_hash=cas_result.receipt_hash,
            base_cursor=Identity.base_cursor,
            proposed_cursor=cas_result.returned_cursor,
        )
        cls.command = replay_cursor_provider.ReplayCursorCompareAndAdvanceCommandV1(
            stream_id=cas_result.stream_id,
            projection_preregistration_hash=cas_result.projection_preregistration_hash,
            intent_hash=cas_result.intent_hash,
            freshness_result_fingerprint_sha256=cas_result.freshness_result_fingerprint_sha256,
            candidate_attestation_hash=cas_result.attestation_hash,
            candidate_sequence=cas_result.candidate_sequence,
            request_nonce_hash=cas_result.request_nonce_hash,
            transition_receipt_hash=cas_result.receipt_hash,
            base_cursor=Identity.base_cursor,
            proposed_cursor=cas_result.returned_cursor,
            command_hash=replay_cursor_provider._hash_payload(command_payload),
            schema_version=command_payload["schema_version"],
        )
        replacements = {
            old_command.command_hash: cls.command.command_hash,
            old_command.intent_hash: cls.command.intent_hash,
            old_command.base_cursor.cursor_hash: cas_result.observed_cursor_hash,
            old_command.proposed_cursor.cursor_hash: cas_result.returned_cursor_hash,
        }
        cls.provider_result = dataclasses.replace(
            old_result,
            outcome=replay_cursor_provider.ReplayCursorProviderOutcomeV1.ADVANCED,
            command_hash=cls.command.command_hash,
            intent_hash=cls.command.intent_hash,
            observed_cursor_hash=cas_result.observed_cursor_hash,
            returned_cursor_hash=cas_result.returned_cursor_hash,
            receipt_document=_replace_strings(old_result.receipt_document, replacements),
        )
        cls.receipt_claim = signed_receipt.build_replay_cursor_provider_receipt_claim_v1(
            cls.command,
            cls.provider_result,
            registration_evidence,
            signed_registration,
            registration_claim,
            preregistration,
            expected_registration_evidence_hash=old_kwargs[
                "expected_registration_evidence_hash"
            ],
            registration_verification_kwargs=old_kwargs[
                "registration_verification_kwargs"
            ],
        )
        cls.receipt_signature_base64 = base64.b64encode(
            Signed.private_key.sign(
                bytes.fromhex(cls.receipt_claim["receipt_claim_hash"])
            )
        ).decode("ascii")
        cls.signed_receipt_document = signed_receipt.build_signed_replay_cursor_provider_receipt_v1(
            cls.receipt_claim,
            cls.command,
            cls.provider_result,
            registration_evidence,
            signed_registration,
            registration_claim,
            preregistration,
            public_key_spki_base64=old_kwargs["public_key_spki_base64"],
            signature_base64=cls.receipt_signature_base64,
            expected_receipt_claim_hash=cls.receipt_claim["receipt_claim_hash"],
            expected_registration_evidence_hash=old_kwargs[
                "expected_registration_evidence_hash"
            ],
            registration_verification_kwargs=old_kwargs[
                "registration_verification_kwargs"
            ],
        )
        cls.receipt_verify_kwargs = {
            "public_key_spki_base64": old_kwargs["public_key_spki_base64"],
            "signature_base64": cls.receipt_signature_base64,
            "expected_signed_receipt_hash": cls.signed_receipt_document[
                "signed_receipt_hash"
            ],
            "expected_receipt_claim_hash": cls.receipt_claim[
                "receipt_claim_hash"
            ],
            "expected_registration_evidence_hash": old_kwargs[
                "expected_registration_evidence_hash"
            ],
            "registration_verification_kwargs": old_kwargs[
                "registration_verification_kwargs"
            ],
        }
        cls.receipt_verify_args = (
            cls.signed_receipt_document,
            cls.receipt_claim,
            cls.command,
            cls.provider_result,
            registration_evidence,
            signed_registration,
            registration_claim,
            preregistration,
        )
        cls.receipt_evidence = signed_receipt.evaluate_signed_replay_cursor_provider_receipt_v1(
            *cls.receipt_verify_args,
            **cls.receipt_verify_kwargs,
        )

        cls.identity_cas_context = {
            "identity_bound_result": Identity.identity_result,
            "identity_bound_verification_context": Identity.identity_context,
            "freshness_binding_result": Identity.freshness_result,
            "freshness_binding_verification_context": Identity.freshness_context,
            "replay_cursor_cas_binding_result": cas_result,
            "attestation": Identity.attestation,
            "base_cursor": Identity.base_cursor,
            "observed_cursor": Identity.base_cursor,
            "expected_identity_bound_post_merge_hash": Identity.identity_result[
                "identity_bound_post_merge_hash"
            ],
            "expected_freshness_binding_hash": Identity.freshness_result.binding_hash,
            "expected_replay_cursor_cas_binding_hash": cas_result.binding_hash,
            "request_nonce_hash": Identity.request_nonce_hash,
            "expected_observed_cursor_hash": cas_result.observed_cursor_hash,
        }
        cls.receipt_context = {
            "signed_receipt_document": cls.signed_receipt_document,
            "receipt_claim_document": cls.receipt_claim,
            "registration_evidence_document": registration_evidence,
            "signed_registration_document": signed_registration,
            "registration_claim_document": registration_claim,
            "preregistration_document": preregistration,
            **cls.receipt_verify_kwargs,
        }
        cls.identity_receipt_document = identity_receipt_bridge.evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1(
            Identity.bridge,
            cls.identity_cas_context,
            cas_result,
            cls.command,
            cls.provider_result,
            cls.receipt_evidence,
            cls.receipt_context,
            expected_identity_bound_cas_bridge_hash=Identity.bridge[
                "identity_bound_cas_bridge_hash"
            ],
            expected_replay_cursor_cas_binding_hash=cas_result.binding_hash,
            expected_provider_command_hash=cls.command.command_hash,
            expected_signed_receipt_verification_evidence_hash=cls.receipt_evidence[
                "verification_evidence_hash"
            ],
        )
        cls.identity_receipt_context = {
            "identity_bound_cas_bridge_document": Identity.bridge,
            "identity_bound_cas_verification_context": cls.identity_cas_context,
            "replay_cursor_cas_binding_result": cas_result,
            "provider_command": cls.command,
            "provider_result": cls.provider_result,
            "signed_receipt_evidence_document": cls.receipt_evidence,
            "signed_receipt_verification_context": cls.receipt_context,
            "expected_identity_bound_cas_bridge_hash": Identity.bridge[
                "identity_bound_cas_bridge_hash"
            ],
            "expected_replay_cursor_cas_binding_hash": cas_result.binding_hash,
            "expected_provider_command_hash": cls.command.command_hash,
            "expected_signed_receipt_verification_evidence_hash": cls.receipt_evidence[
                "verification_evidence_hash"
            ],
        }

        cls.upstream_kwargs = {
            "observer_registrations": Conformance.observer_registrations,
            "provider_preregistration_kwargs": Conformance.provider_preregistration_kwargs,
            "signed_receipt_verify_args": cls.receipt_verify_args,
            "signed_receipt_verify_kwargs": cls.receipt_verify_kwargs,
            "expected_signed_receipt_evidence_hash": cls.receipt_evidence[
                "verification_evidence_hash"
            ],
        }
        original_evidence = Conformance.signed_receipt_evidence_document
        original_upstream = Conformance.upstream_kwargs
        try:
            Conformance.signed_receipt_evidence_document = cls.receipt_evidence
            Conformance.upstream_kwargs = cls.upstream_kwargs
            cls.bound_signed_reports = [
                Conformance._build_signed_report(
                    index,
                    case_rows=Binding.bound_case_rows[index],
                )
                for index in range(3)
            ]
        finally:
            Conformance.signed_receipt_evidence_document = original_evidence
            Conformance.upstream_kwargs = original_upstream

        cls.quorum_evidence = conformance.evaluate_replay_cursor_provider_conformance_observer_quorum_v1(
            cls.bound_signed_reports[:2],
            Binding.plan_document,
            Binding.provider_preregistration_document,
            cls.receipt_evidence,
            **cls.upstream_kwargs,
        )
        cls.conformance_context = {
            "signed_report_documents": cls.bound_signed_reports[:2],
            "plan_document": Binding.plan_document,
            "provider_preregistration_document": Binding.provider_preregistration_document,
            "signed_receipt_evidence_document": cls.receipt_evidence,
            **cls.upstream_kwargs,
        }
        cls.identity_conformance_document = identity_conformance_bridge.evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_conformance_bridge_candidate_v1(
            cls.identity_receipt_document,
            cls.identity_receipt_context,
            cls.quorum_evidence,
            cls.conformance_context,
            expected_identity_bound_signed_receipt_bridge_hash=cls.identity_receipt_document[
                "identity_bound_signed_provider_receipt_bridge_hash"
            ],
            expected_conformance_quorum_evidence_hash=cls.quorum_evidence[
                "quorum_evidence_hash"
            ],
            expected_signed_receipt_evidence_hash=cls.receipt_evidence[
                "verification_evidence_hash"
            ],
            expected_conformance_plan_hash=Binding.plan_document[
                "conformance_plan_hash"
            ],
            expected_provider_preregistration_hash=Binding.provider_preregistration_document[
                "preregistration_hash"
            ],
        )
        cls.identity_conformance_context = {
            "identity_bound_signed_receipt_bridge_document": cls.identity_receipt_document,
            "identity_bound_signed_receipt_bridge_verification_context": cls.identity_receipt_context,
            "conformance_quorum_evidence_document": cls.quorum_evidence,
            "conformance_quorum_verification_context": cls.conformance_context,
            "expected_identity_bound_signed_receipt_bridge_hash": cls.identity_receipt_document[
                "identity_bound_signed_provider_receipt_bridge_hash"
            ],
            "expected_conformance_quorum_evidence_hash": cls.quorum_evidence[
                "quorum_evidence_hash"
            ],
            "expected_signed_receipt_evidence_hash": cls.receipt_evidence[
                "verification_evidence_hash"
            ],
            "expected_conformance_plan_hash": Binding.plan_document[
                "conformance_plan_hash"
            ],
            "expected_provider_preregistration_hash": Binding.provider_preregistration_document[
                "preregistration_hash"
            ],
        }

        cls.manifests = [
            transcript_binding.build_replay_cursor_provider_conformance_transcript_manifest_v1(
                cls.bound_signed_reports[index],
                Binding.plan_document,
                cls.receipt_evidence,
                runner_implementation_sha256=Binding.runner_hashes[index],
                environment_manifest_sha256=Binding.environment_hashes[index],
                case_transcript_rows=Binding.transcript_rows[index],
                expected_signed_observer_report_hash=cls.bound_signed_reports[index][
                    "signed_observer_report_hash"
                ],
            )
            for index in range(2)
        ]
        cls.binding_verify_kwargs = {
            "expected_quorum_evidence_hash": cls.quorum_evidence[
                "quorum_evidence_hash"
            ],
            "quorum_verify_kwargs": cls.upstream_kwargs,
        }
        cls.binding_document = transcript_binding.evaluate_replay_cursor_provider_conformance_transcript_binding_v1(
            cls.manifests,
            cls.quorum_evidence,
            cls.bound_signed_reports[:2],
            Binding.plan_document,
            Binding.provider_preregistration_document,
            cls.receipt_evidence,
            **cls.binding_verify_kwargs,
        )
        cls.content_bundles = [
            transcript_content.build_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                cls.manifests[index],
                case_payload_rows=Content.payload_rows[index],
                expected_transcript_manifest_hash=cls.manifests[index][
                    "transcript_manifest_hash"
                ],
            )
            for index in range(2)
        ]
        cls.content_verify_kwargs = {
            "expected_transcript_binding_hash": cls.binding_document[
                "transcript_binding_hash"
            ],
            "transcript_binding_verify_kwargs": cls.binding_verify_kwargs,
        }
        cls.content_evidence = transcript_content.evaluate_replay_cursor_provider_conformance_transcript_content_v1(
            cls.content_bundles,
            cls.binding_document,
            cls.manifests,
            cls.quorum_evidence,
            cls.bound_signed_reports[:2],
            Binding.plan_document,
            Binding.provider_preregistration_document,
            cls.receipt_evidence,
            **cls.content_verify_kwargs,
        )
        cls.content_context = {
            "content_bundle_documents": cls.content_bundles,
            "transcript_binding_document": cls.binding_document,
            "transcript_manifest_documents": cls.manifests,
            "quorum_evidence_document": cls.quorum_evidence,
            "signed_report_documents": cls.bound_signed_reports[:2],
            "plan_document": Binding.plan_document,
            "provider_preregistration_document": Binding.provider_preregistration_document,
            "signed_receipt_evidence_document": cls.receipt_evidence,
            **cls.content_verify_kwargs,
        }
        cls.result = cls._evaluate_static()

    @classmethod
    def _evaluate_static(cls, **overrides):
        Binding = cls.binding_fixture
        arguments = {
            "identity_bound_conformance_bridge_document": cls.identity_conformance_document,
            "identity_bound_conformance_bridge_verification_context": cls.identity_conformance_context,
            "transcript_content_evidence_document": cls.content_evidence,
            "transcript_content_verification_context": cls.content_context,
            "expected_identity_bound_conformance_bridge_hash": cls.identity_conformance_document[
                "identity_bound_signed_provider_conformance_bridge_hash"
            ],
            "expected_content_verification_hash": cls.content_evidence[
                "content_verification_hash"
            ],
            "expected_transcript_binding_hash": cls.binding_document[
                "transcript_binding_hash"
            ],
            "expected_conformance_quorum_evidence_hash": cls.quorum_evidence[
                "quorum_evidence_hash"
            ],
            "expected_signed_receipt_evidence_hash": cls.receipt_evidence[
                "verification_evidence_hash"
            ],
            "expected_conformance_plan_hash": Binding.plan_document[
                "conformance_plan_hash"
            ],
            "expected_provider_preregistration_hash": Binding.provider_preregistration_document[
                "preregistration_hash"
            ],
        }
        arguments.update(overrides)
        return bridge.evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_transcript_content_bridge_candidate_v1(
            **arguments
        )

    def test_exact_local_content_candidate_remains_blocked(self):
        self.assertIsNotNone(self.result)
        self.assertEqual(self.result["status"], bridge.STATUS)
        self.assertEqual(self.result["decision"], bridge.DECISION)
        self.assertEqual(self.result["permission_state"], "BLOCKED")
        self.assertEqual(self.result["consumer_status"], "UNMOUNTED_CANDIDATE")
        self.assertTrue(all(value is False for value in self.result["authority"].values()))

    def test_exact_verifier_reconstructs_bridge(self):
        self.assertTrue(
            bridge.verify_strategy_correlation_identity_bound_signed_replay_cursor_provider_transcript_content_bridge_candidate_v1(
                self.result,
                self.identity_conformance_document,
                self.identity_conformance_context,
                self.content_evidence,
                self.content_context,
                expected_identity_bound_provider_transcript_content_bridge_hash=self.result[
                    "identity_bound_provider_transcript_content_bridge_hash"
                ],
                expected_identity_bound_conformance_bridge_hash=self.identity_conformance_document[
                    "identity_bound_signed_provider_conformance_bridge_hash"
                ],
                expected_content_verification_hash=self.content_evidence[
                    "content_verification_hash"
                ],
                expected_transcript_binding_hash=self.binding_document[
                    "transcript_binding_hash"
                ],
                expected_conformance_quorum_evidence_hash=self.quorum_evidence[
                    "quorum_evidence_hash"
                ],
                expected_signed_receipt_evidence_hash=self.receipt_evidence[
                    "verification_evidence_hash"
                ],
                expected_conformance_plan_hash=self.binding_fixture.plan_document[
                    "conformance_plan_hash"
                ],
                expected_provider_preregistration_hash=self.binding_fixture.provider_preregistration_document[
                    "preregistration_hash"
                ],
            )
        )

    def test_evaluation_is_deterministic(self):
        self.assertEqual(self._evaluate_static(), self.result)

    def test_old_content_chain_cannot_be_spliced(self):
        old_case = self.content_fixture(
            "test_valid_local_content_passes_without_availability_promotion"
        )
        old_evidence = old_case.evaluate()
        old_context = {
            "content_bundle_documents": self.content_fixture.content_bundles,
            "transcript_binding_document": self.content_fixture.binding_document,
            "transcript_manifest_documents": self.content_fixture.manifests,
            "quorum_evidence_document": self.content_fixture.quorum_evidence,
            "signed_report_documents": self.content_fixture.bound_signed_reports[:2],
            "plan_document": self.content_fixture.plan_document,
            "provider_preregistration_document": self.content_fixture.provider_preregistration_document,
            "signed_receipt_evidence_document": self.content_fixture.signed_receipt_evidence_document,
            **self.content_fixture.evaluation_kwargs,
        }
        self.assertIsNone(
            self._evaluate_static(
                transcript_content_evidence_document=old_evidence,
                transcript_content_verification_context=old_context,
                expected_content_verification_hash=old_evidence[
                    "content_verification_hash"
                ],
                expected_transcript_binding_hash=self.content_fixture.binding_document[
                    "transcript_binding_hash"
                ],
            )
        )

    def test_missing_content_bundle_is_rejected(self):
        evidence = transcript_content.evaluate_replay_cursor_provider_conformance_transcript_content_v1(
            self.content_bundles[:1],
            self.binding_document,
            self.manifests,
            self.quorum_evidence,
            self.bound_signed_reports[:2],
            self.binding_fixture.plan_document,
            self.binding_fixture.provider_preregistration_document,
            self.receipt_evidence,
            **self.content_verify_kwargs,
        )
        context = {
            **self.content_context,
            "content_bundle_documents": self.content_bundles[:1],
        }
        self.assertIsNone(
            self._evaluate_static(
                transcript_content_evidence_document=evidence,
                transcript_content_verification_context=context,
                expected_content_verification_hash=evidence[
                    "content_verification_hash"
                ],
            )
        )

    def test_tampered_identity_conformance_bridge_is_rejected(self):
        document = copy.deepcopy(self.identity_conformance_document)
        document["permission_state"] = "ALLOWED"
        self.assertIsNone(
            self._evaluate_static(identity_bound_conformance_bridge_document=document)
        )

    def test_tampered_content_evidence_is_rejected(self):
        document = copy.deepcopy(self.content_evidence)
        document["admission_status"] = "ALLOWED"
        self.assertIsNone(
            self._evaluate_static(transcript_content_evidence_document=document)
        )

    def test_expected_hash_drift_is_rejected(self):
        for field in (
            "expected_identity_bound_conformance_bridge_hash",
            "expected_content_verification_hash",
            "expected_transcript_binding_hash",
            "expected_conformance_quorum_evidence_hash",
            "expected_signed_receipt_evidence_hash",
            "expected_conformance_plan_hash",
            "expected_provider_preregistration_hash",
        ):
            with self.subTest(field=field):
                self.assertIsNone(self._evaluate_static(**{field: "a" * 64}))

    def test_identity_context_alias_is_rejected(self):
        context = dict(self.identity_conformance_context)
        context["compatibility_alias"] = True
        self.assertIsNone(
            self._evaluate_static(
                identity_bound_conformance_bridge_verification_context=context
            )
        )

    def test_content_context_alias_is_rejected(self):
        context = dict(self.content_context)
        context["compatibility_alias"] = True
        self.assertIsNone(
            self._evaluate_static(transcript_content_verification_context=context)
        )

    def test_quorum_or_report_splice_is_rejected(self):
        context = {
            **self.content_context,
            "signed_report_documents": self.content_fixture.bound_signed_reports[:2],
        }
        self.assertIsNone(
            self._evaluate_static(transcript_content_verification_context=context)
        )

    def test_provider_preregistration_splice_is_rejected(self):
        document = copy.deepcopy(
            self.binding_fixture.provider_preregistration_document
        )
        document["identity"]["registry_id"] = "synthetic-spliced-registry"
        context = {
            **self.content_context,
            "provider_preregistration_document": document,
        }
        self.assertIsNone(
            self._evaluate_static(transcript_content_verification_context=context)
        )

    def test_shape_compatible_alias_is_rejected(self):
        alias = SimpleNamespace(**self.content_evidence)
        self.assertIsNone(
            self._evaluate_static(transcript_content_evidence_document=alias)
        )

    def test_local_content_never_promotes_availability_or_execution(self):
        facts = self.result["facts"]
        self.assertTrue(facts["local_content_hashes_and_sizes_exactly_verified"])
        self.assertFalse(facts["external_artifact_retrieval_verified"])
        self.assertFalse(facts["public_artifact_availability_verified"])
        self.assertFalse(facts["runner_implementation_verified"])
        self.assertFalse(facts["environment_manifest_verified"])
        self.assertFalse(facts["observer_test_execution_source_truth_verified"])
        self.assertFalse(facts["external_provider_conformance_verified"])

    def test_output_redacts_payloads_manifests_reports_keys_and_signatures(self):
        forbidden_keys = {
            "content_bundle_documents",
            "content_bundles",
            "case_payloads",
            "transcript_manifest_documents",
            "case_transcripts",
            "signed_report_documents",
            "observer_report",
            "public_key_spki_base64",
            "signature_base64",
            "signed_receipt_document",
            "receipt_document",
        }
        self.assertTrue(forbidden_keys.isdisjoint(set(_nested_keys(self.result))))
        serialized = json.dumps(self.result, sort_keys=True)
        self.assertNotIn(self.receipt_signature_base64, serialized)
        for report in self.bound_signed_reports[:2]:
            self.assertNotIn(report["signature_base64"], serialized)
            self.assertNotIn(report["public_key_spki_base64"], serialized)
        for rows in self.content_fixture.payload_rows:
            for row in rows:
                for key, value in row.items():
                    if key != "case_id":
                        self.assertNotIn(value, serialized)


if __name__ == "__main__":
    unittest.main()
