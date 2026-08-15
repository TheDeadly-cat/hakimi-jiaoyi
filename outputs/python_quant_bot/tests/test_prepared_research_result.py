from __future__ import annotations

from pathlib import Path
import tempfile
import unittest


from exchange_terminal.services.prepared_research_result import (
    build_prepared_research_result,
    load_prepared_research_result,
    prepared_research_result_path,
    publish_json_no_clobber,
    publish_prepared_research_result_no_clobber,
    verify_prepared_research_result,
)
from exchange_terminal.services.research_exposure import prior_symbol_exposure


class PreparedResearchResultTests(unittest.TestCase):
    def _protocol(self) -> dict[str, object]:
        return {
            "registration_id": "prepared-test",
            "protocol_hash": "a" * 64,
            "batch_spec_hash": "b" * 64,
        }

    def _claim(self) -> dict[str, object]:
        return {"claim_hash": "c" * 64}

    def _report(self) -> dict[str, object]:
        protocol = self._protocol()
        claim = self._claim()
        completion = {
            "result_hash": "d" * 64,
            "dataset_manifest_hash": "e" * 64,
        }
        return {
            "batch_spec_hash": "b" * 64,
            "dataset_manifest_hash": "e" * 64,
            "batch_run_hash": "d" * 64,
            "research_governance": {
                "protocol": protocol,
                "single_use_claim_receipt": claim,
                "completion_receipt": completion,
            },
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def _prepared(self) -> dict[str, object]:
        return build_prepared_research_result(
            workflow="NESTED_VARIANT_RESEARCH",
            registration_id="prepared-test",
            protocol_hash="a" * 64,
            claim_hash="c" * 64,
            batch_spec_hash="b" * 64,
            result_hash="d" * 64,
            dataset_manifest_hash="e" * 64,
            output_file="strategy_research_final.json",
            report=self._report(),
        )

    def _verify(self, prepared: dict[str, object]) -> dict[str, object]:
        return verify_prepared_research_result(
            prepared,
            expected_workflow="NESTED_VARIANT_RESEARCH",
            expected_protocol=self._protocol(),
            expected_claim=self._claim(),
            report_verifier=lambda _report: {"status": "PASS", "blockers": []},
            reserved_output_files={"current_strategy_research_report.json"},
        )

    def test_deterministic_hidden_basename_does_not_match_exposure_glob(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            path = prepared_research_result_path(
                report_dir,
                protocol_hash="a" * 64,
            )
            self.assertFalse(path.name.startswith("strategy_research_"))
            self.assertFalse(path.name.startswith("strategy_matrix_"))
            published = publish_prepared_research_result_no_clobber(
                report_dir,
                self._prepared(),
            )
            self.assertEqual(published["status"], "PUBLISHED")
            self.assertEqual(prior_symbol_exposure(report_dir), {})

    def test_prepared_publish_is_idempotent_but_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            prepared = self._prepared()
            first = publish_prepared_research_result_no_clobber(report_dir, prepared)
            second = publish_prepared_research_result_no_clobber(report_dir, prepared)
            tampered = dict(prepared)
            tampered["output_file"] = "strategy_research_other.json"
            conflict = publish_prepared_research_result_no_clobber(report_dir, tampered)
            loaded = load_prepared_research_result(
                report_dir,
                protocol_hash="a" * 64,
            )
        self.assertEqual(first["status"], "PUBLISHED")
        self.assertEqual(second["status"], "EXISTING_IDENTICAL")
        self.assertEqual(conflict["status"], "BLOCK")
        self.assertEqual(loaded["prepared"], prepared)

    def test_tamper_and_nested_execution_authority_fail_closed(self) -> None:
        prepared = self._prepared()
        prepared["result_hash"] = "f" * 64
        self.assertEqual(self._verify(prepared)["status"], "BLOCK")

        authority = self._prepared()
        authority["report"]["nested"] = {"can_trade": True}  # type: ignore[index]
        authority["prepared_hash"] = build_prepared_research_result(
            workflow="NESTED_VARIANT_RESEARCH",
            registration_id="prepared-test",
            protocol_hash="a" * 64,
            claim_hash="c" * 64,
            batch_spec_hash="b" * 64,
            result_hash="d" * 64,
            dataset_manifest_hash="e" * 64,
            output_file="strategy_research_final.json",
            report=authority["report"],  # type: ignore[arg-type]
        )["prepared_hash"]
        verification = self._verify(authority)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(any(
            "authority_not_false" in blocker
            for blocker in verification["blockers"]
        ))

    def test_reserved_output_comparison_is_case_insensitive(self) -> None:
        prepared = self._prepared()
        prepared["output_file"] = "CURRENT_STRATEGY_RESEARCH_REPORT.JSON"
        resealed = build_prepared_research_result(
            workflow="NESTED_VARIANT_RESEARCH",
            registration_id="prepared-test",
            protocol_hash="a" * 64,
            claim_hash="c" * 64,
            batch_spec_hash="b" * 64,
            result_hash="d" * 64,
            dataset_manifest_hash="e" * 64,
            output_file=str(prepared["output_file"]),
            report=prepared["report"],  # type: ignore[arg-type]
        )
        verification = self._verify(resealed)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "prepared_result_output_basename_invalid",
            verification["blockers"],
        )

    def test_matrix_workflow_binds_matrix_result_not_outer_run_hash(self) -> None:
        protocol = self._protocol()
        claim = self._claim()
        report = self._report()
        report.pop("batch_run_hash")
        report["matrix_result_hash"] = "d" * 64
        report["batch_run_hash"] = "f" * 64
        prepared = build_prepared_research_result(
            workflow="STRATEGY_MATRIX",
            registration_id="prepared-test",
            protocol_hash="a" * 64,
            claim_hash="c" * 64,
            batch_spec_hash="b" * 64,
            result_hash="d" * 64,
            dataset_manifest_hash="e" * 64,
            output_file="strategy_matrix_final.json",
            report=report,
        )
        verification = verify_prepared_research_result(
            prepared,
            expected_workflow="STRATEGY_MATRIX",
            expected_protocol=protocol,
            expected_claim=claim,
            report_verifier=lambda _report: {"status": "PASS", "blockers": []},
        )
        self.assertEqual(verification["status"], "PASS", verification["blockers"])

    def test_final_publish_never_overwrites_conflicting_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "final.json"
            first = publish_json_no_clobber(
                output,
                {"value": 1},
                failure_blocker="final_write_failed",
            )
            conflict = publish_json_no_clobber(
                output,
                {"value": 2},
                failure_blocker="final_write_failed",
            )
            self.assertEqual(output.read_text(encoding="utf-8"), "{\n  \"value\": 1\n}")
        self.assertEqual(first["status"], "PUBLISHED")
        self.assertEqual(conflict["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
