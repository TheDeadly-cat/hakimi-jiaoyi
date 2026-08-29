from __future__ import annotations

import base64
import copy
import dataclasses
import json
from types import SimpleNamespace
import unittest

from exchange_terminal.application import (
    strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1
    as bridge,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_receipt_v1
    as signed_provider_receipt,
)
from exchange_terminal.application.ports import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1
    as replay_cursor_provider,
)
from tests.test_strategy_correlation_identity_bound_position_derived_replay_cursor_cas_bridge_candidate_v1 import (
    StrategyCorrelationIdentityBoundPositionDerivedReplayCursorCasBridgeCandidateV1Tests
    as IdentityBoundCasFixture,
)
from tests.test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_receipt_v1 import (
    ReplayCursorProviderSignedReceiptV1Tests as SignedReceiptFixture,
)


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


class StrategyCorrelationIdentityBoundSignedReplayCursorProviderReceiptBridgeCandidateV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        IdentityBoundCasFixture.setUpClass()
        SignedReceiptFixture.setUpClass()
        signed_case = SignedReceiptFixture(
            "test_valid_preregistered_key_receipt_is_local_only"
        )
        signed_case.setUp()

        cls.identity_fixture = IdentityBoundCasFixture
        cls.signed_fixture = SignedReceiptFixture
        cls.signed_case = signed_case
        cls.cas_result = IdentityBoundCasFixture.cas_result
        cls.identity_bridge_document = IdentityBoundCasFixture.bridge

        command_payload = replay_cursor_provider._command_payload(
            stream_id=cls.cas_result.stream_id,
            projection_preregistration_hash=cls.cas_result.projection_preregistration_hash,
            intent_hash=cls.cas_result.intent_hash,
            freshness_result_fingerprint_sha256=cls.cas_result.freshness_result_fingerprint_sha256,
            candidate_attestation_hash=cls.cas_result.attestation_hash,
            candidate_sequence=cls.cas_result.candidate_sequence,
            request_nonce_hash=cls.cas_result.request_nonce_hash,
            transition_receipt_hash=cls.cas_result.receipt_hash,
            base_cursor=IdentityBoundCasFixture.base_cursor,
            proposed_cursor=cls.cas_result.returned_cursor,
        )
        cls.command = replay_cursor_provider.ReplayCursorCompareAndAdvanceCommandV1(
            stream_id=cls.cas_result.stream_id,
            projection_preregistration_hash=cls.cas_result.projection_preregistration_hash,
            intent_hash=cls.cas_result.intent_hash,
            freshness_result_fingerprint_sha256=cls.cas_result.freshness_result_fingerprint_sha256,
            candidate_attestation_hash=cls.cas_result.attestation_hash,
            candidate_sequence=cls.cas_result.candidate_sequence,
            request_nonce_hash=cls.cas_result.request_nonce_hash,
            transition_receipt_hash=cls.cas_result.receipt_hash,
            base_cursor=IdentityBoundCasFixture.base_cursor,
            proposed_cursor=cls.cas_result.returned_cursor,
            command_hash=replay_cursor_provider._hash_payload(command_payload),
            schema_version=command_payload["schema_version"],
        )

        old_command = signed_case.command
        old_result = signed_case.result
        replacements = {
            old_command.command_hash: cls.command.command_hash,
            old_command.intent_hash: cls.command.intent_hash,
            old_command.base_cursor.cursor_hash: cls.cas_result.observed_cursor_hash,
            old_command.proposed_cursor.cursor_hash: cls.cas_result.returned_cursor_hash,
        }
        cls.provider_result = dataclasses.replace(
            old_result,
            outcome=replay_cursor_provider.ReplayCursorProviderOutcomeV1.ADVANCED,
            command_hash=cls.command.command_hash,
            intent_hash=cls.command.intent_hash,
            observed_cursor_hash=cls.cas_result.observed_cursor_hash,
            returned_cursor_hash=cls.cas_result.returned_cursor_hash,
            receipt_document=_replace_strings(old_result.receipt_document, replacements),
        )

        cls.claim = signed_case._build_claim(
            command=cls.command,
            result=cls.provider_result,
        )
        cls.signature_base64 = base64.b64encode(
            SignedReceiptFixture.private_key.sign(
                bytes.fromhex(cls.claim["receipt_claim_hash"])
            )
        ).decode("ascii")
        cls.registration_evidence_hash = SignedReceiptFixture.registration_evidence_document[
            "verification_evidence_hash"
        ]
        cls.signed_document = signed_provider_receipt.build_signed_replay_cursor_provider_receipt_v1(
            cls.claim,
            cls.command,
            cls.provider_result,
            SignedReceiptFixture.registration_evidence_document,
            SignedReceiptFixture.signed_registration_document,
            SignedReceiptFixture.registration_claim_document,
            SignedReceiptFixture.preregistration_document,
            public_key_spki_base64=signed_case.public_key_spki_base64,
            signature_base64=cls.signature_base64,
            expected_receipt_claim_hash=cls.claim["receipt_claim_hash"],
            expected_registration_evidence_hash=cls.registration_evidence_hash,
            registration_verification_kwargs=SignedReceiptFixture.registration_verification_kwargs,
        )
        cls.receipt_evidence = signed_provider_receipt.evaluate_signed_replay_cursor_provider_receipt_v1(
            cls.signed_document,
            cls.claim,
            cls.command,
            cls.provider_result,
            SignedReceiptFixture.registration_evidence_document,
            SignedReceiptFixture.signed_registration_document,
            SignedReceiptFixture.registration_claim_document,
            SignedReceiptFixture.preregistration_document,
            public_key_spki_base64=signed_case.public_key_spki_base64,
            signature_base64=cls.signature_base64,
            expected_signed_receipt_hash=cls.signed_document["signed_receipt_hash"],
            expected_receipt_claim_hash=cls.claim["receipt_claim_hash"],
            expected_registration_evidence_hash=cls.registration_evidence_hash,
            registration_verification_kwargs=SignedReceiptFixture.registration_verification_kwargs,
        )

        cls.identity_context = {
            "identity_bound_result": IdentityBoundCasFixture.identity_result,
            "identity_bound_verification_context": IdentityBoundCasFixture.identity_context,
            "freshness_binding_result": IdentityBoundCasFixture.freshness_result,
            "freshness_binding_verification_context": IdentityBoundCasFixture.freshness_context,
            "replay_cursor_cas_binding_result": cls.cas_result,
            "attestation": IdentityBoundCasFixture.attestation,
            "base_cursor": IdentityBoundCasFixture.base_cursor,
            "observed_cursor": IdentityBoundCasFixture.base_cursor,
            "expected_identity_bound_post_merge_hash": IdentityBoundCasFixture.identity_result[
                "identity_bound_post_merge_hash"
            ],
            "expected_freshness_binding_hash": IdentityBoundCasFixture.freshness_result.binding_hash,
            "expected_replay_cursor_cas_binding_hash": cls.cas_result.binding_hash,
            "request_nonce_hash": IdentityBoundCasFixture.request_nonce_hash,
            "expected_observed_cursor_hash": cls.cas_result.observed_cursor_hash,
        }
        cls.signed_context = {
            "signed_receipt_document": cls.signed_document,
            "receipt_claim_document": cls.claim,
            "registration_evidence_document": SignedReceiptFixture.registration_evidence_document,
            "signed_registration_document": SignedReceiptFixture.signed_registration_document,
            "registration_claim_document": SignedReceiptFixture.registration_claim_document,
            "preregistration_document": SignedReceiptFixture.preregistration_document,
            "public_key_spki_base64": signed_case.public_key_spki_base64,
            "signature_base64": cls.signature_base64,
            "expected_signed_receipt_hash": cls.signed_document["signed_receipt_hash"],
            "expected_receipt_claim_hash": cls.claim["receipt_claim_hash"],
            "expected_registration_evidence_hash": cls.registration_evidence_hash,
            "registration_verification_kwargs": SignedReceiptFixture.registration_verification_kwargs,
        }
        cls.result = cls._evaluate_static()

    @classmethod
    def _evaluate_static(cls, **overrides):
        arguments = {
            "identity_bound_cas_bridge_document": cls.identity_bridge_document,
            "identity_bound_cas_verification_context": cls.identity_context,
            "replay_cursor_cas_binding_result": cls.cas_result,
            "provider_command": cls.command,
            "provider_result": cls.provider_result,
            "signed_receipt_evidence_document": cls.receipt_evidence,
            "signed_receipt_verification_context": cls.signed_context,
            "expected_identity_bound_cas_bridge_hash": cls.identity_bridge_document[
                "identity_bound_cas_bridge_hash"
            ],
            "expected_replay_cursor_cas_binding_hash": cls.cas_result.binding_hash,
            "expected_provider_command_hash": cls.command.command_hash,
            "expected_signed_receipt_verification_evidence_hash": cls.receipt_evidence[
                "verification_evidence_hash"
            ],
        }
        arguments.update(overrides)
        return bridge.evaluate_strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1(
            **arguments
        )

    @classmethod
    def _command_with(cls, **changes):
        values = {
            "stream_id": cls.command.stream_id,
            "projection_preregistration_hash": cls.command.projection_preregistration_hash,
            "intent_hash": cls.command.intent_hash,
            "freshness_result_fingerprint_sha256": cls.command.freshness_result_fingerprint_sha256,
            "candidate_attestation_hash": cls.command.candidate_attestation_hash,
            "candidate_sequence": cls.command.candidate_sequence,
            "request_nonce_hash": cls.command.request_nonce_hash,
            "transition_receipt_hash": cls.command.transition_receipt_hash,
            "base_cursor": cls.command.base_cursor,
            "proposed_cursor": cls.command.proposed_cursor,
        }
        values.update(changes)
        payload = replay_cursor_provider._command_payload(**values)
        return replay_cursor_provider.ReplayCursorCompareAndAdvanceCommandV1(
            **values,
            command_hash=replay_cursor_provider._hash_payload(payload),
            schema_version=payload["schema_version"],
        )

    def test_exact_identity_bound_signed_receipt_is_local_only(self):
        self.assertIsNotNone(self.result)
        self.assertEqual(self.result["status"], bridge.STATUS)
        self.assertEqual(self.result["decision"], bridge.DECISION)
        self.assertEqual(self.result["permission_state"], "BLOCKED")
        self.assertEqual(self.result["consumer_status"], "UNMOUNTED_CANDIDATE")
        self.assertEqual(self.result["provider"]["outcome"], "ADVANCED")
        self.assertTrue(all(value is False for value in self.result["authority"].values()))

    def test_verifier_reconstructs_exact_bridge(self):
        self.assertTrue(
            bridge.verify_strategy_correlation_identity_bound_signed_replay_cursor_provider_receipt_bridge_candidate_v1(
                self.result,
                self.identity_bridge_document,
                self.identity_context,
                self.cas_result,
                self.command,
                self.provider_result,
                self.receipt_evidence,
                self.signed_context,
                expected_identity_bound_signed_provider_receipt_bridge_hash=self.result[
                    "identity_bound_signed_provider_receipt_bridge_hash"
                ],
                expected_identity_bound_cas_bridge_hash=self.identity_bridge_document[
                    "identity_bound_cas_bridge_hash"
                ],
                expected_replay_cursor_cas_binding_hash=self.cas_result.binding_hash,
                expected_provider_command_hash=self.command.command_hash,
                expected_signed_receipt_verification_evidence_hash=self.receipt_evidence[
                    "verification_evidence_hash"
                ],
            )
        )

    def test_old_signed_fixture_identity_cannot_be_spliced(self):
        old_evidence = self.signed_case._evaluate()
        old_context = {
            **self.signed_context,
            "signed_receipt_document": self.signed_case.signed_document,
            "receipt_claim_document": self.signed_case.claim,
            "signature_base64": self.signed_case.signature_base64,
            "expected_signed_receipt_hash": self.signed_case.signed_document[
                "signed_receipt_hash"
            ],
            "expected_receipt_claim_hash": self.signed_case.claim[
                "receipt_claim_hash"
            ],
        }
        self.assertIsNone(
            self._evaluate_static(
                provider_command=self.signed_case.command,
                provider_result=self.signed_case.result,
                signed_receipt_evidence_document=old_evidence,
                signed_receipt_verification_context=old_context,
                expected_provider_command_hash=self.signed_case.command.command_hash,
                expected_signed_receipt_verification_evidence_hash=old_evidence[
                    "verification_evidence_hash"
                ],
            )
        )

    def test_command_intent_splice_is_rejected(self):
        command = self._command_with(intent_hash="a" * 64)
        self.assertIsNone(
            self._evaluate_static(
                provider_command=command,
                expected_provider_command_hash=command.command_hash,
            )
        )

    def test_command_transition_receipt_splice_is_rejected(self):
        command = self._command_with(transition_receipt_hash="b" * 64)
        self.assertIsNone(
            self._evaluate_static(
                provider_command=command,
                expected_provider_command_hash=command.command_hash,
            )
        )

    def test_provider_returned_cursor_splice_is_rejected(self):
        provider_result = dataclasses.replace(
            self.provider_result,
            returned_cursor_hash="c" * 64,
        )
        self.assertIsNone(self._evaluate_static(provider_result=provider_result))

    def test_provider_registry_splice_is_rejected_by_signed_receipt(self):
        provider_result = dataclasses.replace(
            self.provider_result,
            registry_id="synthetic-spliced-registry",
        )
        self.assertIsNone(self._evaluate_static(provider_result=provider_result))

    def test_rejected_provider_outcome_cannot_enter_success_bridge(self):
        provider_result = replay_cursor_provider.ReplayCursorCompareAndAdvanceResultV1(
            outcome=replay_cursor_provider.ReplayCursorProviderOutcomeV1.CONFLICT_REJECTED,
            command_hash=self.provider_result.command_hash,
            intent_hash=self.provider_result.intent_hash,
            registry_id=self.provider_result.registry_id,
            registry_revision=self.provider_result.registry_revision,
            observed_cursor_hash=self.provider_result.observed_cursor_hash,
            returned_cursor_hash=self.provider_result.observed_cursor_hash,
            receipt_document=self.provider_result.receipt_document,
            schema_version=self.provider_result.schema_version,
        )
        self.assertIsNone(self._evaluate_static(provider_result=provider_result))

    def test_modified_signed_evidence_is_rejected(self):
        evidence = copy.deepcopy(self.receipt_evidence)
        evidence["decision"] = "LOCAL_SIGNATURE_PROMOTED"
        self.assertIsNone(
            self._evaluate_static(signed_receipt_evidence_document=evidence)
        )

    def test_wrong_signature_is_rejected(self):
        context = {
            **self.signed_context,
            "signature_base64": base64.b64encode(b"\x00" * 64).decode("ascii"),
        }
        self.assertIsNone(
            self._evaluate_static(signed_receipt_verification_context=context)
        )

    def test_incomplete_verification_context_is_rejected(self):
        context = dict(self.identity_context)
        context.pop("observed_cursor")
        self.assertIsNone(
            self._evaluate_static(identity_bound_cas_verification_context=context)
        )

    def test_alias_objects_are_rejected(self):
        command_alias = SimpleNamespace(**dataclasses.asdict(self.command))
        self.assertIsNone(self._evaluate_static(provider_command=command_alias))

    def test_expected_hash_drift_is_rejected(self):
        self.assertIsNone(
            self._evaluate_static(expected_provider_command_hash="d" * 64)
        )

    def test_output_redacts_receipt_cursor_key_and_signature_material(self):
        forbidden_keys = {
            "receipt_document",
            "base_cursor",
            "proposed_cursor",
            "public_key_spki_base64",
            "signature_base64",
        }
        self.assertTrue(forbidden_keys.isdisjoint(set(_nested_keys(self.result))))
        serialized = json.dumps(self.result, sort_keys=True)
        self.assertNotIn(self.signature_base64, serialized)
        self.assertNotIn(self.signed_case.public_key_spki_base64, serialized)
        self.assertFalse(self.result["facts"]["raw_receipt_exposed"])
        self.assertFalse(self.result["facts"]["raw_cursor_exposed"])
        self.assertFalse(self.result["facts"]["signature_material_exposed"])


if __name__ == "__main__":
    unittest.main()
