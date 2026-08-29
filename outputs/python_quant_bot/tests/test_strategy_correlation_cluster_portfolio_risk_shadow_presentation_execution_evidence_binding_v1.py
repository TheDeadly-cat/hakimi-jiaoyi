from __future__ import annotations

import copy
import hashlib
import inspect
import json
import unittest
from unittest import mock

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1
    as subject,
)


FIXTURE_HASH = "1" * 64
PROJECTION_IMPL_HASH = "2" * 64
CARD_HASH = "3" * 64
PROJECTION_DOCUMENT_HASH = "4" * 64
DESCRIPTOR_HASH = "5" * 64
RECEIPT_HASH = "6" * 64


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _passing_receipt(*_args: object, **_kwargs: object) -> dict[str, object]:
    return {
        "schema": "upstream-verification",
        "status": "PASS",
        "verified": True,
        "checks": {"exact_rebuild_match": True, "authority_locked": True},
    }


class ShadowPresentationExecutionEvidenceBindingV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v7 = {
            "schema": (
                "strategy-correlation-cluster-portfolio-risk-shadow-consumer-"
                "preregistration-v7"
            ),
            "status": "BLOCKED",
            "contract_pins": {
                "consumer_fixture_javascript_sha256": FIXTURE_HASH,
                "immutable_v6_contract_pins": {
                    "projection_v3_implementation_sha256": PROJECTION_IMPL_HASH,
                    "freshness_gate_card_v3_javascript_sha256": CARD_HASH,
                },
            },
            "authority": {
                "activation": False,
                "paper_trading": False,
                "live_trading": False,
            },
        }
        self.node_receipt = {
            "schema": "fixture-execution-receipt-v1",
            "status": "PASS",
            "receipt_hash": RECEIPT_HASH,
            "projection_document_sha256": PROJECTION_DOCUMENT_HASH,
            "verification": {"descriptor_sha256": DESCRIPTOR_HASH},
            "authority": {"mount": False, "browser": False},
        }
        self.evidence = {
            "schema": (
                "strategy-correlation-cluster-portfolio-risk-presentation-"
                "fixture-execution-evidence-v1"
            ),
            "status": "PASS",
            "source": {
                "fixture_implementation_sha256": FIXTURE_HASH,
                "projection_implementation_sha256": PROJECTION_IMPL_HASH,
                "card_implementation_sha256": CARD_HASH,
                "projection_hash": PROJECTION_DOCUMENT_HASH,
                "descriptor_hash": DESCRIPTOR_HASH,
                "node_receipt_hash": RECEIPT_HASH,
            },
            "authority": {
                "runtime": False,
                "mount": False,
                "browser": False,
                "paper_trading": False,
                "live_trading": False,
            },
        }
        self.v7_context = {
            "preregistration_v6_document": {"schema": "v6"},
            "v6_verification_context": {"exact": True},
            "successor_implementation_sha256": (
                subject.EXPECTED_IMPLEMENTATION_SHA256[
                    "shadow_preregistration_v7"
                ]
            ),
        }
        self.evidence_context = {
            "node_execution_receipt": self.node_receipt,
            "expected_projection_hash": PROJECTION_DOCUMENT_HASH,
        }
        self.manifest = copy.deepcopy(subject.EXPECTED_IMPLEMENTATION_SHA256)
        self.v7_verifier = mock.patch.object(
            subject, "_VERIFY_V7", side_effect=_passing_receipt
        )
        self.evidence_verifier = mock.patch.object(
            subject, "_VERIFY_FIXTURE_EVIDENCE", side_effect=_passing_receipt
        )
        self.v7_verifier.start()
        self.evidence_verifier.start()
        self.addCleanup(self.v7_verifier.stop)
        self.addCleanup(self.evidence_verifier.stop)

    def _build(self, **overrides: object) -> dict[str, object]:
        arguments = {
            "preregistration_v7_document": self.v7,
            "fixture_execution_evidence": self.evidence,
            "preregistration_v7_verification_context": self.v7_context,
            "fixture_execution_evidence_verification_context": (
                self.evidence_context
            ),
            "current_implementation_sha256": self.manifest,
        }
        arguments.update(overrides)
        return subject.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1(
            **arguments
        )

    def test_valid_binding_passes_without_unlocking_registration(self) -> None:
        document = self._build()
        self.assertEqual(document["status"], "PASS")
        self.assertTrue(document["facts"]["local_fixture_execution_evidence_bound"])
        self.assertTrue(
            document["facts"]["shadow_preregistration_v7_remains_blocked"]
        )
        self.assertFalse(
            document["facts"]["presentation_consumer_registration_evidence_bound"]
        )
        self.assertTrue(all(value is False for value in document["authority"].values()))

    def test_source_summary_contains_hashes_not_raw_evidence(self) -> None:
        document = self._build()
        self.assertTrue(
            all(
                isinstance(value, str) and len(value) == 64
                for value in document["source_hashes"].values()
            )
        )
        serialized = json.dumps(document, sort_keys=True)
        self.assertNotIn("fixture-execution-receipt-v1", serialized)
        self.assertNotIn('"schema": "v6"', serialized)

    def test_document_hash_is_canonical(self) -> None:
        document = self._build()
        unhashed = copy.deepcopy(document)
        supplied = unhashed.pop("binding_sha256")
        self.assertEqual(supplied, _canonical_hash(unhashed))

    def test_manifest_missing_extra_drift_and_type_alias_block(self) -> None:
        variants = []
        missing = copy.deepcopy(self.manifest)
        missing.pop("fixture_execution_receipt_v1_js")
        variants.append(missing)
        extra = copy.deepcopy(self.manifest)
        extra["legacy"] = "6" * 64
        variants.append(extra)
        drift = copy.deepcopy(self.manifest)
        drift["shadow_preregistration_v7"] = "7" * 64
        variants.append(drift)
        alias = copy.deepcopy(self.manifest)
        alias["presentation_fixture_execution_evidence_v1"] = 8
        variants.append(alias)
        for manifest in variants:
            with self.subTest(manifest=manifest):
                self.assertEqual(
                    self._build(current_implementation_sha256=manifest)["status"],
                    "BLOCKED",
                )

    def test_context_missing_extra_and_cross_splice_block(self) -> None:
        missing = copy.deepcopy(self.v7_context)
        missing.pop("v6_verification_context")
        extra = copy.deepcopy(self.evidence_context)
        extra["compatibility_alias"] = True
        cross_splice = copy.deepcopy(self.evidence_context)
        cross_splice["expected_projection_hash"] = "9" * 64
        self.assertEqual(
            self._build(preregistration_v7_verification_context=missing)["status"],
            "BLOCKED",
        )
        self.assertEqual(
            self._build(
                fixture_execution_evidence_verification_context=extra
            )["status"],
            "BLOCKED",
        )
        self.assertEqual(
            self._build(
                fixture_execution_evidence_verification_context=cross_splice
            )["status"],
            "BLOCKED",
        )

    def test_each_implementation_pin_mismatch_blocks(self) -> None:
        mutations = (
            ("fixture_implementation_sha256", "a" * 64),
            ("projection_implementation_sha256", "b" * 64),
            ("card_implementation_sha256", "c" * 64),
        )
        for key, value in mutations:
            evidence = copy.deepcopy(self.evidence)
            evidence["source"][key] = value
            with self.subTest(key=key):
                self.assertEqual(
                    self._build(fixture_execution_evidence=evidence)["status"],
                    "BLOCKED",
                )

    def test_compatibility_alias_cannot_replace_exact_fixture_field(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["source"]["consumer_fixture_javascript_sha256"] = (
            evidence["source"].pop("fixture_implementation_sha256")
        )
        self.assertEqual(
            self._build(fixture_execution_evidence=evidence)["status"],
            "BLOCKED",
        )

    def test_projection_hash_chain_break_blocks(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["source"]["projection_hash"] = "e" * 64
        self.assertEqual(
            self._build(fixture_execution_evidence=evidence)["status"],
            "BLOCKED",
        )

    def test_receipt_and_descriptor_hash_cross_splice_block(self) -> None:
        receipt_splice = copy.deepcopy(self.evidence)
        receipt_splice["source"]["node_receipt_hash"] = "7" * 64
        descriptor_splice = copy.deepcopy(self.evidence)
        descriptor_splice["source"]["descriptor_hash"] = "8" * 64
        self.assertEqual(
            self._build(fixture_execution_evidence=receipt_splice)["status"],
            "BLOCKED",
        )
        self.assertEqual(
            self._build(fixture_execution_evidence=descriptor_splice)["status"],
            "BLOCKED",
        )

    def test_upstream_verification_failure_and_exception_block(self) -> None:
        with mock.patch.object(
            subject,
            "_VERIFY_V7",
            return_value={
                "status": "FAIL",
                "verified": False,
                "checks": {"exact": False},
            },
        ):
            self.assertEqual(self._build()["status"], "BLOCKED")
        with mock.patch.object(
            subject, "_VERIFY_FIXTURE_EVIDENCE", side_effect=ValueError("drift")
        ):
            self.assertEqual(self._build()["status"], "BLOCKED")

    def test_source_status_promotion_and_authority_leak_block(self) -> None:
        promoted = copy.deepcopy(self.v7)
        promoted["status"] = "PASS"
        leaked = copy.deepcopy(self.evidence)
        leaked["authority"]["runtime"] = True
        self.assertEqual(
            self._build(preregistration_v7_document=promoted)["status"],
            "BLOCKED",
        )
        self.assertEqual(
            self._build(fixture_execution_evidence=leaked)["status"],
            "BLOCKED",
        )

    def test_non_boolean_authority_alias_blocks(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["authority"]["runtime"] = 0
        self.assertEqual(
            self._build(fixture_execution_evidence=evidence)["status"],
            "BLOCKED",
        )

    def test_inputs_are_not_mutated_and_output_is_deterministic(self) -> None:
        inputs = copy.deepcopy(
            (self.v7, self.evidence, self.v7_context, self.evidence_context)
        )
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(
            (self.v7, self.evidence, self.v7_context, self.evidence_context),
            inputs,
        )

    def test_exact_verifier_accepts_only_exact_rebuild(self) -> None:
        document = self._build()
        receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1(
            document,
            self.v7,
            self.evidence,
            preregistration_v7_verification_context=self.v7_context,
            fixture_execution_evidence_verification_context=self.evidence_context,
            current_implementation_sha256=self.manifest,
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertTrue(receipt["verified"])
        tampered = copy.deepcopy(document)
        tampered["facts"]["browser_execution_proven"] = True
        rejected = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1(
            tampered,
            self.v7,
            self.evidence,
            preregistration_v7_verification_context=self.v7_context,
            fixture_execution_evidence_verification_context=self.evidence_context,
            current_implementation_sha256=self.manifest,
        )
        self.assertEqual(rejected["status"], "FAIL")

    def test_real_v7_and_adr0195_contracts_bind_without_mocks(self) -> None:
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1
            as upstream_evidence,
        )
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7
            as upstream_v7,
        )
        from tests import (
            test_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1
            as evidence_tests,
        )
        from tests import (
            test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7
            as v7_tests,
        )

        case_type = v7_tests.PortfolioRiskShadowConsumerPreregistrationV7Tests
        case = case_type(
            methodName=next(
                name for name in dir(case_type) if name.startswith("test_")
            )
        )
        case.setUp()
        projection, node_receipt, evidence = evidence_tests._build()
        v7_context = {
            "preregistration_v6_document": case.v6_document,
            "v6_verification_context": case.v6_context,
            "successor_implementation_sha256": case.manifest,
        }
        evidence_context = {
            "node_execution_receipt": node_receipt,
            "expected_projection_hash": projection["projection_hash"],
        }

        with mock.patch.object(
            subject,
            "_VERIFY_V7",
            upstream_v7.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7,
        ), mock.patch.object(
            subject,
            "_VERIFY_FIXTURE_EVIDENCE",
            upstream_evidence.verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1,
        ):
            document = subject.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1(
                case.document,
                evidence,
                preregistration_v7_verification_context=v7_context,
                fixture_execution_evidence_verification_context=evidence_context,
                current_implementation_sha256=dict(
                    subject.EXPECTED_IMPLEMENTATION_SHA256
                ),
            )
            verification = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1(
                document,
                case.document,
                evidence,
                preregistration_v7_verification_context=v7_context,
                fixture_execution_evidence_verification_context=evidence_context,
                current_implementation_sha256=dict(
                    subject.EXPECTED_IMPLEMENTATION_SHA256
                ),
            )

        self.assertEqual(document["status"], "PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(case.document["status"], "BLOCKED")
        self.assertFalse(
            document["facts"]["presentation_consumer_registration_activated"]
        )

    def test_api_and_context_shapes_are_frozen(self) -> None:
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1
        )
        self.assertEqual(
            tuple(signature.parameters),
            (
                "preregistration_v7_document",
                "fixture_execution_evidence",
                "preregistration_v7_verification_context",
                "fixture_execution_evidence_verification_context",
                "current_implementation_sha256",
            ),
        )
        self.assertEqual(
            subject.V7_VERIFICATION_CONTEXT_KEYS,
            frozenset(
                {
                    "preregistration_v6_document",
                    "v6_verification_context",
                    "successor_implementation_sha256",
                }
            ),
        )
        self.assertEqual(
            subject.EVIDENCE_VERIFICATION_CONTEXT_KEYS,
            frozenset({"node_execution_receipt", "expected_projection_hash"}),
        )

    def test_source_has_no_runtime_browser_or_profit_promotion(self) -> None:
        source = inspect.getsource(subject)
        self.assertNotIn("runtime/", source.lower())
        self.assertNotIn("selenium", source.lower())
        self.assertNotIn("playwright", source.lower())
        forbidden = "R" + "EADY"
        self.assertNotIn(forbidden, source)
        document = self._build()
        self.assertFalse(document["facts"]["runtime_mutations_performed"])
        self.assertFalse(document["facts"]["profitability_proven"])


if __name__ == "__main__":
    unittest.main()
