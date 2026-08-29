from __future__ import annotations

import copy
import hashlib
import inspect
import json
import unittest
from unittest import mock

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1
    as subject,
)


FIXTURE_HASH = "1" * 64
PROJECTION_HASH = "2" * 64
CARD_JS_HASH = "3" * 64
CARD_CSS_HASH = "4" * 64
REGISTRATION_HASH = "5" * 64
BINDING_HASH = "6" * 64
DESCRIPTOR_HASH = "7" * 64
PROJECTION_DOCUMENT_HASH = "8" * 64


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
        "status": "PASS",
        "verified": True,
        "blockers": [],
        "checks": {"exact_rebuild_match": True, "authority_locked": True},
    }


class ShadowPresentationRegistrationEvidenceBindingV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v7 = {
            "schema_version": "shadow-preregistration-v7",
            "status": "BLOCKED",
            "contract_pins": {
                "consumer_fixture_javascript_sha256": FIXTURE_HASH,
                "immutable_v6_contract_pins": {
                    "projection_v3_implementation_sha256": PROJECTION_HASH,
                    "freshness_gate_card_v3_javascript_sha256": CARD_JS_HASH,
                    "freshness_gate_card_v3_stylesheet_sha256": CARD_CSS_HASH,
                },
                "presentation_registration_expected_document_hash": (
                    REGISTRATION_HASH
                ),
                "presentation_registration_implementation_sha256": (
                    subject.EXPECTED_IMPLEMENTATION_SHA256[
                        "presentation_registration_candidate_v1"
                    ]
                ),
                "presentation_registration_schema_version": (
                    "registration-candidate-v1"
                ),
                "presentation_registration_status": "BLOCKED",
            },
            "authority": {
                "descriptive_only": True,
                "current_admission_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.execution_binding = {
            "schema": (
                "strategy-correlation-cluster-portfolio-risk-shadow-"
                "presentation-execution-evidence-binding-v1"
            ),
            "status": "PASS",
            "binding_sha256": BINDING_HASH,
            "source_hashes": {
                "shadow_preregistration_v7_document_sha256": _canonical_hash(
                    self.v7
                ),
                "projection_document_sha256": PROJECTION_DOCUMENT_HASH,
                "fixture_descriptor_sha256": DESCRIPTOR_HASH,
            },
            "facts": {
                "local_fixture_execution_evidence_bound": True,
                "presentation_consumer_registration_evidence_bound": False,
                "presentation_consumer_registration_activated": False,
            },
            "authority": {
                "consumer_activation": False,
                "presentation_registration": False,
                "mount": False,
            },
        }
        self.registration = {
            "schema_version": "registration-candidate-v1",
            "status": "BLOCKED",
            "registration_hash": REGISTRATION_HASH,
            "contract_pins": {
                "consumer_fixture_javascript_sha256": FIXTURE_HASH,
                "projection_implementation_sha256": PROJECTION_HASH,
                "card_javascript_sha256": CARD_JS_HASH,
                "card_stylesheet_sha256": CARD_CSS_HASH,
            },
            "facts": {
                "registration_candidate_built": True,
                "registration_activated": False,
                "ui_mounted": False,
                "server_route_registered": False,
            },
            "authority": {
                "descriptive_only": True,
                "presentation_consumer_activation_allowed": False,
                "presentation_mount_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.execution_context = {
            "fixture_execution_evidence": {"schema": "fixture-evidence"},
            "preregistration_v7_verification_context": {"exact": True},
            "fixture_execution_evidence_verification_context": {"exact": True},
            "current_implementation_sha256": {"exact": "9" * 64},
        }
        self.registration_context = {
            "current_implementation_sha256": {"asset": "a" * 64}
        }
        self.manifest = copy.deepcopy(subject.EXPECTED_IMPLEMENTATION_SHA256)
        self.execution_verifier = mock.patch.object(
            subject, "_VERIFY_EXECUTION_BINDING", side_effect=_passing_receipt
        )
        self.registration_verifier = mock.patch.object(
            subject, "_VERIFY_REGISTRATION", side_effect=_passing_receipt
        )
        self.execution_verifier.start()
        self.registration_verifier.start()
        self.addCleanup(self.execution_verifier.stop)
        self.addCleanup(self.registration_verifier.stop)

    def _build(self, **overrides: object) -> dict[str, object]:
        arguments = {
            "preregistration_v7_document": self.v7,
            "execution_binding_document": self.execution_binding,
            "registration_candidate_document": self.registration,
            "execution_binding_verification_context": self.execution_context,
            "registration_candidate_verification_context": (
                self.registration_context
            ),
            "current_implementation_sha256": self.manifest,
        }
        arguments.update(overrides)
        return subject.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1(
            **arguments
        )

    def test_valid_successor_binding_passes_without_activation(self) -> None:
        document = self._build()
        self.assertEqual(document["status"], "PASS")
        self.assertTrue(
            document["facts"][
                "registration_candidate_evidence_bound_in_successor"
            ]
        )
        self.assertTrue(document["facts"]["registration_candidate_remains_blocked"])
        self.assertFalse(document["facts"]["registration_activated"])
        self.assertTrue(all(value is False for value in document["authority"].values()))

    def test_source_documents_remain_blocked_and_unmodified(self) -> None:
        inputs = copy.deepcopy(
            (self.v7, self.execution_binding, self.registration)
        )
        document = self._build()
        self.assertEqual(self.v7["status"], "BLOCKED")
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertFalse(document["facts"]["source_documents_mutated"])
        self.assertEqual(
            (self.v7, self.execution_binding, self.registration), inputs
        )

    def test_context_missing_extra_and_scalar_alias_block(self) -> None:
        missing = copy.deepcopy(self.execution_context)
        missing.pop("fixture_execution_evidence")
        extra = copy.deepcopy(self.registration_context)
        extra["compatibility_alias"] = True
        scalar = {"current_implementation_sha256": "a" * 64}
        self.assertEqual(
            self._build(execution_binding_verification_context=missing)["status"],
            "BLOCKED",
        )
        self.assertEqual(
            self._build(
                registration_candidate_verification_context=extra
            )["status"],
            "BLOCKED",
        )
        with mock.patch.object(
            subject,
            "_VERIFY_REGISTRATION",
            return_value={"status": "BLOCK", "blockers": ["exact"]},
        ):
            self.assertEqual(
                self._build(
                    registration_candidate_verification_context=scalar
                )["status"],
                "BLOCKED",
            )

    def test_manifest_missing_extra_drift_and_type_alias_block(self) -> None:
        variants = []
        missing = copy.deepcopy(self.manifest)
        missing.pop("presentation_registration_candidate_v1")
        variants.append(missing)
        extra = copy.deepcopy(self.manifest)
        extra["legacy"] = "b" * 64
        variants.append(extra)
        drift = copy.deepcopy(self.manifest)
        drift["presentation_execution_evidence_binding_v1"] = "c" * 64
        variants.append(drift)
        alias = copy.deepcopy(self.manifest)
        alias["presentation_registration_candidate_v1"] = 1
        variants.append(alias)
        for manifest in variants:
            with self.subTest(manifest=manifest):
                self.assertEqual(
                    self._build(current_implementation_sha256=manifest)["status"],
                    "BLOCKED",
                )

    def test_registration_document_hash_cross_splice_blocks(self) -> None:
        registration = copy.deepcopy(self.registration)
        registration["registration_hash"] = "d" * 64
        self.assertEqual(
            self._build(registration_candidate_document=registration)["status"],
            "BLOCKED",
        )

    def test_registration_implementation_identity_drift_blocks(self) -> None:
        v7 = copy.deepcopy(self.v7)
        v7["contract_pins"][
            "presentation_registration_implementation_sha256"
        ] = "e" * 64
        execution = copy.deepcopy(self.execution_binding)
        execution["source_hashes"][
            "shadow_preregistration_v7_document_sha256"
        ] = _canonical_hash(v7)
        self.assertEqual(
            self._build(
                preregistration_v7_document=v7,
                execution_binding_document=execution,
            )["status"],
            "BLOCKED",
        )

    def test_each_presentation_pin_mismatch_blocks(self) -> None:
        mutations = (
            ("consumer_fixture_javascript_sha256", "f" * 64),
            ("projection_implementation_sha256", "0" * 64),
            ("card_javascript_sha256", "a" * 64),
            ("card_stylesheet_sha256", "b" * 64),
        )
        for key, value in mutations:
            registration = copy.deepcopy(self.registration)
            registration["contract_pins"][key] = value
            with self.subTest(key=key):
                self.assertEqual(
                    self._build(
                        registration_candidate_document=registration
                    )["status"],
                    "BLOCKED",
                )

    def test_execution_binding_v7_cross_splice_blocks(self) -> None:
        execution = copy.deepcopy(self.execution_binding)
        execution["source_hashes"][
            "shadow_preregistration_v7_document_sha256"
        ] = "c" * 64
        self.assertEqual(
            self._build(execution_binding_document=execution)["status"],
            "BLOCKED",
        )

    def test_missing_fixture_execution_evidence_blocks(self) -> None:
        execution = copy.deepcopy(self.execution_binding)
        execution["facts"]["local_fixture_execution_evidence_bound"] = False
        self.assertEqual(
            self._build(execution_binding_document=execution)["status"],
            "BLOCKED",
        )

    def test_status_promotion_and_activation_leak_block(self) -> None:
        promoted = copy.deepcopy(self.registration)
        promoted["status"] = "PASS"
        activated = copy.deepcopy(self.registration)
        activated["facts"]["registration_activated"] = True
        self.assertEqual(
            self._build(registration_candidate_document=promoted)["status"],
            "BLOCKED",
        )
        self.assertEqual(
            self._build(registration_candidate_document=activated)["status"],
            "BLOCKED",
        )

    def test_authority_true_or_non_boolean_blocks(self) -> None:
        leaked = copy.deepcopy(self.registration)
        leaked["authority"]["presentation_mount_allowed"] = True
        aliased = copy.deepcopy(self.execution_binding)
        aliased["authority"]["mount"] = 0
        self.assertEqual(
            self._build(registration_candidate_document=leaked)["status"],
            "BLOCKED",
        )
        self.assertEqual(
            self._build(execution_binding_document=aliased)["status"],
            "BLOCKED",
        )

    def test_upstream_verifier_failure_and_exception_block(self) -> None:
        with mock.patch.object(
            subject,
            "_VERIFY_EXECUTION_BINDING",
            return_value={"status": "FAIL", "verified": False, "blockers": []},
        ):
            self.assertEqual(self._build()["status"], "BLOCKED")
        with mock.patch.object(
            subject, "_VERIFY_REGISTRATION", side_effect=ValueError("drift")
        ):
            self.assertEqual(self._build()["status"], "BLOCKED")

    def test_source_summary_contains_hashes_not_raw_documents(self) -> None:
        document = self._build()
        self.assertTrue(
            all(
                isinstance(value, str) and len(value) == 64
                for value in document["source_hashes"].values()
            )
        )
        serialized = json.dumps(document, sort_keys=True)
        self.assertNotIn("fixture-evidence", serialized)
        self.assertNotIn("registration-candidate-v1\"", serialized)

    def test_canonical_hash_and_deterministic_nonmutation(self) -> None:
        inputs = copy.deepcopy(
            (
                self.v7,
                self.execution_binding,
                self.registration,
                self.execution_context,
                self.registration_context,
            )
        )
        first = self._build()
        second = self._build()
        unhashed = copy.deepcopy(first)
        supplied = unhashed.pop("binding_sha256")
        self.assertEqual(first, second)
        self.assertEqual(supplied, _canonical_hash(unhashed))
        self.assertEqual(
            (
                self.v7,
                self.execution_binding,
                self.registration,
                self.execution_context,
                self.registration_context,
            ),
            inputs,
        )

    def test_exact_verifier_accepts_rebuild_and_rejects_tamper(self) -> None:
        document = self._build()
        receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1(
            document,
            self.v7,
            self.execution_binding,
            self.registration,
            execution_binding_verification_context=self.execution_context,
            registration_candidate_verification_context=self.registration_context,
            current_implementation_sha256=self.manifest,
        )
        self.assertEqual(receipt["status"], "PASS")
        tampered = copy.deepcopy(document)
        tampered["facts"]["registration_activated"] = True
        rejected = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1(
            tampered,
            self.v7,
            self.execution_binding,
            self.registration,
            execution_binding_verification_context=self.execution_context,
            registration_candidate_verification_context=self.registration_context,
            current_implementation_sha256=self.manifest,
        )
        self.assertEqual(rejected["status"], "FAIL")

    def test_api_and_context_shapes_are_frozen(self) -> None:
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1
        )
        self.assertEqual(
            tuple(signature.parameters),
            (
                "preregistration_v7_document",
                "execution_binding_document",
                "registration_candidate_document",
                "execution_binding_verification_context",
                "registration_candidate_verification_context",
                "current_implementation_sha256",
            ),
        )
        self.assertEqual(
            subject.REGISTRATION_VERIFICATION_CONTEXT_KEYS,
            frozenset({"current_implementation_sha256"}),
        )

