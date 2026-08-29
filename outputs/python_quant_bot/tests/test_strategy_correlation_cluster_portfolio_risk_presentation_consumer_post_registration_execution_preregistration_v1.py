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
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7
    as registration_v7,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_receipt_v4 as receipt_test_support


class PostRegistrationExecutionPreregistrationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        case = receipt_test_support.PortfolioRiskPresentationConsumerExecutionReceiptV4Tests(
            "test_python_clear_projection_produces_exact_local_receipt"
        )
        case.setUp()
        cls.addClassCleanup(case.doCleanups)
        cls._bundles = {}
        manifest = (
            registration_v7.expected_presentation_consumer_implementation_sha256_v7()
        )
        for state, projection in (
            ("CLEAR", case._projection()),
            ("TAIL_BLOCK", case._projection(coupled=True)),
            ("EXACT_UNKNOWN", case._projection(observations=[])),
        ):
            node = case._node(projection, f"issuance-v1-{state.lower()}")
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
            cls._bundles[state] = (
                registration,
                manifest,
                evidence,
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
            )

    def setUp(self) -> None:
        self.issuance_id = "post-registration-v5-issuance-0001"
        self.commitment = sha256(
            b"synthetic-post-registration-v5-nonce-0001"
        ).hexdigest()

    def _inputs(self, state: str = "CLEAR") -> tuple[dict, dict, dict, dict, dict, dict, dict]:
        return copy.deepcopy(self._bundles[state])

    def _build(
        self,
        inputs: tuple[dict, dict, dict, dict, dict, dict, dict] | None = None,
        issuance_id: object | None = None,
        commitment: object | None = None,
    ) -> dict:
        values = self._inputs() if inputs is None else inputs
        return issuance_v1.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1(
            *values,
            self.issuance_id if issuance_id is None else issuance_id,
            self.commitment if commitment is None else commitment,
        )

    def test_exact_context_builds_blocked_single_use_preregistration(self) -> None:
        document = self._build()
        self.assertEqual(document["status"], "BLOCKED")
        self.assertTrue(document["facts"]["local_preregistration_complete"])
        self.assertEqual(len(document["closed_local_blockers"]), 5)
        self.assertEqual(
            document["anti_replay"]["required_registry_operation"],
            "ATOMIC_PUT_IF_ABSENT_THEN_CONSUME_ONCE",
        )
        self.assertEqual(document["anti_replay"]["challenge_use_limit"], 1)
        self.assertEqual(document["anti_replay"]["receipt_issue_limit"], 1)
        self.assertIn(
            "EXTERNAL_ANTI_REPLAY_REGISTRY_UNBOUND",
            document["blockers"],
        )

    def test_registration_evidence_and_pre_receipt_hashes_are_bound(self) -> None:
        inputs = self._inputs()
        document = self._build(inputs)
        self.assertEqual(
            document["source"]["registration_v7_hash"],
            inputs[0]["registration_hash"],
        )
        self.assertEqual(
            document["source"]["execution_evidence_v4_hash"],
            inputs[2]["evidence_hash"],
        )
        self.assertEqual(
            document["source"]["pre_registration_receipt_v4_hash"],
            inputs[3]["receipt_hash"],
        )

    def test_three_execution_semantics_remain_blocked_and_distinct(self) -> None:
        for state in ("CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN"):
            with self.subTest(state=state):
                document = self._build(self._inputs(state))
                self.assertTrue(
                    document["facts"]["local_preregistration_complete"]
                )
                self.assertEqual(
                    document["source"]["execution_semantic_state"],
                    state,
                )
                self.assertEqual(document["status"], "BLOCKED")
                self.assertFalse(
                    document["authority"][
                        "post_registration_receipt_issuance_allowed"
                    ]
                )

    def test_scope_changes_with_issuance_id_or_nonce_commitment(self) -> None:
        original = self._build()
        alternate_id = self._build(
            issuance_id="post-registration-v5-issuance-0002"
        )
        alternate_commitment = self._build(
            commitment=sha256(b"synthetic-alternate-nonce").hexdigest()
        )
        hashes = {
            original["anti_replay"]["scope_hash"],
            alternate_id["anti_replay"]["scope_hash"],
            alternate_commitment["anti_replay"]["scope_hash"],
        }
        self.assertEqual(len(hashes), 3)

    def test_deterministic_rebuild_does_not_claim_nonce_consumption(self) -> None:
        first = self._build()
        second = self._build()
        self.assertEqual(
            first["preregistration_hash"],
            second["preregistration_hash"],
        )
        self.assertFalse(first["anti_replay"]["registry_bound"])
        self.assertFalse(
            first["anti_replay"]["atomic_consumption_verified"]
        )
        self.assertFalse(first["anti_replay"]["duplicate_rejection_verified"])

    def test_invalid_issuance_ids_and_commitments_fail_closed(self) -> None:
        cases = (
            {"issuance_id": ""},
            {"issuance_id": "Contains Spaces"},
            {"commitment": "0" * 64},
            {"commitment": "f" * 64},
            {"commitment": "not-a-hash"},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                document = self._build(**kwargs)
                self.assertFalse(
                    document["facts"]["local_preregistration_complete"]
                )
                self.assertEqual(document["closed_local_blockers"], [])

    def test_resealed_registration_authority_promotion_blocks_context(self) -> None:
        inputs = list(self._inputs())
        inputs[0]["authority"]["paper_authorized"] = True
        inputs[0] = seal_strict_canonical_document(
            inputs[0],
            "registration_hash",
        )
        document = self._build(tuple(inputs))
        self.assertFalse(document["facts"]["local_preregistration_complete"])
        self.assertEqual(
            document["source"]["registration_v7_schema_version"],
            "UNKNOWN",
        )

    def test_evidence_substitution_breaks_registration_rebuild(self) -> None:
        inputs = list(self._inputs("CLEAR"))
        inputs[2] = self._inputs("TAIL_BLOCK")[2]
        document = self._build(tuple(inputs))
        self.assertFalse(document["facts"]["local_preregistration_complete"])
        self.assertIn(
            "LOCAL_PREREGISTRATION_CHECK_FAILED:registration_v7_exact_blocked_candidate",
            document["blockers"],
        )

    def test_target_schema_alias_reseal_is_rejected_by_public_verifier(
        self,
    ) -> None:
        inputs = self._inputs()
        document = self._build(inputs)
        alias = copy.deepcopy(document)
        alias["issuance"]["target_receipt_schema_version"] = (
            "portfolio-risk-joint-evidence-consumer-execution-receipt-v3"
        )
        alias = seal_strict_canonical_document(alias, "preregistration_hash")
        verification = issuance_v1.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1(
            alias,
            *inputs,
            self.issuance_id,
            self.commitment,
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_public_verifier_accepts_exact_blocked_preregistration(self) -> None:
        inputs = self._inputs()
        document = self._build(inputs)
        verification = issuance_v1.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1(
            document,
            *inputs,
            self.issuance_id,
            self.commitment,
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["preregistration_status"], "BLOCKED")
        self.assertEqual(verification["execution_semantic_state"], "CLEAR")
        self.assertFalse(verification["anti_replay_registry_bound"])
        self.assertFalse(verification["post_registration_receipt_issued"])

    def test_resealed_preregistration_authority_promotion_is_rejected(
        self,
    ) -> None:
        inputs = self._inputs()
        document = self._build(inputs)
        promoted = copy.deepcopy(document)
        promoted["authority"][
            "post_registration_receipt_issuance_allowed"
        ] = True
        promoted = seal_strict_canonical_document(
            promoted,
            "preregistration_hash",
        )
        verification = issuance_v1.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1(
            promoted,
            *inputs,
            self.issuance_id,
            self.commitment,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(
            verification["post_registration_receipt_issuance_allowed"]
        )

    def test_preregistration_is_summary_only_without_nonce_or_authority(self) -> None:
        document = self._build()
        self.assertFalse(document["facts"]["raw_nonce_received"])
        self.assertFalse(document["facts"]["nonce_entropy_verified"])
        self.assertFalse(document["facts"]["nonce_material_embedded"])
        self.assertFalse(
            document["facts"]["external_anti_replay_registry_bound"]
        )
        self.assertFalse(document["facts"]["runtime_assets_accessed"])
        self.assertFalse(document["facts"]["network_accessed"])
        self.assertFalse(document["facts"]["ui_mounted"])
        self.assertFalse(document["facts"]["profitability_proven"])
        serialized = json.dumps(document)
        self.assertNotIn("synthetic-post-registration-v5-nonce-0001", serialized)
        promotion = "\\b" + "R" + "EADY" + "\\b"
        self.assertNotRegex(serialized, promotion)


if __name__ == "__main__":
    unittest.main()
