from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


H = "a" * 64
DESCRIPTOR_HASH = "d" * 64


class ShadowConsumerPreregistrationV10Tests(unittest.TestCase):
    def setUp(self) -> None:
        authority = {
            "descriptive_only": True,
            "writer_allowed": False,
            "presentation_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        self.v9 = seal_strict_canonical_document(
            {
                "schema_version": subject.preregistration_v9.SCHEMA_VERSION,
                "static_fingerprint": subject.preregistration_v9.STATIC_FINGERPRINT,
                "status": "BLOCKED",
                "contract_state": "KNOWN",
                "decision": "synthetic-v9",
                "source": {},
                "contract_pins": {"legacy": "pinned"},
                "required_shadow_input_schemas": [
                    {"input": f"input-{index}", "schema_version": f"v{index}"}
                    for index in range(14)
                ],
                "closed_local_blockers": [
                    {"blocker": f"closed-{index}", "closure_verified": True}
                    for index in range(6)
                ],
                "blocker_refinements": [],
                "blockers": [
                    "provider_trust_unproven",
                    "presentation_render_descriptor_independent_review_missing",
                    "presentation_http_transport_unregistered_and_unexercised",
                ],
                "reuse_plan": [],
                "activation_order": [
                    "INDEPENDENTLY_REVIEW_ADR0192_RENDER_DESCRIPTOR",
                    "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
                ],
                "facts": {
                    "implementation_pin_count": 41,
                    "local_evidence_closure_count": 2,
                    "consumer_fixture_v3_execution_evidence_bound": True,
                    "presentation_registration_v1_evidence_bound": True,
                    "render_descriptor_independently_reviewed": False,
                    "presentation_http_transport_registered": False,
                    "browser_visual_review_v3_performed": False,
                },
                "authority": authority,
            },
            "preregistration_hash",
        )
        review_blockers = list(subject.SIGNED_REVIEW_REMAINING_BLOCKERS) + [
            "presentation_registration_not_activated"
        ]
        self.review = seal_strict_canonical_document(
            {
                "schema_version": subject.signed_review_v1.EVIDENCE_SCHEMA_VERSION,
                "static_fingerprint": subject.signed_review_v1.STATIC_FINGERPRINT,
                "status": "PASS",
                "facts": {
                    "detached_signature_verified": True,
                    "descriptor_hash_bound": True,
                    "review_request_exactly_verified": True,
                    "claim_intake_exactly_verified": True,
                    "independent_review_complete": False,
                    "real_world_reviewer_identity_verified": False,
                    "reviewer_process_independence_verified": False,
                    "descriptor_content_review_observed_by_system": False,
                    "runtime_mutations_performed": False,
                },
                "blockers": review_blockers,
                "source_lineage": {"descriptor_sha256": DESCRIPTOR_HASH},
                "authority": authority,
            },
            "evidence_hash",
        )
        self.binding = seal_strict_canonical_document(
            {
                "schema": subject.execution_binding_v2.SCHEMA,
                "static_fingerprint": subject.execution_binding_v2.STATIC_FINGERPRINT,
                "status": "PASS",
                "decision": "synthetic-binding-v2",
                "checks": {"exact": True, "pins": True},
                "facts": {
                    "fixture_execution_evidence_bound": True,
                    "fixture_execution_receipt_bound_via_evidence": True,
                    "registration_candidate_evidence_bound": True,
                    "registration_candidate_remains_blocked": True,
                    "independent_review_completed": False,
                    "external_artifact_attestation_verified": False,
                    "process_identity_authenticated": False,
                    "execution_receipt_signed": False,
                    "mount_performed": False,
                },
                "source_hashes": {"fixture_descriptor_hash": DESCRIPTOR_HASH},
                "authority": {
                    "registration_activation": False,
                    "presentation_mount": False,
                    "current_switch": False,
                    "paper_trading": False,
                    "live_trading": False,
                },
            },
            "binding_sha256",
        )
        self.v9_context = {
            "preregistration_v8_document": {},
            "http_candidate_response": {},
            "http_candidate_request": {},
            "v8_verification_context": {},
            "successor_implementation_sha256": {},
        }
        self.review_context = {
            "registration": {},
            "signed_attestation": {},
            "review_request_document": {},
            "review_claim": {},
            "claim_intake_document": {},
            "public_key_base64": "synthetic-public-key",
            "expected_registration_hash": H,
            "expected_signed_attestation_hash": H,
            "review_nonce_hash": H,
            "v9_verification_context": {},
        }
        self.binding_context = {
            "registration_candidate_document": {},
            "fixture_execution_evidence": {},
            "registration_verification_context": {},
            "fixture_execution_evidence_verification_context": {},
            "current_implementation_sha256": {},
        }
        self.manifest = copy.deepcopy(
            subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
        )
        self.v9_receipt = {
            "status": "PASS",
            "preregistration_exactly_verified": True,
            "preregistration_status": "BLOCKED",
            "blockers": [],
            "writer_allowed": False,
            "http_route_registration_allowed": False,
            "presentation_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        self.binding_receipt = {
            "status": "PASS",
            "verified": True,
            "checks": {"exact_rebuild_match": True, "authority_locked": True},
        }

    def _build(self, **overrides):
        values = {
            "preregistration_v9_document": self.v9,
            "signed_review_evidence": self.review,
            "execution_evidence_binding_v2_document": self.binding,
            "v9_verification_context": self.v9_context,
            "signed_review_evidence_verification_context": self.review_context,
            "execution_binding_verification_context": self.binding_context,
            "successor_implementation_sha256": self.manifest,
            "v9_receipt": self.v9_receipt,
            "review_result": True,
            "binding_receipt": self.binding_receipt,
            "v9_side_effect": None,
            "review_side_effect": None,
            "binding_side_effect": None,
        }
        values.update(overrides)

        def v9_verifier(*_args, **_kwargs):
            if values["v9_side_effect"] is not None:
                raise values["v9_side_effect"]
            return copy.deepcopy(values["v9_receipt"])

        def review_verifier(*_args, **_kwargs):
            if values["review_side_effect"] is not None:
                raise values["review_side_effect"]
            return values["review_result"]

        def binding_verifier(*_args, **_kwargs):
            if values["binding_side_effect"] is not None:
                raise values["binding_side_effect"]
            return copy.deepcopy(values["binding_receipt"])

        with (
            patch.object(subject, "_VERIFY_V9", side_effect=v9_verifier),
            patch.object(
                subject, "_VERIFY_SIGNED_REVIEW", side_effect=review_verifier
            ),
            patch.object(
                subject,
                "_VERIFY_EXECUTION_BINDING",
                side_effect=binding_verifier,
            ),
        ):
            return subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10(
                values["preregistration_v9_document"],
                values["signed_review_evidence"],
                values["execution_evidence_binding_v2_document"],
                v9_verification_context=values["v9_verification_context"],
                signed_review_evidence_verification_context=values[
                    "signed_review_evidence_verification_context"
                ],
                execution_binding_verification_context=values[
                    "execution_binding_verification_context"
                ],
                successor_implementation_sha256=values[
                    "successor_implementation_sha256"
                ],
            )

    def test_valid_v10_is_known_blocked_without_authority(self) -> None:
        document = self._build()
        self.assertEqual(document["contract_state"], "KNOWN")
        self.assertEqual(document["status"], "BLOCKED")
        self.assertTrue(all(document["source"]["verification_checks"].values()))
        self.assertTrue(document["facts"]["signed_review_claim_cryptographically_verified"])
        self.assertTrue(document["facts"]["consumer_fixture_v4_execution_evidence_bound"])
        self.assertFalse(document["facts"]["render_descriptor_independently_reviewed"])
        self.assertFalse(document["facts"]["ui_mounted"])
        self.assertTrue(document["authority"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_review_blocker_is_refined_not_falsely_closed(self) -> None:
        document = self._build()
        self.assertNotIn(
            "presentation_render_descriptor_independent_review_missing",
            document["blockers"],
        )
        for blocker in subject.SIGNED_REVIEW_REMAINING_BLOCKERS:
            self.assertIn(blocker, document["blockers"])
        self.assertIn(
            "external_independent_review_not_completed", document["blockers"]
        )
        refinement = document["blocker_refinements"][-1]
        self.assertEqual(
            refinement["remaining_requirements"],
            list(subject.SIGNED_REVIEW_REMAINING_BLOCKERS),
        )

    def test_execution_v2_gaps_remain_explicit(self) -> None:
        document = self._build()
        for blocker in subject.EXECUTION_REMAINING_BLOCKERS:
            self.assertIn(blocker, document["blockers"])
        self.assertFalse(document["facts"]["fixture_execution_receipt_signed"])
        self.assertFalse(
            document["facts"]["external_fixture_artifact_attestation_verified"]
        )

    def test_consumer_first_activation_order_is_complete_and_non_trading(self) -> None:
        document = self._build()
        self.assertEqual(document["activation_order"], list(subject.ACTIVATION_ORDER))
        joined = " ".join(document["activation_order"])
        for token in ("PROVIDER", "REVIEWER", "SIGN", "DOM", "BROWSER", "HTTP", "MOUNT", "CURRENT"):
            self.assertIn(token, joined)
        self.assertNotIn("PAPER", joined)
        self.assertNotIn("LIVE", joined)

    def test_output_contains_hash_summaries_not_source_documents(self) -> None:
        document = self._build()
        rendered = json.dumps(document, sort_keys=True)
        self.assertNotIn("public_key_base64", rendered)
        self.assertNotIn("signed_attestation", rendered)
        self.assertNotIn("fixture_execution_evidence", rendered)
        self.assertEqual(
            document["source"]["reviewed_and_executed_descriptor_sha256"],
            DESCRIPTOR_HASH,
        )

    def test_descriptor_cross_splice_is_unknown_even_when_verifiers_pass(self) -> None:
        review = copy.deepcopy(self.review)
        review["source_lineage"]["descriptor_sha256"] = "e" * 64
        review = seal_strict_canonical_document(
            {key: value for key, value in review.items() if key != "evidence_hash"},
            "evidence_hash",
        )
        document = self._build(signed_review_evidence=review)
        self.assertEqual(document["contract_state"], "UNKNOWN")
        self.assertFalse(
            document["source"]["verification_checks"][
                "reviewed_descriptor_matches_executed_fixture"
            ]
        )

    def test_each_context_missing_extra_and_scalar_alias_is_unknown(self) -> None:
        cases = (
            ("v9_verification_context", self.v9_context),
            (
                "signed_review_evidence_verification_context",
                self.review_context,
            ),
            ("execution_binding_verification_context", self.binding_context),
        )
        for argument, context in cases:
            with self.subTest(argument=argument, drift="missing"):
                changed = copy.deepcopy(context)
                changed.pop(next(iter(changed)))
                self.assertEqual(self._build(**{argument: changed})["contract_state"], "UNKNOWN")
            with self.subTest(argument=argument, drift="extra"):
                changed = copy.deepcopy(context)
                changed["extra"] = {}
                self.assertEqual(self._build(**{argument: changed})["contract_state"], "UNKNOWN")
            with self.subTest(argument=argument, drift="scalar"):
                self.assertEqual(self._build(**{argument: []})["contract_state"], "UNKNOWN")

    def test_manifest_missing_extra_drift_and_bool_alias_are_unknown(self) -> None:
        cases = []
        missing = copy.deepcopy(self.manifest)
        missing.pop(next(iter(missing)))
        cases.append(missing)
        extra = copy.deepcopy(self.manifest)
        extra["extra"] = H
        cases.append(extra)
        drift = copy.deepcopy(self.manifest)
        drift[next(iter(drift))] = "0" * 64
        cases.append(drift)
        boolean = copy.deepcopy(self.manifest)
        boolean[next(iter(boolean))] = True
        cases.append(boolean)
        for manifest in cases:
            with self.subTest(manifest=manifest):
                self.assertEqual(
                    self._build(successor_implementation_sha256=manifest)[
                        "contract_state"
                    ],
                    "UNKNOWN",
                )

    def test_each_source_verifier_failure_and_exception_is_unknown(self) -> None:
        bad_v9 = copy.deepcopy(self.v9_receipt)
        bad_v9["status"] = "BLOCK"
        bad_binding = copy.deepcopy(self.binding_receipt)
        bad_binding["verified"] = False
        cases = (
            {"v9_receipt": bad_v9},
            {"review_result": False},
            {"binding_receipt": bad_binding},
            {"v9_side_effect": RuntimeError("v9")},
            {"review_side_effect": RuntimeError("review")},
            {"binding_side_effect": RuntimeError("binding")},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.assertEqual(self._build(**overrides)["contract_state"], "UNKNOWN")

    def test_source_status_fact_and_authority_promotions_are_unknown(self) -> None:
        v9 = copy.deepcopy(self.v9)
        v9["status"] = "READY"
        v9 = seal_strict_canonical_document(
            {key: value for key, value in v9.items() if key != "preregistration_hash"},
            "preregistration_hash",
        )
        review = copy.deepcopy(self.review)
        review["facts"]["independent_review_complete"] = True
        review = seal_strict_canonical_document(
            {key: value for key, value in review.items() if key != "evidence_hash"},
            "evidence_hash",
        )
        binding = copy.deepcopy(self.binding)
        binding["authority"]["presentation_mount"] = True
        binding = seal_strict_canonical_document(
            {key: value for key, value in binding.items() if key != "binding_sha256"},
            "binding_sha256",
        )
        for overrides in (
            {"preregistration_v9_document": v9},
            {"signed_review_evidence": review},
            {"execution_evidence_binding_v2_document": binding},
        ):
            with self.subTest(overrides=overrides):
                self.assertEqual(self._build(**overrides)["contract_state"], "UNKNOWN")

    def test_non_boolean_authority_alias_is_unknown(self) -> None:
        review = copy.deepcopy(self.review)
        review["authority"]["presentation_mount_allowed"] = 0
        review = seal_strict_canonical_document(
            {key: value for key, value in review.items() if key != "evidence_hash"},
            "evidence_hash",
        )
        self.assertEqual(
            self._build(signed_review_evidence=review)["contract_state"],
            "UNKNOWN",
        )

    def test_build_is_deterministic_and_inputs_are_not_mutated(self) -> None:
        inputs = (
            self.v9,
            self.review,
            self.binding,
            self.v9_context,
            self.review_context,
            self.binding_context,
            self.manifest,
        )
        before = copy.deepcopy(inputs)
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(inputs, before)

    def test_public_verifier_accepts_exact_rebuild_and_rejects_tamper(self) -> None:
        document = self._build()
        with (
            patch.object(subject, "_VERIFY_V9", return_value=self.v9_receipt),
            patch.object(subject, "_VERIFY_SIGNED_REVIEW", return_value=True),
            patch.object(
                subject,
                "_VERIFY_EXECUTION_BINDING",
                return_value=self.binding_receipt,
            ),
        ):
            receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10(
                document,
                self.v9,
                self.review,
                self.binding,
                v9_verification_context=self.v9_context,
                signed_review_evidence_verification_context=self.review_context,
                execution_binding_verification_context=self.binding_context,
                successor_implementation_sha256=self.manifest,
            )
            self.assertEqual(receipt["status"], "PASS")
            self.assertTrue(receipt["preregistration_exactly_verified"])
            tampered = copy.deepcopy(document)
            tampered["facts"]["ui_mounted"] = True
            tampered = seal_strict_canonical_document(
                {
                    key: value
                    for key, value in tampered.items()
                    if key != "preregistration_hash"
                },
                "preregistration_hash",
            )
            blocked = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10(
                tampered,
                self.v9,
                self.review,
                self.binding,
                v9_verification_context=self.v9_context,
                signed_review_evidence_verification_context=self.review_context,
                execution_binding_verification_context=self.binding_context,
                successor_implementation_sha256=self.manifest,
            )
            self.assertEqual(blocked["status"], "BLOCK")
            self.assertFalse(blocked["preregistration_exactly_verified"])

    def test_pin_counts_and_local_closures_are_layered(self) -> None:
        document = self._build()
        self.assertEqual(document["facts"]["predecessor_implementation_pin_count"], 41)
        self.assertEqual(document["facts"]["successor_implementation_pin_count"], 4)
        self.assertEqual(document["facts"]["implementation_pin_count"], 45)
        self.assertEqual(document["facts"]["closed_local_blocker_count"], 8)
        self.assertEqual(document["facts"]["local_evidence_closure_count"], 4)

    def test_successor_manifest_matches_actual_source_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = {
            "shadow_preregistration_v9": root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9.py",
            "signed_review_attestation_v1": root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1.py",
            "presentation_execution_evidence_binding_v2": root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v2.py",
            "strict_canonical_json_hash": root
            / "exchange_terminal/services/strict_canonical_json_hash.py",
        }
        actual = {
            key: hashlib.sha256(path.read_bytes()).hexdigest()
            for key, path in paths.items()
        }
        self.assertEqual(actual, subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256)

    def test_api_and_source_boundary_are_frozen(self) -> None:
        build_signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10
        )
        self.assertEqual(
            list(build_signature.parameters),
            [
                "preregistration_v9_document",
                "signed_review_evidence",
                "execution_evidence_binding_v2_document",
                "v9_verification_context",
                "signed_review_evidence_verification_context",
                "execution_binding_verification_context",
                "successor_implementation_sha256",
            ],
        )
        source = inspect.getsource(subject)
        self.assertNotIn('"READY"', source)
        self.assertNotIn("exchange_terminal.server", source)
        self.assertNotIn("http_contract", source)
        self.assertNotIn("app.js", source)


if __name__ == "__main__":
    unittest.main()
