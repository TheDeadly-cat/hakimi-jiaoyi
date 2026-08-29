from __future__ import annotations

import base64
from copy import deepcopy
import inspect
import unittest

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_transcript_content_verifier_v1
    as content_verifier,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_transcript_binding_v1
    as binding_tests,
)


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


class ReplayCursorProviderConformanceTranscriptContentVerifierV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        if cls.__dict__.get("_fixture_setup_complete_v1") is True:
            return
        fixture_class = (
            binding_tests.ReplayCursorProviderConformanceTranscriptBindingV1Tests
        )
        fixture_class.setUpClass()
        cls.fixture_class = fixture_class
        fixture = fixture_class(
            methodName="test_valid_binding_passes_locally_but_admission_blocks"
        )
        cls.binding_document = fixture.evaluate()
        cls.manifests = fixture_class.manifests
        cls.quorum_evidence = fixture_class.quorum_evidence
        cls.bound_signed_reports = fixture_class.bound_signed_reports
        cls.plan_document = fixture_class.plan_document
        cls.provider_preregistration_document = (
            fixture_class.provider_preregistration_document
        )
        cls.signed_receipt_evidence_document = (
            fixture_class.signed_receipt_evidence_document
        )
        cls.binding_evaluation_kwargs = fixture_class.evaluation_kwargs
        cls.payload_rows = [
            cls._build_payload_rows(index) for index in range(2)
        ]
        cls.content_bundles = [
            content_verifier.build_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                cls.manifests[index],
                case_payload_rows=cls.payload_rows[index],
                expected_transcript_manifest_hash=cls.manifests[index][
                    "transcript_manifest_hash"
                ],
            )
            for index in range(2)
        ]
        cls.evaluation_kwargs = {
            "expected_transcript_binding_hash": cls.binding_document[
                "transcript_binding_hash"
            ],
            "transcript_binding_verify_kwargs": (
                cls.binding_evaluation_kwargs
            ),
        }
        cls._fixture_setup_complete_v1 = True

    @classmethod
    def _build_payload_rows(cls, index: int):
        return [
            {
                "case_id": row["case_id"],
                "transcript_artifact_base64url": _b64url(
                    f"transcript-artifact-{index + 1}-{row['case_id']}".encode(
                        "ascii"
                    )
                ),
                "command_trace_base64url": _b64url(
                    f"command-trace-{index + 1}-{row['case_id']}".encode(
                        "ascii"
                    )
                ),
                "result_trace_base64url": _b64url(
                    f"result-trace-{index + 1}-{row['case_id']}".encode(
                        "ascii"
                    )
                ),
                "stdout_base64url": _b64url(
                    f"stdout-{index + 1}-{row['case_id']}".encode("ascii")
                ),
                "stderr_base64url": _b64url(
                    f"stderr-{index + 1}-{row['case_id']}".encode("ascii")
                ),
            }
            for row in cls.manifests[index]["case_transcripts"]
        ]

    def evaluate(self, bundles=None, *, binding=None):
        return content_verifier.evaluate_replay_cursor_provider_conformance_transcript_content_v1(
            self.content_bundles if bundles is None else bundles,
            self.binding_document if binding is None else binding,
            self.manifests,
            self.quorum_evidence,
            self.bound_signed_reports[:2],
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document,
            **self.evaluation_kwargs,
        )

    def test_reproduces_hash_only_without_content_gap(self):
        self.assertEqual(self.binding_document["status"], "PASS")
        self.assertFalse(
            self.binding_document["facts"]["transcript_artifacts_retrieved"]
        )
        self.assertNotIn("case_payloads", self.binding_document)

    def test_valid_local_content_passes_without_availability_promotion(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["admission_status"], "BLOCKED")
        self.assertTrue(result["facts"]["local_component_hashes_verified"])
        self.assertTrue(result["facts"]["local_component_sizes_bounded"])
        for name in (
            "external_artifact_retrieval_verified",
            "public_artifact_availability_verified",
            "external_persistence_verified",
            "runner_implementation_verified",
            "observer_test_execution_source_truth_verified",
            "external_provider_conformance_verified",
            "execution_verified",
        ):
            self.assertFalse(result["facts"][name])
        self.assertTrue(
            all(
                value is False
                for key, value in result["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_missing_duplicate_or_wrong_observer_bundle_is_blocked(self):
        missing = self.evaluate(bundles=self.content_bundles[:1])
        self.assertEqual(missing["status"], "BLOCK")
        duplicate = self.evaluate(
            bundles=[self.content_bundles[0], self.content_bundles[0]]
        )
        self.assertEqual(duplicate["status"], "BLOCK")
        self.assertIn(
            "DUPLICATE_CONTENT_BUNDLE_OBSERVER_ID", duplicate["blockers"]
        )
        changed = deepcopy(self.content_bundles[0])
        changed["observer_id"] = "synthetic-unbound-observer"
        changed.pop("content_bundle_hash")
        changed = seal_strict_canonical_document(
            changed, "content_bundle_hash"
        )
        wrong = self.evaluate(bundles=[changed, self.content_bundles[1]])
        self.assertEqual(wrong["status"], "BLOCK")

    def test_missing_reordered_or_noncanonical_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            content_verifier.build_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                self.manifests[0],
                case_payload_rows=self.payload_rows[0][:-1],
                expected_transcript_manifest_hash=self.manifests[0][
                    "transcript_manifest_hash"
                ],
            )
        reordered = deepcopy(self.payload_rows[0])
        reordered[0], reordered[1] = reordered[1], reordered[0]
        with self.assertRaises(ValueError):
            content_verifier.build_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                self.manifests[0],
                case_payload_rows=reordered,
                expected_transcript_manifest_hash=self.manifests[0][
                    "transcript_manifest_hash"
                ],
            )
        padded = deepcopy(self.payload_rows[0])
        padded[0]["stdout_base64url"] += "="
        with self.assertRaises(ValueError):
            content_verifier.build_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                self.manifests[0],
                case_payload_rows=padded,
                expected_transcript_manifest_hash=self.manifests[0][
                    "transcript_manifest_hash"
                ],
            )

    def test_changed_content_or_manifest_hash_is_rejected(self):
        changed = deepcopy(self.payload_rows[0])
        changed[0]["result_trace_base64url"] = _b64url(
            b"different-result-trace"
        )
        with self.assertRaises(ValueError):
            content_verifier.build_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                self.manifests[0],
                case_payload_rows=changed,
                expected_transcript_manifest_hash=self.manifests[0][
                    "transcript_manifest_hash"
                ],
            )
        with self.assertRaises(ValueError):
            content_verifier.build_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                self.manifests[0],
                case_payload_rows=self.payload_rows[0],
                expected_transcript_manifest_hash="0" * 64,
            )

    def test_per_component_size_limit_is_enforced(self):
        oversized = deepcopy(self.payload_rows[0])
        oversized[0]["stdout_base64url"] = _b64url(
            b"x" * (content_verifier.MAX_CASE_COMPONENT_BYTES + 1)
        )
        with self.assertRaises(ValueError):
            content_verifier.build_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                self.manifests[0],
                case_payload_rows=oversized,
                expected_transcript_manifest_hash=self.manifests[0][
                    "transcript_manifest_hash"
                ],
            )

    def test_upstream_binding_mutation_is_blocked(self):
        changed = deepcopy(self.binding_document)
        changed["facts"]["external_provider_conformance_verified"] = True
        result = self.evaluate(binding=changed)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("UPSTREAM_TRANSCRIPT_BINDING_NOT_EXACT", result["blockers"])

    def test_bundle_verifier_rejects_resealed_promotion(self):
        bundle = self.content_bundles[0]
        self.assertTrue(
            content_verifier.verify_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                bundle,
                self.manifests[0],
                expected_content_bundle_hash=bundle["content_bundle_hash"],
            )
        )
        promoted = deepcopy(bundle)
        promoted["admission_status"] = "READY"
        promoted.pop("content_bundle_hash")
        promoted = seal_strict_canonical_document(
            promoted, "content_bundle_hash"
        )
        self.assertFalse(
            content_verifier.verify_replay_cursor_provider_conformance_transcript_content_bundle_v1(
                promoted,
                self.manifests[0],
                expected_content_bundle_hash=promoted["content_bundle_hash"],
            )
        )

    def test_exact_evidence_verifier_rejects_resealed_promotion(self):
        result = self.evaluate()
        self.assertTrue(
            content_verifier.verify_replay_cursor_provider_conformance_transcript_content_v1(
                result,
                self.content_bundles,
                self.binding_document,
                self.manifests,
                self.quorum_evidence,
                self.bound_signed_reports[:2],
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_content_verification_hash=result[
                    "content_verification_hash"
                ],
                **self.evaluation_kwargs,
            )
        )
        promoted = deepcopy(result)
        promoted["admission_status"] = "READY"
        promoted.pop("content_verification_hash")
        promoted = seal_strict_canonical_document(
            promoted, "content_verification_hash"
        )
        self.assertFalse(
            content_verifier.verify_replay_cursor_provider_conformance_transcript_content_v1(
                promoted,
                self.content_bundles,
                self.binding_document,
                self.manifests,
                self.quorum_evidence,
                self.bound_signed_reports[:2],
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_content_verification_hash=promoted[
                    "content_verification_hash"
                ],
                **self.evaluation_kwargs,
            )
        )

    def test_output_is_bundle_order_independent_and_redacted(self):
        first = self.evaluate()
        second = self.evaluate(bundles=list(reversed(self.content_bundles)))
        self.assertEqual(first, second)
        serialized = repr(first)
        for row in self.payload_rows[0]:
            for key, value in row.items():
                if key != "case_id":
                    self.assertNotIn(value, serialized)

    def test_production_has_no_provider_call_file_network_or_runtime_access(self):
        source = inspect.getsource(content_verifier)
        for forbidden in (
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