    def test_real_v7_adr0196_and_registration_contracts_bind(self) -> None:
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1
            as upstream_registration,
        )
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1
            as upstream_binding,
        )
        from tests import (
            test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1
            as registration_tests,
        )
        from tests import (
            test_strategy_correlation_cluster_portfolio_risk_presentation_fixture_execution_evidence_v1
            as evidence_tests,
        )
        from tests import (
            test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7
            as v7_tests,
        )

        v7_type = v7_tests.PortfolioRiskShadowConsumerPreregistrationV7Tests
        v7_case = v7_type(
            methodName=next(name for name in dir(v7_type) if name.startswith("test_"))
        )
        v7_case.setUp()
        registration_type = (
            registration_tests.PortfolioRiskPresentationConsumerRegistrationV1Tests
        )
        registration_case = registration_type(
            methodName=next(
                name
                for name in dir(registration_type)
                if name.startswith("test_")
            )
        )
        registration_case.setUp()
        projection, node_receipt, evidence = evidence_tests._build()
        v7_context = {
            "preregistration_v6_document": v7_case.v6_document,
            "v6_verification_context": v7_case.v6_context,
            "successor_implementation_sha256": v7_case.manifest,
        }
        evidence_context = {
            "node_execution_receipt": node_receipt,
            "expected_projection_hash": projection["projection_hash"],
        }
        execution_document = upstream_binding.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1(
            v7_case.document,
            evidence,
            preregistration_v7_verification_context=v7_context,
            fixture_execution_evidence_verification_context=evidence_context,
            current_implementation_sha256=dict(
                upstream_binding.EXPECTED_IMPLEMENTATION_SHA256
            ),
        )
        execution_context = {
            "fixture_execution_evidence": evidence,
            "preregistration_v7_verification_context": v7_context,
            "fixture_execution_evidence_verification_context": evidence_context,
            "current_implementation_sha256": dict(
                upstream_binding.EXPECTED_IMPLEMENTATION_SHA256
            ),
        }
        registration_context = {
            "current_implementation_sha256": registration_case.manifest
        }

        with mock.patch.object(
            subject,
            "_VERIFY_EXECUTION_BINDING",
            upstream_binding.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1,
        ), mock.patch.object(
            subject,
            "_VERIFY_REGISTRATION",
            upstream_registration.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1,
        ):
            document = subject.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1(
                v7_case.document,
                execution_document,
                registration_case.document,
                execution_binding_verification_context=execution_context,
                registration_candidate_verification_context=(
                    registration_context
                ),
                current_implementation_sha256=dict(
                    subject.EXPECTED_IMPLEMENTATION_SHA256
                ),
            )
            verification = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1(
                document,
                v7_case.document,
                execution_document,
                registration_case.document,
                execution_binding_verification_context=execution_context,
                registration_candidate_verification_context=(
                    registration_context
                ),
                current_implementation_sha256=dict(
                    subject.EXPECTED_IMPLEMENTATION_SHA256
                ),
            )

        self.assertEqual(document["status"], "PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(v7_case.document["status"], "BLOCKED")
        self.assertEqual(registration_case.document["status"], "BLOCKED")
        self.assertFalse(document["facts"]["registration_activated"])

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
