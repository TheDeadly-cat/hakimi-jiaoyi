from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v8
    as registration_v8,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9
    as registration_v9,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v8 as registration_v8_support


ROOT = Path(__file__).resolve().parents[1]


class PortfolioRiskPresentationConsumerRegistrationV9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        support_type = (
            registration_v8_support.PortfolioRiskPresentationConsumerRegistrationV8Tests
        )
        support_type.setUpClass()
        cls.support_type = support_type
        cls.assets_v8 = registration_v8.expected_presentation_asset_sha256_v8()
        cls.assets_v9 = registration_v9.expected_presentation_asset_sha256_v9()

    def _chain(self, state: str = "CLEAR") -> tuple:
        v8_support = self.support_type()
        support, inputs, registration_v7_document = v8_support._bundle(state)
        registration_v8_document = registration_v8.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v8(
            registration_v7_document,
            support.manifest,
            *inputs,
            self.assets_v8,
        )
        return (
            support,
            inputs,
            registration_v7_document,
            registration_v8_document,
        )

    def _build(
        self,
        state: str = "CLEAR",
        assets: dict | None = None,
    ) -> dict:
        support, inputs, registration_v7_document, registration_v8_document = (
            self._chain(state)
        )
        return registration_v9.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9(
            registration_v8_document,
            registration_v7_document,
            support.manifest,
            *inputs,
            self.assets_v8,
            assets if assets is not None else self.assets_v9,
        )

    def test_exact_chain_builds_blocked_unmounted_registration_v9(self) -> None:
        document = self._build()
        self.assertEqual(document["status"], "BLOCKED")
        self.assertEqual(document["consumer"]["fixture_status"], "UNMOUNTED")
        self.assertTrue(document["source"]["local_contract_complete"])
        self.assertTrue(document["source"]["predecessor_registration_v8_exact"])
        self.assertFalse(document["facts"]["route_bound"])
        self.assertFalse(document["facts"]["browser_visual_review_performed"])
        self.assertFalse(
            document["facts"]["registry_organization_identity_verified"]
        )

    def test_three_semantic_states_remain_distinct_and_blocked(self) -> None:
        documents = [
            self._build(state)
            for state in ("CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN")
        ]
        self.assertEqual(
            len({document["registration_hash"] for document in documents}),
            3,
        )
        self.assertTrue(
            all(document["status"] == "BLOCKED" for document in documents)
        )
        self.assertTrue(
            all(
                document["consumer"]["fixture_status"] == "UNMOUNTED"
                for document in documents
            )
        )

    def test_asset_manifest_has_exact_six_v2_pins_and_current_hashes(self) -> None:
        paths = {
            "anti_replay_gap_card_v2_js": (
                ROOT
                / "exchange_terminal"
                / "static"
                / "evidence_anti_replay_registry_gap_card_v2.js"
            ),
            "anti_replay_gap_consumer_fixture_v2_js": (
                ROOT
                / "exchange_terminal"
                / "static"
                / "evidence_anti_replay_registry_gap_consumer_fixture_v2.js"
            ),
            "anti_replay_gap_cross_runtime_test_v2_py": (
                ROOT
                / "tests"
                / "test_anti_replay_registry_gap_presentation_cross_runtime_v2.py"
            ),
            "anti_replay_gap_presentation_adr_0246": (
                ROOT
                / "docs"
                / "adr"
                / "0246-neutral-registry-identity-evidence-gap-presentation-v2.md"
            ),
            "anti_replay_gap_presentation_test_v2_js": (
                ROOT
                / "exchange_terminal"
                / "static"
                / "evidence_anti_replay_registry_gap_presentation_v2.test.js"
            ),
            "anti_replay_gap_projection_v2_js": (
                ROOT
                / "exchange_terminal"
                / "static"
                / "evidence_anti_replay_registry_gap_projection_v2.js"
            ),
        }
        self.assertEqual(set(paths), set(self.assets_v9))
        self.assertEqual(len(paths), 6)
        for name, path in paths.items():
            with self.subTest(name=name):
                self.assertEqual(
                    sha256(path.read_bytes()).hexdigest(),
                    self.assets_v9[name],
                )

    def test_missing_extra_and_substituted_v2_assets_fail_closed(self) -> None:
        cases = []
        missing = dict(self.assets_v9)
        missing.pop(next(iter(missing)))
        cases.append(missing)
        extra = dict(self.assets_v9)
        extra["unexpected"] = "0" * 64
        cases.append(extra)
        substituted = dict(self.assets_v9)
        substituted["anti_replay_gap_card_v2_js"] = "f" * 64
        cases.append(substituted)
        for manifest in cases:
            with self.subTest(keys=sorted(manifest)):
                with self.assertRaises(ValueError):
                    self._build(assets=manifest)

    def test_registration_is_summary_only_and_non_authoritative(self) -> None:
        document = self._build()
        self.assertTrue(
            all(value is False for value in document["authority"].values())
        )
        self.assertFalse(document["source"]["artifact_files_read"])
        self.assertFalse(document["source"]["artifacts_executed"])
        self.assertTrue(document["source"]["static_source_only"])
        self.assertFalse(document["facts"]["current_artifact_written"])
        self.assertFalse(document["facts"]["paper_authorized"])
        self.assertFalse(document["facts"]["writer_allowed"])
        self.assertFalse(document["facts"]["external_source_trust_verified"])
        self.assertFalse(document["facts"]["signer_role_identity_verified"])

    def test_v2_consumer_reuses_frozen_v1_stylesheet(self) -> None:
        document = self._build()
        self.assertEqual(
            document["consumer"]["stylesheet_asset"],
            "evidence_anti_replay_registry_gap_card_v1.css",
        )
        self.assertTrue(
            document["consumer"]["stylesheet_reused_without_modification"]
        )
        self.assertEqual(
            document["contract_pins"]["reused_v1_stylesheet_sha256"],
            "8df1da62171147843bc655f07c79090d1176d16a8b3186c4f83390e3e02e08ad",
        )
        self.assertEqual(
            document["consumer"]["identity_evidence_local_observation_count"],
            2,
        )
        self.assertEqual(
            document["consumer"]["identity_evidence_unverified_count"],
            6,
        )

    def test_public_verifier_accepts_exact_blocked_registration_v9(self) -> None:
        support, inputs, registration_v7_document, registration_v8_document = (
            self._chain()
        )
        document = registration_v9.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9(
            registration_v8_document,
            registration_v7_document,
            support.manifest,
            *inputs,
            self.assets_v8,
            self.assets_v9,
        )
        exact = registration_v9.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9(
            document,
            registration_v8_document,
            registration_v7_document,
            support.manifest,
            *inputs,
            self.assets_v8,
            self.assets_v9,
        )
        self.assertEqual(exact["status"], "PASS")
        self.assertEqual(exact["registration_status"], "BLOCKED")
        self.assertEqual(exact["fixture_status"], "UNMOUNTED")
        self.assertFalse(exact["route_bound"])
        self.assertFalse(exact["registry_identity_admission_allowed"])
        self.assertFalse(exact["presentation_mount_allowed"])
        self.assertFalse(exact["paper_authorized"])
        self.assertFalse(exact["live_order_allowed"])

    def test_resealed_authority_promotion_fails_exact_rebuild(self) -> None:
        support, inputs, registration_v7_document, registration_v8_document = (
            self._chain()
        )
        document = registration_v9.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9(
            registration_v8_document,
            registration_v7_document,
            support.manifest,
            *inputs,
            self.assets_v8,
            self.assets_v9,
        )
        body = deepcopy(document)
        body.pop("registration_hash")
        body["authority"]["presentation_mount_allowed"] = True
        promoted = seal_strict_canonical_document(body, "registration_hash")
        exact = registration_v9.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9(
            promoted,
            registration_v8_document,
            registration_v7_document,
            support.manifest,
            *inputs,
            self.assets_v8,
            self.assets_v9,
        )
        self.assertEqual(exact["status"], "BLOCK")
        self.assertEqual(exact["registration_status"], "UNKNOWN")
        self.assertFalse(exact["presentation_mount_allowed"])

    def test_predecessor_substitution_fails_closed(self) -> None:
        support, inputs, registration_v7_document, _ = self._chain("CLEAR")
        _, _, _, other_v8 = self._chain("TAIL_BLOCK")
        with self.assertRaises(ValueError):
            registration_v9.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9(
                other_v8,
                registration_v7_document,
                support.manifest,
                *inputs,
                self.assets_v8,
                self.assets_v9,
            )


if __name__ == "__main__":
    unittest.main()
