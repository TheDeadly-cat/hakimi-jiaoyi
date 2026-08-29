from __future__ import annotations

from copy import deepcopy
import inspect
import unittest

from exchange_terminal.application import (
    witness_ownership_state_provider_conformance_presentation_envelope_v1 as presentation,
)
from exchange_terminal.interfaces import (
    witness_ownership_state_provider_conformance_presentation_handoff_v1 as handoff,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_witness_ownership_state_provider_conformance_evidence_v1 as adr0414_tests,
)


class WitnessOwnershipProviderConformancePresentationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = adr0414_tests.WitnessOwnershipProviderConformanceEvidenceV1Tests(
            methodName=(
                "test_two_of_three_signed_reports_pass_locally_but_admission_blocks"
            )
        )
        fixture.setUp()
        self.signed_reports = fixture.signed_reports[:2]
        self.plan_document = fixture.plan_document
        self.provider_preregistration_document = (
            fixture.provider_preregistration_document
        )
        self.signed_receipt_evidence_document = (
            fixture.signed_receipt_evidence_document
        )
        self.quorum_kwargs = fixture.upstream_kwargs
        self.quorum_document = fixture.evaluate()
        self.presentation_build_kwargs = {
            "expected_observer_quorum_evidence_hash": self.quorum_document[
                "quorum_evidence_hash"
            ],
            "observer_quorum_evaluation_kwargs": self.quorum_kwargs,
        }
        self.presentation_document = presentation.build_witness_ownership_provider_conformance_presentation_envelope_v1(
            self.quorum_document,
            self.signed_reports,
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document,
            **self.presentation_build_kwargs,
        )

    def build_handoff(self, presentation_document=None):
        return handoff.build_witness_ownership_provider_conformance_presentation_handoff_v1(
            self.presentation_document
            if presentation_document is None
            else presentation_document,
            self.quorum_document,
            self.signed_reports,
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document,
            expected_presentation_envelope_hash=(
                self.presentation_document["presentation_envelope_hash"]
                if presentation_document is None
                else presentation_document["presentation_envelope_hash"]
            ),
            presentation_build_kwargs=self.presentation_build_kwargs,
        )

    def test_ordered_stage_contract_is_exact_and_neutral(self):
        self.assertEqual(
            self.presentation_document["ordered_stage_contract"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(self.presentation_document["display_tone"], "NEUTRAL")

    def test_source_axis_claims_only_local_exact_binding(self):
        axis = self.presentation_document["axes"][0]
        self.assertEqual(axis["stage"], "SOURCE")
        self.assertEqual(axis["state"], "LOCALLY_BOUND")
        self.assertTrue(
            self.presentation_document["facts"][
                "source_chain_exactly_verified"
            ]
        )

    def test_gap_axis_keeps_external_source_truth_open(self):
        axis = self.presentation_document["axes"][1]
        self.assertEqual(axis["stage"], "GAP")
        self.assertEqual(axis["state"], "OPEN")
        for name in (
            "observer_test_execution_source_truth_verified",
            "external_provider_conformance_verified",
            "durable_commit_verified",
            "linearizable_read_after_write_verified",
            "rollback_resistance_verified",
        ):
            self.assertFalse(self.presentation_document["facts"][name])

    def test_maturity_axis_does_not_promote_claims_to_execution(self):
        axis = self.presentation_document["axes"][2]
        self.assertEqual(axis["stage"], "MATURITY")
        self.assertEqual(axis["state"], "SIGNED_REPORT_CANDIDATE")
        self.assertEqual(
            self.presentation_document["summary"][
                "verified_execution_case_count"
            ],
            0,
        )

    def test_permission_axis_and_authority_remain_blocked(self):
        axis = self.presentation_document["axes"][3]
        self.assertEqual(axis, {
            "stage": "PERMISSION",
            "state": "BLOCKED",
            "detail": "ASSETS_ROUTE_BROWSER_MOUNT_CURRENT_RUNTIME_PAPER_LIVE_DISABLED",
        })
        self.assertTrue(
            all(
                value is False
                for key, value in self.presentation_document["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_summary_distinguishes_claimed_from_verified_cases(self):
        summary = self.presentation_document["summary"]
        self.assertEqual(summary["required_case_count"], 18)
        self.assertEqual(summary["claimed_case_count"], 18)
        self.assertEqual(summary["verified_execution_case_count"], 0)
        self.assertEqual(summary["required_observer_quorum"], 2)

    def test_raw_reports_keys_and_signatures_are_not_embedded(self):
        serialized = repr(self.presentation_document)
        for signed_report in self.signed_reports:
            self.assertNotIn(signed_report["signature_base64"], serialized)
            self.assertNotIn(signed_report["public_key_spki_base64"], serialized)
        self.assertFalse(
            self.presentation_document["facts"]["raw_observer_reports_embedded"]
        )

    def test_resealed_upstream_promotion_becomes_unknown(self):
        promoted = dict(self.quorum_document)
        promoted["admission_status"] = "READY"
        promoted.pop("quorum_evidence_hash")
        promoted = seal_strict_canonical_document(
            promoted, "quorum_evidence_hash"
        )
        document = presentation.build_witness_ownership_provider_conformance_presentation_envelope_v1(
            promoted,
            self.signed_reports,
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document,
            expected_observer_quorum_evidence_hash=promoted[
                "quorum_evidence_hash"
            ],
            observer_quorum_evaluation_kwargs=self.quorum_kwargs,
        )
        self.assertEqual(document["presentation_status"], "UNMOUNTED_UNKNOWN")
        self.assertTrue(
            all(axis["state"] == "UNKNOWN" for axis in document["axes"])
        )

    def test_exact_presentation_verifier_rejects_resealed_change(self):
        self.assertTrue(
            presentation.verify_witness_ownership_provider_conformance_presentation_envelope_v1(
                self.presentation_document,
                self.quorum_document,
                self.signed_reports,
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_presentation_envelope_hash=self.presentation_document[
                    "presentation_envelope_hash"
                ],
                **self.presentation_build_kwargs,
            )
        )
        changed = deepcopy(self.presentation_document)
        changed["axes"][2]["state"] = "COMPLETE"
        changed.pop("presentation_envelope_hash")
        changed = seal_strict_canonical_document(
            changed, "presentation_envelope_hash"
        )
        self.assertFalse(
            presentation.verify_witness_ownership_provider_conformance_presentation_envelope_v1(
                changed,
                self.quorum_document,
                self.signed_reports,
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_presentation_envelope_hash=changed[
                    "presentation_envelope_hash"
                ],
                **self.presentation_build_kwargs,
            )
        )

    def test_handoff_is_bounded_exact_and_unmounted(self):
        document = self.build_handoff()
        self.assertEqual(
            document["verification_status"],
            "EXACTLY_VERIFIED_NEUTRAL_BLOCKED_PRESENTATION_V1",
        )
        self.assertEqual(document["payload"]["permission"]["state"], "BLOCKED")
        self.assertFalse(document["facts"]["consumer_implementation_present"])
        self.assertFalse(document["facts"]["asset_manifest_complete"])
        self.assertFalse(document["facts"]["ui_mounted"])

    def test_handoff_rejects_unknown_presentation(self):
        unknown = presentation.build_witness_ownership_provider_conformance_presentation_envelope_v1(
            {},
            self.signed_reports,
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document,
            expected_observer_quorum_evidence_hash=self.quorum_document[
                "quorum_evidence_hash"
            ],
            observer_quorum_evaluation_kwargs=self.quorum_kwargs,
        )
        self.assertIsNone(self.build_handoff(unknown))

    def test_exact_handoff_verifier_rejects_permission_promotion(self):
        document = self.build_handoff()
        build_kwargs = {
            "expected_presentation_envelope_hash": (
                self.presentation_document["presentation_envelope_hash"]
            ),
            "presentation_build_kwargs": self.presentation_build_kwargs,
        }
        self.assertTrue(
            handoff.verify_witness_ownership_provider_conformance_presentation_handoff_v1(
                document,
                self.presentation_document,
                self.quorum_document,
                self.signed_reports,
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_handoff_hash=document["handoff_hash"],
                **build_kwargs,
            )
        )
        promoted = deepcopy(document)
        promoted["payload"]["permission"]["state"] = "ALLOWED"
        promoted.pop("handoff_hash")
        promoted = seal_strict_canonical_document(promoted, "handoff_hash")
        self.assertFalse(
            handoff.verify_witness_ownership_provider_conformance_presentation_handoff_v1(
                promoted,
                self.presentation_document,
                self.quorum_document,
                self.signed_reports,
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_handoff_hash=promoted["handoff_hash"],
                **build_kwargs,
            )
        )

    def test_output_is_deterministic_and_report_order_independent(self):
        reversed_document = presentation.build_witness_ownership_provider_conformance_presentation_envelope_v1(
            self.quorum_document,
            list(reversed(self.signed_reports)),
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document,
            **self.presentation_build_kwargs,
        )
        self.assertEqual(reversed_document, self.presentation_document)

    def test_presentation_contains_no_ready_or_profit_claim(self):
        serialized = repr(self.presentation_document) + repr(self.build_handoff())
        self.assertNotIn("READY", serialized)
        self.assertNotIn("PROFITABLE", serialized)
        self.assertFalse(self.presentation_document["facts"]["profitability_proven"])

    def test_production_has_no_assets_browser_io_or_private_keys(self):
        source = inspect.getsource(presentation) + inspect.getsource(handoff)
        for forbidden in (
            "Ed25519PrivateKey",
            "requests.",
            "socket.",
            "subprocess.",
            "sqlite3",
            "os.environ",
            "Path(",
            "open(",
            "playwright",
            "selenium",
            "static/styles.css",
            "static/app.js",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
