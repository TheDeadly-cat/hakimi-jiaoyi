"""Retained v1/v2 report protocols, independently captured from target 4fb6d191."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research import reporting
from hakimi_research import reporting_legacy_v2 as legacy
from hakimi_research.experiment_provenance_consumer_adapter_v1 import (
    build_cli_report_provenance_bundle_candidate,
    verify_cli_report_provenance_bundle_candidate,
)


def fixture() -> dict:
    path = Path(__file__).parent / "fixtures" / "legacy_report_bundle_v2.json"
    return json.loads(path.read_text(encoding="utf-8"))


def expectations(document: dict) -> dict:
    return {
        "expected_reproducibility": document["expected_reproducibility"],
        "expected_context": document["expected_context"],
        "expected_manifest_identity": document["expected_manifest_identity"],
        "expected_artifact_identity": document["artifact_identity"],
    }


class LegacyReportingCompatibilityTests(unittest.TestCase):
    def test_actual_adapter_and_bundle_preserve_target_hashes_and_locks(self):
        document = fixture()
        receipt = build_cli_report_provenance_bundle_candidate(
            document["report"], **expectations(document),
        )
        self.assertEqual(receipt, document["receipt"])
        self.assertEqual(receipt["receipt_hash"], "54feb6ef953f39d69ab14be9dcb104cc5e2d49c63460319a0c020ec78e57b35d")
        self.assertTrue(verify_cli_report_provenance_bundle_candidate(
            receipt, document["report"], **expectations(document),
        ))
        bundle = reporting.build_json_report_bundle_v2(
            document["report"], receipt, artifact_identity=document["artifact_identity"],
        )
        self.assertEqual(bundle, document["bundle"])
        self.assertEqual(bundle["bundle_hash"], "a9da6ffe3faf74aa473f2e3582a45b92dffb1d3a1a8dd4a286444bc1a7c45cc8")
        self.assertTrue(reporting.verify_json_report_bundle_v2(bundle))
        self.assertTrue(bundle["external_artifact_hash_required"])
        for name in ("ranking_allowed", "paper_authorized", "live_order_allowed", "order_entry_allowed", "result_is_profitability_proof"):
            self.assertIs(bundle[name], False)

    def test_protocol_exports_and_rendered_bytes_are_preserved(self):
        for name in ("render_json_report", "plan_json_report_path", "build_json_report_bundle_v2",
                     "verify_json_report_bundle_v2", "save_json_report_bundle_v2", "_canonical_hash"):
            self.assertIs(getattr(reporting, name), getattr(legacy, name))
        self.assertIsNot(reporting.save_json_report, legacy.save_json_report)
        raw = reporting.render_json_report(fixture()["bundle"]).encode("utf-8")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "bac137bceca9c5cdd345ca2019b2e23fb86cc54b385ae9cb11cc6b22b2763ba1")

    def test_recursive_exact_native_json_rejections_are_retained(self):
        class StringAlias(str):
            pass
        class IntAlias(int):
            pass
        class ListAlias(list):
            pass
        class DictAlias(dict):
            pass
        cycle = []
        cycle.append(cycle)
        deep = []
        cursor = deep
        for _ in range(65):
            child = []
            cursor.append(child)
            cursor = child
        invalid = (DictAlias({}), {StringAlias("key"): 1}, {"v": StringAlias("x")},
                   {"v": IntAlias(1)}, {"v": ListAlias([1])}, {"v": (1, 2)},
                   {"v": float("nan")}, {"v": float("inf")}, {"v": cycle}, {"v": deep})
        with patch.object(reporting, "_save_encoded_report") as publish:
            for payload in invalid:
                with self.subTest(kind=type(payload)), self.assertRaises(ValueError):
                    legacy.save_json_report(payload, "reports", "backtest", artifact_id="a" * 64)
            publish.assert_not_called()

    def test_legacy_path_identity_checks_precede_publication(self):
        class StringAlias(str):
            pass
        cases = (("reports", "backtest", ""), (StringAlias("reports"), "backtest", "a" * 64),
                 ("reports", StringAlias("backtest"), "a" * 64), ("reports", "../escape", "a" * 64),
                 ("reports", "backtest", StringAlias("a" * 64)))
        with patch.object(reporting, "_save_encoded_report") as publish:
            for directory, prefix, artifact_id in cases:
                with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                    legacy.save_json_report({}, directory, prefix, artifact_id=artifact_id)
            publish.assert_not_called()
        path = legacy.plan_json_report_path("reports", "p" * 160, "a" * 64)
        self.assertEqual(path.name, "p" * 160 + "_" + "a" * 64 + ".json")

    def test_resealed_outer_bundle_does_not_hide_inner_receipt_change(self):
        bundle = copy.deepcopy(fixture()["bundle"])
        bundle["provenance_receipt"]["provenance_binding"]["context_hash"] = "0" * 64
        bundle["bundle_hash"] = legacy._canonical_hash({key: value for key, value in bundle.items() if key != "bundle_hash"})
        self.assertFalse(reporting.verify_json_report_bundle_v2(bundle))
        with patch.object(reporting, "_save_encoded_report") as publish:
            with self.assertRaises(ValueError):
                reporting.save_json_report_bundle_v2(bundle, "reports")
            publish.assert_not_called()

    def test_bundle_atomic_publish_is_byte_exact_idempotent_and_no_replace(self):
        bundle = fixture()["bundle"]
        with tempfile.TemporaryDirectory() as directory:
            first = Path(reporting.save_json_report_bundle_v2(bundle, directory))
            self.assertEqual(hashlib.sha256(first.read_bytes()).hexdigest(), "bac137bceca9c5cdd345ca2019b2e23fb86cc54b385ae9cb11cc6b22b2763ba1")
            self.assertEqual(reporting.save_json_report_bundle_v2(bundle, directory), str(first))
            self.assertEqual(list(Path(directory).iterdir()), [first])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / bundle["artifact_identity"]["filename"]
            path.write_bytes(b"existing immutable evidence\n")
            with self.assertRaises(FileExistsError):
                reporting.save_json_report_bundle_v2(bundle, directory)
            self.assertEqual(path.read_bytes(), b"existing immutable evidence\n")
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_bundle_staging_and_publish_failures_leave_no_final_artifact(self):
        for operation in ("fsync", "link"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                with patch.object(reporting.os, operation, side_effect=OSError("simulated storage failure")):
                    with self.assertRaises(OSError):
                        reporting.save_json_report_bundle_v2(fixture()["bundle"], directory)
                self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
