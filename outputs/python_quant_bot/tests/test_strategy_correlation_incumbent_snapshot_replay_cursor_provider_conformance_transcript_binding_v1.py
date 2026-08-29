from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import inspect
import unittest

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_evidence_v1
    as conformance_evidence,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_transcript_binding_v1
    as transcript_binding,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_conformance_evidence_v1
    as conformance_tests,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class ReplayCursorProviderConformanceTranscriptBindingV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        if cls.__dict__.get("_fixture_setup_complete_v1") is True:
            return
        fixture_class = (
            conformance_tests.ReplayCursorProviderConformanceEvidenceV1Tests
        )
        fixture_class.setUpClass()
        cls.fixture_class = fixture_class
        cls.plan_document = fixture_class.plan_document
        cls.provider_preregistration_document = (
            fixture_class.provider_preregistration_document
        )
        cls.signed_receipt_evidence_document = (
            fixture_class.signed_receipt_evidence_document
        )
        cls.upstream_kwargs = fixture_class.upstream_kwargs
        cls.runner_hashes = [
            _hash(f"synthetic-transcript-runner-{index + 1}")
            for index in range(3)
        ]
        cls.environment_hashes = [
            _hash(f"synthetic-transcript-environment-{index + 1}")
            for index in range(3)
        ]
        cls.transcript_rows = [
            cls._build_transcript_rows(index) for index in range(3)
        ]
        cls.bound_case_rows = [
            cls._build_bound_case_rows(index) for index in range(3)
        ]
        cls.bound_signed_reports = [
            fixture_class._build_signed_report(
                index, case_rows=cls.bound_case_rows[index]
            )
            for index in range(3)
        ]
        cls.quorum_evidence = conformance_evidence.evaluate_replay_cursor_provider_conformance_observer_quorum_v1(
            cls.bound_signed_reports[:2],
            cls.plan_document,
            cls.provider_preregistration_document,
            cls.signed_receipt_evidence_document,
            **cls.upstream_kwargs,
        )
        cls.manifests = [
            transcript_binding.build_replay_cursor_provider_conformance_transcript_manifest_v1(
                cls.bound_signed_reports[index],
                cls.plan_document,
                cls.signed_receipt_evidence_document,
                runner_implementation_sha256=cls.runner_hashes[index],
                environment_manifest_sha256=cls.environment_hashes[index],
                case_transcript_rows=cls.transcript_rows[index],
                expected_signed_observer_report_hash=(
                    cls.bound_signed_reports[index][
                        "signed_observer_report_hash"
                    ]
                ),
            )
            for index in range(2)
        ]
        cls.evaluation_kwargs = {
            "expected_quorum_evidence_hash": cls.quorum_evidence[
                "quorum_evidence_hash"
            ],
            "quorum_verify_kwargs": cls.upstream_kwargs,
        }
        cls._fixture_setup_complete_v1 = True

    @classmethod
    def _build_transcript_rows(cls, index: int):
        return [
            {
                "case_id": plan_row["case_id"],
                "status": "PASS",
                "transcript_artifact_sha256": _hash(
                    f"transcript-artifact-{index + 1}-{plan_row['case_id']}"
                ),
                "command_trace_sha256": _hash(
                    f"command-trace-{index + 1}-{plan_row['case_id']}"
                ),
                "result_trace_sha256": _hash(
                    f"result-trace-{index + 1}-{plan_row['case_id']}"
                ),
                "stdout_sha256": _hash(
                    f"stdout-{index + 1}-{plan_row['case_id']}"
                ),
                "stderr_sha256": _hash(
                    f"stderr-{index + 1}-{plan_row['case_id']}"
                ),
                "attempt_count": 1,
            }
            for plan_row in cls.plan_document["cases"]
        ]

    @classmethod
    def _build_bound_case_rows(cls, index: int):
        run_context_hash = _hash(
            f"synthetic-replay-run-context-{index + 1}"
        )
        return [
            {
                "case_id": row["case_id"],
                "status": row["status"],
                "evidence_hash": transcript_binding.build_replay_cursor_provider_conformance_case_transcript_evidence_hash_v1(
                    case_id=row["case_id"],
                    status=row["status"],
                    run_context_hash=run_context_hash,
                    runner_implementation_sha256=cls.runner_hashes[index],
                    environment_manifest_sha256=(
                        cls.environment_hashes[index]
                    ),
                    transcript_artifact_sha256=row[
                        "transcript_artifact_sha256"
                    ],
                    command_trace_sha256=row["command_trace_sha256"],
                    result_trace_sha256=row["result_trace_sha256"],
                    stdout_sha256=row["stdout_sha256"],
                    stderr_sha256=row["stderr_sha256"],
                    attempt_count=row["attempt_count"],
                ),
            }
            for row in cls.transcript_rows[index]
        ]

    def evaluate(self, manifests=None, *, quorum=None, reports=None):
        return transcript_binding.evaluate_replay_cursor_provider_conformance_transcript_binding_v1(
            self.manifests if manifests is None else manifests,
            self.quorum_evidence if quorum is None else quorum,
            self.bound_signed_reports[:2] if reports is None else reports,
            self.plan_document,
            self.provider_preregistration_document,
            self.signed_receipt_evidence_document,
            **self.evaluation_kwargs,
        )

    def test_reproduces_arbitrary_hash_without_manifest_gap(self):
        arbitrary_report = self.fixture_class.signed_reports[0]
        with self.assertRaises(ValueError):
            transcript_binding.build_replay_cursor_provider_conformance_transcript_manifest_v1(
                arbitrary_report,
                self.plan_document,
                self.signed_receipt_evidence_document,
                runner_implementation_sha256=self.runner_hashes[0],
                environment_manifest_sha256=self.environment_hashes[0],
                case_transcript_rows=self.transcript_rows[0],
                expected_signed_observer_report_hash=arbitrary_report[
                    "signed_observer_report_hash"
                ],
            )

    def test_case_evidence_hash_binds_every_context_dimension(self):
        row = self.transcript_rows[0][0]
        base = {
            "case_id": row["case_id"],
            "status": row["status"],
            "run_context_hash": _hash("hash-binding-run-context"),
            "runner_implementation_sha256": self.runner_hashes[0],
            "environment_manifest_sha256": self.environment_hashes[0],
            "transcript_artifact_sha256": row[
                "transcript_artifact_sha256"
            ],
            "command_trace_sha256": row["command_trace_sha256"],
            "result_trace_sha256": row["result_trace_sha256"],
            "stdout_sha256": row["stdout_sha256"],
            "stderr_sha256": row["stderr_sha256"],
            "attempt_count": row["attempt_count"],
        }
        original = transcript_binding.build_replay_cursor_provider_conformance_case_transcript_evidence_hash_v1(
            **base
        )
        for field in (
            "run_context_hash",
            "runner_implementation_sha256",
            "environment_manifest_sha256",
            "transcript_artifact_sha256",
            "command_trace_sha256",
            "result_trace_sha256",
            "stdout_sha256",
            "stderr_sha256",
        ):
            changed = dict(base)
            changed[field] = _hash("changed-" + field)
            self.assertNotEqual(
                original,
                transcript_binding.build_replay_cursor_provider_conformance_case_transcript_evidence_hash_v1(
                    **changed
                ),
            )

    def test_valid_binding_passes_locally_but_admission_blocks(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["admission_status"], "BLOCKED")
        self.assertTrue(
            result["facts"][
                "all_passing_reports_have_exact_transcript_manifests"
            ]
        )
        for name in (
            "transcript_artifacts_retrieved",
            "transcript_artifact_content_verified",
            "runner_implementation_verified",
            "environment_manifest_verified",
            "observer_test_execution_source_truth_verified",
            "external_provider_conformance_verified",
            "durable_commit_verified",
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

    def test_missing_duplicate_or_extra_manifest_is_blocked(self):
        missing = self.evaluate(manifests=self.manifests[:1])
        self.assertEqual(missing["status"], "BLOCK")
        duplicate = self.evaluate(
            manifests=[self.manifests[0], self.manifests[0]]
        )
        self.assertEqual(duplicate["status"], "BLOCK")
        self.assertIn(
            "DUPLICATE_TRANSCRIPT_MANIFEST_OBSERVER_ID",
            duplicate["blockers"],
        )

    def test_missing_reordered_or_changed_case_descriptor_is_rejected(self):
        for rows in (
            self.transcript_rows[0][:-1],
            list(reversed(self.transcript_rows[0])),
        ):
            with self.assertRaises(ValueError):
                transcript_binding.build_replay_cursor_provider_conformance_transcript_manifest_v1(
                    self.bound_signed_reports[0],
                    self.plan_document,
                    self.signed_receipt_evidence_document,
                    runner_implementation_sha256=self.runner_hashes[0],
                    environment_manifest_sha256=self.environment_hashes[0],
                    case_transcript_rows=rows,
                    expected_signed_observer_report_hash=(
                        self.bound_signed_reports[0][
                            "signed_observer_report_hash"
                        ]
                    ),
                )
        changed = deepcopy(self.transcript_rows[0])
        changed[0]["result_trace_sha256"] = _hash("changed-result-trace")
        with self.assertRaises(ValueError):
            transcript_binding.build_replay_cursor_provider_conformance_transcript_manifest_v1(
                self.bound_signed_reports[0],
                self.plan_document,
                self.signed_receipt_evidence_document,
                runner_implementation_sha256=self.runner_hashes[0],
                environment_manifest_sha256=self.environment_hashes[0],
                case_transcript_rows=changed,
                expected_signed_observer_report_hash=(
                    self.bound_signed_reports[0][
                        "signed_observer_report_hash"
                    ]
                ),
            )

    def test_wrong_signed_report_hash_is_rejected(self):
        with self.assertRaises(ValueError):
            transcript_binding.build_replay_cursor_provider_conformance_transcript_manifest_v1(
                self.bound_signed_reports[0],
                self.plan_document,
                self.signed_receipt_evidence_document,
                runner_implementation_sha256=self.runner_hashes[0],
                environment_manifest_sha256=self.environment_hashes[0],
                case_transcript_rows=self.transcript_rows[0],
                expected_signed_observer_report_hash=_hash(
                    "wrong-signed-observer-report"
                ),
            )

    def test_upstream_quorum_mutation_is_blocked(self):
        changed = deepcopy(self.quorum_evidence)
        changed["facts"]["external_provider_conformance_verified"] = True
        result = self.evaluate(quorum=changed)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "UPSTREAM_OBSERVER_QUORUM_NOT_EXACT", result["blockers"]
        )

    def test_manifest_verifier_rejects_resealed_promotion(self):
        manifest = self.manifests[0]
        self.assertTrue(
            transcript_binding.verify_replay_cursor_provider_conformance_transcript_manifest_v1(
                manifest,
                self.bound_signed_reports[0],
                self.plan_document,
                self.signed_receipt_evidence_document,
                expected_transcript_manifest_hash=manifest[
                    "transcript_manifest_hash"
                ],
            )
        )
        promoted = deepcopy(manifest)
        promoted["admission_status"] = "READY"
        promoted.pop("transcript_manifest_hash")
        promoted = seal_strict_canonical_document(
            promoted, "transcript_manifest_hash"
        )
        self.assertFalse(
            transcript_binding.verify_replay_cursor_provider_conformance_transcript_manifest_v1(
                promoted,
                self.bound_signed_reports[0],
                self.plan_document,
                self.signed_receipt_evidence_document,
                expected_transcript_manifest_hash=promoted[
                    "transcript_manifest_hash"
                ],
            )
        )

    def test_exact_binding_verifier_rejects_resealed_promotion(self):
        result = self.evaluate()
        self.assertTrue(
            transcript_binding.verify_replay_cursor_provider_conformance_transcript_binding_v1(
                result,
                self.manifests,
                self.quorum_evidence,
                self.bound_signed_reports[:2],
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_transcript_binding_hash=result[
                    "transcript_binding_hash"
                ],
                **self.evaluation_kwargs,
            )
        )
        promoted = deepcopy(result)
        promoted["admission_status"] = "READY"
        promoted.pop("transcript_binding_hash")
        promoted = seal_strict_canonical_document(
            promoted, "transcript_binding_hash"
        )
        self.assertFalse(
            transcript_binding.verify_replay_cursor_provider_conformance_transcript_binding_v1(
                promoted,
                self.manifests,
                self.quorum_evidence,
                self.bound_signed_reports[:2],
                self.plan_document,
                self.provider_preregistration_document,
                self.signed_receipt_evidence_document,
                expected_transcript_binding_hash=promoted[
                    "transcript_binding_hash"
                ],
                **self.evaluation_kwargs,
            )
        )

    def test_output_is_manifest_order_independent_and_redacted(self):
        first = self.evaluate()
        second = self.evaluate(manifests=list(reversed(self.manifests)))
        self.assertEqual(first, second)
        serialized = repr(first)
        for report in self.bound_signed_reports[:2]:
            self.assertNotIn(report["signature_base64"], serialized)
            self.assertNotIn(report["public_key_spki_base64"], serialized)

    def test_production_has_no_private_key_provider_call_io_or_runtime_access(self):
        source = inspect.getsource(transcript_binding)
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
