from __future__ import annotations

import copy
from hashlib import sha256
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4
    as evidence_v4,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1
    as issuance_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_verification_envelope_v1
    as envelope_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7
    as registration_v7,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_receipt_v4 as receipt_test_support


class PostRegistrationPreregistrationVerificationEnvelopeV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        case = receipt_test_support.PortfolioRiskPresentationConsumerExecutionReceiptV4Tests(
            "test_python_clear_projection_produces_exact_local_receipt"
        )
        case.setUp()
        cls.addClassCleanup(case.doCleanups)
        manifest = (
            registration_v7.expected_presentation_consumer_implementation_sha256_v7()
        )
        cls._bundles = {}
        for state, projection in (
            ("CLEAR", case._projection()),
            ("TAIL_BLOCK", case._projection(coupled=True)),
            ("EXACT_UNKNOWN", case._projection(observations=[])),
        ):
            node = case._node(projection, f"envelope-v1-{state.lower()}")
            evidence = evidence_v4.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4(
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
            )
            registration = registration_v7.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7(
                manifest,
                evidence,
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
            )
            issuance_id = f"verification-envelope-{state.lower()}-0001"
            commitment = sha256(
                f"synthetic-envelope-nonce-{state}".encode("ascii")
            ).hexdigest()
            preregistration = issuance_v1.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1(
                registration,
                manifest,
                evidence,
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
                issuance_id,
                commitment,
            )
            cls._bundles[state] = (
                preregistration,
                registration,
                manifest,
                evidence,
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
                issuance_id,
                commitment,
            )

    def _inputs(self, state: str = "CLEAR") -> tuple:
        return copy.deepcopy(self._bundles[state])

    def _build(self, inputs: tuple | None = None) -> dict:
        return envelope_v1.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_verification_envelope_v1(
            *(self._inputs() if inputs is None else inputs)
        )

    def test_public_versions_and_underlying_implementation_pin_are_exact(
        self,
    ) -> None:
        self.assertTrue(envelope_v1.SCHEMA_VERSION.endswith("envelope-v1"))
        self.assertEqual(
            envelope_v1.ISSUANCE_PREREGISTRATION_V1_IMPLEMENTATION_SHA256,
            "76a1c05a55395c3258869336b0d00b8e1613670befea35f6152be6947016e6ce",
        )

    def test_exact_preregistration_builds_pass_summary_envelope(self) -> None:
        inputs = self._inputs()
        envelope = self._build(inputs)
        self.assertEqual(envelope["status"], "PASS")
        self.assertEqual(
            envelope["verification"]["underlying_preregistration_status"],
            "BLOCKED",
        )
        self.assertEqual(
            envelope["source"]["issuance_preregistration_hash"],
            inputs[0]["preregistration_hash"],
        )
        self.assertEqual(
            envelope["source"]["anti_replay_scope_hash"],
            inputs[0]["anti_replay"]["scope_hash"],
        )

    def test_three_execution_semantics_are_preserved(self) -> None:
        for state in ("CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN"):
            with self.subTest(state=state):
                envelope = self._build(self._inputs(state))
                self.assertEqual(envelope["status"], "PASS")
                self.assertEqual(
                    envelope["source"]["execution_semantic_state"],
                    state,
                )
                self.assertFalse(
                    envelope["authority"][
                        "witness_candidate_activation_allowed"
                    ]
                )

    def test_resealed_preregistration_authority_promotion_blocks_envelope(
        self,
    ) -> None:
        inputs = list(self._inputs())
        inputs[0]["authority"]["paper_authorized"] = True
        inputs[0] = seal_strict_canonical_document(
            inputs[0],
            "preregistration_hash",
        )
        envelope = self._build(tuple(inputs))
        self.assertEqual(envelope["status"], "BLOCK")
        self.assertIn(
            "issuance_preregistration_v1_public_verifier_pass",
            envelope["blockers"],
        )
        self.assertIn(
            "issuance_preregistration_authority_locked",
            envelope["blockers"],
        )

    def test_registration_substitution_breaks_hash_edge_and_verifier(self) -> None:
        inputs = list(self._inputs("CLEAR"))
        inputs[1] = self._inputs("TAIL_BLOCK")[1]
        envelope = self._build(tuple(inputs))
        self.assertEqual(envelope["status"], "BLOCK")
        self.assertIn(
            "registration_v7_hash_edge_exact",
            envelope["blockers"],
        )

    def test_issuance_id_or_commitment_substitution_blocks_scope(self) -> None:
        for index, value in ((8, "verification-envelope-clear-9999"), (9, "a" * 64)):
            with self.subTest(index=index):
                inputs = list(self._inputs())
                inputs[index] = value
                envelope = self._build(tuple(inputs))
                self.assertEqual(envelope["status"], "BLOCK")
                self.assertIn(
                    "issuance_id_commitment_and_scope_hash_bound",
                    envelope["blockers"],
                )

    def test_resealed_target_schema_alias_blocks_envelope(self) -> None:
        inputs = list(self._inputs())
        inputs[0]["issuance"]["target_challenge_schema_version"] = (
            "portfolio-risk-execution-witness-document-bundle-challenge-v1"
        )
        inputs[0] = seal_strict_canonical_document(
            inputs[0],
            "preregistration_hash",
        )
        envelope = self._build(tuple(inputs))
        self.assertEqual(envelope["status"], "BLOCK")
        self.assertIn("future_target_schemas_exact", envelope["blockers"])

    def test_resealed_registry_claim_blocks_envelope(self) -> None:
        inputs = list(self._inputs())
        inputs[0]["anti_replay"]["registry_bound"] = True
        inputs[0]["facts"]["external_anti_replay_registry_bound"] = True
        inputs[0] = seal_strict_canonical_document(
            inputs[0],
            "preregistration_hash",
        )
        envelope = self._build(tuple(inputs))
        self.assertEqual(envelope["status"], "BLOCK")
        self.assertIn(
            "anti_replay_registry_remains_explicitly_unbound",
            envelope["blockers"],
        )

    def test_public_verifier_accepts_exact_envelope_and_rejects_tamper(
        self,
    ) -> None:
        inputs = self._inputs()
        envelope = self._build(inputs)
        verification = envelope_v1.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_verification_envelope_v1(
            envelope,
            *inputs,
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(
            verification["underlying_preregistration_status"],
            "BLOCKED",
        )
        tampered = copy.deepcopy(envelope)
        tampered["authority"]["writer_allowed"] = True
        tampered = seal_strict_canonical_document(tampered, "envelope_hash")
        verification = envelope_v1.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_verification_envelope_v1(
            tampered,
            *inputs,
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_envelope_is_summary_only_and_does_not_execute_node(self) -> None:
        envelope = self._build()
        self.assertTrue(
            envelope["facts"]["local_python_verification_execution_observed"]
        )
        self.assertFalse(envelope["facts"]["node_process_executed"])
        self.assertFalse(envelope["facts"]["signature_verified"])
        self.assertFalse(envelope["facts"]["raw_nonce_received"])
        self.assertFalse(
            envelope["facts"]["preregistration_document_embedded"]
        )
        self.assertFalse(envelope["facts"]["registration_document_embedded"])
        self.assertFalse(
            envelope["facts"]["execution_evidence_document_embedded"]
        )
        self.assertFalse(envelope["facts"]["profitability_proven"])
        promotion = "\\b" + "R" + "EADY" + "\\b"
        self.assertNotRegex(json.dumps(envelope), promotion)


if __name__ == "__main__":
    unittest.main()
