"""Inert-metadata admission tests; never run a historical strategy."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
SPEC = importlib.util.spec_from_file_location("_diagnostic_manifest", ROOT / "tools/run_strategy_diagnostics.py")
diagnostic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostic)


def inert_manifest():
    plan = diagnostic.read_document(ROOT / "docs/studies/strategy-diagnostics-plan-20260906.json")
    return {"schema_version": "strategy-diagnostics-run-v1", "plan": plan,
            "plan_hash": diagnostic.digest(plan), "source_content_sha256": diagnostic.SOURCE,
            "wheel_sha256": diagnostic.WHEEL, "cells": [
                {"method": method["label"], "cost_factor": cost, "status": "COMPLETED", "plan_hash": diagnostic.digest(plan),
                 "source_content_sha256": diagnostic.SOURCE, "wheel_sha256": diagnostic.WHEEL,
                 "snapshot_path": "inert-dataset.json", "snapshot_file_sha256": "a" * 64,
                 "report_path": "inert-report.json", "report_file_sha256": "b" * 64,
                 "report_hash": "c" * 64, "spec_path": "inert-spec.json"}
                for method in plan["methods"] for cost in plan["cost_factors"]]}


class DiagnosticManifestBindingTests(unittest.TestCase):
    def test_exact_unique_frozen_matrix_and_types_are_required(self):
        original = inert_manifest()
        self.assertEqual(len(diagnostic.validate_manifest(original)[1]), 16)
        mutations = [lambda m: m["cells"].__setitem__(1, copy.deepcopy(m["cells"][0])),
                     lambda m: m["cells"][0].__setitem__("cost_factor", False),
                     lambda m: m.__setitem__("plan_hash", "0" * 64),
                     lambda m: m["cells"][0].__setitem__("source_content_sha256", "0" * 64),
                     lambda m: m["cells"][0].__setitem__("snapshot_file_sha256", "0" * 64),
                     lambda m: m["cells"].pop()]
        for mutate in mutations:
            candidate = copy.deepcopy(original)
            mutate(candidate)
            with self.assertRaises(ValueError):
                diagnostic.validate_manifest(candidate)

    def test_swapped_label_cannot_reuse_another_configuration_report(self):
        manifest = inert_manifest()
        plan, cells = diagnostic.validate_manifest(manifest)
        snapshot = SimpleNamespace(snapshot_id="d" * 64)
        cell = cells[("D0", 0)]
        expected = diagnostic.make_spec(plan, snapshot, plan["methods"][0], 0).document
        report = {"report_hash": cell["report_hash"], "spec": expected,
                  "evidence": {"source_identity": {"status": "BUILD_VERIFIED", "content_sha256": diagnostic.SOURCE},
                               "environment_verified": {"status": "VERIFIED"}}}
        def read(path):
            return expected if path == "inert-spec.json" else report
        with patch.object(diagnostic, "sha", return_value=cell["report_file_sha256"]), \
                patch.object(diagnostic, "read_document", side_effect=read), \
                patch.object(diagnostic, "verify_report", side_effect=lambda value: value):
            self.assertIs(diagnostic.bound_report(cell, plan, snapshot), report)
            swapped = {**cell, "method": "D1"}
            with self.assertRaisesRegex(ValueError, "binding_failed"):
                diagnostic.bound_report(swapped, plan, snapshot)

    def test_duplicate_replay_or_inflated_ledger_total_is_rejected(self):
        manifest = inert_manifest()
        _, cells = diagnostic.validate_manifest(manifest)
        summary = {"schema_version": "strategy-diagnostics-replay-v1", "plan_hash": manifest["plan_hash"],
                   "source_content_sha256": diagnostic.SOURCE, "verified": 16, "planned": 16,
                   "independent_ledger_checks": 16,
                   "receipts": [{"method": method, "cost_factor": cost, "ledger": {"checks": 1}} for method, cost in cells]}
        self.assertEqual(len(diagnostic.replay_matrix(summary, manifest, cells)), 16)
        duplicate = copy.deepcopy(summary)
        duplicate["receipts"][1] = duplicate["receipts"][0]
        with self.assertRaisesRegex(ValueError, "matrix_mismatch"):
            diagnostic.replay_matrix(duplicate, manifest, cells)
        inflated = {**summary, "independent_ledger_checks": 1000000}
        with self.assertRaisesRegex(ValueError, "sum_mismatch"):
            diagnostic.replay_matrix(inflated, manifest, cells)

    def test_public_export_preserves_original_identity_without_machine_paths(self):
        original = {"schema_version": "strategy-diagnostics-replay-v1", "receipts": [
            {"method": "D0", "cost_factor": 1, "replay": {
                "schema_version": "research-replay-receipt-v1", "receipt_hash": "a" * 64,
                "original_report_hash": "b" * 64, "original_result_hash": "c" * 64,
                "replay_verified": True, "replay_provenance": {
                    "machine_receipt": {"python_executable": "C:/private/python.exe", "package_location": "/home/private/package"},
                    "source_identity": {"content_sha256": diagnostic.SOURCE},
                    "environment_verified": {"status": "VERIFIED"}}}}]}
        before = diagnostic.canonical_bytes(original)
        public = diagnostic.public_replay_projection(original, "d" * 64)
        encoded = diagnostic.canonical_bytes(public).decode("utf-8")
        self.assertEqual(diagnostic.canonical_bytes(original), before)
        self.assertNotIn("machine_receipt", encoded)
        self.assertNotIn("C:/", encoded)
        self.assertNotIn("/home/", encoded)
        self.assertEqual(public["original_summary_file_sha256"], "d" * 64)
        projected = public["receipts"][0]["replay"]
        self.assertNotIn("receipt_hash", projected)
        self.assertEqual(projected["original_receipt_hash"], "a" * 64)
        self.assertEqual(projected["original_report_hash"], "b" * 64)
        self.assertEqual(projected["projection_hash"], diagnostic.digest({k: v for k, v in projected.items() if k != "projection_hash"}))
        self.assertEqual(public["projection_hash"], diagnostic.digest({k: v for k, v in public.items() if k != "projection_hash"}))


if __name__ == "__main__":
    unittest.main()
