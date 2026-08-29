from __future__ import annotations

import copy
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4
    as evidence_v4,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6
    as registration_v6,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7
    as registration_v7,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_receipt_v4 as receipt_test_support


class PortfolioRiskPresentationConsumerRegistrationV7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        case = receipt_test_support.PortfolioRiskPresentationConsumerExecutionReceiptV4Tests(
            "test_python_clear_projection_produces_exact_local_receipt"
        )
        case.setUp()
        cls.addClassCleanup(case.doCleanups)
        cls._bundles = {}
        for name, projection in (
            ("CLEAR", case._projection()),
            ("TAIL_BLOCK", case._projection(coupled=True)),
            ("EXACT_UNKNOWN", case._projection(observations=[])),
        ):
            node = case._node(projection, f"registration-v7-{name.lower()}")
            evidence = evidence_v4.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4(
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
            )
            cls._bundles[name] = (
                evidence,
                node["receipt"],
                node["verification"],
                projection,
                node["preregistration"],
            )

    def setUp(self) -> None:
        self.manifest = (
            registration_v7.expected_presentation_consumer_implementation_sha256_v7()
        )

    def _inputs(self, name: str = "CLEAR") -> tuple[dict, dict, dict, dict, dict]:
        return copy.deepcopy(self._bundles[name])

    def _build(
        self,
        inputs: tuple[dict, dict, dict, dict, dict] | None = None,
        manifest: dict | None = None,
    ) -> dict:
        evidence, receipt, verification, projection, preregistration = (
            self._inputs() if inputs is None else inputs
        )
        return registration_v7.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7(
            self.manifest if manifest is None else manifest,
            evidence,
            receipt,
            verification,
            projection,
            preregistration,
        )

    def test_expected_delta_manifest_has_exact_twenty_six_pins(self) -> None:
        self.assertEqual(len(self.manifest), 26)
        self.assertEqual(
            self.manifest["presentation_registration_v6"],
            "061bae89a89ca090ab3565ff706e5144902f6a1083df970fad172245538d8e60",
        )
        self.assertEqual(
            self.manifest["downside_tail_execution_evidence_v4_py"],
            "c1e9bb3f122dd94cb6fd45a9eb1f1c40ecefc539a2af9d12be5f680c5a3819b5",
        )
        for value in self.manifest.values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_exact_chain_builds_blocked_candidate_with_local_closures(
        self,
    ) -> None:
        document = self._build()
        self.assertEqual(document["status"], "BLOCKED")
        self.assertTrue(document["source"]["local_contract_complete"])
        self.assertEqual(len(document["closed_local_blockers"]), 6)
        self.assertIn(
            "POST_REGISTRATION_EXECUTION_RECEIPT_NOT_ISSUED",
            document["blockers"],
        )
        self.assertFalse(document["facts"]["registration_activated"])
        self.assertFalse(document["authority"]["current_admission_allowed"])

    def test_predecessor_registration_v6_hash_is_exactly_rebuilt(self) -> None:
        predecessor = registration_v6.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6(
            registration_v6.expected_presentation_consumer_implementation_sha256_v6()
        )
        document = self._build()
        self.assertEqual(
            document["consumer"]["predecessor_registration_hash"],
            predecessor["registration_hash"],
        )
        self.assertEqual(
            document["contract_pins"]["predecessor_registration_hash"],
            predecessor["registration_hash"],
        )

    def test_clear_tail_block_and_exact_unknown_are_preserved_not_promoted(
        self,
    ) -> None:
        for state in ("CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN"):
            with self.subTest(state=state):
                document = self._build(self._inputs(state))
                self.assertEqual(document["status"], "BLOCKED")
                self.assertTrue(document["source"]["local_contract_complete"])
                self.assertEqual(
                    document["consumer"]["execution_semantic_state"],
                    state,
                )
                self.assertFalse(document["facts"]["registration_activated"])
                self.assertFalse(document["authority"]["paper_authorized"])

    def test_pre_registration_receipt_absence_requires_future_receipt(
        self,
    ) -> None:
        document = self._build()
        self.assertTrue(
            document["contract_pins"][
                "pre_registration_receipt_formal_registration_absent"
            ]
        )
        self.assertIsNone(
            document["consumer"][
                "pre_registration_receipt_formal_registration_hash"
            ]
        )
        self.assertTrue(
            document["facts"]["post_registration_execution_receipt_required"]
        )
        self.assertFalse(
            document["facts"]["post_registration_execution_receipt_issued"]
        )

    def test_resealed_evidence_authority_promotion_blocks_local_completion(
        self,
    ) -> None:
        inputs = list(self._inputs())
        inputs[0]["authority"]["paper_authorized"] = True
        inputs[0] = seal_strict_canonical_document(inputs[0], "evidence_hash")
        document = self._build(tuple(inputs))
        self.assertEqual(document["status"], "BLOCKED")
        self.assertFalse(document["source"]["local_contract_complete"])
        self.assertIn("EXECUTION_EVIDENCE_V4_NOT_EXACT", document["blockers"])
        self.assertEqual(document["closed_local_blockers"], [])

    def test_formal_registration_insertion_does_not_backfill_receipt(self) -> None:
        inputs = list(self._inputs())
        inputs[1]["source"]["formal_registration_schema_version"] = (
            registration_v7.SCHEMA_VERSION
        )
        inputs[1]["source"]["formal_registration_hash"] = "f" * 64
        inputs[1] = seal_strict_canonical_document(inputs[1], "receipt_hash")
        document = self._build(tuple(inputs))
        self.assertFalse(document["source"]["local_contract_complete"])
        self.assertIn(
            "PRE_REGISTRATION_RECEIPT_FORMAL_ABSENCE_NOT_EXACT",
            document["blockers"],
        )
        self.assertFalse(
            document["facts"][
                "pre_registration_receipt_formal_registration_bound"
            ]
        )

    def test_projection_substitution_breaks_evidence_binding(self) -> None:
        inputs = list(self._inputs("CLEAR"))
        alternate = self._inputs("TAIL_BLOCK")
        inputs[3] = alternate[3]
        document = self._build(tuple(inputs))
        self.assertFalse(document["source"]["local_contract_complete"])
        self.assertIn("EXECUTION_EVIDENCE_V4_NOT_EXACT", document["blockers"])

    def test_missing_extra_and_substituted_manifest_values_fail_closed(
        self,
    ) -> None:
        missing = copy.deepcopy(self.manifest)
        missing.pop("downside_tail_execution_evidence_v4_test_py")
        extra = copy.deepcopy(self.manifest)
        extra["unexpected"] = "f" * 64
        wrong = copy.deepcopy(self.manifest)
        wrong["portfolio_risk_adapter_v6"] = "f" * 64
        for manifest in (missing, extra, wrong):
            with self.subTest(keys=len(manifest)):
                document = self._build(manifest=manifest)
                self.assertFalse(document["source"]["local_contract_complete"])
                self.assertIn(
                    "IMPLEMENTATION_DELTA_MANIFEST_MISMATCH",
                    document["blockers"],
                )
                self.assertEqual(document["closed_local_blockers"], [])

    def test_resealed_legacy_evidence_schema_is_not_promoted(self) -> None:
        inputs = list(self._inputs())
        inputs[0]["schema_version"] = (
            "strategy-correlation-cluster-portfolio-risk-presentation-"
            "consumer-execution-evidence-v3"
        )
        inputs[0] = seal_strict_canonical_document(inputs[0], "evidence_hash")
        document = self._build(tuple(inputs))
        self.assertFalse(document["source"]["execution_evidence_v4_exact"])
        self.assertEqual(
            document["consumer"]["execution_evidence_schema_version"],
            "UNKNOWN",
        )

    def test_public_verifier_accepts_exact_blocked_candidate(self) -> None:
        inputs = self._inputs()
        document = self._build(inputs)
        verification = registration_v7.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7(
            document,
            self.manifest,
            *inputs,
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["registration_status"], "BLOCKED")
        self.assertEqual(verification["execution_semantic_state"], "CLEAR")
        self.assertFalse(verification["formal_registry_activated"])
        self.assertFalse(
            verification["post_registration_execution_receipt_issued"]
        )

    def test_public_verifier_rejects_resealed_authority_promotion(self) -> None:
        inputs = self._inputs()
        document = self._build(inputs)
        promoted = copy.deepcopy(document)
        promoted["authority"]["presentation_mount_allowed"] = True
        promoted = seal_strict_canonical_document(
            promoted,
            "registration_hash",
        )
        verification = registration_v7.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7(
            promoted,
            self.manifest,
            *inputs,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["presentation_mount_allowed"])

    def test_registration_is_summary_only_and_non_authoritative(self) -> None:
        document = self._build()
        self.assertFalse(document["source"]["artifact_files_read"])
        self.assertFalse(document["source"]["artifacts_executed"])
        self.assertFalse(document["source"]["supplied_manifest_embedded"])
        self.assertFalse(document["facts"]["runtime_assets_accessed"])
        self.assertFalse(document["facts"]["runtime_consumer_bound"])
        self.assertFalse(document["facts"]["ui_mounted"])
        self.assertFalse(
            document["facts"]["implementation_hashes_runtime_verified"]
        )
        self.assertFalse(document["facts"]["profitability_proven"])
        promotion = "\\b" + "R" + "EADY" + "\\b"
        self.assertNotRegex(json.dumps(document), promotion)


if __name__ == "__main__":
    unittest.main()
