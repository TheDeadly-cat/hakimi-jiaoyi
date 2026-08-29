from __future__ import annotations

import base64
import copy
import dataclasses
import json
from types import SimpleNamespace
import unittest

from exchange_terminal.application import (
    strategy_correlation_identity_bound_signed_replay_cursor_provider_conformance_bridge_candidate_v1
    as bridge,
)
from exchange_terminal.application import (
    strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1
    as identity_signed_bridge,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_evidence_v1
    as conformance,
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
import tests.test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_evidence_v1 as conformance_fixture_module
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


class StrategyCorrelationIdentityBoundSignedReplayCursorProviderConformanceBridgeCandidateV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        Conformance = (
            conformance_fixture_module.ReplayCursorProviderConformanceEvidenceV1Tests
        )
        Identity = identity_fixture_module.StrategyCorrelationIdentityBoundPositionDerivedReplayCursorCasBridgeCandidateV1Tests
        Signed = signed_fixture_module.ReplayCursorProviderSignedReceiptV1Tests
        Conformance.setUpClass()
        Identity.setUpClass()
        cls.conformance_fixture = Conformance
        cls.identity_fixture = Identity
        cls.signed_fixture = Signed

        old_args = Conformance.signed_receipt_verify_args
        old_kwargs = Conformance.signed_receipt_verify_kwargs
        old_command = old_args[2]
        old_result = old_args[3]
        (
            registration_evidence,
            signed_registration,
            registration_claim,
            preregistration,
        ) = old_args[4:]
        cas_result = Identity.cas_result
        cls.cas_result = cas_result

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
        cls.signed_receipt_verify_kwargs = {
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
        cls.signed_receipt_verify_args = (
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
            *cls.signed_receipt_verify_args,
            **cls.signed_receipt_verify_kwargs,
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
        cls.receipt_verification_context = {
            "signed_receipt_document": cls.signed_receipt_document,
            "receipt_claim_document": cls.receipt_claim,
            "registration_evidence_document": registration_evidence,
            "signed_registration_document": signed_registration,
            "registration_claim_document": registration_claim,
            "preregistration_document": preregistration,
            **cls.signed_receipt_verify_kwargs,
        }
        cls.identity_signed_receipt_bridge_document = identity_signed_bridge.evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1(
            Identity.bridge,
            cls.identity_cas_context,
            cas_result,
            cls.command,
            cls.provider_result,
            cls.receipt_evidence,
            cls.receipt_verification_context,
            expected_identity_bound_cas_bridge_hash=Identity.bridge[
                "identity_bound_cas_bridge_hash"
            ],
            expected_replay_cursor_cas_binding_hash=cas_result.binding_hash,
            expected_provider_command_hash=cls.command.command_hash,
            expected_signed_receipt_verification_evidence_hash=cls.receipt_evidence[
                "verification_evidence_hash"
            ],
        )
        cls.identity_bridge_context = {
            "identity_bound_cas_bridge_document": Identity.bridge,
            "identity_bound_cas_verification_context": cls.identity_cas_context,
            "replay_cursor_cas_binding_result": cas_result,
            "provider_command": cls.command,
            "provider_result": cls.provider_result,
            "signed_receipt_evidence_document": cls.receipt_evidence,
            "signed_receipt_verification_context": cls.receipt_verification_context,
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
            "signed_receipt_verify_args": cls.signed_receipt_verify_args,
            "signed_receipt_verify_kwargs": cls.signed_receipt_verify_kwargs,
            "expected_signed_receipt_evidence_hash": cls.receipt_evidence[
                "verification_evidence_hash"
            ],
        }
        cls.signed_reports = []
        for index, registration in enumerate(Conformance.observer_registrations):
            report_kwargs = {
                "observer_id": registration["observer_id"],
                "run_context_hash": Conformance.signed_reports[index][
                    "observer_report"
                ]["source"]["run_context_hash"],
                "case_rows": Conformance.case_rows,
                **cls.upstream_kwargs,
            }
            report = conformance.build_replay_cursor_provider_conformance_observer_report_v1(
                Conformance.plan_document,
                Conformance.provider_preregistration_document,
                cls.receipt_evidence,
                **report_kwargs,
            )
            message_hash = conformance.build_replay_cursor_provider_conformance_observer_signature_message_hash_v1(
                report,
                Conformance.plan_document,
                cls.receipt_evidence,
            )
            signature_base64 = base64.b64encode(
                Conformance.observer_private_keys[index].sign(
                    bytes.fromhex(message_hash)
                )
            ).decode("ascii")
            cls.signed_reports.append(
                conformance.build_signed_replay_cursor_provider_conformance_observer_report_v1(
                    report,
                    Conformance.plan_document,
                    Conformance.provider_preregistration_document,
                    cls.receipt_evidence,
                    public_key_spki_base64=base64.b64encode(
                        Conformance.observer_spki[index]
                    ).decode("ascii"),
                    signature_base64=signature_base64,
                    report_verify_kwargs=cls.upstream_kwargs,
                )
            )
        cls.quorum_evidence = conformance.evaluate_replay_cursor_provider_conformance_observer_quorum_v1(
            cls.signed_reports,
            Conformance.plan_document,
            Conformance.provider_preregistration_document,
            cls.receipt_evidence,
            **cls.upstream_kwargs,
        )
        cls.conformance_context = {
            "signed_report_documents": cls.signed_reports,
            "plan_document": Conformance.plan_document,
            "provider_preregistration_document": Conformance.provider_preregistration_document,
            "signed_receipt_evidence_document": cls.receipt_evidence,
            **cls.upstream_kwargs,
        }
        cls.result = cls._evaluate_static()

    @classmethod
    def _evaluate_static(cls, **overrides):
        Conformance = cls.conformance_fixture
        arguments = {
            "identity_bound_signed_receipt_bridge_document": cls.identity_signed_receipt_bridge_document,
            "identity_bound_signed_receipt_bridge_verification_context": cls.identity_bridge_context,
            "conformance_quorum_evidence_document": cls.quorum_evidence,
            "conformance_quorum_verification_context": cls.conformance_context,
            "expected_identity_bound_signed_receipt_bridge_hash": cls.identity_signed_receipt_bridge_document[
                "identity_bound_signed_provider_receipt_bridge_hash"
            ],
            "expected_conformance_quorum_evidence_hash": cls.quorum_evidence[
                "quorum_evidence_hash"
            ],
            "expected_signed_receipt_evidence_hash": cls.receipt_evidence[
                "verification_evidence_hash"
            ],
            "expected_conformance_plan_hash": Conformance.plan_document[
                "conformance_plan_hash"
            ],
            "expected_provider_preregistration_hash": Conformance.provider_preregistration_document[
                "preregistration_hash"
            ],
        }
        arguments.update(overrides)
        return bridge.evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_conformance_bridge_candidate_v1(
            **arguments
        )

    def test_exact_local_quorum_candidate_remains_blocked(self):
        self.assertIsNotNone(self.result)
        self.assertEqual(self.result["status"], bridge.STATUS)
        self.assertEqual(self.result["decision"], bridge.DECISION)
        self.assertEqual(self.result["permission_state"], "BLOCKED")
        self.assertEqual(self.result["consumer_status"], "UNMOUNTED_CANDIDATE")
        self.assertTrue(all(value is False for value in self.result["authority"].values()))

    def test_exact_verifier_reconstructs_bridge(self):
        self.assertTrue(
            bridge.verify_strategy_correlation_identity_bound_signed_replay_cursor_provider_conformance_bridge_candidate_v1(
                self.result,
                self.identity_signed_receipt_bridge_document,
                self.identity_bridge_context,
                self.quorum_evidence,
                self.conformance_context,
                expected_identity_bound_signed_provider_conformance_bridge_hash=self.result[
                    "identity_bound_signed_provider_conformance_bridge_hash"
                ],
                expected_identity_bound_signed_receipt_bridge_hash=self.identity_signed_receipt_bridge_document[
                    "identity_bound_signed_provider_receipt_bridge_hash"
                ],
                expected_conformance_quorum_evidence_hash=self.quorum_evidence[
                    "quorum_evidence_hash"
                ],
                expected_signed_receipt_evidence_hash=self.receipt_evidence[
                    "verification_evidence_hash"
                ],
                expected_conformance_plan_hash=self.conformance_fixture.plan_document[
                    "conformance_plan_hash"
                ],
                expected_provider_preregistration_hash=self.conformance_fixture.provider_preregistration_document[
                    "preregistration_hash"
                ],
            )
        )

    def test_evaluation_is_deterministic(self):
        self.assertEqual(self._evaluate_static(), self.result)

    def test_old_quorum_receipt_identity_cannot_be_spliced(self):
        old_quorum = conformance.evaluate_replay_cursor_provider_conformance_observer_quorum_v1(
            self.conformance_fixture.signed_reports,
            self.conformance_fixture.plan_document,
            self.conformance_fixture.provider_preregistration_document,
            self.conformance_fixture.signed_receipt_evidence_document,
            **self.conformance_fixture.upstream_kwargs,
        )
        old_context = {
            "signed_report_documents": self.conformance_fixture.signed_reports,
            "plan_document": self.conformance_fixture.plan_document,
            "provider_preregistration_document": self.conformance_fixture.provider_preregistration_document,
            "signed_receipt_evidence_document": self.conformance_fixture.signed_receipt_evidence_document,
            **self.conformance_fixture.upstream_kwargs,
        }
        self.assertIsNone(
            self._evaluate_static(
                conformance_quorum_evidence_document=old_quorum,
                conformance_quorum_verification_context=old_context,
                expected_conformance_quorum_evidence_hash=old_quorum[
                    "quorum_evidence_hash"
                ],
            )
        )

    def test_single_observer_does_not_form_admissible_quorum(self):
        evidence = conformance.evaluate_replay_cursor_provider_conformance_observer_quorum_v1(
            self.signed_reports[:1],
            self.conformance_fixture.plan_document,
            self.conformance_fixture.provider_preregistration_document,
            self.receipt_evidence,
            **self.upstream_kwargs,
        )
        context = {
            **self.conformance_context,
            "signed_report_documents": self.signed_reports[:1],
        }
        self.assertIsNone(
            self._evaluate_static(
                conformance_quorum_evidence_document=evidence,
                conformance_quorum_verification_context=context,
                expected_conformance_quorum_evidence_hash=evidence[
                    "quorum_evidence_hash"
                ],
            )
        )

    def test_tampered_identity_bridge_is_rejected(self):
        document = copy.deepcopy(self.identity_signed_receipt_bridge_document)
        document["permission_state"] = "ALLOWED"
        self.assertIsNone(
            self._evaluate_static(
                identity_bound_signed_receipt_bridge_document=document
            )
        )

    def test_tampered_quorum_evidence_is_rejected(self):
        evidence = copy.deepcopy(self.quorum_evidence)
        evidence["admission_status"] = "ALLOWED"
        self.assertIsNone(
            self._evaluate_static(conformance_quorum_evidence_document=evidence)
        )

    def test_expected_hash_drift_is_rejected(self):
        for field in (
            "expected_identity_bound_signed_receipt_bridge_hash",
            "expected_conformance_quorum_evidence_hash",
            "expected_signed_receipt_evidence_hash",
            "expected_conformance_plan_hash",
            "expected_provider_preregistration_hash",
        ):
            with self.subTest(field=field):
                self.assertIsNone(self._evaluate_static(**{field: "a" * 64}))

    def test_identity_context_alias_is_rejected(self):
        context = dict(self.identity_bridge_context)
        context["compatibility_alias"] = True
        self.assertIsNone(
            self._evaluate_static(
                identity_bound_signed_receipt_bridge_verification_context=context
            )
        )

    def test_conformance_context_alias_is_rejected(self):
        context = dict(self.conformance_context)
        context["compatibility_alias"] = True
        self.assertIsNone(
            self._evaluate_static(conformance_quorum_verification_context=context)
        )

    def test_registry_drift_is_rejected(self):
        context = dict(self.conformance_context)
        context["provider_preregistration_kwargs"] = {
            **self.conformance_fixture.provider_preregistration_kwargs,
            "registry_id": "synthetic-spliced-registry",
        }
        self.assertIsNone(
            self._evaluate_static(conformance_quorum_verification_context=context)
        )

    def test_mismatched_receipt_evidence_is_rejected(self):
        context = {
            **self.conformance_context,
            "signed_receipt_evidence_document": self.conformance_fixture.signed_receipt_evidence_document,
        }
        self.assertIsNone(
            self._evaluate_static(conformance_quorum_verification_context=context)
        )

    def test_shape_compatible_alias_is_rejected(self):
        alias = SimpleNamespace(**self.identity_signed_receipt_bridge_document)
        self.assertIsNone(
            self._evaluate_static(
                identity_bound_signed_receipt_bridge_document=alias
            )
        )

    def test_local_claims_never_promote_execution_or_conformance(self):
        facts = self.result["facts"]
        self.assertTrue(facts["local_observer_signature_quorum_exactly_verified"])
        self.assertFalse(facts["provider_called_by_bridge"])
        self.assertFalse(facts["provider_execution_verified"])
        self.assertFalse(facts["external_provider_conformance_verified"])
        self.assertFalse(facts["observer_identity_verified"])
        self.assertFalse(facts["observer_independence_verified"])
        self.assertFalse(facts["observer_test_execution_source_truth_verified"])

    def test_output_redacts_reports_cases_keys_and_signatures(self):
        forbidden_keys = {
            "signed_report_documents",
            "observer_results",
            "cases",
            "case_rows",
            "public_key_spki_base64",
            "signature_base64",
            "signed_receipt_document",
            "receipt_document",
        }
        self.assertTrue(forbidden_keys.isdisjoint(set(_nested_keys(self.result))))
        serialized = json.dumps(self.result, sort_keys=True)
        self.assertNotIn(self.receipt_signature_base64, serialized)
        for signed_report in self.signed_reports:
            self.assertNotIn(signed_report["signature_base64"], serialized)
            self.assertNotIn(signed_report["public_key_spki_base64"], serialized)
        self.assertFalse(self.result["facts"]["raw_observer_reports_exposed"])
        self.assertFalse(
            self.result["facts"]["observer_key_or_signature_material_exposed"]
        )


if __name__ == "__main__":
    unittest.main()
