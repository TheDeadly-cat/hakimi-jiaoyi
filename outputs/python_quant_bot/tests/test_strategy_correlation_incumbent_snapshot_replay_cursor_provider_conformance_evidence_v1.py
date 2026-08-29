from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import inspect
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_evidence_v1
    as evidence,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_plan_v1
    as plan,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_receipt_v1
    as receipt_tests,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class ReplayCursorProviderConformanceEvidenceV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if cls.__dict__.get("_fixture_setup_complete_v1") is True:
            return
        receipt_fixture_class = (
            receipt_tests.ReplayCursorProviderSignedReceiptV1Tests
        )
        receipt_fixture_class.setUpClass()
        fixture = receipt_fixture_class(
            methodName="test_valid_preregistered_key_receipt_is_local_only"
        )
        fixture.setUp()
        cls.provider_preregistration_document = (
            fixture.preregistration_document
        )
        cls.provider_preregistration_kwargs = dict(
            fixture.preregistration_kwargs
        )
        cls.signed_receipt_evidence_document = fixture._evaluate()
        cls.signed_receipt_verify_args = (
            fixture.signed_document,
            fixture.claim,
            fixture.command,
            fixture.result,
            fixture.registration_evidence_document,
            fixture.signed_registration_document,
            fixture.registration_claim_document,
            fixture.preregistration_document,
        )
        cls.signed_receipt_verify_kwargs = {
            "public_key_spki_base64": fixture.public_key_spki_base64,
            "signature_base64": fixture.signature_base64,
            "expected_signed_receipt_hash": fixture.signed_document[
                "signed_receipt_hash"
            ],
            "expected_receipt_claim_hash": fixture.claim[
                "receipt_claim_hash"
            ],
            "expected_registration_evidence_hash": (
                fixture.registration_evidence_hash
            ),
            "registration_verification_kwargs": (
                fixture.registration_verification_kwargs
            ),
        }
        cls.observer_private_keys = [
            Ed25519PrivateKey.generate() for _ in range(3)
        ]
        cls.observer_spki = [
            key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            for key in cls.observer_private_keys
        ]
        cls.observer_registrations = [
            {
                "observer_id": f"synthetic-replay-observer-{index + 1}",
                "public_key_spki_sha256": sha256(spki).hexdigest(),
                "organization_claim_hash": _hash(
                    f"synthetic-replay-observer-organization-{index + 1}"
                ),
                "trust_domain": (
                    f"synthetic.replay.observer{index + 1}.local"
                ),
            }
            for index, spki in enumerate(cls.observer_spki)
        ]
        cls.plan_document = plan.build_replay_cursor_provider_conformance_plan_v1(
            cls.provider_preregistration_document,
            observer_registrations=cls.observer_registrations,
            **cls.provider_preregistration_kwargs,
        )
        cls.upstream_kwargs = {
            "observer_registrations": cls.observer_registrations,
            "provider_preregistration_kwargs": (
                cls.provider_preregistration_kwargs
            ),
            "signed_receipt_verify_args": cls.signed_receipt_verify_args,
            "signed_receipt_verify_kwargs": (
                cls.signed_receipt_verify_kwargs
            ),
            "expected_signed_receipt_evidence_hash": (
                cls.signed_receipt_evidence_document[
                    "verification_evidence_hash"
                ]
            ),
        }
        cls.case_rows = [
            {
                "case_id": case_id,
                "status": "PASS",
                "evidence_hash": _hash(
                    f"synthetic-replay-case-evidence-{case_id}"
                ),
            }
            for case_id in plan.EXPECTED_CASE_IDS
        ]
        cls.signed_reports = [
            cls._build_signed_report(index) for index in range(3)
        ]
        cls._fixture_setup_complete_v1 = True

    @classmethod
    def _build_signed_report(
        cls,
        index: int,
        *,
        case_rows=None,
        signature_bytes=None,
    ):
        rows = cls.case_rows if case_rows is None else case_rows
        report = evidence.build_replay_cursor_provider_conformance_observer_report_v1(
            cls.plan_document,
            cls.provider_preregistration_document,
            cls.signed_receipt_evidence_document,
            observer_id=cls.observer_registrations[index]["observer_id"],
            run_context_hash=_hash(
                f"synthetic-replay-run-context-{index + 1}"
            ),
            case_rows=rows,
            **cls.upstream_kwargs,
        )
        message_hash = evidence.build_replay_cursor_provider_conformance_observer_signature_message_hash_v1(
            report,
            cls.plan_document,
            cls.signed_receipt_evidence_document,
        )
        signature = (
            cls.observer_private_keys[index].sign(bytes.fromhex(message_hash))
            if signature_bytes is None
            else signature_bytes
        )
        return evidence.build_signed_replay_cursor_provider_conformance_observer_report_v1(
            report,
            cls.plan_document,
            cls.provider_preregistration_document,
            cls.signed_receipt_evidence_document,
            public_key_spki_base64=base64.b64encode(
                cls.observer_spki[index]
            ).decode("ascii"),
            signature_base64=base64.b64encode(signature).decode("ascii"),
            report_verify_kwargs=cls.upstream_kwargs,
        )

    def evaluate(self, rows=None, *, receipt_evidence=None):
        return evidence.evaluate_replay_cursor_provider_conformance_observer_quorum_v1(
            self.signed_reports[:2] if rows is None else rows,
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document
            if receipt_evidence is None
            else receipt_evidence,
            **self.upstream_kwargs,
        )

    def test_reproduces_unconsumed_provider_self_signature_gap(self):
        self.assertEqual(self.signed_receipt_evidence_document["status"], "PASS")
        self.assertFalse(
            self.signed_receipt_evidence_document["facts"][
                "actual_provider_invocation_verified"
            ]
        )
        self.assertFalse(
            self.signed_receipt_evidence_document["facts"][
                "provider_registered"
            ]
        )

    def test_plan_is_exact_not_run_and_permission_locked(self):
        self.assertTrue(
            plan.verify_replay_cursor_provider_conformance_plan_v1(
                self.plan_document,
                self.provider_preregistration_document,
                observer_registrations=self.observer_registrations,
                **self.provider_preregistration_kwargs,
            )
        )
        self.assertEqual(len(self.plan_document["cases"]), 19)
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

    def test_observer_structural_separation_is_enforced(self):
        for field in (
            "observer_id",
            "public_key_spki_sha256",
            "organization_claim_hash",
            "trust_domain",
        ):
            registrations = deepcopy(self.observer_registrations)
            registrations[1][field] = registrations[0][field]
            with self.assertRaises(ValueError):
                plan.build_replay_cursor_provider_conformance_plan_v1(
                    self.provider_preregistration_document,
                    observer_registrations=registrations,
                    **self.provider_preregistration_kwargs,
                )
        registrations = deepcopy(self.observer_registrations)
        registrations[0]["public_key_spki_sha256"] = (
            self.provider_preregistration_document["identity"][
                "public_key_spki_sha256"
            ]
        )
        with self.assertRaises(ValueError):
            plan.build_replay_cursor_provider_conformance_plan_v1(
                self.provider_preregistration_document,
                observer_registrations=registrations,
                **self.provider_preregistration_kwargs,
            )

    def test_missing_or_reordered_case_is_rejected(self):
        with self.assertRaises(ValueError):
            self._build_signed_report(0, case_rows=self.case_rows[:-1])
        reordered = deepcopy(self.case_rows)
        reordered[0], reordered[1] = reordered[1], reordered[0]
        with self.assertRaises(ValueError):
            self._build_signed_report(0, case_rows=reordered)

    def test_failed_case_report_cannot_join_passing_quorum(self):
        failed_rows = deepcopy(self.case_rows)
        failed_rows[0]["status"] = "FAIL"
        failed_report = self._build_signed_report(1, case_rows=failed_rows)
        result = self.evaluate(rows=[self.signed_reports[0], failed_report])
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "OBSERVER_SIGNATURE_QUORUM_NOT_MET", result["blockers"]
        )

    def test_two_of_three_signed_claims_pass_locally_but_admission_blocks(self):
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
            "atomic_compare_and_advance_verified",
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
        wrong_spki = wrong_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        changed = deepcopy(self.signed_reports[0])
        changed["public_key_spki_base64"] = base64.b64encode(
            wrong_spki
        ).decode("ascii")
        changed["public_key_spki_sha256"] = sha256(wrong_spki).hexdigest()
        changed["signature_base64"] = base64.b64encode(
            wrong_key.sign(bytes.fromhex(changed["signature_message_hash"]))
        ).decode("ascii")
        changed.pop("signed_observer_report_hash")
        changed = seal_strict_canonical_document(
            changed, "signed_observer_report_hash"
        )
        result = self.evaluate(rows=[changed, self.signed_reports[1]])
        self.assertEqual(result["status"], "BLOCK")

    def test_tampered_report_is_blocked(self):
        changed = deepcopy(self.signed_reports[0])
        changed["observer_report"]["cases"][0]["evidence_hash"] = _hash(
            "tampered-replay-case-evidence"
        )
        changed.pop("signed_observer_report_hash")
        changed = seal_strict_canonical_document(
            changed, "signed_observer_report_hash"
        )
        result = self.evaluate(rows=[changed, self.signed_reports[1]])
        self.assertEqual(result["status"], "BLOCK")

    def test_duplicate_or_single_observer_does_not_form_quorum(self):
        duplicate = self.evaluate(
            rows=[self.signed_reports[0], self.signed_reports[0]]
        )
        self.assertEqual(duplicate["status"], "BLOCK")
        self.assertIn("DUPLICATE_OBSERVER_ID", duplicate["blockers"])
        single = self.evaluate(rows=[self.signed_reports[0]])
        self.assertEqual(single["status"], "BLOCK")
        self.assertIn(
            "OBSERVER_REPORT_COUNT_NOT_TWO_OR_THREE", single["blockers"]
        )

    def test_two_valid_of_three_allow_local_quorum_with_one_invalid(self):
        invalid = deepcopy(self.signed_reports[2])
        signature = bytearray(base64.b64decode(invalid["signature_base64"]))
        signature[0] ^= 1
        invalid["signature_base64"] = base64.b64encode(
            bytes(signature)
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

    def test_tampered_upstream_signed_receipt_is_blocked(self):
        changed = deepcopy(self.signed_receipt_evidence_document)
        changed["facts"]["provider_registered"] = True
        result = self.evaluate(receipt_evidence=changed)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "UPSTREAM_PLAN_OR_SIGNED_RECEIPT_NOT_EXACT",
            result["blockers"],
        )

    def test_exact_quorum_verifier_rejects_resealed_promotion(self):
        result = self.evaluate()
        self.assertTrue(
            evidence.verify_replay_cursor_provider_conformance_observer_quorum_v1(
                result,
                self.signed_reports[:2],
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_quorum_evidence_hash=result[
                    "quorum_evidence_hash"
                ],
                **self.upstream_kwargs,
            )
        )
        promoted = deepcopy(result)
        promoted["admission_status"] = "READY"
        promoted.pop("quorum_evidence_hash")
        promoted = seal_strict_canonical_document(
            promoted, "quorum_evidence_hash"
        )
        self.assertFalse(
            evidence.verify_replay_cursor_provider_conformance_observer_quorum_v1(
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

    def test_output_is_order_independent_deterministic_and_redacted(self):
        first = self.evaluate()
        second = self.evaluate(
            rows=[self.signed_reports[1], self.signed_reports[0]]
        )
        self.assertEqual(first, second)
        serialized = repr(first)
        for report in self.signed_reports[:2]:
            self.assertNotIn(report["signature_base64"], serialized)
            self.assertNotIn(report["public_key_spki_base64"], serialized)

    def test_production_has_no_provider_call_private_key_io_or_runtime_access(self):
        source = inspect.getsource(plan) + inspect.getsource(evidence)
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
            ".compare_and_advance(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
