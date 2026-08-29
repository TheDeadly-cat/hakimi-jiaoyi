from __future__ import annotations

import copy
import hashlib
import inspect
import json
import unittest
from unittest import mock

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8
    as subject,
)


EVIDENCE_HASH = "1" * 64
PROJECTION_HASH = "2" * 64
DESCRIPTOR_HASH = "3" * 64
REGISTRATION_IMPLEMENTATION_HASH = (
    "6a5b4cd9a8a0e3552ec34b355c9a27f4560b5621557d605413aa8076c769cc7e"
)


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _passing_receipt(*_args: object, **_kwargs: object) -> dict[str, object]:
    return {
        "status": "PASS",
        "verified": True,
        "blockers": [],
        "checks": {"exact_rebuild_match": True},
    }


class ShadowConsumerPreregistrationV8Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v7 = {
            "schema_version": (
                "strategy-correlation-cluster-portfolio-risk-shadow-consumer-"
                "preregistration-v7"
            ),
            "static_fingerprint": "v7-lock",
            "status": "BLOCKED",
            "preregistration_hash": "4" * 64,
            "source": {"total_implementation_pin_count": 36},
            "contract_pins": {
                "presentation_registration_implementation_sha256": (
                    REGISTRATION_IMPLEMENTATION_HASH
                )
            },
            "required_shadow_input_schemas": [
                {"input": f"input-{index}", "schema_version": f"v{index}"}
                for index in range(14)
            ],
            "closed_local_blockers": [
                {
                    "blocker": f"closed-{index}",
                    "closure": f"closure-{index}",
                    "closure_verified": True,
                }
                for index in range(3)
            ],
            "blocker_refinements": [
                {"source_blocker": "provider", "source_blocker_closed": False},
                {"source_blocker": "projection", "source_blocker_closed": False},
                {
                    "source_blocker": "presentation_consumer_v3_registered",
                    "source_blocker_closed": False,
                    "remaining_requirements": sorted(
                        subject._CLOSED_EVIDENCE_BLOCKERS
                    ),
                },
            ],
            "blockers": [
                "provider_trust_unproven",
                "presentation_consumer_fixture_v3_execution_evidence_not_bound",
                "presentation_consumer_registration_candidate_v1_evidence_not_bound",
            ],
            "reuse_plan": [{"capability": "V7", "decision": "REUSE"}],
            "activation_order": [
                "REGISTER_UNMOUNTED_PRESENTATION_CONSUMER_FIXTURE_V3",
                "EXECUTE_ADR0192_FIXTURE_WITH_SYNTHETIC_PROJECTION_MATRIX",
                "INDEPENDENTLY_REVIEW_ADR0192_RENDER_DESCRIPTOR",
                "BIND_AND_EXACTLY_VERIFY_ADR0193_PRESENTATION_REGISTRATION_CANDIDATE",
                "SEPARATELY_AUTHORIZE_PRESENTATION_REGISTRATION_ACTIVATION",
                "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
            ],
            "facts": {
                "required_shadow_input_count": 14,
                "closed_local_blocker_count": 3,
                "implementation_pin_count": 36,
            },
            "authority": {
                "descriptive_only": True,
                "current_admission_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.registration_evidence = {
            "schema": (
                "strategy-correlation-cluster-portfolio-risk-shadow-"
                "presentation-registration-evidence-binding-v1"
            ),
            "status": "PASS",
            "binding_sha256": EVIDENCE_HASH,
            "source_hashes": {
                "shadow_preregistration_v7_document_sha256": _canonical_hash(
                    self.v7
                ),
                "presentation_execution_evidence_binding_v1_implementation_sha256": (
                    subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                        "presentation_execution_evidence_binding_v1"
                    ]
                ),
                "presentation_registration_candidate_v1_implementation_sha256": (
                    REGISTRATION_IMPLEMENTATION_HASH
                ),
                "projection_document_sha256": PROJECTION_HASH,
                "fixture_descriptor_sha256": DESCRIPTOR_HASH,
            },
            "facts": {
                "local_fixture_execution_evidence_bound": True,
                "registration_candidate_evidence_bound_in_successor": True,
                "registration_candidate_exactly_verified": True,
                "registration_activated": False,
            },
            "authority": {
                "registration_activation": False,
                "presentation_mount": False,
                "current_switch": False,
            },
        }
        self.v7_context = {
            "preregistration_v6_document": {"schema": "v6"},
            "v6_verification_context": {"exact": True},
            "successor_implementation_sha256": {"exact": "5" * 64},
        }
        self.evidence_context = {
            "execution_binding_document": {"schema": "execution-binding"},
            "registration_candidate_document": {"schema": "registration"},
            "execution_binding_verification_context": {"exact": True},
            "registration_candidate_verification_context": {"exact": True},
            "current_implementation_sha256": {"exact": "6" * 64},
        }
        self.manifest = copy.deepcopy(
            subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
        )
        self.v7_verifier = mock.patch.object(
            subject, "_VERIFY_V7", side_effect=_passing_receipt
        )
        self.evidence_verifier = mock.patch.object(
            subject, "_VERIFY_REGISTRATION_EVIDENCE", side_effect=_passing_receipt
        )
        self.v7_verifier.start()
        self.evidence_verifier.start()
        self.addCleanup(self.v7_verifier.stop)
        self.addCleanup(self.evidence_verifier.stop)

    def _build(self, **overrides: object) -> dict[str, object]:
        arguments = {
            "preregistration_v7_document": self.v7,
            "registration_evidence_binding_document": self.registration_evidence,
            "v7_verification_context": self.v7_context,
            "registration_evidence_binding_verification_context": (
                self.evidence_context
            ),
            "successor_implementation_sha256": self.manifest,
        }
        arguments.update(overrides)
        return subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8(
            **arguments
        )

    def test_valid_contract_is_known_but_public_status_stays_blocked(self) -> None:
        document = self._build()
        self.assertEqual(document["contract_state"], "KNOWN")
        self.assertEqual(document["status"], "BLOCKED")
        self.assertTrue(document["facts"]["consumer_fixture_v3_execution_evidence_bound"])
        self.assertTrue(document["facts"]["presentation_registration_v1_evidence_bound"])
        self.assertFalse(document["facts"]["presentation_registration_v1_activated"])

    def test_sources_are_exactly_verified_and_summary_only(self) -> None:
        document = self._build()
        self.assertTrue(document["source"]["immutable_v7_exactly_verified"])
        self.assertTrue(
            document["source"]["registration_evidence_binding_exactly_verified"]
        )
        serialized = json.dumps(document, sort_keys=True)
        self.assertNotIn("execution-binding\"", serialized)
        self.assertNotIn('"schema": "registration"', serialized)

    def test_manifest_layers_36_plus_3_without_duplication(self) -> None:
        document = self._build()
        self.assertEqual(document["facts"]["predecessor_implementation_pin_count"], 36)
        self.assertEqual(document["facts"]["successor_implementation_pin_count"], 3)
        self.assertEqual(document["facts"]["implementation_pin_count"], 39)
        artifacts = document["source"]["new_artifacts"]
        self.assertEqual(len(artifacts), 3)
        self.assertEqual(
            {item["artifact_id"] for item in artifacts}, set(self.manifest)
        )
        self.assertEqual(
            document["contract_pins"][
                "presentation_execution_evidence_binding_schema_version"
            ],
            "strategy-correlation-cluster-portfolio-risk-shadow-presentation-"
            "execution-evidence-binding-v1",
        )

    def test_two_evidence_blockers_close_and_two_real_gates_remain(self) -> None:
        document = self._build()
        self.assertTrue(
            subject._CLOSED_EVIDENCE_BLOCKERS.isdisjoint(document["blockers"])
        )
        self.assertTrue(set(subject._NEW_REMAINING_BLOCKERS) <= set(document["blockers"]))
        self.assertEqual(document["facts"]["local_evidence_closure_count"], 2)
        self.assertEqual(len(document["closed_local_blockers"]), 5)

    def test_fourteen_inputs_and_three_predecessor_closures_are_preserved(self) -> None:
        document = self._build()
        self.assertEqual(
            document["required_shadow_input_schemas"],
            self.v7["required_shadow_input_schemas"],
        )
        self.assertEqual(
            document["closed_local_blockers"][:3],
            self.v7["closed_local_blockers"],
        )

    def test_activation_order_removes_completed_local_steps_only(self) -> None:
        document = self._build()
        self.assertTrue(
            subject._COMPLETED_ACTIVATION_STEPS.isdisjoint(
                document["activation_order"]
            )
        )
        self.assertIn(
            "INDEPENDENTLY_REVIEW_ADR0192_RENDER_DESCRIPTOR",
            document["activation_order"],
        )
        self.assertIn(
            "SEPARATELY_AUTHORIZE_PRESENTATION_REGISTRATION_ACTIVATION",
            document["activation_order"],
        )

    def test_all_authority_remains_denied(self) -> None:
        authority = self._build()["authority"]
        self.assertTrue(authority["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def test_manifest_missing_extra_drift_and_scalar_alias_are_unknown(self) -> None:
        variants = []
        missing = copy.deepcopy(self.manifest)
        missing.pop("shadow_preregistration_v7")
        variants.append(missing)
        extra = copy.deepcopy(self.manifest)
        extra["legacy"] = "7" * 64
        variants.append(extra)
        drift = copy.deepcopy(self.manifest)
        drift["presentation_registration_evidence_binding_v1"] = "8" * 64
        variants.append(drift)
        alias = copy.deepcopy(self.manifest)
        alias["presentation_execution_evidence_binding_v1"] = 1
        variants.append(alias)
        for manifest in variants:
            with self.subTest(manifest=manifest):
                document = self._build(successor_implementation_sha256=manifest)
                self.assertEqual(document["contract_state"], "UNKNOWN")
                self.assertEqual(len(document["closed_local_blockers"]), 3)

    def test_context_missing_extra_and_scalar_alias_are_unknown(self) -> None:
        missing = copy.deepcopy(self.v7_context)
        missing.pop("v6_verification_context")
        extra = copy.deepcopy(self.evidence_context)
        extra["compatibility_alias"] = True
        scalar = "not-a-context"
        for key, value in (
            ("v7_verification_context", missing),
            ("registration_evidence_binding_verification_context", extra),
            ("registration_evidence_binding_verification_context", scalar),
        ):
            with self.subTest(key=key, value=value):
                self.assertEqual(self._build(**{key: value})["contract_state"], "UNKNOWN")

    def test_v7_verifier_failure_and_status_promotion_are_unknown(self) -> None:
        with mock.patch.object(
            subject,
            "_VERIFY_V7",
            return_value={"status": "BLOCK", "blockers": ["exact"]},
        ):
            self.assertEqual(self._build()["contract_state"], "UNKNOWN")
        promoted = copy.deepcopy(self.v7)
        promoted["status"] = "PASS"
        evidence = copy.deepcopy(self.registration_evidence)
        evidence["source_hashes"][
            "shadow_preregistration_v7_document_sha256"
        ] = _canonical_hash(promoted)
        self.assertEqual(
            self._build(
                preregistration_v7_document=promoted,
                registration_evidence_binding_document=evidence,
            )["contract_state"],
            "UNKNOWN",
        )

    def test_registration_evidence_verifier_failure_and_exception_are_unknown(self) -> None:
        with mock.patch.object(
            subject,
            "_VERIFY_REGISTRATION_EVIDENCE",
            return_value={"status": "FAIL", "verified": False, "blockers": []},
        ):
            self.assertEqual(self._build()["contract_state"], "UNKNOWN")
        with mock.patch.object(
            subject, "_VERIFY_REGISTRATION_EVIDENCE", side_effect=ValueError("drift")
        ):
            self.assertEqual(self._build()["contract_state"], "UNKNOWN")

    def test_v7_document_cross_splice_is_unknown(self) -> None:
        evidence = copy.deepcopy(self.registration_evidence)
        evidence["source_hashes"][
            "shadow_preregistration_v7_document_sha256"
        ] = "9" * 64
        self.assertEqual(
            self._build(registration_evidence_binding_document=evidence)[
                "contract_state"
            ],
            "UNKNOWN",
        )

    def test_execution_implementation_cross_splice_is_unknown(self) -> None:
        evidence = copy.deepcopy(self.registration_evidence)
        evidence["source_hashes"][
            "presentation_execution_evidence_binding_v1_implementation_sha256"
        ] = "a" * 64
        self.assertEqual(
            self._build(registration_evidence_binding_document=evidence)[
                "contract_state"
            ],
            "UNKNOWN",
        )

    def test_false_evidence_or_activation_leak_is_unknown(self) -> None:
        false_evidence = copy.deepcopy(self.registration_evidence)
        false_evidence["facts"][
            "registration_candidate_evidence_bound_in_successor"
        ] = False
        activated = copy.deepcopy(self.registration_evidence)
        activated["facts"]["registration_activated"] = True
        self.assertEqual(
            self._build(registration_evidence_binding_document=false_evidence)[
                "contract_state"
            ],
            "UNKNOWN",
        )
        self.assertEqual(
            self._build(registration_evidence_binding_document=activated)[
                "contract_state"
            ],
            "UNKNOWN",
        )

    def test_authority_leak_or_type_alias_is_unknown(self) -> None:
        leaked = copy.deepcopy(self.registration_evidence)
        leaked["authority"]["presentation_mount"] = True
        aliased = copy.deepcopy(self.v7)
        aliased["authority"]["paper_authorized"] = 0
        evidence = copy.deepcopy(self.registration_evidence)
        evidence["source_hashes"][
            "shadow_preregistration_v7_document_sha256"
        ] = _canonical_hash(aliased)
        self.assertEqual(
            self._build(registration_evidence_binding_document=leaked)[
                "contract_state"
            ],
            "UNKNOWN",
        )
        self.assertEqual(
            self._build(
                preregistration_v7_document=aliased,
                registration_evidence_binding_document=evidence,
            )["contract_state"],
            "UNKNOWN",
        )

    def test_build_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        inputs = copy.deepcopy(
            (self.v7, self.registration_evidence, self.v7_context, self.evidence_context)
        )
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(
            (self.v7, self.registration_evidence, self.v7_context, self.evidence_context),
            inputs,
        )

    def test_public_verifier_accepts_exact_rebuild_and_rejects_tamper(self) -> None:
        document = self._build()
        receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8(
            document,
            self.v7,
            self.registration_evidence,
            v7_verification_context=self.v7_context,
            registration_evidence_binding_verification_context=self.evidence_context,
            successor_implementation_sha256=self.manifest,
        )
        self.assertEqual(receipt["status"], "PASS")
        tampered = copy.deepcopy(document)
        tampered["facts"]["presentation_registration_v1_activated"] = True
        rejected = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8(
            tampered,
            self.v7,
            self.registration_evidence,
            v7_verification_context=self.v7_context,
            registration_evidence_binding_verification_context=self.evidence_context,
            successor_implementation_sha256=self.manifest,
        )
        self.assertEqual(rejected["status"], "BLOCK")

    def test_api_and_context_shapes_are_frozen(self) -> None:
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8
        )
        self.assertEqual(
            tuple(signature.parameters),
            (
                "preregistration_v7_document",
                "registration_evidence_binding_document",
                "v7_verification_context",
                "registration_evidence_binding_verification_context",
                "successor_implementation_sha256",
            ),
        )
        self.assertEqual(len(subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256), 3)

    def test_real_v7_and_adr0197_evidence_build_known_blocked_v8(self) -> None:
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1
            as registration,
        )
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7
            as v7_module,
        )
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1
            as execution,
        )
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1
            as registration_evidence,
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
        reg_type = registration_tests.PortfolioRiskPresentationConsumerRegistrationV1Tests
        reg_case = reg_type(
            methodName=next(name for name in dir(reg_type) if name.startswith("test_"))
        )
        reg_case.setUp()
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
        execution_document = execution.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1(
            v7_case.document,
            evidence,
            preregistration_v7_verification_context=v7_context,
            fixture_execution_evidence_verification_context=evidence_context,
            current_implementation_sha256=dict(
                execution.EXPECTED_IMPLEMENTATION_SHA256
            ),
        )
        execution_verification_context = {
            "fixture_execution_evidence": evidence,
            "preregistration_v7_verification_context": v7_context,
            "fixture_execution_evidence_verification_context": evidence_context,
            "current_implementation_sha256": dict(
                execution.EXPECTED_IMPLEMENTATION_SHA256
            ),
        }
        registration_verification_context = {
            "current_implementation_sha256": reg_case.manifest
        }
        registration_evidence_document = registration_evidence.build_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1(
            v7_case.document,
            execution_document,
            reg_case.document,
            execution_binding_verification_context=execution_verification_context,
            registration_candidate_verification_context=(
                registration_verification_context
            ),
            current_implementation_sha256=dict(
                registration_evidence.EXPECTED_IMPLEMENTATION_SHA256
            ),
        )
        registration_evidence_context = {
            "execution_binding_document": execution_document,
            "registration_candidate_document": reg_case.document,
            "execution_binding_verification_context": execution_verification_context,
            "registration_candidate_verification_context": (
                registration_verification_context
            ),
            "current_implementation_sha256": dict(
                registration_evidence.EXPECTED_IMPLEMENTATION_SHA256
            ),
        }

        with mock.patch.object(
            subject,
            "_VERIFY_V7",
            v7_module.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7,
        ), mock.patch.object(
            subject,
            "_VERIFY_REGISTRATION_EVIDENCE",
            registration_evidence.verify_strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1,
        ):
            document = subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8(
                v7_case.document,
                registration_evidence_document,
                v7_verification_context=v7_context,
                registration_evidence_binding_verification_context=(
                    registration_evidence_context
                ),
                successor_implementation_sha256=dict(
                    subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
                ),
            )
            verification = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8(
                document,
                v7_case.document,
                registration_evidence_document,
                v7_verification_context=v7_context,
                registration_evidence_binding_verification_context=(
                    registration_evidence_context
                ),
                successor_implementation_sha256=dict(
                    subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
                ),
            )

        self.assertEqual(document["contract_state"], "KNOWN")
        self.assertEqual(document["status"], "BLOCKED")
        self.assertEqual(verification["status"], "PASS")
        self.assertFalse(document["facts"]["presentation_registration_v1_activated"])
        self.assertEqual(document["facts"]["implementation_pin_count"], 39)

    def test_source_has_no_runtime_browser_or_ready_promotion(self) -> None:
        source = inspect.getsource(subject)
        self.assertNotIn("runtime/", source.lower())
        self.assertNotIn("selenium", source.lower())
        self.assertNotIn("playwright", source.lower())
        forbidden = "R" + "EADY"
        self.assertNotIn(forbidden, source)
        document = self._build()
        self.assertFalse(document["facts"]["runtime_consumer_bound"])
        self.assertFalse(document["facts"]["profitability_proven"])


if __name__ == "__main__":
    unittest.main()
