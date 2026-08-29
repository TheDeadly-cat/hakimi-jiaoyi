from __future__ import annotations

import copy
import inspect
import json
import unittest
from unittest import mock

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)


REGISTRATION_HASH = "1" * 64
PROJECTION_HASH = "2" * 64
RECEIPT_HASH = "3" * 64
DESCRIPTOR_HASH = "4" * 64
EVIDENCE_HASH = "5" * 64
PROJECTION_IMPL = "6" * 64
STRICT_IMPL = "7" * 64
CARD_IMPL = "8" * 64
FIXTURE_IMPL = "9" * 64


def _passing_registration_receipt(*_args, **_kwargs):
    return {
        "schema_version": "registration-verification",
        "status": "PASS",
        "registration_exactly_verified": True,
        "implementation_manifest_exactly_verified": True,
        "blockers": [],
        "registration_activated": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
    }


def _passing_evidence_receipt(*_args, **_kwargs):
    return {
        "schema_version": "evidence-verification",
        "status": "PASS",
        "evidence_exactly_verified": True,
        "blockers": [],
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
    }


class ShadowPresentationExecutionEvidenceBindingV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.registration = {
            "schema_version": subject.registration_v2.SCHEMA_VERSION,
            "status": "BLOCKED",
            "registration_hash": REGISTRATION_HASH,
            "contract_pins": {
                "projection_implementation_sha256": PROJECTION_IMPL,
                "strict_canonical_javascript_sha256": STRICT_IMPL,
                "card_javascript_sha256": CARD_IMPL,
                "consumer_fixture_javascript_sha256": FIXTURE_IMPL,
            },
            "source": {
                "artifact_files_read": False,
            },
            "facts": {
                "registration_candidate_built": True,
                "registration_activated": False,
                "implementation_manifest_externally_attested": False,
            },
            "authority": {
                "descriptive_only": True,
                "registration_activation": False,
                "presentation_mount_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.receipt = {
            "schema_version": subject.execution_evidence_v2.NODE_RECEIPT_SCHEMA_VERSION,
            "status": "PASS",
            "receipt_hash": RECEIPT_HASH,
            "source": {
                "registration_candidate_hash": REGISTRATION_HASH,
                "registration_implementation_sha256": subject.EXPECTED_IMPLEMENTATION_SHA256[
                    "presentation_registration_v2"
                ],
                "projection_hash": PROJECTION_HASH,
                "projection_implementation_sha256": PROJECTION_IMPL,
                "strict_canonical_implementation_sha256": STRICT_IMPL,
                "card_implementation_sha256": CARD_IMPL,
                "fixture_implementation_sha256": FIXTURE_IMPL,
            },
            "verification": {"descriptor_sha256": DESCRIPTOR_HASH},
            "authority": {
                "descriptive_only": True,
                "presentation_mount_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.evidence = {
            "schema_version": subject.execution_evidence_v2.SCHEMA_VERSION,
            "status": "PASS",
            "evidence_hash": EVIDENCE_HASH,
            "source": {
                "registration_candidate_hash": REGISTRATION_HASH,
                "registration_implementation_sha256": subject.EXPECTED_IMPLEMENTATION_SHA256[
                    "presentation_registration_v2"
                ],
                "projection_hash": PROJECTION_HASH,
                "projection_implementation_sha256": PROJECTION_IMPL,
                "strict_canonical_implementation_sha256": STRICT_IMPL,
                "card_implementation_sha256": CARD_IMPL,
                "fixture_implementation_sha256": FIXTURE_IMPL,
                "node_receipt_hash": RECEIPT_HASH,
                "descriptor_hash": DESCRIPTOR_HASH,
            },
            "facts": {
                "node_process_identity_authenticated": False,
                "receipt_signature_verified": False,
                "external_execution_authority_verified": False,
            },
            "authority": {
                "descriptive_only": True,
                "presentation_mount_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.registration_context = {
            "current_implementation_sha256": {"registration": "a" * 64}
        }
        self.evidence_context = {
            "node_execution_receipt": self.receipt,
            "expected_projection_hash": PROJECTION_HASH,
            "expected_registration_hash": REGISTRATION_HASH,
        }
        self.manifest = copy.deepcopy(subject.EXPECTED_IMPLEMENTATION_SHA256)
        self.registration_verifier = mock.patch.object(
            subject,
            "_VERIFY_REGISTRATION",
            side_effect=_passing_registration_receipt,
        )
        self.evidence_verifier = mock.patch.object(
            subject,
            "_VERIFY_EXECUTION_EVIDENCE",
            side_effect=_passing_evidence_receipt,
        )
        self.registration_verifier.start()
        self.evidence_verifier.start()
        self.addCleanup(self.registration_verifier.stop)
        self.addCleanup(self.evidence_verifier.stop)

    def _build(self, **overrides):
        arguments = {
            "registration_candidate_document": self.registration,
            "fixture_execution_evidence": self.evidence,
            "registration_verification_context": self.registration_context,
            "fixture_execution_evidence_verification_context": self.evidence_context,
            "current_implementation_sha256": self.manifest,
        }
        arguments.update(overrides)
        return subject.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2(
            **arguments
        )

    def test_valid_binding_passes_without_activation(self):
        document = self._build()
        self.assertEqual(document["status"], "PASS")
        self.assertTrue(document["facts"]["registration_candidate_evidence_bound"])
        self.assertTrue(document["facts"]["fixture_execution_evidence_bound"])
        self.assertTrue(document["facts"]["registration_candidate_remains_blocked"])
        self.assertTrue(all(value is False for value in document["authority"].values()))

    def test_source_summary_contains_hashes_not_raw_documents(self):
        document = self._build()
        self.assertTrue(
            all(isinstance(value, str) and len(value) == 64 for value in document["source_hashes"].values())
        )
        serialized = json.dumps(document, sort_keys=True)
        self.assertNotIn('"contract_pins"', serialized)
        self.assertNotIn('"node_execution_receipt"', serialized)

    def test_binding_hash_is_canonical(self):
        document = self._build()
        payload = copy.deepcopy(document)
        supplied = payload.pop("binding_sha256")
        self.assertEqual(supplied, strict_canonical_hash(payload))

    def test_manifest_missing_extra_drift_and_bool_alias_block(self):
        variants = []
        missing = copy.deepcopy(self.manifest)
        missing.pop("fixture_execution_receipt_v2_js")
        variants.append(missing)
        extra = {**self.manifest, "legacy": "a" * 64}
        variants.append(extra)
        drift = copy.deepcopy(self.manifest)
        drift["presentation_registration_v2"] = "b" * 64
        variants.append(drift)
        alias = copy.deepcopy(self.manifest)
        alias["presentation_fixture_execution_evidence_v2"] = True
        variants.append(alias)
        for manifest in variants:
            with self.subTest(manifest=manifest):
                self.assertEqual(
                    self._build(current_implementation_sha256=manifest)["status"],
                    "BLOCKED",
                )

    def test_context_missing_extra_and_cross_splice_block(self):
        missing = {}
        extra = {**self.evidence_context, "compatibility_alias": True}
        projection_splice = {
            **self.evidence_context,
            "expected_projection_hash": "a" * 64,
        }
        registration_splice = {
            **self.evidence_context,
            "expected_registration_hash": "b" * 64,
        }
        self.assertEqual(
            self._build(registration_verification_context=missing)["status"],
            "BLOCKED",
        )
        for context in (extra, projection_splice, registration_splice):
            self.assertEqual(
                self._build(
                    fixture_execution_evidence_verification_context=context
                )["status"],
                "BLOCKED",
            )

    def test_each_binding_implementation_pin_drift_blocks(self):
        for key in sorted(self.manifest):
            manifest = copy.deepcopy(self.manifest)
            manifest[key] = "f" * 64
            with self.subTest(key=key):
                self.assertEqual(
                    self._build(current_implementation_sha256=manifest)["status"],
                    "BLOCKED",
                )

    def test_registration_hash_chain_break_blocks(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["source"]["registration_candidate_hash"] = "a" * 64
        self.assertEqual(
            self._build(fixture_execution_evidence=evidence)["status"], "BLOCKED"
        )

    def test_projection_hash_chain_break_blocks(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["source"]["projection_hash"] = "b" * 64
        self.assertEqual(
            self._build(fixture_execution_evidence=evidence)["status"], "BLOCKED"
        )

    def test_receipt_and_descriptor_hash_cross_splice_block(self):
        receipt_splice = copy.deepcopy(self.evidence)
        receipt_splice["source"]["node_receipt_hash"] = "c" * 64
        descriptor_splice = copy.deepcopy(self.evidence)
        descriptor_splice["source"]["descriptor_hash"] = "d" * 64
        self.assertEqual(
            self._build(fixture_execution_evidence=receipt_splice)["status"],
            "BLOCKED",
        )
        self.assertEqual(
            self._build(fixture_execution_evidence=descriptor_splice)["status"],
            "BLOCKED",
        )

    def test_each_production_pin_mismatch_blocks(self):
        mutations = (
            "projection_implementation_sha256",
            "strict_canonical_implementation_sha256",
            "card_implementation_sha256",
            "fixture_implementation_sha256",
            "registration_implementation_sha256",
        )
        for key in mutations:
            evidence = copy.deepcopy(self.evidence)
            evidence["source"][key] = "e" * 64
            with self.subTest(key=key):
                self.assertEqual(
                    self._build(fixture_execution_evidence=evidence)["status"],
                    "BLOCKED",
                )

    def test_verifier_failure_and_exception_block(self):
        with mock.patch.object(
            subject,
            "_VERIFY_REGISTRATION",
            return_value={
                "status": "BLOCK",
                "registration_exactly_verified": False,
                "blockers": ["bad"],
            },
        ):
            self.assertEqual(self._build()["status"], "BLOCKED")
        with mock.patch.object(
            subject,
            "_VERIFY_EXECUTION_EVIDENCE",
            side_effect=ValueError("drift"),
        ):
            self.assertEqual(self._build()["status"], "BLOCKED")

    def test_source_status_and_authority_leak_block(self):
        promoted = copy.deepcopy(self.registration)
        promoted["status"] = "PASS"
        leaked = copy.deepcopy(self.evidence)
        leaked["authority"]["presentation_mount_allowed"] = True
        self.assertEqual(
            self._build(registration_candidate_document=promoted)["status"],
            "BLOCKED",
        )
        self.assertEqual(
            self._build(fixture_execution_evidence=leaked)["status"],
            "BLOCKED",
        )

    def test_non_boolean_authority_alias_blocks(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["authority"]["presentation_mount_allowed"] = 0
        self.assertEqual(
            self._build(fixture_execution_evidence=evidence)["status"], "BLOCKED"
        )

    def test_inputs_are_not_mutated_and_output_is_deterministic(self):
        inputs = copy.deepcopy(
            (
                self.registration,
                self.evidence,
                self.registration_context,
                self.evidence_context,
            )
        )
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(
            (
                self.registration,
                self.evidence,
                self.registration_context,
                self.evidence_context,
            ),
            inputs,
        )

    def test_exact_verifier_accepts_only_exact_rebuild(self):
        document = self._build()
        verification = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2(
            document,
            self.registration,
            self.evidence,
            registration_verification_context=self.registration_context,
            fixture_execution_evidence_verification_context=self.evidence_context,
            current_implementation_sha256=self.manifest,
        )
        self.assertEqual(verification["status"], "PASS")
        tampered = copy.deepcopy(document)
        tampered["facts"]["browser_execution_proven"] = True
        tampered.pop("binding_sha256")
        tampered = seal_strict_canonical_document(tampered, "binding_sha256")
        rejected = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2(
            tampered,
            self.registration,
            self.evidence,
            registration_verification_context=self.registration_context,
            fixture_execution_evidence_verification_context=self.evidence_context,
            current_implementation_sha256=self.manifest,
        )
        self.assertEqual(rejected["status"], "FAIL")

    def test_real_v2_contracts_bind_without_mocked_receipts(self):
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2
            as registration,
        )
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2
            as execution_evidence,
        )
        from tests import (
            test_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2
            as evidence_tests,
        )
        from tests import (
            test_strategy_correlation_cluster_portfolio_risk_projection_v4
            as projection_tests,
        )

        projection_case = projection_tests.PortfolioRiskProjectionV4Tests(
            methodName="test_base_pass_projects_neutral_four_stage_shape"
        )
        projection_case.setUp()
        case = projection_case.adapter_case._build_case()
        projection = projection_case._build_projection(case)["projection"]
        registration_manifest = (
            registration.expected_presentation_consumer_implementation_sha256_v2()
        )
        registration_document = registration.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
            registration_manifest
        )
        node_receipt = evidence_tests._node_receipt(projection)
        evidence = execution_evidence.build_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2(
            node_receipt,
            projection["projection_hash"],
            registration_document["registration_hash"],
        )
        registration_context = {
            "current_implementation_sha256": registration_manifest
        }
        evidence_context = {
            "node_execution_receipt": node_receipt,
            "expected_projection_hash": projection["projection_hash"],
            "expected_registration_hash": registration_document[
                "registration_hash"
            ],
        }
        with mock.patch.object(
            subject,
            "_VERIFY_REGISTRATION",
            registration.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2,
        ), mock.patch.object(
            subject,
            "_VERIFY_EXECUTION_EVIDENCE",
            execution_evidence.verify_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v2,
        ):
            document = subject.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2(
                registration_document,
                evidence,
                registration_verification_context=registration_context,
                fixture_execution_evidence_verification_context=evidence_context,
                current_implementation_sha256=dict(
                    subject.EXPECTED_IMPLEMENTATION_SHA256
                ),
            )
            verification = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2(
                document,
                registration_document,
                evidence,
                registration_verification_context=registration_context,
                fixture_execution_evidence_verification_context=evidence_context,
                current_implementation_sha256=dict(
                    subject.EXPECTED_IMPLEMENTATION_SHA256
                ),
            )
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(registration_document["status"], "BLOCKED")
        self.assertFalse(document["facts"]["registration_activated"])

    def test_api_and_context_shapes_are_frozen(self):
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2
        )
        self.assertEqual(
            tuple(signature.parameters),
            (
                "registration_candidate_document",
                "fixture_execution_evidence",
                "registration_verification_context",
                "fixture_execution_evidence_verification_context",
                "current_implementation_sha256",
            ),
        )
        self.assertEqual(
            subject.REGISTRATION_VERIFICATION_CONTEXT_KEYS,
            frozenset({"current_implementation_sha256"}),
        )
        self.assertEqual(
            subject.EVIDENCE_VERIFICATION_CONTEXT_KEYS,
            frozenset(
                {
                    "node_execution_receipt",
                    "expected_projection_hash",
                    "expected_registration_hash",
                }
            ),
        )

    def test_source_has_no_runtime_browser_or_promotion(self):
        source = inspect.getsource(subject)
        for forbidden in (
            "subprocess",
            "selenium",
            "playwright",
            "requests",
            "sqlite3",
            "exchange_terminal.server",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("R" + "EADY", source)
        document = self._build()
        self.assertFalse(document["facts"]["runtime_mutations_performed"])
        self.assertFalse(document["facts"]["profitability_proven"])


if __name__ == "__main__":
    unittest.main()
