from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import inspect
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    witness_ownership_state_provider_conformance_evidence_v1 as evidence,
)
from exchange_terminal.application import (
    witness_ownership_state_provider_conformance_plan_v1 as plan,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_witness_ownership_state_signed_receipt_v1 as adr0413_tests


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class WitnessOwnershipProviderConformanceEvidenceV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = adr0413_tests.WitnessOwnershipStateSignedReceiptV1Tests(
            methodName="test_valid_signature_passes_but_admission_remains_blocked"
        )
        fixture.setUp()
        self.provider_preregistration_document = (
            fixture.preregistration_document
        )
        self.provider_preregistration_kwargs = fixture.preregistration_kwargs
        self.signed_receipt_evidence_document = fixture.evaluate()
        self.signed_receipt_verify_args = (
            fixture.signed_document,
            fixture.consumer_document,
            fixture.v11_document,
            fixture.command,
            fixture.result,
            fixture.preregistration_document,
        )
        self.signed_receipt_verify_kwargs = {
            "public_key_spki_base64": fixture.public_spki_base64,
            "signature_base64": fixture.signature_base64,
            "expected_signed_receipt_hash": fixture.signed_document[
                "signed_receipt_hash"
            ],
            "expected_consumer_evaluation_hash": fixture.consumer_document[
                "evaluation_hash"
            ],
            "consumer_verify_kwargs": fixture.consumer_verify_kwargs,
            "preregistration_build_kwargs": fixture.preregistration_kwargs,
        }
        self.observer_private_keys = [Ed25519PrivateKey.generate() for _ in range(3)]
        self.observer_spki = [
            key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            for key in self.observer_private_keys
        ]
        self.observer_registrations = [
            {
                "observer_id": f"synthetic-observer-{index + 1}",
                "public_key_spki_sha256": sha256(spki).hexdigest(),
                "organization_claim_hash": _hash(
                    f"synthetic-observer-organization-{index + 1}"
                ),
                "trust_domain": f"synthetic.observer{index + 1}.local",
            }
            for index, spki in enumerate(self.observer_spki)
        ]
        self.plan_document = plan.build_witness_ownership_state_provider_conformance_plan_v1(
            self.provider_preregistration_document,
            observer_registrations=self.observer_registrations,
            **self.provider_preregistration_kwargs,
        )
        self.upstream_kwargs = {
            "observer_registrations": self.observer_registrations,
            "provider_preregistration_kwargs": (
                self.provider_preregistration_kwargs
            ),
            "signed_receipt_verify_args": self.signed_receipt_verify_args,
            "signed_receipt_verify_kwargs": self.signed_receipt_verify_kwargs,
            "expected_signed_receipt_evidence_hash": (
                self.signed_receipt_evidence_document[
                    "verification_evidence_hash"
                ]
            ),
        }
        self.case_rows = [
            {
                "case_id": case_id,
                "status": "PASS",
                "evidence_hash": _hash(f"synthetic-case-evidence-{case_id}"),
            }
            for case_id in plan.EXPECTED_CASE_IDS
        ]
        self.signed_reports = [self.build_signed_report(index) for index in range(3)]

    def build_signed_report(self, index: int, *, case_rows=None, signature_bytes=None):
        rows = self.case_rows if case_rows is None else case_rows
        report = evidence.build_witness_ownership_provider_conformance_observer_report_v1(
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document,
            observer_id=self.observer_registrations[index]["observer_id"],
            run_context_hash=_hash(f"synthetic-run-context-{index + 1}"),
            case_rows=rows,
            **self.upstream_kwargs,
        )
        message_hash = evidence.build_witness_ownership_provider_conformance_observer_signature_message_hash_v1(
            report,
            self.plan_document,
            self.signed_receipt_evidence_document,
        )
        signature = (
            self.observer_private_keys[index].sign(bytes.fromhex(message_hash))
            if signature_bytes is None
            else signature_bytes
        )
        public_key_base64 = base64.b64encode(self.observer_spki[index]).decode(
            "ascii"
        )
        signature_base64 = base64.b64encode(signature).decode("ascii")
        return evidence.build_signed_witness_ownership_provider_conformance_observer_report_v1(
            report,
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document,
            public_key_spki_base64=public_key_base64,
            signature_base64=signature_base64,
            report_verify_kwargs=self.upstream_kwargs,
        )

    def evaluate(self, rows=None):
        return evidence.evaluate_witness_ownership_provider_conformance_observer_quorum_v1(
            self.signed_reports[:2] if rows is None else rows,
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document,
            **self.upstream_kwargs,
        )

    def test_reproduces_provider_self_signature_conformance_gap(self):
        self.assertEqual(self.signed_receipt_evidence_document["status"], "PASS")
        self.assertFalse(
            self.signed_receipt_evidence_document["facts"][
                "external_provider_conformance_verified"
            ]
        )
        self.assertFalse(
            self.signed_receipt_evidence_document["facts"][
                "provider_organization_identity_verified"
            ]
        )

    def test_plan_is_exact_not_run_and_permission_locked(self):
        self.assertTrue(
            plan.verify_witness_ownership_state_provider_conformance_plan_v1(
                self.plan_document,
                self.provider_preregistration_document,
                observer_registrations=self.observer_registrations,
                **self.provider_preregistration_kwargs,
            )
        )
        self.assertEqual(len(self.plan_document["cases"]), 18)
        self.assertTrue(
            all(
                row["execution_status"] == "NOT_RUN"
                for row in self.plan_document["cases"]
            )
        )
        self.assertTrue(
            all(
                value is False
                for key, value in self.plan_document["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_duplicate_observer_identity_is_rejected_by_plan(self):
        registrations = deepcopy(self.observer_registrations)
        registrations[1]["observer_id"] = registrations[0]["observer_id"]
        with self.assertRaises(ValueError):
            plan.build_witness_ownership_state_provider_conformance_plan_v1(
                self.provider_preregistration_document,
                observer_registrations=registrations,
                **self.provider_preregistration_kwargs,
            )

    def test_provider_key_cannot_be_reused_as_observer_key(self):
        registrations = deepcopy(self.observer_registrations)
        registrations[0]["public_key_spki_sha256"] = (
            self.provider_preregistration_document["identity"][
                "public_key_spki_sha256"
            ]
        )
        with self.assertRaises(ValueError):
            plan.build_witness_ownership_state_provider_conformance_plan_v1(
                self.provider_preregistration_document,
                observer_registrations=registrations,
                **self.provider_preregistration_kwargs,
            )

    def test_missing_case_is_rejected(self):
        with self.assertRaises(ValueError):
            self.build_signed_report(0, case_rows=self.case_rows[:-1])

    def test_failed_case_report_cannot_join_passing_quorum(self):
        failed_rows = deepcopy(self.case_rows)
        failed_rows[0]["status"] = "FAIL"
        failed_report = self.build_signed_report(1, case_rows=failed_rows)
        result = self.evaluate(rows=[self.signed_reports[0], failed_report])
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("OBSERVER_SIGNATURE_QUORUM_NOT_MET", result["blockers"])

    def test_two_of_three_signed_reports_pass_locally_but_admission_blocks(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["admission_status"], "BLOCKED")
        self.assertTrue(
            result["facts"]["signed_observer_report_quorum_verified"]
        )
        for name in (
            "observer_identities_verified",
            "observer_independence_source_truth_verified",
            "observer_test_execution_source_truth_verified",
            "external_provider_conformance_verified",
            "durable_commit_verified",
            "linearizable_read_after_write_verified",
            "rollback_resistance_verified",
        ):
            self.assertFalse(result["facts"][name])
        self.assertTrue(
            all(
                value is False
                for key, value in result["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_wrong_observer_key_is_blocked(self):
        wrong_key = Ed25519PrivateKey.generate()
        message_hash = self.signed_reports[0]["signature_message_hash"]
        wrong_signature = wrong_key.sign(bytes.fromhex(message_hash))
        wrong_spki = wrong_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        wrong_document = deepcopy(self.signed_reports[0])
        wrong_document["public_key_spki_base64"] = base64.b64encode(
            wrong_spki
        ).decode("ascii")
        wrong_document["public_key_spki_sha256"] = sha256(wrong_spki).hexdigest()
        wrong_document["signature_base64"] = base64.b64encode(
            wrong_signature
        ).decode("ascii")
        wrong_document.pop("signed_observer_report_hash")
        wrong_document = seal_strict_canonical_document(
            wrong_document, "signed_observer_report_hash"
        )
        result = self.evaluate(rows=[wrong_document, self.signed_reports[1]])
        self.assertEqual(result["status"], "BLOCK")

    def test_tampered_report_is_blocked(self):
        changed = deepcopy(self.signed_reports[0])
        changed["observer_report"]["cases"][0]["evidence_hash"] = _hash(
            "tampered-evidence"
        )
        changed.pop("signed_observer_report_hash")
        changed = seal_strict_canonical_document(
            changed, "signed_observer_report_hash"
        )
        result = self.evaluate(rows=[changed, self.signed_reports[1]])
        self.assertEqual(result["status"], "BLOCK")

    def test_duplicate_signed_observer_rows_do_not_form_quorum(self):
        result = self.evaluate(
            rows=[self.signed_reports[0], self.signed_reports[0]]
        )
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("DUPLICATE_OBSERVER_ID", result["blockers"])

    def test_one_report_does_not_form_quorum(self):
        result = self.evaluate(rows=[self.signed_reports[0]])
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "OBSERVER_REPORT_COUNT_NOT_TWO_OR_THREE", result["blockers"]
        )

    def test_two_valid_of_three_allow_local_quorum_with_one_invalid(self):
        changed_signature = bytearray(
            base64.b64decode(self.signed_reports[2]["signature_base64"])
        )
        changed_signature[0] ^= 1
        invalid = deepcopy(self.signed_reports[2])
        invalid["signature_base64"] = base64.b64encode(
            bytes(changed_signature)
        ).decode("ascii")
        invalid.pop("signed_observer_report_hash")
        invalid = seal_strict_canonical_document(
            invalid, "signed_observer_report_hash"
        )
        result = self.evaluate(
            rows=[self.signed_reports[0], self.signed_reports[1], invalid]
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            len(result["quorum_summary"]["passing_observer_ids"]), 2
        )

    def test_exact_quorum_verifier_rejects_resealed_promotion(self):
        result = self.evaluate()
        self.assertTrue(
            evidence.verify_witness_ownership_provider_conformance_observer_quorum_v1(
                result,
                self.signed_reports[:2],
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_quorum_evidence_hash=result["quorum_evidence_hash"],
                **self.upstream_kwargs,
            )
        )
        promoted = dict(result)
        promoted["admission_status"] = "READY"
        promoted.pop("quorum_evidence_hash")
        promoted = seal_strict_canonical_document(
            promoted, "quorum_evidence_hash"
        )
        self.assertFalse(
            evidence.verify_witness_ownership_provider_conformance_observer_quorum_v1(
                promoted,
                self.signed_reports[:2],
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_quorum_evidence_hash=promoted[
                    "quorum_evidence_hash"
                ],
                **self.upstream_kwargs,
            )
        )

    def test_output_is_deterministic_order_independent_and_redacted(self):
        first = self.evaluate()
        second = self.evaluate(
            rows=[self.signed_reports[1], self.signed_reports[0]]
        )
        self.assertEqual(first, second)
        serialized = repr(first)
        for signed_report in self.signed_reports[:2]:
            self.assertNotIn(signed_report["signature_base64"], serialized)
            self.assertNotIn(signed_report["public_key_spki_base64"], serialized)

    def test_production_has_no_provider_call_private_key_or_io(self):
        source = inspect.getsource(plan) + inspect.getsource(evidence)
        self.assertIn("decode_canonical_base64_v1", source)
        self.assertIn("load_canonical_ed25519_public_key_v1", source)
        for forbidden in (
            "Ed25519PrivateKey",
            "base64.b64decode",
            "requests.",
            "socket.",
            "subprocess.",
            "sqlite3",
            "os.environ",
            "Path(",
            "open(",
            ".compare_consume_and_advance(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
